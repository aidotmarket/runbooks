# BQ-AUTONOMOUS-OPERATIONS — Gate 2 Chunk A (R3)
**Parent BQ:** `build:bq-autonomous-operations`
**Parent spec:** `specs/BQ-AUTONOMOUS-OPERATIONS.md` at commit `43d16df`
**Chunk:** A
**Revision:** R3
**Author:** Codex
**Repo:** aidotmarket/runbooks
**Spec path:** `specs/BQ-AUTONOMOUS-OPERATIONS-chunk-a.md`
**Scope:** Backend implementation only
**Deferred:** Chunk B frontend in `ops.ai.market`; Chunk C meta-runbook

## 0. Executive Summary
This document is the backend implementation spec for Gate 2 Chunk A. It does not reopen Gate 1 decisions. It converts the approved backend design into a build contract covering: schedule registry entity model and CRUD, private APScheduler substrate and migration assertion, predicate engine and dispatch envelopes, production dispatch contract handoff to a Railway-hosted microservice, allAI stewardship subscription and degraded mode, and the attention queue plus independent missed-escalation audit. Living State remains the source of truth for schedule definitions and queue state; APScheduler remains private; `schedule.run.complete` remains the only completion event; GH Actions schedules remain external; production schedule dispatch stays off Titan-1; and the audit continues to bypass allAI output and `queue:attention`.

Chunk A sequence:
1. `A1` Registry data model + CRUD
2. `A2` Executor + APScheduler substrate + startup assertion
3. `A3` Predicate engine + dispatch envelopes
4. `A4` allAI subscription
5. `A5` Attention queue + missed-escalation audit

Chunk A chooses a **dedicated REST API** instead of extending `state_request`. The registry still persists to Living State, but schedule-specific validation, manual trigger, run history, and GH webhook ingest are operational concerns that should not be hidden inside a generic state-patch surface.

## 1. Scope
### 1.1 In scope
- `backend/app/services/schedule_registry/` package
- `schedule:*` Living State entity kind and CRUD
- `queue:attention` entity kind and queue operations
- private APScheduler-backed executor, reconciler, and startup manifest assertion
- migration plan for in-process recurring work and the two live Celery Beat jobs
- tracking and webhook ingest for GH Actions external schedules
- predicate engine with both approved v1 forms and all ten approved comparators
- dispatch envelope and completion-event contracts, including `run_id`, `attempt_number`, and duplicate semantics
- allAI stewardship queue, degraded mode, split criterion, and post-prerequisite integration
- missed-escalation audit, Telegram correlation contract, and watchdog
- acceptance criteria and Gate 3 verification mapping for A1-A5

### 1.2 Out of scope
- `ops.ai.market` UI changes
- runbook-of-runbooks/meta-runbook deliverable
- GH workflow regeneration from registry data
- compound predicates beyond the two approved forms
- replacement of APScheduler with another substrate
- auth/payment/security redesign beyond existing backend controls

### 1.3 Inherited constraints
- Living State is the single source of truth for schedule definitions and attention-queue state.
- APScheduler is internal only; no direct imports or decorators may remain outside the executor adapter.
- `schedule.run.complete` is the only completion event type; `status` carries outcome.
- production schedules must run on Railway-hosted executor infrastructure and must not dispatch through Titan-1.
- GH Actions schedules are `dispatch_mode=gh_actions_external`, outside the sole-API invariant.
- Missed-escalation severity is derived from raw events and schedule state, not queue contents or allAI output.
- Chunk A Gate 3 may not start until `bq-allai-escalation-flusher-wiring` is Gate 3 approved.

## 2. Dependencies and Build Order
### 2.1 Hard prerequisites
**Prerequisite BQs:**
- `bq-allai-escalation-flusher-wiring`
- `build:bq-production-agent-dispatch-microservice` — P0 prerequisite for this BQ's Gate 3 whenever `run_environment=prod` schedules use `dispatch_mode=prod_agent`
- `build:bq-titan-1-production-extraction` — P0 prerequisite for this BQ's Gate 3 for the backup substrate migration referenced in `§6.6.2`

Gate 1 identified the P2+ flusher path as unwired. Chunk A implementation may be authored and even partially landed before that BQ merges, but Chunk A Gate 3 verification must not begin until it is approved. A4 and A5 both depend on the flusher no longer being a noop.

This Chunk A spec defines, but does not implement, the production dispatch microservice interface. `build:bq-production-agent-dispatch-microservice` owns the Railway-hosted service implementation and must be Gate 3 approved before Chunk A Gate 3 verifies any production `prod_agent` schedule.

This Chunk A spec also does not migrate the production backup substrate off Titan-1. `build:bq-titan-1-production-extraction` owns that migration and must be Gate 3 approved before Chunk A Gate 3 can claim the backup-verify production path is fully compliant.

Required post-prerequisite call sites:
- `backend/app/allai/escalation_pipeline.py:217-221`
  - route selection between immediate send and batch flush must be live
- `backend/app/allai/escalation_pipeline.py:308-369`
  - batch flush path must preserve all `correlation_*` fields introduced by Chunk A

Required post-prerequisite behavior:
- P2 stewardship items can enter the batch path without silent drop.
- batched items preserve `correlation_run_id`, `correlation_schedule_id`, `correlation_expected_fire_at`, and `correlation_predicate_evaluated_at`.
- flush failures are observable in logs/events.

### 2.2 Dependency / build-order diagram
```text
A1 Registry Data Model + CRUD
  -> A2 Executor + Startup Assertion
  -> A3 Predicate Engine + Dispatch Envelopes
  -> A4 allAI Subscription
  -> A5 Attention Queue + Missed-Escalation Audit

Safe overlap:
- A1 schema authoring and A2 manifest authoring can overlap.
- A4 queue plumbing can begin once A3 finalizes envelope/result contracts.
- A5 attention-queue schema can begin once A1 entity conventions are fixed.
- A5 audit logic waits for A3 correlation fields and A4 routing behavior.
```

### 2.3 Recommended landing order
1. A1 first: it defines canonical entities and write semantics.
2. A2 second: it defines the runtime boundary and migration enforcement.
3. A3 third: it defines run identity and event contracts consumed by A4/A5.
4. A4 fourth: stewardship subscribes against the final completion-event shape.
5. A5 last: audit correctness depends on A1-A4 being stable.

## 3. Locked Implementation Decisions
### 3.1 API choice
Chunk A uses dedicated routes:
- `GET /api/v1/ops/schedules`
- `POST /api/v1/ops/schedules`
- `GET /api/v1/ops/schedules/{schedule_id}`
- `PATCH /api/v1/ops/schedules/{schedule_id}`
- `DELETE /api/v1/ops/schedules/{schedule_id}`
- `POST /api/v1/ops/schedules/{schedule_id}/trigger`
- `GET /api/v1/ops/runs`
- `GET /api/v1/ops/runs/{run_id}`
- `GET /api/v1/ops/attention`
- `PATCH /api/v1/ops/attention/{item_id}`
- `POST /api/v1/schedules/{schedule_id}/run-start`
- `POST /api/v1/schedules/{schedule_id}/run-result`

