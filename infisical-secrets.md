# Infisical Secrets Management

> **Deployed**: S357 (2026-03-30)
> **URL**: https://secrets.ai.market
> **Railway Project**: `fe02d729-5921-4199-8e6a-2e026acc1326`
> **Replaces**: Doppler (demoted to archive-only, see `doppler-secrets.md`)

## Quick Reference

| Resource | ID |
|---|---|
| Organization | `cba08a81-6af0-409c-a405-f4328e5dbc66` |
| ai-market-backend | `bd272d48-c5a1-4b52-9d24-12066ae4403c` |
| ai-market-frontend | `1c0589a5-0634-4d06-ac4d-56d0e83af3cf` |
| koskadeux-mcp | `0943f641-faee-4324-b337-0d50c276e4a9` |
| SysAdmin Identity | `62f1bfac-3e07-4f4e-b15d-42f1bbcc9f5e` |

## Environments

Each project has three environments: `dev`, `staging`, `prod`.

## SMTP Configuration

SMTP is configured via Resend for outbound email (invites, MFA codes, notifications).

| Variable | Value |
|---|---|
| `SMTP_HOST` | smtp.resend.com |
| `SMTP_PORT` | 587 |
| `SMTP_SECURE` | false (STARTTLS) |
| `SMTP_FROM_ADDRESS` | noreply@ai.market |
| `SMTP_FROM_NAME` | ai.market |
| `SMTP_USERNAME` | resend |
| `SMTP_PASSWORD` | (Resend API key — stored in Railway env vars) |

**Status**: MFA and email invites are now available.

## Accessing Secrets

### Web Dashboard
Navigate to https://secrets.ai.market and log in with your admin account.

### CLI
```bash
export INFISICAL_API_URL=https://secrets.ai.market
infisical login --domain=https://secrets.ai.market

# List secrets
infisical secrets --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=prod

# Export to .env
infisical export --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=prod --format=dotenv > .env

# Inject into a process
infisical run --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=dev -- python app.py
```

### API (Machine Identity)
```bash
# Authenticate with machine identity token
curl -s "https://secrets.ai.market/api/v3/secrets/raw?workspaceId=<PROJECT_ID>&environment=prod&secretPath=/" \
  -H "Authorization: Bearer <TOKEN>"
```

## Machine Identities

> Verified S964 (2026-06-20): headless chain confirmed live end-to-end; client secret is non-expiring; `CLOUDFLARE_API_TOKEN` resolves headlessly from `ai-market-backend`/prod.

### sysadmin-agent
- **Identity ID**: `62f1bfac-3e07-4f4e-b15d-42f1bbcc9f5e`
- **Purpose**: SysAdmin AI agent + unattended jobs on Titan-1 (gateway secret injection, agent skills)
- **Org role**: Admin on all 3 projects (ai-market-backend, ai-market-frontend, koskadeux-mcp)
- **Active auth method**: **Universal Auth** (client-id + client-secret). The identity also has a Token Auth method configured, but Universal Auth is the operative login path on Titan-1 (Last Login Method = Universal Auth). Do not assume the cached token file is a static Token-Auth token — it is a re-minted Universal-Auth JWT (below).
- **Client ID** (non-secret): `b45b755e-455b-4b32-815c-274529edc04d`
- **Client secret expiry**: **never** (EXPIRES = "-" in the UI; ~500+ uses). No rotation clock. If you ever rotate, add a new secret with TTL=0 / Max Uses=0, update the keychain (below), verify, then revoke the old one.

#### Headless auth chain on Titan-1 (how the token file stays alive)
The file `~/.config/infisical/sysadmin-token` is **not** a static token — it is a short-lived Universal-Auth JWT (Access Token TTL 86400s/24h) that is continuously re-minted. Do not treat it as permanent.

1. Universal-auth creds live in the **macOS keychain** under account `infisical-sysadmin-agent`:
   `security find-generic-password -a infisical-sysadmin-agent -s infisical-client-id` (and `-s infisical-client-secret`). Domain comes from `~/.config/infisical/api-domain` (= `https://secrets.ai.market/api`).
2. `~/bin/infisical_auth_refresh.sh` reads those creds, runs `infisical login --method=universal-auth --silent --plain`, and writes the JWT to `~/.config/infisical/sysadmin-token` (chmod 600). Idempotent and **non-interactive — safe to run anytime to verify**.
3. `com.koskadeux.infisical-token-refresh` LaunchAgent runs the refresh every 6h (RunAtLoad). Errors → `/var/tmp/koskadeux/token-refresh.err`.
4. The gateway launches via `~/bin/launch_with_infisical.sh`, which refreshes the token first (S760) then `exec`s `infisical run --token=<jwt> --silent -- gateway_server.py`. The `--token` form is non-interactive and never triggers the login popup.

