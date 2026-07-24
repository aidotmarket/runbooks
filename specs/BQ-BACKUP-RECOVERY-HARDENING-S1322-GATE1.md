# BQ-BACKUP-RECOVERY-HARDENING-S1322 — Gate 1 Design

Status: R11_AUTHORED_PENDING_REVIEW
Owner: Vulcan S1322
Directive: Max, 2026-07-24
Class: security-sensitive production resilience and retention

Review lineage: R1–R8 established the zero-disclosure restore, Keychain cutover, 35/400-day retention, Object Lock, mutation lease, anomaly reset and Qdrant controls. R8 GLM/CC approved; direct MP returned one blocker and six majors. R9 folded fenced journaling, version-complete lifecycle approval, measured alerts, baseline epochs, Qdrant fidelity, negative secret tests and fail-closed acceptance. R9 MP returned one blocker/two majors; GLM/CC approved with findings. R10 folded deterministic retry approval, subprocess secrecy, complete recovery inventory, named journal states and event-driven alert fallback. At exact head `69cde46b329b302fc6768f3a273ddf8f83ba81e3`, CC approved with two clarity findings; GLM's approval was nonaccepting because its input truncated sections 7–13. R11 folds the CC findings and compacts this complete normative artifact below the reviewer input limit without relaxing a control.

## 1. Outcome and verified starting point

ai.market must be demonstrably restorable, fail loudly when any required backup or alert is late/incomplete, and stop retaining daily full backups indefinitely.

This design delivers:

- Titan-1-only, zero-disclosure Infisical restore proof;
- daily S3 retention for 35 days and monthly recovery points for 400 days without weakening Object Lock;
- secure use of Max's already-rotated Telegram token, with no further rotation;
- delivery-proven primary and independent fallback alerts;
- complete recovery-source discovery, per-source freshness/quality checks and measured replacement drills;
- bounded Postgres retry, fail-closed Cloudflare export, and a fidelity gate before Qdrant cadence reduction.

The S1322 audit verified:

- Railway backup deployment `0103b798-f0e3-4592-b601-ace99f0b7b86` failed on 19 July during `COPY public.qdrant_sync_outbox`; no main-DB dump succeeded on 19–20 July, leaving about 72 hours between snapshots.
- The latest main-Postgres dump and `knowledge_base_v2` snapshot restored successfully in disposable environments.
- The latest Infisical object is encrypted and structurally plausible but has not been decrypted/restored with Max's offline key.
- Titan detected the misses, but its stale on-disk Telegram token caused delivery failure. Max has since rotated the token.
- GitHub's six-hour freshness threshold conflicts with the nightly schedule; backend task `poll_backup_watchdog` exists but its Celery beat entry is disabled; Cloudflare uploads contain required zone-settings HTTP 403 errors.
- The versioned/Object-Locked/encrypted/private bucket has no lifecycle policy. On 24 July, classified prefixes held 322 current objects / 257,083,842,321 bytes: 17 candidate monthly points / 9,342,163,753 bytes and 305 daily objects / 247,741,678,568 bytes.
- New main dumps are about 0.37 GB after the 90% database cleanup; old dumps are much larger, while `knowledge_base_v2` is now the main growth source.
- `git-mirrors/` is empty, and AIM Data has a separate Railway Postgres dependency absent from the current recovery matrix.

### 1.1 Authoritative recovery inventory

Before implementation freezes scope, a deterministic job enumerates every Railway project/environment/service/database, Cloudflare account/zone/Worker/KV dependency, S3 recovery prefix, required GitHub repository, Titan-hosted production state, third-party configuration dependency, and customer-custodied boundary used by ai.market, AIM Data or vectorAIz. Its canonical SHA-256 identifies the authoritative inventory.

Each row states owner, production classification, authoritative data class, backup destination/schedule, monitor, RPO/RTO, restore procedure, last successful backup and restore proof, and `covered` or exact exclusion. Live discovery is reconciled quarterly and before Gate 4; no silent addition/removal is allowed.

An exclusion needs Max's exact approval of row/scope/reason, evidence of non-production, regenerability, customer custody or independent backup, residual risk, recovery method, review date and expiry. An older product-wide exclusion cannot silently exclude a newly discovered dependency. AIM Data Railway Postgres remains uncovered until backup/restore/monitoring evidence or its exact exclusion exists. Source is uncovered for independent replacement until every required repo has a verified S3 mirror or exact-approved tested independent source; an empty prefix never passes.

