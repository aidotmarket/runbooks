# BQ-MONEY-PATH-DELIVERY-LEG-S1681 Gate 1

**Status:** Specification candidate; blocking product findings remain in sections 2.6 and 13. This artifact authorizes no implementation, AWS provisioning, secret creation, payment, deployment, production execution, or nightly activation. Opening this PR is not a Council verdict.

**Build Queue entity:** `build:bq-money-path-delivery-leg-s1681`

**Decision:** Extend S1656's disposable money-path environment with actual purchased-data delivery from seller-01's AIM Data device to buyer-01. Require a real Stripe test purchase, authenticated Trust Channel fulfilment, token-authorized direct S3 download, exact fixture bytes, and a separately proven seller Connect transfer before declaring the complete money path passed.

**Source trace:** The sibling `specs/BQ-MONEY-PATH-TEST-ENV-S1656-GATE1.md`, including amendments A1 and A2, was read first. Runbooks baseline is `3c88ca80ba6dcfb96b848290f10bfa3671972712` (fetched `origin/main`). All product citations below were read with `git show` at these immutable commits, not from checkout HEAD or memory:

| Citation prefix | Repository | Exact source SHA |
| --- | --- | --- |
| `backend:` | `aidotmarket/ai-market-backend` | `1c96b257c34938ea547be1eb818d5e902ff49f56` |
| `aim:` | `aidotmarket/aim-data` | `60b6eeea7643a2dd823045a1313cd7d11f92f9c3` (requested v1.23.2 source) |
| `environment:` | `aidotmarket/money-path-test-environment` | `24d884f1a48b73d1f65da07f09cce59bef587d65` |
| unprefixed runbook/spec paths | `aidotmarket/runbooks` | `3c88ca80ba6dcfb96b848290f10bfa3671972712` |

## 1. Decision and problem

S1656's `./bin/verify --from-clean-seed` proves listing publication, paid verification and Stripe setup/capture (AC1–AC12). Its acceptance summary gates seventeen browser criteria and a verification PaymentIntent, but no buyer order, device delivery, downloaded bytes or seller transfer (`environment:bin/verify:739-775`). The browser journey finishes the paid verification and gates those criteria (`environment:browser/s1590-money-path.spec.ts:1097-1129`). Verification payment is the seller buying verification, not buyer-01 buying the dataset.

The task brief records that no seller device has ever delivered a purchased dataset in this environment or production. Bundle `20260908T215737Z` is the supplied historical device/session proof reference, not delivery proof and not a fresh run of the v1.23.2 candidate. This authoring task did not rerun or certify that bundle. Every new acceptance run must independently establish the active seller device and then prove its response to the purchased order.

The new connected journey is: buyer-01 purchases seller-01's S3 fixture listing; the signed payment webhook requests fulfilment; the device at port 18081 answers over Trust Channel; the order reaches delivered; buyer-01 obtains and redeems a download token, GETs the presigned object directly, compares the bytes, and confirms receipt; a real test-mode Connect transfer must be recorded. Online, offline/reconnect and duplicate-delivery cases become mandatory inputs to the nightly result.

## 2. Current integration ground truth

### 2.1 Checkout and paid transition

`POST /checkout/create` selects TransactionService when `ENABLE_CANONICAL_TX` is true (`backend:app/api/v1/endpoints/checkout.py:148-171`); that setting defaults true (`backend:app/core/config.py:99`). Canonical checkout creates and links the Order and Transaction together (`backend:app/services/transaction_service.py:630-662`), then creates a real `mode="payment"` Stripe Session with order/transaction metadata (`backend:app/services/transaction_service.py:752-789`). The T-2026-000774 Buy Now fix is visible in the canonical description fallback, including missing/empty `short_description`, a 500-character cap and final `Data listing` fallback (`backend:app/services/transaction_service.py:762-770`). The legacy snapshot also uses `.get("short_description")` (`backend:app/api/v1/endpoints/checkout.py:114-128`). Do not mistake the legacy synthetic mock Session/PaymentIntent branch for the selected canonical path (`backend:app/api/v1/endpoints/checkout.py:233-268`).

T-2026-000776 already supplies the isolated purchase webhook admission: exact test environment/mode, false livemode, no account context, production-marker refusal, permitted event types `checkout.session.completed` and `payment_intent.succeeded`, and canonical order/transaction binding to a test buyer (`backend:app/api/v1/endpoints/webhooks.py:255-283`, `backend:app/api/v1/endpoints/webhooks.py:382-425`). This is narrower than a general synthetic exception; it does not itself prove both actors are the required manifest fixtures. The harness must check both independently.

The checkout handler validates paid status, amount, currency and stored order/Session/PaymentIntent/Transaction bindings (`backend:app/api/v1/endpoints/webhooks.py:1300-1343`). It invokes `mark_paid` when needed and repairs canonical payment on eligible retries (`backend:app/api/v1/endpoints/webhooks.py:649-675`). A committed `fulfillment_pending` retry checkpoint precedes `request_fulfillment`; successful initiation is required before the event becomes completed (`backend:app/api/v1/endpoints/webhooks.py:766-796`). The checkout return is feedback only, not payment authority (`backend:app/api/v1/endpoints/checkout.py:399-423`).

### 2.2 Online dispatch, offline queue and authorization

