"""
Finance System Phase 2 Tests — BQ-FINANCIAL-SYSTEM
====================================================

Tests cover:
1. PolicyEngine: AUTO/PROPOSE/BLOCKED classification
2. Approve/reject flow
3. Pricing calculation (correct cents, edge cases)
4. Coupon validation (valid/expired/max redemptions)
5. Subscription lifecycle
6. Audit log completeness
7. Integer cents enforced everywhere (Mandate M3)
8. Multi-entity tagged (issuing_entity_id, Mandate M1)
9. Stripe event processing
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

# ---------------------------------------------------------------------------
# Env setup (must happen before app imports)
# ---------------------------------------------------------------------------

import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-32chars!")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _mock_db() -> AsyncMock:
    """Return a mock AsyncSession."""
    db = AsyncMock()
    db._added: list = []

    async def mock_execute(query, *args, **kwargs):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        result.all.return_value = []
        return result

    db.execute = AsyncMock(side_effect=mock_execute)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()

    def mock_add(obj):
        db._added.append(obj)

    db.add = MagicMock(side_effect=mock_add)
    return db


# ---------------------------------------------------------------------------
# 1. PolicyEngine — AUTO/PROPOSE/BLOCKED classification
# ---------------------------------------------------------------------------

class TestPolicyEngineClassification:
    """PolicyEngine correctly classifies tools into AUTO/PROPOSE/BLOCKED."""

    def test_auto_tools_classified(self):
        from app.services.finance.policy_engine import classify
        auto_tools = [
            "get_trial_balance", "get_pnl", "get_invoice_list",
            "get_payment_list", "get_balance", "draft_invoice",
            "calculate_pricing", "validate_coupon", "get_accounts",
            "record_api_cost",
        ]
        for tool in auto_tools:
            assert classify(tool) == "auto", f"{tool} should be AUTO"

    def test_propose_tools_classified(self):
        from app.services.finance.policy_engine import classify
        propose_tools = [
            "propose_refund", "propose_credit_note",
            "propose_manual_journal", "propose_void_invoice",
            "propose_pricing_change", "propose_coupon",
        ]
        for tool in propose_tools:
            assert classify(tool) == "propose", f"{tool} should be PROPOSE"

    def test_blocked_tools_classified(self):
        from app.services.finance.policy_engine import classify
        blocked_tools = [
            "raw_journal_write", "edit_posted_entry",
            "delete_record", "reopen_closed_period", "self_approve",
        ]
        for tool in blocked_tools:
            assert classify(tool) == "blocked", f"{tool} should be BLOCKED"

    def test_unknown_tool_is_blocked(self):
        from app.services.finance.policy_engine import classify
        assert classify("unknown_dangerous_tool") == "blocked"

    def test_policy_engine_is_blocked_method(self):
        from app.services.finance.policy_engine import PolicyEngine
        pe = PolicyEngine()
        assert pe.is_blocked("raw_journal_write") is True
        assert pe.is_blocked("get_trial_balance") is False


# ---------------------------------------------------------------------------
# 2. Approve/reject flow
# ---------------------------------------------------------------------------

class TestApproveRejectFlow:
    """Agent proposals can be approved or rejected."""

    @pytest.mark.asyncio
    async def test_create_proposal(self):
        from app.services.finance.policy_engine import PolicyEngine
        from app.models.finance import FinanceAgentProposal

        pe = PolicyEngine()
        db = _mock_db()

        proposal = await pe.create_proposal(
            tool_name="propose_refund",
            command_type="propose_refund",
            payload={"payment_id": str(uuid.uuid4()), "amount_cents": 5000, "reason": "customer request"},
            idempotency_key=f"test-{uuid.uuid4()}",
            db=db,
        )

        # Proposal and audit log should be added
        proposals = [o for o in db._added if isinstance(o, FinanceAgentProposal)]
        assert len(proposals) == 1
        assert proposals[0].status == "pending"
        assert proposals[0].tool_name == "propose_refund"

    @pytest.mark.asyncio
    async def test_approve_proposal(self):
        from app.services.finance.policy_engine import PolicyEngine
        from app.models.finance import FinanceAgentProposal

        pe = PolicyEngine()
        db = _mock_db()

        # Mock finding a pending proposal
        mock_proposal = MagicMock(spec=FinanceAgentProposal)
        mock_proposal.id = uuid.uuid4()
        mock_proposal.status = "pending"
        mock_proposal.tool_name = "propose_refund"
        mock_proposal.input_payload = {"payment_id": str(uuid.uuid4()), "amount_cents": 5000}

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_proposal
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        approved, token, atype = await pe.approve_proposal(mock_proposal.id, "admin@test.com", db)

        assert approved.status == "approved"
        assert approved.approved_by == "admin@test.com"
        assert approved.approved_at is not None

    @pytest.mark.asyncio
    async def test_reject_proposal(self):
        from app.services.finance.policy_engine import PolicyEngine
        from app.models.finance import FinanceAgentProposal

        pe = PolicyEngine()
        db = _mock_db()

        mock_proposal = MagicMock(spec=FinanceAgentProposal)
        mock_proposal.id = uuid.uuid4()
        mock_proposal.status = "pending"
        mock_proposal.tool_name = "propose_refund"
        mock_proposal.input_payload = {"payment_id": str(uuid.uuid4())}

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_proposal
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        rejected = await pe.reject_proposal(
            mock_proposal.id, "admin@test.com", "Not authorized", db
        )

        assert rejected.status == "rejected"
        assert rejected.rejection_reason == "Not authorized"

    @pytest.mark.asyncio
    async def test_approve_non_pending_raises(self):
        from app.services.finance.policy_engine import PolicyEngine
        from app.models.finance import FinanceAgentProposal

        pe = PolicyEngine()
        db = _mock_db()

        mock_proposal = MagicMock(spec=FinanceAgentProposal)
        mock_proposal.id = uuid.uuid4()
        mock_proposal.status = "approved"  # already approved

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_proposal
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="not pending"):
            await pe.approve_proposal(mock_proposal.id, "admin@test.com", db)

    @pytest.mark.asyncio
    async def test_approve_not_found_raises(self):
        from app.services.finance.policy_engine import PolicyEngine

        pe = PolicyEngine()
        db = _mock_db()

        with pytest.raises(ValueError, match="not found"):
            await pe.approve_proposal(uuid.uuid4(), "admin@test.com", db)


# ---------------------------------------------------------------------------
# 3. Pricing calculation
# ---------------------------------------------------------------------------

class TestPricingService:
    """PricingService calculates fees correctly in integer cents."""

    @pytest.mark.asyncio
    async def test_calculate_with_single_tier(self):
        from app.services.finance.pricing_service import PricingService
        from app.models.finance import PricingTier

        svc = PricingService()
        db = _mock_db()

        mock_tier = MagicMock(spec=PricingTier)
        mock_tier.name = "Standard"
        mock_tier.min_threshold_cents = 0
        mock_tier.rate_bps = 1500  # 15%
        mock_tier.is_active = True

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalars.return_value.all.return_value = [mock_tier]
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.calculate("commission", 100000, db)  # $1000.00

        assert result["calculated_amount_cents"] == 15000  # $150.00
        assert result["rate_bps"] == 1500
        assert result["tier_name"] == "Standard"

    @pytest.mark.asyncio
    async def test_calculate_selects_highest_applicable_tier(self):
        from app.services.finance.pricing_service import PricingService
        from app.models.finance import PricingTier

        svc = PricingService()
        db = _mock_db()

        tier_low = MagicMock(spec=PricingTier)
        tier_low.name = "Standard"
        tier_low.min_threshold_cents = 0
        tier_low.rate_bps = 1500
        tier_low.is_active = True

        tier_high = MagicMock(spec=PricingTier)
        tier_high.name = "Premium"
        tier_high.min_threshold_cents = 50000  # $500
        tier_high.rate_bps = 1200  # 12% discount for higher volume
        tier_high.is_active = True

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalars.return_value.all.return_value = [tier_low, tier_high]
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.calculate("commission", 100000, db)

        assert result["tier_name"] == "Premium"
        assert result["rate_bps"] == 1200
        assert result["calculated_amount_cents"] == 12000

    @pytest.mark.asyncio
    async def test_calculate_no_tiers_raises(self):
        from app.services.finance.pricing_service import PricingService

        svc = PricingService()
        db = _mock_db()

        with pytest.raises(ValueError, match="No active pricing tiers"):
            await svc.calculate("nonexistent", 10000, db)

    @pytest.mark.asyncio
    async def test_calculate_integer_cents_no_floats(self):
        """Pricing calculation must return integer cents, never floats (Mandate M3)."""
        from app.services.finance.pricing_service import PricingService
        from app.models.finance import PricingTier

        svc = PricingService()
        db = _mock_db()

        mock_tier = MagicMock(spec=PricingTier)
        mock_tier.name = "Odd"
        mock_tier.min_threshold_cents = 0
        mock_tier.rate_bps = 333  # 3.33% — produces non-integer if using floats

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalars.return_value.all.return_value = [mock_tier]
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.calculate("commission", 10001, db)  # 10001 * 333 / 10000 = 333.0333

        assert isinstance(result["calculated_amount_cents"], int)
        assert result["calculated_amount_cents"] == 333  # floor via integer division

    @pytest.mark.asyncio
    async def test_create_tier(self):
        from app.services.finance.pricing_service import PricingService
        from app.models.finance import PricingTier

        svc = PricingService()
        db = _mock_db()

        tier = await svc.create_tier("commission", "Enterprise", 1000, db, min_threshold_cents=100000)

        created = [o for o in db._added if isinstance(o, PricingTier)]
        assert len(created) == 1
        assert created[0].name == "Enterprise"
        assert created[0].rate_bps == 1000


# ---------------------------------------------------------------------------
# 4. Coupon validation
# ---------------------------------------------------------------------------

class TestCouponService:
    """CouponService validates and redeems coupons correctly."""

    @pytest.mark.asyncio
    async def test_validate_valid_coupon(self):
        from app.services.finance.coupon_service import CouponService
        from app.models.finance import Coupon

        svc = CouponService()
        db = _mock_db()

        mock_coupon = MagicMock(spec=Coupon)
        mock_coupon.code = "SAVE20"
        mock_coupon.discount_type = "percentage"
        mock_coupon.discount_value = 20
        mock_coupon.valid_from = datetime.now(timezone.utc) - timedelta(days=1)
        mock_coupon.valid_until = datetime.now(timezone.utc) + timedelta(days=30)
        mock_coupon.max_redemptions = 100
        mock_coupon.redemption_count = 5

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_coupon
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.validate("SAVE20", db)
        assert result["valid"] is True
        assert result["discount_type"] == "percentage"
        assert result["discount_value"] == 20

    @pytest.mark.asyncio
    async def test_validate_expired_coupon(self):
        from app.services.finance.coupon_service import CouponService
        from app.models.finance import Coupon

        svc = CouponService()
        db = _mock_db()

        mock_coupon = MagicMock(spec=Coupon)
        mock_coupon.code = "EXPIRED"
        mock_coupon.valid_from = datetime.now(timezone.utc) - timedelta(days=60)
        mock_coupon.valid_until = datetime.now(timezone.utc) - timedelta(days=1)  # expired
        mock_coupon.max_redemptions = None
        mock_coupon.redemption_count = 0

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_coupon
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.validate("EXPIRED", db)
        assert result["valid"] is False
        assert result["reason"] == "Coupon expired"

    @pytest.mark.asyncio
    async def test_validate_max_redemptions_reached(self):
        from app.services.finance.coupon_service import CouponService
        from app.models.finance import Coupon

        svc = CouponService()
        db = _mock_db()

        mock_coupon = MagicMock(spec=Coupon)
        mock_coupon.code = "MAXED"
        mock_coupon.valid_from = datetime.now(timezone.utc) - timedelta(days=1)
        mock_coupon.valid_until = datetime.now(timezone.utc) + timedelta(days=30)
        mock_coupon.max_redemptions = 10
        mock_coupon.redemption_count = 10  # maxed out

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_coupon
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.validate("MAXED", db)
        assert result["valid"] is False
        assert result["reason"] == "Max redemptions reached"

    @pytest.mark.asyncio
    async def test_validate_nonexistent_coupon(self):
        from app.services.finance.coupon_service import CouponService

        svc = CouponService()
        db = _mock_db()

        result = await svc.validate("FAKE", db)
        assert result["valid"] is False
        assert result["reason"] == "Coupon not found"

    @pytest.mark.asyncio
    async def test_validate_not_yet_active(self):
        from app.services.finance.coupon_service import CouponService
        from app.models.finance import Coupon

        svc = CouponService()
        db = _mock_db()

        mock_coupon = MagicMock(spec=Coupon)
        mock_coupon.code = "FUTURE"
        mock_coupon.valid_from = datetime.now(timezone.utc) + timedelta(days=7)  # future
        mock_coupon.valid_until = None
        mock_coupon.max_redemptions = None
        mock_coupon.redemption_count = 0

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_coupon
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.validate("FUTURE", db)
        assert result["valid"] is False
        assert result["reason"] == "Coupon not yet active"

    @pytest.mark.asyncio
    async def test_redeem_percentage_coupon(self):
        from app.services.finance.coupon_service import CouponService
        from app.models.finance import Coupon, CouponRedemption

        svc = CouponService()
        db = _mock_db()

        mock_coupon = MagicMock(spec=Coupon)
        mock_coupon.id = uuid.uuid4()
        mock_coupon.code = "SAVE20"
        mock_coupon.discount_type = "percentage"
        mock_coupon.discount_value = 20
        mock_coupon.valid_from = datetime.now(timezone.utc) - timedelta(days=1)
        mock_coupon.valid_until = datetime.now(timezone.utc) + timedelta(days=30)
        mock_coupon.max_redemptions = 100
        mock_coupon.redemption_count = 5

        call_count = [0]

        async def mock_execute(query, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_coupon
            result.scalar_one.return_value = mock_coupon
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        customer_id = uuid.uuid4()
        redemption = await svc.redeem("SAVE20", customer_id, 10000, db)

        redemptions = [o for o in db._added if isinstance(o, CouponRedemption)]
        assert len(redemptions) == 1
        assert redemptions[0].discount_cents == 2000  # 20% of 10000

    @pytest.mark.asyncio
    async def test_redeem_fixed_coupon_capped(self):
        """Fixed discount cannot exceed the purchase amount."""
        from app.services.finance.coupon_service import CouponService
        from app.models.finance import Coupon, CouponRedemption

        svc = CouponService()
        db = _mock_db()

        mock_coupon = MagicMock(spec=Coupon)
        mock_coupon.id = uuid.uuid4()
        mock_coupon.code = "FLAT50"
        mock_coupon.discount_type = "fixed_cents"
        mock_coupon.discount_value = 5000  # $50 off
        mock_coupon.valid_from = datetime.now(timezone.utc) - timedelta(days=1)
        mock_coupon.valid_until = None
        mock_coupon.max_redemptions = None
        mock_coupon.redemption_count = 0

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_coupon
            result.scalar_one.return_value = mock_coupon
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        # Purchase only $30 — discount capped at $30
        await svc.redeem("FLAT50", uuid.uuid4(), 3000, db)

        redemptions = [o for o in db._added if isinstance(o, CouponRedemption)]
        assert redemptions[0].discount_cents == 3000  # capped at purchase amount


# ---------------------------------------------------------------------------
# 5. Subscription lifecycle
# ---------------------------------------------------------------------------

class TestSubscriptionService:
    """SubscriptionService manages subscription lifecycle."""

    @pytest.mark.asyncio
    async def test_create_subscription(self):
        from app.services.finance.subscription_service import SubscriptionService
        from app.models.finance import Subscription

        svc = SubscriptionService()
        db = _mock_db()

        now = datetime.now(timezone.utc)
        sub = await svc.create(
            customer_id=uuid.uuid4(),
            plan="pro",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            db=db,
        )

        created = [o for o in db._added if isinstance(o, Subscription)]
        assert len(created) == 1
        assert created[0].plan == "pro"
        assert created[0].status == "active"

    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(self):
        from app.services.finance.subscription_service import SubscriptionService
        from app.models.finance import Subscription

        svc = SubscriptionService()
        db = _mock_db()

        mock_sub = MagicMock(spec=Subscription)
        mock_sub.id = uuid.uuid4()
        mock_sub.status = "active"
        mock_sub.cancel_at_period_end = False

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_sub
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.cancel(mock_sub.id, db, immediate=False)

        assert result.cancel_at_period_end is True
        assert result.status == "active"  # stays active until period end

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediate(self):
        from app.services.finance.subscription_service import SubscriptionService
        from app.models.finance import Subscription

        svc = SubscriptionService()
        db = _mock_db()

        mock_sub = MagicMock(spec=Subscription)
        mock_sub.id = uuid.uuid4()
        mock_sub.status = "active"

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_sub
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await svc.cancel(mock_sub.id, db, immediate=True)
        assert result.status == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_already_canceled_raises(self):
        from app.services.finance.subscription_service import SubscriptionService
        from app.models.finance import Subscription

        svc = SubscriptionService()
        db = _mock_db()

        mock_sub = MagicMock(spec=Subscription)
        mock_sub.id = uuid.uuid4()
        mock_sub.status = "canceled"

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_sub
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="already canceled"):
            await svc.cancel(mock_sub.id, db)


# ---------------------------------------------------------------------------
# 6. Audit log completeness
# ---------------------------------------------------------------------------

class TestAuditLog:
    """All agent actions are audit logged."""

    @pytest.mark.asyncio
    async def test_auto_execution_creates_audit_log(self):
        from app.services.finance.policy_engine import PolicyEngine
        from app.models.finance import FinanceAgentAuditLog

        pe = PolicyEngine()
        db = _mock_db()

        await pe.execute_auto(
            tool_name="get_trial_balance",
            payload={"as_of": "2026-03-12"},
            handler_result={"total_debits": 0, "total_credits": 0},
            db=db,
        )

        logs = [o for o in db._added if isinstance(o, FinanceAgentAuditLog)]
        assert len(logs) == 1
        assert logs[0].tool_name == "get_trial_balance"
        assert logs[0].autonomy_level == "auto"
        assert logs[0].status == "executed"

    @pytest.mark.asyncio
    async def test_proposal_creates_audit_log(self):
        from app.services.finance.policy_engine import PolicyEngine
        from app.models.finance import FinanceAgentAuditLog

        pe = PolicyEngine()
        db = _mock_db()

        await pe.create_proposal(
            tool_name="propose_refund",
            command_type="propose_refund",
            payload={"payment_id": str(uuid.uuid4()), "amount_cents": 5000},
            idempotency_key=f"audit-test-{uuid.uuid4()}",
            db=db,
        )

        logs = [o for o in db._added if isinstance(o, FinanceAgentAuditLog)]
        assert len(logs) == 1
        assert logs[0].status == "proposed"

    @pytest.mark.asyncio
    async def test_approval_creates_audit_log(self):
        from app.services.finance.policy_engine import PolicyEngine
        from app.models.finance import FinanceAgentProposal, FinanceAgentAuditLog

        pe = PolicyEngine()
        db = _mock_db()

        mock_proposal = MagicMock(spec=FinanceAgentProposal)
        mock_proposal.id = uuid.uuid4()
        mock_proposal.status = "pending"
        mock_proposal.tool_name = "propose_refund"
        mock_proposal.input_payload = {"amount_cents": 5000}

        async def mock_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_proposal
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        await pe.approve_proposal(mock_proposal.id, "admin@test.com", db)

        logs = [o for o in db._added if isinstance(o, FinanceAgentAuditLog)]
        assert len(logs) == 1
        assert logs[0].status == "approved"
        assert logs[0].approved_by == "admin@test.com"


# ---------------------------------------------------------------------------
# 7. Integer cents enforced everywhere (Mandate M3)
# ---------------------------------------------------------------------------

class TestIntegerCentsPhase2:
    """All Phase 2 monetary amounts use integer cents (Mandate M3)."""

    def test_agent_proposal_no_float_columns(self):
        import sqlalchemy as sa
        from app.models.finance import FinanceAgentProposal
        for col in FinanceAgentProposal.__table__.columns:
            assert not isinstance(col.type, sa.Float), \
                f"FinanceAgentProposal.{col.name} must not be Float (Mandate M3)"
            assert not isinstance(col.type, sa.Numeric), \
                f"FinanceAgentProposal.{col.name} must not be Numeric (Mandate M3)"

    def test_pricing_tier_no_float_columns(self):
        import sqlalchemy as sa
        from app.models.finance import PricingTier
        for col in PricingTier.__table__.columns:
            assert not isinstance(col.type, sa.Float), \
                f"PricingTier.{col.name} must not be Float"

    def test_coupon_no_float_columns(self):
        import sqlalchemy as sa
        from app.models.finance import Coupon
        for col in Coupon.__table__.columns:
            assert not isinstance(col.type, sa.Float), \
                f"Coupon.{col.name} must not be Float"

    def test_coupon_redemption_discount_is_biginteger(self):
        import sqlalchemy as sa
        from app.models.finance import CouponRedemption
        col = CouponRedemption.__table__.columns["discount_cents"]
        assert isinstance(col.type, sa.BigInteger), \
            "CouponRedemption.discount_cents must be BigInteger"

    def test_subscription_no_float_columns(self):
        import sqlalchemy as sa
        from app.models.finance import Subscription
        for col in Subscription.__table__.columns:
            assert not isinstance(col.type, sa.Float), \
                f"Subscription.{col.name} must not be Float"

    def test_pricing_calculation_uses_integer_division(self):
        """Verify the calculation formula uses // not /."""
        import inspect
        from app.services.finance.pricing_service import PricingService
        source = inspect.getsource(PricingService.calculate)
        assert "//" in source, "PricingService.calculate must use integer division (//)"
        # Should not have bare / for amount calculation
        # (We check that // is used, which is the critical guarantee)


