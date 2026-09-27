# BQ-RAILWAY-ALERT-PARITY-S1757 — every Railway email reaches the issue channel and is triaged

Status: combined Gate 1/Gate 2 spec, proposed, R2 (folds all R1 findings: GLM 1-8, DeepSeek 1-4, CC F1-F9). Owner: Mars. Entity: `build:bq-railway-alert-parity-s1757`.
Authority: Max 2026-09-27 (Cowork): "1. I would like not to receive them. 2. I need to verify 100% that they are reported to via API to be triaged by our system like the github alerts before we remove them as emails." Decisions: Event Ledger `11e4a031` (emails stay in the inbox until 7 consecutive clean parity days) and `2d4eb010` (no new Railway key: the watcher keeps its project token; the Titan-1 parity job uses the account token Titan-1 already holds).
Baselines: koskadeux-mcp `origin/main 66e1f90588ad81c6b2578c8c760c63d40232a6c3`; runbooks `issue-channel.md` at current main.

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
2. Production `deploy_failure` and `deploy_crash` for project `ai-market` are triaged by the existing metadata-only worker under the same caps as GitHub CI. Non-production stays `record_only`.
3. A Titan-1 parity job proves daily that every Railway email delivery maps to an issue-channel record or a support ticket, and files a ticket for anything else (other projects, usage alerts, volume deletion, auto-update, unknown types).
4. After 7 consecutive clean UTC days, Railway email notifications are switched off (in-app kept) and the switch is recorded in `issue-channel.md`.

Non-goals: no new Railway credential; no webhook endpoint; no change to GitHub/Cloudflare/Council-provider sources; no auto-remediation of Railway problems; no alert delivery to Max beyond the existing Needs-you surfaces.

## 3. Build

### 3.1 Watcher: Railway event source (koskadeux-mcp)

- `koskadeux_mcp/issue_channel/adapters/railway.py`: add one read-only GraphQL query `RailwayProjectEvents(projectId, first, after, filter: {action: {in: ["crashed","failed"]}, object: {in: ["Deployment"]}})`, paginated newest-first with the existing ordering/lookback guards (`_deployments` pattern) and the existing `history_lookback`. Same `Project-Access-Token` header and token.
- **Kind (DeepSeek-1/2, GLM-4/5, CC F3):** both actions normalize to the EXISTING kind `deploy_failure`; the action is a payload field `event_action` (`crashed` | `failed`). No new kind, no change to `IssueKind`, `rules.KINDS` or resolution vocabularies. Subject is unchanged (`railway:<project>/<environment>/<service>`), so the existing `subject|kind|UTC day` correlation folds a status-poll FAILED/CRASHED and its event into one episode and one dispatch.
- `native_id` keeps the status-poll shape `<project>/<environment>/<service>/<deployment>` so both paths share the deployment identity (DeepSeek-3); the event id is a payload field `event_id`. If the event payload lacks service or deployment ids, resolve through `deployment(id)`; if still unresolved, emit with subject `railway:<project>/<environment>/unknown-service` and `event_id` rather than drop it.
- Tests: status-then-event and event-then-status fold to one episode and one dispatch; event-only crash with restart; watcher self-crash read after restart within lookback; pagination boundary; missing ids; non-production classification; unknown action rejected (observation incomplete, never silently dropped).
- First build check (before any other code): prove with the watcher's project token, read-only, that `events` returns the 10-27 Sep crash/failed events. If it does not, stop and report; do not add a broader token.
- Coverage marker: `sources.railway` expected/observed resources gain `<project>:events`; an events read failure makes the observation incomplete exactly like a deployments failure.
- Query-only boundary (GLM-7, CC F7): a test enumerates every GraphQL document the adapter can send and asserts each is a `query` whose operation name is in an explicit allowlist and whose URL is `backboard.railway.com/graphql/v2`.

### 3.2 Dispatch rules (CC F1, F4, F8)

- The rule engine matches only `kind`, `provider`, `subject` (exact) and `severity_hint` (`rules.py:31`). Add one rule per production service with an EXACT subject, e.g. `railway-prod-ai-market-backend-v1: {provider: railway, kind: deploy_failure, subject: "railway:ai-market/production/ai-market-backend"} -> dispatch_codex`, for every service in project `ai-market` environment `production` at build time (list read from Railway, recorded in the PR). Subjects are literal strings in `dispatch_rules.yaml`, not derived from `RAILWAY_PROJECT_NAME`. Keep `default_action: record_only` and the GitHub rules unchanged; a load test proves the revised table loads with no `table_load_error` and that GitHub `ci_failure` still dispatches.
- Coverage guard: the parity job (§3.3) reports any production `Deployment.*` notification whose subject has no rule as a miss, so a new production service cannot silently stay record_only.
- Lane cap: add a per-provider daily dispatch sub-cap (`railway_daily_dispatch_cap: 2`) inside the existing global caps (4 dispatches, $12 per UTC day) so a Railway crash storm cannot consume GitHub CI triage; GitHub gets its existing behaviour. If `policy.py` cannot express a sub-cap, the build adds the smallest reviewed change there with tests. Worker input gains only allowlisted sanitized Railway fields (service, environment, event_action, deployment id, timestamps); no logs, no variables.

