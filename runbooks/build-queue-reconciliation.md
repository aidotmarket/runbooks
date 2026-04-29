# Build Queue Reconciliation

## Architecture overview

Build Queue reconciliation keeps Living State (LS), Build Queue dashboard state, and git evidence aligned before agents dispatch more build work. The reconciler core reads one BQ entity from LS, fetches Build Queue status, fetches git evidence for every `body.target_repos` repo, reads the gate chunk plan from the local spec, then classifies drift.

Classifications:

| Classification | Meaning |
|---|---|
| `HIGH_CONFIDENCE_GIT_AHEAD` | Git contains completed chunk evidence that cleanly extends LS. This is the only class eligible for automatic safe patching. |
| `ADVISORY_GIT_AHEAD` | Git appears ahead, but confidence is insufficient for automatic mutation. |
| `ADVISORY_BUILD_QUEUE_AHEAD` | Build Queue appears ahead of LS, but git evidence is not sufficient for automatic mutation. |
| `AMBIGUOUS` | Evidence conflicts or a dependency failed. Operators must inspect before mutating LS. |
| `LS_AHEAD_SUSPECTED` | LS records progress that git or Build Queue evidence does not confirm. Treat as potentially stale or manually edited state. |

Triggers:

| Trigger | Entry point | Purpose |
|---|---|---|
| A | `council_request mode=build` pre-dispatch gate | Blocks risky dispatch when LS drift exists. Can auto-patch or bypass with audit. |
| B | `kd_session_open` advisory report | Gives session openers a read-only drift report across in-progress BQs. |
| C | `kd_reconcile_bq` | Manual/on-demand reconciliation inspection and correction. |
| D | Build completion, Build Queue transition poller, git push poller | Event-driven reconciliation after new evidence appears. |

The safe-patch decision uses the `cleanly_extends` invariant. A patch is safe only when all five conditions hold:

1. The proposed chunk is the next chunk in the gate chunk plan.
2. Existing LS chunk entries are preserved and not rewritten.
3. All declared `target_repos` have evidence for the proposed chunk.
4. No later revert or contradictory git evidence invalidates the proposed chunk.
5. The proposed patch does not mutate `gate{N}.status`.

## Trigger reference

| Trigger | When it fires | Reads | Can patch | Cannot patch |
|---|---|---|---|---|
| A | Before accepting `council_request mode=build` with a `bq_code`. | LS BQ entity, Build Queue status, target repo git logs, gate spec. | Yes, only with `auto_reconcile=true` and `HIGH_CONFIDENCE_GIT_AHEAD` plus `cleanly_extends=true`. | Cannot silently proceed on drift; must reject, auto-reconcile, or audited bypass. |
| B | During `kd_session_open`. | In-progress LS BQs, Build Queue status, git evidence, gate specs. | No. | Cannot mutate LS or emit reconciliation events. |
| C | Manual `kd_reconcile_bq` request. | One LS BQ entity, Build Queue status, git evidence, gate spec. | Yes, under the same safe-patch policy as Trigger A. | Cannot patch advisory, ambiguous, unsupported, or unsafe classifications. |
| D | Build completion callback, Build Queue transition poller, or git push poller. | Event payload, LS BQ entity, Build Queue status, git evidence, gate spec. | Yes, only after audit event emission and only on the safe-patch path. | Cannot patch if audit emission fails; cannot patch advisory-only paths. |

## Classification reference

| Classification | Example scenario | Operator action |
|---|---|---|
| `HIGH_CONFIDENCE_GIT_AHEAD` | LS says next action is Chunk 2A, and all target repos contain Chunk 2A commits with no revert evidence. | Use `auto_reconcile=true` or let Trigger D apply the safe patch. |
| `ADVISORY_GIT_AHEAD` | One target repo has the chunk commit, but another declared repo has no matching commit. | Inspect repos and Build Queue history; do not auto-patch. |
| `ADVISORY_BUILD_QUEUE_AHEAD` | Build Queue marks a chunk complete, but git evidence is missing or incomplete. | Verify builder output and commits; patch manually only after evidence is clear. |
| `AMBIGUOUS` | Git fetch fails, Build Queue is unreachable, or evidence includes a revert. | Treat as degraded evidence; resolve the failure or inspect manually. |
| `LS_AHEAD_SUSPECTED` | LS lists Chunk 3 built while git and Build Queue only support Chunk 2. | Audit recent LS writes before dispatching dependent work. |

## Bypass procedure

