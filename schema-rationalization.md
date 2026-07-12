---
system_name: schema-rationalization-s1163
purpose_sentence: Operate the S1163 classify to quarantine to drop procedure for pruning empty, unused tables from the production ai.market Postgres schema.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: BQ-DB-SCHEMA-RATIONALIZATION-S1163 production Postgres schema classification, quarantine monitoring, one-shot quarantine migrations, and P3 drop gates. NOT authoritative for ordinary Alembic practice outside this program, backup implementation, account teardown semantics, or future live-table consolidation BQs.
linter_version: 1.0.0
---

# Schema Rationalization / Quarantine / Drop

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

S1163 reduces the production Postgres schema by classifying every `public` table, moving empty unused tables to `quarantine`, watching for live misses, then dropping only after a quiet window and a unanimous Council gate. The hard safety invariant is execution-time empty-only enforcement under an exclusive table lock.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Audited classification snapshots and manifest | SHIPPED | `scripts/schema_classification_s1163.py:run_snapshot` | backend unit coverage for pure helpers; live read-only S1163/S1165 evidence | 2026-07-11 |
| P2 quarantine one-shot migration | SHIPPED | `alembic/versions/20260711_001_s1163_p2_quarantine_one_shot.py:upgrade` | migration code review + production execution; empty-only runtime assertions | 2026-07-11 |
| P2 quarantine reversal | SHIPPED | `alembic/versions/20260711_001_s1163_p2_quarantine_one_shot.py:downgrade` | one-line inverse documented per table; no live miss yet | 2026-07-11 |
| Three-day quarantine window monitor | SHIPPED | `psql:pg_stat_user_tables` | live S1163 operator procedure | 2026-07-12 |
| P3 drop one-shot migration | PLANNED | `alembic/versions/<pending>_s1163_p3_drop_quarantined_tables.py:upgrade` | must be authored with same assertion pattern as P2 | 2026-07-12 |
| P3 exclusion handling for roadmap tables | SHIPPED | `scripts/schema_classification_s1163.py:ROADMAP_TABLES` | Max checkpoints S1184/S1187 | 2026-07-12 |

P2 production fact: revision `s1163_p2_quarantine` moved 21 tables from `public` to `quarantine` at 2026-07-11T16:50Z and was merged to backend `main` at `31b601788854365d1861c01d029f231d8e721853`.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Classification tooling | `scripts/schema_classification_s1163.py:main` | `specs/evidence/schema-classification-s1163/snapshot-N.json`; `specs/evidence/schema-classification-s1163.json`; `specs/evidence/schema-classification-s1163.md` | Production Postgres read-only DSN from Infisical project `bd272d48-c5a1-4b52-9d24-12066ae4403c`; backend/koskadeux/frontend repo scans | Captures two write-stat snapshots, validates stats reset/window, counts rows, scans models/raw SQL/dependencies, and emits KEEP / KEEP-ROADMAP / OWNED-ELSEWHERE / QUARANTINE. |
| P2 quarantine migration | `alembic/versions/20260711_001_s1163_p2_quarantine_one_shot.py:upgrade` | Postgres schemas `public`, `quarantine`, `mcp_safe`; Alembic revision `s1163_p2_quarantine` | Alembic one-shot execution against production; backup health; Council review gates | Requires `RUN_ONE_SHOT_S1163_P2=1`, checks down-revision parent, creates `quarantine`, drops affected `mcp_safe` mirror views, asserts no external blockers, locks/counts/moves each candidate. |
| Quarantine monitor | `psql:pg_stat_user_tables` | `quarantine` schema stats; Railway deployment logs; Titan-1 `/var/tmp/koskadeux/*.log` and `~/Library/Logs/aimarket_*.log` | Railway GraphQL API; Infisical-sourced `DATABASE_PUBLIC_URL`; Titan local logs | Runs during the 3-day window; any quarantined-table hit is a miss requiring immediate move-back and reclassification. |
| P3 drop migration | `alembic/versions/<pending>_s1163_p3_drop_quarantined_tables.py:upgrade` | Postgres `quarantine` schema; Alembic revision after `s1163_p2_quarantine`; migration history in git | UNANIMOUS Council, backup health, `mcp_safe` mirror view precedent, Max roadmap rulings | Drops only the quiet quarantined set; retains schema history in Alembic/git; must mirror P2 empty-only and one-shot guard design. |
| Backup gate | `state_request:get infra:backup-health` | Living State key `infra:backup-health` | `backup-and-recovery.md`; Railway backup job | P2 and P3 cannot run unless ai-market Postgres backup is green within 24h. |

