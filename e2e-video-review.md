---
runbook_id: e2e-video-review
domain: e2e-testing
status: ACTIVE
authoritative_for:
  - topic: e2e-video-review
    section: §C. Architecture & Interactions
aliases: []
error_signatures: []
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-23
system_name: e2e-video-review
purpose_sentence: Hold the design reasoning for the video-and-Gemini review of test runs - what we chose, what we rejected and why, and what is still open - so that a future instance improving this process starts from the argument rather than repeating it.
owner_agent: mars
escalation_contact: Max (any change to the four questions, to what a finding must prove before it is accepted, or to what is recorded and where); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The DESIGN LOGIC and decision record for reviewing e2e browser-run recordings with a video model - the four owner questions, the evidence a finding must carry, the three-path acceptance gate, deduplication, severity assignment, pass structure, and the rejected alternatives with their reasons. NOT authoritative for the browser_journey runner (e2e-browser-runner.md), the status publisher and coverage manifest (e2e-test-status-publisher.md), charter authoring honesty and the integrity audit (e2e-programme-integrity.md), the ops.ai.market render surface (ops-ai-market.md), or Council dispatch mechanics (agent-dispatch.md).
linter_version: 1.0.0
---

# E2E Video Review

> Max, S1315: "I feel like this is a mine field that can only be crossed in the moment."
>
> The browser agent runs headless and leaves only text behind. Video is being added so a human, and a video model, can see what the run actually looked like. This runbook is NOT an operating manual for a shipped system - very little of it is built. It is the DESIGN RECORD, kept in the runbooks on Max's instruction so that whoever improves this process next can see the reasoning and the rejected alternatives instead of rediscovering them.
>
> Read the §H.6 decision log first. It is the decision log, and it is the reason this file exists. Owner BQ `BQ-E2E-RUN-VIDEO-AND-GEMINI-REVIEW-S1315`.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| Run recordings | The video of each browser journey, the primary evidence this whole mechanism reads | `/Users/max/Downloads/testvideos` on Titan-1, Max-specified. VOLATILE by design - Max deletes old ones and macOS may clear Downloads | e2e-harness |
| Step transcript | The agent's own declared intent and actions per step. Without it the acceptance gate cannot tell a tester fault from a product fault | e2e-harness run artifacts | e2e-browser-runner.md |
| Playwright trace | DOM snapshots and network activity. NOT fed raw - see §H.6 decision log entry 3 | e2e-harness run artifacts | e2e-browser-runner.md |
| Coverage catalog | The 30 journeys. Answers the owner's flow question, which a video model cannot | `docs/coverage.json` in e2e-harness | e2e-programme-integrity.md |
| Gemini via Vertex | The video model. Samples video at roughly one frame per second and can cite MM:SS timestamps | Google Cloud project already used by Council | Council / agent-dispatch.md |
| ops.ai.market Test page | Where Max picks a recording and submits it. Currently read-only; a submit action is a command surface | `aidotmarket/ops-ai-market` | ops-ai-market.md |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Design reasoning and rejected alternatives recorded and findable | SHIPPED | `runbooks/e2e-video-review.md` | n/a | 2026-07-23 |
| Recording directory exists or is created at write time, every run | PLANNED | — | n/a | — |
| Video capture of each browser journey to the Max-specified folder | PLANNED | — | n/a | — |
| Ops Test page lists recordings and submits one for review | PLANNED | — | n/a | — |
| Three-path acceptance gate on findings | PLANNED | — | n/a | — |
| Deterministic severity from category rather than model self-rating | PLANNED | — | n/a | — |
| Stable deduplication across nights and across passes | PLANNED | — | n/a | — |
| Evidence-object schema defined | BROKEN | `runbooks/e2e-video-review.md` | n/a | 2026-07-23 |
| Definition of a violated contract | BROKEN | `runbooks/e2e-video-review.md` | n/a | 2026-07-23 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Recorder | e2e-harness browser journey runner | video files on Titan-1 | run report, tickets | Must fail soft. A recording problem must never change a run's outcome. Must create its directory at write time, every run. |
| Evidence assembler | not yet built | — | transcript, trace, catalog | Builds the single object both the model and the gate read. Load-bearing and currently UNDEFINED - see §F-02. |
| Video model | Gemini via the existing Vertex connection | — | evidence assembler | Sees roughly one frame per second. Cannot read a binary archive. Cannot see the agent's intent unless the assembler gives it. |
| Acceptance gate | not yet built | — | findings, tickets | Decides accepted, accepted-with-review, or demoted. Never discards. |
| Ticket path | support ticket API | support tickets | gate, dedup signature | Only fully accepted findings auto-file. Everything else waits for a human. |

