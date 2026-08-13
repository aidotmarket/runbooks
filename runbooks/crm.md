---
runbook_id: crm
domain: platform-data
status: ACTIVE
owner: vulcan
system_name: crm
purpose_sentence: The party-model CRM that is ai.market's system of record for people, organisations, identities, roles, interactions, tasks and referrals, with a field-level data dictionary, live production row counts, and the payment and support-ticket connectors.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  The CRM data model and its operating surfaces: the party family (party, party_identity,
  party_person, party_organization, party_role_binding), the crm_party_* operations family,
  the CRM Steward agent and its 28 skills, the three Koskadeux MCP tools, the REST surface
  under /api/v1/crm and /api/v1/accounting/crm, and the two outward connectors (payments via
  party_identity provider stripe_connect, support tickets via support_ticket.requester_party_id).
  This runbook is the source of truth for which CRM tables exist in production and which were
  deliberately deleted. Support-ticket lifecycle itself is not in scope. Morning briefing
  delivery is covered by morning-briefing.md. Marketplace listings, orders and Stripe payment
  processing are not in scope.
authoritative_for:
  - topic: crm-data-model
    section: §C. Architecture & Interactions
  - topic: crm-legacy-table-drop
    section: §C. Architecture & Interactions
  - topic: crm-diagnosis
    section: §F. Isolate
  - topic: crm-connectors
    section: §C. Architecture & Interactions
aliases:
  - crm-architecture
  - crm-pipeline
  - crm-target-state
  - party-model
  - crm-steward
error_signatures:
  - signature: relation "crm_pipeline_stages" does not exist
    section: §F. Isolate
  - signature: relation "crm_people" does not exist
    section: §F. Isolate
  - signature: relation "crm_entities" does not exist
    section: §F. Isolate
  - signature: UndefinedTable
    section: §F. Isolate
  - signature: pipeline stages feature is not yet fully set up
    section: §F. Isolate
  - signature: the pipeline stages migration may not have been run
    section: §F. Isolate
  - signature: empty contact_id on upsert
    section: §F. Isolate
last_verified_at: "2026-08-09"
superseded_by: []
supersedes:
  - crm-architecture
  - crm-pipeline
  - crm-target-state
linter_version: 1.0.0
---

# CRM

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

This runbook replaces three legacy documents (`crm-architecture.md`, `crm-pipeline.md`,
`crm-target-state.md`) that were last accurate in early July 2026 and were never indexed in
`CATALOG.json`, `TOPIC-ROUTER.md` or `README.md`. All three described a fourteen-table `crm_*`
data model as "Active (production)". Those fourteen tables were deliberately deleted from
production on 2026-07-03. An agent working from the superseded documents writes queries
against tables that do not exist and, worse, concludes that a migration failed and tries to
recreate them. Do not do that. See §H.1 Invariant 1.

