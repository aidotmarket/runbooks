---
runbook_id: peer-instance-discipline
domain: peer-coordination
status: ACTIVE
authoritative_for:
  - topic: instance-peer-topology
    section: §C. Architecture & Interactions
  - topic: peer-bus-coordination
    section: §E. Operate
  - topic: session-plan-runbook-context
    section: §E. Operate
  - topic: session-close-runbook-impact
    section: §E. Operate
aliases:
  - peer-bus
  - peer-message-bus
error_signatures:
  - signature: peer_message_silently_deduped
    section: §F. Isolate
  - signature: duplicate_claim_on_one_item
    section: §F. Isolate
  - signature: unread_request_or_alert_at_dispatch
    section: §F. Isolate
  - signature: stale_handoff_trusted_at_open
    section: §F. Isolate
  - signature: over_escalation_to_max
    section: §F. Isolate
  - signature: runbook_context_delivery_unavailable
    section: §F. Isolate
  - signature: runbook_impact_evidence_unavailable
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-31
system_name: peer-instance-discipline
purpose_sentence: Peer-symmetric session lifecycle and coordination discipline for the trusted Vulcan and Mars instances, including the deployed-versus-target runbook context and close-impact boundary.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Equal-authority instance behavior; verified deployed-versus-target open, plan, and close behavior; claim-before-work coordination; peer-message bus delivery semantics; boot-state verification; and escalation boundaries.
linter_version: 1.0.0
---

<!-- Canonical source path: runbooks/peer-instance-discipline.md -->

# Peer Instance Discipline

## §A. Header

