# Runbook Topic Router — start here

The **documented entry point** for ai.market runbooks. Find your subject, go straight to the owning runbook (and section). Sections are **self-contained** — you should not need to hop between pages for one answer. If you hit a fact that isn't written down, write it into the owning runbook AND fix the entry here in the **same session** (standard §L).

## Credentials & source-of-truth (where things live)

The most common miss is "what is X and where does its credential live." Answers first:

| You need | Where it lives | Runbook |
|---|---|---|
| Any secret value | Infisical (`secrets.ai.market`) — the ONLY secret store | [infisical-secrets.md](infisical-secrets.md#accessing-secrets) |
| AWS backup-writer keys (S3 put/list, no delete) | Infisical project `ai-market-backend` / env `prod`: `AWS_BACKUP_WRITER_ACCESS_KEY_ID`, `AWS_BACKUP_WRITER_SECRET` | [aws-s3.md](aws-s3.md) |
| AWS account / buckets / regions | account 948749907373; backups bucket `aimarket-backups-prod` (eu-north-1, Object Lock) | [aws.md](aws.md) |
| Cloudflare API token | Infisical `ai-market-backend`/prod: `CLOUDFLARE_API_TOKEN` (zone read + DNS edit + Worker R/W; no KV scope (DNS edit confirmed live S806: created TXT record via API)) | [cloudflare-and-dns.md](cloudflare-and-dns.md) |
| Railway API token | Infisical `ai-market-backend`/prod: `RAILWAY_API_TOKEN` (account-scoped UUID) | [titan-1.md](titan-1.md) |
| Backup/age encryption private key | 1Password only — never in S3 or on a server | [disaster-recovery.md](disaster-recovery.md) |
| Internal API key (agent→backend) | Infisical `ai-market-backend`/prod: `INTERNAL_API_KEY` | [infisical-secrets.md](infisical-secrets.md#machine-identities) |
| Machine-identity creds (unattended jobs) | `~/.config/infisical/` on Titan-1; project `ai-market-backend` | [infisical-secrets.md](infisical-secrets.md#machine-identities) |
| GCP / Vertex (AG / Gemini) auth | service account + Vertex config | [gcp-auth.md](gcp-auth.md) |
| 2FA / TOTP encryption key | backend env | [two-factor-auth.md](two-factor-auth.md) |

## By subject

**Council session gate, gateway restart/deploy, fold dispatch** — arming sequence, auto-numbering, collision/truthful errors, restart procedure, author-mode credentials, canonical gate vocabulary, middleware gaps + workarounds: [council-session-gate-and-fold-ops.md](council-session-gate-and-fold-ops.md).

**Backups & disaster recovery** — what's backed up, where, restore steps: [backup-and-recovery.md](backup-and-recovery.md). Rebuild map (offline bootstrap items, bucket layout, restore order): [disaster-recovery.md](disaster-recovery.md). The "bash" Login Items list explained: [backup-and-recovery.md](backup-and-recovery.md).

**The host — Titan-1 / Mac Studio** — hardware, services + ports, tunnel, Docker dev stack, scheduled jobs: [titan-1.md](titan-1.md). Network topology & remote access: [connectivity.md](connectivity.md#remote-access-to-titan-1).

**Secrets** — accessing, machine identities, rotation, emergency recovery: [infisical-secrets.md](infisical-secrets.md).

**AWS** — account / IAM / S3: [aws.md](aws.md) · [aws-s3.md](aws-s3.md).

**Cloudflare / DNS / Workers / tunnel** — DNS records, Workers, the mcp.ai.market tunnel: [cloudflare-and-dns.md](cloudflare-and-dns.md). The get.vectoraiz.com Worker: [cloudflare-worker.md](cloudflare-worker.md).

**MCP gateway / Koskadeux** — gateway, server, transport (why cloudflared not Tailscale), session lifecycle: [mcp-gateway.md](mcp-gateway.md).

**ai.market backend / frontend** — API service, DB, deploy, customer-data location: [ai-market-backend.md](ai-market-backend.md). Web app: [ai-market-frontend.md](ai-market-frontend.md).

**AIM Data / AIM Node / vectorAIz** — seller conduit + dev conduit: [aim-data.md](aim-data.md) · [aim-node.md](aim-node.md). Dual-brand split: [dual-brand-vectoraiz-aim-channel.md](dual-brand-vectoraiz-aim-channel.md). Releases: [aim-data-release-process.md](aim-data-release-process.md) · [aim-node-release-process.md](aim-node-release-process.md) · [vz-release-process.md](vz-release-process.md).

**allAI / agents** — agent intelligence layer + roster: [allai-agents.md](allai-agents.md).

**Auth** — sign-up / login path: [auth-signup-flow.md](auth-signup-flow.md). 2FA: [two-factor-auth.md](two-factor-auth.md).

**CRM** — architecture, pipeline, target state: [crm-architecture.md](crm-architecture.md) · [crm-pipeline.md](crm-pipeline.md) · [crm-target-state.md](crm-target-state.md).

**Ops dashboards / build queue** — ops.ai.market panels: [ops-ai-market.md](ops-ai-market.md). Build queue lifecycle: [build-queue-lifecycle.md](build-queue-lifecycle.md). Marketing tab: [marketing-tab.md](marketing-tab.md). Morning briefing: [morning-briefing.md](morning-briefing.md).

**Support tickets** — the ai.market support/trouble ticket engine: live API surface, three-principal auth model, ticket-scoped role bindings, rate limits + duplicate-subject collapse, DLQ/quarantine admin triage, email intake go-live (Max-gated `GMAIL_POLLING_ENABLED`), and what is not yet live: [support-ticket-system.md](support-ticket-system.md).

**Session lifecycle / state** — where session state lives: [mcp-gateway.md](mcp-gateway.md). Task state: [task_state.md](task_state.md). Consolidated lifecycle: [session-lifecycle.md](session-lifecycle.md).

**Website copy / marketing voice** — site copy standard (voice rules, claims discipline, machine-legibility): [website-copy-standard.md](website-copy-standard.md).

**SEO / discoverability** — infra + seller validation: [seo-infrastructure.md](seo-infrastructure.md) · [seo-seller-validation.md](seo-seller-validation.md).

**Data requests** — buyer-initiated request surface: [data-requests.md](data-requests.md).

**Email / pipelines** — drafting: [email-drafting.md](email-drafting.md). Gmail drop: [gmail-drop-pipeline.md](gmail-drop-pipeline.md). Meet records → CRM: [meet-records-pipeline.md](meet-records-pipeline.md).

**Connectivity** — physical/network topology, tailnet, redundancy: [connectivity.md](connectivity.md).

**Celery / async** — [celery-infrastructure-deployment.md](celery-infrastructure-deployment.md).

**Docker testing (VZ local)** — [docker-testing.md](docker-testing.md).

**Gateway V2 rollout / rollback** — [gateway_v2_rollout.md](gateway_v2_rollout.md) · [gateway_v2_rollback.md](gateway_v2_rollback.md).

**RTK token optimization** — [rtk-token-optimization.md](rtk-token-optimization.md).

**ACL sole-writer enforcement** — [acl-sole-writer-enforcement.md](acl-sole-writer-enforcement.md).

**AlphaFold publish scale-up** — [alphafold-publish-scale-up.md](alphafold-publish-scale-up.md).

**Vulcan configuration (context hydration / memory)** — [vulcan-configuration.md](vulcan-configuration.md).

**GCP auth** — [gcp-auth.md](gcp-auth.md).

**aimarket public MCP server** — [aimarket-mcp-server.md](aimarket-mcp-server.md).

**Retro verification (BQ-124)** — [bq-124-retro-verification.md](bq-124-retro-verification.md).

**Session lifecycle — open / plan / close** — opening sequence, planning gate, close protocol, the scratch namespace + instance-liveness collision guard (S858): [session-open-protocol.md](session-open-protocol.md) · [session-close-protocol.md](session-close-protocol.md).

**Session registry recovery & migrations** — registry.db desync/recovery, registry migration discipline, and the hazard that the test suite can mutate the live registry.db: [session-registry-recovery.md](session-registry-recovery.md).

**Agent / Council dispatch** — dispatch paths, per-agent quirks, review-mode rules, and the open_response session-clobber warning: [agent-dispatch.md](agent-dispatch.md).

**MCP transport / gateway processes** — the Cloudflare tunnel transport and the gateway-vs-server process split: [gateway-transport.md](gateway-transport.md). See also [mcp-gateway.md](mcp-gateway.md).

**Tool-code activation / deploy verification** — confirm a koskadeux-mcp restart actually took (fresh pid, right service), proof-of-life checks: [activation-verification.md](activation-verification.md).

**Schema migrations (Alembic / backend)** — backend schema migration procedures: [schema-migration.md](schema-migration.md).

**Vulcan / Mars operating discipline** — peer-symmetric claim-before-work, message-bus, and escalation rules: [peer-instance-discipline.md](peer-instance-discipline.md).

---
Every runbook above is registered here; `scripts/router_drift_check.py` enforces coverage + that every link resolves. Add new runbooks to a subject line above in the same change that creates them.
