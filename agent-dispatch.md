# Agent Dispatch

## What it does

Routes tasks to the Council of Models (AG, MP, XAI) and Claude Code (CC) for builds. All dispatch goes through the unified `council_request` Koskadeux MCP tool.

## Agents

| Agent | Model | Dispatch | Default behavior |
|-------|-------|----------|------------------|
| AG | Gemini 3.1 Pro Preview | `council_request(agent=ag)` | **DEFAULTS TO ACTION** — treats every task as a build order. Always add "READ-ONLY — DO NOT modify any files" for non-build tasks. |
| MP | GPT-5.4 | `council_request(agent=mp)` | Analysis and review. Fully automated via Codex CLI. **Mandatory on ALL reviews.** |
| XAI | Grok 4.1 | `council_request(agent=xai)` | Architecture review, challenging assumptions. **Excluded from code audits** (fabricates line numbers/patterns). |
| CC | Claude Opus 4.6 | `council_request(agent=cc)` | Full filesystem builds, multi-file refactors. Always runs in background. |

## AG dispatch path (current as of S293)

```
council_request(agent=ag, task=..., cwd=...)
  → Koskadeux _handle_call_ag()
  → httpx.post("http://127.0.0.1:8766/api/task")  ← ag_server.py (paid Gemini API)
  → AntigravityClient.run_task()
  → Gemini SDK agentic loop (tool calls via MCP HTTP API on port 8765)
  → Returns result_text + token metrics
```

**Important:** AG runs through `ag_server.py` on port 8766 (LaunchAgent: `com.koskadeux.ag_server`), which uses the **paid Gemini API key** from Doppler. This bypasses the old free-tier CLI that had a 250 requests/day quota. The free-tier `antigravity_cli_bridge.py` is dead code — do not use it.

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

*Last updated: S293 (2026-03-19)*

## AG Vertex AI Auth (CRITICAL — do not revert)

AG uses **Vertex AI** via `VERTEX_API_KEY`, NOT the AI Studio `GEMINI_API_KEY`. The AI Studio key has a 250 req/day limit; Vertex AI has no daily cap.

**Auth priority in `antigravity_client.py`:**
1. `VERTEX_API_KEY` → Vertex AI with API key (preferred, no daily limits)
2. `GOOGLE_GENAI_USE_GCA=true` → Vertex AI with gcloud ADC
3. `GEMINI_API_KEY` → AI Studio (has daily quota limits — avoid)

**Where keys live:**
- `VERTEX_API_KEY` in `~/koskadeux-mcp/.env` (NOT in Doppler — .env is sourced by launch script)
- `launch_ag_server.sh` sources `.env` then falls back to Doppler for `GEMINI_API_KEY`

**If AG hits 429 RESOURCE_EXHAUSTED:**
1. Check `~/koskadeux-mcp/.env` has `VERTEX_API_KEY=AQ.Ab8...`
2. Check `launch_ag_server.sh` sources `.env` (not just Doppler)
3. Restart: `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.koskadeux.ag_server.plist && sleep 2 && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.koskadeux.ag_server.plist`
4. Verify: `curl http://localhost:8766/health`

**History:** Fixed S87, S155, S156, S305. Keep reverting because launch script only pulled from Doppler.
