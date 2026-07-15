---
system_name: work-checkout
purpose_sentence: Enforced work checkout - the queue row owns who is working on what, one item one owner, enforced at the tool boundary.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Ownership claim/release semantics on Build Queue rows and trouble tickets, the assignment_query read surface, dispatch-gate enforcement, staleness, and ownership repair.
linter_version: 1.0.0
---

# Work Checkout (Enforced Ownership)

## §A. Header

The YAML frontmatter above is the §A header. Built under BQ-WORK-CHECKOUT-ENFORCED-OWNERSHIP-S1214 (Max directive S1214). The queue row is the checkout: `body.lifecycle.pickup_ownership = {"instance", "session_id", "claimed_at"}`. The peer bus remains notification-only, never the record. Specs: `koskadeux-mcp/specs/BQ-WORK-CHECKOUT-ENFORCED-OWNERSHIP-S1214-GATE1.md` and `-GATE2.md`.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Claim with CAS and M1 status precondition | SHIPPED | `koskadeux-mcp/tools/state.py:2036` | 18 ownership unit tests (C1) | 2026-07-15 |
| Release and force-release (explicit-null clear; same-instance session recovery) | SHIPPED | `koskadeux-mcp/tools/state.py:2141` | C1 suite + T-2026-000258 regression + C4 fold tests | 2026-07-15 |
| Work-is-the-heartbeat claim refresh (M2) | SHIPPED | `koskadeux-mcp/tools/state.py` | C1 suite | 2026-07-14 |
| Stale owner reads as unowned (M3) | SHIPPED | `koskadeux-mcp/tools/state.py:283` | C1/C2 suites | 2026-07-14 |
| assignment_query peer-owned filtering with truthful owner (C2) | SHIPPED | `koskadeux-mcp/tools/assignment_query/query.py` | C2 suite | 2026-07-14 |
| Dispatch-gate enforcement from the queue row, gate ON (C3) | SHIPPED | `koskadeux-mcp/tools/agents.py:609` | Live two-instance collision test S1218/S1219 | 2026-07-14 |
| Ownership writable only by claim/release (invalid_ownership guard) | SHIPPED | `koskadeux-mcp/tools/state.py` | GLM Gate-3 fold regression tests | 2026-07-15 |
| Ticket ownership and session-lifecycle release (C4) | SHIPPED | `koskadeux-mcp/tools/support_ticket.py` | C4 suites (tests/tools/test_session_work_ownership_c4.py, tests/unit/test_support_ticket_ownership_c4.py, backend test_support_ticket_s811_c2.py) + live probe T-2026-000261 | 2026-07-15 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Claim | `state_request action=claim` | `body.lifecycle.pickup_ownership`, entity version | Build Queue lifecycle, peer bus claim message | CAS plus status precondition {planned, in_design, in_progress, blocked}; idempotent for the current owner; conflict returns `owner_conflict` naming holder, session, claimed_at. |
| Release | `state_request action=release` | same row | event ledger | `force=true` permitted between trusted peers. Release writes an explicit `pickup_ownership: null` (merge-safe under the backend deep-merge PATCH; T-2026-000258 root fix, live since koskadeux-mcp `9bdf4e73`). Same-instance conflict is session-scoped: a new session of the owning instance may release its own instance's claim. |
| Read surface | `state_request action=assignment_query` | queue rows | ops dashboard | Peer-owned live rows hidden by default; stale owners read as unowned; `filters.include_peer_owned` for audit reads. |
| Dispatch gate | `council_request` / `dispatch_mp_build` with `caller_instance` | queue row via `ownership_of` | MP/CC/DeepSeek/GLM dispatch paths (5 call sites) | Refuses `peer_claim_conflict` naming holder and next unowned item; `caller_instance` required at the tool boundary (M4); internal fanout inherits identity; fail-open on EXCEPTION preserved (S958 lesson). |
| Staleness | `WORK_CLAIM_STALE_HOURS` env, default 24 | `claimed_at` | claim, read surface | Only ownership with NO owner activity for the whole window expires; active work never goes stale (M2). |
| Kill switch | `PEER_CLAIM_GATE_ENABLED` in `koskadeux-mcp/scripts/launch_mcp_server.sh:7` | process env | dispatch gate | Default 1 (ON). Max decision to disable; event and revert after. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan / Mars | Claim, release, force-release, dispatch under gate | `state_request`, `council_request`, `dispatch_mp_build` | Trusted-operator | COMPLETE |
| Max | Force-release adjudication, gate kill switch | direct instruction | Business/product owner | COMPLETE |
| MP | Builds fixes in this domain | `dispatch_mp_build` | Per dispatch | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An instance is about to start any backlog item (BQ or ticket).
  pre_conditions:
    - session is OPERATIONAL (kd_session_open + kd_session_plan done)
    - peer bus drained
  tool_or_endpoint: state_request action=claim
  argument_sourcing:
    key: the entity key from assignment_query
    instance: the active instance name
    session_id: the current session id
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: key + instance + session_id
  expected_success:
    shape: 'success true; ownership {instance, session_id, claimed_at} matching the caller; new_version returned'
    verification: 'send a kind=claim peer-bus message referencing the entity; re-read shows the ownership object'
  expected_failures:
    - signature: 'owner_conflict 409 naming another live holder'
      cause: the peer holds the item (§F-01), or a stale self-claim from a dead session (§F-02)
    - signature: 'not_claimable naming a terminal status'
      cause: M1 status precondition - the item is completed or cancelled
  next_step_success: start the work; owner activity refreshes the claim automatically (M2)
  next_step_failure: repair per §G-02 (peer); a stale self-claim under a prior session releases normally (same-instance recovery, C4)
