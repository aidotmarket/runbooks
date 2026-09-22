# BQ-PREVIEW-CONTRACT-CROSS-REPO-GATE-S1732 — Gate 2 implementation specification

Status: **GATE 2 implementation specification.** Gate 1 is approved (Council 3/3 R3). This document authorizes only the two implementation chunks below and the companion runbook update. It does not authorize deployment, GitHub/Infisical mutation, customer-data access, feature enablement, or a wire-format change. Gate 3 requires unanimous GLM, DeepSeek, and Gemini review.

Authority and source identities read on 2026-09-22:

- Design authority: `aidotmarket/runbooks@a736593abd4e22affff45af8dadf1f50f4c2de68:specs/BQ-PREVIEW-CONTRACT-CROSS-REPO-GATE-S1732-GATE1.md`.
- AIM Data source: `aidotmarket/aim-data@6529e1ed4d5983a87a9b1e2faadda32e18d4cf76`.
- Backend source: `aidotmarket/ai-market-backend@d5d2e3915fb5067e04b03dfe97716da380002b6b`.

These are immutable identities, not aliases for `origin/main`. The backend tip includes later documentation changes; all code citations below were reread at `d5d2e3915fb5067e04b03dfe97716da380002b6b`.

## 1. Frozen outcome and Gate 2 decisions

There is one authoritative, backend-owned byte corpus. Each repository pins the other by a 40-character lowercase commit SHA, loads its own real Pydantic models and signing code in its own process, and proves the same accept/reject result and exact bytes. Schema coverage supplements that byte gate; it never replaces it.

The following implementation details were left open by Gate 1 and are fixed here:

1. The shared command surface is `scripts/preview_contract_gate.py`; the repository-specific process is `tests/preview_contract_runner.py`. JSON result files are the only interchange between processes.
2. `commitment-model` is the model-isolated operation required for the named commitment model. The complete operation vocabulary is fixed in §3.2; no implementation may add an operation without updating this specification.
3. `request-bytes` invokes `construct_request` when its manifest `models` contains `aim_data.construct_request`, so the producer-to-backend adapter needs no ninth wire operation.
4. A field is “optional” for coverage only when Pydantic reports `field.is_required() is False`. A required field whose annotation admits `None` must be present, and `null` counts as present.
5. Both deploy-key private values are separate Infisical entries in the existing `ai-market-backend` project, `prod` environment, below `/github-actions/preview-contract/`; no new Infisical project is created. They are not application runtime variables and are not added to Railway.
6. The runbook edit is a companion documentation closeout in `aidotmarket/runbooks`, not a third implementation chunk. It lands after both code mains are green, without changing their merge order.

## 2. Chunks and exact files

The merge order is immutable: **AIM Data first, backend second**. The backend PR remains open and red until AIM Data has merged and the backend reverse pin names that merged AIM commit. Both repositories must pass all pre-existing required checks as well as the new gate.

### 2.1 Chunk A — `aidotmarket/aim-data` (merge first)

Base: `6529e1ed4d5983a87a9b1e2faadda32e18d4cf76`. It is compatible with both the old backend main and backend anchor `A`.

Create:

- `.github/workflows/preview-contract-cross-repo.yml` — exact workflow in §5.1.
- `preview-contract-backend.lock.json` — exact schema in §3.1.
- `scripts/preview_contract_gate.py` — `lock`, `verify-manifest`, `coverage`, `compare`, `aim-transition`, and `deleted-consumers` subcommands. The last takes no arguments, prints each checked deleted name and its zero executable-reference count, and exits nonzero on any hit as defined in §7.
- `tests/preview_contract_runner.py` — AIM dispatch for every operation in §3.2.
- `tests/test_preview_contract_cross_repo.py` — lock, manifest, runner, coverage, comparison, transition, and mutation-unit tests.

Modify:

- `app/models/preview_disclosure_schemas.py`: `DisclosureBinding.binding_rules` ports recursive `public_types`; `PreviewDisclosureRequest` compares all nine package members and each proof's `sampled_leaf_list_digest` (`aim-data@6529e1ed…:25-139,142-253`; backend reference `d5d2e391…:128-138,202-232`). Add the package pre-validation described in §3.3 before nested commitment validation.
- `app/services/preview_lifecycle.py`: `withdrawal_candidate`, `refresh_candidate`, and `supersession_candidate` preserve `aggregate_hash_profile` exactly, including `None` (`aim-data@6529e1ed…:124-176`).
- `tests/test_preview_disclosure_schemas.py`: extend the closed-request and invalid-binding coverage with direct positive/negative tests for recursive public types, nine-member package identity, per-proof sampled-leaf mismatch, and exact `literal_error` (`aim-data@6529e1ed…:8-82`).
- `tests/test_preview_lifecycle.py`: parameterize withdraw, refresh, and supersession over omitted legacy, explicit v1, and explicit v2 (`aim-data@6529e1ed…:62-93`).
- `tests/test_preview_signing_service.py`: replace the AIM-owned request/signing/differential golden consumers with the fetched corpus and rewrite `test_pinned_differential_corpus_python_and_node` (`aim-data@6529e1ed…:127-175,562-618`).
- `tests/preview_differential_check.cjs`: accept the backend corpus directory as its sole argument and read `manifest.json`, `inputs/`, and `bytes/`; retain its independent byte/digest/signature implementation (`aim-data@6529e1ed…:tests/preview_differential_check.cjs:2-46`).
- `scripts/build_preview_producer_evidence.py`: replace `fixture_manifest_sha256` with `contract_manifest_sha256`, sourced from the already verified fetched backend `manifest.sha256` (`aim-data@6529e1ed…:499-501`).
- `tests/run_preview_producer_synthetic.py`: require and propagate the verified corpus path/digest to the evidence builder (`aim-data@6529e1ed…:25-38`).
- `tests/test_preview_producer_evidence.py`: extend the manifest assertions to require `contract_manifest_sha256` and absence of the old field (`aim-data@6529e1ed…:112-142`).

Delete, in the same commit:

- `.github/workflows/preview-contract-parity.yml`
- `scripts/check_preview_fixture_parity.py`
- `tests/test_preview_fixture_parity.py`
- `tests/fixtures/preview-fixture-manifest.json`
- `tests/preview_differential_corpus.py`
- `tests/fixtures/aim_preview_differential_v1.json`
- `tests/fixtures/aim_preview_differential_v1.sha256`
- `tests/fixtures/aim_preview_requests_v1.json`
- `tests/fixtures/aim_preview_signing_v1.json`
- `tests/fixtures/aim_preview_signing_requests_v1.sha256`

Do not modify the broader `aim_dataset_*`, policy, package, or manifest-budget fixtures.

### 2.2 Chunk B — `aidotmarket/ai-market-backend` (merge second)

Base: `d5d2e3915fb5067e04b03dfe97716da380002b6b`. Commit the contract changes and corpus as immutable anchor `A`; after Chunk A merges as `B`, add exactly one follow-up commit changing only `preview-contract-aim-data.lock.json` and, if needed, workflow evidence metadata. Merge by merge commit with `A` retained in ancestry.

Create:

- `.github/workflows/preview-contract-cross-repo.yml` — exact workflow in §5.2.
- `preview-contract-aim-data.lock.json` — exact schema in §3.1.
- `scripts/preview_contract_gate.py` — the same command contract as Chunk A plus `backend-transition` and `anchor-diff`.
- `scripts/build_preview_contract_corpus.py` — developer-only proposal writer; it writes a caller-supplied temporary directory and has no in-place/default/update mode.
- `tests/preview_contract_runner.py` — backend dispatch for every operation in §3.2.
- `tests/test_preview_contract_cross_repo.py` — lock, manifest, runner, coverage, comparison, transition, anchor-diff, and mutation-unit tests.
- `tests/fixtures/preview/cross_repo_contract/v1/manifest.json`
- `tests/fixtures/preview/cross_repo_contract/v1/manifest.sha256`
- One `tests/fixtures/preview/cross_repo_contract/v1/inputs/<id>.json` for every ID in §3.3.
- One `tests/fixtures/preview/cross_repo_contract/v1/bytes/<id>.bin` for every accepting ID in §3.3; rejecting IDs have no byte file.

Modify:

- `app/services/listing_preview_disclosure.py`: `allocate_candidate` and `_decide_preview` use `.get("aggregate_hash_profile")`, not a v1 default, when inheriting a historical binding; semantic comparisons may still treat absence as v1 (`backend@d5d2e391…:113-145,179-219`).
- `app/schemas/listing_preview.py`: add the same `PreviewDisclosureRequest` package pre-validation as AIM Data (§3.3), ahead of nested commitment validation; keep the later v2 transport check and all existing validators.
- `tests/test_listing_preview_database.py`: extend historical-v1, no-sample, and withdrawal coverage for legacy/v1/v2 allocation persistence, wire omission, and anchor behavior (`backend@d5d2e391…:379-418,560-676`).
- `tests/test_listing_preview_contracts.py`: point cross-repository byte assertions at the new corpus and add exact error-type/error-code assertions (`backend@d5d2e391…:249-316,369-374`).

No other backend model, serializer, API, database, or public projection changes are permitted. In particular, `ListingPreviewManifest`, `PreviewColumn`, `PreviewLimits`, and `PreviewApproval` remain out of scope (`backend@d5d2e391…:347-421`).

## 3. Corpus, locks, and runners

### 3.1 Exact JSON formats

All JSON files are UTF-8, end in one LF, use sorted keys, and use separators `(',', ':')`. Readers reject duplicate keys, unknown keys, non-canonical encoding, and symlinks anywhere below the corpus root.

`preview-contract-backend.lock.json` has exactly:

```json
{"backend_sha":"<40 lowercase hex>","manifest_sha256":"<64 lowercase hex>"}
```

`preview-contract-aim-data.lock.json` has exactly:

```json
{"aim_data_sha":"<40 lowercase hex>","contract_anchor_sha":"<40 lowercase hex>","manifest_sha256":"<64 lowercase hex>"}
```

No ref-like string (`HEAD`, branch, tag, slash, caret, tilde, colon), extra field, missing field, uppercase hex, or all-zero SHA is accepted. `manifest_sha256` is the SHA-256 of the exact `manifest.json` bytes. `manifest.sha256` is exactly `<digest>  manifest.json\n`.

`manifest.json` has exactly:

```json
{"schema_version":1,"vectors":[{"byte_length":123,"bytes_path":"bytes/<id>.bin","id":"<id>","input_path":"inputs/<id>.json","models":["<model-or-adapter>"],"operation":"<operation>","sha256":"<64 lowercase hex>","expected":"accept"},{"expected":"reject","expected_error_code":"<semantic code>","expected_error_type":"value_error","id":"<id>","input_path":"inputs/<id>.json","models":["<model-or-adapter>"],"operation":"<operation>"}]}
```

Rows are sorted by `id`; `models` is a nonempty sorted unique array. Accept rows contain exactly `id`, `operation`, `input_path`, `expected`, `models`, `bytes_path`, `byte_length`, and `sha256`. Reject rows contain exactly `id`, `operation`, `input_path`, `expected`, `models`, `expected_error_type`, plus `expected_error_code` only for a custom validator. `input_path` and `bytes_path` are normalized relative POSIX paths fixed to the directories above; absolute paths and `..` fail.

The only `models` tokens are the exact strings in this dispatch table. A manifest row uses the token(s) named by its §3.3 abbreviation, sorted lexically; unknown tokens, missing required tokens, extra tokens, and operation/token mismatches fail before dispatch. Imports come only from the runner's own repository root.

| Operation / abbreviation | Manifest token | AIM Data import and callable | Backend import and callable |
|---|---|---|---|
| `binding-model`, `disclosure-preimage` / B | `shared.DisclosureBinding` | `app.models.preview_disclosure_schemas.DisclosureBinding`; `app.services.preview_signing_service.disclosure_bytes` for preimage | `app.schemas.listing_preview.DisclosureBinding`; `app.utils.preview_signing.disclosure_bytes` for preimage |
| `proof-model` / P | `shared.PreviewProof` | `app.models.dataset_commitment_schemas.DatasetPreviewProofContract` | `app.schemas.dataset_commitment.PreviewSignedProofContract` |
| `commitment-model` / C | `shared.PreviewCommitment` | `app.models.dataset_commitment_schemas.DatasetCommitmentContract` | `app.schemas.dataset_commitment.PreviewSignedCommitmentContract` |
| `request-model`, `request-bytes` / R | `shared.PreviewDisclosureRequest` | `app.models.preview_disclosure_schemas.PreviewDisclosureRequest` and `app.services.preview_signing_service.request_bytes` | `app.schemas.listing_preview.PreviewDisclosureRequest` and `app.utils.dataset_commitment.canonical_json_bytes` of `model_dump(mode="json")` |
| `request-model`, `request-bytes` / lifecycle R | `shared.WithdrawalRequest`, `shared.RefreshRequest`, or `shared.SupersessionRequest` according to the ID prefix | Same class name in `app.models.preview_disclosure_schemas`; `request_bytes` for bytes | Same class name in `app.schemas.listing_preview`; canonical request model bytes |
| `platform-envelope-model`, `platform-envelope-preimage` / E | `shared.PlatformEnvelope` | `app.models.preview_disclosure_schemas.PlatformEnvelope`; `app.services.preview_signing_service.platform_envelope_bytes` for preimage | `app.schemas.listing_preview.PlatformEnvelope`; `app.utils.preview_signing.platform_envelope_bytes` for preimage |
| `local-candidate` / LC | `shared.LocalCandidate` | `app.services.preview_signing_service.LocalCandidate.validate` | `app.schemas.listing_preview.DisclosureBinding` plus canonical binding bytes |
| `request-bytes` / CR (alongside R) | `aim_data.construct_request` | `app.services.preview_signing_service.construct_request` | The deterministic request projection described below, then `PreviewDisclosureRequest` |

For `local-candidate`, B is represented by `shared.LocalCandidate` alone; for `request-approve-v2`, R and CR are both represented. The direct `request-model` rejection vectors use `shared.PreviewDisclosureRequest`; lifecycle byte vectors use the matching lifecycle token alone. `request-none` uses the base request token. Validate the exact operation/token relation, not just membership in this table.

