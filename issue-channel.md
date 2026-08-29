---
runbook_id: issue-channel
domain: platform-operations
status: DRAFT
authoritative_for:
  - topic: issue-channel
    section: §C. Architecture & Interactions
  - topic: issue-channel-resolution
    section: §E. Operate
  - topic: issue-channel-replay-corpus
    section: §E. Operate
  - topic: issue-channel-watcher-db-access
    section: §E. Operate
aliases:
  - infrastructure failure channel
  - CI health board
  - issue channel watcher
  - episode resolution
  - expiry floor
  - replay corpus
error_signatures:
  - signature: 'observation_complete":false'
    section: §F. Isolate
  - signature: nodename nor servname provided, or not known
    section: §F. Isolate
  - signature: no_history
    section: §F. Isolate
  - signature: RailwayAdapterError
    section: §F. Isolate
  - signature: expired_count
    section: §F. Isolate
  - signature: resolution.expiry_ttl
    section: §E. Operate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-08-29
system_name: issue-channel
purpose_sentence: The issue channel polls GitHub, Railway and Cloudflare for infrastructure failures, records them as canonical episodes in Postgres, closes them when the provider shows a newer success, and publishes a snapshot that the session-open board renders.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Operation, diagnosis, repair and evolution of the issue channel as a WORKING system: the watcher service, adapters, canonical store, episode resolution and expiry, dispatch policy in dry_run, snapshot/board publication, the replay-corpus exporter, and reaching the watcher database from Titan-1. Gate-2 EVIDENCE process (receipt environments, probes, receipt packages) is owned by issue-channel-gate2-receipts.md. Council review mechanics are owned by council-session-gate-and-fold-ops.md. Secret values are never here (Infisical project bd272d48-c5a1-4b52-9d24-12066ae4403c, env prod).
linter_version: 1.0.0
---

# Issue Channel (infrastructure failure channel)

## §A. Header

YAML frontmatter above is authoritative for the §A header fields. Design authority: `specs/BQ-CI-HEALTH-VISIBLE-AT-SESSION-OPEN-S1511-GATE2.md` on koskadeux-mcp branch `spec/bq-ci-health-visible-at-session-open-s1511` (head `9d1427c683`, Amendment A3 approved S1635). Where this runbook and the spec differ, the spec wins; fix the runbook the same session.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| GitHub CI-failure detection (main branch, active workflows, 2-day lookback) | SHIPPED | `koskadeux_mcp/issue_channel/adapters/github.py` | `tests/issue_channel/test_github_adapter.py` | 2026-08-29 |
| Railway deploy-failure detection (per service, 2-day lookback) | SHIPPED | `koskadeux_mcp/issue_channel/adapters/railway.py` | `tests/issue_channel/test_railway_adapter.py` | 2026-08-29 |
| Cloudflare monitoring source | SHIPPED | `koskadeux_mcp/issue_channel/adapters/cloudflare.py` | `tests/issue_channel/test_cloudflare_adapter.py` | 2026-08-29 |
| Sanitize + quarantine of raw provider payloads | SHIPPED | `koskadeux_mcp/issue_channel/sanitize.py` | `tests/issue_channel/test_contract_corpus.py` | 2026-08-29 |
| Canonical episodes, fingerprint linking, daily correlation_key | SHIPPED | `koskadeux_mcp/issue_channel/normalize.py` | `tests/issue_channel/test_normalize_dedup.py` | 2026-08-29 |
| Episode resolution on provider success witnesses (spec 4.1.1-4.1.3; live since main 8e37cd722b; verified open_count 6 to 1) | SHIPPED | `koskadeux_mcp/issue_channel/resolution.py` | `tests/issue_channel/test_resolution.py` | 2026-08-29 |
| Real dispatch spend in the safe snapshot (`dispatch_spend`: per-UTC-day and total completed measured cost, counts, open intents) and on the board channel line; `cost_usd` stays the watcher's external-action cost | SHIPPED (main 6232014ac5) | `koskadeux_mcp/issue_channel/storage.py` `_dispatch_spend`, `scripts/ground_truth_open_items.py` | `tests/issue_channel/test_admission_db.py`, `tests/test_open_items_channel_segment.py` | 2026-08-29 |
| Zero-wait CC profile gate before leasing; lease 660 s >= timeout 600 + 60 margin (load-time invariant); queue TTL 1020 s (3 x 300 s poller cadence + skew) | SHIPPED (main cf1471c273) | `koskadeux_mcp/issue_channel/poller.py`, `scripts/issue_channel_poller.py`, `koskadeux_mcp/issue_channel/policy.py` | `tests/issue_channel/test_poller.py`, `test_poller_cli.py`, `test_policy_admission.py` | 2026-08-29 |
| Wall-clock expiry floor open to expired (spec 4.1.4; policy resolution.expiry_enabled true, expiry_ttl 7 days; no production expiry yet) | SHIPPED | `koskadeux_mcp/issue_channel/policy.py` | `tests/issue_channel/test_policy_admission.py` | 2026-08-29 |
| Dispatch rules evaluation in dry_run (dispatch_enabled false) | PARTIAL | `koskadeux_mcp/issue_channel/rules.py` | `tests/issue_channel/test_dry_run_rules.py` | 2026-08-29 |
| Snapshot publication, Titan-1 mirror, board segment | SHIPPED | `koskadeux_mcp/issue_channel/snapshot.py` | `tests/issue_channel/test_poller.py` | 2026-08-29 |
| Replay-corpus exporter and offline replay | SHIPPED | `koskadeux_mcp/issue_channel/export.py` | `tests/issue_channel/test_export.py` | 2026-08-28 |
| Live dispatch of a worker on a rule match (rollout step 11) | PLANNED | — | — | 2026-08-29 |

