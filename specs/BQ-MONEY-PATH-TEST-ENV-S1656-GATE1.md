# BQ-MONEY-PATH-TEST-ENV-S1656 Gate 1

**Status:** Specification candidate only. This document authorizes no build, secret creation, DNS change, Stripe object creation, deployment, production configuration change, or production mutation until the Council gate in section 12 passes.

**Build Queue entity:** `build:bq-money-path-test-env-s1656`

**Decision:** Max chose a disposable money-path test environment in S1656. A production override is rejected.

**Source trace:** runbooks `origin/main@e93a6334a82096aa8876e3ba10ee8ebdd724c4d3`; `ai-market-backend origin/main@229689c821022b2fe8f8901f7ca32eca6f685fcf`; AIM Data tag `aim-data-v1.22.7` peeled to `0660c106f04addf641dcb2684d6af2804f6b0435` (also `origin/main`); `ai-market-frontend@c845f50f1df02bd97bfc5e8f9011c78511da6699`. The product refs were fetched and checked against their live remotes on 2026-09-03. All source citations below refer to these exact commits.

## 1. Decision and problem

The S1590 release requires two proofs that production cannot safely provide today:

1. a real Stripe test-mode hosted setup completed through both a freshly reauthenticated return and a signed `checkout.session.completed` webhook, with exact-loader readiness afterward (`specs/BQ-DATA-VERIFICATION-S1590-PAYIN-ONBOARDING-AMENDMENT.md:530`); and
2. signed-in browser proof of the just-in-time card boundary, return flow, failure states, and separation from seller payouts (`specs/BQ-DATA-VERIFICATION-S1590-PAYIN-ONBOARDING-AMENDMENT.md:531`; `specs/BQ-DATA-VERIFICATION-S1590-GENERAL-AVAILABILITY-AMENDMENT.md:148-154`).

The old staging target is not an environment to repair or reuse. Its health charter points to a decommissioned backend and returns 404 on every run (`runbooks/e2e-test-status-publisher.md:126-135`). Production is currently configured with `DATA_VERIFICATION_ENABLED=true`, `STRIPE_PAYIN_ONBOARDING_ENABLED=true`, `STRIPE_TEST_MODE=false`, `FRONTEND_URL=https://ai.market`, and a configured platform account. This was read with the explicitly targeted Railway command required by `ai-market-backend.md:28-39`; no value or identifier was printed.

The production synthetic `seller-01` cannot be made payout-ready by using live Stripe. The answer is a disposable, test-only environment with a new database and Stripe test objects. It is not a production exception, a second staging environment, or a relaxation of any S1590 gate.

The existing browser harness is not this environment: its authenticated buyer and mutating seller phases remain planned, and its pay step remains blocked on separate sandbox routing (`e2e-browser-runner.md:36-55`). S1656 adds a bounded acceptance runner for this disposable stack. It does not retarget the production harness or its sanctioned production URL.

## 2. Current integration ground truth

### 2.1 Backend configuration

The backend already has independent, default-off `DATA_VERIFICATION_ENABLED` and `STRIPE_PAYIN_ONBOARDING_ENABLED` settings and a separate `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID` pin (`ai-market-backend:app/core/config.py:222-231`). It also has the exact existing Stripe names required here: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_TEST_MODE`, `STRIPE_TEST_SECRET_KEY`, `STRIPE_TEST_PUBLISHABLE_KEY`, and `STRIPE_TEST_WEBHOOK_SECRET` (`ai-market-backend:app/core/config.py:307-319`). The effective Stripe properties choose the `STRIPE_TEST_*` values only when `STRIPE_TEST_MODE=true` (`ai-market-backend:app/core/config.py:613-637`).

Current startup validation checks the pay-in platform account identifier and the frontend origin only when onboarding is enabled (`ai-market-backend:app/core/config.py:850-864`). Production permits only `https://ai.market`; a non-production HTTPS origin must be in the effective CORS allowlist; and the existing HTTP exception is exactly `ENVIRONMENT=test` with hostname `localhost` (`ai-market-backend:app/core/config.py:864-899`). Current test-mode validation only logs a warning (`ai-market-backend:app/core/config.py:840-848`). It does not fail startup on `sk_live_` or `pk_live_`. The live-key boot refusal in this specification is therefore a proposed new validation rule, not a claim about existing code.

The backend's default CORS list includes local ports 3000, 5173, 8080, and 8081 but not the port selected below; `CORS_ORIGINS_EXTRA` already exists for an additional origin (`ai-market-backend:app/core/config.py:591-607`). No new CORS setting is needed.

### 2.2 AIM Data register, publish, and seller readiness

The runbook contract says the sole live listing path is AIM Data's signed proxy to `/api/v1/vz/publish`, with separate VZ registration and a private key that remains on the install (`aim-data.md:208-224`). The seller-publish journey likewise separates registration, seller readiness, the signed receiver, the canonical listing record, and browser proof (`aim-data-seller-publish-journey.md:27-40`; `aim-data-seller-publish-journey.md:55-78`). S1656 reuses that path against the disposable backend; it does not create another publish route.

`POST /api/v1/vz/register` accepts an authenticated ai.market user, provisions a non-admin caller as a seller, and registers the AIM Data public key (`ai-market-backend:app/routers/vz_publish.py:64-115`). `POST /api/v1/vz/publish` validates the signed install JWT, requires Redis for replay and rate-limit protection, resolves the seller, and applies the active-seller capability before the canonical listing writer (`ai-market-backend:app/routers/vz_publish.py:122-178`). A provisioning seller receives only the existing fresh-create exception for the exact `readiness_gap` denial; this does not make the seller active (`ai-market-backend:app/routers/vz_publish.py:46-57`; `ai-market-backend:app/routers/vz_publish.py:160-178`).

The active-seller calculation requires a profile name, company name, `totp_enabled=true`, and Stripe payouts live (`ai-market-backend:app/services/capability_resolver.py:24-57`). The durable Stripe signal is `user.stripe_payouts_enabled`; missing or unreadable state fails closed, and only the string value `true` resolves live (`ai-market-backend:app/services/capability_resolver.py:168-200`). The seed must therefore establish all four facts. It may not infer active status from role alone.

