# BQ-DATA-VERIFICATION-S1590 Gate 1 design specification

**Status:** Gate 1 design authority. Council Phase 1 returned CC, Kimi, and GLM `APPROVE_WITH_MANDATES`; this specification folds the converged mandates and Max's frozen decisions.

**Build Queue entity:** `build:bq-data-verification-s1590`

**Design sources:** the frozen Phase 1 deliberation prompt `s1590-data-verification-phase1.md`; the CC response `response-20260821-140621-976797.md`; the Kimi response `response-20260821-140626-047024.md`; the GLM response `response-20260821-140629-427247.md`; and Max's confirmed D1-D8, D10, Q1-Q3 decisions supplied on 21 August 2026. No D9 was supplied, so this specification defines no D9 requirement.

**Code baseline used to verify A1:** `aim-data@6d0b089520d18fa06acf1ed78008c81138216d98`

## 1. Problem

Listings can ask buyers to trust seller-authored claims while showing no honest evidence about the data behind those claims. Seller-initiated verification must create that evidence without breaking ai.market's non-custodial boundary: raw customer data never reaches ai.market, allAI, or any marketplace transit path.

The seller pays for an allAI-directed scan executed by AIM Data in the customer environment. Deterministic conduit code produces structural facts locally. Only the fixed metadata manifest in section 6 crosses to ai.market. allAI then performs one bounded cloud-side narrative pass over that fingerprint and the seller's untrusted descriptive context. The seller may publish the complete result or decline it. A declined result remains private and leaves the listing without a scan-findings badge.

The product claim is exactly this narrow point-in-time claim: on the stated date, ai.market directed a scan of the seller-designated AIM Data source and reports what the scan found. Findings publish as found even when they contradict listing claims.

## 2. Frozen product and trust decisions

The build must implement these decisions without reopening them:

1. The scan runs customer-side through AIM Data. Raw data, raw-derived samples, and data-plane frames do not reach ai.market. Launch coverage is limited to AIM Data-reachable sources. This preserves CORE S1/P8.
2. Published findings state what was found on the scan date. Listing contradictions are not softened, edited, or omitted.
3. After a completed and charged scan, the seller chooses either full publication or decline. Decline publishes nothing and leaves the listing without a scan-findings badge. Partial and edited publication are prohibited.
4. Price is twice ai.market's measured cloud inference token cost, bounded to USD 1-25, using existing Stripe rails and owner pre-authorization.
5. The badge shows the findings, scan date, coverage, and fixed point-in-time disclaimer. A seller may cancel a run, withdraw a publication, or supersede it by publishing a later completed run.
6. The structured seller description is untrusted context. It describes the data to help interpretation; it cannot change scan scope, tools, facts, charge, or publication state.
7. Numeric or composite quality scores are absent from listing pages until separately redefined.
8. Before the scan, the seller may opt into a schema-level preview and row counts generated from the same scan report. This is the T-2026-000689 minimum-information set; it is not a second scan.
9. Entry points exist in AIM Data at listing time and later.
10. A pre-run probe must select and disclose an honest supported depth class or refuse to start. A budget limit must never silently truncate coverage or produce a partial published result.
11. A withdrawn publication leaves a visible `Scan findings withdrawn by seller on [date]` marker for 30 days.
12. Every initiated scan, including published, declined, cancelled, failed, and superseded runs, feeds BQ-STRUCTURE-METADATA-CORPUS-CAPTURE-S1396 under the disclosed and separated consent rules in section 12.

## 3. Binding architecture

### 3.1 Two-stage execution

**Stage A — deterministic customer-side facts.** ai.market issues a signed, versioned scan specification to AIM Data. AIM Data verifies the signature, resolves the registered source handle to the exact artifact, and runs deterministic conduit code over the complete supported traversal root. The LLM is out of the loop. The conduit computes only the facts in section 6, constructs a canonical fingerprint, and signs a receipt containing the scan-spec hash, fresh nonce, install-key identity, exact local artifact binding, content hash, scan window, coverage, and fingerprint hash.

The scan specification fixes the connector, traversal root, traversal order, fingerprint algorithm, bucket boundaries, approximate-distinct algorithm, deterministic seed, output contract, depth class, and preview toggle. D6 text and source-derived strings cannot modify it. Sampling or approximate algorithms use a seed derived from the signed spec and source binding so unchanged data under the same spec produces byte-identical canonical facts and fingerprint hashes.

**Stage B — bounded cloud-side narrative.** ai.market accepts only a schema-valid, nonce-matched, install-key-signed report. allAI receives the approved fingerprint fields plus the D6 seller description as quoted untrusted context. It performs one bounded narrative pass with no tools and no ability to write deterministic fact fields. Provider usage at this boundary is the exclusive token meter. The D8 preview, when selected, is a view over the same deterministic facts rather than model-authored data.

