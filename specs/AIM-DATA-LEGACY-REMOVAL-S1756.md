# Remove the legacy AIM Data delivery and install paths (chunk F, S1756)

**Status:** DRAFT. D1 decided by Max (2026-09-27, S1756): option A, with the condition in §3 D1. D2 open. Then the full panel (GLM, DeepSeek, CC in the Gemini seat per `d50cbd80` until 2026-10-05; unanimity). Not approved. Not dispatchable.

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
| Any vectorAIz release (`v1.20.x`) | **0** (last vectorAIz meter 2026-06-05) |

So in the last 30 days every serial activation and meter came from AIM Data or from our own machine. vectorAIz has no metered install since June. The three unlinked containers from 195.64.239.146 are the only installs that may be someone outside; they have no account, so no listing.

**Installs behind published listings.** 3 published listings belong to sellers with an active `vz_installs` row. Each is `ai_queryable`, so a purchase today goes through `FulfillmentService.request_fulfillment` to the seller's install over the trust channel:

| Listing | Seller | Install | Note |
| --- | --- | --- | --- |
| `5ab53e16` "Competitive Programming Problems", published 2026-07-06 | `eolymp.com` (Sergey, the first real seller) | 1 active, created 2026-06-17; serial activated, no meter on record | `source_delivery` holds Kaggle and Hugging Face links only |
| `936a08d6` "Gene Expression Differential Analysis Dataset", published 2026-09-15 | `kisa.cat` | 3 active, last created 2026-09-08; serial last metered 2026-09-15 | activated from our IP |
| `281a2b31` "New York City Vehicle Collisions", published 2026-06-08 | `kisa.cat` | same | `source_delivery` null |

Other published listings do not depend on a legacy install: 10 AlphaFold `reference` listings (`source_delivery.kind = public_url`, served by `orders.py` ~708), 38 `e2e-test.ai.market` fixtures, and 9 seeded `ai.market`/`example.com` listings with no install (they cannot be fulfilled today either). Orders: 9 ever; the only `trust_channel` delivery is `fb5eab96` (e2e, 2026-09-22).

**Already dead in production:** `LISTING_LICENSES_ENABLED=true`, so `POST /api/v1/vz/publish` refuses every device publish with `WEBSITE_LICENSE_PUBLISH_REQUIRED` (`seller_workspace_listing_guard.py` 8) for both products. `MULTI_FILE_DATASETS_ENABLED`, `DEMO_FULFILLMENT` and `FULFILLMENT_STAGING_DIR` are unset. `AIM_GATEWAY_ENABLED=true`. The website calls none of `/trust/*`, `/deliveries/*`, `/serials/*`, `/vz/*` or `download-file` (`ai-market-frontend` `3a44f774`).

## 3. Decisions needed from Max before review

**D1. vectorAIz shares the delivery path.** vectorAIz `v1.20.42` carries the same trust-channel client and fulfilment handler as AIM Data (`vectoraiz` `app/services/trust_channel_client.py`, `fulfillment_service.py`; registers via `POST /api/v1/trust/register` and connects to `/ws/trust-channel`). Removing legacy trust-channel fulfilment therefore also means a vectorAIz install can no longer deliver a sale. Gate 1 §7 asks for both ("remove legacy trust-channel fulfilment"; "vectorAIz's routes stay"), which cannot both hold for this one path.
- **Decided (Max, 2026-09-27 ~11:20 CEST, S1756): A.** Max: "Yes on Vectoraiz, but we will be updating it and adding it back so please keep runbook data." Condition: vectorAIz is coming back in an updated form, so everything we know about how its connected mode and legacy delivery worked is kept (§5a).
- A: remove fulfilment over the channel for both products. CORE S1 and P8 forbid ai.market carrying delivered bytes, and the rule page already names this path as the violation. vectorAIz keeps activation, metering, registration and the channel transport; a vectorAIz seller who sells delivers through a gateway or Seller Workspace. Cost today: nothing, since no vectorAIz install has been seen since June and device publishing is already refused.
- B: keep the legacy fulfilment for vectorAIz only. Keeps a CORE S1 violation alive for a product with no active installs. Not recommended.
- C (larger): also remove the trust channel transport and device registration. Simpler code, but vectorAIz loses its connected mode entirely. Not proposed here.

