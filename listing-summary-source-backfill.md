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

Writing facts for a listing fires the existing source trigger, which invalidates that listing's current summary record. A pending draft simply regenerates on the seller's next visit. An APPROVED summary is withdrawn from the public page until the seller approves again. Step 2 below sizes this; if any approved summary would be hit, stop and put the decision to Max before step 3.

## Procedure (headless, from Titan-1)

`DATABASE_URL` is the ONLY thing that selects the target database. Production is selected explicitly, never through the checkout's Railway link (`ai-market-backend.md`, Deployment): `railway variables` passes `-e production`; `railway status` has no `-e` flag, so its JSON (which lists every environment) is filtered on the environment named `production`. Use bash (step 2 uses process substitution). Never echo the URL. Run the three steps as three separate pastes in the SAME persistent bash session (variables carry over); do not join them.

### Step 1 — set up and dry run (read-only)

```bash
set -euo pipefail
cd ~/Projects/ai-market/ai-market-backend && git fetch origin
SHA=$(railway status --json | python3 -c '
import json,sys
d=json.load(sys.stdin)
for e in d["environments"]["edges"]:
    if e["node"]["name"]!="production": continue
    for i in e["node"]["serviceInstances"]["edges"]:
        n=i["node"]; ld=n.get("latestDeployment") or {}
        if n.get("serviceName")=="ai-market-backend":
            assert ld.get("status")=="SUCCESS", ld.get("status")
            print(ld["meta"]["commitHash"])')
# the main checkout's .venv is only valid if dependencies did not change between it and the deployed commit
git diff --quiet "$SHA" origin/main -- requirements.txt pyproject.toml || { echo "dependency drift: build a venv for $SHA"; exit 1; }
WT=$(mktemp -d /var/tmp/koskadeux/backfill-XXXXXX)/wt
git worktree add --detach "$WT" "$SHA"
test "$(git -C "$WT" rev-parse HEAD)" = "$SHA"
cd "$WT"
PY=~/Projects/ai-market/ai-market-backend/.venv/bin/python
export SECRET_KEY=local-backfill-operator-only-not-a-real-key-000
export DATABASE_URL=$(railway variables -e production -s Postgres --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["DATABASE_PUBLIC_URL"].split("?")[0])')
$PY scripts/backfill_listing_summary_sources.py --dry-run > "$WT/../dryrun.jsonl"
tail -1 "$WT/../dryrun.jsonl"
```

`SECRET_KEY` is required only because the script imports the backend settings module; a throwaway local value is correct and no production secret is needed. `ENVIRONMENT` is not required (the first production run set `ENVIRONMENT=test`; it is inert on this code path and is not a database selector). The `.split("?")[0]` strips any `?sslmode=` query, which asyncpg rejects, without printing the URL. Output is JSON Lines with listing ids, fact names and counts only, never values.

### Step 2 — decide (stop here and read the output)

```bash
set -euo pipefail
: "${WT:?run step 1 in this same shell first}" "${DATABASE_URL:?run step 1 in this same shell first}"
psql "$DATABASE_URL" -Atc "select state, count(*) from listing_summary_records group by state"
python3 - "$WT/../dryrun.jsonl" <<'PY' > "$WT/../would-write.txt"
import json,sys
for line in open(sys.argv[1]):
    r=json.loads(line)
    if r.get("derived_count"): print(r["listing_id"])
PY
psql "$DATABASE_URL" -Atc "select listing_id from listing_summary_records where state='approved'" | sort | comm -12 - <(sort "$WT/../would-write.txt")
```

The last command lists approved summaries that an apply would withdraw from the public page. If it prints anything, stop and ask Max. If it prints nothing, continue.

### Step 3 — apply, confirm, clean up

```bash
set -euo pipefail
cd "$WT"
$PY scripts/backfill_listing_summary_sources.py --apply > "$WT/../apply.jsonl"; tail -1 "$WT/../apply.jsonl"
$PY scripts/backfill_listing_summary_sources.py --dry-run | tail -1 | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r); assert r["mode"]=="dry-run" and r["listings_with_missing_facts"]==0, "facts still missing: rerun apply or investigate"' 
psql "$DATABASE_URL" -Atc "select count(*) from listing_summary_sources"
unset DATABASE_URL SECRET_KEY
cd ~/Projects/ai-market/ai-market-backend && git worktree remove "$WT"
```

A full pass over the public proxy takes about 90 seconds per mode for ~60 listings, so from a 120-second tool shell run each script invocation as its own command. To check one seller's listing, replace the slug:

```bash
psql "$DATABASE_URL" -Atc "select l.slug, array(select jsonb_object_keys(s.facts) order by 1) from listings l join listing_summary_sources s on s.listing_id=l.id where l.slug = 'eolymp-problem-dataset-5ab53e16'"
```

Then the seller opens the listing editor, regenerates or previews At a glance, and approves it. Buyers see nothing until that approval.

## When it breaks

| Symptom | Cause | Fix |
|---|---|---|
| `ValidationError: SECRET_KEY must be set` on start | Script imports app settings | Export the throwaway `SECRET_KEY` as in step 1 |
| `connect() got an unexpected keyword argument 'sslmode'` | asyncpg does not accept `?sslmode=` in the URL | Step 1 already strips the query; if you built the URL by hand, drop everything from `?` |
| `password authentication failed` | Stale `DATABASE_PUBLIC_URL` after a rotation | Compose the URL from parts per `ai-market-backend.md` |
| A listing still shows nothing after backfill | It has no derivable metadata (no row count, format, size, complete schema or privacy score) | Seller adds labelled description sentences or republishes through AIM Data; the preview returns the `guidance` values saying so |

## History

- 2026-09-18 (S1719, Vulcan): first production run after backend PR #417 deployed (`976c5a2bc16b5f30f6832f0c9ed8fdbd38dce76a`, Railway `ai-market-backend` production deployment SUCCESS). Receipt (values as returned by the commands; no URL or secret recorded):

  | Check | Result | Where recorded |
  |---|---|---|
  | Dry run before apply | `{"derived_facts": 229, "listings": 63, "listings_with_missing_facts": 59, "mode": "dry-run"}` | Titan-1 `/var/tmp/koskadeux/backfill-dryrun-s1719.jsonl`, sha256 `12d0c3e1381419da5aee121d0780a4d3108a186e15e12cc05f7513cf86122dc2` |
  | Apply | `{"derived_facts": 229, "listings": 63, "listings_with_missing_facts": 59, "mode": "apply"}` | Titan-1 `/var/tmp/koskadeux/backfill-apply-s1719.jsonl`, sha256 `bea59203e9c226cec03fde46ed57413402e9cf63558d98a6ce2c81528dc980e6` |
  | Confirming dry run | `{"derived_facts": 0, "listings": 63, "listings_with_missing_facts": 0, "mode": "dry-run"}` | session transcript only (not written to a file) |
  | `listing_summary_records` by state before apply | `pending 2`, no `approved` | session transcript only |
  | Same query, re-run 2026-09-18 after apply | `invalidated 2` | re-queried while writing this page |
  | `listing_summary_sources` rows | 2 before, 61 after | before: session transcript; after: re-queried while writing this page |
  | `eolymp-problem-dataset-5ab53e16` fact keys after apply | `{format,row_count}` | session transcript only |

  Files under `/var/tmp` are not durable; the hashes let a reader tell whether they are still the originals. Rows marked "session transcript only" were observed by the operator and are not independently re-checkable.