`request_fulfillment` locks the order, deduplicates existing pending/terminal work and limits fulfilment states (`backend:app/services/fulfillment_service.py:56-107`). An active Trust session selects immediate enqueue; an offline seller selects durable queueing (`backend:app/services/fulfillment_service.py:138-155`). Both paths enqueue the same `vai.fulfillment.deliver` payload for the seller device with the order-derived dedup key, commit and publish via the event bus (`backend:app/services/fulfillment_service.py:360-450`). Missing device registration is an error, not an offline success (`backend:app/services/fulfillment_service.py:417-421`).

`process_pending_for_seller` is a no-op at this pin (`backend:app/services/fulfillment_service.py:157-165`); reconnect recovery instead depends on the outbound-message drain in the WebSocket path (`backend:app/api/v1/endpoints/trust_websocket.py:749-759`). A test that merely calls the no-op does not prove offline recovery. FulfillmentBroker is the owner-checked agent wrapper around the same services, not another transport or a substitute for device response (`backend:app/services/fulfillment_broker.py:82-105`, `backend:app/services/fulfillment_broker.py:169-207`).

The `vai.fulfillment.response` handler validates the envelope, locks the order joined to its listing, requires both to belong to the authenticated seller, checks listing ID, and returns idempotent success for delivered/completed orders (`backend:app/api/v1/endpoints/trust_websocket.py:1279-1312`). FulfillmentService repeats the terminal-state lock/check (`backend:app/services/fulfillment_service.py:185-197`). These ownership and idempotency boundaries must remain intact.

### 2.3 Device, S3 branch and distinct authentication surfaces

The seed logs in seller-01 with password/TOTP, lists or mints the named product API key and hands its value to the host; it refuses ambiguous key state (`environment:seed/seed.py:437-477`). `PINNED_TOTP_BACKEND_SHA` is the requested backend SHA (`environment:seed/seed.py:51`, `environment:seed/seed.py:176-179`). The device contract checks exactly one active seller device, an active linked session, and the current container's fulfilment startup log (`environment:tests/device-contract.py:16-26`, `environment:tests/device-contract.py:30-72`). Its absent-key skip must become a hard acceptance failure.

AIM Data uses the existing registration identity plus `X-API-Key`, then performs hello/challenge/response/established, transcript signing and key derivation (`aim:app/services/trust_channel_client.py:220-244`, `aim:app/services/trust_channel_client.py:319-359`). Its handler registers `vai.fulfillment.deliver`, queues work, resolves the listing's source artifact and selects `_deliver_s3_object` only for `artifact.kind == "s3"` (`aim:app/services/fulfillment_service.py:74-100`, `aim:app/services/fulfillment_service.py:129-163`). The local-file branch streams chunks over Trust Channel (`aim:app/services/fulfillment_service.py:188-234`) and is forbidden for this delivery proof.

S3 delivery requires a configured/verified connection and role ARN; S3BrokerClient returns the presigned GET and its lifetime (`aim:app/services/fulfillment_service.py:284-322`). The device sends `vai.fulfillment.response` with URL, expiry and size, optionally a stored SHA-256, then requires the server's nested successful delivered acknowledgement before marking its log completed (`aim:app/services/fulfillment_service.py:352-386`). An S3 ETag is explicitly not a SHA-256 (`aim:app/services/fulfillment_service.py:358-365`).

**Authentication gap:** Trust Channel API-key readiness does not establish S3 broker readiness. S3BrokerClient requires `serial` plus `install_token` from serial storage and calls `settings.aimarket_url` (`aim:app/services/s3_broker_client.py:47-49`, `aim:app/services/s3_broker_client.py:138-158`). The backend broker validates that serial/install token (`backend:app/api/v1/endpoints/s3_connections.py:230-245`). The environment's device seed above provisions an API key, not proof of these broker credentials. No fabricated serial, copied production activation, direct database activation or implicit API-key fallback is permitted. Section 13 makes this a blocking provisioning finding.

### 2.4 Delivery record is not yet a working S3 download

The S3 response writes `orders.status='delivered'`, delivery method, URL under `delivery_config.gatekeeper_url`, nullable hash, size and timestamps, and completes the pending fulfilment (`backend:app/services/fulfillment_service.py:216-245`). It does not set `delivery_file_path` (`backend:app/services/fulfillment_service.py:216-280`). Canonical status synchronization is already implemented by the database trigger: the clean-schema migration maps delivered Order to delivered Transaction and records an event (`backend:alembic/versions/000_initial.py:19246-19279`, `backend:alembic/versions/000_initial.py:19873`). Preserve and verify this trigger rather than adding a second transition. The order transition table distinguishes delivered from completed (`backend:app/services/order_service.py:87-94`).

`POST /orders/{order_id}/download` calls `issue_download_token`, sets `no-store`, passes through `s3_scoped_credential`, but otherwise returns a reduced DownloadTokenResponse (`backend:app/api/v1/endpoints/orders.py:255-301`). The service requires ownership, delivered/completed status, no revocation, a valid access window and remaining downloads (`backend:app/services/order_service.py:345-381`). The presign branch additionally requires `delivery_file_path`, which the S3 response did not populate; it treats the stored S3 URL as a gatekeeper URL (`backend:app/services/order_service.py:1171-1192`). It issues a JWT and may build `s3_download_urls`, but the endpoint does not expose those fields (`backend:app/services/order_service.py:1208-1244`). Appending gatekeeper semantics to a pre-signed S3 URL is not a proven redemption mechanism.

