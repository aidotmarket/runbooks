# Runbook Topic Router — start here

The **documented entry point** for ai.market runbooks. Find your subject, go straight to the owning runbook (and section). Sections are **self-contained** — you should not need to hop between pages for one answer. If you hit a fact that isn't written down, write it into the owning runbook AND fix the entry here in the **same session** (standard §L).

## On any error, read the runbook FIRST

**Before diagnosing any error, failure, or surprising symptom from code or logs, grep this router and the owning runbook's §F failure table on the error string.** Recurring incidents get misdiagnosed repeatedly because code gets read before the runbook that already documents the fix. Known recurring symptoms:

| Symptom / error string | Read this first |
|---|---|
| `RefreshError: Reauthentication is needed` · AG council reviews fail on auth | [gcp-auth.md §F-04](gcp-auth.md) — Vertex Gemini uses the **API key**, not OAuth/ADC |
| AG review `ValidationError: additionalProperties` / union-type schema | [agent-dispatch.md §C.0](agent-dispatch.md) — Gemini `Schema` subset; sanitize at the adapter |
| Council review returns no verdict / `RepairExhaustedError` | [agent-dispatch.md §O](agent-dispatch.md) — structural-output repair, distinct from input-schema |
| MP review/build fails to read a pinned SHA: `object/path is not available locally`, `git cat-file -t <sha>` fails | [agent-dispatch.md §T](agent-dispatch.md) — the SHA was committed via the GitHub API and the local Titan-1 clone is behind; `git fetch origin main` in the target repo, then redispatch |
| Structural MP build returns `RepairExhaustedError` but `git log` shows the builder commit landed locally | [agent-dispatch.md §U](agent-dispatch.md) — do NOT rebuild; complete the wrapper gates manually (tests + CI paths + cross-review + deliberate instance push) |
| MP build/review dispatch rejected `RUNBOOK_REF_MISSING` / `RUNBOOK_REF_UNRESOLVED` (failed_check path or section) | [codex-mp.md §F-08/§G-08](codex-mp.md) — BLOCK-mode runbook gate; pass structured refs with an exact existing heading, or an Attestation (creates dischargeable debt) |
| MP build killed at exactly 600s / task silent past 300s but commit landed | [codex-mp.md §F](codex-mp.md) — timeout backstop + silent-delivery ground-truth check before any redispatch |


## Credentials & source-of-truth (where things live)

The most common miss is "what is X and where does its credential live." Answers first:

| You need | Where it lives | Runbook |
|---|---|---|
| Any secret value | Infisical (`secrets.ai.market`) — the ONLY secret store | [infisical-secrets.md](infisical-secrets.md#accessing-secrets) |
| AWS backup-writer keys (S3 put/list, no delete) | Infisical project `ai-market-backend` / env `prod`: `AWS_BACKUP_WRITER_ACCESS_KEY_ID`, `AWS_BACKUP_WRITER_SECRET` | [aws-s3.md](aws-s3.md) |
| AWS account / buckets / regions | account 948749907373; backups bucket `aimarket-backups-prod` (eu-north-1, Object Lock) | [aws.md](aws.md) |
| Cloudflare API token | Infisical `ai-market-backend`/prod: `CLOUDFLARE_API_TOKEN` (zone read + DNS edit + Worker R/W + Workers-KV edit; KV write confirmed live S964 — created+deleted a temp namespace via API; DNS edit confirmed live S806. Still lacks Worker Routes + Cloudflare Tunnel scopes — see cloudflare-and-dns.md §Drift item 6) | [cloudflare-and-dns.md](cloudflare-and-dns.md) |
| Railway API token (Titan-1 host) | Infisical `koskadeux-mcp`/prod: `RAILWAY_API_TOKEN` (account-scoped, non-expiring; projectId `0943f641-faee-4324-b337-0d50c276e4a9`) | [titan-1.md](titan-1.md) |
| Backup/age encryption private key | 1Password only — never in S3 or on a server | [disaster-recovery.md](disaster-recovery.md) |
| Internal API key (agent→backend) | Infisical `ai-market-backend`/prod: `INTERNAL_API_KEY` | [infisical-secrets.md](infisical-secrets.md#machine-identities) |
| Machine-identity creds (unattended jobs) | `~/.config/infisical/` on Titan-1; project `ai-market-backend` | [infisical-secrets.md](infisical-secrets.md#machine-identities) |
| Rotate/expire/generate a secret WE own, without typing it (local model) | Titan-1 `/Users/max/local-secops/` (Ollama `llama3.3:70b`; propose→review→execute; allow-listed) | [local-secops.md](local-secops.md) |
| GCP / Vertex (AG / Gemini) auth | Vertex Gemini uses the **API key** `VERTEX_API_KEY` (AQ., Infisical bd272d48) — NOT OAuth/ADC; Gmail = OAuth; gcloud = interactive-only | [gcp-auth.md](gcp-auth.md) |
| 2FA / TOTP encryption key | backend env | [two-factor-auth.md](two-factor-auth.md) |

## By subject

**Council session gate, gateway restart/deploy, fold dispatch** — arming sequence, auto-numbering, collision/truthful errors, restart procedure, author-mode credentials, canonical gate vocabulary, middleware gaps + workarounds: [council-session-gate-and-fold-ops.md](council-session-gate-and-fold-ops.md).

**Reform WS11 — queue-overlay archival cutover** — retiring the 8 sub-surfaces on `config:parallel-worker-queue.body`; build complete (chunks 1–5 on main, S992), Phase-D production cutover gated/pending, per-sub-surface rollback + forward-replay re-cutover, feature-flag surfaces (`config:queue-overlay-feature-flags`), and the WS9 ACL warn→enforce tie-in: [queue-overlay-archival-cutover.md](queue-overlay-archival-cutover.md).

**Qdrant / vector database** — hosting, API-key authentication + lockdown, key locations (Infisical + both Railway services), per-collection S3 backup coverage: [qdrant.md](qdrant.md).

**Backups & disaster recovery** — what's backed up, where, restore steps: [backup-and-recovery.md](backup-and-recovery.md). Rebuild map (offline bootstrap items, bucket layout, restore order): [disaster-recovery.md](disaster-recovery.md). The "bash" Login Items list explained: [backup-and-recovery.md](backup-and-recovery.md).

**The host — Titan-1 / Mac Studio** — hardware, services + ports, tunnel, Docker dev stack, scheduled jobs: [titan-1.md](titan-1.md). Network topology & remote access: [connectivity.md](connectivity.md#remote-access-to-titan-1).

**Secrets** — accessing, machine identities, rotation (incl. **Stripe API key rotation** — which keys, the mandatory Railway-set + redeploy + live-verify, webhook secret is separate), emergency recovery: [infisical-secrets.md](infisical-secrets.md). **Local SecOps assistant** — supervised local-model credential rotation/movement/generation on Titan-1 (values never leave the host, no typing): [local-secops.md](local-secops.md).

**AWS** — account / IAM / S3: [aws.md](aws.md) · [aws-s3.md](aws-s3.md).

**Cloudflare / DNS / Workers / tunnel** — DNS records, Workers, the mcp.ai.market tunnel: [cloudflare-and-dns.md](cloudflare-and-dns.md). The get.vectoraiz.com Worker: [cloudflare-worker.md](cloudflare-worker.md).

**MCP gateway / Koskadeux** — gateway, server, transport (why cloudflared not Tailscale), session lifecycle: [mcp-gateway.md](mcp-gateway.md).

**ai.market backend / frontend** — API service, DB, deploy, customer-data location: [ai-market-backend.md](ai-market-backend.md). Web app: [ai-market-frontend.md](ai-market-frontend.md).
**API error contract — DB constraint → HTTP status** — when a database constraint violation should surface as a 4xx not a raw 500 (constraint-name detection; peer-messages `ck_*` CHECK → 422 worked example): see the "API error mapping" section of [ai-market-backend.md](ai-market-backend.md).

**AIM Data / AIM Node / vectorAIz** — seller conduit + dev conduit: [aim-data.md](aim-data.md) · [aim-node.md](aim-node.md). vectorAIz brand context (AIM Channel retired, superseded by AIM Data): [dual-brand-vectoraiz-aim-channel.md](dual-brand-vectoraiz-aim-channel.md). Releases: [aim-data-release-process.md](aim-data-release-process.md) · [aim-node-release-process.md](aim-node-release-process.md) · [vz-release-process.md](vz-release-process.md).

**allAI / agents** — agent intelligence layer + roster: [allai-agents.md](allai-agents.md). Agent write-approval (HITL) queue — persistence, atomic approve claim, post-approval execution: see the "HITL authorization queue" section of [allai-agents.md](allai-agents.md).

**Codex / MP — Council primary builder** — MP dispatch mechanics (build/review/author, background polling, structural vs legacy paths), Codex CLI config + OAuth, timeout and mutex behavior, the MP failure/symptom table (silent-delivery, RepairExhaustedError, 600s kills, READ-ONLY violations, runbook-gate rejections, push_failed guardrail), and the model-swap procedure (gpt-5.6 and successors, T-2026-000197): [codex-mp.md](codex-mp.md). Roster + per-agent quirks remain canonical in `infra:council-comms`; gate semantics in [agent-dispatch.md](agent-dispatch.md).

**Ticket-probe auto-close — self-closing support tickets** — support tickets close on the production symptom, not the delivery path: each ticket carries a machine still-broken probe (kinds http/db_query/log_grep/flag_state/config_key), and a reconciler runs open-ticket probes on every prod deploy plus an hourly heartbeat, auto-resolving a ticket (with evidence, `resolution_source=probe`) once its probe reports not-broken twice consecutively; an unreachable/probe-rot probe ALARMS and never closes. Feature flag `TICKET_PROBE_RECONCILER_ENABLED` (live on Titan-1 since S1128); http probes require the backend `TICKET_PROBE_HTTP_ALLOWLIST`: [ticket-probe-autoclose.md](ticket-probe-autoclose.md). Canonical status: `build:bq-two-track-ticket-probe-autoclose-s1126`.

**SysAdmin operating model** — bounded Observe→Decide→Act→Verify→(Fix|Escalate) loop, verified capability set, LOUD-DEGRADED bind failures, singleton-owned probes/compliance/scheduler, `/agent-compliance`, typed health contracts, and Railway project-token recovery: [sysadmin.md](sysadmin.md).

**Auth** — sign-up / login path: [auth-signup-flow.md](auth-signup-flow.md). **Login sessions surviving reload (in-memory access token + httpOnly refresh cookie, the same-site invariant, browser verification discipline):** [browser-session-auth.md](browser-session-auth.md). 2FA: [two-factor-auth.md](two-factor-auth.md).

**Account capabilities & seller onboarding** — the capability model (buyer default-on, seller additive), provisioning vs active, the four seller readiness steps (profile name, company name, 2FA, Stripe payouts-live via the durable `users.stripe_payouts_enabled` column), the `require_capability` / `assert_user_capability` guard, the 403 `CapabilityRequiredError` contract, and a seller's path to first sale (connect Stripe → seller goes active): [account-capability-onboarding.md](account-capability-onboarding.md).

**Publish paths — the single publish route** — there is exactly one way a dataset becomes a listing: the signed, active-seller-gated `POST /api/v1/vz/publish` (`vz_publish_service.create_or_update_listing`), used by AIM Data (via its signer/proxy) and vectorAIz. The website has no create/publish — manage only (see-my-listings, preview, retraction-only unpublish, delete) on canonical records. Agent/programmatic surfaces are keep-and-gate at the ActionExecutorService chokepoint. The two website publish wizards were removed and their five tables dropped (S1077): [publish-paths.md](publish-paths.md). Program state: `config:publish-paths-consolidation-tracker`.

**CRM** — architecture, pipeline, target state: [crm-architecture.md](crm-architecture.md) · [crm-pipeline.md](crm-pipeline.md) · [crm-target-state.md](crm-target-state.md). CRM access + auth (Koskadeux gateway only; external `/mcp/crm` connector endpoint REMOVED S1099, rollback constraints): [crm-architecture.md](crm-architecture.md#crm-access-and-auth-s1099--external-mcp-endpoint-removed). Gateway CRM tool mechanics: [mcp-gateway.md](mcp-gateway.md).

**CRM V2 Phase D — legacy read-elimination + table drop** — the V1→V2 cutover: eliminating legacy `select(CRM*)` reads chunk-by-chunk (party model becomes sole read path), the per-chunk gate track, and the Gate-3 access-regression audit (Audit A/B) + conditional access-preserving backfill whenever the ownership predicate changes: [crm-target-state.md](crm-target-state.md#7-migration--consolidation-plan) §7 Phase D. New CRM read families default to `legacy` unless added to `GLOBAL_DEFAULT_FAMILIES` (deliberate global cutover only) — see the read-flag default invariant in §7 Phase D. Canonical status: `config:crm-phase-d-tracker`.

**Ops dashboards / build queue** — ops.ai.market panels: [ops-ai-market.md](ops-ai-market.md). Build queue lifecycle: [build-queue-lifecycle.md](build-queue-lifecycle.md). Marketing tab: [marketing-tab.md](marketing-tab.md). Morning briefing: [morning-briefing.md](morning-briefing.md).

**Staging environment (E2E browser-testing)** — Railway `staging` environment: backend/frontend staging services + dedicated staging Postgres, Stripe TEST config (webhook secret = operator step), deterministic seed, golden-snapshot dump→restore (primary reset path), staging-vs-production parity check (M1). Canonical doc lives in the backend repo: `ai-market-backend/docs/staging-environment.md` (service IDs, URLs, commands, safety guards). Never point staging tooling at production; `scripts/staging_safety.py` enforces. Owner BQ: BQ-E2E-TESTING-FRAMEWORK-S1152 c1 (S1158); c3 additions (S1159): CLI-only deploy path (railway up from checkout — service has no repo link), packaging constraint (Docker image excludes scripts/; app-imported code lives under app/), and the staging-only E2E surgical-reset endpoint (flag-gated route, allowlist, dry-run default, fail-closed JSONL audit) — all in the same backend doc.

**Push guardrail / merging to main** — automated builds (Codex/CC) cannot push to `main`/`master`/`production`; a `pre-push` hook refuses it unless `KD_ALLOW_MAIN_PUSH=1` is set, so only a deliberate reviewed instance merge lands on a protected branch: [build-queue-lifecycle.md](build-queue-lifecycle.md#push-guardrail--automated-builds-cannot-reach-main-s1077).

**Support tickets** — the ai.market support/trouble ticket engine: live API surface, three-principal auth model, ticket-scoped role bindings, rate limits + duplicate-subject collapse, DLQ/quarantine admin triage, the agent management MCP tools (`support_ticket_list/get/patch/message`), email intake go-live (Max-gated `GMAIL_POLLING_ENABLED`), and what is not yet live: [support-ticket-system.md](support-ticket-system.md).

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

**Session registry recovery & migrations** — durable monotonic session-ID high-water mark (session_seq + config:session-seq anchor), the pytest isolation guard on the live registry.db, the two-signal stale-session self-heal, blocked session opens, regressed/reused session numbers, and registry migration discipline: [session-registry-recovery.md](session-registry-recovery.md).

**Agent / Council dispatch** — dispatch paths, per-agent quirks, review-mode rules, and the open_response session-clobber warning: [agent-dispatch.md](agent-dispatch.md).

**MCP transport / gateway processes** — the Cloudflare tunnel transport and the gateway-vs-server process split: [gateway-transport.md](gateway-transport.md). See also [mcp-gateway.md](mcp-gateway.md).

**Tool-code activation / deploy verification** — confirm a koskadeux-mcp restart actually took (fresh pid, right service), proof-of-life checks: [activation-verification.md](activation-verification.md).

**Schema migrations (Alembic / backend)** — backend schema migration procedures: [schema-migration.md](schema-migration.md).

**Vulcan / Mars operating discipline** — peer-symmetric claim-before-work, message-bus, and escalation rules: [peer-instance-discipline.md](peer-instance-discipline.md).

**Operator Telegram notifications** — which bot may message Max and what classes are allowed; @koskadeux_bot killed, only @allai_agent_bot, emergency/human-required only: [operator-telegram-notifications.md](operator-telegram-notifications.md).

---
Every runbook above is registered here; `scripts/router_drift_check.py` enforces coverage + that every link resolves. Add new runbooks to a subject line above in the same change that creates them.

**GitHub reconciliation webhook** — single webhook + event routing, setting `GITHUB_WEBHOOK_SECRET` (Infisical record + Railway-env operational reality), activation + verification: [reconciliation-github-webhook.md](reconciliation-github-webhook.md).
