---
title: Issue Channel
owner: mars
last_verified: '2026-08-30'
aliases:
- infrastructure failure channel
- CI health board
- issue channel watcher
- issue channel poller
error_signatures:
- 'observation_complete":false'
- executor_busy_no_lease
- malformed_output
- expired_unleased
- outcome_unknown
- candidate_invalid
- fallback_waiting_resolution
- duplicate_cardinality
- support_reconciliation_deadline
- support_deadline_unavailable
---

# Issue Channel

## What it does

The active Railway `issue-channel-watcher` service permits one replica. It reads GitHub, Railway, and Cloudflare, sanitizes provider data before persistence, stores canonical issues in the backend Postgres `issue_channel` schema, and publishes a safe snapshot. The snapshot is mirrored to `/Users/max/koskadeux-state/issue-channel/snapshot.json` for local operations and the open-items board.

Provider observations are the sole authority for whether an issue exists and whether it is resolved. A partial, unavailable, untrusted, or unordered observation never resolves an episode. Absence from a lookback window, expiry, timeout, and worker text are not success witnesses.

The watcher collects and resolves issues even when dispatch, the local worker, or the support API is unavailable. Keep the Railway service at one replica; the singleton guard deliberately rejects a second replica.

## Live dispatch boundary

The live rule table is `config/issue_channel/dispatch_rules.yaml`:

- Mode is `live` and the default action is `record_only`.
- Only GitHub `ci_failure` for `aidotmarket/ai-market-backend` matches `ci-failure-main-single-repo-live-v1` and dispatches Codex.
- `default-record-only-v1` remains the catch-all. All other observations are collected without worker dispatch.
- One run is capped at $3, 8 turns, and 600 seconds.
- UTC-day caps are 4 dispatches and $12 measured cost.
- The lease is 660 seconds. Queue TTL is 1020 seconds.
- The completion POST has a 45-second wall deadline and a 64,000-byte response cap. Its phase timeouts do not replace the wall deadline.

The worker is metadata-only triage. Its bounded input contains the canonical public issue, matching and admission summaries, short runbook excerpts, and allowlisted sanitized provider evidence. The Claude process receives an explicit empty `--allowedTools` and runs in an empty `TemporaryDirectory` outside every repository. This execution boundary, not prompt text, prevents tool and repository access. It receives no logs or code unless that material is explicitly present in the safe input fields.

The only accepted provider result is strict JSON with exactly these top-level fields:

```json
{"closed_exit":"triaged","triage_report":{"summary":"...","probable_cause":"...","recommended_next_step":"...","confidence":"low","evidence_refs":[],"runbook_refs":[]}}
```

`closed_exit` may be `triaged`, `resolved_with_evidence`, or `needs_max`. Missing, extra, coerced, malformed, oversized, or unsafe fields become `failed` with `malformed_output`. The system does not invent cost, duration, turns, or a report to make a failed result look complete.

A triage report is a bounded, sanitized annotation. It is never resolution authority. `needs_max` must include a decision request and is only for an authority, security, payment, or customer-data decision, or proven ladder exhaustion. Ordinary severity is not enough.

## Canonical persistence

Persistence may fold a newly observed candidate into an existing canonical issue or resolve it through an alias. The runner must therefore discard the candidate's provisional identity after persistence and use the returned `CanonicalIssue` for fingerprint, episode, evaluation, journaling, admission, dispatch context, and every idempotency key. Folded and aliased identities are supported only through that authoritative returned projection.

Before any support mutation, validate that the admission episode is nonempty, the exact canonical row exists, its episode matches the admission episode, and its state is one of `open`, `expired`, or `resolved`. An absent canonical projection, an empty episode, or any identity or episode mismatch is terminal `candidate_invalid`. Journal the safe fault, make zero support calls, and leave collection and snapshot publication independent.

## Ticket lifecycle

There is exactly one ops support ticket per canonical episode. Its `source_ref` is the stable SHA-256-derived reference for the `episode_key` under the fixed issue-channel ticket namespace. It does not include the automated-triage reason, so a changing reason cannot create a second ticket for the same episode.

The watcher first journals ticket create or patch intent in `dispatch_intents.sanitized_context.ticket_handoff`, then calls the internal support API. It always reconciles by exact `source_ref`:

- Zero matching tickets permits one create.
- One matching ticket is reused.
- More than one is `duplicate_cardinality` and fails loud.
- An unknown create or patch outcome is re-queried on the next watcher tick. Never blind-retry in the same tick.
- `needs_max` reuses the same ticket and sets `human_required=true`.

