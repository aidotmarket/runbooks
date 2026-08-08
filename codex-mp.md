---
system_name: codex-mp
purpose_sentence: Operating manual for MP (Codex), the Council's mandatory builder (not a gate voter since the S1213 roster change) — dispatch mechanics, configuration, timeouts, failure recovery, and the model-swap procedure.
owner_agent: vulcan
escalation_contact: Max (strategic forks, model-tier changes); Mars (structural middleware / runbook-gate internals)
lifecycle_ref: §J
authoritative_scope: MP/Codex build and author dispatch paths, Codex CLI configuration and auth, MP timeout and mutex behavior, MP failure signatures and recoveries, and the model-swap procedure. The signed exact-release runtime owns volatile Council facts; council-roster-quirks:C.1 owns MP interaction rationale.
linter_version: 1.0.0
---

# Codex / MP — Council Primary Builder

**MP** is the Council name for OpenAI **Codex**. It is the mandatory builder
for all BQ/development code builds and is never a voter, reviewer, or Council
Hall participant. All code and spec builds route to MP; CC is never a build
path. This strict separation prevents self-approval and keeps the review panel
independent. The current model comes from the signed exact-release runtime;
the interaction rationale is `council-roster-quirks:C.1`.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Legacy build dispatch (council_request mode=build, no dispatch_class) (S1148, T-113 fix via task 50f9dfad) | SHIPPED | `tools/agents.py:_handle_call_mp` | tests/regression/test_legacy_dispatch_unchanged.py | 2026-07-08 |
| Structural build dispatch (dispatch_class=structural, §O middleware) (S1150, end-to-end on 7ad740a4) | SHIPPED | `council_dispatch_middleware/ + tools/agents.py` | dispatch+AG suite (24/24 at S1131) | 2026-07-09 |
| Background dispatch + polling (S1148) | SHIPPED | `codex_cli_bridge.py:dispatch_codex_cli_streaming; council_request action=check_build` | covered by dispatch suite | 2026-07-08 |
| MP review/Hall dispatch | DEPRECATED | — | Negative mode, Hall, verdict, and quorum tests | 2026-08-02 |
| Spec authoring (mode=author, Gate 1) (S1147) | SHIPPED | `tools/agents.py:_handle_call_mp` | — | 2026-07-07 |
| Concurrency mutex (one Codex CLI at a time) (S1148, MP+CC serialized cleanly) | SHIPPED | `codex_cli_bridge.py:CODEX_LOCK_FILE (/var/tmp/koskadeux/codex_cli.lock, fcntl LOCK_EX)` | — | 2026-07-08 |
| Pre-push CI verification gate + auto-revert (S1150, manifest synthesis fix 25006e5e) | SHIPPED | `ci_verification.py (CI_WORKFLOW_TEST_PATHS)` | agent-dispatch.md §Q | 2026-07-09 |
| Automatic immutable runbook context on every dispatch route | PLANNED | `tools/runbook_delivery.py` | Common-provider route matrix and missing-context failure tests | 2026-08-02 |
| Target-repository action-bound candidate preservation before terminal success | PLANNED | `tools/agents.py` | Cross-repo scope, background completion, deleted-ref, and wrapper recovery tests | 2026-08-02 |
| Progress-based stall abort (S1111) | SHIPPED | `codex_cli_bridge.py (MP_PROGRESS_WINDOW_S=900)` | — | 2026-06-01 |
| Hard timeout backstop (env-tunable) (S1111 fix 995e1338) | SHIPPED | `.env MP_HARD_UPPER_BOUND_S=1800; envelope default in tools/agents.py:_build_mp_provider_envelope` | tests/regression/test_legacy_dispatch_unchanged.py | 2026-06-01 |
| dispatch_mp_build convenience wrapper | SHIPPED | `tools/agents.py:_handle_dispatch_mp_build` | — | 2026-06-01 |
| Codex CLI "goals" loop autonomy on long non-interactive builds (S827 probe: prefix harmless; loop engagement UNVERIFIED — see §F note) | PARTIAL | `/goal prefix accepted (codex exec)` | unverified on long builds | 2026-06-12 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Council dispatch handler | tools/agents.py:_handle_call_mp | task meta/output files under /var/tmp/koskadeux/ and backend action evidence | Koskadeux gateway, automatic context provider, structural middleware | Routes build/author only, derives target repo from validated cwd/spec, injects immutable context, and rejects review/Hall/vote modes. |
| Codex CLI bridge | codex_cli_bridge.py:run_codex_cli | CODEX_LOCK_FILE /var/tmp/koskadeux/codex_cli.lock (fcntl) | Codex CLI binary (codex exec) | Streaming path dispatch_codex_cli_streaming is production; nonstreaming legacy retained. OS-level timeout backstop from MP_HARD_UPPER_BOUND_S; progress-stall abort at MP_PROGRESS_WINDOW_S. Legacy dispatch_codex_cli (~L899) still contains a dead hardcoded `timeout 600` wrapper — zero live callers, remove on next bridge cleanup. |
| Codex CLI + auth | ~/.codex/config.toml | OAuth session (auth_mode: chatgpt) | OpenAI Codex service | model = "gpt-5.6-sol" (frontier-only policy; S1200 per Max directive, T-2026-000197). **The served string is `gpt-5.6-sol` — NOT `gpt-5.6`, NOT `gpt-5.6-codex`; both 400 on our ChatGPT account tier.** Two surfaces must agree: this file AND koskadeux-mcp/.env `MP_MODEL` (the bridge passes `-m MODEL` from the env explicitly). MCP servers deliberately removed from Codex config (62-tool overhead). CLI version at last verify: codex-cli 0.144.3. |
| Structural middleware (§O) | council_dispatch_middleware/ | builder-output manifests | ci_verification.py pre-push gate, SchemaRepair | Fires only when caller passes dispatch_class=structural. Terminal state push_failed is a DESIGNED guardrail: verified commit preserved, instance reviews then merges with KD_ALLOW_MAIN_PUSH=1 (S1150). |
| Automatic context delivery | tools/runbook_delivery.py | Exact activation, task/target digest, immutable delivery identity | aidotmarket/runbooks exact pin and common dispatch provider | Caller has no refs/attestation field. Missing or incomplete context stops dispatch without a legacy path. |
| Build preservation boundary | tools/agents.py | Backend action intent, validated target worktree, current remote candidate ref | Structural wrapper and GitHub collector | A build is not terminal-successful until its exact output commit is recoverable through the action-bound target-repository ref. |
| Cost/pricing surfaces | council_dispatch_middleware/cost_estimator.py; kd_finance.py | MODEL_PRICING / DEFAULT_MODEL_RATES | — | Model swaps MUST update these alongside config (see §G-05). |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Dispatch MP build/author | council_request (agent=mp) | Koskadeux session and exact action/target scope | COMPLETE |
| Vulcan/Mars | Poll background task | council_request (action=check_build, task_id) | same | COMPLETE |
| Vulcan/Mars | Convenience background build | dispatch_mp_build | same | COMPLETE |
| MP | Build/commit/push on Titan-1 repos | Codex CLI (codex exec) via bridge | Max's local git + gh credentials | COMPLETE |
| MP | Review, Hall, or vote | no public path | none | GAP |
| CC | Independent review and gate vote only | council_request (agent=cc, mode=review) | Exact-SHA repository read only | COMPLETE — never a build path; all builds remain MP. |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A BQ chunk or ticket fix needs a code build in a Titan-1 repo
  pre_conditions:
    - open Koskadeux session (kd_session_open + kd_session_plan done)
    - automatic runbook context service and backend action/preservation service healthy
    - target repo fetched (git fetch origin main) if the dispatch pins a SHA committed via GitHub API
    - spec committed at a pinned SHA when spec-grounded (agent-dispatch.md §T — reference path@SHA, never paste long specs)
  tool_or_endpoint: council_request(agent=mp, mode=build, task=..., cwd=<FULL macOS path>, session_id=..., timeout_s optional)
  argument_sourcing:
    cwd: config:resource-registry (full path — shorthand like "backend" is BROKEN, S347)
    runbook_context: do not supply it; the common provider derives and injects exact task-relevant context
    timeout_s: only if the build should exceed the env default; explicit per-dispatch wins over MP_HARD_UPPER_BOUND_S
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: '{task_id, status: dispatched|running} then check_build → {status: completed, result, ...}; MP reports branch/PR/commit'
    verification: verify the backend-observed current candidate ref for the exact validated target repo and action then fetch and inspect the actual diff at file:line before accepting claims; run stated tests if in doubt
  expected_failures:
    - signature: 'automatic runbook context unavailable'
      cause: immutable child delivery failed or was incomplete (see §F-08)
    - signature: 'gateway timeout on foreground dispatch >30s'
      cause: use background dispatch + check_build polling (§F-01)
  next_step_success: gated cross-review by the exact CC+Kimi+GLM panel with builder excluded; AG and DeepSeek are inactive and no fallback exists. Then merge; patch entity verdicts; same-session spec commit if gated
  next_step_failure: consult §F symptom table BEFORE diagnosing from code
