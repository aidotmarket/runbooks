---
system_name: codex-mp
purpose_sentence: Operating manual for MP (Codex), the mandatory primary builder and reviewer of the Council — dispatch mechanics, configuration, timeouts, failure recovery, and the model-swap procedure.
owner_agent: vulcan
escalation_contact: Max (strategic forks, model-tier changes); Mars (structural middleware / runbook-gate internals)
lifecycle_ref: §J
authoritative_scope: MP/Codex dispatch paths, Codex CLI configuration and auth, MP timeout and mutex behavior, MP failure signatures and recoveries, MP model-swap procedure. NOT authoritative for the Council roster (infra:council-comms) or gate semantics (agent-dispatch.md, runbook-first gates).
linter_version: 1.0.0
---

# Codex / MP — Council Primary Builder

**MP** is the Council name for OpenAI **Codex** (model `gpt-5.6-sol`, ChatGPT OAuth). It is the **mandatory primary builder for all BQ/development code builds** and a standard cross-vote reviewer. Per Max ruling S1148: MP/Codex codes development projects; Claude Code (CC) handles trouble-ticket fixes only. MP never reviews its own builds (builder ≠ reviewer is a hard rule). Canonical roster and quirks: `infra:council-comms`; gate mechanics: `agent-dispatch.md`.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Legacy build dispatch (council_request mode=build, no dispatch_class) (S1148, T-113 fix via task 50f9dfad) | SHIPPED | `tools/agents.py:_handle_call_mp` | tests/regression/test_legacy_dispatch_unchanged.py | 2026-07-08 |
| Structural build dispatch (dispatch_class=structural, §O middleware) (S1150, end-to-end on 7ad740a4) | SHIPPED | `council_dispatch_middleware/ + tools/agents.py` | dispatch+AG suite (24/24 at S1131) | 2026-07-09 |
| Background dispatch + polling (S1148) | SHIPPED | `codex_cli_bridge.py:dispatch_codex_cli_streaming; council_request action=check_build` | covered by dispatch suite | 2026-07-08 |
| Review dispatch (mode=review, READ-ONLY advisory) (S1147 gate reviews) | SHIPPED | `tools/agents.py:_handle_call_mp` | see §F-06 caveat | 2026-07-07 |
| Spec authoring (mode=author, Gate 1) (S1147) | SHIPPED | `tools/agents.py:_handle_call_mp` | — | 2026-07-07 |
| Concurrency mutex (one Codex CLI at a time) (S1148, MP+CC serialized cleanly) | SHIPPED | `codex_cli_bridge.py:CODEX_LOCK_FILE (/var/tmp/koskadeux/codex_cli.lock, fcntl LOCK_EX)` | — | 2026-07-08 |
| Pre-push CI verification gate + auto-revert (S1150, manifest synthesis fix 25006e5e) | SHIPPED | `ci_verification.py (CI_WORKFLOW_TEST_PATHS)` | agent-dispatch.md §Q | 2026-07-09 |
| Runbook-refs dispatch gate (BLOCK mode) (S1150 block-mode live; resolver fix a3e71da9) | SHIPPED | `tools/runbook_ref.py:RunbookRefResolver; gate wired in tools/agents.py` | gate suite (S1146 BQ) | 2026-07-09 |
| Progress-based stall abort (S1111) | SHIPPED | `codex_cli_bridge.py (MP_PROGRESS_WINDOW_S=900)` | — | 2026-06-01 |
| Hard timeout backstop (env-tunable) (S1111 fix 995e1338) | SHIPPED | `.env MP_HARD_UPPER_BOUND_S=1800; envelope default in tools/agents.py:_build_mp_provider_envelope` | tests/regression/test_legacy_dispatch_unchanged.py | 2026-06-01 |
| dispatch_mp_build convenience wrapper | SHIPPED | `tools/agents.py:_handle_dispatch_mp_build` | — | 2026-06-01 |
| Codex CLI "goals" loop autonomy on long non-interactive builds (S827 probe: prefix harmless; loop engagement UNVERIFIED — see §F note) | PARTIAL | `/goal prefix accepted (codex exec)` | unverified on long builds | 2026-06-12 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Council dispatch handler | tools/agents.py:_handle_call_mp | task meta/output files under /var/tmp/koskadeux/; Event Ledger (review verdicts per agent-dispatch.md §S) | Koskadeux gateway (council_request tool), runbook gate (tools/runbook_ref.py), structural middleware | Routes mode=build/review/author/open_response; applies runbook-refs gate before dispatch (BLOCK mode since S1150). |
| Codex CLI bridge | codex_cli_bridge.py:run_codex_cli | CODEX_LOCK_FILE /var/tmp/koskadeux/codex_cli.lock (fcntl) | Codex CLI binary (codex exec) | Streaming path dispatch_codex_cli_streaming is production; nonstreaming legacy retained. OS-level timeout backstop from MP_HARD_UPPER_BOUND_S; progress-stall abort at MP_PROGRESS_WINDOW_S. Legacy dispatch_codex_cli (~L899) still contains a dead hardcoded `timeout 600` wrapper — zero live callers, remove on next bridge cleanup. |
| Codex CLI + auth | ~/.codex/config.toml | OAuth session (auth_mode: chatgpt) | OpenAI Codex service | model = "gpt-5.6-sol" (frontier-only policy; S1200 per Max directive, T-2026-000197). **The served string is `gpt-5.6-sol` — NOT `gpt-5.6`, NOT `gpt-5.6-codex`; both 400 on our ChatGPT account tier.** Two surfaces must agree: this file AND koskadeux-mcp/.env `MP_MODEL` (the bridge passes `-m MODEL` from the env explicitly). MCP servers deliberately removed from Codex config (62-tool overhead). CLI version at last verify: codex-cli 0.144.3. |
| Structural middleware (§O) | council_dispatch_middleware/ | builder-output manifests | ci_verification.py pre-push gate, SchemaRepair | Fires only when caller passes dispatch_class=structural. Terminal state push_failed is a DESIGNED guardrail: verified commit preserved, instance reviews then merges with KD_ALLOW_MAIN_PUSH=1 (S1150). |
| Runbook-refs gate | tools/runbook_ref.py:RunbookRefResolver | config:resource-registry (runbooks repo path); runbook_gate ledger events; config:runbook-gate-config | aidotmarket/runbooks checkout | BLOCK mode: mode=build/author REQUIRES runbook_refs (RunbookRef {path, section, synthesis} or Attestation {no_entry_found, subject, reason} — attestation creates dischargeable session debt). |
| Cost/pricing surfaces | council_dispatch_middleware/cost_estimator.py; kd_finance.py | MODEL_PRICING / DEFAULT_MODEL_RATES | — | Model swaps MUST update these alongside config (see §G-05). |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Dispatch MP build/review/author | council_request (agent=mp) | Koskadeux session (X-Agent-Caller, open session required) | COMPLETE |
| Vulcan/Mars | Poll background task | council_request (action=check_build, task_id) | same | COMPLETE |
| Vulcan/Mars | Convenience background build | dispatch_mp_build | same | COMPLETE |
| MP | Build/commit/push on Titan-1 repos | Codex CLI (codex exec) via bridge | Max's local git + gh credentials | COMPLETE |
| MP | Honor READ-ONLY in reviews | prompt-level only | — | PARTIAL — advisory, not enforced (S452); see §F-06. Closes via prompt prefix + post-review `git status` check. |
| CC (Claude Code) | Trouble-ticket fixes ONLY | council_request (agent=cc) | Max ruling S1148 (ledger dedupe_key=s1148-cc-ticket-dispatch-ruling) | COMPLETE — NOT a BQ build path; that remains MP. |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A BQ chunk or ticket fix needs a code build in a Titan-1 repo
  pre_conditions:
    - open Koskadeux session (kd_session_open + kd_session_plan done)
    - runbook_refs prepared (path+section must resolve in aidotmarket/runbooks; BLOCK mode)
    - target repo fetched (git fetch origin main) if the dispatch pins a SHA committed via GitHub API
    - spec committed at a pinned SHA when spec-grounded (agent-dispatch.md §T — reference path@SHA, never paste long specs)
  tool_or_endpoint: council_request(agent=mp, mode=build, task=..., cwd=<FULL macOS path>, session_id=..., runbook_refs=[...], timeout_s optional)
  argument_sourcing:
    cwd: config:resource-registry (full path — shorthand like "backend" is BROKEN, S347)
    runbook_refs: runbooks/TOPIC-ROUTER.md lookup; RunbookRef {path, section, synthesis}
    timeout_s: only if the build should exceed the env default; explicit per-dispatch wins over MP_HARD_UPPER_BOUND_S
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: '{task_id, status: dispatched|running} then check_build → {status: completed, result, ...}; MP reports branch/PR/commit'
    verification: git fetch + inspect the actual diff at file:line before accepting claims (builder output verification); run stated tests if in doubt
  expected_failures:
    - signature: 'RUNBOOK_REF_MISSING / RUNBOOK_REF_UNRESOLVED'
      cause: missing/unresolvable runbook_refs (see §F-08)
    - signature: 'gateway timeout on foreground dispatch >30s'
      cause: use background dispatch + check_build polling (§F-01)
  next_step_success: cross-review with builder excluded (DS/GLM standard; AG file-reading third for security 3/3), then merge; patch entity verdicts; same-session spec commit if gated
  next_step_failure: consult §F symptom table BEFORE diagnosing from code