The YAML frontmatter above is the §A header. This runbook supersedes the retired Primary/Worker discipline: `vulcan` and `mars` are two cooperating instances of the same frontier model with equal authority over shell, git, dispatch, and Living State.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Independent instance open/plan/close surface | SHIPPED | `connected kd_session_open, kd_session_plan, and kd_session_close schemas` | Exact connected-schema plus read-only gateway-health probes | 2026-07-31 |
| Legacy caller-authored plan consultation (harmful compatibility pending retirement) | SHIPPED | `connected kd_session_plan schema; config:runbook-gate-config v3` | Exact connected schema and config read | 2026-07-31 |
| Server-delivered objective-bound plan context (UNAVAILABLE) | PLANNED | — | No deployed lifecycle test | 2026-07-31 |
| Legacy caller-authored close declaration (harmful compatibility pending retirement) | SHIPPED | `connected kd_session_close schema; kd_session_close_status` | Exact connected schema and read-only close-status probe | 2026-07-31 |
| Server-measured runbook impact plus transaction-scoped committed receipt (UNAVAILABLE) | PLANNED | — | No deployed close-transaction test | 2026-07-31 |
| Peer message bus | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_msg_send` | Manual drain verified S835 | 2026-06-16 |
| Peer bus inbox drain | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_msg_inbox` | Manual drain verified S835 | 2026-06-16 |
| Instance status lookup | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_status` | Manual status lookup verified S835 | 2026-06-16 |
| Living State CAS claim | SHIPPED | `state_request:bq_update` | Optimistic versioning exercised by BQ lifecycle | 2026-06-16 |
| Primary/Worker lanes and close ordering | DEPRECATED | `session-open-protocol.md:O.3` | Retired by symmetric-peer model | 2026-06-16 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Peer Instance | `kd_session_open(instance=vulcan or mars)` | `registry.db` instance rows, per-instance handoff | Living State, shell, git, Council dispatch | Either instance may open first, plan independently, work any item, and close independently. |
| Plan Context Boundary | Connected `kd_session_plan` schema | Current legacy consultation input; future immutable delivery receipt | SHA-pinned runbook retrieval | Current deployment asks the caller to supply `runbook_consultation`; the server-delivered two-stage contract is PLANNED and must not be inferred from this runbook. |
| Close Impact Boundary | Connected `kd_session_close` schema and close-status surface | Current legacy exit declaration; future server-owned evidence transaction | Repository baselines, action receipts, runbooks remote | Current deployment exposes `runbook_exit`; structured `runbook_impact` and a transaction-scoped `COMMITTED` receipt are PLANNED and UNAVAILABLE. |
| Claim Transition | `state_request action=bq_update` | `build:bq-*` entity version, status, gate, assignee fields | Build Queue lifecycle | Work starts only after a CAS status transition succeeds against the version just read. |
| Peer Message Bus | `peer_msg_send` / `peer_msg_inbox` | peer-bus messages keyed by recipient, sender, kind, and ack state | Vulcan, Mars | Claim/status/request/response/alert messages coordinate work without Max relay. |
| Dispatch Surface | `council_request` / `dispatch_mp_build` | dispatch tasks, BQ entity refs, branch state | MP builder; connected `council_request` enum (`ag`, `mp`, `deepseek`, `glm`, `cc`); policy target CC/Kimi/GLM voters | Policy and connected schema currently disagree because the enum omits Kimi. Treat full-roster-dependent review and promotion as UNAVAILABLE; do not claim a successful full-panel dispatch until a signed deployed contract and the connected schema both prove the required roster. |
| Git/Shell Surface | shell plus git CLI | local worktree, `origin/main`, branches | target repos | Either peer may inspect, commit, merge, and push within the same authority boundaries. |
| Max Escalation | direct user thread | strategic decision record, BQ notes | Max | Used only for strategic forks or cross-instance unblocks agents cannot resolve. |

There are no lanes, ownership splits, primary approvals, worker audits, or close-order dependencies. Coordination is through state and the peer bus, not through assigning work to the other instance.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Open, claim, operate, schema-supported dispatch, merge, close | `kd_session_open(instance="vulcan")`, state tools, shell, git, dispatch tools | Full trusted-operator scope | PARTIAL — lifecycle authority is available; full-roster-dependent work is unavailable during the policy/schema mismatch |
| Mars | Open, claim, operate, schema-supported dispatch, merge, close | `kd_session_open(instance="mars")`, state tools, shell, git, dispatch tools | Full trusted-operator scope | PARTIAL — lifecycle authority is available; full-roster-dependent work is unavailable during the policy/schema mismatch |
| MP | Mandatory delegated builder; never a vote on its own work | `council_request(mode=build)`, `dispatch_mp_build` | Build scope | COMPLETE |
| CC/Kimi/GLM | Policy-target independent active gate voters | `council_request(mode=review)` | Read-only review at the exact SHA | GAP — connected `council_request` omits Kimi, so the required full panel is not currently callable and roster-dependent work is UNAVAILABLE |
| AG | Paused from the active panel; advisory only when current state explicitly permits | `council_request(mode=review)` | Non-gate read-only advice | PARTIAL — callable advisory path retained; active-panel coverage intentionally absent |
| DeepSeek | Retained callable backend, retired from active voting | `council_request` | Non-voter only | PARTIAL — callable backend retained; active-voter coverage intentionally retired |
| Max | Strategic adjudication | direct instruction | Business/product owner | COMPLETE |

## §E. Operate

### First action after `kd_session_open`

Inspect the exact connected `kd_session_plan` input schema and the exact signed
deployed-contract capability before choosing a planning path. Never infer rollout
state from this runbook, a prior session, or success-looking response prose.

- **Target branch — PLANNED and currently UNAVAILABLE.** Use this branch only
  when a valid signed deployed contract and the connected schema both expose
  objective-bound consultation IDs and gap IDs. The first plan attempt supplies
  objectives but no IDs and must return the typed non-success
  `RUNBOOK_CONTEXT_SELECTION_REQUIRED` without changing session state. Read the
  delivered excerpts, then resubmit the unchanged plan using only those
  server-issued IDs. A typed accepted receipt is the success signal.
- **Deployed compatibility branch — current and harmful.** The schema verified on
  2026-07-31 exposes caller-authored `runbook_consultation` and no consultation or
  gap IDs; the live gate configuration is block mode. Before planning, resolve a
  freshly fetched immutable runbooks `origin/main` SHA, search every objective
  against that one pin, read the returned ACTIVE excerpts, and submit exact
  existing path/section references. Use a truthful no-entry declaration only
  after an honest recorded miss. The declaration is compatibility input, not
  evidence that anything was read, and it must never trigger an invented path,
  synthesis, runbook, or filler update.

At close, make the same capability check. Structured server-owned
`runbook_impact` and a transaction-scoped `COMMITTED` receipt are target behavior
only. The current connected schema exposes legacy `runbook_exit`; provide only
the truthful compatibility value it requires. A reason string, author name, or
locally existing commit is not evidence of operational impact and must not cause
an unrelated documentation edit.

```yaml operate
- id: E-01
  trigger: An instance has opened a session and submitted its plan, and is ready to pick up work.
  pre_conditions: [session_opened_with_instance_name, kd_session_plan_completed]
  tool_or_endpoint: peer_msg_inbox(instance=<vulcan|mars>)
  argument_sourcing:
    instance: the active instance name used in kd_session_open, passed explicitly rather than inferred
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: every unread message for this instance is returned exactly once, and empty output means the bus is clear
    verification: re-running returns nothing, because delivery is at-most-once
  expected_failures: [{signature: inbox_unavailable, cause: gateway or registry is unreachable}, {signature: unread_request_or_alert_at_dispatch, cause: the drain was skipped or its output was not read before work started}]
  next_step_success: Run E-02 before trusting anything the handoff asserts, then choose candidate work.
  next_step_failure: Repair bus access or answer the outstanding peer messages before starting work.