- id: E-02
  trigger: A structural (middleware) build with CI gate + manifest is required
  pre_conditions:
    - everything in E-01
    - reconciliation subservice healthy; there is no bypass_reconcile path
  tool_or_endpoint: council_request(agent=mp, mode=build, dispatch_class=structural, ...)
  argument_sourcing:
    dispatch_class: literal "structural"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: gates pass; terminal state MAY be push_failed BY DESIGN with the verified commit preserved
    verification: review the preserved commit, then KD_ALLOW_MAIN_PUSH=1 git push origin main (fast-forward only)
  expected_failures:
    - signature: 'RepairExhaustedError: schema repair exhausted'
      cause: manifest parse/repair failure AFTER a delivered commit (§F-03; recover per agent-dispatch.md §U, do NOT rebuild)
  next_step_success: as E-01
  next_step_failure: agent-dispatch.md §U procedure
- id: E-03
  trigger: Release verification must prove MP cannot review, vote, or join Hall.
  pre_conditions: [exact_release_artifact_available, signed_runtime_verified, connected_schema_refreshed]
  tool_or_endpoint: schema inspection plus negative mode=review and council_hall participant probes for mp
  argument_sourcing:
    surfaces: inspect dispatch mode conditions, Hall enum/default, verdict persistence, normalization, and quorum consumers
  idempotency: IDEMPOTENT
  expected_success:
    shape: MP is accepted only for build/author and rejected from review, Hall, verdict, and quorum paths
    verification: exact artifact scan plus negative runtime probes produce no Council verdict or state write
  expected_failures:
    - signature: mp_review_surface_present
      cause: legacy reviewer/open-response/Hall route survived the builder-only cutover
  next_step_success: Attach negative proof to the release evidence.
  next_step_failure: Block release and physically remove the legacy route; prompt-level READ-ONLY is not a repair.
