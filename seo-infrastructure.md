# SEO Infrastructure Runbook

Internal infrastructure for search engine indexing and AI crawler discovery.

## Google Search Console

**Property:** `ai.market` (domain property, verified via DNS TXT record on Cloudflare)
**URL:** https://search.google.com/search-console?resource_id=sc-domain:ai.market
**Owner:** Max Robbins (max@ai.market)

### Service Account (Indexing API)

**Email:** `kms-trust-agent@aimarket-prod.iam.gserviceaccount.com`
**GCP Project:** `aimarket-prod`
**Added as:** Owner in Search Console (required for Indexing API)
**Key storage:** `GCP_SERVICE_ACCOUNT_JSON` in Infisical (prod env), injected into Railway at deploy

### Enabled GCP APIs

- `indexing.googleapis.com` — Web Search Indexing API (submit/remove URLs)
- `searchconsole.googleapis.com` — Search Console API (read performance data)

### How URL Submission Works

Backend service at `app/services/search_submission_providers/google.py` uses the Indexing API to notify Google when listings are published or updated. The service authenticates via Application Default Credentials loaded from `GCP_SERVICE_ACCOUNT_JSON`.

Credential setup happens at startup in `app/core/gcp_credentials.py`:
1. Reads `GCP_SERVICE_ACCOUNT_JSON` from env
2. Writes to temp file
3. Sets `GOOGLE_APPLICATION_CREDENTIALS` env var
4. GCP client libraries authenticate automatically via ADC

### Sitemaps

| Sitemap | Source | Contents |
|---------|--------|----------|
| `https://ai.market/sitemap.xml` | Frontend (Next.js) | Static pages (home, /listings) |
| `https://api.ai.market/sitemap-listings.xml` | Backend (FastAPI) | All published listing detail pages |

Both are referenced in `robots.txt` (served by frontend). Google Search Console has both submitted.

### robots.txt

Served by frontend at `https://ai.market/robots.txt`. Source: `app/robots.txt/route.ts`.

Allows all crawlers, blocks `/dashboard`, `/login`, `/register`, `/api/`. References both sitemaps.

## Bing Webmaster

**URL:** https://www.bing.com/webmasters
**API Key:** `BING_WEBMASTER_API_KEY` in Infisical (prod env)
**Submission provider:** `app/services/search_submission_providers/bing.py`

### Setup Steps (if key needs rotation)

1. Go to https://www.bing.com/webmasters
2. Sign in with ai.market Microsoft account
3. Settings → API access → Generate new key
4. `infisical secrets set BING_WEBMASTER_API_KEY "<key>" --env prod --domain https://secrets.ai.market`
5. Redeploy Railway backend

## AI Crawler Discovery

- `/llms.txt` — LLM-readable site description with dataset listings
- `/.well-known/ai-agents.json` — Agent discovery manifest
- `/.well-known/ai-plugin.json` — OpenAI plugin manifest

All served by the backend. Crawl stats tracked at `GET /internal/ai-crawl-stats` (internal API key).

## APScheduler Jobs

- **Search submission drain:** Every 2 minutes, drains pending URL submissions to Google + Bing
- **Discovery readiness refresh:** Every 4 hours, recalculates readiness scores for all listings

## Troubleshooting

### "No robots.txt file" in Search Console
Search Console caches aggressively. Verify directly: `curl -I https://ai.market/robots.txt` (should be 200). GSC will pick it up within 24-48 hours.

### "No crawl data"
Submit sitemaps manually in Search Console → Sitemaps. Use URL Inspection → Request Indexing for priority pages.

### Indexing API 403
Service account must be **Owner** (not just User) in Search Console. Verify at Settings → Users and permissions.

### GCP credentials not loading
Check Railway logs for `GCP_SERVICE_ACCOUNT_JSON not set`. Verify in Infisical: `infisical secrets get GCP_SERVICE_ACCOUNT_JSON --env prod --domain https://secrets.ai.market`
