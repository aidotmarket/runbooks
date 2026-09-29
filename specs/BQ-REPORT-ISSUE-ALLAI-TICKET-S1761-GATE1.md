# BQ-REPORT-ISSUE-ALLAI-TICKET-S1761: Gate 1 design brief r2 (Vulcan S1761)

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
- **Pre-existing weakness (in scope to fix, see D6).** For non-internal callers, `create_ticket` takes `requester_actor_type` and `requester_actor_id` from the request body when present (`support.py:87-88`; `requester_party_id` is already bound at :86). The same callers can also set `issue_class`, `human_required`, `links` and `probe`. And an agent API key that only has scope `support:read` can create tickets.

## Proposed design (r2)

r2 folds the round 1 findings:
- GLM REQUEST_CHANGES (response-20260929-014400-835331): F1 HIGH (one trusted command for both paths), F2 HIGH (no reachable route; do not expose Brain skills), F3 MEDIUM (probe bypass), F4 MEDIUM (snapshot allowlist), F5 MEDIUM (idempotency).
- DeepSeek APPROVE_WITH_NITS (-014403-249707).
- CC APPROVE_WITH_MANDATES (-014406-617298): F1 identity injection, F2 allowlist, F3 party_id already bound, F4 idempotency, F5 channel `allai` exists.

The main change from r1 is that there is no model-invoked write skill. One typed, authenticated server command files every order report. allAI only helps the user describe the problem.

- **D1: one trusted command.** A new service command, `report_order_issue(principal, order_id, proposal_id)`, sits behind one new authenticated route: `POST /api/v1/orders/{order_id}/issue-reports`, called with an ordinary session bearer.
  - The server resolves the principal from the session. It loads the order and requires the principal to be its buyer or seller. An unrelated user gets 404, the same as `GET /orders/{id}`.
  - The server builds every security-relevant ticket field itself: `issue_class='customer'`, `channel='allai'` (the value already exists), requester actor, party and org (from the principal), `links={order_id, listing_id}` (from the loaded order), priority, `risk_score` (unset), `human_required`, and the snapshot.
  - The client may send only:
    - the category (an enum: payment_charge, download_delivery, not_as_described, access_account, refund_request, other)
    - a description (text, maximum 4,000 characters)
    - for download_delivery only: browser (maximum 100) and error text (maximum 1,000)
    - the proposal id
  - Unknown fields are rejected with 422.
  - allAI and the plain fallback form both call this route. Nothing else files order reports.
- **D2: guided intake, with the model outside the trust boundary.**
  - The Report Issue button opens the allAI panel with a typed context `{mode:"report_issue", order_id}`. This extends the panel context schema that currently carries `page` and `listing_id` (`components/allai/AllAIContext.tsx:381-390`, backend `app/routers/anonymous_chat.py:882-928`).
  - When a user is signed in, the panel route authorizes the order before it shows allAI any order state.
  - allAI helps with self-service first, using the real order state (delivered-on date, downloads left, the browser note). It then drafts the category and description for the user to edit.
  - The user presses **Send report** in the UI. The frontend calls D1 with the user-confirmed fields. The model never calls a filing tool, never supplies identity, order ownership or priority, and cannot file without the user's click.
  - Ordinary tokens still cannot invoke generic Brain skills (the S1734 invariant, `allai-agents.md`). No new Brain write skill is added.
- **D3: proposal-based idempotency.**
  - Opening report mode creates a server-held proposal: `POST /orders/{order_id}/issue-reports/proposals` returns `proposal_id`, bound to (principal, order_id) and expiring after 24h.
  - D1 files at most one ticket per `proposal_id`, enforced by a unique constraint on the stored proposal-to-ticket link inside the creating transaction.
  - A retry or a concurrent confirm with the same `proposal_id` returns the same public ref.
  - The existing one-hour subject dedupe and the `SupportRateLimitRejected` path still apply.
- **D4: priority without fabricated probes.**
  - Every customer report is created at `medium` with no probe.
  - `payment_charge` and `refund_request` set `human_required=true`, so the ticket reaches the ops TICKETS view, and the Needs You feed when it is unassigned (`GET /api/v1/ops/needs-max`, runbook `ops-ai-market.md`).
  - No customer report ever gets high or critical priority, and no machine probe is invented.
  - The P0/P1 probe rule moves from `TicketCreateRequest` into `create_support_ticket` itself, so every writer is covered, not only the HTTP schema (GLM F3).
- **D5: fixed snapshot allowlist.** The payload's `order_snapshot` is built from exactly these scalar keys and nothing else:
  - `order_number`
  - `status`
  - `amount_cents`
  - `currency`
  - `created_at`
  - `paid_at` (if present)
  - `delivered_at`
  - `delivery_type`
  - `max_downloads`
  - `downloads_used`
  - `access_expires_at`
  - `revoked` (bool)
  - `escrow_hold_until`
  - `listing_title` (from `listing_snapshot.title` only)

  Explicitly excluded, with a test for each:
  - every `stripe_*` field
  - `transfer_*` fields and `transfer_error`
  - `delivery_config`, `delivery_file_path`, and all hashes
  - `listing_snapshot` beyond the title
  - `revoke_reason`, `revoked_by`
  - `seller_amount_cents`, `platform_fee_cents` (the buyer must not see seller economics)
  - any URL, token or credential

  User text is stored under `payload.user_report` with the key `untrusted: true`. The total payload is capped at 16 KB. Agents that read tickets treat `user_report` as data.
- **D6: hardening the existing public endpoint.** For non-internal principals on `POST /support/tickets`:
  - `requester_actor_type` and `requester_actor_id` are always the principal's. This is the real gap; `requester_party_id` is already bound at `support.py:86` (CC F3).
  - `human_required`, `probe`, `priority` above medium, `risk_score` and `org_party_id` are ignored or rejected.
  - `issue_class` is forced to customer.
  - Creation by API key requires `support:write`.
  - Gate 2 lists current callers with evidence before changing behavior.
- **D7: the fallback.** If the allAI panel is unavailable, the button opens a plain form with the same fields. The form gets a proposal and posts to D1. The mailto link on the order page is removed.
## Scope boundaries

- In scope:
  - The order page `app/dashboard/orders/[id]/page.tsx:625`. It is the only order-scoped mailto link; the buyer and seller views share this page.
  - Other support mailto links exist and are listed for a scope decision, but are NOT in scope unless reviewers or Max say so: `app/checkout/success/CheckoutSuccessContent.tsx:204`, `app/checkout/cancel/page.tsx:22`, `app/support/page.tsx:31`, `app/seller-workspace/support/legal-identity/page.tsx:10`. The investor, partner and newsletter mailto links are not support links and stay as they are.
  - The D1 command, route and proposal table, and the panel's report mode.
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

## Questions for Gate 1 reviewers (r2 delta)

1. Does D1 plus D2 close GLM F1/F2 and CC F1? Specifically: one authenticated command, the server builds every security-relevant field, the model is outside the filing path, and no Brain skill is exposed. Blocking if any path still lets a client or the model choose identity, order ownership or priority.
2. Does D4 close GLM F3? Customer reports are always medium with no fabricated probe, and the probe rule moves into the service.
3. Is the D5 allowlist complete and safe (GLM F4, CC F2, DS)? Name any key that should be added or removed.
4. Does the D3 proposal id give real idempotency under concurrency (GLM F5, CC F4)?
5. Scope, carried over from r1: should the checkout success page and the /support page get the same flow now (without order context), or later? Non-blocking.

Tier: 3 (customer data and support identity). Full panel per d50cbd80: GLM, DeepSeek, and CC in Gemini's seat; unanimous.