Prose: a run produces a video, a step transcript and a trace. An assembler turns those into one evidence object. The model reads the video plus that object and returns structured findings. A gate decides what each finding has earned. Severity is applied by us from the category, not by the model. A stable signature decides whether a finding is new or the same one recurring. The point of the whole chain is that a finding arrives with its evidence attached, because the failure mode of this programme has always been output that looks like insight.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Read the decision log before changing anything here | this runbook §H.7 | none | COMPLETE |
| Vulcan/Mars | Settle the open pass-structure question by measurement | `shell_request` on a real recording | Titan-1 | PARTIAL — cannot be settled until a real recording exists |
| Vulcan/Mars | Put a proposed change to Council before building | `council_request mode=open_response` | Council dispatch | COMPLETE — three rounds already run, see the §H.6 decision log |
| GLM / DeepSeek | Attack a proposed question set or gate | `council_request mode=open_response` | Council dispatch | COMPLETE — each caught what the other missed |
| CC | Review built code | `council_request mode=review` | Council dispatch | COMPLETE — note CC supports review mode only, not open_response |
| Gemini | Analyse a recording and return findings | Vertex, existing Council connection | Google Cloud project | PLANNED |

## §E. Operate

```yaml operate
- id: E-01
  trigger: You are about to change how test-run video is reviewed, or how findings from it are accepted
  pre_conditions:
    - none
  tool_or_endpoint: "read §H.6 decision log in this runbook BEFORE proposing anything"
  argument_sourcing:
    decisions: §H.6 decision log of this runbook
    owner_questions: §H.1 invariants
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'you can state which decision you are reopening, what its original reasoning was, and what new information justifies changing it'
    verification: 'name the decision number in the §H.6 decision log and quote the reason it was decided that way'
  expected_failures:
    - signature: you cannot find the reasoning for an existing choice
      cause: the decision log is incomplete - add it rather than working around it (§F-01)
  next_step_success: propose the change, then put it to Council per E-02
  next_step_failure: repair the log per §G-01
- id: E-02
  trigger: A change to the questions, the gate, or the finding schema is proposed
  pre_conditions:
    - the change names the §H.6 decision it revises
  tool_or_endpoint: "council_request mode=open_response to at least TWO reviewers, separately, each instructed to attack rather than agree"
  argument_sourcing:
    reviewers: current roster in infra:council-comms - do not trust memory
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'two independent critiques, at least one of which disagrees with the other, and an explicit adjudication recorded with reasons'
    verification: 'the second reviewer was given the FIRST reviewer conclusions and asked to attack them by name'
  expected_failures:
    - signature: both reviewers agree with everything
      cause: they were asked to review rather than to attack, or the second was not shown the first's conclusions (§F-03)
  next_step_success: record the adjudication, then freeze
  next_step_failure: re-dispatch with an adversarial framing per §G-03
- id: E-03
  trigger: Settle the open question of one analysis pass versus two
  pre_conditions:
    - at least one real recording exists with its assembled evidence object
  tool_or_endpoint: "measure the assembled evidence object plus the video against the model context window"
  argument_sourcing:
    recording: newest file in the Max-specified video folder
    evidence: the assembled evidence object for that run
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'a measured size, and a decision that follows from it - one pass if it fits with room for careful reasoning, split only if forced'
    verification: 'the number is measured on a real recording, not estimated'
  expected_failures:
    - signature: the question is settled by argument instead of measurement
      cause: exactly the error this runbook exists to prevent (§F-04)
  next_step_success: record the decision in the §H.6 decision log with the measurement
  next_step_failure: do not proceed - an unmeasured split is a guess
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Someone proposes a change that was already considered and rejected | The decision log is incomplete, or the proposer did not read it. This runbook exists because a BQ body is not read and goes stale | search the §H.6 decision log for the topic; if the reasoning is absent, that is the defect | §G-01 | CONFIRMED |
| F-02 | The acceptance gate cannot tell a tester fault from a product fault | The evidence object omits the agent's declared per-step intent. The gate depends entirely on it and the schema is not yet defined | inspect what the assembler actually passes; if intent is missing, the gate is decorative | §G-02 | CONFIRMED |
| F-03 | Council rounds all agree and nothing is caught | Reviewers were asked to review rather than to attack, or the later reviewer was never shown the earlier conclusions by name | check the dispatch text - it must name the prior conclusions and ask for them to be attacked | §G-03 | CONFIRMED |
| F-04 | A structural choice is defended by argument when it is really an empirical question | Reviewers cannot measure. Pass structure and context fit are measurements | ask what number would settle it, then go and measure that number | §G-04 | CONFIRMED |
| F-05 | Recordings stop appearing with no error anywhere | The target directory was cleared, by Max or by macOS, and the writer assumed it persisted | check the directory exists; if the code did not recreate it, that is the defect | §G-05 | CONFIRMED |
| F-06 | Findings are confident, plausible, and wrong | The model attributed a harness fault to the product. On video an agent clicking the wrong element is indistinguishable from a broken control, and a prompt instruction not to conflate them does not prevent it | check whether the finding cites the agent's declared intent and hard evidence of misbehaviour, or only a screenshot impression | §G-06 | CONFIRMED |
| F-07 | The same defect files a fresh ticket every night | Deduplication keyed on values that change per run, such as timings, or on free text the model rephrases | compare two nights of the same defect; if the signature differs, the dedup is fiction | §G-07 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Evidence assembler
  root_cause: the decision log does not record why a choice was made
  repair_entry_point: §H.6 decision log of this runbook
  change_pattern: 'add the missing decision with its date, what was proposed, what was rejected, and the REASON. A decision without its reason is worthless, because the next instance cannot tell whether new information justifies changing it. Max asked for this file precisely so improvement starts from the argument rather than repeating it'
  rollback_procedure: none wanted
  integrity_check: a reader can state why the current choice beats the rejected one
- id: G-02
  symptom_ref: F-02
  component_ref: Evidence assembler
  root_cause: the evidence object omits the agent's declared intent, so the gate cannot function
  repair_entry_point: the evidence-object schema
  change_pattern: 'define the schema explicitly BEFORE building anything that depends on it. It must carry, at minimum, the agent per-step declared intent, the action actually taken, failed network requests with status codes, console errors, failed assertions, and the state of the elements involved. Extract these as text - do NOT pass the raw trace archive, see §H.6 decision log entry 3'
  rollback_procedure: none wanted
  integrity_check: pick a real run and confirm the gate can classify each finding using only the object
- id: G-03
  symptom_ref: F-03
  component_ref: Acceptance gate
  root_cause: reviewers were asked to agree rather than to attack
  repair_entry_point: the council dispatch text
  change_pattern: 'name the prior reviewer conclusions explicitly and instruct the next reviewer to defend or concede each one and to attack the adjudication. Every genuine correction in this design came from a reviewer contradicting another reviewer, never from consensus'
  rollback_procedure: none wanted
  integrity_check: the round produces at least one explicit disagreement or an explicit concession
- id: G-04
  symptom_ref: F-04
  component_ref: Video model
  root_cause: an empirical question is being settled by argument
  repair_entry_point: the measurement itself
  change_pattern: 'identify the number that would settle it and measure it on real data. Pass structure depends on whether the evidence object plus the video fits in one context with room to reason - that is a measurement, and two capable reviewers argued opposite conclusions from the same facts because neither could measure'
  rollback_procedure: none wanted
  integrity_check: the decision cites a measured number taken from a real recording
- id: G-05
  symptom_ref: F-05
  component_ref: Recorder
  root_cause: the writer assumed a volatile directory persists
  repair_entry_point: the recording write path
  change_pattern: 'verify or create the directory at WRITE time, on every run, never once at install. Max: the Downloads folder is for throwaway data. If creation genuinely fails, fail soft and log loudly - a recording problem must never change a test run outcome. Test it by deleting the directory between runs, which is the real condition'
  rollback_procedure: none wanted
  integrity_check: delete the directory, run, and confirm a recording still lands
- id: G-06
  symptom_ref: F-06
  component_ref: Acceptance gate
  root_cause: a harness fault was accepted as a product defect
  repair_entry_point: the three-path gate
  change_pattern: 'apply the gate honestly. Path 1 - agent declared intent plus hard evidence the product misbehaved - is ACCEPTED. Path 2 - a specific timestamp plus concrete visual evidence, not the phrase looks broken, plus a stated user impact - is ACCEPTED WITH REVIEW and must never auto-file a ticket. Everything else is DEMOTED to a tester-issue candidate. Never DISCARD - on a marketplace a missed fault costs more than a false alarm'
  rollback_procedure: none wanted
  integrity_check: take a known harness fault and confirm it cannot reach path 1
- id: G-07
  symptom_ref: F-07
  component_ref: Ticket path
  root_cause: deduplication keyed on values that vary per run
  repair_entry_point: the finding signature
  change_pattern: 'derive the signature from the underlying defect identity - the element, the violated expectation, or the checklist step that failed - and never from timings or from free text the model rephrases. Free text stays as human-readable context and never enters the signature. The signature must dedup BOTH night-over-night recurrence and overlap between analysis passes'
  rollback_procedure: none wanted
  integrity_check: run the same defect twice and confirm one signature and a recurrence count, not two tickets
```

