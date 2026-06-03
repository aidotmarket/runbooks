# ops.ai.market — Ins{ai}ts Operations Dashboard

## What it is

Internal operations dashboard for ai.market. Single-page React app at `https://ops.ai.market`, deployed on Railway as a static site.

**Repo:** [aidotmarket/ops-ai-market](https://github.com/aidotmarket/ops-ai-market)
**Local path:** `/Users/max/Projects/ops-ai-market`
**Backend:** `api.ai.market` → [aidotmarket/ai-market-backend](https://github.com/aidotmarket/ai-market-backend)

## Tech stack

Vite + React + TypeScript, shadcn/ui + Tailwind CSS, ReactFlow (topology), Recharts (metrics). Railway auto-deploys on push to main.

## Tabs and supporting repos

Each tab in the dashboard pulls from specific backend endpoints. All backend endpoints live in `aidotmarket/ai-market-backend`.

| Tab | Component | Purpose | Backend endpoints | Supporting repos |
|-----|-----------|---------|-------------------|-----------------|
| OPS | `OpsPanel.tsx` | Railway health, AI Context Console | `/health`, `/api/v1/ops/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| MONITOR | `MonitorPanel.tsx` | Comms feed, Council Hall, command console | `/api/v1/allai/*`, `/api/v1/comms` (SSE) | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| BUILD QUEUE | `BuildQueuePanel.tsx` | BQ board: list, sort, drag-reorder, status, lifecycle | Reads: `GET /api/v2/build-queue` (list; `?show_completed` / `?show_cancelled`) and `GET /api/v2/build-queue/{code}` (detail). Writes: `POST /api/v2/build-queue/reorder` and `POST /api/v2/build-queue/{code}/{cancel\|affirm\|priority\|complete}`. Gate edits: `/api/v1/build-queue/{code}/gates[/{n}]`. Auth via `X-Internal-API-Key`. | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| AGENTS | `AgentsPanel.tsx` | Unified agent fleet, health, proposals | `/api/v1/cp/agents/*`, `/api/v1/allai/agents/status`, `/api/v1/internal/agent-health` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| RUNBOOKS | `RunbooksPanel.tsx` | Browse and read all operational runbooks | GitHub API (public, no auth) | [runbooks](https://github.com/aidotmarket/runbooks) |
| MARKETING | `MarketingPanel.tsx` | Task queue, campaigns, brand voice | `/api/v1/marketing/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| FINANCE | `FinancePanel.tsx` | Revenue, transactions, invoices, payouts | `/api/v1/finance/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |

## Agents tab — unified fleet view (S363)

The Agents tab merges 3 data sources into a single grid of agent cards:

| Source | Endpoint | What it provides |
|--------|----------|-----------------|
| Control Plane | `GET /api/v1/cp/agents/` | Registry: name, version, DID, heartbeat, status |
| allAI Host | `GET /api/v1/allai/agents/status` | Runtime: subscriptions, event counts, is_running |
| Agent Health | `GET /api/v1/internal/agent-health` | Monitoring: metrics, validation failures, health grade |

Each card shows combined status. Click to open `AgentDetailDrawer.tsx` which calls `/api/v1/cp/agents/{key}/details` for full metadata, skills, and logs. Expandable chevron reveals health metrics, subscriptions, and validation failures inline.

The "PROPOSALS" sub-tab shows agent proposals (autonomous suggestions). Endpoints: `GET /api/v1/cp/agents/proposals/`, `POST .../review`.

## Runbooks tab (S363)

Dynamically fetches all `.md` files from the `aidotmarket/runbooks` GitHub repo via the public API. Extracts titles and descriptions from markdown content. Renders full markdown inline with search/filter. Links back to GitHub for editing.

Below the runbooks grid, a "Repositories" section lists all repos in the `aidotmarket` GitHub org with descriptions and links.

## Build Queue tab — ordering, drag-reorder, and lifecycle (S760)

`BuildQueuePanel.tsx` is the build-queue board. It loads via `fetchBuildQueueV2()` (`GET /api/v2/build-queue`), maps each list item to a `BuildEntity` through `buildQueueItemToEntity()` in `src/components/build-queue/shared.tsx` (the entity body is preserved via `{...item.body}`, so `body.sort_order` and gate data flow straight through to the UI), and refreshes every 30s.

**Sort modes** (dropdown, `SortKey` in `BuildQueuePanel.tsx`): Actionability (default), Recent, Priority, Gate Progress, and **Manual order**. Manual order sorts by priority -> `body.sort_order` -> code, mirroring the backend list ordering (`_sort_key` in `ai-market-backend/app/api/v2/endpoints/build_queue.py`). Items with no saved `sort_order` fall to the end of their priority band, ordered by code.

**Drag-to-reorder** (dnd-kit): `handleDragEnd` reorders within a priority band and calls `reorderBuildQueueItems()` -> `POST /api/v2/build-queue/reorder`, which writes `sort_order = index` to each entity body. The write is version-checked (each item carries its `version_stamp`; a 409 means the order changed server-side, and the panel refetches), and the backend enforces `sort_order` uniqueness within a priority+status group. Dragging a row across priority bands prompts to change its priority instead. After a successful drag the panel switches the view to Manual order so the new order is visibly applied.

**Why Manual order exists:** drag-reorder persisted `sort_order` long before there was a way to *display* it. The board only offered Actionability / Recent / Priority / Gate Progress, none of which read `sort_order`, so a dragged order appeared to snap back. Manual order (shipped S760, PR #5, commit `054d2d9`) is the display surface for the saved order. Product rule: manual order is **within each priority band**, not a flat global order.

## Architecture

Pure frontend — no server-side logic. All data from `api.ai.market`. Auth via Google OAuth.

**API configuration:** Base URL in `src/hooks/useApiConfig.ts`. All calls go through `src/lib/api.ts` with `X-Internal-API-Key` header from localStorage config.

## Deployment

1. Push to `main` on `aidotmarket/ops-ai-market`
2. Railway builds via `Dockerfile` (nginx static site)
3. DNS: `ops.ai.market` → Railway service

**Verify:** `curl -s -o /dev/null -w "%{http_code}" https://ops.ai.market` → 200

## Local development

```sh
cd /Users/max/Projects/ops-ai-market
npm install
npm run dev
```

Backend at `api.ai.market` — CORS configured, no local override needed.

## Key files

| File | Purpose |
|------|---------|
| `src/App.tsx` | Router + tab layout |
| `src/pages/Index.tsx` | Tab switching, panel rendering |
| `src/components/TopNav.tsx` | Navigation bar with tab buttons |
| `src/lib/api.ts` | All API fetch functions |
| `src/lib/financeApi.ts` | Finance-specific API calls |
| `src/hooks/useApiConfig.ts` | Backend URL config |
| `src/hooks/useOpsAuth.ts` | Google OAuth flow |
| `src/types/index.ts` | TypeScript type definitions |
| `src/components/agents/AgentsPanel.tsx` | Unified agent fleet view |
| `src/components/agents/AgentDetailDrawer.tsx` | Agent detail slide-out |
| `src/components/runbooks/RunbooksPanel.tsx` | Runbooks browser + repos list |
| `src/components/build-queue/BuildQueuePanel.tsx` | BQ management |
| `src/components/monitor/MonitorPanel.tsx` | Comms and Council Hall |
| `src/components/marketing/MarketingPanel.tsx` | Marketing operations |
| `src/components/finance/FinancePanel.tsx` | Financial dashboard |

## Extending the console — adding a tab or feature

The console is a pure frontend; every feature is "call a backend endpoint, render the result." To add or extend a tab:

1. **API:** add a typed fetch function in `src/lib/api.ts` using the shared `apiFetch<T>()` helper (it injects the `X-Internal-API-Key` header and the base URL from `useApiConfig`). Add request/response types to `src/types/index.ts`. New backend endpoints live in `aidotmarket/ai-market-backend`.
2. **Component:** add a panel under `src/components/<area>/`. Register the tab in `src/components/TopNav.tsx` and render it in `src/pages/Index.tsx`.
3. **Tests:** add a vitest test next to the component (`__tests__/*.test.tsx`). Mock `fetch` and seed `localStorage` key `insaits_api_config` the way the existing build-queue tests do. Run `npm run test`, `npx tsc --noEmit`, and `npm run lint` before pushing. The CI lint gate (`.github/workflows/lint.yml`) blocks merges on eslint errors (warnings are tolerated).
4. **Ship:** branch off `origin/main`, open a PR, get an MP reviewer pass (builder != reviewer), squash-merge to `main`. A push to `main` triggers the Railway build and the Deploy Receipt workflow.
5. **Verify live:** the JS bundle is hash-named, so confirm a deploy by fetching the live bundle and grepping for a string you added:
   ```sh
   b=$(curl -s https://ops.ai.market/ | grep -oE '/assets/[^"]+\.js' | head -1)
   curl -s "https://ops.ai.market$b" | grep -c "<a string you added>"
   ```

Conventions worth keeping: UI data lives at `entity.body.*` after `buildQueueItemToEntity`-style mapping; lifecycle writes are version-checked (pass the `version_stamp`; handle 409 by refetching); never put the internal API key anywhere but the localStorage config the console already uses.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Health endpoint unavailable" | `/api/v1/internal/agent-health` requires `X-Internal-API-Key` | Verify `INTERNAL_API_KEY` in Infisical matches dashboard config |
| "Failed to load agent details" | Pydantic validation error in backend | Check Railway logs for 500 trace, likely schema mismatch |
| "CONTROL PLANE UNREACHABLE" | `/api/v1/cp/agents/` error | Check backend deploy, verify CP router mounted |
| Blank after deploy | nginx SPA fallback broken | Check `nginx.conf` routes all paths to `index.html` |
| Auth redirect loop | Google OAuth misconfigured | Verify `GOOGLE_CLIENT_ID` in Infisical |
| Runbooks empty | GitHub API rate limit (60 req/hr unauthenticated) | Wait or add GitHub token |
| Repos section empty | Same GitHub API rate limit | Same fix |
| Dragged build-queue order "snaps back" | Sort mode is not Manual order | Select "Manual order" in the sort dropdown (a drag now auto-switches to it). Manual order = priority -> saved `sort_order` -> code. |
| Reorder fails / "order changed on the server" | 409: `sort_order`/version changed server-side | Panel auto-refetches; just re-drag. Backend enforces unique `sort_order` within a priority+status group. |
| Build Queue board blank / 0 items | One malformed entity 500'd `GET /api/v2/build-queue` (legacy `body.gates` shape) | Now skipped+logged by `_safe_entity_to_detail` in `ai-market-backend/app/api/v2/endpoints/build_queue.py`; check Railway logs for the skipped-entity warning, then repair the entity body. |

## Conformance

This runbook predates the strict A-K standard (`specs/BQ-RUNBOOK-STANDARD.md`) and uses the narrative + tables style (same choice as `aim-data.md`). It converts to the strict skeleton when the linter + harness ship; the content above is the source of truth until then.

---

*Created: S363 (2026-04-01). Updated: S760 (2026-06-03) — Build Queue migrated to `/api/v2/build-queue/*`; documented sort modes, drag-reorder, and the Manual order view; added an "Extending the console" guide and build-queue troubleshooting rows.*
