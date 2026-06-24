# Backup & Recovery — ai.market

> Source of truth for **what is backed up, where, on what cadence, how failure is alerted, and how to restore the market.** Destination/identity specifics: [aws-s3.md](./aws-s3.md). Secret locations: [infisical-secrets.md](./infisical-secrets.md). Architecture rationale: `BQ-AI-MARKET-COMPLETE-BACKUP-ARCHITECTURE-TITAN1-CENTRIC-S681`.

## §A. Header
- **system_name:** backup-and-recovery
- **purpose_sentence:** Define what must be backed up to reconstruct ai.market, how each piece is captured to the immutable S3 bucket, how a missed/failed backup pages Max on Telegram, and the exact restore procedure after data loss or credential compromise.
- **owner_agent:** Vulcan-Primary / Mars-Worker
- **escalation_contact:** Max (Telegram, primary)
- **lifecycle_ref:** §J
- **authoritative_scope:** Backup coverage, cadence, integrity verification, failure alerting, and per-component restore. Bucket lockdown + writer identity inherit from aws-s3.md.
- **last_verified:** 2026-06-16 (S884 — main-DB nightly backup migrated off Titan-1 to Railway-native cron `ai-market-backup` @ 02:00 UTC; Titan-1 launchd `com.aimarket.pg-backup` disabled; §F-02 retired)

## §B. Coverage Matrix — what restoring the whole market requires
> **A row is DR-complete only when its backup is LIVE *and to S3*.** Honest status as of 2026-06-07 (S792). The migration target is: **everything to S3 `aimarket-backups-prod`; GCS retired.** Both the main Postgres DB and the Qdrant knowledge_base back up nightly to S3 (recurring, machine-identity auth), and the latest Postgres dump has been restore-validated (archive TOC verified). The legacy GCS bucket was **deleted 2026-06-07 (S795)** — S3 is now the sole off-database backup destination. Remaining migration: rows 3–4 (Infisical secrets DB, vectorAIz) to S3.