### 3.2 Wire directions

Cloud to customer:

- Signed scan spec: spec identity and hash, nonce, registered source handle, connector/profile version, depth class, deterministic seed inputs, field contract, bucket definitions, hard inference budget, preview toggle, issue/expiry times, and cancellation signal.
- No D6-derived instruction, seller-controlled exclusion, request for a raw value, or free-form tool command is permitted.

Customer to cloud:

- Owner consent and launch envelope, including the D6 description.
- The final signed receipt and only the exact fields in section 6.
- Fixed-enum terminal errors when a report cannot be produced.
- No scan-derived progress payload is needed in v1. No raw cells, rows, samples, top values, free-form source errors, credentials, file contents, or data-plane frames cross.

### 3.3 Trust anchors

The v1 trust anchors are the authenticated seller account, registered AIM Data source handle, server-signed scan spec, fresh nonce, per-install signing key, pinned scanner and connector versions, deterministic canonicalization and seeding, exact artifact binding plus content hash, platform-side provider metering, Stripe authorization/capture record, and append-only S1396 corpus record.

The install-key receipt proves that the registered AIM Data installation reported execution of the signed spec against its pinned artifact. It does not prove that a seller-controlled agent binary was untampered. Trusted-hardware or equivalent attestation is deferred but must land before general availability.

## 4. A1 source-handle evidence and consequence

A1 is confirmed at handle level at the pinned AIM Data SHA.

- The production source search finds one `vai.fulfillment.deliver` handler registration, and it routes into `FulfillmentService._handle_deliver`: `aim-data@6d0b089520d18fa06acf1ed78008c81138216d98:app/services/fulfillment_service.py:71-74` and `:103-149`.
- `_find_dataset(listing_id)` resolves `DatasetRecord.listing_id`, with a `publish_result.json` fallback that finds the dataset and backfills its `listing_id`: `aim-data@6d0b089520d18fa06acf1ed78008c81138216d98:app/services/fulfillment_service.py:475-517`.
- Local fulfillment resolves the concrete file by preferring `dataset.processed_path`, then the standard processed Parquet, then the original upload: `aim-data@6d0b089520d18fa06acf1ed78008c81138216d98:app/services/fulfillment_service.py:539-562`.
- S3 fulfillment resolves `S3ObjectMetadata.dataset_id` to `S3Connection`, then presigns the registered `connection.role_arn`, `connection.bucket`, and `metadata.object_key`: `aim-data@6d0b089520d18fa06acf1ed78008c81138216d98:app/services/fulfillment_service.py:519-537` and `:255-290`.

Therefore the scan may honestly bind to the same registered source handle that fulfillment resolves for the listing. This is source identity at handle level, not a promise of byte equality at a future delivery.

The local signed receipt must pin the exact resolved artifact used by that run:

- Local source: canonical resolved path plus SHA-256 content hash.
- S3 source: connection ID, bucket, object key, and SHA-256 content hash.

The exact local locator stays in the customer-side signed receipt. The customer sends a keyed, install-scoped locator commitment plus the content hash; the locator commitment can later be checked against the signed receipt without disclosing a filesystem path or bucket/key to the cloud. This satisfies the exact-artifact pin while keeping the transmitted manifest non-reversible. Because `_resolve_file_path` may choose a different concrete file under the same handle over time, the artifact pin is mandatory.

Post-scan replacement of the file or object behind the handle remains undetectable in v1. That residual is disclosed. A1 supports the source-identity claim; it does not justify a claim of future delivery equality.

## 5. Attestation honesty and public wording

The public attestation is limited to:

> On [scan date and time], at the data owner's authorization and expense, ai.market directed AIM Data to scan the seller-designated source for this listing inside the owner's environment; the structural facts below were computed by ai.market conduit code and the findings are published unedited.

The badge title is `Scan findings — [UTC date]`. No public or internal user-facing copy may use an unqualified truth-status label for the listing or data.

The final merged disclaimer is:

> This is a seller-published, point-in-time scan of what the seller-designated source exposed through AIM Data on [scan date]; the source may change at any time, and this is not a continuing audit, warranty, compliance certification, or guarantee that data delivered later will match or remain available, accurate, complete, or unchanged. Verification does not assess data accuracy, legality, or fitness for any purpose.

The system does not attest:

- Future delivery equality or that bytes later delivered match the scanned artifact.
- Completeness, canonicality, or absence of a curated source.
- Immutability or current state after the scan window.
- Value-level accuracy, quality, legality, licensing, compliance, or fitness.
- Integrity of a seller-controlled agent binary without trusted hardware.

The known v1 residuals are explicit: a curated source and post-scan replacement cannot be detected, and determined agent tampering remains unmitigated. Those residuals are accepted only for the known-counterparty pilot.

