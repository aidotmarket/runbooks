---
runbook_id: gate-specification-authoring
domain: council-operations
status: ACTIVE
authoritative_for:
  - topic: gate-specification-authoring
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: unmeasured_figure_written_as_fact
    section: §E. Operate
  - signature: gate_result_trusted_without_deployed_sha_check
    section: §E. Operate
  - signature: verdict_read_from_legacy_payload
    section: §E. Operate
  - signature: spec_authored_against_stale_source
    section: §E. Operate
  - signature: builder_failure_report_contradicted_by_remote
    section: §G. Repair
  - signature: fold_lost_to_builder_timeout
    section: §G. Repair
  - signature: session_identity_unverified
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-26
system_name: gate-specification-authoring
purpose_sentence: How a Gate 1 or Gate 2 specification is authored and folded so that every claim in it carries whether it was observed, and nothing unobserved is written as fact.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Authoring and fold mechanics for Gate 1 and Gate 2 specifications: where a claim in a spec comes from, how it is marked observed or inherited, what must be re-read at source before it can be written down, how a Council verdict envelope is read, and how a fold dispatch fails.

  Not authoritative for gate transitions, verdict thresholds or dispatch eligibility (gate-procedure, council-gate-process); for dispatch transport, reviewer quirks or roster (agent-dispatch, council-roster-quirks); or for drift classification semantics (build-queue-reconciliation).

  Reference convention: same-file references use bare identifiers such as E-01; cross-file references use file-stem:id, for example council-gate-process:G-02.
linter_version: 1.0.0
---

# Gate Specification Authoring

## §A. Header

The frontmatter above is authoritative for catalog identity. **Authority: delivery companion.** Full CORE, the Boot Kernel, the approved design or specification for the item in hand, and live gate state all prevail over this document.

**Fetch trigger:** authoring a Gate 1 design, authoring a Gate 2 implementation specification, folding review mandates or peer findings into either, or reading a Council verdict on either.

**Source constitution:** CORE v9.12, SHA-256 `1c1147810c5b5dff125d7d5a9b0add1cce50420f03813bae3237162651c6299a`, delivered in the S1346 boot envelope and read there.

**Provenance convention used throughout this runbook.** Every load-bearing claim below is tagged.

- **OBSERVED** — read directly at a named source by the author of this runbook, at the SHA or timestamp given.
- **INHERITED** — carried from a handoff, event or peer message and *not* re-verified here. An inherited claim may be true. It is not evidence.

The convention is not decoration. It is the subject of this runbook applied to the runbook itself, and a reader is entitled to treat an untagged assertion as INHERITED.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Canonical-to-legacy verdict mapping | SHIPPED | `council_verdict_adapter.py` | Read at source; no assertion added here | 2026-07-26 |
| Declared dispatch bound in task metadata | SHIPPED | `tools/async_dispatch.py` | `test_invalid_bound_records_absence` | 2026-07-26 |
| Eligible-population read for spec figures | SHIPPED | `state_request` | `total_eligible` cross-checked against `returned` | 2026-07-26 |
| Drift classification on degraded evidence | BROKEN | `services/build_queue_reconciler.py` | Contested; see T-2026-000411 | 2026-07-26 |
| Spec claim provenance marking | PLANNED | — | Gate 1 design approved on BQ-VERIFIED-OR-FAIL-CLOSED-S1336 | 2026-07-26 |
| Deployed-server SHA verification | PLANNED | — | No tooling; manual procedure E-01 only | 2026-07-26 |
| Session and peer-bus identity verification | BROKEN | `tools/session.py` | None; defect T-2026-000412 | 2026-07-26 |

## §C. Architecture & Interactions

A gate specification is the artifact a Council panel votes on and a builder is measured against. Everything downstream inherits from it. A number that entered the spec unmeasured becomes a build that implements the wrong thing, an audit that passes it, and a production check that confirms it. The failure this runbook exists to prevent is therefore not a broken tool. It is a specification that reads as fact where nobody looked.