The current synthetic-account creator accepts only buyer or seller roles, uses the reserved E2E domain, creates an active and verified `is_test=true` user, and deliberately creates no password (`ai-market-backend:app/e2e/synthetic_accounts.py:117-148`). Password mutation is guarded by database `is_test`, reserved domain, active status, and the packaged pool manifest (`ai-market-backend:app/e2e/synthetic_accounts.py:46-65`; `ai-market-backend:app/e2e/synthetic_accounts.py:68-99`). The committed pool manifest maps `buyer-01`, `seller-01`, and `seller-02` to the exact `E2E_SYNTHETIC_BUYER_01_*`, `E2E_SYNTHETIC_SELLER_01_*`, and `E2E_SYNTHETIC_SELLER_02_*` email/password names (`ai-market-backend:e2e/account_pool.json:4-7`; `ai-market-backend:e2e/account_pool.json:35-45`). By contrast, the dynamic `synthetic_account_secret_names(role, localpart)` helper prepends both the role and the full localpart, so `("seller", "seller-01")` derives the doubled `E2E_SYNTHETIC_SELLER_SELLER_01_*` shape (`ai-market-backend:app/e2e/account_pool.py:137-160`). The disposable seed must read the committed manifest entries and must not call that dynamic helper for these three fixtures. It must preserve the existing protections, exact committed names, and reserved-domain shapes without reusing production rows or copying a production database.

### 2.3 Stripe webhook and the isolated synthetic-event gap

The central Stripe route verifies `Stripe-Signature` before reading an event and uses the effective webhook secret selected by `STRIPE_TEST_MODE` (`ai-market-backend:app/api/v1/endpoints/webhooks.py:108-137`; `ai-market-backend:app/api/v1/endpoints/webhooks.py:303-329`). It inserts `stripe_events` before dispatch, permits a retry only from `failed`, and treats `processing` or `completed` as a duplicate (`ai-market-backend:app/api/v1/endpoints/webhooks.py:343-375`). After successful handling it marks the same row completed and commits (`ai-market-backend:app/api/v1/endpoints/webhooks.py:580-585`). `checkout.session.completed` is critical, so a handler failure rolls back and is recorded as failed for a provider retry (`ai-market-backend:app/api/v1/endpoints/webhooks.py:77-87`; `ai-market-backend:app/api/v1/endpoints/webhooks.py:609-640`).

The S1590 setup Session carries an exact five-field metadata dictionary: `purpose`, `contract_version`, `setup_attempt_id`, `party_id`, and `user_id` (`ai-market-backend:app/services/data_verification_payin_service.py:1159-1166`). The current synthetic exclusion resolves `user_id` and suppresses a synthetic `checkout.session.completed` event before the pay-in finalizer (`ai-market-backend:app/api/v1/endpoints/webhooks.py:198-211`; `ai-market-backend:app/api/v1/endpoints/webhooks.py:271-284`; `ai-market-backend:app/api/v1/endpoints/webhooks.py:378-393`). That is correct for production synthetic traffic but prevents a webhook-first completion for the required isolated test seller. The implementation must add a narrow exception only when all of these per-event conditions are true:

- `ENVIRONMENT` is exactly `test`;
- `STRIPE_TEST_MODE` is true;
- the event has `livemode=false`;
- event type is exactly `checkout.session.completed`;
- `event.account` is absent and the normalized webhook has no connected-account context;
- metadata is exactly the five-field S1590 dictionary, with the canonical pay-in purpose and contract version;
- `metadata.user_id` resolves to a user for which both `is_test=true` and the email domain is exactly the reserved `e2e-test.ai.market` domain; and
- the five metadata values and event Session ID resolve to one current, non-superseded local S1590 setup attempt owned by that user, with matching party, purpose, contract version, checkout Session, `expected_environment=test`, and `expected_livemode=false`.

The event-account value is normalized before dispatch (`ai-market-backend:app/api/v1/endpoints/webhooks.py:323-340`), while the existing attempt model and finalizer bind the current attempt, actor, account context, event Session, metadata, environment, and livemode (`ai-market-backend:app/models/data_verification_payin.py:39-131`; `ai-market-backend:app/services/data_verification_payin_service.py:798-838`; `ai-market-backend:app/services/data_verification_payin_service.py:1107-1123`). The exception must additionally reject before evaluating its allow conditions when `ENVIRONMENT` is `prod` or `production`, or when `FRONTEND_URL` is the canonical production marker `https://ai.market`; the existing validator defines those production markers (`ai-market-backend:app/core/config.py:877-882`). Only then may this one event continue to the existing pay-in finalizer. Production, non-pay-in synthetic events, malformed or unknown attempts, non-synthetic or wrong-domain users, connected-account events, order events, and every live-mode event retain the existing suppression. This uses existing settings and adds no bypass flag.

Passing section 5.2's live-key refusal is a process boot precondition, not a predicate re-evaluated for each webhook. No webhook is served unless that precondition has already passed.

The existing finalizer already checks Session, SetupIntent, PaymentMethod, customer, metadata, off-session usage, and `livemode`, then proves the ordinary default loader returns the same customer and payment method (`ai-market-backend:app/services/data_verification_payin_service.py:1034-1104`). Those checks are not weakened.

### 2.4 AIM Data and frontend routing

AIM Data's `ai_market_url` setting is configurable through the existing alias mechanism (`AIM_DATA_AI_MARKET_URL` and `VECTORAIZ_AI_MARKET_URL`) (`aim-data:app/config.py:26-32`; `aim-data:app/config.py:107-111`; `aim-data:app/config.py:275-288`). Its compose file already passes both variables, but defaults both to production (`aim-data:docker-compose.aim-data.yml:27-45`). The data-verification router constructs its real client with `settings.ai_market_url` (`aim-data:app/routers/data_verification.py:95-120`).

AIM Data refuses data verification until the dataset has a marketplace `listing_id`, and it parses that identifier before resolving the registered source artifact (`aim-data:app/services/data_verification_local_service.py:137-160`; `aim-data:app/services/data_verification_local_service.py:194-208`). Its explicit paid start checks pay-in readiness only after a current quote exists and before it claims a verification start (`aim-data:app/services/data_verification_local_service.py:564-587`). The UI displays the card handoff only from the returned setup state and labels the action as the explicit paid-verification start (`aim-data:frontend/src/components/DataVerificationFlow.tsx:400-436`).

