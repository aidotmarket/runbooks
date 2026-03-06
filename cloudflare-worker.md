# Cloudflare Worker (get.vectoraiz.com)

## What it does

Proxies vectorAIz installer scripts from GitHub. Serves stable and RC installers.

## Routes

| Route | Behavior |
|-------|----------|
| `get.vectoraiz.com/` | Stable installer from `main` branch |
| `get.vectoraiz.com/rc` | Latest RC installer (fetches latest prerelease, generates wrapper) |
| `get.vectoraiz.com/{path}` | Any file from `main` branch |

## Headers

| Header | Values |
|--------|--------|
| `x-vectoraiz-installer` | `v1` |
| `x-vectoraiz-channel` | `stable` or `rc` |

## Cache

- Stable: 5 min
- RC: 2 min

## Configuration

- Format: ES modules (migrated from Service Worker in S215)
- Source: Cloudflare dashboard via API
- Secret binding: `GITHUB_TOKEN` for authenticated GitHub API calls (5000 req/hr)
- Last deployed: 2026-03-04

## When it breaks

| Symptom | Fix |
|---------|-----|
| Installer 404 | Check GitHub repo has file at expected path on `main` |
| RC returns stale version | Wait 2 min for cache expiry |
| Rate limited | Check GITHUB_TOKEN binding in Cloudflare dashboard |
| Worker errors | Check Cloudflare Workers dashboard for logs |
