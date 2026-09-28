---
title: Buyer Request Publication and Discovery
owner: vulcan
last_verified: '2026-09-28'
aliases:
- buyer-requests
- request-matching
- request-publication
error_signatures:
- BUYER_REQUEST_MATCH_RELEVANCE_QUESTION
- delivery_cycle_failed
- request_match_deliveries table does not exist
- rolling_24h_cap
---

# Buyer Request Publication and Discovery

## Overview

This runbook describes current code and deployed state separately; a merged commit is not called deployed until Railway proves the exact SHA.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| One persisted publication decision and reason (deployed) | SHIPPED | `app/services/request_publication_service.py` | `tests/test_request_publication_service.py`, cross-surface tests | 2026-08-29 |
| Public HTML/API/text/sitemap eligibility gate (deployed) | SHIPPED | `app/api/v1/endpoints/public.py` | publication, requests.txt, llms, SEO surface tests | 2026-08-29 |
| Durable seller matching and in-app delivery (deployed; email off) | SHIPPED | `app/services/request_matching_service.py` | 173 bounded tests; Council no HIGH/MEDIUM | 2026-08-29 |
| External seller email (disabled) | PLANNED | `app/core/config.py` | controlled local retry/idempotency tests only | 2026-08-29 |
| Homepage demand feed and Buyer Requests navigation (deployed) | SHIPPED | `app/page.tsx` | 258 frontend tests; typecheck; anonymous production GETs | 2026-08-29 |
| Buyer publication controls, reason and latest check visibility (deployed) | SHIPPED | `app/requests/[slug]/DataRequestDetailClient.tsx`; backend owner response | S1760 focused source tests and exact-head CI; normal owner read-only journey | 2026-09-28 |
| Public MCP request search (deployed) | SHIPPED | `app/services/mcp_tools.py` | 209 bounded backend tests including the agent route; anonymous production tool call | 2026-08-29 |
| Later digest sender (retained state only, not built) | PLANNED | — | cap-state test only | 2026-08-29 |

Pinned rollout evidence, refreshed whenever production or candidate identity changes:

| Surface | Immutable artifact | State and evidence |
|---|---|---|
| Publication gate and public discovery | `aidotmarket/ai-market-backend@faabfb284c69c47d9b8c45a5b1f2abb1d90a3e67` | Deployed by Railway deployment `b8114a63-06d8-42b9-817e-617b4e69769f`, image `sha256:b534428f6d128ae795f9b05542d678399b30f9bb98956fc836152902d7a961fe`; now superseded by the matching release. |
| Matching and in-app delivery | `aidotmarket/ai-market-backend@8a5e2671442abfb54c6b3c8f84281afff21f5bd2` | Deployed by Railway deployment `d61dca86-70f6-46ae-b77a-c1e1b1fb4890`, image `sha256:8c6391b8fd6757a9868dcb863468586117e8df1962d8260a2329a3300606d2c8`; now superseded by the MCP release. |
| Homepage feed and navigation | `aidotmarket/ai-market-frontend@3e61ca6d296edf1ae55c4b5710044d5315802e9c` | Deployed by Railway deployment `4509ace1-941f-466f-bd0f-24ccb73dfb03`, image `sha256:5d0b80fbd6f27ccb912e0900a864f363d4589276ad7510106608131f5af36d9f`; now included in the publication-controls release. |
| Buyer publication controls | `aidotmarket/ai-market-frontend@7f1d7ba45df3a44c2b57fe4d42f18b398e7a864e` | Historical S1632 production deployment `62d6fdcf-f673-4118-b0cd-9bbf45922907`, image `sha256:c12b96a4cd2b147053cb6aa876d63f27d742e8cc4fb16fbb0eb370e6186c8ebe`; Railway status `SUCCESS`. The merged tree `b406444395e3de42a6aaaf45eac98cfad3c829d7` exactly matches the three-member Council-reviewed candidate `d13472d0f2320b4fe6e196f3b2652b692e514df0`. |
| Public MCP request search | `aidotmarket/ai-market-backend@682ff2946d41130e66cb32ff720f3eb65cf15b2d` | Historical S1632 production deployment `a86e2c9f-b102-4414-8e8c-5c06b9d96fc7`, image `sha256:5d4fad9a84fa6809ec3538fe676b376d3c9645ad1db443a11a416a63aec86839`; Railway status `SUCCESS`. The merged tree exactly matches reviewed candidate `852c0b18b0d778089e89618deb45cd4242c49b58`. |
| Later digest sender | No backing artifact | Not built. |