The transaction download wrapper checks Transaction status before calling the same service (`backend:app/api/v1/endpoints/transaction_actions.py:152-171`), so its status readback also proves the installed database synchronization; do not assume the lack of an explicit Python transition means the Transaction stays unchanged. DeliveryService has a separate range-tracked proxy-stream record/finalization path; its `to_status="delivered"` is reached on complete byte coverage (`backend:app/services/delivery_service.py:604-675`). It is not called by the S3 response and must not be invoked by proxying fixture bytes through ai.market merely to advance status.

An empty S3 files list selects scoped credentials; large counts/size also select that delivery type (`backend:app/services/order_service.py:111-130`). The scoped branch returns credentials instead of a JWT (`backend:app/services/order_service.py:1142-1169`). S1681 deliberately uses one small, explicit object and must fail if it accidentally tests the scoped-credential branch.

### 2.5 Actual seller transfer trace

Payout is not wholly absent. Canonical checkout retains funds on the platform for a later transfer (`backend:app/services/transaction_service.py:756-758`). Buyer confirmation starts a 48-hour hold (`backend:app/services/transaction_service.py:896-908`). The confirmation endpoint calls OrderService and records the canonical confirmed event (`backend:app/api/v1/endpoints/transaction_actions.py:80-129`). SettlementService enforces the hold from that event, creates `stripe.Transfer.create` with an idempotency key, persists the order transfer ID/status and transitions the Transaction to settled (`backend:app/services/settlement_service.py:24-25`, `backend:app/services/settlement_service.py:44-125`). `backend:app/tasks/settlement_scheduler.py:18-50` selects eligible transactions and retries failures; the existence of this function does not establish a running scheduler in S1656.

Legacy `confirm_order` explicitly skips its transfer for Transaction-managed orders, then suppresses synthetic legacy transfers; only its remaining noncanonical path creates a Transfer (`backend:app/services/order_service.py:1346-1397`). It commits completed before attempting that transfer, and can subsequently record transfer failure (`backend:app/services/order_service.py:1318-1342`, `backend:app/services/order_service.py:1429-1443`). Neither completed nor `payouts_enabled=true` proves payment to the seller. External bank payout is Stripe's domain, separate from this Connect transfer (`backend:app/services/settlement_service.py:37-42`).

### 2.6 Blocking findings at the pinned baseline

1. S3 broker activation is unproven for the specified API-key install.
2. The S3 response can mark Order delivered without usable token redemption. This is a product integration gap, not a harness assertion to relax.
3. **The requested automatic delivery-to-payout/nightly leg is not implemented end to end.** Transfer code exists, but requires canonical delivery, buyer confirmation, an actual 48-hour hold and an executing settlement path. A clean-seed nightly run cannot truthfully report that transfer immediately. No existing test-only hold control was found in the traced settlement service. Payout remains a blocking product finding until a separately reviewed resolution is incorporated into this spec; it must never become a passing diagnostic or skipped criterion.
4. Environment `versions.env:2-9` pins AIM Data v1.23.1 / `3ca95783e133337f6f64ee3efa04835a8c0f9611`, not the requested v1.23.2 source. The new release digest must be resolved and verified, never invented.

## 3. Exact environment placement and shape

Reuse `/Users/max/Projects/ai-market/money-path-test-environment-s1656` on Titan-1 and Compose project `ai-market-money-path-s1656`. Keep backend 18000, frontend 13000, AIM Data 18081, PostgreSQL 15432, Redis 16379 and webhook proxy 18002 loopback-only. Preserve S1656 A2's runner-only runtime host networking and sole frontend build-stage host networking exception. Do not touch `/Users/max/aim-data-e2e-seller01` or another Compose project.

**Decision D1 — Real isolated S3, not an emulator.** Upload the committed fixture from the seller-side seed process directly to a dedicated private AWS test bucket, under `s1681/<run-id>/synthetic-listing.csv`. Use the existing authenticated backend S3 broker against that bucket. AWS has no Stripe-like test-mode switch: test isolation comes from a dedicated bucket, principal/role, allowlisted account and prefix. A local S3 stand-in would require endpoint/STS adaptations and would not establish real IAM/ExternalId/presign interoperability.

The broker uses STS's default credential chain and ExternalId (`backend:app/services/sts_assumer.py:45-82`); ExternalId is HMAC-derived from the serial and backend SECRET_KEY (`backend:app/core/seller_s3_credentials.py:11-16`). The real broker presigns without GETting object bytes and returns 300 seconds at this pin (`backend:app/api/v1/endpoints/s3_connections.py:404-444`), overriding the device's 900-second fallback. Upload and buyer download never transit ai.market. AIM Data may read the synthetic source for its local analysis; no raw source rows enter backend storage, Trust Channel chunk frames or evidence.

**Secret/config surfaces (proposed additions unless identified as existing):**

