# BQ-BACKUP-RECOVERY-HARDENING-S1322 — Gate 1 Design

Status: R7_AUTHORED_PENDING_REVIEW
Owner: Vulcan S1322
Directive: Max, 2026-07-24
Class: security-sensitive production resilience and retention

R1 commit: `362f234`
R1 reviews: MP nonapproval (`RepairExhaustedError`); GLM `APPROVE_WITH_MANDATES`; CC `APPROVED_WITH_MANDATES` / revise.

R2 folds every GLM and CC mandate: Keychain replaces plaintext Telegram storage; monthly objects receive explicit 400-day COMPLIANCE retention; classification is performed by a single fail-toward-retention controller; the first asynchronous deletion set requires exact Max approval; restore completeness uses a critical-schema manifest; age identity memory/FD handling is hardened; hash provenance and self-hash canonicalization are explicit; untagged/pending objects alert; Qdrant gains retry and baseline-reset semantics.

R2 reviews: GLM `APPROVE_WITH_NITS`; CC raw result contained one mandate but its envelope was malformed and therefore nonapproval; MP remained nonapproval (`RepairExhaustedError`). R3 folds the CC mandate and findings plus all GLM nits: monthly selection is bound to producer integrity evidence, corrupt monthly points have a safe promotion path, identity zeroization occurs only after the full pipe write closes, JSON Canonicalization Scheme is pinned, `/dev/fd/N` wording is precise, and Telegram `.env` removal requires a consumer inventory.

R3 reviews: GLM `APPROVE_WITH_NITS`; CC's raw content said `APPROVE` with two minor clarifications but its fenced/prefaced envelope was malformed and is therefore nonapproval; the MP R2 review remained in flight against the prior exact head. R4 folds every R3 nit: a Living State CAS lease serializes the retention controller, retain-until is defined from classification time, interrupted `op read` zeroizes and refuses, tag checks are separated, no-candidate promotion remains critical, and attestation verification resets rather than removes the self-hash field.

R4 reviews: GLM `APPROVE_WITH_NITS`; CC's raw content said `APPROVE` with two minor findings but its response envelope contained an extra key and is therefore nonapproval. The MP review against the prior R2 head ended in `RepairExhaustedError`; this is a tooling failure and nonapproval, not a substantive objection, and cannot be folded as review feedback. R5 folds the substantive GLM/CC findings: every retention mutator shares one concrete lease, baseline-reset receipts are fully specified, Telegram canaries have a fixed operator-safe label, and the post-24-hour Keychain rollback boundary is explicit.

R5 reviews: GLM `APPROVE_WITH_NITS`; CC's raw content required one lease/apply-protocol correction and two Keychain clarifications, but its fenced response was malformed and is therefore nonapproval. R6 folds all substantive feedback: the canary prefix is ASCII, the conditional weekly Qdrant RPO is explicit, lease renewal is scheduled, read-only manifest approval is separated from the leased mutating phase with mandatory revalidation, and Keychain retention/deletion/recovery preconditions are deterministic.

R6 reviews: GLM `APPROVE_WITH_NITS`; CC returned a valid exact-head `APPROVE` with two minor documentation findings. R7 folds every GLM nit and the actionable CC hash-provenance finding: Keychain cleanup uses an auditable one-shot LaunchAgent and a fully defined receipt, the approved manifest hash has a durable non-secret approval receipt, and partial retention applies stop safely and resume only from fresh inventory under a new lease. The full artifact contains section 13, so CC's conditional cross-reference observation required verification but no content change.

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

Qdrant retains a 24-hour RPO until its rebuild drill passes. If Max later activates the approved weekly full-snapshot cadence after that proof, the accepted full-snapshot RPO becomes seven days while the rebuild-from-Postgres path remains bounded by the four-hour full-platform RTO.

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

1. The offline age identity, Telegram token, decrypted Infisical data and provider credentials never enter chat, a networked model, logs, command-line arguments, Git, or a persistent plaintext file. Local secrets required by unattended jobs live in macOS Keychain, not `.env`.
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
5. passes the identity to `age` over an inherited anonymous file descriptor, never placing secret bytes in argv or disk; argv may contain only the non-secret descriptor path `/dev/fd/N`; the parent disables core dumps, locks and later zeroes the minimal identity buffer, creates the descriptor close-on-exec, and explicitly passes it only to the `age` child;
6. streams decrypted bytes directly into `pg_restore` connected to a disposable `postgres:18` container whose data directory is Docker tmpfs and whose network is disabled;
7. computes the plaintext SHA-256 and byte count while streaming and compares both to S3 metadata;
8. verifies `pg_restore` success, catalog/table counts and every object in a versioned expected-critical-schema manifest;
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

