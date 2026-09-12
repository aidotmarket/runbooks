---
title: Seller production payment cutover
owner: vulcan
last_verified: 2026-09-12
aliases:
  - Seller payout quiescence and restore
error_signatures: []
---

# Production payment cutover: stop, reconcile and restore

Prepared September12,2026 for Mars4120. Read-only preflight; no production deployment, configuration, stop, restart, cancellation, queue or database mutation was performed. This is the release-specific supplement to the [Seller Workspace operator guide](seller-workspace-operator-guide.md). It must be incorporated into the accepted payment Gate2 and final deployment record.

## Verified identity and controls

Railway CLI4.30.3 `status --json` succeeded using the already-linked operator directory `/Users/max/Documents/Codex/2026-09-09/seller-agent-account-consumer-continuation/outputs/railway-production-operator-s1707`, with inherited RAILWAY_TOKEN removed. Canonical project is e81dd66f-808c-412e-b32c-f6d910f0ac5d, production environment23e322c3-b195-45d8-9151-c4c27a998c33. Do not use the different historical project ID in the old secrets-runbook header.

At01:59:45UTC, all four backend services' latest deployments were SUCCESS on d766b8e4e66d7803ebe48f8a3132521abbebe957. This is refreshed platform inventory, not end-to-end application proof or evidence that no overlapping deployment exists.

| Role | Service ID | Deployment ID at preflight |
| --- | --- | --- |
| API | 4a68ea36-41de-4300-9bab-48e506b0dba6 | 621173d0-149d-4d9a-a611-09767d7203ba |
| General worker | b04bf73a-aa49-4bdb-9e8d-f8f2715ce9b1 | f5415bba-ced7-4269-a6c8-d8626f3c53d0 |
| Beat | 6f7319f0-2fc1-4e51-9955-6a8bd644e363 | dbef10f9-ee53-47dc-8932-bc7bf689f6e0 |
| Profile worker | ca74c2ac-6045-4d32-9e62-c1c39b8a8a80 | be1504b6-2da0-46d9-86aa-949ec4f2de43 |

Source receipt: [SELLER-RAILWAY-QUIESCENCE-INVENTORY-S1712.json](evidence/seller-cutover-s1712/SELLER-RAILWAY-QUIESCENCE-INVENTORY-S1712.json). General worker consumes default,scheduled,emails,vectoraiz; profile worker consumes only seller_workspace_profile_control. Beat is singleton. All four have one replica in their configured region. Current deployment manifests show drainingSeconds=null and overlapSeconds=null. Database, Redis, Qdrant, frontend, dashboard, watcher and backup are separately inventoried and must not be deleted or stopped merely because they share the project. Inspect the exact writer inventory before excluding any additional application process.

Authenticated read-only GraphQL introspection verified these current operations at https://backboard.railway.app/graphql/v2:

| Operation | Verified signature | Intended use, not executed |
| --- | --- | --- |
| deploymentStop | id:String! → Boolean! | Stop an exact running deployment |
| deploymentCancel | id:String! → Boolean! | Cancel an exact queued/building deployment |
| deploymentRedeploy | id:String!, usePreviousImageTag:Boolean → Deployment! | Recreate a reviewed compatible retained deployment |
| serviceInstanceDeployV2 | serviceId:String!, environmentId:String!, commitSha:String → String! | Deploy the exact accepted commit and retain returned deployment ID |
| deploymentRestart | id:String! → Boolean! | Restart the same deployment; not the selected upgrade mechanism |

