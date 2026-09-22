# BQ-PREVIEW-CONTRACT-CROSS-REPO-GATE-S1732 — Gate 1 design

Status: **GATE 1 R2 candidate — R1 findings folded; awaiting unanimous GLM, DeepSeek and Gemini review.** This is a design only; it authorises no implementation, deployment, credential mutation or customer-data access.

Source identities read for this design:

- `aidotmarket/aim-data@6529e1ed4d5983a87a9b1e2faadda32e18d4cf76` (`origin/main`, 2026-09-22).
- `aidotmarket/ai-market-backend@30a5415085142e610e4b9cb9f85129f5966f09e8` (`origin/main`, 2026-09-22).

## 1. Outcome and decisions

The preview wire has one backend-owned corpus of inputs, rejection cases, canonical bytes and digests. CI in **both** private repositories checks out the other repository at a committed 40-hex SHA and runs those same vectors through both real Pydantic models and both real signing serializers. A schema-only comparison is not sufficient and is not part of the gate.

Binding decisions:

1. **The backend owns the golden vectors.** They live at `ai-market-backend/tests/fixtures/preview/cross_repo_contract/v1/`. The backend allocates the binding and accepts the producer request, so a proposed backend wire change creates the candidate corpus. AIM Data may consume but may not copy or regenerate an authoritative corpus.
2. **Pins never float.** AIM Data commits `preview-contract-backend.lock.json` with `backend_sha` and `manifest_sha256`; the backend commits `preview-contract-aim-data.lock.json` with the three required fields `aim_data_sha`, `contract_anchor_sha` and the same `manifest_sha256`. Both repo SHAs and the anchor SHA are exactly 40 lowercase hex characters. No branch, tag, `HEAD`, API “latest” lookup, submodule remote tip or dependency resolver is accepted.
3. **Every preview wire change is a paired change.** The backend PR must produce the immutable contract-anchor commit; the AIM Data PR must bump `backend_sha` to that exact commit and implement the matching producer behavior; the backend PR cannot merge until its reverse gate pins and passes against the merged AIM Data commit.
4. **The anchor commit is preserved.** Once AIM Data pins backend anchor `A`, the backend PR may add only its AIM Data pin/workflow commit. It must merge by merge commit so that `A` remains an ancestor of backend `main`; squash and rebase are forbidden. The backend branch is not deleted before that merge.
5. **Existing broad dataset fixtures are not renamed into this gate.** Only the new directory above is authoritative for the cross-repository preview wire. Producer-only package/policy tests can remain local, but they cannot satisfy this gate.
6. **The existing runbook page is `aim-data.md`.** `INDEX.md:129-136` identifies it as the source of truth for the seller-local product and its marketplace integration. Gate 2 adds a “Changing the verified-preview wire contract” procedure there; no new runbook page is created. The signing-key page remains about key operation, not contract evolution (`listing-enrichment-platform-signing-key.md:11-29`).

## 2. Ground truth and incident seam

The present AIM workflow checks out only its own repository (`aim-data/.github/workflows/preview-contract-parity.yml:21-30`), then calls a local manifest checker and local tests (`:39-66`). That checker hard-codes a digest for a file inside AIM Data and, when no external path is supplied, explicitly reports that no backend copy was supplied (`aim-data/scripts/check_preview_fixture_parity.py:12-16,54-80`). Its test passes that same local file back as the supposed backend copy (`aim-data/tests/test_preview_fixture_parity.py:17-18`). These checks cannot observe a backend-only model or serializer change.

This is a byte-level compatibility boundary:

- Both repositories use a closed serializer that validates, dumps JSON and passes it to canonical JSON bytes (`aim-data/app/services/preview_signing_service.py:48-57`; backend `app/utils/preview_signing.py:28-37`).
- The disclosure signature preimage adds a fixed domain prefix to those bytes (`aim-data/app/services/preview_signing_service.py:121-126`; backend `app/utils/preview_signing.py:101-106`). The platform envelope is separately domain-prefixed and conditionally omits `valid_until` (`aim-data/app/services/preview_signing_service.py:129-138`; backend `app/utils/preview_signing.py:109-118`).
- `aggregate_hash_profile` is optional for legacy records and is omitted, rather than emitted as `null`, by both model serializers (`aim-data/app/models/preview_disclosure_schemas.py:44-48,74-79`; backend `app/schemas/listing_preview.py:48-52,78-83`). Adding that field to only one model therefore changes signed bytes even when the Python value is `None`.
- AIM Data freezes the backend candidate as exact serialized bytes and refuses a changed reserialization (`aim-data/app/services/preview_signing_service.py:290-313`). Its full request serializer is the actual request preimage boundary (`:316-375`).