| Surface | Purpose and boundary |
| --- | --- |
| Infisical `ai-market-backend/test-env` | Retain existing S1656 injection and generated SECRET_KEY; never import production AWS credentials. Existing AWS production surfaces are documented in `aws.md:106-111`, not authority to reuse them. |
| `S1681_S3_BROKER_ACCESS_KEY_ID`, `S1681_S3_BROKER_SECRET_ACCESS_KEY`, optional `S1681_S3_BROKER_SESSION_TOKEN` | New test-only principal values; inject into backend as standard `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`. Assume only the recorded fixture role; no upload permissions. |
| `S1681_S3_SEED_ACCESS_KEY_ID`, `S1681_S3_SEED_SECRET_ACCESS_KEY`, optional `S1681_S3_SEED_SESSION_TOKEN` | Separate host seed/cleanup identity, Put/Get/Delete only within the test prefix plus narrowly necessary list permission. Never passed to backend, browser or AIM Data. |
| `S1681_S3_ACCOUNT_ID`, `S1681_S3_BUCKET`, `S1681_S3_ROLE_ARN`, `S1681_S3_REGION`, `S1681_S3_PREFIX` | Reviewed test target record, with prefix fixed under `s1681/`; region maps to `AWS_REGION` and `AWS_DEFAULT_REGION`. No endpoint override, production bucket, account wildcard or unrestricted role assumption. Actual identifiers are operator outputs recorded outside evidence/Git where sensitive. |
| `S1656_SELLER01_AIM_API_KEY` | Existing seed-managed device key, mapped to `VECTORAIZ_INTERNAL_API_KEY`; maintain the current API-key install and device identity. |
| Serial/install token in AIM Data serial store | Existing broker authentication surface; requires genuine test-only product provisioning bound to seller-01. No newly invented environment alias or plaintext seed value. Missing supported provisioning is a stop. |
| AIM Data API bases | Explicitly set both `ai_market_url` and the distinct `aimarket_url` to the disposable backend through their supported AIM_DATA/VECTORAIZ aliases. The latter controls S3BrokerClient (`aim:app/config.py:276`, `aim:app/services/s3_broker_client.py:47-49`). |

Require Block Public Access, ACLs disabled, encryption, TLS, exact role trust/ExternalId and short object lifecycle. Apply `aws.md` and `aws-s3.md` during authorized provisioning; this spec creates nothing. The test bucket/role identifiers, scoped credentials and bounded cost authorization must exist before execution; no fallback to the staging or production bucket. **Council question D1:** Does real S3 with distinct uploader and broker identities adequately prove non-custodial delivery, and can supported serial provisioning coexist with the API-key install without an auth redesign?

## 4. Purchase and download decisions

**Decision D2 — Canonical Stripe test data-order checkout.** Keep `ENABLE_CANONICAL_TX=true`, `STRIPE_TEST_MODE=true`, `DEMO_FULFILLMENT=false`. Drive buyer-01's authenticated `POST /api/v1/checkout/create` from the browser journey, then complete its returned real hosted Stripe checkout. Using the public purchase API from the signed-in browser context avoids pretending the owner-only synthetic listing page is buyer-visible (S1656 A2 item 3). Bind the exact buyer/seller/listing/Order/Transaction/Session/PaymentIntent, charge 2500 cents USD as the fixture listing price, and retrieve Stripe truth. Do not use `cs_e2e_mock_*`, `pi_e2e_mock_*`, paid verification, free purchase or direct status writes. Keep the S1590 paid-verification payment separate and unchanged.

The test webhook endpoint must subscribe to `checkout.session.completed` and `payment_intent.succeeded`; prove both signed provider deliveries in either order, and duplicate delivery through Stripe's own resend mechanism. Checkout completion is the fulfilment-driving branch; PaymentIntent success is backup payment confirmation. No `mode=setup`, transfer-created or bank-payout event substitutes for purchase completion. The existing setup event subscription remains for S1656. **Council question D2:** Is this canonical purchase surface sufficient despite synthetic listing visibility, with the existing narrow webhook exception and no additional suppression bypass?

**Decision D3 — Token issue, token redemption, direct presigned GET, exact bytes.** A 200 from `/orders/{id}/download`, a delivered label, a URL string or equal reported hashes alone is insufficient. The backend delivery correction must expose a usable signed token in an authenticated no-store response and a token redemption route that validates buyer/order/expiry/revocation/access window before redirecting to the device-issued S3 URL. Proposed route: `POST /api/v1/orders/{order_id}/download/redeem`, token in the request body, authenticated as the owning buyer, 303 Location to the unmodified presigned URL. Do not place the JWT into the S3 query. Token lifetime must not exceed the stored presign expiry; an expired device URL returns explicit expiry and requires the existing authorised refresh flow, never fabricated success. No raw-byte proxy is introduced.

Bind the stored S3 delivery to the purchased listing version and exact fixture object; populate sufficient durable metadata for authorization without treating a presigned object URL as a gatekeeper. Verify the existing database trigger advances linked canonical delivery consistently with Order, with one durable delivery event; do not add a duplicate event. Preserve scoped-credential and existing gatekeeper responses for their callers. Use an explicit single-object files manifest so this run requires the presign/token branch.

The runner holds the token/URL only in memory, redeems it, validates the Location is the configured test S3 object, fetches it directly and compares the entire response buffer byte for byte with `fixtures/synthetic-listing.csv`. Also record expected/observed length and SHA-256. A redirect elsewhere, changed byte, partial response, empty body, token-only response or scoped credential fails. Negative cases cover wrong buyer, wrong order, tampered/expired token, revoked access and pre-delivery issue. **Council question D3:** Is authenticated token redemption to the seller-issued S3 URL the minimal correct product repair, with expiry and version binding preserved?

