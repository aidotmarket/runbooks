# Cloudflare and DNS

Canonical runbook for everything Cloudflare-fronted at ai.market and vectoraiz.com — DNS records, Workers, the live mcp.ai.market tunnel, and the API access patterns. Supersedes the prior `cloudflare-worker.md` (now Worker-detail subsection of this doc) and the partial Cloudflare table in `ai-market-backend/docs/core/INFRASTRUCTURE.md`.

## What this covers

- The two Cloudflare zones we own (`ai.market`, `vectoraiz.com`) and every live DNS record in them
- The four production Cloudflare Workers and where each one's source-of-truth lives (or doesn't — see drift)
- The `mcp.ai.market` Cloudflare Tunnel that fronts the local Koskadeux MCP gateway on Titan-1
- Secrets, deploy commands, verification, and troubleshooting for each piece
- Five drift items discovered during the S688 audit that need separate follow-up (see §Drift at the bottom)

## Cloudflare account

| Field | Value |
|-------|-------|
| Account name | `Max@ai.market's Account` |
| Account ID | `d5346d3e0f8f344c5f4915aaca689adf` |
| Plan (both zones) | Free Website |
| Active zones | `ai.market` (id `f82ac6762af544d71e8ad5eb3d7fca0c`), `vectoraiz.com` (id `401a4cf862898bc4dd6d03e2a0f50273`) |
| API token | `CLOUDFLARE_API_TOKEN` in Infisical `ai-market-backend` project (id `bd272d48-c5a1-4b52-9d24-12066ae4403c`), env `prod` |

The API token in Infisical has zone read + Worker scripts read/write permissions but **does not** include Cloudflare Tunnel (`cfd_tunnel`) or Worker Routes scopes — both of those endpoints return `10000 Authentication error` with the current token. If you need to manage tunnels or routes via API, mint a new token with those scopes; otherwise use the dashboard or `cloudflared` CLI for tunnels and `wrangler` for routes.

## DNS records (live inventory)

Records as of S688 (2026-05-22). To refresh: see §Verification quick reference.

### `ai.market` zone (30 records)

**Application CNAMEs (Railway-targeted unless noted):**

| Subdomain | Proxied | Target | Notes |
|-----------|---------|--------|-------|
| `ai.market` (apex) | DNS-only | `gtxi2e3b.up.railway.app` | ai-market-frontend |
| `www.ai.market` | DNS-only | `1g9g5jol.up.railway.app` | ai-market-frontend |
| `api.ai.market` | DNS-only | `97vz1cfo.up.railway.app` | ai-market-backend |
| `ops.ai.market` | Proxied | `ufvvklxz.up.railway.app` | ops-ai-market |
| `secrets.ai.market` | Proxied | `jjpiwqgb.up.railway.app` | Infisical (self-hosted on Railway) |
| `mcp.ai.market` | Proxied | `007ddc34-de07-474c-adbc-a648663b9c78.cfargotunnel.com` | Cloudflare Tunnel → Titan-1 (see §Tunnel) |
| `mcp.vectoraiz.com.ai.market` | Proxied | same tunnel as above | **Drift item — looks like a typo creating a 4-label FQDN; cleanup candidate** |
| `get.ai.market` (AAAA `100::`) | Proxied | `get-ai-market` Worker | Installer hub for AIM Data + AIM Node (see §Workers) |
| `pm-bounces.ai.market` | DNS-only | `pm.mtasv.net` | Postmark bounce handler |

**Email — Google Workspace + Postmark + SES + Resend (triple-vendor):**

| Type | Name | Target |
|------|------|--------|
| MX | `ai.market` | `aspmx.l.google.com`, `alt1` … `alt4.aspmx.l.google.com` (5 records, Google Workspace) |
| MX | `send.ai.market` | `feedback-smtp.us-east-1.amazonses.com` (SES outbound subdomain) |
| TXT | `ai.market` | `v=spf1 include:_spf.google.com … include:amazonses.com …` |
| TXT | `ai.market` | `google-site-verification=EUpRHpNxWk_…` |
| TXT | `_dmarc.ai.market` | `v=DMARC1; p=none;` |
| TXT | `resend._domainkey.ai.market` | `p=MIGfMA0GCSqGSIb3DQEBAQU…` (Resend DKIM) |
| TXT | `send.ai.market` | `v=spf1 include:amazonses.com ~all` |

