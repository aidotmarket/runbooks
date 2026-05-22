# Comprehensive Runbook Audit — S690

**Date:** 2026-05-22
**Auditor:** Vulcan (Claude Opus 4.7) on /Users/max/Projects/runbooks
**Scope:** All runbooks under `/Users/max/Projects/runbooks/` (root + `runbooks/` subdir; specs + templates inventoried, not deep-audited)

---

## 1. Executive summary

This audit covered **35 runbook files** (29 at repo root, 5 under `runbooks/`, 1 template) plus the spec/standard directory. The collection is **dense, deeply referenced, and largely accurate** — runbooks added or refreshed since 2026-04-20 are tightly aligned with source (auth-signup-flow, data-requests, cloudflare-and-dns, crm-pipeline, crm-target-state). The older legacy band (2026-03-07 through 2026-04-10) is where stale claims concentrate.

**Total HIGH-severity correctness findings: 6.** Of these, three are infrastructure transport drift (one runbook authoritatively contradicts two others on what tunnel serves `mcp.ai.market`), one is a brand/product name conflict (AIM Channel vs. AIM Data in shipped code), and two are documented-but-not-fixed split-brain in scheduled work (morning-briefing.md misidentifies the briefing trigger). **MED findings: 11.** **LOW findings: 12.**

**Total structural recommendations: 18** — 4 consolidations, 2 splits, 5 renames/retirements, 4 new runbooks needed, 3 structural-standard gaps. The §A-§K standard is currently followed only by the 5 runbooks under `runbooks/` (council family). The other 30 follow informal "What it does / How it works / When it breaks" formatting. Whether they SHOULD adopt §A-§K is a scope question above this audit, but the inconsistency itself is a structural finding.

**Overall verdict: HEALTHY-WITH-DRIFT.** No runbook is a hazard to use today, but five runbooks contain claims a stateless reader would act on and be wrong. The cloudflare-and-dns.md S688 work created a known-good baseline that should be propagated outward (retire `cloudflare-worker.md`, update `mcp-gateway.md`, reconcile `infra:council-comms` references).

**Note on the §A-§K standard:** the task brief described §A-§K as "Context, Pre-flight, Step-by-step, Verification, Rollback, Risks, Logging, Comms, Monitoring, Glossary, Cross-refs." The actual standard in `templates/runbook.template.md` and `specs/BQ-RUNBOOK-STANDARD.md` uses different section names: Header, Capability Matrix, Architecture & Interactions, Agent Capability Map, Operate, Isolate, Repair, Evolve, Acceptance Criteria, Lifecycle, Conformance. This audit measures against the template-as-shipped, not against the task brief description. The §A-§K reference convention is otherwise consistent.

---

## 2. Inventory

### Root-level runbooks (29)

| File | Mtime | Lines | Primary pillar | Description |
|---|---|---|---|---|
| `ai-market-backend.md` | 2026-05-06 | 188 | ai.market | Central FastAPI backend overview, deploy, alembic gotchas |
| `ai-market-frontend.md` | 2026-04-01 | 91 | ai.market | Next.js marketplace frontend; pages, deploy, env |
| `aim-data-release-process.md` | 2026-04-10 | 90 | AIM-Channel | "AIM Data" release script + GHCR multi-arch (uses `AIM Data` name) |
| `aim-node-release-process.md` | 2026-04-08 | 85 | AIM-Node | AIM Node `scripts/release.sh` + Docker build |
| `aim-node.md` | 2026-04-08 | 250 | AIM-Node | AIM Node runtime architecture, wire protocol, security |
| `aimarket-mcp-server.md` | 2026-04-01 | 91 | ai.market | Public MCP server (PyPI/npm) — buyer-facing tools |
| `allai-agents.md` | 2026-05-06 | 112 | ai.market | allAI agent host, service bus, agent roster |
| `auth-signup-flow.md` | 2026-05-06 | 146 | ai.market | OAuth + magic-link sign-up + P0 CRM-blocks-signup issue |
| `bq-124-retro-verification.md` | 2026-04-19 | 179 | ai.market | BQ-124 Celery beat retro-verification procedure |
| `celery-infrastructure-deployment.md` | 2026-04-19 | 399 | ai.market | Production Celery topology on Railway (web/worker/beat) |
| `cloudflare-and-dns.md` | 2026-05-22 | 399 | ai.market + vectoraiz | **Canonical** Cloudflare/DNS/Workers/Tunnel runbook (S688) |
| `cloudflare-worker.md` | 2026-04-17 | 199 | ai.market + vectoraiz | Legacy — covers `vectoraiz-installer` + DMS Worker (subsumed) |
| `crm-architecture.md` | 2026-04-24 | 210 | ai.market | CRM data model + service inventory (V1/V2 bridge) |
| `crm-pipeline.md` | 2026-04-24 | 90 | ai.market | CRM operational entry points (post-S500 rewrite) |
| `crm-target-state.md` | 2026-04-24 | 469 | ai.market | CRM target-state spec / R6 capability matrix |
| `data-requests.md` | 2026-05-06 | 115 | ai.market | Buyer-initiated data-request surface + S574 incident |
| `docker-testing.md` | 2026-03-07 | 46 | AIM-Channel | Local Docker testing for vectorAIz/AIM-Channel on Titan-1 |
| `dual-brand-vectoraiz-aim-channel.md` | 2026-04-10 | 79 | AIM-Channel | vectorAIz vs AIM Channel brand-skin architecture |
| `email-drafting.md` | 2026-03-07 | 37 | Council | Vulcan email drafting + mailto: workflow |
| `gcp-auth.md` | 2026-04-30 | 149 | ai.market | GCP OAuth consent + Gmail tokens + Vertex Express API |
| `gmail-drop-pipeline.md` | 2026-04-04 | 161 | ai.market | drop@ai.market → CRM ingest path |
| `infisical-secrets.md` | 2026-04-30 | 132 | ai.market | Self-hosted Infisical at `secrets.ai.market` |
| `marketing-tab.md` | 2026-03-07 | 39 | ai.market | ops.ai.market Marketing tab notes (very thin) |
| `mcp-gateway.md` | 2026-05-06 | 123 | Council | Koskadeux MCP gateway/process tree (claims Tailscale transport) |
| `meet-records-pipeline.md` | 2026-03-30 | 82 | ai.market | Google Meet Gemini Notes → CRM (planned per S342) |
| `morning-briefing.md` | 2026-03-30 | 116 | ai.market | 07:00 UTC CRM briefing (claims CRM-Steward asyncio timer) |
| `ops-ai-market.md` | 2026-05-06 | 107 | ai.market | `ops.ai.market` Ins{ai}ts dashboard — tabs + endpoints |
| `rtk-token-optimization.md` | 2026-04-04 | 119 | Council | RTK token-killer CLI proxy + agent hooks |
| `seo-infrastructure.md` | 2026-04-01 | 87 | ai.market | Search Console + Bing Webmaster + AI-crawler discovery |
| `seo-seller-validation.md` | 2026-04-01 | 67 | ai.market | Per-listing SEO readiness scores |
| `session-lifecycle.md` | 2026-03-07 | 60 | Council | Vulcan session boot/close + recovery cache |
| `vulcan-configuration.md` | 2026-03-30 | 118 | Council | Memory/context architecture (Anthropic memory edits, layers) |
| `vz-release-process.md` | 2026-03-07 | 59 | AIM-Channel | vectorAIz release script (RC + promote) |