**D2. Sergey's listing.** Gate 1 §7: an install serving a live listing is named and migrated (pair a gateway, re-point the listing, uninstall) before its path is removed. `5ab53e16` is that listing. Options: migrate it as the chunk E real-seller canary (Gate 1 §8) if Sergey agrees; or unpublish it until he pairs a gateway. The `kisa.cat` listings: migrate or unpublish on the owner's word (activated from our own IP; confirm whose account it is).

Until D2 is answered this spec is not sent to review.

## 4. Remove (assuming D1-A)

| Code | Why it goes |
| --- | --- |
| Legacy fulfilment over the channel: `FulfillmentService._send_fulfillment_request`, `_queue_fulfillment`, `process_pending_for_seller`, `handle_fulfillment_response`, `_handle_raw_download_fulfillment`, `_get_active_trust_session`, `_get_device_identifier_for_seller`, `_update_pending_status`, the refresh branch that re-requests a device S3 URL, the demo branch, and every other branch of `request_fulfillment` after the gateway and workspace branches (`fulfillment_service.py` ~142-310, ~320-845). `request_fulfillment` keeps: order lookup, licence check, seller/listing match, the gateway branch, the workspace branch; anything else returns `{"success": False, "error": "Order is not in a fulfillable state"}` (the existing refusal) | This is the legacy trust-channel fulfilment (Gate 1 §7). |
| `app/services/fulfillment_listener_service.py` (whole), `app/api/v1/endpoints/fulfillment_download.py` (`GET /orders/{order_id}/download-file`) and its router include (`router.py` 465-467), `app/services/demo_fulfillment_service.py` | Stream-to-disk on `/tmp/fulfillment` and the proxied buyer download: ai.market holding delivered bytes. Demo writes synthetic rows to the same staging dir and exists only for this path. |
| Channel fulfilment handling: `_handle_fulfillment_action` and every fulfilment/delivery message type in `trust_websocket.py` (~1223-1407 and its dispatch sites), the fulfilment actions in `app/actions/definitions.py`/`registry.py` and `action_executor_service.py` (~552-560 and `_requires_trust_channel` entries that exist only for them), the `order_listeners.py` fulfilment trigger if it only reaches removed branches | Server half of the same path. The channel transport, registration and non-delivery control-plane actions stay (§5). |
| `DeliveryService` (`app/services/delivery_service.py`, whole, including `_queue_delivery_request` 803 and `stream_from_vz` 290), `app/api/v1/endpoints/deliveries.py` (all eight `/deliveries/{transaction_id}/…` routes) and its include (`router.py` 205), `webhooks.py` `_create_delivery_for_payment` (1838) and its call (926), `transaction_service.py` 938-941 | `_queue_delivery_request` asks the install to stream the file to the backend (`delivery_mode: trust_channel_proxy`); `stream_from_vz` streams it on to the buyer. The `stripe_webhook_idempotency` rows it writes are its own markers (only reader and writer: `delivery_service.py`; builder proves it). The table stays in this change (money table; dropping it is not worth the review). |
| `app/services/raw_download_service.py` and the two raw-download routes in `orders.py` (~455-480 download-token, ~525-540 redirect) | Issues tokens for a download from the seller's legacy install ("presents to the seller's VZ"). Gateway orders use the gateway permission routes. |
| AIM Data-only serial routes: `/serials/{serial}/s3-connections/*` (`router.py` 178 include; `external-id`, `verify`, `list-objects`, `presign-object`), the device-S3 delivery branch in `order_service.py` (`_validate_device_s3_record` and the `s3_presigned_url` `delivery_config` handling, ~1684-1810) and `s3_fulfillment.py` symbols reachable only from them | Called only by AIM Data (client path inventory, §9). `s3_fulfillment.py` stays if `s3_qa_sampler.py` 17 or `scoring_service.py` 32 still need it; the builder's script decides and reports. |
| AIM Data-only publish routes in `app/routers/vz_publish.py`: `POST /vz/register` (55), `POST /vz/versions/{version_id}/confirm` (188), `POST /vz/rotate-key` (210), `DELETE /vz/install/{install_id}` (232); the local sample upload and member routes `/vz/versions/{id}/members` and `/vz/versions/{id}/samples/{member}` in `vz_samples.py` | Called only by AIM Data. `POST /vz/publish` is vectorAIz's and stays, though it refuses today (§2). |
| The S1737 storage deletion, if not built first: everything in `specs/P2P-STORAGE-DELETION-S1737.md` §Remove (manifest runtime, delivery staging task, the six delivery tables, shared manifest columns, AIM relay) | Those modules hang off the legacy listener removed here. Folded into this release: no build or BQ for S1737 exists, and Mars (peer 6463) does not hold it and has no objection. S1737's Remove, Keep, One release and acceptance text apply unchanged as part of this spec; the reviewers read it at `specs/P2P-STORAGE-DELETION-S1737.md`. Stay clear of Mars's live paths `app/mcp/connector_auth` and `connector_shared`. |
| Config read only by removed code (generated list is authoritative): at least `FULFILLMENT_STAGING_DIR`, `DEMO_FULFILLMENT` and its production refusal in `config.py`, delivery-token settings used only by `DeliveryService` | Dead with their readers. |
| Tests and scripts that exist only for removed code | Delete, do not rewrite. |