- id: E-02
  trigger: The opening payload or handoff asserts a fact the session is about to rely on, such as a live peer task, a branch position, or a claimed boundary.
  pre_conditions: [boot_payload_read, load_bearing_claims_identified]
  tool_or_endpoint: peer_status plus direct git and process-table reads
  argument_sourcing:
    claims: take every load-bearing assertion from the handoff
    evidence: read the registry, the process table, and git against the remote rather than the narrative
  idempotency: IDEMPOTENT
  expected_success:
    shape: each load-bearing claim is confirmed or corrected against measured evidence
    verification: the corrected value is what the session proceeds on, and the correction is recorded
  expected_failures: [{signature: stale_handoff_trusted_at_open, cause: the handoff was written before the state changed and was taken as current}]
  next_step_success: Proceed on the verified state and record any correction on the affected entity.
  next_step_failure: Stop and re-derive the state before claiming or dispatching anything.
- id: E-03
  trigger: An instance intends to start any queue item, runbook revision, dispatch, or merge.
  pre_conditions: [peer_bus_drained, target_entity_read, current_entity_version_known, origin_main_checked]
  tool_or_endpoint: state_request(action=bq_update, bq_code=<code>, status=in_progress, note=<claimant_note>, session_id=<session>, gate_status_update=false, expected_version=<version>)
  argument_sourcing:
    code: BQ code or lifecycle item identifier from the queue
    version: entity version from the immediately preceding read
    note: active instance, session id, branch or file scope, and intended first action
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: target_entity + expected_version + active_instance
  expected_success:
    shape: the compare-and-swap transition succeeds and the entity records the claimant
    verification: read the entity back and confirm the claimant and version
  expected_failures: [{signature: duplicate_claim_on_one_item, cause: another peer already holds the item or a stale version was used}]
  next_step_success: Send the E-04 claim message, then begin work.
  next_step_failure: Treat the item as taken; pick another item or coordinate with the holder.
