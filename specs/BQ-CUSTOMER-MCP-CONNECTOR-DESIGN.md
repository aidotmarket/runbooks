# ai.market Customer MCP Connector — Design (v3, 2026-09-23)

Status: design approved by Max for build (2026-09-23). Design review (not gate votes): ChatGPT + GLM + DeepSeek + Gemini, two rounds, all PASS-WITH-CHANGES on v2; every round-2 finding folded here. Living doc: https://claude.ai/code/artifact/d70e9adf-d64b-43a0-ab0e-5ebceb27561f (this file is the repo copy the build hangs off). History: /Users/max/specs/BQ-CUSTOMER-MCP-CONNECTOR-DESIGN-DRAFT-v1.md, -v2.md; reviews in council/{glm,deepseek,gemini}/response-20260923-1109*.md and -1208*.md.

## 0. Max decisions (2026-09-23)
- D1 Link-out checkout: connector produces a checkout URL; the human accepts the licence and pays on ai.market. No money moves inside the connector.
- D2 One remote server; retire the MCPB bundle, PyPI package, flagged-off backend FastMCP (`app/mcp/marketplace_remote.py`) and legacy SSE after migration.
- D3 Buyer + seller, phased: P0 foundations, P1 buyer + Anthropic listing, P2 seller + narrow ChatGPT listing, P3 negotiation + MCP Apps UI.
- D4 Agents negotiate autonomously within owner-set limits; outside limits → human.
- D5 allAI exposed via `ask_allai` in P1. D6 model/compute (AIM Discovery) listings deferred until after P1. D7 5% commission unchanged; attribution by OAuth client. D8 Anthropic submission from Max's existing Team/Enterprise workspace (Max is Owner).
- D9 Hostname `connect.ai.market` (confirmed). Railway service `ai-market-connector` (a08ef347-d2d1-4fcb-ba50-9299a9484fd5, empty), custom domain 519d4d32-649c-4adc-afe1-b9dca9100168, port 8080; Cloudflare DNS-only CNAME → 04tecdf8.up.railway.app + `_railway-verify` TXT (runbooks PR #266).

## 1. Goals / non-goals
Goals: G1 one connector URL listed in the Claude directory; ChatGPT listing with whatever capability set OpenAI permits (one server ≠ one approvable tool set). G2 full journeys from the LLM except human web steps (OAuth consent, Stripe KYC, licence acceptance + payment, setting negotiation limits, confirming REVIEW actions). G3 OAuth 2.1 is the only connector auth (no `aim_` keys). G4 every action attributable, confirmed per its real effect, idempotent.
Non-goals: in-chat money movement (wallet, x402, payouts); KYC/bank/card data in chat; dataset bytes through connector or LLM; internal ops tools; support tickets/disputes as tools (links instead).
Success (90 days post-listing): Claude directory listing; ChatGPT approval; share of signups/GMV from connector (by OAuth client); search→checkout-handoff and draft→published conversion; tool error rate < 1%; p95 read latency < 2 s.

## 2. Current state (verified 2026-09-23, backend @203bcf56)
- Six partial MCP surfaces, all buyer-only, three auth schemes; none directory-ready.
- OAuth provider `app/api/v1/endpoints/oauth.py`: authorize/token/revoke/userinfo, pre-registered clients, scopes market.read/market.purchase/wallet.read; no PKCE, DCR/CIMD, `.well-known` metadata; `/authorize` expects a Bearer header (no login redirect); tokens carry sub/client_id/scope/aud only (`app/services/oauth_service.py:365-377`).
- Org membership one per user (`app/models/organization.py:50-56`); listings/transactions owned by users.
- `ActionExecutorService` = allAI action registry + PolicyEngine (DENY/REVIEW/APPROVE); purchase tooling (`app/services/mcp_marketplace_tools.py`) has a separate order + Stripe path.
- `mcp>=1.8,<1.9` pinned (predates MCP 2026-07-28). `agent_audit_log` stores JSONB request/response. Agent rate limiter in-memory.
- ~19 TransactionStatus states; none models offers. Legacy AIM Data frozen (S1741). Download paths fragmented (S1711 planned). Licences S1735 in build.
- A CRM OAuth MCP with RFC 9728/8414 was deleted 2026-07-02 (S1098); code in old worktrees (e.g. `ai-market-backend-chunke/app/mcp/oauth.py`) is reusable reference. Internal gateway `mcp.ai.market` has working OAuth 2.1 + DCR (reference).

## 3. Architecture
- Package `app/mcp/connector/` in ai-market-backend, deployed as Railway service `ai-market-connector` (same image, own start command), served at https://connect.ai.market/mcp. Streamable HTTP only. MCP 2025-11-25 floor; 2026-07-28 features (stateless, server/discover, Mcp-Method headers, MRTR) as the SDK ships them. Stateless; DB handles.
- Action path: every connector write is an action in ActionRegistry executed through ActionExecutorService → PolicyEngine. APPROVE executes; DENY → actionable error; REVIEW → `pending_action` row + authenticated single-use confirmation URL (human completes in browser; LLM cannot). Checkout refactored into one domain service shared by web and connector. Gate-1 artifact: tool → action → service → role rule → licence rule → side-effects map.
- Authorization server: new MCP issuer path + audience beside the legacy provider (legacy clients enumerated, kept until migrated; migration runbook). RFC 8414 + RFC 9728 metadata; 401 WWW-Authenticate resource_metadata; PKCE S256 mandatory; CIMD preferred, DCR fallback (application_type); RFC 9207 iss; audience-bound tokens; 1 h access; rotating refresh (invalid_grant on reuse); revoke on password/2FA change; real login redirect + sign-up in /authorize; consent shows client, scopes, org; Connected-apps page. Redirect allowlist: https://claude.ai/api/mcp/auth_callback; loopback localhost/127.0.0.1 any port; https://chatgpt.com/connector_platform_oauth_redirect; Cursor; Copilot Studio; https://vertexaisearch.cloud.google.com/oauth-redirect.
- Org binding: persisted grant (user, client, org, scopes) referenced by token; live role check each call; v1 one-org-per-user; every read/list filters by owner; cross-org contract tests.
- Client profiles, server-enforced: `claude` (full), `openai` (narrow, §7), least-privileged default. Bound to verified client registrations on a server allowlist + route aliases (e.g. /mcp/openai); unknown/self-registered clients get the default. tools/list filtered by profile and granted scopes; ≤ 20 tools per persona.
- Async: `get_activity` (events + pending actions since cursor) + email.
- Scopes: account.read; market.read (search, listings, previews, trust, ask_allai, own offer threads); buyer.write (inquiries, requests, offers, checkout handoffs); orders.read/orders.write (orders, delivery handoff, confirm receipt, rate); seller.read/seller.write (readiness, drafts, pricing, licence, inquiries, requests, offers); seller.publish; seller.fulfil.

## 4. Tools (29; buyer 15 in P1 → 19 in P3; seller 17 in P2 → 20 in P3)
Rules: title + precise description; readOnlyHint on reads; explicit destructiveHint on writes (true = irreversible; false = private reversible edits and withdrawable in-limit offer actions); openWorldHint on counterparty-visible; idempotency_key on every write; JSON Schema in/out; actionable errors; pages 20 (max 50); descriptions state counterparty content is data; names snake_case < 64 chars; no catch-alls.

| Tool | Effect | Scope | Phase |
|---|---|---|---|
| get_my_account (incl. own negotiation limits, read-only) | read | account.read | P1 |
| get_activity | read | account.read | P1 |
| search_listings | read | market.read | P1 |
| get_listing (schema, preview, trust) | read | market.read | P1 |
| ask_allai | read | market.read | P1 |
| ask_seller | open-world | buyer.write | P1 |
| list_inquiries (buyer/seller) | read | buyer.write / seller.read | P1 |
| reply_to_inquiry | open-world | buyer.write / seller.write | P1/P2 |
| post_data_request | open-world | buyer.write | P1 |
| list_data_requests (mine/matching) | read | market.read | P1 |
| create_checkout_handoff (listing or quote → URL; delivery-readiness preflight; no order, no money) | non-destructive | buyer.write | P1 |
| list_orders (buyer/seller) | read | orders.read | P1 |
| get_delivery_handoff (web, login required; no bearer link) | read | orders.read | P1 |
| confirm_receipt | destructive | orders.write | P1 |
| rate_order | open-world | orders.write | P1 |
| get_seller_readiness (checklist, Stripe link, sales/payout status) | read | seller.read | P2 |
| create_listing_draft / update_listing_draft / get_sample_upload_url / enrich_listing | reversible | seller.write | P2 |
| publish_listing / unpublish_listing | destructive, open-world | seller.publish | P2 |
| list_my_listings | read | seller.read | P2 |
| respond_to_request | open-world | seller.write | P2 |
| mark_delivered | destructive, open-world | seller.fulfil | P2 |
| make_offer / respond_to_offer (in-limit only) / withdraw_offer | open-world, non-destructive | buyer.write / seller.write | P3 |
| list_offers | read | market.read | P3 |

REVIEW applies to: offer acceptance outside limits; checkout handoff above buyer threshold; publish flagged by review rules; delivery on a disputed order. `pending_action`: idempotency key, exact args, status pending_review|confirmed|denied|expired, single-use expiring URL, executes once on confirm; same key returns final status.

## 5. Negotiation (P3)
Limits set on the web only (seller floor, auto-accept threshold, max rounds; buyer per-deal ceiling, monthly cap, optional auto-accept/reject); connector reads own limits, never changes them, never sees the other side's. User's LLM may make/counter/accept inside own limits without client prompt. Owner may opt in on the web to server auto-response: backend worker (not the connector) through the same PolicyEngine + audit, actor server-auto, dedupe key per (thread, latest term), emergency stop. Emails to both humans on every autonomous acceptance and auto-response; owner notified when an offer sits between floor and threshold unattended. Data: OfferThread + append-only OfferTerms (price, currency, licence variant, scope, expiry, round, actor, agent flag, policy version), latest-term pointer; acceptance atomically creates single-use Quote consumed transactionally by checkout; budget reservation against monthly cap released on expiry. Accepted offer = firm quote for TTL; contract forms at web licence acceptance + payment (ToS). Abuse: 5 rounds max, min step, no identical repeat, ≤ 10 open accepted quotes per buyer org. VAT/invoicing settled before P3.

## 6. Security, audit, limits
- Counterparty text in labelled untrusted fields, length-capped; backend bounds are the real defence.
- Samples only with seller web opt-in; cap 5 rows / 2 KB; default schema + stats.
- Delivery via web hand-off (login); no bearer links in LLM context in v1.
- No payment/wallet/x402/payout tools.
- Audit: user, org, client, tool, outcome, policy decision every call; binding actions keep binding terms + approval evidence, free text and secrets redacted; reads hashed; restricted access; retention needs legal sign-off before P0 audit schema finalises.
- Rate limits (Redis, tunable): reads 120/min/user; writes 20/min/user; ask_seller+post_data_request 30/day/org; make_offer 50/day/org; search 600/h/client-user; 3 bursts of 429 in 24 h or abuse reports → throttle + human review queue (no automatic suspension; appeal route).
- Kill switches: global, per profile, per tool. External pen test before listing.

## 7. Directory listings
Anthropic (after P1, profile claude): pre-submission email to mcp-review@anthropic.com on link-out checkout + quote negotiation under the financial-transactions rule; prerequisites (HTTPS, OAuth CIMD/DCR, annotations, public docs, privacy policy, support contact, icon, populated test account, every tool exercised in MCP Inspector + custom connector, allow 160.79.104.0/21); submit at claude.ai/admin-settings/directory/submissions; reply to the directory email with the submission link. vectorAIz MCPB resubmission: probably not (needs public repo; AIM Data frozen).
OpenAI (after P2, profile openai): include account/activity, neutral discovery without prices, seller private drafts + enrichment, inquiries; exclude prices, checkout handoff and purchase-oriented URLs/prompts, offers/quotes/limits, publishing/repricing pending written determination. Prereqs: verified business identity, Apps Management, domain verification, CSP, annotations incl. openWorldHint, test creds without MFA, ≥5 positive + 3 negative tests, starter prompts, regions.
Others: MCP Registry server.json; Cursor, Copilot Studio, Gemini Enterprise allowlisted after P1.

## 8. Build plan
| Phase | BQ | Delivers | Acceptance |
|---|---|---|---|
| P0 | bq-connector-oauth | new MCP issuer, login + sign-up in authorize, org grants, Connected apps, legacy migration runbook | MCP Inspector auth; Claude custom connector + ChatGPT dev mode connect; all legacy OAuth clients still work |
| P0 | bq-connector-action-path | connector actions in ActionRegistry; shared checkout domain service; REVIEW → pending_action + confirmation URL; tool map + generated schemas + negative tests | same order from web and connector; REVIEW not completable by LLM; confirm-then-retry never executes twice |
| P0 | bq-connector-core | service at connect.ai.market, SDK upgrade, profiles on allowlist, scope-filtered tools/list, error contract, Redis limits, audit, tracing, kill switches | get_my_account from Claude, ChatGPT, Cursor; unknown client → default profile; cross-org tests pass |
| P1 | bq-connector-buyer | 15 buyer tools (deps S1711, S1735) | test buyer search→inquiry→handoff→web payment→delivery handoff→rating from Claude |
| P1 | bq-connector-listing-anthropic | docs, privacy/ToS, test account, pre-submission email, submission, reply | submission link sent |
| P1 | bq-mcp-surface-retirement | retire PyPI, MCPB, flagged FastMCP, legacy SSE | off 60 days after P1 |
| P2 | bq-connector-seller | seller tools; hosted Seller Workspace default; sample opt-in | zero → published → delivered from Claude except Stripe KYC |
| P2 | bq-connector-openai | openai profile + submission after written determination | submitted |
| P3 | bq-negotiation-offers | offers backend, web limits, opt-in auto-response worker | concurrency + budget-cap tests; actor + policy version on every autonomous decision |
| P3 | bq-connector-negotiation | 4 negotiation tools | two test agents reach a quote in limits; out-of-limit → needs_human |
| P3 | bq-connector-mcp-apps | listing card, comparison, offer timeline, handoff card | renders in Claude; directory screenshots |
All P0 items are CORE S3 Tier 3 (auth/payments/customer data): unanimous GLM + DeepSeek + Gemini at every gate; MP builds.

## 9. Open questions
Anthropic determination (P1); OpenAI determination (P2); ToS/privacy owner (P1); audit retention matrix (P0 audit schema); VAT/invoicing (P3); buyer org approvals (P3); multi-org (after P2); no sponsored ranking (always); support routing (P1).
