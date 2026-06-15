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


---

## Operator guide (procedures & recovery)

*Folded in from the former koskadeux-mcp operational runbook during the single-source consolidation (S866). The narrative below is the hands-on operator procedure; the §A–§K matrix above is the structured/linted reference for the same system. A later editorial pass can de-duplicate any overlap.*

### Overview

The build-queue dashboard at `ops.ai.market/build-queue` is the single, canonical view of every active and recently-closed build item in the Council of Models system. It replaces three formerly separate views — the legacy backend Postgres `build_queue_items` table, the ad-hoc allAI summary, and the morning standup ticker — with one unified surface. Every row on the dashboard reflects a `build:*` entity that lives in Living State on `koskadeux-mcp` (Titan-1). There is no second store and no parallel cache.

The dashboard exists because the prior split made it easy to mark something "done" in one place while it was still "in progress" somewhere else. The unified lifecycle removes that ambiguity: an item has exactly one stage at any moment, and every stage transition is recorded as a canonical Event Ledger entry written atomically with the mutation that caused it.

Two readers matter:

- **Vulcan** opens the dashboard at the start of every session as part of the morning briefing. Vulcan looks at the escalation row first (stale items, items needing affirmation) and then scans In Progress and In Review for anything blocked.
- **Max** uses the dashboard to set priority, confirm completions, and cancel work. The drag-reorder gesture and the Mark Complete drill-down are the two interactive surfaces; everything else is read-only from Max's seat.

If you are a builder agent (MP, AG, KD), you do not interact with the dashboard directly. You call `state_request` against Living State and the dashboard reflects your changes within one polling interval (30s).

---

### Five lifecycle stages

Every item is in exactly one of five stages. Movement is left-to-right except for cancellation, which can fire from any active stage.

| Stage | Meaning | Transition trigger | Who can advance |
|-------|---------|--------------------|-----------------|
| **Filed** | Item exists in Living State with `business_summary` filled, but no builder has picked it up yet. Equivalent to status `planned`. | `bq_create` action completes; default initial stage. | Vulcan (when filing from a Council session) or Max (manually). |
| **In Progress** | A builder agent is actively working. Status is `in_progress`. The dashboard shows the assignee (e.g. MP, AG, KD) and elapsed time since the transition. | `bq_update status=in_progress`. | Vulcan (when dispatching) or the builder agent itself. |
| **In Review** | The builder has finished and a reviewer (council member or Max) is evaluating. Status is `review` or `failed` pending re-dispatch. | `bq_update status=review`. | The builder agent on completion of work; Vulcan on review dispatch. |
| **Live in Production** | The work is shipped and observable in the production environment relevant to the work-type (see §C). Status is `completed`. **Evidence is required to enter this stage** — see §G of the spec and the centralized transition invariant validator (AC1.10). | `bq_update status=completed` with `evidence={evidence_summary, evidence_refs, actor}`. | Builder, reviewer, or Max — but only with evidence. |
| **Cancelled** | The work will not ship. Status is `cancelled` or `deferred`. The item remains in Living State and is searchable; it does not vanish. | `bq_update status=cancelled` (with reason) or `status=deferred`. | Max, Vulcan, or a council reviewer with explicit reason. |

The forward path is **Filed → In Progress → In Review → Live in Production**. Cancellation is a side-exit available from any of the first three. Once Live in Production is reached, the item is immutable except for affirmation timestamps; if the work needs revisiting, file a new BQ that references the prior one.

---

### Work-type taxonomy

Every item is tagged with one of four work-types. The work-type controls what "Live in Production" actually means and what evidence the completion gate looks for.