## 5. Payout decision and safety boundary

**Decision D4 — Require an actual test Connect Transfer; record the current automation gap as blocking.** After byte verification buyer-01 explicitly confirms receipt through the canonical confirmation route. The target assertion is one real `livemode=false` Transfer to seller-01's seeded Custom account, amount equal to the durable seller share, currency USD, matching Order/Transaction metadata and transfer group, unreversed, with matching local `stripe_transfer_id`, completed transfer status and settled Transaction. Pin the fee/share expectation from the approved fee policy during implementation; require gross = platform fee + seller share. A fabricated transfer, manually funded substitute, payout-ready projection, verification capture or completed Order does not pass.

The 48-hour hold is not shortened here. No clock jump, backdated confirmation, SQL eligibility edit, direct harness-created Stripe Transfer, admin impersonation or legacy flag switch may satisfy D4. This design records that **payout for the requested short clean-seed/nightly journey is not implemented**, while accurately preserving the existing general settlement implementation in section 2.5. Before implementation dispatch, Council/product authority must choose and document a bounded real settlement schedule or an explicitly test-only timing design, its safety predicates, file manifest and acceptance timing. Until then the full money-path command fails closed and no nightly green result is possible. **Council question D4:** What approved settlement timing and executor can prove the genuine transfer from the same clean-seed order without bypassing the production hold? Is any test-only timing exception acceptable, or must the journey be redesigned as a durable multi-day run?

All S1656/A1/A2 live-key boot refusals, ingress restriction, production-marker checks, three-user isolation, read-only production comparison and teardown rules remain mandatory. New raw-data egress is exclusively seller seed → test S3 and test S3 → AIM Data/buyer. No production execution, customer identity or copied production credentials. Retain A2's disclosed KMS/Vertex exceptions without widening them. Only an authorized future operator may provision the scoped AWS resources or activate the nightly job.

No outbound seller email from an offline sale may leave the disposable environment; verify the synthetic notification exclusion or a local sink before testing. If existing behavior requires an external message, stop. S3 credentials, tokens, URLs, object keys, raw source rows, TOTP, emails, Stripe IDs and webhook payloads must not enter screenshots, HARs, traces, logs or evidence. Evidence uses hashes/booleans and allowlisted labels.

## 6. Seed and data isolation

Keep exactly seller-01, buyer-01 and TOTP-disabled seller-02, with the backend-owned system principal tolerated only as in the existing seed. Preserve manifest names, active seller capability, ordinary verification pay-in state separation and the Custom test Connect account (`environment:seed/seed.py:125-179`, `environment:seed/seed.py:215-292`). Buyer-01 receives no seller/Connect role or fabricated payout authority.

The seller-side seed computes the committed fixture SHA-256/length, uploads only that file to the run-owned test S3 key, and records a restricted cleanup manifest. Seed establishes the genuine seller-01 broker activation through supported product provisioning, creates/verifies an AIM Data S3 connection, registers the one object and publishes its listing via the real signed publish flow. Publish with `fulfillment_type=ai_queryable` (the existing default, `backend:app/models/marketplace.py:133-141`) and an explicit single-object S3 manifest; `file_download` would bypass Trust Channel (`backend:app/services/fulfillment_service.py:127-129`), and `reference` is not this journey. Assert both the listing fulfilment type and resolved source kind S3 before any buyer purchase. Do not upload a local-file listing and patch its kind afterward. Preserve original S1656 fixture bytes and paid-verification criteria; the S3 fixture must support that same local verification journey or the change requires an amendment.

Run the online case and offline case in separately guarded clean-seed phases inside the one command. Each phase recreates the same three users and one listing; each has its own opaque order/transaction and test object references. This avoids duplicate-active-purchase constraints and role mutation. The unchanged S1656 role/verification sequence runs in the online phase; the offline phase is an additional clean case. Capture phase evidence before reset and verify cleanup, no outstanding unresolved settlement and no pending work before advancing. D4's unresolved settlement timing currently blocks this phase progression.

Reset retains `test-env`, deletes only run-owned test S3 objects after target checks and revokes only that run's ephemeral access where supported. Terminal teardown additionally removes newly provisioned test-only resources using their recorded ownership, verifies absence and records provider-retained Stripe objects honestly. Never delete an unrelated bucket/role or reuse another run's object.

## 7. Connected journey and fault branches