- id: E-04
  trigger: Codex model swap (e.g., gpt-5.6 → successor on release; gpt-5.5→gpt-5.6 executed S1181, T-2026-000197)
  pre_conditions:
    - availability VERIFIED on our Codex CLI auth tier (smoke dispatch) — a config pointing at an unserved model breaks the mandatory primary builder
  tool_or_endpoint: manual per §G-05
  argument_sourcing:
    model_string: OpenAI release notes + codex CLI model list
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: smoke build dispatch returns model_actual=<new model>; cross-review leg green
    verification: model_actual assertion + full-tree grep count of old model string == historical/pricing rows only
  expected_failures:
    - signature: dispatches 4xx/hang after swap
      cause: model not served on tier — revert config.toml model line (§G-05 rollback)
  next_step_success: update and sign every exact runtime/model surface plus `council-roster-quirks:C.1`; refresh this runbook §B/§C rows + §J
  next_step_failure: revert per §G-05, keep ticket open
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Foreground council_request(agent=mp) times out ~30s | Gateway proxy timeout on tasks >30s | reproduce with a trivial task (fast) vs a real build (times out) | §G-01 | CONFIRMED |
| F-02 | Task "running" indefinitely / silent past 300s, but files expected | MP delivered and committed even though the envelope tracker stalled (S451 family) | `git log --oneline -3` + `git status --short` in cwd; py_compile changed files | §G-02 | CONFIRMED |
| F-03 | Structural build returns RepairExhaustedError but commit landed and worktree clean | Builder-output-manifest parse/repair failure AFTER the build succeeded (hit 4/4 structural builds S1147) | git log shows the commit; diff matches chunk scope | §G-03 | CONFIRMED |
| F-04 | Build killed at exactly 600s | Pre-S1111 hardcoded envelope default overriding MP_HARD_UPPER_BOUND_S; OR server running stale module (gateway must be restarted after codex_cli_bridge.py changes — Python import cache) | check server process start time vs fix commit 995e1338; envelope timeout in dispatch args | §G-04 | CONFIRMED |
| F-05 | Dispatch fails "object/path is not available locally" on a SHA-pinned task | The pinned SHA was committed via GitHub API; local clone lacks the object | `git cat-file -t <sha>` in cwd fails | §G-06 | CONFIRMED |
| F-06 | Ordinary schema accepts MP review/Hall/vote | Legacy MP review route survived; prompt-level READ-ONLY never enforced the builder-only boundary | Inspect exact schema, routes, verdict persistence, and quorum consumers | §G-07 | CONFIRMED |
| F-07 | Second MP/CC dispatch appears hung at start | fcntl mutex serialization behind a running Codex CLI (deliberate) | `lsof /var/tmp/koskadeux/codex_cli.lock`; check_build on the other task |  | CONFIRMED |
| F-08 | Dispatch is refused because automatic runbook context is unavailable or incomplete. | Exact activation, runtime, corpus, task/target binding, or response budget failed. | Inspect the typed delivery error and confirm the child never launched; validate the exact immutable response and common-provider route. | §G-08 | CONFIRMED |
| F-09 | Builder process exits after producing good work but the task cannot report terminal success. | Exact target-repository action-bound remote candidate ref is missing, deleted, stale, or unresolved; background completion correctly waits for preservation. | Resolve validated cwd/spec to repo, read backend action publication binding, and verify the current remote ref points to the output commit. | §G-09 | CONFIRMED |
| F-10 | All MP dispatches fail after a model/config change | Model string not served on auth tier; or partial swap left mismatched EXPECTED_MODELS / adapters | smoke dispatch asserting model_actual; full-tree grep for old string | §G-05 | CONFIRMED |
| F-11 | MP build-result or manifest claims don't match reality (files, line numbers, test counts) | Builder messages over-claim; also spec-over-prompt: MP follows the committed spec over a diverging dispatch prompt | Manual diff inspection at file:line; compare prompt, pinned spec, preserved candidate, and test output |  | CONFIRMED |
| F-12 | Canonical repo checkout found detached after a legacy MP review | A forbidden legacy review route operated on the shared checkout | Inspect worktree list/reflog, preserve any work, and treat route reachability as release drift | §G-10 | CONFIRMED |
| F-13 | Every MP dispatch 400s with `invalid_request_error`; `model_requested` shows an unintended model | Handler process predates a model-config rollback on disk: env is loaded at process start, so `~/.codex/config.toml` + `.env MP_MODEL` being correct on disk is NOT sufficient (S1184/S1185, incident 9180928d) | Model identity smoke (§G-11 step 1); compare handler `ps lstart` (LOCAL time — Titan-1 is CEST=UTC+2, convert before comparing to Z timestamps) against the config-change time | §G-11 | CONFIRMED |
| F-14 | All Codex sessions 401 Unauthorized on wss endpoints; `codex login status` = Not logged in | `~/.codex/auth.json` missing or its refresh-token chain burned ("refresh token was already used") — stale backups do NOT recover it because refresh tokens rotate | `ls ~/.codex/auth.json` + `codex login status` | §G-12 | CONFIRMED (S1185) |
| F-15 | MP repeatedly introduces new defects while fixing prior ones on a hard/safety-critical component (fix N creates defect N+1) | Default reasoning effort too low for the component's complexity | Count audit rounds: ≥2 REVISE rounds where the fix itself introduced a NEW defect (S1186 escalation spine: uuid4 dedup regression, ack leaks, benign-false storms) | §G-13 | CONFIRMED (S1186) |
| F-16 | Any git push refused with "GUARDRAIL: refusing malformed pre-push record" | Stale pre-push hook installed in that repository. The pre-fix copy rejects the local ref `HEAD`, so the ordinary `git push origin HEAD:refs/heads/<branch>` form is misread as a corrupted record. The message points at git or at credentials rather than at the hook's own field validation, which is why it reads like a security refusal (T-2026-000556, S1441) | `shasum -a 256 <repo>/.git/hooks/pre-push` against `koskadeux-mcp/githooks/pre-push`; any mismatch is a stale install. The fixed hook names the rejected field on refusal, the stale one does not | §G-14 | CONFIRMED (S1441) |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Council dispatch handler
  root_cause: gateway proxy timeout shorter than real build durations
  repair_entry_point: caller-side dispatch pattern
  change_pattern: always dispatch builds in background (council_request returns task_id immediately) and poll with check_build; never rely on a foreground build call
  rollback_procedure: n/a (usage pattern)
  integrity_check: check_build reaches a terminal status
