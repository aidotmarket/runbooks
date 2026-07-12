---
system_name: qdrant-sync-outbox
purpose_sentence: The Qdrant sync outbox moves canonical allAI state/event changes from Postgres into Qdrant using a claimed, batched consumer.
owner_agent: sysadmin
escalation_contact: Max (human operator)
lifecycle_ref: §J
authoritative_scope: Producer/consumer operation for public.qdrant_sync_outbox, freshness alarms, integrity reconciliation, DLQ drain, concurrency escalation, Max-gated dedup, and the S1194 cutover procedure. NOT Qdrant service hosting or API-key rotation; see qdrant.md.
linter_version: 1.0.0
---

# Qdrant Sync Outbox

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Entity producer coalescing | SHIPPED | `app/services/state_service.py:StateService._enqueue_outbox` | `tests/test_qdrant_producer_coalescing_s1194.py` | 2026-07-12 |
| Claimed batch consumer | SHIPPED | `app/services/qdrant_sync_worker.py` | `tests/test_qdrant_sync_worker_s1194.py` | 2026-07-12 |
| Freshness alarms | SHIPPED | `app/allai/agents/sysadmin/monitors.py` | `tests/test_qdrant_sync_alarm_s1194.py`, `tests/test_sysadmin_qdrant_monitoring_s1194.py` | 2026-07-12 |
| Integrity reconciler | SHIPPED | `app/allai/agents/sysadmin/monitors.py:qdrant_index_integrity_status` | `tests/test_sysadmin_qdrant_monitoring_s1194.py` | 2026-07-12 |
| DLQ drain | SHIPPED | `app/services/qdrant_sync_worker.py:requeue_dead_letters`, `scripts/drain_embedding_dlq.py` | internal admin route plus script tests | 2026-07-12 |
| S1194 dedup | SHIPPED | `scripts/s1194_dedup_qdrant_pending_entities.py` | `tests/test_qdrant_producer_coalescing_s1194.py` | 2026-07-12 |
| Cutover | PLANNED | future `scripts/s1194_qdrant_cutover.py` | not implemented in P1 | 2026-07-12 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Entity producer | `app/services/state_service.py:StateService._enqueue_outbox` | `state_entities`, `qdrant_sync_outbox` | FastAPI/allAI state writers | Coalesces pending entity notifications with update-then-insert SQL and no unique-index dependency; rare duplicate pending rows are tolerated and collapsed by the producer on a later write. |
| Event producer | `app/services/state_service.py:StateService.record_event` | `state_events`, `qdrant_sync_outbox` | allAI event writers | P1 keeps event `embed_text`; P2 owns admission/quarantine. |
| Consumer | `app/services/qdrant_sync_worker.py:start_qdrant_sync_worker` | `qdrant_sync_outbox`, `state_entities`, `state_events` | Vertex Gemini `embed_batch`, Qdrant `knowledge_base_v2` | Claims rows with `FOR UPDATE SKIP LOCKED`, commits, then embeds/upserts. |
| Freshness monitors | `app/allai/agents/sysadmin/monitors.py` | `state_entities`, `state_events` | SysAdmin escalation pipeline | Measures stale canonical rows, not Qdrant as source of truth. |
| Integrity monitor | `app/allai/agents/sysadmin/monitors.py:qdrant_index_integrity_status` | `state_entities`, Qdrant payloads | Qdrant REST | Verifies point existence and `source_version`; legacy unknown rows are degraded, not green. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| SysAdmin | Inspect freshness lag | Internal capability `entity_memory_freshness_lag_seconds`, SQL in §E-01 | read-only backend DB | COMPLETE |
| SysAdmin | Drain DLQ | `POST /api/v1/internal/admin/qdrant/requeue-dead-letters` or `requeue_dead_letters()` | internal admin API | COMPLETE |
| SysAdmin | Raise `EMBED_CONCURRENCY` | Railway env var edit on backend service | Railway backend deploy scope | COMPLETE |
| SysAdmin | Run integrity check | `qdrant_index_integrity_status()` | DB read plus Qdrant API key | COMPLETE |
| SysAdmin | Stop/start consumer | Railway env/deploy controls or app startup/shutdown hooks | backend deploy scope | PARTIAL - no standalone worker service yet |
| Vulcan/Max | Run optional dedup | `scripts/s1194_dedup_qdrant_pending_entities.py` | production DB write with explicit Max GO | COMPLETE, optional Max-gated maintenance |

