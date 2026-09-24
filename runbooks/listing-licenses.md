---
title: Listing licences and signed records
owner: vulcan
last_verified: '2026-09-23'
aliases: [listing licenses, Standard Data Licence, seller licence, signed licence record]
error_signatures:
  - SELLER_TERMS_ACCEPTANCE_PENDING
  - LICENSE_SELECTION_REQUIRED
  - LICENSE_SELECTION_INVALID
  - WEBSITE_LICENSE_PUBLISH_REQUIRED
  - LICENSE_ACCEPTANCE_STALE
  - LICENSE_ACCEPTANCE_REQUIRED
  - LICENSE_ACCEPTANCE_INVALID
  - LICENSE_AUTHORITY_REQUIRED
  - LICENSE_RIDER_ACCEPTANCE_STALE
  - LEGAL_IDENTITY_CONFLICT
  - LEGAL_IDENTITY_REQUIRED
  - SELLER_LEGAL_IDENTITY_REQUIRED
  - BUYER_LEGAL_IDENTITY_REQUIRED
  - LICENSE_DOCUMENT_INVALID
  - LICENSE_SECRET_DETECTED
  - LICENSE_PROHIBITED_TERMS
  - LICENSE_SIZE_INVALID
  - LICENSE_MIME_MISMATCH
  - LICENSE_TEXT_INVALID_UTF8
  - LICENSE_TEXT_NOT_NFC
  - LICENSE_LANGUAGE_NOT_ENGLISH
  - LICENSE_PDF_INVALID
  - LICENSE_PDF_ACTIVE_CONTENT
  - LICENSE_MALWARE_DETECTED
  - LICENSE_MALWARE_SCAN_UNAVAILABLE
  - LICENSE_UPLOAD_UNAVAILABLE
  - LICENSE_TERMINATED
  - LICENSE_NOT_TERMINATED
  - LICENSE_TERMINATION_ACTOR_REQUIRED
  - LICENSE_TERMINATION_INVALID
  - missing_active_markers
  - LISTING_LICENSES_ENABLED=true is incompatible with X402_ENABLED=true
---

# Listing licences and signed records

Operate the seller's listing licence, buyer's signed record and terms 1.1 gate. ai.market is not a party to the seller–buyer licence. Support supplies records and process facts, not legal advice. Source was read at backend `0d21ec3f` and frontend `9c9e4f1`; these are source pins, not a claim about the deployed images. Authority: `specs/BQ-LISTING-LICENSES-S1735-GATE2.md` §§12.7–14 and amendment 1. Licences are enabled in production as of 2026-09-23T22:31Z (Event `15ce797f`), with `TERMS_1_1_EFFECTIVE_AT=2026-09-23T22:30:00Z`, terms 1.1 hash `502c5f3190a560b32320ad8ea860dca60c7ba5e2f2fa907bc72072a0ec361c82`, and `X402_ENABLED=false` (Max `18fab669`; x402 remains off and is not implemented). Amended §14 Seller Workspace listing and buyer purchase/refund proof runs in the [S1656 money-path test environment](../money-path-test-environment.md). Production retains read-only health, current-terms and document-hash checks.

## Capabilities

| Capability | State at source pins | Backing code | Proof to keep |
| --- | --- | --- | --- |
| Standard, custom text/PDF, rider and covenant hashes | Shipped, flag controlled | backend `app/services/license_hashing.py`, `app/resources/licenses/`; frontend `api/listingLicenses.ts` | Six §3.2 vectors and served document hashes |
| Seller signatures and inherited listing binding | Shipped, flag controlled | backend `app/services/seller_license_service.py`, `app/services/inherited_listing_license_service.py`, `app/services/terms_acceptance_service.py` | Real 1.1 terms row, derived acceptance id, listing/version hashes |
| Buyer record, termination and delivery refusal | Shipped | backend `app/services/license_acceptance_service.py`, `app/services/license_record_service.py`, `app/services/license_access_service.py`, `app/api/v1/endpoints/orders.py` | One acceptance/order, lifecycle Event Ledger id, every-door results |
| Browser record and terms pages | Shipped | frontend `api/licenseRecords.ts`, `app/dashboard/orders/[id]/license-record/page.tsx`, `app/dashboard/sales/[id]/license-record/page.tsx`, `app/legal/terms/page.tsx` | Browser transcript and downloaded hashes |

