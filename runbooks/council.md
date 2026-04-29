---
system_name: council
purpose_sentence: A multi-agent review and build system that produces production-quality code via gated cross-review across MP (primary), AG (secondary), DeepSeek (full voter), and CC (fallback).
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Stable architecture, mechanics, and reasoning of the Council operating system. Live config (current model frontiers, retired-agent state, dispatch participants, known quirks) is canonically tracked in infra:council-comms Living State entity.

  Cross-runbook reference convention: file-qualified IDs `<file-stem>:<id>` (e.g., `agent-dispatch:F-01` for symptom F-01 in agent-dispatch.md). Same-file references retain bare `<id>` form. (AC8.)
linter_version: 1.0.0
---

# Council

## §A. Header

The YAML frontmatter above defines the §A header. §J is authoritative for lifecycle refresh tracking; this header is the display summary for stateless readers.

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

`council_request` is the canonical code entry point for Council operations. The Council is documented here as one system: agent rosters, `review_order`, and `dispatch_patterns` belong to the same operating model, while live participant config remains authoritative in `infra:council-comms`.

Strategic why: MP is primary reviewer because Codex CLI automated; deeper wiring-gap detection per S526 Chunk 3B precedent. AG is cross-vote and secondary because Gemini 3.1 Pro is a frontier reviewer, but line-number fabrication risk on code audits per S499 excludes AG from `gate3_post_build_audit` since S342. DeepSeek is a full voter after graduating S528 with 94 dispatches, `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and statistical_record_floor crushed 4.7x. CC is fallback builder because it gives a 300s MP Codex CLI timeout safety net, Opus-tier reasoning for complex multi-file builds, and a 600s default timeout.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Council Dispatch | `koskadeux-mcp/tools/agents.py:_handle_call_*` | `infra:council-comms`, dispatch task records | Codex CLI, Gemini/AG server, DeepSeek API/server, Claude Code | Routes build, review, and fallback work to the configured agent roster. |
| Gate Review Flow | `build:bq-* Living State entities` | build entities, gate status fields, review verdicts | Council dispatch, author-mode tokens, runbook specs | Implements the BQ 4-gate flow and binds authoring/review mode to dispatch provenance. |
| Council Hall | `koskadeux-mcp/tools/agents.py:_handle_council_hall` | deliberation IDs, response transcripts | MP, AG, DeepSeek, Vulcan synthesis | Runs multi-agent deliberation when independent reviews are insufficient. |
| Agent Roster | `infra:council-comms` | active agents, retired agents, quirks, model frontier notes | dispatch gateway, runbooks, memory references | Live config source for MP, AG, DeepSeek, CC, Vulcan, and retired XAI cold storage. |
| Review Order | `infra:council-comms.review_order` | ordered voter list, fallback policy | Gate Review Flow, Council Hall | Defines primary, secondary, full-voter, and fallback sequencing. |
| Dispatch Patterns | `infra:council-comms.dispatch_patterns` | mode templates, timeout caps, cost caps | Council Dispatch, gateway tokens | Encodes review-only, author-mode, fallback-build, and deliberation routing constraints. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| MP | build, primary review, spec authoring | Codex CLI / GPT-5.5 | full repo write | COMPLETE |
| AG | cross-vote review, secondary | Gemini CLI / Gemini 3.1 Pro | repo read | COMPLETE |
| DeepSeek | full voter (review-only, $1/dispatch cap) | DeepSeek API / deepseek-v4-pro | repo read | COMPLETE |
| CC | fallback builder | Claude Code / Opus | full repo write, 600s timeout | COMPLETE |
| Vulcan | orchestrator (Vulcan-direct authoring + state management) | Anthropic API | gateway, Living State, all repos | COMPLETE |
| XAI | DEPRECATED retired S528; architecture-only niche superseded | Grok CLI | retired | PARTIAL — retired; cold-storage details move to `agent-dispatch.md` appendix in C2 |

MP owns primary review because the Codex CLI path is automated and has shown deeper wiring-gap detection per S526 Chunk 3B. AG remains valuable as a Gemini 3.1 Pro frontier cross-vote, but S499 line-number fabrication risk means code-audit line claims must be verified before use. DeepSeek is a full voter because S528 graduation produced 94 dispatches with `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and statistical_record_floor crushed 4.7x. XAI is retired because line-number fabrication exclusion has applied since S342 and DeepSeek superseded the architecture-only niche; see the retired-agents appendix planned for `agent-dispatch.md`.

## §E. Operate

