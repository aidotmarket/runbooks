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

Historical text carried verbatim from the retired root copy. Its former
MP/AG/DeepSeek reviewer roster and Council-R1 approval rule are superseded and
grant no current dispatch or voting authority. The only surviving operational
point is that new dispatch failure surfaces are filed as revisions to this
runbook rather than as new build-queue items. Current revisions follow the live
CC/Kimi/GLM review panel from `infra:council-comms`.

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
| Codex CLI backend for MP | SHIPPED | `koskadeux-mcp/dispatch_codex_cli.py` | Codex CLI dispatch path exercised by MP build tasks | 2026-04-29 |
| Gemini/AG server backend | SHIPPED | `koskadeux-mcp/antigravity_client.py` | AG server health + task dispatch coverage | 2026-04-29 |
| DeepSeek server/API backend | SHIPPED | `koskadeux-mcp/deepseek_server.py` | DeepSeek review-schema and server health coverage | 2026-04-29 |
| Claude Code backend for CC | SHIPPED | `koskadeux-mcp/tools/agents.py:_handle_call_cc` | CC background task dispatch coverage | 2026-04-29 |
| XAI Grok dispatch | DEPRECATED | `koskadeux-mcp/xai_client.py` | Retired S528; cold-storage only, no active dispatch coverage | 2026-04-29 |


### §B.1 Council roster (folded from the retired root copy)

Carried from the retired root copy and corrected at S1351 against live `infra:council-comms` v62.

**Read §B and §D as implementation coverage, and this block as operational roster truth.** They are answering different questions and the apparent disagreement was never a contradiction. §B records whether the dispatch code exists and is wired; §D records whether the adapter and auth scope are complete. Neither says whether the agent currently votes. AG carries `COMPLETE` implementation coverage in §D and is PAUSED operationally. XAI carries `DEPRECATED` dispatch status in §B because the client is cold-storage rather than deleted, and is RETIRED operationally. DeepSeek carries `COMPLETE` implementation coverage and is retired from voting. The §B and §D last-verified dates of 2026-04-29 apply to the code claims only.

`infra:council-comms` remains canonical for live roster state. Read it before dispatching.


**Gate voter panel: CC + Kimi + GLM — exactly three** (Max direct directive S1319; CORE v9.13 names CC, Kimi and GLM in the amendment gate). ACTIVATION STATUS: ACTIVE. Kimi replaced the DeepSeek seat at the S1319 cutover (koskadeux-mcp `1a7d9c6e`, deployed at `2257a367`, gateway restarted 2026-07-24). `REQUIRED_MEMBERS` and `VALID_MEMBER_IDS` in `council_gate_runner.py` are exactly {cc, kimi, glm}. The deployed gateway enforces this panel.

