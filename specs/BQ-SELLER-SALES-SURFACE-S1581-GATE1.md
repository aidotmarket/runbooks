# BQ-SELLER-SALES-SURFACE-S1581 Gate 1 design specification

**Status:** Gate 1 design authority. Gate 1 review round 1 returned CC APPROVE, GLM APPROVE, and Kimi APPROVE_WITH_MANDATES; this commit folds those mandates.

**Build Queue entity:** `build:bq-seller-sales-surface-s1581`

**Design source:** Living State entity version 9, including `council_phase1`, `council_phase2`, `delivery_method_query_result`, `ground_truth_gt2_detail_page`, `ground_truth_gt3_backend_authorization`, `folded_defect`, and `gate4_constraint`, read on 20 August 2026.

**Code baselines:**

- `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569`
- `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b`

## 1. Problem

An active seller has no web surface that shows the orders they must fulfil. The seller navigation currently labels `/dashboard/orders` as `Orders`, but that page calls `getMyOrders()` and presents the buyer's purchases. The same account can buy and sell, so the overloaded word `Orders` hides which side of the transaction the page represents.

The evidence at the pinned frontend SHA is:

- Active and provisioning sellers currently receive an `Orders` navigation entry targeting `/dashboard/orders`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/layout.tsx:87-107`.
- `/dashboard/orders` calls `getMyOrders()` and displays the heading `My Orders`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:71-101` and `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:136-170`.
- `getMyOrders()` calls `/orders/mine` without a role parameter: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:api/orders.ts:4-6`. The backend defaults that request to `role="buyer"`: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/orders.py:117-141`.
- The frontend already declares `getSellerOrders()` on `/seller/orders`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:api/seller.ts:3-5`. A source search at this SHA finds no call site other than that declaration, and there is no `app/dashboard/sales/page.tsx`.
- The backend seller list exists, is restricted to the active seller capability, and returns seller-specific order facts: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:261-326`.

This is an information architecture defect, not a missing write capability. The first build must make sales visible without adding a human delivery path.

## 2. Operational ground truth and product posture

The Living State production query from S1582 found zero rows in `orders`, with zero orders in every status, alongside 33 listings and 72 users. There is therefore no observed automated Trust Channel delivery path and no observed manual delivery path. Both are intended-only. There is also no paid-to-delivered latency distribution from which to derive an escalation threshold.

The read-only first slice is safe because there is currently no fulfilment volume to mishandle. This fact does not prove automation works. Automation remains the design centre, but it is unproven intent rather than observed behaviour. The human seller is an observer first and an exception handler second. Copy must describe state, not instruct a seller to upload data or mark an order delivered.

## 3. Binding design

1. Add `/dashboard/sales`, backed by the existing `GET /seller/orders`. The page is read-only.
2. Retire the bare label `Orders` from dashboard navigation. Directional labels are `Sales` and `Purchases`.
3. Add `Sales` and `Purchases` to the active seller navigation in the same change. Repointing the current seller entry to Sales without adding Purchases would remove the seller's stable navigation path to their own purchases and regress the behaviour shipped in frontend commit `5ccff46016e3b4fda3b4b21f6ddfe6ea2b0230ce`.
4. Keep the buyer purchase URL `/dashboard/orders`. Change its navigation label and page heading only. A future `/dashboard/purchases` URL is optional and is not part of this build.
5. Do not add upload, manual delivery, `Mark Delivered`, or any other mutation control to Sales.
6. Sales rows must not link to `/dashboard/orders/[id]`. Keep the required facts inline. A dedicated `/dashboard/sales/[id]` is deferred.
7. Treat `needs_action` as informational only. It is exactly an alias for `status == "pending_delivery"`, not an escalation decision: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:310-323`. Render `Awaiting delivery`, `paid_at`, and the age of `paid_at`, with no action prompt and no client-side staleness threshold.
8. Give Sales its own status type and display dictionary. Do not import or extend the buyer `OrderStatus`, whose values and labels are different: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:types/index.ts:365-394` and `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:11-25`.
9. Fold the seller overview statistics contract correction into this build.
10. Do not expose a live Sales navigation entry to a provisioning seller. Omit it until the seller capability becomes active. This matches the active-only API gate and avoids advertising a destination that cannot load.