1. Validate clean Git, both spec pins, exact images and test target guards before secret injection or evidence creation. Perform guarded reset/seed; establish current seller device, handler startup and active trust session.
2. Complete S1656's original role, publication, setup/webhook, verification and capture proofs with the S3-backed synthetic fixture. Verify the actual source object and local listing binding; never follow the returned production marketplace URL.
3. Sign in buyer-01, create the canonical data checkout, complete Stripe's test hosted flow and observe signed payment processing. Assert one payment transition and one queued outbound fulfilment request for that order/device.
4. Observe the real device handle `vai.fulfillment.deliver`, broker presign, `vai.fulfillment.response`, successful delivered acknowledgement, completed pending fulfilment, delivered Order and delivered canonical Transaction. Deadline: 120 seconds after accepted payment while device is online. All timestamps and correlations come from independent read-only service/DB observations.
5. Issue/redeem the token, directly GET and compare bytes within the actual returned URL lifetime. Then buyer-01 confirms receipt. Execute and observe only the approved D4 settlement path; at present this is blocked rather than passing.
6. Redeliver the original signed Stripe events using the provider. Exercise application-message redelivery through the real registered device over a fresh encrypted Trust Channel envelope: resend the same business response/request correlation, not old ciphertext. A test driver may use the device's existing client and handler; it must not impersonate another identity or call the backend response service directly. Record this driver use. Require unchanged delivery credentials hash, delivered timestamp, canonical event count, charge count and transfer count. Multiple device processing logs are permissible; multiple durable business deliveries are not.
7. In the second clean phase, stop only the exact-label S1656 AIM Data container before buyer purchase, verify session inactivity, then buy. Observe durable pending outbound work and no delivered state/token during a 30-second observation window. Restart the same install/volumes without reseeding, prove fresh session and real queue drain, then delivered and byte equality within 180 seconds. Do not reissue payment or manually invoke fulfilment to recover it. Duplicate Stripe delivery while offline must leave one logical request. Restore the device in a finally path even if the case fails.
8. Recheck original safety assertions and production snapshots, source identities and clean worktree. Only the conjunction of all criteria may create `summary.json`.

## 8. Independently testable acceptance criteria and evidence

Every criterion is reachable from `./bin/verify --from-clean-seed`, checked outside the application code under test, and reports its own required boolean. A unit test, log phrase or mocked provider cannot substitute. Supporting negative contract tests may use throwaway local clones/services and must not reach production.

| Criterion | Required independent proof |
| --- | --- |
| DL1 — Provenance and seed | Pre-write mutual pin validation; exact v1.23.2 SHA/digest; three fixtures; genuine broker activation; one active seller-01 API-key device/session; exact test S3 target and source kind. Missing key/serial or a skipped device check fails. |
| DL2 — Original regression | All original seventeen S1656 gated browser checks, persisted published verification epoch and real manual test authorization/capture pass, with original expected amounts and no production effect. |
| DL3 — Actual data purchase | Browser/API buyer identity, real hosted payment Session, retrieved test PaymentIntent, 2500 USD cents, linked canonical Order/Transaction and seller-01; no mock IDs, free purchase or verification-payment substitution. |
| DL4 — Signed payment and dispatch | Both required provider event types observed; signature validation and stored binding; one payment transition; durable order-correlated fulfilment request. Test both arrival orders and provider redelivery, with no second charge/payment event. |
| DL5 — Online device delivery | Real device request/response/ack and source S3 branch; pending completion, Order and Transaction delivered within 120 seconds; no raw chunk transmission or proxy stream. |
| DL6 — Download integrity | Authenticated token issue, real redemption, allowed S3 GET 200, complete byte equality to the committed fixture, equal lengths and SHA-256 within expiry; download counter changes exactly once for that issuance. |
| DL7 — Download refusals | Separate isolated probes for nonbuyer, wrong order, tampered/expired token, revoked order and pre-delivery issue; no usable URL or bytes, no unauthorized counter consumption. Scoped-credential output fails this single-object scenario. |
| DL8 — Offline recovery | Device down and session inactive before payment; one durable pending request, no delivery/token for 30 seconds; same device reconnect drains work without repurchase/reseed; delivered and matching bytes within 180 seconds. |
| DL9 — Business idempotency | Provider duplicate events and genuine device response redelivery leave one logical fulfilment, one delivered transition per entity, original delivered timestamp/credentials hash, one charge and no duplicate transfer; replay also after confirmation/settlement cannot regress terminal state. |
| DL10 — Seller paid | Real retrieved test Connect Transfer plus local completed transfer record and settled Transaction, correct seller destination, share/currency/group/metadata, no reversal and exactly one transfer. **Blocking at the supplied baseline; cannot be skipped or inferred.** |
| DL11 — Isolation and cleanup | No production effect, raw rows or secrets in backend/evidence; no real notification; exact-label device restored, test objects cleaned and no ambiguous pending order/transfer left before a reset. |
| DL12 — Nightly integration | The command executes the wrapper contract: same command and pins, nonzero propagation/no summary on a deliberately failed local test, and overlap refusal without reset or success. Release additionally requires one real scheduled invocation with all original checks and DL1–DL12; a manual summary alone does not prove scheduler activation. |

**Decision D5 — Extend the fail-closed summary and mutually pin the new head.** Keep the existing source/environment/A2 provenance and original paid-verification fields (`environment:bin/verify:764-775`). Add schema version, `spec_delivery_gate1_sha`, baseline environment SHA, verified image digests, fixture expected hash/length, per-phase source/clean-seed identity and `delivery_cases.online` / `delivery_cases.offline`. Each case contains local listing/order/transaction/device/session IDs; hashed provider/request correlations; checkout mode, amount/currency/livemode; event type/dedupe outcomes; queued/sent/response/delivered timestamps; source kind; token-issued/redeemed booleans and expiry; HTTP status, observed byte count/hash and byte-equality boolean; confirmation timestamp; transfer reference hash, amount/currency/livemode, destination-match boolean, local transfer status and Transaction status. Add duplicate before/after counts and credential hashes, `per_delivery_criterion` DL1–DL12, cleanup/production comparison results and invocation kind (manual or nightly), start/end/exit identity. The scheduled receipt references the completed command summary, avoiding a self-referential success gate. Never store raw provider objects, token values or presigned URLs.