- id: G-02
  symptom_ref: F-02
  component_ref: Codex CLI bridge
  root_cause: tracker/envelope stall while the underlying Codex process delivered
  repair_entry_point: ground-truth check in the build cwd
  change_pattern: verify delivery via git log/status + test run; if delivered, proceed to review/merge; do NOT redispatch blindly (duplicate work / conflicting branches)
  rollback_procedure: n/a
  integrity_check: delivered diff matches task scope; tests green
- id: G-03
  symptom_ref: F-03
  component_ref: Structural middleware (§O)
  root_cause: SchemaRepair/manifest-parser stage fails on the builder-output manifest after a successful build
  repair_entry_point: agent-dispatch.md §U procedure
  change_pattern: confirm delivery → run chunk tests + CI_WORKFLOW_TEST_PATHS locally → Gate 3 cross-review (builder excluded) → KD_ALLOW_MAIN_PUSH=1 fast-forward push → record wrapper_incident on the entity + decision event
  rollback_procedure: git revert of the pushed commit
  integrity_check: CI paths green; cross-review verdicts recorded
- id: G-04
  symptom_ref: F-04
  component_ref: Codex CLI bridge
  root_cause: hardcoded 600s envelope default (fixed 995e1338, activates on server restart) or stale imported module
  repair_entry_point: tools/agents.py:_build_mp_provider_envelope; server restart
  change_pattern: until the running server includes the fix, pass timeout_s explicitly (e.g. 1800) on builds expected >8 min; after any codex_cli_bridge.py change, restart the gateway/server or it serves the stale module
  rollback_procedure: n/a
  integrity_check: long build survives past 600s
