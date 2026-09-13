"""Marketplace MCP auth middleware — MCP API key authentication for FastMCP.

Pure ASGI middleware (not BaseHTTPMiddleware) for SSE compatibility.
Validates MCP API keys (aim_* Bearer tokens) via the existing auth infrastructure
in mcp_deps.py / mcp_key_service.py.

Per-tool scope enforcement happens inside the tool implementations, not here.
This middleware handles:
  - Bearer token extraction & HMAC-SHA256 validation
  - Redis cache → Postgres fallback
  - Rate limiting (per-key + per-user aggregate)
  - Abuse detection (IP block, burst, auto-revoke)
  - Setting auth context for tool access

Auth modes:
  1. MCP_API_KEY_SECRET is set → full auth (production)
  2. MCP_API_KEY_SECRET is unset → 503 (marketplace MCP requires API keys)

CREATED: 2026-02-24  (BQ-E2)
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.request_ip import resolve_client_ip

logger = logging.getLogger(__name__)


class _MarketplaceMCPAuthMiddleware:
    """ASGI middleware that validates MCP API keys for marketplace tools."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract request path — skip auth for health check
        path = scope.get("path", "")
        if path.rstrip("/") in ("/health", ""):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        request_id = str(uuid.uuid4())

        # Resolve the trusted caller IP via the shared resolver. Building a
        # Starlette Request from the ASGI scope is body-safe here: resolve_client_ip
        # only reads request.client and request.headers, never receive()/the body.
        client_ip = resolve_client_ip(Request(scope))

        # Check IP block
        try:
            from app.services.mcp_middleware_service import is_ip_blocked
            if await is_ip_blocked(client_ip):
                response = _error_response(
                    429, "RATE_LIMITED",
                    "Too many failed attempts. Try again later.",
                    request_id,
                )
                await response(scope, receive, send)
                return
        except Exception:
            pass  # Fail open

        # Require Bearer token
        if not auth_header.startswith("Bearer "):
            response = _error_response(
                401, "AUTH_REQUIRED",
                "Authorization: Bearer aim_<key> header required",
                request_id,
            )
            await response(scope, receive, send)
            return

        bearer_token = auth_header[7:]
        if not bearer_token.startswith("aim_"):
            try:
                from app.services.mcp_middleware_service import record_auth_failure
                await record_auth_failure(client_ip)
            except Exception:
                pass
            response = _error_response(
                401, "AUTH_INVALID",
                "Invalid API key format (must start with aim_)",
                request_id,
            )
            await response(scope, receive, send)
            return

        # Validate key via existing service
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.mcp_key_service import MCPKeyService

            async with AsyncSessionLocal() as db:
                key_service = MCPKeyService(db)
                key_info = await key_service.validate_key(bearer_token)

                if key_info is None:
                    key_prefix = bearer_token[:8]
                    try:
                        from app.services.mcp_middleware_service import record_auth_failure
                        await record_auth_failure(client_ip, key_prefix)
                    except Exception:
                        pass
                    response = _error_response(
                        401, "AUTH_INVALID", "Invalid API key", request_id,
                    )
                    await response(scope, receive, send)
                    return

                # Check auto-revoke
                key_hash = key_info["key_hash"]
                try:
                    from app.services.redis_service import redis_service
                    flag = await redis_service.get(f"mcp_autorevoke:{key_info['key_prefix']}")
                    if flag:
                        response = _error_response(
                            401, "AUTH_REVOKED",
                            "API key revoked due to abuse detection",
                            request_id,
                        )
                        await response(scope, receive, send)
                        return
                except Exception:
                    pass

                # Burst / throttle check
                from app.services.mcp_middleware_service import (
                    check_burst,
                    check_rate_limit,
                    is_throttled,
                )

                if await is_throttled(key_hash):
                    response = _error_response(
                        429, "RATE_LIMITED",
                        "Temporarily throttled due to burst activity",
                        request_id,
                    )
                    await response(scope, receive, send)
                    return

                # Per-key rate limit
                rate_limit = key_info["rate_limit_per_min"]
                allowed, remaining, reset_epoch = await check_rate_limit(key_hash, rate_limit)
                if not allowed:
                    retry_after = max(1, reset_epoch - int(time.time()))
                    response = _error_response(
                        429, "RATE_LIMITED", "Rate limit exceeded", request_id,
                        extra_headers={
                            "Retry-After": str(retry_after),
                            "RateLimit-Limit": str(rate_limit),
                            "RateLimit-Remaining": "0",
                            "RateLimit-Reset": str(reset_epoch),
                        },
                    )
                    await response(scope, receive, send)
                    return

                # Burst detection
                burst_ok = await check_burst(key_hash, rate_limit)
                if not burst_ok:
                    response = _error_response(
                        429, "RATE_LIMITED",
                        "Burst rate limit exceeded. Slow down.",
                        request_id,
                    )
                    await response(scope, receive, send)
                    return

                # Store auth context in scope for tools to read
                scope["state"] = scope.get("state", {})
                scope["state"]["mcp_marketplace_auth"] = {
                    "user_id": key_info["user_id"],
                    "api_key_id": key_info["id"],
                    "key_hash": key_hash,
                    "key_prefix": key_info["key_prefix"],
                    "scopes": key_info["scopes"],
                    "rate_limit_per_min": rate_limit,
                    "rate_limit_remaining": remaining,
                    "rate_limit_reset": reset_epoch,
                    "request_id": request_id,
                }

                # Fire-and-forget: update last_used_at. last_used_ip is a nullable
                # INET column, so persist NULL rather than the "unknown" sentinel.
                import asyncio
                asyncio.create_task(
                    _update_last_used(key_hash, client_ip if client_ip != "unknown" else None)
                )

        except Exception as e:
            logger.error("Marketplace MCP auth error: %s", e)
            response = _error_response(
                500, "SERVER_ERROR", "Authentication service error", request_id,
            )
            await response(scope, receive, send)
            return

        # Auth passed — forward to FastMCP
        await self.app(scope, receive, send)


async def _update_last_used(key_hash: str, ip: str | None) -> None:
    """Background task to update last_used_at."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.mcp_api_key import MCPApiKey
        from sqlalchemy import update
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(MCPApiKey)
                .where(MCPApiKey.key_hash == key_hash)
                .values(
                    last_used_at=datetime.now(timezone.utc),
                    last_used_ip=ip,
                )
            )
            await session.commit()
    except Exception as e:
        logger.debug("last_used_at update failed (non-critical): %s", e)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    *,
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a standard MCP error response (C3 contract)."""
    headers = {"X-Request-Id": request_id}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers=headers,
    )


def marketplace_mcp_auth_app(mcp_server) -> ASGIApp:
    """Wrap the FastMCP streamable_http_app with MCP API key auth.

    Auth is always required for marketplace MCP (unlike CRM which can
    fall back to authless in local dev).
    """
    inner = mcp_server.streamable_http_app()

    if not settings.MCP_API_KEY_SECRET:
        logger.warning(
            "MCP_API_KEY_SECRET not set — marketplace MCP will reject all requests"
        )

    return _MarketplaceMCPAuthMiddleware(inner)
