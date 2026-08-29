# BQ-BUYER-REQUEST-LIQUIDITY-VISIBILITY-S1632

## 1. Business outcome

Genuine buyer requirements become public, searchable, agent-readable, and visible to relevant sellers without a routine human approval queue. Test, unsafe, unconsented, or uncertain requests stay private and carry one stable reason that explains what happens next.

The market is AI-operated:

- the normal path is automatic;
- a human is asked only when the automated checks cannot safely decide;
- no request may remain quietly blocked;
- the buyer and operators see the same primary decision and reason code.

Only buyer-approved requirement metadata is public. Raw customer datasets, samples, credentials, private identity, and direct contact details are never published by this flow.

## 2. One decision, everywhere

The backend owns one `RequestPublicationDecision` projection. Every public or promotional surface consumes it rather than rebuilding eligibility rules.

### 2.1 Decisions

| Decision | Meaning | Customer outcome |
|---|---|---|
| `eligible` | All checks pass | Publish automatically and run discovery/matching side effects |
| `action_required` | Buyer can resolve the issue | Keep private and return one actionable reason |
| `needs_review` | Automated checks found genuine uncertainty | Keep private, record an exception, and expose the reason to ops |
| `ineligible` | Test identity, withdrawn consent, rejection, closure, or expiry | Keep private and remove from public discovery |

`needs_review` is an exception outcome, not the normal route. No separate standing approval queue is required for clean requests.

### 2.2 Stable reason codes

- `eligible`
- `email_verification_required`
- `public_consent_required`
- `public_content_changed`
- `contact_or_personal_data_detected`
- `automated_check_unavailable`
- `synthetic_identity`
- `moderation_rejected`
- `consent_withdrawn`
- `request_not_open`
- `request_expired`

The public rule is intentionally short:

> An open, unexpired request from a verified non-synthetic buyer is public when the buyer has explicitly consented to the current public text and the automated safety check passed.

### 2.3 Consent and edit binding

Store on the request:

- public consent state;
- consent timestamp and policy version;
- SHA-256 hash of the public fields covered by consent;
- automated moderation decision, reason, and decision timestamp.

The public hash covers title, description, categories, format preferences, price range, currency, regulatory requirements, provenance requirements, and urgency in a deterministic canonical representation. A material edit changes the hash, makes the request private, and automatically runs the checks again. Consent remains valid only when the buyer explicitly confirms the changed public text. Withdrawal makes the request private immediately.

### 2.4 Automatic safety check

The first implementation reuses the existing contact-information detector and canonical synthetic-identity rules. Clean text passes automatically. Detected contact or personal information produces `needs_review`; unavailable automated checks fail closed as `needs_review`. Test accounts and reserved E2E domains produce `ineligible` and never create public/search/email effects.

The decision stores reason metadata but never stores detected personal values in logs, metrics, or notification metadata.

## 3. Eligibility transition and side effects

One transactional outbox records `request_eligibility_changed` with a unique request/content-hash transition key. Consumers are idempotent and observable.

### 3.1 Became eligible

1. Clear request and public-discovery caches.
2. Submit the canonical request URL to supported search providers.
3. Enqueue matching against approved active listings.
4. Make the request available to HTML, public API, sitemap, `requests.txt`, `llms.txt`, `llms-full.txt`, markdown/JSON-LD, homepage feed, and public MCP request search.

### 3.2 Became ineligible

1. Remove the request from every public projection.
2. Return `404` for never-public/private content and `410` for withdrawn, rejected, closed, or expired previously-public content according to stored publication history.
3. Clear caches and enqueue supported search removal/update handling.
4. Cancel unsent match notifications. Already-sent notifications remain in the audit ledger but their links resolve to the truthful non-public state.

## 4. Seller matching and alerts

Matching runs only for an eligible request and uses the canonical listing vector collection. Every candidate is revalidated in Postgres before selection.

Default policy:

- configurable initial similarity threshold: `0.75`;
- maximum five distinct sellers per request;
- one best active approved non-synthetic listing per seller;
- no buyer-to-self match;
- durable unique `(request_id, seller_id)` match-delivery record;
- email and in-app channel state tracked separately;
- notification preferences apply to both channels;
- maximum three request-match emails per seller per day; additional matches remain in-app and are eligible for a later digest;
- retries resume missing channel work without duplicating completed delivery.

