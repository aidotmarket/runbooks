---
title: GCP Auth
owner: vulcan
last_verified: '2026-09-22'
aliases:
- Vertex authentication
- Gmail OAuth
- gcloud credentials
- Trust Channel KMS
- Sign in with Google
- OAuth consent screen
error_signatures:
- 'Error 403: org_internal'
- ai.market can only be used within its organisation
- 'invalid_grant: Bad Request'
- Failed to authenticate Gmail
- 'RefreshError: Reauthentication is needed. Please run gcloud auth application-default login'
- 401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED
- Reauthentication failed
---

# GCP Auth

## Overview


## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Gmail OAuth refresh-token storage and use | SHIPPED | `ai-market-backend gmail_tokens table + GmailService/GmailWatchService` | Exercised by briefing send and drop-pipeline watch paths | 2026-06-01 |
| OAuth consent screen = External, publishing status In production (customer Google sign-in works; Gmail refresh tokens do not expire) | SHIPPED | `Google Auth Platform > Audience > User type (project aimarket-prod)` | Found NOT Internal on 2026-09-21 despite the 2026-06-01 check; Max set it to Internal 2026-09-21 (S1734), which blocked every non-ai.market customer at Google sign-in (`Error 403: org_internal`, first customer sergey@eolymp.com, 2026-09-22); Max set it to External + In production 2026-09-22 (S1736). Verified after the change: max@ and finance@ refresh tokens refresh and read Gmail | 2026-09-22 |
| gcloud CLI session auth (Pub/Sub and GCP admin) | SHIPPED | `gcloud CLI on Titan-1` | Verified via gcloud auth list and pubsub list | 2026-06-01 |
| Pub/Sub gmail-push topic and subscription | SHIPPED | `GCP Pub/Sub gmail-push -> api.ai.market gmail webhook` | Verified via gcloud pubsub topics/subscriptions list | 2026-06-01 |
| Vertex AI Gemini API-key auth | SHIPPED | `ai-market-backend app.core.config Settings.VERTEX_GEMINI_KEY` | Verified via Infisical key-prefix check expecting AQ. | 2026-06-01 |
| Trust Channel KMS service-account ADC | SHIPPED | `ai-market-backend app/core/gcp_credentials.py + app/core/kms_lifecycle.py` | `tests/test_kms_lifecycle_s1606.py`; live RSA registration and both Trust Channel handshakes | 2026-08-25 |

## Architecture & interactions

GCP authentication for ai.market spans four independent auth paths. Gmail OAuth uses long-lived refresh tokens stored in the `gmail_tokens` Railway Postgres table; the same GCP project `aimarket-prod` also holds the customer "Sign in with Google" client (`240358013785-fb8tb9r8...`, backend `GOOGLE_OAUTH_CLIENT_ID`), so the consent-screen setting serves both. It MUST be User Type External with publishing status In production: Internal blocks every customer outside the ai.market Workspace (`Error 403: org_internal`), and Testing expires Gmail refresh tokens after 7 days and limits sign-in to listed test users. The gcloud CLI holds a separate interactive session used for Pub/Sub and GCP admin; it requires a browser login and cannot be driven headlessly. Vertex AI Gemini uses a Vertex Express API key (prefix `AQ.`) held in Infisical as `VERTEX_GEMINI_KEY`. The Trust Channel KMS runtime separately uses `GCP_SERVICE_ACCOUNT_JSON`, canonical in Infisical `ai-market-backend`/`prod` and synchronized to Railway production; application credentials are configured before the shared KMS client is initialized. The KMS credential is not a Gemini credential.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Gmail OAuth | `GmailService / GmailWatchService` | `gmail_tokens (Railway Postgres)` | Gmail API, briefing, drop pipeline, draft sending | Refresh tokens non-expiring while the consent screen is In production (External or Internal); they expire in 7 days under Testing |
| OAuth Consent Screen | `GCP Console OAuth consent (project aimarket-prod)` | GCP project config | Gmail OAuth and customer Google sign-in | MUST be External + In production; Internal locks customers out, Testing expires tokens |
| gcloud CLI | `gcloud on Titan-1` | local gcloud config | Pub/Sub admin, GCP admin tasks | Interactive browser login only; Vulcan cannot do it headlessly |
| Pub/Sub | `gmail-push topic + gmail-push-sub` | GCP Pub/Sub | Gmail watch to `https://api.ai.market/api/v1/webhooks/gmail` | Drives the inbound drop pipeline |
| Vertex AI Gemini | `genai.Client(vertexai=True, api_key=...)` | `VERTEX_GEMINI_KEY (Infisical)` | Gemini embeddings and chat | API-key auth (AQ. prefix); embed calls MUST pass output_dimensionality |
| Trust Channel KMS | `configure_gcp_credentials` then `get_kms_client` | `GCP_SERVICE_ACCOUNT_JSON (Infisical -> Railway)` | GCP KMS keyring `ai-market-trust` | Runtime identity is `kms-trust-agent@aimarket-prod.iam.gserviceaccount.com`; private credential material must never be printed or persisted outside approved secret-backed transfer. |

