---
system_name: browser-runner
purpose_sentence: Operate, diagnose, and evolve the isolated macOS GUI session on Titan-1 that runs real, headed Google Chrome for agent-driven browser journeys without ever appearing on Max's desktop.
owner_agent: vulcan
escalation_contact: Max (account password, reboot/re-login of the kdbrowser session, any change to sudo posture); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The `kdbrowser` macOS user on Titan-1, its GUI session, the localhost job runner (`com.koskadeux.browser-runner`), the job contract used to drive real headed Chrome, and the isolation guarantees. NOT authoritative for the e2e-harness charter/agent-loop mechanics (owner BQ-E2E-TESTING-FRAMEWORK-S1152, repo aidotmarket/e2e-harness), for AIM Data itself (aim-data-release-process.md), or for Titan-1 host inventory (titan-1.md).
linter_version: 1.0.0
---

# Browser Runner — isolated headed Chrome on Titan-1

> Headed Chrome needs a real macOS graphical session, and macOS refuses to place a window off-screen (a window positioned at -32000,-32000 is clamped back onto the visible display; verified S1211). So a browser journey run as `max` always lands on Max's desktop. This runbook covers the fix: a second macOS user (`kdbrowser`) whose own GUI session hosts a localhost job runner. Mars/Vulcan post Playwright jobs to it; real Google Chrome opens, renders, and is driven inside that session, invisible to whoever is using the machine. Stood up S1211 after the S1209 AIM Data walkthrough proved that headed runs and Max's own work cannot share one desktop.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| `kdbrowser` local macOS account (uid 502) | The isolated GUI session that hosts the browser | Titan-1 local directory service (`dscl . -read /Users/kdbrowser`) | macOS / Max (creation needs sudo) |
| `kdbrowser` account password | Needed to (a) log the session in at the console, (b) run commands as that user via `su` without root | Infisical `TITAN_KDBROWSER_PASSWORD`, project **koskadeux-mcp**, env **prod**, root path (`secrets.ai.market`). Set + verified S1213 (rotated off the `something` placeholder). Fetch: `infisical secrets get TITAN_KDBROWSER_PASSWORD --projectId 0943f641-faee-4324-b337-0d50c276e4a9 --env prod --plain --silent --domain https://secrets.ai.market`, or the API at `/api/v3/secrets/raw` with the sysadmin token. Never in the repo, a plist, or a dotenv. See §G-04 if absent | Infisical (`secrets.ai.market`) |
| `com.koskadeux.browser-runner` LaunchAgent | Starts the job runner automatically whenever the `kdbrowser` session logs in | `/Users/kdbrowser/Library/LaunchAgents/com.koskadeux.browser-runner.plist` | this runbook |
| Job runner | HTTP job surface on `127.0.0.1:8790` | `/Users/kdbrowser/kd-browser-runner/runner.py` | this runbook |
| Jobs directory | The only path the runner will execute scripts from | `/tmp/kd-browser-jobs` (mode 777; scripts world-readable) | this runbook |
| Python + Playwright | Drives the browser | `/Users/max/Projects/ai-market/e2e-harness/.venv/bin/python` (readable by `kdbrowser`) | e2e-harness repo |
| Google Chrome | The real browser under test | `/Applications/Google Chrome.app` (Playwright `channel="chrome"`) | macOS |
| Fast user switching | The one-time human action that creates the GUI session | System-level `MultipleSessionEnabled=1`; menu item via `com.apple.controlcenter` | macOS / Max |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Isolated GUI session hosting real headed Chrome, invisible to the console user | SHIPPED | `/Users/kdbrowser/kd-browser-runner/runner.py` | S1211 live using macOS fast user switching + `kdbrowser` account (uid 502): job drove Chrome 148 (UA `Chrome/148.0.0.0`, no `Headless` token) through AIM Data login to datasets; window survived >15s; Max saw nothing | 2026-07-14 |
| Job runner HTTP surface (`GET /health`, `POST /run`) bound to localhost | SHIPPED | `/Users/kdbrowser/kd-browser-runner/runner.py:Handler` | S1211 live: health + two job executions (`probe.py`, `aimdata-proof.py`) | 2026-07-14 |
| Path confinement — only scripts under `/tmp/kd-browser-jobs` execute | SHIPPED | `/Users/kdbrowser/kd-browser-runner/runner.py:Handler.do_POST` | S1211: realpath prefix check rejects paths outside the jobs dir | 2026-07-14 |
| Per-job environment injection (credentials passed at call time, never at rest) | SHIPPED | `/Users/kdbrowser/kd-browser-runner/runner.py:Handler.do_POST` | S1211: `env` field merged into an `os.environ` copy; synthetic buyer-01 credentials injected per job | 2026-07-14 |
| Autostart on session login | SHIPPED | `/Users/kdbrowser/Library/LaunchAgents/com.koskadeux.browser-runner.plist` | S1211: `RunAtLoad` + `KeepAlive`; runner answered `/health` immediately after Max logged the session in | 2026-07-14 |
| Survives reboot without a human | BROKEN | `/Users/kdbrowser/Library/LaunchAgents/com.koskadeux.browser-runner.plist` | No auto-login configured for `kdbrowser`; after any Titan-1 reboot the session is gone until someone logs it in (§F-01/§G-01) | 2026-07-14 |
| Caller authentication on the job surface | PARTIAL | `/Users/kdbrowser/kd-browser-runner/runner.py:Handler.do_POST` | Any local process can post a job; accepted risk on a single-operator host; see §F-05 and §H.1 | 2026-07-14 |
| e2e-harness charters routed through the runner | PLANNED | `aidotmarket/e2e-harness` | Branch `build/real-agent-loop-20260713` is unmerged; the harness still launches Chrome in the caller's session | 2026-07-14 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| `kdbrowser` GUI session | macOS `loginwindow` (created by fast user switching) | macOS session registry (`who`, `launchctl print gui/502`) | WindowServer; the LaunchAgent | The whole isolation guarantee. Without it, headed Chrome starts and dies within seconds (`TargetClosedError`), because there is no window server to attach to. Verified S1211: with no GUI session, `launch(headless=False)` navigates once and then the target closes. |
| Job runner | `runner.py:Handler` (HTTP on `127.0.0.1:8790`) | `/tmp/kd-browser-jobs` (job scripts + artifacts) | Mars/Vulcan (`POST /run`); Playwright; Chrome | Runs as uid 502 inside the GUI session. `GET /health` returns `{ok, uid, gui_session}`. `POST /run {script, timeout, env}` executes the script with the e2e-harness venv python, cwd = jobs dir, and returns `{exit_code, stdout, stderr}` (stdout capped 20k, stderr 8k). |
| Job scripts | any `*.py` under `/tmp/kd-browser-jobs` | screenshots/artifacts written alongside, in the same dir | Playwright sync API; the product under test | Written by the calling instance as `max`, executed by `kdbrowser`. They must be world-readable (mode 644). Jobs are ephemeral by design — `/tmp` clears on reboot, and nothing in them is a system of record. |
| LaunchAgent | `com.koskadeux.browser-runner.plist` | logs at `/tmp/kd-browser-runner.log` / `.err` | launchd (gui domain of uid 502) | `RunAtLoad` + `KeepAlive`. Starts only when the session logs in; there is no system-domain daemon, deliberately — a daemon has no GUI session and therefore cannot host a browser. |
| `su` bridge | `/usr/bin/su - kdbrowser -c '<cmd>'` driven by an `expect` wrapper | none | Mars/Vulcan shell (as `max`) | How the runner is installed and repaired without root: `su` needs the *target* user's password, not sudo. Password comes from Infisical at call time. |