A support API outage is nonfatal to provider collection, canonical resolution, and snapshot publication.

An `outcome_unknown` or `expired_unleased` intent without an accepted triage report still needs a durable operator surface. The watcher emits one bounded, low-confidence safe fallback ticket for the authoritative episode `source_ref` and journals phase `fallback_waiting_resolution`. Repeated watcher cycles reconcile and reuse that exact ticket instead of duplicating it. The candidate becomes selectable again only after canonical resolution so the same ticket can advance to its terminal handoff. Fallback ticket work never blocks provider collection or snapshot publication.

Each watcher tick selects at most 20 recoverable nonterminal support candidates from the database, ordered by `updated_at`, `created_at`, and `id`. Journaling an attempted row moves it behind untouched rows so later candidates continue to progress. The terminal phases `candidate_invalid`, `human_required_no_close`, `needs_max_complete`, and `resolved_complete` are excluded.

A 45-second monotonic total deadline wraps only the synchronous support calls in that bounded pass. On POSIX it uses `ITIMER_REAL`, restores the prior signal handler and timer, and uses no threads. On exhaustion it records `support_reconciliation_deadline`, stops support work promptly, retains later candidates for the next tick, and continues to snapshot publication below the 300-second cadence. If the process cannot install that deadline safely, it records `support_deadline_unavailable` and makes no synchronous support calls in that pass.

Only a complete provider-success witness resolves the canonical episode. Then, and only then, the watcher may auto-resolve the linked ticket when `human_required` is exactly the boolean `false`. Boolean `true`, null, missing, strings, numbers, and malformed values are never treated as false; they park safely without a close call. The watcher never closes a ticket from worker text, a partial observation, absence, expiry, or timeout.

The central backend `update_support_ticket` operation owns lifecycle timestamps. It row-locks the ticket; stamps server `resolved_at` or `closed_at` only on a genuine transition; preserves `resolved_at` across `resolved` to `closed`; leaves timestamps unchanged on a repeated terminal status; and clears both timestamps on a terminal-to-nonterminal reopen while preserving the existing probe reset. It honors an explicit `resolved_at` or `resolution_source` and never invents a `resolution_source`. The uncommon `closed` to `resolved` reversal is not specially normalized; treat it as a product-policy decision instead of guessing or expanding this runbook into a support state-machine specification.

## Snapshot telemetry

Snapshot `mode` is the actual dispatch-rule mode. `collection_mode` and `default_action` remain `record_only`. `action_counts` reports the current bounded watcher pass and separates support mutation attempts from admitted worker dispatches; it is not a historical total. `dispatch_spend` remains the separate admission and measured-spend view.

Daily admission caps and reservations use the intent `utc_day`, which is the admission day. Snapshot `completed_count` and completion-cost UTC-day metrics instead use `completed_at`, or `late_completion_at` for late completions. Around midnight, a bounded run admitted and reserved on one UTC day can complete and be reported on the next. Never use completion-day reporting as cap accounting: it can include prior-day admissions and exclude current-day reservations that have not completed.

## Access and identities

Refer to credentials and identities by name only. Never paste or log their values.

- `ISSUE_CHANNEL_POLLER_KEY` authenticates the outbound local poller to the queue API.
- `INTERNAL_API_KEY` authenticates watcher calls to the internal support API.
- Provider inputs include `ISSUE_CHANNEL_GITHUB_TOKEN`, `RAILWAY_API_TOKEN`, `ISSUE_CHANNEL_CLOUDFLARE_TOKEN`, and `CLOUDFLARE_ACCOUNT_ID`.
- Watcher database access uses `ISSUE_CHANNEL_WATCHER_DATABASE_URL` and database role `issue_channel_watcher`.
- Poller database access uses its dedicated database role `issue_channel_poller`.

Use Railway variable references on `issue-channel-watcher` so the service consumes the managed production variables without copied values. Provider credentials stay read-only and least-privileged: GitHub repository metadata and Actions reads, Railway reads, and Cloudflare reads. Do not give the local poller provider credentials or the watcher a broader support identity.

## Normal health check

Confirm the newest watcher deployment is successful and read its current logs from the linked Railway project:

```sh
railway deployment list -s issue-channel-watcher --json
railway logs -s issue-channel-watcher
```

Confirm GitHub workflow state and recent `main` runs:

```sh
gh workflow list --repo aidotmarket/ai-market-backend --all
gh run list --repo aidotmarket/ai-market-backend --branch main --limit 30
```

