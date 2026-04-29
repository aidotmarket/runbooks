# Agent Dispatch

## What it does

Routes tasks to the Council of Models (AG, MP, XAI) and Claude Code (CC) for builds. All dispatch goes through the unified `council_request` Koskadeux MCP tool.

## Model Selection Policy (S516 — FRONTIER ONLY)

Each Council agent runs **exactly one configured model**: the current provider frontier. No tiered fallbacks, no fast/cheap variants in production dispatch. Eval mode does NOT bypass this — cost concerns are filed as separate BQs rather than silently routing to a lower tier.

The canonical source of truth is `infra:council-comms.model_policy.agent_frontier_models` (Living State). This runbook reflects that registry. If they disagree, **the registry wins** and this runbook is stale.

Tracked under `BQ-MODEL-REGISTRY-CENTRALIZATION` (P1, planned) — extends structured `models.primary` registration to AG/MP/XAI (currently only DeepSeek registered structurally) and adds CI gates against hardcoded model strings outside the registry-fetch path.

## Agents

| Agent | Model (frontier) | Dispatch | Default behavior |
|-------|------------------|----------|------------------|
| AG | `gemini-3.1-pro-preview` (Vertex AI) | `council_request(agent=ag)` | **DEFAULTS TO ACTION** — treats every task as a build order. Always add "READ-ONLY — DO NOT modify any files" for non-build tasks. |
| MP | `gpt-5.5` (Codex CLI / ChatGPT OAuth) | `council_request(agent=mp)` | Analysis and review. Fully automated via Codex CLI. **Mandatory on ALL reviews.** |
| XAI | `grok-4-1-fast-reasoning` (TENTATIVE — verification pending under BQ-MODEL-REGISTRY-CENTRALIZATION) | `council_request(agent=xai)` | Architecture review, challenging assumptions. **Excluded from code audits** (fabricates line numbers). |
| DeepSeek | Registry-resolved primary alias (frontier-only, S516 directive) | `council_request(agent=deepseek)` | **READ-ONLY ENFORCED during eval window** (2026-04-27 → ~2026-05-11). Server-routed through `deepseek_server.py` on port 8768 with MCP tool surface and mode-aware envelopes. |
| CC | `claude-opus-4-7` (Claude Opus 4.7) | `council_request(agent=cc)` | Full filesystem builds, multi-file refactors. Always runs in background. |

## AG dispatch path (current as of S293)

```
council_request(agent=ag, task=..., cwd=...)
  → Koskadeux _handle_call_ag()
  → httpx.post("http://127.0.0.1:8766/api/task")  ← ag_server.py (paid Gemini API)
  → AntigravityClient.run_task()
  → Gemini SDK agentic loop (tool calls via MCP HTTP API on port 8765)
  → Returns result_text + token metrics
```

**Important:** AG runs through `ag_server.py` on port 8766 (LaunchAgent: `com.koskadeux.ag_server`), which uses the **paid Vertex AI API key** from Infisical. This bypasses the old free-tier CLI that had a 250 requests/day quota. The free-tier `antigravity_cli_bridge.py` is dead code — do not use it.

### AG safety rules

- AG defaults to action — every task is treated as a build order
- Non-build requests (audits, reviews, analysis) **MUST** include: `READ-ONLY — DO NOT modify any files.`
- Always run `git diff --stat` after AG tasks to verify what changed
- 2-Strike rule: stop after 2 consecutive failures → consult Vulcan

### AG known issues (fixed S293)

**History compaction bug (FIXED):** `_compact_chat_history()` was running between Gemini's function_call and the function_response, breaking the SDK's strict conversation ordering rule. Error: `400 INVALID_ARGUMENT: function response turn must immediately follow function call turn`. Fix: moved compaction to start of each turn loop. Commit `fe7a99e`.

**Fake system_notice (FIXED):** BQ-044's soft ceiling injected a `Part.from_function_response(name="system_notice")` for a function Gemini never called — another ordering violation. Fix: inject notice into the last real tool output's response dict instead. Same commit.

### AG empty responses after tool use

