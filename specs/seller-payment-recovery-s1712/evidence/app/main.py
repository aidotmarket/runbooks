"""ai.market API - Main Application

Phase 3.H.3: Background task scheduling now supports two modes:
- APScheduler (in-process): For single-instance deployments
- Celery (distributed): For multi-instance deployments

Set SCHEDULER_MODE=celery to disable in-process scheduler
when running Celery workers separately.
"""

import sys
import os
import asyncio
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, PlainTextResponse
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.core.config import settings
from app.core.log_redaction import RedactingFormatter, redact_handler
from app.api.v1.router import api_router
from app.api.v2.router import api_router as api_v2_router
from app.api.v1.state_events_errors import (
    StateEventsHTTPException,
    state_events_exception_handler,
    state_events_validation_exception_handler,
)
from app.api import webhooks
from app.api import secrets
from app.services.worker_service import worker_service
from app.services.telegram_relay import telegram_relay  # BQ-077: relay replaces monolith
from app.allai import agent_host
from app.allai.agents import AllAIBrainAgent, MatchmakerAgent, SysAdminAgent, AgentLogAgent, CRMStewardAgent, FinanceAgent, ListingEnricherAgent, ListingShareCaptionAgent, MarketingOpsAgent
from app.core.correlation import CorrelationIdMiddleware
from app.allai.trace_context import TraceContext, reset_trace, set_trace
from app.middleware.agent_auth import AgentAuthMiddleware
from app.middleware.ai_bot_logger import AIBotLoggerMiddleware
from app.middleware.gatekeeper import GatekeeperMiddleware

# Configure logging explicitly for Railway visibility
# This ensures logger.info() calls appear in container stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True  # Override any existing config
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
for handler in logging.getLogger().handlers:
    handler.setFormatter(
        RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )


def _configure_uvicorn_log_redaction() -> None:
    """Apply redaction to Uvicorn handlers while preserving their formatting."""

    try:
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            for handler in logging.getLogger(logger_name).handlers:
                redact_handler(handler)
    except Exception:
        # Logging hardening must never break application startup.
        pass


_configure_uvicorn_log_redaction()
logger = logging.getLogger(__name__)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

# T-2026-000580 (2026-08-13): historical classification for the tables
# intentionally dropped by the July 2026 S1113 CRM retirement migration.
KNOWN_RETIRED_TABLES: frozenset[str] = frozenset({
    "crm_contact_pipeline",
    "crm_conversation_states",
    "crm_email_drafts",
    "crm_entities",
    "crm_interactions",
    "crm_learned_preferences",
    "crm_organizations",
    "crm_people",
    "crm_pipeline_history",
    "crm_pipeline_stages",
    "crm_playbooks",
    "crm_referrals",
    "crm_relationships",
    "crm_tasks",
})


def _read_public_file(relative_path: str) -> str:
    return (PUBLIC_DIR / relative_path).read_text(encoding="utf-8")


# Scheduler mode: "apscheduler" (in-process) or "celery" (external worker)
# Set SCHEDULER_MODE=celery when running Celery workers separately
SCHEDULER_MODE = os.getenv("SCHEDULER_MODE", "apscheduler").lower()