- id: E-04
  trigger: A compare-and-swap claim has succeeded and the peer needs to know the work boundary.
  pre_conditions: [cas_claim_succeeded, claim_scope_known]
  tool_or_endpoint: peer_msg_send(to=<peer|both>, kind=claim, ref_entity=<entity>, body=<scope>)
  argument_sourcing:
    to: the other peer, or both when it is not known which peer is live
    ref_entity: the claimed entity key
    body: claimant instance, session id, evidence, and the boundary the claim does not cross
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: from_instance + to_instance + kind + ref_entity
  expected_success:
    shape: the message is persisted and returned with an id
    verification: the returned row carries the id, kind, and ref_entity that were intended
  expected_failures: [{signature: peer_message_silently_deduped, cause: an earlier message shares the same sender, recipient, kind, and ref_entity, so this one is dropped without an error}]
  next_step_success: Work inside the claimed scope.
  next_step_failure: Re-send under a distinct ref_entity or kind and confirm a new id before proceeding.
- id: E-05
  trigger: An instance is about to dispatch another agent, merge a branch, or close its session.
  pre_conditions: [work_scope_claimed_or_read_only, local_git_status_known]
  tool_or_endpoint: peer_msg_inbox(instance=<vulcan|mars>)
  argument_sourcing:
    instance: the active instance, passed explicitly
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: no unread claim conflict, request, or alert remains
    verification: the drain returns nothing, or every returned message has been answered or acknowledged
  expected_failures: [{signature: unread_request_or_alert_at_dispatch, cause: a peer message arrived after the last drain and the dispatch would proceed blind to it}]
  next_step_success: Dispatch, merge, or close.
  next_step_failure: Answer or acknowledge the message first; a dispatch may be refused outright while an ack is pending.
- id: E-06
  trigger: A peer needs information, progress, a decision, or an urgent unblock.
  pre_conditions: [message_kind_selected, recipient_known, ref_entity_chosen]
  tool_or_endpoint: peer_msg_send(to=<vulcan|mars|both>, kind=<status|request|response|alert>, ref_entity=<distinct ref>, body=<message>)
  argument_sourcing:
    kind: claim for ownership; status for information only; request when an answer is needed; response when replying; alert when the peer must act
    ref_entity: a reference distinct from every earlier message of the same kind to the same peer
    body: the operational fact, the requested action, and the evidence
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: from_instance + to_instance + kind + ref_entity
  expected_success:
    shape: the persisted row is returned with a new id, and request and alert rows carry requires_ack
    verification: compare the returned id against the previous send and confirm it is new
  expected_failures: [{signature: peer_message_silently_deduped, cause: the tuple of sender, recipient, kind, and ref_entity repeats an earlier message; a changed body does not defeat it}, {signature: over_escalation_to_max, cause: a routine coordination fact was sent to Max instead of the peer}]
  next_step_success: Continue without assigning or approving the peer's work.
  next_step_failure: Vary ref_entity or kind, re-send, and confirm a new id.
- id: E-07
  trigger: A drained message of kind request or alert requires acknowledgement.
  pre_conditions: [message_read, message_id_known]
  tool_or_endpoint: peer_msg_ack(message_id=<id>)
  argument_sourcing:
    message_id: the id from the drained row
  idempotency: IDEMPOTENT
  expected_success:
    shape: the persisted row is returned with acked_at set
    verification: read the returned row and confirm acked_at is populated
  expected_failures: [{signature: unread_request_or_alert_at_dispatch, cause: the message was read but never acknowledged, so the sender and the dispatch gate still treat it as pending}]
  next_step_success: Proceed with the dispatch, merge, or close that the pending acknowledgement was blocking.
  next_step_failure: Re-read the inbox output for the correct id; acknowledging the wrong id leaves the original pending.
- id: E-08
  trigger: An instance needs to know whether the peer is live before coordinating, dispatching, or reloading anything shared.
  pre_conditions: [none]
  tool_or_endpoint: peer_status(instance=<optional>)
  argument_sourcing:
    instance: omit to return every registry row, or name one peer to inspect it alone
  idempotency: IDEMPOTENT
  expected_success:
    shape: registry rows carrying instance, session id, state, and last-seen time
    verification: a recent last-seen time with state OPERATIONAL means the peer is live
  expected_failures: [{signature: stale_handoff_trusted_at_open, cause: peer liveness was taken from the handoff narrative instead of the registry}]
  next_step_success: Coordinate on the measured peer state.
  next_step_failure: Treat peer liveness as unknown and take no action that a live peer would not tolerate.
