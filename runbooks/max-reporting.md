---
runbook_id: max-reporting
domain: operator-discipline
status: DRAFT
authoritative_for:
  - topic: max-facing-round-summary
    section: §E. Operate
aliases: []
error_signatures:
  - signature: Max-facing narration appears mid-round
    section: §F. Isolate
  - signature: Summary contains codes or process jargon
    section: §F. Isolate
  - signature: Boot-contract marker assertion fails
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-29
system_name: max-reporting
purpose_sentence: Preserve the source-defined Max-facing discipline of one end-of-round summary, exactly two mid-round carve-outs, plain-language structure, timestamp and marker conventions, and constitutional change control.
owner_agent: mars
escalation_contact: Max
lifecycle_ref: §J
authoritative_scope: The Max-facing per-round output contract, summary structure and voice, hard-stop and blocking-question carve-outs, UTC timestamp header, round-end markers, and boot-contract marker guard; session mechanics, the skill source, business-summary fields, and peer messaging remain out of scope.
linter_version: 1.0.0
---

# Max Reporting — End-of-Round Summary Discipline

> Phase 2 Chunk D DRAFT. The root source remains unchanged. CORE §3 remains the
> canonical rule; this page does not amend the constitution, opening prompt,
> boot-contract test, or waiver store.

## §A. Header

The frontmatter supplies the required fields. The source identifies Mars as
owner, either instance as operator, and Max as the decision authority for rule
changes. CORE §3 is canonical. `infra:opening-prompt` is an elaboration and
must yield on conflict.

Dependencies recorded by the source are CORE §3 in the boot constitution
payload, `infra:opening-prompt` in Living State, the `write-like-max` skill, the
boot-contract marker test, and `date -u` on Titan-1. Exact credentials are
either not applicable or not provided.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| One Max-facing summary per round | SHIPPED | `CORE.md §3` | Boot-contract marker assertion | 2026-07-12 |
| Exactly two mid-round carve-outs | SHIPPED | `CORE.md §3` | Boot-contract marker assertion | 2026-07-12 |
| Opening-prompt elaboration subordinate to CORE | SHIPPED | `infra:opening-prompt` | Manual boot-payload read | 2026-07-12 |
| UTC header and round-end marker convention | SHIPPED | `max-reporting.md` | No automated test recorded | 2026-07-12 |
| Outgoing-summary jargon lint | PLANNED | — | No test recorded | 2026-07-12 |

No newer live verification is asserted by this docs-only rewrite.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Rule Source | `CORE.md` §3 | Constitution store | `kd_session_open` payload | Canonical on conflict. |
| Elaboration | `infra:opening-prompt` | Living State | Boot payload | Longer explanation; subordinate to CORE. |
| Marker Guard | Koskadeux MCP boot-contract test | Git test source | CI | Guards the rule in the delivered payload, not a side copy. |
| Summary Composer | Either instance | No state store | `write-like-max` and `date -u` | Buffers in-round work for one delivery point. |
| Waiver Store | `config:runbook-waivers` | Living State | Runbook-first gate discharge | Source records pre-runbook accumulated waivers on this subject. |

A round is one work cycle ending in one summary. Tool calls, dispatches, and
diagnostics remain out of Max-facing output until that delivery point. The only
mid-round exceptions are a verified hard stop and a genuinely blocking question.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Compose the end-of-round summary | `write-like-max` and `date -u` | Not applicable | COMPLETE |
| Vulcan or Mars | Issue a verified hard stop | Plain Max-facing report, then stop | Not applicable | COMPLETE |
| Vulcan or Mars | Ask one blocking question | One concise Max-facing question | Not applicable | COMPLETE |
| Max | Approve a rule change | CORE amendment with one peer review | Constitutional authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A round is complete and its outcome is ready for Max.
  pre_conditions:
    - work_concluded_or_parked_with_state_recorded
    - fresh_UTC_timestamp_obtained_with_date_u
  tool_or_endpoint: One chat reply structured under CORE §3.
  argument_sourcing:
    structure: State what was done; what is needed from Max only if genuinely needed; why it mattered in plain terms; and anything critical only when present.
    voice: Use write-like-max and outcome-first plain business English.
    exclusions: Keep BQ codes, gate numbers, SHAs, tool names, and session numbers out of the prose.
    framing: Put the UTC timestamp header first and one of CONTINUE, DECISION, or CLOSE SESSION last.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: One short message Max can act on without decoding internal process.
    verification: Re-read before sending; omit empty sections and rewrite jargon.
  expected_failures:
    - signature: Summary contains codes or process jargon
      cause: The draft was composed from working state rather than outcomes.
    - signature: Summary lacks timestamp or round-end marker
      cause: The source convention was skipped.
  next_step_success: Await Max's next instruction.
  next_step_failure: Repair the draft before sending.
