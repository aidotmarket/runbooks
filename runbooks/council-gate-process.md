---
title: Council Gate Process
owner: mp
last_verified: '2026-07-27'
aliases: []
error_signatures:
- authoring_distinction_trap
- break_glass_left_enabled
- chunk_scope_gap
- cross_review_block
- directional_evidence_missing
- fabricated_line_reference
- gate1_status_trap
- harness_bound_to_stale_code
- missing_design_artifact
- unresolved_mandates
---

# Council Gate Process

## Overview

This runbook documents the stable gate-process slice: Build Queue entity shape, Gate 1 through Gate 4 transitions, author/reviewer provenance, and the cross-review completion gate.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Build Queue entity tracking | SHIPPED | `build:bq-* Living State entities` | Gate transitions verified through BQ entity state review | 2026-04-29 |
| Gate 1 design review | SHIPPED | `build:bq-*.gate1` | CC/Kimi/GLM design-review artifacts attached to BQ records | 2026-07-27 |
| Gate 2 chunking and implementation spec | SHIPPED | `specs/BQ-*-GATE2.md` | Chunk specs reviewed before build dispatch | 2026-04-29 |
| Gate 3 post-build audit | SHIPPED | `build:bq-*.gate3` | Mandatory reviewer verdicts checked against commit SHAs | 2026-04-29 |
| Gate 4 production verification | SHIPPED | `build:bq-*.gate4` | Customer-perspective verification recorded before completion | 2026-04-29 |
| Cross-review completion enforcement | SHIPPED | `cross_review_gate.py` | Non-builder reviewer check required before `state_request(action=bq_complete)` | 2026-04-29 |
| Author-mode dispatch binding | PARTIAL | `dispatch_mp_build` | Provenance captured operationally; stricter tokenization remains a follow-up | 2026-04-29 |
| Break-glass bypass | SHIPPED | `/var/tmp/koskadeux/break_glass` | Manual emergency path verified by operator cleanup procedure | 2026-04-29 |

## Architecture & interactions

The gate process is a stateful quality-control pipeline for `build:bq-*` work. A BQ starts as a problem or change request, moves through design, implementation planning, post-build audit, and production verification, then can close only when the reviewer set includes at least one approving agent that did not build the artifact.

Strategic why: the BQ system exists because Council work needs reproducible decision records, not just chat transcripts. The four gates separate four different risks: Gate 1 asks whether the work should be built, Gate 2 fixes the build plan and chunk boundaries, Gate 3 audits whether the code matches the approved plan, and Gate 4 verifies the customer-visible result. Cross-review is mandatory because a builder can miss their own integration mistake; requiring a non-builder reviewer creates independent evidence before `state_request(action=bq_complete)`. Dispatch-binding tokens exist to distinguish author-mode work from review-mode work, preventing a review agent from accidentally becoming the builder of record.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| BQ Entity | `build:bq-* Living State entities` | gate fields, builders, reviewers, verdicts, body summary | Vulcan, Mars, MP, CC, Kimi, GLM | Canonical work record for gate status and provenance. |
| Gate 1 Design | `build:bq-*.gate1` | problem statement, design verdicts, mandates | CC, Kimi, GLM, Vulcan, Mars | Approves the shape of the work before implementation planning. |
| Gate 2 Chunking | `specs/BQ-*-GATE2.md` | chunk plan, files touched, ACs, risks, test plan | MP author; CC, Kimi, GLM reviewers; Vulcan, Mars | MP authors the bounded implementation plan; the active gate panel reviews it before build dispatch. |
| Gate 3 Audit | `build:bq-*.gate3` | commit SHAs, audit rounds, findings, mandates | CC, Kimi, GLM | Verifies implemented changes against Gate 1 and Gate 2 evidence. |
| Gate 4 Verification | `build:bq-*.gate4` | production checks, customer-perspective verification | reviewer agents, Vulcan | Confirms the shipped behavior and closes the BQ only after review evidence exists. |
| Cross-Review Gate | `cross_review_gate.py` | builders, reviewers, `gateN.<agent>_verdict` fields | `state_request(action=bq_complete)`, Living State | Requires `approved_reviewers - builders` to be non-empty. |
| Compliance Gate | `BQ-COUNCIL-COMPLIANCE-GATE-AUTHORING-DISTINCTION` | gate status, author-mode provenance | dispatch surfaces, BQ state | Blocks build dispatch when Gate 1 mandates are unresolved or author/review mode is ambiguous. |
| Break Glass | `/var/tmp/koskadeux/break_glass` | local filesystem sentinel | operator, completion path | Emergency-only bypass; must be removed immediately after use. |

