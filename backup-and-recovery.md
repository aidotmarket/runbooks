# Backup & Recovery — ai.market

> Source of truth for **what is backed up, where, on what cadence, how failure is alerted, and how to restore the market.** Destination/identity specifics: [aws-s3.md](./aws-s3.md). Secret locations: [infisical-secrets.md](./infisical-secrets.md). Architecture rationale: `BQ-AI-MARKET-COMPLETE-BACKUP-ARCHITECTURE-TITAN1-CENTRIC-S681`.

## §A. Header
- **system_name:** backup-and-recovery
- **purpose_sentence:** Define what must be backed up to reconstruct ai.market, how each piece is captured to the immutable S3 bucket, how a missed/failed backup pages Max on Telegram, and the exact restore procedure after data loss or credential compromise.
- **owner_agent:** Vulcan-Primary / Mars-Worker
- **escalation_contact:** Max (Telegram, primary)
- **lifecycle_ref:** §J
- **authoritative_scope:** Backup coverage, cadence, integrity verification, failure alerting, and per-component restore. Bucket lockdown + writer identity inherit from aws-s3.md.
- **last_verified:** 2026-06-07 (S795 — Qdrant nightly to S3 LIVE; watchdog covers PG+Qdrant; backup machine-identity Client ID rotated)

## §B. Coverage Matrix — what restoring the whole market requires
> **A row is DR-complete only when its backup is LIVE *and to S3*.** Honest status as of 2026-06-07 (S792). The migration target is: **everything to S3 `aimarket-backups-prod`; GCS retired.** Both the main Postgres DB and the Qdrant knowledge_base back up nightly to S3 (recurring, machine-identity auth), and the latest Postgres dump has been restore-validated (archive TOC verified). The legacy GCS bucket was **deleted 2026-06-07 (S795)** — S3 is now the sole off-database backup destination. Remaining migration: rows 3–4 (Infisical secrets DB, vectorAIz) to S3.

| # | Component | Why it matters | Backup method (target) | Status 2026-06-07 | Restore ref |
|---|---|---|---|---|---|
| 1 | **ai.market Postgres** (marketplace + Living State + dispatch ledger) | Core platform + dev/build state | nightly `pg_dump@17 -Fc` -> S3 `postgres/ai-market/<date>/` | **LIVE to S3 nightly (S793, machine identity)**; restore-validated 2026-06-07; GCS retired | §E-R2 |
| 2 | **ai.market Qdrant** (allAI knowledge_base) | allAI memory | nightly snapshot -> S3 `qdrant/<date>/` | **LIVE to S3 nightly (S794)**; GCS retired | §E-R7 |
| 3 | **Infisical Postgres** (secrets, root of trust) | Without secrets nothing authenticates/deploys | in-Railway scheduled dump -> S3 `postgres/infisical/<date>/` | **LIVE (S797)** — nightly Railway cron, age-encrypted to offline key; restore-drill verified (1,209 tables) | §E-R3 |
| 4 | **vectorAIz Postgres + Qdrant** (separate Railway project) | Second data surface | nightly dump/snapshot -> S3 | NONE; PENDING | §E-R7 |
| 5 | **Source code** (all `aidotmarket/*` repos) | The app, specs, handoff history | GitHub (durable) + Max Titan-1 clones; nightly `git --mirror` -> S3 `git-mirrors/` | Code SAFE (GitHub + local clones); S3 mirror PENDING | §E-R4 |
| 6 | **Railway deploy config** (services, env, domains, cron) | How code is wired into infra | nightly Railway API export -> S3 `railway-config/<date>/` | PENDING | §E-R5 |
| 7 | **Cloudflare** (Worker KV data, DNS/zone) | Edge routing, KV state | Worker code in repos; nightly KV + zone export -> S3 `cloudflare/<date>/` | PENDING | §E-R6 |
| 8 | **Failure alerting** | A backup must never fail silently again | S3-freshness watchdog -> Telegram; secondary GitHub issue | **LIVE (S792)** — see §F | §F-01 |

**Restore-from-S3-alone today:** PARTIAL. S3 now holds nightly main-DB dumps (row 1, restore-validated 2026-06-07) and Qdrant snapshots (row 2). Rows 3–7 still live only in their primary homes (GitHub, Railway, Infisical, Cloudflare), so nothing is at imminent risk of permanent loss; a true "rebuild the market from S3" posture still needs rows 3–4 LIVE to S3.