- id: G-05
  symptom_ref: F-10
  component_ref: Codex CLI + auth
  root_cause: model swap is multi-surface; partial swaps break dispatch or cost accounting
  repair_entry_point: signed exact-release runtime plus every MP model consumer in koskadeux-mcp
  change_pattern: Verify the candidate model and intended reasoning-effort values with a bounded build-mode smoke, update every code/config/pricing/schema/runtime surface in one reviewed change, sign the exact runtime, reload only at a peer-safe zero-child boundary, and repeat the build-mode smoke. Full-tree search must show no live old model or hardcoded fallback. MP remains build-only throughout; no review leg is used as model evidence.
  rollback_procedure: Roll forward every model surface and the signed runtime to one previously verified exact value, reload at a peer-safe zero-child boundary, and repeat the build-mode smoke; a config-only change is not a rollback.
  integrity_check: signed runtime, connected schema, provider-observed model_actual, pricing, and every live consumer agree; MP review/Hall/vote probes remain rejected
- id: G-13
  symptom_ref: F-15
  component_ref: Codex CLI bridge (reasoning-effort dial)
  root_cause: default reasoning effort comes from ~/.codex/config.toml and is global; safety-critical or high-complexity dispatches need a stronger effort per-dispatch, and MP has repeatedly introduced regressions on hard components at default effort (S1186 escalation spine: 3 audit rounds)
  repair_entry_point: reasoning_effort parameter on call_mp / dispatch_mp_build (koskadeux-mcp 0bc68129, S1186)
  change_pattern: 'Pass reasoning_effort=<value> per dispatch. Accepted enum: none | low | medium | high | xhigh (invalid → ValueError). **`minimal` was REMOVED at S1205** — gpt-5.6-sol returns a hard 400 on it ("Unsupported value: minimal is not supported with the gpt-5.6-sol-1p-codexswic-ev3 model. Supported values are: none, low, medium, high, and xhigh"). The accepted set is MODEL-SPECIFIC: re-probe it on every model swap and prune the enum in codex_cli_bridge.ALLOWED_REASONING_EFFORTS and both tool schemas in the same change, or dispatches selecting a dropped value fail outright. OMIT reasoning_effort and behavior is unchanged — ~/.codex/config.toml governs exactly as before (backward compatible). When set, the bridge injects `-c model_reasoning_effort=<value>` into the codex exec args. xhigh is the ceiling. USE xhigh for safety-critical work (anything where a defect can silently drop an alert, lose money, or expose customer data) and for components where MP has previously regressed. NOTE: a newly merged dial does NOT take effect until the gateway reloads (both instances idle) — same F-13 trap as a model swap.'
  rollback_procedure: omit the parameter (no-op; config.toml governs) — the dial is additive and reversible by not passing it
  integrity_check: dispatch succeeds and model_matched=true; omitting the param reproduces pre-0bc68129 behavior
- id: G-06
  symptom_ref: F-05
  component_ref: Codex CLI bridge
  root_cause: GitHub-API-created commits are not in the local clone
  repair_entry_point: target repo checkout
  change_pattern: git fetch origin main (or the specific ref) in the target repo BEFORE any SHA-pinned dispatch; make it a pre-dispatch checklist item
  rollback_procedure: n/a
  integrity_check: git cat-file -t <sha> returns commit
- id: G-07
  symptom_ref: F-06
  component_ref: Council dispatch handler
  root_cause: A legacy MP review/Hall/verdict path survived the builder-only cutover.
  repair_entry_point: exact ordinary schema, handler routes, verdict persistence, and quorum consumers
  change_pattern: Physically remove MP from review and Hall modes and prove negative runtime rejection; never use prompt-level READ-ONLY as an authorization boundary.
  rollback_procedure: Stop rollout and preserve any unexpected work for manual reconciliation; do not reactivate the legacy review route.
  integrity_check: MP is accepted only for build/author and cannot emit, persist, normalize, or count a Council verdict.
