"""
MCP Marketplace Tool Service (BQ-E2)
=====================================

Business logic backing the 7 Marketplace MCP tools.

Delegates to existing services (ListingService, ListingSearchService,
OrderService, allai_responder_service) — never duplicates logic.

Council mandates addressed:
  C1  Per-user aggregate rate limiting (200 req/min across all keys)
  C2  Prompt injection hardening (500 char cap on query_metadata)
  C3  Standardized JSON error contract {"error": {"code": …, "message": …}}
  C6  Input validation bounds
  C7  Agent polling mitigation (check_access 1/min per listing)
  C8  Idempotency key required on initiate_purchase

CREATED: 2026-02-24
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.seller_setup_service import get_seller_payout_readiness
from app.services.fee_calculator import split_platform_fee_cents
from app.services.mcp_middleware_service import (
    check_idempotency,
    hash_request_body,
    store_idempotency,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# C2: Maximum query length for query_metadata (prompt injection hardening)
QUERY_METADATA_MAX_CHARS = 500

# C6: Input validation bounds
SEARCH_QUERY_MAX_CHARS = 200
LIMIT_MAX = 50
LIMIT_DEFAULT = 10
OFFSET_MAX = 10_000
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{0,253}[a-z0-9]$")
PRICE_MAX = 1_000_000.0

# C7: Agent polling mitigation — check_access backoff
CHECK_ACCESS_COOLDOWN_SECONDS = 60

# Tool-level rate limits (purchases and allAI queries)
PURCHASE_RATE_LIMIT_PER_HOUR = 5
QUERY_METADATA_RATE_LIMIT_PER_HOUR = 20

# C1: Per-user aggregate rate limit
USER_AGGREGATE_RATE_LIMIT_PER_MIN = 200

# Valid trust levels and data formats for filtering
VALID_TRUST_LEVELS = {"L0", "L1", "L2", "L3"}
VALID_DATA_FORMATS = {
    "parquet", "csv", "json", "jsonl", "avro", "orc",
    "tsv", "xlsx", "xml", "sql",
}

# C2: Prompt injection blocklist patterns
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|above|all)\s+(instructions?|prompts?)",
    r"(?i)system\s*prompt",
    r"(?i)you\s+are\s+(now|a)",
    r"(?i)act\s+as\s+",
    r"(?i)disregard\s+",
    r"(?i)<\|.*\|>",
    r"(?i)\{\{.*\}\}",
]
INJECTION_RE = [re.compile(p) for p in INJECTION_PATTERNS]


# PII column heuristics (shared with mcp_marketplace.py)
PII_COLUMN_PATTERNS = {
    "email", "e_mail", "ssn", "social_security", "phone", "telephone",
    "first_name", "last_name", "full_name", "person_name", "customer_name",
    "user_name", "address", "street",
    "ip_address", "ip_addr", "credit_card", "card_number", "passport",
    "date_of_birth", "dob", "national_id", "driver_license",
}


# ---------------------------------------------------------------------------
# Error contract (C3)
# ---------------------------------------------------------------------------

class ToolError(Exception):
    """Structured tool error that maps to the standard JSON contract.

    Attributes:
        code:      Machine-readable error code (e.g. RATE_LIMIT_EXCEEDED)
        message:   Human-readable description
        retryable: Whether the client should retry
    """

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


def _error_json(code: str, message: str, *, retryable: bool = False) -> str:
    """Return the standardized error JSON string (C3)."""
    return json.dumps({
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        }
    }, ensure_ascii=False)


def _json(obj: Any) -> str:
    """Serialize to compact JSON string."""
    return json.dumps(obj, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Validation helpers (C6)
# ---------------------------------------------------------------------------

def _validate_search_params(
    query: str,
    limit: int,
    offset: int,
    min_price: Optional[float],
    max_price: Optional[float],
    min_privacy_score: Optional[float],
    min_quality_score: Optional[float],
    trust_level: Optional[str],
    data_format: Optional[str],
) -> Optional[str]:
    """Validate search parameters. Returns error message or None."""
    if not query or not query.strip():
        return "query is required and cannot be empty"
    if len(query) > SEARCH_QUERY_MAX_CHARS:
        return f"query must be <= {SEARCH_QUERY_MAX_CHARS} characters"
    if limit < 1 or limit > LIMIT_MAX:
        return f"limit must be between 1 and {LIMIT_MAX}"
    if offset < 0 or offset > OFFSET_MAX:
        return f"offset must be between 0 and {OFFSET_MAX}"
    if min_price is not None and (min_price < 0 or min_price > PRICE_MAX):
        return f"min_price must be between 0 and {PRICE_MAX}"
    if max_price is not None and (max_price < 0 or max_price > PRICE_MAX):
        return f"max_price must be between 0 and {PRICE_MAX}"
    if min_price is not None and max_price is not None and min_price > max_price:
        return "min_price cannot exceed max_price"
    if min_privacy_score is not None and (min_privacy_score < 0 or min_privacy_score > 10):
        return "min_privacy_score must be between 0 and 10"
    if min_quality_score is not None and (min_quality_score < 0 or min_quality_score > 100):
        return "min_quality_score must be between 0 and 100"
    if trust_level is not None and trust_level not in VALID_TRUST_LEVELS:
        return f"trust_level must be one of: {', '.join(sorted(VALID_TRUST_LEVELS))}"
    if data_format is not None and data_format.lower() not in VALID_DATA_FORMATS:
        return f"data_format must be one of: {', '.join(sorted(VALID_DATA_FORMATS))}"
    return None


def _resolve_listing_id(listing_id: str) -> Tuple[Optional[UUID], Optional[str]]:
    """Resolve listing_id as UUID or slug. Returns (uuid, slug)."""
    try:
        return UUID(listing_id), None
    except (ValueError, AttributeError):
        # Treat as slug
        if SLUG_PATTERN.match(listing_id):
            return None, listing_id
        return None, None


def _validate_query_metadata_input(query: str) -> Optional[str]:
    """C2: Validate query_metadata input for prompt injection.

    Returns error message or None.
    """
    if not query or not query.strip():
        return "query is required"
    if len(query) > QUERY_METADATA_MAX_CHARS:
        return f"query must be <= {QUERY_METADATA_MAX_CHARS} characters"
    for pattern in INJECTION_RE:
        if pattern.search(query):
            return "Query contains disallowed patterns"
    return None


# ---------------------------------------------------------------------------
# Rate limiting helpers (C1, C7, tool-level limits)
# ---------------------------------------------------------------------------

async def _check_user_rate_limit(user_id: str) -> bool:
    """C1: Per-user aggregate rate limit (200 req/min across all keys).

    Returns True if allowed, False if rate limited.
    """
    try:
        from app.services.redis_service import redis_service
        await redis_service.connect()

        rl_key = f"mcp_user_rl:{user_id}"
        now = time.time()
        window = 60

        pipe = redis_service.client.pipeline()
        pipe.zremrangebyscore(rl_key, 0, now - window)
        pipe.zadd(rl_key, {str(now): now})
        pipe.zcard(rl_key)
        pipe.expire(rl_key, window + 1)
        results = await pipe.execute()

        count = results[2]
        return count <= USER_AGGREGATE_RATE_LIMIT_PER_MIN
    except Exception as e:
        logger.warning("User rate limit check failed (allowing): %s", e)
        return True


async def _check_tool_rate_limit(key_hash: str, tool: str, limit: int, window: int = 3600) -> bool:
    """Tool-level rate limit (e.g. 5 purchases/hour, 20 queries/hour).

    Returns True if allowed.
    """
    try:
        from app.services.redis_service import redis_service
        await redis_service.connect()

        rl_key = f"mcp_tool_rl:{tool}:{key_hash}"
        now = time.time()

        pipe = redis_service.client.pipeline()
        pipe.zremrangebyscore(rl_key, 0, now - window)
        pipe.zadd(rl_key, {str(now): now})
        pipe.zcard(rl_key)
        pipe.expire(rl_key, window + 1)
        results = await pipe.execute()

        count = results[2]
        return count <= limit
    except Exception as e:
        logger.warning("Tool rate limit check failed (allowing): %s", e)
        return True


async def _check_access_cooldown(user_id: str, listing_id: str) -> bool:
    """C7: Agent polling mitigation — max 1 check_access per listing per minute.

    Returns True if allowed.
    """
    try:
        from app.services.redis_service import redis_service
        await redis_service.connect()

        cd_key = f"mcp_access_cd:{user_id}:{listing_id}"
        existing = await redis_service.get(cd_key)
        if existing:
            return False
        await redis_service.set(cd_key, "1", expire=CHECK_ACCESS_COOLDOWN_SECONDS)
        return True
    except Exception as e:
        logger.warning("Access cooldown check failed (allowing): %s", e)
        return True


# ---------------------------------------------------------------------------
# PII helpers
# ---------------------------------------------------------------------------

def _is_pii_column(col_name: str) -> bool:
    """Heuristic PII detection by column name."""
    normalized = col_name.lower().replace("-", "_").replace(" ", "_")
    return any(pattern in normalized for pattern in PII_COLUMN_PATTERNS)


def _cardinality_bucket(card: Any) -> str:
    """Convert cardinality to coarse bucket."""
    try:
        card = int(card)
    except (TypeError, ValueError):
        return "unknown"
    if card < 10:
        return "low (<10)"
    elif card < 100:
        return "medium (10-100)"
    elif card < 1000:
        return "high (100-1000)"
    return "very high (>1000)"


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def tool_search_datasets(
    query: str,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_privacy_score: Optional[float] = None,
    min_quality_score: Optional[float] = None,
    trust_level: Optional[str] = None,
    data_format: Optional[str] = None,
    limit: int = LIMIT_DEFAULT,
    offset: int = 0,
    *,
    user_id: str,
    key_hash: str,
) -> str:
    """Tool 1: Search the ai.market marketplace for datasets."""
    # C1: Per-user rate limit
    if not await _check_user_rate_limit(user_id):
        return _error_json("RATE_LIMIT_EXCEEDED", "Per-user rate limit exceeded (200/min)", retryable=True)

    # C6: Input validation
    err = _validate_search_params(
        query, limit, offset, min_price, max_price,
        min_privacy_score, min_quality_score, trust_level, data_format,
    )
    if err:
        return _error_json("VALIDATION_ERROR", err)

    async with AsyncSessionLocal() as db:
        try:
            from app.services.listing_search_service import ListingSearchService

            service = ListingSearchService(db)
            results = await service.search(
                query=query.strip(),
                category=category,
                min_price=min_price,
                max_price=max_price,
                min_privacy_score=min_privacy_score,
                limit=limit,
                offset=offset,
            )

            # Post-filter by trust_level, quality_score, data_format if provided
            items = results.get("results", [])
            if trust_level:
                items = [r for r in items if r.get("trust_level") == trust_level]
            if min_quality_score is not None:
                items = [r for r in items if (r.get("quality_score") or 0) >= min_quality_score]
            if data_format:
                items = [r for r in items if (r.get("data_format") or "").lower() == data_format.lower()]

            # Shape response
            shaped = []
            for r in items:
                shaped.append({
                    "id": str(r.get("id", "")),
                    "title": r.get("title"),
                    "slug": r.get("slug"),
                    "description": (r.get("short_description") or r.get("description", ""))[:200],
                    "category": r.get("category"),
                    "price": float(r["price"]) if r.get("price") is not None else None,
                    "pricing_type": r.get("pricing_type", "one_time"),
                    "data_format": r.get("data_format"),
                    "row_count": r.get("source_row_count"),
                    "column_count": r.get("source_column_count"),
                    "quality_score": r.get("quality_score"),
                    "privacy_score": float(r["privacy_score"]) if r.get("privacy_score") is not None else None,
                    "trust_level": r.get("trust_level"),
                    "verification_status": r.get("verification_status"),
                    "url": f"/api/v1/listings/{r.get('slug') or r.get('id')}",
                })

            filters_applied = {}
            if category:
                filters_applied["category"] = category
            if min_price is not None:
                filters_applied["min_price"] = min_price
            if max_price is not None:
                filters_applied["max_price"] = max_price
            if trust_level:
                filters_applied["trust_level"] = trust_level
            if data_format:
                filters_applied["data_format"] = data_format

            return _json({
                "results": shaped,
                "total": results.get("total", len(shaped)),
                "query": query.strip(),
                "filters_applied": filters_applied,
            })
        except Exception as e:
            logger.error("search_datasets failed: %s", e)
            return _error_json("SERVER_ERROR", "Search failed", retryable=True)


async def tool_get_dataset_details(
    listing_id: str,
    *,
    user_id: str,
    key_hash: str,
) -> str:
    """Tool 2: Get complete details for a dataset listing."""
    if not await _check_user_rate_limit(user_id):
        return _error_json("RATE_LIMIT_EXCEEDED", "Per-user rate limit exceeded (200/min)", retryable=True)

    uid, slug = _resolve_listing_id(listing_id)
    if uid is None and slug is None:
        return _error_json("VALIDATION_ERROR", "listing_id must be a valid UUID or slug")

    async with AsyncSessionLocal() as db:
        try:
            from app.services.seller_listing_public_presentation import (
                is_workspace_listing, approved_workspace_details, PublicPresentationUnavailable,
            )
            where = "id = :id" if uid else "slug = :slug"
            params = {'id': uid} if uid else {'slug': slug}
            workspace = (await db.execute(text(
                f"SELECT * FROM listings WHERE {where} AND status = 'published'"
            ), params)).mappings().fetchone()
            if workspace and is_workspace_listing(workspace):
                try:
                    return _json(await approved_workspace_details(db, workspace))
                except PublicPresentationUnavailable:
                    return _error_json("NOT_FOUND", "Listing not found")
            from app.services.listing_service import ListingService

            service = ListingService(db)
            listing = None

            if uid:
                listing = await service.get_by_id(uid)
            if not listing and slug:
                # Slug lookup
                result = await db.execute(
                    text("SELECT id FROM listings WHERE slug = :slug AND status = 'published' LIMIT 1"),
                    {"slug": slug},
                )
                row = result.mappings().fetchone()
                if row:
                    listing = await service.get_by_id(row["id"])

            if not listing:
                return _error_json("NOT_FOUND", "Listing not found")

            # Block unpublished/suspended from search (C5/MP-M6)
            if listing.get("status") not in ("published",):
                return _error_json("NOT_FOUND", "Listing not found")

            # Shape seller info (safe fields only)
            seller_info = None
            seller_result = await db.execute(
                text("""
                    SELECT id, full_name, verification_status
                    FROM users WHERE id = :sid
                """),
                {"sid": listing.get("seller_id")},
            )
            seller_row = seller_result.mappings().fetchone()
            if seller_row:
                seller_info = {
                    "id": str(seller_row["id"]),
                    "display_name": seller_row.get("full_name") or "Anonymous Seller",
                    "verification_status": seller_row.get("verification_status") or "unverified",
                }

            return _json({
                "id": str(listing.get("id", "")),
                "title": listing.get("title"),
                "slug": listing.get("slug"),
                "description": listing.get("description"),
                "short_description": listing.get("short_description"),
                "category": listing.get("category"),
                "secondary_categories": listing.get("secondary_categories"),
                "tags": listing.get("tags"),
                "price": float(listing["price"]) if listing.get("price") is not None else None,
                "pricing_type": listing.get("pricing_type", "one_time"),
                "subscription_price_monthly": listing.get("subscription_price_monthly"),
                "data_format": listing.get("data_format"),
                "update_frequency": listing.get("update_frequency"),
                "row_count": listing.get("source_row_count"),
                "column_count": listing.get("source_column_count"),
                "quality_score": listing.get("quality_score"),
                "privacy_score": float(listing["privacy_score"]) if listing.get("privacy_score") is not None else None,
                "trust_level": listing.get("trust_level"),
                "verification_status": listing.get("verification_status"),
                "compliance_status": listing.get("compliance_status"),
                "seller": seller_info,
                "stats": {
                    "view_count": listing.get("view_count", 0),
                    "purchase_count": listing.get("purchase_count", 0),
                    "inquiry_count": listing.get("inquiry_count", 0),
                },
                "published_at": listing.get("published_at"),
                "updated_at": listing.get("updated_at"),
            })
        except Exception as e:
            logger.error("get_dataset_details failed: %s", e)
            return _error_json("SERVER_ERROR", "Failed to retrieve listing", retryable=True)


async def tool_get_dataset_schema(
    listing_id: str,
    *,
    user_id: str,
    key_hash: str,
) -> str:
    """Tool 3: Get the schema (column definitions) for a dataset."""
    if not await _check_user_rate_limit(user_id):
        return _error_json("RATE_LIMIT_EXCEEDED", "Per-user rate limit exceeded (200/min)", retryable=True)

    uid, slug = _resolve_listing_id(listing_id)
    if uid is None and slug is None:
        return _error_json("VALIDATION_ERROR", "listing_id must be a valid UUID or slug")

    async with AsyncSessionLocal() as db:
        try:
            where_clause = "l.id = :id" if uid else "l.slug = :slug"
            param = {"id": uid} if uid else {"slug": slug}

            result = await db.execute(
                text(f"""
                    SELECT l.id, l.title, l.schema_info, l.data_format,
                           l.source_row_count, l.source_column_count, l.source_delivery
                    FROM listings l
                    WHERE {where_clause} AND l.status = 'published'
                """),
                param,
            )
            row = result.mappings().fetchone()
            if not row:
                return _error_json("NOT_FOUND", "Listing not found")

            from app.services.seller_listing_public_presentation import is_workspace_listing
            if is_workspace_listing(row):
                return _error_json("workspace_schema_unsupported", "No approved public schema is available.")

            schema_info = row["schema_info"]
            if isinstance(schema_info, str):
                try:
                    schema_info = json.loads(schema_info)
                except (json.JSONDecodeError, TypeError):
                    schema_info = {}

            if not schema_info:
                return _json({
                    "listing_id": str(row["id"]),
                    "title": row["title"],
                    "data_format": row["data_format"],
                    "row_count": row["source_row_count"],
                    "column_count": row["source_column_count"],
                    "columns": [],
                    "note": "No schema information available for this listing.",
                })

            columns = schema_info.get("columns", schema_info.get("fields", []))
            shaped_columns = []
            if isinstance(columns, list):
                for col in columns:
                    shaped_columns.append({
                        "name": col.get("name"),
                        "type": col.get("type", "unknown"),
                        "description": col.get("description"),
                        "nullable": col.get("nullable"),
                    })

            return _json({
                "listing_id": str(row["id"]),
                "title": row["title"],
                "data_format": row["data_format"],
                "row_count": row["source_row_count"] or schema_info.get("row_count"),
                "column_count": row["source_column_count"] or len(shaped_columns),
                "columns": shaped_columns,
                "primary_key": schema_info.get("primary_key"),
                "note": "ai.market is non-custodial. Schema describes the dataset structure; raw data is delivered by the seller after purchase.",
            })
        except Exception as e:
            logger.error("get_dataset_schema failed: %s", e)
            return _error_json("SERVER_ERROR", "Failed to retrieve schema", retryable=True)


async def tool_preview_dataset(
    listing_id: str,
    *,
    user_id: str,
    key_hash: str,
) -> str:
    """Tool 4: Get a PII-safe structural preview of a dataset."""
    if not await _check_user_rate_limit(user_id):
        return _error_json("RATE_LIMIT_EXCEEDED", "Per-user rate limit exceeded (200/min)", retryable=True)

    uid, slug = _resolve_listing_id(listing_id)
    if uid is None and slug is None:
        return _error_json("VALIDATION_ERROR", "listing_id must be a valid UUID or slug")

    async with AsyncSessionLocal() as db:
        try:
            where_clause = "l.id = :id" if uid else "l.slug = :slug"
            param = {"id": uid} if uid else {"slug": slug}

            result = await db.execute(
                text(f"""
                    SELECT l.id, l.title, l.schema_info, l.privacy_score,
                           l.quality_score, l.source_row_count, l.source_delivery
                    FROM listings l
                    WHERE {where_clause} AND l.status = 'published'
                """),
                param,
            )
            row = result.mappings().fetchone()
            if not row:
                return _error_json("NOT_FOUND", "Listing not found")

            from app.services.seller_listing_public_presentation import is_workspace_listing
            if is_workspace_listing(row):
                return _error_json("workspace_preview_unsupported", "This listing has no public sample.")

            schema_info = row["schema_info"]
            if isinstance(schema_info, str):
                try:
                    schema_info = json.loads(schema_info)
                except (json.JSONDecodeError, TypeError):
                    schema_info = {}

            if not schema_info:
                return _json({
                    "listing_id": str(row["id"]),
                    "title": row["title"],
                    "columns": [],
                    "row_count": row["source_row_count"],
                    "quality_indicators": {
                        "privacy_score": float(row["privacy_score"]) if row["privacy_score"] else None,
                        "quality_score": row["quality_score"],
                    },
                })

            columns = schema_info.get("columns", schema_info.get("fields", []))
            redacted = []
            if isinstance(columns, list):
                for col in columns:
                    col_name = col.get("name", "")
                    is_pii = col.get("pii_flagged", False) or _is_pii_column(col_name)

                    if is_pii:
                        # R5: Suppress samples for identifier columns
                        redacted.append({
                            "name": col_name,
                            "type": col.get("type", "unknown"),
                            "pii_flag": True,
                            "pii_reason": "PII detected — statistics suppressed for privacy",
                            "cardinality": _cardinality_bucket(col.get("cardinality", 0)),
                            "null_pct": col.get("null_pct", 0),
                            "note": "PII detected — statistics suppressed for privacy",
                        })
                    else:
                        # Safe column — apply k-anonymity on top_values
                        top_values = col.get("top_values", col.get("sample_values", []))
                        if isinstance(top_values, list):
                            if all(isinstance(v, dict) for v in top_values):
                                safe = [v for v in top_values if v.get("count", 5) >= 5]
                                suppressed = len(top_values) - len(safe)
                                if suppressed > 0:
                                    safe.append({"value": "other", "count": None})
                                top_values = safe
                            else:
                                # Plain list of sample values — limit to 5
                                top_values = top_values[:5]

                        redacted.append({
                            "name": col_name,
                            "type": col.get("type", "unknown"),
                            "pii_flag": False,
                            "cardinality": col.get("cardinality"),
                            "null_pct": col.get("null_pct", 0),
                            "sample_values": top_values,
                        })

            completeness = schema_info.get("completeness")
            if completeness is None:
                # Estimate from null percentages
                null_pcts = [c.get("null_pct", 0) for c in columns if isinstance(c, dict)]
                if null_pcts:
                    avg_null = sum(float(p) for p in null_pcts) / len(null_pcts)
                    completeness = round(1.0 - (avg_null / 100.0), 2)

            return _json({
                "listing_id": str(row["id"]),
                "title": row["title"],
                "columns": redacted,
                "row_count": row["source_row_count"] or schema_info.get("row_count"),
                "quality_indicators": {
                    "completeness": completeness,
                    "privacy_score": float(row["privacy_score"]) if row["privacy_score"] else None,
                    "quality_score": row["quality_score"],
                },
            })
        except Exception as e:
            logger.error("preview_dataset failed: %s", e)
            return _error_json("SERVER_ERROR", "Failed to retrieve preview", retryable=True)


async def tool_initiate_purchase(
    listing_id: str,
    idempotency_key: str,
    *,
    user_id: str,
    key_hash: str,
    api_key_id: str,
) -> str:
    """Tool 5: Start the purchase flow for a dataset listing.

    C8: idempotency_key is required (not optional).
    """
    if not await _check_user_rate_limit(user_id):
        return _error_json("RATE_LIMIT_EXCEEDED", "Per-user rate limit exceeded (200/min)", retryable=True)

    # C8: Validate idempotency key
    if not idempotency_key or not idempotency_key.strip():
        return _error_json("VALIDATION_ERROR", "idempotency_key is required. Generate a UUIDv4 for each unique purchase intent.")

    # Tool-level rate limit: 5 purchases/hour
    if not await _check_tool_rate_limit(key_hash, "initiate_purchase", PURCHASE_RATE_LIMIT_PER_HOUR):
        return _error_json("RATE_LIMIT_EXCEEDED", "Purchase rate limit exceeded (5/hour)", retryable=True)

    uid, slug = _resolve_listing_id(listing_id)
    if uid is None and slug is None:
        return _error_json("VALIDATION_ERROR", "listing_id must be a valid UUID or slug")

    async with AsyncSessionLocal() as db:
        try:
            # Idempotency check
            req_body = json.dumps({"listing_id": listing_id}, sort_keys=True).encode()
            req_hash = hash_request_body(req_body)
            cached = await check_idempotency(
                db=db,
                idempotency_key=idempotency_key,
                api_key_id=UUID(api_key_id),
                endpoint="mcp:initiate_purchase",
                request_hash=req_hash,
            )
            if cached:
                if cached.get("conflict"):
                    return _error_json(
                        "IDEMPOTENCY_CONFLICT",
                        "Same idempotency key used with different listing_id",
                    )
                if cached.get("cached_response"):
                    return json.dumps(cached["body"]) if isinstance(cached["body"], dict) else str(cached["body"])

            # Resolve listing
            if uid:
                where_clause = "l.id = :id"
                param: Dict[str, Any] = {"id": uid}
            else:
                where_clause = "l.slug = :slug"
                param = {"slug": slug}

            result = await db.execute(
                text(f"""
                    SELECT l.id, l.title, l.slug, l.price, l.seller_id, l.status
                    FROM listings l
                    WHERE {where_clause} AND l.status = 'published'
                """),
                param,
            )
            listing = result.mappings().fetchone()
            if not listing:
                return _error_json("NOT_FOUND", "Listing not found")

            listing = dict(listing)

            # Owner check
            if str(listing["seller_id"]) == user_id:
                return _error_json("VALIDATION_ERROR", "Cannot purchase your own listing")

            readiness = await get_seller_payout_readiness(db, listing["seller_id"])
            if not readiness.purchasable:
                return _error_json(
                    "SELLER_SETUP_INCOMPLETE",
                    "Seller is completing setup; this listing is not available for purchase yet.",
                )

            # Check for existing active order
            active_order = await db.execute(
                text("""
                    SELECT id FROM orders
                    WHERE buyer_id = :buyer AND listing_id = :listing
                    AND status NOT IN ('cancelled', 'refunded', 'completed')
                    LIMIT 1
                """),
                {"buyer": user_id, "listing": listing["id"]},
            )
            if active_order.mappings().fetchone():
                return _error_json("VALIDATION_ERROR", "Active order already exists for this listing")

            # Calculate amounts
            amount_cents = int(float(listing["price"]) * 100)
            _platform_fee_cents, _seller_amount_cents = split_platform_fee_cents(amount_cents)

            # Create order
            from app.services.order_service import get_order_service

            order_service = get_order_service(db)
            snapshot = {
                "id": str(listing["id"]),
                "title": listing.get("title"),
                "price": float(listing["price"]),
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }

            order = await order_service.create_order(
                buyer_id=UUID(user_id),
                seller_id=listing["seller_id"],
                listing_id=listing["id"],
                amount_cents=amount_cents,
                listing_snapshot=snapshot,
            )

            # Create Stripe checkout session
            import stripe
            from app.core.config import settings
            from app.core.stripe_async import run_stripe

            success_url = f"{settings.FRONTEND_URL}/orders/{order['id']}/success?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{settings.FRONTEND_URL}/listings/{listing.get('slug', listing['id'])}"

            checkout_session = await run_stripe(
                stripe.checkout.Session.create,
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": listing.get("title", "Dataset"),
                            "metadata": {"listing_id": str(listing["id"])},
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "order_id": str(order["id"]),
                    "listing_id": str(listing["id"]),
                    "buyer_id": user_id,
                    "mcp_initiated": "true",
                },
            )

            # Update order with Stripe session
            await db.execute(
                text("UPDATE orders SET stripe_checkout_session_id = :sid WHERE id = :oid"),
                {"sid": checkout_session.id, "oid": order["id"]},
            )
            await db.commit()

            response_data = {
                "order_id": str(order["id"]),
                "order_number": order.get("order_number"),
                "checkout_url": checkout_session.url,
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
                "listing": {
                    "id": str(listing["id"]),
                    "title": listing.get("title"),
                    "price": float(listing["price"]),
                },
                "note": "Complete payment at the checkout URL. Session expires in 30 minutes.",
            }

            # Store idempotency
            await store_idempotency(
                db=db,
                idempotency_key=idempotency_key,
                api_key_id=UUID(api_key_id),
                endpoint="mcp:initiate_purchase",
                request_hash=req_hash,
                response_status=200,
                response_body=response_data,
            )

            return _json(response_data)
        except Exception as e:
            logger.error("initiate_purchase failed: %s", e)
            return _error_json("SERVER_ERROR", "Purchase initiation failed", retryable=True)


async def tool_check_access(
    listing_id: str,
    *,
    user_id: str,
    key_hash: str,
) -> str:
    """Tool 6: Check if the authenticated user has purchased access to a dataset.

    C5: Requires orders:read scope (confirmed — read-only check).
    C7: Rate limited to 1 check per listing per minute.
    """
    if not await _check_user_rate_limit(user_id):
        return _error_json("RATE_LIMIT_EXCEEDED", "Per-user rate limit exceeded (200/min)", retryable=True)

    uid, slug = _resolve_listing_id(listing_id)
    if uid is None and slug is None:
        return _error_json("VALIDATION_ERROR", "listing_id must be a valid UUID or slug")

    resolved_id = str(uid) if uid else listing_id

    # C7: Per-listing cooldown
    if not await _check_access_cooldown(user_id, resolved_id):
        return _error_json(
            "RATE_LIMIT_EXCEEDED",
            "check_access is limited to 1 request per listing per minute. "
            "Please wait before checking again.",
            retryable=True,
        )

    async with AsyncSessionLocal() as db:
        try:
            # Resolve slug to UUID
            actual_uid = uid
            if not actual_uid and slug:
                slug_result = await db.execute(
                    text("SELECT id, title FROM listings WHERE slug = :slug LIMIT 1"),
                    {"slug": slug},
                )
                slug_row = slug_result.mappings().fetchone()
                if slug_row:
                    actual_uid = slug_row["id"]

            if not actual_uid:
                return _error_json("NOT_FOUND", "Listing not found")

            # Get listing title
            listing_result = await db.execute(
                text("SELECT id, title FROM listings WHERE id = :id"),
                {"id": actual_uid},
            )
            listing_row = listing_result.mappings().fetchone()
            listing_title = listing_row["title"] if listing_row else "Unknown"

            # Check for completed/delivered/in_escrow orders (owner-bound)
            order_result = await db.execute(
                text("""
                    SELECT id, order_number, status, created_at,
                           escrow_released_at, delivered_at, completed_at, confirmed_at,
                           transaction_id, buyer_id, listing_id, revoked, purchased_version_id,
                           access_expires_at, downloads_used, max_downloads
                    FROM orders
                    WHERE buyer_id = :buyer_id
                      AND listing_id = :listing_id
                      AND status IN ('paid', 'in_escrow', 'pending_delivery',
                                     'delivered', 'completed', 'partially_refunded')
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"buyer_id": user_id, "listing_id": actual_uid},
            )
            order_row = order_result.mappings().fetchone()

            if order_row and order_row["status"] == "partially_refunded":
                from app.services.order_service import OrderService
                if not await OrderService(db)._partial_access_available(dict(order_row)):
                    order_row = None
            if order_row:
                return _json({
                    "has_access": True,
                    "listing_id": str(actual_uid),
                    "listing_title": listing_title,
                    "order": {
                        "id": str(order_row["id"]),
                        "order_number": order_row["order_number"],
                        "status": order_row["status"],
                        "purchased_at": order_row["created_at"],
                        "escrow_released_at": order_row.get("escrow_released_at"),
                    },
                })
            else:
                return _json({
                    "has_access": False,
                    "listing_id": str(actual_uid),
                    "listing_title": listing_title,
                    "purchase_url": "Use the initiate_purchase tool to start the purchase flow.",
                })
        except Exception as e:
            logger.error("check_access failed: %s", e)
            return _error_json("SERVER_ERROR", "Access check failed", retryable=True)


