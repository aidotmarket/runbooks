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

## S1691 production catalog preflight — seller migration not applied

At September 9 01:23 UTC, bounded catalog-only checks through the existing web
and normal-worker application DSNs independently found all nine seller release
relations absent from `public`: `seller_assistant_requests`,
`seller_listing_drafts`, `seller_listing_sources`, `seller_listing_approvals`,
`seller_listing_publications`, `seller_download_sessions`,
`seller_download_file_grants`, `seller_approved_source_chunks` and
`seller_listing_search_outbox`. These are the eight mapped tables and SQL outbox
required by held backend `3e473b9972c5704a3b2874829310cf23b801f5e7` admission.
The check used `pg_catalog`, not privilege-filtered `information_schema`, and
read no application rows. Both transactions reported read-only and rolled back.
No application module, migration, worker task, provider or KMS operation ran.

Both observed application roles have public USAGE but no public CREATE,
superuser, CREATEDB, CREATEROLE or BYPASSRLS privilege. The web environment has
an author DSN; the worker environment does not. Only presence booleans were
recorded; the author DSN was not used. Absence of the nine relations means their
write ACLs, types, constraints and triggers cannot yet be certified. This check
does not inspect future default privileges or certify every external consumer.

The inspected processes still run production main
`1c96b257c34938ea547be1eb818d5e902ff49f56`, at web deployment
`2357f6b8-5771-4725-93e8-f86c8499d752` and worker deployment
`25cf4705-d2fe-408f-bd1f-30f92f7b2b1a`. Railway also retains Beat deployment
`4d3a99e5-0b21-4920-a192-935ec965f3c5` at the same main. Public health is
healthy/apscheduler with no reported drift for that deployed model set. This
does not establish readiness for the different held seller model set.

Before an authorized rollout, apply and verify the reviewed schema through the
separate owner migration path, with incompatible writers excluded. Verify the
actual application-role read/write permissions and integrity objects before
admitting each compatible web/worker. Never grant application DDL, give Beat a
database credential, or bypass admission to resolve this finding. The assistant
table remains an unconditional billing floor even when Workspace is disabled.
No production migration, grant, deployment or flag change was authorized here.

Exact queries, redacted results, identities and inherited seal verification:
`seller-aws-r2-release-continuation/outputs/SELLER-CATALOG-*.json` and
`SELLER-OPEN-VERIFICATION.json`. The S1690 scheduler approvals and held integration
remain accepted. R2 authority/implementation, enabled release, production KMS,
recovery/rolling fleet, scheduler liveness/alerting and accepted capacity remain
open. The existing support-send and launch-demand questions remain pending.

## Folder selection acceptance (September 8 requirement; synthetic delivery verified)

Max reported that the first customer had 22,000 files in one folder. Treat 22,000 files as a required acceptance case, not a maximum. Sellers must be able to combine individual files and complete folders, including subfolders, then confirm the exact file count and total size before saving. Deduplicate overlapping choices. Counting uses object metadata only; it does not read file contents or invoke profiling or Allai.

Show progress while enumerating and a concise summary with a paged file preview. Confirmation remains unavailable until enumeration completes. A failed page, access failure, or explicit capacity boundary must never become a silently accepted partial selection. Changing the selection invalidates confirmation. Persist the confirmed object identities as the immutable source snapshot; later additions to the folder require a new selection and confirmation.

Required evidence includes a synthetic 22,000-file nested folder, overlapping file/folder choices, exact count and byte total, later-page failure, responsive browser rendering, save/reload, approval/publication and complete buyer delivery. Measure provider calls, request sizes and runtime through those stages. Passing a small folder test or increasing a schema limit is insufficient. Current two-file AWS proof does not establish this capacity. Use local synthetic fixtures first; the existing AWS authorization covers only the three tiny fixture objects, not a new 22,000-object provider fixture.

### September 8 large-folder development evidence

Source manifests now have explicit 50,000-file and 64 MB metadata bounds. Folder enumeration reports metadata count/size progress, deduplicates identical overlaps, rejects changed duplicates and incomplete pages, and waits 60 seconds after a pre-discovery HTTP429 before retrying the same cursor (at most three retries). Unknown network/provider outcomes are not retried with a potentially consumed cursor. The source-only endpoint accepts up to 1,000 metadata rows; profiling retains its 100-row page boundary. Large source validation uses a common-folder metadata scan with exact key/version/ETag/size comparison, at most 1,000 provider pages; it never silently accepts unchecked files. This is not yet a durable background scan: leaving the page stops further enumeration.

A PostgreSQL service test saved and reloaded all 22,000 nested synthetic file identities, counted exactly 242,011,000 bytes and made 22 metadata-list calls. Later-page changed/missing/out-of-scope records, repeated cursors and provider failure leave no saved source or save audit. Source/approval/publication/delivery regression tests: 67 passed; adapter/source discovery tests: 31 passed, including the 1,000-row HTTP response and unchanged profiling page boundary.

Normal Chrome tabs1702607580 and1702607583 at http://127.0.0.1:4341 verified counting progress with save disabled, then 22,000 files totaling 21.5 MB (22,528,000 exact bytes), explicit confirmation, actual encrypted source-service save, and a fresh page reload retaining every file. Selected and review previews render 50 filenames per page. The exact saved synthetic Regional Retail Sales listing ($30.00, Research use, no public sample) was reviewed, explicitly approved and published via actual services in an isolated PostgreSQL database, listing7c64a154-3aa7-42fb-9517-471b62d3311d. Allai stayed visible. Discovery/provider, authentication and KMS are local synthetic seams; no 22,000-object cloud fixture or production publication occurred. Frontend focused tests: 44 passed; TypeScript validation passed.

The synthetic 22,000-file acceptance case now includes complete native Chrome delivery through the actual HTTP service, PostgreSQL and Redis, as recorded below. Real-cloud bulk transfer remains unverified; existing real AWS browser transfer evidence covers only the two selected fixture files.

### September 8 large-folder delivery implementation

Delivery grants are now immutable encrypted rows keyed by session/file index. Migration005 copies old envelopes without decryption and retains the legacy map as historical evidence. New legacy-map writes are rejected, so older application writers fail closed after the migration; coordinate application/migration rollout with the feature disabled. Existing indexed grants cannot be updated or deleted. The S1673 candidate prohibits downgrade when seller records exist; it preserves indexed envelopes, legacy evidence and integrity guards. No production migration has been applied.

Migration006 adds immutable encrypted approved-source chunks (64 identities each, at most 1 MB plaintext per chunk). The first new download builds the complete derived index transactionally from the hash-verified frozen approval, with at most eight concurrent KMS operations. Subsequent file requests recheck the live purchased-version authority and decrypt only their chunk. The encrypted payload binds approval, connection/version, manifest hash, chunk position, full object count and full byte total. A partial or mismatched index fails closed; pre-index sessions may read their original frozen snapshot. The index holds metadata only, not file bodies. Tests caught an ORM identity-map stale read; current source chunks, listing versions and authority rows are explicitly refreshed from the database.

The actual PostgreSQL delivery-service test issued every one of 22,000 synthetic file grants with one download allowance and 344 encrypted source chunks; reopening the full frozen source during individual file requests was forbidden by the test. Provider and KMS were synthetic, so elapsed time is not real-cloud performance evidence. Separate browser-stream unit coverage wrote all 22,000 synthetic 42-byte files (924,000 bytes) through one bundle, with one writer open at a time and 22,000 unique filenames. This is not normal-Chrome or real-storage transfer proof.

### September 8 HTTP delivery rate handling (S1666)

Per-file grants now use a separate bounded Redis budget: 600 requests per buyer per minute, 1,200 per source IP, and 6,000 globally. Keys aggregate every order and session; changing an order, session or file cannot reset the budget. Source IP uses the existing trusted-proxy resolver and a hashed key. Preparation and download-session allocation retain the existing ten-per-minute caller limits. Authorization, payment/refund/dispute/revocation, expiry, connection authority, purchase allowances and immutable cached grants remain enforced by the delivery service. Redis unavailability fails closed. A rate refusal returns HTTP429 with Retry-After:60 and no-store before entering the delivery service.

