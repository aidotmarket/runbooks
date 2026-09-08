---
title: Seller Workspace provider verification
owner: unassigned
last_verified: '2026-09-08'
aliases: []
error_signatures:
  - 'HTTP 403 / Cloudflare error 1010 at oauth2/token'
---

# Seller Workspace provider verification

Read seller-workspace-cloud-listing-delivery.md, infisical-secrets.md and the provider runbook before work. This document records development evidence, not public availability or permission to change provider settings.

## Folder selection acceptance (September 8 requirement; delivery scale still pending)

Max reported that the first customer had 22,000 files in one folder. Treat 22,000 files as a required acceptance case, not a maximum. Sellers must be able to combine individual files and complete folders, including subfolders, then confirm the exact file count and total size before saving. Deduplicate overlapping choices. Counting uses object metadata only; it does not read file contents or invoke profiling or Allai.

Show progress while enumerating and a concise summary with a paged file preview. Confirmation remains unavailable until enumeration completes. A failed page, access failure, or explicit capacity boundary must never become a silently accepted partial selection. Changing the selection invalidates confirmation. Persist the confirmed object identities as the immutable source snapshot; later additions to the folder require a new selection and confirmation.

Required evidence includes a synthetic 22,000-file nested folder, overlapping file/folder choices, exact count and byte total, later-page failure, responsive browser rendering, save/reload, approval/publication and complete buyer delivery. Measure provider calls, request sizes and runtime through those stages. Passing a small folder test or increasing a schema limit is insufficient. Current two-file AWS proof does not establish this capacity. Use local synthetic fixtures first; the existing AWS authorization covers only the three tiny fixture objects, not a new 22,000-object provider fixture.

### September 8 large-folder development evidence

Source manifests now have explicit 50,000-file and 64 MB metadata bounds. Folder enumeration reports metadata count/size progress, deduplicates identical overlaps, rejects changed duplicates and incomplete pages, and waits 60 seconds after a pre-discovery HTTP429 before retrying the same cursor (at most three retries). Unknown network/provider outcomes are not retried with a potentially consumed cursor. The source-only endpoint accepts up to 1,000 metadata rows; profiling retains its 100-row page boundary. Large source validation uses a common-folder metadata scan with exact key/version/ETag/size comparison, at most 1,000 provider pages; it never silently accepts unchecked files. This is not yet a durable background scan: leaving the page stops further enumeration.

A PostgreSQL service test saved and reloaded all 22,000 nested synthetic file identities, counted exactly 242,011,000 bytes and made 22 metadata-list calls. Later-page changed/missing/out-of-scope records, repeated cursors and provider failure leave no saved source or save audit. Source/approval/publication/delivery regression tests: 67 passed; adapter/source discovery tests: 31 passed, including the 1,000-row HTTP response and unchanged profiling page boundary.

Normal Chrome tabs1702607580 and1702607583 at http://127.0.0.1:4341 verified counting progress with save disabled, then 22,000 files totaling 21.5 MB (22,528,000 exact bytes), explicit confirmation, actual encrypted source-service save, and a fresh page reload retaining every file. Selected and review previews render 50 filenames per page. The exact saved synthetic Regional Retail Sales listing ($30.00, Research use, no public sample) was reviewed, explicitly approved and published via actual services in an isolated PostgreSQL database, listing7c64a154-3aa7-42fb-9517-471b62d3311d. Allai stayed visible. Discovery/provider, authentication and KMS are local synthetic seams; no 22,000-object cloud fixture or production publication occurred. Frontend focused tests: 44 passed; TypeScript validation passed.

Large-folder buyer delivery remains unproven end to end. The delivery work below removes the repeated full-source and growing-map work; actual HTTP-limit and browser/cloud proof is still required before declaring the acceptance case complete. Existing real AWS browser transfer evidence covers only the two selected fixture files.

### September 8 large-folder delivery implementation

Delivery grants are now immutable encrypted rows keyed by session/file index. Migration005 copies old envelopes without decryption and retains the legacy map for a reversible downgrade. New legacy-map writes are rejected, so older application writers fail closed after the migration; coordinate application/migration rollout with the feature disabled. Existing indexed grants cannot be updated or deleted. Downgrade restores all indexed envelopes before dropping the new table. No production migration has been applied.