`request-approve-v2` has one canonical JSON input envelope with exactly `candidate`, `commitment`, `proofs`, and `approved_p1`. `candidate` is the complete `DisclosureBinding` object for `LocalCandidate.validate`; `commitment` is the complete signed commitment object; `proofs` is the ordered complete proof-object array equal to `commitment.proofs`; `approved_p1` is an object with exactly `summary_id`, `summary_approval_id`, `summary_hash`, `render_hash`, `aggregate_hash`, `content_revision`, `source_revision`, `listing_id`, and `listing_version_id`, each copied byte-for-byte as a JSON value from `candidate`. No `signer`, private key, signature override, path, or extra envelope member is accepted. The signer is runner-local: derive an Ed25519 private key from `SHA-256(b"preview-contract-cross-repo-v1 synthetic signing seed")`, construct a test-only signer exposing `_keys()` and `sign_disclosure(binding)` with the real `disclosure_bytes`, and require the candidate/commitment/proofs' signer references and signatures to match that key. Both runners derive the same key in memory; no key material enters the corpus, log, or artifact. AIM calls `LocalCandidate.validate(candidate)` then the real `construct_request(..., signer=signer, approved_p1=approved_p1)`. Backend derives the identical seller signature over `disclosure_bytes(candidate)`, builds the six request fields from the envelope, validates `PreviewDisclosureRequest`, and serializes its canonical model bytes. A mismatched approved P1 projection or malformed envelope fails; production identities and keys are forbidden.

### 3.2 Operations and output contract

The complete operation vocabulary is:

- `binding-model`: validate `DisclosureBinding`; output canonical JSON bytes of `model_dump(mode="json")`.
- `proof-model`: validate `DatasetPreviewProofContract` / `PreviewSignedProofContract`; output canonical model bytes.
- `commitment-model`: validate `DatasetCommitmentContract` / `PreviewSignedCommitmentContract`; output canonical model bytes.
- `disclosure-preimage`: call the real `disclosure_bytes`; output its domain-prefixed bytes (`aim-data@6529e1ed…:121-126`; backend `d5d2e391…:101-106`).
- `request-model`: validate the concrete request class named by the exact token table above; output canonical model bytes.
- `request-bytes`: validate the request and call the real request serializer. When `models` names `aim_data.construct_request`, construct through `LocalCandidate` and `construct_request` first (`aim-data@6529e1ed…:295-375`).
- `platform-envelope-model`: validate `PlatformEnvelope`; output canonical model bytes.
- `platform-envelope-preimage`: call the real `platform_envelope_bytes`; output its domain-prefixed bytes (`aim-data@6529e1ed…:129-138`; backend `d5d2e391…:109-118`).
- `local-candidate`: AIM validates through `LocalCandidate.validate` and rereads `binding_bytes`; backend validates `DisclosureBinding` and emits the same binding bytes.

Each runner first resolves and changes to `--repo-root`, prepends only that root to `sys.path`, and rejects an imported `app` module whose resolved path is outside that root. This prevents the caller checkout from satisfying the peer runner's imports. It then emits canonical result JSON with `repo_sha`, `manifest_sha256`, and sorted `results`. An accept result has `id`, `status:"accept"`, `byte_length`, `sha256`, and base64url `bytes`; a reject result has `id`, `status:"reject"`, ordered Pydantic `errors` containing exact `loc`, `type`, and normalized custom `code`. Normalize a custom code only from the exact validator token in `ctx.error`/`msg`, never by substring search. Unexpected exceptions fail the runner. Neither runner writes the corpus. Lock and manifest validation before dependency installation use only the Python standard library.

### 3.3 Complete initial vector inventory

Model abbreviations below expand exactly as follows: `B` = both repositories' `DisclosureBinding`; `P` = both proof contracts; `C` = both commitment contracts; `R` = both `PreviewDisclosureRequest` families; `E` = both `PlatformEnvelope`; `LC` = AIM `LocalCandidate` plus backend `DisclosureBinding`; `CR` = AIM `construct_request` plus backend `PreviewDisclosureRequest`. Every accepting row names the expanded models in `manifest.json`, not these abbreviations.

Accept vectors:

| ID | Operation | Models | Purpose |
|---|---|---|---|
| `binding-legacy-approve-owner` | `binding-model` | B | omitted profile; owner |
| `binding-v1-approve-licensed` | `binding-model` | B | v1; licensed |
| `binding-v2-approve-public-domain` | `binding-model` | B | v2; public_domain |
| `binding-v2-approve-other-authorized` | `binding-model` | B | other_authorized |
| `binding-v2-none` | `binding-model` | B | approve/no-sample |
| `binding-legacy-withdraw` | `binding-model` | B | withdrawal, omitted profile |
| `binding-v1-withdraw` | `binding-model` | B | withdrawal, v1 |
| `binding-v2-withdraw` | `binding-model` | B | withdrawal, v2 |
| `proof-v1-policy-v1` | `proof-model` | P | package v1, policy v1; `signature_algorithm` omitted; sibling `direction=left` |
| `proof-v2-policy-v2` | `proof-model` | P | package v2, policy v2; `signature_algorithm` present; sibling `direction=right` |
| `commitment-v1-previous-absent` | `commitment-model` | C | v1 proof; optional previous ID absent |
| `commitment-v2-previous-present` | `commitment-model` | C | v2 proof; previous ID present |
| `commitment-no-proofs` | `commitment-model` | C | valid standalone commitment with `proofs` omitted; default empty list |
| `preimage-binding-legacy` | `disclosure-preimage` | B | legacy bytes |
| `preimage-binding-v1` | `disclosure-preimage` | B | v1 bytes |
| `preimage-binding-v2` | `disclosure-preimage` | B | v2 bytes |
| `request-approve-v2` | `request-bytes` | R, CR | complete approval and constructed producer request |
| `request-none` | `request-bytes` | R | complete no-sample request |
| `request-withdraw-legacy` | `request-bytes` | R | legacy inheritance |
| `request-withdraw-v1` | `request-bytes` | R | v1 inheritance |
| `request-withdraw-v2` | `request-bytes` | R | v2 inheritance |
| `request-refresh-legacy` | `request-bytes` | R | legacy inheritance |
| `request-refresh-v1` | `request-bytes` | R | v1 inheritance |
| `request-refresh-v2` | `request-bytes` | R | v2 inheritance |
| `request-supersede-legacy` | `request-bytes` | R | legacy inheritance |
| `request-supersede-v1` | `request-bytes` | R | v1 inheritance |
| `request-supersede-v2` | `request-bytes` | R | v2 inheritance |
| `envelope-model-legacy-open` | `platform-envelope-model` | E | legacy binding; `valid_until` omitted |
| `envelope-model-v1-all-statuses` | `platform-envelope-model` | E | active, rotated, revoked signer keys |
| `envelope-model-v2-bounded` | `platform-envelope-model` | E | v2 binding; `valid_until` present |
| `envelope-preimage-legacy` | `platform-envelope-preimage` | E | legacy signed bytes |
| `envelope-preimage-v1` | `platform-envelope-preimage` | E | v1 signed bytes |
| `envelope-preimage-v2` | `platform-envelope-preimage` | E | v2 signed bytes |
| `local-candidate-legacy` | `local-candidate` | LC | stored/re-read legacy binding bytes |
| `local-candidate-v1` | `local-candidate` | LC | stored/re-read v1 bytes |
| `local-candidate-v2` | `local-candidate` | LC | stored/re-read v2 bytes |