- id: E-02
  trigger: A structural (middleware) build with CI gate + manifest is required
  pre_conditions:
    - everything in E-01
    - reconciliation subservice healthy OR bypass_reconcile with justification
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
  trigger: A diff needs an MP cross-review (MP was NOT the builder)
  pre_conditions:
    - MP is not the builder of the work under review
    - review prompt prefixed with explicit "DO NOT git add. DO NOT git commit. DO NOT git push. DO NOT modify any file. Report only."
  tool_or_endpoint: council_request(agent=mp, mode=review, dispatch_sha=<40-hex>, task=..., cwd=..., session_id=...)
  argument_sourcing:
    dispatch_sha: git rev-parse of the branch head under review
  idempotency: IDEMPOTENT
  expected_success:
    shape: verdict in the 6-value enum (APPROVE | APPROVE_WITH_NITS | APPROVE_WITH_MANDATES | REVISE | REQUEST_CHANGES | REJECT) + findings
    verification: run `git status` in cwd after the review — MP treats READ-ONLY as advisory (S452)
  expected_failures:
    - signature: silent past 300s with status still running
      cause: MP may have already delivered (§F-02); check ground truth before redispatching
  next_step_success: record verdict per agent-dispatch.md §S (gate-level fields, not per-chunk)
  next_step_failure: §F-02 ground-truth check
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
  next_step_success: update infra:council-comms agent_frontier_models.mp + provider status with evidence; refresh this runbook §B/§C rows + §J
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
| F-06 | READ-ONLY review modified/committed/pushed files | MP treats READ-ONLY as advisory and "helpfully" remediates (S452, observed repeatedly) | `git status` + `git log` in cwd immediately after review | §G-07 | CONFIRMED |
| F-07 | Second MP/CC dispatch appears hung at start | fcntl mutex serialization behind a running Codex CLI (deliberate) | `lsof /var/tmp/koskadeux/codex_cli.lock`; check_build on the other task |  | CONFIRMED |
| F-08 | Dispatch rejected RUNBOOK_REF_MISSING or RUNBOOK_REF_UNRESOLVED (failed_check path/section) | BLOCK-mode runbook gate: refs absent, path not a file under the runbooks repo, or section heading doesn't resolve; historical: registry file-as-repo-root bug (fixed a3e71da9) | run RunbookRefResolver locally in the koskadeux venv with the same refs; grep the runbook for the exact heading | §G-08 | CONFIRMED |
| F-09 | Structural build ends in push_failed though everything green | DESIGNED guardrail terminal state — verified commit preserved for instance review | inspect preserved commit | §G-09 | CONFIRMED |
| F-10 | All MP dispatches fail after a model/config change | Model string not served on auth tier; or partial swap left mismatched EXPECTED_MODELS / adapters | smoke dispatch asserting model_actual; full-tree grep for old string | §G-05 | CONFIRMED |
| F-11 | MP verdict/manifest claims don't match reality (files, line numbers, test counts) | Builder messages over-claim; also spec-over-prompt: MP follows the committed spec over a diverging dispatch prompt (S530 — usually MP is RIGHT) | manual diff inspection at file:line (mandatory on every fold); compare prompt vs spec text |  | CONFIRMED |
| F-12 | Canonical repo checkout found on detached HEAD after an MP review; a peer-held branch checkout silently abandoned | Review dispatched WITHOUT cwd: MP falls back to the canonical checkout and `git checkout <dispatch_sha>` moves its HEAD (S1175: Mars's spec branch checkout detached during vulcan's T-115 review; no data lost — branch was committed+pushed) | `git worktree list` + `git reflog -3` in the canonical checkout ("checkout: moving from <branch> to <sha>") | §G-10 | CONFIRMED |
| F-13 | Every MP dispatch 400s with `invalid_request_error`; `model_requested` shows an unintended model | Handler process predates a model-config rollback on disk: env is loaded at process start, so `~/.codex/config.toml` + `.env MP_MODEL` being correct on disk is NOT sufficient (S1184/S1185, incident 9180928d) | Model identity smoke (§G-11 step 1); compare handler `ps lstart` (LOCAL time — Titan-1 is CEST=UTC+2, convert before comparing to Z timestamps) against the config-change time | §G-11 | CONFIRMED |
| F-14 | All Codex sessions 401 Unauthorized on wss endpoints; `codex login status` = Not logged in | `~/.codex/auth.json` missing or its refresh-token chain burned ("refresh token was already used") — stale backups do NOT recover it because refresh tokens rotate | `ls ~/.codex/auth.json` + `codex login status` | §G-12 | CONFIRMED (S1185) |
| F-15 | MP repeatedly introduces new defects while fixing prior ones on a hard/safety-critical component (fix N creates defect N+1) | Default reasoning effort too low for the component's complexity | Count audit rounds: ≥2 REVISE rounds where the fix itself introduced a NEW defect (S1186 escalation spine: uuid4 dedup regression, ack leaks, benign-false storms) | §G-13 | CONFIRMED (S1186) |

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
  repair_entry_point: ~/.codex/config.toml (model line) + full-tree grep of koskadeux-mcp
  change_pattern: 'ORDER MATTERS (S673 lesson): (1) verify availability with a smoke dispatch; (2) FULL-TREE grep for the old model string FIRST — live code, adapters (council_config, ag/mp adapters, EXPECTED_MODELS in council_gate_runner), cost_estimator DEFAULT_MODEL_RATES/AGENT_DEFAULT_MODELS, kd_finance MODEL_PRICING, council_orchestrator MEMBERS, test fixtures; (3) swap config.toml + every live surface; ADD new pricing rows, keep historical rows; (4) update infra:council-comms agent_frontier_models.mp + mp_provider_status with evidence; (5) smoke build asserting model_actual + one cross-review leg; (6) refresh this runbook. Tracked precedent: T-2026-000197 (gpt-5.5→gpt-5.6, attempted S1181). RESOLVED (S1200, Max directive): MP is now on **gpt-5.6-sol** (koskadeux-mcp 4ca1f755). The S1181/S1184 loop was a STRING error, not an availability error — the model was there, the name was wrong. On our Codex ChatGPT OAuth tier: `gpt-5.6` -> HTTP 400 'not supported when using Codex with a ChatGPT account'; `gpt-5.6-codex` -> HTTP 400 same; `gpt-5.6-sol` -> HTTP 200. ALWAYS probe the exact string with a bare `codex exec --model <string>` BEFORE touching any code. The S1186 note's warning about residual latent gpt-5.6 fallbacks was RIGHT and the residue was WORSE than recorded: the S1184 rollback reverted config.toml + .env but NOT the code, leaving the unserved bare gpt-5.6 as the hardcoded default in FIVE live surfaces (mp_client.py, council_hall/agent_adapters.py, council_config.py, council_gate_runner.py EXPECTED_MODELS, council_orchestrator.py MEMBERS.mp) — inert only while env/config overrode them, and a 400 on the mandatory primary builder for any path that fell through. All aligned at 4ca1f755. **A rollback that touches only config is not a rollback.** Revert the code in the same change. LESSON (F-13): config-on-disk correct is NOT sufficient — the handler loads env at process start, so a swap is not live until the gateway reloads; always assert model_actual via smoke BEFORE any build.'
  rollback_procedure: revert the config.toml model line (env/config precedence makes this sufficient for immediate fallback); revert PR for code surfaces
  integrity_check: model_actual == intended on smoke dispatch; grep finds old string only in historical/pricing rows