- id: E-02
  trigger: An instance finishes or abandons an item mid-session.
  pre_conditions:
    - caller is the current owner
  tool_or_endpoint: state_request action=release, or bq_update to a terminal state (completed/cancelled/failed) which releases in the same write (M5)
  argument_sourcing:
    key: the owned entity key
    instance: the active instance name
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'released true (release) or the terminal status transition applied (bq_update)'
    verification: 're-read the entity; body.lifecycle.pickup_ownership is null'
  expected_failures:
    - signature: 'release reports success=true released=false reason=session_owner_changed'
      cause: a newer session re-claimed the row between enumerate and release - benign no-op (close report buckets it as skipped)
  next_step_success: item returns to the unowned pool or leaves the queue
  next_step_failure: re-read the entity; if ownership persists after a clean release this is a regression of T-2026-000258 - open a ticket (the historical §G-01 repair pattern still documents the manual clear)
- id: E-03
  trigger: An audit or dashboard read needs to see peer-owned rows.
  pre_conditions:
    - read-only intent
  tool_or_endpoint: state_request action=assignment_query with filters.include_peer_owned=true
  argument_sourcing:
    caller_instance: the active instance name
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'rows include peer-owned items, each carrying a truthful owner field'
    verification: 'owner.instance populated on live-owned rows'
  expected_failures:
    - signature: 'invalid_assignment_query'
      cause: malformed filters or expand values
  next_step_success: none (read)
  next_step_failure: correct the arguments and re-issue
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `owner_conflict` 409 naming the PEER instance | The peer legitimately holds the item | Read `owner` in the refusal; confirm holder instance differs from caller | §G-02 | CONFIRMED |
| F-02 | `release` returns success but ownership persists on re-read | Regression of T-2026-000258 (root fix live since koskadeux-mcp `9bdf4e73`: release writes explicit null, merge-safe) | Re-read the entity after release; confirm the running server is on/after `9bdf4e73` | §G-01 | DEPRECATED |
| F-03 | `invalid_ownership` refusal on put/patch touching pickup_ownership | Deliberate guard: ownership is writable only by claim/release | Reproduce with a minimal patch; the refusal names the rule | §G-01 | CONFIRMED |
| F-04 | `peer_claim_conflict` on council_request or dispatch_mp_build | The item is live-owned by the peer | The refusal names the holder and the next unowned item | §G-02 | CONFIRMED |
| F-05 | `caller_instance_required` on a build/review dispatch | Missing explicit caller identity at the tool boundary (M4) | Inspect the dispatch args for caller_instance | §G-03 | CONFIRMED |
| F-06 | `author-mode dispatch rejected before MP launch` on a row the CALLER itself claimed; details show `identity_required_for_owned_row` | Pre-fix gateway: author-mode gate writes carried no instance (T-2026-000262; fixed at koskadeux-mcp `e124a764`, activates at gateway reload) | Check `transition_details` in the rejection payload (post-fix) or run `transition_to_authoring_in_flight(return_details=True)` locally; confirm the running server predates `e124a764` | §G-04 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-02
  component_ref: Release
  root_cause: 'T-2026-000258: _body_with_ownership pops the key but backend atomic_write PATCH deep-merges, so key removal no-ops; the MCP patch tool refuses the field by design (F-03)'
  repair_entry_point: backend POST /api/v1/allai/state/atomic_write with X-Internal-API-Key
  change_pattern: 'RETIRED 2026-07-15 (S1228): the T-2026-000258 root fix shipped and is live - the release path writes an explicit pickup_ownership null (koskadeux-mcp `9bdf4e73`, regression-tested) and same-instance session recovery covers stale self-claims, so this repair should no longer be needed. Historical pattern, kept for a regression scenario only: GET the entity for the current version, then one atomic_write carrying entity_write {method: patch, body: {lifecycle: {pickup_ownership: null}}, expected_version} AND event_append {event_type: work_ownership_released, unique dedupe_key}; verify null on re-read, then re-claim. Any need to use this again is itself a defect - open a ticket.'
  rollback_procedure: re-claim under the intended instance/session
  integrity_check: claim succeeds under the current session; the release event is visible in the ledger