## §E. Operate - Serving Customers

Production deploy sequence for S1194 P1: merge the feature branch, deploy the backend, let Alembic run the online migration at container start, and let the new claimed consumer start draining. The migration adds only nullable/defaulted columns and no CHECK/NOT NULL constraint, so old containers can continue writing `qdrant_sync_outbox` rows during Railway rolling deploy overlap. The S1194 pending-entity dedup script is optional afterwards; it is Max-gated maintenance to accelerate backlog catch-up, not a deploy prerequisite.

```yaml operate
- id: E-01
  trigger: Check entity freshness lag during incident triage
  pre_conditions:
    - read-only database access or SysAdmin capability access
  tool_or_endpoint: entity_memory_freshness_lag_seconds_status(session_factory=AsyncSessionLocal)
  argument_sourcing:
    session_factory: backend default AsyncSessionLocal
  idempotency: IDEMPOTENT
  expected_success:
    shape: status object with lag_seconds, severity, condition_status
    verification: lag below QDRANT_ENTITY_FRESHNESS_WARN_SECONDS or owned incident note
  expected_failures:
    - signature: stale/critical lag
      cause: consumer stopped, backlog too large, stale claims, Vertex/Qdrant failure
  next_step_success: done
  next_step_failure: §F F-01
- id: E-02
  trigger: Drain dead-letter rows after fixing the root cause
  pre_conditions:
    - root cause fixed or explicitly understood
    - operator has internal admin authorization
  tool_or_endpoint: POST /api/v1/internal/admin/qdrant/requeue-dead-letters
  argument_sourcing:
    item_ids: optional list from `SELECT id FROM qdrant_sync_outbox WHERE status='dead_letter'`
  idempotency: IDEMPOTENT
  expected_success:
    shape: requeued_count and item_ids
    verification: dead_letter count decreases; freshness lag begins falling
  expected_failures:
    - signature: rows return to dead_letter
      cause: unfixed Vertex/Qdrant/application error
  next_step_success: E-01
  next_step_failure: §F F-03
- id: E-03
  trigger: Temporarily raise consumer throughput
  pre_conditions:
    - backlog is growing
    - Vertex/Qdrant error rate is healthy
    - Max or incident owner approves temporary concurrency increase
  tool_or_endpoint: Railway variable update `EMBED_CONCURRENCY=<n>` on ai-market-backend, then redeploy
  argument_sourcing:
    n: start at 2; raise further only with observed Qdrant/Vertex headroom
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: desired EMBED_CONCURRENCY value plus deploy SHA
  expected_success:
    shape: more local consumer loops, disjoint claims by SKIP LOCKED
    verification: backlog age and count decrease without DLQ growth
  expected_failures:
    - signature: 429/5xx from Vertex or Qdrant
      cause: external service saturation
  next_step_success: restore EMBED_CONCURRENCY=1 after drain
  next_step_failure: revert to EMBED_CONCURRENCY=1 and use §F F-03
- id: E-04
  trigger: Run the Qdrant integrity check manually
  pre_conditions:
    - QDRANT_API_KEY configured
    - backend DB reachable
  tool_or_endpoint: qdrant_index_integrity_status(session_factory=AsyncSessionLocal)
  argument_sourcing:
    sample_size: settings.QDRANT_INTEGRITY_SAMPLE_SIZE
  idempotency: IDEMPOTENT
  expected_success:
    shape: ok=true or degraded legacy evidence with counts
    verification: missing_count=0 and orphan_count within threshold
  expected_failures:
    - signature: missing_count or orphan_count above threshold
      cause: Qdrant point loss, stale payload, delete failure
  next_step_success: done
  next_step_failure: §F F-04
- id: E-05
  trigger: Stop/start the consumer during deploy or incident handling
  pre_conditions:
    - active incident owner
    - deployment plan written in ticket
  tool_or_endpoint: Railway stop/start or redeploy of ai-market-backend
  argument_sourcing:
    target_service: ai-market-backend production service
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: no new processing rows after stop; claims resume after start
    verification: `SELECT status, count(*) FROM qdrant_sync_outbox GROUP BY status`
  expected_failures:
    - signature: processing rows remain stale
      cause: worker killed mid-batch
  next_step_success: E-01
  next_step_failure: §G G-01
- id: E-06
  trigger: Optionally run S1194 pending entity dedup after deploy
  pre_conditions:
    - explicit Max GO
    - production deploy is complete
    - no active incident on qdrant_sync_outbox
  tool_or_endpoint: `.venv/bin/python scripts/s1194_dedup_qdrant_pending_entities.py --dry-run`, then without `--dry-run`
  argument_sourcing:
    DATABASE_URL: production database URL from backend runtime context
  idempotency: IDEMPOTENT
  expected_success:
    shape: before/after duplicate_targets and duplicate_rows; after duplicate_rows=0
    verification: duplicate query returns zero rows; queue head advances faster
  expected_failures:
    - signature: duplicate_rows remains nonzero
      cause: live producer race or batch failed
  next_step_success: done
  next_step_failure: wait and retry only with Max GO; deploy is not blocked
```

