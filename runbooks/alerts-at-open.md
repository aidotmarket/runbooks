---
title: Alerts at session open (S1529)
owner: mars
last_verified: '2026-08-12'
aliases: []
error_signatures: []
---

# Alerts at session open (S1529)

## Overview

- **BQ:** `build:bq-alerts-at-open-s1529`.
- **Repos / surfaces:**
  - `koskadeux-mcp` — `scripts/ground_truth_open_items.py` (collector + publisher, sole writer of the entity), `tests/test_ground_truth_alerts_s1529.py`.
  - `ops-ai-market` — `src/components/build-queue/OpenItemsPanel.tsx`, `src/types/index.ts`, `src/components/build-queue/__tests__/OpenItemsPanel.test.tsx`.
  - Living State — `infra:open-items-board`, key `body.alerts`.
- **Why it exists.** Twice in one month a system was screaming into a void for days or months and it reached the operator only because someone happened to look. GitHub issues were the first case: four had been open since March, one since 2026-03-16, and nobody had read them. The operator gets one line at session open; if a signal is not on that line it does not exist.

## Capabilities

| Capability | Status | Where | Evidence |
|---|---|---|---|
| Collect GitHub issue alerts at every session open | SHIPPED | `ground_truth_open_items.py` | koskadeux-mcp main `41ccff2e`; Gate 3 R1 unanimous approve (CC `9a06eb97`, Kimi `40286e81`, GLM `5b51408c`) |
| Publish alerts into `infra:open-items-board` | SHIPPED | same script, `--publish` | entity v100 at first live run; v102 carried 4 real alerts on 2026-08-12 |
| One combined tally on the operator's open line | SHIPPED | same script | S1532 |
| Render alerts on `https://ops.ai.market/build-queue` | SHIPPED | `OpenItemsPanel.tsx` | S1532 |
| Unreachable source never renders as zero | SHIPPED | collector + panel | see Acceptance criteria AC-3 |
| Sources beyond GitHub (uptime, expiring credentials) | NOT BUILT, DELIBERATELY | — | a new source is admitted only once its silence has actually cost us; see Changes and maintenance |
| Severity levels, routing, stored alert state | NOT BUILT, DELIBERATELY | — | see Changes and maintenance |

## Architecture & interactions

```
session open ──> ground_truth_open_items.py --publish
                   │
                   ├── git remotes + runbook index + deploy marker ──> open items (12)
                   └── GitHub API ────────────────────────────────────> alerts (N)
                                       │
                                       ▼
                         Living State  infra:open-items-board
                                 body.items[]   body.alerts{}
                                       │
                                       ▼
                    ops.ai.market/build-queue  OpenItemsPanel.tsx
```

Two rules hold this together and both are load-bearing:

1. **Sole writer.** `ground_truth_open_items.py --publish` is the only thing that writes `infra:open-items-board`. Nothing that reports its own progress may write it. The board previously rendered Living State build-queue entities, which was the machinery's own account of itself.
2. **The collector reads outside systems only.** It never consults Living State. A collector that asked our own records whether our own records were healthy would tell us what we already believe.

The alerts block is **additive and optional**. Snapshots published before S1529 have no `alerts` key and the page must behave exactly as it did before on them.

Live shape:

```json
"alerts": {
  "status": "ok",              // "ok" | "unavailable"
  "count": 4,
  "unreachable": 0,
  "sources": [
    { "source": "github", "status": "ok",
      "alerts": [ { "source": "github", "title": "...", "age": "2026-03-23",
                    "url": "https://github.com/..." } ] }
  ]
}
```

An unreachable source is `{ "source": name, "status": "unreachable", "detail": "one line" }` with **no** `alerts` array. A wholly failed collector is `{ "status": "unavailable", "detail": "...", "sources": [] }` with no `count` and no `unreachable`.

## Agent capabilities

| Actor | May | May not |
|---|---|---|
| Either instance (vulcan, mars) | run `--publish` at session open; read the entity | hand-edit `infra:open-items-board` |
| Any other agent or job | read the entity | write it, under any circumstance |
| ops.ai.market | read and render | write anything; the page is read-only by design |