- id: G-02
  symptom_ref: F-01
  component_ref: Read surface
  root_cause: two instances converging on the same item - the system working as designed
  repair_entry_point: assignment_query
  change_pattern: leave the item alone and work the next_unowned item named in the refusal; if the holder session is genuinely dead past WORK_CLAIM_STALE_HOURS the row reads as unowned and a normal claim succeeds; force-release only by agreement over the peer bus or by Max
  rollback_procedure: n/a - no state was changed
  integrity_check: the loser proceeds on a different item; no duplicate work
- id: G-03
  symptom_ref: F-05
  component_ref: Dispatch gate
  root_cause: build or review dispatch issued without explicit caller identity
  repair_entry_point: the dispatch call arguments
  change_pattern: re-dispatch with caller_instance set to the active instance (or system for genuine non-instance callers); never route around the gate by writing state directly
  rollback_procedure: n/a
  integrity_check: dispatch proceeds and the event records the caller
- id: G-04
  symptom_ref: F-06
  component_ref: Author-mode gate writes
  root_cause: 'T-2026-000262: author_mode_state transitions issued bq_update gate writes without instance, so C4 owned-row enforcement refused them on rows the dispatching instance had itself claimed; the dispatch path swallowed the detail'
  repair_entry_point: koskadeux-mcp main e124a764 (fix 6fe22c65) - caller_instance threads through all five author transitions into the bq_update instance arg; rejection payload now carries transition_details
  change_pattern: 'Post-reload: nothing to do - author-mode dispatch on a self-claimed row just works, and peer-owned rows are still refused. Pre-reload (gateway older than e124a764): release the claim via the post-C4 LOCAL release path, bind the authoring lease locally with transition_to_authoring_in_flight(return_details=True), dispatch with the SAME dispatch_id/token (gateway takes the idempotent branch), re-claim after authoring completes (the completion write hits the same refusal on an owned row). Evented S1229 dedupe s1229-authoring-claim-release-workaround.'
  rollback_procedure: revert e124a764 on main; unowned/legacy behavior is unchanged by the fix (instance key omitted when absent)
  integrity_check: author-mode dispatch succeeds on a self-claimed row; peer-owned dispatch still refuses with owner_conflict