Reject vectors:

| IDs | Operation / models | Exact expectation |
|---|---|---|
| `extra-request`, `extra-binding`, `extra-commitment`, `extra-proof`, `extra-envelope` | matching model operation / R, B, C, P, E | `extra_forbidden` |
| `extra-envelope-binding` | `platform-envelope-model` / E | nested binding `extra_forbidden` |
| `local-candidate-extra` | `local-candidate` / LC | `extra_forbidden` before storage |
| `literal-request-profile` | `request-model` / R | `literal_error` |
| `literal-binding-profile`, `literal-binding-decision`, `literal-binding-preview-type`, `literal-binding-content-type`, `literal-binding-sample-decision`, `literal-binding-aggregate-profile`, `literal-binding-rights-code`, `literal-binding-signature-algorithm`, `literal-binding-signature-profile` | `binding-model` / B | `literal_error` |
| `literal-proof-media-type`, `literal-proof-package-profile`, `literal-proof-scan-policy`, `literal-proof-scan-verdict`, `literal-proof-signature-algorithm` | `proof-model` / P | `literal_error` |
| `literal-proof-sibling-direction` | `proof-model` / P | nested `ProofSibling.direction` `literal_error` |
| `literal-commitment-canonicalization`, `literal-commitment-hash`, `literal-commitment-signature-algorithm` | `commitment-model` / C | `literal_error` |
| `literal-envelope-profile`, `literal-envelope-signature-algorithm`, `literal-signer-key-algorithm`, `literal-signer-key-status` | `platform-envelope-model` / E | `literal_error` |
| `request-proof-v1-unsupported` | `request-model` / R | `value_error`, code `unsupported_proof` |
| `package-mismatch-url`, `package-mismatch-media-type`, `package-mismatch-profile`, `package-mismatch-byte-ceiling`, `package-mismatch-scan-policy`, `package-mismatch-scan-policy-version`, `package-mismatch-scanned-at`, `package-mismatch-scan-verdict`, `package-mismatch-signer-reference` | `request-model` / R | `value_error`, code `package_mismatch` |
| `proof-sampled-leaf-list-mismatch` | `request-model` / R | `value_error`, code `sampled_leaf_list_mismatch` |
| `schema-binary-top`, `schema-binary-array`, `schema-binary-object`, `schema-binary-object-array` | `binding-model` / B | `value_error`, code `binary_sample_forbidden` |

The ordinary nested public-type shape is exercised by all four approved bindings. Inputs use fixed synthetic UUIDs, timestamps, digests, keys, and signatures only. No customer value, raw row, credential, local path, or customer identifier is allowed.

The initial inventory above is exact, including `commitment-no-proofs`; adding an accept row to repair a coverage hole requires a reviewed specification revision. The following field-presence matrix fixes the non-required fields from the pinned models. Every row has an accepted present and absent case; all other named-model fields are required and appear in their corresponding direct accept vector. Nested instances count only when their parent vector accepts. For nested `ProofSibling.direction`, the two proof-model vectors provide the two allowed values and the rejection above exercises an unknown value. For proof package/profile/scan-policy values, the two proof-model vectors provide v1 and v2; all other enumerated literal/enum values are assigned by the purposes in the inventory (four rights codes, two binding decisions/sample decisions, and three signer-key statuses).

| Model and `field.is_required() is False` path | Present accepted vector | Absent accepted vector |
|---|---|---|
| `DisclosureBinding.aggregate_hash_profile` | `binding-v1-approve-licensed` | `binding-legacy-approve-owner` |
| Proof contract `signature_algorithm` | `proof-v2-policy-v2` | `proof-v1-policy-v1` |
| Commitment contract `previous_commitment_id` | `commitment-v2-previous-present` | `commitment-v1-previous-absent` |
| Commitment contract `canonicalization_profile`, `hash_algorithm`, `signature_algorithm` | `commitment-v2-previous-present` | `commitment-v1-previous-absent` |
| Commitment contract `proofs` | `commitment-v1-previous-absent` | `commitment-no-proofs` |
| `SignerKeyEvidence.valid_until` | `envelope-model-v2-bounded` | `envelope-model-legacy-open` |

Set the absent commitment default fields in `commitment-v1-previous-absent` all absent together, and the present fields in `commitment-v2-previous-present` all present together. A required nullable field remains explicitly present, including `null`. The matrix is verified against the live pinned classes, not substituted for the model-derived coverage walk; a newly added default field without both cases fails coverage.

The two `package-mismatch-profile` and `package-mismatch-signer-reference` rows must remain `request-model` / R with exact `package_mismatch`. Use at least two proofs, copy the same ordered proofs into `commitment.proofs`, and vary exactly the named member between them. Both repos add a `PreviewDisclosureRequest` `mode="before"` validator that, only when the raw request is a mapping with at least two proof mappings and every proof has all nine package keys, compares the raw nine-member package tuples and raises `ValueError("package_mismatch")` when they differ. The raw comparison is necessary also for the single-literal media type: nested proof or commitment validation would otherwise reject before package identity is checked. This runs before nested commitment `mixed_profiles` and before the existing v2 `unsupported_proof` transport check. Missing package keys and a single invalid proof continue through existing nested validation; isolated `literal-*` proof vectors still report `literal_error`. Keep the later transport check for a uniform v1 request; `request-proof-v1-unsupported` still reports `unsupported_proof`. Assert exactly one Pydantic `value_error` with code `package_mismatch` for each of the nine mismatch inputs in both repositories, with no earlier `unsupported_proof`, `mixed_profiles`, or `literal_error`.

### 3.4 Manifest and schema-coverage algorithms

`verify-manifest` performs, in order: safe-root/symlink checks; canonical JSON checks; schema/key checks; sorted/unique ID and model checks; exact operation check; exact file-set equality; rejection-has-no-bytes check; input SHA read safety; accept byte length/SHA check; exact `manifest.sha256` check; exact lock digest check. Any failure exits nonzero before a model is imported.

Each runner records coverage independently from its own imported models:

1. Register exactly `DisclosureBinding`, the proof contract, the commitment contract, `PreviewDisclosureRequest`, and `PlatformEnvelope`. Proof/commitment sources are AIM `app/models/dataset_commitment_schemas.py:212-279` and backend `app/schemas/dataset_commitment.py:331-394`; binding/request/envelope sources are in §2. Include recursively nested `ProofSibling` and `SignerKeyEvidence`.
2. Resolve `model_fields` and annotations with `typing.get_origin/get_args`; unwrap `Annotated`, unions, and containers; enumerate every `Literal` and every Enum member. Never use JSON schema or a handwritten field list.
3. For every accept vector/model pair, retain the parsed input before validation. Dispatch the operation, including nested instances. Attribute a nested field to the nested model class and its concrete input path, not to the parent and not by text search.
4. Count a field present when its key exists in that model's input object, even when the value is `null`; count absent when the key does not exist. Count literal/enum coverage only after that model accepts the vector.
5. Evaluate a model only in operations and parent contexts where that model itself accepts. A rejected full request does not count toward proof coverage; `proof-v1-policy-v1` does.
6. Fail for any field with no accepted present case; any `field.is_required() is False` field with no accepted absent case; or any allowed Literal/Enum value with no accepted value case. Report model, field path, and missing condition. Also require the proof contract's v1 and v2 `package_profile` and `scan_policy` values in accepted **direct `proof-model`** vectors; nested commitment/request instances do not discharge this direct-model requirement. This makes deletion of `proof-v1-policy-v1` observable even though a v1 proof remains nested in a commitment.
7. Run coverage in both repositories before comparing bytes. Removing `proof-v1-policy-v1` must fail both jobs at coverage with model, field path, and missing v1 value, after all integrity and transition checks pass as described in §9.

`compare` requires identical IDs/statuses, exact expected error type, exact custom code where declared, expected byte equality, cross-runner byte equality, and matching byte length/SHA. Changing `sampled_leaf_list_mismatch` to another `value_error` code therefore fails.

## 4. Lock transitions and immutable anchor

For either transition command, a `pull_request` event uses `git merge-base HEAD origin/<base-ref>` after fetching the base ref; a `push` to `main` uses the event's `before` SHA as the diff base (verify it is reachable with the full checkout), including a merge commit. The all-zero `before` SHA is allowed only for initial repository creation and uses the empty tree. Reject other event types, unavailable bases, and shallow histories. Classify the lock diff from that base through the tested `HEAD`; unchanged locks are accepted. Unit tests cover both event kinds and initial installation.

`aim-transition` accepts only: initial installation when the file is absent at the diff base; no SHA change; or a new `backend_sha` equal to the fetched backend `HEAD` with a new `manifest_sha256` equal to its verified corpus digest. The anchor declaration is the AIM lock's `backend_sha` together with the fetched backend commit's own corpus transition: require that commit's first-parent corpus `manifest.sha256` is absent (initial installation) or differs, and that its manifest/file-set checks pass. Thus an unchanged-manifest, non-anchor SHA bump cannot be declared merely by editing a lock or PR description. The backend reverse lock's `contract_anchor_sha`, read from the tested backend checkout during `backend-transition`, must later equal this same SHA; it cannot be self-referential inside anchor `A`. The backend `A..HEAD` confinement separately proves no later contract change. A same-manifest pin-only change fails. Test the structural declaration and a same-digest non-anchor bump on both PR and push events.

`backend-transition` accepts only: initial installation; no SHA change; or the single reverse-pin follow-up where `manifest_sha256` is unchanged, `aim_data_sha` advances to the fetched AIM commit whose own lock names `A` and that digest, and `contract_anchor_sha` either remains `A` or changes once from an initial placeholder to `A`. The placeholder must be a valid pre-`A` backend ancestor, never a floating ref; no later change to `contract_anchor_sha` is allowed except a new reviewed paired wire anchor. Require the diff from `A` to the tested `HEAD` to contain only the two permitted paths below. Any non-anchor pin bump fails. The push of the AIM merge classifies against its `before` SHA as no-change or a permitted AIM transition; the push of the backend merge classifies the reverse-pin sequence against its `before` SHA, with the same anchored evidence. Test both.

`anchor-diff` runs:

```bash
git merge-base --is-ancestor "$CONTRACT_ANCHOR_SHA" HEAD
git diff --exit-code "$CONTRACT_ANCHOR_SHA"..HEAD -- . ':(exclude)preview-contract-aim-data.lock.json' ':(exclude).github/workflows/preview-contract-cross-repo.yml'
```

The entire `A..HEAD` tree diff is confined to the reverse lock and the named workflow; a changed, added, renamed, or deleted path anywhere else fails, including `app/services/listing_preview_disclosure.py`. AIM paths are never compared in a backend diff; they execute from the pinned AIM checkout. Once AIM pins `A`, the backend branch must not amend, rebase, or delete `A`. Test a disposable post-anchor change to `app/services/listing_preview_disclosure.py` and require nonzero `anchor-diff` exit.

## 5. Exact workflows and runner commands

### 5.1 AIM Data `.github/workflows/preview-contract-cross-repo.yml`

```yaml
name: Preview contract cross-repo

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  preview-contract-cross-repo:
    name: Preview contract cross-repo
    runs-on: ubuntu-latest
    timeout-minutes: 40
    env:
      VECTORAIZ_AUTH_ENABLED: 'false'
      VECTORAIZ_DATA_DIRECTORY: /tmp/preview-contract/data
      VECTORAIZ_UPLOAD_DIRECTORY: /tmp/preview-contract/uploads
      VECTORAIZ_PROCESSED_DIRECTORY: /tmp/preview-contract/processed
      DATABASE_URL: sqlite:////tmp/preview-contract/test.db
    steps:
      - name: Checkout AIM Data
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Validate lock
        id: lock
        run: python scripts/preview_contract_gate.py lock --kind aim-data --file preview-contract-backend.lock.json --github-output "$GITHUB_OUTPUT"
      - name: Require target-only backend key
        env:
          DEPLOY_KEY: ${{ secrets.PREVIEW_CONTRACT_BACKEND_READ_DEPLOY_KEY }}
        run: test -n "$DEPLOY_KEY"
      - name: Checkout pinned backend
        uses: actions/checkout@v4
        with:
          repository: aidotmarket/ai-market-backend
          ref: ${{ steps.lock.outputs.backend_sha }}
          path: peer/ai-market-backend
          ssh-key: ${{ secrets.PREVIEW_CONTRACT_BACKEND_READ_DEPLOY_KEY }}
          fetch-depth: 0
          persist-credentials: false
      - name: Verify checkout and manifest
        run: |
          test "$(git -C peer/ai-market-backend rev-parse HEAD)" = "${{ steps.lock.outputs.backend_sha }}"
          python scripts/preview_contract_gate.py verify-manifest --corpus peer/ai-market-backend/tests/fixtures/preview/cross_repo_contract/v1 --expected "${{ steps.lock.outputs.manifest_sha256 }}"
          python scripts/preview_contract_gate.py aim-transition --event "$GITHUB_EVENT_PATH" --peer peer/ai-market-backend
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install isolated repositories
        run: |
          python -m venv /tmp/preview-contract/aim-venv
          /tmp/preview-contract/aim-venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt -r requirements-dev.txt
          python -m venv /tmp/preview-contract/backend-venv
          /tmp/preview-contract/backend-venv/bin/pip install -r peer/ai-market-backend/requirements.txt -r peer/ai-market-backend/requirements-dev.txt
          mkdir -p /tmp/preview-contract/data /tmp/preview-contract/uploads /tmp/preview-contract/processed /tmp/preview-contract/results
      - name: Run both implementations
        run: |
          /tmp/preview-contract/backend-venv/bin/python peer/ai-market-backend/tests/preview_contract_runner.py --repo-root peer/ai-market-backend --corpus peer/ai-market-backend/tests/fixtures/preview/cross_repo_contract/v1 --output /tmp/preview-contract/results/backend.json
          /tmp/preview-contract/aim-venv/bin/python tests/preview_contract_runner.py --repo-root . --corpus peer/ai-market-backend/tests/fixtures/preview/cross_repo_contract/v1 --output /tmp/preview-contract/results/aim-data.json
          /tmp/preview-contract/aim-venv/bin/python scripts/preview_contract_gate.py coverage --result /tmp/preview-contract/results/aim-data.json
          /tmp/preview-contract/backend-venv/bin/python peer/ai-market-backend/scripts/preview_contract_gate.py coverage --result /tmp/preview-contract/results/backend.json
          /tmp/preview-contract/aim-venv/bin/python scripts/preview_contract_gate.py compare --corpus peer/ai-market-backend/tests/fixtures/preview/cross_repo_contract/v1 --left /tmp/preview-contract/results/aim-data.json --right /tmp/preview-contract/results/backend.json
          node tests/preview_differential_check.cjs peer/ai-market-backend/tests/fixtures/preview/cross_repo_contract/v1
      - name: Focused regressions and deletion proof
        run: |
          /tmp/preview-contract/aim-venv/bin/python -m pytest -q tests/test_preview_contract_cross_repo.py tests/test_preview_disclosure_schemas.py tests/test_preview_lifecycle.py tests/test_preview_signing_service.py tests/test_preview_producer_evidence.py
          /tmp/preview-contract/aim-venv/bin/python tests/run_preview_producer_synthetic.py --output /tmp/preview-contract/synthetic-bundle --reference tests/fixtures/preview-producer-synthetic-shas.json --contract-corpus peer/ai-market-backend/tests/fixtures/preview/cross_repo_contract/v1
          /tmp/preview-contract/aim-venv/bin/python scripts/preview_contract_gate.py deleted-consumers
```