### `runbooks/` subdirectory (council family, §A-§K conformant)

| File | Mtime | Lines | Pillar | Description |
|---|---|---|---|---|
| `runbooks/agent-dispatch.md` | 2026-04-30 | 407 | Council | Dispatch mechanics — council_request/dispatch_mp_build/council_hall |
| `runbooks/build-queue-reconciliation.md` | 2026-04-29 | 145 | Council | Trigger A-D reconciliation of LS↔BQ↔git evidence |
| `runbooks/council.md` | 2026-04-30 | 373 | Council | Council operating model — roster, gates, dispatch patterns |
| `runbooks/council-gate-process.md` | 2026-04-30 | 424 | Council | BQ 4-gate process + cross-review enforcement |
| `runbooks/council-hall-deliberation.md` | 2026-04-30 | 504 | Council | Multi-agent deliberation, synthesis, cross-pollination |

### `specs/` (9 files — not runbooks; design/standard specs)

`BQ-AUTONOMOUS-OPERATIONS-chunk-a.md`, `BQ-AUTONOMOUS-OPERATIONS.md`, `BQ-COUNCIL-RUNBOOK-CONFORMANCE-GATE1.md`, `BQ-COUNCIL-RUNBOOK-CONFORMANCE-GATE2.md`, `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING-CI-AUDIT.md`, `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING-GATE1.md`, `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING-GATE2.md`, `BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md`, `BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md`, `BQ-RUNBOOK-STANDARD.md`, `bq-runbook-decentralization-gate1.md`. Per `README.md`, `BQ-RUNBOOK-STANDARD.md` is the design contract.

### `templates/`

`runbook.template.md` — the canonical §A-§K scaffold.

---

## 3. Correctness findings

### HIGH

#### H-1. `mcp-gateway.md` declares Tailscale Funnel as the active mcp.ai.market transport — actually cloudflared

**Runbook:** `mcp-gateway.md` §Transport, §Backup admin path, §History
**Verbatim claim:** "**Transport:** Tailscale Funnel (replaced Cloudflare Tunnel pre-S572 per `config:resource-registry`)" (`mcp-gateway.md:8`). And: "**Pre-S572** — Tailscale Funnel migration replaced Cloudflare Tunnel as the `mcp.ai.market` public transport… The `com.koskadeux.cloudflared` LaunchAgent is decommissioned and pending plist removal by SysAdmin." (`mcp-gateway.md:122`).

**Actual source:** `cloudflare-and-dns.md:381` says verbatim: "**Pre-S572** — Resource registry + `mcp-gateway.md` claim Tailscale Funnel replaced Cloudflare Tunnel for `mcp.ai.market`. **Migration did not complete** — cloudflared remains the active transport (S688 verification)." Live verification: `launchctl list | grep cloudflared` shows `com.koskadeux.cloudflared` PID 2041, status 1 (active). `cat ~/Library/LaunchAgents/com.koskadeux.cloudflared.plist` (verified at audit time) shows `cloudflared tunnel … run koskadeux` is the program argument. `curl -s -o /dev/null -w "%{http_code}" https://mcp.ai.market/.well-known/oauth-protected-resource` returns `200`. DNS resolution per `cloudflare-and-dns.md:40`: `mcp.ai.market` proxied → `007ddc34-de07-474c-adbc-a648663b9c78.cfargotunnel.com` (a Cloudflare Tunnel address, not Tailscale).

**Severity:** HIGH — A stateless reader of `mcp-gateway.md` will (a) believe Tailscale daemon is the path-to-recover, (b) think the cloudflared LaunchAgent is "decommissioned" and try to remove it, (c) misdiagnose any 502/504 from `mcp.ai.market`. The reader will look at `tailscale funnel status` instead of `launchctl kickstart -k com.koskadeux.cloudflared`.

**Recommended fix:** Rewrite the Transport, Architecture, Restart, and History sections of `mcp-gateway.md` to match `cloudflare-and-dns.md`. Add an explicit "mcp.ai.market transport is cloudflared, not Tailscale Funnel — see cloudflare-and-dns.md drift item 1" callout at the top. Until completed, both runbooks must point at each other so a reader can reach the correct one. Coordinate with whoever owns `infra:council-comms` / `config:resource-registry` so the Living State entity doesn't keep propagating the stale claim. (This is item #1 in the §S688 drift inventory in `cloudflare-and-dns.md`.)

---

#### H-2. `morning-briefing.md` attributes the 07:00 UTC briefing to a CRM-Steward asyncio timer — actually APScheduler-driven and decoupled from CRM Steward

