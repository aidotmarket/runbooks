# BQ-RAILWAY-ALERT-PARITY-S1757 — every Railway email reaches the issue channel and is triaged

Status: combined Gate 1/Gate 2 spec, proposed, R3 (folds R1: GLM 1-8, DeepSeek 1-4, CC F1-F9; R2: GLM 1-6). Owner: Mars. Entity: `build:bq-railway-alert-parity-s1757`.
Authority: Max 2026-09-27 (Cowork): "1. I would like not to receive them. 2. I need to verify 100% that they are reported to via API to be triaged by our system like the github alerts before we remove them as emails." Decisions: Event Ledger `11e4a031` (emails stay in the inbox until 7 consecutive clean parity days) and `2d4eb010` (no new Railway key: the watcher keeps its project token; the Titan-1 parity job uses the account token Titan-1 already holds).
Baselines: koskadeux-mcp `origin/main 66e1f90588ad81c6b2578c8c760c63d40232a6c3` (adapter at `koskadeux_mcp/issue_channel/adapters/railway.py`); ai-market-backend `origin/main 3f97cd5fe64b97f408517f9d042dafa77e679375` (`.github/workflows/health-check.yml`, `scripts/health_check.py`, state read route `app/api/v1/endpoints/state.py:352-365`); runbooks `issue-channel.md`, `backend-daily-health-check.md` at current main.

## 1. Problem and ground truth (2026-09-27)

Railway sends Max an email for each notification (`notificationDeliveries`, type `EMAIL`). Read with the Titan-1 account token for 2026-09-07..27:

| Railway notification | Emails | In the issue channel today |
|---|---|---|
| `Deployment.failed` ai-market-backend production (7 Sep; 25-26 Sep x4) | 5 | Yes: watcher deployment-status poll, e.g. `iss_01M3DDDRXBGVD2CC3DVE3FB9VK`, `iss_01M3DH09N094RNGMCN9NK3D12H` (all four deployment ids linked) |
| `Deployment.crashed` ai-market-celery-worker production (10 Sep) | 1 | Yes |
| `Deployment.crashed` issue-channel-watcher production (21 Sep, 26 Sep, 27 Sep x3) | 5 | **No.** A crash followed by restart never leaves a `CRASHED` deployment status, and the watcher cannot observe its own crash. |
| `Deployment.crashed` ai-market-backend-verify-s1648 in env verify-s1648 (13-16 Sep) | ~12 | **No** (same cause; non-production) |
| `UsageAlert.triggered` (17, 18, 22 Sep), `ServiceInstance.auto_updated` (12 Sep) | 4 | **No source** |

Every Railway observation is `record_only`: `config/issue_channel/dispatch_rules.yaml` dispatches only GitHub `ci_failure` for `aidotmarket/ai-market-backend`. The watcher polls only project `ai-market` (`RAILWAY_PROJECT_ID`); projects `aim-data`, `vectorAIz` and `infisical` are not observed.

Railway's project-scoped `events(projectId, filter:{action:{in:["crashed","failed"]}})` query returned 20 events for 10-27 Sep that match every `Deployment.*` email to within 0.2 s (checked with the account token; access with the watcher's project token is **UNVERIFIED** and is the first build check, §3.1).

## 2. Outcome

1. Every Railway `Deployment.crashed` / `Deployment.failed` in project `ai-market`, any environment, becomes an issue-channel record from Railway's event log, including crashes of the watcher itself (read on its next healthy cycle through the lookback window).
2. Production Railway `failed` and `crashed` events for project `ai-market` are triaged as the existing kind `deploy_failure` (distinguished only by the sanitized `event_action` field) by the existing metadata-only worker. Non-production stays `record_only`.
3. A Titan-1 parity job proves daily that every Railway email delivery maps to an issue-channel record or a support ticket, and files a ticket for anything else (other projects, usage alerts, volume deletion, auto-update, unknown types).
4. After 7 consecutive clean UTC days, Railway email notifications are switched off (in-app kept) and the switch is recorded in `issue-channel.md`.

