# CRM Target-State Runbook — System Standard

> **Purpose**: This document is the authoritative specification for the ai.market CRM system. Every feature described here must (a) work as specified, (b) have automated test coverage, (c) be accessible to the CRM steward agent, and (d) expose integration interfaces for Accounting, Support, and Sales systems. If the system diverges from this document, the system is wrong.

> **Status**: DRAFT R3 — S447. R3: Fixed pipeline test coverage claims per MP R2 review. BQ-CRM-RUNBOOK-STANDARD.

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
| Update person fields | Partial | SERVICE-LAYER | Partial (service-bus) | Covered | Sa |
| Soft-delete person | Partial | DATA-INTEGRITY | Partial (service-bus) | Covered (`test_crm_soft_delete_and_constraints`) | — |
| Create organization | Working | — | Yes (`create_organization`) | Covered | Sa, A |
| Search/list organizations | Working | — | No | Covered (`test_crm_soft_delete_and_constraints:75`) | Sa |
| Update/delete organization | Partial | SERVICE-LAYER | No | Covered (`test_crm_service_gate1:425`) | Sa |
| Merge duplicate contacts | Not built | — | No | — | — |

### 2.2 Relationships & Entity Network

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create relationship | Working | DATA-INTEGRITY | Yes (`create_relationship`) | Covered | Sa |
| List/query relationships | Working | DATA-INTEGRITY | Yes (`get_entity_context` includes relationships) | Covered (`test_crm_service_gate1:514`) | Sa, Su |
| Relationship types (referral, colleague, reports_to) | Working | — | Yes (via `create_relationship`) | Covered | Sa |
| Entity network graph | Working | — | Yes (`get_entity_context`) | Covered (`test_crm_soft_delete_and_constraints:127`) | Sa |

### 2.3 Interactions & Communication Log

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Log interaction (email, call, note, social, whatsapp) | Working | — | Yes (`add_note`, `log_note`) | Covered | Su, Sa |
| Interaction dedup (description_hash, 24h window) | Working | — | No | Covered | — |
| List/search interactions | Working | — | Via `get_entity_context` | Covered | Su |
| Email ingest (drop@ai.market → CRM) | Partial | — | No | Partial (gmail drop tests) | Su, Sa |
| Voice memo ingest | Partial | — | No | Gap | — |

### 2.4 Task Lifecycle

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create task (with dedup) | Working | — | Yes (`create_task`) | Covered | Su, Sa |
| Complete task | Working | — | Yes (`complete_task`) | Covered | — |
| Snooze task | Working | — | Yes (`snooze_task`) | Covered | — |
| Cancel task | Working | — | No | Covered (`test_crm_service_gate1:713`) | — |
| Move contact forward | Working | — | Yes (`move_contact_forward`) | Covered | — |
| Get pending/overdue tasks | Working | BRIEFING-FIX | Yes (`get_daily_briefing`) | Covered | Su |
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
| Create referral | Working | DATA-INTEGRITY | No | Partial | A, Sa |
| Referral status tracking | Working | — | No | Partial | A |
| Commission-on-close | Working | — | No | Covered (`test_crm_referral_commission:65`) | A |
| Commission plans/rules/overrides (V2) | Working | — | No | Covered | A |
| Commission accruals (V2) | Working | — | No | Covered | A |

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
| Daily briefing data assembly | Working | BRIEFING-FIX | Yes (`get_daily_briefing`) | Partial | — |
| Gmail HTML morning briefing | Partial | BRIEFING-FIX | No | Gap | — |
| Telegram briefing delivery | Working | — | No | Gap | — |
| Person-centric task cards | Working | — | No | Gap | — |
| Claude deep links | Working | — | No | Gap | — |

### 2.9 Authorization & Data Integrity

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Soft-delete (deleted_at) filtering | Partial | DATA-INTEGRITY | N/A | Partial | — |
| Auth/RBAC for CRM endpoints | Not built | AUTH-RBAC | N/A | Gap | All |
| Service layer enforcement | Not built | SERVICE-LAYER | N/A | Gap | All |
| Audit trail | Partial (pipeline only) | — | No | Gap | A, Su |

