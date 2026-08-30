---
title: Task Spooler Build Queue
owner: vulcan
last_verified: '2026-08-10'
aliases:
- build-queue-runner
- codex-queue
error_signatures:
- Codex FIFO unavailable
- dispatch refused before model execution
- queued row with idle slot
- tsp command not found
- no such job
- builder output artifact missing or incomplete
- cannot remove a running job
- minimal_bridge_repo_unresolved
- minimal_bridge_base_unresolved
- jobs lost on kill
---

# Task Spooler Build Queue

## Overview


## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Task Spooler binary installed on Titan-1 | SHIPPED | `/opt/homebrew/bin/ts` | Smoke-proven S1488, Homebrew formula task-spooler 1.0.4 | 2026-08-09 |
| Immediate job handle on enqueue | SHIPPED | `/opt/homebrew/bin/ts` | Two enqueues returned ids in 0.284s wall including server start | 2026-08-09 |
| Server drains with no caller attached | SHIPPED | `/opt/homebrew/bin/ts` | Caller exited, two jobs ran to completion unattended | 2026-08-09 |
| Independent queue per repository | SHIPPED | `koskadeux_mcp/tsp_queue.py` | Two sockets ran concurrently, smoke-proven S1488 | 2026-08-09 |
| Exit code and queue-output capture per job | SHIPPED | `/opt/homebrew/bin/ts` | Task Spooler smoke coverage; queue output is separate from the bridge's durable builder transcript | 2026-08-10 |
| Bridge integration (dispatch enqueues, never waits) | SHIPPED | `koskadeux_mcp/bridge_runner.py` | `tests/test_tsp_queue.py`, `tests/unit/test_c2_minimal_bridge_routing.py` | 2026-08-10 |
| Durable builder transcript and test-output artifacts | SHIPPED | `koskadeux_mcp/minimal_bridge.py` | `tests/test_minimal_bridge.py` covers clean exit, timeout, crash and no-change paths | 2026-08-10 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Task Spooler binary | `/opt/homebrew/bin/ts` | Per-socket server state and Task Spooler's own output files | Any shell command | On macOS Homebrew the binary is `ts`. It is `tsp` only on Debian/Ubuntu. Never hardcode `tsp`. |
| ts server | Auto-started by the first `ts` invocation on a socket | Same | The jobs it supervises | One server per `TS_SOCKET`. It owns the queue and drains it whether or not any caller is attached. |
| Queue socket | `TS_SOCKET` env var | Unix socket file | One per repository | A distinct socket is a fully independent queue. This is how per-repository serialisation is achieved: a koskadeux-mcp build must never block an ai-market-backend build. |
| tsp_queue wrapper | `koskadeux_mcp/tsp_queue.py` | durable socket/slot files beneath `KD_TS_SOCKET_DIR`; default `/Users/max/koskadeux-state/ts-sockets` mode `0700` | `ts` binary | Thin wrapper: enqueue, list, output, remove, kill. Resolves the binary from `KD_TS_BIN` (default `ts`). This root is independent of `KOSKADEUX_DURABLE_STATE_DIR`. |
| bridge runner | `koskadeux_mcp/bridge_runner.py` | job specs, reports, `*.builder-output.log`, and `*.tests-output.log` under `KD_TS_JOB_DIR`; default `/Users/max/koskadeux-state/ts-sockets/jobs` | `minimal_bridge.dispatch` | The process ts actually executes. Reads a job spec, streams combined output to the durable artifact, runs the build, and writes the report. Nothing may block on it. |
| legacy SQLite queue | no current source consumer | `/var/tmp/koskadeux/control/codex_queue.sqlite3` if residue exists | none | Retired residue: the former consumer was removed. Preserve it; do not migrate, query, or reactivate it under S1456. |
| minimal bridge | `koskadeux_mcp/minimal_bridge.py` `dispatch()` | ephemeral Git worktrees under `/var/tmp/koskadeux/minimal-bridge-worktrees/`; durable reports/transcripts under the job directory; durable outcomes default `/Users/max/koskadeux-state/bridge_outcomes.db` | git, Codex CLI | Build semantics only. It streams combined builder output before preservation/push and records artifact paths, byte counts, completeness, exit code and explicit test status. Serialisation is ts's job. |
| dispatch handler | `tools/agents.py _dispatch_via_minimal_bridge` | — | tsp_queue | Resolves base_sha, writes the job spec, enqueues, returns a handle immediately. It MUST NOT wait for the build. |

