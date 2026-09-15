# S1717 Gate 2 — Data verification platform key distribution

**Status:** AUTHORED_PENDING_REVIEW; implementation specification, no deployment approval or live acceptance claim.
**Binding authority:** [Gate 1](BQ-DATA-VERIFICATION-PLATFORM-KEY-DISTRIBUTION-S1717-GATE1.md), APPROVED 2026-09-15; all §§1–7 apply unchanged.
**Runbooks base:** `e1009593160a98449724ccf20b8a2520d453c0e4`; branch `spec/bq-data-verification-platform-key-distribution-s1717-gate2`.
**Backend source pin:** `ai-market-backend@2846e6def5e734980fcc3a48ffab5fd976f28b3e`, `/Users/max/Projects/ai-market/ai-market-backend`.
**AIM Data source pin:** `aim-data@51e2740f6972c008626e186d8b265601c58eca32`, `/Users/max/Projects/ai-market/aim-data`.
Source citations below were checked with `git show <pin>:<path>`; line numbers refer to those pins, not working trees or deployed code.
Operational references: [backend](../ai-market-backend.md), [release process](../aim-data-release-process.md), [seller journey](../data-verification-seller-journey.md), at the runbooks base above.

## 1. Dependency, scope and review gates

Implement A, obtain its Gate 3 approval, merge and verify its production deployment before B is released; B development may use A's reviewed contract.
Review B before merge/promotion; C consumes the approved A/B SHAs and release packet, then proceeds only under release/deployment authority.
Gate 3 requires independent GLM + DeepSeek approval of the exact candidate for **each chunk**; CC waived, builder MP excluded from voting.
Every MP brief below includes Gate 1 and this spec, source/base pins, exact allowed files, test commands, AC evidence, failures/skips and stop conditions.
Each review packet names candidate SHA/checkout/diff, reviewer model/verdict/evidence references, available tools and finite review turn budget; changed candidates require fresh review.
Keep authenticated install-signed delivery only: no public key route, sign-in enrichment, bootstrap, key file/cache, new gate, connector or payment contract.
No private-key export, per-install injection, customer allowlist, signing-scheme change or customer-to-cloud manifest change; install and commitment keys retain their roles.
The intentional wire break has no old-client compatibility promise; signed `spec_version` and existing signed payload remain unchanged.

## 2. Chunk A — backend implementation

All paths in this section are relative to the backend pin; new symbols/files are explicitly designated.

| Exact file | Symbols and required change |
| --- | --- |
| `app/schemas/data_verification.py` | Add `PlatformKey(StrictModel)` and `ScanSpecIssueResponse(StrictModel)` using `StrictModel` at :109–110; preserve `SignedScanSpec` at :347–351. |
| `app/services/data_verification_signing.py` | Extend `DataVerificationSigningService` (:55–75): new immutable `SigningSelection` and `effective_selection` expose concrete `(key_id, key_version, algorithm)`; `sign` consumes that same selection. |
| `app/services/kms_service.py` | `get_signing_public_key(*, key_version="1")` mirrors `get_encryption_public_key` (:255); extend `sign_data` with the same optional version, passed to `_get_key_version_path`. Preserve existing callers' version-1 default. |
| `app/services/data_verification_service.py` | `issue_scan_spec` (:745 onward) returns the envelope on first issue and cached replay; add `PlatformVerificationKeyUnavailable` and a pair-validation/assembly helper `build_scan_spec_issue_response`. |
| `app/api/v1/endpoints/data_verification.py` | `create_scan_spec` (:148–189) changes response model/type to `ScanSpecIssueResponse`, still HTTP 201; map the new key failure to the fixed 503 after existing payment cleanup. |
| `app/models/data_verification.py` | `VerificationEpoch` adds nullable `key_id = Column(String(128))`, `key_version = Column(Text)` beside `signed_spec_payload` (:200); existing `signature_algorithm` (:192) records algorithm. |
| `alembic/versions/20260915_002_s1717_verification_signing_pair.py` (new) | Revision `s1717_verification_signing_pair`, `down_revision="s1716_s1294_foundation"`; add only those two nullable columns. |

