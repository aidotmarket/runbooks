---
title: Seller Workspace operator guide
owner: vulcan
last_verified: '2026-09-12'
aliases:
  - Seller Workspace diagnosis support and upgrades
  - Seller AWS and R2 operating procedure
error_signatures:
  - stale_version
  - DELETE_IN_PROGRESS
---

# Seller Workspace operator guide

This is the continuing operator guide for diagnosis, support, controlled upgrades and recovery. Read it together with the dated [live release record](seller-workspace-live-release.md). That record preserves individual failures and receipts; this guide explains the system and the procedure. The [architecture contract](../seller-workspace-cloud-listing-delivery.md) contains frozen security requirements and historical W1/W2 scope, which must not be mistaken for current availability.

## Verified baseline and remaining gates

Verified on September 11, 2026, against backend candidate `6c0e93cbf805b48a7b0c4e589deda6c880378784`, merged as `012159b93330ef54951ccd035534d3299f742063` in [PR393](https://github.com/aidotmarket/ai-market-backend/pull/393):

- AWS S3 and R2 connection, source selection, allAI-assisted preparation, exact seller approval/publication and actual paid browser downloads passed in production. These are earlier S1707 receipts, not newly purchased tests.
- AWS profiling passed twice through the normal application, scheduled worker, installed broker, actual ECS task, committed database evidence and authenticated evidence retrieval. Both connections belong to the same seller. This is not cross-seller proof.
- AWS profiling admission is currently paused on backend and dedicated worker after the tests. Core AWS/R2 functionality remains enabled at the last production check. R2 **profiling** remains unimplemented; R2 connection/publication/delivery must not be described as R2 profiling.
- Physical test resources and credentials were removed; original stacks and execution permissions were restored. At 17:25:20 UTC AWS confirmed exact task-definition records A15/B9 absent, with retained request IDs. Application, physical, template/permission, local-secret and metadata cleanup are now complete.
- Joint live compatibility with Mars's AIM Data environment remains open. Successful production downloads, source tests, a draft overlay and a healthy deployment do not close that gate.

Refresh actual deployed identities, capabilities, cleanup records and the current owner before an operation. The dates, IDs and pins in this guide are an evidence baseline, not permission to reuse expired installations or authorizations.

## Safe continuation by another instance

1. Read the current session lifecycle and owner registry, the current handoff, this guide, the release record, `SELLER-CHECKPOINT-S1712.json` and Living State `infra:seller-workspace-release-s1712`. Read named supporting receipts and source only as needed; do not stall on an exhaustive historical bundle.
2. Confirm one implementation owner. S1712 is the current Vulcan owner; closed S1707 must not be reopened. Preserve peer worktrees and Mars's S1656 environment. Do not create replacement tasks or subagents without authority.
3. Inspect branch status before editing. Work in the owned checkout, fetch current main, and retain exact candidate, merge and deployed SHA separately. A clean old worktree does not prove current production identity.
4. Prefix every shell command with `rtk`; use `rtk proxy` for commands without a specialized wrapper. Apply the same rule to commands launched by helper scripts. Inspect helpers before running them: several dated helpers perform mutations.
5. Read [Infisical secrets](../infisical-secrets.md) and [local SecOps](../local-secops.md) before credential/configuration work. Do not substitute another vault, invent a principal, print secret values or recover authorization from logs.
6. Preserve the user's cumulative **$100 project authority**. The September 11 conservative allocation is $84.8369454546, including $50 of earlier purchases. It is reserved exposure, not a final bill. Keep a current allocation ledger and bounded resource lifetimes; unused attempts, credits and delayed billing are not new spending headroom. Do not repeatedly ask for incremental approval within existing scope and cap. New purchases/refunds/payouts and peer mutations are not automatically authorized by the cap.
7. A timed-out mutation has an unknown outcome. Read its operation handle, idempotency record or current state before retrying. A Living State timeout can precede a committed write; verify the expected version instead of issuing a duplicate update.

Use [session lifecycle](../session-lifecycle.md) and the current Council runbooks for governed handoff/review. This page does not replace their current contracts.

## Architecture and custody

| Component | Owns | Diagnose here |
|---|---|---|
| Existing seller dashboard | Session-authenticated UI, provider ceremony, source selection, review/approval | Actual browser requests, capabilities and versions; never infer capability from a visible button |
| Backend API and PostgreSQL | Ownership, encrypted provider references, immutable source/approval/publication, job state, entitlement and audit | Owner-scoped API plus bounded read-only database queries |
| Redis, Beat and dedicated profile control worker | Scheduled metadata control, revision-bound heartbeat, outbox/reconciliation and cleanup | Queue, scheduler routes, heartbeat revision/time and persisted leases |
| Installed AWS verifier | Checks exact stack, signed packages, IAM, network, DNS, encryption, image and resource binding | Installed verifier response and exact inspected resource controls |
| Installed AWS broker | Starts/polls/cancels/cleans an exact job-bound ECS task | Broker operation, request hash, actual task ARN and attempt |
| ECS profiling image | Bounded parsing in seller AWS account with isolated scratch | Exact digest, container startup, limits, output and exit status |
| Publication/delivery services | Approved immutable version, purchased authority and short-lived direct object grants | Approval/version/authority/order/session/file-grant chain |
| Seller AWS S3 or R2 | Dataset storage and actual buyer bytes | Provider metadata and authorized direct download proof |

Provider credentials are versioned envelope-encrypted server-side records. Listing JSON, allAI prompts, task queue messages, public presentation and buyer manifests must not contain provider secrets. The backend control worker orchestrates metadata; it does not parse seller datasets in its process. ECS uses a read-only root and one nonpersistent `/scratch` mount, owned by UID/GID 65532 with mode 0700 and `TMPDIR=/scratch`.

allAI receives bounded structured evidence and proposes text. Seller approval binds the exact presentation/source version; allAI cannot connect storage, broaden scope, approve, publish or mint buyer authority. Current public projection uses `approved_public_presentation` and the explicit no-sample decision. Historical public-sample design language is not proof that an arbitrary sample path is available.

New browser listings use `workspace_connection`; existing device listings retain `legacy_serial`. Both meet at marketplace contracts, not a shared runtime or installation identity. Purchased bytes flow directly from provider to buyer; ai.market checks entitlement and commits audit before returning grants.

## Source map for diagnosis and changes

Paths below are relative to the exact backend checkout being inspected. Read the file at the deployed/candidate SHA, not an unrelated peer checkout.

| Concern | Primary source |
|---|---|
| Capability truth and stage dependency checks | `app/core/seller_workspace_config.py` |
| Connection and profile HTTP contract | `app/api/v1/endpoints/seller_workspace.py`, `app/schemas/seller_workspace.py` |
| AWS connection/rotation | `app/services/seller_workspace_connection.py` |
| R2 input/custody/provider adapter | `app/schemas/seller_workspace_r2.py`, `app/services/seller_workspace_r2_connection.py`, `app/services/seller_workspace_r2.py` |
| Envelope encryption and audit | `app/services/seller_workspace_encryption.py`, `app/services/seller_workspace_audit.py` |
| Job transactions, versions, leases, costs, evidence | `app/services/seller_workspace_profile.py`, `app/models/seller_workspace.py` |
| AWS broker/verifier calls and canonical hashing | `app/services/seller_workspace_profile_aws.py` |
| Scheduled control and readiness | `app/tasks/seller_workspace_profile.py`, `app/core/seller_profile_readiness.py`, `docs/seller-profile-worker-readiness.md`, `railway.profile-worker.json` |
| Installed infrastructure | `infra/seller_workspace_profile/template.yaml`, `broker/handler.py`, `verifier/handler.py`, `common/contracts.py`, `package.py`, `README.md` |
| Actual parser image and enforced limits | `seller_workspace_profile_runtime/Dockerfile`, `profile_task/main.py`, `profile_task/supervisor.py`, `profile_task/limits.py` |
| Source, review, approval and publication | `app/services/seller_listing_source.py`, `seller_listing_review.py`, `seller_listing_approval.py`, `seller_listing_publication.py` and corresponding schemas/routes |
| Public projection and search | `app/services/seller_listing_public_presentation.py`, `seller_listing_search.py` |
| Purchased delivery | `app/services/seller_workspace_delivery.py`, `seller_workspace_delivery_aws.py`, `seller_workspace_delivery_limits.py`, `app/api/v1/endpoints/seller_workspace_delivery.py` |
| Large manifests and lazy file lookup | `app/schemas/seller_source_limits.py`, `app/services/seller_approved_source_index.py` |

## Normal seller and buyer operation

Start with `GET /api/v1/seller-workspace/capabilities`. The backend combines implementation markers, master/provider/stage flags, key/principal readiness and, for AWS profiling, fresh worker readiness. Defaults remain off in source. An environment flag alone is not a passed prerequisite.

**AWS connection.** Create a connection through the normal authenticated product route. The server generates a connection-specific ExternalId and exact-principal trust ceremony. Use those actual values; never substitute a prior connection's ExternalId. The seller installs the bounded role and submits role ARN, bucket, prefix and region to verification. Verification assumes the role and pins scope. Rotation starts a new connection-local ceremony and activates it only after verification; the existing active credential remains authoritative until replacement succeeds. Disconnect blocks new use and destroys recoverable authorization material while preserving redacted audit.

**R2 connection.** The approved current path is dedicated bucket read-only credentials entered through `POST /connections/r2`; replacement uses `PUT /connections/{id}/r2-credentials`. Inputs include actual account ID, jurisdiction, bucket, prefix, write-only key fields, `dedicated_bucket_readonly: true` and expected version. Use the current schema and UI; never place keys in shell arguments, screenshots, receipts or error text. This path does not mean OAuth was repaired. OAuth HTTP 403/error 1010 remains a provider-authority issue; do not broaden the client, bypass WAF, invent parent access-key authority or publish a support message as a troubleshooting shortcut.

**Select and prepare.** Discover actual provider metadata and freeze the selected source version. The listing-selection limit is 50,000 files and 64,000,000 metadata bytes. This is a private manifest bound; it is distinct from the 10-object profiling selector. Preserve version IDs/ETags and source hash. allAI may propose description/presentation from allowed evidence; seller review and exact approval remain separate steps. Changed content, source scope or material presentation needs new review/approval, not an edit to a purchased immutable version.

**Publish and purchase.** Publication binds approved presentation, source snapshot, connection scope, listing version and `DeliveryAuthority`. Public search must read the approved public projection, not private draft fields. Pre-purchase checks validate stored authority, active credentials and frozen object metadata. Payment and purchased version remain marketplace-owned.

**Download.** The delivery service resolves the purchased immutable version, not the seller's latest draft. It checks buyer ownership, payment/transaction state, expiry, revocation, download allowance, active connection and authority scope. A download session consumes one bundle allowance; per-file grants are generated lazily and stored encrypted. The file URL lifetime is at most 300 seconds and also bounded by order/session expiry. Previously issued provider URLs can remain usable until expiry; disconnect/refund blocks new issuance rather than promising recall of already issued bearer URLs.

Per-file traffic limits are 600/buyer/minute, 1,200/source-IP/minute and 6,000/global/minute across orders/sessions. HTTP 429 returns `Retry-After: 60`; respect it. Do not restart whole purchases or evade rate keys. If a stored file grant expired, use the supported new-download flow, with its normal allowance check.

## AWS profiling: exact operating sequence

All paths below are under `/api/v1/seller-workspace`. Use the signed-in seller's normal session and a unique actual `Idempotency-Key` for each logical mutation. Preserve that key privately for retries of the same request; do not print authorization headers. Versions in this example describe a fresh successful connection; always use the version actually returned.

| Step | Request and required bindings | Required result |
|---|---|---|
| 1 | `POST /connections` with provider `aws`; then `POST /connections/{id}/verify` with actual role ARN/bucket/prefix/region | Verified connection, normally version 2 |
| 2 | `PUT /connections/{id}/profile-runtime/source-kms-keys` with `expected_version` equal to connection version and actual `key_arns` | Source key-set version; the unencrypted fixture used `[]` and returned 1. Do not use expected version 0 after verification |
| 3 | `POST /connections/{id}/profile-runtime/estimates` with key-set version, supported region, `availability_zone_count: 2`, `interface_endpoint_count: 5` | Unexpired standing-cost receipt |
| 4 | `POST /connections/{id}/profile-runtime/authorize` with connection version, key-set version, actual standing receipt and `cost_acknowledged: true` | Authorized runtime, normally version 1, with immutable server pins |
| 5 | Install the reviewed signed template with actual application-generated IDs and approved scope | Exact stack outputs, package signatures, image and controls; installation alone is insufficient |
| 6 | `POST /connections/{id}/profile-runtime/verify` with runtime version and actual `runtime_references` | Installed verifier accepted; runtime normally version 2 |
| 7 | `GET /connections/{id}/source-objects` with selected prefix, version mode and bounded page size | Actual key/version/ETag/size bindings |
| 8 | `POST /cloud-object-selectors` with same connection/runtime, current runtime version, version mode, discovery cursor and 1–10 object bindings | Immutable selector and hash, no foreign runtime mixing |
| 9 | `POST /profile-jobs/estimates` with connection/runtime/selector, standing receipt and quota profile `default` | Unexpired job-cost receipt for the exact selection |
| 10 | `POST /profile-jobs` with those IDs, actual job estimate receipt, quota profile and `cost_acknowledged: true` | Durable job ID before claiming execution |
| 11 | `GET /profile-jobs/{id}`, then `GET /profile-evidence/{evidence_id}` | Terminal success plus normal owner retrieval of committed evidence |

Runtime references are the actual stack ID, broker/verifier alias ARNs, cluster ARN, control key ARN, control bucket, field-token secret ARN/version, task-definition ARN, subnet IDs and task security-group ID. Do not fabricate them or modify a verified binding in place.

Before installation, preserve original stack templates, execution policies, trust, keys/grants and source inventory. Inspect the change set and cleanup permissions. Confirm exact account/region and installation lifetime. In S1712 the 30-day standing estimate was $80.862842 per runtime; the temporary test used a three-hour bound and reserved exposure for both runtimes. That dated amount is not a current AWS price quote. Application receipts expire after 15 minutes; refresh expired estimates through the normal flow. Product spend limits and user project authority are separate checks.

The current code supports `eu-west-1` and `us-east-1`. It enforces standing/marginal admission caps and seller/global rolling budgets in `seller_workspace_profile.py`. Do not change a quota to make an incident pass. Inspect current price-table version/expiry and enforced runtime limits before another run.

The evidence contract caps 10 objects; 67,108,864 source bytes/object and 268,435,456 total; 100,000 rows/object and 250,000 total; 512 fields/object; 256 emitted field records/90,112 field-record JSON bytes; JSON depth 32; and 536,870,912 decompressed bytes total. These are schema bounds. For CPU, memory, wall time, compression and parser enforcement, also read the actual image's `profile_task/limits.py`, supervisor and tests. A schema maximum alone is not runtime enforcement proof. The inspected image also fixes one parser child, eight processes, 64 open files, 1 GiB temporary bytes, 3 GiB address space, 540 CPU seconds, 600 wall seconds, at most two attempts, a 100:1 decompression ratio and 131,072 final-result bytes. Declared object size may be up to 100 GiB, but bounded reads remain subject to the much smaller source-byte limits; do not confuse declared size with authorized ingestion.

## Scheduler, leases and persisted evidence

The dedicated queue is `seller_workspace_profile_control`. Beat sends heartbeat/reconciliation/expiry work; the dedicated worker executes it. The heartbeat is stored under the actual `RAILWAY_GIT_COMMIT_SHA`, has a 90-second TTL, and is rejected if stale, future-dated, malformed or for another revision. Redis failure closes readiness. Do not inject a timestamp or treat an unrelated worker heartbeat as evidence.

Jobs move through `queued`, `starting`, `running`, `validating_result`, optionally `cancel_requested`, then `succeeded`, `failed`, `cancelled` or `expired`. The service owns transitions with version/attempt/lease protection. Duplicate delivery without a lease releases the worker slot. Reconciliation retries durable outbox delivery and revisits terminal jobs whose attempt cleanup is incomplete. Direct SQL transitions, resetting an attempt counter or manually placing a guessed message on the queue bypass those controls.

Trace one incident by seller, connection, runtime/version, selector/hash, estimate, job/version/attempt, request hash, actual task ARN, evidence ID and deployment SHA. Read these tables with owner/ID filters and selected columns only:

- `cloud_connections`, `cloud_connection_credentials`: status, active/pending pointers, credential lifecycle timestamps; never ciphertext/ExternalId material in ordinary support output.
- `seller_workspace_profile_runtimes`, `seller_workspace_profile_source_kms_key_sets`, runtime cost estimates: version and bound identity/receipt metadata.
- `cloud_object_selectors`, `seller_workspace_profile_cost_estimates`, `seller_workspace_profile_jobs`, `seller_workspace_profile_attempts`: ownership, immutable selection, state, lease, counters, reservation/charge and cleanup status.
- `seller_workspace_listing_evidence`, `seller_workspace_audit_events`: committed evidence reference, expiry/deletion status and redacted audit.

Use read-only transactions. Do not run `SELECT *` against credential or private source tables, dump environment variables, or copy entire database backups to troubleshoot one job.

Success requires all of: actual container exit zero; job `succeeded`; normal evidence GET 200; committed undeleted evidence row matching the job; released reservation; cleanup timestamps; and independently recomputed hashes/bindings. A cloud result file, health endpoint or task exit zero alone is insufficient.

Canonical hashing uses JSON with `ensure_ascii=False`, sorted keys, separators `(',', ':')`, `allow_nan=False`, encoded UTF-8. Recompute semantic hash; attestation hash over `{semantic_hash, runtime_attestation}`; and result-integrity hash over the result without its integrity field. Check the exact schema in source before implementing a verifier. Then compare job ID, attempt, request SHA and runtime image binding. The wire attestation digest is 64 lowercase hex characters without `sha256:`. The historical `task_definition_digest` field binds the image hash, not a hash of task-definition JSON.

S1712 results each had six files, 1,333 source bytes, 517 decompressed bytes, 12 rows and 12 fields without truncation. Normalized aggregate comparison removed only per-source selector hash and per-runtime field tokens. That comparison is not identical-authority repeatability or cross-seller isolation proof. Keep those claims distinct.

## When it breaks

| Symptom | First discriminating check | Supported response |
|---|---|---|
| Profile unavailable despite flag | Actual backend/worker SHA, all four pins, price expiry and revision-bound scheduled heartbeat | Fix the missing prerequisite through configuration/release workflow; do not forge readiness |
| Queue grows; no work progresses | Dedicated queue routing, worker admission, DB role, outbox state and lease ownership | Restore normal worker/reconciliation; preserve attempt and idempotency state |
| `worker_step_limit_exceeded` | Persisted state/lease and whether duplicate/deferred work held the slot | Compare current duplicate/deferred release behavior; diagnose task before scheduling more |
| Installed verifier cannot invoke, KMS denial | Lambda environment decrypt phase versus handler failure; exact role denials and managed-key grant | Preserve exact function/key/context restrictions; do not add broad decrypt permission |
| `CannotPullContainerError`, registry DNS failure | Exact account-qualified ECR hostname and DNS firewall rules | Verify current hostname chain; review a narrow template/verifier correction |
| S3 layer name allowed but DNS still fails | CNAME chain including regional `s3-r-w` target and redirect inspection | Check current DNS; no wildcard or disabling block-all/redirect inspection |
| Image layer HTTP failure after DNS works | Regional ECR starport bucket endpoint statement | Compare documented service-signed layer policy separately from source/control role conditions |
| Source/control S3 denied | Gateway `Principal: '*'` plus exact `aws:PrincipalArn` conditions, source prefix and request/result paths | Correct exact policy representation; never remove source/control role conditions |
| Container exit 50 before parsing | `W3_CONTROL_BUCKET`, `W3_REQUEST_KEY`, `W3_REQUEST_SHA256` supplied by broker | Fix/re-sign broker; do not pass credentials or arbitrary task overrides |
| Read-only filesystem/scratch failure | Actual image UID/ownership, `/scratch` mount and `TMPDIR` | Preserve one ephemeral writable mount and read-only root; test actual image |
| Exit zero but `profile_result_invalid` | Actual wire JSON through backend schema; UUID representation, digest prefix, counters and three hashes | Correct source contract and run wire fixture tests; do not mark failed evidence accepted |
| Generic 409 “Idempotency key cannot be reused” | Same key/request hash AND connection/runtime/version ownership bindings | Re-read actual versions and binding; this text can mask `stale_version`, not just key reuse |
| HTTP 429 during many-file delivery | `Retry-After`, aggregate rate keys and per-file progress | Wait the supplied interval; resume bounded flow without new purchase |
| Buyer grant refused after rotation/change | Purchased immutable scope, active credential and frozen object metadata | Restore valid same-scope authorization or normal seller replacement; do not rewrite purchased version |
| R2 OAuth 403/error 1010 | Exact approved provider path and scope | Retain provider-authority block; use only already approved credential path |
| CFN deletion fails on firewall/task definition | Exact failed events, mutation protection and execution-role effective permissions | Perform only authorized exact cleanup; preserve failures and original policy baseline |
| ECS definition `DELETE_IN_PROGRESS` | Exact ARN describe response; stopped tasks and deletion request receipt | Read-only follow-up until absence; do not repeatedly submit delete or confuse inactive cluster with definition absence |

The infrastructure README records the individual AWS diagnoses and provider documentation. It includes historical failed-run statements; the current release record establishes the later successful run. For new provider behavior or permission semantics, check current official provider documentation before modifying controls.

## Read-only support procedure and receipt bundle

First establish impact: connection management, preparation/publication, paid delivery or profiling. Retrieve current capabilities and exact deployment identity. Then trace one actual resource chain above. Use existing authenticated UI/API and bounded provider reads; inspect only the owned installation. Collect UTC timestamps, sanitized error category, request ID, exact IDs/versions/hashes, operation outcome and next discriminating check.

The current local evidence root is `/Users/max/Documents/Codex/2026-09-11/seller-workspace-final-release-continuation`. Its `outputs/` contains durable user-facing receipts; `work/` contains inspected diagnostic and mutation helpers. A future instance on another machine must retrieve the retained receipt bundle rather than assuming these paths exist.

From that root, the following are existing **read-only provider/database probes** (they write local receipts). Inspect their fixed IDs and paths before use; they are S1712-specific, not general cleanup commands:

```sh
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python work/profile-result-wire-run-s1712/verify_definition_absence.py
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python work/profile-result-wire-run-s1712/read_committed_proof.py
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python work/profile-result-wire-run-s1712/check_quiescence.py
```

`verify_application_evidence.py` independently checks retained aggregate results. `verify_cleanup.py`, `verify_remaining_resources.py`, `check_key_grants.py` and `check_db_cleanup.py` inspect physical/application cleanup. Do not substitute a similarly named older run directory. Preserve previous timestamped observations before overwriting a receipt needed for chronology.

Never include Authorization headers, cookies, ExternalIds, R2 keys, decrypted runtime envelopes, presigned URLs or raw source cells in the support bundle. Exclude browser storage and network response bodies that carry credentials. Keep aggregate evidence access-controlled even when it has no raw cells. Audit local receipts after cleanup and remove temporary authorization copies. Browser navigation/reset can clear ephemeral automation state; it does not revoke a provider credential.

## Controlled teardown and cleanup acceptance

1. Freeze new profiling admission through the approved configuration path and verify actual backend/worker values. Do not shut off unrelated core seller stages. Identify every owned job/attempt/task and preserve evidence before deleting control outputs.
2. Cancel outstanding jobs through the versioned API where required; wait for actual stopped tasks and application attempt cleanup. Inspect pending outbox/leases/reservations and terminal attempts with incomplete cleanup. A zero queue length alone is not quiescence.
3. Revoke the test connections through normal application semantics. Verify active/pending credential pointers are clear and recoverable encrypted material is destroyed. Preserve redacted audit and committed proof.
4. Restore the exact original stack template, not a guessed minimal template. During authorized teardown, disable mutation protection only on the owned DNS firewall association, disassociate it and wait for absence. Keep operating protection enabled until teardown.
5. Check deployment-role cleanup permissions before installing. `ecs:DeregisterTaskDefinition`/`DescribeTaskDefinition` do not support task-family resource scoping; do not silently widen to `Resource: '*'`. Existing authorized operator access may clean an exact positively identified definition without broadening the stack role. Record any CFN retries/failures honestly.
6. Remove only owned temporary resources and test fixtures. Independently verify functions, buckets, secrets, logs, event rules, roles, endpoints, VPC/network, DNS groups/associations and active tasks absent, and expected clusters inactive. Preserve pre-existing KMS keys; verify state and exact grants, removing only identified test grants.
7. Restore original source trust and execution policies and prove equality with baselines. Source deletion requires fresh direct proof no runtime consumer remains and application connections are revoked. The S1712 exceptional ordering used a less-than-60-second proof while CFN metadata was finishing; it did not alter pending deletion requests or stack roles. Do not generalize that ordering without equivalent proof.
8. Wait for terminal CFN status and inspect resource events. Separately verify exact ECS definition absence. Accept only the expected exact not-found response, with request ID; access denial or timeout is not absence.
9. Remove temporary local authorization material and audit outputs. Do not rerun `cleanup_sources.py` after its baseline has intentionally been redacted. Mutation helpers are not idempotent merely because their filenames contain “cleanup.”

Track **application cleanup**, **physical resource cleanup**, **template/permission restoration**, **local secret cleanup** and **provider metadata deletion** separately. Only all required true states support overall cleanup completion. Repeated delete requests do not speed an asynchronous provider state.

## Upgrade, deployment and rollback

For the refund/settlement correction, use the [production payment cutover runbook](seller-production-payment-cutover.md). It names the verified Railway stop/restore controls, old-writer exclusion, interrupted-payment reconciliation and exact evidence required before enabling the new code. Its September12 receipts are read-only preparation, not a completed cutover.


1. Record current owner, source SHA, deployed SHA per service, four immutable pins, runtime IDs/versions, active jobs and baseline configuration. Read current relevant runbooks and exact Council contract. Preserve peer changes; use an owned branch/worktree.
2. Fix the smallest responsible layer. A broker wire correction does not justify loosening verifier IAM/network checks. Update this guide and the infrastructure README when their instructions become inaccurate.
3. Run focused contract/adversarial tests and required broader checks. For image changes, run the actual production image with network disabled, read-only root, non-root UID, dropped capabilities, CPU/memory bounds and scratch mount. Synthetic AWS I/O is useful but does not replace real cloud proof.
4. Dispatch exact-candidate review using the current task-visible Council contract. CC/GLM/DeepSeek are required voters for this work; Kimi is comparison-only. Preserve candidate SHA, submitted artifact hashes, returned verdicts and any accepted nits. Do not dispatch using guessed signed inputs or stale schema.
5. Package/sign immutable broker and verifier ZIPs through the reviewed release process. Bind the full image repository/account/region/path and digest. Preserve unsigned and signed hashes separately. Compare CI artifacts with reviewed source and published bytes; filenames or success labels are insufficient.
6. Merge the exact reviewed candidate, verify CI and candidate-to-merge content. Publish only authorized immutable artifacts. Changing a pin requires a new normal runtime authorization and installed verification; never edit an existing verified runtime binding to bypass versioning.
7. Update secret/configuration values through Infisical/local SecOps dry-run then execution, with values suppressed. In S1712 the backend secret project was `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment `prod`; revalidate against the runbook before use. Do not set `AUTHOR_DISPATCH_DATABASE_URL` on the application role path.
8. Verify actual deployed commit and pins for backend, ordinary worker, Beat and dedicated profile worker. Configuration sync can redeploy an older commit; a successful deployment label is not exact-source proof. Use an exact-commit deployment only when a verified mismatch requires it. Verify live database role/schema admission and revision-bound scheduled heartbeat.
9. Run a fresh bounded normal API/browser proof with actual application-generated IDs and an adequate cost/lifetime allocation. Confirm installed verifier, real task, committed evidence, hashes, ownership denials and cleanup. Do not reuse an expired runtime/estimate or count a prior failed logical job as unused capacity.
10. Publish exact receipts and update current status/checkpoint/Living State. Keep any broader compatibility/recovery gates explicit. Do not mark full release complete from static review or a successful isolated run.

For rollback, stop new admission at the affected stage, preserve evidence and reconcile/cancel active jobs. Restore the last reviewed compatible source and matching pins/configuration; do not combine old code with new artifacts. Database changes need an inspected migration/recovery plan; never blindly downgrade a schema holding purchased rights. Restore backups into an isolated target and compare schema/data, purchased-version authority, replay, revocation and immutability before a production recovery decision. Keep `legacy_serial` fulfillment intact and do not rewrite authority kinds.

## Joint AIM Data compatibility gate

[PR27](https://github.com/aidotmarket/money-path-test-environment/pull/27) merged as `c6b8770e69514035b2c78f0433f86209b4cefe0f` after final candidate `a7f1daf396c290810d1535c9049aeccb2b6f56ed` received APPROVE_WITH_NITS from CC, GLM and DeepSeek. The base was `03d3f30acf854537edd76fdb19e1cf521b577c9a`; candidate and merge trees were verified equal. Its nine-file scope includes the isolated static-contract correction below. Candidate and baseline-without-overlay static checks, six prepare tests, two Compose tests and CFN lint 1.50.1 passed. The repository had no hosted workflows or commit statuses; checks API access returned 403. Do not claim hosted CI success for this merge.

Mars S1714 owns the durable S1656 run; Vulcan S1712 owns Workspace implementation. Mars message 4090 verified run25 bundle `20260911T233041Z`: full browser journey, purchase confirmation, checkpoint `pending_settlement`, and direct settlement checker exit 2 with `pending-hold`. Infisical mapped that child exit to supervisor exit 1; this wrapper result is not evidence of a failed paid run. Purchase/browser hashes and production snapshots were checked. The hold deadline is **2026-09-13T23:41:11.491739Z**, September 14 at 01:41 Madrid. This timestamp does not open a work window: Mars must verify settlement and explicitly announce the post-settlement window.

The protected run remains pinned to environment `03d3f30acf854537edd76fdb19e1cf521b577c9a`, backend `d766b8e4e66d7803ebe48f8a3132521abbebe957`, and both acceptance specifications `519b1d5893dc410392cc66051dad0902572dcef9`. Merging PR27 did not change the peer checkout, runtime or pins. Preserve seller01 identity/device/trust/serial/orders, existing buyer01 orders, checkpoints and the exact shared `environment.lock`. Do not run the peer settlement checker independently or create a second environment to bypass the window.

### Static probe diagnosis and private preparation

A missing `device-boot/changed.calls` previously came from a copied operational checker using live default evidence and lock paths. The child refused mutation because a settlement was pending, but lock acquisition could already have written the shared lock record. The reviewed correction assigns `S1656_ACCEPTANCE_EVIDENCE_DIR` beneath the temporary probe and asserts containment. Diagnose the child exit/stderr first; isolate copied operational helpers and never overwrite a peer lock as a repair. Run these contract probes sequentially. Normal boot performs two positive Compose renders and one missing-principal negative render.

The preparer writes a private envelope. Pass only its `parameters` array to the CloudFormation SDK Parameters argument. A CLI consumer must write that array alone to a distinct exclusively created mode-0600 file and pass the file path, without printing/interpolating values. Reject incomplete output and remove both owned files during cleanup. Preparation is not provider or activation authority.

### Unresolved activation and refund dependencies

The normal seed clears seller02 TOTP/Connect/payouts state, while public Connect routes refuse synthetic users. GET Connect status can persist provider state for admitted users. A reviewed seed-only activation/deactivation amendment is required; do not patch payout flags, copy seller01 secrets or relax public synthetic guards. The draft is not Gate1 approval. Workspace design candidate `9aa91d48fcdfd166b510f1a0f5c3197b89b24287` was submitted to CC/GLM/DeepSeek; reviewer findings and the final implementation specification must be resolved before build. Mars's conditional non-interference feedback requires exact shared locking, captured before-state, provider disposition and default seed/reset refusal while an amendment is active or inconsistent.

At backend `d766b8e4`, the synthetic purchase exception does not admit `charge.refunded`, so a Stripe TEST refund alone does not establish an application refund or new-grant refusal. Source inspection also found that human refunds leave the transaction unchanged, settlement lacks a linked-order refund/revocation check, and finance commits separately from order/event handling. These are source findings, not a reproduced live erroneous transfer. The filed dispute-hold dependency owns human refund transition and settlement exclusion; the finance dependency owns retry-safe refund processing. **Authority updated September 12:** Max authorized the necessary production dependencies through event `99af61fd-db46-42fd-a18d-1d0698e457d1`, relayed in Mars4096. The earlier filed-work restriction is superseded for human refunded/revoked settlement exclusion, refund retry consistency and necessary acceptance redesign. Mars S1714 owns `build:bq-refund-safe-production-s1714`; Vulcan S1712 retains Workspace activation/admission. Proceed through the agreed MP build and unanimous Council gates without requesting repeat approval. Unrelated filed scopes remain excluded. The live-window and protected-run requirements remain separate technical gates.

The existing acceptance browser proof revokes the same order at lines 255–257 of `browser/s1681-delivery-leg.ts`, then confirms it at 267 and expects completed/confirmed at 269. Correct settlement exclusion therefore needs an explicitly reviewed acceptance redesign. Preserve old proof as evidence of its original specification; do not clear revocation, remove assertions or treat the old payout as proof of corrected refund semantics. Do not reuse S1681 `--abandon-refunded` for Workspace orders or invoke internal handlers manually.

Mars4103 agrees a separate Workspace W evidence namespace/window after required S1681 money phases conclude. S1681 retains exact positive/negative P/N order cardinality; W is never an extra hidden member. Preserve the settled P order and installation identities for joint regression, then prove exact W refund/cleanup. Settlement proofs use genuine 48-hour holds and can span multiple days. Mars4105 will pin a processor-and-schema readiness interface at Gate2; Workspace refund admission must fail closed when that prerequisite is absent, rather than relying on a flag or deployment-order prose.

The joint sequence must prove seller02 Workspace publication beside seller01 device listings in shared search; authorized hosted Stripe TEST checkout by buyer01; common dispatcher delivery; actual downloaded byte hash; cross-seller denial; API-key denial of session-only download; normal full-refund application/finance transition; durable direct and scheduled settlement refusal including retries/races; new-grant refusal; and cleanup. Record exact shared versions and both owners' confirmation. No new real-money first sale is implied.

The finish line includes reviewed production deployment and outside verification of money-path plus Seller Workspace. Use the existing upgrade/rollback procedure, actual per-service deployed identities and immutable artifact matches, normal public-domain capabilities and authorized existing-order delivery checks. A test overlay merge, hold, healthy process or seed-only milestone does not close production release. Refresh the historical production observation before any deployment; the last retained four-service observation was September 11 at 17:30 UTC on `ec5262cf25ac46cf6ba437457572f587df375ac3`.

## Current release and evidence index

Repository artifacts are durable; local receipts must be retained with the handoff. All receipt paths below are relative to the evidence root's `outputs/`.

| Evidence | Location / identity |
|---|---|
| Current checkpoint and narrative | `SELLER-CHECKPOINT-S1712.json`, `SELLER-LIVE-PROFILING-S1712.md` |
| Successful application jobs/evidence | `profile-result-wire-run-s1712/SELLER-PROFILE-APPLICATION-SUCCESS-S1712.json`, `SELLER-PROFILE-APPLICATION-EVIDENCE-A-S1712.json`, `SELLER-PROFILE-APPLICATION-EVIDENCE-B-S1712.json` in the same directory |
| Committed DB and binding denial | Same directory: `SELLER-PROFILE-DB-COMMITTED-PROOF-S1712.json`, `SELLER-PROFILE-CONNECTION-RUNTIME-DENY-S1712.json` |
| Cleanup baseline/result | Same directory: `SELLER-PROFILE-TEARDOWN-INVENTORY-S1712.json`, `SELLER-PROFILE-CLEANUP-CHECKPOINT-S1712.json`, `SELLER-PROFILE-DIRECT-CLEANUP-PROOF-S1712.json`, `SELLER-PROFILE-DEFINITION-ABSENCE-S1712.json` |
| Budget and local material audit | Same directory: `SELLER-BOOTSTRAP-BUDGET-REFRESH-S1712.json`, `LOCAL-AUTHORIZATION-AUDIT-S1712.json` |
| Published release | `SELLER-PROFILE-RESULT-WIRE-PUBLISHED-S1712.json` and related source/review/build/merge/deployment receipts |
| Compatibility review and merge | `SELLER-INTEROP-ROUND3-VALIDATION-S1712.json`, `SELLER-INTEROP-DOC-CORRECTION-STATUS-S1712.json`, `SELLER-INTEROP-PR27-MERGE-S1712.json` |
| Joint release dependencies and owner evidence | `SELLER-PRODUCTION-RELEASE-PLAN-S1712.md`, `SELLER-INTEROP-GATE1-AMENDMENT-DRAFT-S1712.md`, `SELLER-MARS-LATEST-RECOVERED-S1712.json`; Mars receipt `/Users/max/koskadeux-state/s1656/s1714-run25-pending-hold-verification.json` |

Successful jobs: A `98c2ff63-74e7-4d2b-9d84-a67bd926a8b7`, B `66d0b846-0176-462e-a9d4-82844950f650`. Evidence: A `1a032af5-a4f6-4f18-b6ea-5babad4184ce`, B `9dde318e-e3f1-4d64-8f86-8508f94f2b7e`. Confirmed absent metadata: `arn:aws:ecs:eu-west-1:948749907373:task-definition/s1653-w3-a-profile:15` and `...:task-definition/s1653-w3-b-profile:9`. Earlier A14/B8 belong to another run and were already fully cleaned.

PR393 baseline pins:

| Artifact | SHA-256 |
|---|---|
| Runtime image | `1eb51f22b220e89993606882c55daa38ee0b3545498cdd4c9f25c39a2d1896af` |
| Signed broker ZIP | `b9bbcb53c6050744bf6d632afa7e0fab8abae616a45752abd0801839b5d76a2e` |
| Signed verifier ZIP | `133c9a6f10c5edacc443479448b386ee4f9716daf7e1986d3a384238e4f7a210` |
| Raw template | `1a55758aa5c1c1be4aa04cda98a470953f3cd8a1e69efdc84ac5765666714b16` |
| Canonical template | `7d8404f2cbec7f94ee215df5fbd03028dcfdd6975305e516c8bf8f1b2a5508c8` |

The image retains the `sha256:` prefix in the ECR URI. Raw/canonical template hashes and unsigned/signed ZIP hashes are not interchangeable. Obtain complete artifact keys and signing receipts from the publication record rather than constructing a plausible key.

Before handing off, state exact deployed identity, active feature gates, last successful user-path proof, all remaining resources/permissions, cumulative allocation, pending operation handles, peer ownership/window, next action and explicit completion criteria. A future instance should be able to continue from this bounded set without guessing credentials, rerunning consumed jobs or declaring an unfinished gate complete.
