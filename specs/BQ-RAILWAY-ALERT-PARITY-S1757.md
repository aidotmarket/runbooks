# BQ-RAILWAY-ALERT-PARITY-S1757 — every Railway email reaches the issue channel and is triaged

Status: combined Gate 1/Gate 2 spec, proposed. Owner: Mars. Entity: `build:bq-railway-alert-parity-s1757`.
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

- `koskadeux_mcp/issue_channel/adapters/railway.py`: add one read-only GraphQL query `RailwayProjectEvents(projectId, first, after, filter action in ["crashed","failed"], object in ["Deployment"])`, paginated newest-first with the existing ordering/lookback guards (`_deployments` pattern) and the existing `history_lookback`. Same `Project-Access-Token` header and token. The adapter keeps sending queries only; add a test that every GraphQL document it can send starts with `query` and matches an allowlist of operation names.
- Each event yields a `RawEnvelope`: kind `deploy_crash` (action `crashed`) or `deploy_failure` (action `failed`); subject `railway:<project>/<environment>/<service>` (same as today); `native_id` `<project>/<environment>/<service>/<deployment>/event:<event id>`; fields: event id, deployment id, environment id/name, production flag, severity, created_at. Service/deployment ids come from the event payload; if the payload lacks them, resolve through `deployment(id)`; if still unresolved, emit with subject `railway:<project>/<environment>/unknown-service` rather than dropping it.
- Dedup: a failed deployment already recorded by the status poll and its `failed` event must correlate to the same episode (same subject, kind, UTC day, deployment id member). Tests cover: status-then-event, event-only (crash with restart), watcher self-crash seen after restart within lookback, pagination boundary, events with missing ids, non-production classification.
- First build check (before any other code): prove with the watcher's project token, read-only, that `events` returns the 10-27 Sep crash/failed events. If it does not, stop and report; do not add a broader token.
- Coverage marker: `sources.railway` expected/observed resources gain `<project>:events`; an events read failure makes the observation incomplete exactly like a deployments failure.

### 3.2 Dispatch rule

`config/issue_channel/dispatch_rules.yaml`: add `railway-production-deploy-live-v1` matching provider `railway`, kinds `deploy_failure` and `deploy_crash`, environment class `production`, subject prefix `railway:ai-market/production/`, action `dispatch_codex`; keep `default_action: record_only`. Shared existing caps (per run $3/8 turns/600 s; UTC day 4 dispatches/$12) apply to the combined GitHub + Railway lane; one dispatch per episode, never per event. The worker input gains only allowlisted sanitized Railway fields (service, environment, status, event action, deployment id, timestamps); no logs, no variables.

### 3.3 Titan-1 parity job (koskadeux-mcp)

- New `scripts/railway_alert_parity.py` + launchd job `com.koskadeux.railway-alert-parity` (every 15 minutes; daily summary at 06:45 UTC). Token: the existing account-scoped Titan-1 token `titan-1-koskadeux`, obtained exactly as `titan-1.md` prescribes (`source ~/bin/railway-env.sh`, `RAILWAY_TOKEN` unset). Whether the watcher's Infisical `RAILWAY_API_TOKEN` is the same value or a separate project token is **UNVERIFIED**; the build must prove by names/scope checks (never by printing values) that the watcher keeps a project-scoped token and that the account token is used only by this job; never logged, never written to disk by the job, never sent anywhere but `backboard.railway.com`. Queries only (same allowlist test).
- Each run reads `notificationDeliveries(filter:{type: EMAIL})` newest-first over the last 8 days, grouping deliveries by `notificationInstance.id`.
- Match rule: for `Deployment.crashed` / `Deployment.failed` in project `ai-market`, the instance's `resourceId` (deployment id) must appear as a member/native id of an issue-channel record (read-only query on `issue_channel.canonical_issues` with the existing read role, or the safe snapshot mirror if it proves complete). Any other instance (other projects, `UsageAlert.*`, `Volume*`, `ServiceInstance.*`, unknown) is not expected in the watcher and is filed as a support ticket (existing support-ticket API, idempotent on the instance id) with event type, severity, project/service/environment names and time only.
- Unmatched `ai-market` deployment instances older than 30 minutes are parity misses: file a support ticket (idempotent) and count a miss.
- Output: Living State `infra:railway-alert-parity` (sole writer: this job) with window, counts by type, matched, ticketed, misses, last run, last success; a stale record (>1 h) is itself surfaced by the existing issue poller as a stale-job issue. Daily Event Ledger entry `railway-alert-parity-daily`.
- Clean day = every run of the UTC day succeeded, zero misses, every non-watcher instance ticketed.

### 3.4 Email switch-off

After 7 consecutive clean days, record the evidence on the entity, then switch Railway email notifications off for Max's account (Railway account notification settings, in-app kept on). Prefer the Railway notification settings API if a documented mutation exists; otherwise ask Max to toggle it in the Railway dashboard (one click; exact path recorded). Verify: next Railway notification appears in `notificationDeliveries` as `INAPP` only and in the issue channel. Update `issue-channel.md` (sources, dispatch boundary, parity job, email switch-off and how to turn it back on).

## 4. Acceptance

| ID | Evidence |
|---|---|
| R1 | Project-token `events` read proof (first build check) |
| R2 | Adapter tests §3.1 incl. self-crash-after-restart and dedup with status poll |
| R3 | Rule tests: production failure/crash dispatch once per episode; non-production and other projects record_only; caps shared |
| R4 | Parity job tests with recorded GraphQL fixtures: match, miss, ticket idempotency, non-deployment types, pagination, API failure = run failed (never "clean") |
| R5 | Live: first real production Railway failure or crash after deploy is recorded, dispatched and triaged (report present); no synthetic production failure is created |
| R6 | 7 consecutive clean parity days in `infra:railway-alert-parity` before email switch-off |
| R7 | Backfill run over 2026-09-20..27 reproduces the §1 table (5 watcher crashes and usage alerts ticketed, failures matched) |

Review: Tier 3 (monitoring fail-closed envelope + account-token use): full panel GLM, DeepSeek, CC in Gemini seat per d50cbd80. MP builds; Mars verifies. Deploy watcher changes through the existing issue-channel-watcher path; load the launchd job per `titan-1.md`.

## 5. Risks

- Railway event schema is undocumented: fail closed (observation incomplete, parity run failed), never silently skip.
- Crash storms: one dispatch per episode plus existing daily caps; excess stays recorded.
- Titan-1 offline: parity record goes stale and is surfaced; emails stay on until 7 clean days, so no gap before switch-off. After switch-off, a stale parity record for >24 h must reopen email notifications (documented manual step).
