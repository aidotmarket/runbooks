# Morning Briefing

## What it does

Sends a daily CRM briefing email to max@ai.market at 08:00 CET (07:00 UTC). Contains overdue tasks, pending tasks, recent activity, and action links per contact.

## How it works

```
Railway (ai-market-backend) boots
  → CRM Steward agent starts
  → asyncio timer loop waits until 07:00 UTC
  → Calls CRMBriefingService.send_daily_briefing()
  → Generates HTML briefing from CRM data
  → Sends via Gmail API (max@ai.market OAuth token from gmail_tokens table)
  → Pings Healthchecks.io
```

## Key files

| File | Purpose |
|------|---------|
| `app/allai/agents/crm_steward.py` | `_daily_timer_loop()` fires at 07:00 UTC |
| `app/services/crm_briefing_service_gmail.py` | Gmail-based briefing generator + sender |
| `app/services/crm_briefing_service.py` | Legacy Postmark-based version (DO NOT USE — Postmark not configured) |

## Critical: Import path

The CRM Steward MUST import from the **Gmail** service:
```python
from app.services.crm_briefing_service_gmail import CRMBriefingService
```

NOT the Postmark version:
```python
# WRONG — Postmark API key is not set, silently fails
from app.services.crm_briefing_service import CRMBriefingService
```

## Critical: GCP OAuth consent screen

The Gmail API refresh tokens are stored in the `gmail_tokens` table (Railway Postgres). If the GCP OAuth consent screen is set to "External/Testing", these tokens **expire after 7 days** and the briefing silently stops sending.

**Required setting:** GCP OAuth consent screen must be **Internal** (not External/Testing).

See `gcp-auth.md` for full details on verification and recovery.

## Manual trigger

```bash
curl -X POST "https://ai-market-backend-production.up.railway.app/api/v1/crm/admin/send-briefing" \
  -H "Content-Type: application/json" \
  -H "X-Internal-API-Key: <key from Doppler>" \
  -d '{}'
```

This publishes a CRM_MANUAL_BRIEFING event that CRM Steward handles via `_handle_manual_briefing()`.

The internal API key is: check `INTERNAL_API_KEY` in Doppler (ai-market, prd) or in `~/koskadeux-mcp/.env`.

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| No briefing received | Gmail OAuth refresh token expired (consent screen is External/Testing) | Set consent screen to Internal (see `gcp-auth.md`), then re-auth and push token |
| No briefing received | Railway redeployed after 07:00 UTC | Timer resets on deploy. Manually trigger or wait for next day |
| No briefing received | Wrong import (Postmark instead of Gmail) | Check `crm_steward.py` imports point to `crm_briefing_service_gmail` |
| No briefing received | CRM Steward not starting | Check Railway logs for agent startup errors |
| Briefing has stale data | Redis cache | Clear CRM cache or wait for TTL |
| Briefing sent but empty | No CRM tasks | Working as intended — briefing only shows active tasks |

## History of breakage

- **S85-S97:** Briefing stopped — removed from scheduler, never wired to agent
- **S103:** Fixed — wired into CRM Steward daily timer at 07:00 UTC
- **S124:** Broke during backend service stripping — fixed via manual trigger
- **S226:** Broke again — CRM Steward was importing Postmark service instead of Gmail service. Fixed by switching import.
- **S341:** Briefing stopped for days. Root cause: GCP OAuth consent screen was "External/Testing", causing 7-day refresh token expiry. Gmail send silently failed. Fixed by refreshing tokens and pushing to Railway DB. Runbook updated. Permanent fix: set consent screen to Internal.
