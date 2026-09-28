# BQ-REPORT-ISSUE-ALLAI-TICKET-S1761: Gate 1 design brief (Vulcan S1761)

BQ: `build:bq-report-issue-allai-ticket-s1761` (P1). Origin: Max directive, Event 7d927a3c (2026-09-28), given while he looked at his own first real order page: "This should not open an email it should have allai walk the user through a trouble ticket report which we get in our ops console."

## Problem

On the buyer order page, **Report Issue** is `mailto:support@ai.market?subject=Issue with Order <8 chars>` (ai-market-frontend `app/dashboard/orders/[id]/page.tsx:625`, test at `page.test.tsx:309`). This has four problems:
- It depends on a mail client being configured.
- It carries no order context beyond 8 characters.
- It creates nothing the team tracks.
- It bypasses the support ticket system that the ops console already shows.

## What already exists (verified on backend origin/main at 49e2129a, frontend at ac0e0e40)

- **Support tickets.** `POST /api/v1/support/tickets` (`app/api/v1/endpoints/support.py:80`) creates a `support_ticket` row via `create_support_ticket`. It accepts a signed-in user's bearer token (`get_support_principal`, `app/api/v1/dependencies/support_ticket_auth.py:37`), and customers read their own tickets through `GET /support/tickets/mine` and the ticket messages endpoints. The ops console reads the same table.
- **allAI ticket status.** The allAI brain already has a read skill, `ticket_status_cards` (`app/allai/agents/allai_brain.py` ~1760), which shows the acting user their tickets as `SupportPrincipal(human, user_id, party_id, is_internal=False)`.
- **Frontend.** The allAI panel is global (`components/allai/AllAIContext.tsx`: `open()`, `sendMessage`, `page: pathname`). The anonymous surface already sends `context.page` and `context.listing_id`.
- **Pre-existing weakness (in scope to fix, see D5).** For non-internal callers, `create_ticket` takes `requester_actor_type` and `requester_actor_id` from the request body when present (`support.py:85-86`). The same callers can also set `issue_class`, `human_required`, `links` and `probe`. And an agent API key that only has scope `support:read` can create tickets.

## Proposed design

- **D1: button.** Report Issue becomes a button. It opens the allAI panel in a report-issue mode seeded with typed context: `{intent: "report_issue", order_id}`. The frontend sends only the order id. The backend derives everything else (listing, seller, status, payment, delivery state) from the order after checking that the acting user is the buyer or seller on the order (the same authorization as `GET /orders/{id}`). Nothing sensitive is put in URLs.
- **D2: guided intake.** allAI asks a short, bounded sequence:
  - It picks a category from a fixed list: payment or charge, download or delivery, data not as described, access or account, refund request, other.
  - It asks what happened, in the buyer's own words.
  - For download problems, it asks which browser and what error text appeared.
  - Where allAI can answer directly, it offers self-service first, grounded in the order's real state. Examples: "your files were delivered on <date>; you have 2 downloads left"; "this browser saves each file to Downloads". The user can always choose "file a report anyway."
  - It then shows a summary for the user to confirm. Nothing is filed without an explicit confirm.
- **D3: filing.** A new allAI brain **write** skill, `report_order_issue`, creates the ticket through the service layer, never through the public endpoint:
  - `issue_class='customer'` and `channel='allai'` (or `'web'` if the enum can't be extended).
  - `requester_actor_type/actor_id/party_id` always come from the authenticated acting user, never from model output.
  - `links={order_id, listing_id}`; the payload holds the category, the user's text, the transcript excerpt, and a server-derived order snapshot (status, payment state, delivery counters, timestamps; no card, bank or credential data, and no raw file contents).
  - Priority is server-derived. `medium` is the default. Money categories (payment, refund) are `high` with a machine probe, as the schema requires for P0/P1 (`TicketCreateRequest.require_probe_for_p0_p1`). The model never sets priority.
  - It is idempotent per (user, order, confirm action): a double-confirm or retry files one ticket.
  - It is rate limited by the existing `SupportRateLimitRejected` path.
  - allAI replies with the ticket's public ref and says where to follow it. The existing `ticket_status_cards` skill and the orders page link show status.
- **D4: ops console.** The ticket appears in the existing ops console support queue with the order link and the snapshot, so ops sees it the same way other customer tickets appear (ops-ai-market TICKETS view; `human_required` tickets with no assignee also reach the Needs You feed through `GET /api/v1/ops/needs-max`, per runbook `ops-ai-market.md`). Nothing new is built in the ops console unless Gate 2 shows the current queue view hides `issue_class='customer'` tickets. Money-category tickets set `human_required=true`.
- **D5: hardening.** Close the pre-existing spoofing gap in `POST /support/tickets`:
  - For non-internal principals, `requester_actor_type/actor_id/party_id` are always the principal's.
  - Non-internal principals cannot set `human_required`, `probe`, or an `issue_class` other than customer.
  - Creation by API key needs a write scope (`support:write`), not `support:read`.
  - Gate 2 must first confirm, with a read-only query, which current callers rely on these fields.
- **D6: fallback.** If allAI is unavailable (feature flag off, provider down, or the user is on a surface without the panel), the button opens a plain form with the same fields. The form posts to the hardened endpoint with `order_id` in `links`, so a report is never lost. The mailto link is removed.

## Scope boundaries

- In scope:
  - The order page `app/dashboard/orders/[id]/page.tsx:625`. It is the only order-scoped mailto link; the buyer and seller views share this page.
  - Other support mailto links exist and are listed for a scope decision, but are NOT in scope unless reviewers or Max say so: `app/checkout/success/CheckoutSuccessContent.tsx:204`, `app/checkout/cancel/page.tsx:22`, `app/support/page.tsx:31`, `app/seller-workspace/support/legal-identity/page.tsx:10`. The investor, partner and newsletter mailto links are not support links and stay as they are.
  - The one allAI skill.
  - Endpoint hardening.
  - The fallback form.
  - Tests.
  - The runbook `allai-agents.md` and support ticket runbook entries.
- Out of scope:
  - Refunds or any money movement. A refund-category report only files a ticket; `bq-refund-safe-production-s1714` owns refunds.
  - Dispute holds (`bq-dispute-hold-gate-s1711`).
  - Changing the allAI model (`bq-allai-openai-luna-chatgpt-oauth-s1761`).
  - Email notification changes.

## Invariants

- No raw customer data leaves the seller's storage (CORE S1). The order snapshot is metadata only.
- A user can report only on orders they are a party to.
- Model output never decides identity, priority or authorization.
- The customer's text is stored as data. It is never interpreted as instructions to agents downstream (ops agents that read tickets treat the payload as untrusted).

## Questions for Gate 1 reviewers

1. Is "allAI write skill through the service layer" the right filing path, or should allAI call the hardened public endpoint as the user? Blocking if either path lets model output choose identity or priority.
2. Is the D5 hardening safe to ship in this BQ, or does it break an existing internal caller that depends on non-internal override of requester fields? Name any caller you find.
3. Is the order snapshot free of anything that should not be in a ticket (payment instrument details, credentials, delivery tokens, signed URLs)? Blocking if the design allows those in.
4. Is self-service first (D2) acceptable, given that the user can always file anyway? Or should reporting be immediate?
5. Fallback (D6): is a plain form the right fallback, or is it in the way of the directive's intent?
6. Scope: should the checkout success page and the /support page get the same flow now (without order context), or later?

Tier: 3 (customer data and support identity). Full panel per d50cbd80: GLM, DeepSeek, and CC in Gemini's seat; unanimous.
