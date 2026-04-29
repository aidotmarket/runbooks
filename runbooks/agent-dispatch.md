---
system_name: agent-dispatch
purpose_sentence: Council dispatch mechanics for delegating tasks to agents (MP, AG, DeepSeek, CC) and managing dispatch surfaces (council_request, dispatch_mp_build, council_hall).
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Stable dispatch mechanics + symptom/repair patterns. Live config (current model frontiers, dispatch participants, environment paths) is canonically tracked in infra:council-comms Living State entity.

  Cross-runbook reference convention: file-qualified IDs `<file-stem>:<id>` per parent runbooks/council.md §A. Same-file references retain bare IDs.
linter_version: 1.0.0
---

# Agent Dispatch

## §A. Header

The YAML frontmatter above defines the §A header. This runbook documents stable dispatch mechanics, operational failure patterns, and repair decisions for Council agent dispatch.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| `council_request` unified dispatch | SHIPPED | `koskadeux-mcp/tools/agents.py:_handle_call_*` | Koskadeux MCP dispatch integration coverage | 2026-04-29 |
| `dispatch_mp_build` background build dispatch | SHIPPED | `koskadeux-mcp/tools/agents.py:_handle_dispatch_mp_build` | MP background dispatch smoke coverage | 2026-04-29 |
| `council_hall` deliberation dispatch | SHIPPED | `koskadeux-mcp/tools/agents.py:_handle_council_hall` | Council Hall transcript dispatch coverage | 2026-04-29 |
| Codex CLI backend for MP | SHIPPED | `koskadeux-mcp/dispatch_codex_cli.py` | Codex CLI dispatch path exercised by MP build/review tasks | 2026-04-29 |
| Gemini/AG server backend | SHIPPED | `koskadeux-mcp/antigravity_client.py` | AG server health + task dispatch coverage | 2026-04-29 |
| DeepSeek server/API backend | SHIPPED | `koskadeux-mcp/deepseek_server.py` | DeepSeek review-schema and server health coverage | 2026-04-29 |
| Claude Code backend for CC | SHIPPED | `koskadeux-mcp/tools/agents.py:_handle_call_cc` | CC background task dispatch coverage | 2026-04-29 |
| XAI Grok dispatch | DEPRECATED | `koskadeux-mcp/xai_client.py` | Retired S528; cold-storage only, no active dispatch coverage | 2026-04-29 |

## §C. Architecture & Interactions

Dispatch is a gateway-controlled routing layer. Operators submit a task, target agent, mode, working directory, and evidence references; the gateway chooses the agent backend, applies mode constraints, and returns either a synchronous result or a background task id.

