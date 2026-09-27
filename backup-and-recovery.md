---
title: Backup & Recovery — ai.market
owner: Vulcan-Primary / Mars-Worker
last_verified: '2026-09-27'
aliases: []
error_signatures: []
---

# Backup & Recovery — ai.market

> Current backup evidence, restore limits, and recovery steps. A backup object or isolated component restore does not prove application recovery. Destination/identity specifics: [aws-s3.md](./aws-s3.md). Secret locations: [infisical-secrets.md](./infisical-secrets.md). Recovery map: [disaster-recovery.md](./disaster-recovery.md). Architecture rationale: `BQ-AI-MARKET-COMPLETE-BACKUP-ARCHITECTURE-TITAN1-CENTRIC-S681`.

## Overview
- **system_name:** backup-and-recovery
- **purpose_sentence:** Record observed backup coverage, alerting, tested component restores, and the remaining work before ai.market application recovery can be claimed.
- **owner_agent:** Vulcan-Primary / Mars-Worker
- **escalation_contact:** Max (Telegram, primary)
- **lifecycle_ref:** Maintenance
- **authoritative_scope:** Backup coverage, cadence, integrity verification, failure alerting, and per-component restore. Bucket lockdown + writer identity inherit from aws-s3.md.
- **last_verified:** 2026-09-27 (S1754 controller ground-truth audit; component evidence and limits below). The 2026-08-25 S1605 check remains in the dated incident history.

## Capabilities
> **Current position, 2026-09-27:** S3 objects, hashes, archive listings, isolated restores, role repair, and application recovery are separate checks. The bucket's observed versioning, 35-day COMPLIANCE Object Lock, and AES256 encryption preserve retention for objects stored there; they do not establish coverage or recoverability for every system. The June 2026 GCS retirement and S3 migration notes below are historical. The owner excludes our own AIM Data/vectorAIz data from S3; do not override that decision.