- id: E-02
  trigger: Work cannot safely continue because a verified blocker remains after the source-supported cheap retry.
  pre_conditions:
    - blocker_verified_not_assumed
    - safe_state_known
  tool_or_endpoint: One plain hard-stop chat report, followed by no further work.
  argument_sourcing:
    content: State what stopped, what was tried, and what state remains safe without speculation.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Max knows work stopped and why; no later tool action follows the report.
    verification: Confirm the transcript contains no continuation after the stop.
  expected_failures:
    - signature: Continuing after a hard stop
      cause: The carve-out was treated as a progress channel.
  next_step_success: Wait for Max or the verified blocker to clear.
  next_step_failure: Stop means stop.
- id: E-03
  trigger: Max's answer is genuinely required before work can proceed and no safe default or recorded assumption exists.
  pre_conditions:
    - question_is_blocking
    - decision_cannot_wait_for_round_summary
  tool_or_endpoint: One concise chat question with only the context needed to answer.
  argument_sourcing:
    content: State the decision, options, and recommendation when one exists; do not bundle status.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Max can answer in one line.
    verification: Remove any narration that is not necessary to decide.
  expected_failures:
    - signature: Status updates bundled into blocking question
      cause: The carve-out was used to smuggle narration.
  next_step_success: Resume after Max answers.
  next_step_failure: Strip the message to the decision and re-evaluate whether it is truly blocking.
- id: E-04
  trigger: The Max-facing output rule itself needs to change.
  pre_conditions:
    - concrete_failure_or_friction_recorded
    - Max_approval_available
    - one_peer_review_available
  tool_or_endpoint: CORE.md §3 amendment with version bump and changelog line.
  argument_sourcing:
    synchronized_surfaces: Keep CORE §3, infra:opening-prompt, the boot-contract marker test, and this runbook aligned in the same reviewed change.
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: CORE version number
  expected_success:
    shape: The four source-listed surfaces agree after a Max-approved peer review.
    verification: Boot-contract marker test is green against the delivered payload.
  expected_failures:
    - signature: Boot-contract marker assertion fails
      cause: The guarded canonical sentence was weakened, removed, or not updated in the same reviewed change.
  next_step_success: Record peer ratification in the CORE changelog.
  next_step_failure: Restore the canonical marker or complete the authorized same-change update.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Max-facing narration, acknowledgement, or progress appears mid-round | Reply drafted between work steps | Read the transcript; anything outside a hard stop or blocking question is a violation | G-01 | CONFIRMED |
| F-02 | Summary contains codes, gate terms, SHAs, tool names, or session numbers | Draft copied from working state | Scan the exact prose against the §E-01 exclusion list | G-02 | CONFIRMED |
| F-03 | Boot-contract marker assertion fails after a CORE edit | Guarded clause changed or disappeared | Diff CORE §3 against the assertion and run the boot-contract test | G-03 | CONFIRMED |
| F-04 | Plan gate rejects this subject because waivers accumulated | Earlier subject waivers lack a `created` or `commit` discharge | Count subject rows in `config:runbook-waivers` and inspect `discharged_by` | G-04 | CONFIRMED |
| F-05 | Summary omits UTC header or round-end marker | Convention skipped | Inspect the first and last lines before sending | G-02 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Summary Composer
  root_cause: Output was emitted mid-round outside the two carve-outs.
  repair_entry_point: Operator composition discipline
  change_pattern: Buffer work for the summary; before any mid-round message, test whether it is a verified hard stop or an answer-required blocking question.
  rollback_procedure: Not applicable; a sent message cannot be unsent.
  integrity_check: The next complete round contains exactly one ordinary Max-facing message.
- id: G-02
  symptom_ref: F-02
  component_ref: Summary Composer
  root_cause: The draft contains internal process language or omitted framing.
  repair_entry_point: The unsent summary draft
  change_pattern: Rewrite outcome-first in plain English, strip the exclusion list, add the fresh UTC header, and add one round-end marker.
  rollback_procedure: Restore the prior unsent draft if necessary.
  integrity_check: A non-technical reader can act on the summary unaided.
- id: G-03
  symptom_ref: F-03
  component_ref: Marker Guard
  root_cause: A CORE amendment broke the guarded delivered-payload clause.
  repair_entry_point: The CORE change and marker test in one reviewed change
  change_pattern: Restore the canonical marker or, after a legitimate Max-approved peer-reviewed rule change, update the assertion in the same change set.
  rollback_procedure: Revert the CORE edit.
  integrity_check: The boot-contract test passes and the open payload carries the canonical clause.
