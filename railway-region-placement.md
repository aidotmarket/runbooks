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
  2. Confirm zero RUNNING instances across **every** deployment of the service. The tool pages through the full deployment history and fails closed if enumeration is incomplete; Beat has more than 50 deployments.
  3. Only then apply the new placement.

  This trades duplicate emission for a pause of a few minutes. The pause is bounded:

- **One deadline per pass.** Every Beat pass, move or recovery, runs under one 12-minute monotonic deadline. It covers stop, zero-RUNNING confirmation, deployment discovery, deployment, readiness and acceptance. Every wait, sleep, Railway request (including each page of the deployment listing) and health request inside the pass is capped by what is left of it. Each request, including reading and decoding its body, runs under the absolute deadline. A **read** still arriving when the budget runs out is abandoned, and control returns at once. A **mutation** counts as done only when Railway returns a decoded 200 response. Any HTTP error (a 502 or 504 gateway answer proves nothing about the upstream change), a timeout, a disconnect, or no answer by the deadline is an *unknown outcome*: Railway may still apply the change. The tool then exits 1 without recovering, because a late mutation could overwrite the recovery. This holds in every phase: a move, an automatic recovery and a standalone `restore` all end with a `mutation_unfenced` journal line naming the phase and the pending mutation, never with `restore_result`. See "When it breaks" for how such an outcome is resolved. Every recovery pass, automatic or `restore`, ends with a settlement inside its own 12-minute deadline: the tool waits 60 seconds, then re-runs acceptance pinned to the deployment the recovery accepted. A newer deployment, a placement change, or running out of budget makes the recovery a failure (exit 1), never a silent success. A request that would start after the deadline is refused. Acceptance that finishes after the deadline is a failure.
- **Admission reserves recovery time.** The move is admitted only if at least 27 minutes remain before the next Beat crontab tick: one move pass, one full recovery pass, and 3 minutes of margin. This is checked at precheck and again immediately before Beat is stopped. A refusal at either check changes nothing and exits 3; recovery runs only if a mutation was actually attempted.
- **Recovery is never refused for clearance.** If the move fails after a mutation, the recovery pass runs at once under its own 12-minute deadline. A standalone `restore` skips the clearance check too. While Beat is down, a tick can be missed but never duplicated.

The crontab ticks (UTC) are:

- hourly at :20 and :35;
- daily at 02:45, 03:00, 04:00, 04:30 and 15:00;
- 05:00, which is Sunday-only but treated as daily, the safe direction;
- 04:17, the connector audit purge from backend PR #562, counted now.

In practice Beat can move only when started between :36 and :53 past an hour with no daily tick in the next 27 minutes. Interval tasks such as the one-minute heartbeat resume when Beat starts.
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
| `region_consolidate.py` | `ff952d26698ed902374d32cd869d38809b22a50c7cb73294fb83d404778724ef` |
| `test_region_consolidate.py` | `545ea79191c9dfbb46a63a084cee093624c1c4d323d1484ff3727bb21c7618df` |
| `region_inventory.py` | `76cc3f906d2c9401a19847eb028fa02d459a68710a95861ff5523d559561dfca` |

The offline tests cover these cases:

- crash after readiness;
- replica mismatch;
- a lingering predecessor;
- image or manifest drift;
- a running cron execution;
- replica preservation;
- a bounded Infisical refresh;
- the Beat clearance window;
- pagination past the first page of deployments;
- an older RUNNING deployment blocking acceptance;
- a cron run that crashes during the wait;
- `verify` rejecting an unexpected region;
- a failed Beat move running recovery without a clearance check;
- the clearance check applying only on admission;
- a single deadline capping every wait;
- a move refused when the image changed since capture;
- a second-check admission refusal exiting 3 with zero mutations;
- a failure before any mutation not triggering recovery;
- a standalone restore ignoring clearance;
- a mutation answered with HTTP 400, 500, 502 or 504, inside or outside a Beat pass, exiting 1 with no recovery;
- an unknown mutation during automatic recovery or a standalone restore ending with `mutation_unfenced` and no `restore_result`, naming the pending mutation;
- the pending update's complete placement payload kept in the `mutation_unfenced` line;
- request timeouts capped by the deadline and refused after it;
- acceptance after the deadline failing;
- a trickling response returning control at the deadline;
- no timeout floor beyond the remaining budget;
- health checks propagating the deadline;
- a slow paginated listing stopping at the deadline;
- a mutation without an answer by the deadline treated as an unknown outcome;
- a mutation socket timeout treated as an unknown outcome;
- a read timeout not treated as an unknown outcome;
- no recovery after an unknown mutation outcome;
- settlement pinned to the accepted deployment;
- settlement within the recovery deadline;
- recovery and restore both using the settling pass.

All 43 pass. The watcher readiness pattern was checked against live logs: `receipts/watcher-readiness-sample.json` shows 28 matching lines in 113.

The tool is a dry run unless `--execute` is given, handles one service per call, and journals every step to `receipts/consolidation-journal.jsonl`.

