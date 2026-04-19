# Celery Infrastructure Deployment

## What it does

Production Celery for `ai-market-backend` runs as a three-service Railway topology from one shared Docker image:

- Web service: FastAPI via `uvicorn`, with HTTP healthcheck on `/health`
- Worker service: Celery worker consuming `default`, `scheduled`, `emails`, and `vectoraiz`
- Beat service: singleton Celery Beat scheduler publishing due tasks to Redis

This runbook covers the live production deployment shipped by BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT Gate 3 Chunks A-D on `aidotmarket/ai-market-backend` `origin/main`:

- `464398c` — Railway worker/beat config
- `f1e9665` — transport config + atomic cleanup path
- `b539d8f` — worker heartbeat + internal freshness probe
- `e908c44` — Gmail polling retirement flagging

Scope reference:

- Gate 2 implementation spec: `specs/BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT-GATE2.md` at `bf8ae43`, especially `§10` and `§11`
- Gate 1 retro-verification plan: `specs/BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT-GATE1.md` at `47b688c7`, especially `§11`

## Architecture

All three services build from the same backend image. Railway differentiates process role by `deploy.startCommand`, not by separate images.

```text
Git push to aidotmarket/ai-market-backend main
  -> Railway builds one backend image from Dockerfile
  -> Web service starts FastAPI via Dockerfile CMD
  -> Worker service overrides startCommand:
       celery -A app.core.celery_app worker --loglevel=info --concurrency=2 -Q default,scheduled,emails,vectoraiz
  -> Beat service overrides startCommand:
       celery -A app.core.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```

Runtime dependencies:

- Redis is the Celery broker and result backend.
- Postgres is required by the worker because task bodies access application state.
- Beat is scheduler-only. It reads schedule configuration from code and publishes due tasks to Redis. It does not execute task bodies and should not hold database or Gmail credentials.
- The web service remains the only process with an HTTP healthcheck. Worker and beat are non-HTTP processes and rely on process restart policy plus runtime probes.

## Service Inventory

| Item | Name | ID / Value | Notes |
|------|------|------------|-------|
| Railway project | `ai-market` | `e81dd66f-808c-412e-b32c-f6d910f0ac5d` | Production project |
| Railway environment | `production` | `23e322c3-b195-45d8-9151-c4c27a998c33` | Canonical prod environment |
| Worker service | `ai-market-celery-worker` | `b04bf73a-aa49-4bdb-9e8d-f8f2715ce9b1` | Consumes all four queues |
| Beat service | `ai-market-celery-beat` | `6f7319f0-2fc1-4e51-9955-6a8bd644e363` | Must remain singleton |
| Backend web service | `ai-market-backend` | Railway console source of shared app secrets | Web remains owner of `/health` |

## Runtime Topology

| Service | Process | Build source | Start mode | Health posture |
|---------|---------|--------------|------------|----------------|
| Web | `uvicorn app.main:app` | `Dockerfile` | Dockerfile `CMD` | `/health` HTTP check |
| Worker | `celery worker` | Same `Dockerfile` image | `railway.worker.json` `deploy.startCommand` | No HTTP check; inspect logs + heartbeat |
| Beat | `celery beat` | Same `Dockerfile` image | `railway.beat.json` `deploy.startCommand` | No HTTP check; inspect logs + due-task emission |

Key production commands:

- Worker: `celery -A app.core.celery_app worker --loglevel=info --concurrency=2 -Q default,scheduled,emails,vectoraiz`
- Beat: `celery -A app.core.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule`

Operational invariants:

- Worker queue list must stay `default,scheduled,emails,vectoraiz`.
- Beat `numReplicas` must stay `1`. More than one beat instance duplicates schedule emission.
- `CELERY_VISIBILITY_TIMEOUT` is pinned to `900` seconds in production for worker and beat.

## Environment Wiring

The worker and beat services are intentionally not configured identically. Beat is least-privilege by design.

