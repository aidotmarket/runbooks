# Koskadeux MCP — Gateway, Server, Transport & Session Lifecycle

> Canonical operations runbook for the **internal Koskadeux MCP** that the two AI
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
instances (Vulcan and Mars, equal-authority peers) can call MCP tools from a hosted
browser session. All tool calls (`council_request`, `state_request`, `kd_session_*`,
`shell_request`, `dispatch_mp_build`, etc.) execute locally on Titan-1 against the
filesystem, agents, Council infrastructure, and Living State.

- **Public hostname:** `mcp.ai.market`
- **Transport:** **Cloudflared** (Cloudflare Tunnel) — NOT Tailscale Funnel. See "Transport: why cloudflared" below.
- **Auth on the public surface:** OAuth (RFC 9728 — protected-resource metadata at `/.well-known/oauth-protected-resource`)

## Architecture

```
Claude.ai (hosted browser — Vulcan + Mars, equal-authority peers)
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
| `ag_server` | 8766 | `com.koskadeux.ag_server` | Legacy inactive compatibility process. It is outside ordinary Council/Hall authority and must not emit, persist, or count a Council verdict. |
| `deepseek_server` | 8768 | `com.koskadeux.deepseek_server` | Legacy inactive retired compatibility process. It is outside ordinary Council/Hall authority and must not emit, persist, or count a Council verdict. |
| `lilly_server.py` | — | `com.koskadeux.lilly` | Companion service. |
| `council-hall` | — | `com.koskadeux.council-hall` | Council hall service. |

The current gate voter and Hall panel is exactly CC + Kimi + GLM. MP is the
mandatory builder and is never a reviewer, voter, or Hall participant. AG and
DeepSeek are inactive; their legacy processes, if still present, confer no
Council authority. The signed exact-release contract owns callable roster,
roles, models, providers, limits, and schema digest. Read
`runbooks/council-roster-quirks.md` for the human interaction card and rationale
for each role. Historical `infra:council-comms` prose is discovery evidence,
not live authority.

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

```

There is no ordinary Council restart path for AG or DeepSeek. Do not restore a
legacy process to repair a Council gate or Hall failure. A required review uses
the exact CC/Kimi/GLM panel; schema disagreement blocks roster-dependent work
until the signed release and connected schema agree.

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

Vulcan and Mars are equal-authority peers. Session lifecycle state is keyed by instance:
either peer may open first, and each opens, plans, operates, and closes independently. There
are no role-based lanes, lifecycle slots, parent-session dependency, or close ordering.

```
kd_session_open(session_id, instance=vulcan|mars)
  → returns CORE.md + that instance's handoff + BQ status + service health
  → registers only the named instance's canonical backend session and captures
    its repository/provider/obligation/runbook-activation baseline
kd_session_plan(session_id, tool_budget, objectives, delegation_strategy)
  → accepts one ordinary plan and returns complete immutable runbook context
    before atomically transitioning that session PLANNING → OPERATIONAL
  → an unchanged lost-response retry returns byte-identical content
kd_session_close(session_id, instance=vulcan|mars, reason, summary, handoff_content)
  → transports backend PREPARE/COMMIT using backend-observed action/provider
    evidence; atomically closes only the named instance and preserves the peer
  → returns the immutable signed COMMITTED receipt and typed obligations
```

The backend session/close ledger is canonical. Local registry rows and handoff
files are recoverable caches reconciled from backend truth; the gateway has no
SQLite/HMAC close authority or fallback journal. A peer open or close must not
mutate the other peer's canonical session, boot-gate state, claim, or handoff.
Coordinate a handler restart because it affects both live connections, then use
backend state and exact request retry/reopen semantics rather than inferring
lifecycle state from a local file.

Plan and dispatch callers never supply runbook references, attestations, or gap
claims. Context is automatic at first plan and at the common child provider.
Close callers never supply impact, exit, waiver, or discharge claims. Semantic
uncertainty produces one visible nonblocking backend obligation; trusted
mechanical evidence failure leaves the session open with zero close-side writes.
The next behavior-changing action for a component with an OPEN obligation is
blocked while diagnostics and runbook remediation remain available.

