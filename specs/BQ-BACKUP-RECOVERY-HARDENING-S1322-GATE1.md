# BQ-BACKUP-RECOVERY-HARDENING-S1322 — Gate 1 Design

Status: R14_AUTHORED_PENDING_REVIEW
Owner: Vulcan S1322
Directive: Max, 2026-07-24
Class: security-sensitive production resilience and retention

Review lineage: R1–R8 established the zero-disclosure restore, Keychain cutover, 35/400-day retention, Object Lock, mutation lease, anomaly reset and Qdrant controls. R8 GLM/CC approved; direct MP returned one blocker and six majors. R9 folded fenced journaling, version-complete lifecycle approval, measured alerts, baseline epochs, Qdrant fidelity, negative secret tests and fail-closed acceptance. R9 MP returned one blocker/two majors; GLM/CC approved with findings. R10 folded deterministic retry approval, subprocess secrecy, complete recovery inventory, named journal states and event-driven alert fallback. At exact head `69cde46b329b302fc6768f3a273ddf8f83ba81e3`, CC approved with two clarity findings; GLM's approval was nonaccepting because its input truncated sections 7–13. R11 compacted the complete artifact below the reviewer limit; GLM approved, while CC's approval envelope was malformed. R12 folded CC's fixture-anchor finding; GLM/CC approved, but MP handler failed and direct exact-head MP returned one blocker/one major. R13 moved restore into a host-pinned no-swap VM and separated classification from deletion eligibility. Direct MP reviewed exact R13 head `a539133dc548d05b0fad209476f0ef0f0604814e` and returned ten findings. R14 folds all ten: complete host/guest secret residency, exact DELETE-row authorization, signed producer manifests and semantic restore proof, inventory-derived bounded retention families, an immutable deletion ledger, an external dead-man, continuously valid Qdrant cadence evidence, an explicit irreversible lifecycle boundary, and complete QEMU teardown.

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

Each row states owner, production classification, source/service, authoritative data class, exact source and destination/prefix, essentiality, retention class/disposition, current/noncurrent/marker bytes, measured growth, bounded steady-state byte/object envelope, backup schedule, monitor, RPO/RTO, restore procedure, last successful backup and restore proof, and `covered` or exact exclusion. Retention families are generated only from this inventory, never a hand-maintained prefix list. This explicitly includes main and Infisical Postgres, every Qdrant collection, Railway and Cloudflare exports, every required Git mirror, AIM Data, Titan/vectorAIz sources and every later-discovered source. A bounded forensic family declares admission, maximum bytes/objects/age and terminal disposition; it cannot be a permanent catch-all. Unknown families/versions remain Object-Locked, untagged, protected and immediately alerting. Live discovery is reconciled quarterly and before Gate 4; no silent addition/removal is allowed, and Gate 4 blocks any covered source without a finite measured envelope.

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

Max keeps the age identity in 1Password; neither it nor an `op://` reference is sent to Codex. The preferred proof profile retrieves the identity wholly inside the pinned guest through an approved guest-local mechanism whose executable/configuration hashes are reviewed and attested, so private material never enters host userspace. If that mechanism is unavailable, the only permitted fallback is an attested Titan proof profile: host swap is disabled (not merely avoided), sleep/hibernation and hibernation-image persistence are disabled, host kernel core/crash dumps are disabled, and every secret-bearing host process and IPC buffer is locked before use and continuously residency-verified until zeroization. Any other profile refuses the run. The deterministic verifier:

1. enumerates `postgres/infisical/*.dump.age` newest-to-oldest, selects the newest complete valid producer-signed version, and records nonsecret S3 provenance/metadata;
2. downloads ciphertext only into a mode-0700 temporary directory;
3. obtains exactly one raw `AGE-SECRET-KEY-...` line inside the guest, or under the attested fallback obtains it from `op read` into locked host memory and transfers it once over an anonymous locked FD;
4. passes it only to `age` over an anonymous FD; decrypted bytes flow through anonymous pipes to hashing and `pg_restore`;
5. restores inside a dedicated ephemeral QEMU VM running Postgres 18, with guest swap absent, runtime/data on guest tmpfs, an immutable read-only OS image, no writable block device and `network=none`;
6. verifies the producer-signed manifest and compares its plaintext/ciphertext SHA-256, bytes, TOC and transaction identity before checking the reviewed critical-schema and semantic-assertion manifests;
7. emits only a mode-0600 redacted attestation;
8. in `finally`, terminates the complete QEMU process group, waits and reaps every child, closes every inherited/monitor/serial/secret FD and chardev, unmounts and verifies teardown of every guest tmpfs/shared mount, removes downloaded ciphertext and ephemeral directories, and attests no residual process, FD, mount, socket, chardev, firmware/NVRAM state, tmpfs allocation or file remains.