Current P2 quarantine set: `access_tokens`, `agent_telemetry`, `agent_telemetry_2026_03`, `agent_telemetry_2026_04`, `agent_telemetry_default`, `allai_admin_grants`, `allai_mediation`, `analytics_events`, `conversation_messages`, `conversations`, `dataset_licenses`, `google_tokens`, `knowledge_base`, `license_templates`, `llm_conversations`, `low_confidence_privacy_backfills`, `processed_emails`, `quality_scores`, `referral_earnings`, `seller_inquiry_preferences`, `stripe_webhook_events`.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan/mars | Refresh classification evidence | backend shell + Infisical CLI + read-only Postgres connection | Infisical backend prod secret read; read-only DB session | COMPLETE |
| vulcan/mars | Execute P2/P3 one-shot migration | backend shell with Alembic and explicit one-shot env guard | Production DB DDL; requires backup green and review gates | COMPLETE |
| vulcan/mars | Monitor quarantine window | psql, Railway GraphQL, local Titan grep | read-only DB, Railway read logs, local log read | COMPLETE |
| MP (Codex) | Build/review migration code | `council_request` build/review | backend repo branch; no prod credentials | COMPLETE |
| AG/DS/XAI | Independent schema-risk review | `council_request` review | read-only code/spec review | COMPLETE |
| Max | Business roadmap checkpoint and final P3 approval | Owner ruling | Product owner authority over KEEP-ROADMAP exclusions | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Refresh the classification snapshot and manifest before a quarantine/drop decision.
  pre_conditions:
    - backend repo is on current main and has no unrelated working tree edits
    - Infisical CLI can read project bd272d48-c5a1-4b52-9d24-12066ae4403c env prod
    - read-only production DSN is sourced from AUTHOR_DISPATCH_DATABASE_URL, DATABASE_PUBLIC_URL, or DATABASE_URL; never passed on argv
  tool_or_endpoint: "from ai-market-backend: AUTHOR_DISPATCH_DATABASE_URL=\"$DSN\" .venv/bin/python scripts/schema_classification_s1163.py snapshot; then AUTHOR_DISPATCH_DATABASE_URL=\"$DSN\" SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS=3 .venv/bin/python scripts/schema_classification_s1163.py classify"
  argument_sourcing:
    DSN: "infisical secrets get AUTHOR_DISPATCH_DATABASE_URL --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c --env prod --plain, fallback DATABASE_PUBLIC_URL only when AUTHOR_DISPATCH_DATABASE_URL is unavailable"
    SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS: "3 per Max S1165 ruling for this program"
  idempotency: IDEMPOTENT
  expected_success:
    shape: new snapshot-N.json and refreshed schema-classification-s1163.{json,md}; manifest status FINAL_ELIGIBLE when window and stats_reset checks pass
    verification: "git diff specs/evidence/schema-classification-s1163*; manifest write_delta_evidence.valid=true before using it for a migration"
  expected_failures:
    - signature: "Set AUTHOR_DISPATCH_DATABASE_URL, DATABASE_PUBLIC_URL, or DATABASE_URL"
      cause: no DSN was supplied through env
    - signature: "status=PRELIMINARY or reason=stats_reset_changed"
      cause: evidence window is not valid for a migration gate
  next_step_success: present classification and KEEP-ROADMAP candidates to Max/Council before any DDL
  next_step_failure: fix credential/window issue and rerun; do not author or execute DDL from a PRELIMINARY manifest
