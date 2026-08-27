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

## R.6c V-2c receipt procedure (done S1623)
Actual poller executor-context proof. Probe `review-packages/S1511-GATE2-RECEIPTS/v2c-probe/v2c_probe_main.py` runs ONLY under launchd: a development-tooling LaunchAgent (`com.koskadeux.issue-channel.v2cprobe`, plist copy + sha in the package) bootstraps the chunk-1 checkout's harness with the koskadeux-mcp venv python, working directory = the detached chunk-1 checkout (`86e364c2`), ppid 1, no TTY, no profile sourcing, no inbound listener (lsof LISTEN empty). State root `/Users/max/koskadeux-state/issue-channel` (0700) holds both the dedicated executor lock `issue-channel.lock` and the Gate 1 local snapshot path `snapshot.json`.
Flow: seed one synthetic queued intent (exact R.6b seeding contract) plus one `issue_channel.safe_snapshot_records` row (superuser DSN, synthetic state) -> authenticated `GET snapshot`, validate strict response keys and the 10-key forbidden-field scan, atomic tmp+fsync+`os.replace` mirror preserving cloud `generated_at`, fresh render `channel ok` -> authenticated lease -> harness `DispatchPolicy.from_mapping` full finite-positive revalidation at the worker boundary with admitted==enforced digest -> two competing poller workers: file flock EX|NB refused for the second AND harness ExecutorLock returns None without worker construction (exactly 1 construction) -> deterministic fake worker -> `POST complete-intent` with the same intent + nonce, 200 `completed`, measured cost matches the fake worker -> mirror stopped, sleep past 2x cadence, render `channel stale`; missing path renders `channel unavailable`.
Gotchas: seed the snapshot row with `generated_at = now` immediately before the mirror or the fresh render can already be stale over the WAN; do the stale sleep AFTER completion so the lease window stays comfortable; launchd env DOES carry a `SHELL` var from the user record - the no-interactive-shell proof is ppid 1 + no TTY, not SHELL absence. Teardown additions: delete `/Users/max/koskadeux-state/issue-channel/` (synthetic mirror + lock) with the other receipt artifacts.

## R.6d V-4 receipt procedure (done S1623)
Executed only after a Council-unanimous execution plan (koskadeux-mcp branch plan/s1511-v4-execution-v3 @ 6155dabb; Kimi + GLM APPROVE_WITH_MANDATES folded, CC APPROVE_WITH_NITS honored). Probes: `v4-probe/v4_lib.py` (10 sentinel classes x 4 encodings: exact/base64/url/hex), `v4_main.py` (phase A), `v4_phaseB.py` (phase B), `restore_roles_step.sql` (the D4 documented restore step).
Phase A: purge prior v4 rows -> seed as-sanitized rows through the WATCHER role (real writer path) across all six issue_channel tables + one intent + snapshot row, plus two labeled PLANTED-SELF-TEST sentinel rows (scanner self-test) -> lease/complete via the deployed queue surface -> scan every table row, all three endpoint responses, and the local mirror. Zero hits outside planted rows AND the scanner must find every planted encoding. Retention proven by inserting without `expires_at` (30d quarantine / 90d sanitized-raw server defaults). Interrupted-tx: open a tx, INSERT an intent, `os.close(conn.fileno())` (NOT socket.fromfd - that dups the fd and kills nothing), verify row absent and no lingering backend/locks; terminate leftover `v4-interrupted` backends in the purge step or re-runs count them as stuck.
Phase B (clean-before-immutable order): real-mechanism dump `pg_dump -Fc --no-owner --no-privileges` (pg 17, same major as the deployed container; backup_pg.py has no -n/-N filter) -> scan raw bytes AND `pg_restore -f -` SQL text BEFORE upload (the SQL-text scan is load-bearing; -Fc compression makes raw-byte scanning non-evidential) -> upload ONLY to `receipts/s1511/postgres/<date>/` with `--checksum-sha256`, assert the S3 response digest matches, and assert `postgres/ai-market/` + `backup-health/ai-market/` newest objects are unchanged before/after -> restore into `issue_channel_restore` -> inventory match (tables/constraints/indexes/alembic head/row counts) -> zero-decryption disposition -> grants ABSENT as expected (dump cannot carry ACLs/default-privs; roles are cluster-level) -> apply the restore role step -> full role-matrix probe PASS on the restored DB. SUPERSEDED (S1624): the binding restore role step is now `restore_roles_step_v3.py` (package V3 `corrective3/r6/`), which executes the pinned migration's own `_apply_security_matrix` verbatim instead of hand-copied SQL; v1/v2 SQL files are historical only — v2 provably leaves the watcher read-only on a clean restore.
Gotchas: PG17 pg_dump emits `SET transaction_timeout` which a PG16 receipt server rejects as pg_restore's single ignorable error - assert exactly that one error, prod restores are same-major; `aclexplode('{}'::aclitem[])` errors ("ACL arrays must be one-dimensional") - use `c.relacl is not null` + lateral instead; `correlation_key`/`episode_key` are plain identifiers, exclude them from key-material checks and test bytea columns + crypto defaults instead (backend-wide pgcrypto rides in any full dump and is outside issue_channel scope). RESUME_FROM_RESTORE=1 / RESUME_FROM_GRANTS=1 resume a failed phase B on the same sha256-verified artifact without a second WORM upload.
Receipt: `v4-noncustodial-surface-scan.json` (PASS, provable-now scope; deferred items recorded as binding implementation mandates mapped to their increments). Teardown additions: `drop database issue_channel_restore`; `/tmp/v4_receipt_s1511.dump`; the WORM object under `receipts/s1511/` self-expires with the bucket's 35d COMPLIANCE lock and cannot be deleted earlier.

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


