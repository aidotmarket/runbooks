> **S612 Process Consolidation Owner**: this runbook is the single canonical reference for CI gates AND deploy verification after the S612 consolidation that collapsed ~8 process BQs into BQ-PROCESS-CI-DEPLOY-GATES-S612 (P1). Per Council mandate, this file now covers BOTH pre-merge CI gates (branch protection, lint, smoke tests) and post-merge activation verification (proof-of-life checks).
>
> **Section layout:**
> - **§CI Gates (pre-merge)** — main-branch protection rules across ai-market-backend, ai-market-frontend, ops-ai-market, koskadeux-mcp, aim-node; required CI checks before merge; branch-protection configuration.
> - **§Lint gates** — lint pass enforcement; ops-ai-market lint configuration.
> - **§Deploy verification (post-merge)** — Railway deploy receipt verification; production smoke tests; activation proof-of-life (existing body below).
>
> Backend correctness primitives (atomic-write idempotency, token target binding, entity CAS locking) are explicitly NOT consolidated under this BQ per Council mandate; they remain product backend BQs.
>
> Revisions land as PRs; require MP review-mode approval. Filed under S612.

---

# Activation Verification Runbook
## R.1 Purpose
Gate 3 is not complete when code exists only in Git. It is complete when the
live runtime is serving that code.
This runbook exists because long-running services can keep stale imported
modules in memory after merge or local file edits. S465 produced two concrete
examples of that failure mode:
- `build:bq-session-boot-footprint`: the smaller boot payload did not become
  real until `com.koskadeux.mcp` was restarted and a fresh `kd_session_open`
  showed the new footprint.
- `build:bq-council-dispatch-optimization` Phase 1b.2: repo state was correct,
  but Gate 3 needed restart-plus-runtime proof before the optimization was
  actually live.
Use this runbook whenever a BQ changes code imported by a long-running local
service or changes a remotely hosted service that deploys asynchronously after
`git push`.
Do not stop at "tests passed" or "push succeeded." Verify from the live runtime
that the new behavior is visible where the customer or operator actually hits
the service.
## R.2 Service Inventory
Canonical six-service scope for this runbook:
| Service | Runtime host | Restart mechanism | Health probe endpoint |
|---|---|---|---|
| `koskadeux-mcp` (`com.koskadeux.mcp`) | Titan-1 `launchd`, local Python on `:8765` | `launchctl kickstart -k gui/$UID/com.koskadeux.mcp` | `http://127.0.0.1:8765/health` |
| `ai-market-backend` | Railway production | `git push origin main` triggers async auto-deploy | `https://api.ai.market/health` |
| `ai-market-frontend` | Cloudflare Pages | `git push origin main` triggers Pages deploy | `https://ai.market/` |
| `ops.ai.market` | Cloudflare Pages | `git push origin main` triggers Pages deploy | `https://ops.ai.market/` |
| `council-hall` (`com.koskadeux.council-hall`) | Titan-1 `launchd`, FastAPI on `:8770` | `launchctl kickstart -k gui/$UID/com.koskadeux.council-hall` | `http://127.0.0.1:8770/health` |
| `ag_server` (`com.koskadeux.ag_server`) | Titan-1 `launchd`, FastAPI on `:8766` | `launchctl kickstart -k gui/$UID/com.koskadeux.ag_server` | `http://127.0.0.1:8766/health` |
Interpretation rules:
- Local launchd services require an explicit restart after code change.
- Railway and Cloudflare-hosted services restart by deploy, not by local
  process management.
- Health is necessary but not sufficient. If the change affects behavior beyond
  health JSON, run one probe that exercises the changed path.
## R.3 Per-service Activation-verification Recipes
**1. `koskadeux-mcp` full worked example**
Detect the change:
```bash
git diff --name-only <base>..<head> | grep -E '^(tools/|koskadeux_server\.py|session_boot_gate\.py|cross_review_gate\.py|council_(gate_runner|replay_harness|task_template|output_schemas|verdict_adapter|dispatch_models)\.py|(mp|antigravity|xai|vulcan)_client\.py|(openai_responses|google_genai)_client\.py)'
git rev-parse --short HEAD
```
Pre-restart evidence from a fresh boot:
- Call `kd_session_open({"session_id":"SXXX"})`
- Record `service_health.mcp.healthy`
- Record `context_profile.total_est_tokens`
- Record the relevant `context_profile.components` fields
Restart:
```bash
launchctl kickstart -k gui/$UID/com.koskadeux.mcp
sleep 6
```
**Confirm the restart actually took (process identity) BEFORE trusting health:**
```bash
# The REAL handler is koskadeux_server.py on :8765. Confirm a FRESH pid + start time.
ps -Ao pid,lstart,etime,command | grep -F 'koskadeux_server.py' | grep -v grep
```
- The `pid` and `lstart` MUST be newer than the kickstart you just issued. A stale pid/elapsed time means the restart did NOT replace the process.
- Verify you are reading `koskadeux_server.py` (the `:8765` handler), NOT the launchd `infisical run` / `/bin/bash` wrapper pid, and NOT the separate `com.koskadeux.gateway` (`gateway_server.py` on `:8767`). Restarting the gateway does not restart the handler, and vice versa.
- Do NOT judge freshness by `service_health.mcp.version` alone: that string is hardcoded in `tools/session.py` and can lag the server's real version (at S869 `koskadeux_server.py` reported `1.10` while the health helper still emitted `1.9`). Trust pid/start-time first, then the boot-payload code-path signature, over any single version field.
Post-restart verification:
- Call `kd_session_open({"session_id":"SXXX-VERIFY"})` from a fresh session
- Confirm `service_health.mcp.healthy == true`
- Confirm the boot payload now matches the new code path
- Compare pre/post `context_profile.total_est_tokens`
Expected success:
- The stale pre-restart boot signature is gone
- The post-restart token count and payload fields match the new implementation
- For the S465 footprint case, post-restart evidence shows the corrected boot
  shape and the expected token delta
