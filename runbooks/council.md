---
runbook_id: council
domain: council-operations
status: ACTIVE
authoritative_for:
  - topic: council-operations
    section: §C. Architecture & Interactions
  - topic: council-schema-drift
    section: §F. Isolate
  - topic: council-roster-drift
    section: §F. Isolate
aliases: []
error_signatures:
  - signature: timeout
    section: §E. Operate
  - signature: read-only agent attempted write
    section: §E. Operate
  - signature: missing dispatch token
    section: §E. Operate
  - signature: schema_roster_mismatch
    section: §E. Operate
  - signature: council_schema_drift
    section: §F. Isolate
  - signature: council_roster_drift
    section: §G. Repair
  - signature: agent silence
    section: §E. Operate
  - signature: no resolution
    section: §E. Operate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-27
system_name: council
purpose_sentence: A multi-agent build and review system with MP as mandatory builder and CC, Kimi, and GLM as the gate voter panel.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Stable architecture, mechanics, and reasoning of the Council operating system. The deployed gateway schema owns callable dispatch arguments; deployed gate constants own required membership; the newest explicitly superseding infra:council-comms amendments supply role/model/retirement history and known quirks. Absent state fields are never inferred.

  Cross-runbook reference convention: file-qualified IDs `<file-stem>:<id>` (e.g., `agent-dispatch:F-01` for symptom F-01 in `runbooks/agent-dispatch.md`). Same-file references retain bare `<id>` form. (AC8.)
linter_version: 1.0.0
---

# Council

## §A. Header

The YAML frontmatter above defines the §A header. §J is authoritative for lifecycle refresh tracking; this header is the display summary for stateless readers. Vulcan is the single schema-valid lifecycle owner, while Vulcan and Mars retain equal-authority peer co-ownership of Council orchestration and state management.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Council dispatch (`council_request`) | SHIPPED | `koskadeux-mcp/tools/agents.py:_handle_call_*` | Council dispatch integration covered by Koskadeux MCP dispatch tests | 2026-04-29 |
| Gate review (BQ 4-gate flow) | SHIPPED | `build:bq-* Living State entities` | Gate transition checks tracked in build entity review state | 2026-04-29 |
| Council Hall multi-agent deliberation | SHIPPED | `koskadeux-mcp/tools/agents.py:_handle_council_hall` | Council Hall dispatch path exercised by deliberation sessions | 2026-04-29 |
| Cross-review-gate enforcement | SHIPPED | `koskadeux-mcp gateway author-mode dispatch tokens` | Gateway author/read-only distinction reviewed in gate process audits | 2026-04-29 |
| Living State config authority | SHIPPED | `infra:council-comms` | State freshness verified during Council runbook conformance chunks | 2026-04-29 |
| Retired-agent cold storage | DEPRECATED | — | XAI active-dispatch coverage retired; cold-storage state lives in `infra:council-comms.retired_agents.xai` | 2026-04-29 |

## §C. Architecture & Interactions

`council_request` is the canonical dispatch entry point. A dispatch uses one `agent`, an intent-bearing `mode` (`review`, `build`, `author`, or `open_response`), and `task`; review/build calls add only keys exposed by the live tool schema, such as `cwd`, `dispatch_sha`, `base`, `head`, `bq_code`, `session_id`, `caller_instance`, and `runbook_refs`. `action` is reserved for build management (`check_build` or `list_builds`), not review/build dispatch.

The current gate voter panel is CC + Kimi + GLM exactly. MP is the mandatory builder and
is not a gate voter. AG is PAUSED, and XAI is RETIRED. Model assignments, dispatch caps,
quirks, and any later roster change must be verified against deployed code, the
live callable schema, and the newest explicitly superseding Living State amendment.
The current `infra:council-comms` entity has no canonical `review_order` or
`dispatch_patterns` field and contains historical records; do not invent those paths.

The current Codex connector schema in S1413 omits `kimi` even though the newer
S1321 gate contract requires Kimi and Living State records later successful Kimi
dispatches. That is a client/gateway schema-coherency fault: stop and reload or
refresh the connector, then verify the callable schema. Never substitute another
reviewer or remove Kimi from policy merely to make the call validate.