async def run_migrations():
    """Run Alembic migrations on startup (async-safe).

    Phase 3.H.1: Replaced 700+ lines of inline SQL with Alembic.
    Migrations now tracked in alembic/versions/

    Uses asyncio.create_subprocess_exec to avoid blocking the event loop
    (S110 fix: subprocess.run was a synchronous blocking call).
    """
    try:
        logger.info("Starting database migrations via Alembic...")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Python executable: {sys.executable}")

        # Run alembic upgrade head as async subprocess (non-blocking)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "alembic", "upgrade", "head",
            cwd=os.getcwd(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("Database migration timed out after 60 seconds")
            raise RuntimeError("Alembic migration timed out")

        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if proc.returncode == 0:
            logger.info("Database migrations completed successfully.")
            if stdout_text:
                logger.info(f"Alembic output: {stdout_text[:500]}")
            # S97: Belt-and-suspenders — ensure columns even after migration
            try:
                from app.core.database import async_engine
                async with async_engine.begin() as conn:
                    await _ensure_missing_columns(conn)
            except Exception as e:
                logger.warning(f"Post-migration column check failed: {e}")
        else:
            logger.error(f"Alembic migration failed with code {proc.returncode}")
            if stderr_text:
                logger.error(f"Alembic stderr: {stderr_text[:1000]}")
            if stdout_text:
                logger.error(f"Alembic stdout: {stdout_text[:1000]}")
            raise RuntimeError(
                f"Alembic migration failed with code {proc.returncode}"
            )

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def _ensure_missing_columns(conn):
    """S97: Add missing columns to existing tables.
    
    Uses ALTER TABLE ADD COLUMN IF NOT EXISTS (PG 9.6+).
    Safe to run repeatedly - idempotent.
    """
    from sqlalchemy import text
    
    # Ensure enum types for MobileTask
    await conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mobile_task_type') THEN
                CREATE TYPE mobile_task_type AS ENUM (
                    'listing_create', 'listing_update', 'listing_delete',
                    'order_create', 'profile_update', 'search',
                    'notification', 'sync', 'custom'
                );
            END IF;
        END $$;
    """))
    
    await conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mobile_task_status') THEN
                CREATE TYPE mobile_task_status AS ENUM (
                    'pending', 'processing', 'completed',
                    'failed', 'rejected', 'expired'
                );
            END IF;
        END $$;
    """))
    
    missing_column_fixes = [
        # S100: Gmail Pub/Sub column (migration 20260130_019 never applied due to 4-head issue)
        ("gmail_tokens", "last_history_id", "BIGINT"),
        # Mobile Task Queue — belt-and-suspenders for mobile_tasks table
        ("mobile_tasks", "error_message", "TEXT"),
        ("mobile_tasks", "hmac_signature", "VARCHAR(256)"),
        ("mobile_tasks", "api_key_id", "VARCHAR(255)"),
        ("mobile_tasks", "processed_at", "TIMESTAMP WITH TIME ZONE"),
        ("mobile_tasks", "payload", "JSONB DEFAULT '{}'"),
        ("mobile_tasks", "id", "UUID DEFAULT uuid_generate_v4()"),
        ("mobile_tasks", "task_type", "mobile_task_type NOT NULL"),
        ("mobile_tasks", "status", "mobile_task_status NOT NULL DEFAULT 'pending'"),
        ("mobile_tasks", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT now()"),
        ("mobile_tasks", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT now()"),
    ]
    
    fixed = 0
    for table, column, col_type in missing_column_fixes:
        try:
            await conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
            ))
            fixed += 1
        except Exception as e:
            logger.warning(f"Column fix skipped ({table}.{column}): {e}")
    
    # Ensure primary key on mobile_tasks.id
    await conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conrelid = 'mobile_tasks'::regclass AND contype = 'p'
            ) THEN
                ALTER TABLE mobile_tasks ADD PRIMARY KEY (id);
            END IF;
        END $$;
    """))
    
    # Ensure indexes for mobile_tasks
    try:
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mobile_tasks_task_type ON mobile_tasks (task_type);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mobile_tasks_status ON mobile_tasks (status);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mobile_tasks_api_key_id ON mobile_tasks (api_key_id);"))
    except Exception as e:
        logger.warning(f"Index creation skipped (mobile_tasks may not exist): {e}")
    
    if fixed:
        logger.info(f"S97: Ensured {fixed} columns exist across CRM tables")


def check_migration_heads() -> None:
    """BQ-091 AC-4: Verify exactly one Alembic migration head exists.

    Uses Alembic's programmatic API (ScriptDirectory.get_heads) to count
    migration heads at startup. Raises RuntimeError if multiple heads are
    detected, preventing the application from starting with a diverged
    migration graph.

    This catches multi-head drift early — before migrations run — so
    developers fix merge conflicts before deploying.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_cfg = Config(os.path.join(os.getcwd(), "alembic.ini"))
    script_dir = ScriptDirectory.from_config(alembic_cfg)
    heads = script_dir.get_heads()

    if len(heads) == 0:
        raise RuntimeError(
            "BQ-091: No Alembic migration heads found. "
            "The alembic/versions/ directory may be empty or misconfigured."
        )
    elif len(heads) > 1:
        raise RuntimeError(
            f"BQ-091: Multiple Alembic migration heads detected ({len(heads)}): "
            f"{heads}. Run 'alembic merge heads -m \"merge\"' to consolidate "
            f"before deploying. See BQ-091 for context."
        )
    else:
        logger.info(f"Migration head check passed: single head '{heads[0]}'")


async def _safe_start(coro, name: str, timeout: int = None):
    """Start a service with a timeout. Logs error but never blocks startup."""
    if timeout is None:
        timeout = int(os.environ.get("STARTUP_TIMEOUT", "10"))
    try:
        await asyncio.wait_for(coro, timeout=timeout)
        logger.info(f"{name} started")
    except asyncio.TimeoutError:
        logger.error(f"{name} timed out after {timeout}s — skipping (app will still serve)")
    except Exception as e:
        logger.error(f"{name} start error: {e}")


async def _start_sysadmin_health_contract_scheduler(app: FastAPI) -> None:
    async def _run_sysadmin_health_contract_scheduler():
        try:
            from app.allai.agents.sysadmin.singleton import get_sysadmin_agent

            sysadmin = await get_sysadmin_agent()
            await sysadmin.run_scheduler_forever()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"SysAdmin health-contract scheduler crashed: {e}", exc_info=True)

    task = asyncio.create_task(_run_sysadmin_health_contract_scheduler())
    app.state.sysadmin_health_contract_scheduler_task = task