Non-goals: no new Railway credential; no webhook endpoint; no change to GitHub/Cloudflare/Council-provider sources; no auto-remediation of Railway problems; no alert delivery to Max beyond the existing Needs-you surfaces.

## 3. Build

### 3.1 Watcher: Railway event source (koskadeux-mcp)

- `koskadeux_mcp/issue_channel/adapters/railway.py`: add one read-only GraphQL query `RailwayProjectEvents(projectId, first, after, filter: {action: {in: ["crashed","failed"]}, object: {in: ["Deployment"]}})`, paginated newest-first with the existing ordering/lookback guards (`_deployments` pattern) and the existing `history_lookback`. Same `Project-Access-Token` header and token.
- **Kind (DeepSeek-1/2, GLM-4/5, CC F3):** both actions normalize to the EXISTING kind `deploy_failure`; the action is a payload field `event_action` (`crashed` | `failed`). No new kind, no change to `IssueKind`, `rules.KINDS` or resolution vocabularies. Subject is unchanged (`railway:<project>/<environment>/<service>`), so the existing `subject|kind|UTC day` correlation folds a status-poll FAILED/CRASHED and its event into one episode and one dispatch.
- `native_id` keeps the status-poll shape `<project>/<environment>/<service>/<deployment>` so both paths share the deployment identity (DeepSeek-3); the event id is a payload field `event_id`. If the event payload lacks service or deployment ids, resolve through `deployment(id)`; if still unresolved, emit with subject `railway:<project>/<environment>/unknown-service` and `event_id` rather than drop it.
- Tests: status-then-event and event-then-status fold to one episode and one dispatch; event-only crash with restart; watcher self-crash read after restart within lookback; pagination boundary; missing ids; non-production classification; unknown action rejected (observation incomplete, never silently dropped).
- First build checks (before any other code; any failure stops the build with an explicit stopped status, never fixture-only acceptance; evidence recorded redacted):
  1. With the watcher's project token, read-only, `events` returns the 10-27 Sep crash/failed events.
  2. With the Titan-1 account token, read-only, `notificationDeliveries` pages both `EMAIL` and `INAPP` deliveries and exposes `notificationInstance{id, eventType, resourceId, projectId, serviceId, environmentId, createdAt}`.
  3. For at least one historical crashed deployment, `notificationInstance.resourceId` equals the deployment id seen by the watcher. Mars pre-check 2026-09-27 (to be re-proven by the build): crashed instances 282a6498, 9a3e3e9b, e7b02dbb equal issue-channel-watcher deployment ids 282a6498 (27 Sep 08:46Z), 9a3e3e9b (06:15Z), e7b02dbb (26 Sep 15:49Z); failed instances 3251e66d, 3bee73b3, a59bb8c2, 11f9f679 equal the four FAILED ai-market-backend deployments.
- Coverage marker: `sources.railway` expected/observed resources gain `<project>:events`; an events read failure makes the observation incomplete exactly like a deployments failure.
- Query-only boundary (GLM-7, CC F7): a test enumerates every GraphQL document the adapter can send and asserts each is a `query` whose operation name is in an explicit allowlist and whose URL is `backboard.railway.com/graphql/v2`.

### 3.2 Dispatch rules (CC F1, F4, F8)

