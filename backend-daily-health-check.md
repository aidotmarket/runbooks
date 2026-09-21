---
title: Backend Daily Health Check (GitHub workflow, "Health Check CRITICAL" issues)
owner: vulcan
last_verified: '2026-09-21'
aliases: [Daily Health Check, Health Check CRITICAL, health-check.yml, health_check.py, railway-volumes, volume capacity alert, backend issue 435]
error_signatures: ["volume_unknown", "Health Check CRITICAL", "RAILWAY_API_TOKEN not set", "Check crashed:"]
---

# Backend Daily Health Check (GitHub workflow, "Health Check CRITICAL" issues)

## What it does

`ai-market-backend/.github/workflows/health-check.yml` ("Daily Health Check") runs at 07:00 UTC every day and on manual dispatch. It runs `scripts/health_check.py`, which calls the production backend (`BACKEND_URL`, default `https://ai-market-backend-production.up.railway.app`) with the `INTERNAL_API_KEY` repository secret in the `X-Internal-API-Key` header. Six independent checks: Railway volumes (`/api/v1/internal/health/railway-volumes`), Postgres (`/api/v1/internal/health/postgres`), Redis (`/api/v1/internal/health/redis`), SSL certificates, the backend `/health` endpoint, and the Cloudflare worker. The workflow also fetches backup status and can run an auto-VACUUM on a bloat warning.

If any check is `critical` the workflow opens a GitHub issue titled `Health Check CRITICAL — <date>` with labels `health-check` and `urgent`. The open-items board counts those issues as one GitHub alert (`Health Check CRITICAL xN, <first>..<last>`), which is why the page headline can be one higher than the number of rows.

## How to read an issue

Each critical line is `**<check name>** (<category>): <message>`. Open the linked workflow run for the full JSON report. Reproduce one check headless from Titan-1 without printing the key:

    curl -s -H "X-Internal-API-Key: $INTERNAL_API_KEY" \
      https://api.ai.market/api/v1/internal/health/railway-volumes | python3 -m json.tool

## When it breaks

### `volume_unknown` ... `<serviceId>/<mountPath>: <n>MB` - old false alarm, FIXED 2026-09-21 (S1734)

Seen daily 2026-09-16..20 (backend issues #408, #411, #418, #428, #435): Postgres ~5549 MB and Qdrant ~8457 MB reported critical. Cause: `app/api/v1/endpoints/health_internal.py` judged used size alone (`>= 4096 MB` critical) without reading capacity, and returned no volume name. Real capacity, read 2026-09-21 from Railway GraphQL (`environment.volumeInstances.sizeMB`): every volume is 50000 MB; Postgres 11%, Qdrant 17%, Redis 2%.

Fixed by ai-market-backend PR #438: the endpoint now reads `sizeMB`, `volume { name }` and `service { name }` and decides on percentage of capacity (`>= 90%` critical, `>= 80%` warning, missing capacity = warning "capacity unknown"). Each check is named `volume_<volume name>` (for example `volume_postgres-volume`) and its message reads `postgres-volume (Postgres): 5592 / 50000 MB (11%)`.

If a volume check goes `warning` or `critical` now, it is real:

1. Confirm with the curl above; the message carries used, capacity and percent.
2. Grow the volume in Railway (service, Volumes) or reduce data following `qdrant.md` / `backup-and-recovery.md`.
3. `capacity unknown` means Railway returned no `sizeMB`: query it by hand (Railway credentials in `sysadmin.md`, account token as Bearer, `User-Agent` header required) before assuming anything.

### `railway_volumes` skipped: `RAILWAY_API_TOKEN not set`

The backend service has no `RAILWAY_API_TOKEN`. See `sysadmin.md` (Railway credentials: the account token and the project token serve different consumers) before changing it.

### `railway_volumes` critical: `Endpoint error: ...` or `Railway API error: ...`

The backend could not be reached with the internal key, or Railway's GraphQL API rejected the call. Check the `INTERNAL_API_KEY` repository secret against Infisical (`infisical-secrets.md`), then the Railway token as above.

### `<function name>` critical: `Check crashed: ...`

The check itself raised. It is a bug in `scripts/health_check.py`, not an infrastructure failure; the other checks still ran.
