# Remove the legacy AIM Data delivery and install paths (chunk F, S1756)

**Status:** DRAFT. D1 and D2 decided by Max (2026-09-27, S1756; §3). In review with the full panel (GLM, DeepSeek, CC in the Gemini seat per `d50cbd80` until 2026-10-05; unanimity). Not approved. Not dispatchable.

**Authority:** Gate 1 §7 of `specs/BQ-AIM-DATA-GATEWAY-S1741-GATE1.md` (approved 3/3 at `8078d1e4`, Event `fb0d7272`): legacy trust-channel fulfilment, `_queue_delivery_request`, serial activation and metering, and the AIM Data-only publish routes are removed in chunk F under their own deletion spec using the S1737 pattern; vectorAIz's routes stay. Gate 2 §12 (approved at `ed36b0ec`) narrows this: serial activation and metering are not removed while any vectorAIz install uses them, and this spec must first attribute every active serial to a product. Rule page: `runbooks/data-delivery-p2p.md` (the legacy path is the one remaining place ai.market carries delivered bytes; the gateway's direct delivery is its replacement, which T-2026-000839 was waiting for). Risk class: customer data, delivery and payments, so unanimous Council on this spec and on the build (CORE S3).

**Base:** `ai-market-backend` `main` at `a0b4a969` (production). Line numbers below are at that SHA; re-cite at dispatch. MP builds on `build/aim-data-legacy-removal-s1756`.

## 1. Principle

AIM Data is now the gateway. Delete every backend path whose only purpose is to serve a legacy AIM Data install (the 90,000-line `aidotmarket/aim-data` container), and every path through which ai.market receives, stages or streams the bytes of a delivered file. Where a surviving caller branches into removed code, delete the branch so the surviving behaviour is the only behaviour. No replacement abstractions, shims or new flags. Anything vectorAIz still needs stays, and is named in §5.

## 2. Production read (Vulcan, 2026-09-27 08:30Z, read-only transaction)

Method: `psql` over `scripts/test-db-dsn.sh` with `set default_transaction_read_only=on`; queries in §9. It supersedes the Gate 2 §12 table, which counted listings with `status='listed'`. Production listings use `published`, so that row was always 0 and is wrong.

**Serial attribution (Gate 2 §12 requirement).** vectorAIz stopped releasing at `v1.20.42-rc.4` (2026-07-17; tag `pre-split` 2026-05-27). AIM Data releases are `aim-data-v1.21.0` (2026-06-20) onwards, and AIM Data's config defaults `app_version` to `1.25.0`; vectorAIz defaults to `dev`.

| Activated serials metered in the last 30 days: 106 | Count |
| --- | --- |
| Host `Koskadeux.local` (our own machine; versions `dev`, `1.25.0`, `local-s750`) | 63 |
| Docker-hostname containers at AIM Data versions `v1.22.5-rc.1` … `v1.25.2`, activation IP 79.152.10.124 (the same IP as `Koskadeux.local`: our e2e and test installs; 4 are linked to `e2e-test.ai.market` users) | 39 |
| Container, blank version, activation IP 79.152.10.124, linked to a `kisa.cat` user | 1 |
| Containers, blank version, auto-provisioned, no user, activation IP 195.64.239.146 (a Ukrainian ISP), activated 2026-09-15, last metered 2026-09-17 | 3 |
| Any vectorAIz release (`v1.20.x`) | **0** (last vectorAIz meter 2026-06-26) |

So in the last 30 days every serial activation and meter came from AIM Data or from our own machine. vectorAIz has no metered install since 2026-06-26.

**All 579 activated serials** (GLM F4; classification: host `Koskadeux.local` → ours; version `1.21`–`1.29` with or without `v` → AIM Data; `v1.20.x` or `latest` → vectorAIz; `dev` elsewhere → pre-split vectorAIz default; empty → blank):

