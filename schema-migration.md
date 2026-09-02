---
title: Schema Migration Runbook
owner: unassigned
last_verified: '2026-08-28'
aliases: []
error_signatures: []
---

# Schema Migration Runbook

## S.1 Purpose
Alembic-based database schema migration procedures across ai-market-backend, koskadeux-mcp (Living State database), and any other service with versioned schema. Owned by **BQ-PROCESS-BUILD-QUEUE-INTEGRITY-S612** (P1, delegated migration-discipline section). Filed S612 per DS mandate that the runbook set was missing dedicated schema-migration coverage.

## S.2 Pre-migration checklist
Before authoring any new Alembic revision:
1. `alembic heads` MUST return exactly 1 head on the target branch.
2. If multiple heads: author a merge revision FIRST. Do not author new revisions on a multi-head tree.
3. Check `alembic current` against production HEAD via Railway deploy log.

## S.3 Authoring a new revision
1. Branch off main: `git checkout -b feat/<schema-change-slug>`.
2. `alembic revision -m "<short_snake_case_description>"` (auto-generates revision ID).
3. Edit `upgrade()` AND `downgrade()` functions. Both REQUIRED.
4. **Forward test**: `alembic upgrade head` on a fresh local DB. Confirm no errors.
5. **Backward test**: `alembic downgrade -1` from the new head. Confirm clean reversal.
6. **Forward-forward test**: re-run `alembic upgrade head`. Confirm clean re-application.
7. If any test fails, revise the revision script BEFORE submitting PR.

## S.4 Merge revisions
When two branches each add a revision on top of the same parent:
1. Local: `alembic merge -m "merge <branch_a> + <branch_b>" <revision_a> <revision_b>`.
2. Test forward + backward against the merge head.
3. PR the merge alongside the second-merged branch.

## S.5 Production deploy alignment
- Railway runs `scripts/run_alembic_startup.sh` via the Dockerfile command on
  every backend deploy. When `AUTHOR_DISPATCH_DATABASE_URL` is present, the
  helper uses that schema-owner DSN as the Alembic child process's
  `DATABASE_URL`. The application then starts with the original restricted
  `DATABASE_URL` from the container environment. The pre-existing author
  variable remains visible in that environment; this boundary prevents the app
  database engine from selecting it, rather than removing the secret. Local and
  staging environments without the author DSN fall back to `DATABASE_URL`.
- The production application role is intentionally DDL-denied. Do not grant it
  `CREATE` on `public` to make a migration pass. Before relying on the split,
  verify only the presence of both Railway variable names (never print their
  values), and use the established Infisical author DSN for read-only catalog
  checks of the two roles.
- After merge to main, watch the Railway deploy log for the alembic upgrade step.
- If Alembic fails on production, first confirm Railway retained the previous
  successful deployment. Do not manually edit production schema. Revert the
  feature PR when its migration bytes are defective. When the migration bytes
  are verified and the failure is instead the execution role or transport,
  land the smallest independently reviewed deploy-path repair and let Alembic
  apply the unchanged migration on the next deploy.

## S.6 Schema-only PR rules
- Schema-only PRs (no app code changes) require MP review-mode approval.
- Code-with-schema PRs require both MP + AG (or DS) reviewer approval.
- The `alembic_version` table column width has been widened (S576): revision IDs can now exceed 32 chars. Tracked under BQ-ALEMBIC-VERSION-NUM-WIDEN-S576 (product backend BQ, NOT consolidated under S612 per AG mandate).