The Titan parent runs with `RLIMIT_CORE=0`, locks its identity and pipe buffers, and launches QEMU with `-overcommit mem-lock=on` (not lazy/on-fault) after proving the hard memlock limit exceeds the entire fixed VM allocation plus QEMU overhead. The VM may start only when QEMU confirms all guest/host-emulator memory is pinned; any unlocked page refuses the run. QEMU uses `dump-guest-core=off`, immutable firmware, no writable pflash/NVRAM/firmware-variable store, no path-backed writable chardev/monitor/serial socket, and no writable QEMU/debug/log path; all required channels are anonymous locked FDs with fixed allow-lists. Guest boot verifies `SwapTotal=0`, no swap device/file, no writable block device, no crash dump/kdump, tmpfs for every runtime/data/log path, and network disabled. In fallback mode, the attested host profile proves the disabled host swap/hibernation-image/kernel-dump controls before secret retrieval; a sleep/power-transition or residency-verification failure aborts and invalidates the attestation.

Thus every plaintext-bearing `age`, hashing, `pg_restore`, Postgres and restored-row page stays inside guest RAM that is pinned against host swap; only ciphertext and the immutable secret-free VM image touch persistent storage. The minimal host identity buffer must `mlock`; its complete pipe write into the pinned VM channel closes before zeroize/unlock. Exact environment and FD allow-lists prevent inheritance by AWS, QEMU management, cleanup or Ollama. No database password appears in argv/environment.

Each process group has a deadline. Timeout, signal, partial write, broken pipe, downstream close or interrupted `op read` closes FDs, terminates/reaps children and zeroes buffers. Any unavailable tool/profile/key/QEMU capability, invalid identity shape, metadata/hash/TOC/schema mismatch, host or guest memlock/swap/sleep preflight failure, tmpfs/read-only-disk/network failure, memory/FD control failure, restore failure or incomplete cleanup refuses PASS.

Raw stdout/stderr, verbose/debug tracing, shell traces, core/container logs and environment/command dumps are forbidden. Required catalog output is bounded and parsed in memory, rejected for forbidden content, reduced to allow-listed counts/digests and zeroed. Child errors become fixed nonsecret failure class plus numeric status. Before exit, leak probes scan child argv/environment/FDs, temporary paths, mounts/log settings and the audit payload; inability to prove no secret/restored-data persistence is failure.

Every backup is accompanied by a canonical producer-signed manifest issued through an isolated signing authority. Its signing key is unavailable to the backup writer/uploader and is anchored by a separately controlled, pinned verification key plus an immutable append-only audit record. It binds manifest schema/version and unique nonce/sequence; source/service; bucket/key/version ID; ciphertext and plaintext digests/bytes; production time; Postgres LSN/transaction or Qdrant snapshot identity; TOC/snapshot and schema-manifest versions; and producer result. Verification rejects unsigned, unknown-key, revoked-key, replayed/duplicate-sequence, stale, mismatched or result-failed objects. Restore selection walks newest to oldest and chooses the newest complete valid signed recovery point, never merely the newest object. Object Lock/versioning preserves the exact signed version but does not substitute for this producer authenticity.

The signed manifest also binds a versioned non-disclosing semantic assertion set. In the isolated guest it verifies allow-listed row-count bounds and keyed canonical digests, enabled/validated constraints, exact migration head, presence/counts of critical record classes, and isolated read-only functional checks. Assertion keys are separately controlled; only assertion IDs, expected/observed equality or bounded counts and PASS/FAIL leave the guest—never rows, values, secret names or raw query output. Any assertion/version/manifest mismatch fails the restore point.

### 3.2 Attestation and local AI

