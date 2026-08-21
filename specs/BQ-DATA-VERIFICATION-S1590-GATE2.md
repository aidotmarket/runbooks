# BQ-DATA-VERIFICATION-S1590 Gate 2 implementation specification

**Status:** Gate 2 authoring candidate; build dispatch and production enablement remain blocked as described in sections 8 and 10.

**Build Queue entity:** `build:bq-data-verification-s1590`

**Design authority:** [Gate 1](BQ-DATA-VERIFICATION-S1590-GATE1.md) at `0cf14638ad9fc9551d1d3ee66031bda084bca783`, approved R3 unanimously by CC, Kimi, and GLM. Gate 1 is the sole product and trust authority. This document cites its decisions and fixes only implementation boundaries, files, acceptance checks, and test order. It does not replace or restate that design.

**Process authority:** `runbooks/council-gate-process.md` section E-02. The files below come from the source survey required by that process row.

## 1. Scope and non-goals

The build is the Slice 1 implementation frozen by Gate 1 sections 2, 3, 6-12, and 14: one eolymp-shaped AIM Data connector, scan-spec v1, deterministic facts followed by one bounded allAI narrative pass, the approved manual-capture payment lifecycle, seller publish or decline, the public scan-findings artifact, rerun supersession, the D8 preview option, and S1396 capture from the first initiated run.

Every item listed as deferred in Gate 1 section 14 remains deferred. In particular, these chunks do not add scheduled scans, drift detection, transaction-time checks, buyer-side fulfillment corroboration, additional connectors, buyer-triggered scans, public attempt history, quality scoring, compliance claims, or general-availability attestation hardening.

All new production behavior is fail-closed behind `DATA_VERIFICATION_ENABLED=false`. Reviewers may build and test the code before the checkpoints in section 8 pass; no paid production scan, production scan-spec issuance, or production badge publication may be enabled before they pass.

## 2. Ground-truth source trace

The trace was performed read-only on 21 August 2026. These SHAs fix the evidence used to name the files and seams in this plan; builders must stop and revise this specification if their dispatch baseline has materially diverged.

| Repository and traced SHA | Current path | Consequence for this plan |
| --- | --- | --- |
| `aim-data@6d0b089520d18fa06acf1ed78008c81138216d98` | `app/services/fulfillment_service.py` registers the sole `vai.fulfillment.deliver` handler, resolves `listing_id` through `DatasetRecord`, then resolves either the selected local artifact or the linked `S3ObjectMetadata` / `S3Connection`. | The scanner must call an extracted shared artifact resolver. It must not introduce a second listing-to-source mapping. This preserves Gate 1 sections 3.1 and 4 and AC6-AC7. |
| same | `app/services/s3_broker_client.py` obtains brokered presigned object access; AIM Data has no AWS credential path. | The S3 connector must consume the brokered object stream and must not add AWS credentials or copy source bytes to ai.market. |
| same | `app/routers/marketplace_publish.py` and `app/core/crypto.py` already create install-key-signed HTTP requests for listing publication. | Verification commands and receipts extend the signed HTTP control-plane pattern. They do not depend on the currently different AIM Data and backend Trust Channel envelope shapes. |
| same | `frontend/src/pages/DatasetDetail.tsx`, `frontend/src/lib/api.ts`, and `frontend/src/pages/DatasetDetail.test.tsx` own the listing preparation and already-published dataset surfaces. | One verification flow mounted on this page provides both Gate 1 section 2 entry points without creating a second seller application. |
| `ai-market-backend@ce64f51e8b377eb07520aae6210c41bf3979d5dd` | `app/routers/vz_publish.py`, `app/services/vz_publish_service.py`, and `app/models/vz_install.py` validate an install public key and bind a signed action to the seller and listing source. | Extract a generic install-action validator while retaining the current publish wrapper unchanged; verification uses distinct action claims and payload hashes. |
| same | `app/core/stripe_async.py`, `app/api/v1/endpoints/webhooks.py`, and `app/services/transaction_service.py` provide async Stripe calls, webhook deduplication, and an off-session PaymentIntent precedent. | The verification payment service uses those rails, one manual-capture PaymentIntent, opaque Stripe metadata, and the existing webhook entry point. It does not create a parallel webhook endpoint. |
| same | `app/services/agent_auth_service.py` can read a Stripe customer/default-payment-method mapping, but the ordinary seller listing path does not prove that mapping exists. | Paid pilot launch fails closed without a seller payment method on file; section 9 records the Sergey dependency rather than expanding Slice 1 into payment-method onboarding. |
| same | `app/core/llm.py` returns content and model identity but currently discards provider usage. `app/allai/brain.py` can estimate usage. | The bounded narrative adapter must retain actual provider-reported usage and reject absent usage. Estimated or client-reported usage is prohibited by Gate 1 sections 9-10. |
| same | `app/models/corpus.py`, `app/schemas/corpus.py`, `app/services/corpus_policy.py`, and migration `alembic/versions/20260818_001_s1396_b_schema.py` implement immutable S1396 structures, but the existing generation interaction requires a fingerprint and cannot represent every pre-fingerprint scan outcome. | Add a dedicated immutable verification-event record under the S1396 policy boundary. Do not overload a generation interaction or make a fingerprint mandatory for cancelled and failed starts. |
| same | `app/schemas/listing_public.py` and `app/api/v1/endpoints/public.py` expose public listing detail and `quality_score`. | Add the active scan artifact and withdrawal marker to the public projection and remove the numeric quality score from that projection, as required by Gate 1 sections 2, 11, and 14. |
| `ai-market-frontend@f46fa6caff7ea6799ac2748329eda7864d01b01f` | `app/listings/[slug]/page.tsx` and `components/ListingPurchaseAdvisory.tsx` render numeric quality information; `types/index.ts` carries it. | Remove that public score path and render one strict scan-findings component from the backend artifact. |