Justification: generic `state_request` is too weak for schedule-specific semantic validation, manual trigger, webhook idempotency, and run-oriented audit contracts. Dedicated routes keep Living State authoritative while making schedule behavior explicit and testable.

### 3.2 `run_id` format
Run-ID UUID version: `UUIDv7` per parent `§5.3` as amended in `08d0b0d→43d16df` Appendix G.1.

Chunk A chooses **UUIDv7** over ULID. It preserves time ordering, fits standard UUID tooling, and avoids custom identifier semantics. Contract: `run_id` is lowercase UUIDv7 string; `attempt_number` starts at `1`; `(run_id, attempt_number)` is the idempotency key.

### 3.3 Entity conventions
- schedule key pattern: `schedule:<dashed-name>`
- attention queue key: `queue:attention`
- both entity kinds must include `body.summary`
- all writes use existing Living State optimistic-lock patterns; no blind overwrites

## 4. Backend Package and Module Layout
### 4.1 New package layout
```text
backend/app/services/schedule_registry/
  __init__.py
  api.py
  constants.py
  errors.py
  models.py
  repository.py
  service.py
  validation.py
  seeding.py
  schemas/
    schedule.schema.json
    attention-queue.schema.json
    dispatch-envelope.schema.json
    run-result.schema.json
  executor/
    __init__.py
    apscheduler_adapter.py
    bootstrap.py
    dispatcher.py
    manifest_assertion.py
    registry_reconciler.py
    webhook_ingest.py
  predicates/
    __init__.py
    comparators.py
    engine.py
    forms.py
  audit/
    __init__.py
    attention_queue.py
    missed_escalation.py
    watchdog.py
```

### 4.2 Module responsibilities
| Module | Responsibility |
|---|---|
| `api.py` | FastAPI routers for schedules, runs, attention, external webhooks |
| `models.py` | Pydantic request/response models and enums |
| `repository.py` | thin Living State read/write/version wrapper |
| `service.py` | schedule CRUD orchestration and manual trigger entrypoint |
| `validation.py` | JSON Schema loading and semantic validation |
| `seeding.py` | idempotent seed definitions/application |
| `executor/apscheduler_adapter.py` | only allowed APScheduler import site |
| `executor/bootstrap.py` | startup entrypoint: assert, load, register, subscribe |
| `executor/dispatcher.py` | builds envelopes and dispatches council/direct/webhook runs |
| `executor/manifest_assertion.py` | scans code and checks `migration-manifest.yaml` |
| `executor/registry_reconciler.py` | one-minute registration drift repair |
| `executor/webhook_ingest.py` | shared GH run-start / run-result logic |
| `predicates/comparators.py` | ten comparators |
| `predicates/engine.py` | evaluation, cost budget, event emission |
| `audit/attention_queue.py` | queue writes, resolution, purge, session-open reads |
| `audit/missed_escalation.py` | R1-R6 independent audit rules and Telegram verification |
| `audit/watchdog.py` | audit-heartbeat watchdog |

### 4.3 APScheduler import boundary
Allowed direct import:
- `backend/app/services/schedule_registry/executor/apscheduler_adapter.py`

Forbidden everywhere else:
- `import apscheduler`
- `from apscheduler ...`
- direct `add_job(...)`
- direct recurring decorators such as `@cron(...)`

## 5. A1 — Registry Data Model + CRUD
### 5.1 Persistence model
Schedule definitions are stored as Living State entities keyed `schedule:<id>`. No dedicated schedule table is added in v1. The schedule entity stores canonical configuration, current runtime summary, counters, and bounded recent history. The event ledger remains the durable history for runs and audit correlation. This split is deliberate: entity state is current truth, ledger state is historical truth.

### 5.2 Required schema file
- `backend/app/services/schedule_registry/schemas/schedule.schema.json`

### 5.3 Required field set
Identity / descriptive:
- `id`
- `name`
- `description`
- `summary`
- `owner`
- `created_session`
- `last_edited_by`

Trigger definition:
- `trigger_type`
- `cron_expression` when `trigger_type=cron`
- `timezone`
- `predicate` when `trigger_type=state_predicate`
- `evaluation_cadence_seconds` when `trigger_type=state_predicate`

Dispatch definition:
- `run_environment`
- `agent`
- `dispatch_mode`
- `task_prompt` when `dispatch_mode in {council_request, prod_agent}`
- `callable_path` when `dispatch_mode=direct_callable`
- `gh_workflow_path` when `dispatch_mode=gh_actions_external`
- `council_mode` when `dispatch_mode=council_request`
- `agent_kind` when `dispatch_mode=prod_agent`
- `allowed_tools` when `dispatch_mode in {council_request, prod_agent}`
- `timeout_seconds`
- `budget_usd`
- `escalation_target`
- `priority`

Operational control:
- `enabled`
- `paused_until`
- `concurrency_policy`
- `max_instances`
- `misfire_grace_time_seconds`
- `coalesce`
- `run_id_authority`

Auto-managed:
- `last_run_at`
- `last_run_status`
- `last_run_task_id`
- `last_run_run_id`
- `last_run_result_entity_key`
- `next_run_at`
- `run_count_total`
- `run_count_failure`
- `run_history` bounded array of last 100 summarized runs

### 5.4 Defaults
| Field | Default |
|---|---|
| `timezone` | `UTC` |
| `run_environment` | `dev` for locally authored schedules; production seeds must set `prod` explicitly |
| `timeout_seconds` | `600` |
| `budget_usd` | `1.0` for LLM-backed dispatches |
| `enabled` | `true` |
| `concurrency_policy` | `skip_if_running` |
| `max_instances` | `1` |
| `misfire_grace_time_seconds` | `3600` |
| `coalesce` | `true` |
| `run_id_authority` | `executor`, except `gh_actions_external` |
| `owner` | `max` |

### 5.5 Enum/range validation
| Field | Allowed values / bounds |
|---|---|
| `trigger_type` | `cron`, `state_predicate`, `manual_only` |
| `run_environment` | `prod`, `dev` |
| `dispatch_mode` | `direct_callable`, `prod_agent`, `gh_actions_external`, `council_request` |
| `escalation_target` | `telegram_p0_p1`, `attention_queue`, `silent_success_only` |
| `concurrency_policy` | `serial_queue`, `skip_if_running`, `allow_parallel` |
| `run_id_authority` | `executor`, `external_webhook` |
| `priority` | integer `0..3` |
| `evaluation_cadence_seconds` | integer `>=60` |
| `timeout_seconds` | integer `>=1` |
| `misfire_grace_time_seconds` | integer `>=0` |
| `max_instances` | integer `>=1` |

