---
system_name: constitution-amendment
purpose_sentence: How CORE.md (the agent constitution, served as infra:constitution on every session boot) is amended — a unanimous Council gate (CC, DeepSeek, GLM) plus Max's direct approval, then a versioned apply to Living State and the backend git mirror with boot-delivery verification.
owner_agent: mars
escalation_contact: Max (human operator)
lifecycle_ref: §J
authoritative_scope: The amendment process for CORE.md / infra:constitution only. NOT the companion docs (BUSINESS-CONTEXT.md, PROTOCOLS.md, INFRASTRUCTURE.md), NOT the Design Charter (changed by replacement per its own rule), NOT runbooks (standard §L governs those).
linter_version: 1.0.0
---

# Constitution Amendment — changing CORE.md

**The rule (CORE footer, v9.11, Max directive S1242):** every amendment to CORE.md — including editorial changes — requires a **unanimous Council gate (CC, DeepSeek, GLM — 3/3 valid verdicts per CORE §5 decision rules) AND Max's direct approval**. Either instance may then apply the approved change. No reduced quorum, no voter substitution, no builder vote. This replaced the prior "Max approval + one peer review" rule; v9.10 and v9.11 were the last amendments made under the old rule.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Constitution served on session boot from the DB entity | SHIPPED | `koskadeux-mcp:tools/session.py` | `tests/integration/test_constitution_comms_invariant.py` | 2026-07-16 |
| Boot-contract marker assertion (§3 comms invariant text must be present) | SHIPPED | `tests/integration/test_constitution_comms_invariant.py` | CI on koskadeux-mcp | 2026-07-16 |
| Optimistic-versioned entity patch | SHIPPED | `koskadeux-mcp:tools/state.py` | entity history v16→v18 (S1242 live) | 2026-07-16 |
| Git mirror on backend main | SHIPPED | `ai-market-backend:docs/core/CORE.md` | manual byte diff vs entity (E-04) | 2026-07-16 |
| Unanimous Council gate for amendments | SHIPPED | `koskadeux-mcp:tools/agents.py` | CORE v9.11 footer + §5 decision rules | 2026-07-16 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Living State entity | `tools/state.py:state_request` | Postgres `state_entities`, key `infra:constitution` (body.content, body.version_label, append-only amendment records) | kd_session_open boot payload; ops console | Boot source of truth. Optimistic `expected_version` on every write. |
| Git mirror | `ai-market-backend:docs/core/CORE.md` | git, backend main | Railway auto-deploys backend on push (docs-only change still rebuilds) | Mirrors the entity byte-for-byte. On divergence the entity wins (G-02). |
| Boot delivery | `tools/session.py:kd_session_open` | Titan-1 `registry.db` | both instances on every open | 46,000-char wire budget; §3 marker assertion; constitution_source=db. |
| Council gate | `tools/agents.py:council_request` | council task logs | CC / DeepSeek / GLM voters | 3/3 valid unanimous verdicts required. Voter quirks: agent-dispatch.md, codex-mp.md. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan / Mars | dispatch the amendment diff to each voter | `council_request` (agent=cc, deepseek, glm) | MCP session | COMPLETE |
| Vulcan / Mars | apply the entity patch | `state_request` action=patch | MCP session (boot-gated) | COMPLETE |
| Vulcan / Mars | commit + push the git mirror | `shell_request` (git; `KD_ALLOW_MAIN_PUSH=1` on the push) | Titan-1 shell | COMPLETE |
| Max | final approval / veto | direct instruction in session | human | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An amendment to CORE.md is proposed (by Max or by an instance)
  pre_conditions:
    - Exact old→new wording drafted (verbatim strings, not a paraphrase)
    - The §3 comms marker text is untouched by the diff
    - Projected content size under 46,000 chars
  tool_or_endpoint: council_request (three dispatches, agent=cc / deepseek / glm)
  argument_sourcing:
    diff: the exact old→new wording inline in each prompt (GLM and DeepSeek have no filesystem access)
    verdict_enum: offer APPROVE | APPROVE_WITH_NITS | APPROVE_WITH_MANDATES | REVISE | REQUEST_CHANGES | REJECT verbatim
  idempotency: IDEMPOTENT
  expected_success:
    shape: three valid verdicts, all APPROVE-class (3/3 unanimous)
    verification: each voter's verdict parses; model_matched where applicable
  expected_failures:
    - signature: missing / malformed / model-mismatched verdict
      cause: transport or parser failure — gate fails closed (F-04)
    - signature: any non-APPROVE-class verdict
      cause: substantive objection — amendment returns to drafting; do not proceed to E-02
  next_step_success: E-02
  next_step_failure: F-04, or redraft