<!-- catalog:historical -->
Strategic why: MP is primary reviewer because Codex CLI automated; deeper wiring-gap detection per S526 Chunk 3B precedent. AG is cross-vote and secondary because Gemini 3.1 Pro is a frontier reviewer, but line-number fabrication risk on code audits per S499 excludes AG from `gate3_post_build_audit` since S342. DeepSeek is a full voter after graduating S528 with 94 dispatches, `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and statistical_record_floor crushed 4.7x. CC is fallback builder because it gives a 300s MP Codex CLI timeout safety net, Opus-tier reasoning for complex multi-file builds, and a 600s default timeout.
<!-- /catalog:historical -->

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Council Dispatch | `koskadeux-mcp/tools/agents.py:_handle_call_*` | dispatch task records | One explicitly selected backend per call | Routes a singular `agent` under explicit `mode`; `action` manages existing build tasks only. |
| Gate Review Flow | `build:bq-* Living State entities` | build entities, gate status fields, review verdicts | Council dispatch, author-mode tokens, runbook specs | Implements the BQ 4-gate flow and binds authoring/review mode to dispatch provenance. |
| Council Hall | `koskadeux-mcp/tools/agents.py:_handle_council_hall` | deliberation IDs, response transcripts | Configured voter panel and synthesis | Runs multi-agent deliberation when independent reviews are insufficient. |
| Gate Roster | `koskadeux-mcp/council_gate_runner.py` deployed constants plus newest `infra:council-comms` amendment | required member ids and policy history | Gate Review Flow, gateway schema | S1321 records exact `{cc,kimi,glm}` membership; code/schema/state disagreement fails closed. |
| Dispatch Contract | live `council_request` tool schema at the deployed gateway SHA | accepted argument names and enums | agents, runbooks, connector clients | Unknown or client-blocked arguments are schema drift, not an invitation to improvise. |
| Policy History | `infra:council-comms` superseding amendment records | role/model/retirement history and quirks | operators, deployment verification | Read newest superseding records; absent fields such as `review_order` and `dispatch_patterns` are not valid state paths. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| MP | Roster status ACTIVE: mandatory build author; not a gate voter | Builder backend from `infra:council-comms` | repo write when author-mode is explicit | COMPLETE |
| CC | Roster status ACTIVE: gate voter | Voter backend from `infra:council-comms` | repo read | COMPLETE |
| Kimi | Roster status ACTIVE: gate voter | Shared provider read-only review loop | bounded read-only at-SHA repository tools | COMPLETE |
| GLM | Roster status ACTIVE: gate voter | Shared provider read-only review loop | bounded read-only at-SHA repository tools | COMPLETE |
| DeepSeek | Roster status RETIRED: no active gate role | Retained dispatch backend | none for current gates | COMPLETE |
| AG | Roster status PAUSED: no active gate role | Paused backend metadata in `infra:council-comms` | none for current gates | COMPLETE |
| XAI | Roster status RETIRED: no active gate role | Retirement metadata in `infra:council-comms` | none | PARTIAL — retired; see `infra:council-comms.retired_agents.xai` for cold storage and reactivation procedure |
| Vulcan + Mars | Roster status ACTIVE: equal-authority peer orchestration and state management | Koskadeux MCP | gateway, Living State, repos | COMPLETE |

<!-- catalog:historical -->
MP owns primary review because the Codex CLI path is automated and has shown deeper wiring-gap detection per S526 Chunk 3B. AG remains valuable as a Gemini 3.1 Pro frontier cross-vote, but S499 line-number fabrication risk means code-audit line claims must be verified before use. DeepSeek is a full voter because S528 graduation produced 94 dispatches with `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and statistical_record_floor crushed 4.7x. XAI is retired because line-number fabrication exclusion has applied since S342 and DeepSeek superseded the architecture-only niche; see the retired-agents appendix planned for `runbooks/agent-dispatch.md`.
<!-- /catalog:historical -->

## §E. Operate

