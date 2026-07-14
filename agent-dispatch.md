> **S612 Process Consolidation Owner**: this runbook is the single canonical reference for agent dispatch reliability after the S612 consolidation that collapsed ~20 process BQs into BQ-PROCESS-AGENT-DISPATCH-RELIABILITY-S612 (P0). Per MP review mandate, content is organized under four explicit sub-sections; existing body sections map into these per the survivor BQ body.absorbed_bqs subsection field. Future failure surfaces file as revisions to this runbook, NOT as new BQs.
>
> **Sub-section layout (Council R1 mandate, MP/AG/DS concurrent):**
> - **§A Dispatch routing & credentials** — dispatch routing failure modes, tool namespace prefix quirks, bq_code mandatory on Council dispatches, fold-dispatch credential primary minting, spec-authoring compliance-gate misfire.
> - **§B Builder runtime reliability** — MP/Codex wrapper repair-exhausted false-failure, MP runner workspace contamination, MP build timeout tunability, mid-round server checkpoint loss recovery, manifest emission verifier safety, Codex bridge CI workflow stability.
> - **§C Reviewer wrapper contracts** — progress-guard wrong for review mode (write-first pattern), DS spec inlining requirement, AG read-only enforcement.
> - **§D Agent-specific behaviors** — DS verdict emission + enum drift + spec mandate cleanup + diff access; AG review auto-chunking + sandbox writes + streaming generation + review depth security; MP codex CLI streaming wrapper regression.
>
> Revisions require Council R1 review-mode approval. Filed under S612.

---

# Agent Dispatch Runbook

## Council roster (current — canonical: infra:council-comms)

**Gate voter panel: CC + DeepSeek + GLM — exactly three** (Max-approved S1213; CORE 9.8; BQ-COUNCIL-ROSTER-CC-REVIEW-GLM-VOTER-S1213). ACTIVATION STATUS: code shipped and Gate-3-approved on branch feat/council-roster-chunk1-2-cc-review-path-s1221 (head 49739a44, S1222); the deployed gateway enforces the previous panel until the Chunk 5 activation freeze completes (merge + gateway restart + live per-voter proof). Consensus: 2/3 standard only after 3/3 valid participation; 3/3 unanimous for security/auth/money/production-data/customer-data; missing/failed/malformed/model-mismatched voters fail the gate closed — no builder substitution, no reduced quorum, no fallback voter.

Per-agent:
- **MP**: mandatory builder for both instances; never substituted; never votes on its own work; explicit review dispatch remains available but MP is NOT a gate voter.
- **CC**: first-class code/spec reviewer via the read-only review path (`council_request agent=cc mode=review`): plan mode, no permission bypass, Read/Glob/Grep-only tool surface, pinned dispatch_sha, model verified (`claude-opus-4-8`; mismatch discards the vote), full terminal envelope preserved through async status reads. Never a build path for BQ/development code.
- **DeepSeek**: gate voter, review + spec-authoring, per-dispatch cost cap, raw-JSON-only prompts, ≤3 findings.
- **GLM**: gate voter, review-only, content-cited/diff-inlined (no filesystem access); verify quoted code against the diff (nested-quote garble quirk).
- **AG is PAUSED** (absent from active rosters; adapter/config and explicit review dispatch remain valid — pause, not deletion).
- **XAI is RETIRED** (Max go, S994).
- **Vulcan/Mars are never gate voters** (instance non-voter rule). Reversal condition: if Vulcan's model returns to any Anthropic model, the change is blocked until CC panel independence is re-reviewed (CORE 9.8).

Historical rounds with vulcan/ag/mp voter keys remain readable (schema legacy keys); write-path member validation rejects retired members. Canonical roster + per-agent quirks live in `infra:council-comms` (model_policy patched v58, S1222: cc=claude-opus-4-8, vulcan=gpt-5.6-sol).

This section documents the S1213 roster change and discharges the S1221 waived roster-change runbook attestations (S1221-D1..D7).

## §C.0 AG / Gemini response-schema constraints (Vertex google-genai Schema subset)

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