Migration006 adds immutable encrypted approved-source chunks (64 identities each, at most 1 MB plaintext per chunk). The first new download builds the complete derived index transactionally from the hash-verified frozen approval, with at most eight concurrent KMS operations. Subsequent file requests recheck the live purchased-version authority and decrypt only their chunk. The encrypted payload binds approval, connection/version, manifest hash, chunk position, full object count and full byte total. A partial or mismatched index fails closed; pre-index sessions may read their original frozen snapshot. The index holds metadata only, not file bodies. Tests caught an ORM identity-map stale read; current source chunks, listing versions and authority rows are explicitly refreshed from the database.

The actual PostgreSQL delivery-service test issued every one of 22,000 synthetic file grants with one download allowance and 344 encrypted source chunks; reopening the full frozen source during individual file requests was forbidden by the test. Provider and KMS were synthetic, so elapsed time is not real-cloud performance evidence. Separate browser-stream unit coverage wrote all 22,000 synthetic 42-byte files (924,000 bytes) through one bundle, with one writer open at a time and 22,000 unique filenames. This is not normal-Chrome or real-storage transfer proof.

The full 22,000-file browser/cloud acceptance remains open. In particular, HTTP file-grant requests still share the existing ten-per-minute caller budget, and the buyer client does not yet pause/retry rate rejections. Resolve a bounded, appropriate delivery request budget and visible retry behavior, then test through actual HTTP limits and normal Chrome. Preserve purchase allowances, entitlement/revocation checks, per-file freshness and the no-remint-after-expiry rule. The existing three-object AWS authorization does not authorize a new bulk object fixture.

## Cloudflare OAuth

The private development client is db7c0057a307855bb73914fb58723ad8, in account d5346d3e0f8f344c5f4915aaca689adf. Max approved creation and subsequently approved the exact account-level read scopes workers-r2.read and workers-r2-bucket-item.read. Do not ask again for that same consent. Normal Chrome completed consent and redirected to the exact local callback with a code.

The token endpoint https://dash.cloudflare.com/oauth2/token rejected Client Secret Basic exchange with HTTP 403. A diagnostic request with a synthetic invalid code returned text/plain error1010 rather than an OAuth JSON error. No tokens were acquired and no stored files read. This is not evidence of an incorrect secret. Resolve supported server-client access with the endpoint owner. Do not change ai.market zone security or recreate/rotate the client speculatively. Cloudflare documents error1010 at https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/.

Infisical target: ai-market-backend project bd272d48-c5a1-4b52-9d24-12066ae4403c, prod, root /. Max chose STAGING_CLOUDFLARE_SELLER_OAUTH_CLIENT_SECRET and STAGING_CLOUDFLARE_SELLER_OAUTH_CLIENT_ID. The secret was retrieved nonempty through CLI without displaying it. ID lookup returned empty; the public registered ID is known. The STAGING prefix is not access isolation.

## AWS synthetic environment discovery

Read-only verification on September 8 found the e2e/test_buckets.json configuration inconsistent with this host's Infisical prod catalog. Its E2E_S3_ACCESS_KEY_ID, E2E_S3_SECRET_ACCESS_KEY and E2E_S3_REGION entries returned empty. Existing E2E_AWS_ACCESS_KEY_ID, E2E_AWS_SECRET_ACCESS_KEY and E2E_AWS_REGION were nonempty.

STS identified arn:aws:iam::157263244532:user/aimarket-e2e-harness. Infisical E2E_AWS_ACCOUNT_ID matches 157263244532; E2E_AWS_BUCKET_PREFIX is aimarket-e2e-. This is a separate test account from the older aws.md account948749907373. Stop if caller identity does not match the explicitly configured test account.

A bounded ListBuckets(Prefix=aimarket-e2e-, MaxBuckets=20) returned no buckets and no continuation token. No object listings, reads, writes, deletes, IAM or bucket setting changes occurred. This does not prove the account contains no buckets outside the configured prefix. The earlier ai-market-e2e-s3-test fixture cannot be silently substituted for a missing verified fixture. Do not change the shared cleanup configuration merely to match credential names: it also controls destructive teardown, and its exact account/bucket/prefix ownership must be established first.

## Next required evidence

1. Resolve the Cloudflare token endpoint's supported server-client access, then repeat a fresh one-use authorization attempt within existing consent scope. Verify token audience/expiry/refresh, bucket binding, revocation and the approved direct-delivery authority before enabling R2.
2. Complete the dedicated synthetic AWS fixture under Max’s September 8 authorization, then verify exact-prefix read restrictions and browser CORS. This authorization covers the prepared bucket, read role, and three tiny synthetic files only.
3. Verify the full Chrome seller-to-buyer transfer against that fixture. Unit tests and catalog metadata do not substitute for provider or browser proof.