The gate state shape is intentionally small: `gate1`, `gate2`, `gate3`, and `gate4` hold status and verdict evidence; `builders` records agents that modified files or authored commits; `reviewers` records agents that supplied review or verification verdicts. Verdict strings are accepted only when they communicate approval, verification, or pass semantics. Gate transitions should update the BQ entity and the human-readable handoff in the same session.

### Rational-use tiering and stopping rules (ADOPTED by Max, 2026-08-18, S1570)

Decision record: `decision:council-usage-guidelines-s1570` (Living State), consensus of CC, GLM, Kimi, and MP, adopted verbatim by Max. These rules implement CORE S3 risk-sizing operationally; they do not amend the constitution. The constitutional floor is untouched: security, auth, payments, and customer-data changes always take three reviewers unanimous, and the builder never reviews its own work.

**Tier rule.** A change's tier is the highest tier any hunk touches.

- **TIER 3 - three reviewers, unanimous (constitutional floor):** security, auth, payments, customer data, and the fail-closed envelope guarding them: spend/rate caps, session/token/output budgets, mutation fences, PII fields, new external egress, destructive migrations on customer tables. Tiering UP is always allowed; tiering below this floor is AMENDMENT-REQUIRED.
- **TIER 1 - one reviewer:** ordinary production behavior changes, APIs, non-sensitive migrations, jobs and schedules, deploy config, dependency bumps with runtime impact, prompt/model changes affecting product output, council/reviewer plumbing outside the Tier 3 envelope.
- **TIER 0 - tests plus recorded builder verification, no Council:** docs, comments, tests-only changes, formatting, copy, dead-code deletion, generated files and lockfiles, single values inside an already-reviewed bound. A document that encodes a load-bearing invariant on a Tier 3 system is at least Tier 1.

**Escalation triggers (any one raises the tier):** the diff touches a protected surface even incidentally; weakens a fail-closed default; changes a value a safety invariant depends on; runs an irreversible or data-dropping migration; adds a new dependency, external egress, or crypto primitive; deletes or weakens tests; follows an incident in the same module; a reviewer is uncertain or reviewers split.

**Stopping rules.** APPROVE_WITH_MANDATES ENDS the review when every mandate is objective, local, and verifiable by tests or deterministic evidence: the builder folds, runs the named checks, records the evidence, and ships. Re-review happens only when a mandate changes logic on a protected path, changes architecture or a trust boundary, or the required evidence fails - and then delta-scoped only, never a fresh full pass. A byte-identical resubmit is refused with the prior verdict. Hard caps: Tier 1 = 2 rounds, Tier 3 = 3 rounds. At the cap, stop: the spec is wrong, not the code - escalate to Max, revert, or re-scope. Tier 3 never force-ships at cap without unanimity.

**Effort budgets (written into the request preamble):** Tier 1 = diff plus direct callers, roughly 10-15 reviewer turns, one response. Tier 3 = full relevant scope, roughly 25-40 turns, independent verification of load-bearing claims only. On exhaustion the reviewer returns a partial verdict naming uncovered areas. Silence is never approval.

**Quota allocation:** reserve Kimi primarily for Tier 3 (its weekly quota is the scarce unanimity seat); route Tier 1 to a CC/GLM rotation.

**Degraded mode:** a missing response is a withheld gate, never a pass. Launcher circuit breaker: two delivery attempts, then mark the reviewer down and alert - no retry storms. Tier 0/1 proceed on tests plus builder verification (Tier 1 fails over to another reviewer). Tier 3 waits, or merges only under explicit logged Max authorization labeled UNREVIEWED with a tracked review-debt item and a mandatory retroactive review; making that lane standing policy is AMENDMENT-REQUIRED and was NOT adopted.

**Builder obligations that make lighter review safe:** specs carry explicit invariants, non-goals, acceptance criteria, and rollback; each material requirement maps to an automated test; the builder performs a mandatory recorded self-check (full diff read, requirement-to-evidence trace, secrets and migration safety, prescribed suite run, residual risk declared). This is builder verification, not self-review.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| MP | mandatory builder; not a gate voter | Codex CLI / gpt-5.6-sol | repository write only in explicit build/author mode | COMPLETE |
| CC | active gate voter | Claude Code read-only review path | repository read | COMPLETE |
| Kimi | active gate voter | shared provider read-only review loop / deployed registry-pinned Kimi Code model | bounded read-only at-SHA repository tools | COMPLETE |
| GLM | active gate voter | shared provider read-only review loop / z-ai/glm-5.2 | bounded read-only at-SHA repository tools | COMPLETE |
| AG | paused; explicit non-gate review only when live state permits | Gemini / Vertex | repository read | COMPLETE |
| DeepSeek | retired from the active gate roster | retained dispatch backend | no current gate authority | COMPLETE |
| Vulcan | gate orchestrator and Living State operator | GPT-5.6-sol / MCP tools | gateway, LS, all repos | COMPLETE |

