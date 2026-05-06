# MCP Gateway

## What it does

Exposes the Koskadeux MCP server on Titan-1 to the public internet at `https://mcp.ai.market` so Vulcan (Claude on claude.ai) can call MCP tools from a hosted browser session. All MCP tool calls (`council_request`, `state_request`, `kd_session_*`, `shell_request`, `dispatch_mp_build`, etc.) flow through this path and are executed locally on Titan-1 against the user's filesystem, agents, and Council infrastructure.

**Public hostname:** `mcp.ai.market`
**Transport:** Tailscale Funnel (replaced Cloudflare Tunnel pre-S572 per `config:resource-registry`)
**Auth on the public surface:** OAuth (RFC 9728 — protected resource metadata at `/.well-known/oauth-protected-resource`)

## Architecture

```
Claude.ai (claude.ai/code, hosted browser)
  → https://mcp.ai.market           [Tailscale Funnel — public surface]
  → tailscaled on Titan-1           [terminates the funnel locally]
  → gateway_server.py :8767         [thin MCP-protocol proxy + OAuth]
  → HTTP POST localhost:8765/api/call
  → koskadeux_server.py :8765       [real handler — imports tools/agents.py]
  → tool execution (filesystem, agents, Council, Living State HTTP client → backend)
```

The split into two local processes is load-bearing. `gateway_server.py` is a thin MCP-protocol proxy: it terminates the public connection, refreshes its tool listing every ~60s from `/api/tools` on `:8765`, and forwards tool calls via `POST /api/call`. `koskadeux_server.py` is the real handler — `tools/agents.py` is imported here, so **code changes to tool handlers require restarting `koskadeux_server.py` specifically**, not the gateway. (Discovered S519; correction to earlier "kill gateway_server" memory rule.)

## Processes (all managed by launchd — auto-restart on crash)

| Process | Port | LaunchAgent label | Purpose |
|---------|------|-------------------|---------|
| `koskadeux_server.py` | 8765 | `com.koskadeux.mcp` | MCP REAL HANDLER — imports `tools/agents.py`. ALL tool implementations execute here. |
| `gateway_server.py` | 8767 | `com.koskadeux.gateway` | MCP-protocol proxy. Forwards to `:8765` via HTTP. Hardcodes `KOSKADEUX_URL=http://localhost:8765`. |
| `ag_server` (Gemini) | 8766 | `com.koskadeux.ag_server` | Council voter — Gemini (Vertex Express). Loopback only. |
| `deepseek_server` | 8768 | `com.koskadeux.deepseek_server` | Council voter — DeepSeek V4. Loopback only. |
| `lilly_server.py` | — | `com.koskadeux.lilly` | Companion service. |
| `council-hall` | — | `com.koskadeux.council-hall` | Council hall service. |

**Public exposure** is provided by `tailscaled` (Tailscale daemon), not by a `com.koskadeux.*` LaunchAgent. Funnel state for `mcp.ai.market` is managed by `tailscale funnel` / `tailscale serve` configuration on Titan-1; there is no app-level tunnel binary in the Koskadeux launchd tree. The legacy `com.koskadeux.cloudflared` agent is decommissioned (registry: "Tailscale Funnel has replaced Cloudflare for mcp.ai.market exposure"); SysAdmin follow-up is to remove the stale plist entirely.

**Plist locations** (all under `~/Library/LaunchAgents/`):
- `com.koskadeux.mcp.plist` → `python /Users/max/koskadeux-mcp/koskadeux_server.py` (logs `/tmp/koskadeux_mcp.log`)
- `com.koskadeux.gateway.plist` → `python /Users/max/koskadeux-mcp/gateway_server.py`
- `com.koskadeux.ag_server.plist` → `uvicorn ag_server:app --port 8766`
- `com.koskadeux.deepseek_server.plist` → `uvicorn deepseek_server:app --port 8768`

## Restart commands

Use `launchctl kickstart -k`. macOS `pkill -9` is unreliable here because launchd respawns the supervised processes immediately (PPID=1, KeepAlive=true), and silent re-kills cause confusion. The S520 correction supersedes the older `pkill` guidance.

```bash
# Restart the REAL handler (do this when tools/agents.py changed)
launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp

# Restart the proxy (rarely needed; clears proxy cache without touching handler state)
launchctl kickstart -k gui/$(id -u)/com.koskadeux.gateway

# Restart Council voters
launchctl kickstart -k gui/$(id -u)/com.koskadeux.ag_server
launchctl kickstart -k gui/$(id -u)/com.koskadeux.deepseek_server
```

After restarting `com.koskadeux.mcp`, in-memory session state (the checkpoint tracker) is wiped. The boot gate is enforced at the HTTP `/api/call` layer, so before any other tool call you must re-run:

```
kd_session_open  → kd_session_plan
```

Tailscale Funnel does not need an explicit restart for code changes; `tailscaled` keeps the public surface alive across `koskadeux_server` restarts. If the funnel itself is unhealthy, restart `tailscaled` (system daemon) and re-verify with `tailscale status` and `tailscale funnel status`.

## Verifying the path end-to-end