S1456 does not relocate any Task Spooler socket, slot marker, job spec, report,
builder/test transcript, or `bridge_outcomes.db`: those defaults are already
durable and have their own `KD_TS_*` / `KD_BRIDGE_*` contracts. It also does not
make Task Spooler's queue server state a member of the five-record migration.

### Architecture & interactions.1 Why the previous queue was replaced

The hand-written SQLite FIFO at `/var/tmp/koskadeux/control/codex_queue.sqlite3` produced seven defects, catalogued from a live end-to-end observation on 2026-08-09 09:00-09:46 UTC (Mars S1487 field report, folded to `build:bq-minimal-builder-bridge-s1455` `phase2_queue_acceptance_criteria_s1488`):

1. A task reported terminal to its caller left its row `queued`.
2. A free slot did not drain: promotion only happened while some caller was itself blocking inside the acquire loop.
3. Liveness lied in two different ways. The legacy bridge wrote `heartbeat_at` once at claim and never advanced it across a 37-minute live run. The minimal bridge swept by process liveness but recorded the shared MCP server PID, which never dies, so orphaned rows were unreapable by construction.
4. The dispatch handle was returned after the wait, not before, so an envelope loss was indistinguishable from a real failure and caused duplicate dispatches on both instances within 25 minutes.
5. One global FIFO head-of-line blocked unrelated repositories.
6. No supported recovery command and no runbook. Recovery was a hand-written SQL UPDATE.
7. The unit suite wrote into the live queue; nineteen leaked rows are on record.

Every one of these is a solved problem in any mature job queue. Task Spooler solves all seven with a binary and no code of ours.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan / Mars | Dispatch a build | `dispatch_mp_build` (enqueues via tsp_queue, returns a handle) | operator | COMPLETE |
| Vulcan / Mars | Inspect, unblock or clear the queue | `ts -l`, `ts -c`, `ts -r`, `ts -K` per How to operate | operator | COMPLETE |
| MP (Codex) | Build, including on this control surface (Max ruling S1488 event `6005ec17`: Codex may edit any builder control file; its only rule is that it cannot review its own work as a Council member, CORE S4) | minimal bridge | builder | COMPLETE |
| Council (CC/Kimi/GLM) | Gate 3 correctness adjudication | council dispatch | reviewer | COMPLETE |

## How to operate

