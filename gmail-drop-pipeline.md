# Gmail Drop Pipeline

## What it does

Emails sent to `drop@ai.market` are automatically ingested into the CRM. A new contact is created (or matched to existing), the email is logged as an interaction, and an LLM generates a summary.

## How it works

```
Email arrives at drop@ai.market
  → Gmail API users.watch() detects inbox change
  → Gmail publishes to GCP Pub/Sub topic: projects/aimarket-prod/topics/gmail-push
  → Push subscription POSTs to: https://api.ai.market/api/v1/webhooks/gmail
  → Backend webhook handler:
    1. Decodes Pub/Sub message (base64 historyId)
    2. Fetches new messages via Gmail API
    3. Extracts sender email, subject, body
    4. CRM upsert: creates contact if new, matches if existing
    5. Logs interaction (type: email) against the contact
    6. LLM summarizes the email content
    7. Stores summary in interaction record
```

## Key files

| File | Purpose |
|------|--------|
| `app/api/v1/endpoints/gmail_webhook.py` | Webhook endpoint |
| `app/services/gmail_watch_service.py` | Gmail watch setup and renewal |
| `app/services/gmail_service.py` | Gmail API client |
| `app/api/webhooks.py` | Webhook routing |
| `app/core/config.py` | `GMAIL_TOPIC_NAME`, `GCP_PROJECT_ID` |

## Configuration

| Variable | Location | Value |
|----------|----------|-------|
| `GMAIL_TOPIC_NAME` | Doppler (prd) | `projects/aimarket-prod/topics/gmail-push` |
| `GCP_PROJECT_ID` | Doppler (prd) | `aimarket-prod` |
| Gmail OAuth tokens | Database (`gmail_tokens` table) | Auto-refreshed |

## GCP Resources

| Resource | Details |
|----------|--------|
| Project | `aimarket-prod` |
| Topic | `gmail-push` |
| Subscription | `gmail-push-sub` (push to `https://api.ai.market/api/v1/webhooks/gmail`, 60s ack) |
| Auth account | `max@ai.market` |

## Gmail watch renewal

Gmail watches expire after 7 days. The scheduler (`app/core/scheduler.py`) calls `renew_all_watches()` daily to keep them alive.

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

3. **Test the pipeline:** Send an email to `drop@ai.market` and check CRM for new contact/interaction within 1-2 minutes.

4. **Check Gmail watch is active:** Look at scheduler logs or call `renew_all_watches()` manually.

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Emails not appearing in CRM | Gmail watch expired | Trigger `renew_all_watches()` |
| Pub/Sub 403 errors | GCP auth token expired | `gcloud auth login --account=max@ai.market` |
| Webhook returning 500 | Railway deploy issue | Check Railway logs for ai-market-backend |
| "GMAIL_TOPIC_NAME not configured" | Doppler var missing | Check Doppler prd config |
| New emails not detected | historyId gap | Stop and re-create watch |

## Built

S222 — commit `f85c77e`. Verified S223 (Pub/Sub subscription confirmed).
