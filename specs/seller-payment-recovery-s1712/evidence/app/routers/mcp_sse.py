"""
Public agent-facing MCP SSE and JSON-RPC tool-call endpoints.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Awaitable, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.request_ip import resolve_client_ip
from app.middleware.rate_limiter import RateLimitDecision, check_rate_limit
from app.services.mcp_tools import (
    check_price,
    evaluate_trust,
    get_listing_detail,
    search_buyer_requests,
    search_listings,
)

logger = logging.getLogger(__name__)
router = APIRouter()

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-03-26"
PUBLIC_SEARCH_LIMIT_MAX = 25
SSE_HEARTBEAT_SECONDS = 15


PUBLIC_TOOL_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "search_listings",
        "description": "Search published ai.market listings by query, category, and price range.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text search query."},
                "keyword": {"type": "string", "description": "Alias for query."},
                "category": {"type": "string", "description": "Optional category filter."},
                "price_min": {"type": "number", "description": "Minimum price filter."},
                "price_max": {"type": "number", "description": "Maximum price filter."},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": PUBLIC_SEARCH_LIMIT_MAX},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_buyer_requests",
        "description": "Search public buyer requirements on ai.market by query, category, and urgency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text search query."},
                "category": {"type": "string", "description": "Optional category filter."},
                "urgency": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Optional buyer urgency filter.",
                },
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": PUBLIC_SEARCH_LIMIT_MAX},
                "page": {"type": "integer", "default": 1, "minimum": 1},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_listing_detail",
        "description": "Get full public metadata, trust attestation summary, and schema preview for a listing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "string", "description": "Listing UUID."},
                "slug": {"type": "string", "description": "Listing slug."},
            },
            'anyOf': [{"required": ["listing_id"]}, {"required": ["slug"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "evaluate_trust",
        "description": "Return the seller-published, point-in-time scan findings for a listing; this is not a composite trust judgment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "string", "description": "Listing UUID."},
                "slug": {"type": "string", "description": "Listing slug."},
            },
            'anyOf': [{"required": ["listing_id"]}, {"required": ["slug"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_price",
        "description": "Return current price, availability, and fulfillment method for a listing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "string", "description": "Listing UUID."},
                "slug": {"type": "string", "description": "Listing slug."},
            },
            'anyOf': [{"required": ["listing_id"]}, {"required": ["slug"]}],
            "additionalProperties": False,
        },
    },
]


class SearchListingsArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    query: str = Field(validation_alias=AliasChoices("query", "keyword"), min_length=1)
    category: str | None = Field(default=None, min_length=1)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    limit: int = Field(default=10, ge=1, le=PUBLIC_SEARCH_LIMIT_MAX)
    offset: int = Field(default=0, ge=0, le=10_000)

    @model_validator(mode="after")
    def validate_range(self) -> "SearchListingsArguments":
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError("price_min cannot exceed price_max")
        return self


class SearchBuyerRequestsArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    category: str | None = Field(default=None, min_length=1)
    urgency: Literal["low", "normal", "high", "urgent"] | None = None
    limit: int = Field(default=10, ge=1, le=PUBLIC_SEARCH_LIMIT_MAX)
    page: int = Field(default=1, ge=1)


class ListingLookupArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_id: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    @model_validator(mode="after")
    def validate_target(self) -> "ListingLookupArguments":
        if not self.listing_id and not self.slug:
            raise ValueError("One of listing_id or slug is required")
        return self


ToolHandler = Callable[[AsyncSession, dict[str, Any]], Awaitable[dict[str, Any]]]


def get_public_tool_manifest() -> list[dict[str, Any]]:
    return PUBLIC_TOOL_MANIFEST


def get_public_webmcp_manifest() -> dict[str, Any]:
    return {
        "name": "ai.market public WebMCP",
        "version": "1.0.0",
        "description": "Public read-only discovery tools for ai.market listings and buyer requirements.",
        "server": {
            "transport": "sse",
            "sse_url": "/api/v1/agent/sse",
            "tool_call_url": "/api/v1/agent/tools/call",
        },
        "auth": {"type": "none"},
        "tools": get_public_tool_manifest(),
    }


def _client_ip(request: Request) -> str:
    return resolve_client_ip(request)


def _rate_headers(decision: RateLimitDecision) -> dict[str, str]:
    return decision.headers()


def _jsonrpc_error(*, rpc_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": rpc_id, "error": error}


def _jsonrpc_result(*, rpc_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": rpc_id, "result": result}


def _audit_response_payload(
    tool_name: str | None,
    status_name: str,
    response_payload: dict[str, Any],
) -> dict[str, Any] | None:
    # Buyer Request text is public to callers but is not retained in metrics or audit logs.
    if tool_name == "search_buyer_requests" and status_name == "success":
        return None
    return response_payload


def _sse_event(name: str, payload: dict[str, Any], event_id: str | None = None) -> str:
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {name}")
    lines.append(f"data: {json.dumps(payload)}")
    return "\n".join(lines) + "\n\n"


async def _log_tool_call(
    db: AsyncSession,
    *,
    tool_name: str,
    client_ip: str,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any] | None,
    http_status: int,
    status: str,
    error_message: str | None,
    duration_ms: int | None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO agent_audit_log (
                tool_name,
                api_key_id,
                client_ip,
                request_payload,
                response_payload,
                http_status,
                status,
                error_message,
                duration_ms,
                created_at
            ) VALUES (
                :tool_name,
                NULL,
                CAST(:client_ip AS INET),
                CAST(:request_payload AS JSONB),
                CAST(:response_payload AS JSONB),
                :http_status,
                :status,
                :error_message,
                :duration_ms,
                NOW()
            )
            """
        ),
        {
            "tool_name": tool_name,
            "client_ip": client_ip if client_ip and client_ip != "unknown" else None,
            "request_payload": json.dumps(jsonable_encoder(request_payload)),
            "response_payload": json.dumps(jsonable_encoder(response_payload)) if response_payload is not None else None,
            "http_status": http_status,
            "status": status,
            "error_message": error_message,
            "duration_ms": duration_ms,
        },
    )
    await db.commit()