Strategic why: Why MP=primary dispatch builder: Codex CLI automation and deeper wiring-gap detection per S526 Chunk 3B precedent make MP the default builder/reviewer path. Why AG=secondary cross-vote: Gemini 3.1 Pro frontier reasoning is valuable for independent review, but line-number fabrication risk excludes AG from `gate3_post_build_audit` since S342. Why DeepSeek=graduated full voter S528: 94 dispatches, `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and statistical record floor crushed 4.7x justified full-voter dispatch. Why CC=fallback builder: it is the 300s MP Codex CLI timeout safety net and provides Opus-tier reasoning for complex multi-file builds.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Dispatch Gateway | `koskadeux-mcp/tools/agents.py:_handle_call_*` | task records, Living State build refs | MP, AG, DeepSeek, CC, Vulcan | Normalizes task args and mode boundaries before backend invocation. |
| MP Backend | `koskadeux-mcp/dispatch_codex_cli.py` | Codex config, git branch, build task record | Codex CLI / GPT-5.5 | Synchronous reviews may time out; substantial builds use `dispatch_mp_build`. |
| AG Backend | `koskadeux-mcp/ag_server.py` -> `antigravity_client.py` | AG server task record, Vertex auth env | Gemini CLI / Gemini 3.1 Pro | Read-only review prompts must state no file modification. |
| DeepSeek Backend | `koskadeux-mcp/deepseek_server.py` -> `deepseek_client.py` | DeepSeek task record, API token env | DeepSeek API / deepseek-v4-pro | Full voter; read-oriented review path with strict result validation. |
| CC Backend | `koskadeux-mcp/tools/agents.py:_handle_call_cc` | background task id, working tree | Claude Code / Opus | Fallback builder path with full repo write and longer timeout. |
| Environment Loader | launch scripts and LaunchAgents | PATH, Infisical-backed tokens, local config | Codex CLI, Gemini, DeepSeek, Claude Code | `gemini` must be on PATH; provider tokens must come from approved secret sources. |
| MCP Tool Prefix | dispatched prompt or MCP tool invocation | tool-call transcript | Koskadeux MCP bridge | Tool prefix casing must use capitalized `Koskadeux:`; lowercase can silently fail. |
| Cross-Runbook IDs | runbook prose convention | same-file IDs, file-qualified IDs | §F and §G references | Same-file references use `F-01`; cross-runbook references use `agent-dispatch:F-01`. |

Agent processes require a clean working directory when the task may write, a readable repo when the task is review-only, provider credentials in the approved environment, and PATH entries for backend CLIs. `run_background` style dispatch must explicitly export required PATH segments because it does not inherit the interactive shell environment.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| MP | dispatch from Codex CLI | Codex CLI / GPT-5.5 | full repo write | COMPLETE |
| AG | dispatch from `antigravity_client.py` | Gemini CLI / Gemini 3.1 Pro | repo read | COMPLETE |
| DeepSeek | dispatch from `deepseek_server.py` | DeepSeek API / deepseek-v4-pro | repo read | COMPLETE |
| CC | dispatch from Claude Code wrapper | Claude Code / Opus | full repo write, 600s timeout | COMPLETE |
| Vulcan | dispatch orchestration | Anthropic API / MCP tools | gateway, LS, all repos | COMPLETE |
| XAI | RETIRED - see retired-agents appendix | Grok CLI | retired | PARTIAL — retired; see appendix for cold-storage and reactivation procedure |

XAI uses `PARTIAL` coverage here only because §D coverage status is constrained to `COMPLETE|PARTIAL|GAP|PLANNED`. The dispatch status is `DEPRECATED` in §B, and the retirement record is the retired-agents appendix plus `infra:council-comms.retired_agents.xai`.

## §E. Operate

```yaml operate
- id: E-01
  trigger: A BQ chunk requires MP to build or audit a dispatch-scoped change.
  pre_conditions: [feature_branch_exists, target_repo_clean_or_intentionally_dirty, relevant_specs_read, BQ_entity_has_body_summary]
  tool_or_endpoint: dispatch_mp_build(task=<prompt>, cwd=<repo>, branch=<branch>, timeout=300)
  argument_sourcing:
    prompt: derive from the BQ chunk ACs, required context, and verification plan
    cwd: use the target repo absolute path
    branch: use the active feature branch
    timeout: use the configured MP background timeout unless the BQ states otherwise
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(branch + prompt_digest + target_commit)
  expected_success: {shape: background task id plus committed artifact or audit verdict, verification: compare git HEAD, task transcript, and BQ build summary}
  expected_failures:
    - {signature: gateway_timeout, cause: task exceeded synchronous endpoint limit}
    - {signature: stale_task_state, cause: files committed but dispatcher status did not refresh}
  next_step_success: Run customer-perspective verification, patch the BQ entity, and request review.
  next_step_failure: Use F-01 or F-04 to choose retry, reconcile, or manual escalation.
- id: E-02
  trigger: A completed build needs independent AG review.
  pre_conditions: [commit_sha_known, review_scope_is_read_only, specs_and_diff_available, AG_server_healthy]
  tool_or_endpoint: council_request(agent=ag, mode=review, task=<read_only_prompt>, cwd=<repo>)
  argument_sourcing:
    read_only_prompt: include "READ-ONLY - DO NOT modify any files" plus exact review scope
    cwd: use the repo containing the commit under review
    evidence_refs: include spec path, commit SHA, and files changed
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash("ag" + commit_sha + review_scope)
  expected_success: {shape: verdict with findings or explicit clean approval, verification: verify any cited line numbers against the actual files}
  expected_failures:
    - {signature: progress_guard_timeout, cause: AG backend stopped making progress}
    - {signature: unsupported_line_claim, cause: model cited a fabricated or stale line reference}
  next_step_success: Attach verified verdict to the gate review record.
  next_step_failure: Use F-02, narrow the prompt, or redispatch to another voter.