# ---------------------------------------------------------------------------
# 8. Multi-entity tagged (Mandate M1)
# ---------------------------------------------------------------------------

class TestMultiEntityPhase2:
    """All Phase 2 models have entity_id (Mandate M1)."""

    def test_agent_proposal_has_entity_id(self):
        from app.models.finance import FinanceAgentProposal
        cols = {c.name for c in FinanceAgentProposal.__table__.columns}
        assert "entity_id" in cols, "FinanceAgentProposal missing entity_id (Mandate M1)"

    def test_pricing_tier_has_entity_id(self):
        from app.models.finance import PricingTier
        cols = {c.name for c in PricingTier.__table__.columns}
        assert "entity_id" in cols, "PricingTier missing entity_id (Mandate M1)"

    def test_coupon_has_entity_id(self):
        from app.models.finance import Coupon
        cols = {c.name for c in Coupon.__table__.columns}
        assert "entity_id" in cols, "Coupon missing entity_id (Mandate M1)"

    def test_subscription_has_entity_id(self):
        from app.models.finance import Subscription
        cols = {c.name for c in Subscription.__table__.columns}
        assert "entity_id" in cols, "Subscription missing entity_id (Mandate M1)"


# ---------------------------------------------------------------------------
# 9. Stripe event processing
# ---------------------------------------------------------------------------

