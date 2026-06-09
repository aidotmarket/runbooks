# Titan-1 — the Mac Studio (dev workstation + local AI council + MCP host)

Canonical map of the physical machine the whole operation runs from. Live source of the same data: `state_get("infra:titan-1")` (kept in sync with this doc). Related: `connectivity.md` (network), `mcp-gateway.md` (gateway/tunnel detail), `backup-and-recovery.md` (the scheduled jobs), `infisical-secrets.md` (machine-identity creds).

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

## Role in the ecosystem
Titan-1 is where **the company is actually built and operated**:
- **Local AI council** — the model servers Vulcan/Mars dispatch to (AG/Gemini, DeepSeek, XAI/Grok bridge) run here.
- **MCP orchestration** — the Koskadeux MCP server + gateway run here and are the tool interface both instances use.
- **Local marketplace dev environment** — AIM Data and a local ai-market backend run here in Docker (see Docker stack).
- **Backup origin** — every nightly S3 backup + the watchdog is a launchd job on this machine.
- **Our own data** — our own AIM Data / vectorAIz dev data lives in the local Docker Postgres/Qdrant here, covered by Titan-1's local + physically-separate backup (not S3; customer data is non-custodial).

## Services & ports
| Service | Port | Process | Autostart (LaunchAgent) | Purpose |
|---|---|---|---|---|
| Koskadeux MCP server | 8765 (all ifaces) | `koskadeux_server.py` | `com.koskadeux.mcp` | Agent tool interface (the MCP tools) |
| Koskadeux gateway | 8767 (all ifaces) | `gateway_server.py` (under `infisical run`) | `com.koskadeux.gateway` | MCP gateway/proxy — public entry point |
| AG (Gemini) server | 8766 (localhost) | `ag_server.py` | `com.koskadeux.ag_server` | Gemini FastAPI microservice for Council |
| DeepSeek server | 8768 (localhost) | python (under `infisical run`) | `com.koskadeux.deepseek_server` | DeepSeek Council voter |
| Council Hall | internal | python (under `infisical run`) | `com.koskadeux.council-hall` | Multi-agent deliberation backend |
| XAI/Grok bridge | on-demand | `grok_cli_bridge.py` | (on-demand via Council) | Grok CLI bridge for XAI dispatch |
| Antigravity IDE backend | — | `antigravity.py` | `com.max.antigravity` | IDE backend |

Support agents (also launchd): `auto-continue`, `nosleep` (caffeinate), `lilly`, `mcp-probe`, `ide-health`, `fireflies-sync`, `eu_gemini_checker`, `infisical-token-refresh`.

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

## Scheduled jobs (launchd → S3)
nightly main-DB backup, Qdrant backup, Railway-config export, Cloudflare export, the S3 backup watchdog (Telegram alarm), and daily stats. Full label→script→purpose table and the "why everything shows as bash in Login Items" note live in `backup-and-recovery.md`.

## CLI tooling (versions as of 2026-06-09)
codex 0.138.0 · gemini 0.45.2 · claude 2.1.169 · gh 2.93.0 · grok 1.1.4 · infisical 0.43.91 · aws 2.34.62 · railway 4.30.3 · age 1.3.1 · python3 3.14.5

## Key paths
`/Users/max/koskadeux-mcp` (MCP server/gateway, active) · `/Users/max/Projects/ai-market/{ai-market-backend,ai-market-frontend,aim-data,runbooks}` · `/Users/max/ops/aimarket-backend-main` (backup worktree). Canonical paths: `state_get("config:resource-registry")`.

_Maintained alongside `infra:titan-1` in Living State. Last live inventory: 2026-06-09 (S799.w)._
