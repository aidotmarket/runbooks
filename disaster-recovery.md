---
title: Disaster Recovery — ai.market (what is in S3 and how to rebuild)
owner: unassigned
last_verified: '2026-09-27'
aliases: []
error_signatures: []
---

# Disaster Recovery — ai.market (what is in S3 and how to rebuild)

> This repository file is the current map; [backup-and-recovery.md](./backup-and-recovery.md) has the operational detail. The S3 `RESTORE-README.md` copy was still the June 8 version (SHA256 beginning `595282`) on Sep 27. Sync is pending; do not rely on that copy for current recovery limits.

## 0. Before you can restore anything — offline bootstrap items
Confirm sanctioned access to the required offline materials before a recovery drill or incident. Their availability has not been established by an S3 object listing:
- **age private key** — decrypts the Infisical secrets dump. Existing offline custody policy is **1Password only**; sanctioned access and actual availability remain unverified. Loss would block that dump's recovery.
- **AWS read credentials** for `aimarket-backups-prod` (eu-north-1, account 948749907373) to GET objects. The backup *writer* key is write+list-only and cannot read or delete.
- **Infisical master/recovery keys** — to bring Infisical and its protected data back after a full DB restore. The Sep 27 encrypted backup predates `/connector-auth` signing keys generated at 08:46:55.551161Z. Mars 6647 reports no separate key recovery copy; its connector runbook regeneration procedure is pending. Recovery of these keys is untested.
- **Service secret values and roles** — the Railway topology export records names only. The main DB dump excludes ownership/ACLs and does not supply passwords.

## 1. What was observed — `s3://aimarket-backups-prod`

Versioning, 35-day COMPLIANCE Object Lock, and AES256 encryption were observed on Sep 27. These protect stored objects within the retention window; they do not establish complete system coverage or application recovery.

| Prefix | Contents | Cadence | Restore |
|---|---|---|---|
| `postgres/ai-market/<date>/` | Main marketplace DB, `pg_dump -Fc`. Sep 27 object: 1,416,413,526 bytes, SHA256 `1bc0d09d507ecb7e8e37090292f794df1a26a5edeff2be46c17415abe23d5ddb`. | nightly schedule | R2: full isolated PG17 restore exit 0, 378 tables, no invalid indexes, including five `connector_oauth_*` tables; post-backup writes, owner/ACL, and application behavior unproven |
| `postgres/infisical/<date>/` | Fresh age-encrypted Infisical DB backup observed | nightly schedule | R1: full decrypt/restore blocked pending sanctioned offline age/master/recovery keys; historical TOC listing is not a restore |
| `qdrant/<collection>/<date>/` | Sep 27 snapshots for `action_logs`, `aim_tools`, `data_requests`, `knowledge_base`, `knowledge_base_v2`, `listings` | scheduled snapshots | R5: all six downloaded, hash-verified, isolated no-network restore in Qdrant v1.18.2; `listings` live 59 vs snapshot 60, cause unproven |
| `railway-config/<date>/` | Railway topology and variable **names**, no secret values | nightly schedule | R3: names-only map, not credential recovery |
| `cloudflare/<date>/` | DNS and KV exports observed | nightly schedule | R6: D1/R2 inventory incomplete because of permissions; Worker source coverage unproven |
| `backup-health/` | Per-source last-run status JSON | per run | — |