The A1 trace agrees with Gate 1 section 4. No alternative fulfillment path or source registry was found, so the approved A1 conclusion is used without reopening it.

## 3. Cross-repository contract and ownership

Gate 1 section 6 remains the exhaustive wire authority. Chunk 1 materializes that contract as versioned schemas and fixtures, but section 8.1 must approve the exact candidate before production enablement.

| Boundary | Producer | Consumer | Binding implementation rule |
| --- | --- | --- | --- |
| Quote probe | AIM Data | ai.market backend | Only the consented aggregate probe inputs needed to choose a complete depth class; no raw locator, D6 pre-sanitization input, or source error text. |
| Signed scan spec v1 | ai.market backend | AIM Data | KMS/platform-signed, expiring, nonce-bound spec whose fields and prohibitions are fixed by Gate 1 sections 3 and 6. |
| Signed receipt and report | AIM Data | ai.market backend | Install-action signature covers the canonical payload hash and Gate 1 section 6 receipt bindings. The raw locator and commitment key remain local. |
| Payment truth | Stripe webhook/reconciliation | ai.market backend | Backend-only state transitions; AIM Data receives a display-safe state, never a Stripe secret or payment-method identifier. |
| Published artifact | ai.market backend | public ai.market frontend | Immutable complete artifact or the time-bounded withdrawal marker. There is no partial-edit request shape. |
| Corpus event | ai.market backend | S1396 restricted store | One minimized append-only event per initiated epoch and terminal/lifecycle outcome, independent of publication consent. |

The shared canonical JSON fixtures are copied byte-for-byte into both Python test suites and pinned by a digest in each repository. Runtime code is not shared across repositories. A digest mismatch blocks the dependent chunk rather than allowing two dialects of scan spec v1.

## 4. Chunk plan

The file lists are exhaustive for each chunk. A builder who needs another production file must stop, explain the integration reason, and obtain a Gate 2 revision before touching it. Fixture and snapshot updates caused solely by a named test are included beside that test.

### Chunk 1 — Backend epoch, contract, and signed control plane

**Repository:** `ai-market-backend`

**Boundary:** Establish the disabled-by-default epoch store, exact request/response schemas, install-action authentication, quote endpoint, and platform-signed scan-spec issuance. Do not call Stripe, run allAI, accept a completed report, or publish an artifact in this chunk.

**Gate 1 citations:** sections 3, 6, 8, 9, and 13; AC2, AC5, AC12, and AC23.

**Files touched:**

- `app/core/config.py`
- `app/models/__init__.py`
- `app/models/data_verification.py` (new)
- `app/schemas/data_verification.py` (new)
- `app/services/vz_publish_service.py`
- `app/services/data_verification_signing.py` (new)
- `app/services/data_verification_service.py` (new)
- `app/api/v1/endpoints/data_verification.py` (new)
- `app/api/v1/router.py`
- `alembic/env.py`
- `alembic/versions/20260821_001_s1590_verification_epochs.py` (new)
- `tests/fixtures/data_verification_v1/scan_spec.json` (new)
- `tests/fixtures/data_verification_v1/report.json` (new)
- `tests/fixtures/data_verification_v1/schema_digests.json` (new)
- `tests/test_data_verification_contract.py` (new)
- `tests/test_data_verification_control_plane.py` (new)
- `tests/test_vz_publish.py`

**Acceptance criteria:**

1. `DATA_VERIFICATION_ENABLED` defaults false, and disabled endpoints cannot issue a quote or scan spec.
2. The persisted epoch supports the original seller scan plus disabled linked future epoch kinds required by Gate 1 section 8 and AC23; no deferred flow is callable.
3. A generic install-action validator accepts an expected action and canonical payload hash, while existing `publish_listing` behavior and tests remain unchanged.
4. The quote endpoint either returns one named complete depth class and its hard maximum or refuses before Stripe. It cannot represent a partial traversal.
5. Scan-spec v1 is canonical, signed through the existing platform KMS boundary, expiring, and bound to the epoch, listing, registered source handle, nonce, connector version, depth class, D8 flag, and policy versions.
6. Unknown keys, unknown enums, non-canonical payloads, stale nonces, replayed actions, and attempts to request prohibited fields fail closed and create no scan-start state.