The allow-listed attestation records schema/time/host/profile, bucket/key/version/last-modified/ciphertext bytes, signed-manifest/key/audit/nonce identity, expected/observed plaintext hash/bytes/TOC, semantic-assertion-set identity/results, client/server versions, restore/catalog counts, QEMU version/argv hash/fixed memory, full-VM and every secret-bearing host process/IPC memlock/residency proof, host swap/hibernation-image/kernel-dump state, guest `SwapTotal=0`, guest-core-dump-off, absent writable block/firmware/NVRAM/chardev/log/crash-dump paths, tmpfs/network/sleep controls, RLIMIT/zeroization/FD/interruption/process-group-reaping/mount/ciphertext/residual-resource cleanup outcomes, overall PASS, and RFC 8785 self-hash. Hashing canonicalizes with existing `attestation_sha256=null`; independent verification repeats this and constant-time compares.

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

Future uploads use collision-resistant unique keys and refuse overwrite. The writer cannot tag or change retention. New objects remain untagged and match no expiration rule until one daily controller assigns a version-specific inventory-derived classification tag (`retention_class=daily|monthly|forensic`) to an exact declared family. No covered family—including Git mirrors, AIM Data, Titan/vectorAIz exports or a later source—can exist outside the authoritative inventory and envelope. Forensic admission requires its bounded class/disposition and never advances a recovery point.

The bucket's default 35-day COMPLIANCE retention remains mandatory for every new data object. Classification never shortens it; selected monthly versions are extended from classification/promotion time to 400 days before tagging.

The first integrity-verified UTC object per family/month becomes `retention_class=monthly` only after its exact version receives a 400-day COMPLIANCE extension; other data versions become `retention_class=daily`. Integrity requires exact producer `status=ok`, matching bytes, required SHA/TOC/snapshot metadata, noncritical anomaly state and, for topology/Cloudflare, schema completeness. Listing/nonzero upload alone is insufficient.

Existing classification uses fully paginated `ListObjectVersions`, including every current/noncurrent version and delete marker. Each row records identity/state/bytes/dates, inferred noncurrent-since from the immediately newer entry, lock, version tags, integrity evidence and eligibility. Ambiguous clocks remain untagged/ineligible. Delete markers get explicit disposition and are never recovery points.

Classification alone never makes a version lifecycle-eligible. Lifecycle rules require both its `retention_class` and a version-specific `deletion_approved=true` tag that only the exact-approved apply path may set. Uncertainty fails toward retention and alerts. Daily reconciliation requires one class tag per data version and a verified 400-day monthly point per completed family/month, but it cannot write `deletion_approved`. On UTC day 3, missing monthly is critical. A corrupt monthly is never unlocked/downgraded: promote/lock the next verified candidate and receipt it; if none exists, remain critical until a replacement restore passes.

### 5.2 Fenced mutation broker

All controller/operator mutations share a 15-minute optimistic-CAS Living State lease, renewed by minute 10; each acquisition increments a monotonic fence. Controllers have no S3 mutation credential. One broker owns restricted prefix list/version-list, version tag and Object Lock get/put only—no object read/delete/bypass/lifecycle/invariant-changing permission. Its policy permits retention only 399–401 days from trusted classification/promotion time. Lifecycle installation assumes a separate short-lived role limited to invariant/lifecycle get/put.

Before each write, the broker persists a `prepared` row with operation/fence/owner, exact key/version, target, plan/manifest hashes and expected pre/post-state; it rereads current lease, then writes, exact-readbacks and records `applied` before another operation. Timeout/lost response records `indeterminate` and blocks that family/version.

Indeterminate reconciliation is append-only: exact target → `applied`; exact recorded pre-state → `reconciled_not_applied` (a new fence may prepare the same target); any third state stays blocked. An expired lease with nonterminal rows cannot auto-replace. Replacement proves prior broker termination, reconciles rows, then obtains a new fence. Old holders cannot reach S3; broker serializes fences. Any lease/journal/readback failure stops before the next write and alerts.

### 5.3 Lifecycle and exact approval

Family-prefix/tag-scoped canonical rules require an AND match on prefix, `retention_class` and `deletion_approved=true`:

- daily current expiry after 35 days; eligible noncurrent removal one day after noncurrent;
- monthly current expiry after 400 days; eligible noncurrent removal one day after noncurrent;
- no automatic delete-marker cleanup; markers remain explicitly inventoried/retained because an untagged marker rule could bypass exact approval;
- no unknown, unclassified or deletion-unapproved action.

The same two version-tag filters apply to current/noncurrent rules. Object Lock remains authoritative. Eligibility is calculated from object age and derived noncurrent time; ambiguity retains. Any later marker cleanup requires a separate exact-reviewed, exact-version deletion design and is outside this lifecycle.

