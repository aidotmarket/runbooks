---
system_name: gcp-auth
purpose_sentence: Google Cloud authentication for the ai.market backend covering Gmail API (briefings, drop pipeline, draft sending), Pub/Sub, and Vertex AI Gemini, via OAuth refresh tokens, the gcloud CLI, and the Vertex Express API key.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Authentication for all GCP-backed services used by ai.market: Gmail OAuth refresh tokens (gmail_tokens table), the OAuth consent-screen requirement, gcloud CLI session auth, Pub/Sub gmail-push wiring, and Vertex AI Gemini API-key auth. Secret values are canonical in Infisical (project bd272d48-c5a1-4b52-9d24-12066ae4403c); this runbook documents auth mechanics and recovery, not secret values.
linter_version: 1.0.0
---

# GCP Auth

## §A. Header

The YAML frontmatter above defines the §A header. §J is authoritative for lifecycle refresh tracking; this header is the display summary for stateless readers.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Gmail OAuth refresh-token storage and use | SHIPPED | `ai-market-backend gmail_tokens table + GmailService/GmailWatchService` | Exercised by briefing send and drop-pipeline watch paths | 2026-06-01 |
| OAuth consent screen = Internal (non-expiring refresh tokens) | SHIPPED | `GCP Console OAuth consent screen (project aimarket-prod)` | Verified manually via consent-screen User Type check | 2026-06-01 |
| gcloud CLI session auth (Pub/Sub and GCP admin) | SHIPPED | `gcloud CLI on Titan-1` | Verified via gcloud auth list and pubsub list | 2026-06-01 |
| Pub/Sub gmail-push topic and subscription | SHIPPED | `GCP Pub/Sub gmail-push -> api.ai.market gmail webhook` | Verified via gcloud pubsub topics/subscriptions list | 2026-06-01 |
| Vertex AI Gemini API-key auth | SHIPPED | `ai-market-backend app.core.config Settings.VERTEX_GEMINI_KEY` | Verified via Infisical key-prefix check expecting AQ. | 2026-06-01 |
| Legacy service-account ADC (KMS/GCS only) | DEPRECATED | `ai-market-backend app/core/gcp_credentials.py` | Not used for Gemini since S533; SA cleanup tracked under BQ-VERTEX-SA-IAM-HARDENING | 2026-06-01 |

## §C. Architecture & Interactions

GCP authentication for ai.market spans three independent auth paths. Gmail OAuth uses long-lived refresh tokens stored in the `gmail_tokens` Railway Postgres table; these stay valid only while the GCP OAuth consent screen for project `aimarket-prod` is set to User Type Internal (External/Testing apps expire refresh tokens after 7 days and silently break briefings, the drop pipeline, and draft sending). The gcloud CLI holds a separate interactive session used for Pub/Sub and GCP admin; it requires a browser login and cannot be driven headlessly. Vertex AI Gemini uses a Vertex Express API key (prefix `AQ.`) held in Infisical as `VERTEX_GEMINI_KEY`, independent of both Gmail OAuth and the legacy service-account ADC path (which remains only for non-Gemini GCP services such as KMS and GCS).

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Gmail OAuth | `GmailService / GmailWatchService` | `gmail_tokens (Railway Postgres)` | Gmail API, briefing, drop pipeline, draft sending | Refresh tokens non-expiring only while consent screen is Internal |
| OAuth Consent Screen | `GCP Console OAuth consent (project aimarket-prod)` | GCP project config | Gmail OAuth | User Type MUST be Internal; single most important setting |
| gcloud CLI | `gcloud on Titan-1` | local gcloud config | Pub/Sub admin, GCP admin tasks | Interactive browser login only; Vulcan cannot do it headlessly |
| Pub/Sub | `gmail-push topic + gmail-push-sub` | GCP Pub/Sub | Gmail watch to `https://api.ai.market/api/v1/webhooks/gmail` | Drives the inbound drop pipeline |
| Vertex AI Gemini | `genai.Client(vertexai=True, api_key=...)` | `VERTEX_GEMINI_KEY (Infisical)` | Gemini embeddings and chat | API-key auth (AQ. prefix); embed calls MUST pass output_dimensionality |

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

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Max | interactive gcloud login and OAuth consent-screen configuration | GCP Console plus browser | GCP owner (max@ai.market) | COMPLETE |
| Vulcan/Mars | verify auth state, push refreshed Gmail token to Railway DB, redeploy, verify Vertex key prefix | shell plus railway plus infisical | repo plus Railway plus Infisical | COMPLETE |
| GmailService | programmatic send using stored refresh token | ai-market-backend | gmail_tokens read | COMPLETE |
| GmailWatchService | inbox watch driving the drop pipeline | ai-market-backend | Gmail watch | COMPLETE |

