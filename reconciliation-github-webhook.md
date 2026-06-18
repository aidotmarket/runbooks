# GitHub → Reconciliation Webhook

## §A. Header
The single GitHub webhook that drives build-queue reconciliation and CI-failure deploy monitoring for `ai-market-backend`. One endpoint, one secret, event-type routing. Pillar: Council/Koskadeux orchestration. Origin: BQ-GITHUB-WEBHOOK-ROUTE-COLLISION-RECONCILE-VS-CIFAILURE-S933 (shipped S942, PR #181, squash 52693064).

## §B. Capability Matrix
| GitHub event | Handler action |
|---|---|
| `push` (ref `refs/heads/main`) | full reconciliation pass |
| `pull_request` (opened/closed/reopened/synchronize) | reconcile the matching build entity (by repo + head branch) |
| `workflow_run` | existing deploy_monitor failure handling (unchanged) |
| any other event | `202 accepted` no-op |

## §C. Architecture & Interactions
- Single handler `github_failure_webhook` in `app/api/v1/endpoints/webhooks.py`, mounted at `POST /api/v1/webhooks/github` (live: `https://api.ai.market/api/v1/webhooks/github`).
- Verifies the GitHub HMAC signature against `GITHUB_WEBHOOK_SECRET` for ALL events BEFORE branching on the `X-GitHub-Event` header. Fail-closed.
- One webhook, one secret. Do NOT create a second webhook or a second secret.
- The old path `POST /webhooks/github` (from `app/api/webhooks.py`, mounted at `/webhooks`) was removed and now 404s. That module still serves `/gmail`, `/telegram`, `/railway`.

## §D. Agent Capability Map
- Vulcan / Mars: own the handler code, the GitHub webhook config, and verification.
- SysAdmin agent: can READ Infisical secrets (`infisical_get_secret`); does NOT set Railway env vars.
- Generating the secret value and configuring the GitHub webhook are operator (Max) actions — agents do not handle secret values in plaintext.

## §E. Operate — setting the secret / activating
**CRITICAL GOTCHA:** the running app reads `GITHUB_WEBHOOK_SECRET` from its process environment = a **Railway variable on `ai-market-backend`**. It does NOT load Infisical at runtime — Infisical is wired only for the SysAdmin agent skill (`app/agents/sysadmin/skills/infisical_ops.py`), not injected into app settings at startup. A secret placed only in Infisical will NOT reach the app. See `infisical-secrets.md` → Known Gotchas. (BQ-RAILWAY-INFISICAL-SYNC manual-sync class.)

1. Generate locally: `openssl rand -hex 32`. Keep it; never paste it into chat, logs, or commits.
2. Record in Infisical (system of record): `https://secrets.ai.market` → project `bd272d48-c5a1-4b52-9d24-12066ae4403c` → **Production** env → add `GITHUB_WEBHOOK_SECRET` at root.
3. Set the operational value the app reads: Railway → project `ai-market` → service `ai-market-backend` → Variables → add `GITHUB_WEBHOOK_SECRET` (same value). Use the masked field, not the CLI.
4. Redeploy so the app re-reads env: `unset RAILWAY_TOKEN; railway redeploy --service ai-market-backend --yes` from `~/Projects/ai-market/ai-market-backend` (or let the variable-change redeploy run).
5. Configure GitHub: repo `aidotmarket/ai-market-backend` → Settings → Webhooks → Add webhook. Payload URL `https://api.ai.market/api/v1/webhooks/github`; content type `application/json`; Secret = same value; events = Pushes + Pull requests + Workflow runs.
6. Verify (§F).

## §F. Isolate — diagnostics
- `POST /api/v1/webhooks/github` (no/bad signature):
  - `503 "GitHub webhook not configured"` → secret unset in the Railway env (app can't see it). Re-check step 3 + redeploy.
  - `401 "Invalid signature"` → secret IS loaded and verification active (expected for a bad signature).
- `POST /webhooks/github` → `404` expected (old path retired).
- GitHub → repo Settings → Webhooks → the hook → **Recent Deliveries**: ping shows `202`; a signed real delivery shows `200`. Non-2xx → read the response body there.
- Read deliveries via API: `gh api repos/aidotmarket/ai-market-backend/hooks/<id>/deliveries`.

## §G. Repair
- Rotation: new value → update Infisical (prod) + Railway var → redeploy → update the GitHub webhook secret to match → confirm ping 202. Both ends must match in one window.
- Duplicate/wrong webhook: `gh api repos/aidotmarket/ai-market-backend/hooks`; keep exactly one pointing at the canonical URL.

## §H. Evolve
### §H.1 Invariants
- ONE endpoint (`/api/v1/webhooks/github`), ONE shared secret, ONE GitHub webhook.
- Signature verified for ALL events before any routing; fail-closed (401 bad sig, 503 secret-unset).
- `workflow_run` → deploy_monitor behavior must not change when event routing is extended.
### §H.2 Change rule
Adding an event type = add a branch in `github_failure_webhook` PLUS a full-app test (TestClient against `app.main:app`, not the isolated router). Isolated-router tests miss mount/collision bugs — that was the original failure mode.

## §I. Acceptance Criteria
- Canonical path live + fail-closed; old path 404.
- Secret present in BOTH Infisical (record) AND the Railway env (operational).
- GitHub webhook delivers: ping 202; real delivery 2xx.

## §J. Lifecycle
Shipped S942 (PR #181, squash 52693064). Reviews: DeepSeek + XAI APPROVE; MP builder (excluded). Prod-verified S942 (ping 202, 503→401 after secret set, old path 404).

## §K. Conformance
After any secret rotation, or quarterly: ping returns 202; canonical path 401 on bad sig; old path 404.