The gate therefore compares accepted/rejected values **and exact output bytes**, including every omission rule, default, normalized UUID/timestamp, nested commitment/proof and envelope.

## 3. Canonical corpus and runner

### 3.1 Files and format

Backend directory `tests/fixtures/preview/cross_repo_contract/v1/` contains:

- `manifest.json`: canonical UTF-8 JSON with sorted keys and no insignificant whitespace. Each row has `id`, `operation`, `input_path`, `expected` (`accept` or `reject`); a rejection has `expected_error_type` (the Pydantic `type`, such as `literal_error`, `extra_forbidden` or `value_error`) and, when a custom validator is expected, `expected_error_code` (the semantic string, such as `sampled_leaf_list_mismatch` or `binary_sample_forbidden`); an acceptance has `bytes_path`, `byte_length` and lowercase SHA-256.
- `manifest.sha256`: `<sha256><two spaces>manifest.json\n`, hashing the exact committed `manifest.json` bytes.
- `inputs/<id>.json`: a complete closed input, never a partial schema sketch.
- `bytes/<id>.bin`: the exact expected output, including the domain prefix where the operation is a signature preimage. Raw `.bin` is authoritative; a hex string in a test report is diagnostic only.

The manifest itself contains no signature private material. Existing synthetic public keys/signatures may be copied into the new backend-owned inputs only where verification is part of the operation. No raw dataset row, customer value, credential, path or customer identifier is admitted.

Both repositories expose a small runner with the same operation names, but neither runner generates or blesses expected bytes in CI:

- `binding-model`, `disclosure-preimage`, `request-model`, `request-bytes`, `platform-envelope-model`, `platform-envelope-preimage`, and `local-candidate`.
- For `accept`, each runner must accept the input and its output must byte-equal `bytes/<id>.bin`; the two outputs must also byte-equal each other.
- For `reject`, each runner must reject at model validation before signing and independently assert the exact Pydantic error `type` named by `expected_error_type` and, for a custom validator, the exact normalized semantic string named by `expected_error_code`. Matching only “raised an exception,” only `value_error`, or only a message substring is a failure. Unknown-literal vectors assert `type == "literal_error"` directly.
- A separate verifier recomputes every file digest, the manifest digest and completeness (no unmanifested input/byte file). CI has no update/bless flag. A developer-only generator may write a temporary proposal, but review must show the byte diff before it replaces committed vectors.

The verifier also enforces **schema-coverage completeness in both repositories' cross-repo jobs**. Each repository derives fields from its own imported Pydantic `model_fields`, rather than from a hand-written field list: backend `DisclosureBinding`, `PreviewDisclosureRequest` and `PlatformEnvelope` (`app/schemas/listing_preview.py:29,157,314`) plus `PreviewSignedProofContract` and `PreviewSignedCommitmentContract` (`app/schemas/dataset_commitment.py:331,377`); AIM Data `DisclosureBinding`, `PreviewDisclosureRequest` and `PlatformEnvelope` (`app/models/preview_disclosure_schemas.py:25,142,291`) plus `DatasetPreviewProofContract` and `DatasetCommitmentContract` (`app/models/dataset_commitment_schemas.py:212,262`). For every named model, the checker fails unless every field is present in at least one accept vector executed through that model, every optional field is also absent in at least one accept vector executed through that model, and every allowed value of every `Literal` or enum field is present in at least one accept vector. Coverage is attributed by parsed model and nested field path, never by text search. This is a corpus-completeness guard, not a schema-equality substitute for the byte gate.

### 3.2 Required vector matrix

The initial corpus is complete only when it covers:

| Family | Required cases and assertions |
|---|---|
| Legacy / v1 / v2 binding | Legacy has no `aggregate_hash_profile` key and its canonical preimage remains byte-identical; v1 and v2 carry `aim-approved-aggregates-v1` and `aim-approved-aggregates-v2` respectively and produce distinct pinned bytes. The backend currently allocates v2 explicitly (`backend app/services/listing_preview_disclosure.py:103-110`). |
| Complete request | Approve, `none` (the fixture key for the no-sample lifecycle), withdraw, refresh and `supersede` (the fixture key for supersession) with nested binding, commitment and proofs. Backend request round-trips already use those five shapes (`backend tests/test_listing_preview_contracts.py:299-302`); the new gate pins their exact complete request bytes in both implementations. |
| Complete platform envelope | Binding + seller signature + signer keys + platform signature, including open-ended `valid_until` omission and nested legacy/v1/v2 binding preimages. |
| Backend → producer | A backend-allocated candidate is accepted by AIM Data `LocalCandidate.validate`, and its stored/re-read `binding_bytes` equal the backend bytes. Unknown fields are rejected rather than dropped. |
| Producer → backend | An AIM Data `construct_request` result is accepted by backend `PreviewDisclosureRequest`; backend reserialization equals AIM request bytes. The producer constructs and validates the whole request before signing (`aim-data/app/services/preview_signing_service.py:316-365`). |
| Package identity | Two proofs differing in any of `preview_package_url`, `package_media_type`, `package_profile`, `package_byte_ceiling`, `scan_policy`, `scan_policy_version`, `scanned_at`, `scan_verdict` or `signer_reference` reject with package mismatch. Backend includes all nine (`backend app/schemas/listing_preview.py:202-219`); AIM Data currently includes only the first four (`aim-data/app/models/preview_disclosure_schemas.py:187-199`). |
| Sampled leaves | A per-proof `sampled_leaf_list_digest` differing from the computed list rejects as `sampled_leaf_list_mismatch`, matching backend `app/schemas/listing_preview.py:230-236`. |
| Closed vocabulary | Unknown field at request, binding, commitment, proof and nested envelope levels rejects as `extra_forbidden`; an unknown value for each safety-relevant `Literal` rejects as **`literal_error`**. The assertion is directly on the Pydantic error type, not a base exception or message substring. AIM Data's closed base already sets `extra="forbid"` (`aim-data/app/models/dataset_commitment_schemas.py:18-25`). |
| Public schema types | Top-level binary, array-of-binary, object-field binary and object→array→binary all reject as `binary_sample_forbidden`; ordinary nested public types accept. Backend recursion is at `backend app/schemas/listing_preview.py:127-138`; AIM Data presently goes directly from `CanonicalSchema` to descriptor checks (`aim-data/app/models/preview_disclosure_schemas.py:123-139`). |
| Lifecycle inheritance | For legacy, v1 and v2 prior bindings, withdraw, refresh and supersession preserve the wire profile: legacy remains omitted; v1 remains v1; v2 remains v2. AIM lifecycle helpers copy the old binding (`aim-data/app/services/preview_lifecycle.py:124-176`), while current tests assert other fields but omit this field (`aim-data/tests/test_preview_lifecycle.py:62-93`). Backend withdrawal currently converts an absent legacy key to explicit v1 (`backend app/services/listing_preview_disclosure.py:113-145,201-208`); Gate 2 changes both sites to preserve `None`/omission while retaining semantic-v1 comparison for historical records. This is a compatibility repair, not a new profile. |

The current Node differential checker is retained only as an independent serializer implementation, changed to read the fetched backend corpus. Its useful byte/digest/signature assertions are at `aim-data/tests/preview_differential_check.cjs:31-46`; its AIM-generated local corpus is not retained as a second source.

## 4. Drift disposition from T-811