- id: G-08
  symptom_ref: F-08
  component_ref: Automatic context delivery
  root_cause: the provider could not validate or fit exact context bound to the child task and target
  repair_entry_point: common dispatch provider and immutable runbook delivery runtime
  change_pattern: repair the exact activation runtime corpus task binding or response budget then redispatch through the ordinary route without adding caller references
  rollback_procedure: keep the child unlaunched; never use a direct or legacy dispatch path
  integrity_check: every public direct and indirect route injects complete context with one immutable delivery identity
- id: G-09
  symptom_ref: F-09
  component_ref: Build preservation boundary
  root_cause: successful output is not yet durably recoverable through the exact action-bound target-repository candidate ref
  repair_entry_point: structural wrapper publication and backend GitHub ref verifier
  change_pattern: preserve or recover the output commit publish/update the allowed candidate ref for this exact action and wait for backend verification before cleanup or terminal success
  rollback_procedure: stop cleanup and retain the worktree/artifact until preservation succeeds
  integrity_check: current remote ref resolves to the exact output commit under the expected repo session actor and action binding
- id: G-10
  symptom_ref: F-12
  component_ref: Council dispatch handler
  root_cause: A forbidden legacy MP review route operated on a shared checkout.
  repair_entry_point: canonical checkout evidence plus legacy route removal
  change_pattern: Preserve and reconcile the checkout without destructive reset, restore the intended branch only after proving its tip and cleanliness, then remove the MP review route and add a negative regression test.
  rollback_procedure: n/a
  integrity_check: canonical checkout is reconciled, peer notified, and MP review is schema-invalid and runtime-rejected.
- id: G-11
  symptom_ref: F-13
  component_ref: Koskadeux handler process (koskadeux_server.py) + Codex model config
  root_cause: model env/config loaded at handler start; a disk rollback does not reach a running process
  repair_entry_point: operator restart, then smoke
  change_pattern: '1) Run a bounded MP build-mode model smoke in a disposable test branch; assert provider-observed model_actual matches the signed runtime. 2) If wrong, verify config, env, and code fallbacks agree, then restart only at a peer-safe zero-child boundary. The gateway is unavailable during the bounce; there is no local fallback. 3) Re-run the same build-mode smoke before real work.'
  rollback_procedure: n/a (restart + config alignment)
  integrity_check: smoke returns success=true and model_matched=true. Post-S1205 this is REAL evidence: model_actual is read back from the Codex rollout file (~/.codex/sessions/**/rollout-*-<session_id>.jsonl), not the requested string echoed back, and it fails closed to false when the rollout is missing, unparseable, or disagrees with the CLI banner. Before S1205 model_matched was hardcoded true and proved nothing.
- id: G-12
  symptom_ref: F-14
  component_ref: Codex CLI ChatGPT OAuth credential (~/.codex/auth.json)
  root_cause: credential file lost or refresh-token rotation chain broken; deletion vector undetermined S1185 (no koskadeux code touches the file)
  repair_entry_point: Max interactive re-login (AI instances CANNOT do this - browser OAuth on Max ChatGPT account)
  change_pattern: '1) Do NOT restore old auth.json backups as a fix: rotated refresh tokens fail with "refresh token was already used", and a stale file makes codex login status lie - remove any stale copy so status honestly reads Not logged in. 2) Ask Max to run on Titan-1: codex logout, then codex login, completing the browser sign-in. 3) Verify: codex login status = Logged in using ChatGPT; direct smoke: cd ai-market-backend && echo "Reply with exactly: SMOKE_OK" | codex exec --model gpt-5.6-sol -; then the G-11 handler smoke.'
  rollback_procedure: n/a
  integrity_check: direct smoke returns SMOKE_OK on the intended model AND handler smoke shows model_matched=true (real readback post-S1205; see G-11)