Read the safe local mirror. A healthy mirror is fresh, shows every source complete, and agrees with database status counts:

```sh
jq '{generated_at,mode:.snapshot.mode,collection_mode:.snapshot.collection_mode,default_action:.snapshot.default_action,action_counts:.snapshot.action_counts,open_count:.snapshot.open_count,expired_count:.snapshot.expired_count,sources:(.snapshot.sources|map_values(.observation_complete)),dispatch_spend:.snapshot.dispatch_spend,breaker:.snapshot.breaker}' /Users/max/koskadeux-state/issue-channel/snapshot.json
```

Read watcher deploys and logs in Railway, workflow definitions and runs in GitHub Actions, and the safe snapshot at the local mirror path above. Do not use worker output or the mirror alone as provider authority.

An ai.market `EMERGENCY LOCAL FALLBACK` banner alone can mean the local connector or client path failed; it is not proof that the shared gateway or database failed. Independently inspect the local connector process and configured path, run `kd status`, issue one small read-only gateway command, and run a read-only database `SELECT`. If the database or the real gateway is unreachable, stop production operations. Never use the local fallback as a production-operation bypass.

## Diagnose detection

Start with the source entry in the mirror. Compare `expected_resources` with `observed_resources`, check `error_class`, and determine which provider read is incomplete. Then inspect the matching provider directly.

For a GitHub CI episode, enumerate active workflows and recent `main` runs. Confirm the workflow identity, conclusion, head branch, and timestamps. A successful read with no history is an observed `no_history` witness; a failed or untrusted read is incomplete.

```sh
gh workflow list --repo aidotmarket/ai-market-backend --all --json id,name,path,state
gh run list --repo aidotmarket/ai-market-backend --branch main --limit 100 --json databaseId,workflowDatabaseId,workflowName,status,conclusion,createdAt,headSha,url
```

For Railway or Cloudflare, use the provider console or read-only API identity named above. Do not infer provider health from the watcher process being alive.

## Inspect queue, intents, spend, and breaker

Run the read-only SQL in this runbook through an authorized `psql` session. Check recent intents before changing a rule or retrying anything. `queued`, `leased`, and `outcome_unknown` are open intent states. `expired_unleased`, `completed`, and `late_completion` are terminal journal states.

The breaker opens on its reviewed failure-rate or flap thresholds and opens immediately for forced faults such as digest mismatch or measured cost above budget. An open breaker blocks new admission but does not stop provider collection or resolution. Do not reset it until the underlying journal evidence is understood.

## Diagnose malformed output

Find the intent with `fault_code`, `closed_exit`, and `ticket_handoff`, then correlate its timestamp with the local poller log and backend queue logs. `malformed_output` means the strict worker result failed validation; it is not a triage result and creates no trustworthy report or measurements.

Verify the output had exactly `closed_exit` and `triage_report`, the closed exit was allowed, the report had its exact bounded fields, `decision_request` appeared only for `needs_max`, all values were strict types, and sanitization and size checks passed. Repair the producer or contract-compatible parser and add a focused fixture. Never patch the row into a successful completion.

## Reconcile a missing or duplicate ticket

Read `sanitized_context.ticket_handoff` to obtain the exact `source_ref`, phase, error code, and linked `public_ref`. Query the internal support-ticket list operation by that exact `source_ref`; do not search by title.

If the result is zero and the phase is `create_unknown`, restore the support API and let the next watcher tick re-query before it creates. Do not issue a same-tick manual create. If the result is one, reuse it and allow the watcher to advance the handoff. If the result is more than one, preserve both records, stop automatic mutation for that episode, and escalate the duplicate-cardinality fault to the support owner. Do not guess which ticket to delete.

## Handle needs_max

Confirm the stored report contains a bounded `decision_request` and that the reason is authority, security, payment, customer data, or proven ladder exhaustion. Confirm the same episode ticket has `human_required=true`. The ticket is the decision surface; do not create a second ticket and do not auto-close it after provider recovery.

If ordinary CI severity produced `needs_max`, treat the result as a contract defect. Correct the worker prompt or validation with focused tests rather than accepting severity as authority.

## Verify provider-success resolution

For GitHub CI, a success witness must come from the same workflow and `main`, and its `created_at` must be strictly newer than the failure. The observation containing that witness must be complete. Confirm the canonical episode then has `status='resolved'` and a `resolved_at` timestamp.