- id: E-02
  trigger: Unanimous Council approval obtained
  pre_conditions:
    - E-01 complete with 3/3 APPROVE-class verdicts
  tool_or_endpoint: present the exact wording + Council result to Max in the round summary or a blocking question
  argument_sourcing:
    wording: verbatim from the gated diff
  idempotency: IDEMPOTENT
  expected_success:
    shape: Max's direct approval, recorded verbatim in the amendment record
    verification: approval text quoted in body.core_amendment_* record
  expected_failures:
    - signature: Max declines or amends
      cause: final-authority veto — return to drafting (re-gate if wording changes)
  next_step_success: E-03
  next_step_failure: redraft and re-run E-01
- id: E-03
  trigger: Council-unanimous + Max-approved amendment ready to apply
  pre_conditions:
    - E-01 and E-02 complete
    - Backend repo clean and at origin/main
  tool_or_endpoint: edit docs/core/CORE.md (assert each old string occurs exactly once) → git commit + KD_ALLOW_MAIN_PUSH=1 push → state_request patch infra:constitution
  argument_sourcing:
    expected_version: current entity version from a fresh state_request get
    content: read the committed file byte-exact (do NOT retype); the S1242 pattern posts to localhost:8765/api/call with the file read programmatically
    amendment_record: new body.core_amendment_<session> key with change, reason, approvals, commit SHA, safety_check
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: expected_version (a replayed patch fails on version conflict rather than double-applying)
  expected_success:
    shape: backend main advanced; entity version +1; version_label bumped
    verification: E-04
  expected_failures:
    - signature: version_conflict on the patch
      cause: concurrent entity write (F-01)
    - signature: GUARDRAIL refusal text on the push
      cause: pre-push hook noise — may print even when the push lands (F-05); verify ground truth before retrying
  next_step_success: E-04
  next_step_failure: F-01 / F-05