```yaml operate
- id: E-01
  trigger: A gate audit needs one required reviewer's verdict at an exact commit.
  pre_conditions: [target_repo_available, exact_commit_known, required_reviewer_known_from_deployed_gate_contract, live_schema_accepts_reviewer]
  tool_or_endpoint: council_request(agent=<required_reviewer>, mode=review, task=<evidence_bound_audit_prompt>, cwd=<repo>, dispatch_sha=<sha>, base=<base_sha>, head=<sha>, session_id=<session>)
  argument_sourcing:
    agent: dispatch one call per member required by the deployed gate contract; never pass a plural agents field
    mode: review
    task: derive from the BQ gate task and embed exact spec, changed-file, and evidence references
    cwd: use the repository root containing dispatch_sha
    dispatch_sha: resolve the full commit SHA from server-visible Git
    base: resolve the reviewed base SHA when diff scoping is required
    head: use the same exact reviewed commit as dispatch_sha
    session_id: use the active KD session
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(agent + target_repo + dispatch_sha + gate + task_digest)
  expected_success: {shape: Task id or terminal reviewer envelope, verification: Match agent, reviewed SHA, model identity, read-only coverage, and verdict to the requested gate role}
  expected_failures:
    - {signature: "timeout", cause: agent process exceeded configured timeout or progress guard}
    - {signature: "read-only agent attempted write", cause: dispatch role/auth boundary mismatch}
    - {signature: "schema_roster_mismatch", cause: required reviewer is absent from the callable client schema}
  next_step_success: Attach the commit-bound verdict to the BQ review record and repeat for the other required members
  next_step_failure: Preserve the transcript; on `schema_roster_mismatch` reload or refresh the gateway/connector and re-probe, never substitute a member
- id: E-02
  trigger: An approved BQ chunk needs an MP structural build.
  pre_conditions: [build entity reconciled, approved spec readable, clean dedicated branch or wrapper worktree available, runbook context selected]
  tool_or_endpoint: council_request(agent=mp, mode=build, task=<bounded_build_prompt>, cwd=<repo>, bq_code=<BQ-code>, caller_instance=<mars|vulcan>, dispatch_class=structural, session_id=<session>, runbook_refs=<exact_refs>, verifier_subtype=<type>, timeout_s=<seconds>)
  argument_sourcing:
    task: derive from the approved chunk spec with exact parent, file scope, tests, and no-push instruction when the wrapper owns publication
    cwd: use the canonical repository root expected by the wrapper
    bq_code: use the reconciled BQ code
    caller_instance: use the active peer instance
    runbook_refs: use exact catalog/runbook section evidence required by the dispatch gate
    verifier_subtype: choose the manifest contract matching the artifact
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: bq_code + approved_parent + task_digest
  expected_failures:
    - {signature: "missing dispatch token", cause: author-mode or review-mode gateway token not bound}
    - {signature: "schema argument mismatch", cause: caller used an old action/prompt/context_refs/agents contract}
  expected_success: {shape: Confirmed task id followed by wrapper-verified commit and artifact manifest, verification: Reconcile task status with isolated Git, canonical branch, and remote equality before retry or promotion}
  next_step_success: Send the exact landed commit through required non-author gate review
  next_step_failure: Preserve task id and reconcile Git before any retry; never dispatch duplicate work from a timeout alone
- id: E-03
  trigger: A dispatched Council build is asynchronous and needs status reconciliation.
  pre_conditions: [task_id_was_confirmed, no_duplicate_retry_has_started]
  tool_or_endpoint: council_request(action=check_build, task_id=<task_id>)
  argument_sourcing:
    action: check_build
    task_id: use the exact id returned by E-02; do not guess from recency
  idempotency: IDEMPOTENT
  expected_success: {shape: Current wrapper task state and any terminal result, verification: Reconcile claimed result with canonical and isolated Git before treating it as success or failure}
  expected_failures:
    - {signature: "agent silence", cause: task remains nonterminal beyond its bounded timeout}
    - {signature: "no resolution", cause: wrapper state and Git evidence disagree}
  next_step_success: Continue waiting, verify terminal artifacts, or promote only after evidence agrees
  next_step_failure: Preserve the task and branch evidence and follow agent-dispatch reconciliation; do not blindly redispatch
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Required reviewer cannot be dispatched | Client schema omits a policy-required member, gateway and connector schemas are stale, or backend enum drift exists | Compare deployed required-member constants, the live callable `council_request` enum, newest superseding state amendment, and handler SHA | G-01 | CONFIRMED |
| F-02 | Review/build call is rejected for unknown arguments | Caller used retired `action=review/build`, `prompt`, `context_refs`, plural `agents`, `dispatch_pattern`, or `review_order` fields | Compare the attempted key set with the live callable schema before retrying | G-02 | CONFIRMED |
| F-03 | Wrapper task state disagrees with Git | Timeout/status lag, isolated worktree commit retained after wrapper error, or canonical/remote branch not advanced | Inspect exact task id, isolated Git, canonical branch, commit tree/parent, and remote equality before classifying | G-03 | CONFIRMED |

<!-- catalog:historical -->
The §F and §G entries preserve incident-era MP-primary/AG-secondary operations and their
repairs. They are historical evidence only, not current dispatch instructions.

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | AG progress-guard timeout during review | Gemini/AG server stalled, prompt too broad, recurring progress-guard defect from BQ-COUNCIL-AG-PROGRESS-GUARD-FIX | Inspect dispatch transcript for last progress marker and compare timeout against `infra:council-comms.dispatch_patterns` | §G-01 | CONFIRMED |
| F-02 | MP READ-ONLY commit-during-review | Review dispatch accidentally granted write-mode, gateway token mismatch, reviewer used builder path | Compare dispatch token mode with git author activity and task prompt | §G-02 | CONFIRMED |
| F-03 | Dispatcher stale but files committed | Agent completed local work while dispatcher state failed to refresh, Living State task result lag, gateway status cache stale | Check branch git log/status against dispatcher task status and Living State build body.summary | §G-03 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Council Dispatch
  root_cause: AG review dispatch exceeded the progress guard before producing a usable verdict.
  repair_entry_point: koskadeux-mcp/tools/agents.py:_handle_call_*
  change_pattern: Narrow the review prompt, redispatch AG read-only, and route recurring timeout evidence to BQ-COUNCIL-AG-PROGRESS-GUARD-FIX.
  rollback_procedure: Cancel the replacement dispatch and retain the prior task transcript as failed evidence.
  integrity_check: Confirm the new AG result includes a verdict and references real files or explicitly declines unsupported line claims.
- id: G-02
  symptom_ref: F-02
  component_ref: Gate Review Flow
  root_cause: Review-mode work crossed the auth boundary and produced a commit from a read-only task.
  repair_entry_point: koskadeux-mcp gateway author-mode dispatch tokens
  change_pattern: Quarantine the commit, rerun the review from a clean read-only dispatch, and require author-mode token binding for any accepted write.
  rollback_procedure: Drop only the quarantined review commit after preserving its diff for audit evidence.
  integrity_check: Verify the accepted review task has no git write side effects and the BQ entity records read-only provenance.
- id: G-03
  symptom_ref: F-03
  component_ref: Council Dispatch
  root_cause: Dispatcher task state lagged behind actual repo writes.
  repair_entry_point: infra:council-comms.dispatch_patterns
  change_pattern: Reconcile git commit SHA, dispatcher task id, and Living State build body.summary before promoting the gate.
  rollback_procedure: Revert the state patch if the commit SHA or branch does not match the artifact under review.
  integrity_check: Confirm git HEAD, dispatcher result, and Living State build summary all name the same artifact.
```