async def _stop_sysadmin_health_contract_scheduler(app: FastAPI) -> None:
    task = getattr(app.state, "sysadmin_health_contract_scheduler_task", None)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("SysAdmin health-contract scheduler stopped")
    except Exception as e:
        logger.error(f"SysAdmin health-contract scheduler stop error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    try:
        from app.core.seller_schema_readiness import main as check_seller_schema

        schema_result = await asyncio.to_thread(check_seller_schema)
    except Exception:
        raise RuntimeError(
            "Seller schema unavailable to application role; web not started."
        ) from None
    if schema_result != 0:
        raise RuntimeError(
            "Seller schema unavailable to application role; web not started."
        )
    _configure_uvicorn_log_redaction()
    # S110: Diagnostic — ensure lifespan entry is visible in Railway logs
    import sys as _sys
    print("[LIFESPAN] Entering startup sequence", flush=True, file=_sys.stderr)
    print("[LIFESPAN] Entering startup sequence", flush=True)
    # Startup
    # Set up GCP credentials (TD-005)
    from app.core.gcp_credentials import setup_gcp_credentials
    from app.services.kms_service import kms_service

    if setup_gcp_credentials():
        logger.info("GCP credentials configured successfully")
    else:
        logger.warning("GCP credentials not configured - KMS features may fail")

    kms_ready = await kms_service.initialize(force=True)
    app.state.kms_readiness = kms_service.get_status()
    if not kms_ready:
        logger.error(
            "KMS is not ready; KMS-dependent operations will fail closed"
        )
    logger.info("=== LIFESPAN START ===")
    logger.info(f"Scheduler mode: {SCHEDULER_MODE}")

    # BQ-OBS Phase 1: OpenTelemetry instrumentation (moved from module level)
    # Inside lifespan so it never runs during alembic migrations, tests, or CLI scripts.
    from app.core.observability import init_telemetry
    from app.core.database import async_engine as _otel_engine
    init_telemetry(app, engine=_otel_engine)

    # Anonymous allAI readiness is isolated: a failed binding disables only the
    # signed-out surface and never prevents unrelated services from starting.
    try:
        from app.core.anonymous_chat_metrics import init_anonymous_chat_metrics
        from app.services.anonymous_chat_enforcement import (
            verify_anonymous_chat_bindings,
        )

        init_anonymous_chat_metrics()
        app.state.anonymous_chat_readiness = await verify_anonymous_chat_bindings()
    except Exception as exc:
        from app.services.anonymous_chat_enforcement import (
            AnonymousChatReadiness,
            set_anonymous_chat_readiness,
        )

        readiness = AnonymousChatReadiness("not_ready", "startup_verification_error")
        set_anonymous_chat_readiness(readiness)
        app.state.anonymous_chat_readiness = readiness
        logger.error("Anonymous chat binding verification failed: %s", exc)

    # BQ-091 AC-4: Fail fast if migration graph has diverged heads
    logger.info("Checking Alembic migration heads...")
    # S110: check_migration_heads does sync file I/O — offload to thread
    await asyncio.to_thread(check_migration_heads)

    logger.info("Running database migrations...")

    # Migration failure is a startup failure. Keep this outside the tolerant
    # seed/bootstrap boundary so lifespan cannot reach READY on schema drift.
    await run_migrations()

    try:
        # Seed permissions
        from app.actions.seed_templates import seed_permission_templates
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            logger.info("Seeding permission templates...")
            await seed_permission_templates(db)
            
            # Bootstrap platform manifest (TD-007 - S50)
            from app.core.bootstrap import bootstrap_platform_manifest, seed_global_policies
            logger.info("Bootstrapping ai.market platform manifest...")
            await bootstrap_platform_manifest(db)
            
            # Seed global policies (S51 - Content Validation)
            logger.info("Seeding global policies...")
            await seed_global_policies(db)

            # BQ-122: Seed agent + agent_version records from agent_registry
            # Idempotent — skips agents that already exist in the DB.
            from app.seeds.seed_agents import seed_agents
            logger.info("Seeding agent registry...")
            agent_count = await seed_agents(db)
            if agent_count:
                logger.info("Seeded %d new agents into agent table", agent_count)

            from app.models.observability import ActionPolicy
            policy = (
                await db.execute(
                    select(ActionPolicy).where(ActionPolicy.action_type == "run_backup")
                )
            ).scalars().first()
            if policy is None:
                db.add(ActionPolicy(
                    id=uuid.uuid4(),
                    action_type="run_backup",
                    description="Phase 1 alert triage remediation for backup recovery",
                    requires_approval=False,
                    max_frequency_per_hour=3,
                    cooldown_seconds=300,
                    retry_limit=2,
                    confidence_threshold=0.7,
                    enabled=True,
                ))
                await db.commit()
                logger.info("Seeded ActionPolicy for run_backup")

            warmup_policy = (
                await db.execute(
                    select(ActionPolicy).where(ActionPolicy.action_type == "cold_start_warmup")
                )
            ).scalars().first()
            if warmup_policy is None:
                db.add(ActionPolicy(
                    id=uuid.uuid4(),
                    action_type="cold_start_warmup",
                    description="Warm a health endpoint to detect Railway cold starts",
                    requires_approval=False,
                    max_frequency_per_hour=6,
                    cooldown_seconds=120,
                    retry_limit=2,
                    confidence_threshold=0.7,
                    enabled=True,
                ))
                await db.commit()
                logger.info("Seeded ActionPolicy for cold_start_warmup")

    except Exception as e:
        logger.error(f"Startup error: {e}")
    
    # S110: Optional service skip for healthcheck debugging
    # Set SKIP_SERVICES=1 in Railway env to bypass all non-essential services
    skip_services = os.environ.get("SKIP_SERVICES", "0") == "1"
    if skip_services:
        logger.warning("SKIP_SERVICES=1 — skipping scheduler, worker, telegram, agents")
    
    # Start background scheduler (Phase 3.C.4 / Phase 3.H.3)
    # Only start in-process scheduler if not using Celery
    scheduler_started = False
    if not skip_services and SCHEDULER_MODE == "apscheduler":
        from app.core.scheduler import start_scheduler, stop_scheduler
        await _safe_start(start_scheduler(), "Scheduler (APScheduler)")
        # Check if it actually started (start_scheduler sets global)
        from app.core.scheduler import scheduler as _sched
        if _sched and _sched.running:
            try:
                from app.jobs.aim_settlement_jobs import register_aim_settlement_jobs

                register_aim_settlement_jobs(_sched)
                logger.info("Registered AIM settlement APScheduler jobs")
            except Exception as e:
                logger.error(f"AIM settlement job registration error: {e}")
            scheduler_started = True
    elif not skip_services:
        logger.info("In-process scheduler disabled (SCHEDULER_MODE=celery)")
        logger.info("Ensure Celery worker and beat are running separately")
    
    if not skip_services:
        # Register HITL regeneration callbacks (S59 - Agent Framework)
        try:
            from app.services.hitl_callbacks import register_hitl_callbacks
            register_hitl_callbacks()
            logger.info("HITL regeneration callbacks registered")
        except Exception as e:
            logger.error(f"HITL callback registration error: {e}")

        # Register agents (sync — just appends to a list)
        # AllAIBrainAgent registered first — Tier 0 boots before all others
        try:
            agent_host.register(AllAIBrainAgent)
            agent_host.register(MatchmakerAgent)
            agent_host.register(SysAdminAgent)
            agent_host.register(AgentLogAgent)
            agent_host.register(CRMStewardAgent)
            agent_host.register(FinanceAgent)
            agent_host.register(ListingEnricherAgent)  # BQ-B1A: Metadata enrichment
            agent_host.register(MarketingOpsAgent)  # BQ-MARKETING-QUEUE Phase 3A
        except Exception as e:
            logger.error(f"Agent Host registration error: {e}")

        # Register agent skills into AGENTS dict (before DB sync and gateway start)
        try:
            from app.core.agent_registry import AGENTS
            from app.services.crm_steward_skills import CRM_SKILLS
            AGENTS["crm-steward"]["skills"] = CRM_SKILLS
            logger.info("Registered %d CRM Steward skills", len(CRM_SKILLS))
        except Exception as e:
            logger.error(f"Skill registration error: {e}")

        # BQ-ALLAI-BRAIN Phase A: Populate action contract registry
        try:
            from app.allai.action_contracts import populate_default_contracts
            populate_default_contracts()
        except Exception as e:
            logger.error(f"Action contract registration error: {e}")

        # BQ-AGENT-FRAMEWORK Build 5: Sync registry with DB
        try:
            from app.core.agent_registry import sync_registry_with_db
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await sync_registry_with_db(db)
        except Exception as e:
            logger.error(f"Registry DB sync error: {e}")

        # S110 fix: Start all services concurrently so one slow service
        # doesn't delay the others.  Each _safe_start has its own timeout.
        await asyncio.gather(
            _safe_start(worker_service.start(), "Worker Service"),
            _safe_start(telegram_relay.start(), "TelegramRelay"),
            _safe_start(agent_host.start(), "Agent Host"),
        )
        app.state.agent_registry = agent_host.registry

        try:
            from app.allai.incident_sweeper import incident_sweeper

            await incident_sweeper.start()
            app.state.incident_sweeper = incident_sweeper
            logger.info("Incident sweeper started")
        except Exception as e:
            logger.error(f"Incident sweeper start error: {e}")

        # BQ-AGENT-TEMPLATE Phase 3: Register agents for auto-mount
        try:
            from app.allai.agent_router_registry import register_agent, mount_agent_routers
            # NOTE: Agent classes are already imported at module scope.
            # Do not re-import them here: Python would treat them as local
            # names for this function and shadow the earlier references used
            # by the registration block above.

            for agent_cls in [
                SysAdminAgent, AgentLogAgent, MarketingOpsAgent,
                MatchmakerAgent, ListingEnricherAgent, AllAIBrainAgent,
                CRMStewardAgent, ListingShareCaptionAgent,
            ]:
                register_agent(agent_cls)

            mounted = mount_agent_routers(app)
            logger.info(f"Agent auto-mount: {mounted} routers mounted")
        except Exception as e:
            logger.error(f"Agent auto-mount error: {e}")

        # BQ-124: Start Qdrant sync outbox worker
        try:
            from app.services.qdrant_sync_worker import start_qdrant_sync_worker
            await start_qdrant_sync_worker()
            logger.info("Qdrant sync outbox worker started")
        except Exception as e:
            logger.error(f"Qdrant sync worker start error: {e}")

    # BQ-E2: Marketplace MCP Server — start session manager
    if _marketplace_mcp_available:
        try:
            from app.mcp.marketplace_remote import mcp_server as _mktplace_mcp
            _marketplace_mcp_cm = _mktplace_mcp.session_manager.run()
            await _marketplace_mcp_cm.__aenter__()
            logger.info("Marketplace MCP server session manager started")
        except Exception as e:
            _marketplace_mcp_cm = None
            logger.error(f"Marketplace MCP session manager start error: {e}")
    else:
        _marketplace_mcp_cm = None

    # AIM Discovery MCP Server — start session manager
    if _aim_discovery_mcp_available:
        try:
            from app.mcp.aim_discovery import mcp_server as _aim_discovery_mcp
            _aim_discovery_mcp_cm = _aim_discovery_mcp.session_manager.run()
            await _aim_discovery_mcp_cm.__aenter__()
            logger.info("AIM Discovery MCP server session manager started")
        except Exception as e:
            _aim_discovery_mcp_cm = None
            logger.error(f"AIM Discovery MCP session manager start error: {e}")
    else:
        _aim_discovery_mcp_cm = None

    # Establish Gmail watch on startup so the email-to-CRM pipeline
    # survives deploys without waiting for the daily 9 AM UTC cron.
    if not skip_services:
        await _safe_start(
            _start_sysadmin_health_contract_scheduler(app),
            "SysAdmin health-contract scheduler",
            timeout=1,
        )

        async def _gmail_watch_startup():
            try:
                from app.core.scheduler import renew_gmail_watches_job
                await renew_gmail_watches_job()
                logger.info("Gmail watch established on startup")
            except Exception as e:
                logger.warning(f"Gmail watch startup hook failed (will retry at next cron): {e}")

        asyncio.create_task(_gmail_watch_startup())

    logger.info("=== LIFESPAN READY ===")
    oauth_cleanup = None
    if settings.AIM_DATA_OAUTH_ENABLED:
        from app.services.aim_data_oauth_service import cleanup_loop
        oauth_cleanup = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        if oauth_cleanup is not None:
            oauth_cleanup.cancel()
            try:
                await oauth_cleanup
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("AIM Data OAuth cleanup task failed")
    
    # Shutdown
    logger.info("=== LIFESPAN SHUTDOWN ===")

    await _stop_sysadmin_health_contract_scheduler(app)

    try:
        from app.services.trust_channel_service import drain_all_trust_connections
        from app.services.trust_event_bus import trust_event_bus

        await drain_all_trust_connections(
            {
                "type": "drain",
                "reason": "server_shutdown",
                "grace_seconds": 10,
                "reconnect_policy": {
                    "full_handshake_required": True,
                    "backoff_seconds": [1, 2, 4, 8, 16, 30],
                    "jitter_percent": 25,
                },
            },
            grace_seconds=10.0,
        )
        await trust_event_bus.stop()
    except Exception as e:
        logger.error(f"Trust channel drain error: {e}")

    # Stop Marketplace MCP session manager (BQ-E2)
    if _marketplace_mcp_cm is not None:
        try:
            await _marketplace_mcp_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Marketplace MCP session manager stop error: {e}")

    # Stop AIM Discovery MCP session manager
    if _aim_discovery_mcp_cm is not None:
        try:
            await _aim_discovery_mcp_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"AIM Discovery MCP session manager stop error: {e}")

    if not skip_services:
        # Stop Telegram Relay (BQ-077)
        try:
            await telegram_relay.stop()
        except Exception as e:
            logger.error(f"TelegramRelay stop error: {e}")
        
        # Stop Agent Host (Phase 5 - AI Operations)
        try:
            await agent_host.stop()
        except Exception as e:
            logger.error(f"Agent Host stop error: {e}")

        try:
            await worker_service.stop()
        except Exception as e:
            logger.error(f"Worker Service stop error: {e}")

        try:
            sweeper = getattr(app.state, "incident_sweeper", None)
            if sweeper is not None:
                await sweeper.stop()
        except Exception as e:
            logger.error(f"Incident sweeper stop error: {e}")

        # BQ-124: Stop Qdrant sync outbox worker
        try:
            from app.services.qdrant_sync_worker import stop_qdrant_sync_worker
            await stop_qdrant_sync_worker()
        except Exception as e:
            logger.error(f"Qdrant sync worker stop error: {e}")

    # Stop scheduler only if it was started
    if scheduler_started:
        try:
            from app.core.scheduler import stop_scheduler
            stop_scheduler()
        except Exception as e:
            logger.error(f"Scheduler stop error: {e}")

    try:
        await kms_service.aclose()
    except Exception as e:
        logger.error(f"KMS client shutdown error: {e}")
    finally:
        from app.core.gcp_credentials import cleanup_credentials

        cleanup_credentials()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Data Marketplace API - SEO for AI",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "CRM Support",
            "description": (
                "Read-only CRM support surface. There is no public REST dispute-write "
                "successor; see /docs/workflows/crm-support."
            ),
        }
    ],
    lifespan=lifespan
)


