---
system_name: max-reporting
purpose_sentence: Operate, diagnose, and evolve the Communicating-with-Max discipline that limits Max-facing output to one end-of-round summary with exactly two carve-outs.
owner_agent: mars
escalation_contact: Max (rule changes); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The per-round Max-facing output contract (CORE §3 "Execution Philosophy — Communicating with Max"), the summary's required structure and voice, the two carve-outs (hard stop, blocking question), the timestamp header and round-end markers, and the boot-contract marker test that guards the rule. NOT authoritative for session open/close mechanics (session-open-protocol.md, session-close-protocol.md), the write-like-max skill content itself (skill source is canonical), business_summary field rules (CORE §8), or peer-to-peer messaging (peer-instance-discipline.md).
linter_version: 1.0.0
---

# Max Reporting — the End-of-Round Summary Discipline

> The system-enforced comms contract: between the start of a round and its single end-of-round summary, an instance emits nothing Max-facing, with exactly two carve-outs. CORE §3 is the canonical statement; `infra:opening-prompt` carries the longer elaboration and points back to CORE §3. This runbook is the operator page: how to compose the summary, when a carve-out applies, how to diagnose violations, and how the rule may change.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| CORE.md §3 (constitution) | The canonical rule text (single-summary invariant, two carve-outs, summary structure) | Constitution payload returned by `kd_session_open`; source doc in Living State constitution store | Koskadeux MCP |
| `infra:opening-prompt` (Living State) | The longer elaboration; must not diverge from CORE §3 | Living State via gateway | Koskadeux MCP |
| write-like-max skill | Max's voice for summaries and outward-facing prose | Claude.ai user skill `write-like-max` | Claude.ai project config |
| Boot-contract marker test | Regression guard: asserts the marker text "The ONLY Max-facing output in a round is one short end-of-round summary" is present in the boot constitution payload | koskadeux-mcp test suite (boot-contract tests) | koskadeux-mcp CI |
| `date -u` on Titan-1 | The `[YYYY-MM-DD HH:MM UTC]` timestamp header on every Max-facing reply | Titan-1 shell | Titan-1 |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Canonical rule in constitution (CORE §3, v9.6 tightening) | SHIPPED | `CORE.md` | boot-contract marker assertion | 2026-07-12 |
| Boot-contract delivery-boundary marker test (guards the delivered payload, not a side copy) | SHIPPED | `koskadeux-mcp/tests` | CI | 2026-07-12 |
| Opening-prompt elaboration pointing at CORE §3 | SHIPPED | `infra:opening-prompt` | manual read at boot | 2026-07-12 |
| Timestamp header + round-end markers (CONTINUE / DECISION / CLOSE SESSION) | SHIPPED | `max-reporting.md` | none (convention) | 2026-07-12 |
| Automated lint of outgoing summaries for jargon/codes | PLANNED | — | n/a | 2026-07-12 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Rule source | CORE.md §3 | constitution store (db) | delivered on every `kd_session_open` | Canonical. If CORE §3 and any elaboration conflict, CORE §3 wins. |
| Elaboration | `infra:opening-prompt` | Living State | boot payload `opening_prompt` | Longer prose; explicitly subordinate to CORE §3. |
| Marker guard | koskadeux-mcp boot-contract test | git (test source) | CI on koskadeux-mcp | Dropping or weakening the §3 marker text from the boot payload fails the build. |
| The operator (Vulcan/Mars) | this runbook §E | none | write-like-max skill; `date -u` | The rule governs OUTPUT only; Max's own interface choices (e.g. thinking visibility) are his call. |
| Waiver store | `config:runbook-waivers` | Living State | runbook-first-gates.md §E-05 discharge path | Carries the accumulated waivers on this subject until discharged by this file's commit SHA. |

