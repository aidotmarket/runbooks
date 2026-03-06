# CRM Pipeline

## What it does

Manages all contacts, organizations, interactions, and tasks for ai.market business relationships. Max interacts via Telegram, Vulcan interacts via MCP tools.

## How it works

### Telegram path (Max → CRM)
```
Max sends message to Telegram bot
  → CRM Steward agent classifies intent
  → Routes to handler: add prospect, draft email, log note, search
  → Executes against CRM API
  → Returns confirmation to Telegram
```

### Vulcan path (sessions → CRM)
```
Vulcan uses MCP tools directly:
  crm_create_contact, crm_upsert_contact
  crm_get_contact_360
  crm_log_interaction
  crm_create_task, crm_cancel_task, crm_update_task
  crm_search_interactions
```

## Key files

| File | Purpose |
|------|--------|
| `app/allai/agents/crm_steward.py` | Telegram-driven CRM agent |
| `app/api/v1/endpoints/crm.py` | CRM API endpoints |
| `app/services/crm_service.py` | Business logic |
| `app/models/crm.py` | Database models |

## API endpoints

All at `/api/v1/crm/`:
- People CRUD, organizations, relationships
- Interaction logging (email, call, note, social, whatsapp)
- Task management (create, pending, overdue, complete)
- Draft generation, approval, sending
- Entity network/relationship graph

## Daily maintenance (automated)

- Stale contact detection: 180+ days since last interaction
- Pipeline hygiene: 30+ days stuck in same stage
- Conversation state in Redis with Postgres backup

## MCP tools reference

| Tool | Use for |
|------|--------|
| `crm_create_contact` | New person |
| `crm_upsert_contact` | Create or update by email match |
| `crm_get_contact_360` | Full context before outreach |
| `crm_log_interaction` | Record email/call/note |
| `crm_search_interactions` | Find person by name/email + history |
| `crm_create_task` | Schedule follow-up |
| `crm_cancel_task` | Mark done/cancelled |
| `crm_update_task` | Reschedule |

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `crm_create_task` returns 500 | FK constraint or missing entity | Check entity_id exists, check Railway logs |
| Telegram bot not responding | CRM steward process down | Check Railway service health |
| Duplicate contacts | Email not matching | Use `crm_upsert_contact` instead of create |
| Stale data in 360 view | Redis cache | Wait for TTL or flush manually |

## Known bugs

- CRM task creation 500 error (hit during S222 for Leo @ Wayy follow-up task)