## How to operate

At every session open, first message, one line, nothing more:

```bash
python3 /Users/max/koskadeux-mcp/scripts/ground_truth_open_items.py --publish
```

Expected shape: `https://ops.ai.market/build-queue - N open items, M alerts`. Give the operator the URL and the counts. Do not paste the list, do not summarise it, do not rank it. If the publish step fails, say so plainly on that same line and give the count from the local run.

Read the alerts themselves on the page, not in chat.

## When it breaks

| Symptom | First check | Likely cause |
|---|---|---|
| Open line shows items but no alert count | `state_get infra:open-items-board` → is `body.alerts` present? | running an old collector; the entity predates S1529 |
| `alerts unavailable` on the page | collector output for the GitHub call | GitHub API unreachable or credential expired — this is the honest state, not a bug |
| An alert count of 0 with a source listed as unreachable | this is a defect, see Acceptance criteria AC-3 | zero and unknown have been conflated somewhere |
| Page shows alerts, open line does not, or the two totals differ | both halves computing the tally | the two halves have drifted; they must agree |
| Board and page both stale | `body.generated_at`, panel marks stale past 24h | nobody ran `--publish`; the page correctly shows stale rather than guessing |

## Repair

- **Stale board.** Run `--publish`. Never hand-edit the entity to look current.
- **Alert that is no longer true.** Fix it at source: close the GitHub issue with evidence. The collector is a mirror; do not filter at the mirror. Four health-check issues, one Stripe/Doppler issue and one unreproducible issue were closed this way on 2026-08-12 (S1532), taking the count from 4 to 1.
- **An alert nobody can act on.** Close it with the reason, as above. An issue nobody can act on displaces ones that can, because the operator only reads one line.
- **Source unreachable.** Leave it visible. Do not suppress it, do not default it to zero.

## Changes and maintenance

This is deliberately small, and the smallness is the design, not an unfinished state:

- No severity levels. No routing. No stored alert state. No new alerting stack.
- A new source is admitted **only once its silence has actually cost us**, and only with a one-line entry that renders like GitHub's.
- Every extension keeps the honesty rules in Acceptance criteria. Anything that could make an unreachable source look healthy is rejected on sight.

Known forward work, tracked elsewhere, do not duplicate here: Vulcan is building the path that feeds these alerts to Codex for triage, fix, or escalation before they reach the operator. When that lands, this panel will need to show what has been **done**, not only what is outstanding. That is a change to this page's meaning and should be specified before it is built.

## Acceptance criteria

- **AC-1.** At every session open the operator gets one line: URL, open-item count, alert count.
- **AC-2.** The two halves agree. The tally on the open line and the tally on the page are the same number for the same entity state.
- **AC-3.** A source that could not be reached is **never** rendered as zero alerts. `unreachable > 0` shows a visible marker naming each unreachable source and its detail line.
- **AC-4.** `alerts.status == "unavailable"` shows "alerts unavailable" and falls the combined tally back to branch items only. It does not show zero.
- **AC-5.** An absent `alerts` key renders exactly as the page did before S1529. Nothing breaks on an old snapshot.
- **AC-6.** The page adds no write path. It is read-only by design and stays that way.
- **AC-7.** Tests pass **merged into main**, not only on the branch. A previous chunk of this BQ shipped an assertion pinned to one end of a git diff: green on the branch, red forever after merge. Always run the merged-into-main scenario before merging and ask reviewers for it explicitly.

## Maintenance

| Date | Event |
|---|---|
| 2026-08-12 | Collector + publish shipped, koskadeux-mcp main `41ccff2e`. Gate 3 R1 unanimous approve, zero blocking. Gate 4 deferral recorded on the entity. |
| 2026-08-12 | First live run: entity v100 carries the alerts block; collapse verified in production. |
| 2026-08-12 (S1532) | Combined tally and page render landed together. Alert backlog worked: 4 alerts to 1. |
