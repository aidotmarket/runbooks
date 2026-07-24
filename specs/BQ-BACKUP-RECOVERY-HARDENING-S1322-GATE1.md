# BQ-BACKUP-RECOVERY-HARDENING-S1322 — Gate 1 Design

Status: AUTHORED_PENDING_REVIEW  
Owner: Vulcan S1322  
Directive: Max, 2026-07-24  
Class: security-sensitive production resilience and retention  

## 1. Outcome

ai.market must have a recovery system that is demonstrably restorable, fails loudly when any required backup is late or incomplete, and does not retain daily full backups indefinitely.

This design implements:

- a deterministic, zero-disclosure Infisical restore proof on Titan-1;
- 35-day daily and 400-day monthly S3 retention without weakening Object Lock;
- secure installation of Max's already-rotated Telegram credential without rotating it again;
- independent, delivery-proven backup alerts;
- per-source freshness and backup-quality checks;
- bounded retry for transient Postgres dump failures;
- fail-closed Cloudflare exports;
- documented RPO/RTO and replacement drills.

## 2. Current evidence and problem statement

The S1322 audit established:

- Railway deployment `0103b798-f0e3-4592-b601-ace99f0b7b86` failed on 2026-07-19 when the Postgres server closed the connection during `COPY public.qdrant_sync_outbox`.
- No successful main-DB dump exists for 19 or 20 July, leaving about 72 hours between successful snapshots.
- The latest main-Postgres dump and `knowledge_base_v2` Qdrant snapshot both restored successfully in disposable environments.
- The current Infisical object is encrypted and structurally plausible, but has not been decrypted and restored with Max's offline key.
- The Titan-1 watchdog detected the missed backups, but Telegram delivery fails because the on-disk token is stale. Max states that the token was recently rotated and must not be rotated again.
- GitHub `backup-verify.yml` creates daily false alerts because its six-hour threshold is incompatible with the nightly schedule and scheduler delay.
- Backend `poll_backup_watchdog` exists, but its Celery beat entry remains disabled.
- Cloudflare exports upload successfully while required zone-settings calls contain HTTP 403 errors.
- The bucket has Object Lock COMPLIANCE/35 days, versioning, encryption and public-access blocking, but no lifecycle policy.
- On 2026-07-24 the classified backup prefixes contained 322 current objects / 257,083,842,321 bytes. A first-successful-per-family-per-month policy identifies 17 monthly recovery points / 9,342,163,753 bytes and 305 daily objects / 247,741,678,568 bytes.
- The recent database cleanup reduced new main-Postgres dumps to roughly 0.37 GB, but pre-cleanup dumps remain much larger. Qdrant `knowledge_base_v2` is now the dominant growth source.

## 3. Non-negotiable security invariants

1. The offline age identity, Telegram token, decrypted Infisical data and provider credentials never enter chat, a networked model, logs, command-line arguments, Git, or a persistent plaintext file.
2. Local Ollama may inspect only a redacted attestation. It must never receive the age identity, ciphertext plaintext, restored rows, Telegram token, or 1Password item contents.
3. Deterministic programs, not an LLM, perform cryptographic verification and database restore.
4. Object Lock stays enabled in COMPLIANCE mode. No retention period is shortened, no bypass permission is introduced, and no protected version is deleted.
5. Production retention is applied only after an exact inventory preview, reviewed policy artifact, recovery-point classification, and post-apply readback.
6. Missing metadata, partial exports, unverified notification delivery and malformed review output fail closed.
7. A backup job may retry a transient dump once; it may never overwrite or disguise the failed attempt.

## 4. Zero-disclosure Infisical restore proof

### 4.1 Trust boundary

The proof runs only on Titan-1. Max keeps the age identity in 1Password and supplies only an `op://...` reference or a hidden local prompt. The reference is not the key.

The verifier:

1. resolves the latest `postgres/infisical/*.dump.age` object with the local read-capable AWS profile;
2. records object key, version ID, ciphertext bytes, last-modified time and non-secret S3 metadata;
3. downloads only the encrypted object into a mode-0700 temporary directory;
4. obtains the age identity from 1Password through `op read`;
5. passes the identity to `age` over an inherited anonymous file descriptor, never argv or disk;
6. streams decrypted bytes directly into `pg_restore` connected to a disposable `postgres:18` container whose data directory is Docker tmpfs and whose network is disabled;
7. computes the plaintext SHA-256 and byte count while streaming and compares both to S3 metadata;
8. verifies `pg_restore` success, catalog/table counts and a small fixed set of schema-only invariants;
9. stops/removes the container and deletes the encrypted temporary directory in `finally`;
10. writes a mode-0600 JSON attestation containing no secret values or restored data.

The verifier must refuse if:

- `op`, `age`, Docker or the AWS profile is unavailable;
- 1Password cannot return an age identity;
- the identity has an invalid age-secret-key shape;
- the latest object is missing required metadata;
- hash, byte count or TOC count differs;
- Docker is not using tmpfs or cannot disable networking;
- restore or any invariant fails;
- cleanup cannot remove the disposable container.

### 4.2 Local AI role

After deterministic success, an optional second command sends only the redacted attestation JSON plus a fixed review rubric to `llama3.3:70b` at `127.0.0.1:11434`. The response may summarize PASS/FAIL and missing evidence. It is secondary evidence and cannot convert a deterministic failure into success.

### 4.3 Attestation

Required fields:

- schema version and UTC timestamp;
- host identity `Titan-1`;
- S3 bucket, object key, version ID, last-modified and ciphertext bytes;
- expected and observed plaintext SHA-256/bytes;
- expected and observed TOC count;
- Postgres client/server versions;
- restore exit status, non-system schema count and table count;
- Docker `network=none`, `data_storage=tmpfs`;
- cleanup result;
- overall `PASS` only when every check passes;
- SHA-256 of the canonical attestation itself.

The attestation must not include table rows, secret names, the 1Password reference, key fingerprints derived from private material, environment dumps or raw subprocess output.

## 5. Secure Telegram credential installation

The existing rotated token is retained. A new local-only installer is added to Local SecOps:

1. Max supplies token and chat ID through 1Password references or hidden TTY prompts on Titan-1.
2. The installer validates format locally and calls Telegram `getMe`.
3. It sends a clearly labelled no-action-required canary to Max's chat and requires HTTP 2xx, JSON `ok=true`, and a numeric `message_id`.
4. Only after delivery succeeds does it atomically replace the two keys in `/Users/max/koskadeux-mcp/.env`, preserving unrelated lines and mode 0600.
5. It restarts no unrelated services. The watchdog reads the file on every invocation.
6. It records only timestamp, action, success/failure, HTTP status and message ID in the Local SecOps audit log.

Rollback is the installer's mode-0600 same-host backup of the prior `.env`; the backup contains secrets and must be removed after the new credential passes a second watchdog canary. No token value or token hash is logged.

The watchdog's `tg()` function must:

- use `curl --fail-with-body --silent --show-error`;
- parse the JSON response;
- require `ok=true` and numeric `message_id`;
- log the message ID on success;
- return non-zero on absent credentials, HTTP failure or API failure;
- cause the watchdog process to exit non-zero if any required alert cannot be delivered.

## 6. Retention and storage reduction

### 6.1 Classification

Every future backup object under the following families receives an S3 object tag:

- `retention=monthly` for the first successful UTC backup in a month;
- `retention=daily` otherwise.

Families:

- `postgres/ai-market`;
- `postgres/infisical`;
- each required `qdrant/<collection>`;
- `railway-config`;
- `cloudflare`.

For existing objects, the retention tool deterministically chooses the first successful object per family/month as monthly and classifies all other objects daily. The plan output lists every monthly key and aggregate daily/monthly counts and bytes.

`backup-health/`, `RESTORE-README.md`, audit evidence and unknown prefixes are excluded and remain untouched.

### 6.2 Lifecycle policy

The exact policy contains:

- `retention=daily`: expire current versions after 35 days; permanently remove eligible noncurrent versions one day after they become noncurrent;
- `retention=monthly`: expire current versions after 400 days; permanently remove eligible noncurrent versions one day after they become noncurrent;
- an untagged delete-marker cleanup rule only;
- no rule that changes Object Lock, encryption, versioning or public access;
- no lifecycle action on an unknown/unclassified prefix.