**Failure mode (root trigger behind the lost-handoff incidents):** if the keychain creds go missing or the client secret expires, the refresh `login` fails, and an `infisical run` without a valid token falls back to interactive auth, which hangs/degrades the gateway on (re)start and can drop in-memory session state. Mitigated today because the client secret is non-expiring and S760 refreshes before launch — but a missing keychain entry would re-trigger it. To verify health: run `~/bin/infisical_auth_refresh.sh` and check the JWT `exp` on the token file.

**Rotate keychain creds** (after creating a new non-expiring client secret in the UI):
```bash
security add-generic-password -U -a infisical-sysadmin-agent -s infisical-client-secret -w '<NEW_SECRET>'
~/bin/infisical_auth_refresh.sh >/dev/null && echo OK   # mints a fresh JWT
```
No gateway restart needed — the next scheduled refresh / next launch picks it up. Coordinate on the peer bus before restarting `com.koskadeux.gateway` / `-infisical-token-refresh` / `-mcp`; a cycle blips any live MCP build.

## Secret Rotation

**App-read secrets are NOT loaded from Infisical at runtime** (see Known Gotchas). The FastAPI app on `ai-market-backend` reads secrets from the **Railway variable store**. Updating Infisical alone does NOT reach production. For any app-read secret:

1. Update the value in Infisical (dashboard or API). Env slug is `prod` (not "production"). Infisical stays the canonical record for humans/agents.
2. Set the same value in Railway: `railway variables --service ai-market-backend --set "KEY=VALUE" --skip-deploys` (never echo the value).
3. Redeploy so the new container boots with it: `railway redeploy --service ai-market-backend --yes`.
4. Verify the service is healthy and, where possible, that the new value actually works (Stripe example below). Only THEN revoke the old credential.

Until `BQ-RAILWAY-INFISICAL-SYNC` lands (tracked; ticket `T-2026-000048`), steps 2-4 are mandatory, not optional. A future auto-sync will collapse this to "update Infisical, redeploy."

### Stripe API keys (`acct_1SuHQHRucxd97j0A`)

What each key is: `STRIPE_SECRET_KEY` (sk_live, backend, full account access — the sensitive one); `STRIPE_PUBLISHABLE_KEY` (pk_live, public; currently NOT wired into the frontend, so rotating it cannot break the site); `STRIPE_WEBHOOK_SECRET` (whsec, verifies inbound webhooks — NOT an API key, separate rotation, unaffected by an API-key roll); `STRIPE_TEST_*` are sandbox-only (ignore for live work).