## Architecture and records

| Store | Meaning and mutation rule |
| --- | --- |
| `license_documents` | Seller-owned custom text or private original PDF, raw `source_sha256`, canonical `license_sha256`, clean hygiene report and status. Owner and referenced document FKs are `RESTRICT`; public `/api/v1/licenses/custom/{license_sha256}` is a notice, not the original. See `app/models/license_document.py`, `app/services/custom_license_service.py`, `app/api/v1/endpoints/license_documents.py`. |
| `seller_license_acceptances` | Append-only seller signature with frozen legal name, jurisdiction, signer, exact instrument hashes and source (`submission` or `platform_terms_v1.1`). UPDATE/DELETE trigger refuses changes. See `app/models/seller_license_acceptance.py`, `alembic/versions/20260922_001_s1735_listing_licenses.py`. |
| `license_acceptances` | One signed contract per order, frozen buyer and seller identities, listing/version, instrument bytes/hashes, signer/channel. Only `status: active → terminated` may change; DELETE and contract-field UPDATE refuse. See `app/models/license_acceptance.py`, the same migration and `app/services/license_acceptance_service.py`. |
| `license_acceptance_events` | Append-only `terminated` and `deletion_confirmed` facts, each linked to `allai_event_ledger`; one of each type per acceptance. Termination records `deletion_due_at`. See the same model, migration and service. |
| `listings`, `listing_versions`, `orders.listing_snapshot` | Current selection, publication-time version copy and purchase-time frozen snapshot. They carry all component hashes and seller acceptance binding. A later listing or seed edit cannot rewrite a signed order. See `app/services/seller_license_service.py`, `app/services/order_service.py`, migration `20260922_001_s1735_listing_licenses.py`. |
| `organizations`, `terms_acceptance` | Organization legal name/jurisdiction are reconciled against billing identity; terms acceptance retains signer, scope, version, hash and time. Conflict is a refusal, not a reason to overwrite either source. See `app/services/legal_identity.py`, `app/services/terms_acceptance_service.py`. |

The party-authorized `GET /api/v1/orders/{order_id}/license-record` and `?format=pdf` render from the immutable acceptance. Buyer and seller each see their **own** legal identity; the counterparty appears only as `identified to ai.market under order X`, bound to that order. A stranger gets 404. The PDF is an on-demand projection, not the database authority. Code: backend `app/services/license_record_service.py`, `app/api/v1/endpoints/orders.py`; frontend `api/licenseRecords.ts`.

## Instruments and hashes

The exact released resources are `app/resources/licenses/standard-1.0.md`, `ai-training-rider-1.0-true.md`, `ai-training-rider-1.0-false.md`, and `marketplace-listing-1.0.md`. Public full text/JSON and hashes are served at `/api/v1/licenses/standard/1.0/{ai-training|no-ai-training}`, `/api/v1/licenses/ai-training-rider/1.0/{permitted|not-permitted}`, and `/api/v1/licenses/marketplace-listing/1.0` (`app/api/v1/endpoints/license_documents.py`). The custom URL exposes only its notice; an authorized listing document download uses `/api/v1/listings/{listing_id}/license-document?download=true`.

`app/services/license_hashing.py` converts Unicode to NFC, CRLF/CR to LF, strips trailing horizontal whitespace and supplies one final LF. It canonicalizes declared JSON parameters, rejects duplicate/unknown keys, numbers in parameter schemas and non-boolean training values. Each SHA-256 hashes length-prefixed UTF-8 domain, code, version, canonical text and canonical JSON parameters. Custom uploads also bind raw `source_sha256`; PDF canonical text is JSON with content type and source hash, while the original PDF bytes are retained verbatim. Never hash a rendered PDF or a summary as the contract.