## §H. Evolve

### §H.1 Invariants

- **Max's four questions are the spine and are not removable.** What a user hits, what the tester gets wrong, how to improve the flow, and how to improve the experience.
- **A finding arrives with its evidence or it does not arrive as a finding.** Point findings cite a timestamp, what was on screen, and what was expected. Diffuse findings cite a time range, the pattern, and the expected baseline.
- **Nothing is discarded.** Findings that fail the gate are demoted to a reviewable queue. A missed fault costs more than a false alarm.
- **The model does not set severity.** It states the category; severity follows deterministically from our rubric.
- **A harness fault is never reported as a product defect on visual impression alone.** Path 1 needs declared intent plus hard evidence.
- **Deduplication never keys on values that vary per run.** No timings, no model-rephrased prose.
- **The recording directory is verified or created at write time, every run.** It is volatile by design.
- **Recording and analysis never change a test run's outcome.** Fail soft, log loudly.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Removing or reinterpreting one of Max's four questions without his decision.
- Auto-filing a ticket from a finding that only reached path 2 or was demoted.
- Discarding a finding instead of demoting it.
- Letting the model assign severity, or acting on a model-assigned severity.
- Deduplicating on run-varying values, which silently converts recurrence into a flood of duplicates.
- Assuming the recording directory persists.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Changing the evidence-object schema, since the gate depends on it entirely.
- Changing the definition of a violated contract.
- Changing pass structure, which must be settled by measurement per §E-03.
- Sending recordings anywhere other than the existing Google Cloud project.