Prose: Mars (running as `max`) writes a Playwright script into `/tmp/kd-browser-jobs`, then POSTs its path to `127.0.0.1:8790/run` with any credentials the job needs. The runner — already alive inside the `kdbrowser` GUI session — executes it, so Chrome opens on that session's desktop. Max, logged in as himself, sees nothing. Artifacts (screenshots, transcripts) land back in the jobs directory, readable by both users.

Two facts drive every design choice here, both established empirically in S1211: headed Chrome requires a GUI session, and macOS will not let a window hide off-screen. Everything else follows.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Mars / Vulcan | Check the runner is alive | `shell_request` then `curl -s http://127.0.0.1:8790/health` | local shell as `max` | COMPLETE |
| Mars / Vulcan | Run a browser journey in the isolated session | `shell_request` then `POST /run` with a script under `/tmp/kd-browser-jobs` | local shell as `max`; per-job env injection | COMPLETE |
| Mars / Vulcan | Install or repair the runner | `shell_request` then `expect` + `su - kdbrowser` | `kdbrowser` password from Infisical | COMPLETE |
| Mars / Vulcan | Create the account, enable auto-login, change sudo posture | none | requires sudo — not held | GAP — closed only by Max running the command, or by Max granting a scoped NOPASSWD sudoers entry (§H) |
| Mars / Vulcan | Log the GUI session in after a reboot | none | requires console access | GAP — closed by enabling auto-login for `kdbrowser` (needs Max; see §G-01) |
| e2e-harness | Route charter runs through the runner | `e2e-harness run` | n/a | PLANNED — the harness still launches Chrome in the caller's session (§B) |