## §C. Architecture & Interactions

One Railway watcher polls three providers, sanitizes what it sees, stores canonical episodes in the backend Postgres, resolves them from provider success witnesses, and publishes a snapshot that Titan-1 mirrors into the session-open board.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Watcher service issue-channel-watcher | Railway project ai-market, env production, service id `d48dd44c-4541-4387-89da-50b2b1d0c8fe`; `deploy/issue-channel-watcher/Dockerfile` → replica guard `scripts/replica_singleton_guard_watcher.py` → `scripts/issue_channel.py` | Postgres schema `issue_channel` on the backend Postgres | GitHub, Railway, Cloudflare APIs; Living State publisher | Auto-deploys `aidotmarket/koskadeux-mcp` main on push. `numReplicas = 1` is a Gate-2 mandate; a second replica fails on purpose. |
| Adapters | `adapters/{github,railway,cloudflare}.py` | none (stateless per poll) | provider APIs (read-only tokens) | Emit failure envelopes AND per-resource current-state **witnesses** (latest run on main / newest deployment per service) from data already fetched — zero extra HTTP calls. |
| Observation completeness | `models.py SourceObservation` (`expected_resources`, `observed_resources`, `observation_complete`) | snapshot | resolution | A resource with a SUCCESSFUL read but empty history is observed as `{"state":"no_history"}`. Only a failed/untrusted/unordered READ leaves a resource unobserved (completeness false). |
| Canonical store | `storage.py` (`canonical_issues`, `source_records`, `safe_raw_records`, `quarantine`, `dispatch_intents`) | Postgres `issue_channel.*`, role `issue_channel_watcher` | resolution, rules, snapshot | `canonical_issues.status ∈ {open, resolved, expired}`; `resolved_at`; `episode_key` = correlation_key plus ordinal; per-member failure metadata in `safe_metadata`. |
| Resolution | `resolution.py`, `storage.py reconcile_observation` (runner calls it after each COMPLETE observation) | canonical_issues | witnesses, policy | Subject episode = `(provider, subject, kind)`. Witnesses bound only to the kind they resolve (GitHub workflow → `ci_failure`, Railway deployment → `deploy_failure`). |
| Policy | `policy.py`, `config/issue_channel/policy.yaml` (`resolution.expiry_enabled`, `resolution.expiry_ttl`, dispatch caps, `dispatch_enabled`) | none | runner | Fail-closed at startup on invalid values. |
| Rules + journal (dry_run) | `rules.py`, `journal.py`, `config/issue_channel/dispatch_rules.yaml` | `dispatch_intents` (empty while dry_run), `canonical_issues.safe_metadata.decision` | policy, breaker | In dry_run, decisions are written on the canonical row (`decision.rule_id`, `would_action`, `dry_run`, `evaluated_at`), never as intents. |
| Snapshot + mirror | `snapshot.py`; Titan-1 LaunchAgent `com.koskadeux.issue-channel-poller` mirrors to `/Users/max/koskadeux-state/issue-channel/snapshot.json` | Living State `infra:open-items-board` (via `ground_truth_open_items.py --publish`) | ops.ai.market board | Snapshot carries `open_count`, `expired_count`, `episode_transitions`, per-source completeness, per-issue state. |
| Replay corpus exporter | `scripts/issue_channel.py --export-corpus <dir>` (`export.py`) | writes `raw/<fp>.json`, `issues.json`, `MANIFEST.json` | `--replay --rules … --corpus <dir>` (`rules.py load_corpus`) | Read-only; reads canonical, source and safe-raw tables only; never quarantine; never writes the DB. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| mars / vulcan | read watcher DB from Titan-1 | `psql` via Postgres public TCP proxy (§E) | role `issue_channel_watcher` (read) | COMPLETE |
| mars / vulcan | export replay corpus, run replay | `scripts/issue_channel.py --export-corpus` / `--replay` | same DB role | COMPLETE |
| mars / vulcan | inspect deploy status / logs | `railway deployment list -s issue-channel-watcher --json`, `railway logs -s issue-channel-watcher` | Railway CLI login (max@ai.market); in gateway fallback shells set `PATH=/opt/homebrew/bin:$PATH HOME=/Users/max` | COMPLETE |
| mars / vulcan | change resolution/dispatch policy | edit `config/issue_channel/policy.yaml`, PR, three-seat Gate 3 | repo write via PR | COMPLETE |
| MP (builder) | code changes | `dispatch_mp_build` on koskadeux-mcp | branch push only | COMPLETE |
| CC / Kimi / GLM | Gate 3 review | `council_request mode=review` (§E.5 for Kimi packaging) | read | COMPLETE |
| SysAdmin | Railway/Infisical questions | `sysadmin_request` | — | COMPLETE |

