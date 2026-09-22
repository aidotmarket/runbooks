# Delete ai.market's seller-data storage and relay code (S1737)

**Authority:** Max, 2026-09-22, S1737 — "simplify code whenever possible to not be additive", then, on the proposal to delete rather than guard: "Then do it". Event Ledger `109db5e8` (plan change) and the S1737 decision event for this spec. Rule: `runbooks/data-delivery-p2p.md`. Risk class: customer-data and delivery → unanimous Council (GLM, DeepSeek, Gemini) on this spec and on the build.

**Source pins:** ai-market-backend `origin/main` `6acf09761a08a6b97ceede1f0705567df3bc0e05`; the build rebases on whatever `main` is after backend PR #451 (S1735 licence chunk C) merges, because #451 edits `delivery_buyer.py`, `public_sample_service.py` and `public.py` (Mars, peer message 5843).

## What goes

Code that stores seller bytes in ai.market's R2 bucket, proxies them from it, or relays AIM sessions. None of it is enabled in production and every table it owns has 0 rows (prod read S1737: `order_staging`, `transfer_session_members`, `transfer_chunk_receipts`, `transfer_part_receipts`, `order_delivery_members`, `buyer_download_meter`, `listing_sample_assets`, `seller_sample_assets`, `listing_asset_tombstones` all 0; `aim_nodes` 2 rows, 0 `relay_mode`).

| Remove | Notes |
| --- | --- |
| `app/services/listing_asset_store.py` | The only R2 client. Config fields `LISTING_ASSET_*` go with it. |
| `app/services/manifest_fulfillment.py` storage path | R2 multipart upload of seller files. The two call sites in `fulfillment_listener_service.py` (lines ~94, ~132, ~823) fall back to the legacy refusal `MANIFEST_DELIVERY_REQUIRED` behaviour. Delete the module if nothing else remains in it. |
| `app/services/delivery_buyer.py`, `delivery_completion.py`, `delivery_reconciliation.py`, `app/tasks/delivery_staging.py`, `app/tasks/multi_file_versions.py` | Staging, presign, completion, reconciliation and sweeps for R2-staged orders. Remove their Celery includes and beat entries (`celery_app.py` ~89-90, ~150-152). |
| The three manifest-download routes in `app/api/v1/endpoints/orders.py` (~959-980) | They only presign R2 objects. |
| `app/services/public_sample_service.py`, `app/api/v1/endpoints/vz_samples.py` and their routes (`public.py` ~96, ~885; `vz_publish.py` ~317) | Sample bytes stored in and proxied from R2. `disclosure_snapshot_service.py` ~47 inlines the one helper it imports (`authority_kind`). |
| `WORKSPACE_SAMPLE_FILES_ENABLED` | Gates only samples. |
| `app/api/v1/aim_relay.py`, `app/services/aim_relay_service.py`, relay branches in `aim_service.py` (~103-113, ~535-611), router include (`router.py` 59, 139) | AIM relay mode. `connection_mode` becomes DIRECT only. |
| Models for the dropped tables (`multi_file_delivery.py`, `listing_sample_asset.py`, `seller_sample_asset.py`, `ListingAssetTombstone` in `listing_version_member.py`), their `registry.py` entries | |
| Tests that exist only for removed code | Delete, don't rewrite. |
| One alembic migration | Drops the nine tables above and `aim_nodes.relay_mode`. Each drop first refuses (raises) if the table or column holds any row, following `20260920_001_s1294_drop_legacy_row_preview.py`; `SET lock_timeout = '5s'` before the DDL. Downgrade recreates empty structures. |

## What stays

- The manifest contract a peer-to-peer design reuses (Mars, 5843): `listing_version_members` and its model, `manifest_hash` on listing versions, manifest intake and validation in `vz_publish` / `vz_publish_service.py`, `listing_summary.py`, `listing_versioning.py`, `delivery_transfer_plan.py` if it holds no storage, and `MULTI_FILE_DATASETS_ENABLED`, which then gates only manifest publishing and stays off. The per-file grant/consume semantics and buyer-side hash check are recorded here as the contract to rebuild peer-to-peer; their R2-bound implementation is removed.
- The live legacy delivery path (`fulfillment_listener_service.py` stream-to-disk, `delivery_service.py` `_queue_delivery_request`). It is the only way AIM Data orders deliver today; it goes under T-2026-000839 once a peer-to-peer replacement exists.
- Seller Workspace S3/R2 delivery from the seller's own bucket (`order_service` `assume_seller_role`, `seller_workspace_delivery`). It is compliant.
- Licence gates from #451 on every surviving delivery door.

## Build rules

MP builds on `build/p2p-storage-deletion-s1737` from post-#451 `main`. The diff should be almost all deletions. No new abstractions, no compatibility shims, no feature flags to replace removed code; where a caller loses a dependency, remove the caller's branch rather than stubbing it. Report every remaining reference to a removed symbol (`git grep`) and why it stays. Run the full backend test suite and report exact counts; a test that fails only because it tested removed code is deleted. Check `ai-market-frontend` and `aim-data` for calls to the removed routes and report them; frontend removals go in a separate PR in the same round.

## After deploy

1. Run the procedure in `runbooks/data-delivery-p2p.md`; `/health` green; `alembic_version` at the new head.
2. Remove `LISTING_ASSET_*` from Infisical `ai-market-backend` prod (`infisical-secrets.md`).
3. Max deletes the `aimarket-listing-assets` bucket and its bucket-scoped token in the Cloudflare dashboard (created by him, 2026-09-16).
4. Retire `listing-asset-store.md` and update `runbooks/data-delivery-p2p.md`'s current-state table in the same session.