Only after those facts are true should the same linked ticket with `human_required` exactly boolean `false` reach `resolved`. Every other representation parks safe even though the canonical episode resolved. Verify terminal ticket status and lifecycle timestamps together; `resolution_source` is optional under current semantics.

## Deployment order and rollback

Backend integration PR #311 merged as `e16f205fe59cd9c56fb4482e4b85e2e1f114c22e` and was first deployed successfully in Railway deployment `8e99939f-aa07-48eb-bd6c-9259d16c7ea4`; that deployment is now superseded and removed. PR #311 is included in the current active backend deployment `b73fa943-ad43-4c65-8c75-29f609936094`. The database Alembic head is `t2026_000727_provider_num_turns`, post-rollout provider-turn residue is zero, and the exact backend verification passed 117 tests.

The watcher base PR #207 merged as `b435068161f3dcaa9421c0c84e0a344b9c769490`; final canary hotfix PR #209 merged as `e26ebeffc2ccaf66a2f0cb6f5626f0271e8b4ccd`. Railway deployment `ff27a413-4bed-4656-bbcd-a984255fe177` is the active successful watcher. The exact issue-channel suite passed 425 tests and the final candidate received full CC, Kimi, and GLM approval.

Support-ticket lifecycle PR #314 merged as `0610c160af8ee6c6ee0422eaccb687656ea0aafb` and is active in Railway deployment `b73fa943-ad43-4c65-8c75-29f609936094`. Its focused lifecycle tests passed 8 tests and the relevant support slice passed 64. Merge workflows were green: Role Authority Lint `33326601922`, Site Smoke `33326601911`, Gold Path `33326601925`, Alembic Guardrails `33326601895`, and Dependency Drift `33326601893`.

Use backend-first expand/contract whenever the queue contract changes:

1. Deploy the backend migration and tolerant backend application first. `provider_num_turns` is nullable and is initially backfilled from retained `turns`.
2. Verify the backend accepts legacy `turns`, canonical `provider_num_turns`, or equal dual fields. Contradictory dual fields must reject. New backend writes both columns.
3. Deploy `issue-channel-watcher` only after the backend and migration are healthy.
4. Keep issue-channel email enabled throughout dual coverage.
5. After every old backend image has stopped, run the migration's documented post-rollout reconciliation so canonical-null, legacy-nonnull rows receive `provider_num_turns=turns`.
6. Run the read-only residue query below and prove zero before proposing any later contract migration.

Never drop `turns` in this change. A future drop requires a separate reviewed change after zero residue is proven.

For rollback, roll the watcher back first to the prior successful image; the tolerant backend continues to accept its legacy completion shape. Keep the expanded backend column and retained `turns` in place. Roll the backend application back only to an image compatible with both retained fields. Do not use schema rollback as an incident response.

Kill switches are narrow:

- Set `dispatch_enabled: false` in `config/issue_channel/policy.yaml` to stop new worker dispatch while collection and resolution continue.
- Change only the explicit CI rule to `record_only` to disable that lane while retaining the live catch-all.
- Roll back `issue-channel-watcher` to the last successful Railway deployment for a watcher regression.

Do not disable email during dual coverage. Do not stop collection merely because the support API, worker, or local mirror is unhealthy.

## Live canary and cleanup

The authorized canary used stable workflow ID `345908153`. Failure run `33314116206` was created at `2026-08-30T13:24:57Z` and completed with the deliberate failure at `13:25:05Z`. It produced canonical issue `iss_01M19DKMF3R7DD2JA1BHX8QZHQ` for episode `aidotmarket/ai-market-backend|ci_failure|2026-08-30|2`.

The episode admitted exactly one intent, `04275df4-bc5d-4de5-b844-81841d8b2003`. It ended `outcome_unknown`; the breaker sample was `failed`; and the journal recorded `lease_expiry`. Before any lease, the watcher performed the guarded authoritative-episode repair. The deployed fallback then created exactly one ops ticket, `T-2026-000731`, with `human_required=false` and phase `fallback_waiting_resolution`.

Newer same-workflow `main` run `33324876164` was created at `2026-08-30T17:18:11Z` and completed successfully at `17:18:20Z`. The complete watcher observation at `2026-08-30T17:18:52.390720Z` resolved the canonical episode and ticket and advanced the handoff to `resolved_complete`. Later database proof still showed exactly one canonical issue, one intent, and one ticket. Email remained enabled throughout.

