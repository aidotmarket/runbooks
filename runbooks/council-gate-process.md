---
system_name: council-gate-process
purpose_sentence: Council Build Queue gate-process runbook for operating the BQ four-gate flow and enforcing non-builder cross-review before completion.
owner_agent: mp
escalation_contact: vulcan
lifecycle_ref: §J
authoritative_scope: |
  Stable BQ gate mechanics, gate-transition reasoning, cross-review enforcement, and symptom/repair patterns. Live Council membership, review order, dispatch participants, model frontiers, and exceptional overrides are canonically tracked in the infra:council-comms Living State entity.

  Cross-runbook reference convention: same-file references use bare IDs such as `F-01` or `G-01`; cross-file references use `<file-stem>:<id>` such as `agent-dispatch:E-01`.
linter_version: 1.0.0
---

# Council Gate Process

## §A. Header

The YAML frontmatter above defines the §A header. This runbook documents the stable gate-process slice: Build Queue entity shape, Gate 1 through Gate 4 transitions, author/reviewer provenance, and the cross-review completion gate.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Build Queue entity tracking | SHIPPED | `build:bq-* Living State entities` | Gate transitions verified through BQ entity state review | 2026-04-29 |
| Gate 1 design review | SHIPPED | `build:bq-*.gate1` | MP/AG design-review artifacts attached to BQ records | 2026-04-29 |
| Gate 2 chunking and implementation spec | SHIPPED | `specs/BQ-*-GATE2.md` | Chunk specs reviewed before build dispatch | 2026-04-29 |
| Gate 3 post-build audit | SHIPPED | `build:bq-*.gate3` | Mandatory reviewer verdicts checked against commit SHAs | 2026-04-29 |
| Gate 4 production verification | SHIPPED | `build:bq-*.gate4` | Customer-perspective verification recorded before completion | 2026-04-29 |
| Cross-review completion enforcement | SHIPPED | `cross_review_gate.py` | Non-builder reviewer check required before `bq_complete` | 2026-04-29 |
| Author-mode dispatch binding | PARTIAL | `dispatch_mp_build` | Provenance captured operationally; stricter tokenization remains a follow-up | 2026-04-29 |
| Break-glass bypass | SHIPPED | `/var/tmp/koskadeux/break_glass` | Manual emergency path verified by operator cleanup procedure | 2026-04-29 |

## §C. Architecture & Interactions

The gate process is a stateful quality-control pipeline for `build:bq-*` work. A BQ starts as a problem or change request, moves through design, implementation planning, post-build audit, and production verification, then can close only when the reviewer set includes at least one approving agent that did not build the artifact.

Strategic why: the BQ system exists because Council work needs reproducible decision records, not just chat transcripts. The four gates separate four different risks: Gate 1 asks whether the work should be built, Gate 2 fixes the build plan and chunk boundaries, Gate 3 audits whether the code matches the approved plan, and Gate 4 verifies the customer-visible result. Cross-review is mandatory because a builder can miss their own integration mistake; requiring a non-builder reviewer creates independent evidence before `bq_complete`. Dispatch-binding tokens exist to distinguish author-mode work from review-mode work, preventing a review agent from accidentally becoming the builder of record.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| BQ Entity | `build:bq-* Living State entities` | gate fields, builders, reviewers, verdicts, body summary | Vulcan, MP, AG, DeepSeek, CC | Canonical work record for gate status and provenance. |
| Gate 1 Design | `build:bq-*.gate1` | problem statement, design verdicts, mandates | MP, AG, DeepSeek, Vulcan | Approves the shape of the work before implementation planning. |
| Gate 2 Chunking | `specs/BQ-*-GATE2.md` | chunk plan, files touched, ACs, risks, test plan | MP, Vulcan, builders | Converts approved design into bounded implementation work. |
| Gate 3 Audit | `build:bq-*.gate3` | commit SHAs, audit rounds, findings, mandates | MP, AG, DeepSeek | Verifies implemented changes against Gate 1 and Gate 2 evidence. |
| Gate 4 Verification | `build:bq-*.gate4` | production checks, customer-perspective verification | reviewer agents, Vulcan | Confirms the shipped behavior and closes the BQ only after review evidence exists. |
| Cross-Review Gate | `cross_review_gate.py` | builders, reviewers, `gateN.<agent>_verdict` fields | `bq_complete`, Living State | Requires `approved_reviewers - builders` to be non-empty. |
| Compliance Gate | `BQ-COUNCIL-COMPLIANCE-GATE-AUTHORING-DISTINCTION` | gate status, author-mode provenance | dispatch surfaces, BQ state | Blocks build dispatch when Gate 1 mandates are unresolved or author/review mode is ambiguous. |
| Break Glass | `/var/tmp/koskadeux/break_glass` | local filesystem sentinel | operator, completion path | Emergency-only bypass; must be removed immediately after use. |

