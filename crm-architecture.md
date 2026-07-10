# CRM Architecture

## What it is

The CRM is ai.market's system of record for people, organizations, relationships, tasks, interactions, pipeline stages, referrals, and outbound communications. It is consumed by the founder (via morning briefing + ops dashboard), AI agents (CRM steward, briefing monitors, marketing ops), and the MCP tool surface (Koskadeux).

## Data model

### V1 — Active (production)

The live production path uses these tables under `app/models/crm.py`:

- **`crm_entities`** — polymorphic base for all CRM records (soft-delete via `deleted_at`)
- **`crm_persons`** — contacts: name, email, title, linkedin, AI profile fields, optional `organization_id` → `crm_organizations`
- **`crm_organizations`** — companies: name, domain, industry, AI research fields
- **`crm_relationships`** — graph edges between any two entities (type: `referral`, `colleague`, `reports_to`, etc.)
- **`crm_interactions`** — communication log: type (`email`, `call`, `note`, `social`, `whatsapp`), direction, content, summary, `description_hash` for dedup (BQ-096)
- **`crm_tasks`** — action items: `task_type` (follow_up, draft_email, research, schedule_call, reminder, custom), `due_date`, `status`, `reasoning`, `description_hash` for dedup
- **`crm_email_drafts`** — AI-generated email drafts tied to a task (HITL review flow)
- **`crm_playbooks`** — workflow definitions (lightly used)
- **`crm_learned_preferences`** — extracted preference rules from interactions

Pipeline tables in `app/models/crm_pipeline.py`:
- **`crm_pipeline_stages`** — ordered stages: `new_lead` → `qualified` → `proposal` → `negotiation` → `closed`
- **`crm_contact_pipeline`** — person↔stage mapping (1:1 per person)
- **`crm_pipeline_history`** — audit trail of stage transitions with duration

Referral tables in `app/models/crm_referral.py`:
- **`crm_referrals`** — tracks who referred whom, with `commission_rate` and status

Other:
- **`crm_conversation_state`** — Telegram steward conversation context (`app/models/crm_conversation.py`)
- **`email_drafts`** — standalone email draft table (separate from `crm_email_drafts`) with `reviewed_at`, `sent_at` — used by `worker_service.py` for auto-drafted replies

### V2 — Domain layer (emerging, partial)

Under `app/domains/crm/` a newer architecture is being built around:

- **`party`** — canonical participant (replaces `crm_entities`)
- **`party_identity`** — external IDs (provider + external_id)
- **`party_role_binding`** — contextual roles
- Trust scoring: `party_score_event`, `party_score_snapshot`, `party_infraction`
- Commercial: `crm_opportunity`, `agreement`
- Revenue: `commission_plan`, `commission_rule`, `commission_override`, `commission_accrual`

**Current status:** V2 models exist but active API/service paths still mostly use V1. Some V1 models have `party_id` dual-write columns for bridging. Operations (tasks, interactions) are NOT yet migrated to V2.

## Service layer

All under `app/services/`:

| File | Purpose | Status |
|------|---------|--------|
| `crm_service.py` (794 lines) | Core CRUD: entity, person, org, interaction, task services | **Active — primary** |
| `crm_steward_skills.py` (1711 lines) | AI agent skill functions: find_contact, add_note, create_task, etc. | **Active** |
| `crm_briefing_service.py` | Person-centric task briefing with Claude deep links | **RETIRED (not present in repo as of S500) — see `crm_briefing_service_gmail.py`** |
| `crm_briefing_service_gmail.py` (519 lines) | Gmail-delivered HTML briefing (renders the morning email) | **Active — main briefing renderer** |
| `briefing_data_service.py` (410 lines) | Async data assembly: CRM + BQ + allAI + platform health | **Active** |
| `briefing_generator.py` (180 lines) | Markdown rendering for Telegram/text briefings | **Active** |
| `briefing_delivery.py` (430 lines) | Delivery: Telegram + Postmark email + Brief Me HMAC links | **Active** |
| `crm_context_service.py` (252 lines) | Older tokenized briefing context (sync sessions) | **Likely stale — uses missing `CRMBriefing` model** |
| `email_ingest_service.py` (401 lines) | Gmail drop pipeline: extract contacts, upsert, log interactions | **Active** |
| `draft_service.py` (171 lines) | CRUD for standalone `email_drafts` table | **Active** |
| `crm_ai_service.py` (320 lines) | LLM-powered entity enrichment and analysis | **Active** |
| `crm_research_service.py` (689 lines) | Web research for contacts (search + scrape + summarize) | **Active** |
| `outreach_context_service.py` (732 lines) | Builds context for outbound messaging | **Active** |
| `outreach_generation_service.py` | Generates outreach drafts via LLM | **Active** |
| `crm_dedup_service.py` (198 lines) | Interaction and task dedup via description hashing (BQ-096) | **Active** |
| `crm_pipeline_service.py` (401 lines) | Pipeline stage management and transitions | **Active** |
| `crm_referral_service.py` (194 lines) | Referral tracking and commission calculation | **Active** |
| `marketing_task_engine.py` (771 lines) | Marketing task queue: generate, schedule, execute, track | **Active** |