## §E. Operate

The bash for E-01/E-03/E-06 is kept verbatim in `runbooks/scripts/issue_channel_operate.sh` (`source` it; functions ic_url, ic_status, ic_rows, ic_health, ic_export, ic_package_for_kimi) and summarised here; the `tool_or_endpoint` fields are the authoritative commands.

```yaml operate
- id: E-01
  trigger: Need to read the production watcher database from Titan-1 (status counts, decisions, resolution state).
  pre_conditions: [~/.config/infisical/sysadmin-token present, railway CLI logged in as max@ai.market, PATH includes /opt/homebrew/bin and HOME=/Users/max in gateway fallback shells]
  tool_or_endpoint: "~/bin/infisical_auth_refresh.sh; W=$(curl -sf 'https://secrets.ai.market/api/v3/secrets/raw/ISSUE_CHANNEL_WATCHER_DATABASE_URL?workspaceId=bd272d48-c5a1-4b52-9d24-12066ae4403c&environment=prod&secretPath=/' -H \"Authorization: Bearer $(cat ~/.config/infisical/sysadmin-token)\" | python3 -c 'import json,sys;print(json.load(sys.stdin)[\"secret\"][\"secretValue\"])'); PUB=$(cd /Users/max/ops/aimarket-backend-main && railway variables -s Postgres --json | python3 -c 'import json,sys;print(json.load(sys.stdin)[\"DATABASE_PUBLIC_URL\"])'); URL=$(W=\"$W\" PUB=\"$PUB\" python3 -c 'import os;from urllib.parse import urlsplit,urlunsplit;w=urlsplit(os.environ[\"W\"]);p=urlsplit(os.environ[\"PUB\"]);print(urlunsplit((w.scheme,f\"{w.username}:{w.password}@{p.hostname}:{p.port}\",w.path,w.query,w.fragment)))'); psql \"$URL\" -At -c 'select status, count(*) from issue_channel.canonical_issues group by 1;'"
  argument_sourcing:
    credentials: watcher URL from Infisical prod (user/password/dbname), host and port from the Postgres service DATABASE_PUBLIC_URL (the internal host postgres.railway.internal is unreachable from Titan-1)
    role: issue_channel_watcher (read); never echo $W or $URL; never write with this role
  idempotency: IDEMPOTENT
  expected_success: {shape: psql returns rows and select current_user is issue_channel_watcher, verification: status counts match the mirror snapshot open_count}
  expected_failures:
    - {signature: "nodename nor servname provided, or not known", cause: internal host used instead of the public proxy}
    - {signature: "password authentication failed", cause: DATABASE_PUBLIC_URL carries a stale password after rotation; compose from POSTGRES_PASSWORD per ai-market-backend.md}
    - {signature: "Unauthorized", cause: railway CLI in a fallback shell without HOME/PATH}
  next_step_success: Proceed with the read (E-02 verification or E-03 export).
  next_step_failure: Isolate with F-03 / F-04; repair G-03.
- id: E-02
  trigger: A watcher deploy landed (any merge to koskadeux-mcp main) or the board looks wrong.
  pre_conditions: [railway CLI logged in, Titan-1 mirror LaunchAgent com.koskadeux.issue-channel-poller running]
  tool_or_endpoint: "railway deployment list -s issue-channel-watcher --json; python3 -c \"import json;s=json.load(open('/Users/max/koskadeux-state/issue-channel/snapshot.json'));print(s['generated_at'],s['snapshot']['open_count'],s['snapshot'].get('expired_count'),{k:v['observation_complete'] for k,v in s['snapshot']['sources'].items()})\"; cd /Users/max/koskadeux-mcp && python3 scripts/ground_truth_open_items.py --publish"
  argument_sourcing:
    expected_commit: the merged main SHA; newest deployment row must be SUCCESS on it
    timing: wait one poll (about 2 minutes) after SUCCESS before reading the mirror
  idempotency: IDEMPOTENT
  expected_success: {shape: snapshot generated_at newer than the deploy; every source observation_complete true; open_count and expired_count present; board republished, verification: E-01 status counts agree with open_count}
  expected_failures:
    - {signature: "observation_complete\":false", cause: a witness or resource cannot be observed, or a provider read failed; see F-01}
    - {signature: "generated_at older than deploy", cause: mirror stale or watcher crash-looping; check railway logs -s issue-channel-watcher}
  next_step_success: Retain snapshot and E-01 output (hashed) in the active review package if part of a gate.
  next_step_failure: Isolate with F-01 / F-09; repair G-01 / G-05.
- id: E-03
  trigger: Need real historical data to calibrate dispatch rules (rollout receipts) or to reproduce a decision offline.
  pre_conditions: [E-01 URL composed, koskadeux-mcp venv present, a FRESH output directory under the active review package]
  tool_or_endpoint: "ISSUE_CHANNEL_WATCHER_DATABASE_URL=\"$URL\" venv/bin/python scripts/issue_channel.py --export-corpus \"$OUT\"; venv/bin/python scripts/issue_channel.py --replay --rules config/issue_channel/dispatch_rules.yaml --corpus \"$OUT\""
  argument_sourcing:
    OUT: review-packages/<package>/corpus-<UTC timestamp>; never reuse a directory
    rules: the shipped config/issue_channel/dispatch_rules.yaml at the SHA under test
  idempotency: IDEMPOTENT
  expected_success: {shape: one-line JSON summary with issues_exported and issues_skipped_no_raw; MANIFEST.json with sha256 per file; replay report schema issue-channel-replay-report-v1 with http_calls 0, verification: raw file count equals issues.json row count; hash MANIFEST into the receipt}
  expected_failures:
    - {signature: "socket.gaierror", cause: internal DB host; use E-01 composition}
    - {signature: "StorageSafetyError", cause: a safe raw projection is absent for a row; the exporter skips and counts it}
  next_step_success: Cite corpus MANIFEST sha256 and replay totals in the receipt (issue-channel-gate2-receipts.md).
  next_step_failure: Isolate with F-03.
- id: E-04
  trigger: Need to change the expiry floor, its TTL, or roll resolution back.
  pre_conditions: [three-seat Gate 3 available (CC, Kimi, GLM), spec Amendment A3 0.7 read]
  tool_or_endpoint: "edit config/issue_channel/policy.yaml keys resolution.expiry_enabled (bool, required) and resolution.expiry_ttl (must exceed every provider lookback; v1 7 days); PR to koskadeux-mcp main; watcher auto-deploys"
  argument_sourcing:
    floor_only_rollback: resolution.expiry_enabled false (ttl becomes optional; witness resolution keeps working)
    full_rollback: revert the watcher deployment to the pre-A3 image; there is deliberately no switch that disables witness resolution
    written_states: resolved, expired and resolved_at are never rewritten by either rollback
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: watcher starts and E-02 shows all sources complete, verification: policy load test test_policy_admission.py green; startup refuses invalid ttl when enabled}
  expected_failures:
    - {signature: "resolution.expiry_ttl", cause: invalid/missing/zero/negative ttl with expiry_enabled true; startup fails closed by design}
  next_step_success: Record the change in the BQ and Event Ledger.
  next_step_failure: Revert the PR.
- id: E-05
  trigger: Sending a code or spec candidate to Kimi for Council review.
  pre_conditions: [candidate pushed to a branch, base and head SHAs known]
  tool_or_endpoint: "P=<review package>/<candidate>; git diff <base>..<head> > $P/diff.patch; git archive <head> koskadeux_mcp/issue_channel tests/issue_channel config/issue_channel | tar -x -C $P; cp spec, pytest and ruff logs; (cd $P && shasum -a 256 * > SHA256SUMS); council_request agent=kimi mode=review cwd=$P"
  argument_sourcing:
    step_budget: state a 40-step budget and at most 5 targeted reads in the task text
    cwd: the package directory (Kimi reviews from a pinned checkout and cannot git fetch)
  idempotency: IDEMPOTENT
  expected_success: {shape: response file appears in /Users/max/council/kimi/ with a verdict line, verification: grep -inE '^APPROVE|^REVISE|^VERDICT' on the response}
  expected_failures:
    - {signature: "loop.max_steps_exceeded", cause: 40-step cap on a broad ask; narrow the brief}
    - {signature: "Candidate artifact absent from the pinned checkout", cause: branch not packaged on disk}
  next_step_success: Fold findings; re-dispatch R2 with the delta patch.
  next_step_failure: Repair G-04.
- id: E-06
  trigger: A builder branch exists and must be verified independently before a PR is opened.
  pre_conditions: [head SHA known, koskadeux-mcp venv present]
  tool_or_endpoint: "git worktree add /tmp/wt-<x> <head>; cd /tmp/wt-<x>; venv/bin/python -m pytest tests/issue_channel -q -p no:cacheprovider; venv/bin/python -m ruff check koskadeux_mcp/issue_channel tests/issue_channel; git merge --no-commit --no-ff origin/main && git merge --abort; git worktree remove --force /tmp/wt-<x>"
  argument_sourcing:
    execution: run via shell_request action=background (suite takes about 2.5 minutes and exceeds the 120 s exec timeout); poll the log files
    mypy: not installed in the venv; make no mypy claim
  idempotency: IDEMPOTENT
  expected_success: {shape: N passed, RUFF_EXIT=0, merge dry-run clean, verification: retain the logs in the review package and cite the exact commands in the Gate 3 request}
  expected_failures:
    - {signature: "Timed out after 120s", cause: ran in foreground; use background}
    - {signature: "CONFLICT", cause: main advanced under the branch; merge origin/main into the branch (no rebase)}
  next_step_success: Open the PR and dispatch the three-seat Gate 3.
  next_step_failure: Send failures back to MP on the same branch.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `observation_complete: false` for github/railway on every poll; nothing ever resolves | A witness resource is in `expected_resources` but never observed (new workflow/service shape the adapter does not handle); or a provider read genuinely failing | Snapshot: `set(expected_resources) - set(observed_resources)` per source; check `error_class`; `railway logs -s issue-channel-watcher` | G-01 | CONFIRMED |
| F-02 | Episode stays open although the provider is green | Not every bound member is SUCCESS (another active workflow on main is red/cancelled); the success is older than the failure; the witness is `no_history`; poll incomplete (F-01) | `gh api repos/<r>/actions/workflows` then per-workflow latest run on main; compare `created_at` with the failure's; read `safe_metadata` on the row | G-02 | CONFIRMED |
| F-03 | `psql: nodename nor servname provided, or not known` from Titan-1 | Using the internal host `postgres.railway.internal` | — | G-03 | CONFIRMED |
| F-04 | `railway: Unauthorized` or `railway: command not found` inside shell_request | Gateway emergency-fallback shell has minimal PATH/HOME | `echo $PATH; echo $HOME` | G-03 | CONFIRMED |
| F-05 | Kimi review returns no response file | 40-step cap exceeded, or branch not fetchable from its pinned checkout | `tail /Users/max/council/kimi/launcher-<id>.md.log` shows `loop.max_steps_exceeded` or fetch failure | G-04 | CONFIRMED |
| F-06 | open_count climbs and never falls (pre-A3 symptom) | Running an image before main `8e37cd722b` | `railway deployment list` commit hash | G-05 | CONFIRMED |
| F-07 | `expired` rows appear | Source degraded for > expiry_ttl (no complete observation), or provider truly silent | Check the source's completeness history; expired is loud by design, never treated as resolved | G-05 | HYPOTHESIZED |
| F-08 | Two dispatches would fire for one repository | Two open episodes (different days) on the same subject before resolution was live; or two distinct subject episodes | Replay corpus (E3) `would_dispatch` per fingerprint | G-05 | CONFIRMED |
| F-09 | Board and DB disagree on open items | Mirror stale (`generated_at` old) or board not republished | Compare snapshot `generated_at` with deploy time; E2 step 4 | G-05 | HYPOTHESIZED |
| F-10 | Poller log shows `executor_busy_no_lease` on a tick; queued intent not leased yet | Expected: a Council CC review holds the dedicated CC profile lock; the poller checks it with zero wait BEFORE leasing (main cf1471c273, V-5b F1) and retries next tick. Queue TTL 1020 s covers three ticks. Only a fault if it persists past the TTL (then `expired_unleased`) | `grep executor_busy_no_lease /var/tmp/koskadeux/issue-channel-poller.out.log`; `pgrep -fl "/opt/homebrew/bin/claude -p"` shows the holder | none needed; if persistent, see CC profile hold in council-comms | CONFIRMED (S1636, live) |
| F-11 | Watcher refuses policy at load: `lease_duration_s must be >= timeout_s + 60s completion margin` | policy.yaml edited with a lease shorter than the worker timeout plus margin; fail-closed by design (PR #200) | `venv/bin/python -c "from koskadeux_mcp.issue_channel.policy import load_policy_bundle; load_policy_bundle()"` | Set lease_duration_s >= timeout_s + 60 and re-review the policy | CONFIRMED (unit test) |
| F-12 | Board channel line shows no spend although a dispatch completed today | Snapshot older than the completion (watcher tick pending), or channel stale/unavailable (spend is suppressed on those statuses by design), or image before main 6232014ac5 | `python3 -c "import json;print(json.load(open('/Users/max/koskadeux-state/issue-channel/snapshot.json'))['snapshot'].get('dispatch_spend'))"` | Wait one watcher tick, then E-02 republish | CONFIRMED (S1636: 2 dispatches today $1.25 rendered) |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Adapters
  root_cause: an expected witness resource can never be observed (e.g. a resource with no history), so completeness is permanently false
  repair_entry_point: adapters/{github,railway}.py witness construction; resolution.py member binding
  change_pattern: a SUCCESSFUL read with empty history must be recorded as an observed `no_history` witness and excluded from members; only failed reads leave a resource unobserved. Add a test with the production resource shape. PR + three-seat Gate 3.
  rollback_procedure: revert the PR; detection is unaffected either way
  integrity_check: post-deploy snapshot shows all sources complete (E2)
- id: G-02
  symptom_ref: F-02
  component_ref: Resolution
  root_cause: predicate or member binding does not match spec 4.1.2/4.1.3
  repair_entry_point: resolution.py, storage.py reconcile_observation, tests/issue_channel/test_resolution.py
  change_pattern: fix against the spec clause, add the failing fixture first, keep request-count assertions unchanged
  rollback_procedure: revert the PR
  integrity_check: 330+ tests green; external verification per E2
- id: G-03
  symptom_ref: F-03
  component_ref: Canonical store
  root_cause: Titan-1 cannot reach postgres.railway.internal; gateway fallback shells have minimal PATH/HOME (also F-04)
  repair_entry_point: operator shell
  change_pattern: use E1 (public TCP proxy with watcher credentials); prefix PATH=/opt/homebrew/bin:$PATH HOME=/Users/max in fallback shells
  rollback_procedure: none (read-only access pattern)
  integrity_check: psql select current_user returns issue_channel_watcher
- id: G-04
  symptom_ref: F-05
  component_ref: Resolution
  root_cause: Kimi cannot fetch branches from its pinned checkout and dies silently past 40 steps
  repair_entry_point: council_request dispatch
  change_pattern: package the candidate on disk per E5 and give a step budget
  rollback_procedure: none
  integrity_check: response file exists in /Users/max/council/kimi/
- id: G-05
  symptom_ref: F-06
  component_ref: Watcher service issue-channel-watcher
  root_cause: stale image, stale mirror, expected expiry, or two open episodes on one subject (F-06-F-09)
  repair_entry_point: railway deployment list -s issue-channel-watcher; E2; rollout step 11 fingerprint selection
  change_pattern: redeploy main for F-06; republish board for F-09; investigate the degraded source for F-07 (expired is non-absorbing); name one fingerprint explicitly for F-08
  rollback_procedure: revert the offending deployment
  integrity_check: snapshot generated_at newer than deploy, all sources complete, board republished
```