Prose: a round is one work cycle that ends in a summary. Everything an instance does inside the round — tool calls, dispatches, diagnostics — stays off Max's screen. The summary is the single delivery point. Two narrow interrupts exist and nothing else: a hard stop (work cannot safely continue) and a blocking question (Max's answer is genuinely required to proceed and cannot wait).

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Compose and deliver the end-of-round summary | write-like-max skill + `date -u` timestamp | n/a | COMPLETE |
| Vulcan/Mars | Issue a hard stop | plain-text report, then stop | n/a | COMPLETE |
| Vulcan/Mars | Ask a blocking question | single question, single response | n/a | COMPLETE |
| Max | Approve changes to the rule | CORE.md amendment (Max approval + one peer review) | Max authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A round of work is complete and Max needs the result
  pre_conditions:
    - all in-round work concluded or parked with state recorded
    - fresh `date -u` timestamp obtained from Titan-1
  tool_or_endpoint: "the chat reply itself — one summary, structured per CORE §3"
  argument_sourcing:
    structure: "(1) what was done, a sentence or two; (2) what is needed from Max, ONLY if something genuinely is; (3) why it mattered, tied plainly to the pillars, with an honest line on necessity/simplicity/better-way; (4) anything critical, omitted if none"
    voice: write-like-max skill; plain business English; outcome first
    exclusions: no BQ codes, gate numbers, SHAs, tool names, or session numbers in the prose
    header: "[YYYY-MM-DD HH:MM UTC] from `date -u` on Titan-1 at the top"
    footer: "round-end marker: CONTINUE / DECISION / CLOSE SESSION"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: one message; Max can act on it without asking what any term means
    verification: re-read before sending; if a non-technical co-founder would stumble, rewrite
  expected_failures:
    - signature: summary contains codes/jargon or narrates process steps
      cause: drafting from working state instead of outcome-first (§F-02)
  next_step_success: await Max's next instruction
  next_step_failure: rewrite before sending; the violation is preventable at composition time
- id: E-02
  trigger: Work cannot safely continue (gateway or database unreachable, or a 2-strike abort)
  pre_conditions:
    - the blocker is verified, not assumed (retry once where cheap)
  tool_or_endpoint: "the chat reply — a plain hard-stop report, then stop"
  argument_sourcing:
    content: what stopped, what was tried, what state is safe; no speculation
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Max knows work is stopped and why; nothing else is attempted
    verification: no further tool calls after the report
  expected_failures:
    - signature: continuing to improvise after reporting the stop
      cause: treating the carve-out as a progress note (§F-01)
  next_step_success: wait for Max or for the blocker to clear
  next_step_failure: stop means stop
- id: E-03
  trigger: Max's answer is genuinely required to proceed and cannot wait for the summary
  pre_conditions:
    - the question is truly blocking; a default or a recorded assumption will not do
  tool_or_endpoint: "the chat reply — one question, framed with just enough context to answer it"
  argument_sourcing:
    content: the decision needed, the options, the recommendation if one exists
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Max can answer in one line
    verification: if the question needs a paragraph of background, it was probably not blocking
  expected_failures:
    - signature: bundling status updates into the question
      cause: smuggling narration through the carve-out (§F-01)
  next_step_success: resume the round with the answer
  next_step_failure: strip the question to the decision and re-ask
- id: E-04
  trigger: The rule itself needs to change
  pre_conditions:
    - concrete failure or friction documented
  tool_or_endpoint: "CORE.md §3 amendment: Max approval + one peer review, version bump, changelog line"
  argument_sourcing:
    procedure: CORE.md footer rule ("Updated by either instance with Max's approval and one peer review"); keep `infra:opening-prompt` and this runbook in sync in the same change
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: CORE version number
  expected_success:
    shape: CORE §3, opening-prompt, boot-contract marker test, and this runbook all agree
    verification: boot-contract test green after the change
  expected_failures:
    - signature: boot-contract test failure on the marker text
      cause: the amendment weakened or dropped the guarded clause (§F-03)
  next_step_success: peer ratification recorded in the CORE changelog
  next_step_failure: restore the marker text or update the test in the SAME reviewed change
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Max-facing narration, acknowledgements, or progress notes appear mid-round | drafting replies between tool calls; treating a carve-out as a status channel | read the transcript: any Max-visible text between round start and the summary that is neither a hard stop nor a blocking question is a violation | §G-01 | CONFIRMED |
| F-02 | Summary contains BQ codes, gate numbers, SHAs, tool names, or session numbers in prose | composing from working state; skipping the write-like-max pass | scan the summary for the exclusion list in §E-01 | §G-02 | CONFIRMED |
| F-03 | koskadeux-mcp CI fails the boot-contract marker assertion | a CORE edit dropped or reworded the guarded clause "The ONLY Max-facing output in a round is one short end-of-round summary" | run the boot-contract test locally; diff CORE §3 against the marker text | §G-03 | CONFIRMED |
| F-04 | Plan gate rejects a session naming this subject ("End-of-round summary / Max reporting" waiver bite) | ≥2 undischarged waiver rows accumulated on the subject before this runbook existed | count the subject's rows in `config:runbook-waivers` lacking discharged_by kind created/commit | §G-04 | CONFIRMED |
| F-05 | Summary omits the timestamp header or round-end marker | convention skipped under time pressure | look at the top and bottom of the sent summary | §G-02 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: The operator (Vulcan/Mars)
  root_cause: output emitted mid-round outside the two carve-outs
  repair_entry_point: composition habit; no code change
  change_pattern: "work silently; buffer everything for the summary. If a message is about to be sent mid-round, apply the test: is this a hard stop, or a question Max must answer to proceed? If neither, it waits. Acknowledge the miss in the next summary only if Max raises it"
  rollback_procedure: n/a
  integrity_check: next round's transcript has exactly one Max-facing message
