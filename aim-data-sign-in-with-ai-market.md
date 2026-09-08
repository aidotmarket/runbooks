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

The CLI verifies exact immutable fields and migration ownership, never adopts a conflicting row. `created` means absent/would create on dry-run, `unchanged` means matching provisioned row; neither alone proves active. `conflict` results exit 2: stop and investigate schema/provenance; do not overwrite it. A narrow DB check is `SELECT client_id,is_active FROM oauth_clients WHERE client_id='aim_data_desktop_v1';`; it complements, not replaces, the trust/provenance check. For authorized repair only, `rtk proxy .venv/bin/python scripts/provision_aim_data_oauth.py --apply` provisions. The CLI remains dry-run/`--apply` provisioning only; activation is performed by migration `s1665_aim_data_oauth_activate`, with no manual CLI activation step. Recheck public status and deployment identity afterward.

**Switch off, backend first:**

```sh
rtk proxy railway variables -e production -s ai-market-backend --set AIM_DATA_OAUTH_ENABLED=false
rtk proxy railway deployment list -e production -s ai-market-backend
```

Wait for the new deployment to succeed and status to report `enabled:false`. Set website build variable `NEXT_PUBLIC_AIM_DATA_OAUTH_ENABLED` to the literal `false` (case-insensitive after the fold; `0`/`off` are also accepted), rebuild and redeploy the frontend; a runtime variable change alone cannot change the compiled UI. Clear the tab's `aim_data_authorization_request` continuation metadata. Backend and AIM Data `AIM_DATA_OAUTH_ENABLED` flags use Pydantic bool parsing. Set `AIM_DATA_OAUTH_ENABLED=false` in the customer Compose `.env`, then run `rtk docker compose -f docker-compose.aim-data.yml up -d --force-recreate app`. This restarts process-local attempts; clear invalidated OAuth tokens/mode through local logout. Do not remove data volumes.

**`disable_and_revoke` — revoke reserved refresh families and pending work:** after backend off and old instances drained, an authorized DB operator runs this transaction against the confirmed production DB. It mirrors `revoke_grant` for only the reserved client; no public bulk-revoke endpoint is shipped. Capture counts only, never token/session row contents.

```sql
BEGIN;
SELECT count(*) AS locked_grants FROM (SELECT id FROM aim_data_oauth_grants
 WHERE client_id='aim_data_desktop_v1' FOR UPDATE) AS reserved;
UPDATE auth_sessions SET revoked_at=now(), revoke_reason='aim_data_refresh_revoked'
 WHERE session_id IN (SELECT current_session_id FROM aim_data_oauth_grants
                      WHERE client_id='aim_data_desktop_v1');
UPDATE aim_data_oauth_grants SET revoked_at=now()
 WHERE client_id='aim_data_desktop_v1' AND revoked_at IS NULL;
DELETE FROM aim_data_authorization_transactions WHERE client_id='aim_data_desktop_v1';
UPDATE oauth_authorization_codes SET expires_at=now()
 WHERE client_id='aim_data_desktop_v1' AND used_at IS NULL;
COMMIT;
```

Preserve source website sessions, other clients and additive schema. OAuth refresh rotates its family/session; replay revokes the reserved grant/current session. Default access lifetime is **30 minutes**, refresh **7 days**, subject to session/account policy. Some consumers do not check session revocation: switch-off/revocation is not instant access-token invalidation. Record deployed `ACCESS_TOKEN_EXPIRE_MINUTES` and last possible issuance time; residual access can last that configured lifetime (30m default).

## E. Customer installation

Use the [AIM Data install/release instructions](aim-data.md) and a released image containing this flow and the defaults flip; record its version and digest, not an assumed tag. Install on the computer running your browser. Keep the published port and OAuth loopback port equal in `.env`; use 8080 normally, or an available port such as 8099/18081. Start with `rtk docker compose -f docker-compose.aim-data.yml up -d`, then open the installer's exact `http://127.0.0.1:<published-port>` URL.

Click **Sign in with ai.market**, authenticate on ai.market using your existing method (including Google/GitHub and required 2FA), check the displayed account and disclosure, then Continue. Completion returns through `/login/complete` to credential-free `/datasets`. Cancel requires a fresh start. Authentication and registration are separate: `registration_status:not_ready` is not publish readiness or seller promotion.

Remote-host/browser-on-another-computer use is unsupported: loopback returns to the browser's computer, not the remote Docker host. Use a browser on the install host, or the existing supported password access path if the account has a password. Provider-only accounts must retry later/contact support. Do not expose new network bindings, substitute a remote callback, prescribe a tunnel, force a password, or disable 2FA to bypass this limitation.

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