```yaml operate
- id: E-01
  trigger: An operator needs to see everything currently queued or running for a repository
  pre_conditions:
    - Task Spooler installed (`command -v ts` returns `/opt/homebrew/bin/ts`)
    - The queue key for the repository is known
  tool_or_endpoint: TS_SOCKET=<socket-for-repo> ts -l
  argument_sourcing:
    arg: TS_SOCKET is the per-repository socket under KD_TS_SOCKET_DIR
  idempotency: IDEMPOTENT
  expected_success:
    shape: "Table with columns ID, State, Output, E-Level, Times(r/u/s), Command"
    verification: "State is one of queued, running, finished. E-Level is the exit code and is populated only once finished."
  expected_failures:
    - signature: tsp command not found
      cause: "The binary is `ts` on macOS Homebrew, not `tsp`. `tsp` is the Debian package name."
  next_step_success: Read the row you need; use E-02 for queue output and E-06 for builder evidence
  next_step_failure: See F-03

- id: E-02
  trigger: An operator needs Task Spooler's queue output or exit code of a specific job
  pre_conditions:
    - The job id is known from E-01
  tool_or_endpoint: TS_SOCKET=<socket> ts -c <id>
  argument_sourcing:
    arg: id from the ID column of `ts -l`
  idempotency: IDEMPOTENT
  expected_success:
    shape: "The bridge runner's captured queue stdout/stderr"
    verification: "Cross-check the E-Level column in `ts -l` for the exit code"
  expected_failures:
    - signature: no such job
      cause: "The job id belongs to a different socket, or the server was killed and restarted"
  next_step_success: Done
  next_step_failure: Confirm you are on the right TS_SOCKET

- id: E-06
  trigger: An operator needs the builder's account of its work or the post-build test evidence
  pre_conditions:
    - The job report path is known from E-04 or the persisted job spec
    - The report exists, or the job has reached a terminal Task Spooler state
  tool_or_endpoint: Read `report_path`, then read the report's `builder_output_path`; if `tests_output_path` is non-null, read that artifact too
  argument_sourcing:
    arg: Artifact paths come from the job spec/report, never from a guessed temporary filename
  idempotency: IDEMPOTENT
  expected_success:
    shape: "Report contains builder_output_path, builder_output_bytes, builder_output_complete, builder_exit_code, terminal_status, tests_status, and (when configured) tests_output_path"
    verification: "The builder artifact exists for clean_exit, timeout, crashed, and nothing_changed. tests_status is one of not_configured, passed, failed, or unavailable; clean_exit alone is not test evidence."
  expected_failures:
    - signature: builder output artifact missing or incomplete
      cause: "Evidence capture failed; do not treat the build as verified and do not discard any preserved work"
  next_step_success: Review the retained transcript and diff, then apply the relevant Gate 3 procedure
  next_step_failure: Preserve the report/spec and inspect the isolated worktree before any new dispatch

- id: E-03
  trigger: A queued job must be withdrawn before it runs
  pre_conditions:
    - The job is in state `queued`, not `running`
  tool_or_endpoint: TS_SOCKET=<socket> ts -r <id>
  argument_sourcing:
    arg: id from `ts -l`
  idempotency: IDEMPOTENT
  expected_success:
    shape: "Job disappears from `ts -l`"
    verification: "Re-run `ts -l` and confirm the row is gone"
  expected_failures:
    - signature: cannot remove a running job
      cause: "Use `ts -k <id>` to kill a running job, or let it finish"
  next_step_success: Done
  next_step_failure: See G-02

- id: E-04
  trigger: A build must be dispatched
  pre_conditions:
    - The target checkout is at the intended base SHA
    - The expected branch is a build/* branch
  tool_or_endpoint: dispatch_mp_build
  argument_sourcing:
    arg: "caller_instance, expected_branch, repo, task, ref_entity, timeout_s"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: '{success: true, status: "queued", task_id, ts_job_id, queue_key, report_path, builder_output_path}'
    verification: "The handle comes back immediately. `ts -l` shows the job. The call MUST NOT wait for the build."
  expected_failures:
    - signature: minimal_bridge_repo_unresolved
      cause: "Pass the canonical org/repo key, e.g. aidotmarket/ai-market-backend, not a bare repo name"
    - signature: minimal_bridge_base_unresolved
      cause: "The configured checkout's HEAD did not resolve to a 40-hex SHA"
  next_step_success: Poll the report path or `ts -l`; do not block
  next_step_failure: Fix the argument and dispatch again; nothing was queued

- id: E-05
  trigger: The ts server for a repository must be restarted or cleared entirely
  pre_conditions:
    - No job you care about is running (`ts -l` shows no `running` row)
    - Peer instance has been told, because a restart loses queued jobs
  tool_or_endpoint: TS_SOCKET=<socket> ts -K
  argument_sourcing:
    arg: TS_SOCKET for the affected repository only
  idempotency: IDEMPOTENT
  expected_success:
    shape: "Server exits; next `ts` invocation on that socket starts a fresh one"
    verification: "`ts -l` returns an empty table"
  expected_failures:
    - signature: jobs lost on kill
      cause: "EXPECTED. ts holds the queue in the server process. Queued jobs do not survive a kill. This is the accepted trade for having no broker; the durable record of what was dispatched lives in the bridge outcomes DB, not in ts."
  next_step_success: Re-dispatch anything that was queued and had not started
  next_step_failure: See F-03
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Dispatch returned a transport or gateway error and you do not know whether the build is running | Envelope loss on a call that waited; or a genuine refusal before enqueue | `TS_SOCKET=<socket> ts -l` for a matching job, then `git ls-remote origin refs/heads/<expected_branch>` | G-01 | CONFIRMED |
| F-02 | You are about to re-dispatch after an error | The first dispatch may have succeeded | ALWAYS run F-01 first. Re-dispatch duplicates cost and can collide on the same branch. Two instances did exactly this within 25 minutes on 2026-08-09. | G-01 | CONFIRMED |
| F-03 | `tsp: command not found` | The macOS Homebrew binary is `ts`; `tsp` is the Debian name | `command -v ts` | G-03 | CONFIRMED |
| F-04 | `ts` runs but behaves like a timestamp filter | `moreutils` is installed and shadows Task Spooler; both ship a `ts` | `brew list --formula \| grep -x moreutils` and `ts -h \| head -1` (Task Spooler prints `usage: ts [action] ...`) | G-03 | HYPOTHESIZED |
| F-05 | Rows sit `queued` in the OLD SQLite queue while nothing is running | Legacy defect: the owner PID recorded is the shared MCP server, which never dies, so the sweep can never fire | `sqlite3 /var/tmp/koskadeux/control/codex_queue.sqlite3 "select ticket,state,pid from codex_queue where state in ('queued','running');"` then check whether that pid is the MCP server | G-02 | CONFIRMED |
| F-06 | A build for one repository is not starting while an unrelated repository's build runs | Everything is sharing one socket instead of one socket per repository | Compare `TS_SOCKET` values used by the two dispatches | G-04 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: dispatch handler
  root_cause: A dispatch that waits inside the call can exceed the transport window, so the caller sees an error while the job is queued or running.
  repair_entry_point: Do not repair by re-dispatching. Verify first.
  change_pattern: "Run `ts -l` on the repository socket and `git ls-remote origin refs/heads/<branch>`. If a job exists or the branch moved, the dispatch SUCCEEDED - wait for it. Only dispatch again if both checks are negative. The permanent fix is that dispatch returns a handle before it queues, which is the point of this integration."
  rollback_procedure: none required, this is a diagnostic procedure
  integrity_check: "The branch head after the build differs from the base SHA you dispatched from"

- id: G-02
  symptom_ref: F-05
  component_ref: legacy SQLite queue
  root_cause: "Orphaned rows whose recorded owner PID is the shared MCP server process. `_pid_live` returns True forever, so `_recover_dead` can never sweep them, and strict FIFO head-of-line means every later job is blocked indefinitely."
  repair_entry_point: /var/tmp/koskadeux/control/codex_queue.sqlite3
  change_pattern: "UPDATE codex_queue SET state='cancelled', finished_at=strftime('%s','now'), terminal_reason='<who cleared it and why>' WHERE ticket IN (<ids>) AND state='queued'; ALWAYS record a terminal_reason naming the instance and the cause - both operators have relied on reading each other's reasons. Tell the peer on the bus, because a cleared row may be theirs."
  rollback_procedure: "None. Cancelling a queued row destroys no work; the job never started. Re-dispatch if it was wanted."
  integrity_check: "select count(*) from codex_queue where state in ('queued','running') returns only rows that genuinely have a live builder"

- id: G-03
  symptom_ref: F-04
  component_ref: Task Spooler binary
  root_cause: moreutils and task-spooler both install an executable named `ts`
  repair_entry_point: Homebrew
  change_pattern: "Do not uninstall either blindly. Set KD_TS_BIN to the absolute path of the Task Spooler binary and reference that everywhere. If moreutils must coexist, `brew unlink moreutils` is reversible; uninstalling is not necessary."
  rollback_procedure: "brew link moreutils"
  integrity_check: "$KD_TS_BIN -h | head -1 prints `usage: ts [action] [-ngfmdE] ...`"

- id: G-04
  symptom_ref: F-06
  component_ref: Queue socket
  root_cause: A single shared socket serialises repositories that have no contention with each other. Each build already gets its own git worktree, so cross-repository serialisation buys nothing and cost a production fix roughly 50 minutes on 2026-08-09.
  repair_entry_point: koskadeux_mcp/tsp_queue.py socket resolution
  change_pattern: "Derive TS_SOCKET from the repository identity so each repository has its own queue. Verify by enqueuing on two repositories at once and confirming both run."
  rollback_procedure: "Point both back at one socket; behaviour degrades to global serialisation, it does not break."
  integrity_check: "Two jobs on different queue keys are both in state `running` at the same time"
```

