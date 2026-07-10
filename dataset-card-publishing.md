---
system_name: dataset-card-publishing
purpose_sentence: Publish metadata dataset cards for ai.market listings to HuggingFace, Kaggle, and data.world so LLM agents and buyers discover listings everywhere.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Outbound dataset-card publishing channels (HuggingFace, Kaggle, data.world) in ai-market-backend — job enqueue, card rendering, provider API contracts, URL persistence, JSON-LD sameAs. NOT the source of truth for general SEO infrastructure (Search Console, sitemaps, llms.txt — see seo-infrastructure.md) or disclosure snapshot approval flows.
linter_version: 1.0.0
---

# Dataset-Card Publishing (HuggingFace / Kaggle / data.world)

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

Every published or updated ai.market listing gets a metadata dataset card pushed to external data platforms, each carrying a backlink to `https://ai.market/listings/{slug}`. This is core AI-discoverability work (CORE §2, ai.market pillar): buyers asking an LLM anywhere in the world should surface our customers' listings. Cards are metadata-only by default; actual sample rows publish only to HuggingFace and only with a seller-approved disclosure snapshot.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| HF metadata-only card publish (no snapshot required) | SHIPPED | `app/services/huggingface_service.py:publish_dataset_card_for_search_submission` | unit tests (backend 26ac843e) | 2026-07-09 |
| HF row-backed sample publish (seller-approved snapshot, exact version) | SHIPPED | `app/services/huggingface_service.py:publish_dataset_card_for_search_submission` | unit tests | 2026-07-09 |
| HF stale-data-file sweep on metadata-only republish | SHIPPED | `app/services/huggingface_service.py:_remove_stale_hf_data_files` | unit tests | 2026-07-09 |
| Kaggle metadata card publish (blob-token contract) | BROKEN | `app/services/kaggle_service.py:_upsert_kaggle_dataset` | tests target old multipart contract | 2026-07-10 |
| data.world metadata card publish | PARTIAL | `app/services/dataworld_service.py:publish_dataset_card_for_search_submission` | unit tests only; never live-verified (no DATAWORLD_API_TOKEN) | 2026-07-10 |
| Job enqueue on listing published/updated events | SHIPPED | `app/services/search_submission_service.py:_append_metadata_card_job_if_needed` | unit tests | 2026-07-09 |
| Idle-republish guard (card-hash + disclosure_version match) | SHIPPED | `app/services/search_submission_service.py:_append_huggingface_job_if_needed` | unit tests | 2026-07-09 |
| source_delivery URL persistence + JSON-LD sameAs regen | SHIPPED | `app/services/huggingface_service.py:publish_dataset_card_for_search_submission` | unit tests | 2026-07-09 |