| §3.2 vector | Canonical bytes | SHA-256 |
| --- | ---: | --- |
| Standard 1.0, training yes | 6557 | `4b05dbcd0c186746d3deab6c68beaebba88610de8e85122efb4d527edb1263c6` |
| Standard 1.0, training no | 6613 | `e83e03bb731fee832d108ef77689f7ff49e3409f88124b483b2ef34ca7ba3821` |
| Rider 1.0, permitted | 438 | `f9785144dc4d48af6446512cbabd03431a35015d71b92260f4dcfab164084140` |
| Rider 1.0, not permitted | 317 | `8878e2fb3327378e90a1d9206da9aa2b419255872cdfa6a883c0d2688f768416` |
| Covenant 1.0 | 1211 | `a91234b67bf7467a0c80f6e1caa47b563032e94751146901b796eaaf220431af` |
| Custom PDF v1, `%PDF-1.4 test`, training yes | 118 | `80a42b3f3b022e19ce60ad7b2cf59b524877b92320ec49f8af859833764a55f4` |

These are asserted by backend `tests/test_listing_license_hash_vectors.py`; the first five are also pinned in frontend `api/listingLicenses.ts`. Verify the **deployed** backend seed by recording its image/source SHA and running the hash functions inside that serving image:

```bash
rtk proxy railway ssh -e production -s ai-market-backend 'python -c "from app.services.license_hashing import hash_standard_license,hash_rider,hash_covenant,hash_custom_pdf; print(hash_standard_license({\"ai_training\":True})); print(hash_standard_license({\"ai_training\":False})); print(hash_rider({\"ai_training\":True})); print(hash_rider({\"ai_training\":False})); print(hash_covenant()); print(hash_custom_pdf(b\"%PDF-1.4 test\"))"'
```

Compare all six lines in order with the table, and compare live `?format=json` responses for the five stock variants too. The PDF test vector is computed by `hash_custom_pdf`, not a public seed endpoint. A source checkout test alone does not prove which resources are deployed.

## Agent capabilities

| Actor | Operation | Scope and evidence |
| --- | --- | --- |
| Seller browser/API | Sign a chosen Standard or custom selection, then publish | Seller capability, own clean document, legal identity and fresh component hashes; `app/services/seller_license_service.py` |
| Buyer browser | Review full text and hashes, sign once, open order-history JSON/PDF | Authenticated buyer; `app/api/v1/endpoints/orders.py`, frontend `components/BuyButton.tsx` |
| Authenticated agent | Purchase with returned hashes and `authority_confirmed:true` | Bound principal/credential, typed name null; `app/services/license_acceptance_service.py` |
| Operator | Check deployment/config/schema and reconcile evidence; disable for a licence defect or unsafe enabled configuration | Existing Railway/DB authority only; no direct record edit or ad-hoc contract reconstruction |

## How to operate

```yaml operate
- id: E-01
  trigger: Enable listing licences in production under the S1738 decision (procedure retained as the enablement record)
  pre_conditions:
    - Exact deployed backend/frontend SHAs and image identities match the reviewed candidates; record them
    - Production Alembic head is s1738_preserve_binding_summary; /health has no model/schema drift
    - X402_ENABLED is not true; record the nonsecret flag state
    - Deployed seed digests match all six §3.2 vectors as described above
    - The terms 1.1 source document has one effective-date placeholder and the chosen UTC RFC 3339 instant/hash are recorded
    - The S1656 money-path test environment is designated for amended §14 Seller Workspace listing and buyer purchase/refund proof
  tool_or_endpoint: Railway CLI on the explicitly selected production environment; public /health and /api/v1/legal/terms/current
  argument_sourcing:
    effective_at: S1738 launch instant chosen and recorded by the operator in UTC RFC 3339 (example shape 2026-09-23T12:00:00Z)
    service: ai-market-backend in Railway production (see ai-market-backend.md Deployment)
  idempotency: CHECK CURRENT VALUES BEFORE EACH SET; EACH SET REDEPLOYS
  expected_success:
    shape: both deployments SUCCESS, health clean, current terms version 1.1 and hash equal to dated source bytes
    verification: confirm /health, current terms 1.1 and its effective instant/hash, and the served terms-document hash in production; retain receipts. Run amended §14 in S1656.
  expected_failures:
    - signature: LISTING_LICENSES_ENABLED=true is incompatible with X402_ENABLED=true
      cause: startup configuration refuses the combination; keep licence flag off and reconcile X402 state
    - signature: terms hash mismatch or unhealthy /health
      cause: wrong effective instant, source/image or schema; turn flag off and investigate
```