> HISTORICAL, superseded: the panel was CC + DeepSeek + GLM from S1213, activated at S1223 (49739a44 merged to koskadeux-mcp main as d370d65c, gateway restarted on the merged SHA, live per-voter proof CC/DeepSeek/GLM all APPROVE plus fail-closed quorum verification inside the Chunk 5 freeze; Vulcan ratification peer msg #1178). That record is retained as history and must not be read as current roster state. Consensus: 2/3 standard only after 3/3 valid participation; 3/3 unanimous for security/auth/money/production-data/customer-data; missing/failed/malformed/model-mismatched voters fail the gate closed — no builder substitution, no reduced quorum, no fallback voter.

Per-agent:
- **MP**: mandatory builder for both instances; never substituted; never a gate reviewer or voter.
- **CC**: first-class code/spec reviewer via the read-only review path (`council_request agent=cc mode=review`): plan mode, no permission bypass, Read/Glob/Grep-only tool surface, pinned dispatch_sha, model verified (`claude-opus-4-8`; mismatch discards the vote), full terminal envelope preserved through async status reads. Never a build path for BQ/development code.
- **Kimi**: gate voter, review-only, with bounded read-only at-SHA repository tools (`read_file_at_sha`, `list_dir_at_sha`, `grep_at_sha`, `git_show`) through the shared provider review loop. It has no write, shell, network, state, secret, restart, or deployment authority. Live exact-SHA proof: task `2db3201d` on koskadeux-mcp `fdf50693`.
- **DeepSeek**: RETIRED from voting at S1321, superseding the S528 graduation. It can no longer cast a valid member vote on any gate. The dispatch surface `agent=deepseek` remains technically callable and `deepseek_server` may still be running, but nothing routes votes to it and new gate dispatches must not target it. HISTORICAL capabilities, retained for reactivation reference only: review plus spec-authoring, per-dispatch cost cap, raw-JSON-only prompts, ≤3 findings. No cold-storage record has been written yet; reinstatement follows the XAI pattern, a Council-approved roster change (BREAKING per §H.2) plus Max approval.
- **GLM**: gate voter, review-only, with the same bounded read-only at-SHA repository tools as Kimi through the shared provider review loop. It has no write, shell, network, state, secret, restart, or deployment authority. Live exact-SHA proof: task `ff0f2f67` on koskadeux-mcp `fdf50693`; malformed terminal JSON was repaired once under the unchanged evidence identity and returned a binding verdict.
- **AG is PAUSED** (absent from active rosters; adapter/config and explicit review dispatch remain valid — pause, not deletion).
- **XAI is RETIRED** (Max go, S994).
- **Vulcan/Mars are never gate voters** (instance non-voter rule). Reversal condition: if Vulcan's model returns to any Anthropic model, the change is blocked until CC panel independence is re-reviewed (CORE 9.8).

Historical rounds with vulcan/ag/mp voter keys remain readable (schema legacy keys); write-path member validation rejects retired members. Canonical roster + per-agent quirks live in `infra:council-comms` (model_policy patched v58, S1222: cc=claude-opus-4-8, vulcan=gpt-5.6-sol).

This section documents the S1213 roster change and discharges the S1221 waived roster-change runbook attestations (S1221-D1..D7).


## §C. Architecture & Interactions

Dispatch is a gateway-controlled routing layer. Operators submit a task, target agent, mode, working directory, and evidence references; the gateway chooses the agent backend, applies mode constraints, and returns either a synchronous result or a background task id.

Historical rationale, superseded for current roster/build roles: MP's Codex CLI automation and wiring-gap detection made it the primary dispatch builder; AG supplied a secondary cross-vote; DeepSeek's S528 record justified its former full-voter seat; and CC once served as fallback builder. Current operational truth is the block above: MP is mandatory builder, CC/Kimi/GLM are the gate voters, AG is paused, and DeepSeek is retired.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Dispatch Gateway | `koskadeux-mcp/tools/agents.py:_handle_call_*` | task records, Living State build refs | MP, CC, Kimi, GLM, retained AG/DeepSeek backends, Vulcan | Normalizes task args and mode boundaries before backend invocation. |
| MP/Council review middleware | `koskadeux-mcp/tools/agents.py` review dispatch handlers and provider read-only review loop | immutable Git-object evidence, returned envelope | CC, Kimi, GLM, retained DeepSeek backend | Preloads or reads exact-SHA review evidence and applies provider-specific bounds before dispatch. |
| Kimi review path | shared `provider_readonly_review.py` loop | immutable Git objects, evidence ledger, returned envelope | Kimi | Reads authorized files only through `read_file_at_sha`, `list_dir_at_sha`, `grep_at_sha`, and `git_show` at the pinned commit. |
| git push guardrail, pre-push hook | repository pre-push hook and environment resolution | local ref, remote ref, push environment | git remote | Guards main pushes; remote-ref equality is authoritative for the push outcome. |
| MP Backend | `koskadeux-mcp/dispatch_codex_cli.py` | Codex config, git branch, build task record | Codex CLI / GPT-5.5 | Synchronous reviews may time out; substantial builds use `dispatch_mp_build`. |
| AG Backend | `koskadeux-mcp/ag_server.py` -> `antigravity_client.py` | AG server task record, Vertex auth env | Gemini CLI / Gemini 3.1 Pro | Read-only review prompts must state no file modification. |
| DeepSeek Backend | `koskadeux-mcp/deepseek_server.py` -> `deepseek_client.py` | DeepSeek task record, API token env | DeepSeek API / deepseek-v4-pro | Retained, technically callable review path; retired from active gate voting. |
| CC Backend | `koskadeux-mcp/tools/agents.py:_handle_call_cc` | background review task id, immutable review evidence | Claude Code / Opus | Active gate voter through the read-only review path; never a BQ/development builder. |
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

MP build dispatches use the Codex CLI bridge. For
`council_request agent=mp mode=build` and `dispatch_mp_build`, the default
backend path is `dispatch_codex_cli_streaming`. Retained MP review/open-response
handler code is not current gate authority and must not be used for a gate vote.

The streaming bridge launches Codex CLI with `subprocess.Popen`,
`start_new_session=True`, and disk-backed output capture. It monitors progress
from three signals: the final output file, the stdout transcript, and
`cwd/task_state.md` when present. Any mtime or size growth counts as progress.

The retained non-gate `council_request agent=mp mode=open_response` handler
returns a `dispatch_async` task ID, but it cannot supply review or voting
authority. The background closure still calls `run_codex_cli`; direct
`run_codex_cli` callers retain fixed-deadline semantics for backward
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
| MP | mandatory build dispatch from Codex CLI | Codex CLI / GPT-5.5 | full repo write only in explicit build/author mode | COMPLETE |
| AG | dispatch from `antigravity_client.py` | Gemini CLI / Gemini 3.1 Pro | repo read | COMPLETE |
| DeepSeek | dispatch from `deepseek_server.py` | DeepSeek API / deepseek-v4-pro | repo read | COMPLETE |
| CC | active gate review from Claude Code wrapper | Claude Code / Opus | read-only pinned-SHA review; no BQ/development build authority | COMPLETE |
| Kimi | dispatch through the shared provider read-only review loop | Moonshot API (OpenAI-compatible) / kimi-k3 | bounded read-only at-SHA repository tools; no writes or privileged effects | COMPLETE — live exact-SHA read and binding-verdict proof `2db3201d` |
| GLM | dispatch through the shared provider read-only review loop | OpenRouter / z-ai/glm-5.2 | bounded read-only at-SHA repository tools; no writes or privileged effects | COMPLETE — live exact-SHA read, terminal repair, and binding-verdict proof `ff0f2f67` |
| Vulcan | dispatch orchestration | GPT-5.6-sol / MCP tools | gateway, LS, all repos | COMPLETE |
| XAI | RETIRED - see retired-agents appendix | Grok CLI | retired | PARTIAL — retired; see appendix for cold-storage and reactivation procedure |

This table records IMPLEMENTATION coverage, not operational roster status. A `COMPLETE` row means the adapter and auth scope are wired, not that the agent currently votes. AG is `COMPLETE` here and PAUSED operationally; DeepSeek is `COMPLETE` here and retired from voting at S1321. The live gate voter panel is CC + Kimi + GLM and is recorded in §B.1, with `infra:council-comms` canonical.

XAI uses `PARTIAL` coverage here only because §D coverage status is constrained to `COMPLETE|PARTIAL|GAP|PLANNED`. The dispatch status is `DEPRECATED` in §B, and the retirement record is the retired-agents appendix plus `infra:council-comms.retired_agents.xai`.


## §E. Operate

```yaml operate
- id: E-01
  trigger: A BQ chunk requires MP to build a dispatch-scoped change.
  pre_conditions: [feature_branch_exists, target_repo_clean_or_intentionally_dirty, relevant_specs_read, BQ_entity_has_body_summary]
  tool_or_endpoint: dispatch_mp_build(task=<prompt>, cwd=<repo>, branch=<branch>, timeout=300)
  argument_sourcing:
    prompt: derive from the BQ chunk ACs, required context, and verification plan
    cwd: use the target repo absolute path
    branch: use the active feature branch
    timeout: use the configured MP background timeout unless the BQ states otherwise
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(branch + prompt_digest + target_commit)
  expected_success: {shape: background task id plus committed artifact, verification: "compare git HEAD, task transcript, and BQ build summary"}
  expected_failures:
    - {signature: gateway_timeout, cause: task exceeded synchronous endpoint limit}
    - {signature: stale_task_state, cause: files committed but dispatcher status did not refresh}
  next_step_success: Run customer-perspective verification, patch the BQ entity, and request review.
  next_step_failure: Use F-01 or F-04 to choose retry, reconcile, or manual escalation.
- id: E-02
  trigger: A completed build needs optional non-gate AG advice and live state explicitly permits that advisory dispatch.
  pre_conditions: [commit_sha_known, review_scope_is_read_only, specs_and_diff_available, AG_server_healthy, infra_council_comms_confirms_AG_advisory_eligibility]
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
  next_step_success: Attach the verified result as non-gate advisory evidence; obtain the required CC/Kimi/GLM votes separately.
  next_step_failure: Use F-02 or narrow the prompt; do not substitute AG, MP, or DeepSeek for an active gate voter.
- id: E-03
  trigger: A gate review needs Kimi's required voter coverage.
  pre_conditions: [Kimi_provider_healthy, review_scope_is_read_only, exact_dispatch_sha_known, dispatch_cost_cap_available]
  tool_or_endpoint: council_request(agent=kimi, mode=review, task=<review_prompt>, cwd=<repo>, dispatch_sha=<sha>)
  argument_sourcing:
    review_prompt: derive from gate ACs and changed-file list
    mode: review only
    dispatch_sha: use the exact immutable commit under review
    cost_cap: read from infra:council-comms dispatch config
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash("kimi" + commit_sha + review_scope)
  expected_success: {shape: strict review result with verdict, findings, and at-SHA read evidence, verification: ensure exact-model/schema validation and required-file coverage passed}
  expected_failures:
    - {signature: health_failure, cause: provider unavailable or credential missing}
    - {signature: schema_validation_failure, cause: result did not match required review shape}
    - {signature: repository_review_coverage_incomplete, cause: required exact-SHA files were not read completely}
  next_step_success: Add Kimi's verdict and immutable read evidence to the Council review set.
  next_step_failure: Repair the Kimi path and retry; do not substitute MP, AG, DeepSeek, or any other non-member.
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
| F-09 | HISTORICAL (superseded at deployed `fdf50693`): GLM or DeepSeek returned a countable verdict over a silently truncated inline diff | Before the shared at-SHA review loop, the GLM/DeepSeek inline path capped evidence at 40,000 characters; DeepSeek is now retired and GLM uses the four bounded exact-SHA tools | Historical verdicts remain unproven; current GLM verification requires a pinned dispatch SHA, complete required-file tool coverage, and a binding strict verdict | G-09 | CONFIRMED |
| F-10 | HISTORICAL (superseded at deployed `fdf50693`): Kimi timed out while receiving one unbounded inlined diff | Before the shared at-SHA review loop, Kimi received the full inline diff under a latency cap | Historical failures remain diagnostic records; current Kimi verification requires a pinned dispatch SHA, complete paginated at-SHA reads, and a binding strict verdict | G-10 | CONFIRMED |
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
  root_cause: A live-state-authorized non-gate AG advisory dispatch stopped making progress before returning advice.
  repair_entry_point: koskadeux-mcp/antigravity_client.py
  change_pattern: Re-read infra:council-comms; only if it still explicitly permits AG advisory work, narrow the prompt, require read-only mode, repair health if needed, and redispatch once as non-gate advice. Never use the result as voter coverage.
  rollback_procedure: Cancel or supersede the timed-out advisory task id; preserve the gate as failed closed until CC/Kimi/GLM evidence is complete.
  integrity_check: Verify the replacement advice and citations, label it non-gate, and confirm it was not added to the voter set.
- id: G-03
  symptom_ref: F-03
  component_ref: MP Backend
  root_cause: MP dispatches are queued behind the Codex CLI mutex.
  repair_entry_point: koskadeux-mcp/dispatch_codex_cli.py
  change_pattern: Wait for the active MP build task; independent CC/Kimi/GLM review work may proceed in its own lane, but no voter may substitute for another and queueing alone is not failure.
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
  root_cause: HISTORICAL — the former GLM/DeepSeek inline path silently truncated evidence at 40,000 characters (T-2026-000364). The deployed GLM path at fdf50693 replaced it with bounded exact-SHA repository reads; DeepSeek is retired.
  repair_entry_point: provider_readonly_review.py and the GLM review dispatch handler
  change_pattern: For current GLM reviews, pin dispatch_sha and require full changed-file coverage through read_file_at_sha/list_dir_at_sha/grep_at_sha/git_show before accepting the strict verdict. Treat any historical truncated GLM or DeepSeek verdict as unproven and re-run GLM on the exact immutable commit when current evidence is needed.
  rollback_procedure: None; verdicts are additive, so discard the uncovered verdict and re-run scoped.
  integrity_check: The GLM envelope records the exact dispatch SHA, complete required-file coverage in its evidence ledger, exact model match, and a valid binding verdict.
- id: G-10
  symptom_ref: F-10
  component_ref: Kimi review path
  root_cause: HISTORICAL — the former Kimi inline path supplied one unbounded diff and could exhaust its latency budget (T-2026-000365). The deployed path at fdf50693 replaced it with paginated exact-SHA repository reads.
  repair_entry_point: provider_readonly_review.py and the Kimi review dispatch handler
  change_pattern: For current Kimi reviews, pin dispatch_sha and require complete paginated reads for every required file before accepting the strict verdict. A repository-tool failure or incomplete coverage fails the review closed.
  rollback_procedure: None; re-dispatch scoped.
  integrity_check: The Kimi envelope records the exact dispatch SHA, complete required-file coverage in its evidence ledger, exact model match, and a valid binding verdict.
- id: G-11
  symptom_ref: F-11
  component_ref: git push guardrail, pre-push hook
  root_cause: The pre-push guardrail appears to evaluate `KD_ALLOW_MAIN_PUSH` in a context where it is not visible, prints a refusal, and returns non-zero while the push itself completes; the precise mechanism is not established (T-2026-000367).
  repair_entry_point: the repository pre-push hook and its environment resolution
  change_pattern: Until the ticketed fix ships, confirm every push against the remote before acting on the result, and do not re-dispatch, re-commit, or repair on the strength of the printed error alone. The cost of believing it is redoing work that already landed, which is how a correct build was discarded in S1324.
  rollback_procedure: None.
  integrity_check: Remote head equals local head for the pushed branch and the working tree is clean.
```


### §G.1 Historical empty-completion incident (DeepSeek / former GLM inline path) — T-2026-000232

Historical symptom: a review dispatch to DeepSeek or the former GLM inline path failed with a parse
error and `raw_response_length=0`, e.g. `DeepSeekResponseParseError: ...
(candidate_count=0, ..., raw_response_length=0)`, or a blank GLM verdict. A
trivial `mode=open_response` probe to the same provider succeeds, which proves
the provider is up and misleads you into hunting a prompt or parser defect.

Historical cause: the provider reasoning trace and visible
content share ONE output budget. With a small `max_tokens`, a substantive review
spends the whole budget thinking and returns zero content tokens -> empty
completion -> parse failure. This is already written down in
`config:resource-registry` -> `secrets.OPENROUTER_API_KEY.notes`. Read the
registry and TOPIC-ROUTER on the error string BEFORE reading code.

Current handling:

1. Read `finish_reason` and the token telemetry now returned in the review
   envelope (`prompt_tokens`, `completion_tokens`, `reasoning_tokens`,
   `max_tokens`, `prompt_chars`, `empty_content_retries`). `finish_reason=length`
   with `reasoning_tokens` at or near `max_tokens` is the signature.
2. Budget content separately from reasoning. Review budget is 32000 tokens with a
   separate 8000-token reasoning cap (`reasoning.max_tokens` on OpenRouter), plus
   retry-once-on-empty at double budget. Landed in koskadeux-mcp `f1aa7d19`.
3. For current GLM review, pin the exact dispatch SHA and require complete
   evidence coverage through only `read_file_at_sha`, `list_dir_at_sha`,
   `grep_at_sha`, and `git_show`. The shared provider loop paginates reads and
   fails closed on repository-tool failure, incomplete coverage, invalid
   terminal schema, or an unprovable cost bound. Do not use the former inline
   diff/cap workaround. DeepSeek is retired and cannot supply gate coverage.

Deploy note: the active GLM review budget and shared read-only loop live in
`openrouter_glm_client.py`, `provider_readonly_review.py`, and `tools/agents.py`.
A merge to main is not live until `com.koskadeux.mcp` restarts onto the new
commit. The retained DeepSeek service is outside the active roster and is not
part of current gate verification.

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
      id: E-02. trigger: A completed dispatch-gateway patch needs optional non-gate AG advice and infra:council-comms explicitly permits that advisory dispatch. pre_conditions: live-state AG advisory eligibility, commit SHA, changed-file list, repo cwd, read-only scope, and AG server health are known. tool_or_endpoint: council_request(agent=ag, mode=review, task=<read_only_prompt>, cwd=<repo>). argument_sourcing: eligibility from current infra:council-comms; task from the advisory questions plus "READ-ONLY - DO NOT modify any files"; cwd from the checked-out repo; evidence refs from spec, commit, and diff. idempotency: IDEMPOTENT_WITH_KEY on ag + commit_sha + review_scope. expected_success: AG returns non-gate read-only advice with no file writes, and cited lines are verified before attachment. expected_failures: missing live-state eligibility, progress-guard timeout, MAX_TURNS exhaustion, unsupported line claim, unhealthy AG backend, or counting AG toward a gate. next_step_success: attach the result as advisory evidence and obtain the required CC/Kimi/GLM votes separately. next_step_failure: preserve the advisory failure and fail closed for gate purposes; never substitute AG, MP, or DeepSeek for an active voter.
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
      id: E-03. trigger: A gate review needs Kimi's required active-voter coverage. pre_conditions: Kimi provider is healthy, review scope is read-only, the exact dispatch SHA is known, and the configured cost cap is available. tool_or_endpoint: council_request(agent=kimi, mode=review, task=<review_prompt>, cwd=<repo>, dispatch_sha=<sha>). argument_sourcing: task from gate ACs and changed-file coverage; cwd from the reviewed repo; exact immutable SHA from git; cost cap and model from infra:council-comms. idempotency: IDEMPOTENT_WITH_KEY on kimi + dispatch_sha + review_scope. expected_success: Kimi returns a schema-valid binding verdict with complete at-SHA evidence from only the four bounded repository-read tools. expected_failures: provider health failure, model mismatch, repository-tool failure, incomplete required-file coverage, schema validation failure, or cost-cap refusal. next_step_success: add the Kimi vote to the CC/Kimi/GLM gate set. next_step_failure: fail the gate closed and retry Kimi without substituting MP, AG, or DeepSeek.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha]
        argument_values:
          agent: kimi
          mode: review
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-02, G-02, council:I-04]
    scenario: |
      id: F-02. trigger: A live-state-authorized non-gate AG advisory dispatch stalls with a progress-guard timeout while checking a dispatch patch. pre_conditions: infra:council-comms explicitly permits the advisory dispatch, and the AG transcript, last progress marker, original prompt, repo cwd, and AG server health are available. tool_or_endpoint: AG transcript plus council_request task record. argument_sourcing: task id from gateway response; timeout marker from transcript; prompt size from payload; health from AG server check. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as AG progress-guard timeout and cite BQ-COUNCIL-AG-PROGRESS-GUARD-FIX before any advisory redispatch. expected_failures: treating it as a policy disagreement, losing the transcript, rerunning the same broad prompt, or counting AG toward a gate. next_step_success: use G-02 with a narrower read-only prompt only if live-state eligibility remains explicit. next_step_failure: preserve the AG non-response and fail closed for gate purposes; obtain CC/Kimi/GLM votes without substitution.
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
      id: F-02. trigger: A live-state-authorized non-gate AG advisory dispatch returns no verdict because review-mode MAX_TURNS=25 is exhausted. pre_conditions: infra:council-comms explicitly permits the advisory dispatch, and the AG transcript, max-turn marker, diff size, prompt body, and review_order are available. tool_or_endpoint: council_request task transcript. argument_sourcing: max-turn evidence from transcript; changed files from git diff; role expectation from infra:council-comms review_order. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as AG review-mode budget exhaustion and cite BQ-COUNCIL-AG-MAX-TURNS-REVIEW-MODE. expected_failures: accepting a partial non-verdict, widening timeout without narrowing scope, confusing it with gateway outage, or counting AG toward a gate. next_step_success: redispatch with G-02 using an ultra-tight diff-only prompt only if live-state eligibility remains explicit. next_step_failure: preserve AG non-response and fail closed for gate purposes; obtain CC/Kimi/GLM votes without substitution.
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
      id: G-02. trigger: A live-state-authorized non-gate AG advisory dispatch exhausts MAX_TURNS without a usable result. pre_conditions: infra:council-comms still explicitly permits the advisory retry, and the failed task id, original diff, changed-file list, exact review questions, and transcript are preserved. tool_or_endpoint: council_request(agent=ag, mode=review, task=<ultra_tight_diff_only_prompt>, cwd=<repo>). argument_sourcing: changed files from git diff --name-only; exact questions from the failed prompt; cwd from repo; read-only instruction from §E. idempotency: IDEMPOTENT_WITH_KEY on failed_task_id + narrowed_prompt_digest. expected_success: AG returns focused non-gate advisory evidence over only the dispatch diff. expected_failures: second timeout, broad architecture critique, fabricated file:line claim, or an attempt to count AG toward a gate. next_step_success: attach the replacement as advisory evidence and obtain CC/Kimi/GLM votes separately. next_step_failure: preserve AG non-response and fail closed for gate purposes; never use MP or DeepSeek as voter coverage.
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

