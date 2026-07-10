---
system_name: account-teardown
purpose_sentence: Define the verified erasure footprint of a user account and the safe manual teardown procedure until the automated Council-gated feature ships.
owner_agent: vulcan
escalation_contact: Max (all real-customer erasures, legal-record disposition); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The user-account erasure FOOTPRINT (which tables and external systems hold user-linked data, with re-derivation queries) and the MANUAL teardown procedure and its guardrails. NOT authoritative for the future automated teardown feature (its own Council-gated spec under BQ-E2E-TESTING-FRAMEWORK-S1152), the capability model (account-capability-onboarding.md), sign-up (auth-signup-flow.md), backups (backup-and-recovery.md), or the schema-slimming work (ai-market-backend specs/BQ-DB-SCHEMA-RATIONALIZATION-S1163-GATE1.md, which will shrink this footprint).
linter_version: 1.0.0
---

# Account Teardown & User-Data Erasure

> Covers the verified data footprint of a user account on ai.market (the `users` FK closure, delete-rule inventory, and no-FK "weak link" identifier tables), the manual operator teardown procedure that works today, the external PII surfaces (Stripe, CRM, tokens, backups), and the guardrails any future automated teardown feature must honor. Re-authored S1165 from live production measurements (backend main `abb5b55d`, prod DB read 2026-07-09) after the S1161 draft was lost uncommitted. The automated teardown FEATURE is planned, not shipped — owner BQ: `BQ-E2E-TESTING-FRAMEWORK-S1152` (E2E Option B rides on it); its spec requires UNANIMOUS Council (customer-data class).

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where the credential lives | Owning service |
|---|---|---|---|
| ai.market prod Postgres | The `users` row and its FK closure; all weak-link tables | `AUTHOR_DISPATCH_DATABASE_URL` — Infisical `ai-market-backend`/prod (project `bd272d48…`); Railway-native `DATABASE_URL` vars are STALE, do not use (`backup-and-recovery.md` §F-02 caveat) | ai.market backend |
| Stripe | External PII: customer objects, Connect accounts, payment/refund/transfer records referenced by `stripe_*` id columns | `STRIPE_*` — Infisical `ai-market-backend`/prod | Payments |
| CRM (`crm_*`, `party_person`) | Person/org records keyed by email, independent of `users` | same prod Postgres | CRM Steward |
| Google/Gmail token tables | OAuth grants keyed by email (`gmail_tokens`, `google_tokens`, `gmail_drafts`) | same prod Postgres; Google-side revocation via the token | ai.market backend |
| S3 backups (`aimarket-backups-prod`) | Nightly `pg_dump` copies of ALL of the above under Object Lock (WORM) | AWS backup-writer keys — Infisical `ai-market-backend`/prod | Infra (`backup-and-recovery.md`) |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Verified erasure footprint: FK closure + delete-rule inventory + weak-link scan, with re-derivation queries (this runbook §C/§E-01; evidence trail in backend specs/evidence/schema-classification-s1163/) | SHIPPED | `account-teardown.md:§E-01 queries against pg_constraint / information_schema.columns` | Re-run live S1165 against prod; §C numbers are from that run | 2026-07-09 |
| Manual operator teardown of a known-test account (ordered, single-transaction, dry-run-first) | PARTIAL | `account-teardown.md:§G-01 operator psql procedure (no backend code path exists)` | None automated (manual procedure; mandatory dry-run SELECT phase per §G-01) | 2026-07-09 |
| Automated first-class teardown feature (allowlist + hard is_test flag, API-driven, unanimous-Council-gated; DORMANT until Max go-live: routes flag-gated off, token secret unset) | SHIPPED | `ai-market-backend app/e2e/teardown.py + teardown_guard.py + teardown_inventory.py; routes /api/v1/e2e/{teardown,reset,preflight} gated by E2E_TEST_ROUTES_ENABLED; migration 20260710_003 (append-only e2e_teardown_audit + extended users.is_test trigger); e2e-harness src/e2e_harness/preflight.py prod opt-in` | 41 backend tests (t1 migration + t2 unit + real-PG matrix + preflight) + 18 harness tests; Gate 3 UNANIMOUS t1/t2/t3; Gate 4 prod-verified t1/t2 (route absence, live tamper-trigger proofs); full live run pends Max go-live | 2026-07-10 |
| Right-to-erasure for a real customer end-to-end (DB + Stripe + CRM + tokens + backup-retention handling) | PLANNED | — | n/a (intake procedure §E-03 exists; execution is Max-gated per §H.1) | 2026-07-09 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| users FK closure (prod Postgres) | `psql:$AUTHOR_DISPATCH_DATABASE_URL` (catalog SQL in §E-01; no backend entry point exists) | `public.users` + the recursive FK closure — 121 tables total incl. `users`, live-verified S1165 (was 116 at the S1163 measurement; schema grew) | every backend module writing user-linked rows | 63 distinct tables carry direct FKs to `users` (66 table×delete-rule pairs, 72 FK constraints). Delete rules by distinct table: 43 NO ACTION, 17 CASCADE, 4 SET NULL, 2 RESTRICT. A naive `DELETE FROM users` is BLOCKED by the 43 NO ACTION + 2 RESTRICT tables. |
| Weak-link identifier tables (no FK to users) | `information_schema.columns` scan (§E-01 step 3) | PII-bearing with rows TODAY: `party_person` (394, emails), `crm_v2_backfill_report` (389, customer payloads), `support_ticket` (205) + `support_message` (95) (actor ids), `crm_audit_log` (65), `incident_actions` (21), `meet_notes_interactions` (14, participant emails), `gmail_tokens` (3, emails). Empty-but-armed PII holders: `accounts` (email + stripe_customer_id), `beta_signups`, `beta_feedback`, `partner_inquiries`, `gmail_drafts`, `google_tokens`, `support_email_quarantine`, `credit_deductions`, `policies`, `policy_evaluation_logs`, `journal_entries` (created_by), `api_usage` partition family (user_id), stripe-id holders (`billing_entities`, `refunds`, `reconciliation_records`, `seller_payout_entries`, `stripe_events`, `wallet_pending_topups`). | CRM Steward, support flows, Gmail/Google integrations, Stripe webhooks | CASCADE never reaches these — every teardown must scrub them explicitly by id AND email. `state_events`/`state_events_archive` `actor` values are orchestration instance names (OWNED-ELSEWHERE, out of scope). `ai_crawler_events.user_agent`, `service_registry.owner`, `agent.owner_team` reviewed S1165 as non-personal, excluded. |
| External PII surfaces | Stripe API/dashboard; CRM tools (tool_search "crm"); Google token revocation | Stripe customer/Connect objects; `party_person` + `crm_party_*`; OAuth refresh tokens | Payments, CRM Steward | Deleting DB rows does NOT delete the Stripe customer/account or revoke Google grants; each needs its own call. |
| Backups (WORM) | `backup-and-recovery.md:§E-01/§E-03` | S3 `postgres/ai-market/<date>/` under Object Lock | nightly Railway cron | Backups are IMMUTABLE by design: erasure from backups happens by retention expiry only. A teardown is complete for live data + future backups, never for existing WORM objects (§H.1). |
| Legal-record tables | (frozen — no entry point) | `terms_acceptance`, `disclosure_snapshots` (the two RESTRICT FKs to users, deliberately) | terms enforcement gate, HF disclosure flow | RESTRICT is intentional: consent/e-sign records. Disposition on erasure is a legal/business decision — Max gate, never routine deletion (§H.1). |