## 5. Keep

- **Gateway delivery** (`aim_gateway*.py`, `gateway_delivery_*`, `order_delivery_states.py`, tasks `aim_gateway_*`), **Seller Workspace delivery** (`seller_workspace_delivery*.py`, `assume_seller_role`), and **public-URL reference listings** (`orders.py` ~708, `source_delivery.py`).
- **vectorAIz:** serial activation and metering (`serials.py` routes other than `s3-connections`, `serial_service.py`, `serial_token_service.py`, `metering_ingestion_service.py`), `POST /api/v1/trust/register`, the channel transport (vectorAIz `v1.20.42` connects to the top-level alias `/ws/trust-channel`, `main.py` 896-898; AIM Data to `/api/v1/trust/stream`; both are the one `trust_websocket` handler, which stays minus its fulfilment handling), `/trust/stream/vc`, the device routes in `trust.py`, non-delivery control-plane actions, `POST /vz/publish`, and the `/api/v1/connect/*` onboarding routes. The `vz_installs` table stays (read by `vz_publish_service.py`); only the AIM Data routes that write it go.
- **Samples:** everything S1737 keeps (seller-chosen public sample, CORE v9.19).
- **Schema:** `pending_fulfillments`, `transactions`, `stripe_webhook_idempotency`, `vz_installs`, `serials`, `serial_usage` stay. This spec drops no table or column of its own; S1737's schema changes (folded in) are the only ones.
- **Runbook data (Max's D1 condition).** No runbook page is deleted by this change. Pages that describe removed behaviour (`trust-channel.md`, `dual-brand-vectoraiz-aim-channel.md`, `vz-release-process.md`, `aim-data.md`, `aim-data-release-process.md`, `aim-data-sign-in-with-ai-market.md`, `publish-paths.md`, `runbooks/data-delivery-p2p.md`, `runbooks/delivery-ack-monitor.md`, and any other page the builder's grep finds) keep their content and gain a short dated status line at the top: what chunk F removed from the backend, that vectorAIz will return in an updated form, and where the removed code lives. The removed code stays recoverable by an annotated git tag `pre-chunk-f-s1756` on the backend base SHA, pushed before merge; each page's status line names that tag. Pages are corrected only where they would otherwise tell an operator something false about production today.
- Out of scope, named so reviewers do not assume them: the AIM Node endpoints (`aim.py`, `aim_discovery.py`, `aim_observability.py`, `aim_seller.py`, `aim_metering.py`) and the data-verification routes AIM Data calls (`/data-verification/*`). Both are candidates for later removal; the verified-label product has no gateway equivalent yet, so that is a product decision, not a deletion.

