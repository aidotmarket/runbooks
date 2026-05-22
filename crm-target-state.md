# CRM Target-State Runbook — System Standard

> **Purpose**: This document is the authoritative specification for the ai.market CRM system. Every feature described here must (a) work as specified, (b) have automated test coverage, (c) be accessible to the CRM steward agent, and (d) expose integration interfaces for Accounting, Support, and Sales systems. If the system diverges from this document, the system is wrong.

> **Status**: R6 — 2026-04-24. R6 refresh (S500): integrated S499 emergency-data findings into a coherent known-bug surface. Changes: (a) Phase 3.5 added to §7 to track BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK; (b) §6 expanded with the user-scoping wipeout, steward dispatch gaps D10/D11/D12, and OPUS_CRM audit issues 1–7; (c) §2.3 and §2.10 mark voice memo ingest as Removed (S499 decision, C02); (d) §3 skill count corrected from 16→28 decorated skills in `crm_steward_skills.py` with public/internal re-audit pending under D07; (e) Appendix B retires `crm_agent_request.py` and redirects the natural-language agent surface to MCP `crm_remote.py`; (f) §7 Phase 4 BQ statuses refreshed (AGENT-COVERAGE → REDIRECT STUB to COMPOSITE-SKILLS per S474; SALES-SURFACE B2 shipped S481 `8315c11`). **S500 amendment (2026-04-24)**: C02 voice memo removal narrowed to CRM surface only; Telegram voice ingest (`voice_transcription_service.py`, `telegram_relay.py:185`, `webhooks.py:1816`) preserved per CC Gate 1 Q3 finding (validated by MP R1 task `80089f05`) — see BQ body.c02_narrowing_s500. Prior R5 (S469, 2026-04-18): marked **BQ-CRM-INTEGRATION-CONTRACTS** DONE after Gate 4 close in S469 (backend commit `1d27532`), updated §4.1 Accounting to shipped `/api/v1/accounting/crm` contracts and canonical Stripe Connect identity guidance, removed stale in-flight references, refreshed §7 to Tier 2 Gate 1 R1 parallel-lane reality, and added capability-horizon references for `BQ-MEET-RECORDS-CRM` and `BQ-CRM-REFERRAL-TRACKING`. BQ-CRM-RUNBOOK-STANDARD.

> Tier status is tracked in Living State entity `config:crm-operational-plan`. This runbook is the stable target-state; Living State is the dynamic status tracker.

---

## 1. System Boundary & Identity Model

### What the CRM Is
The CRM is ai.market's system of record for **people, organizations, relationships, interactions, tasks, pipeline stages, referrals, outreach, and commissions**. It is consumed by:
- **Max** (via morning briefing, ops dashboard, Claude deep links)
- **AI Agents** (CRM steward, briefing monitors, marketing ops)
- **MCP tool surface** (Koskadeux `crm_request` and related tools)
- **External systems** (future: Accounting, Support, Sales automation)

### What the CRM Is Not
The CRM does not manage: marketplace listings, AIM Node sessions, VZ deployment state, or user authentication. Those are separate domains with their own systems of record.

### Canonical Identifiers
| ID | Scope | Purpose |
|---|---|---|
| `entity_id` | V1 CRM | Primary key for persons, organizations in `crm_entities` |
| `party_id` | V2 CRM | Canonical cross-domain identity — target state for all integrations |
| `task_id` | Tasks | Action item tracking, HITL workflow |
| `draft_id` | Drafts | Email draft lifecycle |
| `interaction_id` | Interactions | Communication log entries |
| `referral_id` | Referrals | Referral + commission tracking |
| `opportunity_id` | V2 Commercial | Deal/opportunity tracking |
| `pipeline_stage_id` | Pipeline | Stage positioning |

### V1/V2 Bridge State
The current system runs V1 (crm_entities/crm_persons/crm_organizations) as the active production path. V2 (party/party_identity/party_role_binding) models exist with dual-write columns. **Target state after current BQs**: V1 remains primary for operations; V2 `party_id` becomes the canonical external identifier for integration contracts. Full V1→V2 migration is a future BQ.

---

## 2. CRM Capabilities Matrix

Each capability is described with:
- **Feature**: What it does
- **Status**: Working / Partial / Broken
- **BQ**: Which active BQ modifies it (if any)
- **Agent Skill**: Whether the CRM steward can invoke it (Yes / Partial / No)
- **Test Coverage**: Covered / Gap
- **Integration**: Which external system needs it (A=Accounting, Su=Support, Sa=Sales)

