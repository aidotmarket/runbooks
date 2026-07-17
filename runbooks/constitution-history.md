---
runbook_id: constitution-history
domain: boot-kernel
status: ACTIVE
authoritative_for:
  - topic: constitution-history
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: constitution_source_drift
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: max
last_verified_at: 2026-07-17
system_name: constitution-history
purpose_sentence: This companion indexes constitutional amendments and prior versions while preserving current CORE as the sole normative constitutional authority.
owner_agent: max
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Delivery companion for amendment provenance, prior-version retrieval, source hashing, and historical audits; it does not authorize constitutional change.
linter_version: 1.0.0
---

# Constitution History

## §A. Header

The frontmatter is authoritative for catalog identity. **Authority: historical delivery companion.** Current full CORE is the sole normative constitution and prevails over every historical version, commit message, amendment record, and this companion. Historical text never authorizes current behavior.

**Fetch trigger:** amendment, provenance, or historical audit.

**Source constitution:** CORE v9.11, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`, version preamble and final amendment clause; §5 supplies the referenced decision rules.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Current constitution provenance | SHIPPED | `infra:constitution` | Byte hash and git mirror comparison | 2026-07-17 |
| Amendment record history | SHIPPED | `infra:constitution` | Entity history read | 2026-07-17 |
| Prior-version retrieval | SHIPPED | `docs/core/CORE.md` | Git object retrieval by full SHA | 2026-07-17 |
| Amendment procedure routing | SHIPPED | `constitution-amendment.md` | Gate and Max-approval evidence audit | 2026-07-17 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Current Constitution | `infra:constitution.body.content` | Living State | Session boot and amendment workflow | Sole current normative authority. |
| Git Mirror | `docs/core/CORE.md` | Git history | Source hashing and prior versions | Must be byte-identical to current content when used as source. |
| Amendment Records | `infra:constitution` entity history | Living State history | Provenance audit | Records approvals, rationale, and changes. |
| Amendment Procedure | `constitution-amendment.md` | Runbooks git history | Council and Max approval | Procedure only; cannot self-authorize a change. |
| Prior Git Objects | Full commit SHA | Backend repository object database | Historical audit | Retrieve exact prior text without treating it as current. |

### Normative projection — CORE v9.11 preamble

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> **Version:** 9.11

> **Last Updated:** 2026-07-16 (S1242 — amendment process tightened: constitution changes now require a unanimous Council gate (CC, DeepSeek, GLM) PLUS Max's direct approval, replacing 'Max approval + one peer review'; procedure in `aidotmarket/runbooks` → `constitution-amendment.md`. Full amendment history lives in Living State (`infra:constitution` amendment records + entity history) and in git history of this file. Current roster and consensus rules: §4–§5. Prior bump: 9.10, S1242 §3 2-Strike investigate-and-correct amendment. Max-approved S1242; Vulcan ratification of 9.10 and 9.11 requested under the outgoing rule.)

### Normative projection — CORE final amendment clause

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> This document is the canonical agent constitution for ai.market. It holds invariants only. Amendments require a unanimous Council gate (CC, DeepSeek, GLM — 3/3 valid verdicts, per §5 decision rules) AND Max's direct approval; either instance may then apply the approved change. Procedure: `aidotmarket/runbooks` → `constitution-amendment.md`.

### Version index

The table is historical retrieval metadata derived from backend Git history. It is not normative text and does not replace Living State amendment records.

| Version | Git commit | Date | Historical change summary |
|---|---|---|---|
| 9.11 | `6851a671a7adb0a7511162b0c5bd1939cb274162` | 2026-07-16 | Unanimous Council gate plus Max direct approval required for amendments. |
| 9.10 | `356a2dfe947d8e84be288437b6407e226d0dc1a2` | 2026-07-16 | Two-strike rule changed to investigate and correct before abort when possible. |
| 9.9 | `76a5d193abf2b00e3c052b5eca312e330087310f` | 2026-07-15 | Header history prose trimmed without invariant change. |
| 9.8 | `012a06f7680e9e5e857914fb24994b36ae8bc3d3` | 2026-07-15 | Council roster changed to CC, DeepSeek, and GLM voters with MP builder-only and AG paused. |
| 9.7 | `5155acc5a89aef6146e45fef0fcb690fd845f74f` | 2026-07-02 | Database-only handoff and fail-closed session close. |
| 9.4 | `3436ac0e79e391f5b5a8310174c2639ceb63fc3c` | 2026-06-23 | Git mirror synchronized to the ratified 9.4 content. |
| 9.2 | `97331e21c6bfe602896cbafef33ec32dfe18da69` | 2026-06-11 | Federated learning deferred, language-first invariants added, peer symmetry recorded. |
| 9.1 | `7993b4d0d22f0b4ea440ea8cbcbe5b9a3056099d` | 2026-06-09 | Product split and runbook-first discovery revisions. |
| 9.0 | `8cccfb91d821a72f4b5ec343f17c583707a0eb7e` | 2026-05-30 | Peers model, Design Charter reconciliation, invariants-only frame. |
| 8.0 | `b3fc6a563e0fb46450dcaabe7bceacd6c03c3347` | 2026-05-01 | Strategic shift refresh. |
| 7.4 | `378f4621f4cf8f4b6f85fbcea2f8c5985bfd57b9` | 2026-04-07 | AIM Node product description era. |
| 7.3 | `dedc81ee65b62524f9354c1cb086831b2380e8ae` | 2026-03-22 | Gate 4, Council membership, and tool-name refresh. |
| 7.1 | `da77f745799be351583de20b9faabf24b83dcf4d` | 2026-03-12 | Council-reviewed source precedence and execution restructure. |
| 6.3 | `3d2435c2c80d1741a44f594dedc3a9b36102dc5a` | 2026-03-01 | CRM agent discovery additions. |
| 6.0 | `29cebb46b36576182ee44815e4e9a9fdcc031711` | 2026-02-23 | Agent constitution restructure. |

Use full Git SHAs for retrieval. Intermediate commits can share a version label; inspect commit chronology and exact bytes rather than inferring semantics from version numbers alone.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Audit current and prior constitutional sources | Living State and Git read | Read | COMPLETE |
| CC, DeepSeek, GLM | Supply amendment-gate verdicts | Council review | Read-only | COMPLETE |
| Max | Directly approve or reject an amendment | Human decision | Final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An audit needs the exact current constitution and its source hash.
  pre_conditions: [living_state_available, git_mirror_available]
  tool_or_endpoint: state_get("infra:constitution") plus git hash-object docs/core/CORE.md
  argument_sourcing: {content: use exact current body content bytes, mirror: use the canonical backend Git file}
  idempotency: IDEMPOTENT
  expected_success: {shape: byte-identical current sources and one SHA-256, verification: compare exact bytes before accepting the mirror}
  expected_failures: [{signature: constitution_source_drift, cause: Living State and the selected Git mirror differ or a moved stub was hashed}]
  next_step_success: Record the exact source and hash in the dependent artifact.
  next_step_failure: Stop projection or amendment work until current authority is reconciled.
- id: E-02
  trigger: A provenance audit needs a prior constitution version.
  pre_conditions: [full_commit_sha_known, backend_repository_available]
  tool_or_endpoint: git show <sha>:docs/core/CORE.md
  argument_sourcing: {sha: use the full commit from verified Git history}
  idempotency: IDEMPOTENT
  expected_success: {shape: exact historical CORE bytes, verification: record commit SHA version label and content digest}
  expected_failures: [{signature: prior_version_unresolved, cause: branch name, abbreviated ambiguity, wrong repository, or missing object was used}]
  next_step_success: Compare history without applying it as current authority.
  next_step_failure: Fetch the verified object or keep the historical claim unproven.
- id: E-03
  trigger: A proposed constitutional semantic change needs authorization.
  pre_conditions: [exact_diff_written, rationale_written, current_source_hash_known]
  tool_or_endpoint: constitution-amendment.md procedure
  argument_sourcing: {council: require valid CC DeepSeek and GLM verdicts, max: require direct approval, diff: bind all evidence to exact bytes}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(current_sha + proposed_diff + verdict_set + max_approval)
  expected_success: {shape: authorized exact amendment with complete provenance, verification: validate 3 of 3 verdicts and direct Max approval before apply}
  expected_failures: [{signature: amendment_authority_incomplete, cause: diff, unanimous valid panel, or direct Max approval is missing}]
  next_step_success: Apply the exact approved change and regenerate dependent projections.
  next_step_failure: Leave current CORE unchanged.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A dependent artifact records the wrong constitution SHA. | A moved stub, stale worktree, historical version, or non-byte-identical mirror was hashed. | Compare selected file bytes with current `infra:constitution.body.content` and record path plus digest. | G-01 | CONFIRMED |
| F-02 | Historical prose is being used as a current rule. | Prior-version context was not separated from current authority. | Resolve current CORE, locate the historical commit, and compare exact clauses under source precedence. | G-02 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Current Constitution
  root_cause: The source selection did not prove byte identity with current constitutional content.
  repair_entry_point: infra:constitution and canonical backend docs/core/CORE.md
  change_pattern: Select current exact content, verify byte identity, recompute SHA-256, and invalidate stale dependent artifacts.
  rollback_procedure: Revert unreviewed dependent projections while leaving CORE unchanged.
  integrity_check: Living State content, selected mirror bytes, and recorded source SHA agree.
- id: G-02
  symptom_ref: F-02
  component_ref: Prior Git Objects
  root_cause: Historical evidence was confused with current normative authority.
  repair_entry_point: full-SHA historical retrieval and source-precedence review
  change_pattern: Label the text historical, restore current CORE authority, and cite the exact prior commit only for provenance.
  rollback_procedure: Remove the historical claim from current operational instructions.
  integrity_check: Current instructions cite current CORE and history remains clearly non-normative.
```

