---
title: Qdrant — Vector Database (hosting, auth, backups)
owner: sysadmin
last_verified: '2026-10-01'
aliases: []
error_signatures:
- unauth returns 200
- backend qdrant calls 401 after rotation
- HTTP 401
- Qdrant redeploy digest differs
---

# Qdrant — Vector Database (hosting, auth, backups)

## Overview


## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Qdrant hosting (Railway service in ai-market project) | SHIPPED | `railway://ai-market/Qdrant` | manual curl | 2026-06-30 |
| API-key authentication (REST/gRPC require api-key header) | SHIPPED | `QDRANT__SERVICE__API_KEY` | unauth /collections returns 401; with-key returns 200 | 2026-06-30 |
| Backend authenticates with the key | SHIPPED | `app/core/qdrant_client.py` | backend /backup-status qdrant collection_source=qdrant_api | 2026-06-30 |
| Per-collection S3 snapshot backups (all live collections) | SHIPPED | `scripts/backup_qdrant.py` | watchdog + /backup-status; S1081: all 4 collections verified backed up (action_logs, knowledge_base, knowledge_base_v2, listings) | 2026-06-30 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Qdrant service | Railway svc 6f7211f0; public https://qdrant-production-470c.up.railway.app, internal RAILWAY_SERVICE_QDRANT_URL :6333 | Railway volume | backend, allAI embedding pipeline | API-key enforced since S1081 |
| Backend Qdrant client | app/core/qdrant_client.py | n/a | Qdrant | reads QDRANT_HOST, QDRANT_API_KEY from env |
| Backup watchdog | runbooks/scripts/s3_backup_watchdog.sh (Koskadeux launchd com.aimarket.s3-backup-watchdog) | S3 aimarket-backups-prod/qdrant/ | Telegram alert | checks qdrant/ prefix freshness |
| SysAdmin backup monitor | app/allai/agents/sysadmin/backup_monitor.py _evaluate_s3_qdrant_collections | Redis history; S3 | /backup-status endpoint | cross-checks live collection list vs S3 snapshots |

### Architecture & interactions.1 Source of truth vs derived index (READ FIRST)

Qdrant stores **derived** data only. It is NOT a system of record. Every collection is an embedding index rebuilt from Postgres:

- `listings` — semantic-search + matchmaking index of marketplace listings. Source of truth is the Postgres `listings` table (`app/models/marketplace.py` -> `class Listing`). Rebuilt by `POST /api/v1/search/reindex` (admin/system; `listing_search_service.reindex_all()` re-embeds every published listing).
- `knowledge_base`, `knowledge_base_v2`, `action_logs` — likewise re-ingestable from their Postgres / source data.

**Implication for backups and DR:** losing a Qdrant collection is a *reindex/re-embed window*, not data loss. The S3 snapshots here are a recovery-time **convenience** (they skip the re-embedding cost and the rebuild window), NOT source-of-truth protection. The data that MUST be backed up is Postgres (priority-1; see `backup-and-recovery.md`). This matches the canonical backup-scope rule "Qdrant excluded (re-ingestable)" in `config:resource-registry`. Treat the Qdrant backup-coverage monitor as a convenience signal, not a data-loss alarm.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| SysAdmin | report backup freshness | backup_status / backup_verify skills | internal API key | COMPLETE |
| SysAdmin | run qdrant snapshot | runbooks/scripts/backup_qdrant.py (Koskadeux) | AWS backup-writer + Qdrant api-key | PARTIAL — only knowledge_base today; extend to all live collections per Repair G-02 |

## How to operate

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
- id: E-04
  trigger: Any Qdrant restart or redeploy (variable change, config change)
  pre_conditions:
    - Peers told; backend search falls back to SQL while Qdrant restarts (one replica plus a volume, so the old container stops first; knowledge_base_v2 holds about 1.7M points and loads for about 2 minutes, and the public domain returns 502 meanwhile)
    - Record the running deployment's meta.imageDigest and GET / version
  tool_or_endpoint: Railway GraphQL serviceInstanceDeployV2(serviceId, environmentId) ONLY; read serviceInstance(source.image) and the new deployment's meta.image and meta.imageDigest
  notes: |
    Rehearsed S1786 on a scratch image service (receipt koskadeux-state/s1786/step5/image-rehearsal.json):
    serviceInstanceUpdate(source.image) alone does not deploy.
    serviceInstanceRedeploy reuses the previous deployment's image reference, so a just-changed source.image is ignored.
    serviceInstanceDeployV2 deploys the instance's current source.image.
    A variable change without skipDeploys auto-deploys with the previous deployment's image reference.
    variableDelete did not deploy within 120 s; follow it with serviceInstanceDeployV2.
    Production deployment f60cd9f5 still carries the untagged reference qdrant/qdrant. Until a serviceInstanceDeployV2 replaces it, serviceInstanceRedeploy and variable-triggered deploys pull the newest release.
  argument_sourcing:
    arg: the service instance source.image, which must be qdrant/qdrant@sha256:<digest> (since S1786 the pin is 1.19.1, sha256:12364fe851b9f17356fc88189fc06d1b521262e04659ec7345975b00c9246a10)
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: new deployment SUCCESS, meta.imageDigest equals the pinned digest, GET / version unchanged, every collection green with unchanged points_count
    verification: compare digest, version and per-collection points_count before and after
  expected_failures:
    - signature: Qdrant redeploy digest differs
      cause: serviceInstanceRedeploy reuses the previous deployment's image reference and ignores a just-changed source.image. Before S1786 the deployment image was untagged qdrant/qdrant, so a redeploy pulled the newest release (S1786, 2026-10-01, 1.18.2 to 1.19.1).
  next_step_success: done
  next_step_failure: G-03
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Backend embedding/search fails with 401 | backend QDRANT_API_KEY missing or mismatched vs Qdrant service key | compare Infisical/Railway backend QDRANT_API_KEY vs Qdrant QDRANT__SERVICE__API_KEY | G-01 | CONFIRMED |
| F-02 | /backup-status qdrant status=corrupt, collections show no_backups | live collection has no S3 snapshot prefix (real backup gap) | read collection_results in /backup-status | G-02 | CONFIRMED |
| F-03 | unauth /collections returns 200 | auth not enforced (key unset or stale deploy) | curl without api-key header | G-01 | CONFIRMED |
| F-04 | Qdrant runs a different version after a redeploy | redeploy reused the untagged image reference and pulled a newer release | compare the latest deployment's meta.imageDigest and GET / version with the record taken before the restart | G-03 | CONFIRMED |