### §H.4 SAFE predicates

SAFE otherwise:
- Wording of this runbook and of the decision log entries.
- Adding a new evaluation category that only widens what is looked for.
- Read-only tooling that lists or plays recordings.

### §H.5 Boundary definitions

#### module

The review chain: recorder, evidence assembler, video-model prompt, acceptance gate, signature and ticket path.

#### public contract

What an accepted finding MEANS: a real problem, evidenced, correctly attributed to the product rather than the tester, and severity-rated by our rubric rather than the model's judgement.

#### runtime dependency

The Titan-1 recording folder, the existing Google Cloud connection, and the support ticket API.

#### config default

The recording location, the retention and size limits, and the category-to-severity rubric.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Anything touching Max's four questions, what a finding must prove, or where recordings go escalates to Max.

#### Decision log

Every entry records what was proposed, what was rejected, and WHY. A decision without its reason cannot be safely revisited. All entries are S1315 (2026-07-23) unless stated.

1. **Evidence rule for findings.** Proposed: every finding must cite a timestamp, what was on screen, and what was expected. REJECTED as sole rule — it suppresses diffuse problems, a journey confusing overall or a site slow throughout, which have no single timestamp. ADOPTED: two finding shapes, point and diffuse, the latter carrying a time range plus a pattern plus an expected baseline. Lesson worth keeping: a rule written against fabrication can quietly buy blindness.
2. **Deduplication.** Proposed: hash the question, timestamps, screen description and expectation. REJECTED — timings vary every run and the description is prose the model rewrites, so the same defect looks new every night and the recurrence count is fiction. ADOPTED: a signature derived from the defect's own identity, reusing the harness signature concept, covering both nightly recurrence and cross-pass overlap.
3. **Corroborating evidence.** Proposed: hand the Playwright trace to the video model alongside the video. REJECTED — a trace is a compressed archive the model cannot read; it would ignore it and still produce findings that look corroborated and are not. ADOPTED: extract failed requests with status codes, console errors, failed assertions and relevant element state as text.
4. **Severity.** Proposed: the model rates severity. REJECTED — models over-rate cosmetics and under-rate money and trust problems. ADOPTED: the model states a category; we map category to severity deterministically.
5. **Acceptance gate.** Proposed: accept a product-defect finding only with declared intent plus a contract violation. REJECTED as written — it assumes every real defect trips a technical check, and a broken layout, a price rendering as zero, a missing trust badge and a contrast failure trip none, so the gate would only catch what our existing checks already catch. ADOPTED: three paths, accepted, accepted-with-review, demoted.
6. **Failure handling.** Proposed: discard findings that fail the gate. REJECTED — a missed fault on a marketplace costs more than a false alarm. ADOPTED: demote, never discard.
7. **Pass structure.** Proposed: three passes, the third reasoning over the first two. REJECTED — a pass citing earlier prose legitimises earlier hallucinations. A two-pass compromise was then also challenged as keeping the overhead while losing cross-pollination. OPEN: one pass versus two, to be settled by MEASURING the evidence object plus video against the context window on a real recording. Do not settle it by argument.
8. **Max's flow question.** Proposed: ask the video model how to improve the testing flow. REJECTED — it sees one journey and knows nothing of the other twenty-nine, so it will emit generic advice. ADOPTED: keep the question, answer it from our own coverage catalog by comparing what the journey exercised against what exists.
9. **Recording location.** Max-specified as the Downloads folder, explicitly throwaway. ADOPTED: verify or create at write time on every run, with a test that deletes the directory between runs.
10. **Method.** Every correction above came from one reviewer contradicting another, never from consensus. ADOPTED as procedure: at least two reviewers, the later ones shown the earlier conclusions by name and told to attack them.