## 2. Security and safety invariants

1. The age identity, Telegram token, decrypted Infisical bytes/rows and provider credentials never enter chat, a networked model, logs, argv, Git or persistent plaintext. Unattended local secrets use macOS Keychain, not `.env`.
2. Local Ollama sees only an allow-listed redacted attestation. Deterministic programs perform cryptographic and restore verification.
3. Object Lock stays COMPLIANCE; no retain-until is shortened, bypass permission added, versioning/encryption/BPA weakened, or protected version deleted.
4. Retention apply requires complete version inventory, reviewed canonical policy, exact imminent-deletion manifest, Max's exact approval and post-write readback.
5. Missing metadata, partial export, unverified delivery, ambiguous lifecycle clock, drift or malformed/qualified Council output fails closed.
6. A backup may retry one classified transient failure but may not overwrite/disguise a failed attempt.
7. Production writes/deletes and offline-key use remain blocked until their stated gates and local user action.

## 3. Zero-disclosure Infisical restore proof

### 3.1 Titan-only data path

Max keeps the age identity in 1Password and supplies an `op://` reference or hidden local prompt on Titan-1; neither is sent to Codex. The deterministic verifier:

1. selects the latest `postgres/infisical/*.dump.age` version and records nonsecret S3 provenance/metadata;
2. downloads ciphertext only into a mode-0700 temporary directory;
3. obtains exactly one raw `AGE-SECRET-KEY-...` line from `op read`;
4. passes it only to `age` over an anonymous FD; decrypted bytes flow through anonymous pipes to hashing and `pg_restore`;
5. restores into disposable Postgres 18 with tmpfs data and `network=none`;
6. compares plaintext SHA-256/bytes and TOC metadata; checks a reviewed, versioned critical-schema manifest (schemas, tables, extensions and migrations);
7. removes the container and encrypted temporary directory in `finally`;
8. emits only a mode-0600 redacted attestation.

The parent and children run with `RLIMIT_CORE=0`. The minimal identity buffer must `mlock`; the complete pipe write closes before zeroize/unlock. Exact per-child environment and FD allow-lists prevent inheritance by AWS, Docker, `pg_restore`, Postgres, cleanup or Ollama. No database password appears in argv/environment; restore traffic uses only the isolated local container channel.

Each process group has a deadline. Timeout, signal, partial write, broken pipe, downstream close or interrupted `op read` closes FDs, terminates/reaps children and zeroes buffers. Any unavailable tool/profile/key, invalid identity shape, metadata/hash/TOC/schema mismatch, tmpfs/network failure, memory/FD control failure, restore failure or incomplete cleanup refuses PASS.

Raw stdout/stderr, verbose/debug tracing, shell traces, core/container logs and environment/command dumps are forbidden. Required catalog output is bounded and parsed in memory, rejected for forbidden content, reduced to allow-listed counts/digests and zeroed. Child errors become fixed nonsecret failure class plus numeric status. Before exit, leak probes scan child argv/environment/FDs, temporary paths, mounts/log settings and the audit payload; inability to prove no secret/restored-data persistence is failure.

Age AEAD authenticates ciphertext; SHA metadata detects transport corruption but is not independent authenticity against replacement of both object and metadata. Object Lock/versioning plus exact version ID supply storage provenance.

### 3.2 Attestation and local AI

The allow-listed attestation records schema/time/host, bucket/key/version/last-modified/ciphertext bytes, expected/observed plaintext hash/bytes/TOC, client/server versions, restore/catalog counts, tmpfs/network controls, RLIMIT/mlock/zeroization/FD/interruption/cleanup outcomes, overall PASS, and RFC 8785 self-hash. Hashing canonicalizes with existing `attestation_sha256=null`; independent verification repeats this and constant-time compares.

It excludes rows, secret names, 1Password reference, private-material fingerprints, environment data and raw child output; any unknown field or forbidden-pattern match fails. Only after deterministic PASS may optional `llama3.3:70b` at `127.0.0.1` review this attestation/rubric. It cannot override failure.

## 4. Telegram cutover and fail-loud delivery

### 4.1 Keychain cutover

