# BQ-BACKUP-RECOVERY-HARDENING-S1322 — Gate 1 Design Spec

## 0. Header

| Field | Value |
|---|---|
| BQ key | `build:bq-backup-recovery-hardening-s1322` |
| Status | Gate 1 R1 design artifact; production implementation prohibited by this commit |
| Authoring date | 2026-07-24 |
| Audit source | S1322 backup, restore, monitoring, storage, and runbook audit |
| Spec repository | `aidotmarket/runbooks` |
| Spec path | `specs/BQ-BACKUP-RECOVERY-HARDENING-S1322-GATE1.md` |
| Authoring branch | `build/s1322-backup-recovery-audit` |
| Production repositories | `aidotmarket/runbooks` and `aidotmarket/ai-market-backend` only as enumerated in §10 |
| S3 scope | `s3://aimarket-backups-prod`, account `948749907373`, region `eu-north-1` |
| Primary operator | Max |
| Design authority | Max explicitly authorized all S1322 recommendations on 2026-07-24 |

This document is the complete Gate 1 design. It resolves policy and safety decisions but does not change production code, credentials, schedules, IAM, S3 configuration, Railway services, Cloudflare permissions, local LaunchAgents, or stored backup objects. Gate 2 must turn this design into implementation chunks. Gate 3 must build and test those chunks. Gate 4 must produce the production evidence in §13.

### 0.1 Owner decisions locked by this Gate

The following are not open questions:

1. Retention is **35 daily days plus one verified monthly recovery point retained for 400 days**. The 400-day floor implements the approved 12-month policy with safety margin, so calendar boundaries may temporarily keep 13 or 14 monthly points.
2. Storage must fall materially after the already-authorized approximately 90% database cleanup. Reduction comes from smaller source dumps and bounded retention, never from excluding required tables from a dump.
3. Existing and future backup object versions are classified deterministically as `daily` or `monthly`.
4. S3 Versioning remains enabled.
5. S3 Object Lock remains **COMPLIANCE**. It must never be changed to Governance, suspended, bypassed, shortened, or removed.
6. No locked version is deleted. Lifecycle may act only after the applicable COMPLIANCE retain-until time; S3's asynchronous deletion timing may make physical retention longer than 35 or 400 days.
7. The already-rotated Telegram token is reconciled into the Titan-1 watchdog. It is **not rotated again** as part of this BQ.
8. The current Infisical backup must be decrypted and restored by a deterministic verifier on Titan-1. Max supplies the age identity locally from 1Password.
9. The age identity, decrypted archive, restored database contents, and secret values never enter chat, model context, network egress, logs, argv, crash dumps, or persistent disk.
10. Ollama is not part of the proof-producing path. If invoked, it receives only the redacted attestation defined in §6.8.
11. Telegram is accepted only with a real `sendMessage` response proving HTTP 2xx, JSON `ok=true`, the expected destination, and an integer `message_id`.
12. RPO and RTO are fixed by §4. No later implementation chunk may weaken them without a new owner decision and fresh Gate 1 review.

## 1. Problem statement and audited baseline

S1322 demonstrated that the latest main Postgres artifact and the latest `knowledge_base_v2` Qdrant artifact were hash-checked and restored successfully in isolation. It also found that recoverability claims were materially broader than the evidence:

- A failed Railway `pg_dump` deployment created an approximately 72-hour main-Postgres snapshot gap while copying `qdrant_sync_outbox`.
- The bucket contained 469 versions and 250,751,581,295 bytes, approximately 233.5 GiB. Main Postgres accounted for approximately 174.5 GiB and Qdrant approximately 58.9 GiB.
- Object Lock COMPLIANCE with a 35-day default, Versioning, SSE-S3, and Block Public Access were live, but no lifecycle policy existed.
- At least approximately 46.7 GiB was already older than 35 days.
- The current Infisical artifact had not been decrypted and restored during S1322.
- The Titan-1 watchdog detected failures but its Telegram call returned HTTP 401 and its shell function ignored the failed response.
- GitHub's six-hour threshold was incompatible with nightly backups and generated repeated urgent issues instead of one deduplicated incident.
- Backend task `app.tasks.scheduled.poll_backup_watchdog` existed but its Celery beat entry was disabled.
- Qdrant whole-prefix freshness could be satisfied by one fresh collection while another required collection was missing.
- Cloudflare exports uploaded a fresh-looking object even when required zone-settings calls returned HTTP 403.
- `git-mirrors/` was empty, the S3 `RESTORE-README.md` was stale, and the small AIM Data Railway Postgres database was absent from the recovery matrix.

The design must move the system from "some fresh objects and two successful restore drills" to a schedule-aware, integrity-checked, fail-loud recovery system with reproducible evidence.

## 2. Goals and non-goals

### 2.1 Goals

1. Meet the RPO/RTO contract in §4 for every required recovery source.
2. Produce one independently restorable, integrity-attested backup set per required source and UTC day.
3. Keep one verified monthly recovery point per required source for 400 days.
4. Reduce steady-state S3 use materially after the database cleanup without weakening recoverability or immutability.
5. Detect missing, stale, corrupt, anomalously small/large, TOC-divergent, collection-incomplete, and partially exported artifacts.
6. Make three independent notification paths honest:
   - Titan-1 watchdog to Telegram;
   - backend hourly poll to the existing allAI escalation path;
   - GitHub dead-man's-switch issue.
7. Prove current Infisical decryption and scratch restoration without exposing the offline identity or plaintext.
8. Publish reviewed recovery instructions both in Git and as an immutable S3 recovery map.
9. Produce machine-readable acceptance evidence that can be audited without trusting model prose.

### 2.2 Non-goals

1. This Gate 1 commit does not implement, deploy, merge, or activate production changes.
2. This BQ does not perform application-data cleanup. The approximately 90% database cleanup is an input condition; its own approval and evidence remain separate.
3. This BQ does not arbitrarily exclude `qdrant_sync_outbox`, `state_events`, or any other required table from `pg_dump`. Source-level retention may reduce live DB size, but every resulting backup is a complete logical dump of the selected database.
4. This BQ does not back up non-custodial seller datasets held in seller-owned buckets.
5. This BQ does not store the offline age identity in Infisical, Railway, S3, Git, local files, environment files, Docker layers, shell history, or model-readable state.
6. This BQ does not rotate Telegram again.
7. This BQ does not claim that GitHub plus local clones is equivalent to an S3 source mirror. The code-recovery dependency remains explicit; populating `git-mirrors/` requires a separate Gate 1 because it is outside this BQ's exact file scope.
8. This BQ does not use a model verdict as restore evidence. Deterministic commands and machine-verifiable attestations are authoritative.

