---
runbook_id: durable-runtime-state
domain: runtime-operations
status: DRAFT
authoritative_for: []
aliases: []
error_signatures: []
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-08-25
system_name: durable-runtime-state
purpose_sentence: Discovery-only candidate for the reviewed S1456 five-record durable runtime-state path, exact-preimage conflict adjudication, migration, cutover, resume, acceptance, and lossless rollback contracts.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: None while DRAFT; this page records the exact reviewed candidate contract for later independent review and does not authorize a live migration, launchd action, publication, or cutover.
linter_version: 1.0.0
---

# Durable Runtime State Relocation (S1456)

## §A. Header

This is a **DRAFT discovery document, not operating authority**. It describes
the Gate 4 remediation candidate implemented at exact `koskadeux-mcp` SHA
`5ab1da824671739b935aed8bd868289eb6997298`. The locked Gate 1 design is
`specs/BQ-DURABLE-STATE-RELOCATION-S1456-CURRENT.md` at exact SHA
`fb1802cdca61946ea25fb28bc0dd965e29e3bcf4`; Gate 2 is
`specs/BQ-DURABLE-STATE-RELOCATION-S1456-GATE2.md` in that exact code
candidate. The runbooks candidate starts from published runbooks main
`8843542562daf6bc3b5d80f6911d4136279da458` on branch
`docs/bq-durable-state-gate4-s1605`.

Candidate tests and this page do not prove a live cutover. Do not use this page
to install, unload, bootstrap, kickstart, migrate, publish, or write either live
runtime-state root. A live Gate 4 action requires separately reviewed exact
code and runbooks SHAs, explicit authorization evidence, peer-clearance
evidence, immediate preflight, and the controller's `--reviewed-live` boundary.
No secret, record content, review content, or credential belongs in a command
transcript or receipt.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| One resolver for five MCP-owned records | PLANNED | `koskadeux_mcp/runtime_state_paths.py` | Python/shell isolated path and consumer-parity tests | 2026-08-19 |
| Strict restart-history durability | PLANNED | `admin.py` | malformed/symlink/read/write/fsync and 503/no-exit tests | 2026-08-19 |
| Sanitized inventory and copy-first migration | PLANNED | `koskadeux_mcp/durable_state_cutover.py` | CLI and isolated migration tests | 2026-08-19 |
| Exact-preimage conflict adjudication and MCP descendant refusal | PLANNED | `koskadeux_mcp/durable_state_cutover.py` | union/conflict/preimage/crash-resume, adapter/CLI authority, and launcher PID/exec tests | 2026-08-25 |
| Receipt-bound macOS cutover and rollback | PLANNED | `koskadeux_mcp/durable_state_macos.py` | simulated launchd/crash/cutover/rollback tests | 2026-08-19 |
| Finite 16-point soak and same-process acceptance | PLANNED | `koskadeux_mcp/durable_state_cutover.py` | injected private clock/scheduler tests; no 15-minute unit sleep | 2026-08-24 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Shared resolvers | `koskadeux_mcp/runtime_state_paths.py`, `scripts/runtime_state_paths.sh` | five fixed durable children | MCP, probe, reloader, publishers | Side-effect free; one root; legacy variables inert. |
| Admin restart history | `admin.py` | durable `restart_count.json` | drain/restart and `/admin/status` | Strict schema, atomic write, sanitized fail-closed errors. |
| Transaction controller | `scripts/durable_runtime_state.py` | `cutovers/s1456` migration, adjudication, and transaction receipts | independent Gate 4 process | Inventory/status read-only; mutations reviewed-live gated. |
| macOS adapter | `koskadeux_mcp/durable_state_macos.py` | staged and installed definitions plus sanitized evidence | Git, launchd, local health | Candidate implementation; no live action in this build. |
| Soak and acceptance | `koskadeux_mcp/durable_state_cutover.py`, `scripts/durable_runtime_state.py accept` | `s1456.soak.v1` result and terminal receipt | production adapter plus private injected test seam | Sixteen finite checkpoints run in the accepting process; live time only after authorization. |

### §C.1 Five-record disposition

Only these five MCP-owned records move. Existing sources are retained; the
candidate creates no compatibility symlink for any of them.

| Record | Legacy source | Durable destination | Writers/readers and disposition |
|---|---|---|---|
| CC task records | `/var/tmp/koskadeux/cc_tasks` | `/Users/max/koskadeux-state/cc_tasks` | `claude_code_client.py`, `tools/async_dispatch.py`, poll/list readers, migration liveness, and the reloader guard share this directory. Copy the exact relative-file set; new directory mode is `0700`; contained file modes are preserved. |
| Deprecated-alias counters | `/var/tmp/koskadeux/session_instance_alias_counters.json` | `/Users/max/koskadeux-state/session_instance_alias_counters.json` | `tools/session.py` reads/writes only the resolved durable file. Normal scratch lifecycle is not alias evidence. |
| Admin restart history | `/var/tmp/koskadeux/restart_count.json` | `/Users/max/koskadeux-state/restart_count.json` | `admin.py` drain/restart writer and `/admin/status` reader use the same resolver and strict schema. |
| Deployment marker | `/var/tmp/koskadeux/deployed_sha` | `/Users/max/koskadeux-state/deployed_sha` | reloader plus both ground-truth publishers share the fixed durable marker. |
| Same-SHA secret-refresh request | `/var/tmp/koskadeux/mcp_secret_refresh_request` | `/Users/max/koskadeux-state/mcp_secret_refresh_request` | probe writes and reloader reads/removes the same SHA-bound durable request. Probe retry/backoff state remains separate and ephemeral. |