<!-- /catalog:historical -->

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Dispatch Contract
  root_cause: Required-member policy and the callable client/gateway schema disagree.
  repair_entry_point: deployed gateway schema generation and connector reload
  change_pattern: Verify the deployed gate constants and handler SHA, repair schema generation or reload the connector, then prove the required member is callable; never substitute another reviewer.
  rollback_procedure: Keep gate promotion blocked and restore the last coherent gateway/schema pair if the repair changes policy unexpectedly.
  integrity_check: Confirm policy member ids, callable enum, actual model identity, and one read-only smoke dispatch agree.
- id: G-02
  symptom_ref: F-02
  component_ref: Dispatch Contract
  root_cause: Operative instructions or caller code used an obsolete tool contract.
  repair_entry_point: live council_request schema plus the calling runbook or client
  change_pattern: Replace retired fields with singular agent, explicit mode, task, and only currently exposed evidence/context keys; validate examples against a pinned schema artifact.
  rollback_procedure: Preserve the rejected payload as evidence and do not weaken schema validation to accept fictional fields.
  integrity_check: Replay the corrected call through schema validation and verify it reaches the intended read-only or build path.
- id: G-03
  symptom_ref: F-03
  component_ref: Council Dispatch
  root_cause: Wrapper state and repository publication progressed on different clocks.
  repair_entry_point: council_request(action=check_build, task_id=<exact_id>) plus isolated/canonical Git inspection
  change_pattern: Reconcile task state against exact commit, tree, parent, file scope, clean worktree, canonical branch, and remote equality; use preservation recovery only after a verified wrapper false failure.
  rollback_procedure: Do not launch a duplicate task or manufacture success state; leave the evidence intact until canonical publication is resolved.
  integrity_check: Confirm wrapper terminal result and all three Git views identify the same artifact.