If AG completes tool calls but returns an empty `result_text`, the likely cause is:
1. **ag_server still running old code** — restart: `pkill -f ag_server.py` (launchd auto-restarts)
2. **Token budget exhausted** — check `total_input_tokens + total_output_tokens` in response
3. **Gemini went silent** — the client sends a synthesis prompt ("provide your complete text response") as a fallback

## MP dispatch path (current as of S286)

```
council_request(agent=mp, task=...)
  → Koskadeux _handle_call_mp()
  → Codex CLI (~/koskadeux-mcp/dispatch_codex_cli.py)
  → Config: ~/.codex/config.toml (auth_mode: chatgpt, model: gpt-5.4)
  → Returns response text + metrics
```

**Important:** The old `call_mp` API endpoint is dead (returns 401). MP is fully automated via the Codex CLI with ChatGPT OAuth authentication. No manual paste workflow needed.

### MP known issues

- **Gateway timeout:** `council_request(agent=mp)` times out on tasks >30s. Use `dispatch_mp_build` (background) for anything substantial like builds or long reviews.
- **MCP server removed** from Codex config to prevent 62-tool overhead per API call.

## XAI dispatch

```
council_request(agent=xai, task=...)
  → Koskadeux _handle_call_xai()
  → xai_client.py (chat/completions API)
  → Returns response text
```

### XAI rules

- **EXCLUDED from code audits** — XAI fabricates line numbers, code patterns, and findings when auditing code without direct tool access. Treat XAI code audit findings as zero analytical weight unless independently verified.
- Strong on high-level architecture and assumption challenges
- Mandatory dissent voice in Council design reviews (Gate 1)
- For Gate 3 when 4/4 unanimous is needed (security/money): include XAI but scope to architecture-only review

## DeepSeek Council Voter (server-routed, current as of S527)

```
council_request(agent=deepseek, task=..., mode=review|open_response)
  → Koskadeux _handle_call_deepseek()
  → httpx.post("http://127.0.0.1:8768/api/task")  ← deepseek_server.py
  → DeepSeek client agentic loop (tool calls via MCP HTTP API on port 8765)
  → Returns mode-aware result + token metrics
```

**Important:** DeepSeek is now routed through `deepseek_server.py` on port `8768` (LaunchAgent: `com.koskadeux.deepseek_server`). Do not add or use any alternate DeepSeek dispatch path; the server is the canonical Council voter path.

### DeepSeek frontier-only policy (S516)

- **`infra:council-comms.deepseek.models.primary`** resolves the sole production model alias. The registry wins over environment variables and runbook text.
- **`infra:council-comms.deepseek.models.primary_max_reasoning_alias` = `deepseek-v4-pro-max`** — available for tasks where maximum reasoning effort matters (Think Max mode).
- **BANNED aliases** (do not use):
  - `deepseek-v4-flash` — cost variant, OUT of scope per Max S516 directive
  - `deepseek-chat` — deprecated 2026-07-24 (currently points to v4-flash non-thinking)
  - `deepseek-reasoner` — deprecated 2026-07-24 (currently points to v4-flash thinking)
- Eval mode does NOT bypass the frontier-only rule.

### DeepSeek auth + secret management

- `DEEPSEEK_API_KEY` lives in **Infisical** at `infisical://secrets.ai.market/koskadeux-mcp/PROD/DEEPSEEK_API_KEY` (project ID `0943f641-faee-4324-b337-0d50c276e4a9`, env `prod`).
- `scripts/launch_deepseek_server.sh` fetches only that Infisical project/env/path (`/`) and exports the key before starting the server.
- **No `.env` fallback. No hardcoded literal. No alternative providers.** `deepseek_server.py` performs a startup auth/model probe and exits non-zero before binding port `8768` if credentials or registry resolution fail.

### DeepSeek safety rules

- **READ-ONLY normalization:** during the active eval window, DeepSeek may run `mode=review` and `mode=open_response`; write-capable build/author modes stay blocked by the router and client-side read-only filters.
- **Tool safety:** review-mode tool exposure is normalized to read-only MCP tools. Write tools are not offered for review dispatch.
- **Parallel fallback latch:** native parallel tool calls may run only after the probe path allows them. Transient gateway/provider failures latch the dispatch back to serial tool execution for the current request.
- **Registry-resolved model alias:** production dispatch uses `infra:council-comms.deepseek.models.primary`; do not hardcode or silently override the alias in launch scripts or wrapper code.