Max confirms the rotated token is recoverable from an approved secure source, then enters token/chat ID directly into Apple's `security add-generic-password -w` prompts for versioned Keychain items; values never enter installer argv/history. The installer reads only candidate items, validates locally, calls `getMe`, and sends `[BACKUP CANARY - NO ACTION REQUIRED]` plus session/task ID. It requires HTTP 2xx, JSON `ok=true`, numeric `message_id`, then atomically switches a nonsecret mode-0600 pointer.

Before `.env` change, it inventories repositories, LaunchAgents and running configurations referencing either Telegram variable. Stale lines in `/Users/max/koskadeux-mcp/.env` are removed without plaintext backup only after all consumers are migrated and the Keychain-backed watchdog passes a second canary. No unrelated service restarts.

For 24 hours rollback is pointer reversal. After the second canary, a mode-0600 one-shot user LaunchAgent (fixed helper plus nonsecret item names only) deletes named superseded Keychain items by the deadline, writes a nonsecret receipt to both audit stores and disables itself. The watchdog alerts on missing/failed/late cleanup. Receipt fields: schedule/attempt/completion, UID, item names, second-canary message ID, outcome and label. The disabled plist remains until next reviewed cleanup or 90 days, then is removed only after both receipts. After deletion, recovery is local re-entry of the same rotated token, not provider re-rotation.

### 4.2 Secret-safe Telegram sender

A reviewed in-process HTTPS client—not `curl` or any child—reads Keychain values into locked memory, constructs the endpoint internally, disables inherited proxies/debug tracing, verifies TLS, limits one attempt to a five-second connect/read budget, accepts only allow-listed nonsecret message fields, parses bounded JSON in memory, and zeroes response/credential buffers. Token-bearing URL, request/body, token, chat ID, Keychain output and raw response/exception never reach argv, environment, process lists, crash reports, stdout/stderr or logs.

Success requires `ok=true` and numeric message ID. Logs contain only fixed error class, HTTP status and success message ID. Missing credentials, TLS/timeout/HTTP/parse/API failure exits nonzero. Exceptions are normalized after forbidden-content scanning. Tests force every failure/signal/crash path and probe process/audit artifacts for leakage.

## 5. Retention and storage reduction

### 5.1 Classification and Object Lock

Future uploads use collision-resistant unique keys and refuse overwrite. The writer cannot tag or change retention. New objects remain untagged and match no expiration rule until one daily controller classifies these families:

- `postgres/ai-market`, `postgres/infisical`;
- every required `qdrant/<collection>`;
- `railway-config`, `cloudflare`.

The bucket's default 35-day COMPLIANCE retention remains mandatory for every new data object. Classification never shortens it; selected monthly versions are extended from classification/promotion time to 400 days before tagging.

The first integrity-verified UTC object per family/month becomes `retention=monthly` only after its exact version receives a 400-day COMPLIANCE extension; other data versions become `retention=daily`. Integrity requires exact producer `status=ok`, matching bytes, required SHA/TOC/snapshot metadata, noncritical anomaly state and, for topology/Cloudflare, schema completeness. Listing/nonzero upload alone is insufficient.

Existing classification uses fully paginated `ListObjectVersions`, including every current/noncurrent version and delete marker. Each row records identity/state/bytes/dates, inferred noncurrent-since from the immediately newer entry, lock, version tags, integrity evidence and eligibility. Ambiguous clocks remain untagged/ineligible. Delete markers get explicit disposition and are never recovery points.

Uncertainty fails toward retention and alerts. Daily reconciliation requires one accepted tag per data version and a verified 400-day monthly point per completed family/month. On UTC day 3, missing monthly is critical. A corrupt monthly is never unlocked/downgraded: promote/lock the next verified candidate and receipt it; if none exists, remain critical until a replacement restore passes.

### 5.2 Fenced mutation broker

All controller/operator mutations share a 15-minute optimistic-CAS Living State lease, renewed by minute 10; each acquisition increments a monotonic fence. Controllers have no S3 mutation credential. One broker owns restricted prefix list/version-list, version tag and Object Lock get/put only—no object read/delete/bypass/lifecycle/invariant-changing permission. Its policy permits retention only 399–401 days from trusted classification/promotion time. Lifecycle installation assumes a separate short-lived role limited to invariant/lifecycle get/put.

Before each write, the broker persists a `prepared` row with operation/fence/owner, exact key/version, target, plan/manifest hashes and expected pre/post-state; it rereads current lease, then writes, exact-readbacks and records `applied` before another operation. Timeout/lost response records `indeterminate` and blocks that family/version.