## Repair

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
  root_cause: RESOLVED S1081 — the live job (runbooks/scripts/backup_qdrant.py) now enumerates all live collections; previously knowledge_base-only
  repair_entry_point: runbooks/scripts/backup_qdrant.py list_collections()
  change_pattern: enumerate live collections from the Qdrant API (with api-key) and snapshot each to s3 under qdrant/{collection}/
  rollback_procedure: n/a (additive). If a collection is lost entirely, canonical recovery is a REBUILD FROM POSTGRES, not the S3 snapshot — listings rebuild via POST /api/v1/search/reindex (reindex_all). The S3 snapshot only saves the re-embed window.
  integrity_check: /backup-status qdrant aggregate=ok (every live collection has a fresh prefix)
- id: G-03
  symptom_ref: F-04
  component_ref: Qdrant service
  root_cause: serviceInstanceRedeploy does not apply a just-changed source.image; it redeploys the previous image reference
  repair_entry_point: Railway GraphQL serviceInstanceUpdate(source.image) on svc 6f7211f0
  change_pattern: Do not roll back to the older version. Qdrant does not support opening storage with an older release after a newer one has opened it. Check health first (GET / version, every collection green, points_count matches the record). Then set source.image to qdrant/qdrant@<running digest> with no deploy. This is containment only: the running deployment still carries the old image reference (untagged after S1786), and serviceInstanceRedeploy or a variable-triggered deploy would reuse it and could pull another release. The exposure stays open until the next restart goes through E-04 (serviceInstanceDeployV2) and that deployment's meta.image reads qdrant/qdrant@<digest>. Record an Event and correct this page.
  rollback_procedure: restore collections from S3 snapshots or rebuild from Postgres (G-02) only if storage is damaged
  integrity_check: E-03 plus every collection green and the instance source.image equal to the running digest; closed only when a later E-04 deployment shows meta.image pinned to the digest
```

## Changes and maintenance

### H.1 Invariants

- Qdrant is a DERIVED index; Postgres is the source of truth. Never treat a Qdrant collection as primary data; any collection can be rebuilt (listings via POST /api/v1/search/reindex).
- Qdrant MUST require an API key (no anonymous access). The key lives in Infisical (canonical) and is mirrored to the backend service env and the Qdrant service env.
- The backend's key and the Qdrant service's key MUST be identical, or the backend cannot connect.
- Rotation order is ALWAYS backend-first, Qdrant-second.

### H.2 BREAKING predicates

- Removing QDRANT__SERVICE__API_KEY from the Qdrant service (re-opens the DB to the internet).
- Setting different keys on the backend vs the Qdrant service.

### H.3 REVIEW predicates

- Changing QDRANT_HOST or the public domain.
- Adding a new Qdrant collection (must be added to the backup job — see G-02).

### H.4 SAFE predicates

- Rotating the key via E-02 in a maintenance window.
- Read-only auth checks (E-01).

### H.5 Boundary definitions

#### module

app/core/qdrant_client.py (backend client); app/allai/agents/sysadmin/backup_monitor.py (monitor); scripts/backup_qdrant_s3.py (snapshot job).

#### public contract

Qdrant REST/gRPC require the api-key header. Backend reads QDRANT_API_KEY from env (Pydantic Settings, case-sensitive).

#### runtime dependency

Upstream source of truth: Postgres (listings table etc.) — Qdrant is rebuilt from it. Infra: Railway Qdrant service + volume; AWS S3 aimarket-backups-prod for snapshots; Infisical for the key.

#### config default

Qdrant default is NO auth — this is overridden by QDRANT__SERVICE__API_KEY. Backend QDRANT_API_KEY default is None; monitor _qdrant_headers tolerates an unset key (sends keyless).

### H.6 Adjudication

Auth/key changes are security changes: unanimous Council + Max GO per CORE, except an emergency re-open rollback (G-01 rollback) which may be done immediately to restore service, then reviewed.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - How to operate E-01
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
      - How to operate E-01
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
      - How to operate E-02
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
      - When it breaks F-01
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
      - When it breaks F-02
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
      - When it breaks F-03
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
      - Repair G-01
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
      - Repair G-02
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
      - Changes and maintenance H.1
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
      - Changes and maintenance H.2
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
      - When it breaks F-02
      - Repair G-02
    scenario: The dashboard reads "corrupt" but Qdrant responds normally; decide whether this is a backup-coverage gap or a Qdrant outage before acting.
    expected_answers:
      - kind: classification
        tool: backup-status
        argument_keys:
          - collection_results
          - status
    weight: 0.0909
```

### Acceptance criteria.1 Weight Justification

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

## Maintenance

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
first_staleness_detected_at: null
```