## §H. Evolve

### §H.1 Invariants

- Provider observations are the only issue-existence and resolution authority (spec §1 inv. 4); `expired` is the single non-observational state and is never treated as resolution.
- Resolution needs a COMPLETE observation and terminal SUCCESS on EVERY bound member witness, each newer than that member's latest open failure. History-window fall-out is never evidence.
- Witnesses add zero HTTP calls (adapter tests assert request counts: GitHub 4, Railway 3).
- No plaintext secret or customer data in canonical state, witnesses, snapshots, journals, logs, or corpora.
- `dispatch_enabled: false` until rollout step 11 is executed under its own receipt.

### §H.2 BREAKING predicates

- Any change that lets a partial observation resolve, or that resolves on absence of a failure envelope.
- Adding an HTTP call, scope, or endpoint to any adapter.
- Writing to the DB from `--export-corpus` or reading quarantine from it.
- A second replica of the watcher.

### §H.3 REVIEW predicates

- Any change to `policy.yaml` values, dispatch_rules, member binding, or episode keying.
- New provider or new resource shape (check F-01 class first).

### §H.4 SAFE predicates

- Test-only changes; RESOLUTION.md wording; snapshot fields that add information without removing any.

### §H.5 Boundary definitions

#### module

`koskadeux_mcp/issue_channel/` and `scripts/issue_channel.py`; `config/issue_channel/`.