| Variable | Source | Why it exists on worker |
|----------|--------|-------------------------|
| `REDIS_URL` | Redis service reference | Broker + result backend |
| `DATABASE_URL` | Postgres service reference | Task bodies touch DB state |
| `INTERNAL_API_KEY` | `${{ai-market-backend.INTERNAL_API_KEY}}` | Shared internal auth/config usage |
| `GMAIL_REFRESH_TOKEN` | `${{ai-market-backend.GMAIL_REFRESH_TOKEN}}` | Gmail task execution still lives on worker during soak |
| `GMAIL_SENDER_ADDRESS` | `${{ai-market-backend.GMAIL_SENDER_ADDRESS}}` | Gmail service runtime |
| `GMAIL_TOPIC_NAME` | `${{ai-market-backend.GMAIL_TOPIC_NAME}}` | Gmail watch/push config parity |
| `GOOGLE_OAUTH_CLIENT_ID` | `${{ai-market-backend.GOOGLE_OAUTH_CLIENT_ID}}` | Gmail OAuth runtime |
| `GOOGLE_OAUTH_CLIENT_SECRET` | `${{ai-market-backend.GOOGLE_OAUTH_CLIENT_SECRET}}` | Gmail OAuth runtime |
| `GOOGLE_OAUTH_CREDENTIALS_JSON` | `${{ai-market-backend.GOOGLE_OAUTH_CREDENTIALS_JSON}}` | Gmail/Google credentials |
| `SECRET_KEY` | `${{ai-market-backend.SECRET_KEY}}` | App import-time/runtime secret |
| `DOWNLOAD_TOKEN_SECRET_KEY` | `${{ai-market-backend.DOWNLOAD_TOKEN_SECRET_KEY}}` | App import-time/runtime secret |
| `CELERY_VISIBILITY_TIMEOUT` | Worker-local env | Set to `900` |

Worker note: Gmail polling is disabled by default, but the worker still needs Gmail/Google secrets during the push-only soak because worker-executed code paths still import and may call Gmail-related services.

| Variable | Source | Why it exists on beat |
|----------|--------|-----------------------|
| `REDIS_URL` | Redis service reference | Broker for publishing due tasks |
| `INTERNAL_API_KEY` | `${{ai-market-backend.INTERNAL_API_KEY}}` | Shared internal config/auth requirements at import time |
| `SECRET_KEY` | `${{ai-market-backend.SECRET_KEY}}` | App import-time/runtime secret |
| `DOWNLOAD_TOKEN_SECRET_KEY` | `${{ai-market-backend.DOWNLOAD_TOKEN_SECRET_KEY}}` | App import-time/runtime secret |
| `CELERY_VISIBILITY_TIMEOUT` | Beat-local env | Set to `900` for consistent transport policy |

Beat omissions are intentional:

- No `DATABASE_URL`
- No `GMAIL_*`
- No `GOOGLE_OAUTH_*`
- No `GOOGLE_OAUTH_CREDENTIALS_JSON`

Why: per Gate 2 `§8`, beat only schedules. It never executes task bodies. Keeping database and Gmail credentials off beat reduces blast radius and prevents accidental privilege creep.

## Heartbeat Monitoring

Production liveness is proven by an end-to-end heartbeat task, not by process presence alone.

### How the heartbeat works

- Beat emits `app.tasks.scheduled.celery_runtime_heartbeat` every `60` seconds on the `scheduled` queue.
- Worker executes the task and writes Redis key `celery:heartbeat:worker:<hostname>`.
- Redis TTL is `180` seconds.
- Payload shape:

```json
{
  "timestamp_utc_iso": "2026-04-19T10:00:00.000000+00:00",
  "worker_hostname": "<railway-hostname>",
  "worker_pid": 123
}
```

- Internal probe: `check_celery_worker_heartbeat` in `app/api/v1/endpoints/health_internal.py`
- Probe threshold: stale after `120` seconds
- Probe states:
  - `ok` — freshest heartbeat at or under 120 seconds old
  - `stale` — heartbeat exists but is older than 120 seconds
  - `missing` — no usable heartbeat keys found

### How to inspect heartbeat

Use SysAdmin/Vulcan tooling first if available. Manual Redis inspection is the fallback.

Manual Redis check pattern:

```bash
unset RAILWAY_TOKEN && railway shell -s ai-market-celery-worker
python - <<'PY'
import asyncio, json
from app.core.redis_cache import get_cache_client

async def main():
    client = await get_cache_client()
    keys = []
    cursor = 0
    while True:
        cursor, batch = await client.scan(cursor=cursor, match="celery:heartbeat:worker:*", count=100)
        keys.extend(batch)
        if cursor in (0, "0", b"0"):
            break
    print([k.decode() if isinstance(k, bytes) else k for k in keys])
    for key in keys:
        raw = await client.get(key)
        print((key.decode() if isinstance(key, bytes) else key), json.loads(raw))

asyncio.run(main())
PY
```

