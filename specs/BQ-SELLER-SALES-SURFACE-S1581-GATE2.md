# BQ-SELLER-SALES-SURFACE-S1581 Gate 2 implementation specification

**Status:** Gate 2 implementation specification, authored pending review.

**Gate 2 review record:** Round 1 returned CC `REQUEST_CHANGES`, GLM `APPROVE_WITH_MANDATES`, and Kimi `APPROVE_WITH_MANDATES`. This round-2 fold commit folds those findings without changing the Gate 1 decisions or the thirteen-file implementation manifest.

**Build Queue entity:** `build:bq-seller-sales-surface-s1581`

**Binding design authority:** `runbooks@73752294af7dd58870ae3028814f8931de4b6b25:specs/BQ-SELLER-SALES-SURFACE-S1581-GATE1.md:1`. Gate 1 is closed. This document implements it without changing its decisions.

**Implementation baseline:** `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569`

**Contract-check baseline:** `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b`

## 1. Implementation boundary

The implementation changes `ai-market-frontend` only. It adds the read-only Sales list, separates Sales and Purchases navigation, corrects the seller overview statistics consumer, and adds or updates the tests named below.

No backend change is needed or permitted by this specification. The pinned backend already provides:

- `GET /auth/capabilities`, returning the effective seller capability used to guard the page: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/auth.py:371-376`.
- `GET /seller/stats`, with provisioning access and all fields required by the corrected overview contract: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:82-183`.
- `GET /seller/orders`, with active-seller access, `status_filter`, `limit`, `offset`, seller ownership, the required response fields, and no mutation: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/seller.py:261-326`.
- `GET /orders/mine`, whose default role is buyer and which remains the Purchases data source: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/endpoints/orders.py:117-183`.
- Every seller status required by Gate 1: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/models/order.py:33-45`.

The seller router is already included in the shipped API router: `ai-market-backend@a47354a5cc109e162b8d7dddb9b9f8bb41284a1b:app/api/v1/router.py:328-330`.

## 2. File manifest

The build diff is limited to the following files. Nothing outside this manifest may change.

### 2.1 New files

| File | Required change |
| --- | --- |
| `app/dashboard/sales/page.tsx` | Add the capability-gated, read-only Sales page, local filters, deterministic sort, desktop table, mobile cards, seller status presentation, and all page states. |
| `app/dashboard/sales/page.test.tsx` | Add Sales page tests covering access, requests, sorting, presentation, status handling, page states, retry, and Sales/Purchases separation. |
| `api/seller.test.ts` | Add client tests proving the exact `/seller/orders` query object for filtered and All requests and the typed seller stats request. |

At the baseline, `app/dashboard/sales/page.tsx`, its test, and `api/seller.test.ts` do not exist.

### 2.2 Edited files

| File | Required change |
| --- | --- |
| `types/index.ts` | Add `SellerOrderStatus` and replace the stale `SellerOrder` and `SellerStats` contracts in place inside the existing seller-types section, without changing `SellerFinancials` or buyer order types. |
| `api/seller.ts` | Type `getSellerStats()` and extend `getSellerOrders()` to accept and pass `status_filter`, `limit`, and `offset`. |
| `app/dashboard/layout.tsx` | Render the exact active-seller, provisioning-seller, and buyer navigation, and retain the existing buyer-only route redirect policy. |
| `app/dashboard/layout.test.tsx` | Add exact navigation order/target tests and buyer/provisioning Sales access tests. |
| `app/dashboard/page.tsx` | Consume the real seller stats fields and add the linked `Sales awaiting delivery` overview card. |
| `app/dashboard/page.test.tsx` | Replace incorrect seller stats mocks with the complete real shape and assert the corrected values, label, pointer, and retained seller Purchases behavior. |
| `app/dashboard/orders/page.tsx` | Change the buyer list heading to `Purchases` in non-empty and empty states while retaining `No orders yet` as the empty subheading. |
| `app/dashboard/orders/page.test.tsx` | Cover the `Purchases` heading in empty and non-empty fixtures and retain the existing buyer data-source assertion. |
| `app/dashboard/orders/[id]/page.tsx` | Change only the visible back-link copy from `Back to Orders` to `Back to Purchases`. |
| `app/checkout/success/CheckoutSuccessContent.tsx` | Change both `Check My Orders` links to `Check My Purchases`; retain their `/dashboard/orders` targets. |

## 3. Verified current frontend

The manifest above follows the current tree at the pinned frontend SHA:

- The seller client has untyped one-line stats and orders calls, and `getSellerOrders()` accepts no arguments: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:api/seller.ts:1-5`.
- The existing seller dashboard section contains stale, unused `SellerStats` and `SellerOrder` interfaces: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:types/index.ts:228-255`. `SellerStats` has six fields, including backend-absent `published_listings` and `total_revenue`, and lacks the fields required by section 7. `SellerOrder` has seven fields, uses `amount` instead of `amount_cents`, and types `status` as an unrestricted string. Neither interface has an importer anywhere else in the pinned frontend tree; the overview instead types stats as `any`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.tsx:41-48`.
- The separate buyer section contains `OrderStatus`, `BuyerOrder`, and `BuyerOrderDetail` and remains unchanged: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:types/index.ts:365-394`.
- Dashboard access already resolves `CapabilityStatus` and redirects a buyer from a route outside the buyer allowlist to `/dashboard/inquiries`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/layout.tsx:21-69`.
- Seller and buyer navigation currently use `Orders` and `My Orders`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/layout.tsx:87-109`.
- The Purchases page already has local badge helpers, a responsive desktop table, a mobile card layout, the shared spinner, and an empty state: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:11-69` and `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:103-238`.
- The Requests page provides the closest current responsive table/mobile-card structure: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/requests/page.tsx:106-160`.
- The Listings page provides the current dashboard retry panel, empty card, and table shell: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/listings/page.tsx:91-130`.
- The seller Inquiries page provides the current local status dictionary and pill helper shape: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/seller/inquiries/page.tsx:14-29`.
- The overview has an existing card grid but reads nonexistent `views`, `sales`, and `revenue` fields: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.tsx:481-543`.
- The current overview tests repeat the incorrect `{ views, sales, revenue }` stats shape three times: in the active-seller stats fixture, active-seller personal-purchase fixture, and purchase-failure fixture at `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.test.tsx:122-149`, `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.test.tsx:160-176`, and `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.test.tsx:259-290`.
- The current buyer detail back link is the only dashboard back-navigation occurrence of `Back to Orders`: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/[id]/page.tsx:288-303`.
- The checkout timeout and error states contain the two required `Check My Orders` replacements: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/checkout/success/CheckoutSuccessContent.tsx:158-202`.
- `formatPrice()` and `formatDate()` already supply the USD and absolute date formatting used by the dashboard: `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:lib/format.ts:1-14`.