- id: E-03
  trigger: A review task needs DeepSeek full-voter coverage.
  pre_conditions: [DeepSeek_server_or_API_healthy, review_scope_is_read_only, dispatch_cost_cap_available]
  tool_or_endpoint: council_request(agent=deepseek, mode=review, task=<review_prompt>, cwd=<repo>)
  argument_sourcing:
    review_prompt: derive from gate ACs and changed-file list
    mode: use review unless an approved future BQ expands scope
    cost_cap: read from infra:council-comms dispatch config
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash("deepseek" + commit_sha + review_scope)
  expected_success: {shape: strict review result with verdict and findings, verification: ensure schema validation passed and citations are real}
  expected_failures:
    - {signature: health_failure, cause: server unavailable or API token missing}
    - {signature: schema_validation_failure, cause: result did not match required review shape}
  next_step_success: Add DeepSeek verdict to the Council review set.
  next_step_failure: Repair backend health or route to AG/MP fallback per gate policy.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Gateway timeout, including 5xx from dispatch endpoints | Task too large for synchronous path, backend process hung, gateway timeout lower than backend timeout | Compare gateway response, backend logs, and task duration; check whether a background task id was created | G-01 | CONFIRMED |
| F-02 | AG progress-guard timeout | Recurring BQ-COUNCIL-AG-PROGRESS-GUARD-FIX issue, broad prompt, Gemini server stall | Inspect AG transcript for last progress marker and verify AG server health | G-02 | CONFIRMED |
| F-03 | MP mutex queue visible during multiple MP dispatches | Multiple MP dispatches serialize through the Codex CLI path; observable queue, not a correctness failure | Check task start times and mutex/queue logs before declaring failure | G-03 | CONFIRMED |
| F-04 | Dispatcher stale but files committed | MP completed local work but gateway task state or Living State did not refresh | Compare git log/status with dispatcher task record and build entity `body.summary` | G-04 | CONFIRMED |
| F-05 | MCP tool prefix lowercase silent-fail | Tool prefix used as `koskadeux:` instead of capitalized `Koskadeux:` | Check the tool name casing in the dispatched prompt or MCP call trace | G-05 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Dispatch Gateway
  root_cause: Dispatch exceeded gateway tolerance or backend stopped responding before a useful result was returned.
  repair_entry_point: koskadeux-mcp/tools/agents.py:_handle_call_*
  change_pattern: Retry once with narrower scope; if the task is substantial, redispatch through a background build surface such as dispatch_mp_build.
  rollback_procedure: Mark the timed-out dispatch failed and preserve the transcript before launching the replacement.
  integrity_check: Confirm only one successful task result is attached to the BQ record.
- id: G-02
  symptom_ref: F-02
  component_ref: AG Backend
  root_cause: AG stopped making progress before returning a review verdict.
  repair_entry_point: koskadeux-mcp/antigravity_client.py
  change_pattern: Narrow the prompt, require read-only mode, restart AG server if health is bad, and redispatch once.
  rollback_procedure: Cancel or supersede the timed-out task id in the review record.
  integrity_check: Verify the replacement verdict and any line citations against the changed files.
- id: G-03
  symptom_ref: F-03
  component_ref: MP Backend
  root_cause: MP dispatches are queued behind the Codex CLI mutex.
  repair_entry_point: koskadeux-mcp/dispatch_codex_cli.py
  change_pattern: Wait for the active MP task or schedule non-blocking work with another read-only reviewer; do not treat queueing alone as failure.
  rollback_procedure: None unless a duplicate task was dispatched; then cancel the duplicate and keep the oldest valid task.
  integrity_check: Confirm task ordering and that the accepted result corresponds to the intended prompt digest.
- id: G-04
  symptom_ref: F-04
  component_ref: Dispatch Gateway
  root_cause: Repo writes completed but dispatcher or Living State status remained stale.
  repair_entry_point: dispatch task record and build entity patch
  change_pattern: Reconcile git HEAD, committed files, dispatcher task id, and Living State build `body.summary` before promoting the gate.
  rollback_procedure: Revert only the state patch if the commit SHA does not match the reviewed artifact.
  integrity_check: Confirm branch HEAD, task transcript, and build summary name the same commit.