## API layer

> **HISTORICAL NOTE (updated S1099, supersedes S500):** `crm_agent_request.py` was retired at S499, and `app/mcp/crm_remote.py` (the external `/mcp/crm` FastMCP endpoint) was deleted at S1099 under BQ-CRM-MCP-ENDPOINT-REMOVAL-S1098 (Max decision: no direct claude.ai connector to the CRM). The natural-language agent surface is the Koskadeux gateway tool family (`crm_request`, `crm_log_interaction`, `crm_search_interactions` in `koskadeux-mcp/tools/crm.py`), thin wrappers over the backend REST API (`/api/v1/crm/agent-request`, `/api/v1/crm/interactions`, `/api/v1/crm/search`). The old S500 "DO NOT DELETE crm_remote.py" warning is obsolete: the gateway path never used `/mcp/crm`. Historical commits: prior HTTP endpoint `7c51e21`; removal merge `1a514583` (backend).

| File | Routes | Purpose |
|------|--------|---------|
| `api/v1/endpoints/crm.py` (1788 lines) | `/api/v1/crm/*` | Main CRM CRUD, tasks, drafts, briefing, import, admin ops |
| `api/v1/endpoints/crm_pipeline.py` (247 lines) | `/api/v1/crm/pipeline/*` | Pipeline stages and movement |
| `api/v1/endpoints/crm_referrals.py` (112 lines) | `/api/v1/crm/referrals/*` | Referral management |
| `api/v1/endpoints/crm_support.py` | `/api/v1/crm/support/*` | Support workflow endpoints (scope tracked under BQ-CRM-SUPPORT-WORKFLOWS) |
| `api/v1/endpoints/crm_admin.py` | `/api/v1/crm/admin/*` | Admin-internal operations |
| `api/v1/endpoints/accounting_crm.py` | `/api/v1/accounting/crm/*` | Read-only contracts for accounting (`require_accounting_scope`). Shipped S469. |
| `api/v1/endpoints/briefing.py` | `/api/v1/briefing/*` | Briefing view with HMAC auth |
| `api/routers/email_drafts.py` | `/api/v1/drafts/*` | Standalone draft CRUD |
| Koskadeux gateway `tools/crm.py` (mcp.ai.market) | MCP tools over REST | **Primary NL agent surface** — `crm_request` / `crm_log_interaction` / `crm_search_interactions` calling `/api/v1/crm/*`. The former `app/mcp/crm_remote.py` `/mcp/crm` endpoint was removed at S1099. |

## Agent layer

| File | Role |
|------|------|
| `allai/agents/crm_steward.py` | CRM steward agent: processes events, manages Telegram interactions, exposes skills |
| `allai/agents/sysadmin/briefing_monitor.py` | Monitors briefing delivery health |
| Koskadeux gateway `tools/crm.py` | **Primary natural-language CRM surface**. MCP tools on mcp.ai.market wrapping backend REST (`/api/v1/crm/*`) with the internal key; the CRM Steward handles intent server-side. `app/mcp/crm_remote.py` removed at S1099 (BQ-CRM-MCP-ENDPOINT-REMOVAL-S1098). |

### Steward skill exposure & the HITL gate (S1173, T-2026-000217 / T-2026-000219)

