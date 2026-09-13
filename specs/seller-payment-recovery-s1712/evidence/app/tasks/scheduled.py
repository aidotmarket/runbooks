"""
Scheduled Background Tasks
==========================

PURPOSE:
    Periodic tasks executed by Celery Beat.
    Migrated from APScheduler (TD-010).

TASKS:
    - process_reminders: Send inquiry reminder emails
    - process_auto_confirmations: Auto-confirm delivered orders
    - poll_gmail_inbox: Break-glass Gmail polling fallback, disabled by default

PHASE: 3.H.3 (TD-010 Resolution)
CREATED: 2026-01-26
"""

import asyncio
import json
import logging
import os
import random
import socket
import urllib.error
import urllib.request
from functools import wraps
from datetime import date, datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis_cache import get_cache_client

logger = logging.getLogger(__name__)

CELERY_RUNTIME_HEARTBEAT_TTL_SECONDS = 180


# =============================================================================
# ASYNC HELPER
# =============================================================================

def async_task(func):
    """
    Decorator to run async functions in Celery tasks.
    
    Celery tasks are synchronous by default, so we need to
    run async code in an event loop.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(func(*args, **kwargs))
    return wrapper


def _event_archival_task(func):
    """Apply the retention hold before the async task adapter does any work."""
    async_wrapper = async_task(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not settings.EVENT_ARCHIVAL_ENABLED:
            logger.warning(
                "Celery task skipped: event archival disabled by "
                "EVENT_ARCHIVAL_ENABLED=False"
            )
            return {"status": "disabled", "reason": "event_archival_disabled"}
        return async_wrapper(*args, **kwargs)

    return wrapper


# =============================================================================
# SCHEDULED TASKS
# =============================================================================

@shared_task(name="app.tasks.scheduled.celery_runtime_heartbeat")
@async_task
async def celery_runtime_heartbeat():
    """Write a Redis freshness signal proving beat -> broker -> worker execution."""
    hostname = socket.gethostname()
    timestamp = datetime.now(timezone.utc).isoformat()
    key = f"celery:heartbeat:worker:{hostname}"
    payload = {
        "timestamp_utc_iso": timestamp,
        "worker_hostname": hostname,
        "worker_pid": os.getpid(),
    }

    client = await get_cache_client()
    if client is None:
        raise RuntimeError("Redis unavailable for celery runtime heartbeat")

    await client.setex(
        key,
        CELERY_RUNTIME_HEARTBEAT_TTL_SECONDS,
        json.dumps(payload),
    )
    logger.info(
        "celery.runtime.heartbeat",
        extra={"worker": hostname, "ts": timestamp},
    )
    return key


@celery_app.task(
    name="app.tasks.scheduled.aggregate_metadata_corpus_error_priors",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
)
@async_task
async def aggregate_metadata_corpus_error_priors(
    self,
    capture_day: str | None = None,
):
    """Persist the prior UTC day's immutable correction-delta counters."""

    if (
        settings.CORPUS_CORRECTION_DELTA_ENABLED is not True
        or settings.CORPUS_METADATA_ERROR_PRIOR_AGGREGATION_ENABLED is not True
    ):
        return {"status": "disabled"}

    from app.services.metadata_corpus_capture import aggregate_error_priors

    day = (
        date.fromisoformat(capture_day)
        if capture_day is not None
        else datetime.now(timezone.utc).date() - timedelta(days=1)
    )
    async with AsyncSessionLocal() as db:
        async with db.begin():
            counters = await aggregate_error_priors(
                db,
                capture_day=day,
                settings_object=settings,
            )
    logger.info(
        "S1396 metadata error-prior aggregation complete",
        extra={"capture_day": day.isoformat(), "counter_count": len(counters)},
    )
    return {"status": "persisted", "day": day.isoformat(), "counters": counters}