## 4. Durable order-detail admissibility rule

A shared order detail route is admissible only when its framing, every data fetch, and every mutation are gated on the viewer's relationship to that specific order, meaning buyer-of-record or seller-of-record. A global account role is never sufficient.

The current purchase detail route is blocked for Sales for two independent reasons.

All three Phase 2 reviewers named linking Sales rows to the current `/dashboard/orders/[id]` route as their single formal dissent point. It is therefore a blocked design, not a builder option.

First, it is a buyer presentation. The frontend client types `GET /orders/{id}` as `BuyerOrderDetail`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:api/orders.ts:9-11`. The page stores that type, requests buyer download access automatically for fulfilled orders, and does not gate that download request on the viewer's relationship to the order: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/[id]/page.tsx:57-141`. It labels the counterparty as `Seller`, the money as `Amount Paid`, and the date as `Purchase Date`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/[id]/page.tsx:298-325`. The backend's safe detail response also deliberately omits seller proceeds: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/schemas/order.py:226-255`. The correct slice-one seller source is `GET /seller/orders`.

The Council's structural rationale also described `GET /orders/{id}` as buyer-scoped and said a seller-of-record could receive 403 or 404. That part does not hold at the pinned backend SHA. The endpoint returns `OrderSafeResponse` and permits either the buyer-of-record or seller-of-record: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/orders.py:206-227`. This correction does not change the blocked design. The frontend route remains buyer-framed, starts buyer download work, and lacks seller proceeds.

Second, the current detail page renders the wrong party's action controls. `Confirm Receipt` has no role check, while `Mark Delivered` is gated only on the user's global seller role: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/[id]/page.tsx:370-388`. The backend rejects a deliver attempt from anyone other than the seller-of-record and rejects confirmation by anyone other than the buyer-of-record, so this is a false-affordance and trust defect rather than a demonstrated privilege escalation: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/transaction_actions.py:57-77` and `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/transaction_actions.py:80-103`. That defect is tracked as `T-2026-000688` and is not fixed by this build.

## 5. Scope

In scope:

- Active-seller Sales navigation and the new read-only `/dashboard/sales` list.
- Active-seller Purchases navigation at the existing `/dashboard/orders` URL.
- Buyer navigation label `Purchases` at the unchanged `/dashboard/orders` URL.
- The `/dashboard/orders` page heading change to `Purchases`.
- The two post-checkout links labelled `Check My Orders` change to `Check My Purchases`; their `/dashboard/orders` targets stay unchanged.
- Any dashboard back-link whose visible label is the bare word `Orders` changes to `Purchases`; its target stays unchanged.
- Seller-specific list fields, status dictionary, filters, sort, and page states defined below.
- Omission of Sales navigation for provisioning sellers, plus safe handling of direct visits without calling the active-only endpoint.
- Seller overview statistics field correction and its test correction.
- An active-seller Overview pointer using the corrected `pending_fulfillments` field and linking to the default Sales view.

## 6. Explicit non-scope

- A `/dashboard/sales/[id]` detail route.
- Reuse of or links to `/dashboard/orders/[id]` from Sales.
- Manual delivery UI, file upload, delivery proof entry, or `Mark Delivered`.
- Notifications, email, realtime updates, or stale-order alerts.
- A `/dashboard/purchases` URL or migration of inbound links.
- The buyer/seller action and framing corrections tracked by `T-2026-000688`.
- Refund, cancellation, dispute, redelivery, messaging, payout management, export, or bulk actions.
- A frontend escalation threshold or a change to backend `needs_action` semantics.
- Claims that Trust Channel delivery or manual delivery is live.

## 7. Navigation, access, headings, and copy

### 7.1 Active seller navigation

Use these exact strings, targets, and order:

| Position | String | Target |
| --- | --- | --- |
| 1 | `Overview` | `/dashboard` |
| 2 | `Listings` | `/dashboard/listings` |
| 3 | `Sales` | `/dashboard/sales` |
| 4 | `Purchases` | `/dashboard/orders` |
| 5 | `Inquiries` | `/dashboard/seller/inquiries` |
| 6 | `Settings` | `/dashboard/settings` |

The existing conditional `Blog Admin` entry for `max@ai.market` is unaffected and remains appended after these six role-navigation entries.

The page heading at `/dashboard/sales` is exactly `Sales`.

### 7.2 Provisioning seller behaviour

Omit `Sales` from provisioning-seller navigation. Keep `Overview`, `Listings`, `Purchases`, `Inquiries`, and `Settings` in their existing order, with `Purchases` at `/dashboard/orders`.

A direct visit by a provisioning seller to `/dashboard/sales` must not call `GET /seller/orders`. It renders the heading `Sales` and the exact explanatory text `Sales unlock after seller setup is complete.` A buyer-only or other non-seller direct visit is redirected to `/dashboard/inquiries` by the existing dashboard access policy and must not call the endpoint.

This choice follows the verified capability difference: seller stats permit provisioning access, but seller orders require active access: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:82-100` and `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:261-274`.

### 7.3 Buyer navigation

Keep every buyer target and every other buyer string unchanged. The resulting exact navigation is:

| Position | String | Target |
| --- | --- | --- |
| 1 | `Overview` | `/dashboard` |
| 2 | `My Inquiries` | `/dashboard/inquiries` |
| 3 | `Purchases` | `/dashboard/orders` |
| 4 | `My Requests` | `/dashboard/requests` |

The page heading at `/dashboard/orders` is exactly `Purchases`. In the empty state, replace the current `No orders yet` h1 with `Purchases` and render `No orders yet` as the empty-state subheading beneath it, keeping the directional page language consistent. Its URL and buyer data source remain unchanged. Any `Back to Orders` navigation label on the buyer detail route becomes `Back to Purchases`, with the target still `/dashboard/orders`. No action, fetch, authorization, or other detail-page behaviour changes under this specification.

## 8. `GET /seller/orders` contract and list presentation

### 8.1 Verified request contract

`GET /seller/orders` accepts:

| Parameter | Current contract |
| --- | --- |
| `status_filter` | Optional string. The endpoint documentation names `pending_delivery`, `delivered`, and `completed`. |
| `limit` | Integer, default 50, maximum 100. |
| `offset` | Integer, default 0, minimum 0. |

It requires the active seller capability and currently orders results by `created_at DESC`: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:261-295`. Extend the existing `getSellerOrders()` client signature to accept and pass `status_filter`, `limit`, and `offset` as query parameters.

### 8.2 Verified response contract

The response is a JSON array. The endpoint currently has no declared response model. Each item contains exactly these emitted fields: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:295-326`.

| Field | Wire shape | Slice-one use |
| --- | --- | --- |
| `id` | UUID serialized as string | Stable row key only. Do not link it to purchase detail. |
| `order_number` | String | Render as `Sale`. This is the seller-visible reference. |
| `listing_id` | UUID serialized as string | Retain in the typed object; do not make the title a new navigation path in this slice. |
| `listing_title` | String, with backend fallback `Unknown` | Render as `Listing`. |
| `buyer_email` | String | Render as `Buyer`. Do not add a contact action. |
| `amount_cents` | Integer cents | Render as `Gross (USD)`. |
| `seller_amount_cents` | Integer cents | Render as `You receive (USD)`. |
| `status` | String order status | Render only through the seller status dictionary in section 9. |
| `needs_action` | Boolean | Retain as informational data only. Do not use for copy, badges, sorting, colour, or prompts. |
| `created_at` | ISO 8601 string or null | Render as the fallback date when `paid_at` is null. |
| `paid_at` | ISO 8601 string or null | Render the absolute paid time and relative age. |
| `delivered_at` | ISO 8601 string or null | Render inline beneath a Delivered state when present. |
| `completed_at` | ISO 8601 string or null | Render inline beneath a Completed state when present. |

The list must define its own typed `SellerOrder` contract rather than reuse `BuyerOrder` or `BuyerOrderDetail`.

The page renders seven visible columns on desktop: `Sale`, `Listing`, `Buyer`, `Gross (USD)`, `You receive (USD)`, `Status`, and `Paid`. The mobile card renders the same facts. `Paid` uses the existing absolute date formatter and adds a neutral relative age, for example `Aug 20, 2026 (3 hours ago)`. Age changes only the text. It does not change colour, position, status, or add an action. If `paid_at` is null, render `Not paid` and show `created_at` as `Created <absolute date>`.

The seller list omits `currency`, even though the order model defaults currency to USD: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/models/order.py:130-137`. Slice one makes the limitation explicit by labelling both amount columns `(USD)`. Adding per-order currency to the seller list is deferred and becomes mandatory before non-USD orders are admitted. Do not make a buyer-detail call to discover currency.