#### public contract

Snapshot schema fields consumed by the board; `issue-channel-replay-corpus-v1` and `issue-channel-replay-report-v1`; `canonical_issues.status` values.

#### runtime dependency

Backend Postgres (`issue_channel` schema), Railway service `issue-channel-watcher`, provider tokens in Infisical prod.

#### config default

`policy.yaml`: `dispatch_enabled: false`, `resolution.expiry_enabled: true`, `resolution.expiry_ttl` 7 days.

### §H.6 Adjudication

Spec 4.1 (Amendment A3) is the contract; Council three-seat (CC, Kimi, GLM) adjudicates at Gate 3; Max adjudicates policy value changes.

## §I. Operational Examples

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-02, §F]
    scenario: |
      id: E-02. trigger: main 8e37cd722b deployed at 2026-08-29 14:38:57Z with six open rows and every ai-market-backend workflow on main green. tool_or_endpoint: snapshot mirror read plus E-01 status counts. expected_success: first complete poll (14:40Z) resolved the ai-market-backend ci_failure episodes of 2026-08-27 and 2026-08-28 together, the runbooks ci_failure and both Railway deploy_failure episodes; vectoraiz ci_failure stayed open because no newer success exists on main; open_count 6 to 1. Evidence: review-packages/S1511-GATE2-RECEIPTS/a3-postfix-snapshot-20260829T144416Z.json (sha256 473f6c05...) and a3-postfix-canonical-20260829T144416Z.txt (sha256 42197f00...); Event Ledger f6ea7d2c-3d60-4182-9459-f0d11f620270. next_step_failure: isolate with F-01.
    expected_answers:
      - kind: human_action
        verb: verify
        object: post-deploy snapshot and canonical status counts
        target: all sources complete and open_count fell from 6 to 1
    weight: 1.0
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1635
last_refresh_commit: 8e37cd722b
last_refresh_date: 2026-08-29T14:50:00Z
owner_agent: mars
refresh_triggers:
  - any merge touching koskadeux_mcp/issue_channel or config/issue_channel
  - rollout step 11 (live dispatch) execution
  - first production expiry transition
  - new provider or resource shape
scheduled_cadence: 30d
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
retrofit: false
trace_matrix_path: null
word_count_delta: null
```