- id: G-02
  symptom_ref: F-02
  component_ref: The operator (Vulcan/Mars)
  root_cause: jargon or missing header/marker in the summary
  repair_entry_point: the summary draft
  change_pattern: rewrite outcome-first in plain business English via the write-like-max skill; strip the §E-01 exclusion list; add the `date -u` header and a round-end marker before sending
  rollback_procedure: n/a
  integrity_check: a non-technical reader can act on the summary unaided
- id: G-03
  symptom_ref: F-03
  component_ref: Marker guard
  root_cause: CORE amendment broke the guarded clause
  repair_entry_point: the CORE.md change and/or the boot-contract test, in one reviewed change
  change_pattern: either restore the exact marker text in CORE §3, or — if the rule legitimately changed with Max approval + peer review — update the marker assertion to the new canonical sentence in the same change set, never in a separate unreviewed commit
  rollback_procedure: git revert the CORE edit
  integrity_check: boot-contract test green; kd_session_open payload carries the clause
- id: G-04
  symptom_ref: F-04
  component_ref: Waiver store
  root_cause: subject accumulated waivers before the owning page existed
  repair_entry_point: "config:runbook-waivers rows via runbook-first-gates.md §E-05"
  change_pattern: "this runbook IS the covering page: patch the subject's waiver rows with discharged_by {kind: created, ref_or_reason: <bare SHA of the commit that added this file>}"
  rollback_procedure: re-patch discharged_by to null
  integrity_check: next kd_session_open standup no longer tripwires the subject
