---
runbook_id: agent-dispatch
domain: council-operations
status: ACTIVE
authoritative_for:
  - topic: agent-dispatch
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: gateway_timeout
    section: §E. Operate
  - signature: stale_task_state
    section: §E. Operate
  - signature: progress_guard_timeout
    section: §E. Operate
  - signature: unsupported_line_claim
    section: §E. Operate
  - signature: health_failure
    section: §E. Operate
  - signature: schema_validation_failure
    section: §E. Operate
  - signature: env_var_in_inherited_only
    section: §E. Operate
  - signature: default_cwd_false_positive
    section: §E. Operate
  - signature: bootout_without_plist_patch
    section: §E. Operate
  - signature: tr_truncation_false_negative
    section: §E. Operate
  - signature: mp_busy
    section: §E. Operate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-26
system_name: agent-dispatch
purpose_sentence: Council dispatch mechanics for delegating tasks to agents (MP, CC, Kimi, GLM, and the paused AG) and managing dispatch surfaces (council_request, dispatch_mp_build, council_hall).
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Stable dispatch mechanics + symptom/repair patterns. Live config (current model frontiers, dispatch participants, environment paths) is canonically tracked in infra:council-comms Living State entity.

  Cross-runbook reference convention: file-qualified IDs `<file-stem>:<id>` per parent runbooks/council.md §A. Same-file references retain bare IDs.
linter_version: 1.0.0
---

# Agent Dispatch

> **CONSOLIDATION NOTICE (Mars S1348).** This document is the result of Max's option A decision on the `agent-dispatch.md` fork. The two divergent files of that name have been merged into this one, at the catalog-indexed path `runbooks/agent-dispatch.md`, and the repo-root copy has been deleted. The unmerged branch `docs/runbook-dispatch-owner-abandoned-s1338` is folded in here (§W, §X, and the §X pointer inside §G.1) and is now superseded. Content was carried across by a content-preserving union and machine-verified for zero line loss. Nothing was rewritten, summarised, or reconciled by hand.
>
> **Where the retired root copy's sections went.** The two documents used the same section letters for different things, so some labels had to move. Everything is present.
>
> | Retired root copy | Now at | Note |
> |---|---|---|
> | Preamble duplicate-copy warning | Removed | It described the fork that this merge resolves. |
> | S612 consolidation-owner block | §A.1 | The §A–§D layout it mandates is not the §A–§K house standard used here. Unmapped: see §A.1. |
> | Council roster | §B.1 | Resolved at S1351. §B and §D record implementation coverage; §B.1 records operational roster truth. See §B.1. |
> | §C.0 | §C.0 | Unchanged, now a subsection of §C. A later status note for it sits at "§C.0 status note (S1152)" further down, in its original position. |
> | §C Architecture | §C.1 | The house §C keeps the letter. |
> | §G Repair | §G.2 | The house §G keeps the letter. |
> | §G.1 | §G.1 | Unchanged. |
> | §I Scenarios | §G.3 | The house §I is the harness-bound scenario set and must match `tests/fixtures/harness_scenarios/agent-dispatch/` exactly, so the root scenarios moved under Repair, which is what they describe. |
> | §J Plus-One Discipline | §Y | The house §J is Lifecycle. |
> | §K Conflict Adjudication Procedure | §Z | The house §K is Conformance. |
> | §L through §X | Unchanged | No collision. |
>
> **Two conflicts were recorded here at S1348 and are now RESOLVED at S1351** by the frontmatter owner against live `infra:council-comms` v62, which is the canonical source both surfaces already named. (1) The roster disagreement in §B.1 is settled: AG operational status is PAUSED and XAI is RETIRED, and the active gate voter panel is CC + Kimi + GLM. (2) The duplicate XAI retirement record is settled: the Retired-Agents Appendix is XAI's single home, the unique code-retirement evidence from the S1153 note has been folded into it, and the standalone duplicate is removed.

## §A. Header

The YAML frontmatter above defines the §A header. This runbook documents stable dispatch mechanics, operational failure patterns, and repair decisions for Council agent dispatch.


### §A.1 Consolidation ownership and revision policy (S612, folded from the retired root copy)

Carried verbatim from the retired root copy. Two things to know before reading it. The four-way §A–§D sub-section layout this block mandates is not the §A–§K structure this document actually uses, and §A–§K is what `CATALOG.json` and strict lint enforce. The mapping between the two layouts was never written down and is not invented here. The revision policy in the block stands: new failure surfaces are filed as revisions to this runbook, not as new build-queue items.

>
> **S612 Process Consolidation Owner**: this runbook is the single canonical reference for agent dispatch reliability after the S612 consolidation that collapsed ~20 process BQs into BQ-PROCESS-AGENT-DISPATCH-RELIABILITY-S612 (P0). Per MP review mandate, content is organized under four explicit sub-sections; existing body sections map into these per the survivor BQ body.absorbed_bqs subsection field. Future failure surfaces file as revisions to this runbook, NOT as new BQs.
>
> **Sub-section layout (Council R1 mandate, MP/AG/DS concurrent):**
> - **§A Dispatch routing & credentials** — dispatch routing failure modes, tool namespace prefix quirks, bq_code mandatory on Council dispatches, fold-dispatch credential primary minting, spec-authoring compliance-gate misfire.
> - **§B Builder runtime reliability** — MP/Codex wrapper repair-exhausted false-failure, MP runner workspace contamination, MP build timeout tunability, mid-round server checkpoint loss recovery, manifest emission verifier safety, Codex bridge CI workflow stability.
> - **§C Reviewer wrapper contracts** — progress-guard wrong for review mode (write-first pattern), DS spec inlining requirement, AG read-only enforcement.
> - **§D Agent-specific behaviors** — DS verdict emission + enum drift + spec mandate cleanup + diff access; AG review auto-chunking + sandbox writes + streaming generation + review depth security; MP codex CLI streaming wrapper regression.
>
> Revisions require Council R1 review-mode approval. Filed under S612.

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


### §B.1 Council roster (folded from the retired root copy)

Carried from the retired root copy and corrected at S1351 against live `infra:council-comms` v62.

**Read §B and §D as implementation coverage, and this block as operational roster truth.** They are answering different questions and the apparent disagreement was never a contradiction. §B records whether the dispatch code exists and is wired; §D records whether the adapter and auth scope are complete. Neither says whether the agent currently votes. AG carries `COMPLETE` implementation coverage in §D and is PAUSED operationally. XAI carries `DEPRECATED` dispatch status in §B because the client is cold-storage rather than deleted, and is RETIRED operationally. DeepSeek carries `COMPLETE` implementation coverage and is retired from voting. The §B and §D last-verified dates of 2026-04-29 apply to the code claims only.

`infra:council-comms` remains canonical for live roster state. Read it before dispatching.


**Gate voter panel: CC + Kimi + GLM — exactly three** (Max direct directive S1319; CORE v9.12 names CC, Kimi and GLM in the amendment gate). ACTIVATION STATUS: ACTIVE. Kimi replaced the DeepSeek seat at the S1319 cutover (koskadeux-mcp `1a7d9c6e`, deployed at `2257a367`, gateway restarted 2026-07-24). `REQUIRED_MEMBERS` and `VALID_MEMBER_IDS` in `council_gate_runner.py` are exactly {cc, kimi, glm}. The deployed gateway enforces this panel.