## §F. Isolate - Diagnosing Deviations

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Backlog grows or freshness lag rises | consumer stopped, empty-loop sleep only, external failure, old code deployed | `SELECT status,target_type,count(*),min(created_at) FROM qdrant_sync_outbox GROUP BY status,target_type` plus SysAdmin freshness status | §G G-04 | CONFIRMED |
| F-02 | Rows stuck in `processing` | worker killed after claim before ack | `SELECT id,claimed_at,claimed_by FROM qdrant_sync_outbox WHERE status='processing' ORDER BY claimed_at LIMIT 20` | §G G-01 | CONFIRMED |
| F-03 | DLQ grows | repeated Vertex/Qdrant failures, invalid event payload, bug in canonical entity read | `SELECT id,target_type,target_id,last_error FROM qdrant_sync_outbox WHERE status='dead_letter' ORDER BY processed_at DESC LIMIT 20` | §G G-02 | CONFIRMED |
| F-04 | Integrity check reports missing points | Qdrant data loss, failed upsert not retried, payload version mismatch | run E-04 and inspect missing sample | §G G-03 | CONFIRMED |
| F-05 | Event freshness stays `pre_admission` | P2 event admission has not shipped | read event monitor evidence; `indexing_disposition` still NULL |  | CONFIRMED |
| F-06 | Alarm is silent while consumer is disabled | monitor registration, scheduler, or escalation pipeline failure | check scheduler has `qdrant_memory_freshness_monitors`; run E-01 manually | §G G-05 | HYPOTHESIZED |

## §G. Repair - Fixing Problems

