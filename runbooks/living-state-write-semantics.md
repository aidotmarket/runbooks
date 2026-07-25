---
runbook_id: living-state-write-semantics
domain: build-queue
status: ACTIVE
authoritative_for:
  - topic: living-state-write-semantics
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: patch_replaced_list_wholesale
    section: §F. Isolate
  - signature: write_reported_success_but_lost_data
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-25
system_name: living-state-write-semantics
purpose_sentence: How state_request writes actually merge, so an operator stops silently destroying list data with a partial patch.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Merge semantics of state_request put and patch, the read-back obligation, and the optimistic-lock contract. Entity schemas and gate mechanics are out of scope and live in council-gate-process and build-queue-reconciliation.
linter_version: 1.0.0
---

# Living State Write Semantics

## §A. Header

The frontmatter above is the §A header. This runbook covers one narrow, load-bearing fact that is not written down anywhere else and that has already caused silent data loss: **`state_request(action=patch)` deep-merges objects but replaces lists wholesale.**

**Authority: delivery companion.** Full CORE and the Boot Kernel prevail in any conflict.

**Fetch trigger:** before any write to a Living State entity that contains a list.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| `patch` object deep-merge | SHIPPED | `state_service` patch path | Probed live on `config:scratch-merge-probe-s1332` | 2026-07-25 |
| `patch` list wholesale replacement | SHIPPED, HAZARDOUS | same | Same probe; behaviour confirmed, not desired | 2026-07-25 |
| Optimistic locking via `expected_version` | SHIPPED | version column | Exercised S1334 on `build:bq-listing-enrichment-seller-tools-s1294` v182 to v183 to v184 | 2026-07-25 |
| Required-argument contract on `patch` | SHIPPED | tool handler | Observed S1334: omitting `expected_version` is rejected | 2026-07-25 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Patch writer | `state_request(action=patch)` | entity `body`, `version` | every BQ and infra entity | Deep-merges nested objects. **Replaces any list it is given, in full.** |
| Put writer | `state_request(action=put)` | entity `body`, `version` | same | Whole-body replace. Honest about what it does; `patch` is the one that surprises people. |
| Optimistic lock | `expected_version` | `version` column | reconciliation job | Required on `patch` alongside `key`, `body`, `updated_by`, `source_ref`. A stale value fails the write rather than clobbering. |
| Reconciliation job | background | `git_state`, `lifecycle` | all `build:bq-*` | Writes to the same entities and bumps `version` without warning, so a read-then-write gap is real. |

**Strategic why.** The Build Queue is the canonical record of what has been decided and reviewed. A write that reports success while dropping list elements produces a record that is confidently wrong, which is worse than an obvious failure: nobody re-checks a green result. This is the same class as the report-does-not-match-reality failures tracked at `BQ-MP-WRAPPER-DISCARDS-CORRECT-WORK-S1315`, but it fires inside our own state layer rather than a builder wrapper.

**The rule, stated once.** Send the complete list, every time. Never send a partial list expecting the elements you omitted to survive. Re-read the entity after every write.

Filed as **T-2026-000388**. Mars confirmed at S1332 that this is a distinct root cause from T-2026-000384, which normalised the write body.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Read, patch, put, verify | `state_request` | full Living State write | COMPLETE |
| MP | Never writes Living State directly | n/a | none | COMPLETE |
| Reconciliation job | Writes `git_state` and `lifecycle` | background handler | scoped write | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An operator is about to patch an entity whose body contains a list.
  pre_conditions: [entity_read_immediately_before, complete_list_assembled, current_version_known]
  tool_or_endpoint: state_request(action=patch, key, body, updated_by, source_ref, expected_version)
  argument_sourcing:
    body: send the COMPLETE list, including every element already present that is being kept
    expected_version: use the version from the read taken immediately before this write
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(key + expected_version + body_digest)
  expected_success: {shape: entity returned at version plus one, verification: read the returned body and count the list elements}
  expected_failures:
    - {signature: patch_replaced_list_wholesale, cause: a partial list was sent and the omitted elements were destroyed}
    - {signature: write_reported_success_but_lost_data, cause: success was taken from the return code rather than from a read-back}
  next_step_success: Confirm the element count and continue.
  next_step_failure: Use F-01 immediately, before any further write.
- id: E-02
  trigger: A write must not race the reconciliation job or the peer instance.
  pre_conditions: [entity_read, version_captured]
  tool_or_endpoint: state_request(action=patch) with expected_version
  argument_sourcing: {expected_version: from the read, never from memory or from an earlier turn}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(key + expected_version)
  expected_success: {shape: accepted write, verification: returned version is exactly the expected version plus one}
  expected_failures: [{signature: version_conflict, cause: reconciliation or the peer wrote between the read and the write}]
  next_step_success: Continue.
  next_step_failure: Re-read, rebuild the body against the new state, and retry once. Do not force.
- id: E-03
  trigger: The write is large or structural and a partial merge would be ambiguous.
  pre_conditions: [whole_body_assembled]
  tool_or_endpoint: state_request(action=put)
  argument_sourcing: {body: the complete body, since put replaces wholesale by design}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(key + body_digest)
  expected_success: {shape: entity replaced, verification: read back and diff against intent}
  expected_failures: [{signature: unintended_field_loss, cause: put omitted fields that patch would have preserved}]
  next_step_success: Continue.
  next_step_failure: Restore from the pre-write read, which is why the pre-write read is mandatory.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A list on an entity is shorter than it was, and no error was raised. | A partial list was sent to `patch`, which replaced rather than merged it. | Compare the current list against the pre-write read or the prior version; the write will have succeeded and bumped `version`. | G-01 | CONFIRMED |