Three properties make a spec safe to vote on.

1. **Every decision-relevant claim carries its provenance.** Not a citation to a document, a statement of what was actually observed and when. "52 eligible items" is a claim; "52 eligible items, `assignment_query` with `include_peer_owned`, `returned` 52 and `has_more` false, 2026-07-26T10:26Z" is evidence.
2. **Absence is recorded as absence.** A specification that cannot establish something must say so in the text, not omit it. Omission reads downstream as "not applicable", which is a positive finding nobody made.
3. **The spec is written against the code as it is, or as it is contracted to become.** Never as it is remembered. Where a component is under concurrent repair, the spec states which behaviour it assumes and what happens if that repair does not land.

### Components

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Specification text | `specs/BQ-*-GATE*.md` | Claims, methods, code references, open questions | Council round | A claim without a method is inherited, not observed. |
| Verdict envelope | `council_verdict_adapter.py` | Canonical verdict, mandates, findings | Gate record | Read structured_payload; the legacy projection is lossy. |
| Fold dispatch wrapper | `council_request mode=build agent=mp` | Branch, commit, builder report | Specification text | The report can contradict the remote; the remote wins. |
| Async dispatch | `tools/async_dispatch.py` | Declared timeout and deadline metadata | Fold dispatch wrapper | The declared bound is a truthful declaration, not enforcement. |
| Session and peer-bus identity | `kd_session_open` and `peer_msg_send` | Session registry, updated_by, from_instance | Every record above | Identity is caller-asserted and verified by nothing. |

The actors: the authoring instance owns the text; MP is the mandatory builder for spec-fold dispatches and cannot review its own output; the Council panel votes; Living State holds gate status; Git holds the spec blob. Where Living State and a handoff disagree about gate state, Living State wins. Where Git and a builder's report disagree about what was pushed, Git wins (see G-01).

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Author and fold the specification, dispatch rounds, read verdicts | State and Council tools | Spec text and gate state | COMPLETE |
| MP | Build the fold on an approved dispatch | `council_request mode=build` | Repository write | COMPLETE |
| CC, GLM, Kimi | Review and vote independently | `council_request mode=review` | Read-only | COMPLETE |
| AG | Review with the diff inlined | `mode=open_response` | Read-only | PARTIAL — no repository read at SHA; closure tracked on BQ-COUNCIL-REPO-READ-PARITY-GLM-S1325 |
| Max | Approve constitutional-weight design and decide genuine forks | Human decision | Final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A gate round has returned and its outcome is about to be recorded.
  pre_conditions: [round_complete, dispatch_sha_known]
  tool_or_endpoint: git rev-parse origin/main plus the deployed process start time
  argument_sourcing:
    sha: read from the remote and never from the dispatch report
    process: confirm the server started after that SHA landed
  idempotency: IDEMPOTENT
  expected_success:
    shape: deployed SHA equals the SHA the specification describes
    verification: read both and compare
  expected_failures:
    - signature: gate_result_trusted_without_deployed_sha_check
      cause: deployed code was not established before the result was believed
  next_step_success: Record the outcome with the SHA in the specification body.
  next_step_failure: Mark the result UNVERIFIED and rerun the round pinned to a known SHA.
- id: E-02
  trigger: A reviewer verdict must be turned into a recorded round outcome.
  pre_conditions: [verdict_envelope_present]
  tool_or_endpoint: structured_payload on the review envelope
  argument_sourcing:
    verdict: read structured_payload only
    rationale: legacy_payload is a lossy projection with no approve-with-mandates value
  idempotency: IDEMPOTENT
  expected_success:
    shape: canonical verdict preserved including approve-with-mandates
    verification: compare the recorded outcome against the reviewer prose
  expected_failures:
    - signature: verdict_read_from_legacy_payload
      cause: approve-with-mandates was collapsed to REVISE by the compatibility mapping
  next_step_success: Record the canonical verdict and any mandates separately from lifecycle status.
  next_step_failure: Re-read the envelope and correct the recorded outcome in place.
