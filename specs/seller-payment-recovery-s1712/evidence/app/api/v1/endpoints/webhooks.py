"""
Webhook Endpoints
=================

PURPOSE:
    Handle external webhooks:

    Stripe (BQ-WEBHOOK-AUDIT hardened):
    - checkout.session.completed (orders AND credit purchases)
    - account.updated / capability.updated (Connect onboarding)
    - charge.dispute.created / charge.dispute.closed
    - charge.refunded (full + partial)
    - payout.failed
    - payment_intent.payment_failed / payment_intent.succeeded

    Railway.com (INFRA-002):
    - Deployment status changes -> SysAdmin monitoring

CREATED: January 2026
UPDATED: February 23, 2026 (BQ-WEBHOOK-AUDIT) - Full audit hardening
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from collections.abc import Mapping
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_async_db, get_db
from app.domains.crm.core.stripe_connect_identity import (
    get_stripe_connect_user_sync,
    upsert_stripe_connect_identity,
)
from app.models.allai_state import StateEntity
from app.services.billing_service import BillingService
from app.services.deploy_monitor import deploy_monitor_service
from app.services.data_verification_payment_service import DataVerificationPaymentService
from app.services.data_verification_payin_service import (
    CONTRACT_VERSION as DATA_VERIFICATION_PAYIN_CONTRACT_VERSION,
    PURPOSE as DATA_VERIFICATION_PAYIN_PURPOSE,
    DataVerificationPayInError,
    DataVerificationPayInService,
)
from app.services.order_service import OrderService
from app.services.reconciliation_job import (
    reconcile_entity,
    resolve_targets,
    run_reconciliation_pass,
)
from app.services.stripe_connect_service import (
    derive_kyc_status,
    derive_onboarding_status,
)
from app.e2e.synthetic_exclusion import actor_is_synthetic, synthetic_trigger_metadata

logger = logging.getLogger(__name__)
router = APIRouter()
_billing_service = BillingService()


# =============================================================================
# STRIPE — CRITICAL EVENT TYPES (BQ-WEBHOOK-AUDIT section 5)
# =============================================================================
# Events where a processing failure MUST return 500 so Stripe retries.
CRITICAL_EVENT_TYPES = frozenset({
    "checkout.session.completed",
    "payment_intent.succeeded",
    "charge.refunded",
    "charge.dispute.created",
    "charge.dispute.closed",
    "payout.failed",
})


def _is_data_verification_payment_event(event: Mapping[str, Any]) -> bool:
    if event.get("type") not in {
        "payment_intent.amount_capturable_updated",
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "payment_intent.canceled",
    }:
        return False
    data = event.get("data")
    obj = data.get("object") if isinstance(data, Mapping) else None
    metadata = obj.get("metadata") if isinstance(obj, Mapping) else None
    return isinstance(metadata, Mapping) and set(metadata) == {"verification_id"}


# =============================================================================
# STRIPE WEBHOOK (BQ-WEBHOOK-AUDIT hardened)
# =============================================================================

def _verify_stripe_event(
    payload: bytes,
    sig_header: str,
) -> dict | stripe.StripeObject:
    """Verify Stripe signature with secret rotation support (section 3).

    Tries STRIPE_WEBHOOK_SECRET first, then STRIPE_WEBHOOK_SECRET_PREVIOUS.
    Raises HTTPException(400) on failure.
    """
    secrets_to_try = [settings.stripe_webhook_secret]
    prev = getattr(settings, "STRIPE_WEBHOOK_SECRET_PREVIOUS", None)
    if prev:
        secrets_to_try.append(prev)

    for secret in secrets_to_try:
        try:
            return stripe.Webhook.construct_event(
                payload, sig_header, secret, tolerance=300
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            continue

    logger.warning(
        "Stripe webhook signature verification failed (all secrets exhausted)"
    )
    raise HTTPException(status_code=400, detail="Invalid signature")


def _normalize_stripe_event(event: dict | stripe.StripeObject) -> dict:
    """Return a recursively materialized mapping for safe optional-field access."""
    if isinstance(event, stripe.StripeObject):
        return event.to_dict()
    return event


def _log_webhook(
    event_id: str,
    event_type: str,
    livemode: bool,
    stripe_account: str | None,
    request_id: str,
    processing_ms: int,
    result: str,
    error_class: str | None = None,
) -> None:
    """Emit structured log line per BQ-WEBHOOK-AUDIT section 7."""
    log_data = {
        "event_id": event_id,
        "event_type": event_type,
        "livemode": livemode,
        "stripe_account": stripe_account,
        "request_id": request_id,
        "processing_ms": processing_ms,
        "result": result,
        "error_class": error_class,
    }
    if result == "error":
        logger.error(f"stripe_webhook: {json.dumps(log_data)}")
    else:
        logger.info(f"stripe_webhook: {json.dumps(log_data)}")


def _metadata_marks_e2e(metadata: Any) -> bool:
    if not isinstance(metadata, dict):
        return False
    if synthetic_trigger_metadata(metadata).is_synthetic:
        return True
    for value in metadata.values():
        if isinstance(value, str) and (
            value.startswith("cs_e2e_mock_")
            or value.startswith("pi_e2e_mock_")
            or value.startswith("evt_e2e_mock_")
        ):
            return True
    return False


def _checkout_session_is_e2e_mock(session: Mapping[str, Any]) -> bool:
    metadata = session.get("metadata") or {}
    return (
        _metadata_marks_e2e(metadata)
        or str(session.get("id") or "").startswith("cs_e2e_mock_")
        or str(session.get("payment_intent") or "").startswith("pi_e2e_mock_")
    )


def _row_is_synthetic(row: Any) -> bool:
    if not row or not isinstance(row, Mapping):
        return False
    return actor_is_synthetic({"is_test": row["is_test"], "email": row["email"]}).is_synthetic


def _user_id_is_synthetic_sync(db: Session, user_id: Any) -> bool:
    if not user_id:
        return False
    row = db.execute(
        text("SELECT is_test, email FROM users WHERE id = :user_id"),
        {"user_id": str(user_id)},
    ).mappings().fetchone()
    return _row_is_synthetic(row)


def _stripe_connect_account_is_synthetic_sync(db: Session, stripe_account_id: str | None) -> bool:
    if not stripe_account_id:
        return False
    row = get_stripe_connect_user_sync(stripe_account_id, db)
    return _row_is_synthetic(row)


def _order_scope_is_synthetic_sync(
    db: Session,
    *,
    order_id: Any = None,
    payment_intent_id: str | None = None,
) -> bool:
    if not order_id and not payment_intent_id:
        return False
    where = "o.id = :order_id" if order_id else "o.stripe_payment_intent_id = :payment_intent_id"
    params = {"order_id": str(order_id)} if order_id else {"payment_intent_id": payment_intent_id}
    row = db.execute(
        text(f"""
            SELECT
                buyer_u.is_test AS buyer_is_test,
                buyer_u.email AS buyer_email,
                seller_u.is_test AS seller_is_test,
                seller_u.email AS seller_email,
                listing_u.is_test AS listing_seller_is_test,
                listing_u.email AS listing_seller_email
            FROM orders o
            LEFT JOIN users buyer_u ON buyer_u.id = o.buyer_id
            LEFT JOIN users seller_u ON seller_u.id = o.seller_id
            LEFT JOIN listings l ON l.id = o.listing_id
            LEFT JOIN users listing_u ON listing_u.id = l.seller_id
            WHERE {where}
            LIMIT 1
        """),
        params,
    ).mappings().fetchone()
    if not row or not isinstance(row, Mapping):
        return False
    return any(
        actor_is_synthetic({"is_test": row[f"{prefix}_is_test"], "email": row[f"{prefix}_email"]}).is_synthetic
        for prefix in ("buyer", "seller", "listing_seller")
    )


def _stripe_event_has_s1656_test_shape(
    event: Mapping[str, Any],
    *,
    normalized_stripe_account: str | None,
) -> bool:
    """Fail closed on production shapes before any S1656 admission lookup."""

    environment = str(settings.ENVIRONMENT or "").strip().lower()
    # These markers are intentionally evaluated before any allow predicate or
    # local user/attempt lookup. A production-shaped process cannot enter the
    # S1656 exception even when the event itself is otherwise perfectly bound.
    if (
        environment in {"prod", "production"}
        or settings.FRONTEND_URL == "https://ai.market"
        or bool(os.getenv("RAILWAY_ENVIRONMENT"))
        or bool(os.getenv("PRODUCTION"))
    ):
        return False

    if (
        settings.ENVIRONMENT != "test"
        or settings.STRIPE_TEST_MODE is not True
        or event.get("livemode") is not False
        or "account" in event
        or normalized_stripe_account is not None
    ):
        return False

    return True


def _stripe_event_is_s1656_test_payin(
    event: Mapping[str, Any],
    db: Session,
    *,
    normalized_stripe_account: str | None,
) -> bool:
    """Admit only the bound S1656 synthetic pay-in completion."""
    if not _stripe_event_has_s1656_test_shape(
        event, normalized_stripe_account=normalized_stripe_account,
    ) or event.get("type") != "checkout.session.completed":
        return False

    data = event.get("data")
    session = data.get("object") if isinstance(data, Mapping) else None
    metadata = session.get("metadata") if isinstance(session, Mapping) else None
    expected_metadata_keys = {
        "purpose",
        "contract_version",
        "setup_attempt_id",
        "party_id",
        "user_id",
    }
    if not isinstance(metadata, Mapping) or set(metadata) != expected_metadata_keys:
        return False
    if (
        metadata.get("purpose") != DATA_VERIFICATION_PAYIN_PURPOSE
        or metadata.get("contract_version")
        != DATA_VERIFICATION_PAYIN_CONTRACT_VERSION
    ):
        return False

    metadata_values = {
        key: metadata.get(key)
        for key in ("setup_attempt_id", "party_id", "user_id")
    }
    if not all(isinstance(value, str) for value in metadata_values.values()):
        return False
    try:
        parsed_ids = {key: UUID(value) for key, value in metadata_values.items()}
    except (TypeError, ValueError, AttributeError):
        return False
    if any(str(parsed_ids[key]) != value for key, value in metadata_values.items()):
        return False

    session_id = session.get("id")
    if not isinstance(session_id, str) or not session_id:
        return False

    row = db.execute(
        text("""
            SELECT
                u.is_test,
                u.email,
                a.id AS setup_attempt_id,
                a.party_id,
                a.auth_user_id,
                a.purpose,
                a.contract_version,
                a.checkout_session_id,
                a.superseded_by_attempt_id,
                a.expected_environment,
                a.expected_livemode
            FROM users u
            JOIN data_verification_payin_setup_attempt a
              ON a.auth_user_id = u.id
            WHERE u.id = :user_id
              AND a.id = :setup_attempt_id
        """),
        {
            "user_id": parsed_ids["user_id"],
            "setup_attempt_id": parsed_ids["setup_attempt_id"],
        },
    ).mappings().fetchone()
    if not row or not isinstance(row, Mapping) or row["is_test"] is not True:
        return False

    email = row["email"]
    if not isinstance(email, str):
        return False
    localpart, separator, domain = email.rpartition("@")
    if not localpart or separator != "@" or domain.lower() != "e2e-test.ai.market":
        return False

    return (
        str(row["setup_attempt_id"]) == metadata_values["setup_attempt_id"]
        and str(row["party_id"]) == metadata_values["party_id"]
        and str(row["auth_user_id"]) == metadata_values["user_id"]
        and row["purpose"] == metadata["purpose"]
        and row["contract_version"] == metadata["contract_version"]
        and row["checkout_session_id"] == session_id
        and row["superseded_by_attempt_id"] is None
        and row["expected_environment"] == "test"
        and row["expected_livemode"] is False
    )


def _stripe_event_is_s1656_test_purchase(
    event: Mapping[str, Any],
    db: Session,
    *,
    normalized_stripe_account: str | None,
) -> bool:
    """Admit only a local synthetic buyer's bound test purchase completion."""
    if not _stripe_event_has_s1656_test_shape(
        event, normalized_stripe_account=normalized_stripe_account,
    ):
        return False

    event_type = event.get("type")
    if event_type not in {"checkout.session.completed", "payment_intent.succeeded"}:
        return False
    data = event.get("data")
    obj = data.get("object") if isinstance(data, Mapping) else None
    metadata = obj.get("metadata") if isinstance(obj, Mapping) else None
    required_keys = {"order_id", "transaction_id"}
    allowed_keys = required_keys | ({"tx_number"} if event_type == "checkout.session.completed" else set())
    if (
        not isinstance(metadata, Mapping)
        or not required_keys <= set(metadata) <= allowed_keys
        or not all(isinstance(metadata[key], str) for key in required_keys)
    ):
        return False
    try:
        parsed_ids = {key: UUID(metadata[key]) for key in required_keys}
    except (TypeError, ValueError, AttributeError):
        return False
    if any(str(parsed_ids[key]) != metadata[key] for key in required_keys):
        return False

    row = db.execute(
        text("""
            SELECT buyer_u.is_test
            FROM orders o
            JOIN users buyer_u ON buyer_u.id = o.buyer_id
            WHERE o.id = :order_id
              AND o.transaction_id = :transaction_id
        """),
        {key: metadata[key] for key in required_keys},
    ).mappings().fetchone()
    return isinstance(row, Mapping) and row.get("is_test") is True


