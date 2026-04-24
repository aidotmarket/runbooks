# CRM Pipeline

> **Status:** S500 rewrite (2026-04-24). Prior revision was pre-S400 and referenced MCP tool names (`crm_create_contact`, `crm_upsert_contact`, `crm_get_contact_360`, `crm_log_interaction`, `crm_create_task`, `crm_cancel_task`, `crm_update_task`, `crm_search_interactions`) that no longer exist in the current surface. The current agent surface is a single natural-language `crm_request` MCP tool routed through `app/mcp/crm_remote.py`. This rewrite aligns with `crm-target-state.md` R6 and `crm-architecture.md` S500.

## What it does

Manages all contacts, organizations, relationships, interactions, tasks, pipeline stages, referrals, and outbound communications for ai.market business relationships. See `crm-architecture.md` for the full data model and service inventory, and `crm-target-state.md` §2 for the complete capability matrix with status / BQ / agent / test coverage / integration columns.

## How Max and agents interact with the CRM

### 1. Primary: natural-language via `crm_request`

Max (via Claude.ai Connector or MP Mac Codex CLI) and Vulcan (via Koskadeux MCP) call a single `crm_request` tool routed through `app/mcp/crm_remote.py` (mounted at `/mcp/crm`, authless or bearer-authed via `CRM_MCP_TOKEN`). The CRM steward classifies intent and dispatches to one of **28 `@skill`-decorated functions** in `app/services/crm_steward_skills.py` (public/internal classification pending re-audit under **BQ-CRM-USER-SCOPING D07**). Each skill calls a service-layer method that writes through domain-scoped services in `app/domains/crm/**`.

**Verified end-to-end (S458 allAI-first design)**: live read trace `754792b8-efd8-4270-8415-96d916e40fa2` (find_contact), live write trace `dffad565-0cf8-4014-910d-6ed2b1fb7f3a` (create_task via 2-turn tool use).

**Incomplete as of S500** (tracked under **BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK**):

- `_dispatch_by_intent` in `app/allai/agents/crm_steward.py` does not invoke `CRMAIService` for free-text intent routing (D10)
- `_cmd_task`, `_cmd_drafts`, `_cmd_draft`, `_cmd_reject` are stubs without real service calls (D11)
- `_handle_draft_email_step` + `_handle_confirm_draft_step` are not implemented (D12)

These three gaps block Max's goal of using the CRM via Claude + MP Mac clients for full read/write.

### 2. Secondary: Telegram steward

`app/allai/agents/crm_steward.py` (~98 kB) handles Telegram bot interactions. Multi-turn conversation state persists in `crm_conversation_state` (Redis with Postgres backup).

### 3. Scheduled: morning briefing

Runs at **07:00 UTC daily** via APScheduler (`app/core/scheduler.py:214 send_morning_briefing_job`; cron trigger registered at `:805`). Renderer: `app/services/crm_briefing_service_gmail.CRMBriefingService`. Delivery: Gmail HTML.

**S499 / S500 note**: user-scoping columns (`created_by_user_id` on `crm_people` / `crm_organizations` / `crm_tasks` / `crm_interactions`) were backfilled as an emergency data restoration on 2026-04-24 because scoped briefing queries had been returning empty. Systemic fix (Alembic migration replacing the SQL + CI lint + service fallback + regression tests + `crm_briefing_contact_count` metric with alarm) is in flight under **BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK** Track 2.

## Key files

