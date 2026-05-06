# ai-market-backend — Central Platform API

## What it is

FastAPI backend powering all of ai.market. Handles auth, listings, orders, payments, agents, CRM, fulfillment, and the allAI intelligence layer.

**Repo:** [aidotmarket/ai-market-backend](https://github.com/aidotmarket/ai-market-backend)
**Live:** `api.ai.market`
**Local path:** `/Users/max/Projects/ai-market/ai-market-backend`
**Hosting:** Railway (auto-deploy on push to main)

## Tech stack

Python 3.11, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL, Redis, Qdrant (vector search), APScheduler, Infisical (secrets).

## Deployment

Railway auto-deploys from `main`. On startup, runs `alembic upgrade head` before the app starts.

**Verify deploy:**
```sh
railway deployment list   # confirm SUCCESS
curl -s https://api.ai.market/health
```

**If deploy fails:** Check Railway build logs. Common issues: migration errors (see Alembic section), import errors, missing env vars.

## Key directories

| Path | Purpose |
|------|---------||
| `app/api/v1/endpoints/` | All HTTP endpoints (~90 files) |
| `app/api/v1/router.py` | Central router — all endpoint mounting with prefixes |
| `app/models/` | SQLAlchemy ORM models (~65 files) |
| `app/services/` | Business logic layer (~160 services) |
| `app/allai/` | allAI intelligence layer — agent host, service bus, agents |
| `app/core/` | Config, database, security, redis, LLM client |
| `app/schemas/` | Pydantic request/response schemas |
| `alembic/versions/` | Database migrations (162+) |

## Major endpoint groups

| Prefix | Endpoint file(s) | What it does |
|--------|-------------------|-------------|
| `/auth` | `auth.py`, `account_auth.py` | Login, signup, magic links, JWT |
| `/api/v1/listings` | `listings.py`, `public.py` | Create/edit/search listings |
| `/api/v1/orders` | `orders.py`, `checkout.py` | Order lifecycle, Stripe checkout |
| `/api/v1/deliveries` | `deliveries.py`, `fulfillment_download.py` | File delivery, download tokens |
| `/api/v1/stripe` | `stripe.py`, `stripe_connect.py` | Payments, seller onboarding |
| `/api/v1/allai` | `allai.py` | allAI brain, search, agent dispatch |
| `/api/v1/cp/agents` | `agent_control.py` | Agent control plane — fleet management |
| `/api/v1/crm` | `crm.py`, `crm_pipeline.py` | CRM contacts, organizations, pipeline |
| `/api/v1/allai/state` | `state.py` | Living State — generic entity CRUD, atomic writes, event ledger. Build-queue lifecycle decisions are NOT made here; see `/api/v1/allai/build-queue` for status transitions. |
| `/api/v1/allai/build-queue` | `bq_lifecycle.py` | Build-queue lifecycle transitions. `POST /bulk-transition` (registered first) and `POST /{key:path}/transition`. Auth: `X-Internal-API-Key`. Calls `BuildQueueLifecycleService` in-process; persists via `StateService.atomic_write` (single Postgres tx for entity + event ledger). |
| `/api/v1/marketing` | `marketing.py` | Campaign management, drafts |
| `/api/v1/finance` | (via `financeApi`) | Revenue, transactions, invoices |
| `/api/v1/internal` | `agent_health.py`, `health_internal.py` | Internal health checks (X-Internal-API-Key required) |
| `/webhooks` | `webhooks.py`, `gmail_webhook.py`, etc. | Stripe, Gmail, Drive, Railway webhooks |
| `/api/v1/search` | `search.py` | Listing search (Qdrant-backed) |
| `/api/v1/mcp` | `mcp.py`, `mcp_server.py` | MCP protocol endpoints |

## Notable services (`app/services/`)

| Service file | Class | Purpose |
|--------------|-------|---------|
| `bq_lifecycle_service.py` | `BuildQueueLifecycleService` | Build-queue lifecycle decisions (status transitions, gate progression, build-body invariants, pillar enum check). Wraps `StateService.atomic_write` for persistence; never mutates `StateEntity` directly. Bug-for-bug compatible with the Mac-side validators in `koskadeux-mcp/tools/state.py` at the time of the BQ-BACKEND-V2-PROXY-REAL-MCP-INTEGRATION-VERIFICATION cutover. |
| `business_summary_validator.py` | (pure-function module) | Validates the `body.summary` field on `kind=build` entities. Ported from `koskadeux-mcp/tools/state_validators/business_summary_validator.py` so backend can enforce summary requirements alongside the data, in-process. |
| `state_service.py` | `StateService` | Generic Living State CRUD, version locking, cache, event ledger. Owns `atomic_write` (single Postgres transaction for `entity_write` + `token_consume` + `event_append`). Build-queue specifics live in `bq_lifecycle_service.py`, which delegates here. |

## Database

PostgreSQL on Railway. Connection via `DATABASE_URL` (internal Railway hostname — not reachable externally).

**Alembic migrations:** All migrations must be idempotent using existence checks (`DO $$ BEGIN ... EXCEPTION WHEN duplicate_object`). Railway runs `alembic upgrade head` on every deploy.

**If a migration fails mid-execution:** The migration may have partially applied (tables created but `alembic_version` not stamped). Fix by making the migration idempotent and redeploying.

```sh
# Check current migration state
railway run alembic current
# Generate new migration
alembic revision --autogenerate -m "description"
```

## Configuration

Secrets in Infisical (`secrets.ai.market`, prod env). Key variables:

| Variable | Purpose |
|----------|--------|
| `DATABASE_URL` | PostgreSQL connection |
| `REDIS_URL` | Redis connection |
| `QDRANT_URL` + `QDRANT_API_KEY` | Vector search |
| `INTERNAL_API_KEY` | Internal endpoint auth |
| `STRIPE_SECRET_KEY` | Payments |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth |
| `GEMINI_API_KEY` | LLM calls (allAI brain) |

## Scheduled jobs (APScheduler)

Jobs defined in `app/core/scheduler.py`. Include: backup triggers, stale data cleanup, briefing generation, Gmail watch renewal, deploy monitoring.

## Troubleshooting

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| 500 on an endpoint | `railway logs -d -n 50` — look for traceback | Fix code, push to main |
| Migration failure on deploy | Railway build log shows Alembic error | Make migration idempotent, redeploy |
| Redis connection errors | Check `REDIS_URL` in Infisical | Verify Railway Redis service is running |
| Agent health endpoint 401 | Missing `X-Internal-API-Key` header | Check ops dashboard API config matches `INTERNAL_API_KEY` |
| Qdrant search failures | Check Qdrant service in Railway | Verify `QDRANT_URL` and collection exists |
| Stripe webhook failures | Check webhook signing secret | Verify `STRIPE_WEBHOOK_SECRET` in Infisical |
| Customer sees `/login?error=oauth_failed` after Google/GitHub consent | Sign-up path failure — check `app/auth/oauth.py:408` `ensure_user_crm_identity` is NOT raising and rolling back the auth transaction | See `auth-signup-flow.md` for full architecture, known issues, diagnostic procedure, and backfill |

---

*Created: S363 (2026-04-01)*

## Alembic + asyncpg Gotchas (Railway)

Railway runs Alembic via asyncpg (async PostgreSQL driver). This introduces constraints that don't exist with psycopg2 (sync):

### 1. No multi-statement prepared statements
asyncpg rejects `op.execute()` calls containing multiple SQL statements separated by semicolons.

**Fails:**
```python
op.execute("CREATE TABLE ...; INSERT INTO ...; UPDATE ...;")
```

**Works:**
```python
op.execute("CREATE TABLE ...")
op.execute("INSERT INTO ...")
op.execute("UPDATE ...")
```

### 2. Temp tables with ON COMMIT DROP are destroyed between op.execute() calls
asyncpg auto-commits between separate `op.execute()` calls even under Alembic's transactional DDL. This means `CREATE TEMP TABLE ... ON COMMIT DROP` tables disappear before the next statement can use them.

**Fails:**
```python
op.execute("CREATE TEMP TABLE tmp ... ON COMMIT DROP AS SELECT ...")
op.execute("INSERT INTO target SELECT ... FROM tmp")  # tmp is gone
```

**Works — PL/pgSQL DO block (recommended for multi-step data operations):**
```python
op.execute("""
    DO $$
    DECLARE rec RECORD; new_id UUID;
    BEGIN
        FOR rec IN SELECT ... FROM source WHERE ...
        LOOP
            INSERT INTO parent (...) VALUES (...) RETURNING id INTO new_id;
            INSERT INTO child (parent_id, ...) VALUES (new_id, ...);
        END LOOP;
    END $$
""")
```

**Works — CTE (for single-statement operations):**
```python
op.execute("""
    WITH source AS (SELECT ... FROM ...)
    INSERT INTO target SELECT ... FROM source
    ON CONFLICT DO NOTHING
""")
```

### 3. Migration already applied = won't re-run
If a migration runs "successfully" but has no effect (e.g., temp table was empty due to the ON COMMIT DROP issue), Alembic stamps it as applied. You must create a **new revision** to fix it — you can't just edit the existing one.

### 4. Unique constraint conflicts on backfills
Always check for pre-existing data from other creation paths (admin endpoints, CRM backfills, manual inserts). Use `ON CONFLICT DO NOTHING` or `NOT EXISTS` subqueries. For partial unique indexes (like `ux_crm_people_email_active`), prefer `NOT EXISTS` over `ON CONFLICT ON CONSTRAINT`.

### Summary: Safe migration pattern for asyncpg
```python
def upgrade() -> None:
    # Each op.execute() = one statement
    # Use PL/pgSQL DO blocks for correlated multi-table inserts
    # Use CTEs for single-statement derivations
    # Always ON CONFLICT / NOT EXISTS for idempotency
    # Never use temp tables across op.execute() boundaries
    # Never put multiple statements in one op.execute()
```

*Discovered in S427. See also: alembic/versions/20260410_002_backfill_parties_v2.py for a working example.*
