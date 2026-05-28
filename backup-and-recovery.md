# Backup & Recovery — ai.market

> Destination/identity specifics live in [aws-s3.md](./aws-s3.md). Architecture rationale: `BQ-AI-MARKET-COMPLETE-BACKUP-ARCHITECTURE-TITAN1-CENTRIC-S681`. This runbook is the source of truth for **what is backed up, on what cadence, and how to restore the market**.

## §A. Header
- **system_name:** backup-and-recovery
- **purpose_sentence:** Define what must be backed up to reconstruct ai.market, how each piece is captured to the immutable S3 bucket, and the exact procedure to restore after data loss or credential compromise.
- **owner_agent:** Vulcan-Primary
- **escalation_contact:** Max
- **lifecycle_ref:** §J
- **authoritative_scope:** Source of truth for backup coverage, cadence, integrity verification, and per-component restore procedures. Bucket lockdown + writer identity inherit from `aws-s3.md`. Secret locations from `infisical-secrets.md`.
- **linter_version:** not yet run (prose form, consistent with sibling runbooks pending the harness pass)

## §B. Coverage Matrix — what restoring the whole market requires
> Honest status as of S723. **A backup is only DR-complete when its row is LIVE.** Today only row 1 is LIVE.

| # | Component | Why it matters for restore | Backup method | Status | Restore ref |
|---|---|---|---|---|---|
| 1 | **ai.market Postgres** (marketplace + Living State + author_dispatch) | The platform's core data + dev/build state | `pg_dump -Fc` → S3 `postgres/ai-market/<date>/` (+ Railway native backups) | **LIVE** — first dump uploaded + verified S723 | §E-R2 |
| 2 | **Infisical Postgres** (secrets, root of trust) | Without secrets nothing can authenticate/deploy | in-Railway scheduled dump → S3 `postgres/infisical/<date>/` (DB has no public endpoint; dump runs inside its Railway project) | PENDING (build approved S723) | §E-R3 |
| 3 | **Source code** (all `aidotmarket/*` repos) | The application itself; specs; HANDOFF history | nightly `git clone --mirror` / `fetch --all` → S3 `git-mirrors/<repo>.git` | PENDING | §E-R4 |
| 4 | **Railway deployment config** (services, env vars, build/start, volumes, domains, cron) | How the code is wired into running infrastructure | nightly Railway API export (project/service/variables) → S3 `railway-config/<date>/` | PENDING | §E-R5 |
| 5 | **Cloudflare** (Workers KV data, Worker code, DNS/zone config) | Edge routing, redirects, KV-held state | Worker code in repos (row 3); nightly KV bulk export + zone/DNS export → S3 `cloudflare/<date>/` | PENDING | §E-R6 |
| 6 | **User/object data** | Marketplace is **non-custodial** — seller data stays in the seller's own S3 via STS, so it is NOT ours to back up. Any app-side uploaded files → confirm + cover. Qdrant vectors = re-ingestable, excluded. | per-source (confirm app object storage exists) | PENDING (scope confirm) | §E-R7 |
| 7 | **Encryption key custody** (client-side AES-256-GCM key, offline) | Decrypt backups if Titan + all online copies are gone | key in Infisical + offline paper copy (S681 §14) | PENDING | §G-03 |
| 8 | **Nightly automation + silent-failure alerting** | The last backup job failed silently for months | scheduled jobs + daily heartbeat to `infra:backup-health` + dead-man alert | PENDING | §F-01 |

**Restore-from-bucket-alone answer (S723):** NOT YET. The bucket currently holds one snapshot of component 1. The other components still exist only in their primary homes (GitHub, Railway, Infisical, Cloudflare), so nothing is at imminent risk of permanent loss — but a true "rebuild the market from the bucket" posture requires rows 2–6 to go LIVE.

