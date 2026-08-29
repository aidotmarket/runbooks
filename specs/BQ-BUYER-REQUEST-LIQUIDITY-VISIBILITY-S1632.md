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

The backend owns one persisted, authoritative `RequestPublicationDecision` projection with `decision`, `reason`, `decision_version`, `public_content_hash`, and safe check metadata. It is recomputed transactionally whenever an input changes. Every public or promotional surface consumes it rather than rebuilding eligibility rules.

### 2.1 Decisions

| Decision | Meaning | Customer outcome |
|---|---|---|
| `eligible` | All checks pass | Publish automatically and run discovery/matching side effects |
| `action_required` | Buyer can resolve the issue | Keep private and return one actionable reason |
| `needs_review` | Automation cannot safely decide yet | Keep private, record a visible exception, and automatically retry infrastructure failures or route genuine uncertainty for bounded review |
| `ineligible` | Test identity, withdrawn consent, rejection, closure, or expiry | Keep private and remove from public discovery |

`needs_review` is an exception outcome, not the normal route. No separate standing approval queue is required for clean requests.

### 2.2 Stable reason codes

- `eligible`
- `email_verification_required`
- `public_consent_required`
- `public_content_changed`
- `contact_or_personal_data_detected`
- `automated_check_unavailable`
- `safety_uncertain`
- `synthetic_identity`
- `moderation_rejected`
- `consent_withdrawn`
- `request_not_open`
- `request_expired`

The public rule is intentionally short:

> An open, unexpired request from a verified non-synthetic buyer is public when the buyer has explicitly consented to the current public text and the automated safety check passed.

### 2.3 Reason mapping and precedence

Every reason maps to exactly one decision and next action. When several conditions apply, the first matching row wins; no surface may choose its own priority.

| Priority | Reason | Decision | Next action |
|---:|---|---|---|
| 1 | `synthetic_identity` | `ineligible` | No public or seller effect; test traffic remains private |
| 2 | `consent_withdrawn` | `ineligible` | Buyer may explicitly consent again if the request is otherwise open |
| 3 | `moderation_rejected` | `ineligible` | Terminal safety rejection; expose the policy-safe explanation |
| 4 | `request_not_open` | `ineligible` | Reopen or create a current request when allowed |
| 5 | `request_expired` | `ineligible` | Renew the request when allowed |
| 6 | `email_verification_required` | `action_required` | Verify the buyer email |
| 7 | `contact_or_personal_data_detected` | `action_required` | Remove contact details and personal identifiers, then re-confirm the public text |
| 8 | `public_content_changed` | `action_required` | Review and confirm the newly persisted public text |
| 9 | `public_consent_required` | `action_required` | Explicitly consent to the current public text |
| 10 | `automated_check_unavailable` | `needs_review` | No buyer action; retry automatically when the check recovers |
| 11 | `safety_uncertain` | `needs_review` | Hold as a genuine exception with a visible reason and bounded safety review |
| 12 | `eligible` | `eligible` | Publish and run discovery/matching side effects |

`needs_review` therefore has two explicit recovery paths. Infrastructure unavailability is automatically re-driven and is never handed to a human backlog. A genuinely uncertain safety result may be reviewed as an exception; its resolution must write a new versioned decision and a policy-safe buyer explanation. Persistent detector false positives may escalate from repeated `action_required` to `safety_uncertain`, but never by silently changing the mapping above.

### 2.4 Consent and edit binding

Store on the request:

- public consent state;
- consent timestamp and policy version;
- SHA-256 hash of the public fields covered by consent;
- automated moderation decision, reason, and decision timestamp;
- monotonically increasing `decision_version` and nullable `first_published_at`.

`public_hash_v1` is SHA-256 over RFC 8785 canonical JSON encoded as UTF-8. The object has exactly these keys: title, description, categories, format preferences, price minimum, price maximum, currency, regulatory requirements, provenance requirements, and urgency. Persisted strings use Unicode NFC and LF line endings without lossy trimming. Set-like arrays are NFC-normalized, deduplicated, and sorted by Unicode code point. Prices are strings with exactly two decimal places; currency is uppercase; missing values are explicit JSON `null`. Golden fixtures pin the bytes and hash.

