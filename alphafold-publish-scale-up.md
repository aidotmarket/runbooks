# AlphaFold Reference Listings — Publish Scale-Up Runbook

## What it is

Operational procedure for publishing AlphaFold model-organism proteomes to ai.market as
free ($0) reference listings, and for adding more reference datasets later. Reference
listings are non-custodial pointers: the listing carries metadata + a public source URL;
ai.market never stores the data. As of S789 all 10 model-organism proteomes are live.

**Pillar:** ai.market (the marketplace) + AI-discoverability of public datasets.
**Seller surface:** `public@ai.market` auto-publish (L3).
**Live:** `api.ai.market` / listing pages on `www.ai.market`.

---

## §A — Prerequisites (the four enabling fixes)

A reference-listing publish + view path only works with all four of these on `main`:

| Fix | Repo / PR | Why it is required |
|-----|-----------|--------------------|
| `FulfillmentType.REFERENCE = "reference"` | ai-market-backend #119 | Lets a listing declare a reference fulfillment type without a 500 on the marketplace path. |
| Relax `orders_amount_cents_check` for $0 | ai-market-backend #120 | Reference listings are $0; the old CHECK constraint rejected zero-cent orders. |
| `DeliveryMethod.REFERENCE = "reference"` (model **and** schema) | ai-market-backend #121 | Order-detail response serialization coerces `delivery_method` through the enum; missing member = 500 on `GET /orders/{id}`. See §I. |
| Listing description renders sanitized markdown | ai-market-frontend #24 | Descriptions are authored in markdown (§E); without this the detail page shows raw markdown in one `<p>`. |

Verify before any bulk publish:
```sh
cd /Users/max/Projects/ai-market/ai-market-backend && git fetch origin -q
git log --oneline origin/main | grep -E '#119|#120|#121'
cd ../ai-market-frontend && git fetch origin -q && git log --oneline origin/main | grep '#24'
railway deployment list -s ai-market-backend --json | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['status'])"
```

---

## §B — Source dataset & multi-shard wildcard representation

Source bucket (requester-pays): `gs://public-datasets-deepmind-alphafold-v4`.
Per-proteome objects live under `proteomes/` and are sharded by size. Represent the **whole
proteome** with a single wildcard so the listing points at every shard:

```
source_delivery.url = gs://public-datasets-deepmind-alphafold-v4/proteomes/proteome-tax_id-<TAX>-*_v4.tar
```

E. coli is the one exception — it is a single object, so use the explicit suffix
`-0_v4.tar` (no wildcard). Shard counts (canonical organism→tax_id map lives in Living State
`infra:worker-coord:789:alphafold-free-listings`; verify there before trusting tax ids):

| Organism | tax_id | Shards | URL suffix |
|----------|--------|--------|-----------|
| E. coli | 83333 | 1 | `-0_v4.tar` (explicit, no wildcard) |
| C. elegans | 6239 | 3 | `-*_v4.tar` |
| Fruit fly (D. melanogaster) | 7227 | 4 | `-*_v4.tar` |
| Rat | 10116 | 4 | `-*_v4.tar` |
| Yeast (S. cerevisiae) | 559292 | 4 | `-*_v4.tar` |
| Zebrafish | 7955 | 6 | `-*_v4.tar` |
| Mouse | 10090 | 8 | `-*_v4.tar` |
| Arabidopsis thaliana | 3702 | 14 | `-*_v4.tar` |
| Human | 9606 | 19 | `-*_v4.tar` |
| Maize (Zea mays) | 4577 | 20 | `-*_v4.tar` |

---

## §C — Seller identity & auth

| Field | Value |
|-------|-------|
| Seller | `public@ai.market` |
| user_id | `d9490c85-41b1-4a13-a759-f9280dc1e22b` |
| device | `e44915fe664c3848fd874a8fa79d113b1a83c51dba6b253c8b3b24f355451241` (L3 auto-publish) |
| dataset id pattern | `alphafold-<organism_key>-<tax_id>-v4` |