<!-- catalog:historical -->
### Historical S733-S852 role-slot implementation record (retired)

The material below preserves the former role-slot and ordered-close implementation as a
historical record. It is not current operating guidance.

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

**The live open/close lifecycle (`tools/session.py`) resolves the active session from the
local registry `sessions` table — NOT the remote `infra:active-session-lock`.** Open stopped
claiming that lock (Ch5 allai-activation, commit 06e70975); the **S852 close-lock-retirement
fix** then repointed close + the close-gate at the registry (`session_close_gate.py
_resolve_session_id_fallback` reads the registry, not the lock), and `release_role_slot` now
tolerates the retired lock as a no-op. The earlier model — remote lock as the sole
active-session authority — is retired. The local registry `role_locks` table remains a
**vestigial second authority** for the role *slot*: nothing in the lifecycle writes it, so it
sits frozen (observed S734: `role_locks` showed `primary=724` with no worker row, ~10 sessions
stale). It is read only by `tools/process_audit.py::audit_role_locks` and the admin
`POST /api/admin/release_role_slot` endpoint, both of which therefore return wrong answers off
the stale record. **Planned fix (gate-hardening Unit D): retire the local `role_locks` table +
registry role-lock methods and repoint those two readers at the single authority — the
registry (NOT the remote lock; S852 made the registry authoritative for active-session
resolution).** The registry `sessions` table (boot-gate persistence) is correct and stays.

**Per-instance handoff:** `HANDOFF.primary.md` and `HANDOFF.worker.md` (in the `koskadeux-mcp`
repo). The legacy single-file `/var/tmp/koskadeux/HANDOFF.md` scheme was retired S733 (Unit B);
a worker boot reads `HANDOFF.worker.md` regardless of how it was written.
<!-- /catalog:historical -->

## Least-privilege secret launch boundary (S1413)

The launcher authenticates to Infisical only long enough to fetch the explicit
allowlist required by that service. It then removes the Infisical access JWT,
universal-auth material, inherited broad project secrets, and unrelated agent or
Git credentials before starting the child. It does not use `infisical run` to
inject an entire project environment into arbitrary shell, Council, or builder
processes. `SSH_AUTH_SOCK` and repository-write credentials are absent unless a
narrow registered action explicitly requires them.

The gateway/backend channel, GitHub read collector, Railway/provider collector,
signing verifier, and any branch-scoped publisher use separate named credentials
with the smallest resource and operation scope. In particular, backend runbook
verification uses a selected-repository, read-only GitHub credential; it is not
a general developer token. Branch publication uses a separate credential bound
to the exact authorized repository/ref action. No secret value or prefix may be
printed, included in process arguments, persisted in task output, or delivered
to an agent prompt.

Startup fails closed when authentication, allowlisted fetch, signed cutover
status, or required credential validation fails. There is no expired-token,
cached-secret, empty-environment, direct-child, or arbitrary-shell fallback. The
launcher records only redacted credential names, issuer identities, expiry
metadata, and fetch/result digests needed for diagnosis.

**Recovery:** repair or rotate the exact named credential at its owner, verify
least-privilege scope without printing its value, drain the affected service,
restart through the installed allowlist launcher, and prove the new PID has the
expected redacted environment plus a healthy signed contract. A credential
observed in process arguments or logs is compromised: revoke/rotate it at the
coordinated zero-child boundary and do not reuse it merely because it is
short-lived.

## Recovery

- **Force recovery:** `touch /var/tmp/koskadeux/force_recovery` (or tell the instance "recover").
  `kd_session_open` then includes the recovery cache and deletes the trigger file.
