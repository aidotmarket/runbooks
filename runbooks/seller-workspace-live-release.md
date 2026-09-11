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

At 2026-09-11 10:15 UTC, backend, ordinary worker, Beat and dedicated profile worker all reported successful deployments of `408f242e0a02306ff625725bfb43d1722b027638`. Public health was healthy with no schema drift. The backend and profile worker had a fresh revision-bound heartbeat and matching reviewed image, template, verifier and broker pins. Profiling admission was false on both. All core AWS/R2 backend flags were true.

[Backend PR388](https://github.com/aidotmarket/ai-market-backend/pull/388) releases a duplicate or deferred delivery's worker slot when it owns no lease. Candidate `19e23710ea063711c00469daa976bc77d89e43fc` received CC, GLM and DeepSeek approval; its merged tree is identical. A read-only check of the running profile worker confirmed the reviewed task-source hash, the 20-second reconcile and 60-second cleanup schedules, application database role `ai_market_app`, no author/owner database DSN and an empty control queue. This is runtime verification of the correction, not a successful cloud profiling run.

[Backend PR387](https://github.com/aidotmarket/ai-market-backend/pull/387), candidate `3e6a8d7239fde5f26ad5b0dfd8a64ff34301b8cf`, received CC, GLM and DeepSeek acceptance and was merged. The final tree `79ded4d4018549c6f84aecfb43024236f61fa688` is exactly the combined tree that passed 117 focused tests and cfn-lint. The signed verifier was published and its exact hash, plus the canonical template digest, propagated through Infisical to the backend and explicitly to the dedicated worker. Both actual runtimes report all four matching artifact pins and readiness if admission were enabled; admission remains false.

The canonical template digest is `d9442e9db652c763ed6b4575ca91fe04876d9958845a04d1f9c8fb0a4d27691d`; raw YAML SHA-256 is `bf2e40de30ab093cbd14a330322055d5be0f7d75d6a161d36feebed8e482f36a`. These are deliberately different representations. The signed verifier SHA-256 is `23d4dc949b87350d7e5ca1c22cc277bb24fc53f23f72a4617f1127cdd0deae04`. Use the signed publication receipt for its immutable S3 object version and signing-job identity.

The retained paid-download receipt records one $25 AWS purchase and one $25 R2 purchase, both delivered through normal Chrome. Their saved 31-byte and 26-byte synthetic files were rehashed on September 11 and still match the receipt. The $50 purchase allowance is consumed; do not repeat purchases. Source credentials were revoked and synthetic listings were unlisted after proof.

Evidence lives in the S1707 and S1712 output directories named in the current `infra:handoff:instance=vulcan` and `infra:seller-workspace-release-s1712` records. Use the bounded primary status/checkpoint/compatibility files there, followed by the exact receipt needed. Historical entries are evidence, not renewed authority.

## When it breaks

1. Check the exact application job and attempt, deployed backend/worker revision and immutable runtime authorization. A verifier pass proves admission checks; it does not prove that ECS pulled or ran the container.
2. For `CannotPullContainerError`, inspect the exact failed hostname, owned DNS allow list and ECR endpoint's private-DNS state. Preserve the exact-host allow list and block-all rule. Do not add a registry wildcard or broaden provider authority to hide a failure.
3. For heartbeat starvation, distinguish the actual lease owner from duplicate/deferred deliveries. The owner continues polling; an unowned delivery returns so reconciliation and heartbeat work can run. Preserve the existing lease and scheduling rules.
4. Obtain exact source review under [Council](council.md), resolve required findings and check CI. Merge with the expected candidate head; verify the merged source and combined changes. Preserve peer worktrees and deployments.
5. A changed verifier/template requires newly signed, versioned artifacts and fresh immutable runtime authorizations. Verify package contents, signatures and hashes before applying only the changed canonical configuration. Keep the unchanged broker and runtime image pinned.
6. Follow [Infisical](../infisical-secrets.md) and [Local SecOps](../local-secops.md); never print values. Check actual backend and dedicated-worker propagation, deployment identities and scheduled heartbeat before reopening profiling admission.

AWS explicitly requires subdomains to be included separately in a DNS Firewall list. See the note after step 20 in [AWS's DNS Firewall example](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-getting-started.html). The retained incident receipt also confirms that both ECR Docker endpoints had private DNS enabled; live success with the correction still requires a new authorized run.

## Bounded live proof and cleanup

The September 11 08:46:43 UTC allowance was $15 cumulative, two logical jobs, four attempts and two temporary installations. Both logical jobs were consumed, with pre-start failures and zero output. It does not authorize another job. Prepare the concrete reviewed corrections and fresh usage/budget evidence before requesting an appropriate new bounded allowance. Preserve completed purchase proofs.

After any new allowance, freeze its exact start cutoff, cleanup deadline, job/attempt limits and temporary permission expiry. Use fresh real application connections and authorizations, approved synthetic sources and the ordinary scheduled worker/broker/task path. Record actual evidence results and isolation checks. Installation, local tests, signed packages and failed starts are separate from successful profiling.

Restore only the exact owned test resources and original permissions. Preserve pre-existing stacks, roles and keys. Disable mutation protection only on the owned DNS association during authorized teardown, remove that association before its network, wait for terminal CloudFormation status and then inspect the actual remaining resources. Revoke only positively identified test grants; remove temporary sources and credential material.

At 10:14 UTC both original bootstrap templates and keys were restored; functions, VPCs, endpoints and DNS resources were absent; clusters were inactive. Both former task definitions `s1653-w3-a-w3-profile:10` and `s1653-w3-b-w3-profile:4` were confirmed absent. This supersedes the earlier deletion-in-progress observation. The S1712 previous-run cleanup receipt preserves the direct inspection.

## Compatibility and completion

Workspace and AIM Data/VZ share marketplace listings and versions, with origin-specific mutation rules. Legacy mutation routes reject changing Workspace-approved versions. Buyer rights remain bound to the purchased immutable version, entitled buyer, access window and current refund/revocation state.

Confirm the deployed AIM Data contract and the smallest meaningful cross-interface proof with Mars. Existing focused integration results do not constitute joint sign-off; their broader legacy serial-fixture failure remains disclosed. The proposed buyer-download unification is separately gated and does not expand this release work.

Full completion requires evidence for both provider journeys, successful actual profiling, exact deployment identities, permissions and cleanup, joint compatibility and current indexed documentation. Report each requirement honestly; do not promote a passing intermediate check into full release completion.