- id: E-03
  trigger: A figure is about to be written into a specification.
  pre_conditions: [figure_identified]
  tool_or_endpoint: state_request action=assignment_query or the owning measurement surface
  argument_sourcing:
    value: produce it in this session from a named read
    method: record the call and its filters and its timestamp beside the value
  idempotency: IDEMPOTENT
  expected_success:
    shape: value and method recorded together
    verification: a reader can reproduce the figure from the method alone
  expected_failures:
    - signature: unmeasured_figure_written_as_fact
      cause: the figure arrived by handoff or peer message or summary and was written as observation
  next_step_success: Write the figure with its method.
  next_step_failure: Label the figure explicitly unmeasured or remove it.
- id: E-04
  trigger: A specification will alter or depend on existing code.
  pre_conditions: [target_repo_known, current_sha_fetched]
  tool_or_endpoint: git show origin/main path plus a trace of the actual call path
  argument_sourcing:
    behaviour: read the current source along the integration path
    prohibition: never author from memory or from a summarised state entity
  idempotency: IDEMPOTENT
  expected_success:
    shape: every code claim cites a source file and a SHA
    verification: re-read the cited lines at the cited SHA
  expected_failures:
    - signature: spec_authored_against_stale_source
      cause: the cited code has moved or never matched the description
  next_step_success: State which behaviour the specification assumes where a component is under concurrent repair.
  next_step_failure: Re-fetch and re-author the affected section before the round.
- id: E-05
  trigger: Content attributed to this instance or to a peer is about to be folded in.
  pre_conditions: [author_claimed]
  tool_or_endpoint: independent confirmation from the named author
  argument_sourcing:
    author: confirm out of band with the named instance
    rationale: frontmatter owner and updated_by and bus from_instance are writer-supplied claims
  idempotency: IDEMPOTENT
  expected_success:
    shape: the named author confirms authorship directly
    verification: peer acknowledgement or this session own record
  expected_failures:
    - signature: session_identity_unverified
      cause: any caller may assert an instance identity and nothing checks it
  next_step_success: Fold the content and record who wrote it.
  next_step_failure: Leave the content uncommitted and treat it as unattributed.