The gate state shape is intentionally small: `gate1`, `gate2`, `gate3`, and `gate4` hold status and verdict evidence; `builders` records agents that modified files or authored commits; `reviewers` records agents that supplied review or verification verdicts. Verdict strings are accepted only when they communicate approval, verification, or pass semantics. Gate transitions should update the BQ entity and the human-readable handoff in the same session.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| MP | primary Gate 1-3 reviewer and frequent builder | Codex CLI / GPT-5.5 | full repo write | COMPLETE |
| AG | secondary cross-vote and independent reviewer | Gemini CLI / Gemini 3.1 Pro | repo read | COMPLETE |
| DeepSeek | full Council voter for read-oriented gate review | DeepSeek API / deepseek-v4-pro | repo read | COMPLETE |
| CC | fallback builder when MP timeout or complexity requires it | Claude Code / Opus | full repo write | COMPLETE |
| Vulcan | gate orchestrator and Living State operator | Anthropic API / MCP tools | gateway, LS, all repos | COMPLETE |

MP is primary because Codex CLI automation gives it reliable repo interaction and it has historically caught deeper wiring gaps in build chunks. AG is the cross-vote reviewer because Gemini 3.1 Pro gives strong independent reasoning, while its line-number fabrication risk means every cited line must be verified before Gate 3 evidence is accepted. DeepSeek is a full voter after S528 because 94 dispatches showed `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and a 4.7x crushed statistical record floor. CC is the fallback builder because it gives Opus-tier multi-file reasoning and a practical escape hatch when MP Codex CLI hits the 300s timeout. Vulcan owns orchestration because gate movement is stateful across specs, commits, reviews, and Living State.

## §E. Operate

```yaml operate
- id: E-01
  trigger: A new BQ needs Gate 1 design review before any implementation plan or build dispatch.
  pre_conditions: [bq_entity_exists, problem_statement_written, scope_and_out_of_scope_known, candidate_reviewer_available]
  tool_or_endpoint: bq_update(entity=build:bq-*, gate=gate1, status=<status>, reviewer_verdict=<verdict>)
  argument_sourcing:
    entity: use the Living State key for the BQ under review
    status: derive from the reviewer verdict using APPROVED, APPROVED_WITH_MANDATES, or REJECTED
    reviewer_verdict: attach MP first and add AG or DeepSeek when risk warrants cross-vote
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(entity + gate1 + reviewer + verdict_commit)
  expected_success: {shape: Gate 1 status plus reviewer verdict on the BQ entity, verification: read the entity back and confirm mandates are explicit}
  expected_failures:
    - {signature: missing_design_artifact, cause: BQ entity does not explain the problem, scope, or acceptance criteria}
    - {signature: unresolved_mandates, cause: Gate 1 is APPROVED_WITH_MANDATES and cannot yet dispatch build work}
  next_step_success: Author or update the Gate 2 chunking spec.
  next_step_failure: Return to design authoring or escalate ambiguous scope to Vulcan.