Lifecycle metadata records the S1369 roster and exact-SHA review-path refresh. The most recent registered scenario-harness pass remains the earlier S1265 run.

```yaml lifecycle
last_refresh_session: S1369
last_refresh_commit: 959a4ac
last_refresh_date: 2026-07-27T22:21:28Z
owner_agent: vulcan
refresh_triggers:
  - council_request dispatch contract or allowed_tools handling changes
  - agent backend auth/env wiring changes
  - active, retired, or reactivation state changes for Council agents
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: 0.0
last_harness_date: 2026-07-18T08:36:20.840312Z
first_staleness_detected_at: null
```

The dispatch scenario set is registered under `tests/fixtures/harness_scenarios/agent-dispatch/` and passed the S1265 conformant harness.


## §K. Conformance

Conformance fields for the S1369 content refresh.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1369 / 2026-07-27T22:21:28Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

The §K block records the strict-lint result; harness state is authoritative in §J.


## §L Historical DeepSeek Review-Round Completeness (superseded)

The following terminal DeepSeek states are retained only to interpret historical
rounds:

- `verdict_received`
- `classified_timeout`
- `classified_malformed`
- `classified_truncated`
- `classified_hallucinated_context`
- `classified_provider_error`
- `audited_waiver`

The former degraded-round rule allowed a primary verdict to carry after a
terminal DeepSeek failure. It is not current gate authority. Current gate rounds
require complete valid CC/Kimi/GLM participation; a missing, failed, malformed,
model-mismatched, or incomplete active voter fails the gate closed.

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
Follow the current dispatch and repair rules. Historical plus-one and
DeepSeek-conflict procedures below do not remain in force; the sandbox only
narrows an explicitly live-state-authorized non-gate AG advisory dispatch.

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