From the established Railway-linked operator checkout, use `rtk proxy railway variables -e production -s ai-market-backend --json` only through a filter that prints the named nonsecret values; do not dump the full variable set. Check `alembic_current` and `alembic_head` in `https://api.ai.market/health`; both must be `s1738_preserve_binding_summary`. Compute the expected terms hash from the pinned `app/legal/terms_v1_1.md` **after** substituting its single `{{TERMS_1_1_EFFECTIVE_AT}}` byte placeholder with the selected instant, exactly as `app/core/config.py:canonical_terms_document` does. With `EFFECTIVE_AT` set to the selected UTC instant, this read-only local calculation emits the expected digest:

```bash
rtk git -C /Users/max/Projects/ai-market/ai-market-backend show 0d21ec3f:app/legal/terms_v1_1.md | rtk proxy python3 -c 'import hashlib,sys; source=sys.stdin.buffer.read(); token=b"{{TERMS_1_1_EFFECTIVE_AT}}"; assert source.count(token)==1; print(hashlib.sha256(source.replace(token,sys.argv[1].encode("ascii"))).hexdigest())' "$EFFECTIVE_AT"
```

`TERMS_HASH_SHA256`, if configured, must equal that computed hash. The following commands are the enabled sequence after prerequisites are recorded:

```bash
# Set EFFECTIVE_AT to the recorded UTC instant in this shell; do not reuse the example date above.
rtk proxy railway variables -e production -s ai-market-backend --set "TERMS_1_1_EFFECTIVE_AT=$EFFECTIVE_AT"
rtk proxy railway deployment list -e production -s ai-market-backend
# Wait for newest deployment SUCCESS and recheck /health before the second set.
rtk proxy railway variables -e production -s ai-market-backend --set LISTING_LICENSES_ENABLED=true
rtk proxy railway deployment list -e production -s ai-market-backend
rtk proxy curl -fsS https://api.ai.market/health
rtk proxy curl -fsS https://api.ai.market/api/v1/legal/terms/current
```

The newest deployment must be SUCCESS and serve the intended image. The public terms response must be HTTP 200 with `terms_version: "1.1"`, `effective_at` equal to the selected instant and `terms_hash_sha256` equal to the locally calculated SHA-256. Fetch `/api/v1/legal/terms/document` and hash its raw bytes too. `app/api/v1/endpoints/legal_terms.py` registers `/current` and `/document` only at flag-on startup. The redeploy caused by setting `TERMS_1_1_EFFECTIVE_AT` alone (flag still off) still serves legacy terms 1.0; only the flag-on redeploy serves 1.1. Do not call a clean `/health` or a successful set command Gate 4 completion.

```yaml operate
- id: E-02
  trigger: A licence defect is found in production or in the S1656 amended §14 proof, or the enabled configuration is unsafe; a probe expectation mismatch alone is not a defect until the refusal and absence of writes are checked
  pre_conditions:
    - Capture the failure, exact deployment/flag identity and affected order ids without secrets
  tool_or_endpoint: railway variables -e production -s ai-market-backend --set LISTING_LICENSES_ENABLED=false
  idempotency: SAFE TO REPEAT AFTER READING CURRENT FLAG
  expected_success:
    shape: newest redeployment SUCCESS and /health clean; new purchase UI/terms route return to flag-off behavior
    verification: preserve signed rows, lifecycle events, public licence pages, source logs and failed-step receipts
  expected_failures:
    - signature: deployment not SUCCESS
      cause: platform/build failure; keep admission closed and escalate with deployment id
```

