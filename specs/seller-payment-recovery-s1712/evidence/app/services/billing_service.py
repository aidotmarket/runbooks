"""
Billing Service
===============

PURPOSE:
    Manage prepaid credits, calculate costs, and handle escrow hold states.
    
ARCHITECTURE:
    Fully async using SQLAlchemy AsyncSession.
    All database operations use await for non-blocking I/O.
    
NOTES:
    All amounts in CENTS to avoid floating point issues.
    Markup percentages stored in api_settings table.
    
REFACTORED:
    S44 (2026-01-27) - TD-003: Converted from "fake async" to true async.
    S58 (2026-01-31) - P2.2: Added escrow hold state functionality.
    Previous version used sync Session inside async functions, blocking event loop.
"""

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from uuid import UUID, uuid4
from typing import Tuple, Dict, Any, Optional

from app.models.gateway import APICredits, APISettings, APIUsage, CreditReservation
from app.models.finance import BillingEntity, Payment, Refund, StripeEvent
from app.services.finance.engine import FinanceEngine
from app.services.api_credit_availability import available_api_credits

logger = logging.getLogger(__name__)

ALLAI_BILLING_TRIAL_THEN_PAY = "trial_then_pay"
ALLAI_BILLING_MONTHLY_FREE_CAP = "monthly_free_cap"


