---
system_name: session-registry-recovery
purpose_sentence: Keep Koskadeux session-ID allocation monotonic and unblocked by documenting the durable high-water-mark registry, its test-isolation guard, the two-signal stale-session self-heal, and the recovery paths when session opens stall or numbers look wrong.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  The Koskadeux session registry on Titan-1: the SQLite store at /var/tmp/koskadeux/registry.db (tables sessions, session_seq, schema_migrations, close_transactions), the durable monotonic allocator and its Living State anchor config:session-seq, the KOSKADEUX_REGISTRY_DB override, pytest isolation from the live DB, the last_seen + peer-bus stale-session self-heal, the append-only schema migrations, and the operator recovery paths. This runbook is the source of truth for diagnosing and repairing session-open blocks and session-number anomalies. It is NOT the source of truth for the boot-payload contents (session-open-protocol.md) or session close (session-close-protocol.md). The retired primary/worker lock-slot model is out of scope (symmetric peers, CORE v9.2 S811).
linter_version: 1.0.0
---

# Session Registry Recovery

## §A. Header

The YAML frontmatter above defines the §A header. §J is authoritative for lifecycle refresh tracking; this header is the display summary for stateless readers.

> **Model note.** As of CORE v9.2 (S811) Koskadeux runs **symmetric peers** (vulcan, mars) with no primary/worker lock slots. The session registry is an **instance-keyed `sessions` table** (one row per instance, plus a non-human `scratch` row) carrying a **durable monotonic high-water mark** (`session_seq` + Living State anchor `config:session-seq`), shipped S867. The older `infra:active-session-lock` primary/worker slot model and the iCloud lock-pointer are retired; recovery procedures here target the current model.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Durable monotonic session-ID high-water mark | SHIPPED | `koskadeux-mcp tools/registry.py session_seq table + apply_session_seq_migration` | Verified live: schema_migrations v7, session_seq.next_value=875, integrity_check ok | 2026-06-16 |
| Anchor reserved before issuance (fail-closed on Living State) | SHIPPED | `koskadeux-mcp tools/registry.py Registry.register_allocated_session` | Verified by source read; reserve_anchor reserves config:session-seq before INSERT | 2026-06-16 |
| Living State durable anchor config:session-seq | SHIPPED | `koskadeux-mcp tools/session.py _session_seq_key` | Verified live: anchor re-seeds session_seq on registry rebuild | 2026-06-16 |
| KOSKADEUX_REGISTRY_DB path override | SHIPPED | `koskadeux-mcp tools/registry.py _resolve_db_path` | Read by registry, admin endpoints, and phantom-cleanup script | 2026-06-16 |
| pytest isolation from the live registry.db | SHIPPED | `koskadeux-mcp conftest.py module-level env + tools/registry.py open_registry guard` | conftest sets KOSKADEUX_REGISTRY_DB at collection time; guard raises on prod path under PYTEST_CURRENT_TEST | 2026-06-16 |
| Production-path hard guard | SHIPPED | `koskadeux-mcp tools/registry.py RegistryProductionPathError` | open_registry raises if PYTEST_CURRENT_TEST set and path is production | 2026-06-16 |
| Two-signal stale-session self-heal (last_seen TTL + peer-bus) | SHIPPED | `koskadeux-mcp tools/session.py _auto_close_stale_instance_if_safe` | Auto-closes a stale row on open only when last_seen past TTL AND no recent peer-bus signal; fail-open on peer-check error | 2026-06-16 |
| session_auto_closed_stale audit event | SHIPPED | `koskadeux-mcp tools/session.py _emit_session_auto_closed_stale` | Event type registered in tools/state.py; emitted on self-heal close | 2026-06-16 |
| Transactional append-only schema migrations | SHIPPED | `koskadeux-mcp scripts/migrate_session_registry.py + tools/registry.py apply_session_seq_migration` | BEGIN IMMEDIATE; idempotency keyed on live DDL, not the version row | 2026-06-16 |
| Phantom-session cleanup utility | SHIPPED | `koskadeux-mcp scripts/s852_phantom_session_cleanup.py` | Used S852 to clear inflated phantom rows and S901 to reap a single stale scratch OPERATIONAL row; RANGE deleter (number > --cutoff, minus --protect); preserves the counter floor by protecting live sessions (does NOT re-anchor, does NOT back up — take a manual backup first) | 2026-06-16 |
| Admin recovery endpoints (boot-gate bypass) | SHIPPED | `koskadeux-mcp tools/admin_endpoints.py` | Reachable on gateway 8767 when no session is open | 2026-06-16 |
| Legacy primary/worker lock slots + iCloud lock-pointer | DEPRECATED | `koskadeux-mcp tools/icloud_sync.py (legacy)` | Retired under symmetric peers (CORE v9.2 S811); not a recovery path | 2026-06-16 |