## §E. Operate

```yaml operate
- id: E-01
  trigger: an instance needs to drive the real UI (product verification, E2E charter, reproduction of a customer report)
  pre_conditions:
    - kdbrowser GUI session logged in
    - "runner answers /health with gui_session: true"
    - the target app is reachable from Titan-1
  tool_or_endpoint: 'POST http://127.0.0.1:8790/run with {"script": "/tmp/kd-browser-jobs/<name>.py", "timeout": <seconds>, "env": {...}}'
  argument_sourcing:
    script: written by the caller into /tmp/kd-browser-jobs, mode 644
    env: credentials fetched at call time from Infisical via e2e-harness/scripts/harness-env.sh; never written to disk
    timeout: caller's judgement; the runner returns HTTP 504 past it
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: 'HTTP 200 {exit_code: 0, stdout, stderr}'
    verification: artifacts in the jobs dir; no window on Max's screen
  expected_failures:
    - signature: exit_code != 0
      cause: job logic
    - signature: HTTP 400
      cause: script outside the jobs dir
    - signature: HTTP 504
      cause: timeout
    - signature: connection refused
      cause: §F-01
  next_step_success: read stdout/artifacts; file findings as tickets
  next_step_failure: §F; a job may mutate the product under test, so re-running is the caller's decision, not the runner's
- id: E-02
  trigger: start of any session that intends to drive the browser
  pre_conditions:
    - none
  tool_or_endpoint: GET http://127.0.0.1:8790/health
  argument_sourcing:
    arguments: n/a (no arguments)
  idempotency: IDEMPOTENT
  expected_success:
    shape: '{"ok": true, "uid": 502, "gui_session": true}'
    verification: response reports uid 502 and gui_session true
  expected_failures:
    - signature: connection refused
      cause: session not logged in — §F-01
    - signature: "gui_session: false"
      cause: runner started outside a GUI session — §F-02
  next_step_success: proceed to E-01
  next_step_failure: §G-01
- id: E-03
  trigger: first setup, or the runner files are missing or corrupt
  pre_conditions:
    - kdbrowser account exists
    - its password is retrievable
  tool_or_endpoint: "expect wrapper around /usr/bin/su - kdbrowser -c '<install script>', copying runner.py to ~/kd-browser-runner/ and the plist to ~/Library/LaunchAgents/"
  argument_sourcing:
    password: Infisical TITAN_KDBROWSER_PASSWORD
    staged_files: written by the caller to /tmp first, since max cannot write into /Users/kdbrowser
  idempotency: IDEMPOTENT
  expected_success:
    shape: both files present, owned by kdbrowser, plist mode 644
    verification: runner starts on the next session login
  expected_failures:
    - signature: su auth failure
      cause: wrong password
    - signature: permission denied
      cause: staging path not world-readable
  next_step_success: E-02; the install overwrites in place
  next_step_failure: §G-04
- id: E-04
  trigger: after any change to the runner, the account, or macOS
  pre_conditions:
    - session up
  tool_or_endpoint: run a job that reports navigator.userAgent and window size and stays open more than 15s
  argument_sourcing:
    arguments: n/a (no arguments)
  idempotency: IDEMPOTENT
  expected_success:
    shape: UA contains Chrome/ and NOT HeadlessChrome; the page is still evaluable after the wait
    verification: Max reports no window appeared
  expected_failures:
    - signature: UA says HeadlessChrome
      cause: a headless fallback crept in
    - signature: TargetClosedError
      cause: no GUI session — §F-02
  next_step_success: record the verification date in §B
  next_step_failure: §F-02
```

