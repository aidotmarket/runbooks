---
title: Seller Workspace live release operations
owner: vulcan
last_verified: '2026-09-11'
aliases:
  - Seller Workspace production release
  - AWS profiling cleanup
error_signatures:
  - CannotPullContainerError
  - runtime_image_identity_mismatch
  - worker_step_limit_exceeded
---

# Seller Workspace live release operations

AWS S3 and Cloudflare R2 seller publication and real paid browser downloads have passed in production. Full release completion still requires successful actual AWS profiling and joint AIM Data compatibility confirmation. Profiling admission is paused; the core seller features remain enabled. This page supersedes historical W1/W2 availability statements in [the architecture runbook](../seller-workspace-cloud-listing-delivery.md), while preserving its non-custodial and immutable-approval requirements.

## Verified checkpoint

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
5. A changed verifier/template requires newly signed, versioned artifacts and fresh immutable runtime authorizations. Verify package contents, signatures and hashes before applying only the changed canonical configuration. Keep the unchanged broker and runtime image pinned.
6. Follow [Infisical](../infisical-secrets.md) and [Local SecOps](../local-secops.md); never print values. Check actual backend and dedicated-worker propagation, deployment identities and scheduled heartbeat before reopening profiling admission.

AWS explicitly requires subdomains to be included separately in a DNS Firewall list. See the note after step 20 in [AWS's DNS Firewall example](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-getting-started.html). The retained incident receipt also confirms that both ECR Docker endpoints had private DNS enabled; live success with the correction still requires a new authorized run.

## Bounded live proof and cleanup

The September 11 08:46:43 UTC allowance was $15 cumulative, two logical jobs, four attempts and two temporary installations. Both logical jobs were consumed, with pre-start failures and zero output. It does not authorize another job. Prepare the concrete reviewed corrections and fresh usage/budget evidence before requesting an appropriate new bounded allowance. Preserve completed purchase proofs.

After any new allowance, freeze its exact start cutoff, cleanup deadline, job/attempt limits and temporary permission expiry. Use fresh real application connections and authorizations, approved synthetic sources and the ordinary scheduled worker/broker/task path. Record actual evidence results and isolation checks. Installation, local tests, signed packages and failed starts are separate from successful profiling.

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