### 2.1 Contact & Organization Management

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create/upsert person | Working | — | Yes (`upsert_contact`) | Covered | Sa |
| Search/list persons | Working | — | Yes (`find_contact`, `search_contacts`) | Covered | Sa, Su |
| Update person fields | Working | DONE (SERVICE-LAYER) | Yes (`update_contact` via service-bus) | Covered | Sa |
| Soft-delete person | Working | DONE (DATA-INTEGRITY) | Yes (`delete_entity` via service-bus) | Covered (`test_crm_soft_delete_and_constraints`) | — |
| Create organization | Working | — | Yes (`create_organization`) | Covered | Sa, A |
| Search/list organizations | Working | — | No | Covered (`test_crm_soft_delete_and_constraints:75`) | Sa |
| Update/delete organization | Working | DONE (SERVICE-LAYER) | Partial (service-bus skills registered, agent coverage tracked in AGENT-COVERAGE) | Covered (`test_crm_service_gate1:425`) | Sa |
| Merge duplicate contacts | Not built | — | No | — | — |

### 2.2 Relationships & Entity Network

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create relationship | Working | DONE (DATA-INTEGRITY) | Yes (`create_relationship`) | Covered | Sa |
| List/query relationships | Working | DONE (DATA-INTEGRITY) | Yes (`get_entity_context` includes relationships) | Covered (`test_crm_service_gate1:514`) | Sa, Su |
| Relationship types (referral, colleague, reports_to) | Working | — | Yes (via `create_relationship`) | Covered | Sa |
| Entity network graph | Working | — | Yes (`get_entity_context`) | Covered (`test_crm_soft_delete_and_constraints:127`) | Sa |

### 2.3 Interactions & Communication Log

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Log interaction (email, call, note, social, whatsapp) | Working | — | Yes (`add_note`, `log_note`) | Covered | Su, Sa |
| Interaction dedup (description_hash, 24h window) | Working | — | No | Covered | — |
| List/search interactions | Working | — | Via `get_entity_context` | Covered | Su |
| Email ingest (drop@ai.market → CRM) | Partial | — | No | Partial (gmail drop tests) | Su, Sa |
| Voice memo ingest | **Removed — CRM surface only (S499/S500); Telegram voice ingest preserved** | BQ-CRM-USER-SCOPING C02 | No | N/A | — |

### 2.4 Task Lifecycle

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create task (with dedup) | Working | — | Yes (`create_task`) | Covered | Su, Sa |
| Complete task | Working | — | Yes (`complete_task`) | Covered | — |
| Snooze task | Working | — | Yes (`snooze_task`) | Covered | — |
| Cancel task | Working | — | No | Covered (`test_crm_service_gate1:713`) | — |
| Move contact forward | Working | — | Yes (`move_contact_forward`) | Covered | — |
| Get pending/overdue tasks | Working | DONE (BRIEFING-FIX) | Yes (`get_daily_briefing`) | Covered | Su |
| Task states: in_progress, waiting | Not built | — | No | — | Su |
| Task-linked email drafts (CRMEmailDraft) | Working | — | Yes (`draft_email`) | Gap | Sa |

### 2.5 Pipeline & Sales Lifecycle

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Pipeline stages (new_lead → closed) | Working | — | No | Gap — no dedicated CRM pipeline test file | Sa, A |
| Move contact through pipeline | Working | — | No | Gap — no dedicated CRM pipeline test file | Sa |
| Bulk pipeline moves | Working | — | No | Gap — no dedicated CRM pipeline test file | Sa |
| Pipeline history/audit | Working | — | No | Gap — no dedicated CRM pipeline test file | A |
| Stage duration analytics | Working | — | No | Gap | Sa |
| Conversion rate analytics | Working | — | No | Gap | Sa |
| Pipeline overview/search | Working | — | No | Gap | Sa |

### 2.6 Referrals & Commissions

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create referral | Working | DONE (DATA-INTEGRITY) | No (tracked in AGENT-COVERAGE) | Partial | A, Sa |
| Referral status tracking | Working | — | No | Partial | A |
| Commission-on-close | Working | — | No | Covered (`test_crm_referral_commission:65`) | A |
| Commission plans/rules/overrides (V2) | Working | — | No | Covered | A |
| Commission accruals (V2) | Working | DONE (INTEGRATION-CONTRACTS) | No | Covered | A |
| Formal referral attribution / commission source tracking | Planned | BQ-CRM-REFERRAL-TRACKING (T4 horizon) | No | Gap | A, Sa |

### 2.7 Outreach & Research

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Outreach context assembly | Partial | — | No | Gap | Sa |
| Outreach draft generation | **Broken** | — | No | Gap | Sa |
| Web research/enrichment | Partial-to-broken | — | No | Gap | Sa |
| CRM AI parse/classify/profile | Partial | — | No | Gap | — |

