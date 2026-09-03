---
title: S1656 Money Path Test Environment
owner: vulcan
last_verified: '2026-09-03'
aliases:
  - BQ-MONEY-PATH-TEST-ENV-S1656
  - S1656 money path
  - money-path-test-environment
  - ai-market-money-path-s1656
error_signatures:
  - live Stripe secret-key prefix refused before network access
  - live Stripe publishable-key prefix refused before network access
  - Stripe test key does not belong to the pinned platform Account
  - FRONTEND_URL must equal http://localhost:13000
  - source checkout is dirty
  - source checkout differs from the recorded SHA
  - seller-01 effective seller capability is not active
  - Stripe redelivery must record duplicate without another finalization
  - backend did not record Stripe provider redelivery as duplicate
  - parsed and normalised production snapshots differ
  - reset target lacks the exact S1656 ownership label
  - deployment marker observed; seed refused
  - immutable mint-policy validation failed
  - Cloudflare targets remain or absence is unproved
  - pinned host-network browser-runner cannot reach all localhost origins
---

# S1656 Money Path Test Environment

This page operates the disposable, test-only environment that exercises the S1590 money path without using production customer data, production Stripe mode, a Railway database or cache, or a production application deployment. It describes the real implementation at `aidotmarket/money-path-test-environment` Chunk C main `64e57f23b0e83fefc02e7ea15d651a5dad5e8a7a` plus Chunk D candidate `6d9b434ab42faff1218eb59c78e171dd58d5cc64`; it does not claim that the candidate has passed its later Council review or AC1-AC12 release-evidence run.

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
| ai-market-backend | `267f68fd7582453d95f504bc612d18570852e287` |
| ai-market-frontend | `c845f50f1df02bd97bfc5e8f9011c78511da6699` |
| AIM Data source | `3bb318440d71b79162ef6a9ae625f1c8e30ca609` |
| AIM Data image | `v1.22.8-rc.1@sha256:74c3b233fd288b5ec8bc9ce37de2f43ae1ee833bad757e70015f894f45c8c7bd` |
| Browser runner | Playwright `1.61.0`, Chromium revision `1228`, browser `149.0.7827.55` |

`./bin/up` prepares managed clones under `.state/sources/{backend,frontend,aim-data}` from the exact GitHub remotes, requires clean working trees, fetches the full SHAs, and checks them out detached. `./bin/preflight` refuses short SHAs, branches, dirty trees, wrong remotes, tag/SHA disagreement, image-digest disagreement, or browser package/revision drift. Do not repair a pin failure by moving a tag, selecting `main`, editing a managed checkout, or substituting another image.

Successful preflight writes `.runtime/aim-data-image-digest.json`. After local backend/frontend builds, `up` writes `.runtime/image-digests.json` with the three source SHAs and image digests. These runtime files support identity inspection; they are not AC1-AC12 release evidence.

## D. Secrets and credential split

The dedicated application-secret boundary is Infisical project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment `test-env`, secret path `/`. It has no Railway sync. The lifecycle reads the authorized machine identity from `~/.config/infisical/sysadmin-token`, sets `INFISICAL_API_URL=https://secrets.ai.market`, and injects the environment through:

```sh
infisical run --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=test-env -- <command>
```

The exact `test-env` secret names are:

```text
STRIPE_TEST_SECRET_KEY
STRIPE_TEST_PUBLISHABLE_KEY
STRIPE_TEST_WEBHOOK_SECRET
STRIPE_PAYIN_PLATFORM_ACCOUNT_ID
SECRET_KEY
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

The credential responsibilities are deliberately separate:

| Credential | Stored/injected from | Allowed work | Explicitly forbidden |
| --- | --- | --- | --- |
| `CLOUDFLARE_TUNNEL_TOKEN` | `test-env`; `cloudflared` container only | Connect the existing tunnel | Policy reads, route/DNS management, token lifecycle |
| `CLOUDFLARE_S1656_TEARDOWN_API_TOKEN` | `test-env`; host lifecycle only | Read, remove, and prove absence of only the exact S1656 route and DNS record | Token mint/read/revoke, container injection, unrelated Cloudflare objects |
| `CLOUDFLARE_ADMIN_API_TOKEN` | project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, `prod`; isolated admin subprocess only | Permission-group discovery, teardown-token mint, token re-read, revocation, post-revocation proof; if the narrow token is already inactive/missing, read-only route/DNS absence proof | Route or DNS mutation |

The teardown token has exactly `Cloudflare Tunnel Write` on account `d5346d3e0f8f344c5f4915aaca689adf` and `DNS Write` on zone `f82ac6762af544d71e8ad5eb3d7fca0c`. Mint requests an expiry 23 hours 59 minutes ahead and rejects any provider result exceeding 24 hours after issue. Its token value exists only in Infisical; the immutable record stores the token ID, canonical returned policies, policy hash, times, and allowed targets without the value.

`./bin/verify --from-clean-seed` also performs read-only production comparison. It reads `DATABASE_PUBLIC_URL` and `CLOUDFLARE_ADMIN_API_TOKEN` from project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment `prod`, and `RAILWAY_API_TOKEN` from project `0943f641-faee-4324-b337-0d50c276e4a9`, environment `prod`. Those credentials are used only for the bounded read-only snapshots; they are not passed into application containers.

## E. Boot and lifecycle

Honest host prerequisites are Docker with Docker Compose, `git`, `curl`, `python3`, `dig`, the Infisical CLI, network access to GitHub/GHCR/Stripe/Infisical/Cloudflare, and an authorized Infisical machine identity at `~/.config/infisical/sysadmin-token`. Node, Playwright, and Chromium are supplied by the pinned runner container and must not be taken from the host.

Before minting, the teardown evidence root must already exist, be owned by the operator, be outside the checkout, and have mode `0700`:

```sh
mkdir -p /Users/max/koskadeux-state/s1656/teardown-evidence
chmod 0700 /Users/max/koskadeux-state/s1656/teardown-evidence
```

Run the lifecycle in this order from the repository root:

```sh
./bin/mint-teardown-token
./bin/up
./bin/verify --from-clean-seed
./bin/reset
./bin/down
```

Use `./bin/down --terminal` instead of the final command only when the disposable Infisical `test-env` must also be destroyed. Finish teardown inside the minted token's 24-hour window.

`./bin/up` performs pure safety assertions, prepares exact detached source clones, verifies the AIM Data tag/digest and Stripe platform Account, builds backend/frontend, records image identities, starts the stack with `--wait`, verifies the pinned runner and all three localhost origins, and then invokes `./bin/seed`. Success is exactly:

```text
up: ai-market-money-path-s1656 is healthy and the three-fixture seed is ready
```

The clean acceptance command intentionally calls guarded `reset`, which calls `up` and therefore reseeds, before running the fixed browser sequence. A successful wrapper prints `verify: AC1-AC12 journey passed; redacted evidence: <run-directory>`; verify that directory and its files rather than relying on the line alone.

## F. Seed contract

`./bin/seed` accepts no arguments, requires a healthy backend, executes the read-only mounted `/s1656/seed.py` in that container, and refuses a database host other than Compose service `postgres`. It consumes only the exact committed manifest-backed secret names and creates or restores exactly these fixtures:

| Fixture | Required initial truth |
| --- | --- |
| `seller-01` | Active, verified, synthetic seller with profile/company, TOTP enabled, one active `auth_user` PartyIdentity, one Stripe test Connect Express account, Stripe-retrieved `payouts_enabled=true`, and effective seller capability `active` with no missing steps |
| `buyer-01` | Active, verified, synthetic buyer with no seller, Connect, listing, ordinary payment-method, setup-attempt, or verification state |
| `seller-02` | Active, verified, synthetic seller with profile/company, TOTP disabled, one active `auth_user` PartyIdentity, and no Connect, payout, listing, ordinary payment-method, setup-attempt, or verification state |

The Connect Express idempotency key is fixed for seller-01. The ordinary pay-in platform Account and seller Connect Account must be separate test-mode objects. The seeder does not set the payout projection until Stripe retrieval reports Express, the S1656 marker, active transfers, and `payouts_enabled=true`; it never creates Connect state for buyer-01 or seller-02. Success is `seed: three-fixture contract passed`.

`reset` removes only exact-label S1656 local targets and volumes, retains `test-env`, calls `up`, reruns migrations, and recreates this exact seed. Never mutate a fixture into another role, patch readiness with SQL, or add an unlisted fixture.

## G. Operate the acceptance journey

`./bin/verify --from-clean-seed` executes one serial flow:

1. Capture a normalized, read-only production snapshot: backend deployment SHA/status and flags, production counts for the synthetic domain, public listing search, public health, Cloudflare tunnel configurations, and the complete paginated DNS record set.
2. Guard-reset, rebuild/start, health-check, and seed the environment.
3. Prove signed-out auth refresh and readiness return 401 and route to login.
4. Prove buyer-01 is redirected to inquiries and receives hidden/404 readiness.
5. Prove seller-02 sees no payment control and receives the indistinguishable 404 readiness.
6. Sign into AIM Data as seller-01, import the committed synthetic CSV, register/publish exactly one listing, record but never visit the returned production `marketplace_url`, and render `http://localhost:13000/listings/<listing_id>` against the local API.
7. Prove no card control before the quote, both acknowledgements, and explicit paid-start action. Only a `setup_required` result exposes `http://localhost:13000/dashboard/data-verification/payment-method`.
8. Sign into the local frontend as seller-01, reauthenticate, and complete the Stripe-hosted `mode=setup` page with Stripe test data entered only on Stripe's page.
9. Prove Stripe test endpoint `we_1UBctVRx8FzPjYyVDIFWEFMT` is enabled for the exact S1656 URL and `checkout.session.completed`, provider delivery succeeds with `livemode=false`, and the backend persists one completed event row.
10. Ask Stripe to redeliver that same event. Prove one event row remains, the duplicate log increments, and neither the ordinary identity nor finalization audit changes.
11. Prove webhook-first and a separate freshly reauthenticated return-first setup converge on the same ordinary customer identity, readiness is `ready`, and the seller Connect identity is unchanged.
12. Return to AIM Data, start paid verification, wait for the signed scan/report lifecycle and manual-capture epoch, prove the final PaymentIntent and charge are test-mode and captured, and publish the findings.
13. Capture the same normalized production snapshot again and require structural equality after volatile fields are removed.

