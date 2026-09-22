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

Authority: Max, S1736 (2026-09-22), Event Ledger dedupe keys `s1736-delivery-must-be-p2p` and `s1736-p2p-audit-decisions`. It restates CORE P2, P8 and S1.

Rejected designs, do not propose them again:

- Cloudflare R2 (or any ai.market-owned S3/GCS/R2 bucket) for delivered files or delivery staging.
- A live relay that streams delivered bytes through ai.market servers, even without writing them to disk.

Accepted exceptions (Max, same decision):

- Kaggle and Hugging Face mirrors on ai.market-owned accounts of public datasets (the published mirror listings, including Sergey's). These are public copies, not purchase deliveries.
- Listing samples built from a seller's real rows only with that seller's explicit agreement, and even then served from the seller's install or the seller's cloud, never stored by ai.market.

## Automatic rejection reason in review

Any Council voter (GLM, DeepSeek, Gemini) or peer (Vulcan, Mars) reviewing a spec, PR or config change must return REJECT, with no mandate needed, if the change would make ai.market write, upload, stage, cache, relay or proxy the bytes of a delivered seller data file, or store real seller rows as a sample. Cite this page. This is not a trade-off to be weighed against convenience or launch dates. A change that removes such a path is in scope for any delivery item.

The Council request standard (`REVIEW_PROTOCOL`, see `runbooks/council.md`) carries this reason once the S1737 change to it merges; until then include this paragraph in the request body of any delivery-touching review.

## Current state (verified 2026-09-22, S1737, backend `origin/main` 6acf09761)

| Path | What it does today | Live? | Plan step / ticket |
| --- | --- | --- | --- |
| Legacy trust-channel fulfilment, `app/services/fulfillment_listener_service.py` `_legacy_handle_complete`, `STAGING_DIR` default `/tmp/fulfillment` | Seller install streams the file to the backend, which writes it to container disk and issues a buyer token; the seller-bound response also carries the buyer's raw download token (`trust_websocket.py`) | **Yes** — this is how every AIM Data order is delivered today | Step 2, T-2026-000839 |
| Manifest (multi-file) delivery, `app/services/manifest_fulfillment.py` → R2 `orders/…` | Multipart-uploads seller files into `aimarket-listing-assets` | No — `MULTI_FILE_DATASETS_ENABLED` unset (default False) | Step 4 |
| Listing samples, `listing_asset_store.py` / `public_sample_service.py` / `vz_samples.py` | Stores and proxies sample bytes from R2 | No — `WORKSPACE_SAMPLE_FILES_ENABLED` unset (default False) | Step 4 |
| `delivery_service.py` `trust_channel_proxy` mode; AIM `relay_mode` (`aim_service.py`, `aim_relay_service.py`) | Streams through ai.market | Relay unused (0 of 4 `aim_nodes`, S1736) | Step 5 |
| `demo_fulfillment_service.py` `STAGING_DIR` | Also defaults to `/tmp/fulfillment`; imported by `fulfillment_service.py` | Not yet classified | Classify under step 2 |
| Seller Workspace S3 route (`order_service` `assume_seller_role`) | Buyer downloads from the seller's bucket with a scoped credential | Yes | Compliant — the model for step 2 |

Checks run on 2026-09-22: both flags absent from Railway `production` / `ai-market-backend`; `config.py` lines 64–65 default both to False; `aimarket-listing-assets` holds 0 objects.

## Procedure: verify ai.market holds no delivered data

Run after any delivery change, before launch, and whenever a review asks.

```bash
cd /Users/max/Projects/ai-market/ai-market-backend && unset RAILWAY_TOKEN && git fetch -q origin
git grep -nE "MULTI_FILE_DATASETS_ENABLED|WORKSPACE_SAMPLE_FILES_ENABLED" origin/main -- app/core   # both must default to False
railway variables -e production -s ai-market-backend --json > /tmp/rv.json                      # never cat this file
python3 -c "import json;d=json.load(open('/tmp/rv.json'));[print(k,d.get(k,'<unset>')) for k in ('MULTI_FILE_DATASETS_ENABLED','WORKSPACE_SAMPLE_FILES_ENABLED')]"
```

Both must print `<unset>` or `false`. Then list the bucket with the read-only procedure in `listing-asset-store.md` (same `/tmp/rv.json`, `list_objects_v2`); the key count must be 0. Delete `/tmp/rv.json` afterwards.

Never set either flag to true in production until its step-4 peer-to-peer rebuild has shipped with unanimous Council approval and Max has approved enabling it.

## When it breaks

- **Delivered bytes found on ai.market infrastructure** (any key under `orders/` or `samples*/` in the bucket, a relay session carrying data, files kept beyond one legacy transfer): this is customer data held against the rule. Stop the path that wrote it (turn the flag off), tell Mars on the peer bus and Max directly, and record the object keys, order ids and seller ids without reading content. Deletion follows Max's decision.
- **A review approves a change that stores or relays delivered bytes**: the gate is invalid. Reopen it at Gate 2 with this page cited.
- **Legacy path files in `/tmp/fulfillment`**: expected until step 2 ships; the Railway container disk is ephemeral, so files vanish on redeploy (this is also why buyers could not download in the S1736 end-to-end run). Do not "fix" that by moving staging to a bucket.