S3 Object Lock remains authoritative: a locked version cannot be deleted by lifecycle before its retain-until time.

### 6.3 Apply protocol

The retention tool defaults to plan-only and requires `--apply` plus the SHA-256 of the generated plan.

Apply order:

1. read and record bucket versioning, Object Lock, encryption and public-access state;
2. abort if any invariant differs;
3. tag the monthly recovery points;
4. tag remaining in-scope current objects daily;
5. verify all in-scope objects have exactly one accepted retention tag;
6. install the lifecycle policy;
7. read back and byte-compare its canonical JSON;
8. regenerate inventory and confirm no object was synchronously deleted;
9. record a redacted apply receipt in the runbooks audit directory and Living State.

Lifecycle is asynchronous and removal after eligibility is irreversible. Rollback can disable the rules before S3 acts, but cannot recover a permanently expired version. The plan must state this explicitly.

### 6.4 Qdrant growth decision

The approved 35-day daily policy is implemented first. It cannot make daily 5.8 GB full Qdrant snapshots small: Object Lock intentionally sets a 35-day physical floor.

A separate measured drill must prove that `knowledge_base_v2` can be rebuilt from Postgres within the four-hour full-platform RTO before its cadence is reduced. Until that proof exists, daily Qdrant snapshots remain required. Legacy `knowledge_base`, `action_logs` and `listings` may move to weekly cadence only after an owner/dependency query proves they are derived and non-authoritative.

## 7. Backup production hardening

### 7.1 Postgres

- Add exactly one retry for connection-reset/server-closed/transient network failures.
- Use bounded exponential backoff with jitter and a fresh temporary output path.
- Record the failed attempt before retry.
- Do not retry authentication, permission, disk-headroom, encryption, validation or upload failures.
- Never upload an artifact unless size, SHA-256 and `pg_restore --list` checks pass.
- Add relative-size anomaly gates against recent successful same-source artifacts:
  - warning below 60% or above 180% of the seven-run median;
  - critical below 20% or above 500%;
  - an explicit, time-bounded baseline reset records approved database cleanups so a legitimate 90% reduction is not treated indefinitely as corruption.

### 7.2 Qdrant

- Monitor and report every required collection independently.
- Record snapshot bytes and SHA-256 for each collection.
- A successful small collection cannot mask a stale or missing `knowledge_base_v2`.
- Add relative-size anomaly checks per collection.
- Preserve exact collection name and source cluster/version in health metadata.

### 7.3 Cloudflare

- Define DNS and zone settings as required sections for both zones.
- Treat HTTP error payloads, missing sections and schema mismatch as job failure.
- KV is explicitly classified per namespace as required or regenerable; do not silently include new namespaces.
- Upload may occur for forensic evidence under a `status=failed` health record, but must not advance the successful-backup freshness marker.
- Current token scope must include the permission needed to read zone settings before Cloudflare recovery is declared green.

## 8. Independent monitoring

### 8.1 Titan-1

The six-hour watchdog remains independent of Infisical. It checks:

- main Postgres;
- Infisical Postgres;
- every required Qdrant collection;
- Railway configuration;
- Cloudflare complete-success marker;
- current monthly recovery point for every family after UTC day 2.

It checks freshness, non-zero size, expected metadata and size anomaly status. Alert delivery itself is a required check.

### 8.2 Backend

Enable `backup-watchdog-hourly` in Celery beat only after production credentials and the internal endpoint are proven. The task must fail, retry and escalate when the endpoint is unavailable; missing `INTERNAL_API_KEY` is critical configuration drift, not `skipped`.

### 8.3 GitHub

`backup-verify.yml` becomes a secondary dead-man's switch:

- threshold 30 hours, aligned with nightly schedules and scheduler delay;
- reads S3-canonical status;
- one open issue per incident fingerprint;
- updates the existing issue while unhealthy;
- closes it automatically after two consecutive healthy checks;
- links only current S3/Railway instructions, never deleted GCS workflows.

## 9. Recovery objectives and drills