## Changes and maintenance

### H.1 Invariants

- Nothing a caller touches may wait. Dispatch returns a handle before anything queues. This is a Max directive (S1488) and a hard acceptance criterion, not a preference.
- Serialisation is scoped to real contention. Different repositories never block each other.
- We do not write queue code. If a queue behaviour is missing, first establish whether Task Spooler already provides it.
- Tests never touch a live queue. `KD_TS_SOCKET_DIR` must be redirected to a temp path in every test.
- A job's terminal state and its caller's answer are never allowed to disagree.
- Combined builder stdout/stderr is streamed to a durable per-job artifact before preservation or push; no terminal path may discard it.
- A report records whether tests were not configured, passed, failed, or unavailable. `clean_exit` is never a substitute for test evidence.

### H.2 BREAKING predicates

- Reintroducing any caller-side wait, poll loop, lease, heartbeat or PID-liveness check on the dispatch path.
- Returning the dispatch handle after the queue wait rather than before.
- Collapsing per-repository sockets back to one global queue.
- Making the ts binary name a hardcoded literal rather than `KD_TS_BIN`.

### H.3 REVIEW predicates

- Changing the slot count away from 1 per repository socket. The reason the old queue used one slot was never recorded; if concurrency is enabled, the shared `~/.codex` home is the collision candidate to settle first, because the minimal bridge inherits the environment and does not seed a private `CODEX_HOME` per run (the legacy bridge did).
- Adding a broker, daemon or queue library. The whole point of this choice is that there is none.

