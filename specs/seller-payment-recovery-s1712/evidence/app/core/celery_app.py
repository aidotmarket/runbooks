"""
Celery Application Configuration
================================

PURPOSE:
    Distributed task queue for background job processing.
    Runs alongside the web application's APScheduler jobs.

ARCHITECTURE:
    - Broker: Redis (existing infrastructure)
    - Result Backend: Redis
    - Worker: Separate process from FastAPI
    - Beat: Integrated scheduler for periodic tasks

TASKS:
    - process_reminders: Hourly inquiry reminders
    - process_auto_confirmations: Hourly order confirmations
    - gmail_polling: Disabled by default during push-only soak
    - vectoraiz: Async embedding and indexing tasks

PHASE: 3.H.3 (TD-010 Resolution) + vectorAIz Phase 2
CREATED: 2026-01-26
UPDATED: vectorAIz Phase 2 - Added async embedding tasks
"""

import logging
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_init
from kombu import Queue

from app.core.config import settings

logger = logging.getLogger(__name__)


@worker_init.connect
def admit_worker_application_role(**kwargs):
    """Refuse in the parent before pool/consumer startup; Beat never sends this."""
    try:
        from app.core.seller_schema_readiness import main

        result = main()
    except Exception:
        # Signal.send swallows ordinary exceptions. Never include driver details.
        result = 1
    if result != 0:
        logger.error("Seller schema unavailable to application role; worker not started.")
        raise SystemExit(1)
    # The worker does not execute FastAPI's lifespan. Configure ADC before
    # forking so each child can decrypt the stored profile runtime bindings.
    if settings.GCP_SERVICE_ACCOUNT_JSON:
        try:
            from app.core.gcp_credentials import setup_gcp_credentials

            credentials_ready = setup_gcp_credentials()
        except Exception:
            credentials_ready = False
        if not credentials_ready:
            logger.error("Worker encryption credentials unavailable; worker not started.")
            raise SystemExit(1)

# =============================================================================
# CELERY APP CONFIGURATION
# =============================================================================