> HISTORICAL, superseded: the panel was CC + DeepSeek + GLM from S1213, activated at S1223 (49739a44 merged to koskadeux-mcp main as d370d65c, gateway restarted on the merged SHA, live per-voter proof CC/DeepSeek/GLM all APPROVE plus fail-closed quorum verification inside the Chunk 5 freeze; Vulcan ratification peer msg #1178). That record is retained as history and must not be read as current roster state. Consensus: 2/3 standard only after 3/3 valid participation; 3/3 unanimous for security/auth/money/production-data/customer-data; missing/failed/malformed/model-mismatched voters fail the gate closed — no builder substitution, no reduced quorum, no fallback voter.

Per-agent:
- **MP**: mandatory builder for both instances; never substituted; never votes on its own work; explicit review dispatch remains available but MP is NOT a gate voter.
- **CC**: first-class code/spec reviewer via the read-only review path (`council_request agent=cc mode=review`): plan mode, no permission bypass, Read/Glob/Grep-only tool surface, pinned dispatch_sha, model verified (`claude-opus-4-8`; mismatch discards the vote), full terminal envelope preserved through async status reads. Never a build path for BQ/development code.
- **Kimi**: gate voter, review, content-cited (no at-SHA file reading yet, tracked by BQ-KIMI-DEEPSEEK-PARITY-S1321); verify quoted code against the supplied material.
- **DeepSeek**: RETIRED from voting at S1321, superseding the S528 graduation. It can no longer cast a valid member vote on any gate. The dispatch surface `agent=deepseek` remains technically callable and `deepseek_server` may still be running, but nothing routes votes to it and new gate dispatches must not target it. HISTORICAL capabilities, retained for reactivation reference only: review plus spec-authoring, per-dispatch cost cap, raw-JSON-only prompts, ≤3 findings. No cold-storage record has been written yet; reinstatement follows the XAI pattern, a Council-approved roster change (BREAKING per §H.2) plus Max approval.
- **GLM**: gate voter, review-only, content-cited/diff-inlined (no filesystem access); verify quoted code against the diff (nested-quote garble quirk).
- **AG is PAUSED** (absent from active rosters; adapter/config and explicit review dispatch remain valid — pause, not deletion).
- **XAI is RETIRED** (Max go, S994).
- **Vulcan/Mars are never gate voters** (instance non-voter rule). Reversal condition: if Vulcan's model returns to any Anthropic model, the change is blocked until CC panel independence is re-reviewed (CORE 9.8).

Historical rounds with vulcan/ag/mp voter keys remain readable (schema legacy keys); write-path member validation rejects retired members. Canonical roster + per-agent quirks live in `infra:council-comms` (model_policy patched v58, S1222: cc=claude-opus-4-8, vulcan=gpt-5.6-sol).

This section documents the S1213 roster change and discharges the S1221 waived roster-change runbook attestations (S1221-D1..D7).


## §C. Architecture & Interactions

Dispatch is a gateway-controlled routing layer. Operators submit a task, target agent, mode, working directory, and evidence references; the gateway chooses the agent backend, applies mode constraints, and returns either a synchronous result or a background task id.

Strategic why: Why MP=primary dispatch builder: Codex CLI automation and deeper wiring-gap detection per S526 Chunk 3B precedent make MP the default builder/reviewer path. Why AG=secondary cross-vote: Gemini 3.1 Pro frontier reasoning is valuable for independent review, but line-number fabrication risk excludes AG from `gate3_post_build_audit` since S342. Why DeepSeek=graduated full voter S528: 94 dispatches, `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and statistical record floor crushed 4.7x justified full-voter dispatch. Why CC=fallback builder: it is the 300s MP Codex CLI timeout safety net and provides Opus-tier reasoning for complex multi-file builds.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Dispatch Gateway | `koskadeux-mcp/tools/agents.py:_handle_call_*` | task records, Living State build refs | MP, AG, DeepSeek, CC, Vulcan | Normalizes task args and mode boundaries before backend invocation. |
| MP/Council review middleware | `koskadeux-mcp/tools/agents.py` review dispatch handlers and `_resolve_council_review_diff` | inlined review diff, returned envelope | GLM, DeepSeek, CC | Preloads review diffs and applies provider-specific size handling before dispatch. |
| Kimi review path | Kimi review handler `cap_chars` argument and timeout budget | inlined review diff, returned envelope | Kimi | Sends scoped review material to Kimi within the configured latency budget. |
| git push guardrail, pre-push hook | repository pre-push hook and environment resolution | local ref, remote ref, push environment | git remote | Guards main pushes; remote-ref equality is authoritative for the push outcome. |
| MP Backend | `koskadeux-mcp/dispatch_codex_cli.py` | Codex config, git branch, build task record | Codex CLI / GPT-5.5 | Synchronous reviews may time out; substantial builds use `dispatch_mp_build`. |
| AG Backend | `koskadeux-mcp/ag_server.py` -> `antigravity_client.py` | AG server task record, Vertex auth env | Gemini CLI / Gemini 3.1 Pro | Read-only review prompts must state no file modification. |
| DeepSeek Backend | `koskadeux-mcp/deepseek_server.py` -> `deepseek_client.py` | DeepSeek task record, API token env | DeepSeek API / deepseek-v4-pro | Full voter; read-oriented review path with strict result validation. |
| CC Backend | `koskadeux-mcp/tools/agents.py:_handle_call_cc` | background task id, working tree | Claude Code / Opus | Fallback builder path with full repo write and longer timeout. |
| Environment Loader | launch scripts and LaunchAgents | PATH, Infisical-backed tokens, local config | Codex CLI, Gemini, DeepSeek, Claude Code | `gemini` must be on PATH; provider tokens must come from approved secret sources. |
| MCP Tool Prefix | dispatched prompt or MCP tool invocation | tool-call transcript | Koskadeux MCP bridge | Tool prefix casing must use capitalized `Koskadeux:`; lowercase can silently fail. |
| Peer Bus | `koskadeux-mcp/tools/peer_messages.py:_handle_peer_msg_send` | peer message rows, per-instance ack state | Vulcan, Mars | Coordination channel between the two peer instances. `kind` drives the ack requirement; send dedupes on `(from_instance, to_instance, kind, ref_entity)`. See F-07/G-07. |
| Cross-Runbook IDs | runbook prose convention | same-file IDs, file-qualified IDs | §F and §G references | Same-file references use `F-01`; cross-runbook references use `agent-dispatch:F-01`. |

Agent processes require a clean working directory when the task may write, a readable repo when the task is review-only, provider credentials in the approved environment, and PATH entries for backend CLIs. `run_background` style dispatch must explicitly export required PATH segments because it does not inherit the interactive shell environment.

### The background dispatch meta record

`tools/async_dispatch.py:dispatch_async` is the generic background dispatcher
for every Council agent. Call sites on `koskadeux-mcp` main `4365fcf4`, measured
in S1345 by agent literal in `tools/agents.py`: `ag` 7, `deepseek` 4, `mp` 3,
`glm` 2, `cc` 1, `kimi` 1, `kimi-shadow` 1. It is not MP-specific, and a change
to it reaches every agent.

It runs the work as a **daemon thread inside the dispatching process** and writes
one record per task to `/var/tmp/koskadeux/cc_tasks/{task_id}.meta.json`. That
record is the only thing an outside reader has. Written before this entry
existed, because two instances separately concluded there was no documentation
of what these fields mean and what may be inferred from them.

| Field | Written | What a reader may conclude | What a reader may NOT conclude |
|---|---|---|---|
| `task_id` | at dispatch | the record's identity | nothing about progress |
| `task` | at dispatch | the prompt as sent | nothing about what the agent did with it |
| `agent`, `builder` | at dispatch | which agent was addressed | not which model answered |
| `dispatched_at`, `dispatched_iso` | at dispatch | when it started, epoch seconds and local ISO | `dispatched_iso` carries no timezone suffix; do not treat it as UTC |
| `status` | `running` at dispatch, terminal by the worker | the terminal values are observed | **`running` is a dispatch-time claim, not an observation.** Nothing re-checks it |
| `owner_pid` | at dispatch, S1338 | which process owns the thread; if that process is gone the work cannot still be running | a live pid does not mean this task is progressing, only that its owner survives |
| `completed_at` | by the worker | the worker reached the end | absent does not mean still running, see below |

**The failure mode this record has, and why `running` cannot be trusted alone.**
The worker that writes the terminal state is a daemon thread in the dispatching
process. If that process dies, the thread dies with it and **no terminal state is
ever written**, so `running` becomes permanent. Observed on T-2026-000393: MP
task `b21a2ac8` read `running` at 5310s against a declared 1800s bound, with no
output file and no done marker, because the server restarted twenty-three
seconds into the build. At the time of that measurement 131 tasks were stuck
`running` with no pid and no done marker, and 130 of those had no output file at
all.

`owner_pid` (S1338, merged at `57336b5b`) is the repair: a reader can now
establish that nothing is running any more instead of taking the dispatch-time
claim on trust. Note the deliberate asymmetry in `_owner_process_gone`: it
returns False whenever the answer is **not known**, so records with no owner are
left alone rather than guessed at. Absence of knowledge is not evidence of
death.

**The bound the task was given, added in S1345.** `dispatch_async` now takes a
keyword-only `timeout_s` and always writes two further keys, `timeout_s` and
`deadline_at`. Merged to `koskadeux-mcp` main at `5a9ea9ed` under Max's accepted
option B of `decision:bounded-dispatch-path-s1340`, after two non-author Council
approvals. `deadline_at` is `dispatched_at + timeout_s`, computed after the
`extra_meta` merge so the two can never disagree.

| Field | Written | What a reader may conclude | What a reader may NOT conclude |
|---|---|---|---|
| `timeout_s` | at dispatch, S1345 | the bound the caller declared | `null` means no bound was declared, NOT that the task is unbounded in effect |
| `deadline_at` | at dispatch, S1345 | when the task said it would be done by | that anything happens at that moment |

Only the Kimi review dispatch is wired so far. Every other call site still records
`null` for both, which is honest rather than absent: no bound was declared to the
dispatcher. Wiring MP, CC, GLM and AG is separate work.

**Read those two fields for exactly what they are.** They are
declaration, not enforcement. Nothing in `async_dispatch.py` kills a runaway
thread or cancels work at the deadline. A task past its `deadline_at` is a task
that said it would be done by now, not a task that has been stopped. Nothing
reads that field and acts on it yet. `null` in
either field means no bound was declared, and it must never be filled in with a
default; a fabricated bound is worse than a recorded absence.

**Do not confuse this path with the hardened one.**
`codex_cli_bridge.dispatch_codex_cli` wraps the build in an OS-level `timeout`
and records `pid`, `timeout_s`, `codex_bin` and `model`. It has **no live
caller** and its own docstring says so; its two callers are both tests. It is
also fixed-deadline, which is the behaviour progress-aware timeouts were built
to remove after a healthy build was killed at 1800s in S1265. Reading its
richer meta and assuming the live path behaves the same way is a mistake that
has been made before.


### §C.0 AG / Gemini response-schema constraints (Vertex google-genai Schema subset)

AG runs on Gemini via the Vertex google-genai SDK, whose `Schema` type accepts only a
subset of JSON Schema. A `response_schema` (e.g. `AG_REVIEW_RESPONSE_FORMAT` in
`tools/agents.py`) must avoid keywords the SDK rejects, or EVERY AG review-mode dispatch
fails with a pydantic `ValidationError` ("Extra inputs are not permitted") *before Vertex
ever runs*. Known incompatibilities, each of which took down all AG reviews until fixed:

- **Union type arrays** like `["string","null"]` — express nullability as
  `{"type":"string","nullable":true}` instead. (S831; regression
  `tests/test_ag_review_schema_vertex.py`.)
- **`additionalProperties`** (any value, `true` or `false`) — Gemini does not support the
  keyword at all. `AGAdapter._sanitize_gemini_schema` strips it (and any key in
  `GEMINI_UNSUPPORTED_SCHEMA_KEYS`) recursively at the adapter boundary before the schema
  reaches `GenerateContentConfig`, so shared review schemas may still carry it for other
  providers. (S1132; regression `tests/test_ag_review_schema_additionalproperties_s1132.py`.)

Fix new incompatibilities at the **adapter boundary** (`council_dispatch_middleware/adapters/
ag_adapter.py`), not by hand-editing every schema — Gemini's subset is the tightest, and
cross-provider schemas must stay valid for MP/DS/GLM. This is distinct from
`RepairExhaustedError` (§O), which is a *structural output* repair failure, not an
input-schema rejection. It is also distinct from the AG review **ref-resolution** path
(`dispatch_sha`/`base`/`head` preload) — a separate fix in the same S1132 session.


### §C.1 Architecture: MP Codex CLI bridge and timeout knobs (was root copy §C)

MP build and review dispatches use the Codex CLI bridge. For
`council_request agent=mp mode=build`, `council_request agent=mp mode=review`,
and `dispatch_mp_build`, the default backend path is now
`dispatch_codex_cli_streaming`.

The streaming bridge launches Codex CLI with `subprocess.Popen`,
`start_new_session=True`, and disk-backed output capture. It monitors progress
from three signals: the final output file, the stdout transcript, and
`cwd/task_state.md` when present. Any mtime or size growth counts as progress.

`council_request agent=mp mode=open_response` now returns immediately with a
`dispatch_async` task ID. The background closure still calls `run_codex_cli`
and preserves the shaped envelope; callers poll `council_request action=check_build`.
Direct `run_codex_cli` callers retain fixed-deadline semantics for backward
compatibility.

Timeout knobs:

- `MP_PROGRESS_WINDOW_S`: no-progress window before the bridge treats a build as
  stuck. Default: `300`. (Tuning history: started at `90` for gpt-5.4. Bumped to
  `300` at S553 after gpt-5.5 dispatches false-positive-killed at the 90s mark
  during normal reasoning phases between visible stdout writes. Two consecutive
  fold dispatches failed at elapsed=172s and 405s with empty partial_output;
  direct codex test from the same trusted directory completed in 4.4s. See
  BQ-MP-CODEX-STREAMING-WRAPPER-REGRESSION-S553.)
- `MP_HARD_UPPER_BOUND_S`: absolute upper bound for a streaming dispatch.
  Default: `1200`.
- `MP_TIMEOUT_S`: legacy alias mapped to `MP_HARD_UPPER_BOUND_S` when the new
  env var is not set.


## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| MP | dispatch from Codex CLI | Codex CLI / GPT-5.5 | full repo write | COMPLETE |
| AG | dispatch from `antigravity_client.py` | Gemini CLI / Gemini 3.1 Pro | repo read | COMPLETE |
| DeepSeek | dispatch from `deepseek_server.py` | DeepSeek API / deepseek-v4-pro | repo read | COMPLETE |
| CC | dispatch from Claude Code wrapper | Claude Code / Opus | full repo write, 600s timeout | COMPLETE |
| Kimi | dispatch from the local fail-closed one-shot client | Moonshot API (OpenAI-compatible) / kimi-k3 | no tool access, review material inlined | PARTIAL — dispatch and strict-schema voting complete; at-SHA repo reading not wired (BQ-KIMI-DEEPSEEK-PARITY-S1321) |
| GLM | dispatch from `openrouter_glm_client.py` | OpenRouter / z-ai/glm-5.2 | no filesystem access, diff inlined | PARTIAL — dispatch and voting complete; file reading not wired |
| Vulcan | dispatch orchestration | Anthropic API / MCP tools | gateway, LS, all repos | COMPLETE |
| XAI | RETIRED - see retired-agents appendix | Grok CLI | retired | PARTIAL — retired; see appendix for cold-storage and reactivation procedure |

This table records IMPLEMENTATION coverage, not operational roster status. A `COMPLETE` row means the adapter and auth scope are wired, not that the agent currently votes. AG is `COMPLETE` here and PAUSED operationally; DeepSeek is `COMPLETE` here and retired from voting at S1321. The live gate voter panel is CC + Kimi + GLM and is recorded in §B.1, with `infra:council-comms` canonical.

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
  expected_success: {shape: background task id plus committed artifact or audit verdict, verification: "compare git HEAD, task transcript, and BQ build summary"}
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
- id: E-04
  trigger: After any change to the laptop-routing env-var deployment surface (KOSKADEUX_DISABLE_LAPTOP_ROUTING in com.koskadeux.council-hall.plist or related agents), the fix must be smoke-verified before claiming durable.
  pre_conditions: [plist_change_committed_to_disk, plist_passes_plutil_lint, council_hall_currently_running_or_intentionally_down]
  tool_or_endpoint: shell + launchctl bootout/bootstrap + council_request(mode=open_response, cwd=<repo>)
  argument_sourcing:
    plist_path: ~/Library/LaunchAgents/com.koskadeux.council-hall.plist (the dispatch process; NOT com.koskadeux.mcp.plist)
    domain: gui/$(id -u) where uid is the active user (typically 501 on Titan-1)
    smoke_cwd: any path under /Users/max/Projects/* (e.g. ai-market-backend) — MUST exercise _should_route_to_laptop() routing decision; DEFAULT_CWD bypasses the check and false-positives the verification
    smoke_task: "short prompt that returns hostname + env var value (verbatim shell echo); response time and absence of laptop-side error (\"node: No such file or directory\") is the diagnostic"
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(plist_sha256 + env_var_state)
  expected_success: {shape: "smoke response returns Titan-1 hostname (Koskadeux.local) + env var value \"1\" + no SSH-to-laptop error", verification: "ps -E -p <NEW_PID> shows env var in running process, AND launchctl print shows env var in canonical \"environment\" Dict (not only \"inherited environment\")"}
  expected_failures:
    - {signature: env_var_in_inherited_only, cause: bootout+bootstrap was not run; the user-domain launchctl setenv inheritance is propagating the var but the plist EnvironmentVariables Dict does not contain it; logout/reboot will lose the fix}
    - {signature: default_cwd_false_positive, cause: smoke called council_request without an explicit cwd under /Users/max/Projects/*; routing decision bypassed; verification meaningless}
    - {signature: bootout_without_plist_patch, cause: bootout+bootstrap was run on an unpatched plist; routing fix was REMOVED from running environment (worse than starting state)}
    - {signature: tr_truncation_false_negative, cause: env verification pipe `ps -E | tr ' ' '\n' | grep VAR` splits env entries containing spaces; var appears missing when actually present; use `ps -E -p PID | grep VAR` directly without tr}
  next_step_success: Patch the relevant BQ body.s<session>_durability_fix_resolution with smoke evidence (new PID, response time, hostname, env var presence in both bash wrapper and python child); record plist backup path for rollback.
  next_step_failure: Use G-06 to recover (restore plist from backup, re-validate, redo bootout+bootstrap on patched plist).
- id: E-05
  trigger: Any MP dispatch (dispatch_mp_build or council_request agent=mp) while Vulcan and Mars share the single Codex CLI lane.
  pre_conditions: [peer_bus_drained, no_peer_mp_dispatch_in_flight, lane_claim_announced_on_peer_bus]
  tool_or_endpoint: peer_msg_send(kind=status, to=<peer>, ref_entity=<build_ref>) then dispatch_mp_build(...) or council_request(agent=mp, ...)
  argument_sourcing:
    lane_claim: announce BEFORE dispatch, naming the ref_entity, the work item, and the queued items behind it (established S1303, peer-bus msgs #1524-#1526)
    dispatch_order: strictly one MP task at a time across BOTH instances; queue everything else behind the active task
    release: announce lane release on the peer bus when the active task reaches a terminal state
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: exactly one MP task active system-wide with a matching prior bus claim, verification: "check_build shows a single in-flight MP task; peer bus shows claim before dispatch timestamp"}
  expected_failures:
    - {signature: mp_busy, cause: a second MP dispatch entered the shared Codex CLI lane while a task was in flight; the harness progress guard kills a task at ~900s, losing whichever build it lands on}
  next_step_success: Dispatch the next queued lane item and announce the new claim.
  next_step_failure: check_build both task_ids to establish which survived; after the lane clears, re-dispatch the killed task; never retry into an occupied lane.
- id: E-06
  trigger: A Vulcan/Mars session opens, or is about to dispatch, merge, or close, and must synchronize with its peer before acting.
  pre_conditions: [session_registered_in_registry, peer_bus_reachable]
  tool_or_endpoint: peer_msg_inbox(instance=<self>) then peer_status(); verify boot payload claims (BQ tips, worktree SHAs, owned items) against git and Living State before relying on them
  argument_sourcing:
    drain_points: at session open, before any dispatch or merge, and before close (CORE S14); a drain marks non-ack messages consumed, so read everything returned
    ack_rule: kind=request and kind=alert require peer_msg_ack; pending unacked high-priority messages fail-close peer dispatch gates
    boot_verification: handoff and boot payload are advisory; origin branch tips and Living State are ground truth (background MP tasks can land pushes after a handoff is written)
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: empty or fully read inbox with all request/alert messages acked and boot claims verified against git/Living State, verification: "peer_msg_inbox returns no unconsumed rows; no pending_ack rows remain for self; verified SHAs match origin"}
  expected_failures:
    - {signature: stale_task_state, cause: handoff-listed work already landed on origin via a late-finishing background task; re-dispatching it duplicates a completed fold}
  next_step_success: Proceed with claim/dispatch/close; announce lane claims per E-05.
  next_step_failure: Reconcile drift in the same session (update Living State/BQ note to the verified origin state) before dispatching anything that depends on it.
```


## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Gateway timeout, including 5xx from dispatch endpoints | Task too large for synchronous path, backend process hung, gateway timeout lower than backend timeout | Compare gateway response, backend logs, and task duration; check whether a background task id was created | G-01 | CONFIRMED |
| F-02 | AG progress-guard timeout | Recurring BQ-COUNCIL-AG-PROGRESS-GUARD-FIX issue, broad prompt, Gemini server stall | Inspect AG transcript for last progress marker and verify AG server health | G-02 | CONFIRMED |
| F-03 | MP mutex queue visible during multiple MP dispatches | Multiple MP dispatches serialize through the Codex CLI path; observable queue, not a correctness failure | Check task start times and mutex/queue logs before declaring failure | G-03 | CONFIRMED |
| F-04 | Dispatcher stale but files committed | MP completed local work but gateway task state or Living State did not refresh | Compare git log/status with dispatcher task record and build entity `body.summary` | G-04 | CONFIRMED |
| F-05 | MCP tool prefix lowercase silent-fail | Tool prefix used as `koskadeux:` instead of capitalized `Koskadeux:` | Check the tool name casing in the dispatched prompt or MCP call trace | G-05 | CONFIRMED |
| F-06 | DeepSeek dispatch fails (connection refused on 127.0.0.1:8768, or the server crash-loops at startup) | Server down; launcher resolved no or invalid DEEPSEEK_API_KEY from Infisical; or the stored key is expired, malformed, or overwritten so the startup auth-probe gets HTTP 401 from api.deepseek.com | Check the listener with `lsof -nP -iTCP:8768 -sTCP:LISTEN` and tail `/var/tmp/koskadeux/deepseek_server.log` plus `_error.log`; a startup 401 means a bad stored key value, an Infisical fetch error means launcher wiring (wrong project) | G-06 | CONFIRMED |
| F-07 | Peer-bus message silently deduplicated (send returns an older row; the new body never persists) | peer_msg_send dedupes on (from_instance, to_instance, kind, ref_entity) and returns the prior row as idempotent success (T-2026-000339); observed dropping substantive coordination updates in S1321 and S1324 | Compare the returned row's created_at and body against what was just sent; a stale created_at or mismatched body means the send was deduped, not delivered | G-07 | CONFIRMED |
| F-08 | MP dispatch task record stuck in running after the Codex process exited, or a correct build failed on the one-commit post-build invariant | Handler does not bind task-record lifecycle to process lifecycle (T-2026-000351); the one-commit invariant counts commits against the caller checkout's possibly stale local HEAD rather than the actual branch point (T-2026-000360) | Check whether the expected branch or commit exists on the remote via git fetch plus git log; a pushed remote-equal artifact with a running record is the stale-record defect; a failed task with a preserved_commit_ref plus a stale pre_build_base_sha is the invariant defect | G-08 | CONFIRMED |
| F-09 | GLM or DeepSeek returns a normal, countable review verdict on a large change, and the verdict answers questions about files the reviewer never saw | The GLM/DeepSeek review path silently truncates the inlined diff at `_REVIEW_DIFF_INLINE_CAP_CHARS = 40,000` characters in `tools/agents.py::_resolve_council_review_diff`, appends a truncation marker, and returns success; the handler checks only preload success and never inspects the truncated flag, while the CC handler checks the same flag and refuses with `cc_review_diff_truncated` (T-2026-000364) | Compare the reported `prompt_chars` in the returned envelope against the real diff size from `git diff --stat` before trusting any verdict; a materially smaller prompt means the reviewer received only a fraction of the change; reconstruct the inline file order because truncation keeps the head of the concatenated diff and drops later files entirely | G-09 | CONFIRMED |
| F-10 | A Kimi review dispatch on a large diff exhausts its timeout and returns no verdict, at both 120s and 600s | The Kimi handler passes `cap_chars = 2**63-1`, so unlike GLM and DeepSeek it never truncates; it receives the entire diff and cannot complete within the latency budget; observed on 99,816 characters (T-2026-000365) | Confirm the dispatch reached the provider and timed out rather than failing at auth or transport, and compare the diff size against previous successful Kimi reviews; a timeout that scales with diff size, with no truncation marker anywhere in the envelope, is this failure | G-10 | CONFIRMED |
| F-11 | `git push` to main prints a guardrail refusal and `error: failed to push some refs`, while the same stderr block also prints a successful ref update, and the commit is in fact on the remote | The pre-push guardrail appears to evaluate `KD_ALLOW_MAIN_PUSH` in a context where it is not visible, prints a refusal, and returns non-zero while the push itself completes; the precise mechanism is not established; observed live in S1326 on koskadeux-mcp when `KD_ALLOW_MAIN_PUSH=1 git push origin main` printed the refusal and error alongside `2257a367..2961f03d main -> main` (T-2026-000367) | Never conclude a push outcome from `git push` output; run `git fetch`, then compare `git rev-parse` against the remote ref, or use `git ls-remote`, and check `git rev-list --left-right --count` against the remote branch | G-11 | CONFIRMED |


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
- id: G-06
  symptom_ref: F-06
  component_ref: DeepSeek Backend
  root_cause: DeepSeek server is down, the launcher resolved no or invalid DEEPSEEK_API_KEY from Infisical, or the stored key value is malformed or overwritten so the startup auth-probe fails with HTTP 401.
  repair_entry_point: koskadeux-mcp/scripts/launch_deepseek_server.sh -> /Users/max/bin/launch_with_infisical.sh (Infisical project bd272d48) -> DEEPSEEK_API_KEY
  change_pattern: "On a startup 401: rotate DEEPSEEK_API_KEY in the canonical Infisical project (prod), then launchctl kickstart -k gui/$(id -u)/com.koskadeux.deepseek_server. On an Infisical fetch error: point launch_with_infisical.sh at project bd272d48. No automated process writes this secret, so a junk value indicates a manual overwrite, rotate it in Infisical and re-probe."
  rollback_procedure: Old launcher backups are kept at /tmp/launch_deepseek_server.sh.bak.*; restore the prior launcher if an edit regresses.
  integrity_check: curl 127.0.0.1:8768/health returns ok, and a live council_request open_response to deepseek returns success=true with model_actual=deepseek-v4-pro.
- id: G-07
  symptom_ref: F-07
  component_ref: Peer Bus
  root_cause: peer_msg_send treats a (from, to, kind, ref_entity) tuple match as an idempotent duplicate and silently returns the old row, discarding the new body (T-2026-000339).
  repair_entry_point: koskadeux-mcp peer message send handler
  change_pattern: Until the ticketed fix ships, vary ref_entity or kind for any follow-up message on the same subject (for example suffix the ref_entity with a round or step marker), and verify the returned row echoes the body just sent before relying on delivery. Cross-artifact attribution forensics arising from dropped or misattributed bus messages are Max-gated; evidence pointers live in the session handoffs and tickets, not here.
  rollback_procedure: None; resend with a distinct ref_entity or kind.
  integrity_check: The returned row's body and created_at match the message just sent.
- id: G-08
  symptom_ref: F-08
  component_ref: MP Backend
  root_cause: The MP handler leaves task records in running after process exit and can fail correct builds by measuring the one-commit invariant against a stale local base (T-2026-000351, T-2026-000360).
  repair_entry_point: koskadeux-mcp MP dispatch handler and post-build invariant
  change_pattern: Treat the committed artifact as ground truth; verify completion with git fetch plus git log on the expected branch, never with check_build alone. Before dispatching an MP build in a repo, confirm the caller checkout's main is not materially behind origin; if a build fails on the invariant with a preserved_commit_ref, recover by landing the preserved commit on the intended branch rather than rebuilding.
  rollback_procedure: Preserved refs under refs/koskadeux-build/ retain failed-delivery artifacts; discard only after the recovery branch is pushed and verified.
  integrity_check: The remote branch head equals the preserved or reported commit SHA, and the diff scope matches the dispatch's declared file boundary.
- id: G-09
  symptom_ref: F-09
  component_ref: MP/Council review middleware
  root_cause: The GLM/DeepSeek review path silently truncates the inlined diff at `_REVIEW_DIFF_INLINE_CAP_CHARS = 40,000` in `tools/agents.py::_resolve_council_review_diff`, appends a truncation marker, and returns success; its handler checks only preload success and never inspects the truncated flag, while the CC handler refuses the same input with `cc_review_diff_truncated` (T-2026-000364).
  repair_entry_point: tools/agents.py review dispatch handlers and _resolve_council_review_diff
  change_pattern: Until the ticketed fix ships, split the review per file using the `review_paths` pathspec argument on `council_request` and state the coverage explicitly in the prompt, so each dispatch is well inside the cap and the reviewer knows what it did and did not receive. Treat any historical GLM or DeepSeek verdict on a diff over 40,000 characters as unproven rather than as an approval.
  rollback_procedure: None; verdicts are additive, so discard the uncovered verdict and re-run scoped.
  integrity_check: For every voter, `prompt_chars` is consistent with the size of the pathspec it was given, and every file in the change is covered by at least one dispatch to that voter.
- id: G-10
  symptom_ref: F-10
  component_ref: Kimi review path
  root_cause: The Kimi handler passes `cap_chars = 2**63-1`, so unlike GLM and DeepSeek it never truncates; it receives the entire diff and cannot complete within the latency budget; observed on 99,816 characters (T-2026-000365).
  repair_entry_point: the Kimi review handler cap_chars argument and its timeout budget
  change_pattern: Until the ticketed fix ships, scope Kimi reviews per file with `review_paths`, the same workaround as G-09 but for the opposite reason. For full-document design review of a specification without pasting the document, dispatch with `base` set to the fork point, `head` set to the spec commit, and `review_paths` limited to the spec file; the whole document then renders as additions. That technique kept a 29,000 character document under GLM's cap and inside Kimi's latency budget in S1325.
  rollback_procedure: None; re-dispatch scoped.
  integrity_check: A verdict is returned, and the union of the `review_paths` across dispatches covers every changed file.
- id: G-11
  symptom_ref: F-11
  component_ref: git push guardrail, pre-push hook
  root_cause: The pre-push guardrail appears to evaluate `KD_ALLOW_MAIN_PUSH` in a context where it is not visible, prints a refusal, and returns non-zero while the push itself completes; the precise mechanism is not established (T-2026-000367).
  repair_entry_point: the repository pre-push hook and its environment resolution
  change_pattern: Until the ticketed fix ships, confirm every push against the remote before acting on the result, and do not re-dispatch, re-commit, or repair on the strength of the printed error alone. The cost of believing it is redoing work that already landed, which is how a correct build was discarded in S1324.
  rollback_procedure: None.
  integrity_check: Remote head equals local head for the pushed branch and the working tree is clean.
```


### §G.1 Reviewer returns an EMPTY completion (DS / GLM) — T-2026-000232

Symptom: a review dispatch to DeepSeek or GLM fails immediately with a parse
error and `raw_response_length=0`, e.g. `DeepSeekResponseParseError: ...
(candidate_count=0, ..., raw_response_length=0)`, or a blank GLM verdict. A
trivial `mode=open_response` probe to the same provider succeeds, which proves
the provider is up and misleads you into hunting a prompt or parser defect.

Cause: DS and GLM are REASONING models. The reasoning trace and the visible
content share ONE output budget. With a small `max_tokens`, a substantive review
spends the whole budget thinking and returns zero content tokens -> empty
completion -> parse failure. This is already written down in
`config:resource-registry` -> `secrets.OPENROUTER_API_KEY.notes`. Read the
registry and TOPIC-ROUTER on the error string BEFORE reading code.

Repair:

1. Read `finish_reason` and the token telemetry now returned in the review
   envelope (`prompt_tokens`, `completion_tokens`, `reasoning_tokens`,
   `max_tokens`, `prompt_chars`, `empty_content_retries`). `finish_reason=length`
   with `reasoning_tokens` at or near `max_tokens` is the signature.
2. Budget content separately from reasoning. Review budget is 32000 tokens with a
   separate 8000-token reasoning cap (`reasoning.max_tokens` on OpenRouter), plus
   retry-once-on-empty at double budget. Landed in koskadeux-mcp `f1aa7d19`.
3. Scope the review; do not truncate it. `council_request mode=review` accepts
   `review_paths` (a git pathspec list). The inlined diff is capped at
   `_REVIEW_DIFF_INLINE_CAP_CHARS`, which since T-2026-000399 (koskadeux-mcp
   `4365fcf4`) reads `COUNCIL_REVIEW_DIFF_INLINE_CAP_CHARS` (env, default 400000)
   rather than a 40,000 literal. Material above the cap is no longer silently
   truncated on the GLM and CC paths: the dispatch is REFUSED. Split a large
   branch into two or more scoped reviews, each under the cap. The Kimi voting
   path and the DeepSeek handler do not yet refuse; see §V and T-2026-000400.

Deploy note: the review budget lives in `openrouter_glm_client.py`,
`deepseek_client.py`, `deepseek_server.py` and `tools/agents.py`. A merge to main
is NOT live until the owning process restarts. `com.koskadeux.mcp` carries the
GLM client in-process; DeepSeek runs as its own long-lived service. Bouncing only
the MCP server leaves DeepSeek on stale code and it keeps returning empty
completions. Restart BOTH.

> **READ §X FIRST.** These two commands are correct but INCOMPLETE as written.
> A bare kickstart taken while a Council panel or build is in flight destroys it
> silently, and the automatic guard that is meant to prevent that cannot see our
> in-flight work (T-2026-000398). §X carries the pre-flight, the detached
> invocation, and the verification. Do not run these two lines on their own.

```
launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp
launchctl kickstart -k gui/$(id -u)/com.koskadeux.deepseek_server
```

The MCP bounce wipes boot state; re-run `kd_session_open` + `kd_session_plan`
after. Verify with a real review dispatch against a large diff, not a probe: a
trivial probe passes even when the bug is fully present (verified live S1190 —
GLM 39.5k-char prompt, 24,790 reasoning tokens, `finish_reason=stop`, full
verdict envelope).


### §G.2 Codex CLI progress and timeout error types (was root copy §G)

`error_type=stuck_no_progress` means Codex CLI produced no observable progress
for the configured progress window. Treat this as a genuine hang or wait state:
inspect the prompt, check whether the model is waiting for impossible input, and
rescope or clarify the task before retrying. `partial_output` contains whatever
had already been written to the final output file.

Before declaring a real hang on a freshly-promoted model, verify the progress
window is wide enough to cover the model's typical reasoning duration between
stdout writes. New frontier models can be in extended thinking phases for 60s+
between visible writes; if `MP_PROGRESS_WINDOW_S` is tight, the watchdog will
kill normal builds. Ship a model promotion with a paired progress-window review.

`error_type=hard_timeout` means the task kept making progress but exceeded the
absolute budget. Treat this as an oversized chunk: split the work smaller, reduce
test scope inside the agent prompt, or deliberately raise `MP_HARD_UPPER_BOUND_S`
for a known long-running verification. `partial_output` may contain a useful
draft response, but disk state still needs customer-perspective verification.

`error_type=timeout` is a deprecated compatibility alias for old fixed-deadline
callers. New streaming paths should report `hard_timeout` instead.


### §G.3 Scenarios: MP build timeout outcomes (was root copy §I)

Scenario: MP build reports `stuck_no_progress`.

Interpretation: none of the monitored progress signals grew for
`MP_PROGRESS_WINDOW_S`. The process group was terminated, escalated to SIGKILL
after 3 seconds if needed, and reaped. Investigate prompt quality and any
external wait condition before retrying.

Scenario: MP build reports `hard_timeout`.

Interpretation: progress was still visible, but total runtime crossed
`MP_HARD_UPPER_BOUND_S`. The process group was terminated and reaped. Verify any
files written on disk, then rescope the build into smaller chunks.

Scenario: MP build runs longer than the progress window but succeeds.

Interpretation: at least one progress signal kept growing, commonly
`task_state.md` while source files were being edited before the final Codex
output file was written. This is expected and is the primary fix for the old
600-second false failure mode.


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

Lifecycle metadata records the S1265 content-conformance refresh and registered scenario-harness pass.

```yaml lifecycle
last_refresh_session: S1265
last_refresh_commit: 03cd4c0
last_refresh_date: 2026-07-17T20:00:00Z
owner_agent: vulcan
refresh_triggers:
  - council_request dispatch contract or allowed_tools handling changes
  - agent backend auth/env wiring changes
  - active, retired, or reactivation state changes for Council agents
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: 1.0
last_harness_date: 2026-07-17T20:00:00Z
first_staleness_detected_at: null
```

The dispatch scenario set is registered under `tests/fixtures/harness_scenarios/agent-dispatch/` and passed the S1265 conformant harness.


## §K. Conformance

Conformance fields for the S1265 content refresh.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1265 / 2026-07-17T20:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

The §K block records the strict-lint result; harness state is authoritative in §J.


## §L Review-Round Completeness

The terminal DeepSeek states are:

- `verdict_received`
- `classified_timeout`
- `classified_malformed`
- `classified_truncated`
- `classified_hallucinated_context`
- `classified_provider_error`
- `audited_waiver`

`classified_timeout`, `classified_malformed`, `classified_truncated`,
`classified_hallucinated_context`, and `classified_provider_error` are degraded
rounds. The primary verdict carries, the round is marked complete, and the chat
summary disposition must be
`DeepSeek result unavailable — see completeness block.`

Pending DeepSeek work is not a degraded round. It is incomplete, and no folding
or builder dispatch proceeds until a terminal state lands.

## §M Sandbox-Based Review-Mode Tool Restriction

AG review dispatches run with the review-mode sandbox enabled. The caller layer
forces `review_sandbox_strict=True` whenever `mode=review`, and the AG server
routes `shell_request action=exec` through `koskadeux_review_sandbox.sandbox_exec`
using `sandbox/review_mode_readonly.sb`. The profile is read-only for the
workspace and home tree, with only the task-scoped scratch directory under
`/private/tmp/koskadeux-review-sandbox-*` writable.

Review mode rejects caller attempts to widen the tool surface before dispatch.
The six rejected widening parameters are `bypass_sandbox`,
`legacy_subprocess`, `_skip_sandbox`, `sandbox_disabled`, `raw_exec`, and
`escape_sandbox`. A truthy value for any of them returns
`error_type=review_mode_widen_attempt` and does not start the AG task. Build-mode
dispatches are not affected by this review-only guard.

Sandbox denials and widening attempts are audit evidence. The event type is
`review_mode_sandbox_deny`; operators should inspect the payload for the
`task_id`, `bq_code`, `cwd`, and `offending_param` or sandbox error text before
deciding whether the task exposed a legitimate missing read allowance or a
blocked mutation.

Changes to `sandbox/review_mode_readonly.sb` are change-controlled. Pull
requests targeting `main` that touch the profile run
`.github/workflows/sandbox-profile-change-control.yml`, which requires an
`Approved-by: max` trailer in the PR commit messages or PR body. If the trailer
is absent, obtain Max approval and re-commit or update the PR body with the
trailer before merging.

This restriction is additive to the operator runbook requirements in §A-§K.
Follow the existing dispatch, repair, plus-one, and conflict-adjudication rules;
the sandbox only narrows what AG review mode may execute while those procedures
remain in force.

## §M.1 Agent sub-sessions must NOT run the human session lifecycle (S855)

**Incident (S855):** a `council_request agent=ag mode=open_response` dispatch caused the AG
sub-session to run the `vulcan`/`mars` session lifecycle (open/plan/close) as `instance=vulcan`
(the missing-instance default) and **clobbered the LIVE human `vulcan` registry row**, not just a
handoff entity. The live `vulcan` row flipped `S855 -> S856`, cycled to `CLOSED`, and a `decision:`
entity was written `updated_by=ag` despite an explicit `READ-ONLY` prompt. Blast radius: blocked
MP + DeepSeek council-hall dispatches and destroyed the live `vulcan` session.

**Deployed mitigation (S858, live on `origin/main`; registry migration v6 applied 2026-06-15):**
- Missing-instance opens route to a non-human `scratch` namespace instead of defaulting to `vulcan`
  (`_instance_from_args` -> `_open_scratch_session`); the scratch open returns a minimal row and
  skips the human boot payload.
- `_instance_liveness_collision` refuses an open when the target `instance` already holds a live
  `PLANNING`/`OPERATIONAL` row under a DIFFERENT `session_id` (same-id reopen allowed; `scratch` exempt).
- Registry migration v6 (`scratch_instance_namespace`) rebuilds the `sessions` PK CHECK to admit `scratch`.

**Verification signal:** after the fix, dispatching an agent during a live human session leaves the
human row's identity tuple `(instance, session_id, role, started_at, state)` unchanged; any agent-side
open lands in `scratch`. A live `scratch` row (e.g. `scratch|S865 CLOSED`) is the mitigation working,
not a fault.

**Still open:** dispatched agents can still retain `state_request` WRITE access on non-review paths.
Positive lockdown is scoped to **BQ-PEER-BUS-GATEWAY-INSTANCE-IDENTITY-S843**. S858 neutralizes the
clobber; it does not yet fully sandbox all agent writes.

## §N DeepSeek Skipped Anti-Pattern

Do not emit or accept "DeepSeek SKIPPED" as a review outcome. Skipping the +1
review hides whether the round is clean, additive, conflicting, or degraded.

The dispatch surface rejects explicit skip attempts such as `_skip_fanout`,
fanout config disablement, and direct short-circuiting of the fanout hook. The
regression coverage lives in
`tests/integration/test_skip_fanout_regression.py`.

## §O Wired Structural Dispatch Path (BQ-COUNCIL-DISPATCH-MIDDLEWARE-WIRING)

The wired middleware path fires only for structural dispatches:
`dispatch_class="structural"` in the handler args for MP, AG, or DS.
Non-structural calls stay on the legacy branch.

Structural dispatches follow this sequence:

1. `CouncilPacketBuilder` builds the packet.
2. `ModeContract` validates mode-specific dispatch requirements.
3. `ToolRegistry` resolves the concrete tool adapter.
4. `TransportRetry` invokes the adapter (`MPAdapter`, `AGAdapter`, or
   `DSAdapter`) with retry and budget enforcement.
5. `CouncilOutputValidator` validates the adapter response.
6. `SchemaRepair` repairs malformed structural output when possible.
7. `DispatchLedger.emit_dispatch_result` records the dispatch result and
   telemetry.

The legacy non-structural path is preserved verbatim and remains the rollback
target. If structural middleware must be disabled, route the affected traffic
back through the existing non-structural dispatch behavior rather than changing
the legacy implementation.

The synthetic verification harness lives at
`evidence/synthetic_dispatch_harness.py`. It produces the AC-11 verification
artifact format, including repair-exhaustion coverage. The current verification
record is `evidence/middleware-wiring-verification.md`.

Operational signals to monitor:

- Ledger emission rate: every structural dispatch should emit exactly one
  terminal dispatch result.
- Telemetry field coverage: all 17 `TelemetryPayload` fields should be
  populated, as covered by
  `test_dispatch_ledger_telemetry_payload_has_17_populated_fields`.
- Repair exhaustion handling: `RepairExhaustedError` should propagate to the
  caller and emit a failure ledger entry.

Failure modes:

- `BudgetExhaustedError`: `TransportRetry` exhausted its USD retry budget before
  receiving an acceptable adapter response.
- `RepairExhaustedError`: `SchemaRepair` exhausted repair attempts and the
  structural response remains invalid.
- Ledger emission failure: caller policy decides whether the dispatch fails open
  or closed. Preserve the adapter result when fail-open is intentional, and make
  fail-closed behavior explicit in the caller.

## §P DeepSeek Context-Access Auto-Resolution Layer

When `council_request agent=deepseek mode=review` is dispatched,
`deepseek_server.py` auto-extracts any commit SHA from the task prompt, fetches
the diff via `git show` at that SHA in the configured `repo_root`, validates
cited file paths against `git ls-tree`, and prepends a structured
`RESOLVED REPO CONTEXT` prelude before sending the prompt to the DeepSeek API.

The default `repo_root` is `/Users/max/koskadeux-mcp`, set in
`deepseek_server.py:_default_review_repo`. For non-default repositories, callers
must pass the `cwd` parameter explicitly, pointing at the repo that contains the
cited SHA.

Now structurally enforced — see §Q.

Prelude format:

```text
============================================================
RESOLVED REPO CONTEXT (auto-injected by deepseek_server context-resolution layer)
============================================================
Repo root: /Users/max/koskadeux-mcp
Resolved SHA: 5d60f9ce...
Resolved at: 2026-05-03T13:20:00Z

DIFFSTAT:
<git show {sha} --stat output>

CITED PATHS VALIDATION:
✓ tests/integration/test_ag_review_sandbox_preserves_reads.py — exists at {sha}
✓ .github/workflows/sandbox-profile-change-control.yml — exists at {sha}
⚠ src/handlers/shell.py — NOT IN TREE at {sha} (cited in prompt but does not exist)

FULL DIFF:
<git show {sha} verbatim, possibly truncated>

============================================================
END RESOLVED REPO CONTEXT
============================================================

<original task_body follows>
```

If the diff exceeds the auto-cap, the `FULL DIFF` header is marked
`(truncated)` and the diff body ends with an explicit truncation marker. The
default cap is 10K tokens, approximated as about 40K chars.

Fallback paths do not break dispatch:

- No SHA in prompt: prompt is sent unchanged.
- Invalid `repo_root`: prompt is sent unchanged and a warning is logged.
- Git command failure: prompt is sent unchanged and a warning is logged.
- Over-cap diff: diff is truncated with an explicit marker, then dispatch
  continues.

Belt-and-suspenders manual diff inlining still works for very-large diffs that
exceed the auto-cap. Use it only when the operator needs to provide a narrower
or more curated context than the automatic `git show` prelude can carry.

Design references:

- `specs/bq-council-deepseek-context-access-fix-gate1.md`
- `specs/bq-council-deepseek-context-access-fix-gate2.md`

## §Q — Build Dispatch CI-Workflow Verification Gate

Structural MP build dispatches run the CI-workflow verification gate after MP
reports build success and before the success envelope returns to the caller.
The gate executes the paths listed in `ci_verification.py:CI_WORKFLOW_TEST_PATHS`.
On pass, the build envelope includes a `ci_workflow_check` block. On persistent
test failure, the dispatch wrapper reverts `HEAD`, pushes the revert to `main`,
and returns a failure envelope instead of allowing the regression to stand.

Error envelopes:

- `ci_regression`: the configured CI-workflow tests failed after retry and the
  automatic revert push succeeded. Treat the build commit as rejected; inspect
  `failing_tests`, `pytest_output_truncated`, and `revert_commit_sha`, then
  dispatch a corrected follow-up chunk.
- `ci_regression_revert_push_failed`: the tests failed and the local revert was
  attempted, but pushing the revert failed after retry. Treat this as urgent
  operator recovery: inspect the broken commit SHA and worktree state in the
  envelope, restore `main` manually, then re-run the CI-workflow tests.
- `ci_check_unavailable`: required gate infrastructure such as `pytest` or
  `git` is missing. Fix the tool availability problem on the dispatch host and
  retry the build; do not bypass unless Max explicitly authorizes emergency
  operation.
- `ci_check_timeout`: the gate subprocess exceeded its timeout. Inspect whether
  the test run is hung or simply too slow, correct the underlying issue or
  adjust the chunk size, then retry.

To extend coverage, edit only the `CI_WORKFLOW_TEST_PATHS` constant in
`ci_verification.py` and add the new test path as a repository-relative string.
Keep the list aligned with the CI workflow's dispatch-critical coverage and
update the corresponding unit assertion in `tests/unit/test_ci_verification.py`
in the same patch.

The skip flag is an emergency-only operator pattern. Use `skip_flag=True`
through the dispatch surface only under explicit Max authorization, comparable
to break-glass operation. A skipped gate must produce an audited
`ci_check_bypass` event with the reason, and the returned envelope must show
`ci_workflow_check.status == "skipped"`.

Design references:

- `specs/bq-council-build-verification-full-ci-suite-gate1.md`
- `specs/bq-council-build-verification-full-ci-suite-gate2.md`

## R

§R — Pre-Push Gate Composition. Structural MP build dispatches use pre-push gate composition. The shipped row is
`pre-push gate composition`: status `shipped`, implementation
`tools/agents.py:_run_pre_push_gate_composition`, call site
`_handle_call_mp_build`.

The wrapper owns the full sequence:

1. Pre-build invariants: the working tree must be clean and the current branch
   must not be ahead of its upstream.
2. Builder execution: MP creates exactly one local commit and returns
   `claimed_commit_sha`; MP does not push.
3. Post-build invariants: the branch must contain exactly one new commit and
   `claimed_commit_sha` must match `HEAD`.
4. Pre-push gates: run `ci_workflow_check`, parse the single
   `builder-output-manifest` block, run `builder_output_check`, then push only
   if both gates pass.

The discard primitive is `git reset --hard <pre_build_base_sha>`. It is used for
post-build invariant failures, CI failures, missing or malformed manifest output,
and builder-output claim mismatches. A push failure is the exception: if all
pre-push gates passed but `git push` fails, the verified local commit is
preserved and the envelope returns `error_type=push_failed` with manual recovery
guidance.

Manifest emission is part of the MP build prompt template for structural builds.
The prompt is selected by `verifier_subtype` (`general`, `code_fold`,
`runbook_revision`, or `spec_authoring`) and requires exactly one fenced
`builder-output-manifest` JSON block with `manifest_version: 1`. Supported
claim kinds are `surface_exists`, `code_fold`, and `runbook_row_shipped`;
`code_fold` has a soft cap of 3 claims and reports a warning rather than
failing solely for cap excess.

Emergency bypasses are explicit and audited. `skip_ci_check` bypasses only the
CI-workflow gate. `skip_output_verification` or `KD_SKIP_OUTPUT_VERIFICATION`
bypasses only builder-output verification; the manifest parser still records a
parsed manifest when present, and the returned envelope reports
`builder_output_check.status == "skipped"`.

## §S Review Verdict Persistence

Review-mode primary Council dispatches for `agent=ag`, `agent=mp`, and
`agent=deepseek` persist returned verdict text in the handler after the provider
result is available. The handler writes to the target branch, not from inside the
review sandbox.

Dispatch contract:

- Callers should pass `verdict_target_branch` on review-mode dispatches. During
  the migration phase `VERDICT_TARGET_BRANCH_REQUIRED=False`, missing branches
  emit `write_outcome=missing_verdict_target_branch_warning` and return the
  provider envelope unchanged for manual fallback.
- The post-migration flip is operator-controlled by changing
  `VERDICT_TARGET_BRANCH_REQUIRED=True` in `tools/agents.py`. After the flip,
  review-mode primary dispatches without `verdict_target_branch` fail at handler
  entry with `missing_verdict_target_branch`.
- Verdict filenames are `specs/<bq_slug>-r<round>-<reviewer>.md`. Reviewer keys
  are `ag`, `mp`, and `ds`; `agent=deepseek` maps to `ds`. If round is absent,
  the handler writes under `r1`. (GLM joined the standard roster S994; the handler maps `agent=glm` to key `glm` and persists verdicts via the same path — verified S994 in tools/agents.py.)

Failure modes:

- `missing_verdict`: provider envelope has no usable `response`, `result_text`,
  `response_text`, or `DispatchResult.response_text`. No file is written.
- `disk_write_failed`: local staging or commit failed. Use the returned envelope
  text and manually commit the verdict if needed.
- `branch_missing`: `origin/<verdict_target_branch>` could not be fetched or
  resolved. Repair or create the branch, then retry the dispatch or manually
  commit the verdict.
- `push_rejected`: push failed, timed out, or exhausted force-with-lease retry.
  Envelope includes `push_outcome=rejected_after_retries` and
  `persistence_outcome=push_rejected`.
- `lock_timeout`: same-branch persistence lock could not be acquired inside the
  wall-time budget. Envelope includes `persistence_outcome=lock_timeout`.

Each path emits `council_verdict_persist` with `write_outcome`,
`verdict_target_branch`, `write_path`, `verdict_sha`, `wall_time_ms`,
`lock_wait_ms`, `retries`, `wall_time_exceeded`, `lock_timeout`, `session_id`,
and `correlation_id`. The verdict trailer is HTML comments:
`__verdict_sha__`, `__dispatch_id__`, and `__written_at__`.

Migration:

This git-file sink is a bridge to Living State. When the S621 build-entity
Council-round schema is locked, file a follow-on BQ to move `_persist_verdict`
from `specs/*-r*-*.md` commits to the build entity's structured
`council.rounds[].reviewers.*` fields.

Operator troubleshooting:

If the verdict file is missing after a review dispatch, inspect the returned
envelope for `persistence_outcome` and `push_outcome`, then check the matching
`council_verdict_persist` event. For `missing_verdict` or
`disk_write_failed`, commit the envelope's verdict text manually. For
`branch_missing`, repair the target branch and retry. For `push_rejected` or
`lock_timeout`, retry after confirming no competing writer is advancing the
same branch.

## §T — MP Spec-File Dispatch Standard (canonical, S827)

Canonical pattern for any MP dispatch grounded in a spec (Max directive S826, probe-verified S827; Living State: `infra:council-comms.mp_spec_file_dispatch_standard`).

Reference the COMMITTED spec path at a pinned commit SHA — never a bare path, never long specs pasted inline (Codex /goal objectives cap at 4,000 chars; real specs do not fit). Required thin-contract wrapper elements:

1. Read instruction: "use `git show <SHA>:<path>` — do not trust the working tree".
2. Scope guards: READ-ONLY for reviews, plus the S452 prefix (DO NOT git add/commit/push/modify) — MP treats READ-ONLY as advisory.
3. Output contract: numbered parts, §-citation requirement against the spec's own section numbers.
4. Untruncated-read proof: demand the exact first and last line of the file verbatim.
5. Explicit stop condition.

/goal prefix is optional: the goals feature is stable+enabled on Titan-1 Codex 0.139.0 and /goal-prefixed prompts are accepted via `codex exec`, but goal-LOOP engagement (multi-turn autonomy to a stop condition) in non-interactive exec is UNVERIFIED on long builds. Do not rely on loop autonomy until a long-build dispatch demonstrates it; the load-bearing, proven element is path@SHA + wrapper.

Evidence: S827 probe — MP read specs/BQ-ALLAI-ACTIVATION-S826-GATE1.md @ 4e9cfec6 via git show, exact first+last lines verbatim, accurate §-citations, zero file modifications, 66s.

## §U — Post-build wrapper failure with a delivered commit (RepairExhaustedError recovery, S1147)

**Symptom:** a structural MP build dispatch returns `RepairExhaustedError: schema repair exhausted` (builder-output-manifest could not be repaired into a valid structural response), but `git log` in the build cwd shows MP's commit landed and `git status` is clean. Observed S1147 on BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146 C1 (task d8f1c473, commit c710ed75). This is the §B "MP delivered even though the envelope says failed" family (S451 quirk), surfacing on the §O structural path at the output-validation stage — the failure is in manifest parsing/repair, NOT in the build.

**Procedure (do NOT redispatch a rebuild):**
1. Confirm delivery: `git log --oneline -3`, `git status --short`, and inspect the commit diff against the chunk's spec scope.
2. Complete the wrapper's pre-push gates manually: run the chunk's new tests plus `ci_verification.py:CI_WORKFLOW_TEST_PATHS` locally; all green or stop.
3. Run the chunk's Gate 3 cross-review with builder excluded (MP built it → DS + GLM review).
4. On pass, push as a deliberate instance merge: `KD_ALLOW_MAIN_PUSH=1 git push origin main` (fast-forward only).
5. Record the workaround: patch the BQ entity (chunk verdicts + `wrapper_incident`) and emit a `decision` event.

**Escalation:** if this recurs, file a BQ against the SchemaRepair/manifest-parser stage of the §O middleware rather than repeating manual recovery.

**Related:** before ANY MP dispatch pinned to a SHA that was committed via the GitHub API, `git fetch origin main` in the target repo first — the local clone will not have the object and the dispatch fails with `object/path is not available locally` (observed twice S1147; see §T and the TOPIC-ROUTER symptom table).

### §U addenda (S1147, activation session)

- The RepairExhaustedError-with-delivered-commit pattern hit **4/4 structural MP builds** in S1147. §U recovery worked every time with zero rebuilds. A BQ against the SchemaRepair/manifest-parser stage is now warranted (see BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146 follow-ups).
- **Check for shadowing after every MP session.py build:** one S1147 chunk added a module-level helper duplicating a pre-existing function name (`_read_state_entity`), silently shadowing the original for all earlier call sites. Grep `grep -n "def <name>(" <file>` for duplicate defs before review; the introduced-failure baseline diff (worktree at parent commit, identical pytest selection, `comm -13`) catches the symptom.
- **GLM inline reviews: inline VERBATIM code for anything GLM must judge.** An orchestrator-condensed summary produced two false REQUEST_CHANGES findings in S1147 (an "undefined variable" and a "missing guard" that existed only in the summary). Condense context, never the code under audit.
- **DeepSeek review degradation (empty responses, raw_response_length 0):** after 2 strikes on the same subtask, substitute AG as cross-reviewer (tight DO-ONLY checklist prompt, verify its citations by grep) rather than stalling the gate.

### §U resolution note (S1150)

The manual-recovery loop in §U is now largely obsolete: the pipeline auto-recovers. Two S1150 fixes landed (koskadeux-mcp `745ba12d`, `25006e5e`) closing tickets T-2026-000193 and T-2026-000177: (1) structural build dispatches no longer die on a variable-scope error introduced by the S1147 wrapper fix — root-cause any repeat of "Gateway Error: upstream service unavailable" on build dispatch by running the handler in-process to get the real traceback (the gateway swallows it; the in-process repro is the decisive diagnostic, see T-193 for the recipe); (2) the pre-push gate no longer discards a green commit when the builder omits the manifest fence — it synthesizes a schema-valid manifest from the git diff, flags `requires_manual_diff_review`, and proceeds through CI + claim verification. Expected terminal state for a structural build on main is now `error_type=push_failed` with ALL gates passed and `operator_recovery_guidance` naming the verified commit — the guardrail refusing an automated main push is by design; the instance reviews (builder ≠ reviewer) and performs the `KD_ALLOW_MAIN_PUSH=1` merge. Keep §U's steps only for the case where gates genuinely did not run.

### §C.0 status note (S1152)

The §C.0 "sanitize at the adapter" fix is now IMPLEMENTED: `antigravity_client._gemini_sanitize_schema` (koskadeux-mcp `fc8a0d4a`) recursively strips `additionalProperties`/`$schema`/`unevaluatedProperties` from every tool inputSchema before building Gemini FunctionDeclarations. Trigger: the S1150 close gate added `additionalProperties` to `kd_session_close.runbook_exit`, which killed ALL AG dispatches at tool-fetch time (observed S1152 hall voter dispatch). If AG ever fails again with `FunctionDeclaration ... extra_forbidden`, a NEW rejected key has appeared — add it to the `_REJECTED` tuple in the sanitizer rather than editing tool schemas.

## Gate-change consultation for shipped mandates (S1164, discharges S1164-D4)
Loosening or altering ANY mechanism installed under a unanimous Council mandate (customer-data, security, auth, payments) requires a fresh design vote at the SAME bar (unanimous) BEFORE build — even when Max directs the change; his directive settles the business decision, the vote hardens the implementation invariants. Procedure: (1) write a compact spec stating context, the exact loosening, and the invariants that stay hard; (2) dispatch the standing voters (check infra:council-comms for roster; S1164 used MP+AG+DeepSeek) in open_response with verdict APPROVE/APPROVE_WITH_MANDATES/REJECT, max 3 findings; (3) fold ALL mandates into the build prompt as BINDING; (4) normal build → Gate-3 (reviewer≠builder, inline diffs for DS/GLM per T-2026-000206) → merge → Gate-4 live verify; (5) record the decision as a state event naming the vote and mandates. Precedent: S1164 HF metadata-only-by-default (unanimous; hard line kept: data rows always require seller-approved disclosure snapshot).

## §V — CC gate-review dispatch mechanics (S1231)

CC (`council_request agent=cc mode=review`) is a read-only gate voter with filesystem access, but its dispatch contract is stricter than DS/GLM:

- **Pinned worktree required.** `cwd` must be a checkout whose HEAD equals `dispatch_sha`, or the dispatch fails `checkout_not_pinned` (`cc_review_target_invalid`). Never re-point the live server checkout (`/Users/max/koskadeux-mcp`); create a detached worktree: `git worktree add --detach <path> <sha>` and pass that as `cwd`.
- **Exactly one pinned ref.** Supplying conflicting `dispatch_sha`/`head`/`sha` aliases fails `dispatch_sha_alias_conflict`; supplying none fails `dispatch_sha_required`.
- **Inline diff cap, CC-only.** The CC preload inlines the pinned diff and HARD-FAILS loud (`cc_review_diff_truncated`) if it exceeds `CC_REVIEW_DIFF_INLINE_CAP_CHARS` (env, default 120000, read at process start — a change needs a handler restart). Shipped T-2026-000263 @ koskadeux-mcp 83c9189d after a 45.4k single-file Gate 2 spec could not pass the shared 40k cap and `review_paths` cannot narrow a single file.
- **Truncation is fail-closed and detection is authoritative (T-2026-000399, koskadeux-mcp `4365fcf4`, was an open gap until 2026-07-26).** The shared preloader cap is now `COUNCIL_REVIEW_DIFF_INLINE_CAP_CHARS` (env, default 400000, read at process start), not the old 40k literal, and both the GLM path and the CC path refuse rather than dispatch when material is truncated (`review_diff_truncated` / `cc_review_diff_truncated`). Detection trusts the resolver's `truncated` boolean and falls back only to a LINE-ANCHORED header match; the previous substring test for `FULL DIFF (truncated):` matched its own sentinel inside any diff touching this code, which made CC structurally unable to review the review subsystem for three weeks. Do not reintroduce a substring test. **Still open, tracked as T-2026-000400:** the Kimi voting path resolves with `cap_chars=2**63-1`, so `truncated` is permanently False there and the refusal can never fire; `_handle_call_deepseek` (`tools/agents.py:1780`) resolves with the default cap and has no refusal guard at all. Until those close, a Kimi or DeepSeek verdict on very large material still needs the manual size check: `git show <sha> -- <path> | wc -c`.
- **Model verification.** A `model_matched: false` CC result discards the vote (CORE §5); redispatch.
- **Output-schema contract (S1248).** The CC review path injects NO output schema into the prompt; the server validates the final message against `council_output_schemas.TARGET_VERDICT_SCHEMA` and rejects anything else as `cc_review_malformed_verdict`. The dispatcher MUST state the contract in the task, verbatim: the ENTIRE final message is one raw JSON object (first char `{`, no prose/fences outside it) with ALL FOUR keys required and `additionalProperties: false` everywhere: `verdict` one of `APPROVE` | `APPROVED_WITH_MANDATES` | `REJECT` (there is NO `APPROVE_WITH_NITS`/`REVISE` in this validator — non-blocking findings ride in `findings` under verdict `APPROVE`); `mandates` `[]` or items with exactly `id` (`^M[0-9]+$`), `description`, `severity` (`blocking`|`major`|`minor`), `target_file`, `target_location`; `findings` items with required `severity` (`blocking`|`major`|`minor`), `title`, `description` and optional `target_file`/`target_location` — NO `id` key on findings; `summary` non-empty. Discovered the hard way in S1248: four dispatches burned guessing the schema one validation error at a time. Defect ticket: schema should be auto-injected by the CC review path like MP's response_format.

## §W — A dispatched build reports "running" for ever (abandoned worker, S1338, discharges S1338-D1)

**Symptom:** `council_request(action=check_build, task_id=...)` returns
`status: running` with an `elapsed_s` far past the declared bound, and the task
never reaches a terminal state. No branch appears on the remote. Observed S1334
on MP task `b21a2ac8`: 5310s against a declared 1800s, no artifact, no
terminal state, and the record still says running days later.

**Do not diagnose this from the task record. Diagnose it from the process
table.** The task record is the thing that is lying; reading it harder does not
help. Three prior sessions read it and concluded, wrongly, that no timeout
enforcement existed.

### Mechanism

Builds dispatched through `tools/async_dispatch.dispatch_async` run the worker
as a **daemon thread inside the dispatching process** (the MCP server), and the
meta file at `/var/tmp/koskadeux/cc_tasks/{task_id}.meta.json` is written once,
at dispatch, saying `"status": "running"`. **Only that thread will ever update
it.** If the server restarts, the thread dies with it and nothing is left alive
that could ever write a terminal state.

Two guards exist for this and neither could fire:

1. `claude_code_client.check_claude_code` contains a timeout reaper. It is
   guarded by `if pid:` and `dispatch_async` recorded no pid. Measured S1338:
   **1407 of 1409 task metas carried no pid**, so the reaper was unreachable on
   the live path. Re-derive that census rather than trusting the number:

   ```
   python3 -c "
   import glob, json
   m = glob.glob('/var/tmp/koskadeux/cc_tasks/*.meta.json'); n = 0
   for f in m:
       try:
           if json.load(open(f)).get('pid') is None: n += 1
       except Exception: n += 1
   print(n, 'of', len(m), 'metas carry no pid')"
   ```
2. The S320 crash guard for thread tasks starts its 120s grace timer from the
   **mtime of the output file**. A worker that dies before producing output
   never writes one, so the timer never starts. Measured S1338: **131 tasks
   stuck running with no pid and no done marker, 130 of them with no output
   file.** The single case the guard was written for is the single case it
   cannot detect.

**Vocabulary, because this section uses both.** `check_build` is
`claude_code_client.check_claude_code`; `list_builds` is
`claude_code_client.list_claude_code_tasks`. Symptoms below are written in
MCP-action terms and repairs in function terms; they are the same two
instruments.

**The instruments also disagreed.** `check_build` returned `running` for a
record that `list_builds` reported as `finished`. If two tools give opposite
answers about one task, neither is evidence; go to the process table.

### Procedure

1. `ls -la /var/tmp/koskadeux/cc_tasks/{task_id}*`. A lone `.meta.json` with no
   `.json` and no `.done` means the worker produced nothing at all.
2. `python3 -c "import json;print(json.load(open('/var/tmp/koskadeux/cc_tasks/{task_id}.meta.json'))['dispatched_iso'])"`
3. **Ask launchd which process it owns, not the process table.**
   `launchctl list com.koskadeux.mcp | grep '"PID"'`, then
   `ps -eo pid,lstart -p <that pid>`. **If the server start time is later than
   the dispatch time, the worker was killed by the restart.** That is the whole
   diagnosis. Twenty-three seconds separated the two in the S1334 case.

   **Do not use `pgrep -f koskadeux_server.py` and do not use a bare
   `ps | grep` without `grep -v grep`.** Both match the shell and python
   children of the command doing the checking, because the pattern sits in
   their own argv. S1340 recorded pid 49834 as the server on exactly this
   mistake; the real pid was 49692. Two phantom pids appeared and vanished
   across consecutive samples and very nearly got reported as a crash loop.
   For a launchd-owned job, launchd is the authority.

   **Compare like with like.** `ps lstart` prints LOCAL time; git commit
   timestamps and Living State are UTC. S1340 compared a local start against a
   UTC commit time and reported a 58-second race that was actually a gap of
   nearly two hours. The conclusion survived, the number did not, and a
   58-second window and a two-hour window argue for completely different
   fixes.
4. Confirm nothing landed: `git ls-remote origin 'refs/heads/<branch>'` against
   the remote, never a local branch and never the task record.
5. **Branch on step 3 before you do anything.**

   **If the server start time is LATER than the dispatch time:** the worker was
   killed by the restart. The dispatch is dead. Re-dispatch; there is nothing to
   recover unless `task_state.md` exists in the build cwd.

   **If the server start time is EARLIER than the dispatch time: STOP. The
   worker may still be alive.** Nothing in this section licenses re-dispatch in
   that case, and re-dispatching puts two workers on one task, both writing the
   same branch. Remember this same section says declared timeouts are ADVISORY,
   not enforced, and the streaming path exists precisely so that a long healthy
   build is not killed for being slow: elapsed time past the declared bound is
   therefore not evidence of death. Establish liveness positively instead —
   signal 1 in §X for an MP build, or poll `check_build` and watch for the
   output file to grow — and if you cannot establish it either way, say so and
   escalate rather than guessing. Absence of a terminal record is the symptom
   this whole section exists to explain; it is not proof the worker is gone.

### Repair, and what is still open

**MERGED to main at `621dbedc` (S1340).** Gate 3 unanimous: R1 CC APPROVE,
GLM APPROVE, Kimi APPROVED_WITH_MANDATES; R2 after folding Kimi's M1, all three
APPROVE with zero mandates. Regression proved by measurement, not assertion:
identical selector at base and merged head, failure NAMES diffed, 21 and 21,
sets identical. What landed:
`dispatch_async` records `owner_pid`, `check_claude_code` returns a terminal
`failed` / `worker_abandoned` verdict when that process is gone, and
`list_claude_code_tasks` stops reporting the same record as `finished`.
`_owner_process_gone` returns False whenever the answer is not known, so records
carrying no owner are left alone rather than guessed at.

**All three R1 mandates, and what actually happened to each — so a later reader
cannot mistake deferral for discharge.**

- **M2 (consumer audit), DISCHARGED, no code change.** Read-only audit at
  `621dbedc` found the only two consumers of `list_claude_code_tasks` —
  `tools/agent_request.py:98` and `_handle_list_builds` in `tools/agents.py:6255`
  — are pure pass-through: both serialise the result with `json.dumps` and
  neither branches on the status string. The risk M2 named, a consumer bucketing
  an unknown status as non-terminal, does not exist. The vocabulary split is
  real and remains: `list_claude_code_tasks` reports `abandoned` while
  `check_claude_code` reports `failed` with `error_type: worker_abandoned` for
  the same record. It is downgraded to documentation, and this paragraph is that
  documentation. Revisit only if a consumer ever starts branching on the string.
- **M3 (reconcile the ~130 pid-less orphans), STILL OWED, NOT DISCHARGED.** The
  change prevents recurrence and heals nothing retroactively. Those records will
  report `running` from `check_claude_code` and `finished` from
  `list_claude_code_tasks` until a one-time reconciliation lands. Tracked as
  T-2026-000393 residual B.
- **M1 (non-positive owner_pid), FOLDED BEFORE MERGE:** `_owner_process_gone` now rejects a
non-positive `owner_pid` **before** probing. A negative value reached
`os.kill(-n, 0)`, which probes a process GROUP rather than a process, so a
`ProcessLookupError` there produced a terminal verdict from malformed input —
a hole in the one property the change exists to guarantee.

**T-2026-000393 residual A is DECIDED (S1340, Max approved).** The earlier
direction recorded here — wire the live path onto the hardened
`codex_cli_bridge.dispatch_codex_cli` — was **REJECTED** on evidence. Do not
pursue it:

- `dispatch_async` is **agent-generic** and serves AG, XAI and MP, while
  `dispatch_codex_cli` is codex-only. Routing onto it would fix MP builds and
  leave every other agent dispatch with the identical defect.
- It is **fixed-deadline**, which is precisely what killed anon-visitor Chunk 1
  on `hard_timeout` at 1800s in S1265. The progress-aware streaming path exists
  to remove that failure.
- It has **no live caller**, so promoting it to carry every build is a large
  unmeasured bet.

The accepted direction instead:

- **B (approved, next).** Persist the declared `timeout_s` and a computed
  `deadline_at` in the meta at dispatch. `owner_pid` already arrives with
  `621dbedc`. **This is declaration, not enforcement** — nothing kills a
  runaway thread. It makes the record truthful; it does not make the bound
  binding. State it that way rather than letting it read as a timeout fix.
- **C (highest leverage, after B).** Surface the **real codex child pid** onto
  the live meta. The correction that unlocked this: the live path *does* have a
  genuine OS child process — `dispatch_codex_cli_streaming` spawns `codex exec`
  — and we simply throw its identity away instead of recording it. Recording it
  repairs the reaper, the S320 guard and the reload guard **without changing a
  single one of their predicates**.

Until B lands, treat any declared build timeout as advisory rather than
enforced.

**Related:** T-2026-000393 (residuals, including ~130 legacy records that will
report running for ever and are deliberately not guessed at), and §B on the
"MP delivered even though the envelope says failed" family, which is the
opposite error — that one under-reports success, this one under-reports death.

## §X — Restarting the MCP server (do not do it by hand first, S1340)

**There IS a sanctioned restart procedure and it is automatic.** Both instances
searched this router in S1339/S1340, found nothing, told each other no procedure
existed, and proposed a manual restart to Max. The procedure was not in the
index; it was in launchd and in the repo, running once a minute, writing a log
that named the exact two commits under discussion. **Read the machine before
concluding a mechanism is absent.**

### The mechanism

`com.koskadeux.mcp-reloader` (a user LaunchAgent, `StartInterval` 60) runs
`scripts/reload_when_idle.sh` in `koskadeux-mcp`. Each tick it fast-forwards to
`origin/main`, then **refuses** to bounce unless the tree is clean, no session is
live or unverifiable, and no build child is in flight. On success it kickstarts
`com.koskadeux.mcp` and records the deployed commit in
`/var/tmp/koskadeux/deployed_sha`.

**Merged is not live.** Code on main is not running until that bounce happens.
To check whether a deploy is outstanding:

```
cat /var/tmp/koskadeux/deployed_sha            # what is running
git -C /Users/max/koskadeux-mcp rev-parse origin/main   # what is merged
tail -5 /tmp/koskadeux_mcp_reload.log          # why it is deferring
```

A repeating `deferring` line naming two commits is the reloader working
correctly, not a fault. It is waiting for both instances to close.

### THE HAZARD — the idle guard cannot see our builds (T-2026-000398)

Step 4b of the script decides whether a build is in flight by reading a `pid`
from each task meta, and treats a meta with **no pid** as *not blocking*, on the
stated reasoning that a pid-less record is an HTTP thread task. **That reasoning
is inverted.** A thread task is the one kind of work a bounce is guaranteed to
destroy, because the thread lives inside the server process and dies with it,
and the only writer of its terminal state was that thread.

`dispatch_async` records no pid, and **1407 of 1409 metas carry none**. Measured
live in S1340: the guard returned `RUNNING_BUILDS=0` while a real build was
running. Had the restart gone ahead, it would have destroyed that build silently
and reproduced the very incident the S1338 work was fixing.

**Therefore, until T-2026-000398 lands: never close a session with a Council
panel or a build in flight, and never restart by hand without checking
yourself.**

**Do not simply list every meta without a done marker.** There are ~134 legacy
records in that state on this machine (S1340, measured) and they will never
acquire one, so a naive loop prints 134 lines of noise and tells you nothing.
Two signals, in this order:

```
# 1. AUTHORITATIVE for MP builds: is a builder subprocess actually alive?
#    Build the pattern from two pieces so THIS shell's own argv never contains
#    the literal phrase. Immune to self-match by construction, which a bare
#    pgrep is not (see the note below, and §W step 3).
PAT='codex'' exec'
pgrep -fl "$PAT"

# 2. FRESH thread tasks: no done marker AND touched in the last 6 hours.
#    6h matches BUILD_STALE_SECONDS in reload_when_idle.sh; anything older is
#    a legacy orphan, not live work.
find /var/tmp/koskadeux/cc_tasks -name '*.meta.json' -mmin -360 | while read m; do
  t=$(basename "$m" .meta.json)
  [ -e "/var/tmp/koskadeux/cc_tasks/$t.done" ] || echo "IN FLIGHT (or died today): $t"
done
```

**On the split pattern, stated precisely rather than dramatically.** §W tells
you never to trust a bare pattern match on the process table, so this section
must not hand you one. Measured in S1340: `pgrep -fl 'codex exec'` run from an
agent shell did **not** in fact match its own wrapper, while
`ps -eo pid,ppid,command | grep -E '[c]odex exec'` **did** return the checking
shell itself. So the naive form was not observed to self-match, and the ps form
was. The split-literal above removes the possibility either way, at the cost of
one line. Prefer construction over a claim that a hazard did not occur the one
time it was tried.

**Council panels are covered by NEITHER signal and there is no mechanical check
for them.** A review dispatched to CC, GLM or Kimi is a thread task that spawns
no subprocess, so signal 1 cannot see it, and signal 2 cannot tell it apart from
something that already died. Panel safety is enforced SOCIALLY — by step 2
below, by the peer bus, and by each instance not closing while it has a panel
out. Stated here rather than left to be discovered: if you did not dispatch the
panel yourself, you cannot prove from this machine that none is running.

Signal 1 empty and signal 2 empty means nothing is running. Signal 1 empty with
entries in signal 2 means either a live thread task (an AG/GLM/Kimi review, which
spawns no subprocess) or something that already died today — and you cannot tell
which from the record, which is the whole reason this section exists. **Resolve
it before bouncing: poll `check_build` on those task ids, or ask the instance
that dispatched them.** Do not treat "I could not tell" as "nothing is running";
that is the exact inversion T-2026-000398 is about.

### If a manual restart is genuinely required

Only with a human decision on the record, because it drops every connected
session including Max's.

1. Run the pre-flight above, then confirm the tree is clean and that
   `origin/main` is what you intend to deploy:

   ```
   git -C /Users/max/koskadeux-mcp status --porcelain     # must print nothing
   git -C /Users/max/koskadeux-mcp rev-parse origin/main  # the SHA you are deploying
   cat /var/tmp/koskadeux/deployed_sha                    # what is running now
   ```

2. Tell the peer instance and get an answer. **Do not act on silence.**

3. Kickstart **detached**, or the command dies with the server it is bouncing.
   If you are running through the MCP server, a bare foreground kickstart kills
   your own shell mid-command:

   ```
   cat > /var/tmp/koskadeux/restart.sh <<'SH'
   #!/bin/bash
   sleep 3
   launchctl kickstart -k "gui/$(id -u)/com.koskadeux.mcp" \
     >> /tmp/koskadeux_mcp_reload.log 2>&1
   SH
   chmod +x /var/tmp/koskadeux/restart.sh
   nohup /var/tmp/koskadeux/restart.sh >/dev/null 2>&1 &
   disown
   ```

   The `sleep` lets your tool call return before the server goes away. Expect
   the next call or two to fail while it comes back; that is normal.

4. **Verify from launchd, never from the kickstart exit code.** Tolerant
   extraction, because the output format is not guaranteed across macOS
   versions:

   ```
   launchctl list com.koskadeux.mcp | awk -F'= ' \
     '/"PID"/{gsub(/[^0-9]/,"",$2); print "PID="$2} \
      /LastExitStatus/{gsub(/[^0-9]/,"",$2); print "LastExitStatus="$2}'
   ```

   Observed on this machine (S1340): `"PID" = 49692;` and
   `"LastExitStatus" = 9;`. Nine is the SIGKILL of the old process and is the
   expected value — but accept `137` too (128+9), which some systems report for
   the same event. A non-zero status consistent with SIGKILL means the bounce
   worked; it does not mean the server crashed.

   Then confirm the new start time is later than the commit you are deploying,
   remembering §W's local-versus-UTC trap:

   ```
   # Both sides in UTC, so there is nothing left to convert in your head.
   TZ=UTC ps -o lstart= -p <the PID from above>
   git -C /Users/max/koskadeux-mcp show -s --format=%cI <the SHA>
   ```

   Naming the local-versus-UTC trap without giving the conversion is how S1340
   repeated it. If you remember one thing: `ps lstart` is LOCAL, git and Living
   State are UTC, and this box runs CEST (UTC+2), so an uncorrected comparison
   is wrong by two hours in the direction that makes a stale process look fresh.

   **If verification fails** — no PID, a `LastExitStatus` you cannot reconcile
   with a SIGKILLed predecessor, or a start time NOT later than the commit —
   the bounce did not do what you think. **Do not write `deployed_sha`.**
   Leaving it stale is the safe failure: the reloader keeps seeing a pending
   deploy and keeps deferring. Check `/tmp/koskadeux_mcp.log` for a startup
   failure, and note `KeepAlive` here restarts only on a NON-zero exit, so a job
   that exited cleanly will not come back on its own.

5. **Only after that verification**, record the deploy:

   ```
   printf '%s\n' <the SHA you verified> > /var/tmp/koskadeux/deployed_sha.tmp \
     && mv /var/tmp/koskadeux/deployed_sha.tmp /var/tmp/koskadeux/deployed_sha
   ```

   Use the SHA you actually verified as running, which is `origin/main` at the
   moment of the bounce, not local `HEAD` (they differ whenever you have
   unpushed commits). Write via a temp file and rename so a half-written marker
   can never be read. **Order matters and is not cosmetic:** writing this first,
   or on the strength of the kickstart returning zero, tells the reloader a
   deploy succeeded when it may not have. That is a fail-open on the single file
   that records what is actually running, and the automatic reloader trusts it
   without question.

6. Message the peer the new pid and start time before either instance dispatches
   anything.

### Related

§W (abandoned worker — what a careless bounce produces), T-2026-000398 (the
guard's inverted predicate, covering all three mechanisms that share it),
T-2026-000397 (narrower duplicate, superseded by 398).


## §Y Plus-One Discipline (was root copy §J)

Review-mode MP and AG dispatches require a DeepSeek +1 review. The discipline is
defined by four contracts:

- Findings folding: primary findings remain first, DeepSeek-only findings fold
  into the next round, and overlapping severity conflicts are surfaced instead
  of silently downgraded.
- Conflict surfacing: incompatible verdicts or incompatible severities write a
  `verdict_conflict` ledger event and block later builder dispatches for the
  same BQ and review round.
- Side-by-side display: chat summaries use
  `tools/council_review_summary.py::render_review_summary` so primary and
  DeepSeek verdicts always appear together with finding-count breakdowns.
- Review-round completeness: a round is not complete until the primary verdict
  and a terminal DeepSeek state are both recorded for the same BQ and round.

For chat output, use the fixed review-summary block. Do not hand-write a summary
that omits the DeepSeek verdict, finding counts, or disposition line.


## §Z Conflict Adjudication Procedure (was root copy §K)

When a `verdict_conflict` event exists, dispatch remains blocked until one of
the ledgered resolution paths lands:

- `merge_primary`: keep the primary reviewer result as the builder input.
- `merge_union`: merge the primary findings with DeepSeek-only findings.
- `re_review`: send the round back through review after clarifying the conflict.

Adjudication events use `verdict_conflict_adjudicated`. Emergency waivers use
`verdict_conflict_waived`. Both require audit fields in the payload:
`actor`, `timestamp`, `conflict_id`, `justification`, and for adjudication,
`adjudication`.

Only authorized adjudicators may unblock a conflict. The default authorized
actor is `max`; non-authorized events are audit evidence only and do not unblock
dispatch.


## Retired-Agents Appendix

### XAI (Grok) - RETIRED S528

XAI was Council's challenger/architect-only voter from S342-S528. It was retired due to consistent line-number fabrication on code audits, excluded from `gate3_post_build_audit` since S342 per BQ-COUNCIL-XAI-LINE-NUMBER-VERIFICATION, and DeepSeek graduation S528 superseded the architecture-only niche with broader review competence.

Cold-storage state: preserved via `xai_client.py` and `grok_cli_bridge.py` in the koskadeux-mcp repo; reactivation runbook documented at `infra:council-comms.retired_agents.xai` Living State entity.

Reactivation procedure summary: see `infra:council-comms.retired_agents.xai.reactivation_procedure` for step-by-step. Trigger conditions are a model upgrade significantly improving line-number reliability or a specific audit niche that XAI uniquely fills.

**Retirement completed in code (S1153, folded here at S1351 from the former standalone note).** XAI/Grok is retired in CODE as well as roster. Max-directed Codex cleanup @ koskadeux-mcp `d75abc40` removed xai from all active Council schemas/enums, KD routing, Council Hall, gate-write validation, cross-review registration, and seed state; `council_request(agent="xai")` returns a retirement error; `XAIClient` was removed from kd_clients while legacy `xai_client.py` and `grok_cli_bridge.py` remain on disk, unrouted. Post-hoc cross-review: AG APPROVE with one LOW finding, that the Council Hall seat enum was narrowed to {mp, ag} instead of widened to the active roster, fixed @ `c49fa6c9` with GLM APPROVE. Activation of both commits required an MCP server restart. HISTORICAL detail, do not read as current roster: the S1153 fixtures and hall seats referenced ag/mp/glm/deepseek/cc, which was the roster of that date. Roster canonical remains `infra:council-comms` (XAI retired since S528/S994).


## Appendix - E-04 Canonical Smoke Sequence (laptop-routing durability fix)

Precedent S691 (first complete codified application; predecessor durability gap S686, Mars S690.W T3 ordering finding). Related repair scenarios: G-01 (gateway timeout), G-03 (codex queue), G-06 (routing-fix smoke recovery).

1. Confirm env var ABSENT in plist before edit: `/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:KOSKADEUX_DISABLE_LAPTOP_ROUTING' <plist>` should fail.
2. Backup: `cp <plist> /tmp/<plist-name>.S<session>.bak`.
3. Add env var: `/usr/libexec/PlistBuddy -c 'Add :EnvironmentVariables:KOSKADEUX_DISABLE_LAPTOP_ROUTING string 1' <plist>`.
4. Validate XML: `plutil -lint <plist>`.
5. Capture OLD_PID: `launchctl list | awk '$3=="<service>"{print $1}'`.
6. bootout: `launchctl bootout gui/$(id -u)/<service>`; poll `launchctl list` until the service is unloaded.
7. bootstrap: `launchctl bootstrap gui/$(id -u) <plist>`; poll `launchctl list` until NEW_PID is present and != OLD_PID.
8. Verify env in BOTH the bash wrapper AND python child PIDs: `pstree -p <NEW_PID>`; for each PID, `ps -E -p <PID> | grep KOSKADEUX_DISABLE_LAPTOP_ROUTING` (no tr pipe).
9. Cross-check `launchctl print gui/$(id -u)/<service>` shows the env var in the canonical 'environment' Dict, NOT only 'inherited environment'.
10. Smoke dispatch: `council_request agent=mp mode=open_response cwd=/Users/max/Projects/ai-market/ai-market-backend task='echo hostname + ENV var'`; verify hostname=Koskadeux.local, env=1, no node-path error.
11. Optional: mode=review smoke with a real BQ context (implicitly covered by any subsequent reviewer dispatch in the same session).

### T-2026-000300 harness semantics (shipped 2026-07-21, koskadeux-mcp @ 57590559)

The enforcing code ships an atomically-versioned §E supplement at `koskadeux-mcp/runbooks/agent-dispatch.md` (rows E-T300-01/02); that file is a narrow supplement and THIS runbook remains canonical. Summary of the shipped semantics:

| Signature / procedure | Meaning | Operator action |
|---|---|---|
| `pre_build_branch_ahead` | Branch genuinely ahead of ITS OWN origin ref (never compared against origin/HEAD since 57590559). Payload carries repo_root/branch/upstream_ref/head_sha. | Push the branch or reconcile; do not force-dispatch. |
| `pre_build_detached_unpushed` | Detached HEAD not contained in any origin ref after fetch --prune. | Push or attach the intended branch, re-dispatch. |
| `pre_build_git_probe_failed` | git itself failed (missing binary, timeout, no-origin named distinctly). Fails closed, nothing discarded. | Fix the environment; work untouched. |
| Stacked-build pre-position | For builds atop an unmerged reviewed commit: check out the target branch at its PUSHED head, set upstream to the branch's own origin ref, pass explicit `cwd` on dispatch. | Required before any stacked structural dispatch. |
| Failure/timeout preservation | Builder commits are pinned to `refs/koskadeux-build/<sha>` before any teardown; timeout payloads report worktree_path + preserved ref; retained worktrees carry a TTL marker and are reaped after expiry. | Recover via the pinned ref; never assume a failed verdict means lost work. |