Already-durable `registry.db`, `gateway_storage.json`, boot-gate state derived
from the registry directory, Task Spooler sockets/jobs/reports/transcripts, and
`bridge_outcomes.db` do not move. Retired Council/KD stores, stale queue files,
and legacy artifact directories are preserved but neither migrated nor revived.

### §C.2 Explicit ephemeral and out-of-scope paths

| Path or family | Disposition |
|---|---|
| `deploy_hold.json` | Ephemeral hour-bounded manual latch in the unloaded legacy supervisor lane. Reboot expiry is intentional. Any lane reactivation first requires a new durability review. |
| `recovery_S*.json`, `recovery_latest.json` | Ephemeral per-session recovery buffers. Git, registry, and backend state remain authority; buffer loss cannot rewrite them. |
| `mcp_probe_restart_state.json` | Active but rebuildable retry/backoff cache controlled only by `KOSKADEUX_PROBE_STATE_DIR`. It is not the secret-refresh request. |
| `session_close_pending.json` and instance siblings | Ephemeral retry journals re-derived from pushed Git and backend close events. |
| `break_glass`, `break_glass_audit.jsonl` | Intentionally temporary TTL-bounded security control and local reconciliation buffer; persisting the sentinel would weaken safety. |
| `control/codex_queue.sqlite3` and sidecars | Retired-in-fact residue after removal of its consumer. Preserve; do not migrate or reactivate. |
| `council_hall.db`, old `verdicts/`, `agent_usage.csv`, `council_artifacts` | Retired current-MCP paths or legacy residue. Current Council transport uses `/Users/max/council`; preserve residue, do not migrate it. |
| KD stores, scheduler/dispatcher state, `execution_plans`, legacy specs/control files | Dormant legacy lane under current configuration. Do not migrate or start a writer without a new ground-truth review. |
| reload/session/repository locks, PID files, sockets, logs, crash evidence, temporary worktrees and packages | Ephemeral coordination or evidence. The reload lock stays `/var/tmp/koskadeux/reload_when_idle.lock.d`. |
| independent-service cursors such as `fireflies_last_sync.json` | Outside the MCP service boundary; the owning service must decide durability separately. |

### §C.3 One-root resolver contract

The only root variable for the five records is:

`KOSKADEUX_DURABLE_STATE_DIR=/Users/max/koskadeux-state`

Python exposes side-effect-free `pathlib.Path` resolvers
`durable_state_root()`, `cc_tasks_dir()`,
`instance_alias_counters_file()`, `restart_count_file()`,
`deployed_sha_file()`, and `secret_refresh_request_file()`. An unset variable
uses the default; an explicitly empty value is refused. Fixed child names are
appended without resolving symlinks or creating anything.

Shell consumers source `scripts/runtime_state_paths.sh`, which exports only
`KD_CC_TASKS_DIR`, `KD_DEPLOYED_SHA_FILE`,
`KD_SECRET_REFRESH_REQUEST_FILE`, and independent
`KD_RELOAD_LOCK_DIR`. Alias and restart history are Python-only. The legacy
variables `KOSKADEUX_STATE_DIR`, `KOSKADEUX_CC_TASKS_DIR`, and
`KOSKADEUX_PROBE_STATE_DIR` never redirect any of the five records;
`KOSKADEUX_PROBE_STATE_DIR` still controls only probe retry state. A reload-lock
override is accepted only in explicit isolated test mode and only beneath the
declared test directory.

The canonical MCP, probe, and reloader plists all pin the same durable root.
The probe prepends the repository root derived from its own `__file__` before
importing the resolver, so its launchd execution from `/` with no `PYTHONPATH`
does not depend on cwd or a repository install.

### §C.4 Restart-history write and failure semantics

The only valid record is a JSON object with exactly non-negative integer
`count` and a list of string `timestamps`. An absent file reads as count zero
and an empty timestamp list. A present malformed, wrong-shaped, symlinked,
non-regular, or unreadable record raises sanitized `RestartHistoryError` with
stable code `restart_history_unreadable`; no content is logged and zero is
never manufactured.

Increment retains the newest 50 timestamps and writes a sibling mode-`0600`
temporary file, flushes and fsyncs it, atomically replaces the destination,
then fsyncs the parent. Before-replace failure leaves the previous file
unchanged. Parent-fsync failure after replace makes persistence indeterminate,
but disk may contain only the complete old or complete new valid record. The
process then poisons restart history: further increments are refused,
`/admin/status` returns 503 with the stable code, drain/restart restores state
to `RUNNING`, suppresses `sys.exit(0)`, and logs only that code. On the next
process start, whichever complete record survived is strictly revalidated.
The count records a restart attempt before exit, not proof of relaunch.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Independent Gate 4 controller | inventory/status; reviewed adjudication/migration/cutover/resume/rollback/accept | `scripts/durable_runtime_state.py` | separate exact-artifact live authority | PLANNED |
| MCP handler | CC records, alias counters, restart history | shared Python resolver | process service identity | PLANNED |
| Probe | retry cache plus same-SHA refresh writer | `scripts/mcp_probe.py` | launchd service identity | PLANNED |
| Reloader | CC liveness, marker and request reader/remover | `scripts/reload_when_idle.sh` | launchd service identity | PLANNED |
| Ground-truth publishers | deployment-marker reads | shared Python/shell resolver | local operator process | PLANNED |

