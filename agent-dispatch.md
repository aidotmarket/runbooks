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
| DeepSeek | `deepseek-v4-pro` (frontier-only, S516 directive) | `council_request(agent=deepseek)` | **READ-ONLY ENFORCED during eval window** (2026-04-27 → ~2026-05-11). Direct-API today; full Council parity (server + tool surface + agentic loop) lands under BQ-COUNCIL-DEEPSEEK-SERVER-PARITY (Gate 1 APPROVED S516, Gate 2 chunking pending WRAPPER-RELAXED-MODE). |
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

## DeepSeek dispatch path (current as of S516)

```
council_request(agent=deepseek, task=..., mode=review)
  → Koskadeux _handle_call_deepseek()
  → Direct DeepSeek API call (https://api.deepseek.com/v1/chat/completions)
  → Strict review-schema validation (verdict + findings list)
  → Returns dict with result_text + token metrics
```

**Important — current state is NOT full Council voter parity.** Current DeepSeek dispatch is a direct-API call with strict-schema validation, no Koskadeux MCP gateway tools (no `state_request`, no `shell_request`, no filesystem, no git), no agentic loop. This is a known gap; full parity ships under `BQ-COUNCIL-DEEPSEEK-SERVER-PARITY` (Gate 1 APPROVED at spec SHA `54f1e0e`, S516).

### DeepSeek frontier-only policy (S516)

- **`infra:council-comms.deepseek.models.primary` = `deepseek-v4-pro`** — the sole production model.
- **`infra:council-comms.deepseek.models.primary_max_reasoning_alias` = `deepseek-v4-pro-max`** — available for tasks where maximum reasoning effort matters (Think Max mode).
- **BANNED aliases** (do not use):
  - `deepseek-v4-flash` — cost variant, OUT of scope per Max S516 directive
  - `deepseek-chat` — deprecated 2026-07-24 (currently points to v4-flash non-thinking)
  - `deepseek-reasoner` — deprecated 2026-07-24 (currently points to v4-flash thinking)
- Eval mode does NOT bypass the frontier-only rule.

### DeepSeek auth + secret management

- `DEEPSEEK_API_KEY` lives in **Infisical** at `infisical://secrets.ai.market/koskadeux-mcp/PROD/DEEPSEEK_API_KEY` (project ID `0943f641-faee-4324-b337-0d50c276e4a9`, env `prod`).
- **No `.env` fallback. No hardcoded literal. No alternative providers.** This is preventive defense-in-depth applied before any credential drift can happen (lessons from `BQ-AG-DISPATCH-DEFENSE-IN-DEPTH`).
- After Gate 2 ships: `launch_deepseek_server.sh` performs Infisical-only fetch and `deepseek_server.py` startup assertion fail-loud-crashes if the credential is absent.

### DeepSeek evaluation window (active S513 → ~S540)

- Started: 2026-04-27T07:40Z
- Expected end: 2026-05-11T07:40Z (14d) or earlier sample-size-bound (28d hard max: 2026-05-25)
- `infra:council-comms.deepseek.evaluation.active = true`
- `infra:council-comms.deepseek.read_only = true` enforced at three layers (router, DeepSeek client, XAI client) via `eval_active.is_deepseek_eval_active()` (cache TTL 60s)
- Cost caps: $1/dispatch, $10/day, $100/window
- Tracked in `BQ-COUNCIL-DEEPSEEK-EVALUATION` (Gate 2 APPROVED at 512490f).

### DeepSeek roadmap to full Council parity

`BQ-COUNCIL-DEEPSEEK-SERVER-PARITY` Gate 1 APPROVED S516. Gate 2 chunking sequenced after `BQ-COUNCIL-DISPATCH-WRAPPER-RELAXED-MODE` Gate 1 APPROVED. Five planned chunks:

1. `deepseek_server.py` skeleton + `/health` endpoint (FastAPI on port 8767)
2. Agentic loop with tool-fetching from `localhost:8765/api/tools`
3. Launch script + plist + Infisical integration (preventive AG-defense L1–L6 parity)
4. Dispatch wrapper rewire in `tools/agents.py:_handle_call_deepseek` + mode-aware response
5. Tests + CI workflow + this runbook updated to reflect server-routed dispatch

After Gate 2 build ships, the dispatch path becomes:

```
council_request(agent=deepseek, task=..., mode=review|author|build)
  → Koskadeux _handle_call_deepseek()
  → httpx.post("http://127.0.0.1:8767/api/task")  ← deepseek_server.py (DeepSeek API + MCP tools)
  → DeepSeek client agentic loop (tool calls via MCP HTTP API on port 8765)
  → Returns mode-aware result + token metrics
```

### DeepSeek known issues

- **Wrapper schema mismatch for non-review tasks (S514):** `deepseek_client.py` enforces strict review schema (verdict + findings list). Open-ended question authoring fails wrapper validation even when API returns 200 OK. Tracked under `BQ-COUNCIL-DISPATCH-WRAPPER-RELAXED-MODE` (Gate 1 R1 APPROVE_WITH_MANDATES, R2 in flight). Workaround during S514: direct API bypass for question-authoring tasks. Stop using bypass once Gate 2 of WRAPPER-RELAXED-MODE ships.
- **Council compliance gate (existing):** Council compliance gate enforces `read_only = true` at router/client layers during eval window. Do NOT attempt to bypass.

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
| CC compliance gate blocks | Gate 2 not passed in Living State | Check `state_get("build:bq-...")` gate2 status |
| CC missing `gh` | CC doesn't have GitHub CLI | Use `run_background` with PATH export for releases |

---

*Last updated: S516 (2026-04-27) — added DeepSeek dispatch section + frontier-only model policy + BQ-AG-DEFENSE-IN-DEPTH revocation note. Prior: S363 (2026-04-01) added AG Vertex AI auth section.*

## AG Vertex AI Auth (CRITICAL — do not revert)

AG uses **Vertex AI** via `VERTEX_API_KEY`, NOT the AI Studio `GEMINI_API_KEY`. The AI Studio key has a 250 req/day limit; Vertex AI has no daily cap.

**Auth priority in `antigravity_client.py`:**
1. `VERTEX_API_KEY` → Vertex AI with API key (preferred, no daily limits)
2. `GOOGLE_GENAI_USE_GCA=true` → Vertex AI with gcloud ADC
3. `GEMINI_API_KEY` → AI Studio (has daily quota limits — avoid)

**Where keys live (Infisical-first, as of S363):**
- `VERTEX_API_KEY` in **Infisical** (prod env) — primary source, pulled by `launch_ag_server.sh` at startup
- `VERTEX_API_KEY` in `~/koskadeux-mcp/.env` — fallback only (sourced before Infisical overrides)
- `GEMINI_API_KEY` in **Infisical** (prod env) — AI Studio key. The key is intentionally left in Infisical per Max S516 classification (regression hazard, not security breach, not active production blocker). AG R1 cross-review of BQ-AG-DISPATCH-DEFENSE-IN-DEPTH flagged this as a HIGH (only environment-level revocation fully defends against stale-branch checkout); Max chose to drop the GCP revocation and accept the residual hazard given AG runs cleanly on `VERTEX_API_KEY`. The original code-only L2 (strip the key fetch from `launch_ag_server.sh`) is still in scope for that BQ's Gate 2 build; AC8-equivalent (defense survives stale-branch checkout) is downgraded to best-effort.
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