`op read` must return exactly one raw `AGE-SECRET-KEY-...` identity line. The verifier disables core dumps for itself and children (`RLIMIT_CORE=0`), uses `mlock` for the in-process identity buffer, writes the complete identity to the pipe, closes the write end, and only then zeroes/unlocks the source buffer. It refuses if any write is partial or any memory/descriptor control cannot be applied. The anonymous descriptor is inherited by `age` only; Docker, AWS, Ollama and later subprocesses cannot inherit it.

A timeout, signal, short read, broken pipe or interrupted `op read` immediately closes both pipe ends, zeroes/unlocks every buffered identity byte, terminates any child, and returns failure. Partial identity material is never retried or reused.

The expected-critical-schema manifest is produced from a known-good Infisical schema, versioned without data or secret values, and independently reviewed. A restore cannot pass if any required schema, table, extension or migration-history relation is absent. Counts alone are informational and never establish completeness.

The plaintext hash stored beside the ciphertext is a transport/accidental-corruption control, not independent authenticity against an actor able to replace both object and metadata. Successful age AEAD authentication proves ciphertext integrity under the offline identity; Object Lock/versioning and the recorded version ID provide the storage provenance boundary.

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
- SHA-256 of RFC 8785 JSON Canonicalization Scheme bytes with `attestation_sha256` set to JSON `null`, followed by insertion of the resulting digest.

Independent verification must parse the attestation, set the existing `attestation_sha256` field back to JSON `null` without deleting the field, reproduce RFC 8785 bytes, and compare the computed digest in constant time.

The attestation must not include table rows, secret names, the 1Password reference, key fingerprints derived from private material, environment dumps or raw subprocess output.

## 5. Secure Telegram credential installation

The existing rotated token is retained. Before installation, Max confirms the same rotated token is durably retrievable from 1Password or another approved secure source. It is not copied back into `.env`. A new local-only installer stores it in a versioned macOS Keychain item:

1. Max supplies token and chat ID through the `security add-generic-password ... -w` Keychain prompt on Titan-1. The value is entered directly into Apple's prompt and is never visible to the installer, shell history or argv.
2. The installer reads only the candidate Keychain items, validates format locally and calls Telegram `getMe`.
3. It sends a canary beginning exactly `[BACKUP CANARY - NO ACTION REQUIRED]`, followed by the session/task ID, to Max's chat and requires HTTP 2xx, JSON `ok=true`, and a numeric `message_id`.
4. Only after delivery succeeds does it atomically switch a non-secret, mode-0600 pointer file to the versioned candidate Keychain service names.
5. Before changing `.env`, it inventories every repository, LaunchAgent and running process configuration that references `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID`. It removes the stale lines from `/Users/max/koskadeux-mcp/.env` only after proving the watchdog is the sole live consumer or migrating every other consumer to its own reviewed Keychain pointer. The Keychain-backed watchdog must pass a second canary first. No backup of the stale plaintext values is created.
6. It restarts no unrelated services. The watchdog resolves the versioned Keychain service names from the pointer file on every invocation.
7. It records only timestamp, action, success/failure, HTTP status and message ID in the Local SecOps audit log.

Rollback during the first 24 hours is an atomic pointer switch to the prior Keychain service names. After the second canary, the installer registers a mode-0600, one-shot per-user LaunchAgent whose `ProgramArguments` contain only the reviewed cleanup helper path and non-secret versioned Keychain service/account names. Its calendar trigger is no later than 24 hours after that canary. The helper deletes only the named superseded items, records success or failure, disables the job after success, and leaves its non-secret plist for audit until the next reviewed cleanup. The watchdog alerts if the job is missing, fails, or any superseded item outlives the deadline.

The deletion receipt records scheduled time, actual attempt and completion times, local UID, versioned service/account names, second-canary message ID, outcome, and LaunchAgent label; it contains no token value or token-derived hash. After deletion, rollback to those items is intentionally unavailable; recovery requires Max to re-enter the same already-rotated token from the confirmed approved secure source. That accepted boundary does not require or authorize provider-side rotation. No plaintext rollback file, token value or token hash is created or logged.