**Runbook:** `morning-briefing.md` §How it works → Daily timer (automatic)
**Verbatim claim:** "Railway (ai-market-backend) boots → CRM Steward agent starts via AgentHost → asyncio `_daily_timer_loop()` waits until 07:00 UTC → Calls `CRMBriefingService.send_daily_briefing()` DIRECTLY (no event bus)" (`morning-briefing.md:13-19`). And: "`app/allai/agents/crm_steward.py` | `_daily_timer_loop()` fires at 07:00 UTC (automatic path)" (`morning-briefing.md:37`).

**Actual source:** `app/core/scheduler.py:214-220`:
```
async def send_morning_briefing_job():
    """Send daily CRM briefing email. Runs at 07:00 UTC via APScheduler.

    This is intentionally decoupled from AgentHost/CRM Steward to minimize
    failure modes. The briefing is a read + send — it doesn't need the
    agent event system.
    """
```
The job is registered in the same file at line 810 with `CronTrigger(hour=7, minute=0, timezone="UTC")` and `id="morning_briefing"`. The `_daily_timer_loop` in `app/allai/agents/crm_steward.py:330` exists but its docstring at line 332 calls it the "Daily maintenance timer" (BQ-078/S100) — not the briefing dispatcher. `crm-pipeline.md:31` correctly attributes the briefing to APScheduler at `scheduler.py:214` (cron registration at `:805` — actually `:810` — minor off-by-five). `crm-architecture.md:144` describes the briefing as scheduler-triggered.

**Severity:** HIGH — A reader debugging a missed briefing will (a) look at CRM Steward registration / agent count, (b) consider the routing policy whitelist, and miss the actual scheduler/CronTrigger registration path entirely. The runbook also lists `_handle_manual_briefing` / `CRM_MANUAL_BRIEFING` event types — grepping crm_steward.py for them returns zero matches, suggesting that path was also retired.

**Recommended fix:** Rewrite §How it works → Daily timer to point at `app/core/scheduler.py:214 send_morning_briefing_job` and the cron registration at `:810`. Remove the "CRM Steward → asyncio → _daily_timer_loop" claim or relabel the loop as "daily maintenance, not briefing." Verify the manual-trigger path (`POST /api/v1/crm/admin/send-briefing`, the `CRM_MANUAL_BRIEFING` event, `_SOURCE_EVENT_TYPE_ALLOW`, `crm.admin.send_briefing` source) against current code before reasserting it; if retired, mark this section "Historical (S341)."

---

#### H-3. Naming conflict — runbook collection uses both "AIM Channel" and "AIM Data" for the same product

**Runbook:** `dual-brand-vectoraiz-aim-channel.md` and `aim-data-release-process.md`
**Verbatim claim 1:** "Names decided by Council Hall consensus: MP + AG unanimous, Vulcan concurred. … 'AIM Channel' chosen for data (dynamic path feeding the marketplace) … Rejected: AIM Data (generic/trademark)" (`dual-brand-vectoraiz-aim-channel.md:74-78`).
**Verbatim claim 2:** "# AIM Data Release Process" (`aim-data-release-process.md:1`); "release-aim-data.sh rc patch | RC tag | aim-data-v0.0.2-rc.1" (`aim-data-release-process.md:33`); "ghcr.io/aidotmarket/aim-data" (`aim-data-release-process.md:72`).

**Actual source:** `/Users/max/Projects/vectoraiz/vectoraiz-monorepo/scripts/release-aim-data.sh` exists. The script's own banner reads: "**AIM Data** Release Script (v2)" and uses `IMAGE="ghcr.io/aidotmarket/aim-data"`, `TAG_PREFIX="aim-data-"`, `COMPOSE_FILE="docker-compose.aim-data.yml"`. Installer paths: `installers/aim-data/install.sh` and `installers/aim-data/install.ps1`. `cloudflare-and-dns.md:96` confirms `get.ai.market/aim-data*` routes the `get-ai-market` Worker.

**Severity:** HIGH — There is a real semantic ambiguity. Either (a) "AIM Channel" was the decision, the shipped scripts/installers/image are out-of-spec and should rename, or (b) "AIM Data" is the de-facto product name and the dual-brand runbook is recording a decision that was reversed. Today the runbook collection asserts both. A reader of `dual-brand-vectoraiz-aim-channel.md` will look for "AIM Channel" branding in code and find none.

**Recommended fix:** Reconcile with Max which is correct. If "AIM Data" is canonical now, update `dual-brand-vectoraiz-aim-channel.md` to record the reversal + rationale, rename the runbook to `dual-brand-vectoraiz-aim-data.md`, and update the rejected-names list. If "AIM Channel" is canonical, file the renames as a real BQ (scripts, installer dirs, GHCR image, CF Worker route, docker-compose file). Either way, the runbook collection should not assert both.

---

#### H-4. `cloudflare-worker.md` is the superseded runbook but is not marked retired

**Runbook:** `cloudflare-worker.md` (entire file)
**Verbatim claim:** None — the file does not mark itself as superseded. It still claims to be the live source for `vectoraiz-installer` and the DMS Worker. `vz-release-process.md:88` references it as a live cross-ref.

**Actual source:** `cloudflare-and-dns.md:3` declares: "**Supersedes the prior `cloudflare-worker.md` (now Worker-detail subsection of this doc) and the partial Cloudflare table in `ai-market-backend/docs/core/INFRASTRUCTURE.md`**." And `cloudflare-and-dns.md:388` says: "`cloudflare-worker.md` — legacy runbook; content is fully subsumed here. Mark deprecated." It has been three weeks (Apr 17 → May 22) and the deprecation mark hasn't landed.

**Severity:** HIGH (procedural) — Two runbooks claim authoritative coverage of the same area. The newer one is more accurate (correctly notes cloudflared is the live tunnel, lists all four Workers including `get-ai-market` and `aim-node-installer`, captures the DNS inventory). A reader landing on `cloudflare-worker.md` from a stale link will get an incomplete picture.