There is no shared dashboard list, table, card, badge, filter, loading, or empty-state component at this SHA. Sales must not create such an abstraction in this slice. It reuses the existing local visual patterns as follows:

| Sales concern | Existing pattern to match |
| --- | --- |
| List and overview card | The purchase summary section and linked rows in `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/page.tsx:242-287`. |
| Desktop table | The responsive table shell and cell spacing in `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:140-200` and `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/requests/page.tsx:106-138`. |
| Mobile card | The responsive card switch in `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:202-237` and `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/requests/page.tsx:140-160`, but use a non-link `<article>` for Sales. |
| Status badge | The local dictionary plus pill helper structure in `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/seller/inquiries/page.tsx:14-29`. |
| Filter | No dashboard filter component exists. Add a local four-button group inside the Sales page and use the existing rounded border/button styling. Do not create a reusable filter component. |
| Loading | The 8-by-8 indigo spinner used in `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/page.tsx:103-108`. Keep the `Sales` heading above it. |
| Empty | The bordered white empty card used in `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/listings/page.tsx:120-127`, with Gate 1 copy. |
| Error and retry | The red bordered retry panel in `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/listings/page.tsx:99-109`, with Gate 1 copy and `Try again`. |

## 4. Shared contracts

### 4.1 `types/index.ts`

Work inside the existing seller dashboard type section at lines 228-255; do not create a second seller section. Add `SellerOrderStatus`, replace the existing `SellerOrder` and `SellerStats` interfaces in place with these definitions in full, drop their stale fields, and leave `SellerFinancials` untouched:

```ts
export type SellerOrderStatus =
  | 'created'
  | 'paid'
  | 'in_escrow'
  | 'pending_delivery'
  | 'delivered'
  | 'completed'
  | 'disputed'
  | 'resolved'
  | 'delivery_failed'
  | 'refunded'
  | 'cancelled';

export interface SellerOrder {
  id: string;
  order_number: string;
  listing_id: string;
  listing_title: string;
  buyer_email: string;
  amount_cents: number;
  seller_amount_cents: number;
  status: SellerOrderStatus;
  needs_action: boolean;
  created_at: string | null;
  paid_at: string | null;
  delivered_at: string | null;
  completed_at: string | null;
}

export interface SellerStats {
  period: string;
  total_listings: number;
  total_views: number;
  total_inquiries: number;
  total_sales: number;
  period_sales: number;
  period_revenue_cents: number;
  period_revenue_display: string;
  pending_fulfillments: number;
  conversion_rate: number;
}
```

Do not change or extend `OrderStatus`, `BuyerOrder`, or `BuyerOrderDetail`. Seller status values are a separate contract.

After the edit, `types/index.ts` must contain exactly one `export interface SellerStats` declaration and exactly one `export interface SellerOrder` declaration.

### 4.2 `api/seller.ts`

Import `SellerOrder` and `SellerStats` from `@/types`. Add this parameter type in `api/seller.ts`:

```ts
export interface SellerOrderListParams {
  status_filter?: 'pending_delivery' | 'delivered' | 'completed';
  limit: number;
  offset: number;
}
```

Keep the existing Axios-response convention in this module. The resulting function boundaries are:

```ts
export const getSellerStats = () => api.get<SellerStats>('/seller/stats');
export const getSellerFinancials = () => api.get('/seller/financials');
export const getSellerOrders = (params: SellerOrderListParams) =>
  api.get<SellerOrder[]>('/seller/orders', { params });
```

For `All`, the caller passes `{ limit: 100, offset: 0 }`; it does not pass `status_filter: undefined`. For the other filters, it passes the exact backend status string with the same limit and offset.

## 5. Sales page implementation

### 5.1 Component and helper boundaries

Create `app/dashboard/sales/page.tsx` as a client module. Keep every Sales-only helper in this file. Do not add another component or utility module.

The file contains these boundaries:

1. `type SalesFilter = 'pending_delivery' | 'all' | 'delivered' | 'completed'`.
2. A `FILTERS` constant in this visible order: `Awaiting delivery`, `All`, `Delivered`, `Completed`.
3. The exhaustive `SELLER_STATUS` dictionary from section 5.2.
4. `isSellerOrderStatus(status: string): status is SellerOrderStatus`, implemented with an own-property check against `SELLER_STATUS`.
5. `getSellerStatusPresentation(status: string)`, returning the dictionary entry or the fixed unknown fallback. It does not log during render.
6. `sortSellerOrders(orders, filter)`, returning a copied and sorted array. It never mutates the API response.
7. `formatRelativeAge(date, now)`, using `Intl.RelativeTimeFormat('en', { numeric: 'always' })`. Use these exact millisecond constants: second `1_000`, minute `60_000`, hour `3_600_000`, day `86_400_000`, week `604_800_000`, month `2_592_000_000` (30 days), and year `31_536_000_000` (365 days). Select the largest whole nonzero unit from years, months, weeks, days, hours, minutes, then seconds. Pass a negative value for past times so the output is such as `3 hours ago`. Tests fix system time.
8. `SalesPageContent`, which reads the optional `status` search parameter, resolves capabilities, fetches data, owns retry/filter state, reports unknown statuses, and renders the page.
9. The default `SalesPage`, which wraps `SalesPageContent` in `Suspense` so `useSearchParams()` does not break a production Next build. Its fallback includes the `Sales` heading and `Loading sales...`.

The accepted `status` search values are `pending_delivery`, `all`, `delivered`, and `completed`. Any missing or other value selects `pending_delivery`. Filter clicks change local state only. They do not add a new URL contract. The overview deep link `/dashboard/sales?status=pending_delivery` therefore selects the default view.

### 5.2 Seller status dictionary

Use this dictionary in full. The label strings are the exact Gate 1 strings. The classes reuse the current dashboard badge palette. `Awaiting delivery` is deliberately neutral.

```ts
type SellerStatusPresentation = { label: string; css: string };

const SELLER_STATUS: Record<SellerOrderStatus, SellerStatusPresentation> = {
  created: { label: 'Order created', css: 'bg-gray-100 text-gray-600' },
  paid: { label: 'Paid', css: 'bg-[#E8EAF6] text-[#303F9F]' },
  in_escrow: { label: 'Payment held', css: 'bg-[#E8EAF6] text-[#303F9F]' },
  pending_delivery: { label: 'Awaiting delivery', css: 'bg-gray-100 text-gray-700' },
  delivered: { label: 'Delivered', css: 'bg-indigo-100 text-indigo-800' },
  completed: { label: 'Completed', css: 'bg-green-100 text-green-800' },
  disputed: { label: 'Disputed', css: 'bg-red-100 text-red-800' },
  resolved: { label: 'Dispute resolved', css: 'bg-gray-100 text-gray-600' },
  delivery_failed: { label: 'Delivery failed', css: 'bg-red-100 text-red-800' },
  refunded: { label: 'Refunded', css: 'bg-gray-100 text-gray-600' },
  cancelled: { label: 'Cancelled', css: 'bg-gray-100 text-gray-600' },
};
```

The runtime fallback is `{ label: 'Status unavailable', css: 'bg-gray-100 text-gray-600' }`. Maintain a component-local `useRef<Set<string>>` of reported unknown values. After rows load, an effect reports each previously unseen unknown value once with exactly:

```ts
console.error('Unknown seller order status:', status);
```

This placement prevents the desktop and mobile render branches, re-renders, and React development checks from logging the same runtime value more than once. Never render the raw value.

### 5.3 Capability and request sequence

On mount and whenever the selected filter changes:

1. Mark the page loading, clear the error, and clear the current rows so stale rows cannot remain visible.
2. Call the existing `getCapabilities()` client.
3. If `capabilities.seller.effective_status === 'provisioning'`, set the provisioning state, stop, and make no `getSellerOrders()` call.
4. If the status is not `active` or `provisioning`, set a blocked state, stop, and make no seller-orders call. This is a required defence-in-depth state: while capabilities are unresolved, the layout's legacy `user.role === 'seller' || user.role === 'admin'` fallback can mount the child before a later `not_requested` or `suspended` resolution triggers the buyer redirect.
5. If the status is `active`, await `getSellerOrders()` with the selected status, `limit: 100`, and `offset: 0`. Omit `status_filter` for `All`.
6. Unwrap the Axios response and store only the current request's `response.data`. Use the existing cancelled-effect pattern so a slow response from a previous filter cannot overwrite a newer selection.
7. On failure, clear rows and render the error state. The `Try again` button repeats steps 1 through 6 with the same selected filter.

This page imports `getCapabilities`, `getSellerOrders`, `formatDate`, `formatPrice`, and the seller types. It does not import `@/api/orders`, `@/api/transactions`, a transaction action, delivery, upload, refund, or dispute client.

### 5.4 Sort

Sort the copied response before rendering:

- For `Awaiting delivery`, compare `paid_at` ascending, then `created_at` ascending, then `order_number` ascending.
- For `All`, `Delivered`, and `Completed`, compare `paid_at` descending, then `created_at` descending, then `order_number` ascending.
- A null date sorts after a non-null date in both directions. If both values are null, continue to the next key.
- Compare dates by parsed epoch milliseconds and order numbers with `localeCompare`.
- Return `0` only after all three keys match. JavaScript's stable sort then preserves API order for an exact tie.

`needs_action` is never read by the comparator or presentation code.

### 5.5 Rendering

The heading `Sales` is an `<h1>` and is the first visible page heading in every state. Empty and error state headings are `<h2>` elements below it.

For an active seller, render the local four-button filter group under the heading. Use `aria-pressed` to identify the selected filter. The selected button uses the existing indigo dashboard treatment; unselected buttons use the existing gray bordered treatment.

When rows exist, render:

- A desktop table inside the existing `hidden md:block overflow-x-auto rounded-lg border border-gray-200` shell.
- Seven headers in this order: `Sale`, `Listing`, `Buyer`, `Gross (USD)`, `You receive (USD)`, `Status`, `Paid`.
- A mobile `md:hidden` list of non-interactive `<article>` cards. Each card uses a `<dl>` and renders the same seven labels and values.
- `order_number` verbatim for `Sale`, `listing_title` for `Listing`, and `buyer_email` for `Buyer`.
- `formatPrice(amount_cents / 100)` and `formatPrice(seller_amount_cents / 100)` under the explicitly USD-labelled columns.
- The seller status pill from section 5.2. If status is `delivered` and `delivered_at` is present, show `formatDate(delivered_at)` on a separate neutral line beneath the badge. If status is `completed` and `completed_at` is present, do the same with `completed_at`. Do not add a label or action to those date lines.
- For a non-null `paid_at`, render `formatDate(paid_at)` followed by the neutral relative age in parentheses, such as `Aug 20, 2026 (3 hours ago)`.
- For null `paid_at`, render `Not paid`. If `created_at` is non-null, add `Created ` followed by `formatDate(created_at)` on the next neutral line.

No value in the table or card is a link. Do not render a row click handler, button, upload control, delivery control, action menu, `href`, or seller detail affordance.

### 5.6 Exact page-state copy

Use these strings exactly:

| State | Heading and body/action |
| --- | --- |
| Provisioning | Page heading `Sales`; body `Sales unlock after seller setup is complete.` |
| Blocked | Page heading `Sales`; body `Sales are unavailable for this account.` No seller-order request is made. |
| Loading | Page heading `Sales`; body `Loading sales...` |
| Default-filter empty | Empty heading `No sales awaiting delivery`; body `Paid sales awaiting delivery will appear here.` |
| All-filter empty | Empty heading `No sales yet`; body `Sales will appear here after a buyer completes payment.` |
| Other-filter empty | Empty heading `No sales match this filter`; body `Choose another status to view your sales.` |
| Error | Error heading `Sales are unavailable`; body `We couldn't load your sales. Try again.`; button `Try again` |

Do not add `Needs action`, `Upload`, `Deliver now`, or `Mark delivered` copy.

## 6. Navigation and Purchases edits

### 6.1 `app/dashboard/layout.tsx`

The existing layout already holds the capability state and route policy. Do not add a provider or context.

Derive `isSellerActive` from `sellerStatus === 'active'` after capabilities resolve. Keep `isSeller` as active or provisioning for the existing seller dashboard framing. Build the navigation arrays as follows.

Active seller, exact order and targets:

| Position | String | Target |
| --- | --- | --- |
| 1 | `Overview` | `/dashboard` |
| 2 | `Listings` | `/dashboard/listings` |
| 3 | `Sales` | `/dashboard/sales` |
| 4 | `Purchases` | `/dashboard/orders` |
| 5 | `Inquiries` | `/dashboard/seller/inquiries` |
| 6 | `Settings` | `/dashboard/settings` |

Provisioning seller, exact order and targets:

| Position | String | Target |
| --- | --- | --- |
| 1 | `Overview` | `/dashboard` |
| 2 | `Listings` | `/dashboard/listings` |
| 3 | `Purchases` | `/dashboard/orders` |
| 4 | `Inquiries` | `/dashboard/seller/inquiries` |
| 5 | `Settings` | `/dashboard/settings` |

Buyer, exact order and targets:

| Position | String | Target |
| --- | --- | --- |
| 1 | `Overview` | `/dashboard` |
| 2 | `My Inquiries` | `/dashboard/inquiries` |
| 3 | `Purchases` | `/dashboard/orders` |
| 4 | `My Requests` | `/dashboard/requests` |

Keep the conditional `Blog Admin` link appended after the role navigation. Keep `/dashboard/orders` and its descendants in buyer purchase context. Keep the buyer allowlist unchanged. `/dashboard/sales` is not added to that allowlist, so a buyer direct visit retains the existing redirect to `/dashboard/inquiries`.

Do not show `Sales` while capabilities are unresolved. This prevents a provisioning seller with a legacy global seller role from seeing an active-only link during capability resolution.

### 6.2 `app/dashboard/orders/page.tsx`

Keep `getMyOrders()`, `getMyTransactions()`, all row data, links, actions, and URLs unchanged.

- In the non-empty branch, replace the page heading `My Orders` with `Purchases`.
- In the empty branch, render page heading `Purchases` as `<h1>`, then render `No orders yet` as the empty-state `<h2>` beneath it. Keep `You haven't purchased any datasets yet.` and `Browse data` unchanged.

### 6.3 `app/dashboard/orders/[id]/page.tsx`

Change only the text node `Back to Orders` to `Back to Purchases`. Keep `href="/dashboard/orders"`. Do not touch imports, effects, requests, action gates, transaction handling, download behavior, or any other copy. The current action boundary that must remain unchanged is at `ai-market-frontend@509ce253e9a2a16ba8584af7f144a85d4c895569:app/dashboard/orders/[id]/page.tsx:370-388`.

### 6.4 `app/checkout/success/CheckoutSuccessContent.tsx`

Change the timeout-state and error-state text nodes from `Check My Orders` to `Check My Purchases`. Keep both targets as `/dashboard/orders`. Do not change polling, timeout, verification, success-state behavior, or `View Order`.

## 7. Seller overview edits

### 7.1 `app/dashboard/page.tsx`

Import `SellerStats` and change `stats` from `any` to `SellerStats | null`. Keep the current fetch orchestration and Axios response handling. Continue assigning `statsRes.data`.

Change only these card reads and the stated label:

| Current | Required |
| --- | --- |
| `stats?.views || 0` | `stats?.total_views ?? 0` |
| `stats?.sales || 0` | `stats?.total_sales ?? 0` |
| `Total Revenue` | `Revenue (30 days)` |
| ``${(stats?.revenue || 0).toFixed(2)}`` | `stats?.period_revenue_display ?? '$0.00'` |

Render `period_revenue_display` verbatim. Do not prepend another currency symbol and do not call `.toFixed()`.

Change the active-seller card grid from three columns to two columns at `sm` and four at `lg`. Add a fourth card as a `Link` whose entire card target is `/dashboard/sales?status=pending_delivery`. Its exact label is `Sales awaiting delivery`; its value is `stats?.pending_fulfillments ?? 0`. Use the same white card, border, shadow, label, and value styles as the existing three cards. Use the existing neutral gray icon color and do not add age-dependent styling or read `needs_action`.

Do not change the overview Purchases section or `getMyOrders()` behavior. `View all orders` is not a bare navigation or back-navigation label and is outside the copy replacements approved by Gate 1.

### 7.2 `app/dashboard/page.test.tsx`

Define one complete contract-shaped seller stats fixture and reuse it in every active-seller test:

```ts
const sellerStats = {
  period: '30d',
  total_listings: 2,
  total_views: 12,
  total_inquiries: 4,
  total_sales: 3,
  period_sales: 2,
  period_revenue_cents: 4550,
  period_revenue_display: '$45.50',
  pending_fulfillments: 2,
  conversion_rate: 75,
};
```

Mock `getSellerStats()` as `{ data: sellerStats }` in all three active-seller tests that currently carry the wrong shape: `renders active seller stats from capability state alone`, `renders purchases and order rows for an active seller`, and `keeps active seller dashboard content when purchases fail to load`. Rename the first of those tests to `renders active seller stats from the real contract shape`. Assert:

- `12`, `3`, and `$45.50` render.
- `Revenue (30 days)` renders and `Total Revenue` does not.
- The link named `Sales awaiting delivery` targets `/dashboard/sales?status=pending_delivery` and contains the nonzero value `2`.
- The existing active-seller personal purchase still renders and `/dashboard/orders` remains its list target.
- A rejected `getMyOrders()` still does not erase the seller stats or the Sales pointer.

Add a zero fixture assertion, using the same complete shape with `pending_fulfillments: 0`, that the pointer visibly renders `0`.

## 8. Test plan

### 8.1 Test files and assertions

#### New `api/seller.test.ts`

- `passes the Awaiting delivery query to seller orders`: assert `api.get` receives `'/seller/orders'` and `{ params: { status_filter: 'pending_delivery', limit: 100, offset: 0 } }`.
- `omits status_filter for All`: assert the params object is exactly `{ limit: 100, offset: 0 }` and has no `status_filter` property.
- `requests typed seller stats`: assert `getSellerStats()` calls `api.get('/seller/stats')` and returns the mocked Axios response unchanged.

#### Edited `app/dashboard/layout.test.tsx`

- `renders exact active seller navigation`: use an active capability response and assert link names and hrefs in DOM order: Overview, Listings, Sales, Purchases, Inquiries, Settings.
- `omits Sales for provisioning sellers but keeps Purchases`: assert the five exact provisioning names/targets in order and no Sales link.
- `renders exact buyer navigation`: assert Overview, My Inquiries, Purchases, My Requests and their targets in order.
- `redirects a buyer direct Sales visit`: set the pathname to `/dashboard/sales`, return an inactive seller capability, assert `router.push('/dashboard/inquiries')`, and assert the child does not render.
- Keep the current purchase-context test and update its descriptive child text only if needed; its `/dashboard/orders` route and hidden setup progress behavior remain unchanged.

#### New `app/dashboard/sales/page.test.tsx`

- `guards provisioning sellers before seller orders`: return provisioning capabilities, assert the `Sales` heading and exact provisioning body, and assert `getSellerOrders` has zero calls.
- `blocks unavailable seller capabilities before seller orders`: exercise `not_requested` and `suspended` resolutions separately, assert the `Sales` heading and exact blocked body for each, and assert `getSellerOrders` has zero calls in both cases.
- `shows the Sales heading and Loading sales... without stale rows`: use a two-phase arrangement. Resolve rows for one filter, switch to a second filter, leave the second request pending, then assert both exact strings and the absence of the first filter's fixture row.
- `requests the selected filters with the bounded query`: cover default pending, All, Delivered, and Completed; assert exact params each time.
- `renders all seven facts in desktop and mobile presentations without links`: use one pending fixture, assert the seven labels and values occur in both responsive branches, assert the container has no anchor, and assert no detail URL or action text.
- `keeps needs_action informational`: fix system time at `2026-08-20T15:00:00Z` and render two otherwise identical pending fixtures differing only in `needs_action`, including one with `paid_at: '2026-08-20T12:00:00Z'`; assert identical label/class/action/link treatment, prove ordering follows timestamps and order number rather than the boolean, and assert the exact absolute date `Aug 20, 2026` and exact relative age `3 hours ago`. The test must fail if either paid-date rendering is removed or changed.
- `sorts pending sales oldest paid first with deterministic ties`: use three pending fixtures, fix the clock, and assert DOM order by `paid_at` ascending, then `created_at` ascending, then `order_number` ascending.
- `sorts all non-default filters newest paid first with nulls and deterministic ties`: cover All, Delivered, and Completed explicitly. For each filter, include a null `paid_at` fixture and fixtures with equal `paid_at` and `created_at` but distinct order numbers; assert newest paid dates first, null dates last, and ascending `order_number` tie-breaking. The test must fail if any one of the three filter branches, null-last handling, or order-number tie-break is broken.
- `maps every seller status independently`: use `it.each` over all eleven Gate 1 values and exact labels; assert buyer-only labels `Pending`, `Fulfilled`, and `Failed` are not used for seller-only states.
- `reports an unknown status exactly once`: keep `SellerOrder.status` as the eleven-value union and use the explicit fixture cast `status: 'future_status' as SellerOrderStatus` to simulate runtime contract drift. Assert `Status unavailable` appears in both responsive presentations, `future_status` is absent, and `console.error` is called once with `('Unknown seller order status:', 'future_status')`.
- `renders each exact empty state`: separately select default, All, Delivered, and Completed and assert the exact heading/body pair.
- `renders exact error copy and retries the same request`: reject once, assert the exact heading/body/button, click `Try again`, resolve, and assert the same params object was used on both seller-order calls.
- `keeps one sale and one personal purchase on separate surfaces`: render Sales with a sale fixture and the Purchases page with a different buyer-order fixture in the same test; assert each title is present only on its directional surface and assert the seller client never receives the purchase fixture.
- Use fake system time for relative-age assertions and restore real timers and `console.error` after each test.

