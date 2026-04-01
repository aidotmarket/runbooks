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
| `/api/v1/state` | `state.py` | Living State — build queue, config |
| `/api/v1/marketing` | `marketing.py` | Campaign management, drafts |
| `/api/v1/finance` | (via `financeApi`) | Revenue, transactions, invoices |
| `/api/v1/internal` | `agent_health.py`, `health_internal.py` | Internal health checks (X-Internal-API-Key required) |
| `/webhooks` | `webhooks.py`, `gmail_webhook.py`, etc. | Stripe, Gmail, Drive, Railway webhooks |
| `/api/v1/search` | `search.py` | Listing search (Qdrant-backed) |
| `/api/v1/mcp` | `mcp.py`, `mcp_server.py` | MCP protocol endpoints |

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

---

*Created: S363 (2026-04-01)*