- The rule engine matches only `kind`, `provider`, `subject` (exact) and `severity_hint` (`rules.py:31`). Add one rule per production service with an EXACT subject, e.g. `railway-prod-ai-market-backend-v1: {provider: railway, kind: deploy_failure, subject: "railway:ai-market/production/ai-market-backend"} -> dispatch_codex`, for every service in project `ai-market` environment `production` at build time (list read from Railway, recorded in the PR). Subjects are literal strings in `dispatch_rules.yaml`, not derived from `RAILWAY_PROJECT_NAME`. Keep `default_action: record_only` and the GitHub rules unchanged; a load test proves the revised table loads with no `table_load_error` and that GitHub `ci_failure` still dispatches.
- Coverage guard: the parity job (§3.3) reports any production `Deployment.*` notification whose subject has no rule as a miss, so a new production service cannot silently stay record_only.
- Lane cap: a Railway admission-lane counter (max 2 Railway dispatches per UTC day) enforced at admission, inside the existing global caps, and kept OUTSIDE the immutable six-field worker policy: `policy.py`, `workers.py`, the `v1-reviewed` policy version and the contract corpus are unchanged. The limit lives in `dispatch_rules.yaml` (rule-table config, loaded and validated with the rules). Changed files (CC R3 LOW-1): `rules.py` (`ROOT_KEYS` plus a `RuleTable` field and its validation; a bare new root key would fail the closed-key check and drop the whole table to record_only) and the admission/metering code (`journal.py` `_meter_from_rows`, today metered globally) for the per-provider count. Advisory (CC R3): if the build-time production service count is 2 or fewer, episode folding already bounds Railway to 2 dispatches per day; the build records the count and may drop the lane cap with that evidence. Tests: shipped config loads; GitHub and Railway admitted under their caps; journaled policy JSON still accepted by the worker; removing the lane config restores today's behaviour. Worker input gains only allowlisted sanitized Railway fields (service, environment, event_action, deployment id, timestamps); no logs, no variables.

### 3.3 Titan-1 parity job (koskadeux-mcp)