**Test plan:** Run the three named focused test files; run `tests/test_vz_publish.py` as regression coverage; apply and downgrade the new migration on an empty test database; compare fixture digests; and assert the feature-off response before any Stripe or model mock is invoked.

### Chunk 2 — AIM Data artifact resolver, eolymp connector, and local deterministic engine

**Repository:** `aim-data`

**Depends on:** Chunk 1 contract fixtures.

**Boundary:** Resolve the exact fulfillment artifact, verify the signed spec, run the one supported connector locally, sanitize D6 locally, construct deterministic facts/coverage/D8 view, and sign the receipt. Do not implement seller screens or make publication decisions.

**Gate 1 citations:** sections 3-4, 6-9, and 13; AC1 and AC3-AC10.

**Files touched:**

- `app/services/fulfillment_service.py`
- `app/services/source_artifact_resolver.py` (new)
- `app/services/marketplace_action_signer.py` (new)
- `app/routers/marketplace_publish.py`
- `app/services/data_verification/__init__.py` (new)
- `app/services/data_verification/contract.py` (new)
- `app/services/data_verification/sanitizer.py` (new)
- `app/services/data_verification/scanner.py` (new)
- `app/services/data_verification/connectors/__init__.py` (new)
- `app/services/data_verification/connectors/eolymp_v1.py` (new)
- `app/services/s3_broker_client.py`
- `tests/fixtures/data_verification_v1/scan_spec.json` (new)
- `tests/fixtures/data_verification_v1/report.json` (new)
- `tests/fixtures/data_verification_v1/schema_digests.json` (new)
- `tests/fixtures/data_verification_v1/hostile_d6.json` (new)
- `tests/test_fulfillment.py`
- `tests/test_dataset_publish_signed_proxy.py`
- `tests/test_data_verification_resolver.py` (new)
- `tests/test_data_verification_scanner.py` (new)
- `tests/test_data_verification_sanitizer.py` (new)

**Acceptance criteria:**

1. Fulfillment and verification call the same resolver for `listing_id -> DatasetRecord -> resolved local path or S3 connection/bucket/object`; no second registry, fallback guess, or seller-supplied locator exists.
2. The resolver pins the exact selected artifact before reading. Local preferred-file changes and S3 connection/bucket/key changes alter the local locator commitment or content hash and reject stale identity as required by Gate 1 section 4.
3. Local and brokered S3 streams produce the same canonical report for the same bytes. No AWS credentials are introduced and no source bytes leave AIM Data.
4. The eolymp-v1 connector traverses every reachable supported object in deterministic order. Unsupported shape, incomplete coverage, or budget incompatibility refuses the run; it never silently samples away an object.
5. Facts, seeds, methods, buckets, coverage, and D8 projection are deterministic and model-independent. Unchanged bytes and spec yield byte-identical facts and fingerprint hashes.
6. D6 rejects every prohibited or obfuscated fixture before the signer or HTTP client sees it. The commitment key stays local, is distinct from the install signature key, and is absent from all transmitted objects and logs.
7. The signed receipt covers exactly the bindings required by Gate 1 section 6 and never the raw locator. Skipped objects use commitments and fixed reasons only.

**Test plan:** Run the six named test files; run the existing S3 tests `tests/test_s3_broker_client.py` and `tests/test_s3_scan_service.py`; compare the shared fixture digests with Chunk 1; run determinism twice against local and mocked broker streams; run one-row, two-row, low-cardinality, hostile-name, changed-file, changed-S3-key, permission-denied, and unsupported-connector fixtures; inspect captured HTTP and log records for prohibited bytes.

### Chunk 3 — Manual-capture payment lifecycle

**Repository:** `ai-market-backend`

**Depends on:** Chunk 1. Production execution also depends on checkpoint 8.2.

**Boundary:** Implement only the Gate 1 section 10 state machine, Stripe manual authorization/capture/void/reconciliation, and display-safe lifecycle status. Do not infer findings, publish, onboard payment methods, refund captured scans, or enable production.

**Gate 1 citations:** sections 9-10 and AC13-AC16.

**Files touched:**

- `app/models/data_verification.py`
- `app/schemas/data_verification.py`
- `app/services/data_verification_service.py`
- `app/services/data_verification_payment_service.py` (new)
- `app/api/v1/endpoints/data_verification.py`
- `app/api/v1/endpoints/webhooks.py`
- `alembic/versions/20260821_002_s1590_payment_state.py` (new)
- `tests/test_data_verification_payment.py` (new)
- `tests/test_data_verification_reconciliation.py` (new)
- `tests/test_webhooks.py`

**Acceptance criteria:**