Plan is default/read-only. Its immutable desired state lists every version/marker's identity, pre-state, terminal tag/lock/disposition, eligibility, deletion approval and deterministic operation-DAG position. Canonical retry representation treats only exact journal-backed terminal states as completed prefix. A separate canonical imminent-deletion projection lists every eligible current/noncurrent version/marker plus explicitly retained versions and oldest survivor per family.

Max's immutable approval receipt binds both SHA-256 values, time/approver and totals. The effective manifest has one canonical typed row per version/marker and separates exact `DELETE` rows from `RETAINED`, oldest-`SURVIVOR`, `MARKER` and non-operative `CONTEXT` rows. Apply requires that receipt, acquires a fence, rereads complete inventory/invariants, reproduces both artifacts exactly, extends monthly locks, reconciles class tags, then sets `deletion_approved=true` only when the active receipt's canonical row exactly matches receipt ID, key, version ID, retention class, eligibility clock and operation=`DELETE`. A retained, survivor, marker, context, absent, duplicated or field-mismatched row is never taggable. It verifies every disposition before staging lifecycle.

On partial failure, the receipt records fence, artifact/desired-state hashes, completed DAG prefix, next step, every exact operation/readback, failure, lifecycle state, release/retry and operator/session. Retry proves prior termination, reconciles nonterminal rows, rereads all state and reconstructs original desired state plus completed prefix. It rejects unjournaled new/missing identities, tag/lock/invariant/lifecycle/eligibility drift, reordered/nonprefix completion, unexplained satisfied state or changed deletion disposition.

Retry regenerates the effective deletion manifest. Any canonical delta—including a late/concurrent arrival or prior monotonic write changing eligibility—causes no further write and requires a fresh plan, exact Max approval and receipt. Stored hashes never authorize a changed set.

Lifecycle enablement is the irreversible boundary. Before it, apply freezes or drains queued classifier/broker work at a recorded DAG boundary, stages the exact lifecycle rules as `Disabled`, reads back byte-equivalent canonical JSON, and proves expiry/noncurrent handling, marker survival and Object Lock behavior in a disposable versioned Object-Locked bucket. Drift, queued arrival, failed readback/proof or an indeterminate journal row stops and returns to read-only planning. Pre-enable rollback removes/restores only the disabled staged rules and reverses non-monotonic planning state; retention extensions remain safe monotonic writes. After a final fresh exact-artifact Council approval and Max approval immediately before the enable call, the broker rechecks receipt/inventory/queue equality and enables/readbacks the same rules. After enable, rollback cannot promise recovery of an asynchronously deleted version: stop by disabling the rules, preserve and inventory retained survivors, and restore/reupload a verified survivor as a new Object-Locked version under a fresh plan. No queued work resumes until post-boundary reconciliation. The approved 35/400-day periods do not change.

After installation, the daily controller may continue classifying but cannot create deletion eligibility. Each later batch approaching 35/400-day eligibility gets a fresh version-complete inventory, canonical effective-deletion projection and exact Max approval under the same fence/journal protocol before the broker applies `deletion_approved=true`. A new/changed/missing version between plan and apply changes the projection and aborts. The broker enforces the complete canonical DELETE-row match above, not receipt membership alone.

An immutable append-only lifecycle ledger records each exact version's approval receipt/row hash, tag readback, lifecycle expiration observation, permanent-deletion observation and reconciliation status. Every S3 expiration/permanent-deletion event must match the exact approved `DELETE` row before it is accepted; an out-of-manifest, wrong-version/class/clock/receipt, retained/survivor/marker/context deletion alerts immediately and freezes mutations. Reconciliation alerts on overdue approved deletion, unbounded marker growth, and each family's current/noncurrent/marker bytes or growth outside its steady-state envelope. Async deletion is irreversible; disabling rules cannot recover an expired version.

`backup-health/`, `RESTORE-README.md`, audit evidence and unknown prefixes are untouched.

## 6. Backup hardening and Qdrant decision

### 6.1 Postgres, Qdrant and Cloudflare

Postgres gets one retry only for classified reset/server-closed/transient network failures, with bounded jitter/backoff, fresh temp path and recorded first failure. Auth/permission/disk/encryption/validation/upload/signing failures do not retry. Publication requires the producer-signed manifest contract in section 3.1, immutable audit anchoring, size/SHA-256, `pg_restore --list`, semantic-assertion identity and successful result. Qdrant and configuration producers use the same source-appropriate signed fields. No unsigned or mismatched artifact advances freshness, monthly selection or restore eligibility.