- id: E-02
  trigger: Gate 1 has passed and the BQ needs a chunked implementation plan.
  pre_conditions: [gate1_status_approved_or_mandates_resolved, spec_path_selected, files_touched_known, test_plan_known]
  tool_or_endpoint: specs/BQ-*-GATE2.md plus bq_update(entity=build:bq-*, gate=gate2, status=<status>)
  argument_sourcing:
    spec_path: use the BQ slug and canonical specs directory
    files_touched: derive from the approved design and repository survey
    status: set from MP review of the implementation spec
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(entity + spec_path + spec_commit)
  expected_success: {shape: reviewed Gate 2 spec with chunk ACs and test plan, verification: confirm the spec commit and BQ gate2 status match}
  expected_failures:
    - {signature: gate1_status_trap, cause: Gate 1 still says APPROVED_WITH_MANDATES after mandates were satisfied}
    - {signature: chunk_scope_gap, cause: Gate 2 does not name all files or acceptance checks}
  next_step_success: Dispatch the approved chunk build through the correct builder path.
  next_step_failure: Patch Gate 1 status to APPROVED when mandates are fulfilled or revise the chunk spec.
- id: E-03
  trigger: A chunk build has landed and must pass Gate 3 post-build audit.
  pre_conditions: [feature_branch_exists, commit_sha_known, gate2_spec_reviewed, builder_recorded]
  tool_or_endpoint: council_request(agent=mp, task=<audit_prompt>, allowed_tools=[Read,Grep,Glob,LS])
  argument_sourcing:
    audit_prompt: include Gate 1, Gate 2, commit SHA, changed files, and explicit read-only review instructions
    commit_sha: use the build commit being promoted
    builder_recorded: read from BQ entity builders list or infer from dispatch transcript before patching state
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(entity + gate3 + commit_sha + reviewer)
  expected_success: {shape: PASS, PASS_WITH_MANDATES, or FAIL verdict tied to the commit SHA, verification: verify cited file lines and attach the verdict}
  expected_failures:
    - {signature: authoring_distinction_trap, cause: a review dispatch performed writes and became builder evidence}
    - {signature: fabricated_line_reference, cause: reviewer cited non-existent or stale lines}
  next_step_success: Fix mandates or proceed to Gate 4 verification.
  next_step_failure: Re-dispatch read-only review or return the chunk to build repair.
- id: E-04
  trigger: Gate 3 has passed and the BQ is ready for production verification and completion.
  pre_conditions: [gate3_passed, production_or_customer_perspective_check_defined, non_builder_reviewer_available, break_glass_absent]
  tool_or_endpoint: bq_complete(entity=build:bq-*, verification=<customer_perspective_evidence>)
  argument_sourcing:
    verification: record endpoint checks, UI behavior, logs, or data validation from the customer perspective
    reviewers: read from BQ entity reviewers and `gate4.<agent>_verdict` fields
    builders: read from BQ entity builders before attempting completion
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(entity + gate4 + verification_digest + reviewer)
  expected_success: {shape: BQ completed with Gate 4 PASS and non-builder reviewer evidence, verification: confirm `approved_reviewers - builders` is non-empty}
  expected_failures:
    - {signature: cross_review_block, cause: only builders supplied approval or verification}
    - {signature: break_glass_left_enabled, cause: emergency sentinel was used and not removed}
  next_step_success: Close the session handoff with entity key, commit, and verification summary.
  next_step_failure: Use F-01, F-04, or agent-dispatch:E-02 to obtain valid non-builder review evidence.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Completion blocked by cross-review gate | Builder is the only approving reviewer, reviewer verdict field missing, or verdict string does not match approval regex | Compare `builders`, `reviewers`, and `gate4.<agent>_verdict`; compute `approved_reviewers - builders` manually | G-01 | CONFIRMED |
