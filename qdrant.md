---
system_name: qdrant
purpose_sentence: Qdrant is the vector database that stores ai.market embeddings (listings, knowledge base, action logs); this runbook covers its hosting, its API-key authentication, and its S3 backup coverage.
owner_agent: sysadmin
escalation_contact: Max (human operator)
lifecycle_ref: §J
authoritative_scope: The Railway-hosted Qdrant service in the ai-market project, its API-key auth, the backend's connection to it, and the per-collection S3 snapshot backups. NOT the embedding/inference pipeline (see allAI) nor the S3 backup transport (see backup-and-recovery.md).
linter_version: 1.0.0
---

# Qdrant — Vector Database (hosting, auth, backups)

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Qdrant hosting (Railway service in ai-market project) | SHIPPED | `railway://ai-market/Qdrant` | manual curl | 2026-06-30 |
| API-key authentication (REST/gRPC require api-key header) | SHIPPED | `QDRANT__SERVICE__API_KEY` | unauth /collections returns 401; with-key returns 200 | 2026-06-30 |
| Backend authenticates with the key | SHIPPED | `app/core/qdrant_client.py` | backend /backup-status qdrant collection_source=qdrant_api | 2026-06-30 |
| Per-collection S3 snapshot backups (only knowledge_base covered) | PARTIAL | `scripts/backup_qdrant_s3.py` | watchdog + /backup-status; S1081 gap: action_logs, knowledge_base_v2, listings UNBACKED | 2026-06-30 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Qdrant service | Railway svc 6f7211f0; public https://qdrant-production-470c.up.railway.app, internal RAILWAY_SERVICE_QDRANT_URL :6333 | Railway volume | backend, allAI embedding pipeline | API-key enforced since S1081 |
| Backend Qdrant client | app/core/qdrant_client.py | n/a | Qdrant | reads QDRANT_HOST, QDRANT_API_KEY from env |
| Backup watchdog | runbooks/scripts/s3_backup_watchdog.sh (Titan-1 launchd com.aimarket.s3-backup-watchdog) | S3 aimarket-backups-prod/qdrant/ | Telegram alert | checks qdrant/ prefix freshness |
| SysAdmin backup monitor | app/allai/agents/sysadmin/backup_monitor.py _evaluate_s3_qdrant_collections | Redis history; S3 | /backup-status endpoint | cross-checks live collection list vs S3 snapshots |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| SysAdmin | report backup freshness | backup_status / backup_verify skills | internal API key | COMPLETE |
| SysAdmin | run qdrant snapshot | scripts/backup_qdrant_s3.py (Titan-1) | AWS backup-writer + Qdrant api-key | PARTIAL — only knowledge_base today; extend to all live collections per §G G-02 |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Verify Qdrant is locked and the key works
  pre_conditions:
    - Have QDRANT_API_KEY from Infisical (project bd272d48, env prod)
  tool_or_endpoint: curl https://qdrant-production-470c.up.railway.app/collections
  argument_sourcing:
    arg: api-key header from Infisical QDRANT_API_KEY
  idempotency: IDEMPOTENT
  expected_success:
    shape: unauth request returns HTTP 401; request with api-key header returns HTTP 200 + collections list
    verification: compare both HTTP codes
  expected_failures:
    - signature: unauth returns 200
      cause: QDRANT__SERVICE__API_KEY not set on the Qdrant service, or service not redeployed
  next_step_success: done
  next_step_failure: re-apply G-01
- id: E-02
  trigger: Key compromise or scheduled rotation
  pre_conditions:
    - Maintenance window (brief Qdrant + backend restart)
  tool_or_endpoint: Railway variableUpsert + Infisical secrets raw API
  argument_sourcing:
    arg: new key = python secrets.token_urlsafe(48)
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: backend and Qdrant service both hold the new key; unauth 401, with-new-key 200
    verification: E-01 with the new key
  expected_failures:
    - signature: backend qdrant calls 401 after rotation
      cause: backend env/Infisical not updated before Qdrant enforced the new key
  next_step_success: done
  next_step_failure: G-01