## §N Historical DeepSeek Skip Rule (superseded)

The former DeepSeek +1 process rejected "DeepSeek SKIPPED" outcomes. DeepSeek is
now retired, so current gate dispatches must not target it at all.

Historical fanout regression coverage remains in
`tests/integration/test_skip_fanout_regression.py`; it does not alter the current
CC/Kimi/GLM roster or permit fallback.

## §O Historical Structural Middleware Wiring

This section records retained middleware plumbing from
BQ-COUNCIL-DISPATCH-MIDDLEWARE-WIRING. References to AG or DeepSeek below are
implementation history, not current gate eligibility; current voting uses only
CC, Kimi, and GLM, and MP is the mandatory builder.

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

## §P Historical DeepSeek Context-Access Auto-Resolution Layer (superseded)

Everything in this section documents retained pre-retirement behavior only.
DeepSeek is retired and must not be dispatched for current gate coverage. The
fallback and truncation behavior below is not an authorized current review
procedure.

Historically, when `council_request agent=deepseek mode=review` was dispatched,
`deepseek_server.py` auto-extracts any commit SHA from the task prompt, fetches
the diff via `git show` at that SHA in the configured `repo_root`, validates
cited file paths against `git ls-tree`, and prepends a structured
`RESOLVED REPO CONTEXT` prelude before sending the prompt to the DeepSeek API.