## §C. Architecture & Interactions
- **Immutable destination:** S3 `aimarket-backups-prod` (eu-north-1, acct 948749907373) — versioning + Object Lock **COMPLIANCE/35d** + SSE-S3 + public access blocked. Locked objects are un-deletable/un-overwritable by anyone (incl. root) for 35 days. (`aws-s3.md` §E-05/§E-06.)
- **Write path:** IAM `aimarket-backup-writer`, policy `backup-write-only` (PutObject + ListBucket only). A stolen writer key cannot destroy or alter history. Creds in Infisical `ai-market-backend` prod.
- **Tiers (S681):** (1) Railway-native scheduled backups/PITR on each Postgres; (2) immutable S3 copies (this bucket); (3) Time Machine on Titan-1; (4) Backblaze offsite. Independent failure domains.
- **Run location:** ai.market PG + repos + Railway/CF exports run from Titan-1 (reachable). Infisical PG dump runs **inside its own Railway project** (no public endpoint — deliberate hardening, not relaxed for backup).

## §D. Agent Capability Map
| Agent | Operation | Tool | Auth | Coverage |
|---|---|---|---|---|
| Vulcan | On-demand ai.market PG backup | `pg_dump@17` + boto3 (writer key) | backup-write-only + DB superuser URL | COMPLETE (§E-01) |
| Vulcan | Verify a backup landed / restore-readiness | boto3 list + `pg_restore --list` | read | COMPLETE (§E-03) |
| Vulcan | Build nightly jobs | launchd (Titan) + Railway cron | per-source | PENDING |
| Max | Enable Railway native backups/PITR | Railway console | owner | PENDING |
| Max | Offline custody of encryption + Infisical master key | offline | physical | PENDING |

## §E. Operate
**E-01 — On-demand ai.market PG backup (the path used S723).**
- `pg_dump@17 -Fc --no-owner --no-privileges` against the ai.market PG public proxy → local file → boto3 `upload_file` to `aimarket-backups-prod` under `postgres/ai-market/<YYYYMMDD>/railway-<ts>.dump` with sha256 + bytes in object metadata → local temp removed.
- creds: `AUTHOR_DISPATCH_DATABASE_URL` (DB) + `AWS_BACKUP_WRITER_*` (S3), both Infisical `ai-market-backend` prod, injected via `infisical run`.
- expected_success: pg_dump rc=0; S3 object size == local bytes; `pg_restore --list` returns a non-trivial TOC.

**E-02 — Nightly automated (PENDING build).** Titan launchd for rows 1,3,4,5; Railway-internal cron for row 2; daily heartbeat to `infra:backup-health`; dead-man alert on staleness. Until LIVE, run E-01 manually.

**E-03 — Verify a backup.** boto3 `list_objects_v2` shows today's object; size matches; `pg_restore --list` reads the archive (restore-readiness without restoring).

## §E-R. Restore the market (DR procedure, ordered)
> Order matters: secrets → infra → data → code → edge.
- **§E-R1 Pre-flight:** identify the failure (single component vs full loss). Retrieve the offline encryption key + Infisical master key from offline custody if online copies are gone.
- **§E-R2 ai.market PG:** provision a Postgres (Railway or elsewhere) → `pg_restore` the latest `postgres/ai-market/<date>/` dump → point the backend `DATABASE_URL` at it. (Marketplace + Living State + dispatch ledger come back together — they share one DB.)
- **§E-R3 Infisical PG:** provision Postgres → restore latest `postgres/infisical/<date>/` → bring up Infisical with its master key → all other services can now fetch secrets.
- **§E-R4 Source code:** `git clone` from `git-mirrors/` (or GitHub if intact) → repos restored.
- **§E-R5 Railway infra:** recreate project/services from `railway-config/<date>/` export → set env vars from restored Infisical → deploy from restored code.
- **§E-R6 Cloudflare:** redeploy Workers from code → restore KV from `cloudflare/<date>/` → re-apply DNS/zone config.
- **§E-R7 User/object data:** non-custodial seller data is in sellers' own S3 (not restored by us); restore any app object storage from its prefix; re-ingest Qdrant from source.
- **§E-R8 Validate:** health checks green; a known listing + order present; Living State queryable; signed publish works.