## 6. Customer-to-cloud metadata manifest

> **CORE S3 UNANIMOUS SIGN-OFF REQUIRED — EXACT METADATA FIELD LIST THAT CROSSES THE WIRE.** No field may be added, widened, made more precise, or repurposed without a new unanimous CORE S3 decision. A reconstruction exercise against a representative fingerprint is a release gate; if any field exposes a raw cell value, that field is removed before launch.

The manifest is exhaustive. The D6 field is listed separately because it is seller-authored context, not scan-derived metadata.

| Transmitted field | Shape and source | One-line non-reconstructibility argument |
| --- | --- | --- |
| `verification_id`, `listing_id` | Opaque marketplace UUIDs | Identifiers bind records but contain no source content. |
| `owner_authorization_id`, `quote_id`, `idempotency_key` | Opaque marketplace-generated IDs | Random control-plane identifiers prove consent and deduplicate work without encoding source content. |
| `wire_manifest_version`, `corpus_disclosure_version`, `payment_disclosure_version`, `accepted_at_utc` | Fixed policy versions plus consent timestamp | Policy references and time record what the owner accepted, not any data record. |
| `requested_action` | Fixed enum `start`, `cancel`, `publish`, `decline`, or `withdraw` | A lifecycle command changes state but contains no source content. |
| `source_handle_id` | Opaque registered AIM Data handle ID | The opaque handle identifies a connection record, not any row or credential. |
| `artifact_locator_commitment` | HMAC-SHA-256 over the canonical resolved path or S3 connection/bucket/object key, keyed per installation | A keyed digest pins the exact locator but does not reveal or permit enumeration of that locator. |
| `content_sha256` | SHA-256 of the complete resolved file or object bytes | The one-way digest supports equality comparison but cannot reconstruct source bytes. |
| `spec_id`, `spec_version`, `spec_hash` | Signed scan-spec identity | These identify marketplace policy, not customer content. |
| `nonce_echo` | Fresh random challenge copied from the signed spec | A random freshness value contains no customer content. |
| `install_key_id`, `agent_version`, `connector_type`, `connector_version` | AIM Data receipt provenance | Software and key identifiers describe the scanner, not source records. |
| `started_at_utc`, `completed_at_utc`, `duration_ms` | Receipt timestamps and derived duration | Timing establishes the scan window without disclosing a source value. |
| `depth_class`, `row_count_algorithm_version`, `distinct_algorithm_version`, `histogram_version`, `numeric_bucket_version` | Fixed policy enums/versions | Fixed method labels disclose how facts were computed, not the underlying values. |
| `coverage.objects_discovered`, `coverage.objects_scanned` | Integer aggregate counts | Counts reveal only the number of reachable structural objects, not their records. |
| `coverage.objects_skipped_by_reason` | Counts keyed only by fixed reason enum such as `permission_denied`, `unsupported_type`, or `timeout` | Bucketed failure counts expose no object name, error string, or source value. |
| `coverage.skipped[]` | Install-keyed `object_id` plus fixed reason enum | The keyed object commitment and enum prove which structural object was skipped without revealing its name, path, error text, or records. |
| `objects[].object_id` | Install-keyed stable HMAC of canonical object identity | The commitment supports stable comparison while hiding database, table, file, or path names. |
| `objects[].column_names[]` | Exact column names in canonical order | Schema labels contain no cell values and cannot reconstruct a source record; source comments are excluded. |
| `objects[].column_types[]` | Declared and deterministic inferred type enum aligned to column names | Type classes constrain representation but reveal no actual cell value. |
| `objects[].null_rate[]` | Aggregate null count divided by row count, encoded at fixed precision | A per-column proportion cannot identify which row is null or recover a value. |
| `objects[].approx_distinct_count[]` | Deterministic approximate cardinality estimate and algorithm/error flag | An aggregate cardinality estimate reveals neither the distinct values nor their row membership. |
| `objects[].length_histograms[]` | Counts in fixed, coarse length buckets per supported column | Bucket counts reveal only value-length distribution and no string or row value. |
| `objects[].numeric_range_buckets[]` | Occupancy counts over policy-fixed numeric buckets; never observed min/max | Fixed bucket occupancy avoids transmitting exact extrema and cannot reconstruct individual numbers or rows. |
| `objects[].row_count`, `objects[].row_count_method` | Integer count plus fixed enum `exact`, `catalog_estimate`, or `deterministic_sample_estimate(n)` | The count and honest method describe volume without exposing any row content. |
| `fingerprint_hash`, `canonicalization_version` | SHA-256 over the canonical approved fact payload plus policy version | The digest detects fact changes but cannot reconstruct the canonical payload or source rows. |
| `receipt_signature`, `signature_algorithm` | Install-key signature over spec, nonce, local locator binding, content hash, coverage, and fingerprint | A signature proves receipt integrity and contains no source content beyond the separately approved signed fields. |
| `terminal_error_code` | Optional fixed enum when no report exists | A fixed code exposes outcome class without leaking a source name, path, query, or error string. |
| `d6_description` | Bounded seller-authored plain text, transported as quoted untrusted context | This is not derived from scanning; it is knowingly supplied by the owner and cannot grant access or reconstruct data unless the owner puts data into it. |
| `preview_requested` | Boolean selected before authorization | A boolean controls presentation only and contains no source content. |