Indeterminate reconciliation is append-only: exact target → `applied`; exact recorded pre-state → `reconciled_not_applied` (a new fence may prepare the same target); any third state stays blocked. An expired lease with nonterminal rows cannot auto-replace. Replacement proves prior broker termination, reconciles rows, then obtains a new fence. Old holders cannot reach S3; broker serializes fences. Any lease/journal/readback failure stops before the next write and alerts.

### 5.3 Lifecycle and exact approval

Family-prefix/tag-scoped canonical rules:

- daily current expiry after 35 days; eligible noncurrent removal one day after noncurrent;
- monthly current expiry after 400 days; eligible noncurrent removal one day after noncurrent;
- approved prefix-only expired-delete-marker cleanup;
- no unknown/unclassified action.

The same version-tag filter applies to current/noncurrent rules. Object Lock remains authoritative. Eligibility is calculated from object age, derived noncurrent time and marker state/surviving data; ambiguity retains.

Plan is default/read-only. Its immutable desired state lists every version/marker's identity, pre-state, terminal tag/lock/disposition, eligibility, deletion approval and deterministic operation-DAG position. Canonical retry representation treats only exact journal-backed terminal states as completed prefix. A separate canonical imminent-deletion projection lists every eligible current/noncurrent version/marker plus explicitly retained versions and oldest survivor per family.

Max's immutable approval receipt binds both SHA-256 values, time/approver and totals. Apply requires that receipt, acquires a fence, rereads complete inventory/invariants, reproduces both artifacts exactly, extends monthly locks, tags monthly then daily exact versions, verifies every version/marker disposition, installs/readbacks canonical lifecycle JSON, confirms no synchronous deletion, receipts results, then CAS-releases.

On partial failure, the receipt records fence, artifact/desired-state hashes, completed DAG prefix, next step, every exact operation/readback, failure, lifecycle state, release/retry and operator/session. Retry proves prior termination, reconciles nonterminal rows, rereads all state and reconstructs original desired state plus completed prefix. It rejects unjournaled new/missing identities, tag/lock/invariant/lifecycle/eligibility drift, reordered/nonprefix completion, unexplained satisfied state or changed deletion disposition.

Retry regenerates the effective deletion manifest. Any canonical delta—including a prior monotonic write changing eligibility—causes no further write and requires a fresh plan, exact Max approval and receipt. Stored hashes never authorize a changed set. Lifecycle is installed only after all tag/lock readbacks and current manifest equality. Async deletion is irreversible; disabling rules cannot recover an expired version.

`backup-health/`, `RESTORE-README.md`, audit evidence and unknown prefixes are untouched.

## 6. Backup hardening and Qdrant decision

### 6.1 Postgres, Qdrant and Cloudflare

Postgres gets one retry only for classified reset/server-closed/transient network failures, with bounded jitter/backoff, fresh temp path and recorded first failure. Auth/permission/disk/encryption/validation/upload failures do not retry. Upload requires size, SHA-256 and `pg_restore --list`.

Each source has immutable baseline epoch in `stable/reset_pending/collecting/critical`. Stable uses seven verified noncritical artifacts. Cleanup/reindex reset receipt—stored before run—binds old epoch/median/count, reason/change, approved expected range, Max/Council approval, one-run default and ≤72-hour expiry. First in-range structural success starts a new collecting epoch; old samples never mix. Under seven samples, enforce approved range and, at ≥3, current median; seven establishes stable. Expiry is critical and needs new approval.

Normal anomaly gates warn below 60%/above 180% of seven-run median and are critical below 20%/above 500%. Critical/out-of-range artifacts go only to forensic `status=failed`, untagged, with no freshness/monthly advancement, and alert. Warning artifacts cannot be monthly without explicit integrity acceptance.

Qdrant reports each required collection independently with bytes/hash, cluster/version and per-collection anomaly; no small collection masks `knowledge_base_v2`. One transient snapshot/download/upload retry is allowed; auth/schema/hash/missing collection is not. Cloudflare requires DNS/zone settings for both zones, schema-complete exports and explicit required/regenerable KV classification. HTTP errors/missing sections fail; forensic uploads do not advance freshness.

### 6.2 Qdrant cadence gate

Daily 35-day snapshots remain until a measured rebuild of `knowledge_base_v2` from exact restored Postgres completes inside four-hour full-platform RTO. Evidence binds Postgres object/version and transaction/LSN, `qdrant_sync_outbox` high-water, Qdrant cluster/version and rebuild commit, and proves Postgres plus retained events/outbox authoritative.