| Drift | Decision |
|---|---|
| Backend recursive `public_types` / `binary_sample_forbidden` | **Port to AIM Data** and cover top-level and nested-binary rejection vectors/tests (§3.2). This is producer admission, not merely backend policy. |
| `PreviewDisclosureRequest` proof package tuple | **Port the five missing members to AIM Data** and cover every member by vectors. AIM proof models already carry all fields (`aim-data/app/models/dataset_commitment_schemas.py:212-232`); the omission is only in request agreement. |
| Per-proof `sampled_leaf_list_mismatch` | **Port to AIM Data** and cover by an exact rejection vector; otherwise the producer can sign a request the backend refuses. |
| `aggregate_hash_profile` lifecycle behavior | **Repair backend legacy withdrawal and complete both repos' tests**, with legacy omission plus v1/v2 preservation across withdraw, refresh and supersession (§3.2). No wire field is added by this work. |
| Unknown literal assertion | **Port/complete tests** and assert `literal_error` directly in each runner. A generic `ValueError` assertion is vacuous. |
| `PlatformEnvelope` | **Covered by vectors** because it is signed by the backend and verified by AIM Data. |
| `ListingPreviewManifest`, `PreviewColumn`, `PreviewLimits`, `PreviewApproval` | **Out of scope for this gate.** They are backend-owned buyer/public response projections after request acceptance (`backend app/schemas/listing_preview.py:347-421`), not producer candidate/request or shared signing-preimage input. `PreviewApproval`'s nested `PlatformEnvelope` is covered; if AIM Data later consumes any wrapper, that use must first add it to this corpus. |

## 5. CI in both directions

### 5.1 Credential and checkout contract

Use two distinct read-only deploy-key credentials, each attached to and able to read exactly one target repository, with no user account or shared expiry coupling. AIM Data alone holds the private credential for the read-only deploy key attached to `ai-market-backend`, as GitHub Actions secret `PREVIEW_CONTRACT_BACKEND_READ_DEPLOY_KEY`. The backend alone holds the separate private credential for the read-only deploy key attached to `aim-data`, as `PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY`. Each value is stored as a separate Infisical secret under CORE S2; no value is ever committed, printed, placed in an artifact or accepted from a PR input. Rotation follows `infisical-secrets.md`; only mechanisms and secret names appear in code.

Each workflow is triggered by `pull_request` and by `push` to `main`, never by `pull_request_target`: fork-controlled code must never receive a repository secret. It validates the lock schema before using the credential, checks out its own PR with the normal job token, then checks out the other private repository into a fixed sibling directory using the target-only read secret and the lock's exact SHA. It verifies `git rev-parse HEAD == lock SHA`, disables credential persistence, verifies the fetched `manifest.sha256`, and runs with read-only repository permissions. Fork PRs fail closed because the secret is unavailable; they do not silently skip the gate. Credential smoke tests prove that the AIM-held credential cannot read AIM Data and the backend-held credential cannot read the backend.

### 5.2 AIM Data gate

Replace the deleted workflow with `.github/workflows/preview-contract-cross-repo.yml`. It:

1. Validates `preview-contract-backend.lock.json` and checks out backend at `backend_sha`.
2. Verifies the backend corpus manifest digest equals the lock's `manifest_sha256`.
3. Runs schema-coverage completeness against each repository's own models, then runs the corpus once through backend models/serializers and once through AIM models/serializers, including `LocalCandidate` and request construction/acceptance adapters.
4. Compares expected raw bytes, cross-runner raw bytes, exact rejection types and custom error codes.
5. Runs the repointed Node verifier against the fetched corpus.

It does not import backend runtime modules into AIM Data. The two runners execute in separate processes/environments and exchange only synthetic corpus inputs and output bytes/digests.

### 5.3 Backend reverse gate

Add `.github/workflows/preview-contract-cross-repo.yml` in the backend. It:

1. Validates `preview-contract-aim-data.lock.json` and checks out AIM Data at `aim_data_sha`.
2. Reads AIM Data's `preview-contract-backend.lock.json` and requires its `backend_sha` to equal the backend PR's declared immutable `contract_anchor_sha`, and its `manifest_sha256` to equal the backend's exact `manifest.sha256`.
3. Checks out backend history with `fetch-depth: 0` (an explicit fetch of the anchor commit is an equivalent implementation), requires `contract_anchor_sha` to be an ancestor of the tested backend commit, and requires no contract path to differ between the anchor tree and tested tree. The exact included paths are backend `app/schemas/listing_preview.py`, `app/schemas/dataset_commitment.py`, `app/utils/preview_signing.py`, `app/utils/dataset_commitment.py` and `tests/fixtures/preview/cross_repo_contract/v1/`, and AIM Data `app/models/preview_disclosure_schemas.py`, `app/models/dataset_commitment_schemas.py`, `app/services/preview_signing_service.py` and `app/services/dataset_merkle_service.py`. The lock files and `.github/workflows/preview-contract-cross-repo.yml` are explicitly excluded. Thus the follow-up commit may change only the reverse pin/workflow evidence, not the wire after AIM reviewed it.
4. Runs schema-coverage completeness against each repository's own models, then runs the same backend and AIM runners and asserts the same values, bytes, error types and custom error codes.