- **Backend.** Code that ships to `ai-market-backend` on Railway or to `koskadeux-mcp` on Titan-1. *Live in Production* means: deployed to the relevant environment, observable in logs, and a smoke check has run within the last hour. Evidence references typically point at deploy IDs, commit SHAs, and a smoke-check link.
- **Orchestration.** Council-protocol changes, dispatcher tweaks, MCP tool additions, prompt edits. *Live in Production* means: the change is loaded by the running Sentinel/dispatcher and a dispatch through the affected path has succeeded since the change. Evidence references typically point at a successful dispatch ID and the relevant config entity in Living State.
- **Spec-or-Doc.** Spec authoring, runbook writes, CORE.md updates, design notes. *Live in Production* means: merged to the canonical branch (usually `main`) and reachable from the index that humans browse (CORE.md, the specs directory, or the runbooks directory). Evidence references the merge commit SHA and the path the doc landed at.
- **Frontend.** UI work in `ai-market-frontend` or any operator dashboard. *Live in Production* means: deployed to `ops.ai.market` (or the relevant subdomain) and visually verified by Max or Vulcan. Evidence references the deploy URL, a screenshot or short description of the verified behavior, and the commit SHA.

The work-type is set at file time and rarely changes. If the work straddles categories, pick the dominant one — the evidence shape only needs to satisfy the dominant category.

---

### Stale-item escalation

The morning briefing carries an escalation row that surfaces items the lifecycle has forgotten about. Three thresholds drive it, all measured in **sessions** (not wall-clock days), so the alarm only fires on sessions that actually happened:

- **Yellow at 3 sessions.** An item has been in In Progress or In Review for 3 sessions without any state change and without an `affirm` action. The briefing prints a yellow bullet under "Stale items" with the item code, current stage, and the last actor who touched it. No action required, but worth a glance.
- **Red at 7 sessions.** Same condition, sustained to 7 sessions. The briefing prints a red bullet and the item floats to the top of the In Progress / In Review list on the dashboard. Vulcan should ask the assigned builder for a status update or reassign.
- **Escalation at 14 sessions.** The briefing prints a separate escalation row titled "Items needing affirmation" listing every item whose `last_affirmed_at` has not advanced in 14 sessions. This row exists per **AC5.1** of the locked Gate 2 spec and is the formal trigger for either explicit affirmation (Max or the assigned builder runs the `affirm` action, which updates `last_affirmed_at` without changing status) or for escalation to cancellation/deferral.

To clear a stale item from the escalation list:

1. Open the dashboard, find the item, click into it.
2. If the work is still active, click **Affirm** — this writes `last_affirmed_at = now()` and resets the stale clock.
3. If the work has actually shipped but no one marked it complete, use Mark Complete with evidence.
4. If the work is dead, cancel it with a one-line reason (see §F).

Never silence a stale alarm by editing the timestamp directly. The affirm action is ledgered; a manual edit is not.

---

### Drag-reorder priority

Max sets priority by dragging rows on the dashboard. The gesture maps to a `POST /api/v2/build-queue/reorder` call carrying an `ordered_items` array of `{code, version_stamp}` entries. The proxy forwards this to Living State as a single `bq_bulk_update` action, which performs an atomic compare-and-swap on every item's `version_stamp`.

Two consequences worth understanding:

- **Atomic batch.** Either the whole reorder lands or none of it does. If any single item's `version_stamp` has advanced since the dashboard last loaded (someone else changed priority, or the assigned builder logged a status change), the entire batch is rejected with a 409. The dashboard refreshes the list and asks Max to redo the gesture. This is intentional — partial reorders produce visually-confusing intermediate states.
- **Ledgered with actor.** The reorder produces a single canonical Event Ledger entry stamped with `actor=max` (or whoever is authenticated), the prior order, the new order, and the timestamp. This is how we audit "why did the queue look like this on Tuesday?".

To recover from an accidental reorder:

1. Open the Event Ledger view and find the most recent `bq_priority_reorder` event by `actor=max`.
2. The event payload contains the `prior_order` array. Copy it.
3. Drag the dashboard back to that order, or — for large reverts — call `bq_bulk_update` directly with the prior `ordered_items` and current `version_stamp` values.
4. The reversion writes its own ledger entry; the original mistake remains in the ledger as well, which is desired.

Do **not** try to "undo" by deleting the original event from the ledger. Events are append-only by design.

---

### Cancellation flow

Cancellation is for work that will definitely not ship in its current form. Deferral is for work that might still ship but is parked indefinitely. The mechanics are the same; the user-visible label differs.

The cancellation flow:

1. Open the item on the dashboard.
2. Click **Cancel** (or **Defer**). A modal asks for a one-line reason.
3. Submit. The dashboard issues `bq_update status=cancelled` (or `status=deferred`) with the reason in `evidence_summary` and the actor stamped automatically.
4. Living State writes the status change and a canonical Event Ledger entry (`bq_cancelled` or `bq_deferred`) atomically. The item now appears in the Cancelled tab; it is **not** removed from Living State.

A ledgered cancellation reason looks like:

```json
{
  "event_type": "bq_cancelled",
  "code": "BQ-EXAMPLE-S999",
  "actor": "max",
  "evidence_summary": "Superseded by BQ-EXAMPLE-V2-S1010; original approach abandoned after R2 review.",
  "ts": "2026-05-10T14:32:11Z",
  "prior_status": "in_progress"
}
```

Cancelled items remain searchable indefinitely. To find one:

- Filter the dashboard's Cancelled tab by code, work-type, or actor.
- Search the Event Ledger for `event_type=bq_cancelled` plus a substring of the code.
- Query Living State directly: `state_request action=search prefix=build:` then filter `body.status in (cancelled, deferred)`.

When in doubt between cancel and defer, prefer cancel. A deferred item that sits for months is harder to act on than a cancelled item that someone re-files fresh. The Chunk 4 cleanup manifest (see §G) used this same heuristic to dispose of the legacy backlog; this runbook does **not** trigger a new cleanup pass — it documents how the existing one works.

---

### Cleanup adjudication harness

Periodically the queue accumulates items that no one is moving and no one is actively cancelling. The cleanup adjudication harness is the bulk mechanism for clearing these out — built once in Chunk 1.5, executed once as the Chunk 4 pre-flight, and **not** re-run by Chunk 5.

The harness lives in `tools/cleanup_adjudication.py` and runs in three phases:

1. **Draft verdicts.** `draft_verdicts()` snapshots every item with `status in (planned, in_progress, review)` and `last_affirmed_at` older than the configured cleanup horizon. It produces a manifest with one draft verdict per item — typically `cancel`, `defer`, or `keep_active` — and captures each item's `current_version_stamp` so the later signoff can perform per-item CAS.
2. **Council review.** `dispatch_council_review()` sends the manifest to MP, AG, and DS in `mode=open_response`. Each reviewer flags items where they disagree with the draft verdict. The harness returns the disagreement set; Vulcan reconciles before going to Max.
3. **Max signoff.** `apply_max_signoff()` requires a Max-issued approval token. On invocation it auto-issues a `cleanup_adjudication_token` (see §I), then walks the manifest applying each verdict via `bq_update` with the per-item `expected_version` and the adjudication token attached. Items whose `version_stamp` has moved since the snapshot are skipped and reported back; the rest are mutated and ledgered.

Draft verdicts land at `config:cleanup-adjudication-runs/<run_id>` in Living State, with the resolved manifest archived alongside after signoff. The Chunk 4 cleanup pre-flight manifest is the canonical archive of what was disposed of during cutover; reference it by run_id when explaining the historical state of the queue.

While a cleanup adjudication run is active, soft-freeze (§H) is engaged to prevent racing writes from invalidating the snapshot.

---

### Soft-freeze mechanism

Soft-freeze is a writable boolean on `config:build-queue-freeze` that, when active, blocks lifecycle-affecting writes against `build:*` entities while still allowing reads and the `affirm` action.

What it blocks (returns `{error: freeze_active}`):

- `bq_create`
- `bq_update` for status, priority, sort_order changes
- `bq_bulk_update` (reorder)
- Cancel and defer transitions

What it allows (passes through normally):

- All reads (`state_request action=get`, `action=list`, `action=search`)
- The `affirm` action (updates `last_affirmed_at` only — does not change lifecycle state)
- Writes to non-`build:*` entities (out of soft-freeze scope)

Soft-freeze engages automatically during cleanup adjudication runs (§G) and can be engaged manually for cutover windows or incident response. To override soft-freeze for a single emergency operation, mint a `freeze_lift_operation` token from Max's seat (see §I). The token is single-use, time-boxed to 5 minutes, and bypasses the freeze for exactly one mutation; the bypass is stamped into the Event Ledger so the audit trail records who overrode and why.

