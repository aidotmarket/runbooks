"""
PolicyEngine — BQ-FINANCIAL-SYSTEM Phase 2
===========================================

Classifies agent commands as AUTO / PROPOSE / BLOCKED.
- AUTO: read-only + deterministic writes — execute immediately, audit logged.
- PROPOSE: creates FinanceAgentProposal record, awaits human approval.
- BLOCKED: reject outright.

Tool registry maps tool_name → (handler_key, autonomy_level).
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.finance import FinanceAgentProposal, FinanceAgentAuditLog
from app.services.finance.engine import AIMARKET_ENTITY_ID

VALID_APPROVER_TYPES = frozenset({"system", "admin", "agent"})


# ---------------------------------------------------------------------------
# Tool registry: tool_name → autonomy level
# ---------------------------------------------------------------------------

AUTO_TOOLS = frozenset({
    "get_trial_balance",
    "get_pnl",
    "get_invoice_list",
    "get_payment_list",
    "get_balance",
    "draft_invoice",
    "calculate_pricing",
    "validate_coupon",
    "get_accounts",
    "record_api_cost",
    # Phase 3a
    "get_reconciliation_status",
    "get_tax_summary",
    "get_period_status",
    "run_reconciliation",
})

PROPOSE_TOOLS = frozenset({
    "propose_refund",
    "propose_credit_note",
    "propose_manual_journal",
    "propose_void_invoice",
    "propose_pricing_change",
    "propose_coupon",
    # Phase 3a
    "propose_close_period",
    "propose_tax_filing",
    "allocate_payment_manual",
})

BLOCKED_TOOLS = frozenset({
    "raw_journal_write",
    "edit_posted_entry",
    "delete_record",
    "reopen_closed_period",
    "self_approve",
})


def classify(tool_name: str) -> str:
    """Return autonomy level for a given tool name."""
    if tool_name in AUTO_TOOLS:
        return "auto"
    if tool_name in PROPOSE_TOOLS:
        return "propose"
    if tool_name in BLOCKED_TOOLS:
        return "blocked"
    # Unknown tools are blocked by default
    return "blocked"


class PolicyEngine:
    """Routes agent commands through the autonomy classification pipeline."""

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    async def _audit_log(
        self,
        tool_name: str,
        autonomy_level: str,
        input_payload: dict,
        status: str,
        db: AsyncSession,
        output_payload: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> FinanceAgentAuditLog:
        log = FinanceAgentAuditLog(
            tool_name=tool_name,
            autonomy_level=autonomy_level,
            input_payload=input_payload,
            output_payload=output_payload,
            status=status,
            error=error,
            approved_by=approved_by,
        )
        if status == "approved":
            log.approved_at = datetime.now(timezone.utc)
        db.add(log)
        await db.flush()
        return log

    # ------------------------------------------------------------------
    # Execute AUTO tool
    # ------------------------------------------------------------------

    async def execute_auto(
        self,
        tool_name: str,
        payload: dict,
        handler_result: Any,
        db: AsyncSession,
    ) -> dict:
        """Execute an AUTO tool and log it."""
        output = handler_result if isinstance(handler_result, dict) else {"result": str(handler_result)}
        await self._audit_log(
            tool_name=tool_name,
            autonomy_level="auto",
            input_payload=payload,
            status="executed",
            output_payload=output,
            db=db,
        )
        return output

    # ------------------------------------------------------------------
    # Create PROPOSE proposal
    # ------------------------------------------------------------------

    async def create_proposal(
        self,
        tool_name: str,
        command_type: str,
        payload: dict,
        idempotency_key: str,
        db: AsyncSession,
        created_by: str = "finance_agent",
        entity_id: UUID = AIMARKET_ENTITY_ID,
        output_preview: Optional[Dict[str, Any]] = None,
    ) -> FinanceAgentProposal:
        """Create a pending proposal for human approval."""
        # Idempotency check
        existing = await db.execute(
            select(FinanceAgentProposal).where(
                FinanceAgentProposal.idempotency_key == idempotency_key
            )
        )
        existing_proposal = existing.scalar_one_or_none()
        if existing_proposal is not None:
            return existing_proposal

        proposal = FinanceAgentProposal(
            entity_id=entity_id,
            tool_name=tool_name,
            command_type=command_type,
            input_payload=payload,
            output_preview=output_preview,
            status="pending",
            created_by=created_by,
            idempotency_key=idempotency_key,
        )
        db.add(proposal)
        await db.flush()

        await self._audit_log(
            tool_name=tool_name,
            autonomy_level="propose",
            input_payload=payload,
            status="proposed",
            db=db,
        )

        return proposal

    # ------------------------------------------------------------------
    # Approve / Reject proposals
    # ------------------------------------------------------------------

    def _generate_approval_token(
        self, proposal_id: UUID, approved_by: str, timestamp: str,
    ) -> str:
        """Generate HMAC-SHA256 approval token using server-side secret."""
        settings = get_settings()
        secret = getattr(settings, "FINANCE_APPROVAL_SECRET", None) or settings.SECRET_KEY
        msg = f"{proposal_id}{approved_by}{timestamp}".encode()
        return hmac.new(secret.encode(), msg=msg, digestmod=hashlib.sha256).hexdigest()

    async def approve_proposal(
        self,
        proposal_id: UUID,
        approved_by: str,
        db: AsyncSession,
        approver_type: str = "admin",
    ) -> tuple[FinanceAgentProposal, str, str]:
        """Approve a pending proposal with hardened identity (MP-P2-1)."""
        if not approved_by:
            raise ValueError("approved_by must not be empty")
        if approver_type not in VALID_APPROVER_TYPES:
            raise ValueError(f"approver_type must be one of {sorted(VALID_APPROVER_TYPES)}")

        result = await db.execute(
            select(FinanceAgentProposal).where(FinanceAgentProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal.status != "pending":
            raise ValueError(f"Proposal {proposal_id} is not pending (status: {proposal.status})")

        # Self-approval prevention: proposer must not be the approver
        if proposal.created_by == approved_by:
            raise ValueError(
                f"Self-approval denied: proposer '{approved_by}' cannot approve their own proposal"
            )

        now = datetime.now(timezone.utc)

        # HMAC-SHA256 approval token using server-side secret (not spoofable)
        approval_token = self._generate_approval_token(
            proposal_id, approved_by, now.isoformat(),
        )

        proposal.status = "approved"
        proposal.approved_by = approved_by
        proposal.approved_at = now
        await db.flush()

        log = await self._audit_log(
            tool_name=proposal.tool_name,
            autonomy_level="propose",
            input_payload=proposal.input_payload,
            status="approved",
            approved_by=approved_by,
            db=db,
        )
        # Store hardened identity on the audit log entry
        log.approver_type = approver_type
        log.approval_token = approval_token
        await db.flush()

        return proposal, approval_token, approver_type

    async def reject_proposal(
        self,
        proposal_id: UUID,
        rejected_by: str,
        reason: str,
        db: AsyncSession,
    ) -> FinanceAgentProposal:
        """Reject a pending proposal."""
        result = await db.execute(
            select(FinanceAgentProposal).where(FinanceAgentProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal.status != "pending":
            raise ValueError(f"Proposal {proposal_id} is not pending (status: {proposal.status})")

        proposal.status = "rejected"
        proposal.rejected_at = datetime.now(timezone.utc)
        proposal.rejection_reason = reason
        await db.flush()

        await self._audit_log(
            tool_name=proposal.tool_name,
            autonomy_level="propose",
            input_payload=proposal.input_payload,
            status="rejected",
            db=db,
        )

        return proposal

    # ------------------------------------------------------------------
    # List pending proposals
    # ------------------------------------------------------------------

    async def list_pending(
        self,
        db: AsyncSession,
        entity_id: UUID = AIMARKET_ENTITY_ID,
        limit: int = 50,
    ) -> list[FinanceAgentProposal]:
        result = await db.execute(
            select(FinanceAgentProposal)
            .where(
                FinanceAgentProposal.entity_id == entity_id,
                FinanceAgentProposal.status == "pending",
            )
            .order_by(FinanceAgentProposal.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Audit log queries
    # ------------------------------------------------------------------

    async def get_audit_log(
        self,
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FinanceAgentAuditLog]:
        result = await db.execute(
            select(FinanceAgentAuditLog)
            .order_by(FinanceAgentAuditLog.proposed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Block check
    # ------------------------------------------------------------------

    def is_blocked(self, tool_name: str) -> bool:
        return classify(tool_name) == "blocked"