## §C Architecture

MP build and review dispatches use the Codex CLI bridge. For
`council_request agent=mp mode=build`, `council_request agent=mp mode=review`,
and `dispatch_mp_build`, the default backend path is now
`dispatch_codex_cli_streaming`.

The streaming bridge launches Codex CLI with `subprocess.Popen`,
`start_new_session=True`, and disk-backed output capture. It monitors progress
from three signals: the final output file, the stdout transcript, and
`cwd/task_state.md` when present. Any mtime or size growth counts as progress.

`council_request agent=mp mode=open_response` keeps the legacy synchronous
`run_codex_cli` path because it is intended for fast text-only voter responses.
Direct `run_codex_cli` callers also retain fixed-deadline semantics for backward
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

## §G Repair

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
   `_REVIEW_DIFF_INLINE_CAP_CHARS = 40_000` (`tools/agents.py`); anything above
   that is silently truncated and the reviewer audits half the code. Split a
   large branch into two or more scoped reviews, each under the cap.

Deploy note: the review budget lives in `openrouter_glm_client.py`,
`deepseek_client.py`, `deepseek_server.py` and `tools/agents.py`. A merge to main
is NOT live until the owning process restarts. `com.koskadeux.mcp` carries the
GLM client in-process; DeepSeek runs as its own long-lived service. Bouncing only
the MCP server leaves DeepSeek on stale code and it keeps returning empty
completions. Restart BOTH:

```
launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp
launchctl kickstart -k gui/$(id -u)/com.koskadeux.deepseek_server
```

The MCP bounce wipes boot state; re-run `kd_session_open` + `kd_session_plan`
after. Verify with a real review dispatch against a large diff, not a probe: a
trivial probe passes even when the bug is fully present (verified live S1190 —
GLM 39.5k-char prompt, 24,790 reasoning tokens, `finish_reason=stop`, full
verdict envelope).

## §I Scenarios

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

## §J Plus-One Discipline

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

## §K Conflict Adjudication Procedure

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

### XAI retirement completed in code (S1153)

XAI/Grok is now retired in CODE as well as roster: Max-directed Codex cleanup @ koskadeux-mcp `d75abc40` removed xai from all active Council schemas/enums, KD routing, Council Hall, gate-write validation, cross-review registration, and seed state; `council_request(agent="xai")` returns a retirement error; `XAIClient` removed from kd_clients (legacy `xai_client.py` + `grok_cli_bridge.py` remain on disk, unrouted). Post-hoc cross-review: AG APPROVE (one LOW finding — the Council Hall seat enum was narrowed to {mp, ag} instead of widened to the active roster; fixed @ `c49fa6c9`, GLM APPROVE: hall seats now mp/ag/glm/deepseek/cc, default mp/ag/glm). Roster canonical remains `infra:council-comms` (xai retired since S528/S994). Activation of both commits requires an MCP server restart; quorum/test fixtures now reference ag/mp/glm/deepseek/cc.

## Gate-change consultation for shipped mandates (S1164, discharges S1164-D4)
Loosening or altering ANY mechanism installed under a unanimous Council mandate (customer-data, security, auth, payments) requires a fresh design vote at the SAME bar (unanimous) BEFORE build — even when Max directs the change; his directive settles the business decision, the vote hardens the implementation invariants. Procedure: (1) write a compact spec stating context, the exact loosening, and the invariants that stay hard; (2) dispatch the standing voters (check infra:council-comms for roster; S1164 used MP+AG+DeepSeek) in open_response with verdict APPROVE/APPROVE_WITH_MANDATES/REJECT, max 3 findings; (3) fold ALL mandates into the build prompt as BINDING; (4) normal build → Gate-3 (reviewer≠builder, inline diffs for DS/GLM per T-2026-000206) → merge → Gate-4 live verify; (5) record the decision as a state event naming the vote and mandates. Precedent: S1164 HF metadata-only-by-default (unanimous; hard line kept: data rows always require seller-approved disclosure snapshot).