def _stripe_event_is_e2e_synthetic(event: dict, db: Session) -> bool:
    obj = event.get("data", {}).get("object", {}) or {}
    metadata = obj.get("metadata") or {}
    if _metadata_marks_e2e(metadata):
        return True

    event_type = event.get("type")
    if event_type in ("account.updated", "account.application.deauthorized", "capability.updated"):
        return _stripe_connect_account_is_synthetic_sync(db, obj.get("id") or event.get("account"))

    if event_type == "checkout.session.completed":
        if _user_id_is_synthetic_sync(db, metadata.get("user_id")):
            return True
        return _order_scope_is_synthetic_sync(db, order_id=metadata.get("order_id"))

    if event_type in ("payment_intent.succeeded", "payment_intent.payment_failed"):
        return _order_scope_is_synthetic_sync(
            db,
            order_id=metadata.get("order_id"),
            payment_intent_id=obj.get("id"),
        )

    if event_type in ("charge.refunded", "charge.dispute.created", "charge.dispute.closed"):
        return _order_scope_is_synthetic_sync(db, payment_intent_id=obj.get("payment_intent"))

    if event_type == "payout.failed":
        return _stripe_connect_account_is_synthetic_sync(db, obj.get("destination"))

    return False


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Handle Stripe webhooks (BQ-WEBHOOK-AUDIT hardened).

    Signature verification -> idempotency check -> event dispatch.
    Return code policy per section 5: 400 sig, 200 dup/unknown, 500 critical, 200+log non-critical.
    """
    start_ms = time.monotonic()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    request_id = request.headers.get("X-Request-ID", "")

    # -- 1. Signature verification (section 3) --
    if not sig_header:
        logger.warning("stripe_webhook: missing Stripe-Signature header")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    event = _normalize_stripe_event(_verify_stripe_event(payload, sig_header))

    event_id: str = event["id"]
    event_type: str = event["type"]
    livemode: bool = event.get("livemode", False)
    stripe_account: str | None = event.get("account")
    payload_sha256 = hashlib.sha256(payload).hexdigest()

    event_object = event.get("data", {}).get("object", {}) or {}
    event_metadata = event_object.get("metadata") or {}
    is_payin_checkout = (
        event_type == "checkout.session.completed"
        and isinstance(event_metadata, Mapping)
        and event_metadata.get("purpose") == DATA_VERIFICATION_PAYIN_PURPOSE
    )
    log_event_id = "redacted_payin_event" if is_payin_checkout else event_id

    if stripe_account and not is_payin_checkout:
        logger.info(f"stripe_webhook: Connect account present: {stripe_account}")

    # -- 2. Idempotency: dedup check that allows retries on failed events --
    # INSERT new row, or if a 'failed' row exists from a previous attempt,
    # UPDATE it to 'processing' so Stripe retries can re-process.
    # Rows with status 'completed' or 'processing' block re-processing (true dedup).
    dedup_result = db.execute(
        text("""
            INSERT INTO stripe_events
                (stripe_event_id, event_type, stripe_created, livemode,
                 stripe_account, processed_at, payload_sha256, status, payload_json, signature_valid)
            VALUES
                (:event_id, :event_type, :stripe_created, :livemode,
                 :stripe_account, NOW(), :sha256, 'processing', cast(:signed_payload as jsonb), true)
            ON CONFLICT (stripe_event_id) DO UPDATE
                SET status = CASE WHEN EXCLUDED.event_type='charge.refunded' AND stripe_events.status='completed' THEN stripe_events.status ELSE 'processing' END, processed_at = NOW()
                WHERE stripe_events.status = 'failed' OR EXCLUDED.event_type = 'charge.refunded'
            RETURNING stripe_event_id, error_message
        """),
        {
            "event_id": event_id,
            "event_type": event_type,
            "stripe_created": event.get("created"),
            "livemode": livemode,
            "stripe_account": None if is_payin_checkout else stripe_account,
            "sha256": payload_sha256,
            "signed_payload": json.dumps(event),
        },
    )
    dedup_row = dedup_result.fetchone()
    fulfillment_retry = bool(dedup_row and dedup_row[1] == "fulfillment_pending")
    if not dedup_row:
        # Row exists with status != 'failed' (completed/processing) — genuine duplicate
        db.rollback()
        elapsed = int((time.monotonic() - start_ms) * 1000)
        _log_webhook(log_event_id, event_type, livemode, stripe_account if not is_payin_checkout else None, request_id, elapsed, "duplicate")
        return {"status": "success", "message": "already processed"}
    if event_type == 'charge.refunded':
        previous = db.execute(text('select payload_json,signature_valid,payload_sha256 from stripe_events where stripe_event_id=:eid'), {'eid':event_id}).mappings().one()
        if previous['payload_json'] is not None and previous['payload_json'] != event:
            db.rollback()
            raise HTTPException(400, 'Refund event binding changed')
        db.execute(text('update stripe_events set payload_json=cast(:payload as jsonb),signature_valid=true where stripe_event_id=:eid'), {'eid':event_id,'payload':json.dumps(event)})
    db.flush()


    # -- 3. Dispatch to handler (same transaction as dedup row) --
    validated_payment = False
    repaired = False
    agent_attempt_event = False
    try:
        s1656_test_payin = _stripe_event_is_s1656_test_payin(
            event,
            db,
            normalized_stripe_account=stripe_account,
        )
        s1656_test_purchase = _stripe_event_is_s1656_test_purchase(
            event,
            db,
            normalized_stripe_account=stripe_account,
        )
        from app.services.s1681_refund_test_admission import admits_s1681_negative_refund, admits_s1681_failed_run_refund
        from app.services.workspace_refund_test_admission import admits_workspace_refund
        s1681_test_refund = (admits_s1681_negative_refund(event,db,normalized_stripe_account=stripe_account) or
                            admits_s1681_failed_run_refund(event,db,normalized_stripe_account=stripe_account) or
                            admits_workspace_refund(event,db,normalized_stripe_account=stripe_account))
        applied_refund_replay = (event_type=='charge.refunded' and db.scalar(text("select refund_phase='applied' from stripe_events where stripe_event_id=:id"),{'id':event_id}) is True)
        if not (s1656_test_payin or s1656_test_purchase or s1681_test_refund or applied_refund_replay) and _stripe_event_is_e2e_synthetic(event, db):
            db.execute(
                text("""
                    UPDATE stripe_events
                    SET status = 'completed',
                        error_message = 'e2e_scope_suppressed'
                    WHERE stripe_event_id = :eid
                """),
                {"eid": event_id},
            )
            db.commit()
            elapsed = int((time.monotonic() - start_ms) * 1000)
            _log_webhook(log_event_id, event_type, livemode, stripe_account if not is_payin_checkout else None, request_id, elapsed, "e2e_suppressed")
            return {"status": "success", "message": "e2e synthetic event suppressed"}

        finance_result = None
        checkout_data = None
        if _is_data_verification_payment_event(event):
            if settings.DATA_VERIFICATION_ENABLED:
                async for async_db in get_async_db():
                    try:
                        handled = await DataVerificationPaymentService(async_db).handle_webhook(
                            event_type=event_type,
                            payment_intent=event["data"]["object"],
                        )
                        if not handled:
                            raise RuntimeError("data-verification PaymentIntent is not bound")
                    except Exception:
                        await async_db.rollback()
                        raise
                    break

        elif event_type in ("account.updated", "capability.updated"):
            await _handle_account_update(event["data"]["object"], db)

        elif event_type == "account.application.deauthorized":
            await _handle_account_update(
                event["data"]["object"],
                db,
                deauthorized=True,
            )

        elif event_type == "checkout.session.completed":
            session_obj = event["data"]["object"]
            metadata = session_obj.get("metadata", {})
            if metadata.get("purpose") == DATA_VERIFICATION_PAYIN_PURPOSE:
                try:
                    setup_attempt_id = UUID(str(metadata.get("setup_attempt_id")))
                except (TypeError, ValueError):
                    # A signed but unbound event is terminal and has no local
                    # attempt authority. It changes no application state.
                    setup_attempt_id = None
                if setup_attempt_id is not None:
                    async for async_db in get_async_db():
                        try:
                            result = await DataVerificationPayInService(
                                async_db
                            ).finalize_data_verification_payin_setup(
                                setup_attempt_id,
                                trigger="webhook",
                                event_session_id=session_obj.get("id"),
                                event_metadata=metadata,
                                event_account=stripe_account,
                            )
                            if not result.terminal:
                                raise DataVerificationPayInError(
                                    result.code, retryable=True
                                )
                            if result.code == "payin_unknown_attempt_noop":
                                db.execute(
                                    text("""
                                        UPDATE stripe_events
                                        SET error_message = 'payin_unknown_attempt_noop'
                                        WHERE stripe_event_id = :eid
                                    """),
                                    {"eid": event_id},
                                )
                                logger.info(
                                    "stripe_webhook: payin_unknown_attempt_noop"
                                )
                        except Exception:
                            await async_db.rollback()
                            raise
                        break
            elif metadata.get("type") == "credit_purchase":
                _handle_credit_purchase_completed(session_obj, db)
                async for async_db in get_async_db():
                    try:
                        finance_result = await _billing_service.handle_stripe_event(event, async_db)
                        await async_db.commit()
                    except Exception:
                        await async_db.rollback()
                        raise
                    finally:
                        break
            elif metadata.get("type") == "serial_credit_topup":
                _handle_serial_credit_topup(session_obj, db)
            else:
                checkout_data = await _handle_checkout_completed(session_obj, db)
                if checkout_data and checkout_data.get("refused"):
                    db.rollback()
                    return {"status": "success", "message": "already processed"}
                if checkout_data and checkout_data.get("already_processed"):
                    repaired = settings.ENABLE_CANONICAL_TX and _repair_canonical_payment(
                        checkout_data, session_obj, db
                    )
                    repaired = repaired or (fulfillment_retry and checkout_data.get("order_status") in ("paid", "pending_delivery"))
                    if not repaired:
                        # No repair needed: undo the provisional dedup claim.
                        db.rollback()
                        elapsed = int((time.monotonic() - start_ms) * 1000)
                        _log_webhook(log_event_id, event_type, livemode, stripe_account, request_id, elapsed, "duplicate")
                        return {"status": "success", "message": "already processed"}
                validated_payment = bool(checkout_data and not checkout_data.get("already_processed"))
                if validated_payment and not checkout_data.get("marked_paid_inline"):
                    async for async_db in get_async_db():
                        try:
                            order_service = OrderService(async_db)
                            await order_service.mark_paid(
                                checkout_data["order_id"],
                                checkout_data["payment_intent_id"],
                                expected_binding=checkout_data["expected_binding"],
                            )
                        except Exception:
                            await async_db.rollback()
                            raise
                        finally:
                            break

                # BQ-BIZ-GOLD-PATH Gate 3: Store payment metadata on canonical TX.
                # Status sync handled by PG trigger (orders→transactions) — do NOT
                # open a separate async session to avoid deadlock (Gate 3 P0-1).
                if settings.ENABLE_CANONICAL_TX and validated_payment:
                    _tx_id = checkout_data.get("transaction_id")
                    if _tx_id:
                        _pi_id = session_obj.get("payment_intent")
                        db.execute(
                            text("""
                                UPDATE transactions SET
                                    metadata = jsonb_set(
                                        COALESCE(metadata, '{}'),
                                        '{payment_intent_id}',
                                        CAST(:pi_json AS jsonb)
                                    ),
                                    paid_at = NOW()
                                WHERE id = :id
                            """),
                            {"id": _tx_id, "pi_json": json.dumps(_pi_id)},
                        )
                        db.execute(
                            text("""
                                INSERT INTO transaction_events
                                    (id, transaction_id, event_type, actor_type, from_status, to_status, payload, created_at)
                                VALUES
                                    (:id, :tx_id, 'status_changed', 'stripe', 'checkout_pending', 'paid',
                                     :payload, NOW())
                            """),
                            {
                                "id": uuid4(),
                                "tx_id": _tx_id,
                                "payload": json.dumps({"payment_intent_id": _pi_id, "source": "webhook_inline"}),
                            },
                        )
                        logger.info(f"Canonical TX {_tx_id} payment metadata stored (trigger handles status)")

        elif event_type == "payment_intent.succeeded":
            _handle_payment_succeeded(event["data"]["object"], db)
            # Persist a retryable checkpoint before crossing the async service boundary.
            db.execute(
                text("UPDATE stripe_events SET status = 'failed', error_message = 'finance_pending' WHERE stripe_event_id = :eid"),
                {"eid": event_id},
            )
            db.commit()
            obtained_session=False
            async for async_db in get_async_db():
                obtained_session=True
                try:
                    finance_result = await _billing_service.handle_stripe_event(event, async_db)
                    await async_db.commit()
                except Exception:
                    await async_db.rollback()
                    raise
                break
            if not obtained_session:raise RuntimeError('Capture finance session unavailable')
            # BQ-BIZ-DELIVERY-CONFIDENCE: create delivery record with idempotency guard
            await _create_delivery_for_payment(event_id, event["data"]["object"])

        elif event_type == "payment_intent.payment_failed":
            pi = event["data"]["object"]
            from app.services.order_money_service import locate_agent_event_sync, OrderMoneyConflict
            # A signed original-agent locator cannot become a noncritical 200
            # when its authoritative database/provider evidence is unavailable.
            agent_attempt_event = isinstance(pi.get('metadata'),dict) and pi['metadata'].get('buyer_type')=='agent'
            try:
                agent_order_id=locate_agent_event_sync(db,pi)
            except OrderMoneyConflict:
                agent_attempt_event=True
                raise
            if agent_order_id is not None:
                agent_attempt_event=True
                db.execute(text("UPDATE stripe_events SET status='failed',error_message='finance_pending' WHERE stripe_event_id=:id"),{'id':event_id})
                db.commit()
                obtained = False
                async for async_db in get_async_db():
                    obtained = True
                    try:
                        finance_result = await _billing_service.handle_stripe_event(event,async_db)
                        await async_db.commit()
                    except BaseException:
                        await async_db.rollback()
                        raise
                    break
                if not obtained: raise RuntimeError('Agent reconciliation session unavailable')
            else:
                _handle_payment_failed_agent(pi, db)
            logger.warning(f"stripe_webhook: payment_intent.payment_failed pi={pi.get('id')}")

        elif event_type == "charge.refunded":
            from app.services.refund_processing_service import admit_order_refund_sync, process_order_refund
            admission = admit_order_refund_sync(db,event)
            obtained_session = False
            async for async_db in get_async_db():
                obtained_session = True
                try:
                    finance_result = await process_order_refund(async_db,event)
                except BaseException:
                    await async_db.rollback()
                    raise
                break
            if not obtained_session:
                raise RuntimeError('Refund effects session unavailable')
            return finance_result

        elif event_type == "charge.dispute.created":
            _handle_dispute_created(event["data"]["object"], db)

        elif event_type == "charge.dispute.closed":
            _handle_dispute_closed(event["data"]["object"], db)

        elif event_type == "payout.failed":
            await _handle_payout_failed(event["data"]["object"], db)

        else:
            # Unknown event — acknowledge, don't process (section 5)
            elapsed = int((time.monotonic() - start_ms) * 1000)
            _log_webhook(event_id, event_type, livemode, stripe_account, request_id, elapsed, "ignored")
            db.execute(
                text("UPDATE stripe_events SET status = 'completed' WHERE stripe_event_id = :eid"),
                {"eid": event_id},
            )
            db.commit()
            return {"status": "success"}

        # Persist a retryable checkpoint before crossing the async service boundary.
        # A crash or exception after payment commit must not suppress redelivery.
        if validated_payment or repaired:
            db.execute(
                text("UPDATE stripe_events SET status = 'failed', error_message = 'fulfillment_pending' WHERE stripe_event_id = :eid"),
                {"eid": event_id},
            )
            db.commit()
            from app.services.fulfillment_service import get_fulfillment_service

            obtained_session = False
            async for async_db in get_async_db():
                obtained_session = True
                try:
                    ful_result = await get_fulfillment_service(async_db).request_fulfillment(
                        checkout_data["order_id"]
                    )
                    if ful_result.get("success") is False:
                        raise RuntimeError("Fulfillment initiation failed")
                except Exception:
                    await async_db.rollback()
                    raise
                break
            if not obtained_session:
                raise RuntimeError("Fulfillment session unavailable")

        db.execute(
            text("UPDATE stripe_events SET status = 'completed', error_message = NULL WHERE stripe_event_id = :eid"),
            {"eid": event_id},
        )
        db.commit()

        elapsed = int((time.monotonic() - start_ms) * 1000)
        _log_webhook(log_event_id, event_type, livemode, stripe_account if not is_payin_checkout else None, request_id, elapsed, "processed")
        if finance_result is not None:
            return finance_result

    except Exception as e:
        # Rollback everything — dedup row + handler side effects
        db.rollback()

        elapsed = int((time.monotonic() - start_ms) * 1000)
        _log_webhook(log_event_id, event_type, livemode, stripe_account if not is_payin_checkout else None, request_id, elapsed, "error", e.__class__.__name__)

        # Return code policy (section 5)
        if event_type in CRITICAL_EVENT_TYPES or agent_attempt_event or _is_data_verification_payment_event(event):
            # Critical: rollback left no dedup row, so Stripe retry starts fresh
            logger.error(f"CRITICAL_WEBHOOK_FAILURE: {event_type} {log_event_id} — {e.__class__.__name__}")
            # Record failure for observability (separate transaction)
            try:
                db.execute(
                    text("""
                        INSERT INTO stripe_events
                            (stripe_event_id, event_type, stripe_created, livemode,
                             stripe_account, processed_at, payload_sha256, status, error_message, payload_json, signature_valid)
                        VALUES
                            (:event_id, :event_type, :stripe_created, :livemode,
                             :stripe_account, NOW(), :sha256, 'failed', :err, cast(:signed_payload as jsonb), :signature_valid)
                        ON CONFLICT (stripe_event_id) DO UPDATE
                            SET status = 'failed', error_message = EXCLUDED.error_message
                            WHERE stripe_events.status <> 'completed' AND stripe_events.refund_phase IS DISTINCT FROM 'applied'
                    """),
                    {
                        "event_id": event_id,
                        "event_type": event_type,
                        "stripe_created": event.get("created"),
                        "livemode": livemode,
                        "stripe_account": None if is_payin_checkout else stripe_account,
                        "sha256": payload_sha256,
                        # Preserve signed refund provenance even when admission
                        # could not start. A default empty payload strands retry.
                        "signed_payload": json.dumps(event) if event_type == 'charge.refunded' or agent_attempt_event else '{}',
                        "signature_valid": event_type == 'charge.refunded' or agent_attempt_event,
                        "err": (
                            e.__class__.__name__
                            if is_payin_checkout
                            else ("fulfillment_pending" if validated_payment or repaired else str(e)[:2000])
                        ),
                    },
                )
                db.commit()
            except Exception:
                db.rollback()
            raise HTTPException(status_code=500, detail="Processing failed for critical event")
        else:
            # Non-critical: record failure so duplicates are blocked
            logger.warning(f"NON_CRITICAL_WEBHOOK_ERROR: {event_type} {log_event_id} — {e.__class__.__name__}")
            try:
                db.execute(
                    text("""
                        INSERT INTO stripe_events
                            (stripe_event_id, event_type, stripe_created, livemode,
                             stripe_account, processed_at, payload_sha256, status, error_message)
                        VALUES
                            (:event_id, :event_type, :stripe_created, :livemode,
                             :stripe_account, NOW(), :sha256, 'failed', :err)
                        ON CONFLICT (stripe_event_id) DO UPDATE
                            SET status = 'failed', error_message = EXCLUDED.error_message
                            WHERE stripe_events.status <> 'completed' AND stripe_events.refund_phase IS DISTINCT FROM 'applied'
                    """),
                    {
                        "event_id": event_id,
                        "event_type": event_type,
                        "stripe_created": event.get("created"),
                        "livemode": livemode,
                        "stripe_account": None if is_payin_checkout else stripe_account,
                        "sha256": payload_sha256,
                        "err": (
                            e.__class__.__name__
                            if is_payin_checkout
                            else str(e)[:2000]
                        ),
                    },
                )
                db.commit()
            except Exception:
                db.rollback()
            return {"status": "error", "message": "non-critical processing failed"}

    return {"status": "success"}


# =============================================================================
# STRIPE EVENT HANDLERS
# =============================================================================

async def _upsert_stripe_connect_identity_bridge(
    *,
    user_id: UUID,
    stripe_account_id: str,
    onboarding_status: str | None = None,
    payouts_enabled: bool | None = None,
    details_submitted: bool | None = None,
    kyc_status: str | None = None,
    source: str,
) -> None:
    async with AsyncSessionLocal() as async_db:
        try:
            await upsert_stripe_connect_identity(
                user_id,
                stripe_account_id,
                onboarding_status=onboarding_status,
                payouts_enabled=payouts_enabled,
                details_submitted=details_submitted,
                kyc_status=kyc_status,
                source=source,
                db=async_db,
            )
            await async_db.commit()
        except Exception as exc:
            await async_db.rollback()
            logger.error(
                "stripe_connect_identity_bridge_upsert_failed",
                extra={
                    "event": "stripe_connect_identity_bridge_upsert_failed",
                    "user_id": str(user_id),
                    "stripe_account_id": stripe_account_id,
                    "source": source,
                    "writer": "webhook",
                    "exception_class": type(exc).__name__,
                    "severity": "high",
                },
                exc_info=True,
            )


async def _handle_account_update(
    account: dict,
    db: Session,
    *,
    deauthorized: bool = False,
) -> None:
    """Sync Connect account status to database (non-critical)."""
    stripe_id = account["id"]
    payouts_enabled = (
        False if deauthorized else account.get("payouts_enabled", False)
    )
    charges_enabled = (
        False if deauthorized else account.get("charges_enabled", False)
    )
    details_submitted = (
        False if deauthorized else account.get("details_submitted", False)
    )
    is_complete = details_submitted and charges_enabled
    onboarding_status = derive_onboarding_status(account, deauthorized=deauthorized)
    kyc_status = derive_kyc_status(account, deauthorized=deauthorized)

    user_update = db.execute(
        text("""
            UPDATE users
            SET stripe_payouts_enabled = :payouts,
                stripe_onboarding_complete = CASE
                    WHEN :is_complete THEN 'complete'
                    WHEN CAST(:details_submitted AS text) = 'true' THEN 'pending'
                    ELSE 'not_started'
                END,
                stripe_details_submitted = CAST(:details_submitted AS text)
            WHERE stripe_account_id = :stripe_id
        """),
        {
            "payouts": "true" if payouts_enabled else "false",
            "is_complete": is_complete,
            "details_submitted": "true" if details_submitted else "false",
            "stripe_id": stripe_id,
        },
    )
    if user_update.rowcount == 0:
        logger.error(
            "stripe_connect_user_update_zero_rows",
            extra={
                "event": "stripe_connect_user_update_zero_rows",
                "stripe_account_id": stripe_id,
                "webhook_handler": "account_update",
            },
        )
    user = db.execute(
        text("SELECT id FROM users WHERE stripe_account_id = :stripe_id"),
        {"stripe_id": stripe_id},
    ).mappings().fetchone()
    if user:
        await _upsert_stripe_connect_identity_bridge(
            user_id=user["id"],
            stripe_account_id=stripe_id,
            onboarding_status=onboarding_status,
            payouts_enabled=payouts_enabled,
            details_submitted=details_submitted,
            kyc_status=kyc_status,
            source="users",
        )

    logger.info(f"Updated Stripe account {stripe_id}: payouts={payouts_enabled}, complete={is_complete}")


# =============================================================================
# CREDIT PURCHASE HANDLER (BQ-073)
# =============================================================================

def _handle_credit_purchase_completed(session: dict, db: Session) -> None:
    """Handle checkout.session.completed for credit pack purchases.

    Atomically credits the user's balance using database-level row locking
    (SELECT ... FOR UPDATE) to prevent race conditions.
    """
    session_id = session["id"]
    payment_status = session.get("payment_status")
    metadata = session.get("metadata", {})

    if payment_status != "paid":
        logger.warning(f"Credit purchase {session_id} payment_status={payment_status}, expected 'paid'")
        return

    user_id_str = metadata.get("user_id")
    credit_cents_str = metadata.get("credit_cents")
    pack_id = metadata.get("pack_id", "unknown")
    price_cents_str = metadata.get("price_cents", "0")

    if not user_id_str or not credit_cents_str:
        logger.error(f"Credit purchase {session_id} missing metadata: user_id={user_id_str}, credit_cents={credit_cents_str}")
        return

    try:
        user_id = UUID(user_id_str)
        credit_cents = int(credit_cents_str)
        price_cents = int(price_cents_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Credit purchase {session_id} invalid metadata: {e}")
        return

    if credit_cents <= 0:
        logger.error(f"Credit purchase {session_id} non-positive credit_cents={credit_cents}")
        return

    result = db.execute(
        text("""
            SELECT id, balance_cents, total_purchased_cents
            FROM api_credits
            WHERE user_id = :user_id
            FOR UPDATE
        """),
        {"user_id": user_id},
    )
    existing = result.mappings().fetchone()

    if existing:
        db.execute(
            text("""
                UPDATE api_credits
                SET balance_cents = balance_cents + :credit_cents,
                    total_purchased_cents = total_purchased_cents + :credit_cents,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """),
            {"credit_cents": credit_cents, "user_id": user_id},
        )
        new_balance = existing["balance_cents"] + credit_cents
        logger.info(f"Credit purchase: user {user_id} +{credit_cents} (pack={pack_id}), balance {existing['balance_cents']} -> {new_balance}")
    else:
        db.execute(
            text("""
                INSERT INTO api_credits (
                    id, user_id, balance_cents, total_purchased_cents,
                    free_trial_cents, free_trial_used_cents, total_used_cents,
                    billing_mode, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :credit_cents, :credit_cents,
                    500, 0, 0, 'prepaid', NOW(), NOW()
                )
            """),
            {"id": uuid4(), "user_id": user_id, "credit_cents": credit_cents},
        )
        new_balance = credit_cents
        logger.info(f"Credit purchase: user {user_id} created ledger with {credit_cents} (pack={pack_id})")

    # Audit trail
    api_key_row = db.execute(
        text("SELECT id FROM customer_api_keys WHERE user_id = :uid AND is_active = true LIMIT 1"),
        {"uid": user_id},
    ).fetchone()

    if api_key_row:
        db.execute(
            text("""
                INSERT INTO api_usage (
                    id, user_id, api_key_id, service, endpoint,
                    request_type, input_tokens, output_tokens,
                    vendor_cost_cents, customer_cost_cents,
                    free_trial_used, status_code, response_time_ms, created_at
                ) VALUES (
                    :id, :user_id, :api_key_id, 'credit_purchase', '/credits/purchase',
                    :request_type, 0, 0, 0, :price_cents,
                    false, 200, 0, NOW()
                )
            """),
            {
                "id": uuid4(),
                "user_id": user_id,
                "api_key_id": api_key_row[0],
                "request_type": f"pack_{pack_id}",
                "price_cents": price_cents,
            },
        )

    logger.info(f"Credit purchase completed: session={session_id}, user={user_id}, pack={pack_id}, credits={credit_cents}, new_balance={new_balance}")


def _handle_serial_credit_topup(session: dict, db: Session) -> None:
    """Handle checkout.session.completed for serial credit top-ups.

    BQ-VZ-BALANCE-CLAIM: Credits go to the account (if linked), and also
    to the serial for backwards compatibility. Account auto-created from
    Stripe customer_email if not already present.
    """
    session_id = session["id"]
    payment_status = session.get("payment_status")
    metadata = session.get("metadata", {})

    if payment_status != "paid":
        logger.warning(f"Serial credit topup {session_id} payment_status={payment_status}, expected 'paid'")
        return

    serial_id_str = metadata.get("serial_id")
    amount_usd_str = metadata.get("amount_usd")
    serial_number = metadata.get("serial_number", "unknown")

    if not serial_id_str or not amount_usd_str:
        logger.error(f"Serial credit topup {session_id} missing metadata: serial_id={serial_id_str}, amount_usd={amount_usd_str}")
        return

    try:
        from decimal import Decimal
        serial_id = serial_id_str  # UUID as string for parameterized query
        amount_usd = Decimal(amount_usd_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Serial credit topup {session_id} invalid metadata: {e}")
        return

    if amount_usd <= 0:
        logger.error(f"Serial credit topup {session_id} non-positive amount_usd={amount_usd}")
        return

    # Convert to cents for account-level balance
    amount_cents = int(amount_usd * 100)

    result = db.execute(
        text("""
            SELECT id, credit_usd, used_usd, account_id
            FROM serials
            WHERE id = :serial_id
            FOR UPDATE
        """),
        {"serial_id": serial_id},
    )
    row = result.mappings().fetchone()

    if not row:
        logger.error(f"Serial credit topup {session_id}: serial {serial_id} not found")
        return

    # --- BQ-VZ-BALANCE-CLAIM: Account-based credit portability ---
    customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
    customer_id = session.get("customer")
    account_id = row["account_id"]

    if customer_email:
        customer_email = customer_email.strip().lower()

        if not account_id:
            # Check if account exists for this email
            acct_result = db.execute(
                text("SELECT id FROM accounts WHERE LOWER(email) = :email LIMIT 1"),
                {"email": customer_email},
            )
            acct_row = acct_result.mappings().fetchone()

            if acct_row:
                account_id = str(acct_row["id"])
            else:
                # Auto-create account from Stripe email
                acct_result = db.execute(
                    text("""
                        INSERT INTO accounts (email, stripe_customer_id, balance_cents, total_purchased_cents)
                        VALUES (:email, :stripe_cid, 0, 0)
                        RETURNING id
                    """),
                    {"email": customer_email, "stripe_cid": customer_id},
                )
                acct_row = acct_result.mappings().fetchone()
                account_id = str(acct_row["id"])
                logger.info(f"Auto-created account {account_id} for {customer_email}")

            # Link serial to account
            db.execute(
                text("UPDATE serials SET account_id = :account_id, updated_at = NOW() WHERE id = :serial_id"),
                {"account_id": account_id, "serial_id": serial_id},
            )

        # Credit account balance (SELECT ... FOR UPDATE for atomicity)
        db.execute(
            text("""
                UPDATE accounts
                SET balance_cents = balance_cents + :amount_cents,
                    total_purchased_cents = total_purchased_cents + :amount_cents,
                    stripe_customer_id = COALESCE(stripe_customer_id, :stripe_cid),
                    updated_at = NOW()
                WHERE id = :account_id
            """),
            {"amount_cents": amount_cents, "stripe_cid": customer_id, "account_id": account_id},
        )
        logger.info(
            f"Account {account_id} credited +{amount_cents}c "
            f"(serial={serial_number}, session={session_id})"
        )

    # Also credit serial-level balance (backwards compatibility)
    db.execute(
        text("""
            UPDATE serials
            SET credit_usd = credit_usd + :amount,
                payment_enabled = true,
                updated_at = NOW()
            WHERE id = :serial_id
        """),
        {"amount": amount_usd, "serial_id": serial_id},
    )

    new_credit = row["credit_usd"] + amount_usd
    logger.info(
        f"Serial credit topup completed: session={session_id}, "
        f"serial={serial_number} ({serial_id}), "
        f"+${amount_usd}, credit_usd {row['credit_usd']} -> {new_credit}"
    )


def _repair_canonical_payment(checkout_data: dict, session: dict, db: Session) -> bool:
    """Claim an unstamped canonical payment once, within the webhook commit.

    Lock the canonical row so concurrent redeliveries observe the winner's
    paid_at and cannot append another payment event or request fulfillment.
    """
    tx_id = checkout_data.get("transaction_id")
    if not tx_id or checkout_data.get("order_status") not in ("paid", "pending_delivery"):
        return False
    from app.services.order_money_service import _locked_initial_pair, validate_order_binding
    locked_order, locked_tx = _locked_initial_pair(db, checkout_data['order_id'])
    if locked_tx is None or locked_tx.id != UUID(str(tx_id)):
        raise ValueError('Canonical repair reverse binding mismatch')
    validate_order_binding(locked_order, locked_tx)
    tx = db.execute(
        text("SELECT paid_at FROM transactions WHERE id = :id FOR UPDATE"),
        {"id": tx_id},
    ).mappings().fetchone()
    if tx is None or tx["paid_at"] is not None:
        return False
    pi_id = session.get("payment_intent") or checkout_data.get("payment_intent_id")
    db.execute(
        text("""
            UPDATE transactions SET paid_at = COALESCE(:paid_at, NOW()),
                metadata = jsonb_set(COALESCE(metadata, '{}'),
                    '{payment_intent_id}', CAST(:pi_json AS jsonb))
            WHERE id = :id
        """),
        {"id": tx_id, "paid_at": checkout_data.get("paid_at"), "pi_json": json.dumps(pi_id)},
    )
    db.execute(
        text("""
            INSERT INTO transaction_events
                (id, transaction_id, event_type, actor_type, from_status, to_status, payload, created_at)
            SELECT :id, :tx_id, 'status_changed', 'stripe', 'checkout_pending', 'paid',
                CAST(:payload AS jsonb), NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM transaction_events
                WHERE transaction_id = :tx_id AND event_type = 'status_changed'
                    AND from_status = 'checkout_pending' AND to_status = 'paid'
            )
        """),
        {"id": uuid4(), "tx_id": tx_id,
         "payload": json.dumps({"payment_intent_id": pi_id, "source": "webhook_inline"})},
    )
    return True


async def _handle_checkout_completed(session: dict, db: Session) -> dict | None:
    """Handle checkout.session.completed for ORDER payments (critical).

    Validates the checkout session before the service-layer paid transition.
    """
    session_id = session["id"]
    payment_status = session.get("payment_status")
    payment_intent_id = session.get("payment_intent")
    metadata = session.get("metadata", {})
    order_id = metadata.get("order_id")

    if not order_id:
        logger.warning(f"Checkout session {session_id} missing order_id in metadata")
        return None

    result = db.execute(text("SELECT * FROM orders WHERE id = :id"), {"id": order_id})
    order = result.mappings().fetchone()

    if not order:
        logger.error(f"Order {order_id} not found for session {session_id}")
        return None

    refusal = {"already_processed": True, "refused": True} if order["status"] != "created" else None

    if payment_status != "paid":
        logger.warning(f"Checkout session {session_id} payment_status={payment_status}")
        return refusal

    # Gate 3 R1 Fix 4: Validate paid amount and currency match the order.
    # Prevents amount manipulation attacks via tampered checkout sessions.
    session_amount = session.get("amount_total")
    session_currency = (session.get("currency") or "").upper()
    order_currency = (order.get("currency") or "USD").upper()
    if session_amount != order["amount_cents"]:
        logger.critical(
            f"PAYMENT AMOUNT MISMATCH for order {order_id}: "
            f"session.amount_total={session_amount}, order.amount_cents={order['amount_cents']}. "
            f"Checkout session {session_id} — NOT processing payment."
        )
        return refusal
    if session_currency != order_currency:
        logger.critical(
            f"PAYMENT CURRENCY MISMATCH for order {order_id}: "
            f"session.currency={session_currency}, order.currency={order_currency}. "
            f"Checkout session {session_id} — NOT processing payment."
        )
        return refusal

    # Producers commit orders before saving Stripe IDs: match stored IDs when
    # present. Metadata cannot introduce a transaction the order does not own.
    tx_id = order.get("transaction_id")
    metadata_tx = metadata.get("transaction_id")
    stored_session = order.get("stripe_checkout_session_id")
    stored_pi = order.get("stripe_payment_intent_id")
    if (
        ("transaction_id" in metadata and (not tx_id or str(metadata_tx) != str(tx_id)))
        or (stored_session and session_id != stored_session)
        or (stored_pi and payment_intent_id != stored_pi)
    ):
        logger.warning("Checkout binding mismatch for order %s", order_id)
        return refusal
    if tx_id:
        canonical = db.execute(
            text("SELECT id FROM transactions WHERE id = :tx_id AND order_id = :order_id"),
            {"tx_id": tx_id, "order_id": order["id"]},
        ).mappings().fetchone()
        if not canonical:
            return refusal

    from app.services.order_money_service import ExpectedPaymentBinding, OrderMoneyConflict
    reverse_ids = db.execute(text("SELECT id FROM transactions WHERE order_id=:oid ORDER BY id"),
                             {"oid": order["id"]}).scalars().all()
    if reverse_ids != ([UUID(str(tx_id))] if tx_id else []):
        raise OrderMoneyConflict('Checkout reverse cardinality mismatch')
    expected_binding = None
    if tx_id:
        expected_binding = ExpectedPaymentBinding(
            order_id=UUID(str(order['id'])), transaction_id=UUID(str(tx_id)),
            stored_checkout_session_id=stored_session, signed_checkout_session_id=session_id,
            signed_payment_intent_id=payment_intent_id, signed_amount_cents=session_amount,
            signed_currency=session_currency, buyer_id=UUID(str(order['buyer_id'])),
            seller_id=UUID(str(order['seller_id'])), listing_id=UUID(str(order['listing_id'])),
            platform_fee_cents=order['platform_fee_cents'], seller_amount_cents=order['seller_amount_cents'])

    if order["status"] != "created":
        logger.info(f"Order {order_id} already processed (status={order['status']})")
        return {
            "already_processed": True,
            "order_id": UUID(str(order["id"])),
            "transaction_id": order.get("transaction_id"),
            "order_status": order["status"],
            "paid_at": order.get("paid_at"),
            "payment_intent_id": order.get("stripe_payment_intent_id"),
        }

    if _checkout_session_is_e2e_mock(session):
        from app.services.order_money_service import bind_initial_order_payment_intent_sync
        bind_initial_order_payment_intent_sync(db, order_id=UUID(str(order['id'])),
            payment_intent_id=payment_intent_id, expected_transaction_id=UUID(str(tx_id)) if tx_id else None,
            mode='checkout_completion', expected_binding=expected_binding)
        db.execute(
            text("""
                UPDATE orders
                SET stripe_payment_intent_id = :pi_id,
                    status = 'pending_delivery',
                    paid_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id
            """),
            {"id": order["id"], "pi_id": payment_intent_id},
        )
        db.execute(
            text("""
                INSERT INTO order_events (id, order_id, event_type, actor_type, metadata)
                VALUES (:id, :oid, 'paid', 'stripe', :meta)
            """),
            {
                "id": uuid4(),
                "oid": order["id"],
                "meta": json.dumps({"payment_intent_id": payment_intent_id, "e2e_synthetic": True}),
            },
        )
        return {
            "order_id": UUID(str(order["id"])),
            "payment_intent_id": payment_intent_id,
            "marked_paid_inline": True,
            "transaction_id": tx_id,
            "expected_binding": expected_binding,
        }

    return {
        "order_id": UUID(str(order["id"])),
        "payment_intent_id": payment_intent_id,
        "marked_paid_inline": False,
        "transaction_id": tx_id,
            "expected_binding": expected_binding,
    }


def _handle_payment_succeeded(payment_intent: dict, db: Session) -> None:
    """Backup confirmation — only processes if order wasn't already marked paid."""
    from app.services.order_money_service import locate_agent_event_sync
    if locate_agent_event_sync(db,payment_intent) is not None:
        # The independent capture transaction owns the complete original attempt.
        return
    pi_id = payment_intent["id"]
    result = db.execute(
        text("SELECT id, transaction_id FROM orders WHERE stripe_payment_intent_id = :pi_id AND status = 'created'"),
        {"pi_id": pi_id},
    )
    order = result.mappings().fetchone()
    if order:
        from app.services.order_money_service import lock_order_money_sync
        money = lock_order_money_sync(db,order['id'])
        if (money.order.status!='created' or money.order.revoked or money.state.independent_revocation or
                money.state.refund_applied_cents or money.state.reconciliation_reason):
            return
        if order["transaction_id"]:
            tx_row = db.execute(
                text("SELECT buyer_type FROM transactions WHERE id = :tx_id"),
                {"tx_id": order["transaction_id"]},
            ).mappings().fetchone()
            if tx_row and tx_row["buyer_type"] == "agent":
                updated = db.execute(
                    text(
                        """
                        UPDATE transactions
                        SET status = 'paid', paid_at = NOW(), updated_at = NOW()
                        WHERE id = :tx_id AND status = 'agent_payment_pending'
                        RETURNING id
                        """
                    ),
                    {"tx_id": order["transaction_id"]},
                ).fetchone()
                if updated:
                    db.execute(
                        text(
                            """
                            INSERT INTO transaction_events
                                (id, transaction_id, event_type, actor_type, from_status, to_status, payload, created_at)
                            VALUES
                                (:id, :tx_id, 'status_changed', 'stripe', 'agent_payment_pending', 'paid', :payload, NOW())
                            """
                        ),
                        {
                            "id": uuid4(),
                            "tx_id": order["transaction_id"],
                            "payload": json.dumps({"payment_intent_id": pi_id, "source": "payment_intent.succeeded"}),
                        },
                    )
                    _insert_agent_audit_log(
                        db,
                        tool_name="webhook_payment_succeeded",
                        transaction_id=order["transaction_id"],
                        response_payload={"status": "paid", "payment_intent_id": pi_id},
                    )
        db.execute(
            text("UPDATE orders SET status = 'pending_delivery', paid_at = NOW(), updated_at = NOW() WHERE id = :id"),
            {"id": order["id"]},
        )
        logger.info(f"Order {order['id']} marked as paid via payment_intent.succeeded (backup)")