Production proof exposed a pre-existing central-backend inconsistency: ticket status was `resolved` while `resolved_at` was null. After full Council review and the PR #314 deployment above, exact canary ticket `T-2026-000731` was repaired once with guarded SQL using canonical `resolved_at` `2026-08-30T17:18:45.30817Z`. Exactly one row changed, and `resolution_source` intentionally remains null.

Cleanup PR #313 merged as `5eb4d992b4b253c048ac03a6b0962febb0fcd437` and removed only `.github/workflows/issue-channel-canary.yml`. All merge workflows were green: Site Smoke `33326033562`, Dependency Drift `33326033541`, Alembic Guardrails `33326033578`, and Gold Path `33326033569`. The workflow no longer exists.

A future deliberate canary requires fresh explicit authorization and a separately reviewed temporary workflow. Before running it, prove a green provider baseline, one complete watcher observation, and zero open or expired matching episodes. Dispatch exactly one failure, inspect an unknown outcome instead of retrying, then use one strictly newer success from the same workflow and `main`. Remove the temporary workflow only after complete observation proves canonical and eligible-ticket resolution, and wait for all cleanup-merge workflows to turn green.

## Read-only SQL

Connect with an authorized read-only identity. These queries contain no credentials and make no changes.

Status counts:

```sql
SELECT status, count(*) AS episodes
FROM issue_channel.canonical_issues
GROUP BY status
ORDER BY status;
```

Exact canary preflight for open or expired GitHub CI episodes:

```sql
SELECT id, episode_key, status, opened_at, resolved_at
FROM issue_channel.canonical_issues
WHERE provider = 'github'
  AND subject = 'aidotmarket/ai-market-backend'
  AND kind = 'ci_failure'
  AND status IN ('open', 'expired')
ORDER BY opened_at;
```

Recent intents, including canonical and legacy turns:

```sql
SELECT id,
       created_at,
       updated_at,
       status,
       measured_cost_usd,
       provider_num_turns,
       turns AS legacy_turns,
       closed_exit,
       fault_code
FROM issue_channel.dispatch_intents
ORDER BY created_at DESC
LIMIT 50;
```

Ticket handoff journal:

```sql
SELECT id,
       status,
       sanitized_context -> 'admission' ->> 'episode_key' AS episode_key,
       sanitized_context -> 'ticket_handoff' AS ticket_handoff,
       updated_at
FROM issue_channel.dispatch_intents
WHERE sanitized_context ? 'ticket_handoff'
ORDER BY updated_at DESC
LIMIT 50;
```

Exact canary cardinality and lifecycle:

```sql
SELECT id, episode_key, status, resolved_at
FROM issue_channel.canonical_issues
WHERE episode_key = 'aidotmarket/ai-market-backend|ci_failure|2026-08-30|2';

SELECT id,
       status,
       fault_code,
       sanitized_context -> 'ticket_handoff' AS ticket_handoff
FROM issue_channel.dispatch_intents
WHERE sanitized_context -> 'admission' ->> 'episode_key'
      = 'aidotmarket/ai-market-backend|ci_failure|2026-08-30|2';

SELECT public_ref,
       payload->>'source_ref' AS source_ref,
       status,
       human_required,
       human_required IS FALSE AS auto_close_eligible,
       resolved_at,
       closed_at,
       resolution_source,
       CASE
         WHEN status = 'resolved' THEN resolved_at IS NOT NULL
         WHEN status = 'closed' THEN resolved_at IS NOT NULL AND closed_at IS NOT NULL
         ELSE resolved_at IS NULL AND closed_at IS NULL
       END AS lifecycle_coherent
FROM support_ticket
WHERE payload->>'source_ref' = (
  SELECT sanitized_context -> 'ticket_handoff' ->> 'source_ref'
  FROM issue_channel.dispatch_intents
  WHERE id = '04275df4-bc5d-4de5-b844-81841d8b2003'
);
```

Each query must return exactly one row and the IDs must be `iss_01M19DKMF3R7DD2JA1BHX8QZHQ`, `04275df4-bc5d-4de5-b844-81841d8b2003`, and `T-2026-000731`. A resolved or closed ticket needs the corresponding server timestamp; a reopened nonterminal ticket needs both lifecycle timestamps cleared. Treat `resolution_source` as optional and do not backfill or invent it merely because it is null.

Completion-day measured spend in UTC:

```sql
SELECT count(*) AS completed_count_utc_day,
       coalesce(sum(measured_cost_usd), 0) AS completed_cost_usd_utc_day
FROM issue_channel.dispatch_intents
WHERE (status = 'completed'
       AND completed_at >= date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
       AND completed_at < (date_trunc('day', now() AT TIME ZONE 'UTC') + interval '1 day') AT TIME ZONE 'UTC')
   OR (status = 'late_completion'
       AND late_completion_at >= date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
       AND late_completion_at < (date_trunc('day', now() AT TIME ZONE 'UTC') + interval '1 day') AT TIME ZONE 'UTC');
```

Provider-turn residue after post-rollout reconciliation:

```sql
SELECT count(*) AS provider_turn_residue
FROM issue_channel.dispatch_intents
WHERE provider_num_turns IS NULL
  AND turns IS NOT NULL;
```

## Maintenance map

In `aidotmarket/ai-market-backend`, the queue and migration contract lives in:

- `alembic/versions/20260826_001_issue_channel_schema_and_queue.py`
- `alembic/versions/20260830_001_provider_num_turns.py`
- `app/models/issue_channel.py`
- `app/api/v1/issue_channel_queue.py`
- `app/services/issue_channel_queue.py`
- `app/api/v1/endpoints/support.py`
- `app/services/support_ticket_service.py`

Focused backend tests are `tests/test_issue_channel_provider_num_turns_migration.py`, `tests/test_issue_channel_migration.py`, `tests/test_issue_channel_queue_api.py`, `tests/test_issue_channel_queue_service.py`, and `tests/test_support_ticket_s811_c2.py`. Ticket lifecycle behavior is maintained in `app/api/v1/endpoints/support.py`, `app/services/support_ticket_service.py`, and their focused support tests; do not reimplement it in the watcher.

In `aidotmarket/koskadeux-mcp`, the watcher and local poller live in:

- `scripts/issue_channel.py` and `scripts/issue_channel_poller.py`
- `deploy/issue-channel-watcher/Dockerfile` and `deploy/issue-channel-watcher/railway.toml`
- `config/issue_channel/sources.yaml`, `policy.yaml`, and `dispatch_rules.yaml`
- `koskadeux_mcp/issue_channel/adapters/`
- `koskadeux_mcp/issue_channel/runner.py`, `sanitize.py`, `normalize.py`, `storage.py`, and `resolution.py`
- `koskadeux_mcp/issue_channel/dispatch.py`, `journal.py`, `breaker.py`, `workers.py`, `triage.py`, `escalate.py`, and `poller.py`
- `claude_code_client.py` and `tools/support_ticket.py`

Focused watcher coverage is under `tests/issue_channel/`, especially `test_github_adapter.py`, `test_railway_adapter.py`, `test_cloudflare_adapter.py`, `test_resolution.py`, `test_admission_db.py`, `test_dispatch_context.py`, `test_workers.py`, `test_triage_report.py`, `test_escalate.py`, `test_poller.py`, `test_breaker.py`, and `test_cloud_singleton_service_definition.py`. Board rendering is covered by `tests/test_open_items_channel_segment.py`; support-tool behavior by `tests/unit/test_support_ticket_tool.py`.

For a safe update, use an MP build on a fresh branch, run the focused tests independently, and send the exact candidate through full CC, Kimi, and GLM review. If a backend contract changes, deploy backend-first. Then obtain live provider, database, Railway, snapshot, and eligible-ticket proof. Update `last_verified` only after that proof.

## When it breaks

### Observation incomplete

Symptom: a source has `observation_complete=false`, and episodes do not resolve.

Likely cause: an expected workflow, service, or zone was not observed; the provider read failed; or ordering could not be trusted.

Verify: compare expected and observed resources in the mirror, inspect `error_class`, then query the provider directly with its read-only identity.

Repair or rollback: restore provider access or add the verified resource shape with adapter tests. Roll back the watcher if a new adapter caused the gap. Never mark the observation complete by hand.

### executor_busy_no_lease

Symptom: the poller reports `executor_busy_no_lease` and no intent is leased.

Likely cause: the dedicated executor profile is held by another authorized task. This is normal for a bounded period.

Verify: inspect the local poller log and confirm the intent remains `queued`; compare its age with the 1020-second queue TTL.

Repair or rollback: let the holder finish. If the condition would outlive TTL, repair the stuck executor owner before the next tick. Do not take a lease first and do not run a second worker profile.

### malformed_output

Symptom: an intent fails with `malformed_output`, with no trusted closed exit or report.

Likely cause: missing or extra fields, type coercion, invalid `needs_max` shape, unsafe content, or size overflow.

Verify: inspect `fault_code`, the poller timestamp, and validation logs; compare the result with the exact two-field contract.