`ScanSpecIssueResponse` requires exactly `wire_version`, `scan_spec`, `platform_key`; `wire_version` is literal `data-verification-scan-spec-response-v2`.
`PlatformKey` requires exactly `key_id` (nonempty string ≤128), `key_version` (string matching `^[1-9][0-9]*$`), `algorithm` (literal `RSASSA_PKCS1_V1_5_SHA256`), `pem` (ASCII SubjectPublicKeyInfo PEM for one RSA public key).
Both new models use `extra=forbid`; reject missing/extra fields, non-string IDs/versions, certificates, private keys, multiple PEM blocks and non-RSA material.
Obtain PEM only through `kms_service.get_signing_public_key(key_version=selection.key_version)`; never infer a latest version or fetch a key URL.
Derive `key_id` from the effective KMS signing ID, validate configuration agreement, and set signature-covered `payload.platform_key_id` from that selection before signing.
Use one immutable selection for payload, signing and lookup; verify the signature with the returned RSA key and check ID/algorithm equality before successful issue or persistence.
Persist `key_id`, `key_version`, existing `signature_algorithm` and unchanged inner `signed_spec_payload` together in the existing epoch transaction; do not persist PEM or an envelope inside the signed document.
On replay (:804–826), preserve all existing request/payment binding checks, load the recorded pair, fetch its recorded version and return the unchanged signed spec with the matching key.
Never re-sign, relabel an outstanding spec, create a second paid start, or use a newly selected version to repair replay; mismatched/unavailable recorded ID fails closed.
Missing historical pair metadata is an inconsistency: return the fixed 503 without guessing version 1 or backfilling from current configuration; drain issuance/replay obligations before rotation.
Migration decision: new nullable columns, not reuse of `policy_versions` JSONB; legacy rows remain unchanged and payment-only epochs may retain NULL until issuance.
The pinned migration graph has one head, `s1716_s1294_foundation`, declared in `alembic/versions/20260915_001_s1294_listing_enrichment.py:16–17`.
Use idempotent `ADD COLUMN IF NOT EXISTS`; test empty/legacy/partially applied schemas and repeated upgrade. Downgrade uses existence guards; normal operational rollback retains the additive columns and recorded pairs.
If the implementation base has another head, stop and reconcile/review the migration parent explicitly; do not silently create a second head or edit historical revisions.
Configuration/KMS/PEM/pair failure returns HTTP 503, `{"detail":"platform verification key is unavailable"}`; no raw exception, validation input or provider body escapes.
Retain `authorize` and `fail_our_fault` behavior: new pre-persistence failures use existing authorized-payment cleanup; replay failures must not void issued work or repeat financial operations.
Feature-off remains HTTP 404, `{"detail":"data verification is disabled"}`, before KMS; quote (:126–145) makes zero public-key calls even if lookup would fail.
Sanitize exactly the existing raw-provider logs at `kms_service.py:249` (`get_signing_public_key`) and :305 (`sign_data`) to fixed reason plus exception class; do not broaden into unrelated logging cleanup.

### A tests, commands and MP brief

Extend existing `tests/test_data_verification_control_plane.py` (issue/signing/gating), `tests/test_data_verification_contract.py` (strict models), `tests/test_data_verification_payment.py` (cached issue/replay/cleanup) and `tests/test_kms_lifecycle_s1606.py` (versioned lookup/signing).
Add `tests/test_data_verification_platform_key_migration.py` for model/DDL parity, migration head, repeated/partial upgrades, NULL legacy rows and recorded-pair preservation on PostgreSQL in the existing isolated test harness.
Required rows: v2 strictness; returned PEM equals KMS PEM; signer/version/payload ID/algorithm agree; real RSA verification with returned key; invalid/non-RSA/key/KMS/configuration refuses; version switch and replay retain the original pair.
Also cover feature-off zero KMS, install/action authentication, quote zero public-key calls, pre-issue cleanup, issued replay without repeated payment, missing legacy pair, and captured success/503/provider-failure log redaction.
From backend checkout, focused command:
`rtk proxy .venv/bin/python -m pytest -q tests/test_data_verification_control_plane.py tests/test_data_verification_contract.py tests/test_data_verification_payment.py tests/test_kms_lifecycle_s1606.py tests/test_data_verification_platform_key_migration.py`
Regression command: `rtk proxy .venv/bin/python -m pytest -q tests/test_data_verification*.py tests/test_log_redaction.py`
Migration verification in an isolated test database: `rtk proxy .venv/bin/python -m alembic heads` and `rtk proxy .venv/bin/python -m alembic upgrade head` (run upgrade twice); no production DB for tests.
MP A brief: implement only the seven implementation paths and five named test files above; preserve payment/manifest/privacy invariants, provide schema before/after and AC1/AC3 evidence, then submit exact SHA to Gate 3. Skipped PostgreSQL cases are an open gate, not a pass.

