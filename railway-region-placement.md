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

None of the services to be moved has a volume; `capture` proves this per service (see Procedure).

## Risks and how the procedure handles them

A region change writes only `multiRegionConfig`. Railway then starts a new deployment from the existing snapshot. The tool does not take "same snapshot" on trust: acceptance compares the new deployment's `imageDigest` and its whole deploy manifest (command, cron schedule, healthcheck, restart policy, everything except placement) with the values captured beforehand, and fails if anything differs. Volume absence is evidenced too: `capture` reads each project's volume instances and refuses any planned service that has one; the receipt records an empty `volumes` list per service.

- **Celery Beat is a singleton.** More than one Beat duplicates schedule emission ([celery-infrastructure-deployment.md](celery-infrastructure-deployment.md)). That page does **not** establish that the overlap during routine deploys is safe, so this procedure does not rely on overlap. Beat moves **stop before start**:
  1. Stop the running deployment.
  2. Confirm zero RUNNING instances across all of the service's deployments.
  3. Only then apply the new placement.

  This trades duplicate emission for a pause of a few minutes. The tool refuses to move Beat outside a UTC window clear of its crontab entries: minute 43 to 12, not in hours 02–05 or 15, with the hourly entries at :20 and :35. That keeps any scheduled crontab tick out of the pause. Interval tasks such as the one-minute heartbeat resume when Beat starts.
- **Workers, watcher and signer.** These may briefly overlap with their predecessor, as on any deploy. Concurrent Celery workers are a supported mode. Acceptance requires the predecessor to have zero RUNNING instances before the move is reported done.
- **Infisical** has no healthcheck, so the API can return errors while the new container starts. Native syncs push to Railway and are not affected at runtime. Move it last, with no Infisical `prod` write in flight. Its readiness check, a status 200 followed by an auth refresh, is bounded; a timeout restores it.
- **Cron backups** (`ai-market-backup` 02:00 UTC, `infisical-backup` 03:00 UTC) move only while no execution is RUNNING. Never move them within 15 minutes of their schedule. If the deploy triggers one execution, acceptance waits up to 15 minutes for it to finish; backups are written under timestamped names. The cron schedule is part of the compared manifest.

## Procedure

Prerequisites:

- `source ~/bin/railway-env.sh; unset RAILWAY_TOKEN`;
- a fresh `receipts/region-inventory.json` from `region_inventory.py`.

Files, all in `koskadeux-state/s1786/`:

| File | sha256 |
|---|---|
| `region_consolidate.py` | `8d4ce8adb3ab007650d4bb3d8be846034a4fb678d7726c7b4eef5eca1ddbf516` |
| `test_region_consolidate.py` | `ec55547aee013681254c5507779c808dde7c4bd5817d455f81b70f9bb81450df` |
| `region_inventory.py` | `76cc3f906d2c9401a19847eb028fa02d459a68710a95861ff5523d559561dfca` |

The offline tests cover these cases:

- crash after readiness;
- replica mismatch;
- a lingering predecessor;
- image or manifest drift;
- a running cron execution;
- replica preservation;
- a bounded Infisical refresh;
- the Beat window.

The tool is a dry run unless `--execute` is given, handles one service per call, and journals every step to `receipts/consolidation-journal.jsonl`.

1. Run `capture` once. It writes `receipts/consolidation-pre.v2.json` with the placement, deployment id, image digest, deploy manifest and volume evidence for each service, and refuses to overwrite an existing receipt.
2. Post a peer HOLD: there must be no backend merge or deploy, and no Infisical `prod` write, while moves run. Check that no backup cron is due within 15 minutes.
3. Run `move <service> --execute` in this order:
   1. `ai-market-backup`
   2. `infisical-backup`
   3. `issue-channel-watcher`
   4. `ai-market-gateway-door-worker`
   5. `ai-market-seller-profile-worker`
   6. `ai-market-celery-worker`
   7. `ai-market-celery-beat` (in its window)
   8. `gateway-signer`
   9. `Infisical`

   Stop at the first nonzero exit. The move target is the captured config with its single region replaced by `us-west2`, so the replica count is preserved.

   A service is accepted only when all of these hold, read **after** readiness:
   - the latest deployment is the one this call created, and its status is `SUCCESS` (cron: `SUCCESS` or `SLEEPING`);
   - its `multiRegionConfig` equals the target exactly, region and replicas;
   - its image digest and deploy manifest equal the captured ones;
   - RUNNING instances exist only on that deployment and equal its replica count. For cron, zero are RUNNING once any triggered run has finished; the cron predecessor is covered by this same check across all deployments;
   - `api.ai.market/health` returns 200;
   - its readiness check passes:

     | Kind | Readiness check |
     |---|---|
     | beat | `beat: Starting` |
     | watcher | a completed cycle line containing `"action_counts"` |
     | infisical | `secrets.ai.market/api/status` returns 200, then the auth refresh succeeds within the deadline |
     | worker, signer, cron | the deployment-level checks above |

   Exit codes: 0 accepted; 3 refused at precheck with nothing changed; 2 move failed and the service was restored with the same acceptance; 1 restore failed (escalate).
4. Afterwards:
   - Run `status`.
   - Run `verify <service>` for any service you want to re-check.
   - Check that tonight's backups at 02:00 and 03:00 UTC ran: S3 objects plus a health record with `status=ok`.
   - Check that the watcher freshness stays green ([issue-channel.md](issue-channel.md)).
   - Check that the celery worker heartbeat stays fresh.
   - Release the HOLD.

**Rollback:** `restore <service> --execute` puts a service back at its captured placement, with the same acceptance and the same Beat stop-before-start.

**Record:** the journal, an Event Ledger entry, and the placement table on this page updated with the result.

## When it breaks

- **The tool exits 3.** A precheck refused (placement drift, unhealthy service, or Beat outside its window); nothing was changed.
- **The tool exits 1 (restore failed).** Run `status` and put the service back by hand in the Railway dashboard (Settings → Regions). Record what happened in the journal and on the Event Ledger.
- **The deployment never leaves `DEPLOYING`.** The tool gives up after 15 minutes and restores. Check whether `us-west2` has capacity, then retry later.
- **Infisical errors continue after a move.** Run `secrets.ai.market/api/status`. If it is not 200 after 5 minutes, `restore Infisical --execute`.
- **Limiter or Redis timeouts in a service.** First check that the service runs in the same region as its datastore.