- id: G-14
  symptom_ref: F-16
  component_ref: 'pre-push guardrail (koskadeux-mcp githooks/pre-push, installed per repository into .git/hooks)'
  root_cause: 'Two tracked copies of one guardrail. githooks/pre-push installs into koskadeux-mcp via scripts/install-git-hooks.sh; scripts/pre-push installs into EVERY OTHER repository via scripts/install_pre_push_hook.sh --repo PATH. T-2026-000383 fixed only the first, so backend and runbooks ran the pre-fix hook for eleven days and a correct push was refused as malformed. Converged at koskadeux-mcp 0e9c75ad6.'
  repair_entry_point: 'koskadeux-mcp 0e9c75ad6 - scripts/pre-push made byte-identical to githooks/pre-push, with tests/unit/test_pre_push_hook_single_source.py failing on any future divergence'
  change_pattern: '1) Confirm staleness by hash, not by reading the tracked file - shasum -a 256 on the INSTALLED .git/hooks/pre-push versus koskadeux-mcp/githooks/pre-push. 2) Back up, then reinstall from the tracked source - cp .git/hooks/pre-push .git/hooks/pre-push.pre-<ticket>.<stamp>, then sh scripts/install_pre_push_hook.sh --repo <abs path> from the koskadeux-mcp checkout (the installer refuses a repo with core.hooksPath set, which would make the install inert). 3) Verify behaviour against the INSTALLED hook by feeding it the records git would send, since a tracked file passing tests proves nothing about what is running - printf the four-field record into the hook with argv origin and the remote URL, and require - main refused without KD_ALLOW_MAIN_PUSH, main allowed with it, HEAD to main STILL refused, HEAD to build/* allowed, production refused, non-refs garbage and bad OIDs and short records all still refused, local filesystem remote exempt. 4) Push forms - prefer git push origin <branch> or git push origin refs/heads/<local>:refs/heads/<remote>; the HEAD form is legitimate and now accepted, and the resource registry documents it as the koskadeux-mcp workaround for origin/HEAD tracking. 5) Expect a stray unrelated refusal in stderr on koskadeux-mcp and backend commits - an untracked post-commit hook backgrounds git push origin main on every main commit and cannot set KD_ALLOW_MAIN_PUSH, so the guardrail refuses it silently. That is a separate superseded convention, not a failure of your push.'
  rollback_procedure: 'restore the backup - cp .git/hooks/pre-push.pre-<ticket>.<stamp> .git/hooks/pre-push'
  integrity_check: 'every repository installed hook sha256 equals githooks/pre-push, AND a synthetic protected-branch record is still refused without KD_ALLOW_MAIN_PUSH in each of them'
