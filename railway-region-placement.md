---
title: Railway region placement and consolidation
owner: unassigned
last_verified: '2026-10-01'
aliases: [region move, region consolidation, us-west2, us-east4, multiRegionConfig, service placement, latency region]
error_signatures: [limiter Redis budget exceeded]
---

# Railway region placement and consolidation

**Rule (Max, 2026-10-01, Event `ec51bcab`):** run each service in the region with the lowest latency to what it talks to. In practice that means the region of its datastores. For `ai-market` and `infisical secrets-management.`, Postgres, Redis and Qdrant are in `us-west2` and have volumes there, so their app services belong in `us-west2`. A service in another region pays a cross-continent round trip on every query. S1786 measured this on the connector: 6 to 8 of 12 limiter calls to Redis missed their 100 ms budget from `us-east4`, against 12 of 12 after the move (see [customer-mcp-connector.md](customer-mcp-connector.md) "Gate 4 Step 3 done").

## Inventory (read-only)

`koskadeux-state/s1786/region_inventory.py` lists every project, environment and service with its live `multiRegionConfig`, and writes `receipts/region-inventory.json`. It needs `source ~/bin/railway-env.sh; unset RAILWAY_TOKEN`.

Placement on 2026-10-01 before consolidation:

| Project | In `us-west2` | In `us-east4-eqdc4a` |
|---|---|---|
| ai-market | Postgres, Redis, Qdrant, backend, frontend, ops-dashboard, connector, connector-auth | celery-worker, celery-beat, gateway-door-worker, seller-profile-worker, gateway-signer, issue-channel-watcher, ai-market-backup (cron 02:00 UTC) |
| infisical secrets-management. | Postgres, Redis | Infisical, `ai-market-backend` (the Infisical backup cron, 03:00 UTC) |
| aim-data | — | backend, qdrant, postgres (volume) — co-located; legacy, being replaced; not moved |
| vectorAIz | all four | — |

None of the services to be moved has a volume.

## Why a move is low risk

A region change creates a new deployment from the **same snapshot**: there is no rebuild and no change to variables, command or replica count. It is the same swap that every backend merge already performs on these services. That includes the brief overlap of two Beat or worker containers, which is already accepted for routine deploys (see [celery-infrastructure-deployment.md](celery-infrastructure-deployment.md)). The service-specific risks are:

- **Infisical:** it has no healthcheck, so the API can return errors for about a minute while the new container starts. Native syncs push to Railway and are not affected at runtime. Move it last, and only when no Infisical `prod` write is in flight.
- **gateway-signer:** it has a `/health` healthcheck, so the old container serves until the new one passes. Its source is a CLI upload; a redeploy reuses that snapshot.
- **Cron backups:** a deploy may run the job once. That is harmless, because backups are written under timestamped names. Never move a cron service within 15 minutes of its schedule.

## Procedure

The tool is `koskadeux-state/s1786/region_consolidate.py` (sha256 recorded in the PR). It is a dry run unless `--execute` is given, handles one service per call, and journals every step to `receipts/consolidation-journal.jsonl`.

1. Run `capture` once. It writes `receipts/consolidation-placement-pre.json` (prior placement and deployment ids) and refuses to overwrite it.
2. Post a peer notice: there must be no backend merge or deploy, and no Infisical `prod` write, while a move runs. Check that no backup cron is due within 15 minutes.
3. Run `move <service> --execute` in this order:
   1. `ai-market-backup`
   2. `infisical-backup`
   3. `issue-channel-watcher`
   4. `ai-market-gateway-door-worker`
   5. `ai-market-seller-profile-worker`
   6. `ai-market-celery-worker`
   7. `ai-market-celery-beat`
   8. `gateway-signer`
   9. `Infisical`

   Stop at the first nonzero exit.

   A service is accepted only when all of these hold:
   - the new deployment is `SUCCESS` (cron: `SUCCESS` or `SLEEPING`);
   - its manifest lists exactly `us-west2`;
   - one instance is running (not checked for cron);
   - the prior deployment is `REMOVED`;
   - `api.ai.market/health` returns 200;
   - its kind check passes:

     | Kind | Check |
     |---|---|
     | worker | a `celery@… ready.` log line |
     | beat | `beat: Starting` or `Scheduler: Sending due task` |
     | watcher | a completed cycle line containing `"action_counts"` |
     | http | Railway healthcheck passed |
     | infisical | `secrets.ai.market/api/status` returns 200, then `infisical_auth_refresh.sh` succeeds |

   On failure the tool restores that service to its captured placement and exits 2 (restored) or 1 (restore failed: escalate).
4. Afterwards:
   - Run `status`.
   - Check that the next backup runs at 02:00 and 03:00 UTC: S3 objects plus a health record with `status=ok`.
   - Check that the watcher freshness stays green ([issue-channel.md](issue-channel.md)).
   - Check that the celery worker heartbeat stays fresh.

**Rollback:** `restore <service> --execute` puts a service back at its captured prior placement, using the same acceptance checks.

**Record:** the journal, an Event Ledger entry, and the placement table on this page updated with the result.

## When it breaks

- **The tool exits 1 (restore failed).** Run `status` and put the service back by hand in the Railway dashboard (Settings → Regions). Record what happened in the journal and on the Event Ledger.
- **The deployment never leaves `DEPLOYING`.** The tool gives up after 15 minutes and restores. Check whether `us-west2` has capacity, then retry later.
- **Infisical errors continue after a move.** Run `secrets.ai.market/api/status`. If it is not 200 after 5 minutes, `restore Infisical --execute`.
- **Limiter or Redis timeouts in a service.** First check that the service runs in the same region as its datastore.
