# BQ-TEST-ENV-GCP-ISOLATION-S1658 Gate 1 design specification

**Status:** Proposed Gate 1 design; not Council-approved and not implementation or spending authority.

**Build Queue entity:** `build:bq-test-env-gcp-isolation-s1658` (requested identity; live board ownership not verified here).

**Design sources:** Max's authoring instruction, including T-2026-000765 and the S1656 handoff state and temporary approval dated 2026-09-06; the immutable source inventory in section 4. This document follows the S1590 template's numbered problem, frozen decisions, binding architecture, evidence, scope, acceptance, gate, risk, and reservation structure, with task-specific middle sections.

**Runbooks baseline:** `aidotmarket/runbooks@263984b6719fb0701c565848302566d3680c743d`, fetched `origin/main` on 2026-09-07. The requested `runbooks/money-path-test-environment.md` and `runbooks/gcp-auth.md` are repository-root files `money-path-test-environment.md` and `gcp-auth.md`, not a nested directory.

**Branch:** `spec/bq-test-env-gcp-isolation-s1658`, created directly from that baseline. Only this file may differ; specifically exclude `specs/BQ-STARLETTE-CVE-48710-FRAMEWORK-UPGRADE-S1658-GATE1.md` from the other in-flight branch. Commit and push; do not merge.

## 1. Problem

The synthetic money-path environment still shares production GCP security and billing boundaries. Max reports that `s1656-test-signing-key` and `s1656-test-encryption-key` were created inside `projects/aimarket-prod/locations/us-central1/keyRings/ai-market-trust`, that `kms-trust-agent@aimarket-prod.iam.gserviceaccount.com` received `roles/cloudkms.admin` on that ring, and that Infisical `test-env` contains a copy of the production `VERTEX_GEMINI_KEY`. This was temporarily approved on 2026-09-06, not approved as the permanent architecture.

The environment code corroborates dedicated test key names inside the shared ring and a copied Vertex key, but source comments are not live IAM or secret-value proof. The design replaces these dependencies without rotating production credentials or altering production key material. It also evaluates the host-network dependency of the frontend image build.

## 2. Frozen product and trust decisions

1. Preserve the S1656 synthetic-only, local-data, Stripe-test-only safety boundary and existing money-path acceptance journey.
2. Use a dedicated test GCP project, dedicated ring, and dedicated signer/verifier-only service account. Do not silently settle for another ring in `aimarket-prod`.
3. Use a newly issued, test-only Vertex Gemini API key and an enforced monthly request budget. A copied production key or alert-only budget cannot satisfy isolation.
4. Rotate the complete credential/configuration tuple in Infisical backend project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, environment `test-env`, path `/`, through raw v3 API calls with the sysadmin token. Never use the bare Infisical CLI for rotation or verification.
5. Prove every consuming process uses the new tuple before disabling or scheduling destruction of old test key versions. Preserve a demonstrated rollback window first.
6. The sole production IAM change is removing the temporary `roles/cloudkms.admin` member grant from the exact production ring. Preserve every other binding, condition, and key/version property.
7. CORE S3 requires unanimous **CC + GLM + DeepSeek** approval of the exact artifact for security posture and credentials. No substitute reviewer or majority vote. Infrastructure build WIP limit is one before dispatch.
8. This authoring task performs no cloud mutation, secret read/write, paid inference, implementation, review dispatch, deployment, or merge.

## 3. Binding architecture

### 3.1 Project decision

Select a new project under the existing ai.market organization `1062465481671`, with proposed ID `aimarket-test-s1658`, ring `ai-market-test-s1658`, and location `us-central1`. These names are proposed, not verified available resources. Record actual project ID/number and billing-account binding before implementation; an unavailable ID requires an explicitly recorded equivalent test-only ID.

| Option | Evidence and consequence | Decision |
| --- | --- | --- |
| Dedicated ring and SA inside `aimarket-prod` | Configurable KMS paths permit it (B1), but Vertex budget enforcement is scoped to a project and service, not a KMS ring or individual key (G1). A cap there could pause production Vertex. Production project-level inherited access remains a shared boundary. | Reject for this combined KMS and Vertex isolation task. |
| Dedicated project, ring and identities | KMS paths already accept project/location/ring variables (B1). A test project permits a test-only Vertex service cap (G1), separate billing attribution, and an independently inspected IAM boundary. Provisioning/billing authority and inherited organization policies still need verification. | Selected; extra setup is justified by the spending and credential boundary. |