### H.4 SAFE predicates

- Changing socket directory location via `KD_TS_SOCKET_DIR`.
- Adding read-only inspection helpers over `ts -l`.
- Adding queue keys for new repositories.

### H.5 Boundary definitions

#### module

`koskadeux_mcp/tsp_queue.py` (queue wrapper), `koskadeux_mcp/bridge_runner.py` (the process ts executes), and `koskadeux_mcp/minimal_bridge.py` (builder execution and evidence capture).

#### public contract

`dispatch_mp_build` returns `{success, status: "queued", task_id, ts_job_id, queue_key, report_path, builder_output_path, base_sha, expected_branch}` immediately and never blocks. The terminal report adds the durable builder transcript and explicit test evidence fields. Existing refusal `error_type` strings (`minimal_bridge_repo_unresolved`, `minimal_bridge_base_unresolved`) are unchanged.

#### runtime dependency

Homebrew formula `task-spooler` 1.0.4, binary `ts`. No broker, no daemon of ours, no Python queue library.

#### config default

`KD_TS_BIN=ts`, `KD_TS_SOCKET_DIR=/Users/max/koskadeux-state/ts-sockets` (0700), one slot per socket.

### H.6 Adjudication

Queue behaviour questions are settled by reading Task Spooler's own documentation and by measurement on Titan-1, not by writing new rules. Correctness of any change to this surface is adjudicated at Gate 3 by the Council, per CORE S4. Where this runbook and `builder-controls.md` overlap, builder-controls is authoritative for what happens after the builder starts and this runbook is authoritative for how the job got there.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - E-04
    scenario: An operator dispatches a build while another build is already running on the same repository.
    expected_answers:
      - kind: tool_call
        tool: dispatch_mp_build
        argument_keys:
          - caller_instance
          - expected_branch
          - repo
    weight: 0.1
  - id: I-02
    type: operate
    refs:
      - E-01
    scenario: An operator needs to see everything queued or running for one repository.
    expected_answers:
      - kind: tool_call
        tool: ts
        argument_keys:
          - TS_SOCKET
    weight: 0.1
  - id: I-03
    type: operate
    refs:
      - E-02
      - E-03
    scenario: A queued build is no longer wanted and must be withdrawn before it starts.
    expected_answers:
      - kind: tool_call
        tool: ts
        argument_keys:
          - TS_SOCKET
          - id
    weight: 0.1
  - id: I-04
    type: isolate
    refs:
      - F-01
      - F-02
    scenario: A dispatch call returns a generic transport error and the operator does not know whether the build is running.
    expected_answers:
      - kind: human_action
        verb: verify
        object: whether a job or a moved branch already exists before re-dispatching
        target: Titan-1
    weight: 0.15
  - id: I-05
    type: isolate
    refs:
      - F-03
    scenario: A new operator runs tsp -l on Titan-1 and gets command not found.
    expected_answers:
      - kind: classification
        label: WRONG_BINARY_NAME
    weight: 0.05
  - id: I-06
    type: isolate
    refs:
      - F-06
    scenario: A backend build will not start while an unrelated koskadeux-mcp build runs.
    expected_answers:
      - kind: classification
        label: SHARED_SOCKET_HEAD_OF_LINE
    weight: 0.1
  - id: I-07
    type: repair
    refs:
      - F-05
      - G-02
    scenario: Rows sit queued in the legacy SQLite queue while no builder runs and the slot is idle.
    expected_answers:
      - kind: human_action
        verb: cancel
        object: orphaned queued rows with a recorded terminal_reason, then notify the peer
        target: legacy codex_queue database
    weight: 0.1
  - id: I-08
    type: repair
    refs:
      - G-04
    scenario: Per-repository serialisation has regressed to a single global queue.
    expected_answers:
      - kind: human_action
        verb: repartition
        object: queue sockets so each repository has its own
        target: koskadeux_mcp/tsp_queue.py
    weight: 0.1
  - id: I-09
    type: evolve
    refs:
      - H.2
    scenario: A proposed change makes the dispatch handler wait for the queue before returning its handle.
    expected_answers:
      - kind: classification
        label: BREAKING_CALLER_BLOCKS
    weight: 0.1
  - id: I-10
    type: evolve
    refs:
      - H.3
    scenario: Someone proposes raising the slot count above one to run builds concurrently.
    expected_answers:
      - kind: classification
        label: REVIEW_CONCURRENCY_UNSETTLED
    weight: 0.05
  - id: I-11
    type: ambiguous
    refs:
      - E-05
      - G-01
    scenario: A build has produced no output for forty minutes and an operator wants to clear the queue.
    expected_answers:
      - kind: human_action
        verb: distinguish
        object: a slow live build from a stalled one before killing anything
        target: Titan-1
    weight: 0.05