## 3. Chunk B — AIM Data implementation

All application/test paths below are relative to the AIM Data pin; the sole runbooks touch belongs to the runbooks repository.

| Exact file | Symbols and required change |
| --- | --- |
| `app/services/data_verification/contract.py` | Add strict `PlatformKey`/`ScanSpecIssueResponse` with the exact A wire fields; new `select_platform_verification_key` validates delivered RSA PEM/binding or exceptional override. Preserve `parse_and_verify_scan_spec` (:154–194). |
| `app/services/data_verification_client.py` | `DataVerificationClient.start` (:152–159) returns validated v2 envelope; `__init__`/`_request` enforce configured HTTPS origin and reject redirects. Wrap JSON/model failures in fixed `DataVerificationClientError`. |
| `app/routers/data_verification.py` | `VerificationRuntime`/`build_runtime` (:82–121) stop constructing scanner or reading platform/commitment keys; retain required install signing identity/authentication. `_platform_public_key` (:50–62) becomes lazy optional override decoding. |
| `app/routers/data_verification.py` | New `_scanner_factory` closes over install identity; `start_verification` (:171–194) passes it to local `start`, instead of `runtime.scanner`. |
| `app/services/data_verification_local_service.py` | `start` and `_start_with_lease` take `scanner_factory`; at :664–671 unwrap `response.scan_spec`, preserve verification-identity check, select key and construct scanner after response arrival. |
| `app/services/data_verification/scanner.py` | `DataVerificationScanner.__init__` accepts selected RSA key; `scan` passes only the inner document and selected key to `parse_and_verify_scan_spec`, logs verification success separately from key receipt. |
| `data-verification-seller-journey.md` (runbooks) | Correct key delivery/override guidance as specified below; no frontend copy or behavior change. |

No AIM Data database/model migration, key persistence, cache, refresh loop, high-water mark or key-history service; each start uses its own response key in process memory.
`build_runtime` still loads the existing install signing keys needed for authenticated requests; “no key read” here removes scanner/platform/commitment-key bootstrap, not install authentication.
Reject bare `SignedScanSpec`, unknown wire version, missing/extra envelope/key fields and malformed JSON before scanner construction; use `extra=forbid` and literal version, without coercing key-version numbers.
For delivered-key selection require `payload.platform_key_id == platform_key.key_id` and `scan_spec.signature_algorithm == platform_key.algorithm`; compare RSA numbers when checking equivalent PEM encodings.
Read nonempty `DATA_VERIFICATION_PLATFORM_PUBLIC_KEY_PEM` only on start: preserve literal PEM, escaped-newline and base64-wrapped PEM compatibility; selected override must decode to one RSA public key.
Valid override wins over a different delivered key, is exempt from delivered ID/version binding/bookkeeping, and receives no fabricated identity; the envelope remains structurally mandatory.
Invalid override returns fixed `platform verification key is invalid`, without fallback; invalid delivered key/binding returns fixed `platform verification key is invalid`; malformed envelope returns `ai.market returned an invalid scan-spec response`.
Use existing client/local error transport; never surface raw parse inputs, traceback/provider text or scan results on refusal. Signature failure terminates the first attempt with no refresh/reissue.
Preserve hash, RSA signature, expiry, cancellation, nonce replay, source/scope checks and scan-before-verification prohibition, plus leases, recovery, report ingestion and payment lifecycle behavior.
Default origin remains `https://api.ai.market` via `AIM_DATA_AI_MARKET_URL`; validate scheme/hostname/effective port, reject userinfo/non-HTTPS, retain TLS certificate/hostname verification and force `follow_redirects=False` including injected clients.
This authenticates the configured platform origin; no literal hostname pinning, key URL, protection from a hostile platform/customer host, immediate revocation or rollback-detection promise is added.
Log source `scan_spec_response`/`operator_override`, fixed result/reason enums and existing request correlation ID; safe ID/version only for delivered keys. Log receipt and successful signature verification separately; quote logs neither key acquisition nor verification.

