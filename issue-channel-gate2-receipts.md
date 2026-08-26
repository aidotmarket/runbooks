# Issue-Channel Gate 2 Receipts Runbook

## R.1 Purpose and scope boundary
Owns the Gate-2 receipt (evidence) process for BQ-CI-HEALTH-VISIBLE-AT-SESSION-OPEN-S1511: the receipt environment lifecycle, credential identities, probe procedures, evidence package layout, and the failure modes met while producing receipts. Authority for WHAT must be proven is the Gate 2 spec `specs/BQ-CI-HEALTH-VISIBLE-AT-SESSION-OPEN-S1511-GATE2.md` at koskadeux-mcp commit `cdb8e50e` (section 8, V-1 through V-5b); this page never overrides it.

**Boundary:** the full component runbook `issue-ingestion-channel.md` (sections A-K: watcher operation, kill switches, rebuild, queue procedures, rollout/rollback) is owed at implementation completion per Gate 2 spec section 2.6 and does NOT exist yet. Until it lands, this page is the only issue-channel runbook and covers receipts only.

## R.2 Evidence package
- Location: `/Users/max/Projects/ai-market/review-packages/S1511-GATE2-RECEIPTS/` (Titan-1).
- Acceptance is immutable-package on the UNCHANGED spec head `cdb8e50e` (spec sections 8/9), including CORE S4 cross-review of the V-2 receipt + SHA-currency determination. V-5b runs only post-acceptance, pre-rule-activation.
- Chunk provenance: harness chunk 1 = koskadeux-mcp branch `build/bq-s1511-gate2-receipts-v5a-v2c` head `86e364c2` (verified S1618); backend chunk 2 = ai-market-backend branch `build/bq-s1511-gate2-backend-queue-harness` head `40f57482` on base `632f7fbe82` (verified S1620: 22/22 focused tests on real Postgres, ruff clean on new files, router.py findings pre-existing on base).
- Retained checkouts: `/Users/max/koskadeux-state/worktrees/s1608-issue-channel-spec` (spec pin), `/Users/max/koskadeux-state/review-checkouts/s1511-g2recut-cdb8e50e`, `.../s1511-receipts1-86e364c2`, `.../s1511-backend-40f57482`. Prune only after package acceptance (backend one after V-3/V-4 receipts complete).

## R.3 Credential identities (identities only - values live in Infisical, never here)
| Identity | Home | Purpose | Rotation / revocation |
|---|---|---|---|
| `ISSUE_CHANNEL_GITHUB_TOKEN` | Infisical project ai-market-backend (`bd272d48`), env prod, path / | Dedicated fine-grained read-only GitHub PAT (Actions: read + Metadata: read, all aidotmarket repos) for the cloud watcher GitHubAdapter and V-1/V-3 probes. Minted by Max 2026-08-26, expiry 2026-11-24. | Regenerate in GitHub fine-grained tokens console, update Infisical; revoke = delete token in console, immediate. |
| `ISSUE_CHANNEL_POLLER_KEY` | Infisical project ai-market-backend (`bd272d48`), env prod, path / | Dedicated Titan-1 poller credential for the three-operation queue surface. Minted S1620. No consumer until rollout; independently revocable. | Rotate value in Infisical + backend service env together; revoke = remove from backend env, all poller requests then fail closed. |
- Receipt-environment services use RECEIPT-ONLY values generated per run, never the prod identities above (exception: the GitHub token is read-only and may be used for read probes).
- Search rule (S1620 lesson): the vault is split across three projects; ALWAYS search all projects and envs before declaring a credential absent. `config:resource-registry` in Living State is the index and MUST be updated in the same session a secret is added.

## R.4 Receipt environment lifecycle (Railway)
Decision of record (Event `e3b40d4f`, S1620): receipts run in a dedicated EMPTY non-prod environment inside the existing `ai-market` Railway project (`e81dd66f-808c-412e-b32c-f6d910f0ac5d`), created for the receipt run and torn down after acceptance. Production env/services untouched. Note: only `production` exists normally; any `staging` id in local Railway CLI config is stale.

Current instance (S1620): environment `receipt-s1511` id `cce7977e-6db8-4bfa-9925-b761b21c15f6`; Postgres service `receipt-s1511-pg` id `3b9df3d8-36f5-430e-a1da-ecc9b66215f3` (image `ghcr.io/railwayapp-templates/postgres-ssl:16`, volume at `/var/lib/postgresql/data`, TCP proxy `sakura.proxy.rlwy.net:18061`, db `issue_channel_receipt`).