**Written so it can be used without system access.** §C carries the complete field-level data
dictionary and the production row counts as measured on 2026-08-09, so an agent holding only
this file can reason about what a query will return, decide whether a symptom is expected, and
name the probable cause before touching anything. Where a claim needs live confirmation, §F
gives the exact verification query.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Contact and organisation CRUD on the party model | SHIPPED | `app/services/crm_service.py:CRMEntityService` | Live read via `crm_search_interactions` returned the expected party row | 2026-08-09 |
| Identity resolution across providers | SHIPPED | `app/domains/crm/core/models.py:PartyIdentity` | 477 rows across 4 providers in production | 2026-08-09 |
| Role bindings (buyer / data_seller) | SHIPPED | `app/domains/crm/core/models.py:PartyRoleBinding` | 40 rows, 2 distinct roles in production | 2026-08-09 |
| Interaction log | SHIPPED | `app/domains/crm/core/models.py:CrmPartyInteraction` | 167 rows across 8 interaction types | 2026-08-09 |
| Task lifecycle | SHIPPED | `app/domains/crm/core/models.py:CrmPartyTask` | 87 rows: 55 pending, 27 completed, 5 cancelled | 2026-08-09 |
| Natural-language agent dispatch | SHIPPED | `app/allai/agents/crm_steward.py:CRMStewardAgent` | `crm_request` returned a structured envelope with `actions_taken` | 2026-08-09 |
| CRM Steward skills | SHIPPED | `app/services/crm_steward_skills.py:CRM_SKILLS` | 28 registered skills, 9 read and 19 write; live `crm_request` returned a structured envelope | 2026-08-09 |
| Pipeline stage reporting | DEPRECATED | — | Removed at backend `5143235d` under Max ruling S1490. Backing tables were deleted 2026-07-03; see §F-01 | 2026-08-09 |
| Referrals | PARTIAL | `app/api/v1/endpoints/crm_referrals.py` | 3 rows in `crm_party_referral`; endpoint reads the party table, the legacy model object is dead | 2026-08-09 |
| Email drafts | PARTIAL | `app/api/v1/endpoints/crm.py` | `crm_party_email_draft` has 0 rows in production; path is unexercised | 2026-08-09 |
| Payments connector (party to Stripe Connect) | SHIPPED | `app/services/crm/stripe_connect_identity_reader.py` | 7 `stripe_connect` identities in production | 2026-08-09 |
| Accounting read contracts | PARTIAL | `app/api/v1/endpoints/accounting_crm.py` | Endpoints mounted; `commission_accrual` and `agreement` both 0 rows, so unexercised | 2026-08-09 |
| Support-ticket connector (ticket to party) | PARTIAL | `app/models/support.py:SupportTicket.requester_party_id` | Column, FK and index exist; 0 of 580 tickets populated, see §F-04 | 2026-08-09 |
| Trust scoring | PLANNED | `app/domains/crm/trust/` | `party_infraction` and `party_score_snapshot` both 0 rows | 2026-08-09 |
| Commercial opportunities and agreements | PLANNED | `app/domains/crm/commercial/` | `crm_opportunity` and `agreement` both 0 rows | 2026-08-09 |
| CRM Steward daily maintenance | DEPRECATED | — | Removed at backend `5143235d`. All three checks read deleted tables and had failed silently since 2026-07-03; see §F-01 |  2026-08-09 |
| Morning briefing | SHIPPED | `app/services/crm_briefing_service_gmail.py` | 105 rows in `crm_briefing_runs`; delivery detail lives in morning-briefing.md | 2026-08-09 |
| External CRM MCP endpoint | DEPRECATED | — | `api.ai.market/mcp/crm/mcp` returns 404 by design, see §H.1 Invariant 4 | 2026-08-09 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Party core | `app/domains/crm/core/models.py` | `party`, `party_person`, `party_organization`, `party_identity`, `party_role_binding` | Everything below; `users` via `party_identity(provider='auth_user')` | The canonical participant model. `party` is the spine, the detail tables hang off `party.id`, identities map external systems onto a party. |
| CRM operations | `app/domains/crm/core/models.py` | `crm_party_task`, `crm_party_interaction`, `crm_party_email_draft`, `crm_party_playbook`, `crm_party_learned_preference`, `crm_party_conversation_state`, `crm_party_referral` | Party core by `party_id` | The work layer. Every row points at a party. `legacy_entity_id` on task and interaction is a dead pointer to a deleted table, kept for provenance only. |
| CRM service layer | `app/services/crm_service.py:CRMEntityService` | Party core plus CRM operations | Steward skills, REST endpoints | Roughly 4,000 lines. Contains 15 surviving `select(CRM*)` sites against deleted tables. Most sit behind the hard-disabled read-route shim, but not all: see §C.1, where two sites in this file have no visible guard and reachability is unproven in both directions. Do not read this row as a guarantee. |
| CRM Steward agent | `app/allai/agents/crm_steward.py:CRMStewardAgent` | Reads and writes through the service layer | allAI, Koskadeux MCP tools | Parses natural language, chooses skills, returns a structured envelope with `ok`, `status`, `result`, `error`, `warnings`, `trace_id`, `actions_taken`. |
| Steward skills | `app/services/crm_steward_skills.py:CRM_SKILLS` | Party core plus CRM operations | The steward agent | 28 skills: 9 read (health is one of them) and 19 write. `get_pipeline_status` was removed at backend `5143235d`, see §F-01. |
| REST surface | `app/api/v1/router.py` | Party core plus CRM operations | Frontend, internal callers, accounting | Mounted at `/api/v1/crm` behind `require_crm_auth_by_method` and `enforce_crm_permissions`. |
| Read-route shim | `app/domains/crm/phase_b/read_flags.py:get_read_route` | none | Service layer, steward skills | Always returns `party_only`. `legacy_fallback_enabled()` returns `False` unconditionally. This is what keeps most of the 37 legacy select sites unreachable. Exactly one site is proven reachable and the rest are unproven in both directions; see §C.1. |
| Write-mode shim | `app/core/config.py:get_crm_v2_write_mode` | none | Service layer | Always returns party-authoritative. Named a compatibility shim in its own docstring. |
| Payments connector | `app/services/crm/stripe_connect_identity_reader.py` | `party_identity` where `provider='stripe_connect'` | Stripe Connect, accounting endpoints | Canonical source for seller Stripe Connect identity. Legacy `users.stripe_account_id` and `seller_profiles.stripe_connect_id` are still dual-written but must not be read by new code. |
| Accounting contracts | `app/api/v1/endpoints/accounting_crm.py` | `commission_accrual`, `crm_party_referral`, `party_identity` | Accounting consumers | Read-only, prefix `/api/v1/accounting/crm`, scope `accounting:read`. |
| Support connector | `app/models/support.py:SupportTicket` | `support_ticket`, `support_message` | Support agent, CRM party core | `requester_party_id` and `org_party_id` are real FKs to `party.id`. Populated only when an authenticated non-internal caller opens a ticket. See §F-04. |
| Event outbox | `app/models/crm_events.py` | `crm_entity_event_outbox` | allAI vector corpus | 15 rows. Producer side of the corpus ingestion path. |
| Audit log | `app/domains/crm/core/models.py:CrmAuditLog` | `crm_audit_log` | Service layer writes | 71 rows. |

### §C.1 What exists in production, and what does not

Measured directly against the production database on 2026-08-09. Alembic head at the time of
measurement was `s1299_c1_corpus_control_plane`.

**Live tables and row counts.**

| Table | Columns | Rows | Purpose |
|---|---|---|---|
| `party` | 7 | 480 | Canonical participant spine. |
| `party_person` | 13 | 396 | Person detail, keyed by `party_id`. |
| `party_organization` | 9 | 33 | Organisation detail, keyed by `party_id`. |
| `party_identity` | 7 | 477 | External identifiers mapped onto a party. |
| `party_role_binding` | 6 | 40 | What a party is allowed to be, optionally scoped to a context party. |
| `crm_party_task` | 25 | 87 | Action items. |
| `crm_party_interaction` | 18 | 167 | Communication log. |
| `crm_party_referral` | 16 | 3 | Referral tracking with commission rate. |
| `crm_party_email_draft` | 12 | 0 | AI-drafted emails awaiting review. Unexercised. |
| `crm_party_playbook` | 11 | 0 | Workflow definitions. Unexercised. |
| `crm_party_learned_preference` | 10 | 0 | Extracted preference rules. Unexercised. |
| `crm_party_conversation_state` | 11 | 0 | Telegram steward conversation context. Unexercised. |
| `crm_opportunity` | 14 | 0 | Commercial pipeline, V2. Unexercised. |
| `crm_audit_log` | 8 | 71 | CRM mutation audit. |
| `crm_entity_event_outbox` | 12 | 15 | Outbox to the allAI corpus. |
| `crm_briefing_runs` | 21 | 105 | Morning briefing execution history. |
| `crm_user_roles` | 5 | 1 | CRM role assignment for platform users. |
| `crm_v2_backfill_report` | 17 | n/a | Migration provenance. |
| `crm_fk_rewire_backfill_preimage` | 5 | n/a | Migration provenance. |
| `party_agent` | 10 | 0 | Agent parties. Unexercised. |
| `party_infraction` | 10 | 0 | Trust infractions. Unexercised. |
| `party_score_event` | 7 | 0 | Trust score events. Unexercised. |
| `party_score_snapshot` | 13 | 0 | Trust score snapshots. Unexercised. |
| `agreement` | 10 | 0 | Commercial agreements. Unexercised. |
| `commission_plan` | 8 | 0 | Commission plans. Unexercised. |
| `commission_rule` | 9 | 0 | Commission rules. Unexercised. |
| `commission_override` | 10 | 0 | Commission overrides. Unexercised. |
| `commission_accrual` | 12 | 0 | Commission accruals. Unexercised. |
| `support_ticket` | 34 | 580 | Support tickets. Carries the party FKs. |
| `support_message` | 14 | 572 | Ticket messages. |