## §E. Operate

```yaml operate
[]
```

The operate form is deliberately empty while this page is DRAFT. The exact
candidate command surface below documents code for review; it does not grant
an executable operation.

### §E.1 Exact command contracts

Entry point: `python3 scripts/durable_runtime_state.py`. Omitting a subcommand
selects `inventory`, so `--candidate-sha <B>` alone is read-only inventory.

| Command | Exact arguments | Contract |
|---|---|---|
| `inventory` | `inventory --candidate-sha <B>` | Read-only sanitized source/destination inventory after proving B exists in the control repository. No directories or records are created. |
| `status` | `status` | Read-only sanitized ACTIVE/nonterminal/terminal/orphan transaction status. An absent transaction root returns empty lists. |
| `adjudicate` | `adjudicate --candidate-sha <B> --expected-source-cc-manifest <hash> --expected-destination-cc-manifest <hash> --expected-source-deployed-sha <sha> --expected-destination-deployed-sha <sha> <reviewed-live-inputs>` | Reconciles only the reviewed disjoint CC-task and stale legacy-marker conflicts. The durable marker must already equal B. |
| `migrate` | `migrate --candidate-sha <B> <reviewed-live-inputs>` | Performs the reviewed preflight and then copy-first migration only. It is not an ungated execute switch. |
| `cutover` | `cutover --candidate-sha <B> --prior-sha <A> <reviewed-live-inputs>` | Starts or advances the receipt-bound A-to-B forward transaction. |
| `resume` | `resume <reviewed-live-inputs>` | Selects only the uniquely verified ACTIVE transaction, re-proves evidence, and continues forward or rollback from the last proven boundary. |
| active rollback | `rollback --reason <safe-code> <reviewed-live-inputs>` | Rolls back only the verified ACTIVE nonterminal forward transaction. Reason permits letters, digits, underscore, dot and hyphen. |
| accepted rollback | `rollback --reason <safe-code> --from-accepted <forward-id> <reviewed-live-inputs>` | With no ACTIVE transaction, creates a new rollback transaction linked to one immutable terminal accepted forward receipt. |
| `accept` | `accept --transaction-id <forward-id> --cc-smoke-task-id <task-id> <reviewed-live-inputs>` | Runs the production 16-point/900-second checker itself and transitions only that exact ACTIVE transaction. It accepts no caller-supplied soak mapping or clock/checker injection. |

`<reviewed-live-inputs>` means all five flags below on every mutating command:

```text
--reviewed-live
--reviewed-code-sha <full-B-sha>
--reviewed-runbooks-sha <full-reviewed-runbooks-sha>
--authorization-evidence-id <non-secret-id>
--peer-clearance-evidence-id <non-secret-id>
```

Missing inputs refuse with `reviewed_live_inputs_required`; absent
`--reviewed-live` refuses with `reviewed_live_required`; a candidate mismatch
refuses with `reviewed_code_sha_mismatch`. These flags are an executable live
boundary, not proof that authorization exists. The production adapter also
requires an independent control checkout, exact clean code/runbooks main SHAs,
candidate/prior presence, healthy gateway/MCP and required handlers, exact
deployed marker, peer clearance, zero live/indeterminate CC tasks, expected
plist/old-root preimage, and normally no refresh request. Uncertainty refuses.
The installed plist bytes observed by this preflight are the sole rollback
definitions for A: their SHA-256 values are journaled before any move, the exact
bytes are retained in the transaction directory, and rollback never reconstructs
A from a Git checkout.

### §E.2 Inventory, migration, and receipt schema

Migration verifies a pre-existing user-owned, non-symlink durable root that is
not group/world-writable and never chmods it. It requires zero live and zero
indeterminate CC tasks; stale/dead records are accounted for but not rewritten.
It refuses symlinks, wrong owners/types/modes, differing destinations, and any
source change during the copy. Each new destination is copied to a sibling
temporary path and published without overwrite, then exact tree, hashes, modes,
owner and relative-file set are rechecked. Absent source plus absent destination
is `not_present`; identical destinations are idempotent. Sources are never
deleted or rewritten.

The immutable mode-`0600` migration receipt lives below
`cutovers/s1456/migration-receipts/` and uses schema
`s1456.migration.v1`. It records kind/status, full candidate SHA, source and
durable roots, source-snapshot digest, sanitized CC liveness, and one row per
record containing disposition plus source/destination snapshots. Snapshots
contain metadata, counts, relative paths, modes, owners, and hashes—not record
contents.

Transaction receipts are mode `0600` at
`cutovers/s1456/<transaction-id>/receipt.json`, schema
`s1456.transaction.v1`. Base fields are kind (`forward` or `rollback`), full
transaction id, full A/B SHAs, and phase. The preflight checkpoint adds only
the reviewed code/runbooks SHAs, authorization and peer-clearance evidence IDs,
preflight digest, MCP generation, old-root hashes, and the three installed-A
definition hashes. Later checkpoints add hash-pinned definition/record evidence,
process generations, actor evidence, and accepted snapshot hashes. Per-label
moves/installs are checkpointed
individually. Updates are validated monotonic transitions written through a
mode-`0600` sibling temp, file fsync, atomic replace, and directory fsync.
`s1456.rollback-reconciliation.v1` and `s1456.soak.v1` likewise contain
sanitized hashes/times/results, never secrets, record contents, command output,
or review contents.