| F-02 | Gate 2 build dispatch blocked after Gate 1 APPROVED_WITH_MANDATES | Mandates were satisfied in prose but `gate1.status` was never patched from `APPROVED_WITH_MANDATES` to `APPROVED` | Read the BQ entity and compare Gate 1 mandate resolution notes to `gate1.status` | G-02 | CONFIRMED |
| F-03 | Ghost entity or stale BQ state appears during promotion | Session patched a wrong key, stale entity version, or handoff referenced a superseded BQ slug | Read the target `build:bq-*` entity, recent event history, and git branch evidence before promoting | G-03 | CONFIRMED |
| F-04 | Review-mode dispatch becomes authoring evidence | Prompt omitted read-only constraints or used builder dispatch for an audit task, triggering the authoring-distinction trap | Inspect dispatch transcript, file writes, and builder/reviewer lists for the same agent | G-04 | CONFIRMED |
| F-05 | Break-glass bypass used or left enabled | Emergency sentinel was touched for a gate false positive and not removed after completion | Check `/var/tmp/koskadeux/break_glass` and session notes for bypass rationale | G-05 | CONFIRMED |
| F-06 | Gate 3 audit contains unsupported line-number claims | Reviewer hallucinated line numbers or reviewed stale diff context | Verify every cited path and line against the commit under audit | G-06 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Cross-Review Gate
  root_cause: Completion requires at least one approving reviewer who is not also a builder, and the entity lacks that evidence.
  repair_entry_point: cross_review_gate.py
  change_pattern: Dispatch a read-only Gate 4 verification to AG, DeepSeek, or MP if MP was not the builder; patch `reviewers` and `gate4.<agent>_verdict` only after verifying the returned evidence.
  rollback_procedure: Remove only the invalid reviewer field if it was patched without evidence; keep valid builder and commit records intact.
  integrity_check: Confirm `approved_reviewers - builders` is non-empty before rerunning `bq_complete`.
- id: G-02
  symptom_ref: F-02
  component_ref: Compliance Gate
  root_cause: Gate 1 mandate status remained in the blocking state after mandates were resolved.
  repair_entry_point: build:bq-*.gate1
  change_pattern: Patch `gate1.status` from `APPROVED_WITH_MANDATES` to `APPROVED` only when the mandate-resolution evidence is present in the entity or spec.
  rollback_procedure: Restore `APPROVED_WITH_MANDATES` if the mandate evidence cannot be found.
  integrity_check: Read the entity back and confirm Gate 2 dispatch is unblocked for the intended chunk only.
- id: G-03
  symptom_ref: F-03
  component_ref: BQ Entity
  root_cause: Gate action targeted stale or wrong Living State data.
  repair_entry_point: state_get("build:bq-*")
  change_pattern: Reconcile entity key, branch, commit SHA, spec path, and handoff; patch the correct entity with an explicit supersedes note if needed.
  rollback_procedure: Revert only the mistaken state patch when it points to the wrong entity; never revert code commits without a separate decision.
  integrity_check: Confirm the promoted entity, branch HEAD, and spec all name the same BQ slug and commit.
- id: G-04
  symptom_ref: F-04
  component_ref: Compliance Gate
  root_cause: Author-mode and review-mode provenance were mixed, so the same agent may count as builder and reviewer.
  repair_entry_point: BQ-COUNCIL-COMPLIANCE-GATE-AUTHORING-DISTINCTION
  change_pattern: Discard the tainted review as completion evidence, preserve it as build context if useful, and redispatch a strict read-only review to a non-builder.
  rollback_procedure: Remove the tainted reviewer verdict from gate evidence while keeping the builder record.
  integrity_check: Verify no files changed during the replacement review dispatch.
- id: G-05
  symptom_ref: F-05
  component_ref: Break Glass
  root_cause: Emergency bypass sentinel bypassed normal gate enforcement or remained after the incident.
  repair_entry_point: /var/tmp/koskadeux/break_glass
  change_pattern: Remove the sentinel immediately after the emergency action, document the reason, and rerun the gate check without bypass.
  rollback_procedure: If completion depended solely on bypass, reopen the BQ state and collect normal review evidence.
  integrity_check: Confirm the sentinel path is absent and the entity has a normal non-builder verifier.
- id: G-06
  symptom_ref: F-06
  component_ref: Gate 3 Audit
  root_cause: Review evidence contains fabricated or stale line references.
  repair_entry_point: build:bq-*.gate3
  change_pattern: Verify each cited line; strike unsupported findings or redispatch with exact commit SHA and changed-file list.
  rollback_procedure: Mark the unsupported verdict superseded rather than deleting the transcript.
  integrity_check: Attach only findings whose cited files and lines exist at the audited commit.
