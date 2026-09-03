---
title: ai-market-backend — Central Platform API
owner: unassigned
last_verified: '2026-08-27'
aliases:
- Railway backend deployment
- FastAPI production API
error_signatures: []
---

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

**Railway CLI targeting (S1654/S1655):** the repo checkout at `/Users/max/Projects/ai-market/ai-market-backend` is linked to the `verify-s1648` environment, not production. Every Railway command against production must pass `-e production -s ai-market-backend` explicitly; a bare `railway variables` or `railway deployment list` silently answers for the wrong environment. Postgres reads use `-e production -s Postgres` (see the connect snippet under "Customer data").

**Verify deploy:**
```sh
railway deployment list -e production -s ai-market-backend   # confirm SUCCESS
railway variables -e production -s ai-market-backend --json   # config evidence; never echo values into a package, export keys only
curl -s https://api.ai.market/health
```

**Flag flips redeploy:** `railway variables -e production -s ai-market-backend --set NAME=value` triggers a full redeploy (~3 min). Poll `deployment list` until the newest row is SUCCESS before probing.

**Running the test suite locally:** use the repo venv interpreter, not system python: `/Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python -m pytest <paths>`. System python lacks the backend dependency set.

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
| `/api/v1/connect` | `stripe_connect.py` | Supported Standard Connect seller onboarding and status |
| `/api/v1/webhooks/stripe` | `webhooks.py` | Central Stripe events for Connect, checkout, payments, disputes, and payouts |
| `/api/v1/allai` | `allai.py` | allAI brain, search, agent dispatch |
| `/api/v1/cp/agents` | `agent_control.py` | Agent control plane — fleet management |
| `/api/v1/crm` | `crm.py`, `crm_pipeline.py` | CRM contacts, organizations, pipeline |
| `/api/v1/allai/state` | `state.py` | Living State — generic entity CRUD, atomic writes, event ledger. Build-queue lifecycle decisions are NOT made here; see `/api/v1/allai/build-queue` for status transitions. |
| `/api/v1/allai/build-queue` | `bq_lifecycle.py` | Build-queue lifecycle transitions. `POST /bulk-transition` (registered first) and `POST /{key:path}/transition`. Auth: `X-Internal-API-Key`. Calls `BuildQueueLifecycleService` in-process; persists via `StateService.atomic_write` (single Postgres tx for entity + event ledger). |
| `/api/v1/marketing` | `marketing.py` | Campaign management, drafts |
| `/api/v1/finance` | (via `financeApi`) | Revenue, transactions, invoices |
| `/api/v1/internal` | `agent_health.py`, `health_internal.py` | Internal health checks (X-Internal-API-Key required) |
| `/webhooks` | `webhooks.py`, `gmail_webhook.py`, etc. | Stripe, Gmail, Drive, Railway webhooks |
| `/api/v1/search` | `search.py` | Public listing search (PostgreSQL lexical ranking plus Qdrant semantic ranking) |
| `/api/v1/mcp` | `mcp.py`, `mcp_server.py` | MCP protocol endpoints |

## Seller capability enforcement & dashboard access

**RETIRED 2026-08-09, T-2026-000565 C2-B, merged to backend main at `644ee1d64`.** Onboarding enforcement no longer exists anywhere in `app/`. This section previously described two flexible-auth dependencies and an `onboarding_completed` gate; both enforcers and the `get_current_user_flexible_no_onboarding` helper are deleted. Do not reinstate them and do not look for them.

Why it went: the gate was a blanket 403 keyed on `onboarding_completed`, and the wizard that could clear that flag had already been deleted from the frontend. Every Google sign-up was therefore trapped permanently — 15 real users, newest 2026-08-07, one of whom reached live Stripe payouts and still could not open his dashboard. The gate was a product-completeness check wearing a security check's clothes; all three Gate 3 reviewers said so independently.

**What replaced it.** There is now ONE flexible-auth dependency, `listings.get_current_user_flexible`, and it AUTHENTICATES ONLY. Authorization is per surface:

- **Seller writes** assert capability explicitly: `await assert_user_capability(user, db, "seller")`. Eight call sites — `ai_discovery`, `disclosure_snapshots`, `disputes.seller_respond`, `orders.deliver_order`, `orders.revoke_access`, `ratings.respond_to_rating`, `inquiries.seller_respond`, `transaction_actions.deliver_transaction` — plus the pre-existing assertions in `listings.py` and `seller.py`.
- **Role-gated routes** use the `require_capability(...)` dependency: `profiles` `/seller/me` GET and PATCH at threshold `provisioning`; `vz_publish` confirm/rotate-key/revoke at `active`.
- **Owner-scoped dashboard reads** need no capability at all. The handler filters by the authenticated user's id, which is the boundary. Seller `/stats /financials /orders /pending`; inquiries `/mine /stats`; conversations `/mine /stats`; orders `/mine /stats`; listings `/mine`.
- **Conversations are capability-neutral by design.** Participant/owner scope is the boundary (`InquiryService.respond_to_inquiry` → 403 "Not authorized"). A partially-provisioned buyer CAN start and reply to a conversation; that is intended, not a regression.

**THE TRAP, and it has bitten once.** `assert_user_capability` resolves through `CapabilityResolver`, which does an unconditional `await self.db.execute(...)`. It therefore requires an `AsyncSession`. A route holding the SYNC `Session` from `get_db` must NOT pass that session: `sqlalchemy.orm.Session.execute` is not a coroutine function and the result has no `__await__`, so the endpoint returns HTTP 500 for every caller. This shipped once, on `inquiries.seller_respond`, and would have broken every seller reply to a buyer inquiry. Existing tests could not catch it because the test double is a `Mock` and `capability_resolver.py:150-160` has explicit `isinstance(self.db, Mock)` escape hatches that return `{}` before the await runs. The fix pattern is at `inquiries.py:510-520`: inject a second dependency `cap_db: AsyncSession = Depends(get_async_db)` for the capability check only and leave the sync `db` driving the route body. If you add a capability assertion to a sync route, do this, and write a regression test that does not use a Mock session.

**Admin-only routes take no seller gate.** `transaction_actions.settle_transaction` is admin-only; asserting seller capability there made it unreachable for its only authorised role. The approved Gate 2 spec text said otherwise and the Council ratified the code over the text (Kimi M1, S1488).

**Known non-blocking product question, CC finding S1488.** `vz_publish` rotate-key and revoke-install sit at threshold `active`, so a seller still `provisioning` cannot revoke a compromised install or rotate a leaked key until Stripe onboarding completes. Correct for publishing, arguable for these two defensive actions. Recorded, not changed.

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

Endpoint tests that exercise the trusted `X-Forwarded-For` path must also model
an internal socket peer in the ASGI request scope. Starlette's stock
`TestClient` uses the non-IP peer name `testclient`; the resolver correctly
classifies that as unknown and will not trust a forwarding header on its own.
Set the test peer to an internal/CGNAT address instead of weakening or mocking
the production trust rule.

T-2026-000240 centralized all active consumers on this contract; it did not change any numeric thresholds, since current telemetry did not justify tuning them.

## Scheduled jobs (APScheduler)

Jobs defined in `app/core/scheduler.py`. Include: backup triggers, stale data cleanup, briefing generation, Gmail watch renewal, deploy monitoring.

## Public listing search relevance

`GET /api/v1/search` combines PostgreSQL lexical ranking with Qdrant semantic ranking. PostgreSQL remains the source of truth for listing publication state and searchable listing fields; Qdrant is a derived semantic index. Do not diagnose a relevant-listing miss as a Qdrant-only failure.

When a published listing is absent for a customer query:

1. Confirm the listing is public and inspect its title, description, category, and tags in PostgreSQL. Reproduce the exact customer query against the live public endpoint and retain a nonsense-query zero-result control.
2. Check the PostgreSQL lexical rank and the Qdrant semantic result separately. Preserve the global `SEARCH_SCORE_THRESHOLD` unless the ticket explicitly proves that the threshold itself is wrong.
3. If the miss is a narrow vocabulary mismatch, add only ticket-grounded, bounded lexical synonyms in `app/services/listing_search_service.py`. Keep the original query for exact-title and trigram scoring; apply expansion only to the PostgreSQL full-text query. Do not add schema changes or mutate production listing data to repair ranking.
4. Run the focused listing-search service tests, deploy the exact merge commit, re-run both customer queries and the nonsense control, then verify the anonymous production journey using `e2e-browser-runner.md` E-01. Preserve the existing Browse-all fallback.

**T-2026-000697 proof (2026-08-24):** backend merge `674a9052a145ba76b9d47b5022d367019497d8c6`, Railway deployment `8465c33b-3eb6-4a94-babb-bc42cc1d45d4`, and anonymous E2E run `run-20260824T173157Z-3f57b11d`. Both `traffic` and `urban traffic incidents with coordinates` visibly returned `New York City Vehicle Collisions`; the nonsense control returned zero. The global threshold and Browse-all fallback were unchanged.

