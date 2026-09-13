"""
Finance Agent Router - BQ-FINANCIAL-SYSTEM Phase 2
==================================================

Agent command interface for the finance system.
Auth: X-Internal-API-Key (same as Phase 1 finance router).

Endpoints:
- POST /command — Submit typed AgentCommand
- GET /pending — List pending proposals
- POST /approve/{id} — Approve proposal (executes it)
- POST /reject/{id} — Reject proposal
- GET /audit-log - Agent action history
"""

from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_internal_api_key
from app.core.database import get_async_db
from app.schemas.finance import (
    AgentCommand,
    AgentCommandResult,
    AuditLogEntry,
    GetTrialBalanceCommand,
    InvoiceCreate,
    ProposalResponse,
)
from app.services.finance.coupon_service import CouponService
from app.services.finance.engine import AIMARKET_ENTITY_ID, FinanceEngine
from app.services.finance.gl_service import GLService
from app.services.finance.invoice_service import InvoiceService
from app.services.finance.payment_service import PaymentService
from app.services.finance.period_service import PeriodService
from app.services.finance.policy_engine import PolicyEngine, classify
from app.services.finance.pricing_service import PricingService
from app.services.finance.reconciliation import ReconciliationService
from app.services.finance.tax_service import TaxService

router = APIRouter(
    prefix="/api/v1/finance/agent",
    tags=["Finance Agent"],
    dependencies=[Depends(get_internal_api_key)],
)

_policy = PolicyEngine()
_engine = FinanceEngine()
_gl = GLService()
_inv = InvoiceService()
_pay = PaymentService()
_pricing = PricingService()
_coupon = CouponService()
_period = PeriodService()
_recon = ReconciliationService()
_tax = TaxService()
_ENTITY = AIMARKET_ENTITY_ID


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

async def _dispatch_auto(
    command: AgentCommand,
    db: AsyncSession,
) -> dict:
    """Execute an AUTO-level command and return the result."""
    ct = command.command_type

    if ct == "get_trial_balance":
        cmd = command if isinstance(command, GetTrialBalanceCommand) else command
        as_of = getattr(cmd, "as_of", None) or date.today()
        tb = await _gl.trial_balance(_ENTITY, as_of, db)
        return tb.model_dump(mode="json")

    elif ct == "get_pnl":
        pnl = await _gl.profit_and_loss(
            _ENTITY, command.period_start, command.period_end, db  # type: ignore[attr-defined]
        )
        return pnl.model_dump(mode="json")

    elif ct == "get_invoice_list":
        invoices = await _inv.list(
            _ENTITY, db,
            status=getattr(command, "status", None),
            limit=getattr(command, "limit", 50),
        )
        return {"invoices": [{"id": str(i.id), "number": i.invoice_number, "status": i.status, "total_cents": i.total_cents} for i in invoices]}

    elif ct == "get_payment_list":
        payments = await _pay.list(
            _ENTITY, db,
            status=getattr(command, "status", None),
            limit=getattr(command, "limit", 50),
        )
        return {"payments": [{"id": str(p.id), "amount_cents": p.amount_cents, "status": p.status} for p in payments]}

    elif ct == "get_accounts":
        accounts = await _gl.list_accounts(_ENTITY, db)
        return {"accounts": accounts}

    elif ct == "get_balance":
        as_of = getattr(command, "as_of", None) or date.today()
        tb = await _gl.trial_balance(_ENTITY, as_of, db)
        code = getattr(command, "account_code", "")
        for acct in tb.accounts:
            if acct.get("code") == code:
                return {"account_code": code, "debit_balance": acct["debit_balance"], "credit_balance": acct["credit_balance"]}
        return {"account_code": code, "debit_balance": 0, "credit_balance": 0}

    elif ct == "draft_invoice":
        inv_data = InvoiceCreate(
            customer_id=command.customer_id,  # type: ignore[attr-defined]
            due_date=date.today(),
            lines=command.line_items,  # type: ignore[attr-defined]
            notes=getattr(command, "notes", None),
        )
        invoice = await _inv.create_draft(inv_data, db)
        return {"invoice_id": str(invoice.id), "invoice_number": invoice.invoice_number, "total_cents": invoice.total_cents}

    elif ct == "calculate_pricing":
        result = await _pricing.calculate(
            command.tier_type,  # type: ignore[attr-defined]
            command.amount_cents,  # type: ignore[attr-defined]
            db,
        )
        return result

    elif ct == "validate_coupon":
        result = await _coupon.validate(command.code, db)  # type: ignore[attr-defined]
        return result

    elif ct == "record_api_cost":
        entry = await _engine.record_api_cost(
            provider=command.provider,  # type: ignore[attr-defined]
            amount_cents=command.amount_cents,  # type: ignore[attr-defined]
            period_id=UUID("00000000-0000-0000-0000-000000000000"),  # placeholder
            idempotency_key=command.idempotency_key,
            db=db,
        )
        return {"journal_entry_id": str(entry.id), "entry_number": entry.entry_number}

    # Phase 3a AUTO tools
    elif ct == "get_reconciliation_status":
        period_id = UUID(getattr(command, "period_id", "00000000-0000-0000-0000-000000000000"))
        return await _recon.summary(_ENTITY, period_id, db)

    elif ct == "get_tax_summary":
        return await _tax.summary(
            _ENTITY,
            getattr(command, "period_start", date.today()),
            getattr(command, "period_end", date.today()),
            db,
        )

    elif ct == "get_period_status":
        return await _period.status(_ENTITY, db)

    elif ct == "run_reconciliation":
        period_id = UUID(getattr(command, "period_id", "00000000-0000-0000-0000-000000000000"))
        return await _recon.run(_ENTITY, period_id, db)

    raise ValueError(f"Unknown auto command type: {ct}")