class TestStripeEventProcessing:
    """PaymentService.record_stripe_event processes webhook events into GL."""

    @pytest.mark.asyncio
    async def test_payment_intent_succeeded(self):
        from app.services.finance.payment_service import PaymentService
        from app.models.finance import Payment, JournalEntry, AccountingPeriod, GLAccount

        svc = PaymentService()
        db = _mock_db()

        customer_id = str(uuid.uuid4())

        # Mock: no existing payment, then period, then account lookups
        mock_payment = MagicMock(spec=Payment)
        mock_payment.id = uuid.uuid4()
        mock_payment.journal_entry_id = None

        mock_period = MagicMock(spec=AccountingPeriod)
        mock_period.id = uuid.uuid4()

        mock_account_1000 = MagicMock(spec=GLAccount)
        mock_account_1000.id = uuid.uuid4()
        mock_account_1000.code = "1000"

        mock_account_4000 = MagicMock(spec=GLAccount)
        mock_account_4000.id = uuid.uuid4()
        mock_account_4000.code = "4000"

        call_count = [0]

        async def mock_execute(query, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # Check for existing payment — none
                result.scalar_one_or_none.return_value = None
            elif call_count[0] == 2:
                # Get or create period
                result.scalar_one_or_none.return_value = mock_period
            else:
                # Bulk GL account lookup via scalars().all()
                result.scalars.return_value.all.return_value = [mock_account_1000, mock_account_4000]
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        event_data = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "amount": 50000,
                    "currency": "usd",
                    "metadata": {
                        "customer_id": customer_id,
                        "payment_type": "commission",
                        "order_id": str(uuid.uuid4()),
                    },
                    "payment_method_types": ["card"],
                    "charges": {"data": []},
                }
            },
        }

        result = await svc.record_stripe_event(event_data, db)
        assert result["status"] == "processed"
        assert "payment_id" in result

    @pytest.mark.asyncio
    async def test_unknown_event_type_ignored(self):
        from app.services.finance.payment_service import PaymentService

        svc = PaymentService()
        db = _mock_db()

        result = await svc.record_stripe_event(
            {"type": "customer.created", "data": {"object": {}}},
            db,
        )
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_missing_customer_id_skipped(self):
        from app.services.finance.payment_service import PaymentService

        svc = PaymentService()
        db = _mock_db()

        result = await svc.record_stripe_event(
            {
                "type": "payment_intent.succeeded",
                "data": {"object": {"id": "pi_test", "amount": 1000, "metadata": {}}},
            },
            db,
        )
        assert result["status"] == "skipped"
        assert "customer_id" in result["reason"]