The buyer waits on HTTP429 and retries only the same file in the same download session, at most three retries per file. It honors a valid delay up to 60 seconds, defaults to 60 when the header is absent, and refuses unsupported longer or malformed delays. Cancellation and page exit abort the wait. Other HTTP statuses and unknown network outcomes do not trigger this retry. Current file/total and rate-wait progress are visible; no new download allowance is allocated during the wait, and expired cached grants are never reminted. This conservative initial budget makes 22,000 files a roughly 37-minute minimum journey before transfer overhead, not a promised production throughput.

Verification: six HTTP/real-Redis tests pass, including 600 successful file-grant responses followed by429, same-session recovery after window expiry, changed-order/session aggregation, IP/global saturation, 610 concurrent requests producing exactly600 successes and10 rejections, and Redis outage refusal. Five isolate the real route and limiter with a synthetic delivery service. The sixth runs the actual PostgreSQL purchase service for602 files:600 granted, file601 rate-limited, one allowance consumed, then purchase revocation during the wait prevents further grants after the rate window resets. This HTTP test caught an obsolete download-response index bound of0–9; the response now accepts the shared selection bound, and the22K service test validates its complete response against that schema. Separately all47 PostgreSQL delivery regression tests pass, including the22K immutable-grant test. Frontend25 component/API/stream tests pass, including retry, cancellation, non-rate failure handling and22K streaming; TypeScript and focused lint pass. These are not a full production-stack or real-cloud bulk transfer claim.

A separate normal-Chrome preview at http://127.0.0.1:4343/ uses the real purchase/file endpoints, PostgreSQL migrations005/006, isolated Redis and native browser folder writes with22,000 synthetic42-byte files. Identity, public peer IP, provider responses/bytes and KMS are explicit local test seams. Max selected the native folder in normal Chrome. The user tab1702607595 showed the pause at file601 and later file1201, proving automatic recovery. It then reported Saved22000files with2downloadsremaining. A separate filesystem observer verified all22,000 unique expected filenames,42bytes each,924,000totalbytes and the expected SHA256 for every file (2b2573d5ea0b352e24bebd015f3fe83693a5b81a6252cf811b65dcf6a5037def). The actual database reports22,000grants and one consumed allowance. Receipt: /Users/max/Documents/Codex/2026-09-08/seller-workspace-delivery-continuation/outputs/SELLER-BROWSER-DOWNLOAD-RESULT.json. This completes the synthetic22K native browser transfer proof, not real-cloud bulk transfer. Preserve the older previews and their databases, which still load older code. This preview's new database may be removed on shutdown, so preserve its live process during evidence collection.

Real-cloud22,000-file transfer and the final released customer journey remain unverified. The existing three-object AWS authorization does not authorize a new bulk object fixture. No production migration, deployment, provider mutation or support message is authorized by these development results.

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
2. Preserve the completed dedicated AWS fixture, exact-prefix restrictions, browser CORS and two-file native Chrome transfers recorded below. Its authorization covers the prepared bucket, read role and three tiny synthetic files only.
3. Preserve the completed S1667 local integrated-candidate and search-worker evidence below. Complete independent review, remaining R2 implementation and authorized release-environment evidence. The completed synthetic 22,000-file native Chrome transfer does not establish real-cloud bulk transfer or production readiness.

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

## September 8 current-candidate acceptance (S1667)

Separate local Celery Beat and worker processes used the unmodified60-second seller-listing-search schedule, a dedicated Redis59942, disposable PostgreSQL and dedicated Qdrant1.15.5 at59943. Actual publication queued an ID-only outbox row; Beat dispatched it, the worker wrote the public search point and actual marketplace search returned the listing. Pausing immediately hid the listing through PostgreSQL filtering before remote deletion. The next scheduled run removed the point. Resume queued and restored it on the following run. The worker committed and cleared each outbox row. Public index payloads excluded the private brief and filenames. The initial fixture lacked PostgreSQL pg_trgm; adding the already-required extension to the disposable fixture corrected that test setup. The full repeat passed in132.94seconds. Embeddings were synthetic and all services were local; this is not production-worker or semantic-quality proof. Receipt: /Users/max/Documents/Codex/2026-09-08/seller-workspace-completion-after-22k/outputs/SELLER-SEARCH-WORKER-RESULT.json.

Normal Chrome tab1702607604 at4345 walked the current seller code against a fresh4344PostgreSQL-backed preview. Allai returned suggestions through the actual accounting endpoint; explicit acceptance saved the description and reload restored it. Whole-folder selection deduplicated the existing choice, confirmed four files and31,992,000bytes, then saved. The exact review showed those files privately and the accepted description/price/license publicly. Explicit no-sample and four confirmations preceded approval, then explicit publication created one listing. Pause and resume persisted with two visibility audits. The ledger recorded one completed request,28starter cents reserved,2charged, unused hold returned, and paid balance unchanged at0.23focused assistant/accounting/search/management regressions also passed. Identity/capabilities/discovery/provider metadata/model/KMS and unused foreign-key targets remain synthetic seams. No customer credit, model spend or production mutation occurred. Receipt: /Users/max/Documents/Codex/2026-09-08/seller-workspace-completion-after-22k/outputs/SELLER-INTEGRATED-BROWSER-RESULT.json.

The new4344/4345preview must be preserved independently of earlier evidence environments. This closes local current-candidate acceptance gaps; Cloudflare authority, full-scope independent review and concrete authorized enabled-release proof remain outstanding. Final released-on-by-default acceptance is not current authorization to change production flags.


## September 8 review corrections (S1669)

The original CC technical review returned APPROVE_WITH_NITS; DeepSeek returned APPROVE_WITH_MANDATES. These are static assessments of the original snapshots, not release certification or approval of later folds. GLM's original detached request subsequently returned REQUEST_CHANGES; preserve all three responses and review the final updated heads only after folding validated findings.

CC's expired starter-credit finding reproduced in actual PostgreSQL: request-conflict, another in-flight request and rate-limit refusal each rolled back an expired hold refund. The correction commits that refund before those three refusals. It preserves credit/request locking, request identity, the two-minute expiry, the existing rate limit and starter-only accounting. No periodic sweeper, paid-credit fallback or model spend is added.

Historical S1669 publication migration002 unlisted Workspace offers before dropping their bindings. That partial rollback is superseded by the S1673 candidate: retained seller records prohibit schema downgrade before any listing, authority, table or trigger is changed. Use the preserved-history procedure below. Already-issued signed links retain their bounded lifetime. No production migration has run.

CC's proposed cross-buyer first-download race is not supported by source: the service locks the shared listing-version row before ensuring its source index. A real PostgreSQL concurrent two-buyer/two-order test passed with one complete source chunk, two independent sessions and one allowance per buyer. No conflict-suppression code was added. Static original-review approval still must be followed by review of the updated exact heads.

### R2 authority documentation check (S1669)

Cloudflare's current [OAuth integration documentation](https://developers.cloudflare.com/fundamentals/oauth/integrate-with-cloudflare/) confirms the existing token and revocation endpoints. Its [temporary-credentials API](https://developers.cloudflare.com/api/resources/r2/subresources/temporary_credentials/methods/create/) requires a parentAccessKeyId in addition to bearer authorization, bucket, permission and TTL. The [R2 token documentation](https://developers.cloudflare.com/r2/api/tokens/) derives S3 credentials from a created API token's ID and value. These pages do not establish that this application's approved OAuth read scopes can supply that parent identity or mint equivalent direct-delivery authority. This is an unresolved provider contract, not proof that OAuth cannot support it. Do not substitute the OAuth client ID for a parent access-key ID or infer API-token creation permission from read consent. Resolve supported exchange access and this authority contract before implementing/enabling R2 delivery. No extra scopes, stored-token fallback or provider mutation is authorized.


### GLM release findings still open (S1669)