1. One opaque `verification_id` creates at most one manual-capture PaymentIntent, one capture, and one void/release; webhook delivery and API retries are idempotent.
2. The server refuses authorization when the quote is outside USD 1-25, when the ordinary seller has no usable payment method on file, or when checkpoint 8.2 has not been recorded for production.
3. No signed scan spec is released before Stripe reports a capturable authorization. No result is revealed or publishable before confirmed capture.
4. Authorization failure, pre-inference cancellation, and our-fault failure publish nothing and void once. During/after-inference cancellation follows the charged-decline path. Unknown capture truth remains hidden in reconciliation.
5. The amount is recomputed from actual provider usage and the pinned provider/model price; it is twice provider cost, rounded as Gate 1 specifies, bounded by the authorization and USD 1-25. Missing or irreconcilable usage voids rather than estimates.
6. Stripe metadata contains opaque control IDs only; source, locator, D6, findings, and corpus content are absent.

**Test plan:** Run the three named focused/regression files with a fake Stripe adapter; replay and reorder webhook fixtures; inject timeouts before and after capture; test authorization expiry and permanent no-capture truth; assert financial call counts and state transitions for every Gate 1 section 10 state; assert no result serializer is reached before `CAPTURED`.

### Chunk 4 — Bounded allAI narrative, grounding, and S1396 capture

**Repository:** `ai-market-backend`

**Depends on:** Chunks 1-3 and the validated signed AIM Data report from Chunk 2.

**Boundary:** Accept a valid report, run exactly one tool-free narrative request, retain provider usage, validate grounding, finalize the immutable artifact, and append minimized corpus events. Do not add a second model pass or let model output write fact, charge, or lifecycle fields.

**Gate 1 citations:** sections 3.1, 7, 10, 12-13; AC10-AC11, AC15-AC16, and AC20-AC22.

**Files touched:**

- `app/core/llm.py`
- `app/models/data_verification.py`
- `app/models/corpus.py`
- `app/schemas/data_verification.py`
- `app/schemas/corpus.py`
- `app/services/data_verification_service.py`
- `app/services/data_verification_narrative_service.py` (new)
- `app/services/data_verification_corpus_service.py` (new)
- `app/services/corpus_policy.py`
- `app/api/v1/endpoints/data_verification.py`
- `alembic/versions/20260821_003_s1590_corpus_events.py` (new)
- `tests/fixtures/data_verification_v1/hostile_reports.json` (new)
- `tests/test_data_verification_narrative.py` (new)
- `tests/test_data_verification_corpus.py` (new)
- `tests/test_corpus_models.py`
- `tests/test_corpus_safety.py`

**Acceptance criteria:**

1. The backend accepts only a canonical, schema-valid, signature-valid, nonce-matched, unexpired report for the expected install, source, spec, and epoch; a changed byte or replay fails before allAI.
2. allAI receives only the approved canonical fingerprint and already-sanitized D6 as quoted untrusted context. It has no tools and runs at most once.
3. Actual provider input/output usage and pinned price identity survive the adapter boundary. Absence or inconsistency is an our-fault failure and cannot fall back to `app/allai/brain.py` estimation.
4. Every identifier and number in model-authored public fields is grounded exactly as Gate 1 section 7 requires. A failure removes all model-authored fields under the fixed fingerprint-only notice without retrying the model.
5. Every initiated and later lifecycle outcome appends the required minimized S1396 event, including starts that end before a fingerprint exists. Corpus and publication consent remain separate.
6. The corpus table is append-only, deny-by-default, and audited. It cannot store pre-sanitization D6, raw locators, commitment keys, source errors, credentials, values, samples, or free-form failure strings.

**Test plan:** Run the four named focused/regression files; use a counting model fake to prove exactly zero or one calls; test prompt injection in D6/column names, non-grounded numbers and identifiers, missing usage, price drift, fingerprint-only fallback, and every Gate 1 AC21 outcome; inspect prompts, logs, analytics doubles, Stripe doubles, and database rows for hostile fixture bytes; test immutable-table update/delete rejection and denied unaudited reads.

### Chunk 5 — AIM Data seller flow and interface quality

**Repository:** `aim-data`

**Depends on:** Chunks 1-4.

**Boundary:** Add the seller-facing D6, consent, quote, review, lifecycle, and rerun UI to the existing dataset detail page. This chunk submits signed commands and renders backend states; it does not compute prices or mutate cloud state locally.

**Gate 1 citations:** sections 2, 6, and 9-12; AC12-AC16, AC20, and AC24.

**Files touched:**

- `app/models/data_verification.py` (new)
- `app/routers/data_verification.py` (new)
- `app/schemas/data_verification.py` (new)
- `app/services/data_verification_client.py` (new)
- `app/services/data_verification_local_service.py` (new)
- `app/main.py`
- `alembic/env.py`
- `alembic/versions/024_bq_data_verification_s1590.py` (new)
- `frontend/src/lib/api.ts`
- `frontend/src/components/DataVerificationFlow.tsx` (new)
- `frontend/src/components/DataVerificationFlow.test.tsx` (new)
- `frontend/src/pages/DatasetDetail.tsx`
- `frontend/src/pages/DatasetDetail.test.tsx`
- `tests/test_data_verification_router.py` (new)
- `tests/test_data_verification_local_service.py` (new)

**Acceptance criteria:**

