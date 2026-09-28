---
title: ops.ai.market — Ins{ai}ts Operations Dashboard
owner: unassigned
last_verified: '2026-09-28'
aliases: []
error_signatures: []
---

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
| BUILD QUEUE | `build-queue/OpenItemsPanel.tsx` | Retained project work, completion evidence gaps, retained branches, loaded alert entries and entries in the current Needs You feed projection are shown separately. Only an exact `certified_done` stage may be hidden, subject to outside-flag and metadata visibility fallback. The board has no age window. | Reads Living State `infra:open-items-board`, whose sole writer is `koskadeux-mcp/scripts/ground_truth_open_items.py --publish`; Needs You uses its separate backend feed. | [koskadeux-mcp](https://github.com/aidotmarket/koskadeux-mcp) |
| AGENTS | `AgentsPanel.tsx` | Unified agent fleet, health, proposals | `/api/v1/cp/agents/*`, `/api/v1/allai/agents/status`, `/api/v1/internal/agent-health` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| RUNBOOKS | `RunbooksPanel.tsx` | Browse and read all operational runbooks | GitHub API (public, no auth) | [runbooks](https://github.com/aidotmarket/runbooks) |
| MARKETING | `MarketingPanel.tsx` | Task queue, campaigns, brand voice | `/api/v1/marketing/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| FINANCE | `FinancePanel.tsx` | Revenue, transactions, invoices, payouts | `/api/v1/finance/*` | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |
| APPROVALS | `HitlApprovalsPanel.tsx` | Agent HITL approval queue — pending agent actions with Approve/Deny; nothing runs until approved. Nav badge shows pending count. Approve/deny send `{resolver_email}` (the ops-login email) so the decision is attributed to the human who clicked. 409 = another operator already claimed the row (informational, panel refetches). | `GET /api/v1/ops/agents/hitl-queue`, `POST /api/v1/ops/agents/hitl-queue/{id}/approve\|deny` — internal-key-enabled (dual-auth) since backend `6a9c35f7`, unanimous Council S1175 (T-2026-000220) | [ai-market-backend](https://github.com/aidotmarket/ai-market-backend) |

## Needs-Max rows on BUILD QUEUE — unified decision surface (S1181, consolidated S1585)

Since S1585 the needs-Max feed renders as flagged rows at the top of the BUILD QUEUE list (`build-queue/NeedsMaxRow.tsx`; `formax/ForMaxPanel.tsx` is deleted). It reads `GET /api/v1/ops/needs-max`, a read-only backend aggregation whose ticket arm admits only non-terminal tickets with `human_required=true` and an absent-or-Max first-class assignee; owner-assigned tickets, demoted incidents, and superseded incidents are excluded. Demoted (still-escalated) incidents and unknown-owner human_required tickets surface on the OPS panel Attention list via `GET /api/v1/ops/operator-attention`; superseded incidents are simply resolved; owner-assigned tickets live on the owner's TICKETS view. The backend returns `{ total, items[] }` sorted by urgency then age; each item carries `{source, id, title, urgency_or_priority, created_at, age_seconds, deep_link_tab}`.

The needs-Max rows render at the top of the BUILD QUEUE list (third nav item, after OPS and MONITOR). Each row deep-links to its owning tab; APPROVALS rows offer inline Approve/Deny that reuse the existing `HitlApprovalsPanel` approve/deny helpers (no duplicated resolution logic). The red count badge is attached to the BUILD QUEUE nav item specifically (not global); the document-title count and red-dot favicon fire whenever needsMax.total > 0, and a failed feed fetch renders a red "needs-you feed unreachable" banner plus an error marker on the badge, never a silent zero. With zero items the page simply shows the board (the old "Nothing needs you." empty state is deleted; the board's own empty state is "Nothing open in the window, or the board has not published yet.").

The Remediator summary (handled, fixed, retrying, needs-attention totals and the recent list) remains available as API data on `GET /api/v1/ops/needs-max` but is NOT rendered anywhere on the consolidated queue page since S1585; frontend tests assert the seven-day report and all Remediator text are absent from BUILD QUEUE.

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

**Publisher serialization recovery (S1605).** If one run prints both `snapshot write FAILED: Object of type PosixPath is not JSON serializable` and `Living State publish FAILED` with the same error, inspect `items[].branch_refs[].deployment_attestation.source`. The durable deployment-marker constant remains a `Path`; the producer converts it with `os.fspath` only when constructing the JSON attestation and strictly serializes the snapshot before opening the local destination. Do not hand-edit the board, add `default=str`, introduce a generic normalizer, or change sole-writer/exit semantics. After the repaired producer is merged and deployed, run the normal publisher once and require: no `FAILED` line, `/Users/max/koskadeux-state/open-items-board.json` parses as complete JSON, Living State advances with a fresh `generated_at`, and the authorized operator Chrome session shows that fresh timestamp. This is recovery evidence, not a new gate or confirmation.

**S1605 serialization-runbook ref closeout.** After the repaired producer was
deployed and repeated publisher/Chrome checks showed fresh, parseable board
state, `docs/bq-board-json-boundary-s1605` at
`872cccfcad3516d3fef770849854fa5d0143198a` was copied byte-for-byte to
`archive/s1605/gate4/board-json-boundary` and the original remote ref was
deleted under an exact expected-tip lease. The archive is recovery evidence
only; it does not add a gate, confirmation, writer, or alternate publication
path.

**Names, overviews and display metadata.** Titles, one-paragraph business explanations, explicit runbook links and the two bounded `outside_verification_open` flags come from `koskadeux-mcp/scripts/open_items_catalog.json`. Exact `(repo, full branch)` mappings take precedence over legacy `branch_keys` fragments; collisions remain under a raw git slug. These mappings change grouping and presentation only, never membership, stage, sole-writer authority, ownership, closure or deletion safety. An absent name remains visible under its raw slug, flagged "no plain name yet". Every overview renders inline under its title. A runbook link helps discovery but is not completion evidence.

**Exact branch-identity repair (S1605, historical).** The default project key uses the earliest session stamp so deliberately staged branches stay on one programme row. If unrelated projects reuse the same session stamp, use the smallest exact mapping and keep each ref's evidence untouched. The S1604 repair separated `dispatch-base-derivation-s1604`, `profile-update-mass-assignment-s1604` and `verified-label-website-page-s1604`; its dry run expected the dispatch row to be `certified_done` under the then-deployed classifier. That expectation is historical evidence, not an instruction to certify that row under the current four-part contract. Recheck its exact refs and positive completion evidence before any current stage or deletion decision.

**No activity window (S1483).** The board previously showed only work touched in the last 14 days and named the excluded repos in an "honest gaps" footer. Max removed the window: the page is called open items, so it shows everything open however long it has sat, and the footer is suppressed because there is nothing left to disclaim. `GT_ITEMS_DAYS` still narrows the view for a deliberate recent-activity cut; unset means show everything. Expect a large number — 215 at S1483 against 25 under the old window. Read it as **retained matching remote work refs, not live commitments**: merged refs remain part of the lifecycle, and a one-time triage is still needed before any safe manual branch removal.

**Definition of DONE:** live in production AND verified from outside AND legacy path removed AND runbook indexed. A runbook link is a display aid, not completion proof. The former classifier could label a merged, deployed, documented row `certified_done` without outside or legacy receipts. Strict classifier PR [263](https://github.com/aidotmarket/koskadeux-mcp/pull/263) candidate `857b14155b1c072271f104f4ff4767821d86609b` received all three CC/GLM/DeepSeek APPROVE_WITH_NITS votes and merged as `aeab40aff9e43ac072d3dc54973a471ad18c56ea`. Its accepted normal CLI publisher execution passed the exact-source check and 67 tests, and published v655 before catalogue PR 262 entered. Neither an absent `outside_verification_open` flag nor a runbook link supplies positive outside or legacy evidence; this classifier cannot certify DONE or authorize branch deletion.

**Item lifecycle (S1545).** The S1545 producer at `aidotmarket/koskadeux-mcp@f6d5394ffb8abf03de967af5af46b88ff33e6864` established the scan of retained matching remote work refs, including merged refs. Its migration baseline omits only the 97 exact `repo + branch + tip` identities already merged when S1545 began. A moved, recreated or reused ref no longer matches that identity and becomes visible again.

The accepted strict classifier assigns one lifecycle stage: `in_progress` if any ref is unmerged; `production_unknown` if deployment evidence is missing or unreliable; `merged_undeployed` if a merged ref is known not deployed; `documentation_unknown` if the index cannot be read; `live_undocumented` if deployed but the current helper says runbook coverage is absent; `outside_verification_pending` if the explicit outside flag is true; otherwise `completion_verification_pending` because exact-ref positive outside and legacy retirement receipts are missing. The current helper's word matches are unreliable; PR 272 proposes the explicit path validation below. Each stage returns `safe_to_delete_branch=false`. `certified_done` remains an exact UI filter value, but this classifier does not emit it. The long-running gateway deployed marker remains at `7fb`; the accepted normal CLI producer can run the merged source separately, without a gateway reload. Check that invocation's checkout, exact source hash, tests and clean artifact receipt independently. The snapshot body has no `producer_sha` or `source_sha`; its `deploy_line` is a deployment marker, not proof of the executed publisher SHA. No gateway restart or override is indicated; forced TTL 0 approval remains pending.

**Board accuracy evidence and rollout (S1760, 2026-09-28).** Ops UI PR [38](https://github.com/aidotmarket/ops-ai-market/pull/38), candidate `c5525b16afeba202c91f9639199b2ed32f19039a`, received the one GLM presentation review recorded at `/Users/max/council/glm/response-20260928-022845-330361.md` and 47 independent tests. It merged as `9a158d9658f28a8f7dc8c1e45c7b15f396a8b05f` at 00:35:51Z. Railway `ops-dashboard` active deployment `e92d612a-10c4-4133-acac-453c45418b18` reported SUCCESS at that exact merge. Authenticated Chrome showed 50 project work rows, 8 evidence gaps, 277 retained branches, 0 loaded alert entries, 2 entries in the current Needs You feed projection and 58 hidden legacy machine-certified rows. The zero loaded-alert count describes that feed output only; it does not establish provider health or absence of incidents. The page's `last_verified` date records this scoped live UI display verification only. The producer remained at deployed `7fb` old-classifier code and its snapshot was generated 2026-09-27 21:22:03Z; those UI numbers do not certify the whole board, its recovery or any hidden row.

That UI paragraph is a dated historical receipt. Incident `8474ce21-2854-412d-a57b-b0b187eee47d` later resolved at 01:06:44Z after one manual failed-job retry and an actual scheduled remediator check; it does not demonstrate autonomous repair. The backend verifier's `github_default_branch_missing` behavior remains open: its run object omits `default_branch` although repository GET reports `main`. Phase 1 design `2698d` cleared MD only; runtime, read-only selector, real Postgres, agent-complete Remediator runbook, full panel and activation remain unfinished. No actor ownership, automatic resolution or notification change follows from the design. At 07:02Z a separate supported API view showed four escalated incidents, four Attention rows and one Needs You ticket, T820. T820 stays OPEN and human-required: the 04:27Z private owner read was unavailable, and 10:27Z is the next actual scheduled read, not a forced check. The pinned diagnostic `51846dc` received all three APPROVE_WITH_NITS votes, passed 847 tests and merged as `209780aa4907bda9b42dbb8ae6801e9fd6c69f73` at 06:50:43Z; docs `324c237` received its GLM raiser APPROVE_WITH_NITS and merged as this page's base `f943ad0c69a214c2c0d695ce0d376fdec6cec60b` at 06:49:44Z. Backend, worker, Beat and seller-profile deployments at that exact backend merge were active SUCCESS by 06:53Z; `/api/health` and `/health` returned 200 healthy, and migration head equalled current `s1757_users_auth_generation` with no drift. The bounded 06:52–06:53:50Z backend log window had zero candidates, no validated marker, cause or recovery. These facts do not prove the customer journey or a privacy/retry fix; do not requery the private provider or request more private data for this check.

Catalogue PR 262 entered after v655 and normal publishing subsequently produced v656, v657 and v658. The last independently verified v658 snapshot was generated at 2026-09-28T05:24:17Z: 126 retained projects, 47 work rows (43 `in_progress`, four `merged_undeployed`), 79 evidence gaps (71 `completion_verification_pending`, eight `live_undocumented`), 459 visible refs, six unnamed, zero certificates, zero safe-delete rows, zero loaded alerts shown and one Needs You ticket, T820. Fresh normal Chrome at 07:09Z showed the same projection. Zero loaded alerts describes the projection, not provider health. Forty-four individual manual closeouts were verified: 39 old GitHub demotions (29 accepted-source, nine retired and one negative control), four legacy P0, and new hidden CI `db851` resolved at 06:12:31Z by accepted source with a same-workflow witness. `db851` never appeared in human views, so there was no visible badge drop. Four paused OAuth/preview refs remain open and unmerged under Max's prior stop; do not claim their retirement or repair. Retained developer refs are inventory, distinct from new failures.

**PR 272 coverage candidate and operator sequence (S1760).** [Source PR 272](https://github.com/aidotmarket/koskadeux-mcp/pull/272) changes only the runbook-coverage helper and tests. Pinned source `51560ce5fcdb621f1338898d51952d8a14a2ba62` requires an explicit configured relative `.md` path that exists on `origin/main` and appears exactly once in its current `INDEX.md` before coverage is positive. An unavailable or invalid index yields unknown first; a matching word in a label, an unindexed path, a legacy receipt, or a displayed link does not prove coverage. The frozen v658 projection has 88 of 126 `runbook_indexed=true` flags without validated paths; if candidate 272 were accepted and normally published against the same 459 refs, 60 deployed rows would move from `completion_verification_pending` to `live_undocumented` because coverage is unproved. This is a projected reclassification, not a fresh board count or zero-gap claim. Candidate 272 has no grading membership, positive certification or delete-authority change. CC, GLM and DeepSeek source reviews and exact publisher acceptance are all PENDING; describe it as staged until unanimous review, exact merge, normal publisher execution and GET plus Chrome acceptance.

Operate from the current snapshot and its timestamp. Isolate a suspect row by exact repo/full branch and tip, then inspect its deployment attestation, explicit configured runbook path and current unique index entry. For a missing path, repair only the appropriate source/catalogue and index through their normal reviewed route; leave `live_undocumented` visible until a fresh accepted publisher and Chrome agree. For missing or malformed metadata, index or feed, preserve unknown and visible rows; do not turn an unavailable read into zero. For unrelated word collisions, require the explicit path check rather than a label match. After publication, verify the executed normal CLI source by its invocation checkout and hash, clean artifact receipt, fresh board version/`generated_at`, supported GET and normal Chrome; keep the gateway marker separate. The sole publisher remains `ground_truth_open_items.py --publish`; never hand-edit `infra:open-items-board`.

**Operator read and rollback check.** Check exact Git refs, deployment attestations, validated indexed paths and separately recorded outside and legacy evidence; a false flag is not a receipt. Read project work and completion gaps as retained development inventory; read alerts and Needs You as current feed projections and inspect their supported source records before action. A missing or partial feed is unknown. Only exact `certified_done` rows may be hidden, while an outside flag or unavailable/malformed display metadata keeps a completed-looking row visible. If source or feed regresses or goes stale, show snapshot age and the source limitation, keep uncertain rows visible and withhold completion and deletion claims. Incident triage remains metadata-only: backend CI dispatch is limited and defaults to record-only, while the separate remediator has `execute_allowed=false`; neither establishes shared automatic recovery.

Deployment proof uses the repository's existing delivery model. `koskadeux-mcp` uses ancestry from the deployed-SHA marker; `runbooks` treats merge to `main` as deployment; and the centrally hosted backend, customer frontend, and ops dashboard use one read-only Railway project snapshot pinned to the expected production environment, service name, source repository, `main` branch, successful active deployment, exact commit SHA, deployment UUID, and timezone-aware deployment time. The resolver refreshes an exact provider-reported commit before declaring it absent, so a stale local checkout cannot manufacture an attestation warning. A shared Railway read failure is reported once; a malformed or missing individual service leaves only that repository unknown and does not discard healthy service evidence.

AIM Data is customer-hosted, so it has no single central production deployment. Its deployment-equivalent evidence is the latest stable `aim-data-v*` GitHub release tag plus a completed successful `AIM Data Release` workflow at that exact tag and commit. That existing workflow publishes the GHCR image, verifies its version label and multi-architecture manifest, smoke-tests the container, and only then creates the GitHub release. A release or matching-workflow read failure leaves AIM Data `production_unknown`; it never becomes deployed from a tag alone.

These evidence readers observe Git, deployment and runbook state; they do not add permission gates or stop delivery. An unreadable migration baseline reveals merged refs; missing deployment or documentation proof stays unknown and cannot establish completion. The script never consults Living State for membership or stage.

S1605 implementation evidence, 2026-08-26: `aidotmarket/koskadeux-mcp` PR 180 merged as `e82e4f0f69b2833c537d9629f2a37140c2a8801e`; the existing automatic reloader fast-forwarded the clean canonical checkout and recorded that exact SHA in the deployed marker at 14:39:12Z. The focused resolver suites passed 45 tests, final-head GitHub Tests and Drain On Close Host Route checks were green, and final CC/Kimi/GLM review of candidate `981370ea7b55437b8dfae5321cb550ae96cbeda1` returned approval with non-blocking nits only. Publishing from the deployed merge produced `infra:open-items-board` v312 at `2026-08-26T14:40:34Z` with current provider evidence for backend `632f7fbe82`, frontend `ac3a15a764`, ops `f093293859`, and AIM Data release `aim-data-v1.22.5` at `6d0b089520`. Authorized operator Chrome then showed 10 visible open rows, four certified-done retained rows hidden, zero alerts, and none of the five former deployment-evidence warnings. Chrome recovery and identity-separation evidence is maintained in `runbooks/chrome-browser-use.md`.

Branch deletion remains manual. A current safe-to-delete decision requires independent positive evidence for all four DONE checks against exact refs, plus a current producer result that supports `safe_to_delete_branch=true`; neither accepted PR 263 nor staged PR 272 provides one. Never infer safety from a former `certified_done` label or a false/absent outside flag, and never override `production_unknown`. Preserve exact expected-tip leases and archive unique uncontained tips before any separately authorized removal. The UI never uses Living State build status to hide a row.

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
4. **Ship:** branch off `origin/main` and open a PR. Apply the current review authority in [Council](runbooks/council.md) and [Council Gate Process](runbooks/council-gate-process.md), especially their ACTIVE OVERRIDE and tier/re-review rules. Specs and trust-area changes take the full unanimous panel; a small nonsensitive change can take one reviewer, and blocking raisers re-review the delta unless design or trust changes. MP authors/builds and does not vote on its own artifact; explicit non-voting second opinions retain their separate status. After the applicable review, squash-merge to `main`; a push to `main` triggers the Railway build and Deploy Receipt workflow.
5. **Verify live:** the JS bundle is hash-named, so confirm a deploy by fetching the live bundle and grepping for a string you added:
   ```sh
   b=$(curl -s https://ops.ai.market/ | grep -oE '/assets/[^"]+\.js' | head -1)
   curl -s "https://ops.ai.market$b" | grep -c "<a string you added>"
   ```

Conventions worth keeping: UI data lives at `entity.body.*` after `buildQueueItemToEntity`-style mapping; lifecycle writes are version-checked (pass the `version_stamp`; handle 409 by refetching); never put the internal API key anywhere but the localStorage config the console already uses.

## When it breaks

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
| Build Queue timestamp stays stale and the publisher reports `PosixPath is not JSON serializable` | The deployment-marker `Path` crossed into a nested deployment attestation; the local snapshot may also have been truncated before serialization failed. | Do not edit the board. Confirm the deployed producer contains the S1605 boundary conversion and serialize-before-open repair, rerun the sole publisher, then verify local JSON, Living State version/timestamp, and the rendered page as described above. |

## Conformance

Keep this narrative page aligned with the deployed dashboard and its current data sources.

---

*Created: S363 (2026-04-01). Updated: S1760 (2026-09-28) — accepted strict CLI classifier evidence, dated v658 projection and staged PR 272 coverage contract; joint source review and publisher acceptance remain pending.*