Other detail facts identified by Council are not present in this list response: the full purchased listing snapshot or version, `platform_fee_cents`, `delivery_method`, `auto_confirm_at`, payout or transfer state, delivery proof, and order event history. They are deferred with `/dashboard/sales/[id]`. Slice one makes no second call and must not imply that these fields are present. Gross, seller net, buyer, state, and the available timestamps are the complete slice-one must-see set.

### 8.3 Default filter and sort

The default filter is `Awaiting delivery`, implemented as `status_filter=pending_delivery`. `All`, `Delivered`, and `Completed` are the other first-slice filter choices. The filter's visible labels use the seller dictionary, never raw status codes.

Within `Awaiting delivery`, sort the returned rows by `paid_at` ascending, then `created_at` ascending, then `order_number` ascending. This keeps the longest-waiting paid sale visible without declaring it stale or urgent. For `All`, `Delivered`, and `Completed`, sort by `paid_at` descending, then `created_at` descending, then `order_number` ascending. Client sorting is required because the endpoint exposes no sort parameter.

The UI requests `limit=100` and `offset=0`. More than 100 matching sales is a change trigger for server-side pagination and sort, not a reason to invent an incomplete client pagination contract in slice one. Production currently has zero orders.

### 8.4 Page states and exact copy

The `Sales` heading remains visible in every state.

| State | Exact copy and behaviour |
| --- | --- |
| Loading | `Loading sales...` No stale rows remain visible. |
| Default-filter empty | Heading `No sales awaiting delivery`; body `Paid sales awaiting delivery will appear here.` The `All` filter remains available. |
| All-filter empty | Heading `No sales yet`; body `Sales will appear here after a buyer completes payment.` |
| Other-filter empty | Heading `No sales match this filter`; body `Choose another status to view your sales.` |
| Error | Heading `Sales are unavailable`; body `We couldn't load your sales. Try again.` Show a `Try again` button that repeats the same read request. Do not redirect to Purchases and do not show mutation guidance. |

## 9. Seller status dictionary

The backend order state machine defines these values: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/models/order.py:33-45`. The Sales surface must exhaustively map all of them:

| Backend status | Exact seller display |
| --- | --- |
| `created` | `Order created` |
| `paid` | `Paid` |
| `in_escrow` | `Payment held` |
| `pending_delivery` | `Awaiting delivery` |
| `delivered` | `Delivered` |
| `completed` | `Completed` |
| `disputed` | `Disputed` |
| `resolved` | `Dispute resolved` |
| `delivery_failed` | `Delivery failed` |
| `refunded` | `Refunded` |
| `cancelled` | `Cancelled` |

An unknown runtime value renders `Status unavailable` and calls `console.error('Unknown seller order status:', status)` exactly once. It must never expose a raw code or fall back to the buyer status dictionary. Do not add a telemetry dependency or a new module. `Awaiting delivery` is neutral status copy. There is no `Needs action`, `Upload`, `Deliver now`, or `Mark delivered` copy.

## 10. Folded seller overview statistics defect

The seller Overview cards currently read `stats.views`, `stats.sales`, and `stats.revenue`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.tsx:481-543`. `GET /seller/stats` returns `total_views`, `total_sales`, `period_revenue_cents`, `period_revenue_display`, and the rest of its real response shape: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:172-183`. The current Vitest mock repeats the nonexistent frontend fields and therefore masks the defect: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.test.tsx:122-149` and `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.test.tsx:259-290`.