| # | Component | Why it matters | Backup method (target) | Status 2026-06-07 | Restore ref |
|---|---|---|---|---|---|
| 1 | **ai.market Postgres** (marketplace + Living State + dispatch ledger) | Core platform + dev/build state | nightly `pg_dump@17 -Fc` -> S3 `postgres/ai-market/<date>/` | **LIVE to S3 nightly (S884) — Railway-native cron `ai-market-backup` @ 02:00 UTC** (migrated off Titan-1); restore-validated 2026-06-07 | §E-R2 |
| 2 | **ai.market Qdrant** (allAI knowledge_base) | allAI memory | nightly snapshot -> S3 `qdrant/<date>/` | **LIVE to S3 nightly (S794)**; GCS retired | §E-R7 |
| 3 | **Infisical Postgres** (secrets, root of trust) | Without secrets nothing authenticates/deploys | in-Railway scheduled dump -> S3 `postgres/infisical/<date>/` | **LIVE (S797)** — nightly Railway cron, age-encrypted to offline key; restore-drill verified (1,209 tables) | §E-R3 |
| 4 | **vectorAIz + AIM Data (our own)** | Our own second-surface data | n/a — on Titan-1 | **OUT OF SCOPE for S3 (owner decision S799):** our own AIM Data + vectorAIz data lives on Titan-1, covered by Titan-1 local + physically-separate backup; customer data is non-custodial (sellers' own buckets). Not in S3 by design. | Titan-1 backup |
| 5 | **Source code** (all `aidotmarket/*` repos) | The app, specs, handoff history | GitHub (durable) + Max Titan-1 clones; nightly `git --mirror` -> S3 `git-mirrors/` | Code SAFE (GitHub + local clones); S3 mirror PENDING | §E-R4 |
| 6 | **Railway deploy config** (services, env, domains, cron) | How code is wired into infra | nightly Railway API export -> S3 `railway-config/<date>/` | **LIVE (S799.w):** nightly export (04:00/05:00 local, machine-identity) + watchdog monitors `railway-config/` | §E-R5 |
| 7 | **Cloudflare** (Worker KV data, DNS/zone) | Edge routing, KV state | Worker code in repos; nightly KV + zone export -> S3 `cloudflare/<date>/` | **LIVE (S799.w):** nightly DNS records + zone settings to `cloudflare/<date>/` (04:30/05:30 local, machine-identity) + watchdog; Worker scripts in GitHub; KV not captured (token scope; regenerable DMS counters) | §E-R6 |
| 8 | **Failure alerting** | A backup must never fail silently again | S3-freshness watchdog -> Telegram; secondary GitHub issue | **LIVE (S792)** — see §F | §F-01 |

**Restore-from-S3-alone today:** PARTIAL. S3 now holds nightly main-DB dumps (row 1, restore-validated 2026-06-07) and Qdrant snapshots (row 2). Rows 3–7 still live only in their primary homes (GitHub, Railway, Infisical, Cloudflare), so nothing is at imminent risk of permanent loss; a true "rebuild the market from S3" posture still needs rows 3–4 LIVE to S3.

## §C. Architecture & Interactions
- **Primary destination (target):** S3 `aimarket-backups-prod` — eu-north-1, acct `948749907373`. Versioning + **Object Lock COMPLIANCE / 35-day** + SSE-S3 + Block-Public-Access. A locked object cannot be deleted or overwritten by anyone (incl. root) for 35 days — survives a stolen credential. Layout `postgres/ai-market/<date>/`, `postgres/infisical/<date>/`, `qdrant/`.
- **Write identity:** IAM `aimarket-backup-writer`, policy `backup-write-only` (PutObject + ListBucket only). Creds in Infisical `ai-market-backend` prod (`AWS_BACKUP_WRITER_ACCESS_KEY_ID` / `_SECRET`). Manual ops use `aws --profile aimarket` (svc-titan-vulcan).
- **Legacy destination (RETIRED 2026-06-07, S795; writer + dead code DELETED 2026-06-24, S1014):** GCS `gs://aimarket-backups` (GCP project `aimarket-prod`) has been **deleted**. Its writer, GitHub Actions `backup.yml`, was *believed* disabled in S794 but in fact kept running on its 03:00 cron and 404ing against the deleted bucket daily (false 'backup failed' email + Telegram) until it was **deleted from the repo in S1014** (commit cb149908). The latent GCS code it relied on was also deleted in S1014 (commit dfd53cfd): `scripts/backup_all.py`, `scripts/backup_local.py`, `scripts/backup_qdrant.sh`, and the `services/backup/` 'Unified Backup Service' dir (no importers; no Railway service deployed from it). Live S3 scripts `scripts/backup_pg.py` + `scripts/backup_qdrant_s3.py` retained.
- **Tiers (S681 target):** (1) Railway-native PITR per Postgres; (2) immutable S3 (this bucket); (3) Time Machine on Titan-1; (4) Backblaze offsite. Independent failure domains.

## §D. Current Mechanisms (exact, as deployed)
| Mechanism | Where | Schedule | Does | Status |
|---|---|---|---|---|
| GitHub Actions `Automated Backups` (`backup.yml`) | aidotmarket/ai-market-backend | (was) daily 03:00 UTC + dispatch | `pg_dump` + Qdrant snapshot -> **GCS**; opened a GitHub issue on failure | **DELETED (S1014, commit cb149908)** — was NEVER effectively disabled despite the S794 note; kept firing daily and 404ing on the deleted GCS bucket. Removed from the repo. |
| GitHub Actions `Backup Staleness Check` (`backup-verify.yml`) | same | daily 06:00 UTC + dispatch | hits `/api/v1/internal/backup-status`; opens a GitHub issue if PG/Qdrant > 6h stale | **LIVE (still active as of S1014 — the S794 'disabled' note was WRONG).** Legitimate secondary dead-man's-switch; accuracy depends on the backend `backup-status` / SysAdmin verifier reading S3 truthfully (S1014 write-only-key HeadObject fix). |
| Railway cron `ai-market-backup` (`backup_pg.py`, `Dockerfile.ai-market-backup`, config `railway.ai-market-backup.json`) | Railway (ai-market project) | 02:00 UTC nightly (restart NEVER) | `pg_dump@17 -Fc` -> **S3** `postgres/ai-market/<date>/` + health record; DB via `AUTHOR_DISPATCH_DATABASE_URL`, S3 via `${{ai-market-backend.AWS_BACKUP_WRITER_*}}` | **LIVE (S884)** — migrated off Titan-1 (launchd `com.aimarket.pg-backup` now disabled); manual run verified 3.31 GB dump, ~8 min. **Heartbeat (S909, T-2026-000021 RESOLVED):** the run writes the `infra:backup-health` heartbeat with real `sha256`/`toc_entries` and is now **fail-loud** — see E-01a. |
| Railway cron `infisical-pg-backup` (`backup_pg.py`, config `railway.infisical-backup.json`) | Railway (infisical secrets project) | 03:00 UTC nightly | `pg_dump`@18 -> age-encrypt -> **S3** `postgres/infisical/<date>/` via write-only key | **LIVE (S797)** — restore-drill verified, 1,209 tables / 6,994 entries |
| **launchd `com.aimarket.qdrant-backup`** (`run_qdrant_backup.sh` -> `backup_qdrant.py`) | Titan-1 | 02:30/03:30 Europe/Berlin (per-UTC-day lock) | snapshot `knowledge_base` -> **S3** `qdrant/<date>/`; size-verified via ListBucket; health record to `backup-health/qdrant/last-run.json` | **LIVE (S794)** — ran via launchd path, verified |
| **launchd `com.aimarket.s3-backup-watchdog`** (`runbooks/scripts/s3_backup_watchdog.sh`) | Titan-1 | every 6h + RunAtLoad | checks newest S3 **Postgres and Qdrant** objects; **Telegram alert if missing or > 26h** | **LIVE (S792, widened S794)** — see §F |
| ~~Manual GCS->S3 copy~~ | — | — | — | **OBSOLETE (S795)** — GCS retired; nightly direct-to-S3 jobs supersede this |

## §E. Operate
**E-01 — Take an immediate S3 backup of the main DB now.** Trigger the Railway `ai-market-backup` cron service on demand: Railway dashboard -> ai-market project -> `ai-market-backup` -> **Run now** (API equiv: `deploymentInstanceExecutionCreate(serviceInstanceId)`), then confirm a fresh object via §E-03. It dumps over `AUTHOR_DISPATCH_DATABASE_URL` and writes straight to S3 with the backup-writer key. (Legacy Titan-1 `launchctl kickstart com.aimarket.pg-backup` is retired/disabled S884; plist preserved for emergency revert per §E-04.)
**E-01a — Backup heartbeat env dependency (S909, T-2026-000021).** The `ai-market-backup` service MUST have `INTERNAL_API_KEY` (= backend internal key; Infisical project `ai-market-backend`) and `RAILWAY_BACKEND_URL` (= `https://ai-market-backend-production.up.railway.app`) set — they drive the `infra:backup-health` Living State heartbeat. Set S909 (previously absent, which silently skipped the heartbeat, froze it >26h, and fired a **false-positive P0** — incident a53ada1d). The heartbeat is now **fail-loud**: on a successful dump the S3 object always uploads first, then if the heartbeat cannot be written the run logs an S3 health record `status=failed` `stage=living_state_heartbeat` and **exits 10** instead of skipping. Service id `53aa2e80-8ffa-4e22-a38f-f52a6b6c6c80`, instance `2307844d-5fac-4342-8ec2-afdf92219d91`. Verified S909: on-demand run wrote heartbeat `status=ok` sha256 `be78a33a…` toc 2271.
**E-02 — (retired).** The GCS recurring workflow was disabled S794 and the bucket deleted S795. Recurring backups are now the Titan-1 launchd jobs (§D); trigger one on demand via §E-01.
**E-03 — Verify a backup landed.** `aws s3 ls s3://aimarket-backups-prod/postgres/ai-market/ --recursive --profile aimarket | tail`; size > 0; optionally `pg_restore --list <dump>` returns a TOC.
**E-04 — Emergency revert to the Titan-1 job** (only if the Railway `ai-market-backup` cron is broken): the launchd plist is preserved at `~/Library/LaunchAgents/com.aimarket.pg-backup.plist` (disabled S884). Re-enable: `launchctl enable gui/$(id -u)/com.aimarket.pg-backup && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aimarket.pg-backup.plist`, then kickstart it. Prefer fixing the Railway service first.

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

**§F-02 — (retired S884).** The dual-Berlin-slot launchd failure mode no longer applies: the main-DB backup is a single Railway cron at 02:00 UTC (restart NEVER), not the back-to-back 01:00/02:00 Berlin launchd slots. The 2026-06-10 transient mid-dump disconnect is mitigated by running inside Railway. CAVEAT: the Railway run still connects over the public proxy (`AUTHOR_DISPATCH_DATABASE_URL`); pointing it at the internal DB host would cut runtime/exposure further (optional). S884 FINDING: Railway's own `Postgres`-service and project-shared `DATABASE_URL` vars are STALE — they do not authenticate; the only working main-DB credential is Infisical `AUTHOR_DISPATCH_DATABASE_URL`. Do not trust the Railway-native DB URLs for restore/ops; separate cleanup advised.
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
- **last_refresh_session:** S799.w (Mars — see 2026-06-08 note: infisical backup cron schedule restored + merged to main + service-name/monitoring reconciliation). Prior S795 (GCS bucket retired/deleted + latest S3 PG dump restore-validated; Qdrant nightly to S3 documented LIVE; watchdog widened to PG+Qdrant; backup machine-identity Client ID rotation recorded; §B/§C/§D/§E/§H GCS references reconciled to retired state)
- **last_refresh_date:** 2026-06-08
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
- ~~Extend coverage to the Infisical secrets DB; full restore drill.~~ **DONE (S797):** Infisical secrets DB backed up nightly (Railway cron, age-encrypted) + restore-drill verified. Still open: vectorAIz project coverage. Follow-up: ~~merge to main~~ **DONE (S799.w)** — merged (cron restored on the branch first). **Still pending: repoint the Railway service from `feat/bq-infisical-secrets-db-s3-backup-s795` to `main`** (it still builds from the branch). ~~Retire GCS~~ **DONE (S795):** GCS `aimarket-backups` deleted by Max after rows 1–2 verified live + restore-validated on S3.
- ~~Rotate the machine-identity Client Secret (it transited chat during setup).~~ **DONE (S794):** recreating the Universal Auth method changed the Client ID; new Client ID `6673bf3a-3601-4df3-9e01-f7b5bb42e8e4` synced to `~/.config/infisical/backup-machine-identity.client-id`, secret rotated via the paste-once tool, old secret revoked. Verified: auth OK, 118 secrets injected, full PG backup ran.
- Root-cause the secrets.ai.market reachability flap. **Mitigated (S794):** `tailscale set --accept-routes=false` on Titan-1 (it was pulling egress onto the tunnel); secrets.ai.market healthy over LAN. WATCH: a stale utun9 default route lingers and Tailscale CLI 1.94.2 lags daemon 1.98.5 — if the flap recurs, clear the version skew / bounce tailscaled.
- Convert or retire other Infisical consumers (e.g. `com.koskadeux.infisical-token-refresh`) after review.

### 2026-06-08 (S797): Infisical secrets DB backup — LIVE + restore-verified
- New Railway cron `infisical-pg-backup` in the infisical secrets-management project (config `railway.infisical-backup.json`, branch `feat/bq-infisical-secrets-db-s3-backup-s795`): nightly 03:00 UTC, `pg_dump`@18 -> age-encrypt -> S3 `postgres/infisical/`, write-only key, restartPolicy NEVER.
- Encrypts to an OFFLINE age recipient (private key in 1Password only); creds are STATIC Railway vars, never fetched from Infisical (no circular dependency on the thing being backed up).
- Watchdog now monitors `postgres/infisical/` (>26h missing/stale).
- Bugs fixed at source en route: Dockerfile `useradd` collided with the Debian `backup` user; root `.dockerignore` hid `scripts/` (added per-Dockerfile ignore); pg client 17 -> 18 (server 18.3); shared repo `railway.json` forced the backend build (added dedicated config file); creds now whitespace-trimmed (a paste newline caused SignatureDoesNotMatch).
- Restore drill: decrypted with the offline key, `pg_restore -l` via a PG18 client listed 6,994 TOC entries / 1,209 tables, no corruption.


### 2026-06-08 (S799.w): cron schedule restored, merged to main, naming + monitoring reconciliation

Investigating a "do-not-merge-blind" flag on the infisical backup branch surfaced a real defect plus three doc/reality gaps. All resolved or recorded:

- **Schedule defect (fixed + live).** A one-shot end-to-end test commit had dropped `cronSchedule` from `railway.infisical-backup.json`'s `deploy` block with a subject claiming it was restored afterwards — it never was, and the branch tip carried no cron. The live service builds **config-as-code from that file**, so the schedule survived only because the service had not yet redeployed off the cron-less tip; the next redeploy would have silently disabled nightly secrets backups. Restored `0 3 * * *` and pushed; the service auto-redeployed and the build succeeded from the cron-restored commit. Nightly 03:00 UTC is back in place (including the earlier SignatureDoesNotMatch cred-trim fix).
- **Schedule lives in config-as-code, NOT the Railway dashboard.** To change the secrets-backup schedule, edit `deploy.cronSchedule` in `railway.infisical-backup.json` and redeploy. Editing it in the Railway UI does not persist across deploys.
- **Service-name correction.** The live Railway service is named **`ai-market-backend`** inside the **`infisical secrets-management.`** project — it shares the repo with the API but uses `Dockerfile.infisical-backup` + config `railway.infisical-backup.json` to run the backup job. It is NOT literally named `infisical-pg-backup`; do not search for that name. Railway's GraphQL `ServiceInstance` type does not expose `branch`/`cronSchedule` — read the schedule from the config file or a deployment's `meta.serviceManifest`, not the API.
- **Backup-target wiring.** `scripts/backup_pg.py` is unified by `BACKUP_TARGET`: `infisical` -> dumps `BACKUP_DATABASE_URL`, age-encrypts (`AGE_RECIPIENT`), uploads `postgres/infisical/<date>/...dump.age`; `ai-market` -> dumps `AUTHOR_DISPATCH_DATABASE_URL`, unencrypted, `postgres/ai-market/`. AWS creds `AWS_BACKUP_WRITER_ACCESS_KEY_ID` / `_SECRET` (write+list only).
- **Alerting confirmed live.** The S3 dead-man's-switch watchdog DOES monitor `postgres/infisical/` (target `infisical-secrets`, >26h -> Telegram) and its launchd job is loaded — a missed secrets backup pages Max independent of Infisical/Living State.
- **Minor open item.** The in-Railway job's heartbeat to Living State `infra:backup-health` is not landing for the `infisical` source (still under `pending_sources`) — likely the service lacks `INTERNAL_API_KEY` / `RAILWAY_BACKEND_URL`. Not safety-critical (the watchdog covers alerting); wiring it would move `infisical-pg` out of `pending_sources`.


### 2026-06-08 (S799.w, cont.): Railway-config export + disaster-recovery map
- **Railway topology export to S3.** New `scripts/railway_config_export.py` queries every Railway project -> service for source repo/branch, config-as-code path, cron, region, and variable NAMES (secret VALUES deliberately excluded — they live in Infisical, already backed up). First snapshot uploaded to `s3://aimarket-backups-prod/railway-config/<date>/`. **Now recurring (S799.w):** nightly launchd job `com.aimarket.railway-config-export` (04:00/05:00 local, machine-identity, mirrors the qdrant backup) runs `run_railway_config_export.sh` -> `railway_config_export.py`; watchdog extended to monitor `railway-config/`.
- **Disaster-recovery map.** New `disaster-recovery.md` (the rebuild map: bucket layout, offline bootstrap items, restore order, monitoring). A copy is stored at `s3://aimarket-backups-prod/RESTORE-README.md` so the map survives even if GitHub + Titan-1 are gone.
- **Honest coverage:** core data (main DB, allAI memory, secrets DB) is LIVE to immutable S3 + watchdog-alarmed. Still not in S3: vectorAIz data, Cloudflare (Worker KV/DNS), S3 git mirror. Code is safe via GitHub + local clones. "Rebuild entirely from S3 alone" remains PARTIAL until those land.


### 2026-06-08 (S799.w): vectorAIz + AIM Data excluded from S3 (owner decision)
Our own AIM Data and vectorAIz data lives on Titan-1 and is covered by Titan-1's own local + physically-separate backup; customer datasets are non-custodial (in sellers' own buckets), not ours to back up. Per Max, these are OUT OF SCOPE for the S3 bucket (row 4 updated). Remaining S3 gaps: Cloudflare (Worker KV/DNS) and an S3 git mirror; code is durable in GitHub + local clones.


