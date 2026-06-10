# Koskadeux MCP — Gateway, Server, Transport & Session Lifecycle

> Canonical operations runbook for the **internal Koskadeux MCP** that the two Claude
> instances (Vulcan + Mars, peers) drive Titan-1 through. For the **public/customer** MCP
> that exposes marketplace tools to external LLM clients, see `aimarket-mcp-server.md` —
> that is a different system.
>
> Consolidates the former `session-lifecycle.md` (now a stub pointing here). A future
> §A–§K-conformant, possibly repo-local edition is tracked by the runbook-decentralization
> and autonomous-operations BQs; the central-vs-service location + final name are decided
> there. Until then this central runbook is authoritative. Filename kept as `mcp-gateway.md`
> deliberately so that gated relocation owns the rename.

## What it is

Exposes the Koskadeux MCP server on Titan-1 at `https://mcp.ai.market` so the hosted Claude
instances (Vulcan = primary slot, Mars = worker slot) can call MCP tools from a hosted
browser session. All tool calls (`council_request`, `state_request`, `kd_session_*`,
`shell_request`, `dispatch_mp_build`, etc.) execute locally on Titan-1 against the
filesystem, agents, Council infrastructure, and Living State.

- **Public hostname:** `mcp.ai.market`
- **Transport:** **Cloudflared** (Cloudflare Tunnel) — NOT Tailscale Funnel. See "Transport: why cloudflared" below.
- **Auth on the public surface:** OAuth (RFC 9728 — protected-resource metadata at `/.well-known/oauth-protected-resource`)

## Architecture

```
Claude.ai (hosted browser — Vulcan primary + Mars worker)
  → https://mcp.ai.market           [Cloudflare Tunnel — public surface]
  → cloudflared on Titan-1          [com.koskadeux.cloudflared: `cloudflared tunnel run koskadeux`]
  → gateway_server.py :8767         [thin MCP-protocol proxy + OAuth]
  → HTTP POST localhost:8765/api/call
  → koskadeux_server.py :8765       [REAL handler — imports tools/agents.py]
  → tool execution (filesystem, agents, Council, Living State HTTP client → backend)
```

The split into two local processes is load-bearing (S519). `gateway_server.py` is a thin
MCP-protocol proxy: it terminates the public connection, refreshes its tool listing ~60s
from `/api/tools` on `:8765`, and forwards calls via `POST /api/call`. `koskadeux_server.py`
is the real handler — `tools/agents.py` is imported here, so **code changes to tool
handlers require restarting `koskadeux_server.py` (`com.koskadeux.mcp`), not the gateway.**

## Processes (launchd-managed — auto-restart on crash; plists under `~/Library/LaunchAgents/`)

| Process | Port | LaunchAgent label | Purpose |
|---|---|---|---|
| `koskadeux_server.py` | 8765 | `com.koskadeux.mcp` | REAL HANDLER — imports `tools/agents.py`; all tool implementations execute here. |
| `gateway_server.py` | 8767 | `com.koskadeux.gateway` | MCP-protocol proxy → `:8765` via HTTP (`KOSKADEUX_URL=http://localhost:8765`). |
| `cloudflared` | — | `com.koskadeux.cloudflared` | **Public transport for `mcp.ai.market`** (`cloudflared tunnel run koskadeux`). LOAD-BEARING — do not remove. |
| `ag_server` | 8766 | `com.koskadeux.ag_server` | Council voter — Gemini (Vertex). Loopback only. |
| `deepseek_server` | 8768 | `com.koskadeux.deepseek_server` | Council voter — DeepSeek. Loopback only. |
| `lilly_server.py` | — | `com.koskadeux.lilly` | Companion service. |
| `council-hall` | — | `com.koskadeux.council-hall` | Council hall service. |

## Transport: why cloudflared (not Tailscale Funnel)