The backend response does not change. The frontend must:

1. Define and use a `SellerStats` response type with `period`, `total_listings`, `total_views`, `total_inquiries`, `total_sales`, `period_sales`, `period_revenue_cents`, `period_revenue_display`, `pending_fulfillments`, and `conversion_rate`.
2. Change the card reads from `views` to `total_views`, from `sales` to `total_sales`, and from `revenue` to `period_revenue_display`. Render `period_revenue_display` verbatim; do not prefix a currency symbol and do not call `.toFixed`.
3. Change the third card label from `Total Revenue` to `Revenue (30 days)` while the request uses the endpoint's default `period=30d`. The response's period revenue must not be presented as all-time revenue.
4. Correct the Vitest mocks to use the real backend shape. The active-seller test uses nonzero values including `total_views: 12`, `total_sales: 3`, `period_revenue_cents: 4550`, and `period_revenue_display: "$45.50"`, then asserts that `12`, `3`, and `$45.50` render.
5. Preserve the test that a purchases failure does not erase active-seller dashboard content, but give its seller stats mock the same real response shape.

The active-seller Overview must add a neutral pointer labelled exactly `Sales awaiting delivery`. Its value is `pending_fulfillments`, and the whole pointer links to `/dashboard/sales?status=pending_delivery`. It renders `0` when the backend returns zero. It must not say `needs action`, change colour based on age, or use `needs_action`.

## 11. Acceptance criteria

Each criterion is independently checkable.

1. An active seller sees the exact six navigation entries and targets in section 7.1, in that order.
2. A provisioning seller does not see `Sales` in navigation. A direct visit to `/dashboard/sales` renders `Sales unlock after seller setup is complete.` and makes zero requests to `/seller/orders`.
3. A buyer sees the exact four navigation entries and targets in section 7.3. `/dashboard/orders` remains the Purchases target.
4. The visible heading on `/dashboard/sales` is `Sales`; in both empty and non-empty fixtures, the visible page heading on `/dashboard/orders` is `Purchases`.
5. No dashboard navigation or back-navigation link uses the bare label `Orders`. Existing `/dashboard/orders` and `/dashboard/orders/[id]` URLs remain valid.
6. The active-seller Sales page calls `GET /seller/orders` with the selected status filter, `limit=100`, and `offset=0`. No Sales code calls `/orders/mine`, `/orders/{id}`, `/seller/pending`, or a transaction endpoint.
7. A fixture containing one pending sale and one personal purchase renders the sale under Sales and the purchase under Purchases. Neither appears in the other list.
8. A Sales row and mobile card render the seven visible facts in section 8.2. The row and card contain no link to `/dashboard/orders/[id]` and no seller detail link.
9. `needs_action=true` changes no copy, colour, order, button, link, or prompt. `pending_delivery` renders `Awaiting delivery`, with absolute `paid_at` and relative age.
10. The default filter and stable sort match section 8.3. A test with three pending fixtures proves oldest `paid_at` first and deterministic tie-breaking.
11. Unit fixtures cover every status in section 9 and prove the seller dictionary is independent of the buyer `OrderStatus` and buyer labels. An unknown-status fixture renders `Status unavailable`, never the raw code, and proves `console.error` is called exactly once as `console.error('Unknown seller order status:', status)`.
12. Sales imports no delivery, upload, refund, dispute, transaction, or other mutation client. There is no `Mark Delivered` control.
13. Loading, each empty case, error, retry, and provisioning copy match section 8.4 and section 7.2 exactly.
14. The seller stats client or consumer is typed to the real response. Tests mock the complete real shape and prove nonzero `total_views`, `total_sales`, and `period_revenue_display` values render.
15. The active-seller Overview renders `Sales awaiting delivery` from `pending_fulfillments` and links it to `/dashboard/sales?status=pending_delivery`. A nonzero contract-shaped mock proves the displayed count is nonzero.
16. The existing seller-purchases behaviour from frontend commit `5ccff46016e3b4fda3b4b21f6ddfe6ea2b0230ce` remains covered: an active seller's personal purchase summary and Purchases navigation still reach `/dashboard/orders`.
17. The `T-2026-000688` action behaviour is unchanged. Any edit to the buyer detail page is limited to replacing visible `Orders` back-navigation copy with `Purchases`.
18. Frontend type-checking, linting, the focused dashboard/Sales Vitest suite, and the existing purchase tests pass.
19. Gate 4 finds the exact literal `Sales will appear here after a buyer completes payment.` in the live ai.market frontend bundle, using the method in section 12.

