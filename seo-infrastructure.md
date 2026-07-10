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

> **Owning runbook moved:** dataset-card-publishing.md is now the §A–K source of truth for HF/Kaggle/data.world card publishing (created S1167). The sections below are retained as narrative history; consult the owning runbook first.

Flag-gated push channel: every published/updated listing with a disclosure snapshot gets a HF dataset repo + README card. `HUGGINGFACE_SUBMISSION_ENABLED` defaults to `False` (app/core/config.py); **as of S1164 (2026-07-09) it is SET to `true` in Railway prod alongside `HUGGINGFACE_TOKEN` — the channel is LIVE.** Flipping it remains a Max-only production action. As of S1164 (Council unanimous + Max directive, backend 26ac843e): METADATA-ONLY cards publish for EVERY published/updated listing with NO disclosure snapshot required — the card is rendered from public listing fields only (title/description/tags/price/backlink), carries a metadata-only directory-listing disclaimer, license falls back to `other` (normalized: URLs/free-text never enter the YAML license field), and the no-snapshot branch is structurally README-only (stale data files swept). Actual data/sample rows still publish ONLY with a seller-approved disclosure snapshot (sample_decision=approved_rows, exact version) — seller consent remains mandatory beyond public metadata. First live card: huggingface.co/datasets/ai-market/eolymp-problem-dataset-5ab53e16-sample.

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

### Troubleshooting (cont.)
- llms.txt shows an error or missing listings → as of S1164 the endpoint never renders exception text (neutral fallback + per-section catch, backend f1fbda17). If "Public discovery metadata is temporarily limited." or "Featured listings are temporarily unavailable." appears, read backend logs (logger "Error generating llms.txt" / "Failed generating featured listings section"). Historical cause (T-2026-000204): featured_service recent_sales queried a non-existent transactions table; now reads purchases.

## Kaggle + data.world Metadata-Card Publishing (S1164, backend d52ebef4)
Two further metadata-only card channels replicating the HF pattern under identical invariants — metadata-only PERIOD (no row-publishing mode exists in code). Flag-gated OFF by default: `KAGGLE_SUBMISSION_ENABLED`, `DATAWORLD_SUBMISSION_ENABLED` (app/core/config.py; not set in Railway). KAGGLE IS LIVE (S1164): `KAGGLE_USERNAME`=maxrobbinsaimarket + `KAGGLE_API_TOKEN` (KGAT_ token, **Bearer-only** — Basic auth returns 401; code 3aefc42c prefers KAGGLE_API_TOKEN, legacy KAGGLE_KEY Basic fallback retained) + `KAGGLE_SUBMISSION_ENABLED`=true, all in Infisical prod AND Railway backend env, registered in config:resource-registry secrets. First live card: kaggle.com/datasets/maxrobbinsaimarket/eolymp-problem-dataset-5ab53e16 (published manually S1164 via the proven contract below). **RESOLVED S1167: T-2026-000207** (blob-token flow live, merges 6ccbd78d + b0562cc4; owning detail now in dataset-card-publishing.md). The proven Kaggle contract is: (1) POST /api/v1/blobs/upload (Bearer, JSON {type:dataset,name,contentLength}) -> {token,createUrl}; (2) PUT bytes to createUrl (no Kaggle auth header); (3) POST /api/v1/datasets/create/new (Bearer, JSON with title<=50 chars hard limit, slug, ownerSlug, licenseName, isPrivate:false, files:[{token}]) — NOTE HTTP 200 with body.status="Error" is a FAILURE, check the body. App path live-verified S1167; title collisions ('already in use') route to the version path. data.world: `DATAWORLD_API_TOKEN` does not exist yet — awaiting Max; flag off. Kaggle publish uploads exactly one file (README.md = the card) via kaggle.com/api/v1 Basic auth; data.world creates/updates an OPEN dataset with the card as summary via api.data.world/v0. Success persists source_delivery.kaggle_url / dataworld_url and adds them to JSON-LD sameAs. Migration 20260710_001 widened ck_ssj_provider to include kaggle/dataworld (single alembic head, parented on t200_email_ingest_receipt). Troubleshooting: jobs dead with credential errors → check the four env vars; retries capped at MAX_ATTEMPTS=5. Known parity follow-up (GLM LOW, applies to HF too): URL persistence runs after remote creation; a persist failure can leave a remote card without a local URL reference.