```

## §H. Evolve

### §H.1 Invariants

- `council_request` remains the canonical code entry point for Council dispatch.
- The live gateway schema is authoritative for callable arguments; deployed gate constants are authoritative for required members; newest superseding `infra:council-comms` amendments provide role/model/retirement history and quirks.
- Missing Living State paths such as `review_order` or `dispatch_patterns` must not be inferred from historical narrative.
- Read-only review agents must not receive repo write scope without explicit Council change review.

### §H.2 BREAKING predicates

- Retiring a Council member is BREAKING because deployed required-member and validation constants change.
- Enabling write-mode for a read-only agent is BREAKING because it changes an auth boundary.
- Removing `council_request` as the canonical dispatch entry point is BREAKING.

### §H.3 REVIEW predicates

- Adding a Council member requires REVIEW.
- Changing any configured model frontier requires REVIEW.
- Changing required gate members or deployed Council Hall `VALID_AGENTS`/`DEFAULT_AGENTS` requires REVIEW.

### §H.4 SAFE predicates

- Increasing the $/dispatch cap is SAFE when auth scope, required members, and participant roles do not change.
- Documentation-only updates that preserve code/schema/state source ownership are SAFE.
- Timeout tuning inside an existing dispatch path is SAFE unless it changes fallback ownership.

### §H.5 Boundary definitions

#### module

The module boundary is the Council operating slice in Koskadeux MCP, Living State build entities, and the runbooks that document them.

#### public contract

The public contract is the `council_request` surface, Council Hall surface, BQ gate review semantics, and dispatch-mode/auth-mode distinction exposed to operators and agents.

#### runtime dependency

A runtime dependency is any agent backend, CLI, API, gateway token service, or Living State entity required for Council dispatch or gate review to run.

#### config default

A config default is a value read from its owning deployed code or an explicit current state field: model frontier, required-member set, dispatch timeout, cost cap, or Hall default. Historical prose and absent state paths are not defaults.

### §H.6 Adjudication

When two agents classify a Council change differently, use the more restrictive class and record the dispute in the BQ review record. Max resolves classification disputes that alter auth scope, membership, or gate policy.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §D]
    scenario: |
      id: E-01. trigger: GLM must review an exact gate commit. pre_conditions: repository root, base SHA, dispatch SHA, session id, and audit prompt are known; review is read-only. tool_or_endpoint: council_request(agent=glm, mode=review, task=<audit_prompt>, cwd=<repo>, dispatch_sha=<sha>, base=<base>, head=<sha>, session_id=<session>). argument_sourcing: agent from deployed required-member policy; SHAs from server-visible Git; task from gate evidence; cwd from repository root. idempotency: IDEMPOTENT_WITH_KEY on agent + dispatch_sha + task_digest. expected_success: a commit-bound read-only reviewer envelope or confirmed task id. expected_failures: schema rejection, model mismatch, incomplete coverage, timeout, or write side effect. next_step_success: verify and attach the verdict. next_step_failure: preserve evidence and apply F-01 or F-02 without substituting a voter.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha, base, head, session_id]
        argument_values: {agent: glm, mode: review}
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02, §D]
    scenario: |
      id: E-02. trigger: An approved structural chunk needs the mandatory MP builder. pre_conditions: BQ is reconciled, dedicated branch is clean, approved parent and spec are exact, runbook refs are available, and no peer lane conflict exists. tool_or_endpoint: council_request(agent=mp, mode=build, task=<bounded_prompt>, cwd=<repo>, bq_code=<BQ>, caller_instance=mars, dispatch_class=structural, session_id=<session>, runbook_refs=<refs>, verifier_subtype=general, timeout_s=1200). argument_sourcing: BQ/spec/parent from reviewed state and Git; caller/session from registry; refs from pinned runbook context; cwd from canonical repo. idempotency: IDEMPOTENT_WITH_KEY on BQ + parent + task_digest. expected_success: confirmed task id and wrapper-verified artifact. expected_failures: reconciliation failure, dirty branch, peer conflict, schema mismatch, timeout, or manifest failure. next_step_success: verify landed Git and send the commit to non-author review. next_step_failure: preserve task id and reconcile before any retry.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, bq_code, caller_instance, dispatch_class, session_id, runbook_refs, verifier_subtype, timeout_s]
        argument_values: {agent: mp, mode: build, dispatch_class: structural}
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: |
      id: E-03. trigger: A confirmed asynchronous build task needs a status check. pre_conditions: exact task id exists and no duplicate retry has started. tool_or_endpoint: council_request(action=check_build, task_id=<id>). argument_sourcing: task_id only from the original dispatch receipt. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: current wrapper task state and any terminal result. expected_failures: unknown task id or state/Git disagreement. next_step_success: reconcile terminal output with isolated, canonical, and remote Git. next_step_failure: retain evidence and investigate; never guess a newer task.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [action, task_id]
        argument_values: {action: check_build}
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01, G-01]
    scenario: |
      id: F-01. trigger: policy requires Kimi but the current connector enum rejects agent=kimi. pre_conditions: deployed gate-member evidence, live callable schema, handler SHA, and connector session are available. tool_or_endpoint: compare deployed constants and callable schema, then reload or refresh the gateway/connector. argument_sourcing: required member from S1321/deployed code; enum from the actual client tool schema; SHA from deployment evidence. idempotency: READ_ONLY_DIAGNOSTIC until a controlled reload. expected_success: classify schema-coherency failure, not voter absence. expected_failures: substituting another voter or editing policy to fit a stale client. next_step_success: apply G-01 and prove one exact-model read-only Kimi smoke after refresh. next_step_failure: keep the gate blocked.
    expected_answers:
      - kind: human_action
        verb: reconcile
        object: required-member policy with callable schema
        target: F-01 then G-01
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-02, G-02]
    scenario: |
      id: F-02. trigger: a copied runbook submits a council_request payload with obsolete `action: review`, plural `agents`, `prompt`, and `context_refs` fields. pre_conditions: rejected payload and live schema are available. tool_or_endpoint: compare attempted argument keys with council_request schema. argument_sourcing: attempted keys from error receipt; accepted keys from the live connector. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: identify every obsolete key and the singular agent/mode/task replacement. expected_failures: weakening validation or retrying the same fictional payload. next_step_success: apply G-02 to the owning instruction/client. next_step_failure: block the dispatch until executable syntax is known.
    expected_answers:
      - kind: human_action
        verb: compare
        object: rejected dispatch keys
        target: F-02 then G-02
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-03, G-03, agent-dispatch:F-01]
    scenario: |
      id: F-03. trigger: wrapper reports failure but an isolated MP worktree contains a candidate commit. pre_conditions: task id, isolated path, canonical branch, remote ref, expected parent, and scope are known. tool_or_endpoint: council_request(action=check_build, task_id=<id>) plus read-only Git inspection. argument_sourcing: task id from receipt; paths/parent/scope from dispatch; remote from branch config. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: distinguish verified wrapper false failure from incomplete or unsafe work. expected_failures: pre-dispatch preservation ref, blind push, duplicate dispatch, or unverified state patch. next_step_success: apply G-03 and use bounded recovery only if every invariant passes. next_step_failure: leave evidence intact and stop.
    expected_answers:
      - kind: human_action
        verb: reconcile
        object: wrapper state and exact Git artifact
        target: F-03 then G-03
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-01, F-01]
    scenario: |
      id: G-01. trigger: connector reload is complete after a required-member enum mismatch. pre_conditions: deployed policy unchanged, handler and connector restarted, and exact review SHA available. tool_or_endpoint: council_request(agent=<required_member>, mode=review, task=<smoke_prompt>, cwd=<repo>, dispatch_sha=<sha>). argument_sourcing: agent from deployed required-member set; task is a bounded read-only schema/model smoke; cwd/SHA from Git. idempotency: IDEMPOTENT_WITH_KEY on agent + handler_sha + dispatch_sha. expected_success: schema accepts the member and result proves exact model/read-only coverage. expected_failures: enum still missing, model mismatch, or write side effect. next_step_success: resume the complete panel. next_step_failure: roll back to last coherent gateway/schema pair and keep gate blocked.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha]
        argument_values: {mode: review}
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-02, F-02]
    scenario: |
      id: G-02. trigger: an obsolete review payload must be corrected. pre_conditions: one required reviewer, audit prompt, repo root, and exact SHA are known. tool_or_endpoint: council_request(agent=glm, mode=review, task=<audit_prompt_with_refs>, cwd=<repo>, dispatch_sha=<sha>). argument_sourcing: move old prompt/context_refs content into task; replace plural agents with one agent; replace action=review with mode=review. idempotency: IDEMPOTENT_WITH_KEY on agent + SHA + task_digest. expected_success: payload passes schema and reaches read-only review. expected_failures: any retired key remains or evidence is no longer commit-bound. next_step_success: update the owning runbook/client and add a schema regression. next_step_failure: preserve rejection and do not bypass schema.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha]
        argument_values: {agent: glm, mode: review}
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H]
    scenario: |
      id: H-01. trigger: a proposal changes the required gate-member set. pre_conditions: current/proposed constants, quorum math, model policy, schema changes, and migration plan are written. tool_or_endpoint: deployed gate-runner and schema change under Council review. argument_sourcing: current truth from code plus newest amendment; proposed truth from reviewed design. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify BREAKING and require coordinated code/schema/state/runbook rollout. expected_failures: patching prose or Living State alone. next_step_success: open reviewed gate changes and live fail-closed tests. next_step_failure: retain current panel.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H, G-02]
    scenario: |
      id: H-02. trigger: council_request gains an additive evidence-reference field. pre_conditions: source schema, handler plumbing, authorization, clients, and pinned runbook-schema artifact plan are known. tool_or_endpoint: gateway schema and handler change plus executable-example validation. argument_sourcing: field semantics from reviewed spec; compatibility from current callable schema. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify REVIEW and update code, generated schema artifact, clients, tests, and runbooks together. expected_failures: documenting the field before deployment or accepting it without handler plumbing. next_step_success: deploy then live-probe before making the example authoritative. next_step_failure: retain task-embedded refs.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [F-01, G-01, §H.6]
    scenario: |
      id: AMB-01. trigger: deployed code/state require Kimi, current client schema omits Kimi, and an urgent gate is waiting. pre_conditions: exact code SHA, state amendment, client schema, risk class, and reload authority are available. tool_or_endpoint: stop gate promotion and reconcile the code/schema/deployment boundary. argument_sourcing: evidence from deployed constants, newest superseding state record, and actual callable enum. idempotency: READ_ONLY_DIAGNOSTIC until controlled reload. expected_success: classify as schema-coherency incident; no substitute or reduced quorum. expected_failures: treating either stale client or historical state prose as sole truth. next_step_success: refresh and smoke-test the required member. next_step_failure: escalate to Max with the gate blocked.
    expected_answers:
      - kind: human_action
        verb: stop
        object: gate promotion under schema mismatch
        target: F-01 then G-01
    weight: 0.09090909090909091
```

