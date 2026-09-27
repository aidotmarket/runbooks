---
title: Titan-1 — the Mac Studio (dev workstation + local AI council + MCP host)
owner: unassigned
last_verified: '2026-07-17'
aliases: []
error_signatures: []
---

# Titan-1 — the Mac Studio (dev workstation + local AI council + MCP host)

Canonical map of the physical machine the whole operation runs from. Live source of the same data: `state_get("infra:titan-1")` (kept in sync with this doc). Related: `connectivity.md` (network), `mcp-gateway.md` (gateway/tunnel detail), [backup-and-recovery.md](./backup-and-recovery.md) (backup schedules, evidence, and limits), [disaster-recovery.md](./disaster-recovery.md) (recovery map), `infisical-secrets.md` (machine-identity creds).

## Identity & hardware
| | |
|---|---|
| Hostname | `Koskadeux.local` |
| Serial | `G6XQC2KL44` (Mac Studio, `Mac15,14`) |
| Chip | Apple M3 Ultra — 32 cores (24 performance + 8 efficiency) |
| Memory | 256 GB unified |
| Disk | 926 GB SSD — data volume ~51% used, ~450 GB free (2026-06-09) |
| OS | macOS 26.5.1 (build 25F80) |
| LAN | 192.168.1.192 · Tailscale node `koskadeux-10` = 100.95.61.121 |

## macOS user accounts

| Account | Purpose | Credential |
|---|---|---|
| `max` | Primary operator account; all agent sessions, Homebrew, repos | Max personal — not stored |
| `kdbrowser` | Isolated test account for human-fidelity browser testing (kd-browser runner, Codex-driven walks; home carries `kd-browser-runner/`) | Infisical `koskadeux-mcp`/prod, path `/`, secret `TITAN_KDBROWSER_PASSWORD` (verified present S1260; value never read out) |

Codex CLI is installed system-wide via Homebrew (`/opt/homebrew/bin/codex`, on PATH for all accounts via `/etc/paths.d/homebrew`); OpenAI login state is per-account under `~/.codex/`. Verified S1260: `kdbrowser` Codex is logged in (ChatGPT auth, `~kdbrowser/.codex/auth.json`). CAVEAT: the kd-browser runner (`127.0.0.1:8790`) launches jobs with a minimal launchd env - job requests must pass `env.PATH` including `/opt/homebrew/bin` or `codex` fails with `env: node: No such file or directory`.

## Role in the ecosystem
Titan-1 is where **the company is actually built and operated**:
- **Local AI council** — the model servers Vulcan/Mars dispatch to (AG/Gemini, DeepSeek, XAI/Grok bridge) run here.
- **MCP orchestration** — the Koskadeux MCP server + gateway run here and are the tool interface both instances use.
- **Local marketplace dev environment** — AIM Data and a local ai-market backend run here in Docker (see Docker stack).
- **Backup host for selected jobs** — Titan-1 runs the Qdrant, Railway-config, and Cloudflare S3 exports and the S3 freshness watchdog. The main ai.market Postgres dump runs on Railway at 02:00 UTC; the age-encrypted Infisical Postgres dump runs on Railway at 03:00 UTC. See [backup-and-recovery.md](./backup-and-recovery.md) for the current job map and limits.
- **Our own data** — our own AIM Data / vectorAIz dev data lives in local Docker Postgres/Qdrant. The S799 owner decision excludes it from S3. A Sep 27 `tmutil isexcluded` check returned `Excluded` for `/Users/max/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`; a prior Backblaze exclusion observation was not rechecked in this audit. This does not establish that every alternative backup is absent or that data was lost. Classify the important Docker volumes and prove an independent export and restore before claiming coverage. Time Machine recovery of selected host files is a separate claim: the actual registry SQLite file was extracted from the Sep 27 `20260927-141950` snapshot (61,440 bytes, integrity OK, six tables), but that does not prove Docker volume or whole-host disaster recovery. See [disaster-recovery.md](./disaster-recovery.md).