- id: G-05
  symptom_ref: F-05
  component_ref: MCP Tool Prefix
  root_cause: Prompt or tool call used a lowercase MCP prefix that the bridge silently ignored.
  repair_entry_point: dispatched prompt or MCP tool invocation
  change_pattern: Replace lowercase `koskadeux:` with capitalized `Koskadeux:` and rerun the affected dispatch step.
  rollback_procedure: Mark the failed lowercase attempt as superseded.
  integrity_check: Confirm the next transcript contains the expected tool call result.
```

## §H. Evolve

### §H.1 Invariants

- Dispatch mode must preserve read-only versus write-capable auth boundaries.
- Live model frontiers, dispatch participants, timeout defaults, and retired-agent state remain authoritative in `infra:council-comms`.
- Same-file §F/§G references use bare IDs; cross-runbook references use file-qualified IDs.

### §H.2 BREAKING predicates

- Removing a dispatch tool such as `council_request`, `dispatch_mp_build`, or `council_hall` is BREAKING.
- Granting write scope to AG or DeepSeek dispatch without a Council-approved role change is BREAKING.
- Reactivating XAI as an active voter is BREAKING because retired-agent state and review order change.

### §H.3 REVIEW predicates

- Adding a new dispatch tool is REVIEW.
- Changing model frontiers for MP, AG, DeepSeek, or CC is REVIEW.
- Changing default dispatch participants, review order, or Council Hall participant sets is REVIEW.
- Replacing a backend server, CLI, or API client is REVIEW.

### §H.4 SAFE predicates

- Bumping an internal timeout is SAFE when auth scope, tool surface, and fallback ownership do not change.
- Updating symptom prose or repair examples is SAFE when IDs and contracts remain stable.
- Adding a new verification command to an existing repair is SAFE.

### §H.5 Boundary definitions

#### module

The module boundary is the dispatch slice: gateway handlers, agent backend wrappers, launch environment, and dispatch task records.

#### public contract

The public contract is the operator-facing dispatch surface: task, agent, mode, cwd, context refs, synchronous result, background task id, and review verdict shape.

#### runtime dependency

A runtime dependency is any CLI, server, API, token, LaunchAgent, PATH entry, or Living State entity needed for a dispatch task to run.

#### config default

A config default is any model frontier, timeout, cost cap, participant list, or retired-agent flag read from `infra:council-comms`.

### §H.6 Adjudication

When two agents classify a dispatch change differently, use the more restrictive class. Max resolves changes that affect auth scope, money/security behavior, or active Council membership.

## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-02, §D, council:I-02]
    scenario: |
      id: E-02. trigger: A completed dispatch-gateway patch needs independent AG review before Gate 3 closes. pre_conditions: commit SHA, changed-file list, repo cwd, read-only scope, and AG server health are known. tool_or_endpoint: council_request(agent=ag, mode=review, task=<read_only_prompt>, cwd=<repo>). argument_sourcing: agent and mode from §D auth map; task from gate ACs plus "READ-ONLY - DO NOT modify any files"; cwd from the checked-out repo; evidence refs from spec, commit, and diff. idempotency: IDEMPOTENT_WITH_KEY on ag + commit_sha + review_scope. expected_success: AG returns a read-only verdict with no file writes, and cited lines are verified before attachment. expected_failures: AG progress-guard timeout, MAX_TURNS exhaustion, unsupported line claim, or unhealthy AG backend. next_step_success: attach the verified verdict to the gate record. next_step_failure: isolate with F-02 and repair with G-02 or cover the review with another voter.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd]
        argument_values:
          agent: ag
          mode: review
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-01, F-04, G-04]
    scenario: |
      id: E-01. trigger: MP must build a dispatch-scoped fix and the operator has approval to bypass stale state reconciliation until after the commit is produced. pre_conditions: feature branch, absolute cwd, task prompt, BQ entity, and intentional bypass_reconcile rationale are available. tool_or_endpoint: dispatch_mp_build(task=<prompt>, cwd=<repo>, branch=<branch>, timeout=300, bypass_reconcile=true). argument_sourcing: prompt from BQ chunk ACs; cwd from the target repo absolute path; branch from git status; bypass_reconcile from the approved dispatch note. idempotency: IDEMPOTENT_WITH_KEY on branch + prompt_digest + target_commit. expected_success: MP returns a background task id and commit SHA, then the operator reconciles git HEAD, task transcript, and BQ summary before promotion. expected_failures: gateway timeout, stale task state, mutex queue delay, or accidental review-mode token. next_step_success: run verification and request review. next_step_failure: use F-04/G-04 to reconcile before retrying or escalating.
    expected_answers:
      - kind: tool_call
        tool: dispatch_mp_build
        argument_keys: [task, cwd, branch, timeout, bypass_reconcile]
        argument_values:
          bypass_reconcile: true
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03, §D, council:I-01]
    scenario: |
      id: E-03. trigger: A cross-vote needs DeepSeek to review an open_response-style agent output for dispatch correctness. pre_conditions: DeepSeek health, dispatch_cost_cap, open_response transcript, review prompt, and repo cwd are available. tool_or_endpoint: council_request(agent=deepseek, mode=review, task=<open_response_cross_vote_prompt>, cwd=<repo>). argument_sourcing: task from the open_response transcript plus gate questions; cwd from the reviewed repo; cost cap from infra:council-comms; agent role from §D. idempotency: IDEMPOTENT_WITH_KEY on deepseek + transcript_digest + review_scope. expected_success: DeepSeek returns a schema-valid read-only verdict that agrees or identifies concrete dispatch issues. expected_failures: health failure, token failure, schema validation failure, or cost cap refusal. next_step_success: add DeepSeek verdict to the Council review set. next_step_failure: repair DeepSeek backend health or route fallback per gate policy.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd]
        argument_values:
          agent: deepseek
          mode: review
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-02, G-02, council:I-04]
    scenario: |
      id: F-02. trigger: AG review dispatch stalls with a progress-guard timeout while checking a dispatch patch. pre_conditions: AG transcript, last progress marker, original prompt, repo cwd, and AG server health are available. tool_or_endpoint: AG transcript plus council_request task record. argument_sourcing: task id from gateway response; timeout marker from transcript; prompt size from payload; health from AG server check. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as AG progress-guard timeout and cite BQ-COUNCIL-AG-PROGRESS-GUARD-FIX before any redispatch. expected_failures: treating it as a policy disagreement, losing the transcript, or rerunning the same broad prompt. next_step_success: use G-02 with a narrower read-only prompt. next_step_failure: escalate backend health and cover with MP/DeepSeek if gate timing requires.
    expected_answers:
      - kind: human_action
        verb: classify
        object: AG progress-guard timeout
        target: F-02 then G-02
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-02, G-02, council:I-05]
    scenario: |
      id: F-02. trigger: AG returns no verdict because review-mode MAX_TURNS=25 is exhausted on a broad dispatch diff. pre_conditions: AG transcript, max-turn marker, diff size, prompt body, and review_order are available. tool_or_endpoint: council_request task transcript. argument_sourcing: max-turn evidence from transcript; changed files from git diff; role expectation from infra:council-comms review_order. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as AG review-mode budget exhaustion and cite BQ-COUNCIL-AG-MAX-TURNS-REVIEW-MODE. expected_failures: accepting a partial non-verdict, widening timeout without narrowing scope, or confusing it with gateway outage. next_step_success: redispatch with G-02 using an ultra-tight diff-only prompt. next_step_failure: preserve AG non-response and use MP/DeepSeek verdicts for coverage.
    expected_answers:
      - kind: human_action
        verb: classify
        object: AG MAX_TURNS=25 review-mode exhaustion
        target: BQ-COUNCIL-AG-MAX-TURNS-REVIEW-MODE then G-02
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-01, G-01, F-05, G-05]
    scenario: |
      id: F-01. trigger: MP dispatch appears to fail silently after a cwd shorthand is used, and a later retry returns a gateway timeout after more than 30 seconds. pre_conditions: submitted prompt, cwd argument, gateway response, backend logs, and MCP tool-call trace are available. tool_or_endpoint: gateway logs plus dispatch_mp_build transcript. argument_sourcing: cwd from the failed payload; duration from gateway logs; S347 evidence from incident notes; tool prefix from transcript. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify cwd shorthand silent failure as the first defect, cite S347, and separately identify the >30s gateway timeout path as F-01 if the retry reached the backend. expected_failures: collapsing both symptoms into auth failure, or retrying without converting cwd to an absolute path. next_step_success: rerun with absolute cwd and background dispatch if the task exceeds sync tolerance. next_step_failure: escalate gateway logs with transcript evidence.
    expected_answers:
      - kind: human_action
        verb: classify
        object: MP cwd shorthand silent failure plus gateway timeout
        target: S347, F-01, and G-01
    weight: 0.08333333333333333
  - id: I-07
    type: repair
    refs: [G-02, F-02, council:I-08]
    scenario: |
      id: G-02. trigger: AG MAX_TURNS exhaustion leaves a dispatch-gateway review without a usable verdict. pre_conditions: failed task id, original diff, changed-file list, exact review questions, and transcript are preserved. tool_or_endpoint: council_request(agent=ag, mode=review, task=<ultra_tight_diff_only_prompt>, cwd=<repo>). argument_sourcing: changed files from git diff --name-only; exact questions from the failed prompt; cwd from repo; read-only instruction from §E. idempotency: IDEMPOTENT_WITH_KEY on failed_task_id + narrowed_prompt_digest. expected_success: AG returns a focused read-only verdict over only the dispatch diff. expected_failures: second timeout, broad architecture critique, or fabricated file:line claim. next_step_success: attach replacement verdict and mark the failed task superseded. next_step_failure: use MP/DeepSeek coverage and record AG non-response.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd]
        argument_values:
          agent: ag
          mode: review
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-02, E-02, council:I-09]
    scenario: |
      id: G-02. trigger: A Council review contains AG file:line claims and the operator must validate them before promoting the verdict. pre_conditions: verdict text, file path, line number, and reviewed commit checkout are available. tool_or_endpoint: nl -ba FILE | sed -n 'Np'. argument_sourcing: FILE and N from each AG citation; commit from the gate review record; repo path from cwd. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: every cited line is checked against the reviewed commit and only matching claims are accepted. expected_failures: wrong checkout, off-by-one line, fabricated line, or accepting unverified evidence. next_step_success: keep verified findings and annotate unsupported claims. next_step_failure: reject line-specific claim and request evidence-backed restatement.
    expected_answers:
      - kind: tool_call
        tool: nl -ba FILE | sed -n 'Np'
        argument_keys: [FILE, N]
    weight: 0.08333333333333333
  - id: I-09
    type: evolve
    refs: [§H, §D, council:I-10]
    scenario: |
      id: H-01. trigger: A proposal adds a new active Council agent to dispatch rotation. pre_conditions: proposed agent role, auth scope, backend surface, model frontier, review_order impact, and dispatch_patterns patch are known. tool_or_endpoint: infra:council-comms patch plus runbook update. argument_sourcing: roster and review_order from Living State; backend contract from proposed code; auth boundary from §D and §H invariants. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as BREAKING because active membership and dispatch math change. expected_failures: calling it SAFE because existing tools still accept the same arguments, or skipping retired-agent policy review. next_step_success: open Gate 1/Gate 2 Council review before activation. next_step_failure: block active dispatch until adjudicated.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H, §D, council:I-11]
    scenario: |
      id: H-02. trigger: A proposal changes the frontier model for MP while keeping the Codex CLI dispatch surface unchanged. pre_conditions: prior model, proposed model, role, timeout/cost effects, and review-quality evidence are available. tool_or_endpoint: infra:council-comms.model_policy.agent_frontier_models patch. argument_sourcing: current model policy from Living State; performance evidence from dispatch history; affected runbook rows from §D. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as REVIEW and require evidence that the new model meets or exceeds the prior dispatch role. expected_failures: treating it as docs-only because handler arguments are unchanged, or ignoring role-specific quirks. next_step_success: update model policy and runbook rows after review. next_step_failure: keep the prior frontier.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-11
    type: ambiguous
    refs: [F-01, F-03, F-05, G-01, G-03, G-05]
    scenario: |
      id: AMB-01. trigger: A dispatch failed silently and the operator cannot tell whether the cause is auth, gateway timeout, mutex contention, or malformed task/cwd. pre_conditions: submitted payload, auth context, gateway timing, queue logs, MCP tool prefix, cwd, and backend transcript are available. tool_or_endpoint: compare gateway logs, auth/token state, MP mutex queue, payload shape, and MCP trace before retrying. argument_sourcing: token source from launch env; timing from gateway logs; queue position from MP backend logs; task and cwd from request payload. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: branch the ambiguity into concrete §F symptoms: auth/token outside this runbook's provider setup, F-01 gateway timeout, F-03 mutex queue, F-05 lowercase prefix, or malformed cwd/task such as S347 shorthand. expected_failures: blind redispatch, assuming auth without timing evidence, or ignoring a queued MP task that may still finish. next_step_success: apply the matching §G repair and preserve the failed transcript. next_step_failure: escalate with payload and log excerpts.
    expected_answers:
      - kind: human_action
        verb: triage
        object: silent dispatch failure
        target: auth versus F-01/F-03/F-05 versus malformed task or cwd
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [F-04, G-04, F-01, G-01]
    scenario: |
      id: AMB-02. trigger: MP says a build completed, but the gateway task still looks stale and the branch may or may not contain the commit. pre_conditions: MP transcript, gateway task id, git log, git status, BQ build summary, and branch name are available. tool_or_endpoint: compare git HEAD, dispatcher task record, and Living State build entity. argument_sourcing: commit SHA from MP transcript and git log; task status from gateway; build summary from BQ entity; branch from git status. idempotency: READ_ONLY_DIAGNOSTIC until state reconciliation is intentionally patched. expected_success: distinguish dispatcher-stale-but-files-committed F-04 from a real gateway timeout F-01, and do not launch duplicate build work until git HEAD is checked. expected_failures: accepting stale state as failure without checking git, or patching Living State to a commit that is not on the branch. next_step_success: use G-04 to reconcile state if the commit exists, or G-01 to retry narrowly if it does not. next_step_failure: escalate with transcript, task id, and git evidence.
    expected_answers:
      - kind: human_action
        verb: distinguish
        object: stale dispatcher state versus failed MP build
        target: F-04/G-04 before F-01/G-01 retry
    weight: 0.08333333333333333
```

