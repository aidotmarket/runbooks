---
title: Celery Infrastructure Deployment
owner: unassigned
last_verified: '2026-09-08'
aliases: []
error_signatures: []
---

# Celery Infrastructure Deployment

## What it does

Production Celery for `ai-market-backend` runs as a three-service Railway topology built from the same Dockerfile. Each service has its own image digest; do not assume image-byte equality from the shared source commit:

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

### September 8 effective fleet check (S1682)

Read-only Railway inventory and SSH agree that web, worker and Beat run backend
`1c96b257c34938ea547be1eb818d5e902ff49f56`, not seller candidate
`b3f68a18a727ff8d4f8aac8ba3e397df89b88be5`. Active deployment IDs are
`2357f6b8-5771-4725-93e8-f86c8499d752` (web),
`25cf4705-d2fe-408f-bd1f-30f92f7b2b1a` (worker), and
`4d3a99e5-0b21-4920-a192-935ec965f3c5` (Beat). Each has one replica; web is in
us-west2 and worker/Beat in us-east4-eqdc4a. The three image digests differ.
The process commands match the existing commands below; web runs one Uvicorn
worker. Worker and Beat effective healthcheckPath are null; web uses /health.
No explicit pre-deploy command, overlap duration or draining duration is recorded
in these manifests. Null settings do not establish the platform's effective
defaults or a safe migration/rolling-release sequence.

Public /health reports healthy, no schema/model drift, and scheduler_mode
apscheduler. An existing Redis worker heartbeat was fresh on read. These checks
do not certify all scheduled tasks or exclude duplicate scheduling; in-process
APScheduler and Celery scheduling coexist and require release-specific analysis.
No task was dispatched and no production SQL or customer data was read.

Beat has REDIS_URL but no DATABASE_URL. This matches the scheduler-only posture
documented below. The seller candidate's railway.beat.json adds
`python -m app.core.seller_schema_readiness` before Celery; that probe requires
DATABASE_URL even with Workspace off. Running the exact reviewed local ARM image
`sha256:7b6cf73a4c706dfc4d46e3c7497dbe1fe4856238086ee396579fa43ba8d61228`
with that command, a synthetic SECRET_KEY, no DATABASE_URL and network disabled
refused startup with exit1 before Beat. The deployment is therefore NOT ready to
use the seller candidate with unchanged Beat configuration. Do not remove the
shared billing migration floor, grant production access, or change provider
configuration merely to make the probe pass. Resolve scheduler admission and
its intended database authority as a separately reviewed release change, then
prove the actual release configuration. Production settings remain unchanged.

Evidence and exact commands: seller-r2-release-next-continuation/outputs,
SELLER-EFFECTIVE-FLEET-INVENTORY.json, SELLER-RUNTIME-*.json,
SELLER-HEARTBEAT-*.json, SELLER-BEAT-REFUSAL-*.json and SELLER-PUBLIC-HEALTH.json.
The first runtime inspector checked the wrong optional author-variable name
DATABASE_URL_AUTHOR; that field is not evidence about AUTHOR_DISPATCH_DATABASE_URL.
The heartbeat inspector checks the latter name correctly on the worker only.
No production role/ACL or KMS certification is implied.

All three services build from the same backend Dockerfile. Railway differentiates process role by `deploy.startCommand`; verify each resulting image independently.

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

## When it breaks

Use the On-Call Playbook and Verification Checks above when the deployed Celery topology fails.


## S1684 seller admission design disposition

All three focused reviewers approved the revised design with nits; see the S1684
section of seller-workspace-provider-verification.md and the immutable design
SHA256 cff8d34177f4363cde87cde236409a7338409487f81e57c6276080c723ce5728.
Parent worker_init and beginning-of-lifespan application-role checks must be
implemented and proved before replacing the seller Beat probe. Beat remains
scheduler-only without database authority. Existing normal worker prefix stays.
The staged isolated command override is not a production command change. Actual
scheduled-path, refusal and exact-code review remain open; static inventory is
not full fleet or duplicate-absence certification. No deployment is authorized.


