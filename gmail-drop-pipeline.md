# Gmail Drop Pipeline

## What it does

Emails cc'd or sent to `drop@ai.market` are automatically ingested into the CRM. A new contact is created (or matched to existing), the email is logged as an interaction, and an LLM generates a summary.

## Gmail Filter (in max@ai.market settings)

There is a Gmail filter rule that must remain in place:

| Matches | Action |
|---------|--------|
| `to:(drop@ai.market)` | Skip Inbox, Apply label "CRM-Drop" |

This filter ensures drop emails don't clutter the inbox. The pipeline still picks them up because the Gmail watch monitors ALL mailbox changes (no `labelIds` filter), not just inbox changes.

**IMPORTANT:** If this filter is deleted, drop emails will land in the inbox instead of being labeled. The pipeline will still work, but the inbox will get noisy.

## How it works

```
Email arrives at drop@ai.market (cc or direct)
  → Gmail filter: skip inbox, apply "CRM-Drop" label
  → Gmail watch (users.watch, NO labelIds filter) detects mailbox change
  → Gmail publishes to GCP Pub/Sub topic: projects/aimarket-prod/topics/gmail-crm-drop
  → Push subscription POSTs to: https://api.ai.market/api/v1/webhooks/gmail
  → Backend webhook handler:
    1. Decodes Pub/Sub message (base64 historyId)
    2. Fetches new messages via Gmail API (historyTypes=messageAdded)
    3. Checks if drop@ai.market is in To/CC addresses
    4. Routes to EmailIngestService for CRM processing
    5. CRM upsert: creates contact if new, matches if existing
    6. Logs interaction (type: email) against the contact
    7. LLM summarizes the email content
    8. Stores summary in interaction record
```

## Key files

| File | Purpose |
|------|---------|
| `app/api/v1/endpoints/gmail_webhook.py` | Webhook endpoint |
| `app/services/gmail_watch_service.py` | Gmail watch setup, renewal, and notification processing |
| `app/services/gmail_service.py` | Gmail API client (auth, fetch, send) |
| `app/services/email_ingest_service.py` | CRM contact upsert + interaction logging |
| `app/api/webhooks.py` | Webhook routing |
| `app/core/config.py` | `GMAIL_TOPIC_NAME`, `GCP_PROJECT_ID` |

## Configuration

| Variable | Location | Value |
|----------|----------|-------|
| `GMAIL_TOPIC_NAME` | Railway env var | `projects/aimarket-prod/topics/gmail-crm-drop` |
| `GCP_PROJECT_ID` | Railway env var | `aimarket-prod` |
| Gmail OAuth tokens | Database (`gmail_tokens` table) | Refresh token auto-refreshes access token |
| Gmail filter | Gmail settings > Filters | `to:(drop@ai.market)` → Skip Inbox, label "CRM-Drop" |

## GCP Resources

| Resource | Details |
|----------|---------|
| Project | `aimarket-prod` |
| Topic | `gmail-crm-drop` |
| Subscription | `gmail-crm-drop-sub` (push to `https://api.ai.market/api/v1/webhooks/gmail`, 60s ack) |
| Auth account | `max@ai.market` |

## Gmail watch renewal

Gmail watches expire after 7 days. The scheduler (`app/core/scheduler.py`) calls `renew_all_watches()` daily to keep them alive. The watch is also renewed on app startup (`_gmail_watch_startup` in `main.py`).

## OAuth tokens and the GCP "Testing" problem

The GCP OAuth app (`aimarket-prod`) may still be in "Testing" mode. In testing mode, **refresh tokens expire after 7 days**. This silently kills both this pipeline AND the morning briefing.

**Permanent fix:** Publish the GCP OAuth app to "Production" in the [GCP Console OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent?project=aimarket-prod). Production apps get refresh tokens that don't expire (unless manually revoked).

**If tokens expire (manual re-auth required):**
```bash
cd ~/Projects/ai-market/ai-market-backend
python3 scripts/setup_gmail_auth.py  # secrets loaded from Railway env vars
```
This opens a browser for Google consent. The script saves the new refresh token, but it connects to `postgres.railway.internal` which isn't reachable from Titan-1. Push the token to Railway DB manually:
```bash
echo "UPDATE gmail_tokens SET refresh_token = '&lt;NEW_TOKEN&gt;', updated_at = NOW() WHERE email_address IN ('max@ai.market', 'ally@ai.market');" | railway connect Postgres
```
Then redeploy to renew the watch:
```bash
railway redeploy --yes
```

## How to verify

1. **Check Pub/Sub subscription exists:**
   ```bash
   gcloud config set account max@ai.market
   gcloud config set project aimarket-prod
   gcloud pubsub subscriptions list
   ```

2. **Check webhook endpoint is live:**
   ```bash
   curl -s https://api.ai.market/health
   ```

3. **Test the pipeline:** CC `drop@ai.market` on an email and check CRM for new contact/interaction within 1-2 minutes.

4. **Check Gmail watch is active:** Look at scheduler logs or trigger a redeploy (watch renews on startup).

5. **Check Gmail filter:** Gmail settings > Filters > verify `to:(drop@ai.market)` → Skip Inbox, Apply label "CRM-Drop".

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Emails not appearing in CRM | Gmail OAuth refresh token expired (7-day expiry in Testing mode) | Re-run `setup_gmail_auth.py`, push token to Railway DB, redeploy |
| Emails not appearing in CRM | Gmail watch expired | Redeploy backend (watch renews on startup) |
| Emails not appearing in CRM | Gmail filter deleted | Re-create filter in Gmail settings: `to:(drop@ai.market)` → Skip Inbox, Apply "CRM-Drop" |
| Pub/Sub 403 errors | GCP auth token expired | `gcloud auth login --account=max@ai.market` |
| Webhook returning 500 | Railway deploy issue | Check Railway logs for ai-market-backend |
| "GMAIL_TOPIC_NAME not configured" | Railway env var missing | Check Railway service variables |
| New emails not detected | historyId gap | Stop and re-create watch (redeploy) |

## History of breakage

- **S222:** Built. Verified S223 (Pub/Sub subscription confirmed).
- **S341:** Pipeline down for days. Root cause: GCP OAuth refresh token expired (app in Testing mode). Fixed by re-running setup_gmail_auth.py and pushing token to Railway DB. Runbook updated to document Gmail filter, OAuth expiry, and manual token refresh procedure.
- **S361:** Topic renamed from `gmail-push` to `gmail-crm-drop`. GMAIL_TOPIC_NAME set in Railway. Watch activated S360.

## Built

S222 — commit `f85c77e`. Verified S223 (Pub/Sub subscription confirmed).
Updated S341 — documented Gmail filter, OAuth token expiry, and recovery procedure.
Updated S360 — corrected topic/subscription names to `gmail-crm-drop`.