| File | Purpose |
|------|---------|
| `app/allai/agents/crm_steward.py` | Telegram steward + intent dispatch state machine |
| `app/api/v1/endpoints/crm.py` (1788 lines) | REST CRUD surface under `/api/v1/crm/*` |
| `app/api/v1/endpoints/crm_pipeline.py` | Pipeline stage endpoints |
| `app/api/v1/endpoints/crm_referrals.py` | Referral endpoints |
| `app/api/v1/endpoints/crm_support.py` | Support workflow endpoints |
| `app/api/v1/endpoints/accounting_crm.py` | Read-only contracts for Accounting (shipped S469) |
| `app/services/crm_steward_skills.py` (~109 kB) | 28 `@skill`-decorated agent skills |
| `app/services/crm_service.py` (~49 kB) | Core CRUD business logic |
| `app/services/crm_briefing_service_gmail.py` | Active briefing renderer (07:00 UTC) |
| `app/services/briefing_delivery.py` | Delivery: Telegram + Postmark + HMAC links |
| `app/services/briefing_data_service.py` | Async data assembly (audit pending per C04) |
| `app/mcp/crm_remote.py` (~23 kB) | **Primary NL agent surface** — MCP `crm_request` tool family |
| `app/models/crm.py` | V1 database models |
| `app/domains/crm/**` | V2 domain layer (party, identity, trust, commercial, revenue) |

## Agent skill catalog

28 `@skill`-decorated skills in `crm_steward_skills.py`. See `crm-target-state.md` §3 for the classification plan. Core published skills include: `find_contact`, `upsert_contact`, `add_note`, `create_task`, `complete_task`, `snooze_task`, `create_organization`, `create_relationship`, `move_contact_forward`, `get_daily_briefing`, `get_entity_context`. Service-bus-decorated but not publicly exposed: `update_contact`, `update_person`, `delete_entity`, pipeline moves, referral management, research/enrichment, admin/import.

## Daily automated operations

- **07:00 UTC**: morning briefing generation + Gmail delivery
- **Interaction dedup**: `description_hash` with 24h window (`crm_dedup_service.py`)
- **Stale contact detection**: 180+ days since last interaction
- **Auto follow-up**: new contact creation triggers 7-day follow-up task

## Known bugs and active fixes

See `crm-target-state.md` §6 for the authoritative list. Active tracking: **BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK** (P0) covers 19 items across three tracks (Track 1 emergency data restoration DONE S499; Track 2 D01–D12 systemic fix PENDING; Track 3 C01–C07 cleanup PENDING).

## Interfaces consumed by / exposed to other domains

- **Accounting**: read contracts at `/api/v1/accounting/crm/*` (shipped S469 per **BQ-CRM-INTEGRATION-CONTRACTS** Gate 4 close `1d27532`)
- **Support**: allAI-first (primary) via `crm_request`; REST at `/api/v1/crm/support/*` pending **BQ-CRM-SUPPORT-WORKFLOWS**
- **Sales**: REST at `/api/v1/crm/v2/*` — PATCH/DELETE shipped S481 per **BQ-CRM-SALES-SURFACE** B2 at commit `8315c11`

## When it breaks

See the troubleshooting table in `crm-architecture.md` "When it breaks". Quick reference:

| Symptom | First check | Likely cause |
|---------|-------------|--------------|
| Briefing email empty | Simulate scoped query against Max's `user_id` (`0a3eb2e1-8cc1-4ea9-84ce-542491784be3`); post-D05: check `crm_briefing_contact_count` metric | User-scoping columns null — see Track 1 (done) / Track 2 (pending) |
| Briefing not arriving at 07:00 UTC | `gateway.log` + Railway logs for `send_morning_briefing_job`; scheduler registry in Redis | Scheduler down, Gmail OAuth expired, service crash |
| `crm_request` from Claude/MP returns empty | Verify bearer token via `CRM_MCP_TOKEN`; check `app/mcp/crm_remote.py` routing; user lookup on recipient email | Possibly steward dispatch gap (D10/D11/D12) for intent-routed flows |
| Duplicate contacts | Email not matching on upsert | Ask: "upsert contact with email X" rather than "create contact" |
| Stale 360 view | Redis cache TTL | Wait for TTL or flush manually |

## Last updated

- **S500 (2026-04-24)** — full rewrite aligned with `crm-target-state.md` R6 and `crm-architecture.md` S500 audit.
- S222 (original) — stale: referenced retired MCP tool names; structure preserved for historical context in prior revisions.