@celery_app.task(
    name="app.tasks.scheduled.process_request_publication",
    bind=True,
    max_retries=1,
    default_retry_delay=120,
    autoretry_for=(Exception,),
)
@async_task
async def process_request_publication(self):
    """Refresh publication state, matching, and independent delivery channels."""
    from app.services.data_request_service import expire_stale_requests
    from app.services.request_publication_service import (
        process_publication_discovery_outbox,
        reconcile_legacy_publication_decisions,
        redrive_unavailable_publication_checks,
        redrive_verified_email_publication_checks,
    )
    from app.services.request_matching_service import (
        drain_request_match_deliveries,
        inspect_initial_match_reports,
        process_inventory_rematches,
        process_request_matching_outbox,
    )

    async with AsyncSessionLocal() as db:
        expired = await expire_stale_requests(db)
        reconciled = await reconcile_legacy_publication_decisions(db, limit=1000)
        email_retried = await redrive_verified_email_publication_checks(db, limit=100)
        retried = await redrive_unavailable_publication_checks(db, limit=100)
        discovered = await process_publication_discovery_outbox(db, limit=100)
        matched = await process_request_matching_outbox(db, limit=50)
        inventory = await process_inventory_rematches(db, limit=25)
        delivered = await drain_request_match_deliveries(db, limit=50)
        inspected = await inspect_initial_match_reports(db, limit=3)
    return {
        "expired": expired,
        "legacy_reconciled": reconciled,
        "email_checks_retried": email_retried,
        "checks_retried": retried,
        "discovery_processed": discovered,
        "matching": matched,
        "inventory": inventory,
        "delivery": delivered,
        "inspection": inspected,
    }