The following are prohibited everywhere outside the customer environment: raw cell values, sample rows, verbatim values or strings, top-N values, value-frequency labels, source comments, source error strings, credentials, query text, data-plane payloads, and text-column min/max. Exact numeric min/max is also excluded; only policy-fixed bucket occupancy may cross.

Column names are allowed by the frozen baseline but remain untrusted source-derived text. They are escaped for rendering, quoted as data in the narrative prompt, and denied any control role. If the CORE S3 reconstruction review rejects exact column names, the field list must return to Gate 1; the builder may not silently hash or omit them because that would change the approved product artifact.

## 7. Facts, narrative, and D6 isolation

Fact fields are written only by deterministic conduit code and become immutable after receipt validation. allAI cannot write or amend the fingerprint, coverage, methods, timestamps, artifact binding, or charge inputs.

The narrative is a separate, clearly labeled `allAI interpretation` field. Its only evidence inputs are the approved fingerprint and the D6 description. The system prompt places D6, column names, and every other source-derived string in quoted data sections; the narrative pass has no tools and no scan, payment, or publication capability.

A grounding validator applies before capture and seller reveal:

- Every identifier and number in the narrative must exist verbatim in the approved fingerprint.
- A missing or transformed identifier, number, compliance claim, or unsupported factual assertion fails validation.
- Slice 1 makes one bounded narrative pass. If it fails validation, the complete result becomes fingerprint-only with a fixed `allAI interpretation withheld because grounding validation failed` notice. No second pass may breach the hard budget.
- Seller context is not republished. The public artifact shows only `seller_context_provided: true|false`.

Hostile fixtures must place instructions in D6, object identifiers, and column names. They pass only when they cannot alter traversal roots, discovered/scanned coverage, fact values, output schema, token cap, charge, capture timing, seller election, or publication state. A fixed fixture on unchanged data must produce byte-identical facts and fingerprint hashes across repeated scans.

## 8. Verification artifact schema

One immutable `VerificationEpoch` record represents one initiated scan. The v1 schema reserves additive epoch fields now so slice 2-3 drift checks and fulfillment-time buyer-side corroboration do not require replacing the artifact model.

| Field | Provenance | Visibility and rule |
| --- | --- | --- |
| `artifact_version`, `verification_series_id`, `epoch_id` | Marketplace | Public opaque IDs; series groups additive epochs. |
| `epoch_kind` | Marketplace | v1 is `seller_scan`; reserved values are `drift_recheck` and `buyer_fulfillment_corroboration`. Reserving values does not implement those deferred flows. |
| `prior_epoch_id`, `corroborates_epoch_id` | Marketplace | Nullable in v1; additive links for future epochs. |
| `listing_id`, `source_handle_id` | Marketplace/AIM Data | Listing binding; source handle remains opaque publicly. |
| `resolved_artifact_commitment`, `content_sha256` | Signed AIM Data receipt | Internal attestation evidence; content hash may be shown as a shortened reference. |
| `spec_id`, `spec_version`, `spec_hash`, `depth_class` | Marketplace scan spec | Public method provenance. |
| `scanned_at_utc`, `completed_at_utc`, `duration_ms` | Validated signed receipt | Public point-in-time scan window. |
| `agent_version`, `connector_type`, `connector_version`, `install_key_id` | Signed receipt | Versions public; install key ID internal. |
| `coverage` | Deterministic conduit | Public discovered/scanned/skipped counts and fixed reasons. Any skipped object remains visible; unsupported partial output cannot publish. |
| `fingerprint`, `fingerprint_hash`, method versions | Deterministic conduit | Public facts from section 6 and integrity hash. |
| `narrative`, `narrative_state` | allAI plus grounding validator | Public and labeled, or fixed fingerprint-only notice. Cannot write facts. |
| `seller_context_provided` | Marketplace | Public boolean only; D6 text is not public. |
| `preview_requested`, `schema_preview`, `row_counts` | Seller choice plus deterministic conduit | Public only when the pre-run D8 option is true; derived from the same fingerprint. |
| `listing_claim_comparison` | Deterministic facts mapped by allAI | Public, grounded, and allowed to contradict seller listing claims. |
| `publication_state`, `published_at_utc`, `declined_at_utc`, `withdrawn_at_utc`, `superseded_by_epoch_id` | Marketplace lifecycle | Full-state audit; declined and never-published records stay private. |
| `metered_input_tokens`, `metered_output_tokens`, `provider_cost_usd`, `charge_usd` | Cloud meter plus Stripe | Seller-visible receipt; not required on the public listing artifact. |
| `corpus_event_id`, `corpus_capture_state` | BQ-S1396 | Internal pseudonymous reference and append outcome. |
| `receipt_signature`, `receipt_key_id` | AIM Data receipt validation | Internal proof reference. |

