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

## HuggingFace Dataset-Card Publishing (BQ-SEO-HF-PUBLISH-S804, shipped S1142)

Flag-gated push channel: every published/updated listing with a disclosure snapshot gets a HF dataset repo + README card. **`HUGGINGFACE_SUBMISSION_ENABLED` defaults to `False` (app/core/config.py) and is NOT set in Railway env — enabling it is a Max-only production action.** While off, no HF jobs are created.

How it works (all in ai-market-backend, merged main 7370d023):
- Orchestrator: `SearchSubmissionService._append_huggingface_job_if_needed` enqueues `huggingface/dataset_card` jobs for listing `published` + `updated` events (flag + disclosure_version required). Dispatch routes through `HuggingFaceSubmissionProvider.publish_dataset_card` → `HuggingFaceService.publish_dataset_card_for_search_submission`.
- Snapshot source: `DisclosureSnapshotService.get_snapshot_for_hf_card` (returns metadata-only snapshots too); the strict `get_snapshot_for_hf` keeps its 409 for no-row snapshots.
- Row-backed publish pushes ONLY seller-approved sample rows for the exact disclosure version. Metadata-only publish uploads README only AND deletes any previously published data files (`_remove_stale_hf_data_files`) — customer-data safety requirement, unanimous Council mandate.
- Idle-republish guard: an `updated` event is skipped only when BOTH disclosure_version AND rendered card hash match the last succeeded HF job (hashes stored as JSON in that job's `last_error` — known semantic wrinkle, GLM LOW finding).
- Backlink: `https://ai.market/listings/{slug}` (id fallback); card frontmatter carries license/tags/source_url/citation. On success, `Listing.source_delivery.huggingface_url` is persisted and listing JSON-LD `sameAs` regenerated via `generate_listing_jsonld`. JSON-LD-only regen failure logs an error but does not fail the job.
- Retry: HF 429/5xx retry; 400/401/403/404 terminal (`PERMANENT_FAILURE_CODES` now includes 404).

### Troubleshooting
- No HF jobs appearing → expected while `HUGGINGFACE_SUBMISSION_ENABLED` is unset/false. Check Railway variables (`railway variables --json | grep -i huggingface`).
- HF job dead with 401/403 → check `HUGGINGFACE_TOKEN` / `HUGGINGFACE_HUB_TOKEN` in prod secrets.
- Stale rows visible on HF after a seller withdraws sample approval → republish with the metadata-only snapshot; the publish path deletes non-README files. If `list_repo_files` is unavailable the fallback only sweeps data/train/test/validation folders (GLM LOW finding — stray root files could survive; escalate if seen).
- Card out of date after listing edit → confirm an `updated` submission event fired; the guard republishes whenever the rendered card hash differs.