<!-- catalog:historical -->
The S529/S530 conformance scenarios below are retained as historical fixtures. Their
MP/AG/DeepSeek panel and role expectations are not the current gate contract.

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §D, agent-dispatch:E-02]
    scenario: |
      id: E-01. trigger: A Gate 2 chunking spec needs full Council review before the build plan closes. pre_conditions: feature branch, Gate 2 spec path, BQ entity, and current infra:council-comms.dispatch_patterns.gate2_spec_review are available. tool_or_endpoint: council_request(action=review, agents=[mp, ag, deepseek], dispatch_pattern=gate2_spec_review, context_refs=<spec, branch, build_id>). argument_sourcing: agents and pattern from infra:council-comms; branch from git; build_id from Living State. idempotency: IDEMPOTENT_WITH_KEY on build_id + gate + spec_sha + agent. expected_success: three read-only verdicts attached to the BQ record. expected_failures: timeout, missing agent backend, stale dispatch pattern, or auth-mode mismatch. next_step_success: close Gate 2 review or fold mandates into the spec. next_step_failure: isolate with F-01/F-03 or dispatch mechanics via agent-dispatch:F-02.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [action, agents, dispatch_pattern, context_refs]
        argument_values:
          action: review
          agents: [mp, ag, deepseek]
          dispatch_pattern: gate2_spec_review
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02, §D, agent-dispatch:E-03]
    scenario: |
      id: E-02. trigger: A Gate 3 post-build audit is ready after a code chunk lands. pre_conditions: feature branch HEAD, committed diff, build entity, and security-sensitive scope are known. tool_or_endpoint: council_request(action=gate_review, agents=[mp, ag, deepseek], dispatch_pattern=gate3_post_build_audit, commit=<sha>). argument_sourcing: agents from the security rule in infra:council-comms; commit from git rev-parse HEAD; evidence refs from spec and diff. idempotency: IDEMPOTENT_WITH_KEY on build_id + gate3 + commit + agent. expected_success: MP, AG, and DeepSeek deliver read-only audit verdicts with no write side effects. expected_failures: AG line-number risk, backend timeout, stale review_order, or missing dispatch token. next_step_success: attach verdict set and promote or remediate. next_step_failure: isolate with F-01/F-03 and verify any file:line claims before accepting them.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [action, agents, dispatch_pattern, commit]
        argument_values:
          action: gate_review
          agents: [mp, ag, deepseek]
          dispatch_pattern: gate3_post_build_audit
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-01, §D, agent-dispatch:E-01]
    scenario: |
      id: E-03. trigger: A code chunk has an approved Gate 2 spec and needs an implementation author. pre_conditions: branch target, spec excerpt, acceptance criteria, and write-mode authorization are explicit. tool_or_endpoint: council_request(action=build, agent=mp, prompt=<code chunk>, context_refs=<spec, branch, files>). argument_sourcing: agent from §D primary-builder policy; prompt from chunk spec; branch from git; auth mode from gate record. idempotency: IDEMPOTENT_WITH_KEY on build_id + chunk_id + branch + prompt_digest. expected_success: MP returns a commit SHA and implementation summary. expected_failures: Codex CLI timeout, missing repo context, or accidental review-mode token. next_step_success: send the commit to Gate 3 review. next_step_failure: reconcile dispatcher state with git or use CC fallback if MP times out.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [action, agent, prompt, context_refs]
        argument_values:
          action: build
          agent: mp
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-01, G-01, agent-dispatch:F-02]
    scenario: |
      id: F-01. trigger: AG review-mode dispatch stops with a progress-guard timeout while reviewing a Council spec. pre_conditions: dispatch transcript and timeout policy are available. tool_or_endpoint: dispatcher transcript plus infra:council-comms.dispatch_patterns. argument_sourcing: task id from council_request response; timeout cap from Living State; prompt size from dispatch payload. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as AG progress-guard timeout and cite BQ-COUNCIL-AG-PROGRESS-GUARD-FIX C1-C4 as the relevant defect/fix history. expected_failures: confusing backend outage with prompt-budget exhaustion, or redispatching before preserving transcript evidence. next_step_success: apply G-01 with a narrower review prompt. next_step_failure: escalate backend health to dispatch maintainers.
    expected_answers:
      - kind: human_action
        verb: inspect
        object: AG progress-guard timeout transcript
        target: F-01 then G-01
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-01, G-01, agent-dispatch:F-02]
    scenario: |
      id: F-02. trigger: AG returns no verdict because review-mode MAX_TURNS=25 is exhausted on a broad diff. pre_conditions: AG transcript, prompt body, and diff size are available. tool_or_endpoint: council_request task transcript. argument_sourcing: max-turn evidence from transcript; affected files from git diff; expected agent role from infra:council-comms.review_order. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as AG review-mode budget exhaustion and cite BQ-COUNCIL-AG-MAX-TURNS-REVIEW-MODE. expected_failures: treating it as a Council policy disagreement or accepting a partial non-verdict. next_step_success: use G-01 redispatch with an ultra-tight diff-only prompt. next_step_failure: request MP/DeepSeek read-only coverage while preserving the exhausted AG result.
    expected_answers:
      - kind: human_action
        verb: classify
        object: AG MAX_TURNS exhaustion
        target: G-01 diff-only redispatch
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-02, G-02, agent-dispatch:F-02]
    scenario: |
      id: F-03. trigger: MP was dispatched for review but produced a commit. pre_conditions: dispatch mode, task prompt, git log, and branch status are available. tool_or_endpoint: git log plus council_request dispatch record. argument_sourcing: token mode from gateway record; commits from git; prompt role from task payload. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as MP READ-ONLY violation, cite the S452 quirk, and quarantine the commit before accepting any review result. expected_failures: silently keeping the commit, or rerunning from the dirty branch. next_step_success: apply G-02 and rerun the review from clean read-only state. next_step_failure: escalate auth-boundary mismatch to Vulcan/Max.
    expected_answers:
      - kind: human_action
        verb: quarantine
        object: MP review-mode commit
        target: F-02 then G-02
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [§D, G-01]
    scenario: |
      id: F-04. trigger: AG verdict cites exact file:line findings that look plausible but do not match the diff. pre_conditions: AG verdict text, affected file paths, and repository checkout are available. tool_or_endpoint: nl -ba FILE | sed -n 'Np'. argument_sourcing: FILE and N from the AG verdict; repo path from the checked-out branch. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as AG line-number fabrication risk per BQ-COUNCIL-AG-LINE-NUMBER-VERIFICATION and verify every cited line before promoting the verdict. expected_failures: treating fabricated lines as confirmed audit evidence. next_step_success: accept only verified claims and record unverified ones as unsupported. next_step_failure: request a corrected review without line-number dependence.
    expected_answers:
      - kind: tool_call
        tool: nl -ba FILE | sed -n 'Np'
        argument_keys: [FILE, N]
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-01, F-01, agent-dispatch:G-02]
    scenario: |
      id: G-01. trigger: AG MAX_TURNS=25 exhaustion leaves a Gate 2 review without a verdict. pre_conditions: exhausted transcript, original diff, and target review questions are preserved. tool_or_endpoint: council_request(action=review, agent=ag, prompt=<diff-only narrowed prompt>, context_refs=<changed files>). argument_sourcing: changed files from git diff --name-only; review questions from the failed prompt; timeout cap from infra:council-comms. idempotency: IDEMPOTENT_WITH_KEY on failed_task_id + narrowed_prompt_digest. expected_success: AG returns a focused verdict over the exact diff. expected_failures: second timeout, unsupported broad architecture critique, or line-number fabrication. next_step_success: attach the replacement verdict and mark the failed task superseded. next_step_failure: use MP/DeepSeek verdicts and record AG non-response in the BQ.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [action, agent, prompt, context_refs]
        argument_values:
          action: review
          agent: ag
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-01, §D]
    scenario: |
      id: G-02. trigger: A Council verdict contains file:line claims from AG and the operator must decide whether they are reliable. pre_conditions: verdict, file path, line numbers, and checked-out commit are available. tool_or_endpoint: nl -ba FILE | sed -n 'Np'. argument_sourcing: FILE and N from each verdict citation; commit from the review record. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: every cited line is checked against the reviewed commit and the accepted finding text matches the actual line. expected_failures: wrong checkout, off-by-one citation, or fabricated line. next_step_success: keep verified claims and annotate unsupported claims. next_step_failure: reject the line-specific finding and request evidence-backed restatement.
    expected_answers:
      - kind: tool_call
        tool: nl -ba FILE | sed -n 'Np'
        argument_keys: [FILE, N]
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: |
      id: H-01. trigger: A proposal adds a new Council agent to active review rotation. pre_conditions: proposed agent role, auth scope, model frontier, and dispatch backend are known. tool_or_endpoint: infra:council-comms patch plus runbook update. argument_sourcing: roster and review_order from Living State; dispatch patterns from infra:council-comms; security rule from §H invariants. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as BREAKING because it changes dispatch_patterns, review_order, and 3-of-3 security rule math. expected_failures: calling it SAFE because code entry points stay the same. next_step_success: open a Gate 1/Gate 2 change with Council review. next_step_failure: block active dispatch until the policy is adjudicated.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [§H]
    scenario: |
      id: H-02. trigger: A proposal changes the frontier model for an existing Council agent. pre_conditions: prior model, proposed model, role, measured review quality, and cost/timeout implications are known. tool_or_endpoint: infra:council-comms.model_policy.agent_frontier_models patch. argument_sourcing: current model policy from Living State; performance evidence from dispatch history; affected runbook rows from §D. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as REVIEW and require evidence that the new model performs at or above the prior bar. expected_failures: treating the swap as documentation-only or ignoring role-specific quirks. next_step_success: update model_policy and runbooks after review. next_step_failure: keep the prior model frontier.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-03, §H, council-hall-deliberation:F-04, council-hall-deliberation:G-04]
    scenario: |
      id: AMB-01. trigger: A Gate 2 chunking spec gets conflicting MP and AG decomposition recommendations. pre_conditions: both verdicts, original spec, chunk-risk rationale, and BQ state are available. tool_or_endpoint: compare verdicts, then repair through Vulcan-direct fold or Council Hall only if evidence remains insufficient. argument_sourcing: claims from MP/AG transcripts; chunk boundaries from the spec; precedent from the S529 R2 Vulcan-direct fold pattern. idempotency: READ_ONLY_DIAGNOSTIC until a new spec patch is intentionally authored. expected_success: classify first as §F cross-vote divergence, not immediate §H evolution; redirect to §G repair by folding mandates into the spec or escalating to council-hall-deliberation:G-04 if the conflict is substantive. expected_failures: changing chunking rules prematurely, or picking one reviewer without preserving the dissent. next_step_success: produce a revised Gate 2 spec with both concerns resolved. next_step_failure: open Council Hall/Max adjudication.
    expected_answers:
      - kind: human_action
        verb: classify
        object: MP/AG chunk decomposition disagreement
        target: cross-vote divergence then council-hall-deliberation:G-04 before §H evolution
    weight: 0.08333333333333333
```

<!-- /catalog:historical -->

## §J. Lifecycle

Lifecycle metadata records the S1265 content-conformance refresh and registered scenario-harness pass.

```yaml lifecycle
last_refresh_session: S1265
last_refresh_commit: 03cd4c0
last_refresh_date: 2026-07-17T20:00:00Z
owner_agent: vulcan
refresh_triggers:
  - council_request interface or roster semantics change
  - active or retired Council member capability/status changes
  - cross-runbook reference convention changes
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: 0.16666666666666666
last_harness_date: 2026-07-18T08:36:20.840312Z
first_staleness_detected_at: null
```

The Council runbook scenario set is registered under `tests/fixtures/harness_scenarios/council/` and passed the S1265 conformant harness.

## §K. Conformance

Conformance fields for the S1265 content refresh.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1265 / 2026-07-17T20:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

The §K block records the strict-lint result; harness state is authoritative in §J.