Production proof for the matching release: `BUYER_REQUEST_MATCHING_ENABLED=true`, publication side effects on, external email false. After Max directed Vulcan to keep the clean test demand visible, all 42 retained outbox rows were processed by discovery and matching with zero errors. Nine open, clean, previously public test requests are eligible and zero delivery rows exist because synthetic buyers remain excluded from seller matching. Four open test requests flagged for contact or personal data remain private. `/api/health` reports process health. `/health` reports HTTP 200 with `alembic_head=alembic_current=s1632_request_matching` and `alembic_drift=false`; its overall `degraded` label is the pre-existing model-inventory drift, not migration drift.

Anonymous production proof for the frontend release: `/` contains the primary `Buyer Requests` navigation and renders `Buyer demand, live now`. An authorised Chrome DOM proof of `/requests` shows all nine eligible test requests with working detail links. The public list API returns nine items, `requests.txt` contains the same demand, and the backend request sitemap contains nine detail URLs. The generated Next.js `/sitemap.xml` can lag this change by its normal one-hour cache; its stable `/requests` index remains present while detail entries refresh. No retained sample was deleted and no second frontend eligibility rule was added.

Anonymous production proof for agent discovery: `/.well-known/webmcp.json` advertises `search_buyer_requests` with its typed public search arguments. An unauthenticated JSON-RPC call to `/api/v1/agent/tools/call` with query `dataset` returned `count=9`, `total=9`, and nine public request records, matching the authoritative public eligibility projection. The production agent audit suppresses the response payload. This surface exposes only the public allowlist fields and delegates eligibility to `data_request_service.list_requests(public_only=True)`; it does not create another publication rule.

The buyer-controls evidence above is the earlier S1632 checkpoint. Its owner-journey gap was subsequently addressed by the separately accepted normal My Requests navigation run 230727. For the S1760 owner-outcome fold, backend PR #516 merged as `53cc5057b203525e32dd28fcb320a97bf316b3d9` and Railway deployment `4b794635-462b-484b-9fd9-54f3771b6443` reported `SUCCESS`, `main`, stopped false and build-only false. Frontend owner display runtime `cf1c7333eaa77957083be1795147ce343397d635` had unanimous CC/GLM/DeepSeek approval; the later test-only folds left runtime bytes unchanged. Exact-head hosted CI `36375187043` passed for `79b51cb26a6932222b4ce56cf7445b18c5a49633`; merge `eebc5272a1408cb806f51450a7a3f7257d5c3a9d` deployed as `9a554aca-5de4-446e-89b3-2051a45c419a` with the same Railway source/status checks. These are exact source and deployment receipts, not per-request retry proof.

### Owner publication check outcome and retry (T-2026-000820)

The existing owner detail response exposes four persisted fields: `publication_check_outcome` (`clean`, `contact_or_personal_data`, `rejected`, `uncertain`, `unavailable`), `publication_checked_at`, `publication_retry_count`, and `publication_retry_at`. The first two are null before a check. The retry time is null when no check is scheduled. `publication_retry_stage` is derived by the owner response: `none` when retry time is null, `fast_retry` while a retry is scheduled with count below 6, and `recovery_probe` when it is scheduled with count 6. These fields report the **latest persisted check**, not every attempt or a provider diagnostic trace. The count is a capped scheduler stage, not a lifetime attempt count.

