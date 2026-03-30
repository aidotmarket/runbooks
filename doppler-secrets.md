# Doppler Secrets Management

> **⚠️ DEPRECATED** — Doppler is no longer the source of truth for secrets.
> Replaced by self-hosted Infisical as of S357 (2026-03-30).
> See `infisical-secrets.md` for the current runbook.
> Doppler retains a frozen snapshot of secrets but should NOT be updated.

---

## What it was

All secrets and API keys for ai.market were stored in Doppler. This has been replaced by self-hosted Infisical at https://secrets.ai.market.

## Configs (archived)

| Config | Where used |
|--------|----------|
| `prd` | Railway production (ai-market-backend) |
| `dev_personal` | Titan-1 local development |
| `dev` | Local development |

## Common operations (for reference only)

```bash
# View a secret
doppler secrets get SECRET_NAME --config prd --project ai-market

# List all secrets
doppler secrets --config prd --project ai-market
```