Prose: the closure was 116 tables at the S1163 measurement and is 121 today (the HF-metadata-card merge added `disclosure_snapshots` among others). The footprint MOVES with every schema change — §E-01's queries, not this table's snapshot numbers, are the operational source of truth. `BQ-DB-SCHEMA-RATIONALIZATION-S1163` is expected to shrink it substantially (most closure tables are empty: the live business is 43 users, 33 listings, 0 purchases).

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Derive/refresh the footprint (read-only catalog queries) | shell_request → psql $AUTHOR_DISPATCH_DATABASE_URL | Infisical machine identity (sysadmin token) | COMPLETE |
| Vulcan/Mars | Manual guarded teardown of a test account | shell_request → §G-01 procedure | same; plus Max GO for any non-test account | COMPLETE — manual §G-01 remains valid; the automated API path (BQ-ACCOUNT-TEARDOWN-S1165 t1–t3, shipped 2026-07-10) supersedes it for allowlisted is_test accounts once Max flips E2E_TEST_ROUTES_ENABLED |
| CRM Steward | Locate/remove person records by email | crm_request / crm_search_interactions | internal agent auth | PARTIAL — search COMPLETE; hard-delete flow unverified — verify and document in a CRM runbook refresh before the first real erasure |
| SysAdmin agent | Backup-health precondition check | state_request get infra:backup-health | Living State | COMPLETE |
| teardown feature (shipped, dormant) | API-driven erasure with allowlist + is_test guard | POST /api/v1/e2e/teardown/account (signed token, dry-run-first) + GET /api/v1/e2e/preflight/{id}; e2e-harness prod opt-in preflight | unanimous Council (held t1–t3) + Max go-live flag | COMPLETE — shipped under BQ-ACCOUNT-TEARDOWN-S1165 (backend 096ac580/e9c0495c/38c9453d, harness 408ac96); dormant until E2E_TEST_ROUTES_ENABLED + E2E_TEARDOWN_TOKEN_SECRET are set by Max |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Need the current, true data footprint of a user account (erasure intake, teardown spec work, audit)
  pre_conditions:
    - Infisical machine identity valid (~/bin/infisical_auth_refresh.sh succeeds)
    - read access to prod DB
  tool_or_endpoint: psql "$AUTHOR_DISPATCH_DATABASE_URL" with three catalog queries — (1) recursive FK closure from 'users'::regclass over pg_constraint contype='f'; (2) direct-FK delete-rule inventory (SELECT confdeltype, conrelid::regclass FROM pg_constraint WHERE contype='f' AND confrelid='users'::regclass); (3) weak-link scan of information_schema.columns for identifier columns (user|email|customer|owner|created_by|actor|person, stripe_*id) in tables outside the FK set, joined to pg_stat_user_tables.n_live_tup
  argument_sourcing:
    dsn: Infisical secret AUTHOR_DISPATCH_DATABASE_URL, project bd272d48-c5a1-4b52-9d24-12066ae4403c, env prod, domain https://secrets.ai.market, token file ~/.config/infisical/sysadmin-token
  idempotency: IDEMPOTENT
  expected_success:
    shape: closure count (121 as of S1165), per-delete-rule table lists, weak-link tables with rowcounts
    verification: record the run date; diff against §C
  expected_failures:
    - signature: interactive-login garbage from the infisical CLI
      cause: token flag omitted — always pass --token explicitly
    - signature: empty secret value (rc=0, len 0)
      cause: --projectId omitted, querying the wrong project drawer (infisical-secrets.md)
  next_step_success: if counts drifted from §C, refresh §C and §J in the same session (§G-03)
  next_step_failure: fix auth per infisical-secrets.md; never fall back to Railway-native DB URLs
