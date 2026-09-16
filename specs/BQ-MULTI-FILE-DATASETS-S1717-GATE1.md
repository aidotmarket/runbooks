# BQ-MULTI-FILE-DATASETS-S1717 Gate 1 design specification

**Status:** Gate 1 candidate; independent review pending (GLM + DeepSeek; CC waived by Max). No implementation approval.
**Build Queue entity:** `build:bq-multi-file-datasets-s1717` (P0).
**Authority:** Max product ruling 2026-09-16, Event Ledger `a790fb22-e575-4455-97f6-95170385d085`: "a product is a directory, not a file"; Max 2026-09-16: the verified label is voluntary and a customer must be able to list without it.
**Trigger:** support ticket `T-2026-000785` — the first real seller (eolymp, 21,000 files; "Acid Trap Dataset" folder) uploaded a directory and AIM Data produced one dataset card per file, one card stuck in Processing at 0 rows, and the seller asked whether he must merge everything into one file.
**Author:** Mars (direct-authored: MP quota exhausted until 2026-09-20; Mars does not vote).
**Source pins:** `aim-data@b5629a50d5cebfb693fdfc07e93a7124a75cb88b` (main after PR #61), `ai-market-backend@8ed234af49b3ba7d8fa84e363c5fe8263f40a23a` (main after PR #406), runbooks main `441c70e`. Line references were read with `git show` at these pins.

## 1. Problem

A seller's product is a directory: data blocks, a free sample, a README, a description, sometimes thousands of files. Today every layer models a product as one file:

- AIM Data bulk upload (`app/routers/datasets.py:426`, BQ-108) creates one `DatasetRecord` per uploaded file (`app/models/dataset.py:39-60`: `original_filename`, `storage_filename`, `file_type`, `processed_path`, `listing_id`; `batch_id` and `relative_path` exist but only group notifications). Processing (`app/services/processing_service.py:232`) profiles and runs allAI metadata per record. Publishing (`app/routers/marketplace_publish.py:403`) publishes one record as one listing and sets `listing_id` on that record.
- The publish receiver's `VersionPublish` contract already carries `object_count`, `total_size_bytes` and a `manifest_hash` over `{"objects": [...]}` (`marketplace_publish.py:110-118`, `:246`), and the Seller Workspace S3 route publishes a prefix with N objects (`:281-293`). The local-file route always publishes one object; the interop record pins `object_count == 1` for it (`specs/SELLER-ROUTE-INTEROP-S1711.md:12`).
- Delivery for a local-file listing streams one dataset file over the Trust Channel (`app/services/fulfillment_service.py:106-219`: "Looks up the dataset, streams it back in 64KB chunks"); the S3 route delivers one presigned object (`:284`). The buyer download unification item already asks how multi-file grants work (`specs/BQ-BUYER-DOWNLOAD-UNIFICATION-S1711-GATE1.md:34`).
- The paid verification scan (`specs/BQ-DATA-VERIFICATION-S1590-GATE1.md` §6) is already multi-object: the manifest carries `objects[]` keyed by customer-held commitments and `coverage.skipped[]` with fixed reasons. It scans "the registered source", which for a local dataset is one file today.
- The free sample is "approved rows" of the one file (`DatasetDetail.tsx` `sampleDecision === "approved_rows"`), not a chosen subset of files.

Consequences: a real seller cannot list a real dataset without merging it by hand; a 21,000-file directory would create 21,000 cards and 21,000 allAI metadata passes; documentation files become "datasets"; and the seller's question ("must I merge?") is the honest answer today. This is the first wall every serious seller hits, before the verified label even enters the picture.

## 2. Decision (design authority)

**D1. A dataset is a directory.** One `DatasetRecord` represents an uploaded directory tree (or a single file, which is the one-member case). Its members are files with a stable relative path, size, content hash, detected type and a **role**: `data`, `sample`, `documentation`, `other`. Roles are detected by convention and always editable by the seller before publish (defaults: tabular/document files under `SAMPLE/`, `sample/`, or named `sample*` → `sample`; `README*`, `HOW_TO_USE*`, `*DESCRIPTION*`, `LICENSE*` → `documentation`; everything else tabular/document → `data`; unsupported types → `other`, never processed, never delivered unless the seller marks them `data`).

**D2. Processing is per directory, bounded.** Profiling, PII scan and allAI metadata run once per dataset over a deterministic sample of members (fixed policy: up to N data members chosen by stable hash order, size-capped), not once per file. Documentation members feed the listing description as seller-supplied context (quoted, never executed). The dataset shows one status; per-member failures are recorded as member status with a fixed reason (`unsupported_type`, `too_large`, `parse_failed`, `timeout`) and never leave the dataset spinning — an "endless Processing at 0 rows" card is a bug this design removes.

**D3. One listing per dataset, N objects.** The local-file publish path emits the existing `VersionPublish` contract with `object_count = number of data members`, `total_size_bytes` = their sum, and `manifest_hash` over the member manifest (relative path, size, SHA-256, role). The `object_count == 1` interop pin is retired for the local route. The listing's public schema/row-count summary is the aggregate of data members (documented as such), not a single file's.

**D4. Free sample = chosen member files.** The seller marks which members are the sample (default: role `sample`); the disclosure snapshot lists them by relative path, size and hash; the existing "approved rows" sample remains available for single-file datasets. Sample members are delivered to buyers before purchase through the existing sample surfaces; data members only after purchase.

**D5. Delivery is the whole set.** A purchase delivers every data member. The Trust Channel local route streams members sequentially under one transfer manifest (per-member SHA-256, ordered, resumable per member); the S3 route already presigns per object. The buyer download door (S1711) receives a manifest with N objects and lets the buyer fetch each or a server-assembled archive; this specification does not choose zip-vs-manifest — it requires that S1711 Gate 1 decide it with `object_count > 1` as the normal case, not the exception.

**D6. Verification covers the directory.** The S1590 scan runs over all data members as `objects[]`; sample and documentation members are excluded from facts and listed under `coverage.skipped[]` with reason `excluded_by_role`. No change to the manifest, privacy boundary, payment or publication contract; the quote's `source_size_class` and hold follow from the set.

**D7. The verified label stays voluntary, and says so.** Listing never depends on verification, a card, or a quote. Seller-facing copy on the dataset page reads "Optional: add a verified shape label" above the verification panel, and `data-verification-seller-journey.md` §B states in its first sentence that the whole procedure is optional and seller-initiated. (Confirmed against `aim-data` `DatasetDetail.tsx:1323`/`:1665`: the panel renders only after a listing exists and does nothing until clicked; card only at paid start per S1646.)

**D8. Scale.** 21,000 members must be a normal upload: member registration is streamed and idempotent by (dataset, relative path, hash); the UI shows the directory as one card with a member table (paged, filterable by role/status); re-uploading the same directory updates changed members only. Hard caps are policy settings (members per dataset, bytes per dataset) with a clear refusal, not a hang.

## 3. Non-goals

No change to pricing, commission, payout, the customer-to-cloud manifest, the S1590 privacy boundary, the Seller Workspace S3 model (it already is a prefix), the Trust Channel encryption, or the buyer's identity/access rules. No merging of member files server-side. No cross-dataset bundles. No public per-member browsing beyond the sample members.

## 4. Customer-visible behaviour

1. Upload a folder → one card "Acid Trap Dataset" with member count, total size, one status.
2. Open it → member table with role chips (data / sample / documentation / other), per-member status and reason, "Set role" and "Mark as sample" actions; profiling summary over the data members; description drafted from documentation members for the seller to approve.
3. Publish → one listing; buyers see one product with N files, aggregate schema/row summary, the sample members downloadable.
4. Buy → all data members delivered; the order page shows a file list with per-file progress and hashes.
5. Optional: "Add a verified shape label" → the S1590 flow over the data members; the report's coverage section shows N objects scanned, sample/docs excluded by role.
6. Existing single-file datasets and listings keep working unchanged (one-member directories).

## 5. Interactions and sequencing

- `build:bq-buyer-download-unification-s1711` (planned): must take `object_count > 1` as its base case (D5). Sequence: this Gate 1 first, then S1711 Gate 1 amends its §2 target accordingly; the two builds may proceed in parallel after that.
- `build:bq-data-verification-s1590` (completed) and `build:bq-data-verification-platform-key-distribution-s1717` (Gate 4 pending): D6 uses the shipped manifest; only the AIM Data connector's object enumeration changes.
- `specs/SELLER-ROUTE-INTEROP-S1711.md:12` `object_count == 1` for the local route becomes `object_count == number of data members`; the S3 route is unchanged.
- Seller Workspace (AWS) listings already publish a prefix; D3/D5 bring the local route to parity with it, which is the smallest safe path: reuse the N-object contract that exists rather than invent a bundle format.

## 6. Chunks (for Gate 2 to pin)

- **A — AIM Data model and upload:** members table, roles, streamed idempotent registration, per-member status/reason, directory card + member table UI, caps. Migration on the AIM Data local database.
- **B — AIM Data processing:** per-directory bounded profiling/PII/allAI, documentation as context, member failure states.
- **C — Publish and sample:** N-object `VersionPublish` from the local route, disclosure snapshot with sample members, listing aggregate summary; backend acceptance of `object_count > 1` on the local route and interop record update.
- **D — Delivery:** Trust Channel multi-member transfer manifest; order page file list; hand-off to S1711 for the buyer door.
- **E — Verification over the set:** AIM Data connector enumerates data members as `objects[]`, role exclusion in `coverage.skipped[]`.
- **F — Copy and runbooks:** D7 wording; `aim-data-seller-publish-journey.md` and `data-verification-seller-journey.md` updated; INSTALL/README.
Dependency: A → B → C → (D ∥ E) → F. Each chunk: MP builds, GLM + DeepSeek Gate 3, CC waived; nothing ships to the stable image before C and D are both approved (a listing with N objects must be deliverable).

## 7. Acceptance criteria

- **AC1.** Uploading a directory with ≥ 10,000 files in AIM Data yields one dataset, one status, a member table, and completes profiling within the policy bound; no per-file allAI call.
- **AC2.** Roles default by convention and are editable; unsupported members are `other` with a visible reason; no card ever stays in Processing without a member-level reason.
- **AC3.** Publishing produces one listing with `object_count = data members`, a manifest hash the receiver verifies, and the sample members listed in the disclosure snapshot; the public listing shows N files and the aggregate summary.
- **AC4.** A purchase delivers every data member with per-member hash verification; a one-member dataset delivers exactly as today.
- **AC5.** A paid verification over the directory produces one report whose coverage lists N objects and the excluded roles; the S1590 privacy tests still pass unchanged.
- **AC6.** Listing, sample and delivery all complete for a seller who never opens the verification panel; the panel is labelled optional; the runbook says so.
- **AC7.** Existing single-file datasets/listings (Sergey's June listing, Max's listing 936a08d6) are unaffected before and after upgrade (regression on a copy of a real install volume).
- **AC-final (Gate 4):** Sergey lists the Acid Trap Dataset as one product from his own install on the stable image, with his chosen sample, and a buyer test account receives the whole set; evidence recorded without customer data.

## 8. Risks

- Large-set delivery over the Trust Channel is the long pole; D5 keeps the per-member stream and defers the buyer-door shape to S1711, which is the item already designed for that door.
- Aggregate listing summaries could mislead if members have different schemas; the summary must name the number of schemas found and show the per-member schema in the member table.
- Role defaults will sometimes be wrong; the seller edits before publish and the disclosure snapshot is the record.
- The 21,000-file case makes the profiling sample policy visible to sellers; it must be stated on the dataset page ("profiled on N of M files").