Any change to a covered field changes the persisted hash, makes the request private, and automatically runs the checks again. Consent confirmation names the already-persisted hash and is rejected on a concurrent hash mismatch; edit and confirmation cannot silently bind to different content. A consent-policy-version mismatch also requires explicit re-consent. Withdrawal makes the request private immediately.

### 2.5 Automatic safety check

The first implementation adds one typed request-publication classifier adapter around the existing contact/PII signals and canonical synthetic-identity rules. It inspects the current persisted public fields without rewriting them and returns exactly one of `clean`, `contact_or_personal_data`, `rejected`, `uncertain`, or `unavailable`, plus only safe metadata such as detector version and category codes. It never returns matched values, snippets, positions, or rewritten text.

`clean` continues toward eligibility; contact/personal-data maps to buyer self-service `action_required`; `rejected` maps to `ineligible`; `uncertain` maps to the exception-only `needs_review`; and `unavailable` maps to fail-closed `needs_review` with automatic bounded retry and recovery re-drive. Test accounts and reserved E2E domains produce `ineligible` before external side effects and never create public/search/email effects.

The decision stores reason metadata but never stores detected personal values in logs, metrics, or notification metadata.

## 3. Eligibility transition and side effects

One transactional outbox records `request_eligibility_changed` with unique `(request_id, decision_version)` identity. Every event carries `from_decision`, `to_decision`, primary reason, `public_content_hash`, and the committed version. The version increments only when the authoritative decision, primary reason, or bound public hash changes. Consumers apply only versions newer than the last version they processed; the hash is validation data, never the event identity. This supports ordered same-content cycles such as eligible → withdrawn → eligible without losing a transition.

### 3.1 Became eligible

1. Clear request and public-discovery caches.
2. Submit the canonical request URL to supported search providers.
3. Enqueue matching against approved active listings.
4. Make the request available to HTML, public API, sitemap, `requests.txt`, `llms.txt`, `llms-full.txt`, markdown/JSON-LD, homepage feed, and public MCP request search.

### 3.2 Became non-eligible

1. Remove the request from every public projection.
2. Apply the HTTP/cache matrix below.
3. Clear caches and enqueue supported search removal/update handling.
4. Cancel unsent match notifications. Already-sent notifications remain in the audit ledger but their links resolve to the truthful non-public state.

Chunk 1 durably retains matching events in this outbox while the Chunk 2 consumer is disabled. Activating Chunk 2 drains each retained version exactly once; no eligibility transition is dropped or re-created between deploys. `automated_check_unavailable` decisions use the same durable mechanism for bounded automatic retry and a recovery re-drive, with no human outage backlog.

### 3.3 Public HTTP and cache matrix

| Current state | Publication history | Public response | Cache/search action |
|---|---|---:|---|
| `eligible` | any | `200` | Publish current canonical content and refresh controlled caches/index submissions |
| non-eligible | never public (`first_published_at` is null) | `404` | `no-store`; never submit |
| `action_required` or `needs_review` | previously public | `404` | Purge controlled caches immediately; submit update/removal; may return to `200` on a later version |
| terminal `ineligible` | previously public | `410` | Purge controlled caches immediately and submit removal |

Terminal includes withdrawn, rejected, closed/not-open, expired, or later-classified synthetic content. Re-eligibility creates a newer decision version, restores `200`, and refreshes discovery. The minimal publication-history state is only nullable `first_published_at`; no second event-history subsystem is required.

## 4. Seller matching and alerts

Matching runs only for an eligible request and uses the canonical listing vector collection. Every candidate is revalidated in Postgres before selection.

Default policy:

- configurable initial similarity threshold: `0.75`;
- maximum five distinct sellers per request;
- one best active approved non-synthetic listing per seller, ordered by similarity descending, listing `updated_at` descending, then listing ID ascending;
- no buyer-to-self match;
- durable unique `(request_id, seller_id)` match-delivery record;
- email and in-app channel state tracked separately;
- notification preferences apply to both channels;
- maximum three request-match emails per seller in a rolling 24-hour window; additional matches remain in-app and are eligible for a later digest;
- retries resume missing channel work without duplicating completed delivery.

Seller selection orders each seller's best candidate by similarity descending, then seller ID ascending, and takes the first five. A listing becoming approved/active, or receiving a material metadata/vector update, enqueues one bounded rematch against currently eligible open requests that do not already have a `(request_id, seller_id)` delivery record. This later-inventory path may add an in-app result or later digest but never bypasses request/seller caps or re-alerts an already delivered seller. Every delivery worker revalidates the current request `decision_version`, `eligible` state, seller preference, and listing approval/activity immediately before send.

Before automatic external email is enabled, controlled fixtures must prove the correct collection and ranking. An automated relevance inspector examines the first three genuine eligible match reports; a human is asked only when that inspector returns a concrete question or uncertainty. This inspection does not block publication, indexing, in-app visibility, or later clean automation.

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

### 5.3 One public surface inventory

The Gate 3 implementation matrix must enumerate and test, at minimum: HTML directory, HTML detail, public API list/detail, sitemap, request markdown, Demand JSON-LD, `requests.txt`, `llms.txt`, `llms-full.txt`, homepage feed, navigation links, public MCP search, search submission/removal, cache invalidation, and seller notification links. Every row names the shared decision read, expected eligible behavior, expected never-public behavior, expected temporarily-private behavior, and expected terminal-removal behavior. A surface cannot ship if it rebuilds eligibility locally.

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

- migration for consent, `public_hash_v1`, typed current decision/reason, monotonic `decision_version`, minimal `first_published_at`, moderation metadata, and eligibility outbox;
- one typed decision service, exhaustive reason/precedence table, and non-rewriting detector adapter;
- synthetic/reserved-domain exclusion;
- automatic contact/personal-data self-service outcome and automatic detector-recovery re-drive;
- all existing public read surfaces and search submission gated by the decision;
- existing requests default private until current consent exists;
- durable matching events retained with the consumer disabled until Chunk 2;
- eligibility-side-effect kill switch delivered in this chunk;
- focused cross-surface tests, including pagination-before-filter protection.

### Chunk 2 — Matching and notifications

- correct listing collection and Postgres revalidation;
- deterministic per-seller grouping, ranking/tie-breaks, threshold and caps;
- later approved/materially changed inventory rematch trigger;
- durable outbox/dedup and per-channel delivery state;
- send-time decision-version revalidation, preferences, daily email cap, synthetic/self-match exclusions;
- external-email kill switch delivered before any external email is enabled;
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
7. Same-hash withdrawal/re-consent and expiry/renewal create ordered distinct decision versions and correctly remove then republish the request.
8. Detector unavailability remains private, retries automatically on recovery, and creates no human outage backlog.
9. Golden canonicalization fixtures are stable across array order and decimal representations; every covered value change changes the hash; edit/consent races fail closed.
10. Never-public, temporarily private, terminally removed, and re-eligible requests follow the exact HTTP/cache matrix.
11. Re-running matching or delivery produces no duplicate seller alert.
12. One seller with several matching listings receives one request alert using the deterministic best active approved listing.
13. Later qualifying inventory can match an eligible open request without re-alerting a seller already delivered that request.
14. At most five sellers are selected per request and at most three request-match emails are sent to one seller in any rolling 24-hour window.
15. The homepage never labels synthetic, private, or insufficient inventory as live demand.
16. Public MCP and text discovery return the same eligible request set as the website.
17. Metrics explain every suppression using a stable reason without exposing request text or personal values.

## 9. Rollback

One configuration switch disables new request eligibility side effects while preserving private drafts and owner access. A second switch disables external seller email while leaving matching reports and in-app state available. Rollback never broadens public visibility: the shared read gate remains fail-closed.