### 5.6 Semantic validation rules
- `cron_expression` valid five-field cron only when `trigger_type=cron`
- `cron_expression` absent when `trigger_type!=cron`
- `predicate` present only when `trigger_type=state_predicate`
- `evaluation_cadence_seconds` required when `trigger_type=state_predicate`
- every schedule must declare `run_environment in {prod, dev}`
- `task_prompt` and `council_mode` required for `dispatch_mode=council_request`
- `task_prompt`, `agent_kind`, `allowed_tools`, `budget_usd`, and `timeout_seconds` required for `dispatch_mode=prod_agent`
- `callable_path` required for `dispatch_mode=direct_callable`
- `gh_workflow_path` required for `dispatch_mode=gh_actions_external`
- `dispatch_mode=gh_actions_external` requires `run_id_authority=external_webhook`
- `allowed_tools` may be non-empty only for `council_request` or `prod_agent`
- `budget_usd` required for LLM-backed schedules and may be null for pure callables
- `concurrency_policy=allow_parallel` requires `max_instances > 1`
- `trigger_type=manual_only` forbids `cron_expression`, `predicate`, and `evaluation_cadence_seconds`
- `run_environment=prod AND dispatch_mode=council_request` is a schema rejection; router refuses to register or patch such a schedule
- `dispatch_mode=prod_agent` is valid only for `run_environment=prod`
- `dispatch_mode=council_request` is valid only for `run_environment=dev`
- any schedule registered into the production executor must assert Railway hosting fingerprint at startup
- create callers may not set auto-managed fields except seed/migration tooling

### 5.7 CRUD contracts
#### 5.7.1 Create
`POST /api/v1/ops/schedules`

Behavior:
- validate against schema + semantic rules
- normalize defaults
- derive/create key `schedule:<id>`
- reject duplicate key with `409 Conflict`
- return canonical object plus entity version

Create requirements:
- caller provides `id` or a `name` from which `id` can be derived
- `summary` is required and non-empty
- auto-managed fields must not be supplied

#### 5.7.2 Read/list
`GET /api/v1/ops/schedules`

Supported filters:
- `agent`
- `enabled`
- `trigger_type`
- `dispatch_mode`
- `escalation_target`
- `owner`
- `include_external`

Supported sorting:
- default `id`
- optional `next_run_at`

`GET /api/v1/ops/schedules/{schedule_id}` returns:
- canonical entity body
- Living State version
- derived runtime snapshot: `is_due_now`, `is_registered`, `runtime_registration_hash`, `next_evaluation_at` where relevant

#### 5.7.3 Patch
`PATCH /api/v1/ops/schedules/{schedule_id}`

Requirements:
- `expected_version` required
- patch applies only to mutable fields
- full resulting entity is revalidated before write
- write emits change signal for executor reconciliation

Mutable fields:
- `name`, `description`, `summary`
- `cron_expression`, `timezone`, `predicate`, `evaluation_cadence_seconds`
- `agent`, `task_prompt`, `callable_path`, `gh_workflow_path`, `council_mode`, `agent_kind`, `allowed_tools`
- `timeout_seconds`, `budget_usd`, `escalation_target`, `priority`
- `enabled`, `paused_until`
- `concurrency_policy`, `max_instances`, `misfire_grace_time_seconds`, `coalesce`
- `owner`

Immutable after create except seed/migration tooling:
- `id`
- `run_environment`
- `dispatch_mode`
- `run_id_authority`
- `created_session`

`dispatch_mode` and `run_environment` are intentionally immutable: moving between internal, production-agent, council, and external ownership is a migration, not a casual edit.

#### 5.7.4 Delete
`DELETE /api/v1/ops/schedules/{schedule_id}`

Requirements:
- `expected_version` required
- removes the schedule entity
- preserves event-ledger history
- triggers in-memory deregistration via reconciler
- blocks deletion of protected/core seed schedules unless privileged internal admin semantics are used

### 5.8 Manual trigger
`POST /api/v1/ops/schedules/{schedule_id}/trigger`

Contract:
- allowed for enabled or disabled schedules; paused schedules may still be manually triggered
- always creates a new `run_id`
- always uses `attempt_number=1`
- sets `trigger.type=manual`
- bypasses cron/predicate gating
- respects `dispatch_mode` and `timeout_seconds`
- respects `concurrency_policy` by default; privileged `force=true` may bypass overlap protection

### 5.9 Optimistic locking
Rules:
- every PATCH and DELETE requires `expected_version`
- attention-item resolution requires `expected_version`
- executor/webhook updates use read-modify-write with max three retries
- conflict response is `409` with error code `schedule_version_conflict`, current version, and current entity snapshot

Conflict behavior:
- user-authored edits are never silently merged with conflicting user-authored edits
- executor/webhook retries apply only to auto-managed fields
- auto-managed updates must not overwrite user edits to `enabled`, `cron_expression`, `predicate`, `priority`, or other control fields

### 5.10 Seed data contract
Seeds live in `seeding.py` and are applied explicitly, not implicitly in request handlers.

Seed categories:
- internal migrated schedules
- GH external tracked schedules
- audit/watchdog schedules
- queue maintenance schedules

Seed rules:
- create if missing
- patch only seed-owned fields
- never silently overwrite user-owned fields unless a reviewed migration-correction step explicitly says so

## 6. A2 — Executor + APScheduler Substrate + Startup Assertion
### 6.1 Private substrate rule
After Chunk A lands:
- no backend code outside `schedule_registry.executor.apscheduler_adapter` imports APScheduler
- no direct `@cron` decorators remain
- no direct `scheduler.add_job(...)` calls remain outside the adapter
- no service/API surface exposes APScheduler types

### 6.2 Runtime architecture
Executor components:
- `bootstrap`
  - run startup assertion
  - load schedules
  - register internal jobs
  - subscribe to schedule-change notifications
- `apscheduler_adapter`
  - own the single scheduler instance
  - translate registry semantics into APScheduler settings
- `registry_reconciler`
  - every minute compare registry state to live registration and repair drift

The one-minute sweep is required even if CRUD paths also push immediate updates. It is the safety net for missed notifications, restarts, and partial failures.

### 6.2a Production hosting contract
Production internal schedules and the APScheduler executor run only on Railway, specifically in the production Railway backend service that owns `ai-market-backend` recurring work. Titan-1 may run dev/test schedulers only, and those schedules must carry `run_environment=dev`.

Enforcement:
- production startup refuses to boot the executor unless the process exposes the expected Railway-hosted startup fingerprint
- any schedule with `run_environment=prod` must be seeded, reconciled, and executed only from the Railway-hosted production service
- Titan-1 may seed or exercise `run_environment=dev` schedules locally, but may not host live production APScheduler registration or production dispatch

### 6.3 Required manifest
File:
- `backend/config/migration-manifest.yaml`

Allowed dispositions:
- `migrated_to: schedule:<id>`
- `keep_ephemeral: <rationale>`
- `retired: <commit_sha>`
- `external_to_backend: <location>`

Startup assertion:
1. scan backend source for `while True` loops containing `sleep(...)` / `asyncio.sleep(...)` at durations `>=60s`
2. inspect Celery `beat_schedule` keys
3. inspect known recurring-registration helpers
4. compare every detected recurring-work site to the manifest
5. abort startup if any recurring pattern lacks a manifest disposition

Implementation notes:
- regex/static detection is acceptable for v1; AST parsing is optional
- false positives are acceptable if they force manifest review
- false negatives for known patterns listed in the migration inventory are not acceptable
- fatal logs must include file path and line number for every unmatched site

