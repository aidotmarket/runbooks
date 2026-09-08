---
title: AIM Data — Sign in with ai.market
owner: vulcan
last_verified: '2026-09-08'
aliases:
- aim data oauth
- sign in with ai.market
- aim_data_desktop_v1
- AIM_DATA_OAUTH_ENABLED
error_signatures:
- client_disabled
- unauthorized_client
- loopback_origin_required
- invalid_request
- invalid_grant
- address already in use
- origin_mismatch
- csrf_failed
- backend_unsupported
- backend_unavailable
---

# AIM Data — Sign in with ai.market

## A. Purpose and audience

Operate and troubleshoot AIM Data account sign-in: customer installation, operator readiness, fallback, revocation and rollback. Source contracts are verified; Gate 4 live proofs remain pending.

**Default state:** ships ON BY DEFAULT in backend, website and customer install (Max directive 2026-09-08, event `a2486ee9`). `AIM_DATA_OAUTH_ENABLED` and website `NEXT_PUBLIC_AIM_DATA_OAUTH_ENABLED` are rollback levers: set to false to switch off. The reserved client is active after migration `s1665_aim_data_oauth_activate`. This supersedes the historical default-off rollout wording in [Gate 2 §§3, 7, 9–10](specs/BQ-AIM-DATA-SIGN-IN-WITH-AI-MARKET-S1659-GATE2.md); migration/deployment verification remains pending in §I.

## B. Contracts

- Public client `aim_data_desktop_v1`; no client secret, provider secret or signing key on the customer host. Authorization code + PKCE **S256**, scope `aim_data.session`; full account-session authority equivalent to password sign-in, not a limited dataset permission or proof of binary identity.
- Callback is exactly `http://127.0.0.1:<published-port>/api/auth/aim-market/callback`. Canonical decimal port 1024–65535; no localhost, IPv6, remote hostname, credentials, extra path, query or fragment. Code exchange must match the original redirect URI, including port.
- Open numeric origin `http://127.0.0.1:<published-port>` exactly as installer output, on the Docker host. `AIM_DATA_PORT` and `AIM_DATA_OAUTH_LOOPBACK_PORT` must match. Mandated proof ports: **8080, 8099, 18081**; these are not an exclusive allowlist.
- Production issuer `https://api.ai.market`; frontend origin `https://ai.market`; `AIM_DATA_OAUTH_TEST_MODE=false`. Website sign-in resumes the same authorization request, shows the account and access disclosure, and requires Continue. Cancel grants no session.
- One uvicorn worker: `WORKERS`, `WEB_CONCURRENCY`, `UVICORN_WORKERS`, `VECTORAIZ_WORKERS` absent or `1`. Attempts live in bounded process memory; restarting expires them. Profiling workers are separate.

## C. Readiness and status

`GET https://api.ai.market/api/v1/oauth/clients/aim_data_desktop_v1/status` is unauthenticated, no-store: HTTP 200 with `client_id`, boolean `enabled`, `protocol_version:1`. `enabled:false` means backend switch off OR reserved row missing/inactive/untrusted (including provisioning ownership mismatch), not necessarily an outage. DB failure returns 503 `temporarily_unavailable`; 404 indicates an older backend. Readiness does not prove browser acceptance.

Local `GET /api/auth/aim-market/bootstrap` returns `enabled`, `reason`, `csrf_nonce`, `loopback_origin`; use the login page status text and keep nonce/cookies out of evidence. `local_disabled` means customer switch off, `client_disabled` means valid upstream disabled status, `backend_unsupported` means old backend or refused issuer configuration, and `backend_unavailable` means malformed/error/timeout response. Start rechecks readiness. The primary button also requires exact browser origin; password/2FA stays available.

## D. Operator procedure

**Verify provisioned identity and active row.** Use the backend checkout and an explicitly supplied, securely loaded `DATABASE_URL` beginning `postgresql://`; no default DB target and no DSN in reports. Production Railway commands must name `-e production -s ai-market-backend` (the local checkout can be linked to a different environment). Use a reachable operator DB URL for local scripts; Railway private DNS need not resolve on the operator host.