@app.middleware("http")
async def trace_context_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID")
    token = set_trace(TraceContext(correlation_id=correlation_id) if correlation_id else TraceContext())
    try:
        return await call_next(request)
    finally:
        reset_trace(token)

# Correlation ID middleware (S57 - Distributed Tracing)
app.add_middleware(CorrelationIdMiddleware)

# Gatekeeper middleware for download links
app.add_middleware(GatekeeperMiddleware)

# AI crawler analytics logging for known AI bot traffic only.
app.add_middleware(AIBotLoggerMiddleware)

# Agent API key auth for protected routes. Add this after Gatekeeper and before
# CORS so the effective request order is CORS -> AgentAuth -> Gatekeeper.
app.add_middleware(
    AgentAuthMiddleware,
    protected_path_prefixes=(f"{settings.API_V1_PREFIX}/agent",),
    public_path_prefixes=(
        "/.well-known/llms.txt",
        "/.well-known/webmcp.json",
        "/llms.txt",
        "/llms-full.txt",
        "/requests.txt",
        "/.well-known/requests.txt",
        "/health",
        "/api/health",
        "/docs",
        "/openapi.json",
        f"{settings.API_V1_PREFIX}/agent/openapi.json",
        f"{settings.API_V1_PREFIX}/agent/llms.txt",
        f"{settings.API_V1_PREFIX}/agent/sse",
        f"{settings.API_V1_PREFIX}/agent/tools/call",
    ),
)