#### Edited `app/dashboard/orders/page.test.tsx`

- Update the empty-state test to assert page heading `Purchases`, subheading `No orders yet`, unchanged body/link, and one `getMyOrders()` call.
- Add `renders Purchases heading with a buyer order` using a non-empty buyer fixture; assert the purchase title renders, the `Purchases` heading is visible, and the seller sale fixture title is absent.

#### Edited `app/dashboard/page.test.tsx`

- Apply all assertions in section 7.2.
- Retain the provisioning-seller purchase test and active-seller purchase test.
- Retain the purchase-failure isolation assertion with the corrected complete stats mock.

No new test file is added for `app/dashboard/orders/[id]/page.tsx` or `CheckoutSuccessContent.tsx`. Their permitted edits are single copy replacements and are checked by the source and diff validation in section 9.4. The buyer detail behavior criterion is also a manual diff gate because a component test would require reproducing unrelated download, transaction, terms, and timer behavior without increasing confidence in the one-line copy edit.

### 8.2 Acceptance mapping

| Gate 1 criterion | Proof |
| --- | --- |
| 1 | `app/dashboard/layout.test.tsx > renders exact active seller navigation`. |
| 2 | `app/dashboard/layout.test.tsx > omits Sales for provisioning sellers but keeps Purchases`; `app/dashboard/sales/page.test.tsx > guards provisioning sellers before seller orders`; `app/dashboard/sales/page.test.tsx > blocks unavailable seller capabilities before seller orders`; `app/dashboard/layout.test.tsx > redirects a buyer direct Sales visit`. |
| 3 | `app/dashboard/layout.test.tsx > renders exact buyer navigation`. |
| 4 | `app/dashboard/sales/page.test.tsx > shows the Sales heading and Loading sales... without stale rows`; both `app/dashboard/orders/page.test.tsx` heading tests. |
| 5 | The three layout navigation tests; section 9.4 bare-copy scan; manual `/dashboard/orders` and `/dashboard/orders/<known-id>` route check. |
| 6 | Both filtered-query tests in `api/seller.test.ts`; `app/dashboard/sales/page.test.tsx > requests the selected filters with the bounded query`; section 9.4 Sales source-boundary scan. |
| 7 | `app/dashboard/sales/page.test.tsx > keeps one sale and one personal purchase on separate surfaces`; `app/dashboard/orders/page.test.tsx > renders Purchases heading with a buyer order`. |
| 8 | `app/dashboard/sales/page.test.tsx > renders all seven facts in desktop and mobile presentations without links`; manual responsive browser check at desktop and mobile widths. |
| 9 | `app/dashboard/sales/page.test.tsx > keeps needs_action informational`. |
| 10 | `app/dashboard/sales/page.test.tsx > sorts pending sales oldest paid first with deterministic ties`; `app/dashboard/sales/page.test.tsx > sorts all non-default filters newest paid first with nulls and deterministic ties`. |
| 11 | `app/dashboard/sales/page.test.tsx > maps every seller status independently` and `reports an unknown status exactly once`. |
| 12 | Sales row/card no-link test; section 9.4 Sales source-boundary scan; manual check that Sales has no mutation control. |
| 13 | `app/dashboard/sales/page.test.tsx > guards provisioning sellers before seller orders`; `app/dashboard/sales/page.test.tsx > blocks unavailable seller capabilities before seller orders`; the loading, empty-state, error, and retry Sales tests. |
| 14 | `app/dashboard/page.test.tsx > renders active seller stats from the real contract shape`; `npm run typecheck`. |
| 15 | The nonzero and zero `Sales awaiting delivery` assertions in `app/dashboard/page.test.tsx`. |
| 16 | Existing `app/dashboard/page.test.tsx > renders purchases and order rows for an active seller`, retained with `/dashboard/orders`; active-seller layout test. |
| 17 | Section 9.4 buyer-detail diff audit. Manually load a known buyer order and confirm existing download and transaction actions behave as before. |
| 18 | Section 9.2 focused suites and section 9.3 type-check, lint, purchase suites, and full-suite baseline comparison. |
| 19 | Section 10 local bundle sentinel check, followed by the named live Gate 4 verification step. |

## 9. Build order and validation

### 9.1 Build order

Apply the work in this order. Run the named focused check after each numbered step before continuing.