```

## §H. Evolve

### §H.1 Invariants

- **The queue row is the checkout.** Ownership lives on `body.lifecycle.pickup_ownership`, never in bus messages, handoff prose, or side entities. The peer bus is notification only.
- **Ownership is written only by claim and release.** put/patch refuse the field (`invalid_ownership`). The §G-01 backend repair pattern (retired; historical) is the sole sanctioned bypass, only for a regression of the fixed stuck case, always with the event appended and a ticket opened.
- **The work is the heartbeat.** Owner activity refreshes the claim; there is no lease-renewal protocol. Only a fully silent owner past `WORK_CLAIM_STALE_HOURS` expires.
- **No item can be hidden from everyone.** Stale owners read as unowned in the read path (M3).
- **The gate never bricks dispatch.** Fail-open on EXCEPTION is preserved (S958 lesson); refusals are deliberate, truthful, and name the holder plus the next unowned item.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Removing the CAS from claim, or widening ownership writers beyond claim/release.
- Moving the source of truth off the queue row (back to bus messages or any parallel signal entity).
- Defaulting `PEER_CLAIM_GATE_ENABLED` to off, or making missing caller identity fail-open on build/review dispatches.
- Introducing midnight-based or bus-based claim expiry.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Changing the `WORK_CLAIM_STALE_HOURS` default or the claimable-status set.
- Adding refusal codes or changing refusal payload shapes.
- Adding a new ownership-bearing item kind beyond Build Queue rows and trouble tickets.

### §H.4 SAFE predicates

SAFE otherwise:
- Wording changes in refusal messages; event payload additions; test additions; documentation.
- Logging or dashboard-display changes that do not alter ownership semantics.

### §H.5 Boundary definitions

#### module

`koskadeux-mcp/tools/state.py` (claim/release/refresh/staleness), `koskadeux-mcp/tools/assignment_query/query.py` (read surface), `koskadeux-mcp/tools/agents.py` (dispatch gate), `koskadeux-mcp/scripts/launch_mcp_server.sh` (gate switch).

#### public contract

`state_request` actions claim/release/assignment_query and their refusal codes (`owner_conflict`, `not_claimable`, `invalid_ownership`), the dispatch-gate refusals (`peer_claim_conflict`, `peer_claim_required`, `caller_instance_required`), the ownership object shape `{instance, session_id, claimed_at}`, and the ownership events.

#### runtime dependency

The Living State backend `atomic_write` endpoint on ai-market-backend; the koskadeux-mcp venv Python runtime.

#### config default

`WORK_CLAIM_STALE_HOURS` (default 24) and `PEER_CLAIM_GATE_ENABLED` (default 1) in the MCP server environment.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Anything weakening the one-item-one-owner guarantee or the writable-only-by-claim/release guard escalates to Max; the ruling is added to §H.1 as a clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Mars wants to start a queue item after opening and draining the bus. What is the first action?
    expected_answers:
      - kind: tool_call
        action: state_request action=claim with key, instance, session_id; then a kind=claim peer-bus message
    weight: 0.0909091
  - id: I-02
    type: repair
    refs: [G-01]
    scenario: Claim returns owner_conflict naming mars under a previous session id while mars itself is claiming. What is happening and what do you do?
    expected_answers:
      - kind: tool_call
        action: release under your own instance with the current session (same-instance recovery, C4), then re-claim; if release cannot clear it, treat as a T-2026-000258 regression - ticket it and use the historical G-01 pattern
    weight: 0.0909091
  - id: I-03
    type: repair
    refs: [G-02]
    scenario: A build dispatch is refused with peer_claim_conflict naming vulcan. What next?
    expected_answers:
      - kind: human_action
        action: leave the item alone and work the next_unowned item named in the refusal; never force-release a live peer claim unilaterally
    weight: 0.0909091
  - id: I-04
    type: operate
    refs: [E-02]
    scenario: Mars finishes an item. How is ownership released and verified?
    expected_answers:
      - kind: tool_call
        action: bq_update to the terminal state (releases in the same write) or action=release, then re-read and confirm pickup_ownership is null; if not, ticket it as a T-2026-000258 regression (historical G-01 pattern applies)
    weight: 0.0909091
  - id: I-05
    type: isolate
    refs: [F-03]
    scenario: A patch writing pickup_ownership returns invalid_ownership. Is this a defect?
    expected_answers:
      - kind: human_action
        action: no - deliberate guard; use claim/release (the retired G-01 repair is for a regression of the fixed stuck case only)
    weight: 0.0909091
  - id: I-06
    type: isolate
    refs: [F-01]
    scenario: An item's owner has been silent past WORK_CLAIM_STALE_HOURS. Can it be claimed?
    expected_answers:
      - kind: tool_call
        action: yes - stale reads as unowned (M3); claim normally
    weight: 0.0909091
  - id: I-07
    type: isolate
    refs: [F-04]
    scenario: A dashboard read needs to include peer-owned rows.
    expected_answers:
      - kind: tool_call
        action: assignment_query with filters.include_peer_owned=true
    weight: 0.0909091
  - id: I-08
    type: evolve
    refs: [E-01]
    scenario: 'Proposal: let put/patch write ownership for convenience.'
    expected_answers:
      - kind: human_action
        action: classify BREAKING and refuse without full Council review
    weight: 0.0909091
  - id: I-09
    type: evolve
    refs: [E-02]
    scenario: 'Proposal: expire all claims at midnight to keep the queue tidy.'
    expected_answers:
      - kind: human_action
        action: classify BREAKING - midnight/bus-based expiry is an explicit §H.2 predicate (the S958-era bug class)
    weight: 0.0909091
  - id: I-10
    type: ambiguous
    refs: [F-01, F-02]
    scenario: A claim returns owner_conflict but the handoff prose says the item is free. Which is right?
    expected_answers:
      - kind: human_action
        action: the queue row wins - inspect the holder in the refusal; if it is your own dead session release it under the current session (same-instance recovery), if it is the live peer work the next item; correct the handoff prose
    weight: 0.0909091
  - id: I-11
    type: operate
    refs: [E-01]
    scenario: The gate must be disabled in an emergency.
    expected_answers:
      - kind: human_action
        action: Max decision only - PEER_CLAIM_GATE_ENABLED=0 in the launch script env, evented and reverted after
    weight: 0.0909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1225
last_refresh_commit: 5227dc8
last_refresh_date: 2026-07-15T11:15:00Z
owner_agent: mars
refresh_triggers:
  - a new ownership-bearing item kind landing
  - claim/release/staleness semantics changing
  - dispatch gate call sites changing
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-15T08:45:00Z
first_staleness_detected_at: null
```