```

### E-01. Verify the deployed server SHA before trusting any gate result

A gate result produced by a server running code other than the code you read is not evidence about the code you read. Before accepting a round's outcome, confirm the deployed SHA and that the process serving the gate started after that SHA landed.

- OBSERVED: at S1346, `origin/main` of `koskadeux-mcp` moved from `4365fcf4` to `5a9ea9ed` inside a single working hour. A spec authored against the earlier SHA and reviewed after the move is reviewed against different code than it describes.
- INHERITED: this debt has been attested and carried since S1339 without a written procedure. That is why it is written here.

Procedure: record the SHA in the dispatch, pin the reviewer worktree to it (detached), and state the SHA in the spec body. If the deployed SHA cannot be established, the result is UNVERIFIED and fails closed.

### E-02. Read the structured verdict, never the legacy one

- OBSERVED at `council_verdict_adapter.py:9-13`, `origin/main` `4365fcf4`: `CANONICAL_TO_LEGACY_VERDICT` maps `APPROVE` to `PASS`, `APPROVED_WITH_MANDATES` to `REVISE`, and `REJECT` to `REJECT`. The reverse table additionally maps `REQUEST_CHANGES` to `APPROVED_WITH_MANDATES`.

The consequence is that a panel voting *approve with mandates* is recorded in the legacy vocabulary as `REVISE`, because that vocabulary has no approve-with-mandates value. Prose saying "approve" beside a field saying "REVISE" is therefore the mapping working as designed, not a reviewer contradiction and not a parser defect.

Read `structured_payload`. Never `legacy_payload`. A round logged from the legacy field is logged more negatively than the panel voted.

- INHERITED: at least two earlier rounds on BQ-VERIFIED-OR-FAIL-CLOSED-S1336 are believed to have been recorded this way. Not re-checked here; treat as an open audit item, not a finding.

### E-03. Measure before writing a number

No figure enters a specification unless one of the following is true.

1. You produced it in this session from a named read, and the spec records the method.
2. You reproduce it verbatim and label it explicitly as unmeasured.

A figure that arrived by handoff, by peer message, or by any summary of either is INHERITED and cannot be written as fact.

- OBSERVED at S1346, 2026-07-26T10:26Z: `state_request action=assignment_query`, `caller_instance=vulcan`, `filters.include_peer_owned=true`, `limit=200` returns `total_eligible` 52, `returned` 52, `has_more` false. Fifty-two is the eligible population and the spec may say so with that method recorded.
- OBSERVED: `bq_drift_report` in the S1346 boot envelope carries thirteen rows. It is a subset of the same population and any spec quoting it must say which.
- INHERITED and explicitly unmeasured: "3 of 52 carrying target_repos" and "94 percent". Both appear in the S1343 record; nobody has produced a measurement either way. Write them as unmeasured or re-derive them. Do not attribute them to a peer.
- OBSERVED, superseded figures: 41, "34 of 41" and "83 percent" came from a list endpoint that truncates (T-2026-000410). They are wrong and must not be carried forward.

### E-04. Trace the integration path before specifying a change to existing code

Read the current source along the actual call path. Never specify against memory or against a summarised state entity.

- OBSERVED at `services/build_queue_reconciler.py`, `origin/main` `4365fcf4`: the terminal `return Classification.ADVISORY_GIT_AHEAD, divergences, None` is a bare fall-through carrying no error code. The reconciler therefore reports a positive classification on a path where it established nothing.
- OBSERVED at the same file and SHA: `advisory_cap` is set from `error_code in {"build_queue_unreachable", "chunk_plan_unavailable"}` and *caps* the classification at advisory rather than escalating it. Degraded evidence produces a confident-looking advisory finding.

Both are the same shape as the failure in §C: a system reporting a finding it did not make. A spec that folds either must state which behaviour it assumes and what happens if the repair does not land first.

### E-05. Verify the identity of anything that wrote on your behalf

- OBSERVED at S1346: a builder subprocess called `kd_session_open` with `instance=vulcan` and then with `session_id=S1346`, a number already held by a live operator session, submitted its own `kd_session_plan` against it, and subsequently wrote to Living State with `updated_by=vulcan` and sent a peer message with `from_instance=vulcan`. Evidence in the Codex rollout for that run and in `infra:session-status:S1346:role=primary`, which carried seven runbook-debt entries from two different authors all stamped `instance=vulcan`.
- NOT ESTABLISHED: the same run is *not* shown by its own transcript to have created the worktree and runbook file that appeared during it. Adjacency in time is not authorship. That artifact remains unattributed.

Before folding any content attributed to yourself or a peer, confirm the author independently. Frontmatter, an `updated_by` field and a bus `from_instance` are all claims typed by a writer, not provenance records. Full account: T-2026-000412.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A number in the spec has no recorded method. | It arrived by handoff, peer message or summary and was promoted to fact. | Search the spec for figures lacking an adjacent method; attempt to reproduce each from the text alone. | G-01 | CONFIRMED |
| F-02 | A verdict field and the reviewer's prose disagree. | The outcome was read from the legacy projection, which has no approve-with-mandates value. | Re-read structured_payload on the same envelope and compare. | G-01 | CONFIRMED |
| F-03 | A builder reports the work was not preserved. | The wrapper discarded its own report while the commit and push in fact succeeded. | git ls-remote the branch and read the blob at the reported message. | G-02 | CONFIRMED |
| F-04 | A fold dispatch returns nothing at its time bound. | The builder banks no partial work and abandons the run at the bound. | Read the task metadata for the declared bound and the run duration. | G-03 | CONFIRMED |
| F-05 | Work is attributed to an instance that did not do it. | Session and bus identity are caller-asserted and unchecked. | Ask the named author directly; compare session registry start times against the write timestamps. | G-04 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Specification text
  root_cause: An inherited claim was recorded as an observation.
  repair_entry_point: The spec section carrying the claim
  change_pattern: Re-derive the value from its owning surface and record the method beside it, or relabel it explicitly unmeasured.
  rollback_procedure: Remove the claim rather than leave it unmarked.
  integrity_check: Every figure in the spec can be reproduced from its own recorded method.
- id: G-02
  symptom_ref: F-03
  component_ref: Fold dispatch wrapper
  root_cause: The wrapper's report contradicts the state of the remote.
  repair_entry_point: The feature branch on the remote
  change_pattern: Confirm the remote first; adopt the pushed commit if present and discard the failure report.
  rollback_procedure: Take no destructive action against the branch until the remote has been read.
  integrity_check: The canonical commit is identified by content, not by the builder's message.
- id: G-03
  symptom_ref: F-04
  component_ref: Async dispatch
  root_cause: The declared bound is informational and the builder banks no partial work.
  repair_entry_point: The dispatch call
  change_pattern: Pass an explicit bound, instruct the builder to commit early with gaps marked, and redispatch the remainder.
  rollback_procedure: Retain any partial commit rather than resetting the worktree.
  integrity_check: A redispatched fold starts from the committed partial, not from the beginning.
- id: G-04
  symptom_ref: F-05
  component_ref: Session and peer-bus identity
  root_cause: Instance identity is asserted by the caller and verified by nothing.
  repair_entry_point: The affected Living State entity or bus message
  change_pattern: Annotate the record with the true author and the false fields, in place, so the incident stays legible; do not delete it.
  rollback_procedure: Leave the disputed content uncommitted until authorship is established.
  integrity_check: No downstream fold consumes content whose author is unconfirmed.
```

