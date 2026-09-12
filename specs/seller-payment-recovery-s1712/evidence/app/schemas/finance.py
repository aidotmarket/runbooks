"""
Finance System Pydantic Schemas — BQ-FINANCIAL-SYSTEM Phase 1
=============================================================
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AccountType(str, Enum):
    asset = "asset"
    liability = "liability"
    equity = "equity"
    revenue = "revenue"
    expense = "expense"


class InvoiceStatus(str, Enum):
    draft = "draft"
    issued = "issued"
    paid = "paid"
    void = "void"
    overdue = "overdue"


class PaymentStatus(str, Enum):
    succeeded = "succeeded"
    pending = "pending"
    failed = "failed"
    refunded = "refunded"


class PeriodStatus(str, Enum):
    open = "open"
    closing = "closing"
    closed = "closed"


class AutonomyLevel(str, Enum):
    auto = "auto"
    propose = "propose"
    blocked = "blocked"


class SourceType(str, Enum):
    stripe_payment = "stripe_payment"
    invoice = "invoice"
    manual = "manual"
    reversal = "reversal"
    api_cost = "api_cost"
    credit_purchase = "credit_purchase"
    subscription = "subscription"


# ---------------------------------------------------------------------------
# GL / Chart of Accounts
# ---------------------------------------------------------------------------

class GLAccountResponse(BaseModel):
    id: UUID
    code: str
    name: str
    account_type: AccountType
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Journal Entries
# ---------------------------------------------------------------------------

class JournalLineResponse(BaseModel):
    account_code: str
    account_name: str
    debit_cents: int
    credit_cents: int
    memo: Optional[str] = None

    model_config = {"from_attributes": True}


class JournalEntryResponse(BaseModel):
    id: UUID
    entry_number: str
    entry_date: date
    posted_at: Optional[datetime] = None
    description: str
    source_type: str
    lines: List[JournalLineResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

class InvoiceLineCreate(BaseModel):
    description: str
    quantity: int = 1
    unit_price_cents: int
    gl_account_code: str


class InvoiceCreate(BaseModel):
    customer_id: UUID
    due_date: date
    lines: List[InvoiceLineCreate]
    notes: Optional[str] = None


class InvoiceLineResponse(BaseModel):
    id: UUID
    description: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    tax_rate_bps: int
    tax_cents: int

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    status: InvoiceStatus
    issue_date: date
    due_date: date
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    lines: List[InvoiceLineResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class PaymentResponse(BaseModel):
    id: UUID
    stripe_payment_intent_id: Optional[str] = None
    customer_id: UUID
    amount_cents: int
    currency: str
    status: PaymentStatus
    payment_method: Optional[str] = None
    received_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# GL Reports
# ---------------------------------------------------------------------------

class TrialBalance(BaseModel):
    entity_id: UUID
    as_of: date
    accounts: List[dict]   # [{code, name, type, debit_balance, credit_balance}]
    total_debits: int
    total_credits: int
    is_balanced: bool


class ProfitAndLoss(BaseModel):
    entity_id: UUID
    period_start: date
    period_end: date
    revenue: dict            # {commission, subscription, credits, enhancement, total}
    cost_of_revenue: dict    # {api, infra, payouts, total}
    gross_profit_cents: int
    expenses: dict           # {stripe_fees, infra, total}
    net_income_cents: int


class ReconciliationSummary(BaseModel):
    period: str
    matched_count: int
    unmatched_count: int
    matched_amount_cents: int
    unmatched_amount_cents: int
    discrepancy_cents: int


# ---------------------------------------------------------------------------
# Accounting Periods
# ---------------------------------------------------------------------------

class AccountingPeriodResponse(BaseModel):
    id: UUID
    year: int
    month: int
    status: PeriodStatus
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

class SubscriptionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    plan: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Finance Agent Typed Commands
# ---------------------------------------------------------------------------

class AgentCommand(BaseModel):
    """Base for all finance agent commands."""
    command_type: str
    idempotency_key: str = Field(..., description="Unique key to prevent duplicate execution")


class DraftInvoiceCommand(AgentCommand):
    command_type: str = "draft_invoice"
    customer_id: UUID
    line_items: List[InvoiceLineCreate]
    notes: Optional[str] = None


class ProposeRefundCommand(AgentCommand):
    command_type: str = "propose_refund"
    payment_id: UUID
    amount_cents: int
    reason: str


class RecordCostCommand(AgentCommand):
    command_type: str = "record_api_cost"
    provider: str
    amount_cents: int
    period_year: int
    period_month: int


class ProposeManualJournalCommand(AgentCommand):
    command_type: str = "propose_manual_journal"
    lines: List[dict] = Field(..., description="[{account_code, debit_cents, credit_cents, memo}]")
    description: str


class ProposeVoidInvoiceCommand(AgentCommand):
    command_type: str = "propose_void_invoice"
    invoice_id: UUID
    reason: str


class ProposePricingChangeCommand(AgentCommand):
    command_type: str = "propose_pricing_change"
    tier_type: str
    name: str
    min_threshold_cents: int = 0
    rate_bps: int


class ProposeCouponCommand(AgentCommand):
    command_type: str = "propose_coupon"
    code: str
    discount_type: str = Field(..., description="percentage or fixed_cents")
    discount_value: int
    applies_to: str = Field(..., description="commission, subscription, or credits")
    max_redemptions: Optional[int] = None
    valid_from: datetime
    valid_until: Optional[datetime] = None


class GetTrialBalanceCommand(AgentCommand):
    command_type: str = "get_trial_balance"
    as_of: Optional[date] = None


class GetPnlCommand(AgentCommand):
    command_type: str = "get_pnl"
    period_start: date
    period_end: date


class GetInvoiceListCommand(AgentCommand):
    command_type: str = "get_invoice_list"
    status: Optional[str] = None
    limit: int = 50


class GetPaymentListCommand(AgentCommand):
    command_type: str = "get_payment_list"
    status: Optional[str] = None
    limit: int = 50


class GetAccountsCommand(AgentCommand):
    command_type: str = "get_accounts"


class GetBalanceCommand(AgentCommand):
    command_type: str = "get_balance"
    account_code: str
    as_of: Optional[date] = None


class CalculatePricingCommand(AgentCommand):
    command_type: str = "calculate_pricing"
    tier_type: str
    amount_cents: int


class ValidateCouponCommand(AgentCommand):
    command_type: str = "validate_coupon"
    code: str


# ---------------------------------------------------------------------------
# Agent Proposal / Audit Responses
# ---------------------------------------------------------------------------

class ProposalResponse(BaseModel):
    id: UUID
    tool_name: str
    command_type: str
    input_payload: dict
    output_preview: Optional[dict] = None
    status: str
    created_by: str
    approved_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogEntry(BaseModel):
    id: UUID
    tool_name: str
    autonomy_level: str
    input_payload: dict
    output_payload: Optional[dict] = None
    status: str
    proposed_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    error: Optional[str] = None

    model_config = {"from_attributes": True}


class AgentCommandResult(BaseModel):
    """Standardized result from agent command execution."""
    autonomy_level: str
    status: str  # executed, proposed, blocked
    result: Optional[dict] = None
    proposal_id: Optional[UUID] = None
    message: str


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

class PricingTierCreate(BaseModel):
    tier_type: str
    name: str
    min_threshold_cents: int = 0
    rate_bps: int


class PricingTierResponse(BaseModel):
    id: UUID
    tier_type: str
    name: str
    min_threshold_cents: int
    rate_bps: int
    is_active: bool

    model_config = {"from_attributes": True}


class PricingCalculation(BaseModel):
    tier_type: str
    input_amount_cents: int
    rate_bps: int
    calculated_amount_cents: int
    tier_name: str


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------

class CouponCreate(BaseModel):
    code: str
    discount_type: str = Field(..., description="percentage or fixed_cents")
    discount_value: int
    applies_to: str = Field(..., description="commission, subscription, or credits")
    max_redemptions: Optional[int] = None
    valid_from: datetime
    valid_until: Optional[datetime] = None


class CouponResponse(BaseModel):
    id: UUID
    code: str
    discount_type: str
    discount_value: int
    applies_to: str
    max_redemptions: Optional[int] = None
    redemption_count: int
    valid_from: datetime
    valid_until: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CouponValidation(BaseModel):
    valid: bool
    code: str
    discount_type: Optional[str] = None
    discount_value: Optional[int] = None
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

class RevenueMetricsResponse(BaseModel):
    mrr_cents: int = 0
    arr_cents: int = 0
    commission_revenue_cents: int = 0
    credit_revenue_cents: int = 0
    subscription_revenue_cents: int = 0
    total_revenue_cents: int = 0
    period_start: date
    period_end: date


class PayoutResponse(BaseModel):
    id: UUID
    entry_number: str
    seller_name: str
    amount_cents: int
    status: str
    payout_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    customer_id: UUID
    plan: str
    stripe_subscription_id: Optional[str] = None
    current_period_start: datetime
    current_period_end: datetime