On `unavailable`, the request stays fail-closed and is automatically scheduled. Stages 1 through 5 delay 1, 5, 15, 60 and 240 minutes respectively; stage 6 schedules a 360-minute recovery probe and stays at 6 for later probes. A non-`unavailable` check clears the retry schedule and resets the count to 0. The scheduler redrives due rows every two minutes. A future `publication_retry_at` proves scheduling only; confirm an actual later `publication_checked_at` and outcome before calling a retry or recovery observed. Safe coarse category codes exist but cannot identify every provider failure class; the semantic cause of the current production `unavailable` outcome is unproved. General service health is not evidence of this request's retry.

The normal sanctioned owner read-only run `run-20260928T035805Z-1576944c` passed nine steps: Dashboard > My Requests reopened the existing synthetic private request and showed automated check unavailable (not rejection), last check at 2026-09-28 02:26 GMT+2, next scheduled check at 06:26 GMT+2 (04:26 UTC), fast retry, and no owner action needed. At that observation, the scheduled retry had not yet been observed executing; actual recovery remained unverified. The normal anonymous run `run-20260928T040243Z-924965de` saw “Request not found” on that exact private detail. An independent exact-slug public GET returned 404 with `no-store`. That run's title-only browser-list comparison was insufficient to establish the similarly titled public row's identity. The follow-up normal anonymous run `run-20260928T040542Z-c969d2bc` completed at 04:06:31 UTC with four passed steps, zero findings, and zero mutations: a native click on the public row opened a detail URL ending `292929f3`, distinct from the private request ending `31554259`. This resolves that row-click identity check only; full public-list/discovery and withdrawal/current privacy acceptance remain open. Do not infer identity from a similar title.

On 2026-09-28, the later normal owner read-only run `run-20260928T042610Z-7eee2820` completed at 04:27:48 UTC with eight passed steps and zero mutations. Dashboard > My Requests reopened the exact existing private request ending `31554259`. Its latest persisted check advanced from 00:26 to 04:27 UTC; the next check was scheduled for 10:27 UTC, with `recovery_probe` capped at stage 6. The outcome remained `unavailable` and visibility remained private. This proves that the scheduled automatic retry executed, but not recovery, the provider cause, public discovery, or withdrawal.

Owner-only fields do not enter the unchanged public response allowlist. Anonymous and other-owner access to a private request stays 404; a withdrawn formerly public request stays 410, with `no-store` on these detail responses. Public eligibility, exact-content consent hash, edit invalidation, and withdrawal protections remain in force. The frontend request list/detail and shared homepage three-request preview use `no-store` for fresh public data; this does not claim every discovery endpoint or sitemap has that cache policy. The accepted contact false-positive repair and separate My Requests navigation proof remain current; the initial `84bf` candidate is historical, not an outstanding unapproved state.

T820 remains **OPEN**. Closure requires source and documentation review, exact-head CI and deployment, observed sanctioned existing-request owner outcome **and recovery**, independent frontend list/detail cache freshness, and normal public/discovery plus withdrawal/current privacy acceptance. The owner read, observed retry, and schema fields alone do not satisfy these gates. No new request, editor write, consent change, production support SQL, or provider intervention is part of this documentation fold.

Refresh that proof only from authorised read-only sources: Railway's exact deployment list, the three resolved boolean settings from `app.core.config.settings`, aggregate counts/states from `request_publication_outbox`, `request_match_deliveries`, and `data_requests`, plus public GETs to `/api/health` and `/health`. Do not dump all environment variables, customer rows, request text, or identities into evidence.

## Architecture & interactions