### 2026-06-08 (S799.w): Cloudflare DR export LIVE
Nightly Cloudflare export to S3 (`cloudflare/<date>/`): all DNS records (ai.market 30, vectoraiz.com 8) + zone settings, via `scripts/cloudflare_export.py` wrapped by `run_cloudflare_export.sh` (machine-identity) under launchd `com.aimarket.cloudflare-export` (04:30/05:30 local, per-UTC-day lock). Watchdog extended to `cloudflare/`. Worker SCRIPTS are not exported (source in GitHub). Worker KV is not captured — the current token lacks KV scope and KV holds only regenerable dead-man-switch counters; mint a KV-read token if KV capture is later wanted. This closes the last S3 coverage gap; the only item still not in S3 is an S3 git mirror (code is durable in GitHub + local clones).

## Reading the Login Items "bash" list (Titan-1 launchd agents)

macOS System Settings → General → Login Items & Extensions → "Allow in the Background" labels each job by the program it launches. Our scheduled jobs launch via `/bin/bash <script>`, so they ALL show as identical "bash — unidentified developer" rows. They are NOT duplicates — each runs a different script. The 10 bash background items on Titan-1 (`~/Library/LaunchAgents/`), oldest first:

| launchd label | script | purpose | added |
|---|---|---|---|
| com.koskadeux.mcp | launch_mcp_server.sh | Koskadeux MCP gateway launcher | 2026-02-02 |
| com.aimarket.daily-stats | run_daily_stats.sh | daily stats job | 2026-02-11 |
| com.koskadeux.ag_server | launch_ag_server.sh | AG (Gemini) model server | 2026-03-04 |
| com.koskadeux.deepseek_server | launch_deepseek_server.sh | DeepSeek model server | 2026-04-29 |
| com.koskadeux.infisical-token-refresh | bash -lc | Infisical token refresh | 2026-06-03 |
| com.aimarket.s3-backup-watchdog | s3_backup_watchdog.sh | S3 backup freshness alarm (Telegram) | 2026-06-07 |
| com.aimarket.pg-backup | run_pg_backup.sh | nightly main-DB backup → S3 — **DISABLED S884** (migrated to Railway cron `ai-market-backup`; plist kept for revert) | 2026-06-07 |
| com.aimarket.qdrant-backup | run_qdrant_backup.sh | nightly Qdrant backup → S3 | 2026-06-07 |
| com.aimarket.railway-config-export | run_railway_config_export.sh | nightly Railway topology export → S3 | 2026-06-08 |
| com.aimarket.cloudflare-export | run_cloudflare_export.sh | nightly Cloudflare DNS export → S3 | 2026-06-08 |