## When it breaks
- **Multi-heads on main**: must merge before next revision lands.
- **Hand-rolled head detection lies**: never infer the head set by grepping/parsing `revision`/`down_revision` out of the version files — merge revisions use a multi-line tuple `down_revision`, which single-line parsers miss, producing false multi-head counts (and false “all clear” single-head reads). Always run the real `alembic heads`. To run it locally without a DB (the `heads` command reads the script tree only, no connection needed) but past the app `Settings` import, export dummy env first: `export SECRET_KEY=$(openssl rand -hex 32) DATABASE_URL=postgresql+asyncpg://u:p@localhost:5432/dummy ENVIRONMENT=development`.
- **A migration metadata test names an old merge as the predecessor**: run `alembic heads` before changing migration files. A historical revision can legitimately point to its branch predecessor while a later merge collapses that branch into the single current lineage. If the real graph has one head, inspect the migration and Git history and correct the stale test expectation; do not rewrite an applied migration merely to satisfy the test.
- **Forward test passes but backward fails**: missing `downgrade()` coverage. Common with constraint additions where reverting requires explicit drop.
- **Production diverged from local**: someone hand-applied schema. Pull latest, compare via `alembic current` on production, reconcile via merge revision.
- **Long-running migrations on production**: Railway deploy timeouts. Pre-deploy the schema change in a separate maintenance-window PR; ship code that uses it in a follow-up PR.
- **`permission denied for schema public` from the application role**: confirm
  the failed deployment never replaced the prior successful one, then verify
  that `scripts/run_alembic_startup.sh` is present and that the production
  service has both `AUTHOR_DISPATCH_DATABASE_URL` and `DATABASE_URL`. The
  author role must have `CREATE` on `public`; the application role must not.
  Repair the migration connection boundary and redeploy. Never grant DDL to the
  application role and never apply the migration body by hand.

## S.7a S1163 schema-classification tooling (operator reference)

The BQ-DB-SCHEMA-RATIONALIZATION-S1163 classifier lives at `ai-market-backend/scripts/schema_classification_s1163.py` and feeds the pre-migration evidence chain for the quarantine/drop migrations. Operator commands (run from the backend repo root; `.venv/bin/python` has psycopg2):

```bash
export INFISICAL_API_URL=$(cat ~/.config/infisical/api-domain)
export INFISICAL_TOKEN=$(cat ~/.config/infisical/sysadmin-token)
DSN=$(infisical secrets get AUTHOR_DISPATCH_DATABASE_URL --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c --env prod --plain | grep "^postgres" | tail -1)
AUTHOR_DISPATCH_DATABASE_URL="$DSN" .venv/bin/python scripts/schema_classification_s1163.py snapshot
AUTHOR_DISPATCH_DATABASE_URL="$DSN" SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS=<days> .venv/bin/python scripts/schema_classification_s1163.py classify
```

- Connections are session read-only with statement timeouts (`connect_readonly`); never pass the DSN on the command line.
- `SCHEMA_CLASSIFICATION_MIN_WINDOW_DAYS` (added S1184, merged f1d875a9 under Max waiver 66cb2134) overrides the default 14-day minimum write-delta window; invalid or non-positive values fail loudly. The manifest records the effective `minimum_days`; classify emits `FINAL_ELIGIBLE` only when the snapshot window meets it and `pg_stat_database.stats_reset` is unchanged between snapshots.
- Evidence outputs: `specs/evidence/schema-classification-s1163/snapshot-N.json` and `specs/evidence/schema-classification-s1163.{json,md}` — commit them to backend main.
- The full worker-runnable operator runbook for the S1163 quarantine/drop remainder is a queued deliverable that will absorb this section; until it lands, this plus the Gate-1 spec (`specs/BQ-DB-SCHEMA-RATIONALIZATION-S1163-GATE1.md`) are the operating references.

## S.7b Full-history bootstrap verification (T-2026-000076 collider guards)

Replaying the whole migration history onto an empty database used to crash on "collider" migrations, because production carries a regenerated baseline that already owns many objects. The B1-B4 slices convert raw DDL into schema-aware guarded DDL using the helpers in `ai-market-backend/alembic_b1_guard.py` (`ensure_table`/`ensure_column`/`ensure_constraint`/`ensure_index`/`ensure_trigger`/`ensure_enum`/`ensure_function`, with `drop_if_owned` on downgrade, backed by the `alembic_b1_object_ownership` table). A helper accepts an existing object only when its catalog definition is equivalent; otherwise it raises `STOP_DEPLOYMENT`.

**Two replay tests are required, and the first one alone is not sufficient.** Last executed against PostgreSQL 17 in S1533.

1. **Empty-database replay** proves the migrations still work from nothing. It exercises only the fresh-create path.

```bash
docker run -d --name <slug>-pg17 -p 127.0.0.1:0:5432 -e POSTGRES_PASSWORD=postgres postgres:17-alpine
export SECRET_KEY=$(openssl rand -hex 32) ENVIRONMENT=development RUN_ONE_SHOT_S1163_P2=1
DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:<port>/<db>" .venv/bin/alembic upgrade head
```