**Domain verification TXT (don't touch — Railway / Lovable / Search Console):**

- `_railway-verify.ai.market`, `_railway-verify.www.ai.market`, `_railway-verify.ops.ai.market`, `_railway-verify.secrets.ai.market`
- `_lovable.ops.ai.market` (two records — investigate if both still needed)

**NS records (delegation indicator):**

The zone contains NS records pointing at name.com nameservers (`ns1cvw.name.com`, `ns2btz.name.com`, `ns3ckl.name.com`, `ns4fmx.name.com`). These appear inside the Cloudflare zone alongside Cloudflare-proxied records, which is unusual — typically a Cloudflare-authoritative zone shows only Cloudflare's own NS. Live traffic to `mcp.ai.market` resolves to Cloudflare anycast IPs (`104.21.38.254`, `172.67.141.177`), confirming Cloudflare is in the actual serving path. SysAdmin follow-up: verify the registrar-level delegation chain — likely "Cloudflare for SaaS" / partial-DNS mode with name.com as registrar.

### `vectoraiz.com` zone (8 records)

| Type | Name | Proxied | Target | Notes |
|------|------|---------|--------|-------|
| CNAME | `vectoraiz.com` (apex) | Proxied | `2hpir0hi.up.railway.app` | vectoraiz-website |
| CNAME | `www.vectoraiz.com` | Proxied | `jt51g3xl.up.railway.app` | vectoraiz-website |
| CNAME | `dev.vectoraiz.com` | Proxied | `vectoraiz-frontend-production.up.railway.app` | dev surface |
| CNAME | `api.vectoraiz.com` | DNS-only | `mnvi2z45.up.railway.app` | vectoraiz API |
| AAAA | `get.vectoraiz.com` | Proxied | `100::` | `vectoraiz-installer` Worker |
| TXT | `_railway-verify.vectoraiz.com` | DNS-only | `railway-verify=e14a36a2…` | Railway domain claim |
| TXT | `_railway-verify.www.vectoraiz.com` | DNS-only | `railway-verify=68b5db4c…` | Railway domain claim |
| TXT | `_lovable.app.vectoraiz.com` | DNS-only | `lovable_verify=9f2625e3…` | Lovable verification |

**Note:** there is no `mcp.vectoraiz.com` record in this zone. The `mcp.vectoraiz.com.ai.market` record in the ai.market zone (drift item above) may have been intended to live here.

## Cloudflare Workers (4)

| Worker name | Routes | Source-of-truth | Last deploy | Notes |
|-------------|--------|-----------------|-------------|-------|
| `get-ai-market` | `get.ai.market/`, `get.ai.market/aim-data*`, `get.ai.market/aim-node*` | `aidotmarket/cf-get-worker` (standalone repo; wrangler) | 2026-04-09 | **Canonical** installer hub for AIM Data + AIM Node. Serves landing pages + proxies `install.sh`, `install.ps1`, `docker-compose.yml` from product repos. No GITHUB_TOKEN binding — uses unauthenticated raw.githubusercontent.com (rate-limit risk under load). |
| `vectoraiz-installer` | `get.vectoraiz.com/*` | **Dashboard-only / API-only — NO source repo** ⚠ | 2026-02-25 | Proxies vectoraiz installer scripts. Has channel routing (stable/RC/marketplace). Has `GITHUB_TOKEN` binding. **Drift: source-control this Worker — see §Drift item 2.** |
| `aim-node-installer` | `[Unknown — Worker Routes API requires elevated token]` | **Dashboard-only / API-only — NO source repo** ⚠ | 2026-04-08 | Source preview shows it proxies the `aidotmarket/aim-node` GitHub repo with routes for `/rc`, `/windows`, `/aim-node/rc`, `/aim-node/windows`. Has `GITHUB_TOKEN` binding. Likely superseded by `get-ai-market`'s `/aim-node*` route handling; SysAdmin to confirm and decommission. |
| `allai-dead-man-switch` | (cron-only — no HTTP routes) | `aidotmarket/ai-market-backend` → `workers/` (wrangler) | 2026-03-12 | Monitors allAI Brain heartbeat at `https://api.ai.market/api/v1/internal/heartbeat/brain`, alerts via Telegram on consecutive failures. Cron `*/5 * * * *`. KV namespace `DMS_KV` (`d82ea459cc3e4025a41393b8b8190ce9`). Secret mirrors `HEARTBEAT_URL`, `INTERNAL_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — see Worker-secret rotation discipline below. |

### `get-ai-market` — installer hub for AIM Data + AIM Node

Source: `/Users/max/Projects/ai-market/cf-get-worker` (repo `aidotmarket/cf-get-worker`).

Routes (from `wrangler.toml`):

- `get.ai.market/aim-data*` — proxies from `aidotmarket/vectoraiz` repo (`installers/aim-data/install.sh`, `install.ps1`; `docker-compose.aim-data.yml`)
- `get.ai.market/aim-node*` — proxies from `aidotmarket/aim-node` repo
- `get.ai.market/` — landing page

Deploy:

    cd /Users/max/Projects/ai-market/cf-get-worker
    npx wrangler deploy

Verify:

    curl -sL https://get.ai.market/aim-data/install.sh | head -5
    curl -sL https://get.ai.market/aim-node/install.sh | head -5
    curl -sL https://get.ai.market/ | head -20

### `vectoraiz-installer` — get.vectoraiz.com installer

**Source-of-truth: Dashboard-only.** This Worker has no local repo and no wrangler.toml. Last deploy was via direct API upload (`source=api`), 2026-02-25. Changes today require re-uploading via the multipart-API pattern below; until source-controlled, the worker.js content can only be retrieved by API export.

Routes: `get.vectoraiz.com/*`. Behavior (per previous runbook content):

| Route | Behavior | Channel |
|-------|----------|---------|
| `get.vectoraiz.com/` | Stable installer from `main` branch | `stable` |
| `get.vectoraiz.com/market` | Marketplace installer — sets `VECTORAIZ_CHANNEL=marketplace` | `marketplace` |
| `get.vectoraiz.com/rc` | Latest RC installer (fetches latest prerelease, generates wrapper) | `rc` |
| `get.vectoraiz.com/{path}` | Any file from `main` branch | n/a |

Bindings:

- `GITHUB_TOKEN` (secret_text) — authenticated GitHub API calls, 5000 req/hr

Response headers:

- `x-vectoraiz-installer: v1`
- `x-vectoraiz-channel: stable | rc | marketplace`

Cache:

- Stable & marketplace: 5 min
- RC: 2 min

Deploy via API (multipart, required for ES modules format) — see §Worker deploy patterns below.

Verify:

    curl -sL https://get.vectoraiz.com/market | head -10
    curl -sL https://get.vectoraiz.com | head -5
    curl -sI https://get.vectoraiz.com/market | grep x-vectoraiz

### `aim-node-installer` — likely deprecated

**Source-of-truth: Dashboard-only.** Last deploy 2026-04-08 via wrangler (author max@ai.market) but no local wrangler.toml found, so the source directory was deleted or never landed in a repo.

Source preview (retrieved via API): proxies `aidotmarket/aim-node` GitHub repo. Routes: `/rc`, `/aim-node/rc`, `/windows`, `/aim-node/windows`, fallback `/install.sh`.

Likely superseded by `get-ai-market`'s `/aim-node*` route. SysAdmin verify (a) whether anything still routes to this Worker, (b) if not, delete it to remove the knowledge leak.

### `allai-dead-man-switch` — DMS heartbeat Worker

Source: `/Users/max/Projects/ai-market/ai-market-backend/workers/dead-man-switch.js`. Wrangler config: `ai-market-backend/workers/wrangler.toml`.

Behavior: polls `https://api.ai.market/api/v1/internal/heartbeat/brain` every 5 min via cron, alerts to Telegram after 2 consecutive failures; suppresses to once per 24h for `never_seen` state.

Bindings:

| Worker secret | Source of truth | Purpose |
|---------------|-----------------|---------|
| `HEARTBEAT_URL` | Static — `https://api.ai.market/api/v1/internal/heartbeat/brain` | The endpoint the Worker polls |
| `INTERNAL_API_KEY` | Infisical `ai-market-backend` prod → `INTERNAL_API_KEY` | `X-Internal-API-Key` header sent to backend |
| `TELEGRAM_BOT_TOKEN` | Infisical → `TELEGRAM_BOT_TOKEN` | Alert delivery |
| `TELEGRAM_CHAT_ID` | Infisical → `TELEGRAM_CHAT_ID` | Alert delivery target |
| `DMS_KV` (KV namespace) | `d82ea459cc3e4025a41393b8b8190ce9` | Stores `dms:failure_count`, `dms:last_alert_ts`, `dms:agent_state` |

**Infisical-mirror discipline:** Worker secrets are write-only after set, so drift between Infisical and the Worker is invisible until the Worker starts 401-spamming Telegram. **Any rotation of an Infisical value that this Worker mirrors must also be pushed to the Worker in the same operation.** There is no automatic sync.

Rotation example (`INTERNAL_API_KEY`):

    cd /Users/max/Projects/ai-market/ai-market-backend/workers
    KEY=$(infisical secrets get INTERNAL_API_KEY \
      --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c \
      --env prod --domain https://secrets.ai.market --plain)
    echo -n "$KEY" | npx wrangler secret put INTERNAL_API_KEY

Verify:

    curl -sI https://api.ai.market/api/v1/internal/heartbeat/brain \
      -H "X-Internal-API-Key: $KEY" | head -1   # expect HTTP/2 200

**If `wrangler secret put` reports Success but the Worker keeps 401-ing** (observed S461; root cause not understood) — use the REST API workaround in §Worker deploy patterns then redeploy.

Inspect KV:

    for k in "dms:failure_count" "dms:last_alert_ts" "dms:agent_state"; do
      echo "--- $k ---"
      npx wrangler kv key get "$k" --remote \
        --namespace-id d82ea459cc3e4025a41393b8b8190ce9
    done
    # Healthy: failure_count=0, agent_state=was_alive

When the DMS breaks:

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Telegram spam: "allAI Brain DMS Alert … HTTP 401" every 10 min | `INTERNAL_API_KEY` in Worker ≠ Infisical | Re-sync (commands above) |
| Telegram spam: "HTTP 503" or connection errors | Backend down or Railway deploy in progress | `railway status`; usually self-clears on deploy finish |
| "last_seen=never" suppression alert | allAI Brain has never registered | Separate issue — investigate the Brain itself |
| No alerts when the Brain IS down | Worker cron stopped firing | Cloudflare dashboard → Workers → Cron triggers |

### Worker deploy patterns (shared reference)

**Multipart ES-modules deploy** (required for any Worker with `export default` syntax — applies to `vectoraiz-installer`, `aim-node-installer`, anything else dashboard-deployed):

    CF_TOKEN=$(infisical secrets get CLOUDFLARE_API_TOKEN \
      --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c \
      --env prod --plain --silent --domain https://secrets.ai.market)
    ACCT_ID="d5346d3e0f8f344c5f4915aaca689adf"

    cat > /tmp/cf_body << MULTIPART
    ------CloudflareWorkerUpload
    Content-Disposition: form-data; name="metadata"
    Content-Type: application/json

    {"main_module":"worker.js","keep_bindings":["secret_text"]}
    ------CloudflareWorkerUpload
    Content-Disposition: form-data; name="worker.js"; filename="worker.js"
    Content-Type: application/javascript+module

    $(cat /path/to/worker.js)
    ------CloudflareWorkerUpload--
    MULTIPART

    curl -s -X PUT \
      -H "Authorization: Bearer $CF_TOKEN" \
      -H "Content-Type: multipart/form-data; boundary=----CloudflareWorkerUpload" \
      --data-binary @/tmp/cf_body \
      "https://api.cloudflare.com/client/v4/accounts/$ACCT_ID/workers/scripts/<SCRIPT_NAME>"

⚠ `Content-Type: application/javascript` (non-multipart) uploads fail with "Unexpected token 'export'" because CF treats it as Service Worker format. Must use multipart with `application/javascript+module`.

**Secret-set via REST API workaround** (when `wrangler secret put` reports Success but the Worker keeps using the old value — observed S461 on the DMS Worker):

    curl -s -X PUT \
      -H "Authorization: Bearer $CF_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"SECRET_NAME\",\"text\":\"$VALUE\",\"type\":\"secret_text\"}" \
      "https://api.cloudflare.com/client/v4/accounts/$ACCT_ID/workers/scripts/<SCRIPT_NAME>/secrets"

    cd /path/to/wrangler/dir
    npx wrangler deploy   # force fresh deployment to rebind
    npx wrangler versions list --name <SCRIPT_NAME> | head -5

## Cloudflare Tunnel — mcp.ai.market

**This is the live transport for `mcp.ai.market`.** Despite earlier docs claiming a Tailscale Funnel migration, the active path today is Cloudflare's `cloudflared` tunnel running on Titan-1.

| Field | Value |
|-------|-------|
| Tunnel name | `koskadeux` |
| Tunnel UUID | `007ddc34-de07-474c-adbc-a648663b9c78` |
| Created | `2026-02-17T10:47:48Z` |
| Local config | `/Users/max/.cloudflared/config.yml` (credentials at `/Users/max/.cloudflared/007ddc34-de07-474c-adbc-a648663b9c78.json`) |
| LaunchAgent | `com.koskadeux.cloudflared` → `/opt/homebrew/bin/cloudflared tunnel --config /Users/max/.cloudflared/config.yml run koskadeux` |
| DNS record | CNAME `mcp.ai.market` → `007ddc34-de07-474c-adbc-a648663b9c78.cfargotunnel.com` (proxied) |
| Ingress | `mcp.ai.market` → `http://localhost:8767` (gateway proxy) — admin path `^/api/admin/.*$` returns 404 |
| cloudflared version (deployed) | 2026.2.0 (upgrade available to 2026.5.0) |

Ingress config verbatim:

    tunnel: 007ddc34-de07-474c-adbc-a648663b9c78
    credentials-file: /Users/max/.cloudflared/007ddc34-de07-474c-adbc-a648663b9c78.json

    ingress:
      - hostname: mcp.ai.market
        path: ^/api/admin/.*$
        service: http_status:404
      - hostname: mcp.ai.market
        service: http://localhost:8767
        originRequest:
          noTLSVerify: true
          connectTimeout: 30s
          keepAliveTimeout: 900s
          keepAliveConnections: 20
      - service: http_status:404

**Parallel Tailscale Funnel exists but is not what `mcp.ai.market` is using.** `tailscale funnel status` shows:

    https://koskadeux-10.tail30cd96.ts.net (Funnel on)
    |-- / proxy http://localhost:8767

This is a separate public surface on the Tailscale-issued hostname. It's available as a fallback if the cloudflared tunnel ever goes dark, but **no DNS record points at it today**. If you want Tailscale Funnel to take over `mcp.ai.market`, you have to (a) cut over the CNAME and (b) decommission the cloudflared tunnel — neither has been done.

### Tunnel operations

    # Status from Titan-1
    cloudflared tunnel list                       # find the koskadeux tunnel
    cloudflared tunnel info koskadeux             # connection details

    # Process check
    ps -ef | grep -i cloudflared | grep -v grep
    launchctl list | grep com.koskadeux.cloudflared

    # Restart
    launchctl kickstart -k gui/$(id -u)/com.koskadeux.cloudflared

### Tunnel troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `mcp.ai.market` returns 502/504 from claude.ai | cloudflared connection lost / restarting | `launchctl kickstart -k gui/$(id -u)/com.koskadeux.cloudflared` |
| `mcp.ai.market` resolves but connection refused | gateway proxy on `:8767` not listening | `lsof -iTCP:8767 -sTCP:LISTEN`; restart `com.koskadeux.gateway` |
| `mcp.ai.market` returns 404 on every path | `path: ^/api/admin/.*$` rule matching too broadly or ingress misordered | Edit `~/.cloudflared/config.yml`, restart cloudflared |
| Admin endpoints accidentally exposed | Ingress rule order wrong | Verify `/api/admin/*` rule precedes the catch-all (current config is correct) |
| New tunnel needed | Old credentials lost or rotating | `cloudflared tunnel create <name>` + update DNS CNAME + update config.yml |

For the wider MCP gateway path (gateway proxy on `:8767` → real handler on `:8765` → tool execution), see `mcp-gateway.md`. That runbook covers the local process tree and should be cross-referenced when troubleshooting tool-call failures that turn out to be local-process problems rather than tunnel problems.

## Drift inventory (S688 audit findings)

These are the gaps between documented state and live state, discovered during the S688 verification pass. Each is a SysAdmin-eligible follow-up.

1. **`mcp.ai.market` transport documentation drift.** Both `mcp-gateway.md` (pre-this-revision) and `config:resource-registry` claimed Tailscale Funnel had replaced Cloudflare Tunnel pre-S572. **The cloudflared service is still active** (PID 2041, Wed 11AM start) and is the actual transport. The Tailscale Funnel exists on a separate hostname but is not in the DNS path for `mcp.ai.market`. *Action:* either (a) actually complete the Tailscale migration and decommission cloudflared, or (b) update the registry + gateway runbook to match the cloudflared reality.

2. **`vectoraiz-installer` Worker has no source repo.** Last deploy was 2026-02-25 via direct API upload. Worker code can only be retrieved by API export. *Action:* extract current worker.js, commit to a Worker source repo (`aidotmarket/cf-vectoraiz-installer` recommended, mirroring `cf-get-worker`), redeploy via wrangler to confirm round-trip.

3. **`aim-node-installer` Worker is probably stale.** No local source, no wrangler config. Functionality appears subsumed by `get-ai-market`'s `/aim-node*` routes. *Action:* SysAdmin verify nothing actively routes to this Worker, then delete the script.

4. **DNS record `mcp.vectoraiz.com.ai.market` is a 4-label oddity.** Points to the same tunnel as `mcp.ai.market`. Looks like a typo where someone meant to create `mcp.vectoraiz.com` (in the vectoraiz.com zone) but accidentally typed it as a subdomain of ai.market. *Action:* delete unless someone deliberately set this up.

5. **`com.koskadeux.cloudflared` LaunchAgent is NOT decommissioned.** The `config:resource-registry` description marks it as "stale/redundant — SysAdmin follow-up to decommission." It's currently the only thing keeping `mcp.ai.market` reachable. *Action:* before any decommission, complete drift item 1.

A sixth, related item: **The Cloudflare API token in Infisical lacks Worker Routes + Cloudflare Tunnel scopes.** Both endpoints return `10000 Authentication error`. Not urgent — dashboard and `cloudflared` CLI cover those surfaces — but the token should be widened or split if we want Workers-routes verification fully API-driven.

## Verification quick reference

End-to-end public surfaces:

    # Frontend
    curl -sI https://ai.market | head -3
    curl -sI https://www.ai.market | head -3

    # Backend API
    curl -sI https://api.ai.market/healthz | head -3

    # Ops dashboard
    curl -sI https://ops.ai.market | head -3

    # Infisical
    curl -sI https://secrets.ai.market | head -3

    # MCP gateway (Cloudflare Tunnel + Koskadeux)
    curl -s -i https://mcp.ai.market/.well-known/oauth-protected-resource | head -10
    # Expect HTTP/2 200 + RFC 9728 metadata document.

    # Installer hubs
    curl -sL https://get.ai.market/aim-data/install.sh | head -3   # AIM Data
    curl -sL https://get.ai.market/aim-node/install.sh | head -3   # AIM Node
    curl -sL https://get.vectoraiz.com | head -3                   # vectoraiz
    curl -sI https://get.vectoraiz.com/market | grep x-vectoraiz   # channel header check

Re-fetch full DNS inventory:

    CF_TOKEN=$(infisical secrets get CLOUDFLARE_API_TOKEN \
      --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c \
      --env prod --plain --silent --domain https://secrets.ai.market)

    for ZONE in f82ac6762af544d71e8ad5eb3d7fca0c 401a4cf862898bc4dd6d03e2a0f50273; do
      curl -s -H "Authorization: Bearer $CF_TOKEN" \
        "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?per_page=100" | jq '.result[] | {type, name, content, proxied}'
    done

List active Workers:

    curl -s -H "Authorization: Bearer $CF_TOKEN" \
      "https://api.cloudflare.com/client/v4/accounts/d5346d3e0f8f344c5f4915aaca689adf/workers/scripts" | \
      jq -r '.result[] | "\(.id)\t\(.modified_on)"'

## History

- **2026-02-17** — `koskadeux` Cloudflare Tunnel created (UUID `007ddc34…`); `mcp.ai.market` cuts over to tunnel.
- **2026-02-25** — `vectoraiz-installer` Worker last deployed via direct API (no repo source-of-truth from this point forward — see drift item 2).
- **2026-03-12** — `allai-dead-man-switch` Worker shipped (`ai-market-backend/workers/`); cron `*/5 * * * *` heartbeat monitor.
- **2026-03-20** — `vectoraiz-installer` Worker last documented update (per old `cloudflare-worker.md` runbook).
- **2026-04-08** — `aim-node-installer` Worker deployed (no source repo found; likely superseded by `get-ai-market`).
- **2026-04-09** — `get-ai-market` Worker shipped (repo `aidotmarket/cf-get-worker`); canonical installer hub for AIM Data + AIM Node.
- **Pre-S572** — Resource registry + `mcp-gateway.md` claim Tailscale Funnel replaced Cloudflare Tunnel for `mcp.ai.market`. **Migration did not complete** — cloudflared remains the active transport (S688 verification).
- **S688 (2026-05-22)** — Live audit; this runbook authored. Five drift items filed.

## References

- `mcp-gateway.md` — Tailscale Funnel + Koskadeux MCP process tree on Titan-1. Cross-reference for tool-call path debugging.
- `ai-market-backend/docs/core/INFRASTRUCTURE.md` — formerly held the partial Cloudflare table; should be reduced to a one-line pointer to this runbook.
- `cloudflare-worker.md` — legacy runbook; content is fully subsumed here. Mark deprecated.
- `infisical-secrets.md` — patterns for fetching `CLOUDFLARE_API_TOKEN` and Worker-secret mirrors.
- `seo-infrastructure.md` — Google Search Console + Bing Webmaster + the AI-crawler discovery surfaces; DNS-adjacent but separate concern.
- `config:resource-registry` — Living State entity with the canonical map of accounts, project IDs, hostnames. `secrets`, `services`, `launchd_services`, `infisical_projects` sections all interact with this runbook.

## Discipline

- **Before any Cloudflare change**, re-fetch the live DNS + Worker inventory via the API commands in §Verification — the documented table can drift between sessions, and the §Drift list above shows it has done so repeatedly.
- **Worker secret rotation is a two-step**: Infisical first, then `wrangler secret put` (or the REST API workaround for the wrangler-reports-success-but-doesn't-take pattern). Forgetting the second step causes invisible 401-storms.
- **Any new Worker must land in a repo before it ships to production.** `vectoraiz-installer` and `aim-node-installer` are the cautionary tales — dashboard-only / API-only deploys become knowledge leaks the moment whoever deployed them stops remembering.
- **Any new DNS record added by hand** (Cloudflare dashboard or partner UI) must be reflected here in the next session — re-run the DNS verification query and update the §`ai.market` zone / §`vectoraiz.com` zone tables.
- **`mcp.ai.market` transport changes** require coordinated DNS + LaunchAgent + ingress-config edits. The current cloudflared / Tailscale Funnel ambiguity (drift item 1) is the kind of half-finished migration this discipline is meant to prevent.

## Google Search Console domain verification (added S806)
The `search-submission@aimarket-prod.iam.gserviceaccount.com` service account is a **verified owner** of `ai.market` (domain-level) via a `google-site-verification=` TXT record on the zone root, created through the Cloudflare API. Do not delete that TXT record — Google rechecks it periodically and removal revokes the service account's ownership, which silently kills Google sitemap/indexing submissions (the search fan-out pipeline). The SA key lives in Infisical `ai-market-backend`/prod as `GSC_SERVICE_ACCOUNT_JSON`. Registered properties: `sc-domain:ai.market`, `https://ai.market/`, `https://api.ai.market/`.