## §C. Architecture & Interactions

The session registry is a SQLite database on Titan-1 at `/var/tmp/koskadeux/registry.db`, opened through `registry.py open_registry`, whose path resolves from the `KOSKADEUX_REGISTRY_DB` environment variable (defaulting to the production path). The `sessions` table is instance-keyed: at most one row each for `vulcan`, `mars`, and the non-human `scratch` instance. Session numbers come from a durable monotonic high-water mark held in the `session_seq` single-row table and mirrored to the Living State anchor `config:session-seq` (Railway Postgres). The allocator `Registry.register_allocated_session` reserves the anchor to at least the candidate number BEFORE writing the registry row, and fails closed if Living State is unreachable, so a registry rebuild or restore re-seeds from the anchor and never rewinds. Stale rows self-heal on open via `_auto_close_stale_instance_if_safe`, which closes a row only when its `last_seen_at` is past the TTL AND the peer bus shows no recent signal from that instance (fail-open on a peer-check error to avoid killing a live session). Schema changes are append-only migrations applied transactionally and idempotently against the live table shape.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Session Registry | `tools/registry.py open_registry` | `registry.db (sessions, session_seq, schema_migrations, close_transactions)` | boot gate (session.py), peer bus, admin endpoints | Instance-keyed; resolves path from KOSKADEUX_REGISTRY_DB |
| Allocator | `tools/registry.py Registry.register_allocated_session` | `session_seq + config:session-seq (Living State)` | session.py _allocate_session_in_registry | Reserves anchor before issuing; BEGIN IMMEDIATE; scratch excluded from max |
| Durable HWM Anchor | `tools/session.py _session_seq_key` | `config:session-seq (Living State, Railway PG)` | Allocator, recovery re-seed | Re-seed source on registry rebuild; never decreases |
| Self-Heal | `tools/session.py _auto_close_stale_instance_if_safe` | `sessions.last_seen_at + peer_messages` | any_session_live (registry.py), peer bus | Two-signal; CAS-guarded close; emits session_auto_closed_stale |
| Migration Runner | `scripts/migrate_session_registry.py` | `schema_migrations` | registry.py apply_*_migration | Append-only; idempotency keyed on live DDL not version row |
| Boot Gate | `tools/session.py _handle_kd_session_plan` | in-memory gate state (wiped on restart) | kd_session_open, kd_session_plan | PLANNING then OPERATIONAL; re-run open+plan after restart |
| Admin Recovery | `tools/admin_endpoints.py` | `registry.db` | gateway 8767 | Bypasses the boot gate; reachable with no session open |

### Canonical identifiers

| Resource | Value |
|---|---|
| Registry DB path | `/var/tmp/koskadeux/registry.db` |
| Path override env | `KOSKADEUX_REGISTRY_DB` |
| Durable anchor key | `config:session-seq` (Living State) |
| Current schema version | `7` (`session_seq_durable_hwm`) |
| Stale TTL | `SESSION_LIVE_TTL_SECONDS` default `1800` |
| MCP restart | `launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp` |
| Backup dir | `/var/tmp/koskadeux/backups/` |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | inspect registry state, run migration status/apply, run phantom cleanup, restart MCP and verify | shell plus state_request | Titan-1 shell plus Living State | COMPLETE |
| Vulcan/Mars | re-seed or re-affirm the durable anchor after a regression | state_request patch on config:session-seq | Living State | COMPLETE |
| kd_session_open | auto self-heal a stale instance row on open | tools/session.py self-heal path | registry | COMPLETE |
| Max | authorize or perform a physical host restart and resolve strategic forks | shell | host owner | COMPLETE |