The one reviewed Gate 4 conflict path does not alter migration's
`destination_differs` refusal. `adjudicate` requires exact initial manifests
for both CC directories and exact legacy/durable deployment SHAs. The durable
SHA must be B. It publishes a mode-`0600` `s1456.adjudication.v1` prepared
receipt containing the reviewed code/runbooks SHAs and non-secret authority
IDs, then copy-only unions disjoint CC entries into both roots without
overwrite. A same-path metadata/content conflict, unexpected entry, missing
union member, unsafe root, or live/indeterminate task refuses. It archives the
stale legacy marker bytes mode `0600`, atomically replaces only the legacy
marker with the durable B bytes and mode, and never overwrites the durable
marker. Prepared receipts resume only from receipt-pinned subsets at the three
tested crash boundaries. Completion requires exact CC equivalence and matching
B markers before unchanged migration may issue its normal receipt.

### §E.3 Deterministic identity, ACTIVE selection, and orphans

Transaction root and each transaction directory are user-owned mode `0700`.
A forward id is `s1456-<prior12>-to-<candidate12>-aNNNN`, where `NNNN` is one
greater than the greatest well-formed retained terminal receipt for that A/B
pair, starting `0001`. A rollback from accepted is
`s1456-rollback-<forward-id>-aNNNN`, numbered against retained rollbacks linked
to that forward receipt. Malformed names do not participate.

ACTIVE selection writes a unique mode-`0600`
`.ACTIVE.<transaction-id>.candidate` with `O_CREAT|O_EXCL`, fsyncs it, and uses
a same-directory hard link as the no-overwrite compare-and-set for `ACTIVE`.
After parent fsync it removes the candidate link and fsyncs again. Only the
winner may create the mode-`0700` transaction directory and atomic
`prepared`/`rollback_prepared` receipt; no operational side effect precedes the
receipt.

Exactly one nonterminal receipt may exist and it must match `ACTIVE`. Missing
ACTIVE with a nonterminal, multiple nonterminals, changed/malformed identity,
an ACTIVE pointer to missing/terminal/unexpected state, or an unreferenced
nonterminal-looking directory fails closed. The sole recovery exception before
side effects is a valid ACTIVE with a missing transaction directory or exact
empty mode-`0700` directory: resume may publish only its initial receipt. A
matching leftover candidate link is removed only after byte equality; one
candidate without ACTIVE may retry the same link CAS only with no other
nonterminal. Multiple, mismatched, malformed, or cross-filesystem candidates
remain and fail closed.

Terminal receipts and unrecognized directories are retained as sanitized
orphans and never auto-selected or deleted. Terminal `accepted` or
`rolled_back` hard-links ACTIVE without overwrite to
`ACTIVE.<transaction-id>.terminal`, fsyncs, removes ACTIVE, and fsyncs again;
resume proves byte equality before completing an interrupted archive.

### §E.4 Launchd fence, phases, and safe prefixes

Forward phases are:

`prepared` -> `definitions_staged` -> `agents_fenced` -> `records_copied` ->
`candidate_published` -> `candidate_started` -> `candidate_verified` ->
`marker_sealed` -> `persistent_definitions_installed` -> `actors_enabled` ->
terminal `accepted` (or `rolled_back`).

Before fencing an actor, the controller moves and hash-verifies all installed
MCP/probe/reloader plists from `~/Library/LaunchAgents` into the transaction
directory, one receipt checkpoint per label. It then bootouts in order reloader,
probe, MCP and proves all absent. Before `marker_sealed`, no candidate plist is
in the persistent auto-load domain and only MCP may be bootstrapped from the
staged definition. Candidate exact SHA, new process generation, health and
handlers are proved before marker B is atomically sealed.

If launchd completed the staged MCP bootstrap but the process crashed before
`candidate_started` (or rollback `prior_started`) was checkpointed, resume
accepts only the exact staged path and definition with the expected SHA,
handlers, health, PID and generation. It returns that generation without a
second bootstrap; any other loaded state is refused.

After marker seal, persistent installs are locked to MCP, probe, reloader:

| Persistent definition prefix | Safe reboot/login behavior |
|---|---|
| none (all pre-seal phases) | Starts none of the three actors. |
| MCP only | Starts only reviewed MCP B; probe and reloader remain absent. |
| MCP + probe | Probe may write only a B-bound request; no reloader exists to consume it. |
| MCP + probe + reloader | All three exact definitions share the durable root and reviewed B. |