**Outside this bucket by owner decision:** our own AIM Data + vectorAIz knowledge on Titan-1 must be retained and must not be added to S3 without a new owner decision. `Docker.raw` is excluded by Time Machine, and neither peer has independent Docker volume export/restore proof (#6552/#6553). Dev/e2e recovery belief is unverified. Customer datasets are non-custodial in sellers' buckets. An S3 git mirror is pending; complete Worker source coverage and an application rebuild have not been proven.

## 2. Restore order — secrets, infra, data, code, edge
- **R1 Infisical secrets DB.** Under sanctioned offline-key access, decrypt the chosen `.dump.age`, perform a full restore with the matching Postgres client, then validate Infisical and dependent signing keys. The June 8 `pg_restore -l` listed 6,994 entries / 1,209 tables but did not execute a restore. No Sep 27 full decrypt/restore was authorized or proven. The latest fresh S3 object at 03:04:46Z (4,756,325 bytes) predates `/connector-auth` signing key generation at 08:46:55.551161Z. Live public JWKS SHA256 `75d3999ee3bc147a30fb444207dbcd58330266945b97ab14f545489495d2cc19` matches the public audit generation record, but does not prove a backed-up or tested recovery key. Mars 6647 reports no separate recovery copy and owns the pending connector runbook regeneration procedure.
- **R2 Main marketplace DB.** Select and hash-check a dump; restore into an isolated PG17 instance. Sep 27 full restore exited 0 with 378 tables and no invalid indexes, including `connector_oauth_clients`, `connector_oauth_codes`, `connector_oauth_grants`, `connector_oauth_refresh_tokens`, and `connector_oauth_transactions`; post-backup writes, ACLs, and application behavior remain unproven. Restore required roles, ACLs, default ACLs, and credentials separately before application use. GitHub confirms reviewed PR509 head `fd6b934296b8b3d648b0e3116d139367e8e38066` merged at 16:43:13Z as `eef83bd5204fbf258a094f07d411d33d3eb0d513`. Controller evidence reports Railway backend deployment `12c6edb2-eb41-4c24-b8bd-6177c3557236` SUCCESS at exact `eef83bd5204fbf258a094f07d411d33d3eb0d513`, 29 passing fake unit tests, and bounded isolated PG17 repair/refusal/rollback checks. No production helper SQL was performed. The helper does not cover all roles/passwords or prove application recovery.
- **R3 Railway infra.** Use the `railway-config/` export to reconstruct topology and variable names. Recover actual secret values through the approved secret path, then verify service wiring; the export alone is insufficient.
- **R4 Code.** Retrieve exact required revisions from GitHub or verified local/mirror copies. Do not assume the pending S3 git mirror or all Worker source is complete.
- **R5 Qdrant indexes.** Restore or rebuild all six collections. The Sep 27 isolated Qdrant v1.18.2 restores had live aliases 0 and matching counts/config except `listings` (live 59, snapshot 60). The cause is unproven; no point payload or application checks were performed.
- **R6 Edge and local data.** Reconcile Cloudflare DNS/KV exports with live inventory; obtain permission-complete D1/R2 inventory and verify Worker source. Preserve local AIM Data/vectorAIz knowledge and separately prove Docker volume recovery.
- **R7 Application validation.** Test restored roles/credentials, Infisical, signing, listings/orders, Living State, search, and dependent paths. No end-to-end application recovery has been established.

## 3. Is it working? — monitoring
A Titan-1 watchdog has a six-hour schedule and historical Telegram alert evidence. The claimed two-hour timezone error was not established: AWS CLI 2.34.62 `aws s3 ls` used local time, and the same object appeared at 10:32:24 in UTC, 12:32:24 in Madrid, matching HeadObject 10:32:24Z. GitHub confirms PR309 head `5e341d5614c2ebe6a03a387e492e0495817505c5` merged at 13:19:28Z as `b1185dbf991ac859655f393ab5132946bed2e71e`. Controller evidence records dedicated install `/Users/max/ops/s1754-watchdog-main-36cde2cf`, installed script SHA256 `880f743551d71993732974956b5fa853addc2dd36af32b4e15e7b7a6d57c6d6d`, and first normal run at 17:12:37Z passing PG, Infisical, config, Cloudflare, and six Qdrant collection freshness checks. Actual failure alert delivery remains unverified. For T876, the 02:00 UTC cron was never missing: an unrelated deployment interrupted a dump. GitHub confirms PR508 merged at `20eb5d72951c3569ef98c1d624532d7d60fddc41`. Controller evidence records backup deployment `51983f16-1824-44a5-b669-53f9b3786b6e` remaining at exact `20eb5d72951c3569ef98c1d624532d7d60fddc41` across subsequent backend releases, with four effective `serviceManifest.build.watchPatterns`, 02:00 UTC cron, and restart NEVER. The supported API resolved T876 at 16:45:45.506585Z after artifact, isolated PG17 restore, and real unrelated-release negative-watch acceptance. This is bounded controller evidence, not Git proof or full disaster recovery. The GitHub secondary check's actual threshold is **26h**, not 6h. Verify object timestamps and alert receipt separately.

Infisical offline key custody and service restore, Redis durable-state recovery, important Docker volume coverage, independent Git backup, KMS/re-pair, the S3 recovery map's approved writer, and actual alert delivery remain open. Exporter PR319 and docs PR315/317/318 are separate review candidates, not deployed recovery coverage.

_Updated in repository: 2026-09-27 (S1754). S3 map sync pending; the S3 copy remains stale at June 8, SHA256 beginning `595282`. Authoritative operational detail: [backup-and-recovery.md](./backup-and-recovery.md)._

## When it breaks

Follow the order above and record each missing proof. An S3 object, a successful isolated component restore, and a working recovered application are different outcomes. Do not report complete disaster recovery until the open keys, roles, local data, Cloudflare/Railway inventory, monitoring, and application checks are closed.