The actual final environment head is an implementation output, not `24d884...` and not a placeholder accepted by the verifier. After the final environment PR, the runbooks release-pin amendment in Chunk D must name that exact immutable head in both S1656 A2 and this spec's release record. The operator supplies `S1656_SPEC_A2_SHA` and new `S1681_SPEC_SHA` as full, locally present runbooks commits; they may be the same commit carrying both records. Verification reads both with `git show`, requires the two exact final-head records to equal its clean environment HEAD, validates the pinned product versions and rejects missing/malformed/nonexistent/stale pins before injection, evidence root or any write. No fetch during verify. Recheck HEAD/clean state at summary creation. This avoids embedding the spec's own future SHA in the environment commit and preserves A2's mutual binding (`environment:bin/verify:30-49`).

Progressive redacted diagnostics may exist after preflight, but no `summary.json` may exist unless all required criteria, including payout, are true. Write it atomically as mode 0400 under the existing mode-0700 external evidence root; missing fields fail rather than defaulting true. Add executable negative cases for both pins, mid-run source drift, missing device, byte mismatch, duplicate business effects and absent/failed transfer. **Council question D5:** Are these independent correlations and dual exact-head pins sufficient to prevent a healthy device, old bundle, verification payment or partial delivery being reported as the complete money path?

## 9. Operator runbook requirement

Implementation is incomplete until `money-path-test-environment.md` is updated in the reviewed runbooks chunk, retaining frontmatter, A–K structure and literal `## When it breaks`. Cover exact S3 ownership/credentials/cost bounds; supported broker activation; device readiness; purchase versus paid verification; online/offline/replay procedures; token expiry and byte verification; confirmation/settlement timing; required evidence fields; nighttime lock/schedule ownership; and exact reset/teardown recovery.

Correct stale Express wording at `money-path-test-environment.md:184-188` to the implemented Custom account (`environment:seed/seed.py:247-292`, sibling A2 item 2). Add failure rows for missing serial/install token, wrong API base, STS/ExternalId refusal, non-S3 source, absent device, queue not draining, response authorization mismatch, Order/Transaction divergence, missing delivery path, token/presign expiry, byte mismatch, transfer absent/hold pending/failed, stale mutual pins and overlapping nightly invocation. No advice to patch SQL or weaken guards. Regenerate only existing `INDEX.md` and `ERRORS.md` through `scripts/index.py` if needed for registration. This authoring PR changes none of those files.

## 10. Non-goals

- Production execution, deployment, Railway changes, customer journeys or production payout.
- Trust Channel protocol, cipher, framing, handshake, ownership or replay-rule changes.
- OAuth-install registration (T-2026-000780, shipped v1.23.2); replacing the specified API-key install with OAuth is not a workaround.
- Local-file streaming through ai.market, raw-data proxy custody, bulk/scoped-credential delivery, folder grants or alternate fixtures.
- Replacing paid verification, changing its prices/amounts, synthetic listing visibility or seller readiness rules.
- Changing production settlement policy, bank payout execution, live Stripe objects, fake transfers, time travel or manually marking success.
- A new staging environment, CI SaaS execution with copied secrets, production nightly harness changes or new governance tooling.

## 11. Finite implementation chunks

At most four chunks, each exactly one PR to one repository. Each PR names its exact base and candidate SHA, tests and complete manifest. No extra file, repository or fifth chunk is implicit. Findings in section 13 block dispatch until resolved in this design; if resolution needs different files, amend the applicable manifest before implementation. Existing delivery APIs and S1656 acceptance cannot be silently relaxed to fit a manifest.

### Chunk A — backend S3 delivery integration

**Repository:** `aidotmarket/ai-market-backend`, baseline backend SHA above.

**Manifest:** `app/services/fulfillment_service.py`; `app/services/order_service.py`; `app/api/v1/endpoints/orders.py`; `app/schemas/order.py`; new `tests/test_s1681_s3_delivery.py`.

**Boundary:** D3's durable single-object S3 delivery metadata, verification of existing canonical synchronization, token issue/redemption, access/expiry/version checks and atomic/idempotent business transitions. Preserve existing Trust response authorization and protocol; focused concurrent duplicate, unauthorized token, expired URL and scoped/gatekeeper regression tests. No payout/auth/hold changes are authorized by this manifest. D4 resolution requiring product changes must explicitly revise this chunk before dispatch.

### Chunk B — environment S3 seed and connected acceptance

**Repository:** `aidotmarket/money-path-test-environment`, baseline environment SHA above.

**Manifest:** `versions.env`; `compose.yaml`; `compose.aim-data.override.yaml`; `bin/preflight`; `bin/up`; `bin/seed`; `bin/reset`; `bin/down`; `bin/verify`; `seed/seed.py`; `seed/host-seed.py`; new `seed/s3-fixture.py`; `browser/s1590-money-path.spec.ts`; new `browser/s1681-delivery-leg.ts`; `tests/device-contract.py`; `tests/compose-contract.sh`; `tests/test-seed-contract.py`; `tests/test-journey-contract.py`; `tests/test-verify-fail-closed.sh`; new `tests/test-delivery-contract.py`.

