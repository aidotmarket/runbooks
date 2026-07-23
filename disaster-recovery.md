# Disaster Recovery — ai.market (what is in S3 and how to rebuild)

> A copy of this file lives at `s3://aimarket-backups-prod/RESTORE-README.md` so the recovery map survives even if GitHub and Titan-1 are gone. This document is the **map**; `backup-and-recovery.md` (same repo) is the full **manual**.

> **S1322 audit warning — 2026-07-24:** the S3 copy was last uploaded 2026-06-08 and is stale. Current ground truth is: main Postgres and `knowledge_base_v2` Qdrant were fully restored successfully in isolated drills; the current Infisical artifact was not decrypted/restored; Telegram delivery is broken (HTTP 401); GitHub's secondary alarm is generating daily false positives; Cloudflare zone-settings export returns HTTP 403; `git-mirrors/` is empty; and there is no S3 lifecycle policy. Publish this corrected file to S3 after review.

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
| `qdrant/<collection>/<date>/` | Qdrant snapshots for `knowledge_base_v2`, `knowledge_base`, `action_logs`, and `listings` | nightly | R5 |
| `railway-config/<date>/` | Railway topology map: services, source repo/branch, config-as-code path, cron, domains, variable NAMES — **no secret values** | nightly | R3 |
| `cloudflare/<date>/` | DNS records and KV data for ai.market + vectoraiz.com; **zone-settings currently fail with HTTP 403** (Worker scripts are in GitHub) | nightly, currently partial | R6 |
| `backup-health/` | Per-source last-run status JSON | per run | — |

**Intentionally not in this bucket:** our own AIM Data + vectorAIz data — it lives on Titan-1, covered by Titan-1's own local + physically-separate backup (owner decision); customer datasets are non-custodial (sellers' own buckets). **Still to add to S3:** an S3 git mirror (code is durable in GitHub + local clones). Application **code** for every system is in GitHub + local clones, so it is rebuildable.

## 2. Restore order — secrets, infra, data, code, edge
- **R1 Infisical secrets DB.** Pull newest `postgres/infisical/<date>/*.dump.age`; `age -d -i <offline-key> -o infisical.dump <obj>`; restore with a **Postgres 18** client (`docker run --rm -v "$PWD":/work postgres:18 pg_restore --clean --if-exists -d <db-url> /work/infisical.dump`); bring Infisical up with its master key. Secrets come back first — everything else authenticates against them.
- **R2 Main marketplace DB.** Provision Postgres; `pg_restore` newest `postgres/ai-market/<date>/`; point the backend `DATABASE_URL` at it.
- **R3 Railway infra.** Read newest `railway-config/<date>/*.json` for the service map (repos, branches, config-as-code paths, cron, domains, variable names); recreate services from those repos; set each variable's VALUE from restored Infisical (the export holds names only).
- **R4 Code.** `git clone github.com/aidotmarket/*` (plus local clones on Titan-1).
- **R5 allAI memory.** Recreate Qdrant on the same minor version; restore newest required collection snapshots under `qdrant/<collection>/<date>/`. `knowledge_base_v2` is the current primary allAI collection.
- **R6 Edge.** Redeploy Cloudflare Workers from repos; restore DNS records and any required KV values from newest `cloudflare/<date>/`. Zone settings must be captured again with a token that can read them; current exports contain 403 error records and are not sufficient for that step.

## 3. Is it working? — monitoring
A Titan-1 watchdog checks the newest object under five prefixes every 6h: `postgres/ai-market/`, `postgres/infisical/`, `qdrant/`, `railway-config/`, and `cloudflare/`. It detects missing/stale objects, but **Telegram delivery is not operational as of S1322** because the configured token returns HTTP 401. The whole-prefix Qdrant check can also be masked by one healthy collection; monitor every required collection separately. The GitHub secondary verifier must not be trusted until its six-hour threshold and issue deduplication are fixed.

_Last updated: 2026-07-24 (S1322). Authoritative operational detail: `backup-and-recovery.md`._
