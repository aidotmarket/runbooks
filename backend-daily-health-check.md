---
title: Backend Daily Health Check (GitHub workflow, "Health Check CRITICAL" issues)
owner: unassigned
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

### `volume_unknown` ... `<serviceId>/<mountPath>: <n>MB` - false alarm by design (open as of 2026-09-21)

Seen daily from 2026-09-16 (backend issue #435 and four before it): two criticals, `.../var/lib/postgresql/data: ~5549MB` and `.../qdrant/storage: ~8457MB`.

Cause, in `app/api/v1/endpoints/health_internal.py` (railway-volumes endpoint):

- The status is decided on used size alone: `currentSizeMB >= 4096` is `critical`, `>= 2048` is `warning`. The Railway GraphQL query asks only for `id`, `currentSizeMB`, `mountPath`, `serviceId`. It never reads the volume's capacity, so a healthy volume that has simply grown past 4 GB is reported critical every day, forever.
- The name is always `volume_unknown`: `scripts/health_check.py` builds the check name from `vol.get('volume', 'unknown')`, and the endpoint never returns a `volume` key. Tell the volumes apart by the mount path in the message (`/var/lib/postgresql/data` = Postgres, `/qdrant/storage` = Qdrant).

What to do when you see it:

1. Do not treat it as an outage. Nothing is failing; the number is how much is stored, not how full the disk is.
2. Check real headroom: read each volume's capacity in the Railway dashboard (service, Volumes) or through the Railway API using the credentials in `sysadmin.md`, and compare it with the reported MB. Act only if a volume is genuinely above about 80% of its capacity: grow the volume in Railway (Postgres, Qdrant), or reduce data following `qdrant.md` / `backup-and-recovery.md` first.
3. Close the duplicate daily issues once headroom is confirmed, referencing this page.

The product fix (not done, no owner as of S1733): have the endpoint also request the volume's capacity from Railway, decide `warning`/`critical` on percentage of capacity, and return a `volume` name (for example the mount path) so the check is no longer called `volume_unknown`. It touches production monitoring only, no customer data; a proportionate review is enough. Update this section when it ships.

### `railway_volumes` skipped: `RAILWAY_API_TOKEN not set`

The backend service has no `RAILWAY_API_TOKEN`. See `sysadmin.md` (Railway credentials: the account token and the project token serve different consumers) before changing it.

### `railway_volumes` critical: `Endpoint error: ...` or `Railway API error: ...`

The backend could not be reached with the internal key, or Railway's GraphQL API rejected the call. Check the `INTERNAL_API_KEY` repository secret against Infisical (`infisical-secrets.md`), then the Railway token as above.

### `<function name>` critical: `Check crashed: ...`

The check itself raised. It is a bug in `scripts/health_check.py`, not an infrastructure failure; the other checks still ran.
