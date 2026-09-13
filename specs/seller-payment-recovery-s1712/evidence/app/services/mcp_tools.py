"""
Public MCP tools for ai.market marketplace discovery.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.listing_public import (
    VerificationArtifactPublic,
    VerificationWithdrawalPublic,
)
from app.services.data_verification_service import verification_public_projection
from app.services.jsonld_service import (
    mask_public_jsonld_urls,
    sanitize_public_properties,
)
from app.services import data_request_service


SEARCH_LIMIT_DEFAULT = 10
SEARCH_LIMIT_MAX = 25
SEARCH_OFFSET_MAX = 10_000


class SearchListingItem(BaseModel):
    listing_id: UUID
    slug: Optional[str] = None
    title: str
    short_description: Optional[str] = None
    category: Optional[str] = None
    price: float
    pricing_type: Optional[str] = None
    trust_level: Optional[str] = None
    data_format: Optional[str] = None
    published_at: Optional[Any] = None


class SearchListingsResponse(BaseModel):
    query: str
    category: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    limit: int
    offset: int
    count: int
    listings: List[SearchListingItem]


class SearchBuyerRequestItem(BaseModel):
    request_id: UUID
    slug: str
    canonical_url: str
    title: str
    description: str
    categories: List[str] = Field(default_factory=list)
    format_preferences: List[str] = Field(default_factory=list)
    urgency: str
    price_range_min: Optional[float] = None
    price_range_max: Optional[float] = None
    currency: str = "USD"
    regulatory_requirements: List[str] = Field(default_factory=list)
    provenance_requirements: Optional[str] = None
    published_at: Optional[Any] = None
    expires_at: Optional[Any] = None


class SearchBuyerRequestsResponse(BaseModel):
    query: str
    category: Optional[str] = None
    urgency: Optional[str] = None
    limit: int
    page: int
    count: int
    total: int
    requests: List[SearchBuyerRequestItem]


class TrustAttestationSummary(BaseModel):
    available: bool
    verified: bool = False
    uploaded_at: Optional[Any] = None
    issuer: Optional[str] = None
    proof_type: Optional[str] = None
    merkle_root: Optional[str] = None
    pii_risk_level: Optional[str] = None
    overall_completeness: Optional[float] = None
    overall_consistency: Optional[float] = None
    overall_uniqueness: Optional[float] = None
    sample_challenge_pass: Optional[bool] = None
    fingerprint: Optional[Dict[str, Any]] = None


class SchemaColumnPreview(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class SchemaPreview(BaseModel):
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    data_format: Optional[str] = None
    columns: List[SchemaColumnPreview] = Field(default_factory=list)


class ListingDetailPayload(BaseModel):
    listing_id: UUID
    slug: Optional[str] = None
    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: Optional[str] = None
    secondary_categories: Optional[Any] = None
    tags: Optional[Any] = None
    price: float
    pricing_type: Optional[str] = None
    subscription_price_monthly: Optional[float] = None
    data_format: Optional[str] = None
    update_frequency: Optional[str] = None
    source_row_count: Optional[int] = None
    source_column_count: Optional[int] = None
    trust_level: Optional[str] = None
    privacy_score: float = 0.0
    searchability_score: float = 0.0
    raw_metadata: Optional[Any] = None
    jsonld: Optional[Any] = None
    synthetic_queries: Optional[Any] = None
    published_at: Optional[Any] = None
    schema_info: Optional[Any] = None
    trust_attestation: TrustAttestationSummary
    schema_preview: SchemaPreview


class ListingDetailResponse(BaseModel):
    listing: ListingDetailPayload


class TrustEvaluationResponse(BaseModel):
    listing_id: UUID
    slug: Optional[str] = None
    status: Literal["published", "withdrawn", "not_available"]
    scan_findings: VerificationArtifactPublic | VerificationWithdrawalPublic | None


class PriceCheckResponse(BaseModel):
    listing_id: UUID
    slug: Optional[str] = None
    title: str
    price: float
    pricing_type: Optional[str] = None
    subscription_price_monthly: Optional[float] = None
    currency: str = "USD"
    availability: str
    fulfillment_method: str
    listing_type: Optional[str] = None
    published_at: Optional[Any] = None


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_value(val) for key, val in value.items()}
    return value


def _parse_jsonish(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: _normalize_value(value) for key, value in row.items()}
    for key in (
        "secondary_categories",
        "tags",
        "schema_info",
        "compliance_details",
        "raw_metadata",
        "source_delivery",
        "jsonld",
        "synthetic_queries",
        "quality_attestation_vc",
        "privacy_score_breakdown",
        "quality_score_breakdown",
    ):
        if key in normalized:
            normalized[key] = _parse_jsonish(normalized[key])
    return normalized


def _validate_listing_id(listing_id: str | UUID | None) -> UUID | None:
    if listing_id is None:
        return None
    if isinstance(listing_id, UUID):
        return listing_id
    try:
        return UUID(str(listing_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="listing_id must be a valid UUID") from exc


def _resolve_listing_clause(listing_id: str | UUID | None, slug: str | None) -> tuple[str, dict[str, Any]]:
    resolved_id = _validate_listing_id(listing_id)
    if resolved_id:
        return "l.id = :listing_id", {"listing_id": resolved_id}
    if slug:
        return "l.slug = :slug", {"slug": slug}
    raise HTTPException(status_code=400, detail="One of listing_id or slug is required")


def _extract_attestation_summary(row: dict[str, Any]) -> TrustAttestationSummary:
    vc = row.get("quality_attestation_vc")
    if not isinstance(vc, dict):
        return TrustAttestationSummary(
            available=False,
            verified=bool(row.get("attestation_verified")),
            uploaded_at=row.get("attestation_uploaded_at"),
        )

    subject = vc.get("credentialSubject") or {}
    fingerprint = subject.get("fingerprint") if isinstance(subject, dict) else None
    if not isinstance(fingerprint, dict) and any(key in vc for key in ("columns", "overall_completeness", "merkle_root")):
        fingerprint = vc

    proof = vc.get("proof") if isinstance(vc.get("proof"), dict) else {}
    return TrustAttestationSummary(
        available=True,
        verified=bool(row.get("attestation_verified")),
        uploaded_at=row.get("attestation_uploaded_at"),
        issuer=vc.get("issuer"),
        proof_type=proof.get("type"),
        merkle_root=(fingerprint or {}).get("merkle_root"),
        pii_risk_level=(fingerprint or {}).get("pii_risk_level"),
        overall_completeness=(fingerprint or {}).get("overall_completeness"),
        overall_consistency=(fingerprint or {}).get("overall_consistency"),
        overall_uniqueness=(fingerprint or {}).get("overall_uniqueness"),
        sample_challenge_pass=(fingerprint or {}).get("sample_challenge_pass"),
        fingerprint=fingerprint,
    )


def _build_schema_preview(row: dict[str, Any]) -> SchemaPreview:
    schema_info = row.get("schema_info")
    if not isinstance(schema_info, dict):
        return SchemaPreview(
            row_count=row.get("source_row_count"),
            column_count=row.get("source_column_count"),
            data_format=row.get("data_format"),
            columns=[],
        )

    raw_columns = schema_info.get("columns") or schema_info.get("fields") or []
    columns: list[SchemaColumnPreview] = []
    if isinstance(raw_columns, list):
        for item in raw_columns[:10]:
            if isinstance(item, dict):
                columns.append(
                    SchemaColumnPreview(
                        name=item.get("name"),
                        type=item.get("type") or item.get("dtype"),
                        description=item.get("description"),
                    )
                )
            else:
                columns.append(SchemaColumnPreview(name=str(item)))

    return SchemaPreview(
        row_count=row.get("source_row_count") or schema_info.get("row_count"),
        column_count=row.get("source_column_count") or schema_info.get("column_count") or len(raw_columns),
        data_format=row.get("data_format") or schema_info.get("format"),
        columns=columns,
    )


def _fulfillment_method(row: dict[str, Any]) -> str:
    listing_type = row.get("listing_type")
    if listing_type == "raw":
        return "file_download"
    return "api_access"


async def _get_listing_row(
    db: AsyncSession,
    *,
    listing_id: str | UUID | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    clause, params = _resolve_listing_clause(listing_id, slug)
    result = await db.execute(
        text(
            f"""
            SELECT
                l.id,
                l.slug,
                l.title,
                l.description,
                l.short_description,
                l.category,
                l.secondary_categories,
                l.tags,
                l.price,
                l.pricing_type,
                l.subscription_price_monthly,
                l.data_format,
                l.update_frequency,
                l.source_row_count,
                l.source_column_count,
                l.schema_info,
                l.privacy_score,
                l.quality_score,
                l.searchability_score,
                l.trust_level,
                l.verification_status,
                l.compliance_status,
                l.compliance_details,
                l.privacy_score_breakdown,
                l.quality_score_breakdown,
                l.raw_metadata,
                l.listing_type,
                l.source_delivery,
                l.jsonld,
                l.synthetic_queries,
                l.quality_attestation_vc,
                l.attestation_verified,
                l.attestation_uploaded_at,
                l.public_verification_epoch_id,
                ve.state AS verification_publication_state,
                ve.public_artifact_payload AS verification_public_artifact,
                ve.withdrawn_at AS verification_withdrawn_at,
                l.published_at
            FROM listings l
            LEFT JOIN verification_epochs ve
              ON ve.epoch_id = l.public_verification_epoch_id
            WHERE l.status = 'published' AND {clause}
            LIMIT 1
            """
        ),
        params,
    )
    row = result.mappings().fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _normalize_row(dict(row))


async def search_listings(
    db: AsyncSession,
    *,
    query: str | None = None,
    keyword: str | None = None,
    category: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    limit: int = SEARCH_LIMIT_DEFAULT,
    offset: int = 0,
) -> dict[str, Any]:
    resolved_query = query if query is not None else keyword
    if not resolved_query or not resolved_query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    if price_min is not None and price_max is not None and price_min > price_max:
        raise HTTPException(status_code=400, detail="price_min cannot exceed price_max")

    safe_limit = max(1, min(int(limit), SEARCH_LIMIT_MAX))
    safe_offset = max(0, min(int(offset), SEARCH_OFFSET_MAX))

    sql = """
        SELECT
            l.id AS listing_id,
            l.slug,
            l.title,
            l.short_description,
            l.category,
            l.price,
            l.pricing_type,
            l.trust_level,
            l.data_format,
            l.published_at
        FROM listings l
        WHERE l.status = 'published'
          AND (
            l.title ILIKE :search
            OR COALESCE(l.short_description, '') ILIKE :search
            OR COALESCE(l.description, '') ILIKE :search
            OR COALESCE(l.category, '') ILIKE :search
            OR COALESCE(l.tags::text, '') ILIKE :search
          )
    """
    params: dict[str, Any] = {
        "search": f"%{resolved_query.strip()}%",
        "prefix_search": f"{resolved_query.strip()}%",
        "limit": safe_limit,
        "offset": safe_offset,
    }

    if category:
        sql += " AND l.category = :category"
        params["category"] = category
    if price_min is not None:
        sql += " AND l.price >= :price_min"
        params["price_min"] = price_min
    if price_max is not None:
        sql += " AND l.price <= :price_max"
        params["price_max"] = price_max
    sql += """
        ORDER BY
            CASE WHEN l.title ILIKE :prefix_search THEN 0 ELSE 1 END,
            l.published_at DESC NULLS LAST,
            l.created_at DESC
        LIMIT :limit OFFSET :offset
    """

    result = await db.execute(text(sql), params)
    rows = []
    for raw_row in result.mappings().fetchall():
        row = _normalize_row(dict(raw_row))
        if "listing_id" not in row and "id" in row:
            row["listing_id"] = row["id"]
        rows.append(row)
    response = SearchListingsResponse(
        query=resolved_query,
        category=category,
        price_min=price_min,
        price_max=price_max,
        limit=safe_limit,
        offset=safe_offset,
        count=len(rows),
        listings=[SearchListingItem.model_validate(row) for row in rows],
    )
    return response.model_dump(mode="json")


async def search_buyer_requests(
    db: AsyncSession,
    *,
    query: str,
    category: str | None = None,
    urgency: str | None = None,
    limit: int = SEARCH_LIMIT_DEFAULT,
    page: int = 1,
) -> dict[str, Any]:
    resolved_query = query.strip()
    if not resolved_query:
        raise HTTPException(status_code=400, detail="query is required")

    safe_limit = max(1, min(int(limit), SEARCH_LIMIT_MAX))
    safe_page = max(1, int(page))
    requests, total = await data_request_service.list_requests(
        db,
        search=resolved_query,
        categories=[category] if category else None,
        urgency=urgency,
        page=safe_page,
        per_page=safe_limit,
        public_only=True,
    )
    items = [
        SearchBuyerRequestItem(
            request_id=request.id,
            slug=request.slug,
            canonical_url=f"https://ai.market/requests/{request.slug}",
            title=request.title,
            description=request.description,
            categories=request.categories or [],
            format_preferences=request.format_preferences or [],
            urgency=request.urgency,
            price_range_min=request.price_range_min,
            price_range_max=request.price_range_max,
            currency=request.currency or "USD",
            regulatory_requirements=request.regulatory_requirements or [],
            provenance_requirements=request.provenance_requirements,
            published_at=request.published_at,
            expires_at=request.expires_at,
        )
        for request in requests
    ]
    return SearchBuyerRequestsResponse(
        query=resolved_query,
        category=category,
        urgency=urgency,
        limit=safe_limit,
        page=safe_page,
        count=len(items),
        total=total,
        requests=items,
    ).model_dump(mode="json")


async def get_listing_detail(
    db: AsyncSession,
    *,
    listing_id: str | UUID | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    row = await _get_listing_row(db, listing_id=listing_id, slug=slug)
    detail = ListingDetailResponse(
        listing=ListingDetailPayload(
            listing_id=row["id"],
            slug=row.get("slug"),
            title=row["title"],
            description=row.get("description"),
            short_description=row.get("short_description"),
            category=row.get("category"),
            secondary_categories=row.get("secondary_categories"),
            tags=row.get("tags"),
            price=float(row.get("price") or 0.0),
            pricing_type=row.get("pricing_type"),
            subscription_price_monthly=row.get("subscription_price_monthly"),
            data_format=row.get("data_format"),
            update_frequency=row.get("update_frequency"),
            source_row_count=row.get("source_row_count"),
            source_column_count=row.get("source_column_count"),
            trust_level=row.get("trust_level"),
            privacy_score=float(row.get("privacy_score") or 0.0),
            searchability_score=float(row.get("searchability_score") or 0.0),
            raw_metadata=row.get("raw_metadata"),
            jsonld=mask_public_jsonld_urls(row.get("jsonld"), row),
            synthetic_queries=row.get("synthetic_queries"),
            published_at=row.get("published_at"),
            schema_info=row.get("schema_info"),
            trust_attestation=_extract_attestation_summary(row),
            schema_preview=_build_schema_preview(row),
        )
    )
    return sanitize_public_properties(
        detail.model_dump(mode="json"),
        extra_forbidden_properties={"compliance_status", "compliance_details"},
    )


async def evaluate_trust(
    db: AsyncSession,
    *,
    listing_id: str | UUID | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    row = await _get_listing_row(db, listing_id=listing_id, slug=slug)
    scan_findings = verification_public_projection(row)
    if isinstance(scan_findings, VerificationArtifactPublic):
        status = "published"
    elif isinstance(scan_findings, VerificationWithdrawalPublic):
        status = "withdrawn"
    else:
        status = "not_available"
    response = TrustEvaluationResponse(
        listing_id=row["id"],
        slug=row.get("slug"),
        status=status,
        scan_findings=scan_findings,
    )
    return response.model_dump(mode="json")


async def check_price(
    db: AsyncSession,
    *,
    listing_id: str | UUID | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    row = await _get_listing_row(db, listing_id=listing_id, slug=slug)
    response = PriceCheckResponse(
        listing_id=row["id"],
        slug=row.get("slug"),
        title=row["title"],
        price=float(row.get("price") or 0.0),
        pricing_type=row.get("pricing_type"),
        subscription_price_monthly=row.get("subscription_price_monthly"),
        availability="in_stock",
        fulfillment_method=_fulfillment_method(row),
        listing_type=row.get("listing_type"),
        published_at=row.get("published_at"),
    )
    return response.model_dump(mode="json")


async def _get_agent_transaction(
    db: AsyncSession,
    *,
    transaction_id: UUID,
    api_key_id: UUID,
) -> dict[str, Any]:
    result = await db.execute(
        text("SELECT * FROM transactions WHERE id = :id"),
        {"id": transaction_id},
    )
    row = result.mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx = dict(row)

    from app.services.agent_auth_service import AgentAuthService

    key_row = await AgentAuthService(db).get_api_key(api_key_id)
    if tx.get("buyer_type") != "agent":
        raise HTTPException(status_code=403, detail="Transaction is not agent-owned")
    if tx.get("party_id") and tx["party_id"] != key_row["org_id"]:
        raise HTTPException(status_code=403, detail="Cross-org access denied")
    return tx


async def initiate_purchase(
    db: AsyncSession,
    *,
    api_key_id: UUID,
    listing_id: UUID,
    idempotency_key: str,
) -> dict[str, Any]:
    from app.services.agent_auth_service import AgentAuthService
    from app.services.seller_setup_service import assert_seller_payout_ready
    from app.services.transaction_service import get_transaction_service

    auth_service = AgentAuthService(db)
    key_row = await auth_service.get_api_key(api_key_id)
    auth_service.require_scope(key_row, "purchase")

    tx_service = get_transaction_service(db)
    org_ctx = await auth_service.get_org_context(api_key_id)
    if not org_ctx.get("org_owner_user_id"):
        raise HTTPException(status_code=422, detail="Organization owner could not be resolved")

    listing = await tx_service._get_listing_for_agent(listing_id)
    if listing["status"] != "published":
        raise HTTPException(status_code=400, detail="Listing is not available for purchase")
    await assert_seller_payout_ready(db, listing["seller_id"])
    amount_cents = int(float(listing["price"]) * 100)
    try:
        existing = (
            await db.execute(
                text(
                    """
                    SELECT *
                    FROM transactions
                    WHERE api_key_id = :api_key_id
                      AND listing_id = :listing_id
                      AND idempotency_key = :idempotency_key
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "api_key_id": api_key_id,
                    "listing_id": listing_id,
                    "idempotency_key": idempotency_key,
                },
            )
        ).mappings().fetchone()
        if existing and existing["status"] in {"initiated", "agent_payment_pending", "paid"}:
            return dict(existing)

        await auth_service.check_spend_cap(api_key_id, amount_cents)
        await auth_service.increment_spend(api_key_id, amount_cents)
        tx = await tx_service.initiate_agent(
            listing_id=listing_id,
            buyer_id=org_ctx["org_owner_user_id"],
            api_key_id=api_key_id,
            idempotency_key=idempotency_key,
            commit=False,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    tx["status_note"] = "initiate_agent reserves spend and creates the transaction in 'initiated' status until checkout starts."
    return tx


async def checkout(
    db: AsyncSession,
    *,
    api_key_id: UUID,
    transaction_id: UUID,
) -> dict[str, Any]:
    from app.services.agent_auth_service import AgentAuthService
    from app.services.transaction_service import get_transaction_service

    auth_service = AgentAuthService(db)
    key_row = await auth_service.get_api_key(api_key_id)
    auth_service.require_scope(key_row, "purchase")
    await _get_agent_transaction(db, transaction_id=transaction_id, api_key_id=api_key_id)
    return await get_transaction_service(db).create_agent_checkout(transaction_id, api_key_id)


async def check_order_status(
    db: AsyncSession,
    *,
    api_key_id: UUID,
    transaction_id: UUID,
) -> dict[str, Any]:
    from app.services.agent_auth_service import AgentAuthService

    auth_service = AgentAuthService(db)
    key_row = await auth_service.get_api_key(api_key_id)
    auth_service.require_scope(key_row, "search")
    tx = await _get_agent_transaction(db, transaction_id=transaction_id, api_key_id=api_key_id)
    order_status = None
    if tx.get("order_id"):
        order_row = (
            await db.execute(
                text("SELECT status FROM orders WHERE id = :id"),
                {"id": tx["order_id"]},
            )
        ).mappings().fetchone()
        order_status = order_row["status"] if order_row else None
    return {
        "transaction_id": str(tx["id"]),
        "tx_number": tx["tx_number"],
        "status": tx["status"],
        "tx_status": tx["status"],
        "order_id": str(tx["order_id"]) if tx.get("order_id") else None,
        "order_status": order_status,
        "payment_intent_id": tx.get("stripe_payment_intent_id"),
    }