Chunk B's runbook touch must replace “AIM Data fetches and persists it” with “the platform signing public key is delivered with each authenticated scan spec and used in process memory”; align the obsolete failure guidance with this behavior. Explain lazy start and the exceptional PEM-only operator override: ordinary onboarding, upgrades, Compose and stable images need no value. This is a later Chunk B edit, not a second file in this Gate 2 candidate.

### B tests, commands and MP brief

Extend `tests/test_data_verification_router.py` (existing client contract tests) and `tests/test_data_verification_local_service.py` (start/lease/recovery); adapt fakes to strict envelopes/scanner factories.
Extend `tests/test_data_verification_scanner.py` for delivered/override RSA verification, binding, equivalent PEM and unchanged verifier protections; retain resolver/sanitizer/enabled-default tests as regressions.
Required rows: quote/free probe/status with absent or invalid override invoke no platform-key reader/scanner; valid v2 verifies; bare/unknown/extra/missing/malformed responses refuse before scan; ID/algorithm mismatch refuses.
Also test independent response keys across starts, no signature-failure reissue, valid override precedence without tuple metadata, invalid override without fallback, supported PEM encodings and forbidden key forms.
Cover HTTPS/userinfo/redirect refusal, existing signed auth, hash/signature/expiry/cancellation/nonce/scope/receipt/payment recovery and success/failure log redaction with hostile sentinel values.
From AIM Data checkout: `rtk proxy python -m pytest -q tests/test_data_verification_router.py tests/test_data_verification_local_service.py tests/test_data_verification_scanner.py tests/test_data_verification_resolver.py tests/test_data_verification_sanitizer.py tests/test_data_verification_enabled_default.py`
Sign-in regressions: `rtk proxy python -m pytest -q tests/test_aim_market_oauth.py tests/test_aim_market_oauth_call_inventory.py tests/test_aim_market_oauth_deployment.py tests/test_device_registration.py tests/test_trust_registration_oauth.py`.
Frontend `frontend/src/components/DataVerificationFlow.tsx` and `DataVerificationFlow.test.tsx` remain unchanged; no frontend command/copy change is required.
Runbooks touch validation: `rtk proxy python3 scripts/check.py` and `rtk git diff --check` in runbooks.
MP B brief: implement the six application files, three extended test files and one runbook touch above; provide AC2/AC3 evidence and unchanged frontend diff, submit exact candidates to Gate 3, and do not release before verified A deployment.

## 4. Chunk C — release and production acceptance

MP C brief: consume approved A/B candidates, perform the reviewed RC→stable workflow, verify defaults/deployed identities, and collect both live AC-finals with Max as the authorized seller; stop on missing deployment/paid-consent authority or failed acceptance.
Release files: `scripts/release-aim-data.sh` (`update_release_defaults`), `.github/workflows/aim-data-release.yml`, `.github/workflows/ci-release-integrity.yml`, `Dockerfile.customer`, `docker-compose.aim-data.yml`, `installers/aim-data/install.sh`, `installers/aim-data/install.ps1`.
No release machinery redesign/schema change: promotion owns the existing default-version edits; workflow at the pin triggers on `aim-data-v*`, stable Git tag pattern `aim-data-vX.Y.Z`, RC `aim-data-vX.Y.Z-rc.N`.
Through the release runbook's background execution with `/opt/homebrew/bin` on PATH, from AIM Data run `rtk proxy scripts/release-aim-data.sh rc patch`, then `rtk proxy scripts/release-aim-data.sh promote aim-data-vX.Y.Z-rc.N` with the actual reviewed RC tag (the script requires its full prefix).
Wait for RC build/smoke proof before promotion; stable performs a fresh multi-arch build, not an RC retag. Require workflow label/version proof, amd64/arm64 manifest, smoke health and release-integrity checks.
Confirm the actual workflow-derived image tag (Git prefix is stripped), stable `version` label without `-rc.`, index digest and running platform digest; do not infer image tag/digest from Git tag alone.
Confirm default Compose and both standalone installers, including scripts served by `get.ai.market`, select that stable version and resolve to the promoted digest; retain installer versions/hashes and release assets.
Backend first: merge approved A triggers Railway production auto-deploy; run `rtk proxy railway deployment list -e production -s ai-market-backend` and `rtk proxy curl -fsS https://api.ai.market/health`.
Require successful production deployment metadata with Git SHA equal to the approved merge, /health success and migration head; a healthy response alone is insufficient SHA proof. Capture these before B promotion.
AC-final uses a separate ordinary fresh stable-image install with an empty persistent volume, no extra environment/seeding/override; Max signs in, runs free probe and obtains a production quote.
AC-final-b preserves install `9c51517b`, container `aim-data-fresh-s1665`, its non-empty volume and identity: capture prior failure, upgrade in place to promoted digest, then free probe, quote and explicit paid start's successful signature verification.
Do not empty/reinitialize that existing volume to manufacture AC-final. Record the fresh install's distinct identity; neither proof substitutes for the other.
Use Max's authorized seller/source and ordinary explicit paid-start consent, preserving card setup and payment boundaries; record resulting lifecycle state, including incomplete/failed states, truthfully.

