# S1717 Gate 1 — Data verification platform key distribution (R2)

**Status:** R2 fold candidate; independent approval pending. No implementation or deployment approval.
**Authority:** Max decision event `8fa786ba-61cb-4185-913a-7ece3d7d3880`; Mars binding R1 → R2 fold, 2026-09-15.
**Base:** runbooks `7a918d40eef541b787ebd18ecbf5570ec4563184`; R1 `91c1aba0ae75bca9414009956c4ff8d30c463c1e`.
**Review panel:** GLM + DeepSeek must approve the exact candidate; CC waived; builder MP excluded.
**Source trace:** `aim-data@51e2740f6972c008626e186d8b265601c58eca32` and `ai-market-backend@2846e6def5e734980fcc3a48ffab5fd976f28b3e`; all code citations below were re-read with `git show` at these SHAs, not inferred from working trees or production.

**R1 fold log:** Adopts DeepSeek BETTER + SIMPLER and GLM SIMPLER's removal of sign-in enrichment. Scan-spec delivery removes the public route and its abuse problem (GLM 3/4; DeepSeek F4/F6); lazy construction and process memory remove bootstrap/storage/refresh machinery (DeepSeek SIMPLER). Explicit key binding and the PEM-only override exception discharge GLM 2. Restoring the journey file to base leaves one candidate artifact (DeepSeek F1; GLM 1). Source pins discharge DeepSeek F3; the evidence limits and reproducible packet requirements address DeepSeek F2/GLM 1 without claiming live proof. AC-final-b discharges DeepSeek F5. The strict response envelope makes the adopted wire change implementable.

## 1. Problem, scope, and evidence

Ordinary installs are reported to fail before verification because the platform public key is absent.
Static cause verified: AIM Data `app/routers/data_verification.py:50-62` reads the override and refuses when unset; `:82-120` constructs the scanner eagerly.
The quote handler at `:156-168` only needs `runtime.client`, yet reaches that key read; start is at `:171-194`.
The live production failure was supplied by the orchestrator and was **not re-run in this documentation fold**; deployed identities and live outcomes remain unverified here.
Scope is authenticated scan-spec key delivery, lazy verification, process-memory key identity checks, and the later stable release.
No new public endpoint, sign-in/registration enrichment, or persisted platform key file is part of this design.
Compose/installer PEM injection and per-install seeding are rejected because the product must work for every ordinary customer install.
No signing scheme, private-key export, customer allowlist, new feature gate, connector, payment contract, or customer-to-cloud manifest change is authorized.
Existing install signing keys and customer-held commitment keys retain their separate roles.

Binding parent references, verified at the runbooks base:

- `specs/BQ-DATA-VERIFICATION-S1590-GATE1.md:36-64`: signed specs and trust anchors; `:108-155`: exhaustive manifest and commitment-key boundary.
- `specs/BQ-DATA-VERIFICATION-S1590-GATE2.md:46`, `:92`: KMS-signed, expiring, nonce-bound scan spec; delivery is unspecified there.
- `specs/BQ-DATA-VERIFICATION-S1590-GENERAL-AVAILABILITY-AMENDMENT.md:13-27`, `:108-115`: all-seller availability, accepted agent-tamper residual, and unchanged privacy/payment invariants.

## 2. Backend response contract

Keep authenticated, install-signed `POST /api/v1/data-verification/scan-spec`, HTTP 201.
The current route is backend `app/api/v1/endpoints/data_verification.py:148-189`; retain its feature gate, action authentication, consent, payment, and idempotency checks.
Replace the bare `SignedScanSpec` response with a strict `ScanSpecIssueResponse` envelope:

```json
{
  "wire_version": "data-verification-scan-spec-response-v2",
  "scan_spec": {"payload": "<existing ScanSpecPayload object>", "spec_hash": "...", "signature_algorithm": "RSASSA_PKCS1_V1_5_SHA256", "spec_signature": "..."},
  "platform_key": {"key_id": "platform-signing-key", "key_version": "1", "algorithm": "RSASSA_PKCS1_V1_5_SHA256", "pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"}
}
```

The payload placeholder above denotes the existing object, not a string on the wire.
Both envelope and `PlatformKey` reject extra fields; `wire_version` is the literal shown, and all three envelope fields are required.
`SignedScanSpec` remains unchanged inside `scan_spec`; do not insert sibling key fields into it or its signed payload.
Backend strictness is at `app/schemas/data_verification.py:109-110`, `:347-351`; AIM Data strictness is at `app/services/data_verification/contract.py:58-59`, `:147-151`.
**Compatibility decision:** this intentionally replaces the old response shape. Every current ordinary install fails before this call, so Mars accepts a coordinated wire-shape change; old clients are not promised compatibility.
The outer wire version changes; signed `spec_version` and customer-to-cloud manifest versions do not.
Deploy the compatible backend before promoting AIM Data; a bare legacy response or unknown envelope version is rejected by the new client.