The market uses one decision everywhere. An ordinary open, unexpired request from a verified non-synthetic buyer becomes public only when the buyer has consented to the exact current public text and the automated safety result is clean. Public website, API, sitemap, text, agent, homepage, search-submission, and seller-matching surfaces consume that persisted decision; none may invent its own eligibility rule. The current nine public test requests are a narrow operator-authorised visibility exception: they passed the safety check and were previously public, retain their synthetic-buyer classification, and therefore remain excluded from seller matching. This exception does not authorise publishing the four test requests flagged for contact or personal data.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Publication decision | `recompute_publication_decision` | `data_requests` | owner API, every public read | Decisions: `eligible`, `action_required`, `needs_review`, `ineligible`; one stable primary reason and next action. |
| Consent | `PUT/DELETE /api/v1/data-requests/{id}/publication-consent` | content hash, policy version, timestamp | owner frontend | Editing covered text invalidates prior consent. |
| Transition outbox | `request_publication_outbox` | unique request/version row | search, cache, matching | Keeps committed work until each consumer records completion or visible retry state. |
| Seller selection | `process_request_matching_outbox` | `request_match_deliveries` | Qdrant listings plus Postgres | Threshold 0.75, maximum five sellers, one best listing per seller, no synthetic/self match. |
| Delivery | `drain_request_match_deliveries` | independent in-app/email states | notifications, Resend | Completed channels are not repeated; retries retain missing work. |
| Later inventory | `process_inventory_rematches` | listing checked/retry columns | canonical listing indexing | A better current listing may replace an unsent row; delivered rows remain immutable. |
| Relevance inspection | first three genuine reports | delivery inspection state/code | automated inspector | A concrete question is visible; it does not block publication or in-app delivery. |

Human review is an exception for genuine ambiguity, not the normal publication path. Infrastructure unavailability retries automatically. No request may sit in an unexplained queue.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| allAI/backend workers | Decide, publish, match, retry through merged Chunk 2 | publication and matching services | service/database | COMPLETE |
| Buyer | Consent, edit, withdraw, inspect reason | owner API and frontend | own request | PARTIAL — deployed code is complete; close after one authorised controlled owner journey proves consent and withdrawal in production |
| Seller | Receive in-app match and respond | notifications and request response API | own account/listing | PARTIAL — in-app path is merged; external email remains disabled pending controlled proof |
| Public AI agent | Search eligible Buyer Requests | `search_buyer_requests` on the public MCP server | anonymous, public fields only | COMPLETE |
| Vulcan/Mars | Deploy, inspect, and roll back through this runbook | Railway, read-only SQL, runbooks | operator | COMPLETE |
| Human reviewer | Answer a concrete exception question; no routine queue | bounded exception surface | explicit exception only | COMPLETE |

## How to operate

E-01 and G-01 retain the historical S1632 rollout checkpoint. Their `682ff2946d41130e66cb32ff720f3eb65cf15b2d` pin records that checkpoint; it does not establish the current production image or independently authorize rollback to that older image against the current production migration graph. Verify current deployment and migration identity before any operational decision.

