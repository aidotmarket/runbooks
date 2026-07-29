---
runbook_id: session-operations
domain: session-lifecycle
status: DRAFT
authoritative_for:
  - topic: session-open
    section: §E. Operate
  - topic: session-plan
    section: §E. Operate
  - topic: session-close
    section: §E. Operate
aliases: [session-open-protocol, session-close-protocol]
error_signatures:
  - signature: PLANNING_GATE
    section: §F. Isolate
  - signature: BOOT_NON_TRUNCATABLE_OVER_BUDGET
    section: §F. Isolate
  - signature: no_active_session_for_id
    section: §F. Isolate
  - signature: instance must be one of
    section: §F. Isolate
supersedes: [session-open-protocol, session-close-protocol]
superseded_by: []
owner: mars
last_verified_at: 2026-07-29
system_name: session-operations
purpose_sentence: Open, plan, operate, and close registered ai.market sessions without crossing instance boundaries or treating stale client labels as roster truth.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: The operator procedure for registered session open, planning-gate discharge, current-session operation, and authorized instance-scoped close.
linter_version: 1.0.0
---

# Session Operations

> Phase 2 Chunk A plus bounded Chunk B continuation draft. The source files
> remain in place until containment, reference checks, valid lint, and a non-author
> review are complete. While this header says DRAFT, this file is not catalog
> authority and must not change generated catalog surfaces.

## §A. Header

The frontmatter supplies the required header fields. Ground truth wins over this
document: the active roster comes from 'config:instance-registry', the current
handoff from 'infra:handoff:instance=<instance>', and session state from the
session registry.

Read-only checks on 2026-07-29 found that roster v2 lists Vulcan, Mars, and Athena.
The identity gate deployed at 'fd768e0d' accepts Athena for session open and
explicitly identified shell operations. The peer-message client still rejects
Athena with HTTP 422 and 'instance must be one of: mars, vulcan'. Athena's
close/handoff path can address the wrong instance, so Athena must not call
'kd_session_close' until the defect is repaired and independently verified.
These are consumer defects, not evidence for rewriting the roster as two-party.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Registered-instance session open | PARTIAL | `koskadeux-mcp:kd_session_open` | Live Athena open; implementation path not inspected in this docs-only promotion | 2026-07-29 |
| Instance-keyed planning gate | SHIPPED | `koskadeux-mcp:kd_session_plan` | Live S1389 rejected-then-accepted plan | 2026-07-29 |
| Instance-scoped handoff read | PARTIAL | `state_request:get infra:handoff:instance=<instance>` | Athena handoff v4 read directly; open misrouting remains known | 2026-07-29 |
| Instance-scoped close for Vulcan and Mars | PARTIAL | `koskadeux-mcp:kd_session_close` | Source-supported current path; not reverified in this docs-only promotion | 2026-07-29 |
| Instance-scoped close for Athena | BROKEN | `koskadeux-mcp:kd_session_close` | Deployed handoff-key collapse remains live; no Athena close attempted | 2026-07-29 |
| Peer-inbox drain before close | PARTIAL | `peer_msg_inbox` | Current client rejects Athena with HTTP 422 | 2026-07-29 |
| Boot-size protection | PARTIAL | `koskadeux-mcp:BOOT_WIRE_BUDGET_CHARS` | Source records 64,000 characters; implementation not inspected | 2026-07-29 |