This makes a backend contract PR red before merge until the matching AIM Data change is merged and pinned. A digest-only coincidence cannot pass: both the immutable source SHA and manifest digest must agree, and both real implementations execute.

### 5.4 Enforcement contract

Both repositories' `main` branches are protected and require the exact job-name status check **`Preview contract cross-repo`**. Protection includes administrators with no bypass actor or bypass allowance; force pushes are disabled. Backend contract PRs use a merge commit only: squash and rebase merges are forbidden for this path because they can break `git merge-base --is-ancestor A main`; the merge commit preserves anchor `A` in `main` ancestry. The open anchor branch is retained until that merge.

Bootstrap is explicit. The first PR introduces the `pull_request` workflow and runs `Preview contract cross-repo` successfully once. Before that PR merges, Max performs the gated GitHub-administrator step in each repository: read the observed check context, update default-branch protection to require that exact check with administrators included and no bypass or force push, and read the protection back through the GitHub API. Only then may the first PR merge. A disposable failing-mutation PR must be shown unmergeable, including for an administrator, and its evidence includes the failing job URL and API output naming the required check. Protection creation or modification is a Max-gated provider mutation; Gate 2 may prepare exact commands but may not perform it without that authorization.

### 5.5 Lock-transition policy

The initial Gate 2 installation is the only non-wire-change transition. After installation, AIM Data's `backend_sha` advances only to a reviewed immutable backend contract anchor, and the backend's `aim_data_sha` advances only in the single reverse-pin follow-up naming the merged AIM Data commit for that anchor. Unrelated refactors, routine dependency changes and standalone pin-only PRs may not advance either pin. Both workflows classify lock-file diffs against the merge base and fail a SHA change unless CI can identify one of those transitions and its paired anchor/reverse-pin evidence; unchanged `manifest_sha256` does not excuse a move. A same-manifest pin bump to a non-anchor commit therefore fails even when both runners pass.

## 6. Deletions and replacement

Gate 2 deletes from AIM Data, in the same PR that adds the replacement gate:

- `.github/workflows/preview-contract-parity.yml` — the self-only workflow.
- `scripts/check_preview_fixture_parity.py` and `tests/test_preview_fixture_parity.py` — the static local digest/copy check.
- `tests/fixtures/preview-fixture-manifest.json` — the AIM-owned manifest used by that check.
- `tests/preview_differential_corpus.py`, `tests/fixtures/aim_preview_differential_v1.json` and `tests/fixtures/aim_preview_differential_v1.sha256` — AIM code generating AIM expected bytes; the Node checker is repointed to backend-owned vectors.
- `tests/fixtures/aim_preview_requests_v1.json`, `tests/fixtures/aim_preview_signing_v1.json` and `tests/fixtures/aim_preview_signing_requests_v1.sha256` — duplicate request/preimage goldens. Exact-byte tests that use them (`aim-data/tests/test_preview_signing_service.py:129-133,567-568`) move to the fetched corpus; ordinary model unit tests use factories and remain network-free.

Every executable consumer is closed in the same AIM Data PR. `scripts/build_preview_producer_evidence.py:499-501` replaces `fixture_manifest_sha256` with the verified backend corpus manifest digest (or removes the field); `tests/run_preview_producer_synthetic.py:25-38` remains runnable against that changed builder; and `tests/test_preview_signing_service.py:593-618` removes or rewrites `test_pinned_differential_corpus_python_and_node` against the fetched backend corpus. `tests/preview_differential_check.cjs` is repointed entirely to the fetched backend corpus and has no AIM-generated expected-byte input.

The broader `aim_dataset_*`, policy, package and manifest-budget fixtures remain because they drive producer-local dataset/package behavior, not because they prove cross-repository parity. They are excluded from the new digest manifest unless a complete nested request vector embeds their relevant value. No old parity job or copied preview request/signing golden remains alongside the new gate.