## S1685 isolated profile task loop correction

Repeated actual profile reconcile/expire_cleanup deliveries in the new isolated
prefork worker failed with `Event loop is closed`, even after correcting the
synthetic role's missing UPDATE grant. The tasks called asyncio.run for each
delivery while AsyncSessionLocal retained pooled connections bound to the prior
loop. The isolated correction reuses the existing version_notification_service
run_async helper, as seller search already does, for all three profile wrappers.
It preserves task names, queues, concurrency, feature checks and task bodies.
Verify repeated scheduled task completion in the same worker process; a first
successful task or worker readiness alone cannot establish this correction.
The actual failure logs and correction proof are in seller-scheduler-implementation-
continuation/outputs. Production and existing peer environments remain unchanged.

S1685 final disposition: CC/GLM/DeepSeek APPROVE_WITH_NITS, no HIGH/MEDIUM findings, for exact c3a28af26bc093aec11375c702d70d8cf5124067. Intrinsic worker/web refusal and actual isolated scheduled publication, retry/recovery, profile-loop reuse and broker-only Beat proof passed. PR354 integrated by exact fast-forward into held seller PR342. This supersedes the S1684 pending implementation statement above, without clearing production exclusion, schema transition, topology, ACL/KMS, R2 or enabled-release gates. All new S1685 containers stopped cleanly with artifacts retained.

## S1686 live scheduling overlap and queue coverage

Read-only September 8 verification at23:42–23:46UTC confirms the same three
production deployments at1c96b257. All24inspected source hashes match main.
Web has30persisted APScheduler job IDs:25core,1reconciliation and4settlement/
payout registrations added by lifespan. All30resolve to exact source; do not
describe the earlier25core count as the whole scheduler. Source registration
files are unchanged on held sellerc3a28af. Persistence alone is not successful
execution proof; no persisted job pickle or customer payload was deserialized.

Server-filtered logs show both periodic owners active for inquiry reminders,
order auto-confirmations and Buyer Request publication: each scheduler records
3hourly reminder/confirmation events and90publication events in the3hour window.
Web records execution starts; Beat records due emissions. This proves scheduling
overlap, not duplicate business effects or successful worker completion. Existing
idempotency is not waived. Public health remains healthy/apscheduler/no drift.

Metadata-only LLEN at23:46:17UTC reports25,402messages in translations and30,999
in seller_workspace_profile_control; the observed worker consumes neither.
The10-service production inventory has one Celery worker and no profile or
translation worker. Other external consumers are unverified. Do not purge these
queues, read customer payloads, expand worker queues or start consumers as a
health check: accumulated jobs may invoke providers/models or customer effects.
Existing ordinary queues were empty in this sample; that is not task-success
or backlog-safety proof. No queue or runtime configuration was changed.

A proposed correction removes only the three overlapping Beat registrations,
retaining their callable tasks and all web jobs. It is NOT reviewed/implemented.
Keep SCHEDULER_MODE unchanged; a blanket switch would omit other web-only work,
including settlement/payout. Require narrow design review, persisted Beat-entry
restart proof, complete isolated registration coverage and exact-code review.
Production old-producer/in-flight exclusion remains separately authorized.
Evidence and proposal: seller-r2-release-after-scheduler/outputs,
SELLER-TOPOLOGY-RESULT.md and SELLER-SCHEDULER-OWNERSHIP-PROPOSAL.md.

One metadata SSH attempt failed to connect; one identical read-only retry passed.
No service restart or access change was used. R2, writeACL/KMS, schema transition,
accepted capacity and enabled customer journey remain open.


## S1687 reviewed narrow ownership design