PARTIAL rows state their gap. No row claims implementation-level verification
because Athena's charter limits this work to documents.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Active-instance roster | 'state_request get config:instance-registry' | Living State roster entity | Identity gate and session tools | Canonical for membership; client enum text may lag it. |
| Session open | 'kd_session_open(instance=<registered-instance>)' | Session registry and handoff | Constitution, briefing, health | Creates or reopens the named instance's session and returns its boot payload. |
| Planning gate | 'kd_session_plan(session_id=<sid>, ...)' | Instance/session boot state | Runbook resolver and gated tools | Success moves the named live session from PLANNING to OPERATIONAL. |
| Handoff | 'state_request get infra:handoff:instance=<instance>' | Per-instance Living State entity | Session open and close | Read the exact key if open payload identity is suspect. |
| Peer message bus | 'peer_msg_inbox(instance=<instance>)' | Peer-message store | Open and pre-close checks | Athena support is not deployed as of 2026-07-29. |
| Session close | 'kd_session_close(session_id=<sid>, instance=<instance>, ...)' | Registry, handoff, audit surfaces | Repository preflight and inbox | Requires Max's explicit consent and a verified instance-safe path. |
| Registry recovery | 'runbooks/session-registry-recovery.md' | Registry and related state | Open and close | Separate authority for diagnosis and recovery. |

Session and instance identifiers are separate. Reopening the same pair is
recovery; opening a different live session id against an occupied instance can
be a liveness collision. A missing instance is not permission to guess one.

The Registry recovery path above is a DRAFT forward reference: the destination
runbook has not yet been promoted at this commit. References to that path,
build:bq-agent-identity-n-peer-roster-s1374, and peer-instance discipline must resolve in the full reference scan
before this document can become ACTIVE.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Registered operator | Open its own session | 'kd_session_open' | Its own roster identity | COMPLETE |
| Registered operator | Plan its own session | 'kd_session_plan' | Its own live session | COMPLETE |
| Vulcan or Mars | Close its own authorized session | 'kd_session_close' | Its own verified identity | PARTIAL — closes when instance-safe verification is complete |
| Athena | Close its own session | 'kd_session_close' | None while defect is live | GAP — do not call; build:bq-agent-identity-n-peer-roster-s1374 owns repair |
| Registered operator | Read its handoff | 'state_request get' | Readable Living State | COMPLETE |
| Registered operator | Drain its inbox | 'peer_msg_inbox' | Its own identity | PARTIAL — client rejects Athena |
| Max | Authorize close or rule on identity ambiguity | Human decision | Final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A registered operator begins a session or recovers after a gateway restart.
  pre_conditions: [instance_name_known, roster_membership_verified]
  tool_or_endpoint: kd_session_open
  argument_sourcing:
    instance: Read the exact key from config:instance-registry; never infer it from stale client text.
    session_id: Use the assigned S-number when one exists; otherwise follow the current allocation contract.
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: instance plus session_id
  expected_success:
    shape: Boot payload with session id, constitution, handoff context, business briefing, health, and planning requirement.
    verification: Confirm the returned session and instance; if handoff identity is suspect, read the keyed handoff directly.
  expected_failures:
    - signature: instance must be one of
      cause: A client surface has a stale roster or the supplied instance is inactive.
    - signature: BOOT_NON_TRUNCATABLE_OVER_BUDGET
      cause: The protected boot floor exceeds the configured wire budget.
  next_step_success: Read the binding handoff and charter fully, then submit E-02.
  next_step_failure: Stop on identity or database failure and report the exact error; do not substitute another instance.
- id: E-02
  trigger: Session open returned PLANNING state.
  pre_conditions: [session_open_succeeded, binding_handoff_read, governing_runbooks_consulted]
  tool_or_endpoint: kd_session_plan
  argument_sourcing:
    session_id: Copy exactly from E-01.
    objectives: Derive from handoff, Max's instruction, and verified queue state.
    work_type: Classify the planned work without downgrading structural work to evade a gate.
    delegation_strategy: State what is direct and what is delegated.
    runbook_consultation: Cover every objective with a RunbookRef or honest no_entry_found entry.
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: session_id plus plan or amendment payload
  expected_success:
    shape: The named session transitions from PLANNING to OPERATIONAL.
    verification: The next in-scope tool call does not return PLANNING_GATE.
  expected_failures:
    - signature: PLANNING_GATE
      cause: The plan was not accepted, the gateway restarted, or objective coverage is incomplete.
  next_step_success: Verify the DB-owned pickup target and begin the highest-priority eligible owned work.
  next_step_failure: Correct the rejection detail; after restart, reopen the same pair and resubmit.