Create (account-scoped token via `source ~/bin/railway-env.sh`; GraphQL v2 at backboard.railway.com):
1. `environmentCreate(input:{projectId, name:"receipt-s1511", skipInitialDeploys:true})` - empty env, no service inheritance.
2. `serviceCreate(input:{projectId, environmentId, name:"receipt-s1511-pg", source:{image:"ghcr.io/railwayapp-templates/postgres-ssl:16"}})`.
3. `variableCollectionUpsert` with POSTGRES_USER/POSTGRES_PASSWORD (fresh `openssl rand -hex 24` per run, held only in a mode-600 temp file for the run)/POSTGRES_DB/`PGDATA=/var/lib/postgresql/data/pgdata`.
4. `volumeCreate(input:{projectId, environmentId, serviceId, mountPath:"/var/lib/postgresql/data"})`.
5. `tcpProxyCreate(input:{environmentId, serviceId, applicationPort:5432})` - gives external host:port for Titan-1.
6. `serviceInstanceDeployV2(environmentId, serviceId)`; poll `deployment(id){status}` to SUCCESS; verify with `psql ... sslmode=require -c 'select version()'`.

Teardown after package acceptance: `environmentDelete(id)` (removes env-scoped instances/volume) and `serviceDelete` for any project-level service artifacts created for receipts; delete the temp password file; record teardown in the BQ note.

## R.5 Applying the backend schema to the receipt DB
From the detached checkout of the chunk-2 head (NOT the working clone):
```bash
cd /Users/max/koskadeux-state/review-checkouts/s1511-backend-40f57482
export SECRET_KEY=$(openssl rand -hex 32)   # Settings import requires it; dummy is fine
export ENVIRONMENT=development RUN_ONE_SHOT_S1163_P2=1   # mandatory: the chain contains an operator-gated one-shot (schema-migration.md), clean bootstrap is never a bare upgrade
export DATABASE_URL="postgresql://postgres:<pw>@<proxy-host>:<port>/issue_channel_receipt?ssl=require"
nohup .../.venv/bin/python -u -m alembic upgrade head < /dev/null >> /tmp/s1511_receipt_migration.log 2>&1 & disown
```
- asyncpg rejects `?sslmode=`; use `?ssl=require` in DATABASE_URL. Plain `psql` uses `sslmode=require`.
- The full chain (300+ revisions) over the WAN proxy takes tens of minutes. Run it in background with nohup + `-u` + stdin from /dev/null and poll the log; alembic commits per revision, so a killed run RESUMES from `alembic_version` - just rerun the same command.
- ONE runner at a time: two concurrent `alembic upgrade head` runs deadlock on `alembic_version` (second blocks on lock; first can sit idle-in-transaction). Check `ps aux | grep alembic` and `pg_stat_activity` before starting; kill duplicates.
- Done when `alembic_version.version_num = s1511_issue_channel_queue` and schema `issue_channel` exists with roles `issue_channel_watcher` and `issue_channel_queue_api`.

## R.6 Probe procedures
- **Role matrix (V-3 step 5):** `RECEIPT_DSN=<libpq dsn> python3 review-packages/S1511-GATE2-RECEIPTS/v3_role_matrix_probe.py` - SET LOCAL ROLE per principal, positive grants for the watcher, negative SELECTs for the queue role on quarantine/raw/canonical/source, full denial for an unprivileged stand-in, default-ACL dump. PASS verdict required; JSON goes into the package as the `two_role_revoke_grant_matrix` receipt line.
- **Queue endpoint fail-closed (V-3 step 6):** requires the queue surface deployed as a service in the receipt env (branch `build/bq-s1511-gate2-backend-queue-harness`); probe all three operations from OUTSIDE Railway with absent key, a wrong existing internal key, and the dedicated poller key; record TLS identity and OpenAPI/route-table exclusion.
- **V-2b / V-2c / V-4:** per spec section 8 verbatim; V-4's real-backup line means the REAL backend backup/restore including the `issue_channel` schema (CORE S3 - unanimous Council where required), never a synthetic copy.