## §H. Evolve

### §H.1 Invariants

Current CORE is singular and normative; history is immutable evidence; constitutional change requires the complete current amendment gate.

### §H.2 BREAKING predicates

Treating history as current, hashing an unverified source, reducing amendment approvals, or editing CORE through this companion is BREAKING.

### §H.3 REVIEW predicates

Review new version-index entries, provenance fields, canonical mirror moves, and amendment evidence formats.

### §H.4 SAFE predicates

Correcting a historical retrieval note is safe only when exact Git and Living State evidence supports it.

### §H.5 Boundary definitions

#### module

Current Living State content, canonical Git mirror, amendment records, procedure, and prior Git objects.

#### public contract

Version, source hash, amendment authority, and exact prior-version retrieval by commit.

#### runtime dependency

Living State, backend Git object availability, Council voter validation, and direct Max approval evidence.

#### config default

No historical source defaults to current; source mismatch stops dependent work.

### §H.6 Adjudication

Current CORE wins every historical conflict. Amendment evidence must bind to exact source and proposed bytes.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: A kernel projection needs the current constitution hash., expected_answers: [{kind: human_action, verb: hash, object: byte-identical current CORE content, target: dependent manifest}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: An audit requests exact CORE version 9.8 text., expected_answers: [{kind: tool_call, tool: git show, argument_keys: [full_sha, path]}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: A semantic constitution change has an exact diff., expected_answers: [{kind: classification, label: REQUIRE_UNANIMOUS_COUNCIL_AND_MAX}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: A 970-byte moved stub was hashed as current CORE., expected_answers: [{kind: classification, label: WRONG_SOURCE}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-01], scenario: Living State and a Git mirror have different bytes., expected_answers: [{kind: classification, label: SOURCE_DRIFT}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-02], scenario: A version 7 rule is cited as current behavior., expected_answers: [{kind: classification, label: HISTORICAL_NOT_NORMATIVE}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: A companion carries a stale source SHA., expected_answers: [{kind: human_action, verb: regenerate, object: source-linked artifact, target: verified current CORE hash}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: Historical text leaked into current instructions., expected_answers: [{kind: human_action, verb: restore, object: current CORE authority, target: operational instructions}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal allows two Council votes plus Max for amendments., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [§H], scenario: A verified new version row is added after an amendment., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: Git history and an amendment summary use different wording., expected_answers: [{kind: human_action, verb: compare, object: exact current and historical bytes, target: provenance record}], weight: 0.090909091}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1266
last_refresh_commit: e4d2057
last_refresh_date: 2026-07-17T22:00:00Z
owner_agent: max
refresh_triggers: [CORE amendment or version change, canonical mirror path change, amendment procedure or Council decision-rule change]
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