Each source has immutable baseline epoch in `stable/reset_pending/collecting/critical`. Stable uses seven verified noncritical artifacts. Cleanup/reindex reset receipt—stored before run—binds old epoch/median/count, reason/change, approved expected range, Max/Council approval, one-run default and ≤72-hour expiry. First in-range structural success starts a new collecting epoch; old samples never mix. Under seven samples, enforce approved range and, at ≥3, current median; seven establishes stable. Expiry is critical and needs new approval.

Normal anomaly gates warn below 60%/above 180% of seven-run median and are critical below 20%/above 500%. Critical/out-of-range artifacts go only to forensic `status=failed`, untagged, with no freshness/monthly advancement, and alert. Warning artifacts cannot be monthly without explicit integrity acceptance.

Qdrant reports each required collection independently with bytes/hash, cluster/version and per-collection anomaly; no small collection masks `knowledge_base_v2`. One transient snapshot/download/upload retry is allowed; auth/schema/hash/missing collection is not. Cloudflare requires DNS/zone settings for both zones, schema-complete exports and explicit required/regenerable KV classification. HTTP errors/missing sections fail; forensic uploads do not advance freshness.

### 6.2 Qdrant cadence gate

Daily 35-day snapshots remain until a measured rebuild of `knowledge_base_v2` from exact restored Postgres completes inside four-hour full-platform RTO. Evidence binds Postgres object/version and transaction/LSN, `qdrant_sync_outbox` high-water, Qdrant cluster/version and rebuild commit, and proves Postgres plus retained events/outbox authoritative.

Acceptance requires exact collection/point/ID sets; canonical logical digest over each ID/payload/vector; vector/schema/index config; zero missing/dead-letter operations through high-water; and fixed known-listing/filter/ranking/nearest-neighbor queries. Nondeterministic index bytes are rebuilt/validated separately. Effective data RPO from authoritative Postgres/outbox must be ≤24 hours.

Only then may `knowledge_base_v2` full snapshots become weekly (seven-day snapshot RPO while effective data RPO remains 24 hours). Weekly mode continuously fail-closes when its last exact-environment proof is older than 90 days and invalidates immediately on any schema/migration, vector/index configuration, embedding model/version/digest, Qdrant version, outbox state/ordering/retry/dead-letter semantics, or rebuild-code/dependency change. A proposed invalidating change is gated until a fresh exact-environment rebuild proof passes; otherwise cadence atomically returns to daily first and a signed, restore-validated daily recovery point is proven before the invalidation lands. An unplanned invalidation immediately alerts and blocks dependent deployment/weekly success claims until daily proof exists. Every cadence proof measures combined exact Postgres restore plus Qdrant rebuild and validation within the full-platform four-hour RTO, not rebuild alone. Legacy collections need owner/dependency and identical continuously fresh fidelity proof. Monitoring thresholds change atomically with cadence and alert if either snapshot or rebuild evidence is unavailable.

## 7. Independent monitoring and recovery objectives

### 7.1 Delivery paths

Titan watchdog runs every 15 minutes, independently of Infisical, and checks main/Infisical Postgres, each Qdrant collection, Railway config, complete Cloudflare marker, monthly points, version classification, freshness, metadata and anomaly. Alert RTO begins when canonical health first makes failure detectable. The engineering budget is ≤15 minutes to scheduled pickup, ≤1 minute for Telegram failure plus marker creation, and ≤14 minutes from marker to SES Delivery. Telegram is attempted immediately; failure writes a signed nonsecret exact-prefix S3 marker and exits nonzero.

A separately administered external dead-man schedules a challenge at least every 15 minutes outside Titan, AWS/S3/EventBridge and their marker-write failure domain. It requires a signed, nonce-bound health acknowledgement and independently delivers a fixed nonsecret alert with delivery receipt within 30 minutes of a missed/failed challenge. Its scheduler, state and primary/secondary notification providers do not depend on Titan, S3, Telegram, SES, Infisical or the main database; loss of the primary notification provider fails over within the same 30-minute budget, and only recipient-delivery evidence counts. It monitors the Titan watchdog itself plus the S3 relay rather than trusting their self-reports.

