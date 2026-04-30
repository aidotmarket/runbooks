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

## Vertex AI / Gemini (S533)

The application uses Vertex AI for Gemini embeddings (`gemini-embedding-001`) and chat (`gemini-2.5-flash`). As of S533, **auth is via Vertex AI Express API key**, not service-account ADC.

| Aspect | Value |
|---|---|
| Auth model | Vertex Express API key |
| Key prefix | `AQ.` (legacy Developer API was `AIza...`) |
| Project scope | Key is bound to a GCP project at creation; no `project=` or `location=` parameter required at SDK construction |
| Settings field | `VERTEX_GEMINI_KEY: SecretStr` in `app.core.config.Settings` |
| Pydantic case sensitivity | `SettingsConfigDict(case_sensitive=True)` — env var name MUST match field exactly |
| Canonical env var name | `VERTEX_GEMINI_KEY` (uppercase, no aliases permitted in production code) |

### SDK construction

```python
from google import genai
from google.genai.types import EmbedContentConfig

client = genai.Client(vertexai=True, api_key=settings.VERTEX_GEMINI_KEY.get_secret_value())

# Embeds: output_dimensionality is MANDATORY — default is 3072, qdrant collection is smaller
resp = client.models.embed_content(
    model='gemini-embedding-001',
    contents='...',
    config=EmbedContentConfig(output_dimensionality=settings.LLM_EMBEDDING_DIMENSIONS),
)
```

### Verification

```bash
infisical secrets get VERTEX_GEMINI_KEY \
  --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c \
  --env prod --plain --silent --domain https://secrets.ai.market \
  | head -c 4
# Expect: AQ.A   (anything else is wrong)
```

### When it breaks

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 UNAUTHENTICATED — ACCESS_TOKEN_TYPE_UNSUPPORTED` | Wrong key type passed (OAuth token, Developer API key) | Verify prefix is `AQ.`. Re-create in GCP Console → Credentials → API Keys, scoped to Vertex AI API |
| `401 UNAUTHENTICATED` on AG dispatches | AG reads `VERTEX_API_KEY` (separate Infisical secret); value drift after rotation | Sync `VERTEX_API_KEY` value to match `VERTEX_GEMINI_KEY`, restart `ag_server`. Long-term: consolidate to one canonical name |
| `embed` returns 3072-dim vectors causing qdrant upsert failures | Code path forgot `EmbedContentConfig(output_dimensionality=...)` | Every embed call must pass `output_dimensionality=settings.LLM_EMBEDDING_DIMENSIONS` |
| `invalid_grant: Invalid JWT Signature` (legacy SA path) | Service-account private key in Infisical rejected by GCP. Resolved S533 by switching to API-key auth — SA path no longer used for Gemini | Do not rotate SA for Gemini; SA cleanup is independent (P3 follow-up `BQ-VERTEX-SA-IAM-HARDENING`) |

### Legacy: Service-account ADC (no longer used for Gemini)

The codebase still uses `GCP_SERVICE_ACCOUNT_JSON` ADC bootstrap at `app/core/gcp_credentials.py:56` and `app/main.py:327` for non-Gemini GCP services (KMS, GCS). The S533 finding that the Infisical-stored SA private key is rejected by GCP (`invalid_grant: Invalid JWT Signature`) does not affect Gemini auth and is tracked separately under `BQ-VERTEX-SA-IAM-HARDENING` (P3).
