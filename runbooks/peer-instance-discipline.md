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
  - signature: peer_runbook_context_delivery_unavailable
    section: §F. Isolate
  - signature: peer_runbook_impact_evidence_unavailable
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-31
system_name: peer-instance-discipline
purpose_sentence: Peer-symmetric session lifecycle and coordination discipline for the trusted Vulcan and Mars instances, including automatic runbook context and backend-owned close evidence.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Equal-authority instance behavior; automatic plan and child runbook delivery; backend-owned close evidence; claim-before-work coordination; peer-message bus delivery semantics; boot-state verification; and escalation boundaries.
linter_version: 1.0.0
---

<!-- Canonical source path: runbooks/peer-instance-discipline.md -->

# Peer Instance Discipline

## §A. Header

The YAML frontmatter above is the §A header. This runbook supersedes the retired Primary/Worker discipline: `vulcan` and `mars` are two cooperating instances of the same frontier model with equal authority over shell, git, dispatch, and Living State.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Independent instance open/plan/close surface | SHIPPED | `koskadeux-mcp/tools/session.py` | Exact connected-schema plus read-only gateway-health probes | 2026-07-31 |
| Automatic one-call plan context and exact retry | PLANNED | `koskadeux-mcp/tools/runbook_delivery.py` | Immutable corpus, byte-identical retry, and no-prior-write tests | 2026-08-02 |
| Backend-measured impact, obligations, and transaction-scoped committed receipt | PLANNED | `ai-market-backend/app/services/runbook_close_v2_service.py` | Trusted collector, remote-ref, crash/retry, obligation, and receipt tests | 2026-08-02 |
| Physical retirement of caller consultation/refs/exit and local gate authority | PLANNED | `koskadeux-mcp/tools/session.py` | Fresh-schema and no-old-symbol/file/store/fallback tests | 2026-08-02 |
| Peer message bus | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_msg_send` | Manual drain verified S835 | 2026-06-16 |
| Peer bus inbox drain | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_msg_inbox` | Manual drain verified S835 | 2026-06-16 |
| Instance status lookup | SHIPPED | `koskadeux-mcp/tools/peer_bus.py:peer_status` | Manual status lookup verified S835 | 2026-06-16 |
| Living State CAS claim | SHIPPED | `state_request:bq_update` | Optimistic versioning exercised by BQ lifecycle | 2026-06-16 |
| Primary/Worker lanes and close ordering | DEPRECATED | `session-open-protocol.md:O.3` | Retired by symmetric-peer model | 2026-06-16 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Peer Instance | `kd_session_open(instance=vulcan or mars)` | `registry.db` instance rows, per-instance handoff | Living State, shell, git, Council dispatch | Either instance may open first, plan independently, work any item, and close independently. |
| Plan Context Boundary | Connected `kd_session_plan` schema | Immutable delivery and accepted-plan receipt | Backend-approved exact runbook activation and all-corpus search | One ordinary request supplies complete context and accepts the plan; unchanged lost-response retry is byte-identical. No caller runbook fields exist. |
| Close Impact Boundary | Connected `kd_session_close` schema and close-status surface | Backend session/action evidence, obligations, handoff, outbox, signed receipt | GitHub, Railway, database/provider audit state, runbooks remote | Gateway transports PREPARE/COMMIT. Semantic obligations are nonblocking; trusted mechanical failures write nothing. No caller impact/exit fields or local authority exist. |
| Claim Transition | `state_request action=bq_update` | `build:bq-*` entity version, status, gate, assignee fields | Build Queue lifecycle | Work starts only after a CAS status transition succeeds against the version just read. |
| Peer Message Bus | `peer_msg_send` / `peer_msg_inbox` | peer-bus messages keyed by recipient, sender, kind, and ack state | Vulcan, Mars | Claim/status/request/response/alert messages coordinate work without Max relay. |
| Dispatch Surface | `council_request` / `dispatch_mp_build` | dispatch tasks, BQ entity refs, branch state | MP builder; exact CC/Kimi/GLM voters | The measured connected schema is stale because it omits Kimi and exposes inactive AG/DeepSeek. Treat roster-dependent work as UNAVAILABLE until the signed runtime and refreshed schema prove MP build-only, exact CC/Kimi/GLM review/Hall, and AG/DeepSeek rejection. |
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
| AG | Inactive; ordinary Council and Hall reject it | no Council tool | None | GAP — release must prove schema/runtime rejection |
| DeepSeek | Inactive and retired; ordinary Council and Hall reject it | no Council tool | None | GAP — release must prove schema/runtime rejection |
| Max | Strategic adjudication | direct instruction | Business/product owner | COMPLETE |

