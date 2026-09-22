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
| `app/services/public_sample_service.py`, `app/api/v1/endpoints/vz_samples.py`, the sample routes (`public.py` ~96, ~885), the samples router include (`app/routers/vz_publish.py` ~317) | Sample bytes stored in and proxied from the bucket. `disclosure_snapshot_service.py` ~47 inlines `authority_kind`. The licence spec's public-sample rule (S1735 Gate 2 §6, `require_listing_license_snapshot` on the sample route) is superseded: ai.market serves no sample bytes at all, which satisfies its Gate 1 §6.5 trivially; Mars records the same in the licence spec after #451 merges. Chunk C's gates on the deleted routes go with them. On the #451 base, `listing_license_snapshot_gate` (`public_sample_service.py` 41-43 at `f046bfc`) moves unchanged into `public.py`, where it still decorates `/public/listings/{slug}` (`public.py` 790-792 at `f046bfc`); in `tests/test_listing_license_route_inventory.py` the deleted sample route leaves `expected`, the three `orders/{order_id}/members*` routes leave `ACTIVE_ROUTES`, and `/public/listings/{slug}` keeps its `listing_snapshot` marker. |
| Sample validation in `vz_publish_service.finalize_local_version` (~1311-1332) | It requires a stored `ListingSampleAsset` for each `is_sample` member. The block goes; `is_sample` remains manifest metadata only. A sample, when it returns, is served from the seller's own origin. |
| `WORKSPACE_SAMPLE_FILES_ENABLED` | Gated only samples. |
| AIM relay: `app/api/v1/aim_relay.py`, `app/services/aim_relay_service.py`, its router include (`router.py` 59, 139), and every `relay_mode` / `AIMRelayService` / `AIMConnectionMode.RELAY` branch in `aim_service.py` (at least ~103-133, ~535-611, ~681-697, ~765-766, ~823-849) | Relay unused. `connection_mode` is always DIRECT. Also remove the four `AIMTraceEventType.RELAY_*` members, their metadata schemas in `aim_observability_service.py`, and the relay-only `buyer_node_id` request field (`app/schemas/aim_session.py`). `RELAY` leaves `AIMConnectionMode`; the Postgres enum label stays (removing a label is not worth a type rewrite). |
| Shared columns on live tables, all null in production (S1737 read: `orders.delivery_manifest_hash` 0 non-null; `transfer_sessions` `manifest_hash` 0, `staging_generation` 0, `completion_state` ≠ `none` 0; `fulfillment_download_tokens` `manifest_hash` 0, `purchased_version_id` 0): `orders.delivery_manifest_hash`; `transfer_sessions.manifest_hash`, `staging_generation`, `completion_state`, `completion_lease_until`, `ck_transfer_completion_state`, `uq_transfer_manifest_receiving_order`, the `order_delivery_manifest_hash` query expression; `fulfillment_download_tokens.manifest_hash`, `purchased_version_id` | They exist only for the manifest runtime. Every surviving reader treats the value as null today; delete those reading branches in release 1. The columns and their ORM attributes stay until release 2. |
| Config used only by removed code (the generated rule below is authoritative; known names): `LISTING_ASSET_*`, `WORKSPACE_SAMPLE_FILES_ENABLED`, `SAMPLE_DAILY_BYTES_PER_LISTING`, `SAMPLE_CLIENT_RATE`, `SAMPLE_UPLOAD_RATE`, `SAMPLE_UPLOAD_TIMEOUT_S`, `SAMPLE_SELLER_QUOTA_BYTES`, `SAMPLE_PENDING_TTL_S`, `SAMPLE_APPROVED_TTL_S`, `SAMPLE_REAPER_INTERVAL_S`, `TRANSFER_SESSION_TTL_S`, `ABANDONED_ORDER_TTL_S`, `TRANSFER_PART_BYTES`, `TRANSFER_MAX_OPEN_SESSIONS`, `TRANSFER_RETRY_AFTER_S`, `TRANSFER_METADATA_WAIT_S`, `TRANSFER_LOCKED_BATCH_ROWS`, `TRANSFER_PRESIGN_TTL_S`, `TRANSFER_GRANT_MARGIN_S`, `METER_RETENTION_S`, `DOWNLOAD_GRANT_BYTES_PER_HOUR`; public sample response fields in `app/schemas/listing_public.py` | Keep `SAMPLE_MAX_FILES`, `SAMPLE_MAX_FILE_BYTES`, `SAMPLE_MAX_TOTAL_BYTES`, `TRANSFER_MAX_MEMBER_BYTES`, `TRANSFER_MAX_TOTAL_BYTES`: manifest validation in `vz_publish_service.py` uses them. |
| Release 2 only: models `multi_file_delivery.py`, `listing_sample_asset.py`, `seller_sample_asset.py`, `ListingAssetTombstone` (only; `ListingVersionMember` stays) and their `registry.py` entries; the shared-column and `aim_nodes` relay ORM attributes | Removed together with the schema they map, so models and database never disagree. |
| `scripts/verify_s1717_d_store.py`; tests that exist only for removed code | Delete, don't rewrite. |

