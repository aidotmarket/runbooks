# Seller-route interoperability: AIM Data device route (Mars) × Seller Workspace cloud route (Vulcan)

Status: DRAFT for joint sign-off (Max, 2026-09-11: "compare both interfaces' account permissions, listing/version records, publication rules and buyer download rights; verify that a listing created through either route behaves correctly in the shared marketplace; record the result with Mars and fix only demonstrated differences"). Source identity: backend `be28ae3e382bcbb07a62594037e0595d8f189238`, frontend `943429b586fa4acd55f81f23ded5005cbcf841e1`, AIM Data `51e2740f6972c008626e186d8b265601c58eca32`. Every cell is a source reading by Mars; Vulcan corrects any cell that is wrong, then both sign §5.

## 1. Comparison (read from source)

| Dimension | AIM Data device route | Seller Workspace cloud route | Same? |
| --- | --- | --- | --- |
| Seller identity to the platform | A registered device with a `VZ-…` serial and install token; publish authority = `_validate_s3_connection_publish_authority` (serial ↔ install ↔ seller `user_id`, `vz_publish_service.py:698–710`) | The seller's own session (JWT) on `/seller-workspace/*`; connections owned by `owner user_id`; per-connection random ExternalId | No (by design) — both resolve to the same `users.id` |
| Data location | Seller's device or seller's S3 (STS assume-role with `derive_external_id(serial)`) | Seller's AWS S3 or Cloudflare R2 (STS assume-role / R2 token, per-connection ExternalId) | Same non-custodial posture; different credential identity |
| Listing record | `listings` row: `fulfillment_type = 'ai_queryable'` (or reference), `source_dataset_id = <AIM dataset id>`, `raw_metadata.s3_connection {bucket, region, role_arn, serial_id, prefix}` (`vz_publish_service.py:944–966`), `source_delivery` device binding | `listings` row: `fulfillment_type = 'file_download'`, `listing_type = 'raw'`, `source_delivery = {authority_kind: 'workspace_connection', …}` (`seller_listing_publication.py:126–131`), no `source_dataset_id`, no `raw_metadata.s3_connection` | Same table, disjoint markers |
| Version record | `listing_versions` row per signed publish: `prefix`, `object_count == 1`, `status active` via `vz_publish` (`:882–910`) | `listing_versions` row: `prefix = 'workspace/<approval>/'`, `status active`, `published_at` (`seller_listing_publication.py:133`) | Same table; Workspace prefix convention differs; single-object invariant not asserted for Workspace |
| Publication rule | Device-signed publish; verified label only after a paid verification through the device scanner (S1590/S1681) | Approval-gated publication from the Workspace; verified label not reachable (no device; W3 profiling is bounded ranges, not the signed scan) | Different — verified label gap on Workspace (open synergy question, `money-path-proof-loop.md` §E) |
| Marketplace visibility | Ordinary listing; search/marketplace code has no route-specific filter found (`search_service.py`, `marketplace.py`: no `workspace`/`ai_queryable` branching) | Same | Same |
| Purchase | `POST /checkout/create` → hosted Stripe Checkout; order/transaction created; `payment_intent_data.metadata {order_id, order_number}` (live PI also carries `transaction_id`) | Same endpoint; the mock-webhook and zero-amount branches call `fulfill_workspace_purchase` inline (`checkout.py:249–251, 285–288`) | Same entry; Workspace has inline fulfilment on the synthetic/zero-amount branches, device route does not |
| Fulfilment after payment | `FulfillmentService` Trust-Channel path: `vai.fulfillment.deliver` → device response → `handle_fulfillment_response` (S1681 G3) | `FulfillmentService` branches first on `is_workspace_source(order.source_delivery)` (`fulfillment_service.py:177–178`) → `seller_workspace_delivery` | One dispatcher, two branches |
| Buyer download | `POST /orders/{id}/download` (+ `redeem`, `refresh`, legacy variants) — session or API key | `POST /seller-workspace/orders/{id}/prepare` → `download` → per-file grant — session only (`seller_workspace_delivery.py:20–23`) | Different (Max decision 8510ec8c: unify; `build:bq-buyer-download-unification-s1711`) |
| Web order page | Device-delivered redeem NOT wired (`app/dashboard/orders/[id]/page.tsx`) | `order.workspace_delivery` branch wired | Gap on the device route |
| Agent API | `agent/router.py:899` builds a legacy gatekeeper URL | Not reachable | Gap on both |
| Refund / revocation | `charge.refunded` → `_handle_refund` marks order refunded/revoked (human path leaves `transactions.status`), suppressed for synthetic scope (`webhooks.py:551–563`) | Same webhook path; Workspace grants are revoked by order `revoked` flag? (vulcan to confirm) | Vulcan to confirm |
| Settlement | Transfer after the hold via the settlement scheduler (S1681 §F) | Same scheduler? (vulcan to confirm the Workspace order sets `seller_amount_cents`/`transfer_group` identically) | Vulcan to confirm |

## 2. Demonstrated differences (fix only these, each as its own item)

1. Buyer download: two routes, two auth rules, two UIs — decided (unify; `bq-buyer-download-unification-s1711`).
2. Web order page cannot download a device-delivered order; agent API builds a legacy URL — folded into (1).
3. Verified label unreachable for Workspace listings — design question, not a defect; owner: joint, after (1).
4. Single-object invariant (`object_count == 1`, G3.4) is asserted on the device route and not on Workspace versions — vulcan to confirm whether Workspace versions are multi-object by design (they are: multi-file grants), in which case the shared `listing_versions.object_count` semantics need one sentence in the listing spec.

## 3. Not differences (confirmed same)

Same `users`, `listings`, `listing_versions`, `orders`, `transactions` tables; same checkout entry point and Stripe account; same `FulfillmentService` dispatcher; same marketplace search surface; same synthetic-exclusion policy for webhooks.

## 4. Verification of "a listing created through either route behaves correctly in the shared marketplace"

Evidence already in hand: device route — S1656/S1681 clean-seed runs 8–12 (publish, verify, purchase, Trust-Channel delivery at be28ae3e); Workspace route — Vulcan's 98 focused integration tests (vulcan to name the module and SHA). Missing and required for sign-off, one run each, at the same backend `be28ae3e`:

- W→shared: a Workspace-published listing is (a) returned by the public marketplace search alongside a device-route listing, (b) purchasable by buyer-01 through the shared `/checkout/create` hosted path (not the mock branch), (c) delivered through `FulfillmentService` → workspace branch, (d) downloadable by the buyer's session, (e) refused to the buyer's API key (until unification), (f) refund via `charge.refunded` revokes the Workspace grant.
- D→shared: the same six for a device-route listing (a–d and f are already covered by runs 8–12 and G15; (e) API key download works).
- Cross: seller-01 owning one listing of each kind; the seller dashboard lists both; the settlement scheduler treats both orders identically (vulcan: which environment runs this).

## 5. Sign-off

- Mars: the table above is what I read at be28ae3e; I sign §3 and differences 1–3. Pending Vulcan's corrections and the W→shared run.
- Vulcan: (to complete) corrections to §1, confirmation of the refund/settlement cells, the test module identity for the 98 tests, and the W→shared run evidence.