- id: E-03
  trigger: List live Qdrant collections to confirm reachability with the key
  pre_conditions:
    - Have QDRANT_API_KEY from Infisical
  tool_or_endpoint: curl with api-key header against https://qdrant-production-470c.up.railway.app/collections
  argument_sourcing:
    arg: api-key header from Infisical QDRANT_API_KEY
  idempotency: IDEMPOTENT
  expected_success:
    shape: HTTP 200 with the JSON collections list
    verification: parse result.collections
  expected_failures:
    - signature: HTTP 401
      cause: wrong or missing api-key
  next_step_success: done
  next_step_failure: G-01
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Backend embedding/search fails with 401 | backend QDRANT_API_KEY missing or mismatched vs Qdrant service key | compare Infisical/Railway backend QDRANT_API_KEY vs Qdrant QDRANT__SERVICE__API_KEY | G-01 | CONFIRMED |
| F-02 | /backup-status qdrant status=corrupt, collections show no_backups | live collection has no S3 snapshot prefix (real backup gap) | read collection_results in /backup-status | G-02 | CONFIRMED |
| F-03 | unauth /collections returns 200 | auth not enforced (key unset or stale deploy) | curl without api-key header | G-01 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Qdrant service
  root_cause: key missing/mismatched between Qdrant service and backend
  repair_entry_point: Railway variableUpsert (QDRANT__SERVICE__API_KEY on svc 6f7211f0; QDRANT_API_KEY on backend svc 4a68ea36) + Infisical bd272d48
  change_pattern: set the SAME key on backend (env + Infisical) FIRST, redeploy backend, THEN set/redeploy Qdrant so the backend already authenticates when enforcement turns on
  rollback_procedure: remove QDRANT__SERVICE__API_KEY from the Qdrant service + redeploy to revert to open (emergency only)
  integrity_check: E-01 (unauth 401, with-key 200) + backend /backup-status collection_source=qdrant_api
- id: G-02
  symptom_ref: F-02
  component_ref: SysAdmin backup monitor
  root_cause: the qdrant snapshot job does not enumerate all live collections (only knowledge_base as of S1081)
  repair_entry_point: scripts/backup_qdrant_s3.py collection list
  change_pattern: enumerate live collections from the Qdrant API (with api-key) and snapshot each to s3://aimarket-backups-prod/qdrant/{collection}/
  rollback_procedure: n/a (additive)
  integrity_check: /backup-status qdrant aggregate=ok (every live collection has a fresh prefix)