Resume derives permitted RunAtLoad actor state from the exact verified prefix,
rechecks installed hashes, and completes only the missing suffix. An exact
probe or reloader may already have run only when its definition is in that
prefix; a B-bound request remains the receipt-bound rollback trigger. Probe
is bootstrapped only after all definitions are installed. Immediately before
reloader bootstrap: no request; zero live/indeterminate CC task; shared-root
parity; unchanged MCP generation; and B agreement across marker, main and
publisher. Installing the reloader arms a mode-`0600`, receipt-bound first-tick
guard before launchd can load it. Reloader starts last. Its first completed
controller or RunAtLoad evaluation occurs before any fetch or fast-forward and
must be `already_deployed_no_refresh`, with zero fetch, fast-forward, marker
write, request removal, or kickstart calls and no second MCP generation. The
controller rechecks local and remote `origin/main`, marker, request absence, and
generation before removing that guard. The publication comparison is
direction-independent for B and A. An uncontrolled result preserves the guard;
rollback immediately re-fences its reloader and remains nonterminal. After
fencing the reloader, rollback may atomically replace only that
exact source-transaction B guard with the exact A guard; a foreign guard is
refused. Rollback remains nonterminal and the reloader remains fenced until
both the local tracking ref and live remote `origin/main` publish A; only then
may the A guard and ordinary watcher be armed. This prevents a restored A tree
from being fast-forwarded back to B. Drift or a B request in the
post-seal/pre-first-tick window triggers receipt-bound rollback; the request is
quarantined rather than consumed as a normal tick.

Launchd proof reads only one-tab, top-level service fields and ignores nested
coalition `state = active` rows. Both `state = running` and the normal
`state = not running` service form are valid only when all remaining top-level
fields are well formed. Missing, malformed, or contradictory first-tick
evidence enters the same receipt-bound rollback path.

Crash injection covers immediately before and after every file move, receipt
replace, marker replace, persistent plist install, and launchd action. Resume
uses a phase-aware recovery preflight: it re-proves the exact reviewed authority,
retained installed-A bytes, the marker values allowed for that forward or
rollback phase, old-root baseline until reconciliation, clean repositories, and
the safe persistent-definition prefix. It does not require actors that the
recorded phase has intentionally fenced. The phase string alone is never
trusted. Changed/unexpected labels or definitions, skipped phases, old-root
writes, and evidence ambiguity fail closed. Logout/reboot simulation covers
every pre-seal phase and each post-seal prefix and may never start an old-path
writer.

### §E.5 Forward acceptance and 16-point soak

Before publication, prove exact current code/runbooks main and reviewed SHAs,
deployed A, clean trees, gateway/MCP/handlers, peer clearance, CC quiescence,
no request, and marker/plist/old-root preimage. Then: sanitized inventory;
stage/fence; migrate and verify; re-prove the live repository clean immediately
before any reset; publish B; bootstrap staged MCP only; prove
generation/SHA/health/handlers; seal marker B; install all three persistent
definitions; start probe then reloader with the no-op first tick.

Acceptance takes only the identifier of an already-completed CC read-only smoke;
it does not dispatch CC. At every check it proves and polls the task's successful
metadata/result/done regular files directly under the durable `cc_tasks` root;
reloader liveness uses the
same root; marker agrees with both publishers; probe/reloader request paths
agree without creating a live test request; live alias and restart consumers
resolve the durable paths; and old-root hashes remain unchanged.

The finite soak begins immediately after `actors_enabled`. It has exactly 16
checks: check 1 at monotonic `t=0`, then checks 2-16 at
`t=60,120,180,240,300,360,420,480,540,600,660,720,780,840,900` seconds.
Each receipt row records scheduled monotonic deadline, actual start/completion
monotonic time, wall time, and sanitized results. Every check requires:

- MCP, probe and reloader healthy;
- unchanged MCP process generation;
- marker SHA, ground-truth board SHA and publisher SHA all equal B;
- successful CC polling; and
- unchanged hashes for all five old-root records.

A check completed at or after the next 60-second deadline is missed; catch-up
is forbidden. Early, failed, fewer-than-16, monotonic regression, old-root
change, check 16 before `t=900`, or total elapsed below 900 seconds is an
immediate rollback trigger. Terminal acceptance requires the exact
`s1456.soak.v1` top-level and per-check field sets, exact candidate/generation,
finite and internally consistent monotonic aggregates, sequential checks,
on-time boundaries, all required boolean/SHA results, and exact unchanged
old-root hashes; extra, missing, malformed, or caller-simplified rows are
rejected. Only the reviewed public API/CLI may run the production checker and
real monotonic scheduler and transition the exact ACTIVE transaction in the same
process. The strict receipt validator is defense-in-depth after that harness
completes. Unit tests inject time only through a private model seam and never
sleep 15 minutes; only a separately authorized live action may run real time.
Every mutating CLI command, public Python wrapper, and exported transaction-
root, ACTIVE-publication, or receipt-transition primitive repeats the
independent-controller check before adapter construction, directory/pointer/
receipt mutation, launchd work, soak, or acceptance. An MCP-owned child is
never accepted as Gate 4 authority. Immediately before its final `exec`, the
production launcher exports `KOSKADEUX_MCP_SERVER_PID=$$`; the server retains
that PID and every descendant inherits it. Any positive inherited server PID
refuses mutation, so grandchildren cannot evade the boundary through an
intermediate shell. Independent operator shells do not inherit the marker.

### §E.6 Active and accepted rollback reconciliation

Plain rollback continues the ACTIVE forward receipt with a monotonic rollback
checkpoint. Post-acceptance rollback requires no ACTIVE, an immutable accepted
forward receipt plus matching terminal pointer archive, marker B, and no later
consumer. It creates a new linked rollback receipt pinning the source receipt
hash, A/B SHAs, accepted snapshot hashes, reason, source generation, and
`rollback_of`; the accepted forward receipt remains immutable.