- id: E-02
  trigger: Tear down a known-test account (E2E cleanup) — the only account class deletable without Max
  pre_conditions:
    - account provably test (harness-created/documented; once S1152 lands, allowlist + is_test flag)
    - nightly backup green within 24h (infra:backup-health)
    - E-01 footprint fresh this session
  tool_or_endpoint: §G-01 ordered manual procedure (operator SQL, single transaction, dry-run first)
  argument_sourcing:
    user_id: from the test-account record/harness output, confirmed by SELECT id,email FROM users WHERE id=…
    dsn: as E-01
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: users row gone; closure tables hold no rows for the id; weak-link scrub clean
    verification: §G-01 integrity check
  expected_failures:
    - signature: foreign_key_violation on NO ACTION/RESTRICT tables
      cause: ordering error (§F-01)
    - signature: residual weak-link rows
      cause: no-FK tables never cascade (§F-02)
  next_step_success: log a decision event in Living State recording the teardown (id, date, session)
  next_step_failure: ROLLBACK (single transaction), diagnose per §F, fix ordering, retry once; 2-strike rule applies
- id: E-03
  trigger: A REAL customer requests account deletion / right-to-erasure
  pre_conditions:
    - requester identity verified against the account email
    - request recorded
  tool_or_endpoint: blocking escalation to Max with the E-01 footprint attached — no deletion before Max GO (terms_acceptance / disclosure_snapshots are legal records per §H.1; Stripe/financial records may carry statutory retention)
  argument_sourcing:
    user_id_and_email: from the verified request
    footprint: E-01 output
  idempotency: IDEMPOTENT
  expected_success:
    shape: Max ruling on legal-record + financial-record disposition
    verification: then §G-01 for the DB, plus Stripe deletion/anonymization, CRM removal (CRM Steward), Google token revocation, and a recorded note that WORM backups purge by retention expiry only
  expected_failures: []
  next_step_success: execute per Max ruling; log completion event with a per-surface checklist
  next_step_failure: n/a (intake step)
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `DELETE FROM users` fails with foreign_key_violation | 43 NO ACTION + 2 RESTRICT direct-FK tables (by design); children not deleted first or delete out of order | read the constraint name in the error; `SELECT conrelid::regclass, confdeltype FROM pg_constraint WHERE conname='<name>'` | §G-01 | CONFIRMED |
| F-02 | User PII still findable after a "successful" teardown | weak-link tables have no FK so nothing cascades: CRM (`party_person`), tokens, support tables, `accounts`, beta/partner intake, `api_usage` family | run the §E-01 step-3 weak-link scan filtered by the user's id AND email | §G-02 | CONFIRMED |
| F-03 | PII persists outside the database after full DB teardown | Stripe customer/Connect objects; Google-side OAuth grants; S3 WORM backups | Stripe dashboard search by email; token tables + Google account page; backup objects persisting is EXPECTED (retention) | §G-02 | CONFIRMED |
| F-04 | Footprint numbers in §C disagree with a fresh §E-01 run | schema drift — every migration can grow/shrink the closure (grew 116→121 between S1163 and S1165); the S1163 P3 drop will shrink it | re-run §E-01; diff table lists against §C | §G-03 | CONFIRMED |
| F-05 | Teardown transaction hangs | lock contention with live writers on closure tables | `pg_stat_activity` / `pg_locks` for the blocked pid; confirm `lock_timeout` was set per §G-01 | §G-01 | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: users FK closure (prod Postgres)
  root_cause: the schema deliberately blocks naive deletion (NO ACTION/RESTRICT); deletion must be ordered children-first and guarded (also prevents F-05 via timeouts)
  repair_entry_point: operator psql "$AUTHOR_DISPATCH_DATABASE_URL" single transaction (no backend file:function exists yet; the S1152 feature will own one)
  change_pattern: in ONE transaction with SET LOCAL lock_timeout='5s' and statement_timeout='60s' — (1) DRY RUN, SELECT count(*) per direct-FK table for the user id and record the hit list; (2) delete NO ACTION rows children-first per the closure edges; (3) resolve the 2 RESTRICT tables per authorization (test account — delete rows; real customer — only per the Max ruling from E-03); (4) SET NULL tables need no action (verify nulling acceptable); (5) DELETE FROM users — CASCADE tables clear themselves; (6) COMMIT only if every step's rowcounts match the dry run
  rollback_procedure: ROLLBACK (everything inside the one transaction); after COMMIT there is no rollback — restore path is the nightly backup (backup-and-recovery.md), which is why the backup-green precondition is mandatory
  integrity_check: re-run the dry-run SELECT phase — zero rows for the id across all direct-FK tables and users; then G-02's scrub check