Flag-off restores legacy new-purchase behavior but does **not** erase `seller_license_acceptances`, `license_acceptances`, events or custom documents. Existing signed records remain downloadable by a recorded party, their termination and hash gates still apply, and public immutable stock/custom-notice pages remain available (`app/services/license_access_service.py`, `app/api/v1/endpoints/orders.py`, `app/api/v1/endpoints/license_documents.py`). Do not down-migrate a database with signed rows; the migration refuses this.

```yaml operate
- id: E-03
  trigger: Diagnose inherited terms pending or pre-F terms 1.0 wrong-hash history
  pre_conditions:
    - Read-only database connection through the existing approved production procedure
  tool_or_endpoint: SELECT only from terms_acceptance, listings, listing_versions and seller_license_acceptances
  idempotency: READ ONLY
  expected_success:
    shape: counts, dates and IDs sufficient to reconcile each affected seller without exposing terms content
    verification: seller personally accepts real terms 1.1; inspect new terms id, derived seller acceptance id and listing/version bindings
  expected_failures:
    - signature: SELLER_TERMS_ACCEPTANCE_PENDING
      cause: inherited listing has no real current seller terms acceptance/binding
```

Pre-F production stored 1.0 acceptances with the vectorAIz text hash `f125dc59ac17b342f6a1dd645a8ac2c5894416d32bf8756cace2f77534c99341`. Max Event `487f2379` keeps those rows unchanged as history; affected accounts re-accept 1.1 after enable. Use this read-only query for the affected-account inventory, returning account IDs, counts and dates only (no names, emails, text or IP):

```sql
BEGIN READ ONLY;
SELECT accepted_by_user_id, count(*) AS wrong_hash_rows,
       min(accepted_at) AS first_accepted_at, max(accepted_at) AS last_accepted_at
FROM terms_acceptance
WHERE terms_version = '1.0'
  AND terms_hash_sha256 = 'f125dc59ac17b342f6a1dd645a8ac2c5894416d32bf8756cace2f77534c99341'
GROUP BY accepted_by_user_id ORDER BY accepted_by_user_id;
COMMIT;
```

Inherited listings are viewable but purchase returns `409 SELLER_TERMS_ACCEPTANCE_PENDING` until the seller signs current 1.1 terms with authority and legal identity. That same acceptance transaction creates the append-only `platform_terms_v1.1` seller record and binds eligible `listings` and `listing_versions`; it does not fabricate an earlier acceptance date (`app/services/inherited_listing_license_service.py`, `app/services/terms_acceptance_service.py`, `app/services/order_service.py`). Legacy AIM Data publish is withdrawn: with the flag on, `WEBSITE_LICENSE_PUBLISH_REQUIRED` refuses it before a write. New self-hosted gateway users publish and license through the website, per amendment 1 and `app/services/seller_workspace_listing_guard.py`.

```yaml operate
- id: E-04
  trigger: Buyer requests their signed record, or a completed full refund/dispute requires termination proof
  pre_conditions:
    - Authenticate the recorded party and bind the request to its order id
    - For termination, use the existing verified refund or dispute-resolution flow, never direct SQL
  tool_or_endpoint: GET /api/v1/orders/{order_id}/license-record and ?format=pdf; POST /api/v1/orders/{order_id}/license-record/deletion-confirmation is buyer-only after termination
  idempotency: READ RECORD REPEATABLY; TERMINATION AND BUYER CONFIRMATION ARE SINGLE EVENTS
  expected_success:
    shape: role-appropriate record/PDF, exact licence/rider/covenant hashes, one termination Event Ledger id and a 30-day deletion_due_at
    verification: reconcile acceptance.status, license_acceptance_events, allai_event_ledger and every generated delivery door
  expected_failures:
    - signature: LICENSE_TERMINATED
      cause: signed order was terminated; delivery must refuse
    - signature: LICENSE_ACCEPTANCE_STALE
      cause: frozen order snapshot and acceptance component hashes differ; stop issuance and investigate
```