Both instances own the non-interactive recovery steps (inspect, migrate, cleanup, re-seed, restart-and-verify). The self-heal runs automatically inside `kd_session_open`. Max is the escalation contact for a host-level restart or a strategic decision (for example, deliberately re-anchoring the counter).

## §E. Operate

```yaml operate
- id: E-01
  trigger: Routine verification that the session registry is healthy before relying on session opens.
  pre_conditions:
    - registry.db exists at the production path or KOSKADEUX_REGISTRY_DB points at the intended DB
    - sqlite3 available on Titan-1
  tool_or_endpoint: "sqlite3 /var/tmp/koskadeux/registry.db on schema_migrations, session_seq, sessions, plus PRAGMA integrity_check"
  argument_sourcing:
    db_path: production path, or KOSKADEUX_REGISTRY_DB if overridden
    expected_schema_version: 7 (session_seq_durable_hwm)
  idempotency: IDEMPOTENT
  expected_success:
    shape: schema_migrations top version is 7, session_seq.next_value is greater than every live session number, integrity_check returns ok, and only vulcan, mars, and scratch rows exist
    verification: confirm each query output matches the expected version, a monotonic next_value, and ok integrity
  expected_failures:
    - signature: "integrity_check_not_ok"
      cause: SQLite corruption, repair via G-04
    - signature: "schema_version_below_7"
      cause: a pending migration has not applied, repair via G-04
  next_step_success: No action; the registry is healthy.
  next_step_failure: Isolate using F-04 for corruption or pending migration.
- id: E-02
  trigger: Confirm the monotonic counter has not regressed or reused a number after a suspicious event.
  pre_conditions:
    - registry readable
    - Living State reachable for the anchor read
  tool_or_endpoint: "compare session_seq.next_value, the Living State anchor config:session-seq, and the max non-scratch session number"
  argument_sourcing:
    local_next: session_seq.next_value from registry.db
    anchor: config:session-seq next_value from Living State
    max_row: highest numeric session id among vulcan and mars rows
  idempotency: IDEMPOTENT
  expected_success:
    shape: session_seq.next_value is at least the anchor and strictly greater than the max non-scratch session number
    verification: all three agree on a non-decreasing high-water mark
  expected_failures:
    - signature: "next_value_below_anchor"
      cause: registry rebuilt or restored without re-seeding from the anchor, repair via G-02
    - signature: "number_reused_or_regressed"
      cause: live DB mutated by a test run or a rewritten row, repair via G-02
  next_step_success: No action; the counter is monotonic.
  next_step_failure: Isolate using F-02 and re-seed the anchor.
- id: E-03
  trigger: Restart the MCP server in a way that safely applies any pending registry migration.
  pre_conditions:
    - a registry backup can be written
    - operator is ready to re-run kd_session_open and kd_session_plan after restart
  tool_or_endpoint: "back up registry.db, then launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp in the FOREGROUND, then verify"
  argument_sourcing:
    backup_target: /var/tmp/koskadeux/backups/registry.db.<UTC>.bak
    restart_label: com.koskadeux.mcp
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: the timestamped backup filename makes repeated backups distinct and safe
  expected_success:
    shape: a fresh server pid with a recent start time, schema version 7, session_seq present and monotonic, and integrity ok
    verification: ps -o lstart on the new pid shows a recent start, and the §E-01 checks pass
  expected_failures:
    - signature: "restart_did_not_fire"
      cause: a backgrounded or detached kickstart was killed by the shell sandbox before running, repair via G-04 restart guidance
    - signature: "migration_rollback_in_logs"
      cause: a migration failed mid-run and the server entered memory-only mode, repair via G-04
  next_step_success: Re-run kd_session_open and kd_session_plan to re-establish the boot gate.
  next_step_failure: Isolate using F-04.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | kd_session_open is blocked or hangs and a row appears occupied with no live process | A stale OPERATIONAL or PLANNING row whose instance is no longer running; self-heal did not fire because last_seen was recently bumped, OR (observed S901) the stale row belongs to a DIFFERENT instance than the one opening — on-open self-heal evaluates the opening instance's own slot and does not sweep foreign-instance stale rows, so a stale scratch/peer row survives another instance's open and needs a manual reap | Read the sessions table and compare last_seen_at age against the TTL; check peer_status and the peer bus for a real signal from that instance | §G-01 | CONFIRMED |
| F-02 | A session number regressed, reused, or looks lower than expected | The live registry.db was mutated by a test run or a row was rewritten, rewinding the max-based floor; or a rebuild did not re-seed from the anchor | Compare session_seq.next_value, the config:session-seq anchor, and the max non-scratch row; cross-check the peer bus for the real latest number | §G-02 | CONFIRMED |
| F-03 | The scratch row appears to drive the allocator or a surprising scratch number shows up | scratch rows are test or agent-isolation residue; the allocator must exclude scratch from its max | Read the sessions table for the scratch row and confirm the allocator floor uses only vulcan and mars rows | §G-03 | CONFIRMED |
| F-04 | health reports registry_mode memory_only, or logs show a migration rollback, or integrity_check is not ok | SQLite corruption, a failed mid-run migration leaving memory-only mode, or a pending migration not yet applied | Run integrity_check and read schema_migrations; check the server logs for a rollback sentinel | §G-04 | CONFIRMED |
| F-05 | The schema_migrations version row disagrees with the real table shape | Test mutation of the live DB advanced or rewound the version row independent of the actual DDL | Inspect the live schema with sqlite3 .schema sessions and compare against the version row; the live DDL is authoritative | §G-05 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Self-Heal
  root_cause: A stale instance row is blocking opens; the two-signal self-heal did not auto-close it because last_seen_at was within the TTL or a peer-check error forced fail-open.
  repair_entry_point: tools/session.py _auto_close_stale_instance_if_safe
  change_pattern: First retry kd_session_open, which runs the self-heal and auto-closes a row that is past the TTL with no recent peer-bus signal, emitting session_auto_closed_stale. If the row is genuinely dead but still inside the TTL window, confirm via peer_status and the peer bus that the instance is not live, then run scripts/s852_phantom_session_cleanup.py against the registry to clear the phantom row. The script is a RANGE deleter: it removes every session number strictly above --cutoff that is not in --protect, across the registry AND Living State, and DEFAULTS to --cutoff 846 (which would delete current live sessions). To reap a single stale row, set --cutoff to just below the target number and --protect every live session id, e.g. to reap S801 while S900/S901 are live: --cutoff 800 --upper 801 --protect S900,S901. Dry-run (omit --execute) first and confirm phantom_rows lists ONLY the target. Never clear a row whose instance shows recent peer-bus activity.
  rollback_procedure: The cleanup script does NOT back up the registry (verified S901; this runbook previously claimed it did). The OPERATOR MUST copy registry.db to /var/tmp/koskadeux/backups/ BEFORE running --execute, then restore that backup if a row was cleared in error.
  integrity_check: kd_session_open succeeds, the sessions table shows the stale row CLOSED, and a session_auto_closed_stale event is present.
- id: G-02
  symptom_ref: F-02
  component_ref: Durable HWM Anchor
  root_cause: The local session_seq fell below the durable anchor, or a rebuild or restore did not re-seed from config:session-seq, so the max-based floor rewound.
  repair_entry_point: tools/session.py _session_seq_key plus the config:session-seq Living State entity
  change_pattern: The durable anchor config:session-seq stores next_value, the NEXT allocatable number (one greater than the highest issued), and session_seq.next_value uses the same next-value units. Re-seed by patching config:session-seq next_value to the maximum of the current anchor next_value, the local session_seq next_value, and the highest issued session number PLUS ONE. The plus-one matters because the peer bus reports the highest issued number (for example S873) while the anchor is in next-value units, so patching the raw issued number would let the next open reissue it. Then let the next open re-establish session_seq from the anchor, or apply the session_seq migration which seeds from the computed max. Never lower the anchor; never reset to 1.
  rollback_procedure: The anchor only ever increases; if an over-large value was written, leave it (a skipped number is harmless) rather than lowering the anchor.
  integrity_check: session_seq.next_value is at least the anchor and strictly greater than the max non-scratch row, and the next open issues a strictly higher number.
- id: G-03
  symptom_ref: F-03
  component_ref: Allocator
  root_cause: A scratch row is being treated as part of the allocation floor, or scratch residue from a test or agent-isolation run is confusing the operator.
  repair_entry_point: tools/registry.py Registry.register_allocated_session
  change_pattern: Confirm the allocator computes its floor from vulcan and mars rows only and excludes scratch (it raises if asked to allocate for scratch). Treat scratch rows as non-authoritative; if a scratch row is stale, close it via the self-heal path. No allocation logic change is needed unless the scratch row is provably included in the max.
  rollback_procedure: None; this is a verification and cleanup, not a code change.
  integrity_check: The next allocated number is one greater than the max vulcan/mars row regardless of any scratch row value.
- id: G-04
  symptom_ref: F-04
  component_ref: Migration Runner
  root_cause: SQLite corruption, a failed mid-run migration leaving memory-only mode, or a pending migration not applied on the running server.
  repair_entry_point: scripts/migrate_session_registry.py
  change_pattern: Back up registry.db first. Run the migration runner with status to see applied versions, then apply to bring the DB to version 7. On corruption, rebuild the DB and let the anchor re-seed session_seq. Restart the MCP via FOREGROUND launchctl kickstart (a backgrounded or detached restart is killed by the shell sandbox before it runs) and verify the new pid start time with ps -o lstart before declaring success.
  rollback_procedure: Restore the pre-repair backup from /var/tmp/koskadeux/backups/ and restart if the migration or rebuild leaves the registry worse.
  integrity_check: health reports registry_mode sqlite, schema_migrations top version is 7, integrity_check is ok, and a fresh server pid is serving tool calls.
- id: G-05
  symptom_ref: F-05
  component_ref: Migration Runner
  root_cause: The schema_migrations version row disagrees with the real table shape after test mutation of the live DB.
  repair_entry_point: scripts/migrate_session_registry.py plus sqlite3 .schema
  change_pattern: Treat the live DDL as authoritative, not the version row. Inspect the real schema, then re-run the migration runner, which decides what to apply by inspecting the live table shape and is idempotent, to reconcile the version row to reality. Do not hand-edit the version row.
  rollback_procedure: Restore the pre-repair backup if reconciliation changes the table unexpectedly.
  integrity_check: sqlite3 .schema sessions matches the expected version-7 shape and the version row reads 7.
```