### 2.8 Briefing & Reporting

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Daily briefing data assembly | Working | DONE (BRIEFING-FIX) | Yes (`get_daily_briefing`) | Partial | — |
| Gmail HTML morning briefing | Working | DONE (BRIEFING-FIX) | No | Gap | — |
| Telegram briefing delivery | Working | — | No | Gap | — |
| Person-centric task cards | Working | — | No | Gap | — |
| Claude deep links | Working | — | No | Gap | — |

### 2.9 Authorization & Data Integrity

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Soft-delete (deleted_at) filtering | Working | DONE (DATA-INTEGRITY) | N/A | Partial | — |
| Auth/RBAC for CRM endpoints | Working | DONE (AUTH-RBAC) | N/A | Covered | All |
| Service layer enforcement | Working | DONE (SERVICE-LAYER) | N/A | Covered | All |
| Audit trail | Partial (pipeline only) | — | No | Gap | A, Su |

### 2.10 Admin, Import & Data Operations

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Contact/org import | Working | — | No | Gap | — |
| Seed pipeline stages | Working | — | No | Gap | — |
| Duplicate cleanup/dedup | Working | — | No | Gap | — |
| Outbound Gmail send | Working | — | No | Gap | Sa |
| Gmail validation/status | Working | — | No | Gap | — |
| Voice memo ingest endpoint | **Removed — CRM surface only (S499/S500); Telegram voice ingest preserved** | BQ-CRM-USER-SCOPING C02 | No | N/A | — |

### 2.11 V2 Domain Layer (Emerging)

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Party identity + external IDs | Working | DONE (INTEGRATION-CONTRACTS) | No | Covered | All |
| Party role bindings | Working | — | No | Covered | All |
| Trust scoring + infractions | Partial | — | No | Covered | Su |
| Opportunities | Working | — | No | Covered | Sa, A |
| TX event dispatcher | Working | — | No | Covered | All |
| V2 operations wrappers | **Broken** | — | No | Partial (`test_crm_v2_operations:89`) | — |

### 2.12 Customer Support / allAI First-Responder (NEW S458)

Per Max's directive: *AI handles all customer interactions unless human risk management is needed.* The allAI first-responder model treats CRM-backed support as a default-AI flow with explicit escalation paths.

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Natural-language CRM request dispatch (`crm_request`) | Working | DONE (AGENT-DISPATCH-FIX, AGENT-LLM-TOOL-USE, ALLAI-SKILL-REGISTRATION) | Yes — full multi-turn tool use verified in prod S458 | Covered (`test_crm_agent_dispatch_malformed.py`, `test_crm_agent_end_to_end_tool_use.py`, `test_base_agent_skill_registration.py`) | Su |
| Dispatch layer honest-envelope contract | Working | DONE (AGENT-DISPATCH-FIX) | — | Covered | All |
| Tool-use protocol prompt + tool_choice injection | Working | DONE (AGENT-LLM-TOOL-USE) | — | Covered | All |
| Skill registration lazy-fill at read boundary | Working | DONE (ALLAI-SKILL-REGISTRATION) | — | Covered | All |
| allAI-first support intake and triage | Planned | SUPPORT-WORKFLOWS (Gate 1 R1 draft) | Planned | Gap | Su |
| Dispute resolution workflow | Planned | SUPPORT-WORKFLOWS (Gate 1 R1 draft; from ENTERPRISE-FEATURES carve-out) | No | Gap | Su |
| SLA tracking on support tasks | Planned | SUPPORT-WORKFLOWS (Gate 1 R1 draft) | No | Gap | Su |
| Ticket ↔ CRM linkage | Planned | SUPPORT-WORKFLOWS (Gate 1 R1 draft) | No | Gap | Su |
| Human escalation signal | Planned | SUPPORT-WORKFLOWS (Gate 1 R1 draft) | Planned | Gap | Su |
| Meet notes ingestion to CRM (Google Drive → Meet Gemini Notes) | Planned | BQ-MEET-RECORDS-CRM (T4 horizon) | No | Gap | Su |

**Design principle**: Every support interaction starts with allAI. Escalation to Max happens only when (a) risk/compliance signal requires human judgment, (b) AI confidence below threshold, or (c) the counterparty explicitly requests human contact. See §4.2 for the integration contract.

**Verification evidence (S458)**: Live read trace `754792b8-efd8-4270-8415-96d916e40fa2` (find_contact), live write trace `dffad565-0cf8-4014-910d-6ed2b1fb7f3a` (create_task via 2-turn tool use, task UUID `d0b11969-28dc-4bf8-aec3-e11340e6ef56`). See Event Ledger entry `885de070-6fa5-4142-a4db-77d6bee11d22`.