### 3.3 Titan-1 parity job (koskadeux-mcp)

- `scripts/railway_alert_parity.py` + launchd job `com.koskadeux.railway-alert-parity` (every 15 minutes). Token: the existing account-scoped Titan-1 token `titan-1-koskadeux`, obtained exactly as `titan-1.md` prescribes (`source ~/bin/railway-env.sh`, `RAILWAY_TOKEN` unset). Build proves by name/scope checks, never by printing values, that the watcher keeps a project-scoped token and the account token is used only by this job. The job is query-only (same allowlist test as §3.1), never logs or stores the token, and never calls any Railway mutation (GLM-7, CC F7). Residual risk accepted by Event `2d4eb010`: the token itself is account-wide; read-only is enforced by code and tests, not by Railway.
- **Ground truth (GLM-1):** `notificationDeliveries` (EMAIL and INAPP) grouped by `notificationInstance.id`. Every instance counts, whichever channel carried it, so parity survives the email switch-off because in-app deliveries continue.
- **Cursor, not a window (GLM-3):** the job persists a high-water mark (newest instance `createdAt` + id fully processed) and pages back until it reaches it. If the mark is older than Railway's retrievable history or pagination cannot reach it, the run fails and the day is not clean.
- **Match (GLM-2, CC F2):** for `Deployment.crashed` / `Deployment.failed` in project `ai-market`, `notificationInstance.resourceId` is the deployment id (verified 2026-09-27: resourceIds 3251e66d, 3bee73b3, a59bb8c2, 11f9f679 equal the four FAILED deployment ids). The job matches it against the persisted per-observation records of the issue channel (raw/sanitized envelope `native_id`, which carries every folded deployment id), read-only through a dedicated read role; not against canonical issue member lists and not against the snapshot mirror (CC F6). The build names the exact table/column and adds a test with a folded multi-deployment episode.
- **Everything else** (other projects, `UsageAlert.*`, `Volume*`, `ServiceInstance.*`, unknown types): filed as a support ticket through the existing support-ticket API, idempotent by an external reference equal to the notification instance id. The job verifies each ticket exists by reading it back; a create or read-back failure fails the run (GLM-6).
- Unmatched `ai-market` deployment instances older than 30 minutes are misses: ticket (same idempotency) and count.
- Output: Living State `infra:railway-alert-parity` (sole writer: this job; launchd single instance plus a lock file so runs never overlap) with cursor, counts by type, matched, ticketed, misses, last run, last success; daily Event Ledger entry `railway-alert-parity-daily`.
- **Independent staleness (GLM-1, CC F5):** the existing backend GitHub Actions Daily Health Check (`health-check.yml`, runs off Titan-1) reads `infra:railway-alert-parity` and reports CRITICAL when `last_success` is older than 2 hours; this reaches the issue channel through the existing GitHub path. No Titan-1 component judges its own freshness.
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
| R5 | Query-only allowlist tests for adapter and job; token-scope name checks |
| R6 | Health-check freshness test (stale parity record -> CRITICAL) |
| R7 | Backfill run from 2026-09-20T00:00Z to build time: every §1 row either matched (deployment failures, celery crash) or ticketed (watcher crashes before this deploy, verify-s1648 crashes, usage alerts, auto-update), with zero unexplained items |
| R8 | Live: first real production Railway failure or crash after deploy is recorded, dispatched and triaged; no synthetic production failure |
| R9 | 7 consecutive clean days before switch-off; post-switch-off INAPP-only verification |

Review: Tier 3 (monitoring fail-closed envelope + account-token use): full panel GLM, DeepSeek, CC in Gemini seat per d50cbd80. MP builds; Mars verifies. Deploy watcher changes through the existing issue-channel-watcher path; load the launchd job per `titan-1.md`; health-check change ships through the backend PR path.

## 5. Risks

- Railway event and notification schemas are undocumented: fail closed (observation incomplete, parity run failed), never silently skip.
- Crash storms: correlation folds per subject and day, Railway sub-cap 2 per day, excess stays recorded.
- Titan-1 offline: parity record goes stale; the GitHub health check reports it; emails stay on until 7 clean days, and after switch-off the 24-hour rule reopens them.