S3 ObjectCreated routes via EventBridge to minimal Lambda. With IAM only, Lambda validates marker signature/schema/time/fingerprint, deduplicates, and sends a fixed nonsecret template from one verified SES identity to one allow-listed Max destination. It reads only that marker version, no backups/secrets. EventBridge retry age and Lambda/SES timeouts may not extend the marker-to-SES-Delivery success path beyond 14 minutes; exhaustion routes immediately to DLQ. Lambda/DLQ alarms use separate CloudWatch/SNS and are tested end to end within the same 30-minute detection-to-notification RTO, but do not convert a missing SES Delivery into success for the primary fallback fixture.

Relay receipt binds S3 event/version/fingerprint, Lambda request, SES message ID/send time and SES delivery/bounce. Only matching SES `Delivery` is success; publish acceptance is insufficient. Invalid marker, bounce/complaint/timeout/missing delivery/retry exhaustion is critical. Seven consecutive scheduled fixtures spanning times of day must inject just after a watchdog poll (worst detection latency), deliberately fail Telegram, and prove both injection-to-SES-Delivery ≤30 minutes and marker-to-SES-Delivery ≤14 minutes. Tests cover duplicates, allow-list and DLQ alarm.

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

Runbooks: watchdog, external dead-man, Cloudflare/Railway/Qdrant wrappers, signed-manifest producer/verifier and immutable audit, plan/apply retention tool, lifecycle JSON/ledger, Infisical verifier, Telegram installer/sender, inventory generator and exclusion receipts, git-mirror producer/verifier, EventBridge/Lambda/SES/DLQ infrastructure, `backup-and-recovery.md`, `disaster-recovery.md`, `aws-s3.md`, `local-secops.md`, redacted receipts.

Titan deployment uses reviewed Git content under `/Users/max/local-secops/` with owner-only permissions. No secret enters a worktree.

### 8.2 Required tests/reviews

1. Version-complete classification across pages/months/current/noncurrent/markers/ambiguous clocks/corrupt first backup/unknown prefix/idempotence and monthly promotion.
2. Fence/broker tests: no controller S3 access; stale holder rejection; prepared-before-write; ownership/readback; renewal; prior-worker termination; both indeterminate terminal states; immutable desired/DAG reconstruction; every named drift rejection; effective-manifest regeneration; class tags never create eligibility; fresh approval and exact canonical DELETE-row match for every initial/later eligibility tag; late/concurrent/overdue arrival aborts.
3. Lifecycle tests reject retained/survivor/marker/context and every receipt/key/version/class/clock/operation mismatch; verify immutable exact-version expiration/permanent-deletion ledger, immediate out-of-manifest alert, overdue deletion, marker growth and current/noncurrent/marker byte-envelope reconciliation. Stage/read back disabled rules, prove them in a disposable versioned Object-Locked bucket, test queue freeze/drain and every pre-enable stop/rollback, then require final exact approval at enable and prove post-boundary survivor recovery.
4. Postgres retry/temp cleanup; every baseline receipt/state/sample/expiry/quarantine path; every producer's signed-manifest success plus unsigned/unknown/revoked/replayed/stale/result/object/digest/bytes/time/LSN/transaction/TOC/snapshot/schema-version mismatch negatives and newest-valid-point selection.
5. Per-collection masking and full Qdrant boundary/digest/schema/dead-letter/query/RPO/RTO proof; proof-freshness expiry and every schema/vector/embedding/Qdrant/outbox/rebuild invalidation trigger; gated fresh proof or atomic daily fallback with a signed validated daily recovery point; combined Postgres restore plus rebuild within four hours; Cloudflare 403/missing-section regression.
6. Keychain installer/canaries/consumer migration/one-shot cleanup; Telegram argv/env/FD/proxy/debug/exception/output/audit leak probes across HTTP/API/timeout/signal/crash.
7. Scheduled Titan detection at worst cadence phase; Telegram message ID; seven EventBridge-to-SES fixtures each proving injection-to-delivery ≤30m and marker-to-delivery ≤14m; external dead-man tests kill the watchdog, take Titan offline, deny S3, fail marker writes and fail the primary external notification provider, each end to end to independently delivered receipt within 30m; invalid signature/duplicates/bounce/missing delivery/retry/DLQ/recipient/IAM tests; GitHub threshold/dedupe/two-green without RTO credit.
8. Infisical synthetic PG18/age proof: preferred guest-local retrieval and attested fallback; producer-signature/unknown-key/revocation/replay/object-field/semantic-manifest negatives; no plaintext; full-allocation and all host secret process/IPC memlock/residency; host swap/hibernation-image/kernel-dump and QEMU guest-core/writable firmware/NVRAM/chardev/log negatives; guest swap/writable-disk/crash-dump absence; forced partial/unlocked-page/sleep failures; per-child argv/env/FD allow-lists; output suppression/normalized errors; RLIMIT/mlock refusal; interruption/timeout; explicit QEMU group termination/reaping, FD/chardev closure, tmpfs/mount teardown, ciphertext removal and residual-resource attestation; leak probes and constant-time RFC 8785 self-hash.
9. Live inventory fixtures covering every named platform/dependency; inventory-derived families for Git mirrors, AIM Data and later sources; bounded forensic admission/disposition; unknown-family protection/alert; unlisted source, empty mirror, expired exclusion, missing finite envelope/monitor or stale restore blocks.
10. Exact-commit Council review with builder excluded; one-subsystem production cutover with readback/rollback checkpoints.