```bash
# 1. Local handler reachable on :8765
curl -s http://localhost:8765/api/tools | head -c 400

# 2. Local proxy reachable on :8767 and refreshing from :8765
curl -s http://localhost:8767/health

# 3. Public surface answering through Tailscale Funnel
curl -s -i https://mcp.ai.market/.well-known/oauth-protected-resource
# Expect 200 with the protected-resource metadata document.

# 4. Tailscale daemon healthy
tailscale status
tailscale funnel status
```

A path-failure usually localises by which step first stops returning 200.

## When it breaks

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| All MCP tools fail; `/api/tools` on `:8765` is fine | Gateway proxy stale or out of sync | `launchctl kickstart -k gui/$(id -u)/com.koskadeux.gateway` |
| All MCP tools fail; `/api/tools` on `:8765` errors or hangs | `koskadeux_server.py` wedged | `launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp`, then re-run `kd_session_open` + `kd_session_plan` |
| Code change to `tools/agents.py` not visible | Restarted the gateway, not the handler | Restart `com.koskadeux.mcp` (the handler imports `tools/agents.py`); proxy restart is not enough |
| `mcp.ai.market` returns 502/504 from claude.ai but `:8767` is healthy | Tailscale Funnel down or misrouted | `tailscale status`; `tailscale funnel status`; restart `tailscaled` (`sudo launchctl kickstart -k system/com.tailscale.tailscaled` on macOS) |
| `mcp.ai.market` returns 401/403 | OAuth-protected-resource flow rejected the bearer | Verify the OAuth metadata endpoint serves the expected issuer; re-auth from claude.ai |
| Tool calls return "checkpoint required" | Boot gate — session state wiped after a handler restart | Re-run `kd_session_open` then `kd_session_plan` before any other tool |
| `git push origin main` from `koskadeux-mcp` returns "Everything up-to-date" but no commit lands | Local `main` tracks `origin/HEAD` instead of `origin/main` | Use `git push origin HEAD:main`; verify with `git fetch origin && git log --oneline -3 origin/main` (S519) |
| Cannot restart remotely (Max away from Titan-1) | Public surface is the only path in | Tailscale SSH provides a backup admin path independent of the Funnel; see "Backup admin path" below |

## Backup admin path

The MCP gateway is the only path Vulcan has to issue tools, so when the gateway is dead Vulcan cannot restart it. Tailscale (the same product that provides the Funnel) also provides Tailscale SSH, which gives a persistent SSH path to Titan-1 independent of the Funnel surface. Use that to run `launchctl kickstart -k …` when the Funnel is healthy but the local handlers are wedged, or when the Funnel itself is degraded.

## Known issues

- **Handler restart wipes in-memory session state.** The checkpoint tracker is process-local; after `launchctl kickstart -k …com.koskadeux.mcp` the boot gate (enforced at the HTTP `/api/call` layer) requires `kd_session_open` + `kd_session_plan` before any other tool unlocks. Observed S485 during AC-R4-10.
- **MCP transport reconnection latency.** After a handler or gateway restart, claude.ai takes 5–15 minutes from the user's perspective to fully resync the tool listing. This is hosted-browser MCP behaviour, not a local fault.
- **"CHECKPOINT REQUIRED" looks like a transport failure.** From Claude's side, a boot-gate rejection and a transport drop produce similar surface errors. If `kd_recovery_write` also fails, it is transport — that tool is exempt from the gate.

## Connection health

Tailscale provides built-in connection health for the Funnel surface (`tailscale status`, `tailscale funnel status`); there is no separate watchdog needed for the public path. The earlier `cloudflared`-targeted watchdog placeholder is decommissioned with the transport. If finer-grained local-process health is desired, the right place is a check that polls `http://localhost:8767/health` and `http://localhost:8765/api/tools` directly and kicks the relevant LaunchAgent on failure.

## History

- **S225** — Checkpoint gate bumped 15→30; `session_open`/`session_close` exempted.
- **S226** — Gateway dropped 3x during a session. Root cause: stale connections (not the checkpoint gate; `kd_recovery_write` is exempt). Tailscale SSH backup path proposed.
- **S485** — `launchd_services` registry mapped: `com.koskadeux.mcp` (port 8765, real handler), `com.koskadeux.gateway` (proxy), `com.koskadeux.ag_server`, `com.koskadeux.lilly`, `com.koskadeux.council-hall`, plus the now-legacy `com.koskadeux.cloudflared`. Restart wipes in-memory session state.
- **S519** — Two-process architecture clarified: `gateway_server.py` is a proxy; `koskadeux_server.py` is the real handler that imports `tools/agents.py`. Restart pattern correction filed in registry under `process_architecture_s519`.
- **S520** — `pkill` restart pattern corrected to `launchctl kickstart -k -p gui/$(id -u)/com.koskadeux.mcp`. The handlers are launchd-supervised (PPID=1, KeepAlive=true) and respawn instantly after `pkill`, making the older guidance unreliable.
- **Pre-S572** — Tailscale Funnel migration replaced Cloudflare Tunnel as the `mcp.ai.market` public transport (per `config:resource-registry`: "Tailscale Funnel has replaced Cloudflare for mcp.ai.market exposure"). The `com.koskadeux.cloudflared` LaunchAgent is decommissioned and pending plist removal by SysAdmin.
- **S572** — Runbook fully rewritten to match the current Tailscale Funnel architecture (BQ-BACKEND-V2-PROXY-REAL-MCP-INTEGRATION-VERIFICATION §3.6).