- id: E-04
  trigger: Amendment applied; verify delivery
  pre_conditions:
    - E-03 complete
  tool_or_endpoint: state_request get infra:constitution; byte-compare vs git show origin/main:docs/core/CORE.md; next kd_session_open shows the new version_label
  argument_sourcing:
    entity_content: state_request get
    file_content: git show origin/main:docs/core/CORE.md
  idempotency: IDEMPOTENT
  expected_success:
    shape: version_label matches, marker text present, sizes equal and under 46,000
    verification: read-only comparison
  expected_failures:
    - signature: entity and file differ
      cause: one side applied without the other (F-02)
  next_step_success: done — log a decision event on infra:constitution
  next_step_failure: G-02
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Entity patch rejected with a version conflict | concurrent write to infra:constitution between get and patch | re-run state_request get; compare returned version vs the expected_version sent | G-01 | CONFIRMED |
| F-02 | Git file and entity content diverge | one side edited without the other, or a retyped (not file-read) patch introduced drift | byte-compare `git show origin/main:docs/core/CORE.md` vs entity body.content | G-02 | CONFIRMED |
| F-03 | Boot-contract CI test fails after an amendment | §3 comms marker text altered, or constitution dropped/truncated in the boot payload | run `tests/integration/test_constitution_comms_invariant.py` in koskadeux-mcp; grep content for the marker string | G-03 | CONFIRMED |
| F-04 | Council gate cannot reach 3/3 valid verdicts | voter transport failure, malformed verdict enum, model mismatch, missing cwd/inline diff for GLM/DeepSeek | inspect each council task result; classify per agent-dispatch.md / codex-mp.md §F | | CONFIRMED |
| F-05 | Push to backend main prints a GUARDRAIL refusal yet may have landed | pre-push hook emits the refusal text even on a KD_ALLOW_MAIN_PUSH=1 push that succeeds (observed S1242, commits 356a2dfe and 6851a671) | `git fetch origin && git log -1 origin/main`, and confirm via the GitHub API commits/main | | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Living State entity
  root_cause: optimistic-lock conflict — another write advanced the entity between read and patch
  repair_entry_point: tools/state.py:state_request (action=get then action=patch)
  change_pattern: re-get the entity, confirm the concurrent change does not overlap the amendment, re-apply the identical patch at the version returned in the conflict error
  rollback_procedure: none needed — the failed patch wrote nothing
  integrity_check: E-04 byte comparison passes
- id: G-02
  symptom_ref: F-02
  component_ref: Git mirror
  root_cause: file and entity updated out of step, or drift introduced by retyping content instead of reading the committed file
  repair_entry_point: ai-market-backend:docs/core/CORE.md + tools/state.py:state_request
  change_pattern: the ENTITY is the boot authority — sync the file to the entity content (write file from entity, commit as a sync), unless the entity is provably stale (missing an approved amendment), in which case patch the entity from the file with a sync note in the amendment record
  rollback_procedure: git revert the sync commit; entity history preserves every prior version
  integrity_check: byte-compare passes; boot shows the expected version_label
- id: G-03
  symptom_ref: F-03
  component_ref: Boot delivery
  root_cause: amendment touched the §3 comms marker text or pushed content over the wire budget
  repair_entry_point: docs/core/CORE.md §3 Execution Philosophy (Communicating with Max clause)
  change_pattern: restore the marker sentence verbatim ("The ONLY Max-facing output in a round is one short end-of-round summary"), re-run the boot-contract test, then re-apply the amendment around the protected text; if size is the problem, trim history prose per the v9.9 precedent rather than raising the budget
  rollback_procedure: revert to the prior entity version (entity history) and prior git commit
  integrity_check: test_constitution_comms_invariant.py green; content size under 46,000
