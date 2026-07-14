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

## Seller onboarding enforcement & dashboard access

Dashboard READ endpoints must load for a seller still mid-onboarding (`onboarding_completed=false`), while writes/payout stay gated. Two flexible-auth dependencies live in `listings.py`:

- `get_current_user_flexible` — authenticates AND enforces onboarding (raises 403 `Onboarding required`). Use for writes, listing-create, payout, and gated actions.
- `get_current_user_flexible_no_onboarding` — authenticates but skips the onboarding gate. Use for **owner-scoped dashboard READS only** — the handler still filters by the authenticated user's id, so there is no cross-account exposure.

Owner-scoped dashboard reads currently on the non-enforcing dependency: seller `/stats /financials /orders /pending`; inquiries `/mine /stats`; conversations `/mine /stats`; orders `/mine /stats`; listings `/mine`. If a new "My X" dashboard list/stats read 403s for a partial-onboarding seller, switch that route's dependency to `get_current_user_flexible_no_onboarding` and add a test asserting 200-on-read plus still-403-on-write. Reviewer note: dropping the onboarding gate on these owner-scoped reads is auth-scope — it earns a unanimous Council Gate-3 (reviewer != builder).

**Stripe Connect return URLs:** the hosted-onboarding AccountLink in `stripe_connect.py` must return to the real frontend route `/dashboard/stripe-return` (refresh → `/dashboard/stripe-return?abandoned=1`, which that page reads as the abandoned/incomplete case). Do NOT use bare `/settings` — there is no `/settings` route (settings lives at `/dashboard/settings`), so it 404s and dead-ends the seller right after connecting.

## Notable services (`app/services/`)

| Service file | Class | Purpose |
|--------------|-------|---------|
| `bq_lifecycle_service.py` | `BuildQueueLifecycleService` | Build-queue lifecycle decisions (status transitions, gate progression, build-body invariants, pillar enum check). Wraps `StateService.atomic_write` for persistence; never mutates `StateEntity` directly. Bug-for-bug compatible with the Mac-side validators in `koskadeux-mcp/tools/state.py` at the time of the BQ-BACKEND-V2-PROXY-REAL-MCP-INTEGRATION-VERIFICATION cutover. |
| `business_summary_validator.py` | (pure-function module) | Validates the `body.summary` field on `kind=build` entities. Ported from `koskadeux-mcp/tools/state_validators/business_summary_validator.py` so backend can enforce summary requirements alongside the data, in-process. |
| `state_service.py` | `StateService` | Generic Living State CRUD, version locking, cache, event ledger. Owns `atomic_write` (single Postgres transaction for `entity_write` + `token_consume` + `event_append`). Build-queue specifics live in `bq_lifecycle_service.py`, which delegates here. |

## Database

PostgreSQL on Railway. The app connects via `DATABASE_URL` (internal Railway hostname `postgres.railway.internal`, not reachable externally). To reach production from an external host (Titan-1, the laptop), use the public TCP proxy exposed as `DATABASE_PUBLIC_URL` on the **Postgres** service — see "Customer data: where it lives, and how to delete or reset an account" below for the exact connect snippet.

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

## Rate limiting and the caller's IP address (trust boundary)

`app/core/rate_limiter.py` (`AuthRateLimiter`, `LoginRateLimiter`) throttles by caller. Endpoints using it include the E2E preflight route, beta signup, partner inquiry, serial generation, login and magic-link.

**`app/core/request_ip.py` (`resolve_client_ip`) is the only caller-IP source for backend consumers. Never parse `request.client.host` or forwarding headers directly in a consumer.**