- id: E-03
  trigger: A plan or amendment needs runbook coverage.
  pre_conditions: [objective_list_final, runbooks_repo_readable]
  tool_or_endpoint: kd_session_plan.runbook_consultation
  argument_sourcing:
    path: Resolve an existing path from git truth.
    section: Use an exact heading, anchor, or section token present in that file.
    covers: Use one-based objective numbers from the current plan or amendment.
    no_entry_found: Use only after a real search finds no governing entry, with subject and reason.
  idempotency: IDEMPOTENT
  expected_success:
    shape: Every objective is covered by at least one resolved reference or explicit attestation.
    verification: The planning gate accepts without uncovered-objective detail.
  expected_failures:
    - signature: PLANNING_GATE
      cause: A path or section does not resolve, or an objective is uncovered.
  next_step_success: Preserve the consultation as the operating basis.
  next_step_failure: Correct path, section, or covers; do not manufacture absence.
- id: E-04
  trigger: Max explicitly authorizes a close or governing policy independently permits stopping.
  pre_conditions: [close_authorized, instance_safe_close_path_verified, owned_repo_state_accounted_for, handoff_prepared]
  tool_or_endpoint: kd_session_close
  argument_sourcing:
    instance: Use the current session's exact registered identity.
    session_id: Use the current session id.
    handoff_content: Record durable priorities, blockers, and exact refs.
    summary: State what landed and what remains.
    reason: State the real authorized reason.
    runbook_exit: Discharge plan-time runbook obligations honestly.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Only the named instance closes; its handoff and audits update; peers remain untouched.
    verification: Read close status and instance-scoped state before reporting completion.
  expected_failures:
    - signature: no_active_session_for_id
      cause: Wrong instance/session pair or partial close state.
    - signature: instance must be one of
      cause: The close client does not support the active roster identity.
  next_step_success: Report the verified instance-scoped result once.
  next_step_failure: Do not retry blindly or perform a manual close; inspect read-only status and route to the owner.
- id: E-05
  trigger: Athena reaches any condition that would normally lead to E-04.
  pre_conditions: [instance_is_athena]
  tool_or_endpoint: No close call while the Athena close/handoff defect remains live.
  argument_sourcing:
    defect_state: Read build:bq-agent-identity-n-peer-roster-s1374 or a superseding independently verified repair record.
  idempotency: IDEMPOTENT
  expected_success:
    shape: Athena remains open and reports close withheld because the path is unsafe.
    verification: No Athena kd_session_close audit exists from this attempt.
  expected_failures:
    - signature: no_active_session_for_id
      cause: A close was attempted despite the hold.
  next_step_success: Continue authorized work or await direction; preserve a lean coordination note.
  next_step_failure: Stop and report exact identity evidence without substituting Vulcan or Mars.