The public result has three visually distinct provenance groups: `Facts computed by AIM Data`, `allAI interpretation`, and fixed marketplace limitations. Seller corrections cannot edit a scan result; a correction requires changing the source or listing claim and initiating a new paid run.

## 9. Coverage and honest depth

The free local probe determines source reachability, object count, size class, supported connector capabilities, and the complete depth class that fits the maximum authorized inference input. It sends only the corresponding approved aggregate fields after owner consent.

Before payment authorization, the seller sees the named depth class and its exact policy. A depth class may lower aggregate precision uniformly, such as fixed wider numeric buckets or an explicitly estimated row-count method, but it must traverse every reachable supported object in the registered root. It cannot silently omit objects or let D6 select exclusions. If no supported depth class can produce a complete artifact within the USD 25 authorization and hard token budget, the run is refused before authorization.

`coverage` always reports objects discovered, scanned, and skipped by fixed reason. A skipped object does not become invisible. Publication is allowed only when the completed result includes the entire report for the selected, disclosed depth class. No seller or model can delete a skip, fact, contradiction, or limitation.

## 10. Payment charge state machine

> **CORE S3 UNANIMOUS SIGN-OFF REQUIRED — PAYMENT CHARGE STATE MACHINE, TRANSITIONS, METER SOURCE, AND CAPTURE MECHANISM.** Production execution is blocked until unanimous sign-off is recorded. The builder may not substitute automatic capture, client-reported metering, post-result capture, incremental authorization, or a different failure/refund policy.

The meter source is exclusively provider usage returned for the single cloud-side allAI narrative request and recorded at ai.market's billing boundary. Local probing and deterministic scanning consume no billed tokens. `provider_cost_usd` uses the provider/model price pinned for the job. `charge_usd = min(authorized_usd, max(1.00, round_half_up_to_cents(2 * provider_cost_usd)))`, and `authorized_usd` is never greater than USD 25.

| State | Entry condition | Permitted transition and financial effect |
| --- | --- | --- |
| `CREATED` | Owner selects source, listing, D6 context, and D8 option. | Run free local probe; no Stripe object and no charge. |
| `QUOTED` | Probe selects an honest supported depth class and produces a maximum quote of USD 1-25. | Owner accepts the quote and both separated consents, or aborts with no charge. Refuse pre-run if no complete depth class fits. |
| `AUTHORIZING` | Owner accepted quote. | Create one Stripe PaymentIntent with manual capture, the quoted amount, opaque `verification_id`, and idempotency key. No source or D6 metadata enters Stripe. |
| `AUTHORIZED` | Stripe confirms a capturable authorization. | Release the signed scan spec. A scan must never start before this state. Authorization failure terminates `AUTH_FAILED` with no scan or charge. |
| `SCANNING_LOCAL` | AIM Data accepted the signed spec. | Produce deterministic report, or honor a pre-completion cancel. Seller cancel before cloud inference terminates `CANCELLED_VOIDED`; the hold is voided and nothing publishes. Source or platform failure terminates `FAILED_VOIDED`; the hold is voided. |
| `NARRATING_CLOUD` | Valid signed report and nonce received; hard token budget fixed from authorization. | Make one bounded allAI request. A cancel request during this atomic pass prevents seller reveal and publication but does not interrupt metering; after validation it follows normal completion/capture and then terminates as declined. Our-fault inference or validator-system failure terminates `FAILED_VOIDED`. A grounding rejection is not system failure: the complete result is fingerprint-only. |
| `CAPTURE_PENDING` | Deterministic report is complete and narrative is grounded or replaced by the fixed fingerprint-only notice. | Compute charge solely from cloud provider usage, then make one idempotent manual capture for at most the authorized amount. The seller cannot see results in this state. Capture failure leaves results hidden and requires payment reconciliation; it cannot publish. |
| `CAPTURED` | Stripe confirms the one capture. | Reveal the immutable complete result to the seller. No refund is due for a completed scan. Owner chooses full publication or decline. |
| `PUBLISHED` | Owner elects full publication. | Publish atomically. Charge stands. A later published scan may supersede it; each completed run is separately charged. |
| `DECLINED` | Owner declines, including a cancel requested during the atomic narrative pass. | Publish nothing; listing remains without a scan-findings badge. Charge stands. |
| `WITHDRAWN` | Owner withdraws an already published result. | Remove the report from the active badge, show the 30-day withdrawal marker, and retain the completed charge. |
| `SUPERSEDED` | Owner publishes a later completed epoch. | Replace the active badge atomically; retain prior artifact and charge. |
| `AUTH_FAILED`, `CANCELLED_VOIDED`, `FAILED_VOIDED` | Terminal pre-completion outcome. | No report or partial result publishes. Any authorization is released/voided; no refund workflow is needed because nothing was captured. Corpus capture still records the minimized outcome. |