def _handle_payment_failed_agent(payment_intent: dict, db: Session) -> None:
    """Agent-only payment_intent.payment_failed handler."""
    from app.services.order_money_service import locate_agent_event_sync,OrderMoneyConflict
    if locate_agent_event_sync(db,payment_intent) is not None:
        raise OrderMoneyConflict('Durable agent failure requires original provider reconciliation')
    pi_id = payment_intent["id"]
    order = db.execute(
        text("SELECT id, transaction_id FROM orders WHERE stripe_payment_intent_id = :pi_id"),
        {"pi_id": pi_id},
    ).mappings().fetchone()
    if not order or not order["transaction_id"]:
        return

    from app.services.order_money_service import lock_order_money_sync
    money = lock_order_money_sync(db,order['id'])
    if money.state.refund_applied_cents or money.state.reconciliation_reason:
        return
    tx_row = db.execute(
        text("SELECT buyer_type, api_key_id, amount_cents, status FROM transactions WHERE id = :tx_id"),
        {"tx_id": order["transaction_id"]},
    ).mappings().fetchone()
    if not tx_row or tx_row["buyer_type"] != "agent":
        return
    if tx_row["status"] != "agent_payment_pending":
        logger.info("Ignoring out-of-order payment_failed for tx=%s status=%s", order["transaction_id"], tx_row["status"])
        return

    db.execute(
        text(
            """
            UPDATE transactions
            SET status = 'agent_payment_failed', updated_at = NOW()
            WHERE id = :tx_id
            """
        ),
        {"tx_id": order["transaction_id"]},
    )
    db.execute(
        text(
            """
            UPDATE orders
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = :order_id
            """
        ),
        {"order_id": order["id"]},
    )
    if tx_row["api_key_id"]:
        db.execute(
            text(
                """
                UPDATE agent_api_keys
                SET spend_used = GREATEST(spend_used - :amount, 0),
                    updated_at = NOW()
                WHERE id = :api_key_id
                """
            ),
            {"amount": tx_row["amount_cents"] or 0, "api_key_id": tx_row["api_key_id"]},
        )
    db.execute(
        text(
            """
            INSERT INTO transaction_events
                (id, transaction_id, event_type, actor_type, from_status, to_status, payload, created_at)
            VALUES
                (:id, :tx_id, 'status_changed', 'stripe', 'agent_payment_pending', 'agent_payment_failed', :payload, NOW())
            """
        ),
        {
            "id": uuid4(),
            "tx_id": order["transaction_id"],
            "payload": json.dumps({"payment_intent_id": pi_id, "source": "payment_intent.payment_failed"}),
        },
    )
    _insert_agent_audit_log(
        db,
        tool_name="webhook_payment_failed",
        transaction_id=order["transaction_id"],
        response_payload={"status": "agent_payment_failed", "payment_intent_id": pi_id},
    )