## §H. Evolve

### §H.1 Invariants

Every decision-relevant claim carries whether it was observed. Absence is recorded as absence. Code claims cite a SHA. Verdicts are read canonically. Unverified fails closed.

### §H.2 BREAKING predicates

Removing the provenance requirement, permitting an unmeasured figure to be recorded as observed, reading verdicts from the legacy projection, or allowing unattributed content to be folded is BREAKING.

### §H.3 REVIEW predicates

Review changes to the verdict vocabulary or its mapping, to the measurement surface a figure is derived from, to dispatch bound semantics, or to identity attribution in Living State and the peer bus.

### §H.4 SAFE predicates

Adding worked examples, promoting a claim from inherited to observed, or tightening a procedure without weakening a criterion is SAFE.

### §H.5 Boundary definitions

#### module

Specification blobs in Git, their fold commits, the review envelopes bound to them, and the gate records that cite them.

#### public contract

A specification that a panel can vote on: claims with provenance, code references with SHAs, and explicit statements of what was not established.

#### runtime dependency

Living State gate records, the repository at a named SHA, Council dispatch and its verdict envelopes, and the measurement surfaces a figure is derived from.

#### config default

An unestablished claim is UNVERIFIED and fails closed. No default, no inherited summary and no writer-supplied identity field can manufacture an observation.

### §H.6 Adjudication