- A steward skill is only reachable via `crm_request` if it has an `@skill` wrapper on `CRMStewardAgent` in `app/allai/agents/crm_steward.py`. The handlers in `app/services/crm_steward_skills.py` are NOT auto-exposed — if the agent replies "that skill does not exist in my skill set" but the handler exists, check the wrapper wiring first (that was T-2026-000219).
- `delete_entity` and `delete_task` are wired with `requires_authorization=True`. The `AgentRequestFactory` HITL gate (`app/allai/agent_request_factory.py`, "HITL gate" section) hard-blocks any skill whose `_skill_meta.requires_authorization` is true: it persists a pending row in `agent_hitl_request` and returns `status=pending_hitl` without executing. Approval via `POST /api/v1/agents/ops/hitl-queue/{id}/approve` (superuser) executes the stored call; deny discards it. Regression guard: `tests/test_crm_steward_delete_skill_exposure_t219.py` (also asserts no other steward skill silently gains the gate).
- Post-cutover dedup (T-2026-000217): `CRMEntityService.find_existing_person/organization/person_by_name` run ONLY the party-native queries; the legacy `crm_people`/`crm_organizations` SELECTs are gated behind `legacy_fallback_enabled()` (hard-False since the S1113 table drop). Steward responses key `contact_id`/`entity.id`/audit on `party_id` via `_party_id_str()`. Symptom of regression: upsert returns empty `contact_id` + output-validation failure + no row in `party_person` (an `UndefinedTable` rollback upstream).

## Known issues (S500 audit — supersedes S364)

### Bugs fixed S364
- CC contacts not getting interactions logged → fixed `aee7796`
- `last_interaction_at` never updating → fixed `aee7796`
- `email_drafts` missing columns → migration `2f0b9b1`
- Tasks accept past `due_date` without validation → fix in progress

### Architecture issues (from MP audit)
1. **Two architectures running in parallel** — V1 `crm_entities` vs V2 `domains/crm/party`. Same concepts exist in too many places.
2. **6 briefing files** — should consolidate to 2-3 under `domains/crm/briefing/`
3. **Two draft models** — `email_drafts` (standalone) and `crm_email_drafts` (CRM-tied). Should be one.
4. **Task lifecycle** — `completed_at`, `cancelled_at`, `snoozed_until`, `closed_reason` columns added S364 (`75277a4`). Snooze/cancel methods + MCP tools added. Still missing: `in_progress`, `waiting` states.
5. **`crm_context_service.py`** — DELETED S364 (`705a97e`). Was stale/broken.
6. **`completed_at`** — FIXED S364. Column added (`75277a4`), ghost writes commented out (`2a903fd`).
7. **`api/v1/endpoints/crm.py`** is 1788 lines — too large, should split by resource. (Carry-forward to S365.)

### S500 findings (new)