### DeepSeek mode examples

```json
{"agent": "mp", "mode": "open_response", "task": "Summarize the release risk in one paragraph."}
```

```json
{"agent": "ag", "mode": "open_response", "task": "READ-ONLY -- DO NOT modify any files. Explain the likely failing test."}
```

```json
{"agent": "xai", "mode": "open_response", "task": "Challenge the architecture assumptions for this gate."}
```

```json
{"agent": "deepseek", "mode": "open_response", "task": "Answer as a Council voter without strict review JSON."}
```

### DeepSeek evaluation window (active S513 → ~S540)

- Started: 2026-04-27T07:40Z
- Expected end: 2026-05-11T07:40Z (14d) or earlier sample-size-bound (28d hard max: 2026-05-25)
- `infra:council-comms.deepseek.evaluation.active = true`
- `infra:council-comms.deepseek.read_only = true` enforced at router, wrapper, server tool-filter, and client layers via `eval_active.is_deepseek_eval_active()` (cache TTL 60s)
- Cost caps: $1/dispatch, $10/day, $100/window
- Tracked in `BQ-COUNCIL-DEEPSEEK-EVALUATION` (Gate 2 APPROVED at 512490f).

### DeepSeek known issues

- **Review mode remains strict:** `mode=review` must return the strict review envelope (`verdict`, `findings`, `summary`). Use `mode=open_response` for plain text.
- **Tool probe Branch B fallback:** if the native tool-use probe logs repeated transient failures or provider rejection, `deepseek_server.py` logs Branch B fallback details and uses the emulated/serial path instead of exiting. Check `/var/tmp/koskadeux/deepseek_server.log` and `/var/tmp/koskadeux/deepseek_server_error.log` for `DeepSeek tool probe`, `mode=emulated`, and `requires_chunk=B3`.
- **Council compliance gate (existing):** Council compliance gate enforces `read_only = true` during eval window. Do NOT attempt to bypass.

## CC builds

```
council_request(agent=cc, task=..., cwd=..., bq_code=...)
  → Always runs in background → returns task_id
  → Check progress: council_request(action=check_build, task_id=...)
  → List all: council_request(action=list_builds)
```

- Auto-pushes to main after tests pass (post-commit hooks)
- Compliance gate (`council_compliance_gate.py`) blocks dispatch if Gate 2 not passed
- CC does **NOT** have `gh` (GitHub CLI) in PATH — never use CC for VZ releases
- `run_background` does NOT inherit PATH — always prefix with `export PATH="/opt/homebrew/bin:$PATH"`

## Council gates

| Gate | When | Who reviews | Threshold |
|------|------|-------------|-----------|
| Gate 1 (Design) | Before spec | All 4 voters (AG, MP, XAI, Vulcan) | 3/4 majority |
| Gate 2 (Spec) | Before build | All 4 voters | 3/4 majority |
| Gate 3 (Audit) | After build | Min 2 reviewers (AG+MP mandatory on schema/security) | 3/4 majority |

- **4/4 unanimous** required for: security, auth, payments, money flows
- **CRITICAL veto** by any brain → halts process, escalates to Max
- 3 rounds max per gate
- XAI excluded from Gate 3 code audits (architecture-only if included for vote count)

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| AG returns empty response | ag_server running stale code | `pkill -f ag_server.py` (auto-restarts) |
| AG 400 INVALID_ARGUMENT | History compaction bug (pre-S293) | Update `antigravity_client.py` from main |
| AG 429 RESOURCE_EXHAUSTED | Gemini quota hit | Exponential backoff built in (3 retries). If persistent, check billing. |
| MP 401 / connection refused | Using dead `call_mp` API | Use `council_request(agent=mp)` (Codex CLI path) |
| MP timeout | Task too long for sync dispatch | Use `dispatch_mp_build` for background |
| XAI fabricated findings | XAI auditing code without tool access | Never trust XAI code-level citations. Verify independently. |
| DeepSeek health probe fails | Missing Infisical credential or registry lookup failure | Check `launchctl print gui/$(id -u)/com.koskadeux.deepseek_server`, `/var/tmp/koskadeux/deepseek_server_error.log`, and Infisical project `0943f641-faee-4324-b337-0d50c276e4a9` env `prod` path `/` |
| DeepSeek tool probe falls back | Provider/gateway transient errors or native tool-call rejection | Check `/var/tmp/koskadeux/deepseek_server.log` for `DeepSeek tool probe`, `mode=emulated`, `requires_chunk=B3`, and Branch B fallback details |
| DeepSeek review rejects plain text | `mode=review` requires strict review JSON | Use `mode=open_response` for plain text Council answers |
| CC compliance gate blocks | Gate 2 not passed in Living State | Check `state_get("build:bq-...")` gate2 status |
| CC missing `gh` | CC doesn't have GitHub CLI | Use `run_background` with PATH export for releases |

