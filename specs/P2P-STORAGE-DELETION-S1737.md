# Delete ai.market's seller-data storage and relay code (S1737)

**Authority:** Max, 2026-09-22, S1737: "simplify code whenever possible to not be additive" (Event Ledger `109db5e8`), then, on the proposal to delete rather than guard: "Then do it" (`87fb454b`). Rule: `runbooks/data-delivery-p2p.md`. Risk class: customer data and delivery, so unanimous Council (GLM, DeepSeek, Gemini) on this spec and on the build.

**Base:** ai-market-backend `main` after PR #451 (S1735 licence chunk C) merges; citations below are to `6acf09761a08a6b97ceede1f0705567df3bc0e05` and, where marked, to the #451 head `f046bfc16d301cea9cf6062fae93eb8193ae3eca`. MP builds on `build/p2p-storage-deletion-s1737`.

## Principle

Delete every module whose purpose is to receive, buffer, stage, store, presign, proxy or relay seller bytes through ai.market, plus everything that exists only to serve those modules. Where a surviving caller branches into removed code, delete the branch so the flag-off behaviour becomes the only behaviour. No replacement abstractions, shims or new flags. The one exception is code that a surviving live path needs; it is named below.

## Remove

| Code | Why it goes |
| --- | --- |
| `app/services/listing_asset_store.py`; config `LISTING_ASSET_*` | Only client of the ai.market-owned `aimarket-listing-assets` bucket. (Seller-owned R2 in `seller_workspace_r2.py` stays.) |
| `app/services/manifest_fulfillment.py`, `delivery_transfer_plan.py` (holds seller bytes in `PartBuffer`), `delivery_runtime.py`, `delivery_store_executors.py`, `delivery_session_state.py`, `delivery_buyer.py`, `delivery_completion.py`, `delivery_reconciliation.py` | The manifest delivery runtime: buffers, R2 multipart, staging state, presign, completion, reconciliation. Each is imported only by the others. |
| `app/tasks/delivery_staging.py`, `app/tasks/multi_file_versions.py`; their Celery includes and beat entries (`app/core/celery_app.py` ~89-90, ~150-152) | Sweeps of the bucket. |
| Manifest branches in `fulfillment_listener_service.py` (~94, ~132, ~823), `fulfillment_service.py` (~607-614, ~666-673), `order_service.py` (~697-706) | With the runtime gone, a manifest (multi-file) version is not purchasable and no seller request carries `delivery_manifest_hash`: the current flag-off behaviour, made unconditional. No multi-file listing exists (prod, S1737: `listing_version_members` 0 rows; the 2 `listing_versions` are Seller Workspace `s3` single-object versions, whose live path is the flag-off branch kept here), so no order can reach the removed runtime and no constructor-time refusal is needed. |
| The three manifest-download routes in `app/api/v1/endpoints/orders.py` (~959-980) | They only presign bucket objects. |
| `app/services/public_sample_service.py`, `app/api/v1/endpoints/vz_samples.py`, the sample routes (`public.py` ~96, ~885), the samples router include (`app/routers/vz_publish.py` ~317) | Sample bytes stored in and proxied from the bucket. `disclosure_snapshot_service.py` ~47 inlines `authority_kind`. The licence spec's public-sample rule (S1735 Gate 2 §6, `require_listing_license_snapshot` on the sample route) is superseded: ai.market serves no sample bytes at all, which satisfies its Gate 1 §6.5 trivially; Mars records the same in the licence spec after #451 merges. Chunk C's gates on the deleted routes go with them. On the #451 base, `listing_license_snapshot_gate` (`public_sample_service.py` 41-43 at `f046bfc`) moves unchanged into `public.py`, where it still decorates `/public/listings/{slug}` (`public.py` 790-792 at `f046bfc`); in `tests/test_listing_license_route_inventory.py` the deleted sample route leaves `expected` and `/public/listings/{slug}` keeps its `listing_snapshot` marker. |
| Sample validation in `vz_publish_service.finalize_local_version` (~1311-1332) | It requires a stored `ListingSampleAsset` for each `is_sample` member. The block goes; `is_sample` remains manifest metadata only. A sample, when it returns, is served from the seller's own origin. |
| `WORKSPACE_SAMPLE_FILES_ENABLED` | Gated only samples. |
| AIM relay: `app/api/v1/aim_relay.py`, `app/services/aim_relay_service.py`, its router include (`router.py` 59, 139), and every `relay_mode` / `AIMRelayService` / `AIMConnectionMode.RELAY` branch in `aim_service.py` (at least ~103-133, ~535-611, ~681-697, ~765-766, ~823-849) | Relay unused. `connection_mode` is always DIRECT. The `RELAY` member leaves the Python enum; the Postgres enum type keeps its value (removing an enum value is not worth a type rewrite). |
| Models `multi_file_delivery.py`, `listing_sample_asset.py`, `seller_sample_asset.py`, `ListingAssetTombstone` (only; `ListingVersionMember` stays), their `registry.py` entries | Tables dropped below. |
| `scripts/verify_s1717_d_store.py`; tests that exist only for removed code | Delete, don't rewrite. |