### 5.2 Backend `.github/workflows/preview-contract-cross-repo.yml`

```yaml
name: Preview contract cross-repo

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  preview-contract-cross-repo:
    name: Preview contract cross-repo
    runs-on: ubuntu-latest
    timeout-minutes: 40
    env:
      DATABASE_URL: sqlite+aiosqlite:////tmp/preview-contract/backend.db
      SECRET_KEY: preview-contract-ci-only-not-production
    steps:
      - name: Checkout backend with anchor history
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Validate lock
        id: lock
        run: python scripts/preview_contract_gate.py lock --kind backend --file preview-contract-aim-data.lock.json --github-output "$GITHUB_OUTPUT"
      - name: Require target-only AIM Data key
        env:
          DEPLOY_KEY: ${{ secrets.PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY }}
        run: test -n "$DEPLOY_KEY"
      - name: Checkout pinned AIM Data
        uses: actions/checkout@v4
        with:
          repository: aidotmarket/aim-data
          ref: ${{ steps.lock.outputs.aim_data_sha }}
          path: peer/aim-data
          ssh-key: ${{ secrets.PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY }}
          fetch-depth: 0
          persist-credentials: false
      - name: Verify pins, anchor, and manifest
        run: |
          test "$(git -C peer/aim-data rev-parse HEAD)" = "${{ steps.lock.outputs.aim_data_sha }}"
          python scripts/preview_contract_gate.py verify-manifest --corpus tests/fixtures/preview/cross_repo_contract/v1 --expected "${{ steps.lock.outputs.manifest_sha256 }}"
          python scripts/preview_contract_gate.py backend-transition --event "$GITHUB_EVENT_PATH" --peer peer/aim-data
          CONTRACT_ANCHOR_SHA="${{ steps.lock.outputs.contract_anchor_sha }}" python scripts/preview_contract_gate.py anchor-diff
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install isolated repositories
        run: |
          python -m venv /tmp/preview-contract/backend-venv
          /tmp/preview-contract/backend-venv/bin/pip install -r requirements.txt -r requirements-dev.txt
          python -m venv /tmp/preview-contract/aim-venv
          /tmp/preview-contract/aim-venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu -r peer/aim-data/requirements.txt -r peer/aim-data/requirements-dev.txt
          mkdir -p /tmp/preview-contract/data /tmp/preview-contract/uploads /tmp/preview-contract/processed /tmp/preview-contract/results
      - name: Run both implementations
        run: |
          /tmp/preview-contract/backend-venv/bin/python tests/preview_contract_runner.py --repo-root . --corpus tests/fixtures/preview/cross_repo_contract/v1 --output /tmp/preview-contract/results/backend.json
          /tmp/preview-contract/aim-venv/bin/python peer/aim-data/tests/preview_contract_runner.py --repo-root peer/aim-data --corpus tests/fixtures/preview/cross_repo_contract/v1 --output /tmp/preview-contract/results/aim-data.json
          /tmp/preview-contract/backend-venv/bin/python scripts/preview_contract_gate.py coverage --result /tmp/preview-contract/results/backend.json
          /tmp/preview-contract/aim-venv/bin/python peer/aim-data/scripts/preview_contract_gate.py coverage --result /tmp/preview-contract/results/aim-data.json
          /tmp/preview-contract/backend-venv/bin/python scripts/preview_contract_gate.py compare --corpus tests/fixtures/preview/cross_repo_contract/v1 --left /tmp/preview-contract/results/backend.json --right /tmp/preview-contract/results/aim-data.json
          node peer/aim-data/tests/preview_differential_check.cjs tests/fixtures/preview/cross_repo_contract/v1
      - name: Focused regressions
        run: |
          /tmp/preview-contract/backend-venv/bin/python -m pytest -q tests/test_preview_contract_cross_repo.py tests/test_listing_preview_contracts.py tests/test_listing_preview_database.py
```

Neither workflow contains `pull_request_target`, a bless/update flag, an artifact containing SSH configuration, or a conditional secret skip. A fork PR without the secret fails at the key preflight.

## 6. Credentials, bootstrap, and enforcement

### 6.1 Two credentials

Provision only after Max authorizes the provider mutation:

| Holder repository secret | Read-only deploy key attached to target | Infisical identity (name only) |
|---|---|---|
| AIM Data: `PREVIEW_CONTRACT_BACKEND_READ_DEPLOY_KEY` | `aidotmarket/ai-market-backend`, title `preview-contract-from-aim-data` | `ai-market-backend/prod/github-actions/preview-contract/aim-data/PREVIEW_CONTRACT_BACKEND_READ_DEPLOY_KEY` |
| Backend: `PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY` | `aidotmarket/aim-data`, title `preview-contract-from-backend` | `ai-market-backend/prod/github-actions/preview-contract/backend/PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY` |

Local SecOps generates two independent Ed25519 keypairs, stores each private key directly in the named Infisical entry, installs each public key on only its target with `read_only:true`, and copies the private value directly into only the named holder repository secret. Do not print, export to a transcript, reuse, give write access, or add either value to a PR input or artifact.