Current source confirms that the inherited agent dataset detail/evaluation service can accept published Workspace listings yet substitute Single User, zero bytes, CSV defaults, seller verification and fixed quality/completeness metrics. Workspace agent/MCP/public projections must preserve exact approved terms and immutable size/count; unsupported sample/evaluation must fail closed. Also outstanding: bounded server-side source review paging at the50K/64MBbound; crash-hold expiry before unrelated shared API-credit consumption (the S1669 refusal correction does not solve this); a preserved-record post-publication rollback procedure/rehearsal; and a new frozen review bundle with exact reproducible commands, historical raw receipts and a finite reviewer budget. GLM treats these as requested changes. None is release-approved or completed by the two S1669 corrections. The full unchanged report and next priorities are retained in the S1669 task outputs.


## S1670 Workspace agent projection correction

Workspace agent and MCP detail handlers now reuse the digest-checked immutable public presentation and the publication-bound ListingVersion object count and byte total. The approved title, description, category, tags, price and licence remain exact. Unmeasured rows/columns and seller verification remain null; formats and schema summaries are empty rather than claiming CSV or conversion. Agent search no longer represents unprofiled Workspace rows/columns as measured zero. Marketplace search hydration was inspected: it retains current PostgreSQL visibility and stored metadata rather than the agent detail defaults.

Agent evaluation, sample preview and the separate synthetic-preview service refuse no-sample Workspace listings. MCP preview and schema handlers report explicit unsupported capabilities. Detail lookup by UUID and MCP slug both use the same projection. Withdrawal removes agent/MCP detail availability. Legacy detail/evaluation/sample behavior remains in its existing branch.

Proof uses actual isolated PostgreSQL approval/publication and the HTTP response models, MCP handlers and synthetic-preview service, with a distinctive Research licence and 42-byte source. It verifies parity, no private source metadata, unsupported previews, slug lookup, withdrawal and unchanged legacy behavior. Provider/KMS and MCP rate admission are synthetic; this is not live browser, cloud or production-release proof. The expanded fixture initially lacked legacy rating columns defined in the initial migration; only the disposable fixture was corrected. Exact command and raw logs are retained in S1670 SELLER-PROJECTION-TEST-RECEIPT.json. Independent updated-head review remains required.

## S1671 bounded private review pages

The review response now includes `source_hash` and `source_page` instead of the complete `source_files` array. The first page defaults to 50 filenames. A caller may request 1–1,000 records, but every page is also limited to 256,000 bytes of serialized file metadata. Exact full-selection count and byte total appear on every page and in the seller summary; approval continues to cover the complete immutable selection, never just the displayed page.

GET `/seller-workspace/listing-review/files?cursor=...` requires the active owner seller's JWT and existing review/approval readiness. Cursors contain a position, page-size and saved review/source version/hash binding; they confer no authority. Each page rechecks owner, saved draft, source hash/version and live connection under the same review locks. Changes reject the cursor with HTTP409, including a same-content new source version. Saved source reads now verify the decrypted envelope digest. Invalid inputs and private errors are non-reflecting; both routes return no-store,private.

The browser retains the first page and current page, plus small cursor positions for backward navigation. Filenames wrap inside a bounded scroll area so long keys cannot push the listing preview and paging controls far down the page. It verifies page identity, position, bounds and full totals, aborts navigation on exit, and disables approval/publication readiness during a page load or after any page error. A changed or unverified page clears displayed filenames and requires a full refresh. Returning to page one revalidates the saved review. No full-selection array is downloaded or cached in browser storage.

This is a bounded transport change, not a new source-storage format: each server page still decrypts and validates the existing at-most-64,000,000-byte encrypted metadata envelope. The review-header query now avoids loading its ciphertext redundantly. No plaintext cache, derived source table, migration, provider request or model call was added. Backend per-request memory and latency remain proportional to the saved manifest; release capacity must be assessed with the recorded local measurements rather than assumed cloud throughput.

S1671 verification: actual isolated PostgreSQL/HTTP/AES-GCM saved and paged exactly 50,000 synthetic file identities occupying 63,839,010 metadata bytes, totaling 1,250,025,000 file bytes. All 250 byte-limited responses (requested page-size 1,000) matched every saved identity and total. The default first 50-file review response was 66,751 bytes in 1.11 seconds locally; the largest response including its envelope was 257,958 bytes. Full setup/traversal took 313.13 seconds. Process peak RSS was 807,731,200 bytes and includes the Python test runner, retained expected fixture, save/encryption and HTTP work; it is not a standalone production per-request memory measurement. Provider, identity and KMS were synthetic. No provider calls occurred during page retrieval. The first failed fixture-size assertion and later private-cache-header failure are retained with their fixes in S1671 receipts, not erased.

Focused review/auth/cursor proof passed five tests, plus a corrected private-header regression and the near-bound case. Existing source/approval/publication/agent projection selection passed 34 tests including the prior22Ksource roundtrip; 28 frontend tests, TypeScript, focused backend/frontend lint and116runbook checks/index passed. Normal Chrome tab1702607607 at4347 against a fresh4346database verified exact totals,50visible rows,server next-page navigation,explicit synthetic confirmations,stale-draft refusal with filenames removed and approval disabled,then refresh to the new price with confirmations cleared. Long keys wrap inside a bounded scroll area. This is a component/HTTP proof, not a new full release journey, live-cloud proof or repeat of the completed22Knative buyer transfer. Raw command receipts and browser observations are in /Users/max/Documents/Codex/2026-09-08/seller-review-paging-full-release/outputs.

Independent updated-head review remains required. GLM6 shared-credit crash-hold expiry, GLM7 preserved-history rollback and GLM3 immutable review provenance remain open, as do R2 and authorized enabled release. Older frontend previews read the original frontend worktree: S1671 moved its frontend edits into a new isolated worktree and restored the old four edited files byte-for-byte to4696cb64. Do not fast-forward or restart that original preview checkout. Existing preview/database processes were not restarted or stopped.


## S1672 shared-credit crash-hold expiry

The inherited crash defect reproduced in actual isolated PostgreSQL: after an assistant reserved10starter cents and its worker was killed before settlement, an unrelated15-cent API deduction used5paid cents despite20starter cents being available after expiry. Both BillingService and the Co-Pilot credit deduction path reproduced that outcome.

Shared credit availability now expires assistant holds older than the existing two-minute lease before balance checks, API reservations or deductions. It locks and refreshes the account before locking the expired request rows, refunds only the held starter amount and marks the same seller/request identity failed. Shared consumers and assistant reservation/settlement use this helper. Concurrent consumption cannot refund twice; valid holds remain reserved. A late assistant result cannot settle an expired request, and its failed identity cannot invoke the model again. No paid balance or total-used increment is part of expiry. Monthly policy remains distinct.

The caller retains transaction ownership. Consumption commits recovery together with its deduction; balance reads and refused consumption can roll back housekeeping, but every later availability/consumer call excludes the expired hold again. There is no background sweeper and no promise that idle accounts have physically rewritten counters exactly at two minutes. Read paths acquire an account lock until their caller finishes the transaction. The assistant-request migration must exist before this application candidate serves shared billing, including when Seller Workspace flags are off; feature disable is not permission to remove this table.

Verification uses disposable synthetic PostgreSQL and the actual assistant-request migration plus actual shared billing services. A separate interpreter commits a reservation and is killed before settlement; only the persisted test timestamp is then moved past the unchanged deadline. No real model, payment, customer credits, provider or production mutation is involved. Exact commands, environment, failures and final results are retained in the S1672 task outputs. Independent updated-head review and production concurrency/release proof remain required. GLM7 preserved-history rollback, GLM3 immutable full review bundle, R2 and appropriately authorized enabled release remain open.


## Preserved-history rollback procedure (S1673 candidate)

This is an isolated-development procedure awaiting updated independent review and exact release-environment rehearsal. It is not authorization to change production flags, deployments, migrations or customer state. Never run older candidate downgrade scripts: those packages retain destructive behavior. Use the exact reviewed migration package, including its migration safety helper. Database-owner manual DROP/trigger bypass is outside this guarantee.

### Before first use

Confirm exact application/migration identities, backup/restore coverage, effective flags on every web/worker instance, and that all seller-serving writers are drained. Apply the seller chain through seller_approved_source_chunks while the new stages remain off. Upgrade005 copies pre-existing encrypted legacy grants byte-for-byte without KMS or reminting; after upgrade, old legacy-map writers fail closed. Do not roll old and new grant-writing application versions together with delivery enabled. Verify every serving instance uses the compatible index-aware release before enabling any authorized stage.