The live public surface for `mcp.ai.market` is **cloudflared** (`com.koskadeux.cloudflared`,
running `cloudflared tunnel run koskadeux`). A Tailscale Funnel migration was *attempted*
pre-S572 and was recorded in `config:resource-registry` and older docs as complete — **it
never completed.** S688 verification: `launchctl list | grep cloudflared` shows the agent
active, and `mcp.ai.market` DNS resolves through `*.cfargotunnel.com` (a Cloudflare Tunnel
address, not Tailscale). The resource-registry "Tailscale replaced Cloudflare" claim is
**stale**; the canonical transport reference is `cloudflare-and-dns.md` (drift items #1, #5).
Older guidance that points at `tailscale funnel status` is wrong for this path — use the
cloudflared path. **Do not remove the `com.koskadeux.cloudflared` plist.**

## Restart commands

Use `launchctl kickstart -k` — NOT `pkill`. The handlers are launchd-supervised (PPID=1,
KeepAlive=true) and respawn instantly after `pkill`, which makes the older `pkill` guidance
unreliable (S520 correction).

```bash
# Real handler (do this when tools/agents.py or any tool handler changed)
launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp

# Proxy (rarely needed; clears proxy cache without touching handler state)
launchctl kickstart -k gui/$(id -u)/com.koskadeux.gateway

# Public transport (if mcp.ai.market is unreachable but :8767 is healthy)
launchctl kickstart -k gui/$(id -u)/com.koskadeux.cloudflared

# Council voters
launchctl kickstart -k gui/$(id -u)/com.koskadeux.ag_server
launchctl kickstart -k gui/$(id -u)/com.koskadeux.deepseek_server
```

**Verify the restart actually bounced the process — `kickstart` can silently no-op.**
`launchctl kickstart -k` returns exit 0 (the command "fired") even when it does NOT replace
the running process: the old PID keeps serving the old code, so a code change looks like it
never landed. ALWAYS confirm the PID changed before declaring the new code live (S766 boot-path
activation lesson — a launchctl restart reported "fired" yet the old process kept running):

```bash
# Capture PID, kickstart, confirm a DIFFERENT PID is now serving
OLD=$(launchctl list | awk '/com\.koskadeux\.mcp/{print $1}')
launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp
sleep 2
NEW=$(launchctl list | awk '/com\.koskadeux\.mcp/{print $1}')
echo "pid $OLD -> $NEW"   # MUST differ; if equal, the restart no-opped — re-run kickstart
```

### Restarting/redeploying the handler FROM INSIDE a session (S807 pattern)

A shell_request command executes inside the `com.koskadeux.mcp` process tree, so a deploy
script that stops the handler will kill itself unless it is detached into a NEW process
session. Two traps, both hit S807:

1. **`setsid` does not exist on macOS.** A `nohup setsid script &` launcher dies instantly
   and silently (no log file is ever created). Detach with Python instead:

   ```bash
   /usr/bin/python3 -c "import subprocess; subprocess.Popen(['/path/to/deploy.sh'], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)"
   ```

2. **`nohup ... &` alone is NOT enough** — it does not change the process group, and
   `launchctl bootout` tears down the service's process group.

Deploy script shape: log everything to a file under /var/tmp/koskadeux/, `sleep 3` first
(lets the parent tool call return), `launchctl bootout` (real stop — `kickstart -k` is a
restart and leaves no migration window), run migrations, `launchctl bootstrap` the plist
back, then verify the PID changed and `curl :8765/health` (allow several seconds for the
launcher's Infisical fetches before trusting a failed probe). After the handler returns,
the live instance MUST re-run kd_session_open + kd_session_plan (in-memory session state
is dropped). The gateway (:8767) does not need a restart for handler-code changes.

**A handler restart drops BOTH instances' in-memory session state** → both Vulcan and Mars
must re-open + re-plan. Never restart unilaterally while the peer is live — coordinate
(via Max) when both reach a clean stop. (See "Known issues → restarts drop both sessions.")

## Session lifecycle (consolidated from the former `session-lifecycle.md`)

The MCP hosts the session lifecycle for the two cooperating Claude instances. They are
**peers** — one holds the "primary" lifecycle slot, one the "worker" slot; that decides
only **close order** (worker releases first), NOT authority.

**Open** (one per instance, back-to-back):

```
kd_session_open(session_id, instance_role=primary|worker, parent_session_id=<primary id, for worker>)
  → returns CORE.md + handoff + BQ status + service health
  → handoff is read DB-FIRST from infra:handoff:role=<role> (per-role file is the fallback);
    the boot payload reports handoff_source = "db" | "file" so you can tell which path served.
    "db" = the database read worked (the proven path since the S766 cutover); "file" = the DB
    read/write is broken and the file fallback served — investigate before trusting the handoff.
  → also surfaces read-only next_ready: the top pending item peeked from the author-dispatch
    database (pickup_query.peek over AUTHOR_DISPATCH_DATABASE_URL). Additive; legacy pickup still live.
  → registers the session in the local registry; claims the role slot in the remote lock
kd_session_plan(session_id, tool_budget, objectives, delegation_strategy)
  → transitions the boot gate PLANNING → OPERATIONAL; unlocks all other tools
```

**Boot gate:** enforced at the HTTP `/api/call` layer. Before `plan` is submitted only
`open`/`plan` are allowed (PLANNING); after `plan`, OPERATIONAL. The gate state is
**disk-backed** (see "Where state lives"), so PLANNING/OPERATIONAL survives a process
restart — but a fresh `open` + `plan` is still required after a restart because the
in-process server object is re-instantiated.

**Close** (only on a real stop condition; worker first, then primary):

```
kd_session_close(session_id, instance_role, reason, summary, handoff_content)
  → commit/push dirty repos → DUAL-WRITE the handoff to BOTH the database
    (infra:handoff:role=<role>) AND HANDOFF.<role>.md → release the role slot → log end
  → do NOT hand-edit HANDOFF.<role>.md: close owns both writes and they must stay in sync.
```

### Where session state lives — TWO records, and why

1. **Local SQLite registry** — `/var/tmp/koskadeux/registry.db` (tables: `sessions`,
   `role_locks`, `close_transactions`) plus the sidecar `/var/tmp/koskadeux/boot_gate_runtime.json`
   (checkpoint flag). Disk-backed so PLANNING/OPERATIONAL and session rows survive a process
   restart (`kill -9` + `launchctl kickstart`). Managed by `tools/registry.py` and
   `session_boot_gate.py`.
2. **Remote Living State lock** — entity `infra:active-session-lock` in Living State
   (Railway), holding the `primary` and `worker` slots, CAS-guarded by `expected_version`.
   Managed by `tools/session_lock.py` (`open_session_namespace` / `resolve_active_session_slot`
   / `release_role_slot`).

**The live open/close lifecycle (`tools/session.py`) uses ONLY the remote Living State lock
as the slot authority.** The local registry's `role_locks` table is a **vestigial second
authority**: nothing in the current lifecycle writes it, so it sits frozen (observed S734:
`role_locks` still showed `primary=724` with no worker row — ~10 sessions stale — while the
remote lock correctly showed `primary=734, worker=734.w`). It is read only by
`tools/process_audit.py::audit_role_locks` and the admin `POST /api/admin/release_role_slot`
endpoint, both of which therefore return wrong answers off the stale record. **Planned fix
(gate-hardening Unit D): retire the local `role_locks` table + registry role-lock methods and
repoint those two readers at the remote lock — single authority.** The registry `sessions`
table (boot-gate persistence) is correct and stays.

**Per-instance handoff:** `HANDOFF.primary.md` and `HANDOFF.worker.md` (in the `koskadeux-mcp`
repo). The legacy single-file `/var/tmp/koskadeux/HANDOFF.md` scheme was retired S733 (Unit B);
a worker boot reads `HANDOFF.worker.md` regardless of how it was written.

## Infisical token & auth refresh (S760)

All launchd-managed services (gateway, mcp, council-hall, AG/DeepSeek servers) start via `/Users/max/bin/launch_with_infisical.sh`, which injects prod secrets through `infisical run`. The Infisical access token is a short-lived JWT (~24h) stored at `~/.config/infisical/sysadmin-token`, minted from a universal-auth machine identity whose client-id/secret live in the macOS login keychain (account `infisical-sysadmin-agent`) via `/Users/max/bin/infisical_auth_refresh.sh` (idempotent; writes the JWT to the token file).

**Failure mode (fixed S760):** the token file was refreshed only on-demand with no schedule, so the JWT could lapse. A service restart after expiry reads the stale token and fails to fetch secrets (`infisical run` -> 403 -> service comes up with empty env). Misleading symptom: secret reads via that token return empty/403 and can look like "secret missing in Infisical" — it is not. Re-mint the token first, then re-check.

**Fix (S760):**
- `launch_with_infisical.sh` now calls `infisical_auth_refresh.sh` before reading the token file, so every (re)start gets a fresh JWT. The refresh is **non-fatal**: if it fails, the wrapper falls back to the existing token file rather than blocking startup. Original wrapper backed up at `launch_with_infisical.sh.bak-S760`.
- New LaunchAgent `com.koskadeux.infisical-token-refresh` runs the refresh every 6h (`StartInterval 21600`, `RunAtLoad`), keeping the file valid for any direct reader. stdout is discarded (it would print the JWT); errors go to `/var/tmp/koskadeux/token-refresh.err`.

**Recovery (token expired / service can't fetch secrets):**
- Re-mint now: `/Users/max/bin/infisical_auth_refresh.sh >/dev/null`
- Confirm validity: decode the JWT `exp` in `~/.config/infisical/sysadmin-token`.
- If the refresh errors with "Infisical creds missing from keychain", restore the universal-auth client-id/secret to keychain account `infisical-sysadmin-agent`.

## Recovery

- **Force recovery:** `touch /var/tmp/koskadeux/force_recovery` (or tell the instance "recover").
  `kd_session_open` then includes the recovery cache and deletes the trigger file.
- **Legacy note:** the older "`kd_recovery_write` after every step / 30-tool-call stale-block"
  discipline and `kd_recovery_cache.json` predate the disk-backed registry and are largely
  superseded — durable session/boot state now lives in `registry.db`. Gate-hardening Unit D
  hardens this further.

## Verifying the path end-to-end

```bash
curl -s http://localhost:8765/api/tools | head -c 400          # 1. real handler
curl -s http://localhost:8767/health                            # 2. proxy
curl -s -i https://mcp.ai.market/.well-known/oauth-protected-resource   # 3. public surface (expect 200)
launchctl list | grep cloudflared                               # 4. transport active
# DNS sanity: mcp.ai.market should resolve via *.cfargotunnel.com
```

A path failure localises by which step first stops returning 200 / active.

## When it breaks

| Symptom | Likely cause | Fix |
|---|---|---|
| All MCP tools fail; `:8765` `/api/tools` is fine | Gateway proxy stale | `launchctl kickstart -k gui/$(id -u)/com.koskadeux.gateway` |
| All MCP tools fail; `:8765` errors/hangs | Handler wedged | kickstart `com.koskadeux.mcp`, then re-run `kd_session_open` + `kd_session_plan` |
| Code change to a tool handler not visible | Restarted gateway, not handler | kickstart `com.koskadeux.mcp` (it imports `tools/agents.py`) |
| Code change still not visible after kickstarting the handler | `kickstart` fired but no-opped — PID unchanged | Confirm the PID changed (`launchctl list \| grep com.koskadeux.mcp`); if unchanged, re-run kickstart and re-verify before declaring the new code live (S766) |
| `mcp.ai.market` 502/504 but `:8767` healthy | Cloudflared tunnel down/misrouted | kickstart `com.koskadeux.cloudflared`; check `cloudflared tunnel info koskadeux` |
| `mcp.ai.market` 401/403 | OAuth flow rejected the bearer | Verify the OAuth metadata endpoint issuer; re-auth from claude.ai |
| "BOOT GATE / checkpoint required" | Session state expects open+plan after a restart | Re-run `kd_session_open` then `kd_session_plan` before any other tool |
| `handoff_source` reads `file` when `db` was expected | DB handoff read or write failing; per-role file fallback served | Inspect the `_upsert_handoff_entity` DB write path (look for `handoff_db_write=warn`); confirm `infra:handoff:role=<role>` exists in Living State |
| A call returns *another* call's output | Response cross-talk under concurrent load | See Known issues → "response cross-talk"; re-read (idempotent GET) to confirm true state |
| `git push origin main` says "up-to-date" but no commit lands | Local `main` tracks `origin/HEAD` | `git push origin HEAD:main`; verify `git fetch origin && git log --oneline -3 origin/main` (S519) |

## Known issues

- **Restarts drop both instances' in-memory session.** A handler restart re-instantiates the
  server; both primary + worker must re-open + re-plan. The disk-backed registry preserves
  PLANNING/OPERATIONAL + session rows, but the gate still requires a fresh open+plan.
  Coordinate restarts — never restart unilaterally while the peer is live.
- **Response cross-talk under concurrent primary+worker.** Observed S734 ~15:00 UTC: a
  `state_request` PATCH executed correctly server-side (the write landed) but the response
  handed back to the caller was a *different* concurrent command's output; the next call
  returned correctly. Server effect applies; the client gets the wrong response body;
  self-recovers on the next call. Suspected ASGI/SSE response-lifecycle violation
  (a second `response.start`). Under investigation in the gate-hardening reform (Unit A
  transport dig). Mitigation: treat a foreign/surprising response as a transport hiccup and
  re-read (idempotent GET) to confirm the actual state before assuming the operation failed.
- **Event-log emit can perturb the lifecycle.** The reconciler/lifecycle event emit to the
  backend `/api/v1/allai/events/` endpoint 422s (the emitter sends general lifecycle events
  but the backend model accepts only dispatch-telemetry variants), and close-path end-event
  puts can 409. A failed emit can divert a close before it finishes (slot not released).
  Gate-hardening Unit A makes all emits best-effort/non-blocking and fixes the `/events/`
  payload schema.
- **MCP transport reconnection latency.** After a restart, claude.ai takes ~5–15 min from the
  user's perspective to fully resync the tool listing — hosted-browser MCP behaviour, not a
  local fault.

## Backup admin path

Cloudflared is the only inbound path the instances have to issue tools, so when the
gateway/handler is dead they cannot restart it themselves. Use a direct admin path to Titan-1
(Tailscale SSH if configured, or local/physical access) to run `launchctl kickstart -k …`
when the public surface is healthy but the local handlers are wedged, or when the tunnel
itself is degraded.

## Why it's built this way (rationale for future readers)

- **Two local processes (proxy + handler):** keeps the public surface stable across handler
  code-restarts; only the handler imports tool code, so a tools change → restart the handler
  only (S519).
- **`launchctl kickstart`, not `pkill`:** handlers are launchd-supervised (KeepAlive=true) and
  respawn instantly after `pkill`, making `pkill` unreliable (S520).
- **cloudflared, not Tailscale:** the Tailscale migration was attempted pre-S572 and recorded
  as done but never completed; cloudflared is the live tunnel (S688 verified).
- **Two lock records (local registry + remote Living State):** historical — the lifecycle
  moved to the remote Living State lock as the single authority; the local `role_locks` table
  was left behind and is now dead/stale, slated for retirement (Unit D). Boot-gate/session
  persistence legitimately uses the local registry `sessions` table so a restart doesn't lose
  PLANNING/OPERATIONAL.
- **Peer model (no primary-over-worker authority):** the two slots only order close (worker
  first); both instances have equal authority over shell, git, dispatch, and Living State.

## In-flight: gate-hardening reform (seam-hardening, not a rewrite)

Tracked in `config:gate-hardening-reform-plan`. Decision (S731): harden the failing seams,
not rewrite. Units + ownership:

- **A — Vulcan:** non-blocking event/log emit (no emit can block/crash a lifecycle op) +
  `/events/` payload-schema fix + the ASGI/SSE response-correlation dig (the cross-talk above).
- **B — Mars (SHIPPED S733):** handoff consolidation — collapsed the legacy
  `/var/tmp/koskadeux/HANDOFF.md` into per-instance `HANDOFF.<role>.md`; reader+writer agree;
  legacy retired.
- **C — Vulcan:** deploy hygiene — enforce "running server == merged HEAD" (the server has run
  hours-stale before a restart).
- **D — Mars (IN PROGRESS):** durable session state + the local `role_locks` retirement
  described above + the session-suite harness reconcile so the session test gate ships green.

**Caution:** the `session.py` fixes for Unit B are merged to `main` but are **NOT live until
the next coordinated MCP restart** — and a restart drops both sessions, so it is coordinated
via Max, not done unilaterally.

## History

- **S225** — checkpoint gate bumped 15→30; `session_open`/`session_close` exempted.
- **S485** — launchd service map established; restart wipes in-memory session state.
- **S519** — two-process architecture clarified (proxy `:8767` vs real handler `:8765`).
- **S520** — `pkill` → `launchctl kickstart -k` correction.
- **Pre-S572** — Tailscale Funnel migration ATTEMPTED to replace Cloudflare Tunnel for
  `mcp.ai.market`; did NOT complete (S688 verified). cloudflared remains active + load-bearing.
- **S690** — comprehensive runbook audit flagged this runbook's Tailscale-vs-cloudflared drift
  (H-1) and the "cloudflared decommissioned" error (H-5).
- **S731** — gate-hardening reform plan converged (Units A–D).
- **S733** — Unit B (handoff consolidation) shipped.
- **S734** — Transport corrected to cloudflared throughout; `session-lifecycle.md`
  consolidated into this runbook; Unit D diagnosis recorded (dead local `role_locks` table;
  the response cross-talk known issue).