```yaml repair
- id: G-01
  symptom_ref: F-02
  component_ref: Consumer
  root_cause: processing claim exceeded QDRANT_CLAIM_STALE_AFTER_SECONDS
  repair_entry_point: app/services/qdrant_sync_worker.py:reap_stale_claims
  change_pattern: let the reaper return stale processing rows to pending with exponential next_attempt_at backoff
  rollback_procedure: manually reset rows only if reaper is broken: UPDATE qdrant_sync_outbox SET status='pending', claimed_at=NULL, claimed_by=NULL WHERE status='processing'
  integrity_check: processing count reaches zero; replay writes qdrant_indexed_version matching state_entities.version
- id: G-02
  symptom_ref: F-03
  component_ref: Consumer
  root_cause: dead-lettered rows exhausted max_attempts
  repair_entry_point: app/services/qdrant_sync_worker.py:requeue_dead_letters
  change_pattern: fix root cause, then requeue selected IDs or all DLQ rows
  rollback_procedure: stop requeue if last_error repeats; keep remaining dead_letter rows for inspection
  integrity_check: DLQ count falls; freshness lag falls; no repeated last_error
- id: G-03
  symptom_ref: F-04
  component_ref: Integrity monitor
  root_cause: Qdrant point missing or stale relative to Postgres
  repair_entry_point: future scripts/s1194_qdrant_cutover.py or targeted outbox enqueue
  change_pattern: enqueue canonical entity upserts/deletes from Postgres, then let P1 consumer write payload source_version
  rollback_procedure: stop consumer; do not restore stale outbox rows as source of truth
  integrity_check: E-04 returns missing_count=0 and orphan_count within threshold
- id: G-04
  symptom_ref: F-01
  component_ref: Consumer
  root_cause: consumer throughput below enqueue rate
  repair_entry_point: app/services/qdrant_sync_worker.py:start_qdrant_sync_worker
  change_pattern: raise EMBED_CONCURRENCY temporarily, confirm batched claims/upserts are healthy, lower after drain
  rollback_procedure: set EMBED_CONCURRENCY=1 and redeploy
  integrity_check: backlog count and oldest age decrease without DLQ growth
- id: G-05
  symptom_ref: F-06
  component_ref: Freshness monitors
  root_cause: monitor/scheduler/escalation registration broken
  repair_entry_point: app/core/scheduler.py:start_scheduler and app/allai/agents/sysadmin/agent.py
  change_pattern: restore qdrant monitor job registration and SysAdmin escalation policy
  rollback_procedure: manual incident page to Max while code fix deploys
  integrity_check: disabling consumer for the test window produces a non-green freshness status and escalation
```

## §H. Evolve - Extending the System

### §H.1 Invariants

- Postgres is canonical. Entity embeddings are built from the current `state_entities.kind/key/summary/body`, not from stale entity `embed_text`.
- No silent exclusion. A row may stop contributing to freshness only through a shipped, monitored admission decision; P2 owns that.
- Batch first. Upserts should use `embed_batch()` and batched Qdrant writes unless a documented external limit forces smaller batches.
- Claims must commit before any Vertex or Qdrant call.
- Entity/event work is split by existing `target_type`; do not add a second routing column that old producers must populate during rolling deploy overlap.
- Outbox `done`/`failed` transitions must be conditional on `status='processing'` and the same `claimed_by` worker that claimed the row.
- Entity producer coalescing must not depend on a unique constraint. It updates one pending survivor, marks duplicate pending losers superseded on a successful coalesce, and inserts only when no pending row exists.
- Pending delete rows win over pending upsert rows for the same entity target. Otherwise the survivor is the highest `source_version`, tie-broken by `created_at DESC, id DESC`.
- Rare duplicate pending rows are tolerated by design: they can cause at most redundant canonical re-reads/embeds, and guarded version acks prevent stale Qdrant freshness from being recorded.

### §H.2 Change-class predicate tree

BREAKING if any change reintroduces a required partial unique index or writer pause for P1 deploy, trusts entity `embed_text` for version ack, drops `qdrant_indexed_version`, weakens claimed-worker ack/fail guards, changes `source_version` payload semantics, or disables the freshness alarm.

REVIEW if any change changes config defaults (`EMBED_BATCH_SIZE`, `EMBED_CONCURRENCY`, `QDRANT_CLAIM_STALE_AFTER_SECONDS`), adds event admission/quarantine, adds retention, or changes the cutover flow.

SAFE if the change is a focused bugfix preserving the invariants above, adds test coverage, or updates this runbook without changing runtime behavior.

### §H.3 Boundary definitions

