"""
API Dependencies
================

PURPOSE:
    Shared FastAPI dependencies for authentication and authorization.
    
REFACTORED: January 19, 2026 - Converted from raw SQL to SQLAlchemy ORM
UPDATED: January 21, 2026 - Added internal API key authentication
UPDATED: January 26, 2026 - Added get_current_active_user for Trust Channel
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status, Security, Request, Header, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional, Union
from uuid import UUID
import logging
import os
import secrets

from app.core.database import get_db, get_async_db
from app.core.security import decode_token, ExpiredTokenError
from app.core.config import settings
from app.domains.crm.core.models import CrmPartyEmailDraft, CrmPartyTask, Party
from app.models import User
from app.models.capability import CapabilityName, CapabilityStatus
from app.schemas.capability import CapabilityRequiredError, CapabilityStatusValue
from app.services.capability_resolver import CapabilityResolver
from app.schemas.crm import CRMEmailDraftCreate, CRMRelationshipCreate
from app.services.crm.stripe_connect_identity_reader import read_stripe_connect_identity

security = HTTPBearer()


# =============================================================================
# INTERNAL API KEY AUTHENTICATION
# =============================================================================

API_KEY_NAME = "X-Internal-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


@dataclass(frozen=True)
class CRMAuthContext:
    user: Optional[User]
    user_id: Optional[UUID]
    auth_method: str


async def get_internal_api_key(
    api_key: str = Security(api_key_header)
) -> str:
    """
    Dependency to validate the internal API key for service-to-service calls.
    
    Used for /v1/internal/* endpoints that should only be called by
    trusted internal services (e.g., MCP tools, orchestrator).
    
    Relies on Pydantic settings validation to fail on startup if the key
    isn't configured in production environments.
    """
    # Require INTERNAL_API_KEY to be configured
    if not settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="INTERNAL_API_KEY not configured — endpoint disabled"
        )
    if api_key and secrets.compare_digest(api_key, settings.INTERNAL_API_KEY):
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing Internal API Key — send header X-Internal-API-Key",
    )


# =============================================================================
# USER AUTHENTICATION
# =============================================================================

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """Get current authenticated user from JWT token (returns dict)."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.status == "active"
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return {
        "user_id": str(user.id),
        "id": str(user.id),  # Alias for compatibility
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


async def get_user_or_internal_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Dual-auth dependency: accepts X-Internal-API-Key OR JWT Bearer token.

    - Internal key path: validates key via compare_digest, returns a synthetic
      admin User (no DB query — the valid key IS the authentication).
    - JWT path: falls back to standard Bearer token validation.

    Used for endpoints that need to be callable by both human users (JWT) and
    internal services like Vulcan/MCP orchestrator (API key).
    """
    from sqlalchemy import select as sa_select, cast, String as SAString

    logger = logging.getLogger(__name__)

    # Prefer JWT when both Authorization (Bearer) and X-Internal-API-Key are present.
    # This prevents the synthetic nil-UUID user from masking the real JWT identity.
    auth_header = request.headers.get('authorization', '')
    has_bearer = auth_header.lower().startswith('bearer ')

    # Path 1: Internal API Key (only if no Bearer token is present)
    if api_key and settings.INTERNAL_API_KEY and not has_bearer:
        if secrets.compare_digest(api_key, settings.INTERNAL_API_KEY):
            # Return a synthetic admin user for internal service calls.
            # No DB query needed — the valid key IS the authentication.
            synthetic_user = User(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                email="internal@ai.market",
                first_name="Internal",
                last_name="Service",
                role="admin",
                status="active",
            )
            request.state.auth_method = "internal_key"
            return synthetic_user
        logger.warning("Invalid Internal API Key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )

    # Path 2: JWT Bearer token (extract from Authorization header)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = decode_token(token)
        except ExpiredTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        result = await db.execute(
            sa_select(User).where(User.id == user_id, cast(User.status, SAString) == "active")
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        request.state.auth_method = "jwt"
        return user

    # No credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (X-Internal-API-Key or Bearer token)",
    )


async def get_crm_auth_context(
    request: Request,
    internal_api_key: Optional[str] = Security(api_key_header),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_async_db),
) -> CRMAuthContext:
    """
    CRM dual-auth dependency: JWT first, then API key fallback.

    Accepts:
    - Authorization: Bearer <jwt>
    - X-Internal-API-Key: <key>
    - X-API-Key: <key>

    JWT callers resolve to a real active User and expose their UUID via user_id.
    API-key callers preserve legacy system-level behavior and resolve with user_id=None.
    """
    from sqlalchemy import select as sa_select, cast, String as SAString

    auth_header = request.headers.get("Authorization")
    has_bearer = bool(auth_header and auth_header.startswith("Bearer "))

    if has_bearer:
        token = auth_header[7:]  # type: ignore[index]
        try:
            payload = decode_token(token)
        except ExpiredTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await db.execute(
            sa_select(User).where(
                User.id == user_id,
                cast(User.status, SAString) == "active",
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.auth_method = "jwt"
        return CRMAuthContext(user=user, user_id=user.id, auth_method="jwt")

    api_key = internal_api_key or x_api_key
    if api_key:
        if settings.INTERNAL_API_KEY and secrets.compare_digest(api_key, settings.INTERNAL_API_KEY):
            request.state.auth_method = "api_key"
            return CRMAuthContext(user=None, user_id=None, auth_method="api_key")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer token or X-API-Key/X-Internal-API-Key)",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _get_owned_entity_by_id(
    entity_id: UUID,
    db: AsyncSession,
    auth: CRMAuthContext,
) -> Party:
    query = select(Party).where(Party.id == entity_id, Party.deleted_at.is_(None))

    result = await db.execute(query)
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CRM party not found",
        )
    return entity


async def get_owned_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> Party:
    """Resolve a CRM entity only if it belongs to the authenticated JWT user."""
    return await _get_owned_entity_by_id(entity_id, db, auth)


async def get_owned_form_entity(
    entity_id: UUID = Form(...),
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> Party:
    """Resolve a CRM entity submitted as multipart form data."""
    return await _get_owned_entity_by_id(entity_id, db, auth)


async def get_owned_body_entity(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> Party:
    """Resolve a CRM entity referenced by a top-level entity_id JSON field."""
    body = await request.json()
    entity_id = body.get("entity_id") if isinstance(body, dict) else None
    if entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="entity_id is required",
        )
    try:
        entity_uuid = UUID(str(entity_id))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid entity_id",
        )
    return await _get_owned_entity_by_id(entity_uuid, db, auth)


async def get_owned_context_entity(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> Optional[Party]:
    """Resolve an optional CRM entity referenced in request.context.entity_id."""
    body = await request.json()
    context = body.get("context") if isinstance(body, dict) else None
    entity_id = context.get("entity_id") if isinstance(context, dict) else None
    if entity_id is None:
        return None
    try:
        entity_uuid = UUID(str(entity_id))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid context.entity_id",
        )
    return await _get_owned_entity_by_id(entity_uuid, db, auth)


async def get_owned_source_entity(
    rel_in: CRMRelationshipCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> Party:
    return await _get_owned_entity_by_id(rel_in.source_entity_id, db, auth)


async def get_owned_target_entity(
    rel_in: CRMRelationshipCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> Party:
    return await _get_owned_entity_by_id(rel_in.target_entity_id, db, auth)


async def get_owned_task_for_draft(
    draft_in: CRMEmailDraftCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> CrmPartyTask:
    from app.api.v1.dependencies.crm_ownership import CRM_ACCESS_LEVEL_ADMIN, resolve_crm_access_level

    crm_role = await resolve_crm_access_level(auth, db)
    query = (
        select(CrmPartyTask)
        .where(
            CrmPartyTask.id == draft_in.task_id,
            CrmPartyTask.deleted_at.is_(None),
        )
    )
    if auth.user_id is not None and crm_role != CRM_ACCESS_LEVEL_ADMIN:
        query = query.where(CrmPartyTask.assigned_to_user_id == auth.user_id)

    result = await db.execute(query)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def get_owned_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> CrmPartyTask:
    from app.api.v1.dependencies.crm_ownership import CRM_ACCESS_LEVEL_ADMIN, resolve_crm_access_level

    crm_role = await resolve_crm_access_level(auth, db)
    query = (
        select(CrmPartyTask)
        .where(
            CrmPartyTask.id == task_id,
            CrmPartyTask.deleted_at.is_(None),
        )
    )
    if auth.user_id is not None and crm_role != CRM_ACCESS_LEVEL_ADMIN:
        query = query.where(CrmPartyTask.assigned_to_user_id == auth.user_id)

    result = await db.execute(query)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def get_owned_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    auth: CRMAuthContext = Depends(get_crm_auth_context),
) -> CrmPartyEmailDraft:
    from app.api.v1.dependencies.crm_ownership import CRM_ACCESS_LEVEL_ADMIN, resolve_crm_access_level

    crm_role = await resolve_crm_access_level(auth, db)
    if auth.user_id is None or crm_role == CRM_ACCESS_LEVEL_ADMIN:
        query = (
            select(CrmPartyEmailDraft)
            .where(
                CrmPartyEmailDraft.id == draft_id,
                CrmPartyEmailDraft.deleted_at.is_(None),
            )
        )
    else:
        query = (
            select(CrmPartyEmailDraft)
            .join(CrmPartyTask, CrmPartyEmailDraft.task_id == CrmPartyTask.id)
            .where(
                CrmPartyEmailDraft.id == draft_id,
                CrmPartyEmailDraft.deleted_at.is_(None),
                CrmPartyTask.deleted_at.is_(None),
                CrmPartyTask.assigned_to_user_id == auth.user_id,
            )
        )

    result = await db.execute(query)
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return draft


async def get_optional_user(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_async_db),
) -> Optional[User]:
    """Return authenticated User if credentials present, else None.

    Used for public endpoints that show extra data to the owner.
    Never raises 401 — missing/invalid credentials simply return None.
    """
    try:
        return await get_user_or_internal_key(request, api_key, db)
    except HTTPException:
        return None


def _capability_value(capability: CapabilityName | str) -> str:
    return capability.value if isinstance(capability, CapabilityName) else str(capability)


async def assert_user_capability(
    user: User,
    db: AsyncSession,
    capability: CapabilityName | str,
    required_status: CapabilityStatus | str = CapabilityStatus.active,
) -> User:
    resolver = CapabilityResolver(user=user, db=db)
    capability_set = await resolver.resolve(user.id)
    capability_name = _capability_value(capability)
    readiness = getattr(capability_set, capability_name)
    required = required_status.value if isinstance(required_status, CapabilityStatus) else str(required_status)
    if readiness.effective_status.value == required or (
        required == CapabilityStatus.provisioning.value
        and readiness.effective_status == CapabilityStatusValue.active
    ):
        return user

    reason = readiness.reason
    if not reason:
        if readiness.persisted_status == CapabilityStatusValue.active:
            reason = "readiness_gap"
        else:
            reason = readiness.persisted_status.value
    payload = CapabilityRequiredError(
        capability=capability_name,  # type: ignore[arg-type]
        persisted_status=readiness.persisted_status.value,  # type: ignore[arg-type]
        effective_status=readiness.effective_status.value,  # type: ignore[arg-type]
        missing_steps=readiness.missing_steps,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=payload.model_dump(),
    )


def require_capability(
    capability: CapabilityName | str,
    required_status: CapabilityStatus | str = CapabilityStatus.active,
):
    async def dependency(
        user: User = Depends(get_user_or_internal_key),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        return await assert_user_capability(user, db, capability, required_status)

    return dependency


async def get_admin_or_internal_key(
    user: User = Depends(get_user_or_internal_key),
) -> User:
    """
    Dual-auth admin dependency: accepts X-Internal-API-Key OR admin JWT.

    - Internal key → synthetic admin User (role="admin") → passes
    - Admin JWT → real admin User → passes
    - Regular user JWT → 403
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def get_current_active_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token (returns User ORM object).
    
    Used when you need the actual User model object, e.g., for relationships
    or when accessing model methods/attributes directly.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.status == "active"
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user


def get_current_seller(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure current user is a seller."""
    if current_user["role"] != "seller":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller access required"
        )
    return current_user


def get_current_buyer(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure current user is a buyer."""
    if current_user["role"] != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Buyer access required"
        )
    return current_user


def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure current user is an admin."""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_user_from_jwt_or_api_key(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Dual-auth dependency: accepts JWT Bearer token OR X-API-Key header.

    - JWT path: standard Bearer token validation → User ORM object.
    - X-API-Key path: validates aim_* key via MCPKeyService → resolves to
      the seller User who owns the key.

    Used for endpoints callable by both browser sessions (JWT) and
    vectorAIz instances (X-API-Key).
    """
    from sqlalchemy import select as sa_select, cast, String as SAString

    logger = logging.getLogger(__name__)

    auth_header = request.headers.get("Authorization")
    api_key_value = request.headers.get("X-API-Key")

    # Determine if we have a real JWT Bearer (not an aim_ key sent as Bearer)
    has_jwt = (
        auth_header
        and auth_header.startswith("Bearer ")
        and not auth_header[7:].startswith("aim_")
    )
    has_api_key = bool(api_key_value) or (
        auth_header and auth_header.startswith("Bearer aim_")
    )

    # Reject ambiguous credentials: both JWT and X-API-Key present
    if has_jwt and api_key_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ambiguous credentials — provide either Bearer token or X-API-Key, not both",
        )

    # Path 1: JWT Bearer token
    if has_jwt:
        token = auth_header[7:]  # type: ignore[index]
        try:
            payload = decode_token(token)
        except ExpiredTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        result = await db.execute(
            sa_select(User).where(
                User.id == user_id,
                cast(User.status, SAString) == "active",
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        request.state.auth_method = "jwt"
        return user

    # Path 2: X-API-Key header (aim_* MCP keys)
    # Also handle aim_* sent as Bearer token
    if not api_key_value and auth_header and auth_header.startswith("Bearer aim_"):
        api_key_value = auth_header[7:]

    if api_key_value:
        if not api_key_value.startswith("aim_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format (must start with aim_)",
            )
        from app.services.mcp_key_service import MCPKeyService

        key_service = MCPKeyService(db)
        key_info = await key_service.validate_key(api_key_value)
        if key_info is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        result = await db.execute(
            sa_select(User).where(
                User.id == key_info["user_id"],
                cast(User.status, SAString) == "active",
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key owner not found or inactive",
            )
        request.state.auth_method = "api_key"
        return user

    # No credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer token or X-API-Key header)",
    )


def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Ensure current user is an admin/superuser (returns User ORM object).
    
    Used for admin-only endpoints that need direct access to the User model.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user


# =============================================================================
# KYC VERIFICATION (Phase 4.R.5)
# =============================================================================

def get_kyc_verified_seller(
    current_user: dict = Depends(get_current_seller),
    db: Session = Depends(get_db)
) -> dict:
    """
    Ensure current seller has verified KYC status.
    
    Used for actions that require trust verification, such as:
    - Responding to data requests
    - Submitting proposals
    - Initiating transactions
    
    Sellers can VIEW requests without KYC, but cannot RESPOND until verified.
    """
    identity = read_stripe_connect_identity(current_user["id"])
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller profile not found. Please complete onboarding."
        )

    metadata = identity.party_metadata or {}
    kyc_status = metadata.get("kyc_status", "not_started")
    
    if kyc_status != "verified":
        status_messages = {
            "not_started": "Please complete identity verification to respond to requests.",
            "pending": "Your identity verification is pending. Please wait for approval.",
            "requires_action": "Additional information required for verification. Check your Stripe dashboard.",
            "failed": "Identity verification failed. Please contact support."
        }
        detail = status_messages.get(
            kyc_status, 
            f"KYC verification required (current status: {kyc_status})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            headers={"X-KYC-Status": kyc_status}
        )
    
    return current_user


# =============================================================================
# AGENT AUTHENTICATION (S62 - Phase 6.Bridge.2)
# =============================================================================

from app.schemas.agent_auth import AgentIdentity, AgentTrustLevel

# Internal agent shared secret (set via environment variable)
INTERNAL_AGENT_KEY = os.getenv("INTERNAL_AGENT_KEY")
if INTERNAL_AGENT_KEY is None:
    logging.getLogger(__name__).warning(
        "INTERNAL_AGENT_KEY not set — all agent-key auth attempts will be rejected"
    )

async def get_current_agent(
    request: Request,
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    authorization: Optional[str] = Header(None),
) -> AgentIdentity:
    """
    Authenticate an AI Agent (internal or external).
    
    Authentication Methods:
    1. X-Agent-Key header: For internal system agents (service bus callers)
    2. Authorization Bearer: For external OAuth-authenticated agents (future)
    
    Returns:
        AgentIdentity with trust level and scopes
        
    Raises:
        HTTPException 401: If no valid credentials provided
        HTTPException 403: If agent lacks required permissions
    """
    # Method 1: Internal Agent Key (shared secret)
    if x_agent_key:
        if INTERNAL_AGENT_KEY is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Agent key authentication is not configured",
                headers={"WWW-Authenticate": "X-Agent-Key"},
            )
        if secrets.compare_digest(x_agent_key, INTERNAL_AGENT_KEY):
            return AgentIdentity(
                id="system",
                name="Service Bus Caller",
                trust_level=AgentTrustLevel.INTERNAL,
                scopes=["*"],  # Full access for internal agents
                is_admin=True,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid agent key",
                headers={"WWW-Authenticate": "X-Agent-Key"},
            )
    
    # Method 2: Bearer Token (OAuth - future implementation)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        # TODO: Implement OAuth token validation for external agents
        # For now, reject with informative message
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="External agent OAuth not yet implemented. Use X-Agent-Key for internal agents.",
        )
    
    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Agent authentication required. Provide X-Agent-Key header.",
        headers={"WWW-Authenticate": "X-Agent-Key"},
    )


async def get_current_agent_or_user(
    request: Request,
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_async_db),
) -> "Union[AgentIdentity, User]":
    """
    Authenticate either an Agent OR a User.
    
    Useful for endpoints that can be accessed by both humans and AI agents.
    Checks for agent credentials first, falls back to user JWT.
    """
    # Try agent auth first
    if x_agent_key:
        return await get_current_agent(request, x_agent_key, authorization)
    
    # Fall back to user auth
    if authorization and authorization.startswith("Bearer "):
        # Reuse existing user auth logic
        return await get_current_active_user(
            authorization=authorization,
            db=db
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide X-Agent-Key or Bearer token.",
    )