## §E. Operate

### First action after `kd_session_open`

Submit one ordinary `kd_session_plan` request with objectives and routing. The
accepted response automatically contains complete immutable context; read it
before calling work tools and amend the plan when verified guidance changes the
approach. Do not pass runbook paths, sections, references, consultations, gap
IDs, attestations, waivers, or desired impact outcomes. An unchanged
lost-response retry must return identical bytes. Child dispatch context is also
automatic and cannot be supplied or suppressed by the caller.

The first accepted response identifies itself with `response_kind=first_plan`,
returns the exact `open_obligations` snapshot searched with the plan, and labels
safe-to-read but semantically unverified excerpts with
`guidance_action_authority=false`. Read those excerpts as grounded guidance,
then verify any load-bearing action against its owning system; the label must
never be promoted by caller assertion.

Close a session with no caller runbook declaration while the server derives
truthful impact evidence. Pass only the ordinary session, instance, summary,
reason, and handoff.
The server owns baselines, action/provider evidence, impact classification,
obligations, coverage, PREPARE/COMMIT, and the signed receipt. A REQUIRED or
semantic UNCERTAIN result creates one visible nonblocking obligation; it does not
force filler or block the truthful close. That OPEN obligation does block the
next behavior-changing action for its component while diagnostics and runbook
remediation remain allowed.

A mechanical evidence failure returns `prepare_blocked` and writes no partial
close state. A successful PREPARE is `PREPARED`; only the matching exact COMMIT
may produce the `committed_receipt` and final `COMMITTED` state.

There is no compatibility branch. If a freshly listed schema exposes
`runbook_consultation`, `runbook_refs`, `runbook_impact`, or `runbook_exit`, or a
gateway process can use local gate/journal state, stop mutation and repair the
incomplete one-way cutover.

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
  pre_conditions: [connected_plan_schema_inspected, signed_cutover_status_verified, objectives_known]
  tool_or_endpoint: kd_session_plan(session_id=<session>, objectives=<objectives>, delegation_strategy=<strategy>, tool_budget=<budget>)
  argument_sourcing:
    objectives_and_strategy: use the assigned task and intended routing without adding a runbook filename citation or desired impact result
    runbook_context: do not supply it; the gateway validates the backend-approved exact activation searches every objective and returns complete context in the accepted response
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: session_id + exact canonical request digest + plan revision
  expected_success:
    shape: one PLAN_ACCEPTED response_kind=first_plan result contains complete immutable context, open_obligations, guidance_action_authority labels, and the accepted receipt
    verification: read the context before work confirm exact activation/request/response identities and prove an unchanged lost-response retry is byte-identical
  expected_failures: [{signature: peer_runbook_context_delivery_unavailable, cause: exact activation runtime corpus signed status or complete response could not be verified}]
  next_step_success: Drain the peer inbox with E-01, then act only on context and load-bearing facts that were actually read and verified.
  next_step_failure: Stay in PLANNING; use G-09 and do not add caller evidence or use a local/stale fallback.