async def _mcp_sse_events(request: Request) -> AsyncGenerator[str, None]:
    session_id = f"public-{int(time.time() * 1000)}"
    init_payload = {
        "jsonrpc": JSONRPC_VERSION,
        "id": "server-init",
        "result": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "ai.market public MCP", "version": "1.0.0"},
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    yield _sse_event("message", init_payload, event_id="server-init")

    tools_payload = {
        "jsonrpc": JSONRPC_VERSION,
        "method": "notifications/tools/list",
        "params": {
            "tools": get_public_tool_manifest(),
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    yield _sse_event("message", tools_payload, event_id="tools-list")

    heartbeat_count = 0
    while True:
        if await request.is_disconnected():
            return
        await asyncio.sleep(SSE_HEARTBEAT_SECONDS)
        heartbeat_count += 1
        heartbeat = {
            "jsonrpc": JSONRPC_VERSION,
            "method": "notifications/ping",
            "params": {
                "sessionId": session_id,
                "count": heartbeat_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        yield _sse_event("heartbeat", heartbeat, event_id=f"heartbeat-{heartbeat_count}")


def _parse_payload(payload: Any) -> tuple[Any, str | None, dict[str, Any], dict[str, Any]]:
    if not isinstance(payload, dict):
        return None, None, {}, {}

    rpc_id = payload.get("id")
    if isinstance(payload.get("params"), dict):
        params = payload["params"]
        return rpc_id, params.get("name"), params.get("arguments") or {}, payload

    tool_name = payload.get("tool") or payload.get("name")
    arguments = payload.get("arguments") or {}
    return rpc_id, tool_name, arguments, payload


def _validate_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    validators: dict[str, type[BaseModel]] = {
        "search_listings": SearchListingsArguments,
        "search_buyer_requests": SearchBuyerRequestsArguments,
        "get_listing_detail": ListingLookupArguments,
        "evaluate_trust": ListingLookupArguments,
        "check_price": ListingLookupArguments,
    }
    validator = validators[tool_name]
    return validator.model_validate(arguments).model_dump(exclude_none=True)


async def _run_search_listings(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    return await search_listings(db, **arguments)


async def _run_search_buyer_requests(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    return await search_buyer_requests(db, **arguments)


async def _run_get_listing_detail(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    return await get_listing_detail(db, **arguments)


async def _run_evaluate_trust(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    return await evaluate_trust(db, **arguments)


async def _run_check_price(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    return await check_price(db, **arguments)


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "search_listings": _run_search_listings,
    "search_buyer_requests": _run_search_buyer_requests,
    "get_listing_detail": _run_get_listing_detail,
    "evaluate_trust": _run_evaluate_trust,
    "check_price": _run_check_price,
}


@router.get("/sse", response_model=None)
async def mcp_sse_endpoint(request: Request) -> StreamingResponse | JSONResponse:
    client_ip = _client_ip(request)
    decision = await check_rate_limit(client_ip, identity_type="ip", operation="read")
    if not decision.allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers=_rate_headers(decision),
        )

    return StreamingResponse(
        _mcp_sse_events(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            **_rate_headers(decision),
        },
    )


@router.post("/tools/call")
async def mcp_tool_call(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> JSONResponse:
    client_ip = _client_ip(request)
    decision = await check_rate_limit(client_ip, identity_type="ip", operation="read")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    rpc_id, tool_name, arguments, request_payload = _parse_payload(payload)

    if not decision.allowed:
        response_payload = _jsonrpc_error(rpc_id=rpc_id, code=-32029, message="Rate limit exceeded")
        await _log_tool_call(
            db,
            tool_name=tool_name or "unknown",
            client_ip=client_ip,
            request_payload=request_payload,
            response_payload=response_payload,
            http_status=429,
            status="rate_limited",
            error_message="Rate limit exceeded",
            duration_ms=0,
        )
        return JSONResponse(status_code=429, content=response_payload, headers=_rate_headers(decision))

    if tool_name not in TOOL_HANDLERS:
        response_payload = _jsonrpc_error(rpc_id=rpc_id, code=-32601, message="Unknown tool")
        await _log_tool_call(
            db,
            tool_name=tool_name or "unknown",
            client_ip=client_ip,
            request_payload=request_payload,
            response_payload=response_payload,
            http_status=404,
            status="error",
            error_message="Unknown tool",
            duration_ms=0,
        )
        return JSONResponse(status_code=404, content=response_payload, headers=_rate_headers(decision))

    started = time.perf_counter()
    status_code = 200
    status_name = "success"
    error_message: str | None = None

    try:
        validated_arguments = _validate_arguments(tool_name, arguments)
        result = await TOOL_HANDLERS[tool_name](db, validated_arguments)
        response_payload = _jsonrpc_result(rpc_id=rpc_id, result={"tool": tool_name, "data": jsonable_encoder(result)})
    except HTTPException as exc:
        status_code = exc.status_code
        status_name = "error"
        error_message = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
        response_payload = _jsonrpc_error(rpc_id=rpc_id, code=-32000, message=error_message)
    except (TypeError, ValueError, ValidationError) as exc:
        status_code = 400
        status_name = "error"
        error_message = str(exc)
        response_payload = _jsonrpc_error(rpc_id=rpc_id, code=-32602, message="Invalid params", data=str(exc))
    except Exception:
        logger.exception("Public MCP tool call failed for %s", tool_name)
        status_code = 500
        status_name = "error"
        error_message = "Internal server error"
        response_payload = _jsonrpc_error(rpc_id=rpc_id, code=-32603, message=error_message)

    duration_ms = int((time.perf_counter() - started) * 1000)
    await _log_tool_call(
        db,
        tool_name=tool_name,
        client_ip=client_ip,
        request_payload=request_payload,
        response_payload=_audit_response_payload(tool_name, status_name, response_payload),
        http_status=status_code,
        status=status_name,
        error_message=error_message,
        duration_ms=duration_ms,
    )
    return JSONResponse(status_code=status_code, content=response_payload, headers=_rate_headers(decision))