| F-02 | State disagrees with git, a branch, or a review record. | The write succeeded but was never read back, so a silent loss went unnoticed. | Read the entity and compare against ground truth in git and the dispatch record. | G-02 | CONFIRMED |
| F-03 | A patch is rejected for missing arguments. | `patch` requires `key`, `body`, `updated_by`, `source_ref` and `expected_version` together. | Read the error text; it names the full required set. | G-03 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Patch writer
  root_cause: A partial list was supplied to a writer that replaces lists wholesale.
  repair_entry_point: state_request(action=patch)
  change_pattern: Reconstruct the complete list from the prior version or from ground truth, then write it in full with a current expected_version.
  rollback_procedure: There is no automatic rollback. Restore from the pre-write read, the prior entity version, or ground truth in git.
  integrity_check: Read back and count the elements; the count must match the reconstruction.
- id: G-02
  symptom_ref: F-02
  component_ref: Patch writer
  root_cause: Success was inferred from the return rather than confirmed by a read.
  repair_entry_point: state_request(action=get)
  change_pattern: Adopt the read-back habit unconditionally, then repair whatever the read reveals.
  rollback_procedure: None needed for the read itself.
  integrity_check: The read-back body matches the intended body field by field.
- id: G-03
  symptom_ref: F-03
  component_ref: Patch writer
  root_cause: The required-argument set was incomplete.
  repair_entry_point: state_request(action=get) then patch
  change_pattern: Read the entity to obtain the current version, then resend with the full argument set.
  rollback_procedure: None; the rejected write did not land.
  integrity_check: The returned version is the read version plus one.
```

## §H. Evolve

### §H.1 Invariants

- A patch that contains a list must contain that list in full.
- Every write is followed by a read.
- `expected_version` comes from a read taken immediately before the write, never from memory.

### §H.2 BREAKING predicates

Changing list-merge semantics in either direction is BREAKING, because every existing caller was written against the current behaviour. Removing the `expected_version` requirement is BREAKING.

### §H.3 REVIEW predicates

Adding a merge strategy selector, changing the required-argument set, or changing conflict behaviour is REVIEW.

### §H.4 SAFE predicates

Clarifying prose and adding examples are SAFE.

### §H.5 Boundary definitions

#### module

The `state_request` write path: `put`, `patch`, and their version handling.

#### public contract

Merge semantics, the required-argument set, and the optimistic-lock behaviour.

#### runtime dependency

The Living State backend and the reconciliation job that writes concurrently.

#### config default

None. There is no merge-strategy setting; the behaviour described here is the only behaviour.

### §H.6 Adjudication

If this runbook and observed behaviour disagree, observed behaviour wins and this runbook is stale. Re-probe on a scratch entity, never on a live BQ.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: An operator must add one element to an existing list on a BQ entity., expected_answers: [{kind: human_action, verb: send, object: the complete list including existing elements, target: state_request patch}], weight: 0.125}
  - {id: I-02, type: operate, refs: [E-02], scenario: A write must not race the reconciliation job., expected_answers: [{kind: tool_call, tool: state_request, argument_keys: [action, key, body, updated_by, source_ref, expected_version], argument_values: {action: patch}}], weight: 0.125}
  - {id: I-03, type: operate, refs: [E-03], scenario: A structural rewrite would be ambiguous under a partial merge., expected_answers: [{kind: classification, label: USE_PUT_WITH_COMPLETE_BODY}], weight: 0.125}
  - {id: I-04, type: isolate, refs: [F-01], scenario: A list is shorter than before and the write returned success., expected_answers: [{kind: classification, label: PATCH_REPLACED_LIST_WHOLESALE}], weight: 0.125}
  - {id: I-05, type: isolate, refs: [F-02], scenario: Living State disagrees with the branch and commit evidence., expected_answers: [{kind: human_action, verb: read, object: the entity, target: comparison against ground truth}], weight: 0.125}
  - {id: I-06, type: repair, refs: [G-01], scenario: Elements were destroyed by a partial list patch., expected_answers: [{kind: human_action, verb: reconstruct, object: the complete list, target: a full-list write at a current expected_version}], weight: 0.125}
  - {id: I-07, type: evolve, refs: ["§H"], scenario: A proposal makes patch merge lists element by element., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.125}
  - {id: I-08, type: ambiguous, refs: ["§H.6"], scenario: This runbook says lists are replaced but a probe shows a merge., expected_answers: [{kind: human_action, verb: re-probe, object: the behaviour on a scratch entity, target: correction of this runbook}], weight: 0.125}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1334
last_refresh_commit: null
last_refresh_date: 2026-07-25T15:20:00Z
owner_agent: vulcan
refresh_triggers:
  - state_request merge semantics change
  - required-argument set on patch changes
  - T-2026-000388 is resolved
scheduled_cadence: 90d
last_harness_pass_rate: null
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: null
last_lint_result: null
retrofit: false
trace_matrix_path: null
word_count_delta: null
```

Authored at S1334 to discharge part of the S1332 close waiver. Not yet catalogued in `CATALOG.json` and not yet lint-run or harness-run; both are owed before this entry can be cited as coverage.