## 12. Gate 4 verification

Cloudflare Pages provides no reliable deployed-SHA source for this frontend. Git state, a successful build, or a branch deployment is not production proof.

The build must introduce this exact ASCII string as the All-filter empty-state body:

```text
Sales will appear here after a buyer completes payment.
```

Gate 4 must run from outside the deployment environment. The verifier signs in through the normal production sign-in flow with an active-seller account, then loads `https://ai.market/dashboard/sales` in the same authenticated browser session and collects the same-origin JavaScript asset URLs returned by the page and its Next.js build manifest. Fetch those assets from `https://ai.market`, decompress them, and search their bytes for the exact string. Record the live URL, UTC verification time, HTTP statuses, matched asset URL, matching literal, and the Next.js `buildId` from the `/_next/static/<buildId>/_buildManifest.js` URL. Gate 4 passes only when the string is present in a live production asset. Local output, preview assets, source maps, GitHub, and Cloudflare build status are insufficient.

## 13. Risks and falsifiers

| Decision at risk | Risk | Evidence that falsifies the decision |
| --- | --- | --- |
| Read-only first slice | Human sellers may actually be the normal delivery actor, making observation without action insufficient. | A nonempty production cohort in which manual delivery methods dominate, ordinary sellers call a deliver endpoint, pending orders are blocked for lack of a browser delivery path, or the Trust Channel listener proves unwired. Any of these triggers a separately designed manual-delivery slice. |
| Neutral `Awaiting delivery` | Some pending orders may eventually need an explicit escalation. | A nonempty per-delivery-method distribution of `paid_at` to automated `delivered_at`, plus stuck terminal outcomes, supports a calibrated backend threshold. A server-defined `needs_action` based on that evidence may then drive prominence. |
| No seller detail route | Inline fields may become insufficient as disputes, delivery proof, payout state, or support needs appear. | Seller research or support evidence shows repeated need for facts absent from the list, or a relation-aware seller detail contract is built and passes dual-role tests for every fetch and mutation. That permits `/dashboard/sales/[id]`; it does not permit an uncorrected purchase detail link. |
| Existing seller list contract is enough | The untyped endpoint may drift or omit a fact required for correct display. | A contract test or live authenticated response differs from section 8.2, a non-USD order appears, or more than 100 matching sales makes client sorting incomplete. Add a backend response model, currency, and server pagination/sort before widening the surface. |
| Omit Sales while provisioning | Provisioning sellers cannot use the active-only endpoint today. | The backend capability gate is intentionally changed to provisioning and product evidence shows useful safe seller-order data exists before activation. Only then may navigation expose Sales earlier. |
| Bundle-string Gate 4 proof | A deployment can succeed without serving the intended new route bundle. | The exact unique string is absent from every live production asset. That falsifies deployment of this change even when Cloudflare reports success. |

## 14. Author's reservations

I have no reservation about the binding route, navigation, read-only scope, status, or admissibility decisions. I reserve only on one supporting statement as originally written: at the pinned backend SHA, `GET /orders/{id}` is not buyer-only and does not reject the seller-of-record. Section 4 records the verified contract instead of repeating that claim. The blocked-detail conclusion remains supported by the buyer-typed and buyer-framed frontend, automatic buyer download request, omission of seller proceeds, and wrong-party action affordances.