Gate 2 records the deletion proof item by item: the workflow has no second checkout; the checker and its test compare/hash AIM-local paths; the AIM differential generator computes expected bytes from AIM's serializer (`aim-data/tests/preview_differential_corpus.py:29-76`) and the Node program only checks that generated local corpus; the request/signing JSON and checksum are read only by AIM tests (`aim-data/tests/test_preview_signing_service.py:129-133,567-568`). Therefore none can see a backend-only optional field. Historical reports may retain their old evidence links, but no executable self-check remains. An executable-path `git grep` for every deleted file and module name must return no hits; immutable historical reports may be searched separately but cannot be executable inputs.

## 7. How a wire change lands

1. Create paired backend and AIM Data PR branches from current `main`; write the intended compatibility rule and vectors first.
2. On the backend branch, change the contract/model/serializer if required, update the backend-owned corpus, review the raw byte diff, and commit immutable contract anchor `A`. Push `A`; do not merge, amend, rebase or delete it.
3. On the AIM Data branch, implement acceptance/serialization compatibility, port any shared validation, set `preview-contract-backend.lock.json.backend_sha=A` and copy the verified manifest digest. AIM CI checks out `A` and must pass. Merge AIM Data first as commit `B`.
4. On the same backend PR, add one follow-up commit that sets `preview-contract-aim-data.lock.json.aim_data_sha=B` and `contract_anchor_sha=A`. The reverse gate proves AIM's lock names `A`, proves the backend contract tree has not changed since `A`, and runs both implementations.
5. Merge backend with `A` preserved as an ancestor. Confirm both `main` workflow runs pass and record `A`, `B`, the backend merge SHA, manifest digest and job URLs in the PRs and `aim-data.md` history.

Compatibility is mandatory during the interval after step 3 and before step 5: AIM Data `main` must still accept/emit the old backend-main form. If that is impossible, the wire change needs an explicit versioned dual-read/old-write migration design and cannot use this simple sequence.

## 8. Chunk plan

Smallest safe plan: **two implementation chunks / two PRs**, with the backend PR held open across both.

| Chunk | Repository | Content | Merge order |
|---|---|---|---|
| A | `aim-data` (paired with unmerged backend anchor) | Port the three validation gaps; lifecycle/error-type tests; new lock and cross-repo workflow; delete old workflow/checks/copied goldens; repoint Node verifier; update `aim-data.md`. | First, only after CI passes against backend anchor `A`. |
| B | `ai-market-backend` | Backend-owned corpus and manifest; preserve legacy profile omission in withdrawal; backend lock and reverse workflow; any future wire change; final pin-only commit naming merged AIM `B`. | Second, preserving anchor `A`. |

The initial S1732 implementation changes no wire field; it codifies the current compatible contract and closes the identified validation/test drift. Future field changes follow the same two chunks.

## 9. Acceptance criteria

