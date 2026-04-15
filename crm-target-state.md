# CRM Target-State Runbook — System Standard

> **Purpose**: This document is the authoritative specification for the ai.market CRM system. Every feature described here must (a) work as specified, (b) have automated test coverage, (c) be accessible to the CRM steward agent, and (d) expose integration interfaces for Accounting, Support, and Sales systems. If the system diverges from this document, the system is wrong.

> **Status**: DRAFT — S447. Pending Council review and Gate 1 approval under BQ-CRM-RUNBOOK-STANDARD.

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
| Search/list persons | Working | — | Yes (`find_contact`) | Covered | Sa, Su |
| Update person fields | Partial | SERVICE-LAYER | Partial (service-bus) | Covered | Sa |
| Soft-delete person | Partial | DATA-INTEGRITY | Partial (service-bus) | Covered | — |
| Create organization | Working | — | Yes (`create_organization`) | Covered | Sa, A |
| Search/list organizations | Working | — | No | Gap | Sa |
| Update/delete organization | Partial | SERVICE-LAYER | No | Gap | Sa |
| Merge duplicate contacts | Not built | — | No | — | — |

### 2.2 Relationships & Entity Network

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create relationship | Working | DATA-INTEGRITY | Yes (create only) | Covered | Sa |
| List/query relationships | Working | DATA-INTEGRITY | No (service-bus) | Gap | Sa, Su |
| Relationship types (referral, colleague, reports_to) | Working | — | No | Gap | Sa |
| Entity network graph | Not built | — | No | — | Sa |

### 2.3 Interactions & Communication Log

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Log interaction (email, call, note, social, whatsapp) | Working | — | Yes (`add_note`) | Covered | Su, Sa |
| Interaction dedup (description_hash, 24h window) | Working | — | No | Covered | — |
| List/search interactions | Working | — | No (service-bus) | Covered | Su |
| Email ingest (drop@ai.market → CRM) | Partial | — | No | Gap | Su, Sa |
| Voice memo ingest | Partial (TODO) | — | No | — | — |

### 2.4 Task Lifecycle

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create task (with dedup) | Working | — | Yes (`create_task`) | Covered | Su, Sa |
| Complete task | Working | — | Yes (`complete_task`) | Covered | — |
| Snooze task | Working | — | Yes (`snooze_task`) | Covered | — |
| Cancel task | Working | — | Partial (service-bus) | Gap | — |
| Move task forward | Working | — | Yes (`move_task_forward`) | Covered | — |
| Get pending/overdue tasks | Working | BRIEFING-FIX | Yes (`get_daily_briefing`) | Covered | Su |
| Task states: in_progress, waiting | Not built | — | No | — | Su |
| Task-linked email drafts (CRMEmailDraft) | Working | — | No | Gap | Sa |

### 2.5 Pipeline & Sales Lifecycle

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Pipeline stages (new_lead → closed) | Working | — | Partial (`get_pipeline_status`) | Gap | Sa, A |
| Move contact through pipeline | Partial | — | No | Gap | Sa |
| Bulk pipeline moves | Partial | — | No | Gap | Sa |
| Pipeline history/audit | Partial | — | No | Gap | A |
| Stage duration analytics | Partial | — | No | Gap | Sa |
| Conversion metrics | Not built | — | No | — | Sa |

### 2.6 Referrals & Commissions

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Create referral | Working | DATA-INTEGRITY | No | Partial | A, Sa |
| Referral status tracking | Working | — | No | Partial | A |
| Commission-on-close | Partial | — | No | Gap | A |
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

### 2.10 V2 Domain Layer (Emerging)

| Feature | Status | BQ | Agent | Tests | Integration |
|---|---|---|---|---|---|
| Party identity + external IDs | Working | — | No | Covered | All |
| Party role bindings | Working | — | No | Covered | All |
| Trust scoring + infractions | Partial | — | No | Covered | Su |
| Opportunities | Working | — | No | Covered | Sa, A |
| TX event dispatcher | Working | — | No | Covered | All |
| V2 operations wrappers | **Broken** | — | No | Gap | — |

---

## 3. CRM Steward — Agent Capability Map

### Current Skills (23 decorated, 11 exposed as wrappers)

**Fully accessible via agent**:
- `find_contact`, `upsert_contact`, `create_organization`
- `add_note`, `create_task`, `complete_task`, `snooze_task`, `move_task_forward`
- `get_daily_briefing`, `get_pipeline_status`
- NL compatibility endpoint (`/crm/agent-request`)

**Decorated but NOT exposed as agent wrappers** (12+ skills):
- `update_contact`, `update_person`, `delete_entity`
- Relationship management skills
- Draft management skills
- Research and enrichment skills
- Pipeline move skills
- Interaction search/listing skills

### Target State: Full Agent Coverage

After BQ-CRM-COMPOSITE-SKILLS and this runbook's gap analysis, the steward MUST be able to:

1. **Contact ops**: Create, read, update, soft-delete persons and organizations. Search by any field. Merge duplicates.
2. **Relationship ops**: Create, read, delete relationships. Query entity network.
3. **Interaction ops**: Log any type. Search/filter interactions. Trigger email ingest manually.
4. **Task ops**: Full lifecycle — create, complete, cancel, snooze, reassign. Query pending/overdue/snoozed.
5. **Pipeline ops**: Move contacts through stages. Bulk moves. Query stage analytics.
6. **Referral ops**: Create, track, close referrals. Query commission status.
7. **Outreach ops**: Generate outreach drafts. Assemble context. Trigger research enrichment.
8. **Briefing ops**: Trigger on-demand briefing. Query briefing data.
9. **Admin ops**: Import contacts. Seed pipeline stages. Run data integrity checks.

### Skill Gap Closure Plan
Each gap maps to either BQ-CRM-COMPOSITE-SKILLS (multi-step) or a new BQ. The test suite must include agent-level integration tests: steward skill → service → database → verified outcome.

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
| Commission accrual created/settled | Yes (V2 TX) | No | P1 |
| Referral closed with commission | Yes (service) | No | P1 |
| Pipeline stage changed | Yes (service) | No | P2 |
| Party ↔ Stripe mapping | Yes (party_identity) | No | P1 |
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
| Contact lookup (email, name, party_id) | Yes | Yes | — |
| Interaction history | Yes | Yes | — |
| Trust score snapshot | Yes (V2) | No | P1 |
| Infraction log | Yes (V2) | No | P1 |
| Create support task | Yes | Yes | — |
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
| Contact/org CRUD | Yes | Yes | — |
| Pipeline CRUD + analytics | Yes | Partial | P1 |
| Outreach generation | Broken | No | P1 |
| Research enrichment | Broken | No | P2 |
| Referral CRUD | Yes | Yes | — |
| Relationship graph query | Yes | No | P2 |

---

## 5. Test Standard & Acceptance Matrix

### Principle
Every row in the Capabilities Matrix (Section 2) must have at least one automated test that validates the feature works end-to-end. The test name must reference the capability ID (e.g., `test_2_1_create_person`, `test_2_5_pipeline_move`).

### Current Coverage
- **439 CRM-related tests** across the repo
- **Well covered**: Core CRUD, steward skills, V2 identity/trust/revenue, referral basics, auth guardrails, briefing skill
- **Gaps**: Pipeline service/endpoints, outreach generation/context, research service, briefing delivery/data assembly, draft service, referral endpoints, V2 operations against real DB, steward→V2 integration

### Test Tiers
1. **Unit tests**: Each service method, each model validation rule
2. **Integration tests**: Service → database round-trip, soft-delete filtering, dedup behavior
3. **Agent tests**: Steward skill → service → database → verified outcome
4. **Contract tests**: Each integration endpoint returns expected schema
5. **Regression tests**: Every bug fixed by DATA-INTEGRITY, BRIEFING-FIX, SERVICE-LAYER, AUTH-RBAC

### Gap Closure Plan
A new BQ or extension of CRM-TESTING will generate tests for every "Gap" cell in Section 2. Target: 100% feature coverage per this runbook.

---

## 6. Known Broken/Partial Items Requiring Immediate Fix

1. **Outreach generation broken**: `outreach_generation_service.py` maps to `CRMTaskType.FOLLOW_UP_EMAIL` which doesn't exist as an enum
2. **V2 operations not production-safe**: `operations/service.py` doesn't set `entity_id` despite non-null constraint
3. **Research backfill broken**: Writes `last_researched_at` to `CRMPerson` but field is on `CRMOrganization`
4. **Steward skill fragmentation**: 23 decorated skills, 24 listed, only 11 wrappers exposed
5. **Briefing split-brain**: Gmail-based sender vs Postmark delivery running in parallel
6. **Pipeline under-tested**: No dedicated test file for pipeline service or endpoints

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

### Phase Plan
1. **Current BQs land** → fixes data integrity, auth, briefing, service layer
2. **This runbook** → establishes the standard
3. **Test gap closure** → validates every feature per runbook
4. **Agent skill expansion** → steward covers all features
5. **Integration contracts** → stable API for Accounting/Support/Sales
6. **V1→V2 migration** → party_id becomes sole identifier (future BQ)

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
| `crm.py` (1788 lines) | `/api/v1/crm/*` | Core CRUD, tasks, drafts, briefing, import, admin |
| `crm_pipeline.py` (247 lines) | `/api/v1/crm/pipeline/*` | Pipeline stages and movement |
| `crm_referrals.py` (112 lines) | `/api/v1/crm/referrals/*` | Referral management |
| `crm_agent_request.py` (344 lines) | `/api/v1/crm/agent-request` | NL agent endpoint — **DO NOT DELETE** |
| `briefing.py` | `/api/v1/briefing/*` | Briefing view with HMAC auth |
| `email_drafts.py` | `/api/v1/drafts/*` | Standalone draft CRUD |