The current shared BillingService and CoPilot paths require seller_assistant_requests even with SELLER_WORKSPACE_ENABLED=false. That migration is now an unconditional downgrade floor, including when empty. Feature flags cannot make dropping it safe. Earlier application packages must retain the expanded schema; any future removal requires a separately reviewed accounting migration and compatibility plan.

An unused schema may downgrade only as far as seller_assistant_requests. The guard examines drafts, assistant requests, saved sources, approvals, publications, download sessions, search outbox, file grants, approved source chunks and Workspace audit. Any retained row blocks removal, including failed requests, paused offers, expired sessions/grants and historical audit. Do not delete history to make the guard pass. The guard takes transaction-scoped exclusive table locks, checks after acquiring them, and refuses lock acquisition after five seconds. A refused migration must roll back its transaction. Keep writers drained through migration completion; this does not claim availability for serving traffic during DDL.

### After any seller use or publication

1. Stop new publication/assistant activity using the affected stage controls, keeping authenticated management available long enough to pause all affected Workspace offers. Disable new publication with SELLER_WORKSPACE_AWS_PUBLISH_ENABLED=false. Pause through the owner-scoped management operation; verify SQL status=unlisted and is_listed=false. Verify public/agent views and checkout no longer expose a purchasable offer, and allow the search worker to process the durable removal outbox. Record exact affected IDs and result evidence in the authorized environment. A flag change alone does not remove a public offer.
2. Preserve orders, purchased versions, delivery authorities, approvals, source snapshots, mappings, download counts, session/grant identities, assistant accounting and audit. Pausing new sales leaves existing purchased access intact when delivery remains enabled. If the incident requires stopping delivery too, set SELLER_WORKSPACE_AWS_DELIVERY_ENABLED=false and drain affected requests; new/cached API grant responses fail closed. Existing signed URLs may remain usable for their already-issued lifetime, at most five minutes. Expiry is not permission to delete entitlement or audit records.
3. Retain the schema and immutable records; repair forward or restore a proven compatible application release against the retained schema. Do not downgrade the seller chain, merge indexed grants back into writable legacy storage, turn off integrity triggers, reset allowances or rewrite authority kinds. Preserve legacy_serial behavior. A master feature shutdown also disables normal management, so complete/verify the authorized pause first or use a separately reviewed incident procedure.
4. Before restoring service, verify exact code/configuration/migration identities; paused offers remain non-public; failed assistant identities cannot replay; unchanged request/session/file retries return the same stored grant with the same download count; and revocation/refund/access expiry still refuse access. Re-enable affected delivery only with appropriate authority. Resume sales separately after independent review and release proof; preserving purchase rights is not automatic permission to republish.

### Isolated rehearsal and limits

The candidate uses actual PostgreSQL seller migrations and production model schemas for listings, versions, delivery authorities, orders and audit. The unused chain upgrades, downgrades to the assistant floor and upgrades again. A separate rehearsal saves source/draft, approves and publishes through actual services, uses a persisted synthetic purchased order, issues one grant, rejects an old-format writer, pauses, checks purchase refusal, disables delivery, refuses every seller downgrade entry point, and restores compatible delivery. Complete before/after records match; request and file retries do not issue another link or consume another allowance. A legacy-layout fixture checks upgrade005 preserves the exact encrypted envelope and cached access without reminting. Each retained-table class blocks independently; an in-flight writer is allowed to commit before the guard rechecks and refuses.

Test seams remain explicit: synthetic identity/KMS/AWS responses, minimal unrelated FK targets and a synthetic order instead of Stripe checkout. Mixed-writer proof exercises old-format SQL against the migrated database, not a rolling production deployment. This does not establish production concurrency, real payments, production backup restoration, external public/browser rollback evidence or an enabled release. Exact commands, selection, versions, exit status, failures, warnings and raw logs are in the S1673 task outputs. Updated-head Council review, GLM3 immutable full review evidence, R2 and appropriately authorized release remain open.

## S1676 independent correction acceptance and release capacity context

The S1674 sealed candidate has now received all three required independent reports: CC APPROVE_WITH_MANDATES, GLM REQUEST_CHANGES and DeepSeek REQUEST_CHANGES. All three accept GLM1/3/4/5/6/7 technically and identify no new HIGH/MEDIUM code defect in the corrective delta. This supersedes the earlier sections' pending-review status only. The full AWS-and-R2 enabled-release objective remains incomplete: R2 implementation and its OAuth/direct-delivery contract, release configuration and the provider/identity/KMS/accounting/search/outside-customer journey remain open. GLM grades missing release/capacity proof MEDIUM; CC and DeepSeek grade per-page cost LOW. Preserve these distinct verdicts; technical acceptance is not unanimous release approval.

Reviewed identities are backend d9ef6d2983fabf0ab9ff07cefcc584e278fff446, frontend a52cd541dfcdae199395a391c7227b5733d26262 and runbooks 788360e8d37b8a843d533c3f61f4356431611128. Seal index SHA256 is 08a603f2a9a10f03e9424b1d8eb14e036655a006aa4c92bd6c0d0dc214e7af46. This later operational note is outside that seal and was not reviewed by its voters. All reports were static review, not independent execution of historical tests. Missing early environments/versions, suppressed warnings and reviewer network verification remain unverified. Exact reports, source-check annotations and capacity context are retained in /Users/max/Documents/Codex/2026-09-08/seller-final-review-full-release/outputs.