| # | Component | Why it matters | Backup method (target) | Evidence and limit, 2026-09-27 | Restore ref |
|---|---|---|---|---|---|
| 1 | **ai.market Postgres** (marketplace + Living State + dispatch ledger) | Core platform + dev/build state | nightly `pg_dump@17 -Fc` -> S3 `postgres/ai-market/<date>/` | Sep 27 dump: 1,416,413,526 bytes, SHA256 `1bc0d09d507ecb7e8e37090292f794df1a26a5edeff2be46c17415abe23d5ddb`. Full isolated PG17 restore exited 0 with 378 tables. Ownership and ACLs were excluded; no application recovery proven. | How to operate-R2 |
| 2 | **ai.market Qdrant** (six collections) | Search and allAI indexes | collection snapshots -> S3 `qdrant/<collection>/<date>/` | All six Sep 27 snapshots downloaded, hash-verified, and restored in isolated no-network Qdrant v1.18.2 containers: `action_logs`, `aim_tools`, `data_requests`, `knowledge_base`, `knowledge_base_v2`, `listings`. Live aliases: 0. Point counts/config matched except `listings` live 59 vs snapshot 60; cause unproven. No payload inspection or application recovery. | How to operate-R7 |
| 3 | **Infisical Postgres** (secrets, root of trust) | Without secrets nothing authenticates/deploys | Railway scheduled age-encrypted dump -> S3 `postgres/infisical/<date>/` | Fresh encrypted backup observed. Full decrypt/restore is blocked pending sanctioned offline age, master, and recovery keys. June 8 historical TOC listing (1,209 tables) was not a full restore. Backup predates new signing keys. | How to operate-R3 |
| 4 | **vectorAIz + AIM Data (our own)** | Our own second-surface data | local Titan-1 coverage; S3 excluded by owner | Keep this data. Owner excludes our own AIM Data from S3 (S799); do not expand S3 scope. `Docker.raw` is excluded by Time Machine, and independent Docker volume export/restore proof is absent for both peers (#6552/#6553). Dev/e2e recovery belief is unverified. | Titan-1 backup |
| 5 | **Source code** (all `aidotmarket/*` repos) | App, specs, history | GitHub and local clones; S3 `git-mirrors/` proposed | GitHub/local copies are observed recovery sources; an S3 mirror and complete application rebuild are not proven. | How to operate-R4 |
| 6 | **Railway deploy config** | Services, wiring, secret references | topology export -> S3 `railway-config/<date>/` | Names-only topology export observed. It does not recover variable secret values or prove redeployment. | How to operate-R5 |
| 7 | **Cloudflare** | Edge routing and data | DNS/zone/KV exports -> S3 `cloudflare/<date>/` | DNS and KV exports observed. D1/R2 inventory is incomplete because of permissions; this is not proof of absence. Worker source coverage is unproven. | How to operate-R6 |
| 8 | **Failure alerting** | Detect missed backups | S3 freshness watchdog -> Telegram; secondary GitHub issue | T876 restored the missing backup schedule. The claimed two-hour timezone alarm error is unsupported by the same-object check below. Per-collection Qdrant checks and current Telegram delivery remain unproven. GitHub secondary threshold is 26h. | When it breaks |

**Restore-from-S3-alone:** unproven and incomplete. The Sep 27 main PostgreSQL and six Qdrant component restores are bounded evidence; they do not include Infisical decrypt/restore, all role credentials, local Docker volumes, Cloudflare inventory, Railway secret values, or application recovery. Do not call the market DR-complete or guarantee data safety from bucket retention alone.

## Architecture & interactions
- **Primary destination:** S3 `aimarket-backups-prod` — eu-north-1, acct `948749907373`. Sep 27 evidence confirms bucket versioning, **Object Lock COMPLIANCE / 35-day**, and AES256 encryption for stored objects; see [aws-s3.md](./aws-s3.md) for bucket controls. These controls preserve retained objects but cannot cover data that was never exported. Layout includes `postgres/ai-market/<date>/`, `postgres/infisical/<date>/`, and `qdrant/<collection>/<date>/`.
- **Write identity:** IAM `aimarket-backup-writer`, policy `backup-write-only` (PutObject + ListBucket only). Creds in Infisical `ai-market-backend` prod (`AWS_BACKUP_WRITER_ACCESS_KEY_ID` / `_SECRET`). Manual ops use `aws --profile aimarket` (svc-titan-vulcan).
- **Legacy destination (RETIRED 2026-06-07, S795; writer + dead code DELETED 2026-06-24, S1014):** GCS `gs://aimarket-backups` (GCP project `aimarket-prod`) has been **deleted**. Its writer, GitHub Actions `backup.yml`, was *believed* disabled in S794 but in fact kept running on its 03:00 cron and 404ing against the deleted bucket daily (false 'backup failed' email + Telegram) until it was **deleted from the repo in S1014** (commit cb149908). The latent GCS code it relied on was also deleted in S1014 (commit dfd53cfd): `scripts/backup_all.py`, `scripts/backup_local.py`, `scripts/backup_qdrant.sh`, and the `services/backup/` 'Unified Backup Service' dir (no importers; no Railway service deployed from it). Live S3 scripts `scripts/backup_pg.py` + `scripts/backup_qdrant_s3.py` retained.
- **Tiers (S681 target):** (1) Railway-native PITR per Postgres; (2) immutable S3 (this bucket); (3) Time Machine on Titan-1; (4) Backblaze offsite. These are architectural targets, not proof of independent recovery. In particular, Time Machine excludes `Docker.raw`; no independent Docker volume export/restore proof was available for #6552/#6553 on Sep 27.

## Agent capabilities
| Mechanism | Where | Schedule | Does | Status |
|---|---|---|---|---|
| GitHub Actions `Automated Backups` (`backup.yml`) | aidotmarket/ai-market-backend | (was) daily 03:00 UTC + dispatch | `pg_dump` + Qdrant snapshot -> **GCS**; opened a GitHub issue on failure | **DELETED (S1014, commit cb149908)** — was NEVER effectively disabled despite the S794 note; kept firing daily and 404ing on the deleted GCS bucket. Removed from the repo. |
| GitHub Actions `Backup Staleness Check` (`backup-verify.yml`) | same | daily 06:00 UTC + dispatch | hits `/api/v1/internal/backup-status`; opens a GitHub issue if PG/Qdrant > 26h stale (one missed nightly; was 6h until S1530 — see 2026-08-12 note) | **LIVE (still active as of S1014 — the S794 'disabled' note was WRONG).** Legitimate secondary dead-man's-switch; accuracy depends on the backend `backup-status` / SysAdmin verifier reading S3 truthfully (S1014 write-only-key HeadObject fix). |
| Railway cron `ai-market-backup` (`backup_pg.py`, `Dockerfile.ai-market-backup`, config `railway.ai-market-backup.json`) | Railway (ai-market project) | 02:00 UTC nightly (restart NEVER) | `pg_dump@17 -Fc` -> **S3** `postgres/ai-market/<date>/` + health record; DB via `AUTHOR_DISPATCH_DATABASE_URL`, S3 via `${{ai-market-backend.AWS_BACKUP_WRITER_*}}` | **LIVE (S884)** — migrated off Titan-1 (launchd `com.aimarket.pg-backup` now disabled); manual run verified 3.31 GB dump, ~8 min. **T876:** PR508 merged at `20eb5d72951c3569ef98c1d624532d7d60fddc41`; exact-commit backup `51983f16` and backend `76a0b18c` deployments succeeded. Effective backup manifest has four `watchPaths`; cron is 02:00 UTC, restart NEVER. Dashboard `watchPatterns: []` is not the effective config. A genuine unrelated-release negative match is still pending; ticket remains in progress. **Heartbeat (S909, T-2026-000021 RESOLVED):** the run writes the `infra:backup-health` heartbeat with real `sha256`/`toc_entries` and is now **fail-loud** — see E-01a. |
| Railway secrets backup (`backup_pg.py`, config `railway.infisical-backup.json`) | Railway (infisical secrets project; historical service-name correction below) | 03:00 UTC nightly | `pg_dump`@18 -> age-encrypt -> **S3** `postgres/infisical/<date>/` via write-only key | Fresh encrypted object observed Sep 27; full decrypt/restore awaits sanctioned offline keys. The S797 TOC listing was a format check only. |
| **launchd `com.aimarket.qdrant-backup`** (`run_qdrant_backup.sh` -> `backup_qdrant.py`) | Titan-1 | 02:30/03:30 Europe/Berlin (per-UTC-day lock) | collection snapshots -> **S3** `qdrant/<collection>/<date>/` | Six Sep 27 snapshots passed isolated restore; see row 2. A top-level `qdrant/` freshness check does not prove each collection is present. |
| **launchd `com.aimarket.s3-backup-watchdog`** (`runbooks/scripts/s3_backup_watchdog.sh`) | Titan-1 | every 6h + RunAtLoad | checks S3 object freshness; Telegram alert path | Historical operation is documented below. A draft forces `TZ=UTC` but is unmerged and uninstalled: 12 mocked tests pass; DeepSeek says REVISE because it falsely requires retired collections, with other reviews pending. Current per-collection checks and Telegram delivery remain unproven. |
| ~~Manual GCS->S3 copy~~ | — | — | — | **OBSOLETE (S795)** — GCS retired; nightly direct-to-S3 jobs supersede this |

## How to operate
**E-01 — Take an immediate S3 backup of the main DB now.** Trigger the Railway `ai-market-backup` cron service on demand: Railway dashboard -> ai-market project -> `ai-market-backup` -> **Run now** (API equiv: `deploymentInstanceExecutionCreate(serviceInstanceId)`), then confirm a fresh object via How to operate-03. It dumps over `AUTHOR_DISPATCH_DATABASE_URL` and writes straight to S3 with the backup-writer key. (Legacy Titan-1 `launchctl kickstart com.aimarket.pg-backup` is retired/disabled S884; plist preserved for emergency revert per How to operate-04.)
**E-01a — Backup heartbeat env dependency (S909, T-2026-000021).** The `ai-market-backup` service MUST have `INTERNAL_API_KEY` (= backend internal key; Infisical project `ai-market-backend`) and `RAILWAY_BACKEND_URL` (= `https://ai-market-backend-production.up.railway.app`) set — they drive the `infra:backup-health` Living State heartbeat. Set S909 (previously absent, which silently skipped the heartbeat, froze it >26h, and fired a **false-positive P0** — incident a53ada1d). The heartbeat is now **fail-loud**: on a successful dump the S3 object always uploads first, then if the heartbeat cannot be written the run logs an S3 health record `status=failed` `stage=living_state_heartbeat` and **exits 10** instead of skipping. Service id `53aa2e80-8ffa-4e22-a38f-f52a6b6c6c80`, instance `2307844d-5fac-4342-8ec2-afdf92219d91`. Verified S909: on-demand run wrote heartbeat `status=ok` sha256 `be78a33a…` toc 2271.
**E-02 — (retired).** The GCS recurring workflow was deleted in S1014 after the S795 bucket deletion. The main DB is backed up by Railway cron; other jobs are listed under Agent capabilities. See E-01 for an on-demand main-DB run.
**E-03 — Verify a backup landed.** `aws s3 ls s3://aimarket-backups-prod/postgres/ai-market/ --recursive --profile aimarket | tail` shows object presence and size. A matching hash and `pg_restore --list` check integrity/format only. Record a full isolated restore result separately, including table count, exit code, excluded owner/ACL material, and any application checks.
**E-04 — Emergency revert to the Titan-1 job** (only if the Railway `ai-market-backup` cron is broken): the launchd plist is preserved at `~/Library/LaunchAgents/com.aimarket.pg-backup.plist` (disabled S884). Re-enable: `launchctl enable gui/$(id -u)/com.aimarket.pg-backup && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aimarket.pg-backup.plist`, then kickstart it. Prefer fixing the Railway service first.

## How to operate-R. Restore the market (ordered: secrets -> infra -> data -> code -> edge)
- **R1 Pre-flight:** scope the failure (one component vs total loss). Confirm sanctioned offline age, Infisical master/recovery, and S3 read access without exposing key material. Identify required role credentials and source revisions. Preserve local AIM Data/vectorAIz knowledge and establish a separate Docker volume recovery path.
- **R2 ai.market PG:** provision an isolated PG17 instance and restore the chosen `postgres/ai-market/<date>/` dump. The Sep 27 full isolated restore exited 0 with 378 tables. The dump excluded ownership/ACLs; restore the required role matrix separately. The bounded issue-channel/audit ACL helper at `3bd8ac262eae54f48411306dd5347f23d34cb9b7` passed 16 tests plus isolated idempotency, default ACL, and forced rollback checks. **Do not use it as an accepted recovery step:** PR509 is blocked by DS REVISE / GLM APPROVE_WITH_MANDATES pending reviewed application `SET ROLE` reachability checks. A controller's isolated PG17 synthetic watcher membership (`INHERIT FALSE`, `SET TRUE`) showed the helper succeeding while `pg_has_role(..., 'SET')` was true and direct `SELECT` was false; the membership was removed and scratch ACL restored afterward. The helper does not restore all roles/passwords or prove application recovery.
- **R3 Infisical PG:** nightly Railway cron writes an **age-encrypted** custom-format dump to `postgres/infisical/<date>/railway-<ts>.dump.age`. A sanctioned operator must obtain the offline age and Infisical master/recovery keys, decrypt the chosen object, fully restore it with a matching Postgres client, and validate Infisical and dependent signing keys. The June 8 S797 decrypt plus `pg_restore -l` listed 6,994 TOC entries / 1,209 tables; it did **not** execute a full restore. The fresh Sep 27 encrypted backup has not passed full decrypt/restore, and it predates new signing keys.
- **R4 Source:** retrieve the exact required revisions from GitHub or independently verified mirrors; the S3 `git-mirrors/` target is not established as complete.
- **R5 Railway infra:** use `railway-config/<date>/` as a topology and variable-name guide, then recover secret values through the approved secret recovery path and verify each service before deployment. The export alone cannot recreate credentials.
- **R6 Cloudflare:** verify Worker source and the actual DNS/KV/D1/R2 inventory before restoring edge state. DNS/KV exports are observed; D1/R2 permissions prevented a complete inventory. Do not infer absence or source coverage.
- **R7 Data:** restore all six Qdrant collections from their `qdrant/<collection>/` snapshots or rebuild indexes from verified source data. Sep 27 isolated snapshots restored in Qdrant v1.18.2; `listings` count differed (live 59, snapshot 60), with cause unproven. Preserve our own local AIM Data/vectorAIz knowledge and plan separate Docker volume recovery; do not move it to S3 without an owner decision.
- **R8 Validate:** check identities, roles, credentials, listings/orders, Living State, signing, search, and dependent application paths in the restored environment. Component restore success alone is insufficient.

## When it breaks

**When it breaks-02 — (retired S884).** The dual-Berlin-slot launchd failure mode no longer applies: the main-DB backup is a single Railway cron at 02:00 UTC (restart NEVER), not the back-to-back 01:00/02:00 Berlin launchd slots. The 2026-06-10 transient mid-dump disconnect is mitigated by running inside Railway. CAVEAT: the Railway run still connects over the public proxy (`AUTHOR_DISPATCH_DATABASE_URL`); pointing it at the internal DB host would cut runtime/exposure further (optional). S884 FINDING: Railway's own `Postgres`-service and project-shared `DATABASE_URL` vars are STALE — they do not authenticate; the only working main-DB credential is Infisical `AUTHOR_DISPATCH_DATABASE_URL`. Do not trust the Railway-native DB URLs for restore/ops; separate cleanup advised.
**This is the answer to "tell me when a backup does not run."**
- **What:** `com.aimarket.s3-backup-watchdog` runs `runbooks/scripts/s3_backup_watchdog.sh` every 6 hours (and at load).
- **Check:** the checked-in script lists five prefixes: `postgres/ai-market/`, `postgres/infisical/`, `qdrant/`, `railway-config/`, and `cloudflare/`. It compares their newest object to a 26h threshold. AWS CLI 2.34.62 `aws s3 ls` renders local time: a direct HeadObject at 10:32:24Z appeared as 10:32:24 in UTC and 12:32:24 in Madrid. The older local-time producer and local BSD date parser did not prove a two-hour alarm error. The current script still does not check each Qdrant collection, and Telegram response/delivery is unconfirmed. The draft `TZ=UTC` fix is not installed; its retired-collection requirement needs correction and review.
- **Alert path:** direct HTTPS POST to `https://api.telegram.org/bot<token>/sendMessage` -> bot **koskadeux_bot** -> Max's chat. Creds `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` read from `koskadeux-mcp/.env`. No Infisical dependency (deliberate — the alerter must work even when Infisical is the thing that's broken).
- **Historically verified:** a 2026-06-07 test ping delivered (message_id 1639) to chat 80805807. This does not prove Sep 27 alert delivery.
- **Secondary alert:** the GitHub `Backup Staleness Check` (`backup-verify.yml`) opens an urgent GitHub issue (email) if the backend-reported PG/Qdrant backups go > 26h stale. As of S1081 it reads the **S3-canonical** status from `GET /backup-status` (not the now-defunct Redis `backup:last` events that the deleted `backup.yml` used to write), so its June-2026 false-positive class is closed. S1530 (2026-08-12) closed a second false-positive class: the former 6h staleness window was shorter than the gap between the ~00:30 UTC qdrant snapshot and the check's actual 06:30–08:30 UTC run (GitHub cron drift), which filed a false GitHub issue daily from 12 Jul to 12 Aug (#218–#250, all closed). Window is now 26h = one missed nightly, matching the primary watchdog (commit 58a3580b3 in ai-market-backend). Backups themselves were verified continuous against S3 object timestamps; the only genuine outage in that period was postgres 19–20 Jul, which the primary Telegram watchdog caught (8 ALERT lines) and which recovered 21 Jul.
- **2026-08-25 incident #280:** the secondary check timed out after five minutes against `/api/v1/internal/backup-status` while the backend was on the earlier KMS transport deployment; it opened a backup-staleness issue even though direct S3 truth showed Postgres at 02:05 UTC and Qdrant at 00:37 UTC, both fresh. After the KMS REST transport repair was deployed, the unchanged workflow rerun `32899073668` completed in 9 seconds and skipped issue creation. Treat an `endpoint unreachable` issue as an availability-path alert until How to operate-03 proves actual staleness; do not trigger an extra backup merely from that label.
- **Log:** `~/Library/Logs/aimarket_s3_backup_watchdog.log` (one `OK`/`ALERT` line per run).
- **Verify:** compare the same object's HeadObject time with `aws s3 ls` under the actual timezone, check each current Qdrant collection, and confirm Telegram receipt under authorized operational controls. A local `OK` log line alone does not prove delivery.