## §H. Evolve

### §H.1 Invariants

- The session-number allocator MUST be monotonic: a newly issued number is never less than or equal to any previously issued number, even after a registry wipe, rebuild, or restore (it re-seeds from `config:session-seq`).
- The durable anchor `config:session-seq` only ever increases; it is never lowered.
- The anchor MUST be reserved to at least the candidate number BEFORE the registry row is written, and allocation MUST fail closed if Living State is unreachable.
- Tests MUST NOT operate on the production `registry.db`: `conftest.py` sets `KOSKADEUX_REGISTRY_DB` at collection time and `open_registry` raises `RegistryProductionPathError` if `PYTEST_CURRENT_TEST` is set on the production path.
- The `scratch` instance is excluded from the allocation floor and is never issued an allocated number.
- A stale row is auto-closed only on TWO signals (last_seen past TTL AND no recent peer-bus signal); the peer check fails open on error so a live session is never killed.
- Schema migrations are append-only; existing column names and types are frozen, and idempotency is keyed on the live table shape, not the `schema_migrations` version row.

### §H.2 BREAKING predicates

- Making the allocator able to issue a number less than or equal to a prior number (including resetting to 1, or lowering the anchor) is BREAKING; it violates the monotonic invariant.
- Removing or weakening the pytest production-path guard, or the collection-time env override, is BREAKING; tests would corrupt live session state.
- Changing allocation to issue before reserving the anchor, or to fail open when Living State is unreachable, is BREAKING; it reintroduces the regression vector.
- Removing a column from `sessions`, `session_seq`, or `schema_migrations`, or changing a column type, is BREAKING; migrations are append-only.

