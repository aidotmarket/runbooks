"""
Finance Agent skeleton for BQ-FINANCIAL-SYSTEM.

Phase 1 keeps the agent intentionally narrow: read/reporting skills plus a
reconciliation trigger. Finance Engine and the database remain the final
validators for any money-bearing write.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.allai.base_agent import BaseAgent
from app.allai.event_bus import Event
from app.allai.service_bus import DomainDeclaration
from app.allai.skill import skill
from app.core.database import AsyncSessionLocal
from app.services.finance.engine import AIMARKET_ENTITY_ID
from app.services.finance.gl_service import GLService
from app.services.finance.payment_service import PaymentService
from app.services.finance.reconciliation import ReconciliationService

logger = logging.getLogger(__name__)


class FinanceSkillBase(BaseModel):
    entity_id: UUID = Field(default=AIMARKET_ENTITY_ID)
    actor_id: str
    request_id: str
    idempotency_key: str


class FinanceSkillResult(BaseModel):
    status: str
    message: Optional[str] = None
    proposal_id: Optional[UUID] = None
    data: Optional[dict] = None
    error: Optional[str] = None


class GetTrialBalanceInput(FinanceSkillBase):
    as_of: date


class ListPaymentsInput(FinanceSkillBase):
    status_filter: Optional[str] = Field(default=None, alias="status")
    limit: int = 50

    model_config = {"populate_by_name": True}


class RunReconciliationInput(FinanceSkillBase):
    period_id: UUID


class FinanceAgent(BaseAgent):
    agent_key = "finance"
    domain = DomainDeclaration(name="finance", resources=["ledger", "payments", "reconciliation"])
    name = "allAI:Finance"
    description = "Finance operations agent for ledger, payments, and reconciliation"
    semver = "0.1.0"
    tier = 1

    rate_limit_per_minute = 60
    budget_cap_usd = Decimal("2.00")
    quarantine_threshold = 3

    interaction_modes = ["rest_api"]
    depends_on: list[str] = ["agent-log"]
    subscriptions: list[str] = []
    publishes: list[str] = []

    def __init__(self) -> None:
        super().__init__()
        self._gl = GLService()
        self._payments = PaymentService()
        self._reconciliation = ReconciliationService()

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events. Currently a no-op - finance events are skill-routed."""
        logger.debug(
            "FinanceAgent received event %s (type=%s), no handler configured",
            event.id,
            event.event_type,
        )

    @skill(
        name="get_trial_balance",
        description="Return a trial balance snapshot for a billing entity as of a given date.",
        access="read",
        input_schema=GetTrialBalanceInput,
    )
    async def get_trial_balance(self, input: GetTrialBalanceInput) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            result = await self._gl.trial_balance(input.entity_id, input.as_of, db)
            return FinanceSkillResult(
                status="ok",
                data=result.model_dump(mode="json"),
            ).model_dump(mode="json")

    @skill(
        name="list_payments",
        description="List recent payments for a billing entity.",
        access="read",
        input_schema=ListPaymentsInput,
    )
    async def list_payments(self, input: ListPaymentsInput) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            payments = await self._payments.list(
                entity_id=input.entity_id,
                db=db,
                status=input.status_filter,
                limit=input.limit,
            )
            return FinanceSkillResult(
                status="ok",
                data={
                    "payments": [
                        {
                            "id": str(payment.id),
                            "amount_cents": payment.amount_cents,
                            "status": payment.status,
                            "payment_type": payment.payment_type,
                            "received_at": payment.received_at.isoformat(),
                        }
                        for payment in payments
                    ]
                },
            ).model_dump(mode="json")

    @skill(
        name="run_reconciliation",
        description="Run Stripe to ledger reconciliation for an accounting period.",
        access="write",
        mutates_state=True,
        input_schema=RunReconciliationInput,
    )
    async def run_reconciliation(self, input: RunReconciliationInput) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            result = await self._reconciliation.run(
                entity_id=input.entity_id,
                period_id=input.period_id,
                db=db,
            )
            await db.commit()
            return FinanceSkillResult(status="ok", data=result).model_dump(mode="json")