Only Max can perform the interactive gcloud browser login and change the OAuth consent-screen User Type; these cannot be done headlessly by an agent. Vulcan/Mars own the non-interactive recovery steps (token DB update, redeploy, key verification). The backend services consume the stored credentials at runtime.

## §E. Operate

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
  next_step_failure: Isolate using §F-03 for account/project mismatch.
- id: E-02
  trigger: Gmail-dependent jobs (briefing, drop pipeline, draft sending) stopped because refresh tokens expired.
  pre_conditions: [OAuth consent screen confirmed or being set to Internal, GOOGLE_OAUTH_CREDENTIALS_JSON available in Railway env, railway CLI authenticated on Titan-1]
  tool_or_endpoint: python3 scripts/setup_gmail_auth.py then update gmail_tokens via railway connect Postgres then railway redeploy --yes
  argument_sourcing:
    credentials: GOOGLE_OAUTH_CREDENTIALS_JSON sourced from Railway env (no local secret files)
    emails: max@ai.market and ally@ai.market
    db_update: UPDATE gmail_tokens SET refresh_token then redeploy to renew the Gmail watch
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: gmail_tokens rows for max@ai.market and ally@ai.market hold fresh refresh tokens and the redeploy renews the Gmail watch, verification: briefing and drop pipeline resume; confirm rows updated_at is current}
  expected_failures:
    - {signature: "consent_screen_not_internal", cause: tokens re-expire in 7 days because User Type is still External/Testing}
    - {signature: "db_unreachable_from_titan", cause: setup script cannot reach postgres.railway.internal directly; the token must be pushed via railway connect Postgres}
  next_step_success: Verify briefing and drop pipeline resume on the next scheduled run.
  next_step_failure: Apply §G-01 to fix the consent screen before re-issuing tokens.
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
  next_step_failure: Isolate using §F-04 and re-create the key scoped to the Vertex AI API.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Morning briefing or drop pipeline silently stopped | Gmail refresh token expired because the OAuth consent screen is External/Testing rather than Internal | Open the GCP Console OAuth consent screen for project aimarket-prod and check User Type; check gmail_tokens.updated_at age | §G-01 | CONFIRMED |