Repair or rollback: fix the worker producer or compatible validator and add the failing fixture. Do not fabricate measurements, a report, or success fields.

### candidate_invalid

Symptom: support reconciliation parks an intent at terminal phase `candidate_invalid` and makes no support call.

Likely cause: the persisted canonical projection is absent, the admission episode is empty, the exact canonical row is missing, or the canonical and admission episodes disagree.

Verify: compare the returned `CanonicalIssue`, admission episode, exact database row, and canonical state. Confirm later evaluation, journal, context, and idempotency fields all use the returned canonical identity rather than the provisional candidate.

Repair or rollback: repair the persistence projection or identity handoff and add the folded or aliased case to focused tests. Never patch around the check or mutate support from a mismatched candidate.

### expired_unleased or outcome_unknown

Symptom: an intent is `expired_unleased` or `outcome_unknown`.

Likely cause: no lease before 1020 seconds, or a lease expired without an accepted completion.

Verify: inspect `created_at`, `leased_at`, `lease_expires_at`, `reservation_released_at`, `fault_code`, breaker sample fields, and whether an accepted triage report exists. If no report was accepted, verify one exact episode `source_ref` and handoff phase `fallback_waiting_resolution`.

Repair or rollback: fix the executor, transport, or backend before new admission. Reconcile unknown outcomes from the journal; never blind-retry a worker that may have run. Let the deterministic fallback provide the low-confidence operator surface while collection and snapshot publication continue.

### Fallback ticket absent

Symptom: an `outcome_unknown` or `expired_unleased` intent without an accepted report has no linked fallback ticket.

Likely cause: missing `INTERNAL_API_KEY`, support API outage, terminal `candidate_invalid`, or an unknown create outcome.

Verify: read `ticket_handoff`, prove phase `fallback_waiting_resolution` when a mutation was attempted, query the exact authoritative-episode `source_ref`, and inspect watcher logs for the safe error code.

Repair or rollback: restore the named support identity or API, then let the next tick re-query and create only if the exact count is still zero. Collection and resolution remain live.

### Fallback ticket duplicated

Symptom: exact authoritative-episode `source_ref` reconciliation returns more than one fallback ticket and records `duplicate_cardinality`.

Likely cause: an earlier blind or concurrent create bypassed the single-ticket ladder.

Verify: list tickets by exact `source_ref` and retain every `public_ref` and timestamp.

Repair or rollback: stop automatic ticket mutation for the episode and have the support owner reconcile the duplicates. Do not delete or choose a winner from title similarity.

### support_reconciliation_deadline

Symptom: a bounded pass records `support_reconciliation_deadline`; later support candidates remain untouched while provider collection and snapshot publication continue.

Likely cause: one or more synchronous support calls consumed the 45-second total deadline.

Verify: inspect the ordered candidate IDs, handoff phases, attempted-row journal timestamps, support latency, and snapshot publication time. Confirm no more than 20 candidates were selected and the snapshot still published below the 300-second cadence.

Repair or rollback: restore support API latency or availability and let the next tick resume retained candidates in database order. Do not extend the deadline, start threads, or blind-retry an unknown mutation.

### support_deadline_unavailable

Symptom: a bounded pass records `support_deadline_unavailable` and makes no synchronous support calls while collection and snapshot publication continue.

Likely cause: the process could not safely install the POSIX `ITIMER_REAL` deadline or preserve the existing signal state.

Verify: inspect the runtime platform, main-thread signal context, prior handler and timer state, and watcher error code. Confirm candidate rows were retained without mutation attempts.

Repair or rollback: restore the supported POSIX main-thread execution environment or roll back the watcher image. Do not bypass the fail-closed boundary with an unbounded call or a thread.

### Ticket will not close

Symptom: the canonical episode is resolved but its linked ticket remains open.

Likely cause: `human_required` is not exactly boolean `false`, provider resolution is incomplete, the support API is unavailable, or the patch outcome is unknown.

Verify: prove complete provider success, canonical `status='resolved'`, exact linked `public_ref`, ticket status, the stored type and value of `human_required`, and ticket handoff phase. Null, missing, string, number, malformed, and boolean `true` values must all park safe.

Repair or rollback: correct the producer of an invalid `human_required` value; do not coerce it in the watcher. For exact boolean `false`, restore the support API and let the next tick reconcile the patch. Never close from worker text.

### Lifecycle timestamp inconsistency

Symptom: ticket status is `resolved` with null `resolved_at`, `closed` without both terminal timestamps, a reopened ticket retains terminal timestamps, or repeat terminal updates move timestamps.