Use `auto_reconcile=true` when the reconciler reports `HIGH_CONFIDENCE_GIT_AHEAD`, `cleanly_extends=true`, and the proposed patch only appends the next chunk and advances `next_action`. The system applies the LS patch, emits `ls_drift_reconciled`, and then proceeds.

Use `bypass_reconcile=true` only when a human intentionally wants to proceed without patching LS. Include `reconcile_justification` with the concrete reason, such as "Build Queue outage; verified Chunk 2A commit in target repo manually." Bypasses emit `ls_drift_bypassed` with caller, session, classification, LS state, and justification. Missing or vague justifications should be treated as review findings.

Do not use bypass to avoid a clean safe patch. Do not bypass unsupported target repos until repo ownership is confirmed and `body.target_repos` is corrected.

## Weekly bypass-rate review checklist

Run the report over a rolling 7-day window:

```bash
cd /Users/max/koskadeux-mcp
python3 scripts/bypass_audit_report.py --days 7
```

The script queries:

```json
{
  "action": "list",
  "event_type": "ls_drift_bypassed",
  "updated_since": "<UTC timestamp for now minus 7 days>"
}
```

Paste this markdown table into the weekly session handoff:

```markdown
| BQ | Session | Bypass Count | Caller | Justifications |
|---|---|---|---|---|
```

Review steps:

1. Sort by highest bypass count.
2. For each repeated BQ/session pair, confirm each justification references concrete evidence or a known outage.
3. Confirm there is no pattern of bypassing clean `HIGH_CONFIDENCE_GIT_AHEAD` patches.
4. For unsupported or missing `target_repos`, run the backfill script in dry-run mode and patch LS after verification:

```bash
python3 scripts/backfill_target_repos.py
python3 scripts/backfill_target_repos.py --apply
```

5. File a follow-up BQ if bypasses cluster around the same failure mode.

Scheduling option: the weekly report is registered in `koskadeux_server.py` through `BackgroundScheduler` as `build_queue_bypass_audit_report`. It runs Mondays at 09:00 UTC and writes the markdown table to the server log. For a manual-only deployment, keep using the command above.

## Failure-mode runbook

| Failure | Signature | Action |
|---|---|---|
| `build_queue_unreachable` | Reconciler report has `error_code=build_queue_unreachable`; Trigger B report includes an outage flag; build queue poller logs `poll skipped after API outage`. | Do not auto-patch from Build Queue evidence. Verify backend health and retry. Bypass only with manual git evidence and a specific justification. |
| `git_fetch_failed` | Reconciler report has `error_code=git_fetch_failed`; git push poller logs `git push poll skipped`. | Check GitHub token, network, repo access, and branch name. Re-run after `git fetch origin` succeeds. |
| `chunk_plan_unavailable` | Reconciler cannot resolve the gate spec or chunk sequence. | Confirm `gate{N}.spec_path` and local `specs/` file exist. Do not patch until the chunk plan is readable. |
| `unsupported_target_repo` | `body.target_repos` is missing or contains a repo outside the supported `aidotmarket/*` scope. | Confirm ownership. Backfill or correct `body.target_repos`, then rerun reconciliation. |

## Operational notes

Poller cursor keys:

| Poller | Cursor key |
|---|---|
| Build Queue transition poller | `infra:build-queue-poller-cursor` |
| Git push poller | `infra:git-push-poller-cursor` |

To inspect a cursor:

```json
{"action":"get","key":"infra:build-queue-poller-cursor"}
{"action":"get","key":"infra:git-push-poller-cursor"}
```

To reset a cursor, patch or put the cursor body with an empty position after confirming no in-flight events depend on it:

```json
{"action":"put","key":"infra:build-queue-poller-cursor","kind":"infra","summary":"Reset Build Queue poller cursor","body":{},"updated_by":"vulcan","source_ref":"build-queue-reconciliation-runbook","expected_version":<current_version>}
{"action":"put","key":"infra:git-push-poller-cursor","kind":"infra","summary":"Reset git push poller cursor","body":{"repos":{}},"updated_by":"vulcan","source_ref":"build-queue-reconciliation-runbook","expected_version":<current_version>}
```

Verify pollers are running from `koskadeux_server.py` startup logs. Expected signatures:

| Component | Healthy log signature |
|---|---|
| Scheduler startup | `Trigger D pollers started` |
| Build Queue poller registration | `build_queue poller registered` |
| Git push poller registration | `git_push poller registered` |
| Bypass audit report registration | `bypass audit report job registered` |
| Build Queue outage | `build_queue poll skipped after API outage` |
| GitHub outage/rate limit | `git push poll skipped` or `git push poll rate-limited` |
| Weekly bypass report | `weekly ls_drift_bypassed report` |