## 6. Order of operations

1. Max answers D1 and D2. 2. D2 is carried out (listing migrated or unpublished; confirmed by the same read). 3. Full panel on this spec. 4. MP builds; Gate 3 full panel. 5. One deploy: this code removal plus S1737's code and its one migration. 6. After deploy: `/health` green; `GET /api/v1/deliveries/<uuid>`, `GET /orders/<uuid>/download-file` and `POST /api/v1/vz/register` return 404 from outside; a gateway order and a Seller Workspace order still deliver (re-run the S1755 self-test step 8 and the workspace smoke); runbook status lines per §5 (runbook data kept, `data-delivery-p2p.md` table updated to "no path carries delivered bytes" with the old rows kept below as history); `aidotmarket/aim-data` archived with a README pointer to the gateway (Gate 1 §7), after Max's GO.

## 7. Build rules

Report every remaining `git grep` hit in `app` and `scripts` for a removed module, symbol or route and why it stays. Run the full backend suite on disposable PG17 and report exact counts against `main` (known baseline: money suites 51 failures identical to base, S1755). Frontend: no change expected (§2); the builder confirms with a grep of `ai-market-frontend` for every removed path.

**Generated acceptance (S1737 pattern).** The builder's script parses the files and symbols listed in §4 at the base SHA and emits every removed module (dotted path), top-level class and function, route (method and path) and `Settings` field. Pass at the candidate SHA: no import of a removed module; no reference to a removed qualified name; no removed route in `app.routes`; no removed `Settings` field; `request_fulfillment` reaches only the three kept branches (a unit test per branch plus one per refused kind: `ai_queryable` with an install, `file_download` without gateway source, demo seller); `alembic check` clean. The report includes the script and its output; nothing is added to the repo.

## 8. Review questions

1. Is anything in §4 still reached by the gateway, Seller Workspace or public-URL paths?
2. Is anything in §5 kept only by habit, and could go now without touching vectorAIz?
3. Does removing `_create_delivery_for_payment` change any money-state transition for gateway or workspace orders?
4. Does folding S1737 into one release create any ordering hazard (its migration plus this code removal in one deploy)?
5. SIMPLER / BETTER.

## 9. Queries

```sql
set default_transaction_read_only=on;
-- serial attribution
select coalesce(version,'<blank>'), hostname, activation_ip, count(*) from serials
 where status='activated' and last_meter_at > now()-interval '30 days' group by 1,2,3;
-- published listings whose seller has an active legacy install
select l.id, split_part(u.email,'@',2), l.fulfillment_type, l.published_at
  from listings l join users u on u.id=l.seller_id
 where l.status='published' and exists (select 1 from vz_installs i where i.seller_id=u.id and i.is_active);
-- orders by delivery method
select coalesce(delivery_method::text,'?'), count(*) from orders group by 1;
```

Client path inventory: `git grep` of `/api/v1/…` literals in `aidotmarket/aim-data` and `aidotmarket/vectoraiz` `origin/main` `app/`; AIM Data-only: `serials/{serial}/s3-connections/*`, `vz/register`, `vz/versions/*`, `vz/rotate-key`, `vz/install/*`, `trust/stream`, `data-verification/*`, `listings/{id}/at-a-glance*`; both: `serials/{serial}/{activate,meter,refresh,status,account,credits/*}`, `trust/register`, `connect/*`, `vz/publish`.