async def _create_delivery_for_payment(stripe_event_id: str, payment_intent: dict) -> None:
    """BQ-BIZ-DELIVERY-CONFIDENCE: create delivery record on successful payment.

    Records webhook attempts and resumes delivery using the service metadata guard.
    """
    pi_id = payment_intent["id"]
    async for async_db in get_async_db():
        try:
            from app.services.delivery_service import DeliveryService

            svc = DeliveryService(async_db)

            # Look up order → transaction
            row = (await async_db.execute(
                text("""
                    SELECT t.id AS transaction_id
                    FROM orders o
                    JOIN transactions t ON t.order_id = o.id
                    WHERE o.stripe_payment_intent_id = :pi_id
                    LIMIT 1
                """),
                {"pi_id": pi_id},
            )).fetchone()

            if not row:
                logger.info(f"No transaction found for pi={pi_id}, skipping delivery creation")
                return

            transaction_id = row[0]

            # The marker records the attempt; delivery metadata guards completion.
            idem_key = f"delivery:{stripe_event_id}"
            inserted = await svc.record_stripe_webhook_idempotency(
                event_id=stripe_event_id,
                event_type="payment_intent.succeeded",
                idempotency_key=idem_key,
                payload_hash=hashlib.sha256(pi_id.encode()).hexdigest(),
                transaction_id=transaction_id,
            )
            if not inserted:
                logger.info(f"Delivery idempotency hit for event {stripe_event_id}, resuming delivery")

            # Create delivery record (service has its own internal idempotency via metadata flag)
            await svc.create_delivery_record(transaction_id, actor_type="system")
            logger.info(f"Delivery record created for transaction {transaction_id} (pi={pi_id})")
        except Exception as e:
            await async_db.rollback()
            logger.error(f"Failed to create delivery record for pi={pi_id}: {e}")
            raise
        break