Webhook reconciliation and the `verification_id` idempotency key must prove one PaymentIntent and at most one capture per epoch. A completed scan is charged before the seller sees findings regardless of later publish, decline, withdrawal, or supersede. Our-fault failures void the hold. There are no refunds on completed scans.

The pre-scan screen states the exact maximum authorization, twice-token-cost formula, USD 1 floor, USD 25 cap, cloud-only meter source, completion-based charge, results-hidden-until-capture rule, no-refund posture for completed scans, void-on-our-fault outcome, and corpus terms.

## 11. Publication and badge lifecycle

Starting a new scan leaves the current published result in place. Only a later completed, captured, and explicitly published epoch atomically supersedes it. The active badge shows:

- `Scan findings — [UTC date]`.
- The complete deterministic findings and any grounded allAI interpretation.
- Coverage: objects discovered, scanned, and skipped with fixed reasons.
- The exact row-count method wherever a count appears.
- The D8 schema preview and row counts only when the seller selected that option before the run.
- The fixed disclaimer in section 5.

Decline publishes nothing. No prior failed, cancelled, or declined result becomes buyer-visible. Withdrawal removes the report from the active badge and displays the fixed 30-day marker. After 30 days the listing simply has no active scan findings, while the internal immutable record remains. Superseded records remain internally linked; public scan-history UI is deferred.

The scan date and disclaimer are the only v1 freshness presentation. There are no freshness tiers, automatic drift labels, transaction-time checks, or continuous-monitoring claims in Slice 1.

## 12. Corpus capture and consent

Every initiated epoch emits a BQ-STRUCTURE-METADATA-CORPUS-CAPTURE-S1396 record, including published, declined, cancelled, failed, withdrawn, and superseded outcomes. Capture begins with Slice 1.

The pre-scan screen presents corpus consent separately from the later publication election. Initiating a scan requires affirmative acknowledgement of this fixed disclosure:

> Every scan, including one you later decline, cancel, fail, withdraw, or supersede, contributes minimized and pseudonymized structure metadata and outcome records to ai.market's internal data-understanding corpus. No raw data or sample values leave your environment, and nothing becomes public unless you separately choose to publish a completed result.

Corpus records use pseudonymous verification, listing, source-handle, and install references. They store the approved fingerprint, scan spec and policy hashes, minimized outcome, grounded narrative or failure state, publication decision, meter totals, and provenance. They do not store raw data, exact local locators, credentials, source error strings, or public seller identity.

D6 is processed ephemerally for the narrative pass. At rest, only a redacted form is stored: secrets and direct identifiers are removed under a fixed redaction policy, with a redaction-policy version and hash retained. The unredacted D6 field is not copied into Stripe, logs, public artifacts, or general analytics.

Access to scan corpus content is deny-by-default, role-scoped, audited, and limited to the S1396 pipeline and explicitly authorized corpus operators. Publication consent does not grant corpus access, and corpus consent does not publish anything. A declined scan is never reachable through a buyer-facing path.

## 13. Integrity and gaming

| Attack | Binding mitigation | Honest v1 residual |
| --- | --- | --- |
| Curated source or staged view | Bind spec and receipt to the registered fulfillment source handle; pin the exact resolved artifact and content hash; scan the full supported root; publish coverage. | The seller may curate what that handle exposes. v1 cannot discover data withheld outside the registered source. |
| Post-scan swap | Pin artifact content hash and show scan time; supersede only with a new run. | Content behind the same handle may change after the scan and before delivery without detection. |
| D6 or schema-name prompt injection | Signed policy fixes scope; facts are LLM-independent; quote untrusted text; no narrative tools; validate grounding; hostile fixtures gate release. | Seller wording may influence narrative emphasis, but cannot change a fact or lifecycle state. |
| Re-run shopping | Facts and seed are deterministic; every completed run is paid; every run enters S1396; only a complete result may publish. | A seller may improve or change the source, decline an earlier result, then publish a later result. Buyers see the current scan date, not private attempts. |
| Selective editing | Immutable artifact and atomic full publication. | Seller retains the frozen right to publish or decline. |
| Agent tampering | Signed spec, nonce, install-key receipt, deterministic consistency tests, and known-counterparty pilot. | A determined owner controlling the host can tamper without trusted hardware. Accepted only for the pilot. |
| Metadata leakage | Exact allowlist, fixed aggregate methods, no values/samples/errors, S3 reconstruction review, strict corpus access. | Column names can carry sensitive or adversarial text; they remain allowed only if unanimous S3 review accepts them. |
| Charge manipulation | Cloud-only meter, manual capture, hard budget, idempotency, results hidden until capture. | Correctness still depends on Stripe reconciliation and pinned provider pricing. |