Do not change the global gcloud default project. Any future provider operation must name its exact project, location, ring, key, and identity. No Gmail/OAuth/Pub/Sub migration accompanies the new project; `gcp-auth.md` documents those as independent production auth paths.

### 3.2 KMS identities and purpose separation

Create new version-1 keys in the new ring: `s1658-test-signing-key` with `RSA_SIGN_PKCS1_2048_SHA256`, and `s1658-test-encryption-key` with `RSA_DECRYPT_OAEP_2048_SHA256`. Preserve algorithm and version compatibility with B1; never export KMS private keys.

The primary runtime account is proposed as `kms-test-signer@aimarket-test-s1658.iam.gserviceaccount.com`. Grant `roles/cloudkms.signerVerifier` only on the signing CryptoKey and `roles/cloudkms.publicKeyViewer` only on the encryption CryptoKey for current readiness checks. It has no decrypt, create, destroy, IAM-write, key-administration, project-editor/owner, or production permissions. Public-key retrieval is not private-key decryption (G2).

**Compatibility consequence:** B1 initializes one client, reads both public keys, signs, and also exposes private-key decryption. `trust_channel_service.py:312` calls that decryption path. A signer/verifier-only identity cannot be claimed compatible with every existing Trust Channel operation through a secret swap alone.

The proposed implementation therefore separates the decrypt credential/client: `kms-test-decrypt@aimarket-test-s1658.iam.gserviceaccount.com`, granted only `roles/cloudkms.cryptoKeyDecrypter` and `roles/cloudkms.publicKeyViewer` on the new encryption CryptoKey. Add a test-only `GCP_KMS_DECRYPT_SERVICE_ACCOUNT_JSON` setting and explicit decrypt-client construction; this setting and split are **new design**, not existing behavior. It cannot sign, administer keys, or impersonate the signer. The signer cannot impersonate it. Both credentials remain backend-only; AIM Data receives public material only. Existing production client behavior remains unchanged when the test-only split is absent.

This separation limits each principal's privileges; it does not isolate the two capabilities from a compromised backend process holding both credentials. Council must explicitly assess that residual. If the split is rejected, return to Gate 1; do not grant decrypt/admin to the requested signer account to make tests pass. Provisioning uses a separate authorized operator identity which is never injected into containers.

### 3.3 Vertex credential boundary

Issue a new authorization key for Vertex AI in the dedicated test project, compatible with the existing `genai.Client(vertexai=True, api_key=...)` contract. Follow the local runbook's Vertex Express `AQ.` requirement; do not substitute OAuth/ADC, an AI Studio/Developer API key, or a production copy. Prefix is only a format check: prove actual authentication, resource ownership, and billing attribution (R2, B2, G3).

Restrict the key to the Vertex AI API and the supported application restrictions appropriate to the actual egress. If a backing Vertex service account is required, it must be test-only and separate from KMS identities. Record provider-returned key ID, parent project, restrictions and backing identity without the key string. Provider compatibility/restriction availability remains a preflight gate, not an assumed fact.

## 4. Source evidence and consequences

All Git observations below were read without modifying the environment or managed application repositories. Line references apply to the full immutable SHA specified in each row. `R` means runbooks at the baseline above; `E` means environment at `5899f82027e40118f9bf9ab389dd9b923fb078d9`.