One current path is not configurable: `PAYMENT_SETUP_URL` is hard-coded to `https://ai.market/dashboard/data-verification/payment-method` (`aim-data:app/services/data_verification_local_service.py:55-60`; `aim-data:app/services/data_verification_local_service.py:166-171`). Repointing only the two API URL variables would therefore send the test browser back to production. The implementation must explicitly add a new AIM Data Settings field named `data_verification_payment_handoff_url`, with the explicit environment aliases `AIM_DATA_PAYMENT_SETUP_URL` and `VECTORAIZ_PAYMENT_SETUP_URL`, defaulting to the current production URL. The distinct Settings name avoids collision with the existing response field `DataVerificationView.payment_setup_url` (`aim-data:app/schemas/data_verification.py:202-215`); the two required environment aliases remain unchanged. This is a proposed new setting. It is used only to replace the hard-coded constant, and its validator permits HTTP only for a localhost URL in the S1656 test install. No production default or copy changes.

The marketplace frontend's browser API base is the existing `NEXT_PUBLIC_API_URL`, with a localhost:8000 development fallback (`ai-market-frontend:api/client.ts:1-10`). Its example environment also names server-side `API_URL` (`ai-market-frontend:.env.example:1-2`), and Next rewrites read these existing names (`ai-market-frontend:next.config.ts:14-23`). No frontend setting or production code change is required.

## 3. Exact environment placement and shape

### 3.1 Placement

Create a new private repository, `aidotmarket/money-path-test-environment`, cloned on Titan-1 at:

```text
/Users/max/Projects/ai-market/money-path-test-environment-s1656
```

Its Docker Compose project name is exactly `ai-market-money-path-s1656`. Titan-1 is the correct host because it already runs the isolated AIM Data install, the operator browser, Docker/OrbStack, and the headless Infisical identity. This environment is development/test infrastructure and is not in any production critical path.

The existing AIM Data test install at:

```text
/Users/max/aim-data-e2e-seller01
```

is the reference pattern only and remains untouched. S1656 reproduces its isolated-volume, synthetic-import, seller-01, v1.22.7, and `DATA_VERIFICATION_ENABLED=true` shape inside the single `ai-market-money-path-s1656` Compose project. Because v1.22.7 hard-codes the production payment-setup URL, the implementation builds the smallest reviewed AIM Data release candidate containing only section 2.4's new setting and uses that exact SHA-derived image tag in the override. The v1.22.7 install is the baseline, not evidence that the unmodified image can satisfy the handoff.

### 3.2 Services and ports

| Service | Image or build | Host binding | Network exposure |
|---|---|---|---|
| `backend` | `ai-market-backend` built from `BACKEND_RC_SHA` | `127.0.0.1:18000 -> 8000` | Loopback only; private Compose network |
| `frontend` | `ai-market-frontend` built from `FRONTEND_RC_SHA` with `NEXT_PUBLIC_API_URL=http://localhost:18000` | `127.0.0.1:13000 -> 3000` | Loopback only; private Compose network |
| `postgres` | `postgres:16-alpine` | `127.0.0.1:15432 -> 5432` | Loopback only; new named volume |
| `redis` | a pinned Redis image digest selected during implementation | `127.0.0.1:16379 -> 6379` | Loopback only; new named volume |
| `webhook-proxy` | pinned nginx or equivalent minimal reverse proxy | `127.0.0.1:18002 -> 8080` | Accepts only the exact Stripe webhook path |
| `cloudflared` | a pinned Cloudflare image digest | no host port | Outbound tunnel to `webhook-proxy` only |
| AIM Data `app` | reviewed `AIM_DATA_RC_SHA` image based on v1.22.7 | `127.0.0.1:18081 -> 80` | S1656 private network and volumes |
| AIM Data `postgres` | `postgres:16-alpine` | no host port | S1656 private network and separate named volume |

The backend uses only the new PostgreSQL and Redis services. No Railway URL, production database dump, shared Docker volume, external Docker network, or production cache is allowed. Container host aliases for `api.ai.market` and Railway database hosts resolve to loopback as a second guard. The browser reaches only `http://localhost:13000`, `http://localhost:18081`, and Stripe-hosted test pages.

The non-secret test configuration is exact:

```text
ENVIRONMENT=test
STRIPE_TEST_MODE=true
DATA_VERIFICATION_ENABLED=true
STRIPE_PAYIN_ONBOARDING_ENABLED=true
FRONTEND_URL=http://localhost:13000
CORS_ORIGINS_EXTRA=http://localhost:13000
NEXT_PUBLIC_API_URL=http://localhost:18000
API_URL=http://backend:8000
AIM_DATA_AI_MARKET_URL=http://host.docker.internal:18000
VECTORAIZ_AI_MARKET_URL=http://host.docker.internal:18000
AIM_DATA_PAYMENT_SETUP_URL=http://localhost:13000/dashboard/data-verification/payment-method
VECTORAIZ_PAYMENT_SETUP_URL=http://localhost:13000/dashboard/data-verification/payment-method
```

The Compose service definitions inject `DATA_VERIFICATION_ENABLED=true` independently into backend and AIM Data from the single declared value.

### 3.3 Exact source identity

The environment repository contains `versions.env` with full 40-character `BACKEND_RC_SHA`, `FRONTEND_RC_SHA`, and `AIM_DATA_RC_SHA` values and pinned image digests. `./bin/up` refuses a branch name, tag-only value, moving `main`, short SHA, dirty checkout, or a checked-out commit different from the recorded SHA. It clones each product into a disposable state directory, checks out the exact commit detached, builds locally, records image digests, and labels every container with all three SHAs.

The final release-candidate SHAs cannot be this Gate 1 document's source baselines because sections 2.3 and 2.4 require reviewed code changes that do not exist at those baselines. Each implementation dispatch records its candidate SHA before the next chunk begins. The environment never builds an unreviewed working tree.

The acceptance runner is self-contained in the environment repository rather than borrowing a mutable host installation. Chunk D commits `package.json`, `package-lock.json`, and `playwright.config.ts`; pins `@playwright/test`, `playwright`, and `playwright-core` to exactly `1.61.0` with no range; and commits `browser/browser-version.json` with Chromium revision `1228` and browser version `149.0.7827.55`. The runner image is exactly `mcr.microsoft.com/playwright:v1.61.0-noble@sha256:35488358a60d3e7eacc4f02e0985e3b46240424d6d7b229732332016e6127508` for Titan-1's `linux/arm64` Docker engine. `./bin/preflight --check-browser-runner` is the runnable check: it refuses unless the lockfile resolves all three packages to `1.61.0`, the image digest matches, and the container reports the committed Chromium revision and browser version. `./bin/up` invokes that check before browser launch. This option is chosen so AC1 retains only Docker and Infisical as host prerequisites and cannot silently depend on a globally installed Node, Playwright, browser, or the separate production E2E harness.