**2. `ai-market-backend`**
Identify:
```bash
git -C /Users/max/Projects/ai-market/ai-market-backend diff --name-only <base>..<head> | grep -vE '^(docs/|tests/|\.github/)'
git -C /Users/max/Projects/ai-market/ai-market-backend rev-parse --short HEAD
```
Restart/deploy:
```bash
git -C /Users/max/Projects/ai-market/ai-market-backend push origin main
```
Verify:
```bash
curl -fsS https://api.ai.market/health
```
Expected output:
- HTTP `200`
- Root health path is `/health`, not `/api/v1/health`
- If the response includes version or SHA data, it matches the pushed commit
- If not, run one probe against the changed endpoint or response field
**3. `ai-market-frontend`**
Identify:
```bash
git -C /Users/max/Projects/ai-market/ai-market-frontend diff --name-only <base>..<head>
git -C /Users/max/Projects/ai-market/ai-market-frontend rev-parse --short HEAD
```
Restart/deploy:
```bash
git -C /Users/max/Projects/ai-market/ai-market-frontend push origin main
```
Verify:
```bash
curl -fsS https://ai.market/ | grep -F "<marker introduced by the change>"
```
Expected output: the changed DOM marker, copy, metadata tag, or asset URL is
present on the live site.
**4. `ops.ai.market`**
Identify:
```bash
git -C /Users/max/Projects/ops-ai-market diff --name-only <base>..<head>
git -C /Users/max/Projects/ops-ai-market rev-parse --short HEAD
```
Restart/deploy:
```bash
git -C /Users/max/Projects/ops-ai-market push origin main
```
Verify:
```bash
curl -fsS https://ops.ai.market/ | grep -F "<marker introduced by the change>"
```
Expected output: the changed UI marker is visible in the live page payload.
**5. `council-hall`**
Identify:
```bash
git diff --name-only <base>..<head> | grep -E '^(council_hall/|council_.*\.py)'
git rev-parse --short HEAD
```
Restart:
```bash
launchctl kickstart -k gui/$UID/com.koskadeux.council-hall
sleep 3
```
Verify:
```bash
curl -fsS http://127.0.0.1:8770/health
```
Expected output: JSON containing `"service":"council-hall"` and normally
`"status":"ok"`.
**6. `ag_server`**
Identify:
```bash
git diff --name-only <base>..<head> | grep -E '^(ag_server\.py|antigravity_.*\.py|scripts/launch_ag_server\.sh)'
git rev-parse --short HEAD
```
Restart:
```bash
launchctl kickstart -k gui/$UID/com.koskadeux.ag_server
sleep 3
```
Verify:
```bash
curl -fsS http://127.0.0.1:8766/health
```
Expected output: JSON containing `"service":"ag_server"` and `"status":"ok"`.
## R.4 Railway Async Verification Pattern
Railway deploy completion is asynchronous. `git push` only creates the deploy;
it does not prove the new container is already serving traffic.
Pattern:
- Push to `origin/main`
- Poll the public root health route at `/health`
- Tolerate 30-60s deploy lag before declaring failure
- If the health body exposes commit SHA or version data, compare it to the
  pushed revision
- If the health body does not expose revision data, run one changed endpoint
  probe after health turns green
Concrete example:
```bash
TARGET_SHA=$(git -C /Users/max/Projects/ai-market/ai-market-backend rev-parse --short HEAD)
for i in {1..12}; do
  curl -fsS https://api.ai.market/health && break
  sleep 5
done
echo "expected commit: $TARGET_SHA"
```
Interpretation:
- Success means `https://api.ai.market/health` returns `200`
- Use `/health` at the site root for Railway verification in this runbook
- Do not use `/api/v1/health` for this step
## R.5 LS Schema Reference
Write activation evidence under:
```json
body.gate3_live_verification.{service_key}
```
Minimal shape:
```json
{
  "restart_evidence": {
    "method": "launchctl kickstart -k gui/$UID/com.koskadeux.mcp",
    "verified_at": "2026-04-18T11:16:00Z"
  },
  "pre_restart_measurement": {
    "pid": 69597,
    "context_profile.total_est_tokens": 6378
  },
  "post_restart_measurement": {
    "pid": 70123,
    "context_profile.total_est_tokens": 6404
  },
  "delta": {
    "context_profile.total_est_tokens": 26,
    "note": "fresh runtime loaded the new boot path"
  },
  "historical_cases": {
    "s465": {
      "note": "original evidence preserved here"
    }
  }
}
```
Notes:
- `service_key` examples: `koskadeux_mcp`, `ai_market_backend`,
  `ai_market_frontend`, `ops_dashboard`, `council_hall`, `ag_server`
- `restart_evidence`, `pre_restart_measurement`,
  `post_restart_measurement`, and `delta` are the canonical top-level fields
- `historical_cases.{session_id}` preserves the original evidence while the
  canonical top-level fields store the current normalized shape
