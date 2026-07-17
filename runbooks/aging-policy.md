---
runbook_id: aging-policy
domain: boot-kernel
status: ACTIVE
authoritative_for:
  - topic: aging-policy
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: stale_queue_undispatched
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-17
system_name: aging-policy
purpose_sentence: This companion carries the staleness thresholds, work-in-progress limits, boot obligations, anti-duplication rule, and close carry requirements.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Delivery companion for stale and critical-stale standup decisions, queue ordering, repeat incidents, WIP limits, and session-close aging accountability.
linter_version: 1.0.0
---

# Aging Policy

## §A. Header

The frontmatter is authoritative for catalog identity. **Authority: delivery companion.** Full CORE and the Boot Kernel prevail. Current item ages, priorities, incident counts, and statuses come from Living State, never this file.

**Fetch trigger:** stale or critical-stale standup or queue decision.

**Source constitution:** CORE v9.11, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`, section 6.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Seven-day stale classification | SHIPPED | `state_bq_status` | Session-open standup | 2026-07-17 |
| Fourteen-day critical-stale classification | SHIPPED | `state_bq_status` | Session-open standup | 2026-07-17 |
| Repeat-incident promotion | SHIPPED | `state_event` | Queue decision audit | 2026-07-17 |
| WIP and anti-duplication constraints | SHIPPED | `build:bq-*` | Pre-dispatch checks | 2026-07-17 |
| Close carry accountability | SHIPPED | `infra:handoff:instance=*` | Session close verification | 2026-07-17 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Queue Status | `state_bq_status` | Living State BQ entities | Session-open standup | Source for approvals, dispatch state, priority, and age. |
| Aging Classifier | CORE §6 thresholds | Derived at open | Queue decisions | Seven days is stale; fourteen days is critical-stale. |
| Repeat Incident Control | `state_event` | Incident and decision events | Priority and freeze actions | Second repeat promotes P0; third freezes new domain work. |
| WIP Control | Active build records | Build Queue and Living State | Dispatch preflight | Infrastructure/ops limit one; total limit three. |
| Close Carry | `infra:handoff:instance=*` | Database-only handoff | Next session | Aging obligations lead when approved work remains undispatched. |

### Normative projection — CORE §6

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> - **7-day threshold:** Any BQ item that has passed Gate 2 (or Gate 1 with no Gate 2 required) and has not been dispatched for build within 7 days is STALE.
> - **14-day threshold:** Any stale item older than 14 days is CRITICAL-STALE.
> - **Repeat incident rule:** If a production failure recurs in a domain where an approved BQ fix exists but was never built:
>   - 2nd incident: auto-promote to P0
>   - 3rd incident: freeze new work in that domain until the approved fix is dispatched

> At session start, BEFORE proposing new work or accepting new directives, each instance MUST:
>
> 1. Review all non-complete BQ items from `state_bq_status`
> 2. Identify items approved but undispatched for >7 days
> 3. If stale items exist, the instance's FIRST communication to Max MUST surface them explicitly: item name, age since approval, repeat incident count, required next action — and recommend dispatching the oldest stale item before new work
> 4. If Max directs new work while stale approved items exist: state what is being deferred and the risk, request explicit override, and log a `decision` event via `state_event`

> - **Infrastructure/ops WIP limit:** 1 active build at a time
> - **Total active build WIP limit:** 3 (across all tracks, both instances)
> - **No new Gate 1 reviews** while any approved item has been waiting >14 days for dispatch
> - **No successor specs:** MUST NOT create a new BQ spec for a problem that already has an approved BQ covering it. Default action is dispatch the existing approved item, not write a replacement.

> When closing a session where approved items were NOT dispatched:
> - The role handoff record MUST include an "AGING OBLIGATIONS" section at the top (before priorities)
> - Each aging item MUST include: BQ code, title, days since approval, repeat incident count, required next action
> - MUST log a `decision` event explaining why the item was deferred
> - Items carried forward more than 3 sessions without dispatch require escalation to Max with explicit "dispatch or cancel" recommendation

> Before creating any new BQ entity, search Living State (`state_bq_status`) for existing items in the same domain. If an approved-but-unbuilt item covers the same problem space, dispatch it instead of creating a new spec.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Classify and surface aging work | `state_bq_status` | Living State read | COMPLETE |
| MP | Build the selected approved item | `council_request mode=build` | Approved repository scope | COMPLETE |
| Max | Explicitly override queue ordering or decide dispatch versus cancel | Human decision | Final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Session open must classify approved but undispatched work.
  pre_conditions: [bq_status_available, approval_dates_available]
  tool_or_endpoint: state_bq_status
  argument_sourcing: {age: compute from approval timestamp to current UTC time, incidents: read recorded repeat count}
  idempotency: IDEMPOTENT
  expected_success: {shape: priority list with stale and critical-stale labels, verification: recompute age and compare dispatch state}
  expected_failures: [{signature: stale_queue_undispatched, cause: approved work exceeded threshold without dispatch or explicit decision}]
  next_step_success: Recommend oldest stale approved work before new work.
  next_step_failure: Surface missing state and avoid inventing age or status.
- id: E-02
  trigger: A new directive competes with stale approved work.
  pre_conditions: [stale_items_known, new_directive_known]
  tool_or_endpoint: state_event
  argument_sourcing: {decision: record deferred item risk and explicit override when given}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(session + deferred_items + directive_digest)
  expected_success: {shape: auditable queue override decision, verification: read the event and confirm all deferred items are named}
  expected_failures: [{signature: aging_override_unlogged, cause: new work proceeded without explicit risk and decision evidence}]
  next_step_success: Proceed within WIP limits.
  next_step_failure: Keep the oldest approved item as the recommended next action.
- id: E-03
  trigger: Session close carries approved work that was not dispatched.
  pre_conditions: [handoff_writable, aging_items_recomputed]
  tool_or_endpoint: state_patch("infra:handoff:instance=*")
  argument_sourcing: {aging_obligations: include code title days incidents and next action before priorities}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(instance + session + aging_obligations_digest)
  expected_success: {shape: confirmed database handoff with leading aging obligations, verification: read back handoff and decision events}
  expected_failures: [{signature: aging_close_carry_missing, cause: deferred approved work was omitted or under-specified}]
  next_step_success: Close only after confirmed handoff write.
  next_step_failure: Leave the session open for idempotent handoff retry.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Approved work is older than seven days and undispatched. | Queue ordering, missing ownership, WIP saturation, or unlogged override deferred it. | Read BQ approval and dispatch timestamps, incident count, active WIP, and decision events. | G-01 | CONFIRMED |
| F-02 | A successor spec duplicates approved unbuilt work. | Anti-duplication search was skipped or stale state was used. | Compare the proposed problem with all active same-domain BQ summaries and approved scope. | G-02 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Aging Classifier
  root_cause: Approved work aged beyond its dispatch threshold without an executed or explicit queue decision.
  repair_entry_point: state_bq_status and build dispatch preflight
  change_pattern: Recompute age and incidents, apply priority or freeze rules, then dispatch the oldest eligible item or record Max override.
  rollback_procedure: Cancel an ineligible dispatch and restore the prior queue state without erasing aging evidence.
  integrity_check: Queue status, event record, WIP, and dispatch target agree.
- id: G-02
  symptom_ref: F-02
  component_ref: Queue Status
  root_cause: Existing same-domain approved scope was not searched before authoring.
  repair_entry_point: state_bq_status
  change_pattern: Stop successor authoring and route the need to the existing approved BQ unless scope evidence proves a distinct problem.
  rollback_procedure: Abandon the duplicate draft without altering the approved BQ.
  integrity_check: One authoritative BQ covers the problem and its next action is explicit.
```