```

After E-02, prefer pending reviews and owned work before new queue work, then
take the highest-priority eligible unclaimed item. The five S612 BQ names in the
source are provenance, not a current priority list.

The source records a 64,000-character boot budget, protected non-truncatable
content, advisory trimming, a 'truncated' ledger, and 'boot_payload_fit'. This
promotion did not inspect implementation. Treat them as source-supported but
implementation-unverified. Keep handoffs lean; put durable detail in Living State.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Identity call says 'instance must be one of: mars, vulcan' for Athena. | Client roster is stale or subsystem widening is incomplete. | Read the canonical roster and exact owning repair record; do not infer inactivity from the label. | G-01 | CONFIRMED |
| F-02 | Open returns the wrong handoff or identity context. | Legacy default or wrong handoff key. | Read 'infra:handoff:instance=<intended-instance>' directly. | G-02 | CONFIRMED |
| F-03 | 'PLANNING_GATE' appears after a plan or restart. | Transition absent, wrong session id, or rejected coverage. | Check exact pair and objective coverage. | G-03 | CONFIRMED |
| F-04 | 'BOOT_NON_TRUNCATABLE_OVER_BUDGET' appears. | A protected component exceeds the boot floor. | Use returned size telemetry; do not trim protected content. |  | CONFIRMED |
| F-05 | Close returns 'no_active_session_for_id' or changes another handoff. | Wrong routing or partial close. | Use read-only close status and instance-scoped reads. | G-04 | CONFIRMED |
| F-06 | Athena peer-inbox drain returns HTTP 422. | Peer-bus widening is not deployed. | Preserve exact status/detail and read build:bq-agent-identity-n-peer-roster-s1374 state. | G-01 | CONFIRMED |
| F-07 | A live scratch session is present. | Dispatch or missing-instance machine session uses a reserved namespace. | Confirm it does not collide with a registered operator. |  | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Active-instance roster
  root_cause: A consumer-specific identity surface lags the canonical roster.
  repair_entry_point: The owning identity or peer-bus work item, not this docs branch.
  change_pattern: Record the exact failing tool and error, confirm membership, and route implementation work to its owner. Use an explicit instance argument only where an already-reviewed compatibility path requires it.
  rollback_procedure: Withdraw any claim that the client label is canonical; never impersonate another peer.
  integrity_check: The same tool accepts the identity and affects only that identity in an independent test.
- id: G-02
  symptom_ref: F-02
  component_ref: Handoff
  root_cause: Open resolved a legacy or wrong per-instance handoff key.
  repair_entry_point: Read-only lookup for infra:handoff:instance=<instance>, then the owning ticket.
  change_pattern: Use the correct handoff for planning, record the misroute, and leave the wrong handoff untouched.
  rollback_procedure: Discard conclusions drawn from the wrong handoff and replan from the correct one.
  integrity_check: Direct key read and future open return the same identity and version.
- id: G-03
  symptom_ref: F-03
  component_ref: Planning gate
  root_cause: The plan transition is absent for the current instance/session pair.
  repair_entry_point: kd_session_open and kd_session_plan for the same pair.
  change_pattern: Reopen after verified restart, resubmit full coverage, and make no gated call before acceptance.
  rollback_procedure: None; do not open under another instance.
  integrity_check: Plan succeeds and the next in-scope call is not rejected.
- id: G-04
  symptom_ref: F-05
  component_ref: Session close
  root_cause: Close addressed the wrong key or partially completed.
  repair_entry_point: kd_session_close_status and instance-scoped read surfaces.
  change_pattern: Stop retries, preserve evidence, and route to the lifecycle owner.
  rollback_procedure: No manual rollback is authorized; direct SQL or hand-built close events can compound damage.
  integrity_check: Intended state is recovered without modifying another instance.
```

Historical Primary/Worker manual-close and direct-lock procedures are not current
repairs. They remain in the source pending archival.

## §H. Evolve

### §H.1 Invariants

- The active roster is data, not a hard-coded two-instance list.
- An instance operates only as its own registered identity.
- Open, plan, and close state is scoped to the exact instance/session pair.
- Close requires authority and must not affect another instance.
- Identity or database failure never authorizes impersonation, direct SQL, or a
  manual close.
- This runbook grants no authority beyond CORE, Max's instruction, or charter.

### §H.2 BREAKING predicates

- Hard-code the operator roster or default a rejected identity to a peer.
- Make one instance's lifecycle call mutate another instance.
- Restore Primary/Worker slots, parent dependency, or '.W' session identifiers.
- Permit Athena close before the defect is independently cleared.

### §H.3 REVIEW predicates

- Change any session tool's public contract.
- Change roster, handoff, registry, peer-message, close-transaction, or boot-wire
  semantics.
- Change consultation coverage or close authorization.
- Add a registered operator.

