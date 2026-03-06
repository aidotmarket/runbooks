# Marketing Tab (ops.ai.market)

## What it does

The Marketing tab in ops.ai.market displays the marketing plan with tasks, timelines, and progress. Seeded from real Excel data (March 2026 plan).

## How it works

```
Excel data (March 2026 marketing plan)
  → Seeded into backend via API
  → ops.ai.market Marketing tab renders tasks
  → Auto-generated tasks use skip endpoint (not delete)
  → Manual tasks can be created/edited in UI
```

## Key files

| File | Purpose |
|------|--------|
| `app/api/v1/endpoints/marketing.py` | Marketing API |
| ops-ai-market repo | Dashboard frontend |

## Access

- URL: https://ops.ai.market
- Navigate to Marketing tab

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Marketing tab empty | Seed data not loaded | Re-run seed endpoint |
| Tasks not updating | Backend deploy needed | Check Railway deploys |
| Auto-generated tasks reappearing | Using delete instead of skip | Use skip endpoint |

## Security note from audit

M16: Marketing seed endpoint (`/api/v1/marketing/admin/seed`) accessible to any authenticated user, not just admins. Needs fix to use `get_admin_or_internal_key`.
