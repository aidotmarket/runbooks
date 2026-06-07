---
system_name: build-queue-lifecycle
purpose_sentence: Living State is the canonical store of all development-work state, surfaced at ops.ai.market/build-queue, tracking every item from filed through to live-in-production with ledgered transitions, stale-item escalation, and a Council-adjudicated cleanup path.
owner_agent: vulcan
escalation_contact: max@ai.market
lifecycle_ref: §J
authoritative_scope: Living State lifecycle fields, the atomic mutate-plus-event write path, the soft-freeze and cleanup-token config entities, and the build-queue dashboard read proxy. Explicitly OUT of scope are the legacy build_queue/build_queue_history tables, retired in early May.
linter_version: 1.0.0
---

# Build-Queue Lifecycle Management

## §A. Header

YAML frontmatter above is authoritative for the §A header fields. Living State is the single canonical store; the dashboard at ops.ai.market/build-queue is a read projection; git holds code and spec file content only. The legacy backend build_queue and build_queue_history tables were dropped (migration 20260507_001_drop_bq_legacy) and must never be reintroduced.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Lifecycle stages incl. Live-in-Production as canonical exit | LIVE | tools/state.py `_validate_lifecycle_transition` | test_bq_create_completion_blocked.py | 2026-05 (S577) |
| Single write path: all 5 handlers route through shared helper | LIVE | tools/state.py `_persist_with_lifecycle_invariants` | test_handlers_route_through_persistence_helper.py | 2026-05 (S566) |
| Mandatory canonical Event Ledger entry per lifecycle write | LIVE | tools/state.py `_emit_canonical_event_atomic` | test_event_emission_atomicity.py | 2026-05 (S568) |
| Atomic mutate-plus-event (DB-level, single commit) | LIVE | POST /api/v1/allai/state/atomic_write (ai-market-backend) | backend atomic_write suite | 2026-05 (S568) |
| Completion-evidence gate (no completed without evidence) | LIVE | tools/state.py `_validate_lifecycle_transition` | test_bq_create_completion_blocked.py | 2026-05 (S566) |
| Soft-freeze on lifecycle writes (reads + affirm always allowed) | LIVE | config:build-queue-freeze | covered in chunk 1.5 suite | 2026-05 (S568) |
| Cleanup-token lifecycle (issue / atomic-consume / revoke) | LIVE | tools/state.py `verify_and_consume_token`; config:build-queue-tokens | chunk 1.5 token suite | 2026-05 (S568) |
| Stale-item escalation 3/7/14 sessions | LIVE | lifecycle_eligibility_handler; session-open standup | boot standup aging_obligations | 2026-06 (S792) |
| Per-item drift reconciliation | LIVE | lifecycle_eligibility_handler | reconciliation job suite | 2026-06 (S792) |
| Legacy build_queue table retirement | LIVE | migration 20260507_001_drop_bq_legacy | archive verified 106 items/465 rows | 2026-05 (S577) |
| Plain-English summary + work-type backfill | PARTIAL | bulk patch pass (Max pre-approved) | n/a (data backfill) | ~80 items pending |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Living State write path | `state_request` (koskadeux-mcp) | Railway Postgres via ai-market-backend `/api/v1/allai/state` | dashboard proxy, morning briefing, reconciler | All mutations route through `_persist_with_lifecycle_invariants`; never write the DB directly |
| Atomic write endpoint | POST `/api/v1/allai/state/atomic_write` | same | token consumption, event ledger | Single AsyncSession, flush-only services, one commit; SELECT FOR UPDATE on singleton tokens entity |
| Dashboard read proxy | ops.ai.market/build-queue | Living State (read) | Max | Read projection only; if a panel is wrong, the underlying entity is wrong |
| Reconciler | lifecycle_eligibility_handler (scheduled) | Living State | session-open standup | Auto-recomputes eligibility + drift; emits drift report into the boot standup |
| Morning briefing | APScheduler `app/core/scheduler.py` | Living State | max@ai.market | Surfaces the >14-session escalation row (AC5.1) |

**Lifecycle transition triggers (AC1.9).** Transitions are explicit, never inferred from CI/deploy/webhook signals:

| From | To | Trigger | Guard |
|---|---|---|---|
| (none) | filed/in_progress | `state_request put` with work-type tag | work_type required; triage flag if ambiguous |
| in_progress | live_in_production | explicit transition with typed verification evidence | completion-evidence gate; evidence shape per work-type |
| any active | cancelled | cancel with ledgered reason | reason required |
| any | (priority change) | drag-reorder writes priority, actor=max | ledgered event; activity-only touch |
| no movement 3/7/14 sessions | yellow/red/briefing-escalation | reconciler on `last_affirmed_at` age | affirm resets the clock |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan / Mars | file / patch / transition / complete / cancel | `state_request` (put/patch/bq_update/bq_complete/bq_bulk_update) | full write via persistence helper | LIVE |
| Vulcan / Mars | run cleanup adjudication pre-flight | Chunk-4 cleanup manifest (see §F) | token-scoped | LIVE |
| Reconciler | recompute eligibility + drift | lifecycle_eligibility_handler | system | LIVE |
| Dispatch wrapper | reject dispatches lacking a valid active build-queue reference | dispatch enforcement gate | system | see §H.1 |
| Max | priority reorder, batch cleanup sign-off | dashboard | actor=max ledgered | LIVE |