### Canonical resource identifiers

| Resource | Value |
|---|---|
| Production project | `aimarket-prod` (number `240358013785`) |
| Organization | `1062465481671` (ai.market Workspace) |
| OAuth Client ID | `240358013785-dip4sn1ki9ti66m02u50ditbghrj0uls.apps.googleusercontent.com` |
| Pub/Sub topic | `gmail-push` |
| Pub/Sub subscription | `gmail-push-sub` delivering to `https://api.ai.market/api/v1/webhooks/gmail` |
| Prod GCP account | `max@ai.market` (the personal account `maxdrobbins@gmail.com` has no aimarket-prod access) |
| Vertex models | `gemini-embedding-001` (embeddings), `gemini-2.5-flash` (chat) |

Vertex client construction is `genai.Client(vertexai=True, api_key=settings.VERTEX_GEMINI_KEY.get_secret_value())`; every `embed_content` call MUST pass `EmbedContentConfig(output_dimensionality=settings.LLM_EMBEDDING_DIMENSIONS)` because the default output is 3072-dimensional, larger than the qdrant collection.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Max | interactive gcloud login and OAuth consent-screen configuration | GCP Console plus browser | GCP owner (max@ai.market) | COMPLETE |
| Vulcan/Mars | verify auth state (direct refresh check per account), prepare the E-02 environment for Max's re-auth, redeploy only if the Gmail watch lapsed, verify Vertex key prefix | shell plus railway plus infisical | repo plus Railway plus Infisical | COMPLETE |
| GmailService | programmatic send using stored refresh token | ai-market-backend | gmail_tokens read | COMPLETE |
| GmailWatchService | inbox watch driving the drop pipeline | ai-market-backend | Gmail watch | COMPLETE |

