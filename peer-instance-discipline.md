---
system_name: peer-instance-discipline
purpose_sentence: Peer-symmetric operating discipline for the trusted Vulcan and Mars instances.
owner_agent: vulcan/mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Equal-authority instance behavior, claim-before-work coordination, peer-message bus usage, and escalation boundaries.
linter_version: 1.0.0
---

# Peer Instance Discipline

## §A. Header

The YAML frontmatter above is the §A header. This runbook supersedes the retired Primary/Worker discipline: `vulcan` and `mars` are two cooperating instances of the same frontier model with equal authority over shell, git, dispatch, and Living State.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Independent instance open/plan/close | SHIPPED | `koskadeux-mcp/tools/session.py:kd_session_open` | Session lifecycle smoke coverage | 2026-06-16 |
| Peer message bus | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_msg_send` | Manual drain verified S835 | 2026-06-16 |
| Peer bus inbox drain | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_msg_inbox` | Manual drain verified S835 | 2026-06-16 |
| Instance status lookup | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_status` | Manual status lookup verified S835 | 2026-06-16 |
| Living State CAS claim | SHIPPED | `state_request:bq_update` | Optimistic versioning exercised by BQ lifecycle | 2026-06-16 |
| Primary/Worker lanes and close ordering | DEPRECATED | `session-open-protocol.md:O.3` | Retired by symmetric-peer model | 2026-06-16 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Peer Instance | `kd_session_open(instance=<vulcan|mars>)` | `registry.db` instance rows, per-instance handoff | Living State, shell, git, Council dispatch | Either instance may open first, plan independently, work any item, and close independently. |
| Claim Transition | `state_request action=bq_update` | `build:bq-*` entity version, status, gate, assignee fields | Build Queue lifecycle | Work starts only after a CAS status transition succeeds against the version just read. |
| Peer Message Bus | `peer_msg_send` / `peer_msg_inbox` | peer-bus messages by `to`, `from_instance`, kind, ack state | Vulcan, Mars | Claim/status/request/response/alert messages coordinate work without Max relay. |
| Dispatch Surface | `council_request` / `dispatch_mp_build` | dispatch tasks, BQ entity refs, branch state | MP, AG, DeepSeek, CC | Either peer may dispatch after draining the bus and confirming no competing claim. |
| Git/Shell Surface | shell plus git CLI | local worktree, `origin/main`, branches | target repos | Either peer may inspect, commit, merge, and push within the same authority boundaries. |
| Max Escalation | direct user thread | strategic decision record, BQ notes | Max | Used only for strategic forks or cross-instance unblocks agents cannot resolve. |

There are no lanes, ownership splits, primary approvals, worker audits, or close-order dependencies. Coordination is through state and the peer bus, not through assigning work to the other instance.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Open, claim, operate, dispatch, merge, close | `kd_session_open(instance="vulcan")`, state tools, shell, git, dispatch tools | Full trusted-operator scope | COMPLETE |
| Mars | Open, claim, operate, dispatch, merge, close | `kd_session_open(instance="mars")`, state tools, shell, git, dispatch tools | Full trusted-operator scope | COMPLETE |
| MP/AG/DeepSeek/CC | Delegated review/build work | `council_request`, `dispatch_mp_build` | Per dispatch mode | COMPLETE |
| Max | Strategic adjudication | direct instruction | Business/product owner | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An instance opens a session and is ready to pick up work.
  pre_conditions: [session_opened_with_instance_name, kd_session_plan_completed]
  tool_or_endpoint: peer_msg_inbox(instance=<vulcan|mars>)
  argument_sourcing:
    instance: the active instance name used in kd_session_open
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: active_instance + inbox_cursor
  expected_success: Inbox is drained; request and alert messages are acknowledged or queued for immediate response.
  expected_failures: [inbox_unavailable, unread_request, unread_alert]
  next_step_success: Choose candidate work from the queue and run E-02 before touching it.
  next_step_failure: Repair bus access or answer required peer messages before starting work.
- id: E-02
  trigger: An instance intends to start any queue item, runbook revision, dispatch, or merge.
  pre_conditions: [peer_bus_drained, target_entity_read, current_entity_version_known, origin_main_checked]
  tool_or_endpoint: state_request(action=bq_update, bq_code=<code>, status=in_progress, expected_version=<version>, note=<claim_note>)
  argument_sourcing:
    code: BQ code or lifecycle item identifier from the queue/router/handoff
    version: entity version from the immediately preceding Living State read
    claim_note: active instance, session id, branch or file scope, and intended first action
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: target_entity + expected_version + active_instance
  expected_success: CAS transition succeeds and the entity records the claimant.
  expected_failures: [version_conflict, status_already_in_progress, missing_body_summary]
  next_step_success: Send E-03 claim message, then begin work.
  next_step_failure: Treat the item as already taken; pick another item or coordinate with the claimant.
- id: E-03
  trigger: A CAS claim succeeds.
  pre_conditions: [cas_claim_succeeded, claim_scope_known]
  tool_or_endpoint: peer_msg_send(to=<other|both>, kind=claim, subject=<item>, body=<scope>)
  argument_sourcing:
    to: the other peer, or both when uncertain which peer is live
    subject: claimed BQ/runbook/branch/file scope
    body: include claimant instance, session id, CAS evidence, and intended work boundary
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: target_entity + cas_version + "claim"
  expected_success: Claim message is visible to the peer bus.
  expected_failures: [send_failed, ambiguous_claim_scope]
  next_step_success: Proceed with work inside the claimed scope.
  next_step_failure: Pause work until the bus message is sent or Max resolves a bus outage.
- id: E-04
  trigger: An instance is about to dispatch another agent, merge a branch, or close its session.
  pre_conditions: [work_scope_claimed_or_read_only, local_git_status_known]
  tool_or_endpoint: peer_msg_inbox(instance=<vulcan|mars>)
  argument_sourcing:
    instance: active instance
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: active_instance + "pre-dispatch-merge-close" + inbox_cursor
  expected_success: No unread claim conflicts, requests, or alerts remain.
  expected_failures: [unread_claim_conflict, request_requires_ack, alert_requires_ack]
  next_step_success: Dispatch, merge, or close.
  next_step_failure: Acknowledge and resolve the peer message before proceeding.
- id: E-05
  trigger: A routine peer needs information, progress, or a handoff note.
  pre_conditions: [message_kind_selected, recipient_known]
  tool_or_endpoint: peer_msg_send(to=<vulcan|mars|both>, kind=<status|request|response|alert>, body=<message>)
  argument_sourcing:
    kind: claim for work ownership, status for FYI, request for answer needed, response for reply, alert for urgent unblock
    body: concise operational fact, requested action, deadline if any, and evidence link
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: recipient + kind + subject + body_digest
  expected_success: Status messages inform; request and alert messages are acked by the recipient.
  expected_failures: [missing_ack, wrong_kind, over_escalation_to_max]
  next_step_success: Continue without assigning or approving peer work.
  next_step_failure: Retry once, then escalate only if cross-instance unblock is impossible.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Two peers appear to be working the same item | CAS was skipped, claim message unread, stale handoff was trusted | Read target entity version/history, drain peer bus, inspect branch/file overlap | G-01 | CONFIRMED |
| F-02 | CAS claim fails | Another peer already claimed, entity advanced, or stale version was used | Re-read entity and compare expected_version/status/claim note | G-02 | CONFIRMED |
| F-03 | Peer request or alert is discovered late | Bus was not drained at open, before dispatch/merge, or before close | Drain inbox and check ack-required messages | G-03 | CONFIRMED |
| F-04 | Work proceeds from stale handoff or queue addendum | Ground-truth verification skipped | Compare entity body, `origin/main`, branch list, and relevant artifact state | G-04 | CONFIRMED |
| F-05 | A multi-finding fold claims more than the diff proves | Builder output not checked line-by-line | Verify each claimed finding against actual diff at file/line | G-05 | CONFIRMED |
| F-06 | Max is asked to resolve routine execution details | Peer treated Max as dispatcher/approver instead of strategic owner | Review unresolved facts; check whether peer/status/request could answer | G-06 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Claim Transition
  root_cause: Work began without both CAS ownership and a peer-bus claim.
  repair_entry_point: state_request action=bq_update
  change_pattern: Stop both peers at the next safe point; the peer without the successful CAS claim backs out or narrows scope; record a status message with the surviving owner.
  rollback_procedure: Revert only unmerged/unpushed duplicate work that belongs to the losing claim; never revert unrelated peer changes.
  integrity_check: Entity status, claim note, peer-bus claim, branch owner, and next action all name one instance.
- id: G-02
  symptom_ref: F-02
  component_ref: Claim Transition
  root_cause: Optimistic versioning rejected the claim because the item changed.
  repair_entry_point: state_request action=get
  change_pattern: Treat CAS failure as "item already taken"; re-read state and either send a request to the claimant or choose another item.
  rollback_procedure: None; failed CAS has no side effect.
  integrity_check: No local edits, dispatches, or merges were started after the failed claim.
- id: G-03
  symptom_ref: F-03
  component_ref: Peer Message Bus
  root_cause: Required inbox drains were skipped.
  repair_entry_point: peer_msg_inbox
  change_pattern: Drain immediately; ack every request/alert; defer dispatch/merge/close until conflicts are resolved.
  rollback_procedure: If dispatch or merge already happened, send status with evidence and reconcile state before continuing.
  integrity_check: Inbox has no unacked request/alert and no unread conflicting claim.
- id: G-04
  symptom_ref: F-04
  component_ref: Git/Shell Surface
  root_cause: Prior-session text was trusted over Living State and git.
  repair_entry_point: state_request action=get plus git fetch
  change_pattern: Re-read entity, fetch origin, compare branch/log/diff evidence, then update or abandon the stale action.
  rollback_procedure: Do not revert shipped work; update the plan and state note to match actual ground truth.
  integrity_check: The next action is supported by both Living State and origin/main.
- id: G-05
  symptom_ref: F-05
  component_ref: Dispatch Surface
  root_cause: Fold output bundled too many findings or was accepted without diff inspection.
  repair_entry_point: git diff / file:line inspection
  change_pattern: Check every claimed finding manually; split remaining findings into smaller follow-up folds with a soft cap around three.
  rollback_procedure: Mark unsupported claims unresolved; keep verified edits only.
  integrity_check: Each closed finding maps to a concrete diff hunk.
- id: G-06
  symptom_ref: F-06
  component_ref: Max Escalation
  root_cause: Routine coordination was escalated instead of using peer tools.
  repair_entry_point: peer_msg_send kind=request
  change_pattern: Convert routine asks into peer request/response messages; escalate to Max only for strategic forks, cost/timeline scope changes, destructive operations, or cross-instance unblocks.
  rollback_procedure: Send Max a concise correction if a routine ask was already surfaced.
  integrity_check: Max-facing thread contains only genuine decisions or unblocks.
```