### §H.4 SAFE predicates

- Clarify examples without changing contract or authority.
- Add an evidenced error signature.
- Refresh a verified defect state, date, or source reference.

### §H.5 Boundary definitions

#### module

Roster resolution, session open, planning gate, handoff, peer messaging, session
close, and registry recovery.

#### public contract

The named MCP signatures, lifecycle/identity result fields, Living State keys,
and instance-isolation guarantee.

#### runtime dependency

Gateway, session registry, Living State, runbook resolver, peer-message store,
and repository reads used by close preflight.

#### config default

No registered identity is supplied implicitly. Machine sub-sessions may use a
reserved namespace only when the live contract explicitly defines it.

### §H.6 Adjudication

The roster identifies intended membership, but a failed consumer operation
remains failed. Stop or use only an already-reviewed compatibility argument for
that exact tool. Session state beats prose. Any ambiguity that could address the
wrong identity escalates to Max and the lifecycle owner.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: Athena begins while client text lists only Vulcan and Mars., expected_answers: [{kind: tool_call, tool: kd_session_open, argument_keys: [instance]}], weight: 0.0833333333}
  - {id: I-02, type: operate, refs: [E-02], scenario: Open succeeded and state is PLANNING., expected_answers: [{kind: tool_call, tool: kd_session_plan, argument_keys: [session_id, objectives, delegation_strategy, runbook_consultation]}], weight: 0.0833333333}
  - {id: I-03, type: operate, refs: [E-03], scenario: Objective two is uncovered and plan rejects., expected_answers: [{kind: human_action, verb: cover, object: objective two, target: consultation}], weight: 0.0833333333}
  - {id: I-04, type: isolate, refs: [F-01], scenario: Bus rejects Athena while roster lists Athena., expected_answers: [{kind: classification, label: STALE_CONSUMER_ROSTER}], weight: 0.0833333333}
  - {id: I-05, type: isolate, refs: [F-02], scenario: Athena open returns a Vulcan handoff., expected_answers: [{kind: tool_call, tool: state_request, argument_keys: [action, key]}], weight: 0.0833333333}
  - {id: I-06, type: isolate, refs: [F-05], scenario: Close returns no_active_session_for_id after changing handoff state., expected_answers: [{kind: human_action, verb: stop, object: retries, target: read-only close status}], weight: 0.0833333333}
  - {id: I-07, type: repair, refs: [G-03], scenario: Restart causes PLANNING_GATE after accepted plan., expected_answers: [{kind: tool_call, tool: kd_session_open, argument_keys: [instance, session_id]}], weight: 0.0833333333}
  - {id: I-08, type: repair, refs: [G-04], scenario: Close may have addressed the wrong identity., expected_answers: [{kind: human_action, verb: preserve, object: evidence, target: lifecycle owner}], weight: 0.0833333333}
  - {id: I-09, type: evolve, refs: [§H.2], scenario: Omitted instance defaults to Vulcan., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0833333333}
  - {id: I-10, type: evolve, refs: [§H.4], scenario: Verified date refresh changes no procedure., expected_answers: [{kind: classification, label: SAFE}], weight: 0.0833333333}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: Roster lists Athena but identity tool rejects it., expected_answers: [{kind: human_action, verb: stop, object: failed operation, target: exact tool}], weight: 0.0833333333}
  - {id: I-12, type: operate, refs: [E-05], scenario: Athena is asked to close while misrouting remains live., expected_answers: [{kind: human_action, verb: withhold, object: kd_session_close, target: Athena session}], weight: 0.0833333337}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1389