## Mediated inquiry response boundary

`MediationService` decides the disposition and attempts the durable `message_audit` write before publishing best-effort Redis trust events. A held decision must still raise 422 before any `inquiries` or `inquiry_messages` insert. Trust-event publication is observability, not part of the customer-response or seller-delivery boundary: `_emit_trust_events` publishes the two events concurrently under one total one-second budget, logs timeout/failure, and returns. Do not move trust events before the decision/audit, broaden the timeout to the event bus globally, or detach unreferenced tasks into the request lifecycle.

When a held inquiry remains on **Submitting...** even though `message_audit` already contains the held row, compare the browser click, audit timestamp, and final response timestamp. A roughly ten-second post-audit delay indicates sequential Redis socket waits in the response path. Verify a repair with the focused mediation timeout tests, the production `mediation-contact-leak-probe` charter, and a read-only database check proving two new held audits and zero inquiry rows for the synthetic buyer during the run window.

**T-2026-000698 proof (2026-08-24):** backend candidate `7009c41fbf3ce8ea5c741f683c28379831451539`, merge `283c6c21ae0d3445fbb619f3bcafc52d980bf431`, and Railway deployment `bce826e7-25f4-40a9-8b1a-513fbbfdfa75`. Production E2E run `run-20260824T183519Z-9f8666bb` completed both plain and disguised contact attempts with a visible held result. PostgreSQL showed exactly two new `message_audit` rows, both `held` with retry count 3, and zero new inquiry rows in the run window.

## When it breaks

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| 500 on an endpoint | `railway logs -d -n 50` — look for traceback | Fix code, push to main |
| Migration failure on deploy | Railway build log shows Alembic error | Make migration idempotent, redeploy |
| Redis connection errors | Check `REDIS_URL` in Infisical | Verify Railway Redis service is running |
| Agent health endpoint 401 | Missing `X-Internal-API-Key` header | Check ops dashboard API config matches `INTERNAL_API_KEY` |
| Public search misses a relevant published listing | Reproduce the exact query and a nonsense control; inspect PostgreSQL lexical rank and Qdrant semantic output separately | Follow **Public listing search relevance** above; preserve the global threshold and use bounded lexical synonyms only for a verified vocabulary mismatch |
| Qdrant search failures | Check Qdrant service in Railway | Verify `QDRANT_URL` and collection exists; remember PostgreSQL lexical ranking is an independent search path |
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

**Operator note:** the peer bus enforces these at the DB layer. If a `peer_msg_send` claim fails, the cause is almost always a missing `ref_entity` — always send claims WITH a `ref_entity` (see `runbooks/peer-instance-discipline.md`).

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

## Model-table drift and money-path recovery

The public `GET /health` response includes two model-schema fields in addition to the Alembic fields:

- `missing_model_tables`: an exact sorted list of model-backed tables that are absent, `[]` when none are absent, or `null` when database inspection failed.
- `model_schema_drift`: `true` when `missing_model_tables` is non-empty, `false` only when inspection succeeded and no model tables are missing, or `null` when the result is unknown.

Treat `null` as unknown and fail closed. Treat `model_schema_drift: true` as unhealthy even if the service still reports `status: healthy`; the list is the remaining repair scope.

Migration `s1488_money_path_tables` restores only the money-path tables `orders`, `transactions`, and `transaction_events`. It creates them from the current SQLAlchemy models in foreign-key order and skips a table that already exists. It does not claim to repair every missing model table. After deployment, require all three names to be absent from `missing_model_tables`; preserve and track any other listed tables as residual drift.

For a seller dashboard `500` on `/api/v1/seller/stats`, check application logs for `UndefinedTable` and query `/health`. If `orders` is listed, verify that Railway startup ran `alembic upgrade head`, that `alembic_current` and `alembic_head` both equal `s1488_money_path_tables`, and that the three money-path table names no longer appear in the missing-table list.

Rollback is forward-fix only after the database is stamped at `s1488_money_path_tables`. Do not run this revision's downgrade on a production database: sibling foreign keys can block it, and pre-existing fallback-created tables or data may be destroyed. Do not redeploy an older image that lacks the `s1488` revision because its Alembic graph cannot resolve the stamped database revision. Correct defects with a new reviewed migration/code revision and deploy forward.

*Money-path recovery guidance added: S1507 (2026-08-11), T-2026-000580.*