## §F. Isolate — Diagnosing Deviations

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `curl 127.0.0.1:8790/health` returns connection refused | The `kdbrowser` GUI session is not logged in (most often: Titan-1 rebooted); or the LaunchAgent was unloaded | `who` — is there a `kdbrowser console` line? If absent, the session is gone, not the runner | §G-01 | CONFIRMED |
| F-02 | Headed Chrome starts, navigates once, then `TargetClosedError: Target page, context or browser has been closed` within seconds | The process has no GUI session (runner was started via `su` from a shell instead of by launchd inside the session) | `GET /health` shows `gui_session: false`; also `who` shows no `kdbrowser console` | §G-02 | CONFIRMED |
| F-03 | A Chrome window appears on Max's desktop during a run | The job ran as `max` (harness or script bypassed the runner), not through `POST /run` | Check the run's `uid` in job stdout — it must be 502 | §G-03 | CONFIRMED |
| F-04 | `POST /run` returns HTTP 400 `script must live under /tmp/kd-browser-jobs` | The script was written elsewhere, or a symlink resolves outside the jobs dir | `realpath` the script path | §G-05 | CONFIRMED |
| F-05 | An unexpected job ran, or the runner executed something no instance dispatched | The job surface has no caller authentication — any local process can post to it | Read `/tmp/kd-browser-runner.log`; correlate with session records | §G-06 | HYPOTHESIZED |
| F-06 | Job fails `ModuleNotFoundError: playwright` or cannot exec the interpreter | The e2e-harness venv moved, was rebuilt, or lost world-read permission | As `kdbrowser`: `test -r /Users/max/Projects/ai-market/e2e-harness/.venv/bin/python` | §G-07 | CONFIRMED |
| F-07 | UA reports `HeadlessChrome` on a run that was supposed to be headed | The job passed `headless=True`, or `channel="chrome"` was omitted so Playwright used its bundled headless shell | Inspect the job's `launch()` call | §G-08 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: '`kdbrowser` GUI session'
  root_cause: the session is created by an interactive login and does not survive a reboot; no auto-login is configured
  repair_entry_point: macOS fast user switching (menu bar user item, then KD Browser), or the lock screen's Switch User
  change_pattern: Max logs the kdbrowser session in once with its password, then switches back to his own account. The LaunchAgent starts the runner automatically. No instance can do this step — it requires console access
  rollback_procedure: none needed; logging the session out simply returns to the previous state
  integrity_check: "who shows kdbrowser console; GET /health shows gui_session: true"
- id: G-02
  symptom_ref: F-02
  component_ref: Job runner
  root_cause: the runner was started from a shell via su (setup or testing), which has no window server, so any headed browser it spawns dies
  repair_entry_point: pkill -f kd-browser-runner/runner.py, then log the GUI session in (G-01) and let launchd start it
  change_pattern: never leave a su-started runner behind — it holds port 8790 and will shadow the real one
  rollback_procedure: n/a (kill and restart is the whole repair)
  integrity_check: "GET /health shows gui_session: true"
- id: G-03
  symptom_ref: F-03
  component_ref: Job scripts
  root_cause: the browser was launched by a process running as max — the e2e-harness still launches Chrome in the caller's session (§B PLANNED row)
  repair_entry_point: the calling code path; route it through POST /run instead
  change_pattern: any headed launch must happen inside a job script executed by the runner. Until the harness is routed through the runner, run harness charters headless, or run the journey as a runner job
  rollback_procedure: kill the stray Chrome as max — never as kdbrowser, because that kills the isolated run
  integrity_check: "job stdout reports uid: 502"
- id: G-04
  symptom_ref: F-01
  component_ref: '`su` bridge'
  root_cause: the account password is not in Infisical, or was rotated
  repair_entry_point: Infisical TITAN_KDBROWSER_PASSWORD (prod)
  change_pattern: ask Max for the password (or a rotation), store it in Infisical (project koskadeux-mcp, env prod, key TITAN_KDBROWSER_PASSWORD), and never write it to the repo, a plist, or a dotenv. su needs the target user's password — it does not need sudo, which is why no root is required for day-to-day operation. ROTATION (S1213 lesson): only Max can reset this account's password — no instance holds sudo, and the runner itself runs as uid 502 without admin, so `dscl . -passwd` needs the OLD password. Never rotate it from a shell unless the new value is written to Infisical in the SAME command; a rotation whose new value is lost cannot be undone by any instance. Always verify after a rotation with BOTH `dscl . -authonly kdbrowser <pw>` and an `su` login — a Settings-side change that does not take will still read back cleanly from the vault
  rollback_procedure: n/a (credential retrieval only)
  integrity_check: su - kdbrowser -c whoami prints kdbrowser
