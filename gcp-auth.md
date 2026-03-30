# GCP Auth

## What it does

Manages Google Cloud authentication for Gmail API (morning briefing, drop pipeline, draft sending) and Pub/Sub.

## Accounts

| Account | Used for |
|---------|----------|
| `max@ai.market` | Production GCP project (`aimarket-prod`) — Gmail API, Pub/Sub |
| `maxdrobbins@gmail.com` | Personal GCP (no access to aimarket-prod) |

## OAuth Consent Screen — MUST BE "Internal"

The GCP OAuth app (`aimarket-prod`) controls refresh token lifetime for the Gmail API. This is critical.

| Setting | Required Value | Why |
|---------|---------------|-----|
| **User Type** | **Internal** | Internal apps get non-expiring refresh tokens. External/Testing apps expire tokens after 7 days, silently breaking the morning briefing, Gmail drop pipeline, and draft sending. |

**How to verify/fix:**
1. Go to [GCP Console > OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent?project=aimarket-prod)
2. Confirm **User Type = Internal**
3. If it says "External" or "Testing", click **MAKE INTERNAL** (or edit and change)

This is the single most important setting. If it's wrong, everything Gmail-related breaks silently after 7 days.

**Who can authorize:** Only users in the `ai.market` Google Workspace domain (max@ai.market, ally@ai.market). This is all we need.

## Gmail OAuth Tokens

The backend stores Gmail refresh tokens in the `gmail_tokens` table (Railway Postgres). These tokens are used by `GmailService` to send emails (briefings, drafts) and by `GmailWatchService` to monitor the inbox (drop pipeline).

| Email | Purpose |
|-------|---------|
| `max@ai.market` | Sending briefings, reading inbox for drop pipeline |
| `ally@ai.market` | Sending outbound emails (drafts, outreach) |

**If tokens need refreshing** (only happens if consent screen is NOT Internal):
```bash
cd ~/Projects/ai-market/ai-market-backend
# Secrets now sourced from Infisical / Railway env vars
python3 scripts/setup_gmail_auth.py  # Uses GOOGLE_OAUTH_CREDENTIALS_JSON from Railway env
```
Then push the new token to Railway DB (setup script can't reach `postgres.railway.internal` from Titan-1):
```bash
echo "UPDATE gmail_tokens SET refresh_token = '<NEW_TOKEN>', updated_at = NOW() WHERE email_address IN ('max@ai.market', 'ally@ai.market');" | railway connect Postgres
```
Then redeploy to renew the Gmail watch:
```bash
cd ~/Projects/ai-market/ai-market-backend && railway redeploy --yes
```

## gcloud CLI Auth

Separate from Gmail OAuth. Used for Pub/Sub management, GCP admin tasks.

```bash
gcloud auth login --account=max@ai.market
gcloud config set project aimarket-prod
```

This requires interactive browser login — Vulcan cannot do it headlessly.

## Verify setup

```bash
gcloud auth list                    # Check active account
gcloud config get-value project     # Should be: aimarket-prod
gcloud pubsub topics list           # Should show gmail-push
gcloud pubsub subscriptions list    # Should show gmail-push-sub
```

## GCP Resources

| Resource | Details |
|----------|--------|
| Project | `aimarket-prod` (number: `240358013785`) |
| Organization | `1062465481671` (ai.market Workspace) |
| OAuth Client ID | `240358013785-dip4sn1ki9ti66m02u50ditbghrj0uls.apps.googleusercontent.com` |
| Pub/Sub Topic | `gmail-push` |
| Pub/Sub Subscription | `gmail-push-sub` → `https://api.ai.market/api/v1/webhooks/gmail` |

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Morning briefing stops | Gmail refresh token expired (consent screen is External/Testing) | Set consent screen to Internal, then re-auth |
| Drop pipeline stops | Same as above | Same fix |
| "Reauthentication failed" in gcloud | gcloud session expired | `gcloud auth login --account=max@ai.market` in terminal |
| "does not have permission" | Wrong gcloud account active | `gcloud config set account max@ai.market` |
| Wrong project | gcloud pointed at wrong project | `gcloud config set project aimarket-prod` |

## History

- **S341:** Discovered consent screen was "External/Testing" causing 7-day token expiry. Documented requirement for "Internal" setting. Updated runbook with full Gmail OAuth recovery procedure.