## 14. Slice 1 scope

In scope:

1. One connector matched to the eolymp source shape and launch limited to that supported AIM Data-reachable source class.
2. Scan spec v1, signed spec, nonce, install-key receipt, exact resolved-artifact pin, content hash, deterministic seeding, deterministic facts, and one bounded cloud allAI narrative pass.
3. The exhaustive section 6 fingerprint and coverage fields, with LLM-independent computation and grounding validation.
4. Free local probe, honest depth class or refusal, quote, Stripe manual-capture pre-authorization, hard cloud token budget, capture before reveal, and the complete state machine in section 10.
5. Radical advance disclosure and separated corpus/publication consent.
6. Seller review followed by atomic publish or decline.
7. Badge with findings, scan date, coverage, row-count methods, and fixed disclaimer.
8. Cancellation, 30-day withdrawal marker, and supersede by a newly published run.
9. D8 option producing the schema-level preview and row counts from the same report, closing the T-2026-000689 minimum set.
10. S1396 capture from day one for every scan outcome, with minimization, pseudonymization, D6 redaction, and strict access control.
11. Removal of quality scores from listing pages.
12. AIM Data entry at listing time and later.

Explicitly deferred:

- Drift re-checks, scheduled re-scans, automatic change detection, and staleness tiers.
- Transaction-time re-verification.
- Buyer-side fulfillment fingerprint corroboration; this is the planned slice 2-3 use of the epoch schema.
- Attestation-crypto hardening beyond the signed v1 spec, nonce, and install-key receipt. It must land before general availability.
- Multi-source or composite listings.
- Public scan-history or attempt-count UI.
- Buyer-triggered runs.
- Broad connector coverage beyond the one eolymp-matched connector.
- Quality scoring, compliance certification, legal classification, or fitness judgments.

## 15. Acceptance criteria

Each criterion is independently checkable.

1. A repository search finds no raw cell, sample-row, top-N value, verbatim source value, source error, text min/max, or data-plane payload in any S1590 customer-to-cloud message or persisted cloud record.
2. The implemented customer-to-cloud schema equals section 6 exactly, and unanimous CORE S3 sign-off on that field list is linked in the implementation review.
3. A reconstruction review against representative eolymp fingerprints cannot recover any raw value. Any recovered raw value blocks launch and removes the responsible field through a new Gate 1/S3 decision.
4. Two scans of unchanged source bytes with the same spec produce byte-identical fact payloads and fingerprint hashes.
5. The signed receipt verifies the signed spec hash, nonce, install key, exact local artifact binding, content hash, scan window, coverage, and fingerprint hash. A stale nonce, changed spec, changed report byte, or wrong install key is rejected.
6. A1 integration tests prove the scan resolves the same registered `listing_id` source handle as fulfillment and pins the exact resolved local path or S3 connection/bucket/object key plus content hash before reading.
7. A local-resolution fixture in which the preferred file changes under the same handle produces a different locator commitment or content hash; it never reuses the prior artifact identity.
8. Coverage fixtures include an inaccessible object and show discovered, scanned, and skipped-by-fixed-reason counts. No object name or free-form error crosses for the skipped object.
9. Every row count carries `exact`, `catalog_estimate`, or deterministic sample-estimate method and parameters; no estimate is presented as exact.
10. D6, object-name, and column-name hostile fixtures cannot change scope, coverage, facts, schema, token cap, charge, capture timing, seller election, or publication state.
11. Every identifier and number in a published narrative exists in the fingerprint. A failed grounding check yields the fixed fingerprint-only notice and no second model pass.
12. The pre-run probe either names a complete supported depth class with exact limitations or refuses before Stripe authorization. Budget exhaustion cannot yield partial publication.
13. The payment implementation equals section 10 and links unanimous CORE S3 approval. Tests prove no scan before authorization, no capture above authorization or USD 25, no client-reported token charge, no result reveal before capture, and at most one capture per epoch.
14. Authorization failure, pre-inference seller cancel, source failure, and our-fault failure publish nothing and void the hold. A completed captured scan is not refunded after publish, decline, withdrawal, or supersede.
15. A completed result is charged before seller reveal. Publish exposes every fact, contradiction, coverage limitation, narrative state, and disclaimer atomically; decline exposes none and leaves no active badge.
16. The listing and API contain no unqualified truth-status string, numeric quality score, compliance claim, future-delivery equality claim, or continuous-monitoring claim.
17. The badge uses `Scan findings — [UTC date]`, shows coverage and row-count methods, links the full report, and renders the exact disclaimer in section 5.
18. Withdrawal shows the exact marker for 30 days; supersede switches the active artifact only after the later run is completed, captured, and explicitly published.
19. The D8 option is fixed before authorization and produces schema preview and row counts from the same fingerprint with no second scan or model-authored facts.
20. Published, declined, cancelled, failed, withdrawn, and superseded fixtures each append a minimized pseudonymous S1396 event. Publication and corpus decisions are separate, and declined content has no buyer-facing path.
21. Corpus tests prove unredacted D6, exact local locators, credentials, raw values, and free-form source errors are absent; access is deny-by-default and audited.
22. The v1 persisted schema accepts linked `drift_recheck` and `buyer_fulfillment_corroboration` epoch records without changing or rewriting the original seller-scan epoch, while those flows remain disabled in Slice 1.
23. Unsupported connectors cannot start or display scan findings. AIM Data exposes the supported entry at listing time and later.
24. Focused unit, contract, injection, determinism, payment idempotency/webhook, corpus-access, and end-to-end pilot tests pass before production review.