## 3. Safety and trust invariants

### 3.1 S3 invariants

1. Bucket Versioning stays `Enabled`.
2. Object Lock configuration stays `ObjectLockEnabled=Enabled` with default mode `COMPLIANCE`.
3. The default 35-day lock is a floor for newly written versions.
4. A monthly version receives an explicit COMPLIANCE retain-until time of at least `object_creation_time + 400 days`.
5. A classifier may extend a retain-until time but must refuse to shorten it.
6. No implementation role receives `s3:BypassGovernanceRetention`; COMPLIANCE cannot be bypassed in any case.
7. The backup writer remains write-and-list only. It receives no delete permission and no general read/exfiltration permission.
8. The retention controller is a separate least-privilege identity limited to version listing, version tags, retention reads/extensions, lifecycle reads/writes, and inventory evidence for this bucket.
9. A lifecycle proposal is rejected if it disables versioning, changes Object Lock, directly names a version for deletion, lacks the required tag filters, or can expire a version before its class floor.
10. Lifecycle configuration is installed only after 100% classification coverage and dry-run reconciliation pass.

### 3.2 Secret invariants

1. Secrets are never printed, echoed, interpolated into shell commands, placed in command-line arguments, committed, or included in exception text.
2. Shell tracing is disabled for all secret-bearing processes.
3. Telegram request URLs are never logged because the token is part of the URL.
4. Raw HTTP client exceptions are sanitized before logging.
5. The offline age identity is acquired only after a local, interactive 1Password authorization by Max.
6. The Infisical ciphertext may cross the S3 network boundary; the age identity and decrypted bytes may not.
7. The scratch Postgres target is local, network-disabled, read-only except for explicitly declared memory-backed mounts, log-disabled, core-dump-disabled, and swap-disabled.
8. Cleanup is mandatory on success, failure, signal, timeout, and host reboot. Cleanup evidence must prove that no plaintext path or persistent Docker volume was created.

### 3.3 Evidence invariants

1. Freshness is not integrity, integrity is not restore success, and restore success is not full-platform recovery. Evidence records these separately.
2. Every evidence document identifies repository commit, container image digest, object version ID, verification time, verifier version, and result.
3. Evidence contains no credentials, connection strings, secret values, raw database rows, raw TOC, Cloudflare KV values, or Telegram token fragments.
4. A failed or incomplete source emits a failure record but must not advance the source's last-success timestamp.
5. Model summaries are advisory. They cannot change pass/fail fields or satisfy an acceptance criterion.

## 4. Recovery objectives

### 4.1 Fixed service objectives

| Recovery source | Required prefix or authority | Backup cadence | RPO | Component RTO | Full-platform contribution |
|---|---|---:|---:|---:|---|
| Main ai.market Postgres | `postgres/ai-market/` | nightly | ≤ 24h | ≤ 2h | required |
| Infisical Postgres | `postgres/infisical/` | nightly | ≤ 24h | ≤ 2h | first restore dependency |
| AIM Data Railway Postgres | `postgres/aim-data/` | nightly | ≤ 24h | ≤ 2h | required for AIM Data |
| Qdrant required collections | one prefix per §4.2 collection | nightly | ≤ 24h | ≤ 2h | required |
| Railway topology | `railway-config/` | nightly | ≤ 24h | ≤ 1h to usable manifest | required |
| Cloudflare DNS/settings/KV manifest | `cloudflare/` | nightly | ≤ 24h | ≤ 1h to usable manifest | required |
| Recovery instructions | reviewed Git source plus `RESTORE-README.md` | on every approved source change and at least monthly | ≤ 30d documentation drift | ≤ 15m access | required |
| Source code | GitHub protected repositories plus verified Titan-1 clones; `git-mirrors/` remains a tracked gap until populated | continuous Git push | ≤ 24h for unpushed local work | ≤ 1h clone/checkout | required external dependency |

**Full-platform RTO:** ≤ 4 hours from declaration of a recoverable total-loss incident to the validation checks in the approved recovery runbook passing.

### 4.2 Required Qdrant collections

The required set is explicit and configuration-controlled:

```text
knowledge_base_v2
knowledge_base
action_logs
listings
```

The backup job may discover and back up additional live collections, but discovery may not remove a required collection from monitoring. Adding a production collection requires the same change to the required-set configuration, backup job, monitor, restore drill, runbook, and tests. Removing a required collection requires an owner-approved decommission record and proof that no live reader or recovery path depends on it.

### 4.3 Schedule-aware deadline semantics

Each source registry row contains:

```json
{
  "source_id": "stable identifier",
  "schedule_utc": "declared expected schedule",
  "success_deadline_utc": "latest normal completion time",
  "max_staleness_hours": 26,
  "required": true,
  "last_success_object_version_id": "opaque S3 version id",
  "last_success_at": "RFC3339 UTC",
  "integrity_status": "ok|warning|failed",
  "restore_status": "current|due|failed"
}
```

The normal nightly staleness ceiling is 26 hours. The per-source deadline is authoritative when it is stricter. A monitor evaluates the last **successful complete artifact**, not the newest object under a broad prefix. Failure records, partial exports, health files, README updates, and unrelated collections never refresh a backup source.

## 5. S3 retention and storage-reduction design

### 5.1 Classification domain

Every current and future object **version** in `aimarket-backups-prod` must have exactly one lifecycle class tag:

```text
backup-retention-class=daily
backup-retention-class=monthly
```

This includes backup artifacts, health/status records, failure diagnostics, Git mirror artifacts when present, and versioned recovery documents. Delete markers are inventoried separately because S3 does not tag them like object versions. No unclassified version is permitted after cutover.

Additional non-authoritative tags are allowed:

```text
backup-source=<source_id>
backup-verification=verified|failed|control
backup-classifier-version=<semantic version>
```

The lifecycle class is version-specific. The classifier always calls version-aware APIs and never assumes that a key identifies only one version.

### 5.2 Daily class