---

## 3. CRM Steward — Agent Capability Map

### Current Skills (28 `@skill`-decorated in `crm_steward_skills.py`; public/internal classification pending re-audit under BQ-CRM-USER-SCOPING D07)

**Published public skills** (accessible via MCP/API/Telegram):
- `find_contact` — search contacts by name/email/query
- `upsert_contact` — create or update contact (matches by email then name)
- `add_note` — log interaction/note against entity
- `create_task` — create follow-up task with dedup
- `create_organization` — create/upsert organization by name
- `create_relationship` — link two CRM entities
- `complete_task` — mark task completed
- `snooze_task` — postpone task to future date
- `move_contact_forward` — push open tasks forward N days + reset last-contact
- `get_daily_briefing` — user-scoped daily CRM briefing
- `get_entity_context` — full entity context (interactions, relationships, tasks)

**Additional internal skills** (in manifest but not public):
- `add_prospect` — multi-step contact creation flow
- `draft_email` — email drafting via approval pipeline
- `log_note` — add note to existing contact
- `search_contacts` — search by name/company/email
- `general_chat` — general CRM-aware conversation

**Decorated service-bus skills NOT exposed** (in `crm_steward_skills.py`):
- `update_contact`, `update_person`, `delete_entity`
- Pipeline move/query skills
- Referral management skills
- Research/enrichment skills
- Admin/import skills

### Target State: Full Agent Coverage

After BQ-CRM-AGENT-COVERAGE, the steward MUST be able to:

1. **Contact ops**: Create, read, update, soft-delete persons and organizations. Search by any field. Merge duplicates.
2. **Relationship ops**: Create, read, delete relationships. Query entity network. (Partially done via `create_relationship` + `get_entity_context`)
3. **Interaction ops**: Log any type. Search/filter interactions. Trigger email ingest manually.
4. **Task ops**: Full lifecycle — create, complete, cancel, snooze, reassign. Query pending/overdue/snoozed.
5. **Pipeline ops**: Move contacts through stages. Bulk moves. Query stage analytics.
6. **Referral ops**: Create, track, close referrals. Query commission status.
7. **Outreach ops**: Generate outreach drafts. Assemble context. Trigger research enrichment.
8. **Briefing ops**: Trigger on-demand briefing. Query briefing data.
9. **Admin ops**: Import contacts. Seed pipeline stages. Run data integrity checks.

### Skill Gap Closure Plan
Each gap maps to BQ-CRM-AGENT-COVERAGE (expanded from COMPOSITE-SKILLS). Depends on SERVICE-LAYER landing first (single write path). Test suite must include agent-level integration tests: steward skill → service → database → verified outcome.

---

## 4. Integration Contracts

### 4.1 Accounting Interface

**What Accounting needs from CRM**:
- Commission accruals and settlement events (via V2 `commission_accrual`)
- Referral close events with commission amounts
- Pipeline stage-change events (for revenue recognition timing)
- Party identity resolution (`party_id` ↔ Stripe customer/connect account)

**Current state (R5 / shipped in `ai-market-backend@main` as of `1d27532`)**:
- Read-only contract surface is live at `app/api/v1/endpoints/accounting_crm.py` under `/api/v1/accounting/crm`, protected by `require_accounting_scope("accounting:read")`.
- Shipped endpoints: `GET /commission-accruals/{transaction_id}`, `GET /commission-accruals`, `GET /referrals/{referral_id}`, `GET /referrals`, `GET /party-stripe-mappings/{party_id}`, `GET /party-stripe-mappings/by-customer/{stripe_customer_id}`, and `GET /party-stripe-mappings/by-connect-account/{stripe_connect_account_id}`.
- Shipped schemas live in `app/schemas/accounting_crm.py`: `CommissionAccrualRead` / `CommissionAccrualList`, `ReferralCommissionRead` / `ReferralCommissionList`, and `PartyStripeMappingRead`.
- Seller-side Stripe Connect is now canonically read from `party_identity(provider='stripe_connect')`. Legacy `users.stripe_account_id` and `seller_profiles.stripe_connect_id` remain dual-written by existing writers, but new code must not add fresh reads from those columns; readers go through `app/services/crm/stripe_connect_identity_reader.py`.
- M7 inter-chunk gate validated the consolidation on real sandbox Stripe Connect onboarding in S468: DB evidence on `acct_1TNbCtRoppdDnnXZ` showed `party_identity` byte-exact with `users.stripe_account_id`, with idempotency confirmed.
- Canonical implementation spec: `specs/BQ-CRM-INTEGRATION-CONTRACTS-GATE2.md` at backend commit `8c298dc`.
- Explicitly out of scope: `billing_entities` and other merchant-of-record semantics remain separate; do not treat them as present in this CRM contract.