- id: G-05
  symptom_ref: F-04
  component_ref: Job runner
  root_cause: the runner only executes real paths under /tmp/kd-browser-jobs — deliberately, so a stray path cannot turn the runner into a general execution service
  repair_entry_point: runner.py:Handler.do_POST (prefix check)
  change_pattern: move the script into the jobs directory, mode 644. Do not widen the check
  rollback_procedure: n/a (no state changed)
  integrity_check: the job runs and returns an exit_code
- id: G-06
  symptom_ref: F-05
  component_ref: Job runner
  root_cause: no caller authentication; accepted on a single-operator host, per the Design Charter (build no machinery for an absent adversary)
  repair_entry_point: runner.py:Handler.do_POST
  change_pattern: if Titan-1 ever hosts another user or an untrusted process, add a shared-secret header read from a file only max and kdbrowser can read, and reject requests without it. Do NOT expose the port beyond 127.0.0.1 under any circumstances
  rollback_procedure: revert to the unauthenticated handler
  integrity_check: a request without the header is refused; a request with it succeeds
- id: G-07
  symptom_ref: F-06
  component_ref: Job runner
  root_cause: the runner executes jobs with the e2e-harness venv, which lives under /Users/max and must stay world-readable
  repair_entry_point: runner.py:PYTHON
  change_pattern: 'restore read permission, or repoint PYTHON at a venv the kdbrowser account owns. Chrome itself needs nothing extra — channel="chrome" uses the system Google Chrome'
  rollback_procedure: repoint PYTHON back to the previous interpreter
  integrity_check: "a trivial job (launch, goto, close) returns exit_code: 0"
- id: G-08
  symptom_ref: F-07
  component_ref: Job scripts
  root_cause: 'headless=True or a missing channel="chrome" — Playwright then uses its bundled headless shell, which is NOT the customer''s browser'
  repair_entry_point: the job's launch() call
  change_pattern: 'use p.chromium.launch(channel="chrome", headless=False). Real Chrome reports Chrome/<version>; the headless shell reports HeadlessChrome/<version> and is detectable by sites (relevant at the payment step)'
  rollback_procedure: n/a (job-local change)
  integrity_check: E-04