Where a runbook table and a live test assert opposite behaviour for the same component, neither wins by seniority. Record both, state which one the specification assumes, and escalate the contradiction as its own item before the fold proceeds. Applies directly to the degraded-evidence classification contested on T-2026-000411.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-03], scenario: A figure arrives in a peer handoff and is about to be written into the spec., expected_answers: [{kind: classification, label: INHERITED_NOT_OBSERVED}], weight: 0.0833333333}
  - {id: I-02, type: operate, refs: [E-01], scenario: A round result arrives and the deployed server SHA has not been checked., expected_answers: [{kind: classification, label: UNVERIFIED}], weight: 0.0833333333}
  - {id: I-03, type: operate, refs: [E-02], scenario: The verdict field reads REVISE while every reviewer prose approves with conditions., expected_answers: [{kind: classification, label: APPROVED_WITH_MANDATES}], weight: 0.0833333333}
  - {id: I-04, type: operate, refs: [E-04], scenario: The spec cites a function that moved two commits ago., expected_answers: [{kind: classification, label: STALE_SOURCE}], weight: 0.0833333333}
  - {id: I-05, type: isolate, refs: [F-03], scenario: The builder reports the completed range was not persisted., expected_answers: [{kind: human_action, verb: check, object: remote branch, target: git ls-remote}], weight: 0.0833333333}
  - {id: I-06, type: isolate, refs: [F-05], scenario: A document signed by this instance appears that this instance did not write., expected_answers: [{kind: classification, label: UNATTRIBUTED}], weight: 0.0833333333}
  - {id: I-07, type: isolate, refs: [F-01], scenario: A percentage in the spec has no method recorded beside it., expected_answers: [{kind: classification, label: UNMEASURED}], weight: 0.0833333333}
  - {id: I-08, type: repair, refs: [G-01], scenario: A figure in the spec cannot be reproduced from its own text., expected_answers: [{kind: human_action, verb: relabel, object: the figure, target: explicit unmeasured}], weight: 0.0833333333}
  - {id: I-09, type: repair, refs: [G-04], scenario: A Living State entity carries an updated_by that the named instance denies., expected_answers: [{kind: human_action, verb: annotate, object: the entity, target: in place attribution correction}], weight: 0.0833333333}
  - {id: I-10, type: evolve, refs: [§H.2], scenario: A proposal allows an inherited summary figure to be recorded as observed., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0833333333}
  - {id: I-11, type: evolve, refs: [§H.3], scenario: The verdict vocabulary gains an additional canonical value., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0833333333}
  - {id: I-12, type: ambiguous, refs: [§H.6], scenario: A runbook table and two live tests assert opposite behaviour for the same branch., expected_answers: [{kind: classification, label: ADJUDICATE_BEFORE_FOLD}], weight: 0.0833333337}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1346
last_refresh_commit: 7288f88
last_refresh_date: 2026-07-26T11:00:00Z
owner_agent: vulcan
refresh_triggers: [CORE version change, verdict vocabulary or adapter change, dispatch bound semantics change, session or peer-bus identity verification landing, provenance marking becoming structural]
scheduled_cadence: 30d
last_harness_pass_rate: 0.0
last_harness_date: 2026-07-26T11:13:42Z
first_staleness_detected_at: null
```

## §K. Conformance

The recorded harness score of 0.0 is a real measured result and is reported here rather than smoothed. It does not mean the twelve scenarios were judged and failed. The run at 2026-07-26T11:13:42Z returned `INVALID_RESPONSE` on all twelve, with the reason `response is not a JSON object matching the harness output schema`, so no scenario was ever scored on its content. The score therefore measures the harness dispatch path, not this document's legibility. Cause and fix are on T-2026-000413; the score must be re-taken once that lands, and until then this runbook has no evidence either way about how well a stateless agent can use it.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1346 / 2026-07-26T11:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: null
word_count_delta: null
```


This runbook conforms to the §A–§K standard and is a catalog member. It was authored at S1346 by Vulcan, directly and not by a builder dispatch, on branch `runbook/gate-specification-authoring-vulcan-s1346` based at `7288f88`.

It discharges the runbook debt carried as S1343-D1..D10 and S1346-D1..D3, whose subjects were deployed-SHA verification before trusting a gate result and Gate 1 / Gate 2 specification fold authoring.

An earlier file of the same intended path appeared on this host during S1346 with authorship unestablished. It was deliberately not read into this document, not adopted and not committed; it is recorded on T-2026-000412. A document about honest authorship does not enter the library under an unverified signature.