## Scheduled Inventory

These periodic tasks matter most for Celery operational checks:

| Beat entry | Task | Queue | Schedule |
|------------|------|-------|----------|
| `celery-worker-heartbeat` | `app.tasks.scheduled.celery_runtime_heartbeat` | `scheduled` | Every 60s |
| `process-support-sla-breaches` | `app.tasks.scheduled.process_support_sla_breaches` | `scheduled` | Every 300s |
| `process-reminders-hourly` | `app.tasks.scheduled.process_reminders` | `scheduled` | Hourly, minute 5 |
| `process-auto-confirmations-hourly` | `app.tasks.scheduled.process_auto_confirmations` | `scheduled` | Hourly, minute 10 |
| `vectoraiz-optimize-index` | `vectoraiz.optimize_search_index` | `vectoraiz` | Daily, 03:00 UTC |
| `qdrant-reconciler-nightly` | `app.tasks.scheduled.run_qdrant_reconciler` | `scheduled` | Daily, 04:00 UTC |
| `kd-janitor-weekly` | `app.tasks.scheduled.run_kd_janitor` | `scheduled` | Sunday, 05:00 UTC |
| `cleanup-notifications-daily` | `app.tasks.scheduled.cleanup_notifications` | `scheduled` | Daily, 03:00 UTC |
| `cleanup-stuck-agent-transactions` | `app.tasks.scheduled.cleanup_stuck_agent_transactions` | `scheduled` | Hourly, minute 20 |
| `gmail-polling` | `app.tasks.scheduled.poll_gmail_inbox` | `scheduled` | Every 60s only when `GMAIL_POLLING_ENABLED=True` |

## On-Call Playbook

All Railway CLI commands in this environment should be prefixed with `unset RAILWAY_TOKEN &&` to avoid stale-token conflicts.

### Worker down

Condition:

- Heartbeat probe returns `missing` or `stale`
- No recent `celery.runtime.heartbeat` lines in worker logs

Detection:

```bash
unset RAILWAY_TOKEN && railway logs -s ai-market-celery-worker
```

First response:

1. Check logs for crash loop, import failure, Redis connection failure, or task-level hard failure.
2. Confirm beat is still emitting due tasks; do not assume beat is broken just because worker is down.
3. Redeploy the worker service.

```bash
unset RAILWAY_TOKEN && railway redeploy -s ai-market-celery-worker
```

4. Re-check logs for startup and fresh `celery.runtime.heartbeat`.

### Beat down

Condition:

- No `Scheduler: Sending due task` lines for more than 60 seconds during active schedule periods
- Worker remains up but heartbeat stops because beat is no longer emitting the heartbeat task

Detection:

```bash
unset RAILWAY_TOKEN && railway logs -s ai-market-celery-beat
```

First response:

1. Verify the beat process is not running or is stuck before assuming worker failure.
2. Redeploy beat. Beat is a singleton; restart-on-crash is the recovery path.

```bash
unset RAILWAY_TOKEN && railway redeploy -s ai-market-celery-beat
```

3. Confirm fresh `Scheduler: Sending due task celery-worker-heartbeat` output and a new worker heartbeat within two minutes.

### Redis down

Condition:

- Worker and beat both show broker connection failures
- Heartbeat goes missing
- Task dispatch and result writes stop together

Detection:

1. Check worker logs for Redis connection errors.
2. Check beat logs for Redis connection errors.
3. Check Redis service health in Railway and SysAdmin tooling.

First response:

1. Treat Redis as the shared dependency, not separate worker and beat incidents.
2. Verify the Redis service is healthy and reachable.
3. Wait for Redis recovery before forcing repeated redeploys.
4. After Redis is healthy, verify services reconnect automatically. `broker_connection_retry_on_startup=True` covers startup retry.

### Task failures in worker logs

Condition:

- Task-specific exceptions appear in worker logs
- Queue is healthy, but one or more task types are failing

Detection:

```bash
unset RAILWAY_TOKEN && railway logs -s ai-market-celery-worker
```

First response:

1. Identify the task name and whether failure is deterministic or transient.
2. Check whether the task has `autoretry_for` semantics and may self-recover.
3. If the failure is a bad deploy or missing secret, fix config first.
4. If the failure was transient and the task is safe to rerun, use the manual trigger procedure in this runbook.