| Key field | Contract |
| --- | --- |
| `key_id` | Nonempty signing ID, at most 128 characters; equal to the effective signer ID and signed payload ID. |
| `key_version` | Positive decimal string matching `^[1-9][0-9]*$`; the actual KMS CryptoKeyVersion used for this signature. |
| `algorithm` | Literal `RSASSA_PKCS1_V1_5_SHA256`; equal to `scan_spec.signature_algorithm`. |
| `pem` | ASCII SubjectPublicKeyInfo PEM for one RSA public key; no certificate or private key. |

Obtain PEM exclusively from `kms_service.get_signing_public_key()` (`app/services/kms_service.py:238-252`).
Signer ID/algorithm and canonical signing are at `app/services/data_verification_signing.py:55-75`.
**Payload check:** backend `ScanSpecPayload` already carries `platform_key_id` at `app/schemas/data_verification.py:328`; AIM Data carries it at `app/services/data_verification/contract.py:131`.
No new payload field is needed: signing serializes the entire payload, so this existing ID is signature-covered. Populate it from the same effective signer selection.
Signing and public-key lookup currently use version `1` (`app/services/kms_service.py:197-225`, `:238-246`, `:275-287`).
Share the concrete ID/version/algorithm selection between signing and delivery; never label a PEM using an independently selected latest version.
Return a key matching the particular spec, including idempotent responses; never pair an outstanding spec with a newly rotated, unrelated key.
Validate the pair before successful issue; preserve existing payment failure handling and never create another paid start to repair key delivery.
Configuration/KMS/key inconsistency fails closed with HTTP 503 and `{"detail":"platform verification key is unavailable"}`; expose no provider detail.
Feature-off remains HTTP 404, `{"detail":"data verification is disabled"}`, before KMS work (`app/api/v1/endpoints/data_verification.py:56-58`).
Quote stays unchanged and never calls KMS public-key lookup (`app/api/v1/endpoints/data_verification.py:126-145`).

## 3. AIM Data integration and override

`build_runtime` constructs the authenticated client/install context without reading or parsing any platform key, including an override.
Remove eager scanner construction from `app/routers/data_verification.py:114-120`; quote/free probe and status need no verifier.
At start, pass a scanner factory or equivalent lazy dependency through `start_verification` into the local start service.
Change `DataVerificationClient.start` (`app/services/data_verification_client.py:152-159`) to return validated `ScanSpecIssueResponse`, not `SignedScanSpec.model_validate(response.json())`.
In `app/services/data_verification_local_service.py:664-671`, unwrap `response.scan_spec`, select the response key or override, and construct the scanner only then; preserve the existing verification-identity check.
Pass only the inner signed-spec document and the selected RSA key to `parse_and_verify_scan_spec` (`app/services/data_verification/contract.py:154-194`).
Keep canonical hash, RSA signature, freshness, cancellation, nonce replay, source/scope binding, and scan-before-verification prohibitions unchanged.
Parsing/key errors use fixed display-safe refusals through the existing client/local error transport; never silently start scanning.

For platform-delivered keys, require `spec.payload.platform_key_id == platform_key.key_id` and `spec.signature_algorithm == platform_key.algorithm` before acceptance.
Maintain an in-memory, per-process cache keyed by `(origin, key_id, key_version, algorithm)`; store validated RSA public numbers with that tuple.
Insertion/comparison must be atomic across concurrent starts. The same tuple with different RSA numbers is an integrity error; reject without replacing it.
Equivalent PEM encodings with identical RSA numbers are not a key change. A distinct tuple is validated independently.
Every issued spec carries its key; verification uses that response's tuple, not the most recently seen cache entry.
No refresh loop or signature-triggered reissue is needed. A signature failure terminates closed on the first verification attempt.
Restart clears this cache; it has no key history, version high-water mark, or cross-process rollback-detection promise.

`DATA_VERIFICATION_PLATFORM_PUBLIC_KEY_PEM` remains an exceptional PEM-only operator override: when nonempty it wins for start verification.
Preserve existing literal/escaped-newline/base64-wrapped PEM input compatibility (`app/routers/data_verification.py:50-62`); validate the decoded value as one RSA public key.
The override is exempt from platform ID/version tuple bookkeeping and delivered-key ID binding; do not invent IDs or versions for it.
Supported scan-spec algorithm and all signature/hash/expiry/nonce/scope checks still apply. The envelope remains structurally required, but its key does not replace the override.
An invalid override fails closed with `platform verification key is invalid`, without fallback to the delivered key; quote remains key-independent.
Document the variable as exceptional operator control; normal onboarding, upgrade, Compose, and the stable image require no value.

## 4. Trust and rotation

TLS certificate/hostname validation to the configured `AIM_DATA_AI_MARKET_URL` HTTPS origin binds the delivered key to ai.market.
Origin means scheme, hostname, and effective port; reject userinfo, non-HTTPS origins, and redirects for this authenticated response. Never follow a key URL from the response.
A hostile platform could sign anything anyway: this establishes platform authorship, not protection from the platform; a hostile customer host remains outside the guarantee.
Rotation switches signer and delivered key together; outstanding specs drain by expiry while retaining their matching delivered verification key.
Coordinate rotation after outstanding issuance/replay obligations drain; do not introduce a key-history service or relabel old specs.
There is no immediate revocation promise. Existing disable/expiry controls remain the emergency boundary; neither key delivery nor process memory revokes old valid signatures.