### 8.3 Gate 4 evidence

All must pass:

- fresh successful restores: main Postgres, Qdrant and Max-assisted Infisical; critical-schema and every zero-disclosure negative control green;
- candidate/Keychain Telegram canaries with message IDs; complete consumer migration/pointer cutover; no stale `.env` plaintext;
- scheduled worst-phase Telegram fixture injection-to-message ≤30m and seven scheduled failed-Telegram fixtures each with injection-to-SES-Delivery ≤30m and marker-to-SES-Delivery ≤14m; external dead-man delivery receipts prove watchdog-kill, Titan-offline, S3-denied, marker-write-failure and primary-provider-failure alerts within 30 minutes; GitHub dedupe/recovery and backend scheduled task observed;
- canonical live-reconciled recovery inventory: each row has backup/restore/monitor/RPO/RTO or exact unexpired exclusion; AIM Data Postgres and every required source repo explicitly pass;
- Railway/Cloudflare recovery points meet RPO; Cloudflare has both zones/settings and no error records;
- every `deletion_approved=true` tag exactly matches an active canonical DELETE row on receipt ID/key/version/class/clock/operation; all retained/survivor/marker/context negatives pass; no ambiguous eligibility, prepared or indeterminate journal row; applied rows exact-readback; disabled staging/disposable Object-Lock proof/final pre-enable approvals and enable readback are immutable; the version-specific lifecycle ledger accounts for every expiration/permanent deletion with zero out-of-manifest or overdue event;
- every inventory-derived family, including Git mirrors, AIM Data, bounded forensic and later sources, has measured current/noncurrent/marker bytes, growth and finite 35/400-day steady-state envelope; unknowns remain protected/alerting and no covered source is unbounded;
- merged runbooks and S3 `RESTORE-README.md` bind Git commit/blob/local hash to object version/download hash with byte equality;
- newest valid producer-signed recovery points have immutable key/audit provenance and version-bound non-disclosing semantic restore PASS; unsigned, unknown, replayed and mismatched objects are rejected;
- Qdrant logical fidelity, continuously fresh invalidation proof, 24h effective RPO and combined Postgres-restore-plus-rebuild within the four-hour full-platform RTO before and throughout weekly mode;
- replacement drill proves every inventory RPO/RTO with zero unresolved exceptions.

An exception needs Max's exact bounded waiver naming owner/risk/compensating control/expiry; expiry blocks Gate 4. A waiver cannot remove an inventory row: that requires section-1 exact exclusion.

## 9. Approved source-data retention, separately migrated

Max approved on 24 July:

- `qdrant_sync_outbox status=done`: 30 days;
- `qdrant_sync_outbox status=dead_letter`: 180 days;
- `state_events`: 12 months;
- weekly Qdrant full snapshots only after section-6.2 fidelity, 24h effective RPO and 4h RTO proof.

This Gate 1 design deletes no production rows and changes no Qdrant cadence. A separate exact-reviewed migration uses bounded batches, dependency/FK checks, dry-run counts, required archive for authoritative events, immutable receipts, post-validation and rollback/rebuild proof. Unknown outbox states remain retained. Until that migration and rebuild drill pass, storage reduction comes only from reviewed S3 lifecycle and the completed DB cleanup.