1. Post a peer HOLD: there must be no backend merge or deploy, and no Infisical `prod` write, while moves run. Check that no backup cron is due within 15 minutes.
2. Run `capture` **after** the HOLD, immediately before the moves. It writes `receipts/consolidation-pre.v2.json` with the placement, deployment id, image digest, deploy manifest and volume evidence for each service. It refuses to overwrite an existing receipt; move a stale one to `receipts/archive/` first. `move` refuses with exit 3 if a service's image or manifest has changed since capture, which means a deploy happened. That way a routine release can never be mistaken for a failed move and rolled back.
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

   Stop at the first nonzero exit. The move target is the captured config with its single region replaced by `us-west2`, so the replica count is preserved. If the placement update does not start a deployment within 45 seconds, the tool redeploys the **running deployment's own image** with `deploymentRedeploy(id, usePreviousImageTag: true)`. It never uses `serviceInstanceRedeploy`, which builds the branch head (see the first live attempt below).

   A service is accepted only when all of these hold, read **after** readiness:
   - the latest deployment is the one this call created, and its status is `SUCCESS` (cron: `SUCCESS` or `SLEEPING`);
   - its `multiRegionConfig` equals the target exactly, region and replicas;
   - its image digest, commit and deploy manifest equal the captured ones;
   - RUNNING instances exist only on that deployment and equal its replica count. For cron, zero are RUNNING once any triggered run has finished; the cron predecessor is covered by this same check across all deployments;
   - `api.ai.market/health` returns 200;
   - its readiness check passes:

     | Kind | Readiness check |
     |---|---|
     | beat | `beat: Starting` |
     | watcher | a completed cycle line containing `"action_counts"` |
     | infisical | `secrets.ai.market/api/status` returns 200, then the auth refresh succeeds within the deadline |
     | worker, signer, cron | the deployment-level checks above |

   Every wait is bounded. A read or acceptance timeout is a failure that goes straight to restore; a mutation with an unknown outcome is not, and exits 1 with restore deliberately withheld. Cron acceptance completes its wait before reading any field. A dry run evaluates every precondition and exits 3 if one would refuse.

   Exit codes: 0 accepted; 3 refused at precheck with nothing changed; 2 move failed and the service was restored with the same acceptance; 1 escalate by hand: either a mutation's outcome is unknown (in any phase) and every further change is withheld, or the restore itself failed.
4. Afterwards:
   - Run `status`.
   - Run `verify <service> moved` (or `prior` after a restore) for any service you want to re-check. For Beat, readiness accepts the boot line or any periodic `Scheduler: Sending due task` line. It compares against the independently expected placement, runs readiness, and exits 4 on failure.
   - Check that tonight's backups at 02:00 and 03:00 UTC ran: S3 objects plus a health record with `status=ok`.
   - Check that the watcher freshness stays green ([issue-channel.md](issue-channel.md)).
   - Check that the celery worker heartbeat stays fresh.
   - Release the HOLD.

**Rollback:** `restore <service> --execute` puts a service back at its captured placement, with the same acceptance and the same Beat stop-before-start.

**Record:** the journal, an Event Ledger entry, and the placement table on this page updated with the result.

## First live attempt (S1786, 2026-10-01 18:14–18:21 UTC)

Under a peer HOLD, capture ran and `move ai-market-backup --execute` started. The placement update did not start a deployment, so the tool (then v11, sha256 `787f87c0…`) sent `serviceInstanceRedeploy`. Railway built the branch head, backend `main` `9b2b276b`, not the running commit `20eb5d72`; the us-west2 deployment `008c7cb2` reached `SUCCESS` with a different image digest. Acceptance correctly refused it (`image_same: false`) and recovery put the service back in `us-east4` (deployment `628a63ba`, `SUCCESS`, original digest, exit 2). The service now runs `9b2b276b` in its original region. No other service was touched; the HOLD was released. v12 redeploys the exact previous image and also compares the commit. The run needs a fresh capture, because the 18:14 receipt has no commit field and the backup deployment changed.

## When it breaks

- **The tool exits 3.** A precheck refused (placement drift, unhealthy service, or Beat outside its window); nothing was changed.
- **The tool exits 1.** Read the last journal line.
  - `mutation_unfenced` (phase `move`, `recovery` or `restore`): a Railway change may still land. The line names the pending call and its complete variables (service, environment, deployment ID or the full placement). Make **no** further change to that service, by tool or dashboard. Nothing the tool or `status` can observe proves that the specific pending call is spent: placement can already match, a deployment can come from an earlier call, and a `deploymentStop` has no new deployment to look for. So there is no observation-based release: keep the HOLD on that service and escalate to Max at once with the journal line. Do not assume the service is running. If the pending call was a `deploymentStop` on Beat, scheduled tasks may be stopped until Max decides how to resolve it; say so in the escalation. Any further change to that service waits for his decision.
  - `restore_result ok=false`: the restore itself got definite answers but failed acceptance. Run `status` and put the service back by hand in the Railway dashboard (Settings → Regions).
  - Either way, record what happened in the journal and on the Event Ledger.
- **The deployment never leaves `DEPLOYING`.** The tool gives up after 15 minutes and restores. Check whether `us-west2` has capacity, then retry later.
- **Infisical errors continue after a move.** Run `secrets.ai.market/api/status`. If it is not 200 after 5 minutes, `restore Infisical --execute`.
- **Limiter or Redis timeouts in a service.** First check that the service runs in the same region as its datastore.
