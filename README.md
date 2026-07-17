# ai.market Runbooks

This repository is the source of truth for ai.market system-level runbooks. The inventory
below reports files in the current tree; it does not claim that every file conforms to the
runbook standard. Chunk 1 replaces this one-shot inventory with catalog-generated status.

## Generated runbook inventory

Generation command (run from the repository root):

```bash
LC_ALL=C find . runbooks -maxdepth 1 -type f -name '*.md' ! -name README.md -print \
  | sed 's#^./##' \
  | LC_ALL=C sort \
  | awk 'BEGIN { print "<!-- BEGIN GENERATED RUNBOOK INVENTORY -->"; print "| Runbook path |"; print "|---|" } { print "| `" $0 "` |" } END { print "<!-- END GENERATED RUNBOOK INVENTORY -->" }'
```

<!-- BEGIN GENERATED RUNBOOK INVENTORY -->
| Runbook path |
|---|
| `TOPIC-ROUTER.md` |
| `account-capability-onboarding.md` |
| `account-teardown.md` |
| `acl-sole-writer-enforcement.md` |
| `activation-verification.md` |
| `agent-dispatch.md` |
| `ai-market-backend.md` |
| `ai-market-frontend.md` |
| `aim-data-release-process.md` |
| `aim-data-seller-publish-journey.md` |
| `aim-data.md` |
| `aim-node-release-process.md` |
| `aim-node.md` |
| `aimarket-mcp-server.md` |
| `allai-agents.md` |
| `allai-escalation-safety-spine.md` |
| `alphafold-publish-scale-up.md` |
| `auth-signup-flow.md` |
| `aws-s3.md` |
| `aws.md` |
| `backup-and-recovery.md` |
| `bq-124-retro-verification.md` |
| `browser-session-auth.md` |
| `build-queue-lifecycle.md` |
| `celery-infrastructure-deployment.md` |
| `cloudflare-and-dns.md` |
| `cloudflare-worker.md` |
| `codex-mp.md` |
| `connectivity.md` |
| `constitution-amendment.md` |
| `council-session-gate-and-fold-ops.md` |
| `crm-architecture.md` |
| `crm-pipeline.md` |
| `crm-target-state.md` |
| `data-requests.md` |
| `dataset-card-publishing.md` |
| `dev-tickets.md` |
| `disaster-recovery.md` |
| `docker-testing.md` |
| `dual-brand-vectoraiz-aim-channel.md` |
| `e2e-browser-runner.md` |
| `email-drafting.md` |
| `gateway-transport.md` |
| `gateway_v2_rollback.md` |
| `gateway_v2_rollout.md` |
| `gcp-auth.md` |
| `gmail-drop-pipeline.md` |
| `infisical-secrets.md` |
| `local-secops.md` |
| `marketing-tab.md` |
| `max-reporting.md` |
| `mcp-gateway.md` |
| `meet-records-pipeline.md` |
| `morning-briefing.md` |
| `operator-telegram-notifications.md` |
| `ops-ai-market.md` |
| `peer-instance-discipline.md` |
| `publish-paths.md` |
| `qdrant-sync-outbox.md` |
| `qdrant.md` |
| `queue-overlay-archival-cutover.md` |
| `reconciliation-github-webhook.md` |
| `rtk-token-optimization.md` |
| `runbook-first-gates.md` |
| `runbooks/agent-dispatch.md` |
| `runbooks/build-queue-reconciliation.md` |
| `runbooks/council-gate-process.md` |
| `runbooks/council-hall-deliberation.md` |
| `runbooks/council.md` |
| `schema-migration.md` |
| `schema-rationalization.md` |
| `seo-infrastructure.md` |
| `seo-seller-validation.md` |
| `session-close-protocol.md` |
| `session-lifecycle.md` |
| `session-open-protocol.md` |
| `session-registry-recovery.md` |
| `support-ticket-system.md` |
| `sysadmin.md` |
| `task_state.md` |
| `ticket-probe-autoclose.md` |
| `titan-1.md` |
| `trust-channel.md` |
| `two-factor-auth.md` |
| `vulcan-configuration.md` |
| `vz-release-process.md` |
| `website-copy-standard.md` |
| `work-checkout.md` |
<!-- END GENERATED RUNBOOK INVENTORY -->

## Working on a runbook

- Create a new runbook: `runbook-new <system-name>`
- Validate a runbook: `runbook-lint <path>`
- Run the harness locally: `runbook-harness --runbook <path>`

## Tooling

This repository ships `runbook-tools`, a Python package providing:
- `runbook-lint` — validates runbooks against the standard (20 checks per §K.1 of the spec)
- `runbook-new` — generates a scaffold runbook
- `runbook-harness` — runs the stateless-agent legibility harness nightly

Installation: `pip install -e .` (Python 3.11+).

Design contract: `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md`.