### §H.3 REVIEW predicates

- Changing the stale TTL (`SESSION_LIVE_TTL_SECONDS`) or the second-signal source for self-heal requires REVIEW; it changes when a row is considered reapable.
- Adding a new schema migration requires REVIEW; it must be append-only, transactional, and idempotent on the live DDL.
- Changing how `scratch` is namespaced or admitted to the `sessions` table requires REVIEW.

### §H.4 SAFE predicates

- Read-only inspection of the registry, the anchor, and the migration state is SAFE.
- Running the migration runner with status, or applying an already-defined append-only migration, is SAFE.
- Re-seeding the anchor upward to the true high-water mark is SAFE (the anchor only increases).

### §H.5 Boundary definitions

#### module

The module boundary is the Koskadeux session-registry surface: `tools/registry.py` (store, allocator, migrations), the registry-facing parts of `tools/session.py` (boot gate, self-heal, anchor), `scripts/migrate_session_registry.py`, and `tools/admin_endpoints.py`.

#### public contract

The public contract is the registry shape other code depends on: the `sessions`, `session_seq`, and `schema_migrations` table schemas, the `KOSKADEUX_REGISTRY_DB` env override, the `config:session-seq` anchor semantics, and the `session_auto_closed_stale` event type.

#### runtime dependency