1. Replace the stale seller types in place and add `SellerOrderStatus` in `types/index.ts`; type `api/seller.ts`; add `api/seller.test.ts`. Confirm exactly one `export interface SellerStats` and one `export interface SellerOrder` remain, then run `npm run typecheck` and `npm test -- api/seller.test.ts`.
2. Add `app/dashboard/sales/page.tsx` and `app/dashboard/sales/page.test.tsx`. Run `npm run typecheck` and the Sales/API tests. The route exists but is not exposed in navigation yet.
3. Apply one atomic navigation and Purchases tranche: edit `app/dashboard/layout.tsx`, `app/dashboard/layout.test.tsx`, `app/dashboard/orders/page.tsx`, `app/dashboard/orders/page.test.tsx`, `app/dashboard/orders/[id]/page.tsx`, and `app/checkout/success/CheckoutSuccessContent.tsx` together. Run the layout, Sales, and Purchases tests plus the source/diff checks. Do not leave a candidate commit in which the old seller `Orders` entry points to Sales without the `Purchases` entry.
4. Correct `app/dashboard/page.tsx` and `app/dashboard/page.test.tsx`, including the Sales pointer. Run the dashboard, Sales, and API tests.
5. Run all validation in sections 9.2 through 10, inspect the complete manifest diff, and create one frontend implementation candidate commit containing every production edit and its tests.

All thirteen manifest files must land in the same final implementation commit. In particular, the Sales navigation entry, the active-seller Purchases entry, the buyer Purchases rename, and the unchanged `/dashboard/orders` target are one correctness unit. The seller stats correction is also part of this Gate 1 build and must not be split into an optional follow-up.

### 9.2 Focused tests

From `/Users/max/Projects/ai-market/ai-market-frontend` at the implementation candidate:

```sh
npm test -- api/seller.test.ts app/dashboard/layout.test.tsx app/dashboard/sales/page.test.tsx app/dashboard/orders/page.test.tsx app/dashboard/page.test.tsx
```

Passing means all five files and every test in them pass with exit code 0, no unhandled rejection, and no unexpected `console.error`. The unknown-status test temporarily spies on the one mandated error and restores the spy.

Run the existing purchase-related suites explicitly:

```sh
npm test -- app/dashboard/orders/page.test.tsx app/dashboard/page.test.tsx components/BuyButton.test.tsx components/orders/OrderVersionAccessSummary.test.tsx components/orders/ScopedCredentialDownload.test.tsx api/checkout.test.ts
```

Passing means all six files pass with exit code 0.

### 9.3 Type-check, lint, build, and full suite

```sh
npm run typecheck
npm run lint
npm run build
npm test
```

Expected results:

- `npm run typecheck`: exit 0 with no TypeScript diagnostic.
- `npm run lint`: exit 0. At the pinned clean baseline it emits seven existing `@next/next/no-img-element` warnings across six files: `app/blog/[slug]/page.tsx`, `app/dashboard/settings/page.tsx`, `app/l/[code]/page.tsx`, `components/Layout.tsx` twice, `components/listings/SellerShareControls.tsx`, and `components/listings/ShareKitModal.tsx`. This build adds no warning.
- `npm run build`: exit 0 and include `/dashboard/sales` in the generated route output. The build must not require a backend or environment change.
- `npm test`: compare against the pinned clean-main baseline. At `509ce253e9a2a16ba8584af7f144a85d4c895569`, Vitest reports 37 files, 156 tests, 36 files passed, 155 tests passed, and one existing failure: `app/dashboard/listings/[id]/edit/page.test.tsx > EditListingPage > loads compliance notes and saves compliance fields in the listing update payload`. The assertion expects `source_row_count: 100` but receives `source_row_count: undefined`. The builder must not edit that out-of-manifest file. The candidate is non-regressing only if this is the sole full-suite failure and every new/focused/purchase test passes.

The clean pinned baseline was checked directly on 20 August 2026: type-check exited 0; lint exited 0 with the warnings above; the three existing dashboard/layout/orders suites passed 14 of 14 tests; and the full suite had only the named inherited failure.

### 9.4 Source and diff boundaries

Run these checks from the frontend root:

```sh
git diff --check 509ce253e9a2a16ba8584af7f144a85d4c895569
git diff --name-only 509ce253e9a2a16ba8584af7f144a85d4c895569
```

The name-only output must contain exactly the thirteen manifest paths in section 2.

Run the Sales production-source boundary check:

```sh
if rg -n "@/api/(orders|transactions)|getMyOrders|getOrder\(|/orders/mine|/seller/pending|confirmTransaction|deliverTransaction|Mark Delivered|Deliver now|Upload" app/dashboard/sales/page.tsx; then exit 1; fi
```

Passing means no output and exit 0.

Run the retired copy check:

```sh
if rg -n "Check My Orders|Back to Orders|name: 'Orders'|name: 'My Orders'" app/dashboard app/checkout/success/CheckoutSuccessContent.tsx; then exit 1; fi
```

Passing means no output and exit 0. Internal component names, API names, error messages, order numbers, and non-navigation phrases such as `View Order` or `View all orders` are not changed by this check.

Inspect the buyer detail diff:

```sh
git diff --unified=3 509ce253e9a2a16ba8584af7f144a85d4c895569 -- 'app/dashboard/orders/[id]/page.tsx'
```

Passing means the only changed line is `Back to Orders` becoming `Back to Purchases`. Any import, fetch, condition, button, effect, or other copy change fails the Gate 2 boundary.

Inspect the checkout diff:

```sh
git diff --unified=3 509ce253e9a2a16ba8584af7f144a85d4c895569 -- app/checkout/success/CheckoutSuccessContent.tsx
```