- id: G-13
  symptom_ref: F-15
  component_ref: Codex CLI bridge (reasoning-effort dial)
  root_cause: default reasoning effort comes from ~/.codex/config.toml and is global; safety-critical or high-complexity dispatches need a stronger effort per-dispatch, and MP has repeatedly introduced regressions on hard components at default effort (S1186 escalation spine: 3 audit rounds)
  repair_entry_point: reasoning_effort parameter on call_mp / dispatch_mp_build (koskadeux-mcp 0bc68129, S1186)
  change_pattern: 'Pass reasoning_effort=<value> per dispatch. Model-agnostic enum: none | minimal | low | medium | high | xhigh (invalid → ValueError). OMIT it and behavior is unchanged — ~/.codex/config.toml governs exactly as before (backward compatible). When set, the bridge injects `-c model_reasoning_effort=<value>` into the codex exec args. xhigh is the ceiling on gpt-5.5; max/ultra require gpt-5.6. USE xhigh for safety-critical work (anything where a defect can silently drop an alert, lose money, or expose customer data) and for components where MP has previously regressed. NOTE: a newly merged dial does NOT take effect until the gateway reloads (both instances idle) — same F-13 trap as a model swap.'
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
  root_cause: READ-ONLY is prompt-level advisory for MP
  repair_entry_point: review prompt template + post-review check
  change_pattern: 'prefix EVERY MP review with: "DO NOT git add. DO NOT git commit. DO NOT git push. DO NOT modify any file. Report only." and run git status in cwd after; if MP committed anyway, git reset/revert the remediation and keep only the verdict'
  rollback_procedure: git reset --hard to pre-review SHA (verify nothing legitimate is lost)
  integrity_check: clean git status post-review