1. Every newly written object version starts as `daily`.
2. Its COMPLIANCE retain-until time is at least creation plus 35 days.
3. The daily lifecycle rule requests current-version expiration at 35 days.
4. Noncurrent versions become eligible one day after becoming noncurrent, but Object Lock remains authoritative and prevents deletion before the 35-day floor.
5. Physical deletion is asynchronous and may occur later. The contract is a minimum retention and bounded lifecycle intent, not exact-to-the-second deletion.

### 5.3 Monthly class

1. At 00:30 UTC on the first day of each month, the classifier selects the latest fully successful, integrity-verified version for each required source from the previous UTC calendar month.
2. The selected version is changed from `daily` to `monthly`.
3. Before changing the tag, the controller extends COMPLIANCE retain-until to at least `object creation + 400 days`.
4. The controller reads the retained-until value back and fails closed unless the observed value is at least the requested value.
5. The monthly lifecycle rule requests current-version expiration at 400 days. Noncurrent eligibility is one day, but the 400-day Object Lock floor remains authoritative.
6. If no verified source version exists for a source-month, the classifier emits `MONTHLY_SOURCE_GAP`, makes no substitute choice from a different month, and pages through all healthy notification paths.

### 5.4 Existing-object backfill

Backfill is a two-phase, resumable operation:

1. **Inventory/dry run**
   - Enumerate all versions and delete markers with pagination.
   - Record key, opaque version ID, creation time, size, existing tags, Object Lock mode, and retain-until time.
   - Map each version to a source registry row.
   - Select one monthly version per source per UTC month within the trailing 400 days using existing success/integrity evidence.
   - Mark every other version `daily`.
   - Produce a signed plan hash. Make no mutation.
2. **Apply/reconcile**
   - Re-read each version immediately before mutation.
   - Refuse if version ID, current mode, or retain-until differs from the dry-run precondition.
   - Extend monthly COMPLIANCE locks before applying monthly tags.
   - Never shorten daily or monthly locks.
   - Resume idempotently from a version-key checkpoint.
   - Re-inventory until every version has exactly one class and every monthly version has the required retain-until time.

Existing versions older than their class floor may be tagged and later expired by lifecycle. The implementation must never call `DeleteObject` or `DeleteObjects` during backfill.

### 5.5 Lifecycle configuration

The installed S3 lifecycle configuration contains only:

1. `daily-current-expiration`: filter `backup-retention-class=daily`, current expiration 35 days.
2. `daily-noncurrent-expiration`: same filter, noncurrent expiration 1 day.
3. `monthly-current-expiration`: filter `backup-retention-class=monthly`, current expiration 400 days.
4. `monthly-noncurrent-expiration`: same filter, noncurrent expiration 1 day.
5. `abort-incomplete-multipart-upload`: abort incomplete multipart uploads after 1 day; this does not delete completed versions.

The exact generated JSON is committed and tested in Gate 3. A policy test rejects missing filters, retention below the fixed values, versioning changes, Object Lock changes, and any direct delete operation. Lifecycle installation is blocked until the post-backfill reconciliation report is clean.

### 5.6 Storage target and measurement

Storage reduction is measured, not guessed:

1. Capture a pre-cutover inventory of version count and bytes by source, class, current/noncurrent state, lock state, and age band.
2. Establish a post-cleanup baseline only from a backup that passes size/hash/TOC checks and a scratch restore. Historical pre-cleanup size must not cause the expected 90% shrink to be classified as corruption.
3. Forecast 35 daily plus the 13 or 14 calendar-month positions that can overlap a rolling 400-day window, per source, using the post-cleanup verified median.
4. Report actual version bytes weekly until the lifecycle curve stabilizes.
5. Gate 4 requires:
   - 100% classification;
   - no reduction in locked-version count caused by the cutover;
   - an explicit expected-reclaimable-byte total;
   - a projected steady-state total at least 60% below the S1322 233.5 GiB baseline unless actual required post-cleanup artifact sizes mathematically make that impossible;
   - if the 60% target is impossible, a new owner decision before acceptance rather than weakening retention or excluding required data.

No acceptance statement may equate lifecycle configuration with immediate reclamation. Locked and asynchronously expired versions may delay the realized decrease.

## 6. Deterministic Titan-1 Infisical restore verifier

### 6.1 Purpose

The verifier proves that a chosen `postgres/infisical/` object version:

1. is the intended immutable ciphertext;
2. decrypts with Max's offline age identity;
3. is a valid Postgres custom archive;
4. restores into a clean Postgres 18 scratch database;
5. passes structural and aggregate sanity checks;
6. leaves behind only a redacted attestation.

It does not expose the offline identity, plaintext archive, restored rows, secret values, or raw TOC.

### 6.2 Deterministic inputs

The operator supplies:

- exact S3 key and opaque version ID;
- expected encrypted-object checksum/size from the independent inventory;
- verifier commit SHA;
- pinned Postgres 18 container image digest;
- a 1Password secret reference naming the offline age identity.

The 1Password reference may be present in process configuration; the identity value may not. The verifier rejects floating container tags, absent version IDs, unpinned verifier commits, and checksums that do not match the downloaded ciphertext stream.

### 6.3 Identity ingress

1. Max starts the verifier locally on Titan-1 from an ordinary Terminal session, outside model-controlled execution.
2. `op read` performs local interactive authorization.
3. Its stdout is connected directly to the age process through an anonymous pipe or inherited file descriptor.
4. The identity is never assigned to a shell variable, environment variable, command substitution, file, named pipe on disk, clipboard, or argv.
5. The verifier disables shell history and tracing and sets a restrictive umask before spawning any child.
6. Identity-pipe creation and closure are tested under success, error, timeout, and signal paths.

### 6.4 Ciphertext and plaintext flow

```text
S3 GetObject(version-id, encrypted bytes)
  -> streaming encrypted SHA-256/size verifier
  -> age decrypt (identity arrives on a separate anonymous FD)
  -> tee-like in-memory plaintext SHA-256 counter
  -> pg_restore stdin inside isolated Postgres 18 scratch container
```

The encrypted stream may be retried before decryption. Once plaintext emission begins, the entire decrypt/restore attempt is single-use; any interruption destroys the scratch container and restarts from ciphertext.

### 6.5 Scratch container

The container contract is:

- image pinned by digest;
- `--network none`;
- `--read-only`;
- `--tmpfs /var/lib/postgresql/data`;
- `--tmpfs /tmp`;
- `--tmpfs /run/postgresql`;
- `--log-driver none`;
- no bind mounts;
- no named or anonymous Docker volumes;
- no published ports;
- no environment secret or external database URL;
- local trust over the container's Unix socket only;
- core dumps disabled;
- container memory limit set;
- swap disabled by setting memory-swap equal to memory;
- fixed locale, timezone UTC, and deterministic Postgres settings;
- forced removal after the attestation is finalized.

Before starting, the verifier records Docker's volume list and the target image digest. After cleanup it proves no new volume exists and no verifier container remains.

### 6.6 Verification stages

1. Verify ciphertext byte count and SHA-256 against the selected object-version evidence.
2. Stream decrypted bytes to `pg_restore --list` and compute:
   - archive parse exit code;
   - TOC entry count;
   - normalized TOC fingerprint;
   - plaintext archive SHA-256.
3. Start a fresh scratch container and stream a second decryption of the same ciphertext into full `pg_restore`.
4. Reject any restore warning or error not explicitly allowlisted by exact Postgres version and reason.
5. Run local structural checks through the Unix socket:
   - database connects;
   - expected migration/version table exists;
   - expected Infisical core schema families exist;
   - aggregate table count, schema count, extension count, and non-secret row-count bands are within the approved baseline;
   - no raw row, secret value, encrypted secret payload, member identity, project name, or secret path is emitted.
6. Destroy the scratch container and memory-backed filesystems.
7. Serialize the attestation from fixed field order and canonical JSON.
8. Hash and sign the attestation with a local operator evidence key that is distinct from the age identity.

The list pass and full restore pass deliberately decrypt twice. This avoids persisting or replaying a plaintext archive.

### 6.7 Fail-closed conditions

The verifier fails and produces a redacted failure attestation for:

- wrong or missing version ID;
- ciphertext size/hash mismatch;
- age decryption failure;
- any identity byte appearing in a child argv, environment snapshot, log capture, or file audit;
- nonzero `pg_restore --list`;
- TOC outside approved bands;
- normalized TOC fingerprint mismatch without an approved schema-change baseline;
- full restore error or timeout;
- structural check failure;
- attempted network access by the scratch container;
- persistent Docker volume, bind mount, or plaintext path;
- incomplete teardown;
- failure to sign the final attestation.

Failure details use fixed reason codes and bounded sanitized text. Raw stderr from age, `pg_restore`, Docker, `op`, or HTTP clients is not copied into the attestation.

### 6.8 Redacted attestation contract

The only object that may be given to local Ollama is canonical JSON with this shape:

```json
{
  "schema": "aimarket.infisical_restore_attestation.v1",
  "result": "pass",
  "verified_at": "RFC3339 UTC",
  "verifier_commit": "40-char SHA",
  "container_image_digest": "sha256:...",
  "s3": {
    "bucket": "aimarket-backups-prod",
    "key_class": "postgres/infisical",
    "version_id_hash": "sha256 of opaque version id",
    "ciphertext_bytes": 0,
    "ciphertext_sha256": "..."
  },
  "archive": {
    "plaintext_sha256": "...",
    "toc_entries": 0,
    "toc_fingerprint": "..."
  },
  "restore": {
    "pg_major": 18,
    "restore_exit": 0,
    "schema_count": 0,
    "table_count": 0,
    "extension_count": 0,
    "aggregate_checks": "pass"
  },
  "isolation": {
    "network": "none",
    "persistent_volumes_created": 0,
    "containers_remaining": 0,
    "plaintext_files_detected": 0
  },
  "secret_scan": "pass",
  "attestation_sha256": "...",
  "signature": "..."
}
```

Names, rows, values, raw TOC, errors, credentials, object version ID, 1Password reference, age recipient, and key fingerprints are excluded from the Ollama input. Ollama output is stored separately and labeled `advisory_model_summary`; it cannot overwrite or amend the attestation.

## 7. Backup artifact integrity and retry design

### 7.1 Common artifact manifest

Every successful backup artifact has an adjacent or health-record manifest containing:

- source ID;
- exact object key and version ID;
- created-at UTC;
- writer commit and image digest;
- plaintext bytes where applicable;
- uploaded bytes;
- SHA-256 of the source artifact;
- S3 checksum algorithm and returned checksum;
- TOC count and fingerprint for Postgres;
- collection name and snapshot metadata for Qdrant;
- section-result map for exports;
- anomaly-baseline version;
- retry attempt count;
- overall status.

The manifest itself does not make a failed artifact successful. `overall_status=ok` is written only after every required check and S3 readback permitted by the verification identity succeeds.

### 7.2 Postgres size/hash/TOC anomaly rules

Each Postgres source uses a baseline built from the last seven successful, restore-verified post-cleanup artifacts. Before seven exist, the first approved post-cleanup restore is the seed baseline.

Fail the artifact if any of the following occurs:

1. size below the fixed absolute floor for that source;
2. size less than 50% or greater than 200% of the verified rolling median without an approved baseline-reset record;
3. local SHA-256 mismatch against S3 checksum/readback;
4. `pg_restore --list` nonzero;
5. TOC entry count less than 80% or greater than 125% of the verified rolling median without an approved schema-change record;
6. required TOC object classes are absent;
7. normalized TOC fingerprint differs from the approved schema manifest without a linked migration or cleanup baseline change.

The approximately 90% cleanup is handled by a one-time `post_cleanup_baseline_reset` that requires a full scratch restore before adoption. It must not simply widen anomaly thresholds.

### 7.3 Bounded `pg_dump` retry

`scripts/backup_pg.py` performs at most **three total attempts**:

1. initial attempt;
2. retry after 60 seconds;
3. final retry after 300 seconds.

Rules:

- Only enumerated transient connection-loss, connection-reset, and server-restart classes are retryable.
- Authentication, client/server major-version mismatch, insufficient disk, configuration, permission, cancellation, and integrity failures are not retryable.
- Each attempt uses a new temporary path and restarts the entire consistent dump.
- Failed temporary archives are securely removed before the delay.
- No failed attempt uploads under the canonical success prefix.
- Total job wall time is bounded; scheduler timeouts are longer than the explicit job bound.
- Logs contain reason codes, attempt number, duration, and sanitized tail classification, not URLs, credentials, hostnames, SQL text, or raw stderr.
- After final failure, the job writes a failure health record, does not advance `last_success_at`, exits nonzero, and is observable by all three monitor paths.