## 4. Webhook ingress choice

Stripe CLI `stripe listen --forward-to` can forward sandbox events to a local endpoint, and Stripe documents it as the local-listener path. It is not selected here because it adds a separately authenticated, long-running CLI session and a listener signing secret whose lifecycle is tied to that session. That makes clean-clone boot, stable external replay, and the Infisical-only secret rule harder to prove.

Use a named Cloudflare Tunnel route instead:

```text
https://s1656-money-path-webhook.ai.market/api/v1/webhooks/stripe
```

Cloudflare Tunnel is an outbound-only connection from Titan-1, but a published application hostname is public. The tunnel therefore targets `webhook-proxy`, not `backend`. The proxy must:

- accept only `POST /api/v1/webhooks/stripe`;
- reject every other method and path with 404;
- preserve the raw request body and `Stripe-Signature` header byte-for-byte;
- add no authentication header and perform no body parsing;
- impose a small request-body limit sufficient for Stripe events; and
- forward only to `http://backend:8000/api/v1/webhooks/stripe` on the private Compose network.

The endpoint is registered in Stripe test mode for the exact events needed by S1590, including `checkout.session.completed` and the data-verification PaymentIntent lifecycle. The signing secret from that test-mode endpoint is stored as `STRIPE_TEST_WEBHOOK_SECRET`. The hostname never serves the frontend, authentication API, health route, database, Redis, or AIM Data.

The hostname is a bounded DNS record in the production `ai.market` zone, even though it routes only test traffic. Creation after Gate 1 is the sole allowed production-zone mutation. `./bin/down` must disable and remove the Cloudflare Tunnel published-application route and delete the exact `s1656-money-path-webhook.ai.market` DNS record, then fail unless the Cloudflare control-plane lookup shows neither route nor record and an authoritative DNS query shows the hostname no longer resolves. The redacted teardown evidence records the checked hostname, route/record absence, query time, and command exit status without exposing the tunnel token or zone identifier.