def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.
    
    Uses Redis as both broker and result backend.
    """
    # Use REDIS_URL from settings, fallback to localhost for local dev
    broker_url = settings.REDIS_URL or "redis://localhost:6379/0"
    result_backend = broker_url
    visibility_timeout = settings.CELERY_VISIBILITY_TIMEOUT
    
    app = Celery(
        "ai_market",
        broker=broker_url,
        backend=result_backend,
        include=[
            "app.tasks.scheduled",  # Periodic tasks
            "app.tasks.orders",     # Order-related tasks
            "app.tasks.emails",     # Email tasks
            "app.tasks.vectoraiz",  # vectorAIz embedding tasks
            "app.tasks.translations",  # Listing translation tasks
            "app.tasks.share_assets",  # Listing share card asset tasks
            "app.tasks.version_notifications",  # S1097 version availability emails
            "app.tasks.lifecycle_emails",  # S1548 signup lifecycle email outbox
            "app.tasks.seller_workspace_profile",  # W3 metadata-only control tasks
        ]
    )
    
    # Celery configuration
    app.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        
        # Task execution
        broker_connection_retry_on_startup=True,
        broker_transport_options={"visibility_timeout": visibility_timeout},
        task_acks_late=True,  # Acknowledge after task completion (reliability)
        task_reject_on_worker_lost=True,  # Requeue if worker dies mid-task
        worker_prefetch_multiplier=1,  # One task at a time per worker (fairness)
        worker_max_tasks_per_child=500,  # Recycle worker processes periodically

        # Result backend settings
        result_backend_always_retry=True,
        result_expires=3600,  # Results expire after 1 hour
        
        # Beat scheduler settings (for periodic tasks)
        beat_scheduler="celery.beat:PersistentScheduler",
        beat_schedule_filename="/tmp/celerybeat-schedule",  # Persist schedule
        
        # Queue configuration
        task_queues=(
            Queue("default", routing_key="default"),
            Queue("scheduled", routing_key="scheduled"),
            Queue("emails", routing_key="emails"),
            Queue("vectoraiz", routing_key="vectoraiz"),  # Dedicated queue for embedding tasks
            Queue("translations", routing_key="translations"),
            Queue(
                "seller_workspace_profile_control",
                routing_key="seller_workspace_profile_control",
            ),
        ),
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
        
        # Logging
        worker_hijack_root_logger=False,  # Don't override our logging config
    )
    
    # ==========================================================================
    # BEAT SCHEDULE (Periodic Tasks)
    # ==========================================================================
    # APScheduler owns periodic reminders, auto-confirmations and Buyer Request
    # publication. Keep their Celery tasks callable, but do not schedule them here.
    # SCHEDULER_MODE=celery or SKIP_SERVICES=1 leaves those workflows ownerless;
    # changing that topology requires a separately reviewed ownership migration.
    app.conf.beat_schedule = {
        "celery-worker-heartbeat": {
            "task": "app.tasks.scheduled.celery_runtime_heartbeat",
            "schedule": 60.0,
            "options": {"queue": "scheduled"},
        },

        # CRM support SLA breach scan - every 5 minutes
        "process-support-sla-breaches": {
            "task": "app.tasks.scheduled.process_support_sla_breaches",
            "schedule": 300.0,
            "options": {"queue": "scheduled"},
        },

        # vectorAIz search index optimization - daily at 3 AM UTC
        "vectoraiz-optimize-index": {
            "task": "vectoraiz.optimize_search_index",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "vectoraiz"},
        },
        "seller-listing-search": {
            "task": "vectoraiz.seller_listing_search",
            "schedule": 60.0,
            "options": {"queue": "vectoraiz"},
        },
        "translations-drain-outbox": {
            "task": "translations.drain_outbox",
            "schedule": 300.0,
            "options": {"queue": "translations"},
        },
        "share-assets-drain-outbox": {
            "task": "share_assets.drain_outbox",
            "schedule": 300.0,
            "options": {"queue": "scheduled"},
        },
        "version-notifications-drain-outbox": {
            "task": "version_notifications.drain_outbox",
            "schedule": 300.0,
            "options": {"queue": "scheduled"},
        },
        "lifecycle-emails-drain-outbox": {
            "task": "lifecycle_emails.drain_outbox",
            "schedule": 300.0,
            "options": {"queue": "emails"},
        },
        "lifecycle-emails-attempt-sweep": {
            "task": "lifecycle_emails.attempt_sweep",
            "schedule": crontab(minute=35),
            "options": {"queue": "emails"},
        },
        "lifecycle-emails-daily-sweep": {
            "task": "lifecycle_emails.daily_sweep",
            "schedule": crontab(hour=15, minute=0),
            "options": {"queue": "emails"},
        },
        "metadata-corpus-error-priors-daily": {
            "task": "app.tasks.scheduled.aggregate_metadata_corpus_error_priors",
            "schedule": crontab(hour=2, minute=45),
            "options": {"queue": "scheduled"},
        },
        "seller-workspace-profile-reconcile": {
            "task": "seller_workspace_profile.reconcile",
            "schedule": 20.0,
            "options": {"queue": "seller_workspace_profile_control"},
        },
        "seller-workspace-profile-expire-cleanup": {
            "task": "seller_workspace_profile.expire_cleanup",
            "schedule": 60.0,
            "options": {"queue": "seller_workspace_profile_control"},
        },

        # BQ-124 Phase B1: Nightly Qdrant reconciler - daily at 4 AM UTC
        "qdrant-reconciler-nightly": {
            "task": "app.tasks.scheduled.run_qdrant_reconciler",
            "schedule": crontab(hour=4, minute=0),
            "options": {"queue": "scheduled"},
        },

        # BQ-124 Phase C: KD Janitor governance - weekly Sunday 5 AM UTC
        "kd-janitor-weekly": {
            "task": "app.tasks.scheduled.run_kd_janitor",
            "schedule": crontab(hour=5, minute=0, day_of_week=0),
            "options": {"queue": "scheduled"},
        },
        "cleanup-notifications-daily": {
            "task": "app.tasks.scheduled.cleanup_notifications",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "scheduled"},
        },
        "cleanup-stuck-agent-transactions": {
            "task": "app.tasks.scheduled.cleanup_stuck_agent_transactions",
            "schedule": crontab(minute=20),
            "options": {"queue": "scheduled"},
        },
        # DEFERRED (S757.w, Max-approved option A): backup-watchdog-hourly is DISABLED until
        # the backup cutover. Re-enable as the FINAL cutover step, only after the Railway backup
        # cron service exists and AWS_BACKUP_WRITER_* are live in the web service -- otherwise the
        # watchdog fail-closes on absent backups and pages a premature P0. Re-add verbatim:
        #     "backup-watchdog-hourly": {
        #         "task": "app.tasks.scheduled.poll_backup_watchdog",
        #         "schedule": crontab(minute=30),
        #         "options": {"queue": "scheduled"},
        #     },
    }

    from app.core.seller_workspace_config import SellerWorkspaceConfig

    seller_config = SellerWorkspaceConfig.from_environment()
    if seller_config.enabled and seller_config.aws_profile_enabled:
        app.conf.beat_schedule["seller-workspace-profile-heartbeat"] = {
            "task": "seller_workspace_profile.heartbeat",
            "schedule": 30.0,
            "options": {"queue": "seller_workspace_profile_control", "expires": 30},
        }

    if settings.GMAIL_POLLING_ENABLED:
        app.conf.beat_schedule["gmail-polling"] = {
            "task": "app.tasks.scheduled.poll_gmail_inbox",
            "schedule": 60.0,
            "options": {"queue": "scheduled"},
        }

    if settings.EVENT_ARCHIVAL_ENABLED:
        # BQ-124 Phase D3: archive old state events after reconciliation.
        app.conf.beat_schedule["event-archival-nightly"] = {
            "task": "app.tasks.scheduled.run_event_archival",
            "schedule": crontab(hour=4, minute=30),
            "options": {"queue": "scheduled"},
        }
    
    return app


# Global Celery app instance
celery_app = create_celery_app()


# =============================================================================
# TASK BASE CLASS (for async support)
# =============================================================================

class AsyncTask(celery_app.Task):
    """
    Base task class that provides async database session support.
    
    Usage:
        @celery_app.task(base=AsyncTask, bind=True)
        def my_task(self):
            async with self.get_db() as db:
                # Use db session
                pass
    """
    
    _db_session = None
    
    async def get_db(self):
        """Get async database session."""
        from app.core.database import AsyncSessionLocal
        return AsyncSessionLocal()


# Export for use in task modules
__all__ = ["celery_app", "AsyncTask"]