```

## §H. Evolve

### §H.1 Invariants

- Every BQ gate transition must leave auditable state on the `build:bq-*` entity.
- Builder and reviewer provenance must remain separable.
- Gate 4 completion requires non-builder review evidence unless Max explicitly authorizes emergency break-glass use.
- Same-file §F/§G references use bare IDs; cross-runbook references use file-qualified IDs such as `agent-dispatch:F-04`.

### §H.2 BREAKING predicates

- Removing one of the four gates or collapsing Gate 3 and Gate 4 is BREAKING.
- Removing cross-review enforcement before `bq_complete` is BREAKING.
- Granting write-mode review authority to AG or DeepSeek without changing builder/reviewer provenance rules is BREAKING.
- Changing the BQ entity key shape away from `build:bq-*` is BREAKING.

### §H.3 REVIEW predicates

- Adding a new gate outcome such as `CONDITIONAL` is REVIEW.
- Changing dispatch participants for a gate is REVIEW.
- Adding an agent, retiring an agent, or changing the model frontier used for gate review is REVIEW.
- Increasing the per-dispatch cost cap for gate review is REVIEW.
- Changing the verdict regex or accepted completion language is REVIEW.

### §H.4 SAFE predicates

- Clarifying gate prose is SAFE when state fields and transition rules do not change.
- Adding another verification example to Gate 4 is SAFE.
- Updating symptom or repair text is SAFE when IDs, component names, and gate contracts remain stable.
- Correcting stale dates or commit pointers in §J or §K is SAFE when conformance meaning does not change.

### §H.5 Boundary definitions

#### module

The module boundary is the BQ gate-process slice: BQ entity fields, gate transition records, reviewer verdict evidence, completion checks, and emergency bypass handling.

#### public contract

The public contract is the operator-visible sequence Gate 1 design -> Gate 2 chunking -> Gate 3 audit -> Gate 4 verification -> completion, including accepted statuses and required evidence.

#### runtime dependency

A runtime dependency is any Living State surface, dispatch path, review transcript, filesystem sentinel, or commit reference needed to evaluate or move a BQ gate.

#### config default

A config default is any Council review order, dispatch participant set, model frontier, cost cap, or bypass policy read from `infra:council-comms`.

### §H.6 Adjudication

When agents disagree on the evolve class for a gate-process change, use the more restrictive class. Max resolves changes that affect completion enforcement, emergency bypass behavior, money/security impact, or active Council membership.

## §I. Scenario Set

C3 placeholder: the gate-process scenario set is populated in C5a.3. That chunk must add at least 5 scenarios scoped to gate flow with at least 2 operate scenarios, 1 isolate scenario, 1 repair scenario, and 1 evolve or ambiguous-symptom scenario. This placeholder intentionally omits the `yaml acceptance` block so linter v1.0.0 reports the single expected §I placeholder failure for this chunk.

## §J. Lifecycle

C3 placeholder: C5c populates final AC11 lifecycle fields after C5a.3 scenario authoring and C5b harness execution.

```yaml lifecycle
last_refresh_session: S530
last_refresh_commit: b49ec60
last_refresh_date: 2026-04-29T00:00:00Z
owner_agent: mp
refresh_triggers:
  - bq_gate_contract_change
  - cross_review_gate_change
  - infra_council_comms_drift
  - scheduled_cadence
scheduled_cadence: 90d
last_harness_pass_rate: 0.0
last_harness_date: 2026-04-29T00:00:00Z
first_staleness_detected_at: null
```

Current conformance_status is `provisional` per Gate 1 §10 until C5c finalizes lifecycle telemetry after scenario authoring, harness execution, and the Infisical cutover constraint. This field is prose-only here because runbook-lint v1.0.0 rejects `conformance_status` as an additional §K YAML key.

## §K. Conformance

C3 placeholder: C5c populates final conformance fields after C5a.3 scenario authoring and C5b harness execution. This chunk intentionally leaves §I as a placeholder, so one §I lint failure is expected.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S530 / 2026-04-29T00:00:00Z
last_lint_result: FAIL
trace_matrix_path: null
word_count_delta: null
```

`conformance_status: provisional` is intentionally not present in §K YAML until BQ-RUNBOOK-LINT-FRESHNESS-FIELDS v1.1.0 expands the schema.