---

*Last updated: S527 (2026-04-29) — updated DeepSeek to server-routed Council voter path on port 8768, added open_response examples, safety rules, and Branch B fallback troubleshooting. Prior: S516 (2026-04-27) added DeepSeek dispatch section + frontier-only model policy + BQ-AG-DEFENSE-IN-DEPTH revocation note. Prior: S363 (2026-04-01) added AG Vertex AI auth section.*

## AG Vertex AI Auth (CRITICAL — do not revert)

AG uses **Vertex AI** via `VERTEX_API_KEY`, NOT the AI Studio `GEMINI_API_KEY`. The AI Studio key has a 250 req/day limit; Vertex AI has no daily cap.

**Auth priority in `antigravity_client.py`:**
1. `VERTEX_API_KEY` → Vertex AI with API key (preferred, no daily limits)
2. `GOOGLE_GENAI_USE_GCA=true` → Vertex AI with gcloud ADC
3. `GEMINI_API_KEY` → AI Studio (has daily quota limits — avoid)

**Where keys live (Infisical-first, as of S363):**
- `VERTEX_API_KEY` in **Infisical** (prod env) — primary source, pulled by `launch_ag_server.sh` at startup
- `VERTEX_API_KEY` in `~/koskadeux-mcp/.env` — fallback only (sourced before Infisical overrides)
- `GEMINI_API_KEY` — **REVOKED at GCP and DELETED from Infisical (S516, 2026-04-27).** The Mar 30 2026 AI Studio API key was deleted at GCP Console; the Infisical entry was removed in the same session. Any stale-branch checkout that runs `launch_ag_server.sh` will get an empty value from the Infisical fetch, and even if a value were somehow present, the underlying GCP key no longer exists — auth would fail loudly. The Vertex Express key (`VERTEX_API_KEY`, bound to `vertex-express@aimarket-prod`) was rotated in the same session to a new value ending `...YuHA` after a misconfigured restriction broke AG dispatch (recovery took ~30 min). Defense-in-depth posture per BQ-AG-DISPATCH-DEFENSE-IN-DEPTH AC8 (defense survives stale-branch checkout) is now **ACTIVE** (was best-effort before S516).
- `launch_ag_server.sh` lives at `~/koskadeux-mcp/scripts/launch_ag_server.sh`

**Key sourcing order in `launch_ag_server.sh`:**
1. Sources `~/koskadeux-mcp/.env` for non-secret config
2. Fetches `VERTEX_API_KEY` from Infisical → overrides `.env` value if found
3. Falls back to `GEMINI_API_KEY` from Infisical only if not in `.env`

**If AG hits 429 RESOURCE_EXHAUSTED:**
1. Verify Infisical has `VERTEX_API_KEY`: `infisical secrets get VERTEX_API_KEY --plain --env prod --domain https://secrets.ai.market --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c`
2. Verify `.env` fallback: `grep VERTEX_API_KEY ~/koskadeux-mcp/.env`
3. Restart: `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.koskadeux.ag_server.plist && sleep 2 && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.koskadeux.ag_server.plist`
4. Verify: `curl http://localhost:8766/health`

**History:** Fixed S87, S155, S156, S305. S363: migrated key sourcing from .env-only to Infisical-first.