```

## §H. Evolve — Extending the System

### §H.1 Invariants

- The job runner binds `127.0.0.1` only. It is never exposed on the LAN, through Cloudflare, or through any tunnel.
- Jobs execute only from `/tmp/kd-browser-jobs`. The path confinement is not widened.
- Credentials reach jobs only through per-call `env` injection, fetched from Infisical at call time. Nothing at rest — not in the plist, not in a dotenv, not in the repo.
- Browser journeys that verify the customer experience use real Google Chrome (`channel="chrome"`, `headless=False`). Headless is a fallback, and its use is stated in the finding.
- The isolated session exists to keep the browser off the operator's desktop. Any change that could put a window back on Max's screen is BREAKING.
- No sudo is required to operate this system. Setup steps that need root are Max's, and they are the only ones.
- Module boundary for this system: the runner is a single file (`runner.py`); its public contract is the two HTTP routes and the job-script path convention.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- The runner binds anything other than `127.0.0.1`.
- Path confinement is removed or widened.
- Credentials are persisted at rest.
- The browser channel changes away from real Chrome for customer-journey verification.
- The isolation guarantee is weakened so a window can reach the console user's desktop.
- The `/run` request or response shape changes without a shim.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Adding caller authentication.
- Adding auto-login for `kdbrowser` (changes the host's security posture — Max decision).
- Routing the e2e-harness through the runner.
- Adding a new route.
- Changing the interpreter the runner executes jobs with.
- Granting any sudoers entry to close the §D GAP rows.

### §H.4 SAFE predicates

SAFE otherwise:
- New job scripts.
- Log or diagnostic additions.
- Timeout defaults.
- Documentation.

### §H.5 Boundary definitions

#### module

The runner is a single-file module: `runner.py`.

#### public contract

The two HTTP routes, `GET /health` and `POST /run`, plus the job-script path convention that executable scripts live under `/tmp/kd-browser-jobs`.

#### runtime dependency

The e2e-harness virtual environment and Playwright, executed through `/Users/max/Projects/ai-market/e2e-harness/.venv/bin/python`.

#### config default

The constants at the top of `runner.py`.

### §H.6 Adjudication

Two evolutions are already named and unbuilt: auto-login for `kdbrowser` (removes the only human step, at the cost of a machine that boots straight into a logged-in second session — Max's call), and harness integration (the e2e-harness launches Chrome in the caller's session today, which is the one remaining way a window can land on Max's desktop).

The more restrictive classification wins between disagreeing agents. Disputes unresolvable under the predicates escalate to Max; the ruling is added to §H.1 as a clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: An instance needs to drive AIM Data at localhost:8099 while Max works on Titan-1 — writes a job, POSTs it, gets exit_code 0, and Max sees no window.
    expected_answers:
      - kind: human_action
        action: write a job under /tmp/kd-browser-jobs, POST it to /run, verify exit_code 0, and confirm Max sees no window
    weight: 0.09090909
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: An instance opens and checks readiness — /health returns gui_session true.
    expected_answers:
      - kind: tool_call
        tool: GET http://127.0.0.1:8790/health
        arguments: "verify gui_session: true"
    weight: 0.09090909
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: The runner files are missing after a home-directory reset — reinstalled through the su bridge without root.
    expected_answers:
      - kind: human_action
        action: reinstall through the expect + su - kdbrowser bridge without root
    weight: 0.09090909
  - id: I-04
    type: isolate
    refs: [F-01, G-01]
    scenario: Titan-1 was rebooted overnight and the morning charter run fails — who shows no kdbrowser console; Max logs the session in once; the runner comes back by itself.
    expected_answers:
      - kind: human_action
        action: check who for kdbrowser console; if absent, have Max log that session in once and let the LaunchAgent restart the runner
    weight: 0.09090909
  - id: I-05
    type: repair
    refs: [F-02, G-02]
    scenario: A test runner was left running from a shell — headed jobs die with TargetClosedError; kill it and let launchd own the port.
    expected_answers:
      - kind: human_action
        action: kill the shell-started runner and let launchd inside the kdbrowser GUI session own port 8790
    weight: 0.09090909
  - id: I-06
    type: isolate
    refs: [F-03, G-03]
    scenario: A harness charter opens Chrome on Max's desktop — the job ran as max; route it through the runner or run headless.
    expected_answers:
      - kind: human_action
        action: confirm the job ran as max, then route the headed launch through POST /run or run the harness charter headless
    weight: 0.09090909
  - id: I-07
    type: isolate
    refs: [F-07, G-08]
    scenario: 'A finding claims the customer''s browser was used, but the UA says HeadlessChrome — the job launch() omitted channel="chrome".'
    expected_answers:
      - kind: human_action
        action: 'set the job launch call to p.chromium.launch(channel="chrome", headless=False) and verify the UA reports Chrome, not HeadlessChrome'
    weight: 0.09090909
  - id: I-08
    type: repair
    refs: [G-04]
    scenario: The kdbrowser password is not in Infisical — install and repair are blocked; ask Max, store it, never commit it.
    expected_answers:
      - kind: human_action
        action: ask Max for the password or rotation, store TITAN_KDBROWSER_PASSWORD in Infisical, and never commit it
    weight: 0.09090909
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: 'Proposal: expose the runner on the LAN so a laptop can drive it — BREAKING (violates the localhost invariant); rejected.'
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.09090909
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: 'Proposal: enable auto-login for kdbrowser so a reboot needs no human — REVIEW (host security posture; Max decision), not SAFE.'
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.09090909
  - id: I-11
    type: ambiguous
    refs: [F-01]
    scenario: GET /health is connection refused, and it is not yet known whether the kdbrowser GUI session is absent or the LaunchAgent was unloaded. What is the first action?
    expected_answers:
      - kind: human_action
        action: check who for a kdbrowser console line to distinguish a missing GUI session from a runner or LaunchAgent problem
    weight: 0.09090909
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1211
last_refresh_commit: 5f968f167661
last_refresh_date: '2026-07-14T00:00:00Z'
owner_agent: vulcan
refresh_triggers:
  - any change to the runner or the kdbrowser account
  - Titan-1 OS upgrade
  - harness integration landing
  - any incident where a browser window reaches the console user's desktop
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: '2026-07-14T00:00:00Z'
first_staleness_detected_at: null
```

Authorship note: Mars authored the initial runbook in S1211; either instance (Vulcan/Mars) operates it.

Initial-issue lifecycle note: the original values were "initial issue (this commit)", "90 days", and "n/a (first issue)"; the machine-readable block uses the pre-issue parent commit, canonical `90d`, and pending-harness form required by the linter.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1211 / 2026-07-14T00:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: null
word_count_delta: null
```

Conformance note: this is a new runbook, not a retrofit, so trace-matrix and word-count-delta values are not applicable; the PR check for this commit records the PASS.