### 6.4 Translation to APScheduler
| Registry field | APScheduler behavior |
|---|---|
| `cron_expression` | cron trigger |
| `timezone` | trigger timezone |
| `concurrency_policy=skip_if_running` | `max_instances=1`, discard overlap |
| `concurrency_policy=serial_queue` | `max_instances=1`, allow one pending fire inside grace |
| `concurrency_policy=allow_parallel` | `max_instances=<value>` |
| `misfire_grace_time_seconds` | misfire grace time |
| `coalesce` | coalesce flag |
| `max_instances` | max instances |

Additional runtime semantics:
- `skip_if_running` must emit observability for overlap skips
- `serial_queue` is limited to one pending logical fire in v1; no unbounded backlog

### 6.5 Reconciler cadence and duties
Cadence:
- every 60 seconds

Duties:
- reload enabled schedules
- compare entity version/hash to registration metadata
- add missing jobs
- update stale jobs
- remove disabled/deleted jobs
- recompute `next_run_at`
- warn if internal registry schedules are not registered
- reject any `run_environment=prod` internal schedule observed on a non-Railway host
- ignore `gh_actions_external` for internal registration while still maintaining metadata

### 6.6 Migration inventory and exact file actions
#### 6.6.1 Live Celery Beat jobs
Jobs to migrate:
- `celery-worker-heartbeat`
- `gmail-polling`

Required backend file changes:
- update `backend/app/core/celery_app.py`
  - delete both live entries from `app.conf.beat_schedule`
  - leave `beat_schedule = {}` or equivalent empty structure, with comment that registry is authoritative for backend recurring work
- update deploy/process config in backend repo
  - remove dedicated Celery Beat process once Gate 3 proves migration
  - if that removal is staged later, manifest must still record the transitional disposition and beat schedule must already be empty

Required seed entries:
- `schedule:backend-celery-worker-heartbeat`
- `schedule:backend-gmail-polling`

Recommended dispatch mode:
- both use `dispatch_mode=direct_callable`
- callables point at the existing task wrappers, not at Celery Beat

Migration transition table:

| Scheduler | Source file to delete | Seed registry entry key | Env vars/feature flags to retire | Rollout order |
|---|---|---|---|---|
| `celery-worker-heartbeat` | `backend/app/core/celery_app.py` | `schedule:backend-celery-worker-heartbeat` | `(audit: grep backend for *_INTERVAL_*, *_CRON_*, *_SCHEDULE_*)` | `1st` |
| `gmail-polling` | `backend/app/core/celery_app.py` | `schedule:backend-gmail-polling` | `GMAIL_POLL_INTERVAL_SECONDS`, `(audit: grep backend for *_INTERVAL_*, *_CRON_*, *_SCHEDULE_*)` | `2nd` |
| `backup-verify (backend portion)` | `backend/app/core/scheduler.py` | `schedule:backend-backup-verify-daily` | `BACKUP_VERIFY_* if any`, `(audit: grep backend for *_INTERVAL_*, *_CRON_*, *_SCHEDULE_*)` | `3rd (after bq-titan-1-production-extraction completes)` |

#### 6.6.2 Additional internal migrations from parent inventory
Required seed entries:
- `schedule:backend-sysadmin-health-check-5m`
- `schedule:backend-backup-verify-daily`
- `schedule:backend-incident-sweeper-5m`
- `schedule:crm-steward-daily-maintenance`
- `schedule:backend-sysadmin-monitor-<name>` per migrated monitor

Required backend code changes:
- in `backend/app/core/scheduler.py`, delete or disable recurring registration for SysAdmin health and backup verify
- delete or disable the `IncidentSweeper` 300-second self-loop
- delete or disable `CRMStewardAgent` daily self-registration
- remove per-monitor ad-hoc recurring registration from `SysAdminAgent` and replace it with seed-backed schedules

Explicit manifest `keep_ephemeral` items:
- `BaseAgent` heartbeat 90-second TTL
- Telegram remediation per-proposal timeouts

Backup substrate cross-reference:
Chunk A does NOT migrate the backup substrate itself. The backup-verify cadence remains as specified here, but the underlying `/var/tmp/koskadeux/backups` mechanics currently tied to Titan-1 disk are migrated by `build:bq-titan-1-production-extraction`, which is a P0 Gate 3 prerequisite for this BQ. Recommended destination, pending finalization in that BQ, is Backblaze B2.

#### 6.6.3 GH Actions tracked schedules
Required seed entries:
- `schedule:gh-smoke-test`
- `schedule:gh-backup-daily`
- `schedule:gh-backup-verify-ci-daily`
- `schedule:gh-health-check-daily`
- `schedule:gh-quarantine-weekly`
- `schedule:gh-runbook-harness-daily`

Locked three-way backup stagger:
- GH backup `03:00 UTC`
- backend verify `03:30 UTC`
- GH CI verify `06:00 UTC`

This stagger is required and must remain distinct in seed metadata and verification tests.

### 6.7 Registration classes
Internal schedules:
- `trigger_type=cron` -> cron job
- `trigger_type=state_predicate` -> cadence job that evaluates predicate
- `trigger_type=manual_only` -> no timed registration

External schedules:
- `dispatch_mode=gh_actions_external` -> never internally scheduled
- still loaded so run-start / run-result webhooks can resolve against known schedules

### 6.8 Dispatch Host Matrix
| dispatch_mode | allowed_run_environment | execution_host | Titan-1 permitted? |
|---|---|---|---|
| `direct_callable` | `prod`, `dev` | In-process on the executor's host | Only if executor runs on Titan-1 (`dev` only) |
| `prod_agent` | `prod` | Railway (`bq-production-agent-dispatch-microservice`) | NEVER |
| `gh_actions_external` | `prod`, `dev` | GitHub-hosted runners | NEVER (GitHub cloud only) |
| `council_request` | `dev` only | Titan-1 CLIs via Koskadeux MCP gateway | Yes (`dev` only) |

Production schedules (`run_environment=prod`) must never dispatch through Titan-1; registry write-validation enforces this.

### 6.9 Failure handling
Fatal bootstrap failures:
- manifest assertion failure
- invalid schema or seed data
- APScheduler bootstrap failure
- inability to load registry definitions
- missing or invalid Railway production-host fingerprint for a production executor

Per-schedule runtime failures:
- one schedule registration fails while others continue
- one webhook update conflicts but succeeds on retry
- one predicate evaluation errors
- one prod-agent completion webhook retries idempotently on duplicate `(run_id, attempt_number)`

Per-schedule runtime failures surface as events/logs and do not kill the whole scheduler unless the adapter itself becomes unusable.

## 7. A3 — Predicate Engine + Dispatch Envelopes
### 7.1 Supported forms
Chunk A implements exactly the two approved v1 forms.

Form A:
```json
{"kind":"event_age_exceeds","event_type":"backup.verify.complete","threshold_seconds":172800}
```