The default `repo_root` is `/Users/max/koskadeux-mcp`, set in
`deepseek_server.py:_default_review_repo`. For non-default repositories, callers
must pass the `cwd` parameter explicitly, pointing at the repo that contains the
cited SHA.

This was structurally enforced for the former backend — see §Q.

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

In the former path, if the diff exceeded the auto-cap, the `FULL DIFF` header was marked
`(truncated)` and the diff body ends with an explicit truncation marker. The
default cap is 10K tokens, approximated as about 40K chars.

Historical fallback behavior did not break dispatch:

- No SHA in prompt: prompt is sent unchanged.
- Invalid `repo_root`: prompt is sent unchanged and a warning is logged.
- Git command failure: prompt is sent unchanged and a warning is logged.
- Over-cap diff: diff is truncated with an explicit marker, then dispatch
  continues.

Manual diff inlining belonged to that former path and must not be used as
current gate evidence. Current Kimi and GLM voters use only the bounded
exact-SHA four-tool loop; CC uses its pinned read-only review path.

Design references:

- `specs/bq-council-deepseek-context-access-fix-gate1.md`
- `specs/bq-council-deepseek-context-access-fix-gate2.md`

## §Q — Build Dispatch CI-Workflow Verification and Recovery

Structural MP build dispatches record four immutable values before any shared
branch mutation:

- `dispatch_base_sha`: the commit from which the isolated slot started;
- `builder_commit_sha`: the builder's verified, exactly-one-commit result;
- `target_branch`: the shared branch selected at dispatch time; and
- `expected_remote_old_sha`: the remote branch tip observed before the build.

The CI-workflow gate runs in the isolated slot after the builder reports
success and before any push. The gate executes the paths listed in
`ci_verification.py:CI_WORKFLOW_TEST_PATHS`. A persistent pre-push CI failure
resets only that isolated slot worktree to `dispatch_base_sha`; it must not
reset, check out, or otherwise mutate a peer slot or the shared checkout.

Every normal or recovery push to the shared branch is a single
compare-and-swap attempt:

```text
git push --force-with-lease=<branch>:<expected_remote_old_sha> origin HEAD:<branch>
```

The expected SHA is immutable for the attempt. A failed lease must never be
handled by refreshing the expected SHA, rebasing, or retrying automatically.
A fresh dispatch or explicit operator adjudication is required.

The pre-push path normally leaves no remote regression to undo. If a retained
legacy or operator recovery path must undo a commit that was already pushed,
the only permitted revert selector is the recorded `builder_commit_sha`.
Immediately before preparing that revert, verify that the recovery worktree's
observed commit equals `builder_commit_sha`. Never infer the selector from the
current branch position.

Error envelopes and operator handling:

- `ci_regression`: CI failed before push and the isolated slot was reset to
  `dispatch_base_sha`, or a commit-specific legacy recovery completed. Inspect
  the failing tests and immutable SHA evidence, correct the build, and start a
  fresh dispatch.
- `ci_regression_head_moved`: the recovery worktree no longer points at
  `builder_commit_sha`. No revert or push was attempted. Preserve the worktree,
  compare `builder_commit_sha` with `observed_head_sha`, identify who advanced
  it, and adjudicate a new recovery from immutable evidence.
- `shared_branch_cas_rejected`: the remote no longer equals
  `expected_remote_old_sha`, or the explicit lease was rejected. Preserve the
  local commit or prepared revert, inspect `observed_remote_sha`, and start a
  fresh dispatch. Do not refresh, rebase, or retry the rejected attempt.
- `ci_regression_revert_failed`: the exact-SHA revert could not be prepared.
  Preserve the worktree and inspect its status before any manual cleanup.
- `ci_check_unavailable` or `ci_check_timeout`: repair the gate environment or
  timeout cause, then begin a fresh dispatch.

Each failure envelope must remain secret-free and include
`dispatch_base_sha`, `builder_commit_sha`, `target_branch`,
`expected_remote_old_sha`, `observed_head_sha`, `observed_remote_sha`, and
`mutation_occurred`.

The skip flag is emergency-only. Use it only with explicit authorization. A
skipped gate must emit an audited `ci_check_bypass` event and return
`ci_workflow_check.status == "skipped"`.

Design authority:

- `specs/BQ-CONCURRENT-BUILD-CAPACITY-S1214-GATE2.md` §3.4 and §4-C3 at
  `db849f67`.

## §S Review Verdict Persistence

Review-mode dispatches can persist returned verdict text in the handler after the
provider result is available. Current gate-voter reviewer keys are `cc`, `kimi`,
and `glm`; the retained non-gate/backend keys are `ag`, `mp`, and `ds`
(`agent=deepseek` maps to `ds`). The handler writes to the target branch, not
from inside the review sandbox.

Dispatch contract:

- Callers should pass `verdict_target_branch` on review-mode dispatches. During
  the migration phase `VERDICT_TARGET_BRANCH_REQUIRED=False`, missing branches
  emit `write_outcome=missing_verdict_target_branch_warning` and return the
  provider envelope unchanged for manual fallback.
- The post-migration flip is operator-controlled by changing
  `VERDICT_TARGET_BRANCH_REQUIRED=True` in `tools/agents.py`. After the flip,
  review-mode primary dispatches without `verdict_target_branch` fail at handler
  entry with `missing_verdict_target_branch`.
- Verdict filenames are `verdicts/<bq_slug>/r<round>/<reviewer>.md`. Reviewer
  keys supported by the deployed handler are `cc`, `kimi`, `glm`, `ag`, `mp`,
  and `ds`; `agent=deepseek` maps to `ds`. If round is absent, the handler writes
  under `r1`. Only `cc`, `kimi`, and `glm` are current gate voters.

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

Canonical pattern for an MP build dispatch grounded in a spec (Max directive S826, probe-verified S827; Living State: `infra:council-comms.mp_spec_file_dispatch_standard`). MP does not use this pattern for gate review.

Reference the COMMITTED spec path at a pinned commit SHA — never a bare path, never long specs pasted inline (Codex /goal objectives cap at 4,000 chars; real specs do not fit). Required thin-contract wrapper elements:

1. Read instruction: "use `git show <SHA>:<path>` — do not trust the working tree".
2. Scope guards: the explicit build/author file boundary and prohibited out-of-scope paths.
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
3. Run the chunk's Gate 3 review with the builder excluded and the complete active panel (MP built it → CC + Kimi + GLM review).
4. On pass, push as a deliberate instance merge: `KD_ALLOW_MAIN_PUSH=1 git push origin main` (fast-forward only).
5. Record the workaround: patch the BQ entity (chunk verdicts + `wrapper_incident`) and emit a `decision` event.

**Escalation:** if this recurs, file a BQ against the SchemaRepair/manifest-parser stage of the §O middleware rather than repeating manual recovery.

**Related:** before ANY MP dispatch pinned to a SHA that was committed via the GitHub API, `git fetch origin main` in the target repo first — the local clone will not have the object and the dispatch fails with `object/path is not available locally` (observed twice S1147; see §T and the TOPIC-ROUTER symptom table).

### §U addenda (S1147, activation session)

- The RepairExhaustedError-with-delivered-commit pattern hit **4/4 structural MP builds** in S1147. §U recovery worked every time with zero rebuilds. A BQ against the SchemaRepair/manifest-parser stage is now warranted (see BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146 follow-ups).
- **Check for shadowing after every MP session.py build:** one S1147 chunk added a module-level helper duplicating a pre-existing function name (`_read_state_entity`), silently shadowing the original for all earlier call sites. Grep `grep -n "def <name>(" <file>` for duplicate defs before review; the introduced-failure baseline diff (worktree at parent commit, identical pytest selection, `comm -13`) catches the symptom.
- **HISTORICAL GLM inline-review lesson (superseded by deployed `fdf50693`):** an orchestrator-condensed summary produced two false findings in S1147. Current GLM reviews read the exact pinned repository objects through the shared four-tool loop; do not replace those reads with a summary.
- **HISTORICAL DeepSeek substitution note (superseded by S1319/S1321):** DeepSeek is retired and AG is paused. Neither AG nor DeepSeek can substitute for CC, Kimi, or GLM; a missing active voter fails the gate closed.

### §U resolution note (S1150)

The manual-recovery loop in §U is now largely obsolete: the pipeline auto-recovers. Two S1150 fixes landed (koskadeux-mcp `745ba12d`, `25006e5e`) closing tickets T-2026-000193 and T-2026-000177: (1) structural build dispatches no longer die on a variable-scope error introduced by the S1147 wrapper fix — root-cause any repeat of "Gateway Error: upstream service unavailable" on build dispatch by running the handler in-process to get the real traceback (the gateway swallows it; the in-process repro is the decisive diagnostic, see T-193 for the recipe); (2) the pre-push gate no longer discards a green commit when the builder omits the manifest fence — it synthesizes a schema-valid manifest from the git diff, flags `requires_manual_diff_review`, and proceeds through CI + claim verification. Expected terminal state for a structural build on main is now `error_type=push_failed` with ALL gates passed and `operator_recovery_guidance` naming the verified commit — the guardrail refusing an automated main push is by design; the instance reviews (builder ≠ reviewer) and performs the `KD_ALLOW_MAIN_PUSH=1` merge. Keep §U's steps only for the case where gates genuinely did not run.

### §C.0 status note (S1152)

The §C.0 "sanitize at the adapter" fix is now IMPLEMENTED: `antigravity_client._gemini_sanitize_schema` (koskadeux-mcp `fc8a0d4a`) recursively strips `additionalProperties`/`$schema`/`unevaluatedProperties` from every tool inputSchema before building Gemini FunctionDeclarations. Trigger: the S1150 close gate added `additionalProperties` to `kd_session_close.runbook_exit`, which killed ALL AG dispatches at tool-fetch time (observed S1152 hall voter dispatch). If AG ever fails again with `FunctionDeclaration ... extra_forbidden`, a NEW rejected key has appeared — add it to the `_REJECTED` tuple in the sanitizer rather than editing tool schemas.

## Gate-change consultation for shipped mandates (S1164, discharges S1164-D4)
Loosening or altering ANY mechanism installed under a unanimous Council mandate (customer-data, security, auth, payments) requires a fresh design vote at the SAME bar (unanimous) BEFORE build — even when Max directs the change; his directive settles the business decision, the vote hardens the implementation invariants. Procedure: (1) write a compact spec stating context, the exact loosening, and the invariants that stay hard; (2) read infra:council-comms and dispatch the current standing voters — CC, Kimi, and GLM — with verdict APPROVE/APPROVED_WITH_MANDATES/REJECT; (3) fold ALL mandates into the build prompt as BINDING; (4) normal MP build → Gate 3 exact-commit CC/Kimi/GLM review → merge → Gate 4 live verify; (5) record the decision as a state event naming the vote and mandates. Historical precedent: S1164 used the then-current MP/AG/DeepSeek roster; that roster is not current authority.

## §V — CC gate-review dispatch mechanics (S1231)

CC (`council_request agent=cc mode=review`) is a read-only gate voter with filesystem access, but its dispatch contract differs from the shared Kimi/GLM exact-SHA review loop:

- **Pinned worktree required.** `cwd` must be a checkout whose HEAD equals `dispatch_sha`, or the dispatch fails `checkout_not_pinned` (`cc_review_target_invalid`). Never re-point the live server checkout (`/Users/max/koskadeux-mcp`); create a detached worktree: `git worktree add --detach <path> <sha>` and pass that as `cwd`.
- **Exactly one pinned ref.** Supplying conflicting `dispatch_sha`/`head`/`sha` aliases fails `dispatch_sha_alias_conflict`; supplying none fails `dispatch_sha_required`.
- **Inline diff cap, CC-only.** The CC preload inlines the pinned diff and HARD-FAILS loud (`cc_review_diff_truncated`) if it exceeds `CC_REVIEW_DIFF_INLINE_CAP_CHARS` (env, default 120000, read at process start — a change needs a handler restart). Shipped T-2026-000263 @ koskadeux-mcp 83c9189d after a 45.4k single-file Gate 2 spec could not pass the shared 40k cap and `review_paths` cannot narrow a single file.
- **Historical inline-diff truncation controls remain relevant only to CC and retained legacy backends.** CC's preload fails closed on `cc_review_diff_truncated`. The former GLM and Kimi inline-cap defects tracked by T-2026-000399/T-2026-000400 were superseded for those two voters by deployed `fdf50693`: both now use the shared exact-SHA loop with only `read_file_at_sha`, `list_dir_at_sha`, `grep_at_sha`, and `git_show`, pagination to completion, and required-file coverage before a verdict. DeepSeek remains retired; do not use its retained inline backend for gate coverage.
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


## §X.2 — A read-only review dies with no verdict on a wide commit (T-2026-000457, S1375)

**Symptom.** A GLM or Kimi review returns no verdict at all and fails with
`repository_tool_call_limit_exceeded`, message "<provider> requested an invalid
number of repository calls". Retrying with a narrower prompt does not help.