1. An eolymp-supported dataset shows the same flow before first publication and after listing publication; unsupported connectors show a clear unavailable state and cannot launch.
2. The five surfaces in section 6 satisfy every named UX criterion and use the canonical vocabulary/copy fixture, including error and keyboard/focus behavior.
3. D6 and D8 selections are fixed before authorization. The UI cannot add a free-form field, choose object exclusions, lower coverage, edit facts, or alter a charge.
4. The UI displays only server-authoritative lifecycle and financial states. Refresh/restart resumes the same epoch and cannot duplicate authorization, inference, capture, or publication.
5. Cancel is offered only with the consequence appropriate to the current server state. Results remain hidden through reconciliation and become reviewable only after confirmed capture.
6. Starting a rerun leaves the active publication visible. Publish, decline, withdraw, and rerun commands are explicit, separately confirmed, and signed.

**Test plan:** Run the four named frontend/backend tests; exercise the flow with keyboard only and at narrow/wide layouts; test refresh at every payment state; test unsupported source, authorization failure, local failure, reconciliation, fingerprint-only narrative, publish, decline, withdrawal, and rerun; assert action availability and exact consent/quote copy against fixtures.

### Chunk 6 — Publication projection, badge, score removal, and cross-repository journey

**Repositories:** `ai-market-backend`, then `ai-market-frontend`

**Depends on:** Chunks 1-5.

**Boundary:** Atomically publish the complete artifact or no artifact, expose the active artifact/withdrawal marker in the public listing contract, remove numeric quality score from listing surfaces, and render the badge. This chunk does not expose private attempts or declined results.

**Gate 1 citations:** sections 5, 8, 11, and 14; AC16-AC19 and AC25.

**Backend files touched:**

- `app/models/marketplace.py`
- `app/models/data_verification.py`
- `app/schemas/data_verification.py`
- `app/schemas/listing_public.py`
- `app/services/data_verification_service.py`
- `app/api/v1/endpoints/data_verification.py`
- `app/api/v1/endpoints/public.py`
- `alembic/versions/20260821_004_s1590_publication.py` (new)
- `tests/test_data_verification_publication.py` (new)
- `tests/test_public_listings.py`

**Frontend files touched:**

- `types/index.ts`
- `app/listings/[slug]/page.tsx`
- `app/listings/[slug]/page.test.tsx`
- `app/listings/[slug]/__snapshots__/page.test.tsx.snap`
- `components/ListingPurchaseAdvisory.tsx`
- `components/ListingPurchaseAdvisory.test.tsx`
- `components/listings/ScanFindingsBadge.tsx` (new)
- `components/listings/ScanFindingsBadge.test.tsx` (new)

**Acceptance criteria:**

1. Publish is one transaction that exposes every immutable fact, contradiction, limitation, coverage count, row-count method, narrative state, attestation, and disclaimer. Decline exposes none.
2. A listing has at most one active artifact. Publishing a later completed-and-captured epoch atomically supersedes the former one; starting or completing a rerun does not.
3. Withdrawal removes the artifact and returns only Gate 1's exact marker for 30 days. After that window no active badge or private history leaks through the public API.
4. The public API and listing page expose no numeric/composite quality score or unqualified truth, accuracy, compliance, fitness, continuous-monitoring, or future-delivery claim.
5. D8 schema preview and row counts render only when selected for that epoch and come from the same deterministic artifact.
6. Public rendering escapes source-derived text and preserves the complete approved artifact without client-side filtering or editing.

**Test plan:** Run the four backend/frontend suites plus the new component suite; update and review the one named snapshot; assert public JSON for published, declined, withdrawn-inside-window, withdrawn-after-window, and superseded epochs; search rendered text and public JSON for forbidden score/claim strings; execute one browser journey from AIM Data selection through quote, capture, review, publish, public badge, rerun supersession, and withdrawal. Static review, deploy receipt, and the browser journey are recorded as separate evidence per Gate 1 section 16.

## 5. Dependency and dispatch order

```text
Chunk 1 backend contract/control plane
  -> Chunk 2 AIM Data resolver/scanner
  -> Chunk 3 backend payment
  -> Chunk 4 backend narrative/corpus
  -> Chunk 5 AIM Data seller flow
  -> Chunk 6 backend publication, public frontend, and journey
```

Chunk 2 may prepare local-only code while Chunk 1 is under review, but it cannot claim contract acceptance until the fixture digests match. Chunks 3 and 4 may be reviewed independently after Chunk 1, but the first complete end-to-end state transition requires both plus Chunk 2. Chunk 6 is the only chunk authorized to expose the artifact publicly.

Each dispatch is one repository except Chunk 6, which has an explicit backend subcommit before the dependent frontend subcommit. A Gate 3 review receives the exact subcommit SHA and does not infer frontend correctness from backend tests or vice versa.

## 6. Interface Quality (binding Max requirement, decision event c721541c)

This section is a binding Gate 2 acceptance layer over Gate 1 sections 5-6 and 9-11. “Working” controls with internal enum labels, ambiguous money language, or compressed disclosure text fail even if their API calls succeed.

### 6.1 Curated D6 vocabulary