### 7.4 Qdrant completeness

1. The job backs up every required collection in §4.2 and may back up additional discovered collections.
2. Each collection has an independent artifact, hash, size baseline, success timestamp, and restore status.
3. Overall Qdrant status is failed if any required collection is missing, stale, corrupt, or failed.
4. One fresh collection can never mask another.
5. A collection is removed from the required set only through the decommission procedure in §4.2.
6. Gate 4 restores every required collection into an isolated Qdrant instance pinned to the production-compatible image digest.

### 7.5 Cloudflare partial-failure semantics

A Cloudflare export is successful only if all required sections succeed:

- zone inventory;
- DNS records for every required zone and every pagination page;
- zone settings for every required zone;
- required KV namespace inventory;
- every required KV key/value read;
- canonical JSON serialization;
- local hash;
- S3 upload and independent checksum/readback.

Any HTTP error, pagination inconsistency, missing zone, required KV read failure, schema error, or checksum mismatch makes the run failed. On failure:

1. no object is written under the canonical `cloudflare/<date>/` success prefix;
2. a redacted diagnostic may be written under `failed/cloudflare/<date>/`;
3. the previous successful object remains the freshness reference;
4. the process exits nonzero;
5. the monitor pages after the source deadline;
6. Cloudflare response bodies, tokens, and KV values are never logged.

Gate 3 must provision the least-privilege Cloudflare token scopes needed to read the required settings and KV surfaces. A fresh partial object is never accepted as recovery coverage.

### 7.6 AIM Data Postgres

The small Railway Postgres database used by AIM Data becomes a first-class backup source:

- source ID `aim-data-pg`;
- prefix `postgres/aim-data/`;
- nightly complete custom-format dump;
- 24-hour RPO and 2-hour component RTO;
- independent credentials and health record;
- the same size/hash/TOC/retry/retention rules as other Postgres sources;
- a scratch-restore Gate 4 proof.

This closes the S1322 recovery-map omission. It does not bring non-custodial seller data into ai.market custody.

## 8. Monitoring and notification design

### 8.1 Single required-source registry

The Titan-1 watchdog, backend monitor, GitHub workflow, runbooks, tests, and recovery README consume or generate from the same versioned registry. Required entries are:

```text
postgres/ai-market/
postgres/infisical/
postgres/aim-data/
qdrant/knowledge_base_v2/
qdrant/knowledge_base/
qdrant/action_logs/
qdrant/listings/
railway-config/
cloudflare/
RESTORE-README.md
```

`git-mirrors/` is represented as `required_external_gap`. It must appear in every report but must not incorrectly page as a missed nightly backup while the approved source-code authority remains GitHub plus verified Titan-1 clones. This BQ does not populate it; that requires a separate Gate 1.

The registry distinguishes artifact prefixes from control objects. Monitoring selects only an `overall_status=ok` artifact of the expected type. Health/status objects and failure diagnostics cannot satisfy source freshness.

### 8.2 Titan-1 watchdog

The shell implementation is replaced with a testable Python program that:

1. evaluates every registry entry independently;
2. uses version-aware S3 listing;
3. applies schedule-aware deadlines;
4. validates size/hash/TOC/export/collection health from signed manifests;
5. emits a stable incident fingerprint based on failed source IDs and reason codes;
6. exits nonzero on any required-source failure or notification failure;
7. writes only redacted structured logs;
8. never logs request URLs or raw client exceptions.

The watchdog remains independent of Infisical and the backend so it can report failure of either.

### 8.3 Telegram token reconciliation without model exposure

The token is not read, compared, copied, or tested by a model.

1. Max retrieves the already-rotated value from its authoritative local 1Password item.
2. A reviewed local installer runs outside model control and invokes macOS Keychain's hidden password prompt (`security add-generic-password ... -w` with `-w` last and no value argument).
3. Max pastes the token into that hidden local prompt. It does not enter shell history, stdin captured by Codex, argv, Git, `.env`, or logs.
4. The Keychain item is named `ai.market.s3-backup-watchdog.telegram`, scoped to the Titan-1 operator account and the watchdog runtime.
5. The old token entry in the model-readable `.env` is no longer consumed by the watchdog. Removal or redaction of that stale line occurs only after the Keychain-backed canary passes.
6. The watchdog retrieves the token in memory and uses an in-process HTTPS client. It never spawns `curl` with a token-bearing URL.
7. No token rotation API is called by this BQ.

### 8.4 Telegram delivery contract

A send is successful only when all are true:

- TLS verification succeeds;
- HTTP status is 2xx;
- response JSON parses;
- `ok` is exactly `true`;
- `result.message_id` is an integer;
- returned chat ID matches the configured expected chat ID.

The redacted log records UTC time, notification class, incident fingerprint, HTTP status class, and `message_id`. It records no URL, body text, chat ID, username, or token material.

Cutover requires one explicit canary whose received message is confirmed by Max and whose API response supplies the recorded `message_id`. Ongoing health uses one weekly canary at a fixed UTC time. Canary failure is itself an alert-path incident and is surfaced through backend/GitHub paths; it never exits zero silently.

### 8.5 Backend hourly poll

The existing `poll_backup_watchdog` Celery task is activated at minute 30 of every hour.

- Missing `INTERNAL_API_KEY` becomes a task failure, not `status=skipped`.
- The internal endpoint evaluates all registry sources, not only Postgres and aggregate Qdrant.
- The poll emits one incident per stable fingerprint and updates/recoveries idempotently.
- A request failure, malformed response, or absent required source fails the task.
- The worker/beat deployment is accepted only after a real scheduled execution is observed with the expected task ID, result, and source count.

### 8.6 GitHub timing and deduplication

`.github/workflows/backup-verify.yml` becomes a schedule-aware external dead-man's switch:

1. Run daily after the latest declared source success deadline plus margin, and support manual dispatch.
2. Do not hard-code a six-hour age. Consume source statuses and deadlines from the backend response.
3. Treat endpoint unreachable, unauthorized, malformed, incomplete, or internally inconsistent responses as unhealthy.
4. Use stable marker `<!-- backup-recovery-watchdog:v2 -->`, label `backup-failure`, and a constant incident title.
5. Search for the existing open marked issue before creating one.
6. If unhealthy and an issue exists, update its summary and append one bounded status comment only when the fingerprint changes or once per 24 hours.
7. If unhealthy and no issue exists, create exactly one issue.
8. When all sources recover, add one recovery comment and close the marked issue.
9. Repeated healthy runs create nothing.
10. Workflow concurrency permits only one active verifier for the branch; permissions remain least-privilege `contents: read`, `issues: write`.
11. The issue body points to current S3/runbook recovery paths, not deleted GCS workflows.

## 9. Runbook and S3 recovery-map publication

The reviewed source of truth remains Git:

- `backup-and-recovery.md` for architecture, schedules, operations, verification, and repair;
- `disaster-recovery.md` for ordered total-loss recovery;
- `aws-s3.md` for bucket, Object Lock, lifecycle, IAM, and retention;
- `operator-telegram-notifications.md` for token custody and delivery proof;
- `titan-1.md` for local verifier, watchdog, Keychain, and LaunchAgent operation.

After the production changes pass Gate 4 review:

1. Render a standalone recovery map from the reviewed `disaster-recovery.md` commit.
2. Embed source repo, exact commit SHA, render time, content SHA-256, and verifier schema version.
3. Upload it as a new version of `s3://aimarket-backups-prod/RESTORE-README.md`.
4. Apply the daily class immediately. The monthly classifier may select an approved version according to §5.
5. Read back that exact version through the recovery-reader identity and verify content hash.
6. Record the S3 version ID hash and source commit in acceptance evidence.
7. Republish on every approved source-runbook change and at least monthly even if content is unchanged.

No stale S3 README may be cited as current. Git and S3 hashes must match.

## 10. Exact repository and file scope for Gate 2/3

No production file outside this allowlist may change without reopening Gate 1 or adding a separately reviewed chunk amendment.

### 10.1 `aidotmarket/runbooks`

Existing files allowed to change:

```text
backup-and-recovery.md
disaster-recovery.md
aws-s3.md
operator-telegram-notifications.md
titan-1.md
scripts/cloudflare_export.py
scripts/s3_backup_watchdog.sh              # delete only after Python replacement is live
```

New files allowed:

```text
scripts/backup_source_registry.json
scripts/s3_backup_watchdog.py
scripts/s3_retention_classifier.py
scripts/infisical_restore_verify.py
scripts/reconcile_watchdog_telegram_token.sh
scripts/publish_restore_readme.py
ops/launchd/com.aimarket.s3-backup-watchdog.plist
ops/launchd/com.aimarket.s3-retention-classifier.plist
tests/test_backup_source_registry.py
tests/test_s3_backup_watchdog.py
tests/test_s3_retention_classifier.py
tests/test_infisical_restore_verify.py
tests/test_cloudflare_export.py
tests/test_publish_restore_readme.py
```

Local deployment targets generated from reviewed source:

```text
/Users/max/Library/LaunchAgents/com.aimarket.s3-backup-watchdog.plist
/Users/max/Library/LaunchAgents/com.aimarket.s3-retention-classifier.plist
/Users/max/Library/Logs/aimarket_s3_backup_watchdog.log
/Users/max/Library/Logs/aimarket_s3_retention_classifier.log
macOS Keychain service ai.market.s3-backup-watchdog.telegram
```

The local paths are deployment state, not Git authoring locations.

### 10.2 `aidotmarket/ai-market-backend`

Existing files allowed to change:

```text
.github/workflows/backup-verify.yml
app/allai/agents/sysadmin/backup_monitor.py
app/api/v1/endpoints/backup_status.py
app/core/celery_app.py
app/tasks/scheduled.py
scripts/backup_pg.py
scripts/backup_qdrant_s3.py
tests/scripts/test_backup_pg.py
tests/test_backup_s3_watchdog.py
tests/test_celery_app_config.py
tests/test_scheduled_notifications.py
```

New files allowed:

```text
Dockerfile.aim-data-backup
railway.aim-data-backup.json
tests/test_backup_verify_workflow.py
tests/test_backup_status_contract.py
```

The AIM Data backup reuses the reviewed `scripts/backup_pg.py` implementation and is deployed from this repository into the AIM Data Railway project through the two new pinned deployment files. Its database credential is isolated to that backup service; it is not copied into the ai.market backend web service.

### 10.3 External configuration in scope

Configuration changes are limited to:

- S3 lifecycle rules and version tags/retention extensions described in §5;
- one least-privilege retention-controller IAM policy/identity;
- Cloudflare read scopes required by §7.5;
- Railway variables and cron/deployment config for the enumerated backup services;
- Celery beat activation;
- two Titan-1 LaunchAgents;
- one macOS Keychain item;
- the S3 `RESTORE-README.md` object.

No other bucket, AWS account, Telegram bot, Railway project/service, Cloudflare zone, local secret, or credential is in scope.

## 11. Test plan

### 11.1 Hermetic unit and contract tests

1. Source registry schema, exact required prefixes, exact required Qdrant collections, uniqueness, and schedule deadlines.
2. Version-aware S3 pagination including duplicate keys, noncurrent versions, delete markers, and opaque version IDs.
3. Daily/monthly selection across month/year/leap-day boundaries.
4. Backfill idempotence, checkpoint restart, precondition drift, and refusal to shorten COMPLIANCE.
5. Lifecycle JSON filters and fixed 35/400-day floors.
6. Locked versions are never passed to delete APIs; test client exposes no delete method to classifier code.
7. `pg_dump` transient retry count/delays and permanent-failure no-retry behavior.
8. Fresh temp path per retry and cleanup on signal/timeout.
9. Size baseline seed/reset, median boundaries, hash mismatch, TOC count/fingerprint, and approved schema-change path.
10. Qdrant required-collection completeness where one fresh collection cannot mask one stale/missing collection.
11. Cloudflare all-success, per-section 403/429/5xx, pagination truncation, missing zone, missing KV value, and no canonical upload after partial failure.
12. Telegram HTTP/JSON/chat/message-ID validation and redaction of token-shaped strings from messages, arguments, exceptions, and tracebacks.
13. GitHub workflow timing, endpoint failure, stable marker, create/update/no-op/recover/close, concurrency, and least-privilege permissions.
14. Celery schedule existence and missing-secret fail-closed behavior.
15. S3 README render determinism and readback hash.
16. Attestation canonicalization, signing, secret scanner, and Ollama projection allowlist.