References for the transport decision: [Stripe local webhook forwarding](https://docs.stripe.com/webhooks) and [Cloudflare Tunnel published applications](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/).

## 5. Secrets and live-mode refusal

### 5.1 Infisical boundary

Create a dedicated Infisical environment with slug `test-env` in the existing `ai-market-backend` project. The current runbook lists only `dev`, `staging`, and `prod`, so `test-env` is a new environment, not a renamed existing one (`infisical-secrets.md:24-36`). It has no Railway sync and no path into the production environment.

Store these existing backend names in `ai-market-backend/test-env`:

| Name | Required value class |
|---|---|
| `STRIPE_TEST_SECRET_KEY` | Stripe test secret key beginning `sk_test_` |
| `STRIPE_TEST_PUBLISHABLE_KEY` | Stripe test publishable key beginning `pk_test_` |
| `STRIPE_TEST_WEBHOOK_SECRET` | signing secret for the S1656 test-mode endpoint |
| `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID` | the platform account returned by the test key |

Also store test-only operational credentials there using the committed pool-manifest names: `E2E_SYNTHETIC_SELLER_01_EMAIL`, `E2E_SYNTHETIC_SELLER_01_PASSWORD`, `E2E_SYNTHETIC_SELLER_01_TOTP`, `E2E_SYNTHETIC_SELLER_02_EMAIL`, `E2E_SYNTHETIC_SELLER_02_PASSWORD`, `E2E_SYNTHETIC_BUYER_01_EMAIL`, and `E2E_SYNTHETIC_BUYER_01_PASSWORD`, plus database passwords, AIM Data local keys, and the proposed operational secret `CLOUDFLARE_TUNNEL_TOKEN`. The `_EMAIL`/`_PASSWORD` names are the exact committed entries (`ai-market-backend:e2e/account_pool.json:4-7`; `ai-market-backend:e2e/account_pool.json:35-45`); seller-01's `_TOTP` name is the fixed accompanying secret for its enabled TOTP. `CLOUDFLARE_TUNNEL_TOKEN` is not an application setting; it is consumed only by the `cloudflared` container. The seed must not call `synthetic_account_secret_names` for any of these fixtures.

Secret values appear in no Compose file, dotenv file, Git object, build argument, image layer, command-line argument, log, screenshot, test artifact, or evidence bundle. `infisical run --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=test-env -- ...` injects them into the one-command process. The project ID must be explicit because Titan-1's default Infisical project points elsewhere (`infisical-secrets.md:202-204`). Existing app settings are case-sensitive, so names remain canonical upper snake case (`infisical-secrets.md:185-189`).

Do not copy or expose `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET_PREVIOUS`, or any `sk_live_` value. The previous webhook secret is load-bearing because signature verification tries it after the effective webhook secret (`ai-market-backend:app/api/v1/endpoints/webhooks.py:117-127`). The production runbook's `STRIPE_TEST_*` values currently sit beside live values in `prod`; S1656 must not reuse that mixed drawer (`infisical-secrets.md:122-130`).

### 5.2 Mandatory boot assertions

Before migrations, seed, health-ready, or browser launch, the one-command boot fails unless all of these are true:

1. `ENVIRONMENT == "test"`;
2. `STRIPE_TEST_MODE is True`;
3. `STRIPE_TEST_SECRET_KEY` begins `sk_test_` and never `sk_live_`;
4. `STRIPE_TEST_PUBLISHABLE_KEY` begins `pk_test_` and never `pk_live_`;
5. `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, and `STRIPE_WEBHOOK_SECRET_PREVIOUS` are each absent or empty;
6. `STRIPE_TEST_WEBHOOK_SECRET` is non-empty and canonical for Stripe signing-secret use;
7. `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID` is one canonical `acct_` identifier;
8. retrieving the platform Account with the effective test key returns that exact configured account; and
9. `FRONTEND_URL` passes the existing localhost-only test exception.

Assertions 1-7 and 9 are pure and run before Account retrieval. A supplied `sk_live_` or `pk_live_`, even a fake one, fails locally before a socket opens. Tests instrument the Stripe call boundary and prove call count zero on such a failure. Account retrieval is the only permitted Stripe preflight call and proves the test key belongs to the pinned test platform.

The new Settings assertions are scoped only to the `ENVIRONMENT == "test"` branch of the existing validator. They do not run as unconditional shared assertions and cannot refuse a production boot with `ENVIRONMENT` in `prod`/`production`, canonical `FRONTEND_URL=https://ai.market`, or live-name variables set; the current validator already separates test-localhost and production handling (`ai-market-backend:app/core/config.py:839-900`). The exact fail-closed tests cover each of the four live-name variables, including `STRIPE_WEBHOOK_SECRET_PREVIOUS`, and prove production-shaped Settings remain accepted by this new test-only branch. Account retrieval belongs in the environment repository's `bin/preflight`, after the pure checks and before migrations, seed, or health-ready. The application retains its current runtime account checks. No new bypass or safety setting is authorized.

## 6. Seed and data isolation

`./bin/seed` is idempotent against a newly migrated S1656 database and refuses any database host outside the Compose service. It reads the exact three committed manifest entries named in section 2.2, never calls the dynamic secret-name helper, and creates only these fixtures:

### 6.1 Synthetic seller

- email `seller-01@e2e-test.ai.market` from committed manifest name `E2E_SYNTHETIC_SELLER_01_EMAIL`, with password from committed manifest name `E2E_SYNTHETIC_SELLER_01_PASSWORD` and fixed accompanying TOTP name `E2E_SYNTHETIC_SELLER_01_TOTP`;
- `role=seller`, `status=active`, `email_verified=true`, and `is_test=true`;
- a non-empty display/profile name and company name;
- password from Infisical;
- TOTP enabled with the seed held only in Infisical;
- exactly one active `auth_user` PartyIdentity for the seller party;
- seller capability persisted in the normal seller state; and
- one Stripe Connect Express test account belonging to the same test platform.

The seeder creates the Express account with the effective `sk_test_` key, uses Stripe-supported test identity and external-account data, requests only the capability needed for payouts, and retrieves it until Stripe reports `payouts_enabled=true`. Stripe's test-mode response is the authority. Only after that response may the seeder write the canonical `stripe_connect` PartyIdentity and the durable `user.stripe_payouts_enabled="true"` projection. It then runs `CapabilityResolver.resolve` and requires effective seller status `active` with no missing steps. It must never set the payout projection independently of a retrieved test account.

The ordinary pay-in platform account and the seller Connect Express account are different objects. The seeder records only opaque local fixture references in evidence, never either `acct_` value.

### 6.2 Synthetic buyer

- email `buyer-01@e2e-test.ai.market` from committed manifest name `E2E_SYNTHETIC_BUYER_01_EMAIL`, with password from committed manifest name `E2E_SYNTHETIC_BUYER_01_PASSWORD`;
- `role=buyer`, `status=active`, `email_verified=true`, and `is_test=true`;
- password from Infisical; and
- no seller, Connect, listing, ordinary payment-method, or verification state.

### 6.3 Synthetic TOTP-disabled seller

- email `seller-02@e2e-test.ai.market` from committed manifest name `E2E_SYNTHETIC_SELLER_02_EMAIL`, with password from committed manifest name `E2E_SYNTHETIC_SELLER_02_PASSWORD`;
- `role=seller`, `status=active`, `email_verified=true`, and `is_test=true`;
- a non-empty display/profile name and company name;
- password from Infisical;
- `totp_enabled=false`, with no TOTP seed or code;
- exactly one active `auth_user` PartyIdentity for the seller party; and
- no Stripe Connect account or identity, payout projection, ordinary payment method, setup attempt, listing, or verification state.

The seller-02 fixture exists only for the GA hidden/unavailable proof. The journey must not mutate seller-01 or buyer-01 to obtain this state. This is a normal synthetic seller row: the user model carries seller identity, name/company, TOTP, and payout fields (`ai-market-backend:app/models/user.py:51-72`; `ai-market-backend:app/models/user.py:83-87`), and the existing capability resolver treats `totp_enabled` other than true and absent payout truth as missing readiness steps (`ai-market-backend:app/services/capability_resolver.py:37-57`; `ai-market-backend:app/services/capability_resolver.py:168-200`).

### 6.4 Reset and clean-seed role execution

`./bin/reset` uses the same label-guarded target checks as teardown, drops only the S1656 disposable databases and volumes, reruns migrations, and invokes `./bin/seed` to recreate exactly seller-01, buyer-01, and seller-02 in their declared initial states. It creates no listing, Connect state for buyer-01 or seller-02, pay-in setup attempt, payment method, or verification state. `./bin/verify --from-clean-seed` is the single acceptance command: it performs that guarded reset/reseed internally, then runs the signed-out, buyer-01, seller-02, and eligible seller-01 browser cases in fixed order. No fixture mutation, ad-hoc SQL, manual database edit, or extra unlisted fixture is permitted.

### 6.5 No production data

No production database snapshot, customer row, Stripe object identifier, login cookie, token, listing, sample, corpus record, or secret is copied. The listing source is a committed, generated synthetic CSV fixture with no personal data. Reset always recreates the local databases from migrations and seed; it never restores a dump.

## 7. AIM Data installation and real journey

The environment reproduces the `/Users/max/aim-data-e2e-seller01` pattern through a Compose override in the S1656 repository. It does not edit that reference directory's `.env`, join its Compose project, or share its volumes. The override supplies the reviewed AIM Data image, both existing API target aliases, the new payment-setup URL aliases, and `DATA_VERIFICATION_ENABLED=true` through the process environment.

The operator signs into AIM Data as seller-01. AIM Data performs the real `/api/v1/vz/register` flow, prepares the synthetic dataset, and sends the real signed `/api/v1/vz/publish`. The active seller gate must pass from seeded facts, not from the provisioning create-only exception. The returned listing is stored in the test Postgres and renders at `http://localhost:13000/listings/<slug>`.

The acceptance walk is one connected sequence:

1. In normal Chrome, sign into AIM Data as seller-01 and publish one synthetic listing.
2. Open data verification. Before quote acceptance there is no card prompt, card setting, or setup handoff.
3. Request a quote, review it, select both required acknowledgements, and use the explicit paid-start action.
4. The server returns `setup_required`; only then does AIM Data show the handoff to the local test frontend.
5. Sign into the test frontend as the same seller, complete the required reauthentication, and open the Stripe-hosted `mode=setup` page.
6. Enter Stripe test card data only on Stripe's hosted page and complete the setup.
7. Let Stripe deliver a correctly signed test-mode `checkout.session.completed` event through the S1656 hostname before using return reconciliation in the webhook-first case. Verify the pay-in finalizer, then deliver the same event again and verify one completed `stripe_events` row and a duplicate response with no second finalization.
8. Complete the separate return-first case with a fresh post-return reauthentication and prove return and webhook converge.
9. Readiness becomes `ready`. Return to AIM Data and use the explicit paid start again.
10. AIM Data receives a signed scan spec, performs the approved local scan, submits the signed report, and completes the verification lifecycle.
11. The backend creates a test-mode PaymentIntent with `capture_method=manual`, reaches `requires_capture`, and captures the successful final charge. The current manual authorization call already supplies `capture_method="manual"`, `confirm=true`, `off_session=true`, and the bound customer and payment method (`ai-market-backend:app/services/data_verification_payment_service.py:257-280`); the real test proves those current semantics rather than replacing them.

The browser evidence runs the GA access variants against the test frontend from the section 6.4 clean seed: signed out receives the standard 401 and exercises login redirect or refresh; signed-in buyer-01 and signed-in TOTP-disabled seller-02 each receive the same hidden/404 result; eligible seller-01 reaches setup only through the paid-service handoff. No Settings card control appears. All cases run from `./bin/verify --from-clean-seed` and are conjunctive; no user is mutated between roles.

Evidence may contain local UUIDs, run IDs, timestamps, HTTP statuses, boolean Stripe mode/status fields, redacted screenshots, and exact source/image SHAs. It may not contain email addresses, passwords, TOTP seeds/codes, card data, Checkout URLs, Stripe object IDs, webhook payloads, signatures, API keys, billing data, or raw source rows.

## 8. Independently testable acceptance criteria

Each criterion is required and must be testable from outside the service process. Unit tests are supporting evidence, not a substitute.

**AC1 — Clean-clone boot.** From a clean clone of `aidotmarket/money-path-test-environment` on Titan-1, with only Docker and an authorized Infisical machine identity already present, `./bin/up` is the only command. It validates exact product SHAs and the committed package/lock/config/browser manifests, runs `./bin/preflight --check-browser-runner`, builds all three product images, starts the digest-pinned Playwright 1.61.0 / Chromium 149.0.7827.55 revision 1228 runner, starts PostgreSQL 16 and Redis, migrates, seeds, starts the webhook tunnel, and waits for healthy backend, frontend, AIM Data, database, cache, and browser-runner readiness. No host Node, global Playwright, global browser, manual file edit, or second terminal is required.

**AC2 — Live-key fail closed.** A throwaway boot with `STRIPE_TEST_SECRET_KEY=sk_live_refusal_probe` or `STRIPE_TEST_PUBLISHABLE_KEY=pk_live_refusal_probe`, or with any non-empty `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, or `STRIPE_WEBHOOK_SECRET_PREVIOUS`, exits nonzero before migrations, seed, health-ready, or any Stripe call. Instrumented evidence proves zero network calls. No real live key or secret is used in this test. The refusal is exercised under `ENVIRONMENT=test`; a separate Settings test proves the new branch cannot refuse production boot.

**AC3 — Isolation.** Container inspection shows only the named S1656 volumes and private networks, exact loopback port bindings, no production database/Redis URL, no live Stripe name/value, and no external Docker network. Immediately after clean seed and before the listing is published, the test database contains exactly three users—seller-01, buyer-01, and seller-02—and only their section 6 fixture state.

**AC4 — Seed truth.** A host-side verifier proves the seed consumed the committed `E2E_SYNTHETIC_SELLER_01_*`, `E2E_SYNTHETIC_BUYER_01_*`, and `E2E_SYNTHETIC_SELLER_02_*` manifest names and did not call the dynamic helper. Seller-01 is `is_test`, has name, company, TOTP, one active `auth_user`, one separate test Connect Express identity, a Stripe-retrieved `payouts_enabled=true`, and effective seller status active. Buyer-01 has no seller or payment state. Seller-02 is an `is_test` seller with name and company, `totp_enabled=false`, one active `auth_user`, and no Connect, payout, listing, ordinary payment-method, setup-attempt, or verification state. Evidence redacts all provider identifiers and credentials.

**AC5 — Register, publish, and render.** Starting from the AIM Data UI, seller-01 registers its install and publishes exactly one synthetic listing through the signed VZ route. The returned listing ID exists in test Postgres and the listing renders in normal Chrome at the test frontend. Production listing/search reads show no S1656 marker.

**AC6 — Just-in-time setup boundary.** Browser and component evidence proves no card control in Settings, no card prompt before quote acceptance and both acknowledgements, and no handoff before explicit paid start. That start returns `setup_required` and then, and only then, exposes the local test-frontend handoff.

**AC7 — Hosted setup and signed webhook.** The seller completes Stripe-hosted setup in test mode. A real signed `checkout.session.completed` event with `livemode=false` reaches the exact public webhook path, finalizes the current attempt, and is stored as completed. Replaying the same event returns already processed, leaves one dedupe row, and produces no second identity mutation. Invalid signatures fail before dedupe or lookup.

**AC8 — Return convergence and readiness.** A distinct setup run proves a freshly reauthenticated return and the signed webhook converge on the same ordinary identity. Readiness becomes `ready`; Customer, SetupIntent, PaymentMethod, off-session usage, and livemode checks pass; Connect remains unchanged.

**AC9 — End-to-end paid verification.** From AIM Data, the same listing completes quote, explicit paid start, signed scan-spec issue, local scan, signed report ingest, final lifecycle, real test-mode manual authorization, and successful capture. Stripe evidence shows only test mode and manual capture. No raw data or forbidden provider identifier enters evidence.

**AC10 — GA browser roles.** From a guarded clean reset/reseed, the one command `./bin/verify --from-clean-seed` exercises signed-out standard 401 login/refresh behavior, signed-in buyer-01 as the non-seller, signed-in seller-02 with TOTP disabled, and eligible seller-01. Buyer-01 and seller-02 receive indistinguishable 404/unavailable behavior; seller-01 reaches setup only from the paid-service handoff. The command performs no ad-hoc SQL and does not mutate one fixture into another role. This is the S1590 GA AC9 and AC12 proof substrate.

**AC11 — One-command reset and teardown.** `./bin/reset` removes only S1656 containers, networks, and volumes, then recreates, migrates, and reseeds the empty environment with exactly the three section 6 users. `./bin/down` removes only containers, networks, and disposable volumes labeled for the single S1656 Compose project, stops the tunnel, disables/removes its published-application route, and deletes the exact S1656 DNS record. Each command checks the compose project and Cloudflare target identities before deletion and refuses an unresolved or non-S1656 target. Teardown is not successful until Cloudflare control-plane evidence shows both the route and DNS record absent and an authoritative DNS query shows the hostname no longer resolves.

Stripe test objects are deleted or rejected when the provider supports that operation. Provider objects that Stripe retains remain test-mode objects tagged with the fixed S1656 environment marker; they are never presented as deleted. Local teardown success does not depend on falsifying provider retention.

**AC12 — No production effect.** Before and after the journey, read-only checks prove production flags, deployment SHAs, user/listing counts for the S1656 marker, public discovery, and existing Cloudflare routes/records are unchanged; the reserved S1656 route and DNS record are absent again after teardown. No Railway deployment or variable write occurred. No production Event Ledger, customer, listing, payment, Connect, corpus, or cache row was created or changed. The temporary S1656 DNS record described in section 4 is the sole authorized production-zone mutation and routes no production service or traffic.

## 9. Operator runbook requirement

The implementation is incomplete until the same reviewed runbooks change adds root page `money-path-test-environment.md` with the current five-field frontmatter and literal `## When it breaks` section. It must also carry the requested §A-§K structure:

- **§A Purpose and safety boundary** — what the environment proves and what it cannot touch.
- **§B Exact placement and topology** — repository, directories, Compose project, ports, networks, and tunnel hostname.
- **§C Source and image identity** — SHA/digest pinning and clean-clone rules.
- **§D Secrets** — Infisical project/environment, names, injection, redaction, and live-key refusal.
- **§E Boot** — one command, prerequisites, health checks, and expected output.
- **§F Seed** — seller-01, buyer-01, seller-02, committed manifest names, Connect Express, idempotency, clean reset, and no-production-data proof.
- **§G Operate the journey** — register, publish, quote, paid start, setup, webhook, readiness, scan, capture, and browser variants.
- **§H Evidence** — independently readable evidence checklist and forbidden fields.
- **§I When it breaks** — the literal required heading and failure/symptom table.
- **§J Reset and teardown** — exact safe commands, target validation, three-user reseed, tunnel-route and DNS-record removal proof, provider retention, and recovery.
- **§K Maintenance and change control** — owners, refresh triggers, SHA updates, Council gate, and rollback.

The §I table must have at least these rows: live-key prefix refusal; platform-account mismatch; frontend origin rejected; source SHA mismatch; occupied port; migration failure; Redis unavailable; seller not active with exact missing steps; VZ signature/replay failure; AIM Data still targeting production; payment setup URL still targeting production; tunnel down; webhook signature failure; webhook synthetically suppressed; duplicate not deduped; readiness stuck pending; manual authorization not `requires_capture`; capture failure; reset target-label mismatch; and any production marker observed.

Run `scripts/index.py` so the page is registered in generated `INDEX.md` and its error signatures in `ERRORS.md`. `TOPIC-ROUTER.md` does not exist at the source baseline and is NOT created; the S1656 brief's reference to it is superseded by the generated `INDEX.md`/`ERRORS.md` pair, which is the current registration mechanism.

## 10. Non-goals

- No production feature-flag, Railway variable, deployment, database, Redis, Stripe, existing Cloudflare route/record, customer, or listing change. The sole exception is creation and teardown of the reserved S1656 test-only DNS record and tunnel route described in section 4; they may target no production service and must be proven absent after `./bin/down`.
- No production override for seller-01 and no path that makes a production synthetic seller payout-ready.
- No live-mode Stripe key, Customer, SetupIntent, PaymentMethod, PaymentIntent, charge, connected account, transfer, or payout.
- No production data copied into a test database or AIM Data fixture.
- No change to any S1590 specification, acceptance criterion, privacy boundary, payment state machine, publication contract, price, or connector.
- No replacement of the signed VZ register/publish path, active-seller gate, Stripe signature check, `stripe_events` dedupe, exact pay-in finalizer, or manual-capture implementation.
- No proactive card setting, embedded Stripe Elements, iframe, client secret, card display, or collection of card data outside Stripe-hosted test pages.
- No general synthetic-event suppression bypass. The isolated pay-in exception is conjunctive and impossible when `ENVIRONMENT` is production or an event is live-mode.
- No standing staging service, public frontend, public backend, customer-facing SLA, scheduled production job, or production critical-path dependency on Titan-1.
- No new runbook enforcement machinery.

## 11. Finite implementation chunks

Each chunk is one MP dispatch and one commit. A dispatch names the exact repository baseline, branch, acceptance subset, and complete file manifest below. Needing another file stops the dispatch and requires a spec amendment. Chunk D's named Playwright dependency requires its exact committed lockfile; no other generated lockfile change is expected.

### Chunk A — backend test-mode safety and webhook routing

**Repository:** `aidotmarket/ai-market-backend`

**Files:**

- `app/core/config.py`
- `app/api/v1/endpoints/webhooks.py`
- `tests/test_data_verification_payin_readiness.py`
- `tests/test_e2e_stripe_isolation.py`
- `tests/test_webhooks.py`

**Boundary:** Add the section 5.2 test-environment-scoped fail-closed validation and the section 2.3 conjunctive test-environment pay-in routing. Tests must cover each live-name variable including `STRIPE_WEBHOOK_SECRET_PREVIOUS`, both production markers, live mode, non-synthetic and wrong-domain users, malformed/unknown/superseded attempts, mismatched bindings, connected-account events, and every non-pay-in synthetic event. Preserve every production and non-pay-in suppression result. No endpoint, schema, payment, Connect, migration, or feature-default change.

### Chunk B — AIM Data local payment-handoff URL

**Repository:** `aidotmarket/aim-data`

**Files:**

- `app/config.py`
- `app/services/data_verification_local_service.py`
- `tests/test_data_verification_local_service.py`
- `frontend/src/components/DataVerificationFlow.test.tsx`

**Boundary:** Add the explicitly new `data_verification_payment_handoff_url` Settings field with the unchanged `AIM_DATA_PAYMENT_SETUP_URL` and `VECTORAIZ_PAYMENT_SETUP_URL` aliases, preserve the production default, allow only the bounded localhost test URL for S1656, and replace the hard-coded constant. Preserve the existing response field `DataVerificationView.payment_setup_url`. No API-target, UI copy, flow, billing, publish, scan, or customer-compose default change.

### Chunk C — disposable environment foundation

**Repository:** new private `aidotmarket/money-path-test-environment`

**Files:**

- `.gitignore`
- `README.md`
- `versions.env`
- `compose.yaml`
- `compose.aim-data.override.yaml`
- `config/webhook-proxy.conf`
- `bin/preflight`
- `bin/up`
- `bin/down`
- `bin/reset`
- `tests/compose-contract.sh`

**Boundary:** Exact source/image pinning, ports, private networks, Infisical injection, proxy/tunnel, safe lifecycle commands, health checks, Cloudflare route/DNS teardown checks, and structural tests. `versions.env`, `compose.yaml`, and `bin/preflight` reserve the exact section 3.3 runner image/digest and fail-closed check contract, but no seed or browser implementation lands until Chunk D.

### Chunk D — seed and executable acceptance journey

**Repository:** `aidotmarket/money-path-test-environment`

**Files:**

- `versions.env`
- `compose.yaml`
- `package.json`
- `package-lock.json`
- `playwright.config.ts`
- `fixtures/synthetic-listing.csv`
- `seed/seed.py`
- `bin/preflight`
- `bin/up`
- `bin/seed`
- `bin/verify`
- `browser/browser-version.json`
- `browser/s1590-money-path.spec.ts`
- `tests/compose-contract.sh`
- `tests/test-seed-contract.py`
- `tests/test-journey-contract.py`

**Boundary:** The self-contained exact Playwright/Chromium runner manifests, exactly three synthetic accounts from the committed pool names, guarded reset/reseed, test Connect Express truth for seller-01 only, one-command GA role execution, real register/publish, Stripe-hosted setup, signed webhook/dedupe, readiness, scan, manual capture, evidence redaction, and production no-effect checks. `versions.env`, `compose.yaml`, `bin/preflight`, `bin/up`, and `tests/compose-contract.sh` may change only to complete the already-reserved runner image, service, check, launch, and structural assertions; the package lock may contain only the exact section 3.3 dependency graph. No fixture mutation, ad-hoc SQL, external host runner, or mock may satisfy an external acceptance criterion.

### Chunk E — operator runbook and registration

**Repository:** `aidotmarket/runbooks`

**Files:**

- `money-path-test-environment.md` (new)
- `INDEX.md`
- `ERRORS.md`

**Boundary:** Add only section 9's operating page and static topic lookup, then regenerate the existing indexes. No S1590 spec change and no runbook tooling change.

### Release-evidence step — no implementation files

After Chunks A-E are individually reviewed, record their exact SHAs in `versions.env`, review that environment SHA again, and run AC1-AC12. Evidence is stored outside Git in the approved redacted evidence location. A passing unit suite, merge label, image tag, compose status, or tunnel health is not release evidence by itself.

## 12. Council review checklist

CORE S3 payments review requires unanimity. CC, GLM, and DeepSeek must each approve the exact spec SHA before any implementation dispatch. The same three reviewers must approve every implementation SHA before that SHA is merged, built into the environment, or used as acceptance evidence.

- [ ] Review the exact full SHA. Any edit invalidates all prior verdicts on that artifact.
- [ ] Record exact reviewer model identity, verdict, mandates, and immutable response reference for CC, GLM, and DeepSeek.
- [ ] Confirm the environment is disposable, test-only, and placed exactly on Titan-1 as specified.
- [ ] Confirm no live Stripe key or live-name secret reaches a container and the prefix refusal runs before network access.
- [ ] Confirm ordinary pay-in platform state remains separate from the seller's test Connect Express payout identity.
- [ ] Confirm the webhook-only tunnel cannot expose any other backend or frontend route.
- [ ] Confirm the synthetic-event exception is impossible in production and does not weaken order, Connect, payout, or other synthetic suppression.
- [ ] Confirm AIM Data's production payment-setup URL remains the default and only the explicit test override can point to localhost.
- [ ] Confirm source SHAs, image digests, Compose targets, reset targets, and teardown targets are exact and fail closed.
- [ ] Confirm all data is synthetic and no production dump, credential, object identifier, or raw row enters the environment or evidence.
- [ ] Confirm AC1-AC12 are external, conjunctive, and cannot be satisfied by mocks, API-only output, or wrapper status.
- [ ] Confirm each chunk is one MP dispatch with exactly its listed manifest.
- [ ] Confirm there is no production flag change or mutation beyond the exact temporary S1656 DNS record/tunnel route, that both are proven absent after teardown, and that there is no real-mode Stripe object, S1590 amendment, or adjacent improvement.
- [ ] Record unanimous approval. Any dissent, missing reviewer, wrong SHA, unavailable required reviewer, or unresolved blocking mandate stops the build.

## 13. Open questions and stop conditions

1. Resolved by Mars (S1656): `TOPIC-ROUTER.md` is absent from `origin/main` and is not created; registration is `INDEX.md`/`ERRORS.md` via `scripts/index.py` only.
2. The exact `BACKEND_RC_SHA`, `FRONTEND_RC_SHA`, and `AIM_DATA_RC_SHA` are implementation outputs. No current baseline may be substituted because the required backend and AIM Data changes do not exist there.
3. The hostname `s1656-money-path-webhook.ai.market`, the Stripe test-mode platform account, the test webhook endpoint, and the Infisical `test-env` environment must be created by an authorized operator after Gate 1. If any cannot be created with test-only scope, or if the Cloudflare tunnel route and DNS record cannot be removed and proven absent on teardown, stop. Do not fall back to production, reuse the mixed `prod` secret environment, or silently switch to Stripe CLI.
4. If Stripe cannot return `payouts_enabled=true` for a test-mode Express account using its supported test process, stop and bring back provider evidence. Do not substitute a Standard or live account and do not set the durable payout projection by hand.
5. If the environment needs any file outside a chunk manifest, any non-local service besides Stripe/Infisical/Cloudflare/GitHub, or any production mutation beyond section 4's exact temporary DNS record and tunnel route to pass, stop and amend this specification.
