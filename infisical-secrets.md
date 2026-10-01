---
title: Infisical Secrets Management
owner: unassigned
last_verified: '2026-09-27'
aliases: []
error_signatures: ['error code: 1010', FST_ERR_CTP_EMPTY_JSON_BODY, 'Invalid or missing Internal API Key']
---

# Infisical Secrets Management

> **Deployed**: S357 (2026-03-30)
> **URL**: https://secrets.ai.market
> **Railway Project**: `fe02d729-5921-4199-8e6a-2e026acc1326`
> **Replaces**: Doppler (demoted to archive-only, see `doppler-secrets.md`)

## Operating rule: check runbooks first

**Always check for a relevant runbook. If none exists, create one. If it is inaccurate, update it.**

Before advising on secret names, project/environment selection, access, verification or rotation, search the runbooks and read this document and the relevant provider/service runbook. For credential operations, also read [local-secops.md](local-secops.md). Use current evidence to resolve outdated or conflicting instructions; do not invent project names or assume a password manager is the secret store.

## Source of Truth & Propagation (READ FIRST)

**Infisical is the single source of truth for backend secrets.** As of S1125 the native **Infisical→Railway sync is LIVE** (sync `railway-backend-prod`, auto-sync ON, **disable-deletion ON**, initial behaviour "prioritize Infisical"). A change to a secret in Infisical `ai-market-backend`/`prod` now mirrors to the Railway `ai-market-backend` service automatically — no manual Railway set + redeploy for routine changes.

**Connector auth folder (S1753, 2026-09-27):** `CONNECTOR_OAUTH_SIGNING_KEYS` is in the same Infisical project (`bd272d48-c5a1-4b52-9d24-12066ae4403c`), `prod`, folder `/connector-auth`. A second native sync, `railway-connector-auth-prod`, sends that folder only to Railway `ai-market-connector-auth` (`5ee110fc-df73-4107-b8fd-469099cb64d2`); auto-sync is on, initial behavior is `overwrite-destination`, and `disableSecretDeletion` is true. The root `railway-backend-prod` sync is non-recursive: a folder canary did not reach `ai-market-backend` or `ai-market-connector` after a forced root sync pass. Infisical omits `includeAllSubFolders: false` from readback on both syncs, so treat omission as non-recursive only for these pinned, canary-proven shapes. Any Infisical `prod` write can trigger both syncs. Do not write to `/connector-auth` except through the one-time keyset tool or a reviewed procedure; see [customer-mcp-connector.md](customer-mcp-connector.md).

**Issue-channel watcher folder (S1758, 2026-09-28):** `ISSUE_CHANNEL_RAILWAY_EVENTS_TOKEN` is in the same project, `prod`, folder `/issue-channel-watcher-railway`. A third native sync, `railway-issue-channel-watcher-events-prod`, sends that folder only (non-recursive) to Railway `issue-channel-watcher` (`d48dd44c-4541-4387-89da-50b2b1d0c8fe`); auto-sync on, `overwrite-destination`, `disableSecretDeletion` true; a canary proved the folder is outside the root sync. Any Infisical `prod` write can now trigger all three syncs. Write to this folder only through the reviewed controller described in [issue-channel.md](issue-channel.md) "Railway events credential (watcher)".

**How secrets are moved / rotated / generated: the local AI.** Day-to-day credential work runs through the **Local SecOps assistant** on Koskadeux (hand-written plan + guardrailed executor; the local model was retired 2026-08-18; values never leave the host, no human types them). See **[local-secops.md](local-secops.md)** for full operation. It can generate/rotate owned secrets, and copy an existing value **Railway → Infisical** (`reconcile-from-railway`) when Railway has drifted ahead.

**CAUTION (why this matters):** because the sync prioritizes Infisical, a **stale** value in Infisical for a shared key will be pushed over a good Railway value on the next sync. This took prod down once (S1125: stale `GITHUB_TOKEN` + `GCP_SERVICE_ACCOUNT_JSON` clobbered working Railway creds). Before enabling/triggering a sync, ensure Infisical is not stale for shared keys — use `reconcile-from-railway`. Railway-managed vars (e.g. `DATABASE_URL`, `REDIS_URL`, `RAILWAY_*`) must NOT live in Infisical.

