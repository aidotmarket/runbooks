"""Agent API key validation and spend-cap enforcement."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AgentAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_scopes(scope_value: Any) -> list[str]:
        if scope_value is None:
            return []
        if isinstance(scope_value, list):
            return [str(item) for item in scope_value if str(item).strip()]
        if isinstance(scope_value, str):
            return [
                item.strip()
                for item in scope_value.replace(";", ",").split(",")
                if item.strip()
            ]
        return [str(scope_value)]

    @staticmethod
    def _extract_lookup_material(raw_key: str) -> tuple[str, str]:
        cleaned = raw_key.strip()
        if len(cleaned) < 8:
            raise HTTPException(status_code=401, detail="Invalid agent API key")
        prefix = cleaned[:8]
        return prefix, AgentAuthService.hash_api_key(cleaned)

    @staticmethod
    def _invalid_key_error() -> HTTPException:
        return HTTPException(status_code=401, detail="Invalid agent API key")

    @staticmethod
    def _suspended_key_error() -> HTTPException:
        return HTTPException(status_code=401, detail="Agent API key is suspended")

    @staticmethod
    def _scope_error(required_scope: str) -> HTTPException:
        return HTTPException(status_code=403, detail=f"Missing required scope: {required_scope}")

    @staticmethod
    def _spend_cap_error() -> HTTPException:
        return HTTPException(status_code=403, detail="Spend cap exceeded")

    async def validate_key(self, raw_key: str) -> dict[str, Any]:
        if not raw_key:
            raise HTTPException(status_code=401, detail="x-api-key header is required")

        prefix, key_hash = self._extract_lookup_material(raw_key)
        result = await self.db.execute(
            text(
                """
                SELECT
                    id,
                    org_id,
                    scopes,
                    spend_cap,
                    spend_used,
                    rate_limit_rpm,
                    is_active,
                    suspended_until,
                    revoked_at
                FROM agent_api_keys
                WHERE prefix = :prefix
                  AND key_hash = :key_hash
                """
            ),
            {"prefix": prefix, "key_hash": key_hash},
        )
        row = result.mappings().fetchone()
        if not row:
            raise self._invalid_key_error()

        now = datetime.now(timezone.utc)
        suspended_until = row["suspended_until"]
        if not row["is_active"] or row["revoked_at"] is not None:
            raise self._invalid_key_error()
        if suspended_until is not None and suspended_until.tzinfo is None:
            suspended_until = suspended_until.replace(tzinfo=timezone.utc)
        if suspended_until is not None and suspended_until > now:
            raise self._suspended_key_error()

        return {
            "id": row["id"],
            "org_id": row["org_id"],
            "scopes": self._normalize_scopes(row["scopes"]),
            "spend_cap": row["spend_cap"] or 0,
            "spend_used": row["spend_used"] or 0,
            "rate_limit_rpm": row["rate_limit_rpm"] or 60,
        }

    async def validate_api_key(self, raw_key: str | None) -> dict[str, Any]:
        if raw_key is None:
            raise HTTPException(status_code=401, detail="x-api-key header is required")
        return await self.validate_key(raw_key)

    async def check_scope(self, key_data: dict[str, Any], required_scope: str) -> None:
        scopes = set(self._normalize_scopes(key_data.get("scopes", key_data.get("scope"))))
        if "*" in scopes or required_scope in scopes:
            return
        raise self._scope_error(required_scope)

    def require_scope(self, key_row: dict[str, Any], required_scope: str) -> None:
        scopes = set(self._normalize_scopes(key_row.get("scopes", key_row.get("scope"))))
        if "*" in scopes or required_scope in scopes:
            return
        raise self._scope_error(required_scope)

    async def check_spend_cap(self, key_id: UUID, amount_cents: int) -> None:
        result = await self.db.execute(
            text(
                """
                SELECT spend_used, spend_cap
                FROM agent_api_keys
                WHERE id = :key_id
                FOR UPDATE
                """
            ),
            {"key_id": key_id},
        )
        row = result.mappings().fetchone()
        if not row:
            raise self._invalid_key_error()
        spend_used = row["spend_used"] or 0
        spend_cap = row["spend_cap"] or 0
        if spend_used + amount_cents > spend_cap:
            raise self._spend_cap_error()

    async def increment_spend(self, key_id: UUID, amount_cents: int) -> None:
        await self.db.execute(
            text(
                """
                UPDATE agent_api_keys
                SET spend_used = spend_used + :amount_cents,
                    updated_at = NOW()
                WHERE id = :key_id
                """
            ),
            {"key_id": key_id, "amount_cents": amount_cents},
        )

    async def decrement_spend(self, key_id: UUID, amount_cents: int) -> None:
        await self.db.execute(
            text(
                """
                UPDATE agent_api_keys
                SET spend_used = GREATEST(0, spend_used - :amount_cents),
                    updated_at = NOW()
                WHERE id = :key_id
                """
            ),
            {"key_id": key_id, "amount_cents": amount_cents},
        )

    async def get_api_key(self, api_key_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    id,
                    org_id,
                    name,
                    key_hash,
                    prefix,
                    scopes,
                    spend_cap,
                    spend_used,
                    rate_limit_rpm,
                    is_active,
                    suspended_until,
                    revoked_at
                FROM agent_api_keys
                WHERE id = :id
                """
            ),
            {"id": api_key_id},
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent API key not found")
        data = dict(row)
        data["scopes"] = self._normalize_scopes(data.get("scopes"))
        # Preserve compatibility for callers that still expect singular scope.
        data["scope"] = ",".join(data["scopes"])
        return data

    async def reserve_spend(self, api_key_id: UUID, amount_cents: int) -> dict[str, Any]:
        await self.check_spend_cap(api_key_id, amount_cents)
        await self.increment_spend(api_key_id, amount_cents)
        return await self.get_api_key(api_key_id)

    async def rollback_spend(self, api_key_id: UUID, amount_cents: int) -> None:
        await self.decrement_spend(api_key_id, amount_cents)

    async def get_org_context(self, api_key_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    ak.id,
                    ak.org_id,
                    auth_user.external_id::uuid AS org_owner_user_id,
                    stripe_identity.external_id AS stripe_customer_id,
                    stripe_identity.metadata->>'default_payment_method_id' AS default_payment_method_id
                FROM agent_api_keys ak
                LEFT JOIN party_identity auth_user
                    ON auth_user.party_id = ak.org_id
                   AND auth_user.provider = 'auth_user'
                   AND auth_user.is_primary = true
                LEFT JOIN party_identity stripe_identity
                    ON stripe_identity.party_id = ak.org_id
                   AND stripe_identity.provider = 'stripe'
                   AND stripe_identity.is_primary = true
                WHERE ak.id = :id
                """
            ),
            {"id": api_key_id},
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent API key not found")
        return dict(row)