Acceptance requires exact collection/point/ID sets; canonical logical digest over each ID/payload/vector; vector/schema/index config; zero missing/dead-letter operations through high-water; and fixed known-listing/filter/ranking/nearest-neighbor queries. Nondeterministic index bytes are rebuilt/validated separately. Effective data RPO from authoritative Postgres/outbox must be ≤24 hours.

Only then may `knowledge_base_v2` full snapshots become weekly (seven-day snapshot RPO while effective data RPO remains 24 hours). Legacy collections need owner/dependency and identical fidelity proof. Monitoring thresholds change atomically with cadence and alert if either snapshot or rebuild evidence is unavailable.

## 7. Independent monitoring and recovery objectives

### 7.1 Delivery paths

Titan watchdog runs every 15 minutes, independently of Infisical, and checks main/Infisical Postgres, each Qdrant collection, Railway config, complete Cloudflare marker, monthly points, version classification, freshness, metadata and anomaly. Alert RTO begins when canonical health first makes failure detectable. The engineering budget is ≤15 minutes to scheduled pickup, ≤1 minute for Telegram failure plus marker creation, and ≤14 minutes from marker to SES Delivery. Telegram is attempted immediately; failure writes a signed nonsecret exact-prefix S3 marker and exits nonzero.

S3 ObjectCreated routes via EventBridge to minimal Lambda. With IAM only, Lambda validates marker signature/schema/time/fingerprint, deduplicates, and sends a fixed nonsecret template from one verified SES identity to one allow-listed Max destination. It reads only that marker version, no backups/secrets. EventBridge bounded retry/DLQ remains within 30 minutes; Lambda/DLQ alarms use separate CloudWatch/SNS.

Relay receipt binds S3 event/version/fingerprint, Lambda request, SES message ID/send time and SES delivery/bounce. Only matching SES `Delivery` is success; publish acceptance is insufficient. Invalid marker, bounce/complaint/timeout/missing delivery/retry exhaustion is critical. Seven consecutive scheduled fixtures spanning times of day must inject just after a watchdog poll (worst detection latency), deliberately fail Telegram, and prove marker-to-delivery within 30 minutes. Tests cover duplicates, allow-list and DLQ alarm.

GitHub runs every 15 minutes as tertiary dead-man: 30-hour freshness, S3-canonical status, marker polling, one deduplicated issue/fingerprint, update while unhealthy and close after two greens. GitHub cron timing receives no credit toward 30-minute RTO. Its delay/drop cannot weaken EventBridge/SES.

Backend beat entry `backup-watchdog-hourly` invokes task `poll_backup_watchdog`; enable only after credentials/endpoint proof. It fails/retries/escalates on unavailable endpoint and treats missing `INTERNAL_API_KEY` as critical. This tertiary path does not establish 30-minute RTO.

### 7.2 Objectives and drills

- RPO 24h / stale alert by 30h: main/Infisical Postgres, effective Qdrant data, Railway config, complete Cloudflare, required independent source mirrors.
- Qdrant weekly mode: snapshot RPO 7d only after section 6.2; effective data RPO stays 24h.
- Main restore RTO 2h; full platform 4h; alert delivery 30m.
- Every additional inventory row, including AIM Data Postgres unless excluded, gets owner-approved RPO/RTO no weaker than its dependent service.

Drills: monthly automated integrity; quarterly isolated main/Qdrant restores and live-inventory reconciliation; quarterly Max-assisted zero-disclosure Infisical restore; semiannual full replacement covering secrets, topology, source, all inventory databases, Qdrant, Cloudflare and signed application validation.

## 8. Implementation, tests and production acceptance

### 8.1 Scope

Backend: `scripts/backup_pg.py`, `scripts/backup_qdrant_s3.py`, backup monitor/Celery tasks, `backup-verify.yml`, tests.

Runbooks: watchdog, Cloudflare/Railway/Qdrant wrappers, plan/apply retention tool and lifecycle JSON, Infisical verifier, Telegram installer/sender, inventory generator and exclusion receipts, git-mirror producer/verifier, EventBridge/Lambda/SES/DLQ infrastructure, `backup-and-recovery.md`, `disaster-recovery.md`, `aws-s3.md`, `local-secops.md`, redacted receipts.