- **Legacy note:** the older "`kd_recovery_write` after every step / 30-tool-call stale-block"
  discipline, `kd_recovery_cache.json`, and local close journal are retired as
  authority. Durable session, action, handoff, obligation, outbox, and close
  truth lives in the backend ledger; local recovery material is diagnostic cache
  reconciled from that source.

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
| Backend handoff or close receipt is unavailable | Canonical backend ledger or narrow gateway/backend credential failed | Keep the session open, preserve the typed failure, repair the exact backend route/credential, and retry; local handoff files are cache and never a success fallback |
| A call returns *another* call's output | Response cross-talk under concurrent load | See Known issues → "response cross-talk"; re-read (idempotent GET) to confirm true state |
| `git push origin main` says "up-to-date" but no commit lands | Local `main` tracks `origin/HEAD` | `git push origin HEAD:main`; verify `git fetch origin && git log --oneline -3 origin/main` (S519) |

## Known issues

- **Restarts drop both instances' in-memory session.** A handler restart re-instantiates the
  server; both peers must re-open + re-plan independently. The disk-backed registry preserves
  PLANNING/OPERATIONAL + session rows, but the gate still requires a fresh open+plan.
  Coordinate restarts — never restart unilaterally while the peer is live.
- **Response cross-talk under concurrent peer calls.** Observed S734 ~15:00 UTC: a
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
- **Client-side tool-approval delivery is intermittent (S1236/S1237).** Approval-gated tool
  calls (e.g. `support_ticket_patch`, `kd_session_close`) sometimes fail immediately with
  `No approval received` because the claude.ai approval prompt is never rendered/delivered to
  the user. Confirmed NOT ours: the string does not originate in koskadeux-mcp or
  ai-market-backend source; grep both repos before suspecting local code. Observed failing at
  2026-07-16 ~00:00Z and working at ~09:44Z within the same session with no local change.
  Symptom check: if the user reports no approval dialog appeared, it is this. Workarounds:
  retry the call later in the turn/session; record intent on the peer bus or a ticket message
  (non-approval-gated) so state can be reconciled once the path recovers; for cross-instance
  ownership fields, have the peer holding ownership perform the write. No local fix exists;
  if persistent, restart the claude.ai client session before restarting local processes.

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
<!-- catalog:historical -->
- **Two lock records (local registry + remote Living State):** historical — the lifecycle
  moved to the remote Living State lock as the single authority; the local `role_locks` table
  was left behind and is now dead/stale, slated for retirement (Unit D). Boot-gate/session
  persistence legitimately uses the local registry `sessions` table so a restart doesn't lose
  PLANNING/OPERATIONAL.
- **Peer model (no primary-over-worker authority):** the two slots only order close (worker
  first); both instances have equal authority over shell, git, dispatch, and Living State.
<!-- /catalog:historical -->

## In-flight: gate-hardening reform (seam-hardening, not a rewrite)

<!-- catalog:historical -->
The ownership/status list below is a historical S731-S734 change record, not current peer
lane assignment or current delivery status.

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
<!-- /catalog:historical -->

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

## Deploying handler code that needs a true stop window (migrations)

When a change requires a no-live-connections window (e.g. registry table rebuilds), a plain
`kickstart -k` is wrong — it restarts immediately. Use bootout → migrate → bootstrap, and run
the whole sequence as a script DETACHED INTO A NEW PROCESS SESSION, because the orchestrator
executing it is itself a child of the service being stopped:

```bash
# WRONG on macOS: `setsid` does not exist (S807 lesson — the deploy silently never ran).
# RIGHT: detach via Python start_new_session, then the script survives the bootout.
/usr/bin/python3 -c "import subprocess; subprocess.Popen(['/var/tmp/koskadeux/deploy.sh'], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)"
```

The script should: sleep 3 (let the parent tool call return) → `launchctl bootout
gui/$(id -u)/com.koskadeux.mcp` → run the migration with `venv/bin/python` (repo venv is
`venv/`, NOT `.venv/`; bare python3 lacks deps) → `launchctl bootstrap gui/$(id -u)
~/Library/LaunchAgents/com.koskadeux.mcp.plist` → verify the PID CHANGED and `curl
localhost:8765/health` (allow ~10s startup for Infisical fetches before judging health) →
log everything to a file. After the bounce, every live instance must re-open + re-plan.