#### Open questions

- The evidence-object schema is undefined and the gate depends on it. BUILD BLOCKER.
- "Violated contract" is undefined while doing decisive work in the gate. BUILD BLOCKER.
- One pass versus two, pending measurement (§E-03).
- Whether authenticated-session recordings may be kept at all, given video cannot be redacted the way text can. Max decision.
- Retention and size limits on the recording folder. Max decision.
- Whether analysis runs automatically each night or only when Max asks. Max decision.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: You want to change how findings are accepted. What do you do first?
    expected_answers:
      - kind: human_action
        action: read the decision log, name the decision you are reopening, state its original reason, and say what new information justifies changing it
    weight: 0.090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: You have a proposed change to the question set. One reviewer approves it. Ship it?
    expected_answers:
      - kind: human_action
        action: no - dispatch a second reviewer, show them the first reviewer's conclusions by name, and instruct them to attack; every real correction here came from disagreement, not consensus
    weight: 0.090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Two reviewers argue opposite conclusions about one analysis pass versus two. How do you decide?
    expected_answers:
      - kind: human_action
        action: measure the assembled evidence object plus the video against the context window on a real recording; it is an empirical question and neither reviewer can measure
    weight: 0.090909091
  - id: I-04
    type: isolate
    refs: [F-06]
    scenario: A finding says a button was broken. The video shows the agent clicking and nothing happening. Accept it as a product defect?
    expected_answers:
      - kind: human_action
        action: not on that alone - on video a wrong click is indistinguishable from a broken control; require the agent's declared intent plus hard evidence the product misbehaved, otherwise accept-with-review or demote
    weight: 0.090909091
  - id: I-05
    type: isolate
    refs: [F-07]
    scenario: The same defect has filed a new ticket every morning for a week. Cause?
    expected_answers:
      - kind: human_action
        action: the signature is keyed on something that varies per run, such as timings or model-rephrased prose; rekey it on the defect's own identity
    weight: 0.090909091
  - id: I-06
    type: isolate
    refs: [F-05]
    scenario: Recordings stopped appearing and nothing errored. First check?
    expected_answers:
      - kind: human_action
        action: whether the target directory still exists - it is throwaway by design, and the writer must create it at write time rather than assume it persists
    weight: 0.090909091
  - id: I-07
    type: repair
    refs: [G-06]
    scenario: A finding cites only a timestamp and says the checkout page looks broken. What happens to it?
    expected_answers:
      - kind: human_action
        action: it fails path 1 and does not meet path 2 either, because 'looks broken' is not concrete visual evidence with a stated user impact; demote it to the reviewable queue rather than discarding it
    weight: 0.090909091
  - id: I-08
    type: repair
    refs: [G-02]
    scenario: Someone proposes building the acceptance gate this week. The evidence-object schema is not written. Proceed?
    expected_answers:
      - kind: human_action
        action: no - the gate depends entirely on that object, and if it omits the agent's declared intent the gate is decorative; define the schema first
    weight: 0.090909091
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A change auto-files tickets from accept-with-review findings to save human time. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.090909091
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: A change adds a new evaluation category for subscription upsell clarity, widening what is looked for. Classify.
    expected_answers:
      - kind: classification
        verdict: SAFE
    weight: 0.090909091
  - id: I-11
    type: ambiguous
    refs: [§H.6, F-06]
    scenario: A finding shows a price displayed as zero. No technical check failed, and the agent's intent is irrelevant because it merely looked at the page. Product defect, or unprovable?
    expected_answers:
      - kind: classification
        label: ACCEPT_WITH_REVIEW
      - kind: human_action
        action: this is exactly the class the three-path gate exists for - it trips no contract, so path 1 cannot accept it, but concrete visual evidence at a timestamp with a clear user impact earns path 2 and a human look; forcing it through path 1 is how the gate goes blind
    weight: 0.090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1315
last_refresh_commit: fcca188
last_refresh_date: 2026-07-23T13:20:00Z
owner_agent: mars
refresh_triggers:
  - any decision in the §H.6 decision log being revisited or reversed
  - the evidence-object schema or the contract definition being defined, which clears the two build blockers
  - the pass-structure measurement being taken
  - Max ruling on authenticated-session recordings, retention, or automatic nightly analysis
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-23T13:20:00Z
first_staleness_detected_at: "2026-07-23T13:24:00.585073+00:00"
```

Refresh log:
- S1315 (2026-07-23): first authoring, on Max's instruction that the logic of how this is being set up must live in the runbooks and be easily available when the process is improved. Captures three rounds of Council critique in which each reviewer corrected the other, and records two build blockers rather than papering over them.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1315 / 2026-07-23T13:20:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
