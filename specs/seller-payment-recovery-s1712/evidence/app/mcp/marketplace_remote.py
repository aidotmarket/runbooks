"""Remote Marketplace MCP Server — Streamable HTTP transport for AI agents.

Exposes 7 marketplace tools via the MCP protocol so any MCP-compatible agent
(Claude, GPT, Gemini, etc.) can discover, evaluate, and purchase datasets
on ai.market.

Auth: MCP API keys (aim_* Bearer tokens) via marketplace_auth.py
Mount: /mcp/marketplace/ in main.py
Transport: Streamable HTTP (FastMCP default)

Council mandates addressed:
  C1  Per-user aggregate rate limiting (in tool service)
  C2  Prompt injection hardening (500 char cap on query_metadata)
  C3  Standardized JSON error contract
  C5  check_access uses orders:read (confirmed)
  C6  Input validation bounds (in tool service)
  C7  Agent polling mitigation (check_access 1/min per listing)
  C8  idempotency_key required on initiate_purchase

CREATED: 2026-02-24  (BQ-E2)
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    "ai.market Marketplace",
    instructions=(
        "Marketplace tools for ai.market — discover, evaluate, and purchase "
        "datasets. Use search_datasets to find data, get_dataset_details for "
        "full info, get_dataset_schema for column definitions, preview_dataset "
        "for PII-safe previews, initiate_purchase to buy (returns Stripe URL "
        "for human payment), check_access to verify purchase status, and "
        "query_metadata for natural language questions about dataset metadata. "
        "ai.market is non-custodial: raw data is never stored on the platform."
    ),
    stateless_http=True,
)


# ---------------------------------------------------------------------------
# Auth context helper
# ---------------------------------------------------------------------------

def _get_auth_context(ctx) -> dict:
    """Extract auth context from the MCP request context.

    The marketplace_auth.py middleware stores auth info in scope['state'].
    FastMCP passes the request context through ctx.
    """
    try:
        # FastMCP stores the request in the context
        request = ctx.request if hasattr(ctx, "request") else None
        if request:
            state = getattr(request, "state", None)
            if state:
                return getattr(state, "mcp_marketplace_auth", {})
            # Try scope-level state
            scope = getattr(request, "scope", {})
            return scope.get("state", {}).get("mcp_marketplace_auth", {})
    except Exception:
        pass
    return {}


def _require_scope(auth: dict, scope: str) -> Optional[str]:
    """Check if auth context has required scope. Returns error JSON or None."""
    scopes = auth.get("scopes", [])
    if scope not in scopes:
        return json.dumps({
            "error": {
                "code": "INSUFFICIENT_SCOPE",
                "message": f"API key lacks required scope: {scope}",
                "retryable": False,
            }
        })
    return None


def _auth_kwargs(auth: dict) -> dict:
    """Extract kwargs needed by tool service functions."""
    return {
        "user_id": auth.get("user_id", ""),
        "key_hash": auth.get("key_hash", ""),
    }


def _no_auth_error() -> str:
    """Return error when auth context is missing."""
    return json.dumps({
        "error": {
            "code": "AUTH_REQUIRED",
            "message": "Authentication required. Provide Authorization: Bearer aim_<key> header.",
            "retryable": False,
        }
    })


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp_server.tool()
async def search_datasets(
    ctx,
    query: str,
    category: str = "",
    min_price: float = -1,
    max_price: float = -1,
    min_privacy_score: float = -1,
    min_quality_score: float = -1,
    trust_level: str = "",
    data_format: str = "",
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Search the ai.market marketplace for datasets.

    Performs hybrid semantic + keyword search across all published listings.
    Returns ranked results with title, price, category, quality scores, and URLs.

    Args:
        query: Search query (semantic + keyword). Required.
        category: Filter by category slug.
        min_price: Minimum price in USD (omit or -1 to skip).
        max_price: Maximum price in USD (omit or -1 to skip).
        min_privacy_score: Minimum privacy score 0-10 (omit or -1 to skip).
        min_quality_score: Minimum quality score 0-100 (omit or -1 to skip).
        trust_level: Filter by trust level: L0, L1, L2, or L3.
        data_format: Filter by format: parquet, csv, json, etc.
        limit: Results per page, 1-50 (default 10).
        offset: Pagination offset, 0-10000 (default 0).
    """
    auth = _get_auth_context(ctx)
    if not auth.get("user_id"):
        return _no_auth_error()
    scope_err = _require_scope(auth, "listings:read")
    if scope_err:
        return scope_err

    from app.services.mcp_marketplace_tools import tool_search_datasets

    return await tool_search_datasets(
        query=query,
        category=category or None,
        min_price=min_price if min_price >= 0 else None,
        max_price=max_price if max_price >= 0 else None,
        min_privacy_score=min_privacy_score if min_privacy_score >= 0 else None,
        min_quality_score=min_quality_score if min_quality_score >= 0 else None,
        trust_level=trust_level or None,
        data_format=data_format or None,
        limit=limit,
        offset=offset,
        **_auth_kwargs(auth),
    )