An operator-requested active rollback before forward `definitions_staged` is
refused with stable `rollback_before_definitions_staged` before preflight,
checkpoint, or mutation; resume remains the safe path while A is still installed.

Rollback phases are:

`rollback_prepared` -> `definitions_staged` -> `agents_fenced` ->
`records_reconciled` -> `prior_published` -> `prior_started` ->
`prior_verified` -> `marker_sealed` ->
`persistent_definitions_installed` -> `actors_enabled` -> terminal
`rolled_back`.

The same plist fence removes persistent definitions before code or record
changes. Reconciliation first backs up the five old roots. Durable CC files win
only after complete exact-set/hash verification. Current durable alias and
restart JSON replace the frozen old snapshot, or create an old record when its
migration receipt was `not_present`; accepted snapshot hashes are drift/linkage
baselines and never overwrite newer durable state. A B-bound request is moved
to a mode-`0600` quarantine in the rollback receipt area; active durable and
old request paths remain absent. Only its hash/disposition is recorded.

After reconciled old-root proof, publish and bootstrap staged prior MCP A,
prove new generation/SHA/health/handlers, then seal marker A. Reinstall exact A
definitions only after that proof. Bootstrap probe then reloader only after
both local and live remote `origin/main` publish A; until then the rollback is
nonterminal and the reloader is fenced. A quarantined B request records that
prior refresh is still required. After the controlled A no-op tick, the
controller uses nested `actors_enabled` receipt checkpoints to fence the
reloader, write one fresh A request, restart the reloader, wait for normal
consumption, and prove the refreshed A generation, health, handlers, marker,
and local/live remote publication. Crashes resume from the exact fence/write/
start/consume checkpoint; no request is manufactured when reconciliation found
no quarantined intent. Neither `not_required` nor a `completed` nested
checkpoint is terminal authority: every terminal transition re-proves request
absence, the exact healthy A reloader, the disposition's expected generation,
marker, live HEAD, and current local/live remote A publication. Any mismatch
re-fences the reloader and leaves the transaction nonterminal. After publication
returns to A, the no-request path may re-enable only through the same guarded
no-op evaluation and repeat the terminal proof. A completed refreshed-request
path remains stopped for a new reviewed recovery design because its generation-
bound write-once evidence cannot be reused. Never reuse the B request. Any conflicting old-root write,
missing/changed source receipt, marker drift, duplicate consumer, ambiguous
history, or post-acceptance record conflict fails closed and preserves all
backups and receipts.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A consumer still resolves one of the five records under `/var/tmp` or follows a legacy override. | Mixed candidate definitions/code or an unconverted consumer. | Compare all Python/shell resolver outputs and exact plist hashes against reviewed B; do not write either root. | G-01 | CONFIRMED |
| F-02 | Inventory/migration reports differing destination, or adjudication reports preimage/entry/archive/authority drift, symlink, wrong owner/mode, or live/indeterminate task. | Preimage drift, a same-path conflict, or unsafe filesystem/liveness state. | Preserve the refusal and review sanitized inventory, liveness counts, types, modes and hashes; never compare contents in logs. | G-02 | CONFIRMED |
| F-03 | `/admin/status` returns 503 `restart_history_unreadable` or drain returns to RUNNING without exit. | Present restart history is invalid/unreadable or a write became persistence-indeterminate. | Stop increments; inspect only type/owner/mode and validate the schema without printing content. Treat post-replace fsync failure as old-or-new indeterminate. | G-03 | CONFIRMED |
| F-04 | `status` reports multiple nonterminals, pointer mismatch, candidate residue, or sanitized orphan. | Interrupted/racing ACTIVE publication, manual transaction changes, or unexpected directory contents. | Use read-only `status`; compare pointer/receipt identities and hashes. Do not rename, delete, or auto-select an orphan. | G-04 | CONFIRMED |
| F-05 | Candidate health/handler/generation, first no-op tick, publisher agreement, or a soak point fails. | Publication/config/process drift or a B request/old-root write appeared. | Record the failed sanitized proof and invoke only receipt-bound rollback under separate reviewed-live authority. | G-05 | CONFIRMED |
| F-06 | Rollback refuses source receipt, marker, current durable record, or old-root reconciliation. | Accepted receipt drift, later consumer, conflicting writes, or ambiguous history. | Preserve both sides, backups and receipts; compare exact hashes and transaction linkage. Never restore a frozen snapshot over newer durable state. | G-06 | CONFIRMED |
| F-07 | Rollback stays nonterminal with the reloader fenced after a first-tick drift row or after terminal publication drift. | Local tracking moved during the guarded tick, or local/live remote publication moved before terminal proof. Immutable generation-bound evidence cannot authorize a refreshed-request retry; a no-request retry is allowed only through the same guarded no-op after publication returns to A. | Preserve the guard, evidence, request disposition, receipt, and both Git refs. Confirm the reloader is absent and do not delete or rewrite transaction evidence. | G-07 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Shared resolvers
  root_cause: mixed candidate definitions or an unconverted consumer
  repair_entry_point: exact code candidate and isolated path-contract tests
  change_pattern: stop before live action; rebuild and review one exact SHA with three matching definitions
  rollback_procedure: no live change occurred; discard the candidate change
  integrity_check: all five Python paths and the three shell-consumed paths agree without production-root writes