**Cause, measured S1375.** `provider_readonly_review.py` builds
`required_evidence` from EVERY file in the commit's changed-file set, so a
17-file commit demands 17 files of coverage regardless of what the dispatch
prompt asks the reviewer to look at. Against that, `DEFAULT_MAX_CALLS_PER_TURN`
was 4 and the provider was never told the ceiling existed. A model batching
enough calls to cover the required set exceeded the ceiling and the guard raised
fatally. **The trigger is changed-file count, not the repository and not the
reviewer.** Control case the same hour: a 1-file commit passed with 2 calls.
Narrowing the prompt cannot help, because required coverage comes from the
commit, not the prompt.

**Fix, live from koskadeux-mcp `137865b3`.** An over-ceiling batch is now
recoverable: nothing in the batch executes, the provider is told the requested
count and the ceiling and that none ran, and the loop continues. Give-up only
after more than `DEFAULT_MAX_CONSECUTIVE_CALL_LIMIT_VIOLATIONS` (2) consecutive
violations. The provider is told the ceiling and the required-file count up
front. `max_calls_per_turn` is settable per dispatch, default still 4, clamped
to `MAX_CALLS_PER_TURN_CEILING` (16).

**Signatures and what each means now:**

| Signature | Meaning | Action |
|---|---|---|
| `repository_tool_call_limit_exceeded` | Over the per-turn ceiling. **Recoverable** — appears in a correction, not necessarily a failure. | None if the review completes. If it recurs, raise `max_calls_per_turn` for that dispatch. |
| `repository_tool_call_limit_violation_exhausted` | The provider ignored more than two consecutive corrections. | Genuine provider non-compliance. Re-dispatch; if it repeats, the model is not honouring the tool protocol. |
| `repository_tool_call_batch_empty` | The provider returned an empty tool-call batch where calls were required. | Distinct from the above two; do not read it as a budget problem. |

**Diagnosis shortcut.** Failure telemetry now carries `requested_call_count`,
`max_calls_per_turn`, `required_evidence_count`, `turn` and
`consecutive_violation_count`. Read those five before theorising. The original
incident cost a session partly because the guard raised the same code and
message for an empty batch as for an over-ceiling one, which sent the diagnosis
toward the preloader and the repository rather than the call budget.

**Resolution, S1377.** T-2026-000457 is RESOLVED. End-to-end proof on the
deployed fix: GLM task 118e47c2 reviewed a 5-file C2 branch diff including a
full read of an ~8k-line file — 25 turns, 34 repository calls, $3.21 of an $8
cap, zero limit errors, and the terminal conformance repair returned a parsed
APPROVE. Operational rule from the incident pair: **wide GLM/Kimi reviews
(5+ changed files, or any file over ~2k lines) dispatch with
`max_budget_usd=8`.** A $4 cap dies at terminal repair
(`terminal_repair_cost_unprovable`) after the review substance succeeded, which
wastes the whole run at its most expensive point.


## §X.3 — Council re-dispatch and peer-coordination mechanics (S1375)

Three subjects that repeatedly reached the session-plan gate as
`no_entry_found` attestations and had no home. Written here so the next
session cites a runbook instead of attesting again.

### §X.3.1 Re-dispatching a Council round after verdict-enum drift

**The drift.** CC and Kimi intermittently emit the PAST-tense variant
`APPROVED_WITH_MANDATES`. The strict normalizer records that as `REVISE`
(S588 lineage). The substance is an approval; the record says otherwise.

**Rules, learned S1374/S1375:**
- Treat the strictest RECORDED reading as governing, fold everything, and
  re-review. Do not argue the raw text into an approval.
- Always read `raw_completion`, not only the recorded verdict.
- State the six present-tense values verbatim in the prompt
  (`APPROVE | APPROVE_WITH_NITS | APPROVE_WITH_MANDATES | REVISE |
  REQUEST_CHANGES | REJECT`) and say plainly that past-tense spellings are
  invalid and are recorded as REVISE. S1375 R2: all three voters returned
  present-tense values and the drift did not recur.
- **Do NOT specify a custom verdict JSON shape.** The harness enforces its own
  terminal schema; a competing shape in the prompt forces a conformance-repair
  round-trip (measured S1375, GLM task b8fa933f). Constrain the enum, let the
  harness supply the shape.

**Poisoned REQUIRED CONTEXT (T-2026-000446).** Review dispatches carry an
auto-injected "REQUIRED CONTEXT" block that can contain irrelevant and wrong
material — a Stripe/payments section and a 15% figure have both been observed,
against an actual 5% commission, plus a stale 4/4 unanimity claim against the
real 3-voter panel. Inoculate explicitly in the prompt: name the correct panel
(CC, Kimi, GLM), the correct commission, cite T-2026-000446, and tell the
reviewer the injected block is overridden. Reviewers otherwise review against
the injected content.

**Narrow the round.** On a re-review, ask each voter the narrow question — are
your own prior mandates discharged by the text rather than merely referenced,
and did the fold introduce a new defect — and restate that voter's own prior
findings back to it. This is what produced three clean verdicts in one round.

### §X.3.2 Reviewing a peer instance's change request at a pinned commit

The peer asks over the bus, naming a commit. Review the commit, not the
summary.

- Verify claims against ground truth, not against the peer's description. If
  the change projects CORE, compare the projected SHA-256 against
  `source_constitution_sha256` in your own boot kernel byte for byte (S1375,
  a0d5049).
- Check whether the commit is ALREADY an ancestor of `origin/main`. Peer review
  requests frequently arrive post-hoc; say so in the verdict rather than
  implying you gated it.
- Return the verdict on the bus with `kind=response` and a `ref_entity` naming
  the commit, so the thread is findable later.
- Nits belong to the peer to fold. Do not edit a peer's landed work yourself.

### §X.3.3 Confirming a cross-BQ gate dependency before the peer's gate closes

When your design constrains an item the peer owns, informal mention is not
enough — it must be recorded on the peer's entity.

- Send `kind=request` (which requires an ack) naming the constraint, the
  acceptable outcomes, and exactly what you need back.
- Offer explicit alternatives rather than an open question. S1375 offered
  (a) satisfy the constraint now, or (b) close with the gap recorded as a
  residual and blocked on the constraining chunk. Vulcan chose (b) in one line.
- Require the outcome to be written onto the owning entity, not held in either
  instance's head. T-2026-000422 carries
  `cross_bq_dependencies.s1374_chunk4.status=BLOCKS_GATE3_CLOSE`.
- If the answer is (b), record the reciprocal obligation on YOUR entity too, so
  the chunk that owes the discharge knows it owes it.

### §X.3.4 Two subjects that already have owners — stop attesting them

- **Disposition of an approved build item stale beyond the seven-day window**
  belongs to `aging-policy` (`stale_queue_undispatched`, §F. Isolate). S1375
  filed a `no_entry_found` attestation for this in error. CORE S17 requires the
  item to be surfaced and, if deferred, an explicit recorded decision event.
- **Establishing whether a branch actually landed** belongs to
  `branch-landed-verification` (§E-03). Do not re-derive it.

## §X.4 — Dispatch prompts that run in the shared checkout MUST end with "restore checkout to main" (S1376)

