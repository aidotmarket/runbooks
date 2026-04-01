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
| `crm_briefing_service.py` (590 lines) | Person-centric task briefing with Claude deep links | **Active** |
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

| File | Routes | Purpose |
|------|--------|---------|
| `api/v1/endpoints/crm.py` (1788 lines) | `/api/v1/crm/*` | Main CRM CRUD, tasks, drafts, briefing, import, admin ops |
| `api/v1/endpoints/crm_pipeline.py` (247 lines) | `/api/v1/crm/pipeline/*` | Pipeline stages and movement |
| `api/v1/endpoints/crm_referrals.py` (112 lines) | `/api/v1/crm/referrals/*` | Referral management |
| `api/v1/endpoints/crm_agent_request.py` (344 lines) | `/api/v1/crm/agent-request` | **Deprecated** NL agent endpoint |
| `api/v1/endpoints/briefing.py` | `/api/v1/briefing/*` | Briefing view with HMAC auth |
| `api/routers/email_drafts.py` | `/api/v1/drafts/*` | Standalone draft CRUD |

## Agent layer

| File | Role |
|------|------|
| `allai/agents/crm_steward.py` | CRM steward agent: processes events, manages Telegram interactions, exposes skills |
| `allai/agents/sysadmin/briefing_monitor.py` | Monitors briefing delivery health |
| `mcp/crm_remote.py` | MCP tool surface: `list_tasks`, `complete_task`, used by Koskadeux |

## Known issues (S364 audit)

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
5. **`crm_context_service.py`** references `CRMBriefing` model that doesn't exist — likely stale/broken.
6. **`completed_at`** written in API endpoints but column doesn't exist on `CRMTask` model.
7. **`api/v1/endpoints/crm.py`** is 1788 lines — too large, should split by resource.

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
- S364 — 4 bug fixes (CC interactions, last_interaction_at, email_drafts columns, due_date validation `2a903fd`, task lifecycle `75277a4`), auto follow-up, full architecture audit by MP, this runbook created