### 11.2 Local isolation tests

On Titan-1 with synthetic age keys and a synthetic Postgres 18 archive:

1. Prove identity bytes do not appear in `ps`, child argv, captured environment, logs, filesystem scan, Docker inspect, or attestation.
2. Prove decrypted sentinel values do not appear on persistent disk before, during, or after success/failure/signal.
3. Prove scratch container has no network, bind mount, volume, log driver, swap, or residue.
4. Kill each pipeline stage and verify teardown.
5. Feed the redacted attestation to Ollama and prove the submitted bytes equal the allowlisted projection exactly.

Synthetic tests happen before Max supplies the real identity.

### 11.3 Disposable AWS integration tests

Use a dedicated disposable bucket created with Object Lock enabled:

1. Enable Versioning and COMPLIANCE default retention.
2. Create multi-version fixtures with daily/monthly candidates.
3. Run dry-run, apply, and reconcile.
4. Prove monthly retain-until extends to 400 days.
5. Attempt shortening and deletion of locked versions and require failure.
6. Install generated lifecycle and read it back byte-semantically.
7. Test restore-reader checksum readback without giving the writer read access.

Production bucket integration begins only after these pass.

### 11.4 Production canaries and restore drills

1. One main Postgres post-cleanup dump and scratch restore.
2. One Infisical deterministic decrypt/full restore with Max's local identity.
3. One AIM Data Postgres dump and scratch restore.
4. Every required Qdrant collection restored in isolation.
5. One complete Cloudflare export with every required section successful.
6. One Telegram canary with confirmed `message_id`.
7. One scheduled backend poll, not manual task invocation.
8. One unhealthy GitHub simulation proving single-issue creation/update, followed by recovery closure.
9. One exact-version `RESTORE-README.md` readback hash.

### 11.5 Repository validation

Every implementation commit runs its repository's full relevant suite plus:

```text
git diff --check
runbook-catalog check
pytest -q
```

Backend and AIM Data chunks run their existing lint/type/test/CI gates. Tests that require secrets or production access are separate credential-bound canaries and never run in untrusted PR contexts.

## 12. Cutover plan

The order is mandatory:

1. **Freeze evidence.** Capture current S3 configuration, full version inventory, storage totals, required-source status, active schedules, IAM policies, and exact production commits.
2. **Land code dark.** Merge registry, integrity, retry, Cloudflare, monitor, workflow, verifier, and runbook changes with all new schedules and lifecycle mutations disabled.
3. **Post-cleanup baseline.** Produce a new main-DB artifact; run anomaly checks and full scratch restore; approve `post_cleanup_baseline_reset`.
4. **Complete source coverage.** Produce and restore AIM Data; produce every Qdrant collection; produce a complete Cloudflare export.
5. **Synthetic verifier proof.** Pass all §11.2 isolation tests.
6. **Real Infisical proof.** Max locally supplies the age identity; deterministic attestation passes; no model sees key/plaintext.
7. **Telegram reconcile.** Max enters the already-rotated token into Keychain through the hidden local prompt. Run and confirm the canary/message ID. Do not rotate.
8. **Deploy monitors dark.** Compare Titan, backend, and GitHub evaluations for at least one full backup cycle without paging.
9. **Activate backend poll.** Enable Celery beat and observe a real scheduled execution.
10. **Activate GitHub dedup workflow.** Run unhealthy/recovery simulation and prove one issue lifecycle.
11. **Activate Titan paging.** Enable the Python watchdog and weekly canary. Retire the shell watchdog only after the Python LaunchAgent is loaded and observed.
12. **Retention dry run.** Generate the complete version plan; review plan hash, monthly selections, lock extensions, expected reclaimable bytes, and zero-delete property.
13. **Retention apply.** Tag all versions and extend monthly locks. Reconcile to 100%.
14. **Lifecycle activate.** Install the reviewed lifecycle JSON only after step 13 passes.
15. **Publish documentation.** Merge reviewed source runbooks, render/upload `RESTORE-README.md`, and verify exact-version hash.
16. **Observe.** Run at least 72 hours across three nightly cycles. Require zero missing source, false-positive, duplicate issue, ignored Telegram failure, or partial-success artifact.
17. **Gate 4 close.** Assemble §13 evidence and obtain fresh exact-commit/release review before claiming production-ready.

No step may be skipped because a later step appears healthy.

## 13. Acceptance criteria and required evidence

Gate 4 is accepted only when all rows pass.

| ID | Acceptance criterion | Required evidence |
|---|---|---|
| AC1 | S3 Versioning remains enabled and Object Lock remains COMPLIANCE. | Before/after AWS API JSON and config hash. |
| AC2 | No locked version was deleted or had retention shortened. | Full version/retention reconciliation with zero violations and CloudTrail query for prohibited calls. |
| AC3 | Every existing version has exactly one daily/monthly class. | Paginated inventory totals: unclassified=0, dual-class=0. |
| AC4 | Daily floor is 35 days; monthly floor is 400 days. | Lifecycle readback plus sampled/all-version retain-until proofs. |
| AC5 | One verified monthly object exists for each required source-month in the available 400-day window, or each historical gap is explicitly recorded. | Monthly coverage matrix and selection-plan hash. |
| AC6 | Storage reduction is material and honestly projected. | Pre/post bytes, post-cleanup median, reclaimable bytes, steady-state forecast, weekly actuals. |
| AC7 | Main PG meets 24h RPO/2h RTO and retry/anomaly rules. | Scheduled artifact manifest, forced transient retry trace, scratch-restore duration. |
| AC8 | Infisical decrypts and restores with zero secret exposure. | Signed redacted attestation, isolation audit, process/filesystem secret scan; Max confirmation that identity entry stayed local. |
| AC9 | AIM Data PG is covered and restored. | Exact object version manifest and scratch-restore report. |
| AC10 | Every required Qdrant collection is fresh, verified, and independently restored. | Four per-collection manifests and restore reports. |
| AC11 | Cloudflare export is complete and partial failures fail closed. | Successful section manifest plus injected-403 test proving no canonical success object. |
| AC12 | Telegram uses the already-rotated token and confirms delivery. | Keychain item metadata without value, canary UTC, HTTP 2xx, `ok=true`, expected destination check, `message_id`, Max receipt confirmation. |
| AC13 | Telegram failure cannot exit successfully or leak the token. | 401/429/5xx/malformed-response tests and log/argv secret scans. |
| AC14 | Backend poll is active. | Celery beat config, deployed commit, real scheduled task ID/result/source count. |
| AC15 | GitHub timing and dedup work. | Workflow run URLs/IDs for unhealthy repeat and recovery; exactly one issue created then closed. |
| AC16 | Every required prefix/collection is monitored independently. | Registry hash and three-path result comparison with exact source count. |
| AC17 | RPO/RTO are met. | Timed restore-drill report: each component and full-platform critical path ≤ fixed objectives. |
| AC18 | Source runbooks and S3 README match. | Git commit SHA, rendered SHA-256, exact S3 version readback SHA-256. |
| AC19 | Writer remains non-delete and non-read/exfiltration capable. | IAM policy diff and denied Get/Delete canaries; separate reader/controller proof. |
| AC20 | Production survives three nightly cycles after cutover. | 72-hour observation report with all source manifests and notification-path status. |
| AC21 | No production code was introduced by Gate 1. | Gate 1 commit changed exactly this spec file. |

