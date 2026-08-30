---
title: Reload when idle (T-2026-000602)
owner: mars
last_verified: '2026-08-14'
aliases:
- mcp-server-reload
- reloader
error_signatures:
- background build(s) running/queued; deferring
- background-build check failed
---

# Reload when idle (T-2026-000602)

## Overview

- **Ticket:** `T-2026-000602`.
- **Repo / files:** `koskadeux-mcp` — `scripts/reload_when_idle.sh` (trigger + idleness scanner), `koskadeux_mcp/tsp_queue.py` (socket discovery, strict `ts` output parsing, `require_binary`), `tests/test_reload_build_guard.sh` (18 scanner tests incl. mutation-proof coverage), `scripts/RELOAD-WHEN-IDLE.md` (in-repo operator notes).
- **Landed:** merge `b76eca5b82` to main (branch head `4993f00cda`, base `1d3443924a`), 2026-08-14. Council: CC APPROVE_WITH_NITS, GLM APPROVE_WITH_NITS at `43024eff99`; Kimi REQUEST_CHANGES at `43024eff99` then APPROVE_WITH_NITS on the fold `4993f00cda`.
- **Why it exists.** The reloader restarts the MCP server when a new main lands. Before this change its idleness check saw only legacy CC task files, so it was blind to minimal-bridge builds and a reload could kill a running build mid-commit — destroying correct work. That blindness was itself the top failure pattern the minimal bridge was built to end.

## Capabilities

| Capability | Status | Where | Evidence |
|---|---|---|---|
| Reload only when no CC task is in flight | SHIPPED | `reload_when_idle.sh` durable CC scan | pre-existing liveness semantics; path relocated by S1456 candidate |
| Reload only when no minimal-bridge build is in flight, across every `ts-*.socket` queue | SHIPPED | `reload_when_idle.sh` bridge scan + `tsp_queue.py` | 18/18 tests at `4993f00cda`; mutation-proven (guard removed → 7 bridge assertions fail, 7 legacy still pass) |
| Fail closed on any uncertainty (unreadable dirs, missing `ts` binary, unparseable output, fresh unparseable job records, fresh pre-enqueue records) | SHIPPED | scanner `ERR` paths | CC traced every enumerated path at file:line and validated parser edges against the real `/opt/homebrew/bin/ts` |
| Absent legacy task dir cannot skip the bridge scan | SHIPPED | fold `4993f00cda` | Kimi's blocking finding; regression test "absent legacy dir with running bridge build -> 1" |
| Anti-stall: stale/leaked records and orphaned old sockets drain rather than block forever | SHIPPED | staleness windows in scanner | tests 10-17 |

## Architecture & interactions

One shell script runs on a timer/trigger. It first sources
`scripts/runtime_state_paths.sh`. The S1456 candidate fixes its CC task,
deployment-marker, and secret-refresh-request paths beneath the one
`KOSKADEUX_DURABLE_STATE_DIR` root (default
`/Users/max/koskadeux-state`), exporting `KD_CC_TASKS_DIR`,
`KD_DEPLOYED_SHA_FILE`, and `KD_SECRET_REFRESH_REQUEST_FILE`. Legacy
`KOSKADEUX_STATE_DIR`, `KOSKADEUX_CC_TASKS_DIR`, and
`KOSKADEUX_PROBE_STATE_DIR` cannot redirect those records. The independent
reload lock remains `/var/tmp/koskadeux/reload_when_idle.lock.d`; only an
explicit isolated-test contract can override it.

Before reloading, the script executes an embedded Python scanner that must
print a number of in-flight builds; reload proceeds only on `0`. The scanner:
(1) scans `KD_CC_TASKS_DIR` for fresh `.meta.json` without `.done` and with a
live pid; an absent directory contributes zero and NEVER exits early; (2)
discovers every `ts-*.socket` under the already-durable bridge socket directory,
requires the `ts` binary, indexes fresh job-spec records, queries each socket
with strict parsing, and counts running/queued bridge jobs; (3) prints `ERR`
(treated as busy) on any discovery, parse, or identity failure that is not
provably stale. Task Spooler sockets and job records remain under
`/Users/max/koskadeux-state/ts-sockets`; S1456 does not migrate them.

## Agent capabilities

Either instance (vulcan/mars) may merge to koskadeux-mcp main; the merge arms the reloader for the merged code. No sub-agent operates the reloader; it is autonomous machinery.

## How to operate

- Run the scanner by hand exactly as the reloader does: source
  `scripts/runtime_state_paths.sh`, then execute the Python heredoc block in
  `scripts/reload_when_idle.sh` with `CC_TASKS_DIR="$KD_CC_TASKS_DIR"`,
  `BUILD_STALE_SECONDS`, `KD_TS_SOCKET_DIR`, and `KD_TS_JOB_DIR` set as in the
  script. `0` = idle; any positive number or `ERR` = do not reload.
- Full test suite: `bash tests/test_reload_build_guard.sh` from the repo root (expects 18/18).
- MERGE DISCIPLINE: never merge to koskadeux-mcp main while a bridge build is running; the reload the merge arms is the very thing the guard protects against. Check fresh job specs under `koskadeux-state/ts-sockets/jobs/` and `ts` per socket first.

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Reloader never fires; log shows `background-build check failed` persistently | Unreadable socket/job dir, missing `ts` binary, or a genuinely stuck fresh job record | Run the scanner by hand (How to operate); inspect the failing path it raises on | G-01 | CONFIRMED |
| F-02 | Reload killed a running build, or log shows `background build(s) running/queued; deferring` while nothing is visibly building | Guard bypassed or scanner regression | Reproduce with `tests/test_reload_build_guard.sh`; if 18/18 pass, check whether the reload path actually calls the scanner | G-02 | CONFIRMED (design) |

## Repair

- **G-01.** Fix the unreadable dir / install `ts` / remove the provably stale record (older than `BUILD_STALE_SECONDS`). Never "fix" by making an uncertain path print `0`; uncertainty must stay busy.
- **G-02.** Restore the scanner call in the reload path and re-run the suite; any change here re-runs the mutation proof (delete the bridge scan, expect the 7 bridge assertions to fail).

## Changes and maintenance

New build transports must be added to the scanner in the same change that introduces them, with fail-closed semantics and a mutation-proof test, or the reloader is blind to them — which is exactly how T-2026-000602 happened.

## Acceptance criteria

- AC-1: with any fresh live bridge job on any socket, scanner output is non-zero or `ERR`.
- AC-2: with the legacy task dir absent and a fresh live bridge job present, scanner blocks (regression test).
- AC-3: all enumerated uncertainty paths print `ERR`, never `0`.
- AC-4: provably stale artifacts drain; the reloader cannot be starved forever by leaks.

## Maintenance

ACTIVE. Owner mars. Supersedes nothing; extends the reloader that predates the minimal bridge.