The watchdog's `tg()` function must:

- use `curl --fail-with-body --silent --show-error`;
- parse the JSON response;
- require `ok=true` and numeric `message_id`;
- log the message ID on success;
- return non-zero on absent credentials, HTTP failure or API failure;
- cause the watchdog process to exit non-zero if any required alert cannot be delivered.

## 6. Retention and storage reduction

### 6.1 Classification

Every future backup object under the following families is uploaded with a unique, collision-resistant date/time key. Upload refuses an existing key. The write-only backup identity receives no tagging or retention permission, so a compromised writer cannot downgrade a recovery point. New objects are initially untagged and therefore match no expiration rule.

A single daily Railway `backup-retention-controller` classifies new objects only after listing the complete family/month and resolving producer health evidence:

- `retention=monthly` for the first integrity-verified UTC backup in a month, after extending that exact object version's Object Lock COMPLIANCE retain-until to 400 days;
- `retention=daily` otherwise.

Families:

- `postgres/ai-market`;
- `postgres/infisical`;
- each required `qdrant/<collection>`;
- `railway-config`;
- `cloudflare`.

For existing objects, the retention tool deterministically chooses the first successful object per family/month as monthly and classifies all other objects daily. It extends every selected monthly object version to 400-day COMPLIANCE retention before applying the monthly tag.

“Integrity-verified” means the exact object version has a producer health record with `status=ok`; landed byte count equals the producer count; required SHA-256/TOC or Qdrant snapshot metadata is present and within policy; and no size-anomaly state is critical. A mere object listing, non-zero size or successful upload is insufficient. Cloudflare and topology exports additionally require their schema/completeness checks.

Classification fails toward retention: any list, health-evidence, tag, version-ID, lock-extension or concurrency uncertainty leaves objects untagged, which no lifecycle rule expires, and raises an alert. A daily reconciliation pass verifies every in-scope object has exactly one accepted tag and every completed family/month has at least one integrity-verified, 400-day-locked monthly point. It corrects unambiguous drift and fails closed on ambiguity. At 00:00 UTC on day 3, absence of a verified monthly point is critical; the two-day window permits a retry after a failed first-night job and cannot extend silently.

Every tag or retention mutator uses the same optimistic-CAS Living State lease, including the daily controller, reconciliation correction, monthly-point promotion, and the mutating phase of any operator apply command. The lease expires after 15 minutes and is renewed by CAS no later than 10 minutes after acquisition or the prior renewal. A mutator acquires it before the fresh inventory read that authorizes writes, includes the persisted lease ID in every write receipt, and renews only by CAS. Failure to acquire, renew or release the lease performs no tag/retention write and alerts. A stale lease can be replaced only after expiry and a fresh inventory read. No alternate operator path may bypass the shared lease.

If a monthly point is later found corrupt or unrestorable, reconciliation never downgrades or deletes its COMPLIANCE lock. It promotes the next integrity-verified object from that family/month by extending it to 400 days and tagging it monthly, records a replacement receipt, and alerts until the promoted point passes the appropriate restore/integrity check. Multiple locked monthly points are valid when backed by the replacement receipt; “exactly one” is not an invariant.

If no promotable integrity-verified candidate exists, the family/month stays in sustained critical state, no lock or tag is changed, and the operator must create and verify a replacement recovery point. The condition cannot self-clear from the corrupt object.

`backup-health/`, `RESTORE-README.md`, audit evidence and unknown prefixes are excluded and remain untouched.

The controller uses a dedicated IAM identity, separate from the backup writer, with only:

- bucket list/version-list for the approved prefixes;
- get/put object tagging;
- get/put Object Lock retention;
- no `GetObject`, `DeleteObject`, bypass, encryption, versioning, public-access or lifecycle-configuration permission.

An IAM/bucket-policy condition permits the controller's `PutObjectRetention` only for a requested retain-until 399–401 days from the classification or promotion call. The controller computes an absolute UTC timestamp from its trusted current time, not from object creation. COMPLIANCE prevents shortening an existing retain-until regardless. The controller cannot install or alter the lifecycle policy; that remains an exact-reviewed operator action.

### 6.2 Lifecycle policy

The exact policy contains:

- `retention=daily`: expire current versions after 35 days; permanently remove eligible noncurrent versions one day after they become noncurrent;
- `retention=monthly`: expire current versions after 400 days; permanently remove eligible noncurrent versions one day after they become noncurrent;
- an untagged delete-marker cleanup rule only;
- no rule that changes Object Lock, encryption, versioning or public access;
- no lifecycle action on an unknown/unclassified prefix.

S3 Object Lock remains authoritative: a locked version cannot be deleted by lifecycle before its retain-until time.

The noncurrent-version actions use the same tag filters as their current-version rules. Unique-key uploads mean normal backups do not create noncurrent versions; the rule exists only for exceptional administrative replacement. Monthly versions have explicit 400-day COMPLIANCE retention, so neither current nor noncurrent expiration can remove them earlier. Daily backups are guaranteed restorable for the complete 35-day lock window; no RPO/RTO or drill depends on a day-35 object after it becomes lifecycle-eligible.

### 6.3 Apply protocol

The retention tool defaults to plan-only. Plan generation and human approval are read-only and do not acquire or hold the mutator lease. Max's exact approval writes a non-secret, immutable approval receipt in Living State and the versioned runbook audit directory containing the plan SHA-256, imminent-deletion-manifest SHA-256, approval timestamp, approver, and manifest summary totals. `--apply` requires the plan SHA-256 and that approval-receipt ID; it refuses a missing, mutable, mismatched, or differently approved receipt.

Apply order:

1. read and record bucket versioning, Object Lock, encryption and public-access state;
2. abort if any invariant differs;
3. produce a separate imminent-deletion manifest listing every already-older-than-35-days daily candidate by family, key, version ID, bytes, date and retain-until, plus the oldest recovery point that survives for each family;
4. require Max's exact approval of that manifest;
5. at `--apply`, acquire the shared mutator lease, perform a fresh invariant and candidate inventory read under that lease, reproduce the plan and imminent-deletion manifest, and abort unless both SHA-256 values exactly match Max's approved artifacts;
6. extend the selected monthly versions to 400-day COMPLIANCE retention and verify readback;
7. tag the monthly recovery points;
8. tag remaining in-scope current objects daily;
9. verify all in-scope objects have exactly one accepted retention tag;
10. install the lifecycle policy;
11. read back and byte-compare its canonical JSON;
12. regenerate inventory, confirm no object was synchronously deleted, and state that the reviewed deletion manifest is expected to be processed asynchronously;
13. record a redacted apply receipt, including the lease and both approved hashes, in the runbooks audit directory and Living State, then release the lease by CAS.

Lifecycle is asynchronous and removal after eligibility is irreversible. Rollback can disable the rules before S3 acts, but cannot recover a permanently expired version. The plan must state this explicitly.

All pre-lifecycle writes are monotonic and idempotent: a monthly COMPLIANCE extension is never shortened, and tags are reconciled from fresh inventory. If lease renewal or any write/readback fails, the process stops before its next mutation, records the completed steps and exact object versions in a partial-apply receipt, releases the lease if still owned, and alerts. It performs no compensating lock/tag mutation. A retry must acquire a new lease, reread all state, revalidate both approved hashes, and resume idempotently. The lifecycle policy is installed only after every monthly extension/tag and daily tag has verified readback; failure after lifecycle installation is critical and triggers immediate policy readback plus inventory reconciliation, never an assumption of rollback or synchronous deletion.

### 6.4 Qdrant growth decision

The approved 35-day daily policy is implemented first. It cannot make daily 5.8 GB full Qdrant snapshots small: Object Lock intentionally sets a 35-day physical floor.

A separate measured drill must prove that `knowledge_base_v2` can be rebuilt from Postgres within the four-hour full-platform RTO before its cadence is reduced. Until that proof exists, daily Qdrant snapshots remain required. Legacy `knowledge_base`, `action_logs` and `listings` may move to weekly cadence only after an owner/dependency query proves they are derived and non-authoritative.

Any activated weekly Qdrant full-snapshot schedule has a seven-day freshness threshold and seven-day full-snapshot RPO. Monitoring must switch thresholds only in the same reviewed change that switches cadence, retain the rebuild-path four-hour RTO check, and alert if either path is unavailable.

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

Each baseline-reset receipt records timestamp, source/family, reason and change reference, old median and sample count, new expected range, Max approval or exact Council decision reference, and `expires_at`. It applies to one run by default and may never exceed 72 hours. The receipt is stored in Living State and the versioned runbook audit trail; expiry without a new stable seven-run baseline alerts and restores normal anomaly enforcement.

