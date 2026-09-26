---
title: AIM Data gateway — operations
owner: vulcan
last_verified: '2026-09-26'
aliases: [aim-gateway, AIM Data gateway, gateway canary, egress canary, gw-canary, gateway-signer, gateway signer, gateway KMS keys]
error_signatures: [receipt_sequence_mismatch, order_not_deliverable, door_check_stale, Cloudflare GraphQL error, Cloudflare zone unavailable, Cloudflare DNS analytics unavailable, invalid canary label, signer_unavailable, KMS credentials are unconfigured, KMS credentials are invalid, signer_key_version_mismatch, gateway_unavailable, DATABASE_URL or AUTHOR_DISPATCH_DATABASE_URL is required for migrations]
---

# AIM Data gateway — operations

The AIM Data gateway is the small open-source Go service that sellers run with Docker to list and serve files from their own infrastructure. It replaces legacy AIM Data (`aim-data.md`), which is frozen. Design authority: `specs/BQ-AIM-DATA-GATEWAY-S1741-GATE1.md` and `specs/BQ-AIM-DATA-GATEWAY-S1741-GATE2.md`. Build record: Living State `build:bq-aim-data-gateway-rebuild-s1741`.

This page covers what is live today: the repository and release, the egress canary, the `gateway-signer` service with its KMS keys, the door-check worker, and the backend's gateway settings. The feature flag `AIM_GATEWAY_ENABLED` is **on** in production since 2026-09-26 03:05 CEST (S1752; Max: no seller used AIM Data, so turn it on). It is a Railway-only variable on `ai-market-backend` (not in Infisical; see `infisical-secrets.md`), and the workers read it by reference. To turn the gateway off, set it to `false` on the backend and redeploy.

## Repository and release

- Repo: `aidotmarket/aim-data-gateway` (public), checkout `/Users/max/Projects/ai-market/aim-data-gateway` (fetch and read `origin/main`; the local `main` branch there can be stale).
- Image: `ghcr.io/aidotmarket/aim-gateway`, published by `.github/workflows/release.yml` on a `v*` tag. The workflow builds twice and compares digests, pushes, checks an anonymous pull, signs with cosign keyless and attaches SBOM and provenance. The binary version comes from the tag.
- Current release: `v0.1.1`. `v0.1.0` is a superseded prerelease (it reported `0.1.0-dev`).

## Egress canary

The gateway checks that the seller's deny-all egress is really in place (GATE2 §6.7). Every hour and on every reconnect it resolves `<16 hex>.gw-canary.ai.market` and opens TCP to `egress-canary.ai.market:443`. Both must fail. It reports the result in a signed `canary_result`.

### DNS records (Cloudflare zone ai.market, zone id `f82ac6762af544d71e8ad5eb3d7fca0c`)

| Name | Type | Content | Proxied |
| --- | --- | --- | --- |
| `*.gw-canary.ai.market` | A | `192.0.2.1` | yes |
| `egress-canary.ai.market` | A | `192.0.2.1` | yes |

The origin `192.0.2.1` is deliberately unroutable (TEST-NET-1). Proxying makes Cloudflare answer every label with its edge addresses and accept TCP on 443, so any gateway with open egress sees an answer and a connection. Do not unproxy these records or point them at a real origin.

### Server-side check (backend)

- Code: `app/services/aim_gateway_canary_cf.py` (adapter) and `_correlate_canary_logs()` in `app/tasks/aim_gateway_door.py`. The adapter is installed only when all three settings are set: `GATEWAY_CANARY_CF_API_TOKEN`, `GATEWAY_CANARY_CF_ZONE_ID` (`f82ac6762af544d71e8ad5eb3d7fca0c`) and `GATEWAY_CANARY_ZONE` (`gw-canary.ai.market`). Without it, every gateway stays `unknown` and cannot publish.
- Source: Cloudflare GraphQL `dnsAnalyticsAdaptiveGroups`, filtered by `queryName_in`. The worker waits 3 minutes after a result arrives (analytics lag) and queries from 5 minutes before receipt up to the time of the query.
- **Sampling (Amendment C, Max decision dde536b1):** Cloudflare keeps 1 in 10 DNS queries (`sampleInterval` 10). A hit means `open`. A miss counts as "no server-side hit", not as proof. The expected detection rate for a gateway that lies is about 10% per hourly canary, about 92% within 24 hours.
- Token: Infisical project `ai-market-backend`, env `prod`, key `GATEWAY_CANARY_CF_API_TOKEN` (requested from Max on 2026-09-25; until it exists, the general `CLOUDFLARE_API_TOKEN` in the same project, which has Analytics Read, was used for verification). Scope: Zone → Analytics → Read on ai.market only. Only a human creates or rotates this token, in the Cloudflare dashboard; agents never mint or copy it.

