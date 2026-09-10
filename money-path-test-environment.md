---
title: S1656 Money Path Test Environment
owner: mars
last_verified: '2026-09-09'
aliases:
  - BQ-MONEY-PATH-TEST-ENV-S1656
  - BQ-MONEY-PATH-DELIVERY-LEG-S1681
  - S1681 delivery and settlement
  - S1656 money path
  - money-path-test-environment
  - ai-market-money-path-s1656
error_signatures:
  - spec final head differs
  - spec product identity differs
  - AWS CLI v2 is required for conditional S3 uploads
  - offline retry refused
  - missing or conflicting pin
  - "s1681: pending-settlement; environment mutation refused"
  - live Stripe secret-key prefix refused before network access
  - live Stripe publishable-key prefix refused before network access
  - Stripe test key does not belong to the pinned platform Account
  - FRONTEND_URL must equal http://localhost:13000
  - source checkout is dirty
  - checkout differs from the recorded SHA
  - seller-01 effective seller capability is not active
  - Stripe redelivery must record duplicate without another finalization
  - backend did not record Stripe provider redelivery as duplicate
  - 'AC12 failed: parsed and normalised production snapshots differ after volatile fields were removed'
  - 'container/network/volume target <id> lacks the exact S1656 ownership label'
  - deployment marker observed; seed refused
  - immutable mint-policy validation failed
  - Cloudflare targets remain or absence is unproved
  - pinned host-network browser-runner cannot reach all localhost origins
---

# S1656 Money Path Test Environment