### `process_support_sla_breaches` misfires

Condition:

- Overdue support items are not being escalated on time
- No recent `process_support_sla_breaches` completion log despite the 5-minute schedule

First response:

1. Check beat logs for `process-support-sla-breaches` dispatch every 300 seconds.
2. If beat is dispatching, check worker logs for exceptions in `app.tasks.scheduled.process_support_sla_breaches`.
3. If beat is not dispatching any scheduled tasks, treat as a beat incident.
4. If only this task is failing, fix the underlying CRM or DB issue and then manually trigger one controlled run.
5. Verify completion log: `Celery task complete: processed <n> support SLA breaches`

## Gmail Cut-Over State

Push-based Gmail ingestion is now canonical.

Canonical path:

- `GmailWatchService`
- webhook endpoint in `app/api/v1/endpoints/gmail_webhook.py`

Fallback path:

- `poll_gmail_inbox`
- gated behind `GMAIL_POLLING_ENABLED=False` by default

Operational policy:

- Default production state is push-only.
- Rollback to polling is a flag flip on worker env: set `GMAIL_POLLING_ENABLED=True`.
- After changing the flag, redeploy beat so the `gmail-polling` beat entry is reloaded from config.
- Required soak period is 7 full days of push-only operation before deleting the polling code path.

## Deploy Playbook

### Normal deploy

1. Push to `main` in `aidotmarket/ai-market-backend`.
2. Railway auto-deploys the web, worker, and beat services.
3. Verify web health:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.ai.market/health
```

4. Verify worker logs show task consumption and fresh heartbeat.
5. Verify beat logs show `Scheduler: Sending due task`.

### Hotfix rollback

Rollback is service-specific.

```bash
unset RAILWAY_TOKEN && railway redeploy -s ai-market-celery-worker -d <previous_deploy_id>
unset RAILWAY_TOKEN && railway redeploy -s ai-market-celery-beat -d <previous_deploy_id>
unset RAILWAY_TOKEN && railway redeploy -s ai-market-backend -d <previous_deploy_id>
```

### Secret rotation

Shared secrets for worker and beat are sourced from `ai-market-backend` via Railway cross-service references.

Procedure:

1. Update the secret in the `ai-market-backend` service environment.
2. Confirm the worker/beat variable references still point to `${{ai-market-backend.VAR_NAME}}`.
3. Worker and beat should resolve the updated value via the intact cross-reference.

## Manual Task Trigger Procedure

Use this when a scheduled task needs an on-demand run without waiting for the next beat window.

Preferred path:

```bash
unset RAILWAY_TOKEN && railway shell -s ai-market-celery-worker
python - <<'PY'
from app.core.celery_app import celery_app

result = celery_app.send_task("app.tasks.scheduled.process_support_sla_breaches")
print(result.id)
PY
```

Replace the task name as needed, for example:

- `app.tasks.scheduled.run_qdrant_reconciler`
- `app.tasks.scheduled.run_kd_janitor`
- `app.tasks.scheduled.cleanup_stuck_agent_transactions`

Checklist:

1. Trigger from the worker shell so imports and env match production.
2. Copy the returned Celery task ID into the incident notes.
3. Watch worker logs until success or failure: `unset RAILWAY_TOKEN && railway logs -s ai-market-celery-worker`
4. Capture the result dict or error trace.

If `railway shell` is unavailable, use another approved shell path into the worker container and run the same Python pattern there. There is no dedicated HTTP endpoint for ad hoc Celery task dispatch.

## Verification Checks

Minimal post-deploy checks:

1. `https://api.ai.market/health` returns `200`.
2. Beat logs emit `Scheduler: Sending due task celery-worker-heartbeat`.
3. Worker logs emit `celery.runtime.heartbeat`.
4. Redis heartbeat key exists with a fresh timestamp.
5. At least one ordinary scheduled task executes successfully after deploy.

Recommended deeper checks:

1. Confirm `qdrant-reconciler-nightly` and `kd-janitor-weekly` remain present in beat inventory.
2. Confirm `GMAIL_POLLING_ENABLED=False` in production unless break-glass rollback is active.
3. Confirm worker is still consuming `vectoraiz` queue after deploy.

## Built

Created for BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT Gate 3 Chunk E.
References backend implementation at `464398c`, `f1e9665`, `b539d8f`, and `e908c44`.