- id: G-02
  symptom_ref: F-02
  component_ref: Weak-link identifier tables (no FK to users)
  root_cause: no FK means no cascade, and external systems (Stripe, Google, CRM) are not touched by SQL at all (covers F-03)
  repair_entry_point: §E-01 step-3 scan parameterized by the user's id AND email; CRM Steward tools; Stripe API/dashboard; Google token revocation before row deletion
  change_pattern: for each PII-bearing weak-link table in §C, delete or anonymize rows matching the user id/email (test account — delete). For a real erasure additionally — Stripe customer delete/anonymize per Max ruling; CRM party_person + interactions via CRM Steward; revoke Google grants BEFORE deleting token rows; record that WORM backups expire by retention, not deletion
  rollback_procedure: none for external surfaces (Stripe deletion is final) — hence the Max gate for real accounts; the DB portion rides G-01's transaction when run together
  integrity_check: weak-link scan by id AND email returns zero PII rows; Stripe email search returns nothing; token tables empty for the account
- id: G-03
  symptom_ref: F-04
  component_ref: users FK closure (prod Postgres)
  root_cause: the schema evolves; the footprint is a moving target
  repair_entry_point: this file — §C numbers/lists + §J refresh fields
  change_pattern: re-run §E-01, update §C counts and table lists, note the drift and its causing migration, refresh §J in the same commit; after the S1163 P3 drop lands this refresh is MANDATORY (a §J refresh trigger)
  rollback_procedure: git revert of the runbook commit
  integrity_check: runbook-lint PASS and §C matches a same-day §E-01 run