@mcp_server.tool()
async def get_dataset_details(
    ctx,
    listing_id: str,
) -> str:
    """Get complete details for a dataset listing.

    Returns full description, pricing, seller info, quality metrics,
    trust scores, compliance status, update frequency, and tags.

    Args:
        listing_id: UUID or slug of the listing.
    """
    auth = _get_auth_context(ctx)
    if not auth.get("user_id"):
        return _no_auth_error()
    scope_err = _require_scope(auth, "listings:read")
    if scope_err:
        return scope_err

    from app.services.mcp_marketplace_tools import tool_get_dataset_details

    return await tool_get_dataset_details(listing_id=listing_id, **_auth_kwargs(auth))


@mcp_server.tool()
async def get_dataset_schema(
    ctx,
    listing_id: str,
) -> str:
    """Get the schema (column definitions) for a dataset.

    Returns column names, data types, descriptions, and aggregate statistics.
    No raw data rows are included (ai.market is non-custodial).

    Args:
        listing_id: UUID or slug of the listing.
    """
    auth = _get_auth_context(ctx)
    if not auth.get("user_id"):
        return _no_auth_error()
    scope_err = _require_scope(auth, "listings:read")
    if scope_err:
        return scope_err

    from app.services.mcp_marketplace_tools import tool_get_dataset_schema

    return await tool_get_dataset_schema(listing_id=listing_id, **_auth_kwargs(auth))


@mcp_server.tool()
async def preview_dataset(
    ctx,
    listing_id: str,
) -> str:
    """Get a PII-safe structural preview of a dataset.

    Returns column-level statistics (cardinality, null %, value distributions)
    with PII-sensitive columns redacted. No raw data rows are shown.

    Args:
        listing_id: UUID or slug of the listing.
    """
    auth = _get_auth_context(ctx)
    if not auth.get("user_id"):
        return _no_auth_error()
    scope_err = _require_scope(auth, "listings:read")
    if scope_err:
        return scope_err

    from app.services.mcp_marketplace_tools import tool_preview_dataset

    return await tool_preview_dataset(listing_id=listing_id, **_auth_kwargs(auth))


@mcp_server.tool()
async def initiate_purchase(
    ctx,
    listing_id: str,
    idempotency_key: str,
) -> str:
    """Start the purchase flow for a dataset listing.

    Returns a Stripe checkout URL. The human user must complete payment
    in their browser — ai.market does not store payment credentials.

    The checkout session expires in 30 minutes. After successful payment,
    the order enters a 48-hour escrow period for buyer inspection.

    IMPORTANT: idempotency_key is REQUIRED. Generate a UUIDv4 for each
    unique purchase intent to prevent duplicate charges.

    Args:
        listing_id: UUID or slug of the listing to purchase.
        idempotency_key: UUIDv4 for idempotent deduplication (required).
    """
    auth = _get_auth_context(ctx)
    if not auth.get("user_id"):
        return _no_auth_error()
    scope_err = _require_scope(auth, "orders:write")
    if scope_err:
        return scope_err

    from app.services.mcp_marketplace_tools import tool_initiate_purchase

    return await tool_initiate_purchase(
        listing_id=listing_id,
        idempotency_key=idempotency_key,
        user_id=auth.get("user_id", ""),
        key_hash=auth.get("key_hash", ""),
        api_key_id=auth.get("api_key_id", ""),
    )


@mcp_server.tool()
async def check_access(
    ctx,
    listing_id: str,
) -> str:
    """Check if you have purchased access to a dataset.

    Returns the order status and access details if a purchase exists.
    Useful to verify access before attempting to use a dataset.

    NOTE: This tool is rate-limited to 1 request per listing per minute
    to prevent polling loops. After calling initiate_purchase, wait for
    the human to complete payment before checking access.

    Args:
        listing_id: UUID or slug of the listing to check.
    """
    auth = _get_auth_context(ctx)
    if not auth.get("user_id"):
        return _no_auth_error()
    scope_err = _require_scope(auth, "orders:read")
    if scope_err:
        return scope_err

    from app.services.mcp_marketplace_tools import tool_check_access

    return await tool_check_access(listing_id=listing_id, **_auth_kwargs(auth))


@mcp_server.tool()
async def query_metadata(
    ctx,
    query: str,
    listing_id: str = "",
    include_schema: bool = True,
    include_similar: bool = False,
) -> str:
    """Ask a natural language question about dataset metadata.

    Uses allAI (RAG + vector search) to answer questions about dataset
    characteristics, schema details, quality metrics, compliance info,
    and comparisons between listings. Does not access raw data.

    Query is limited to 500 characters. Examples:
    - "What columns contain financial data?"
    - "Compare privacy scores across healthcare datasets"
    - "Which datasets update daily and cost under $100?"
    - "Is this dataset GDPR compliant?"

    Args:
        query: Natural language question (max 500 chars).
        listing_id: Optional UUID or slug to scope to a specific listing.
        include_schema: Include schema info in context (default true).
        include_similar: Include similar listings in results (default false).
    """
    auth = _get_auth_context(ctx)
    if not auth.get("user_id"):
        return _no_auth_error()
    scope_err = _require_scope(auth, "datasets:query")
    if scope_err:
        return scope_err

    from app.services.mcp_marketplace_tools import tool_query_metadata

    return await tool_query_metadata(
        query=query,
        listing_id=listing_id or None,
        include_schema=include_schema,
        include_similar=include_similar,
        **_auth_kwargs(auth),
    )