**Contract**: Shipped read-only REST endpoints for CRM/accounting queries now exist. Event-driven TX wiring still exists where noted below, but canonical transaction → CRM dispatch is not yet the external contract surface.

| Event/Endpoint | Exists | Stable API | Priority |
|---|---|---|---|
| Commission accrual created/settled | Yes (V2 TX + shipped read endpoints) | Yes — `/api/v1/accounting/crm/commission-accruals*` | P1 |
| Referral closed with commission | Yes (service + shipped read endpoints) | Yes — `/api/v1/accounting/crm/referrals*` | P1 |
| Pipeline stage changed | Yes (service) | No — no event hook | P2 |
| Party ↔ Stripe mapping | Yes (`party_identity`) | Yes — `/api/v1/accounting/crm/party-stripe-mappings*` | P1 |
| Revenue summary by period | No | No | P2 |
| Formal referral attribution / payout workflow | Planned | No | T4 horizon — `BQ-CRM-REFERRAL-TRACKING` |

### 4.2 Support Interface (allAI-first design, S458 R4)

**Design principle** (per §2.12): Every support interaction is handled by allAI first. Human escalation only when risk/compliance requires judgment, AI confidence is below threshold, or the counterparty explicitly requests human contact.

**What Support needs from CRM**:
- Natural-language task dispatch via `crm_request` (verified S458) — the primary entry point
- Contact/org lookup by any identifier (for lookups AI needs to perform)
- Interaction history for a contact (for AI context assembly)
- Trust score and infraction history (for risk-weighting AI decisions)
- Task creation for support follow-ups
- Dispute → infraction pipeline (with HITL approval)
- Human escalation signal + audit trail (when AI escalates, we record why)

**Contract**: Agent-first — `crm_request` is the default support surface. REST endpoints remain available for internal/admin and as the underlying service layer the agent calls.

| Event/Endpoint | Exists | Stable API | Priority | Notes |
|---|---|---|---|---|
| `crm_request` natural-language dispatch | Yes (S458) | Yes (MCP + REST) | — | Primary support surface; handles ~90% of support flows |
| Contact lookup (email, name) | Yes | Yes (REST) | — | Agent skill `find_contact` |
| Contact lookup by party_id | Yes | No — service helper only | P1 | Target: expose via REST and agent skill |
| Interaction history | Yes | Yes (REST) | — | Agent skill `get_entity_context` |
| Trust score snapshot | Yes (V2) | No | P1 | Target: expose via REST + agent skill `get_trust_score` |
| Infraction log | Yes (V2) | No | P1 | Target: expose via REST + agent skill `list_infractions` |
| Create support task | Yes | Yes (REST) | — | Agent skill `create_task` |
| Dispute resolution workflow | No | No | P1 | BQ-CRM-SUPPORT-WORKFLOWS (promoted P2→P1 per S458 direction) |
| SLA tracking on support tasks | No | No | P1 | BQ-CRM-SUPPORT-WORKFLOWS |
| Ticket ↔ CRM linkage | No | No | P1 | BQ-CRM-SUPPORT-WORKFLOWS |
| Human escalation signal | No | No | P1 | BQ-CRM-SUPPORT-WORKFLOWS — emit `agent_escalation_requested` event with reason + confidence + trace_id |

**Agent-first acceptance criteria**: For every row above where `Stable API = Yes`, the CRM steward must be able to invoke it via `crm_request`. For rows marked P1, BQ-CRM-SUPPORT-WORKFLOWS must either ship the REST+agent skill or declare a carved-out follow-on BQ.

### 4.3 Sales Interface

**What Sales needs from CRM**:
- Full contact/org/relationship graph
- Pipeline management (move, bulk move, analytics)
- Outreach generation and context
- Referral tracking
- Research enrichment
- Briefing data

**Contract**: REST endpoints + agent skills for automated sales workflows.

| Event/Endpoint | Exists | Stable API | Priority |
|---|---|---|---|
| Contact/org create/list/search/get | Yes | Yes (REST) | — |
| Contact/org update/delete | Yes | No — admin-internal only (`crm.py:744`) | P1 |
| Pipeline CRUD + analytics | Yes | Yes (REST, full suite) | — |
| Outreach generation | Broken | No | P1 |
| Research enrichment | Broken | No | P2 |
| Referral CRUD | Yes | Yes (REST) | — |
| Relationship graph query | Yes | Yes (via entity context) | — |

---

## 5. Test Standard & Acceptance Matrix