`module`: backend source modules are `app/services`, `app/core`, `app/allai`, `app/models`; migrations and scripts are peer trees.

`public contract`: internal admin API shape, environment variable names, Alembic schema contract, and Qdrant payload keys `target_type`, `target_id`, `source_version`, `indexed_at`.

`runtime dependency`: Postgres, Vertex Gemini embeddings, Qdrant, Railway runtime, SysAdmin scheduler.

`config default`: `EMBED_BATCH_SIZE=50`, `EMBED_CONCURRENCY=1`, `QDRANT_SYNC_EMPTY_POLL_INTERVAL_SECONDS=5`, `QDRANT_CLAIM_STALE_AFTER_SECONDS=900`.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [§E E-01]
    scenario: Check lag during a live incident.
    expected_answers: [{kind: tool_call, tool: entity_memory_freshness_lag_seconds_status, argument_keys: [session_factory]}]
    weight: 0.1
  - id: I-02
    type: operate
    refs: [§E E-02]
    scenario: Requeue DLQ rows after fixing a Vertex auth error.
    expected_answers: [{kind: tool_call, tool: requeue_dead_letters, argument_keys: [item_ids]}]
    weight: 0.1
  - id: I-03
    type: operate
    refs: [§E E-03]
    scenario: Raise throughput without changing worker code.
    expected_answers: [{kind: human_instruction, action: set EMBED_CONCURRENCY and redeploy}]
    weight: 0.1
  - id: I-04
    type: isolate
    refs: [§F F-02]
    scenario: Rows are stuck processing after a deploy restart.
    expected_answers: [{kind: sql, query_contains: [status='processing', claimed_at]}]
    weight: 0.1
  - id: I-05
    type: isolate
    refs: [§F F-03]
    scenario: Dead-letter count increases.
    expected_answers: [{kind: sql, query_contains: [dead_letter, last_error]}]
    weight: 0.1
  - id: I-06
    type: isolate
    refs: [§F F-05]
    scenario: Event freshness is unknown before P2.
    expected_answers: [{kind: classification, verdict: pre_admission}]
    weight: 0.1
  - id: I-07
    type: repair
    refs: [§G G-01]
    scenario: Recover stale processing claims.
    expected_answers: [{kind: tool_call, tool: reap_stale_claims, argument_keys: []}]
    weight: 0.1
  - id: I-08
    type: repair
    refs: [§G G-04]
    scenario: Backlog grows but Vertex and Qdrant are healthy.
    expected_answers: [{kind: human_instruction, action: raise EMBED_CONCURRENCY temporarily}]
    weight: 0.1
  - id: I-09
    type: evolve
    refs: [§H]
    scenario: Propose requiring uq_qdrant_outbox_pending_entity and a writer pause for P1 deploy.
    expected_answers: [{kind: classification, verdict: BREAKING}]
    weight: 0.1
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: Add a unit test for M7 zero-row ack re-enqueue.
    expected_answers: [{kind: classification, verdict: SAFE}]
    weight: 0.1
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: BQ-QDRANT-OUTBOX-THROUGHPUT-RETENTION-S1194-P1
last_refresh_commit: pending
last_refresh_date: 2026-07-12T19:53:25Z
owner_agent: sysadmin
refresh_cadence: after each S1194 phase or any production incident touching qdrant_sync_outbox
grace_until: 2026-10-10T00:00:00Z
```

## §K. Linter / Compliance Metadata

```yaml compliance
linter_version: 1.0.0
standard_ref: specs/BQ-RUNBOOK-STANDARD.md
sections_present: [A, B, C, D, E, F, G, H, I, J, K]
agent_forms:
  B: capability_matrix
  C: architecture_table
  D: agent_capability_map
  E: operate_yaml
  F: symptom_index
  G: repair_yaml
  H: predicate_tree
  I: scenario_set
  J: lifecycle_metadata
router_registration: TOPIC-ROUTER.md
```