```

## §H. Evolve

### §H.1 Invariants

- Every CORE.md change — including editorial — requires a unanimous Council gate (CC, DeepSeek, GLM; 3/3 valid verdicts) AND Max's direct approval. No reduced quorum, no voter substitution, no builder vote (Max directive S1242; CORE v9.11 footer).
- The §3 comms-invariant marker text stays verbatim; the boot-contract test enforces it.
- `infra:constitution` is the boot source of truth; the git file is a mirror.
- Total content stays under the 46,000-char boot wire budget.
- Amendment records in the entity body are append-only; approvals are quoted verbatim.

### §H.2 BREAKING predicates

- Weakening or removing the amendment rule itself (footer or this runbook's gate steps).
- Any edit touching the §3 marker sentence.
- Content exceeding the wire budget.
- Patching the entity without expected_version.

### §H.3 REVIEW predicates

- Changing any procedural step in this runbook (normal runbook PR review per standard §L).
- Changing where the mirror lives or how boot sources the constitution.

### §H.4 SAFE predicates

- §J metadata refresh on this runbook.
- Typo fixes in this runbook's prose that do not alter a step.

### §H.5 Boundary definitions

#### module

`tools/session.py` (boot delivery), `tools/state.py` (entity writes) in koskadeux-mcp; `docs/core/` in ai-market-backend.

#### public contract

The kd_session_open boot payload (constitution content + version) consumed by both instances; the CORE footer amendment rule itself.

#### runtime dependency

Postgres (state_entities) on Railway; the koskadeux MCP server (localhost:8765) for gated writes; git/GitHub for the mirror.

#### config default

The 46,000-char boot wire budget (koskadeux-mcp boot fit logic); KD_ALLOW_MAIN_PUSH gate on backend main pushes.

### §H.6 Adjudication

Disputed classifications escalate to Max. Emergency exception: none — there is no emergency path for constitution edits; if production is on fire, fix production, not the constitution.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - §E E-01
    scenario: Max asks to change a CORE §3 rule; produce the correct first action.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys:
          - agent
          - task
    weight: 0.09090909
  - id: I-02
    type: operate
    refs:
      - §E E-03
    scenario: An amendment has 3/3 Council APPROVE and Max's recorded approval; apply it.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys:
          - action
          - key
          - expected_version
    weight: 0.09090909
  - id: I-03
    type: operate
    refs:
      - §E E-04
    scenario: An amendment was just applied; verify it reached both stores and boot delivery.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys:
          - action
          - key
    weight: 0.09090909
  - id: I-04
    type: isolate
    refs:
      - §F F-01
    scenario: The entity patch returns a version conflict; diagnose before retrying.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys:
          - action
          - key
    weight: 0.09090909
  - id: I-05
    type: isolate
    refs:
      - §F F-03
    scenario: CI fails on the boot-contract test right after a constitution edit; find why.
    expected_answers:
      - kind: tool_call
        tool: grep
        argument_keys:
          - pattern
    weight: 0.09090909
  - id: I-06
    type: isolate
    refs:
      - §F F-05
    scenario: The main push printed a GUARDRAIL refusal; determine whether the commit landed before doing anything else.
    expected_answers:
      - kind: tool_call
        tool: git
        argument_keys:
          - fetch
    weight: 0.09090909
  - id: I-07
    type: repair
    refs:
      - §G G-02
    scenario: The git CORE.md and the entity content differ by one paragraph; repair.
    expected_answers:
      - kind: human_action
        action: sync the file from the entity content and commit as a sync (entity is boot authority)
    weight: 0.09090909
  - id: I-08
    type: repair
    refs:
      - §G G-03
    scenario: The §3 marker sentence was reworded in an amendment; repair.
    expected_answers:
      - kind: human_action
        action: restore the marker sentence verbatim, re-run the boot-contract test, re-apply the amendment around it
    weight: 0.09090909
  - id: I-09
    type: evolve
    refs:
      - §H §H.2
    scenario: A proposal suggests dropping the Council gate for "editorial-only" CORE changes; classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.09090909
  - id: I-10
    type: evolve
    refs:
      - §H §H.4
    scenario: A typo fix in this runbook's prose that changes no step; classify.
    expected_answers:
      - kind: classification
        verdict: SAFE
    weight: 0.09090909
  - id: I-11
    type: ambiguous
    refs:
      - §E E-03
      - §F F-02
    scenario: Max approves an amendment verbally but the Council gate was never run; the instance is about to apply. What is the correct first action?
    expected_answers:
      - kind: human_action
        action: stop and run the unanimous Council gate (E-01) before applying — Max approval alone is necessary but not sufficient
      - kind: tool_call
        tool: council_request
        argument_keys:
          - agent
          - task
    weight: 0.09090909
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1242
last_refresh_commit: 6851a671
last_refresh_date: "2026-07-16"
owner_agent: mars
refresh_triggers:
  - any CORE.md amendment
  - Council roster change
  - boot wire budget change
scheduled_cadence: 90d
last_harness_pass_rate: 0.0
last_harness_date: "2026-07-16"
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
retrofit: false
linter_version: 1.0.0
last_lint_run: S1242 / 2026-07-16T12:25:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
