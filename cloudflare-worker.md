# Cloudflare Worker (get.vectoraiz.com)

## What it does

Proxies vectorAIz installer scripts from GitHub. Serves stable, RC, and marketplace-channel installers.

## Routes

| Route | Behavior | Channel |
|-------|----------|---------|
| `get.vectoraiz.com/` | Stable installer from `main` branch | `stable` |
| `get.vectoraiz.com/market` | Marketplace installer — sets `VECTORAIZ_CHANNEL=marketplace` | `marketplace` |
| `get.vectoraiz.com/rc` | Latest RC installer (fetches latest prerelease, generates wrapper) | `rc` |
| `get.vectoraiz.com/{path}` | Any file from `main` branch | n/a |

## How channels work

- The `/market` route serves a wrapper script that `export VECTORAIZ_CHANNEL=marketplace` before running the standard installer
- The installer script writes this to the VZ `.env` file during setup
- VZ reads `VECTORAIZ_CHANNEL` at startup and adapts sidebar order, allAI persona, and onboarding emphasis (see BQ-VZ-CHANNEL)
- Channel is **presentation-only** — never affects permissions, features, billing, or access control
- The download page at `ai.market/download` uses `/market` for "For Data Sellers" and `/` for "For Data Processing"

## Headers

| Header | Values |
|--------|--------|
| `x-vectoraiz-installer` | `v1` |
| `x-vectoraiz-channel` | `stable`, `rc`, or `marketplace` |

## Cache

- Stable & marketplace: 5 min
- RC: 2 min

## Configuration

- Format: ES modules
- Cloudflare account ID: `d5346d3e0f8f344c5f4915aaca689adf`
- Worker name: `vectoraiz-installer`
- Secret binding: `GITHUB_TOKEN` for authenticated GitHub API calls (5000 req/hr)
- API token: `CLOUDFLARE_API_TOKEN` in Infisical (ai-market/prd) / Railway env
- Last deployed: 2026-03-20

## Deploy via API

```bash
CF_TOKEN=$(infisical secrets get CLOUDFLARE_API_TOKEN --env=prod --plain 2>/dev/null || railway variables get CLOUDFLARE_API_TOKEN)
ACCT_ID="d5346d3e0f8f344c5f4915aaca689adf"

# Build multipart body (ES modules format — part name must match main_module)
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
  "https://api.cloudflare.com/client/v4/accounts/$ACCT_ID/workers/scripts/vectoraiz-installer"
```

NOTE: `Content-Type: application/javascript` (non-multipart) uploads fail with "Unexpected token 'export'" because CF treats it as Service Worker format. Must use multipart with `application/javascript+module`.

## Verify after deploy

```bash
# Should show VECTORAIZ_CHANNEL=marketplace
curl -sL https://get.vectoraiz.com/market | head -10

# Standard installer
curl -sL https://get.vectoraiz.com | head -5

# RC installer
curl -sL https://get.vectoraiz.com/rc | head -5

# Headers check
curl -sI https://get.vectoraiz.com/market | grep x-vectoraiz
```

## When it breaks

| Symptom | Fix |
|---------|-----|
| `/market` returns 404 | Route handler missing in Worker code — redeploy via API |
| Installer 404 | Check GitHub repo has `install.sh` on `main` branch |
| RC returns stale version | Wait 2 min for cache expiry |
| Rate limited | Check `GITHUB_TOKEN` binding in Cloudflare dashboard |
| Worker errors | Cloudflare dashboard → Workers → Logs |
| Channel not set after install | Check VZ `.env` file has `VECTORAIZ_CHANNEL=marketplace` |
| Deploy fails "Unexpected token export" | Use multipart upload, not plain `Content-Type: application/javascript` |

---

# DMS Worker — allai-dead-man-switch

Separate Worker from the installer Worker above. Monitors the allAI Brain heartbeat and alerts via Telegram on consecutive failures.

- **Name**: `allai-dead-man-switch`
- **Source**: `ai-market-backend/workers/dead-man-switch.js`
- **Cron**: `*/5 * * * *` (wrangler.toml header comment says 2 min — stale comment, actual is 5 min)
- **KV**: `DMS_KV` (id `d82ea459cc3e4025a41393b8b8190ce9`)
- **Alerts**: after 2 consecutive failures; suppressed to once per 24h for `never_seen` state

## Worker secrets — IMPORTANT: Infisical mirror discipline

The DMS Worker holds Cloudflare secrets that MIRROR values stored in Infisical. Cloudflare Worker secrets are write-only after set, so drift between the two is invisible until the Worker starts returning auth errors.

| Worker secret       | Source of truth                                            | What it does |
|---------------------|------------------------------------------------------------|--------------|
| `HEARTBEAT_URL`     | Static — `https://api.ai.market/api/v1/internal/heartbeat/brain` | The endpoint the Worker polls |
| `INTERNAL_API_KEY`  | Infisical `ai-market-backend` prod → `INTERNAL_API_KEY`    | `X-Internal-API-Key` header sent to backend |
| `TELEGRAM_BOT_TOKEN`| Infisical (or local `.env`) → `TELEGRAM_BOT_TOKEN`         | Alert delivery |
| `TELEGRAM_CHAT_ID`  | Infisical (or local `.env`) → `TELEGRAM_CHAT_ID`           | Alert delivery target |

**Rotation rule**: any time you rotate a value in Infisical that the DMS Worker mirrors, you MUST also push it to the Worker in the same operation. There is no automatic sync. Forgetting this causes the DMS to spam Telegram alerts every 10 min with HTTP 401.

## Sync command (INTERNAL_API_KEY example)

```bash
cd /Users/max/Projects/ai-market/ai-market-backend/workers
KEY=$(infisical secrets get INTERNAL_API_KEY \
  --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c \
  --env prod --domain https://secrets.ai.market --plain)
echo -n "$KEY" | npx wrangler secret put INTERNAL_API_KEY
```

Repeat for any other rotated value. Verify with:

```bash
curl -sI https://api.ai.market/api/v1/internal/heartbeat/brain \
  -H "X-Internal-API-Key: $KEY" | head -1   # expect HTTP/2 200
```

## When the DMS breaks

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Telegram spam: "allAI Brain DMS Alert ... HTTP 401" every 10 min | `INTERNAL_API_KEY` in Worker ≠ Infisical value | Re-sync with the command above |
| Telegram spam: "HTTP 503" or connection errors | Backend down or Railway deploy in progress | Check `railway status`; usually self-clears on deploy finish |
| "last_seen=never" suppression alert | allAI Brain has never registered | Separate issue — investigate allAI Brain itself |
| No alerts when Brain IS actually down | Worker cron stopped firing | Check Cloudflare dashboard → Workers → Cron triggers |

## Future automation (TODO — tracked as SysAdmin skill, not yet built)

Long-term: SysAdmin agent should detect Infisical rotation events and auto-push to all mirror Workers. Until then, rotation is a manual two-step: Infisical first, then `wrangler secret put`. Any Worker that holds an Infisical mirror should be listed in this runbook so the operator knows where to propagate.