1. **User-scoping data wipeout** (S499): `created_by_user_id` was null on 550+ rows across `crm_people` (369), `crm_organizations` (26), `crm_tasks` (54), `crm_interactions` (101). Track 1 restored data atomically on 2026-04-24; Track 2 systemic fix (migration + CI lint + service fallback + regression tests + metric + alarm) pending under **BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK**.
2. **Steward NL dispatch + command layer incomplete** (blocks Max's goal of using CRM via Claude + MP Mac clients for full read/write): `_dispatch_by_intent` not wired to `CRMAIService` (D10); `_cmd_task` / `_cmd_drafts` / `_cmd_draft` / `_cmd_reject` stubbed (D11); `_handle_draft_email_step` + `_handle_confirm_draft_step` unimplemented (D12).
3. **Alembic chain bug**: `20260424_001_add_allai_event_ledger_dedupe_key.py` attached to wrong branch; breaks `test_crm_support_api.py` setup (OPUS_CRM Issue 1; D08).
4. **CRM voice memo surface being removed** (S500 narrowing of S499 decision): `CRMVoiceMemoService` class + CRM voice-memo endpoint + models + schemas + tests + frontend references scheduled for removal under BQ-CRM-USER-SCOPING C02. **PRESERVED**: `voice_transcription_service.py` + `telegram_relay.py:185` + `webhooks.py:1816` (Telegram voice ingest path). See BQ body.c02_narrowing_s500 for validation trail (CC Gate 1 Q3; MP R1 task 80089f05).
5. **`crm_agent_request.py` retired**: NL agent surface moved to MCP `crm_remote.py`. Historical "DO NOT DELETE" warning redirected to the MCP path.
6. **Briefing split-brain may persist**: `crm_briefing_service_gmail.py` is the scheduled renderer at 07:00 UTC (`scheduler.py:214` + `:805`). `briefing_data_service.py` audit (C04) will confirm whether it is vestigial or an active dashboard data source.
7. **Empty pipeline stages despite seed** (C03): audit of `crm_pipeline_stages` + `crm_contact_pipeline` pending — tables appear empty despite `20260130_018` seed migration.
8. **Empty MCP server directory** at `/Users/max/koskadeux-mcp/crm-mcp-server` (C01): remove directory, update `INFRASTRUCTURE.md:136`.
9. **Test-brittle hardcoded date** in `tests/test_crm_agent_request_endpoint.py` (OPUS_CRM Issue 2; D09).

### Recommended consolidation (target state)
```
domains/crm/
  core/       — identity, contacts, relationships, audit
  operations/ — interactions, tasks, task lifecycle
  commercial/ — pipeline, referrals, opportunities
  revenue/    — commission engine
  trust/      — scoring, infractions
  briefing/   — daily/weekly briefing (data + render + delivery)
  ai/         — research, outreach context, draft generation
```

## Email drop pipeline

See `gmail-drop-pipeline.md` for the full flow. Key interaction with CRM:
- New emails to `drop@ai.market` → `EmailIngestService` → upserts contacts → logs interactions for ALL recipients (primary + CC) → auto-creates 7-day follow-up task for new contacts.

## Morning briefing flow

1. **Scheduler** (07:00 UTC) → `BriefingDeliveryService.deliver()`
2. **Data assembly** → `gather_briefing_data()` — parallel fetches: CRM tasks/pipeline, BQ status, allAI decisions, platform health
3. **Rendering** → `generate_daily_briefing()` for markdown, `CRMBriefingServiceGmail._build_html_email()` for HTML
4. **Delivery** → Telegram (markdown) + Gmail (HTML with person-centric cards, overdue badges, Claude deep links)

The "456d overdue" display uses `(now - worst_due_date).days` for the oldest overdue task per contact. The date bug was caused by LLM-created tasks with invalid past dates, now guarded by validation.

## Key code paths

### Creating a contact
`CRMEntityService.create_person()` in `crm_service.py`:
1. Check for existing person by email (case-insensitive)
2. If found, merge data (update empty fields only)
3. If new, create `CRMPerson` record
4. Auto-create 7-day follow-up task (`_create_new_contact_follow_up()`) — S364

### Logging an interaction
`CRMInteractionService.log_interaction()` in `crm_service.py`:
1. Dedup check via `description_hash` (BQ-096) — 24h window
2. If duplicate, return existing
3. If new, create `CRMInteraction`, compute hash
4. Update `CRMEntity.last_interaction_at` — S364 fix

### Task lifecycle
`CRMTaskService` in `crm_service.py`:
- `create_task()` — dedup check, create with hash
- `get_pending_tasks()` — returns `status IN (pending, approved)`
- `get_overdue_tasks()` — returns pending tasks where `due_date < now`
- **Lifecycle methods (S364):**
- `complete_task(task_id, reason)` → sets `completed_at` + `closed_reason`
- `cancel_task(task_id, reason)` → sets `cancelled_at` + `closed_reason`
- `snooze_task(task_id, until)` → sets `snoozed_until` (hidden from briefing)
- `get_pending_tasks()` and `get_overdue_tasks()` exclude snoozed tasks
- MCP tools: `snooze_task`, `cancel_task` available via Koskadeux

## Configuration

| Item | Location |
|------|----------|
| Briefing schedule | `app/core/scheduler.py` — 07:00 UTC daily |
| Gmail OAuth | `gmail_tokens` table + GCP `aimarket-prod` |
| Postmark email | `POSTMARK_API_KEY` in Infisical |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID` in Infisical |
| Pipeline stages | Seeded via `app/seeds/crm_playbooks.py` |

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Tasks showing absurd overdue days | LLM created task with past date | Fixed S364 (`2a903fd`): 24h-past guard in schemas, steward skills, and admin API |
| Contact not in CRM after email | Email pipeline didn't auto-create | Check Railway logs for `EmailIngestService` errors |
| Briefing not arriving | Gmail OAuth expired or scheduler down | See `morning-briefing.md` runbook |
| CC contacts missing interactions | Regression in `process_email()` step 4 | Verify CC fan-out loop in `email_ingest_service.py` |
| `last_interaction_at` always null | Regression in `log_interaction()` | Check entity update after commit in `crm_service.py` |
| Stale tasks piling up | No auto-close/lifecycle management | Manual cleanup; lifecycle feature pending |

## Built / Updated

- S222 — Gmail drop pipeline built
- S341 — Pipeline recovery, OAuth token expiry documented
- S364 — 4 bug fixes (CC interactions, last_interaction_at, email_drafts columns, due_date validation `2a903fd`, task lifecycle `75277a4`), auto follow-up, full architecture audit by MP, consolidation `705a97e` (deleted 3 dead files, merged briefing_generator, retired deprecated router then restored — see below), this runbook created
- S458 — allAI-first CRM agent surface shipped: honest-envelope dispatch (`f743704`), tool-use protocol prompt + tool_choice injection (`382dbc2` / `94c23b8` / `db6c386`), skill registration lazy-fill (`0479940`). `crm_request` MCP tool verified end-to-end in production (live traces in `crm-target-state.md` §2.12).
- S469 — R5 runbook refresh + **BQ-CRM-INTEGRATION-CONTRACTS** Gate 4 close (`1d27532`); `/api/v1/accounting/crm/*` read contracts shipped; seller-side Stripe Connect identity consolidated on `party_identity(provider='stripe_connect')`.
- S481 — **BQ-CRM-SALES-SURFACE** Chunk B2 complete (`8315c11`): public v2 PATCH/DELETE for persons + organizations.
- S499 — Track 1 emergency data restoration (550 rows backfilled across 4 tables); OPUS_CRM code audit (7 issues) committed as `OPUS_CRM_FIX_SCHEDULE.md` at `65f61d3`; **BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK** filed P0; voice-memo removal decision (C02); `crm_agent_request.py` retirement confirmed.
- S500 — R6 runbook refresh: S499 findings integrated; stale file references corrected; steward dispatch/command layer gaps documented (D10/D11/D12); skill count corrected to 28 decorated. Updated: `crm-target-state.md`, `crm-architecture.md`, `crm-pipeline.md` (full rewrite).

## CRM Access And Auth (S1099 — external MCP endpoint removed)

**Current state:** there is NO external CRM MCP endpoint on the backend. `https://api.ai.market/mcp/crm/mcp`, `/health/mcp-crm`, and the root MCP OAuth connector routes (`/.well-known/oauth-*`, `/authorize`, `/token`, `/register`) intentionally return 404. `app/mcp/crm_remote.py`, `app/mcp/auth.py`, and `app/mcp/oauth.py` were deleted under BQ-CRM-MCP-ENDPOINT-REMOVAL-S1098 (Gate-3 unanimous DS+GLM+AG, merged S1099 at backend `1a514583`). Max decision (S1098, ledger event b2d6c05d): all CRM access from Claude goes through the Koskadeux gateway (`mcp.ai.market`); there is deliberately no separate claude.ai connector door and none should be reintroduced.

**How CRM is accessed now:**
- Claude / agents: Koskadeux gateway tools (`crm_request`, `crm_log_interaction`, `crm_search_interactions` in `koskadeux-mcp/tools/crm.py`) → backend REST `/api/v1/crm/*` with the internal key → CRM Steward.
- Backend integrations: REST `/api/v1/crm/*` directly (internal key or JWT per endpoint deps).

**Retired configuration:** `CRM_MCP_TOKEN` and `CRM_MCP_AUTH_ENFORCED` are no longer read by any code. Railway env entries removed at S1099 after prod 404 verification. The Infisical `CRM_MCP_TOKEN` value (project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, env `prod`) is retained for the rollback window, then archived per token policy.

**Rollback** (single revert of the removal merge) constraints:
- Set `CRM_MCP_AUTH_ENFORCED=true` and restore `CRM_MCP_TOKEN` in Railway env BEFORE redeploying rollback code; never redeploy the endpoint authless.
- If the follow-up migration dropping `mcp_auth_codes` + `mcp_refresh_tokens` has already run, restoring `app/mcp/oauth.py` will DB-error on the root OAuth routes: either skip restoring `app/mcp/oauth.py` (static-bearer endpoint only) or restore the two tables from migration downgrade / DB backup first. Do not touch `oauth_clients` in either direction.