- `scripts/railway_alert_parity.py` + launchd job `com.koskadeux.railway-alert-parity` (every 15 minutes). Token: the existing account-scoped Titan-1 token `titan-1-koskadeux`, obtained exactly as `titan-1.md` prescribes (`source ~/bin/railway-env.sh`, `RAILWAY_TOKEN` unset). Build proves by name/scope checks, never by printing values, that the watcher keeps a project-scoped token and the account token is used only by this job. The job is query-only (same allowlist test as §3.1), never logs or stores the token, and never calls any Railway mutation (GLM-7, CC F7). Residual risk accepted by Event `2d4eb010`: the token itself is account-wide; read-only is enforced by code and tests, not by Railway.
- **Ground truth (GLM-1):** `notificationDeliveries` (EMAIL and INAPP) grouped by `notificationInstance.id`. Every instance counts, whichever channel carried it, so parity survives the email switch-off because in-app deliveries continue.
- **Cursor, not a window (GLM-3):** the job persists a high-water mark (newest instance `createdAt` + id fully processed) and pages back until it reaches it. If the mark is older than Railway's retrievable history or pagination cannot reach it, the run fails and the day is not clean.
- **Match (GLM-2, CC F2):** for `Deployment.crashed` / `Deployment.failed` in project `ai-market`, `notificationInstance.resourceId` is the deployment id (verified 2026-09-27: resourceIds 3251e66d, 3bee73b3, a59bb8c2, 11f9f679 equal the four FAILED deployment ids). The job matches it against the persisted per-observation safe records: `issue_channel.safe_raw_records.redacted_projection->>'deployment_id'` scoped to provider railway (the status poll already persists `deployment_id` in its payload, `adapters/railway.py:380-400`; the events path must persist the same field, in a shape that cannot trip sanitizer quarantine; a test asserts an events-path crashed observation lands in `safe_raw_records` with `redacted_projection->>'deployment_id'` equal to the event's deployment id, CC R3 NIT-1; a quarantined observation would be a miss, which fails safe), read-only through a dedicated read role, with an index if the query needs one. Not against canonical issue member lists and not against the snapshot mirror (CC F6). Test with a folded multi-deployment episode finds every deployment id.
- **Everything else** (other projects, `UsageAlert.*`, `Volume*`, `ServiceInstance.*`, unknown types): filed as a support ticket through the existing support-ticket API, idempotent by an external reference equal to the notification instance id. The job verifies each ticket exists by reading it back; a create or read-back failure fails the run (GLM-6).
- Unmatched `ai-market` deployment instances older than 30 minutes are misses: ticket (same idempotency) and count.
- Output: Living State `infra:railway-alert-parity` in the backend state store, written through `PUT /api/v1/state/{key}` (`state.py:567`) with the credential koskadeux-mcp's existing Living State client already uses, so write and health-check read hit the same store; a round-trip test writes the key and reads it back through `GET /api/v1/state/{key}` (CC R3 NIT-2) (sole writer: this job; launchd single instance plus a lock file so runs never overlap) with cursor, counts by type, matched, ticketed, misses, last run, last success; daily Event Ledger entry `railway-alert-parity-daily`.
- **Independent staleness (GLM-1, CC F5):** the backend Daily Health Check (`health-check.yml` on a GitHub-hosted runner, 07:00 UTC daily, `scripts/health_check.py`) gains one check that reads `infra:railway-alert-parity` through the backend state route (`GET /api/v1/state/{key}`, `state.py:352-365`) and reports CRITICAL when the record is absent (404), unreadable (transport error), malformed, or `last_success` is older than 2 hours. The existing CRITICAL path opens a GitHub issue that the issue channel already ingests. Detection latency is up to 24 hours (daily run). No Titan-1 component judges its own freshness. This is an ai-market-backend change reviewed with the rest.
- Clean day = every scheduled run of the UTC day succeeded, cursor continuous, zero misses, every non-watcher instance ticketed and read back.

### 3.4 Email switch-off

After 7 consecutive clean days, record the evidence on the entity, then Max switches Railway email notifications off in the Railway dashboard account notification settings (in-app kept on); the exact click path is recorded in `issue-channel.md`. The account token is not used for this change (GLM-7). Verify: the next Railway notification appears as INAPP only, is matched or ticketed by the parity job, and a deployment one is in the issue channel. Re-enable rule: if the health check reports the parity record stale for more than 24 hours, Mars asks Max to turn Railway emails back on until parity recovers; documented in `issue-channel.md` with how to turn them back on.

## 4. Acceptance

| ID | Evidence |
|---|---|
| R1 | Project-token `events` read proof (first build check) |
| R2 | Adapter tests §3.1 incl. cross-path fold (one episode, one dispatch), self-crash after restart, unknown action |
| R3 | Rule tests: table loads; each production service subject dispatches once per episode; non-production and other projects record_only; GitHub unchanged; Railway sub-cap respected; global caps respected |
| R4 | Parity tests with recorded fixtures: EMAIL+INAPP grouping, cursor continuity and gap failure, folded episode match, miss, ticket idempotency and read-back failure, non-deployment types, pagination, API failure = run failed |
| R5 | Query-only allowlist tests for adapter and job; the three first-build capability probes (§3.1) recorded; watcher still holds a project-scoped token (name/scope check, no value printed) |
| R6 | Health-check tests: stale, absent (404), malformed and unreadable parity record each -> CRITICAL; fresh -> OK |
| R7 | Backfill run from 2026-09-20T00:00Z to build time: every §1 row either matched (deployment failures, celery crash) or ticketed (watcher crashes before this deploy, verify-s1648 crashes, usage alerts, auto-update), with zero unexplained items |
| R8 | Live: first real production Railway failure or crash after deploy is recorded, dispatched and triaged; no synthetic production failure |
| R9 | 7 consecutive clean days before switch-off; post-switch-off INAPP-only verification |

Review: Tier 3 (monitoring fail-closed envelope + account-token use): full panel GLM, DeepSeek, CC in Gemini seat per d50cbd80. MP builds; Mars verifies. Deploy watcher changes through the existing issue-channel-watcher path; load the launchd job per `titan-1.md`; health-check change ships through the backend PR path.

## 5. Risks

- Railway event and notification schemas are undocumented: fail closed (observation incomplete, parity run failed), never silently skip.
- Crash storms: correlation folds per subject and day, Railway sub-cap 2 per day, excess stays recorded.
- Titan-1 offline: parity record goes stale; the GitHub health check reports it; emails stay on until 7 clean days, and after switch-off the 24-hour rule reopens them.
