# Morning Briefing

## What it does

Sends a daily CRM briefing email to max@ai.market at 08:00 CET (07:00 UTC). Contains overdue tasks, pending tasks, recent activity, and action links per contact.

## How it works

Two paths to send a briefing:

### 1. Daily timer (automatic)
```
Railway (ai-market-backend) boots
  → CRM Steward agent starts via AgentHost
  → asyncio _daily_timer_loop() waits until 07:00 UTC
  → Calls CRMBriefingService.send_daily_briefing() DIRECTLY (no event bus)
  → Sends via Gmail API (OAuth token from gmail_tokens table)
  → Pings Healthchecks.io
```

### 2. Manual trigger (event-driven)
```
POST /api/v1/crm/admin/send-briefing
  → Publishes CRM_MANUAL_BRIEFING event (source: crm.admin.send_briefing)
  → Event goes through EventBus → priority streams → routing policy
  → CRM Steward handles via _handle_manual_briefing()
  → Calls CRMBriefingService.send_daily_briefing()
  → Sends via Gmail API
```

**IMPORTANT:** The manual path goes through the routing policy auth gate. The source `crm.admin.send_briefing` must be whitelisted in `_SOURCE_EVENT_TYPE_ALLOW` in `app/allai/routing_policy.py`. Without this, the event gets dead-lettered as "unauthorized".

## Key files

| File | Purpose |
|------|---------|
| `app/allai/agents/crm_steward.py` | `_daily_timer_loop()` fires at 07:00 UTC (automatic path) |
| `app/allai/agents/crm_steward.py` | `_handle_manual_briefing()` handles CRM_MANUAL_BRIEFING event (manual path) |
| `app/services/crm_briefing_service_gmail.py` | Gmail-based briefing generator + sender |
| `app/services/crm_briefing_service.py` | Legacy Postmark-based version (DO NOT USE — Postmark not configured) |
| `app/allai/routing_policy.py` | `_SOURCE_EVENT_TYPE_ALLOW` — must include `crm.admin.send_briefing` |
| `app/allai/agent_host.py` | AgentHost — must register agents (0 agents = no briefing) |
| `app/main.py` | Agent registration block — Python scoping bugs here kill all agents |

## Critical: Agent registration

CRM Steward MUST be running for either briefing path to work. Check Railway logs for:
- `AgentHost: Started - N agents active` (N must be > 0, expect 7+)
- If `0 agents active`, check `app/main.py` for import scoping issues (S341 bug: local imports shadowing module-level imports)

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
  -H "X-Internal-API-Key: <key from ~/koskadeux-mcp/.env>" \
  -d '{}'
```

This publishes a CRM_MANUAL_BRIEFING event that CRM Steward handles via `_handle_manual_briefing()`.

## When it breaks — diagnostic checklist

Check in this order:

| # | Check | How | Fix |
|---|-------|-----|-----|
| 1 | Are agents running? | Railway logs: `AgentHost: Started - N agents active` | If 0, check `app/main.py` for import bugs |
| 2 | Is CRM Steward registered? | Railway logs: grep for `crm-steward` | If missing, check `app/allai/agents/__init__.py` |
| 3 | Is the routing policy blocking manual triggers? | Railway logs: `unauthorized event type crm.manual_briefing` | Add source to `_SOURCE_EVENT_TYPE_ALLOW` in `routing_policy.py` |
| 4 | Are Gmail OAuth tokens valid? | GCP consent screen = Internal? Token updated recently? | See `gcp-auth.md` for re-auth procedure |
| 5 | Was Railway redeployed after 07:00 UTC? | Check Railway deploy time vs 07:00 UTC | Manually trigger or wait for next day |
| 6 | Wrong import (Postmark vs Gmail)? | Check `crm_steward.py` imports | Must be `crm_briefing_service_gmail` |
| 7 | Briefing sent but empty? | No CRM tasks | Working as intended |

## Routing policy details

The manual trigger source `crm.admin.send_briefing` must be whitelisted in:
- File: `app/allai/routing_policy.py`
- Dict: `_SOURCE_EVENT_TYPE_ALLOW`
- Entry: `"crm.admin.send_briefing": {"crm.manual_briefing"}`

The `check_source_authorization()` method also needs a raw-source fallback for non-agent sources (dotted sources like `crm.admin.send_briefing` return `None` from `_source_to_agent_key()`).

## History of breakage

- **S85-S97:** Briefing stopped — removed from scheduler, never wired to agent
- **S103:** Fixed — wired into CRM Steward daily timer at 07:00 UTC
- **S124:** Broke during backend service stripping — fixed via manual trigger
- **S226:** Broke again — CRM Steward was importing Postmark service instead of Gmail service. Fixed by switching import.
- **S341:** Briefing stopped for days. Three compounding failures:
  1. GCP OAuth consent screen was "External/Testing" → 7-day token expiry → Gmail send silently failed
  2. Python scoping bug in `main.py` → 0 agents registered → CRM Steward never started → daily timer never ran
  3. Routing policy blocked manual trigger → `crm.admin.send_briefing` source not whitelisted → event dead-lettered
  Fixed all three. Permanent fix: consent screen set to Internal, scoping bug fixed (commit `53c942c`), routing policy updated.