async def tool_query_metadata(
    query: str,
    listing_id: Optional[str] = None,
    include_schema: bool = True,
    include_similar: bool = False,
    *,
    user_id: str,
    key_hash: str,
) -> str:
    """Tool 7: Ask a natural language question about dataset metadata.

    C2: Prompt injection hardened (500 char cap, blocklist patterns).
    Uses allAI (RAG + vector search) to answer.
    """
    if not await _check_user_rate_limit(user_id):
        return _error_json("RATE_LIMIT_EXCEEDED", "Per-user rate limit exceeded (200/min)", retryable=True)

    # C2: Input validation + injection hardening
    err = _validate_query_metadata_input(query)
    if err:
        return _error_json("VALIDATION_ERROR", err)

    # Tool-level rate limit
    if not await _check_tool_rate_limit(key_hash, "query_metadata", QUERY_METADATA_RATE_LIMIT_PER_HOUR):
        return _error_json("RATE_LIMIT_EXCEEDED", "query_metadata rate limit exceeded (20/hour)", retryable=True)

    async with AsyncSessionLocal() as db:
        try:
            listing_context = None
            listing_title = None
            resolved_uid = None

            # If scoped to specific listing, fetch its metadata
            if listing_id:
                uid, slug = _resolve_listing_id(listing_id)
                if uid is None and slug is None:
                    return _error_json("VALIDATION_ERROR", "listing_id must be a valid UUID or slug")

                where = "l.id = :id" if uid else "l.slug = :slug"
                param = {"id": uid} if uid else {"slug": slug}

                result = await db.execute(
                    text(f"""
                        SELECT l.id, l.title, l.description, l.short_description,
                               l.category, l.tags, l.schema_info, l.data_format,
                               l.source_row_count, l.source_column_count,
                               l.privacy_score, l.quality_score, l.trust_level,
                               l.compliance_status, l.update_frequency
                        FROM listings l
                        WHERE {where} AND l.status = 'published'
                    """),
                    param,
                )
                row = result.mappings().fetchone()
                if row:
                    listing_context = dict(row)
                    listing_title = row["title"]
                    resolved_uid = str(row["id"])

                    # Parse schema_info
                    si = listing_context.get("schema_info")
                    if isinstance(si, str):
                        try:
                            listing_context["schema_info"] = json.loads(si)
                        except (json.JSONDecodeError, TypeError):
                            listing_context["schema_info"] = {}
                else:
                    return _error_json("NOT_FOUND", "Listing not found")

            # Build context for allAI
            try:
                from app.services.allai_responder_service import get_allai_responder

                responder = get_allai_responder()

                # C2: System prompt restriction — metadata only
                metadata_context = listing_context or {}

                auto_result = await responder.try_auto_answer(
                    buyer_question=query.strip(),
                    listing_metadata=metadata_context,
                )

                sources = []
                if resolved_uid:
                    sources.append({
                        "listing_id": resolved_uid,
                        "title": listing_title,
                        "relevance": auto_result.confidence if hasattr(auto_result, "confidence") else None,
                    })

                context_used = []
                if include_schema and listing_context and listing_context.get("schema_info"):
                    context_used.append("schema_info")
                if listing_context:
                    context_used.append("quality_metrics")
                    context_used.append("listing_metadata")

                return _json({
                    "answer": auto_result.response,
                    "sources": sources,
                    "context_used": context_used,
                    "note": "Answer based on metadata only. ai.market does not store raw data.",
                })
            except Exception as e:
                logger.error("allAI query failed: %s", e)
                # Fallback: return metadata summary without LLM
                if listing_context:
                    return _json({
                        "answer": f"I couldn't process the query via allAI, but here's the metadata for '{listing_title}': "
                                  f"Category: {listing_context.get('category')}, "
                                  f"Format: {listing_context.get('data_format')}, "
                                  f"Rows: {listing_context.get('source_row_count')}, "
                                  f"Quality: {listing_context.get('quality_score')}, "
                                  f"Privacy: {listing_context.get('privacy_score')}.",
                        "sources": [{"listing_id": resolved_uid, "title": listing_title}] if resolved_uid else [],
                        "context_used": ["listing_metadata"],
                        "note": "Fallback response — allAI unavailable. Metadata summary provided.",
                    })
                return _error_json("SERVER_ERROR", "Metadata query failed", retryable=True)

        except Exception as e:
            logger.error("query_metadata failed: %s", e)
            return _error_json("SERVER_ERROR", "Metadata query failed", retryable=True)