This page operates the disposable S1656/S1681 money-path environment at `aidotmarket/money-path-test-environment@6a1cfcfa5fc39f88a78ee5e15b1cff5f67ae0aa5` (S1710 folds of `e2028111f66d2b95d0c361d2c888b549b16520f8`; source references written `environment:file:line` that name `e2028111` remain valid for every file except `seed/s3-fixture.py`, `seed/host-seed.py` from line 273 and `tests/test-seed-contract.py`, which PRs #13 and #14 changed): paid verification, buyer purchase, direct S3 delivery and genuine test Connect settlement. Source references written `environment:file:line` below all refer to that immutable commit, read with `git show`; the permanent checkout must be clean at that head before execution. S1709 is a documentation/source verification date, not a connected acceptance result.

## A. Purpose and safety boundary

Use this environment to prove one connected synthetic flow: three-account seed, AIM Data registration and publication, local listing render, just-in-time card setup, signed Stripe test webhook delivery and deduplication, payment readiness, signed scan/report processing, manual authorization and capture, GA role hiding, and before/after production no-effect checks.

The safety boundary is fixed:

- All application data is newly migrated into project-owned local volumes. Never restore a production dump, copy a customer row, reuse a production cookie, or join a shared Docker network or volume.
- Stripe keys and objects are test-mode only. Any `sk_live_`, `pk_live_`, live-name Stripe variable, `RAILWAY_ENVIRONMENT`, or `PRODUCTION` value fails before migrations, seed, health-ready, or a Stripe call.
- No Railway deployment or application-variable write is part of this environment. The only allowed production-zone mutation is the exact temporary Cloudflare route and DNS record named below.
- The public webhook hostname exposes only `POST /api/v1/webhooks/stripe` through the path-restricted proxy. Every other path or method returns 404.
- The VZ publish response contains a known hard-coded production `marketplace_url`. The runner records that it was returned, never navigates to it, and renders the listing at the local frontend URL built from `listing_id`.
- Acceptance uses the real local services, Stripe-hosted test setup, Stripe provider delivery, and the pinned browser runner. Mocks, intercepted API routes, ad-hoc SQL, role mutation, wrapper success text, and unit tests cannot replace the external evidence.
- A production marker in either before/after snapshot is a stop condition. Preserve the evidence, tear down safely, and escalate; do not adjust production to make the comparison pass.

## B. Exact placement and topology

The private repository is cloned on Titan-1 at:

```text
/Users/max/Projects/ai-market/money-path-test-environment-s1656
```

Docker Compose project `ai-market-money-path-s1656` owns its containers, private bridge, and volumes. Every service except `browser-runner` uses that private bridge. Only `browser-runner` uses `network_mode: host`; it publishes no port and mounts the browser code, fixture, package manifests, and Playwright config read-only. Backend, frontend, PostgreSQL, Redis, webhook proxy, and AIM Data also map known production API and Railway database hostnames to loopback as a second guard.

| Service | Exact host binding | Purpose |
| --- | --- | --- |
| frontend | `127.0.0.1:13000 -> 3000` | Browser UI at `http://localhost:13000` |
| backend | `127.0.0.1:18000 -> 8000` | Test API and `http://localhost:18000/health` |
| AIM Data | `127.0.0.1:18081 -> 80` | Installed-product UI and `/api/health` |
| webhook proxy | `127.0.0.1:18002 -> 8080` | Exact Stripe webhook path only |
| backend PostgreSQL | `127.0.0.1:15432 -> 5432` | Disposable backend database |
| backend Redis | `127.0.0.1:16379 -> 6379` | Disposable backend cache |

The externally reachable test ingress and its immutable bindings are:

| Item | Exact value |
| --- | --- |
| Webhook URL | `https://s1656-money-path-webhook.ai.market/api/v1/webhooks/stripe` |
| Cloudflare tunnel | `206c9e81-b201-480f-b6ed-c930c72974f3` (`s1656-money-path`) |
| DNS record | `e506f0ee3753458157b91092bf5b8ea2` |
| DNS target | `206c9e81-b201-480f-b6ed-c930c72974f3.cfargotunnel.com` |
| Stripe test endpoint | `we_1UBctVRx8FzPjYyVDIFWEFMT` |

The proxy preserves the raw request body and `Stripe-Signature`, limits the body to 1 MiB, and forwards only to `http://backend:8000/api/v1/webhooks/stripe`. `cloudflared` is outbound-only and connects only to the proxy.

## C. Source and image identity

`versions.env` is the authority for all source and image pins:

| Product/runtime | Pinned identity |
| --- | --- |
| ai-market-backend | `5cedc41fa8c0ae0fc02d2b6b9fa7b9a7461a9529` |
| ai-market-frontend | `943429b586fa4acd55f81f23ded5005cbcf841e1` |
| AIM Data source | `0f18e89443b5ba9b2c99d326e056abab5259886e` |
| AIM Data image | `v1.23.3-rc.1@sha256:b4744a88a670f0ed9a882d8961702193f377d5798b73777c82c06ef211c1807c` (stable release tags are accepted; the digest is mandatory) |
| Browser runner | Playwright `1.61.0`, Chromium revision `1228`, browser `149.0.7827.0` |

The final head after S1709 was `e2028111f66d2b95d0c361d2c888b549b16520f8` (environment PRs #10/#11/#12); after the S1710 G9 IAM transport fold ([PR #13](https://github.com/aidotmarket/money-path-test-environment/pull/13), S1656 A2 item 15, S1681 Amendment G10) it was `f3ffcd4895825f0c0981a45f43e40e86722db648`; after the S1710 trust-propagation fold ([PR #14](https://github.com/aidotmarket/money-path-test-environment/pull/14), S1656 A2 item 16, S1681 Amendment G11) it is `6a1cfcfa5fc39f88a78ee5e15b1cff5f67ae0aa5`. S1656 A2 item 14 and the S1681 Chunk D release record carry the same environment, product, image and TOTP identities. After this PR merges, supply its full merge commit as both `S1656_SPEC_A2_SHA` and `S1681_SPEC_SHA`, already present in `S1656_RUNBOOKS_REPO` (default `/Users/max/Projects/ai-market/runbooks`). It cannot be embedded in its own document. `environment:bin/check-settlement:34–58` requires each spec's literal final-head record, backend/AIM Data source and full image value; S1681 also requires G9 and ancestry from `08d8433d3564b23353c800b1a0cd4a32874478fb`. Missing, malformed, nonexistent or stale pins refuse before injection/evidence writes; verification never fetches. `environment:bin/verify:34–63` checks clean HEAD and resumes an active run. HEAD/pins are checked again before summary creation (`environment:bin/check-settlement:718–723`).

Historical evidence remains bundle `20260908T215737Z`, environment `24d884f1`, A2 `dbc65504`: original AC1–AC12 and seller-01 active Trust session, not S1681 delivery/settlement proof. The baseline v1.23.2 and separately reviewed registration-fix RC identities are recorded in both specs. Stable v1.23.3 promotion follows connected proof.

`./bin/up` prepares managed clones under `.state/sources/{backend,frontend,aim-data}` from the exact GitHub remotes, requires clean working trees, fetches the exact 40-character SHAs (shallow, depth 1) and checks them out detached. `./bin/preflight` refuses short SHAs, branches, dirty trees, wrong remotes, tag/SHA disagreement, image-digest disagreement, or browser package/revision drift. Do not repair a pin failure by moving a tag, selecting `main`, editing a managed checkout, or substituting another image.

Successful preflight writes `.runtime/aim-data-image-digest.json`. After local backend/frontend builds, `up` writes `.runtime/image-digests.json` with the three source SHAs and image digests. These runtime files support identity inspection; they are not AC1-AC12 release evidence.

## D. Secrets and credential split

The dedicated application-secret boundary is Infisical project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment `test-env`, secret path `/`. It has no Railway sync. The lifecycle reads the authorized machine identity from `~/.config/infisical/sysadmin-token`, sets `INFISICAL_API_URL=https://secrets.ai.market`, and injects the environment through:

```sh
infisical run --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=test-env -- <command>
```

The authoritative core `test-env` secret contract is `e2028111:README.md:97-126`; `MCP_API_KEY_SECRET` is required for device key minting (`e2028111:bin/preflight:148-155`). The core names and S1681 additions are listed below (the A2 KMS/Vertex additions below also apply):

```text
STRIPE_TEST_SECRET_KEY
STRIPE_TEST_PUBLISHABLE_KEY
STRIPE_TEST_WEBHOOK_SECRET
STRIPE_PAYIN_PLATFORM_ACCOUNT_ID
SECRET_KEY
MCP_API_KEY_SECRET
SERIAL_TOKEN_SECRET
S1656_SELLER01_AIM_API_KEY
S1681_SELLER01_SERIAL
S1681_SELLER01_SERIAL_BOOTSTRAP_TOKEN
S1681_SELLER01_SERIAL_INSTALL_TOKEN
S1681_S3_ACCOUNT_ID
S1681_S3_BUCKET
S1681_S3_ROLE_ARN
S1681_S3_REGION
S1681_S3_PREFIX
S1681_S3_BROKER_ACCESS_KEY_ID
S1681_S3_BROKER_SECRET_ACCESS_KEY
S1681_S3_SEED_ACCESS_KEY_ID
S1681_S3_SEED_SECRET_ACCESS_KEY
TOTP_ENCRYPTION_KEY
E2E_SYNTHETIC_SELLER_01_EMAIL
E2E_SYNTHETIC_SELLER_01_PASSWORD
E2E_SYNTHETIC_SELLER_01_TOTP
E2E_SYNTHETIC_SELLER_02_EMAIL
E2E_SYNTHETIC_SELLER_02_PASSWORD
E2E_SYNTHETIC_BUYER_01_EMAIL
E2E_SYNTHETIC_BUYER_01_PASSWORD
POSTGRES_PASSWORD
AIM_DATA_POSTGRES_PASSWORD
VECTORAIZ_SECRET_KEY
AIM_DATA_APIKEY_HMAC_SECRET
AIM_DATA_KEYSTORE_PASSPHRASE
CLOUDFLARE_TUNNEL_TOKEN
CLOUDFLARE_S1656_TEARDOWN_API_TOKEN
CLOUDFLARE_S1656_TUNNEL_ID
CLOUDFLARE_S1656_DNS_RECORD_ID
CLOUDFLARE_S1656_HOSTNAME
CLOUDFLARE_S1656_TEARDOWN_TOKEN_ID
CLOUDFLARE_S1656_MINT_POLICY_SHA256
```

The live-name variables `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, and `STRIPE_WEBHOOK_SECRET_PREVIOUS` must be absent or empty. `SECRET_KEY` is test-env-only and at least 32 characters. `TOTP_ENCRYPTION_KEY` is a test-env-only URL-safe base64 value decoding to exactly 32 bytes. The Stripe secret/publishable keys must start `sk_test_`/`pk_test_`; the webhook secret must be canonical `whsec_`; and the platform Account must be the exact test Account returned by the test secret key.

A2 item 1 additionally requires `GCP_SERVICE_ACCOUNT_JSON`, `GCP_PROJECT_ID`, `GCP_LOCATION`, `GCP_KMS_LOCATION`, `GCP_KMS_KEYRING`, `GCP_KMS_PLATFORM_KEY_NAME=s1656-test-signing-key`, `GCP_KMS_ENCRYPTION_KEY_NAME=s1656-test-encryption-key`, `DATA_VERIFICATION_PLATFORM_PUBLIC_KEY_PEM` and `VERTEX_GEMINI_KEY`. These retain the disclosed production-project credential exceptions and dedicated test-key restriction; preflight rejects production KMS key names. `S1681_SELLER01_SERIAL_BOOTSTRAP_TOKEN` is transient and removed after activation, whereas `S1681_SELLER01_SERIAL_INSTALL_TOKEN` is the captured long-lived device credential.

The credential responsibilities are deliberately separate:

| Credential | Stored/injected from | Allowed work | Explicitly forbidden |
| --- | --- | --- | --- |
| `CLOUDFLARE_TUNNEL_TOKEN` | `test-env`; `cloudflared` container only | Connect the existing tunnel | Policy reads, route/DNS management, token lifecycle |
| `CLOUDFLARE_S1656_TEARDOWN_API_TOKEN` | `test-env`; host lifecycle only | Read, remove, and prove absence of only the exact S1656 route and DNS record | Management mint, token-record read and revoke (self-verification via `GET /user/tokens/verify` is permitted and recorded as `teardown-token-verify.json`), container injection, unrelated Cloudflare objects |
| `CLOUDFLARE_ADMIN_API_TOKEN` | project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, `prod`; isolated host lifecycle or verify-snapshot subprocess only | Permission-group discovery, teardown-token mint, token re-read, revocation, post-revocation proof; verify-time read-only Cloudflare production snapshot; if the narrow token is already inactive/missing, read-only exact-route and exact-hostname DNS absence proof | Route or DNS mutation, container injection, or any unrelated Cloudflare object |

The teardown token has exactly `Cloudflare Tunnel Write` on account `d5346d3e0f8f344c5f4915aaca689adf` and `DNS Write` on zone `f82ac6762af544d71e8ad5eb3d7fca0c`. Mint requests an expiry 23 hours 59 minutes ahead and rejects any provider result exceeding 24 hours after issue. Its token value exists only in Infisical; the immutable record stores the token ID, canonical returned policies, policy hash, times, and allowed targets without the value.

`./bin/verify --from-clean-seed` also performs read-only production comparison. It reads `DATABASE_PUBLIC_URL` and `CLOUDFLARE_ADMIN_API_TOKEN` from project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment `prod`, and `RAILWAY_API_TOKEN` from project `0943f641-faee-4324-b337-0d50c276e4a9`, environment `prod`. Those credentials are used only for the bounded read-only snapshots; they are not passed into application containers.

### S1681 S3 ownership, activation and spend

Max owns test AWS account `157263244532`; Mars owns fixture cleanup. Operator profile `aimarket-sandbox` resolves to `aim-sandbox-cli`. The seed and broker use separate scoped Infisical credentials, never the operator profile or production credentials. See [AWS test-account entry](aws.md#s1681-test-account-157263244532). Bucket `aimarket-s1681-money-path-test-157263244532` in `eu-north-1` has all Block Public Access settings, BucketOwnerEnforced, SSE-S3, TLS-only policy, seven-day expiry under `s1681/` and one-day incomplete multipart abort; versioning is not enabled. Each run owns one unchanged CSV at `s1681/fixtures/<run-stamp>/synthetic-listing.csv`, journalled in `.state/s1681-seed.json` with length/hash and immutable run key (`environment:seed/s3-fixture.py:171–213`). Never use ETag as SHA-256.

Role `arn:aws:iam::157263244532:role/aimarket-connector-s1681-test` permits ListBucket on prefix `s1681/*` and GetObject/GetObjectVersion on that prefix. Trust is account root AND `aws:PrincipalArn=arn:aws:iam::157263244532:user/svc-s1681-broker` AND per-run `sts:ExternalId`. `svc-s1681-broker` can only assume that role. `svc-s1681-seed` has Put/Get/Delete/GetObjectVersion/DeleteObjectVersion under `s1681/*`, ListBucket/ListBucketVersions with that prefix, plus GetRole/UpdateAssumeRolePolicy on exactly the fixture role. No bucket-wide delete or other IAM authority is implied.

AWS budget `aimarket-monthly-guardrail` is $50/month with 50/80/100% alerts. It is a spend guardrail, not an automatic cutoff: the operator stops new runs at the ceiling and investigates alerts. Keep fixture count/bytes bounded to the committed object and clean after settlement; do not accumulate retries. A2 item 1's dedicated test KMS key names and disclosed shared Vertex credential exception remain in force; this AWS budget does not cap Vertex. A finite Vertex spend ceiling remains an execution prerequisite under S1681 §13.3; none is supplied by this record. Do not invent one or widen the existing exception.

The supported seed flow is serial issuance → device activation → install-token capture → serial-bound registration → G9 trust update → real broker verification:

1. `bin/seed` calls the disposable backend's `POST /api/v1/serials/generate` for seller-01. `SERIAL_TOKEN_SECRET` is distinct from prod. Lost issuance responses stop, without blind reissue (two active serials/email, five/IP/hour; `environment:seed/seed.py:526–531`).
2. Persist `S1681_SELLER01_SERIAL` and transient `S1681_SELLER01_SERIAL_BOOTSTRAP_TOKEN` in `ai-market-backend/test-env`. The existing `VECTORAIZ_SERIAL`/`VECTORAIZ_BOOTSTRAP_TOKEN` aliases activate the clean device through `/api/v1/serials/{serial}/activate`. Refuse another install's volume or production API fallback.
3. Capture the real `vzit_` install token into `S1681_SELLER01_SERIAL_INSTALL_TOKEN`; prove bootstrap consumption and remove the bootstrap vault key. Stop the app while the registration worker persists the serial-bound VZ install, then recreate AIM Data. `/vz/register` carries activated serial plus serial install token alongside the authenticated seller. API-key Trust readiness alone is insufficient (`environment:seed/host-seed.py:150–202`).
4. Create/read the single product S3 connection, obtain its derived ExternalId, and update only the fixture role's ExternalId condition while preserving its principal/action/other trust fields. Read back exact equality, configure the role and call the real broker verification, then scan/register exactly the uploaded object (`environment:seed/host-seed.py:245–314`; `environment:seed/s3-fixture.py:109–142`). A failed update or verification stops before publish. `S1681_S3_EXTERNAL_ID` is a per-run product output, not a static input; the journal holds only its hash. Reset does not restore trust: the next serial requires a new G9 update.
5. Require exactly one active seller-01 device, its linked active Trust session and the current container's fulfilment startup log within 60 seconds (`environment:tests/device-contract.py:27–67`). Missing API key returns exit 2 and aborts verify (`environment:bin/verify:431–436`). Never fabricate serials, copy production activation, overwrite a foreign install, patch SQL or weaken a guard.

## E. Boot and lifecycle

Honest host prerequisites are Docker with Docker Compose, AWS CLI v2 (`environment:bin/preflight:39–48` refuses v1 because uploads are conditional) and AWS S3 / IAM / STS endpoint reachability from Titan-1 for fixture validation, upload, G9 trust update, broker verification and cleanup, `git`, `curl`, `python3`, `dig`, the Infisical CLI, the Docker buildx CLI plugin (`bin/preflight` uses `docker buildx imagetools`), network access to GitHub, GHCR, Docker Hub (`docker.io`), `mcr.microsoft.com`, `registry.npmjs.org` (frontend and runner `npm ci`), the PyPI and Debian package repositories (pinned backend image build), Stripe, Infisical, Cloudflare, Railway's GraphQL endpoint and the public `ai.market` endpoints (verify-time production no-effect reads), and the authoritative DNS servers `dig` queries, an authorized Infisical machine identity at `~/.config/infisical/sysadmin-token`, an authorized GitHub SSH credential for the three private `git@github.com:aidotmarket/{ai-market-backend,ai-market-frontend,aim-data}.git` remotes cloned by `./bin/up`, and GHCR pull authorization when the pinned private image requires it. Node, Playwright, and Chromium are supplied by the pinned runner container and must not be taken from the host. Spec AC1's "only Docker and Infisical" wording is narrower than these real command and credential prerequisites and is to be reconciled by specification amendment A2 (S1656).

Before `./bin/down`, the teardown evidence root must exist, be owned by the operator, be outside the checkout, and have mode `0700`:

```sh
mkdir -p /Users/max/koskadeux-state/s1656/teardown-evidence
chmod 0700 /Users/max/koskadeux-state/s1656/teardown-evidence
```

After both reviewed merge-commit pins are locally available and exported, mint the teardown token immediately before boot:

```sh
rtk proxy ./bin/mint-teardown-token
rtk proxy ./bin/up
rtk proxy ./bin/verify --from-clean-seed
```

The final command starts or resumes Option A and normally returns 2 while settlement is pending. Follow §G's daily settlement/resume procedure. Only after both phases settle and evidence/cleanup complete, use `rtk proxy ./bin/down`; use `--terminal` only when the disposable Infisical `test-env` must also be destroyed. Renew the 24-hour teardown token as needed during the multi-day run and finish teardown within the current token's validity. `reset` is a guarded recovery operation, not an unconditional next step after purchase.

`./bin/up` performs pure safety assertions, prepares exact detached source clones, verifies the AIM Data tag/digest and Stripe platform Account, builds backend/frontend, records image identities, starts the stack with `--wait`, verifies the pinned runner and all three localhost origins, and then invokes `./bin/seed`. Success is exactly:

```text
up: ai-market-money-path-s1656 is healthy and the three-fixture seed is ready
```

The first clean acceptance phase calls guarded `reset`, which calls `up` and reseeds. Later invocations resume the durable active run. Original AC1–AC12 status text is only the verification half; require both settled delivery phases and the final summary described in §H.

## F. Seed contract

`./bin/seed` accepts no arguments, requires a healthy backend, executes the read-only mounted `/s1656/seed.py` in that container, and refuses a database host other than Compose service `postgres`. It consumes only the exact committed manifest-backed secret names and creates or restores exactly these fixtures:

| Fixture | Required initial truth |
| --- | --- |
| `seller-01` | Active, verified, synthetic seller with profile/company, TOTP enabled, one active `auth_user` PartyIdentity, one Stripe test Connect Custom account, Stripe-retrieved `payouts_enabled=true`, and effective seller capability `active` with no missing steps |
| `buyer-01` | Active, verified, synthetic buyer with no seller, Connect, listing, ordinary payment-method, setup-attempt, or verification state |
| `seller-02` | Active, verified, synthetic seller with profile/company, TOTP disabled, one active `auth_user` PartyIdentity, and no Connect, payout, listing, ordinary payment-method, setup-attempt, or verification state |

The Connect Custom idempotency key is fixed for seller-01. The ordinary pay-in platform Account and seller Connect Account must be separate test-mode objects. The seeder does not set the payout projection until Stripe retrieval reports Custom, the S1656 marker, active transfers, and `payouts_enabled=true`; it never creates Connect state for buyer-01 or seller-02. Success is `seed: three-fixture contract passed`.

`reset` removes only exact-label S1656 local targets and volumes, retains `test-env`, calls `up`, reruns migrations, and recreates this exact seed. Never mutate a fixture into another role, patch readiness with SQL, or add an unlisted fixture.

## G. Operate the acceptance journey

`./bin/verify --from-clean-seed` executes one serial flow:

1. Capture a normalized, read-only production snapshot: backend deployment SHA/status and flags, production counts for the synthetic domain, public listing search, public health, Cloudflare tunnel configurations, and the complete paginated DNS record set.
2. Guard-reset, rebuild/start, health-check, and seed the environment.
3. Prove signed-out auth refresh and readiness return 401 and route to login.
4. Prove buyer-01 is redirected to inquiries and receives hidden/404 readiness.
5. Prove seller-02 sees no payment control and receives the indistinguishable 404 readiness.
6. Sign into AIM Data as seller-01, use the seeded, scanned single-object S3 dataset from the unchanged committed CSV, register/publish exactly one listing, record but never visit the returned production `marketplace_url`, and render `http://localhost:13000/listings/<listing_id>` against the local API.
7. Prove no card control before the quote, both acknowledgements, and explicit paid-start action. Only a `setup_required` result exposes `http://localhost:13000/dashboard/data-verification/payment-method`.
8. Sign into the local frontend as seller-01, reauthenticate, and complete the Stripe-hosted `mode=setup` page with Stripe test data entered only on Stripe's page.
9. Prove Stripe test endpoint `we_1UBctVRx8FzPjYyVDIFWEFMT` is enabled for the exact S1656 URL and `checkout.session.completed`, provider delivery succeeds with `livemode=false`, and the backend persists one completed event row.
10. Ask Stripe to redeliver that same event. Prove one event row remains, the duplicate log increments, and neither the ordinary identity nor finalization audit changes.
11. Prove webhook-first and a separate freshly reauthenticated return-first setup converge on the same ordinary customer identity, readiness is `ready`, and the seller Connect identity is unchanged.
12. Return to AIM Data, start paid verification, wait for the signed scan/report lifecycle and manual-capture epoch, prove the final PaymentIntent and charge are test-mode and captured, and publish the findings.
13. Capture the same normalized production snapshot again and require structural equality after volatile fields are removed.

At `e2028111:browser/s1590-money-path.spec.ts:220-241`, the runner observes every request, classifies any `localhost` or `127.0.0.1` hostname as local, and classifies the roots and subdomains of `stripe.com`, `stripe.network`, `stripecdn.com`, `hcaptcha.com`, `apple.com` and `cdn-apple.com` as the Stripe-hosted surface. It records the method and origin as forbidden for `host.docker.internal`, explicitly for `ai.market` and all its subdomains, and for every other non-local/non-Stripe-hosted request; it also records every navigation origin. This is observation followed by refusal through the final assertion that the forbidden-request list is empty, not request interception; local traffic is not restricted to the three configured origins or ports. A passing journey's `browser-evidence.json` proves no production navigation through its complete recorded `navigation_origins`, which must contain no production origin; that list must also exclude the returned `marketplace_url` origin and `production_marketplace_url_never_navigated` must be `true`.

### S1681 purchase, delivery, replay and Option A settlement

Paid verification is seller-01 buying the report: preserve the seventeen original checks, published epoch, 2500-cent authorization and 100-cent capture. Buyer-01 separately purchases the listing for 2500 USD cents through real Stripe-hosted `mode=payment` Checkout. Its linked Order/Transaction and retrieved test PaymentIntent must match buyer, seller, listing/version, amount, currency and `livemode=false`. A setup Session or verification PaymentIntent cannot prove purchase (`environment:browser/s1681-delivery-leg.ts:74–141`).

Run `rtk proxy ./bin/verify --from-clean-seed` with both locally available merge-commit pins exported. It owns these phases:

1. **Online:** publish the single verified S3 object, buy as buyer-01, observe both signed provider event types and their actual first-arrival order, then provider redelivery without a second charge. Require real `vai.fulfillment.deliver`/response/ack, completed pending work and both Order/Transaction delivered within 120 seconds of accepted payment. Require zero raw chunks (`environment:browser/s1681-delivery-leg.ts:104–167`).
2. **Bytes and authorization:** use the authenticated order download endpoint to issue a no-store token, redeem it, and GET the returned URL directly from the allowed S3 host within its lifetime. Require 200, full byte equality, equal lengths and SHA-256 against `fixtures/synthetic-listing.csv`, and one download-counter consumption. Signed token expiry cannot exceed stored presign expiry or access deadline. Exercise nonbuyer, wrong order, tampered/expired token, revoked/pre-delivery order, expired presign, access deadline, exhausted downloads, last reservation, wrong version/generation and correlated refresh/replay. Never log tokens/URLs or accept scoped credentials for this single-object path. Only the authenticated correlated refresh may replace expired credentials; replay must not consume another counter or advance another business event.
3. **Confirmation and replay:** buyer confirmation makes Order completed and canonical Transaction confirmed, with exactly one canonical confirmed event. Redeliver provider events through Stripe and business responses through the real device handler in a fresh encrypted envelope; record driver use. Ordinary replay must preserve timestamps, credential hash, delivery/event/charge/transfer counts and terminal states. Old ciphertext or a direct backend response-service call is not replay proof.
4. **Hold:** Option A preserves the purchase-confirmation receipt and returns **2** while the genuine 48-hour hold runs. Keep services, database, device volume, fixture and active checkpoint intact. `rtk proxy ./bin/check-settlement` checks the same order; before the deadline it returns 2 (`pending-hold`). After the hold it invokes the existing test settlement scheduler, retrieves a real Stripe test Transfer and repeats the cycle to prove idempotency. Require exactly one unreversed transfer of 2375 USD cents (125-cent platform fee), matching destination/group/metadata, local transfer completed and Transaction settled. Missing/failed/divergent transfer is failure; time passing alone is not proof (`environment:bin/check-settlement:194–214, 830–945`).
5. **Offline:** after online settlement passes, rerun `rtk proxy ./bin/verify --from-clean-seed`. Resume cleans the settled online fixture and starts the distinct clean offline phase. The harness stops only its labelled AIM Data container before purchase, proves session inactivity and 30 seconds of one queued request with no delivery/token, then restarts the same install/volumes. Require a new session, real outbound-queue drain, delivery and matching bytes within 180 seconds without repurchase, reseed or manual fulfilment. The driver restores the device in its finally path. Both initial payment-event orders are covered across the two phases (`environment:browser/s1681-delivery-leg.ts:69–73, 117–167`).
6. **Conclude:** wait the offline phase's own 48-hour hold and run the settlement check again. Then rerun `verify --from-clean-seed` to join both settled phases, clean the fixture, compare production, recheck pins and write the sole full summary. A pending return, settled online half or manually completed summary is not scheduled release proof (`environment:bin/check-settlement:667–807`).

`bin/verify --settlement-snapshot` records the admitted active phase's production comparison; `--settlement-cleanup` adds scoped fixture cleanup. These are helper-owned settlement operations, not alternatives to purchase/settlement proof or ways around pending guards (`environment:bin/verify:117–130, 415–420`).

### Nighttime ownership and admission

Max is the invoking Titan-1 operator; Mars owns the runbook, evidence review, credential renewal and safe teardown coordination. Before activation, verify the permanent checkout is clean at the final head, the host timezone is Europe/Madrid, both spec merge commits exist locally, the evidence root is operator-owned mode 0700, and the next operator can renew the 24-hour teardown token during the multi-day hold. Mint/renew without resetting pending state; teardown waits for settlement.

Store literal `KEY=VALUE` lines in `/Users/max/koskadeux-state/s1656/nightly-pins.env`, an operator-owned regular non-symlink file, mode 0600 (stricter is accepted). Required keys: `S1656_SPEC_A2_SHA` and `S1681_SPEC_SHA`, each the full lowercase 40-hex merge commit of this PR. Optional `S1656_RUNBOOKS_REPO` must be an existing absolute directory. No quotes, shell syntax, blank lines, duplicates or extra keys. `S1681_NIGHTLY_PINS_FILE` may select another absolute path outside the environment repository. Conflicting inherited SHA pins refuse before writes (`environment:bin/nightly:21–50, 110–124`). Do not use the authoring base as an acceptance pin.

`rtk proxy ./bin/check-settlement --pins` is the read-only pin check after the manual operator exports the same two values. `--lock` is the shared lifecycle wrapper; `--guard` checks inherited ownership and pending state, not a bypass. `bin/up`, `seed`, `reset`, `down`, `preflight`, manual verify and both nightly invocations share `/Users/max/koskadeux-state/s1656/environment.lock`, held with nonblocking exclusive flock and verified ancestor ownership. A collision fails; never unlink the lock, kill another owner or reset beneath a run. Each invocation has a 30-minute deadline and propagates nonzero failure; there is no 48-hour sleeping process (`environment:bin/check-settlement:101–184`).

The committed `config/com.aimarket.s1681-settlement.plist` calls `bin/nightly --settlement-check` daily at **01:30**; `config/com.aimarket.s1681-money-path.plist` calls `bin/nightly` at **02:00**, both Europe/Madrid host time. `TZ` alone does not change launchd calendar time. **Do not install or activate either plist until DL1–DL11 are proven.** No installation is performed by Chunk D. Later activation must pre-create both plists' stdout/stderr paths under the evidence root with mode 0600. Wrapper logs are unique mode-0600 fixed-status logs. The wrapper runs its local contract before the real command and writes separate scheduled receipts hashing existing phase/summary evidence; exit-2 receipts remain pending. DL12 release requires a genuinely scheduled run joining purchase/resume and settlement receipts, not a manual invocation of `nightly` (`environment:README.md:288–314`; `environment:bin/nightly:59–107`; both plists:7–35).

## H. Evidence and redaction

Evidence is independent only when the referenced files exist and can be read without trusting command success text.

| Evidence | Exact location | Required contents |
| --- | --- | --- |
| Mint policy | `/Users/max/koskadeux-state/s1656/mint-policy/<token-id>.json` | Mode `0444`; token ID, issue/expiry, complete API-returned policies, SHA-256, exact allowed targets; no token value |
| Acceptance | `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/` | Mode `0700` run root with `online/` and `offline/` phase directories, immutable phase receipts and final `summary.json` (mode `0400`); pending phases have no full summary |
| Teardown | `/Users/max/koskadeux-state/s1656/teardown-evidence/<UTC-run-stamp>/` | Mode `0700` directory containing the applicable active-token or already-revoked evidence variant below, `authoritative-dns-absence.txt`, and `summary.json`; terminal runs also contain Infisical delete/absence proof |
| Runtime identity | `.runtime/aim-data-image-digest.json`, `.runtime/image-digests.json` | Exact source SHA and image-digest bindings; supporting identity only |

On the active-token path, teardown evidence contains the token read and verification, route/DNS before state and removal or already-absent responses, control-plane and authoritative absence proofs, token revocation response, and post-revocation inactive/not-found proof. On the already-revoked path, it instead contains `token-already-revoked.*`, `tunnel-route-admin-absence.*`, and `dns-admin-absence.*` plus authoritative DNS absence; the admin credential performs only those absence reads and no route/DNS mutation.

D5 requires schema version, environment and both spec SHAs, original paid-verification/epoch fields, image digests, fixture expected hash/length and distinct clean-seed identities. Each `delivery_cases.online`/`offline` records local listing/order/transaction/device/session IDs; hashed provider/request correlations; checkout mode/amount/currency/livemode; event ordering/dedupe; queue/send/response/delivery times; S3 source kind; token issue/redemption and expiry; HTTP status, observed length/hash and byte equality; confirmation time/event count; duplicate before/after counts and credential hashes; settlement option/state/deadline; purchase and settlement receipt hashes, both invocation/source identities and observation times; transfer hash/amount/currency/livemode/destination match and local/Transaction status. Require all `per_delivery_criterion` DL1–DL12, cleanup/production results and invocation/start/end/exit identity. Never default a missing field to true (`environment:bin/check-settlement:728–807`).

`active-run.json` (mode 0600) points to immutable `online/` or `offline/` `purchase-confirmation.json` and `settlement-check.json`; `cleanup.json`, `production-settlement.json` and original `original-s1656.json` support the join. The final summary is atomic mode 0400. `scheduled-*.json` or `scheduled-pending-*.json` separately hashes the command evidence and reports the wrapper invocation/exit. Preserve these together. The implemented summary's `baseline_environment_sha` is B1 `e94aad9ab777c0dd220574693e4a00c0dff7a7e2` (`environment:bin/check-settlement:798–807`); the release records separately preserve the original pre-S1681 baseline `24d884f1a48b73d1f65da07f09cce59bef587d65`.

The acceptance summary must say `acceptance: passed`, `from_clean_seed: true`, and carry the three exact source SHAs. The teardown summary must say route, DNS, authoritative DNS, and token revocation are true and must distinguish `teardown_token_already_revoked`; `infisical_test_env_absent` is true only for `down --terminal`.

Never store token or key values, raw emails, passwords, TOTP seeds or codes, raw `acct_` identifiers, card data, Checkout URLs, Stripe object IDs, webhook bodies or signatures, billing data, raw customer/source rows, or provider responses containing a token. The browser runner hashes provider identifiers into opaque evidence references. Local UUIDs, run IDs, timestamps, HTTP statuses, booleans, exact source/image SHAs, and redacted screenshots are allowed.

## When it breaks

§I is a symptom-first table. Run the listed read or lifecycle command from the environment repository; do not weaken a guard to clear an error.

| Symptom | Cause | Fix | Exact command or evidence path |
| --- | --- | --- | --- |
| `live Stripe secret-key prefix refused before network access` or publishable-key equivalent | A live prefix was placed in a test-only name | Remove the live value from `test-env`, restore a real Stripe test key, and rerun; never copy from `prod` | `./bin/up`; mint/acceptance evidence remains outside Git under `/Users/max/koskadeux-state/s1656/` |
| `Stripe test key does not belong to the pinned platform Account` | `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID` and the Account retrieved by `STRIPE_TEST_SECRET_KEY` differ | Correct the two `test-env` entries as one test-platform pair, then rerun preflight through `up` | `./bin/up`; no `acct_` value may enter evidence |
| `FRONTEND_URL must equal http://localhost:13000` or CORS refusal | An injected origin drifted from the only allowed S1656 origin | Restore both exact localhost values; do not allow another HTTP origin | `./bin/up`; `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml config` |
| A source is dirty, on a branch, has the wrong remote, or differs from the recorded SHA | A managed clone was edited or a pin/remote changed | Inspect the named `.state/sources/<product>` checkout, preserve any unexpected work, restore the exact clean detached pin, and rerun; amend/review rather than choosing another SHA | `git -C .state/sources/<product> status --short`; `git -C .state/sources/<product> rev-parse HEAD`; `.runtime/image-digests.json` |
| Docker reports an occupied port for 13000, 18000, 18081, 18002, 15432, or 16379 | Another local process owns a fixed loopback binding | Identify the listener, stop it only after confirming ownership, then rerun; do not change S1656 ports | `lsof -nP -iTCP:<port> -sTCP:LISTEN`; `./bin/up` |
| Backend or AIM Data migration fails and `up` never reaches healthy | Product migration or disposable database startup failed | Read service logs. If the failure is confined to S1656 disposable state, run guarded reset; otherwise stop and return the exact log with the pinned SHA | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs backend aim-data aim-data-postgres postgres`; `./bin/reset` |
| Redis is unavailable or backend health waits indefinitely | The pinned Redis container is unhealthy or its S1656 volume is unusable | Inspect only the S1656 Redis service; use guarded reset for disposable-state recovery | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml ps redis`; `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs redis`; `./bin/reset` |
| `seller-01 effective seller capability is not active` with seller status not `active` or a non-empty `missing_steps` list (seed/seed.py:313 prints only the generic signature, not the list) | Seeded TOTP/profile/party/Connect payout truth is incomplete | Do not patch the database or payout projection. Rerun the guarded clean seed; if it repeats, preserve the resolver output and Stripe test evidence for the backend owner | `./bin/verify --from-clean-seed`; `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/browser-evidence.json` |
| AIM Data VZ register/publish returns a signature or replay failure | AIM Data signing secrets disagree, a nonce was replayed, or backend/AIM Data clocks or pinned code disagree | Inspect both services, retain the exact HTTP status, and rerun only from a clean seed after correcting the secret pair or code pin | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs aim-data backend`; `./bin/verify --from-clean-seed` |
| AIM Data calls `api.ai.market` or another production API | API target aliases were not the committed `http://host.docker.internal:18000` server-side value or a request escaped the guard | Stop immediately. Restore the committed override; do not add a hosts bypass or navigate to production | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml config`; `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/browser-evidence.json` |
| Payment setup handoff points to production | `AIM_DATA_PAYMENT_SETUP_URL` or `VECTORAIZ_PAYMENT_SETUP_URL` drifted | Restore both to the exact localhost payment-method route and rerun from clean seed | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml config`; `./bin/verify --from-clean-seed` |
| Tunnel is down or Stripe cannot reach the endpoint | `cloudflared` is unhealthy, connector token/route is wrong, or proxy is unavailable | Check local proxy restriction first, then connector logs and exact route. Never replace the tunnel with Stripe CLI | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml ps webhook-proxy cloudflared`; `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs webhook-proxy cloudflared` |
| Webhook returns an invalid-signature failure | `STRIPE_TEST_WEBHOOK_SECRET` does not match test endpoint `we_1UBctVRx8FzPjYyVDIFWEFMT`, or proxy/body/header preservation drifted | Restore the endpoint's test signing secret and committed proxy config; never disable verification | `./bin/verify --from-clean-seed`; `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs webhook-proxy backend` |
| A real test `checkout.session.completed` event is synthetically suppressed | The user/attempt/platform/livemode/event predicates do not all match the S1656 exception | Inspect the exact backend decision and fixture truth; correct the test object/binding rather than broadening synthetic-event routing | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs backend`; `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/browser-evidence.json` |
| `Stripe redelivery must record duplicate without another finalization` or `backend did not record Stripe provider redelivery as duplicate` | Dedupe row/log or identity/audit idempotency regressed | Preserve the provider redelivery and completed-row evidence, stop acceptance, and return it to the backend owner; do not replay by posting a captured payload | `./bin/verify --from-clean-seed`; `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/browser-evidence.json` |
| Readiness stays `pending` instead of `ready` | Webhook or fresh return did not reconcile a valid off-session SetupIntent/customer/payment method, or platform/livemode binding differs | Inspect backend logs and the browser evidence for both setup generations, then rerun from clean seed after repairing the binding | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs backend`; `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/browser-evidence.json` |
| Manual authorization never reaches `requires_capture` before capture | Ordinary payment identity is not ready, provider authorization failed, or the signed verification epoch is invalid | Stop the paid flow. Inspect the backend epoch/Stripe status in redacted logs and rerun only after the root cause is fixed; do not change capture mode or write epoch state | `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs backend aim-data`; `./bin/verify --from-clean-seed` |
| Capture fails or the final charge is not captured | PaymentIntent/charge/provider state or report-finalization binding failed | Preserve the failure, verify no production marker, and return it to the payments owner. Do not create a manual replacement payment outside the journey | `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/browser-evidence.json`; `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml logs backend aim-data` |
| Reset says a container, network, or volume `lacks the exact S1656 ownership label` | A candidate target is foreign or its ownership label drifted | Stop. Inspect all Compose project targets; never force-remove or relabel an ambiguous object | `docker ps -a --filter label=com.docker.compose.project=ai-market-money-path-s1656`; `docker network ls --filter label=com.docker.compose.project=ai-market-money-path-s1656`; `docker volume ls --filter label=com.docker.compose.project=ai-market-money-path-s1656` |
| `deployment marker observed; seed refused`, public search finds the fixture, production counts change, or normalized snapshots differ | Test data escaped, a production marker was injected, or production changed during the run | Stop, preserve both snapshots, perform safe terminal teardown, and escalate. Do not change production or normalize away the difference | `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/production-before.json`; `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/production-after.json`; `./bin/down --terminal` |
| `immutable mint-policy validation failed`, token expired, or policy hash/resources changed | The record is missing/stale, the 24-hour window closed, or Cloudflare/Infisical state drifted | Mint a new bounded token. Use replacement only when an existing unexpired record must be revoked first; never hand-edit the mode-0444 record | `./bin/mint-teardown-token`; if required, `./bin/mint-teardown-token --replace`; `/Users/max/koskadeux-state/s1656/mint-policy/` |
| Narrow teardown token is already inactive/missing and Cloudflare targets remain or absence is unproved | The revoked-token recovery path cannot mutate route/DNS and admin read-only proof found residual state | Stop local/terminal continuation, mint a fresh narrow token, then rerun teardown. The admin token must remain read-only for targets | `./bin/mint-teardown-token`; `./bin/down`; `/Users/max/koskadeux-state/s1656/teardown-evidence/<UTC-run-stamp>/` |
| Browser-runner image, packages, revision, mounts, topology, or localhost reachability differs | Pinned image/lock/config drifted, a mount became writable, or a service is unhealthy | Restore the committed runner manifests/topology and rerun `up`; do not use host Node or another browser | `./bin/preflight --check-browser-runner`; `docker compose --env-file versions.env -f compose.yaml -f compose.aim-data.override.yaml ps` |
| Evidence directory is missing, not operator-owned, inside Git, or not mode `0700` | Restricted evidence storage was not prepared safely | Create/fix only the exact external directory, verify ownership/mode, and rerun; never redirect evidence into the checkout | `ls -ld /Users/max/koskadeux-state/s1656/{acceptance-evidence,teardown-evidence,mint-policy}` |
| Missing serial/install token | Issuance, activation or vault handoff incomplete | Inspect hashed serial state and supported seed handoff; retain bootstrap only until activation succeeds. Do not reissue on a lost response or substitute the Trust API key. | environment:seed/seed.py:526–552; environment:seed/host-seed.py:150–202 |
| Wrong API base | AIM Data aliases disagree or use production fallback | Stop; restore both server-side API bases to http://host.docker.internal:18000 and keep browser API at localhost:18000. Recreate only the owned service through the lifecycle. | environment:seed/host-seed.py:193 |
| STS/ExternalId refusal, including after reset | New serial derived a different ExternalId or fixture trust/identity drifted; or (`assume_role:AccessDenied` within seconds of the G9 trust write, trust and ExternalId matching) IAM propagation delay, which the seed tolerates for 120 s since PR #14 | Compare the product-derived value and role trust privately; if they match and the refusal clears on a later assume-role, it was propagation — rerun from clean seed at a head that includes PR #14. Rerun the supported G9 seed step only when pending guards admit it; preserve broker principal and exact role scope. No static ExternalId fallback. | environment:seed/s3-fixture.py:109–142; environment:seed/host-seed.py:276–282; .state/s1681-seed.json |
| Non-S3 source | Wrong imported artifact or connection not verified | Stop before purchase; use the single seeded S3 scan/register path after broker verification. Never switch to local-file streaming. | environment:seed/host-seed.py:245–314 |
| Absent device or active session | Missing API key, registration failure or wrong container | Require one seller-01 device/session and current startup log; missing-key exit 2 is failure, not a skip. Preserve pending state while repairing the owned install. | environment:tests/device-contract.py:27–67; environment:bin/verify:431–436 |
| Queue not draining | Same install did not reconnect or outbound drain failed | Inspect active session and order-correlated queued/sent/acked evidence; restore the same labelled device. Do not repurchase, reseed or call fulfilment manually. | online/ or offline/browser-evidence.json; environment:browser/s1681-delivery-leg.ts:142–167 |
| Response authorization mismatch | Seller, listing, device or request correlation differs | Stop and retain redacted correlation evidence for the backend/device owner; no identity substitution or direct response-service call. | environment:bin/check-settlement:218–285 |
| Order/Transaction divergence | Delivery/confirmation transition or canonical trigger failed | Preserve both read-only states and event counts; return the defect to the backend owner. Do not patch SQL or add a duplicate event. | environment:browser/s1681-delivery-leg.ts:154–167; phase purchase-confirmation.json |
| Missing delivery path | Authenticated S3 response did not persist object/version/presign binding | Stop token issuance and inspect the exact response and order binding privately; return a product defect if absent. Do not insert a URL or accept delivered alone. | environment:bin/check-settlement:218–285; phase browser-evidence.json |
| Token/presign expiry | Signed token, presign or access window expired | Use only the supported authenticated correlated refresh where permitted, then issue/redeem a new token; retain negative-probe evidence. Never extend timestamps or log URLs. | phase browser-evidence.json; S1681 spec §4 D3 |
| Byte mismatch | Wrong object/version, truncated GET or fixture drift | Stop acceptance, preserve expected/observed hashes and lengths, and inspect the immutable run journal. Do not alter the fixture or accept ETag as SHA-256. | .state/s1681-seed.json; phase browser-evidence.json |
| Transfer absent, hold pending or failed | 48-hour hold has not elapsed, scheduler failed, or provider/local binding differs | Pending is exit 2: preserve state and run the daily settlement check. After the deadline, absence/failure/divergence fails; inspect redacted transfer proof with the owner, without fake transfer or manual success. | rtk proxy ./bin/check-settlement; phase settlement-check.json |
| spec final head differs / spec product identity differs | One mutual pin names an old environment or product image | Make the reviewed merge commit locally available and export both exact pins; require the clean current final head (`6a1cfcfa` since the S1710 folds) and matching versions.env. Never fetch during verify or weaken pin checks. | rtk proxy ./bin/check-settlement --pins; environment:bin/check-settlement:34–58 |
| Overlapping nightly invocation / lock collision | Manual run or another scheduled owner holds environment.lock | Preserve the owner; inspect its status and retry after it exits. Never unlink the lock or kill the peer. Timeout/failure remains nonzero. | environment:bin/check-settlement:101–184; nightly-*.log |
| Cloudflare WAF 403 on vault writes | Vault request User-Agent is missing or rejected | Use the committed host-seed writer with its s1656-seed/1.0 User-Agent; inspect status without logging bodies or secrets. If it still fails, stop for vault owner investigation; do not disable WAF. | environment:seed/host-seed.py:205–227 |
| AWS CLI v2 is required for conditional S3 uploads | PATH selects AWS CLI v1 | Install/select AWS CLI v2 through the normal host setup, verify aws --version, then rerun preflight when the lock/settlement guard permits. | rtk proxy aws --version; environment:bin/preflight:39–48 |
| Missing/invalid nightly pins file | File absent, symlink, foreign owner, permissive mode, malformed keys or conflicting inherited SHA | Restore the operator-owned mode-0600 regular file with literal keys from the reviewed merge commit; no blank lines or shell syntax. Optional repo comes from file/default. | /Users/max/koskadeux-state/s1656/nightly-pins.env; environment:bin/nightly:21–50 |
| `seed: host handoff failed (details suppressed)` right after the container seed printed `status: seeded`, with `.state/s1681-seed.json` showing `serial_state: active`, `upload_state: uploaded`, a `connection_id` and no `external_id_sha256` | The G9 IAM step (`seed/s3-fixture.py` `iam()`) failed before the trust update. Below environment PR #13 (final head `f3ffcd48`) it passed the request as `--cli-input-json file:///dev/stdin`; aws-cli 2.34.x (Homebrew, Python 3.14) rejects piped stdin with `ParamValidation: Invalid JSON received` although the JSON is valid | Confirm `aws --version`; reproduce read-only with the seed identity (`iam("get-role", S1681_S3_ROLE_ARN)` through `seed_aws_env()`); run only at an environment head that includes PR #13 (private 0600 file transport). Do not pass the policy on argv and do not reissue the serial | `rtk proxy aws --version`; environment:seed/s3-fixture.py `iam()`; `.state/s1681-seed.json` |
| offline retry refused | Failed offline evidence already exists | Inspect and manually quarantine only the eligible failed offline directory under the shared lock as §J directs. Never automatically rename or discard pending money evidence. | environment:bin/verify:128–130; §J Interrupted offline retry |

## J. Reset and teardown

All mutation commands first acquire the shared lock and refuse **exit 2** while the checkpoint is `purchasing` or `pending_settlement`. This includes `up`, `seed`, `reset`, `down` and `preflight`; terminal teardown is not an exception (`environment:bin/check-settlement:130–162`). Preserve the environment and resume settlement; a production-comparison failure does not authorize bypassing this refusal.

`./bin/reset` cleans the exact journalled S3 run prefix using the injected seed identity before removing local state (`environment:bin/reset:38–56`). Cleanup lists object versions/delete markers, deletes only the recorded object and verifies absence; unexpected keys refuse. Bucket versioning is off, but the version-aware cleanup permissions remain required (`environment:seed/s3-fixture.py:215–247`). It never deletes the bucket, role, users or budget, and it never restores old ExternalId trust. Reset also checks the Compose project name and every matching container/network/volume ownership label, removes those local targets with volumes, retains Infisical `test-env`, and executes `./bin/up`; `up` migrates and seeds the exact three fixtures. Reset makes no Cloudflare call and never destroys the stable test-env-only application secrets.

`./bin/down` validates the exact project and Cloudflare identifiers, mode-0444 mint record, token identity, expiry, complete policy document, policy hash, permissions/resources, tunnel configuration, route, and DNS record before mutation. With an active narrow token it removes only the S1656 route and DNS record, proves both absent through Cloudflare control-plane reads and authoritative A/AAAA/CNAME queries, revokes the narrow token through the admin lifecycle authority, and proves inactive/not-found state. It then writes a new immutable evidence run.

If the narrow token is already inactive or missing, the admin authority may only read the exact tunnel configuration and hostname query to prove both targets already absent. It cannot repair them. If either remains or absence is ambiguous, `down` refuses and directs the operator to mint a fresh narrow token; only that token may mutate the route or record.

Plain `./bin/down` retains `test-env`. `./bin/down --terminal` additionally looks up the single exact Infisical environment, deletes it, rereads the workspace, and proves the slug absent. Stripe may retain test-mode objects; retained objects remain test-only and S1656-tagged and must never be described as deleted. A local teardown, token revocation, or `test-env` deletion does not imply provider-object deletion.

If the 24-hour window expires before teardown, run `./bin/mint-teardown-token`. Use `--replace` only for an existing unexpired current record; it admin-revokes and proves the old token before archiving its record. Never delete an ambiguous Docker object, manually edit policy evidence, reuse the connector token for management, or use the admin token for route/DNS mutation.

### Interrupted offline retry

`environment:bin/verify:128–130` refuses an existing offline directory; there is no automatic rename. First inspect `active-run.json`, both phase receipt hashes, test Order/Transaction/Transfer state and device ownership. If any purchase or settlement is pending or uncertain, preserve everything and resolve it through the existing settlement path; do not move the checkpoint or clear its state.

For a failed offline attempt proven to have no pending money and whose online checkpoint remains settled, use the recipe below on Titan-1. It takes the environment's same non-blocking exclusive lock (`e2028111:bin/check-settlement:16-18,101-184`), respecting `S1656_ACCEPTANCE_EVIDENCE_DIR` if set; the default lock is `/Users/max/koskadeux-state/s1656/environment.lock`. Lock denial means another owner is active: do not retry until it exits, unlink the lock or kill the owner. `check-settlement --lock` accepts only commands under `bin/`, so this uses Python's identical `fcntl.flock` semantics directly.

While the command holds the lock and waits at its prompt, repeat the inspection above: verify both phase receipt hashes, test Order/Transaction/Transfer state and device ownership, confirm the failed directory belongs to the active run and contains no purchase checkpoint, and establish no pending or uncertain money. Enter a redacted reason only when all checks pass; otherwise interrupt the command and stop for owner recovery. The recipe checks the settled online checkpoint and directory ownership/mode, refuses symlinks and any offline purchase/settlement receipt, renames only to `offline.failed-<UTC stamp>` without overwriting a quarantine, preserves the directory tree's ownership/modes/contents/hashes by same-parent rename, and appends the reason and paths to the run's restricted `operator.log`.

```sh
rtk proxy python3 - <<'QUARANTINE'
import datetime as dt, fcntl, json, os, re, stat
from pathlib import Path
os.umask(0o077)
root = Path(os.environ.get("S1656_ACCEPTANCE_EVIDENCE_DIR", "/Users/max/koskadeux-state/s1656/acceptance-evidence"))
fd = os.open(root.parent / "environment.lock", os.O_RDWR | os.O_NOFOLLOW)
try:
    if os.fstat(fd).st_uid != os.getuid():
        raise SystemExit("lock owner differs; stop")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another owner active; do not retry until it exits")
    def owned(path):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
            raise SystemExit("symlink or foreign owner; stop")
        return info
    owned(root); owned(root / "active-run.json")
    checkpoint = json.loads((root / "active-run.json").read_text())
    if (checkpoint.get("schema") != "ai.market/s1681-run/v1"
            or checkpoint.get("phase") != "online" or checkpoint.get("state") != "settled"
            or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", checkpoint.get("run", ""))):
        raise SystemExit("safe online checkpoint absent; stop")
    run = root / checkpoint["run"]
    owned(run)
    source = run / "offline"
    before = owned(source)
    if not stat.S_ISDIR(before.st_mode) or stat.S_IMODE(before.st_mode) != 0o700:
        raise SystemExit("offline directory/mode differs; stop")
    for entry in source.rglob("*"):
        owned(entry)
        if entry.name in {"active-run.json", "purchase-confirmation.json", "settlement-check.json"}:
            raise SystemExit("offline purchase/settlement checkpoint present; stop")
    with open("/dev/tty", "r") as tty:
        print("Complete all inspection checks under this lock; enter redacted quarantine reason (blank refuses): ", end="", flush=True)
        reason = tty.readline().strip()
    if not reason:
        raise SystemExit("inspection not confirmed; stop")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = run / ("offline.failed-" + stamp)
    if os.path.lexists(target):
        raise SystemExit("quarantine already exists; stop")
    logfd = os.open(run / "operator.log", os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(logfd, "a") as log:
        info = os.fstat(log.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise SystemExit("operator log ownership/mode differs; stop")
        source.rename(target)
        log.write(json.dumps(dict(at=stamp, action="offline quarantine", source=str(source), destination=str(target), reason=reason)) + "\n")
        log.flush(); os.fsync(log.fileno())
finally:
    os.close(fd)
QUARANTINE
```

Command exit (including refusal or interruption) releases the lock. Never delete receipts or modify checkpoint/receipt contents. After successful quarantine, use the normal pinned `verify --from-clean-seed` resume; if inspection or logging fails, preserve the evidence and stop for owner recovery rather than forcing reset.

## K. Maintenance and change control

Mars owns S1656, this operator page, and the money-path test environment. Product owners own the pinned backend, frontend, and AIM Data code. Refresh this page when any pinned source SHA, image digest, port/origin, Compose topology, fixture contract, secret name, token permission, provider identifier, lifecycle command, evidence schema/path, browser version, or failure signature changes, and after any incident or accepted Council mandate.

Every behavioral change requires a newly pinned environment commit, focused tests, current Council review under the active roster, and a fresh external acceptance run. A tag, merge, unit suite, Compose health, or tunnel health alone is not approval. Never reuse reviewer votes from another SHA. Keep the S1656 scope frozen: no S1590 spec edit, production feature-default change, runbook-tooling change, alternate tunnel/listener, additional fixture, or adjacent improvement belongs here.

To roll back an environment candidate, stop using its SHA and perform guarded teardown with its own pinned lifecycle before reverting Git. Preserve its redacted evidence and exact identities. Do not roll production back, because this environment makes no production application deployment; the temporary route and DNS record must instead be proven absent. Any required file outside the approved chunk manifest or any new external/production mutation requires a specification amendment before implementation.

Residual review nits are recorded for the next relevant code change, not fixed by Chunk D: AIM Data's 409-path `serial_bound` hardening and `trust_channel_client.py:207` log wording; `seed/s3-fixture.py:24–42` validates `S1681_S3_ROLE_ARN` although the uploader does not use the role (broker/G9 do); `bin/nightly:48–50` silently discards inherited `S1656_RUNBOOKS_REPO` in favour of the file/default; and the nightly self-test shares the same 30-minute budget as the command (`bin/nightly:62–67`).