### Principle
Every row in the Capabilities Matrix (Section 2) must have at least one automated test that validates the feature works end-to-end. The test name must reference the capability ID (e.g., `test_2_1_create_person`, `test_2_5_pipeline_move`).

### Current Coverage
- **439+ CRM-related tests** across the repo (including pipeline, referral, steward, service, MCP, soft-delete, FTS, briefing)
- **Well covered**: Core CRUD, steward skills, V2 identity/trust/revenue, referral basics + commission, auth guardrails, briefing skill, soft-delete constraints, org operations, entity network, cancel task
- **Gaps**: CRM pipeline service/endpoints (no dedicated test file), outreach generation/context, research service, briefing delivery/data assembly, draft service, admin/import/dedup, outbound Gmail, voice memo, V2 operations against real DB with non-null entity_id, steward→V2 integration, agent-level integration tests
- **Quarantined**: `test_crm_auth.py`, `test_crm_steward_retrofit.py` (skill-count drift), `test_gmail_drafts.py` (skipped)

### Test Tiers
1. **Unit tests**: Each service method, each model validation rule
2. **Integration tests**: Service → database round-trip, soft-delete filtering, dedup behavior
3. **Agent tests**: Steward skill → service → database → verified outcome
4. **Contract tests**: Each integration endpoint returns expected schema
5. **Regression tests**: Every bug fixed by DATA-INTEGRITY, BRIEFING-FIX, SERVICE-LAYER, AUTH-RBAC

### Gap Closure Plan
BQ-CRM-TESTING-V2 (reopen of CRM-TESTING) generates tests for every "Gap" cell in Section 2. Starts immediately; closes only after SERVICE-LAYER and broken-service fixes land. Target: 80% coverage floor with explicit per-feature acceptance.

---

## 6. Known Broken/Partial Items Requiring Immediate Fix

