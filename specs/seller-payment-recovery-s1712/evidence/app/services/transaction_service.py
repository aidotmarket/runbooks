"""
TransactionService — BQ-BIZ-CANONICAL-TX Phase 1
=================================================
State machine + CRUD. Phase 2 methods are stubs (M3).
"""
import json
import logging
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException
from app.services.seller_setup_service import assert_seller_payout_ready
from app.services.fee_calculator import split_platform_fee_cents
from app.services.order_money_service import bounded_payment_method

from app.models.transaction import (
    TransactionStatus,
    VALID_TX_TRANSITIONS,
)

logger = logging.getLogger(__name__)


def agent_checkout_outcome(function):
    """Public service outcomes never expose raw database/provider identifiers."""
    from functools import wraps
    @wraps(function)
    async def outcome(self, tx_id, api_key_id):
        from sqlalchemy.exc import DBAPIError
        from app.services.order_money_service import OrderMoneyConflict
        try:
            return await function(self,tx_id,api_key_id)
        except HTTPException:
            raise
        except (DBAPIError,TimeoutError,ConnectionError) as exc:
            await self.db.rollback()
            raise self._agent_refusal(tx_id,'binding_conflict',unavailable=True) from exc
        except OrderMoneyConflict as exc:
            await self.db.rollback()
            raise self._agent_refusal(tx_id,'evidence_conflict',unavailable='deadline' in str(exc).lower()) from exc
    return outcome


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # === PHASE 1: LIVE ===

    async def lock_stale_agent_payment(self, tx_id, expected_order_id):
        """Caller commits one cleanup candidate or rolls back every refusal.

        Orders precede transactions, authority, Payment, Refund and agent key.
        No authority is created for this unpaid cancellation. An unlinked row
        that becomes linked is refused under its transaction lock; no order is
        acquired beneath it. FK checks for new links conflict with this lock.
        """
        from app.services.order_money_service import validate_order_binding, OrderMoneyConflict
        from app.models.order import Order
        from app.models.transaction import Transaction
        from app.models.order_money_state import OrderMoneyState
        from app.models.finance import Payment, Refund
        from sqlalchemy import select, or_

        order = None
        if expected_order_id is not None:
            order = (await self.db.execute(select(Order).where(Order.id == expected_order_id)
                .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if order is None:
                return None
        tx = (await self.db.execute(select(Transaction).where(Transaction.id == tx_id)
            .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if tx is None or 'canonical_agent_attempt_v1' in (tx.tx_metadata or {}) or tx.order_id != expected_order_id or tx.status != 'agent_payment_pending':
            return None
        if not await self.db.scalar(text("SELECT created_at < NOW()-INTERVAL '1 hour' FROM transactions WHERE id=:id"), {'id': tx_id}):
            return None
        reverse = (await self.db.execute(text('SELECT id FROM orders WHERE transaction_id=:id ORDER BY id'), {'id': tx_id})).scalars().all()
        if reverse != ([expected_order_id] if order else []):
            return None
        if order:
            links = (await self.db.execute(select(Transaction.id).where(Transaction.order_id == order.id))).scalars().all()
            if links != [tx.id]:
                return None
            validate_order_binding(order, tx)
            if (order.status != 'created' or order.paid_at or order.revoked or order.refunded_at
                    or order.refund_amount_cents or order.stripe_refund_id or order.stripe_transfer_id
                    or order.delivered_at or order.completed_at or order.confirmed_at or order.disputed_at):
                return None
            state = (await self.db.execute(select(OrderMoneyState).where(OrderMoneyState.order_id == order.id)
                .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if state and (state.transaction_id != tx.id or state.protocol_version != 1
                    or state.payout_state != 'idle' or state.reconciliation_reason or state.independent_revocation
                    or state.capture_payment_id or state.capture_journal_entry_id or state.refund_applied_cents
                    or state.request_json or state.stripe_transfer_id):
                return None
        elif tx.stripe_payment_intent_id or await self.db.scalar(
                select(OrderMoneyState.order_id).where(OrderMoneyState.transaction_id == tx.id)):
            # Provider/authority history without its order cannot be certified unpaid.
            return None
        if tx.stripe_payment_intent_id:
            ids = (await self.db.execute(select(Order.id).where(Order.stripe_payment_intent_id == tx.stripe_payment_intent_id))).scalars().all()
            if ids != [expected_order_id]:
                return None
            payments = (await self.db.execute(select(Payment).where(Payment.stripe_payment_intent_id == tx.stripe_payment_intent_id)
                .order_by(Payment.id).with_for_update())).scalars().all()
            refunds = (await self.db.execute(select(Refund).where(or_(Refund.order_id == expected_order_id, Refund.transaction_id == tx.id))
                .order_by(Refund.stripe_refund_id, Refund.id).with_for_update())).scalars().all()
            # Read event admission without taking an existing event mutex below order.
            pending = await self.db.scalar(text("""SELECT EXISTS(SELECT 1 FROM stripe_events
                WHERE (refund_order_id=:oid OR refund_payment_intent_id=:pi)
                  AND refund_phase IS NOT NULL)"""), {'oid': expected_order_id, 'pi': tx.stripe_payment_intent_id})
            if payments or refunds or pending:
                return None
        elif await self.db.scalar(select(Refund.id).where(Refund.transaction_id == tx.id).limit(1)):
            return None
        if type(tx.amount_cents) is not int or tx.amount_cents < 0 or tx.paid_at or tx.settled_at:
            return None
        if tx.api_key_id:
            key = (await self.db.execute(text('SELECT org_id,spend_used FROM agent_api_keys WHERE id=:id FOR UPDATE'), {'id': tx.api_key_id})).mappings().one_or_none()
            if key is None or key['org_id'] != tx.party_id or key['spend_used'] < 0:
                raise OrderMoneyConflict('Agent spend ownership/counter mismatch')
        return {'id': tx.id, 'order_id': tx.order_id, 'api_key_id': tx.api_key_id, 'amount_cents': tx.amount_cents}

    async def initiate(
        self,
        buyer_id: UUID,
        origin: str,
        surface: str,
        buyer_type: str = "human",
        seller_id: Optional[UUID] = None,
        listing_id: Optional[UUID] = None,
        data_request_id: Optional[UUID] = None,
        amount_cents: Optional[int] = None,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None,
        auto_commit: bool = True,
    ) -> dict:
        """Create a new Transaction. Returns dict."""
        # Guard against system zero-UUID — callers must provide a real buyer_id
        _ZERO_UUID = UUID("00000000-0000-0000-0000-000000000000")
        if buyer_id == _ZERO_UUID:
            raise HTTPException(
                status_code=400,
                detail="buyer_id is required for internal service calls",
            )
        from app.services.terms_acceptance_service import TermsActor, require_terms_acceptance

        await require_terms_acceptance(
            self.db,
            actor=TermsActor(user_id=buyer_id),
            endpoint="transaction-initiate",
        )

        # Generate tx_number
        result = await self.db.execute(
            text("SELECT COALESCE(MAX(CAST(SUBSTRING(tx_number FROM 4) AS INTEGER)), 0) + 1 FROM transactions")
        )
        next_num = result.scalar()
        tx_number = f"TX-{next_num:06d}"

        # Calculate fees if amount provided
        platform_fee_cents = None
        seller_amount_cents = None
        if amount_cents:
            platform_fee_cents, seller_amount_cents = split_platform_fee_cents(amount_cents)

        tx_id = uuid4()
        await self.db.execute(
            text("""
                INSERT INTO transactions (
                    id, tx_number, origin, surface, buyer_type,
                    buyer_id, seller_id, listing_id, data_request_id,
                    amount_cents, currency, platform_fee_cents, seller_amount_cents, metadata,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :tx_number, :origin, :surface, :buyer_type,
                    :buyer_id, :seller_id, :listing_id, :data_request_id,
                    :amount_cents, :currency, :platform_fee_cents, :seller_amount_cents, :metadata,
                    'initiated', NOW(), NOW()
                )
            """),
            {
                "id": tx_id, "tx_number": tx_number,
                "origin": origin, "surface": surface, "buyer_type": buyer_type,
                "buyer_id": buyer_id, "seller_id": seller_id,
                "listing_id": listing_id, "data_request_id": data_request_id,
                "amount_cents": amount_cents, "currency": currency,
                "platform_fee_cents": platform_fee_cents,
                "seller_amount_cents": seller_amount_cents,
                "metadata": json.dumps(metadata or {}),
            },
        )

        await self._log_event(tx_id, "initiated", "system", to_status="initiated")
        if auto_commit:
            await self.db.commit()
        return await self.get_transaction(tx_id)

    async def initiate_agent(
        self,
        listing_id: UUID,
        buyer_id: UUID,
        api_key_id: UUID,
        idempotency_key: Optional[str] = None,
        commit: bool = False,
    ) -> dict:
        """Create an org-scoped agent transaction without touching the human path."""
        from app.services.agent_auth_service import AgentAuthService

        if idempotency_key:
            existing = await self.db.execute(
                text(
                    """
                    SELECT *
                    FROM transactions
                    WHERE api_key_id = :api_key_id
                      AND idempotency_key = :idempotency_key
                    LIMIT 1
                    """
                ),
                {"api_key_id": api_key_id, "idempotency_key": idempotency_key},
            )
            existing_row = existing.mappings().fetchone()
            if existing_row:
                return dict(existing_row)

        key_service = AgentAuthService(self.db)
        org_ctx = await key_service.get_org_context(api_key_id)
        listing = await self._get_listing_for_agent(listing_id)

        from app.services.terms_acceptance_service import TermsActor, require_terms_acceptance

        await require_terms_acceptance(
            self.db,
            actor=TermsActor(user_id=buyer_id, org_id=org_ctx.get("org_id")),
            endpoint="mcp-order-initiate",
        )

        if listing["status"] != "published":
            raise HTTPException(status_code=400, detail="Listing is not available for purchase")
        if listing["seller_id"] == buyer_id:
            raise HTTPException(status_code=400, detail="Cannot purchase your own listing")
        await assert_seller_payout_ready(self.db, listing["seller_id"])

        amount_cents = int(float(listing["price"]) * 100)
        platform_fee_cents, seller_amount_cents = split_platform_fee_cents(amount_cents)

        tx_id = uuid4()
        tx_number = await self._next_tx_number()
        await self.db.execute(
            text(
                """
                INSERT INTO transactions (
                    id, tx_number, origin, surface, buyer_type,
                    buyer_id, seller_id, party_id, listing_id,
                    api_key_id, idempotency_key, amount_cents, currency,
                    platform_fee_cents, seller_amount_cents,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :tx_number, 'listing_purchase', 'agent_api', 'agent',
                    :buyer_id, :seller_id, :party_id, :listing_id,
                    :api_key_id, :idempotency_key, :amount_cents, 'USD',
                    :platform_fee_cents, :seller_amount_cents,
                    'initiated', NOW(), NOW()
                )
                """
            ),
            {
                "id": tx_id,
                "tx_number": tx_number,
                "buyer_id": buyer_id,
                "seller_id": listing["seller_id"],
                "party_id": org_ctx["org_id"],
                "listing_id": listing_id,
                "api_key_id": api_key_id,
                "idempotency_key": idempotency_key,
                "amount_cents": amount_cents,
                "platform_fee_cents": platform_fee_cents,
                "seller_amount_cents": seller_amount_cents,
            },
        )
        await self._log_event(tx_id, "initiated", "agent", actor_id=buyer_id, to_status="initiated")
        await self._log_agent_audit(
            api_key_id=api_key_id,
            tool_name="initiate_purchase",
            transaction_id=tx_id,
            request_payload={"listing_id": str(listing_id), "idempotency_key": idempotency_key},
            response_payload={"status": "initiated"},
            http_status=200,
            status="success",
        )
        if commit:
            await self.db.commit()
        return await self.get_transaction(tx_id)

    @staticmethod
    def _agent_refusal(tx_id, reason, *, unavailable=False):
        return HTTPException(503 if unavailable else 409, detail={
            'code': 'AGENT_PAYMENT_RECONCILIATION_UNAVAILABLE' if unavailable else 'AGENT_PAYMENT_RECONCILIATION_REQUIRED',
            'transaction_id': str(tx_id), 'reason': reason})

    async def _agent_authenticated(self, tx_id, api_key_id):
        from app.services.agent_auth_service import AgentAuthService
        tx = await self.get_transaction(tx_id)
        if tx is None: raise HTTPException(404, 'Transaction not found')
        key = await AgentAuthService(self.db).get_api_key(api_key_id)
        self._assert_agent_transaction_access(tx,key,api_key_id)
        if tx.get('api_key_id') != api_key_id:
            raise HTTPException(403, 'Agent key ownership mismatch')
        return tx

    @bounded_payment_method
    async def _agent_conflict(self, tx_id, order_id, evidence=None):
        from app.services.order_money_service import _locked_initial_pair, validate_agent_pair, AGENT_ATTEMPT_KEY, AGENT_TRANSITIONS
        def record(sync):
            order, tx = _locked_initial_pair(sync,order_id)
            if tx is None or tx.id != tx_id: raise ValueError('Attempt ownership changed')
            a = validate_agent_pair(order,tx)
            if 'conflict_reconciliation' not in AGENT_TRANSITIONS[a['state']]: return
            if a['revision'] >= 2147483647: raise ValueError('Attempt revision overflow')
            updated = {**a,'state':'conflict_reconciliation','revision':a['revision']+1}
            if evidence is not None and a['observed_payment_intent_id'] in (None,evidence.payment_intent_id):
                updated.update(observed_payment_intent_id=evidence.payment_intent_id,
                    observed_provider_status=evidence.provider_status,observed_at=evidence.observed_at,
                    evidence_source=evidence.source)
            from app.services.order_money_service import validate_agent_attempt
            validate_agent_attempt(updated)
            tx.tx_metadata = {**tx.tx_metadata,AGENT_ATTEMPT_KEY:updated}
            sync.flush()
        await self.db.run_sync(record)
        await self.db.commit()

    @bounded_payment_method
    async def _apply_agent_observation(self, tx_id, api_key_id, evidence):
        import asyncio
        from app.services.order_money_service import (
            _locked_initial_pair, validate_agent_pair, compare_agent_evidence,
            ExpectedPaymentBinding, bind_initial_order_payment_intent_sync,
            transition_agent_attempt_sync, _initial_history_absent, validate_order_binding)
        observed = await self._agent_authenticated(tx_id,api_key_id)
        oid = observed.get('order_id')
        if oid is None: raise self._agent_refusal(tx_id,'binding_conflict')
        def apply(sync):
            sync.execute(text("SET LOCAL lock_timeout='250ms'"))
            sync.execute(text("SET LOCAL statement_timeout='2000ms'"))
            order, tx = _locked_initial_pair(sync,oid)
            if tx is None or tx.id != tx_id: raise ValueError('Attempt reverse binding changed')
            attempt = validate_agent_pair(order,tx)
            compare_agent_evidence(attempt,evidence)
            if attempt['state'] in {'completed','cancelled_reconciled'}:
                validate_order_binding(order,tx)
                if attempt['state']=='completed':
                    from app.services.order_money_service import validate_agent_completed_capture
                    validate_agent_completed_capture(sync,order,tx)
                return attempt['state'],False
            if evidence.provider_status not in {'succeeded','processing','requires_payment_method','requires_confirmation','requires_action','requires_capture','canceled'}:
                transition_agent_attempt_sync(sync,order,tx,state='conflict_reconciliation',evidence=evidence)
                return 'conflict_reconciliation',False
            binding = ExpectedPaymentBinding(UUID(str(order.id)),UUID(str(tx.id)),None,None,evidence.payment_intent_id,
                evidence.amount_cents,evidence.currency.upper(),UUID(str(order.buyer_id)),UUID(str(order.seller_id)),
                UUID(str(order.listing_id)),order.platform_fee_cents,order.seller_amount_cents)
            bind_initial_order_payment_intent_sync(sync,order_id=order.id,
                payment_intent_id=evidence.payment_intent_id,expected_transaction_id=tx.id,
                mode='agent_attempt_completion',expected_binding=binding,
                expected_agent_attempt_id=UUID(attempt['attempt_id']),
                expected_agent_attempt_revision=attempt['revision'],provider_evidence=evidence)
            if evidence.provider_status == 'canceled' and evidence.source == 'provider_read':
                transition_agent_attempt_sync(sync,order,tx,state='cancelled_reconciled',evidence=evidence,release=True)
                return 'cancelled_reconciled',False
            state = ('bound_pending' if evidence.provider_status in {'succeeded','processing'} else
                     'cancellation_unknown' if evidence.provider_status == 'requires_action' else 'response_observed')
            _initial_history_absent(sync,order,tx)
            before = tx.status
            transition_agent_attempt_sync(sync,order,tx,state=state,evidence=evidence)
            tx.status = 'agent_payment_pending' if state == 'bound_pending' else 'initiated'
            sync.flush()
            return state,before != tx.status
        try:
            async with asyncio.timeout(5):
                state,changed = await self.db.run_sync(apply)
                if changed:
                    current = await self.get_transaction(tx_id)
                    await self._log_event(tx_id,'status_changed','system',from_status=observed['status'],
                        to_status=current['status'],payload={'order_id':str(oid),'attempt_state':state})
                    await self._log_agent_audit(api_key_id=api_key_id,tool_name='checkout',transaction_id=tx_id,
                        request_payload={'transaction_id':str(tx_id)},response_payload={'status':current['status']},
                        http_status=422 if state == 'cancelled_reconciled' else 200,status='error' if state == 'cancelled_reconciled' else 'success')
                await self.db.commit()
            return state
        except BaseException:
            await self.db.rollback()
            raise

    @bounded_payment_method
    async def _agent_current_result(self, tx_id, api_key_id):
        from app.services.order_money_service import _locked_initial_pair,validate_agent_pair,validate_order_binding
        tx = await self._agent_authenticated(tx_id,api_key_id)
        def current(sync):
            order, linked = _locked_initial_pair(sync,tx['order_id'])
            if linked is None or linked.id != tx_id: raise ValueError('Attempt reverse binding mismatch')
            attempt = validate_agent_pair(order,linked)
            if attempt['state'] == 'cancelled_reconciled':
                validate_order_binding(order,linked)
                raise HTTPException(422,detail={'code':'AGENT_PAYMENT_CANCELLED','transaction_id':str(tx_id)})
            if order.revoked or order.refund_amount_cents or order.disputed_at or order.status in {'refunded','partially_refunded','disputed','cancelled'}:
                raise HTTPException(409,'Financial history prevents checkout')
            if attempt['state'] not in {'bound_pending','completed'}:
                reason = {'cancellation_unknown':'cancellation_unknown','conflict_reconciliation':'binding_conflict'}.get(attempt['state'],'provider_outcome_unknown')
                raise self._agent_refusal(tx_id,reason)
            validate_order_binding(order,linked)
            if attempt['state']=='completed':
                from app.services.order_money_service import validate_agent_completed_capture
                validate_agent_completed_capture(sync,order,linked)
            return {'transaction_id':str(tx_id),'tx_number':linked.tx_number,'status':linked.status,
                'checkout_id':linked.stripe_payment_intent_id,'payment_status':attempt['observed_provider_status'],
                'order_id':str(order.id)}
        try:
            return await self.db.run_sync(current)
        finally:
            await self.db.rollback()

    @agent_checkout_outcome
    async def reconcile_agent_checkout(self, tx_id: UUID, api_key_id: UUID) -> dict:
        """Read the original provider identity; never dispatch create/cancel again."""
        import asyncio, stripe
        from app.core.stripe_async import run_stripe
        from app.services.order_money_service import AGENT_ATTEMPT_KEY,validate_agent_attempt,agent_provider_evidence
        tx = await self._agent_authenticated(tx_id,api_key_id)
        attempt = validate_agent_attempt((tx.get('metadata') or {}).get(AGENT_ATTEMPT_KEY))
        if attempt['state'] in {'completed','cancelled_reconciled'}:
            return await self._agent_current_result(tx_id,api_key_id)
        pi = attempt['observed_payment_intent_id']
        await self.db.rollback()
        if pi is None: raise self._agent_refusal(tx_id,'provider_outcome_unknown')
        try:
            async with asyncio.timeout(10):
                obj = await run_stripe(stripe.PaymentIntent.retrieve,pi)
            evidence = agent_provider_evidence(obj,source='provider_read',account=attempt['provider_account_id'])
            await self._apply_agent_observation(tx_id,api_key_id,evidence)
        except HTTPException:
            raise
        except Exception as exc:
            await self.db.rollback()
            from sqlalchemy.exc import DBAPIError
            unavailable=isinstance(exc,(DBAPIError,TimeoutError,ConnectionError)) or 'deadline' in str(exc).lower()
            raise self._agent_refusal(tx_id,'evidence_conflict',unavailable=unavailable) from exc
        return await self._agent_current_result(tx_id,api_key_id)

    @bounded_payment_method
    async def _prepare_agent_checkout(self, tx_id, api_key_id, tx, org_ctx, listing):
        import asyncio
        from sqlalchemy import select
        from app.models.transaction import Transaction
        from app.services.order_service import get_order_service
        from app.services.order_money_service import AGENT_ATTEMPT_KEY,agent_now,validate_agent_attempt
        order_service = get_order_service(self.db)
        order = await order_service.create_order(
            buyer_id=org_ctx["org_owner_user_id"],
            seller_id=listing["seller_id"],
            listing_id=tx["listing_id"],
            amount_cents=tx["amount_cents"],
            listing_snapshot={
                "id": str(listing["id"]),
                "title": listing["title"],
                "slug": listing.get("slug"),
                "price": float(listing["price"]),
                "category": listing.get("category"),
            },
            transaction_id=tx_id,
            auto_commit=False,
        )

        try:
            async with asyncio.timeout(5):
                await self.db.execute(text("SET LOCAL lock_timeout='250ms'"))
                await self.db.execute(text("SET LOCAL statement_timeout='2000ms'"))
                locked = (await self.db.execute(select(Transaction).where(Transaction.id==tx_id)
                    .with_for_update().execution_options(populate_existing=True))).scalar_one()
                if (locked.order_id is not None or locked.stripe_payment_intent_id is not None
                        or locked.status != 'initiated' or AGENT_ATTEMPT_KEY in (locked.tx_metadata or {})
                        or locked.api_key_id != api_key_id or locked.party_id != org_ctx['org_id']):
                    raise self._agent_refusal(tx_id,'binding_conflict')
                for field in ('buyer_id','seller_id','listing_id','amount_cents','currency','platform_fee_cents','seller_amount_cents'):
                    if getattr(locked,field) != tx[field]: raise self._agent_refusal(tx_id,'binding_conflict')
                reverse = (await self.db.execute(text('select id from orders where transaction_id=:id order by id'),{'id':tx_id})).scalars().all()
                if reverse != [UUID(str(order['id']))]: raise self._agent_refusal(tx_id,'binding_conflict')
                from app.core.config import settings
                attempt = dict(version=1,attempt_id=str(uuid4()),transaction_id=str(tx_id),original_order_id=str(order['id']),
                    api_key_id=str(api_key_id),org_id=str(org_ctx['org_id']),buyer_id=str(tx['buyer_id']),
                    seller_id=str(tx['seller_id']),listing_id=str(tx['listing_id']),provider_idempotency_key=f'{api_key_id}:{tx_id}',
                    amount_cents=tx['amount_cents'],currency=tx['currency'].lower(),platform_fee_cents=tx['platform_fee_cents'],
                    seller_amount_cents=tx['seller_amount_cents'],customer_id=org_ctx['stripe_customer_id'],
                    payment_method_id=org_ctx['default_payment_method_id'],provider_account_id=None,livemode=not settings.STRIPE_TEST_MODE,
                    request_metadata={'transaction_id':str(tx_id),'order_id':str(order['id']),'api_key_id':str(api_key_id),'buyer_type':'agent'},
                    prepared_at=agent_now(),revision=1,state='prepared_unknown',observed_payment_intent_id=None,
                    observed_provider_status=None,observed_at=None,evidence_source=None,spend_release_state='held',release_evidence=None)
                validate_agent_attempt(attempt)
                locked.order_id=UUID(str(order['id']))
                locked.tx_metadata={**(locked.tx_metadata or {}),AGENT_ATTEMPT_KEY:attempt}
                await self.db.commit()
        except BaseException:
            await self.db.rollback()
            raise
        return attempt

    @bounded_payment_method
    async def _legacy_agent_cached(self, tx_id, api_key_id, observed_order_id):
        """Read an independently coherent historical pair without adopting it."""
        from app.services.order_money_service import (
            _locked_initial_pair, validate_order_binding, AGENT_ATTEMPT_KEY)
        def current(sync):
            order, tx = _locked_initial_pair(sync, observed_order_id)
            if (tx is None or tx.id != tx_id or tx.api_key_id != api_key_id
                    or tx.buyer_type != 'agent' or type(tx.tx_metadata) is not dict
                    or AGENT_ATTEMPT_KEY in tx.tx_metadata):
                raise self._agent_refusal(tx_id, 'binding_conflict')
            validate_order_binding(order, tx)
            if (tx.status not in {'agent_payment_pending','paid','fulfilling','delivered','confirmed','settled','in_escrow'}
                    or order.status not in {'created','paid','pending_delivery','delivered','completed'}
                    or order.revoked or order.refund_amount_cents or order.disputed_at
                    or tx.tx_metadata.get('payment_intent_id') not in (None, order.stripe_payment_intent_id)):
                raise self._agent_refusal(tx_id, 'binding_conflict')
            return dict(transaction_id=str(tx.id), tx_number=tx.tx_number, status=tx.status,
                        checkout_id=tx.stripe_payment_intent_id, payment_status='cached',order_id=str(order.id))
        try:
            return await self.db.run_sync(current)
        finally:
            await self.db.rollback()

    @agent_checkout_outcome
    async def create_agent_checkout(self, tx_id: UUID, api_key_id: UUID) -> dict:
        """Commit one original request before the one-shot external dispatch."""
        import asyncio, stripe
        from sqlalchemy import select
        from app.models.transaction import Transaction
        from app.core.stripe_async import run_stripe
        from app.services.agent_auth_service import AgentAuthService
        from app.services.order_service import get_order_service
        from app.services.order_money_service import AGENT_ATTEMPT_KEY,agent_now,validate_agent_attempt,agent_provider_evidence
        tx = await self._agent_authenticated(tx_id,api_key_id)
        if AGENT_ATTEMPT_KEY in (tx.get('metadata') or {}):
            return await self.reconcile_agent_checkout(tx_id,api_key_id)
        if tx.get('order_id') or tx.get('stripe_payment_intent_id'):
            # Historical rows cannot acquire a fabricated new request/attempt.
            if tx.get('order_id') and tx.get('stripe_payment_intent_id'):
                return await self._legacy_agent_cached(tx_id,api_key_id,tx['order_id'])
            raise self._agent_refusal(tx_id,'binding_conflict')
        if tx['status'] != 'initiated':
            raise HTTPException(400,'Transaction must be initiated')
        auth_service = AgentAuthService(self.db)
        org_ctx = await auth_service.get_org_context(api_key_id)
        if not org_ctx.get("org_owner_user_id"):
            raise HTTPException(status_code=422, detail="Organization owner could not be resolved")
        from app.services.terms_acceptance_service import TermsActor, require_terms_acceptance

        await require_terms_acceptance(
            self.db,
            actor=TermsActor(user_id=org_ctx.get("org_owner_user_id"), org_id=org_ctx.get("org_id")),
            endpoint="mcp-agent-checkout",
        )
        if not org_ctx.get("stripe_customer_id") or not org_ctx.get("default_payment_method_id"):
            await self._mark_agent_checkout_failed(
                tx_id=tx_id,
                api_key_id=api_key_id,
                amount_cents=tx["amount_cents"] or 0,
                from_status=tx["status"],
                reason="Organization has no default payment method configured",
            )
            raise HTTPException(status_code=422, detail="Organization has no default payment method configured")

        listing = await self._get_listing_for_agent(tx["listing_id"])
        if listing["status"] != "published":
            raise HTTPException(status_code=400, detail="Listing is not available for purchase")
        await assert_seller_payout_ready(self.db, listing["seller_id"])
        try:
            attempt = await self._prepare_agent_checkout(tx_id,api_key_id,tx,org_ctx,listing)
        except HTTPException:
            raise
        except Exception as exc:
            await self.db.rollback()
            from sqlalchemy.exc import DBAPIError
            if isinstance(exc,(DBAPIError,TimeoutError,ConnectionError)) or 'deadline' in str(exc).lower():
                raise self._agent_refusal(tx_id,'binding_conflict',unavailable=True) from exc
            raise
        # No commit uncertainty grants the one-shot entitlement: control reaches
        # this line only after a known successful preparation commit.
        try:
            async with asyncio.timeout(20):
                pi = await run_stripe(stripe.PaymentIntent.create,amount=attempt['amount_cents'],currency=attempt['currency'],
                    customer=attempt['customer_id'],payment_method=attempt['payment_method_id'],confirm=True,off_session=True,
                    idempotency_key=attempt['provider_idempotency_key'],metadata=attempt['request_metadata'])
        except Exception as exc:
            raise self._agent_refusal(tx_id,'provider_outcome_unknown') from exc
        evidence = None
        try:
            evidence=agent_provider_evidence(pi,source='create_response',account=attempt['provider_account_id'])
            state=await self._apply_agent_observation(tx_id,api_key_id,evidence)
        except Exception as exc:
            await self.db.rollback()
            try: await self._agent_conflict(tx_id,UUID(attempt['original_order_id']),evidence)
            except Exception as update_error:
                await self.db.rollback()
                raise self._agent_refusal(tx_id,'binding_conflict',unavailable=True) from update_error
            from sqlalchemy.exc import DBAPIError
            unavailable=isinstance(exc,(DBAPIError,TimeoutError,ConnectionError)) or 'deadline' in str(exc).lower()
            raise self._agent_refusal(tx_id,'binding_conflict',unavailable=unavailable) from exc
        if state == 'cancellation_unknown':
            try:
                async with asyncio.timeout(10):
                    await run_stripe(stripe.PaymentIntent.cancel,evidence.payment_intent_id)
            except Exception as exc:
                raise self._agent_refusal(tx_id,'cancellation_unknown') from exc
            return await self.reconcile_agent_checkout(tx_id,api_key_id)
        if evidence.provider_status == 'canceled':
            return await self.reconcile_agent_checkout(tx_id,api_key_id)
        return await self._agent_current_result(tx_id,api_key_id)

    async def transition(
        self,
        tx_id: UUID,
        new_status: str,
        actor_type: str = "system",
        actor_id: Optional[UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
        *, commit: bool = True, money=None,
    ) -> dict:
        """Validate and execute a state transition."""
        tx = await self.get_transaction(tx_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if new_status=='refunded':
            raise HTTPException(409, 'Validated provider refund processor owns this transition')
        if tx['order_id'] and (money is not None or tx.get('stripe_payment_intent_id')):
            from app.services.order_money_service import lock_order_money
            money = money or await lock_order_money(self.db, tx['order_id'])
            tx = await self.get_transaction(tx_id)
            if new_status == 'refunded':
                raise HTTPException(409, 'Validated provider refund processor owns this transition')
            if new_status in {'paid','delivered','confirmed','settled'}:
                if (money.state.independent_revocation or money.order.revoked or
                        money.state.refund_applied_cents or money.state.reconciliation_reason or
                        money.order.status in {'refunded','partially_refunded','disputed'}):
                    raise HTTPException(409, 'Order money restriction prevents transition')
                if new_status == 'settled' and not money.state.stripe_transfer_id:
                    raise HTTPException(409, 'Settlement requires recorded provider Transfer')
                if await self.db.scalar(text("select exists(select 1 from stripe_events where refund_phase='admitted' and (refund_order_id=:oid or refund_payment_intent_id=:pi))"), {'oid':money.order.id,'pi':money.order.stripe_payment_intent_id}):
                    raise HTTPException(409, 'Refund admission prevents transition')

        elif tx['order_id']:
            # Unpaid/free checkout has no PI authority yet. Still acquire the
            # order before its transaction so later status triggers cannot invert.
            await self.db.execute(text('select id from orders where id=:id for update'),{'id':tx['order_id']})
            await self.db.execute(text('select id from transactions where id=:id for update'),{'id':tx_id})
            tx = await self.get_transaction(tx_id)
            if new_status=='settled' and tx['amount_cents']>0:
                raise HTTPException(409, 'Settlement requires recorded provider Transfer')

        current = TransactionStatus(tx["status"])
        target = TransactionStatus(new_status)

        valid_targets = VALID_TX_TRANSITIONS.get(current, [])
        if target not in valid_targets:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: {current.value} → {target.value}. "
                       f"Valid: {[t.value for t in valid_targets]}",
            )

        # Update status + relevant timestamp
        ts_col = {
            "quoted": "quoted_at", "accepted": "accepted_at",
            "paid": "paid_at", "delivered": "delivered_at",
            "settled": "settled_at",
        }.get(target.value)

        ts_clause = f", {ts_col} = NOW()" if ts_col else ""

        await self.db.execute(
            text(f"""
                UPDATE transactions
                SET status = :status, updated_at = NOW() {ts_clause}
                WHERE id = :id
            """),
            {"status": target.value, "id": tx_id},
        )

        await self._log_event(
            tx_id, "status_changed", actor_type,
            actor_id=actor_id,
            from_status=current.value,
            to_status=target.value,
            payload=payload,
        )
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
        return await self.get_transaction(tx_id)

    async def get_transaction(self, tx_id: UUID) -> Optional[dict]:
        result = await self.db.execute(
            text("SELECT * FROM transactions WHERE id = :id"),
            {"id": tx_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None

    async def get_transaction_with_events(self, tx_id: UUID) -> Optional[dict]:
        tx = await self.get_transaction(tx_id)
        if not tx:
            return None
        events_result = await self.db.execute(
            text("SELECT * FROM transaction_events WHERE transaction_id = :id ORDER BY created_at"),
            {"id": tx_id},
        )
        tx["events"] = [dict(r) for r in events_result.mappings().fetchall()]
        return tx

    async def list_transactions(
        self,
        status: Optional[str] = None,
        origin: Optional[str] = None,
        buyer_id: Optional[UUID] = None,
        seller_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[dict]:
        conditions = []
        params = {"limit": limit, "offset": offset}

        if status:
            conditions.append("status = :status")
            params["status"] = status
        if origin:
            conditions.append("origin = :origin")
            params["origin"] = origin
        if buyer_id:
            conditions.append("buyer_id = :buyer_id")
            params["buyer_id"] = buyer_id
        if seller_id:
            conditions.append("seller_id = :seller_id")
            params["seller_id"] = seller_id

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        result = await self.db.execute(
            text(f"SELECT * FROM transactions {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            params,
        )
        return [dict(r) for r in result.mappings().fetchall()]

    # === PHASE 2: GOLD PATH (BQ-BIZ-GOLD-PATH) ===

    async def create_quote(self, tx_id: UUID, amount_cents: int, currency: str, terms: dict) -> dict:
        """Create a quote for negotiated flow. INITIATED → QUOTED."""
        import json
        from app.core.config import settings

        tx = await self.get_transaction(tx_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")

        # Quote fields must not take an implicit transaction UPDATE lock before
        # the parent order. Revalidate the state after waiting for both locks.
        parent_order_id = tx['order_id']
        if parent_order_id:
            await self.db.execute(text('select id from orders where id=:id for update'), {'id': parent_order_id})
        await self.db.execute(text('select id from transactions where id=:id for update'), {'id': tx_id})
        tx = await self.get_transaction(tx_id)
        if tx['order_id'] != parent_order_id:
            raise HTTPException(409, 'Quote parent order binding changed')
        if tx['status'] != 'initiated':
            raise HTTPException(400, 'Quote requires initiated transaction')
        platform_fee_cents, seller_amount_cents = split_platform_fee_cents(amount_cents)

        await self.db.execute(
            text("""
                UPDATE transactions SET
                    amount_cents = :amount, currency = :currency,
                    platform_fee_cents = :pf, seller_amount_cents = :sa,
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'), '{quote_terms}', :terms
                    )
                WHERE id = :id
            """),
            {
                "amount": amount_cents, "currency": currency,
                "pf": platform_fee_cents, "sa": seller_amount_cents,
                "terms": json.dumps(terms), "id": tx_id,
            },
        )

        return await self.transition(
            tx_id, "quoted", "seller",
            payload={"amount_cents": amount_cents, "currency": currency, "terms": terms},
        )

    async def accept_quote(self, tx_id: UUID, buyer_id: UUID) -> dict:
        """Buyer accepts quote. QUOTED → ACCEPTED."""
        tx = await self.get_transaction(tx_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        if tx["buyer_id"] != buyer_id:
            raise HTTPException(403, "Not your transaction")

        return await self.transition(tx_id, "accepted", "buyer", actor_id=buyer_id)

    async def create_checkout(self, tx_id: UUID) -> dict:
        """
        Fixed-price listing purchase flow:
        1. Validate Transaction is in INITIATED state
        2. Auto-quote from listing price → QUOTED
        3. Auto-accept → ACCEPTED
        4. Verify seller payout readiness (M5)
        5. Create Order via OrderService.create_order(transaction_id=tx_id) (M6)
        6. Create Stripe Checkout Session → CHECKOUT_PENDING
        7. Return {transaction_id, checkout_url, tx_number}
        """
        import stripe
        from app.core.config import settings
        from app.core.stripe_async import run_stripe

        tx = await self.get_transaction(tx_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        if tx["status"] != "initiated":
            raise HTTPException(400, f"Transaction must be in 'initiated' state, got '{tx['status']}'")
        if not tx["listing_id"]:
            raise HTTPException(400, "create_checkout requires a listing_id on the Transaction")

        # Fetch listing
        listing_result = await self.db.execute(
            text("""
                SELECT l.*
                FROM listings l
                WHERE l.id = :id
            """),
            {"id": tx["listing_id"]},
        )
        listing = listing_result.mappings().fetchone()
        if not listing:
            raise HTTPException(404, "Listing not found")
        listing = dict(listing)
        if listing["status"] != "published":
            raise HTTPException(
                400,
                {"code": "listing_not_available", "message": "Listing is not available for purchase"},
            )

        # Self-purchase guard (Gate 3 P1)
        if listing["seller_id"] == tx["buyer_id"]:
            raise HTTPException(400, "Cannot purchase your own listing")

        # Calculate amounts
        amount_cents = int(float(listing["price"]) * 100)
        platform_fee_cents, seller_amount_cents = split_platform_fee_cents(amount_cents)

        if amount_cents > 0:
            await assert_seller_payout_ready(self.db, listing["seller_id"])

        # Auto-quote: INITIATED → QUOTED
        await self.db.execute(
            text("UPDATE transactions SET amount_cents=:a, platform_fee_cents=:pf, seller_amount_cents=:sa, seller_id=:sid, updated_at=NOW(), quoted_at=NOW(), status='quoted' WHERE id=:id"),
            {"a": amount_cents, "pf": platform_fee_cents, "sa": seller_amount_cents, "sid": listing["seller_id"], "id": tx_id},
        )
        await self._log_event(tx_id, "status_changed", "system", from_status="initiated", to_status="quoted",
                              payload={"amount_cents": amount_cents, "auto_quote": True})

        # Auto-accept: QUOTED → ACCEPTED
        await self.db.execute(
            text("UPDATE transactions SET status='accepted', accepted_at=NOW(), updated_at=NOW() WHERE id=:id"),
            {"id": tx_id},
        )
        await self._log_event(tx_id, "status_changed", "system", from_status="quoted", to_status="accepted",
                              payload={"auto_accept": True, "fixed_price": True})

        # Create Order via OrderService (M6: pass transaction_id)
        from app.services.order_service import get_order_service
        order_service = get_order_service(self.db)
        tx_metadata = tx.get("metadata") or {}
        if isinstance(tx_metadata, str):
            tx_metadata = json.loads(tx_metadata)
        purchased_version_id = tx_metadata.get("version_id")
        if purchased_version_id:
            purchased_version_id = UUID(str(purchased_version_id))
        order = await order_service.create_order(
            buyer_id=tx["buyer_id"],
            seller_id=listing["seller_id"],
            listing_id=tx["listing_id"],
            amount_cents=amount_cents,
            listing_snapshot={
                "id": str(listing["id"]),
                "title": listing["title"],
                "slug": listing.get("slug"),
                "price": float(listing["price"]),
                "category": listing.get("category"),
            },
            transaction_id=tx_id,  # M6
            auto_commit=False,  # Gate 3 R1 Fix 3: don't commit until Stripe succeeds
            purchased_version_id=purchased_version_id,
        )

        # Link Order to Transaction
        await self.db.execute(
            text("UPDATE transactions SET order_id=:oid, status='checkout_pending', updated_at=NOW() WHERE id=:id"),
            {"oid": order["id"], "id": tx_id},
        )
        await self._log_event(tx_id, "status_changed", "system", from_status="accepted", to_status="checkout_pending",
                              payload={"order_id": str(order["id"]), "order_number": order["order_number"]})

        if amount_cents == 0:
            await self.db.execute(
                text("""
                    UPDATE transactions
                    SET status='paid', paid_at=NOW(), updated_at=NOW()
                    WHERE id=:id
                """),
                {"id": tx_id},
            )
            await self._log_event(
                tx_id,
                "status_changed",
                "system",
                from_status="checkout_pending",
                to_status="paid",
                payload={"payment_source": "free_order", "amount_cents": amount_cents},
            )

            await self.db.execute(
                text("""
                    UPDATE transactions
                    SET status='fulfilling', updated_at=NOW()
                    WHERE id=:id
                """),
                {"id": tx_id},
            )
            await self._log_event(
                tx_id,
                "status_changed",
                "system",
                from_status="paid",
                to_status="fulfilling",
                payload={"auto_transition": True, "trigger": "free_checkout"},
            )

            await order_service.mark_free_pending_delivery(order["id"], auto_commit=False)

            fulfillment_type = listing.get("fulfillment_type")
            if hasattr(fulfillment_type, "value"):
                fulfillment_type = fulfillment_type.value

            final_status = "fulfilling"
            from app.services.seller_workspace_delivery import is_workspace_source, fulfill_workspace_purchase
            if is_workspace_source(listing.get('source_delivery')):
                await fulfill_workspace_purchase(self.db,order['id'],auto_commit=False)
                await self.db.commit()
                final_status = 'delivered'
            elif fulfillment_type == "reference":
                source_delivery = listing.get("source_delivery") or {}
                if isinstance(source_delivery, str):
                    source_delivery = json.loads(source_delivery)
                await order_service.deliver_reference_order(
                    order["id"],
                    source_delivery=source_delivery,
                    auto_commit=True,
                )
                await self.db.execute(
                    text("""
                        UPDATE transactions
                        SET status='delivered', delivered_at=NOW(), updated_at=NOW()
                        WHERE id=:id
                    """),
                    {"id": tx_id},
                )
                await self._log_event(
                    tx_id,
                    "status_changed",
                    "system",
                    from_status="fulfilling",
                    to_status="delivered",
                    payload={
                        "auto_transition": True,
                        "trigger": "free_reference_delivery",
                        "order_id": str(order["id"]),
                    },
                )
                await self.db.commit()
                final_status = "delivered"
            else:
                await self.db.commit()

            return {
                "transaction_id": str(tx_id),
                "tx_number": tx["tx_number"],
                "status": final_status,
                "checkout_url": None,
                "order_id": str(order["id"]),
                "order_number": order["order_number"],
                "amount_cents": amount_cents,
                "currency": "USD",
                "listing_title": listing["title"],
            }

        # Create Stripe Checkout Session
        success_url = f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}/listings/{listing.get('slug', '')}"

        # SEPARATE CHARGES MODEL: Payment captured to PLATFORM account.
        # No transfer_data — funds stay on platform until settle() creates
        # an explicit Transfer after confirmation + hold period.
        # Gate 3 R1 Fix 3: Wrap Stripe call in try/except — rollback orphan
        # order + transaction writes if Stripe session creation fails.
        try:
            description = (listing.get("short_description") or listing.get("description") or "").strip()[:500] or "Data listing"
            checkout_session = await run_stripe(
                stripe.checkout.Session.create,
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "product_data": {"name": listing.get("title") or "Data listing", "description": description},
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"order_id": str(order["id"]), "transaction_id": str(tx_id), "tx_number": tx["tx_number"]},
                payment_intent_data={
                    "metadata": {"order_id": str(order["id"]), "transaction_id": str(tx_id)},
                },
            )
        except Exception:
            await self.db.rollback()
            raise

        # Store checkout session on Order
        await self.db.execute(
            text("UPDATE orders SET stripe_checkout_session_id=:sid, updated_at=NOW() WHERE id=:oid"),
            {"sid": checkout_session.id, "oid": order["id"]},
        )

        await self.db.commit()

        return {
            "transaction_id": str(tx_id),
            "tx_number": tx["tx_number"],
            "status": "checkout_pending",
            "checkout_url": checkout_session.url,
            "order_id": str(order["id"]),
            "order_number": order["order_number"],
            "amount_cents": amount_cents,
            "currency": "USD",
            "listing_title": listing["title"],
        }

    @bounded_payment_method
    async def handle_payment(self, tx_id: UUID, stripe_event: dict) -> dict:
        """Process checkout.session.completed. CHECKOUT_PENDING → PAID. Store payment_intent_id.

        Idempotent: if already paid/beyond, returns current state (safe for Stripe retries).
        """
        import json

        tx = await self.get_transaction(tx_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        from app.services.order_money_service import (
            _locked_initial_pair, ExpectedPaymentBinding,
            bind_initial_order_payment_intent_sync, OrderMoneyConflict,
        )
        if tx.get('order_id') is None:
            raise OrderMoneyConflict('Direct payment requires an existing linked Order')
        payment_intent_id = stripe_event.get('payment_intent')
        observed_order_id = tx['order_id']
        def bind(sync):
            order, linked = _locked_initial_pair(sync, observed_order_id)
            if linked is None or linked.id != tx_id or order.stripe_payment_intent_id != payment_intent_id:
                raise OrderMoneyConflict('Direct payment lacks original Order PI authority')
            binding = ExpectedPaymentBinding(
                UUID(str(order.id)), UUID(str(linked.id)), order.stripe_checkout_session_id, None,
                payment_intent_id, order.amount_cents, order.currency.upper(),
                UUID(str(order.buyer_id)), UUID(str(order.seller_id)), UUID(str(order.listing_id)),
                order.platform_fee_cents, order.seller_amount_cents)
            bind_initial_order_payment_intent_sync(
                sync, order_id=order.id, payment_intent_id=payment_intent_id,
                expected_transaction_id=tx_id, mode='direct_payment_completion',
                expected_binding=binding)
        await self.db.run_sync(bind)
        tx = await self.get_transaction(tx_id)
        # Idempotent: already paid or further along — return gracefully (Gate 3 P0-2)
        PAST_PAYMENT_STATUSES = {
            "paid", "fulfilling", "delivered", "confirmed", "settled",
            "in_escrow", "disputed", "dispute_resolved",
        }
        if tx["status"] in PAST_PAYMENT_STATUSES:
            logger.info(f"handle_payment: TX {tx_id} already at '{tx['status']}', returning idempotent")
            return tx
        if tx["status"] not in ("checkout_pending",):
            raise HTTPException(400, f"Cannot handle payment from status '{tx['status']}'")

        # Store payment_intent_id in metadata
        await self.db.execute(
            text("""
                UPDATE transactions SET
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{payment_intent_id}',
                        :pi_json
                    )
                WHERE id = :id
            """),
            {"id": tx_id, "pi_json": json.dumps(payment_intent_id)},
        )

        paid_tx = await self.transition(
            tx_id, "paid", "stripe",
            payload={"payment_intent_id": payment_intent_id},
        )

        # Auto-chain: paid → fulfilling so delivery endpoint can proceed
        return await self.transition(
            tx_id, "fulfilling", "system",
            payload={"auto_transition": True, "trigger": "handle_payment"},
        )

    async def mark_delivered(self, tx_id: UUID, delivery_proof: dict) -> dict:
        """Seller confirms delivery. FULFILLING → DELIVERED. Store delivery proof metadata.

        Also advances orders.status → 'delivered' so confirm_order() can proceed (Gate 3 P0-3).
        """
        import json

        tx = await self.get_transaction(tx_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        if tx.get('order_id'):
            await self.db.execute(text('select id from orders where id=:id for update'),{'id':tx['order_id']})
            await self.db.execute(text('select id from transactions where id=:id for update'),{'id':tx_id})
            tx = await self.get_transaction(tx_id)


        current = TransactionStatus(tx['status'])
        if TransactionStatus.DELIVERED not in VALID_TX_TRANSITIONS.get(current, []):
            raise HTTPException(400, f"Cannot deliver transaction in status: {current.value}")
        if tx.get('order_id') and tx.get('stripe_payment_intent_id'):
            from app.services.order_money_service import lock_order_money
            money = await lock_order_money(self.db, tx['order_id'])
            pending = await self.db.scalar(text("select exists(select 1 from stripe_events where refund_phase='admitted' and (refund_order_id=:oid or refund_payment_intent_id=:pi))"),
                {'oid':money.order.id,'pi':money.order.stripe_payment_intent_id})
            if (money.order.revoked or money.state.independent_revocation or money.state.refund_applied_cents or
                    money.state.reconciliation_reason or pending or
                    money.order.status in {'refunded','partially_refunded','disputed'}):
                raise HTTPException(409, 'Order money restriction prevents delivery')

        # Store delivery proof only after validating the current locked state.
        await self.db.execute(
            text("""
                UPDATE transactions SET
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{delivery_proof}',
                        :proof
                    )
                WHERE id = :id
            """),
            {"id": tx_id, "proof": json.dumps(delivery_proof)},
        )

        # Gate 3 P0-3: Sync orders.status → 'delivered' so confirm_order() can proceed.
        # The PG trigger syncs order→transaction, but here we need transaction→order.
        if tx.get("order_id"):
            synced = await self.db.execute(
                text("""
                    UPDATE orders SET status = 'delivered', updated_at = NOW()
                    WHERE id = :oid AND status IN ('pending_delivery', 'paid', 'in_escrow')
                    RETURNING id
                """),
                {"oid": tx["order_id"]},
            )
            if synced.scalar_one_or_none() is not None:
                # The real order-sync trigger already performed and recorded
                # delivery. A second delivered->delivered transition refuses.
                await self.db.execute(text('update transactions set delivered_at=coalesce(delivered_at,clock_timestamp()) where id=:id'),{'id':tx_id})
                actual = await self.get_transaction(tx_id)
                if actual['status'] != 'delivered':
                    raise HTTPException(409, 'Order delivery trigger did not persist transaction state')
                await self.db.commit()
                return actual

        return await self.transition(
            tx_id, "delivered", "seller",
            payload={"delivery_proof": delivery_proof},
        )

    async def confirm(self, tx_id: UUID, actor_type: str, actor_id: Optional[UUID] = None) -> dict:
        """Buyer confirms receipt. DELIVERED → CONFIRMED. Starts 48h hold period."""
        return await self.transition(
            tx_id, "confirmed", actor_type,
            actor_id=actor_id,
            payload={"hold_period_hours": 48},
        )

    async def settle(self, tx_id: UUID) -> dict:
        """After hold period, transfer to seller. Delegates to SettlementService."""
        from app.services.settlement_service import get_settlement_service
        settlement_svc = get_settlement_service(self.db)
        return await settlement_svc.settle(tx_id)

    async def dispute(self, tx_id: UUID, reason: str, category: str) -> dict:
        """Block settlement. DELIVERED → DISPUTED."""
        import json

        tx = await self.get_transaction(tx_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        if tx.get('order_id'):
            await self.db.execute(text('select id from orders where id=:id for update'),{'id':tx['order_id']})
            await self.db.execute(text('select id from transactions where id=:id for update'),{'id':tx_id})
            tx = await self.get_transaction(tx_id)


        # Store dispute details in metadata
        await self.db.execute(
            text("""
                UPDATE transactions SET
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{dispute}',
                        :dispute_data
                    )
                WHERE id = :id
            """),
            {"id": tx_id, "dispute_data": json.dumps({"reason": reason, "category": category})},
        )

        return await self.transition(
            tx_id, "disputed", "buyer",
            payload={"reason": reason, "category": category},
        )

    # === INTERNAL ===

    async def _log_event(
        self,
        transaction_id: UUID,
        event_type: str,
        actor_type: str,
        actor_id: Optional[UUID] = None,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ):
        """INSERT-only audit log. No UPDATE/DELETE methods exist. (M6)"""
        import json
        await self.db.execute(
            text("""
                INSERT INTO transaction_events
                    (id, transaction_id, event_type, actor_type, actor_id,
                     from_status, to_status, payload, created_at)
                VALUES
                    (:id, :tx_id, :event_type, :actor_type, :actor_id,
                     :from_status, :to_status, :payload, NOW())
            """),
            {
                "id": uuid4(),
                "tx_id": transaction_id,
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "from_status": from_status,
                "to_status": to_status,
                "payload": json.dumps(payload or {}),
            },
        )

    async def _next_tx_number(self) -> str:
        result = await self.db.execute(
            text("SELECT COALESCE(MAX(CAST(SUBSTRING(tx_number FROM 4) AS INTEGER)), 0) + 1 FROM transactions")
        )
        return f"TX-{result.scalar():06d}"

    async def _get_listing_for_agent(self, listing_id: UUID) -> dict:
        result = await self.db.execute(
            text(
                """
                SELECT l.id, l.title, l.slug, l.price, l.category, l.status, l.seller_id
                FROM listings l
                WHERE l.id = :id
                """
            ),
            {"id": listing_id},
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Listing not found")
        return dict(row)

    def _assert_agent_transaction_access(
        self,
        tx: dict[str, Any],
        key_row: dict[str, Any],
        api_key_id: UUID,
    ) -> None:
        if tx.get("buyer_type") != "agent":
            raise HTTPException(status_code=403, detail="Transaction is not agent-owned")
        if tx.get("party_id") and tx["party_id"] != key_row["org_id"]:
            raise HTTPException(status_code=403, detail="Cross-org access denied")

    async def _mark_agent_checkout_failed(
        self,
        *,
        tx_id: UUID,
        api_key_id: UUID,
        amount_cents: int,
        from_status: str,
        reason: str,
        order_id: Optional[UUID] = None,
    ) -> None:
        from app.services.agent_auth_service import AgentAuthService

        await AgentAuthService(self.db).rollback_spend(api_key_id, amount_cents)
        await self.db.execute(
            text(
                """
                UPDATE transactions
                SET status = 'agent_payment_failed', updated_at = NOW()
                WHERE id = :tx_id
                """
            ),
            {"tx_id": tx_id},
        )
        if order_id:
            await self.db.execute(
                text(
                    """
                    UPDATE orders
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE id = :order_id
                    """
                ),
                {"order_id": order_id},
            )
        await self._log_event(
            tx_id,
            "status_changed",
            "system",
            from_status=from_status,
            to_status="agent_payment_failed",
            payload={"reason": reason},
        )
        await self._log_agent_audit(
            api_key_id=api_key_id,
            tool_name="checkout",
            transaction_id=tx_id,
            request_payload={"transaction_id": str(tx_id)},
            response_payload={"status": "agent_payment_failed", "reason": reason},
            http_status=422,
            status="error",
            error_message=reason,
        )
        await self.db.commit()

    async def _log_agent_audit(
        self,
        *,
        api_key_id: Optional[UUID],
        tool_name: str,
        transaction_id: Optional[UUID],
        request_payload: Optional[Dict[str, Any]],
        response_payload: Optional[Dict[str, Any]],
        http_status: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        await self.db.execute(
            text(
                """
                INSERT INTO agent_audit_log (
                    id, api_key_id, tool_name, transaction_id,
                    request_payload, response_payload, http_status, status,
                    error_message, created_at
                ) VALUES (
                    :id, :api_key_id, :tool_name, :transaction_id,
                    CAST(:request_payload AS JSONB), CAST(:response_payload AS JSONB),
                    :http_status, :status, :error_message, NOW()
                )
                """
            ),
            {
                "id": uuid4(),
                "api_key_id": api_key_id,
                "tool_name": tool_name,
                "transaction_id": transaction_id,
                "request_payload": json.dumps(request_payload or {}),
                "response_payload": json.dumps(response_payload or {}),
                "http_status": http_status,
                "status": status,
                "error_message": error_message,
            },
        )


def get_transaction_service(db: AsyncSession) -> TransactionService:
    return TransactionService(db)