```yaml operate
- id: E-01
  trigger: A build or audit needs a Council review dispatch.
  pre_conditions: [target_repo_available, dispatch_mode_selected, Living State build entity exists when tied to a BQ]
  tool_or_endpoint: council_request(action=review, agent=<mp|ag|deepseek>, prompt=<task>, context_refs=<refs>)
  argument_sourcing:
    agent: choose from §D based on requested role and auth scope
    prompt: derive from BQ gate task or operator request
    context_refs: include spec paths, branch name, commit SHA, and relevant Living State entity
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(agent + target_repo + branch + gate + prompt_digest)
  expected_success: {shape: Dispatch task id plus reviewer verdict or requested artifact, verification: Match task result to the requested gate role and confirm no auth-mode mismatch}
  expected_failures:
    - {signature: "timeout", cause: agent process exceeded configured timeout or progress guard}
    - {signature: "read-only agent attempted write", cause: dispatch role/auth boundary mismatch}
  next_step_success: Attach the verdict or artifact to the BQ review record
  next_step_failure: Isolate using §F-01, §F-02, or §F-03 depending on signature
- id: E-02
  trigger: A BQ chunk needs gate review before promotion.
  pre_conditions: [build entity status is in_progress, branch and commit SHA are known, required specs are readable]
  tool_or_endpoint: council_request(action=gate_review, review_order=<infra:council-comms.review_order>, build_id=<build:bq-*>, commit=<sha>)
  argument_sourcing:
    review_order: read from infra:council-comms
    build_id: read from Living State build entity
    commit: read from git rev-parse HEAD on the feature branch
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: build_id + gate + commit
  expected_success: {shape: Gate verdict set with primary and cross-vote results, verification: Confirm MP primary review and required secondary/full-voter participation are recorded}
  expected_failures:
    - {signature: "missing dispatch token", cause: author-mode or review-mode gateway token not bound}
    - {signature: "stale review_order", cause: dispatcher read old infra:council-comms config}
  next_step_success: Patch the BQ entity with the gate verdict and next gate status
  next_step_failure: Escalate to §G-03 or Council Hall if verdicts conflict
- id: E-03
  trigger: Independent reviews disagree or a Council policy question blocks the next action.
  pre_conditions: [at least two independent reviews exist or the operator has a policy question, disagreement or ambiguity is explicitly stated]
  tool_or_endpoint: council_hall(topic=<question>, participants=<agents>, evidence_refs=<refs>)
  argument_sourcing:
    question: summarize the blocking disagreement
    participants: read from infra:council-comms dispatch_patterns for hall deliberation
    evidence_refs: include specs, commits, review transcripts, and Living State entity keys
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(topic + sorted(evidence_refs))
  expected_success: {shape: Deliberation transcript with synthesized decision and dissent notes, verification: Confirm synthesis cites all participant positions and names the next action}
  expected_failures:
    - {signature: "agent silence", cause: participant backend unavailable or timed out}
    - {signature: "no resolution", cause: evidence gap or policy ruling needed from Max}
  next_step_success: Apply the synthesized decision to the build or runbook task
  next_step_failure: Escalate unresolved policy questions to Max
```

## §F. Isolate

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
  component_ref: Dispatch Patterns
  root_cause: Dispatcher task state lagged behind actual repo writes.
  repair_entry_point: infra:council-comms.dispatch_patterns
  change_pattern: Reconcile git commit SHA, dispatcher task id, and Living State build body.summary before promoting the gate.
  rollback_procedure: Revert the state patch if the commit SHA or branch does not match the artifact under review.
  integrity_check: Confirm git HEAD, dispatcher result, and Living State build summary all name the same artifact.
```

## §H. Evolve

### §H.1 Invariants

- `council_request` remains the canonical code entry point for Council dispatch.
- `infra:council-comms` remains authoritative for live roster, model frontier, retirement, quirk, and dispatch-pattern state.
- Read-only review agents must not receive repo write scope without explicit Council change review.

### §H.2 BREAKING predicates

- Retiring a Council member is BREAKING because `review_order` changes.
- Enabling write-mode for a read-only agent is BREAKING because it changes an auth boundary.
- Removing `council_request` as the canonical dispatch entry point is BREAKING.

### §H.3 REVIEW predicates

- Adding a Council member requires REVIEW.
- Changing model frontiers, such as Gemini 3.1 to 4.0, requires REVIEW.
- Changing dispatch participants or Council Hall participant defaults requires REVIEW.

### §H.4 SAFE predicates

- Increasing the $/dispatch cap is SAFE when auth scope, review order, and participant roles do not change.
- Documentation-only updates that preserve the live-config deference to `infra:council-comms` are SAFE.
- Timeout tuning inside an existing dispatch pattern is SAFE unless it changes fallback ownership.

### §H.5 Boundary definitions

#### module

The module boundary is the Council operating slice in Koskadeux MCP, Living State build entities, and the runbooks that document them.

#### public contract

The public contract is the `council_request` surface, Council Hall surface, BQ gate review semantics, and dispatch-mode/auth-mode distinction exposed to operators and agents.

#### runtime dependency

A runtime dependency is any agent backend, CLI, API, gateway token service, or Living State entity required for Council dispatch or gate review to run.

#### config default

A config default is any default model frontier, review order, dispatch timeout, cost cap, or participant list stored in `infra:council-comms`.

### §H.6 Adjudication

When two agents classify a Council change differently, use the more restrictive class and record the dispute in the BQ review record. Max resolves classification disputes that alter auth scope, membership, or gate policy.

## §I. Acceptance Criteria

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

## §J. Lifecycle

C1 provisional lifecycle metadata is present only to keep owner and refresh intent explicit. C5c populates the final AC11 fields from the integration commit and harness reports.

```yaml lifecycle
last_refresh_session: S529
last_refresh_commit: 841f915
last_refresh_date: 2026-04-29T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - bq_completion
  - gate_approval
  - infra_council_comms_drift
  - scheduled_cadence
scheduled_cadence: 90d
last_harness_pass_rate: 0.0
last_harness_date: 2026-04-29T00:00:00Z
first_staleness_detected_at: null
```

Initial conformance status for the Council runbook family is `provisional` per Gate 1 §10 until C5c finalizes lifecycle telemetry after the Infisical cutover constraint is cleared.

## §K. Conformance

C1 placeholder: C5c populates the final AC12 conformance fields after C5a.1 scenario authoring and C5b harness execution. This chunk intentionally leaves §I incomplete, so lint failure on §I scenario count/distribution is expected.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S529 / 2026-04-29T00:00:00Z
last_lint_result: FAIL
trace_matrix_path: null
word_count_delta: null
```

`conformance_status: provisional` is the intended C5c value under Gate 1 §10; the current linter schema does not yet accept that key in the §K YAML block.
