---
title: Seller Workspace live release operations
owner: vulcan
last_verified: '2026-09-13'
aliases:
  - Seller Workspace production release
  - AWS profiling cleanup
error_signatures:
  - CannotPullContainerError
  - runtime_image_identity_mismatch
  - worker_step_limit_exceeded
  - profile_result_invalid
---

# Seller Workspace live release operations


## Current approved implementation and published harness — 13 September 2026

GLM and DeepSeek both approved the final implementation with advisory nits and no high or medium findings. Their agreement is approval under the explicit project rule; CC is waived. The [complete owner decision](evidence/workspace-mp255-approval-s1712/OWNER-IMPLEMENTATION-DECISION.json), [raw review and coverage manifest](evidence/workspace-mp255-approval-s1712/MANIFEST.json), and [documentary dispositions](evidence/workspace-mp255-approval-s1712/DOCUMENTARY-DISPOSITION.txt) retain the evidence. DeepSeek's full coverage combines its prior semantic review with the latest corrective review; the latest response alone is not a new review of every requirement.

Backend `2a2e7ae8ec1c2e5cc3f517057533ff637ca20e50` remains the approved candidate, not a claim about deployed production. Environment PR37 is published at `fe02fa858d650e702bd8bcef8e1d195e348cdb33`, with tree `39f305a9dfe919d19895a17a66064d3608a56b07` identical to reviewed candidate `a0e028f4e0fa9ab6e53510909e7e8ddd725f20ae`. Reviewed documentary snapshot `24da40e953109eb71996f1a2ed27116bb84167d0` remains immutable; the later publication records source linkage without changing executed receipts. Earlier dated status and pending-review statements below are historical and superseded by this section.

Qualification reconciled 2,537 backend cases to 2,531 passes and six exact inherited baseline failures, with no missing cases. Final private qualification passed 29 native/shared cases and eight negative custody/mount checks, refund replay, database restoration and owned-resource absence. Final host unit tests passed 55 checks; seed 72 and Compose checks passed. Receiver and test runtimes contain 217 and 221 distributions respectively, with Stripe15.6.1, HTTPX0.28.1 and successful dependency checks. Older 218/222 counts include a warning line. Environment has no hosted workflow; do not report absent CI as a passing hosted run.

The full enabled release remains unfinished. Mars owns the protected settlement sequence and window issuance. Protected run25 must keep its current checkout and pins. Subsequent obligations are genuine settlement/hold phases, exact four-service production cutover, actual AWS profiling, both AWS S3 and credential-based R2 connection/publication/delivery journeys, and joint AIM Data confirmation. R2 profiling is explicitly unavailable and is not required for this release. The USD100 authorization is cumulative; the historical84.8369454546 exposure is not a current bill or new allowance.

### Diagnose, support and upgrade from this checkpoint