Likely cause: a caller bypassed the deployed central transition semantics, historical data predates PR #314, or an uncommon `closed` to `resolved` reversal needs a product-policy decision.

Verify: run the ticket lifecycle query above and inspect status, `resolved_at`, `closed_at`, and optional `resolution_source` together. Compare the canonical `resolved_at` before proposing any repair.

Repair or rollback: use the central update path for normal transitions. Historical repair requires separately authorized guarded SQL with an exact row predicate and expected count. Do not invent `resolution_source` or guess how `closed` to `resolved` should behave.

### needs_max

Symptom: the ticket is marked human-required and will not auto-close.

Likely cause: a valid authority, security, payment, customer-data, or ladder-exhaustion decision request; or a worker contract defect.

Verify: inspect the bounded decision request and evidence refs. Confirm ordinary severity was not the reason.

Repair or rollback: route a valid request to the human authority on the same ticket. For an invalid request, repair the worker and tests; never clear `human_required` merely to enable auto-close.

### Spend cap or breaker open

Symptom: new dispatch is refused with a daily cap or `breaker_open` while collection continues.

Likely cause: 4 runs or $12 committed for the UTC day, failure-rate or flap threshold, digest mismatch, or measured cost above budget.

Verify: inspect intent `utc_day`, admission reservations, and admitted-count or committed-cost evidence for the capped day. Use the completion-day query only for reporting, and inspect breaker reasons in the mirror.

Repair or rollback: wait for the UTC-day reset when the cap is genuine. For a breaker, repair the underlying journal or transport fault and follow the reviewed manual-reset path. Never erase spend or fault rows.

### Stale snapshot

Symptom: the mirror is older than two 300-second watcher cadences or disagrees with database counts.

Likely cause: watcher deployment failure, mirror poller failure, queue API outage, or a local atomic-mirror problem.

Verify: compare mirror `generated_at`, Railway deployment time, watcher logs, queue snapshot response, and database status counts.

Repair or rollback: restore the failing watcher or mirror component and wait for a fresh complete snapshot. Do not treat a stale mirror as provider authority.

### Missing INTERNAL_API_KEY

Symptom: support ticket list, create, get, or patch fails authentication while provider state still advances.

Likely cause: the watcher lacks the Railway variable reference for `INTERNAL_API_KEY`, or it points at the wrong environment.

Verify: inspect variable names and references on `issue-channel-watcher` without printing values; confirm the backend internal support route uses the same named production identity.

Repair or rollback: restore the correct Railway variable reference and least privilege, then let the next tick reconcile exact `source_ref`. Do not copy the value into logs or the runbook.

### Legacy and canonical turn contradiction

Symptom: the backend rejects a completion carrying unequal `turns` and `provider_num_turns`.

Likely cause: a mixed-version caller sent contradictory dual fields.

Verify: inspect the request field names and the intent's retained columns without logging credentials or unsafe context.

Repair or rollback: fix the caller to send legacy only, canonical only, or equal dual. Keep the tolerant backend deployed and never overwrite contradictory history or drop `turns`.

### EMERGENCY LOCAL FALLBACK banner

Symptom: ai.market shows `EMERGENCY LOCAL FALLBACK` and an operator suspects a shared gateway or database outage.

Likely cause: the local connector process, configured path, or client route failed while the shared services remained healthy.

Verify: independently inspect the local connector process and path, run `kd status`, issue a small read-only gateway command, and execute a read-only database `SELECT`. Do not infer one result from another.

Repair or rollback: repair the local client path only when gateway and database checks are healthy. If the database or true gateway is unreachable, stop production operations; never use local fallback as a production bypass.

### Canary cleanup or recreation

Symptom: workflow ID `345908153` still appears after cleanup, the removal merge workflows are not all green, or someone proposes reusing the deleted canary.

Likely cause: PR #313 cleanup did not reach the inspected revision, the workflow cache or query is stale, or a new deliberate canary lacks fresh authorization and review.

Verify: confirm `.github/workflows/issue-channel-canary.yml` is absent at current `main`, the workflow no longer exists, and runs `33326033562`, `33326033541`, `33326033578`, and `33326033569` are green. Preserve the completed canary's exact one-canonical, one-intent, one-ticket proof.

Repair or rollback: do not recreate or dispatch the deleted workflow. A future deliberate canary requires fresh explicit authorization and a separately reviewed temporary workflow, followed by the same failure, newer-success, complete-observation, resolution, and cleanup sequence.
