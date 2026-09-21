# BQ-LISTING-LICENSES-S1735 Gate 2 implementation specification

**Status:** Gate 2 **DRAFT r2** (r1 `67c26cf9`: GLM REVISE — `council/glm/response-20260922-000305-307373.md`; DeepSeek APPROVE_WITH_MANDATES — `council/deepseek/response-20260921-235022-303378.md`; Gemini APPROVE_WITH_MANDATES — `council/gemini/response-20260922-000320-469178.md`. Every finding folded in this revision by Mars (wording/scope fold, no design change; MP authored r1). Fold log at the end of §1.) No build dispatch and no production enablement until this exact document commit is approved unanimously at Gate 2 and the BQ `gate2` state matches it.
**Build Queue entity:** `build:bq-listing-licenses-s1735`.
**Design authority:** `specs/BQ-LISTING-LICENSES-S1735-GATE1.md` on `origin/docs/listing-licenses-s1735-gate1`, runbooks commit `df32c7c0416103630759f6f7bc32a71b91c95d6b`, approved 3/3 on design version `2556ec17`; its §§3–7 and mandates M1–M12 are binding and are not reopened here.
**Backend ground truth:** `ai-market-backend` commit `031c837a7ba64fab37c28af3671a7e0758212502`. The author task contains this full SHA; the session request said `...2500`, which is not a Git object in the named checkout. All backend file:line citations below are therefore against the task's existing `...2502` object.
**Surface pins read for authoring:** `ai-market-frontend` `dc4ce72db4700dff1428aed60142732361cb6bc8`; `aim-data` `cd56a13b4d333c9d6849017368c218e7dfb1b1fa`.
**Process authority:** `runbooks/council-gate-process.md` E-02. MP authors and builds; MP does not vote. The current Council is GLM, DeepSeek and Gemini; every implementation chunk requires unanimous 3/3 CORE S3 Gate 3 review from that panel on its exact candidate SHA before merge. CC is non-Council and cannot unlock a gate.
**Max decisions consumed:** Event Ledger `551972f8`: launch Standard plus seller's own licence; add Open/CDLA only on request; AI training defaults to yes; United States/New York law; no lawyer review; personal data prohibited in v1; no cutover prompt for inherited listings, which use the platform-terms bump in §11.

## 1. Scope, invariants and mandate map

This specification adds one licence selection and signature chain from listing submission through every purchase and delivery door. It does not add negotiation, private offers, a DPA path, watermarking, a subscription licence, translated contract text, or an Open licence card. `LISTING_LICENSES_ENABLED` is a new backend flag with default `false`. With the flag off, new endpoints are 404, publish and checkout retain their pre-feature schema and behaviour, seeded records are inert, background work is absent, and existing tests remain byte-for-byte compatible. Migrations may be present while the flag is off but do not make an inherited listing purchasable.

| Mandate | Owning chunk | Named proof |
| --- | --- | --- |
| M1 single constructor | B | `tests/test_listing_license_order_constructor.py::test_every_order_insert_is_owned_by_order_service` plus wallet-purchase E2E |
| M2 creation refusal | B | `tests/test_listing_license_order_constructor.py::test_refusal_matrix_is_atomic` |
| M3 transaction-neutral recorder | B | `tests/test_listing_license_acceptance.py::test_recorder_never_commits_and_rolls_back_with_order` |
| M4 every issuance door | C | `tests/test_listing_license_delivery_gate.py::test_generated_route_inventory_refuses_missing_and_terminated_acceptance` |
| M5 legacy JWT door | C | `tests/test_listing_license_delivery_gate.py::test_legacy_orderless_jwt_route_is_absent` |
| M6 legal identity | A, B | `tests/test_listing_license_identity.py::test_precedence_conflict_and_backfill` |
| M7 canonical hashing | A | `tests/test_listing_license_hash_vectors.py::test_published_vectors` plus frontend and AIM Data vector tests |
| M8 seller acceptance | A, D, F | `tests/test_listing_license_seller_acceptance.py::test_shadow_mode_cannot_bypass_seller_acceptance` |
| M9 audited termination | E | `tests/test_listing_license_termination.py::test_only_status_transitions_and_event_is_written` |
| M10 x402 | C | `tests/test_listing_license_x402.py::test_x402_is_hard_disabled_even_when_old_flags_are_true` |
| M11 custom hygiene | D | `tests/test_custom_license_upload.py::test_hygiene_matrix_and_immutable_content` |
| M12 reviewed text and surfaces | A, D, E, F | `tests/test_listing_license_seed_documents.py::test_seed_text_equals_gate2_blocks` and cross-surface contract tests |

**r1 fold log (2026-09-22).** GLM F1 (imported CC/CC0 instrument undefined): closed by mapping every inherited value to Standard and keeping the old value as provenance only (§4.3, §11) — Max decision 6. GLM F2 (public sample door): closed by the listing-level `require_listing_license_snapshot` rule (§6). GLM F3 / DeepSeek F1 / Gemini F1 (buyer platform-terms gate): retained, shadow-proof, in the refusal matrix (§5). GLM F4 / DeepSeek F2 / Gemini F2 (`sanctions_screening_ref`): nullable, deferred (§4.1, §9). GLM F5 / DeepSeek F3+F5 / Gemini F3+F5 (`terms_acceptance`, `allai_event_ledger` FK): corrected (§4.1). GLM F6 / DeepSeek F4 / Gemini F4 (PDF hash): fully specified with a sixth vector (§3.1). GLM F7 / DeepSeek F6 / Gemini F6 (English canonical): added to hygiene (§9). GLM F8 / DeepSeek F7 / Gemini F7 (`account-teardown.md`): chunk G (§12.7). GLM F9 (x402 test): split assertions (§12.3).

## 2. Instruments and customer copy (M12)

The fenced blocks in §2 are normative seed inputs, not illustrative copy. Seed extraction removes the opening and closing fence only, converts CRLF/CR to LF, applies Unicode NFC, removes trailing spaces on every line, and ensures exactly one terminal LF. No renderer may smart-quote, wrap, translate or otherwise change the bytes used for hashing.

### 2.1 `ai.market Standard Data Licence v1.0`

`STANDARD_TEMPLATE`:

```text
ai.market Standard Data Licence v1.0

This licence is agreed between the seller identified in the signed licence record (the “Licensor”) and the buyer identified in that record (the “Licensee”). It applies only to the dataset version, listing and order identified in that record, together with a later dataset version delivered under that same order (the “Data”). The effective date is the buyer's recorded acceptance time, and the same recorded terms govern any such later version.

1. Licence grant. Subject to payment and this licence, the Licensor grants the Licensee a perpetual, non-exclusive and non-transferable licence to possess, copy, modify and use the Data for the Licensee's internal business purposes. The Licensee may permit its affiliates and contractors to use the Data only while acting for the Licensee, only for those purposes and only under confidentiality and use restrictions at least as protective as this licence. The Licensee remains responsible for them. No other sublicence or transfer is permitted.

2. Permitted work and ownership. The Licensee may analyse the Data and use it to develop, operate and improve products, services, reports, statistics, models, model weights, evaluations, outputs and other derived works. As between the parties, the Licensee owns its analyses, models, outputs and derived works and may commercialise them, provided that a recipient cannot extract or reconstruct the Data, or a material substitute for the Data, from them. The Licensor retains all rights in the Data that this licence does not expressly grant.

3. AI and machine learning. {{AI_TRAINING_CLAUSE}}

4. Restrictions. The Licensee must not redistribute, publish, sell, rent, sublicense or otherwise make the Data itself available to another person except as expressly allowed for affiliates and contractors in section 1. The Licensee must not use the Data to identify or re-identify an individual, combine it with other information for that purpose, or attempt to defeat access, privacy or security controls. Applicable law always applies.

5. Samples and previews. Any sample, preview, schema extract or other material made available before purchase is for evaluation of the listing only. It may not be used in production, redistributed, used to train or evaluate a model, or retained after the evaluation ends.

6. Licensor promises. The Licensor promises that it has the rights needed to offer and license the Data; that it sourced and provides the Data lawfully; that providing and using the Data as this licence permits does not knowingly infringe another person's rights; and that the Data contains no regulated personal data or special-category data. The Licensor also promises that the listing's express statements about the Data are materially accurate when delivered.

7. Inspection, warranty and remedy. The Licensee has seven calendar days after first delivery to inspect the Data and notify ai.market of a material failure to match the listing's express statements. Except for the promises in section 6, the Data is provided as available, without any promise of completeness, accuracy, fitness for a particular purpose, uninterrupted availability or a particular result. For a timely valid notice, the Licensor may either correct or replace the affected Data within a reasonable time or approve a refund. That fix-or-refund choice is the Licensee's exclusive remedy for a Data defect. After seven days, acceptance is final except for fraud, wilful misconduct or rights the law does not allow the parties to exclude.

8. Confidentiality. Each party must protect the other party's non-public information with reasonable care and use it only to perform this licence. This duty does not cover information that was lawfully known without restriction, becomes public without breach, is independently developed, or is lawfully received from another source. A legally compelled disclosure is permitted after notice where lawful.

9. Liability. To the maximum extent permitted by law, each party's total aggregate liability arising from this licence, including liability relating to the promises in section 6, is limited to three times the fees paid for the affected order. The cap does not apply to that party's wilful misconduct or breach of section 8. Neither party is liable for indirect, incidental, special, exemplary or consequential loss, or lost profits or revenue, except where the law does not permit that exclusion.

10. Refund and termination. This licence is perpetual unless the affected order is refunded. On a refund, the licence terminates automatically. Within 30 days after notice of the refund, the Licensee must delete the Data and all copies under its control and confirm deletion through ai.market. The Licensee need not delete models, outputs or derived works that do not contain and cannot be used to extract or reconstruct the Data. Accrued payment, confidentiality, liability, ownership and deletion obligations survive as their nature requires.

11. Notices and marketplace role. Contract notices, defect notices, refund requests and termination communications must be sent through ai.market. ai.market provides the marketplace and record but is not a party to this licence, does not license the Data, gives no legal advice and makes no representation that this licence is suitable for either party. The marketplace terms govern marketplace operation, including non-custodial delivery, the 5% commission, refunds and dispute holds; if this licence conflicts with those operational rules, the marketplace terms prevail for those matters.

12. General. This licence and its signed record are the entire agreement between the Licensor and Licensee about the licensed Data, subject to the marketplace terms described in section 11. A waiver must be written and applies only once. An invalid provision is narrowed or removed only as needed, without affecting the rest. Neither party may assign this licence without the other's written consent, except with a merger or sale of substantially all of its relevant business if the successor accepts this licence. There are no third-party beneficiaries.

13. Governing law and courts. New York law governs this licence, without regard to conflict-of-law rules. The state and federal courts located in New York County, New York have exclusive jurisdiction, and each party consents to those courts.
```

The template token is replaced before hashing and display by exactly one of these clauses:

`STANDARD_AI_TRUE`:

```text
The Licensee may use the Data to train, fine-tune, test and evaluate artificial-intelligence and machine-learning systems, subject to every other restriction in this licence.
```

`STANDARD_AI_FALSE`:

```text
The Licensee must not use the Data to train, fine-tune, test or evaluate artificial-intelligence or machine-learning systems. This does not prohibit ordinary analysis that does not train, fine-tune, test or evaluate such a system.
```

### 2.2 `ai.market Marketplace Listing Covenant v1.0`

`COVENANT_V1`:

```text
ai.market Marketplace Listing Covenant v1.0

By submitting or publishing a listing, the seller identified in the acceptance record promises to ai.market and to each buyer of that listing that: (1) the seller has all rights and authority needed to list, deliver and license the dataset; (2) the dataset was lawfully sourced and may lawfully be supplied for the uses the selected licence permits; (3) the dataset contains no regulated personal data or special-category data; (4) the listing and its stated facts are not materially misleading; and (5) every sample, preview or schema extract is supplied for evaluation only and may not be used in production, redistributed, used to train or evaluate a model, or retained after evaluation.

The seller accepts that the ai.market marketplace terms prevail for non-custodial delivery, the 5% commission, refunds, dispute holds and the evaluation-only sample rule. The seller will not place a conflicting term in a custom licence. Contract, defect, refund and termination notices between seller and buyer must be made through ai.market only. This covenant applies to every version sold while the recorded acceptance is current and survives for purchases already made.
```

### 2.3 `ai.market AI-Training Rider v1.0`

This rider is attached to a seller's own licence; it never changes or interprets the uploaded document.

`RIDER_AI_TRUE`:

```text
ai.market AI-Training Rider v1.0 — Permitted
The Licensor permits the Licensee to use the licensed dataset to train, fine-tune, test and evaluate artificial-intelligence and machine-learning systems, subject to the seller's own licence and the ai.market Marketplace Listing Covenant. If the seller's own licence expressly prohibits that use, the prohibition controls and the listing must not be published until the conflict is removed.
```

`RIDER_AI_FALSE`:

```text
ai.market AI-Training Rider v1.0 — Not permitted
The Licensee must not use the licensed dataset to train, fine-tune, test or evaluate artificial-intelligence or machine-learning systems. This restriction supplements the seller's own licence; if that licence is more restrictive, the more restrictive term controls.
```

### 2.4 Exact summaries and notices

**Buyer summary — ai.market Standard Data Licence v1.0 (not the contract):**

> Not the contract — read and download the full licence before accepting.  
> You may use this delivered dataset version inside your business, including through affiliates and contractors working for you.  
> You own and may commercialise your models, outputs and derived work if the raw dataset cannot be extracted or reconstructed.  
> You may not redistribute or resell the dataset itself, or try to identify or re-identify people.  
> AI/ML training is **{permitted|not permitted}** for this listing.  
> You have seven days to report a material mismatch; the remedy is fix or refund, and a refund ends the licence and requires deletion within 30 days.  
> ai.market is not a party and gives no legal advice; New York law governs.

**Seller summary — ai.market Standard Data Licence v1.0 (not the contract):**

> Not the contract — read the full licence before choosing it.  
> You remain the owner and licensor of the delivered dataset version.  
> The buyer may use it internally and commercialise models, outputs and derived work that do not expose or reconstruct the raw data.  
> The buyer may not redistribute or resell the dataset itself, and AI/ML training follows your displayed switch.  
> You promise that you have the rights, sourced the data lawfully, stated the listing facts accurately and included no regulated personal or special-category data.  
> A material mismatch reported within seven days is remedied by fix or refund; liability is capped as the full licence states.  
> ai.market is not a party and gives no legal advice; New York law governs.

**Amber custom-listing notice:** “The seller's own terms. ai.market did not write these; review them before you accept. The separate ai.market AI-Training Rider and Marketplace Listing Covenant also form part of your record. ai.market is not a party and gives no legal advice.”

**Green Standard badge:** “ai.market standard terms — the same balanced terms every seller on ai.market uses. ai.market is not a party and gives no legal advice.”

**Platform-terms addition (one sentence, verbatim):** “Listings without a chosen licence are offered under the ai.market Standard Data Licence with AI training permitted, and the seller accepts the ai.market Marketplace Listing Covenant for them.”

`CURRENT_TERMS_VERSION` changes from `1.0` to **`1.1`** (the current value is `1.0` at `app/core/config.py:155`).

## 3. Canonical hashing and vectors (M7)

### 3.1 Byte-exact algorithm