- id: G-08
  symptom_ref: F-08
  component_ref: Runbook-refs gate
  root_cause: refs must be structured objects whose path resolves to a real file under the registered runbooks repo and whose section matches a real heading
  repair_entry_point: dispatch arguments (runbook_refs)
  change_pattern: 'consult runbooks/TOPIC-ROUTER.md; pass [{path, section, synthesis}] with an EXACT existing heading (grep "^#" the runbook); if genuinely no entry exists, pass Attestation {no_entry_found: true, subject, reason} — this creates session debt discharged by a runbooks commit before close; never bypass the gate'
  rollback_procedure: n/a
  integrity_check: dispatch accepted; runbook_gate ledger event outcome RESOLVED
- id: G-09
  symptom_ref: F-09
  component_ref: Structural middleware (§O)
  root_cause: designed guardrail — middleware never pushes main itself
  repair_entry_point: instance review + push
  change_pattern: review the preserved verified commit, then KD_ALLOW_MAIN_PUSH=1 git push origin main (fast-forward only)
  rollback_procedure: git revert
  integrity_check: origin/main fast-forwarded to the verified commit
- id: G-10
  symptom_ref: F-12
  component_ref: Council dispatch handler
  root_cause: cwd omitted on a review dispatch — MP defaults to the canonical checkout and moves its HEAD to the dispatch SHA
  repair_entry_point: canonical checkout HEAD + dispatch discipline
  change_pattern: 'restore: git checkout <held-branch> in the canonical checkout after verifying `git status` clean and the branch tip is pushed (reflog shows what was abandoned); prevent: ALWAYS pass cwd on MP review dispatches, pointing at the branch worktree — never dispatch a repo review bare while any instance holds the canonical checkout'
  rollback_procedure: n/a
  integrity_check: canonical checkout back on the held branch, `git status -sb` clean, peer notified