# =============================================================================
# NEW HANDLERS (BQ-WEBHOOK-AUDIT section 6)
# =============================================================================

def _handle_dispute_created(dispute: dict, db: Session) -> None:
    """charge.dispute.created — flag order, revoke buyer access immediately (critical)."""
    payment_intent_id = dispute.get("payment_intent")
    if not payment_intent_id:
        logger.warning("charge.dispute.created: no payment_intent in event data")
        return

    order = db.execute(
        text("SELECT id, status FROM orders WHERE stripe_payment_intent_id = :pi_id"),
        {"pi_id": payment_intent_id},
    ).mappings().fetchone()

    if not order:
        logger.warning(f"charge.dispute.created: no order for pi={payment_intent_id}")
        return

    from app.services.order_money_service import lock_order_money_sync, cancel_reservation
    money = lock_order_money_sync(db,order['id'])
    pending = db.scalar(text("select exists(select 1 from stripe_events where refund_phase='admitted' and (refund_order_id=:oid or refund_payment_intent_id=:pi))"), {'oid':money.order.id,'pi':payment_intent_id})
    if money.state.dispatch_token:
        money.state.payout_state='reconciliation_required'
        money.state.reconciliation_reason='dispute_after_payout_ownership'
    else:
        cancel_reservation(money)
    money.state.revision += 1
    db.flush()
    if money.state.refund_applied_cents or money.order.status in {'refunded','partially_refunded'}:
        return
    db.execute(
        text("""
            UPDATE orders SET
                status = 'disputed',
                disputed_at = NOW(),
                revoked = true,
                revoke_reason = 'Stripe dispute filed',
                revoked_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
        """),
        {"id": order["id"]},
    )

    db.execute(
        text("""
            INSERT INTO order_events (id, order_id, event_type, actor_type, metadata)
            VALUES (:id, :oid, 'disputed', 'stripe', :meta)
        """),
        {
            "id": uuid4(),
            "oid": order["id"],
            "meta": json.dumps({"dispute_id": dispute.get("id"), "reason": dispute.get("reason")}),
        },
    )
    logger.info(f"Order {order['id']} disputed, access revoked")