**Observability:** with the feature on, `OAuthLogFilter` suppresses uvicorn access-log lines containing `/oauth/authorize` or `/oauth/token`. This also covers existing M2M `client_secret_post` traffic. Source: backend candidate `5fe6486e524beda59577100025e4b7e942b29982`, [app/services/aim_data_oauth_service.py:488–498](https://github.com/aidotmarket/ai-market-backend/blob/5fe6486e524beda59577100025e4b7e942b29982/app/services/aim_data_oauth_service.py#L488-L498).

## I. Source and proof links

Historical merged contract pins below predate the default-on directive; they prove paths/behavior, not the new defaults or live acceptance. Backend provisioning helper is **root `aim_data_oauth_provision.py`**, not `app/services/aim_data_oauth_provision.py`.

- Backend `07caaa802e5c3048dacd15c07517b8bbea38939a`: [app/api/v1/endpoints/oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/07caaa802e5c3048dacd15c07517b8bbea38939a/app/api/v1/endpoints/oauth.py), [app/api/v1/endpoints/oauth_clients.py](https://github.com/aidotmarket/ai-market-backend/blob/07caaa802e5c3048dacd15c07517b8bbea38939a/app/api/v1/endpoints/oauth_clients.py), [app/services/aim_data_oauth_service.py](https://github.com/aidotmarket/ai-market-backend/blob/07caaa802e5c3048dacd15c07517b8bbea38939a/app/services/aim_data_oauth_service.py), [aim_data_oauth_provision.py](https://github.com/aidotmarket/ai-market-backend/blob/07caaa802e5c3048dacd15c07517b8bbea38939a/aim_data_oauth_provision.py), [scripts/provision_aim_data_oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/07caaa802e5c3048dacd15c07517b8bbea38939a/scripts/provision_aim_data_oauth.py), [alembic/versions/20260907_001_aim_data_oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/07caaa802e5c3048dacd15c07517b8bbea38939a/alembic/versions/20260907_001_aim_data_oauth.py), [app/core/config.py](https://github.com/aidotmarket/ai-market-backend/blob/07caaa802e5c3048dacd15c07517b8bbea38939a/app/core/config.py).
- Website `4a5b038ad4334515b58dd39cb9f9cec558328f9b`: [lib/aim-data-continuation.ts](https://github.com/aidotmarket/ai-market-frontend/blob/4a5b038ad4334515b58dd39cb9f9cec558328f9b/lib/aim-data-continuation.ts), [app/oauth/authorize/page.tsx](https://github.com/aidotmarket/ai-market-frontend/blob/4a5b038ad4334515b58dd39cb9f9cec558328f9b/app/oauth/authorize/page.tsx), [app/login/LoginForm.tsx](https://github.com/aidotmarket/ai-market-frontend/blob/4a5b038ad4334515b58dd39cb9f9cec558328f9b/app/login/LoginForm.tsx).
- Customer `d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb`: [app/config.py](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/app/config.py), [app/routers/aim_market_oauth.py](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/app/routers/aim_market_oauth.py), [app/services/aim_market_oauth.py](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/app/services/aim_market_oauth.py), [docker-compose.aim-data.yml](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/docker-compose.aim-data.yml), [deploy/entrypoint.sh](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/deploy/entrypoint.sh), [installers/aim-data/install.sh](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/installers/aim-data/install.sh), [frontend/src/pages/LoginPage.tsx](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/frontend/src/pages/LoginPage.tsx), [frontend/src/lib/aimMarketAuth.ts](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/frontend/src/lib/aimMarketAuth.ts), [app/services/connected_login.py](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/app/services/connected_login.py), [app/services/serial_store.py](https://github.com/aidotmarket/aim-data/blob/d8fae2c5bfae38cde18307fd6e1deaf3951e1dcb/app/services/serial_store.py).

| Gate 3 reference / default-state change | Evidence |
| --- | --- |
| A | [Backend PR #344](https://github.com/aidotmarket/ai-market-backend/pull/344) (includes prior provisioning relocation). |
| B | [Frontend PR #59](https://github.com/aidotmarket/ai-market-frontend/pull/59). |
| C | [AIM Data PR #49](https://github.com/aidotmarket/aim-data/pull/49). |
| Defaults flip | [Backend PR #346](https://github.com/aidotmarket/ai-market-backend/pull/346), [frontend PR #60](https://github.com/aidotmarket/ai-market-frontend/pull/60), [AIM Data PR #50](https://github.com/aidotmarket/aim-data/pull/50); open at source verification, not deployment receipts. |

Defaults-flip source pins (reviewed here as open PR candidates): backend `5fe6486e524beda59577100025e4b7e942b29982` [aim_data_oauth_provision.py](https://github.com/aidotmarket/ai-market-backend/blob/5fe6486e524beda59577100025e4b7e942b29982/aim_data_oauth_provision.py) [scripts/provision_aim_data_oauth.py](https://github.com/aidotmarket/ai-market-backend/blob/5fe6486e524beda59577100025e4b7e942b29982/scripts/provision_aim_data_oauth.py) [alembic/versions/20260908_001_aim_data_oauth_activate.py](https://github.com/aidotmarket/ai-market-backend/blob/5fe6486e524beda59577100025e4b7e942b29982/alembic/versions/20260908_001_aim_data_oauth_activate.py) [app/core/config.py](https://github.com/aidotmarket/ai-market-backend/blob/5fe6486e524beda59577100025e4b7e942b29982/app/core/config.py) ; frontend [default predicate](https://github.com/aidotmarket/ai-market-frontend/blob/a27b3be524c3d25ac6c8d6e2bb0755faf8021891/lib/aim-data-continuation.ts); customer [settings](https://github.com/aidotmarket/aim-data/blob/71f73ea21044752fbf8724f80d3db2e887f47f79/app/config.py), [Compose](https://github.com/aidotmarket/aim-data/blob/71f73ea21044752fbf8724f80d3db2e887f47f79/docker-compose.aim-data.yml), [installer](https://github.com/aidotmarket/aim-data/blob/71f73ea21044752fbf8724f80d3db2e887f47f79/installers/aim-data/install.sh).

| Gate 4 live proof | Status |
| --- | --- |
| Deployed A/B identities, active `s1665_aim_data_oauth_activate` seed, C release version/digest and effective defaults | pending |
| AC1/AC2 provider-only fresh install; AC3 2FA, confirmation/Cancel and identity/registration | pending |
| AC4 fallback fresh/upgrade/reload/rotation; local operator key/cookie parity | pending |
| AC6 Docker/browser chain at 8080/8099/18081; wrong/occupied port and remote/origin refusal | pending |
| AC9 refresh race/replay/revocation and lifetime bound; AC14 disable/revoke/rollback and website/other-client continuity | pending |
| AC11 owner-approved no-payment fresh-install charter: login, profile/PII, metadata approval, publish and readiness | pending |
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