| ID | Pinned source | Verified fact / limit |
| --- | --- | --- |
| R1 | R:`money-path-test-environment.md`, sections B-D, E, G-H | Placement is `/Users/max/Projects/ai-market/money-path-test-environment-s1656`; local Compose topology, backend Infisical project, no test-env Railway sync, lifecycle and acceptance evidence. It describes older environment SHA `6d9b434ab42faff1218eb59c78e171dd58d5cc64`, not the current checkout. |
| R2 | R:`gcp-auth.md:34-57,103-130` | Independent Vertex API-key and KMS SA credentials; canonical prod project/org/account; Express key requirement and KMS algorithms. Its example key resource paths use `global`, conflicting with this task's `us-central1` temporary ring. Never infer the mutation location from that example. |
| R3 | R:`infisical-secrets.md:16-20,74-105,170-208,235-240` | Self-hosted raw v3 API; sysadmin-token is refreshed Universal-Auth JWT; JSON newline CLI hazard; explicit project and uppercase names required. Production native sync is documented; older manual-sync paragraphs also remain. Test-env must remain outside that sync. |
| E1 | E:`compose.yaml:35-49`; `compose.aim-data.override.yaml:21`; `bin/preflight:165-169` | Backend receives GCP tuple and Vertex key; AIM Data receives platform public PEM. Preflight fixes old key names and `ai-market-trust`, so configuration-only migration is insufficient. |
| E2 | E:`bin/up:18-48,72-85,93-96,115-123`; `bin/mint-teardown-token:549-574` | Existing up uses authenticated CLI injection; required-name loop omits new GCP names but Compose requires them. Backend starts before frontend build. Existing raw API writer supplies workspace/environment/path/type and POST/PATCH. |
| E3 | E:`compose.yaml:95-145,238-242`; `versions.env:1-8` | Frontend build uses `network: host`, public localhost API build arg, and runtime `API_URL=http://backend:8000`; browser-runner host networking is independent. Managed source pins are those below. |
| B1 | `ai-market-backend@662a5d38e5a555a83842a212ea1046cd2515d549:app/core/config.py:546-561`; `app/core/gcp_credentials.py:65-140`; `app/services/kms_service.py:65-99,117-165,214-236,275-343`; `app/services/trust_channel_service.py:312` | Config builds exact KMS paths; credentials initialize ADC with per-process mode-0600 temp file and may prefer existing ADC; shared KMS client caches readiness, validates both algorithms, defaults to version 1, signs and decrypts. |
| B2 | Same backend SHA:`app/core/config.py:369`; `app/core/llm.py:167-198`; `app/services/data_verification_narrative_service.py:14,28`; `app/api/v1/endpoints/allai.py:754` | Canonical SecretStr Vertex key is used by shared Gemini client construction and other backend paths; completion client is cached. Narrative uses the common LLM layer. `GCP_LOCATION` is injected by E1 but a search of backend `app` found no direct use; do not use it as proof of Vertex region or billing project. |
| A1 | `aim-data@3bb318440d71b79162ef6a9ae625f1c8e30ca609:app/routers/data_verification.py:50-62` | Platform verification public key is read from process environment; literal PEM with escaped newlines or validated base64 PEM is accepted. |
| F1 | `ai-market-frontend@c845f50f1df02bd97bfc5e8f9011c78511da6699:app/page.tsx:169-171,269-275`; `lib/api.ts:3,77-99,165-169` | Homepage fetches listings, featured feed and data requests. Server API helper prefers `API_URL` over `NEXT_PUBLIC_API_URL` and uses 60-second revalidation. Line 170 concerns metric URLs, not the actual data-fetch helper; the Compose comment is incomplete. |

Provider references read on 2026-09-07 (web pages have no Git SHA; preserve dated copies/hashes in implementation evidence and revalidate before provisioning):