## §E. Operate

```yaml operate
- id: transition-to-live
  trigger: built code is deployed and in active use
  pre_conditions:
    - item is in_progress
    - typed verification evidence is available for the item's work-type
  tool_or_endpoint: state_request bq_complete (gate >= 4) OR bq_update with evidence
  argument_sourcing:
    arg: bq_code from the entity; verification text describing what was confirmed live
  idempotency: re-completing an already-live item is a no-op
  expected_success:
    shape: entity status -> completed; canonical lifecycle event emitted
    verification: GET the entity; confirm status + event ledger entry
  expected_failures:
    - signature: completion_evidence_required
      cause: attempted completed transition without evidence
  next_step_success: confirm dashboard reflects live-in-production
  next_step_failure: supply typed evidence per work-type, retry
- id: batch-cleanup-signoff
  trigger: Chunk-4 cleanup pre-flight produced a draft manifest awaiting Max sign-off
  pre_conditions:
    - cleanup manifest exists (see §F)
    - a valid active cleanup token issued
  tool_or_endpoint: POST /api/v1/allai/state/atomic_write with token
  argument_sourcing:
    arg: manifest id; token from config:build-queue-tokens
  idempotency: token is single-use (atomic CAS active->used); replay rejected
  expected_success:
    shape: adjudicated items transitioned in one transaction; token consumed
    verification: token state == used; entities reflect manifest
  expected_failures:
    - signature: token_not_active
      cause: token already consumed or revoked
  next_step_success: confirm manifest applied
  next_step_failure: re-issue a fresh token, re-run sign-off
```

## §F. Isolate

Cleanup adjudication is a **Chunk-4 pre-flight** activity that produces a draft cleanup manifest plus a reconciliation report. **Chunk 5 (this runbook) does NOT execute cleanup adjudication** — operators must reference the most recent Chunk-4 cleanup manifest rather than re-running adjudication from this surface (AC5.2). The manifest is the authoritative record of what was proposed and signed off.

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F1 | Dashboard active count != morning briefing count | stale entity; drift not reconciled | compare total_active_count vs briefing; check reconciler last run | G1 | HIGH |
| F2 | Stale item not escalating | last_affirmed_at being touched by non-affirm writes | confirm activity vs affirm split; check reconciler | G2 | MED |
| F3 | Item shows completed but never deployed | completion-evidence gate bypassed via raw write | inspect event ledger for the transition + evidence | G3 | HIGH |
| F4 | Lifecycle write returns 409/423 freeze_active | soft-freeze window active | GET config:build-queue-freeze | G4 | HIGH |
| F5 | Cleanup sign-off rejected token_not_active | token already consumed/revoked or race | GET config:build-queue-tokens for token state | G5 | HIGH |
| F6 | Cleanup intent unclear / which items | reading stale manifest or none | locate latest Chunk-4 cleanup manifest (do NOT re-adjudicate here) | G6 | MED |

## §G. Repair

```yaml repair
- id: G1
  symptom_ref: F1
  component_ref: reconciler
  root_cause: per-item drift not yet reconciled into canonical count
  repair_entry_point: lifecycle_eligibility_handler
  change_pattern: trigger reconciliation; confirm drift report clears
  rollback_procedure: none (read-side recompute)
  integrity_check: total_active_count == briefing active count
- id: G3
  symptom_ref: F3
  component_ref: tools/state.py _validate_lifecycle_transition
  root_cause: a write path bypassed the persistence helper
  repair_entry_point: route the offending caller through _persist_with_lifecycle_invariants
  change_pattern: no direct session writes; all mutations via the shared helper
  rollback_procedure: revert offending caller change
  integrity_check: test_handlers_route_through_persistence_helper passes
- id: G5
  symptom_ref: F5
  component_ref: tools/state.py verify_and_consume_token
  root_cause: token already consumed (single-use) or revoked
  repair_entry_point: issue a fresh cleanup token in config:build-queue-tokens
  change_pattern: re-issue scoped token; re-run atomic sign-off
  rollback_procedure: revoke the new token if sign-off aborted
  integrity_check: token state transitions active->used exactly once
```

## §H. Evolve

### §H.1 Invariants