Other background items (gateway, council-hall, cloudflared, lilly, etc.) launch via python/cloudflared and show under those names, not "bash". The macOS "App Background Activity: 'bash' can run in the background" notification fires when one of these is added or re-registered (and can lag by hours); the recent additions are the backup jobs above — the newest being the Cloudflare export (2026-06-08). The Background Task Management DB lists each of ours exactly once (no duplicates). Stale plist backups removed S799.w: `com.aimarket.pg-backup.plist.bak-preMI`, `com.koskadeux.council-hall.plist.pre-infisical-S546`, `com.koskadeux.gateway.plist.pre-infisical-S546`.


## 2026-06-24 (S1014, Mars): legacy GCS backup workflow deleted + verifier write-only-key fix

Triggered by daily 'Automated Backups: All jobs have failed' emails + allAI Telegram alerts. Root-caused to TWO doc/reality gaps this runbook carried (both now corrected in §C/§D):

1. **`backup.yml` ('Automated Backups') was NOT actually disabled in S794.** It kept running on its 03:00 cron and 404ing against the deleted GCS bucket `gs://aimarket-backups`, emailing Max and paging via the allAI Telegram bot. **Deleted from ai-market-backend `main` in S1014** (commit cb149908, git push — not gh api, which lacks the `workflow` scope). No live backup path affected: real backups (main PG + Qdrant + Infisical secrets) land in S3 `aimarket-backups-prod` nightly and were verified green this session (`infra:backup-health`: ai-market-pg ok 4.08 GB toc 2275 @ 02:00 UTC; infisical-secrets-pg ok).