last_refresh_commit: 4d0934b4b810ef5d09742bc3a82b95042c5495ef
last_refresh_date: 2026-07-29T00:00:00Z
owner_agent: mars
refresh_triggers:
  - Active-instance roster changes.
  - Session open, plan, close, handoff, peer-bus, or boot-wire contracts change.
  - The Athena peer-bus or close defect is repaired.
  - A lifecycle identity or partial-close incident is recorded.
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1389 / 2026-07-29T09:20:00Z
last_lint_result: FAIL
retrofit: true
trace_matrix_path: specs/ATHENA-PHASE2-CHUNK-A-TRACE-S1389.md
word_count_delta:
  before: 2698
  after: 3322
  pct: 23.13
```

### §K.1 Draft promotion gate ledger

This DRAFT is deliberately outside the generated catalog. Chunk B carries the
promotion state into the document so a later session does not mistake a clean
direct-check result for a promotable authority.

- **Containment:** the trace matrix accounts for every line of
  'session-open-protocol.md' (1–109) and 'session-close-protocol.md' (1–158).
  M3/M4 sources remain in place because live references still resolve to them.
- **Lint integrity blocker:** T-2026-000476 records that
  'rtk runbook-lint --mode strict runbooks/session-operations.md' exits 3 with
  'internal error: Parser must be a string or character stream, not NoneType'.
  Direct execution of all 21 strict checks returned zero findings, but that is
  diagnostic evidence, not a valid wrapper lint verdict. The §K result remains
  FAIL until the normal wrapper completes and reports its own result.
- **DRAFT isolation proof:**
  'specs/ATHENA-DRAFT-CATALOG-ISOLATION-PROOF-S1389.md' discharges CC mandate M1
  at evidence commit 'ae7195407a2c79a6a1bf834f397ac256d27eaaee'. The generator
  skips non-ACTIVE frontmatter before constructing entries; the loader rejects
  non-ACTIVE entries; and the resolver searches only validated entries/indexes
  with no path fallback. Populated draft authority metadata therefore has no
  canonical or supersession effect until status becomes ACTIVE and catalog
  generation runs. Explicit Git-path reads remain possible as review reads.
- **Inherited catalog drift:** the origin/main-derived worktree already drifts in
  'CATALOG.json' and 'TOPIC-ROUTER.md'. Regeneration would remove the three
  agent-dispatch §X.2 signatures 'repository_tool_call_batch_empty',
  'repository_tool_call_limit_exceeded', and
  'repository_tool_call_limit_violation_exhausted', and would move
  agent-dispatch 'last_verified_at' from 2026-07-28 back to 2026-07-26. Those
  unrelated generated changes were restored and are not folded into this draft.
- **Authorship correction:** the original remote commit
  'f18cc2aaf460049b4b93e73583c81478bb4c5ede' was backed up locally, rewritten as
  '72d119fb88b9de5f4c0e9e16f23f8ec49c8630c3', and force-pushed only to the docs
  branch. The replacement author and committer are 'athena <athena@ai.market>'.
- **Remaining content:** promote 'session-registry-recovery.md'; promote
  'peer-instance-discipline.md' while containing 'work-checkout.md' and
  'vulcan-configuration.md'; run the full old-path reference scan; then reconcile
  authority boundaries across the surviving documents.
- **Promotion order:** obtain a valid wrapper lint result, resolve or deliberately
  carry inherited catalog drift through the owning lane, resolve the two promoted
  forward paths, change coherent authorities from DRAFT to ACTIVE, regenerate
  generated surfaces with existing tooling, rerun the isolation probe at that
  exact promotion SHA, and obtain one non-author review on the exact final SHA.
- **Review state:** exact-head reviews at
  '32afa122cd951c757e9f95767729244ae424293c' are complete. CC task '40075d11'
  returned APPROVE with no mandates; GLM task 'b31c4448' returned
  APPROVE_WITH_NITS with no mandates, recorded by Mars at S1394 under event
  '53dac93e'. The nits are non-blocking and do not reopen Chunk A. The eventual
  ACTIVE/catalog change still requires review at its own exact final SHA.
- **Retirement hold:** no source moves until signed prerequisites, containment,
  link checks, generated-surface verification, and non-author review all pass.