# CORS middleware — static origins from config + CORS_ORIGINS_EXTRA env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_v2_router, prefix="/api/v2")

# AIM metering reservations
from app.routers import aim_metering
app.include_router(aim_metering.router, prefix=settings.API_V1_PREFIX)

# MCP error envelope handler (MP-M3): canonical {"error": {...}} for all MCP auth failures
from app.api.v1.mcp_deps import MCPHTTPException, mcp_exception_handler
app.add_exception_handler(MCPHTTPException, mcp_exception_handler)
app.add_exception_handler(StateEventsHTTPException, state_events_exception_handler)


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    state_events_response = await state_events_validation_exception_handler(request, exc)
    if state_events_response is not None:
        return state_events_response
    return await request_validation_exception_handler(request, exc)


app.add_exception_handler(RequestValidationError, _validation_exception_handler)

# Webhooks (Phase 6.A - allAI Communications)
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# Secrets Vault (Phase 6.A - Encrypted Key Management)
app.include_router(secrets.router, tags=["Secrets Vault"])

# PII Router
from app.routers import pii
app.include_router(pii.router)

# LLM Configuration Router (BQ-066 — LLM Gateway)
from app.routers import llm as llm_router_module
app.include_router(llm_router_module.router)

# Chat Router (BQ-066 — LLM Gateway: RAG completions, streaming, templates)
from app.routers import chat as chat_router_module
app.include_router(chat_router_module.router)