- id: G-11
  symptom_ref: F-13
  component_ref: Koskadeux handler process (koskadeux_server.py) + Codex model config
  root_cause: model env/config loaded at handler start; a disk rollback does not reach a running process
  repair_entry_point: operator restart, then smoke
  change_pattern: '1) Model identity smoke: council_request(agent=mp, mode=open_response, task="Reply with exactly one line MODEL_ACTUAL=<model>"); assert raw_completion.model_requested AND model_actual equal the intended model (currently gpt-5.5; ignore the model prose self-description). 2) If wrong model, verify disk truth (grep model ~/.codex/config.toml; grep MP_MODEL koskadeux-mcp/.env; code fallbacks in tools/agents.py, mp_adapter.py, cost_estimator.py must agree), then restart the handler: launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp. Restart rule: peer must be idle/closed (check /var/tmp/koskadeux/registry.db sessions.state); kickstart is safe mid-OWN-session (tools reconnect; expect one brief EMERGENCY LOCAL FALLBACK shell response during the bounce). 3) Re-run the smoke before dispatching real work.'
  rollback_procedure: n/a (restart + config alignment)
  integrity_check: smoke returns success=true, model_requested=model_actual=intended, model_matched=true
- id: G-12
  symptom_ref: F-14
  component_ref: Codex CLI ChatGPT OAuth credential (~/.codex/auth.json)
  root_cause: credential file lost or refresh-token rotation chain broken; deletion vector undetermined S1185 (no koskadeux code touches the file)
  repair_entry_point: Max interactive re-login (AI instances CANNOT do this - browser OAuth on Max ChatGPT account)
  change_pattern: '1) Do NOT restore old auth.json backups as a fix: rotated refresh tokens fail with "refresh token was already used", and a stale file makes codex login status lie - remove any stale copy so status honestly reads Not logged in. 2) Ask Max to run on Titan-1: codex logout, then codex login, completing the browser sign-in. 3) Verify: codex login status = Logged in using ChatGPT; direct smoke: cd ai-market-backend && echo "Reply with exactly: SMOKE_OK" | codex exec --model gpt-5.5 -; then the G-11 handler smoke.'
  rollback_procedure: n/a
  integrity_check: direct smoke returns SMOKE_OK on the intended model AND handler smoke shows model_matched=true