MP is the mandatory builder and is excluded from voting on its own work. The active gate panel is exactly CC, Kimi, and GLM; Kimi replaced DeepSeek at S1319, DeepSeek is retired from voting, and AG is paused. Kimi and GLM use the shared bounded read-only exact-SHA repository review loop, while CC uses its read-only review path. Vulcan and Mars orchestrate as equal-authority non-voters. `infra:council-comms` remains canonical for live membership and model strings.

## How to operate

```yaml operate
- id: E-01
  trigger: A new BQ needs Gate 1 design review before any implementation plan or build dispatch.
  pre_conditions: [bq_entity_exists, problem_statement_written, scope_and_out_of_scope_known, candidate_reviewer_available]
  tool_or_endpoint: state_request(action=bq_update, bq_code=<code>, status=<status>, gate=1, note=<panel_evidence_refs>, session_id=<session>, gate_status_update=true, expected_version=<version>)
  argument_sourcing:
    bq_code: use the canonical BQ code from the Living State entity under review
    status: derive from the reviewer verdict using APPROVED, APPROVED_WITH_MANDATES, or REJECTED
    panel_evidence_refs: reference the complete valid CC/Kimi/GLM verdict artifacts required by current policy; MP remains builder-only
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
  tool_or_endpoint: specs/BQ-*-GATE2.md plus state_request(action=bq_update, bq_code=<code>, gate=2, status=<status>, note=<review_evidence>, session_id=<session>, gate_status_update=true, expected_version=<version>)
  argument_sourcing:
    spec_path: use the BQ slug and canonical specs directory
    files_touched: derive from the approved design and repository survey
    status: derive from the complete valid CC/Kimi/GLM review panel; MP authors the implementation spec and does not vote on it
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
  pre_conditions: [feature_branch_exists, commit_sha_known, gate2_spec_reviewed, builder_recorded, connected_client_schema_lists_every_required_voter]
  tool_or_endpoint: council_request(agent=<cc|kimi|glm>, mode=review, task=<audit_prompt>, cwd=<repo>, dispatch_sha=<commit_sha>) for every active voter
  argument_sourcing:
    audit_prompt: include Gate 1, Gate 2, commit SHA, changed files, and explicit read-only review instructions
    commit_sha: use the build commit being promoted
    builder_recorded: read from BQ entity builders list or infer from dispatch transcript before patching state
    reviewer_panel: read the exact active CC/Kimi/GLM roster from infra:council-comms; MP is the builder and cannot vote
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(entity + gate3 + commit_sha + reviewer)
  expected_success: {shape: APPROVE, APPROVED_WITH_MANDATES, or REJECT verdict tied to the commit SHA, verification: verify cited file lines and attach the verdict}
  expected_failures:
    - {signature: authoring_distinction_trap, cause: a review dispatch performed writes and became builder evidence}
    - {signature: fabricated_line_reference, cause: reviewer cited non-existent or stale lines}
    - {signature: schema_roster_mismatch, cause: upstream required-voter constants and the connected client council_request enum disagree; refresh or reconnect and fail closed}
  next_step_success: Fix mandates or proceed to Gate 4 verification.
  next_step_failure: Re-dispatch read-only review or return the chunk to build repair.
- id: E-04
  trigger: Gate 3 has passed and the BQ is ready for production verification and completion.
  pre_conditions: [gate3_passed, production_or_customer_perspective_check_defined, non_builder_reviewer_available, break_glass_absent]
  tool_or_endpoint: state_request(action=bq_complete, bq_code=<code>, summary=<summary>, gate=4, evidence_links=<links>, session_id=<session>, verification=<customer_perspective_evidence>)
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
  next_step_failure: Use F-01 or F-04 and obtain valid read-only evidence from the current CC/Kimi/GLM panel; AG advice, MP, and DeepSeek cannot satisfy the gate.
- id: E-05
  trigger: A guard-class (decides-something) change reaches Gate 4 and state_request(action=bq_complete) requires directional evidence, not prose, that the guard works in the deployed direction.
  pre_conditions: [gate3_passed, merge_sha_pinned, real_gate_implementation_importable, bq_entity_live, evidence_path_writable]
  tool_or_endpoint: pinned-worktree harness driving the REAL BuildCompletionGate.check with production-shaped state_request(action=bq_complete) payloads (pattern origin /tmp/kd-wt-guard-g4-s1305/.g4/harness.py, S1305, BQ-GUARD-DIRECTION-EVIDENCE-GATE-S1206 @ 4a29b132)
  argument_sourcing:
    merge_sha: pin a worktree at the exact merged SHA and sys.path the harness to it so the proof binds to shipped code, not a stale import
    bq_entity: use the real Living State BQ entity via live lookup; never a fixture entity
    git_range: derive the persisted branch range live from git, never hardcode
    verification_payload: construct the full directional-evidence dict (schema_version, guard_class, environment, refusal{input_variant, stimulus, expected_decision, observed_decision, observation_ref}, separation{principal_a, principal_b, binding_a, binding_b, observation_ref})
    cases: run all six directions - (A) prose-only verification must BLOCK, (B) spoofed observed_decision=allowed must BLOCK, (C) same-principal separation must BLOCK, (D) honest well-formed evidence must PASS, (E) override self-ack must stay INERT, (F) peer-ack must ACTIVATE
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(entity + gate4 + pinned_sha + case_set_digest)
  expected_success: {shape: exit 0 with per-case evidence.json (label, ok, gate outcome excerpt) at the pinned SHA, verification: every blocked case shows the gate refusal string and every accepted case shows the gate returning None; evidence.json referenced from gate4.evidence on the BQ entity}
  expected_failures:
    - {signature: directional_evidence_missing, cause: verification is prose or lacks the required refusal/separation structure, so the gate blocks an honest completion attempt}
    - {signature: harness_bound_to_stale_code, cause: harness imported the long-running service or an unpinned checkout instead of the pinned merge-SHA worktree, proving the wrong code}
  next_step_success: Attach evidence.json to gate4.evidence, run the live post-restart probes per activation-verification, then state_request(action=bq_complete).
  next_step_failure: Rebuild the harness against the pinned SHA or repair the directional-evidence payload; do not weaken the gate to admit prose.
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Completion blocked by cross-review gate | Builder is the only approving reviewer, reviewer verdict field missing, or verdict string does not match approval regex | Compare `builders`, `reviewers`, and `gate4.<agent>_verdict`; compute `approved_reviewers - builders` manually | G-01 | CONFIRMED |
| F-02 | Gate 2 build dispatch blocked after Gate 1 APPROVED_WITH_MANDATES | Mandates were satisfied in prose but `gate1.status` was never patched from `APPROVED_WITH_MANDATES` to `APPROVED` | Read the BQ entity and compare Gate 1 mandate resolution notes to `gate1.status` | G-02 | CONFIRMED |
| F-03 | Ghost entity or stale BQ state appears during promotion | Session patched a wrong key, stale entity version, or handoff referenced a superseded BQ slug | Read the target `build:bq-*` entity, recent event history, and git branch evidence before promoting | G-03 | CONFIRMED |
| F-04 | Review-mode dispatch becomes authoring evidence | Prompt omitted read-only constraints or used builder dispatch for an audit task, triggering the authoring-distinction trap | Inspect dispatch transcript, file writes, and builder/reviewer lists for the same agent | G-04 | CONFIRMED |
| F-05 | Break-glass bypass used or left enabled | Emergency sentinel was touched for a gate false positive and not removed after completion | Check `/var/tmp/koskadeux/break_glass` and session notes for bypass rationale | G-05 | CONFIRMED |
| F-06 | Gate 3 audit contains unsupported line-number claims | Reviewer hallucinated line numbers or reviewed stale diff context | Verify every cited path and line against the commit under audit | G-06 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Cross-Review Gate
  root_cause: Completion requires at least one approving reviewer who is not also a builder, and the entity lacks that evidence.
  repair_entry_point: cross_review_gate.py
  change_pattern: Dispatch read-only Gate 4 verification to the current CC/Kimi/GLM panel; patch `reviewers` and `gate4.<agent>_verdict` only after verifying each returned result and preserving builder exclusion.
  rollback_procedure: Remove only the invalid reviewer field if it was patched without evidence; keep valid builder and commit records intact.
  integrity_check: Confirm `approved_reviewers - builders` is non-empty before rerunning `state_request(action=bq_complete)`.
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
  repair_entry_point: state_request(action=get, key=build:bq-*)
  change_pattern: Reconcile entity key, branch, commit SHA, spec path, and handoff; patch the correct entity with an explicit supersedes note if needed.
  rollback_procedure: Revert only the mistaken state patch when it points to the wrong entity; never revert code commits without a separate decision.
  integrity_check: Confirm the promoted entity, branch HEAD, and spec all name the same BQ slug and commit.
- id: G-04
  symptom_ref: F-04
  component_ref: Compliance Gate
  root_cause: Author-mode and review-mode provenance were mixed, so the same agent may count as builder and reviewer.
  repair_entry_point: BQ-COUNCIL-COMPLIANCE-GATE-AUTHORING-DISTINCTION
  change_pattern: Discard the tainted review as completion evidence, preserve it as build context if useful, and redispatch strict read-only review to the required current CC/Kimi/GLM voter; MP, AG, and DeepSeek cannot replace that voter.
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

## Changes and maintenance

### Changes and maintenance.1 Invariants

- Every BQ gate transition must leave auditable state on the `build:bq-*` entity.
- Builder and reviewer provenance must remain separable.
- Gate 4 completion requires non-builder review evidence unless Max explicitly authorizes emergency break-glass use.
- Same-file When it breaks/Repair references use bare IDs; cross-runbook references use file-qualified IDs such as `agent-dispatch:F-04`.

### Changes and maintenance.2 BREAKING predicates

- Removing one of the four gates or collapsing Gate 3 and Gate 4 is BREAKING.
- Removing cross-review enforcement before `state_request(action=bq_complete)` is BREAKING.
- Granting write-mode authority to any gate voter, or restoring retired/paused voter authority without an approved roster change, is BREAKING.
- Changing the BQ entity key shape away from `build:bq-*` is BREAKING.

### Changes and maintenance.3 REVIEW predicates

- Adding a new gate outcome such as `CONDITIONAL` is REVIEW.
- Changing dispatch participants for a gate is REVIEW.
- Adding an agent, retiring an agent, or changing the model frontier used for gate review is REVIEW.
- Increasing the per-dispatch cost cap for gate review is REVIEW.
- Changing the verdict regex or accepted completion language is REVIEW.

### Changes and maintenance.4 SAFE predicates

- Clarifying gate prose is SAFE when state fields and transition rules do not change.
- Adding another verification example to Gate 4 is SAFE.
- Updating symptom or repair text is SAFE when IDs, component names, and gate contracts remain stable.
- Correcting stale dates or commit pointers in Maintenance or §K is SAFE when conformance meaning does not change.

### Changes and maintenance.5 Boundary definitions

#### module

The module boundary is the BQ gate-process slice: BQ entity fields, gate transition records, reviewer verdict evidence, completion checks, and emergency bypass handling.

#### public contract

The public contract is the operator-visible sequence Gate 1 design -> Gate 2 chunking -> Gate 3 audit -> Gate 4 verification -> completion, including accepted statuses and required evidence.

#### runtime dependency

A runtime dependency is any Living State surface, dispatch path, review transcript, filesystem sentinel, or commit reference needed to evaluate or move a BQ gate.

#### config default

A config default is any Council review order, dispatch participant set, model frontier, cost cap, or bypass policy read from `infra:council-comms`.

### Changes and maintenance.6 Adjudication

When agents disagree on the evolve class for a gate-process change, use the more restrictive class. Max resolves changes that affect completion enforcement, emergency bypass behavior, money/security impact, or active Council membership.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, Architecture & interactions, agent-dispatch:E-03]
    scenario: |
      id: E-01. trigger: A new BQ has a written problem statement and needs Gate 1 design review before any Gate 2 spec or author-mode build dispatch. pre_conditions: build:bq-* entity exists, scope and out-of-scope are explicit, the live CC/Kimi/GLM panel is available, and no chunk spec has been promoted. tool_or_endpoint: state_request(action=bq_update, bq_code=<code>, gate=1, status=<status>, note=<panel_evidence_refs>, session_id=<session>, gate_status_update=true, expected_version=<version>). argument_sourcing: BQ code and version from Living State; reviewer panel from infra:council-comms; status from the complete valid panel using APPROVED, APPROVED_WITH_MANDATES, or REJECTED; note from immutable verdict references. idempotency: IDEMPOTENT_WITH_KEY on BQ code + gate1 + reviewer + verdict_commit. expected_success: Gate 1 status and references to the complete CC/Kimi/GLM verdict set, including mandates, are attached to the BQ entity with design evidence. expected_failures: missing problem statement, missing/malformed/model-mismatched active voter, unresolved mandates hidden in prose, or accidental author dispatch before Gate 1 is settled. next_step_success: author the Gate 2 chunking spec only after status is APPROVED or mandates are resolved. next_step_failure: return to design authoring or escalate ambiguous scope to Vulcan; never substitute MP, AG, or DeepSeek.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, bq_code, status, gate, note, session_id, gate_status_update, expected_version]
        argument_values:
          action: bq_update
          gate: 1
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02, F-02, G-02]
    scenario: |
      id: E-02. trigger: Gate 1 has passed and the BQ needs a bounded Gate 2 implementation spec before chunk build dispatch. pre_conditions: gate1.status is APPROVED or mandate-resolution evidence exists, spec path is selected, files touched and test plan are known, the live CC/Kimi/GLM panel is available, and compliance gate state is readable. tool_or_endpoint: specs/BQ-*-GATE2.md plus state_request(action=bq_update, bq_code=<code>, gate=2, status=<status>, note=<review_evidence>, session_id=<session>, gate_status_update=true, expected_version=<version>). argument_sourcing: spec_path from BQ slug; files_touched from repository survey and approved design; status from the complete valid CC/Kimi/GLM implementation-spec review; MP authors but does not vote. idempotency: IDEMPOTENT_WITH_KEY on BQ code + spec_path + spec_commit. expected_success: panel-reviewed Gate 2 spec names chunk ACs, file scope, risks, and tests, and BQ gate2 state matches the spec commit. expected_failures: Gate 1 still says APPROVED_WITH_MANDATES after mandates were satisfied, a missing/malformed/model-mismatched active voter, chunk scope omits affected files, or dispatch proceeds with no reviewed spec. next_step_success: dispatch the approved chunk build through the MP builder path. next_step_failure: apply G-02 or revise the Gate 2 spec before dispatch; never substitute MP, AG, or DeepSeek for a voter.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, bq_code, status, gate, note, session_id, gate_status_update, expected_version]
        argument_values:
          action: bq_update
          gate: 2
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03, F-04, agent-dispatch:E-03]
    scenario: |
      id: E-03. trigger: A chunk build commit has landed and Gate 3 must audit it against Gate 1 and Gate 2 evidence. pre_conditions: feature branch exists, commit SHA is known, Gate 2 spec is reviewed, builder is recorded, the live CC/Kimi/GLM roster is confirmed, and every reviewer dispatch is read-only. tool_or_endpoint: council_request(agent=<cc|kimi|glm>, mode=review, task=<audit_prompt>, cwd=<repo>, dispatch_sha=<commit_sha>) once for each active voter. argument_sourcing: audit_prompt includes Gate 1, Gate 2, commit SHA, changed files, and explicit no-write instructions; reviewer panel comes from infra:council-comms; builder comes from BQ entity or dispatch transcript; commit comes from git rev-parse or the build handoff. idempotency: IDEMPOTENT_WITH_KEY on entity + gate3 + commit_sha + reviewer. expected_success: a complete valid CC/Kimi/GLM panel returns verdicts tied to the audited commit, with line claims verified before attachment. expected_failures: missing/malformed/model-mismatched voter, review-mode dispatch writes files and becomes authoring evidence, stale diff context, or fabricated line references. next_step_success: fix mandates or move to Gate 4 verification only after the required panel passes. next_step_failure: redispatch the failed active voter read-only or return the chunk to build repair; never substitute MP, AG, or DeepSeek.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha]
        argument_values:
          agent: cc
          mode: review
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha]
        argument_values:
          agent: kimi
          mode: review
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha]
        argument_values:
          agent: glm
          mode: review
    weight: 0.08333333333333333
  - id: I-04
    type: operate
    refs: [E-04, F-01, agent-dispatch:E-02]
    scenario: |
      id: E-04. trigger: Gate 3 has passed and the BQ is ready for Gate 4 production verification plus completion. pre_conditions: gate3 passed, customer-perspective check is defined, reviewers and builders are readable, non-builder reviewer is available, and break_glass sentinel is absent. tool_or_endpoint: state_request(action=bq_complete, bq_code=<code>, summary=<summary>, gate=4, evidence_links=<links>, session_id=<session>, verification=<customer_perspective_evidence>). argument_sourcing: verification from endpoint checks, UI behavior, logs, or data validation; reviewers from BQ reviewers and gate4.<agent>_verdict fields; builders from BQ builders. idempotency: IDEMPOTENT_WITH_KEY on BQ code + gate4 + verification_digest + reviewer. expected_success: BQ completes only when Gate 4 PASS evidence exists and approved_reviewers - builders is non-empty. expected_failures: only builders approved, non-builder verdict says REQUEST_CHANGES, approval wording misses the accepted regex, or break_glass remains enabled. next_step_success: close handoff with entity key, commit, verification, and reviewer summary. next_step_failure: obtain valid non-builder verification before retrying state_request(action=bq_complete).
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, bq_code, summary, gate, evidence_links, session_id, verification]
        argument_values:
          action: bq_complete
          gate: 4
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-02, G-02, E-02]
    scenario: |
      id: F-02. trigger: Gate 2 build dispatch is blocked even though mandate-resolution notes say Gate 1 work was satisfied. pre_conditions: BQ entity, Gate 1 verdict, mandate-resolution evidence, and dispatch block message are available. tool_or_endpoint: state_request(action=get, key=build:bq-*). argument_sourcing: entity key from blocked dispatch; mandate evidence from BQ body and spec; status from gate1.status. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify the block as the Gate 1 APPROVED_WITH_MANDATES compliance trap when prose is resolved but status still blocks downstream dispatch. expected_failures: bypassing the compliance gate, creating a new BQ, or editing Gate 2 before fixing the stale Gate 1 status. next_step_success: apply G-02 and read the entity back. next_step_failure: keep dispatch blocked and return to mandate resolution.
    expected_answers:
      - kind: human_action
        verb: classify
        object: Gate 1 APPROVED_WITH_MANDATES trap
        target: G-02 status patch
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-03, G-03]
    scenario: |
      id: F-03. trigger: Promotion shows a ghost entity from a BQ-code commit, such as the S407 fix path, and the visible BQ state does not match branch evidence. pre_conditions: target build:bq-* key, recent event history, git branch, commit SHA, and handoff text are available. tool_or_endpoint: state_request(action=get, key=build:bq-*) plus git log --oneline. argument_sourcing: entity key from promotion command; commit from git; slug and branch from handoff. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as stale or wrong Living State targeting before promoting, and identify the correct entity, branch HEAD, spec path, and commit. expected_failures: completing the ghost entity, reverting code to make state match, or patching multiple entities without a supersedes note. next_step_success: apply G-03 to reconcile the intended entity. next_step_failure: pause promotion for Vulcan state adjudication.
    expected_answers:
      - kind: human_action
        verb: reconcile
        object: ghost BQ entity against branch and commit evidence
        target: G-03 correct entity patch
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [F-01, G-01, E-04]
    scenario: |
      id: F-01. trigger: state_request(action=bq_complete) refuses a BQ because the only non-builder Gate 4 verdict is REQUEST_CHANGES. pre_conditions: builders list, reviewers list, gate4.<agent>_verdict fields, and completion error are available. tool_or_endpoint: cross_review_gate.py evaluation or manual approved_reviewers - builders computation. argument_sourcing: builder and reviewer sets from BQ entity; approval semantics from verdict strings; failing verdict from Gate 4 field. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as a cross-review gate block because REQUEST_CHANGES is reviewer evidence but not approving evidence. expected_failures: counting a builder PASS as independent review, regex-forcing the verdict text, or using break_glass without emergency authorization. next_step_success: get a real non-builder PASS or address requested changes. next_step_failure: leave the BQ open.
    expected_answers:
      - kind: human_action
        verb: compute
        object: approved_reviewers minus builders
        target: F-01 cross-review block
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-02, F-02, E-02]
    scenario: |
      id: G-02. trigger: Gate 1 mandates are demonstrably resolved, but gate1.status still blocks Gate 2 chunk build dispatch. pre_conditions: original Gate 1 mandate text, resolution evidence, BQ entity version, and intended Gate 2 spec are present. tool_or_endpoint: state_request(action=bq_update, bq_code=<code>, gate=1, status=APPROVED, note=<resolution_evidence>, session_id=<session>, gate_status_update=true, expected_version=<version>). argument_sourcing: BQ code and version from blocked build; resolution evidence from entity or spec; status from the compliance gate contract. idempotency: IDEMPOTENT_WITH_KEY on BQ code + gate1 + approved_patch + evidence_digest. expected_success: gate1.status changes from APPROVED_WITH_MANDATES to APPROVED, the resolution note remains auditable, and only the intended chunk is unblocked. expected_failures: approving without evidence, deleting mandate history, or patching the wrong BQ key. next_step_success: rerun the Gate 2 dispatch precheck. next_step_failure: restore APPROVED_WITH_MANDATES and finish mandate work.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, bq_code, status, gate, note, session_id, gate_status_update, expected_version]
        argument_values:
          action: bq_update
          gate: 1
          status: APPROVED
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-03, F-03]
    scenario: |
      id: G-03. trigger: Promotion found ghost BQ entities or stale keys whose state diverges from the branch, and the operator must clean them without touching code commits. pre_conditions: wrong entity key, correct entity key, branch HEAD, affected commit, and evidence trail are known. tool_or_endpoint: state_request(action=bq_bulk_update, operations=[{bq_code=<ghost>, status=cancelled, note=<superseded_by_correct_entity>, expected_version=<version>}], session_id=<session>). argument_sourcing: ghost BQ codes and versions from state search; correct entity and commit from git and handoff; note from reconciliation evidence. idempotency: IDEMPOTENT_WITH_KEY on sorted(ghost_keys) + correct_entity + commit. expected_success: ghost entities are canceled or annotated as superseded, correct entity remains promoted, and branch evidence is unchanged. expected_failures: canceling the live BQ, reverting code, or hiding stale history. next_step_success: retry promotion against the correct BQ. next_step_failure: escalate Living State repair to Vulcan.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, operations, session_id]
        argument_values:
          action: bq_bulk_update
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [Changes and maintenance, E-01, E-04]
    scenario: |
      id: H-01. trigger: A proposal changes the BQ process from four gates to three by merging Gate 3 audit and Gate 4 verification. pre_conditions: proposed flow, affected BQ entity fields, completion behavior, and cross-review impact are described. tool_or_endpoint: runbook and gate-state contract patch. argument_sourcing: current public contract from Changes and maintenance.5; invariants from Changes and maintenance.1; completion enforcement from Cross-Review Gate. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as BREAKING because it removes or collapses a gate and changes the public transition contract before state_request(action=bq_complete). expected_failures: calling it REVIEW because reviewers still exist, or treating it as prose-only cleanup. next_step_success: open a Gate 1/Gate 2 change with full Council review. next_step_failure: keep the four-gate flow unchanged.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [Changes and maintenance, F-01, G-01]
    scenario: |
      id: H-02. trigger: A proposal changes cross-review concurrence so any reviewer verdict, including REQUEST_CHANGES, can unblock completion if a builder also passes. pre_conditions: proposed rule text, current approval regex, builder/reviewer provenance model, and security impact are known. tool_or_endpoint: cross_review_gate.py plus runbook policy patch. argument_sourcing: current concurrence rule from Architecture & interactions and How to operate-04; review predicates from Changes and maintenance.3; invariants from Changes and maintenance.1. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as REVIEW at minimum because it changes accepted completion language and verdict semantics; escalate toward BREAKING if it removes non-builder approving evidence. expected_failures: treating it as SAFE wording, or accepting REQUEST_CHANGES as approval in an active BQ. next_step_success: require Council review before implementation. next_step_failure: preserve current cross-review gate behavior.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-02, F-03, G-03]
    scenario: |
      id: AMB-01. trigger: A build's chunks_complete count drifts from main after a merge, and Gate 2 status, reconciler output, and Living State do not agree. pre_conditions: main branch BQ state, feature branch BQ state, Gate 2 spec, reconciler transcript, and current commit are available. tool_or_endpoint: compare Gate 2 spec, state_request(action=get, key=build:bq-*), and git diff origin/main...HEAD. argument_sourcing: chunks_complete from Living State; expected chunks from the spec; branch drift from git; reconciler limitations from recent state notes. idempotency: READ_ONLY_DIAGNOSTIC until the root cause is identified. expected_success: hold three hypotheses open: Gate 2 may be incomplete, reconciler may be unable to infer unsupported chunk_plan_unavailable schemas such as BQ-LS-BUILD-QUEUE-AUTORECONCILE-CHUNK-PLAN-SCHEMA/S530, or Living State may be stale. expected_failures: marking Gate 2 complete from a count alone, bypassing reconcile without audit justification, or rewriting the spec to match stale state. next_step_success: pick the evidence-backed repair path, using bypass_reconcile only with an audit-justified note for unsupported BQ schemas. next_step_failure: leave completion blocked pending Vulcan adjudication.
    expected_answers:
      - kind: human_action
        verb: triage
        object: chunks_complete drift across spec, git, reconciler, and Living State
        target: evidence-backed repair path
    weight: 0.08333333333333333
```

## Maintenance

Lifecycle metadata records the S1369 gate-roster refresh. The most recent registered scenario-harness pass remains the earlier S1265 run.

```yaml lifecycle
last_refresh_session: S1369
last_refresh_commit: 217ff63
last_refresh_date: 2026-07-27T22:12:57Z
owner_agent: mp
refresh_triggers:
  - BQ gate lifecycle or state entity contract changes
  - cross-review-gate enforcement changes
  - chunk approval, closeout, or production verification policy changes
scheduled_cadence: 90d
first_staleness_detected_at: null
```