### 7.2 Qdrant

- Monitor and report every required collection independently.
- Record snapshot bytes and SHA-256 for each collection.
- A successful small collection cannot mask a stale or missing `knowledge_base_v2`.
- Add relative-size anomaly checks per collection.
- Retry one transient snapshot/download/upload failure with bounded backoff; never retry authentication, schema, size, hash or collection-not-found failures.
- Support the same explicit, time-bounded baseline-reset receipt used for Postgres after an approved reindex or migration.
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

It separately checks retention classification:

- any in-scope object that is missing a tag, has an unknown tag, has conflicting tags, or remains untagged beyond the controller's daily reconciliation window.

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
- Qdrant RPO: 24 hours until the rebuild drill passes; seven days only after the reviewed weekly-cadence switch described in sections 6.4 and 13.
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
2. tests that an unverified/corrupt first object is never made monthly, day-3 absence alerts, and a later verified object is promoted without shortening the corrupt object's lock;
3. shared-lease tests proving the controller, reconciliation, promotion, and operator apply paths cannot write concurrently or bypass the 15-minute lease; tests also cover renewal by minute 10, lease-free read-only planning, approval-receipt persistence, fresh under-lease inventory, exact revalidation of both approved hashes before the first write, partial-apply receipts, stop-before-next-write behavior, and idempotent resume under a new lease;
4. lifecycle policy snapshot test and AWS readback parser test;
5. mocked Object Lock refusal and no-delete invariant tests;
6. Postgres retry classification tests and clean temporary-file cleanup;
7. size-baseline reset and anomaly tests covering every receipt field, the one-run default, the 72-hour maximum, expiry alerting, and restoration of normal enforcement;
8. Qdrant per-collection masking regression test;
9. Cloudflare 403/missing-section regression tests;
10. Telegram installer and delivery-response tests with secret redaction assertions, the exact canary prefix, deterministic one-shot LaunchAgent scheduling, deletion-receipt fields, missed-cleanup alerting, and proof that `.env` lines remain until all live consumers are inventoried/migrated;
11. watchdog non-zero exit on Telegram failure;
12. Infisical verifier tests with a disposable age identity and synthetic PG18 dump, including proof that no plaintext file is created and partial-pipe writes fail closed;
13. GitHub workflow threshold, deduplication and recovery-close tests;
14. exact-commit Council review with builder excluded;
15. production cutover one subsystem at a time, each with readback and rollback checkpoint.

## 12. Production acceptance evidence

Gate 4 requires all of:

- current main-Postgres and Qdrant restore evidence remains green;
- Max-assisted Infisical attestation is `PASS`;
- the attestation's expected-critical-schema manifest check is complete and green;
- Telegram canary returns and logs a real message ID;
- deliberately induced stale test fixture produces one Telegram alert and one deduplicated GitHub issue;
- backend scheduled poll is observed running;
- Cloudflare export contains valid zone settings for both zones and no error records;
- every in-scope current S3 object is classified daily/monthly;
- lifecycle policy canonical readback matches the reviewed artifact;
- no Object Lock/versioning/encryption/BPA invariant changed;
- post-policy inventory records total bytes and projected 35/400-day steady state;
- the reviewed imminent-deletion manifest and Max's exact approval are attached to the apply receipt;
- source runbooks are merged and the same reviewed disaster-recovery map is uploaded/versioned at `RESTORE-README.md`;
- a replacement drill report states achieved RPO/RTO and any remaining exception.

## 13. Approved source-data retention, separately migrated

Max approved the following retention policy on 2026-07-24:

- `qdrant_sync_outbox` rows with terminal status `done`: 30 days;
- `qdrant_sync_outbox` rows with terminal status `dead_letter`: 180 days;
- `state_events`: 12 months;
- after a measured rebuild drill proves `knowledge_base_v2` recovery within the four-hour full-platform RTO, Qdrant full-snapshot cadence may move from daily to weekly.

This Gate-1 BQ does not itself delete production database rows or reduce Qdrant cadence. A separate exact-reviewed migration must implement bounded batches, foreign-key/dependency checks, dry-run counts, archive requirements for authoritative `state_events`, immutable receipts, post-migration validation, and rollback/rebuild proof. It must treat unknown outbox states as retained and fail closed.

Until that migration and the Qdrant rebuild drill pass their gates, size reduction comes from S3 lifecycle and the already-completed database cleanup.