`sha256` fields are lowercase 64-character hexadecimal. `LP(x)` is an unsigned 64-bit big-endian byte length followed by `x`. Every string is converted to Unicode NFC and UTF-8. Document text additionally converts CRLF/CR to LF, removes trailing horizontal whitespace from each line and has exactly one final LF. JSON is RFC 8785 JCS after NFC-normalising every key and string value; duplicate keys, floats, unknown keys and any value other than the declared schema fail closed. Boolean is JSON `true` or `false`, never a string or integer.

The constructions are:

```text
license_sha256  = SHA256(LP("ai.market/license/v1")  || LP(code) || LP(version) || LP(canonical_text) || LP(JCS(params)))
rider_sha256    = SHA256(LP("ai.market/rider/v1")    || LP("ai-training") || LP("1.0") || LP(canonical_text) || LP(JCS(params)))
covenant_sha256 = SHA256(LP("ai.market/covenant/v1") || LP("marketplace-listing") || LP("1.0") || LP(canonical_text) || LP(JCS({})))
```

For Standard, `code="standard"`, params has exactly `{"ai_training":<boolean>}`, and `canonical_text` is `STANDARD_TEMPLATE` with the token replaced by the matching clause after removing that clause block's terminal LF. For a custom UTF-8 text document, `code="custom"`, `version="1"`, text is the canonical uploaded text and params has exactly `{"ai_training":<boolean>,"source_sha256":"<raw-upload-sha256>"}`. For PDF, `code="custom"`, `version="1"`, params has exactly `{"ai_training":<boolean>,"source_sha256":"<raw-upload-sha256>"}` (identical shape to custom text), and `canonical_text` is the JCS string `{"content_type":"application/pdf","source_sha256":"<raw-upload-sha256>"}` followed by exactly one LF; the original immutable PDF bytes are stored and downloaded verbatim. `source_sha256` therefore appears in both params and canonical_text by design. Chunk A publishes a sixth vector for a PDF whose raw bytes are the ASCII string `%PDF-1.4 test` (so any implementation can reproduce it). This avoids nondeterministic PDF text extraction while binding the exact file. `license_documents.source_sha256` always separately binds the raw upload.

For the rider, params has exactly `{"ai_training":<boolean>}` and the selected rider block is hashed. Omission of the custom-listing switch is canonicalised to `true` before hashing. Covenant params is exactly `{}`. A combined acceptance digest may be exposed for convenience but never substitutes for storing and checking all three component hashes.

### 3.2 Published test vectors

These vectors are generated from the normative §2 blocks by `tests/test_listing_license_hash_vectors.py`; implementations in backend, frontend and AIM Data must reproduce them exactly. The component byte lengths and final digests are filled from the checked extraction script before this specification is dispatched.

| Vector | Params JCS | Canonical-text bytes | Expected SHA-256 |
| --- | --- | ---: | --- |
| Standard v1.0, training permitted | `{"ai_training":true}` | 6,557 | `4b05dbcd0c186746d3deab6c68beaebba88610de8e85122efb4d527edb1263c6` |
| Standard v1.0, training not permitted | `{"ai_training":false}` | 6,613 | `e83e03bb731fee832d108ef77689f7ff49e3409f88124b483b2ef34ca7ba3821` |
| Rider v1.0, permitted | `{"ai_training":true}` | 438 | `f9785144dc4d48af6446512cbabd03431a35015d71b92260f4dcfab164084140` |
| Rider v1.0, not permitted | `{"ai_training":false}` | 317 | `8878e2fb3327378e90a1d9206da9aa2b419255872cdfa6a883c0d2688f768416` |
| Covenant v1.0 | `{}` | 1,211 | `a91234b67bf7467a0c80f6e1caa47b563032e94751146901b796eaaf220431af` |

Tests also assert the false rider vector, malformed/extra params refusal, NFC equivalence, CRLF equivalence, a one-byte text change mismatch, and that true and false Standard variants differ.

## 4. Data model, migration and immutable records

The pinned model has free-text `listings.license`, `license_url` and `usage_terms` (`app/models/marketplace.py:96-102`); `listing_versions` currently has no licence snapshot (`app/models/marketplace.py:217-250`); `orders.listing_snapshot` is already non-null JSONB (`app/models/order.py:132`). Chunk A adds one Alembic revision `alembic/versions/20260922_001_s1735_listing_licenses.py`, revision `s1735_listing_licenses`, with pinned `down_revision="s1294_chunk5a_retirement"` (the pinned head). Dispatch must rebase the revision only if the canonical backend head has moved; it must not edit an already released migration.

### 4.1 New tables

`license_documents` (custom only):

- `id UUID PRIMARY KEY`; `owner_seller_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT`; `title VARCHAR(255) NOT NULL`; `content_type VARCHAR(32) NOT NULL CHECK IN ('text/plain','application/pdf')`; exactly one of `full_text TEXT` and `object_key TEXT` is non-null, matching content type; `size_bytes BIGINT NOT NULL CHECK (size_bytes BETWEEN 1 AND 1048576)`; `source_sha256 CHAR(64) NOT NULL`; `license_sha256 CHAR(64) NOT NULL`; `malware_scan_status VARCHAR(16) NOT NULL CHECK = 'clean'`; `hygiene_report JSONB NOT NULL`; `status VARCHAR(16) NOT NULL CHECK IN ('active','retired','rejected')`; `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- Unique `(owner_seller_id, source_sha256)` and `(owner_seller_id, license_sha256)`; index `(owner_seller_id, status, created_at DESC)`. Object keys are private and never returned by public APIs.

`seller_license_acceptances` (append-only M8 signature):

- `id UUID PRIMARY KEY`; `seller_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT`; `seller_org_id UUID NULL REFERENCES organizations(id) ON DELETE RESTRICT`; `party_type VARCHAR(16) NOT NULL CHECK IN ('organization','sole_trader')`; `seller_legal_name VARCHAR(255) NOT NULL`; `seller_jurisdiction CHAR(2) NOT NULL`; `signer_name VARCHAR(255) NOT NULL`; `signer_title VARCHAR(255) NOT NULL`; `authority_confirmed BOOLEAN NOT NULL CHECK (authority_confirmed)`; `license_code VARCHAR(32) NOT NULL`; `license_version VARCHAR(16) NOT NULL`; `license_params JSONB NOT NULL`; `license_document_id UUID NULL REFERENCES license_documents(id) ON DELETE RESTRICT`; `license_sha256 CHAR(64) NOT NULL`; `rider_sha256 CHAR(64) NULL`; `covenant_code VARCHAR(32) NOT NULL`; `covenant_version VARCHAR(16) NOT NULL`; `covenant_sha256 CHAR(64) NOT NULL`; `ip INET NULL`; `user_agent TEXT NULL`; `accepted_at TIMESTAMPTZ NOT NULL DEFAULT now()`; `source VARCHAR(32) NOT NULL CHECK IN ('submission','platform_terms_v1.1')`; `terms_acceptance_id UUID NULL REFERENCES terms_acceptance(id) ON DELETE RESTRICT`.
- Checks require custom → document and rider, Standard → neither; `platform_terms_v1.1` → non-null terms row; submission → null terms row. Index `(seller_user_id, accepted_at DESC)` and `(seller_org_id, accepted_at DESC)`. Database trigger `reject_seller_license_acceptance_update_delete` rejects UPDATE and DELETE.

`license_acceptances` (one immutable contract row per order):

- `id UUID PRIMARY KEY`; `order_id UUID NOT NULL UNIQUE REFERENCES orders(id) ON DELETE RESTRICT`; `listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE RESTRICT`; `listing_version_id UUID NULL REFERENCES listing_versions(id) ON DELETE RESTRICT`; `seller_acceptance_id UUID NOT NULL REFERENCES seller_license_acceptances(id) ON DELETE RESTRICT`.
- Exact instruments: `license_code`, `license_version`, `license_params JSONB`, nullable `license_document_id`, `license_sha256`, nullable `rider_sha256`, `covenant_code`, `covenant_version`, `covenant_sha256`, plus `license_text TEXT` for stock/text custom or `license_pdf_source_sha256 CHAR(64)` for PDF. This is intentional contract denormalisation; old records do not change when seeds or custom-document status changes.
- Parties: `buyer_user_id`, nullable `buyer_org_id`, `buyer_party_type`, `buyer_legal_name`, `buyer_jurisdiction`, `seller_user_id`, nullable `seller_org_id`, `seller_party_type`, `seller_legal_name`, `seller_jurisdiction`, all required except the two organisation IDs.
- Signature: nullable `typed_name`, nullable `signer_title`, `authority_confirmed BOOLEAN NOT NULL CHECK (authority_confirmed)`, nullable `principal_ref`, nullable `credential_id`, `sanctions_screening_ref VARCHAR(255) NULL` (no screening subsystem exists at the pinned backend — Gate 1 §6.14's premise was wrong; the column is reserved, never populated in this build, and its population is deferred to a platform compliance item), `accepted_at`, nullable `ip`, nullable `user_agent`, `channel CHECK IN ('web','api','agent','mcp','wallet')`. Web requires typed name and title and forbids credential id; non-web requires principal and credential id and requires typed name null.
- Lifecycle: `status VARCHAR(16) NOT NULL DEFAULT 'active' CHECK IN ('active','terminated')`. Index `(buyer_user_id, accepted_at DESC)`, `(seller_user_id, accepted_at DESC)` and `(status, accepted_at)`. A trigger rejects UPDATE of every column except `status`, permits only `active → terminated`, and rejects DELETE.

`license_acceptance_events` (append-only lifecycle facts):

- `id UUID PRIMARY KEY`; `acceptance_id UUID NOT NULL REFERENCES license_acceptances(id) ON DELETE RESTRICT`; `event_type VARCHAR(32) NOT NULL CHECK IN ('terminated','deletion_confirmed')`; `reason VARCHAR(64) NOT NULL`; `actor_type VARCHAR(32) NOT NULL`; nullable `actor_id UUID`; `occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()`; nullable `deletion_due_at TIMESTAMPTZ`; `event_ledger_id UUID NOT NULL REFERENCES allai_event_ledger(id) ON DELETE RESTRICT` (`app/models/allai_event_ledger.py:20`)`; `metadata JSONB NOT NULL DEFAULT '{}'`.
- Unique partial index allows one `terminated` and one `deletion_confirmed` event per acceptance; index `(acceptance_id, occurred_at)`. Checks require `deletion_due_at` only on termination. UPDATE/DELETE trigger rejects all mutation. This table holds termination/deletion facts so `license_acceptances.status` remains the only mutable contract-record column.