```

## §H. Evolve

### §H.1 Invariants

- MP is the mandatory builder for all BQ/development code and spec work. CC is review/vote only and never a build path.
- Builder ≠ reviewer, always. Auth/security/customer-data/money changes require unanimous Council.
- Frontier-only model policy: MP runs exactly ONE configured model, the current OpenAI frontier (Max S516). No fallback tiers in production dispatch.
- Spec-grounded dispatches reference the committed spec path @ pinned SHA (agent-dispatch.md §T); never paste long specs inline.
- Automatic runbook context and target-repository preservation are mandatory; no caller attestation, legacy dispatch, break-glass boolean, or background-process exit can bypass them.
- One Codex CLI at a time (fcntl mutex) — do not remove the lock to "parallelize".
- Model telemetry is EVIDENCE, not a label (S1205, T-2026-000243). `model_actual` is read back from the Codex rollout file and `model_matched` is a real comparison that fails CLOSED — false whenever the dispatch failed or the rollout is missing, unparseable, ambiguous, or disagrees with the CLI banner. Never restore a hardcoded default of true, and never add a bypass env var: an evidence gap must read as a failure, not a pass. The honest limit: the rollout records the model we REQUESTED. Combined with the fact that an unsupported model is a hard 400 with no substitution, requested == served for any turn that COMPLETES. Do not overclaim it as a server attestation.
- The expected model for every active role is sourced from the signed exact-release runtime. A hardcoded or Living-State fallback is forbidden; disagreement fails dispatch closed.
- Provider version pins are not mismatches. GLM serves `z-ai/glm-5.2-20260616` for requested `z-ai/glm-5.2`; Vertex can suffix a version. `_model_matches()` accepts `expected` plus a `-`/`@`/`:` suffix. MP is the exception and compares EXACTLY, because its rollout returns the exact requested string.
- reasoning_effort: gpt-5.6-sol supports none | low | medium | high | xhigh. It does NOT support `minimal` — that is a hard 400. `minimal` was removed from ALLOWED_REASONING_EFFORTS and from the tool schemas at S1205. Re-check the served set on any model swap; it is model-specific.

### §H.2 BREAKING predicates

- Changes the council_request tool contract for agent=mp (argument names/shapes) without a shim.
- Removes or weakens automatic context delivery, exact target-repository preservation, the CI verification gate, or the builder≠reviewer rule.
- Changes the mutex/serialization semantics of the Codex CLI bridge.

### §H.3 REVIEW predicates

- Model swap (follow §G-05; availability-gated).
- Timeout/stall-window default changes (MP_HARD_UPPER_BOUND_S, MP_PROGRESS_WINDOW_S).
- New dispatch_class or middleware stage.

### §H.4 SAFE predicates

- Prompt-template wording improvements; new §F/§G rows from observed incidents; test additions; doc updates.

### §H.5 Boundary definitions

#### module

Immediate subdirectories of koskadeux-mcp (tools/, council_dispatch_middleware/, council_hall/, scripts/). codex_cli_bridge.py and top-level *.py files are root-level modules of one file each.

#### public contract

The council_request / dispatch_mp_build / check_build tool signatures registered on the Koskadeux gateway.

#### runtime dependency

Entries in koskadeux-mcp requirements; the Codex CLI binary version is an OPERATIONAL dependency tracked in §C, not a runtime dependency in the Python sense.

#### config default

The signed exact-release runtime, with local Codex config/env required to match it exactly.

### §H.6 Adjudication

More restrictive classification wins; unresolvable disputes escalate to Max and the ruling is appended to §H.1.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A ticket fix needs an MP build in ai-market-backend. What is the first tool call?
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, session_id]
    weight: 0.09090909
  - id: I-02
    type: operate
    refs: [E-03]
    scenario: A connected schema offers MP mode=review. What is the correct response?
    expected_answers:
      - kind: human_action
        action: block release and remove the legacy MP review route; MP is builder-only
    weight: 0.09090909
  - id: I-03
    type: operate
    refs: [E-04]
    scenario: gpt-5.6 released this morning. What is the FIRST action of the swap?
    expected_answers:
      - kind: human_action
        action: verify availability on our Codex CLI auth tier via a smoke dispatch BEFORE any config change
    weight: 0.09090909
  - id: I-04
    type: isolate
    refs: [F-02]
    scenario: check_build says running for 12 minutes, no output, but the task usually takes 5. First action?
    expected_answers:
      - kind: human_action
        action: check ground truth in the build cwd (git log/status) before redispatching
    weight: 0.09090909
  - id: I-05
    type: isolate
    refs: [F-03]
    scenario: Structural build returned RepairExhaustedError; git log in cwd shows a fresh commit matching the chunk. What happened and what next?
    expected_answers:
      - kind: classification
        action: manifest-stage wrapper failure with delivered work; recover per agent-dispatch.md §U, do not rebuild
    weight: 0.09090909
  - id: I-06
    type: isolate
    refs: [F-08]
    scenario: Dispatch refused because the automatic child context envelope could not be verified. First action?
    expected_answers:
      - kind: human_action
        action: repair the exact activation runtime corpus or task-binding failure and retry the ordinary dispatch without caller references
    weight: 0.09090909
  - id: I-07
    type: repair
    refs: [G-07]
    scenario: A legacy MP review route modified a shared checkout. What do you do?
    expected_answers:
      - kind: human_action
        action: preserve and reconcile the unexpected work, reject the verdict, remove the legacy route, and prove MP review is rejected
    weight: 0.09090909
  - id: I-08
    type: repair
    refs: [G-06]
    scenario: SHA-pinned dispatch fails "object not available locally". Repair?
    expected_answers:
      - kind: human_action
        action: git fetch origin main in the target repo, then redispatch
    weight: 0.09090909
  - id: I-09
    type: evolve
    refs: [§H]
    scenario: Proposal — remove the fcntl mutex so MP and CC can run concurrently in different repos. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.09090909
  - id: I-11
    type: evolve
    refs: [§H]
    scenario: Proposal — add a retry wrapper that automatically redispatches an MP build once when check_build reports failed. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.09090909
  - id: I-10
    type: ambiguous
    refs: [§H, G-05]
    scenario: Proposal — bump MP_HARD_UPPER_BOUND_S from 1800 to 3600 for one giant migration build. Classify and name the safer alternative.
    expected_answers:
      - kind: classification
        verdict: REVIEW
        action: prefer per-dispatch timeout_s=3600 on that one build over changing the env default
    weight: 0.09090909
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1181
last_refresh_commit: d03c704
last_refresh_date: 2026-07-11T12:40:00Z
owner_agent: vulcan
refresh_triggers:
  - model swap (T-2026-000197 gpt-5.6 and any successor)
  - any change to codex_cli_bridge.py, _handle_call_mp, or the structural middleware
  - any new MP failure signature observed in production (add §F/§G rows same session)
  - runbook-gate semantics change (BQ-RUNBOOK-FIRST-ENFORCEMENT follow-ups)
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-08T23:45:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1181 / 2026-07-11T12:40:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