**Deleted tables. These do not exist. Do not recreate them.**

Deleted on 2026-07-03 by migration `alembic/versions/20260703_004_s1113_drop_legacy_crm_tables.py`
(revision `s1113_drop_legacy_crm_tables`), under an explicit Max GO and unanimous Council
approval. The migration asserts no external foreign keys remain and logs a row count per table
before dropping.

`crm_referrals`, `crm_pipeline_history`, `crm_contact_pipeline`, `crm_pipeline_stages`,
`crm_email_drafts`, `crm_learned_preferences`, `crm_tasks`, `crm_interactions`,
`crm_relationships`, `crm_playbooks`, `crm_conversation_states`, `crm_people`,
`crm_organizations`, `crm_entities`.

Note the naming trap: the deleted table is `crm_people`, not `crm_persons`. The superseded
runbooks said `crm_persons`, which was never a real table name in either direction.

**Dead model classes still present in the codebase.** `app/models/crm.py`,
`app/models/crm_pipeline.py` and `app/models/crm_referral.py` still declare SQLAlchemy models
whose `__tablename__` points at the deleted tables: `CRMEntity`, `CRMPerson`, `CRMOrganization`,
`CRMRelationship`, `CRMInteraction`, `CRMPlaybook`, `CRMTask`, `CRMEmailDraft`,
`CRMLearnedPreference`, `CRMPipelineStage`, `CRMContactPipeline`, `CRMPipelineHistory`,
`CRMReferral`, `CRMConversationState`. Importing them is harmless. Executing a query built from
them raises `UndefinedTable`. Chunk C2 reduces the programme count from 37 to 34 such query
sites, in 6 files: 15 in `app/services/crm_service.py`, 6 in
`app/services/crm_steward_skills.py`, 5 in
`app/api/v1/endpoints/crm.py`, 3 in `app/services/outreach_context_service.py`, 3 in
`app/services/crm_briefing_service_gmail.py` and 2 in `app/domains/crm/core/service.py`.
Count the legacy sites with the model names that map to dropped tables, not with a bare
`select(CRM` grep: the bare grep returns 41, because `CRMUserRole` and `CRMBriefingRun` point at
`crm_user_roles` and `crm_briefing_runs`, both of which are LIVE. Those 4 sites are healthy and
must not be deleted.
Counting every reference to a dead model class rather than only query sites gives 449 across 15 application
files after C2, down from 460. Chunk C1 of `build:bq-crm-code-reduction-s1490` removed 4 sites
and 50 references at backend `5143235d` on 2026-08-09. The C2 candidate is branch
`build/bq-crm-code-reduction-s1490-c2` at exact head
`64344613f85cae45813ded20bcdc7fc069a51917`; its merge, deployment and Gate 3 are not yet
complete, so the 34-site and 449-reference counts are candidate state, not shipped or live state.

**Reachability is still NOT settled for the remainder.** A first-pass scan looking for a
`get_read_route`, `party_enabled` or `legacy_fallback_enabled` guard within twelve lines above
each query found roughly half the surviving sites with no visible guard, including
`crm_service.py:merge_person_records`, `crm_service.py:get_task`,
`crm_steward_skills.py:list_interactions`, `crm_steward_skills.py:search_interactions`,
`crm_steward_skills.py:create_relationship` and `crm_steward_skills.py:_load_scoped_entity`.
That scan is a heuristic: a missing guard within twelve lines does not prove a site executes,
because the guard may sit further up the call chain. One site was proven reachable and has now
been removed. The rest are unproven in both directions. Treat an `UndefinedTable` from any CRM
path as plausible rather than surprising, and see §F-02.

C2 removes the `get_contact_context` query against `CRMContactPipeline` and
`CRMPipelineStage`, plus both deleted-table checks in `health`: the `CRMEntity` count and the
active `CRMPipelineStage` count. `get_contact_context` keeps its signature and returns
`pipeline=null` for persons when pipeline context is requested. `health` counts live `Party`
rows with `Party.deleted_at IS NULL` and retains the `entity_count` response key for compatibility.

Candidate validation note: `runbook-lint runbooks/crm.md` exits 3 with
`internal error: 'last_harness_date'` on both exact runbook base
`38497d98a31b8f8a3a8ad896204a8c65451b1e96` and the C2 candidate. This is a pre-existing
lint/harness defect, not a lint PASS.

The earlier claim that `CRMConversationStateService` writes to the deleted
`crm_conversation_states` table was false. Exact backend main
`2d7140878b28911e612b7e037d0d926a121ceb55` and the C2 candidate both use live
`CrmPartyConversationState` / `crm_party_conversation_state` storage for upsert, read and delete,
with no legacy `CRMConversationState` insert/delete fallback. C2 preserves that live path; it was
not part of the deletion.

Settling reachability per site is the remaining P0 work of
`build:bq-crm-code-reduction-s1490`, which will replace this paragraph with a proven per-site
list.

### §C.2 Field dictionary

Types are PostgreSQL types as measured in production. "Null" means the column is nullable.

**`party`** — the spine. One row per participant.

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | no | `gen_random_uuid()` | Primary key. Every other CRM table points here. |
| `party_type` | varchar | no | | `person` (447) or `organization` (33). Determines which detail table holds the rest. |
| `display_name` | text | yes | | Denormalised label. Falls back to person or org name, then to "Unknown". |
| `status` | varchar | no | `'active'` | Lifecycle status. |
| `created_at` | timestamptz | yes | `now()` | |
| `updated_at` | timestamptz | yes | `now()` | |
| `deleted_at` | timestamptz | yes | | Soft-delete tombstone. Every read must filter on this being null. |