- id: E-02
  trigger: Execute a quarantine migration after classification and Max checkpoint.
  pre_conditions:
    - backup health for ai-market-pg is green within 24h in infra:backup-health
    - Council review gate accepted the migration diff
    - Max approved KEEP-ROADMAP list and any FK/dependency exclusions
    - local alembic heads has exactly one head and the migration down_revision matches production current
    - migration contains lock-before-count empty-only assertions inside the same transaction
    - one-shot guard is set only for the operator run, not app startup
  tool_or_endpoint: "RUN_ONE_SHOT_S1163_P2=1 alembic upgrade s1163_p2_quarantine"
  argument_sourcing:
    backup_status: "state_request get infra:backup-health"
    production_current: "alembic current against production or Railway deploy log current revision"
    down_revision: "migration file down_revision; P2 was 20260710_003_bq_account_teardown_t2"
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: alembic revision id
  expected_success:
    shape: 21 approved empty tables moved public to quarantine; affected mcp_safe mirror views dropped/recreated to point at quarantine per P2 precedent
    verification: "SELECT schemaname, relname FROM pg_stat_user_tables WHERE relname = ANY(:quarantine_set) ORDER BY relname; all schemaname='quarantine'"
  expected_failures:
    - signature: "is an operator-controlled one-shot migration"
      cause: RUN_ONE_SHOT_S1163_P2 missing
    - signature: "empty-only quarantine invariant failed"
      cause: a candidate table has rows after lock acquisition
    - signature: "external dependencies on quarantine tables"
      cause: pg_depend/FK/view/policy/function blocker still exists
  next_step_success: start E-03 immediately and run it through the 3-day quarantine window
  next_step_failure: stop; repair per §G; never bypass the assertion or run through app startup