## §H. Evolve

### §H.1 Invariants

- Vulcan and Mars are peers of equal authority over shell, git, dispatch, and Living State.
- No instance assigns, approves, audits-as-supervisor, or closes for the other instance.
- There is no primary/worker, no parent session, no `.W` derivation, no lanes, and no close ordering.
- Sessions open and close independently with `kd_session_open(instance="vulcan")` or `kd_session_open(instance="mars")`.
- Claim-before-work requires both a successful CAS status transition and a `kind=claim` peer-bus message.
- CAS failure or an unread competing claim means the item is already taken.
- The peer bus is drained at open, before dispatch, before merge, and before close.
- `request` and `alert` messages require acknowledgement.
- Max escalation is reserved for strategic forks and cross-instance unblocks.

### §H.2 Change-class predicates

BREAKING if any proposed change:
- Reintroduces primary/worker authority, work lanes, parent/worker session IDs, or close ordering.
- Allows work to begin without CAS claim plus peer-bus claim.
- Lets one instance approve, assign, or supervise the other instance's work.
- Removes ack requirements for `request` or `alert` messages.

REVIEW if any proposed change:
- Adds a new peer-bus message kind.
- Changes claim-note schema, ack semantics, or bus drain timing.
- Changes Max escalation boundaries.
- Changes runbook governance for process BQ consolidation.