## Keep

- The manifest contract for the future peer-to-peer design (Mars, peer message 5843): `listing_version_members`, `manifest_hash`, manifest intake and validation in `vz_publish` / `vz_publish_service.py`, `listing_summary.py`, `listing_versioning.py`, and `MULTI_FILE_DATASETS_ENABLED`, which afterwards gates only manifest publishing and stays off. The per-file grant/consume semantics and buyer-side hash check are the contract to rebuild peer to peer; their bucket-bound implementation goes.
- The live legacy delivery path (`fulfillment_listener_service.py` stream-to-disk, `delivery_service.py` `_queue_delivery_request`). It is how AIM Data orders deliver today; it goes under T-2026-000839 once a peer-to-peer replacement exists.
- Seller Workspace delivery from the seller's own bucket (`order_service` `assume_seller_role`, `seller_workspace_delivery`, `seller_workspace_r2.py`).
- Every #451 licence gate on a surviving door.

## Migration

One revision. Inside its transaction, in this order: `SET LOCAL lock_timeout = '5s'`; `LOCK TABLE` each table below `IN ACCESS EXCLUSIVE MODE`; then refuse (raise, naming the table) if any of these is true, otherwise drop:

- any row in `order_staging`, `transfer_session_members`, `transfer_chunk_receipts`, `transfer_part_receipts`, `order_delivery_members`, `buyer_download_meter`, `listing_sample_assets`, `seller_sample_assets`, `listing_asset_tombstones` → drop the tables (and the `listing_asset_delete_tombstone` trigger and its function `retain_listing_asset_key()`);
- any `aim_nodes` row with `relay_mode = true` or `relay_registered_at IS NOT NULL`, or any `aim_sessions` row with `connection_mode = 'relay'` → drop `aim_nodes.relay_mode` and `aim_nodes.relay_registered_at` (and both columns from `app/models/aim.py`).

Downgrade raises: the dropped objects held no rows, and rolling back the code would be a forward migration, not a restore. Test: the direct-only empty state upgrades; a row in any dropped table, a relay node or a relay session makes it refuse.

Production state read by Vulcan 2026-09-22 (procedure step 3 in `runbooks/data-delivery-p2p.md` now prints all of these): all nine tables 0 rows, `aim_nodes` 2 rows with 0 `relay_mode`, `aim_sessions` 0 rows. Re-run step 3 immediately before merge.

## Build rules

Report every remaining `git grep` hit in `app` and `scripts` for a removed module or symbol and why it stays. Run the full backend suite and report exact counts. Check `ai-market-frontend` and `aim-data` for calls to removed routes; frontend removals are a separate PR in the same round.

## After deploy

The build PR also rewrites the procedure in `runbooks/data-delivery-p2p.md` so it never names a dropped object: step 3 loses the `relay_nodes`, `relay_sessions` and `staging_rows` lines; the rest stays until the bucket is gone. The full current step 3 is run only before merge.

1. `/health` green; `alembic_version` at the new head; run the rewritten procedure.
2. Remove `LISTING_ASSET_*` from Infisical `ai-market-backend` prod (`infisical-secrets.md`).
3. Max deletes the `aimarket-listing-assets` bucket and its bucket-scoped token in the Cloudflare dashboard (he created both, 2026-09-16). Then drop the bucket step from the procedure, retire `listing-asset-store.md`, and update the current-state table.