**Token mint (until the SECRET_KEY drift is reconciled, sign with Railway's *live* key — never the canonical store):**
```sh
railway variables -s ai-market-backend --json > /tmp/rv.json
RK=$(python3 -c "import json;print(json.load(open('/tmp/rv.json'))['SECRET_KEY'])")
SECRET_KEY="$RK" .venv/bin/python -c "from app.core.security import create_access_token; from datetime import timedelta; print(create_access_token({'sub':'d9490c85-41b1-4a13-a759-f9280dc1e22b'}, expires_delta=timedelta(minutes=60)))"
```
Do not hardcode the key anywhere. See `backup-and-recovery.md`/Infisical notes for the drift status.

---

## §D — Markdown description template

Every reference listing description uses this structure (renders via §A fix #24):

```markdown
**<one-line bold summary of the proteome>**

## What's included
- Predicted 3D structures for the complete <organism> proteome (<N> shards)
- Per-residue confidence (pLDDT) and PAE where provided by AlphaFold DB

## Delivery
This is a reference listing pointing at a public Google Cloud bucket. Fetch with:
```
gsutil -u <your-billing-project> -m cp "gs://public-datasets-deepmind-alphafold-v4/proteomes/proteome-tax_id-<TAX>-*_v4.tar" .
```

## License & citation
AlphaFold DB data under CC-BY-4.0. Cite Jumper et al. 2021 and Varadi et al. 2024.
```

---

## §E — Publish procedure

Publishing is **synchronous** (~11s each — metadata enrichment runs inline). Throughput rules:

- Do **not** loop more than ~4 publishes inside one 60s `exec`. Use `timeout=120`, or run the batch in `background`.
- The publish is idempotent: upsert keys on `(device, dataset, seller)`, so retries are safe — re-running never creates duplicates. Each organism appears exactly once.
- After publishing, the **public listings endpoint is cache-backed** — a read immediately after a write can be stale. Re-poll after a few seconds before concluding a publish failed.

Publish payload essentials: `price = 0`, `fulfillment_type = reference`, `delivery_method = reference`,
`source_delivery.url` = the wildcard from §B, `description` = §D template filled in.

---

## §F — Per-organism gsutil shard verification

Confirm every shard the wildcard claims actually exists before/after publish:
```sh
gcloud config set account max@ai.market
gsutil -u aimarket-prod ls "gs://public-datasets-deepmind-alphafold-v4/proteomes/proteome-tax_id-9606-*_v4.tar" | wc -l   # expect 19 for human
```
- `-u aimarket-prod` is **required** (requester-pays bucket); omitting it fails with a billing error, not a not-found.
- An anonymous HTTP `HEAD` on a bucket object returns **403** — that is the requester-pays gate, **not** a reachability/missing-object signal. Use authenticated `gsutil`, never anon HTTP, to judge existence.
- Expected shard count per organism is the §B table.

---

## §G — Post-publish marketplace health check

```sh
curl -s "https://api.ai.market/api/v1/listings?limit=100" | python3 -c "import sys,json;d=json.load(sys.stdin);print('count',len(d.get('items',d.get('listings',[]))))"
```
- The listings endpoint **caps `limit` at 100** — `limit=200` returns HTTP 422. Paginate for larger pulls.
- Confirm each organism appears exactly once and renders markdown on its detail page.
- Sanity-check one order path end to end (see §I) — a $0 reference purchase should create an order and `GET /api/v1/orders/{id}` should return 200.

---

## §H — The order-detail enum gotcha (read before adding ANY new fulfillment/delivery value)

The order-detail 500 fixed in #121 will **recur** for any future delivery/fulfillment value
unless you add the new enum member in **both** places, in the same change:

- `app/models/order.py` — the SQLAlchemy `DeliveryMethod` (and `FulfillmentType`) enum
- `app/schemas/order.py` — the Pydantic `DeliveryMethod` (and `FulfillmentType`) enum

The DB column can hold a string the Pydantic response model has never heard of; serialization
coerces the column value through the response enum, and a missing member raises during
response validation → 500 on `GET /api/v1/orders/{id}`, not at write time. Always grep both
files when touching either enum:
```sh
grep -rn "class DeliveryMethod\|class FulfillmentType" app/models/order.py app/schemas/order.py
```

---

## §I — Verifying the order path

No live reference orders may exist yet; to exercise the path, place a $0 reference order via
the public API as a test buyer, then:
```sh
curl -s -o /tmp/ord.json -w "HTTP %{http_code}\n" -H "Authorization: Bearer <token>" "https://api.ai.market/api/v1/orders/<ORDER_ID>"
```
Expect HTTP 200 with `delivery_method: "reference"` in the body. HTTP 500 here means an enum
member is missing (§H).

---

## §J — Adding a new reference dataset later

1. Confirm the §A fixes are still on `main` (they are permanent, but re-verify after large refactors).
2. Pick the source bucket + wildcard representation (§B). Count shards with §F before publishing.
3. Fill the §D description template.
4. Mint a seller token (§C), publish with the §E throughput rules.
5. Run the §G health check and the §I order path.
6. Record the new dataset in `infra:worker-coord:*` so the organism→source map stays canonical.

---

## §K — Known gotchas (quick reference)

- Requester-pays: always `gsutil -u aimarket-prod`. Anon HTTP HEAD 403 ≠ missing.
- Listings `limit` caps at 100 (422 above that).
- Publish is synchronous ~11s; cap at ~4 per 60s exec or background it.
- Public listings reads are cache-backed — stale right after a write.
- Token mint signs with Railway's live SECRET_KEY until the Infisical drift is reconciled.
- New delivery/fulfillment enum value → add to BOTH model and schema (§H) or order-detail 500s.
- E. coli is single-shard (`-0_v4.tar`); every other organism uses the `-*_v4.tar` wildcard.
- Backend canonical clone may be parked on a feature branch because the worker worktree holds `main` — verify against `origin/main`, do not trust the local checkout.