def _handle_dispute_closed(dispute: dict, db: Session) -> None:
    """charge.dispute.closed — restore if won, keep revoked if lost (critical)."""
    payment_intent_id = dispute.get("payment_intent")
    status = dispute.get("status")  # "won", "lost", "charge_refunded"
    if not payment_intent_id:
        logger.warning("charge.dispute.closed: no payment_intent")
        return

    order = db.execute(
        text("SELECT id, status FROM orders WHERE stripe_payment_intent_id = :pi_id"),
        {"pi_id": payment_intent_id},
    ).mappings().fetchone()

    if not order:
        logger.warning(f"charge.dispute.closed: no order for pi={payment_intent_id}")
        return

    from app.services.order_money_service import lock_order_money_sync, cancel_reservation
    money = lock_order_money_sync(db,order['id'])
    pending = db.scalar(text("select exists(select 1 from stripe_events where refund_phase='admitted' and (refund_order_id=:oid or refund_payment_intent_id=:pi))"), {'oid':money.order.id,'pi':payment_intent_id})
    if (money.state.independent_revocation or money.state.refund_applied_cents or pending or
            money.state.reconciliation_reason or money.order.status in {'refunded','partially_refunded'}):
        return
    if status == "won":
        db.execute(
            text("""
                UPDATE orders SET
                    status = 'completed',
                    dispute_resolved_at = NOW(),
                    dispute_resolution = 'seller_wins',
                    revoked = false,
                    revoke_reason = NULL,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {"id": order["id"]},
        )
        db.execute(
            text("""
                INSERT INTO order_events (id, order_id, event_type, actor_type, metadata)
                VALUES (:id, :oid, 'dispute_resolved', 'stripe', :meta)
            """),
            {
                "id": uuid4(),
                "oid": order["id"],
                "meta": json.dumps({"result": "won", "dispute_id": dispute.get("id")}),
            },
        )
        logger.info(f"Order {order['id']} dispute won, access restored")
    else:
        # lost or charge_refunded
        db.execute(
            text("""
                UPDATE orders SET
                    status = 'refunded',
                    dispute_resolved_at = NOW(),
                    dispute_resolution = 'buyer_wins',
                    updated_at = NOW()
                WHERE id = :id
            """),
            {"id": order["id"]},
        )
        db.execute(
            text("""
                INSERT INTO order_events (id, order_id, event_type, actor_type, metadata)
                VALUES (:id, :oid, 'dispute_resolved', 'stripe', :meta)
            """),
            {
                "id": uuid4(),
                "oid": order["id"],
                "meta": json.dumps({"result": status, "dispute_id": dispute.get("id")}),
            },
        )
        logger.info(f"Order {order['id']} dispute {status}, kept revoked")


def _handle_refund(charge: dict, db: Session) -> None:
    raise RuntimeError('Refund effects require signed durable refund_processing_service admission')


def _insert_agent_audit_log(
    db: Session,
    *,
    tool_name: str,
    transaction_id: UUID,
    response_payload: dict,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO agent_audit_log (
                id, tool_name, transaction_id, response_payload,
                http_status, status, created_at
            ) VALUES (
                :id, :tool_name, :transaction_id, CAST(:response_payload AS JSONB),
                200, 'success', NOW()
            )
            """
        ),
        {
            "id": uuid4(),
            "tool_name": tool_name,
            "transaction_id": transaction_id,
            "response_payload": json.dumps(response_payload),
        },
    )


