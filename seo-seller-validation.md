# Seller SEO Validation Runbook

Discovery health checks and readiness scoring for marketplace listings.

## Overview

BQ-SEOAI-VALIDATION provides per-listing readiness scores (A-F grades) based on 7 checks that determine how discoverable a listing is to search engines and AI crawlers.

## Architecture

**Service:** `app/services/discovery_validation_service.py`
**Schemas:** `app/schemas/discovery_validation.py`

### Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /seller/listings/{slug}/discovery-readiness` | JWT (seller) | Per-listing readiness score |
| `GET /internal/discovery-readiness/overview` | Internal API key | Platform-wide overview (admin) |

### 7 Readiness Checks

| Check | Weight | Severity | What it validates |
|-------|--------|----------|------------------|
| `json_ld_present` | 25 | CRITICAL | Structured data (JSON-LD) exists for the listing |
| `canonical_url_valid` | 20 | CRITICAL | Canonical URL resolves and matches |
| `robots_crawlable` | 20 | CRITICAL | robots.txt allows crawling of the listing URL |
| `sitemap_inclusion` | 15 | WARNING | Listing URL appears in sitemap |
| `title_populated` | 10 | WARNING | Listing has a non-empty title |
| `description_populated` | 5 | WARNING | Listing has a non-empty description |
| `tags_present` | 5 | INFO | Listing has at least one tag |

### Scoring

- Each check contributes its weight to the total score (max 100)
- Grades: A (≥90), B (≥75), C (≥60), D (≥40), F (<40)

## Caching

- Results cached in Redis with prefix `discovery:readiness:{slug}`
- TTL: 6 hours
- Refreshed by APScheduler every 4 hours and on-demand via endpoint access

## Publish Hooks

Three integration points run lightweight validation (4 local checks, no network calls) when listings are published:
- `publish_service.py` (2 hooks)
- `publish_pipeline.py` (1 hook)

These call `maybe_log_low_publish_readiness()` which runs `validate_on_publish()` — a fast subset that skips network-dependent checks (robots, sitemap, canonical). Full 7-check validation runs via the scheduler or endpoint.

## Admin Overview

`GET /internal/discovery-readiness/overview` returns:
- `total_listings`: Count of published listings
- `avg_score`: Platform average readiness score
- `grade_distribution`: Count of listings per grade (A/B/C/D/F)
- `common_failures`: Most frequent failing checks across all listings
- `is_truncated`: Whether results were limited

## Troubleshooting

### Low readiness score
Check which specific checks are failing via the seller endpoint. Most common issues: missing JSON-LD (check `app/services/jsonld_service.py`), robots.txt blocking, or listing not in sitemap.

### Cache stale
Redis key: `discovery:readiness:{slug}`. Clear with `DEL` via Redis CLI or wait for 4h scheduler refresh.