## §C. Architecture & Interactions
- **Primary destination (target):** S3 `aimarket-backups-prod` — eu-north-1, acct `948749907373`. Versioning + **Object Lock COMPLIANCE / 35-day** + SSE-S3 + Block-Public-Access. A locked object cannot be deleted or overwritten by anyone (incl. root) for 35 days — survives a stolen credential. Layout `postgres/ai-market/<date>/`, `postgres/infisical/<date>/`, `qdrant/`.
- **Write identity:** IAM `aimarket-backup-writer`, policy `backup-write-only` (PutObject + ListBucket only). Creds in Infisical `ai-market-backend` prod (`AWS_BACKUP_WRITER_ACCESS_KEY_ID` / `_SECRET`). Manual ops use `aws --profile aimarket` (svc-titan-vulcan).
- **Legacy destination (RETIRED 2026-06-07, S795):** GCS `gs://aimarket-backups` (GCP project `aimarket-prod`) has been **deleted**. Its writer (GitHub Actions `backup.yml`) was disabled in S794; the bucket held only rows 1–2, now live + restore-validated on S3. Latent GCS code still exists but is unscheduled — `backup.yml` (disabled) and `scripts/backup_all.py` / `scripts/backup_qdrant.sh` (no live trigger runs them) — remove as code cleanup.
- **Tiers (S681 target):** (1) Railway-native PITR per Postgres; (2) immutable S3 (this bucket); (3) Time Machine on Titan-1; (4) Backblaze offsite. Independent failure domains.

## §D. Current Mechanisms (exact, as deployed)
| Mechanism | Where | Schedule | Does | Status |
|---|---|---|---|---|
| GitHub Actions `Automated Backups` (`backup.yml`) | aidotmarket/ai-market-backend | daily 03:00 UTC + dispatch | `pg_dump` + Qdrant snapshot -> **GCS**; opens a GitHub issue on failure | **DISABLED (S794)** — was the GCS writer; GCS bucket retired S795 |
| GitHub Actions `Backup Staleness Check` (`backup-verify.yml`) | same | daily 06:00 UTC | hits `/api/v1/internal/backup-status`; opens a GitHub issue if PG/Qdrant > 6h stale | **DISABLED (S794)** — read GCS-fed events; superseded by the S3 watchdog (§F) |
| launchd `com.aimarket.pg-backup` (`run_pg_backup.sh` -> `backup_pg.py`) | Titan-1 | 01:00/02:00 Europe/Berlin | direct `pg_dump` -> **S3** via machine-identity `infisical run` | **LIVE (S793)** — revived via Universal Auth machine identity; verified 2.41 GB dump to S3 |
| Railway cron `infisical-pg-backup` (`backup_pg.py`, config `railway.infisical-backup.json`) | Railway (infisical secrets project) | 03:00 UTC nightly | `pg_dump`@18 -> age-encrypt -> **S3** `postgres/infisical/<date>/` via write-only key | **LIVE (S797)** — restore-drill verified, 1,209 tables / 6,994 entries |
| **launchd `com.aimarket.qdrant-backup`** (`run_qdrant_backup.sh` -> `backup_qdrant.py`) | Titan-1 | 02:30/03:30 Europe/Berlin (per-UTC-day lock) | snapshot `knowledge_base` -> **S3** `qdrant/<date>/`; size-verified via ListBucket; health record to `backup-health/qdrant/last-run.json` | **LIVE (S794)** — ran via launchd path, verified |
| **launchd `com.aimarket.s3-backup-watchdog`** (`runbooks/scripts/s3_backup_watchdog.sh`) | Titan-1 | every 6h + RunAtLoad | checks newest S3 **Postgres and Qdrant** objects; **Telegram alert if missing or > 26h** | **LIVE (S792, widened S794)** — see §F |
| ~~Manual GCS->S3 copy~~ | — | — | — | **OBSOLETE (S795)** — GCS retired; nightly direct-to-S3 jobs supersede this |