- Living State is the SOLE canonical store of development-work state. The legacy build_queue/build_queue_history tables are retired and must not be reintroduced.
- Every lifecycle mutation routes through `_persist_with_lifecycle_invariants`; no handler writes the DB directly.
- Every lifecycle mutation emits a canonical Event Ledger entry; if the caller omits event_payload, Living State auto-derives it.
- `status -> completed` requires typed verification evidence regardless of which action was used (`_validate_lifecycle_transition`).
- Transitions are explicit only; no automatic promotion to live from CI/deploy/webhook signals.
- Every dispatch through any council member or build path requires a valid active build-queue reference; dispatches without one are rejected and the rejection is logged.

### §H.2 BREAKING predicates

- Reintroducing a second canonical store for work state (e.g., resurrecting backend build_queue).
- Allowing a completed transition without evidence on any write path.
- Making the cleanup token reusable / non-atomic.

### §H.3 REVIEW predicates

- Adding a new lifecycle stage or work-type category (taxonomy is fixed at four for v1; expansion is config-only, Council REVIEW).
- Changing stale thresholds away from 3/7/14 sessions.
- Changing the atomic_write transaction boundary.

### §H.4 SAFE predicates

- Tuning stale thresholds within config (values are config, not hardcoded).
- Adding read-only dashboard panels or filters.
- Backfilling business_summary / work_type tags.

### §H.5 Boundary definitions

#### module

tools/state.py (koskadeux-mcp): `_persist_with_lifecycle_invariants`, `_validate_lifecycle_transition`, `_emit_canonical_event_atomic`, `verify_and_consume_token`.

#### public contract

`state_request` actions (put/patch/bq_update/bq_bulk_update/bq_complete); backend POST `/api/v1/allai/state/atomic_write`.

#### runtime dependency

ai-market-backend `/api/v1/allai/state` (Railway Postgres). koskadeux-mcp is an HTTP client of this API — if state ops 500, check the backend app's DB connectivity FIRST.

#### config default

config:build-queue-freeze (freeze inactive by default); config:build-queue-tokens (no active tokens by default).

### §H.6 Adjudication

**Cleanup token lifecycle (AC5.5).**
- **Issuance:** a cleanup token is created in `config:build-queue-tokens` in the `active` state, scoped to a specific cleanup operation/target (the Chunk-4 manifest it authorizes). Tokens are not general-purpose credentials.
- **Atomic CAS consumption:** `verify_and_consume_token()` performs an atomic compare-and-set from `active` -> `used` inside the SAME Living State transaction as the protected mutation, using SELECT FOR UPDATE on the singleton tokens entity. Two concurrent callers cannot both succeed — exactly one consumes the token; the other gets `token_not_active`.
- **Scoping:** a token authorizes only the operation it was issued for; it cannot be replayed against a different manifest or operation.
- **Revocation:** an unused token can be revoked (state -> revoked) before consumption; a revoked or already-used token fails the CAS and the protected operation does not run.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: AC5.2-manifest-reference
    type: isolate
    refs:
      - AC5.2
    scenario: An operator needs to know what the last cleanup proposed and applied.
    expected_answers:
      - kind: reference
        tool: chunk-4-cleanup-manifest
        argument_keys:
          - manifest_id
    weight: 1
  - id: AC5.5-token-atomicity
    type: evolve
    refs:
      - AC5.5
    scenario: Two callers attempt to consume the same cleanup token concurrently.
    expected_answers:
      - kind: invariant
        tool: verify_and_consume_token
        argument_keys:
          - token_id
    weight: 1
  - id: completion-evidence
    type: operate
    refs:
      - AC1.10
    scenario: A caller attempts to mark an item completed without evidence.
    expected_answers:
      - kind: rejection
        tool: state_request
        argument_keys:
          - bq_code
    weight: 1
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S792
last_refresh_commit: PENDING_COMMIT
last_refresh_date: "2026-06-07"
owner_agent: vulcan
refresh_triggers:
  - change to the lifecycle transition model or stage set
  - change to the atomic_write boundary or token mechanics
  - change to stale-escalation thresholds
scheduled_cadence: on-change (no fixed cadence; event-driven)
last_harness_pass_rate: not_yet_run
last_harness_date: not_yet_run
first_staleness_detected_at: null
```

## §K. Conformance

Stale-item escalation (AC3.2–3.5) is enforced operationally: the reconciler flags no-movement at 3 sessions (yellow), 7 sessions (red), and 14 sessions (discrete morning-briefing escalation row, AC5.1). Affirming an item via explicit revalidation resets `last_affirmed_at`; ordinary activity (priority, comments) touches activity only and does NOT reset the staleness clock.

```yaml conformance
linter_version: 1.0.0
last_lint_run: not_yet_run
last_lint_result: structurally_complete_lint_pending_linter_date_field_defect_consistent_with_sibling_AK_runbooks
trace_matrix_path: specs/bq-build-queue-lifecycle-s544-gate2-v6.md
word_count_delta: new_file
```