CC APPROVE_WITH_NITS; GLM and DeepSeek APPROVE_WITH_MANDATES permit new isolated
implementation of only the three overlapping Beat-entry removals. No application
source changed and no exact-code/integration/production approval exists. Preserve
all30web jobs, callable tasks, other Beat entries, queues, singleton Beat and S1685.
The accepted proof plan is seller-scheduler-ownership-continuation/outputs/
SELLER-PROOF-PLAN-REFINEMENT.md; original reports and annotations are separate.

Exact retained image d55c95a5 contains Celery5.6.3. A new network-none/read-only
container inspected PersistentScheduler merge/sync; a separate synthetic shelve
probe reopened20held-base entries with only the3proposed keys omitted and retained
exactly17. This is base-framework proof, not actual configured Beat, broker emission
or candidate proof. First probe failed on Python path; new-container retry passed.
No old fixture changed. No production schedule-store deletion is justified.

Before held-branch integration require actual lifecycle30-ID registration plus
conditional, persisted, reconciliation/settlement and startup-failure cases; exact
image restart from the19-entry production-main seed (plus conditional entries),
removed-key due boundaries/no emissions, retained seller-search emissions and a
second restart; actual due seller publication/search/pause/retry; exact-code review.
SCHEDULER_MODE=celery or SKIP_SERVICES=1 leaves the3workflows ownerless after this
change. APScheduler failures retry on the next tick rather than periodic Celery's
60-second retry cushion. No new mode/retry/fail-fast behavior belongs to this slice.
Production remains gated on actual scheduler liveness/jobs and observable failure,
old-producer exclusion, queued/in-flight accounting and rollback. HTTP200/mode-only
health and previously tolerated overlap do not prove safety. Profile/translation
backlogs remain untouched, with external consumer coverage unverified.


## S1688 isolated ownership implementation and registration proof

Candidate 3e473b9972c5704a3b2874829310cf23b801f5e7 removes only the three
overlapping Beat entries and adds ownership comments plus historical-spec notes.
Callable tasks/retries, all web registrations, other Beat entries, queues, singleton
Beat and S1685 remain unchanged. The candidate is isolated, not integrated or
released. The final image's 1,307 app/migration/startup-script/spec files match source.

Actual lifespan with real APScheduler and a new Redis store passed 15 registration
cases. Baseline and restart contain all30IDs. Existing optional briefing/watchdog/
reconciliation jobs remain persisted when later disabled; a fresh store omits each
conditional job. Reconciliation adds its job before attempting the startup event;
event failure leaves that job registered. Failure on the second settlement add
leaves only the reaper (27totaljobs). Scheduler start failure leaves26pending jobs
and no running scheduler/settlement; briefing exception leaves5pending jobs. Redis
construction failure/timeout falls back to memory. Tolerated startup timeout,
celery mode and SKIP_SERVICES all serve synthetic HTTP200 with no running owner.

These are registration/persistence/failure observations, not business execution:
the fixture starts APScheduler paused and stubs provider, tokenizer, database,
agent and health dependencies explicitly. HTTP200/healthy/mode-only health is not
liveness proof. Reminders/confirmations now recover at the next hourly web tick,
without periodic Beat's60-second retry cushion; callable retries are unchanged.
Production requires actual running jobs and an operator-visible failure signal.
Exact-image due Beat restart/emission proof and admitted-worker SQL/outbox/search/
pause/retry proof remain separately recorded gates, followed by exact-code Council
approval before held-branch integration. No production authority is conferred.
Evidence: seller-scheduler-ownership-implementation/outputs/runtime-evidence.

Final-image Beat persistence proof also passed: exact production-main schedule
seed (19unconditional entries, plus conditional Gmail/archive cases) on the same
Celery5.6.3 dependency image; configured old/new starts against one new persistent
path;125seconds with no removed emissions, retained heartbeat/search emission,
retained scheduling history and second restart. A separate controlled clock run
through minute5/minute10 uses actual complete due selection. This is a schedule-
equivalent old image, not an assertion of production image-byte identity. New
synthetic broker receipts remain distinct from worker/business execution. The
three retired tasks cannot be inferred safe to consume from the real backlog.