Form B:
```json
{"kind":"entity_field_comparison","entity_key":"config:backup-verify-latest","field_path":"body.last_success_at","comparator":"older_than_seconds","value":86400}
```

No compound logic is added.

### 7.2 Comparator surface
Required comparators:
- `equals`
- `not_equals`
- `exists`
- `missing`
- `older_than_seconds`
- `newer_than_seconds`
- `in_set`
- `not_in_set`
- `count_exceeds`
- `count_below`

Runtime rules:
- unsupported comparator fails validation at create/patch time
- type mismatch records evaluation error and yields `matched=false`
- time comparators require parseable datetimes
- count comparators require array-like values

### 7.3 Predicate evaluation contract
Entry point:
- `SchedulePredicateEngine.evaluate(schedule, now_utc)`

Required result fields:
- `schedule_id`
- `predicate_kind`
- `evaluated_at`
- `matched`
- `comparator` where relevant
- `field_path` where relevant
- `evaluation_cost_ms`
- `evaluation_error`
- `correlation_predicate_evaluated_at`

Required event:
- `schedule.predicate.evaluated`

Required event fields:
- `schedule_id`
- `evaluated_at`
- `matched`
- `evaluation_cost_ms`
- predicate metadata sufficient for audit/debugging

Debounce:
- after a true predicate dispatches, that schedule must observe a false result at least once before a new true result can dispatch
- implementation stores `last_predicate_state` and `last_predicate_true_fire_at` in auto-managed metadata

### 7.4 Evaluation cost budget
Budget:
- soft: `100ms`
- hard: `500ms`

Behavior:
- `>100ms` -> warning log with schedule ID and cost
- `>500ms` -> evaluation failure for that attempt, no dispatch
- still emit `schedule.predicate.evaluated` with `matched=false` and `evaluation_error=budget_exceeded`

### 7.5 Dispatch envelope schema
Required file:
- `backend/app/services/schedule_registry/schemas/dispatch-envelope.schema.json`

This schema is the dispatch-time half of the parent contract. It must preserve the `§5.3` dispatch envelope boundary and must not absorb runtime/result facts that belong to parent `§5.4` `schedule.run.complete` events.

Base required fields:
- `schedule_id`
- `run_id`
- `attempt_number`
- `schedule_version`
- `dispatch_mode`
- `dispatched_at`
- `trigger`
- `agent`
- `timeout_seconds`
- `correlation_run_id`
- `correlation_schedule_id`

`prod_agent` required fields:
- `run_environment`
- `agent_kind`
- `task_prompt`
- `allowed_tools`
- `cost_cap_usd`
- `correlation_dispatched_at`

Shared fields:
- `schedule_name`
- `budget_usd`
- `escalation_target`
- `priority`

Conditional correlation fields:
- `correlation_expected_fire_at`
- `correlation_predicate_evaluated_at`

Conditional payload fields:
- `task_prompt`
- `callable_path`
- `council_mode`
- `allowed_tools`
- `gh_workflow_path`
- `predicate_snapshot`

`trigger` object fields:
- `type` = `cron | state_predicate | manual | gh_actions_external`
- `cron_expression` when relevant
- `timezone` when relevant
- `predicate_kind` when relevant
- `expected_fire_at` when relevant

`dispatch_mode=prod_agent` request envelope:

```json
{
  "schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "run_id": "01968caa-f82a-7e91-b5b1-0d84f4a6476b",
  "attempt_number": 1,
  "schedule_version": 12,
  "dispatch_mode": "prod_agent",
  "dispatched_at": "2026-04-22T07:00:00Z",
  "trigger": {
    "type": "cron",
    "cron_expression": "0 7 * * 1",
    "timezone": "UTC",
    "expected_fire_at": "2026-04-22T07:00:00Z"
  },
  "agent": "sysadmin",
  "run_environment": "prod",
  "agent_kind": "sysadmin",
  "task_prompt": "Execute the approved production stewardship task.",
  "allowed_tools": ["state_patch", "ledger_append"],
  "cost_cap_usd": 1.0,
  "timeout_seconds": 900,
  "correlation_run_id": "01968caa-f82a-7e91-b5b1-0d84f4a6476b",
  "correlation_schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "correlation_dispatched_at": "2026-04-22T07:00:00Z",
  "correlation_expected_fire_at": "2026-04-22T07:00:00Z"
}
```

Request envelopes MUST exclude all post-dispatch/runtime fields, including `started_at`, `completed_at`, `status`, `summary`, and any result-only entity references. Those fields appear only on the completion/result path defined in `§7.6-§7.7`, preserving the parent `§5.3` dispatch-side / `§5.4` result-side split.

Chunk A does not implement the production dispatch microservice itself. It defines the request envelope shape this backend must emit and the completion event shape it must ingest, and defers microservice implementation to `build:bq-production-agent-dispatch-microservice`.

### 7.6 Completion event schema and idempotency
Required file:
- `backend/app/services/schedule_registry/schemas/run-result.schema.json`

Rules:
- event type is always `schedule.run.complete`
- `status` is `success | failure | timeout | agent_error | dispatch_error`
- primary key is `(run_id, attempt_number)`

Late duplicate semantics:
- already-seen `(run_id, attempt_number)` is accepted idempotently
- duplicate does not re-increment counters
- if duplicate payload differs, first writer wins and the late payload is logged as mismatch
- a synthesized timeout followed by a late real completion with the same key is treated as duplicate and ignored for latest-state mutation

Counter rules:
- increment `run_count_total` only on first-seen attempt `1`
- increment `run_count_failure` only on first-seen attempt whose status is `failure`, `timeout`, `agent_error`, or `dispatch_error`
- higher-attempt retries do not increment `run_count_total`

Required completion event shape for `prod_agent` dispatches:
- event type remains `schedule.run.complete`
- writer may be the production dispatch microservice or a backend webhook handler acting on its authenticated callback
- payload must include `schedule_id`, `run_id`, `attempt_number`, `started_at`, `completed_at`, `status`, `summary`, and all `correlation_*` fields required by the trigger type
- `status` remains the parent `§5.4` discriminator and is limited to `success | failure | timeout | agent_error | dispatch_error`
- `started_at` is first introduced here on the result path; it MUST NOT be present in the `§7.5` outbound request envelope
- this section inherits the parent `§5.4` sole-completion-event rule: no `prod_agent`-specific success/failure event taxonomy is allowed

### 7.7 Production dispatch webhook contract
Endpoint:
- `POST /api/v1/ops/schedules/prod-agent/run-result`

Auth model:
- transport is HMAC-SHA256 over the raw request body, delivered as `X-Dispatch-Signature: sha256=<hexdigest>`
- backend reads `PROD_AGENT_WEBHOOK_HMAC_SECRET` from Infisical-backed environment at startup; canonical source of truth is Infisical project `ai-market`, environment `prod`, secret path `/backend/autonomous-operations/prod-agent-dispatch`, secret name `PROD_AGENT_WEBHOOK_HMAC_SECRET`
- backend also reads optional `PROD_AGENT_WEBHOOK_HMAC_SECRET_PREVIOUS` from the same Infisical path to support overlap-window rotation
- backend validates the signature before any state mutation or event write

