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
- API token: `CLOUDFLARE_API_TOKEN` in Doppler (ai-market/prd)
- Last deployed: 2026-03-20

## Deploy via API

```bash
CF_TOKEN=$(doppler secrets get CLOUDFLARE_API_TOKEN -p ai-market --config prd --plain)
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