MP builds that operate in a shared repo checkout (anything dispatched with
`cwd` pointing at the live clone rather than an isolated worktree) can leave
that checkout on the build branch when they finish. S1376 measured the cost:
MP left `/Users/max/koskadeux-mcp` on the C2 branch, the next server restart
briefly served UNREVIEWED branch code for ~90 seconds before the drift was
caught and re-bounced. Full account on T-2026-000457.

Rules:

- Every build or fold dispatch prompt that can touch a shared checkout ends
  with an explicit instruction: check out `main` and verify with
  `git branch --show-current` before finishing.
- Before any server restart or reviewed merge, verify the shared checkout is
  on `main` yourself (`git branch --show-current`); do not assume the builder
  complied.
- Never `git checkout` in a shared clone while a builder is running in it.
  For pinned read-only reviews use an ephemeral detached worktree
  (`git worktree add --detach <path> <sha>`) and prune it in the same session.
  For ref-only operations (fast-forwarding `main` to a reviewed head), push
  the named branch ref remotely (`git push origin <branch>:refs/heads/main`)
  and `git fetch origin main:main` locally — neither touches the working tree.
  A raw SHA as the push source is rejected by the pre-push guardrail; use the
  branch name.

This section discharges the S1376 handoff lesson set; the GLM budget rule
lives in §X.2's resolution note.

## §X.5 — Session-open peer-bus drain and boot-state verification (S1379, discharges S1379-D1)

At every session open, and again before any dispatch, merge, or close:

1. Drain the peer bus first (`peer_msg_inbox`). Non-ack messages are consumed
   at-most-once on read — drain deliberately, act on what you drained.
2. HIGH-priority messages and anything `requires_ack` are handled BEFORE any
   new claim in the same turn. `request` and `alert` kinds always need
   `peer_msg_ack`; a drained-but-unacked alert is still open.
3. The bus deduplicates on (from, to, kind, ref_entity). A follow-up claim or
   status on the same entity silently returns the OLD row (`idempotent: true`)
   — check that flag, and vary `ref_entity` (e.g. `key#topic-session`) when a
   fresh row is required.
4. Boot payload claims (deploy SHA, service health, handoff assertions) are
   verified against ground truth before being relied on: read
   `/var/tmp/koskadeux/deployed_sha`, the server PID/start time, and the
   reload log rather than trusting prose. The handoff is a pointer, not
   evidence.
5. Mid-session tool results can carry `PEER MESSAGES AT TURN START` banners:
   these are already-consumed drains. Treat them exactly like step 2 —
   ack what requires ack before proceeding with the turn's claim or dispatch.


## §Y Historical Plus-One Discipline (superseded)

The former MP/AG primary plus DeepSeek +1 process is retained only as history.
It was superseded when Kimi replaced the DeepSeek seat at S1319 and DeepSeek was
retired at S1321. Current gate completeness requires the exact active
CC/Kimi/GLM panel from infra:council-comms; MP is builder-only, AG is paused, and
neither MP, AG, nor DeepSeek can satisfy or supplement a missing gate vote.
Conflict events from historical rounds remain readable, but their roster does
not authorize a current dispatch.


## §Z Historical DeepSeek Conflict Adjudication Procedure (superseded)

This procedure applies only when interpreting legacy MP/AG plus DeepSeek rounds.
It cannot unblock or authorize a current gate. Current CC/Kimi/GLM disagreement
returns through the current Council process and ultimately to Max.

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
10. Smoke the MP lane only through an explicitly bounded build-mode diagnostic in a disposable test branch; MP open-response/review mode is not current gate or review authority.
11. If reviewer routing also changed, run separate read-only smoke reviews through the active CC/Kimi/GLM paths at an exact test commit; never use MP, AG, or DeepSeek as replacement voter coverage.

### T-2026-000300 harness semantics (shipped 2026-07-21, koskadeux-mcp @ 57590559)

The enforcing code ships an atomically-versioned §E supplement at `koskadeux-mcp/runbooks/agent-dispatch.md` (rows E-T300-01/02); that file is a narrow supplement and THIS runbook remains canonical. Summary of the shipped semantics:

| Signature / procedure | Meaning | Operator action |
|---|---|---|
| `pre_build_branch_ahead` | Branch genuinely ahead of ITS OWN origin ref (never compared against origin/HEAD since 57590559). Payload carries repo_root/branch/upstream_ref/head_sha. | Push the branch or reconcile; do not force-dispatch. |
| `pre_build_detached_unpushed` | Detached HEAD not contained in any origin ref after fetch --prune. | Push or attach the intended branch, re-dispatch. |
| `pre_build_git_probe_failed` | git itself failed (missing binary, timeout, no-origin named distinctly). Fails closed, nothing discarded. | Fix the environment; work untouched. |
| Stacked-build pre-position | For builds atop an unmerged reviewed commit: check out the target branch at its PUSHED head, set upstream to the branch's own origin ref, pass explicit `cwd` on dispatch. | Required before any stacked structural dispatch. |
| Failure/timeout preservation | Builder commits are pinned to `refs/koskadeux-build/<sha>` before any teardown; timeout payloads report worktree_path + preserved ref; retained worktrees carry a TTL marker and are reaped after expiry. | Recover via the pinned ref; never assume a failed verdict means lost work. |

## §X.6 — GLM/Kimi review dispatch: preloaded-diff method, pinning, and provider quirks (S1382)

Discharges S1382-D1..D4.

1. Preloaded-diff reviews (S1382-D1). For GLM/Kimi code reviews, dispatch mode=review with explicit `base` and `head`. The legacy coverage controller may still deliver a partial changed-set (T-2026-000460a). ALWAYS include this tripwire in the task: "State the exact number of files in the changed-set you reviewed and list them — if you were shown fewer than the full changed-set, say so explicitly and do not approve." The tripwire caught partial coverage live twice on 2026-07-28. Expect this section to be superseded by bq-council-review-harness-reform-s1382 C3.

2. Full-diff pinning fallback (S1382-D2). When coverage is partial, generate the complete `git diff base..head` yourself and pin it: pinned_artifacts entries require (a) an absolute path under a repo root that is DECLARED in `review_sources` of the SAME dispatch, (b) a suffix in {.md, .txt, .json, .cfg, .ini, .rst, .toml, .yaml, .yml} — rename .diff to .txt, (c) size ≤ 2 MiB, (d) an exact lowercase sha256. Instruct the reviewer that the pinned artifact is the authoritative changed-set and to state its file count.

3. Provider quirks (S1382-D3). GLM's repo harness is bound to koskadeux-mcp and cannot resolve runbooks-repo dispatch SHAs — review runbooks documents via mode=open_response with the text inlined. Kimi open_response needs `max_tokens` ≥ 16000 (reasoning consumes the 4096 default and truncates the answer) and may time out once — retry with `timeout_s=600`. Backend-repo (ai-market-backend) review dispatches require explicit `cwd` set to the backend checkout.

4. Scripted file edits (S1382-D4). Never perform multi-replacement edits via a quoted bash heredoc containing escaped quotes — a Python SyntaxError silently skips ALL replacements while a subsequent `git commit` still succeeds on whatever else was staged. Write the edit script with write_file, run it, then VERIFY the target file content (grep for a folded phrase) before committing.