| ID | Symptom | Cause | Verify | Repair |
|---|---|---|---|---|
| F-01 | No fresh S3 object today | nightly job not running (e.g. Infisical login expired — the 2026-05-29 class) | watchdog ALERT in log + Telegram; `aws s3 ls` shows no today prefix | Changes and maintenance-1 revive job; meanwhile How to operate-01 |
| F-02 | Dump present but tiny | empty/partial dump | size vs prior day; `pg_restore --list` TOC drop | re-run; fix source; halt rotation so a good copy isn't pruned |
| F-03 | No Telegram alert despite stale | watchdog not loaded / Telegram creds rotated | `launchctl list | grep s3-backup-watchdog`; check `.env` creds | reload plist; refresh creds in `koskadeux-mcp/.env` |
| F-04 | Can't decrypt a restored backup | wrong/lost key | key id vs object | retrieve offline copy |

## Repair
- **G-01** Re-establish the schedule + alert so a silent failure can't persist (root-cause class: jobs that fail without paging). 
- **G-02** Re-run the dump; fix source connectivity; halt local rotation so a good prior copy isn't aged out.
- **G-03** Retrieve the offline key/paper copy; never store the only copy on Titan-1.

## Changes and maintenance
1. **Automated jobs authenticate to Infisical with a MACHINE IDENTITY (Universal Auth client-id/secret or access token) — NEVER interactive `infisical login`.** Interactive sessions expire and then fail silently into a login prompt — the exact cause of the 2026-05-29 backup death and the recurring "Infisical keeps bothering me" pain. Machine-identity tokens are non-interactive and renewable. This is the keystone that unblocks rows 1–4 to S3.
2. **Immutability:** the S3 bucket stays Object Lock COMPLIANCE — never weaken to Governance; never give the writer key Delete/Bypass.
3. **The alerter must not depend on Infisical** (it reads Telegram creds from `.env`) — so it still pages even when Infisical is down.
4. **Back up Infisical's own DB to S3** (row 3) — the root of trust must be recoverable; keep the master key offline.
5. **Record each proof at its actual level.** GCS was retired 2026-06-07 after S3 object and archive-TOC checks; the TOC check was not a full restore. Sep 27 added full isolated main-PG and six Qdrant component restores. Infisical full decrypt/restore, local Docker volumes, credentials, and application recovery remain unproven. Our own AIM Data/vectorAIz remains excluded from S3 by owner decision.
- Change classes — BREAKING: weakening Object Lock; writer delete/bypass; exposing the secrets DB publicly; an Infisical consumer reverting to interactive login. REVIEW: new source; retention change; run-location change. SAFE: add a source per pattern; tagging; a verification check.