### 4.2 Existing-table columns

Add `organizations.legal_name VARCHAR(255)` and `jurisdiction CHAR(2)`; the pinned model presently has only the display `name` (`app/models/organization.py:24-34`), while `BillingEntity` supplies `legal_name` and `country_code` (`app/models/finance.py:31-44`). Add the following identical licence snapshot columns to `listings` and `listing_versions`: `license_code`, `license_version`, `license_params JSONB`, nullable `license_document_id`, `license_sha256`, nullable `rider_sha256`, `covenant_code`, `covenant_version`, `covenant_sha256`, `seller_acceptance_id`, and `seller_acceptance_source`. FKs use `RESTRICT`; checks enforce the Standard/custom pairing and `license_params` schema. After the backfill and validation phases, all except `license_document_id`/`rider_sha256` are NOT NULL for rows eligible to publish or purchase. `listing_versions` captures values by copy at publication; it never reads them live from `listings` during delivery.

### 4.3 Upgrade/backfill/down

Upgrade order is: create tables nullable; add organisation and listing/version columns nullable; add uppercase ISO-alpha-2 checks to every new jurisdiction field; seed the three §2 stock instruments in repository resources (not `license_documents`); backfill organisation identity using §8; map **every** inherited value, including the free-text `CC-BY-4.0` / `CC0-1.0` strings, to Standard v1.0 with `ai_training:true` (Max decision 6: existing listings default to Standard; there is no imported-licence instrument in this build), preserving the old `listings.license` / `license_url` values untouched as provenance shown on the listing page as "seller previously indicated: <value>"; leave every inherited `seller_acceptance_id` null and `seller_acceptance_source='platform_terms_v1.1'` until the real seller accepts terms 1.1; copy a listing's snapshot to its existing versions; validate constraints. An inherited listing remains viewable but purchase returns `409 SELLER_TERMS_ACCEPTANCE_PENDING` until the terms row and derived seller acceptance exist. No timestamp is fabricated.

Down migration first refuses if any `license_acceptances`, `license_acceptance_events`, `seller_license_acceptances` or custom `license_documents` row exists, because dropping signed contracts is destructive. If empty, it drops triggers, indexes, constraints, new columns and tables in dependency order and then organisation columns. Rollback of behaviour is the flag, not deletion of signed records.

## 5. One order constructor and creation refusals (M1–M3)

`OrderService.create_order` is at `app/services/order_service.py:638-649`; its insert is at `app/services/order_service.py:681-706`. Its five callers are checkout (`app/api/v1/endpoints/checkout.py:222-231`), MCP (`app/api/v1/endpoints/mcp_marketplace.py:670-676`), marketplace tools (`app/services/mcp_marketplace_tools.py:816-822`), transaction agent checkout (`app/services/transaction_service.py:880-886`) and fixed-price auto-accept (`app/services/transaction_service.py:1319-1325`). The separate wallet insertion at `app/services/agent_service.py:531-559` is removed and routed through the service. The existing `orders.listing_snapshot` remains the delivery-side frozen projection.

The signature becomes:

```python
async def create_order(
    self, *, buyer_id, seller_id, listing_id, amount_cents, listing_snapshot,
    acceptance: LicenseAcceptanceInput,
    stripe_checkout_session_id=None, transaction_id=None, auto_commit=True,
    purchased_version_id=None,
) -> dict:
```

`LicenseAcceptanceInput` requires `accept_license_sha256`, `accept_covenant_sha256`, nullable `accept_rider_sha256`, `authority_confirmed`, `typed_name`, `signer_title`, `channel`, authenticated `principal_ref`, nullable `credential_id`, IP and user agent. It never accepts seller identity or document text from the client. Under one DB transaction and a `SELECT ... FOR UPDATE` lock on listing/version and seller acceptance, the constructor resolves legal identity, re-renders and hashes current terms, verifies all supplied hashes with constant-time comparison, verifies the seller acceptance is the same current version, freezes the instruments into `listing_snapshot`, inserts the order, and calls `record_license_acceptance(session, ...)`. That recorder only adds the row and flushes; it neither commits nor calls `record_terms_acceptance`. The latter currently commits internally at `app/services/terms_acceptance_service.py:136-204` and is therefore shape precedent only.

The constructor **retains** the existing buyer platform-terms gate as its first check: `require_terms_acceptance(..., actor=TermsActor(user_id=buyer_id), endpoint="order-create")` at `app/services/order_service.py:655-661` stays in place and is executed in enforcing mode regardless of `TERMS_GATE_MODE=shadow` (`app/core/config.py:154-160`, `terms_acceptance_service.py:273-278`), so a buyer who has not accepted platform terms 1.1 cannot create an order on any channel; the agent/transaction callers keep their own calls (`transaction_service.py:246-248, 331-333, 978-980`). Refusal happens before order insert, wallet debit, Stripe session creation or commit:

| Condition | Response |
| --- | --- |
| buyer has not accepted the current platform terms | `403 TERMS_ACCEPTANCE_REQUIRED` (existing code, now shadow-proof) |
| absent or stale licence/covenant hash | `409 LICENSE_ACCEPTANCE_STALE` with current public hashes, no text leak |
| custom rider absent or stale | `409 LICENSE_RIDER_ACCEPTANCE_STALE` |
| Standard carries rider, custom lacks document, malformed/unknown params | `422 LICENSE_ACCEPTANCE_INVALID` |
| `authority_confirmed` is not literal true | `422 LICENSE_AUTHORITY_REQUIRED` |
| buyer identity absent | `409 BUYER_LEGAL_IDENTITY_REQUIRED` |
| billing/typed identity conflict | `409 LEGAL_IDENTITY_CONFLICT` with both legal name/jurisdiction values and a reconciliation link |
| seller acceptance absent, stale, wrong version, or inherited terms 1.1 pending | `409 SELLER_TERMS_ACCEPTANCE_PENDING` |
| flag off | pre-feature behaviour; new acceptance keys are not exposed or consumed |

API/agent/MCP/wallet channels bind the authenticated principal and credential id and set typed name null; web requires typed name/title. A bare hash never establishes authority. A forced recorder, Stripe or DB failure rolls back both rows and any wallet mutation. Static test `git grep "INSERT INTO orders" app` allows only the constructor migration/implementation and historical migrations.

Immediately before any Stripe `checkout.session.completed` path changes the order to paid or invokes fulfilment, it locks the order and re-runs `require_active_license_acceptance(order_id)`, then checks the acceptance's hashes against `orders.listing_snapshot`. A mismatch or termination records a failed fulfilment event and emits no credential or delivery. The payment handler currently begins at `app/services/billing_service.py:621`; fulfilment entry is `app/services/fulfillment_service.py:141-180`.

## 6. Issuance gate and complete delivery-door inventory (M4, M5)

`require_active_license_acceptance(session, order_id)` selects the order and its 1:1 acceptance `FOR UPDATE`, refuses missing acceptance with 403 `LICENSE_ACCEPTANCE_REQUIRED`, refuses terminated acceptance with 409 `LICENSE_TERMINATED`, verifies snapshot hashes, and returns the locked acceptance. It does not commit. The termination function takes the same order lock, so issuance either completes first or observes termination; no token, URL, redirect, credential or byte is constructed before the helper returns.

