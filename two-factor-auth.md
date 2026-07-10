# two-factor-auth — TOTP Two-Factor Authentication Reference

## What it is

Reference for the customer-facing TOTP (authenticator-app) two-factor flow in `ai-market-backend`: how a user enrolls, how the secret is stored, the server-side encryption key it depends on, and the failure modes and fixes. This is the runbook to read first whenever 2FA enable/verify returns a 500 on `ai.market/dashboard/settings`.

**Owning service:** `ai-market-backend` (see `ai-market-backend.md` for the broader service runbook)
**Live:** `api.ai.market`
**Customer-facing surface:** `ai.market/dashboard/settings` (frontend) → `/api/v1/auth/2fa/*` (backend)
**Sibling runbooks:** `auth-signup-flow.md` (login/registration), `infisical-secrets.md` (secret store)

## Architectural principle — non-negotiable

The user's TOTP secret is **encrypted at rest**. It is never stored in plaintext and never appears in code. The encryption key lives only in the secret store and is injected into the running process as an environment variable. Losing or changing the key after users have enrolled makes their stored secrets undecryptable, which locks them out of 2FA — so key rotation is a deliberate, user-impacting operation, not a config tweak.

## Path map

| Step | Where | Notes |
|------|-------|-------|
| Begin enrollment | `TOTPService.setup_2fa` in `app/services/totp_service.py` | Generates `pyotp.random_base32()` secret, stores a short-lived setup session in Redis (`TOTP_SETUP_TTL_SECONDS`, ~600s), returns the QR provisioning URI + manual-entry secret to the UI. |
| Verify + enable | `TOTPService.verify_setup` | User submits the 6-digit code. On success the plaintext secret is **encrypted** and written to `users.totp_secret_enc`, and `totp_enabled` is set. |
| Encrypt helper | `TOTPService._encrypt_secret` + `TOTPService._decoded_encryption_key` | Reads `settings.TOTP_ENCRYPTION_KEY`, decodes it, builds the Fernet cipher. This is where both 500s below originate. |
| Disable | `TOTPService` disable path | Clears `users.totp_secret_enc` and `totp_enabled`. |
| Login challenge | `app/api/v1/endpoints/auth.py` (totp checks gate the login/pre-auth flow) | If `totp_enabled` and a secret exist, login requires a current code; uses a one-time `PreAuthSession`. |
| OIDC SSO login challenge | `app/api/v1/endpoints/sso.py` `oidc_callback` | Same gate since S1175 (T-2026-000115, unanimous Council): a totp-enabled user gets the pre-auth challenge instead of a session; `POST /auth/2fa/verify` completes the OIDC login. Previously OIDC minted a session with no code prompt (the 2FA bypass). |
| SSO-originated verify | `app/services/totp_service.py` | The challenge stores the initiating method in `purpose` (`2fa:oidc` / `2fa:saml`, String(20), no migration); `verify_2fa` mints the final session with that `auth_method` so SSO refresh enforcement (`sso.py`, accepts only oidc/saml) doesn't kill the session at first refresh. All non-SSO flows keep `purpose='2fa'`, method `'2fa'`. NOTE: there is no frontend SSO callback page yet — when one is built it must handle the `PreAuthRequiredResponse` shape (reuse `<TwoFactorChallenge>`). |
| Column | `users.totp_secret_enc` (String 512), added by migration `alembic/versions/20260321_001_auth_phase3_totp.py` | Nullable; null = not enrolled. |
| Setting | `TOTP_ENCRYPTION_KEY` in `app/core/config.py` (`Optional[str] = None`) | Read from the process environment by pydantic settings. |

## Configuration — the encryption key (read this before touching anything)

**Setting name:** `TOTP_ENCRYPTION_KEY`

**Required format:** a URL-safe base64 string that decodes to **exactly 32 bytes** (a standard Fernet key). Generate one with:
```
python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```
This yields a 44-character value ending in `=`. The decode logic in `_decoded_encryption_key` accepts the value with or without `=` padding, and also accepts a raw 32-byte string. It does **not** accept hex — a 64-character hex string decodes to 48 bytes under base64 (and is 64 bytes raw), so it is rejected.

**Where the value must live:**
- Infisical, project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment slug **`prod`**. (See `infisical-secrets.md`.)
- The Railway `ai-market-backend` service environment (belt-and-suspenders; the running process reads `TOTP_ENCRYPTION_KEY` from its own env).