- id: E-09
  trigger: An instance has opened and must obtain relevant runbook context before its plan can become operational.
  pre_conditions: [connected_plan_schema_inspected, exact_runbooks_origin_main_sha_resolved, objectives_known]
  tool_or_endpoint: kd_session_plan(session_id=<session>, objectives=<objectives>, delegation_strategy=<strategy>, tool_budget=<budget>, runbook_consultation=<truthful_legacy_refs_or_recorded_misses>)
  argument_sourcing:
    schema_branch: use the current compatibility call shown here only while the connected schema lacks server-issued consultation and gap IDs
    runbook_consultation: search every objective against one freshly fetched immutable origin/main pin; cite exact read path and section bytes, or record an honest miss without inventing content
    target_transition: when and only when the signed deployed capability exists, follow the typed two-stage branch above instead of this legacy input
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: session_id + exact ordered objectives + catalog SHA
  expected_success:
    shape: current compatibility plan is accepted only after truthful references or recorded misses cover the objectives
    verification: confirm the typed gate state is OPERATIONAL; response prose and the caller-authored consultation are not reading evidence
  expected_failures: [{signature: runbook_context_delivery_unavailable, cause: the connected schema has no server-issued consultation or gap IDs, or a signed capability cannot be verified}]
  next_step_success: Drain the peer inbox with E-01, then act only on context and load-bearing facts that were actually read and verified.
  next_step_failure: Stay in PLANNING; use G-09 and do not create a citation, attestation, or runbook merely to pass the gate.
- id: E-10
  trigger: An instance is ready to close and must report runbook impact without turning an unsupported declaration into evidence.
  pre_conditions: [peer_inbox_drained, changed_repositories_measured, connected_close_schema_inspected]
  tool_or_endpoint: kd_session_close(instance=<self>, session_id=<session>, reason=<reason>, summary=<measured_summary>, handoff_content=<database_handoff>, runbook_exit=<truthful_legacy_compatibility_value>)
  argument_sourcing:
    schema_branch: use runbook_exit only while the exact connected schema lacks structured runbook_impact and a transaction-scoped committed receipt
    runbook_exit: state only what is true under the legacy schema; a free-text reason or commit identifier is compatibility input and never semantic impact evidence
    target_transition: use structured impact only after the signed deployed capability proves it and the server supplies repository, action, configuration, and deployment evidence
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: session_id + exact close request digest
  expected_success:
    shape: legacy close returns success for the named instance without converting unsupported prose into a documentation claim
    verification: verify instance-scoped close state; only a future transaction-scoped COMMITTED receipt can establish target close truth
  expected_failures: [{signature: runbook_impact_evidence_unavailable, cause: structured impact or a scoped committed receipt was assumed from a legacy schema or unscoped close-status row}]
  next_step_success: Preserve any genuine documentation gap as a deduplicated follow-up; do not write filler after close.
  next_step_failure: Keep the session recoverable, inspect close status, and use G-10 without inventing an impact decision.