The wire values are stable slugs; sellers see the curated labels and one-sentence help text below. The exact candidate is part of checkpoint 8.1. No surface may show a slug, accept arbitrary text, or invent an `other` value.

| Field shown to seller | v1 wire value -> seller label | Help register |
| --- | --- | --- |
| Data domain | `education_learning` -> Education and learning; `software_technology` -> Software and technology; `business_finance` -> Business and finance; `health_life_sciences` -> Health and life sciences; `public_social` -> Public and social data; `physical_environment` -> Physical and environmental data | “Choose the broad subject this dataset describes.” |
| One record represents | `entity` -> A person, place, item, or organization; `event` -> An event or transaction; `measurement` -> A measurement or observation; `document` -> A document or content item; `relationship` -> A relationship between records; `aggregate` -> A summary or aggregate | “Choose what one row or record most closely represents.” |
| Time coverage | `current_snapshot` -> A current snapshot; `historical_period` -> A historical period; `time_series` -> A time series; `mixed_periods` -> Mixed time periods; `not_time_based` -> Not time-based | “Describe the dataset's time coverage, not how often it changes.” |
| Update frequency | `one_time` -> One-time release; `irregular` -> Updated irregularly; `continuous` -> Updated continuously; `daily` -> Daily; `weekly` -> Weekly; `monthly` -> Monthly; `quarterly` -> Quarterly; `yearly` -> Yearly | “Choose the normal update rhythm.” |
| Intended uses, up to five | `analysis_reporting` -> Analysis and reporting; `research_education` -> Research and education; `machine_learning` -> Machine learning; `benchmarking` -> Benchmarking; `reference_lookup` -> Reference and lookup; `operations_planning` -> Operations and planning | “Select uses the dataset is intended to support. These choices do not change the scan.” |
| Known limitations, up to five | `incomplete_coverage` -> Coverage is incomplete; `missing_values` -> Some values are missing; `estimated_fields` -> Some fields are estimated; `historical_cutoff` -> Data ends at a historical cutoff; `sampled_source` -> The source is sampled; `known_duplicates` -> Some records may be duplicated; `source_defined_categories` -> Categories are defined by the source | “Select limitations buyers should consider. Scan findings remain unedited.” |

Validation uses the wire slugs and Gate 1 section 6's strict key, type, count, normalization, ordering, and size rules. The interface never offers pasted descriptions, free-form limitations, column exclusions, or source-derived suggestions.

### 6.2 Named UX acceptance criteria

#### UX-D6 — D6 picker

- **Seller sees:** Six plainly titled groups, the curated choices above, selection counts for the two tag groups, and a persistent note: “These details help allAI interpret the scan. They do not change what is scanned or what the scan finds.”
- **Language register:** Everyday marketplace English; specific nouns and active voice; no `d6_description`, “taxonomy,” “enum,” “payload,” or policy-version jargon.
- **Seller can / cannot:** The seller can select one value in each single-choice group and up to five approved tags in each tag group, review choices, and clear optional tags. The seller cannot type text, paste source content, create a tag, omit required single-choice fields, or use D6 to select/exclude objects.
- **Failing implementation:** Raw slugs, a generic multi-select with unexplained options, free text, silent truncation at five, error-only-after-submit, or any D6 change that alters probe coverage, facts, price, or scan spec.

#### UX-CONSENT — Pre-scan consent screen

- **Seller sees:** The selected source/listing, supported connector, D6 summary, D8 choice, complete-depth probe status, every Gate 1 section 10 charge/cancel/reveal term, the Gate 1 section 12 corpus disclosure, and separate unchecked publication and corpus acknowledgements. The screen says that raw data and sample values stay in the seller environment and names exactly what metadata crosses by linking the approved manifest.
- **Language register:** Calm, direct, and legally honest without promotional “verified,” “certified,” or “safe” claims. Consequences appear beside the action, not behind a tooltip.
- **Seller can / cannot:** The seller can go back, revise D6/D8 before authorization, abandon with no charge, and open the detailed manifest. The seller cannot continue until the probe succeeds and both separate acknowledgements are actively checked; prior consent is not preselected or carried into a rerun.
- **Failing implementation:** One bundled checkbox, prechecked consent, hidden corpus terms, “cancel anytime for free,” omission of results-hidden-until-capture/no-refund terms, a launch button before a complete-depth result, or copy implying raw-data custody or an accuracy guarantee.

#### UX-QUOTE — Depth-class quote

- **Seller sees:** A human name for the selected complete depth class, what it measures, its uniform limitations and row-count method, objects discovered and any fixed-reason skips known by the probe, the exact maximum authorization, and “Final charge: 2x the measured cloud inference cost, minimum $1, maximum this authorization, never more than $25.” Refusal explains that no complete supported scan fits and creates no authorization.
- **Language register:** Concrete money and coverage language. “Maximum card hold” and “final charge” are distinguished; “tokens” is explained as cloud processing usage, not presented as an unexplained unit.
- **Seller can / cannot:** The seller can accept the named depth class or leave. The seller cannot choose a partial/budget-truncated scan, tune internal buckets, increase the cap above $25, or begin before the manual authorization succeeds.
- **Failing implementation:** “About $X,” a range without maximum-hold meaning, a quality tier that conceals reduced coverage, a spinner that starts scanning while authorizing, client-computed price, or a fallback partial result after refusal.