# Co-Pilot Brain (AC3)
from app.routers import copilot
app.include_router(copilot.router)

# Co-Pilot WebSocket Bridge (BQ-082)
from app.routers import copilot_ws
app.include_router(copilot_ws.router)

# S764: legacy top-level Trust Channel alias for AIM Data clients (/ws/trust-channel)
from app.api.v1.endpoints import trust_websocket as _trust_ws_alias
app.include_router(_trust_ws_alias.ws_alias_router)

# AI Discovery (TD-009 - Dynamic llms.txt)
from app.api.v1.endpoints.llms_txt import router as llms_router
from app.api.v1.endpoints.featured import public_router as featured_public_router
from app.api.v1.endpoints.agent_manifests import router as agent_manifests_router
from app.api.v1.endpoints.sitemap import router as sitemap_router
app.include_router(llms_router, tags=["AI Discovery"])
app.include_router(featured_public_router, tags=["Featured Listings"])
app.include_router(agent_manifests_router, tags=["Agent Manifests"])
app.include_router(sitemap_router, tags=["Sitemaps"])


@app.get("/.well-known/llms.txt", include_in_schema=False)
async def well_known_llms_txt():
    """Redirect to the dynamic /llms.txt endpoint."""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/llms.txt", status_code=301)


@app.get("/.well-known/webmcp.json", include_in_schema=False)
def well_known_webmcp():
    """Serve the public WebMCP manifest used by the agent transport."""
    from app.routers.mcp_sse import get_public_webmcp_manifest

    return JSONResponse(content=get_public_webmcp_manifest())