### 2.10 Admin, Import & Data Operations

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Contact/org import | Working | — | No | Gap | — |
| Seed pipeline stages | Working | — | No | Gap | — |
| Duplicate cleanup/dedup | Working | — | No | Gap | — |
| Outbound Gmail send | Working | — | No | Gap | Sa |
| Gmail validation/status | Working | — | No | Gap | — |
| Voice memo ingest endpoint | Partial | — | No | Gap | — |

### 2.11 V2 Domain Layer (Emerging)

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Party identity + external IDs | Working | — | No | Covered | All |
| Party role bindings | Working | — | No | Covered | All |
| Trust scoring + infractions | Partial | — | No | Covered | Su |
| Opportunities | Working | — | No | Covered | Sa, A |
| TX event dispatcher | Working | — | No | Covered | All |
| V2 operations wrappers | **Broken** | — | No | Partial (`test_crm_v2_operations:89`) | — |

---

## 3. CRM Steward — Agent Capability Map

### Current Skills (16 in manifest, 11 public)

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

**Contract**: Event-driven via TX dispatcher + REST endpoints for queries.

| Event/Endpoint | Exists | Stable API | Priority |
|---|---|---|---|
| Commission accrual created/settled | Yes (V2 TX) | No — service-internal only | P1 |
| Referral closed with commission | Yes (service) | No — service-internal only | P1 |
| Pipeline stage changed | Yes (service) | No — no event hook | P2 |
| Party ↔ Stripe mapping | Yes (party_identity) | No — service helper only (`core/service.py:25`) | P1 |
| Revenue summary by period | No | No | P2 |

### 4.2 Support Interface

**What Support needs from CRM**:
- Contact/org lookup by any identifier
- Interaction history for a contact
- Trust score and infraction history
- Task creation for support follow-ups
- Dispute → infraction pipeline

**Contract**: REST endpoints + agent skills for automated support workflows.

| Event/Endpoint | Exists | Stable API | Priority |
|---|---|---|---|
| Contact lookup (email, name) | Yes | Yes (REST) | — |
| Contact lookup by party_id | Yes | No — service helper only | P1 |
| Interaction history | Yes | Yes (REST) | — |
| Trust score snapshot | Yes (V2) | No | P1 |
| Infraction log | Yes (V2) | No | P1 |
| Create support task | Yes | Yes (REST) | — |
| Dispute resolution workflow | No | No | P2 |

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
4. **Steward skill fragmentation**: 16 skills in manifest, 11 public, but 23+ decorated in service-bus — many not exposed → **BQ-CRM-AGENT-COVERAGE**
5. **Briefing split-brain**: Gmail-based sender (`crm_briefing_service_gmail.py`) vs Postmark delivery (`briefing_delivery.py:185`) running in parallel → **BQ-CRM-BRIEFING-FIX slice 1**
6. **SERVICE-LAYER Gate 1 defers endpoint bypasses**: Some API endpoints bypass service layer; not true single-write-path until Gate 2 lands (`BQ-CRM-SERVICE-LAYER-GATE1.md:61`)

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

### Phase Plan (MP-validated, S447)
1. **Fix this runbook** (R2 → Gate 1 approval)
2. **3 micro-BQs for broken services** (parallel): FIX-OUTREACH, FIX-V2-OPS, FIX-RESEARCH
3. **Continue DATA-INTEGRITY R5, AUTH-RBAC G2, SERVICE-LAYER G2** (immediate)
4. **Reopen CRM-TESTING** as gap-closure track (immediate start, close after service-layer + broken fixes land)
5. **BRIEFING-FIX slice 1**: split-brain resolution (immediate)
6. **AGENT-COVERAGE** (after SERVICE-LAYER): expand steward to all 9 capability domains
7. **BRIEFING-FIX slice 2**: query alignment (after/with SERVICE-LAYER)
8. **INTEGRATION-CONTRACTS** (P1): stable API for Accounting/Support/Sales
9. **ENTERPRISE-FEATURES** re-scoped (P2): custom fields, workflows, lead scoring
10. **V1→V2 migration** → party_id becomes sole identifier (future BQ)

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
| `crm_agent_request.py` (344 lines) | `/api/v1/crm/agent-request` | NL agent endpoint — **DO NOT DELETE** |
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
