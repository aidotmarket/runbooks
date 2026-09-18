---
title: Listing Summary (At a glance) Source-Fact Backfill
owner: unassigned
last_verified: '2026-09-18'
aliases: [At a glance empty, listing summary backfill, legacy source facts, backfill_listing_summary_sources, listing_summary_sources]
error_signatures: ["At a glance preview empty for a listing published before P1", "ValidationError: SECRET_KEY must be set", "connect() got an unexpected keyword argument 'sslmode'"]
---

# Listing Summary (At a glance) Source-Fact Backfill

## What it does

The seller "At a glance" summary (BQ-LISTING-ENRICHMENT-SELLER-TOOLS-S1294, Phase 1) is built only from facts stored in `listing_summary_sources`. Those facts were first captured at AIM Data publish time, so every listing published before Phase 1 had none and its seller preview came up empty (found by the first real seller, 2026-09-17). Since backend main `976c5a2bc` (PR #417) a regenerate derives the missing facts from the listing's own canonical metadata (`source_row_count`, `data_format`, `raw_metadata.file_size_bytes`, complete `schema_info.columns`, `privacy_score`), and `scripts/backfill_listing_summary_sources.py` fills them for every listing in one pass. It never invents licence, coverage or freshness, never generates text, never approves or publishes anything. Code-level detail lives in the backend repo at `docs/runbooks/listing-summary.md`.

## When to run it

- After a bulk import or seed of listings that did not come through AIM Data publish.
- When a seller reports an empty At a glance preview on a listing that has row count or format in its metadata.

It is safe to repeat: unchanged listings get no writes.

## What a write does to sellers and buyers

Writing facts for a listing fires the existing source trigger, which invalidates that listing's current summary record. A pending draft simply regenerates on the seller's next visit. An APPROVED summary is withdrawn from the public page until the seller approves again. Size this before applying:

```bash
psql "$PUB" -Atc "select state, count(*) from listing_summary_records group by state"
```

If any are `approved`, compare their listing ids against the dry-run output lines with `derived_count > 0` and decide with Max before applying.

## Procedure (headless, from Titan-1)

Production Postgres path: `ai-market-backend.md`, "Connecting to production Postgres from an external host" (`DATABASE_PUBLIC_URL` on the Postgres service). Never echo the URL.

```bash
cd ~/Projects/ai-market/ai-market-backend && git fetch origin
# 1. clean worktree of the DEPLOYED commit (check the ai-market-backend production deployment's commit with `railway status --json`)
git worktree add --detach /var/tmp/koskadeux/backfill-main <deployed_sha>
PUB=$(railway variables -s Postgres --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["DATABASE_PUBLIC_URL"])')
cd /var/tmp/koskadeux/backfill-main
export DATABASE_URL="$PUB" ENVIRONMENT=test SECRET_KEY=local-backfill-operator-only-not-a-real-key-000
PY=~/Projects/ai-market/ai-market-backend/.venv/bin/python
$PY scripts/backfill_listing_summary_sources.py --dry-run > /var/tmp/koskadeux/backfill-dryrun.jsonl   # read-only transactions
$PY scripts/backfill_listing_summary_sources.py --apply   > /var/tmp/koskadeux/backfill-apply.jsonl
$PY scripts/backfill_listing_summary_sources.py --dry-run | tail -1                                    # must report 0 missing
```

The script imports the backend settings module, so `SECRET_KEY` and `ENVIRONMENT` must be present even though only the database is used; a throwaway local value is correct here and no production secret is needed. Output is JSON Lines with listing ids, fact names and counts only, never values. A full pass over the public proxy takes about 90 seconds per mode for ~60 listings, so run each mode as its own command when using a 120-second shell.

Verify:

```bash
psql "$PUB" -Atc "select count(*) from listing_summary_sources"
psql "$PUB" -Atc "select l.slug, array(select jsonb_object_keys(s.facts) order by 1) from listings l join listing_summary_sources s on s.listing_id=l.id where l.slug like '<slug-prefix>%'"
```

Then the seller opens the listing editor, regenerates or previews At a glance, and approves it. Buyers see nothing until that approval.

## When it breaks

| Symptom | Cause | Fix |
|---|---|---|
| `ValidationError: SECRET_KEY must be set` on start | Script imports app settings | Export `SECRET_KEY` and `ENVIRONMENT=test` as above |
| `connect() got an unexpected keyword argument 'sslmode'` | asyncpg does not accept `?sslmode=` in the URL | Remove the query parameter from `DATABASE_URL` |
| `password authentication failed` | Stale `DATABASE_PUBLIC_URL` after a rotation | Compose the URL from parts per `ai-market-backend.md` |
| A listing still shows nothing after backfill | It has no derivable metadata (no row count, format, size, complete schema or privacy score) | Seller adds labelled description sentences or republishes through AIM Data; the preview returns the `guidance` values saying so |

## History

- 2026-09-18 (S1719, Vulcan): first production run after PR #417 deployed (`976c5a2bc`). 63 listings, 59 filled, 229 facts; confirming dry-run 0. No approved summaries existed, two pending drafts were invalidated and regenerate on next visit. `eolymp-problem-dataset-5ab53e16` now carries `row_count` and `format`.