## S1624 corrective rounds 2-3 (round-1/2 review findings, executed fixes)

Packages: V2 `57d2bd99`, V3 `3a0ee923` (V3 is authoritative; `corrective/` + `corrective3/`).

- **Restore role step is v3 (migration reuse).** `restore_roles_step_v3.py` imports the
  migration from the pinned backend checkout and runs `_apply_security_matrix` verbatim
  (alembic transport shimmed; all statements logged). Any future restore MUST use this
  mechanism; verify on a clean `--no-owner --no-privileges` restore with the 26-check
  probe (`r6_clean_restore_probe.py`): watcher full DML incl. future tables, app role
  42501-denied on all four future-object classes (TABLE/SEQUENCE/FUNCTION/TYPE), queue
  narrow rights, PUBLIC zero grants.
- **Service credential rule (found-and-fixed).** The r5 negative check caught the queue
  service `DATABASE_URL` carrying the Postgres superuser credential. Production mandate:
  the backend service app DSN must NEVER carry a superuser or watcher credential; the
  queue routes bind only the dedicated queue-role DSN. Receipt env now uses NOSUPERUSER
  `receipt_app_login` (public schema only, denied on issue_channel).
- **Single-replica enforcement is layered and both layers are mandatory in production:**
  (1) config-as-code `numReplicas = 1` in railway.toml — reasserted in the finalized
  manifest on every deploy; (2) `scripts/replica_singleton_guard.py` as the image
  entrypoint (session advisory lock (0x1511,2) on the queue-role DSN, 90s retry for
  redeploy overlap) — a deployment whose definition carries 2 replicas ends FAILED
  (proven: deployment efb70cb7); (3) the v2b advisory-lock runtime exclusion.

### Failure/symptom table additions (Railway + tooling, learned S1624)