## Keep

- The manifest contract for the future peer-to-peer design (Mars, peer message 5843): `listing_version_members`, `manifest_hash`, manifest intake and validation in `vz_publish` / `vz_publish_service.py`, `listing_summary.py`, `listing_versioning.py`, and `MULTI_FILE_DATASETS_ENABLED`, which afterwards gates only manifest publishing and stays off. The per-file grant/consume semantics and buyer-side hash check are the contract to rebuild peer to peer; their bucket-bound implementation goes.
- The live legacy delivery path (`fulfillment_listener_service.py` stream-to-disk, `delivery_service.py` `_queue_delivery_request`). It is how AIM Data orders deliver today; it goes under T-2026-000839 once a peer-to-peer replacement exists.
- Seller Workspace delivery from the seller's own bucket (`order_service` `assume_seller_role`, `seller_workspace_delivery`, `seller_workspace_r2.py`).
- Every #451 licence gate on a surviving door.

## Two releases

**Release 1 (this build): code only.** No migration, and no model or schema change: model files and ORM attributes for the tables and columns above stay exactly as they are, so `alembic check` shows no drift. Everything else in "Remove" goes. After release 1 nothing reads or writes those tables and columns.

**Release 2: schema.** Drops the nine tables, the tombstone trigger and its function, the shared columns with their index, constraint and FK, and the `aim_nodes` relay columns, and removes the models that map them, in one change. Dropping a table with foreign keys takes `ACCESS EXCLUSIVE` on its live parent tables (`orders`, `transfer_sessions`, `users`, `listing_versions`, `cloud_connections`, `seller_listing_approvals`), so release 2 runs in a short maintenance window with `ai-market-backend`, `ai-market-celery-worker` and `ai-market-celery-beat` stopped, never online. It gets its own short Gate 2 amendment with the exact stop/migrate/start procedure, and Max chooses the window. Until then the empty tables and null columns are inert.

Production state read by Vulcan 2026-09-22 (procedure step 3 in `runbooks/data-delivery-p2p.md` prints the table and relay counts; the shared-column reads were separate `psql` counts): all nine tables 0 rows; `aim_nodes` 2 rows, 0 relay; `aim_sessions` 0 rows; `orders.delivery_manifest_hash`, `transfer_sessions.manifest_hash`/`staging_generation`, `fulfillment_download_tokens.manifest_hash`/`purchased_version_id` all null; `transfer_sessions.completion_state` all `none`.

## Build rules

Report every remaining `git grep` hit in `app` and `scripts` for a removed module or symbol and why it stays. Run the full backend suite and report exact counts. Check `ai-market-frontend` for calls to removed routes; removals are a separate PR in the same round. `aim-data`: same round, remove `upload_samples` (`app/services/sample_upload_client.py`, flag-off today) and make its local publish tests treat sample members as metadata only.

Acceptance, generated rather than hand-listed: the builder's script parses deleted files and blocks at the base SHA and lists each removed module (dotted path), top-level class and function (qualified by module), route (method and path) and `Settings` field, plus `AIMConnectionMode.RELAY`, `AIMTraceEventType.RELAY_*`, the four lowercase relay event keys and the `buyer_node_id` field of the AIM session schema. Pass at the candidate SHA: no import of a removed module, no reference to a removed qualified name, no removed route in `app.routes`, no removed field on `Settings`; outside the model files, no reference to the release-2 models or to the shared-column and relay ORM attributes; `alembic check` clean. Allowlist, printed by the script: `listing_license_snapshot_gate` (moved from `public_sample_service.py` to `public.py`) and the release-2 model files and attributes. The report includes the script and its output; nothing is added to the repo.

## After deploy (release 1)

Gate: a runbooks PR that rewrites `runbooks/delivery-ack-monitor.md` down to the surviving legacy monitor (no manifest route, no `MANIFEST_DELIVERY_REQUIRED` remedy) merges with it. Then `/health` green and the full procedure in `runbooks/data-delivery-p2p.md` (every object still exists).

Afterwards:

1. Remove `LISTING_ASSET_*` from Infisical `ai-market-backend` prod (`infisical-secrets.md`).
2. Max deletes the `aimarket-listing-assets` bucket and its bucket-scoped token in the Cloudflare dashboard (he created both, 2026-09-16). Then drop the bucket step from the procedure, retire `listing-asset-store.md`, and update the current-state table.
3. Write the release-2 amendment.