```

## §H. Evolve

### §H.1 Invariants

- **Non-custodial stands:** teardown concerns metadata/PII we hold; there is never raw customer dataset content on ai.market to erase.
- **Orchestration freeze:** `state_*`, `peer_messages`, `author_dispatch_*`, `comms_feed`, `alembic_version` are OWNED-ELSEWHERE; no teardown touches them (their `actor` fields are instance names, not customers).
- **Legal-record gate:** `terms_acceptance` and `disclosure_snapshots` (the two RESTRICT tables) are consent/e-sign records; never deleted without an explicit per-request Max ruling, and their RESTRICT delete rule must not be weakened.
- **Backups are WORM:** erasure from `aimarket-backups-prod` happens only by Object-Lock retention expiry; no teardown claims completeness over historical backups.
- **No automated production deletes without the feature's guards:** until the S1152 teardown feature (allowlist + hard `is_test` flag) ships with unanimous Council approval, only the manual §G-01 procedure is legitimate, and without Max only for test accounts.
- **Single-transaction, dry-run-first:** any DB teardown runs inside one transaction with timeouts and a recorded dry-run hit list.
- **Module deviation declaration:** this runbook documents a procedure over the ai-market-backend schema, not a source tree of its own; §H.5 boundary definitions apply to ai-market-backend when the future teardown feature adds code.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Weakening either RESTRICT delete rule (`terms_acceptance`, `disclosure_snapshots`) to CASCADE or SET NULL.
- Deleting legal-record rows as part of the standard (non-Max-ruled) flow.
- Automating deletion of non-test accounts, or removing the allowlist / `is_test` guard from the planned feature.
- Any teardown path touching an orchestration-owned table.
- Changing or removing any §H.1 invariant.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Adding the automated teardown endpoint (new feature on a public surface — independently unanimous-Council class as customer-data work).
- Adding any new PII-bearing table or identifier column (extends the erasure footprint; the §C inventory must be updated in the same change).
- Changing the weak-link scan pattern set in §E-01.
- Changing the §G-01 deletion ordering or its transaction guards.

### §H.4 SAFE predicates

SAFE otherwise:
- Refreshing §C numbers after a §E-01 run (§G-03).
- Adding §I scenarios or documentation fixes.
- Recording a completed teardown in the refresh log.

### §H.5 Boundary definitions

#### module

Per the standard: an immediate subdirectory of ai-market-backend's `app/` source root (`app/api/`, `app/models/`, `app/services/`, …). This runbook itself has no modules.

#### public contract

The future teardown feature's API endpoint(s) and any MCP tool signature it registers; today there is no public contract — the manual §G-01 procedure is operator-internal.

#### runtime dependency

`requirements.txt` / `pyproject.toml [project.dependencies]` of ai-market-backend, when the feature adds code. This runbook adds none.

#### config default

Values shipping in ai-market-backend's canonical config. The allowlist and `is_test` semantics of the future feature are config-default class once they exist.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Disputes unresolvable under the predicates escalate to Max; the ruling is added to §H.1 as a clarification. Anything touching customer data or the legal-record tables escalates to Max regardless of predicate outcome.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: What data do we hold on user X? First action?
    expected_answers:
      - kind: human_action
        action: run the §E-01 footprint queries via psql against AUTHOR_DISPATCH_DATABASE_URL (closure + delete-rule inventory + weak-link scan filtered by the user's id/email)
    weight: 0.08333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: The E2E harness asks to delete its test account. First action?
    expected_answers:
      - kind: human_action
        action: verify pre-conditions — account provably test AND infra:backup-health green within 24h — before any SQL
    weight: 0.08333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: A customer emails asking for their account to be deleted. First action?
    expected_answers:
      - kind: human_action
        action: verify requester identity against the account email, then escalate to Max with the E-01 footprint attached; no deletion before Max GO
    weight: 0.08333333
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: DELETE FROM users WHERE id=… returns a foreign_key_violation. First action?
    expected_answers:
      - kind: human_action
        action: resolve the constraint name to its table and delete rule via pg_constraint, then follow the §G-01 ordering
    weight: 0.08333333
  - id: I-05
    type: isolate
    refs: [F-02]
    scenario: After a teardown, the customer's email still appears in a support thread. First action?
    expected_answers:
      - kind: human_action
        action: run the weak-link scan (§E-01 step 3) by the user's id AND email — no-FK tables never cascade
    weight: 0.08333333
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: The customer says Stripe still shows their card after teardown. First action?
    expected_answers:
      - kind: human_action
        action: check the Stripe customer object by email per §G-02 — external surfaces are untouched by SQL
    weight: 0.08333333
  - id: I-07
    type: isolate
    refs: [F-04]
    scenario: A fresh footprint run says 124 closure tables but §C says 121. First action?
    expected_answers:
      - kind: human_action
        action: treat as schema drift — identify the migration that added the tables, then refresh §C and §J per §G-03
    weight: 0.08333333
  - id: I-08
    type: repair
    refs: [G-01]
    scenario: A test-account teardown must proceed and the two RESTRICT tables hold rows for the account. First action inside the procedure?
    expected_answers:
      - kind: human_action
        action: within the §G-01 single transaction, delete the account's terms_acceptance and disclosure_snapshots rows (test account — allowed) before the users delete
    weight: 0.08333333
  - id: I-09
    type: repair
    refs: [G-02]
    scenario: A gmail_tokens row exists for the account being erased. Correct order of operations?
    expected_answers:
      - kind: human_action
        action: revoke the Google grant first, then delete the token row (§G-02 ordering)
    weight: 0.08333333
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: Proposal — change the terms_acceptance FK to CASCADE "to simplify teardown". Classification?
    expected_answers:
      - kind: classification
        action: BREAKING (weakens the legal-record invariant §H.1)
    weight: 0.08333333
  - id: I-11
    type: evolve
    refs: [§H]
    scenario: Proposal — add a new table storing buyer emails for a notification digest. Classification, and what must ship with it?
    expected_answers:
      - kind: classification
        action: REVIEW — it extends the erasure footprint; the §C weak-link/PII inventory must be updated in the same change
    weight: 0.08333333
  - id: I-12
    type: ambiguous
    refs: [E-01, G-01, G-02]
    scenario: Make sure user X is fully gone. First action?
    expected_answers:
      - kind: human_action
        action: run the §E-01 footprint filtered by the user's id/email
      - kind: human_action
        action: run §G-01's dry-run SELECT phase for the id
      - kind: human_action
        action: run the weak-link scan by id AND email
    weight: 0.08333333
```

