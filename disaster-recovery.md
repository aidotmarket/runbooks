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
- **age private key** — decrypts the Infisical secrets dump. Its sanctioned offline custody must be confirmed; loss would block that dump's recovery.
- **AWS read credentials** for `aimarket-backups-prod` (eu-north-1, account 948749907373) to GET objects. The backup *writer* key is write+list-only and cannot read or delete.
- **Infisical master/recovery keys** — to bring Infisical and its protected data back after a full DB restore. The Sep 27 encrypted backup predates new signing keys; recover those separately.
- **Service secret values and roles** — the Railway topology export records names only. The main DB dump excludes ownership/ACLs and does not supply passwords.

## 1. What was observed — `s3://aimarket-backups-prod`

Versioning, 35-day COMPLIANCE Object Lock, and AES256 encryption were observed on Sep 27. These protect stored objects within the retention window; they do not establish complete system coverage or application recovery.

| Prefix | Contents | Cadence | Restore |
|---|---|---|---|
| `postgres/ai-market/<date>/` | Main marketplace DB, `pg_dump -Fc`. Sep 27 object: 1,416,413,526 bytes, SHA256 `1bc0d09d507ecb7e8e37090292f794df1a26a5edeff2be46c17415abe23d5ddb`. | nightly schedule | R2: full isolated PG17 restore exit 0, 378 tables; owner/ACL omitted |
| `postgres/infisical/<date>/` | Fresh age-encrypted Infisical DB backup observed | nightly schedule | R1: full decrypt/restore blocked pending sanctioned offline age/master/recovery keys; historical TOC listing is not a restore |
| `qdrant/<collection>/<date>/` | Sep 27 snapshots for `action_logs`, `aim_tools`, `data_requests`, `knowledge_base`, `knowledge_base_v2`, `listings` | scheduled snapshots | R5: all six downloaded, hash-verified, isolated no-network restore in Qdrant v1.18.2; `listings` live 59 vs snapshot 60, cause unproven |
| `railway-config/<date>/` | Railway topology and variable **names**, no secret values | nightly schedule | R3: names-only map, not credential recovery |
| `cloudflare/<date>/` | DNS and KV exports observed | nightly schedule | R6: D1/R2 inventory incomplete because of permissions; Worker source coverage unproven |
| `backup-health/` | Per-source last-run status JSON | per run | — |

**Outside this bucket by owner decision:** our own AIM Data + vectorAIz knowledge on Titan-1 must be retained and must not be added to S3 without a new owner decision. `Docker.raw` is excluded by Time Machine, and neither peer has independent Docker volume export/restore proof (#6552/#6553). Dev/e2e recovery belief is unverified. Customer datasets are non-custodial in sellers' buckets. An S3 git mirror is pending; complete Worker source coverage and an application rebuild have not been proven.

## 2. Restore order — secrets, infra, data, code, edge
- **R1 Infisical secrets DB.** Under sanctioned offline-key access, decrypt the chosen `.dump.age`, perform a full restore with the matching Postgres client, then validate Infisical and dependent signing keys. The June 8 `pg_restore -l` listed 6,994 entries / 1,209 tables but did not execute a restore. No Sep 27 full decrypt/restore was authorized or proven.
- **R2 Main marketplace DB.** Select and hash-check a dump; restore into an isolated PG17 instance. Sep 27 full restore exited 0 with 378 tables. Restore required roles, ACLs, default ACLs, and credentials separately before application use. The bounded issue-channel/audit ACL helper at `3bd8ac262eae54f48411306dd5347f23d34cb9b7` passed 16 tests and isolated idempotency/default ACL/forced rollback proof, but is unreleased and does not cover all roles/passwords.
- **R3 Railway infra.** Use the `railway-config/` export to reconstruct topology and variable names. Recover actual secret values through the approved secret path, then verify service wiring; the export alone is insufficient.
- **R4 Code.** Retrieve exact required revisions from GitHub or verified local/mirror copies. Do not assume the pending S3 git mirror or all Worker source is complete.
- **R5 Qdrant indexes.** Restore or rebuild all six collections. The Sep 27 isolated Qdrant v1.18.2 restores had live aliases 0 and matching counts/config except `listings` (live 59, snapshot 60). The cause is unproven; no point payload or application checks were performed.
- **R6 Edge and local data.** Reconcile Cloudflare DNS/KV exports with live inventory; obtain permission-complete D1/R2 inventory and verify Worker source. Preserve local AIM Data/vectorAIz knowledge and separately prove Docker volume recovery.
- **R7 Application validation.** Test restored roles/credentials, Infisical, signing, listings/orders, Living State, search, and dependent paths. No end-to-end application recovery has been established.

## 3. Is it working? — monitoring
A Titan-1 watchdog has a six-hour schedule and historical Telegram alert evidence. Sep 27 UTC calculation, actual delivery, and per-collection Qdrant coverage shortcomings remain open. Its top-level freshness result does not prove six fresh collection snapshots. The GitHub secondary check's actual threshold is **26h**, not 6h. Verify object timestamps and alert receipt separately.

_Updated in repository: 2026-09-27 (S1754). S3 map sync pending; the S3 copy remains stale at June 8, SHA256 beginning `595282`. Authoritative operational detail: [backup-and-recovery.md](./backup-and-recovery.md)._

## When it breaks

Follow the order above and record each missing proof. An S3 object, a successful isolated component restore, and a working recovered application are different outcomes. Do not report complete disaster recovery until the open keys, roles, local data, Cloudflare/Railway inventory, monitoring, and application checks are closed.