# ---------------------------------------------------------------------------
# 10. Schema validation
# ---------------------------------------------------------------------------

class TestPhase2Schemas:
    """Phase 2 Pydantic schemas validate correctly."""

    def test_agent_command_base(self):
        from app.schemas.finance import AgentCommand
        cmd = AgentCommand(command_type="test", idempotency_key="key-1")
        assert cmd.idempotency_key == "key-1"

    def test_propose_refund_command(self):
        from app.schemas.finance import ProposeRefundCommand
        cmd = ProposeRefundCommand(
            payment_id=uuid.uuid4(),
            amount_cents=5000,
            reason="duplicate charge",
            idempotency_key="ref-1",
        )
        assert cmd.command_type == "propose_refund"
        assert cmd.amount_cents == 5000

    def test_pricing_tier_create(self):
        from app.schemas.finance import PricingTierCreate
        tier = PricingTierCreate(tier_type="commission", name="Standard", rate_bps=1500)
        assert tier.rate_bps == 1500

    def test_coupon_create(self):
        from app.schemas.finance import CouponCreate
        coupon = CouponCreate(
            code="SAVE20",
            discount_type="percentage",
            discount_value=20,
            applies_to="commission",
            valid_from=datetime.now(timezone.utc),
        )
        assert coupon.discount_type == "percentage"

    def test_subscription_create(self):
        from app.schemas.finance import SubscriptionCreate
        now = datetime.now(timezone.utc)
        sub = SubscriptionCreate(
            customer_id=uuid.uuid4(),
            plan="pro",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        assert sub.plan == "pro"

    def test_agent_command_result(self):
        from app.schemas.finance import AgentCommandResult
        result = AgentCommandResult(
            autonomy_level="auto",
            status="executed",
            result={"total_debits": 0},
            message="OK",
        )
        assert result.status == "executed"

    def test_proposal_response(self):
        from app.schemas.finance import ProposalResponse
        resp = ProposalResponse(
            id=uuid.uuid4(),
            tool_name="propose_refund",
            command_type="propose_refund",
            input_payload={"amount_cents": 5000},
            status="pending",
            created_by="finance_agent",
            created_at=datetime.now(timezone.utc),
        )
        assert resp.status == "pending"

    def test_audit_log_entry(self):
        from app.schemas.finance import AuditLogEntry
        entry = AuditLogEntry(
            id=uuid.uuid4(),
            tool_name="get_trial_balance",
            autonomy_level="auto",
            input_payload={},
            status="executed",
            proposed_at=datetime.now(timezone.utc),
        )
        assert entry.autonomy_level == "auto"


# ---------------------------------------------------------------------------
# 11. Router import test
# ---------------------------------------------------------------------------

class TestFinanceAgentRouter:
    """Finance agent router is importable and has expected endpoints."""

    def test_router_imports(self):
        from app.routers.finance_agent import router
        assert router.prefix == "/api/v1/finance/agent"

    def test_router_has_expected_routes(self):
        from app.routers.finance_agent import router
        paths = {r.path for r in router.routes}
        prefix = router.prefix
        assert f"{prefix}/command" in paths
        assert f"{prefix}/pending" in paths
        assert f"{prefix}/approve/{{proposal_id}}" in paths
        assert f"{prefix}/reject/{{proposal_id}}" in paths
        assert f"{prefix}/audit-log" in paths


@pytest.mark.asyncio
async def test_dormant_direct_refund_route_refuses_before_any_db_write():
    from app.services.finance.payment_service import PaymentService
    db = _mock_db()
    with pytest.raises(ValueError, match="refund_processing_service"):
        await PaymentService().record_stripe_event(
            {"type": "charge.refunded", "data": {"object": {}}}, db)
    db.execute.assert_not_called()
    db.flush.assert_not_called()