async def _handle_payout_failed(payout: dict, db: Session) -> None:
    """payout.failed — flag seller account (critical, section 6)."""
    destination = payout.get("destination")
    if not destination:
        logger.warning("payout.failed: no destination in payout")
        return

    user = get_stripe_connect_user_sync(destination, db)

    if not user:
        logger.warning(f"payout.failed: no user for Connect account {destination}")
        return

    db.execute(
        text("""
            UPDATE users SET
                stripe_payouts_enabled = 'false',
                updated_at = NOW()
            WHERE id = :id
        """),
        {"id": user["id"]},
    )
    try:
        await _upsert_stripe_connect_identity_bridge(
            user_id=user["id"],
            stripe_account_id=destination,
            payouts_enabled=False,
            source="users",
        )
    except Exception:
        logger.warning("payout.failed: identity bridge update failed for user %s", user["id"], exc_info=True)

    logger.info(f"payout.failed: user {user['id']} payouts disabled (destination={destination})")


# =============================================================================
# DEPLOY / CI FAILURE WEBHOOKS (Issue #26)
# =============================================================================

def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub's X-Hub-Signature-256 HMAC."""
    if not signature or not secret:
        return False

    expected_sig = signature[7:] if signature.startswith("sha256=") else signature
    computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return secrets.compare_digest(computed, expected_sig)


def verify_webhook_secret_header(header_value: str, secret: str) -> bool:
    """Verify a shared-secret webhook header using timing-safe comparison."""
    if not header_value or not secret:
        return False

    return secrets.compare_digest(header_value, secret)