**Recommended fix:** Add a "DEPRECATED — see `cloudflare-and-dns.md`" banner at the top of `cloudflare-worker.md`. Either delete the file or reduce it to a one-line stub pointing at the canonical runbook. Update the cross-ref in `vz-release-process.md:88`, `aim-data-release-process.md:90`, and `aim-node-release-process.md:85` (all three list `cloudflare-worker.md` under "Related").

---

#### H-5. `mcp-gateway.md` still lists the `com.koskadeux.cloudflared` LaunchAgent as decommissioned/pending plist removal

**Runbook:** `mcp-gateway.md` §Processes block (just below the launchd table)
**Verbatim claim:** "The legacy `com.koskadeux.cloudflared` agent is decommissioned (registry: 'Tailscale Funnel has replaced Cloudflare for mcp.ai.market exposure'); SysAdmin follow-up is to remove the stale plist entirely." (`mcp-gateway.md:36`).

**Actual source:** `launchctl list | grep com.koskadeux.cloudflared` returns PID 2041, status 1 — actively running. The plist `/Users/max/Library/LaunchAgents/com.koskadeux.cloudflared.plist` exists, has `KeepAlive=true`, and runs `cloudflared tunnel run koskadeux`. `cloudflare-and-dns.md:325` calls out this exact contradiction as drift item #5.

**Severity:** HIGH — A SysAdmin acting on this runbook claim might remove the plist, killing `mcp.ai.market`. This is the load-bearing process for the entire MCP gateway public surface.

**Recommended fix:** Until H-1 is resolved, replace the "decommissioned, plist pending removal" line with: "The `com.koskadeux.cloudflared` LaunchAgent IS the active transport for `mcp.ai.market` despite resource-registry claims to the contrary. Do not remove. See `cloudflare-and-dns.md` drift item 1 / 5."

---

#### H-6. `crm-target-state.md` §6 row #4 still references "16 skills in manifest, 11 public, but 23+ decorated"

**Runbook:** `crm-target-state.md:354`
**Verbatim claim:** "Steward skill fragmentation: 16 skills in manifest, 11 public, but 23+ decorated in service-bus — many not exposed → **BQ-CRM-AGENT-COVERAGE**" (`crm-target-state.md:354`).