**Environment-slug gotcha (important):** the Infisical project's environment slug is **`prod`**, not `production`. The code default `INFISICAL_ALLOWED_ENVS = ["production"]` in `config.py` is misleading — the live backend resolves secrets from `prod`. Setting the key under a `production` slug silently does nothing (that environment does not exist in the project).

## Known issues / failure modes

### 500 — "TOTP encryption key not configured"
Raised when `settings.TOTP_ENCRYPTION_KEY` is empty in the **running** process. Two common causes:
1. The key is absent from the environment the backend actually reads (e.g., set under the wrong Infisical slug, or only on a different service).
2. The key was added after the backend last deployed, so the running process never loaded it. **Fix is a redeploy** of `ai-market-backend`.

### 500 — "Invalid TOTP encryption key"
The key is present but the wrong format/length — most often a 64-character hex string instead of a 32-byte URL-safe base64 value. Regenerate per the format above and replace it everywhere it lives, then redeploy.

### 503 — "2FA setup unavailable"
Redis is unreachable. The enrollment setup session is stored in Redis with a TTL; if Redis is down, enrollment can't start. Check the `Redis` service before anything else.

### History
- **S774:** Live "not configured" 500 on the dashboard. Root cause was both failure modes at once — the key existed only under the `prod` slug, in 64-char hex (wrong format), and the running process had never loaded it. Fixed by generating a correct 32-byte URL-safe base64 key, writing it to Infisical `prod` and the Railway `ai-market-backend` env, and redeploying. No users were enrolled at the time, so no re-enrollment was needed.

## Diagnostic procedures (read-only, value never printed)

Presence + format check against Infisical (`prod`), classifying without exposing the value:
```
export INFISICAL_DISABLE_UPDATE_CHECK=true
TOKEN=$(cat ~/.config/infisical/sysadmin-token)
PROJ=bd272d48-c5a1-4b52-9d24-12066ae4403c; DOM=https://secrets.ai.market/api
V=$(infisical secrets get TOTP_ENCRYPTION_KEY --env=prod --token="$TOKEN" --projectId="$PROJ" --domain="$DOM" --plain --silent 2>/dev/null)
V="$V" python3 -c "import os,base64;k=os.environ.get('V','');d=base64.urlsafe_b64decode((k+'='*(-len(k)%4)).encode()) if k else b'';print('present=%s valid_for_code=%s char_len=%d'%(bool(k),len(d)==32,len(k)))"
```
- `present=False` → missing from `prod`. → "not configured" once loaded.
- `valid_for_code=False` with a non-zero length → wrong format. → "Invalid".
- `valid_for_code=True` but the live API still errors → the running process is stale; redeploy.

Confirm it's also on the Railway service (name only, value masked):
```
cd ~/Projects/ai-market/ai-market-backend && unset RAILWAY_TOKEN
railway variables --service ai-market-backend --kv 2>/dev/null | grep -c '^TOTP_ENCRYPTION_KEY='
```

## Recovery / fix procedure

1. Generate a correct key (see Configuration). Keep it in a shell variable; never echo it.
2. Write it to Infisical `prod`:
   `infisical secrets set "TOTP_ENCRYPTION_KEY=$KEY" --env=prod --token="$TOKEN" --projectId="$PROJ" --domain="$DOM"`
3. Write the same value to the Railway backend service:
   `cd ~/Projects/ai-market/ai-market-backend && unset RAILWAY_TOKEN && railway variables --service ai-market-backend --set "TOTP_ENCRYPTION_KEY=$KEY"`
   (Setting a Railway variable auto-triggers a redeploy of that service.)
4. If no redeploy was triggered, force one: `railway redeploy --service ai-market-backend --yes`.
5. **Rotation caveat:** if any users already have `totp_secret_enc` set, changing the key makes their secrets undecryptable. Do not rotate a live key in use. If you must, plan a forced re-enrollment: clear `totp_secret_enc` + `totp_enabled` for affected users and notify them.

## Verifying a fix in production

1. Wait for the `ai-market-backend` deploy to finish (Railway dashboard, or `railway status`). Confirm `/health` is green at `api.ai.market`.
2. In the UI: `ai.market/dashboard/settings` → Security → Enable two-factor authentication. The QR + manual secret should render, and "Verify and enable" with a current code should succeed (no 500).
3. The setup session is Redis-backed with a ~600s TTL; if the screen was open before the fix, reopen it to get a fresh session.

## Cross-references
- `ai-market-backend.md` — service overview, config, troubleshooting
- `auth-signup-flow.md` — login/registration paths and the sign-up-is-sacred principle
- `infisical-secrets.md` — secret store, environments, tokens