Support opens the order-history record endpoint as the authorized buyer, supplies its on-demand PDF and component hashes, and checks the buyer-facing counterparty reference. Never reconstruct a contract from current listing text or expose the seller's legal name/jurisdiction. The seller's sales-history view has its own authorized projection. After a completed **full** refund, `app/services/refund_processing_service.py` calls `terminate_license_acceptance` in the same transaction; a dispute resolution that records a full refund uses `app/services/order_service.py`. Partial refunds do not terminate by this path. Verify `license_acceptances.status='terminated'`, one `license_acceptance_events.event_type='terminated'` with `deletion_due_at = occurred_at + 30 days`, and its `event_ledger_id` pointing to `allai_event_ledger.event_type='license_acceptance.terminated'` (`app/services/license_acceptance_service.py`). Record seller notice and buyer deletion obligation. The buyer's deletion-confirmation control appends a separate event and Event Ledger row; do not mark it confirmed from silence.

Use the generated `tests/test_listing_license_route_inventory.py` route set and `tests/test_listing_license_delivery_gate.py`/`test_listing_license_termination.py` for every-door coverage. Before refund prove valid access; after termination require 403/409 (legacy 404), zero bytes and no URL, redirect, secret or credential across async fulfilment, range/token reuse, scoped refresh, Seller Workspace grants, legacy AIM Data members, agent data/artifact and legacy JWT URL. Retain route list and request/response evidence; do not equate one refused download with coverage.

## Add a stock licence

Get product authority first. Freeze normative full text and buyer/seller summaries, code, version and variants; add new resource bytes and published vectors in `app/resources/licenses/` and `app/services/license_hashing.py`; seed only that exact version; expose its immutable public URL and JSON-LD (`app/api/v1/endpoints/license_documents.py`, `app/services/public_listing_jsonld.py`); update backend/frontend selection, hash and record tests; obtain unanimous exact-candidate review; then include it in a separate enablement decision. Never edit released `1.0` bytes or reinterpret a signed hash. The sequence is Gate 2 §13 product governance, not an existing one-command stock-licence tool.

## When it breaks