**`party_person`** — person detail. Keyed by `party_id`, no surrogate key.

| Column | Type | Null | Meaning |
|---|---|---|---|
| `party_id` | uuid | no | Primary key and FK to `party.id`. |
| `first_name` | varchar | yes | |
| `last_name` | varchar | yes | |
| `email` | varchar | yes | Primary match key for upserts. Nullable, so an email-only lookup can miss. |
| `phone` | varchar | yes | |
| `title` | varchar | yes | Job title. |
| `linkedin_url` | varchar | yes | Secondary match key on upsert. |
| `organization_party_id` | uuid | yes | FK to the employer's `party.id`. |
| `personality_profile` | text | yes | AI-generated. |
| `communication_style` | text | yes | AI-generated. |
| `context_summary` | text | yes | AI-generated rolling summary. |
| `last_interaction_at` | timestamptz | yes | Updated when an interaction is logged. Persistently null is a known regression signature, see §F-05. |
| `notes` | text | yes | |

**`party_organization`** — organisation detail.

| Column | Type | Null | Meaning |
|---|---|---|---|
| `party_id` | uuid | no | Primary key and FK to `party.id`. |
| `name` | text | no | |
| `domain` | varchar | yes | Email domain, used for company matching. |
| `industry` | varchar | yes | |
| `parent_org_party_id` | uuid | yes | FK to `party.id` for group structures. |
| `strategic_value` | text | yes | AI-generated. |
| `research_summary` | text | yes | AI-generated. |
| `last_researched_at` | timestamptz | yes | |
| `notes` | text | yes | |

**`party_identity`** — how a party is known to other systems. This is the join point for every
connector.

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | no | `gen_random_uuid()` | |
| `party_id` | uuid | no | | FK to `party.id`. |
| `provider` | varchar | no | | Namespace of the external id. Live values and counts: `crm_entity` 418, `auth_user` 49, `stripe_connect` 7, `email` 3. |
| `external_id` | varchar | no | | The id within that provider. |
| `metadata` | jsonb | yes | `'{}'` | |
| `is_primary` | boolean | yes | `false` | |
| `created_at` | timestamptz | yes | `now()` | |

Provider semantics an agent needs: `auth_user` maps a platform user to a party and is how
authentication resolves to CRM identity. `stripe_connect` is the canonical seller payment
identity and is the payments connector. `crm_entity` is provenance from the pre-July model and
carries the id of a row in a table that no longer exists; it is useful for tracing history and
useless for joining.

**`party_role_binding`** — what a party is entitled to be.

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | no | `gen_random_uuid()` | |
| `party_id` | uuid | no | | FK to `party.id`. |
| `role` | varchar | no | | Live values: `buyer` 29, `data_seller` 11. |
| `context_party_id` | uuid | yes | | Scopes the role to an organisation. Null means global. |
| `granted_at` | timestamptz | yes | `now()` | |
| `revoked_at` | timestamptz | yes | | A binding is live only while this is null. |

**`crm_party_task`** — action items. The widest operations table.

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | no | `gen_random_uuid()` | |
| `party_id` | uuid | no | | The party the task is about. |
| `legacy_entity_id` | uuid | yes | | Dead pointer to a deleted table. Provenance only, never join on it. |
| `assigned_to_user_id` | uuid | yes | | The ownership predicate for scoped reads. 61 set, 26 null in production. Null means admin and internal-key callers only. |
| `playbook_id` | uuid | yes | | FK to `crm_party_playbook`. |
| `legacy_playbook_id` | uuid | yes | | Dead pointer. |
| `task_type` | varchar | no | | follow_up, draft_email, research, schedule_call, reminder, custom. |
| `description` | text | no | | |
| `due_date` | timestamptz | yes | | Original due field. |
| `due_at` | timestamptz | yes | | Newer due field. Both exist; check which one a given code path reads before trusting an overdue calculation. |
| `sla_breach_at` | timestamptz | yes | | |
| `status` | varchar | yes | `'pending'` | Live values: pending 55, completed 27, cancelled 5. |
| `source_interaction_id` | uuid | yes | | FK to `crm_party_interaction`. |
| `legacy_source_interaction_id` | uuid | yes | | Dead pointer. |
| `payload` | jsonb | yes | `'{}'` | |
| `feedback_history` | jsonb | yes | `'[]'` | |
| `reasoning` | text | yes | | Why the AI created this task. |
| `description_hash` | varchar | yes | | Dedup key. |
| `created_at` | timestamptz | yes | `now()` | |
| `updated_at` | timestamptz | yes | `now()` | |
| `deleted_at` | timestamptz | yes | | Soft delete. |
| `completed_at` | timestamptz | yes | | |
| `cancelled_at` | timestamptz | yes | | |
| `snoozed_until` | timestamptz | yes | | |
| `closed_reason` | text | yes | | |

**`crm_party_interaction`** — communication log.

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | no | `gen_random_uuid()` | |
| `party_id` | uuid | no | | |
| `legacy_entity_id` | uuid | yes | | Dead pointer. |
| `user_id` | uuid | yes | | |
| `created_by_user_id` | uuid | yes | | |
| `interaction_type` | varchar | no | | Live values: email 60, note 49, meeting 32, call 10, telegram 7, outbound_email 5, whatsapp 3, message 1. Note that the real set is wider than the six types the superseded runbooks listed. |
| `direction` | varchar | yes | | inbound or outbound. |
| `content` | text | yes | | |
| `raw_transcript` | text | yes | | |
| `summary` | text | yes | | |
| `sentiment_score` | double precision | yes | | |
| `description_hash` | varchar | yes | | Dedup key. |
| `key_takeaways` | jsonb | yes | `'[]'` | |
| `search_vector` | tsvector | yes | | Full-text index. |
| `occurred_at` | timestamptz | yes | `now()` | When it happened, as opposed to when it was recorded. |
| `created_at` | timestamptz | yes | `now()` | |
| `updated_at` | timestamptz | yes | `now()` | |
| `deleted_at` | timestamptz | yes | | Soft delete. |