Kaggle row: BROKEN is ticket T-2026-000207 — shipped code posts multipart form-data; the live Kaggle API requires the blob-token JSON flow (§G-01). The canonical eolymp card was published manually via the proven contract and is live; the app path 400s until the fix deploys.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Submission orchestrator | `app/services/search_submission_service.py:handle_listing_event` | search_submission_jobs table (provider, event_type, status, disclosure_version, dedup_hour_utc, last_error) | listing published/updated events; scheduler drains pending jobs ~2 min | Enqueues one job per enabled provider per event; idle guard skips updated events when disclosure_version AND rendered card hash match the last succeeded job for that provider (hashes live as JSON in that job's last_error — known semantic wrinkle, GLM LOW) |
| HuggingFace channel | `app/services/huggingface_service.py:publish_dataset_card_for_search_submission` | Listing.source_delivery.huggingface_url; HF repo ai-market/{slug}-sample | HF Hub API (HUGGINGFACE_TOKEN); DisclosureSnapshotService.get_snapshot_for_hf_card | Metadata-only branch is structurally README-only and sweeps stale data files; row branch pushes only seller-approved rows for the exact disclosure version; on success persists URL and regenerates JSON-LD sameAs (regen failure logs, does not fail job); 429/5xx retried, 400/401/403/404 terminal |
| Kaggle channel | `app/services/kaggle_service.py:_upsert_kaggle_dataset` | Listing.source_delivery.kaggle_url | kaggle.com/api/v1 (KAGGLE_USERNAME + KAGGLE_API_TOKEN, Bearer-only) | Metadata-only PERIOD — no row path exists in code. Proven contract: POST /blobs/upload (Bearer, JSON) → PUT bytes to createUrl (no auth) → POST /datasets/create/new or /datasets/create/version/{owner}/{slug} (Bearer, JSON, title ≤50 chars); HTTP 200 with body.status=="Error" is a FAILURE |
| data.world channel | `app/services/dataworld_service.py:publish_dataset_card_for_search_submission` | Listing.source_delivery.dataworld_url | api.data.world/v0 (DATAWORLD_API_TOKEN); GET /v0/user resolves owner slug | Metadata-only PERIOD. Creates/updates an OPEN dataset with the card as summary. Token does not exist yet — flag off; expect contract surprises, verify with curl incrementally before enabling |
| Disclosure snapshots | `app/services/disclosure_snapshot_service.py:get_snapshot_for_hf_card` | disclosure snapshot tables | HF channel only | Returns metadata-only snapshots too; strict get_snapshot_for_hf keeps its 409 for no-row snapshots |
| Config flags | `app/core/config.py` | HUGGINGFACE_SUBMISSION_ENABLED, KAGGLE_SUBMISSION_ENABLED, DATAWORLD_SUBMISSION_ENABLED (all default False) | Railway prod env; Infisical prod | Flipping a flag in prod is a Max-only action |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan/mars | Manually enqueue a card job | psql via scripts/test-db-dsn.sh (INSERT into search_submission_jobs, see §E-02) | prod DB DSN | COMPLETE |
| vulcan/mars | Verify a live card / read job errors | curl or web fetch of card URL; psql SELECT on search_submission_jobs | prod DB DSN (read) | COMPLETE |
| vulcan/mars | Check channel env vars and flags | railway variables --json (source ~/bin/railway-env.sh) | RAILWAY_API_TOKEN | COMPLETE |
| MP (Codex) | Fix provider contract code | council_request mode=build (per CORE §4 build routing) | repo write via worktree branch | COMPLETE |
| SysAdmin agent | Rotate provider tokens in Infisical | sysadmin_request | Infisical prod | PARTIAL — rotation runbook step exists but end-to-end rotation of KAGGLE_API_TOKEN not yet exercised; close by performing one audited rotation (pending: S1164 token traveled through chat) |
| Max | Flip *_SUBMISSION_ENABLED flags in prod; supply new provider tokens | Railway dashboard / Infisical | owner | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Listing published or updated on ai.market (automatic customer-serving path)
  pre_conditions:
    - listing_status_published
    - provider_flag_enabled_in_railway_prod
  tool_or_endpoint: "automatic: SearchSubmissionService.handle_listing_event enqueues search_submission_jobs rows; scheduler drains ~2 min"
  argument_sourcing:
    listing_id: from the listing event payload
    provider: one job per enabled provider flag (§C Config flags)
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: dedup_hour_utc + provider + listing; idle guard additionally skips updated events when disclosure_version and rendered card hash match the last succeeded job
  expected_success:
    shape: job row status pending → succeeded; Listing.source_delivery.{provider}_url persisted; JSON-LD sameAs includes the card URL
    verification: fetch the card URL (e.g. huggingface.co/datasets/ai-market/{slug}-sample) and psql SELECT source_delivery from listings
  expected_failures:
    - signature: job status dead with 401/403 in last_error
      cause: provider token missing/rotated/wrong scheme (Kaggle KGAT tokens are Bearer-only; Basic returns 401)
    - signature: job status dead with 400 in last_error (Kaggle)
      cause: wrong API contract (multipart instead of blob-token JSON) — T-2026-000207
  next_step_success: none — steady state
  next_step_failure: go to §F symptom index
- id: E-02
  trigger: Operator needs to (re)publish a card for one listing outside the event path
  pre_conditions:
    - provider_flag_enabled_in_railway_prod
    - listing_exists_and_published
  tool_or_endpoint: "psql via scripts/test-db-dsn.sh: INSERT INTO search_submission_jobs (provider, dataset_card payload, event_type, status, disclosure_version, dedup_hour_utc) VALUES ('<provider>', ..., 'updated', 'pending', NULL, date_trunc('hour', now() at time zone 'utc'))"
  argument_sourcing:
    provider: one of huggingface | kaggle | dataworld
    listing_id: psql SELECT id FROM listings WHERE slug or title matches
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: dedup_hour_utc — a second insert in the same UTC hour for the same provider/listing is deduped
  expected_success:
    shape: scheduler picks the row up within ~2 minutes; status pending → succeeded
    verification: psql SELECT status, last_error FROM search_submission_jobs ORDER BY created_at DESC; then fetch the live card URL
  expected_failures:
    - signature: row stays pending > 10 min
      cause: scheduler not draining — check backend deploy health on Railway
    - signature: status dead
      cause: read last_error verbatim; route via §F
  next_step_success: confirm source_delivery URL and JSON-LD sameAs persisted (E-01 verification)
  next_step_failure: §F, matching on the last_error signature
- id: E-03
  trigger: Bring a new provider channel live (e.g. data.world when the token arrives)
  pre_conditions:
    - provider_token_exists
    - max_approval_for_flag_flip
  tool_or_endpoint: "sequence: (1) store token in Infisical prod; (2) mirror to Railway backend env; (3) register in config:resource-registry secrets (state_request patch); (4) Max flips {PROVIDER}_SUBMISSION_ENABLED=true in Railway; (5) enqueue one job per §E-02; (6) live-verify the card"
  argument_sourcing:
    token: supplied by Max (never through chat if avoidable; rotate if it was)
    registry_key: config:resource-registry via state_request get, patch with expected_version
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: first job succeeds; card live at provider; source_delivery URL persisted
    verification: fetch card URL; psql check per E-01
  expected_failures:
    - signature: first job dead with 4xx
      cause: untested provider contract — verify each API step incrementally with curl BEFORE re-enqueueing (Kaggle precedent — the documented contract was wrong)
  next_step_success: update §B row status and Last Verified; refresh §J
  next_step_failure: disable flag, fix contract per §G-01 pattern, retry
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | No card jobs appear after listing publish/update | Provider flag unset/false in Railway prod | source ~/bin/railway-env.sh; railway variables --json, grep the *_SUBMISSION_ENABLED flag | §G-03 | CONFIRMED |
| F-02 | Job dead with 401/403 | Token missing, rotated, or wrong auth scheme — Kaggle KGAT tokens are Bearer-only, Basic returns 401 | Read job.last_error; curl the provider auth-cheap endpoint with the prod token (Kaggle: GET api/v1 datasets list with Bearer header) | §G-03 | CONFIRMED |
| F-03 | Kaggle job dead with 400 Bad Request on datasets/create/new | Shipped multipart contract is wrong; live API requires blob-token JSON flow (T-2026-000207) | Read last_error; reproduce with curl: multipart POST returns 400, blob-token flow returns 200 | §G-01 | CONFIRMED |
| F-04 | Provider returned HTTP 200 but no card appears | Kaggle returns HTTP 200 with body.status=="Error" on validation failures (e.g. title > 50 chars); code trusting HTTP status marks the job succeeded | Read the stored response body / last_error; retry the create call with curl and inspect body.status and body.error | §G-01 | CONFIRMED |
| F-05 | Card stale after a listing edit | Idle-republish guard matched: disclosure_version AND card hash equal the last succeeded job; or no updated event fired | psql: read the last succeeded job for the provider — the card hash JSON lives in that job's last_error; confirm an updated submission event exists for the edit | §G-02 | CONFIRMED |
| F-06 | Withdrawn sample rows still visible on HF | Metadata-only republish did not run, or list_repo_files unavailable so fallback swept only data/train/test/validation folders (stray root files survive — GLM LOW) | Fetch the HF repo file list; compare against README-only expectation | §G-02 | CONFIRMED |
| F-07 | Remote card exists but Listing.source_delivery URL / JSON-LD sameAs missing | Persist step failed after remote creation (orphan risk, GLM LOW parity finding), or the card was published manually bypassing the app (eolymp Kaggle precedent) | psql SELECT source_delivery FROM listings; fetch the live card URL to confirm it exists remotely | §G-02 | CONFIRMED |

Log locations: backend logs on Railway (service ai-market-backend); job-level errors in search_submission_jobs.last_error (read it verbatim first — dev-tickets.md §F rule).

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-03
  component_ref: Kaggle channel
  root_cause: Provider API contract drift — shipped code speaks a contract the live API rejects (Kaggle multipart vs blob-token JSON; HTTP-200-with-body-Error semantics)
  repair_entry_point: app/services/kaggle_service.py:_upsert_kaggle_dataset
  change_pattern: Replace the transport with the live-proven flow — (1) POST /api/v1/blobs/upload Bearer JSON {type, name, contentLength} → {token, createUrl}; (2) PUT bytes to createUrl with no Kaggle auth header; (3) POST /datasets/create/new (or create/version/{owner}/{slug} for existing datasets) Bearer JSON with title hard-truncated to 50 chars and files [{token}]; treat HTTP-200 body.status=="Error" as failure surfacing body.error. Route via MP build (dev-tickets.md §C), reviewer ≠ builder, push branch, merge after review, Railway deploy, then re-enqueue per §E-02 and live-verify (Gate 4)
  rollback_procedure: git revert the merge commit on ai-market-backend main and redeploy; the channel returns to its prior (broken-but-inert) state — jobs go dead, no customer data at risk
  integrity_check: Re-enqueued job for a known listing reaches succeeded; card URL fetches 200; source_delivery.{provider}_url and JSON-LD sameAs persisted; unit tests mock all transport calls including the version path and body-Error case
- id: G-02
  symptom_ref: F-07
  component_ref: Submission orchestrator
  root_cause: URL persistence runs after remote creation; a persist failure (or a manual out-of-band publish) leaves a live remote card with no local reference
  repair_entry_point: app/services/search_submission_service.py:handle_listing_event
  change_pattern: Re-enqueue an updated-event job per §E-02 — the provider upsert path must take the existing-dataset/version branch (idempotent against a live remote card) and re-persist source_delivery URL + JSON-LD sameAs. If the provider path cannot find the existing dataset, reconcile using the remote URL recorded in the failed job's last_error
  rollback_procedure: none needed — re-enqueue is additive; a failed reconciliation job goes dead without changing state
  integrity_check: psql shows source_delivery URL populated; listing JSON-LD sameAs contains the card URL; remote card content matches the current rendered card
- id: G-03
  symptom_ref: F-02
  component_ref: Config flags
  root_cause: Provider token absent, expired, rotated without mirroring, or used with the wrong auth scheme
  repair_entry_point: app/core/config.py
  change_pattern: Rotate/set the token in Infisical prod FIRST (sole secret store, CORE §3), mirror to Railway backend env, update config:resource-registry secrets entry via state_request patch with expected_version; verify with a curl call using the exact auth scheme (Kaggle KGAT = Bearer only); then re-enqueue the dead job per §E-02
  rollback_procedure: restore the previous token value in Infisical + Railway from the registry rotation note
  integrity_check: curl auth probe returns 200; re-enqueued job succeeds
```

## §H. Evolve

### §H.1 Invariants

- Kaggle and data.world channels are metadata-only PERIOD — no row-publishing code path exists and none may be added without a full Council gate (customer-data surface, unanimous).
- HF sample rows publish ONLY with a seller-approved disclosure snapshot (sample_decision=approved_rows, exact version). Hard line — do not relax (Max directive + unanimous Council, S1164).
- Raw customer data never touches ai.market infrastructure; cards carry public listing metadata and (HF only) seller-approved sample rows.
- Every card carries a backlink to the ai.market listing and feeds JSON-LD sameAs — AI-discoverability is the point (CORE §2).
- All provider secrets live in Infisical (mirrored to Railway env); no secrets in code or chat.
- Flipping a *_SUBMISSION_ENABLED flag in production is a Max-only action.

### §H.2 BREAKING predicates

- Adds any data-row publishing capability to Kaggle or data.world channels (violates §H.1).
- Publishes HF rows without an approved_rows disclosure snapshot for the exact version (violates §H.1).
- Removes or weakens the metadata-only sweep of stale HF data files.
- Changes the search_submission_jobs schema by removing a field or adding a required field without a default.

### §H.3 REVIEW predicates

- Adds a new provider channel (new module or provider class on the submission surface).
- Changes a provider API contract implementation (transport, auth scheme, endpoint shape).
- Changes a config default in app/core/config.py for any *_SUBMISSION_* setting.
- Adds a runtime dependency for a provider SDK.

### §H.4 SAFE predicates

- Bugfix within existing provider semantics (e.g. correcting an error-classification branch).
- Card template copy/wording changes that keep metadata-only content.
- Test additions; documentation updates.

### §H.5 Boundary definitions

#### module

Immediate subdirectory of ai-market-backend's app/ source root (app/services/, app/api/, app/models/, app/core/). tests/ and migrations/ are peer trees, not modules.

#### public contract

The search_submission_jobs table shape consumed by the scheduler; provider card URL fields in Listing.source_delivery; listing JSON-LD served publicly.

#### runtime dependency

An entry in ai-market-backend requirements.txt / pyproject [project.dependencies]. Dev/test extras are not runtime dependencies.

#### config default

A value shipping in app/core/config.py. Railway env overrides and feature flags are not config defaults.

### §H.6 Adjudication

If two agents classify a change differently, the more restrictive classification wins. Unresolvable disputes escalate to Max; the ruling is appended to §H.1 as a per-system clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - E-02
    scenario: A seller edited their listing description yesterday but the Kaggle card still shows the old text, and no updated job exists for the listing. Republish the card.
    expected_answers:
      - kind: tool_call
        tool: psql_insert_search_submission_job
        argument_keys:
          - provider
          - event_type
          - status
          - dedup_hour_utc
    weight: 0.0909090909
  - id: I-02
    type: operate
    refs:
      - E-03
    scenario: Max has just supplied DATAWORLD_API_TOKEN. What is the first action to bring the data.world channel live?
    expected_answers:
      - kind: human_action
        verb: store
        object: provider token
        target: Infisical prod (then mirror to Railway backend env)
      - kind: tool_call
        tool: infisical_secret_set
        argument_keys:
          - key
          - environment
    weight: 0.0909090909
  - id: I-03
    type: operate
    refs:
      - E-01
    scenario: A listing was just published with HUGGINGFACE_SUBMISSION_ENABLED=true. How do you verify the card shipped correctly?
    expected_answers:
      - kind: tool_call
        tool: fetch_card_url_and_psql_check_source_delivery
        argument_keys:
          - card_url
    weight: 0.0909090909
  - id: I-04
    type: isolate
    refs:
      - F-02
    scenario: A kaggle job is dead and last_error shows 401 Unauthorized. What is the first verification step?
    expected_answers:
      - kind: tool_call
        tool: curl_kaggle_auth_probe_bearer
        argument_keys:
          - authorization_header
    weight: 0.0909090909
  - id: I-05
    type: isolate
    refs:
      - F-05
    scenario: A seller says their HF card is stale after an edit, but the newest HF job succeeded an hour before the edit. Where do you look to determine whether the idle-republish guard suppressed the republish?
    expected_answers:
      - kind: tool_call
        tool: psql_select_last_succeeded_job_last_error
        argument_keys:
          - provider
    weight: 0.0909090909
  - id: I-06
    type: isolate
    refs:
      - F-04
    scenario: The Kaggle create/new call logged HTTP 200 but no dataset exists on kaggle.com. What was missed?
    expected_answers:
      - kind: classification
        verdict: response body.status=="Error" was not checked — HTTP 200 does not mean success on this API
    weight: 0.0909090909
  - id: I-07
    type: repair
    refs:
      - G-01
    scenario: Kaggle publishes 400 with the multipart contract. Describe the repair path.
    expected_answers:
      - kind: human_action
        verb: dispatch
        object: MP build replacing the transport with the blob-token flow (blobs/upload, PUT bytes, create/new or create/version), 50-char title truncation, body.status Error handling; review, merge, deploy, re-enqueue, live-verify
        target: app/services/kaggle_service.py:_upsert_kaggle_dataset
    weight: 0.0909090909
  - id: I-08
    type: repair
    refs:
      - G-02
    scenario: The eolymp Kaggle card is live but listings.source_delivery.kaggle_url is NULL. Fix it.
    expected_answers:
      - kind: tool_call
        tool: psql_insert_search_submission_job
        argument_keys:
          - provider
          - event_type
    weight: 0.0909090909
  - id: I-09
    type: evolve
    refs:
      - §H.2
    scenario: A proposal adds seller-approved sample-row publishing to the data.world channel, mirroring the HF row branch. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.0909090909
  - id: I-10
    type: evolve
    refs:
      - §H.3
    scenario: A proposal changes the Kaggle auth implementation from Basic-fallback-first to Bearer-only, deleting the legacy KAGGLE_KEY path. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.0909090909
  - id: I-11
    type: ambiguous
    refs:
      - F-01
      - F-07
    scenario: Ambiguous — a listing shows no kaggle_url in source_delivery and you do not yet know whether any kaggle job ever ran. Name the correct first action set.
    expected_answers:
      - kind: tool_call
        tool: psql_select_search_submission_jobs_for_listing
        argument_keys:
          - provider
          - listing_id
      - kind: tool_call
        tool: railway_variables_check_flag
        argument_keys:
          - flag_name
    weight: 0.0909090909
```


## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1167
last_refresh_commit: 0e49b1b9
last_refresh_date: 2026-07-10T09:30:00Z
owner_agent: vulcan
refresh_triggers:
  - T-2026-000207 fix deployed (update §B Kaggle row to SHIPPED)
  - data.world channel goes live (update §B row, §D, §E-03 Last Verified)
  - any provider contract change merged
  - incident touching card publishing
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-10T09:30:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1167 / 2026-07-10T09:35:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
