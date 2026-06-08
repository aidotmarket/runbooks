# Disaster Recovery — ai.market (what is in S3 and how to rebuild)

> A copy of this file lives at `s3://aimarket-backups-prod/RESTORE-README.md` so the recovery map survives even if GitHub and Titan-1 are gone. This document is the **map**; `backup-and-recovery.md` (same repo) is the full **manual**.

## 0. Before you can restore anything — offline bootstrap items
You cannot read the backups without these, and they are deliberately NOT in S3 or on any server:
- **age private key** — decrypts the Infisical secrets dump. **1Password only.** If lost, that dump is unrecoverable.
- **AWS read credentials** for `aimarket-backups-prod` (eu-north-1, account 948749907373) to GET objects. The backup *writer* key is write+list-only and cannot read or delete.
- **Infisical master/recovery key** — to bring Infisical back up after its DB is restored.

## 1. What is in the bucket — `s3://aimarket-backups-prod` (eu-north-1; Object Lock COMPLIANCE 35d; SSE-S3; private)
| Prefix | Contents | Cadence | Restore |
|---|---|---|---|
| `postgres/ai-market/<date>/` | Main marketplace DB (marketplace + Living State + dispatch ledger), `pg_dump -Fc` | nightly | R2 |
| `postgres/infisical/<date>/` | Infisical secrets DB, age-encrypted `.dump.age` | nightly 03:00 UTC | R1 |
| `qdrant/knowledge_base/<date>/` | allAI memory (Qdrant snapshot) | nightly | R5 |
| `railway-config/<date>/` | Railway topology map: services, source repo/branch, config-as-code path, cron, domains, variable NAMES — **no secret values** | nightly | R3 |
| `backup-health/` | Per-source last-run status JSON | per run | — |

**Intentionally not in this bucket:** our own AIM Data + vectorAIz data — it lives on Titan-1, covered by Titan-1's own local + physically-separate backup (owner decision); customer datasets are non-custodial (sellers' own buckets). **Still to add to S3:** Cloudflare (Worker KV + DNS) and an S3 git mirror. Application **code** for every system is in GitHub + local clones, so it is rebuildable.

## 2. Restore order — secrets, infra, data, code, edge
- **R1 Infisical secrets DB.** Pull newest `postgres/infisical/<date>/*.dump.age`; `age -d -i <offline-key> -o infisical.dump <obj>`; restore with a **Postgres 18** client (`docker run --rm -v "$PWD":/work postgres:18 pg_restore --clean --if-exists -d <db-url> /work/infisical.dump`); bring Infisical up with its master key. Secrets come back first — everything else authenticates against them.
- **R2 Main marketplace DB.** Provision Postgres; `pg_restore` newest `postgres/ai-market/<date>/`; point the backend `DATABASE_URL` at it.
- **R3 Railway infra.** Read newest `railway-config/<date>/*.json` for the service map (repos, branches, config-as-code paths, cron, domains, variable names); recreate services from those repos; set each variable's VALUE from restored Infisical (the export holds names only).
- **R4 Code.** `git clone github.com/aidotmarket/*` (plus local clones on Titan-1).
- **R5 allAI memory.** Recreate Qdrant; restore newest `qdrant/knowledge_base/<date>/` snapshot.
- **R6 Edge.** Redeploy Cloudflare Workers from repos; re-apply DNS/KV (today rebuilt from repo/manual, not from S3).

## 3. Is it working? — monitoring
A Titan-1 watchdog checks the newest object under each monitored prefix every 6h and **pages Max on Telegram** if any is missing or older than 26h, independent of Infisical. It currently covers `postgres/ai-market/`, `postgres/infisical/`, and `qdrant/`.

_Last updated: 2026-06-08 (S799.w). Authoritative operational detail: `backup-and-recovery.md`._