**Actual source:** Same runbook, §3 (line 193): "Current Skills (**28** `@skill`-decorated in `crm_steward_skills.py`; public/internal classification pending re-audit under BQ-CRM-USER-SCOPING D07)." Verified count: `grep -c "@skill" app/services/crm_steward_skills.py` returns 29 matches (one likely is a comment/docstring; the runbook's "28" is plausibly correct as the decorator count). The R6 refresh note at the top of `crm-target-state.md:5` already says "skill count corrected from 16→28 decorated skills in `crm_steward_skills.py`" — but the §6 row was not updated.

**Severity:** HIGH (internal contradiction in same document) — The R6 lifecycle note announces a correction that the body did not receive. A reader cross-checking against §6 to plan a BQ will plan against stale numbers.

**Recommended fix:** Update `crm-target-state.md:354` to read "Steward skill fragmentation: 28 decorated, 11 published public, public/internal classification pending re-audit under D07." Verify §3's count against current source as part of the same edit.

---

### MED

#### M-1. `mcp-gateway.md` lists `com.koskadeux.lilly` and `com.koskadeux.council-hall` in the process table without ports

**Runbook:** `mcp-gateway.md:33-34`
**Claim:** "`lilly_server.py` | — | `com.koskadeux.lilly` | Companion service. / `council-hall` | — | `com.koskadeux.council-hall` | Council hall service."

**Actual:** Both exist as launchctl-registered processes and both files exist (`lilly_server.py`, `council_hall/`). The runbook says "—" for port but doesn't say what they actually do operationally. Acceptable, but the audit pass for H-1 should also confirm whether these are inside the MCP path or peripheral.

**Severity:** MED. **Fix:** Confirm `lilly_server` and `council-hall` LaunchAgent process scope and add a one-line clarification, or leave with a note that they are peripheral to MCP tool dispatch.

---

#### M-2. `mcp-gateway.md` boot-gate text references `/api/call` boot gate behaviour — verify against current `koskadeux_server.py`

**Runbook:** `mcp-gateway.md:60, 97, 107`
**Claim:** "The boot gate is enforced at the HTTP `/api/call` layer, so before any other tool call you must re-run: `kd_session_open → kd_session_plan`."

**Actual:** `koskadeux_server.py` exists (61.7K). Spot-grep finds the file but the audit did not exhaustively re-verify the boot-gate logic. Listed under "verify before recommending" since this is the type of operational claim a reader will act on.

**Severity:** MED. **Fix:** During the same revision pass for H-1, re-verify boot-gate text against current code, especially the `kd_recovery_write` exemption and the 5-15 minute reconnection note.

---

#### M-3. `morning-briefing.md` references `_handle_manual_briefing` and `CRM_MANUAL_BRIEFING` event — not found in source

**Runbook:** `morning-briefing.md:24-32, 37-38, 99-103`
**Claim:** Event-driven manual path: `POST /api/v1/crm/admin/send-briefing` → publishes `CRM_MANUAL_BRIEFING` event → routing policy gate → `_handle_manual_briefing()` in `crm_steward.py`. Also: "Add source to `_SOURCE_EVENT_TYPE_ALLOW` in `routing_policy.py`."

**Actual:** `grep -n "_handle_manual_briefing\|CRM_MANUAL_BRIEFING\|crm.admin.send_briefing" app/allai/agents/crm_steward.py` returned zero matches in the spot-check (only one match elsewhere). Not deeply verified — the event might be defined in a different module, or it might have been removed as part of the S500 retirement of `crm_agent_request.py` and related event paths.

**Severity:** MED. **Fix:** Verify the manual-trigger path against current source. If retired, remove from runbook or mark "Historical." If the curl endpoint at `/api/v1/crm/admin/send-briefing` still exists but takes a different path, document that.

---

#### M-4. `crm-architecture.md` references `crm_briefing_service.py` as "RETIRED" but `morning-briefing.md` still warns to avoid the Postmark import

**Runbook A:** `crm-architecture.md:56` — "RETIRED (not present in repo as of S500) — see `crm_briefing_service_gmail.py`"
**Runbook B:** `morning-briefing.md:40` — "Legacy Postmark-based version (DO NOT USE — Postmark not configured)" and `morning-briefing.md:58-62` warns "NOT the Postmark version: `from app.services.crm_briefing_service import CRMBriefingService` — WRONG — Postmark API key is not set, silently fails"

**Actual:** Not directly verified at file level. `crm-architecture.md` is post-S500 (2026-04-24); `morning-briefing.md` is 2026-03-30 (pre-S500). If `crm_briefing_service.py` is genuinely removed from the repo, the warning in `morning-briefing.md` about "Postmark vs Gmail" import confusion no longer applies — there's no Postmark version to accidentally import.

**Severity:** MED. **Fix:** Verify presence of `app/services/crm_briefing_service.py` (without `_gmail`). If absent, update `morning-briefing.md` row #6 in the diagnostic table.

---

#### M-5. `vulcan-configuration.md` claims memory cap is 30 slots × 500 chars — not verified against current Anthropic memory subsystem

**Runbook:** `vulcan-configuration.md:15`
**Claim:** "Max slots: 30 (500 chars each)"

**Actual:** This is an Anthropic-platform claim, not a code claim — the audit cannot verify it from the local repos. Listed in §Open questions; treated as MED because runbook is from Mar-30 and the platform may have changed.

**Severity:** MED. **Fix:** Cross-check with current Anthropic platform documentation / memory_user_edits tool behavior. If the cap has changed, update the runbook.

---

#### M-6. `mcp-gateway.md` `/api/admin/*` 404 ingress rule appears in `cloudflare-and-dns.md:270` but rationale is missing in mcp-gateway.md

**Runbook A:** `cloudflare-and-dns.md:270` — "`mcp.ai.market` path `^/api/admin/.*$` returns 404"
**Runbook B:** `mcp-gateway.md` — does not mention the admin-path 404 rule.

**Actual:** Both runbooks describe the same architecture, but only one mentions the ingress rule. A reader of `mcp-gateway.md` debugging a 404 on `/api/admin/...` won't find the explanation.

**Severity:** MED. **Fix:** Cross-reference the admin-path 404 rule in `mcp-gateway.md`'s troubleshooting table when revising for H-1.

---

#### M-7. `celery-infrastructure-deployment.md` and `morning-briefing.md` both describe scheduled jobs but diverge on the scheduler used

**Runbook A:** `celery-infrastructure-deployment.md` lists Celery Beat as the scheduler for `process-support-sla-breaches`, `qdrant-reconciler-nightly`, `kd-janitor-weekly`, etc. (`celery-infrastructure-deployment.md:172-183`).
**Runbook B:** `morning-briefing.md` says APScheduler (or rather, the CRM-Steward asyncio loop). `crm-pipeline.md:31` correctly says APScheduler.

**Actual:** `app/core/scheduler.py` is APScheduler-based and registers `morning_briefing` (line 810) plus other jobs. Celery is a separate scheduler for the celery-managed tasks. The two coexist but the runbooks don't make the boundary clear: which jobs use APScheduler vs which use Celery Beat?

**Severity:** MED. **Fix:** Add a short table in `celery-infrastructure-deployment.md` or a new top-level "scheduled-jobs.md" that names every recurring backend job, names which scheduler runs it (APScheduler vs Celery Beat), and points to the registration site. The two schedulers running in parallel is fine; the absence of a single map is the gap.

---

#### M-8. `mcp-gateway.md` history section refers to S519 / S520 / pre-S572 — but pre-S572 claim is now known to be wrong (per H-1)

**Runbook:** `mcp-gateway.md:121-123`
**Claim:** "**Pre-S572** — Tailscale Funnel migration replaced Cloudflare Tunnel as the `mcp.ai.market` public transport"

**Actual:** Same as H-1. The History entry is the canonical source of the wrong claim. Fixing H-1 must include rewriting this history entry as a "decision pending / migration did not complete."

**Severity:** MED. **Fix:** Reword history entry to: "Pre-S572 — Plan was to migrate to Tailscale Funnel; the DNS cutover was never completed (S688 verification). cloudflared remains the live transport."

---

#### M-9. `gmail-drop-pipeline.md` says the GCP OAuth app may still be in "Testing" mode — `gcp-auth.md` says "Internal" is required and is documented as the fix

**Runbook A:** `gmail-drop-pipeline.md:74-78` — "The GCP OAuth app (`aimarket-prod`) **may still be in 'Testing' mode**. In testing mode, refresh tokens expire after 7 days."
**Runbook B:** `gcp-auth.md:14-27` — "OAuth Consent Screen — MUST BE 'Internal'" with explicit verify/fix steps. S341 history confirms it was set to Internal.

**Actual:** `gcp-auth.md` says the consent screen IS now Internal (S341). `gmail-drop-pipeline.md` still hedges as if the issue is open. A reader will be uncertain.

**Severity:** MED. **Fix:** Replace `gmail-drop-pipeline.md:74-78` with a one-line link to `gcp-auth.md` and a statement that consent screen is currently Internal (verified S341), with the recovery procedure remaining in case of future drift.

---

#### M-10. `cloudflare-worker.md` says `CLOUDFLARE_API_TOKEN` is in "Infisical (ai-market/prd)" — `cloudflare-and-dns.md` says project `bd272d48…` env `prod`

**Runbook A:** `cloudflare-worker.md:43` — "API token: `CLOUDFLARE_API_TOKEN` in Infisical (ai-market/prd) / Railway env"
**Runbook B:** `cloudflare-and-dns.md:21` — "API token: `CLOUDFLARE_API_TOKEN` in Infisical `ai-market-backend` project (id `bd272d48-c5a1-4b52-9d24-12066ae4403c`), env `prod`"

**Actual:** Cross-references in `infisical-secrets.md:13` confirm `ai-market-backend` project id is `bd272d48-c5a1-4b52-9d24-12066ae4403c`. "ai-market/prd" is incorrect — environments are `dev / staging / prod`, not `prd`, and there is no `ai-market` project (the project is `ai-market-backend`).

**Severity:** MED. **Fix:** Either retire `cloudflare-worker.md` per H-4 or correct the line. Token location is downstream of H-4.

---

#### M-11. `cloudflare-worker.md` Cron Note has known stale comment that is documented but not fixed

**Runbook:** `cloudflare-worker.md:108` — "Cron: `*/5 * * * *` (wrangler.toml header comment says 2 min — stale comment, actual is 5 min)"

**Actual:** The runbook itself documents the stale comment but doesn't fix it in source. Not a runbook error, but a tracking gap.

**Severity:** MED. **Fix:** Either fix the wrangler.toml comment or remove the note from the runbook now that `cloudflare-and-dns.md` is canonical.

---

### LOW

#### L-1. `crm-pipeline.md` cites scheduler.py:805 — actual cron registration is at :810

**Claim:** `crm-pipeline.md:31` — "(cron trigger registered at `:805`)"
**Actual:** Line 805 begins the `async with AsyncSessionLocal() as db:` block; line 810 is `scheduler.add_job(`. Five lines off; not a misleading reference.
**Severity:** LOW. **Fix:** Update `:805` to `:810` next pass.

#### L-2. `morning-briefing.md` references `app/main.py` Python scoping bug at S341 — verify if it's still relevant for diagnostics

**Claim:** `morning-briefing.md:43, 89` — Lists this as a current diagnostic check.
**Actual:** S341 (early 2026-02) is months old. The bug was fixed. Keeping it as a diagnostic check is fine for historical context but could be moved to "History of breakage" section.
**Severity:** LOW. **Fix:** Move from active diagnostic to history.

#### L-3. `infisical-secrets.md` "Vertex Gemini key consolidation pending (S533)" — status check whether consolidation closed

**Claim:** `infisical-secrets.md:125-132` — Lists three duplicate secret names: `Vertex_Gemini_Key`, `VERTEX_API_KEY`, `VERTEX_GEMINI_KEY`.
**Actual:** S533 was the rev that updated this runbook (per the git log mention of "S533 updates"). Not verified whether the consolidation actually closed at deploy.
**Severity:** LOW. **Fix:** Check Infisical for current state; close if done.

#### L-4. `aim-node-release-process.md` lists `release.sh` commands but doesn't note version semantics conflict with VZ release script

**Claim:** AIM Node uses `release.sh rc patch`, vectorAIz uses `release.sh patch` (without `rc`). Both are valid but they're different surface.
**Actual:** Both scripts exist (`/Users/max/Projects/ai-market/aim-node/scripts/release.sh`, `/Users/max/Projects/vectoraiz/vectoraiz-monorepo/scripts/release.sh`). Different CLI flag styles for the same conceptual action; nothing technically wrong, just stylistically inconsistent.
**Severity:** LOW. **Fix:** Optional callout in either runbook that AIM Node uses `rc` subcommand, VZ uses bare-mode flag.

#### L-5. `dual-brand-vectoraiz-aim-channel.md` opens with `---` only (front-matter delimiter without yaml) — minor markdown rendering issue

**Claim:** `dual-brand-vectoraiz-aim-channel.md:1` — bare `---` with no yaml between, then closes with `---` on line 79.
**Severity:** LOW. **Fix:** Either add yaml frontmatter or remove the delimiters.

#### L-6. `ai-market-frontend.md` `app/dashboard/inquiries/page.tsx` listed — verify presence

**Claim:** `ai-market-frontend.md:38` — `/dashboard/inquiries` route.
**Actual:** Not verified — would need to grep the frontend repo. Listed as low because the audit didn't deep-verify every route table.
**Severity:** LOW. **Fix:** Optional pass: verify each row of the App Router table against current frontend repo.

#### L-7. `seo-infrastructure.md` Bing Webmaster section is thin — has setup steps but no "when it breaks" symptoms for Bing specifically

**Claim:** `seo-infrastructure.md:49-60` — Bing setup steps with no failure mode coverage.
**Severity:** LOW. **Fix:** Add a "Bing-specific symptoms" row to the troubleshooting table when convenient.

#### L-8. `cloudflare-and-dns.md` and `cloudflare-worker.md` both have a section on the multipart Worker upload pattern — duplication if cloudflare-worker.md stays

**Claim:** `cloudflare-worker.md:46-73`; `cloudflare-and-dns.md:206-234`.
**Severity:** LOW (resolved by retiring cloudflare-worker.md per H-4). **Fix:** Tied to H-4.

#### L-9. `email-drafting.md` is 37 lines — very thin, could be merged into `vulcan-configuration.md` or `crm-pipeline.md`

**Severity:** LOW. **Fix:** Tied to structural recommendation S-1.

#### L-10. `marketing-tab.md` is 39 lines, mostly defers to `ops-ai-market.md` — could be merged

**Severity:** LOW. **Fix:** Tied to structural recommendation S-1.

#### L-11. `vz-release-process.md` says S222 fixed an "accidental stable release" issue but provides only a one-line history

**Severity:** LOW. **Fix:** Optional — link to BQ if relevant.

#### L-12. `session-lifecycle.md` references `/var/tmp/koskadeux/HANDOFF.md` and others — not verified to exist at audit time

**Severity:** LOW. **Fix:** Optional verification pass.

---

## 4. Structural recommendations

### Consolidations (4)

**S-1. Merge `email-drafting.md` + `marketing-tab.md` into existing runbooks.**
- `email-drafting.md` (37 lines) → fold into `vulcan-configuration.md` as a §"Outbound email drafting" or into `crm-pipeline.md` as a §"Email drafting workflow."
- `marketing-tab.md` (39 lines) → fold into `ops-ai-market.md` as a §"Marketing tab" subsection. The existing ops-ai-market.md already documents the Marketing tab on line 26. Most of marketing-tab.md duplicates that row.
**Rationale:** Both files are too thin to justify standalone presence, and both already point at parent runbooks for the substance.

**S-2. Retire `cloudflare-worker.md`** (subsumed by `cloudflare-and-dns.md`, per H-4). Either replace with a one-line "see `cloudflare-and-dns.md`" stub or delete.

**S-3. Merge `crm-pipeline.md` capability surface into `crm-architecture.md`.**
The two runbooks describe overlapping turf — `crm-architecture.md` documents the data model + service inventory + V1/V2 bridge; `crm-pipeline.md` (post-S500 rewrite) documents the operational surface (MCP tool, briefing, scheduled ops). The split is real but the runbooks frequently restate each other (e.g., briefing schedule, dedup window, V1/V2 status). Either: (a) keep both but cross-link more tightly and remove duplicated tables; or (b) merge `crm-pipeline.md` into `crm-architecture.md` as a "§Operational entry points" subsection and let `crm-target-state.md` remain the spec-grade doc.
**Rationale:** Three CRM runbooks (architecture, pipeline, target-state) is one too many for the substance.

**S-4. Move `bq-124-retro-verification.md` into a "procedures" subdirectory or fold its job-runbook content into `celery-infrastructure-deployment.md`.**
This is a one-shot retro-verification procedure for two specific Celery beat tasks. It will become irrelevant once both are post-infra-verified. Either mark with explicit "RETIRE AFTER" condition or fold into the broader Celery runbook.

### Splits (2)

**S-5. Split `cloudflare-and-dns.md` (399 lines, dense).**
Currently bundles: DNS zones, Workers, Cloudflare Tunnel for mcp.ai.market, Worker secrets, and Drift inventory. The DNS inventory and the MCP-Tunnel sections are each large enough to merit their own subsection-as-runbook if cross-references are maintained. Optional — only do this if the file becomes unwieldy.

**S-6. Split `mcp-gateway.md` Council vs. Tunnel concerns.**
After H-1 / H-5 are fixed, `mcp-gateway.md` becomes "local process tree on Titan-1" — well-scoped. Until then, the file conflates the local process tree (correctly described) with the public transport (incorrectly described). This is more a fix than a split — once the cloudflared sections move to `cloudflare-and-dns.md`, the file shrinks naturally.

### Renames / Retirements (5)

**S-7. Mark `cloudflare-worker.md` DEPRECATED at top** (H-4).

**S-8. Mark `mcp-gateway.md` history Pre-S572 entry as "migration not completed"** (M-8).

**S-9. If "AIM Channel" is canonical (per `dual-brand-vectoraiz-aim-channel.md`), rename `aim-data-release-process.md` → `aim-channel-release-process.md` and update all "AIM Data" instances** (H-3). Conversely, if "AIM Data" is canonical, rename `dual-brand-vectoraiz-aim-channel.md` → `dual-brand-vectoraiz-aim-data.md`. The current state is incoherent.

**S-10. Resolve the §A-§K standard divergence.** The 5 runbooks under `runbooks/` (council family) follow §A-§K. The 29 root-level runbooks do not. Per `README.md:3`, "Every runbook conforms to the standard defined in `specs/BQ-RUNBOOK-STANDARD.md`" — but only 5 of 34 actually do. Either (a) the README claim is aspirational and should be reworded, (b) the 29 should be migrated to §A-§K (this is a multi-session project, not an audit-pass fix), or (c) the §A-§K standard is for the council family only and should be documented as such. Recommend (a) with explicit "Adoption status: 5/34 conformant" in the README.

**S-11. Rename `bq-124-retro-verification.md`** to make its retirement condition explicit, e.g. `bq-124-retro-verification-2026.md` or move under a `procedures/` subdir with explicit "retire after both jobs post-infra-verified."

### New runbooks needed (4)

**S-12. `scheduled-jobs.md` — single source of truth for all recurring backend work.**
Combines: APScheduler jobs (in `app/core/scheduler.py`), Celery Beat jobs (in `app/core/celery_app.py`), launchd/cron tasks (Titan-1), and Worker cron jobs (Cloudflare). Resolves M-7. A reader debugging "why didn't X run" should not need to know which scheduler owns X.

**S-13. `living-state.md` — the state CRUD + event ledger + atomic_write surface.**
`allai-agents.md:71-77` describes the build-queue lifecycle ownership and atomic_write contract, but the broader Living State surface (`infra:*`, `config:*`, `build:*` entities; state_get / state_patch / atomic_write semantics; ownership rules) does not have a dedicated runbook. The Council family's `runbooks/build-queue-reconciliation.md` references it; `vulcan-configuration.md` Layer 3 references it; but no single doc covers it.

**S-14. `vectoraiz-monorepo.md` — operating handbook for the monorepo itself.**
Currently the monorepo is referenced by `docker-testing.md` (3 lines), `vz-release-process.md` (release flow), `aim-data-release-process.md` (release flow, but with AIM Data branding), and `dual-brand-vectoraiz-aim-channel.md` (brand architecture). No runbook covers the monorepo's structure, the shared aim-core extraction (referenced in `aim-node.md:196`), the channel/theme system, or test/lint discipline.

**S-15. `external-domains.md` — domain registrar / nameserver / certificate runbook.**
`cloudflare-and-dns.md:62-64` notes the registrar-level delegation chain question ("the zone contains NS records pointing at name.com nameservers… verify the registrar-level delegation chain"). That's currently unresolved. A registrar runbook would document where the actual domain ownership lives, renewal calendar, transfer codes, and the relationship between Cloudflare-for-SaaS / partial DNS mode and the registrar.

### Structural-standard gaps (3)

**S-16. The §A-§K standard adoption is at 5/34 (~15%).** Per `README.md`, every runbook should conform. The README's adoption table currently reads "_(No systems yet conformant — Chunk 2 will add Infisical + AIM Node)_" — i.e., the README itself acknowledges incomplete adoption. Either keep this as a deliberate phased adoption (and update the README to reflect the actual phase) or commit to an adoption schedule for the remaining 29.

**S-17. No runbook lifecycle metadata on the 29 non-conformant runbooks.** The template's §J Lifecycle block (last_refresh, harness_pass_rate, etc.) does not exist on the 29 informal runbooks. A reader has no way to know which informal runbook was last verified. The mtime in git is close to this but doesn't say what "verified" means. Recommend at minimum a "Last verified: YYYY-MM-DD; verified by: …" footer per runbook.

**S-18. Cross-reference convention is inconsistent.** The Council family uses file-qualified IDs like `agent-dispatch:F-01`. The informal runbooks use prose mentions (`see "morning-briefing.md"`). When (if) §A-§K adoption proceeds, the convention should be unified.

---

## 5. Recommended action ordering

### Tier 1 — must-fix (high impact, low effort)

1. **H-1 + H-5 + M-8: mcp-gateway.md cloudflared/Tailscale transport rewrite.** One coordinated edit (~30 min) brings two HIGH findings to closure and removes the load-bearing risk that someone removes the live `com.koskadeux.cloudflared` LaunchAgent.
2. **H-2 + M-3: morning-briefing.md scheduler rewrite.** Verify against `app/core/scheduler.py:214`; rewrite §How it works to point at APScheduler; verify and update the manual-trigger curl path.
3. **H-3: AIM Channel vs. AIM Data reconciliation.** Requires a decision from Max. Once decided, the cleanup is mechanical: rename runbook(s), update cross-refs, optionally file a code-side rename BQ.
4. **H-4 + S-7 + L-8 + M-10: retire `cloudflare-worker.md`.** Add deprecation banner; update 3 cross-refs in release-process runbooks; optionally delete.
5. **H-6: crm-target-state.md §6 row #4 skill-count update.** Single-line edit.

### Tier 2 — clarifying (medium impact, low effort)

6. **M-7 + S-12: new `scheduled-jobs.md`.** Most ROI for medium effort. Resolves the APScheduler/Celery confusion and gives debug-readers a single index.
7. **M-9: `gmail-drop-pipeline.md` GCP consent screen hedging.** Replace with link to `gcp-auth.md`.
8. **M-4: `morning-briefing.md` Postmark warning** — verify legacy file is actually gone; remove or qualify the warning.
9. **M-11 + L-1 + L-2 + L-12: small line-level corrections.** Batchable.

### Tier 3 — strategic (high impact, high effort — multi-session)

10. **S-10: §A-§K adoption decision.** Whether the 29 informal runbooks should migrate to the standard is above this audit's pay grade. If yes: plan as a multi-week phased BQ. If no: rewrite the README to reflect the actual adoption scope (council family only).
11. **S-13: new `living-state.md`.** Important enough to file as a runbook BQ.
12. **S-14: new `vectoraiz-monorepo.md`.** Important for new contributors / agents.
13. **S-3: consolidate CRM trifecta.** Touches three large runbooks; do after Tier 1 settles.

### Tier 4 — optional polish

14. **S-1: merge `email-drafting.md` + `marketing-tab.md`** into parents.
15. **S-11 + S-4: `bq-124-retro-verification.md`** retire-when condition.
16. **L-3 through L-12: incremental cleanups.**

---

## 6. Open questions

1. **AIM Channel vs. AIM Data — which is canonical?** The Council Hall decision in `dual-brand-vectoraiz-aim-channel.md:74-78` chose AIM Channel. The shipped release script, GHCR image name, installer directory, docker-compose file, and Cloudflare Worker route all use `aim-data`. This requires Max's input — the audit cannot resolve it from source.

2. **Did the Tailscale Funnel migration ever begin in any meaningful way?** `cloudflare-and-dns.md:281-286` notes a parallel Tailscale Funnel surface exists on `koskadeux-10.tail30cd96.ts.net` but no DNS record points to it. Should the Tailscale path be (a) completed (cut over DNS, decommission cloudflared), (b) retired (delete the funnel surface, normalize on cloudflared), or (c) maintained as a documented backup? The runbook says "available as fallback" but if it's never been smoke-tested as a fallback, that's optimistic.

3. **Is `morning-briefing.md`'s `_handle_manual_briefing` / `CRM_MANUAL_BRIEFING` event path live?** Spot-grep returned zero matches in `crm_steward.py`. If retired (perhaps as part of the S500 `crm_agent_request.py` retirement), the runbook needs a §"Historical" section.

4. **Is `app/services/crm_briefing_service.py` (without `_gmail`) actually removed?** `crm-architecture.md:56` says yes (RETIRED, not present in repo as of S500). `morning-briefing.md:40, 58-62` says no (Postmark-based, do not import). One is stale.

5. **Are the `_railway-verify.ops.ai.market` and `_lovable.ops.ai.market` TXT records both still needed?** `cloudflare-and-dns.md:60-61` flags the second case ("two records — investigate if both still needed"). Not resolved.

6. **`crm-pipeline.md:31` cites cron registration at `scheduler.py:805` — actual is at `:810`.** Minor, but signals the runbook was written from notes rather than re-checked. Are line-number references in the other CRM runbooks similarly off-by-a-few?

7. **What is the right home for the 5 runbooks under `runbooks/`?** They use §A-§K standard. The 29 root-level runbooks do not. If §A-§K is the target standard, should the root-level runbooks migrate into the `runbooks/` subdirectory once converted? Or is the directory structure orthogonal to the standard? `README.md` does not address this.

8. **Are `lilly_server` and `council-hall` LaunchAgent processes peripheral to MCP tool dispatch, or load-bearing?** `mcp-gateway.md:33-34` lists them without ports and with thin descriptions. `cloudflare-and-dns.md` does not mention them. A reader debugging a Council Hall deliberation timeout doesn't know where to look.

---

*End of audit.*
