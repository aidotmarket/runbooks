# Cloudflare Worker (get.vectoraiz.com)

## What it does

Proxies vectorAIz installer scripts from GitHub. Serves stable, RC, and marketplace-channel installers.

## Routes

| Route | Behavior | Channel |
|-------|----------|---------|
| `get.vectoraiz.com/` | Stable installer from `main` branch | `direct` (default) |
| `get.vectoraiz.com/market` | Marketplace installer — sets `VECTORAIZ_CHANNEL=marketplace` | `marketplace` |
| `get.vectoraiz.com/rc` | Latest RC installer (fetches latest prerelease, generates wrapper) | `stable` (RC) |
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

- Stable: 5 min
- Marketplace: 5 min
- RC: 2 min

## Configuration

- Format: ES modules (migrated from Service Worker in S215)
- Source: Cloudflare dashboard via API
- Secret binding: `GITHUB_TOKEN` for authenticated GitHub API calls (5000 req/hr)
- Worker name: `get-vectoraiz-installer` (in Cloudflare dashboard)

## Adding / updating the `/market` route

The Worker code lives in the Cloudflare dashboard (Workers & Pages → `get-vectoraiz-installer` → Quick Edit). The `/market` handler generates a wrapper bash script:

```javascript
// Inside the fetch handler's route matching:
if (url.pathname === '/market') {
  const stableScript = await fetchFromGitHub('install.sh', env);
  const wrapper = `#!/bin/bash
export VECTORAIZ_CHANNEL=marketplace
${stableScript}`;
  return new Response(wrapper, {
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'cache-control': 'public, max-age=300',
      'x-vectoraiz-installer': 'v1',
      'x-vectoraiz-channel': 'marketplace',
    },
  });
}
```

After editing, click "Save and deploy" in the Cloudflare dashboard.

## Verify after deploy

```bash
# Should return installer with VECTORAIZ_CHANNEL=marketplace near the top
curl -sL https://get.vectoraiz.com/market | head -5

# Should return standard installer (no channel export)
curl -sL https://get.vectoraiz.com | head -5

# Should return RC installer
curl -sL https://get.vectoraiz.com/rc | head -5
```

## When it breaks

| Symptom | Fix |
|---------|-----|
| `/market` returns 404 | Route handler missing in Worker code — re-add per snippet above |
| Installer 404 | Check GitHub repo has `install.sh` on `main` branch |
| RC returns stale version | Wait 2 min for cache expiry |
| Rate limited | Check `GITHUB_TOKEN` binding in Cloudflare dashboard |
| Worker errors | Cloudflare dashboard → Workers → `get-vectoraiz-installer` → Logs |
| Channel not set after install | Check VZ `.env` file has `VECTORAIZ_CHANNEL=marketplace` |
| Wrong channel in VZ | Re-install with correct URL, or manually edit `.env` and restart |