Evidence is stored under an approved immutable evidence namespace using redacted JSON and hashes. Raw credentials, raw restored content, raw TOC, and secret-bearing logs are prohibited evidence.

## 14. Rollback and irreversible limits

### 14.1 Reversible changes

- Disable the new Celery beat entry.
- Disable the GitHub workflow schedule while preserving manual dispatch.
- Unload the two new LaunchAgents and reload the previously preserved watchdog only if its alert path has been safely reconciled.
- Disable S3 lifecycle rules to stop future lifecycle actions.
- Stop future classification runs.
- Revert application code and source runbooks to reviewed prior commits.
- Remove Cloudflare token scopes that were added solely for export after exports are safely paused.

### 14.2 Irreversible or bounded changes

1. A COMPLIANCE retention extension cannot be shortened. Monthly versions extended to 400 days remain locked for that period.
2. Lifecycle deletion of an **unlocked** version is not undone by removing lifecycle rules. This is why lifecycle is last and follows complete restore evidence.
3. A locked version is never a rollback target and never deleted.
4. Existing database cleanup is outside this BQ and is not reversed by backup rollback.
5. A Telegram token is not rotated as rollback. If the Keychain integration fails, disable the new sender and repair access to the same already-rotated token; any future rotation requires a separate explicit owner decision.
6. Evidence and audit records are append-only.

### 14.3 Automatic rollback triggers

Pause at the last safe boundary and disable the new schedule/lifecycle component when any occurs:

- Object Lock mode/config drift;
- any attempted retention shortening or locked-version deletion;
- unclassified or ambiguously classified version after reconcile;
- backup writer gains read/delete;
- source success advances on a failed/partial artifact;
- secret-shaped value appears in logs, argv, environment captures, files, attestations, or model input;
- Telegram response lacks confirmed message ID;
- duplicate GitHub issue;
- required Qdrant collection masked by aggregate freshness;
- Cloudflare partial export written as canonical success;
- restore drill exceeds RTO or fails structural checks.

Rollback does not authorize weakening a safety invariant to recover availability.

## 15. Gate boundaries and implementation chunks

Gate 2 should split implementation into reviewable chunks:

1. **C1 — registry, monitor contract, GitHub dedup, backend poll activation;**
2. **C2 — Postgres retry/anomaly checks plus AIM Data source;**
3. **C3 — Qdrant per-collection integrity and restores;**
4. **C4 — Cloudflare complete-or-fail export;**
5. **C5 — Titan Python watchdog, Keychain reconciliation, Telegram canary;**
6. **C6 — deterministic Infisical verifier and redacted attestation;**
7. **C7 — S3 classifier, backfill, lifecycle, and storage evidence;**
8. **C8 — source runbooks, S3 README publication, and integrated recovery drill.**

Each chunk requires fresh exact-commit review. C7 cannot activate lifecycle before C2, C3, C4, C6, and the C7 dry-run/reconcile proof pass. C8 cannot claim full-platform readiness while `git-mirrors/` remains empty without explicitly naming GitHub plus verified Titan clones as the external source-code dependency.

## 16. Requirement traceability

| Owner requirement | Design section |
|---|---|
| All S1322 recommendations authorized | §§1–15 |
| Daily 35-day plus monthly 12-month retention | §§0.1, 5 |
| Monthly implemented as 400 days | §§0.1, 5.3 |
| Major storage reduction after ~90% DB cleanup | §§2.2, 5.6, 7.2 |
| Do not rotate Telegram again | §§0.1, 8.3, 14.2 |
| Infisical proof without offline key in chat | §6 |
| Deterministic Titan-1 verifier | §6 |
| No key/plaintext in chat/network/logs/argv/disk | §§3.2, 6.3–6.7 |
| Ollama sees redacted attestation only | §6.8 |
| Classify existing/future versions daily/monthly | §5 |
| Preserve Object Lock/versioning | §§3.1, 5, 13 |
| Securely reconcile already-rotated Telegram token | §8.3 |
| Confirm delivery/message ID | §8.4 |
| Fix GitHub timing/dedup | §8.6 |
| Activate backend poll | §8.5 |
| Monitor every prefix/collection | §§4.2, 8.1 |
| Size/hash/TOC anomaly checks | §§7.1–7.2 |
| Bounded `pg_dump` retry | §7.3 |
| Cloudflare partial-failure semantics | §7.5 |
| Set RPO/RTO | §4 |
| Publish source runbooks and S3 README | §9 |
| Exact repo/file scope | §10 |
| Tests | §11 |
| Cutover | §12 |
| Rollback limits | §14 |
| Secret handling | §§3.2, 6, 8.3–8.4 |
| Acceptance evidence | §13 |
| Never weaken COMPLIANCE/delete locked versions | §§0.1, 3.1, 5, 14 |
| Gate 1 only; no production implementation | §§0, 2.2, AC21 |

**End of Gate 1 R1 design artifact.**