## 16. Gate sequence and release blockers

1. Gate 1 approves this design artifact.
2. CORE S3 unanimously approves the exact section 6 wire manifest and section 10 payment state machine before implementation may be production-enabled.
3. Security review passes reconstruction, hostile-input, signature/nonce, secret-redaction, and corpus-access tests.
4. Payments review passes manual-capture, provider-price pinning, hard-budget, idempotency, webhook, void, and hidden-results tests.
5. Static review, deployment proof, and live browser verification remain separate evidence. None substitutes for another.
6. The known-counterparty pilot may proceed only after Gates 1-4. General availability remains blocked on attestation-crypto hardening and a separate unanimous decision for any widened metadata or connector surface.

## 17. Risks and falsifiers

| Decision at risk | Risk | Evidence that falsifies the decision |
| --- | --- | --- |
| Exact metadata allowlist preserves CORE S1/P8 | Aggregate or schema fields may expose real values or permit reconstruction in a narrow dataset. | The reconstruction review recovers a raw value or individual record. Remove the field and return the changed manifest to Gate 1 and unanimous S3 review. |
| Deterministic fingerprinting defeats unchanged-data shopping | Connector ordering, approximate algorithms, or floating-point aggregation may vary. | Two unchanged-source runs under the same spec produce different canonical facts or fingerprint hashes. Fix determinism before launch. |
| A1 supports source identity | Fulfillment and scanning may resolve different handles or concrete artifacts. | An integration fixture resolves a scan handle different from the listing fulfillment handle. Block publication until the binding is corrected; do not weaken copy to a generic process claim. |
| Exact artifact pin closes handle ambiguity at scan time | The resolver may select a different file or object during the scan. | Pre/post content hash or locator differs within one run. Fail the scan and void the hold. |
| Cloud-only metering supports honest twice-cost pricing | Provider usage or pinned price may be absent or irreconcilable. | Any completed job lacks provider usage, price version, or an independently recomputable charge. Void rather than estimate or trust the client. |
| Manual capture fits existing Stripe rails | Account, payment method, authorization window, partial capture, or webhook behavior may differ. | Sandbox and production-mode tests cannot authorize the quote and capture a smaller idempotent amount. Do not substitute a payment mechanism without a new Gate 1/S3 decision. |
| Fingerprint-only fallback is a complete result | Buyers may find a fact-only report insufficient to support the listing. | Pilot evidence shows the report is unusable without narrative. Improve grounding in a later bounded design; do not publish ungrounded prose. |
| Known-counterparty pilot can accept agent tampering residual | Host compromise or manipulated reports may be plausible even in the pilot. | Receipt anomalies, source-owner behavior, or security review shows the residual is unacceptable. Pause the pilot until stronger attestation lands. |
| Epoch-compatible schema is additive | Future buyer-side or drift records may require rewriting v1 facts. | Slice 2 design cannot express comparison and provenance through new linked epochs. Extend with additive fields; never mutate the original epoch. |

## 18. Author's reservations

I have no reservation about the binding D1-D8, D10, Q1-Q3 decisions or the converged Council architecture. Two implementation surfaces remain intentionally blocked pending the required unanimous CORE S3 sign-offs: the exact metadata manifest and payment state machine. A1 is verified at handle level, while future byte equality and agent integrity remain honestly unproven.
