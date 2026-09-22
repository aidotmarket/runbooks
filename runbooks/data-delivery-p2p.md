---
title: Data delivery is peer-to-peer only (ai.market never holds a delivered file)
owner: vulcan
last_verified: '2026-09-22'
aliases: [P2P delivery rule, peer-to-peer delivery, no custody of delivered files, delivery custody, automatic rejection reason, stream-to-disk, /tmp/fulfillment]
error_signatures: []
---

# Data delivery is peer-to-peer only

## The rule

File delivery is peer to peer. The buyer gets the bytes directly from the seller's AIM Data install or from the seller's own cloud storage. ai.market holds the order record and issues download permission (a token, or a short-lived scoped credential or signed link on the seller's own storage). It never stores, stages, caches, relays or proxies the bytes of a delivered data file, on disk, in memory beyond a pass-through, or in any object store it owns.

Authority: Max, S1736 (2026-09-22). The S1736 handoff records it under Event Ledger dedupe keys `s1736-delivery-must-be-p2p` and `s1736-p2p-audit-decisions`; those keys were not independently re-read in S1737. The rule restates Boot Kernel v2 (CORE v9.19) P2, P8 and S1, which stand on their own; v9.19 adds the public-sample exception below.

Rejected designs, do not propose them again:

- Cloudflare R2 (or any ai.market-owned S3/GCS/R2 bucket) for delivered files or delivery staging.
- A live relay that streams delivered bytes through ai.market servers, even without writing them to disk.

Accepted exceptions (Max, same decision):

- Kaggle and Hugging Face mirrors on ai.market-owned accounts of public datasets (the published mirror listings, including Sergey's). These are public copies, not purchase deliveries.
- A public sample: a portion of their own data that the seller chooses to publish on their listing. ai.market may store and show it (CORE v9.19 Data & Security; Max S1739, Event Ledger 45675b19 and 58dae0d1, superseding the S1736/S1737 rule that samples were never stored by ai.market). Only what the seller explicitly selects for publication qualifies; ai.market never reads, profiles or extracts from the rest of the seller's data to make one.

Max decided on 2026-09-22 (S1737) that unused storage and relay code is deleted rather than guarded or rebuilt; only the manifest contract (member list, per-file hashes, `manifest_hash`, per-file grant/consume, buyer-side hash verification) is kept for the peer-to-peer design. Spec: `specs/P2P-STORAGE-DELETION-S1737.md`.

## Automatic rejection reason in review

Any Council voter (GLM, DeepSeek, Gemini) or peer (Vulcan, Mars) reviewing a spec, PR or config change must return REJECT, with no mandate needed, if the change would make ai.market write, upload, stage, cache, relay or proxy the bytes of a delivered seller data file, or store any seller data other than the public sample the seller chose to publish. Cite this page. This is not a trade-off to be weighed against convenience or launch dates. A change that removes such a path is in scope for any delivery item.

The Council request standard (`REVIEW_PROTOCOL`, see `runbooks/council.md`) carries this reason once the S1737 change to it merges; until then include this paragraph in the request body of any delivery-touching review.

## Current state (verified 2026-09-22, S1737, backend `origin/main` 6acf09761)

| Path | What it does today | Live? | Plan step / ticket |
| --- | --- | --- | --- |
| Legacy trust-channel fulfilment, `app/services/fulfillment_listener_service.py` `_legacy_handle_complete`, `STAGING_DIR` default `/tmp/fulfillment` | Seller install streams the file to the backend, which writes it to container disk and issues a buyer token; the seller-bound response also carries the buyer's raw download token (`trust_websocket.py`) | **Yes** — this is how every AIM Data order is delivered today | Step 2, T-2026-000839 |
| Manifest (multi-file) delivery, `app/services/manifest_fulfillment.py` → R2 `orders/…` | Multipart-uploads seller files into `aimarket-listing-assets` | No — `MULTI_FILE_DATASETS_ENABLED` unset (default False) | Being deleted (Max, S1737) |
| Listing samples, `app/services/listing_asset_store.py`, `app/services/public_sample_service.py`, `app/api/v1/endpoints/vz_samples.py` | Stores and serves the seller-chosen public sample from R2 | No — local route gated by `MULTI_FILE_DATASETS_ENABLED`, workspace route by `WORKSPACE_SAMPLE_FILES_ENABLED`; both unset | Kept: permitted public-sample exception (Max S1739, CORE v9.19); not part of the storage deletion |
| AIM `relay_mode` (`app/api/v1/aim_relay.py`, `aim_relay_service.py`, relay branches in `aim_service.py`) | Relays AIM Node sessions through ai.market | No — 0 of 2 `aim_nodes` have `relay_mode` (prod read S1737) | Being deleted (Max, S1737) |
| `delivery_service.py` `_queue_delivery_request` (`delivery_mode: trust_channel_proxy`) | Asks the seller install to stream the file to the backend — the request half of the legacy path above | **Yes** | Step 2, T-2026-000839 (not deleted until a peer-to-peer replacement exists) |
| `demo_fulfillment_service.py` `STAGING_DIR` | Writes generated synthetic rows, not seller bytes, to `/tmp/fulfillment` | No — `DEMO_FULFILLMENT` default False, unset in production, and startup refuses it in production (`config.py`) | Not seller data |
| Seller Workspace S3 route (`order_service` `assume_seller_role`) | Buyer downloads from the seller's bucket with a scoped credential | Yes | Compliant — the model for step 2 |

Checks run on 2026-09-22 (S1737) with the procedure below: all three flags unset in production; bucket 0 objects and 0 in-progress multipart uploads; `/tmp/fulfillment` absent on the running backend container; the dropped legacy row columns (`verified_rows`, `row_data`, `approved_sample`, `sample_preview`) absent; the one surviving legacy row column, `datasets.sample_data` (also exposed by the `mcp_safe.datasets` view), holds nothing because `datasets` has 0 rows; `aim_nodes` has 2 rows, 0 with `relay_mode` (S1736 counted 4 nodes).

## Procedure: check where delivered data could sit

Run after any delivery change, before launch, and whenever a review asks. It reads names and counts only, never content, and never writes secrets to disk. It checks the stores that exist today; while the legacy path is live, a clean result means only that nothing is held right now.

```bash
cd /Users/max/Projects/ai-market/ai-market-backend && unset RAILWAY_TOKEN
# 1. Flags and the bucket (Railway variables piped, never saved)
railway variables -e production -s ai-market-backend --json | .venv/bin/python -c '
import json,sys,boto3,socket,urllib3.util.connection as uc
uc.allowed_gai_family=lambda: socket.AF_INET   # Titan-1: IPv6 to R2 times out
d=json.load(sys.stdin)
for k in ("MULTI_FILE_DATASETS_ENABLED","WORKSPACE_SAMPLE_FILES_ENABLED","DEMO_FULFILLMENT","FULFILLMENT_STAGING_DIR"): print(k, d.get(k,"<unset>"))
s3=boto3.client("s3",endpoint_url=d["LISTING_ASSET_ENDPOINT"],aws_access_key_id=d["LISTING_ASSET_R2_ACCESS_KEY_ID"],aws_secret_access_key=d["LISTING_ASSET_R2_SECRET_ACCESS_KEY"],region_name="auto")
b=d["LISTING_ASSET_BUCKET"]
print("delivery_objects", s3.list_objects_v2(Bucket=b,Prefix="orders/",MaxKeys=1000).get("KeyCount"))
print("delivery_multipart_uploads", len(s3.list_multipart_uploads(Bucket=b,Prefix="orders/").get("Uploads",[])))
print("sample_objects (allowed)", s3.list_objects_v2(Bucket=b,Prefix="samples/",MaxKeys=1000).get("KeyCount"), s3.list_objects_v2(Bucket=b,Prefix="samples-staging/",MaxKeys=1000).get("KeyCount"))
print("other_prefix_objects", sum(1 for o in s3.list_objects_v2(Bucket=b,MaxKeys=1000).get("Contents",[]) if not o["Key"].startswith(("orders/","samples/","samples-staging/"))))'
# 2. Container disk at the effective staging path (pass the remote command as ONE quoted string; `railway ssh -- sh -c ...` silently runs in the app directory instead)
railway ssh -e production -s ai-market-backend 'D="${FULFILLMENT_STAGING_DIR:-/tmp/fulfillment}"; echo "$D"; test -d "$D" && find "$D" -type f | wc -l || echo ABSENT'
# 3. Database (read-only counts; DSN script as used in dataset-card-publishing.md)
cd /Users/max/Projects/ai-market && DSN="$(scripts/test-db-dsn.sh 2>/dev/null)" && psql "$DSN" -X -At \
  -c "set default_transaction_read_only=on" \
  -c "select 'legacy_row_columns', count(*) from information_schema.columns where table_schema='public' and column_name in ('verified_rows','row_data','approved_sample','sample_preview')" \
  -c "select 'datasets_sample_data', count(sample_data) from datasets" \
  -c "select 'relay_nodes', count(*) filter (where relay_mode) from aim_nodes" \
  -c "select 'relay_sessions', count(*) from aim_sessions where connection_mode='relay'" \
  -c "select 'relay_registered', count(*) from aim_nodes where relay_registered_at is not null" \
  -c "select 'delivery_tables_present', count(*) from information_schema.tables where table_schema='public' and table_name in ('order_staging','transfer_session_members','transfer_chunk_receipts','transfer_part_receipts','order_delivery_members','buyer_download_meter')" \
  -c "select 'sample_rows (allowed)', (select count(*) from listing_sample_assets)+(select count(*) from seller_sample_assets)+(select count(*) from listing_asset_tombstones)"; unset DSN
# Before the storage deletion ships, the six delivery tables still exist: also run  select (select count(*) from order_staging)+(select count(*) from transfer_session_members)+(select count(*) from transfer_chunk_receipts)+(select count(*) from transfer_part_receipts)+(select count(*) from order_delivery_members)+(select count(*) from buyer_download_meter);  and expect 0.
```

Expected: `MULTI_FILE_DATASETS_ENABLED`, `DEMO_FULFILLMENT` `<unset>` or `false`, `FULFILLMENT_STAGING_DIR` `<unset>`; `delivery_objects 0`, `delivery_multipart_uploads 0`, `other_prefix_objects 0`; disk `ABSENT` or `0`; `legacy_row_columns`, `datasets_sample_data` and every relay count 0; `delivery_tables_present` 0 once the storage deletion has shipped (6 before, with 0 rows). Sample objects and sample rows are allowed (seller-chosen public samples, CORE v9.19) and are reported for information only. Anything else: see below.

Never set `MULTI_FILE_DATASETS_ENABLED` or `DEMO_FULFILLMENT` to true in production without a peer-to-peer design approved by unanimous Council and Max's approval to enable it. `WORKSPACE_SAMPLE_FILES_ENABLED` gates only the seller-chosen public sample; enabling it needs Max's go-ahead for samples, not a peer-to-peer design.

## When it breaks

- **Delivered bytes found on ai.market infrastructure** (any `orders/…` or unexpected-prefix bucket object or multipart upload, files under `/tmp/fulfillment`, a non-zero delivery or relay count, a relay session carrying data; sample objects and sample rows are not a breach): this is customer data held against the rule. Stop the path that wrote it (turn the flag off), tell Mars on the peer bus and Max directly, and record the object keys, order ids and seller ids without reading content. Deletion follows Max's decision.
- **A review approves a change that stores or relays delivered bytes**: the gate is invalid. Reopen it at Gate 2 with this page cited.
- **Legacy path files in `/tmp/fulfillment`**: expected until step 2 ships; the Railway container disk is ephemeral, so files vanish on redeploy (this is also why buyers could not download in the S1736 end-to-end run). Do not "fix" that by moving staging to a bucket.