```

## §H. Evolve

### §H.1 Invariants

- **One summary per round.** The only Max-facing output in a round is one short end-of-round summary.
- **Exactly two carve-outs.** Hard stop; blocking question. No third category may be added without a CORE amendment.
- **CORE §3 is canonical.** The opening-prompt elaboration and this runbook must not diverge from it; on conflict, CORE §3 wins.
- **Rule changes are Max decisions.** CORE §3 changes require Max approval plus one peer review, per the constitution's own amendment rule.
- **The marker test guards the delivered payload.** The boot-contract assertion checks the constitution payload returned on open, not a side copy.
- **Output-only scope.** The rule takes no position on Max's interface choices (e.g. deliberately enabling thinking visibility).

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Removing the single-summary rule or adding a third carve-out without a Max-approved, peer-reviewed CORE amendment.
- Removing or weakening the boot-contract marker assertion, or pointing it at anything other than the delivered boot payload.
- Making the elaboration (`infra:opening-prompt`) authoritative over CORE §3.
- Changing or removing any §H.1 invariant.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Changing the summary's required structure (the four numbered elements) or the prose exclusion list.
- Changing the timestamp header format or the round-end marker vocabulary.
- Adding automated linting of outgoing summaries (the NOT_BUILT §B row).

### §H.4 SAFE predicates

SAFE otherwise:
- Documentation and example additions; refreshing §B/§J after verifications.

### §H.5 Boundary definitions

#### module

Not a code system. The nearest modules are CORE.md §3 (constitution store) and the koskadeux-mcp boot-contract test file.

#### public contract

The CORE §3 clause text, the marker sentence guarded by the boot-contract test, and the summary structure in §E-01.

#### runtime dependency

None added. The discipline uses only existing surfaces (chat, `date -u`, write-like-max skill).

#### config default

None. The rule is unconditional; there is no enforce-mode toggle.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Disputes unresolvable under the predicates escalate to Max; the ruling is added to §H.1 as a clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A round finished three pieces of work, one ticket was filed, and nothing is needed from Max. What does the reply contain?
    expected_answers:
      - kind: human_action
        action: one summary with a UTC timestamp header, outcome-first plain-English coverage of the work and why it mattered, no codes/SHAs/tool names, the "needed from Max" element omitted, and a round-end marker
    weight: 0.07692308
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: Mid-round, the Living State database becomes unreachable and a retry fails. What is sent to Max?
    expected_answers:
      - kind: human_action
        action: a plain hard-stop report (what stopped, what was tried, safe state) and then nothing further — no improvised continuation
    weight: 0.07692308
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Two irreversible options exist mid-round and neither a default nor a recorded assumption is defensible. What is sent?
    expected_answers:
      - kind: human_action
        action: one blocking question stating the decision, the options, and a recommendation — no bundled status updates
    weight: 0.07692308
  - id: I-04
    type: operate
    refs: [E-01]
    scenario: The work involved gates, SHAs, and dispatch task ids. How do those appear in the summary?
    expected_answers:
      - kind: human_action
        action: they do not appear in the prose; the summary describes outcomes in business terms and the identifiers stay in Living State/tickets/handoff
    weight: 0.07692308
  - id: I-05
    type: isolate
    refs: [F-01]
    scenario: Reviewing a transcript, you find "on it — dispatching the builder now" sent to Max mid-round. Violation?
    expected_answers:
      - kind: classification
        verdict: yes — narration outside the two carve-outs; repair per §G-01
    weight: 0.07692308
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: koskadeux-mcp CI fails with the boot-contract marker assertion after a CORE edit. First action?
    expected_answers:
      - kind: human_action
        action: diff CORE §3 against the guarded marker sentence; restore it or update the assertion in the same Max-approved, peer-reviewed change
    weight: 0.07692308
  - id: I-07
    type: repair
    refs: [G-04]
    scenario: The plan gate bites on the subject "End-of-round summary / Max reporting" although this runbook now exists at commit abc1234. Fix?
    expected_answers:
      - kind: human_action
        action: 'patch the subject rows in config:runbook-waivers with discharged_by {kind: created, ref_or_reason: abc1234} per runbook-first-gates.md §E-05'
    weight: 0.07692308
  - id: I-08
    type: evolve
    refs: [§H.2]
    scenario: A proposal adds a third carve-out ("brief progress note on tasks longer than an hour") directly to this runbook. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING — carve-outs are fixed at two unless CORE §3 is amended with Max approval and peer review
    weight: 0.07692308
  - id: I-09
    type: isolate
    refs: [F-05]
    scenario: A summary was sent without the UTC timestamp header and without a round-end marker. Is this a rule violation and where is it caught?
    expected_answers:
      - kind: human_action
        action: convention violation, not a carve-out breach — caught by reading the sent message top and bottom; repair per §G-02 on the next summary
    weight: 0.07692308
  - id: I-10
    type: isolate
    refs: [F-02]
    scenario: A summary reads "merged feed47b6 after Gate-1 mandates folded; dispatched task 1920d298". What specifically fails and how do you verify?
    expected_answers:
      - kind: human_action
        action: scan against the §E-01 exclusion list — SHAs, gate numbers, and task ids in prose all fail; verify by re-reading the draft before sending
    weight: 0.07692308
  - id: I-11
    type: repair
    refs: [G-03]
    scenario: The rule legitimately changed with Max approval and peer review, and CI is red on the old marker sentence. Fix?
    expected_answers:
      - kind: human_action
        action: update the boot-contract marker assertion to the new canonical sentence in the SAME reviewed change set as the CORE edit, never a separate unreviewed commit
    weight: 0.07692308
  - id: I-12
    type: ambiguous
    refs: [E-02, E-03]
    scenario: Mid-round, a destructive production step is reached that requires Max's explicit gate, and simultaneously the gateway starts timing out intermittently. One message is owed — which carve-out, and what goes in it?
    expected_answers:
      - kind: human_action
        action: if work can safely pause, send the blocking question (the Max-gated decision) and note nothing else; if the gateway degradation makes continuing unsafe, it is a hard stop that reports both facts plainly — never two separate mid-round messages
    weight: 0.07692308
  - id: I-13
    type: evolve
    refs: [§H.3]
    scenario: A proposed change renames the round-end marker vocabulary from CONTINUE / DECISION / CLOSE SESSION to a three-icon scheme. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW — marker vocabulary is a §H.3 predicate, not a §H.1 invariant
    weight: 0.07692308
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1189
last_refresh_commit: d4dd366
last_refresh_date: 2026-07-12T09:00:00Z
owner_agent: mars
refresh_triggers:
  - any CORE §3 amendment
  - any change to the boot-contract marker assertion
  - any change to infra:opening-prompt's Communicating-with-Max section
  - a third undischarged waiver or a confirmed violation pattern on this subject
scheduled_cadence: 180d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-12T09:00:00Z
first_staleness_detected_at: null
```

Refresh log:
- S1192 (2026-07-12): owner_agent corrected to mars — empirical lint run confirmed the current linter has no owner enum restriction (the S1189 'enum lacks mars' claim was stale for this linter); either instance still operates this page.
- S1189 (2026-07-12): first authoring (by mars; owner_agent recorded as vulcan because the linter's owner enum was believed to predate the S811 symmetric-peer model — either instance operates this page), against CORE.md v9.7 §3 (read verbatim from the S1189 boot payload), `infra:opening-prompt` (same payload), and the runbook-first-gates.md §E-05/§G-07 discharge procedure. Written to clear the two accumulated waivers on subject "End-of-round summary / Max reporting".

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1189 / 2026-07-12T09:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