```

### Acceptance criteria.1 Weight Justification

Weights are deliberately unequal, one line per scenario.

- I-01 (0.1): the ordinary dispatch path; frequent, but it has a single well-drilled answer.
- I-02 (0.1): the ordinary inspection path; frequent and cheap, weighted at the baseline.
- I-03 (0.1): withdrawing a queued job; ordinary, and mistakes here are reversible.
- I-04 (0.15): highest weight. Every real cost this surface has inflicted came from misreading a transport error as a build failure, twice in one morning, by both instances independently.
- I-05 (0.05): lowest weight. One short fact, and getting it wrong costs seconds of confusion.
- I-06 (0.1): cross-repository head-of-line blocking; it stalled a production fix, but the diagnosis is mechanical once suspected.
- I-07 (0.1): clearing orphaned legacy rows; damaging if done carelessly, hence baseline rather than low.
- I-08 (0.1): repairing socket partitioning; a real regression path with a clear repair.
- I-09 (0.1): the caller-blocks invariant; violating it recreates the original defect wholesale.
- I-10 (0.05): lowest weight. A single REVIEW classification with one prerequisite to name.
- I-11 (0.05): lowest weight. Judgement under ambiguity, but the safe default (do not kill a running job) is short and unambiguous.

## Maintenance

```yaml lifecycle
last_refresh_session: S1498
last_refresh_commit: 1e8e23db698bad3fa33d4e79c600e06535a671de
last_refresh_date: 2026-08-10T11:01:39Z
owner_agent: vulcan
refresh_triggers:
  - The bridge or durable builder-output contract changes; refresh Capabilities/Architecture & interactions/How to operate and record the implementation SHA
  - Task Spooler is upgraded past 1.0.4
  - Slot count moves away from 1, or the CODEX_HOME concurrency question is settled
  - The legacy SQLite queue in codex_cli_bridge.py is deleted; remove F-05 and G-02
scheduled_cadence: 90d
first_staleness_detected_at: null
```