- G1: [Google Cloud spend cap budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps). Preview capability scopes to one project and service, supports monthly Vertex service caps, and can block new usage. Enforcement is delayed and in-flight requests still accrue charges; overages are billable. Availability in this billing account was not checked.
- G2: [Cloud KMS roles and permissions](https://docs.cloud.google.com/iam/docs/roles-permissions/cloudkms). Signer/verifier, public-key viewer and decrypter are separate roles; admin is unnecessary for runtime crypto.
- G3: [Google API key management](https://docs.cloud.google.com/docs/authentication/api-keys). Key types and supported API restrictions must match the selected Vertex endpoint; live key creation remains unverified.

## 5. Evidence honesty

The temporary IAM grant, actual old version IDs, current secret equality with production, the 2026-09-06 approval record, and T-2026-000765 are user-supplied facts, not independently retrieved provider/ticket evidence in this task. E1 comments date creation to 2026-09-04; this does not establish or contradict a later approval date. Do not label source corroboration as a live audit.

R1's backend pin is older than E's `versions.env`. The checked environment worktree was clean at E, and its origin was `git@github.com:aidotmarket/money-path-test-environment.git`. This design uses E and its source pins for consumer analysis; it makes no claim about deployed image identity or a passing live journey.

## 6. Credential and configuration manifest

| Value in Infisical test-env `/` | New source | Consumers requiring restart/reload proof |
| --- | --- | --- |
| `GCP_PROJECT_ID` | Verified dedicated project ID | Host preflight/Compose; every backend worker's settings/KMS path |
| `GCP_LOCATION`, `GCP_KMS_LOCATION` | Explicit `us-central1` KMS placement; Vertex routing remains separate | Host/Compose; backend KMS uses the latter |
| `GCP_KMS_KEYRING` | `ai-market-test-s1658` | Host preflight/Compose and backend |
| `GCP_KMS_PLATFORM_KEY_NAME`, `GCP_KMS_ENCRYPTION_KEY_NAME` | New test signing/encryption key names | Host preflight/Compose, backend readiness and crypto operations |
| `GCP_SERVICE_ACCOUNT_JSON` | Dedicated signer SA key, secret-backed transfer | Backend ADC and signing client; no inherited host ADC override |
| `GCP_KMS_DECRYPT_SERVICE_ACCOUNT_JSON` (new) | Dedicated decrypt SA key | New explicit test-only backend decrypt client |
| `DATA_VERIFICATION_PLATFORM_PUBLIC_KEY_PEM` | Public key fetched from exact new signing version | AIM Data process and actual scan-spec verification |
| `VERTEX_GEMINI_KEY` | New dedicated Vertex key | Every backend Gemini caller, including cached completion/embedding clients and narrative path; budget guard below |

No private credential enters frontend build args, browser-runner, AIM Data, Git, command arguments, logs, or evidence. Public-key DER SHA-256 fingerprints, SA email/key ID, provider API-key ID, project/ring/version paths, secret revision IDs and equality booleans are sufficient evidence. Never dump Compose configuration, whole process environments, or raw API responses containing secrets.

## 7. Hard budget contract and cost

**Proposed cost line: USD 10 per calendar month maximum admitted Vertex usage for the dedicated test environment; USD 0 authorized spend in this authoring task.** Max has been asked to confirm the amount. Until confirmed, the amount is a proposal and paid activation is blocked. KMS key-version storage/operations and any budget-guard hosting are separate costs requiring a priced estimate and authorization before build; they are not falsely included in the Vertex-only cap.

Configure a dedicated-project Vertex spend cap as a secondary provider control (G1), with no production project in its scope. A provider cap alone cannot promise an exact dollar ceiling. An alert, RPM quota, automatic billing-disable callback, or per-scan price is not a substitute for the following mandatory hard admission guard.

All test Vertex requests must traverse one credential-holding guard; backend callers receive only its internal authorization, not a usable provider key. Adapt test-mode client routing/configuration accordingly; this is proposed implementation and must cover embeddings, narrative, allAI and retries, not just paid scans. The raw `VERTEX_GEMINI_KEY` remains canonical in test-env but is injected only into the guard after migration. Preserve the existing Vertex API-key authentication at the guard-to-provider boundary.

The guard maintains a durable, transactionally serialized monthly ledger outside reset/teardown volumes. Before each provider attempt, reserve an upper bound for all billable input, output and thinking tokens, request fees and enabled features using pinned provider prices and enforced token/model limits. Admit only when settled spend plus all outstanding reservations plus the new reservation is at most the approved cap. Reject unsupported models/features, unknown pricing, missing ledger, clock/period ambiguity or unbounded cost before a provider call. Concurrency begins at one; retries require their own reservation. Timeouts retain the full reservation until positively reconciled; restart cannot free it. Usage reconciliation may refund only a proven excess reservation. Reset, key replacement, rollback and month rollover cannot erase pending liabilities.

Restrict network/credential access so no backend consumer or test operator script bypasses the guard; record attempted bypass refusal. Do not assume SDK retry behavior is bounded: account for each transmitted attempt. A leaked provider key or privileged operator bypass remains a security risk; the Google cap mitigates it but has latency. If no enforceable route and conservative price bound can be demonstrated, leave the new key disabled/unavailable to callers and report **hard cap not satisfied**. Do not relabel a soft provider threshold as a strict invoice guarantee.

## 8. Rotation transaction and raw API procedure

1. At the implementation gate, pin current Git/image identities again; prove sole infrastructure ownership. Read provider resources/IAM and the exact old configuration tuple. Preserve rollback values only in an approved secret-backed restricted record with revision IDs in redacted evidence. Never put them into this spec.
2. Provision the dedicated resources with the separate operator. Read back purposes, algorithms, enabled versions, effective IAM including inherited bindings, API key ownership/restrictions, billing attribution and budget controls. Do not mutate any production key.
3. Build the test-only client split, budget guard and revised exact-resource preflight checks against reviewed pins. New preflight must reject the production project/ring/SA and old key paths in normal mode; prevent host ADC, local `.env` or `versions.env` from overriding the approved credential tuple. Existing E preflight would reject the new ring.
4. Quiesce all test jobs, drain/reconcile in-flight paid epochs and provider calls, then stop credential consumers. Record outstanding ciphertext/signature dependencies; recreate disposable synthetic registrations/sessions after the switch instead of leaving stale trust material. No half-updated tuple may run.
5. Read `~/.config/infisical/sysadmin-token` locally in memory; authenticate only to `https://secrets.ai.market`. Follow R3's Universal-Auth refresh procedure if actually expired; never fall back to interactive/bare CLI secret access or the hosted Infisical domain.
6. Use `GET /api/v3/secrets/raw/<NAME>?workspaceId=bd272d48-c5a1-4b52-9d24-12066ae4403c&environment=test-env&secretPath=/&type=shared`; parse JSON without echoing it. PATCH existing names at `/api/v3/secrets/raw/<NAME>` with JSON `workspaceId`, `environment: test-env`, `secretPath: /`, `type: shared`, and `secretValue`; POST only when confirmed absent. Supply Bearer token in a protected in-memory request header and values in request bodies, never shell arguments. E2 provides the local raw writer precedent; do not treat every 400 as an existing-secret response.
7. Write every manifest entry, then GET each back and compare in memory. Validate SA JSON parsing, expected identities, exact KMS paths, PEM DER fingerprint against provider public key, and Vertex key ID/ownership. Preserve new secret revisions and equality results only. A failed write/readback rolls back the whole tuple while consumers remain stopped; do not assume multi-secret API atomicity.
8. Start consumers from a fresh raw-API-derived, allowlisted environment. Do not reuse `S1656_INFISICAL_INJECTED=true`, an old injected parent shell, or cached values. Recreate backend workers, AIM Data and the guard; prevent secret inheritance into builds. Existing authenticated `infisical run` behavior is documented in E2 but is not the rotation/proof mechanism for this task.
9. Perform section 9 proof and the full S1656 journey, then the production IAM removal in section 10. Retain old test versions enabled for the rollback window; do not revoke the copied production Vertex key or production SA credential.

## 9. Proof that every consumer switched

Generate a consumer ledger tied to exact image digests, container IDs, process start times, source SHAs and one rotation ID. Enumerate every Compose service, backend worker, scheduled/background Gemini caller and host lifecycle entry point at the implementation SHA. An unexplained or unreachable consumer blocks retirement.

- Fresh host loader/preflight reports expected test-only configuration and secret revision IDs without values; no old injection marker or ADC file wins precedence.
- Each backend worker reports actual credential identity and selected KMS version paths from initialized clients, not just its environment. New signing operation verifies under the provider-fetched new public key; old/tampered signatures fail where current trust is required.
- New decrypt client unwraps synthetic ciphertext encrypted to the new encryption public key; signer identity cannot decrypt and decrypt identity cannot sign. Read-only IAM permission evaluation proves no admin/IAM/destruction or production access, without attempting a destructive production call.
- AIM Data's actual verifier fingerprints the new key, accepts a freshly signed scan specification and rejects wrong-key/tampered fixtures. Backend and AIM Data recreate registrations/sessions as necessary; signing PEM must match exactly.
- Every Gemini route uses the guard; one bounded real request proves the new Vertex key works and is attributed to the dedicated project. Embedding dimensionality and completion endpoint behavior remain as in the pinned application; do not route Vertex using the KMS location variable.
- Guard proof covers exhaustion, concurrent reservations, retries, ambiguous timeouts, crashes, restarts, reset and month-boundary outstanding requests. At exhausted balance, provider request count does not increase, including through alternate backend callers and direct bypass attempts.
- Run S1656's complete synthetic money-path acceptance with before/after production no-effect evidence and exact images. A health response, Infisical equality or successful wrapper alone does not prove the journey.

## 10. Remove the temporary production admin grant

Before changing anything, read IAM for **`projects/aimarket-prod/locations/us-central1/keyRings/ai-market-trust`** and persist the canonical policy, etag/version, timestamp and digest in restricted evidence. Also read the production key/version inventory and relevant effective project/ancestor permissions. Resolve the R2 `global` discrepancy by provider resource reads; if the specified temporary member grant is absent, report that result and investigate, rather than mutate another ring.

Using the authorized operator, remove only member `serviceAccount:kms-trust-agent@aimarket-prod.iam.gserviceaccount.com` from its temporary `roles/cloudkms.admin` binding on that exact ring, preserving other members and conditions. Use concurrency/etag protection; a concurrent policy change requires a fresh read and reviewed minimal delta. If the binding becomes empty, remove only that empty binding.

Read IAM again and compare canonical before/after policies: the only delta must be that membership removal. Record effective admin access separately; an inherited admin grant means effective least privilege is still unproven and requires escalation, not an unauthorized wider cleanup. Read key/version inventories again to prove all production algorithms, primary versions and states unchanged. Obtain normal authorized production health/Trust Channel evidence without modifying production data or keys. Rollback never automatically re-adds admin.

## 11. Rollback and retirement lifecycle

Retain old `s1656-test-*` versions and secret-backed old tuple for at least 48 hours and two complete passing clean-seed journeys after cutover. These are proposed acceptance windows. Exercise one controlled rollback/re-cutover during this window before retirement approval.

If new KMS credentials/keys or Vertex key fail, stop new work, drain or retain reservations and reconcile paid epochs, stop consumers, restore the complete previous test-env tuple via the same raw v3 API, read it back, recreate consumers and restore/reseed only synthetic trust state. Restore the prior reviewed preflight mode/pin explicitly so its old-ring guards match. Never mix a new signing key with the old AIM Data PEM or resume a new-key encrypted session under old decryption keys.

Fallback means the current shared-boundary **test** signing/encryption keys and previous copied Vertex value reported by Max, not `platform-signing-key` or `platform-encryption-key`. The old production SA needs only its already-existing runtime crypto rights; removal of temporary admin is not undone. If runtime fallback requires additional production IAM changes, halt for separate authority.

Vertex fallback keeps the durable hard admission guard and the same remaining monthly balance. If that guard or its routing fails, inference stays paused; reverting to unmetered direct use is forbidden. A restored shared production key cannot supply dedicated-project billing evidence, so rollback is explicitly a temporary degraded state and never acceptance of isolation.

After successful re-cutover and the full window, prove every consumer and retained synthetic artifact is independent of old test versions. Disable only the exact old **test** versions first, rerun the journey, and retain restore capability. Schedule destruction only after evidence review and explicit destructive-operation authority at the implementation gate; record provider-returned destruction time and restore deadline. Google destroys key versions, not this design's notion of a whole deletable ring. Keep non-secret old public keys as historical verification evidence if needed.

Before actual destruction, rollback can restore old test versions according to provider-supported state/deadline and reload the old tuple. After destruction, old-key rollback is impossible: stop and recover with new test keys/reseed, never claim the old path remains available. Do not destroy or revoke production KMS keys, the production SA/key, or the production Vertex key; discard only their test-env references after the window.

## 12. Build-time prerender origin evaluation

Current evidence E3/F1 supports a narrow improvement: the server data-fetch helper already prefers `API_URL`. Compose only supplies `NEXT_PUBLIC_API_URL` during build, so prerender falls back to the host's `localhost:18000`. The runtime `API_URL=http://backend:8000` arrives too late for that build. `bin/up` explicitly starts backend first. This was inspected statically; no build was executed here.

**Recommendation:** evaluate supplying a server-only build-time `API_URL` pointing to the real synthetic backend on a dedicated, ephemeral builder-accessible private network. Keep `NEXT_PUBLIC_API_URL=http://localhost:18000` for browser calls. Use an explicitly configured builder that can join that network; do not assume Compose service DNS `backend` is available inside an ordinary BuildKit build. Preserve runtime `API_URL=http://backend:8000` and verify the build origin does not remain in runtime client bundles or cache keys that prevent refresh.

| Alternative | Assessment |
| --- | --- |
| Private-network build origin to real synthetic backend | Preferred evaluation: existing helper precedence may avoid product code changes, retains real prerender responses and removes host networking if the chosen builder supports isolated connectivity. |
| `host.docker.internal` build origin | Could avoid `network: host` but retains host access and platform-specific reachability. Not the recommended isolation end state. |
| Fixture HTTP origin or disabling prerender | Could remove live backend dependency, but changes build semantics and may conceal integration failures. Defer unless the preferred experiment fails and a separate design decision accepts it. |

Evaluation deliverable: pinned builder/version/configuration, clean frontend build with no host-network entitlement, observed requests only to allowed synthetic API/package origins, no production request, fresh homepage plus revalidation after seed, and preserved browser API origin. Inspect cached HTML/Next data and client bundles as well as container settings. Keep browser-runner `network_mode: host` as the independently required S1656 runtime behavior; removing it is not part of this evaluation. Failure records platform limitations and keeps the current build arrangement pending a separate implementation decision; it does not block KMS isolation if the evaluation itself is complete.

## 13. Integrity and operational controls

Keep raw API tokens and secret values entirely within authorized local execution. Test project access must be deny-by-default outside named runtime/provisioning identities, with inherited permissions inspected. Record provider audit event references for actual new-key operations and the exact IAM delta. Keep credential-bearing temporary files only where the existing runtime requires them, restricted to the owning process/container and cleaned on exit; do not export them as evidence.

Do not use board labels, source comments, prefix checks or secret revisions as substitutes for effective IAM, consumer operation or billing evidence. A provider outage, unknown key state, partial rotation, stale worker, budget ambiguity or missing proof pauses cutover/retirement; it never justifies a broader production permission grant.

## 14. Slice 1 scope

In scope: dedicated project/ring and purpose-limited test identities; compatible new keys; test-only KMS client separation; dedicated Vertex key and hard budget guard; exact preflight/configuration updates; raw v3 rotation and per-consumer proof; reversible retirement of old test versions followed by separately authorized destruction; exact temporary production admin removal; build-origin evaluation and recommendation; operational runbook updates after implementation.

Non-scope: production key rotation; any production trust-ring key/version change other than retiring the explicitly named old **test** versions after authorization; any production key-material change; production SA/Vertex-key revocation; production IAM changes beyond the specified temporary ring admin membership; application production deployment, customer data, unrelated framework/spec work, browser-runner network changes, or prerender implementation absent later approval.

## 15. Acceptance criteria

1. Branch parent is the pinned `origin/main` baseline, diff contains only this specification, the other in-flight S1658 spec is absent, and remote branch SHA equals the authored commit. No merge occurs.
2. Exact-source inventory and drift/discrepancy statements remain in the approved design; unavailable live facts are explicitly marked.
3. Readback identifies a separate test project/ring, correct key purposes/algorithms/versions, signer/verifier-only SA and separate decrypt SA. Effective permission checks prove no runtime admin, impersonation or production authority.
4. Both KMS clients perform their intended synthetic crypto operation and are denied the other's private operation. No production client behavior changes are deployed.
5. Dedicated Vertex key ownership, endpoint compatibility and restrictions are proved without revealing values. Canonical `VERTEX_GEMINI_KEY` naming and API-key auth are retained.
6. Max confirms the monthly USD amount; the provider control is scoped only to test Vertex and hard admission evidence satisfies section 7 across every caller and failure mode. No paid activation with unresolved cap enforcement or pricing.
7. Raw v3 write/readback evidence identifies the exact project/environment/path and revisions; no bare CLI rotation, production sync/write or secret exposure occurs.
8. Consumer ledger accounts for every process, cached client, AIM Data verifier and lifecycle path. Actual new-key signing, verification, decryption and inference pass before old test versions are disabled/destroyed.
9. Full S1656 synthetic journey passes with exact images and before/after production no-effect evidence; stale trust state and outstanding epochs are reconciled.
10. Exact production-ring IAM before/after diff removes only the temporary admin membership; production key/version inventory is unchanged and production health is independently established.
11. Rollback to the previous tuple and re-cutover are demonstrated within the retention window without re-adding admin or bypassing the budget. Old-test-version destruction is blocked until the window, independence proof and destructive authority are complete.
12. Prerender evaluation produces the section 12 evidence or a reproducible limitation and recommendation. A runtime browser host-network setting is not confused with a frontend build setting.
13. Unanimous CC+GLM+DeepSeek CORE S3 receipts bind the exact reviewed SHA, and live infrastructure WIP is one before any dispatch. Missing reviewer, capacity or ownership proof blocks dispatch.

## 16. Gate sequence and release blockers

1. Gate 1: author, commit and push this isolated spec. Resolve budget amount and review the explicit extra client/guard work. This task stops after push.
2. Before dispatch: read live session/board/peer ownership and infrastructure WIP, establish the one permitted infrastructure item, then obtain exact-artifact unanimous CORE S3 CC+GLM+DeepSeek review. Do not infer the slot is free from this document; do not dispatch a partial panel.
3. Gate 2: implement only the approved test changes with focused IAM, crypto, credential injection, budget concurrency/failure and rollback tests. Pin fresh provider docs, source commits and images. Billing/project creation, paid tests and destructive authority must be explicitly recorded before those operations.
4. Subsequent infrastructure/live gate: provision, rotate, prove each consumer and journey, remove temporary admin, exercise rollback and observe the retention window. Static review, provider state, runtime proof and authorized browser proof remain separate.
5. Retirement gate: disable and verify old test versions, then schedule destruction only with the required approval and dependency-free evidence. Close the temporary decision only after final proof; do not mark isolation complete while operating on rollback/shared credentials.

## 17. Risks and falsifiers

| Decision at risk | Falsifier | Required response |
| --- | --- | --- |
| Dedicated project isolates test billing/IAM | Key bills production, inherited roles cross the boundary, or budget can pause production | Block activation; correct test-only scope or return to Gate 1. |
| Signer-only role works with existing application | Shared client still attempts decryption under signer identity or readiness requires broader rights | Complete reviewed explicit client split; never add admin/decrypt to signer. |
| Strict budget holds | Any caller bypasses reservations, retry exceeds reservation, unknown charge bound, or ledger resets with environment | Pause paid use; provider delayed cap alone is insufficient. |
| Rotation reached all consumers | Old identity/fingerprint in a live worker, cached client or host invocation | Stop and recreate/reconcile; preserve old test versions. |
| Minimal production change is safe | IAM diff includes anything beyond exact member removal, inherited admin remains, or production health regresses | Stop/escalate; do not perform adjacent cleanup or automatically re-add admin. |
| Old test keys are safe to destroy | Pending ciphertext, signatures requiring active old key, outstanding jobs or unproven rollback | Extend retention; destruction blocked. |
| Private build origin removes host access | Builder cannot join isolated network, reaches production or bakes wrong public origin/cache | Record failed evaluation and defer implementation; preserve current reviewed build. |

## 18. Author's reservations

The architecture is a proposal grounded in pinned code, not completed isolation. Live GCP IAM/resources/billing eligibility, exact old versions, Infisical contents/revisions, ticket/handoff records, active infrastructure WIP, production health and actual build/runtime behavior were not independently verified. The proposed project ID and USD 10 amount are not approvals. The runbook's older environment pin, `global` KMS examples, and omission of newer GCP secret requirements must be reconciled at implementation.

Two requirements make this more than a secret swap: signer-only permissions require an explicit decrypt-client separation, and a strict budget requires an unavoidable durable admission guard because provider spend caps allow overage. These changes need the required unanimous review. If either cannot be proved within the approved scope, paid cutover remains blocked; a soft threshold or broader runtime credential is not a compliant substitute.