**Second incident (S1751/S1752, 2026-09-26):** Infisical `prod` still held `X402_ENABLED=true` after production had moved to `false` on Railway. Two ordinary secret writes through local-secops (`GATEWAY_PAIRING_PEPPER`, `GATEWAY_SIGNER_TOKEN`, 23:12-23:13 UTC, audit.log lines 147-148) made the sync push the whole set, which flipped Railway to `true`. Every backend deploy then failed at startup with `LISTING_LICENSES_ENABLED=true is incompatible with X402_ENABLED=true`; production stayed up only because the previous deployment kept running. Fixed with `secops_execute.py --reconcile X402_ENABLED --execute`; that Infisical write itself triggered a new backend deploy, which is expected. Lesson: **a write to any `prod` secret re-pushes every Infisical-owned key and redeploys the backend.**

**Who owns which flag (checked 2026-09-26; `CRM_V2_READ_MODE`/`CRM_V2_WRITE_MODE` rechecked 2026-09-27 by names-only diff, present in both; recheck with a names-only diff of `railway variables --json` against `infisical export --format json`, run directly with the sysadmin Infisical token (`INFISICAL_TOKEN` from `~/.config/infisical/sysadmin-token`, not as a local-secops plan, which refuses `export`) and printing key names only: the export is an array, so `jq -r '.[].key'`). Do not use a local-secops `infisical secrets get` step to test whether a key exists: it returns `ok` for a key that does not exist.**

- Infisical-owned (change them in Infisical, never only on Railway, or the next sync reverts you): `X402_ENABLED`, `STRIPE_TEST_MODE`, `SYSADMIN_HEAL_ENABLED`, `KAGGLE_SUBMISSION_ENABLED`, `BACKUP_LOCAL_FALLBACK_ENABLED`, `CRM_V2_READ_MODE`, `CRM_V2_WRITE_MODE` (legacy: no longer read by backend code), and all `SELLER_WORKSPACE_*` flags.
- Railway-only (not in Infisical, so the sync leaves them alone; change them on Railway): `AIM_GATEWAY_ENABLED`, `LISTING_LICENSES_ENABLED`, `CUSTOM_LICENSE_TEXT_SUBMISSIONS_ENABLED`, `ORDER_PAYOUT_DISPATCH_ENABLED`, `STRIPE_PAYIN_ONBOARDING_ENABLED`, `DATA_VERIFICATION_ENABLED`, `E2E_TEST_ROUTES_ENABLED`, `E2E_PREFLIGHT_ROUTES_ENABLED`, `ANON_CHAT_ENABLED`, `HUGGINGFACE_SUBMISSION_ENABLED`, `CORPUS_CORRECTION_DELTA_ENABLED`, `CORPUS_METADATA_GENERATION_INTERACTION_ENABLED`, `ALLAI_REMEDIATOR_INCIDENT_QUEUE_ENABLED`, `TERMS_GATE_MODE`, `LLM_ANTHROPIC_REPLACEMENT_MODEL` (S1761: `gpt-5.6-luna`; see allai-agents.md "Model provider switch").
- Before any Infisical `prod` write, compare the Infisical value of every Infisical-owned flag with Railway and reconcile drift first.

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

## Seller Cloudflare development credentials (Max decision, 2026-09-08)