- id: G-04
  symptom_ref: F-04
  component_ref: Waiver Store
  root_cause: Subject waivers predate the covering runbook.
  repair_entry_point: config:runbook-waivers under the runbook-first discharge procedure
  change_pattern: Patch only the subject rows with discharged_by kind created or commit and the bare covering commit SHA.
  rollback_procedure: Reset only those discharged_by values to null.
  integrity_check: The next session-open tripwire no longer bites this subject.
- id: G-05
  symptom_ref: F-05
  component_ref: Summary Composer
  root_cause: Required source convention was omitted.
  repair_entry_point: The unsent summary framing
  change_pattern: Add a fresh date -u header and exactly one source-listed round-end marker.
  rollback_procedure: Restore the prior unsent framing if necessary.
  integrity_check: First and last lines match the source convention.
```

## §H. Evolve

### §H.1 Invariants

- One short end-of-round summary is the only ordinary Max-facing output.
- The only carve-outs are a verified hard stop and a blocking question.
- CORE §3 is canonical over every elaboration.
- Rule changes require Max approval and one peer review.
- The marker test guards the constitution payload delivered on open.
- The rule governs instance output, not Max's interface choices.

### §H.2 BREAKING predicates

- Removing the single-summary invariant or adding a third carve-out without the
  required CORE amendment.
- Weakening the delivered-payload marker guard.
- Making `infra:opening-prompt` authoritative over CORE §3.
- Changing any §H.1 invariant.

### §H.3 REVIEW predicates

- Changing the four-part summary structure, prose exclusion list, timestamp
  format, or marker vocabulary.
- Adding automated outgoing-summary lint.

### §H.4 SAFE predicates

Documentation examples and refreshed verification metadata that do not alter an
invariant or review predicate.

### §H.5 Boundary definitions

#### module

CORE §3, its boot delivery path, the elaboration, the marker test, and operator
composition discipline.

#### public contract

The canonical CORE clause, two carve-outs, summary structure, UTC header, and
round-end marker vocabulary.

#### runtime dependency

Existing chat delivery, `date -u`, the companion skill, and the boot payload.
No new runtime dependency is asserted.

#### config default

None. The source describes the rule as unconditional.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Unresolved
disputes escalate to Max and the ruling becomes an invariant clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A round ends with no decision needed from Max.
    expected_answers:
      - kind: human_action
        verb: send
        object: one outcome-first summary without an empty request section
        target: Max
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: A verified gateway failure makes continuation unsafe.
    expected_answers:
      - kind: human_action
        verb: stop
        object: plain blocker and safe-state report
        target: Max
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Two irreversible choices require Max and no default is safe.
    expected_answers:
      - kind: human_action
        verb: ask
        object: one decision question with options and recommendation
        target: Max
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: The transcript contains a routine progress acknowledgement mid-round.
    expected_answers:
      - kind: classification
        label: violation outside the two carve-outs
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-02]
    scenario: The summary prose contains a SHA, gate number, and tool name.
    expected_answers:
      - kind: human_action
        verb: scan
        object: prose against the exclusion list
        target: unsent summary
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: CI fails the marker assertion after a CORE edit.
    expected_answers:
      - kind: human_action
        verb: diff
        object: CORE clause and delivered-payload assertion
        target: same reviewed change
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-02]
    scenario: An unsent summary is process-heavy and lacks framing.
    expected_answers:
      - kind: human_action
        verb: rewrite
        object: plain outcome, UTC header, and marker
        target: draft
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-04]
    scenario: Old waiver rows remain after the covering runbook exists.
    expected_answers:
      - kind: human_action
        verb: discharge
        object: subject rows with bare covering commit SHA
        target: waiver store
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A proposal adds routine progress updates as a third carve-out.
    expected_answers:
      - kind: classification
        label: BREAKING without a Max-approved peer-reviewed CORE amendment
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: A proposal renames the three round-end markers.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [E-02, E-03]
    scenario: A destructive decision needs Max while infrastructure is intermittently failing.
    expected_answers:
      - kind: human_action
        verb: choose
        object: hard stop if unsafe, otherwise one blocking question
        target: single mid-round message
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1389
last_refresh_commit: 5f968f167661dcac669dd42910037e05a50221ed
last_refresh_date: 2026-07-29T00:00:00Z
owner_agent: mars
refresh_triggers:
  - CORE §3 changes.
  - The boot-contract marker assertion changes.
  - The communicating-with-Max opening-prompt elaboration changes.
  - A confirmed repeated violation or new waiver bite appears.
scheduled_cadence: 180d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1389 / 2026-07-29T00:00:00Z
last_lint_result: PASS
retrofit: true
trace_matrix_path: specs/ATHENA-PHASE2-CHUNK-D-TRACE-S1389.md
word_count_delta:
  before: 3159
  after: 2314
  pct: -26.75
```