## Acceptance criteria
1. (E) "Take a backup now." -> E-01.  2. (E) "Confirm last night landed." -> E-03, with presence distinct from restore proof.  3. (R) "Main DB lost." -> R2 plus roles/credentials and application validation.  4. (R) "Total loss." -> R1→R8 is an ordered plan with open gates, not a proven S3-only rebuild.  5. (F) "A backup didn't run." -> inspect both watchdog and GitHub secondary checks, including delivery and per-collection gaps.  6. (F) "Dump suspiciously small." -> F-02.  7. (H) "Switch bucket to Governance." -> BREAKING, refuse.  8. (R) "Restore but key is gone." -> G-03.  9. (E) "Back up the secrets DB." -> in-Railway encrypted dump; full restore remains open.  10. (H) "Why did Infisical break backups?" -> historical interactive login expiry in Changes and maintenance-1.

## Maintenance
- **last_refresh_session:** S1754 central runbook correction; historical S799.w and S795 notes retained below with present-day limits stated above.
- **last_refresh_date:** 2026-09-27
- **owner_agent:** Vulcan-Primary / Mars-Worker
- **refresh_triggers:** a coverage row goes LIVE to S3; machine identity created; GCS retired; restore drill; incident
- **scheduled_cadence:** 90 days

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

Triggered by daily 'Automated Backups: All jobs have failed' emails + allAI Telegram alerts. Root-caused to TWO doc/reality gaps this runbook carried (both now corrected in Architecture & interactions/Agent capabilities):