## §E. Operate
**E-01 — Take an immediate S3 backup of the main DB now.** Run the nightly direct-to-S3 job on demand: `launchctl kickstart -k gui/$(id -u)/com.aimarket.pg-backup`, then confirm a fresh object via §E-03. The job authenticates via the Infisical machine identity and writes straight to S3 (no GCS).
**E-02 — (retired).** The GCS recurring workflow was disabled S794 and the bucket deleted S795. Recurring backups are now the Titan-1 launchd jobs (§D); trigger one on demand via §E-01.
**E-03 — Verify a backup landed.** `aws s3 ls s3://aimarket-backups-prod/postgres/ai-market/ --recursive --profile aimarket | tail`; size > 0; optionally `pg_restore --list <dump>` returns a TOC.
**E-04 — Revive the direct nightly S3 job** (after §H-1 machine identity exists): set the identity's client-id/secret where `run_pg_backup.sh` can read them non-interactively (NOT interactive `infisical login`), `launchctl kickstart -k gui/$(id -u)/com.aimarket.pg-backup`, confirm a fresh object lands + the watchdog logs OK.

## §E-R. Restore the market (ordered: secrets -> infra -> data -> code -> edge)
- **R1 Pre-flight:** scope the failure (one component vs total loss). Retrieve the offline encryption + Infisical master key if online copies are gone.
- **R2 ai.market PG:** provision Postgres -> `pg_restore` latest `postgres/ai-market/<date>/` -> point backend `DATABASE_URL` at it.
- **R3 Infisical PG (verified S797):** nightly Railway cron writes an **age-encrypted** custom-format dump to `postgres/infisical/<date>/railway-<ts>.dump.age`. Restore: (1) pull the latest `.age` from S3; (2) decrypt with the **OFFLINE age key** (1Password only; never on Titan-1/Railway/Infisical): `age -d -i <key> -o infisical.dump <obj>.age`; (3) restore with a **Postgres 18** client (secrets DB is PG18; Titan-1 local client is 14 -> use `docker run --rm -v "$PWD":/work postgres:18 pg_restore --clean --if-exists -d <new-db-url> /work/infisical.dump`, or `-l` to list); (4) bring Infisical up with its master key. NOTE: the dump is age-encrypted because it exposes secret paths / project+member structure / schema even without the master key — the age key is REQUIRED and there is **no recovery if it is lost**.
- **R4 Source:** `git clone` from `git-mirrors/` (or GitHub) .
- **R5 Railway infra:** recreate services from `railway-config/<date>/` -> set env from restored Infisical -> deploy restored code.
- **R6 Cloudflare:** redeploy Workers -> restore KV from `cloudflare/<date>/` -> re-apply DNS.
- **R7 Data:** non-custodial seller data is in sellers' own S3 (not ours); re-ingest Qdrant from `qdrant/` or source.
- **R8 Validate:** health green; a known listing + order present; Living State queryable; signed publish works.

## §F. Failure Alerting — Telegram (the dead-man's switch)
**This is the answer to "tell me when a backup does not run."**
- **What:** `com.aimarket.s3-backup-watchdog` runs `runbooks/scripts/s3_backup_watchdog.sh` every 6 hours (and at load).
- **Check:** newest object under `s3://aimarket-backups-prod/postgres/ai-market/` **and** under `s3://aimarket-backups-prod/qdrant/`. If either is missing, or older than **26h**, it fires.
- **Alert path:** direct HTTPS POST to `https://api.telegram.org/bot<token>/sendMessage` -> bot **koskadeux_bot** -> Max's chat. Creds `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` read from `koskadeux-mcp/.env`. No Infisical dependency (deliberate — the alerter must work even when Infisical is the thing that's broken).
- **Verified:** 2026-06-07 test ping delivered (message_id 1639) to chat 80805807.
- **Secondary alert:** the GitHub `Backup Staleness Check` opens an urgent GitHub issue (email) if the backend-reported PG/Qdrant backups go > 6h stale.
- **Log:** `~/Library/Logs/aimarket_s3_backup_watchdog.log` (one `OK`/`ALERT` line per run).
- **Test it:** `bash /Users/max/Projects/ai-market/runbooks/scripts/s3_backup_watchdog.sh` (logs OK when fresh); to force-test the channel, temporarily lower `MAX_AGE_H` or send a manual `sendMessage` curl.