Start by separating approved source, published environment and actual deployed identity. Read the [published host procedure](https://github.com/aidotmarket/money-path-test-environment/blob/fe02fa858d650e702bd8bcef8e1d195e348cdb33/workspace/README.md) for the exact command interface, lock, custody and recovery mechanics. Its dated construction/test-count paragraphs are historical; the current qualification and approval above supersede them. Use the [production cutover runbook](seller-production-payment-cutover.md) for deployment controls. Never substitute the published harness merge for an executed protected-runtime pin.

From the actual adopted environment checkout, `rtk proxy bin/workspace-fixture status` reads the fixed authority pointer, journal and backend window without creating authority. Record the checkout SHA, actual versions.env, container/image/source identity, read-only mounts and returned operation/window before interpreting an error. No fixture mutation is authorized merely because status succeeds or a deadline passes. After owner issuance, the normal sequence is open-window, activate, normal authorized public purchase, bind-purchase, normal signed refund, close-window, deactivate; registration must precede refund.

The host journal `.state/workspace-fixture.json` and original receipts under `.state/workspace-windows/<windowUUID>/` retain baseline, opening, registration and terminal evidence. Preserve them for support. A lost receiver response may follow a committed transaction: reconcile the original operation and retry with the same identities, never enroll a replacement credential or reconstruct a baseline. If activation is incomplete or uncertain, keep the window open for recovery; closing first prevents that recovery. A provider denial, timeout or malformed response is not proof of absence. Deactivation restores the owned readiness projection but retains credential custody and financial history. Seed/reset/up deliberately refuse retained lineage; deleting the journal to unblock them is not a supported repair.

For a future upgrade, preserve the accepted contract, full source archive, all original test identities and prior failures. Recheck protected-account cleanup, canonical/legacy caller routing, nullable unique payment binding, signed-event replay, reserved-spend recovery, migration/readiness definitions, bounded provider calls and SDK behavior. Run the complete backend qualification and the environment seed, Compose and host suites at one frozen source, then actual private database/container lifecycle and negative custody/mount checks. Record exact runtime distributions, source hashes, commands, all test phases and owned-resource absence. Compare complete named cases rather than totals alone; advisory documentation fixes do not authorize changing assertions or financial behavior.

The durable raw execution archive remains in `/Users/max/Documents/Codex/2026-09-11/seller-workspace-final-release-continuation/outputs/`. Begin at `SELLER-ENVIRONMENT-IMPLEMENTATION-CURRENT-S1712.json`, the detailed `SELLER-WORKSPACE-DIAGNOSTIC-EVIDENCE-RUNBOOK-S1712.md`, and `seller-combined-implementation-review-final-mp255-v2-s1712/FINAL-MANIFEST.json` (SHA256 `308b82c71802fe2a923f8acbb18437488d4fcf3695f5981df275cbc9490fbe91`). Preserve full raw receipts and use their manifests to retrieve and verify evidence on a future host; the compact committed review records do not replace the complete source/test archives. Do not restore deleted qualification resources using stale container IDs or ports.


The September11 baseline includes successful AWS S3 and Cloudflare R2 seller publication and real paid browser downloads, actual AWS profiling through the normal production application, and verified test cleanup. Those retained results do not establish fresh provider availability or complete the release. The full ordered joint AIM Data/Workspace proof and remaining production gates are still open; refresh actual capabilities and source/image identity before operating. This page supersedes historical W1/W2 availability statements in [the architecture runbook](../seller-workspace-cloud-listing-delivery.md), while preserving its non-custodial and immutable-approval requirements.

## Current project authority — 12 September 2026

Max explicitly authorized continuation without CC. Owner event e4c7e041-4eee-4217-8be5-6591157274ca records this exception for the current S1714 ai.market production objective including Workspace only. Max further clarified: “If GLM and Deepseek agree that is approval.” Agreement by GLM and DeepSeek approving the exact candidate is sufficient approval; no additional CC or user approval is required. This supersedes older prospective CC requirements for this objective. CC is USER-WAIVED and unavailable, never approved. Existing CC findings, complete raw responses and terminal quota failure remain evidence. Historical three-voter receipts below are preserved as history; their CC requirement does not govern current acceptance. No prior vote carries. Sole Mars MP dispatch, full 1990+new testing and source freeze, environment integration, combined review, genuine phases, cutover and enabled AWS S3/Cloudflare R2 proof remain required within the cumulative USD100 authorization. No global Council policy is changed.

For architecture, normal operations, exact API sequencing, diagnosis, safe teardown, upgrades and future-instance handoff, use the [Seller Workspace operator guide](seller-workspace-operator-guide.md). The dated batches below preserve historical authority and failure evidence; the current $100 cumulative authority supersedes older incremental allowances.

## September12 implementation and review boundary

Backendc3 and corrected environment43d67264 have complete implementation acceptance; runbooks PR188 merge0ec6bac7 records those final source/spec pins. Workspace Gate2 candidateb444332a now has unanimous full CC/GLM/DeepSeek design approval with nits and the exact owner decision recorded. The accepted build sequence is backend MP fromc3, then environment43d67264 against actual new backend source. This documentation fold does not claim fixture implementation, an owner window, protected-runtime repin or live acceptance. Read the [current operator procedure and immutable contract](seller-workspace-operator-guide.md#workspace-fixture-design-review-and-recovery-status) for the two-stage order authority, retained credential custody, reset preservation, response collection and future-instance diagnosis.

MP247 has confirmed a fresh-start checkout expectation conflict: inherited canonical-default routing returns200 with both E2E flag values, while the accepted test required false403. The [documentary correction](seller-workspace-operator-guide.md#checkout-branch-correction-under-review) is under review with full raw failure evidence; no product/runtime edit or implementation acceptance follows from it. Independent backend qualification continues.

The dates and earliest-window estimates in historical entries below are not current activation permission. Protected run25 and every required genuine hold/phase remain governed by Mars's explicit lifecycle transition. Current work continues under the existing cumulative $100 authority; no future handoff extension is inferred.

## Final cleanup confirmation

At 17:25:20 UTC AWS returned the exact expected not-found response for task
definitions `s1653-w3-a-profile:15` and `s1653-w3-b-profile:9`. Request IDs are
`03d326c6-a73e-468d-a78c-b57645c05e0f` and
`b5db4161-befd-4da6-9521-74db99c49fe3`. No deletion was resubmitted.
Combined with the previously verified physical, application, template,
permission and local-secret cleanup, the profiling batch is fully cleaned.
The final receipt is
`outputs/profile-result-wire-run-s1712/SELLER-PROFILE-FINAL-CLEANUP-S1712.json`.
The pending-deletion observations below remain dated history.

Mars confirmed the interoperability overlay scope in message 4057.
Environment PR30 merged; PR27 is now rebased to
`ce9506ca02d1b1c29a5045215567d18d688a481b`, candidate
`42ee957715431e2500fa1073849b149592d6cea0`. Six tests and CFN lint passed,
protected baseline paths remain unchanged, and CC/GLM/DeepSeek exact-candidate
Gate 3 review was dispatched. This changes no running environment. The joint
live proof still requires accepted review and Mars's announced post-settlement
window; the earliest stated time is September 14 at 01:30 Madrid.

## Current authorized profiling batch

At 16:20:20 UTC the user explicitly approved up to **$100 for this project**
and asked to stop repeated approval pauses. This supersedes the incremental
profiling allowances below. Continue scoped profiling batches and corrections
within that cumulative cap without requesting another two-job or $5 allowance.
Retain bounded lifetimes and exact cleanup evidence for each batch.

The current result-wire batch uses two fresh verified application connections,
two temporary installations and an operating limit of two logical jobs/four
attempts. Its start cutoff is 18:20:20 UTC and cleanup/temporary permission
expiry is 19:20:20 UTC. These are batch controls, not renewed spend-approval
gates. The conservative cloud allocation is $34.8369454546; reserving the earlier
$50 purchases gives a project total of $84.8369454546, within the cap. Delayed
regional usage is not a final bill and credits are not extra headroom.
The standing application estimate covers 30 days; installations in this batch
must be removed within three hours. No additional purchases, refunds, payouts
or peer environment changes are part of this batch.

At 16:31 UTC the backend and dedicated worker both had profiling enabled,
matching PR393 image/template/verifier/broker pins and a fresh scheduled
heartbeat. Both sources passed normal application verification. Both exact installations passed their installed verifiers, reviewed storage
policies and scratch/image checks. Normal scheduled jobs
`98c2ff63-74e7-4d2b-9d84-a67bd926a8b7` and
`66d0b846-0176-462e-a9d4-82844950f650` succeeded on their first attempts at
16:40 UTC. The application committed evidence
`1a032af5-a4f6-4f18-b6ea-5babad4184ce` and
`9dde318e-e3f1-4d64-8f86-8508f94f2b7e`; normal authenticated evidence GETs returned
200 for both. All semantic, attestation and result-integrity hashes matched,
as did the job, attempt and image bindings.

Each result contains six objects across CSV, TSV, JSON, JSONL and Parquet,
1,333 source bytes, 517 decompressed bytes, 12 rows and 12 fields, with no
truncation. Aggregate semantics are equal after removing only each source's
selector hash and each runtime's field tokens. This proves two successful
scoped connections for the same seller; it does not claim cross-seller proof
or identical-authority repeatability. A request pairing connection A with
runtime B returned 409 and did not create a selector. The generic error text
was “Idempotency key cannot be reused”; source validation rejects the mismatched
connection/runtime binding before insertion.

Both tasks stopped with exit code zero. The application completed both attempt
cleanup records at 16:40:21 UTC. Both connections are revoked, active and
pending credential references are clear and retained encrypted credential
material is zero. Both actual backend and worker flags were verified paused at 16:45 UTC, with
all four reviewed pins and a fresh heartbeat. Core AWS/R2 flags remain enabled.
Original templates match the saved baselines. Direct checks confirm functions,
networks, endpoints, control buckets, secrets, execution roles, event rules and
logs absent, with clusters inactive. Original encryption keys remain enabled
with empty grant lists. Both source buckets were removed and original source
trust restored after fresh proof that all runtime consumers were absent and
both connections revoked. This source cleanup did not alter stack roles or
outstanding deletion requests.

Original execution permissions were restored at 16:54 UTC, with exact template
equality and terminal update events for both policy resources. Temporary local
authorization copies were removed; 59 JSON receipts were audited with no
unredacted sensitive fields. Both original runtime stacks reached `UPDATE_COMPLETE` at 16:57 UTC with
exact baseline templates and directly verified resource absence. Only exact
task-definition records A15/B9 remain in AWS deletion progress. All failed
cleanup events remain recorded; original permissions were not broadened to
hide them. Current receipts:
`outputs/profile-result-wire-run-s1712/`.

## Result-transport correction and previous bootstrap batch

The next approved window began at 15:08:53 UTC with a $35 cumulative cap,
two logical jobs, four attempts and two temporary installations. Both fresh
installations passed the installed verifier and exact scratch-volume checks.
Both scheduled jobs reached the real broker and ECS task, parsed six synthetic
files and wrote cloud results before exiting zero. Each result records 1,333
source bytes, 517 decompressed bytes, 12 rows and 12 fields. The two results
have equal normalized aggregate semantics; their authority and field-token
bindings differ, so this is not identical-authority repeatability proof.

The backend rejected both results before committing application evidence:
strict UUID validation rejected the JSON job-ID string, and the broker emitted
a prefixed image digest where the attestation requires 64 hexadecimal digits.
Jobs `48a88016-3f3b-4d8d-8951-eb5b689a218e` and
`e3afbc4b-a213-48c1-93b1-6e593531f3f9` are cancelled after one attempt each.
Both logical jobs and installations are consumed; unused attempt capacity
does not authorize another job. Profiling admission is false on backend and
profile worker. The start cutoff was 17:08:53 UTC and cleanup/permission expiry
18:08:53 UTC. No purchases, refunds, payouts or peer environment changes were
part of this run.

[Backend PR393](https://github.com/aidotmarket/ai-market-backend/pull/393)
accepts only canonical JSON UUIDs, normalizes the digest to the existing
verifier/backend convention, and adds the integrity-bound completed-file count
to usage. The field named `task_definition_digest` retains its existing image
digest convention; it does not claim a hash of task-definition JSON.
Candidate `6c0e93cbf805b48a7b0c4e589deda6c880378784` passed 159 focused tests;
CC and GLM independently reproduced that result. CC, GLM and DeepSeek approved
with nonblocking notes. All three CI workflows passed, the CI tree equals the
candidate, and both deterministic packages equal the CI artifacts. Merge
`012159b93330ef54951ccd035534d3299f742063` has the exact accepted tree and
preserves Mars PR392. The image, template and verifier are unchanged.

The new signed broker SHA-256 is
`b9bbcb53c6050744bf6d632afa7e0fab8abae616a45752abd0801839b5d76a2e`.
Its versioned signed package contents match the reviewed unsigned package.
At 16:00 UTC all four production services were healthy at the exact merge.
Direct backend and profile-worker reads confirmed all four artifact pins, a
fresh revision-bound scheduled heartbeat, readiness if enabled and admission
false. Core AWS/R2 backend flags remain enabled. All main CI workflows and
public health/schema checks passed. Successful live application acceptance remains required; the later $100
project authorization above covers the fresh scoped batch.

The original runtime stacks and execution permissions are restored with exact
template equality and terminal stack status. Temporary sources, source access,
functions, networks, secrets and logs are removed. Connections are revoked,
retained credentials are zero and local authorization copies are cleared.
Original control keys remain enabled with no grants. Exact task definitions
`s1653-w3-a-profile:14` and `s1653-w3-b-profile:8` were verified absent at
16:20:20 UTC with exact provider responses and request IDs. Cleanup for this
previous bootstrap batch is complete. Receipts, including the final cleanup
record, are under
`outputs/profile-bootstrap-run-s1712/`.

## Previous bootstrap correction and gateway checkpoint

The approved gateway-proof window began at 13:40:15 UTC with a $30 cumulative
ceiling, two logical jobs, four total attempts and two temporary installations.
The start cutoff was 15:40:15 UTC, with cleanup and temporary-permission
expiry set to 16:40:15 UTC. Both fresh runtimes passed the actual installed verifier and
exact gateway-policy readback. Both ECS containers successfully pulled and
started the pinned image, then exited with code 50. Actual task overrides
omitted `W3_CONTROL_BUCKET`, which the entrypoint requires before client setup.
Jobs `574b0591-ca75-41ea-a9ea-643dd263f088` and
`eb36a352-68a4-4fb5-bc00-625a0e4af7c9` are cancelled after one attempt each,
with no profiling evidence. Both logical jobs are consumed; unused attempt
slots do not authorize another logical job. Profiling admission was disabled;
actual backend/worker reads confirmed it false at 14:22 UTC.

[Backend PR391](https://github.com/aidotmarket/ai-market-backend/pull/391),
candidate `c9d091525ff6007fa8a349fea153356401532d2e`, supplies the configured
control bucket and adds one private ephemeral scratch mount for the parsers.
The scratch defect was reproduced locally under the prior read-only image;
the live tasks failed before reaching that stage. The correction retains the
read-only application root, UID/GID 65532, dropped capabilities and resource
limits. The verifier checks the exact volume/mount and refuses alternate
task-definition execution overrides. Local checks passed: 150 focused tests,
template validation, and six synthetic files twice through the real entrypoint
and isolated parser subprocesses. The image test asserts matching semantic
hashes, secret/injection exclusion, read-only root, scratch mode 0700 and
cleanup. Only AWS I/O is mocked. Both final CI workflows passed, including
the actual production-image execution check. CC, GLM and DeepSeek each returned `APPROVE_WITH_NITS`, with no HIGH/MEDIUM
source findings. Merge `1eb127f53003a522e09e588e78acccaa8b06c68d` has the
exact accepted tree. The separately built release image passed a scan with no
high/critical findings, source/configuration binding and full parser execution.
Both signed packages match the reviewed unsigned packages. At 14:52 UTC all
four production services were `SUCCESS` at the accepted merge. Direct backend
and profiling-worker reads confirmed all four artifact pins, readiness if
enabled, a fresh scheduled heartbeat and profiling admission false. Core
AWS/R2 backend flags remain enabled. Public health and schema checks passed.
This is a verified rollout, not a successful live profiling result.

The published image digest is
`sha256:1eb51f22b220e89993606882c55daa38ee0b3545498cdd4c9f25c39a2d1896af`;
canonical template digest is
`7d8404f2cbec7f94ee215df5fbd03028dcfdd6975305e516c8bf8f1b2a5508c8`;
signed broker SHA-256 is
`94bcd91cabbbf41a476191d14321da25b8023d58bf5439970c684cf914ecf3fb`;
signed verifier SHA-256 is
`133c9a6f10c5edacc443479448b386ee4f9716daf7e1986d3a384238e4f7a210`.
Keep the future real AWS volume-format/ownership and successful-result gates.
A read-only pre-deployment database check found zero active profiling jobs,
so no start/reconcile attempt crossed the broker version change.

Both original runtime stacks/templates are restored and `UPDATE_COMPLETE`.
Source buckets and the temporary source policy are removed; original source
trust is restored. Connections are revoked, retained application credential
material is zero, and local authorization copies are cleared. Runtime
networks, functions, secrets and logs are absent; clusters are inactive.
At 14:21:15 UTC the execution-permission stack was `UPDATE_COMPLETE` and its
template exactly matched the original. Exact task definitions
`s1653-w3-a-profile:13` and `s1653-w3-b-profile:7` were both confirmed absent
at 14:40:34 UTC, with the exact provider error and request IDs retained.
Both execution-policy update events completed. Cleanup is complete; the final
receipt is `outputs/profile-gateway-run-s1712/SELLER-PROFILE-FINAL-CLEANUP-S1712.json`.
No new logical job or spending allowance is implied.

### Previous image-layer failure and gateway correction

The next approved S1712 window began at 11:52:07 UTC with a $25 cumulative
ceiling, two logical jobs, four total attempts and two installations; cleanup
and temporary permissions expire at 14:52:07 UTC. Both fresh runtimes passed
the real application verifier. Jobs `09ce800b-f941-45aa-84bf-c2de73fc63e6` and
`3e57f00a-bbed-4001-a87a-76f46db46131` reached ECS at 12:12 UTC, recognized
the pinned image digest, and failed before startup with an image-layer HTTP
error. AWS truncated the stopped reason; the exact HTTP status is unknown.
Both jobs are cancelled after one attempt each, with zero counters and no
evidence output. Both connections are revoked and retain no credential
material. Actual backend and worker admission is false; core AWS/R2 backend
flags remain true. The two-job allowance is consumed.

The live gateway policies restricted image-layer requests to the task execution
role and used role Principals for source/control. AWS documents an exact-role
`aws:PrincipalArn` condition for S3 gateway role restrictions and a read-only
regional ECR layer-bucket statement with `Principal: '*'`.
[Backend PR390](https://github.com/aidotmarket/ai-market-backend/pull/390),
candidate `59f389ee51a5bd8fcc7c7df2710c3e43b476a859`, corrects those three
statements and the matching verifier. The final fold addresses CC's required
singleton-condition normalization and the matching GLM/DeepSeek notes; it
accepts only equivalent scalar/list `ArnEquals.aws:PrincipalArn` forms and
retains rejection of broader or malformed conditions. All 137 focused tests
pass; cfn-lint passed on the identical template. Final CC and DeepSeek returned
`APPROVE_WITH_NITS`; GLM returned `APPROVE`. CC independently reproduced all
137 tests; all three reproduced the 18 narrow gateway cases. GLM/DeepSeek's
full-suite sandbox limitations are disclosed in their responses. Both final
CI workflows passed. Merge `dee543e436cc3c5e81f39d1721e45dcfb98b9244` has
exactly the accepted tree. The signed verifier contents match the unsigned
reviewed package. This is a documented-policy correction, not a successful
live profiling result.

PR390 raw template SHA-256 is
`9d667651d4298db3ad3ffd291e0d7762899a7b4b9dabb02191c80d75dfb77f62`;
canonical template digest is
`8c31a2e81e2c57f5273ebc1f6c400dfbfc3b7d7019e3dcdd139e3ed3c3707a10`;
signed verifier SHA-256 is
`a6f9ea20d3100e4752fb0fc6325ef41fe3b28e0c0b6be413ad246fd2483c1776`.
Broker and runtime image pins are unchanged. The two changed pins have been
applied through Infisical and explicitly to the dedicated worker. Direct reads
at 12:56 UTC show both running services at the merge with all four artifact
pins matching, fresh scheduled heartbeat, readiness if enabled and profiling
admission false. Core AWS/R2 backend flags remain true. At 12:58:50 UTC all
four services report successful deployments at the exact merge. Public health
is healthy with no schema drift. Deployment acceptance does not establish a
successful image pull or profiling result.

At 12:45 UTC both original templates and keys were restored, all runtime
networks/endpoints/functions/secrets/logs were absent, clusters were inactive,
and key grants were empty. Both stacks are `UPDATE_COMPLETE`. Synthetic source
buckets are deleted, the original source-role trust restored, the temporary
policy removed, and local authorization copies removed/redacted. Original
execution permissions were restored through the exact prepared change set after
AWS console reauthentication. At 13:32:02 UTC the stack was `UPDATE_COMPLETE`
and its template exactly matched the original. Both policy resource update
events completed successfully. Direct IAM readback was unavailable to the CLI
identity (`iam:GetPolicy` denied); the retained evidence is the exact template
and terminal CloudFormation resource events. Direct reads at 13:10:29 UTC confirm task
definitions `s1653-w3-a-profile:12` and `s1653-w3-b-profile:6` are both absent
(`Unable to describe task definition.`), with provider request IDs retained.
Cleanup is complete. No new logical job or spending allowance is implied.
Current-run receipts are isolated under
`outputs/profile-dns-run-s1712/`; do not confuse them with the earlier receipts.

### Previous DNS failure and correction

The approved S1712 window began at 10:32:48 UTC with a $20 cumulative ceiling,
two logical jobs, four total attempts and two temporary installations. Both
fresh connections and installed runtimes passed the real application verifier.
Each job selected six small synthetic objects and reached ECS through the
scheduled worker. Both failed before container startup because DNS resolution
of the already-allowed S3 image-layer hostname followed a blocked regional
CNAME target. One attempt each, zero objects/bytes/rows and no evidence output.
Both jobs were cancelled and both connections revoked. The two-job allowance
is consumed; the unused attempt slots do not authorize another logical job.

[Backend PR389](https://github.com/aidotmarket/ai-market-backend/pull/389)
adds the exact region-derived `s3-r-w.<region>.amazonaws.com.` target to the
template and verifier. Candidate `26029e8320fdfd0e47b6149db3dcf50ec23c3fbd`
received CC, GLM and DeepSeek acceptance with only non-blocking nits. All 120
focused checks and cfn-lint passed; CC independently reproduced all 120, and
both CI workflows passed. Merge `fa75b5cfcfc5a7fa24a19ab3ce9300b0f5b45e20`
has exactly the candidate tree. At 11:21 UTC all four Railway services reported
successful deployments at that merge. Direct backend/profile-worker reads
confirmed all four artifact pins, a fresh scheduled heartbeat and profiling
admission false. Public health was healthy without schema drift; core AWS/R2
backend flags remained true. Source approval and this deployment are not
successful profiling proof.

The new raw YAML SHA-256 is
`d834278315a10c0d7faf74d61ffe4a5704dd0436da7e8b0f5885cfd4e795e68a`;
canonical template digest is
`e930719112e2a0cb6a2ba8b8740dc1515a6f7b2bdacac191077b6436a5b24ecd`.
The canonical digest hashes the canonical JSON encoding of the YAML
`TemplateBody` string, matching the verifier's `digest` function; it is not
the raw file hash. The newly signed verifier SHA-256 is
`a8c936054a91ebe6d1264758195dd1f6ae1ce62c72f623597b1ebbd1cb498b9e`.
Broker and runtime image identities are unchanged.

At 11:12 UTC the original execution-role template was restored and
`UPDATE_COMPLETE`, confirmed through the signed-in AWS console and direct
readback. Both source buckets were deleted, original source-role trust
restored and the temporary policy removed. Actual application credential
material retained: zero. Runtime networks, endpoints, DNS controls, functions,
control buckets, secrets, logs and task-execution roles were absent; control-key
grants were empty and the original keys remained enabled. Both bootstrap
stacks were `UPDATE_COMPLETE`. Task definitions `s1653-w3-a-profile:11` and
`s1653-w3-b-profile:5` subsequently finished deletion. Direct reads at 11:41 UTC
confirmed both exact ARNs absent (`Unable to describe task definition.`), with
provider request IDs retained in `SELLER-PROFILE-DEFINITION-ABSENCE-S1712.json`.
The failed S1712 run's cleanup is complete. Successful profiling and the joint
live compatibility proof remain open; cleanup does not renew the consumed
two-job allowance.

### Previous deployment checkpoint

At 2026-09-11 10:15 UTC, backend, ordinary worker, Beat and dedicated profile worker all reported successful deployments of `408f242e0a02306ff625725bfb43d1722b027638`. Public health was healthy with no schema drift. The backend and profile worker had a fresh revision-bound heartbeat and matching reviewed image, template, verifier and broker pins. Profiling admission was false on both. All core AWS/R2 backend flags were true.

[Backend PR388](https://github.com/aidotmarket/ai-market-backend/pull/388) releases a duplicate or deferred delivery's worker slot when it owns no lease. Candidate `19e23710ea063711c00469daa976bc77d89e43fc` received CC, GLM and DeepSeek approval; its merged tree is identical. A read-only check of the running profile worker confirmed the reviewed task-source hash, the 20-second reconcile and 60-second cleanup schedules, application database role `ai_market_app`, no author/owner database DSN and an empty control queue. This is runtime verification of the correction, not a successful cloud profiling run.

[Backend PR387](https://github.com/aidotmarket/ai-market-backend/pull/387), candidate `3e6a8d7239fde5f26ad5b0dfd8a64ff34301b8cf`, received CC, GLM and DeepSeek acceptance and was merged. The final tree `79ded4d4018549c6f84aecfb43024236f61fa688` is exactly the combined tree that passed 117 focused tests and cfn-lint. The signed verifier was published and its exact hash, plus the canonical template digest, propagated through Infisical to the backend and explicitly to the dedicated worker. Both actual runtimes report all four matching artifact pins and readiness if admission were enabled; admission remains false.

The canonical template digest is `d9442e9db652c763ed6b4575ca91fe04876d9958845a04d1f9c8fb0a4d27691d`; raw YAML SHA-256 is `bf2e40de30ab093cbd14a330322055d5be0f7d75d6a161d36feebed8e482f36a`. These are deliberately different representations. The signed verifier SHA-256 is `23d4dc949b87350d7e5ca1c22cc277bb24fc53f23f72a4617f1127cdd0deae04`. Use the signed publication receipt for its immutable S3 object version and signing-job identity.

The retained paid-download receipt records one $25 AWS purchase and one $25 R2 purchase, both delivered through normal Chrome. Their saved 31-byte and 26-byte synthetic files were rehashed on September 11 and still match the receipt. The $50 purchase allowance is consumed; do not repeat purchases. Source credentials were revoked and synthetic listings were unlisted after proof.

Evidence lives in the S1707 and S1712 output directories named in the current `infra:handoff:instance=vulcan` and `infra:seller-workspace-release-s1712` records. Use the bounded primary status/checkpoint/compatibility files there, followed by the exact receipt needed. Historical entries are evidence, not renewed authority.

## When it breaks

After artifact-pin updates, verify both the running commit and all four pins.
During PR391, Infisical's native sync queued backend redeployments from the
previous commit while the merged revision was building. Correct stored values
did not establish the running identity. Once the four backend variables were
read back and profiling remained false, the operator submitted one
`serviceInstanceDeployV2(serviceId, environmentId, commitSha)` for the exact
accepted merge in the existing production service. Keep its returned deployment
ID; inspect the same request after a timeout rather than submitting another.
Require successful deployment plus direct running-version/pin readback before
claiming the rollout is complete. Never substitute a deployment of an unrelated
service or a restart that retains old environment values.

1. Check the exact application job and attempt, deployed backend/worker revision and immutable runtime authorization. A verifier pass proves admission checks; it does not prove that ECS pulled or ran the container.
2. For `CannotPullContainerError`, inspect the exact failed hostname, owned DNS allow list and ECR endpoint's private-DNS state. Preserve the exact-host allow list and block-all rule. Do not add a registry wildcard or broaden provider authority to hide a failure.
   Inspect the complete DNS redirection chain as well as the first name.
   S1712's layer-bucket name was already allowed; public DNS in both supported
   regions resolved it through `s3-r-w.<region>.amazonaws.com`, which was
   missing. The actual source and control bucket names used the same target.
   These are dated public observations, not an in-VPC proof or an AWS promise
   that routing names never change. Before a fresh paid proof, inspect current
   chains; stop for review if another target appears. Preserve
   `INSPECT_REDIRECTION_DOMAIN` and the resource-scoped S3 endpoint/IAM policies.
   AWS requires subsequent chain names to be allowed in
   [DNS Firewall rule settings](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-rule-settings.html).
   Once DNS works, inspect the actual S3 gateway policy for a layer HTTP error.
   [AWS's ECR example](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)
   scopes `s3:GetObject` to `prod-<region>-starport-layer-bucket/*` with
   `Principal: '*'`. Preserve source/control exact roles using
   [the documented ArnEquals aws:PrincipalArn condition](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html).
   A gateway policy does not replace IAM or bucket policies. Do not widen source
   access or live-edit an immutable authorized installation to repair a failure.
3. For heartbeat starvation, distinguish the actual lease owner from duplicate/deferred deliveries. The owner continues polling; an unowned delivery returns so reconciliation and heartbeat work can run. Preserve the existing lease and scheduling rules.
4. Obtain exact source review under [Council](council.md), resolve required findings and check CI. Merge with the expected candidate head; verify the merged source and combined changes. Preserve peer worktrees and deployments.
5. Any changed broker or verifier requires a newly signed, versioned package and fresh immutable runtime authorizations. A template change also requires a new exact template digest. Verify package contents, signatures, hashes and CI source identity before applying only the changed canonical configuration. Preserve every unchanged artifact pin and prove no active jobs cross the change.
6. Follow [Infisical](../infisical-secrets.md) and [Local SecOps](../local-secops.md); never print values. Check actual backend and dedicated-worker propagation, deployment identities and scheduled heartbeat before reopening profiling admission.

AWS explicitly requires subdomains to be included separately in a DNS Firewall list. See the note after step 20 in [AWS's DNS Firewall example](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-getting-started.html). The retained incident receipt also confirms that both ECR Docker endpoints had private DNS enabled; live success with the correction still requires a new authorized run.

## Bounded live proof and cleanup

The September 11 08:46:43 UTC allowance was $15 cumulative, two logical jobs, four attempts and two temporary installations. Both logical jobs were consumed, with pre-start failures and zero output. That historical allowance did not authorize another job. The later $100 project authorization now governs further scoped profiling. Refresh usage and retained reservations before each batch, and preserve completed purchase proofs.

For each batch within the current authorized cap, record its exact start cutoff, cleanup deadline, operating job/attempt limits and temporary permission expiry. Use fresh real application connections and authorizations, approved synthetic sources and the ordinary scheduled worker/broker/task path. Record actual evidence results and isolation checks. Installation, local tests, signed packages and failed starts are separate from successful profiling.

Restore only the exact owned test resources and original permissions. Preserve pre-existing stacks, roles and keys. Disable mutation protection only on the owned DNS association during authorized teardown, remove that association before its network, wait for terminal CloudFormation status and then inspect the actual remaining resources. Revoke only positively identified test grants; remove temporary sources and credential material.

The retained execution role can report cleanup permission failures even after
an owned DNS association was removed directly. S1712 also found that its
task-definition deregistration path lacked permission. Preserve these events;
do not broaden that role to obtain a clean label. Use already-authorized
operator cleanup for the exact task definitions read from current stack
outputs, then verify actual absence separately from terminal stack status.
Do not infer task-definition family names from an older receipt.

At 10:14 UTC both original bootstrap templates and keys were restored; functions, VPCs, endpoints and DNS resources were absent; clusters were inactive. Both former task definitions `s1653-w3-a-w3-profile:10` and `s1653-w3-b-w3-profile:4` were confirmed absent. This supersedes the earlier deletion-in-progress observation. The S1712 previous-run cleanup receipt preserves the direct inspection.

## Compatibility and completion

Workspace and AIM Data/VZ share marketplace listings and versions, with origin-specific mutation rules. Legacy mutation routes reject changing Workspace-approved versions. Buyer rights remain bound to the purchased immutable version, entitled buyer, access window and current refund/revocation state.

Confirm the deployed AIM Data contract and the smallest meaningful cross-interface proof with Mars. Existing focused integration results do not constitute joint sign-off; their broader legacy serial-fixture failure remains disclosed. The proposed buyer-download unification is separately gated and does not expand this release work.

Full completion requires evidence for both provider journeys, successful actual profiling, exact deployment identities, permissions and cleanup, joint compatibility and current indexed documentation. Report each requirement honestly; do not promote a passing intermediate check into full release completion.


### Proposed recovery and verification revision after c6bae

The complete checkout-correction panel requires revision; no new implementation/runtime is accepted. The [current design appendix](../specs/SELLER-WORKSPACE-ACTIVATION-S1712-GATE2.md) proposes an exact registered-Order discovery reference to prevent terminal suppression after binding drift, explicit pending/unknown refund closure refusal and a narrowly scoped three-test compatibility repair (seventeen total backend targets only after acceptance). The original forged-N suppression behavior and all paid-rights/hold/provider requirements remain. See the [detailed diagnostic evidence runbook](evidence/workspace-gate2-s1712/MP247-DIAGNOSTIC-EVIDENCE-RUNBOOK.txt) for exact source identities, baseline diagnosis, archive handling, remaining checks and continuation instructions. Raw historical failures stay preserved; full fresh review and execution precede any release claim.


## Current continuation status

Read the [authoritative operator continuation status](seller-workspace-operator-guide.md#authoritative-continuation-status) for the current candidate, qualification and remaining gates, and the [complete design contract](../specs/SELLER-WORKSPACE-ACTIVATION-S1712-GATE2.md) for implementation/recovery rules. Apply this release procedure only after its required source, review, environment, genuine-phase and provider evidence is verified.