1. **`backup.yml` ('Automated Backups') was NOT actually disabled in S794.** It kept running on its 03:00 cron and 404ing against the deleted GCS bucket `gs://aimarket-backups`, emailing Max and paging via the allAI Telegram bot. **Deleted from ai-market-backend `main` in S1014** (commit cb149908, git push — not gh api, which lacks the `workflow` scope). No live backup path affected: real backups (main PG + Qdrant + Infisical secrets) land in S3 `aimarket-backups-prod` nightly and were verified green this session (`infra:backup-health`: ai-market-pg ok 4.08 GB toc 2275 @ 02:00 UTC; infisical-secrets-pg ok).

2. **`backup-verify.yml` ('Backup Staleness Check') is STILL LIVE** (also wrongly marked disabled S794). Left in place — it is a legitimate secondary dead-man's-switch. Its accuracy depended on the SysAdmin/backend verifier reading S3 truthfully, which it could not:

3. **Verifier false 'corrupt' fixed (commit d32ec1bc).** `app/allai/agents/sysadmin/backup_monitor.py::_evaluate_s3_backup` built its S3 client from the backup-writer key (`AWS_BACKUP_WRITER_*`), which is deliberately PutObject+ListBucket only (no s3:GetObject, per Architecture & interactions/Changes and maintenance invariant 2 — a stolen writer key must not be able to read/exfiltrate backups). It then called `head_object()` (needs GetObject) → AccessDenied/403 → marked the backup `status='corrupt'`, so backup-health read RED while backups were fine. Path-1 fix (honor the write-only design, grant NO new read access): an AccessDenied/403/Forbidden HeadObject is now treated as `metadata_verification='skipped_no_read_grant'` (sha256=None), not corrupt — presence/freshness/size come from ListBucket, and the write-time sha256 is recorded in `infra:backup-health` by the job. Non-permission HeadObject errors still flag corrupt; empty-object and stale-age checks unchanged. Reviewed by MP (Codex): APPROVE. Tests: `tests/test_backup_s3_watchdog.py` 8/8 incl. 2 new regression tests.