#### UX-REVIEW — Publish/decline review

- **Seller sees:** Only after capture, the complete immutable deterministic findings, contradictions, coverage and skips, row-count methods, optional D8 view, clearly separated `allAI interpretation` or fingerprint-only notice, charged amount, scan time, and the exact section 5 attestation/disclaimer. Publish and Decline are equal, explicit choices; publish confirmation states that all displayed content becomes public.
- **Language register:** Neutral evidence language. Negative findings are neither alarming nor softened. “Publish all findings” and “Decline publication” replace vague “Continue” and “Dismiss.”
- **Seller can / cannot:** The seller can inspect the full artifact, publish it atomically, or decline it entirely. The seller cannot edit, hide, reorder, partially publish, request another model answer, receive a refund by declining, or see findings before capture. A pending cancel during/after narrative ends declined without reveal.
- **Failing implementation:** Findings shown during capture reconciliation, a preselected publish action, editable narrative/facts, collapsed hidden contradictions/skips, a partial-publish control, a decline action described as free cancellation, or client-side filtering of the artifact.

#### UX-BADGE — Public scan-findings badge

- **Seller sees:** The same preview a buyer will see: `Scan findings — [UTC date]`, complete findings, coverage, every row-count method, optional D8 fields, the separated narrative state, and the exact Gate 1 section 5 disclaimer. On withdrawal the preview becomes the exact dated marker for the required window; a later run does not replace the current preview until explicitly published.
- **Language register:** Point-in-time, source-specific, and non-certifying. No green-check truth shorthand, numeric quality score, “verified dataset,” accuracy claim, continuous-monitoring claim, or future-delivery promise.
- **Seller can / cannot:** The seller can open the full artifact, withdraw the active publication with a consequence confirmation, or start a paid rerun. The seller cannot edit the public artifact, expose private attempts, label a declined scan, or force supersession before the later epoch is completed-and-captured and published.
- **Failing implementation:** Badge without date/coverage/disclaimer, color or icon implying certification, hidden skipped objects, numeric score, stale badge replaced at rerun start, private attempt count/history, or any public field differing from the captured review artifact.

## 7. Cross-cutting acceptance and evidence

In addition to per-chunk tests, the release candidate must produce:

1. A manifest diff proving the customer-to-cloud runtime schema equals the checkpoint-approved Gate 1 section 6 list and contains no widening.
2. A hostile-fixture evidence bundle covering D6 obfuscation, raw-value reconstruction, low occupancy, column-name injection, nonce/signature tampering, and locator dictionary attacks.
3. A payment transition matrix with Stripe request IDs, idempotency keys, webhook event IDs, state before/after, provider usage, pinned price, authorization, capture, and void amounts for synthetic data only.
4. A corpus evidence matrix mapping every initiated outcome to one minimized immutable event and proving denied/unaudited access.
5. Separate exact-SHA static review, deployment receipt, and signed-in browser journey evidence. Passing one does not stand in for another.

## 8. Production-enablement checkpoints

These checkpoints block production enablement, not specification review, branch merge, local implementation, or non-production tests. `DATA_VERIFICATION_ENABLED` remains false and no production paid pilot scan may run until both are unanimously approved by the active CORE S3 CC/Kimi/GLM panel and the immutable approval references are attached to the exact release candidate.

### 8.1 CORE S3 wire-manifest checkpoint — Gate 1 section 6

**Decision required:** Unanimous sign-off on the exact serialized scan spec and customer-to-cloud schemas, including the complete field list, D6 schema/vocabulary/size/sanitizer policy, low-occupancy threshold and behavior, artifact-locator commitment construction, key separation and custody, receipt signature coverage, and non-enumerability result.

**Required evidence:**

- Exact release-candidate SHA and generated schema digests from backend and AIM Data, with a zero-diff manifest comparison.
- Byte-level captures of every customer-to-cloud message class and searches proving prohibited material is absent.
- Customer-side key-flow diagram and tests proving the commitment/HMAC key never transits, is distinct from the install receipt key, and cannot be selected or derived from cloud-visible material.
- Reconstruction results for representative eolymp, one-row, two-row, low-cardinality, adversarial-column-name, and realistic locator/object dictionary fixtures.
- D6 hostile-input corpus and proof that rejection occurs before HTTP, prompt, persistence, log, analytics, Stripe, or corpus boundaries.
- Signed receipt tamper matrix covering spec, nonce, commitment, content hash, coverage, fingerprint, wrong install key, and raw-locator exclusion.

The standing GLM advisory must appear unchanged in the decision record as an explicit option:

> preselect fixed suppressed_low_occupancy as the single mandatory low-occupancy outcome for all four affected fields.