| Symptom | Cause / fix |
| --- | --- |
| `pg_restore: unsupported version (1.16) in file header` | Archive from pg_dump 17+; use `/opt/homebrew/opt/postgresql@17/bin/pg_restore`, not `/opt/homebrew/bin`. |
| `pg_restore --schema=X` into empty DB: "schema X does not exist" | `--schema` filters objects but omits CREATE SCHEMA; create the schema first. |
| Container loop: `can't open file '/app/scripts/...'` | `.dockerignore` excludes `scripts/`; add `!scripts/<file>` negations. |
| asyncpg `CantChangeRuntimeParamError: parameter "ssl"` | DSN carries `?ssl=require` which asyncpg forwards as a server param; strip the query string and pass `ssl="require"` as a connect kwarg. |
| Railway deployment `meta.serviceManifest` shows staged replica count while BUILDING | Transient pre-finalization value; only the finalized manifest (DEPLOYING/SUCCESS/FAILED) is evidential. |
| Guard blocks a normal redeploy | Old instance holds the advisory lock during drain; the 90s retry window covers it — do not remove the guard, wait. |
| Probe DENY checks all fail with pg_code 25P02 | A helper ran `RESET ROLE` on an aborted transaction, masking the real 42501; wrap per-check work in SAVEPOINTs and suppress errors in the reset path. |


## R.10 TORN DOWN (S1624, 2026-08-27) — receipt environment no longer exists

Acceptance achieved (unanimous two-seat round 3, package V3 `3a0ee923`; Event Ledger
`33cd4513`). Removed the same session: Railway environment `receipt-s1511`
(services receipt-s1511-queue + receipt-s1511-pg, env id cce7977e), all `/tmp/.receipt_*`
secret files incl. `receipt_app_login`'s, the V-4 dump `/tmp/v4_receipt_s1511.dump`,
the r2probe LaunchAgent, worktree `/tmp/s1624-r8-wt`, and pinned checkouts
`s1511-g2recut-cdb8e50e` + `s1511-backend-40f57482`. RETAINED: the immutable packages
V1/V2/V3 + tarballs under `review-packages/` (sole evidence source from now on), the
harness branch `build/bq-s1511-gate2-backend-queue-harness` (receipt-support commits
referenced by receipts), and checkout `s1511-receipts1-86e364c2` (not on the recorded
prune list; prune candidate at next housekeeping). All receipt-DB probes in this
runbook are now HISTORICAL — nothing here is live infrastructure.

## R.11 PRODUCTION INSTALL (S1629, 2026-08-27) — live state of record