# Robots.txt — AI crawler discovery (BQ-AGENT-DISCOVERY)
@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots_txt():
    """Serve robots.txt with AI crawler allow-rules."""
    return """# ai.market - B2B Data Marketplace
# https://ai.market

User-agent: *
Allow: /
Disallow: /api/v1/crm/
Disallow: /api/v1/allai/
Disallow: /api/v1/internal/
Disallow: /mcp/

# AI Crawlers — welcome
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Googlebot
Allow: /

User-agent: CCBot
Allow: /

User-agent: cohere-ai
Allow: /

User-agent: Meta-ExternalAgent
Allow: /

# Discovery endpoints
# /llms.txt - Compact dataset catalog for AI agents
# /llms-full.txt - Detailed dataset catalog
# /.well-known/ai-plugin.json - OpenAI plugin manifest
# /.well-known/ai-agents.json - Agent discovery
# /api/v1/agent/openapi.json - Agent API spec

Sitemap: https://api.ai.market/sitemap.xml
"""

# Demand-Side Discovery (BQ-E4 - Dynamic requests.txt)
from app.api.v1.endpoints.requests_txt import router as requests_txt_router
app.include_router(requests_txt_router, tags=["AI Discovery"])

# allAI Support Chat (S101 — Support Agent Integration)
from app.routers import support_chat
app.include_router(support_chat.router)

# allAI Anonymous Chat (BQ-ALLAI-PANEL — Marketplace Panel)
from app.routers import anonymous_chat
app.include_router(anonymous_chat.router)

# Internal-auth-only anonymous surface control plane.
from app.api.v1.endpoints import anonymous_chat_ops
app.include_router(anonymous_chat_ops.router)

# VZ Publish (BQ-VZ-PUBLISH — Ed25519 trust token)
from app.routers import vz_publish
app.include_router(vz_publish.router)

# BQ-FINANCIAL-SYSTEM Phase 1
from app.routers import finance as finance_router_module
app.include_router(finance_router_module.router)

# BQ-FINANCIAL-SYSTEM Phase 2 — Agent + Billing
from app.routers import finance_agent as finance_agent_router_module
app.include_router(finance_agent_router_module.router)

# BQ-E2: Marketplace MCP Server — Streamable HTTP for AI agent marketplace access
# Endpoint: POST /mcp/marketplace/mcp  (mount path + SDK internal /mcp)
_marketplace_mcp_mount_error = None
_marketplace_mcp_available = False
if settings.MARKETPLACE_MCP_ENABLED:
    try:
        from app.mcp.marketplace_remote import mcp_server as _mktplace_mcp_mount
        from app.mcp.marketplace_auth import marketplace_mcp_auth_app
        app.mount("/mcp/marketplace/", marketplace_mcp_auth_app(_mktplace_mcp_mount))
        _marketplace_mcp_available = True
        logger.info("Marketplace MCP Server mounted at /mcp/marketplace/")
    except Exception as _e:
        _marketplace_mcp_mount_error = str(_e)
        logger.error(f"Marketplace MCP mount failed (app will continue without it): {_e}")
else:
    logger.info("Marketplace MCP Server disabled (MARKETPLACE_MCP_ENABLED=false)")

# AIM Discovery MCP Server — Streamable HTTP for agent discovery tools
# Endpoint: POST /mcp/aim-discovery/mcp  (mount path + SDK internal /mcp)
_aim_discovery_mcp_mount_error = None
try:
    from app.mcp.aim_discovery import mcp_server as _aim_discovery_mcp_mount
    app.mount("/mcp/aim-discovery/", _aim_discovery_mcp_mount.streamable_http_app())
    _aim_discovery_mcp_available = True
    logger.info("AIM Discovery MCP Server mounted at /mcp/aim-discovery/")
except Exception as _e:
    _aim_discovery_mcp_available = False
    _aim_discovery_mcp_mount_error = str(_e)
    logger.error(f"AIM Discovery MCP mount failed (app will continue without it): {_e}")


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "scheduler_mode": SCHEDULER_MODE,
        "deploy_marker": "S141-pydantic-upgrade",
        "docs": "/docs"
    }


def get_alembic_health() -> dict[str, Any]:
    """Return Alembic revision state for health monitoring."""
    try:
        alembic_config = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_config)
        alembic_head = script.get_current_head()

        from app.core.database import engine

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            alembic_current = context.get_current_revision()

        return {
            "alembic_head": alembic_head,
            "alembic_current": alembic_current,
            "alembic_drift": alembic_head != alembic_current,
        }
    except Exception as exc:
        logger.warning(f"Failed to inspect Alembic health state: {exc}")
        return {
            "alembic_head": None,
            "alembic_current": None,
            "alembic_drift": None,
        }


