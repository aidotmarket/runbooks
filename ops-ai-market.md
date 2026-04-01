# ops.ai.market — Ins{ai}ts Operations Dashboard

## What it is

Internal operations dashboard for ai.market. Single-page React app at `https://ops.ai.market`, deployed on Railway as a static site. Repo: `aidotmarket/ops-ai-market`. Local path: `/Users/max/Projects/ops-ai-market`.

## Tech stack

- Vite + React + TypeScript
- shadcn/ui + Tailwind CSS
- ReactFlow (topology graph)
- Recharts (metrics)
- Railway (auto-deploy on push to main)

## Architecture

The dashboard is a pure frontend app — no server-side logic. All data comes from the backend API at `api.ai.market` (repo: `aidotmarket/ai-market-backend`). Auth is via Google OAuth (same as the marketplace).

### API configuration

The backend base URL is stored in `src/hooks/useApiConfig.ts`. API calls go through `src/lib/api.ts` which wraps `fetch` with auth headers.

## Tabs

| Tab | Component | Purpose | Data sources |
|-----|-----------|---------|--------------|
| OPS | `OpsPanel.tsx` | Railway health, AI Context Console | `/api/v1/ops/*`, backend health endpoints |
| MONITOR | `MonitorPanel.tsx` | Comms feed, Council Hall, command console | `/api/v1/allai/*`, SSE streams |
| BUILD QUEUE | `BuildQueuePanel.tsx` | BQ CRUD, status, roadmap view | `/api/v1/state/*` (Living State) |
| AGENTS | `AgentsPanel.tsx` | Agent fleet, health, proposals | 3 endpoints (see below) |
| AGENT HEALTH | `AgentHealthPanel.tsx` | Deep health metrics, validation failures | `/internal/agent-health` |
| MARKETING | `MarketingPanel.tsx` | Task queue, campaigns, brand voice | `/api/v1/marketing/*` |
| FINANCE | `FinancePanel.tsx` | Revenue, transactions, invoices, payouts | `/api/v1/finance/*` |

## Agent data sources (IMPORTANT)

The Agents tab currently pulls from **3 separate endpoints** that represent the same agents in different contexts:

| Source | Endpoint | What it provides | Component |
|--------|----------|-----------------|-----------|
| CP Agents (Control Plane) | `GET /api/v1/cp/agents/` | Registry: name, version, DID, heartbeat, online/offline status | `AgentsPanel.tsx` — "CP AGENTS" section |
| allAI Host Status | `GET /api/v1/allai/agents/status` | Runtime: subscriptions, event counts, is_running state | `AgentsPanel.tsx` — "INTERNAL AGENTS" section |
| Agent Health | `GET /internal/agent-health` | Monitoring: metrics, validation failures, health grade, policies | `AgentHealthPanel.tsx` — separate tab |

**Known issue (S363):** These 3 sources show the same agents in 3 different UI sections, which is confusing. The plan is to unify into a single fleet view where each agent card merges all 3 data sources, with a drill-in drawer for details.

### Agent detail drawer

Clicking a CP Agent card opens `AgentDetailDrawer.tsx` which calls:
- `GET /api/v1/cp/agents/{key}/details` — full agent metadata, skills, config
- `GET /api/v1/cp/agents/{key}/logs` — execution logs with pagination

### Proposals

The Agents tab has a "PROPOSALS" sub-tab showing agent proposals (autonomous suggestions from allAI agents):
- `GET /api/v1/cp/proposals/` — list proposals
- `GET /api/v1/cp/proposals/{id}` — proposal detail
- `POST /api/v1/cp/proposals/{id}/review` — approve/reject

## Deployment

Railway auto-deploys from `main` branch. The app builds as a Docker image using `nginx` to serve the static SPA.

### Deploy steps
1. Push to `main` on `aidotmarket/ops-ai-market`
2. Railway picks up the push and builds via `Dockerfile`
3. Static files served by nginx (`nginx.conf` in repo root)
4. DNS: `ops.ai.market` → Railway service

### Verify deploy
```sh
curl -s -o /dev/null -w "%{http_code}" https://ops.ai.market
# Should return 200
```

## Local development

```sh
cd /Users/max/Projects/ops-ai-market
npm install
npm run dev
# Opens at localhost:8080 (or next available port)
```

The app expects the backend at `api.ai.market` — no local backend override is needed since CORS is configured.

## Key files

| File | Purpose |
|------|---------|
| `src/App.tsx` | Router + tab layout |
| `src/lib/api.ts` | All API fetch functions |
| `src/lib/financeApi.ts` | Finance-specific API calls |
| `src/hooks/useApiConfig.ts` | Backend URL config |
| `src/hooks/useOpsAuth.ts` | Google OAuth flow |
| `src/types/index.ts` | TypeScript type definitions |
| `src/components/agents/AgentsPanel.tsx` | Main agents fleet view |
| `src/components/agents/AgentHealthPanel.tsx` | Agent health deep-dive |
| `src/components/agents/AgentDetailDrawer.tsx` | Agent detail slide-out |

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "AGENT HEALTH ENDPOINT UNREACHABLE" | `/internal/agent-health` endpoint down or not exposed | Check backend logs, verify endpoint exists in backend routes |
| "CONTROL PLANE UNREACHABLE" | `/api/v1/cp/agents/` returning error | Check backend deploy status, verify CP router is mounted |
| Blank dashboard after deploy | Build succeeded but nginx config wrong | Check `nginx.conf` — SPA fallback must route all paths to `index.html` |
| Auth redirect loop | Google OAuth misconfigured | Verify `GOOGLE_CLIENT_ID` in Infisical, check allowed redirect URIs |
| Stale data | 30s polling interval | Click refresh button or wait; check if backend is healthy |

---

*Created: S363 (2026-04-01)*