```yaml operate
- id: E-01
  trigger: Review the retained historical S1632 backend matching and public-MCP rollout checkpoint
  pre_conditions:
    - exact historical S1632 merge SHA was 682ff2946d41130e66cb32ff720f3eb65cf15b2d; this is not a current production or rollback pin
    - Alembic has one head named s1632_request_matching
    - BUYER_REQUEST_MATCH_EMAILS_ENABLED is false
    - a production backup or recoverable Railway database point exists
  tool_or_endpoint: Railway deployment for ai-market-backend
  argument_sourcing:
    revision: exact reviewed merge SHA, never an unpinned branch label
  idempotency: IDEMPOTENT
  expected_success:
    shape: deployment reports the exact SHA; /api/health is healthy; alembic head and current are both s1632_request_matching with no migration drift
    verification: read-only deployment identity, both health endpoints, schema, flag, and aggregate row-state checks; an unrelated model-schema warning does not prove this migration failed
  expected_failures:
    - signature: request_match_deliveries table does not exist
      cause: application code started before the forward migration completed
  next_step_success: run E-02 with controlled fixtures; keep external email off
  next_step_failure: run G-01; do not run the destructive downgrade

- id: E-02
  trigger: Prove matching after deployment
  pre_conditions:
    - E-01 succeeded
    - external email is false
    - controlled non-synthetic buyer, seller, request, and listing fixtures are authorised
  tool_or_endpoint: publication/matching worker plus read-only database and in-app notification inspection
  argument_sourcing:
    fixture: named controlled identities only; never invent a credential or use a real customer as a test
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: request decision_version plus the unique request_id/seller_id delivery row
  expected_success:
    shape: one eligible request selects at most five distinct sellers; each gets at most one in-app result; email remains held
    verification: inspect request decision/version, selected listing/score, per-channel states, notification count, retry/error columns, and synthetic/self exclusions
  expected_failures:
    - signature: delivery_cycle_failed
      cause: a retained channel attempt failed and should have a future retry time
    - signature: BUYER_REQUEST_MATCH_RELEVANCE_QUESTION
      cause: the inspector has one concrete semantic uncertainty; matching work is retained
  next_step_success: leave automatic matching on; record exact proof
  next_step_failure: isolate with When it breaks; disable matching with G-01 only if failure is systemic

- id: E-03
  trigger: Consider enabling external seller-match email
  pre_conditions:
    - E-02 passed with controlled fixtures
    - first three genuine match reports passed automated relevance inspection or expose a resolved concrete question
    - provider-safe duplicate and rolling-cap proof exists
    - Max explicitly authorises enablement
  tool_or_endpoint: BUYER_REQUEST_MATCH_EMAILS_ENABLED
  argument_sourcing:
    value: true only after all preconditions are evidenced
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: one content-bound email per selected seller, maximum three per rolling 24 hours
    verification: provider message ID, content-bound idempotency key, delivery state, and cap state; never log recipient or request text
  expected_failures:
    - signature: rolling_24h_cap
      cause: email remains retained as digest work while in-app delivery continues
  next_step_success: monitor delivery and response conversion without raw customer text
  next_step_failure: set the flag false; preserve delivery rows for diagnosis and retry
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Matching workers fail immediately after deploy | Migration not applied or wrong deployed SHA | Compare deployment SHA, `alembic_version`, and existence of `request_match_deliveries` | G-01 | CONFIRMED |
| F-02 | No sellers selected | Request not eligible/current, no candidate above threshold, listing not active/approved/indexed, self/synthetic exclusion | Read decision/version, canonical Qdrant hit, then Postgres revalidation result; do not lower the threshold to make a fixture pass | G-02 | CONFIRMED |
| F-03 | Repeated delivery failure | Notification/provider exception with retained attempt and retry time | Inspect only state, attempts, next-attempt time, and safe error code; never raw request text or email | G-01 | CONFIRMED |
| F-04 | More than one alert to the same seller/request | Out-of-band write, missing uniqueness, or a different legacy route | Verify unique constraint, delivery row, completed channel timestamps, and that legacy `request.published` handler is the no-op | G-01 | CONFIRMED |
| F-05 | Email does not send | Expected kill switch, preference, synthetic seller, cap, or provider failure | Read `BUYER_REQUEST_MATCH_EMAILS_ENABLED` and channel state before treating it as an outage | G-02 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Delivery
  root_cause: a systemic code/schema/worker failure
  repair_entry_point: BUYER_REQUEST_MATCHING_ENABLED=false and BUYER_REQUEST_MATCH_EMAILS_ENABLED=false
  change_pattern: Disable new matching and every external email while leaving the forward schema and all delivery/outbox rows intact.
  rollback_procedure: At the historical S1632 checkpoint, the documented response was to set both switches false and retain or redeploy the then-current reviewed, migration-aware SHA 682ff2946d41130e66cb32ff720f3eb65cf15b2d. This does not independently authorize redeploying that older image against the current production migration graph. Do not deploy faabfb284c69c47d9b8c45a5b1f2abb1d90a3e67 against a database at s1632_request_matching; its normal container start runs an older Alembic graph first and cannot locate the retained revision. If the current binary itself is implicated, stop and supply a separately reviewed rollback artifact that contains the forward migration graph; never stamp or downgrade merely to make an older image boot.
  integrity_check: /api/health is HTTP 200 healthy; /health has alembic_head=alembic_current=s1632_request_matching and alembic_drift=false; publication public reads remain gated; matching creates no new allocation during one worker interval; delivery/outbox counts, states, attempts, and next-attempt times remain queryable

- id: G-02
  symptom_ref: F-02
  component_ref: Seller selection
  root_cause: expected eligibility, relevance, preference, cap, or retry decision
  repair_entry_point: the authoritative request/listing/delivery state named by the safe reason code
  change_pattern: Correct the source state or wait for the retained retry. Do not hand-insert a match, bypass synthetic exclusion, lower the global threshold for one case, or delete a delivery row to force another alert.
  rollback_procedure: revert only the source-state correction if it was wrong; completed delivery evidence stays immutable
  integrity_check: one current decision, one request/seller row, no duplicate completed channel, visible next action
```