```

Delivery semantics that are easy to get wrong, all observed in use:

- `peer_msg_inbox` **consumes**. Delivery is at-most-once, so a drain is a deliberate act and its output must be read, not discarded. A second drain will not return the same messages.
- `peer_msg_send` **silently dedupes** on the tuple `(from_instance, to_instance, kind, ref_entity)`. A follow-up with a changed body and the same tuple is dropped and no error is raised. Vary `ref_entity` (or `kind`) for every distinct message and confirm the returned id is new.
- `peer_msg_send`, `peer_msg_inbox`, and `peer_msg_ack` take an explicit instance; do not rely on inference when more than one session could be live.
- `peer_status` is read-only and does not consume anything, so it is the safe way to check liveness at any time.
- A pending acknowledgement is not advisory. A dispatch may be refused before a task is even created while a peer message awaits acknowledgement.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Two peers appear to be working the same item | CAS was skipped, claim message unread, stale handoff was trusted | Read target entity version/history, drain peer bus, inspect branch/file overlap | G-01 | CONFIRMED |
| F-02 | CAS claim fails | Another peer already claimed, entity advanced, or stale version was used | Re-read entity and compare expected_version/status/claim note | G-02 | CONFIRMED |
| F-03 | Peer request or alert is discovered late | Bus was not drained at open, before dispatch/merge, or before close | Drain inbox and check ack-required messages | G-03 | CONFIRMED |
| F-04 | Work proceeds from stale handoff or queue addendum | Ground-truth verification skipped | Compare entity body, `origin/main`, branch list, and relevant artifact state | G-04 | CONFIRMED |
| F-05 | A multi-finding fold claims more than the diff proves | Builder output not checked line-by-line | Verify each claimed finding against actual diff at file/line | G-05 | CONFIRMED |
| F-06 | Max is asked to resolve routine execution details | Peer treated Max as dispatcher/approver instead of strategic owner | Review unresolved facts; check whether peer/status/request could answer | G-06 | CONFIRMED |
| F-07 | A peer message was sent successfully but the peer never received it | Send matched an earlier message on sender, recipient, kind, and ref_entity, so it was silently deduped | Compare the returned message id against the previous send; an unchanged or absent new id means the row was dropped | G-07 | CONFIRMED |
| F-08 | A dispatch is refused before any task is created | An unacknowledged peer request or alert is pending against this instance | Drain the inbox and check for rows carrying requires_ack that have no acked_at | G-08 | CONFIRMED |
| F-09 | `runbook_context_delivery_unavailable`, or planning expects server-issued IDs that the connected schema does not expose | Target guidance was mistaken for deployed capability, the client schema is stale, or the signed contract pin is absent | Inspect the exact connected `kd_session_plan` schema and signed deployed contract; current compatibility exposes `runbook_consultation` only | G-09 | CONFIRMED |
| F-10 | `runbook_impact_evidence_unavailable`, or close status cannot prove one scoped committed transaction | Target close semantics were inferred from prose, a legacy `runbook_exit`, or an old/unscoped pending row | Inspect the exact connected `kd_session_close` schema and instance/session-scoped status; require target fields and receipt type before claiming rollout | G-10 | CONFIRMED |

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
- id: G-07
  symptom_ref: F-07
  component_ref: Peer Message Bus
  root_cause: The bus dedupes on the tuple of sender, recipient, kind, and ref_entity, and a changed body does not defeat it, so a follow-up under a repeated tuple is dropped without an error.
  repair_entry_point: peer_msg_send
  change_pattern: Re-send with a ref_entity that is distinct from every earlier message of that kind to that peer, for example by suffixing the entity key with the task or subject the message is about, and confirm the returned row carries a new id.
  rollback_procedure: None; a deduped send has no side effect beyond the message never arriving.
  integrity_check: The returned message id differs from the previous send, and the peer's reply or acknowledgement references the intended ref_entity.
- id: G-08
  symptom_ref: F-08
  component_ref: Dispatch Surface
  root_cause: A pending peer acknowledgement is a hard precondition on dispatch, so the dispatch is refused before a task is created rather than failing later.
  repair_entry_point: peer_msg_ack
  change_pattern: Drain the inbox, acknowledge the pending request or alert by its id, then retry the dispatch and verify the returned task id before acting on it.
  rollback_procedure: None; a refused dispatch created no task, so nothing needs undoing.
  integrity_check: The inbox holds no requires_ack row without acked_at, and the retried dispatch returns a task id that is then confirmed to exist.
- id: G-09
  symptom_ref: F-09
  component_ref: Plan Context Boundary
  root_cause: The server-delivered context contract is not deployed or cannot be authenticated, while the current block-mode compatibility gate still expects caller-authored consultation input.
  repair_entry_point: exact connected kd_session_plan schema plus one freshly fetched runbooks origin/main snapshot
  change_pattern: Remain on the legacy branch; search each objective against the same full SHA, read the returned excerpt, and cite its exact path and section or record an honest miss. Never mint a consultation ID, claim a target receipt, or write filler to discharge legacy debt.
  rollback_procedure: Discard any caller-minted ID or unsupported citation and resubmit only grounded compatibility input.
  integrity_check: Every submitted reference resolves at the recorded full SHA, every miss has recorded search output, and no target capability is claimed.
- id: G-10
  symptom_ref: F-10
  component_ref: Close Impact Boundary
  root_cause: Legacy close input or an unscoped status row was treated as server-measured impact or a transaction-scoped committed receipt.
  repair_entry_point: exact connected kd_session_close schema and instance/session-scoped close-status evidence
  change_pattern: Use only the truthful legacy compatibility value, keep unsupported impact uncertain, and preserve a genuine gap as follow-up rather than changing unrelated documentation. Do not claim target completion until the signed schema and scoped COMMITTED receipt both exist.
  rollback_procedure: Retract the unsupported impact claim; leave the session recoverable and the documentation unchanged while evidence is missing.
  integrity_check: The close claim matches the deployed schema and scoped state, and no reason string, author name, or local object is treated as semantic evidence.
```