2. **Baseline collision replay** is the test that actually matters, because every `compatible_definitions` / `compatible_variants` branch fires only when the object already exists. An empty database never reaches those branches, so a passing empty replay tells you nothing about the guards.

```bash
psql ... -d <db> -f specs/bq-alembic-migration-005-fixtures/prod_advanced_schema_2026-04-26.sql
psql ... -d <db> -c "UPDATE alembic_version SET version_num='000_initial';"   # rewind so every collider replays
DATABASE_URL=... .venv/bin/alembic upgrade head
```

Pass criteria: exit 0, zero `STOP_DEPLOYMENT` occurrences in the log, exactly one `alembic heads`, and an idempotent immediate re-run applying zero migrations.

Test downgrade ownership at the revision or smallest contiguous slice changed by the patch: an object created by that revision is removed and restored, while an equivalent baseline-owned object survives. Do not use an unrelated later revision as the downgrade target; a defect there can fail first and prove nothing about the patch under review. Record such a failure against the owning revision and keep the candidate result explicit.

**Keep the guard in one place.** New collision classes belong in `alembic_b1_guard.py`; migrations should declare expected definitions and call that shared implementation. Do not add migration-local existence checks or copy catalog queries between revisions. A matching existing object is a logged no-op, a mismatched object raises `STOP_DEPLOYMENT`, and downgrade removes only objects recorded in `alembic_b1_object_ownership` for that revision.

**Long revision IDs.** The first long-ID entry point on every supported replay path must call the shared `ensure_alembic_version_width()` before any other migration work, so Alembic can record that revision. Test both a fresh history and the production-shaped resume point with `alembic_version.version_num` constrained to `varchar(32)`; both must finish with width at least 64. Do not add a second width helper to an individual migration.

**`RUN_ONE_SHOT_S1163_P2=1` is mandatory.** `20260711_001_s1163_p2_quarantine_one_shot` deliberately refuses to run unattended, so a clean bootstrap is never a bare `alembic upgrade head`.

> **CORRECTION, S1482 (2026-08-08).** This paragraph previously ended "Production is unaffected because the revision is already applied there." That was FALSE and is retracted. `alembic_version` records the revision as applied, but its body never executed: all 21 tables it moves (`ALTER TABLE quarantine.X SET SCHEMA public`) are still resident in the `quarantine` schema on live production, a 21/21 exact match against the migration's own list. Verified read-only against production Postgres 2026-08-08.
>
> The general lesson is larger than this migration: **on `ai-market-backend`, `alembic_version` is not evidence that a migration ran.** A second, unrelated revision (`s103_canonical_transaction`) is likewise marked applied while the function it creates unconditionally — `sync_order_status_to_transaction` — has zero rows in `pg_proc`. Do not reason from "alembic says X is applied." Check the artifact.
>
> Consequences found the same day: `orders`, `transactions` and `transaction_events` are absent from production while `000_initial` creates all three, 21 foreign-key constraints across 18 tables were destroyed with them, and no purchase has ever completed. Tracked as T-2026-000578. Full drift inventory: `/Users/max/koskadeux-state/s1482-drift/`.

**Reviewing a collider-guard change.** Dispatch one immutable review package containing the complete patch, exact base/head/tree SHAs, validation results, and a pinned read-only checkout. Pin the provenance anchors alongside the diff — `alembic/versions/000_initial.py` (the regenerated baseline), whichever later migration creates the advanced shape, the remediation manifest, and the Chunk E fixture/checksum. Do not split the decision into narrow inline-diff reviews: a reviewer cannot distinguish a legitimate compatible definition from a guessed one without those anchors.

## S.8 Related runbooks
- `runbooks/activation-verification.md` — Railway deploy verification path.
- `runbooks/build-queue-lifecycle.md` — BQ entity lifecycle around schema changes.

## S.9 Owner
This runbook is owned by **BQ-PROCESS-BUILD-QUEUE-INTEGRITY-S612** (P1, delegated section).
Revisions to this page land in `aidotmarket/runbooks`; database implementation lands in `aidotmarket/ai-market-backend`. Payment- or customer-data-adjacent migration changes require the complete CC/GLM/DeepSeek Council review before merge or deployment.