Pass threshold: weighted score ≥ 0.80. Equal weights (1/12); no §I.1 justification needed.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1168
last_refresh_commit: 80708fd1
last_refresh_date: 2026-07-10T11:05:00Z
owner_agent: vulcan
refresh_triggers:
  - BQ-DB-SCHEMA-RATIONALIZATION-S1163 P3 drop landing (MANDATORY footprint re-derivation)
  - teardown feature spec/build gates under BQ-E2E-TESTING-FRAMEWORK-S1152
  - any schema migration touching user-linked tables
  - any real erasure request
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-09T23:30:00Z
first_staleness_detected_at: null
```

Refresh log:
- S1168 (2026-07-10): §B/§D PLANNED→SHIPPED for the automated teardown feature (BQ-ACCOUNT-TEARDOWN-S1165 t1–t3 merged: backend 096ac580/e9c0495c/38c9453d, harness 408ac96; Gate 3 UNANIMOUS each chunk, builder excluded; Gate 4 prod-verified t1/t2). Feature is DORMANT: routes flag-gated off, token secret unset on Railway. §C inventory NOT re-derived — the S1163 P3-drop trigger has not fired yet; re-derivation stays mandatory when it lands. Go-live = spec GATE2-T3 deliverable 4 (Max: flip E2E_TEST_ROUTES_ENABLED, set E2E_TEARDOWN_TOKEN_SECRET on Railway backend from Infisical, then ordered create→reset→teardown→footprint-clean verification). last_refresh_commit references the pre-refresh main head (80708fd1); this entry lands in its child commit.
- S1165 (2026-07-09): first committed authoring. Re-derived the full footprint live against prod (closure 121 tables vs 116 at the S1163 measurement — the schema grew with the HF-metadata merge, adding `disclosure_snapshots` RESTRICT); direct-FK inventory 63 distinct tables (43 NO ACTION / 17 CASCADE / 4 SET NULL / 2 RESTRICT by distinct table); broadened the weak-link scan beyond the S1163 list and classified PII-bearing vs non-personal vs orchestration. Replaces the S1161 draft, which was written in a chat container and lost uncommitted — the direct cause of the commit-and-register-same-session discipline this authoring follows.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1165 / 2026-07-09T23:30:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