## §H. Evolve

### §H.1 Invariants

Vulcan and Mars are peers of equal authority over shell, git, dispatch, and Living State. Neither assigns, approves, supervises, or closes for the other. Work starts only after both a successful compare-and-swap claim and a peer-bus claim message. The bus is drained at open, before dispatch, before merge, and before close. Messages of kind request and alert require acknowledgement. Max is escalated to for strategic forks and cross-instance unblocks, not for routine coordination. A target plan or close shape is never treated as deployed until the exact signed contract and connected schema both prove it. Legacy consultation and exit declarations are compatibility input, never evidence that an agent read a runbook or that a documentation change was useful.

### §H.2 BREAKING predicates

Reintroducing primary and worker authority, work lanes, parent or worker session identifiers, or close ordering is BREAKING. So is permitting work to begin without both a compare-and-swap claim and a peer-bus claim, letting one instance approve or supervise the other's work, removing the acknowledgement requirement from request and alert messages, or claiming server-delivered context or transactional close while the signed deployed contract does not expose it.

### §H.3 REVIEW predicates

Review any new peer-bus message kind, any change to the dedupe tuple or to delivery semantics, any change to claim-note schema, acknowledgement handling, or drain timing, any plan-context or close-impact contract change, and any change to the Max escalation boundary.

### §H.4 SAFE predicates

Wording that preserves the invariants, additional scenario coverage, and narrower clarifications to shell, git, or dispatch hygiene are safe. So is automation that performs these same reads, provided the read still happens and its result is still what is acted on.

### §H.5 Boundary definitions

#### module

The instance registry, the session open/plan/close handlers, the peer message bus, the Living State claim transition, and the dispatch surface that refuses to proceed while an acknowledgement is pending.

#### public contract

The exact connected session schemas and signed deployed capability, the claim recorded on a Build Queue entity, and the peer message row returned by a send, identified by sender, recipient, kind, and ref_entity.

#### runtime dependency

Reachability of the gateway and the registry. Peer liveness is read from the registry, never inferred from a handoff.

#### config default

Absent evidence is absent. A bus that cannot be drained, or a peer whose liveness cannot be read, yields no permission to act; it does not yield a default of "clear".

### §H.6 Adjudication