## R.6a Deploying the queue surface into the receipt env (V-3 step 6, done S1621)
1. `serviceCreate(input:{projectId, environmentId, name:"receipt-s1511-queue", branch:"build/bq-s1511-gate2-backend-queue-harness", source:{repo:"aidotmarket/ai-market-backend"}})` - Railway builds the repo Dockerfile; confirm `deployment.meta.commitHash` equals the verified chunk head before trusting the deployment.
2. Required receipt-only variables beyond the obvious: `SECRET_KEY`, `DATABASE_URL` (internal `receipt-s1511-pg.railway.internal:5432`, superuser ok for receipts), `ISSUE_CHANNEL_QUEUE_DATABASE_URL` (role `issue_channel_queue_api`, `?ssl=require` for asyncpg; set a receipt-only password on the role first via superuser `ALTER ROLE`), `ISSUE_CHANNEL_POLLER_KEY` (receipt-only), `PORT`, and - Settings validators demand these even with `ENVIRONMENT=development` - non-default `DOWNLOAD_TOKEN_SECRET_KEY` and `INTERNAL_API_KEY`. Iterate on deployment logs for any further validator additions.
3. Startup runs `alembic upgrade head`; with the receipt DB already at head it is a no-op, so the one-shot env var is not needed at boot.
4. `serviceDomainCreate(targetPort: 8000)` gives the outside-Railway probe URL. The probe script is `review-packages/S1511-GATE2-RECEIPTS/v3_queue_failclosed_probe.py` (env: `QUEUE_BASE_URL`, `RECEIPT_POLLER_KEY`, `WRONG_INTERNAL_KEY` - reuse the receipt `INTERNAL_API_KEY` as the wrong-existing-internal condition). Expected with correct key on an empty receipt DB: snapshot 404, lease 204, complete-intent 409; anything else on the correct key is a finding.
5. Deploys superseded mid-flight report status `REMOVED`, not `FAILED`; always list the service deployments and judge the newest.
6. Teardown additions for this service: the service and its domain die with `environmentDelete`; also delete `/tmp/.receipt_secret_key`, `/tmp/.receipt_internal_api_key`, `/tmp/.receipt_poller_key`, `/tmp/.receipt_queue_role_pw`.

## R.6b V-2b receipt procedure (done S1621)
Probe sources in the package: `v2b_watcher_runner.py` (two competing runners over advisory lock (5393, 1), run as `issue_channel_watcher` with a receipt-only role password), `v2b_scheduler_cadence_probe.py` (cadence + lock-busy skip = non-overlap), `v2b_competing_lease_probe.py` (seeds ONE synthetic queued intent with the exact validated section 4.3 policy and its canonical digest, then two simultaneous authenticated lease calls; expect one 200 + one 204, completion 200, replay 409). Seeding requires: policy fields exactly the reviewed six, `reservation_amount_usd` numerically equal to `max_budget_usd`, `reservation_held=true`, `utc_day` set, `action='dispatch_codex'`. Replica note: Railway `serviceInstanceUpdate` ACCEPTS a staged `numReplicas=2` (no platform rejection); the watcher service definition must pin `numReplicas: 1` via config-as-code, with the advisory lock as the runtime invariant. Receipt env has no exec surface: run probes from Titan-1 against the receipt Postgres and deployed queue surface, and say so in the receipt's observer line.

## R.7 Failure modes met producing receipts
| Symptom | Cause | Fix |
|---|---|---|
| `connect() got an unexpected keyword argument 'sslmode'` | asyncpg DSN | use `?ssl=require` |
| Settings ValidationError SECRET_KEY | backend Settings import during alembic env | export dummy `SECRET_KEY` |
| migration log stalls at `alembic_version` CREATE | second alembic runner lock-blocked behind first | one runner rule (R.5) |
| `RuntimeError: s1163_p2_quarantine is an operator-controlled one-shot migration` | chain contains an operator-gated one-shot | export `RUN_ONE_SHOT_S1163_P2=1` (R.5); documented in schema-migration.md |
| Railway CLI `Environment not found` / stale env ids | `~/.railway/config.json` link cache is stale | trust live GraphQL, never the CLI link file |
| GraphQL `projects{edges:[]}` on account token | workspace-level listing not exposed for this token shape | query `project(id:...)` directly |
| secret "missing" from vault | searched one of three Infisical projects | R.3 search rule |

## R.8 Related
`alerts-at-open.md` (session-open alerts; its forward-work pointer is replaced at implementation completion per spec 2.6), `schema-migration.md` (general alembic discipline), `titan-1.md` (Railway account token), spec worktree at `cdb8e50e`.

## R.9 Owner
BQ-CI-HEALTH-VISIBLE-AT-SESSION-OPEN-S1511 (P1). Maintained by whichever instance holds the s1511 claim; updated same-session whenever the receipt process changes. Superseded section-by-section as `issue-ingestion-channel.md` lands.
