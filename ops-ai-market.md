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
| BUILD QUEUE — needs-Max rows | `build-queue/NeedsMaxRow.tsx` (rendered by `OpenItemsPanel.tsx`) | S1585 one-queue consolidation: everything awaiting Max renders as flagged rows at the TOP of the single BUILD QUEUE list — no separate page or section. The red count badge sits on the BUILD QUEUE nav item; favicon attention swap and document-title count fire whenever needsMaxCount > 0; a failed feed fetch shows a red "needs-you feed unreachable" banner, never a silent zero. `/for-max` redirects to `/build-queue` (also the default route). Empty state: no flagged rows, board only. Demoted incidents and unknown-owner tickets appear on the OPS panel Attention list instead. | `GET /api/v1/ops/needs-max` + `GET /api/v1/ops/operator-attention` (read-only; dual-auth via `get_admin_or_internal_key`) | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| OPS | `OpsPanel.tsx` | Railway health, AI Context Console | `/health`, `/api/v1/ops/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| MONITOR | `MonitorPanel.tsx` | Comms feed, Council Hall, command console | `/api/v1/allai/*`, `/api/v1/comms` (SSE) | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| BUILD QUEUE | `build-queue/OpenItemsPanel.tsx` | OPEN ITEMS board: unresolved git-derived projects, with a plain-English title and inline one-paragraph overview per item. Rows classified `certified_done` by the same payload are excluded from the open tally and disclosed as retained items not shown. Derived from git remotes, the runbook index and the deploy marker — never from Living State's own build records. No age window since S1483. | Reads Living State `infra:open-items-board`, whose sole writer is `koskadeux-mcp/scripts/ground_truth_open_items.py --publish`. | [koskadeux-mcp](https://github.com/aidotmarket/koskadeux-mcp) |
| AGENTS | `AgentsPanel.tsx` | Unified agent fleet, health, proposals | `/api/v1/cp/agents/*`, `/api/v1/allai/agents/status`, `/api/v1/internal/agent-health` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| RUNBOOKS | `RunbooksPanel.tsx` | Browse and read all operational runbooks | GitHub API (public, no auth) | [runbooks](https://github.com/aidotmarket/runbooks) |
| MARKETING | `MarketingPanel.tsx` | Task queue, campaigns, brand voice | `/api/v1/marketing/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| FINANCE | `FinancePanel.tsx` | Revenue, transactions, invoices, payouts | `/api/v1/finance/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| APPROVALS | `HitlApprovalsPanel.tsx` | Agent HITL approval queue — pending agent actions with Approve/Deny; nothing runs until approved. Nav badge shows pending count. Approve/deny send `{resolver_email}` (the ops-login email) so the decision is attributed to the human who clicked. 409 = another operator already claimed the row (informational, panel refetches). | `GET /api/v1/ops/agents/hitl-queue`, `POST /api/v1/ops/agents/hitl-queue/{id}/approve\|deny` — internal-key-enabled (dual-auth) since backend `6a9c35f7`, unanimous Council S1175 (T-2026-000220) | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |

## Needs-Max rows on BUILD QUEUE — unified decision surface (S1181, consolidated S1585)

Since S1585 the needs-Max feed renders as flagged rows at the top of the BUILD QUEUE list (`build-queue/NeedsMaxRow.tsx`; `formax/ForMaxPanel.tsx` is deleted). It reads `GET /api/v1/ops/needs-max`, a read-only backend aggregation whose ticket arm admits only non-terminal tickets with `human_required=true` and an absent-or-Max first-class assignee; owner-assigned tickets and demoted or superseded incidents are excluded and surface on the OPS panel Attention list via `GET /api/v1/ops/operator-attention`. The backend returns `{ total, items[] }` sorted by urgency then age; each item carries `{source, id, title, urgency_or_priority, created_at, age_seconds, deep_link_tab}`.

The panel is registered first in `TopNav`. Each row deep-links to its owning tab; APPROVALS rows offer inline Approve/Deny that reuse the existing `HitlApprovalsPanel` approve/deny helpers (no duplicated resolution logic). A global nav badge and the browser document title both show the live total from the same endpoint, alongside the preserved APPROVALS pending badge. Empty state text is exactly "Nothing needs you."

The separate Remediator summary keeps its canonical handled, fixed, retrying, and needs-attention totals; its **Recently handled** list omits only entries whose outcome is `fixed`, while retrying and human-required entries remain visible.

**Gate-4 lesson (proposal_status_enum):** the native Postgres `proposal_status_enum` labels are the lowercase enum *values* (`draft`, `submitted`, ...). Filtering `AgentProposal.status == ProposalStatus.SUBMITTED` binds the member *name* (`SUBMITTED`) and 500s with asyncpg `InvalidTextRepresentationError`. Use the codebase cast pattern instead: `cast(AgentProposal.status, String) == ProposalStatus.SUBMITTED.value` (same pattern used for `User.status` in `app/api/deps.py`). Backend endpoint: `app/api/v1/endpoints/ops_needs_max.py`.

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

## Build Queue tab — the open-items board (S1461, revised S1545)

`build-queue/OpenItemsPanel.tsx` renders the OPEN ITEMS board. It **replaced** the Living State build-queue view, and the distinction is the whole point of the tab: the old panel rendered the build machinery's own account of itself, so status flowed back through the same system that produced it. This one renders a snapshot derived from git remotes, the runbook index and the deploy marker only.

**Sole writer.** `koskadeux-mcp/scripts/ground_truth_open_items.py --publish` is the ONLY thing that writes Living State `infra:open-items-board`. Nothing that reports its own progress may write that entity, and it must never be hand-edited to look current. If the board is stale, the page must show stale — the panel surfaces the snapshot age and marks it stale past 24h.

**Names, overviews and display metadata.** Titles, one-paragraph business explanations, explicit runbook links and the two bounded `outside_verification_open` flags come from `koskadeux-mcp/scripts/open_items_catalog.json`. They affect presentation only: they cannot change lifecycle stage, deletion safety, branch membership or sole-writer authority. An absent item still appears under its raw git slug, flagged "no plain name yet". Every overview renders inline under its title. Runbook links are validated against exact, non-archived `origin/main:CATALOG.json` entries; a link means the document is registered, not that its contents are verified or authoritative. Catalog failure is stated as a board gap and conservatively shows completed-looking rows instead of hiding unresolved work.

**No activity window (S1483).** The board previously showed only work touched in the last 14 days and named the excluded repos in an "honest gaps" footer. Max removed the window: the page is called open items, so it shows everything open however long it has sat, and the footer is suppressed because there is nothing left to disclaim. `GT_ITEMS_DAYS` still narrows the view for a deliberate recent-activity cut; unset means show everything. Expect a large number — 215 at S1483 against 25 under the old window. Read it as **retained matching remote work refs, not live commitments**: merged refs remain part of the lifecycle, and a one-time triage is still needed before any safe manual branch removal.

**Definition of DONE**, shown on the board and enforced nowhere else: live in production AND verified from outside AND legacy path removed AND runbook indexed. Anything short of all four is OPEN and must be reported at its true stage, never its best milestone. `certified_done` is only the producer's machine-proven branch-removal precondition — merged, reliably deployed and documented — not independent proof that outside verification and legacy removal are complete. Since S1588, the frontend normally hides that exact machine stage, but keeps a row visible when its bounded `outside_verification_open` display flag is true. If display metadata is unavailable or malformed, it fails toward visibility and shows all completed-looking rows. All visible counts, retained-branch counts, unnamed counts and hidden disclosures derive from that one projection.

**Item lifecycle (S1545).** The producer deployed at `aidotmarket/koskadeux-mcp@f6d5394ffb8abf03de967af5af46b88ff33e6864` scans retained matching remote work refs, including merged refs. Its migration baseline omits only the 97 exact `repo + branch + tip` identities already merged when S1545 began. A moved, recreated or reused ref no longer matches that identity and becomes visible again.

Each retained item has one lifecycle stage: `in_progress` while any matching ref is unmerged; `merged_undeployed` when merge is proved but deployment is not live; `production_unknown` when deployment cannot be proved; `documentation_unknown` when runbook evidence cannot be read; `live_undocumented` when deployment is proved but the indexed runbook is absent; and `certified_done` when every matching ref is merged, reliably deployed and covered by the indexed runbook.

Deployment proof is deliberately narrow: `koskadeux-mcp` uses ancestry from the deployed-SHA marker, `runbooks` treats merge to `main` as deployment, and every other repository stays `production_unknown` until it has a reliable deployed-SHA source. Evidence fails closed: an unreadable migration baseline reveals merged refs instead of hiding them; unreliable deployment or documentation evidence cannot produce `safe_to_delete_branch=true`; and Git evidence gaps are reported rather than treated as success. The script remains the sole writer and never consults Living State for membership or stage.

Branch deletion remains manual. Delete only when `safe_to_delete_branch=true` **and** all four DONE checks have been independently confirmed: live in production, verified from outside, legacy path removed and runbook indexed. Never override `production_unknown`; establish reliable deployment evidence first. Use exact expected-tip leases for every deletion, and archive any unique uncontained tip before removing its working ref. When independent proof is completed for a row carrying `outside_verification_open`, remove that display flag in the same bounded closeout and republish; otherwise the page will truthfully but unnecessarily keep the item open. The UI never uses Living State build status to hide a row.

**Layout rule for this and every panel.** `pages/Index.tsx` wraps the app in `h-screen ... overflow-hidden` and `<main>` in `flex-1 min-h-0 overflow-hidden`. A panel that does not own its own scroll region is therefore **clipped with no scrollbar** — the S1483 symptom, where the list simply ran off the bottom of the window past ~15 rows. Every panel root must carry `h-full flex flex-col ... overflow-y-auto` (see `OpsPanel.tsx`, which had it already). Check this first when a panel "loses" its content at the bottom.

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
| `src/components/build-queue/NeedsMaxRow.tsx` | needs-Max flagged row on the BUILD QUEUE list (needs-max feed; replaced ForMaxPanel in S1585) |
| `src/components/agents/AgentsPanel.tsx` | Unified agent fleet view |
| `src/components/agents/AgentDetailDrawer.tsx` | Agent detail slide-out |
| `src/components/runbooks/RunbooksPanel.tsx` | Runbooks browser + repos list |
| `src/components/build-queue/OpenItemsPanel.tsx` | OPEN ITEMS board (the live Build Queue tab) |
| `src/components/build-queue/BuildQueuePanel.tsx` | Retired Living State BQ view; superseded by OpenItemsPanel (S1461), still present in the tree |
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

*Created: S363 (2026-04-01). Updated: S1588 (2026-08-21) — the Open items projection now excludes exact `certified_done` rows from open counts while disclosing the retained hidden count; project and retained-branch units are distinct.*
