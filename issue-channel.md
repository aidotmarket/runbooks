---
title: Issue Channel
owner: mars
last_verified: '2026-10-04'
aliases:
- infrastructure failure channel
- CI health board
- issue channel watcher
- issue channel poller
error_signatures:
- 'observation_complete":false'
- 'Cannot redeploy yet, please wait for the original deployment to finish building'
- executor_busy_no_lease
- malformed_output
- expired_unleased
- outcome_unknown
- candidate_invalid
- fallback_waiting_resolution
- duplicate_cardinality
- support_reconciliation_deadline
- support_deadline_unavailable
- apiTokens node incomplete
- fresh healthy watcher mirror cycle unproved
- attributable Infisical sync jobs unproved
- Railway project, environment, or service discovery failed
---

# Issue Channel

## What it does

The active Railway `issue-channel-watcher` service permits one replica. It reads GitHub, Railway, Cloudflare, and Council-provider consumption (DeepSeek balance; see Council provider consumption for limits), sanitizes provider data before persistence, stores canonical issues in the backend Postgres `issue_channel` schema, and publishes a safe snapshot. The snapshot is mirrored to `/Users/max/koskadeux-state/issue-channel/snapshot.json` for local operations and the open-items board.

**Current panel (Max `d0a534e6`, 2026-10-01):** the current panel is GLM, DeepSeek and codex2, unanimous; CC is non-voting; Gemini is not dispatched. See `runbooks/council.md` CURRENT PANEL. The d50cbd80 package and tiering rules below still apply; its CC roster does not. **Earlier override (Max S1738, `d50cbd80`, 2026-09-25 to 2026-10-05):** Gemini is not dispatched for any review; CC holds its third voting seat alongside GLM and DeepSeek, with unanimity required. Apply the option A package standard and option C tiering and raiser-only fold re-review in [runbooks/council.md ACTIVE OVERRIDE](runbooks/council.md#overview) to any older roster or dispatch wording below.

Provider observations are the sole authority for whether an issue exists and whether it is resolved. A partial, unavailable, untrusted, or unordered observation never resolves an episode. Absence from a lookback window, expiry, timeout, and worker text are not success witnesses.

The watcher collects and resolves issues even when dispatch, the local worker, or the support API is unavailable. Keep the Railway service at one replica; the singleton guard deliberately rejects a second replica.

The Koskadeux `com.koskadeux.issue-channel-poller` runs every 300 seconds. Since koskadeux-mcp PR #234, it sends one high-priority peer message to both Mars and Vulcan when an `issue-channel:` ticket is non-terminal, unclaimed by an active instance, and older than 60 minutes. It deduplicates alerts for six hours in `/Users/max/koskadeux-state/issue-channel/unowned-alerts.json` and never notifies Max. A crash between sending and writing dedupe state can repeat one alert.

## Live dispatch boundary

The live rule table is `config/issue_channel/dispatch_rules.yaml`:

- Mode is `live` and the default action is `record_only`.
- Only GitHub `ci_failure` for `aidotmarket/ai-market-backend` matches `ci-failure-main-single-repo-live-v1` and dispatches Codex.
- `default-record-only-v1` is the GitHub record-only rule. The top-level `default_action: record_only` is the true catch-all, so every observation not matched for dispatch is collected without worker dispatch.
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

There is exactly one ops support ticket per canonical episode. Its `source_ref` is the stable SHA-256-derived reference for the `episode_key` under the fixed issue-channel ticket namespace. The implementation uses the fixed `AUTOMATED_TRIAGE_REASON` namespace label; no variable triage reason participates in the hash, so changing triage text cannot create a second ticket for the same episode.

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

The `github`, `railway`, `cloudflare`, and `council_providers` entries under `sources` are independent provider-health observations. Diagnose each provider's `status`, `observation_complete`, resources, and error independently; one provider's result does not summarize or erase another provider's state.

### Expired history on the open-items board (S1760 staged companion)

The canonical `expired` rows remain stored and visible for audit. Expiry is not resolution, provider recovery or permission to delete. [MCP PR 276](https://github.com/aidotmarket/koskadeux-mcp/pull/276), exact source `245b1a8471c6bb13a04ccb51c49ec6a0b98cdd2d` on `build/s1760-expired-history-projection` over `df8d1de4590f1f0e2f8b966d8b89632dc1be79b6`, exports `episode_key` from the nonempty canonical database column rather than stale `safe_metadata` JSON. It preserves stored metadata, status and `resolved_at`; no deduplication, deletion, SQL hand repair or provider action follows. The original competing catalogue patch was removed: original `df8`-to-final catalogue delta is zero. Runtime and tests equal qualified `f3b429a7`. The existing `CanonicalIssue` persistence contract still governs folded and aliased identities. Private PostgreSQL checks proved canonical export and byte preservation, not production database repair.

The optional `channel.expired_projection` has version 1. Unknown has exactly `schema_version: 1` and `state: "unknown"`. Known has exactly those two fields plus `total`, `consolidated_history`, `needs_disposition` and `continuing_limitation_count`, with `total = consolidated_history + needs_disposition`. Known requires a snapshot no more than 600 seconds old and **all four** expected provider entries, `github`, `railway`, `cloudflare` and `council_providers`, each `status: ok` and `observation_complete` exactly boolean `true`. Missing any expected entry; any malformed, unhealthy or incomplete entry, including an extra such as `watcher`; a stale or future snapshot; or invalid identity, counters, state/status or timezone-aware ordered times returns closed unknown, never known zero. A healthy, well-formed extra does not by itself invalidate a complete snapshot. A complete healthy empty snapshot can be known zero. Consolidated history additionally requires whole reciprocal link proof: older expired GLM `provider_usage_unavailable` rows must link to a continuing open row with reverse exact aliases and earlier target first-seen time. A structurally valid but unproved link stays in known `needs_disposition`, not global unknown. The dated 27-row fixture had 25 proven retained GLM aliases, two expired rows with unproved disposition and one continuing usage-observation limitation. Those 25 are not repairs or proof of provider recovery. Exact qualified PR276 runtime passed 89 channel and 103 identity/stage checks, including a corrected missing-each-provider counterexample.

The original mirror observation had 120 rows: 91 resolved, 27 expired and two open, including a duplicated exported `episode_key` in two resolved GitHub rows; the database-column cause was not directly inspected. At 2026-09-28 11:54:13Z the mirror had 122 rows (92 resolved, 27 expired, three open), one duplicate exported key and a synthetic `sources.watcher` marker for `admission:idempotency_duplicate`. At 13:04:44Z all four provider entries were `ok` and complete, with two open (vectoraiz August 27 CI and the known GLM usage-observation limitation), 27 expired and backend episode 9 resolved. T886 database resolution was recorded at 13:03:59Z, without exact actor or autonomous-repair attribution. These dated observations are not current counts. Watcher source `5a8` and Railway deployment `6a1d3be2-fca9-4f3a-b020-722814a0069d` were the independently checked identities then; `1b805` and the 11:54 marker are historical. That deployment did not activate PR 276.

[Ops PR 39](https://github.com/aidotmarket/ops-ai-market/pull/39), exact final staged source `5de4799e2a2be31670f313c93099795e2f327cd9`, shows explicit `true` as verified indexed coverage, explicit `false` as unverified and missing/null/malformed evidence as unknown; a discovery link proves neither coverage nor completion. It keeps unknown, inconsistent and stale status visible and retains the raw expired warning when an older producer omits the optional field. Source stale, manual-reset, breaker and spend states retain their UI priority. Its initial and manual board loads and existing default 30-second Needs You poll set the displayed clock when each fetch completes, including rejected fetches; this makes evidence older than 600 seconds unknown. A request that never settles does not advance the clock. There is no production 10-second interval; the test override `10` is 10 milliseconds. It changes no row hiding, filter, deletion, Needs You action, API or auth contract. At final `5de4799e`, independent checks passed 75 focused panel tests, changed-file ESLint, `npm run build`, diff check and clean-worktree check on Node v25.3.0. Final CI 36435525785 and 36435519427 succeeded at lint, not application typecheck. The earlier root `tsc --noEmit` pass checked an empty project-reference root, not the application. `tsc --noEmit -p tsconfig.app.json` reports the same 48 error lines at `2fab13c8` and `5de4799e`, with no new or removed error lines. Separately, exact status type definitions and all five actual valid fixture literals compile without casts under strict TypeScript. The type-only fold changes `src/types/index.ts` and five valid test fixture casts; the runtime panel and all production callers are byte-identical to `2fab13c8`. The bounded status type accepts the base status, optional expiry, then optional singular or plural dispatch-spend suffix, without an unbounded string catchall. These checks do not establish a full application typecheck or whole-suite pass. Diagnose persistent unknown from the canonical source and complete mirror through normal review; retain all rows and history. Roll back producer or UI through normal source delivery if a delivered candidate regresses. Do not clear health, override a breaker or edit a snapshot to force a known count.

### Council provider consumption

`sources.council_providers` is enabled in `config/issue_channel/sources.yaml` and remains under the catch-all `default_action: record_only`; it has no dispatch rule. **Deployment (S1651, Option A, Max decision 9921bea3): LIVE on the Railway `issue-channel-watcher` since deployment a6e9d746 (koskadeux-mcp main 8ae7ebe03d, 2026-09-02 16:18Z).** The watcher CMD selects `council_providers`; `DEEPSEEK_API_KEY` is a literal service variable on the watcher (same practice as its database URLs; re-point it if the key rotates). First live snapshot 2026-09-02T16:19Z carried `provider_balance/deepseek`, `provider_usage_unavailable/glm`, and `builder_timeout_count/mp`. Kimi's launcher, credential, and issue-channel health source are removed under S1721; no current poll scans Kimi logs or emits Kimi usage/quota issues. The Railway watcher still cannot see Koskadeux MP job reports, so the MP count is 0 there; a local run has no persistence path (`ISSUE_CHANNEL_WATCHER_DATABASE_URL` is absent on Koskadeux) and is not scheduled. Each poll reads DeepSeek's authenticated balance with a timeout of at most 10 seconds, records that the repository has no documented read-only GLM coding-plan usage endpoint, and counts MP timeout reports modified in the last 24 hours. It emits `provider_balance` and, when warranted, `provider_exhaustion_projected` for DeepSeek; `provider_usage_unavailable` for GLM; and `builder_timeout_count` for MP. A failed subject check emits `provider_check_failed` rather than aborting the other checks.

DeepSeek balance history uses the channel's existing safe raw storage and loads at most the configured `sample_limit` from the last seven days. Burn rate is `(oldest USD balance - newest USD balance) / elapsed days`. `provider_exhaustion_projected` appears when projected days to zero is below `warn_days` (default 7) or current balance is below `warn_usd` (default USD 10).

Read the latest values from the mirrored snapshot:

```sh
jq '.snapshot.issues[] | select(.source.provider == "council_providers") | {kind,subject,payload,first_seen,last_seen}' /Users/max/koskadeux-state/issue-channel/snapshot.json
```

For an authorized offline export, run `scripts/issue_channel.py --export-corpus <directory>`, select `council_providers` rows in `issues.json`, then follow each `raw_ref`; its safe `projection` contains the same observation payload. Neither surface contains the DeepSeek credential.

`sources.watcher` is different: it is a synthetic watcher-control failure marker, written fail-closed for current policy, table, meter, or admission-control failures. [MCP PR 280](https://github.com/aidotmarket/koskadeux-mcp/pull/280), exact source `2b6bd8f8860915427796e8b2e83db3a0efc2378a` on `build/s1760-duplicate-admission-health`, distinguishes only admission-stage reasons exactly equal to `idempotency_duplicate`, `episode_already_open` or `correlation_already_open`. These expected duplicates refuse dispatch and retain the refusal count plus `issue_channel_admission_duplicate` log marker without creating a synthetic storage outage, second intent, reservation or provider dispatch. Classification uses exact values, never substrings. Genuine policy, table, meter, capacity, breaker, storage, malformed or unknown refusals remain unhealthy and sticky within a mixed pass; a later duplicate cannot reset them. Only a completed normal control cycle removes the exact stale synthetic watcher marker. Provider health stays independent, and provider errors are retained. This candidate changes no admission authority, caps, breaker, reservations or schema. Partial or unavailable providers still require separate diagnosis even if the synthetic marker clears.

At the 2026-09-28 author checkpoint, PRs 276 and 280, classifier/catalogue [PR 279](https://github.com/aidotmarket/koskadeux-mcp/pull/279) source `2870f11ebacc3f4c96e0ce890e9bc0c3ce81df35`, Ops PR 39 and this operating companion were staged, unmerged and unactivated. A clean Git-generated temporary combination from MCP main `5a8a0198` used PR276 `245b1a84`, PR279's previous `23a5fc81` catalogue and PR280 `2b6bd8f8`, without moving refs or releasing. It passed 89 channel, 122 identity/stage and 17 duplicate-health tests (228 total, zero skips/failures), Ruff and diff check. A separate guarded private Unix PostgreSQL cluster passed 15 selected cases with zero skips/failures and was stopped; the 17 marker tests separately include seven private PostgreSQL cases. The final temporary Git-generated combination `f99472165031e9f3b340f1104bc566c60e0a21f4` (tree `1bf201f980f5bb58b5f9724ff77dfd80b279d976`) used exact PR279 `2870f11e` with PR276 `245b1a84` and PR280 `2b6bd8f8` from main `5a8a0198`. Against the earlier 228-plus-15-tested combination `a685720f6c76a6337a7857d9de11092fa55b3416`, only the independently qualified catalogue `about` string changed; all other blobs are identical. The final combination separately passed 24 project-identity tests with zero skips/failures, diff check and a clean-worktree check; it did not rerun all 243 earlier cases. No refs moved and no source was authored or provider/production calls made for that temporary combination. Standalone PR280 passed 17 corrected marker tests and two private Railway status/events admission cases. These are scoped checks, not platform acceptance. At the 2026-09-28 review checkpoint, all five original exact source artifacts received full valid CC APPROVE_WITH_NITS, replacement DeepSeek APPROVE_WITH_NITS and GLM APPROVE_WITH_MANDATES; the original incomplete DeepSeek response was excluded. GLM's UI type mandate was independently verified to the bounded scope above. This polling and test-scope runbook correction remains for controller independent verification. Under the active `d50cbd80`/S1570 stopping rule, no new design change or full-panel retry is required for a locally verifiable mandate. This companion candidate is not controller-verified yet. Normal merge/deploy and sole-publisher supported DB GET plus authenticated-browser acceptance remain pending. PR277 is accepted design only; source trust, certificate implementation and positive completion remain incomplete. Keep the historical `last_verified` value until live proof.

Daily admission caps and reservations use the intent `utc_day`, which is the admission day. Snapshot `completed_count` and completion-cost UTC-day metrics instead use `completed_at`, or `late_completion_at` for late completions. Around midnight, a bounded run admitted and reserved on one UTC day can complete and be reported on the next. Never use completion-day reporting as cap accounting: it can include prior-day admissions and exclude current-day reservations that have not completed.

## Access and identities

Refer to credentials and identities by name only. Never paste or log their values.

- `ISSUE_CHANNEL_POLLER_KEY` authenticates the outbound local poller to the queue API.
- `INTERNAL_API_KEY` authenticates watcher calls to the internal support API.
- Provider inputs include `ISSUE_CHANNEL_GITHUB_TOKEN`, `RAILWAY_API_TOKEN`, `ISSUE_CHANNEL_RAILWAY_EVENTS_TOKEN` (events only; see below), `ISSUE_CHANNEL_CLOUDFLARE_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, and the launcher-injected `DEEPSEEK_API_KEY`.
- Watcher database access uses `ISSUE_CHANNEL_WATCHER_DATABASE_URL` and database role `issue_channel_watcher`.
- In backend source, the queue API uses `ISSUE_CHANNEL_QUEUE_DATABASE_URL` with dedicated database role `issue_channel_queue_api`; the outbound local poller authenticates to that HTTP API with `ISSUE_CHANNEL_POLLER_KEY`.

The cited source does not define either dedicated database role as read-only. **SOURCE evidence, not a check of current production grants:** backend commit `9bcf6affa9b713882d1a2c7aea68fc710b4a619c` declares `issue_channel_watcher` and `issue_channel_queue_api` as the dedicated roles in [migration lines 22-25](https://github.com/aidotmarket/ai-market-backend/blob/9bcf6affa9b713882d1a2c7aea68fc710b4a619c/alembic/versions/20260826_001_issue_channel_schema_and_queue.py#L22-L25). [Migration lines 442-455](https://github.com/aidotmarket/ai-market-backend/blob/9bcf6affa9b713882d1a2c7aea68fc710b4a619c/alembic/versions/20260826_001_issue_channel_schema_and_queue.py#L442-L455) grant the watcher `SELECT`, `INSERT`, `UPDATE`, and `DELETE` across `issue_channel` tables; they grant the queue API role `SELECT` on `safe_snapshot_records` and `SELECT`, `INSERT`, and `UPDATE` on `dispatch_intents`. The [queue API](https://github.com/aidotmarket/ai-market-backend/blob/9bcf6affa9b713882d1a2c7aea68fc710b4a619c/app/api/v1/issue_channel_queue.py#L40-L83) checks the poller HTTP key, while the [queue service](https://github.com/aidotmarket/ai-market-backend/blob/9bcf6affa9b713882d1a2c7aea68fc710b4a619c/app/services/issue_channel_queue.py#L391-L404) checks the dedicated database role. The legacy `scripts/issue_channel_operate.sh` obtains `ISSUE_CHANNEL_WATCHER_DATABASE_URL`, so its queries use writer credentials. It is not the approved read-only operator verification path; do not source it for that purpose. `railway_alert_parity_read` is limited to `source_records(id, provider)` and `safe_raw_records(source_record_id, redacted_projection)` and must not be broadened or reused for `dispatch_intents`.

Use Railway variable references on `issue-channel-watcher` so the service consumes the managed production variables without copied values. Provider credentials stay read-only and least-privileged: GitHub repository metadata and Actions reads, Railway project-token reads, and Cloudflare reads. The one exception is `ISSUE_CHANNEL_RAILWAY_EVENTS_TOKEN`: Railway has no read-only token scope, so it is a workspace-wide token that can change anything in the workspace if stolen (accepted by Max, Event `477a5087`); the watcher adapter uses it for the events query only (query-only allowlist in `RailwayProjectEvents`, live since 2026-09-28; see the status paragraph below). Do not give the local poller provider credentials or the watcher a broader support identity.

## Railway events credential (watcher)

The watcher is to read Railway project `events` (Deployment crashed/failed) with a dedicated workspace token, because its project token is refused on `events` (Events `4982f9e3`, `477a5087`; spec `specs/BQ-RAILWAY-ALERT-PARITY-S1757.md` §3.1). Railway tokens have no read-only scope: this token can change anything in the workspace if stolen. Max accepted that risk (Event `477a5087`). The watcher code must use it only for `RailwayProjectEvents`.

Status (2026-09-28, Mars S1758): the events adapter is live. `RailwayProjectEvents` merged in koskadeux-mcp PR #278 as `5a8a0198ae9624dc4084fffb6bb2c585202083ac` (Gate 3 GLM, DeepSeek, CC in the Gemini seat per `d50cbd80`; folds re-reviewed by raisers). Watcher deployment `6a1d3be2-fca9-4f3a-b020-722814a0069d` reached `SUCCESS` at 11:35Z. The first mirror cycle after it showed `ai-market:<project>:events` in both `expected_resources` and `observed_resources` of `sources.railway`, with `status` `ok` and `observation_complete` `true`, and the events path recorded the 2026-09-27 watcher `CRASHED` deployment. Railway emails stay on until the parity job (spec §3.3, installed 2026-09-28, see [Railway alert parity job (Koskadeux)](#railway-alert-parity-job-koskadeux)) shows 7 clean days (§3.4).

To check events coverage, run `jq '.snapshot.sources.railway | {status, observation_complete, events: (.observed_resources | map(select(endswith(":events"))))}' /Users/max/koskadeux-state/issue-channel/snapshot.json`: expect `status` `ok`, `observation_complete` `true` and `ai-market:e81dd66f-808c-412e-b32c-f6d910f0ac5d:events` listed. This is Railway-source coverage only; check `.snapshot.sources.watcher` separately for overall watcher health. A recognized crash or failure event that cannot be resolved to a known service or deployment marks the observation incomplete by design.

Credential state (provisioned and verified 2026-09-28 by Mars S1758, receipts on entity `build:bq-railway-alert-parity-s1757` `body.credential_receipts`):

- Railway workspace token `issue-channel-watcher-events-s1757`, Railway token id `e8a6632c-c262-4ea5-b726-62ecf7d61247`, workspace `f44bd0d7-5739-411d-9876-aec715294eef` ("maxrobbins's Projects").
- Stored only as `ISSUE_CHANNEL_RAILWAY_EVENTS_TOKEN` in Infisical project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, `prod`, folder `/issue-channel-watcher-railway`.
- Native sync `railway-issue-channel-watcher-events-prod`: that folder only, non-recursive, to Railway `issue-channel-watcher` (`d48dd44c-4541-4387-89da-50b2b1d0c8fe`) only; auto-sync on; initial behaviour `overwrite-destination`; `disableSecretDeletion: true`. A canary proved the folder is outside the root `railway-backend-prod` sync (root sync job `18e19f0f-1719-40da-814d-f62efa9b786e`).
- Any Infisical `prod` write can now trigger three syncs (root -> `ai-market-backend`, `/connector-auth` -> `ai-market-connector-auth`, `/issue-channel-watcher-railway` -> `issue-channel-watcher`). Never write to `/issue-channel-watcher-railway` except through the controller below. See [infisical-secrets.md](infisical-secrets.md).

The only supported tool is the reviewed controller `scripts/railway_watcher_credential/railway_watcher_credential.py` in `aidotmarket/koskadeux-mcp` (operator procedure: `docs/railway-watcher-events-credential-s1757.md` in that repo). Run it on Koskadeux from a detached checkout of current `main` with `/Users/max/koskadeux-mcp/venv/bin/python`, after `source ~/bin/railway-env.sh` and `unset RAILWAY_TOKEN`, and `~/bin/infisical_auth_refresh.sh >/dev/null 2>&1`. Every command is a dry run unless `--execute` is given; never run `--execute` as a build or review check. It refuses while `/Users/max/local-secops/HALT` exists and writes a redacted append-only receipt to `~/koskadeux-state/secrets/railway_watcher_credential.audit.jsonl`.

Commands: `--selftest` (offline), `preflight`, `canary`, `create-sync`, `mint-and-store`, `verify`, `reconcile`, `recover-mint`, `revoke`. For a credential check, run `verify` (read-only). `VERIFIED` does not prove the token is authorized to read Railway `events` or that parity works; that is proven separately by the spec's first-build events probe and by the watcher's `sources.railway` events coverage marker once the adapter is live. `VERIFIED` means the token id still exists in the workspace, the folder holds only the named secret, all three sync scopes are correct, all per-key digests are equal, the three deployments are `SUCCESS`, both health endpoints return 200 and the watcher mirror is healthy.

### Watcher deployment stuck in BUILDING

Seen 2026-09-28: after a `koskadeux-mcp` merge, watcher deployment `56ccb11f-a3e3-479c-bd0a-6209ed8cbecf` stayed `BUILDING` for 25 minutes at the pip install step while Railway status was fully operational (normal builds finish in about 2 minutes). The previous `SUCCESS` deployment keeps serving meanwhile. `deploymentRedeploy` on a building deployment fails with `Cannot redeploy yet, please wait for the original deployment to finish building`.

Recover only when a watcher deployment has been `BUILDING` for more than 15 minutes and its build log shows no progress. Use the account token from `~/bin/railway-env.sh` with `RAILWAY_TOKEN` unset, POST to `https://backboard.railway.app/graphql/v2` with headers `Authorization: Bearer $RAILWAY_API_TOKEN`, `Content-Type: application/json` and a browser `User-Agent` (Cloudflare blocks the default), and never print the token.

1. Announce on the peer bus that you are redeploying `issue-channel-watcher` and ask peers to hold `koskadeux-mcp` `main` merges until you post the result.
2. Record the preconditions: `railway deployment list -s issue-channel-watcher --json` shows the stuck deployment id and its commit, and the previous `SUCCESS` deployment id; `git ls-remote https://github.com/aidotmarket/koskadeux-mcp main` equals the stuck deployment's commit. If `main` has moved, deploy the new `main` SHA instead, and say so in the announcement.
3. Send once: `{"query":"mutation{deploymentCancel(id:\"<stuck id>\")}"}`. Expect `true`, then confirm with the deployment list that it is `REMOVED`. If the response is lost or unclear, re-read the list; do not send the cancel again until it shows the deployment still `BUILDING`.
4. Send once: `{"query":"mutation{serviceInstanceDeployV2(serviceId:\"d48dd44c-4541-4387-89da-50b2b1d0c8fe\",environmentId:\"23e322c3-b195-45d8-9151-c4c27a998c33\",commitSha:\"<SHA from step 2>\")}"}`. Keep the returned deployment id. If the response is lost, look in the deployment list for a new deployment of that commit created after step 3 and use its id; never send a second deploy while one exists.
5. Poll the deployment list until that id is `SUCCESS` with the commit. If it fails or sticks again, stop: the previous `SUCCESS` deployment has been superseded, so redeploy that previous deployment (`mutation{deploymentRedeploy(id:"<previous SUCCESS id>"){id status}}`), read the build log, and escalate rather than repeating the cycle.
6. Wait one watcher cycle, run the mirror check in [Normal health check](#normal-health-check) and the events-coverage check in [Railway events credential (watcher)](#railway-events-credential-watcher), then post the deployment id, commit and result to peers (this releases the merge hold) and record them on the owning build entity.

### Credential controller: executing a step

Before any `--execute`:

1. Announce a production write window on the peer bus. Ask peers not to write Infisical `prod`, change Railway variables, deploy `ai-market-backend`, `ai-market-connector-auth` or `issue-channel-watcher`, or merge to `koskadeux-mcp` `main`. Every `koskadeux-mcp` merge redeploys `issue-channel-watcher`; while that deployment is building the controller refuses with `Railway project, environment, or service discovery failed`. Wait for the watcher deployment to reach `SUCCESS` and rerun. Offer a safe pause between steps for peers' merges.
2. Run the dry run of the step, then `--execute` in the background with output to a file. Each mutation waits for sync jobs, deployments, both health endpoints and a fresh watcher mirror cycle (up to 15 minutes; the watcher publishes about every 6 minutes and the Koskadeux poller copies it every 5), so one step can take 5-20 minutes.
3. Record each step's receipt on the BQ entity and announce the window closed.

Revocation and uncertain-mint recovery follow the controller's operator procedure exactly; there is no rotation path. A replacement is revoke, then a fresh preflight and mint. If a mint outcome is uncertain, never mint again until `recover-mint` proves the name absent.

Known live refusals and meaning:

- `apiTokens node incomplete`: an `apiTokens` row lacks an id or name (account-scoped tokens with a null `workspaceId` are accepted since PR #271).
- `fresh healthy watcher mirror cycle unproved`: no new healthy watcher mirror within 15 minutes after the mutation; check the watcher deployment and snapshot freshness before retrying.
- `attributable Infisical sync jobs unproved`: the expected sync job did not complete; stop, record it, and do not relax the check without review.

<a id="railway-alert-parity-job-titan-1"></a><a id="railway-alert-parity-job-koskadeux"></a>

### Railway alert parity job (Koskadeux)

Installed 2026-09-28 by Mars S1762 (spec §3.3; koskadeux-mcp PR #281 merged as `7b482d0e9189b5dd07fc156f7133ae17472522e1`; operator procedure `docs/railway-alert-parity-job-s1758.md` in that repo). Every 15 minutes it reads Railway's own notification deliveries (EMAIL and INAPP), checks that every production `Deployment.crashed` or `Deployment.failed` was also observed by the watcher, opens an `ops` ticket for each miss older than 30 minutes and for each notification the watcher does not cover (for example `UsageAlert.triggered`, Railway spend warnings), and publishes `infra:railway-alert-parity` plus one `railway-alert-parity-daily` Event Ledger entry per UTC day. A day is clean only when all 96 slots ran successfully with zero misses and nothing pending. Railway emails stay on until 7 consecutive clean UTC days (§3.4).

Installed pieces:

- launchd `com.koskadeux.railway-alert-parity` (`~/Library/LaunchAgents/com.koskadeux.railway-alert-parity.plist`, `StartCalendarInterval` at minutes 2, 17, 32 and 47 of every hour, `RunAtLoad`; koskadeux-mcp PR #304), running `scripts/run_railway_alert_parity.sh` from the `/Users/max/koskadeux-mcp` checkout. Log: `~/Library/Logs/koskadeux/railway-alert-parity.log` (one JSON line per run). Lock and cursor: `~/koskadeux-state/railway-alert-parity/`.
- Loader `~/bin/railway-alert-parity-env.sh` (mode 0700): exports `RAILWAY_ALERT_PARITY_DATABASE_URL` and `INTERNAL_API_KEY` from Infisical with the SysAdmin identity and prints no values. The role password is `RAILWAY_ALERT_PARITY_DB_PASSWORD` in Infisical project koskadeux-mcp (`0943f641-faee-4324-b337-0d50c276e4a9`), `prod`, root; this project has no Railway sync. The DSN host is the Postgres public proxy `shuttle.proxy.rlwy.net:50727`, database `railway`; if Railway moves the proxy, update the loader.
- Database role `railway_alert_parity_read` in the backend Postgres (`railway`): LOGIN, NOINHERIT, no superuser/createrole/createdb/bypassrls, SELECT only on `issue_channel.source_records(id, provider)` and `issue_channel.safe_raw_records(source_record_id, redacted_projection)`; a write probe returns `permission denied`. Index `issue_channel.ix_issue_channel_safe_raw_deployment_id` (valid).
- Independent freshness monitor: backend Daily Health Check `railway_alert_parity` (see [backend-daily-health-check.md](backend-daily-health-check.md)).

Check it:

```sh
launchctl print gui/$(id -u)/com.koskadeux.railway-alert-parity | grep -E "runs|last exit"
tail -5 ~/Library/Logs/koskadeux/railway-alert-parity.log
```

Then read `infra:railway-alert-parity` (`last_success` within 2 hours, `clean_days`) and open tickets whose subject starts `Railway notification`. To rotate the role password, first pause the job (`launchctl bootout gui/$(id -u)/com.koskadeux.railway-alert-parity`), generate a new value into the Infisical secret above, `ALTER ROLE railway_alert_parity_read PASSWORD` with that value through psql stdin (never argv), run the launcher once by hand, and bootstrap the job again (`launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.koskadeux.railway-alert-parity.plist"`).

First run (2026-09-28 14:53Z, backfill from 2026-09-20): 11 notifications, 8 matched deployments including all four `ai-market-backend` FAILED deployments of 2026-09-25/26 (`3251e66d`, `a59bb8c2`, `3bee73b3`, `11f9f679`). One true historical miss, T-2026-000887: the watcher's own crash of 2026-09-21 (deployment `6e81689b`), which it could not see before the events adapter went live; resolved. Two usage alerts (T-2026-000888, T-2026-000889) resolved as informational.

Retries (koskadeux-mcp PR #314, merged 2026-10-01 as `c51a5d2a`): the launcher tries both loaders, `railway-env.sh` and `railway-alert-parity-env.sh`, up to 3 times, 20 seconds apart, refreshing Infisical auth in between. An attempt counts only if `RAILWAY_API_TOKEN`, `RAILWAY_ALERT_PARITY_DATABASE_URL` and `INTERNAL_API_KEY` are all non-empty afterwards; `railway-env.sh` returns 0 even when its fetch fails. The Railway query is tried up to 5 times (waiting 5s, 15s, 60s, then 150s; koskadeux-mcp PR #319, `0c6f3e41`, after slot 2026-10-01 23:15Z failed all 3 earlier attempts) on transport errors, 429/5xx, bad JSON or GraphQL `errors`; any other 4xx and a malformed page fail at once. Each retry writes one redacted line to the log, `{"status": "retry", "code": "railway_query_retry", "attempt": N, "reason": ...}`, where the reason is only a class such as `http_503`, `transport:ConnectTimeout`, `graphql_errors` or `bad_json`; read these lines first when a slot fails. The retry budget is per query, so a run with several flaky pages can still hit the 660-second supervisor and end as `parity_run_timeout`. A supervisor kills the whole run after 660 seconds with `{"status": "failed", "code": "parity_run_timeout"}`, so a run always ends inside its 15-minute slot. Seen 2026-09-30: the day was unclean only because three runs failed with `railway_query_failed` (15:00Z, then 18:45Z and 19:00Z back to back), and because the loader failed right after a Titan-1 macOS reboot at about 07:41Z, which left slot 07:45Z without an attempt. A reboot or logout still loses the slots in which no user session is running (launchd user agents run only while the user is logged in). Check `last reboot` when a slot is missing.

Living State (koskadeux-mcp PR #336, `4e8fac52`): reads and writes of `infra:railway-alert-parity` are tried up to 4 times (waiting 5, 15 and 20s), with a redacted `{"status": "retry", "code": "state_retry", "attempt": N, "op": "read|write"}` line before each retry. If the very first state read still fails, the run now records a failed attempt row for its slot before exiting, so a slot is never silently missing. A `version_conflict` on write fails at once. Seen 2026-10-03: slot 07:45Z failed and slot 11:00Z had no row, both `state_read_failed` from brief backend unavailability; those two runs made no Railway query retries. If `state_read_failed` or `state_write_failed` still appears after four tries, check backend health and any backend deploy at that time.

When it breaks: the log line is `{"status": "failed", "code": "<code>"}` and the run exits nonzero; the next slot retries from the persisted cursor. `railway_query_failed` means the Railway GraphQL call errored or returned `errors`; one isolated failure was seen at install and the next run succeeded. Repeated failures: run the launcher by hand in a minimal environment (`env -i HOME=$HOME PATH=/usr/bin:/bin /bin/zsh /Users/max/koskadeux-mcp/scripts/run_railway_alert_parity.sh`) and check `~/bin/railway-env.sh`. A day that is not clean although every attempt that day succeeded with zero misses and nothing pending means a slot had no run. Count the attempts per slot for that day in `~/koskadeux-state/railway-alert-parity/progress.json` (list `attempts`, key `slot`) against the 96 expected slots. Seen 2026-09-29: all 94 runs that day succeeded with zero misses and nothing pending, but slots 08:00Z and 20:45Z had no attempt, because `StartInterval` 900 is not wall-clock aligned and the run time drifted across slot boundaries. It was fixed by the calendar schedule above (koskadeux-mcp PR #304). If slots go missing again, check `launchctl print gui/$(id -u)/com.koskadeux.railway-alert-parity` and confirm the installed plist in `~/Library/LaunchAgents/` matches the repo copy. To reinstall: `launchctl bootout gui/$(id -u)/com.koskadeux.railway-alert-parity`, copy the plist from the `/Users/max/koskadeux-mcp` checkout into `~/Library/LaunchAgents/`, then run `launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.koskadeux.railway-alert-parity.plist"`. `parity_database_dsn_missing`: the loader did not resolve a secret; run `~/bin/infisical_auth_refresh.sh` and source the loader by hand. Ticket or state failures: check the backend and `INTERNAL_API_KEY`.

## Normal health check

At every instance check-in, start with open `issue-channel:` tickets and the snapshot's open issues. Claim a ticket with `support_ticket_patch` using `ownership_action=claim`, or resolve it with evidence; do not leave an unowned fallback ticket waiting for the next alert.

GitHub Actions failure email is not an operator signal for Max. His GitHub Settings → Notifications → Actions is set to "on GitHub" only for failed workflows, with no email. Use the issue channel and provider evidence for detection and diagnosis.

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

Read the safe local mirror. A healthy normal cycle is fresh, agrees with database status counts, has provider keys `github`, `railway`, `cloudflare`, and `council_providers` with each provider `status` equal to `ok` and `observation_complete` equal to `true`, and has no synthetic `watcher` marker. If `sources.watcher` is present, diagnose that control marker separately from the provider entries:

```sh
jq '{generated_at,mode:.snapshot.mode,collection_mode:.snapshot.collection_mode,default_action:.snapshot.default_action,action_counts:.snapshot.action_counts,open_count:.snapshot.open_count,expired_count:.snapshot.expired_count,source_keys:(.snapshot.sources|keys),sources:(.snapshot.sources|map_values({status,observation_complete,last_attempt,error_class,detail_code})),dispatch_spend:.snapshot.dispatch_spend,breaker:.snapshot.breaker}' /Users/max/koskadeux-state/issue-channel/snapshot.json
```

Read watcher deploys and logs in Railway, workflow definitions and runs in GitHub Actions, and the safe snapshot at the local mirror path above. Do not use worker output or the mirror alone as provider authority.

An ai.market `EMERGENCY LOCAL FALLBACK` banner alone can mean the local connector or client path failed; it is not proof that the shared gateway or database failed. Independently inspect the local connector process and configured path, run `kd status`, issue one small read-only gateway command, and run a read-only database `SELECT`. If the database or the real gateway is unreachable, stop production operations. Never use the local fallback as a production-operation bypass.

## Diagnose detection

Start with the source entry in the mirror. For `github`, `railway`, or `cloudflare`, compare `expected_resources` with `observed_resources`, check `error_class`, and determine which provider read is incomplete. Then inspect the matching provider directly. If the entry is the synthetic `watcher` marker, use its control-failure details and the stale-marker procedure under `When it breaks`; do not treat it as provider health.

For a GitHub CI episode, enumerate active workflows and recent `main` runs. Confirm the workflow identity, conclusion, head branch, and timestamps. A successful read with no history is an observed `no_history` witness; a failed or untrusted read is incomplete.

```sh
gh workflow list --repo aidotmarket/ai-market-backend --all --json id,name,path,state
gh run list --repo aidotmarket/ai-market-backend --branch main --limit 100 --json databaseId,workflowDatabaseId,workflowName,status,conclusion,createdAt,headSha,url
```

For Railway or Cloudflare, use the provider console or read-only API identity named above. Do not infer provider health from the watcher process being alive.

## Inspect queue, intents, spend, and breaker

Run the read-only SQL in this runbook only through a separately authorized, actual least-privileged read-only identity with access to the required tables. The absence of such an identity or approved projection is an evidence gap requiring a reviewed access/projection design; do not fall back to the watcher or queue API writer roles or claim verification without the evidence. The existing backend queue API exposes snapshot `GET` and lease/complete `POST`; the snapshot does not expose accepted dispatch completion metadata, and the POST operations are not a read-only verification path. Check recent intents before changing a rule or retrying anything. `queued`, `leased`, and `outcome_unknown` are open intent states. `expired_unleased`, `completed`, and `late_completion` are terminal journal states.

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

The watcher base PR #207 merged as `b435068161f3dcaa9421c0c84e0a344b9c769490`; final canary hotfix PR #209 merged as `e26ebeffc2ccaf66a2f0cb6f5626f0271e8b4ccd`. Railway deployment `ff27a413-4bed-4656-bbcd-a984255fe177` was a prior successful watcher deployment and remains useful history. Final watcher recovery PR #210 merged as `f8f9e9d654fdc4b4fece4f7b1940732b18a31c7a`; Railway deployment `78c6c0db-0ab6-4891-93ef-a53b2f89ca7c` was successful at that historical checkpoint. Its candidate suite passed 431 tests, the focused regression passed 6 tests, main CI run `33329532859` was green, and the exact candidate received full CC, Kimi, and GLM approval with no HIGH or MEDIUM findings. For the later independently checked active deployment, see the S1760 expired-history section above.

The first post-deploy production snapshot was generated at `2026-08-30T18:59:00.526422Z`. Its source keys were exactly `cloudflare`, `github`, and `railway`, with no synthetic `watcher` marker; every provider had `status: ok` and `observation_complete: true`; and the breaker was closed. The canary's public safe-snapshot `issue_id` remained `iss_01M19DKMF3R7DD2JA1BHX8QZHQ`, with status `resolved` and `resolved_at` `2026-08-30T17:18:45.308170Z`.

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

The authorized canary used stable workflow ID `345908153`. Failure run `33314116206` was created at `2026-08-30T13:24:57Z` and completed with the deliberate failure at `13:25:05Z`. It produced database `canonical_issues.id` UUID `f6c09dc9-87f3-4673-90dc-49eddb50b198` and public safe-snapshot `issue_id` `iss_01M19DKMF3R7DD2JA1BHX8QZHQ` for episode `aidotmarket/ai-market-backend|ci_failure|2026-08-30|2`. Use the UUID for database identity and the `iss_...` value only for public snapshot lookup.

The episode admitted exactly one intent, `04275df4-bc5d-4de5-b844-81841d8b2003`. It ended `outcome_unknown`; the breaker sample was `failed`; and the journal recorded `lease_expiry`. Before any lease, the watcher performed the guarded authoritative-episode repair. The deployed fallback then created exactly one ops ticket, `T-2026-000731`, with `human_required=false` and phase `fallback_waiting_resolution`.

Newer same-workflow `main` run `33324876164` was created at `2026-08-30T17:18:11Z` and completed successfully at `17:18:20Z`. The complete watcher observation at `2026-08-30T17:18:52.390720Z` resolved the canonical episode and ticket and advanced the handoff to `resolved_complete`. Later database proof still showed exactly one canonical issue, one intent, and one ticket. Email remained enabled throughout.

Production proof exposed a pre-existing central-backend inconsistency: ticket status was `resolved` while `resolved_at` was null. After full Council review and the PR #314 deployment above, exact canary ticket `T-2026-000731` was repaired once with guarded SQL using canonical `resolved_at` `2026-08-30T17:18:45.308170Z`. Exactly one row changed, and `resolution_source` intentionally remains null.

Cleanup PR #313 merged as `5eb4d992b4b253c048ac03a6b0962febb0fcd437` and removed only `.github/workflows/issue-channel-canary.yml`. All merge workflows were green: Site Smoke `33326033562`, Dependency Drift `33326033541`, Alembic Guardrails `33326033578`, and Gold Path `33326033569`. The workflow no longer exists.

A future deliberate canary requires fresh explicit authorization and a separately reviewed temporary workflow. Before running it, prove a green provider baseline, one complete watcher observation, and zero open or expired matching episodes. Dispatch exactly one failure, inspect an unknown outcome instead of retrying, then use one strictly newer success from the same workflow and `main`. Remove the temporary workflow only after complete observation proves canonical and eligible-ticket resolution, and wait for all cleanup-merge workflows to turn green.

## Read-only SQL

Connect with a separately authorized, actual least-privileged read-only identity that covers each queried table. These queries contain no credentials and make no changes, but their text alone does not make a writer credential read-only. If that identity or an approved read-only projection is unavailable, record the evidence gap for reviewed access/projection design; do not use `scripts/issue_channel_operate.sh`, `ISSUE_CHANNEL_WATCHER_DATABASE_URL`, the poller role, or `railway_alert_parity_read` as a fallback, and do not report dispatch completion as verified.

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

Each query must return exactly one row. The database `canonical_issues.id` must be UUID `f6c09dc9-87f3-4673-90dc-49eddb50b198`, the intent ID must be `04275df4-bc5d-4de5-b844-81841d8b2003`, and the ticket `public_ref` must be `T-2026-000731`. A safe-snapshot lookup instead uses public `issue_id` `iss_01M19DKMF3R7DD2JA1BHX8QZHQ`; never substitute it for the database UUID. A resolved or closed ticket needs the corresponding server timestamp; a reopened nonterminal ticket needs both lifecycle timestamps cleared. Treat `resolution_source` as optional and do not backfill or invent it merely because it is null.

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

For a safe update, use an MP build on a fresh branch, run the focused tests independently, and apply the active Council override above: CC, GLM and DeepSeek review exact Tier 3 source unanimously; MP does not vote. For the S1760 companions, review exact MCP PRs 276, 279 and 280, Ops PR 39 and both indexed operating pages together before normal merge or release. If a backend contract changes, deploy backend-first. Then obtain live provider, database, Railway, snapshot, sole-publisher supported database GET, authenticated-browser and eligible-ticket proof. Update `last_verified` only after that proof.

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

### Fallback ticket (outcome_unknown / lease_expiry) with no owner

Symptom: a non-terminal `issue-channel:` fallback ticket remains unclaimed after `outcome_unknown` or lease expiry; the poller alerts Mars and Vulcan once it is older than 60 minutes.

Likely cause: triage ended without an accepted report and the fallback handoff had no active owner. From 2026-09-23 ~10:40Z to 2026-09-24 ~10:00Z, every listing-detail page returned HTTP 500; Site Smoke Test failed from its first run, but the fallback ticket stayed unowned for about 23 hours. Frontend PR #81 fixed the page.

Verify: inspect the exact ticket `source_ref`, ownership and handoff phase, then check the Site Smoke Test and direct provider evidence. Do not infer resolution from a timeout or the fallback ticket alone.

Repair or rollback: claim the ticket with `support_ticket_patch` (`ownership_action=claim`), diagnose the provider failure, fix it, and resolve only with a complete provider-success witness.

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

### safe snapshot exceeds size bound

Symptom: Railway mails "Deployment crashed for issue-channel-watcher"; every watcher cycle ends with `koskadeux_mcp.issue_channel.storage.StorageSafetyError: safe snapshot exceeds size bound` from `reconcile_observation` → `_snapshot_payload` (`storage.py`, 1,000,000-byte cap); the mirror stops advancing and the open-items board says the channel is stale. Nothing customer-facing is affected.

Likely cause (T-2026-000814, 2026-09-20 to 21): the snapshot projects every canonical row's full `safe_metadata`, so anything that makes rows grow without bound eventually crosses the cap. The instance that happened: `council_providers` stamped each poll's `native_id` with a full timestamp, so each poll was a new fingerprint appended to the day's episode row (~1,000 per row per day, ~70KB), and those reading rows never resolve. Fixed in koskadeux-mcp `270a0c1fc3` (PR #227): reading identity is per subject per UTC day, and `fingerprints` (internal matching state) is no longer projected. Council found and deliberately left two slower growth paths: reading rows still accumulate three per UTC day forever, and `links` is projected unbounded.

Verify: `railway logs --service issue-channel-watcher -d | grep -c StorageSafetyError`; then, read-only, `SELECT status, count(*), sum(length(safe_metadata::text)) FROM issue_channel.canonical_issues GROUP BY 1` and `... ORDER BY length(safe_metadata::text) DESC LIMIT 3` to see which rows carry the bytes and which key inside them (`fingerprints`, `links`, `member_failures`).

Repair or rollback: fix the producer of the growth (identity or projection) through MP and a Council gate; never raise the cap, hand-edit rows, or delete canonical issues to make the snapshot fit. After the deploy, confirm a fresh snapshot with every provider `ok` and `observation_complete: true`, the byte size well under the cap, and the mirror refreshed on the next 300-second poller tick.

### Stale sources.watcher marker

Symptom: fresh provider observations are healthy, but the snapshot still contains a synthetic `sources.watcher` control-failure marker.

Likely cause: the marker is current because policy, table, meter, or admission control is still failing; the watcher has not completed a later normal control cycle; or stale-marker cleanup regressed. At the 11:54:13Z 2026-09-28 checkpoint, `admission:idempotency_duplicate` was a historical synthetic marker under the then-active code, not proof of a storage outage. The staged PR280 contract above treats only the three exact admission-stage duplicate reasons as expected refusals after normal delivery.

Expected fail-closed admission refusals such as `admission:daily_dispatch_cap`, `admission:breaker_open`, and `admission:dispatch_disabled` can also produce the marker; use `detail_code` to route a genuine cap to the existing spend-cap procedure and do not treat it as a storage outage.

Verify: compare the marker's `last_attempt` with fresh provider observation times and the currently active Railway deployment, then inspect current `issue-channel-watcher` logs. Deployment `78c6c0db-0ab6-4891-93ef-a53b2f89ca7c` is historical, not a current identity check. Provider partial or unavailable entries remain separate evidence and must be diagnosed even if the synthetic marker clears.

Repair or rollback: restore the current control failure and let a normal cycle remove only the exact stale synthetic marker. If a completed normal cycle occurred on the fixed deployment and the marker persists, treat it as a regression and rollback candidate. Never delete, hand-edit, or otherwise rewrite snapshot health.

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

Likely cause: the local connector process, configured path, or client route failed while the shared services remained healthy. In the reproduced case, a nested fallback shell could not find `rtk`, while authoritative ai.market calls remained reachable.

Verify: inspect the local connector environment and stderr first, including its effective `PATH` and whether the configured command can find `rtk`. Independently inspect the connector process and path, run `kd status`, issue a small read-only authoritative ai.market gateway command, and execute a read-only database `SELECT`. The banner alone does not prove gateway outage; do not infer one result from another.

Repair or rollback: repair the local client path only when gateway and database checks are healthy. If the database or true gateway is unreachable, stop production operations; never use local fallback as a production bypass.

### Canary cleanup or recreation

Symptom: workflow ID `345908153` still appears after cleanup, the removal merge workflows are not all green, or someone proposes reusing the deleted canary.

Likely cause: PR #313 cleanup did not reach the inspected revision, the workflow cache or query is stale, or a new deliberate canary lacks fresh authorization and review.

Verify: confirm `.github/workflows/issue-channel-canary.yml` is absent at current `main`, the workflow no longer exists, and runs `33326033562`, `33326033541`, `33326033578`, and `33326033569` are green. Preserve the completed canary's exact one-canonical, one-intent, one-ticket proof.

Repair or rollback: do not recreate or dispatch the deleted workflow. A future deliberate canary requires fresh explicit authorization and a separately reviewed temporary workflow, followed by the same failure, newer-success, complete-observation, resolution, and cleanup sequence.

## Changes

2026-09-28 S1762: documented the installed Railway alert parity job; stuck-build step 6 now links the Normal health check (GLM nit on PR #329).

2026-09-24 S1738: documented the unowned-ticket peer alert, check-in ownership duty, GitHub Actions notification setting, and fallback-ticket recovery after the listing-detail outage.