Use the existing **ai-market-backend** project (`bd272d48-c5a1-4b52-9d24-12066ae4403c`), **prod** environment (dashboard label Production), root folder **/**. Max requested that these development credentials be distinguished in their names instead of creating a project or switching environments:

| Name | Purpose |
|---|---|
| `STAGING_CLOUDFLARE_SELLER_OAUTH_CLIENT_SECRET` | Provider-issued private development OAuth client secret; never include its value in documentation |
| `STAGING_CLOUDFLARE_SELLER_OAUTH_CLIENT_ID` | Client ID `db7c0057a307855bb73914fb58723ad8` |

This prefix records development intent; it is not environment or access isolation. Because prod is documented as synced, these names may propagate to Railway. The development integration must explicitly select these names; production must not use them as fallback credentials. This storage decision does not authorize enabling R2 or deploying the integration.

CLI verification on September 8 found a nonempty, correctly formatted secret, while the client ID lookup returned empty. This is a dated observation, not a permanent status; recheck both before use. A successful CLI exit alone does not prove a value exists.

## Safe CLI verification

Use the CLI for routine verification, with explicit `--domain=https://secrets.ai.market/api`, `--projectId`, `--env=prod`, and `--path=/`. Use the documented machine-identity authentication for unattended work; keep tokens out of arguments and outputs. Query only the requested names. Capture output inside a local process and emit only existence/nonempty checks and, where appropriate, a comparison result. Never print raw secret values into chat or logs.

Verify exact identity values against the provider registration. A secret format check establishes neither an exact match nor successful provider authentication. If a lookup returns empty, check the explicit target and metadata before declaring the stored value blank; wrong-project and missing-key lookups can return exit code zero.

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
- **Purpose**: SysAdmin AI agent + unattended jobs on Koskadeux (gateway secret injection, agent skills)
- **Org role**: Admin on all 3 projects (ai-market-backend, ai-market-frontend, koskadeux-mcp)
- **Active auth method**: **Universal Auth** (client-id + client-secret). The identity also has a Token Auth method configured, but Universal Auth is the operative login path on Koskadeux (Last Login Method = Universal Auth). Do not assume the cached token file is a static Token-Auth token — it is a re-minted Universal-Auth JWT (below).
- **Client ID** (non-secret): `b45b755e-455b-4b32-815c-274529edc04d`
- **Client secret expiry**: **never** (EXPIRES = "-" in the UI; ~500+ uses). No rotation clock. If you ever rotate, add a new secret with TTL=0 / Max Uses=0, update the keychain (below), verify, then revoke the old one.

#### Headless auth chain on Koskadeux (how the token file stays alive)
The file `~/.config/infisical/sysadmin-token` is **not** a static token — it is a short-lived Universal-Auth JWT (Access Token TTL 86400s/24h) that is continuously re-minted. Do not treat it as permanent.

1. Universal-auth creds live in the **macOS keychain** under account `infisical-sysadmin-agent`:
   `security find-generic-password -a infisical-sysadmin-agent -s infisical-client-id` (and `-s infisical-client-secret`). Domain comes from `~/.config/infisical/api-domain` (= `https://secrets.ai.market/api`).
2. `~/bin/infisical_auth_refresh.sh` reads those creds, runs `infisical login --method=universal-auth --silent --plain`, and writes the JWT to `~/.config/infisical/sysadmin-token` (chmod 600). Idempotent and **non-interactive — safe to run anytime to verify**. It also **prints the JWT to stdout**: always run it as `~/bin/infisical_auth_refresh.sh >/dev/null 2>&1` so the token never lands in a transcript or log (S1738).
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

The backend reads its process environment, populated through the documented native Infisical→Railway sync. The earlier manual-sync procedure is superseded by **Source of Truth & Propagation** above.

1. Confirm the exact key, project, environment and intended consumer; use Local SecOps for supported credential operations.
2. Update the canonical Infisical entry within the authorized scope.
3. Verify the sync result and the consuming service's effective configuration. Catalog storage, Railway propagation and successful provider authentication are separate checks.
4. Verify the new credential works before revoking the old one. Restart/redeploy only when needed and authorized; do not manually overwrite Railway as the routine path.

A failed sync requires investigation, not an assumed manual push. Never enable or trigger a sync using stale shared values.

### INTERNAL_API_KEY consumers (verified in the T-2026-000909 rotation, 2026-10-01)

Canonical value: Infisical `ai-market-backend` (project `bd272d48-…`), `prod`, path `/`. A rotation is not done until every consumer below carries the new value:

1. Railway `ai-market-backend` (native Infisical sync), then redeploy it.
2. Railway services that read it by reference `${{ai-market-backend.INTERNAL_API_KEY}}`: `ai-market-backup`, `celery-beat`, `celery-worker`, `gateway-door-worker`, `seller-profile-worker`, `issue-channel-watcher`. Redeploy each. Keep every one of them a reference, never a literal copy (`ai-market-backup` was a literal copy until this rotation).
3. GitHub repo secret `INTERNAL_API_KEY` on `aidotmarket/ai-market-backend` (Daily Health Check workflow); set with `GITHUB_ORG_ADMIN_TOKEN`.
3a. GitHub repo secret `DEPLOY_RECEIPT_KEY` on `aidotmarket/ai-market-frontend` and `aidotmarket/ops-ai-market` (their `deploy-receipt.yml` posts to `/api/v1/allai/events/` with `X-Internal-API-Key`; the backend's own receipt uses item 3's `INTERNAL_API_KEY`, and its unused `DEPLOY_RECEIPT_KEY` secret was set to the same value on 2026-10-01 to avoid a stale copy); same value, set with `GITHUB_ORG_ADMIN_TOKEN` by piping the value to `gh secret set` on stdin. Missed in T909: the ops.ai.market receipt failed with 401 until fixed on 2026-10-01 (S1790, verified by rerunning ops run 36862035300). To find every GitHub consumer, list each `aidotmarket` repo's Actions secrets (names only) for `INTERNAL_API_KEY` and `DEPLOY_RECEIPT_KEY`.
4. Cloudflare Worker `allai-dead-man-switch` secret.
5. Koskadeux: `/Users/max/koskadeux-mcp/.env`. `koskadeux_server.py` calls `load_dotenv(.env, override=True)`, so this file wins over anything the launcher exports. Replace the one line from Infisical (never print the value; verify equality), then `launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp`. Missed in T-909: the restarted MCP kept sending the old key and Living State writes, the peer bus, support tickets and `kd_session_close` all returned HTTP 401 `Invalid or missing Internal API Key`.
6. The e2e harness reads it at run time; nothing to restart.

Other Koskadeux jobs pick up a rotation by themselves: `com.koskadeux.railway-alert-parity` fetches the key from Infisical backend prod on every run (`bin/railway-alert-parity-env.sh`), and `com.koskadeux.ticket-probe-reconciler` re-reads `koskadeux-mcp/.env` on its next interval, so item 5 covers it. The gateway does not use this key.

Verify: backend heartbeat 200 with the new key, a Living State event write, `peer_msg_inbox`, and a support-ticket read.

### Koskadeux `.env` shadow copies

Because of `override=True` (item 5 above), any rotated key that also sits in `koskadeux-mcp/.env` keeps its old value in the MCP process. After any rotation, compare `.env` key names against the rotated set and check equality with Infisical without printing values. Found stale in T-909 and fixed (S1790): `OPENAI_API_KEY` (replaced from backend prod), plus dead `OPENAI_API_KEY_FALLBACK` and `GATEWAY_ADMIN_PASSWORD` lines (removed). `DEEPSEEK_API_KEY` and `GLM_z_AI_API_KEY` are not in `.env`; `scripts/launch_mcp_server.sh` fetches them from Infisical `koskadeux-mcp` prod at launch, so a restart picks up a rotation. The gateway reads `GATEWAY_ADMIN_PASSWORD` from Infisical backend prod through `/Users/max/bin/launch_with_infisical.sh`; it calls `load_dotenv()` without override, so the injected value wins.

### Stripe API keys (`acct_1SuHQHRucxd97j0A`)

What each key is: `STRIPE_SECRET_KEY` (sk_live, backend, full account access — the sensitive one); `STRIPE_PUBLISHABLE_KEY` (pk_live, public; currently NOT wired into the frontend, so rotating it cannot break the site); `STRIPE_WEBHOOK_SECRET` (whsec, verifies inbound webhooks — NOT an API key, separate rotation, unaffected by an API-key roll); `STRIPE_TEST_*` are sandbox-only (ignore for live work).

### Stripe SANDBOX/test-mode keys — where they actually live (S1604)

`STRIPE_TEST_SECRET_KEY`, `STRIPE_TEST_PUBLISHABLE_KEY`, `STRIPE_TEST_WEBHOOK_SECRET` live in the **`prod` environment** alongside the live keys (Railway `production` env of `ai-market-backend`; Infisical `prod`). They are the synthetic-actor keys: `app/core/stripe_async.py:29-40` selects them for `synthetic_actor=True` operations and refuses any key not starting `sk_test_`. Read them with:
`railway variables -e production -s ai-market-backend --kv | grep STRIPE_TEST` (never echo full values into logs or chat).
Do NOT hunt for them in the Infisical `staging` env: an S1603 handoff note claimed they were there, but the prod service token is env-scoped and returns 403 on `staging` (fail-closed, by design: `INFISICAL_ALLOWED_ENVS=['prod']`), the Infisical CLI has no persistent login on this host, and the working copies are the prod-env ones above. Local repo `.env.test` holds placeholders only (`sk_test_xxx`), not real keys.

On a Stripe-flagged compromise of the secret key:
1. Stripe -> Developers -> API keys -> **Roll** the secret key with a short grace window (do NOT pick "now" until the new key is deployed, or the live backend errors). Optionally roll the publishable key too (hygiene; harmless, it's unused client-side). Copy the new value(s); never paste into chat.
2. Save the new value(s) in Infisical `prod` (`STRIPE_SECRET_KEY`, and `STRIPE_PUBLISHABLE_KEY` if rolled).
3. Verify native sync propagation and the consuming service per the general procedure above.
4. **Verify the new secret authenticates BEFORE revoking the old one:**
   `railway run --service ai-market-backend -- .venv/bin/python -c "import os,stripe; stripe.api_key=os.environ['STRIPE_SECRET_KEY']; print(stripe.Account.retrieve().id)"`
   Expect `acct_1SuHQHRucxd97j0A`; an invalid key raises `AuthenticationError`.
5. Once verified, expire/revoke the old key in Stripe.

Do NOT rotate `STRIPE_WEBHOOK_SECRET` for an API-key compromise — separate credential. If you ever do, use the graceful two-value swap (`STRIPE_WEBHOOK_SECRET`=new, `STRIPE_WEBHOOK_SECRET_PREVIOUS`=old; see backend `webhooks.py`).

> S1039: live secret-key compromise rotation. Found `STRIPE_PUBLISHABLE_KEY` in Railway had drifted (matched neither the old nor new Stripe value) — reconciled during the same rotation. Confirms the manual-sync gap (now CLOSED S1125 — native Infisical→Railway sync is live; see Source of Truth section above). `T-2026-000048`.

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

- **App-read secrets are read from the process environment.** The historical S942 manual-sync gap was closed by the S1125 native sync. (`reconciliation-github-webhook.md` still carries the pre-S1125 wording that Infisical-only values do not reach the app; that wording is stale.) Follow Source of Truth & Propagation and Secret Rotation above; verify propagation rather than assuming a catalog write proves runtime adoption.

### `INFISICAL_PROJECT_ID` on Koskadeux points at koskadeux-mcp, not the backend (S964)

The shell env on Koskadeux exports `INFISICAL_PROJECT_ID` = the **koskadeux-mcp** project (`0943f641…`) — gateway/council secrets like `DEEPSEEK_API_KEY`. Backend secrets (`CLOUDFLARE_API_TOKEN`, `AWS_*`, billing, etc.) live in **ai-market-backend** (`bd272d48…`). If you run `infisical secrets get FOO` without `--projectId`, you query koskadeux-mcp and a backend-only secret comes back **empty** (rc=0, len 0) — not missing, just the wrong drawer. Always pass `--projectId` explicitly for cross-project reads.

### `infisical secrets delete` defaults to `--type personal` (S964)

A plain `infisical secrets delete NAME` under machine-identity auth returns `400 Bad Request — Must be user to delete personal secret`, because the CLI default is `--type personal` and machine identities have no personal secrets. To delete a normal (shared) secret, pass `--type shared` explicitly.

## GitHub Tokens — inventory, minting, verification (S1612)

### Inventory (identities only; values live in Infisical)

| Identity | Project/env | Kind & scope | Expiry | Purpose |
|---|---|---|---|---|
| `ISSUE_CHANNEL_CLOUDFLARE_TOKEN` | ai-market-backend / prod (`bd272d48…`) | Cloudflare API token `issue-channel-readonly (koskadeux S1633, no expiry per Max)`, account d5346d3e…, permissions EXACTLY Account Settings:Read + Notifications:Read (all accounts) + Zone:Read (all zones) — the three GETs the s1511 Cloudflare adapter makes (`/accounts/{id}`, `/zones`, `/accounts/{id}/alerting/v3/history`). MINTED 2026-08-28 (mars S1633) through Max's logged-in dashboard session — the dash `/api/v4/user/tokens` POST is WAF-blocked for scripted calls, so the Create Custom Token FORM was driven; use the form, not the API. Verified live: `/user/tokens/verify` active, all three adapter GETs 200, a zone PATCH write-probe 403. **No expiry — Max directive S1633 ("I do not care about the security implication").** WIRED S1634: koskadeux-mcp adapter reads this name (PR #187, main `435021f65e`, CC+GLM APPROVE_WITH_NITS); Railway `issue-channel-watcher` service var set as a LITERAL (R.11 rule) and verified `tokens/verify` active. Note the token has NO Workers Scripts:Read, so it cannot serve backend `remediator_adapters.py` (which lists worker deployments) — that needs its own scoped token or a scope add. The old shared `CLOUDFLARE_API_TOKEN` in the same project returns `Invalid API Token` (code 1000) as of 2026-08-28 — dead; backend `remediator_adapters.py` still names it. | never | s1511 issue-channel Cloudflare source (record-only first) |
| `REMEDIATOR_CLOUDFLARE_TOKEN` | ai-market-backend / prod (`bd272d48…`) + Railway `ai-market-backend` service var (literal) | Cloudflare API token `remediator-readonly (backend S1634, no expiry per Max)`, account d5346d3e…, permission EXACTLY Workers Scripts:Read (all accounts) — the one GET the backend `CloudflareReadAdapter` makes (`/accounts/{id}/workers/scripts/{name}/deployments`). MINTED 2026-08-28 (mars S1634) by driving the dashboard Create Custom Token FORM in Max's Chrome tab (same form-driving as the S1633 token: set the downshift permission input value + `input` event, then select Read via the react-select `option-0` element; the third combo stays disabled until the permission actually registers). Verified: `tokens/verify` active, workers list 200 (4 scripts), deployments GET 200, worker PUT write-probe 403. **No expiry — Max directive S1633.** Replaces the dead shared `CLOUDFLARE_API_TOKEN` for the backend remediator: LIVE as of ai-market-backend main `2be1ae058` (PR #303, CC+GLM APPROVE_WITH_NITS), Railway deploy SUCCESS, live container reports the Cloudflare adapter configured. No code in koskadeux-mcp or ai-market-backend names the old secret any more; delete the dead `CLOUDFLARE_API_TOKEN` value from Infisical and the Railway backend vars at s1511 step 9 (`E2E_CLOUDFLARE_API_TOKEN` is a separate secret, untouched). Note: `CLOUDFLARE_ACCOUNT_ID` is NOT in Infisical prod — it lives only as a Railway backend service var. | never | backend allAI remediator Cloudflare read (S1533) |
| `ISSUE_CHANNEL_GITHUB_TOKEN` | ai-market-backend / prod (also mirrored as a Railway variable on `ai-market-backend`, per the S942 rule above) | Fine-grained PAT, owner `aidotmarket`, ALL repos, **Actions: read-only** + Metadata. VERIFIED LIVE 2026-08-27 (mars S1625): Actions+Metadata reads return 200 across repos and the s1511 watcher completed a 10-repo record-only sweep on this token at zero cost. **Issues: read GRANTED 2026-08-27 (mars S1630)** via console edit, verified 200 on issues-open; token value unchanged. **Checks: read CANNOT be granted**: the fine-grained PAT edit console exposes NO Checks permission for this org (form carries no `integration[default_permissions][checks]` field, verified S1630), while the API 403 on check-runs returns `x-accepted-github-permissions: checks=read`. RESOLVED S1631: this is a GitHub product limitation, not an org setting - GitHub removed the Checks permission from fine-grained PATs entirely; only GitHub App installation tokens can hold checks:read (github.com/orgs/community/discussions/129512, confirmed by GitHub staff). No org-settings action exists. Fix is on our side: drop check-runs from the adapter's expected resources (spec question, to design authority) or stand up a GitHub App if check-runs data is ever truly needed. Until then the watcher's check-runs feed renders `partial` honestly; CI-failure signal is fully carried by workflow-runs (actions: read, 200). This is the s1511 watcher's ONLY credential. | **2026-11-24** (renew before) | s1511 issue-channel watcher CI polling |
| `GITHUB_TOKEN`, `GITHUB_SECRETS_TOKEN` | ai-market-backend / prod | pre-existing backend integrations | see GitHub console | backend |
| gh CLI keyring (maxrobbins) | local keychain, not Infisical | fine-grained PAT (`github_pat_…`), NOT classic: it can push, open/merge PRs and comment, but has **no Administration and no Secrets permission** — deploy keys, repo/Actions secrets and branch protection all return `403 Resource not accessible by personal access token` (verified S1738) | n/a | Max interactive + operator probes only. NEVER wire into a service: shared-overbroad fails V-3-class credential review. |
| `GITHUB_ORG_ADMIN_TOKEN` | ai-market-backend / prod | fine-grained PAT with repository Administration + Secrets on `aidotmarket` (verified S1738: deploy keys, Actions secrets public key and branch protection all 200). Read it programmatically from `https://secrets.ai.market` and pass it as `GH_TOKEN` or a Bearer header inside one process; never echo it | see GitHub console | Operator admin steps Max has authorised: deploy keys, repo secrets, branch protection (first used S1732 provisioning, S1738), repository archive (S1790 `aidotmarket/aim-data`; the gh keyring PAT returns `Resource not accessible by personal access token (archiveRepository)`) |

### Minting a fine-grained org PAT (browser, S1612 lessons)

1. Open `https://github.com/settings/personal-access-tokens/new?target_name=aidotmarket` — the query param sets the resource owner directly; the owner SelectPanel's remote list intermittently fails to load.
2. Set name, repository access, and the needed permission (e.g. Actions → Read-only; Metadata is auto-added). Expiration LAST.
3. **Automation trap:** the expiration menu commits its value only on a real pointer-event sequence (pointerdown→mouseup→click). A synthetic `.click()` leaves hidden input `user_programmatic_access[default_expires_at]` blank or corrupted (observed value `Actions`), and submit fails with `Expiration date can't be blank`. Verify the hidden input reads the day count (e.g. `90`) before generating. A raw `form.submit()` bypasses the component serializer and silently creates nothing — always confirm the token appears in the list afterwards.
4. Store the one-time value straight into Infisical (correct project!), never in files, transcripts, or chat.

### Verifying scope after minting (safe, run within one shell, never echo the value)

- Positive read: `GET /repos/aidotmarket/<repo>/actions/runs?branch=main&per_page=1` → 200.
- Prohibited-write probe (harmless no-op even if wrongly permitted): `PUT /repos/aidotmarket/<repo>/actions/workflows/<id>/enable` on an already-enabled workflow → expect 403 `Resource not accessible by personal access token`. That error string is the normal fine-grained scope refusal, not an auth outage.
- Least-privilege probe: `GET .../contents/README.md` → 403 when Contents is not granted.

## Grafana Cloud tokens (S1786, 2026-10-01)

Grafana Cloud org `aimarket` (id `1670288`) runs on the **Free** plan. Its one stack, `aimarket` (id `1527021`), is in `prod-us-east-3`. On 2026-10-01 the stack showed about 760 active metric series against the free plan's 10,000. The grafana.com stack status read `paused`, which affects the hosted Grafana UI; metric ingestion and queries still worked.

Access policies, all scoped to `stack:1527021`:

| Policy | Scopes | Used by |
|---|---|---|
| `stack-1527021-otlp-write` | metrics/logs/traces/profiles write, metrics:import, alerts:write, rules:write | Backend OTLP export (`OTEL_EXPORTER_OTLP_HEADERS`) and root `GRAFANA_API_TOKEN`. It has **no read scope**, so `GRAFANA_API_TOKEN` queries return `authentication error: invalid scope requested`. |
| `connector-otlp-write` (`dadcb089…`) | metrics:write, traces:write | Token `connector-otlp-write-s1786b`, for the connector's own telemetry (Gate 4 Step 4) |
| `connector-alerting` (`ce43f25b…`) | metrics:read, rules:read/write, alerts:read/write | Token `connector-alerting-s1786b`, for installing and checking connector alert rules |

Both new tokens have no expiry. Mars chose that in S1786; Max did not direct it. They are rotated through the Step 4 procedure. Their values are only in `ai-market-backend`/`prod` folder **`/grafana-ops`**. No sync targets that folder, so its values never reach any service. A `prod` write can still trigger the existing syncs (see READ FIRST), so run the flag and value drift check before writing here. The 2026-10-01 ~08:46Z write produced no backend deployment, and the post-write check showed zero drift. The folder holds:

- `GRAFANA_CONNECTOR_OTLP_WRITE_TOKEN`
- `GRAFANA_CONNECTOR_ALERTING_TOKEN`
- `GRAFANA_STACK_ID` (`1527021`, the OTLP basic-auth user)
- `GRAFANA_PROM_INSTANCE_ID` (`2978270`, the Mimir basic-auth user)
- `GRAFANA_PROM_URL`
- `GRAFANA_ALERTMANAGER_URL`
- `GRAFANA_OTLP_ENDPOINT`

Do not copy these into a synced folder except through a reviewed Step 4 procedure.

**How they were made.** Mars minted them from Max's logged-in grafana.com browser session, by calling the grafana.com API from that tab:

- create the access policy: `POST /api/v1/accesspolicies?region=prod-us-east-3&orgId=1670288`;
- create the token: `POST /api/v1/tokens?…` with `accessPolicyId`. Token IDs: `connector-otlp-write-s1786b` is `3e09d908-2c33-4e03-bc91-a43ea2633d14`, `connector-alerting-s1786b` is `f90b02df-d9b2-4adf-a103-220b6847b04c`. Two earlier tokens whose values were not captured were deleted;
- send an `X-Request-Id` header (a random UUID) on every write, or the API returns 403 `Missing Request ID`;
- read the secret from the response field `token`; it is shown only once.

**Verify (names only, never echo the value).** Run a Mimir query with basic auth `GRAFANA_PROM_INSTANCE_ID`:`GRAFANA_CONNECTOR_ALERTING_TOKEN` against `GRAFANA_PROM_URL/api/prom/api/v1/query?query=count by (service_name) (target_info)`. On 2026-10-01 it returned 200 with `service_name="ai-market-backend"`, and `/api/prom/rules` returned 200 `{}`.

**Revoke.** `DELETE /api/v1/tokens/<id>?region=prod-us-east-3&orgId=1670288`, or use the Access Policies page.

## Failure signatures (S1612 additions)

| Symptom | Cause | Fix |
|---|---|---|
| `403 TokenError "invalid signature"` on Infisical API calls | Calling **app.infisical.com** — our instance is self-hosted at **`https://secrets.ai.market`** (see header). The sysadmin token at `~/.config/infisical/sysadmin-token` is valid for the self-hosted host only. | Use `https://secrets.ai.market/api/v3/secrets/raw?...` with the workspace IDs in Quick Reference. Do not "refresh" the token; it is not expired. |
| `v3/secrets/raw` returns 404 `Secret ... not found` for a secret you just stored | Wrong project: secrets are per-workspace (backend / frontend / koskadeux-mcp), and a secret stored via the UI lands in whichever project was selected. | Search all three workspace IDs from Quick Reference before concluding the secret is missing. |
| GitHub API `Resource not accessible by personal access token` | Fine-grained PAT lacks that permission — expected on scope probes | Only escalate if it appears on an operation the token is documented to allow. |
| GitHub `422 Deploy keys are disabled for this repository` when adding a deploy key | The org setting `deploy_keys_enabled_for_repositories` (Org settings → Member privileges → Deploy keys) is off. It was off until Max enabled it on 2026-09-23 (S1738) | Only Max changes it (org security setting). Check with `GET /orgs/aidotmarket` → `deploy_keys_enabled_for_repositories` |
| A deploy key created with `read_only:true` accepts a push in the first minutes | Observed S1738: one push ~2 minutes after creation landed; every later probe was refused with `ERROR: The key you are authenticating with has been marked as read only` | Repeat the write-refusal probe until it refuses and delete any probe ref; record the time since key creation |
| HTTP 403 `error code: 1010` from `secrets.ai.market` with default `Python-urllib/3.x` User-Agent | Cloudflare browser integrity check, not a token or permission failure | Send a fixed tool User-Agent. |
| HTTP 500 with `FST_ERR_CTP_EMPTY_JSON_BODY` on a bodiless POST such as `/api/v1/secret-syncs/railway/{id}/sync-secrets` | `Content-Type: application/json` was sent with no body | Omit `Content-Type` when there is no body. |
| `Infisical sync recursion setting unknown or enabled` | Infisical readback omits `includeAllSubFolders: false` for both recorded syncs | Treat omission as non-recursive only for the pinned root and connector sync shapes proven by the `/connector-auth` canary. Refuse other unknown or enabled shapes. Canonical index entry: customer-mcp-connector.md. See [customer-mcp-connector.md](customer-mcp-connector.md). |

### Reading Infisical server logs

For read-only diagnosis, Infisical runs on Railway project `fe02d729-5921-4199-8e6a-2e026acc1326` (`infisical secrets-management`), with services `Infisical`, `Postgres`, `Redis`, and `ai-market-backend`. In a scratch directory, run `railway link -p fe02d729-5921-4199-8e6a-2e026acc1326 -e production`, then `railway logs --service Infisical --lines 400`. Search by time or request ID. Never print secret values.

## When it breaks

Use Emergency Recovery, Known Gotchas, and Failure signatures above when secret access or rotation fails.