## Services & ports
| Service | Port | Process | Autostart (LaunchAgent) | Purpose |
|---|---|---|---|---|
| Koskadeux MCP server | 8765 (all ifaces) | `koskadeux_server.py` | `com.koskadeux.mcp` | Agent tool interface (the MCP tools) |
| Koskadeux gateway | 8767 (all ifaces) | `gateway_server.py` (under `infisical run`) | `com.koskadeux.gateway` | MCP gateway/proxy — public entry point |
| AG (Gemini) server | — | retired 2026-08-11 (koskadeux-mcp f0c3eab03c) | none | Removed; nothing listens on 8766 |
| DeepSeek server | 8768 (localhost) | python (under `infisical run`) | `com.koskadeux.deepseek_server` | DeepSeek Council voter |
| Council Hall | internal | python (under `infisical run`) | `com.koskadeux.council-hall` | Multi-agent deliberation backend |
| XAI/Grok bridge | on-demand | `grok_cli_bridge.py` | (on-demand via Council) | Grok CLI bridge for XAI dispatch |
| Antigravity IDE backend | — | `antigravity.py` | `com.max.antigravity` | IDE backend |

Support agents (also launchd): `auto-continue`, `nosleep` (caffeinate), `lilly`, `mcp-probe`, `ide-health`, `fireflies-sync`, `infisical-token-refresh`. `com.koskadeux.gemini-release-checker` (daily 09:15, `koskadeux-mcp/scripts/check_gemini_release.py`) replaced `com.koskadeux.eu_gemini_checker` in S1721; the old job is booted out and its plist is in `~/Library/LaunchAgents/archive-s1721/` (verified 2026-09-21). See `runbooks/council.md`, Gemini member.

## Public transport (how the outside reaches the gateway)
- **Public path = Cloudflare Tunnel.** `cloudflared tunnel run koskadeux` (config `~/.cloudflared/config.yml`, LaunchAgent `com.koskadeux.cloudflared`) fronts the gateway at **mcp.ai.market**. **Do NOT remove `com.koskadeux.cloudflared`** — it is the live public path.
- **Tailscale = private mesh only.** Node `koskadeux-10`; reaches the laptop (`maxbookpro`) and phone over WireGuard for admin/SSH. The older "Tailscale Funnel" public path (S355) is retired; Cloudflare is the public path now.

## Local Docker stack (the dev marketplace)
| Container | Image | Role |
|---|---|---|
| `aim-data-app-1` | `ghcr.io/aidotmarket/aim-data` | AIM Data app (local) |
| `aim-data-postgres-1` | `postgres:16-alpine` | AIM Data DB (our own dev data) |
| `aim-data-qdrant-1` | `qdrant/qdrant` | AIM Data vector store |
| `ai-market-backend-postgres-1` | `postgres:15-alpine` | local backend Postgres (dev) |
| `crm-gate-postgres` | `postgres:16` | CRM gate DB (local) |
| `gifted_shirley` | `github-mcp-server` | GitHub API for Claude Desktop |
| `buildx_buildkit_aimdata-multi0` | `moby/buildkit` | multi-arch image builder |

## Scheduled backup jobs
The main ai.market Postgres dump is a Railway cron at 02:00 UTC, and the encrypted Infisical Postgres dump is a Railway cron at 03:00 UTC. Titan-1 launchd runs the Qdrant, Railway-config, and Cloudflare exports plus the S3 backup watchdog; daily stats is a separate local job. The Sep 27 controller review found the dedicated main-pinned watchdog path installed at 17:12:37Z and five target checks passing, including the six Qdrant collections. This is freshness evidence only; Telegram delivery and full disaster recovery were not certified. See [backup-and-recovery.md](./backup-and-recovery.md) for operational detail and [disaster-recovery.md](./disaster-recovery.md) for restore limits.

## CLI tooling (versions as of 2026-06-09)
codex 0.138.0 · gemini 0.45.2 · claude 2.1.169 · gh 2.93.0 · grok 1.1.4 · infisical 0.43.91 · aws 2.34.62 · railway 4.30.3 · age 1.3.1 · python3 3.14.5