If soft-freeze is stuck active (the `active` field is `true` and you cannot identify the cleanup run that engaged it), see §J for the recovery procedure. Do not toggle the freeze field directly without checking what engaged it — you may unblock a cleanup mid-pass.

---

### Atomic token lifecycle

Three kinds of override token can be minted against `config:build-queue-tokens`:

- **`max_urgent_override`** — Max-issued, 1-hour time-box, used to bypass the completion-evidence requirement when Max personally vouches for a state change that has no harvestable evidence. Rare.
- **`cleanup_adjudication_token`** — auto-issued by `apply_max_signoff()` at the start of a cleanup run, scoped to one `adjudication_id`, used to bypass the completion-evidence requirement on items the cleanup is disposing of.
- **`freeze_lift_operation`** — Max-issued, 5-minute time-box, used to perform exactly one mutation while soft-freeze is active.

Every token is a row in `config:build-queue-tokens` with shape:

```json
{
  "token_id": "tok_a1b2c3...",
  "kind": "cleanup_adjudication",
  "scope": {"adjudication_id": "run_2026_05_10"},
  "issued_to": "max",
  "issued_at": "2026-05-10T14:00:00Z",
  "expires_at": "2026-05-10T15:00:00Z",
  "state": "active"
}
```

The `state` field is the heart of the lifecycle. It moves through `active → used` on consumption, or `active → revoked` on explicit revocation, or `active → expired` when the time-box passes. **Consumption is atomic**: `verify_and_consume_token(token_id, action_kind)` performs a single-transaction compare-and-swap from `active` to `used` inside the LS handler, then chains the protected mutation into the same transaction. If two callers race on the same token, exactly one wins the CAS and proceeds; the other receives `{ok: false, reason: used}` and the protected operation does not run. This is the "no replay" guarantee — see AC1.5.8 of the spec for the full invariant.

The single-use endpoint that ships in production is `POST /api/v1/allai/state/atomic_write` on `koskadeux-mcp`. All token issuance, consumption, and revocation events are recorded in the canonical Event Ledger; the audit trail tells you who minted which token, when it was used, and against which mutation.

To revoke an active token (e.g. at the end of a cleanup run), call `revoke_token(token_id, reason)`. Revocation does not affect tokens already in `used` state — those are immutable history.

---

### Recovery procedures

Three recovery paths cover the situations operators actually hit:

**Reverse a wrong cancellation.**

1. Find the cancellation event in the Event Ledger (`event_type=bq_cancelled`, filter by code).
2. Note the `prior_status` field on the event payload.
3. Issue `bq_update status=<prior_status>` against the item, with `evidence_summary="Reverting cancellation BQ-...; reason: <one line>"` and `actor=<your handle>`.
4. The item returns to its prior stage. Both the original cancellation and the revert sit in the ledger; the audit trail is complete.

If the item was cancelled longer than two weeks ago, prefer filing a fresh BQ that references the cancelled one rather than reverting — context decay tends to make the original scope no longer accurate.

**Handle a `bq_lifecycle_drift_detected` event.**

This event fires when a periodic reconciliation pass finds a `build:*` entity whose state-derived label disagrees with what the dashboard last rendered. The event payload names the item, the expected label, and the observed label.

1. Open the item on the dashboard. Hard-refresh.
2. If the dashboard now matches the entity, the drift was transient (likely a polling-window race). Affirm the item to clear the alarm.
3. If the disagreement persists, inspect `body.status` and `body.gate.*` directly via `state_request action=get key=build:<code>`. The entity is the source of truth; if it reads the way the dashboard *should* be rendering, file a frontend bug. If the entity itself is wrong, fix it with a `bq_update` that carries evidence and the corrective intent in `evidence_summary`.

**Reconciler write cadence — why a quiet item's version doesn't move.**

The periodic reconciliation pass writes `body.git_state` onto a `build:*` entity only when the *substantive* git state it computes differs from what is stored, or when a heartbeat window has elapsed (`RECONCILE_HEARTBEAT_SECONDS` in `app/services/reconciliation_job.py`, coupled to the lifecycle pickup freshness window so a quiet but pickup-eligible item never ages out between writes). Operator consequences:

1. A stable `version` / `version_stamp` on an otherwise-active item is normal, not a stuck reconciler — the item simply has not changed and is not yet due for a heartbeat. Confirm liveness via `body.git_state.last_reconciliation_attempt_at` / `last_reconciled_at`, not the version number.
2. The substantive comparison ignores each drift record's `detected_at` and tolerates stored-only `git_state` keys written by other writers. An item with an actively-stranding drain still writes every pass because its drift `age_seconds` is real, changing content — that is expected, not churn.
3. **Failure path — unresolvable branch.** When the reconciler cannot resolve an item's branch on origin (a filed item that was never branched, or a shipped chunk whose branch was merged and deleted), it records a stable `body.git_state.reconciliation_error` marker `{class, message, first_seen_at, last_seen_at}` *once*, then stays silent — no version bump, no `reconcile_failed` event — for as long as the error `class` is unchanged. A change of class writes again; a successful reconcile clears the marker to `null`. Operator consequence: a resting `reconciliation_error` with `class: branch_not_found` is the **normal** state for branchless items, not a stuck reconciler — `first_seen_at` tells you when the episode began. Failing items are not pickup-eligible, so there is deliberately **no** heartbeat refresh on this path; that absence is what stops a permanently-unresolvable item from bumping its version every backoff cycle. (`_record_reconcile_failure` / `_classify_reconcile_error` in `app/services/reconciliation_job.py`.)

**Soft-freeze stuck active.**

1. Read `config:build-queue-freeze` and inspect the `engaged_by` field.
2. If `engaged_by` references a cleanup adjudication run, look that run up at `config:cleanup-adjudication-runs/<run_id>`. If the run completed (signoff applied, manifest archived), it is safe to set `active=false` directly via `state_request action=patch`. If the run is mid-pass, do not touch the freeze — let the cleanup harness finish and release it.
3. If `engaged_by` references a manual engagement (cutover, incident), confirm with whoever engaged it before releasing.
4. If `engaged_by` is unset and the freeze is mysteriously active, there is a bug — file a BQ and use a `freeze_lift_operation` token (§I) to perform any urgent mutations until the bug is fixed. Do not bulk-disable the freeze without root-causing.

---

### Source-of-truth references

- **Locked spec:** [specs/bq-build-queue-lifecycle-s544-gate2-v6.md](../specs/bq-build-queue-lifecycle-s544-gate2-v6.md) — the Gate 2 v6 lock that defines every invariant cited in this runbook.
- **Closes:** BQ-BUILD-QUEUE-LIFECYCLE-S544 (this runbook is the Chunk 5 deliverable).
- **Dashboard URL:** `ops.ai.market/build-queue`.
- **Living State entities:** `build:*` (one per item), `config:build-queue-freeze` (soft-freeze boolean), `config:build-queue-tokens` (atomic override tokens), `config:cleanup-adjudication-runs/<run_id>` (cleanup manifests).
- **Production endpoints:**
  - `GET /api/v2/build-queue` — list view backing the dashboard.
  - `POST /api/v2/build-queue/reorder` — drag-reorder (§E).
  - `POST /api/v2/build-queue/{code}/cancel` — cancellation (§F).
  - `POST /api/v2/build-queue/{code}/complete` — Mark Complete drill-down (requires evidence).
  - `POST /api/v2/build-queue/{code}/affirm` — clear stale-item alarm (§D).
  - `POST /api/v1/allai/state/atomic_write` — single-use atomic-token write endpoint (§I).
- **Related runbooks:**
  - [runbooks/agent-dispatch.md](agent-dispatch.md) — how builder agents are dispatched.
  - [morning-briefing.md](morning-briefing.md) — the morning briefing where stale-item escalations (§D) appear.
  - [runbooks/activation-verification.md](activation-verification.md) — proof-of-life checks for shipped work.
- **CORE.md cross-reference:** this runbook should be linked from CORE.md under the Build Queue section. That edit is not part of this commit; file a follow-up if it has not been added by the time you read this.