Passing means exactly two text nodes change from `Check My Orders` to `Check My Purchases`, with both hrefs still `/dashboard/orders`.

## 10. Gate 4 sentinel

The All-filter empty body must appear in `app/dashboard/sales/page.tsx` exactly as one JSX text node on one source line:

```tsx
<p className="mt-2 text-sm text-gray-500">Sales will appear here after a buyer completes payment.</p>
```

Do not store the sentence in a constant. Do not use braces, a template literal, concatenation, an entity, nested spans, or JSX interpolation. Do not split the sentence across source lines. This guarantees the exact contiguous ASCII string is available to the compiler and can survive minification as one bundle string:

```text
Sales will appear here after a buyer completes payment.
```

After `npm run build`, run:

```sh
rg -F -l --glob '*.js' "Sales will appear here after a buyer completes payment." .next/static
```

The local check passes when at least one generated JavaScript asset path is printed. It proves the source and local production build retain the sentinel; it is not Gate 4 production proof.

Gate 4 is a named manual verification after production deployment. From outside the deployment environment, the verifier signs in through the normal production flow with an active-seller account and loads `https://ai.market/dashboard/sales` in that authenticated browser session. Collect the same-origin JavaScript assets returned by the page and its Next.js build manifest, fetch and decompress them from `https://ai.market`, and search the asset bytes for the exact literal. Record the live URL, UTC time, HTTP statuses, matched asset URL, exact literal, and the Next.js `buildId` from `/_next/static/<buildId>/_buildManifest.js`. Gate 4 passes only on a live production asset match. Git state, local or preview output, source maps, Cloudflare build status, and a branch deployment do not pass it.

## 11. Manual verification

After the automated checks pass, run these browser checks against the candidate build:

1. As an active seller, verify the six sidebar links and order from section 6.1. Open Sales and exercise all four filters. Verify desktop table and mobile card layouts show the same seven facts and no row/card link or mutation control.
2. As a provisioning seller, verify Sales is absent from the sidebar. Directly enter `/dashboard/sales`, verify the exact provisioning sentence, and confirm in the network panel that no `/seller/orders` request occurs.
3. As a buyer-only account, verify the four sidebar links and order. Directly enter `/dashboard/sales`, verify navigation goes to `/dashboard/inquiries`, and confirm no `/seller/orders` request occurs.
4. With an account fixture that has one seller sale and one personal purchase, verify the sale appears only under Sales and the purchase only under Purchases.
5. Open `/dashboard/orders` with empty and non-empty fixtures and verify `Purchases` remains the page heading. Open a known `/dashboard/orders/<id>` purchase and verify the back label is `Back to Purchases` while existing downloads and transaction actions behave as before.
6. Exercise checkout timeout and error fixtures and verify both links say `Check My Purchases` and still target `/dashboard/orders`.
7. Complete the live bundle verification in section 10 after production deployment.

## 12. Rollback

Rollback is one frontend commit revert. Revert the single implementation commit containing the thirteen manifest files, rebuild, and redeploy the resulting frontend revision. This removes `/dashboard/sales`, restores the prior `Orders` and `My Orders` navigation and headings, restores the prior checkout/back-link copy, removes the overview Sales pointer, and restores the prior seller stats consumer and tests.

There is no backend deploy, schema migration, data migration, feature flag, generated data, cache conversion, or persistent state to reverse. No compensating database action is required. Confirm the rollback by running type-check, lint, the focused tests that remain after the revert, and the standard frontend deployment verification.

## 13. Implementation risks

These are build risks, not Gate 1 design falsifiers.

| Risk | Required control |
| --- | --- |
| A provisioning, not-requested, or suspended visit calls the active-only endpoint before access is known. | Resolve `getCapabilities()` first and make `getSellerOrders()` reachable only from the explicit `active` branch. The Sales page tests prove zero calls for provisioning and for both blocked capability resolutions; the layout redirect test separately proves the eventual buyer redirect. |
| An earlier filter response overwrites a newer selection. | Use the existing effect-cancellation pattern and clear rows at each request start. |
| Null dates or equal timestamps produce unstable row order. | Apply the explicit null-last and three-key comparison in section 5.4 and test ties. |
| Responsive desktop and mobile branches report one unknown status twice. | Report unknown values in an effect with a component-local `Set`, not inside either render branch. |
| Seller labels drift into the buyer dictionary or raw runtime status leaks. | Keep the exhaustive seller dictionary local, type it with `Record<SellerOrderStatus, ...>`, and use a fixed unknown fallback. |
| The overview double-formats `period_revenue_display`. | Render the backend string directly and test `$45.50` from a nonzero complete mock. |
| The `status` search parameter admits an arbitrary backend filter. | Whitelist the four UI values and default every other value to `pending_delivery`. Never forward an unknown query value. |
| `useSearchParams()` causes a production build failure. | Keep it inside `SalesPageContent` and wrap that component in `Suspense` in the default export. Run `npm run build`. |
| The Gate 4 sentinel is folded, split, or absent from the emitted chunk. | Use the one-line JSX text node in section 10 and search the local production assets before deployment. |
| The inherited full-suite failure hides a regression. | Require all focused and purchase suites to pass, and compare the full result by failing test name and count. Do not repair the unrelated listing editor test in this build. |
| A broad copy edit changes buyer-detail behavior or unapproved copy. | Limit the detail and checkout diffs exactly as section 9.4 specifies. |

## 14. Conflicts requiring Gate 1 amendment

None. The pinned backend serves every approved read and access decision. The current frontend can implement the design within the thirteen-file manifest and without a backend change.