Before the first workflow run, smoke-test each key in an isolated `GIT_SSH_COMMAND` process. Run `git ls-remote <target SSH URL> refs/heads/main`, require exactly one nonempty `<40-hex-SHA><TAB>refs/heads/main` record, then `git fetch --no-tags <target SSH URL> <pinned SHA>` into an empty temporary repository and require `git rev-parse FETCH_HEAD` to equal the pinned SHA exactly. This proves the specific commit is readable even if it is not a ref. With the same key, `git ls-remote <holder SSH URL> refs/heads/main` must exit nonzero. Do not treat exit zero with empty output as success. Then verify the holder secret exists by name and run a temporary workflow checkout. Record only exit status, target/holder repository slugs, resolved SHA, key/deploy-key ID, date, and workflow URL, never credential values.

Rotation is add-before-remove: generate a new pair; add the new read-only public key to the same target; replace the named Infisical value and holder GitHub secret without printing it; repeat both positive and negative smoke tests; rerun both gates; then delete the old deploy key and record old/new deploy-key IDs. A suspected disclosure revokes the affected direction immediately; that gate remains failed closed until replacement.

### 6.2 Bootstrap order

1. Create both target-only keys, Infisical entries, and holder secrets; pass positive/negative smoke tests.
2. Open the paired implementation PRs. Commit backend anchor `A`; set AIM's lock to `A` and its manifest digest.
3. Observe one successful `Preview contract cross-repo` PR job in each repository. The backend may use a diagnostic reverse pin but remains unmergeable.
4. **Max-gated admin step:** read existing protection in both repositories. After the new check has reported green, atomically replace only the obsolete required context from the deleted workflow (`producer-contract`, if present) with `Preview contract cross-repo`, apply the remaining protection/merge-method settings below, and read them back before either merge.
5. Prove a disposable failing mutation PR is unmergeable by an administrator.
6. Merge AIM Data as `B`; add the backend's one reverse-pin follow-up naming `B`; rerun; merge backend by merge commit; confirm both `main` jobs pass and `A` is an ancestor.

### 6.3 Exact protection settings and read-back

For each of `aidotmarket/aim-data` and `aidotmarket/ai-market-backend`, Max preserves all unrelated stronger existing protection and applies these exact minimums: required check `Preview contract cross-repo`, strict/up-to-date branch required, administrators enforced, zero pull-request bypass actors, force pushes disabled, deletions disabled, and repository merge methods `allow_merge_commit=true`, `allow_squash_merge=false`, `allow_rebase_merge=false`. First read both `contexts` and `checks` from protection; if the deleted AIM workflow's `producer-contract` appears in either, remove precisely that entry in the same required-status-checks API update that adds the observed new context. Do not remove any other context or check. The backend has no deleted parity workflow; retain any backend `producer-contract` producer if one exists. Refuse the transition if the new check has not reported green on the implementation PR. Read protection back immediately after the update and require the new context present and the obsolete AIM context absent before merge.

The Max-gated commands are:

```bash
REPO=aidotmarket/aim-data
gh api "repos/$REPO/branches/main/protection" > /tmp/preview-protection-before.json
jq --arg repo "$REPO" '{strict:true,contexts:(((.required_status_checks.contexts // []) | map(select(. != (if $repo == "aidotmarket/aim-data" then "producer-contract" else "__never__" end)))) + ["Preview contract cross-repo"] | unique),checks:((.required_status_checks.checks // []) | map(select(.context != (if $repo == "aidotmarket/aim-data" then "producer-contract" else "__never__" end))))}' /tmp/preview-protection-before.json > /tmp/preview-required-checks.json
gh api --method PUT "repos/$REPO/branches/main/protection/required_status_checks" --input /tmp/preview-required-checks.json
gh api --method POST "repos/$REPO/branches/main/protection/enforce_admins"
gh api --method DELETE "repos/$REPO/branches/main/protection/allow_force_pushes" || test "$?" = 1
gh api --method DELETE "repos/$REPO/branches/main/protection/allow_deletions" || test "$?" = 1
gh api --method PATCH "repos/$REPO" -F allow_merge_commit=true -F allow_squash_merge=false -F allow_rebase_merge=false
test "$(jq '.required_pull_request_reviews.bypass_pull_request_allowances.users | length' /tmp/preview-protection-before.json)" = 0
test "$(jq '.required_pull_request_reviews.bypass_pull_request_allowances.teams | length' /tmp/preview-protection-before.json)" = 0
test "$(jq '.required_pull_request_reviews.bypass_pull_request_allowances.apps | length' /tmp/preview-protection-before.json)" = 0
gh api "repos/$REPO/branches/main/protection" --jq '{contexts:.required_status_checks.contexts,checks:.required_status_checks.checks,strict:.required_status_checks.strict,enforce_admins:.enforce_admins.enabled,force_pushes:.allow_force_pushes.enabled,deletions:.allow_deletions.enabled,bypass:.required_pull_request_reviews.bypass_pull_request_allowances}'
gh api "repos/$REPO" --jq '{allow_merge_commit,allow_squash_merge,allow_rebase_merge}'
```

Repeat with `REPO=aidotmarket/ai-market-backend`. If any bypass array is nonempty, stop: Max must remove the named allowance in GitHub before proceeding; the command deliberately does not silently erase an existing governance setting. Preserve the two read-back outputs, failed-mutation mergeability API output, and job URLs.

For rollback, keep the replacement workflow and its required check runnable while reverting contract and pin commits, in the backend-first then AIM order in §10. Revert the AIM workflow deletion only after both reverted mains have green `Preview contract cross-repo` jobs. If restoring the old parity workflow is necessary, first observe its `producer-contract` job green on the rollback PR, then in one Max-gated required-status-checks API update replace `Preview contract cross-repo` with `producer-contract`; read back contexts/checks immediately. Merge the workflow restoration only after that read-back. Preserve every unrelated required check and stronger protection setting throughout. Record the before/after protection JSON and green job URLs. Never leave a revision requiring a context with no producer; if either check cannot report green, stop rollback before merge and use a new paired repair PR.

## 7. Deletion closure

The deleted AIM workflow checks out only AIM Data (`preview-contract-parity.yml:21-30`). The deleted checker hashes an AIM-local manifest and reports no backend copy by default (`scripts/check_preview_fixture_parity.py:12-16,54-80`); its test supplies that same local file as both operands (`tests/test_preview_fixture_parity.py:17-18`). The deleted differential generator derives expected bytes from the AIM serializer (`tests/preview_differential_corpus.py:29-76`), and the Node program reads that output. The request/signing goldens are AIM-only consumers (`tests/test_preview_signing_service.py:129-133,567-568`). None can detect a backend-only optional field.

`deleted-consumers` must run `git grep` over executable paths (`.github`, `app`, `scripts`, `tests`, excluding immutable report text) and fail on every deleted basename or module name. It also asserts:

- `build_preview_producer_evidence.py` emits `contract_manifest_sha256`, never `fixture_manifest_sha256`.
- `run_preview_producer_synthetic.py` succeeds with a verified fetched corpus.
- `test_pinned_differential_corpus_python_and_node` uses the fetched backend corpus.
- `preview_differential_check.cjs` has no AIM-owned expected-byte path.

Historical reports may retain old names but cannot be executable inputs.

## 8. T-811 ports and required tests