## §F. Isolate
| ID | Symptom | Probable cause | Verify | Repair | Confidence |
|---|---|---|---|---|---|
| F-01 | No new backup object for a source today | job not scheduled / silently failing (the S466 + Mar–Apr `koskadeux_backup` class — failed nightly for months pointing at a dead path) | `infra:backup-health` heartbeat stale; `list_objects_v2` shows no today prefix | §G-01 | CONFIRMED |
| F-02 | Dump uploaded but tiny / size mismatch | empty/partial dump; source unreachable mid-run | compare S3 size vs prior day; `pg_restore --list` TOC count drop >10% | §G-02 | CONFIRMED |
| F-03 | Can't decrypt a restored backup | wrong/lost encryption key | check key id vs object; retrieve offline copy | §G-03 | HYPOTHESIZED |

## §G. Repair
- **G-01** Re-establish the schedule (launchd/Railway cron); add the heartbeat + dead-man alert so a silent failure can't persist. Root cause class: jobs that fail without alerting (the exact gap that left us with zero working backups for months).
- **G-02** Re-run the dump; if source is the issue, fix connectivity; halt local rotation so a good prior copy isn't aged out by a bad run.
- **G-03** Retrieve the offline key/paper copy; never store the only copy on Titan-1.

## §H. Evolve — Invariants
1. **Immutability:** the offsite bucket is Object Lock COMPLIANCE — never weaken to Governance; never grant the writer key Delete/Bypass.
2. **Least privilege:** the backup writer can only add; restore/admin uses a separate, human-gated path.
3. **No public exposure of the secrets DB** to take a backup — back it up from inside its own network.
4. **Every scheduled backup must alert on failure** (no silent failure — ever again).
5. **A backup isn't real until a restore drill proves it** (§I + S681 §12).
- Change classes — BREAKING: weakening Object Lock; giving the writer delete/bypass; exposing the secrets DB publicly. REVIEW: new source; changing retention; changing run location. SAFE: adding a source backup per pattern; tagging; a verification check.

## §I. Acceptance Criteria
1. (E) "Take a backup of the ai.market DB now." → E-01.
2. (E) "Confirm last night's backups landed." → E-03 + `infra:backup-health`.
3. (R) "The ai.market DB is lost — restore it." → §E-R2.
4. (R) "Total loss — rebuild the market from the bucket." → §E-R1→R8 in order.
5. (F) "No backup appeared today and nobody noticed." → F-01 (the historical failure mode; heartbeat + dead-man must catch it).
6. (F) "A dump uploaded but is suspiciously small." → F-02 size/TOC check.
7. (H) Classify: "Switch the bucket to Governance so we can prune mistakes." → BREAKING (defeats compromise resistance).
8. (R) "Restore but the encryption key is gone." → §G-03 offline copy.
9. (E) "Back up the secrets DB." → in-Railway job (§E-R3 path), never a public proxy.
10. (ambiguous) "Backups seem broken." → acceptable first actions: check `infra:backup-health` staleness (F-01) OR list today's prefixes (F-01) OR compare object sizes vs prior day (F-02).

## §J. Lifecycle
- **last_refresh_session:** S723 (authored; bucket live, ai.market PG backed up; rows 2–8 pending)
- **last_refresh_commit:** S723 initial authoring
- **last_refresh_date:** 2026-05-28
- **owner_agent:** Vulcan-Primary
- **refresh_triggers:** a coverage row goes LIVE; new source; retention/mode change; restore drill; incident
- **scheduled_cadence:** 90 days
- **last_harness_pass_rate:** not yet run
- **last_harness_date:** null

## §K. Conformance
- **linter_version:** unverified — `runbook-lint` not yet run
- **last_lint_result:** NOT_RUN — prose form consistent with sibling runbooks; harness pass is a follow-up
- **status_caveat:** This runbook is intentionally honest about PENDING coverage. As each nightly source goes LIVE, flip its §B row and update §J.
