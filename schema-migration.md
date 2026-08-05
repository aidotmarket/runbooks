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
- Railway runs `alembic upgrade head` via Dockerfile CMD on every deploy.
- After merge to main, watch the Railway deploy log for the alembic upgrade step.
- If alembic fails on production: rollback the Railway deploy + revert the PR. Do NOT manually edit production schema.

## S.6 Schema-only PR rules
- Schema-only PRs (no app code changes) require MP review-mode approval.
- Code-with-schema PRs require both MP + AG (or DS) reviewer approval.
- The `alembic_version` table column width has been widened (S576): revision IDs can now exceed 32 chars. Tracked under BQ-ALEMBIC-VERSION-NUM-WIDEN-S576 (product backend BQ, NOT consolidated under S612 per AG mandate).

## S.7 Common failure modes
- **Multi-heads on main**: must merge before next revision lands.
- **Hand-rolled head detection lies**: never infer the head set by grepping/parsing `revision`/`down_revision` out of the version files — merge revisions use a multi-line tuple `down_revision`, which single-line parsers miss, producing false multi-head counts (and false “all clear” single-head reads). Always run the real `alembic heads`. To run it locally without a DB (the `heads` command reads the script tree only, no connection needed) but past the app `Settings` import, export dummy env first: `export SECRET_KEY=$(openssl rand -hex 32) DATABASE_URL=postgresql+asyncpg://u:p@localhost:5432/dummy ENVIRONMENT=development`.
- **Forward test passes but backward fails**: missing `downgrade()` coverage. Common with constraint additions where reverting requires explicit drop.
- **Production diverged from local**: someone hand-applied schema. Pull latest, compare via `alembic current` on production, reconcile via merge revision.
- **Long-running migrations on production**: Railway deploy timeouts. Pre-deploy the schema change in a separate maintenance-window PR; ship code that uses it in a follow-up PR.

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

**Two tests are required, and the first one alone is not sufficient.** Verified S1440.

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

Pass criteria: exit 0, zero `STOP_DEPLOYMENT` occurrences in the log, exactly one `alembic heads`, an idempotent immediate re-run applying zero migrations, and `downgrade -N` then re-upgrade leaving the public table count unchanged.

**`RUN_ONE_SHOT_S1163_P2=1` is mandatory.** `20260711_001_s1163_p2_quarantine_one_shot` deliberately refuses to run unattended, so a clean bootstrap is never a bare `alembic upgrade head`. Production is unaffected because the revision is already applied there.

**Reviewing a collider-guard change.** These diffs are large (B4+ was 50 files, ~341KB) and exceed the Council reviewers' inline diff cap in both the GLM and CC paths; a whole-diff dispatch is rejected with `cc_review_diff_truncated`. When scoping a review, pin the provenance anchors alongside the diff — `alembic/versions/000_initial.py` (the regenerated baseline), plus whichever later migration creates the "advanced" shape, plus the Chunk E fixture. Without them a reviewer cannot tell a legitimate baseline-shape `compatible_definition` from a hand-guessed one, and will return confident, wrong mandates. In S1440 four of five Gate 3 mandates were false positives for exactly this reason.

## S.8 Related runbooks
- `runbooks/activation-verification.md` — Railway deploy verification path.
- `runbooks/build-queue-lifecycle.md` — BQ entity lifecycle around schema changes.

## S.9 Owner
This runbook is owned by **BQ-PROCESS-BUILD-QUEUE-INTEGRITY-S612** (P1, delegated section).
Revisions land as PRs against koskadeux-mcp main; require MP review-mode approval (data-correctness criticality).