Titan deployment uses reviewed Git content under `/Users/max/local-secops/` with owner-only permissions. No secret enters a worktree.

### 8.2 Required tests/reviews

1. Version-complete classification across pages/months/current/noncurrent/markers/ambiguous clocks/corrupt first backup/unknown prefix/idempotence and monthly promotion.
2. Fence/broker tests: no controller S3 access; stale holder rejection; prepared-before-write; ownership/readback; renewal; prior-worker termination; both indeterminate terminal states; immutable desired/DAG reconstruction; every named drift rejection; effective-manifest regeneration; fresh approval on any delta.
3. Lifecycle snapshots/readback, Object Lock refusal, no-delete/invariant proof and exact version/marker dispositions.
4. Postgres retry/temp cleanup; every baseline receipt/state/sample/expiry/quarantine path.
5. Per-collection masking and full Qdrant boundary/digest/schema/dead-letter/query/RPO/RTO proof; Cloudflare 403/missing-section regression.
6. Keychain installer/canaries/consumer migration/one-shot cleanup; Telegram argv/env/FD/proxy/debug/exception/output/audit leak probes across HTTP/API/timeout/signal/crash.
7. Scheduled Titan detection at worst cadence phase; Telegram message ID; seven EventBridge-to-SES-delivery fixtures ≤30m; invalid signature/duplicates/bounce/missing delivery/retry/DLQ/recipient/IAM tests; GitHub threshold/dedupe/two-green without RTO credit.
8. Infisical synthetic PG18/age proof: no plaintext, per-child argv/env/FD allow-lists, output suppression/normalized errors, partial writes, RLIMIT/mlock refusal, interruption/timeout/process-group cleanup, tmpfs/network/log refusal, leak probes, attestation allow-list and constant-time RFC 8785 self-hash.
9. Live inventory fixtures covering every named platform/dependency; unlisted AIM Data Postgres, empty mirror, expired exclusion, missing monitor or stale restore blocks.
10. Exact-commit Council review with builder excluded; one-subsystem production cutover with readback/rollback checkpoints.

### 8.3 Gate 4 evidence

All must pass:

- fresh successful restores: main Postgres, Qdrant and Max-assisted Infisical; critical-schema and every zero-disclosure negative control green;
- candidate/Keychain Telegram canaries with message IDs; complete consumer migration/pointer cutover; no stale `.env` plaintext;
- scheduled worst-phase Telegram fixture ≤30m and seven scheduled failed-Telegram fixtures with matching SES Delivery ≤30m; GitHub dedupe/recovery and backend scheduled task observed;
- canonical live-reconciled recovery inventory: each row has backup/restore/monitor/RPO/RTO or exact unexpired exclusion; AIM Data Postgres and every required source repo explicitly pass;
- Railway/Cloudflare recovery points meet RPO; Cloudflare has both zones/settings and no error records;
- every S3 version/marker classified/dispositioned; no ambiguous eligibility; no prepared/indeterminate journal row; applied rows exact-readback; lifecycle canonical readback and all bucket invariants unchanged;
- post-policy total bytes and projected 35/400-day steady state; exact imminent-deletion manifest/Max approval bound to apply receipt;
- merged runbooks and S3 `RESTORE-README.md` bind Git commit/blob/local hash to object version/download hash with byte equality;
- Qdrant logical fidelity, 24h effective RPO and 4h RTO before cadence change;
- replacement drill proves every inventory RPO/RTO with zero unresolved exceptions.

An exception needs Max's exact bounded waiver naming owner/risk/compensating control/expiry; expiry blocks Gate 4. A waiver cannot remove an inventory row: that requires section-1 exact exclusion.

## 9. Approved source-data retention, separately migrated

Max approved on 24 July:

- `qdrant_sync_outbox status=done`: 30 days;
- `qdrant_sync_outbox status=dead_letter`: 180 days;
- `state_events`: 12 months;
- weekly Qdrant full snapshots only after section-6.2 fidelity, 24h effective RPO and 4h RTO proof.

This Gate 1 design deletes no production rows and changes no Qdrant cadence. A separate exact-reviewed migration uses bounded batches, dependency/FK checks, dry-run counts, required archive for authoritative events, immutable receipts, post-validation and rollback/rebuild proof. Unknown outbox states remain retained. Until that migration and rebuild drill pass, storage reduction comes only from reviewed S3 lifecycle and the completed DB cleanup.