- id: E-10
  trigger: An instance is ready to close and the backend must derive impact from trusted evidence.
  pre_conditions: [peer_inbox_drained, owned_work_preserved_on_action_bound_remote_refs, connected_close_schema_inspected]
  tool_or_endpoint: kd_session_close(instance=<self>, session_id=<session>, reason=<reason>, summary=<measured_summary>, handoff_content=<database_handoff>)
  argument_sourcing:
    ordinary_close_fields: derive from the named instance and verified work result without adding a runbook decision evidence waiver or discharge claim
    backend_evidence: the backend owns session baselines action/provider observations evaluator obligations coverage and PREPARE/COMMIT
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: session_id + exact close request digest
  expected_success:
    shape: PREPARED evidence is revalidated and one signed immutable transaction-scoped committed_receipt establishes COMMITTED plus typed nonblocking obligation outcomes
    verification: verify backend signature session request evidence freeze transaction handoff obligations and outbox identities; local files and prose are not truth
  expected_failures: [{signature: prepare_blocked, cause: trusted collector publication ref or mechanical integrity evidence failed before PREPARE and therefore wrote nothing}, {signature: peer_runbook_impact_evidence_unavailable, cause: exact COMMIT revalidation failed after PREPARED}]
  next_step_success: Report any visible OPEN obligation without writing filler; it will constrain the next behavior-changing action for that component.
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
| F-09 | `peer_runbook_context_delivery_unavailable`, incomplete context, or changed bytes on an unchanged retry. | Activation/runtime/corpus/status identity failed, response exceeded its complete budget, or retry identity omitted a semantic field. | Inspect exact request, signed status, activation/catalog/manifest/inventory/source/runtime identities, byte count and response digest; prove zero prior semantic writes. | G-09 | CONFIRMED |
| F-10 | `peer_runbook_impact_evidence_unavailable`, or close status cannot prove one scoped committed transaction. | Trusted collector/publication/mechanical validation failed, COMMIT remote state drifted, or an unscoped/local row was treated as authority. | Inspect backend PREPARE/COMMIT status and provider/ref evidence; verify failure wrote no freeze/obligation/handoff/outbox/receipt or that a retry returns the same committed receipt. | G-10 | CONFIRMED |

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
  root_cause: The one-call immutable context contract or exact retry identity cannot be authenticated or completed.
  repair_entry_point: connected kd_session_plan adapter signed cutover status and pinned runbook runtime/corpus
  change_pattern: remain in PLANNING repair the exact named status runtime object budget or request-digest defect and retry the unchanged ordinary request without caller runbook fields
  rollback_procedure: use a previously signed version-2 deployment only if it preserves the one-way freeze; never restore a legacy field or stale/local corpus path
  integrity_check: the ordinary plan returns complete context before semantic writes and an unchanged lost-response retry returns byte-identical content
- id: G-10
  symptom_ref: F-10
  component_ref: Close Impact Boundary
  root_cause: Trusted mechanical evidence or transaction revalidation failed or local/caller state was mistaken for backend close truth.
  repair_entry_point: backend close-v2 collector PREPARE COMMIT and signed receipt status through the gateway adapter
  change_pattern: leave the session open repair the exact collector ref credential role or drift failure and retry the identical close request; semantic uncertainty remains a nonblocking OPEN obligation
  rollback_procedure: no semantic rollback exists for a zero-write failed PREPARE; never substitute local journal state or caller impact prose
  integrity_check: one signed scoped COMMITTED receipt covers handoff obligations outbox and session close atomically and unchanged retry returns it
```

## §H. Evolve

### §H.1 Invariants

Vulcan and Mars are peers of equal authority over shell, git, dispatch, and Living State. Neither assigns, approves, supervises, or closes for the other. Work starts only after both a successful compare-and-swap claim and a peer-bus claim message. The bus is drained at open, before dispatch, before merge, and before close. Messages of kind request and alert require acknowledgement. Max is escalated to for strategic forks and cross-instance unblocks, not for routine coordination. Automatic context and backend close truth are accepted only from the exact signed deployed contract and scoped receipts. Caller consultation, refs, impact, exit, waiver, local journal, and legacy fallback surfaces remain absent.

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
  - {id: I-14, type: operate, refs: [E-09], scenario: A session has opened and the agent knows objectives but no runbook filename., expected_answers: [{kind: human_action, verb: submit, object: one ordinary objective-bearing plan with no runbook fields, target: automatic complete context in PLAN_ACCEPTED}], weight: 0.0666666667}
  - {id: I-15, type: operate, refs: [E-10], scenario: Close finds semantic uncertainty after all trusted mechanical evidence succeeds., expected_answers: [{kind: classification, label: COMMIT_WITH_ONE_VISIBLE_OPEN_OBLIGATION_AND_NO_FILLER}], weight: 0.0666666662}
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