These controls are also documented in [Railway deployment API](https://docs.railway.com/integrations/api/manage-deployments) and [service API](https://docs.railway.com/integrations/api/manage-services). The schema also exposes deploymentStopped, activeDeployments and deployment instances, which are relevant verification fields. Introspection proves availability of the operation signatures, not write authorization or a successful stop. No write probe was made.

Do not substitute service deletion, deployment-history removal, a guessed zero-replica scale command or the locally failing `railway scale` path. The current API gives an exact deployment stop control. The installed CLI's Region.railwayMetal schema problem was reported by Mars; this preflight did not rerun that failing scale operation or upgrade the CLI.

## When it breaks

Read the established secrets and local-secops runbooks before credential work. The helper now uses the existing ambient account/workspace RAILWAY_API_TOKEN that the working CLI uses, never prints or persists it, and executes only GraphQL queries and CLI status. Use `work/railway-quiescence-readonly-s1712.py` for reproducibility. It refuses if that credential is absent rather than substituting a service token. No credential was generated, rotated or moved. Railway documents account/workspace versus project token inputs in its [CLI authentication reference](https://docs.railway.com/cli).

The initial urllib request returned HTTP403. Using the existing Railway configuration-export client's documented User-Agent and Accept headers with the same credential succeeded. Do not infer that this 403 means the API token is expired, or rotate it. Authentication is still required. See [SELLER-RAILWAY-QUIESCENCE-API-SCHEMA-S1712.json](evidence/seller-cutover-s1712/SELLER-RAILWAY-QUIESCENCE-API-SCHEMA-S1712.json) for retained nonsecret query and fields.

Historical diagnostic attempts: the direct serviceInstance query returned Not Authorized with the backend service's stored API credential and the cached CLI user token. Neither was the existing ambient account/workspace credential selected by the working CLI. No privilege was changed. A local helper bug also copied stale Content-Length between requests; it was corrected by constructing fresh headers. Do not repeat these unsuccessful credential substitutions.

Resolved read path at02:06:29UTC: the working CLI project query already includes `activeDeployments` for each production service instance. It returns exactly one active deployment for each of the four backend roles, matching the IDs and d766b8e4 source above. [SELLER-RAILWAY-ACTIVE-WRITERS-CLI-S1712.json](evidence/seller-cutover-s1712/SELLER-RAILWAY-ACTIVE-WRITERS-CLI-S1712.json) retains the filtered result. Use this verified project-query path for the before/after active-deployment comparison; the helper now uses it. Replica configuration is separately one per service from the inventory; no per-process termination has been performed or proven. A browser inventory found no existing Railway tab and the Mac was locked, so no UI stop-control observation is claimed and no new tab was opened.

Direct control-state query also succeeded at02:11UTC using the same ambient account/workspace credential as CLI. [SELLER-RAILWAY-CONTROL-READ-PROOF-S1712.json](evidence/seller-cutover-s1712/SELLER-RAILWAY-CONTROL-READ-PROOF-S1712.json) contains all four service IDs, active deployment IDs, deploymentStopped=false, canRedeploy, replica count and drain/overlap fields. Both read paths now work and the helper exits0. This removes the read-access uncertainty; it does not prove mutation permission or future termination. At cutover, retain explicit stop results and refresh both direct control state and project active-deployment enumeration.

## Freeze automatic deployments before product merge

The accepted Mars Gate2 at ee94bb25aa630d5e45c9dd0865e8636052787bb7, with acceptance register baac7653f93df83fd4ddf9c56e3fc2b68ac2351a, requires the trigger freeze **before merging any product change**. At02:18UTC the complete paginated inventory showed all four backend services connected to GitHub main with checkSuites=false. Waiting for CI or beginning the freeze after merge leaves a deployment race.

| Role | Trigger ID in the dated preflight |
| --- | --- |
| API | 211648dd-e2ce-4450-a150-62f0c5266586 |
| General worker | ac8e60c5-09dd-49bd-8186-ec2b1c303cd4 |
| Beat | 98893874-afff-41bd-ab86-60cef932290a |
| Profile worker | 675f3200-a9f8-4ac0-874f-5a920b384fc2 |

See the dated [trigger inventory](evidence/seller-cutover-s1712/SELLER-RAILWAY-TRIGGER-INVENTORY-S1712.json), [query/update contract](evidence/seller-cutover-s1712/SELLER-RAILWAY-TRIGGER-CONTRACT-S1712.json) and [mutation schema](evidence/seller-cutover-s1712/SELLER-RAILWAY-TRIGGER-SCHEMA-S1712.json). These are read-only observations, not executed freeze/restore receipts. Refresh the full paginated result for each exact project/environment/service before execution.

The current trigger-update input exposes branch, checkSuites, repository and rootDirectory; it has no enabled or paused field. Do not invent a disable flag or equate checkSuites=true with a freeze. The scoped deploymentTriggerDelete/deploymentTriggerCreate operations are the selected control shapes, subject to exact execution verification. Do not substitute service-wide disconnect, which could affect another environment.

Before deletion, retain every source/configuration field required for exact recreation: projectId, environmentId, serviceId, provider, repository, branch, checkSuites and rootDirectory, plus original trigger ID and any inherited/base-environment binding. The trigger-object query does not expose rootDirectory directly. A separate authenticated serviceInstance query at03:14:53UTC verified rootDirectory=null for all four services and the create-input field types; see [restore-field receipt](evidence/seller-cutover-s1712/SELLER-RAILWAY-TRIGGER-RESTORE-FIELDS-S1712.json). Preserve that explicit null when refreshed, not an assumed default. The same receipt records railway.worker.json for the general worker and railway.beat.json for Beat (API/profile null); trigger operations must preserve those separate service configuration values. Before actual deletion, refresh both trigger and service-instance fields and verify their joint preimage. Refuse an unpreservable/inherited binding until its exact restoration path is established. Pause other operator, CI and variable-sync deployment sources under the same cutover owner.

Delete only the freshly matched environment-scoped triggers and retain each mutation result. Re-query complete pages and verify their absence before product merge. Separately enumerate and cancel/stop any already-queued or active old deployments according to the accepted writer-stop sequence below. Removing a trigger does not stop an existing deployment or prove quiescence. An unexpected new deployment invalidates the boundary and must be reconciled before migration or enablement.

Restore the recorded trigger configurations only after all required roles run the exact accepted source/image/schema and the owner permits automatic deployment again. Capture newly assigned trigger IDs, verify complete returned configuration against the saved preimage and confirm no duplicate trigger or unexpected deployment was introduced. A restored source trigger is not proof that the application itself is healthy; retain the separate source/image/readiness and normal-path execution receipts. After any uncertain delete/create response, read current scoped state before retrying; do not create a second trigger because a response timed out.

## Concrete cutover sequence to bind at Gate2

1. Before product merge, freeze release ownership and automatic deployment activity for the affected services using the exact scoped trigger procedure above. Record the connected source/configuration and every active, queued, building and deploying version; prevent concurrent operator/CI/variable-sync changes during the cutover. A merge or secret-sync-triggered restart must not reintroduce an old writer. A latest-deployment snapshot alone is insufficient. Recheck full inventory throughout the boundary; any unexpected deployment invalidates quiescence.
2. Retain the exact old source/configuration/image/deployment IDs and recovery evidence. Record the accepted new candidate, schema, readiness marker, migration sequence and ORDER_PAYOUT_DISPATCH_ENABLED=false on every new-code participant. Old code does not recognize this new flag, so setting it is not the stop boundary.
3. Stop old public API admission and Beat publishing using the exact captured deployments, then stop/drain every old general worker and any other participating writer from Mars's inventory. Coordinate the shortest reviewed maintenance interval. Keep data stores intact. Explicitly inventory any already-running tasks/provider requests before and after stopping. The profile worker is a separate queue and must be classified from exact code; retain/deploy it as required for compatible schema/runtime, not by assuming it is a payout writer.
4. Do not assume Railway supplies a warm Celery drain. Its [deployment reference](https://docs.railway.com/deployments/reference#singleton-deploys) documents a default zero-second SIGTERM-to-SIGKILL interval. Current configuration does not establish a positive grace period. A reviewed warm-drain mechanism would need its own exact process/queue proof; changing drainingSeconds now has not been shown to affect an already-running deployment. With an immediate stop, treat interrupted payment requests as uncertain and reconcile them before proceeding.
5. Require terminal stopped state for every old deployment and no remaining old active replicas or pending old deployments. Match exact IDs/source, not just service names. Corroborate application/worker termination and database-session/transaction absence; use the platform stop receipt plus active-deployment/instance reads and relevant process/log evidence. Heartbeat expiry alone is inadequate. Broker queue length zero is not proof of zero active/reserved/unacknowledged tasks. Preserve queued work for the new compatible worker; never purge the broker to make a count pass.
6. After all old writers are absent, run Mars's accepted adoption/classification queries and provider reconciliation. Recheck confirmed, refunded/revoked, legacy payout, pending/uncertain operations and exact provider Transfer identities. The preflight count0 is historical and raceable while old writers run. A provider success followed by process death may lack the local commit; it cannot be classified as no payout. Do not create a fresh Transfer/idempotency identity to recover uncertainty. Unknown outcomes hold enablement.
7. Apply only the reviewed backward-compatible migration at the quiescent boundary. Deploy the exact new commit with dispatch still disabled, recording each returned deployment ID and actual source/image/config/schema. Wait until all required participants run the accepted implementation and no old writer remains. Verify readiness and refusals through the normal entry points. A rolling overlap with old code is not accepted proof of safety.
8. Enable payout dispatch only after complete adoption/reconciliation, accepted TEST evidence and the exact gate's enablement conditions. Restore API/worker roles and Beat scheduling in the reviewed order; verify normal scheduled and direct execution, no duplicate transfers, and correct refund/revocation exclusion. Record all changes and receipts before declaring the maintenance window complete.

The mutation shapes to include in the reviewed operator plan are `mutation($id:String!){deploymentStop(id:$id)}` and `mutation($serviceId:String!,$environmentId:String!,$commitSha:String){serviceInstanceDeployV2(serviceId:$serviceId,environmentId:$environmentId,commitSha:$commitSha)}`. These strings were not executed. Supply only freshly verified scoped IDs and the exact accepted candidate; never use latest branch implicitly.

## Restore and rollback

Before any migration or new money-state write, a failed cutover may restore the previously captured compatible deployment using deploymentRedeploy only if its canRedeploy state and retained artifact are still valid. Capture the newly returned ID and prove restored source/configuration. This is a recovery path, not authorization to restore unsafe payout behavior after new state exists.

After migration or new financial state, keep payout admission disabled and follow the accepted forward-compatible recovery protocol. Do not blindly restart the old binaries or downgrade the schema. Preserve paid rights, provider identities, uncertain operations and the new audit records. If restoring an older image is incompatible, leave the affected path closed while applying the reviewed fix. Provider reconciliation remains necessary after any interrupted external call.

## Evidence still required before deployment

This preflight has not stopped production, demonstrated warm drain, tested mutation permission, verified the eventual candidate's readiness, or shown a safe cutover. Full active-deployment/replica enumeration, exact writer/queue and provider-outcome reconciliation, trigger-freeze implementation and successful stop/restore receipts remain mandatory at the actual reviewed cutover. Those are execution evidence requirements under existing authorization; they are not a new user-permission request.

## Evidence location and freshness

The committed JSON receipts above are historical read-only observations from the stated timestamps. They contain no credentials. The reproducible local helper is retained at /Users/max/Documents/Codex/2026-09-11/seller-workspace-final-release-continuation/work/railway-quiescence-readonly-s1712.py; a future machine must retrieve the operational bundle or use the documented GraphQL queries and CLI project inventory with its established credential. Do not assume that local path exists elsewhere. Refresh the named project/environment/service identities immediately before execution, and retain new receipts without overwriting this dated baseline.