**`support_ticket`, the CRM-relevant columns only.** Full ticket schema is out of scope.

| Column | Type | Null | Meaning |
|---|---|---|---|
| `public_ref` | varchar | no | The reference an operator quotes. |
| `requester_actor_type` | varchar | no | Always populated. |
| `requester_actor_id` | varchar | no | Always populated. |
| `requester_party_id` | uuid | yes | FK to `party.id`, indexed. 0 of 580 populated. See §F-04. |
| `org_party_id` | uuid | yes | FK to `party.id`. 0 populated. |
| `requester_key` | generated | no | Coalesce of `requester_party_id` then the actor type and id pair. This is why nothing has failed: the key silently falls back to the actor pair when the party link is absent. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Claude (Vulcan/Mars) | Natural-language CRM task | `crm_request` | Koskadeux gateway, internal key | COMPLETE |
| Claude (Vulcan/Mars) | Find a party and its interactions | `crm_search_interactions` | Koskadeux gateway, internal key | COMPLETE |
| Claude (Vulcan/Mars) | Log an interaction | `crm_log_interaction` | Koskadeux gateway, internal key | COMPLETE |
| CRM Steward | Contact search | `find_contact` | read | COMPLETE |
| CRM Steward | Full contact context | `get_contact_context`, `get_entity_context` | read | COMPLETE |
| CRM Steward | CRM snapshot scoped to acting user | `crm_snapshot` | read | COMPLETE |
| CRM Steward | List and search interactions | `list_interactions`, `search_interactions` | read | COMPLETE |
| CRM Steward | Relationship graph | `get_relationships` | read | COMPLETE |
| CRM Steward | Daily briefing | `get_daily_briefing` | read | COMPLETE |
| CRM Steward | Health check | `health` | read | COMPLETE |
| CRM Steward | Create or update contacts and orgs | `upsert_contact`, `update_contact`, `update_person`, `update_organization`, `create_organization` | write | COMPLETE |
| CRM Steward | Notes and meetings | `add_note`, `log_meeting` | write | COMPLETE |
| CRM Steward | Task lifecycle | `create_task`, `update_task`, `complete_task`, `cancel_task`, `snooze_task`, `reassign_tasks` | write | COMPLETE |
| CRM Steward | Relationships | `create_relationship` | write | COMPLETE |
| CRM Steward | Merge and delete | `merge_contacts`, `delete_entity`, `delete_task` | write | COMPLETE |
| CRM Steward | Move a contact's open tasks forward by N days | `move_contact_forward`, `bulk_move_contacts` | write | COMPLETE |
| Support agent | Open a ticket carrying a party link | `support_ticket_create` | internal or authenticated user | PARTIAL — internal callers resolve to a null party id; closed by resolving the requester party at creation. See §F-04. |
| Accounting consumer | Read commission accruals and referrals | `GET /api/v1/accounting/crm/*` | `accounting:read` | PARTIAL — contract shipped but every backing table holds zero rows, so it is unexercised. See §F-10. |

**Gap analysis.** The pipeline gap is closed by deletion rather than repair: `get_pipeline_status`
and the whole daily maintenance routine were removed at backend `5143235d` (see §F-01 and §G-01).
Do not assume the two `move_*` skills shared that fault. Despite the name,
`move_contact_forward` and `bulk_move_contacts` move task due dates and run entirely on the live
`crm_party_task` table via `CRMTaskService.move_entity_tasks_forward`. They are healthy and were
deliberately left alone. Ticket creation is PARTIAL because internal callers resolve to a null
party id, so the ticket-to-party link is never written; the gap closes by resolving the requester
party at creation (see §F-04 and §G-04). The accounting read contracts are PARTIAL because the
endpoints are mounted and correct but every backing table holds zero rows, so no consumer has
ever exercised them (see §F-10).

## §E. Operate

