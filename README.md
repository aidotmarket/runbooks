# ai.market Runbooks

Operational runbooks for how Max interacts with the ai.market system. One file per process. Each runbook covers what it does, how it works, how to verify it, and what to do when it breaks.

## Runbooks

| # | Process | File | Status |
|---|---------|------|--------|
| 1 | [Gmail Drop Pipeline](gmail-drop-pipeline.md) | `gmail-drop-pipeline.md` | Built S222, verified S223 |
| 2 | [CRM Pipeline](crm-pipeline.md) | `crm-pipeline.md` | Operational |
| 3 | [Marketing Tab](marketing-tab.md) | `marketing-tab.md` | Operational |
| 4 | [VZ Release Process](vz-release-process.md) | `vz-release-process.md` | Operational |
| 5 | [Session Lifecycle](session-lifecycle.md) | `session-lifecycle.md` | Updated S226 |
| 6 | [Email Drafting](email-drafting.md) | `email-drafting.md` | Operational |
| 7 | [Agent Dispatch](agent-dispatch.md) | `agent-dispatch.md` | Updated S226 |
| 8 | [Doppler Secrets](doppler-secrets.md) | `doppler-secrets.md` | **DEPRECATED** — see infisical-secrets.md |
| 9 | [Docker Testing](docker-testing.md) | `docker-testing.md` | Operational |
| 10 | [GCP Auth](gcp-auth.md) | `gcp-auth.md` | Operational |
| 11 | [Cloudflare Worker](cloudflare-worker.md) | `cloudflare-worker.md` | Operational |
| 12 | [Morning Briefing](morning-briefing.md) | `morning-briefing.md` | Fixed S226 |
| 13 | [MCP Gateway](mcp-gateway.md) | `mcp-gateway.md` | New S226 |

## How to use

When something breaks or you need to remember how a process works, open the relevant runbook. Each one is self-contained.

## Updating

Vulcan updates these during sessions when processes change. If you notice a runbook is stale, ask Vulcan to update it.