1. Port backend recursive `public_types` and `binary_sample_forbidden` to `DisclosureBinding.binding_rules`; unit and corpus tests cover top-level binary, array-of-binary, object-field binary, object→array→binary, and an ordinary nested public schema (`backend@d5d2e391…:127-143`; AIM insertion at `6529e1ed…:123-139`).
2. Expand AIM package identity from four members to all nine: URL, media type, profile, byte ceiling, scan policy, scan policy version, scanned at, scan verdict, signer reference. Add the before-validator in both request classes as specified in §3.3 so all nine negative vectors reach `package_mismatch` before nested/later validators; a uniform v1 proof still reaches `unsupported_proof` (`aim-data@6529e1ed…:187-199`; backend `d5d2e391…:202-219`).
3. Compute the per-request sampled digest once and reject any proof whose `sampled_leaf_list_digest` differs with exact code `sampled_leaf_list_mismatch` (`backend@d5d2e391…:230-236`).
4. Preserve omitted/v1/v2 `aggregate_hash_profile` through AIM withdraw/refresh/supersede and backend allocation/withdrawal. Legacy serialization omits the key (`aim-data@6529e1ed…:44-79`; backend `d5d2e391…:48-83`).
5. Assert Pydantic `literal_error` directly for every literal vector in §3.3; no `ValueError` base assertion or message substring passes.
6. Exercise v1 and v2 via `proof-model`, while `request-proof-v1-unsupported` independently proves transport rejection.

## 9. Acceptance and evidence map

Evidence lives in both implementation PR descriptions and the “Changing the verified-preview wire contract” history table in `aim-data.md`: exact `A`, `B`, merge SHAs, manifest digest, workflow job URLs, mutation SHAs/job URLs, deploy-key IDs (never values), protection read-backs, and rollback result.

| Gate 1 AC | Exact proof |
|---|---|
| AC1 | `pytest ...test_preview_contract_cross_repo.py -k lock`; both workflow checkout-SHA assertions; missing-secret fork job URL |
| AC2 | `preview_contract_gate.py verify-manifest`; exact corpus tree/file-set report |
| AC3 | both `Run both implementations` job logs and `compare` result for legacy/v1/v2/request/envelope |
| AC4 | `local-candidate-*` and `request-approve-v2`/CR results, byte equality report |
| AC5 | all `extra-*`, `literal-*`, and custom-code vectors; diagnostic error-code-swap mutation fails both runners |
| AC6 | four binary vectors, nine package mismatch vectors, sampled-leaf mismatch, and focused AIM tests |
| AC7 | nine lifecycle request vectors plus both repositories' lifecycle/database tests |
| AC8 | `deleted-consumers`, focused tests, Node run, evidence-builder run, and `git grep` report |
| AC9 | Disposable M1 and M2 anchors. M1 adds optional omit-None binding field **and** v2 vector/bytes; M2 adds the field with no vector. For each, AIM pin-only branch fails and backend fails before pin, then still fails after diagnostic pin: M1 by acceptance/bytes, M2 by coverage. Record three failing job URLs per mutation and both mutation SHAs, then delete branches. Unit simulation is supplemental only. |
| AC10 | `coverage` reports; use the disposable paired diagnostic corpus/anchor below to remove `proof-v1-policy-v1`; record both jobs passing integrity/transition and runner stages, then failing coverage on the missing direct proof v1 value |
| AC11 | transition unit tests; diagnostic same-manifest bump to a non-anchor commit fails both applicable jobs |
| AC12 | GitHub protection/repository read-backs; administrator sees disposable failing PR as not mergeable; post-merge `git merge-base --is-ancestor A main` |
| AC13 | two positive target and two negative holder smoke-test records; fork PR failure; `git grep pull_request_target .github/workflows/preview-contract-cross-repo.yml` has no hit |
| AC14 | both post-merge `main` job URLs; timeline shows no red main interval; anchor ancestry output |
| AC15 | runbooks diff and refreshed `INDEX.md` metadata only if purpose/verification date changes |
| AC16 | unanimous Gate 3 GLM, DeepSeek, Gemini reports bound to exact candidate SHA |

For the error-code-swap mutation, change only `sampled_leaf_list_mismatch` to `sampled_leaf_digest_mismatch`; both remain Pydantic `value_error`, and both jobs must fail on code inequality. For the non-anchor bump, choose an exact fetched commit that changes no contract path and keep `manifest_sha256` unchanged; transition classification must fail before runners. Never merge mutation branches.

For the AC10 v1-removal diagnostic, fork disposable paired branches from a known green pair. In the backend branch, remove only the `proof-v1-policy-v1` row, its input, and its byte file; regenerate canonical `manifest.json` and `manifest.sha256`, commit these as a new diagnostic anchor `A_v1`, and leave all model code unchanged. In the AIM branch, update only its lock to `backend_sha=A_v1` and the recomputed manifest digest; the `aim-transition` rule treats this changed corpus commit as a new diagnostic anchor. For the backend reverse job, make one disposable reverse-pin commit whose lock names `A_v1`, the diagnostic AIM commit, and the same digest, so `backend-transition` and `anchor-diff` pass. Run both PR jobs. Their recorded logs must show successful lock/manifest verification and runner completion, then `coverage` failure naming the proof contract's missing direct `package_profile=aim-preview-package-v1` (and `scan_policy=aim-preview-policy-v1`) observation. The diagnostic manifest and locks are changed together; a stale digest/file-set failure does not count. Never merge these branches; remove them after recording both job URLs and exact SHAs.

## 10. Runbook change and rollback

After both code mains are green, update existing `aidotmarket/runbooks/aim-data.md`; do not create a new page and do not move the procedure to `listing-enrichment-platform-signing-key.md`. Add “Changing the verified-preview wire contract” with: paired-branch creation; vector-first backend anchor `A`; raw byte review; AIM pin/compatibility work and first merge `B`; backend reverse-pin-only follow-up; merge-commit ancestry check; credential names/scopes and rotation; lock-transition rules; protected-check bootstrap; required evidence fields; and the rollback sequence below. Refresh `INDEX.md` only if its purpose text or verification date changes.

Rollback:

1. Before either merge, close both PRs and revoke only newly installed keys if abandoning the gate.
2. After AIM-only merge, use a rollback PR that retains the runnable new workflow and required check while reverting AIM's contract/pin changes; backend main is unchanged. Observe a green main gate. If restoring the old workflow is necessary, use the Max-gated check migration in §6.3 after its job reports green; only then merge workflow restoration and remove the new key.
3. After both merges, revert backend contract/pin changes first only while AIM remains backward-compatible, then revert AIM's contract/pin changes. Retain runnable gates and run both main gates after each revert. Restore the old workflow only through the §6.3 protection migration.
4. Never delete the authoritative corpus, float/loosen a pin, rewrite anchor `A`, or bypass the required check to make rollback green.
5. A non-backward-compatible wire rollback is a new paired wire change with a new anchor, vectors, pins, reviews, and evidence.

S1732 itself adds no wire field, literal, profile, API, database shape, service, package, or customer-data path. Its only behavior repairs are the approved producer validation parity and legacy profile preservation above.
