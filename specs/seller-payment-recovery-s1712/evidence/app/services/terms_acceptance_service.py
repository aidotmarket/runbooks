"""Terms acceptance recording and shadow/enforcement guard for S1137."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


logger = logging.getLogger(__name__)

TERMS_ACK_SNAPSHOT = {
    "ack_box1": "I have read and agree to the current ai.market Terms of Service.",
    "ack_box2": "I understand that marketplace transactions and listings are governed by these terms.",
    "ack_box3": "I understand ai.market may update these terms and that continued use may require acceptance of updated terms.",
}


@dataclass(frozen=True)
class TermsActor:
    user_id: UUID | None = None
    party_id: UUID | None = None
    org_id: UUID | None = None


def _parse_terms_published_at() -> datetime:
    value = settings.TERMS_PUBLISHED_AT
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def terms_config_payload() -> dict[str, Any]:
    return {
        "terms_version": settings.CURRENT_TERMS_VERSION,
        "terms_hash_sha256": settings.current_terms_hash_sha256,
        "terms_url": settings.TERMS_URL,
        "terms_published_at": _parse_terms_published_at(),
        "checkbox_snapshot": TERMS_ACK_SNAPSHOT,
    }


async def resolve_user_party_id(db: AsyncSession, user_id: UUID) -> UUID | None:
    result = await db.execute(
        text(
            """
            SELECT party_id
            FROM party_identity
            WHERE provider = 'auth_user'
              AND external_id = :external_id
              AND is_primary = true
            LIMIT 1
            """
        ),
        {"external_id": str(user_id)},
    )
    return result.scalar_one_or_none()


async def has_current_terms_acceptance(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    party_id: UUID | None = None,
    org_id: UUID | None = None,
    scope: str | None = None,
) -> bool:
    row = await get_latest_terms_acceptance(
        db,
        user_id=user_id,
        party_id=party_id,
        org_id=org_id,
        scope=scope,
        current_version_only=True,
    )
    return row is not None


async def get_latest_terms_acceptance(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    party_id: UUID | None = None,
    org_id: UUID | None = None,
    scope: str | None = None,
    current_version_only: bool = False,
) -> dict[str, Any] | None:
    clauses: list[str] = []
    params: dict[str, Any] = {}
    if party_id is not None:
        clauses.append("party_id = :party_id")
        params["party_id"] = party_id
    if org_id is not None:
        clauses.append("org_id = :org_id")
        params["org_id"] = org_id
    if user_id is not None:
        clauses.append("accepted_by_user_id = :user_id")
        params["user_id"] = user_id
    if not clauses:
        return None

    scope_clause = ""
    if scope is not None:
        scope_clause = "AND scope = :scope"
        params["scope"] = scope

    version_clause = ""
    if current_version_only:
        version_clause = "AND terms_version = :current_version"
        params["current_version"] = settings.CURRENT_TERMS_VERSION

    result = await db.execute(
        text(
            f"""
            SELECT id, accepted_by_user_id, party_id, org_id, scope, terms_version, accepted_at
            FROM terms_acceptance
            WHERE ({' OR '.join(clauses)})
              {scope_clause}
              {version_clause}
            ORDER BY accepted_at DESC, created_at DESC, id DESC
            LIMIT 1
            """
        ),
        params,
    )
    row = result.mappings().fetchone()
    return dict(row) if row else None


async def record_terms_acceptance(
    db: AsyncSession,
    *,
    accepted_by_user_id: UUID,
    scope: str,
    signer_full_name: str,
    signer_title: str,
    business_legal_name: str,
    authority_ack: bool,
    ack_box1: bool,
    ack_box2: bool,
    ack_box3: bool,
    party_id: UUID | None = None,
    org_id: UUID | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    auth_session_id: str | None = None,
    accepted_at: datetime | None = None,
    admin_initiated: bool = False,
    admin_note: str | None = None,
) -> dict[str, Any]:
    cfg = terms_config_payload()
    accepted_at = accepted_at or datetime.now(timezone.utc)
    result = await db.execute(
        text(
            """
            INSERT INTO terms_acceptance (
                accepted_by_user_id, party_id, org_id, scope,
                terms_version, terms_hash_sha256, terms_url, terms_published_at,
                checkbox_snapshot, accepted_at, signer_full_name, signer_title,
                business_legal_name, authority_ack, ack_box1, ack_box2, ack_box3,
                ip, user_agent, auth_session_id, admin_initiated, admin_note
            ) VALUES (
                :accepted_by_user_id, :party_id, :org_id, :scope,
                :terms_version, :terms_hash_sha256, :terms_url, :terms_published_at,
                CAST(:checkbox_snapshot AS jsonb), :accepted_at, :signer_full_name, :signer_title,
                :business_legal_name, :authority_ack, :ack_box1, :ack_box2, :ack_box3,
                CAST(:ip AS inet), :user_agent, :auth_session_id, :admin_initiated, :admin_note
            )
            RETURNING id, accepted_by_user_id, party_id, org_id, scope, terms_version, accepted_at
            """
        ),
        {
            "accepted_by_user_id": accepted_by_user_id,
            "party_id": party_id,
            "org_id": org_id,
            "scope": scope,
            "terms_version": cfg["terms_version"],
            "terms_hash_sha256": cfg["terms_hash_sha256"],
            "terms_url": cfg["terms_url"],
            "terms_published_at": cfg["terms_published_at"],
            "checkbox_snapshot": json.dumps(cfg["checkbox_snapshot"], sort_keys=True),
            "accepted_at": accepted_at,
            "signer_full_name": signer_full_name.strip(),
            "signer_title": signer_title.strip(),
            "business_legal_name": business_legal_name.strip(),
            "authority_ack": authority_ack,
            "ack_box1": ack_box1,
            "ack_box2": ack_box2,
            "ack_box3": ack_box3,
            "ip": ip,
            "user_agent": user_agent[:512] if user_agent else None,
            "auth_session_id": auth_session_id,
            "admin_initiated": admin_initiated,
            "admin_note": admin_note,
        },
    )
    row = dict(result.mappings().one())
    await db.commit()
    return row


async def require_terms_acceptance(
    db: AsyncSession,
    *,
    actor: TermsActor,
    endpoint: str,
) -> bool:
    """Require current terms acceptance for the acting party.

    In shadow mode this never blocks. It logs would-block metadata only.
    """
    mode = settings.TERMS_GATE_MODE
    if mode == "off":
        return True

    if mode == "shadow" and settings.ENVIRONMENT == "test":
        logger.warning(
            "terms_acceptance_would_block %s",
            json.dumps(
                {
                    "event": "terms_acceptance_would_block",
                    "mode": mode,
                    "endpoint": endpoint,
                    "user_id": str(actor.user_id) if actor.user_id else None,
                    "party_id": str(actor.party_id) if actor.party_id else None,
                    "org_id": str(actor.org_id) if actor.org_id else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "terms_version": settings.CURRENT_TERMS_VERSION,
                    "measurement_skipped": "test_environment",
                },
                sort_keys=True,
            ),
        )
        return False

    try:
        accepted = await has_current_terms_acceptance(
            db,
            user_id=actor.user_id,
            party_id=actor.party_id,
            org_id=actor.org_id,
        )
    except Exception:
        if mode == "shadow":
            logger.exception(
                "terms_acceptance_shadow_check_failed endpoint=%s user_id=%s party_id=%s org_id=%s",
                endpoint,
                actor.user_id,
                actor.party_id,
                actor.org_id,
            )
            return False
        raise
    if accepted:
        return True

    payload = {
        "event": "terms_acceptance_would_block",
        "mode": mode,
        "endpoint": endpoint,
        "user_id": str(actor.user_id) if actor.user_id else None,
        "party_id": str(actor.party_id) if actor.party_id else None,
        "org_id": str(actor.org_id) if actor.org_id else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "terms_version": settings.CURRENT_TERMS_VERSION,
    }
    if mode == "shadow":
        logger.warning("terms_acceptance_would_block %s", json.dumps(payload, sort_keys=True))
        return False

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "TERMS_ACCEPTANCE_REQUIRED",
            "terms_url": settings.TERMS_URL,
            "acceptance_url": "/api/v1/legal/terms/accept",
        },
    )