Before automatic external email is enabled, controlled fixtures must prove the correct collection and ranking. The first three genuine eligible match reports are inspected for relevance; this inspection does not block publication, indexing, in-app visibility, or later clean automation.

## 5. Website and agent discovery

### 5.1 Website

- Add `Buyer Requests` to desktop and mobile main navigation.
- Add `/requests` to the primary sitemap.
- The homepage renders the three newest eligible requests as server-side crawlable links when at least three exist.
- Below three eligible requests, show a truthful buyer invitation rather than calling the section a live feed.
- The request directory and detail pages consume only the shared eligible projection for public visitors.

### 5.2 Machine discovery

- `requests.txt`, request sitemap, request markdown, Demand JSON-LD, `llms.txt`, and `llms-full.txt` consume only eligible requests.
- Expose `llms-full.txt` at the apex host and remove dead request-feed links.
- Add a read-only public MCP request-search tool using the same eligible projection.
- Retain Schema.org `Demand` for requests. Do not describe buyer requirements as available `Dataset` objects.
- OpenAI public Plugin portal submission is a separate follow-on after this MCP behavior is deployed and verified.

## 6. Measurement without hidden rules

Every non-eligible decision increments a metric by reason code. The operating dashboard reports:

- eligible, action-required, needs-review, ineligible, withdrawn, and expired counts;
- automated-decision latency and exception rate;
- match score distribution and selected/suppressed seller counts;
- email/in-app delivered, suppressed, failed, and retried;
- seller view and response conversion;
- homepage impressions and clicks;
- eligible URL index coverage and crawler visits.

No metric, log, event, or alert contains raw request text, detected personal values, buyer email, or raw customer data.

Sustainability trigger: if `needs_review` exceeds 10% of non-test publication attempts over a rolling 30-day window, the reason mix must be reviewed and the automated rule simplified or improved. Humans must not silently absorb growing exception volume.

## 7. Delivery chunks

### Chunk 1 — Eligibility foundation and stop current synthetic exposure

- migration for consent, content hash, moderation decision, publication history, eligibility outbox;
- one typed decision service and stable reasons;
- synthetic/reserved-domain exclusion;
- automatic contact/personal-data check;
- all existing public read surfaces and search submission gated by the decision;
- existing requests default private until current consent exists;
- focused cross-surface tests, including pagination-before-filter protection.

### Chunk 2 — Matching and notifications

- correct listing collection and Postgres revalidation;
- deterministic per-seller grouping, threshold and caps;
- durable outbox/dedup and per-channel delivery state;
- preferences, daily email cap, synthetic/self-match exclusions;
- controlled-fixture and retry tests.

### Chunk 3 — Website and discovery

- consent and decision-state frontend;
- main navigation and homepage eligible feed/empty invitation;
- canonical sitemap and discovery-file corrections;
- public MCP request search;
- cache invalidation and removal behavior;
- focused frontend, API, schema, and discovery tests.

### Chunk 4 — Runbooks, deployment, and proof

- update `data-requests.md` and `seo-infrastructure.md`;
- add `buyer-request-publication-and-discovery.md` and index it;
- deploy exact reviewed SHAs;
- prove clean automatic publication, exception visibility, synthetic exclusion, deduplicated alerting, truthful homepage behavior, search surfaces, and agent discovery;
- record rollback steps and monitoring thresholds.

## 8. Acceptance criteria

1. A clean verified non-test buyer can consent and publish automatically without human approval.
2. A request failing any single eligibility input is absent from every public/search/agent/promotional surface.
3. The API returns the same primary decision and reason displayed to the buyer and ops.
4. No pending request can remain without a reason and next action.
5. Material edits invalidate the old content hash and cannot remain public under stale consent or moderation.
6. Consent withdrawal removes the request from all controlled surfaces within five minutes and enqueues search update/removal.
7. Re-running matching or delivery produces no duplicate seller alert.
8. One seller with several matching listings receives one request alert using the best active approved listing.
9. At most five sellers are selected per request and at most three request-match emails are sent to one seller per day.
10. The homepage never labels synthetic, private, or insufficient inventory as live demand.
11. Public MCP and text discovery return the same eligible request set as the website.
12. Metrics explain every suppression using a stable reason without exposing request text or personal values.

## 9. Rollback

One configuration switch disables new request eligibility side effects while preserving private drafts and owner access. A second switch disables external seller email while leaving matching reports and in-app state available. Rollback never broadens public visibility: the shared read gate remains fail-closed.
