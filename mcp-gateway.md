# MCP Gateway

## What it does

Connects Vulcan (Claude) to Titan-1 via Cloudflare tunnel. All MCP tool calls (run_command, call_mp, state_get, etc.) flow through this gateway.

## Architecture

```
Claude (claude.ai)
  → mcp.ai.market (Cloudflare tunnel)
  → gateway_server.py (port 8767, Titan-1)
  → koskadeux_server.py (port 8765, Titan-1)
  → Tool execution (filesystem, API calls, agents)
```

## Processes (all managed by launchd — auto-restart on crash)

| Process | Port | LaunchAgent | Purpose |
|---------|------|-------------|---------|
| `koskadeux_server.py` | 8765 | `com.koskadeux.mcp` | MCP tool server (57+ tools) |
| `gateway_server.py` | 8767 | `com.koskadeux.gateway` | Gateway/proxy |
| `cloudflared tunnel` | — | `com.koskadeux.cloudflared` | Tunnel to mcp.ai.market |

## Restart commands

```bash
# Restart gateway + tunnel (launchd auto-restarts both)
pkill -f gateway_server.py; pkill -f 'cloudflared tunnel'

# Restart MCP server itself
pkill -f koskadeux_server.py

# Nuclear: restart everything
pkill -f koskadeux_server.py; pkill -f gateway_server.py; pkill -f 'cloudflared tunnel'
```

Wait 5-10 seconds after restart for processes to come up and tunnel to connect.

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| All MCP tools return errors | Gateway stale (most common) | `pkill -f gateway_server.py; pkill -f 'cloudflared tunnel'` |
| All MCP tools return errors | Gateway transport dead | Restart gateway: `pkill -f gateway_server.py; pkill -f "cloudflared tunnel"` |
| Tools work briefly then die | Gateway degrades under load after ~45 min | Restart gateway |
| MCP works but MP/AG fail | Agent-specific issue, not gateway | Check agent logs |
| Can't restart (remote) | No backup access path | Need Tailscale (see below) |

## The chicken-and-egg problem

When the MCP gateway dies, Vulcan can't issue restart commands because the restart command needs the gateway. If Max is remote, there is no backup path.

**Fix: Tailscale SSH** — install Tailscale on Titan-1 for persistent SSH access independent of the Cloudflare tunnel. See Tailscale backup plan (S226).

## Watchdog (planned, not yet built)

```bash
#!/bin/bash
# /usr/local/bin/mcp-watchdog.sh
# Run every 60s via LaunchAgent
if ! curl -s --max-time 5 http://localhost:8767/health > /dev/null 2>&1; then
    logger "MCP gateway unhealthy, restarting"
    pkill -f gateway_server.py
    pkill -f 'cloudflared tunnel'
fi
```

## Known issues

- Gateway connections degrade silently after extended heavy use (~45 min). Launchd only restarts on crash, not on stale connections.
- Checkpoint gate messages ("CHECKPOINT REQUIRED") look identical to transport failures from Claude's side. If kd_recovery_write also fails, it's transport, not the gate.
- MCP transport reconnection after gateway restart takes 5-15 minutes from Claude's perspective.

## History

- S225: Checkpoint gate bumped 15→30, session_open/close exempted
- S226: Gateway dropped 3x during session. Root cause: stale connections (not checkpoint gate — kd_recovery_write IS exempt). Tailscale backup proposed.