**Pre-purchase public sample door (no order exists).** `GET /public/listings/{listing_id}/sample/{index}` (`app/api/v1/endpoints/public.py:91-98`) and the sample metadata/URL emitted by the public listing projection (`public.py:886-896`) serve bytes today on feature/status flags alone (`app/services/public_sample_service.py:89-99`, `:218-256`). A second, listing-level rule `require_listing_license_snapshot(listing_id)` is inserted in `resolve_samples`, `sample_files`, `serve_sample` and the public projection: samples (metadata, URLs and bytes) are exposed only when the listing/version carries a bound licence snapshot with a real seller acceptance (`seller_acceptance_id` not null, or the inherited listing's seller has accepted terms 1.1 and the derived row exists). A pending inherited listing exposes no sample and no sample URL (Gate 1 §6.5: no sample is servable before a licence choice). The generated route inventory matches `/sample` routes to this rule. Test: `tests/test_listing_license_samples.py` — pending inherited listing → 404 sample and no `sample` field in the projection; bound listing → served.

The helper is inserted at each issuance/consumption point below, even where another point appears to call it. This defence in depth is required because the current doors are not one call graph:

| Door | Exact insertion point at backend pin |
| --- | --- |
| raw/reference order access | first line of `OrderService._assert_current_access` and `_authorize_download_access`, `app/services/order_service.py:379-427`; raw token service also rechecks before issuing/consuming at `app/services/raw_download_service.py:45-90` |
| `POST /orders/{id}/download-token` | before service call at `app/api/v1/endpoints/orders.py:358-396` |
| reference `GET /orders/{id}/access` and scoped refresh | before any access projection or public URL at `app/api/v1/endpoints/orders.py:512-620`; before credential construction in refresh at `app/api/v1/endpoints/orders.py:338-355` |
| delivery token | immediately after transaction lock and before reuse/new JWT in `DeliveryService.generate_delivery_token`, `app/services/delivery_service.py:133-202` |
| delivery token consumption | after lock and before claims are accepted in `validate_token`, `app/services/delivery_service.py:234-284`; `stream_from_vz` therefore rechecks on every request/range at `app/services/delivery_service.py:286-305` |
| delivery routes | `POST /deliveries/{tx}/token`, `GET /deliveries/{tx}/download-url`, `GET /deliveries/{tx}/download` at `app/api/v1/endpoints/deliveries.py:65-122` |
| fulfilment request and reply | before dispatch in `FulfillmentService.request_fulfillment`, `app/services/fulfillment_service.py:141-180`, and again in asynchronous `handle_fulfillment_response` before any credential persistence (`app/services/fulfillment_service.py:304-352`) |
| Seller Workspace | before prepare, session download and every per-file grant; routes are `app/api/v1/endpoints/seller_workspace_delivery.py:35-75`, with existing authorisation at `app/services/seller_workspace_delivery.py:82-100` |
| AIM Data manifest | first operation in `app/services/delivery_buyer.py:34-41`; also before member grant and redirect in `app/api/v1/endpoints/orders.py:952-979` |
| fulfilment file download | before `consume_download_token` in `app/api/v1/endpoints/fulfillment_download.py:45-80` |
| agent data | before broker/token work in `GET /agent/orders/{id}/data`, `app/api/v1/agent/router.py:878-917` |
| agent artifact | before broker work in `GET /agent/orders/{id}/artifact`, `app/api/v1/agent/router.py:1120-1164`; at broker already-available token creation (`app/services/fulfillment_broker.py:132-144`); at artifact URL construction (`app/services/fulfillment_broker.py:171-246`); and before every URL/credential branch in `OrderService.issue_download_token` (`app/services/order_service.py:1228-1263`) |

The internal-key `POST /generate-download-token` at `app/api/v1/endpoints/jwt.py:14-23` is **removed**, not adapted: it accepts listing/user without an order and has no legitimate licence-bound identity. Route-regression tests assert it is absent from the FastAPI route table and returns 404.

`tests/test_listing_license_delivery_gate.py` builds its cases from the live FastAPI route table. Each delivery route carries a `license_gate="active_acceptance"` marker set by the dependency/decorator; the test fails if a route matching the delivery response classes, `/download`, `/access`, `/artifact`, `/data`, `/token`, `/grant`, `/refresh`, or credential-producing handlers lacks the marker. It then parameterises every generated case over missing and terminated acceptances, asserting 403/409, empty response-body secrets, no redirect, no token/URL/credential and zero streamed bytes. A concurrency test pauses issuance after the order lock, requests termination, and proves one serial order: if issuance wins, termination completes after it; every later use refuses.

## 7. x402 launch decision (M10)

x402 is hard-disabled for this launch. It currently has its own payment/token flow (`app/api/v1/endpoints/x402.py:50-172`, `app/services/x402_service.py:120-324`) and `X402_ENABLED` defaults false (`app/core/config.py:653-655`); integrating it would create a second paid constructor and enlarge the legal acceptance surface. Chunk C makes `require_x402_enabled` also refuse whenever listing licences are enabled, ignores a listing's legacy x402 opt-in, excludes x402 fields from public purchase capabilities, and startup refuses the invalid combination `LISTING_LICENSES_ENABLED=true` plus `X402_ENABLED=true`. `tests/test_listing_license_x402.py` overrides both old flags and listing metadata, then proves the route is 404 and creates no payment, transaction, order, acceptance or token. A later Gate 1 amendment is required before x402 can be reintroduced through `OrderService.create_order`.

## 8. Legal identity and `/legal/terms` (M6)

Allowed license parties are: (a) an organisation, represented by an authorised natural person, or (b) a sole trader/legal individual acting for business purposes. Consumer purchase is out of scope. Both require a non-blank legal name and ISO 3166-1 alpha-2 jurisdiction. Organisation also requires `buyer_org_id`/`seller_org_id`, signer title and authority confirmation. Sole trader uses the authenticated user id, typed legal name, jurisdiction, title `sole trader`, and authority confirmation for self.

Resolution precedence is deterministic:

1. A party-linked `BillingEntity.legal_name` plus `country_code` wins; those fields exist at `app/models/finance.py:31-44`.
2. Otherwise use typed `business_legal_name` plus jurisdiction from the most recent accepted platform-terms record and backfill the organisation.
3. Otherwise refuse publish/order.

If both sources exist after trim, Unicode NFC and case-fold normalisation and either legal name or jurisdiction differs, return `409 LEGAL_IDENTITY_CONFLICT` with both `{source, legal_name, jurisdiction}` values and do not silently choose. The organisation update/reconciliation flow must resolve it, creating an audit event; only then may the action retry.

`TermsAcceptanceRequest` already collects scope, signer name/title, business legal name and authority (`app/api/v1/endpoints/legal_terms.py:30-55`). Chunk A adds required `jurisdiction`, validates the allowed party types, persists it on the append-only terms record, and backfills `organizations`. Existing accepted terms rows are not rewritten. The terms 1.1 screen asks for the missing jurisdiction when the seller next reaches a gated action. Purchase performs its seller-current-version check independently of `TERMS_GATE_MODE`; that setting is currently `shadow` (`app/core/config.py:159`) and cannot bypass licence authority.

## 9. Seller-side flows and custom-upload hygiene (M8, M11)

All publish channels send one `LicenseSelection`:

```json
{
  "kind": "standard|custom",
  "version": "1.0",
  "ai_training": true,
  "license_document_id": null,
  "license_sha256": "<64 hex>",
  "rider_sha256": null,
  "covenant_code": "marketplace-listing",
  "covenant_version": "1.0",
  "covenant_sha256": "<64 hex>",
  "seller_acceptance": {
    "signer_name": "...", "signer_title": "...",
    "authority_confirmed": true
  }
}
```

Omitting `ai_training` means literal `true` at the receiving boundary before hashing. Omitting the entire selection or covenant confirmation refuses publish. The server ignores client legal names/hashes as authority: it resolves identity, rebuilds hashes, and returns stale-hash errors.

**Web/API listing submission.** The submission screen asks “How can buyers use this data?” and shows exactly two cards: Standard (recommended) and My own licence. Both display the “Allow AI/ML training” toggle pre-set to Allow; custom also uploads a document. The seller must open the summaries/full text and tick the covenant/authority confirmation. API schema is added to the existing listing publish path at `app/api/v1/endpoints/listings.py:633-700` and its request schema; no new general publish endpoint is invented.

**Seller Workspace.** Add the same fields to saved draft content, server-rendered review, approval hash and publication request in backend `app/schemas/seller_listing_draft.py`, `app/services/seller_listing_review.py`, `app/schemas/seller_listing_approval.py` and `app/api/v1/endpoints/seller_listing_publication.py:47-80`; add the two cards/toggle/upload and confirmation to frontend `components/seller-workspace/WorkspaceData.tsx`, `SellerReview.tsx`, `SellerApproval.tsx` and `SellerPublication.tsx`. Any licence change invalidates the review and approval hashes. Existing `price_license_confirmed` is split/replaced by explicit licence/covenant facts, not treated as a signature.

**AIM Data.** Add `license_selection` to `aim-data:frontend/src/pages/DatasetDetail.tsx:844-857` at the publish construction, to `aim-data:frontend/src/lib/api.ts:1181` at `/api/marketplace/publish`, and to the local receiver `aim-data:app/routers/marketplace_publish.py`. The backend receiver then carries it through `/api/marketplace/publish`. Gateway v2 replaces the unused `LicenseTerms {terms_ref, commercial_use, retention_days}` (`app/gateway_v2/surfaces/publish.py:64-81`) with the same `LicenseSelection`, folded into the signed publish bytes; old gateway clients fail closed with an upgrade-required error when the flag is enabled.

**Custom hygiene.** `POST /licenses/custom` is authenticated seller-only, feature-gated and rate-limited. It accepts UTF-8 `.txt` or structurally valid PDF, maximum **1 MiB**, streams to private quarantine, and performs MIME/magic agreement, PDF active-content rejection (JavaScript, launch actions, embedded files, external retrieval), malware scan, secret-pattern scan (private keys, cloud credentials, bearer tokens and high-confidence entropy), UTF-8/NFC validation for text, an English-canonical check (the extracted text must be classified as English by the existing language detector used for listing metadata; a non-English document is rejected with `LICENSE_LANGUAGE_NOT_ENGLISH` — Gate 1 §6.13: English canonical, translations informational only and out of scope), and prohibited-terms scan. It rejects any clause purporting to change non-custodial delivery, the 5% commission, refund handling, dispute hold, evaluation-only samples, marketplace-only notices, or allowing regulated personal data. A human-review result is not introduced: a positive/indeterminate scan fails closed with a named reason. Clean bytes move once to content-addressed immutable storage, get `source_sha256` and canonical `license_sha256`, and cannot be overwritten. Reuse is only by the owning seller. UI displays text verbatim in a plain-text viewer or embeds/downloads the exact PDF, always with the amber notice and separate rider. No sanctions screening exists at the pinned backend; nothing is copied into the signed order record/event projection; no second sanctions system is built.

## 10. Buyer flow, agent fields, histories and termination (M9)

The public listing page shows before purchase: summary labelled “not the contract”, green/amber notice, conspicuous AI-training value, full text expandable, exact document download, covenant and rider where applicable, canonical URLs and component hashes. The current purchase seam is `components/ListingPurchasePanel.tsx:4-70`; the checkout transport is `api/checkout.ts:4-9`.

The Buy screen repeats those materials and collects typed full name, signer title, business legal name, jurisdiction and “I am authorised to accept for <legal name>”. “Accept and continue to payment” posts to the existing `POST /checkout/create` with the three hashes, authority and identity fields. Backend checkout presently calls the constructor at `app/api/v1/endpoints/checkout.py:222-231`. The UI never pre-ticks authority.

Agent/API/MCP listing details expose:

```json
{
  "license": {
    "code": "standard", "version": "1.0",
    "params": {"ai_training": true},
    "summary": ["..."],
    "full_text_url": "https://ai.market/licenses/standard/1.0/ai-training",
    "download_url": "https://ai.market/licenses/standard/1.0/ai-training?download=1",
    "sha256": "...",
    "covenant_sha256": "...",
    "rider_sha256": null
  }
}
```

Purchase fields are `accept_license_sha256`, `accept_covenant_sha256`, `accept_rider_sha256` (required for custom only), and `authority_confirmed:true`. Authentication supplies `principal_ref` and `credential_id`; callers cannot override them and `typed_name` is null. These fields are added to the existing agent/MCP constructor call sites, not a new purchase endpoint.

Buyer order history and seller sales history each link “Licence record”. `GET /orders/{id}/license-record` authorises either recorded party and renders on demand from `license_acceptances`: exact licence, rider, covenant, hashes, listing/version/order, both legal parties/jurisdictions, signature channel/principal, accepted time and current status. `?format=pdf` renders a deterministic downloadable PDF but stores no PDF; DB text/hashes remain truth. Response is `Cache-Control: private, no-store`. Account teardown retains signed contract rows under the existing legal-hold rule.

The constructor registers a post-commit notification, idempotently keyed by acceptance id, telling the seller that the named listing/order was accepted and linking to the sales-history record; rollback sends nothing. If the same purchase later entitles a newer dataset version, no new acceptance is requested: the immutable order snapshot's original licence, rider and covenant govern that later version, and the record renderer lists the later delivered version as fulfilment history without changing contract columns. Chunk E also records operator evidence that the Stripe Tax product classification for the data licence remains the configured electronically supplied service classification; this is a configuration check, not a new tax engine or product decision.

`terminate_license_acceptance(session, order_id, reason, actor)` locks the order/acceptance, permits only `active → terminated`, updates only `license_acceptances.status`, appends a `terminated` event carrying `occurred_at`, reason and `deletion_due_at=occurred_at+30 days`, and writes one Event Ledger row in the same transaction. Refund completion always calls it. A dispute hold blocks all doors immediately through order state; a final refund terminates, while a resolved-no-refund dispute returns the still-active licence. Seller breach termination can be initiated only through ai.market notice. Buyer history displays the deletion duty and records a separate append-only `deletion_confirmed` event; confirmation does not mutate the acceptance or reactivate anything. Contract-column mutation and unaudited SQL transitions are rejected by DB triggers and static tests.

## 11. Public licence URLs, JSON-LD and inherited listings

Public, immutable, cacheable routes are `GET /licenses/<code>/<version>[/<variant>]`, where Standard variants are `ai-training` and `no-ai-training`, covenant is `/licenses/marketplace-listing/1.0`, and rider variants are `/licenses/ai-training-rider/1.0/permitted|not-permitted`. They return summary, full normative text, parameters and hash; `?download=1` is an attachment. Custom documents use authenticated listing/order URLs, never this public namespace.

Replace `LICENSE_URL_MAP` at `app/services/jsonld_service.py:43-54`. Standard/custom listing JSON-LD `license` is the canonical ai.market URL (custom uses `https://ai.market/licenses/custom/<license_sha256>` as a public notice page with amber summary/hash but document access follows listing visibility); there is no imported-licence instrument: inherited listings publish the Standard URL like any other, and the old free-text value is provenance only. MIT, Apache-2.0, CC-BY-SA-4.0, CC-BY-4.0 and CC0-1.0 are all removed from the data-licence map (the whole map is replaced). JSON-LD, public listing API, search result, `llms.txt` and the agent manifest expose the same code/version/variant and never inline custom document text into bulk discovery.

Terms version becomes 1.1 with the exact §2.4 sentence. Existing listings receive Standard/training-yes projections during migration but no invented acceptance. On the seller's next terms-gated publish or order-related action, real terms acceptance creates a `seller_license_acceptances` row with `source=platform_terms_v1.1` and the actual `terms_acceptance_id`; eligible inherited listings atomically point to it. Until then they are browseable but purchase refuses `409 SELLER_TERMS_ACCEPTANCE_PENDING`, even when `TERMS_GATE_MODE=shadow` (the current shadow seam is `app/services/terms_acceptance_service.py:218-278`). No customer is prompted per listing and no cutover deadline exists.

## 12. Chunks, acceptance criteria, risks and dispatch order

Every chunk is built by MP, uses `LISTING_LICENSES_ENABLED=false` by default, includes flag-off proof, and supplies test logs plus exact commit identity to unanimous 3/3 CORE S3 Gate 3 review by GLM, DeepSeek and Gemini. “Merged” is not “enabled”.

| Chunk | Repositories | Mandates | Dispatch dependency |
| --- | --- | --- | --- |
| A — instruments, hashing, identity, schema | backend | M6, M7, M12 | first |
| B — constructor, recorder, refusals | backend | M1–M3, M6 | A Gate 3 |
| C — issuance inventory, legacy removal, x402 | backend | M4, M5, M10 | B Gate 3 |
| D — seller flows | backend + frontend + AIM Data | M8, M11, M12 | A Gate 3; may run parallel with E after B |
| E — buyer flows, records, termination | backend + frontend | M9, M12 | B Gate 3; parallel with D |
| F — discovery, terms bump, inherited listings | backend + frontend | M8, M12 | D and E Gate 3 |
| G — runbook and E2E | runbooks plus test-only fixes in owning repo | all | C and F Gate 3 |

### 12.1 Chunk A — instruments, hashes, migration and identity

**Files:** backend `app/resources/licenses/{standard-1.0.md,marketplace-listing-1.0.md,ai-training-rider-1.0.md}`, `app/services/license_hashing.py`, `app/services/legal_identity.py`, `app/models/{license_document.py,seller_license_acceptance.py,license_acceptance.py,organization.py,marketplace.py,registry.py}`, `app/api/v1/endpoints/legal_terms.py`, `app/services/terms_acceptance_service.py`, `app/core/config.py`, `alembic/versions/20260922_001_s1735_listing_licenses.py`.

**AC/tests:** seed bytes equal §2; all vectors in §3 match across backend fixture, frontend TypeScript fixture and AIM Data fixture; extra/malformed params fail; migration upgrade/backfill/constraints/down refusal pass; identity precedence/conflict/backfill pass. Tests: `tests/test_listing_license_seed_documents.py`, `tests/test_listing_license_hash_vectors.py`, `tests/test_listing_license_migration.py`, `tests/test_listing_license_identity.py`.

**Risk/rollback:** contract byte drift or wrong migration head. Pin seed digests in tests and recheck head at dispatch. Roll back behaviour with flag; never downgrade after signed rows exist.

### 12.2 Chunk B — constructor, acceptance recorder and atomic refusal

**Files:** backend `app/services/{order_service.py,license_acceptance_service.py,agent_service.py,mcp_marketplace_tools.py,transaction_service.py,billing_service.py}`, `app/api/v1/endpoints/{checkout.py,mcp_marketplace.py}`, checkout/order schemas.

**AC/tests:** only constructor creates orders; every §5 refusal produces no order, acceptance, debit or commit; recorder never commits/calls platform recorder; web and authenticated machine channels bind correct signature facts; webhook re-verifies before fulfilment. Tests: `tests/test_listing_license_order_constructor.py`, `tests/test_listing_license_acceptance.py`, existing checkout/MCP/transaction tests.

**Risk/rollback:** missed constructor or partial money mutation. Static insert inventory plus forced-failure tests. Flag off restores old arguments; schema stays.

### 12.3 Chunk C — all delivery doors, legacy JWT removal and x402

**Files:** backend `app/services/{license_access_service.py,order_service.py,raw_download_service.py,delivery_service.py,fulfillment_service.py,fulfillment_broker.py,delivery_buyer.py,seller_workspace_delivery.py}`, `app/api/v1/endpoints/{orders.py,deliveries.py,fulfillment_download.py,seller_workspace_delivery.py,jwt.py,x402.py}`, `app/api/v1/agent/router.py`, `app/core/config.py`.

**AC/tests:** generated inventory covers every §6 row and fails on an unmarked synthetic route; missing/terminated rows disclose nothing; async reply rechecks; lock race is serial; legacy route is absent; x402: (i) configuration validation test — `LISTING_LICENSES_ENABLED=true` plus `X402_ENABLED=true` refuses startup; (ii) route behaviour test under the largest bootable combination (`LISTING_LICENSES_ENABLED=true`, `X402_ENABLED=false`, listing legacy x402 opt-in set) — the x402 routes return 404/410 and produce no transaction, payment, order, acceptance or token. Tests: `tests/test_listing_license_delivery_gate.py`, `tests/test_listing_license_route_inventory.py`, `tests/test_listing_license_x402.py`.

**Risk/rollback:** a hidden delivery seam. Route-table marker plus service-level tests catch both HTTP and asynchronous paths. Flag rollback leaves the removed unsafe legacy route removed.

### 12.4 Chunk D — seller web, API, Seller Workspace and AIM Data

**Files:** backend publish/listing schemas/services named in §9 plus `app/services/custom_license_service.py`, `app/api/v1/endpoints/licenses.py`, gateway v2 publish schema; frontend Seller Workspace components and listing editor/API types; AIM Data `frontend/src/pages/DatasetDetail.tsx`, `frontend/src/lib/api.ts`, `app/routers/marketplace_publish.py`, publish models/client.

**AC/tests:** exactly two cards; toggle defaults true visibly and on omitted API input; covenant/identity required; custom hygiene matrix fails closed; bytes immutable; all three publish routes produce identical hashes and seller records; approval hash invalidates on change. Tests: backend `tests/test_custom_license_upload.py`, `tests/test_listing_license_publish.py`, `tests/test_listing_license_seller_acceptance.py`; frontend `components/seller-workspace/*License*.test.tsx`; AIM Data `tests/test_marketplace_publish_license.py` and `frontend/src/pages/DatasetDetail.test.tsx`.

**Risk/rollback:** unsafe PDF or route shape drift. Keep custom upload private until every scan passes; feature flag removes UI/API capability without deleting clean immutable uploads.

### 12.5 Chunk E — buyer acceptance, records, histories and termination

**Files:** backend checkout/order schemas/endpoints, licence-record renderer/endpoint, refund/dispute hooks and Event Ledger adapter; frontend listing page, `components/ListingPurchasePanel.tsx`, `components/BuyButton.tsx`, `api/checkout.ts`, buyer order and seller sales-history components.

**AC/tests:** listing and Buy screens show/download exact terms; authority starts unchecked; client sends exact fields; agent principal is server-bound; both parties can render equal records while strangers cannot; refund terminates atomically, sets deletion due, writes Event Ledger, and all doors refuse. Tests: `tests/test_listing_license_buyer_checkout.py`, `tests/test_listing_license_record.py`, `tests/test_listing_license_termination.py`; frontend `components/ListingPurchasePanel.test.tsx`, `components/BuyButton.test.tsx`, order-history tests.

**Risk/rollback:** displayed text/hash mismatch or PDF renderer treated as authority. UI asserts server hash over fetched bytes; database record is authority. Flag hides new purchase UI, but signed records remain retrievable.

### 12.6 Chunk F — public discovery, terms 1.1 and inherited listings

**Files:** backend `app/services/jsonld_service.py`, public licence endpoints/resources, public listing/search/agent-manifest/llms services, terms config/copy, inherited activation service; frontend public licence and terms pages.

**AC/tests:** URLs are immutable and cross-hash; JSON-LD uses correct canonical URL; removed software licences do not map; terms exact sentence/version; inherited listing refuses before real terms row even in shadow, then binds exact row and becomes purchasable; no timestamp fabrication. Tests: `tests/test_listing_license_discovery.py`, `tests/test_listing_license_inherited.py`, `tests/test_listing_license_seller_acceptance.py`.

**Risk/rollback:** bulk default mistaken for authority. Nullable acceptance and explicit 409 prevent it. Reverting flag leaves public contract pages available and purchases gated.

### 12.7 Chunk G — operations and real test-pool E2E

**Files:** runbooks `listing-licenses.md`, `INDEX.md`, `ERRORS.md`; E2E specs/fixtures only in the repository that owns the existing test harness. No production code is added here except a narrowly reviewed defect found by the E2E.

**AC/tests:** §14 passes from stable candidates with real test accounts and all evidence retained; runbook checker clean; exact deployed SHAs, feature flags, migrations, route inventory and Event Ledger ids recorded. Risk is confusing local/synthetic success with live completion; Gate 4 requires browser, agent and every-door evidence on the named pool. Rollback turns the flag off while preserving records/public texts.

### 12.8 Dispatch and enablement

Dispatch **A → B → C → (D ∥ E) → F → G**. Cross-repo parts of one chunk are separate PRs tied by a manifest and are not considered Gate 3 complete until every SHA is unanimously approved. Production remains default-off through G. Enable only after migrations, seed digests, terms 1.1 copy, stable-image identities and §14 evidence are reconciled. No Open/CDLA card ships; adding it needs the documented stock-licence procedure and a seller request.

## 13. Operator runbook required in chunk G

Create `listing-licenses.md` and link it from `INDEX.md`; add error-code entries to `ERRORS.md`. The page must explain:

- purpose, flag and safe enable/disable order;
- tables and immutability rules for `license_documents`, `seller_license_acceptances`, `license_acceptances`, listing/version snapshots and organisation identity;
- exact seeded instruments, canonical extraction/hashing, published vectors and how to verify deployed seed digests;
- how to add a stock licence: product authority first, normative text and summaries, code/version/variants, vectors, seed, public URL/JSON-LD, cross-client tests, unanimous review, then enablement (never edit a released version);
- custom-upload quarantine/scanning and how to investigate each refusal without exposing uploaded content;
- how to terminate after refund/dispute outcome, verify the Event Ledger row, deletion due date and all-door refusal, and record buyer deletion confirmation;
- how support answers a buyer asking for their record: authenticate the recorded party, use the order-history record endpoint, provide the on-demand PDF and component hashes, never reconstruct a contract from current listing data;
- inherited listing/terms 1.1 pending reconciliation, `SELLER_TERMS_ACCEPTANCE_PENDING`, identity conflicts, hash-stale errors, route-inventory failures and x402-invalid-config response;
- evidence/retention rules and the fact that ai.market is not a party and support gives no legal advice.

`scripts/check.py` must pass after INDEX/ERRORS edits. Runbook instructions may operate the feature but may not broaden provider, production, money or customer-data authority.

## 14. Gate 4 E2E on the standing test-account pool

The actors are the `*-0N@e2e-test.ai.market` test accounts, not employees or real customers: `seller-01` and `buyer-02` are the testers. Use stable candidate images and a test payment path; record exact image/commit/migration/flag identities.

1. `seller-01` completes legal identity and terms 1.1, then publishes one listing with Standard/training yes through Seller Workspace. Capture the two-card/default-toggle screen, covenant confirmation, seller acceptance id and listing/version hashes.
2. The same seller publishes a second listing through AIM Data with a clean custom PDF/text and the permitted rider. Prove upload hygiene receipt, exact source/hash bytes, gateway/publish fold and amber notice. A separate attempt with a secret pattern and a conflicting marketplace term must refuse without an active document.
3. `buyer-02` opens the Standard listing in a normal browser, downloads and hashes the full text before purchase, completes the Buy screen, pays, and downloads the signed record. Verify one order, one acceptance, frozen seller/buyer identities, exact component hashes and green badge.
4. `buyer-02` purchases the custom listing through the authenticated agent API using returned hashes and `authority_confirmed:true`; verify typed name null, principal/credential captured, custom PDF/text and rider/covenant in the record, and seller sales history renders the same record.
5. Before refund, exercise every generated delivery-door inventory case and prove valid access. Refund the Standard order; verify one audited `active → terminated` transition, 30-day deletion obligation, buyer deletion-confirmation control and seller notice.
6. After termination, exercise every door again, including async fulfilment reply, range/token reuse, scoped credential refresh, Seller Workspace per-file grant, AIM Data members, agent data/artifact and legacy JWT URL. Every case returns 403/409 (legacy 404), discloses no secret/URL/redirect/credential and transfers zero bytes.
7. Update `account-teardown.md` H.1 legal-record inventory with `license_acceptances`, `license_acceptance_events`, `seller_license_acceptances` and custom `license_documents` (RESTRICT; legal-hold exemption per Gate 1 §6.11). Run the issuance-versus-termination race, x402 hostile-flag test, seller-terms-pending inherited listing test, hash-vector tests in all three implementations, migration/schema checks, full affected test suites and runbooks `scripts/check.py`.

Completion evidence is the retained browser/agent transcripts, route inventory, test logs, record downloads and hashes, Event Ledger ids, database cardinality checks, deployed identities and unanimous Gate 3 receipts. A local fixture, healthy service, merged PR, or one successful download is not Gate 4 completion.