Idempotency:
- deduplicate strictly on `(run_id, attempt_number)`
- duplicate callbacks return success with `idempotent=true`
- mismatched duplicate payloads are logged and do not overwrite first-writer data

Behavior:
- request body must conform to the `schedule.run.complete` contract
- missing `X-Dispatch-Signature` header returns HTTP `400`
- backend computes HMAC-SHA256 of the raw request body with `PROD_AGENT_WEBHOOK_HMAC_SECRET`, compares in constant time, and accepts on current-key match
- if current key fails and `PROD_AGENT_WEBHOOK_HMAC_SECRET_PREVIOUS` is configured, backend retries verification once against the previous key to support rotation overlap
- signature mismatch after both checks returns HTTP `401` and logs `webhook.auth.reject` with `schedule_id` when present, `run_id`, `attempt_number`, and available `correlation_*` fields
- successful verification logs `webhook.auth.accept` with `validated_secret=current|previous` for rotation auditability
- backend resolves `schedule_id`, updates `last_run_*` fields, emits/writes the sole completion event to the event ledger, and records correlation metadata required for audit
- this webhook is in scope for Chunk A; the outbound Railway microservice itself is not
- Gate 3 must prove the wire contract with: a schema/auth test asserting `X-Dispatch-Signature: sha256=<hexdigest>` on raw-body payloads; a missing-header test returning `400`; an invalid-signature test returning `401` plus `webhook.auth.reject`; and a rotation-window test showing `webhook.auth.accept` with `validated_secret=previous`

### 7.8 GH external webhook contract
`POST /api/v1/schedules/{schedule_id}/run-start`

Required fields:
- `run_id`
- `attempt_number`
- `started_at`
- `github_run_id`
- `github_workflow`

`POST /api/v1/schedules/{schedule_id}/run-result`

Required fields:
- full completion-event shape

Behavior:
- schedule must exist and have `dispatch_mode=gh_actions_external`
- `run_id_authority` must be `external_webhook`
- result ingest updates `last_run_*` fields, emits/stores `schedule.run.complete`, and deduplicates by `(run_id, attempt_number)`
- missing prior run-start should warn but not block result ingestion; implicit creation is allowed for robustness

### 7.9 Observability
Minimum logs/metrics:
- log every dispatch with `schedule_id`, `run_id`, `attempt_number`, `trigger.type`
- counters: dispatch attempts, dispatch failures, predicate evaluations, predicate matches, overlap skips, webhook duplicates
- histograms: predicate evaluation cost, dispatch latency, completion latency

## 8. A4 — allAI Subscription
### 8.1 Subscription contract
`AllAIBrainAgent.startup()` subscribes only to `schedule.run.complete`. It must not subscribe to non-existent `schedule.run.failed`, `schedule.run.timeout`, or similar lifecycle events. Stewardship filtering happens on `status`, schedule metadata, and result content.

Host contract:
- `AllAIBrainAgent` runs on Railway inside the `ai-market-backend` service
- its bounded queue, two-worker thread pool, and Redis spillover coordination all run in the Railway backend process
- Redis is the existing production Redis
- Titan-1 is prohibited from carrying live stewardship classification, queue processing, escalation dispatch, or attention-queue write traffic

Classification inputs:
- completion event payload
- current schedule metadata
- result entity summary where available
- correlation metadata

### 8.2 Queue topology
Required implementation:
- in-memory bounded queue size `100`
- Redis spillover key `allai:stewardship:spillover`
- dedicated stewardship thread pool size `2`

Ordering:
- higher severity first
- within same severity, older `dispatched_at` first

Spillover behavior:
- items above in-memory capacity spill to Redis
- drain from Redis when in-memory queue size drops below `80`
- all `correlation_*` fields must survive spill and drain unchanged

### 8.3 Degradation policy
Rolling metric:
- stewardship classification p95 latency over last `60s`

Enter degraded mode when:
- p95 `> 5s`

Safe-default routing while degraded:
- stop expensive classifier work for stewardship
- mark event `escalate_suspected=true`
- broaden queue writes so all non-`INFO`/`DEBUG` stewardship events land in `queue:attention`
- do not send Telegram directly from stewardship while degraded

Exit degraded mode when:
- p95 `< 2s` continuously for `10 minutes`

Required events:
- `allai_brain.stewardship_degraded`
- `allai_brain.stewardship_degraded_cleared`

### 8.4 Split criterion
Primary exact metric:
- stewardship completion-event ingress averaged over `7 days`

Threshold:
- file split BQ if average ingress exceeds `1000 events/day` for `7 consecutive days`

Additional forced triggers:
- degraded mode entered `>=3` times in `7 days`
- p95 `>10s` for `15+` minutes twice in `48h`

Carve procedure:
1. create `build:bq-allai-scheduler-steward-agent-split`
2. freeze new stewardship features in `AllAIBrainAgent`
3. copy queue/contract behavior into dedicated-agent design target
4. keep `AllAIBrainAgent` as fallback subscriber until split agent is verified

### 8.5 Routing expectations
| Target / classification result | Required route |
|---|---|
| `silent_success_only` success/info | log only |
| `attention_queue` | write `queue:attention` |
| `telegram_p0_p1` classified `P0/P1` | immediate Telegram + queue |
| `telegram_p0_p1` classified `P2` | queue + P2 batch path once prerequisite lands |

### 8.6 Post-flusher-wiring expectation
After the prerequisite lands:
- P2 stewardship items can be batch-enqueued without losing `correlation_*` metadata
- batch flush emits observable send/log events
- failed enqueue attempts are visible, not silent

## 9. A5 — Attention Queue + Missed-Escalation Audit
### 9.1 `queue:attention` entity kind
Required file:
- `backend/app/services/schedule_registry/schemas/attention-queue.schema.json`

Entity key:
- `queue:attention`

Top-level body fields:
- `summary`
- `items`
- `last_digest_generated_at`
- `last_purge_at`

### 9.2 Attention item shape
Required fields:
- `item_id`
- `created_at`
- `source_schedule_id`
- `source_run_id`
- `source_event_ledger_id`
- `severity`
- `classified_by`
- `classification_confidence`
- `title`
- `body_markdown`
- `actions_suggested`
- `resolved`
- `resolved_at`
- `resolved_by`
- `resolution_note`
- `correlation_run_id`
- `correlation_schedule_id`
- `correlation_expected_fire_at`
- `correlation_predicate_evaluated_at`

Write/read behavior:
- unresolved items are retained until explicit resolution
- read order is severity desc, then `created_at` desc
- purge applies only to resolved items

### 9.3 Severity ladder
| Queue severity | Meaning | Required routing |
|---|---|---|
| `INFO` | informational | queue optional / digest |
| `WARN` | non-urgent drift | queue only |
| `P2` | degraded operation | queue + batch path once prerequisite lands |
| `P1` | urgent | Telegram + queue |
| `P0` | critical | Telegram + queue + repeat-alert policy if unacked |