A runtime dependency is any external system required at run time: SQLite for `registry.db`, Living State on Railway Postgres for the anchor, and the peer-message bus for the self-heal second signal.

#### config default

A config default is a shipped default value: the production `registry.db` path, `SESSION_LIVE_TTL_SECONDS` of 1800, and the current schema version 7.

### §H.6 Adjudication

When two instances classify a registry change differently, the more restrictive class wins and the dispute is recorded. Max resolves any classification dispute that touches the monotonic invariant, the test-isolation guard, or the anchor semantics; the ruling is added here as a §H.1 clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §C]
    scenario: |
      id: E-01. trigger: routine verification the registry is healthy. tool_or_endpoint: sqlite3 against schema_migrations, session_seq, sessions, and PRAGMA integrity_check. expected_success: schema version 7, session_seq.next_value above every live number, integrity ok, only vulcan mars scratch rows. next_step_failure: isolate with F-04.
    expected_answers:
      - kind: human_action
        verb: verify
        object: registry schema version session_seq and integrity
        target: sqlite3 on registry.db
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02, §C]
    scenario: |
      id: E-02. trigger: confirm the counter has not regressed. tool_or_endpoint: compare session_seq.next_value, the config:session-seq anchor, and the max non-scratch number. expected_success: next_value at least the anchor and above the max row. next_step_failure: isolate with F-02.
    expected_answers:
      - kind: human_action
        verb: compare
        object: session_seq anchor and max session number
        target: confirm a non-decreasing high-water mark
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03, §C]
    scenario: |
      id: E-03. trigger: restart MCP and apply any pending migration safely. tool_or_endpoint: back up registry.db then FOREGROUND launchctl kickstart then verify. expected_success: fresh pid, schema 7, monotonic session_seq, integrity ok. next_step_failure: isolate with F-04.
    expected_answers:
      - kind: human_action
        verb: restart
        object: the MCP server in the foreground after a backup
        target: launchctl kickstart then verify pid and schema
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-01, G-01]
    scenario: |
      id: F-01. trigger: kd_session_open hangs and a row looks occupied with no live process. verification: compare last_seen_at age to the TTL and check peer_status and the peer bus. expected_success: classify as a stale row the self-heal did not auto-close. next_step_success: apply G-01.
    expected_answers:
      - kind: human_action
        verb: classify
        object: a blocked session open with a stale row
        target: F-01 then G-01
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-02, G-02]
    scenario: |
      id: F-02. trigger: a session number regressed or reused. verification: compare session_seq.next_value, the anchor, and the max non-scratch row, and cross-check the peer bus. expected_success: classify as a rewound floor from live-DB mutation or a non-reseeded rebuild. next_step_success: apply G-02.
    expected_answers:
      - kind: human_action
        verb: classify
        object: a regressed or reused session number
        target: F-02 then G-02
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-04, G-04]
    scenario: |
      id: F-04. trigger: health reports registry_mode memory_only or logs show a migration rollback. verification: run integrity_check and read schema_migrations and the rollback sentinel. expected_success: classify as corruption, a failed migration, or a pending migration. next_step_success: apply G-04.
    expected_answers:
      - kind: human_action
        verb: classify
        object: a memory-only or rolled-back registry
        target: F-04 then G-04
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [F-05, G-05]
    scenario: |
      id: F-05. trigger: the schema_migrations version row disagrees with the table shape. verification: inspect the live schema and compare to the version row, treating the live DDL as authoritative. expected_success: classify as a version-row drift from test mutation. next_step_success: apply G-05.
    expected_answers:
      - kind: human_action
        verb: classify
        object: a schema version-row disagreement
        target: F-05 then G-05
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-02, F-02]
    scenario: |
      id: G-02. trigger: the local session_seq fell below the durable anchor after a rebuild. change_pattern: re-seed config:session-seq next_value to the max of the anchor next_value, the local session_seq next_value, and the highest issued number plus one, then let the next open re-establish session_seq, never reset to 1. expected_success: next_value at least the anchor and above the max row. next_step_failure: leave an over-large anchor rather than lowering it.
    expected_answers:
      - kind: human_action
        verb: reseed
        object: the durable anchor config:session-seq
        target: the true high-water mark, never reset to 1
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-04, F-04]
    scenario: |
      id: G-04. trigger: a failed mid-run migration left the registry in memory-only mode. change_pattern: back up, run the migration runner to apply to version 7, then FOREGROUND launchctl kickstart and verify the new pid start time. expected_success: registry_mode sqlite, schema 7, integrity ok, fresh pid. next_step_failure: restore the backup and restart.
    expected_answers:
      - kind: human_action
        verb: apply
        object: the pending registry migration then restart in foreground
        target: migration runner then launchctl kickstart with verification
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: |
      id: H-01. trigger: a proposal would let the allocator reset the counter to 1 on a fresh registry. expected_success: classify as BREAKING because it violates the monotonic invariant. next_step_success: block the change and re-seed from the anchor instead.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [§H]
    scenario: |
      id: H-02. trigger: a proposal would remove the pytest production-path guard so a fixture can write to the real registry.db. expected_success: classify as BREAKING because tests would corrupt live session state. next_step_success: keep the collection-time env override and the guard.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [F-01, F-02]
    scenario: |
      id: AMB-01. trigger: on open the operator sees a surprising session number AND a row that looks stale, and asks whether to clear the row and reset the number. pre_conditions: both observations made before any peer-bus check. expected_success: do NOT clear or reset first; cross-check peer_status and the peer bus to decide whether the row is a live peer and whether the number is real or test residue, then isolate via F-01 for the row and F-02 for the number separately. expected_failures: clearing a live peer's row or lowering the counter on the assumption it is residue. next_step_success: run the peer-bus check, then F-01 and F-02 independently. next_step_failure: escalate to Max if a live peer cannot be confirmed either way.
    expected_answers:
      - kind: human_action
        verb: check
        object: peer_status and the peer bus before clearing or resetting
        target: confirm live peer then isolate F-01 and F-02 separately
    weight: 0.08333333333333333
```

## §J. Lifecycle

Lifecycle metadata records the conformance refresh state for this runbook.

```yaml lifecycle
last_refresh_session: S873
last_refresh_commit: 0767d248
last_refresh_date: 2026-06-16T08:30:00Z
owner_agent: vulcan
refresh_triggers:
  - registry schema or migration changes
  - allocator or durable-anchor semantics change
  - stale-session self-heal policy or TTL changes
  - session lifecycle model changes (for example a peer-model change)
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-06-16T08:30:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S873 / 2026-06-16T08:30:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