```sh
rtk proxy railway deployment list -e production -s ai-market-backend
rtk proxy .venv/bin/python scripts/provision_aim_data_oauth.py --dry-run
```

The CLI verifies exact immutable fields and migration ownership, never adopts a conflicting row. `created` means absent/would create on dry-run, `unchanged` means matching provisioned row; neither alone proves active. `conflict` results exit 2: stop and investigate schema/provenance; do not overwrite it. A narrow DB check is `SELECT client_id,is_active FROM oauth_clients WHERE client_id='aim_data_desktop_v1';`; it complements, not replaces, the trust/provenance check. For authorized repair only, `rtk proxy .venv/bin/python scripts/provision_aim_data_oauth.py --apply` provisions. [`scripts/provision_aim_data_oauth.py`](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/scripts/provision_aim_data_oauth.py#L1-L43) is dry-run by default and `--apply` provisions the reserved row; it has no activation flag. Activation is performed by migration [`s1665_aim_data_oauth_activate`](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/alembic/versions/20260908_001_aim_data_oauth_activate.py#L1-L24). Recheck public status and deployment identity afterward.

**Switch off, backend first:**

```sh
rtk proxy railway variables -e production -s ai-market-backend --set AIM_DATA_OAUTH_ENABLED=false
rtk proxy railway deployment list -e production -s ai-market-backend
```

Wait for the new deployment to succeed and status to report `enabled:false`. The website flag `NEXT_PUBLIC_AIM_DATA_OAUTH_ENABLED` is off when its trimmed, lower-cased value is one of `false`, `0`, `off`; anything else (including unset) is on ([merged predicate](https://github.com/aidotmarket/ai-market-frontend/blob/f03abe1a2055611c71be50928b4e063f855c9dcc/lib/aim-data-continuation.ts#L3-L6)). Set it to `false`, rebuild and redeploy the frontend: this is a build-time flag, so a runtime variable change alone cannot change the compiled UI. Clear the tab's `aim_data_authorization_request` continuation metadata. Backend and AIM Data `AIM_DATA_OAUTH_ENABLED` flags use Pydantic bool parsing. Set `AIM_DATA_OAUTH_ENABLED=false` in the customer Compose `.env`, then run `rtk docker compose -f docker-compose.aim-data.yml up -d --force-recreate app`. This restarts process-local attempts; clear invalidated OAuth tokens/mode through local logout. Do not remove data volumes.

**Invoke shipped `disable_and_revoke(db)` — disable the row and revoke reserved refresh families and pending work:** after backend off and old instances drained, an authorized DB operator runs the following from the merged backend checkout and its installed environment, with the explicitly supplied, reachable production `DATABASE_URL` described above and the required backend settings securely loaded. The imports are shipped: [`SessionLocal`](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/core/database.py#L16-L63) and [`disable_and_revoke`](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/services/aim_data_oauth_service.py#L475-L485). No public bulk-revoke endpoint is shipped. Capture counts only, never token/session row contents.

```sh
rtk proxy .venv/bin/python -c "
import os
assert os.environ.get('DATABASE_URL', '').startswith('postgresql://'), 'explicit PostgreSQL DATABASE_URL required'
from app.core.database import SessionLocal
from app.services.aim_data_oauth_service import disable_and_revoke
with SessionLocal() as db:
    disable_and_revoke(db)
"
```

The helper takes `pg_advisory_xact_lock(1659, 1)`, sets `oauth_clients.is_active=false` for `aim_data_desktop_v1`, locks all reserved grants, revokes their current sessions with `revoke_reason='aim_data_disabled'`, and sets `revoked_at=now()` on all reserved grants (including previously revoked grants). It deletes reserved pending authorization transactions, expires unused reserved authorization codes, and commits. This is distinct from [`revoke_grant`](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/services/aim_data_oauth_service.py#L381-L385), which uses `aim_data_refresh_revoked`.

**Re-enable after this procedure:** restoring flags alone leaves the reserved row inactive. Re-run the activation migration's [`upgrade()` logic](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/alembic/versions/20260908_001_aim_data_oauth_activate.py#L11-L24) in an authorized migration transaction: it calls `provision(bind, apply=True)` and then `activate(bind)`, rejecting conflicts. An already-applied revision is not rerun by a normal Alembic upgrade. Alternatively, provision with the existing `--apply` command and then perform the same trusted [`activate(bind)`](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/aim_data_oauth_provision.py#L22-L61) step in a committed transaction; there is no CLI activation flag. At this merged head, provisioning a missing row creates it active, but provisioning an existing inactive row returns `unchanged` and does not reactivate it. The activation migration's downgrade retains data and explicitly does **not** deactivate the client or switch the feature off. Restore the flags, rebuild/redeploy the website, and recheck trusted active identity and public status; revoked grants remain revoked and require fresh sign-in.

Preserve source website sessions, other clients and additive schema. OAuth refresh rotates its family/session; replay revokes the reserved grant/current session. Default access lifetime is **30 minutes**, refresh **7 days**, subject to session/account policy. Some consumers do not check session revocation: switch-off/revocation is not instant access-token invalidation. Record deployed `ACCESS_TOKEN_EXPIRE_MINUTES` and last possible issuance time; residual access can last that configured lifetime (30m default).

## E. Customer installation

Use the [AIM Data install/release instructions](aim-data.md) and a released image containing this flow and the defaults flip; record its version and digest, not an assumed tag. Install on the computer running your browser. Keep the published port and OAuth loopback port equal in `.env`; use 8080 normally, or an available port such as 8099/18081. Start with `rtk docker compose -f docker-compose.aim-data.yml up -d`, then open the installer's exact `http://127.0.0.1:<published-port>` URL.

Click **Sign in with ai.market**, authenticate on ai.market using your existing method (including Google/GitHub and required 2FA), check the displayed account and disclosure, then Continue. Completion returns through `/login/complete` to credential-free `/datasets`. Cancel requires a fresh start. Authentication and registration are separate: `registration_status:not_ready` is not publish readiness or seller promotion.

Remote-host/browser-on-another-computer use is unsupported: loopback returns to the browser's computer, not the remote Docker host. Use a browser on the install host, or the existing supported password access path if the account has a password. Provider-only accounts must retry later/contact support. Do not expose new network bindings, substitute a remote callback, prescribe a tunnel, force a password, or disable 2FA to bypass this limitation.

### E.1 Trust Channel device registration after sign-in (T-2026-000780, v1.23.2)

From AIM Data v1.23.2 the install registers its Trust Channel device with the sign-in token: `complete_connected_login` calls `ensure_trust_device_registered(crypto, access_token, max_retries=1)` after a successful sign-in or token refresh, and the Trust Channel client starts whenever the keystore passphrase is configured (an internal API key is optional and is not used to authenticate the socket). Credential order: sign-in token, then a configured internal API key, then the token persisted by the last sign-in. A persisted token older than its lifetime is refused once at startup (`Registration auth failed (401)`), which is expected; the next sign-in or refresh registers the device and the client connects on its next reconnect without a restart.

Expected log sequence on a fresh or upgraded provider-only install: `Device keypairs initialized (Ed25519 + X25519)` -> (optional `Registration auth failed (401)` from a stale token) -> after sign-in, `/data/keystore.json` gains `certificate` and `platform_*_public_key` -> `Connecting to Trust Channel: wss://api.ai.market/api/v1/trust/stream` -> `Trust Channel established: <session id>`. Production proof: `trust_sessions` row for the device with `is_active=t` and `subscriptions ["fulfillment","system"]`. First live occurrence 2026-09-08 23:33 UTC, session `1db14cf1-45b6-402d-b023-c0372ea9534e`, max@kisa.cat, v1.23.2 (`sha256:18f22e23…`).

| Literal signature | Meaning / fix |
| --- | --- |
| `Trust Channel device registration is missing` repeating after sign-in | Keystore has no certificate. Check the app log for `Registration auth failed`; sign out and sign in again so a fresh token registers the device. If it persists, verify the image is >= v1.23.2 (`/api/health` version) and that the keystore passphrase is set. |
| `Registration auth failed (401)` once at startup, then `Trust Channel established` after sign-in | Normal on upgrade: the persisted token had expired. No action. |

## F. Password and 2FA fallback

When any OAuth lever is off or the backend is old, the local password form and 2FA challenge remain. Provider-only accounts cannot use password fallback. Website login, local operator key/cookie contracts and other OAuth clients retain their existing behavior.

Keep the corrected customer password adapter: it captures the named upstream refresh cookie after password/2FA and rotation, sends that cookie with configured marketplace Origin on refresh, and rejects missing/null token pairs. OAuth mode refreshes through `/api/v1/oauth/token`; password mode uses `/api/v1/auth/refresh`. Reload uses the saved mode (legacy absent mode means password). Logout/account change clears tokens/mode. Never blindly downgrade to v1.22.10; it predates this correction.

## G. Troubleshooting

## When it breaks

| Literal signature | Meaning / fix |
| --- | --- |
| `client_disabled`, `unauthorized_client` | Reserved authorization/token refusal pairs `error:unauthorized_client` with `error_code:client_disabled`; local start maps disabled state to 409. Check §C, deployed switch and trusted active row. During rollback use fallback; do not register a replacement client. |
| `loopback_origin_required` | Localhost or browser origin differs from configured numeric origin. Open the exact installer URL on its host; align both ports, restart, begin a new attempt. |
| `invalid_request`, `invalid_grant` | Backend refuses malformed/non-loopback authorize URI (`invalid_request`) or invalid/mismatched exchange URI/port/code/verifier (`invalid_grant`). Do not edit callback URLs or replay codes; fix port/configuration and restart sign-in. |
| `address already in use` | Host/Docker bind failure for an occupied published port; runtime wording varies, not an AIM Data OAuth error code. Identify the listener; choose a free published port and matching OAuth port without terminating another owner's service. |
| `origin_mismatch`, `csrf_failed` | Foreign Origin gets 403: local bootstrap/start uses `origin_mismatch`, completion uses `csrf_failed`; website consent/metadata requires its configured Origin. Restart from exact numeric local origin; verify configured website origin. Do not loosen CORS or forward arbitrary Origin. |
| `backend_unsupported`, `backend_unavailable` | Check backend version/status and canonical issuer; 404 differs from timeout/5xx/malformed status. Retry after service recovery or use password/2FA where available. |

## H. Retained storage risk

Browser localStorage retains account tokens/auth mode; the local serial file retains the marketplace access token and install state. `app/services/serial_store.py` writes `/data/serial.json` atomically with mode **0600**. Owner-only permissions are not encryption: browser script compromise, host/file access or copied backups can expose credentials. No provider secret or PKCE verifier belongs in persistent storage. Avoid callback URL/query screenshots, request bodies, cookies and credential-bearing logs/exports. Pending local attempts expire after 600s; completed credentials have a 60s one-use window, with periodic cleanup. Check permissions without printing file contents.

**Observability:** with the feature on, `OAuthLogFilter` suppresses uvicorn access-log lines containing `/oauth/authorize` or `/oauth/token`. This also covers existing M2M `client_secret_post` traffic. Source: merged backend `8e71de70f497d9f2000c4bae45f9cf4d3bc23567`, [app/services/aim_data_oauth_service.py:488–498](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/services/aim_data_oauth_service.py#L488-L498).

## I. Source and proof links

Merged source pins below include the defaults-on flip and folded nits; they prove source behavior, not deployment or live acceptance. Backend provisioning helper is **root `aim_data_oauth_provision.py`**, not `app/services/aim_data_oauth_provision.py`.

- Backend `8e71de70f497d9f2000c4bae45f9cf4d3bc23567`: [app/api/v1/endpoints/oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/api/v1/endpoints/oauth.py), [app/api/v1/endpoints/oauth_clients.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/api/v1/endpoints/oauth_clients.py), [app/services/aim_data_oauth_service.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/services/aim_data_oauth_service.py), [aim_data_oauth_provision.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/aim_data_oauth_provision.py), [scripts/provision_aim_data_oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/scripts/provision_aim_data_oauth.py), [alembic/versions/20260907_001_aim_data_oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/alembic/versions/20260907_001_aim_data_oauth.py), [app/core/config.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/core/config.py).
- Website `f03abe1a2055611c71be50928b4e063f855c9dcc`: [lib/aim-data-continuation.ts](https://github.com/aidotmarket/ai-market-frontend/blob/f03abe1a2055611c71be50928b4e063f855c9dcc/lib/aim-data-continuation.ts), [app/oauth/authorize/page.tsx](https://github.com/aidotmarket/ai-market-frontend/blob/f03abe1a2055611c71be50928b4e063f855c9dcc/app/oauth/authorize/page.tsx), [app/login/LoginForm.tsx](https://github.com/aidotmarket/ai-market-frontend/blob/f03abe1a2055611c71be50928b4e063f855c9dcc/app/login/LoginForm.tsx).
- Customer `99ade5f5399c23045e4b927063bc49c6aaa178cf`: [app/config.py](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/app/config.py), [app/routers/aim_market_oauth.py](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/app/routers/aim_market_oauth.py), [app/services/aim_market_oauth.py](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/app/services/aim_market_oauth.py), [docker-compose.aim-data.yml](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/docker-compose.aim-data.yml), [deploy/entrypoint.sh](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/deploy/entrypoint.sh), [installers/aim-data/install.sh](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/installers/aim-data/install.sh), [frontend/src/pages/LoginPage.tsx](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/frontend/src/pages/LoginPage.tsx), [frontend/src/lib/aimMarketAuth.ts](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/frontend/src/lib/aimMarketAuth.ts), [app/services/connected_login.py](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/app/services/connected_login.py), [app/services/serial_store.py](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/app/services/serial_store.py).

| Gate 3 reference / default-state change | Evidence |
| --- | --- |
| A | [Backend PR #344](https://github.com/aidotmarket/ai-market-backend/pull/344) (includes prior provisioning relocation). |
| B | [Frontend PR #59](https://github.com/aidotmarket/ai-market-frontend/pull/59). |
| C | [AIM Data PR #49](https://github.com/aidotmarket/aim-data/pull/49). |
| Defaults flip | [Backend PR #346](https://github.com/aidotmarket/ai-market-backend/pull/346), [frontend PR #60](https://github.com/aidotmarket/ai-market-frontend/pull/60), [AIM Data PR #50](https://github.com/aidotmarket/aim-data/pull/50); merged backend [`8e71de70`](https://github.com/aidotmarket/ai-market-backend/commit/8e71de70f497d9f2000c4bae45f9cf4d3bc23567), frontend [`f03abe1a`](https://github.com/aidotmarket/ai-market-frontend/commit/f03abe1a2055611c71be50928b4e063f855c9dcc), AIM Data [`edea2500`](https://github.com/aidotmarket/aim-data/commit/edea2500ff3beba600c738cb9c3ececcfb4f1e40). |
| T-2026-000780 device registration with the sign-in token | [AIM Data PR #56](https://github.com/aidotmarket/aim-data/pull/56) (Council unanimous R2: CC, GLM, DeepSeek), release [PR #57](https://github.com/aidotmarket/aim-data/pull/57), tag `aim-data-v1.23.2` -> `60b6eeea7643a2dd823045a1313cd7d11f92f9c3`, image `v1.23.2@sha256:18f22e2383599aa882064c902f4c07dcd6a9b9f9bac07d27a1e8316e588a1fe1`. |
| AIM Data nits and release | [PR #51](https://github.com/aidotmarket/aim-data/pull/51), merged [`99ade5f`](https://github.com/aidotmarket/aim-data/commit/99ade5f5399c23045e4b927063bc49c6aaa178cf); tag [`aim-data-v1.23.0-rc.1`](https://github.com/aidotmarket/aim-data/releases/tag/aim-data-v1.23.0-rc.1) points to that merge. Source/release references are not deployment receipts. |

Defaults-flip source pins (merged, with nits folded): backend `8e71de70f497d9f2000c4bae45f9cf4d3bc23567` [aim_data_oauth_provision.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/aim_data_oauth_provision.py) [scripts/provision_aim_data_oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/scripts/provision_aim_data_oauth.py) [alembic/versions/20260908_001_aim_data_oauth_activate.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/alembic/versions/20260908_001_aim_data_oauth_activate.py) [app/core/config.py](https://github.com/aidotmarket/ai-market-backend/blob/8e71de70f497d9f2000c4bae45f9cf4d3bc23567/app/core/config.py) ; frontend [default predicate](https://github.com/aidotmarket/ai-market-frontend/blob/f03abe1a2055611c71be50928b4e063f855c9dcc/lib/aim-data-continuation.ts); customer [settings](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/app/config.py), [Compose](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/docker-compose.aim-data.yml), [installer](https://github.com/aidotmarket/aim-data/blob/99ade5f5399c23045e4b927063bc49c6aaa178cf/installers/aim-data/install.sh).

| Gate 4 live proof | Status |
| --- | --- |
| Deployed A/B identities, active `s1665_aim_data_oauth_activate` seed, C release version/digest and effective defaults | PASS 2026-09-08 (backend a7541416 then 1c96b257, frontend 943429b5, image v1.23.0 `sha256:281e5a6a…` at proof time, now v1.23.1 `sha256:b783f7cb…`; status route `enabled:true`). Evidence: Titan-1 `/Users/max/koskadeux-state/s1665/gate4/EVIDENCE.md`. |
| AC1/AC2 provider-only fresh install; AC3 2FA, confirmation/Cancel and identity/registration | AC1 PASS 2026-09-08 12:45 UTC (Google-only max@kisa.cat, fresh install port 8080; grant + reserved session in production, local user row matched, stores 0600). AC2 GitHub-only carried by Max decision a4ea061c (no GitHub-only identity). AC3 pending. Evidence: `/Users/max/koskadeux-state/s1665/gate4/EVIDENCE.md`. |
| AC4 fallback fresh/upgrade/reload/rotation; local operator key/cookie parity | pending |
| AC6 Docker/browser chain at 8080/8099/18081; wrong/occupied port and remote/origin refusal | pending |
| AC9 refresh race/replay/revocation and lifetime bound; AC14 disable/revoke/rollback and website/other-client continuity | pending |
| AC11 owner-approved no-payment fresh-install charter: login, profile/PII, metadata approval, publish and readiness | carried by Max decision a4ea061c (harness charter deferred); D2 code merged e2e-harness 6be0e0cf |
| AC13 image/layer/bundle/config/log/export/URL scans, TTL cleanup and 0600 store | pending |

Unit tests and Gate 3 references do not close these rows. AC11 requires the authorized D2 entry adaptation, synthetic provider lease and normal authorized Chrome/operator evidence; no paid/Stripe transaction is part of that proof.

## J. Rollback matrix

| Chunk | Action / retained behavior |
| --- | --- |
| A backend | Flag false first; revoke reserved refresh families/current sessions and pending work (§D). Retain additive schema, other clients and website sessions; no destructive downgrade or secret rotation. Record residual access bound. |
| B website | Build flag false, rebuild/redeploy (or previous reviewed frontend after A off); clear continuation metadata. Existing website login stays. |
| C customer | Local flag false, recreate app/expire attempts and clear invalidated OAuth tokens/mode. Retain corrected password/2FA adapter and volumes; provider-only outage guidance applies. |
| D docs/runner/notes | Revert only erroneous content/charter/runner/notes; retain historical proof and outage guidance. No account resets, volume deletion or listing reversal. |

**Residual access after env-only rollback (Council defaults-on review, DeepSeek, 2026-09-08):**

- Pending authorization transactions live for up to **600 s**. `GET /api/v1/oauth/authorize/requests/{request_id}` still serves metadata (`request`, `client_name`, `scope`, `expires_at`, `csrf_nonce`) for a valid transaction with its binding cookie because `metadata()` is not flag-gated. No authorization code or token can be minted while the backend flag is off. Run the `disable_and_revoke` procedure in §D to expire pending transactions immediately.
- Already-issued access tokens remain valid until expiry (**30 minutes** by default; record the configured lifetime as in §D). Refresh is refused once the backend flag is off.

## K. Open items

- **POST-P0-REMOTE — OPEN:** AC12 remote-host/tunnel evidence, owned by this BQ evidence owner; not a P0 gate and no claimed tunnel support.
- **POST-P0-PAID — OPEN:** paid journey evidence owned by S1656; not a P0 gate or included in AC11. No payment certification in this runbook.