Normalization:
- event `info` -> `INFO`
- event `warn` -> `WARN`
- event `p2` -> `P2`
- event `p1` -> `P1`
- event `p0` -> `P0`

### 9.4 Session-open digest pattern
On `kd_session_open`, the bundle must read unresolved items from `queue:attention`.

Read contract:
- unresolved only by default
- sorted by severity desc, then `created_at` desc
- include counts by severity and top item summaries
- do not auto-resolve on read

Resolution endpoint:
- `PATCH /api/v1/ops/attention/{item_id}`

Resolution rules:
- `expected_version` required
- set `resolved=true`, `resolved_at`, `resolved_by`, optional `resolution_note`

### 9.5 Missed-escalation audit
Implementation module:
- `backend/app/services/schedule_registry/audit/missed_escalation.py`

Seeded schedules:
- `schedule:missed-escalation-audit-hourly`
- `schedule:missed-escalation-audit-watchdog`

Integrity rule:
- the audit derives "should-have-escalated" candidates from raw events and schedule state
- it must not inspect `queue:attention` to decide if escalation was required

### 9.6 Rules R1-R6 and correlation keys
| Rule | Detection summary | Severity | Correlation key |
|---|---|---|---|
| `R1` | `schedule.run.complete` failure on `telegram_p0_p1` schedule with priority `0/1` | `P1` | `run_id` |
| `R2` | repeated failing pattern within 24h on `telegram_p0_p1` schedule | `P1` | `run_id` |
| `R3` | `status=dispatch_error` | `P1` | `run_id` |
| `R4` | cron schedule missed expected fire | `P1` | `schedule_id + expected_fire_at` |
| `R5` | `status=timeout` on priority `0/1` schedule | `P0` | `run_id` |
| `R6` | predicate evaluated true but no completion arrives in window | `P1` | `schedule_id + predicate_evaluated_at` |

Additional requirements:
- `R4` applies only to cron schedules
- state-predicate and manual-only schedules are excluded from `R4`

### 9.7 `cron_expected_interval_seconds` derivation
Rules:
- fixed-step cron -> step interval
- daily/weekly/monthly cron -> maximum gap between consecutive expected fires across a one-year horizon
- irregular schedules use max gap, not average

An existing cron iteration helper may be used; otherwise implement locally.

### 9.8 Telegram correlation verification
Every schedule-driven Telegram send used by audit verification must preserve:
- `correlation_run_id`
- `correlation_schedule_id`
- `correlation_expected_fire_at`
- `correlation_predicate_evaluated_at`

Verification mapping:
- `R1`, `R2`, `R3`, `R5` -> `correlation_run_id`
- `R4` -> `correlation_schedule_id + correlation_expected_fire_at`
- `R6` -> `correlation_schedule_id + correlation_predicate_evaluated_at`

Missing correlation fields are a Chunk A defect even if the human-visible message was delivered.

### 9.9 Audit self-escalation and watchdog
When audit finds a missed escalation:
1. emit `autonomous_ops.missed_escalation_detected`
2. send Telegram directly, bypassing allAI
3. write a `P1` attention item sourced from `schedule:missed-escalation-audit-hourly`

Watchdog contract:
- audit emits `schedule.audit.heartbeat` on successful completion
- watchdog runs every 3 hours using Form A event-age predicate with `threshold_seconds=10800`
- if heartbeat is stale, watchdog sends Telegram directly and writes a `P0` attention item

## 10. Acceptance Criteria
### 10.1 A1 — Registry data model + CRUD
| AC ID | Criterion | Falsifiable test shape |
|---|---|---|
| `A1-AC1` | valid cron create persists canonical `schedule:*` entity with exact defaults including `run_environment` | API/integration test posts minimal valid cron schedule and asserts stored fields/defaults/version |
| `A1-AC2` | invalid field combinations are rejected deterministically | validation matrix covers bad cron, missing cadence, `prod+council_request`, `dev+prod_agent`, bad dispatch-field combinations, and bad `allow_parallel` config |
| `A1-AC3` | patch/delete use optimistic locking | stale `expected_version` test asserts `409 schedule_version_conflict` |
| `A1-AC4` | manual trigger issues new UUIDv7 `run_id` without mutating immutable fields | trigger-twice API test compares IDs and entity invariants |

### 10.2 A2 — Executor + substrate + startup assertion
| AC ID | Criterion | Falsifiable test shape |
|---|---|---|
| `A2-AC1` | APScheduler imports exist only in adapter | grep/lint test fails if `apscheduler` import appears elsewhere |
| `A2-AC2` | startup fails on unmatched recurring-work site | integration test injects unmatched loop/beat key and asserts fatal bootstrap error naming file/line |
| `A2-AC3` | production executor boots only on Railway and asserts the expected startup fingerprint | production-bootstrap test injects missing/non-Railway fingerprint and asserts fatal refusal |
| `A2-AC4` | migrated internal schedules seed/register, GH external schedules seed but do not register internally | bootstrap test inspects seed set and live registration set |
| `A2-AC5` | reconciler repairs registration drift within 1 minute | test removes registration and asserts reconciler restores it |

### 10.3 A3 — Predicate engine + dispatch envelopes
| AC ID | Criterion | Falsifiable test shape |
|---|---|---|
| `A3-AC1` | all ten comparators behave correctly and fail safely on type mismatch | unit matrix across valid/invalid fixtures |
| `A3-AC2` | every evaluation emits `schedule.predicate.evaluated` with cost and match metadata | event-ledger integration test per cadence run |
| `A3-AC3` | `(run_id, attempt_number)` idempotency prevents double-counting and handles late duplicates | replay duplicate and mismatched payloads through result handlers |
| `A3-AC4` | `prod_agent` envelopes contain the required request contract and never accept `run_environment=dev` | schema and router validation tests on outbound production-dispatch payloads |
| `A3-AC5` | prod-agent completion webhook authenticates, deduplicates, and writes the sole completion event | webhook integration tests cover raw-body `X-Dispatch-Signature` HMAC validation, missing-header `400`, invalid-signature `401` with `webhook.auth.reject`, duplicate callback replay, and previous-secret rotation acceptance |
| `A3-AC6` | envelopes/results contain required UUIDv7 and correlation fields by trigger type | schema contract tests on cron, predicate, manual, prod-agent, and external-webhook paths |

### 10.4 A4 — allAI subscription
| AC ID | Criterion | Falsifiable test shape |
|---|---|---|
| `A4-AC1` | `AllAIBrainAgent` subscribes only to `schedule.run.complete` and runs only on Railway in production | startup/subscription registry test plus production-host assertion |
| `A4-AC2` | queue overflow spills to Redis and drains back without losing correlation metadata | stress test with >100 events |
| `A4-AC3` | degraded mode activates when rolling p95 exceeds 5s and switches to safe-default routing | latency simulation with route assertions |
| `A4-AC4` | split threshold emits carve trigger | 7-day ingress simulation with artifact assertion |