def _extract_github_failure_event(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    workflow_run = payload.get("workflow_run") or {}
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        repository = {}
    if workflow_run.get("conclusion") != "failure":
        return None

    return {
        "workflow_name": workflow_run.get("name") or payload.get("workflow", "unknown"),
        "repository": _github_repo_full_name(payload.get("repository")),
        "run_id": workflow_run.get("id"),
        "commit_sha": workflow_run.get("head_sha"),
        "branch": workflow_run.get("head_branch"),
        "default_branch": repository.get("default_branch"),
        "failure_url": workflow_run.get("html_url") or workflow_run.get("url"),
        "failure_reason": workflow_run.get("conclusion"),
        "status": workflow_run.get("conclusion"),
    }


def _github_repo_full_name(repo: Any) -> str | None:
    return repo.get("full_name") if isinstance(repo, dict) and isinstance(repo.get("full_name"), str) else None


async def _find_build_for_github_ref(
    db: AsyncSession,
    *,
    repo_full_names: set[str],
    branch_name: str | None,
) -> StateEntity | None:
    if not repo_full_names or not branch_name:
        return None
    result = await db.execute(
        select(StateEntity)
        .where(StateEntity.kind == "build", StateEntity.deleted == False)  # noqa: E712
        .order_by(StateEntity.key)
    )
    for entity in result.scalars().all():
        targets = resolve_targets(entity)
        if targets.target_repo in repo_full_names and targets.target_branch == branch_name:
            return entity
    return None


async def _reconcile_github_entity(entity: StateEntity, db: AsyncSession) -> dict[str, Any]:
    try:
        updated = await reconcile_entity(entity, db)
    except Exception as exc:
        await db.rollback()
        logger.warning("GitHub webhook reconciliation failed for %s", entity.key, exc_info=True)
        return {"status": "failed", "bq_code": entity.key, "error": str(exc)}

    await db.commit()
    return {"status": "reconciled", "bq_code": updated.key}


async def _handle_github_reconciliation_webhook(
    github_event: str,
    payload: Dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    if github_event == "push" and payload.get("ref") == "refs/heads/main":
        stats = await run_reconciliation_pass()
        return {"status": "full_pass", "stats": stats}

    if github_event == "pull_request" and payload.get("action") in {"opened", "closed", "reopened", "synchronize"}:
        pr = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}
        head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
        repo_full_names = {
            name
            for name in (
                _github_repo_full_name(payload.get("repository")),
                _github_repo_full_name(head.get("repo")),
            )
            if name
        }
        entity = await _find_build_for_github_ref(
            db,
            repo_full_names=repo_full_names,
            branch_name=head.get("ref") if isinstance(head.get("ref"), str) else None,
        )
        if entity is None:
            return {"status": "no_matching_entity"}
        return await _reconcile_github_entity(entity, db)

    return {"status": "ignored"}


def _extract_railway_failure_event(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    deployment = payload.get("deployment") or {}
    status = str(
        deployment.get("status")
        or payload.get("status")
        or payload.get("event")
        or ""
    ).upper()
    if status not in {"FAILED", "CRASHED"}:
        return None

    service = payload.get("service") or {}
    environment = payload.get("environment") or payload.get("environmentName")
    if isinstance(environment, dict):
        environment = environment.get("name") or environment.get("id")

    failure_reason = (
        deployment.get("failureReason")
        or deployment.get("reason")
        or payload.get("failure_reason")
        or payload.get("error")
        or payload.get("message")
        or status
    )

    return {
        "service_name": service.get("name") or payload.get("serviceName") or "unknown",
        "service_id": service.get("id") or payload.get("serviceId"),
        "environment": environment or "unknown",
        "deploy_id": deployment.get("id") or payload.get("deployId") or payload.get("id"),
        "deployment_id": deployment.get("id") or payload.get("deployId") or payload.get("id"),
        "failure_reason": failure_reason,
        "status": status.lower(),
        "summary": payload.get("summary"),
    }


@router.post("/github")
async def github_failure_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """Receive GitHub webhooks and dispatch by event type."""
    github_secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", None)
    if not github_secret:
        logger.error("GitHub webhook: GITHUB_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=503, detail="GitHub webhook not configured")

    raw_payload = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(raw_payload, signature_header, github_secret):
        logger.warning("GitHub webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    github_event = request.headers.get("X-GitHub-Event", "")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if github_event in {"push", "pull_request"}:
        return await _handle_github_reconciliation_webhook(github_event, payload, db)

    if github_event != "workflow_run":
        logger.info("GitHub webhook: no-op for unsupported event %s", github_event or "<missing>")
        return JSONResponse(
            status_code=202,
            content={"status": "accepted", "reason": f"unsupported event {github_event or 'missing'}"},
        )

    failure_event = _extract_github_failure_event(payload)
    if not failure_event:
        return {"status": "ignored", "reason": "workflow_run conclusion was not failure"}

    background_tasks.add_task(deploy_monitor_service.handle_failure, "github", failure_event)
    return {"status": "queued", "source": "github", "run_id": failure_event["run_id"]}


@router.post("/railway")
async def railway_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Receive Railway failed deploy webhooks and dispatch deploy_monitor."""
    webhook_secret = getattr(settings, "RAILWAY_WEBHOOK_SECRET", None)
    if not webhook_secret:
        logger.error("Railway webhook: RAILWAY_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=503, detail="Railway webhook not configured")

    raw_payload = await request.body()
    secret_header = request.headers.get("X-Railway-Webhook-Secret", "")
    if not verify_webhook_secret_header(secret_header, webhook_secret):
        logger.warning("Railway webhook: secret verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    failure_event = _extract_railway_failure_event(payload)
    if not failure_event:
        return {"status": "ignored", "reason": "deploy status was not failed"}

    background_tasks.add_task(deploy_monitor_service.handle_failure, "railway", failure_event)
    return {"status": "queued", "source": "railway", "deploy_id": failure_event["deploy_id"]}


# =============================================================================
# TELEGRAM WEBHOOK (S59 - HITL Integration with Iterative Feedback)
# =============================================================================

@router.post("/telegram")
async def telegram_webhook(request: Request):
    """
    Handle Telegram webhook updates.

    Handles:
    - Callback queries (inline button clicks for HITL Accept/Modify)
    - Text AND voice messages as feedback when in Modify mode
    - Regular messages via TelegramService

    HITL Flow:
    1. User clicks Accept -> Action approved
    2. User clicks Modify -> Enters feedback mode
    3. Next message (text OR voice) -> Processed as feedback
    4. Agent regenerates content based on feedback
    5. Loop until Accept

    Phase: S59 - Agent Framework HITL
    """
    try:
        update_data = await request.json()
        update_type = "callback_query" if "callback_query" in update_data else "message" if "message" in update_data else "other"
        logger.info(f"Telegram webhook received: update_type={update_type}")

        from app.services.hitl_service import hitl_service

        # Handle callback queries (inline button clicks)
        if "callback_query" in update_data:
            callback_query = update_data["callback_query"]
            callback_id = callback_query.get("id")
            data = callback_query.get("data", "")
            user = callback_query.get("from", {})
            user_id = user.get("id")
            message = callback_query.get("message", {})
            chat = message.get("chat", {})
            chat_id = chat.get("id")

            # Handle HITL callbacks (accept/modify/details/cancel)
            if data.startswith("hitl_"):
                success = await hitl_service.handle_callback(
                    callback_query_id=callback_id,
                    data=data,
                    user_id=user_id,
                    chat_id=chat_id
                )
                return {"status": "success" if success else "error"}

        # Handle messages (text or voice)
        if "message" in update_data:
            message = update_data["message"]
            chat = message.get("chat", {})
            chat_id = chat.get("id")

            # Check if this chat is in HITL feedback mode FIRST
            if chat_id and hitl_service.is_in_feedback_mode(chat_id):
                feedback_text = None

                # Get text directly if it's a text message
                if message.get("text"):
                    feedback_text = message.get("text")

                # Transcribe if it's a voice message
                elif message.get("voice") or message.get("audio"):
                    from app.services.telegram_relay import telegram_service  # BQ-077: relay

                    # Send processing indicator
                    await telegram_service.send_message(
                        "\U0001f3a4 Processing your voice feedback...",
                        chat_id=chat_id
                    )

                    # Download and transcribe voice
                    voice = message.get("voice") or message.get("audio")
                    file_id = voice.get("file_id")

                    if file_id:
                        try:
                            import httpx
                            bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

                            # Get file path from Telegram
                            async with httpx.AsyncClient() as client:
                                file_response = await client.get(
                                    f"https://api.telegram.org/bot{bot_token}/getFile",
                                    params={"file_id": file_id},
                                    timeout=10.0
                                )
                                file_data = file_response.json()

                                if file_data.get("ok"):
                                    file_path = file_data["result"]["file_path"]

                                    # Download audio file
                                    audio_response = await client.get(
                                        f"https://api.telegram.org/file/bot{bot_token}/{file_path}",
                                        timeout=30.0
                                    )
                                    audio_bytes = audio_response.content

                                    # Transcribe via Whisper
                                    from app.services.voice_transcription_service import transcribe_audio
                                    feedback_text = await transcribe_audio(audio_bytes)

                                    if feedback_text:
                                        # Show transcription
                                        await telegram_service.send_message(
                                            f"\U0001f4dd <b>Feedback:</b>\n<i>\"{feedback_text}\"</i>",
                                            parse_mode="HTML",
                                            chat_id=chat_id
                                        )
                        except Exception as e:
                            logger.error(f"Error transcribing voice feedback: {e}")
                            await telegram_service.send_message(
                                "\u274c Could not transcribe voice. Please type your feedback.",
                                chat_id=chat_id
                            )

                # Process the feedback if we got it
                if feedback_text:
                    updated_request = await hitl_service.process_feedback(chat_id, feedback_text)
                    if updated_request:
                        logger.info(f"HITL: Processed feedback for {updated_request.id}, now v{updated_request.version}")
                        return {"status": "success", "mode": "hitl_feedback"}

        # Fall through to regular TelegramService handling
        from app.services.telegram_relay import telegram_service  # BQ-077: relay
        success = await telegram_service.process_webhook_update(update_data)

        return {"status": "success" if success else "error"}

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        logger.warning(f"WEBHOOK_SOFT_ERROR: telegram error={str(e)[:200]}")
        return {"status": "error", "message": str(e)[:100]}