## §J. Lifecycle

Lifecycle metadata records the final Gate 2 conformance refresh state. Harness scoring remains pending on compact-form §I loader support tracked by `BQ-RUNBOOK-HARNESS-COMPACT-IO`.

```yaml lifecycle
last_refresh_session: S529
last_refresh_commit: 8929cbf
last_refresh_date: 2026-04-29T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - council_request dispatch contract or allowed_tools handling changes
  - agent backend auth/env wiring changes
  - active, retired, or reactivation state changes for Council agents
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-04-29T00:00:00Z
first_staleness_detected_at: null
```

Initial conformance status is `provisional` per Gate 1 §10 until C5c finalizes lifecycle telemetry after the Infisical cutover constraint is cleared.

## §K. Conformance

Final AC12 conformance fields for Gate 2 Chunk C5c.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S530 / 2026-04-29T21:30:45Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

`conformance_status: provisional` is the intended C5c value under Gate 1 §10; the runbook-lint v1.0.0 §K YAML schema rejects `conformance_status` as an additional key, so it is documented in prose until BQ-RUNBOOK-LINT-FRESHNESS-FIELDS enhances the schema for v1.1.0.

## Retired-Agents Appendix

### XAI (Grok) - RETIRED S528

XAI was Council's challenger/architect-only voter from S342-S528. It was retired due to consistent line-number fabrication on code audits, excluded from `gate3_post_build_audit` since S342 per BQ-COUNCIL-XAI-LINE-NUMBER-VERIFICATION, and DeepSeek graduation S528 superseded the architecture-only niche with broader review competence.

Cold-storage state: preserved via `xai_client.py` and `grok_cli_bridge.py` in the koskadeux-mcp repo; reactivation runbook documented at `infra:council-comms.retired_agents.xai` Living State entity.

Reactivation procedure summary: see `infra:council-comms.retired_agents.xai.reactivation_procedure` for step-by-step. Trigger conditions are a model upgrade significantly improving line-number reliability or a specific audit niche that XAI uniquely fills.