```yaml operate
- id: E-01
  trigger: An operator or agent needs a person's CRM record and history.
  pre_conditions:
    - koskadeux_gateway_reachable
    - person_may_not_exist
  tool_or_endpoint: crm_search_interactions(query, limit)
  argument_sourcing:
    query: email or full name, taken from the operator request or the support ticket requester
    limit: literal, default 10
  idempotency: IDEMPOTENT
  expected_success:
    shape: JSON array of objects, each with an entity object and an interactions array. The entity flattens party_person and party_organization fields together, and unset fields are present as null rather than absent.
    verification: entity.id is a party uuid. Re-running the same query returns the same entity.id.
  expected_failures:
    - signature: empty array
      cause: No party matched the query. The email may be absent from party_person, which is nullable.
    - signature: gateway timeout
      cause: Koskadeux gateway or backend unreachable. Not a CRM data fault.
  next_step_success: Use entity.id as the party id for any follow-up write.
  next_step_failure: Retry with a looser query, for example surname only or the email domain, before concluding the party is absent.
- id: E-02
  trigger: A conversation or call needs to be recorded against a known party.
  pre_conditions:
    - party_exists
    - party_id_known
  tool_or_endpoint: crm_log_interaction(entity_id, interaction_type, content, summary)
  argument_sourcing:
    entity_id: entity.id from E-01
    interaction_type: one of note, call, email, social, whatsapp
    content: the body text of the interaction
    summary: optional short summary, may be omitted
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: A row is created in crm_party_interaction and party_person.last_interaction_at is updated.
    verification: Re-read the party through E-01 and confirm the interaction appears and last_interaction_at moved.
  expected_failures:
    - signature: unknown entity_id
      cause: The uuid is not a party id, or it is a deleted-table id carried on party_identity provider crm_entity.
    - signature: interaction_type rejected
      cause: The value is outside the accepted set. Note the stored data contains wider values such as meeting and telegram written by other paths.
  next_step_success: Confirm with E-01 that the interaction appears.
  next_step_failure: If last_interaction_at stays null after a successful write, see F-05.
- id: E-03
  trigger: An open-ended CRM request that does not map to a single tool.
  pre_conditions:
    - koskadeux_gateway_reachable
  tool_or_endpoint: crm_request(task)
  argument_sourcing:
    task: the operator's request in plain English
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Envelope with ok, status, result, error, error_code, warnings, trace_id and actions_taken.
    verification: actions_taken names the skills that ran. Read it before trusting the prose in result.
  expected_failures:
    - signature: ok true with prose describing a missing table
      cause: A real failure wearing a friendly face. The steward caught an UndefinedTable and narrated it as a setup problem. See F-01.
    - signature: ok false with error_code
      cause: The steward could not complete the task. Read error_code before retrying.
  next_step_success: Read actions_taken to learn which skill ran; that is the code path to inspect if the answer looks wrong.
  next_step_failure: Do not retry a write. Read actions_taken first to find out whether the write already landed.
- id: E-04
  trigger: Accounting needs the Stripe Connect account for a seller.
  pre_conditions:
    - party_id_known
    - caller_holds_accounting_read_scope
  tool_or_endpoint: GET /api/v1/accounting/crm/party-stripe-mappings/{party_id}
  argument_sourcing:
    party_id: entity.id from E-01
  idempotency: IDEMPOTENT
  expected_success:
    shape: A party to Stripe mapping read from party_identity where provider is stripe_connect.
    verification: Only 7 stripe_connect identities existed in production on 2026-08-09, so a hit is rare and a miss is normal.
  expected_failures:
    - signature: "404"
      cause: The party has no stripe_connect identity. Normal for a buyer, and not evidence of data loss.
    - signature: "403"
      cause: The caller lacks the accounting read scope.
  next_step_success: none
  next_step_failure: Do not fall back to users.stripe_account_id or seller_profiles.stripe_connect_id. Those columns are still dual-written but are not the canonical source, see H.1 Invariant 3.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | An operator reports the CRM agent said the pipeline stages table does not exist, or that the migration may not have been run | RESOLVED 2026-08-09 at backend `5143235d`. Historical cause: `get_pipeline_status` queried `crm_contact_pipeline` and `crm_pipeline_stages`, deleted 2026-07-03, and narrated the `UndefinedTable` as a setup problem. The skill, the daily pipeline hygiene check, the stale contact check, the Telegram flow recovery and the whole daily maintenance timer are removed. If this symptom reappears, the deletion has been reverted or the prompt has regained a pipeline capability claim. | Ask `crm_request` a pipeline question. Correct behaviour is a clean statement that the CRM has no named pipeline stages, falling back to `crm_snapshot`. Verified live 2026-08-09 19:34Z. Or run `SELECT to_regclass('public.crm_pipeline_stages')` and expect null. | §G-01 | CONFIRMED |
| F-02 | `UndefinedTable`, or a relation-does-not-exist error naming `crm_people`, from a CRM code path other than pipeline | One of the 37 surviving legacy `select(CRM*)` sites executed. Do not assume this is exotic: per §C.1 only one site's reachability is proven and the rest are unproven in both directions, so an ungated site running is a live hypothesis, not an anomaly. | Grep `select(CRM` across the six files listed in §C.1 and find the enclosing function. Confirm `legacy_fallback_enabled()` still returns False, then check whether the failing site has any guard at all. | §G-02 | CONFIRMED |
| F-03 | An agent proposes recreating `crm_entities`, `crm_people` or any other deleted table, or reports the CRM schema as broken | The agent is working from `crm-architecture.md`, `crm-pipeline.md` or `crm-target-state.md`, all superseded, which describe the deleted fourteen as "Active (production)". | Check whether the agent cites `crm_persons`, a table name that never existed. That phrasing is a reliable tell for the superseded documents. | §G-03 | CONFIRMED |
| F-04 | A support ticket cannot be tied back to a CRM party, or `requester_party_id` is null on every ticket | `app/api/v1/endpoints/support.py:create_ticket` sets `requester_party_id` from the request for internal callers and from `principal.party_id` otherwise. `get_support_principal` returns a null `party_id` for internal actors, and internal callers do not pass one. Every ticket to date was opened by an internal actor. Nothing errors because `requester_key` falls back to the actor pair. | Count tickets where `requester_party_id` is not null against the total. Expect 0 of 580 as of 2026-08-09. | §G-04 | CONFIRMED |
| F-05 | `party_person.last_interaction_at` stays null after interactions are logged | The party update after commit in the interaction write path did not run. Historically a regression in `log_interaction`. | Log an interaction via E-02, then read the party back via E-01 and compare `last_interaction_at`. | §G-05 | HYPOTHESIZED |
| F-06 | A contact upsert returns an empty `contact_id`, output validation fails, and no row appears in `party_person` | An `UndefinedTable` rollback upstream in the same transaction, usually from a legacy select site. The write is aborted but the envelope still returns. | Read `actions_taken` and the backend log for `UndefinedTable` under the same trace_id. | §G-02 | CONFIRMED |
| F-07 | A CRM count looks far too low, for example zero tasks for a user who has tasks | Scoped reads filter on `crm_party_task.assigned_to_user_id`. 26 of 87 tasks have it null, and those are reachable only by admin or internal-key callers. | Count `crm_party_task` rows with a null `assigned_to_user_id` against the total. | §G-06 | CONFIRMED |
| F-08 | An overdue calculation disagrees between two surfaces | `crm_party_task` carries both `due_date` and `due_at`. Different code paths read different columns. | Read both columns for the disputed task and identify which one the surface reads. | §G-06 | CONFIRMED |
| F-09 | A join on `legacy_entity_id`, `legacy_playbook_id` or `legacy_source_interaction_id` returns nothing | These columns point at rows in tables deleted 2026-07-03. They are provenance, not joinable keys. | Confirm the target table is absent with `SELECT to_regclass('public.crm_entities')`. | §G-03 | CONFIRMED |
| F-10 | A commission or agreement query returns empty and the caller reports the feature broken | `commission_accrual`, `commission_plan`, `commission_rule`, `commission_override`, `agreement` and `crm_opportunity` all hold zero rows. The contract is shipped, the feature has never been exercised. | Row-count the table. Empty is the expected state, not a defect. | §G-07 | CONFIRMED |
| F-11 | `api.ai.market/mcp/crm/mcp` returns 404 | Correct behaviour. The external CRM MCP endpoint was removed deliberately at backend `1a514583`. All CRM access goes through the Koskadeux gateway. | Confirm the 404 and stop. | §G-07 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Steward skills
  root_cause: Three CRM Steward paths queried tables deleted on 2026-07-03 and were not behind the disabled read fallback, so they executed. get_pipeline_status ran on demand, _check_pipeline_hygiene and _check_stale_contacts ran daily at 0700 UTC, and _recover_active_flows ran on every agent startup. Every failure was caught, appended to an error list and logged, so the daily job failed silently for 37 days.
  repair_entry_point: app/services/crm_steward_skills.py and app/allai/agents/crm_steward.py
  change_pattern: DONE at backend 5143235d, merged to main and deployed 2026-08-09 under Max ruling S1490 (Event Ledger 24522473). Deleted the skill and its registry entry, all three daily/startup checks, run_daily_maintenance, the timer loop and task, DAILY_MAINTENANCE_HOUR_UTC, STUCK_PIPELINE_DAYS, both alert helpers, and every pipeline capability claim in the agent description, domain declaration and prompt. 972 lines removed. move_contact_forward and bulk_move_contacts were deliberately NOT touched, because despite the names they move task due dates on the live crm_party_task table and are healthy. If this needs rebuilding, build it on crm_opportunity, which exists and is empty; do not recreate the deleted tables.
  rollback_procedure: Revert 5143235d. That restores a known-broken state rather than breaking a working one, so the only reason to revert is if the deletion removed something load-bearing that review later identifies.
  integrity_check: crm_request with a pipeline question returns a clean answer and actions_taken shows crm_snapshot rather than get_pipeline_status. Verified live 2026-08-09 at 1934Z, when the steward reported the CRM has no named pipeline stages and returned real party-model counts. The migration-may-not-have-been-run sentence is gone.
- id: G-02
  symptom_ref: F-02
  component_ref: CRM service layer
  root_cause: A legacy select site against a deleted table became reachable.
  repair_entry_point: app/domains/crm/phase_b/read_flags.py:legacy_fallback_enabled
  change_pattern: Confirm the shim still returns False unconditionally. If it does, the caller reached the query without passing through get_read_route, so route it through the party path or delete the branch. Deleting a dead legacy branch is preferred over guarding it again, because the count of these sites should only ever fall.
  rollback_procedure: Revert the commit. Both states are non-functional for that path, so there is no data risk.
  integrity_check: Re-run the failing operation and confirm no UndefinedTable in the trace. Then re-count the legacy select sites and confirm the total fell from 37.
- id: G-03
  symptom_ref: F-03
  component_ref: CRM service layer
  root_cause: Superseded documentation is still discoverable and still asserts the deleted tables are live.
  repair_entry_point: runbooks/crm.md
  change_pattern: Point the agent at this runbook. The three superseded files are archived and named in this file's supersedes list. Never satisfy such a request by writing a migration that recreates a deleted table; that requires an explicit Max decision and unanimous Council under H.1 Invariant 1.
  rollback_procedure: Not applicable, documentation only.
  integrity_check: The agent's proposed query names party, party_person or crm_party tables rather than crm_entities or crm_people.
- id: G-04
  symptom_ref: F-04
  component_ref: Support connector
  root_cause: Ticket creation only resolves a party for authenticated non-internal callers, and every ticket so far arrived through an internal actor whose principal carries a null party id.
  repair_entry_point: app/api/v1/endpoints/support.py:create_ticket
  change_pattern: Resolve the requester's party at creation time for internal callers too, by looking up party_identity on the requester email or user id in the same way app/api/v1/dependencies/support_ticket_auth.py already does for authenticated users, and fall back to null rather than failing the ticket. Backfilling the existing tickets is a separate decision because it touches 580 customer rows.
  rollback_procedure: Revert. The column is nullable and nothing reads it today, so both states are safe.
  integrity_check: Open a ticket as an internal actor for a known party and confirm requester_party_id is populated and the foreign key resolves.
- id: G-05
  symptom_ref: F-05
  component_ref: CRM operations
  root_cause: The party update following an interaction insert did not execute or was rolled back.
  repair_entry_point: app/services/crm_service.py
  change_pattern: Ensure the party_person last_interaction_at update is committed in the same transaction as the interaction insert and is not conditional on a legacy lookup succeeding.
  rollback_procedure: Revert.
  integrity_check: Log an interaction through E-02 and read the party back through E-01; last_interaction_at must equal the interaction occurred_at.
- id: G-06
  symptom_ref: F-07
  component_ref: CRM operations
  root_cause: Ownership and due-date semantics are ambiguous. Tasks with a null assignee are invisible to scoped readers, and two due columns coexist.
  repair_entry_point: app/domains/crm/core/models.py:CrmPartyTask
  change_pattern: For ownership, decide deliberately whether null-assignee tasks should be visible to a scoped reader and make every read agree. For due dates, pick one column, migrate the other, and remove the loser. Do not add a third.
  rollback_procedure: Revert the read change. A data migration between due columns needs its own backout.
  integrity_check: Both surfaces report the same overdue set for the same user.
- id: G-07
  symptom_ref: F-10
  component_ref: CRM operations
  root_cause: An empty table or a deliberate 404 is being read as a defect. No repair is required.
  repair_entry_point: runbooks/crm.md
  change_pattern: Confirm against the row counts in C.1 and the invariants in H.1 that the observed state is the intended one, then close the investigation without a code change. If the caller genuinely needs the feature, that is new work and needs a Build Queue item, not a repair.
  rollback_procedure: Not applicable, no change is made.
  integrity_check: The investigation closes with a documented reference to C.1 or H.1 rather than a commit.
```

## §H. Evolve

### §H.1 Invariants

- **Invariant 1. The fourteen deleted CRM tables stay deleted.** `crm_entities`, `crm_people`, `crm_organizations`, `crm_relationships`, `crm_interactions`, `crm_playbooks`, `crm_tasks`, `crm_email_drafts`, `crm_learned_preferences`, `crm_pipeline_stages`, `crm_contact_pipeline`, `crm_pipeline_history`, `crm_referrals` and `crm_conversation_states` were dropped under an explicit Max GO and unanimous Council approval. Recreating any of them, in a migration or a fallback-create path, requires the same authority again. An agent that concludes the migration did not run is misreading a deliberate decision.
- **Invariant 2. The party is the canonical participant.** All new reads and writes go through `party` and its detail tables. Reads are party-only; `legacy_fallback_enabled()` returns False and must not be made configurable again.
- **Invariant 3. The `stripe_connect` party identity is the canonical seller payment identity.** `users.stripe_account_id` and `seller_profiles.stripe_connect_id` are still dual-written for compatibility. New code must not read them.
- **Invariant 4. There is no external CRM MCP endpoint.** All agent CRM access goes through the Koskadeux gateway. The 404s on `api.ai.market/mcp/crm/mcp` and the root OAuth routes are deliberate and must not be reintroduced.
- **Invariant 5. Nothing here creates tables at runtime.** The CRM must never rely on a fallback table-creation path. That pattern is what hid the loss of the money-path tables until a customer reported it.
- **Invariant 6. The count of dead references only ever falls.** 449 references to model classes bound to deleted tables remain across 15 application files at C2 candidate head `64344613f85cae45813ded20bcdc7fc069a51917`, and `build:bq-crm-code-reduction-s1490` exists to remove them in evidence-backed phases. No change may add a new reference to a dead model class, and a change that guards a dead branch rather than deleting it needs a stated reason.
- **Invariant 7. Soft delete is real.** Every read filters on a null `deleted_at`. A read that forgets this leaks tombstoned rows.

### §H.2 BREAKING predicates

- Recreating, renaming or altering the type of any column in `party`, `party_person`, `party_organization`, `party_identity` or `party_role_binding`.
- Changing the meaning of a `party_identity` provider value, or reusing a retired provider name.
- Changing the ownership predicate for scoped CRM reads.
- Adding a required column without a default to any table with rows.
- Changing or removing any invariant in §H.1.

### §H.3 REVIEW predicates

- Adding or removing a steward skill, or changing a skill's access level between read and write.
- Adding a new `party_identity` provider value.
- Changing which of `due_date` or `due_at` a surface reads.
- Adding a new endpoint under `/api/v1/crm` or `/api/v1/accounting/crm`.
- Deleting any legacy select site, because each deletion changes a live file.

### §H.4 SAFE predicates

- Fixing a bug inside an existing skill without changing its input or output schema.
- Adding tests.
- Updating this runbook.
- Internal refactor inside a single module that preserves all public signatures.

### §H.5 Boundary definitions

#### module

An immediate subdirectory of `app/` in `ai-market-backend`: `app/api/`, `app/models/`, `app/services/`, `app/domains/`, `app/allai/`. `app/` itself is the source root. `alembic/`, `tests/` and `scripts/` are peer trees, not modules.

#### public contract

The OpenAPI document served by the backend, the three Koskadeux MCP tool signatures (`crm_request`, `crm_search_interactions`, `crm_log_interaction`), and the `CRM_SKILLS` registry entries with their declared input and output schemas.

#### runtime dependency

An entry in the backend `requirements.txt` or the `pyproject.toml` project dependencies.

#### config default

A value shipping in the backend's canonical config, `app/core/config.py`. Environment overrides and feature flags are not config defaults.

### §H.6 Adjudication

If two agents classify the same change differently, the more restrictive classification wins. Anything touching Invariant 1 or Invariant 3 escalates to Max regardless of classification, because both concern deletion authority and the money path.

## §I. Operational Examples

```yaml acceptance
scenario_set:
  - id: I-01
    type: isolate
    refs: [F-01, G-01]
    scenario: >
      An operator reports that asking the CRM agent for pipeline status returns a friendly
      message saying the pipeline stages table does not exist and that the migration may not
      have been run. The operator asks whether they should re-run migrations against
      production. The diagnosing agent has no system access.
    expected_answers:
      - kind: classification
        label: >
          No migration. The table was deleted deliberately on 2026-07-03 by migration
          s1113_drop_legacy_crm_tables under an explicit Max GO and unanimous Council
          approval. The agent's own advice is wrong. The real defect is that three steward
          skills still query the deleted pipeline tables. Route to G-01.
  - id: I-02
    type: isolate
    refs: [F-04, G-04]
    scenario: >
      Support asks why no support ticket can be traced back to a CRM contact, and wonders
      whether the ticket to CRM link was ever built. The diagnosing agent has no system
      access.
    expected_answers:
      - kind: classification
        label: >
          The link exists. The support ticket requester party column is a real indexed foreign
          key to party.id. It is null on all 580 tickets because ticket creation only resolves
          a party for authenticated non-internal callers, and every ticket so far came from an
          internal actor. This is a population gap, not a missing feature. Route to G-04.
  - id: I-03
    type: operate
    refs: [E-01]
    scenario: >
      An agent needs the CRM record and interaction history for someone known only by email
      address.
    expected_answers:
      - kind: tool_call
        tool: crm_search_interactions
        argument_keys: [query, limit]
  - id: I-04
    type: isolate
    refs: [F-09]
    scenario: >
      An agent is asked why a report joining crm_party_task.legacy_entity_id to a contact
      record returns no rows at all, and is considering filing a data-loss incident.
    expected_answers:
      - kind: classification
        label: >
          Not data loss. legacy_entity_id points at crm_entities, deleted 2026-07-03. It is
          provenance, not a joinable key. Join on party_id instead. Close without an incident.
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1490
last_refresh_commit: e54ef41ed81421815f9b4e0b8d7b84352455b927
last_refresh_date: "2026-08-09T00:00:00Z"
owner_agent: vulcan
refresh_triggers:
  - Any migration that adds, drops or renames a party or crm_party table
  - Any change to the CRM_SKILLS registry
  - Any change to the Stripe Connect identity reader or the accounting contract endpoints
  - Any change to support ticket party resolution
  - Incident touching CRM data
scheduled_cadence: 90d
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
retrofit: true
trace_matrix_path: audits/crm-runbook-rewrite-s1490-trace.md
word_count_delta:
  before: 10971
  after: 6406
  pct: -41.6
```