def _build_propose_preview(command: AgentCommand) -> dict:
    """Build a human-readable preview for a PROPOSE command."""
    return command.model_dump(mode="json")


# ---------------------------------------------------------------------------
# POST /command — Submit typed AgentCommand
# ---------------------------------------------------------------------------

@router.post("/command", response_model=AgentCommandResult)
async def submit_command(
    command: AgentCommand,
    db: AsyncSession = Depends(get_async_db),
) -> AgentCommandResult:
    """Submit a finance agent command. Routed by PolicyEngine."""
    tool_name = command.command_type
    level = classify(tool_name)

    if level == "blocked":
        return AgentCommandResult(
            autonomy_level="blocked",
            status="blocked",
            message=f"Tool '{tool_name}' is blocked by policy",
        )

    if level == "auto":
        try:
            result = await _dispatch_auto(command, db)
            await _policy.execute_auto(
                tool_name, command.model_dump(mode="json"), result, db
            )
            await db.commit()
            return AgentCommandResult(
                autonomy_level="auto",
                status="executed",
                result=result,
                message="Executed successfully",
            )
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=422, detail=str(e))

    # PROPOSE
    try:
        proposal = await _policy.create_proposal(
            tool_name=tool_name,
            command_type=command.command_type,
            payload=command.model_dump(mode="json"),
            idempotency_key=command.idempotency_key,
            db=db,
            output_preview=_build_propose_preview(command),
        )
        await db.commit()
        return AgentCommandResult(
            autonomy_level="propose",
            status="proposed",
            proposal_id=proposal.id,
            message=f"Proposal created. Awaiting approval (ID: {proposal.id})",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# GET /pending — List pending proposals
# ---------------------------------------------------------------------------

@router.get("/pending", response_model=List[ProposalResponse])
async def list_pending(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_async_db),
) -> list:
    proposals = await _policy.list_pending(db, limit=limit)
    return [ProposalResponse.model_validate(p) for p in proposals]


# ---------------------------------------------------------------------------
# POST /approve/{id} — Approve proposal
# ---------------------------------------------------------------------------

class ApproveRequest(BaseModel):
    approved_by: str


@router.post("/approve/{proposal_id}", response_model=ProposalResponse)
async def approve_proposal(
    proposal_id: UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ProposalResponse:
    """Approve a pending proposal and execute it."""
    try:
        proposal, approval_token, approver_type = await _policy.approve_proposal(
            proposal_id, body.approved_by, db
        )

        # Execute the approved proposal
        payload = proposal.input_payload
        ct = proposal.command_type

        if ct == "propose_refund":
            refund_entry = await _engine.record_refund(
                payment_id=UUID(payload["payment_id"]),
                amount_cents=payload["amount_cents"],
                reason=payload["reason"],
                stripe_refund_id=f"approved:{proposal.id}",
                db=db,
            )
            refund_entry.approved_by = body.approved_by
            refund_entry.approver_type = approver_type
            refund_entry.approval_token = approval_token
            await db.flush()
        elif ct in ("propose_manual_journal", "manual_journal_entry"):
            journal_entry = await _engine.propose_manual_journal(
                lines=payload["lines"],
                description=payload["description"],
                created_by=body.approved_by,
                idempotency_key=payload["idempotency_key"],
                db=db,
            )
            # P1-1: Propagate approval identity to JournalEntry (MP Gate 3)
            journal_entry.approved_by = body.approved_by
            journal_entry.approver_type = approver_type
            journal_entry.approval_token = approval_token
            await db.flush()
        elif ct == "propose_void_invoice":
            await _inv.void(UUID(payload["invoice_id"]), db, reason=payload["reason"])
        elif ct == "propose_pricing_change":
            await _pricing.create_tier(
                tier_type=payload["tier_type"],
                name=payload["name"],
                rate_bps=payload["rate_bps"],
                min_threshold_cents=payload.get("min_threshold_cents", 0),
                db=db,
            )
        elif ct == "propose_coupon":
            from datetime import datetime
            await _coupon.create(
                code=payload["code"],
                discount_type=payload["discount_type"],
                discount_value=payload["discount_value"],
                applies_to=payload["applies_to"],
                valid_from=datetime.fromisoformat(payload["valid_from"]),
                valid_until=datetime.fromisoformat(payload["valid_until"]) if payload.get("valid_until") else None,
                max_redemptions=payload.get("max_redemptions"),
                db=db,
            )

        await db.commit()
        await db.refresh(proposal)
        return ProposalResponse.model_validate(proposal)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# POST /reject/{id} — Reject proposal
# ---------------------------------------------------------------------------

class RejectRequest(BaseModel):
    rejected_by: str
    reason: str


@router.post("/reject/{proposal_id}", response_model=ProposalResponse)
async def reject_proposal(
    proposal_id: UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ProposalResponse:
    try:
        proposal = await _policy.reject_proposal(
            proposal_id, body.rejected_by, body.reason, db
        )
        await db.commit()
        await db.refresh(proposal)
        return ProposalResponse.model_validate(proposal)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# GET /audit-log — Agent action history
# ---------------------------------------------------------------------------

@router.get("/audit-log", response_model=List[AuditLogEntry])
async def get_audit_log(
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_async_db),
) -> list:
    logs = await _policy.get_audit_log(db, limit=limit, offset=offset)
    return [AuditLogEntry.model_validate(log) for log in logs]