- Main Postgres RPO: 24 hours; alert no later than 30 hours after the last success.
- Infisical Postgres RPO: 24 hours; alert no later than 30 hours.
- Qdrant RPO: 24 hours until a rebuild drill supports a lower snapshot cadence.
- Main Postgres RTO: two hours from declaration.
- Full platform RTO: four hours from declaration.
- Alert-delivery RTO: 30 minutes.

Drills:

- monthly automated integrity/metadata verification;
- quarterly isolated full main-Postgres restore;
- quarterly isolated Qdrant restore;
- quarterly Max-assisted Infisical zero-disclosure restore;
- semiannual full replacement exercise: Infisical, Railway topology, source, main Postgres, Qdrant, Cloudflare and signed application validation.

## 10. Implementation scope

### `aidotmarket/ai-market-backend`

- `scripts/backup_pg.py`
- `scripts/backup_qdrant_s3.py`
- `app/allai/agents/sysadmin/backup_monitor.py`
- `app/core/celery_app.py`
- `app/tasks/scheduled.py`
- `.github/workflows/backup-verify.yml`
- focused unit/integration tests

### `aidotmarket/runbooks`

- `scripts/s3_backup_watchdog.sh`
- `scripts/cloudflare_export.py`
- `scripts/railway_config_export.py`
- Qdrant/config/export wrappers as required for tagging
- new plan/apply retention tool and canonical lifecycle JSON
- new deterministic local Infisical restore verifier
- new secure Telegram installer or reviewed Local SecOps deployment payload
- `backup-and-recovery.md`
- `disaster-recovery.md`
- `aws-s3.md`
- `local-secops.md`
- versioned redacted audit/receipt templates

### Titan-1 local deployment

- reviewed scripts deployed under `/Users/max/local-secops/` with owner-only execute/read permissions;
- LaunchAgent/watchdog script updated only from reviewed Git content;
- no secret file committed or copied into a worktree.

## 11. Test and review gates

Required before production:

1. unit tests for classification across month boundaries, failed first-day backup, unknown prefix, versioned objects and idempotent rerun;
2. lifecycle policy snapshot test and AWS readback parser test;
3. mocked Object Lock refusal and no-delete invariant tests;
4. Postgres retry classification tests and clean temporary-file cleanup;
5. size-baseline reset and anomaly tests;
6. Qdrant per-collection masking regression test;
7. Cloudflare 403/missing-section regression tests;
8. Telegram installer and delivery-response tests with secret redaction assertions;
9. watchdog non-zero exit on Telegram failure;
10. Infisical verifier tests with a disposable age identity and synthetic PG18 dump, including proof that no plaintext file is created;
11. GitHub workflow threshold, deduplication and recovery-close tests;
12. exact-commit Council review with builder excluded;
13. production cutover one subsystem at a time, each with readback and rollback checkpoint.

## 12. Production acceptance evidence

Gate 4 requires all of:

- current main-Postgres and Qdrant restore evidence remains green;
- Max-assisted Infisical attestation is `PASS`;
- Telegram canary returns and logs a real message ID;
- deliberately induced stale test fixture produces one Telegram alert and one deduplicated GitHub issue;
- backend scheduled poll is observed running;
- Cloudflare export contains valid zone settings for both zones and no error records;
- every in-scope current S3 object is classified daily/monthly;
- lifecycle policy canonical readback matches the reviewed artifact;
- no Object Lock/versioning/encryption/BPA invariant changed;
- post-policy inventory records total bytes and projected 35/400-day steady state;
- source runbooks are merged and the same reviewed disaster-recovery map is uploaded/versioned at `RESTORE-README.md`;
- a replacement drill report states achieved RPO/RTO and any remaining exception.

## 13. Explicitly deferred destructive data cleanup

This BQ does not delete production database rows.

`qdrant_sync_outbox` terminal rows and old `state_events` are storage-reduction candidates, but their business/audit retention periods are not yet explicit. A separate reviewed migration must define:

- retention duration for `done` and `dead_letter` outbox rows;
- whether `state_events` is legally/audit authoritative;
- archive destination outside the same full-dump database;
- rebuild and rollback proof.

Until that policy is approved, size reduction comes from S3 lifecycle and the already-completed database cleanup, not unreviewed row deletion.