On a Stripe-flagged compromise of the secret key:
1. Stripe -> Developers -> API keys -> **Roll** the secret key with a short grace window (do NOT pick "now" until the new key is deployed, or the live backend errors). Optionally roll the publishable key too (hygiene; harmless, it's unused client-side). Copy the new value(s); never paste into chat.
2. Save the new value(s) in Infisical `prod` (`STRIPE_SECRET_KEY`, and `STRIPE_PUBLISHABLE_KEY` if rolled).
3. Apply to Railway + redeploy per the general procedure above.
4. **Verify the new secret authenticates BEFORE revoking the old one:**
   `railway run --service ai-market-backend -- .venv/bin/python -c "import os,stripe; stripe.api_key=os.environ['STRIPE_SECRET_KEY']; print(stripe.Account.retrieve().id)"`
   Expect `acct_1SuHQHRucxd97j0A`; an invalid key raises `AuthenticationError`.
5. Once verified, expire/revoke the old key in Stripe.

Do NOT rotate `STRIPE_WEBHOOK_SECRET` for an API-key compromise — separate credential. If you ever do, use the graceful two-value swap (`STRIPE_WEBHOOK_SECRET`=new, `STRIPE_WEBHOOK_SECRET_PREVIOUS`=old; see backend `webhooks.py`).

> S1039: live secret-key compromise rotation. Found `STRIPE_PUBLISHABLE_KEY` in Railway had drifted (matched neither the old nor new Stripe value) — reconciled during the same rotation. Confirms the manual-sync gap still bites; tracked in `T-2026-000048`.

## Emergency Recovery

- **Emergency Kit PDF**: Saved during initial setup — required if admin account is locked out
- **Railway project**: Can be redeployed from template if Infisical service fails
- **Postgres backup**: Railway volume snapshots — enable scheduled backups in Railway dashboard
- **SMTP recovery**: If Resend key is rotated, update `SMTP_PASSWORD` in Railway env vars for the Infisical project, then redeploy

## Architecture Notes

- Infisical runs as a separate Railway project (isolated from ai-market services)
- Postgres + Redis on private networking (not publicly accessible)
- User registration disabled — admin creates accounts manually
- SMTP configured via Resend (S358) — email invites and MFA are active

## Cleanup TODO (requires web UI)

- [ ] Delete 3 duplicate/test projects in Infisical dashboard
- [ ] Rename organization from default to "ai.market"

## Legacy: Doppler

Doppler (`doppler-secrets.md`) is demoted to archive-only. It still contains a snapshot of secrets as of 2026-03-30 but is NOT the source of truth. Do not update secrets in Doppler.

## Known Gotchas (S533)

### CLI `--plain` flag mangles JSON values with literal newlines

`infisical secrets get <NAME> --plain` converts escaped `\n` inside a JSON string value (e.g. the `private_key` field of a service-account JSON) into actual newline characters in the output stream. This produces JSON that fails `json.loads()` with `Invalid control character at: line N column X` because real newline chars are not legal inside JSON string values.

Workaround when you need to consume an SA JSON locally via CLI:

```python
import sys, json
raw = sys.stdin.read().rstrip()
sanitized = raw.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
info = json.loads(sanitized)
```

This is a CLI-output-format issue, not a stored-value issue. Railway env-var sync transmits the value correctly because env vars handle escapes differently than CLI stdout.

### Naming convention: canonical UPPER_SNAKE for Pydantic Settings

Application services using Pydantic `SettingsConfigDict(case_sensitive=True)` (e.g. ai-market-backend) require Infisical secret names to match Pydantic field names exactly. The canonical convention is UPPER_SNAKE_CASE (e.g. `VERTEX_GEMINI_KEY`, not `Vertex_Gemini_Key`).

When introducing a new secret, name it UPPER_SNAKE in Infisical from the start to avoid an Infisical→Railway→code rename round-trip.

### Vertex Gemini key consolidation pending (S533)

As of S533, three Infisical secret names hold (or have held) the same Vertex Express API key:
- `Vertex_Gemini_Key` — primary today (created during S533 P0 incident response)
- `VERTEX_API_KEY` — used by AG/Council via `koskadeux-mcp/scripts/launch_ag_server.sh`
- `VERTEX_GEMINI_KEY` — canonical name targeted by `BQ-LLM-EMBEDDING-VERTEX-MIGRATION` Gate 2

Gate 2 pre-flight task consolidates to `VERTEX_GEMINI_KEY` only, updates `launch_ag_server.sh` to read the canonical name, and removes the duplicates.

- **App-read secrets live in the Railway env, not loaded from Infisical at runtime (S942).** Infisical is wired only for the SysAdmin agent skill (`infisical_ops.py`); the FastAPI app reads secrets such as `GITHUB_WEBHOOK_SECRET` from its process env = a Railway variable on `ai-market-backend`. A value placed only in Infisical will NOT reach the app — also set the Railway variable, then redeploy. (BQ-RAILWAY-INFISICAL-SYNC manual-sync class.) See `reconciliation-github-webhook.md` §E.

### `INFISICAL_PROJECT_ID` on Titan-1 points at koskadeux-mcp, not the backend (S964)

The shell env on Titan-1 exports `INFISICAL_PROJECT_ID` = the **koskadeux-mcp** project (`0943f641…`) — gateway/council secrets like `DEEPSEEK_API_KEY`. Backend secrets (`CLOUDFLARE_API_TOKEN`, `AWS_*`, billing, etc.) live in **ai-market-backend** (`bd272d48…`). If you run `infisical secrets get FOO` without `--projectId`, you query koskadeux-mcp and a backend-only secret comes back **empty** (rc=0, len 0) — not missing, just the wrong drawer. Always pass `--projectId` explicitly for cross-project reads.

### `infisical secrets delete` defaults to `--type personal` (S964)

A plain `infisical secrets delete NAME` under machine-identity auth returns `400 Bad Request — Must be user to delete personal secret`, because the CLI default is `--type personal` and machine identities have no personal secrets. To delete a normal (shared) secret, pass `--type shared` explicitly.