@celery_app.task(
    name="app.tasks.scheduled.process_support_sla_breaches",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
@async_task
async def process_support_sla_breaches(self):
    """Process overdue support tasks and rerun classifier on SLA breach."""
    logger.info("Celery task: process_support_sla_breaches starting")

    try:
        async with AsyncSessionLocal() as db:
            from app.services.crm_support_service import CRMSupportService
            from app.services.support_ticket_service import process_support_ticket_response_window_breaches

            service = CRMSupportService(db)
            now = datetime.now(timezone.utc)
            crm_count = await service.process_sla_breaches(now=now)
            ticket_count = await process_support_ticket_response_window_breaches(db, now=now)
            await db.commit()
            count = crm_count + ticket_count
            logger.info(
                "Celery task complete: processed %d support SLA breaches (%d crm, %d tickets)",
                count,
                crm_count,
                ticket_count,
            )
            return count
    except Exception as e:
        logger.error(f"Celery task failed (support_sla_breaches): {e}", exc_info=True)
        raise


@celery_app.task(
    name="app.tasks.scheduled.process_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
@async_task
async def process_reminders(self):
    """
    Background task: Process pending inquiry reminders.
    
    Schedule: Hourly at minute 5
    Migrated from: app/core/scheduler.py::process_reminders_job
    """
    logger.info("Celery task: process_reminders starting")
    
    try:
        async with AsyncSessionLocal() as db:
            from app.services.inquiry_service import InquiryService
            
            service = InquiryService(db)
            count = await service.process_pending_reminders()
            
            if count > 0:
                logger.info(f"Celery task complete: sent {count} reminders")
            else:
                logger.debug("Celery task complete: no reminders to send")
            
            return {"reminders_sent": count}
            
    except Exception as e:
        logger.error(f"Celery task failed (reminders): {e}", exc_info=True)
        raise


@celery_app.task(
    name="app.tasks.scheduled.process_auto_confirmations",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
@async_task
async def process_auto_confirmations(self):
    """
    Background task: Process order auto-confirmations.
    
    Schedule: Hourly at minute 10
    Migrated from: app/core/scheduler.py::process_auto_confirmations_job
    """
    logger.info("Celery task: process_auto_confirmations starting")
    
    try:
        async with AsyncSessionLocal() as db:
            from app.services.order_service import get_order_service
            
            service = get_order_service(db)
            count = await service.process_auto_confirmations()
            
            if count > 0:
                logger.info(f"Celery task complete: auto-confirmed {count} orders")
            else:
                logger.debug("Celery task complete: no orders to auto-confirm")
            
            return {"orders_confirmed": count}
            
    except Exception as e:
        logger.error(f"Celery task failed (auto-confirmations): {e}", exc_info=True)
        raise


@celery_app.task(
    name="app.tasks.scheduled.poll_gmail_inbox",
    bind=True,
    max_retries=3,
    soft_time_limit=50,  # 50 seconds soft limit (schedule is 60s)
    time_limit=55,       # 55 seconds hard limit
)
@async_task
async def poll_gmail_inbox(self):
    """
    Background task: Poll Gmail for unread messages.
    
    Schedule: Every 60 seconds
    Migrated from: app/core/scheduler.py::process_gmail_inbox
    
    Phase 6.A.3.c - Gmail integration
    """
    logger.info("Celery task: poll_gmail_inbox starting")

    if not settings.GMAIL_POLLING_ENABLED:
        logger.info(
            "Gmail polling skipped: disabled by GMAIL_POLLING_ENABLED=False; push webhook path is canonical"
        )
        return {"status": "disabled", "messages_processed": 0}
    
    try:
        async with AsyncSessionLocal() as db:
            from app.services.gmail_service import GmailService
            
            service = GmailService(db)
            
            # Authenticate (uses env var fallback if no DB token)
            if not await service.authenticate():
                logger.warning("Gmail polling: Authentication failed, skipping this run")
                return {"status": "auth_failed", "messages_processed": 0}
            
            # Fetch unread emails
            messages = await service.fetch_unread()
            
            processed_count = 0
            if messages:
                logger.info(f"Gmail polling: Found {len(messages)} unread messages")
                
                for msg in messages:
                    subject_preview = msg.subject[:50] if msg.subject else "(No Subject)"
                    logger.info(f"  - From: {msg.sender}, Subject: {subject_preview}...")

                    try:
                        # Mark as processed
                        await service.mark_processed(
                            msg.id,
                            msg.thread_id,
                            {
                                "sender": msg.sender,
                                "subject": msg.subject,
                                "recipient": msg.recipient
                            }
                        )
                        processed_count += 1
                    except Exception as e:
                        await db.rollback()
                        from app.services.support_ticket_service import record_support_email_dlq

                        await record_support_email_dlq(
                            db,
                            gmail_message_id=msg.id,
                            gmail_thread_id=getattr(msg, "thread_id", None),
                            reason="processing_failure",
                            detail={"error": str(e), "error_type": type(e).__name__},
                        )
                        await db.commit()
                        logger.error(
                            "Gmail polling: message processing failed; captured in DLQ and continuing",
                            extra={"gmail_message_id": msg.id, "gmail_thread_id": getattr(msg, "thread_id", None)},
                            exc_info=True,
                        )
                        continue
            else:
                logger.debug("Gmail polling: No unread messages")
            
            return {"status": "success", "messages_processed": processed_count}
            
    except Exception as e:
        if _is_transient_gmail_poll_error(e):
            retries = getattr(getattr(self, "request", None), "retries", 0)
            if retries < 3:
                countdown = _support_email_retry_countdown(retries)
                logger.warning(
                    "Gmail polling transient failure; retrying in %s seconds (attempt %s/3)",
                    countdown,
                    retries + 1,
                    exc_info=True,
                )
                raise self.retry(exc=e, countdown=countdown)

            async with AsyncSessionLocal() as db:
                from app.services.support_ticket_service import record_support_email_dlq

                await record_support_email_dlq(
                    db,
                    gmail_message_id=f"poll:{getattr(getattr(self, 'request', None), 'id', 'unknown')}",
                    gmail_thread_id=None,
                    reason="gmail_polling_retry_exhausted",
                    detail={"error": str(e), "error_type": type(e).__name__},
                    retry_count=retries,
                )
                await db.commit()
            logger.error("Celery task exhausted transient Gmail polling retries", exc_info=True)
            return {"status": "dlq", "reason": "gmail_polling_retry_exhausted"}

        logger.error(f"Celery task failed (gmail_polling): {e}", exc_info=True)
        raise


def _support_email_retry_countdown(retries: int) -> int:
    base_delays = (60, 300, 900)
    base = base_delays[min(max(retries, 0), len(base_delays) - 1)]
    return base + random.randint(0, max(1, base // 10))


def _is_transient_gmail_poll_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "resp", None), "status", None)
    if status in {429, 500, 502, 503, 504}:
        return True
    text_value = str(exc).lower()
    return any(token in text_value for token in ("timeout", "connection reset", "429", "500", "502", "503", "504"))


# =============================================================================
# BQ-124 PHASE B1: NIGHTLY RECONCILER
# =============================================================================

@celery_app.task(
    name="app.tasks.scheduled.run_qdrant_reconciler",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    soft_time_limit=200,   # 3min20s soft limit (budget is 3min)
    time_limit=210,        # 3min30s hard limit
)
@async_task
async def run_qdrant_reconciler(self):
    """
    Nightly reconciler: detect and repair Qdrant sync drift.

    Schedule: Daily at 04:00 UTC
    BQ-124 Phase B1 — Cursor-based incremental algorithm.
    Budget: max 100 requeues per run AND max 3 minutes runtime.
    """
    logger.info("Celery task: run_qdrant_reconciler starting")

    try:
        from app.tasks.reconciler import run_reconciler

        results = await run_reconciler()
        logger.info(
            "Celery task complete: reconciler checked=%d requeued=%d",
            results.get("checked", 0),
            results.get("requeued", 0),
        )
        return results

    except Exception as e:
        logger.error(f"Celery task failed (reconciler): {e}", exc_info=True)
        raise


# =============================================================================
# BQ-124 PHASE C: KD JANITOR GOVERNANCE
# =============================================================================

@celery_app.task(
    name="app.tasks.scheduled.run_kd_janitor",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    soft_time_limit=300,   # 5 min soft limit
    time_limit=330,        # 5.5 min hard limit
)
@async_task
async def run_kd_janitor(self):
    """
    Weekly KD Janitor: create governance proposals for stale/orphaned entities.

    Schedule: Weekly (Sunday 05:00 UTC)
    BQ-124 Phase C — Proposal-only governance. NO entity/event mutations.
    """
    logger.info("Celery task: run_kd_janitor starting")

    try:
        from app.services.janitor_service import run_janitor

        results = await run_janitor()
        logger.info(
            "Celery task complete: janitor created=%d expired=%d",
            results.get("proposals_created", 0),
            results.get("proposals_expired", 0),
        )
        return results

    except Exception as e:
        logger.error(f"Celery task failed (janitor): {e}", exc_info=True)
        raise


@celery_app.task(
    name="app.tasks.scheduled.cleanup_notifications",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
)
@async_task
async def cleanup_notifications(self):
    """Archive stale notifications using read_at-aware retention."""
    logger.info("Celery task: cleanup_notifications starting")

    try:
        async with AsyncSessionLocal() as db:
            total_archived = 0
            batch_size = 500

            while True:
                result = await db.execute(
                    text(
                        f"""
                        UPDATE notifications
                        SET archived_at = NOW(), updated_at = NOW()
                        WHERE id IN (
                            SELECT id
                            FROM notifications
                            WHERE archived_at IS NULL
                              AND (
                                (read_at IS NULL AND created_at < NOW() - INTERVAL '90 days')
                                OR (read_at IS NOT NULL AND read_at < NOW() - INTERVAL '365 days')
                              )
                            ORDER BY created_at
                            LIMIT {batch_size}
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING id
                        """
                    )
                )
                batch = result.fetchall()
                batch_count = len(batch)
                total_archived += batch_count
                await db.commit()
                if batch_count < batch_size:
                    break

            logger.info("Celery task complete: archived %s notifications", total_archived)
            return {"archived": total_archived}
    except Exception as e:
        logger.error(f"Celery task failed (cleanup_notifications): {e}", exc_info=True)
        raise


@celery_app.task(
    name="app.tasks.scheduled.cleanup_stuck_agent_transactions",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
)
@async_task
async def cleanup_stuck_agent_transactions(self):
    """Fail agent_payment_pending transactions older than one hour and release reserved spend."""
    logger.info("Celery task: cleanup_stuck_agent_transactions starting")

    try:
        from app.services.order_money_service import OrderMoneyConflict
        from app.services.transaction_service import TransactionService

        # The scan owns no row locks. Each candidate has its own transaction;
        # never acquire another order beneath a previous transaction/agent lock.
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(text("""
                SELECT id, order_id FROM transactions
                WHERE status = 'agent_payment_pending'
                  AND created_at < NOW() - INTERVAL '1 hour'
                ORDER BY id
            """))).mappings().all()
            await db.rollback()
            cleaned = 0
            for candidate in rows:
                try:
                    row = await TransactionService(db).lock_stale_agent_payment(
                        candidate['id'], candidate['order_id'])
                except OrderMoneyConflict:
                    await db.rollback()
                    continue
                if row is None:
                    await db.rollback()
                    continue
                # The real order sync trigger is the sole linked cancellation
                # event writer. Unlinked rows retain agent_payment_failed.
                if row['order_id']:
                    await db.execute(text("""
                        UPDATE orders SET status='cancelled', updated_at=NOW() WHERE id=:id
                    """), {'id': row['order_id']})
                else:
                    await db.execute(text("""
                        UPDATE transactions SET status='agent_payment_failed', updated_at=NOW()
                        WHERE id=:id
                    """), {'id': row['id']})
                if row['api_key_id']:
                    await db.execute(text("""
                        UPDATE agent_api_keys
                        SET spend_used=GREATEST(spend_used-:amount,0), updated_at=NOW()
                        WHERE id=:id
                    """), {'id': row['api_key_id'], 'amount': row['amount_cents']})
                if not row['order_id']:
                    await db.execute(
                        text(
                            """
                            INSERT INTO transaction_events
                                (id, transaction_id, event_type, actor_type, from_status, to_status, payload, created_at)
                            VALUES
                                (gen_random_uuid(), :tx_id, 'status_changed', 'system',
                                 'agent_payment_pending', 'agent_payment_failed',
                                 '{"source":"cleanup_stuck_agent_transactions"}'::jsonb, NOW())
                            """
                        ),
                        {"tx_id": row["id"]},
                    )
                await db.execute(
                    text(
                        """
                        INSERT INTO agent_audit_log (
                            id, api_key_id, tool_name, transaction_id, response_payload,
                            http_status, status, created_at
                        ) VALUES (
                            gen_random_uuid(), :api_key_id, 'cleanup_stuck_agent_transactions', :tx_id,
                            CAST(:payload AS JSONB), 200, 'success', NOW()
                        )
                        """
                    ),
                    {
                        "api_key_id": row.get("api_key_id"),
                        "tx_id": row["id"],
                        "payload": json.dumps({"status": "cancelled" if row["order_id"] else "agent_payment_failed"}),
                    },
                )
                await db.commit()
                cleaned += 1
            return {"cleaned": cleaned}
    except Exception as e:
        logger.error(f"Celery task failed (cleanup_stuck_agent_transactions): {e}", exc_info=True)
        raise


@celery_app.task(
    name="app.tasks.scheduled.poll_backup_watchdog",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    soft_time_limit=90,
    time_limit=120,
)
def poll_backup_watchdog(self):
    """Invoke the SysAdmin backup staleness check via internal REST."""
    backend = os.environ.get("RAILWAY_BACKEND_URL", "https://ai-market-backend-production.up.railway.app").rstrip("/")
    api_key = os.environ.get("INTERNAL_API_KEY", "")
    if not api_key:
        logger.warning("Backup watchdog poll skipped: INTERNAL_API_KEY not configured")
        return {"status": "skipped", "reason": "missing_internal_api_key"}

    url = f"{backend}/api/v1/internal/backup-watchdog"
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json", "X-Internal-API-Key": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:500]
        logger.error("Backup watchdog REST poll failed: HTTP %s %s", exc.code, detail)
        raise

    report = body.get("report") or {}
    logger.info("Backup watchdog REST poll complete: overall_status=%s", report.get("overall_status"))
    return {"status": "ok", "overall_status": report.get("overall_status")}


# =============================================================================
# BQ-124 PHASE D3: EVENT ARCHIVAL (runs AFTER reconciler, isolated [M8])
# =============================================================================

@celery_app.task(
    name="app.tasks.scheduled.run_event_archival",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    soft_time_limit=300,   # 5 min soft limit
    time_limit=330,        # 5.5 min hard limit
)
@_event_archival_task
async def run_event_archival(self):
    """
    Event archival: move events older than 90 days to archive table.

    Schedule: Daily at 04:30 UTC (30 min AFTER reconciler at 04:00).
    BQ-124 Phase D3 — Isolated from reconciler. If archival fails,
    reconciler results are NOT rolled back. [M8]
    Budget: max 500 events per run.
    """
    logger.info("Celery task: run_event_archival starting")

    try:
        from app.services.event_archival_service import run_event_archival

        results = await run_event_archival()
        logger.info(
            "Celery task complete: archival archived=%d "
            "delete_reconciled=%d reconciliation_errors=%d qdrant_deleted=%d",
            results.get("archived", 0),
            results.get("delete_reconciled", 0),
            results.get("reconciliation_errors", 0),
            results.get("qdrant_deleted", 0),
        )
        return results

    except Exception as e:
        logger.error(f"Celery task failed (archival): {e}", exc_info=True)
        raise


# =============================================================================
# MANUAL TRIGGER TASKS (for testing/admin)
# =============================================================================

@celery_app.task(name="app.tasks.scheduled.health_check")
def health_check():
    """
    Simple health check task to verify Celery is working.
    
    Usage: 
        from app.tasks.scheduled import health_check
        result = health_check.delay()
        print(result.get(timeout=5))
    """
    logger.info("Celery health check: OK")
    return {"status": "healthy", "worker": "celery"}