class BillingService:
    """
    Async billing service for credit management and escrow operations.
    
    All methods require an AsyncSession from get_async_db dependency.
    """

    def __init__(self) -> None:
        self._finance_engine = FinanceEngine()
        self._default_entity_code = os.getenv("BILLING_ENTITY_CODE", "AIM_WY_LLC")
        self._finance_agent = None

    async def _get_finance_agent(self):
        if self._finance_agent is None:
            from app.allai.agents.finance.agent import FinanceAgent

            self._finance_agent = FinanceAgent()
        return self._finance_agent

    async def _resolve_crm_party_id(
        self,
        *,
        metadata: Dict[str, Any],
        user_id: Optional[UUID],
        customer_ref: Optional[str],
    ) -> Optional[str]:
        direct_id = metadata.get("party_id") or metadata.get("crm_party_id")
        if direct_id:
            return str(direct_id)
        if metadata.get("crm_entity_id") or metadata.get("crm_contact_id"):
            logger.warning(
                "BillingService: ignoring legacy CRM metadata aliases; provide party_id/crm_party_id"
            )

        finance_agent = await self._get_finance_agent()
        query_candidates = [
            metadata.get("customer_email"),
            customer_ref,
            metadata.get("customer_id"),
            str(user_id) if user_id else None,
        ]
        for candidate in query_candidates:
            if not candidate:
                continue
            response = await finance_agent.request_peer(
                target_agent_key="crm-steward",
                skill_name="find_contact",
                input_data={"query": str(candidate), "limit": 1},
                reason="finance_transaction_crm_lookup",
            )
            if not response.success:
                continue
            results = (response.data or {}).get("results") or []
            if results and (results[0].get("party_id") or results[0].get("id")):
                if not results[0].get("party_id"):
                    logger.warning(
                        "BillingService: finance-agent result lacked party_id; falling back to bare id field"
                    )
                return str(results[0].get("party_id") or results[0]["id"])
        return None

    async def _log_transaction_to_crm(
        self,
        *,
        event_type: str,
        metadata: Dict[str, Any],
        user_id: Optional[UUID],
        payment_id: UUID,
        amount_cents: int,
        currency: str,
        journal_entry_id: Optional[UUID] = None,
        refund_id: Optional[UUID] = None,
        customer_ref: Optional[str] = None,
    ) -> None:
        try:
            party_id = await self._resolve_crm_party_id(
                metadata=metadata,
                user_id=user_id,
                customer_ref=customer_ref,
            )
            if not party_id:
                logger.info(
                    "BillingService: skipping CRM transaction log for %s; no CRM party matched",
                    event_type,
                )
                return

            finance_agent = await self._get_finance_agent()
            content = (
                f"Processed {event_type}: payment_id={payment_id}, amount_cents={amount_cents}, "
                f"currency={currency}, journal_entry_id={journal_entry_id}, refund_id={refund_id}."
            )
            response = await finance_agent.request_peer(
                target_agent_key="crm-steward",
                skill_name="add_note",
                input_data={
                    "party_id": party_id,
                    "content": content,
                    "interaction_type": "transaction",
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                },
                reason="finance_transaction_crm_log",
            )
            if not response.success:
                logger.warning(
                    "BillingService: CRM transaction log denied/failed for %s: %s",
                    event_type,
                    response.error,
                )
        except Exception:
            logger.warning(
                "BillingService: CRM transaction log failed for %s",
                event_type,
                exc_info=True,
            )
    
    async def get_balance(self, user_id: UUID, db: AsyncSession) -> Dict[str, Any]:
        """
        Get current credit balance.
        
        Returns:
            {
                "balance_cents": int,
                "free_trial_remaining_cents": int,
                "billing_mode": str,
                "total_used_cents": int
            }
        """
        credits = await available_api_credits(db, user_id)
        
        if not credits:
            # Should exist if user has key, but handle edge case
            return {
                "balance_cents": 0,
                "free_trial_remaining_cents": 0,
                "billing_mode": "prepaid",
                "total_used_cents": 0
            }

        if (credits.allai_billing_mode or ALLAI_BILLING_TRIAL_THEN_PAY) == ALLAI_BILLING_MONTHLY_FREE_CAP:
            anchor = self._current_month_anchor()
            spent = (
                int(credits.allai_month_spent_cents or 0)
                if self._same_calendar_month(credits.allai_month_anchor, anchor)
                else 0
            )
            cap = max(0, int(credits.allai_monthly_cap_cents or 0))
            remaining = max(0, cap - spent) if credits.allai_allowance_enabled else 0
            return {
                "balance_cents": 0,
                "free_trial_remaining_cents": remaining,
                "billing_mode": ALLAI_BILLING_MONTHLY_FREE_CAP,
                "total_used_cents": credits.total_used_cents,
                "allai_month_spent_cents": spent,
                "allai_monthly_cap_cents": cap,
            }
            
        remaining_trial = max(0, credits.free_trial_cents - credits.free_trial_used_cents)
        
        return {
            "balance_cents": credits.balance_cents,
            "free_trial_remaining_cents": remaining_trial,
            "billing_mode": credits.billing_mode,
            "total_used_cents": credits.total_used_cents
        }

    async def _get_active_billing_entity(
        self,
        db: AsyncSession,
        entity_id: Optional[UUID] = None,
    ) -> BillingEntity:
        if entity_id is not None:
            result = await db.execute(
                select(BillingEntity).where(BillingEntity.id == entity_id)
            )
            entity = result.scalar_one_or_none()
            if entity is None:
                raise ValueError(f"Billing entity {entity_id} not found")
            return entity

        result = await db.execute(
            select(BillingEntity).where(
                BillingEntity.code == self._default_entity_code,
                BillingEntity.is_active.is_(True),
            )
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            raise ValueError(
                f"Active billing entity with code {self._default_entity_code!r} not found"
            )
        return entity

    async def _get_or_create_api_credits(
        self,
        user_id: UUID,
        entity_id: UUID,
        db: AsyncSession,
    ) -> APICredits:
        result = await db.execute(
            select(APICredits)
            .where(APICredits.user_id == user_id)
            .with_for_update()
        )
        credits = result.scalars().first()
        if credits is None:
            credits = APICredits(user_id=user_id, entity_id=entity_id)
            db.add(credits)
            await db.flush()
        elif getattr(credits, "entity_id", None) is None:
            credits.entity_id = entity_id
        return credits

    @staticmethod
    def _current_month_anchor(now: Optional[datetime] = None) -> datetime:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    @staticmethod
    def _same_calendar_month(left: Optional[datetime], right: datetime) -> bool:
        if left is None:
            return False
        if left.tzinfo is None:
            left = left.replace(tzinfo=timezone.utc)
        return left.year == right.year and left.month == right.month

    def _roll_allai_month_if_needed(
        self,
        credits: APICredits,
        *,
        now: Optional[datetime] = None,
    ) -> None:
        anchor = self._current_month_anchor(now)
        if not self._same_calendar_month(credits.allai_month_anchor, anchor):
            credits.allai_month_spent_cents = 0
            credits.allai_month_anchor = anchor

    async def check_allai_monthly_allowance(
        self,
        user_id: UUID,
        db: AsyncSession,
        *,
        entity_id: Optional[UUID] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Lock the credit row, roll the monthly anchor if needed, and evaluate
        the allAI monthly-free-cap preflight without touching Stripe/balance.
        """
        current_result = await db.execute(
            select(APICredits).where(APICredits.user_id == user_id)
        )
        current = current_result.scalars().first()
        if current is None:
            return {
                "mode": ALLAI_BILLING_TRIAL_THEN_PAY,
                "allowed": True,
                "reason": None,
            }
        mode = current.allai_billing_mode or ALLAI_BILLING_TRIAL_THEN_PAY
        if mode != ALLAI_BILLING_MONTHLY_FREE_CAP:
            return {"mode": mode, "allowed": True, "reason": None}

        entity = await self._get_active_billing_entity(db, entity_id=entity_id)
        credits = await self._get_or_create_api_credits(
            user_id=user_id,
            entity_id=entity.id,
            db=db,
        )
        self._roll_allai_month_if_needed(credits, now=now)
        cap = max(0, int(credits.allai_monthly_cap_cents or 0))
        spent = max(0, int(credits.allai_month_spent_cents or 0))
        enabled = bool(credits.allai_allowance_enabled)
        remaining = max(0, cap - spent) if enabled else 0
        await db.commit()

        if not enabled:
            return {
                "mode": mode,
                "allowed": False,
                "reason": "monthly_allowance_disabled",
                "remaining_cents": 0,
                "month_spent_cents": spent,
                "cap_cents": cap,
            }
        if spent >= cap:
            return {
                "mode": mode,
                "allowed": False,
                "reason": "monthly_allowance_reached",
                "remaining_cents": 0,
                "month_spent_cents": spent,
                "cap_cents": cap,
            }
        return {
            "mode": mode,
            "allowed": True,
            "reason": None,
            "remaining_cents": remaining,
            "month_spent_cents": spent,
            "cap_cents": cap,
        }

    async def record_allai_monthly_usage_once(
        self,
        *,
        key_record: Any,
        request_id: str,
        usage: Dict[str, int],
        vendor_cost_cents: int,
        customer_cost_cents: int,
        model: str,
        response_time_ms: int,
        db: AsyncSession,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Atomically bind a monthly-free-cap spend increment to one APIUsage row.

        Retries with the same request id return the existing usage result and
        do not increment allai_month_spent_cents again.
        """
        idempotency_key = f"monthly_cap:{request_id}"
        entity = await self._get_active_billing_entity(db)
        credits = await self._get_or_create_api_credits(
            user_id=key_record.user_id,
            entity_id=entity.id,
            db=db,
        )
        self._roll_allai_month_if_needed(credits, now=now)

        cap = max(0, int(credits.allai_monthly_cap_cents or 0))
        spent = max(0, int(credits.allai_month_spent_cents or 0))

        existing = await db.execute(
            select(APIUsage).where(
                APIUsage.user_id == key_record.user_id,
                APIUsage.service == "allie",
                APIUsage.request_type == idempotency_key,
            )
        )
        existing_usage = existing.scalars().first()

        if existing_usage:
            remaining = max(0, cap - spent) if credits.allai_allowance_enabled else 0
            await db.commit()
            return {
                "idempotent": True,
                "absorbed_cents": existing_usage.customer_cost_cents,
                "remaining_cents": remaining,
                "month_spent_cents": spent,
            }

        absorbed_cents = min(max(0, customer_cost_cents), max(0, cap - spent))
        credits.allai_month_spent_cents = spent + absorbed_cents

        usage_log = APIUsage(
            user_id=key_record.user_id,
            api_key_id=key_record.id,
            service="allie",
            endpoint=model,
            request_type=idempotency_key,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            vendor_cost_cents=vendor_cost_cents,
            customer_cost_cents=absorbed_cents,
            free_trial_used=False,
            status_code=200,
            response_time_ms=response_time_ms,
        )
        db.add(usage_log)
        await db.commit()

        month_spent = spent + absorbed_cents
        return {
            "idempotent": False,
            "absorbed_cents": absorbed_cents,
            "remaining_cents": max(0, cap - month_spent),
            "month_spent_cents": month_spent,
        }

    async def _record_credit_topup(
        self,
        user_id: UUID,
        entity_id: UUID,
        payment: Payment,
        journal_entry_id: UUID,
        credit_cents: int,
        customer_ref: Optional[str],
        db: AsyncSession,
    ) -> APICredits:
        credits = await self._get_or_create_api_credits(user_id=user_id, entity_id=entity_id, db=db)
        credits.balance_cents += credit_cents
        credits.total_purchased_cents += credit_cents
        credits.last_topup_payment_id = payment.id
        credits.last_journal_entry_id = journal_entry_id
        credits.customer_ref = customer_ref
        credits.last_topup_at = datetime.now(timezone.utc)
        await db.flush()
        return credits

    async def handle_stripe_event(
        self,
        event: Dict[str, Any],
        db: AsyncSession,
        *,
        signature_valid: bool = True,
    ) -> Dict[str, Any]:
        event_id = event["id"]
        event_type = event["type"]
        event_object = event.get("data", {}).get("object", {})
        metadata = event_object.get("metadata", {}) or {}

        from app.services.order_money_service import resolve_order_id, lock_order_money
        from app.services.refund_processing_service import process_order_refund, ensure_order_capture
        if event_type == 'charge.refunded':
            if not signature_valid:
                raise ValueError('Refund signature required')
            # Processor acquires the event before any order/Payment. Persist a
            # provenance row only for this trusted signed service entrypoint.
            row=(await db.execute(select(StripeEvent).where(StripeEvent.stripe_event_id==event_id)
                .with_for_update())).scalar_one_or_none()
            if row is None:
                db.add(StripeEvent(stripe_event_id=event_id,event_type=event_type,payload_json=event,
                    signature_valid=True,processed_status='received'))
                await db.flush()
            return await process_order_refund(db,event)
        if event_type in {'payment_intent.succeeded','payment_intent.payment_failed'}:
            import asyncio, stripe
            from app.core.stripe_async import run_stripe
            from app.services.order_money_service import (
                locate_agent_event_sync, _locked_initial_pair, validate_agent_pair, compare_agent_evidence,
                agent_provider_evidence, ExpectedPaymentBinding, bind_initial_order_payment_intent_sync,
                transition_agent_attempt_sync, OrderMoneyConflict, payment_database_phase)
            agent_oid = await db.run_sync(lambda sync: locate_agent_event_sync(sync,event_object))
            oid = agent_oid or await resolve_order_id(db,event_object.get('id'),metadata=metadata)
            if oid is not None and (agent_oid is not None or event_type == 'payment_intent.succeeded'):
                if not signature_valid or event.get('account'):
                    raise ValueError('Canonical capture signature/platform scope required')
                await db.rollback()
                async with asyncio.timeout(20):
                    async with asyncio.timeout(10):
                        pi = await run_stripe(stripe.PaymentIntent.retrieve,event_object['id'])
                    ch = None
                    if event_type == 'payment_intent.succeeded':
                        async with asyncio.timeout(10):
                            ch = await run_stripe(stripe.Charge.retrieve,pi['latest_charge'])
                evidence = (agent_provider_evidence(pi,source='signed_event_and_provider_read',
                    account=event.get('account'),signed_event_id=event_id) if agent_oid else None)
                if (pi.get('id') != event_object.get('id')
                        or type(event.get('livemode')) is not bool
                        or pi.get('livemode') is not event['livemode']
                        or pi.get('metadata') != metadata
                        or (agent_oid is not None and (
                            event_object.get('amount') != evidence.amount_cents
                            or type(event_object.get('amount')) is not int
                            or event_object.get('currency') != evidence.currency))):
                    raise OrderMoneyConflict('Original signed/provider binding mismatch')
                async with payment_database_phase(db):
                    await db.execute(text("SET LOCAL lock_timeout='250ms'"))
                    await db.execute(text("SET LOCAL statement_timeout='2000ms'"))
                    row = (await db.execute(select(StripeEvent).where(StripeEvent.stripe_event_id==event_id)
                        .with_for_update())).scalar_one_or_none()
                    if row is None:
                        row = StripeEvent(stripe_event_id=event_id,event_type=event_type,payload_json=event,
                            signature_valid=True,processed_status='received')
                        db.add(row)
                        await db.flush()
                    elif (row.payload_json != event or row.signature_valid is not True
                          or row.event_type != event_type):
                        raise ValueError('Canonical capture event binding changed')
                    order, tx = await db.run_sync(lambda sync: _locked_initial_pair(sync,oid))
                    attempt = None
                    if agent_oid:
                        attempt = validate_agent_pair(order,tx)
                        compare_agent_evidence(attempt,evidence)
                        if event_type == 'payment_intent.payment_failed':
                            if attempt['state'] == 'completed':
                                # A reordered failure cannot erase captured finance.
                                row.processed_status = 'processed'
                                await db.flush()
                                return {'stripe_event_id':event_id,'processed_status':'processed'}
                            if attempt['state'] != 'cancelled_reconciled':
                                if evidence.provider_status != 'canceled':
                                    raise OrderMoneyConflict('Failure event is not terminal no-liability proof')
                                from dataclasses import replace
                                read_evidence=replace(evidence,source='provider_read',signed_event_id=None)
                                binding = ExpectedPaymentBinding(UUID(str(order.id)),UUID(str(tx.id)),None,None,evidence.payment_intent_id,
                                    evidence.amount_cents,evidence.currency.upper(),UUID(str(order.buyer_id)),UUID(str(order.seller_id)),
                                    UUID(str(order.listing_id)),order.platform_fee_cents,order.seller_amount_cents)
                                await db.run_sync(lambda sync: bind_initial_order_payment_intent_sync(sync,
                                    order_id=order.id,payment_intent_id=evidence.payment_intent_id,
                                    expected_transaction_id=tx.id,mode='agent_attempt_completion',expected_binding=binding,
                                    expected_agent_attempt_id=UUID(attempt['attempt_id']),expected_agent_attempt_revision=attempt['revision'],
                                    provider_evidence=evidence))
                                await db.run_sync(lambda sync: transition_agent_attempt_sync(sync,order,tx,
                                    state='cancelled_reconciled',evidence=read_evidence,release=True))
                            row.processed_status='processed'
                            await db.flush()
                            return {'stripe_event_id':event_id,'processed_status':'processed'}
                        if evidence.provider_status != 'succeeded':
                            raise OrderMoneyConflict('Signed success lacks successful provider evidence')
                        binding = ExpectedPaymentBinding(UUID(str(order.id)),UUID(str(tx.id)),None,None,evidence.payment_intent_id,
                            evidence.amount_cents,evidence.currency.upper(),UUID(str(order.buyer_id)),UUID(str(order.seller_id)),
                            UUID(str(order.listing_id)),order.platform_fee_cents,order.seller_amount_cents)
                        await db.run_sync(lambda sync: bind_initial_order_payment_intent_sync(sync,
                            order_id=order.id,payment_intent_id=evidence.payment_intent_id,
                            expected_transaction_id=tx.id,mode='agent_attempt_completion',expected_binding=binding,
                            expected_agent_attempt_id=UUID(attempt['attempt_id']),expected_agent_attempt_revision=attempt['revision'],
                            provider_evidence=evidence))
                        if attempt['state'] != 'completed':
                            await db.run_sync(lambda sync: transition_agent_attempt_sync(sync,order,tx,state='bound_pending',evidence=evidence))
                    elif tx is not None and tx.stripe_payment_intent_id is None:
                        if (pi.get('id') != event_object.get('id') or pi.get('metadata') != metadata
                                or metadata.get('order_id') != str(order.id) or metadata.get('transaction_id') != str(tx.id)
                                or pi.get('livemode') is not event.get('livemode') or pi.get('status') != 'succeeded'):
                            raise OrderMoneyConflict('Original signed recovery provider mismatch')
                        session_id = order.stripe_checkout_session_id
                        original_session = await db.scalar(text("""SELECT payload_json #>> '{data,object,id}'
                            FROM stripe_events WHERE event_type='checkout.session.completed' AND status='completed'
                            AND signature_valid IS TRUE AND payload_json #>> '{data,object,payment_intent}'=:pi
                            AND payload_json #>> '{data,object,id}'=:sid ORDER BY stripe_event_id LIMIT 1"""),
                            {'pi':pi['id'],'sid':session_id})
                        binding = ExpectedPaymentBinding(UUID(str(order.id)),UUID(str(tx.id)),session_id,original_session,pi['id'],
                            pi.get('amount'),pi.get('currency','').upper(),UUID(str(order.buyer_id)),UUID(str(order.seller_id)),
                            UUID(str(order.listing_id)),order.platform_fee_cents,order.seller_amount_cents)
                        await db.run_sync(lambda sync: bind_initial_order_payment_intent_sync(sync,
                            order_id=order.id,payment_intent_id=pi['id'],expected_transaction_id=tx.id,
                            mode='signed_capture_recovery',expected_binding=binding))
                    money = await lock_order_money(db,oid)
                    payment = await ensure_order_capture(db,order=money.order,transaction=money.transaction,
                        provider_payment=pi,provider_charge=ch,origin='payment_event',locked=money)
                    if agent_oid and attempt['state'] != 'completed':
                        from app.services.order_service import OrderService
                        await OrderService(db)._complete_paid_order(oid,pi['id'],auto_commit=False)
                        await db.execute(text("UPDATE transactions SET paid_at=COALESCE(paid_at,NOW()) WHERE id=:id"),{'id':tx.id})
                        await db.refresh(tx,attribute_names=['status','paid_at'])
                        await db.run_sync(lambda sync: transition_agent_attempt_sync(sync,order,tx,state='completed',evidence=evidence))
                    row.entity_id = payment.entity_id
                    row.payload_json = event
                    row.signature_valid = True
                    row.processed_status = 'processed'
                    row.processed_at = datetime.now(timezone.utc)
                    await db.flush()
                    return {'stripe_event_id':event_id,'processed_status':'processed','payment_id':str(payment.id)}

        entity = await self._get_active_billing_entity(
            db,
            entity_id=UUID(metadata["entity_id"]) if metadata.get("entity_id") else None,
        )

        result = await db.execute(
            select(StripeEvent)
            .where(StripeEvent.stripe_event_id == event_id)
            .with_for_update()
        )
        stripe_event = result.scalar_one_or_none()
        if stripe_event is None:
            stripe_event = StripeEvent(
                entity_id=entity.id,
                stripe_event_id=event_id,
                event_type=event_type,
                api_version=event.get("api_version"),
                payload_json=event,
                signature_valid=signature_valid,
                processed_status="received",
                idempotency_key=metadata.get("idempotency_key"),
            )
            db.add(stripe_event)
            await db.flush()
        else:
            stripe_event.entity_id = entity.id
            stripe_event.event_type = event_type
            stripe_event.api_version = event.get("api_version")
            stripe_event.payload_json = event
            stripe_event.signature_valid = signature_valid

        if event_type == "checkout.session.completed":
            if metadata.get("type") != "credit_purchase":
                stripe_event.processed_status = "ignored"
                stripe_event.processed_at = datetime.now(timezone.utc)
                await db.flush()
                return {
                    "stripe_event_id": event_id,
                    "event_type": event_type,
                    "processed_status": "ignored",
                }

            user_id_raw = (
                metadata.get("user_id")
                or metadata.get("customer_id")
                or metadata.get("account_user_id")
            )
            if not user_id_raw:
                raise ValueError("credit purchase webhook missing user_id/customer_id metadata")

            user_id = UUID(user_id_raw)
            payment_intent_id = event_object.get("payment_intent")
            charge_id = event_object.get("payment_intent") or event_object.get("payment_link")
            amount_cents = int(event_object.get("amount_total") or metadata.get("price_cents") or 0)
            credit_cents = int(metadata.get("credit_cents") or amount_cents)
            currency = (event_object.get("currency") or entity.currency or "USD").upper()
            stripe_customer_id = event_object.get("customer")

            payment_result = await db.execute(
                select(Payment)
                .where(Payment.stripe_payment_intent_id == payment_intent_id)
                .with_for_update()
            )
            payment = payment_result.scalar_one_or_none()
            if payment is None:
                payment = Payment(
                    entity_id=entity.id,
                    customer_id=user_id,
                    stripe_payment_intent_id=payment_intent_id,
                    stripe_charge_id=charge_id,
                    stripe_customer_id=stripe_customer_id,
                    amount_cents=amount_cents,
                    currency=currency,
                    status="succeeded",
                    payment_method="stripe_checkout",
                    payment_type="credits",
                    received_at=datetime.now(timezone.utc),
                )
                db.add(payment)
                await db.flush()

            await self._get_or_create_api_credits(user_id,entity.id,db)
            journal_entry = await self._finance_engine.record_credit_purchase(
                user_id=user_id,
                amount_cents=amount_cents,
                stripe_pi_id=payment_intent_id,
                db=db,
                entity_id=entity.id,
            )
            if payment.status not in {"refunded","partially_refunded"}:
                payment.status = "succeeded"
            payment.payment_type = "credits"
            payment.journal_entry_id = journal_entry.id
            payment.net_cents = amount_cents

            credits = await self._record_credit_topup(
                user_id=user_id,
                entity_id=entity.id,
                payment=payment,
                journal_entry_id=journal_entry.id,
                credit_cents=credit_cents,
                customer_ref=stripe_customer_id,
                db=db,
            )

            stripe_event.processed_status = "processed"
            stripe_event.processed_at = datetime.now(timezone.utc)
            await db.flush()
            await self._log_transaction_to_crm(
                event_type=event_type,
                metadata=metadata,
                user_id=user_id,
                payment_id=payment.id,
                amount_cents=amount_cents,
                currency=currency,
                journal_entry_id=journal_entry.id,
                customer_ref=stripe_customer_id,
            )
            return {
                "stripe_event_id": event_id,
                "event_type": event_type,
                "processed_status": stripe_event.processed_status,
                "payment_id": str(payment.id),
                "journal_entry_id": str(journal_entry.id),
                "api_credits_id": str(credits.id),
            }

        if event_type == "payment_intent.succeeded":
            user_id_raw = metadata.get("customer_id") or metadata.get("user_id")
            if not user_id_raw:
                stripe_event.processed_status = "ignored"
                stripe_event.processed_at = datetime.now(timezone.utc)
                await db.flush()
                return {
                    "stripe_event_id": event_id,
                    "event_type": event_type,
                    "processed_status": "ignored",
                }

            user_id = UUID(user_id_raw)
            payment_intent_id = event_object["id"]
            charge_id = event_object.get("latest_charge")
            amount_cents = int(event_object.get("amount") or 0)
            currency = (event_object.get("currency") or entity.currency or "USD").upper()
            payment_type = metadata.get("payment_type", "credits")

            payment_result = await db.execute(
                select(Payment)
                .where(Payment.stripe_payment_intent_id == payment_intent_id)
                .with_for_update()
            )
            payment = payment_result.scalar_one_or_none()
            if payment is None:
                payment = Payment(
                    entity_id=entity.id,
                    customer_id=user_id,
                    stripe_payment_intent_id=payment_intent_id,
                    stripe_charge_id=charge_id,
                    stripe_customer_id=event_object.get("customer"),
                    amount_cents=amount_cents,
                    currency=currency,
                    status="succeeded",
                    payment_method=(event_object.get("payment_method_types") or [None])[0],
                    payment_type=payment_type,
                    received_at=datetime.now(timezone.utc),
                )
                db.add(payment)
                await db.flush()

            journal_entry_id: Optional[UUID] = payment.journal_entry_id
            if payment_type == "credits" and payment.journal_entry_id is None:
                await self._get_or_create_api_credits(user_id,entity.id,db)
                journal_entry = await self._finance_engine.record_credit_purchase(
                    user_id=user_id,
                    amount_cents=amount_cents,
                    stripe_pi_id=payment_intent_id,
                    db=db,
                    entity_id=entity.id,
                )
                payment.journal_entry_id = journal_entry.id
                journal_entry_id = journal_entry.id
                await self._record_credit_topup(
                    user_id=user_id,
                    entity_id=entity.id,
                    payment=payment,
                    journal_entry_id=journal_entry.id,
                    credit_cents=int(metadata.get("credit_cents") or amount_cents),
                    customer_ref=payment.stripe_customer_id,
                    db=db,
                )

            if payment.status not in {"refunded","partially_refunded"}:
                payment.status = "succeeded"
            payment.payment_type = payment_type
            payment.net_cents = amount_cents - int(event_object.get("application_fee_amount") or 0)
            stripe_event.processed_status = "processed"
            stripe_event.processed_at = datetime.now(timezone.utc)
            await db.flush()
            await self._log_transaction_to_crm(
                event_type=event_type,
                metadata=metadata,
                user_id=user_id,
                payment_id=payment.id,
                amount_cents=amount_cents,
                currency=currency,
                journal_entry_id=journal_entry_id,
                customer_ref=payment.stripe_customer_id,
            )
            return {
                "stripe_event_id": event_id,
                "event_type": event_type,
                "processed_status": "processed",
                "payment_id": str(payment.id),
                "journal_entry_id": str(journal_entry_id) if journal_entry_id else None,
            }

        stripe_event.processed_status = "ignored"
        stripe_event.processed_at = datetime.now(timezone.utc)
        await db.flush()
        return {
            "stripe_event_id": event_id,
            "event_type": event_type,
            "processed_status": "ignored",
        }
    
    async def add_credits(
        self, 
        user_id: UUID, 
        amount_cents: int, 
        db: AsyncSession,
        admin_note: str = None
    ) -> APICredits:
        """Add credits to user account (admin action)."""
        stmt = select(APICredits).where(APICredits.user_id == user_id)
        result = await db.execute(stmt)
        credits = result.scalars().first()
        
        if not credits:
            # Initialize if not exists
            credits = APICredits(user_id=user_id)
            db.add(credits)
        
        credits.balance_cents += amount_cents
        credits.total_purchased_cents += amount_cents
        
        await db.commit()
        await db.refresh(credits)
        return credits
    
    async def get_credits(self, user_id: UUID, db: AsyncSession) -> APICredits:
        """Get credits record for user."""
        return await available_api_credits(db, user_id)

    async def deduct_credits(
        self,
        user_id: UUID,
        amount_cents: int,
        db: AsyncSession,
        use_free_trial_first: bool = True
    ) -> bool:
        """
        Deduct credits for API usage.
        
        Args:
            user_id: User to deduct from
            amount_cents: Amount to deduct
            db: AsyncSession instance
            use_free_trial_first: Whether to use free trial credits before paid
            
        Returns:
            True if deduction successful, False if insufficient funds
        """
        credits = await available_api_credits(db, user_id)
        
        if not credits:
            return False

        # Check total funds first (atomicity)
        available_trial = max(0, credits.free_trial_cents - credits.free_trial_used_cents) if use_free_trial_first else 0
        total_available = credits.balance_cents + available_trial
        
        if total_available < amount_cents:
            return False
            
        # Apply deductions
        remaining_deduction = amount_cents
        
        if use_free_trial_first and available_trial > 0:
            from_trial = min(available_trial, remaining_deduction)
            credits.free_trial_used_cents += from_trial
            remaining_deduction -= from_trial
            
        if remaining_deduction > 0:
            credits.balance_cents -= remaining_deduction
            
        credits.total_used_cents += amount_cents
        await db.commit()
        return True
    
    async def calculate_claude_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        db: AsyncSession
    ) -> Tuple[int, int]:
        """
        Calculate vendor cost and customer cost for Claude usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            db: AsyncSession instance
            
        Returns:
            tuple: (vendor_cost_cents, customer_cost_cents)
        """
        settings = await self.get_settings(db)
        
        # Costs are stored in tenths of cents per 1K tokens
        # Default: 3 = 0.3 cents per 1K input, 15 = 1.5 cents per 1K output
        in_cost_per_1k = int(settings.get("claude_input_cost_per_1k", 3))
        out_cost_per_1k = int(settings.get("claude_output_cost_per_1k", 15))
        markup_percent = int(settings.get("claude_markup_percent", 100))
        
        # Vendor cost (tenths of cents -> cents)
        # Cost = (tokens / 1000) * (cost_per_1k / 10)
        vendor_cost_tenths = (input_tokens / 1000 * in_cost_per_1k) + (output_tokens / 1000 * out_cost_per_1k)
        vendor_cost_cents = math.ceil(vendor_cost_tenths / 10)
        
        # Customer cost with markup
        customer_cost_cents = math.ceil(vendor_cost_cents * (1 + markup_percent / 100))
        
        # Ensure minimum 1 cent charge for any non-zero token usage
        if (input_tokens > 0 or output_tokens > 0) and customer_cost_cents == 0:
            vendor_cost_cents = max(vendor_cost_cents, 1)
            customer_cost_cents = max(1, math.ceil(vendor_cost_cents * (1 + markup_percent / 100)))
            
        return vendor_cost_cents, customer_cost_cents
    
    async def has_sufficient_balance(
        self, 
        user_id: UUID, 
        estimated_cost_cents: int,
        db: AsyncSession
    ) -> bool:
        """Check if user has enough credits (including free trial)."""
        credits = await available_api_credits(db, user_id)
        
        if not credits:
            return False
            
        trial_available = max(0, credits.free_trial_cents - credits.free_trial_used_cents)
        total_available = credits.balance_cents + trial_available
        
        return total_available >= estimated_cost_cents
    
    async def get_settings(self, db: AsyncSession) -> Dict[str, Any]:
        """Get all billing-related settings as dict."""
        stmt = select(APISettings)
        result = await db.execute(stmt)
        items = result.scalars().all()
        return {item.key: item.value for item in items}

    # =========================================================================
    # CREDIT RESERVATIONS (BQ-129 — Allie API Proxy)
    # =========================================================================

    async def reserve_credits(
        self,
        user_id: UUID,
        estimated_cents: int,
        db: AsyncSession,
    ) -> Optional[UUID]:
        """
        Atomically check balance and place a hold.

        Uses SELECT ... FOR UPDATE on the credits row to prevent
        concurrent requests from double-spending.

        Respects free trial: reserves from free trial first, then paid.

        Args:
            user_id: User whose credits to reserve
            estimated_cents: Amount to hold in cents
            db: AsyncSession instance

        Returns:
            reservation_id (UUID) on success, None if insufficient balance
        """
        credits = await available_api_credits(db, user_id)

        if not credits:
            return None

        trial_available = max(0, credits.free_trial_cents - credits.free_trial_used_cents)
        total_available = credits.balance_cents + trial_available

        if total_available < estimated_cents:
            return None

        # Deduct from free trial first, then paid balance
        remaining = estimated_cents
        if trial_available > 0:
            from_trial = min(trial_available, remaining)
            credits.free_trial_used_cents += from_trial
            remaining -= from_trial
        if remaining > 0:
            credits.balance_cents -= remaining

        reservation = CreditReservation(
            user_id=user_id,
            amount_cents=estimated_cents,
            status="held",
        )
        db.add(reservation)
        await db.flush()

        reservation_id = reservation.id
        await db.commit()
        logger.info(f"Reserved {estimated_cents}¢ for user {user_id} (reservation={reservation_id})")
        return reservation_id

    async def settle_reservation(
        self,
        reservation_id: UUID,
        actual_cents: int,
        db: AsyncSession,
    ) -> bool:
        """
        Settle a reservation with actual cost.

        If actual < estimated, refund the difference back to the user's
        balance (free trial refunds go to paid balance for simplicity).
        If actual > estimated, deduct the extra.

        Args:
            reservation_id: The held reservation to settle
            actual_cents: Actual cost in cents
            db: AsyncSession instance

        Returns:
            True on success, False if reservation not found or already settled
        """
        stmt = (
            select(CreditReservation)
            .where(CreditReservation.id == reservation_id, CreditReservation.status == "held")
            .with_for_update()
        )
        result = await db.execute(stmt)
        reservation = result.scalars().first()
        if not reservation:
            return False

        diff = reservation.amount_cents - actual_cents

        if diff != 0:
            credit_stmt = (
                select(APICredits)
                .where(APICredits.user_id == reservation.user_id)
                .with_for_update()
            )
            cred_result = await db.execute(credit_stmt)
            credits = cred_result.scalars().first()
            if credits:
                if diff > 0:
                    # Refund excess to paid balance
                    credits.balance_cents += diff
                else:
                    # Deduct extra (shouldn't happen often)
                    credits.balance_cents += diff  # diff is negative

        reservation.status = "settled"
        reservation.settled_cents = actual_cents
        reservation.settled_at = datetime.utcnow()
        await db.commit()
        logger.info(
            f"Settled reservation {reservation_id}: "
            f"reserved={reservation.amount_cents}¢, actual={actual_cents}¢, diff={diff}¢"
        )
        return True

    async def cancel_reservation(
        self,
        reservation_id: UUID,
        db: AsyncSession,
    ) -> bool:
        """
        Cancel a reservation and release the held credits.

        Used on STOP/disconnect — no charge applied.

        Args:
            reservation_id: The held reservation to cancel
            db: AsyncSession instance

        Returns:
            True on success, False if reservation not found or already settled
        """
        stmt = (
            select(CreditReservation)
            .where(CreditReservation.id == reservation_id, CreditReservation.status == "held")
            .with_for_update()
        )
        result = await db.execute(stmt)
        reservation = result.scalars().first()
        if not reservation:
            return False

        # Refund full amount back to paid balance
        credit_stmt = (
            select(APICredits)
            .where(APICredits.user_id == reservation.user_id)
            .with_for_update()
        )
        cred_result = await db.execute(credit_stmt)
        credits = cred_result.scalars().first()
        if credits:
            credits.balance_cents += reservation.amount_cents

        reservation.status = "cancelled"
        reservation.settled_cents = 0
        reservation.settled_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Cancelled reservation {reservation_id}: refunded {reservation.amount_cents}¢")
        return True

    # =========================================================================
    # ESCROW HOLD STATE (P2.2)
    # =========================================================================

    async def hold_escrow(
        self, 
        order_id: UUID, 
        db: AsyncSession,
        hold_hours: int = 48
    ) -> bool:
        """
        Place order in escrow hold state.
        
        Transitions: PAID → IN_ESCROW
        Sets escrow_hold_until to current time + hold_hours.
        
        Args:
            order_id: Order to place in escrow
            db: AsyncSession instance
            hold_hours: Hours to hold in escrow (24-72h configurable)
            
        Returns:
            True if escrow hold successfully applied, False if order not found/invalid state
        """
        try:
            # Calculate escrow hold expiration
            hold_until = datetime.utcnow() + timedelta(hours=hold_hours)
            
            # Update order to IN_ESCROW status with escrow hold details
            result = await db.execute(
                text("""
                    UPDATE orders SET
                        status = 'in_escrow',
                        escrow_hold_until = :hold_until,
                        escrow_hold_hours = :hold_hours,
                        updated_at = NOW()
                    WHERE id = :order_id 
                    AND status = 'paid'
                """),
                {
                    "order_id": order_id,
                    "hold_until": hold_until,
                    "hold_hours": hold_hours
                }
            )
            
            # Check if update actually affected a row
            rows_affected = result.rowcount
            
            if rows_affected > 0:
                # Log escrow hold event
                await db.execute(
                    text("""
                        INSERT INTO order_events (
                            id, order_id, event_type, actor_type, actor_id, metadata
                        ) VALUES (
                            :event_id, :order_id, 'escrow_held', 'system', NULL, :metadata
                        )
                    """),
                    {
                        "event_id": uuid4(),
                        "order_id": order_id,
                        "metadata": f'{{"hold_hours": {hold_hours}, "hold_until": "{hold_until.isoformat()}"}}'
                    }
                )
                
                await db.commit()
                logger.info(f"Order {order_id} placed in escrow for {hold_hours}h until {hold_until}")
                return True
            else:
                logger.warning(f"Could not place order {order_id} in escrow - not in PAID status or not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to hold escrow for order {order_id}: {e}")
            await db.rollback()
            return False

    async def release_escrow(
        self,
        order_id: UUID, 
        db: AsyncSession,
        reason: str = "inspection_period_expired"
    ) -> bool:
        """
        Release escrow and transition order to pending_delivery.
        
        Transitions: IN_ESCROW → PENDING_DELIVERY
        Sets escrow_released_at timestamp.
        
        Args:
            order_id: Order to release from escrow
            db: AsyncSession instance
            reason: Reason for escrow release
            
        Returns:
            True if escrow successfully released, False if order not found/invalid state
        """
        try:
            # Update order to PENDING_DELIVERY status and mark escrow released
            result = await db.execute(
                text("""
                    UPDATE orders SET
                        status = 'pending_delivery',
                        escrow_released_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :order_id 
                    AND status = 'in_escrow'
                """),
                {"order_id": order_id}
            )
            
            # Check if update actually affected a row
            rows_affected = result.rowcount
            
            if rows_affected > 0:
                # Log escrow release event
                await db.execute(
                    text("""
                        INSERT INTO order_events (
                            id, order_id, event_type, actor_type, actor_id, metadata
                        ) VALUES (
                            :event_id, :order_id, 'escrow_released', 'system', NULL, :metadata
                        )
                    """),
                    {
                        "event_id": uuid4(),
                        "order_id": order_id,
                        "metadata": f'{{"reason": "{reason}"}}'
                    }
                )
                
                await db.commit()
                logger.info(f"Order {order_id} escrow released: {reason}")
                return True
            else:
                logger.warning(f"Could not release escrow for order {order_id} - not in IN_ESCROW status or not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to release escrow for order {order_id}: {e}")
            await db.rollback()
            return False

    async def check_expired_escrows(self, db: AsyncSession) -> int:
        """
        Check for expired escrow holds and auto-release them.
        
        Called by background job to automatically release escrow
        when inspection period expires without disputes.
        
        Returns:
            Number of escrows released
        """
        try:
            # Find orders with expired escrow holds
            result = await db.execute(
                text("""
                    SELECT id, escrow_hold_until
                    FROM orders
                    WHERE status = 'in_escrow'
                    AND escrow_hold_until <= NOW()
                    AND disputed_at IS NULL
                """)
            )
            
            expired_orders = result.fetchall()
            released_count = 0
            
            for order_row in expired_orders:
                order_id = order_row[0]
                hold_until = order_row[1]
                
                # Release this expired escrow
                success = await self.release_escrow(
                    order_id=order_id,
                    db=db,
                    reason="inspection_period_expired"
                )
                
                if success:
                    released_count += 1
                    logger.info(f"Auto-released expired escrow for order {order_id} (expired at {hold_until})")
            
            if released_count > 0:
                logger.info(f"Auto-released {released_count} expired escrow holds")
                
            return released_count
            
        except Exception as e:
            logger.error(f"Error checking expired escrows: {e}")
            return 0

    async def get_escrow_status(
        self,
        order_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get current escrow status for an order.
        
        Args:
            order_id: Order to check
            db: AsyncSession instance
            
        Returns:
            Dictionary with escrow status:
            {
                "in_escrow": bool,
                "escrow_hold_until": datetime|None,
                "escrow_hold_hours": int|None,
                "escrow_released_at": datetime|None,
                "time_remaining_hours": float|None,
                "is_expired": bool
            }
        """
        try:
            # Get escrow-related fields from order
            result = await db.execute(
                text("""
                    SELECT 
                        status,
                        escrow_hold_until,
                        escrow_hold_hours,
                        escrow_released_at
                    FROM orders
                    WHERE id = :order_id
                """),
                {"order_id": order_id}
            )
            
            row = result.fetchone()
            if not row:
                return {"error": "Order not found"}
            
            status, hold_until, hold_hours, released_at = row
            
            # Calculate derived fields
            in_escrow = (status == "in_escrow")
            time_remaining_hours = None
            is_expired = False
            
            if hold_until and in_escrow:
                # Calculate time remaining
                now = datetime.utcnow()
                time_delta = hold_until - now
                time_remaining_hours = time_delta.total_seconds() / 3600
                is_expired = (time_remaining_hours <= 0)
            
            return {
                "in_escrow": in_escrow,
                "escrow_hold_until": hold_until.isoformat() if hold_until else None,
                "escrow_hold_hours": hold_hours,
                "escrow_released_at": released_at.isoformat() if released_at else None,
                "time_remaining_hours": time_remaining_hours,
                "is_expired": is_expired
            }
            
        except Exception as e:
            logger.error(f"Error getting escrow status for order {order_id}: {e}")
            return {"error": str(e)}


# Singleton instance for dependency injection
billing_service = BillingService()