## Railway auth / env (machine credential)
Titan-1 reaches Railway (CLI, GraphQL, and the local CLI-backed Railway MCP) with **one account-scoped, non-expiring API token** — minted `titan-1-koskadeux` (Workspace = **No workspace**). It lives **only in Infisical**: project **`koskadeux-mcp`** (projectId `0943f641-faee-4324-b337-0d50c276e4a9`), env `prod`, path `/`, secret name `RAILWAY_API_TOKEN`. Nothing is written to disk. Migrated off Doppler in S993; project/env verified S994.

- **Source it, don't exec it:** `source ~/bin/railway-env.sh`. It refreshes the Infisical machine identity (`infisical_auth_refresh.sh`), fetches `RAILWAY_API_TOKEN`, exports it, and **unsets `RAILWAY_TOKEN`**. `launch_mcp_server.sh` sources it via one guarded line; `railway_client._token()` prefers `RAILWAY_API_TOKEN`, then legacy `RAILWAY_TOKEN`, then `~/.railway/config.json`.
- **Account-scope, NOT workspace-scope:** the token must be account-scoped. Workspace-scoped tokens **403 on CLI account operations** — that was the historical CLI flakiness, and the old workspace-scoped tokens were deleted in S993.
- **`RAILWAY_TOKEN` conflict rule:** a stray `RAILWAY_TOKEN` in the environment overrides `RAILWAY_API_TOKEN` and breaks account ops. Always `unset RAILWAY_TOKEN` before CLI commands (railway-env.sh does this for you).
- **Remote MCP is optional:** `mcp.railway.com` (browser OAuth) is **non-load-bearing** — CLI/GraphQL via the Infisical token is the load-bearing path.
- **Gotcha:** bare `python`/urllib calls to `backboard.railway.app` 403 on a Cloudflare UA block — not an auth failure; `railway_client` uses `httpx`, which works.

Live machine-readable source: `state_get("infra:railway")` → `management_tools.machine_identity`.

## Key paths
`/Users/max/koskadeux-mcp` (MCP server/gateway, active) · `/Users/max/Projects/ai-market/{ai-market-backend,ai-market-frontend,aim-data,runbooks}` · `/Users/max/ops/aimarket-backend-main` (backup worktree). Canonical paths: `state_get("config:resource-registry")`.

_Maintained alongside `infra:titan-1` in Living State. Last live inventory: 2026-06-09 (S799.w)._


## Incident record — 2026-07-04 reboot outage (S1118) + cold-start canary rule

**What happened:** Apple OS patch rebooted Titan-1. All com.koskadeux.* LaunchAgents are
correctly RunAtLoad+KeepAlive and restarted — but the gateway crash-looped (exit 1):
`gateway_server.py` imports `ContentBlock`/`Icon` from `mcp.types`, and the venv held
`mcp==1.8.1` (silently downgraded/reinstalled ~Jul 3 12:36 local, source unattributed;
`requirements.txt` had an unpinned `mcp` line). The old process had the newer SDK in
memory, so nothing failed until the cold start. Public symptom: Cloudflare 502 on
mcp.ai.market (tunnel up, origin :8767 down). Fix: `venv/bin/pip install -U mcp`
(→1.28.1) + kickstart; floor now pinned in requirements.txt (commit d92a15b1).

**Rule — cold-start import canary:** after ANY dependency change in the koskadeux venv
(pip install/upgrade/downgrade, requirements edit, venv rebuild), run:
`for m in koskadeux_server gateway_server; do venv/bin/python -c "import $m" || echo "$m FAILS COLD-START"; done`
A running process proves nothing about the next reboot. Note: importing koskadeux_server
applies pending registry migrations (side effect; idempotent).

**Fast triage for "MCP unreachable after reboot":** probe `https://mcp.ai.market/health`
from anywhere — 530/1033 = tunnel down (cloudflared, system daemon); 502 = tunnel up,
gateway :8767 down (check `/var/tmp/koskadeux/gateway.err`); 200 = path fine, look
higher. Local: `curl 127.0.0.1:{8765,8767}/health`; kickstart:
`launchctl kickstart -k gui/$(id -u)/com.koskadeux.<svc>`.

## When it breaks

Use the reboot-outage incident record and cold-start canary rule above for restart failures; no broader repair procedure is defined.