The panel must approve that option or record another single behavior allowed by Gate 1 section 6 for each of `null_rate`, `approx_distinct_count`, `length_histograms`, and `numeric_range_buckets`. Silence, per-source choice, or implementation defaults do not satisfy the checkpoint. Any field addition, widening, repurposing, or S3 rejection returns through the Gate 1/S3 change path; a builder may not repair it silently.

### 8.2 CORE S3 payment-state checkpoint — Gate 1 section 10

**Decision required:** Unanimous sign-off on the exact transition table, cloud-only meter source, pinned price identity, twice-cost calculation, USD 1-25 limits, manual-capture mechanism, cancellation boundary, hidden-until-captured rule, reconciliation behavior, and exactly-once capture/void guarantees.

**Required evidence:**

- Executable transition matrix for every state/event pair, including invalid transitions and restart recovery.
- Stripe sandbox request/event evidence for authorization failure, cancel before AIM Data acceptance, cancel during local scan, cancel during/after narrative, capture timeout with later success, permanent confirmed no-capture, authorization expiry, duplicate/reordered webhooks, publish, decline, withdraw, and supersede.
- Provider response showing actual usage plus the pinned model/price record and an independently recomputed charge; missing-usage and price-mismatch cases must void rather than estimate.
- Database uniqueness/locking and Stripe idempotency proof for one PaymentIntent, at most one capture, and at most one void/release per epoch.
- API/browser proof that scan cannot start before authorization and findings cannot be serialized, cached, logged, or displayed before confirmed capture.
- Confirmation that an eligible seller payment method on file exists for the named pilot account without placing payment details in source, D6, Stripe metadata, or this repository.

## 9. Risks and known unknowns

| Risk or known unknown | Impact | Required control / owner decision |
| --- | --- | --- |
| Sergey payment-method-on-file dependency | Any paid Slice 1 pilot scan is blocked unless the ordinary seller account has a usable Stripe customer and default payment method; a Connect payout account is not evidence of pay-in readiness. | Sergey must provide or confirm the supported payment-method-on-file path and a sandbox/pilot account before checkpoint 8.2. The build fails closed; onboarding UI is not added to Slice 1. |
| CORE S3 wire decision outstanding | Code may compile against a candidate that cannot legally cross the customer boundary. | Keep production disabled; attach the evidence in 8.1 and revise through the approved change path if rejected. |
| Low-occupancy reconstruction | Singleton and low-cardinality aggregates may reveal row properties. | Decide one signed deterministic behavior under 8.1, with GLM's standing option surfaced verbatim, and pass adversarial reconstruction. |
| Exact column names remain source-derived untrusted strings | Names can contain secrets or prompt/control text even when cells do not cross. | Apply Gate 1 sections 6-7 exactly: schema-bound transport, escaped rendering, quoted prompt data, no control role, hostile fixtures. If S3 rejects the field, return to Gate 1 rather than hashing silently. |
| Customer-held locator commitment key lifecycle | Lost or rotated material can break stable comparison; leaked material can create an enumeration oracle. | Document generation, storage, rotation, backup, destruction, and separation from the receipt key as checkpoint evidence; no cloud recovery shortcut. |
| Existing Trust Channel protocol shapes differ | Depending on the old WebSocket path could drop or misinterpret verification messages. | Use the traced signed HTTP control-plane path for Slice 1. Protocol convergence is separate work and not a hidden dependency. |
| Provider usage is currently discarded by the main LLM adapter | Honest twice-cost charging is impossible without the actual meter. | Chunk 4 retains provider usage; Chunk 3 refuses/voids when it is absent or irreconcilable. Never use estimates. |
| S1396 generation records require a fingerprint | Early cancellation/failure could be omitted from the corpus. | Use the dedicated append-only verification event in Chunk 4, allowing a fixed terminal outcome without a fingerprint while prohibiting raw/free-form content. |
| Seller-controlled agent and curated-source residuals | The public artifact can be mistaken for independent continuous truth. | Preserve the exact Gate 1 section 5 wording and known-counterparty limit. General availability remains deferred. |
| Cross-repository contract drift | Backend and AIM Data may accept different manifests or canonical bytes. | Pin shared fixtures/digests, fail builds on drift, and tie reviews to exact SHAs. |
| Public/private projection leakage | Declined attempts, pre-capture findings, withdrawal history, or scores could leak. | Separate serializers and tests for every lifecycle; public projection has only the active artifact or current withdrawal marker. |

## 10. Dispatch and completion rule

This document is ready for Gate 2 review only when its commit contains no source-repository changes and the Gate 1 wording nits are isolated in their own commit. Gate 2 approval requires a complete valid CC/Kimi/GLM review tied to the spec commit under `runbooks/council-gate-process.md` E-02.

After approval, builders receive one chunk at a time with the exact repository baseline, file scope, acceptance criteria, and tests above. A chunk is not complete merely because focused tests pass: it needs its exact-SHA Gate 3 evidence. Production enablement additionally requires both section 8 checkpoints, deployment proof, and the full signed-in browser journey. No branch or build status may be represented as production proof.