1. **Outreach generation broken**: `outreach_generation_service.py:37` maps to `CRMTaskType.FOLLOW_UP_EMAIL` which doesn't exist as an enum → **BQ-CRM-FIX-OUTREACH**
2. **V2 operations not production-safe**: `domains/crm/operations/service.py:33` doesn't set `entity_id` despite non-null constraint on `CRMInteraction.entity_id` and `CRMTask.entity_id` → **BQ-CRM-FIX-V2-OPS**
3. **Research backfill broken**: `crm_research_service.py:645` writes `last_researched_at` to `CRMPerson` but field is on `CRMOrganization` → **BQ-CRM-FIX-RESEARCH**
4. **Steward skill fragmentation**: 28 `@skill`-decorated methods in `crm_steward_skills.py`, 11 published public — public/internal classification pending re-audit under D07 → **BQ-CRM-AGENT-COVERAGE** (formerly BQ-CRM-COMPOSITE-SKILLS, absorbed BQ-CRM-PATCH-PARITY per S456 audit; skill count corrected from 16→28 per S500 R6 refresh + S691 §6 row sync)
5. **Briefing split-brain**: Gmail-based sender (`crm_briefing_service_gmail.py`) vs Postmark delivery (`briefing_delivery.py:185`) running in parallel → **BQ-CRM-BRIEFING-FIX slice 1**
6. **SERVICE-LAYER Gate 1 defers endpoint bypasses**: Some API endpoints bypass service layer; not true single-write-path until Gate 2 lands (`BQ-CRM-SERVICE-LAYER-GATE1.md:61`)
7. **User-scoping data wipeout** (FIXED S499 Track 1 data restoration; SYSTEMIC FIX PENDING): user-scoped briefing queries returned empty because `created_by_user_id` was null on 550+ rows — 369 `crm_people`, 26 `crm_organizations`, 54 `crm_tasks` (including 7 placeholder UUIDs rewritten), 101 `crm_interactions`. Track 1 restored all rows on production via atomic SQL on 2026-04-24. Track 2 (D01–D12) wires an Alembic migration to replace the SQL (idempotent, reversible, self-healing on backup-restored DBs), adds CI lint on scoping columns, adds defensive service fallbacks on empty-scoped-query + zero-owned, adds regression tests, adds `crm_briefing_contact_count` metric + alarm, closes steward ownership-scoping TODOs at `crm_steward_skills.py:533,668`, and audits other scoping columns since Jan. Track 3 (C01–C07) cleans up the empty `crm-mcp-server` dir, removes `CRMVoiceMemoService` entirely, audits `crm_pipeline_stages` empty-despite-seed, audits `briefing_data_service.py` + `/api/v1/briefing` for vestigial-vs-active, adds a placeholder-UUID regression test, confirms deprecated endpoints removed. Tracked in **BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK**.
8. **Steward natural-language dispatch + command layer incomplete** (blocks Max's goal of using CRM via Claude + MP Mac clients for full read/write): `_dispatch_by_intent` in `app/allai/agents/crm_steward.py` does not invoke `CRMAIService` for free-text intent routing (OPUS_CRM Issue 4 / D10); `_cmd_task`, `_cmd_drafts`, `_cmd_draft`, `_cmd_reject` are stubs without real service calls (Issue 5 / D11); `_handle_draft_email_step` + `_handle_confirm_draft_step` are not implemented (Issue 6 / D12).
9. **Alembic migration ordering for `allai_event_ledger.dedupe_key`**: `alembic/versions/20260424_001_add_allai_event_ledger_dedupe_key.py` has `down_revision = s155_crm_sales_surface_outbox`, but the table is created on a different branch — `tests/test_crm_support_api.py` setup errors with "relation allai_event_ledger does not exist" (OPUS_CRM Issue 1 / D08).
10. **Test-brittle hardcoded date** in `tests/test_crm_agent_request_endpoint.py` fails on any day after the hardcoded `2026-04-22T09:00:00Z` (OPUS_CRM Issue 2 / D09).

---

## 7. Migration & Consolidation Plan

### Target Architecture
```
domains/crm/
  core/         — identity (party), contacts, organizations, relationships, audit
  operations/   — interactions, tasks, task lifecycle, voice memos
  commercial/   — pipeline, referrals, opportunities, outreach
  revenue/      — commission engine (plans, rules, overrides, accruals)
  trust/        — scoring, infractions, dispute resolution
  briefing/     — daily/weekly briefing (data assembly + render + delivery)
  ai/           — research, enrichment, draft generation, AI classification
  integration/  — Accounting, Support, Sales contracts and event hooks
```

### Phase Plan (R5 refresh — S469)

**Phase 0 — Unblock the Agent (COMPLETE S457–S458)**:
- ✅ BQ-CRM-AGENT-DISPATCH-FIX (S457, commit f743704) — honest envelope
- ✅ BQ-CRM-AGENT-LLM-TOOL-USE (S458, commits 382dbc2 + 94c23b8 + db6c386) — tool-use protocol prompt + tool_choice injection
- ✅ BQ-ALLAI-SKILL-REGISTRATION (S458, commit 0479940) — lazy-fill at read boundary
- Net result: `crm_request` fully functional end-to-end; memory edit #15 lifted

**Phase 1 — Core CRM hygiene (COMPLETE through R4)**:
- ✅ DATA-INTEGRITY (multiple slices)
- ✅ AUTH-RBAC
- ✅ SERVICE-LAYER
- ✅ BRIEFING-FIX (both slices)
- ✅ This runbook R4 refresh

**Phase 2 — Stable integration contract (COMPLETE S469)**:
1. ✅ **BQ-CRM-INTEGRATION-CONTRACTS** — Gate 4 closed in S469 after backend landing through commit `1d27532`
2. Net result: Accounting-facing CRM read contracts are live under `/api/v1/accounting/crm/*`; seller-side Stripe Connect reads consolidate on `party_identity(provider='stripe_connect')`

**Phase 3 — Fix broken services (still in progress)**:
1. **3 micro-BQs for broken services** (parallel): BQ-CRM-FIX-OUTREACH, BQ-CRM-FIX-V2-OPS, BQ-CRM-FIX-RESEARCH

**Phase 3.5 — CRM user-scoping systemic fix (ACTIVE S500)**:
1. **BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK** (P0). Gate 0 planned. Track 1 (emergency data restoration) complete S499 — 550 rows backfilled via atomic SQL on Railway Postgres (data-only, not in repo by design). Track 2 (D01–D12 systemic: Alembic migration replacing the SQL, CI lint, service fallback, regression tests, alarm, steward dispatch/command layer, ownership-scoping audit across `crm_interactions`/`crm_playbooks`/`crm_learned_preferences`/`crm_audit_log`, Alembic/test-brittleness fixes) + Track 3 (C01–C07 cleanup: empty MCP dir, voice memo removal, pipeline seed audit, briefing dashboard audit, placeholder-UUID regression, deprecated endpoints confirmation) pending. Blocks full unlock of Max's goal to use CRM via Claude + MP Mac clients.

**Phase 4 — Tier 2 parallel lane (next per `config:crm-operational-plan`)**:
1. **BQ-CRM-AGENT-COVERAGE** — REDIRECT STUB → **BQ-CRM-COMPOSITE-SKILLS** (canonical per S474 consolidation). Composite skills Chunk A + Chunk B2 COMPLETE (4 composite steward skills + 2 MCP write tools + alias canonicalization); Chunk C decided NOT_APPLICABLE; Chunk D PII hardening carved to separate **BQ-CRM-COMPOSITE-SKILLS-PII-HARDENING** (P2).
2. **BQ-CRM-SALES-SURFACE** — Gate 2 Chunk B2 FULLY COMPLETE at backend commit `8315c11` (S481). Public v2 PATCH/DELETE surface for persons + organizations shipped with regression coverage.
3. **BQ-CRM-SUPPORT-WORKFLOWS** — status tracked in Living State; details live on the entity until review closes.
4. These BQs remain part of the Tier 2 lane. Scope stays in each BQ's Gate 1/2 specs until review closes.

**Phase 5 — Testing and polish (future)**:
1. **BQ-CRM-TESTING** (P0, reopened) — begins after Tier 2 completes
2. **BQ-CRM-ENTERPRISE-FEATURES** (P2, scope reduced after SUPPORT-WORKFLOWS carve-out) — custom fields, workflows, lead scoring
3. **V1→V2 migration** → party_id becomes sole identifier

**Cross-cutting (any phase)**:
- BQ-ALEMBIC-BASELINE-REWRITE (P2, not on CRM critical path)
- BQ-ALEMBIC-FILENAME-CONVENTION (P2)

---

## Appendix A: Service File Map

| File | Lines | Domain | Status |
|---|---|---|---|
| `crm_service.py` | 794 | Core CRUD | Active — primary |
| `crm_steward_skills.py` | 1711 | Agent skills | Active — fragmented |
| `crm_briefing_service_gmail.py` | 519 | Briefing render | Active |
| `briefing_data_service.py` | 410 | Briefing data | Active |
| `briefing_delivery.py` | 430 | Briefing delivery | Active |
| `outreach_context_service.py` | 732 | Outreach context | Active |
| `outreach_generation_service.py` | ~500 | Outreach drafts | **Broken** |
| `crm_research_service.py` | 689 | Research | **Partial** |
| `crm_ai_service.py` | 320 | AI enrichment | Partial |
| `crm_pipeline_service.py` | 401 | Pipeline | Active |
| `crm_referral_service.py` | 194 | Referrals | Active |
| `crm_dedup_service.py` | 198 | Dedup | Active |
| `email_ingest_service.py` | 401 | Email drop | Active |
| `draft_service.py` | 171 | Standalone drafts | Active |
| `marketing_task_engine.py` | 771 | Marketing queue | Active |

## Appendix B: API Endpoint Map

| File | Routes | Domain |
|---|---|---|
| `crm.py` (1788 lines) | `/api/v1/crm/*` | Core CRUD, tasks, drafts, briefing, import, admin, Gmail, voice memo, dedup |
| `crm_pipeline.py` (247 lines) | `/api/v1/crm/pipeline/*` | Pipeline stages, moves, bulk moves, history, analytics |
| `crm_referrals.py` (112 lines) | `/api/v1/crm/referrals/*` | Referral management |
| `crm_remote.py` (~23 kB, `app/mcp/crm_remote.py`) | MCP server mounted at `/mcp/crm` | **Primary natural-language agent surface** — `crm_request` tool family for Claude.ai Connectors + Koskadeux. Replaces retired `crm_agent_request.py` (historical reference `7c51e21`). |
| `briefing.py` | `/api/v1/briefing/*` | Briefing view with HMAC auth |
| `email_drafts.py` | `/api/v1/drafts/*` | Standalone draft CRUD |

## Appendix C: Test File Map

| File | Domain | Tests |
|---|---|---|
| `test_crm_service_gate1.py` | Core service (create, update, cancel, relationships) | ~50+ |
| `test_crm_skills_gate1.py` | Steward skills | ~40+ |
| `test_crm_soft_delete_and_constraints.py` | Soft-delete, org list, network | ~30+ |
| `test_crm_steward_skills.py` | Steward skill coverage | ~30+ |
| `test_crm_steward_e2e.py` | End-to-end steward flows | ~20+ |
| `test_crm_mcp_gate1.py` | MCP tool surface | ~20+ |
| `test_crm_fts.py` | Full-text search + pipeline | ~25+ |
| `test_crm_referral.py` | Referral basics | ~15+ |
| `test_crm_referral_commission.py` | Commission-on-close | ~10+ |
| _(no dedicated CRM pipeline test file)_ | Pipeline API endpoints | **Gap** |
| `test_crm_audit_phase3_build_c.py` | Audit/phase3 | ~15+ |
| `test_crm_auth.py` | Auth guardrails | Quarantined |
| `test_crm_steward_retrofit.py` | Skill-count regression | Quarantined |
| `test_gmail_drafts.py` | Gmail draft flow | Skipped |