**Still open after S1014:** (a) `QDRANT_API_KEY` not set in the backend service env — the live-Qdrant collection cross-check degrades to the S3-historical-prefix fallback (non-fatal; S3 freshness alarming unaffected). Wire from Infisical when convenient. (b) DONE (S1014, commit dfd53cfd): deleted the four latent dead GCS scripts/dirs (`scripts/backup_all.py`, `scripts/backup_local.py`, `scripts/backup_qdrant.sh`, `services/backup/`) after verifying no Python importers and no Railway service deploying from `services/backup`. (c) `infra:backup-health` heartbeat tracks only ai-market-pg + infisical-secrets-pg; Qdrant freshness is covered by the launchd watchdog but not the heartbeat (`qdrant_sync_status=pending`).

## 2026-06-30 (S1081, Mars): backup status board now reads S3-canonical — false "failing since June 24" fixed

Symptom: SysAdmin `daily_health_report` repeatedly told Max "backups failing since June 24" while real backups were current (watchdog: all five S3 targets fresh, dated same-day).

Root cause (verified against ground truth; corrects an earlier hypothesis that blamed two stale `~/Library/Logs` files — those are NOT in the code path and were archived this session): the `backup.yml` workflow deleted 2026-06-24 (S1014, commit cb149908) was the ONLY writer of `POST /api/v1/internal/backup-event`, which populates Redis `backup:last:{postgres,qdrant}`. Real backups had already moved to the local launchd jobs, which do not POST that event. So the Redis snapshot froze on its last write (June 24). `GET /api/v1/internal/backup-status` read that frozen snapshot as authoritative for freshness, and BOTH consumers inherited the false signal: the `daily_health_report` skill (Max-facing) and `backup-verify.yml` (the When it breaks secondary GitHub-issue dead-man's-switch).

Fix (commit 63fa4f17, Gate-3: DeepSeek APPROVE + GLM APPROVE_WITH_NITS): `GET /backup-status` now derives postgres+qdrant freshness from the S3-canonical signal — the same S3 object ages the launchd watchdog trusts — via a new side-effect-free `BackupVerificationMonitor.get_s3_backup_status()`. Redis is demoted to optional history only; the endpoint no longer hard-fails when Redis is down. Response contract (`available`, `targets[t].timestamp/status/last_backup_age_hours`) preserved so `backup-verify.yml` age math is unchanged. Scope: postgres+qdrant only, observability-only, no schema/IAM/backup-job changes; the write-only-key invariant (Architecture & interactions/Changes and maintenance-2) is untouched (freshness from ListBucket, never GetObject).

Noted follow-ups (non-blocking, not done here): (a) `get_s3_backup_status` runs sync boto3 calls inside an async method — same pattern as the existing `run_check`; wrap in `asyncio.to_thread` if the internal endpoint ever sees concurrent load. (b) Extend the status board to the other three watchdog targets (infisical-secrets, railway-config, cloudflare) so the board matches the watchdog's full coverage. (c) The When it breaks "secondary alert" (`backup-verify.yml`) now reads the S3-canonical signal, so its prior false-positive class is closed.


## Issue-channel schema restores (pointer, S1624)

Dumps taken with `--no-owner --no-privileges` carry no ACLs or default privileges.
The S1624 receipt's `restore_roles_step_v3.py` instruction refers to a hardcoded
pinned backend checkout that is no longer available; it is historical evidence,
not a currently executable recovery command (see
[issue-channel-gate2-receipts.md](./issue-channel-gate2-receipts.md), "S1624 corrective rounds 2-3"). The older
hand-copied `restore_roles_step.sql`/`_v2.sql` are historical and must not be used:
v2 demonstrably leaves the watcher read-only on a clean restore. The newer
`3bd8ac262eae54f48411306dd5347f23d34cb9b7` helper is also blocked as an
accepted recovery step pending reviewed application `SET ROLE` reachability checks.

## 2026-09-27 (S1754): ground-truth correction

The earlier dated entries record what was claimed or checked at that time; they must not be read as proof of a complete restore today. In particular, June 8 Infisical `pg_restore -l` was a TOC listing, and June 7 main-PG archive checks were not full restores. Sep 27 main PG and six Qdrant collections passed isolated component restores as described in Capabilities. No restored ai.market application was exercised end to end.

The pinned issue-channel/audit ACL helper commit `3bd8ac262eae54f48411306dd5347f23d34cb9b7` retains its bounded test and isolated rollback evidence, but PR509 is blocked by DS REVISE / GLM APPROVE_WITH_MANDATES. The isolated PG17 synthetic watcher membership exposed missing application `SET ROLE` reachability checks despite helper success; the scratch membership and ACL were restored after the probe. Do not use the helper as accepted recovery until the correction is reviewed. It cannot supply every role/password or recover the application. Infisical requires sanctioned offline keys; the fresh encrypted backup predates new signing keys. Cloudflare D1/R2 inventory, Worker source, Railway secret values, local Docker volumes, and current watchdog per-collection checks and Telegram delivery remain open. The same-object AWS CLI check did not support the claimed two-hour timezone error; the draft UTC change is unmerged and uninstalled. T876 restored the backup schedule with exact-commit deployments, but its unrelated-release negative match remains pending, so the ticket is still in progress. The GitHub secondary check uses 26h, not 6h.

The S3 copy `RESTORE-README.md` was observed stale at June 8, SHA256 beginning `595282`; this edited repository map has **not** been synced to S3. Map sync is pending and must be handled under separate authority. Existing bucket versioning, 35-day COMPLIANCE retention, and AES256 encryption remain observed; they do not close these recovery gaps.