| ID | Symptom | Cause | Verify | Repair |
|---|---|---|---|---|
| F-01 | No fresh S3 object today | nightly job not running (e.g. Infisical login expired — the 2026-05-29 class) | watchdog ALERT in log + Telegram; `aws s3 ls` shows no today prefix | §H-1 revive job; meanwhile §E-01 |
| F-02 | Dump present but tiny | empty/partial dump | size vs prior day; `pg_restore --list` TOC drop | re-run; fix source; halt rotation so a good copy isn't pruned |
| F-03 | No Telegram alert despite stale | watchdog not loaded / Telegram creds rotated | `launchctl list | grep s3-backup-watchdog`; check `.env` creds | reload plist; refresh creds in `koskadeux-mcp/.env` |
| F-04 | Can't decrypt a restored backup | wrong/lost key | key id vs object | retrieve offline copy |

## §G. Repair
- **G-01** Re-establish the schedule + alert so a silent failure can't persist (root-cause class: jobs that fail without paging). 
- **G-02** Re-run the dump; fix source connectivity; halt local rotation so a good prior copy isn't aged out.
- **G-03** Retrieve the offline key/paper copy; never store the only copy on Titan-1.

## §H. Evolve — Invariants & the Infisical root-cause fix
1. **Automated jobs authenticate to Infisical with a MACHINE IDENTITY (Universal Auth client-id/secret or access token) — NEVER interactive `infisical login`.** Interactive sessions expire and then fail silently into a login prompt — the exact cause of the 2026-05-29 backup death and the recurring "Infisical keeps bothering me" pain. Machine-identity tokens are non-interactive and renewable. This is the keystone that unblocks rows 1–4 to S3.
2. **Immutability:** the S3 bucket stays Object Lock COMPLIANCE — never weaken to Governance; never give the writer key Delete/Bypass.
3. **The alerter must not depend on Infisical** (it reads Telegram creds from `.env`) — so it still pages even when Infisical is down.
4. **Back up Infisical's own DB to S3** (row 3) — the root of trust must be recoverable; keep the master key offline.
5. **A backup isn't real until a restore drill proves it.** GCS was retired 2026-06-07 once rows 1–2 were live to S3 and the latest PG dump passed an archive-TOC restore drill; a full scratch-restore drill remains the gold standard to schedule. Rows 3–4 still owe S3 coverage + their own drill.
- Change classes — BREAKING: weakening Object Lock; writer delete/bypass; exposing the secrets DB publicly; an Infisical consumer reverting to interactive login. REVIEW: new source; retention change; run-location change. SAFE: add a source per pattern; tagging; a verification check.

## §I. Acceptance Criteria
1. (E) "Take a backup now." -> §E-01.  2. (E) "Confirm last night landed." -> §E-03.  3. (R) "Main DB lost." -> §E-R2.  4. (R) "Total loss — rebuild from S3." -> §E-R1→R8.  5. (F) "A backup didn't run and nobody noticed." -> §F watchdog Telegram (primary) + GitHub staleness (secondary).  6. (F) "Dump suspiciously small." -> F-02.  7. (H) "Switch bucket to Governance to prune mistakes." -> BREAKING, refuse.  8. (R) "Restore but key is gone." -> G-03 offline copy.  9. (E) "Back up the secrets DB." -> in-Railway dump, never a public proxy (§H-4).  10. (H) "Why does Infisical keep breaking backups?" -> §H-1: interactive login expiry; fix = machine identity.

## §J. Lifecycle
- **last_refresh_session:** S795 (GCS bucket retired/deleted + latest S3 PG dump restore-validated; Qdrant nightly to S3 documented LIVE; watchdog widened to PG+Qdrant; backup machine-identity Client ID rotation recorded; §B/§C/§D/§E/§H GCS references reconciled to retired state)
- **last_refresh_date:** 2026-06-07
- **owner_agent:** Vulcan-Primary / Mars-Worker
- **refresh_triggers:** a coverage row goes LIVE to S3; machine identity created; GCS retired; restore drill; incident
- **scheduled_cadence:** 90 days

## §K. Conformance
- **linter_version:** not yet run (prose form; harness pass is a follow-up)
- **status_caveat:** Intentionally honest about PENDING coverage. Flip §B/§D rows and update §J as each S3 source goes LIVE.

---