### Destructive migration downgrade prohibition

`s1632_request_matching.downgrade()` drops the entire `request_match_deliveries` table and the outbox/listing retry columns. After matching has processed any request, that destroys deduplication, delivery, suppression, inspection, and retry evidence; a later re-upgrade can re-alert sellers because the unique history is gone.

For the historical S1632 checkpoint, G-01 recorded switches off on the then-current migration-aware application, schema retained. Do not treat its pinned image as a current rollback target. Do not deploy the older publication image against the forward revision, and do not run `alembic downgrade s1632_request_publication` in production merely to roll back code. A destructive downgrade requires Max's explicit authority, a verified export/backup of every matching table/column, a proven restore procedure, external email off, matching quiesced, and a written decision accepting the possible replay/duplicate-alert consequence. Without all of those, stop.

## Changes and maintenance

### H.1 Invariants

- One persisted publication decision gates every public, search, agent, promotional, and seller-matching surface.
- Synthetic/test identities create no public, search, match, or email effect.
- Failed work is retained with a reason and next attempt; it is not deleted to make a queue look clean.
- A delivered seller/request channel is never re-alerted.
- External email stays off until controlled proof and explicit authority.

### H.2 BREAKING predicates

- A surface publishes or matches without the authoritative eligibility decision.
- A migration or cleanup deletes delivery/outbox evidence.
- A retry can duplicate a completed channel or lose a failed one.

### H.3 REVIEW predicates

- Changing threshold, five-seller limit, email cap, digest behavior, or relevance inspection.
- Adding another public or agent discovery surface.
- Enabling external seller email.

### H.4 SAFE predicates

- Adding read-only state/reason visibility or tests that preserve the same decision.
- Correcting copy or runbook evidence without changing runtime policy.

### H.5 Boundary definitions

#### module

Publication decision, transition outbox, request matching, delivery records, and discovery consumers.

#### public contract

Eligible request HTML/API/text/JSON-LD/sitemap/MCP representations and their 404/410 behavior.

#### runtime dependency

Postgres, canonical Qdrant listings collection, scheduler/Celery, notification service, and optional Resend provider.

#### config default

Matching enabled, threshold 0.75, five sellers, email disabled, three emails per rolling 24 hours.

### H.6 Adjudication

When a request is ambiguous, keep it private and show the primary reason. When matching relevance is ambiguous, retain the match with a concrete inspection question; do not stop unrelated clean work.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: repair
    refs: [G-01]
    scenario: A matching deploy is unhealthy after some delivery rows exist.
    expected_answers:
      - kind: human_action
        verb: disable
        object: matching and email switches
        target: the application rollout while retaining the forward schema and delivery history
    weight: 1.0
```

## Maintenance

```yaml lifecycle
last_refresh_session: S1632
last_refresh_commit: f2ea13d32a9bc85879f3185ce70f75d0c1fcb2f1
last_refresh_date: 2026-08-29T21:24:00Z
owner_agent: vulcan
refresh_triggers:
  - publication decision or reason mapping changes
  - a public, search, agent, matching, email, or digest surface changes
  - either matching/email switch default changes
  - production deployment or rollback evidence changes
scheduled_cadence: 1m
```