```

## §H. Evolve

### §H.1 Invariants

- MP is the mandatory primary builder for BQ/development code builds; CC is ticket-fixes only (Max S1148); CC is NEVER a BQ/spec build path.
- Builder ≠ reviewer, always. Auth/security/customer-data/money changes require unanimous Council.
- Frontier-only model policy: MP runs exactly ONE configured model, the current OpenAI frontier (Max S516). No fallback tiers in production dispatch.
- Spec-grounded dispatches reference the committed spec path @ pinned SHA (agent-dispatch.md §T); never paste long specs inline.
- Gates are never bypassed with break_glass; the runbook gate's attestation/debt mechanism is the only sanctioned "no runbook" path.
- One Codex CLI at a time (fcntl mutex) — do not remove the lock to "parallelize".

### §H.2 BREAKING predicates

- Changes the council_request tool contract for agent=mp (argument names/shapes) without a shim.
- Removes or weakens the runbook-refs gate, the CI verification gate, or the builder≠reviewer rule.
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

~/.codex/config.toml values and koskadeux-mcp .env values named in §C.

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
        argument_keys: [agent, mode, task, cwd, session_id, runbook_refs]
    weight: 0.09090909
  - id: I-02
    type: operate
    refs: [E-03]
    scenario: MP must review a diff at branch head abc123... that GLM built. First tool call?
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, dispatch_sha, task, cwd, session_id]
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
    scenario: Dispatch rejected RUNBOOK_REF_UNRESOLVED failed_check=section. First action?
    expected_answers:
      - kind: human_action
        action: grep the cited runbook for exact headings and correct the section value
    weight: 0.09090909
  - id: I-07
    type: repair
    refs: [G-07]
    scenario: After an MP READ-ONLY review, git status shows a new commit by MP. What do you do?
    expected_answers:
      - kind: human_action
        action: reset/revert the unauthorized remediation, keep only the verdict, and note the S452 quirk in the review record
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