### C evidence manifest and acceptance mapping

All evidence lives under `/Users/max/koskadeux-state/s1717/`; filenames below are required outputs, not claims that they exist already.

| AC / gate | Exact evidence files and contents |
| --- | --- |
| AC1 | `A-tests.txt`, `A-migration.json`: exact commands/cwd/SHA/results, envelope/KMS/signature/gating/quote/pair rows, migration head and repeated/partial upgrade results. |
| AC2 | `B-tests.txt`: lazy quote/start, strict envelope, response/override binding, TLS and unchanged verifier protections with per-test outcomes. |
| AC3 | `regressions.txt`, `log-redaction.json`: backend/AIM Data/sign-in/payment/receipt regressions and sentinel assertions on all new success/failure surfaces including backend 503 and the two sanitized KMS logs. |
| AC4 | `gate1-review-refs.json`: approved exact Gate 1 SHA and GLM/DeepSeek verdict/model/evidence references, CC waiver, MP exclusion; do not relabel Gate 3 as AC4. |
| Gate 3 A/B/C | `gate3-A.json`, `gate3-B.json`, `gate3-C.json`: exact candidates/diffs, independent GLM/DeepSeek approvals, model IDs, packet/evidence references and authority to proceed. |
| Release dependency | `backend-deployment.json`, `backend-health.json`, `release.json`, `installer-defaults.json`: Railway deployment/SHA/head/health, A-before-B timestamps, B source SHA, RC/stable Git tags, workflow runs, labels, image digests and installer/default checks. |
| AC-final | `ac-final-fresh.json`, `ac-final-ui.png`, `ac-final-api.json`: empty-volume-before-use proof, new identity, stable/runtime digest, override absence as boolean, sign-in/free probe/quote UI/API outcomes and production quote reference. |
| AC-final-b | `ac-final-b-before.json`, `ac-final-b-upgrade.json`, `ac-final-b-ui.png`, `ac-final-b-api.json`, `ac-final-b-signature.json`: prior failure, same identity/non-empty volume before/after, digest, probe/quote/start references, consent and signature success with source `scan_spec_response`, resulting payment/lifecycle state. |
| Final index | `manifest.json`: timestamps, file hashes, candidate/deployed identities, AC pass/fail/not-run and limitations; `rollback.json` if rollback is exercised. |

Redact before capture/export: no PEM, signatures, response bodies containing those fields, auth headers/tokens, install secrets, credentials, customer locators or raw provider exceptions; screenshots exclude card/secret/source data.
Use allowlisted API summaries, opaque quote/start references, safe key ID/version, fixed reasons and correlation IDs; preserve meaningful outcomes without dumping environment, volumes or full Docker inspect output.
Unit fixtures may assert KMS PEM equality in memory; exported evidence contains the assertion result, not key material. AC-final quote success does not prove signature verification; AC-final-b must capture that separately.

## 5. Rollback, risks and delivery boundary

Per Gate 1 §6, disable verification before reverting incompatible backend/client code; retain existing expiry/disable emergency controls and parent state/payment preservation rules.
Preserve customer volume, install identity, commitment/install keys, epoch pairs, pending payments and reconciliation; do not drop the additive columns as routine rollback or relabel outstanding specs.
Coordinate rotation only after outstanding issuance/replay obligations drain; an older broken image is rollback containment, never acceptance. No immediate revocation guarantee is introduced.
Risks remain the accepted wire incompatibility, signer/key mispairing during rotation/replay and host/platform compromise; migration NULL handling and coordinated rollout must be proven, not assumed.
This Gate 2 delivery changes exactly this file in one pushed commit; validate with `rtk proxy python3 scripts/check.py` and `rtk git diff --check`, then report exact file, commit/branch, checks, risks and Gate 1 scope adherence.