Refresh log:
- S1228 (2026-07-15): C4 shipped and live-verified. Ticket ownership at the MCP boundary (claim/refresh/release/refusal, stale-as-unowned projection), `kd_session_open` held_items, `kd_session_close` session-claim release with carry_forward_claims, T-2026-000258 root fix (explicit-null release) - koskadeux-mcp main `9bdf4e73` (Gate 3: CC APPROVE after M6/M7/M8 fold `9186ad5f`, DeepSeek APPROVE, GLM APPROVE_WITH_NITS), backend main `800c6217` (Railway deploy SUCCESS). Live probe T-2026-000261 verified claim persistence, peer refusal, same-instance new-session release, terminal release, read projection. §G-01 retired to historical; §B/§C/§E/§F/§H/§I/§J updated. Gateway handler activates on the next idle reload; the next session open should show held_items.
- S1225 (2026-07-15): first authoring, against shipped C1-C3 on koskadeux-mcp main (`fee13056`, `0c8ecca4`, `6d2aadaa`, `a6e1831e`, GLM fold `9ea348a9`), the S1218/S1219 live Gate-4 collision test, and a live S1225 reproduction of the T-2026-000258 release no-op plus its ledgered repair. Discharges S1216-D1/D2.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1225 / 2026-07-15T08:45:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

Router conformance is guarded by `scripts/router_drift_check.py`; the topic router must point to this filename.