- id: G-02
  symptom_ref: F-02
  component_ref: Transaction controller
  root_cause: unsafe ownership, mode, symlink, liveness, or destination preimage
  repair_entry_point: a separately reviewed filesystem or liveness plan
  change_pattern: preserve the refusal and resolve the exact unsafe precondition before rerunning read-only inventory; use adjudication only for the reviewed receipt-bound disjoint-task and stale-marker case
  rollback_procedure: sources and the refused destination remain unchanged
  integrity_check: sanitized inventory shows the reviewed owner, mode, liveness counts, and exact hashes
- id: G-03
  symptom_ref: F-03
  component_ref: Admin restart history
  root_cause: invalid or unreadable history, or persistence-indeterminate atomic write
  repair_entry_point: independent reviewed restart-history recovery
  change_pattern: keep the service RUNNING and select only a complete schema-valid old or new atomic record
  rollback_procedure: preserve both complete candidates and never manufacture a zero record
  integrity_check: a fresh process strictly validates history before admin status returns 200
- id: G-04
  symptom_ref: F-04
  component_ref: Transaction controller
  root_cause: interrupted or racing publication, unexpected contents, or manual transaction drift
  repair_entry_point: reviewed resume only for the deterministic initial pointer recovery states
  change_pattern: never manually delete or select candidate links, terminal archives, or orphans
  rollback_procedure: stop and preserve the entire transaction root for review
  integrity_check: status shows exactly one matching ACTIVE and nonterminal receipt, or no ACTIVE after terminal archive
- id: G-05
  symptom_ref: F-05
  component_ref: macOS adapter
  root_cause: health, generation, definition, request, marker, publisher, soak, or old-root drift
  repair_entry_point: reviewed active or accepted rollback command
  change_pattern: use the same exact artifacts and fresh authority checkpoint; never apply an ad hoc rollback
  rollback_procedure: restore prior A only through the staged-definition fence and lossless reconciliation
  integrity_check: prior health precedes marker A and the terminal receipt is rolled_back
- id: G-06
  symptom_ref: F-06
  component_ref: Transaction controller
  root_cause: changed source receipt, later consumer, conflicting writes, or ambiguous record history
  repair_entry_point: new reviewed recovery design
  change_pattern: preserve both copies, backups, receipts, and exact hashes; do not bypass the verifier
  rollback_procedure: leave all conflicting evidence intact
  integrity_check: no conflicting bytes were discarded and neither root was modified without authority
- id: G-07
  symptom_ref: F-07
  component_ref: macOS adapter
  root_cause: immutable drift evidence or publication drift after a completed nested checkpoint
  repair_entry_point: new exact-artifact reviewed recovery design
  change_pattern: preserve the write-once evidence and nonterminal receipt; a no-request retry may use the same byte-identical guarded no-op after A publication returns, while a refreshed-request retry requires a new reviewed design
  rollback_procedure: keep the reloader fenced and all transaction evidence intact
  integrity_check: no terminal rolled_back receipt exists and publication cannot restart an unreviewed SHA