## §H. Evolve

### §H.1 Invariants

Aging is computed from live approval and dispatch evidence; queue obligations cannot be erased by a new session or successor spec.

### §H.2 BREAKING predicates

Weakening thresholds, WIP limits, repeat-incident actions, close carry, or anti-duplication obligations is BREAKING.

### §H.3 REVIEW predicates

Review changes to timestamp sources, standup rendering, incident counting, priority ordering, or handoff schema.

### §H.4 SAFE predicates

Display and explanation improvements are safe when computed classifications and required actions are unchanged.

### §H.5 Boundary definitions

#### module

Living State BQ records, event ledger, active-build set, standup, and database handoff.

#### public contract

Stale and critical-stale labels, required recommendation, WIP actions, and close carry fields.

#### runtime dependency

Living State, accurate UTC timestamps, Build Queue dispatch status, and handoff persistence.

#### config default

No missing timestamp is treated as fresh; unresolved evidence is surfaced rather than guessed.

### §H.6 Adjudication

CORE sets the rules, live state supplies values, and Max decides explicit queue-order overrides.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: An approved undispatched item reaches eight days old., expected_answers: [{kind: classification, label: STALE}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-01], scenario: An approved undispatched item reaches fifteen days old., expected_answers: [{kind: classification, label: CRITICAL_STALE}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: Session close carries approved undispatched work., expected_answers: [{kind: human_action, verb: record, object: aging obligations, target: top of database handoff}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: A second incident recurs while its approved fix remains unbuilt., expected_answers: [{kind: classification, label: PROMOTE_P0}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-01], scenario: A third incident recurs while its approved fix remains unbuilt., expected_answers: [{kind: classification, label: FREEZE_DOMAIN_NEW_WORK}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-02], scenario: A new spec covers the same problem as an approved BQ., expected_answers: [{kind: classification, label: DUPLICATE_SUCCESSOR}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: An old approved item was omitted from standup., expected_answers: [{kind: human_action, verb: recompute, object: aging list, target: live BQ state}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: Duplicate successor authoring has begun., expected_answers: [{kind: human_action, verb: stop, object: duplicate spec, target: existing approved BQ}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal moves critical-stale from fourteen to thirty days., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [§H], scenario: Standup adds a clearer age display without changing classification., expected_answers: [{kind: classification, label: SAFE}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: Approval timestamp is missing for an undispatched item., expected_answers: [{kind: human_action, verb: surface, object: unknown age evidence, target: queue decision}], weight: 0.090909091}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1266
last_refresh_commit: e4d2057
last_refresh_date: 2026-07-17T22:00:00Z
owner_agent: vulcan
refresh_triggers: [CORE aging threshold or WIP changes, Build Queue timestamp semantics changes, standup or handoff aging fields change]
scheduled_cadence: 30d
last_harness_pass_rate: 1.0
last_harness_date: 2026-07-17T22:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1266 / 2026-07-17T22:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: null
```