Keep AWS/R2 product flags off until release evidence and authorization are complete. Never expose credentials or signed URLs in runbooks, support messages or test outputs.

## When it breaks

- Cloudflare HTTP403/error1010: preserve redacted status and endpoint evidence, and use the supported endpoint-owner escalation above. Do not infer invalid credentials.
- Empty Infisical lookup: verify explicit project, environment, path and exact name; exit code zero is insufficient.
- AWS identity differs from E2E_AWS_ACCOUNT_ID: stop before bucket access and reconcile the intended account.
- No buckets under the configured test prefix: prepare an authorized synthetic fixture; do not broaden discovery or substitute customer storage.

## Authorized AWS fixture (created and provider-verified)

Backend e2e/seller_workspace_aws_fixture.json defines one private SSE-S3 versioned bucket aimarket-e2e-seller-workspace-157263244532 and role aimarket-e2e-seller-workspace-read, conditional on test account157263244532 and us-east-1. The role trusts only the verified aimarket-e2e-harness user with the exact synthetic connection ExternalId. It may list/read only the e2e/seller-workspace/ prefix (plus bucket location); it has no write/delete permission. Browser GET/If-Match CORS is limited to the current two local preview origins and https://ai.market. The retained bucket has no automatic deletion.

Max explicitly authorized provisioning and logged normal Chrome into Testing ai.market (157263244532). On September 8, Infrastructure Composer validated the exact template successfully. CloudFormation stack aimarket-e2e-seller-workspace was submitted in us-east-1, stack ID 243703d0-ab73-11f1-86cf-0e1eff443ba3. Normal Chrome confirmed CREATE_COMPLETE for the stack and both resources. Reading the deployed Template tab and parsing its displayed JSON proved it exactly matches the prepared template. The existing e2e harness CLI identity was independently reverified but lacks cloudformation:ValidateTemplate; no broader credentials or policy grants were added. Composer saved its template in the existing cf-templates--luu7jak35ei2-us-east-1 bucket. The role ExternalId comes from actual create_pending in an isolated synthetic connection service. The proof uses a local test repository/wrapping key and test-only IAM-user principal configuration; it is not production KMS, persistence, or configuration proof. Do not change the shared cleanup fixture configuration until ownership and the intended teardown scope are separately established.

### September 8 provider and delivery results

The actual connection service reached verified for synthetic connection b330c744-e0a3-4ee9-88d7-a3714f7ca315. It first refused the empty prefix with scope_has_no_proof_object. Three approved synthetic files were then created with conditional writes: regional-sales.csv (55 bytes), store-counts.csv (31 bytes), and the outside-prefix denied.csv (38 bytes). Read-role access to the two selected files passed; wrong ExternalId, outside-prefix listing and outside-prefix GET returned AccessDenied, while wrong If-Match returned PreconditionFailed. No write/delete permissions were added to the read role.

The harness identity can read public-access settings but cannot inspect encryption/versioning/ownership/CORS through CLI. Normal Chrome independently confirmed versioning Enabled, SSE-S3 encryption, Bucket owner enforced ownership, all public access blocked, and the exact configured GET/If-Match/ETag CORS rules. These console checks do not require expanding the harness policy.

An isolated local preview used real source validation, review, approval, publication, download-session and per-file delivery services with a synthetic unpaid test order and real AWS storage. HTTP smoke verified both exact file hashes and the expected Access-Control-Allow-Origin through actual signed S3 links, consuming one bundle allowance. This is provider/service evidence, not browser-transfer proof. Normal Chrome rendered the actual buyer download component at http://127.0.0.1:4330/buyer-live.html; automated folder-picker handling returned cancellation. Max subsequently selected /Users/max/Downloads/vectoraiz-test-data in normal Chrome. Two resulting ai-market-* directories each contain both selected CSV files with exact SHA-256 matches. Download records show one allowance per two-file bundle: one earlier HTTP smoke plus two browser transfers. The later observed cancellation message is not proof of a partial transfer; the saved files and grant records establish both full transfers. Local test login/KMS/configuration and stub foreign-key tables remain explicit test seams; no production flags, payments, credentials or database were changed.
