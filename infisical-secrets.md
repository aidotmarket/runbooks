# Infisical Secrets Management

> **Deployed**: S357 (2026-03-30)
> **URL**: https://secrets.ai.market
> **Railway Project**: `fe02d729-5921-4199-8e6a-2e026acc1326`
> **Replaces**: Doppler (demoted to archive-only, see `doppler-secrets.md`)

## Quick Reference

| Resource | ID |
|---|---|
| Organization | `cba08a81-6af0-409c-a405-f4328e5dbc66` |
| ai-market-backend | `bd272d48-c5a1-4b52-9d24-12066ae4403c` |
| ai-market-frontend | `1c0589a5-0634-4d06-ac4d-56d0e83af3cf` |
| koskadeux-mcp | `0943f641-faee-4324-b337-0d50c276e4a9` |
| SysAdmin Identity | `62f1bfac-3e07-4f4e-b15d-42f1bbcc9f5e` |

## Environments

Each project has three environments: `dev`, `staging`, `prod`.

## SMTP Configuration

SMTP is configured via Resend for outbound email (invites, MFA codes, notifications).

| Variable | Value |
|---|---|
| `SMTP_HOST` | smtp.resend.com |
| `SMTP_PORT` | 587 |
| `SMTP_SECURE` | false (STARTTLS) |
| `SMTP_FROM_ADDRESS` | noreply@ai.market |
| `SMTP_FROM_NAME` | ai.market |
| `SMTP_USERNAME` | resend |
| `SMTP_PASSWORD` | (Resend API key — stored in Railway env vars) |

**Status**: MFA and email invites are now available.

## Accessing Secrets

### Web Dashboard
Navigate to https://secrets.ai.market and log in with your admin account.

### CLI
```bash
export INFISICAL_API_URL=https://secrets.ai.market
infisical login --domain=https://secrets.ai.market

# List secrets
infisical secrets --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=prod

# Export to .env
infisical export --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=prod --format=dotenv > .env

# Inject into a process
infisical run --projectId=bd272d48-c5a1-4b52-9d24-12066ae4403c --env=dev -- python app.py
```

### API (Machine Identity)
```bash
# Authenticate with machine identity token
curl -s "https://secrets.ai.market/api/v3/secrets/raw?workspaceId=<PROJECT_ID>&environment=prod&secretPath=/" \
  -H "Authorization: Bearer <TOKEN>"
```

## Machine Identities

### sysadmin-agent
- **Purpose**: SysAdmin AI agent automated access
- **Auth**: Token Auth (non-expiring)
- **Scope**: Admin on all 3 projects
- **Token location**: Titan-1 `/Users/max/.config/infisical/sysadmin-token`

## Secret Rotation

1. Update the secret in Infisical dashboard or API
2. If the secret is also in Railway env vars, update there too: `railway variables set KEY=VALUE`
3. Railway env vars remain the deploy-time injection source — Infisical is the source of truth for humans and agents

## Emergency Recovery

- **Emergency Kit PDF**: Saved during initial setup — required if admin account is locked out
- **Railway project**: Can be redeployed from template if Infisical service fails
- **Postgres backup**: Railway volume snapshots — enable scheduled backups in Railway dashboard
- **SMTP recovery**: If Resend key is rotated, update `SMTP_PASSWORD` in Railway env vars for the Infisical project, then redeploy

## Architecture Notes

- Infisical runs as a separate Railway project (isolated from ai-market services)
- Postgres + Redis on private networking (not publicly accessible)
- User registration disabled — admin creates accounts manually
- SMTP configured via Resend (S358) — email invites and MFA are active

## Cleanup TODO (requires web UI)

- [ ] Delete 3 duplicate/test projects in Infisical dashboard
- [ ] Rename organization from default to "ai.market"

## Legacy: Doppler

Doppler (`doppler-secrets.md`) is demoted to archive-only. It still contains a snapshot of secrets as of 2026-03-30 but is NOT the source of truth. Do not update secrets in Doppler.