- id: E-03
  trigger: Run the mandatory 3-day quarantine window monitoring check.
  pre_conditions:
    - P2 quarantine has executed in production
    - monitoring window is still open or being closed for P3
    - quarantine_set is the exact set in §C, not every relation-does-not-exist string in logs
  tool_or_endpoint: "three checks: (a) psql read-only pg_stat_user_tables; (b) Railway deploymentLogs GraphQL filtered for 'does not exist'/'UndefinedTable'; (c) Titan-1 grep /var/tmp/koskadeux/*.log and ~/Library/Logs/aimarket_*.log"
  argument_sourcing:
    DATABASE_PUBLIC_URL: "Infisical project bd272d48-c5a1-4b52-9d24-12066ae4403c env prod"
    railway_token: "Infisical/Railway operator token per titan-1.md; do not print"
    active_backend_deployment: "Railway GraphQL deployments for ai-market-backend production, latest active/success deployment"
  idempotency: IDEMPOTENT
  expected_success:
    shape: "a) every quarantine table has n_live_tup=0 and n_tup_ins=n_tup_upd=n_tup_del=0; b/c) no log hit names a quarantined table"
    verification: |
      psql "$DATABASE_PUBLIC_URL" -c "SELECT relname,n_live_tup,n_tup_ins,n_tup_upd,n_tup_del FROM pg_stat_user_tables WHERE schemaname='quarantine' ORDER BY relname;"
      Railway GraphQL deploymentLogs(active backend deployment, filter='does not exist OR UndefinedTable'); cross-check any relation name against §C quarantine_set
      # note: agent_telemetry substring intentionally matches the _2026_03/_2026_04/_default partitions; verify any hit against the exact §C quarantine_set before acting
      grep -Ei "does not exist|UndefinedTable|access_tokens|agent_telemetry|allai_admin_grants|allai_mediation|analytics_events|conversation_messages|conversations|dataset_licenses|google_tokens|knowledge_base|license_templates|llm_conversations|low_confidence_privacy_backfills|processed_emails|quality_scores|referral_earnings|seller_inquiry_preferences|stripe_webhook_events" /var/tmp/koskadeux/*.log ~/Library/Logs/aimarket_*.log
  expected_failures:
    - signature: "quarantine table has n_live_tup > 0 or n_tup_ins/upd/del > 0"
      cause: a writer reached a quarantined table
    - signature: "relation '<quarantined_table>' does not exist or UndefinedTable for a quarantined table"
      cause: live code references a quarantined table
    - signature: "relation 'orders' does not exist or crm_* does not exist"
      cause: false alarm if the named table is not in §C quarantine_set; see T-2026-000234/T-2026-000235
  next_step_success: after the full quiet 3-day window, proceed to P3 gate E-04
  next_step_failure: if hit names a quarantined table, run one-line move-back, reclassify, and record the miss; if false alarm, record as unrelated and continue monitoring
- id: E-04
  trigger: Execute P3 drop after a quiet quarantine window.
  pre_conditions:
    - full 3-day window completed with E-03 success
    - UNANIMOUS Council approval for the P3 migration
    - backup health for ai-market-pg is green within 24h
    - migration down_revision is s1163_p2_quarantine or current accepted head after merge-revision reconciliation
    - migration locks each quarantined table, asserts count(*)=0 at execution time, then drops
    - mcp_safe mirror-view handling follows P2 precedent for any table with an mcp_safe view
    - referral_codes is excluded as KEEP-ROADMAP by Max ruling S1187
    - invoices, payments, purchases, refunds and their roadmap family are excluded by Max checkpoint S1184
  tool_or_endpoint: "RUN_ONE_SHOT_S1163_P3=1 alembic upgrade <s1163_p3_drop_revision>"
  argument_sourcing:
    quiet_window_evidence: "E-03 saved operator notes/log excerpts"
    council_verdicts: "Council dispatch/review records; must be unanimous"
    p3_revision: "backend Alembic file authored for P3"
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: alembic revision id
  expected_success:
    shape: quarantined empty tables dropped; excluded KEEP-ROADMAP tables remain in public; production health stays green
    verification: "SELECT to_regclass('quarantine.<table>') for each dropped table returns null; /health green; no quarantine relation errors for 7 days"
  expected_failures:
    - signature: "empty-only drop invariant failed"
      cause: quarantined table gained rows or stats indicated missed write
    - signature: "view or dependency blocker"
      cause: mcp_safe or another object still references a drop target
  next_step_success: update account-teardown footprint and close S1163 with final table count
  next_step_failure: stop; move back affected table if needed; reclassify and redispatch P3 only after new unanimous gate
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Classification manifest is `PRELIMINARY` or write-delta invalid | Fewer than two snapshots, window below `SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS`, or `pg_stat_database.stats_reset` changed | Read `write_delta_evidence` in `specs/evidence/schema-classification-s1163.json`; compare `valid`, `reason`, `window_days`, `stats_reset_changed` | §G-01 | CONFIRMED |
| F-02 | Quarantine/drop migration refuses to run as one-shot | Required `RUN_ONE_SHOT_S1163_P2` or `RUN_ONE_SHOT_S1163_P3` missing | Read Alembic stderr for "operator-controlled one-shot migration"; inspect environment of the one command only | §G-02 | CONFIRMED |
| F-03 | Migration aborts with empty-only invariant failure | Candidate table has rows at execution time after lock acquisition | Read exception text for table name and row count; verify with `SELECT count(*) FROM <schema>.<table>` using read-only DSN | §G-03 | CONFIRMED |
| F-04 | Migration aborts on external dependencies or mcp_safe blocker | FK, view, trigger, policy, function, grant, or mcp_safe mirror still depends on target | Use exception blocker list; query `pg_depend`/`pg_constraint`; compare against P2 `MCP_SAFE_MIRROR_VIEWS` precedent | §G-04 | CONFIRMED |
| F-05 | Quarantine monitor finds n_live_tup or n_tup_ins/upd/del nonzero | A production writer used a quarantined table during the window | Run E-03 pg_stat query; confirm the relname is in §C quarantine_set | §G-05 | CONFIRMED |
| F-06 | Railway/Titan logs show `relation ... does not exist` or `UndefinedTable` for a quarantined table | Live code or job still references a table moved to `quarantine` | Extract relation name from the log and exact timestamp; cross-check against §C quarantine_set | §G-05 | CONFIRMED |
| F-07 | Railway/Titan logs show missing `orders` or `crm_*` relation | False-alarm class: table was never in the S1163 quarantine set; known unrelated tickets T-2026-000234/T-2026-000235 | Extract relation name and compare against §C quarantine_set; if absent, route to owning ticket/runbook, not S1163 move-back | N/A — repair belongs to the owning ticket/runbook (T-2026-000234 / T-2026-000235), not this runbook | CONFIRMED |
| F-08 | P3 proposal includes `referral_codes`, invoices, payments, purchases, refunds, or roadmap family | Builder missed Max S1187/S1184 KEEP-ROADMAP exclusions | Inspect P3 target list and migration constants before dispatch; grep migration for excluded names | §G-06 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Classification tooling
  root_cause: Classification evidence is not migration-grade because write-delta sampling is invalid or too short.
  repair_entry_point: scripts/schema_classification_s1163.py:run_snapshot
  change_pattern: Capture a new read-only snapshot after the required interval, then rerun classify with SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS=3 for S1163. If stats_reset changed, restart the snapshot pair; do not waive this for P2/P3.
  rollback_procedure: none; snapshots are evidence artifacts. Supersede bad evidence with new snapshot files and record why.
  integrity_check: manifest write_delta_evidence.valid=true and status FINAL_ELIGIBLE before Council/Max migration gate.
- id: G-02
  symptom_ref: F-02
  component_ref: P2 quarantine migration
  root_cause: One-shot DDL guard intentionally prevents app-startup Alembic from running the migration.
  repair_entry_point: alembic/versions/20260711_001_s1163_p2_quarantine_one_shot.py:_require_one_shot_guard
  change_pattern: Rerun manually with the exact run guard for the intended revision (`RUN_ONE_SHOT_S1163_P2=1` or P3 equivalent) after rechecking backup health and production current revision.
  rollback_procedure: unset the guard after the operator command; never persist it into Railway app startup env.
  integrity_check: migration proceeds past guard and either completes or fails on a real schema safety assertion.
- id: G-03
  symptom_ref: F-03
  component_ref: P3 drop migration
  root_cause: A target table is not empty at execution time, so S1163 is no longer allowed to quarantine/drop it.
  repair_entry_point: alembic/versions/<pending>_s1163_p3_drop_quarantined_tables.py:upgrade
  change_pattern: Remove the table or whole partition family from the migration target, reclassify it as KEEP or KEEP-ROADMAP, and redispatch review. Never delete rows to satisfy S1163; row disposition is out of scope.
  rollback_procedure: failed migration transaction rolls back automatically; if any prior table moved in an earlier committed step, use G-05 move-back for that table.
  integrity_check: rerun count(*) and classification manifest; P3 target set excludes the non-empty relation.
- id: G-04
  symptom_ref: F-04
  component_ref: P2 quarantine migration
  root_cause: A keep object still depends on a target relation, or an mcp_safe mirror view was not dropped/recreated around the schema move/drop.
  repair_entry_point: alembic/versions/20260711_001_s1163_p2_quarantine_one_shot.py:_assert_no_residual_external_dependencies
  change_pattern: "Treat FK edges to KEEP as a KEEP-ROADMAP review blocker. For mcp_safe mirrors, follow P2: drop affected views before SET SCHEMA/DROP and recreate only when the target remains queryable; do not silently break read-only mirrors."
  rollback_procedure: failed transaction rolls back; if already committed, restore the affected view from the prior migration DDL or move back per G-05.
  integrity_check: dependency blocker query returns empty; affected mcp_safe views either point to the valid schema or are intentionally absent after P3.
- id: G-05
  symptom_ref: F-06
  component_ref: Quarantine monitor
  root_cause: The quarantine window found a real live dependency on a quarantined table.
  repair_entry_point: psql:ALTER_TABLE_SET_SCHEMA
  change_pattern: "One-line move-back: ALTER TABLE quarantine.<table_name> SET SCHEMA public; then reclassify the table/family, record the miss with log evidence, and remove it from P3 targets."
  rollback_procedure: To re-quarantine after a fixed follow-up, use a new reviewed one-shot migration with the same lock-before-count invariant; do not ad-hoc move public back to quarantine during incident response.
  integrity_check: original failing log path stops erroring; `to_regclass('public.<table_name>')` is non-null; new classification marks the table KEEP or KEEP-ROADMAP unless fresh evidence proves otherwise.
- id: G-06
  symptom_ref: F-08
  component_ref: P3 drop migration
  root_cause: P3 target construction ignored owner business exclusions.
  repair_entry_point: alembic/versions/<pending>_s1163_p3_drop_quarantined_tables.py:QUARANTINE_TABLES
  change_pattern: Remove `referral_codes` per Max S1187 and remove invoices/payments/purchases/refunds plus the finance roadmap family per Max S1184. Re-run grep and Council review before execution.
  rollback_procedure: if not executed, amend the migration. If executed, restore from backup because P3 drop is destructive after commit.
  integrity_check: grep of the P3 migration contains none of the excluded names except in comments documenting exclusion.
```

## §H. Evolve

### §H.1 Invariants

- Empty-only is enforced at migration execution time inside the DDL transaction after `ACCESS EXCLUSIVE` lock acquisition; classification evidence alone is never sufficient.
- P2 and P3 are operator-controlled one-shot migrations and must not run from Railway app startup.
- Nightly ai-market Postgres backup must be green within 24h before P2 or P3.
- OWNED-ELSEWHERE tables (`state_*`, `author_dispatch_*`, `peer_messages`, `comms_feed`, `alembic_version`) are outside S1163 and cannot be quarantined or dropped here.
- Partition families are one classification/drop unit; no child-only quarantine/drop.
- `referral_codes` is KEEP-ROADMAP by Max S1187; invoices, payments, purchases, refunds and the finance roadmap family are KEEP-ROADMAP by Max S1184.
- Relation-does-not-exist errors for tables absent from §C quarantine_set are not S1163 quarantine misses.

### §H.2 BREAKING predicates

- Drops or quarantines a table with rows, or weakens the lock-before-count invariant.
- Adds any app-startup path that can run P2/P3 one-shot migrations.
- Removes a KEEP-ROADMAP or OWNED-ELSEWHERE exclusion without a fresh Max ruling and unanimous Council gate.
- Drops a partition child independently from its parent family.

### §H.3 REVIEW predicates

- Changes classifier evidence rules or classification labels.
- Changes the P2/P3 migration target set.
- Changes mcp_safe mirror handling around schema moves/drops.
- Adds a runtime dependency to execute classification or migrations.
- Changes backup-health, Council, or Max checkpoint gates.

### §H.4 SAFE predicates

- Documentation update preserving all invariants.
- Adding a monitor query or log source that cannot mutate production.
- Test additions for classifier helpers or migration constants.
- Narrow bugfix to formatting of evidence output with no classification semantic change.

### §H.5 Boundary definitions

#### module

Immediate subdirectory of ai-market-backend's `app/` source root. `scripts/`, `alembic/`, `specs/`, and `tests/` are peer trees for this runbook, not product modules.

#### public contract

The production Postgres table/schema surface consumed by backend, koskadeux, Railway jobs, and `mcp_safe` read-only mirrors; Alembic revision IDs and downgrade paths are also operator contracts.

#### runtime dependency

Entries in backend runtime dependency files used by production services. Local-only operator CLIs and dev/test extras are not runtime dependencies unless a production job imports them.

#### config default

Values committed in backend config files. Environment variables such as `RUN_ONE_SHOT_S1163_P2`, `RUN_ONE_SHOT_S1163_P3`, and `SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS` are operator-supplied run controls, not config defaults.

### §H.6 Adjudication

If agents disagree on change class, the more restrictive class wins. Any dispute touching table ownership, roadmap status, or customer-data risk escalates to Max.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Refresh S1163 classification evidence using the production read-only DSN.
    expected_answers:
      - kind: tool_call
        tool: schema_classification_s1163_snapshot_then_classify
        argument_keys: [AUTHOR_DISPATCH_DATABASE_URL, SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS]
    weight: 0.0909090909
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: Execute the already-reviewed P2 quarantine migration.
    expected_answers:
      - kind: tool_call
        tool: alembic_upgrade
        argument_keys: [RUN_ONE_SHOT_S1163_P2, revision]
    weight: 0.0909090909
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Run the quarantine monitor on day two of the window.
    expected_answers:
      - kind: tool_call
        tool: psql_pg_stat_user_tables_and_log_checks
        argument_keys: [DATABASE_PUBLIC_URL, quarantine_set]
    weight: 0.0909090909
  - id: I-04
    type: isolate
    refs: [F-07]
    scenario: Railway logs show relation orders does not exist during the window.
    expected_answers:
      - kind: classification
        verdict: false_alarm_not_in_quarantine_set
    weight: 0.0909090909
  - id: I-05
    type: isolate
    refs: [F-06]
    scenario: Titan logs show UndefinedTable for quarantine.conversations.
    expected_answers:
      - kind: tool_call
        tool: cross_check_relation_against_quarantine_set
        argument_keys: [relation_name]
    weight: 0.0909090909
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: P3 aborts because a target table has one row.
    expected_answers:
      - kind: classification
        verdict: empty_only_invariant_blocks_drop
    weight: 0.0909090909
  - id: I-07
    type: repair
    refs: [G-05]
    scenario: A quarantined-table log hit is confirmed for processed_emails.
    expected_answers:
      - kind: tool_call
        tool: psql_alter_table_set_schema_public
        argument_keys: [table_name]
    weight: 0.0909090909
  - id: I-08
    type: repair
    refs: [G-04]
    scenario: P3 review finds an mcp_safe view still depends on a drop target.
    expected_answers:
      - kind: human_action
        verb: amend
        object: migration to handle mcp_safe mirror view before drop
        target: P3 Alembic revision
    weight: 0.0909090909
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A proposal drops agent_telemetry_2026_03 but keeps the parent and other children.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.0909090909
  - id: I-10
    type: ambiguous
    refs: [F-06, F-07]
    scenario: Logs contain relation-does-not-exist errors but the table name has not been extracted yet.
    expected_answers:
      - kind: tool_call
        tool: extract_relation_name_and_compare_to_quarantine_set
        argument_keys: [log_line, quarantine_set]
    weight: 0.0909090909
  - id: I-11
    type: evolve
    refs: [§H.3]
    scenario: A proposal changes the classifier so KEEP-ROADMAP tables require a new evidence field before being excluded from P3.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.0909090909
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1163
last_refresh_commit: 9a8fc1b9
last_refresh_date: 2026-07-12T10:57:00Z
owner_agent: vulcan
refresh_triggers:
  - P3 drop migration authored or executed
  - any quarantine-table miss or false-alarm class changes
  - Max changes KEEP-ROADMAP exclusions
  - classifier rules or evidence format changes
  - S1163 closes with final table count and account-teardown footprint re-derived
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-12T10:57:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1163 / 2026-07-12T10:57:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
