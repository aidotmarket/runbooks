# Doppler Secrets Management

## What it does

All secrets and API keys for ai.market are stored in Doppler. Never hunt in `.env` files or hardcode tokens.

## Configs

| Config | Where used |
|--------|----------|
| `prd` | Railway production (ai-market-backend) |
| `dev_personal` | Titan-1 local development |
| `dev` | Local development |

## Project

```bash
doppler projects  # Lists: ai-market, example-project
```

## Common operations

```bash
# View a secret
doppler secrets get SECRET_NAME --config prd --project ai-market

# Set a secret
doppler secrets set SECRET_NAME=value --config prd --project ai-market

# List all secrets
doppler secrets --config prd --project ai-market
```

## Key secrets

| Secret | Purpose |
|--------|--------|
| `INTERNAL_API_KEY` | Internal API auth (ROTATE — see audit C1) |
| `SECRET_KEY` | JWT signing |
| `STRIPE_SECRET_KEY` | Stripe API |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification |
| `OPENAI_API_KEY` | MP / GPT API |
| `ANTHROPIC_API_KEY` | allAI proxy |
| `GMAIL_TOPIC_NAME` | GCP Pub/Sub topic for Gmail |
| `GCP_PROJECT_ID` | GCP project |
| `DOWNLOAD_TOKEN_SECRET_KEY` | VZ download token signing |

## When it breaks

| Symptom | Fix |
|---------|-----|
| "Secret not found" | Check project name (`ai-market`, not `ai-market-backend`) |
| Railway not picking up changes | Railway auto-syncs from Doppler — redeploy if stuck |
| Local dev missing secrets | `doppler run -- python ...` or check `dev_personal` config |