1. Both locks reject malformed/non-40-hex SHAs, floating refs, absent secrets and a checked-out SHA different from the lock; backend lock validation requires exactly `aim_data_sha`, `contract_anchor_sha` and `manifest_sha256`.
2. There is exactly one authoritative cross-repo corpus, under backend `tests/fixtures/preview/cross_repo_contract/v1/`; every valid vector has exact `.bin` bytes, length and SHA-256, and `manifest.sha256` verifies.
3. Both workflows execute both repositories' real models and serializers in isolated processes and byte-compare legacy, v1, v2, complete request and nested envelope vectors.
4. Backend allocation is accepted byte-for-byte by AIM `LocalCandidate`; AIM request output is accepted and reserialized byte-for-byte by backend `PreviewDisclosureRequest`.
5. Unknown fields reject at every nesting level; unknown literals assert exact `literal_error`, not a base exception; every rejection asserts `expected_error_type` and every custom-validator rejection independently asserts `expected_error_code`; rejection vectors have no expected byte file. Changing one custom semantic code to another while both remain Pydantic `value_error` fails each runner.
6. AIM Data contains backend-equivalent recursive binary refusal, complete nine-member package identity and per-proof sampled-leaf digest enforcement, with positive and negative vectors.
7. Withdraw, refresh and supersession tests cover legacy, v1 and v2: legacy wire omission remains omitted; explicit v1/v2 remains unchanged.
8. The files in §6 are absent. The deletion record covers every removed executable/fixture class and demonstrates why it could not see a backend-only change: single checkout, local-file-as-both-operands, AIM-generated expected bytes, or AIM-only consumers. It cites the current lines in §2 and §6. `build_preview_producer_evidence.py`, `run_preview_producer_synthetic.py`, the rewritten signing-service test and the Node checker run successfully, and an executable-path `git grep` for every deleted name returns no hits.
9. **S1732 mutation proof:** use two disposable backend anchors, each adding an optional binding field with omit-when-`None` and no AIM model/serializer change. For `M1`, add its v2 input/expected bytes; for `M2`, deliberately add no vector. In both cases (a) an AIM branch that changes only `backend_sha` to the anchor fails its gate, by acceptance/bytes for `M1` and by the fetched backend model's schema-coverage completeness for `M2`; and (b) the backend branch fails its reverse gate before the pin matches and, after a diagnostic pin-only update, by acceptance/bytes for `M1` and by backend schema-coverage completeness for `M2`. Preserve both repositories' failing job URLs/logs and exact mutation commits for both cases, then discard the branches. Both CI directions must be observed failing—unit-only simulation is insufficient.
10. Each repository's coverage checker derives the named model fields from that repository, fails any field with no accept vector, fails any optional field with no omission vector, and fails any `Literal`/enum value with no accept vector.
11. Lock-diff classification accepts only initial installation, AIM advancement to a reviewed backend anchor, or the backend's single reverse-pin follow-up; a same-manifest pin-only bump to a non-anchor commit fails.
12. Both `main` branches require the exact `Preview contract cross-repo` check with administrators included, no bypass and no force push. API evidence names the check, and a disposable PR carrying a failing mutation is unmergeable by an administrator. The backend merge commit preserves anchor ancestry, and the ancestor check succeeds with complete/fetched history.
13. The two target-only credential smoke tests fail to read their holder repositories and succeed only against their target repositories; fork `pull_request` jobs fail closed, and neither workflow uses `pull_request_target`.
14. With the matching AIM change and pins applied, both main-branch gates pass; backend anchor is an ancestor of backend main; neither repository's main was red between merges.
15. `aim-data.md` contains the step-by-step procedure from §7, credential names/scopes, lock-transition rules, protected-check bootstrap, rollback and evidence fields; `INDEX.md` metadata is refreshed if its verification date or purpose changes.
16. Gate 3 review is unanimous GLM, DeepSeek and Gemini because this gate protects a signing path.

## 10. Risks and rollback

- **Circular pins / rewritten anchor.** Exact mutual tip pins are impossible without a cycle. The preserved backend anchor plus one pin-only backend follow-up breaks the cycle. CI forbids contract-tree drift after the anchor. If `A` is rewritten, AIM immediately fails checkout and the pair must restart with a new anchor; no exception or floating fallback.
- **Secret exposure or excess scope.** Separate target-only read-only deploy keys, `persist-credentials:false`, no shell tracing, no artifact containing checkout configuration. Revoke/rotate the affected Infisical/GitHub key on any suspected disclosure; its direction fails closed while unavailable without coupling the other credential.
- **False confidence from generated bytes.** CI never blesses. Review shows raw byte/digest changes, and two independently loaded implementations must reproduce them.
- **Longer paired landing.** The backend PR remains red/held until AIM merges. This is intentional: the dangerous side cannot land first. AIM's compatibility requirement keeps both mains green.
- **Rollback.** Before either merge, close both PRs and revoke any newly installed credential. After AIM-only merge, revert the AIM merge to restore its prior contract and workflow; backend main is unchanged. After both merges, revert backend first only if AIM remains backward-compatible, then revert AIM. Never delete the authoritative corpus or loosen a pin to make rollback green. A wire rollback that is not backward-compatible is a new paired wire change with new vectors and pins.

## 11. Non-goals

- No shared contract package; Max's decision is pinned cross-repo golden vectors first. A package is a later separately approved design only if this gate proves insufficient.
- No new or changed wire field, literal, profile, serializer rule, public API or database shape in S1732 itself.
- No new service, bot, repository or floating compatibility broker.
- No customer-data access or carrier. All vectors are synthetic metadata; ai.market never receives raw data (CORE S1).
- No deployment, feature enablement, production secret value, seller action or provider mutation.