Only Max can perform the interactive gcloud browser login and change the OAuth consent-screen User Type; these cannot be done headlessly by an agent. Vulcan/Mars own the non-interactive recovery steps (setting up E-02's environment, per-account verification, a redeploy only if the Gmail watch lapsed, key verification); the token itself is written by setup_gmail_auth.py during Max's browser sign-in. The backend services consume the stored credentials at runtime.

## How to operate

```yaml operate
- id: E-01
  trigger: Routine verification that GCP auth is healthy for Gmail, Pub/Sub, and the active gcloud account.
  pre_conditions: [gcloud CLI installed on Titan-1, max@ai.market is the intended active account, project aimarket-prod is the intended project]
  tool_or_endpoint: gcloud auth list; gcloud config get-value project; gcloud pubsub topics list; gcloud pubsub subscriptions list
  argument_sourcing:
    account: expect max@ai.market as the active account
    project: expect aimarket-prod
    pubsub: expect topic gmail-push and subscription gmail-push-sub
  idempotency: IDEMPOTENT
  expected_success: {shape: active account is max@ai.market and project is aimarket-prod and gmail-push topic plus gmail-push-sub subscription are listed, verification: confirm each command output matches the expected account project topic and subscription}
  expected_failures:
    - {signature: "wrong_active_account", cause: gcloud pointed at a non-prod account}
    - {signature: "wrong_project", cause: gcloud config project is not aimarket-prod}
  next_step_success: No action; auth is healthy.
  next_step_failure: Isolate using When it breaks-03 for account/project mismatch.
- id: E-02
  trigger: Gmail-dependent jobs (briefing, drop pipeline, draft sending) stopped because refresh tokens expired.
  pre_conditions: [OAuth consent screen confirmed External + In production, GOOGLE_OAUTH_CREDENTIALS_JSON available in Railway env, railway CLI authenticated on Titan-1]
  tool_or_endpoint: python3 scripts/setup_gmail_auth.py <address> run by Max on Titan-1 with GOOGLE_OAUTH_CREDENTIALS_JSON from the backend service env and DATABASE_URL set to the Postgres service's DATABASE_PUBLIC_URL (both read via the Railway account token from Infisical, never printed); the script writes gmail_tokens directly. Max signs in in the browser AS the target account. Done this way 2026-09-21 (S1734) for finance@ and max@; no redeploy was needed.
  argument_sourcing:
    credentials: GOOGLE_OAUTH_CREDENTIALS_JSON sourced from Railway env (no local secret files)
    emails: every live gmail_tokens account - max@ai.market (crm_briefing) and finance@ai.market (allai_operations; allai@ai.market is an alias of finance@, not an account). There is no ally@ai.market account; its gmail_tokens row is a dead leftover that nothing authenticates (Max, 2026-09-21).
    db_update: none by hand; setup_gmail_auth.py writes gmail_tokens itself. Redeploy only if the Gmail watch has lapsed (no webhook notifications arriving)
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: gmail_tokens rows for max@ai.market and finance@ai.market hold fresh refresh tokens and each passes a direct refresh check, verification: briefing and drop pipeline resume; confirm rows updated_at is current}
  expected_failures:
    - {signature: "consent_screen_testing", cause: tokens re-expire in 7 days because publishing status is Testing}
    - {signature: "db_unreachable_from_titan", cause: DATABASE_URL left at the backend default or the private postgres.railway.internal host; set it to the Postgres service DATABASE_PUBLIC_URL and re-run the script (no manual UPDATE needed)}
  next_step_success: Verify briefing and drop pipeline resume on the next scheduled run.
  next_step_failure: Apply Repair-01 to fix the consent screen before re-issuing tokens.
- id: E-03
  trigger: Verify the Vertex AI Gemini API key is the correct Express key type before or after a rotation.
  pre_conditions: [infisical CLI authenticated on Titan-1, project id bd272d48-c5a1-4b52-9d24-12066ae4403c reachable]
  tool_or_endpoint: infisical secrets get VERTEX_GEMINI_KEY --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c --env prod --plain --silent --domain https://secrets.ai.market | head -c 4
  argument_sourcing:
    secret_name: VERTEX_GEMINI_KEY (canonical uppercase name; no aliases in production)
    expected_prefix: AQ.A
  idempotency: IDEMPOTENT
  expected_success: {shape: the key prefix is AQ. confirming a Vertex Express API key, verification: head -c 4 returns AQ.A}
  expected_failures:
    - {signature: "wrong_key_prefix", cause: an OAuth token or a legacy Developer API key (AIza...) is stored instead of a Vertex Express key}
  next_step_success: No action; the Vertex key is valid.
  next_step_failure: Isolate using When it breaks-04 and re-create the key scoped to the Vertex AI API.
- id: E-04
  trigger: Verify Trust Channel KMS authentication and key-purpose readiness before or after a credential recovery.
  pre_conditions: [infisical and railway CLIs authenticated on Titan-1, production project aimarket-prod selected, read-only GCP KMS access available]
  tool_or_endpoint: Compare non-secret credential metadata in Infisical and Railway; inspect both KMS public keys and algorithms; then run the Trust Channel E-05 live probe.
  argument_sourcing:
    credential: GCP_SERVICE_ACCOUNT_JSON from Infisical ai-market-backend/prod synchronized to Railway production
    signing_key: projects/aimarket-prod/locations/global/keyRings/ai-market-trust/cryptoKeys/platform-signing-key/cryptoKeyVersions/1
    encryption_key: projects/aimarket-prod/locations/global/keyRings/ai-market-trust/cryptoKeys/platform-encryption-key/cryptoKeyVersions/1
  idempotency: IDEMPOTENT
  expected_success: {shape: Infisical and Railway identify the same active service-account key without exposing it; signing version 1 is RSA_SIGN_PKCS1_2048_SHA256; encryption version 1 is RSA_DECRYPT_OAEP_2048_SHA256; backend readiness and the live two-route handshake pass, verification: correlate the exact deployment SHA and non-secret key ids plus the Trust Channel probe evidence}
  expected_failures:
    - {signature: KMS readiness check failed, cause: credential unavailable or denied, key version unavailable, or key algorithm does not match its configured purpose}
    - {signature: CRYPTO_SCHEME_MISMATCH, cause: an operation was routed to the wrong purpose-specific KMS key}
  next_step_success: Keep the credential secret-backed and record only service-account identity, key id, algorithms, deployment identity, and probe result.
  next_step_failure: Keep Trust Channel registration fail-closed; repair the exact credential, IAM, key name, or algorithm mismatch without exporting any KMS private key.
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Morning briefing or drop pipeline silently stopped | Gmail refresh token expired because the OAuth consent screen publishing status is Testing rather than In production | Open the GCP Console OAuth consent screen for project aimarket-prod and check Publishing status; check gmail_tokens.updated_at age | Repair-01 | CONFIRMED |
| F-02 | gcloud reports `Reauthentication failed` | The interactive gcloud session expired | Run gcloud auth list and confirm whether max@ai.market is still active | Repair-02 | CONFIRMED |
| F-03 | gcloud reports `does not have permission` or operations hit the wrong project | Wrong gcloud account active or gcloud pointed at the wrong project | Compare gcloud config account and project against max@ai.market and aimarket-prod | Repair-03 | CONFIRMED |
| F-04 | AG council reviews fail with `RefreshError: Reauthentication is needed. Please run gcloud auth application-default login` | The AG adapter authenticated with the local user OAuth/ADC token (now expired) instead of the Vertex API key. Vertex Gemini uses the Vertex Express API key (`VERTEX_API_KEY`, AQ. prefix), NOT OAuth/ADC (How to operate, H.1). Recurs whenever the local ADC token expires. | Confirm `VERTEX_API_KEY` is present in the com.koskadeux.mcp process env (`ps eww <mcp pid>`) and AQ.-prefixed in Infisical bd272d48 | Repair-04 | CONFIRMED |
| F-05 | Gemini embed upserts fail / qdrant dimension mismatch | An embed call omitted `output_dimensionality` and defaulted to 3072, exceeding the qdrant collection dimension | Check the embed call passes `output_dimensionality=settings.LLM_EMBEDDING_DIMENSIONS` | Repair-05 | CONFIRMED |
| F-04 | `401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED` on Gemini calls | Wrong key type passed (an OAuth token or a legacy Developer API key instead of a Vertex Express key) | Check the stored VERTEX_GEMINI_KEY prefix; a valid key starts with AQ. | Repair-04 | CONFIRMED |
| F-05 | qdrant upsert fails because embeddings are 3072-dimensional | An embed call omitted output_dimensionality so it defaulted to 3072 while the qdrant collection is smaller | Inspect the embed call site for EmbedContentConfig(output_dimensionality=...) | Repair-05 | CONFIRMED |
| F-06 | Marketplace search takes ~11s · any Gemini **embedding** call takes ~10.4s · qdrant sync outbox throughput stuck near 14k rows/hour | The embedding client is pointed at the **global** Vertex endpoint (`aiplatform.googleapis.com`). `gemini-embedding-001` costs ~10.4s per call there and ~0.3s on any regional endpoint. Latency is flat regardless of batch size and identical on parallel calls, so it looks like a hang, not a queue. Do NOT go looking for a slow model, a bad supplier, or a network problem: DNS/TCP/TLS all complete in ~50ms and TTFB is the whole 10.4s. | From the production container (`railway ssh`), POST the same payload to `aiplatform.googleapis.com` and to `us-west1-aiplatform.googleapis.com` and compare TTFB. Expect ~10.4s vs ~0.3s. | Repair-06 | CONFIRMED |
| F-07 | Trust Channel registration returns 503 or a handshake logs `CRYPTO_SCHEME_MISMATCH` | KMS credential is unavailable/invalid, IAM or key readiness failed, or signing/decrypt was routed to the wrong purpose-specific key | Verify non-secret credential metadata matches between Infisical and Railway; confirm both version-1 algorithms; inspect the exact deployment and correlated Trust Channel log window | Repair-07 | CONFIRMED |

### Checking every saved Gmail login (S1734)

To tell which account is dead, refresh each `gmail_tokens` row directly against Google (`grant_type=refresh_token` to the row's `token_uri` with its `client_id`/`client_secret`), in-process, printing only the address and `OK`/`error`. On 2026-09-21 this showed max@ai.market OK while finance@ai.market and the leftover ally@ai.market returned `invalid_grant`; the backend log line `Failed to authenticate Gmail: ('invalid_grant: Bad Request', ...)` does not name the account. The Google Auth Platform Overview page's Errors chart (20-55 errors/day in late August 2026) is the outside signal that a login is failing. After a password change or reset on any of these accounts, re-run E-02 for it.

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: OAuth Consent Screen
  root_cause: The OAuth consent screen for aimarket-prod is in publishing status Testing, so Gmail refresh tokens expire after 7 days and break briefings, the drop pipeline, and draft sending.
  repair_entry_point: GCP Console OAuth consent screen (project aimarket-prod)
  change_pattern: Set publishing status to In production with User Type External (Audience > Publish app; Branding must have app name, support email, home page https://ai.market and privacy policy https://ai.market/legal/privacy). Never use Make internal: it blocks customer Google sign-in, then re-issue Gmail tokens via E-02 (setup_gmail_auth.py <address> writes gmail_tokens directly). Only the live Workspace users max@ai.market and finance@ai.market authorize; allai@ai.market is an alias of finance@ and there is no ally@ai.market account.
  rollback_procedure: None required; External + In production is the only correct setting. If re-issuance fails, retain the prior token rows until new tokens are confirmed written.
  integrity_check: Confirm User Type reads External and Publishing status reads In production and gmail_tokens rows for both addresses show a current updated_at, then confirm the next briefing run succeeds.
- id: G-02
  symptom_ref: F-02
  component_ref: gcloud CLI
  root_cause: The interactive gcloud session expired.
  repair_entry_point: gcloud CLI on Titan-1
  change_pattern: Run gcloud auth login --account=max@ai.market in an interactive terminal (Max only; cannot be done headlessly).
  rollback_procedure: None; re-login is non-destructive.
  integrity_check: gcloud auth list shows max@ai.market as active.
- id: G-03
  symptom_ref: F-03
  component_ref: gcloud CLI
  root_cause: gcloud is pointed at the wrong account or project.
  repair_entry_point: gcloud CLI on Titan-1
  change_pattern: Run gcloud config set account max@ai.market and gcloud config set project aimarket-prod.
  rollback_procedure: Restore the prior account/project with gcloud config set if the change was unintended.
  integrity_check: gcloud config get-value project returns aimarket-prod and the active account is max@ai.market.
- id: G-04
  symptom_ref: F-04
  component_ref: Vertex AI Gemini
  root_cause: >-
    The AG adapter authenticated with user OAuth/ADC (or a non-Vertex key) instead of the Vertex Express API key; an expired local ADC token then fails with `RefreshError: Reauthentication is needed`. Recurring — the fix is always API-key-first auth, not re-running gcloud login.
  repair_entry_point: GCP Console Credentials API Keys, scoped to the Vertex AI API
  change_pattern: >-
    Re-create the API key scoped to the Vertex AI API so the prefix is AQ., store it as VERTEX_GEMINI_KEY in Infisical. If AG dispatches 401, sync VERTEX_API_KEY to match and restart ag_server. As of S1132, `ag_adapter._select_genai_client_kwargs` PREFERS `VERTEX_API_KEY` (exported into the MCP process env by `scripts/launch_mcp_server.sh` from Infisical project bd272d48) over user OAuth/ADC; project ADC is a fallback only. This reverts the S805 ADC-first ordering, which broke all AG reviews when the local ADC token expired (`RefreshError: Reauthentication is needed`). If AG auth fails, verify `VERTEX_API_KEY` is present in the MCP env (`ps eww` on the com.koskadeux.mcp pid) and AQ.-prefixed in Infisical, then restart com.koskadeux.mcp.
  rollback_procedure: Restore the previous working key value from Infisical history if the new key fails validation.
  integrity_check: head -c 4 of the stored key returns AQ.A and a test embed/chat call succeeds.
- id: G-05
  symptom_ref: F-05
  component_ref: Vertex AI Gemini
  root_cause: An embed call omitted output_dimensionality and defaulted to 3072, which exceeds the qdrant collection dimension.
  repair_entry_point: the embed call site in ai-market-backend
  change_pattern: Pass EmbedContentConfig(output_dimensionality=settings.LLM_EMBEDDING_DIMENSIONS) on every embed_content call.
  rollback_procedure: None; adding the mandatory parameter is the fix.
  integrity_check: Embeddings return the configured dimension and qdrant upserts succeed.
- id: G-06
  symptom_ref: F-06
  component_ref: Vertex AI Gemini
  root_cause: The embedding client is pointed at the GLOBAL Vertex endpoint (aiplatform.googleapis.com), where gemini-embedding-001 costs ~10.4s per call. The same model on any regional endpoint returns in ~0.3s. This was the entirety of the ~11s marketplace search (T-2026-000239) and the ~14k rows/hour ceiling on the qdrant sync outbox. It is NOT a slow model, a bad supplier, or a network problem - DNS/TCP/TLS complete in ~50ms and TTFB is the whole 10.4s.
  repair_entry_point: settings.VERTEX_EMBEDDING_LOCATION (app/core/config.py) and _get_gemini_embedding_client (app/core/llm.py)
  change_pattern: Set VERTEX_EMBEDDING_LOCATION to a region (default us-west1, the closest Vertex region to Railway us-west2) and redeploy; the client is cached for the process lifetime so the value only takes effect on restart. Do NOT point the COMPLETION client at a region - APPROVED_GEMINI_MODEL (gemini-3.1-pro-preview) returns HTTP 404 on us-west1/us-west4/us-central1/us-east4 and is served only from global, where it carries no latency penalty (~2.7s). The two clients must stay separate. Google's published model-location table claims regional availability for the completion model and is wrong; measure from the production container (railway ssh) and treat the container as ground truth.
  rollback_procedure: Set VERTEX_EMBEDDING_LOCATION=global. No re-embedding is needed in either direction - embedding vectors are bit-identical across Vertex endpoints (cosine 1.000000, max abs diff 0.0), so the Qdrant corpus stays valid whichever endpoint is in use.
  integrity_check: GET /api/v1/search/listings?q=<term> returns in <1s with `fallback` absent from the response. A `fallback_reason` of "embedding_failed", or a SEARCH_DEGRADED_NON_SEMANTIC warning in the logs, means search is silently serving keyword-matched, non-semantic results.
- id: G-07
  symptom_ref: F-07
  component_ref: Trust Channel KMS
  root_cause: The backend cannot authenticate to KMS, cannot validate both exact key algorithms, or routes signing and decrypt operations to the same key.
  repair_entry_point: Infisical ai-market-backend/prod, Railway production variables, app/core/gcp_credentials.py, and app/core/kms_lifecycle.py
  change_pattern: Restore the approved kms-trust-agent credential through Infisical-to-Railway synchronization; initialize credentials before the shared KMS client; keep platform-signing-key and platform-encryption-key distinct; validate both version-1 algorithms before reporting ready. Never create a replacement key or change IAM when the existing production resources are healthy.
  rollback_procedure: Restore the previous working Infisical secret version and reviewed backend deployment if the recovered credential or routing fails validation; leave registration fail-closed during rollback.
  integrity_check: Infisical and Railway expose matching non-secret credential metadata; readiness fetches both public keys with exact algorithms; RSA registration returns distinct public keys; both Trust Channel WebSocket paths establish; cleanup leaves the probe device and sessions inactive; correlated logs contain no KMS or crypto-scheme error.
```

## Changes and maintenance

### H.1 Invariants

- The OAuth consent screen for aimarket-prod MUST be User Type External with publishing status In production. Internal blocks customer Google sign-in (`org_internal`); Testing expires Gmail refresh tokens after 7 days.
- `VERTEX_GEMINI_KEY` is the canonical uppercase secret name for the Vertex Express API key; no aliases are permitted in production code.
- Every Gemini embed call MUST pass `output_dimensionality=settings.LLM_EMBEDDING_DIMENSIONS`.
- The gcloud interactive login can only be performed by Max in a browser; it is never headless.
- `GCP_SERVICE_ACCOUNT_JSON` is the production Trust Channel KMS credential, canonical in Infisical `ai-market-backend`/`prod` and synchronized to Railway. It is independent of Vertex Gemini auth and must never be printed or written outside an approved secret-backed transfer.
- Trust Channel KMS signing and decryption MUST use distinct keys with algorithms `RSA_SIGN_PKCS1_2048_SHA256` and `RSA_DECRYPT_OAEP_2048_SHA256`, respectively.
- **Embeddings MUST use a REGIONAL Vertex endpoint; completions MUST use the GLOBAL one.** These are two separate clients in `app/core/llm.py` (`_get_gemini_embedding_client()` regional, `_get_gemini_client()` global) and MUST NOT be merged. `gemini-embedding-001` is ~10.4s on global and ~0.3s regionally; the approved completion model (`APPROVED_GEMINI_MODEL`, currently `gemini-3.1-pro-preview`) returns **HTTP 404 on every regional endpoint** and is served only from global. Google's published model-location table claims otherwise and is wrong — MP cited it and approved a change that would have 404'd every allAI completion. Measure from the production container; the container is ground truth. The region is `VERTEX_EMBEDDING_LOCATION` (default `us-west1`, matching Railway `us-west2`); setting it to `global` is the rollback and costs the 10.4s back.
- Embedding vectors are **bit-identical** across Vertex endpoints (cosine 1.000000, max abs diff 0.0), so changing `VERTEX_EMBEDDING_LOCATION` never requires re-embedding the Qdrant corpus.

### H.2 BREAKING predicates

- Changing the OAuth consent screen to Internal is BREAKING (customers outside ai.market cannot sign in with Google); changing it to Testing is BREAKING (Gmail refresh tokens begin expiring).
- Renaming or aliasing `VERTEX_GEMINI_KEY` is BREAKING because Pydantic case-sensitive settings will fail to load the key.
- Moving Gemini auth to the Trust Channel service-account ADC path is BREAKING because Gemini and KMS use independent credential mechanisms and scopes.

### H.3 REVIEW predicates

- Rotating the Vertex Express API key requires REVIEW because AG reads a separate `VERTEX_API_KEY` that must be synced.
- Changing the Pub/Sub gmail-push topic or subscription target requires REVIEW because it reroutes the drop pipeline.

### H.4 SAFE predicates

- Verifying auth state via the read-only gcloud and Infisical checks is SAFE.
- Re-issuing Gmail tokens while the consent screen is already External + In production is SAFE.

### H.5 Boundary definitions

#### module

The module boundary is the GCP authentication surface used by ai.market: Gmail OAuth, the gcloud CLI session, Pub/Sub wiring, and the Vertex Gemini API key.

#### public contract

The public contract is the set of credentials and endpoints the backend depends on: valid gmail_tokens rows, an active gcloud session, the gmail-push subscription delivering to the webhook, and a valid VERTEX_GEMINI_KEY.

#### runtime dependency

A runtime dependency is any external system required at run time: GCP OAuth, the Gmail API, GCP Pub/Sub, the Vertex AI API, Railway Postgres for gmail_tokens, and Infisical for secret values.

#### config default

A config default is any default identity or scope value: the active gcloud account max@ai.market, the project aimarket-prod, and the canonical secret name VERTEX_GEMINI_KEY.

### H.6 Adjudication

When two operators classify a GCP-auth change differently, use the more restrictive class and record the dispute. Max resolves any classification dispute that alters identity, project scope, or the consent-screen setting.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, Agent capabilities]
    scenario: |
      id: E-01. trigger: routine verification that GCP auth is healthy. tool_or_endpoint: gcloud auth list; gcloud config get-value project; gcloud pubsub topics list; gcloud pubsub subscriptions list. expected_success: active account max@ai.market; project aimarket-prod; topic gmail-push and subscription gmail-push-sub present. next_step_failure: isolate with F-03.
    expected_answers:
      - kind: human_action
        verb: verify
        object: gcloud account project and Pub/Sub wiring
        target: confirm max@ai.market aimarket-prod gmail-push
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02, Architecture & interactions]
    scenario: |
      id: E-02. trigger: Gmail jobs stopped because refresh tokens expired. tool_or_endpoint: setup_gmail_auth.py <address> run with DATABASE_URL set to the Postgres DATABASE_PUBLIC_URL, which writes gmail_tokens directly; redeploy only if the Gmail watch has lapsed (no webhook notifications). expected_success: fresh tokens for max@ai.market and finance@ai.market. next_step_failure: apply G-01 to fix the consent screen first.
    expected_answers:
      - kind: human_action
        verb: reissue
        object: Gmail refresh tokens
        target: setup_gmail_auth.py <address> with DATABASE_URL at the Postgres public URL (direct write), then a direct refresh check; redeploy only if the Gmail watch lapsed
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03, Architecture & interactions]
    scenario: |
      id: E-03. trigger: verify the Vertex Gemini key type. tool_or_endpoint: infisical secrets get VERTEX_GEMINI_KEY then head -c 4. expected_success: prefix is AQ. confirming a Vertex Express key. next_step_failure: isolate with F-04.
    expected_answers:
      - kind: human_action
        verb: verify
        object: VERTEX_GEMINI_KEY prefix
        target: expect AQ.A
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-01, G-01]
    scenario: |
      id: F-01. trigger: morning briefing or drop pipeline silently stopped. verification: check the OAuth consent screen User Type and gmail_tokens age. expected_success: classify as expired Gmail refresh token from a consent screen in Testing. next_step_success: apply G-01.
    expected_answers:
      - kind: human_action
        verb: classify
        object: stopped Gmail jobs
        target: F-01 then G-01
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-02, G-02]
    scenario: |
      id: F-02. trigger: gcloud reports Reauthentication failed. verification: gcloud auth list shows whether max@ai.market is still active. expected_success: classify as an expired interactive gcloud session. next_step_success: apply G-02 (Max re-runs gcloud auth login).
    expected_answers:
      - kind: human_action
        verb: classify
        object: gcloud reauthentication failure
        target: F-02 then G-02
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-03, G-03]
    scenario: |
      id: F-03. trigger: gcloud reports does not have permission or hits the wrong project. verification: compare gcloud config account and project against max@ai.market and aimarket-prod. expected_success: classify as wrong active account or wrong project. next_step_success: apply G-03.
    expected_answers:
      - kind: human_action
        verb: classify
        object: gcloud permission or wrong-project error
        target: F-03 then G-03
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [F-04, G-04]
    scenario: |
      id: F-04. trigger: 401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED on Gemini calls. verification: check the stored VERTEX_GEMINI_KEY prefix expecting AQ. expected_success: classify as wrong key type. next_step_success: apply G-04 and re-create the key scoped to the Vertex AI API.
    expected_answers:
      - kind: human_action
        verb: classify
        object: Gemini 401 unauthenticated
        target: F-04 then G-04
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-01, F-01]
    scenario: |
      id: G-01. trigger: consent screen is in Testing so Gmail tokens keep expiring. change_pattern: publish the app (External + In production) then re-issue tokens via E-02. expected_success: External + In production and fresh tokens for both addresses. next_step_failure: retain prior token rows until new tokens are confirmed.
    expected_answers:
      - kind: human_action
        verb: set
        object: OAuth consent screen User Type
        target: External + In production then re-issue tokens
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-05, F-05]
    scenario: |
      id: G-05. trigger: qdrant upsert fails because embeddings are 3072-dimensional. change_pattern: pass output_dimensionality on every embed_content call. expected_success: embeddings match the configured dimension and upserts succeed. next_step_failure: audit all embed call sites.
    expected_answers:
      - kind: human_action
        verb: add
        object: output_dimensionality on embed calls
        target: EmbedContentConfig dimension parameter
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [Changes and maintenance]
    scenario: |
      id: H-01. trigger: a proposal would switch the OAuth consent screen to Internal or back to Testing. expected_success: classify as BREAKING (Internal locks customers out of Google sign-in; Testing expires refresh tokens). next_step_success: block the change and keep External + In production.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [Changes and maintenance]
    scenario: |
      id: H-02. trigger: a proposal would rename or alias VERTEX_GEMINI_KEY. expected_success: classify as BREAKING because Pydantic case-sensitive settings would fail to load the key. next_step_success: keep the canonical uppercase name.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [F-01, F-04]
    scenario: |
      id: AMB-01. trigger: Gmail jobs stop AND Gemini calls 401 at the same time and the operator asks whether it is one root cause. pre_conditions: both symptoms observed. expected_success: classify as two independent auth paths (Gmail OAuth via consent screen vs Vertex Express key), isolate each separately via F-01 and F-04, not as a single shared fix. expected_failures: assuming one shared credential and applying a single repair. next_step_success: run F-01 and F-04 independently. next_step_failure: escalate if a shared cause is suspected after both isolations.
    expected_answers:
      - kind: human_action
        verb: classify
        object: simultaneous Gmail and Gemini auth failures
        target: two independent paths; isolate F-01 and F-04 separately
    weight: 0.08333333333333333
```

## Maintenance

Lifecycle metadata records this page's most recent operational refresh.

```yaml lifecycle
last_refresh_session: S1734
last_refresh_commit: 0fe590601d725b10466c6c8388483ee677134541
last_refresh_date: 2026-09-21T17:40:00Z
owner_agent: vulcan
refresh_triggers:
  - OAuth consent-screen requirement or Gmail token flow changes
  - Vertex Gemini auth model or canonical key name changes
  - Trust Channel KMS credential, key identity, IAM scope, or purpose routing changes
  - Pub/Sub gmail-push topic or subscription target changes
  - gcloud account or project defaults change
scheduled_cadence: 90d
first_staleness_detected_at: null
```