| F-02 | gcloud reports `Reauthentication failed` | The interactive gcloud session expired | Run gcloud auth list and confirm whether max@ai.market is still active | §G-02 | CONFIRMED |
| F-03 | gcloud reports `does not have permission` or operations hit the wrong project | Wrong gcloud account active or gcloud pointed at the wrong project | Compare gcloud config account and project against max@ai.market and aimarket-prod | §G-03 | CONFIRMED |
| F-04 | `401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED` on Gemini calls | Wrong key type passed (an OAuth token or a legacy Developer API key instead of a Vertex Express key) | Check the stored VERTEX_GEMINI_KEY prefix; a valid key starts with AQ. | §G-04 | CONFIRMED |
| F-05 | qdrant upsert fails because embeddings are 3072-dimensional | An embed call omitted output_dimensionality so it defaulted to 3072 while the qdrant collection is smaller | Inspect the embed call site for EmbedContentConfig(output_dimensionality=...) | §G-05 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: OAuth Consent Screen
  root_cause: The OAuth consent screen for aimarket-prod is External/Testing, so Gmail refresh tokens expire after 7 days and break briefings, the drop pipeline, and draft sending.
  repair_entry_point: GCP Console OAuth consent screen (project aimarket-prod)
  change_pattern: Set User Type to Internal (use MAKE INTERNAL or edit), then re-issue Gmail tokens via E-02 (setup_gmail_auth.py then update gmail_tokens then redeploy). Only ai.market Workspace users (max@ai.market, ally@ai.market) can authorize.
  rollback_procedure: None required; Internal is the only correct setting. If re-issuance fails, retain the prior token rows until new tokens are confirmed written.
  integrity_check: Confirm User Type reads Internal and gmail_tokens rows for both addresses show a current updated_at, then confirm the next briefing run succeeds.
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
  root_cause: A non-Vertex key (OAuth token or legacy Developer API key) is stored for Gemini auth.
  repair_entry_point: GCP Console Credentials API Keys, scoped to the Vertex AI API
  change_pattern: Re-create the API key scoped to the Vertex AI API so the prefix is AQ., store it as VERTEX_GEMINI_KEY in Infisical. If AG dispatches 401, sync VERTEX_API_KEY to match and restart ag_server.
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
```

## §H. Evolve

### §H.1 Invariants

- The OAuth consent screen for aimarket-prod MUST be User Type Internal, or Gmail refresh tokens expire after 7 days.
- `VERTEX_GEMINI_KEY` is the canonical uppercase secret name for the Vertex Express API key; no aliases are permitted in production code.
- Every Gemini embed call MUST pass `output_dimensionality=settings.LLM_EMBEDDING_DIMENSIONS`.
- The gcloud interactive login can only be performed by Max in a browser; it is never headless.

### §H.2 BREAKING predicates

- Changing the OAuth consent screen away from Internal is BREAKING because refresh tokens begin expiring.
- Renaming or aliasing `VERTEX_GEMINI_KEY` is BREAKING because Pydantic case-sensitive settings will fail to load the key.
- Moving Gemini auth back to service-account ADC is BREAKING because the stored SA private key is rejected by GCP.

### §H.3 REVIEW predicates

- Rotating the Vertex Express API key requires REVIEW because AG reads a separate `VERTEX_API_KEY` that must be synced.
- Changing the Pub/Sub gmail-push topic or subscription target requires REVIEW because it reroutes the drop pipeline.

### §H.4 SAFE predicates

- Verifying auth state via the read-only gcloud and Infisical checks is SAFE.
- Re-issuing Gmail tokens while the consent screen is already Internal is SAFE.

### §H.5 Boundary definitions

#### module

The module boundary is the GCP authentication surface used by ai.market: Gmail OAuth, the gcloud CLI session, Pub/Sub wiring, and the Vertex Gemini API key.

#### public contract

The public contract is the set of credentials and endpoints the backend depends on: valid gmail_tokens rows, an active gcloud session, the gmail-push subscription delivering to the webhook, and a valid VERTEX_GEMINI_KEY.

#### runtime dependency

A runtime dependency is any external system required at run time: GCP OAuth, the Gmail API, GCP Pub/Sub, the Vertex AI API, Railway Postgres for gmail_tokens, and Infisical for secret values.

#### config default

A config default is any default identity or scope value: the active gcloud account max@ai.market, the project aimarket-prod, and the canonical secret name VERTEX_GEMINI_KEY.

### §H.6 Adjudication

When two operators classify a GCP-auth change differently, use the more restrictive class and record the dispute. Max resolves any classification dispute that alters identity, project scope, or the consent-screen setting.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §D]
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
    refs: [E-02, §C]
    scenario: |
      id: E-02. trigger: Gmail jobs stopped because refresh tokens expired. tool_or_endpoint: setup_gmail_auth.py then update gmail_tokens via railway connect Postgres then railway redeploy. expected_success: fresh tokens for max@ai.market and ally@ai.market and the Gmail watch renewed. next_step_failure: apply G-01 to fix the consent screen first.
    expected_answers:
      - kind: human_action
        verb: reissue
        object: Gmail refresh tokens
        target: setup script then gmail_tokens update then redeploy
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03, §C]
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
      id: F-01. trigger: morning briefing or drop pipeline silently stopped. verification: check the OAuth consent screen User Type and gmail_tokens age. expected_success: classify as expired Gmail refresh token from a non-Internal consent screen. next_step_success: apply G-01.
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
      id: G-01. trigger: consent screen is External so Gmail tokens keep expiring. change_pattern: set User Type to Internal then re-issue tokens via E-02. expected_success: User Type Internal and fresh tokens for both addresses. next_step_failure: retain prior token rows until new tokens are confirmed.
    expected_answers:
      - kind: human_action
        verb: set
        object: OAuth consent screen User Type
        target: Internal then re-issue tokens
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
    refs: [§H]
    scenario: |
      id: H-01. trigger: a proposal would switch the OAuth consent screen away from Internal. expected_success: classify as BREAKING because refresh tokens begin expiring. next_step_success: block the change and keep Internal.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [§H]
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

## §J. Lifecycle

Lifecycle metadata records the Gate 2 conformance refresh state for this runbook.

```yaml lifecycle
last_refresh_session: S749
last_refresh_commit: 63abe32
last_refresh_date: 2026-06-01T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - OAuth consent-screen requirement or Gmail token flow changes
  - Vertex Gemini auth model or canonical key name changes
  - Pub/Sub gmail-push topic or subscription target changes
  - gcloud account or project defaults change
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-06-01T00:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S749 / 2026-06-01T00:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