## 5. Observability and required tests

Log key source `scan_spec_response` or `operator_override`, fixed result/reason, safe key ID/version when applicable, and existing request correlation ID.
Log successful signature verification separately from key receipt; quote must not claim a key was acquired.
Never log PEM, response bodies, signatures, auth headers, tokens, install secrets, customer locators, or raw provider exceptions.
Use fixed reason enums for metrics; exceptional override logs have no fabricated identity metadata.

| Suite | Required evidence |
| --- | --- |
| Backend response | Strict v2 envelope; returned PEM equals KMS PEM; payload ID, delivered ID, signer version and algorithm agree; signature verifies with returned key. |
| Backend gating | Feature-off 404/body unchanged and zero KMS calls; existing install/action authentication still required. |
| Backend quote | Successful quote makes zero KMS public-key calls, including when key lookup would fail. |
| Backend failures/rotation | Invalid key/KMS/configuration refuses; coordinated version switch and idempotent response preserve spec/key pairing and existing payment cleanup. |
| AIM Data quote | Unset or invalid override does not trigger any key read; free probe/quote succeeds with no scanner construction. |
| AIM Data start | Client unwraps v2; start verifies with delivered key; bare/unknown-version/extra-field responses refuse before scan. |
| AIM Data binding | Signed payload ID mismatch or algorithm mismatch rejects; same tuple/different RSA numbers rejects, including concurrent starts. |
| AIM Data cache | Identical numbers accepted; different tuple and restart work from each response; no signature-failure refresh/reissue. |
| AIM Data override | Valid PEM wins over a different delivered key without ID/version bookkeeping; invalid PEM refuses without fallback; quote unaffected. |
| Regression/redaction | Existing hash, signature, expiry, nonce, scope, receipt, sign-in and payment tests pass; captured success/failure logs contain no prohibited material. |

## 6. Chunks and acceptance

**Chunk A — backend:** strict envelope/key model, shared signing selection, authenticated issue integration, failure behavior and backend tests.
**Chunk B — AIM Data:** strict client parsing, lazy scanner/verifier, response-key binding/cache, override documentation and client tests.
**Chunk C — stable release:** publish reviewed image, confirm installer/default Compose pulls its digest, and execute both AC-finals against production.
Preserve existing customer volume and install identity on upgrade; record backend deployed SHA, AIM Data source SHA, stable tag/digest, installer version, and redacted evidence.
Rollback disables verification before reverting incompatible code and preserves customer state under the parent rollback rules; an older broken image cannot satisfy acceptance.

- **AC1:** Backend envelope, KMS equality, signature-covered ID binding, feature-off and quote isolation tests pass.
- **AC2:** Lazy client integration, tuple integrity, override and unchanged verifier protections pass without a key bootstrap step.
- **AC3:** Log-redaction and regression tests pass; privacy, payment and customer-to-cloud contracts remain unchanged.
- **AC4:** GLM + DeepSeek independently approve the exact Gate 1 candidate; retain verdict/model/evidence references, CC waiver and MP exclusion.
- **AC-final:** Fresh stable-image install, empty persistent volume, no extra environment: sign-in, free probe and quote succeed against production.
  Capture UI/API results, override absence, production quote reference and exact image digest; no manual seeding or development image. This quote proof alone does not prove signature verification.
- **AC-final-b:** An existing, currently failing install upgrades in place on a non-empty volume, with no seeding or override, and completes free probe, quote AND paid start's scan-spec verification.
  Capture the prior failure, retained install identity/volume, promoted digest, quote/start references and successful signature verification with key source `scan_spec_response`.
  Use the authorized seller/source and ordinary explicit paid-start consent; preserve the existing card/payment boundary and record any resulting lifecycle state truthfully.

## 7. Review packet, verification, and risks

The candidate diff against the base must list exactly this spec; the seller-journey hunk is removed because runbooks PR #200 updated that page separately.
Reproduce with `git diff --name-status 7a918d40eef541b787ebd18ecbf5570ec4563184 <R2_SHA>` and `git show <R2_SHA>:specs/BQ-DATA-VERIFICATION-PLATFORM-KEY-DISTRIBUTION-S1717-GATE1.md`.
The next review packet must name exact SHA/checkout, sole changed file, both source pins, available tools, finite review turn budget, and builder command/results/failures/skips.
Attach `python3 scripts/check.py` and diff-check results; distinguish static source verification from the unverified live diagnosis. Do not invent missing production logs or claim the AC-finals ran.
Gate 2 pins implementation files and test commands; Gate 3 reviews implementation; Gate 4 requires both live AC-finals. This fold grants no implementation/release approval.
Risks: incompatible old clients, mispaired signer/key during rotation or replay, and host/platform compromise. Coordinated rollout, pair tests and explicit trust limits bound the design claim.