## 2026-06-07 (S793): Machine identity LIVE — direct S3 nightly backup restored

Root-cause fix for the recurring Infisical login-expiry failures (job dead since 2026-05-29).

- Auth: `com.aimarket.pg-backup` now uses an Infisical Universal Auth machine identity (`titan1-unattended-backup`, Viewer on the ai-market-backend prod project). No interactive `infisical login`.
- Credentials on Titan-1: `~/.config/infisical/backup-machine-identity.client-id` and `.client-secret` (owner `max`, `chmod 600`). Job logs in non-interactively and passes the short-lived token to `infisical run`.
- Login retry: `secrets.ai.market` resolves to two Cloudflare anycast IPs and one is intermittently unreachable from Titan-1 (suspected Tailscale dual-default-route; not yet root-caused). Job retries login up to 6x.
- Postgres client: server is v17, so the job pins `PG_DUMP_BIN`/`PG_RESTORE_BIN` to `/opt/homebrew/opt/postgresql@17/bin` (default PATH `pg_dump` was v14 and refused).
- Script location: LaunchAgent runs `/Users/max/ops/aimarket-backend-main/scripts/run_pg_backup.sh`, a worktree pinned to `origin/main`, so the live job no longer depends on a dev checkout's branch. Refresh with `git -C /Users/max/ops/aimarket-backend-main pull` after backup-script changes merge to main.
- Verified 2026-06-07: produced `s3://aimarket-backups-prod/postgres/ai-market/20260607/railway-20260607T135444Z.dump` (2.41 GB, size+sha256 verified), health `status=ok`, watchdog healthy.

### Still open
- ~~Extend coverage to the Infisical secrets DB; full restore drill.~~ **DONE (S797):** Infisical secrets DB backed up nightly (Railway cron, age-encrypted) + restore-drill verified. Still open: vectorAIz project coverage. Follow-up: merge `feat/bq-infisical-secrets-db-s3-backup-s795` -> main and repoint the Railway service to main (it currently builds from the branch). ~~Retire GCS~~ **DONE (S795):** GCS `aimarket-backups` deleted by Max after rows 1–2 verified live + restore-validated on S3.
- ~~Rotate the machine-identity Client Secret (it transited chat during setup).~~ **DONE (S794):** recreating the Universal Auth method changed the Client ID; new Client ID `6673bf3a-3601-4df3-9e01-f7b5bb42e8e4` synced to `~/.config/infisical/backup-machine-identity.client-id`, secret rotated via the paste-once tool, old secret revoked. Verified: auth OK, 118 secrets injected, full PG backup ran.
- Root-cause the secrets.ai.market reachability flap. **Mitigated (S794):** `tailscale set --accept-routes=false` on Titan-1 (it was pulling egress onto the tunnel); secrets.ai.market healthy over LAN. WATCH: a stale utun9 default route lingers and Tailscale CLI 1.94.2 lags daemon 1.98.5 — if the flap recurs, clear the version skew / bounce tailscaled.
- Convert or retire other Infisical consumers (e.g. `com.koskadeux.infisical-token-refresh`) after review.

### 2026-06-08 (S797): Infisical secrets DB backup — LIVE + restore-verified
- New Railway cron `infisical-pg-backup` in the infisical secrets-management project (config `railway.infisical-backup.json`, branch `feat/bq-infisical-secrets-db-s3-backup-s795`): nightly 03:00 UTC, `pg_dump`@18 -> age-encrypt -> S3 `postgres/infisical/`, write-only key, restartPolicy NEVER.
- Encrypts to an OFFLINE age recipient (private key in 1Password only); creds are STATIC Railway vars, never fetched from Infisical (no circular dependency on the thing being backed up).
- Watchdog now monitors `postgres/infisical/` (>26h missing/stale).
- Bugs fixed at source en route: Dockerfile `useradd` collided with the Debian `backup` user; root `.dockerignore` hid `scripts/` (added per-Dockerfile ignore); pg client 17 -> 18 (server 18.3); shared repo `railway.json` forced the backend build (added dedicated config file); creds now whitespace-trimmed (a paste newline caused SignatureDoesNotMatch).
- Restore drill: decrypted with the offline key, `pg_restore -l` via a PG18 client listed 6,994 TOC entries / 1,209 tables, no corruption.