| Symptom | Cause | Repair |
| --- | --- | --- |
| `LICENSE_SELECTION_REQUIRED` (422) | Flag on and a listing create/update arrived without `license_selection` (`app/services/listing_management_service.py`) | Seller must choose Standard or upload their own licence in the website listing form or Seller Workspace; old clients must upgrade. |
| `422 {"detail":"Request validation failed"}` on Seller Workspace publication create | With the flag on, `ListingPublishRequest` requires `license_selection`; the Seller Workspace route sanitises schema validation errors (`app/schemas/seller_listing_publication.py`, `app/api/v1/endpoints/seller_workspace.py`). This is distinct from `LICENSE_SELECTION_REQUIRED` on the unlisted-listing publish path (`app/services/listing_management_service.py`). | Confirm the request was refused with no write before treating a probe expectation mismatch as a defect. The production seller probe (`e2e-harness` `b039e089`) expected `LICENSE_SELECTION_REQUIRED` from `POST /api/v1/seller-workspace/listing-publication` without `license_selection`, but received this 422 at 22:49:39Z (Railway deploy `8138aafd`, Event `99d5ea8c`). Refusal with no write meets Gate 2 §9; send a valid selection for publication. |
| `LICENSE_SELECTION_INVALID` (422) | `license_selection` shape wrong: Standard with a version other than 1.0 or with custom fields, or custom without document id/rider hash (`app/schemas/license_selection.py`) | Resend a valid selection from the current UI; for custom, finish the upload/scan first so a document id exists. |
| `LICENSE_ACCEPTANCE_STALE` or `LICENSE_RIDER_ACCEPTANCE_STALE` | Client selection, document or order snapshot hash differs from server recomputation | Stop purchase/issuance; fetch canonical served text and hashes, compare selected version/variant and stored snapshot; have the actor review and sign fresh bytes. Do not edit old acceptance. |
| `LEGAL_IDENTITY_CONFLICT` / `LEGAL_IDENTITY_REQUIRED` | Billing and typed name/jurisdiction differ, or one is missing | Reconcile through returned `reconciliation_url` and real identity evidence; never silently prefer the typed value (`app/services/legal_identity.py`). |
| `SELLER_TERMS_ACCEPTANCE_PENDING` | Inherited seller has not genuinely accepted 1.1 | Seller completes `/api/v1/legal/terms/accept`; verify derived binding. Do not insert a synthetic row. |
| `WEBSITE_LICENSE_PUBLISH_REQUIRED` | Frozen legacy publish path used with flag on | Use website/Seller Workspace publish; confirm no listing/document/acceptance write occurred. |
| Upload `LICENSE_SIZE_INVALID`, `LICENSE_MIME_MISMATCH`, `LICENSE_TEXT_INVALID_UTF8`, `LICENSE_TEXT_NOT_NFC`, `LICENSE_LANGUAGE_NOT_ENGLISH`, `LICENSE_PDF_INVALID`, `LICENSE_PDF_ACTIVE_CONTENT`, `LICENSE_SECRET_DETECTED`, `LICENSE_PROHIBITED_TERMS`, `LICENSE_MALWARE_DETECTED`, `LICENSE_MALWARE_SCAN_UNAVAILABLE`, or `LICENSE_UPLOAD_UNAVAILABLE` | Quarantine, ClamAV, content, secret or policy check failed | Record only error code, request id, size/type and non-content digests; check scanner availability and the named check in `app/services/custom_license_service.py`. Seller submits a clean corrected file. Never print, email or log rejected bytes; no active document is created by a refusal. |
| `missing_active_markers` assertion in `tests/test_listing_license_route_inventory.py` | New delivery route lacks the active-acceptance marker | Keep enablement closed; enumerate derived route set and add the reviewed gate before another deploy. This is a test failure, not an HTTP error code. |
| `LISTING_LICENSES_ENABLED=true is incompatible with X402_ENABLED=true` | `app/core/config.py` startup validator rejects both flags | Keep licence flag off; reconcile actual X402 setting. Do not bypass the validator. |
| `LICENSE_TERMINATED`, `LICENSE_ACCEPTANCE_REQUIRED` or `LICENSE_NOT_TERMINATED` | Missing/ended contract or premature deletion confirmation | Check order and immutable acceptance/event rows. Never issue a new token or directly flip status. |

## Repair, evidence and retention

Preserve exact backend/frontend image and commit SHAs, Alembic current/head, named flag values, terms effective instant/document hash, seed vector output, browser and authenticated-agent transcripts, listing/version/order hashes, record downloads, route inventory, before/after database cardinalities, test logs and Event Ledger IDs. Keep original failures. Store private record/PDF and any IDs in the approved restricted evidence location; public runbook receipts contain no identity, token, upload or customer data. Legal records and custom documents are held under `account-teardown.md` H.1 RESTRICT/legal-hold rules; no routine teardown deletes them. A local fixture, healthy `/health`, merged PR, or single download does not close amended §14.

## Changes

- 2026-09-23, S1738: first operator page from backend `0d21ec3f`, frontend `9c9e4f1`, Gate 2 §13 and amendment 1. Licences enabled at 22:31Z (Event `15ce797f`). The flag was off from about 22:49–22:57Z after a seller probe expected the wrong error for a refused, no-write request (Event `99d5ea8c`); Max `36740951` re-enabled it with deploy `b56e4c48` SUCCESS (Event `b19fa14d`). Amended §14 Seller Workspace and buyer purchase/refund proof moved to S1656 because production takes live payments only, hides test listings from buyers, and its test seller has no cloud source or live payouts (buyer side previously placed there by Max `2806dd13`).