The runner allows navigation only to the three localhost origins and Stripe-hosted test pages. Any request to `host.docker.internal`, a production ai.market frontend/API, or another origin fails the journey.

## H. Evidence and redaction

Evidence is independent only when the referenced files exist and can be read without trusting command success text.

| Evidence | Exact location | Required contents |
| --- | --- | --- |
| Mint policy | `/Users/max/koskadeux-state/s1656/mint-policy/<token-id>.json` | Mode `0444`; token ID, issue/expiry, complete API-returned policies, SHA-256, exact allowed targets; no token value |
| Acceptance | `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/` | Mode `0700` directory containing `production-before.json`, `browser-evidence.json`, `production-after.json`, and `summary.json`, each mode `0400` |
| Teardown | `/Users/max/koskadeux-state/s1656/teardown-evidence/<UTC-run-stamp>/` | Mode `0700` directory containing provider responses/statuses, tunnel/DNS absence proofs, token read/revocation/post-revocation proof, `authoritative-dns-absence.txt`, and `summary.json`; terminal runs also contain Infisical delete/absence proof |
| Runtime identity | `.runtime/aim-data-image-digest.json`, `.runtime/image-digests.json` | Exact source SHA and image-digest bindings; supporting identity only |

The acceptance summary must say `acceptance: passed`, `from_clean_seed: true`, and carry the three exact source SHAs. The teardown summary must say route, DNS, authoritative DNS, and token revocation are true; `infisical_test_env_absent` is true only for `down --terminal`.

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
| `seller-01 effective seller capability is not active` with non-empty exact `missing_steps` | Seeded TOTP/profile/party/Connect payout truth is incomplete | Do not patch the database or payout projection. Rerun the guarded clean seed; if it repeats, preserve the resolver output and Stripe test evidence for the backend owner | `./bin/verify --from-clean-seed`; `/Users/max/koskadeux-state/s1656/acceptance-evidence/<UTC-run-stamp>/browser-evidence.json` |
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

## J. Reset and teardown

`./bin/reset` is local-only. It checks the Compose project name and every matching container/network/volume ownership label, removes those local targets with volumes, retains Infisical `test-env`, and executes `./bin/up`; `up` migrates and seeds the exact three fixtures. Reset makes no Cloudflare call and never destroys the stable test-env-only application secrets.

`./bin/down` validates the exact project and Cloudflare identifiers, mode-0444 mint record, token identity, expiry, complete policy document, policy hash, permissions/resources, tunnel configuration, route, and DNS record before mutation. With an active narrow token it removes only the S1656 route and DNS record, proves both absent through Cloudflare control-plane reads and authoritative A/AAAA/CNAME queries, revokes the narrow token through the admin lifecycle authority, and proves inactive/not-found state. It then writes a new immutable evidence run.

If the narrow token is already inactive or missing, the admin authority may only read the exact tunnel configuration and hostname query to prove both targets already absent. It cannot repair them. If either remains or absence is ambiguous, `down` refuses and directs the operator to mint a fresh narrow token; only that token may mutate the route or record.

Plain `./bin/down` retains `test-env`. `./bin/down --terminal` additionally looks up the single exact Infisical environment, deletes it, rereads the workspace, and proves the slug absent. Stripe may retain test-mode objects; retained objects remain test-only and S1656-tagged and must never be described as deleted. A local teardown, token revocation, or `test-env` deletion does not imply provider-object deletion.

If the 24-hour window expires before teardown, run `./bin/mint-teardown-token`. Use `--replace` only for an existing unexpired current record; it admin-revokes and proves the old token before archiving its record. Never delete an ambiguous Docker object, manually edit policy evidence, reuse the connector token for management, or use the admin token for route/DNS mutation.

## K. Maintenance and change control

Vulcan owns this operator page. Product owners own the pinned backend, frontend, and AIM Data code; the environment repository owns lifecycle, seed, runner, and evidence behavior. Refresh this page when any pinned source SHA, image digest, port/origin, Compose topology, fixture contract, secret name, token permission, provider identifier, lifecycle command, evidence schema/path, browser version, or failure signature changes, and after any incident or accepted Council mandate.

Every behavioral change requires a newly pinned environment commit, focused tests, current Council review under the active roster, and a fresh external acceptance run. A tag, merge, unit suite, Compose health, or tunnel health alone is not approval. Never reuse reviewer votes from another SHA. Keep the S1656 scope frozen: no S1590 spec edit, production feature-default change, runbook-tooling change, alternate tunnel/listener, additional fixture, or adjacent improvement belongs here.

To roll back an environment candidate, stop using its SHA and perform guarded teardown with its own pinned lifecycle before reverting Git. Preserve its redacted evidence and exact identities. Do not roll production back, because this environment makes no production application deployment; the temporary route and DNS record must instead be proven absent. Any required file outside the approved chunk manifest or any new external/production mutation requires a specification amendment before implementation.