CC explicitly mandates that the assistant-request migration precede serving this application version, including when Workspace is off. The actual dependency is api_credit_availability.py lines18-29 (the report's32-41 range is inaccurate); migration003 lines22-26 refuses downgrade unconditionally. The Dockerfile runs successful Alembic startup before Uvicorn. Release proof must still verify the effective startup command and actual schema for every serving web/worker instance. Do not treat staging's initial-schema stamp shortcut as proof that seller tables exist, and never delete history or remove the billing floor to permit rollback.

Retain the CC report unchanged, including its advisory wording. Its duplicate-mint503 advisory conflicts with its own acceptance of the race falsification: source locks the order before session/grant inspection and locks ListingVersion before source-index creation. Existing actual PostgreSQL same-request/same-file tests require identical responses and one mint/allowance; their retained execution passed2tests,46deselected,7warnings in6.05s. The cross-buyer test also requires one complete shared index and independent allowances. These observations do not support reintroducing speculative conflict-suppression code. Other original advisories remain open unless specifically resolved.

S1675 separately measured three cold first-page requests at50,000files/63,839,010metadata bytes using actual ASGI/HTTP, PostgreSQL and AES-GCM with synthetic identity/KMS/provider metadata. Fixture construction was excluded from child processes. Single-request time was2.150s; two independent-seller child requests took2.153/2.160s. Sampled request RSS growth was490,700,800/491,192,320/490,766,336bytes; peaks were676,937,728/677,806,080/677,380,096bytes. Every response had50exact filenames, the exact source hash/count/byte total and66,751HTTPbytes with private/no-store. Sampling every10ms may miss brief peaks; growth includes DB/HTTP allocations. This is exploratory local evidence, not production KMS, sustained load, p95 or release acceptance, and it was outside the S1674 review input.

Read-only normal Chrome and Railway inspection in S1676 found production ai-market-backend at one US-West replica with UI maximums24vCPU/24GB. Deployment dbb66382-ac9f-4d51-b6b8-3392d7fc5655 was SUCCESS for264f74a4dd4f160d260fcd2fcaf58949f2e8b296, not the seller candidate. These are configured ceilings, not measured spare capacity, a spending approval or supported seller concurrency. Effective WORKERS, steady-state headroom, launch concurrency/response target and Linux release-image sustained-load proof remain unverified. Do not divide24GB by491MB and call the result supported concurrency. Size a representative isolated test against the concrete launch target before choosing a source-format change; no speculative chunking or plaintext cache is justified by the advisory alone. No provider settings, release flags, deployments or customer data were changed by this inspection.

## S1677 worker and database capacity observations

Read-only Railway SSH confirmed the same production backend deployment and commit on Linux x86_64/Python3.11.11. WORKERS is unset and the actual PID1 Uvicorn command uses --workers1. Six samples over25seconds showed process RSS572,052–595,004KiB and container memory607,948,800–659,808,256bytes; no memory-limit or OOM events were recorded. The effective container ceilings are24,000,000,000memory bytes and24CPU equivalents. A separate production Postgres cgroup-only read showed753,430,528current bytes,777,007,104peak bytes, the same24GB/24CPU ceilings and no OOM events. No SQL, customer records, secret values or provider settings were accessed. These brief current-release observations are not reserved spare capacity or seller-release load acceptance. Production health remained healthy with no reported model/schema drift.

An unmodified production Dockerfile built the exact backendd9ef6d2983fabf0ab9ff07cefcc584e278fff446 archive as a new local Linux/arm64 image b0e7709def83c955e1fc8ca6711367457fee1e8bf5726bcd1f041d4723b9354e. Both import smoke checks passed;1,290application/migration/startup/requirements files inside the image matched the candidate bytes. Resolved package versions are retained, not presumed equal to production. The external diagnostic harness serves the actual review route with one Uvicorn worker, PostgreSQL16 and AES-GCM, using synthetic identity/configuration/provider/KMS seams and minimal unrelated foreign-key tables. It omits full production startup/middleware/background load. Fixture construction runs separately from the web process. This is not billing-schema, full-stack, enabled-release or x86-performance proof.

The initial384MiB disposable database limit caused PostgreSQL worker OOM kills and HTTP503 at two concurrent near-bound reads. Logs and cgroup counters retain four kills; a narrow diagnostic reproduced ConnectionDoesNotExistError during the encrypted-source SELECT. Only that newly-created local database was raised to1536MiB, without swap. No production limit changed. The repeated test had zero additional database OOM kills and zero web OOM kills. Database peak was964,517,888bytes; web container peak851,673,088bytes. Capacity sizing must cover database transfer allocations as well as web parsing/decryption; a web-RSS-only estimate is insufficient.

The repeat completed56exact/private first-page responses from four independent sellers in one database, each owning50,000objects/63,839,010metadata bytes. Eight batches each at concurrency1/2/4 produced8/16/32responses, median1.802/3.631/7.410seconds and maximum2.166/3.828/7.694seconds. A separate trivial HTTP probe waited up to1.624/3.400/5.012seconds respectively. Web process sampled peaks were584,167,424/674,410,496/814,632,960bytes. Sampling targeted10ms but may miss peaks; first-phase pre-load RSS was not captured. These are warm-process diagnostic samples, not sustained production percentiles or a launch SLO. They demonstrate one-worker contention without a response-integrity defect; they do not establish that four concurrent sellers is an acceptable launch target. No speculative source-format or plaintext-cache change was made.

Exact method, commands, image identity, package versions, samples and failures are retained in /Users/max/Documents/Codex/2026-09-08/seller-r2-release-capacity-continuation/outputs. Failures also include a too-short synthetic SECRET_KEY rejected before setup and an unreachable host port on the internal Docker network; the successful load client ran separately inside that network. Only the new test web/database containers were stopped afterward; their data and image remain, and all older previews/databases were preserved. New evidence is outside the S1674 seal and has not been independently reviewed. AWS/R2 release configuration, accepted demand/response targets, production KMS/accounting/search, backup/rolling compatibility and outside enabled journeys remain open. Current Cloudflare documentation still does not establish the approved OAuth-read-scope to parentAccessKeyId/direct-delivery mapping; the existing support request remains unsent pending explicit send permission.


## S1678 release-startup graph correction

The exact prior backend d9ef6d2983fabf0ab9ff07cefcc584e278fff446, in its unmodified S1677 Linux image, failed the real Docker startup command before Uvicorn: Alembic reported multiple heads. Actual `alembic heads` named seller_approved_source_chunks and s1665_aim_data_oauth_activate. This is a newly executed integration finding, outside the S1674 seal and its static reviews. It does not change their historical verdicts.

An isolated backend candidate adds only a no-DDL merge revision, s1678_seller_release_merge, joining those two exact parents, plus a release note. Neither parent migration, AIM Data activation behavior, seller stage flag nor protected preview checkout was changed. The existing image with the one read-only migration overlay has one head. The actual startup helper completed a clean full-history PostgreSQL16 replay and the committed April26 schema-collision fixture on PostgreSQL17; immediate repeats applied no migrations. Both used dedicated synthetic local roles and the documented one-shot bootstrap input. Initial missing application-role input was retained as a failed setup attempt, then corrected in the disposable database only.

Twelve existing startup/graph/author-DSN tests passed in the repository host venv with50warnings retained. The runtime image intentionally lacks pytest; that attempted invocation failed and is not a pass. Merge-only reversal required an explicit parent target because `downgrade -1` was ambiguous. Reversal to seller_approved_source_chunks and re-upgrade changed only the version rows; fingerprints of all326non-version tables, including synthetic accounting history, were identical. This does not authorize operational downgrade below either parent or bypass the existing accounting/history floor.

Actual shared BillingService read and failed assistant-request replay were exercised against the full migrated schema with Workspace off. An expired10-cent synthetic hold restored20starter cents available, retained1000paid cents, and the failed request could not replay. The first fixture used an unhashed request identity and correctly hit request_conflict; a new synthetic account with the correct digest passed. No model call, payment, customer credit or provider was used. The test database role was the local schema owner; production restricted-role and serving-fleet evidence remain open.

The committed worker and Beat configurations override the image command with direct Celery starts. They therefore do not themselves prove schema admission or migration ordering. Release must verify the actual schema and effective command on every serving process, run the authorized migration with writers drained, and admit only compatible application versions. The staging initial-schema/stamp shortcut is still not proof that seller tables exist. CC, GLM and DeepSeek each approved this isolated correction with nits and no HIGH/MEDIUM defect. This grants no production deployment, migration, flags or full release approval. Raw scripts, logs, failures and local restore diagnostics are in the S1678 release-readiness task outputs, separate from the immutable S1674 bundle.

Post-review execution built exact backend 69cdf6828a25ea73182a41e14a7995e0dace0274 (draft PR351) with the unmodified Dockerfile into ARM64 image sha256:ded9db729d4744b384a9edb117f98e10009a5228ea88d08d7112e3a9e6ac8197. All1,432 inspected source files matched and resolved packages matched the prior image. Normal Docker startup and actual application lifespan returned HTTP200 healthy at the merge head without schema/model drift against the full migrated synthetic database. SKIP_SERVICES=1 and AIM Data OAuth disabled exclude background services, Redis, providers and KMS; this is not full topology or production proof and was not part of the earlier sealed review. A synthetic same-cluster backup restored326table data and Alembic-version fingerprints exactly, but schema expression differences remain unresolved; full schema equivalence and operational recovery remain unverified. Separate review annotations clarify Git-commit versus content-hash provenance and the failed billing fixture identity without modifying reviewer reports.


## S1679 Celery schema admission and restricted-role rehearsal

PR351's unanimously reviewed no-DDL startup correction was fast-forwarded into seller PR342 at exact backend69cdf6828a25ea73182a41e14a7995e0dace0274; PR351 is merged. Protected preview checkouts were not advanced. The newer production/main1c96b257c34938ea547be1eb818d5e902ff49f56 is Mars's T779 fulfillment correction, not the seller release; it adds no migration in that delta. Seller release integration must preserve it.

A new isolated candidate0e0a8e315b8fbbf96a3baf362c1312d676d63e40 (draft PR352) repairs a demonstrated process-start gap: the exact prior ARM image's committed worker and Beat commands started against a nonexistent database, and worker logged ready. The commands now run a bounded read-only application-DSN probe before exec of unchanged Celery arguments. It selects no rows, checks all mapped columns of the eight seller draft/accounting/source/approval/publication/download tables plus the SQL search-outbox columns, and does not use author credentials or trust an Alembic stamp. It remains required with Workspace off. This tests readable schema shape, not types, constraints, triggers, write permissions, provider/KMS authority or complete fleet certification. Effective deployed commands and authorized migration order remain separate evidence.

Five focused process/refusal/redaction tests and focused lint pass. Real disposable PostgreSQL checks reject absent database, denied SELECT, stamped-but-missing tables and a missing column, then pass the complete schema with a dedicated non-owner, non-superuser role. Its application role is explicitly denied public CREATE and issue-channel access. Actual shared BillingService with Workspace off restores20starter cents after an expired10cent hold, preserves1000paid cents and refuses failed assistant-request replay. This is a documented synthetic permission fixture, not a claim that production role grants match it.

A separate local PostgreSQL cluster restored the retained synthetic dump with ownership and ACL statements included. First restore failed because issue-channel roles were absent; that partial database and failure are retained. Matching local non-login roles were created, and a second database restored successfully. This does not close semantic schema equivalence, production/PITR/KMS or purchased-rights recovery. Source/image/probe receipts, all failures and current boundaries are in the S1679 seller-r2-release-fleet-continuation outputs. Independent review remains pending at this note's commit. R2, accepted demand/response targets and authorized enabled release remain incomplete.

Exact candidate image sha256:71bd4a0ec5dac58aa7e8ee25da3684643024f5798e765d9b90de21a53bd9d55c built with the unchanged Dockerfile/requirements and matched all1293 inspected source/configuration files. Both final committed commands refused a nonexistent database; each admitted the full schema with the restricted application role and an intentionally unusable author DSN, and reached its own startup marker. Both stopped with exit0 and OOMKilled=false. This is local ARM PostgreSQL/Redis proof with no provider/KMS/model/payment traffic, not deployed command or web graceful-shutdown proof. The first image-inspection script incorrectly expected Dockerfile inside the image; existing .dockerignore excludes it. That failed inspection is retained; only the external inspection script was corrected.

The unchanged Docker HEALTHCHECK still probes web port8000 in these Celery containers and records failures; those raw states are retained. Process startup/clean stop are established, healthy serving-fleet status is not. Railway worker/Beat config sets healthcheckPath=null; effective deployed health behavior remains unverified. Do not suppress this observation or describe the local containers as healthy.

S1679 final independent review: CC, GLM and DeepSeek all APPROVE_WITH_NITS for exact0e0a8e315b8fbbf96a3baf362c1312d676d63e40, no HIGH/MEDIUM finding.3,149sealed files, index3f274962c6fab688c7276961fd7d38e3c210180b2be8856f47e7b6a4405f3d3a. Original reports and bundle remain unchanged. Separate annotations retain SELECT-only/per-statement-timeout/diagnostic/test-portability nits. Post-review controller evidence reproduces the full base-to-head diff exactly (SHA256968112774077853f18cf0854fc5e9450d236de116dba96dd143a505b7df20b03) and captures exact fresh targeted-Ruff/commit-range-diffcheck argv, outputs and exit0. These new provenance checks are not retroactive reviewer execution. Full release/R2/health/type-trigger-write-ACL/backup/KMS/search/rolling gates remain open.

The unanimously reviewed PR352 correction was integrated by exact fast-forward into seller PR342: seller-listing-drafts now0e0a8e315b8fbbf96a3baf362c1312d676d63e40. No protected preview-serving checkout was advanced. This updates the earlier draft/base references above, not production/main. All19S1679containers are stopped, with data/images/internal network retained. Full seller objective remains incomplete.


## S1680 isolated main integration and full-schema publication

The isolated release merge preserves seller0e0a8e315 and main1c96b257 (including
Mars T779), tree59b1524a3067c84b898e0ea5fd3e7a1005656e0c. No protected preview or
main branch was advanced. Existing main fulfillment-listener/notification tests
retain six baseline failures; the seller rollback test also incorrectly treated
the graph-only S1678 merge as a destructive revision. The corrected test uses
Alembic graph identity, verifies merge reversal/reapplication preserves history,
and retains every destructive-revision refusal and shared billing floor.

A separate full-schema PostgreSQL restore exposed an actual publication failure:
listings.schema_info is NOT NULL in 000_initial, whereas the ORM allows null.
Publication now explicitly stores an empty metadata object there. This exposes
no raw field names, file content or public sample and needs no migration or
existing-row rewrite. Focused regression applies the real constraint before
publication/replay. No retrospective approval is implied.

The exact merge image reached HTTP healthy with no model/schema drift and ran
Uvicorn as PID1. A stop with a60-second allowance exited0 in4.86seconds with
application-shutdown-complete logs and OOMKilled=false. SKIP_SERVICES=1, a local
owner DSN and synthetic full-schema restore remain explicit seams. Early Docker
checks failed while startup was incomplete; successful HTTP checks followed.
This is not effective Railway health/fleet or production-role certification.

An overlay rehearsal then exercised actual encrypted source save, draft, review,
approval, publication and ID-only search drain under a local non-owner role with
prototype public SELECT and named write grants. Local Qdrant indexed, removed
and restored the offer; SQL hid the paused offer before vector deletion. The
first query used fallback because its synthetic embedding stub lacked embed_query;
this is retained as a fixture limitation. Provider metadata, connection/credential
placeholders, key wrapping and embeddings are synthetic; no provider/KMS/model
call or payment occurred. Exact-image corrected evidence and review disposition
will supersede this preparation note below. Full R2, production ACL/KMS, semantic
backup/PITR/purchased-rights recovery, rolling fleet, accepted demand targets and
authorized enabled release remain open.

S1680 exact candidate b3f68a18a727ff8d4f8aac8ba3e397df89b88be5, draft PR353:
30publication/search/rollback tests and18OAuth route tests pass. The16lint
diagnostics match the seller base exactly; lint is not clean. The final rebuilt
ARM image matches all inspected source/config files. Its full restored schema
accepts actual source save, draft, review, approval and publication under the
non-owner prototype role; actual Qdrant/public search transitions1/0/1 and drains
the outbox each time, with both embedding methods now supplied synthetically.
Actual shared billing under the same role restores20starter cents, preserves
1000paid cents and refuses failed-request replay with Workspace off. Raw failures,
commands, evidence and scope are retained in seller-r2-release-integration-
continuation/outputs. Review remains pending; no integration into PR342, main or
production is claimed for this new candidate.

## Final narrow integration disposition — S1680

CC, GLM and DeepSeek each returned APPROVE_WITH_NITS on exact b3f68a18a727ff8d4f8aac8ba3e397df89b88be5; no HIGH/MEDIUM or required code change. Original reports are retained verbatim in outputs. Future merge schema fingerprint/allowlist, existing ORM consistency and baseline lint/tests are advisory, not silently cleared. All 3,256 sealed files still match.

The exact reviewed candidate was fast-forwarded into remote codex/seller-listing-drafts; PR342 head now b3f68a18. Main remains 1c96b257c34938ea547be1eb818d5e902ff49f56. Protected local serving branches were not advanced. First push using raw SHA was rejected by the local ref-format guard; the normal named branch push succeeded without bypass. PR353 was marked ready before integration; its GitHub state is separately recorded, not inferred from branch ancestry.

This completes only the reviewed main/seller integration and full-schema publication correction. Full R2 and enabled release objective remains INCOMPLETE. Original full-release review mandates and authorization boundaries remain in force. Next owner must use a fresh session only after authoritative S1680 CLOSED verification.

## S1682 effective fleet and Beat release incompatibility

The exact S1680/S1679/S1678/S1674 sealed indexes and all13,268 indexed file hashes
match; the345-file S1680 final supplement also matches. PR353 remains merged,
PR342 draft/open at b3f68a18a727ff8d4f8aac8ba3e397df89b88be5 against main1c96b257.
Read-only Railway inventory and actual process inspection establish that all
three production services still run main1c96b257, with separate image digests,
one replica each, direct Celery worker/Beat commands and one Uvicorn web worker.
Worker/Beat effective manifests have no HTTP health path; web uses /health.
Public health is healthy/no drift but reports apscheduler. An existing worker
heartbeat is fresh; complete task topology and duplicate-scheduling absence are
not certified. See celery-infrastructure-deployment.md for exact deployment IDs.

A concrete release incompatibility is now proven: live Beat has no DATABASE_URL,
while the reviewed seller command requires one for the read-only schema probe.
The exact final S1680 image with the committed Beat command, synthetic SECRET_KEY,
no DATABASE_URL and network disabled exits1 before starting Beat. This preserves
the guard correctly but cannot serve the unchanged production Beat configuration.
No source, provider configuration, credentials, production deployment, migration
or flag changed. Resolve scheduler admission/authority under independent review
and the existing release-authorization boundary; do not silently grant Beat an
application or schema-owner credential, or weaken the shared billing floor.

The sole new local container seller-beat-no-dsn-s1682 is stopped, exit1,
OOMKilled=false, retained with its logs. Runtime metadata is read-only and
contains credential-presence booleans only. The first inspector used the wrong
optional author-variable name; its false value is not an author-DSN finding.
No old preview, database, container or Chrome tab was changed. Full R2, enabled
journey, semantic backup/rights recovery, production ACL/KMS and rolling release
remain incomplete. Evidence is in seller-r2-release-next-continuation/outputs.


## S1683 synthetic schema and purchased-rights restore milestone

Two NEW internal-only PostgreSQL16 clusters were used; all older databases and
previews were preserved. The source was initialized from the retained S1678
synthetic full-schema dump, then exact b3f68a18 application services created a
new encrypted source, draft, reviewed approval, publication and synthetic order.
The non-owner prototype role issued one bundle allowance and one encrypted grant.
Provider signing, identity, credential retrieval and local key wrapping were
synthetic; no provider, real payment, model or production KMS was called.

A fresh custom-format dump restored into the second cluster with ownership and
ACL statements included. All326non-version table data fingerprints and version
rows matched before subsequent tests. Full schema-only dumps matched after
removing ONLY PostgreSQL random psql restrict/unrestrict nonce lines: no SQL,
ACL, ownership, constraint, trigger, expression or comment normalization. The
four explicitly created local role definitions/policy booleans matched; this is
not production-role or cluster-wide globals certification. It establishes this
new source-to-restored fixture equality, not the original S1678 source's unresolved
expression differences, PITR, live backup freshness or cloud KMS recovery.

Actual restored delivery replayed the exact same grant/session with zero provider
calls, one allowance consumed and two remaining. Revocation then refused further
access. Restored grant/chunk UPDATE attempts hit the real immutable triggers.
Concurrent separate d9ef6d29 and b3f68a18 image processes on the new source database
replayed the same stored grant without remint or another allowance. This is one
real mixed-version service path, not a rolling web/worker/Beat fleet or acceptance
of pre-index legacy writers. No application source or release configuration changed.

Failure truth: first harness import lacked /app in its path; corrected only the
harness. Full-database fingerprint initially used the application role and was
correctly denied issue_channel; corrected to the local PostgreSQL cluster superuser
for comparison only,
leaving all purchase-service runs restricted. The first chunk mutation probe named
a nonexistent ciphertext column; corrected to its real envelope column, then the
immutable trigger refused. The local scope and raw evidence are in
seller-recovery-release-continuation/outputs. New evidence is not independently
reviewed and does not clear the original full-release Council mandates.

A concrete scheduler-only admission proposal is saved separately as
SELLER-SCHEDULER-DESIGN.md. It leaves the current Beat probe in place until an
independently reviewed equivalent release-ordering design is implemented and
proved. Seller search is a Beat task on vectoraiz; APScheduler has unrelated jobs
that a blanket celery-mode switch would remove. Full topology/duplicate absence,
actual scheduled seller search, R2 and authorized enabled release remain open.


## S1684 recovery review and scheduler design milestone

CC, GLM and DeepSeek accepted the bounded S1683 recovery evidence, preserving
its synthetic scope and all original-expression, production ACL/KMS, PITR and
full rolling-fleet limitations. Controller rehashing checked 13,786 inherited
index entries (including repeats), with no mismatches. The fingerprint comparison
used the local PostgreSQL cluster superuser; purchase services stayed restricted.

The revised scheduler design received APPROVE_WITH_NITS from all three seats.
Exact design SHA256: cff8d34177f4363cde87cde236409a7338409487f81e57c6276080c723ce5728.
It requires parent worker_init application-DSN admission before consumption and
web application-DSN admission at the start of lifespan before side effects. All
current seller workers load app.core.celery_app; prove normal, direct and profile
commands. Ordinary exceptions must not become continued startup. Keep the normal
worker prefix and prove actual process refusal, preserved queued messages, and
web nonzero exit with HTTP and socket evidence. Workspace-off is no bypass.

Keep the committed Beat probe until intrinsic checks and isolated refusal proof
pass. Test the scheduler-only command as a declared isolated invocation override:
celery -A app.core.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule.
Prove actual due-task, Redis, worker, SQL outbox, Qdrant and search behavior, with
pause/resume/retry and no duplicate after Beat restart; Beat has no DB authority
or connection attempt. Only then remove the Beat probe prefix in configuration,
repeat exact configured proof and obtain independent exact-code review before
integration. Separate owner migration precedes web/worker admission.

No application/config change or runtime execution occurred in S1684. Static
22-Beat/25-APScheduler registration counts are not effective topology proof.
R2, accepted capacity targets, production exclusion/ACL/KMS and authorized enabled
release remain open. GLM round2 disclosed non-RTK inspection commands, contrary to
the request; CC did not independently hash the design. Reports remain unchanged,
with controller integrity evidence and coverage limitations retained separately
in seller-scheduler-review-fleet-continuation/outputs. No duplicate review dispatch
was used to erase these limitations.


## S1685 intrinsic admission and actual scheduled-path proof

Candidate c3a28af26bc093aec11375c702d70d8cf5124067 adds parent worker_init and
beginning-of-lifespan web checks using the existing bounded application-role
probe. Normal worker prefix remains; direct and profile workers are covered.
Absent database, head-stamped missing tables and denied SELECT produce nonzero
refusal, including Workspace-off/SKIP_SERVICES. A working owner DSN cannot replace
application permission. Real scheduled message bytes/IDs survived nine refused
worker starts. Negative web proof includes HTTP attempts and socket observations;
positive restricted-role startup returned healthy HTTP and stopped cleanly while
retaining existing optional KMS/column-check/seed warnings.

The original retained Beat command stayed guarded through isolated actual
scheduled publication/search, SQL-immediate pause hiding, due deletion, resume,
and a bounded Qdrant failure with retained retry count/deadline and next-due
recovery. Beat emitted nothing during a65second stop and resumed without duplicate
seller IDs in the observed window. Only then was its prefix removed; the exact
configured final command repeated the real pause/resume/retry/search proof.
CC, GLM and DeepSeek all APPROVE_WITH_NITS for exact c3a28af26bc093aec11375c702d70d8cf5124067, with no HIGH/MEDIUM findings. PR354 merged by exact fast-forward into held seller PR342 at that SHA; main remains 1c96b257c34938ea547be1eb818d5e902ff49f56. The 4,571-file review seal is 7babbd6503469a805096207394586983e77e3f822e03ca953528feb181653172. Original reports and their coverage limits are preserved. Advisory loop-helper coupling/deprecation and wrapper coverage nits do not require changes for this integration.
All three unchanged seller/profile schedule entries are explicitly allowlisted
in this harness. This is not complete production schedule or topology proof.

Repeated profile tasks exposed a real closed-event-loop error. The candidate
reuses the existing run_async helper for the three profile wrappers; repeated
actual prefork deliveries then passed. An earlier cleanup failure was a missing
UPDATE grant in the synthetic role, separately corrected only in that fixture.
The readable-shape admission check is not write-privilege certification.

Evidence and all limitations: seller-scheduler-implementation-continuation/outputs.
All new S1685 runtime containers are stopped, retaining data, images and networks. No protected serving checkout was advanced. A post-seal check found old preview listeners4346/4347 and PIDs3276/2477 absent;4344/4345/59941 retained original PIDs. Cause is unverified; S1685 issued no stop/restart to those host processes. Do not claim final listener equality or restart expired fixtures. See SELLER-POST-SEAL-PRESERVATION.md separately from the immutable review input.
Provider/identity/key wrapping/credential placeholders/embeddings are synthetic.
Owner migration rehearsal is a separate no-op at the already-full schema, after
old local processes stopped; it is not a production schema transition or proof
of actual incompatible-production-consumer exclusion. Full R2, production ACL/KMS,
accepted capacity targets and authorized enabled release remain incomplete.

## S1686 complete scheduler registration and live overlap finding

The production web's30persisted APScheduler IDs resolve to25core jobs,
1reconciliation job and4lifespan settlement/payout jobs. Live filtered logs prove
overlapping APScheduler execution starts and Beat emissions for reminders,
auto-confirmations and Buyer Request publication. No duplicate business effect
is inferred. All24inspected live source hashes match unchanged main1c96b257;
held sellerc3a28af is not deployed. This advances topology diagnosis, not full
duplicate-exclusion certification. See celery-infrastructure-deployment.md.

Metadata-only queue counts show25,402translations and30,999profile-control
messages outside the observed worker's queues. No consumer was started and no
message inspected/removed. Any backlog handling needs distinct consumer,
provider/model and customer-data authority; optional profiling does not justify
incidentally enabling that work. A three-Beat-entry removal proposal preserves
all30web jobs and remains unreviewed/unimplemented. Exact evidence/proposal is
in seller-r2-release-after-scheduler/outputs. The support request is still unsent;
R2 authority, release ACL/KMS/schema/capacity and enabled journey remain open.


## S1687 reviewed narrow ownership design

CC APPROVE_WITH_NITS; GLM and DeepSeek APPROVE_WITH_MANDATES permit new isolated
implementation of only the three overlapping Beat-entry removals. No application
source changed and no exact-code/integration/production approval exists. Preserve
all30web jobs, callable tasks, other Beat entries, queues, singleton Beat and S1685.
The accepted proof plan is seller-scheduler-ownership-continuation/outputs/
SELLER-PROOF-PLAN-REFINEMENT.md; original reports and annotations are separate.

Exact retained image d55c95a5 contains Celery5.6.3. A new network-none/read-only
container inspected PersistentScheduler merge/sync; a separate synthetic shelve
probe reopened20held-base entries with only the3proposed keys omitted and retained
exactly17. This is base-framework proof, not actual configured Beat, broker emission
or candidate proof. First probe failed on Python path; new-container retry passed.
No old fixture changed. No production schedule-store deletion is justified.

Before held-branch integration require actual lifecycle30-ID registration plus
conditional, persisted, reconciliation/settlement and startup-failure cases; exact
image restart from the19-entry production-main seed (plus conditional entries),
removed-key due boundaries/no emissions, retained seller-search emissions and a
second restart; actual due seller publication/search/pause/retry; exact-code review.
SCHEDULER_MODE=celery or SKIP_SERVICES=1 leaves the3workflows ownerless after this
change. APScheduler failures retry on the next tick rather than periodic Celery's
60-second retry cushion. No new mode/retry/fail-fast behavior belongs to this slice.
Production remains gated on actual scheduler liveness/jobs and observable failure,
old-producer exclusion, queued/in-flight accounting and rollback. HTTP200/mode-only
health and previously tolerated overlap do not prove safety. Profile/translation
backlogs remain untouched, with external consumer coverage unverified.


## S1692 shared-owner defaults and application permissions preparation

Bounded pg_catalog-only reads through BOTH production web and normal-worker
APPLICATION DSNs on unchanged main1c96b257 inspected ten named shared tables,
their owner and that owner's global/public default ACLs. No author DSN, customer
rows, application imports, migration, grant, task, provider or KMS operation.
Both transactions enforced read-only, bounded timeouts and rollback. S1691's
nine missing seller tables were not rechecked; their admission gate remains open.

All ten shared tables report application SELECT/INSERT/UPDATE/DELETE. api_credits
has RLS enabled (not forced); policies and actual write behavior remain untested.
Each connection reports NOINHERIT, no membership/inherited privilege in the one
observed shared-table owner and no superuser/CREATEDB/CREATEROLE/BYPASSRLS. These
facts do not remove direct grants or certify complete application authority.

IF that observed owner creates new public tables under the inspected defaults,
the application receives SELECT/INSERT/UPDATE/DELETE plus TRUNCATE/REFERENCES/
TRIGGER/MAINTAIN. Sequence SELECT/UPDATE/USAGE, function EXECUTE and type USAGE are
also available. The actual future migration creator is unverified; owner aliases
are local to each receipt. No grant change or future seller ACL certification is
claimed. Default privileges depend on the actual creating role, not inherited
owner membership; current grants on existing tables are separate evidence.

The held approval/publication/file-grant/source-chunk immutability triggers cover
row UPDATE/DELETE, not TRUNCATE. PostgreSQL TRUNCATE does not fire DELETE triggers.
Thus the observed conditional TRUNCATE authority requires explicit release review
and denial proof before relying on those guards for application-role preservation.
No destructive statement was attempted. Do not blanket-revoke shared defaults,
grant app DDL, disable guards or change functions to SECURITY DEFINER as a shortcut.

Migration002 installs invoker guards on ALL updates of listings, listing_versions
and delivery_authorities; they SELECT seller_listing_publications even for general
writers. Migration004 adds a visibility-trigger publication lookup and outbox
upsert. Publication INSERT also reads approvals/connections/listings/versions/
authorities; session INSERT reads orders/publications. Permission and consumer
coverage must include those indirect reads/writes and shared billing with Workspace
off. SELECT FOR UPDATE needs UPDATE privilege as well as SELECT, even on rows
whose business fields remain immutable. No Beat DB credential is justified.

Source-bound requirements, ordering and exact redacted receipts are in
seller-release-permissions-continuation/outputs/SELLER-RELEASE-PERMISSIONS.md and
SELLER-PERMISSIONS-*.json. The source-search leads are not an exhaustive consumer
inventory. Actual creator/RLS, unwanted-permission denial, all-consumer exclusion,
owner migration, KMS/recovery/rolling fleet and both-provider enabled journey stay
open. The S1691 note and this supplement are unreviewed preparation, not previously
reviewed held docs. No application source, migration, grant or production setting
changed. R2/support/demand and all original full-release boundaries remain open.


## S1693 policy context and configured migration identity

Read-only metadata queries through both production application connections found
one applicable permissive ALL-command api_credits policy. USING and WITH CHECK
both call finance_entity_scope(entity_id). Its complete function body exactly
matches the held financial migration (SHA256
52258ac2370a05bfca0052c528c5987b720169d1cdc2711b1115c25e795dd2f9): it returns TRUE
when app.current_entity_id is absent/empty. Fresh diagnostic connections have
that setting absent/empty and active RLS. RLS enabled is therefore not tenant-
filtering proof. No policy function, application row or customer request was
executed; request/pool context and external consumers remain unverified. No
policy change is proposed by this observation.

The web's existing author DSN was used only for a separate bounded read-only
catalog connection, not Alembic. Its current role equals session role, differs
from the app, owns all ten named shared tables in its connection, has public
CREATE and current_schema public. Direct in-memory comparison establishes that
its role name equals the app-observed api_credits owner name. No role name, DSN,
credential or server address was emitted. The worker has no author connection.

The first combined target check returned FALSE. The separate follow-up finds
equal database names/server ports but different server addresses and different
DSN hosts/ports. Different routes are possible; same physical cluster is NOT
certified, nor is a wrong-database incident established. Do not change credentials
or endpoints to force equality. Bind target cluster/creator/release configuration
before migration; current login and source helper selection are not future
execution proof. S1691 absence and S1692 defaults were not rerun.

A scoped proposal and positive/negative proof plan are retained in
seller-release-permission-review-continuation/outputs/
SELLER-PERMISSION-REVIEW-PREPARATION.md. Prefer reviewed per-object narrowing of
unwanted rights on the nine new seller tables before admission, preserving shared
defaults/consumers, locks, invoker guards and the billing floor. This is not final
GRANT SQL or execution authority. No production/source/migration/grant/flag,
provider, customer-data, payment or model-credit operation occurred. Both previous
notes and this addition need independent review; all full-release gates remain.