The trust rule, established by direct raw-chain observation and a two-caller production proof in T-2026-000244 on 2026-07-13 (do not re-derive it from documentation — Railway's behaviour is not what the header names imply):

| Signal | Trust | Rule |
|--------|-------|------|
| Socket peer (`request.client.host`) is INTERNAL/CGNAT | Trusted proxy present | Parse `X-Forwarded-For` under strict bounds, then take the LEFTMOST entry as the actual caller. Production chain observed 2026-07-13: `[actual caller, Railway public edge]`. |
| Socket peer (`request.client.host`) is PUBLIC | Direct connection | The caller bypassed the trusted proxy; ignore all forwarding headers and use the public peer directly. |
| Chain missing, malformed, overlong, or otherwise fails strict parsing | Invalid | Fall back to the explicit `"unknown"` key. Rate-limit/security keys share that bucket; source-IP allowlists fail closed; nullable audit/legal persistence stores NULL where the consumer documents that behavior. |
| `X-Envoy-External-Address` | Untrusted, unused | Caller-supplied and passed through unmodified by Railway's edge; never consulted. |

History: probing production on 2026-07-12 inferred the RIGHTMOST `X-Forwarded-For` hop as trusted and the leftmost entry as attacker-controlled. T-2026-000244 (2026-07-13) superseded that inference with direct observation of the raw header chain plus a two-caller production test, establishing leftmost-after-strict-parsing as the correct rule instead.

Verification standard: for a configured limit N, caller A must 429 on request N+1 (accounting for endpoint-specific semantics), and — once A is exhausted — an unrelated caller B must still retain its own full budget. A single observed 429 is not sufficient proof that a limit binds correctly.

T-2026-000240 centralized all active consumers on this contract; it did not change any numeric thresholds, since current telemetry did not justify tuning them.

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

## API error mapping — DB constraint violations → HTTP status

**Principle:** a violated DB constraint is a client / business-rule error, not a server fault. Any endpoint that writes under constraints MUST translate the resulting SQLAlchemy `IntegrityError` into a 4xx with a clear `detail` — never let it bubble to a raw 500. Detect the specific constraint via the asyncpg structured attribute `exc.orig.constraint_name` (SQLAlchemy wraps asyncpg's `UniqueViolationError` / `CheckViolationError` as `IntegrityError`), with a substring fallback on `str(exc.orig)`.

**Worked example — `POST /api/v1/allai/peer-messages`** (`app/api/v1/endpoints/peer_messages.py`, `send_peer_message`):

| Constraint | Type | Meaning | HTTP status | Notes |
|---|---|---|---|---|
| `uq_peer_messages_claim_ref_entity_utc_day` | UNIQUE (partial) | one claim per (kind, ref_entity, UTC-day) | 200 idempotent (same-instance re-claim) / 409 conflict (cross-instance) | translated in the `IntegrityError` handler |
| `ck_peer_messages_claim_ref_entity_required` | CHECK | `kind <> 'claim' OR ref_entity IS NOT NULL` — a claim must carry a ref_entity | 422 | reachable: a `claim` sent with null `ref_entity` |
| `ck_peer_messages_ack_required_for_request_alert` | CHECK | `(kind NOT IN ('request','alert')) OR requires_ack` | 422 (generic) | UNREACHABLE via this handler — it forces `requires_ack=True` for request/alert kinds; mapped generically for future-proofing only |

**Implementation rule:** match the `ck_peer_messages_` constraint-name prefix *generically* (one branch) so any future CHECK on this table returns 422, not 500. Only genuinely-unknown `IntegrityError`s re-raise.

**Operator note:** the peer bus enforces these at the DB layer. If a `peer_msg_send` claim fails, the cause is almost always a missing `ref_entity` — always send claims WITH a `ref_entity` (see `peer-instance-discipline.md`).

**History:** before the S960 fix the CHECK path surfaced as a raw 500 (the handler only translated the unique-index violation). The 422 mapping shipped to `ai-market-backend` main in commit `c6b34401` (S960).

## Customer data: where it lives, and how to delete or reset an account

All customer and account data lives in the **PostgreSQL `Postgres` service** of the `ai-market` Railway project (production environment). That is the single source of truth for customer identity. Qdrant and Redis hold only derived or transient data, and raw seller data never leaves the seller's own AIM Data install.

**Connecting to production Postgres from an external host (Titan-1, laptop):** the internal `DATABASE_URL` host (`postgres.railway.internal`) is not reachable externally. Use the public TCP proxy, exposed as `DATABASE_PUBLIC_URL` on the **Postgres** service:

```sh
PUB=$(railway variables -s Postgres --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["DATABASE_PUBLIC_URL"])')
psql "$PUB" -c '\conninfo'
```

> **Known drift (observed 2026-06-11, S823):** the `DATABASE_PUBLIC_URL` variable on the Postgres service can carry a **stale password** after a credential rotation (URL password != current `POSTGRES_PASSWORD`), failing with `password authentication failed`. If that happens, compose the connection from parts instead:
```bash
eval $(railway variables -s Postgres --json | python3 -c '
import json,sys,shlex
v=json.load(sys.stdin)
print("export PGPASSWORD="+shlex.quote(v["POSTGRES_PASSWORD"]))
print("export PGHOST="+shlex.quote(v["RAILWAY_TCP_PROXY_DOMAIN"]))
print("export PGPORT="+shlex.quote(str(v["RAILWAY_TCP_PROXY_PORT"])))
print("export PGUSER="+shlex.quote(v["PGUSER"]))
print("export PGDATABASE="+shlex.quote(v["POSTGRES_DB"]))
')
psql -c '\conninfo'


Same credentials and database as the internal URL; only host and port differ. Never echo the full URL (it carries the password) — print host only when logging.

**The account row:** a customer is one row in `users` (`id uuid`, `email`, `role` — a Postgres `userrole` enum with values `buyer` / `seller` / `admin`):

```sh
psql "$PUB" -c "SELECT id, email, role, created_at FROM users WHERE email='<email>';"
```

**Where the data is spread:** roughly 80 tables carry a foreign key to `users`, most empty for a typical seller. Delete rules differ per table, which is why a blind `DELETE FROM users` either fails or orphans rows:

- `ON DELETE CASCADE` (removed automatically with the user): `listings`, `auth_sessions`, `notifications`, `allai_preferences`, `wallets`, `user_preferences`, `notification_preferences`, `conversations`, `inquiries`, `ratings`, `credit_reservations`, `crm_user_roles`, `organization_memberships`, `seller_inquiry_preferences`, and similar.
- `ON DELETE NO ACTION` (blocks the delete; must be cleared first when rows exist): `vz_installs.seller_id`, `buyer_profiles.user_id`, `seller_profiles.user_id`, `crm_people.user_id`, `orders`, `transactions`, `purchases`, `invoices`, `payments`, `api_keys`, `api_credits`, `credit_ledger`, `publish_operations`, and others.
- `ON DELETE SET NULL`: most `crm_*` audit columns (`created_by_user_id`, `*_by`), which are left in place and simply de-attributed.

**Probe exactly which child tables hold rows for a user** (read-only — run before deleting):

```sql
DO $$
DECLARE r RECORD; n BIGINT; uid uuid := '<user-uuid>';
BEGIN
  FOR r IN SELECT tc.table_name t, kcu.column_name c
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name=ccu.constraint_name
    WHERE tc.constraint_type='FOREIGN KEY' AND ccu.table_name='users'
  LOOP
    EXECUTE format('SELECT count(*) FROM %I WHERE %I = $1', r.t, r.c) INTO n USING uid;
    IF n>0 THEN RAISE NOTICE '%.% = %', r.t, r.c, n; END IF;
  END LOOP;
END $$;
```

**Delete or reset an account:** clear the non-cascading children the probe reported, then the user; cascades remove the rest. Run it as one transaction with `ON_ERROR_STOP` so an unexpected dependency aborts cleanly instead of partially deleting:

```sql
BEGIN;
DELETE FROM vz_installs     WHERE seller_id='<uuid>';
DELETE FROM buyer_profiles  WHERE user_id ='<uuid>';
DELETE FROM seller_profiles WHERE user_id ='<uuid>';
DELETE FROM crm_people      WHERE user_id ='<uuid>';
-- add any other NO ACTION tables the probe reported (orders/transactions/etc. for accounts that traded)
DELETE FROM users           WHERE id      ='<uuid>';
SELECT count(*) FROM users WHERE email='<email>';   -- expect 0
COMMIT;
```

Invoke with `psql -v ON_ERROR_STOP=on -f reset.sql`. After this the email is free to register from scratch. For a fresh test seller that only listed (no buyers or orders), the non-cascading set is typically just `vz_installs`, `buyer_profiles`, and `crm_people`.

> Worked example (S773): resetting `max@kisa.cat` (a seller that had published) cleared 1 `vz_installs`, 1 `buyer_profiles`, 1 `crm_people`, then cascaded 2 `listings`, 6 `auth_sessions`, 2 `notifications`, and 1 `allai_preferences` when the user row was deleted.


---

*Created: S363 (2026-04-01)*
*Customer data + reset procedure added: S773 (2026-06-05)*

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