### Verify (headless, on Titan-1)

The sysadmin Infisical token lives at `~/.config/infisical/sysadmin-token`. Never print a token.

```bash
export PATH=/opt/homebrew/bin:$PATH
JWT=$(tr -d '\r\n' < ~/.config/infisical/sysadmin-token)
CFT=$(infisical secrets get GATEWAY_CANARY_CF_API_TOKEN --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c \
  --env prod --domain https://secrets.ai.market --token "$JWT" --plain --silent | tr -d '\r\n')
L=$(openssl rand -hex 8); dig +short @1.1.1.1 $L.gw-canary.ai.market   # must answer (proxied)
# analytics for the zone, last 30 min: expect avg.sampleInterval 10
S=$(date -u -v-30M +%Y-%m-%dT%H:%M:%SZ); U=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -s https://api.cloudflare.com/client/v4/graphql -H "Authorization: Bearer $CFT" -H 'Content-Type: application/json' \
  -d '{"query":"{viewer{zones(filter:{zoneTag:\"f82ac6762af544d71e8ad5eb3d7fca0c\"}){dnsAnalyticsAdaptiveGroups(limit:20,filter:{datetime_geq:\"'$S'\",datetime_leq:\"'$U'\",queryName_like:\"%gw-canary.ai.market\"}){count avg{sampleInterval} dimensions{queryName}}}}}"}'
```

Because of sampling, a single fresh label is often missing. To prove the pipeline works, resolve about 20 fresh labels and expect a few to show up within a few minutes (S1751: 4 of 20 after 6 minutes).

## Signing: gateway-signer and KMS keys

Every permission and every listing-control message the gateway accepts is an Ed25519 JWT signed by Google Cloud KMS. Only the private Railway service `gateway-signer` holds KMS credentials; the backend API asks it to sign over Railway's private network with a bearer token and never holds the KMS credential itself.

### KMS (GCP project `aimarket-prod`)

- Keyring `projects/aimarket-prod/locations/us-central1/keyRings/ai-market-gateway`.
- Keys `gateway-permission` and `gateway-listing`, both `EC_SIGN_ED25519`, protection `SOFTWARE`, version 1.
- KIDs and public keys (base64url raw Ed25519): `gateway-permission-v1` = `IEcnEsLqaai5sL6cJVTa-DRysB2CFcljfrM6iffcBYg`; `gateway-listing-v1` = `xsvG105nguYBmkzUMVucerYBMA0tNbXhO9D5A8_IU08`.
- Service account `gateway-signer@aimarket-prod.iam.gserviceaccount.com` has `cloudkms.signerVerifier` and `cloudkms.viewer` on those two keys only. Exactly one key exists for it; its JSON is the Railway variable `GATEWAY_SIGNER_GCP_CREDENTIALS_JSON` on `gateway-signer` only (set by Max). Only a human creates or rotates that key.
- Project audit config logs `cloudkms` DATA_READ and DATA_WRITE, so every `AsymmetricSign` appears in Cloud Audit Logs with the service-account principal.

### Service `gateway-signer` (Railway project ai-market, production)