**Boundary:** Exact product/digest repins (including TOTP pin if backend advances), test credential injection, approved genuine broker provisioning, direct fixture upload/cleanup, source-kind proof, connected purchase/delivery/download/confirmation and approved payout observation, offline/replay faults and D5 summary. Preserve all existing S1656 checks. No fixture-byte change, local activation fabrication, provider mock or product implementation hidden in the test helper. Broker provisioning must be resolved before this chunk starts.

### Chunk C — nightly harness entry point

**Repository:** `aidotmarket/money-path-test-environment`, exact merged Chunk B as base.

**Manifest:** new `bin/nightly`; new `config/com.aimarket.s1681-money-path.plist`; new `tests/test-nightly-contract.py`; `README.md`.

**Boundary:** A Titan-1 nightly wrapper for the same clean-seed command, absolute working directory, exact locally available spec/environment pins, restricted logs, atomic exclusive lock shared with manual verify, bounded timeout and nonzero failure propagation. Proposed schedule is 02:00 Europe/Madrid host time; never run concurrent reset/seed, kill another owner's run or label a lock refusal successful. The baseline has no committed nightly entry point in this environment; this is an addition, not a claim that a scheduler is already installed. Do not install/activate it until DL1–DL11 and D4 are resolved and proven. Final timeout/schedule compatibility must follow the approved settlement decision; no 48-hour run may silently overlap nightly launches. The final environment candidate is this PR's exact merged head, with no later unreviewed repin.

### Chunk D — runbook, release records and registration

**Repository:** `aidotmarket/runbooks`.

**Manifest:** `money-path-test-environment.md`; `specs/BQ-MONEY-PATH-DELIVERY-LEG-S1681-GATE1.md`; `specs/BQ-MONEY-PATH-TEST-ENV-S1656-GATE1.md`; `INDEX.md`; `ERRORS.md`.

**Boundary:** Section 9 instructions, reviewed resolutions/mandates, final environment head and both exact-head release records, original A1/A2 preservation and generated index changes only. No new implementation files. Review the exact candidate before using its SHA for acceptance. Evidence remains outside Git; activation and a genuinely scheduled run are later authorized execution, not achieved by merging documentation.

## 12. Council review checklist

Follow current `runbooks/gate-procedure.md:48-74`: CC, GLM and DeepSeek are the three voters; money/auth/customer-data scope requires all three valid approvals and unanimity, with builder excluded. This task requests authoring and a PR, not dispatch or votes. Re-read the live gate contract before any future dispatch.

- [ ] Exact spec SHA, all source pins and each D1–D5 decision/question reviewed; every mandate recorded with immutable response and model identity.
- [ ] Real S3 resource/identity isolation, supported broker provisioning and API-key install coexistence resolved without OAuth or protocol changes.
- [ ] Canonical purchase and existing T-2026-000774/T-2026-000776 behavior distinguished from legacy mocks and paid verification.
- [ ] S3 response→Order→Transaction alignment and real token redemption specified without raw-byte custody or leaked credentials.
- [ ] Offline queue drain and business-message replay exercise real services; unauthorized response and terminal-state behavior preserved.
- [ ] D4 has a concrete approved settlement timing/executor; no fake payout, hidden hold bypass or green-with-payout-skipped result.
- [ ] Original S1656 AC1–AC12/A1/A2 obligations preserved; dual mutual pinning and incomplete-summary refusal executable.
- [ ] Four PR manifests sufficient after blocker resolution; runbook, cleanup, budgets, scheduler ownership and timeout all concrete before execution.

## 13. Open questions and stop conditions

1. **Broker provisioning:** identify the supported test-only serial/install-token issuance/activation route and prove seller-01 ownership alongside its existing API-key Trust identity. If this needs a new product auth route, stop and amend the design/manifests; no invented serial, stored production token, OAuth substitution or seed SQL.
2. **Payout:** resolve D4 before build dispatch. Existing general Stripe transfers are real implementation, but the requested same-run automatic payout is not. Decide real delayed execution versus reviewed test-only timing, name the executor and exact files, and prove failure/retry/idempotency semantics. Until then DL10 is blocking and full acceptance cannot pass.
3. **S3 resources:** authorized operator must record actual test account/bucket/role, ExternalId trust, separate uploader/broker scope, region, cleanup ownership and a finite AWS/Vertex spend ceiling. No missing value may fall back to ambient host credentials or production resources.
4. **Source identity:** resolve v1.23.2 tag-to-`60b6eeea7643a2dd823045a1313cd7d11f92f9c3` and actual OCI digest, new backend candidate and matching seed TOTP pin. The historical active-session bundle and v1.23.1 environment image are not substitutes.
5. **Delivery semantics:** if correct token redemption/version binding/canonical synchronization needs files outside Chunk A, amend before building. Any proposal to accept delivered without bytes, or proxy bytes through ai.market, stops this design.
6. **Nightly lifecycle:** confirm named operator ownership and how credentials/teardown-token renewal and settlement duration fit the schedule. Pending money, expired credentials, absent resource ownership or another active run means failure/blocked execution, never reset underneath it.
7. **Universal stop:** production origin/marker, live Stripe object/key, wrong seller/buyer/device/listing, unexpected destination, raw data leakage, unsupported activation, duplicate charge/transfer, byte mismatch, missing required criterion or unreviewed source drift aborts the run. Preserve redacted diagnostics and exact identities; do not write `summary.json`, weaken a check, broaden scope or claim completion.
