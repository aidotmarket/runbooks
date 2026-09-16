# BQ-DATA-VERIFICATION-S1590 directory-root amendment

**Status:** Specification candidate only, reviewed with `BQ-MULTI-FILE-DATASETS-S1717-GATE1.md` (same PR, same panel: GLM + DeepSeek; CC waived by Max). It authorizes no code change until that Gate 1 is approved and its chunk E reaches Gate 2.

**Build Queue entities:** `build:bq-data-verification-s1590` (parent, completed), `build:bq-multi-file-datasets-s1717` (the build that implements this amendment in its chunk E).

**Authority:** Max product ruling 2026-09-16, Event Ledger `a790fb22-e575-4455-97f6-95170385d085` ("a product is a directory, not a file"); Max 2026-09-16: the verified label is voluntary.

**Parent authorities:** [Gate 1](BQ-DATA-VERIFICATION-S1590-GATE1.md), [Gate 2](BQ-DATA-VERIFICATION-S1590-GATE2.md), the [S1646 pay-in amendment](BQ-DATA-VERIFICATION-S1590-PAYIN-ONBOARDING-AMENDMENT.md), the [GA amendment](BQ-DATA-VERIFICATION-S1590-GENERAL-AVAILABILITY-AMENDMENT.md) and the [S1717 platform-key Gate 1](BQ-DATA-VERIFICATION-PLATFORM-KEY-DISTRIBUTION-S1717-GATE1.md).

**Source trace:** `aim-data@b5629a50d5cebfb693fdfc07e93a7124a75cb88b`, `ai-market-backend@8ed234af49b3ba7d8fa84e363c5fe8263f40a23a`. Citations are to those exact checkouts.

## 1. What changes and what does not

The parent Gate 1 resolves the registered source handle "to the exact artifact" (§3 Stage A, `:40`), traverses "every reachable supported object in the registered root" (`:203`), and its A1 test pins "the exact resolved local path or S3 connection/bucket/object key plus content hash before reading" (`:315`). The pinned resolver is single-artifact: `ResolvedArtifact` holds one `local_path` or one `S3ObjectMetadata` and `resolved_object_count()` is 1 for either (`aim-data:app/services/source_artifact_resolver.py:34-51`); the locator commitment is an HMAC over that one path or key (`:53-65`); the scanner reads one payload into one connector stream (`aim-data:app/services/data_verification/scanner.py:173-184`).

This amendment adds one artifact kind, **`local_directory`**, for directory datasets published under S1717 D0/D3. It changes nothing else: the customer-to-cloud manifest fields, the closed skip-reason enum (`permission_denied`, `unsupported_type`, `timeout`; `ai-market-backend:app/schemas/data_verification.py:466-487`), the coverage-total validators, the prohibition on seller-selected exclusions (`:203`) and on deleting skips (`:205`), the quote, payment, capture, publication and corpus-capture contracts, the privacy boundary (no raw member names, paths, error text or records in cloud-visible fields), and the single-file and S3 kinds are all unchanged.

## 2. The directory root

1. **Registered root.** For a listing whose active version was published from a directory dataset, the registered root is the **version-pinned data-member set**: the members with `role = data` in the published `DatasetManifest` (S1717 D0), in manifest index order. Members with other roles are not in the root; they are neither traversed nor reported as skipped. The root is frozen by the published version, not by live roles: a role edit after publish does not change the root of any existing version.
2. **Resolution.** `ResolvedArtifact` gains `kind = "local_directory"` with `root_path` (canonical realpath of the dataset's directory root), `manifest_hash`, and `members[]` (index, canonical relative path, size, SHA-256) taken from the pinned manifest; `resolved_object_count()` returns `data_member_count`. Resolution refuses (`ArtifactResolutionError`) when the listing's active version has no local-route manifest.
3. **Exact binding before reading.** Before any member is read, the conduit verifies every root member in manifest order: the realpath of `root_path/relative_path` stays inside `root_path` (no symlink escape), and its size and SHA-256 equal the manifest. Any mismatch, missing member or extra dependence outside the root is a **stale-manifest failure**: the scan terminates `FAILED_VOIDED` (parent `:219`, hold voided, nothing publishes) with no partial report. A member is never silently skipped for a manifest mismatch; the skip enum is reserved for the parent's three runtime reasons, which still apply per member during traversal (for example a member that becomes unreadable mid-scan is `permission_denied`).
4. **Locator commitment and content hash.** The receipt's `artifact_locator_commitment` is the HMAC (same key as the parent) over the canonical `root_path` plus `manifest_hash`; the receipt's content hash is `manifest_hash`. `objects[].object_id` is the customer-held-keyed HMAC over the member's canonical relative path plus SHA-256, so member comparison across runs is stable while no path reaches ai.market.
5. **Traversal and facts.** The conduit traverses members in manifest order, one connector stream per member, and reports each as one `objects[]` entry; `coverage.objects_discovered = data_member_count`; aggregate facts are computed over all scanned members exactly as the S3-prefix case would compute them over its objects. The quote probe reports `objects_discovered = data_member_count` and `size_class` from `total_data_bytes`.
6. **Fulfilment parity.** Fulfilment and verification resolve the same version-pinned root and manifest (parent A1 `:315`, amended below), so a buyer's delivered set and the scanned set are the same members with the same hashes.

## 3. Acceptance additions (to the parent's A1 list)

- A1 §6 is amended to read: "…pins the exact resolved local path, S3 connection/bucket/object key, **or canonical directory root plus `manifest_hash`**, plus content hash before reading."
- A directory fixture with data, documentation and `other` members produces an accepted report with `objects_discovered` equal to the data-member count, skip reasons only from the parent enum, and coverage totals consistent; documentation and `other` members appear nowhere in the report.
- Changing a member's bytes, removing a member, or replacing a member with a symlink outside the root after publish causes `FAILED_VOIDED` before any read and no charge.
- A role edit after publish does not change `objects_discovered` for the published version.
- No cloud-visible receipt or report field contains a member path or name (existing privacy tests extended with the directory fixture).
- Single-file and S3 fixtures pass unchanged.

## 4. Sequencing

Implemented by S1717 chunk E only after S1717 chunks A–C are approved (the manifest must exist). This amendment is reviewed by the same panel as the S1717 Gate 1 and stands or falls with it; it is not a licence to touch the parent's shipped code before then.