### 10.5 A5 — Attention queue + missed-escalation audit
| AC ID | Criterion | Falsifiable test shape |
|---|---|---|
| `A5-AC1` | `queue:attention` stores required fields and resolves via optimistic locking | entity/API write+resolve test |
| `A5-AC2` | audit rules R1-R6 derive candidates from raw events without reading the queue | rule-engine test with queue access guarded/mocked |
| `A5-AC3` | Telegram verification uses rule-specific correlation keys | per-rule match/no-match tests |
| `A5-AC4` | watchdog fires within 3 hours when audit heartbeat is missing | time-advance integration test asserting direct Telegram send and P0 queue item |

## 11. Gate 3 Verification Contract
### 11.1 A1 evidence mapping
Tests:
- schema validation suite
- CRUD API integration suite
- optimistic-lock conflict tests
- manual-trigger tests

Artifacts:
- committed `schedule.schema.json`
- output showing defaults applied and invalid combinations rejected
- output or log line showing `schedule_version_conflict`

### 11.2 A2 evidence mapping
Tests:
- import-boundary grep/lint
- startup manifest assertion tests
- Railway production-host fingerprint assertion tests
- seed + registration integration tests
- reconciler drift-repair test

Artifacts:
- committed `backend/config/migration-manifest.yaml`
- commit deleting live Celery Beat keys from `backend/app/core/celery_app.py`
- bootstrap logs proving manifest assertion success
- bootstrap logs proving the Railway-hosted startup fingerprint was asserted for production executor startup
- logs/tests proving GH external schedules are tracked but not internally scheduled

### 11.3 A3 evidence mapping
Tests:
- comparator unit suite
- predicate evaluation event tests
- envelope/result schema tests
- duplicate-result idempotency tests
- prod-agent webhook auth/idempotency tests

Artifacts:
- committed `dispatch-envelope.schema.json` and `run-result.schema.json`
- output proving duplicate completion is idempotent
- logs showing UUIDv7 `run_id` and correlation fields for cron, predicate-triggered, and prod-agent runs
- test output proving `run_environment=prod` rejects `dispatch_mode=council_request`
- test/log output proving `X-Dispatch-Signature: sha256=<hexdigest>` raw-body verification, `webhook.auth.reject` on invalid signatures, `400` on missing signature header, and `webhook.auth.accept validated_secret=previous` during rotation overlap

### 11.4 A4 evidence mapping
Tests:
- subscription registry test
- queue spillover/drain test
- degraded-mode enter/exit tests
- split-threshold trigger test

Artifacts:
- code diff in `AllAIBrainAgent`
- production assertion logs showing Railway as the allAI host
- logs/metrics for degraded-mode transitions
- output showing spillover preserved `correlation_*` fields
- artifact/event proving split-BQ filing signal

### 11.5 A5 evidence mapping
Tests:
- attention queue entity/API tests
- audit rule suite covering R1-R6
- Telegram correlation verification tests
- watchdog heartbeat absence test

Artifacts:
- committed `attention-queue.schema.json`
- code diff for audit service and watchdog seeds
- log/event showing `autonomous_ops.missed_escalation_detected`
- Telegram payload examples containing required `correlation_*` fields

## 12. Required Seed Inventory
### 12.1 Internal schedules
- `schedule:backend-sysadmin-health-check-5m`
- `schedule:backend-backup-verify-daily`
- `schedule:backend-celery-worker-heartbeat`
- `schedule:backend-gmail-polling`
- `schedule:backend-incident-sweeper-5m`
- `schedule:crm-steward-daily-maintenance`
- `schedule:backend-sysadmin-monitor-<name>` per migrated monitor
- `schedule:attention-queue-purge-resolved`
- `schedule:missed-escalation-audit-hourly`
- `schedule:missed-escalation-audit-watchdog`

### 12.2 External schedules
- `schedule:gh-smoke-test`
- `schedule:gh-backup-daily`
- `schedule:gh-backup-verify-ci-daily`
- `schedule:gh-health-check-daily`
- `schedule:gh-quarantine-weekly`
- `schedule:gh-runbook-harness-daily`

### 12.3 Seed ownership
Seed-owned fields:
- `summary`
- `description`
- `trigger_type`
- `dispatch_mode`
- `run_id_authority`
- `gh_workflow_path` for external schedules

User-editable after seed:
- `enabled`
- `paused_until`
- `priority`
- `escalation_target`
- `timeout_seconds`
- approved prompt/callable metadata where operationally safe

## 13. Review Focus and Risks
High-signal review targets:
- A1 semantic validation completeness
- A2 manifest false negatives and migration completeness
- A3 retry/counter semantics for duplicates and late results
- A4 safe-default degraded routing
- A5 correlation-field completeness across Telegram and batch paths

Primary implementation risks:
- missing a legacy recurring loop and violating the sole-API invariant
- allowing runtime auto-managed updates to clobber user control-field edits
- leaking APScheduler usage outside the adapter boundary
- losing `correlation_*` metadata in spillover or batch-flush paths
- under-testing late duplicate behavior for GH external results

## 14. Open Questions for Downstream Reviewers
- Should list/read run-history endpoints ship fully in Chunk A before Chunk B consumes them, or is a minimal internal-only read surface acceptable? Current proposal: ship them now so Gate 3 proves the backend contract before frontend dependency begins.
- For `serial_queue`, should v1 allow more than one pending logical fire when repeated intervals are missed within grace, or is a single queued pending fire the right simplification? Current proposal: a single pending queued fire.
- Is there an existing backend metrics primitive preferred for rolling p95 windows, or must A4 implement a local estimator? Current proposal: reuse an existing metrics primitive if present; otherwise implement locally.
- For GH external schedules, should a missing `run-start` be treated as error or warning when `run-result` arrives first? Current proposal: warning only; permit implicit creation for robustness.
- Should protected/core seed schedules be undeletable at the API layer, or deletable only behind a stricter internal admin flag? Current proposal: internal admin flag only, to preserve an emergency escape hatch without DB surgery.
- Do any current Telegram wrappers strip unknown body fields and thereby threaten the required `correlation_*` contract? Reviewers should challenge this explicitly because A5 depends on those fields surviving intact.

## Appendix G — R1 to R2 Closure Map
| R1 finding | R2 closure section |
|---|---|
| Titan-1 production executor host ambiguity | `§6.2a Production hosting contract`, `§11.2` |
| Production dispatch path still used `council_request` | `§5.5`, `§5.6`, `§6.8`, `§7.5`, `§7.7`, `§11.3` |
| Backup topology still implied Titan-1 substrate ownership | `§2.1`, `§6.6.2` |
| Dispatch host matrix missing | `§6.8 Dispatch Host Matrix` |
| allAI host placement not explicit | `§8.1`, `§11.4` |
| UUID version inconsistency vs parent amendment | `§3.2` |
| Migration env-var retirement table missing | `§6.6.1` |

## Appendix H — R2 to R3 Closure Map
| R2 finding | R3 closure section |
|---|---|
| N1 request-side envelope cleaned, worked example aligned, parent dispatch/result split re-asserted | `§7.5`, `§7.6` |
| N2 webhook HMAC-SHA256 contract, rotation support, verifier behavior, and Gate 3 evidence defined | `§7.7`, `§10.3`, `§11.3` |