- Code: `services/gateway_signer/` in `aidotmarket/ai-market-backend` (FastAPI, `POST /sign_permission_key`, `POST /sign_listing_key`, unauthenticated `GET /health`). It builds one KMS client from `GATEWAY_SIGNER_GCP_CREDENTIALS_JSON` and fails closed (503 `signer_unavailable`) with no fallback to Application Default Credentials.
- Service id `dcee2123-6d23-450d-996e-d02c515e7ada`. No public domain, one replica, health check `/health`, private address `gateway-signer.railway.internal:8080`.
- Variables: `GATEWAY_SIGNER_TOKEN` (reference to the backend's value), `GATEWAY_SIGNER_GCP_CREDENTIALS_JSON`, `GATEWAY_KMS_PROJECT/LOCATION/KEYRING`, `GATEWAY_PERMISSION_KEY` and `GATEWAY_LISTING_KEY` (full `.../cryptoKeyVersions/1` paths), `GATEWAY_PERMISSION_KID`, `GATEWAY_LISTING_KID`, `PORT=8080`, `RAILWAY_DOCKERFILE_PATH=services/gateway_signer/Dockerfile`.
- **No repository source, on purpose.** Connected to the backend repo, Railway built and ran the backend root `Dockerfile` instead of the service's Dockerfile setting, and the container crash-looped on `DATABASE_URL or AUTHOR_DISPATCH_DATABASE_URL is required for migrations`. This happened twice in S1752 (Dockerfile path with and without a leading slash; deployment `configFile` was null both times, so the root config file is not proven to be the cause; the second run reused an image for the same commit). Railway's API also refuses to set a per-service config file on new services ("Config as Code is deprecated"). Until the move to Railway Infrastructure as Code (`build:bq-railway-cli-v5-upgrade-s1751`, deadline 2026-12-01), deploy by upload.

### Deploy (Koskadeux, after the change is merged to backend main)

```bash
SHA=<merged main sha>; D=/Users/max/worktrees/signer-deploy-$SHA; mkdir -p $D
cd /Users/max/Projects/ai-market/ai-market-backend && git fetch -q origin && git archive $SHA services/gateway_signer | tar -x -C $D
cd $D && zsh -ic "railway up --service gateway-signer --environment production \
  --project e81dd66f-808c-412e-b32c-f6d910f0ac5d --detach -m 'gateway-signer from ai-market-backend@$SHA'"
```

Upload only `services/gateway_signer/` (no root `railway.json`). Keep the service's watch patterns empty: with patterns set, an upload deploy is `SKIPPED`. Merging to main does not redeploy the signer.

### Backend settings (service ai-market-backend)

Non-secret: `GATEWAY_SIGNER_URL=http://gateway-signer.railway.internal:8080`, `GATEWAY_PERMISSION_PUBLIC_KEYS` and `GATEWAY_LISTING_PUBLIC_KEYS` (JSON lists `[{"kid":...,"alg":"EdDSA","key":...}]` with the KIDs above), `GATEWAY_IMAGE=ghcr.io/aidotmarket/aim-gateway@sha256:b02954e7647f2eee5090ce2749eb3c572fb2ad33d44d41a9d32fe164367fb6da` (v0.1.1, anonymous pull verified), `GATEWAY_VERSION=0.1.1`, `GATEWAY_MINIMUM_VERSION=0.1.1`, `GATEWAY_INSTALL_GUIDE_URL=https://github.com/aidotmarket/aim-data-gateway#install-with-compose`, `GATEWAY_CANARY_HOST=egress-canary.ai.market`, `GATEWAY_CANARY_ZONE=gw-canary.ai.market`, `GATEWAY_CANARY_CF_ZONE_ID=f82ac6762af544d71e8ad5eb3d7fca0c`. `GATEWAY_KMS_PROJECT/LOCATION/KEYRING`, `GATEWAY_PERMISSION_KEY` and `GATEWAY_LISTING_KEY` are also set on the backend with the signer's values, but only the signer reads them; they are not needed there. Secrets from Infisical `ai-market-backend/prod`: `GATEWAY_SIGNER_TOKEN`, `GATEWAY_PAIRING_PEPPER`, `GATEWAY_CANARY_CF_API_TOKEN`. The backend must never hold `GATEWAY_SIGNER_GCP_CREDENTIALS_JSON`. The seller's pairing call returns 503 `gateway_unavailable` unless all of `GATEWAY_IMAGE` (must match `ghcr.io/aidotmarket/aim-gateway@sha256:<64 hex>`), `GATEWAY_VERSION`, `GATEWAY_MINIMUM_VERSION`, `GATEWAY_INSTALL_GUIDE_URL`, `GATEWAY_CANARY_HOST`, `GATEWAY_CANARY_ZONE` are set and both public-key lists parse as non-empty JSON lists (`_pairing_configuration()` in `app/api/v1/endpoints/aim_gateway.py`).

### Verify signing

Run a probe inside the signer container (it has the token; `railway ssh` does not forward stdin, so pass the script base64-encoded). Sign an `aim-minver+jwt` listing claim (`op=minimum_version`, `aud`, `iid`, `iat`=now, `version`), then check:

1. HTTP 200 with `token` and `key_version` = the full `gateway-listing/cryptoKeyVersions/1` path.
2. The signature verifies with the `gateway-listing-v1` public key above and fails with the permission key.
3. Cloud Audit Logs show the call: `gcloud logging read 'protoPayload.serviceName="cloudkms.googleapis.com" AND protoPayload.methodName:"AsymmetricSign"' --project aimarket-prod --limit 3`, principal `gateway-signer@aimarket-prod.iam.gserviceaccount.com`.

Proved in S1752 (2026-09-26 02:16 CEST): all three passed. To prove the private-network path, run the same probe from the backend container with `PROBE_URL=http://gateway-signer.railway.internal:8080` once the backend has redeployed with `GATEWAY_SIGNER_TOKEN`.

## Door-check worker: ai-market-gateway-door-worker

Gate 2 requires door checks and canary correlation to run on a dedicated worker, not the ordinary Celery worker. Celery beat (`ai-market-celery-beat`) schedules `aim_gateway.schedule_door_checks` and `aim_gateway.canary_log_reader` every 300 s onto queue `gateway_door_checks`; only this service consumes that queue. `aim_gateway.gateway_refund_watch` stays on the ordinary worker (`scheduled` queue).

- Service id `11316ad6-b28f-4516-b968-0313d02835bd`, repo `aidotmarket/ai-market-backend` branch `main` (auto-deploys with the backend), Dockerfile `/Dockerfile`, no health check, one replica, restart ON_FAILURE, no domain.
- Start command (service setting, not a config file): `sh -c 'python -m app.core.seller_schema_readiness && exec celery -A app.core.celery_app worker --loglevel=info --concurrency=2 --prefetch-multiplier=1 -Q gateway_door_checks'`.
- Variables are references only: `DATABASE_URL`, `REDIS_URL`, `CELERY_VISIBILITY_TIMEOUT`, `ORDER_PAYOUT_DISPATCH_ENABLED` from `ai-market-celery-worker`; `SECRET_KEY`, `DOWNLOAD_TOKEN_SECRET_KEY`, `INTERNAL_API_KEY`, `AIM_GATEWAY_ENABLED`, `GATEWAY_CANARY_CF_API_TOKEN`, `GATEWAY_CANARY_CF_ZONE_ID`, `GATEWAY_CANARY_ZONE`, `GATEWAY_CANARY_HOST`, `GATEWAY_VERSION`, `GATEWAY_MINIMUM_VERSION`, `GATEWAY_PERMISSION_PUBLIC_KEYS`, `GATEWAY_LISTING_PUBLIC_KEYS` from `ai-market-backend`. It holds no signer token, no pairing pepper and no KMS credential.
- Egress: Railway cannot restrict a service's egress to public addresses, so the rule is enforced in code: `_public_addresses()` in `app/tasks/aim_gateway_door.py` refuses any door host that resolves to a non-global address (`address_not_public`), which covers Railway's private network.
- `AIM_GATEWAY_ENABLED` is set explicitly on the backend (`true` since flag-on, 2026-09-26) because the workers read it by reference; a reference to an unset variable renders empty and fails settings validation. The ordinary worker also references it (for refund watch).
- Created S1752 (2026-09-26). Before it existed, beat had queued about 1,100 no-op tasks since the S1741 merge; the worker drained them on first start. With the flag off every task returns immediately.

Check: `railway logs --service ai-market-gateway-door-worker --environment production` shows `aim_gateway.schedule_door_checks` and `aim_gateway.canary_log_reader` received and succeeded every 5 minutes; the Redis list `gateway_door_checks` stays near 0. Also confirm `aim_gateway.door_check` tasks run for paired gateways and their `gateway_door_checks` rows get a real `state` (not left pending).

## Production self-test (synthetic accounts, no money)

Use this to prove the whole seller-to-buyer path in production after a gateway change. It uses the synthetic E2E accounts (`seller-0N`/`buyer-0N@e2e-test.ai.market`, `is_test=true`), whose credentials are in Infisical project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment `staging` (`E2E_SYNTHETIC_SELLER_01_EMAIL`/`_PASSWORD`/`_TOTP`, likewise for buyers). Read them through the Infisical CLI into the process; never print them. Synthetic sellers pass the Stripe payout-readiness check without Stripe Connect (backend #484), so no real money moves.

Helpers used in S1752 live in `/Users/max/worktrees/gwtest` on Titan-1 (not in a repo): `api.py` (login with TOTP, token cache `~/.cache/gwtest/*.tok` mode 0600, `api.py logout-all` at the end), `pair.py` (mints a pairing code as the seller and writes `host/pairing.env` 0600 without printing it), `arm.py arm|disarm <sha>` (E2E window), and `host/` (compose file, squid, Caddy, gateway config, test CSV).

1. **Host.** Create a small GCP VM (S1752: `aim-gw-selftest-s1752`, us-central1-a) with a firewall rule opening 80/443 only. Copy `host/` and run `docker compose up -d`. The compose file mirrors a strict seller install: the gateway (pinned image digest, read-only, non-root, no capabilities) sits on an `internal` network; its only way out is squid allowing `CONNECT api.ai.market:443`; Caddy terminates TLS for the door on an `sslip.io` name for the VM IP. Use static container IPs (squid `172.30.0.10`, gateway `172.30.0.20`) and `dns: [192.0.2.53]` so the gateway has no external DNS; Docker name resolution does not work with that DNS setting. Do not log squid to `/dev/stdout` (it fails to start).
2. **Pair.** Log in as the seller, run `pair.py`, start the gateway. Pairing, inventory and describe should complete within a minute; check the dashboard page `Dashboard → Gateways`.
3. **Wait for egress `closed`.** The canary check needs one correlation cycle (up to ~10 min). Every backend deploy drops gateways to `unknown` for ~5–8 min; publishing and new permissions stop until the next cycle.
4. **List.** On the gateway page choose **Create listing**, offer the file, set a licence and price, publish.
5. **Buy.** Arm the E2E window (`arm.py arm <current backend sha>`; it redeploys the backend; max 15 min; needs Max's GO for the round), then as a buyer who has accepted the site terms `POST /api/v1/checkout/create` with `listing_id`, the listing's `accept_license_sha256`/`accept_covenant_sha256`, `authority_confirmed: true`, `typed_name`, `signer_title`, `business_legal_name`, `jurisdiction`. A synthetic buyer and seller get a mock payment and an `order_id` back with no Stripe session. Then `arm.py disarm <sha>` (redeploys again). The order must be `pending_delivery`, never `delivered`, until receipts arrive (backend #489 enforces this with a database trigger).
6. **Download.** Wait until the gateway has no blockers (each backend deploy leaves it blocked for 5–15 min, see below). As the buyer, `GET /api/v1/orders/{id}/gateway-delivery` returns a permission and a `browser_url` on the seller's door (if the permission expired, `POST .../gateway-delivery/files/{file_id}/permissions`). Never print the URL; it carries the token. Download it, compare SHA-256 with the source file, and check within a few seconds that the order is `delivered`, `revoked` is false, each file's `gateway_order_files.state` is `delivered`, and `gateway_messages` shows the two receipts stored in full, not `{"withheld": ...}`.
7. **Clean up.** As the seller, `DELETE /api/v1/gateways/{id}` with `{"confirm_open_orders": true}` revokes the gateway, unlists its listings and opens a `missing_data` problem on any still-undelivered order. Then `api.py logout-all`, delete `host/pairing.env`, and delete the VM and firewall rule. `gcloud` needs Max's interactive login (`gcp-auth.md`); if it has expired, ask Max to delete them.

S1752 result (2026-09-26): the full path worked in production on the second purchase, order `e21cfc8d-577c-494e-9663-1ebee418054f` (download 201,928 bytes, SHA-256 matched, both receipts applied, order `delivered` at 22:01 UTC). Getting there found and fixed four backend defects: gateway orders were marked `delivered` at payment (#489), permission issuance deadlocked under row locks (#487), a delivery hold blocked the delivery that releases it (#493), and every real receipt was withheld because of a sequence mismatch (#497). The first test order `28875dda` stays undelivered with an open `missing_data` problem: its receipts were withheld before #497, and the gateway treats that delivery as complete. VM `aim-gw-selftest-s1752` and firewall rule `aim-gw-selftest-s1752-web` were left for Max to delete (gcloud login expired).

## When it breaks

- `Cloudflare GraphQL error: ... authentication` or an HTTP 401/403 in the correlation worker log: the token is missing Analytics Read or was revoked. Ask Max to fix the token in Cloudflare and Infisical, then redeploy the backend. While it is broken, every gateway falls to `unknown` (fail-closed), so publishing and new permissions stop.
- `Cloudflare zone unavailable`: `GATEWAY_CANARY_CF_ZONE_ID` is wrong or the token is not scoped to ai.market.
- All gateways `unknown` although they report `closed`: check that all three settings are set on the backend and the worker (Celery beat runs correlation every 300 s).
- A gateway flips to `open` while it reports `closed`: this is the check working. The seller's egress is open. The gateway stays unsupported until its canary is clean.
- Signer returns 503 `signer_unavailable` and its log says `KMS credentials are unconfigured` or `KMS credentials are invalid`: `GATEWAY_SIGNER_GCP_CREDENTIALS_JSON` is missing or malformed on `gateway-signer`. Max replaces it; never paste or print it.
- `signer_key_version_mismatch`: `GATEWAY_PERMISSION_KEY`/`GATEWAY_LISTING_KEY` on the signer do not name the version KMS used. Keep full `cryptoKeyVersions/N` paths.
- KMS `PERMISSION_DENIED` in the signer log: the service account lost `signerVerifier` on that key.
- `gateway-signer` crash-loops with `DATABASE_URL or AUTHOR_DISPATCH_DATABASE_URL is required for migrations`: it was connected to the repo and built the backend image. Remove that deployment, disconnect the source, and deploy by upload (above).
- Gateway blocked with `egress_open` although its canary reports `closed`, or with `door_check_stale`, right after a backend deploy: normal. Both clear when the door worker runs the next canary correlation and door check (every 300 s); expect 5–15 min, longer after two deploys in a row. `egress_open` here means "not yet correlated", not an open egress.
- Backend log `Gateway channel withheld ... detail=invalid_message:receipt_sequence_mismatch`: the backend is older than #497 and requires a receipt's own `seq` to equal the channel sequence. The released gateway numbers receipts separately (its `receipts_outbox`). Withheld receipts are not resent; the affected order needs a problem and a refund or a new purchase.
- `GET .../gateway-delivery` shows `blocked_code: order_not_deliverable` on a `pending_delivery` order whose `revoke_reason` starts `gateway_delivery_required:`: the backend is older than #493. From #493 on, those two system holds allow delivery and are released by complete receipts; a hold with `revoked_by` set or an independent revocation still blocks.
- Redis list `gateway_door_checks` keeps growing: `ai-market-gateway-door-worker` is down or not consuming that queue. Gateways then never get a door result and cannot publish.