2. **`backup-verify.yml` ('Backup Staleness Check') is STILL LIVE** (also wrongly marked disabled S794). Left in place — it is a legitimate secondary dead-man's-switch. Its accuracy depended on the SysAdmin/backend verifier reading S3 truthfully, which it could not:

3. **Verifier false 'corrupt' fixed (commit d32ec1bc).** `app/allai/agents/sysadmin/backup_monitor.py::_evaluate_s3_backup` built its S3 client from the backup-writer key (`AWS_BACKUP_WRITER_*`), which is deliberately PutObject+ListBucket only (no s3:GetObject, per §C/§H invariant 2 — a stolen writer key must not be able to read/exfiltrate backups). It then called `head_object()` (needs GetObject) → AccessDenied/403 → marked the backup `status='corrupt'`, so backup-health read RED while backups were fine. Path-1 fix (honor the write-only design, grant NO new read access): an AccessDenied/403/Forbidden HeadObject is now treated as `metadata_verification='skipped_no_read_grant'` (sha256=None), not corrupt — presence/freshness/size come from ListBucket, and the write-time sha256 is recorded in `infra:backup-health` by the job. Non-permission HeadObject errors still flag corrupt; empty-object and stale-age checks unchanged. Reviewed by MP (Codex): APPROVE. Tests: `tests/test_backup_s3_watchdog.py` 8/8 incl. 2 new regression tests.

**Still open after S1014:** (a) `QDRANT_API_KEY` not set in the backend service env — the live-Qdrant collection cross-check degrades to the S3-historical-prefix fallback (non-fatal; S3 freshness alarming unaffected). Wire from Infisical when convenient. (b) DONE (S1014, commit dfd53cfd): deleted the four latent dead GCS scripts/dirs (`scripts/backup_all.py`, `scripts/backup_local.py`, `scripts/backup_qdrant.sh`, `services/backup/`) after verifying no Python importers and no Railway service deploying from `services/backup`. (c) `infra:backup-health` heartbeat tracks only ai-market-pg + infisical-secrets-pg; Qdrant freshness is covered by the launchd watchdog but not the heartbeat (`qdrant_sync_status=pending`).