Where a handoff and measured state disagree, measured state wins and the handoff is corrected in place. Where a send appears to have succeeded but the peer never received it, the returned message id decides, not the absence of an error.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: An instance has just opened a session and submitted its plan., expected_answers: [{kind: human_action, verb: drain, object: peer inbox, target: this instance before any work begins}], weight: 0.0666666667}
  - {id: I-02, type: operate, refs: [E-02], scenario: The handoff states that a peer build task is live and bounded for two hours., expected_answers: [{kind: human_action, verb: verify, object: task liveness, target: process table and registry rather than the handoff}], weight: 0.0666666667}
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: An instance intends to start a queue item it has just read and must leave claimant/audit evidence in the same compare-and-swap transition.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, bq_code, status, note, session_id, gate_status_update, expected_version]
        argument_values: {action: bq_update, status: in_progress, gate_status_update: false}
    weight: 0.0666666667
  - {id: I-04, type: operate, refs: [E-04], scenario: A compare-and-swap claim has just succeeded., expected_answers: [{kind: human_action, verb: send, object: claim message, target: the peer with the scope boundary stated}], weight: 0.0666666667}
  - {id: I-05, type: evolve, refs: [§H], scenario: A proposal changes the tuple the bus dedupes on without changing the drain or acknowledgement rules., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0666666667}
  - {id: I-06, type: isolate, refs: [F-07], scenario: A send returned without error but the peer never mentions the message., expected_answers: [{kind: classification, label: PEER_MESSAGE_SILENTLY_DEDUPED}], weight: 0.0666666667}
  - {id: I-07, type: isolate, refs: [F-08], scenario: A dispatch is refused before any task id is created., expected_answers: [{kind: classification, label: UNREAD_REQUEST_OR_ALERT_AT_DISPATCH}], weight: 0.0666666667}
  - {id: I-08, type: isolate, refs: [F-04], scenario: A session proceeds on a handoff assertion that the state has since overtaken., expected_answers: [{kind: classification, label: STALE_HANDOFF_TRUSTED_AT_OPEN}], weight: 0.0666666667}
  - {id: I-09, type: isolate, refs: [F-01], scenario: Two instances appear to be working the same item., expected_answers: [{kind: classification, label: DUPLICATE_CLAIM_ON_ONE_ITEM}], weight: 0.0666666667}
  - {id: I-10, type: repair, refs: [G-07], scenario: A follow-up message was dropped because it repeated an earlier tuple., expected_answers: [{kind: human_action, verb: resend, object: the message, target: a distinct ref_entity with the new id confirmed}], weight: 0.0666666667}
  - {id: I-11, type: repair, refs: [G-08], scenario: A pending acknowledgement is blocking a dispatch., expected_answers: [{kind: human_action, verb: acknowledge, object: the pending message, target: by its id before retrying the dispatch}], weight: 0.0666666667}
  - {id: I-12, type: evolve, refs: [§H], scenario: A proposal reintroduces close ordering between the two instances., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0666666667}
  - {id: I-13, type: ambiguous, refs: [§H.6], scenario: A handoff asserts a boundary is clear while an unread claim exists for the same entity., expected_answers: [{kind: human_action, verb: drain, object: the bus, target: before trusting the handoff, then act on measured state}], weight: 0.0666666667}
  - {id: I-14, type: operate, refs: [E-09], scenario: A session has opened and the connected plan schema exposes only caller-authored runbook_consultation., expected_answers: [{kind: human_action, verb: search, object: every objective at one immutable origin/main SHA, target: exact excerpts and truthful legacy references without invented content}], weight: 0.0666666667}
  - {id: I-15, type: operate, refs: [E-10], scenario: Close exposes only legacy runbook_exit while structured impact and a scoped committed receipt are unavailable., expected_answers: [{kind: human_action, verb: declare, object: only the truthful compatibility value, target: no unrelated runbook edit or unsupported impact claim}], weight: 0.0666666662}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1412
last_refresh_commit: 4b07429
last_refresh_date: 2026-07-31T10:00:00Z
owner_agent: mars
refresh_triggers: [peer bus tool contract changes, delivery or dedupe semantics changes, session lifecycle model changes, claim or compare-and-swap semantics changes, escalation boundary changes]
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1412 / 2026-07-31T10:00:00Z
last_lint_result: PASS
retrofit: true
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: {before: 2238, after: 3632, pct: 62.3}
```