```

## §H. Evolve

### §H.1 Invariants

- Qdrant MUST require an API key (no anonymous access). The key lives in Infisical (canonical) and is mirrored to the backend service env and the Qdrant service env.
- The backend's key and the Qdrant service's key MUST be identical, or the backend cannot connect.
- Rotation order is ALWAYS backend-first, Qdrant-second.

### §H.2 BREAKING predicates

- Removing QDRANT__SERVICE__API_KEY from the Qdrant service (re-opens the DB to the internet).
- Setting different keys on the backend vs the Qdrant service.

### §H.3 REVIEW predicates

- Changing QDRANT_HOST or the public domain.
- Adding a new Qdrant collection (must be added to the backup job — see G-02).

### §H.4 SAFE predicates

- Rotating the key via E-02 in a maintenance window.
- Read-only auth checks (E-01).

### §H.5 Boundary definitions

#### module

app/core/qdrant_client.py (backend client); app/allai/agents/sysadmin/backup_monitor.py (monitor); scripts/backup_qdrant_s3.py (snapshot job).

#### public contract

Qdrant REST/gRPC require the api-key header. Backend reads QDRANT_API_KEY from env (Pydantic Settings, case-sensitive).

#### runtime dependency

Railway Qdrant service + volume; AWS S3 aimarket-backups-prod for snapshots; Infisical for the key.

#### config default

Qdrant default is NO auth — this is overridden by QDRANT__SERVICE__API_KEY. Backend QDRANT_API_KEY default is None; monitor _qdrant_headers tolerates an unset key (sends keyless).

### §H.6 Adjudication

Auth/key changes are security changes: unanimous Council + Max GO per CORE, except an emergency re-open rollback (G-01 rollback) which may be done immediately to restore service, then reviewed.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - §E E-01
    scenario: Verify Qdrant rejects unauthenticated access on the public URL.
    expected_answers:
      - kind: tool_call
        tool: curl
        argument_keys:
          - url
    weight: 0.0909
  - id: I-02
    type: operate
    refs:
      - §E E-01
    scenario: Verify Qdrant accepts the collections request when the api-key header is supplied.
    expected_answers:
      - kind: tool_call
        tool: curl
        argument_keys:
          - url
          - api-key
    weight: 0.0909
  - id: I-03
    type: operate
    refs:
      - §E E-02
    scenario: Rotate the Qdrant API key during a maintenance window, backend-first.
    expected_answers:
      - kind: tool_call
        tool: railway-variableUpsert
        argument_keys:
          - serviceId
          - name
    weight: 0.0909
  - id: I-04
    type: isolate
    refs:
      - §F F-01
    scenario: Backend embedding calls return 401 after a key change; identify the mismatch.
    expected_answers:
      - kind: tool_call
        tool: infisical-vs-railway
        argument_keys:
          - QDRANT_API_KEY
    weight: 0.0909
  - id: I-05
    type: isolate
    refs:
      - §F F-02
    scenario: The backup dashboard shows a Qdrant collection with no S3 snapshot.
    expected_answers:
      - kind: tool_call
        tool: backup-status
        argument_keys:
          - collection_results
    weight: 0.0909
  - id: I-06
    type: isolate
    refs:
      - §F F-03
    scenario: An unauthenticated client still reads collections; determine why enforcement is off.
    expected_answers:
      - kind: tool_call
        tool: curl
        argument_keys:
          - url
    weight: 0.0909
  - id: I-07
    type: repair
    refs:
      - §G G-01
    scenario: Restore matched keys on backend and Qdrant after a 401 incident.
    expected_answers:
      - kind: tool_call
        tool: railway-variableUpsert
        argument_keys:
          - serviceId
          - name
    weight: 0.0909
  - id: I-08
    type: repair
    refs:
      - §G G-02
    scenario: Extend the snapshot job to back up every live collection.
    expected_answers:
      - kind: tool_call
        tool: backup_qdrant_s3
        argument_keys:
          - collections
    weight: 0.0909
  - id: I-09
    type: evolve
    refs:
      - §H §H.1
    scenario: Confirm the invariant that Qdrant never allows anonymous access.
    expected_answers:
      - kind: tool_call
        tool: curl
        argument_keys:
          - url
    weight: 0.0909
  - id: I-10
    type: evolve
    refs:
      - §H §H.2
    scenario: Confirm that removing QDRANT__SERVICE__API_KEY is treated as a BREAKING change.
    expected_answers:
      - kind: classification
        tool: review
        argument_keys:
          - predicate
    weight: 0.0909
  - id: I-11
    type: ambiguous
    refs:
      - §F F-02
      - §G G-02
    scenario: The dashboard reads "corrupt" but Qdrant responds normally; decide whether this is a backup-coverage gap or a Qdrant outage before acting.
    expected_answers:
      - kind: classification
        tool: backup-status
        argument_keys:
          - collection_results
          - status
    weight: 0.0909
```

### §I.1 Weight Justification

All scenarios carry near-equal weight (≈1/11); coverage breadth is valued uniformly for this small, security-critical surface. Per-scenario notes for the divergent (non-baseline) entries:

- I-01: unauthenticated rejection check; baseline weight.
- I-02: authenticated acceptance check; baseline weight.
- I-03: key rotation drill; baseline weight.
- I-04: backend-vs-Qdrant key mismatch is the highest-frequency auth fault; weighted with the baseline.
- I-05: backup-coverage gap detection; equal weight.
- I-06: enforcement-off detection; equal weight.
- I-07: key restoration repair; equal weight.
- I-08: backup-coverage repair; equal weight.
- I-09: anonymous-access invariant; equal weight.
- I-10: BREAKING-predicate recognition; equal weight.
- I-11: corrupt-vs-outage disambiguation; equal weight.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1081
last_refresh_commit: bbb4ec54c976
last_refresh_date: "2026-06-30"
owner_agent: sysadmin
refresh_triggers:
  - key rotation
  - new Qdrant collection added
  - backup coverage change
scheduled_cadence: 90d
last_harness_pass_rate: 0.0
last_harness_date: "2026-06-30"
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
retrofit: false
linter_version: 1.0.0
last_lint_run: S1081 / 2026-06-30T19:25:00Z
last_lint_result: WARN
trace_matrix_path: null
word_count_delta: null
```