def get_model_schema_health() -> dict[str, Any]:
    """Compare model tables with their schema-qualified database identities."""
    try:
        from sqlalchemy import text

        from app.core.database import Base, engine
        from app.models.registry import load_model_registry

        load_model_registry()

        model_tables = {
            f"{table.schema or 'public'}.{table.name}"
            for table in Base.metadata.tables.values()
        }
        model_schemas = sorted(
            {table_name.split(".", 1)[0] for table_name in model_tables}
        )
        with engine.connect() as connection:
            database_tables = {
                f"{schema}.{table}"
                for schema, table in connection.execute(
                    text(
                        "SELECT n.nspname, c.relname "
                        "FROM pg_catalog.pg_class AS c "
                        "JOIN pg_catalog.pg_namespace AS n "
                        "ON n.oid = c.relnamespace "
                        "WHERE n.nspname = ANY(:model_schemas) "
                        "AND c.relkind IN ('r', 'p')"
                    ),
                    {"model_schemas": model_schemas},
                ).all()
            }

        known_retired_tables = {
            f"public.{table_name}" for table_name in KNOWN_RETIRED_TABLES
        }
        schema_missing_tables = sorted(
            model_tables - database_tables - known_retired_tables
        )
        schema_unmapped_tables = sorted(
            table_name
            for table_name in database_tables - model_tables
            if table_name != "public.alembic_version"
            and not table_name.startswith("public.quarantine_")
        )
        if schema_missing_tables:
            logger.warning(
                "Schema health missing model tables: %s", schema_missing_tables
            )
        if schema_unmapped_tables:
            logger.warning(
                "Schema health unmapped database tables: %s", schema_unmapped_tables
            )
        return {
            "schema_model_tables": len(model_tables),
            "schema_missing_table_count": len(schema_missing_tables),
            "schema_unmapped_table_count": len(schema_unmapped_tables),
            "schema_known_retired_count": len(
                model_tables & known_retired_tables
            ),
            "schema_drift": bool(schema_missing_tables),
            "model_schema_drift": bool(schema_missing_tables),
        }
    except Exception as exc:
        logger.warning(f"Failed to inspect schema health: {exc}")
        return {
            "schema_model_tables": None,
            "schema_missing_table_count": None,
            "schema_unmapped_table_count": None,
            "schema_known_retired_count": None,
            "schema_drift": None,
            "model_schema_drift": None,
        }


@app.get("/health")
def health_check():
    """Root health check"""
    alembic_health = get_alembic_health()
    schema_health = get_model_schema_health()
    status = (
        "degraded"
        if alembic_health["alembic_drift"] is True
        or schema_health["schema_drift"] is True
        else "healthy"
    )
    return {
        "status": status,
        "scheduler_mode": SCHEDULER_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **alembic_health,
        **schema_health,
    }


@app.get("/api/health")
def api_health_check():
    """API health check - for frontend connection testing"""
    return {"status": "healthy", "timestamp": __import__('datetime').datetime.utcnow().isoformat()}


@app.get("/health/anonymous-chat")
async def anonymous_chat_health_check():
    """Secret-free binding health, separate from intentional enablement state."""
    from app.core.redis_cache import get_cache_client
    from app.services.anonymous_chat_enforcement import (
        anonymous_chat_runtime_recovery_needed,
        get_anonymous_chat_readiness,
        get_kill_switch,
        verify_anonymous_chat_bindings,
    )

    readiness = get_anonymous_chat_readiness()
    if anonymous_chat_runtime_recovery_needed():
        readiness = await verify_anonymous_chat_bindings()
    disabled = True
    if readiness.ready:
        kill = await get_kill_switch(await get_cache_client())
        if not kill.allowed:
            readiness = get_anonymous_chat_readiness()
            readiness_reason = readiness.reason
            binding_status = readiness.binding_status
        else:
            disabled = kill.reason == "disabled"
            readiness_reason = readiness.reason
            binding_status = readiness.binding_status
    else:
        readiness_reason = readiness.reason
        binding_status = readiness.binding_status
    return {
        "binding_status": binding_status,
        "reason": readiness_reason,
        "enabled": bool(settings.ANON_CHAT_ENABLED and not disabled),
        "kill_switch_disabled": disabled,
        "script_version": readiness.script_version,
    }


@app.get("/health/gcp")
def gcp_health_check():
    """GCP credentials health check (TD-005)"""
    from app.core.gcp_credentials import get_credentials_status
    return get_credentials_status()


@app.get("/health/qdrant")
async def qdrant_health_check():
    """Qdrant vector database health check (TD-013)"""
    from app.core.qdrant_client import qdrant_manager
    return await qdrant_manager.health_check()


@app.get("/api/v1/internal/service-bus/health")
async def service_bus_health_check():
    """Service bus registry health."""
    registry = getattr(app.state, "agent_registry", None)
    if registry is None:
        return {"status": "unavailable", "reason": "registry_not_initialized"}
    return registry.health()


@app.get("/health/mcp-marketplace")
def mcp_marketplace_health():
    """Marketplace MCP Server health check (BQ-E2)."""
    enabled = settings.MARKETPLACE_MCP_ENABLED
    status = "mounted" if _marketplace_mcp_available else ("disabled" if not enabled else "unavailable")
    resp = {
        "status": status,
        "endpoint": "/mcp/marketplace/mcp",
        "auth": "mcp_api_key",
        "enabled": enabled,
    }
    if not _marketplace_mcp_available and _marketplace_mcp_mount_error:
        resp["error"] = _marketplace_mcp_mount_error
    return resp


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["paths"]["/api/v1/state/events"]["post"]["responses"].pop("422", None)
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