SAFE otherwise:
- Documentation wording that preserves the invariants.
- Additional examples or scenario coverage.
- Narrow clarifications to shell, git, or dispatch hygiene.

## §I. Acceptance Criteria

```yaml scenarios
- id: E-CLAIM-01
  weight: 0.10
  prompt: "Mars wants to start BQ-X after opening."
  expected_first_action: "Drain peer_msg_inbox, then read the BQ entity and CAS-claim before work."
- id: E-CLAIM-02
  weight: 0.10
  prompt: "Vulcan's CAS claim succeeds."
  expected_first_action: "Send a kind=claim peer-bus message with scope and CAS evidence."
- id: E-DRAIN-03
  weight: 0.10
  prompt: "A peer is about to dispatch MP."
  expected_first_action: "Drain peer_msg_inbox and resolve unread claim/request/alert messages first."
- id: F-CONFLICT-01
  weight: 0.10
  prompt: "Both peers seem active on the same branch."
  expected_first_action: "Read entity/history, drain bus, and identify the successful CAS claimant."
- id: F-CAS-02
  weight: 0.10
  prompt: "CAS expected_version fails."
  expected_first_action: "Treat item as already taken and re-read state before any work."
- id: F-STALE-03
  weight: 0.10
  prompt: "Handoff says a gate is open, but the branch may have shipped."
  expected_first_action: "Verify Living State and origin/main before acting."
- id: G-BUS-01
  weight: 0.10
  prompt: "A request message was unread before merge."
  expected_first_action: "Pause merge, ack/respond, and resolve the request."
- id: G-FOLD-02
  weight: 0.10
  prompt: "A builder claims five findings fixed."
  expected_first_action: "Verify each finding against the actual diff and split unsupported work."
- id: H-BREAKING-01
  weight: 0.10
  prompt: "Proposal: Mars must close before Vulcan closes."
  expected_first_action: "Classify BREAKING."
- id: H-REVIEW-02
  weight: 0.10
  prompt: "Proposal: add a peer-bus kind named handoff."
  expected_first_action: "Classify REVIEW."
- id: AMB-01
  weight: 0.00
  prompt: "A peer sees stale handoff text and an unread claim for the same BQ."
  expected_first_action: "Drain/resolve the claim and verify Living State plus origin/main; do not start work."
```

The weighted ten-scenario set sums to 1.0. `AMB-01` is an explicit ambiguous-symptom guard and is unweighted until the harness supports overlapping scenario categories.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S870
last_refresh_commit: pending-this-commit
last_refresh_date: 2026-06-16T00:00:00+02:00
owner_agent: vulcan/mars
refresh_triggers:
  - peer bus tool contract changes
  - session lifecycle model changes
  - claim/CAS semantics changes
  - process-BQ consolidation changes
scheduled_cadence: 90 days
last_harness_pass_rate: not_run
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S870 2026-06-16
last_lint_result: "NOT_RUN - runbook-lint is not present in this repo; router_drift_check.py is the available guard for this change"
trace_matrix_path: null
word_count_delta: "retrofit rewrite and rename; old 1297 words, new 2233 words, +936 words (+72.2%)"
```

Router conformance is guarded by `scripts/router_drift_check.py`; the topic router must point to this filename and carry no dangling reference to the retired filename.