| Bucket | Serials | Metered last 30 days | Never metered | Linked to a user | Distinct activation IPs | Last meter |
| --- | --- | --- | --- | --- | --- | --- |
| vectorAIz (`v1.20.x`, `latest`) | 212 | 0 | 184 | 1 | 152 | 2026-06-26 |
| pre-split `dev`, not our machine | 142 | 0 | 123 | 0 | 105 | 2026-03-21 |
| AIM Data (`1.21`+) | 108 | 39 | 67 | 4 | 58 | 2026-09-26 |
| our machine (`Koskadeux.local`) | 103 | 63 | 7 | 0 | 5 | 2026-09-23 |
| blank version | 14 | 4 | 6 | 1 | 8 | 2026-09-17 |

Residual unknowns accepted for this release: the 14 blank-version serials (4 recent: 1 is Max's `kisa.cat`, 3 are the unlinked 195.64.239.146 containers) and the 142 pre-split `dev` serials (none metered since March). None has a published listing. Serial activation and metering stay (§5), so none of them loses anything they use today except legacy delivery. The deploy gate re-runs this query (§9) and blocks on any new bucket or any residual gaining a published listing. The three unlinked containers from 195.64.239.146 are the only installs that may be someone outside; they have no account, so no listing.

**Installs behind published listings.** 3 published listings belong to sellers with an active `vz_installs` row. Each is `ai_queryable`, so a purchase today goes through `FulfillmentService.request_fulfillment` to the seller's install over the trust channel:

| Listing | Seller | Install | Note |
| --- | --- | --- | --- |
| `5ab53e16` "Competitive Programming Problems", published 2026-07-06 | `eolymp.com` (Sergey, the first real seller) | 1 active, created 2026-06-17; serial activated, no meter on record; device last seen 2026-09-22 13:27Z | `source_delivery` holds Kaggle and Hugging Face links; `raw_metadata.s3_connection` set: his files are on his own AWS S3 through AIM Data's S3 connection (the only production listing with it) |
| `936a08d6` "Gene Expression Differential Analysis Dataset", published 2026-09-15 | `kisa.cat` | 3 active, last created 2026-09-08; serial last metered 2026-09-15 | activated from our IP |
| `281a2b31` "New York City Vehicle Collisions", published 2026-06-08 | `kisa.cat` | same | `source_delivery` null |

Other published listings do not depend on a legacy install: 10 AlphaFold `reference` listings (`source_delivery.kind = public_url`, served by `orders.py` ~708), 38 `e2e-test.ai.market` fixtures, and 9 seeded `ai.market`/`example.com` listings with no install (they cannot be fulfilled today either). Orders: 9 ever; the only `trust_channel` delivery is `fb5eab96` (e2e, 2026-09-22).

**Already dead in production:** `LISTING_LICENSES_ENABLED=true`, so `POST /api/v1/vz/publish` refuses every device publish with `WEBSITE_LICENSE_PUBLISH_REQUIRED` (`seller_workspace_listing_guard.py` 10) for both products. `MULTI_FILE_DATASETS_ENABLED`, `DEMO_FULFILLMENT` and `FULFILLMENT_STAGING_DIR` are unset. `AIM_GATEWAY_ENABLED=true`. The website calls none of `/trust/*`, `/deliveries/*`, `/serials/*`, `/vz/*`, `download-file` or the legacy `orders/{id}` download doors (`ai-market-frontend` `3a44f774`); it does call the S1737 manifest-member routes, which the folded frontend PR removes (§4).

## 3. Decisions needed from Max before review

**D1. vectorAIz shares the delivery path.** vectorAIz `v1.20.42` carries the same trust-channel client and fulfilment handler as AIM Data (`vectoraiz` `app/services/trust_channel_client.py`, `fulfillment_service.py`; registers via `POST /api/v1/trust/register` and connects to `/ws/trust-channel`). Removing legacy trust-channel fulfilment therefore also means a vectorAIz install can no longer deliver a sale. Gate 1 §7 asks for both ("remove legacy trust-channel fulfilment"; "vectorAIz's routes stay"), which cannot both hold for this one path.
- **Decided (Max, 2026-09-27 ~11:20 CEST, S1756): A.** Max: "Yes on Vectoraiz, but we will be updating it and adding it back so please keep runbook data." Condition: vectorAIz is coming back in an updated form, so everything we know about how its connected mode and legacy delivery worked is kept (§5, "Runbook data").
- A: remove fulfilment over the channel for both products. CORE S1 and P8 forbid ai.market carrying delivered bytes, and the rule page already names this path as the violation. vectorAIz keeps activation, metering, registration and the channel transport; a vectorAIz seller who sells delivers through a gateway or Seller Workspace. Cost today: nothing, since no vectorAIz install has been seen since June and device publishing is already refused.
- B: keep the legacy fulfilment for vectorAIz only. Keeps a CORE S1 violation alive for a product with no active installs. Not recommended.
- C (larger): also remove the trust channel transport and device registration. Simpler code, but vectorAIz loses its connected mode entirely. Not proposed here.

**D2. Listings on legacy installs. Decided (Max, 2026-09-27 ~12:10 CEST, S1756).**
- `kisa.cat` is Max's own account. Its two listings (`936a08d6`, `281a2b31`) are unpublished at the chunk F deploy; Max re-lists through the website if he wants them.
- Sergey (`5ab53e16`) keeps his data on AWS, so he does not need a gateway. Max: "When proven I want to switch him to the web based tools but I need to know that the switch will work." His listing therefore moves to Seller Workspace (AWS S3), and only after a switch rehearsal passes (§6 step 2). His legacy install was last seen 2026-09-22 13:27Z, so his listing keeps its current path until the switch.
- Consequence for chunk E: Sergey is not the Gate 1 §8 real-seller gateway canary; that needs a seller who keeps data on their own infrastructure.

Review can proceed now; the deploy waits on §6 step 2.

## 4. Remove (D1-A)

Line numbers are at `a0b4a969`; the generated inventory (§7) is authoritative wherever this table and the code disagree.

| Code | Why it goes |
| --- | --- |
| **Fulfilment dispatcher.** In `fulfillment_service.py`: `_send_fulfillment_request`, `_queue_fulfillment`, `process_pending_for_seller` (310; no callers, returns 0), `handle_fulfillment_response` (320), `_handle_raw_download_fulfillment` (524), `_get_active_trust_session` (583), `_get_device_identifier_for_seller` (713), `_update_pending_status` (730), `_mark_fulfillment_completed`/`_failed` and `_notify_*` if only reached from those; inside `request_fulfillment` (142-309): the manifest refusal (198-200), the pending-row check (210-222), both refresh branches (223-235, 263-289; `is_refresh` callers are the removed refresh routes), the demo branch (240-257), the `file_download` branch (259-261) and the trust-session send/queue tail (291-308); the `delivery_manifest_hash` column from its SELECT (162) and from the workspace condition (204). `request_fulfillment` keeps, in this order: order lookup, licence check and seller/listing match (unchanged, 179-190); **gateway** (192-196, unchanged); **Seller Workspace** (202-208, unchanged but for the dropped column); the paid-status check (236-238); **public-URL reference**: new explicit branch, `fulfillment_type == 'reference'` and `source_delivery.kind == 'public_url'` and `source_delivery.url` a non-empty string (anything else falls to the refusal; an `HTTPException` from `deliver_reference_order`, e.g. `order_service.py` 1453-1458, is also mapped to the refusal, GLM R2-4) → `OrderService.deliver_reference_order` (`order_service.py` 1428, the call the free path already makes at `checkout.py` 332 and `transaction_service.py` 1661) → `{"success": True, "status": "delivered"}`; everything else → `{"success": False, "status": "unavailable", "error": "Order is not in a fulfillable state"}`. | Legacy trust-channel fulfilment (Gate 1 §7). The reference branch is not new behaviour to design: today a *paid* reference order falls through to `_queue_fulfillment` (GLM F1, DeepSeek F1); after this change it is delivered by the existing free-path function. |
| **Webhook handling of the refusal.** `webhooks.py` `_mark_paid_and_start_fulfillment_with_license` (545-572) and the second caller (1003-1018) raise `RuntimeError` when `request_fulfillment` returns `success: False`, which makes Stripe retry. For `status: "unavailable"` they log, record the order event, and return normally (the order stays paid and `pending_delivery` for the existing problem/refund path). | A refused kind must not produce a Stripe redelivery loop. The other callers of `request_fulfillment` (`transaction_service.py` 1756, e2e synthetic checkout; `fulfillment_broker.py` 97, agent API; `order_listeners.py` 54, logs only) keep raising on `success: False`; after the §6 deploy gates no published listing can reach `unavailable` through them, and the builder reports each caller's handling (DeepSeek R2-1). |
| `app/services/fulfillment_listener_service.py` (whole), `app/api/v1/endpoints/fulfillment_download.py` (`GET /orders/{order_id}/download-file`) with its import and include (`router.py` 466-467), `app/services/demo_fulfillment_service.py`, `DEMO_FULFILLMENT` and `FULFILLMENT_STAGING_DIR` and their production refusal in `config.py` | Stream-to-disk on `/tmp/fulfillment` and the proxied buyer download: ai.market holding delivered bytes. Demo exists only for this path. |
| **Channel fulfilment.** In `trust_websocket.py`: every `vai.fulfillment.*` message type in the allowlists and `FULFILLMENT_LISTENER_ACTIONS` (96-139), the dispatch (1102-1116) and `_handle_fulfillment_action` (1223-1407); in `trust_websocket_vc.py`: `vai.fulfillment.response` and `vai.fulfillment.ack` in `TRUST_CHANNEL_ALLOWED_ACTIONS` (80-81); `action_executor_service.py` 551-566 and any `_requires_trust_channel` entry that exists only for them; `trust_outbound_writer.py` 261-279 (fires only on `related_order_id`, set only by removed code); `app/schemas/fulfillment.py` symbols used only by removed code; the `order_listeners.py` trigger if it reaches only removed branches. (`app/actions/definitions.py`/`registry.py` hold no fulfilment action; DeepSeek F4.) | Server half of the same path. The channel transport, registration and non-delivery control-plane actions stay (§5). |
| `DeliveryService` (`delivery_service.py`, whole, including `_queue_delivery_request` 803, `stream_from_vz` 290 and `record_stripe_webhook_idempotency` 577), `deliveries.py` (all eight `/deliveries/{transaction_id}/…` routes) with its import (`router.py` 84) and include (205), `webhooks.py` `_create_delivery_for_payment` (1838-1887) and `transaction_service.py` 937-941 (the whole `if` block): each call site is **replaced**, not just deleted, by `FulfillmentService.request_fulfillment(order_id)` after the payment commit, with the same `unavailable` handling as the checkout webhook, so a paid order recovered through `payment_intent.succeeded` (`webhooks.py` 906-926) or agent-payment recovery (`transaction_service.py` 917-941) reaches the same gateway, workspace or reference outcome (GLM R2-1) | `_queue_delivery_request` asks the install to stream the file to the backend (`delivery_mode: trust_channel_proxy`); `stream_from_vz` streams it on to the buyer. Both callers only write delivery metadata, `delivery_ready_at` and idempotency markers; no order or transaction status transition depends on them (all three reviewers agree; builder proves with before/after tests, §7). |
| **Legacy download doors.** `raw_download_service.py` (whole) and `orders.py` `POST /{order_id}/download-token` (450) and `GET /{order_id}/download` (515); `POST /{order_id}/download` (346) with `OrderService.issue_download_token` and its gatekeeper and device-S3 branches (~1560-1680); `POST /{order_id}/download/redeem` (400), `POST /{order_id}/download/refresh` (414), `POST /{order_id}/delivery/refresh` (428), `POST /{order_id}/refresh` (941-1050, "send vai.fulfillment.refresh to seller's vectorAIz"); `POST /{order_id}/deliver` (859) with `OrderService.initiate_delivery` (1333) if the builder's inventory shows it serves only gatekeeper/device delivery; the other callers of `issue_download_token` (GLM R2-2): agent API `GET /orders/{order_id}/data` (`agent/router.py` 932-980) and `GET /orders/{order_id}/artifact` (1117-1195) with `FulfillmentBroker.get_artifact_url` (`fulfillment_broker.py` 175-250), and `GET /transactions/{transaction_id}/download` (`transaction_actions.py` 211-230): all removed, each returns 404 (the agent API issues no usable credential today, `build:bq-agent-api-oauth-access-s1738` deferred; gateway, workspace and reference buyers have their own access routes) | Each issues a token or URL for a legacy install, a seller gatekeeper worker, or AIM Data's device S3 connection. Gateway and Seller Workspace buyers use their own routes; the website calls none of these (`ai-market-frontend` `3a44f774`). |
| **AIM Data device-S3 delivery** (DeepSeek F2). Routes `/serials/{serial}/s3-connections/*` (`router.py` 178; `external-id`, `verify`, `list-objects`, `presign-object`); in `order_service.py`: the `s3_connection` branches of `derive_delivery_type` (130-148, 355), `_issue_s3_scoped_delivery` (468-505), `_count_recent_s3_scoped_credential_events` (517-524), `_build_s3_download_urls` (545-600), `_validate_device_s3_record` and the `s3_presigned_url` `delivery_config` handling (~1684-1810), `refresh_s3_scoped_delivery` (1814-1848); in `orders.py` `GET /{order_id}/access` (610): the `_build_s3_download_urls` and `gatekeeper_url` branches (754, 761), keeping the public-URL branch (~695-731) | Keyed on `raw_metadata.s3_connection`, which only AIM Data's S3 setup writes. Production: exactly one listing carries it, Sergey's `5ab53e16`, which is why the deploy waits for his switch (§6). `s3_fulfillment.py` stays whole: `order_service.py` 56-60, `s3_qa_sampler.py` 17 and `scoring_service.py` 32 import it; the builder removes only what the inventory proves orphaned. |
| **AIM Data-only publish routes.** `vz_publish.py`: `POST /vz/register` (55), `POST /vz/versions/{version_id}/confirm` (188), `POST /vz/rotate-key` (210), `DELETE /vz/install/{install_id}` (232), `POST /vz/versions/{version_id}/members` (`upload_version_members`, 272, on `local_router`); `vz_samples.py` (whole: `POST /vz/versions/{version_id}/samples/{index}`, 21) together with its module-level import and include in `vz_publish.py` (300-302) and the `authenticate_local_action` coupling it uses (`vz_samples.py` 33) if nothing else does (CC M1) | Called only by AIM Data. `POST /vz/publish` (113) is vectorAIz's and stays, though it refuses today (§2); `import app.main` must still succeed. |
| **S1737 storage deletion, folded in.** Everything in `specs/P2P-STORAGE-DELETION-S1737.md` §Remove (manifest runtime, delivery staging task, the six delivery tables, shared manifest columns, AIM relay), with the supersessions below. | No build or BQ for S1737 exists; Mars (peer 6463) does not hold it and has no objection. Stay clear of Mars's live paths `app/mcp/connector_auth` and `connector_shared`. |
| `GET /seller/pending` (`seller.py` 363-415): no client in `aim-data`, `vectoraiz` or `ai-market-frontend`; its message "Please deliver … via vectorAIz" becomes false (GLM Q2). The `/seller/stats` field named `pending_fulfillments` counts orders, not the table, and stays | Dead door after D1-A. |
| Config, tests and scripts used only by removed code (generated list authoritative); `scripts/staging_seed.py` writes to `fulfillment_download_tokens` in `upsert_order` (311-377, the `FulfillmentDownloadToken` at 368) and in the SQL block (687-712): both go (DeepSeek R2-2) | Dead with their readers. Delete, do not rewrite. |

**S1737 supersessions** (all three reviewers: "apply unchanged" was contradictory). Where S1737 and this spec differ, this spec wins:

| S1737 text | In this release |
| --- | --- |
| §Keep: "the live legacy delivery path (`fulfillment_listener_service.py` stream-to-disk, `delivery_service.py` `_queue_delivery_request`) … goes under T-2026-000839" | Deleted whole (rows above). T-2026-000839 closes with this release. |
| §Remove, tests: `test_shipped_legacy_behavior_golden` and its fixtures survive | Deleted with `tests/test_delivery_listener.py` whole; its module-level imports of removed modules (30-34, 18) make the file uncollectable once those modules go. |
| §Remove, shared columns: in-place edits in `fulfillment_listener_service.py`, `fulfillment_service.py` and `demo_fulfillment_service.py` | Subsumed by deletion where the file or branch goes; the kept sites are re-cited at `a0b4a969` (CC L1): `transaction_service.py` 1674, 1910, 1914, 1954; `order_service.py` 723, 732, 741, 745, 760, 1322, 1324, 1330, 1390, 1478 (including the order INSERT); `orders.py` 640, 691, 971; `trust_websocket.py` 1301, 1313; `seller_workspace_delivery.py` 263, 277, 284; `fulfillment_service.py` 162 (drop only that column from the SELECT). |
| §Keep: `vz_samples.py` and the local sample route | Deleted (AIM Data-only). The workspace sample route, public sample serving, `public_sample_service.py`, `listing_asset_store.py` sample API and the three sample tables stay. |
| §Remove: the three manifest-download routes `orders/{order_id}/members*` "the frontend removals are a separate PR in the same round" | Unchanged, and now required: `ai-market-frontend` calls them from `app/dashboard/orders/[id]/DatasetMembers.tsx` 66, `memberDownload.ts` 18 and `page.tsx` 39. That frontend PR is part of this release. |
| §After deploy: `delivery-ack-monitor.md` rewritten to "the surviving legacy monitor" | No legacy monitor survives. The page keeps its content with a dated status line (§5 runbook data). |

## 5. Keep

- **Gateway delivery** (`aim_gateway*.py`, `gateway_delivery_*`, `order_delivery_states.py`, tasks `aim_gateway_*`), **Seller Workspace delivery** (`seller_workspace_delivery*.py`, `assume_seller_role`), and **public-URL reference listings** (`orders.py` ~708, `source_delivery.py`).
- **vectorAIz:** serial activation and metering (`serials.py` routes other than `s3-connections`, `serial_service.py`, `serial_token_service.py`, `metering_ingestion_service.py`), `POST /api/v1/trust/register`, the channel transport (vectorAIz `v1.20.42` connects to the top-level alias `/ws/trust-channel`, `main.py` 896-898; AIM Data to `/api/v1/trust/stream`; both are the one `trust_websocket` handler, which stays minus its fulfilment handling), `/trust/stream/vc`, the device routes in `trust.py`, non-delivery control-plane actions, `POST /vz/publish`, and the `/api/v1/connect/*` onboarding routes. The `vz_installs` table stays (read by `vz_publish_service.py`); only the AIM Data routes that write it go.
- **Samples:** everything S1737 keeps (seller-chosen public sample, CORE v9.19).
- **Schema (GLM F5, DeepSeek F6).** This release drops only what S1737 drops. Every other legacy table stays as history, with its ORM model so `alembic check` is clean, and **no surviving writer**; a later cleanup may drop them once vectorAIz's return is designed (Max D1: keep what we know).

| Table | Disposition |
| --- | --- |
| `transactions`, `vz_installs`, `serials`, `serial_usage` | Live, kept. |
| `pending_fulfillments`, `delivery_audit_log`, `delivery_dead_letter_queue`, `stripe_webhook_idempotency` | History; no reader or writer after this release. |
| `transfer_sessions`, `fulfillment_download_tokens`, `fulfillment_download_log` | History, minus the S1737 shared columns; no writer after this release (`scripts/staging_seed.py` block removed, §4). |
| S1737's six delivery tables, shared columns and `aim_nodes` relay columns | Dropped by S1737's migration. |
- **Runbook data (Max's D1 condition).** No runbook page is deleted by this change. Pages that describe removed behaviour (`trust-channel.md`, `dual-brand-vectoraiz-aim-channel.md`, `vz-release-process.md`, `aim-data.md`, `aim-data-release-process.md`, `aim-data-sign-in-with-ai-market.md`, `publish-paths.md`, `runbooks/data-delivery-p2p.md`, `runbooks/delivery-ack-monitor.md`, and any other page the builder's grep finds) keep their content and gain a short dated status line at the top: what chunk F removed from the backend, that vectorAIz will return in an updated form, and where the removed code lives. The removed code stays recoverable by an annotated git tag `pre-chunk-f-s1756` on the backend base SHA, pushed before merge; each page's status line names that tag. Pages are corrected only where they would otherwise tell an operator something false about production today.
- Out of scope, named so reviewers do not assume them: the AIM Node endpoints (`aim.py`, `aim_discovery.py`, `aim_observability.py`, `aim_seller.py`, `aim_metering.py`) and the data-verification routes AIM Data calls (`/data-verification/*`). Both are candidates for later removal; the verified-label product has no gateway equivalent yet, so that is a product decision, not a deletion.

## 6. Order of operations

1. Max answered D1 and D2 (§3). 2. **Sergey's switch, before the deploy.** (a) Rehearsal on current production with Max's `kisa.cat` account and its verified AWS connection: a folder shaped like Sergey's dataset in S3, listed through Seller Workspace with a licence, bought with a small real card payment, every file downloaded in a normal browser and its SHA-256 matched, the payout reaching the seller's Stripe account after the hold, and the refund decision path exercised. The existing proof (AWS order `c91951ed`, $25, 2026-09-10) is one synthetic one-row file, predates the licence and money-path changes since, and never reached payout (`runbooks/seller-workspace-live-release.md`: payout and full AWS release still open), so it is not enough. (b) Max reviews the result and gives GO. (c) Sergey connects his AWS bucket in Seller Workspace, his listing is re-pointed or re-published from it, one check purchase delivers, then his legacy install is retired. (d) The §9 deploy-gate queries pass: no published listing on a legacy install or on AIM Data's device S3 connection, and no new serial bucket. The `kisa.cat` listings are unpublished at the deploy. 3. Full panel on this spec. 4. MP builds; Gate 3 full panel. 5. One deploy: this code removal plus S1737's code and its one migration. 6. After deploy: `/health` green; `GET /api/v1/deliveries/<uuid>`, `GET /orders/<uuid>/download-file` and `POST /api/v1/vz/register` return 404 from outside; a gateway order and a Seller Workspace order still deliver (re-run the S1755 self-test step 8 and the workspace smoke); runbook status lines per §5 (runbook data kept, `data-delivery-p2p.md` table updated to "no path carries delivered bytes" with the old rows kept below as history); `aidotmarket/aim-data` archived with a README pointer to the gateway (Gate 1 §7), after Max's GO.

## 7. Build rules

Report every remaining `git grep` hit in `app` and `scripts` for a removed module, symbol, route or protocol string and why it stays. Run the full backend suite on disposable PG17 and report exact counts against `main` (known baseline: money suites 51 failures identical to base, S1755). `import app.main` succeeds and `pytest --collect-only` is clean. Frontend: the folded S1737 manifest-member removal (§4); the builder greps `ai-market-frontend` for every other removed path and reports none.

**Before merge:** push an annotated tag `pre-chunk-f-s1756` on the backend base SHA (§5 runbook data).

**Generated acceptance** (S1737 pattern, extended per GLM F3, CC L3, DeepSeek F4). The builder's script takes two inputs and prints both inventories:
1. Parsed from files deleted at the base SHA: every module (dotted path), top-level class and function, route (method and path, from the FastAPI decorators) and `Settings` field.
2. Taken from this spec's §4 as a list, for symbols removed from kept files: every removed method, function and route in `fulfillment_service.py`, `order_service.py`, `orders.py`, `vz_publish.py`, `webhooks.py`, `transaction_service.py`, `trust_websocket.py`, `trust_websocket_vc.py`, `action_executor_service.py`, `trust_outbound_writer.py`, `router.py`, `config.py`; the protocol strings `vai.fulfillment.*`; the dropped tables, columns and models (from S1737).

Pass at the candidate SHA: no import of a removed module; no reference to a removed qualified name; every removed route absent from `app.routes`, and a test that each returns 404; no removed `Settings` field; zero hits for `vai.fulfillment` and for the S1737 column names in `app` and `scripts`; no writer (INSERT, UPDATE, ORM add) for any §5 history table (name collisions that are not writes, such as `app/allai/escalation_pipeline.py` 605-607 `_delivery_dead_lettered`, are pre-attributed as non-writers); `alembic check` clean; the migration upgrades and downgrades on disposable PG17.

**Behaviour tests** (added, not only deleted):
- `request_fulfillment`: gateway order → unchanged; workspace order → unchanged; **paid** public-URL reference order → `delivered`, transaction delivered, `GET /orders/{id}/access` returns the URL, no pending row and no channel message; free reference order → unchanged; `ai_queryable` with a legacy install, `file_download` without gateway source, and a former demo seller → `unavailable`.
- Webhook: `checkout.session.completed` for each kind above; an `unavailable` result returns 200 to Stripe and leaves the order paid and `pending_delivery`; `payment_intent.succeeded` no longer writes `stripe_webhook_idempotency` and changes no order or transaction status compared with base (before/after state diff), for a gateway order and a workspace order.
- Agent-payment recovery (`transaction_service.py` ~925-941) and `payment_intent.succeeded`: for a gateway and a workspace order, same order and transaction states as base; for a paid public-URL reference order, order and transaction `delivered` and `GET /orders/{id}/access` returns the URL; no pending row, channel message or idempotency write.
- Reference listings with `{"kind":"public_url","url":null}` and with an empty URL: webhook 200, refusal recorded, order stays `pending_delivery`.
- `GET /orders/{id}/data`, `GET /orders/{id}/artifact` (agent API) and `GET /transactions/{id}/download` return 404.

The report includes the script, its two inventories and output; nothing is added to the repo except the tests.

## 8. Review questions

1. Is anything in §4 still reached by the gateway, Seller Workspace or public-URL paths?
2. Is anything in §5 kept only by habit, and could go now without touching vectorAIz?
3. Does removing `_create_delivery_for_payment` change any money-state transition for gateway or workspace orders?
4. Does folding S1737 into one release create any ordering hazard (its migration plus this code removal in one deploy)?
5. R2: do the S1737 supersessions, the reference branch, the webhook refusal handling and the table dispositions close R1?
6. SIMPLER / BETTER.

## 9. Queries

```sql
set default_transaction_read_only=on;
-- serial attribution, all activated serials (deploy gate)
with s as (select *, case when hostname='Koskadeux.local' then 'our_machine'
  when version ~ '^v?1\.2[1-9]' then 'aim_data'
  when version ~ '^v?1\.20\.' or version='latest' then 'vectoraiz'
  when coalesce(version,'')='' then 'blank' else 'other:'||version end prod
  from serials where status='activated')
select prod, count(*), count(*) filter (where last_meter_at>now()-interval '30 days') m30,
  count(*) filter (where last_meter_at is null) never, count(user_id) linked,
  count(distinct activation_ip) ips, max(last_meter_at)::date last
from s group by 1 order by 2 desc;
-- published listings whose seller has an active legacy install (deploy gate: 0 rows)
select l.id, split_part(u.email,'@',2), l.fulfillment_type, l.published_at
  from listings l join users u on u.id=l.seller_id
 where l.status='published' and exists (select 1 from vz_installs i where i.seller_id=u.id and i.is_active);
-- published listings on AIM Data's device S3 connection (deploy gate: 0 rows)
select id from listings where status='published' and raw_metadata ? 's3_connection';
-- published listings whose seller holds a residual serial (blank or pre-split dev, not our machine) (deploy gate: 0 rows)
select l.id, split_part(u.email,'@',2) from listings l join users u on u.id=l.seller_id
 where l.status='published' and exists (select 1 from serials s where s.user_id=u.id and s.status='activated'
   and coalesce(s.hostname,'')<>'Koskadeux.local' and (coalesce(s.version,'')='' or s.version='dev'));
-- orders by delivery method
select coalesce(delivery_method::text,'?'), count(*) from orders group by 1;
```

Client path inventory: `git grep` of `/api/v1/…` literals in `aidotmarket/aim-data` and `aidotmarket/vectoraiz` `origin/main` `app/`; AIM Data-only: `serials/{serial}/s3-connections/*`, `vz/register`, `vz/versions/*`, `vz/rotate-key`, `vz/install/*`, `trust/stream`, `data-verification/*`, `listings/{id}/at-a-glance*`; both: `serials/{serial}/{activate,meter,refresh,status,account,credits/*}`, `trust/register`, `connect/*`, `vz/publish`.