```

The machine repair form records fail-closed candidate behavior for review only.
While this discovery page lacks operating authority, neither that form nor the
table below authorizes a live repair.

| ID | Symptom ref | Repair | Rollback / integrity check |
|---|---|---|---|
| G-01 | F-01 | Stop before live action. Rebuild/review one exact code SHA and three matching canonical plists; prove all five resolvers and shell parity in isolated tests. | No live change to undo; require exact-SHA tests and no writes to production roots. |
| G-02 | F-02 | Do not chmod the shared root, overwrite a destination, delete a source, or guess authority. Resolve ownership/liveness/preimage through a separately reviewed plan, then rerun inventory first. | Original sources and refusal remain intact; recheck sanitized exact hashes/modes/counts. |
| G-03 | F-03 | Fail closed, keep service RUNNING, and obtain independent reviewed recovery authority. Choose only a complete schema-valid record after determining which atomic version survived; never manufacture zero. | Revalidate strict schema and mode; `/admin/status` must return 200 only in a fresh process with readable complete history. |
| G-04 | F-04 | Use `resume` only for the explicitly allowed deterministic initial-pointer/empty-directory state. Otherwise stop for operator review; do not manually clean ACTIVE, candidate links, terminal archives, or orphans. | Read-only status must show exactly one ACTIVE/nonterminal pair or no ACTIVE after terminal archival. |
| G-05 | F-05 | Under the same exact reviewed artifacts and fresh authority checkpoint, run plain receipt-bound rollback for the ACTIVE transaction, or accepted rollback for a named immutable accepted receipt. | Prior A health/handlers precede marker A; reconciliation retains post-cutover deltas; terminal state is `rolled_back`. |
| G-06 | F-06 | Stop and preserve both copies. Resolve the unexpected conflict through a new reviewed recovery design; never bypass the reconciliation verifier. | All old/durable records, receipt area and backups remain available and no conflicting bytes were discarded. |
| G-07 | F-07 | Stop with the reloader fenced and preserve all evidence. After both refs return to A, `not_required` may resume only through a byte-identical guarded no-op and fresh terminal proof. A completed refreshed-request checkpoint is not reused; it requires a new exact-artifact reviewed design. Never manually remove the evidence row. | No terminal receipt is written under drift. The no-request path terminalizes only after guarded A recovery; refreshed-request evidence remains intact for review. |

## §H. Evolve

### §H.1 Invariants

- Exactly five records and one root; no broad `/var/tmp/koskadeux` relocation.
- No source deletion, compatibility symlink, schema change, root execution,
  cross-service state change, or secret/content logging.
- One uniquely verified ACTIVE transaction; atomic monotonic receipts and
  no-overwrite pointer/terminal publication.
- Exact candidate/prior code plus exact runbooks SHA and evidence IDs are
  checkpointed before a live mutation, including conflict adjudication.
- Before marker seal the persistent domain contains no candidate definition;
  after seal only a reviewed safe prefix is allowed.
- Rollback preserves verified post-cutover task/counter/history deltas.

### §H.2 BREAKING predicates

Adding a sixth record, accepting a legacy override, creating an old-path
writer/symlink, weakening root/owner/mode/liveness checks, overwriting ACTIVE,
skipping a phase/evidence reproof, starting probe/reloader before marker seal,
or restoring a frozen snapshot over newer durable state is breaking and needs a
new design and unanimous exact-artifact review.

### §H.3 REVIEW predicates

Changing a fixed child name, plist order/label/program, receipt field/schema,
transaction identity, liveness classifier, restart-history schema, first-tick
preconditions, soak timing/checks, rollback reconciliation, or authority input
requires code, tests, this DRAFT, and exact-artifact review to move together.

### §H.4 SAFE predicates

Editorial clarification is safe only when it changes no command, path,
identity, phase, failure, evidence, authority, timing, or rollback meaning and
the generated catalog/manifest remain exact.

### §H.5 Boundary definitions

#### module

The module boundary is the shared resolver, cutover controller, macOS adapter,
soak harness, five named consumers, and three canonical plist definitions at
the exact code candidate.

#### public contract

The public contract is the CLI surface in §E.1 plus sanitized JSON success/error
output. A `DurableStateError` is emitted as `{"ok": false, "error": <stable-code>}`
on stderr with exit status 2.

#### runtime dependency

Runtime dependencies are an independent control checkout, exact code/runbooks
Git objects and clean main checkouts, the durable and legacy roots, launchd,
the three canonical/installed definitions, local health endpoints, CC liveness,
peer clearance, and exact non-secret evidence identifiers.

#### config default

`KOSKADEUX_DURABLE_STATE_DIR` defaults to `/Users/max/koskadeux-state` and may
not be empty. No per-record production override exists.

### §H.6 Adjudication

Code and binding specs win over this discovery page. The only approved
pre-migration exception is the exact-preimage, receipt-bound union/archive/
legacy-marker normalization described in §E.2. It cannot select a nearby SHA,
overwrite the durable marker, merge a same-path conflict, add another record,
or weaken normal migration. Any mismatch stops before mutation; any drift after
a prepared receipt preserves all originals and receipt evidence for reviewed
resume or stop.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set: []
```

The documentation candidate passes only when the new page is discovery-only in
schema-v3 `CATALOG.json`, appears in `TOPIC-ROUTER.md`, has one pending
grandfathered `CORPUS-MANIFEST.yaml` record, leaves the generated README ACTIVE
inventory current and unchanged, leaves
all 26 ACTIVE entries field-for-field unchanged, has no generated drift, passes
focused lint/catalog/manifest tests plus the full runbooks suite, and has a
diff limited to this page, the minimum five operator path contracts, generated
artifacts, manifest, and the README schema/population correction.

Gate 4 remediation candidate acceptance additionally requires the full
`tests/runtime_state` suite, focused Ruff and diff checks, exact CLI/adapter
authority binding, unchanged default migration refusal, copy-only lossless
union, stale-marker archive, durable-marker no-overwrite, all three
crash-resume boundaries, and inherited descendant refusal. Live acceptance is
still separate: exact-artifact review and authority checkpoint;
successful forward sequence and first reloader no-op; all path/consumer/marker
probes; exactly 16 on-time soak checks over at least 900 monotonic seconds; no
old-root change; and terminal `accepted`. None was performed or claimed by this
documentation build.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1605
last_refresh_commit: 5ab1da824671739b935aed8bd868289eb6997298
last_refresh_date: 2026-08-25T08:55:18Z
owner_agent: vulcan
refresh_triggers:
  - any reviewed code or binding-spec change to the five-record path contract
  - any CLI, receipt, transaction, plist, crash, soak, or rollback change
  - any newly discovered live consumer or old-root writer
scheduled_cadence: 1y
```

Lifecycle evidence for this candidate: exact code candidate SHA
`5ab1da824671739b935aed8bd868289eb6997298`; locked Gate 1 SHA
`fb1802cdca61946ea25fb28bc0dd965e29e3bcf4`; Gate 2 file from the exact code
worktree; runbooks base `8843542562daf6bc3b5d80f6911d4136279da458`;
and a no-live-touch build boundary. The final documentation head, generated
counts, ACTIVE equality, tests, drift, and push result belong in the external
candidate report because a document cannot truthfully self-pin its own commit.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
retrofit: false
trace_matrix_path: null
word_count_delta: null
```