- Watcher service: `issue-channel-watcher` id `d48dd44c-4541-4387-89da-50b2b1d0c8fe`, project ai-market, env production, deploys `aidotmarket/koskadeux-mcp` main via `deploy/issue-channel-watcher/{Dockerfile,railway.toml}` (root Dockerfile/railway.toml deliberately untouched — service-definition test pins them). CMD: guard (`scripts/replica_singleton_guard_watcher.py`, session lock (0x1511,3)) then `scripts/issue_channel.py --source github` (GitHub-only per rollout step 6; record_only via shipped dispatch_rules.yaml). Run lock stays (0x1511,2).
- Migration `s1511_issue_channel_queue` CANNOT run via the container's `alembic upgrade head`: it requires env `ISSUE_CHANNEL_APPLICATION_DB_ROLE`, refuses a superuser app role, and requires the migration role ≠ app role. Run it OUT-OF-BAND as postgres with the env set (done S1629). Backend deploys no-op afterwards.
- Backend application role is now `ai_market_app` (NOSUPERUSER; grants on public/mcp_safe/quarantine + default privs from postgres). API + celery-worker `DATABASE_URL` use it; `ai-market-backup` deliberately stays superuser for pg_dump; celery-beat carries no own DATABASE_URL. 26/26 matrix probe on production: `review-packages/S1511-PROD-INSTALL/prod-matrix-receipt-s1629.json`.
- Credentials (values in Infisical bd272d48/prod/): `ISSUE_CHANNEL_WATCHER_DATABASE_URL`, `ISSUE_CHANNEL_QUEUE_DATABASE_URL`, `DATABASE_URL_AI_MARKET_APP`. Railway service vars are literals (not references) — re-point them if the Postgres credential ever rotates.
- Two live defects fixed on koskadeux-mcp main with local-pg regressions: `6630ac5cf6` (advisory_lock left autobegun tx; run_once never started), `832dd69d2c` (same-episode second fingerprint violated unique episode_key; crash loop on a day's 2nd CI failure). Both were carried-GLM-1 compositional-gap territory: when a review says "proof is compositional", run the assembled loop against real Postgres before install.

| Symptom | Cause / fix |
| --- | --- |
| Backend deploy FAILED: `ISSUE_CHANNEL_APPLICATION_DB_ROLE ... is required` | By-design migration guard; run the migration out-of-band per R.11, never bypass. |
| Watcher: `A transaction is already begun on this Session` | Pre-6630ac5cf6 code; pull main. |
| Watcher crash loop: `duplicate key ... canonical_issues_episode_key_key` | Pre-832dd69d2c code; pull main. |

## R.12 ROLLOUT STEPS 7-8 LIVE (S1630, 2026-08-27) — poller + board/ops channel display

- **Titan-1 poller (step 7)**: LaunchAgent `com.koskadeux.issue-channel-poller` (StartInterval 300s, RunAtLoad) runs `~/bin/issue_channel_poller_launch.sh`, which refreshes the sysadmin Infisical JWT, fetches `ISSUE_CHANNEL_POLLER_KEY` (project bd272d48/prod) per run — never stored on disk — and execs `koskadeux-mcp venv python scripts/issue_channel_poller.py --base-url https://api.ai.market`. Outbound-only; executor lock `poller-executor.lock` inside `/Users/max/koskadeux-state/issue-channel/` (0700). Logs: `/var/tmp/koskadeux/issue-channel-poller.{out,err}.log`.
- **Step 7 proofs (all live, external)**: 401 on snapshot+lease with absent and wrong key; authenticated mirror atomically writes `snapshot.json` preserving cloud `generated_at`; empty-queue lease → `no_intent` (204); stale-on-mirror-stop → session-open line rendered `channel stale` past 2x300s (18:42:25Z), recovered after agent load.
- **Board + ops display (step 8)**: session-open line carries the channel segment (AC-5b hunk on koskadeux-mcp main). ops frontend renderer shipped via `ops-ai-market` PR #27 (branch `build/bq-s1511-ops-channel-renderer`, head `bdefc10f`, base `f093293`; MP built, GLM APPROVE zero findings, 30/30 component tests + tsc clean, vulcan `npm run build` verified; merge `ca17d10`; Railway `ops-dashboard` deploy SUCCESS on `ca17d102d6`). Live page verified rendering `CHANNEL / channel unavailable (github)`; line/page agree on the same mirrored snapshot. `expired_unleased` → "dispatcher offline / queue undrained" is fixture-proved in the reviewed component test (a live fault cannot exist while dispatch is disabled, and the board must never be hand-fed).
- **GitHub token state**: Issues:read granted+verified S1630 (see infisical-secrets.md). Checks:read NOT grantable in the PAT console (no `checks` field in the edit form) while the API 403 demands `checks=read`. RESOLVED S1631: GitHub product limitation, not org policy — fine-grained PATs cannot hold checks:read at all (only GitHub Apps; github.com/orgs/community/discussions/129512). Nothing for Max to do in GitHub; the check-runs question goes to design authority (drop from expected resources vs GitHub App). Until settled, `channel unavailable (github)` is the honest steady state; CI-failure signal itself is fully carried by actions:read.
- **Direct push to ops-ai-market main is refused by repository rules** — merge via PR (`gh pr create` + `gh pr merge`).

| Symptom | Cause / fix |
| --- | --- |
| Board says `channel stale` | Poller/mirror stopped: `launchctl print gui/$(id -u)/com.koskadeux.issue-channel-poller`, then err log. Re-bootstrap the plist if absent. |
| Board says `channel unavailable (github)` | Known-honest PAT scope gap (checks). See R.12 GitHub token state. |
| Poller exit nonzero, err log shows 401 | Poller key rotated in Infisical but not on backend service (or vice versa) — R.3 rotation rule: both together. |
