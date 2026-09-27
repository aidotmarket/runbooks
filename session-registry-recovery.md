---
title: Session Registry Recovery
owner: vulcan
last_verified: '2026-09-27'
aliases: []
error_signatures:
- integrity_check_not_ok
- schema_version_below_7
- next_value_below_anchor
- number_reused_or_regressed
- restart_did_not_fire
- migration_rollback_in_logs
---

# Session Registry Recovery

## Overview

The current instance roster has three active peers: `athena`, `mars`, and `vulcan` (previously verified 2026-09-27). Registry admission reads the roster; `scratch` is the non-human registry instance. The older two-peer and primary/worker lock-slot descriptions are historical. The `sessions` table is instance-keyed; `session_seq` and Living State `config:session-seq` provide the monotonic session-number floor. At production source `e8a3177ccf728107549aafa903d2574da5b7c104`, the current schema ladder is versions 1 through 9.

## Capabilities

| Capability | Current behavior and evidence |
|---|---|
| Monotonic session numbers | `Registry.register_allocated_session` reserves the Living State anchor before writing an allocated session. `scratch` is excluded. Source verified at `e8a3177ccf`; the live anchor value was not read in this refresh. |
| Roster-backed instances | `tools/instance_roster.py` supplies active peers and appends `scratch` for registry rows. The current roster is `athena`, `mars`, `vulcan`; it is not a literal SQLite peer-name list. |
| V8 roster migration | `apply_instance_roster_migration` makes legacy `role` nullable and removes the literal instance `CHECK`. Fresh matching shapes record v8 metadata without rebuild or backup. A nonempty old-shape database receives a timestamped mode-0600 SQLite online backup beside the DB before a transactional rebuild; the migration does not prune it. It checks row counts and recreates schema-owned indexes and triggers. |
| V9 capability migration | `apply_session_capability_migration` adds `session_capabilities`, `session_capability_events` (including revocation evidence), and the partial unique `one_live_session_capability` index where `revoked_at IS NULL`. V9 is forward-only. |
| Production DB and test guard | `DEFAULT_DB_PATH` is `/Users/max/koskadeux-state/registry.db`; `KOSKADEUX_REGISTRY_DB` overrides it. `open_registry` rejects the production path under `PYTEST_CURRENT_TEST`. |
| Stale-session self-heal | `tools/session.py` requires an expired `last_seen_at` and no recent peer-bus signal for the opening instance; peer-check errors fail open. Another instance's open does not sweep a foreign-instance row. |

The 2026-09-27 read-only primary-database check used SQLite URI `mode=ro`: `PRAGMA quick_check` returned `ok`; journal mode was `delete`; `schema_migrations` contained versions 1–9; the six tables were `sessions`, `session_seq`, `schema_migrations`, `close_transactions`, `session_capabilities`, and `session_capability_events`; and `one_live_session_capability` existed. These are schema and integrity observations, not a restore or end-to-end recovery test. No capability token, hash, or data row was read.

## Architecture & interactions

The registry is one file in `/Users/max/koskadeux-state`, alongside `council_hall.db`, `boot_gate_runtime.json`, `session_instance_alias_counters.json`, `agent_usage.csv`, `cc_tasks/`, `verdicts/`, and `reloader/`. A registry-only restore proves only that file. Whole durable-state recovery requires a separately approved, coordinated procedure for the complete set and external Living State dependencies.

`Registry.register_allocated_session` admits only active roster peers, rejects `scratch`, checks same-instance live-slot occupancy, reserves the anchor, then writes the row and advances `session_seq`. The `role` column remains a nullable legacy field with a `primary`/`worker` value check; it is not the roster or an authorization source. Compare the local next value, durable anchor, and issuance history before an approved recovery action. Never lower the anchor or reset it to 1.

The v8 backup uses `sqlite3.Connection.backup`, which takes a consistent SQLite snapshot. A raw filesystem copy of an active database is not equivalent. The backup is beside the database under the durable root, not automatically in `/var/tmp/koskadeux/backups/`. A missing `*.pre-instance_roster_role_nullable-*.bak` glob is not loss proof: a fresh matching shape or empty database legitimately skips it. A present backup does not prove complete durable-state or Living State recovery. The 2026-09-27 isolated Time Machine restore proved a 61,440-byte registry file with six tables and `integrity_check=ok`; it did not prove whole-state disaster recovery.

| Component | Source | State and dependency |
|---|---|---|
| Registry and allocator | `tools/registry.py` | `sessions`, `session_seq`, `close_transactions`; Living State anchor and active roster |
| Migrations | `tools/registry.py` v8/v9 functions; `scripts/migrate_session_registry.py` | `schema_migrations` and SQLite schema. Verify the entry point: at this source the standalone runner's registered ladder ends at v8, while `open_registry` applies v9. |
| Self-heal | `tools/session.py` | `sessions.last_seen_at` and peer bus |
| Boot gate | `tools/session.py` | Session lifecycle and durable records |
| Admin recovery | `tools/admin_endpoints.py` | Gateway reachability does not authorize mutation |

### Canonical identifiers

| Resource | Current value |
|---|---|
| Registry path | `/Users/max/koskadeux-state/registry.db` |
| Path override | `KOSKADEUX_REGISTRY_DB` |
| Anchor | `config:session-seq` in Living State |
| Current schema | `9` (`operator_session_capabilities`), after v8 `instance_roster_role_nullable` |
| Tables | `sessions`, `session_seq`, `schema_migrations`, `close_transactions`, `session_capabilities`, `session_capability_events` |
| Registry instances | Current active roster: `athena`, `mars`, `vulcan`; plus non-human `scratch` |
| Stale TTL default | `SESSION_LIVE_TTL_SECONDS=1800` |
| V8 automatic backup | Timestamped `registry.db.pre-instance_roster_role_nullable-*.bak` beside the DB only for a nonempty old-shape migration |

## Agent capabilities

Operators may inspect approved metadata read-only. Migration, restart, cleanup, restore, and anchor writes require the applicable current procedure and authority for the live environment. The roster determines peer admission; this runbook does not grant every peer blanket rights to recovery mutations. Max is the escalation contact for a host-level restart or a decision affecting the durable anchor.

## How to operate

```yaml operate
- id: E-01
  trigger: Verify registry schema and integrity before relying on session opens.
  pre_conditions:
    - Confirm the intended database path and current read-only access procedure.
  tool_or_endpoint: SQLite URI mode=ro; PRAGMA quick_check, sqlite_master table/index names, schema_migrations versions, and PRAGMA table_info(sessions).
  argument_sourcing:
    db_path: Confirm production path or documented KOSKADEUX_REGISTRY_DB override.
    expected_schema_version: 9, with versions 1 through 9 present.
  idempotency: IDEMPOTENT
  expected_success:
    shape: quick_check is ok; six expected tables and the one_live_session_capability index exist; role is nullable and sessions has no literal roster CHECK.
    verification: Compare metadata with deployed source; do not query capability values or sensitive rows.
  expected_failures:
    - signature: integrity_check_not_ok
      cause: Suspected SQLite integrity problem; isolate before repair.
    - signature: schema_version_below_7
      cause: Historical signature for an older migration gap; any version below current 9 also needs source and shape review.
  next_step_success: Record the read-only observation and its limits.
  next_step_failure: Isolate with F-04 or F-05; use an approved procedure for mutation.
- id: E-02
  trigger: Investigate a suspected session-number regression.
  pre_conditions:
    - Approved read-only access to the registry, anchor, and issuance evidence.
  tool_or_endpoint: Compare session_seq.next_value, config:session-seq next_value, and the highest known issued non-scratch number.
  argument_sourcing:
    local_next: Registry next-value metadata.
    anchor: Living State next-value metadata.
    max_issued: Highest confirmed issued number, including history beyond current rows.
  idempotency: IDEMPOTENT
  expected_success:
    shape: The next issuance is above all confirmed issued numbers and does not reduce the anchor.
    verification: Reconcile evidence before proposing a change; a current sessions row alone is not issuance history.
  expected_failures:
    - signature: next_value_below_anchor
      cause: Local floor may be stale after restore or rebuild.
    - signature: number_reused_or_regressed
      cause: Number evidence conflicts; stop allocation and investigate.
  next_step_success: Record evidence; no mutation is implied.
  next_step_failure: Isolate with F-02 and obtain an approved recovery plan.
- id: E-03
  trigger: A migration or restart is proposed after a schema or runtime failure.
  pre_conditions:
    - Current migration and restart procedures, operator authority, peer coordination, and a restore-verified backup plan are approved.
  tool_or_endpoint: Use the approved procedure for this exact deployed source and whole durable-state boundary.
  argument_sourcing:
    migration_target: Verify the actual runtime entry point and current v9 schema; the standalone runner's registered ladder ends at v8 at source e8a3177ccf.
    backup_target: Use a consistent SQLite snapshot and the approved durable-root retention procedure.
  idempotency: CONDITIONAL
  expected_success:
    shape: Migration and restart receipts, exact runtime identity, schema 9, integrity ok, and preserved anchor and peer state.
    verification: Verify separately after an authorized procedure; a fresh PID or backup file is insufficient.
  expected_failures:
    - signature: restart_did_not_fire
      cause: Restart did not occur; diagnose under the current restart procedure.
    - signature: migration_rollback_in_logs
      cause: Migration failed; retain original files and investigate before retry.
  next_step_success: Resume session lifecycle only under its current procedure.
  next_step_failure: Stop and escalate; do not improvise a restore or reseed.
```

## When it breaks

| ID | Symptom | Read-only isolation | Repair reference |
|---|---|---|---|
| F-01 | An open is blocked by an occupied row | Check age, process and peer-bus signals, including foreign-instance rows. Do not infer death from a stale timestamp alone. | G-01 |
| F-02 | A number looks reused or lower | Compare local sequence, anchor, and confirmed issued-number history. | G-02 |
| F-03 | A `scratch` row appears to affect allocation | Verify source excludes `scratch`; check roster admission and allocator evidence. | G-03 |
| F-04 | Registry is unavailable, migration fails, or integrity fails | Read metadata and logs; distinguish corruption, missing schema, and runtime failure. | G-04 |
| F-05 | Version rows disagree with schema shape | Compare live DDL and indexes against deployed source; the row alone is not shape proof. | G-05 |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Self-Heal
  root_cause: A stale or foreign-instance row may block an open.
  repair_entry_point: tools/session.py _auto_close_stale_instance_if_safe
  change_pattern: Under the current approved session procedure, establish that the peer is not live before considering a retry or targeted cleanup. The historical s852_phantom_session_cleanup.py range deleter is not certified here for live use; its old default cutoff and broad reach can affect unrelated sessions and Living State.
  rollback_procedure: Use a separately approved, restore-verified registry and Living State recovery plan; do not raw-copy an active DB or assume a script made a backup.
  integrity_check: Verify the intended row and all active peer sessions without deleting peer history.
- id: G-02
  symptom_ref: F-02
  component_ref: Durable HWM Anchor
  root_cause: The local floor or issuance evidence disagrees with the durable anchor.
  repair_entry_point: tools/session.py anchor logic and tools/registry.py allocator
  change_pattern: Stop and reconcile confirmed issued-number history, local next value, and the Living State anchor. Any approved re-seed must preserve the maximum known next-value floor. Never lower the anchor, reset to 1, or experiment on production.
  rollback_procedure: An anchor increase is intentionally monotonic; do not lower it to undo an overshoot.
  integrity_check: The next approved issuance exceeds every confirmed issued number and the anchor remains monotonic.
- id: G-03
  symptom_ref: F-03
  component_ref: Allocator
  root_cause: Scratch residue or an incorrect inference about allocation.
  repair_entry_point: tools/registry.py Registry.register_allocated_session
  change_pattern: Verify the current source and roster metadata; any cleanup needs a separate approved procedure.
  rollback_procedure: No mutation is prescribed here.
  integrity_check: Scratch is excluded from allocation; active roster peers remain intact.
- id: G-04
  symptom_ref: F-04
  component_ref: Migration Runner
  root_cause: Corruption, a failed migration, or a runtime/schema mismatch.
  repair_entry_point: tools/registry.py migration functions and scripts/migrate_session_registry.py
  change_pattern: Prepare an approved coordinated recovery procedure for exact deployed source, consistent SQLite snapshot, durable-state set, anchor, peers, and restart. Do not treat a v8 standalone runner status as v9 completion, or assume an automatic pre-v8 backup exists.
  rollback_procedure: Restore only through the approved coordinated procedure; a registry file alone does not restore all durable state.
  integrity_check: Schema 9, quick_check ok, source/runtime identity, peer admission, and anchor continuity are independently verified.
- id: G-05
  symptom_ref: F-05
  component_ref: Migration Runner
  root_cause: Migration metadata and actual DDL differ.
  repair_entry_point: tools/registry.py apply_instance_roster_migration and apply_session_capability_migration
  change_pattern: Compare exact schema objects and source. Design a reviewed migration reconciliation before any write; do not hand-edit version rows or assume an old runner repairs v9.
  rollback_procedure: Use the approved consistent snapshot and coordinated restore plan.
  integrity_check: Versions 1 through 9 and the six-table, partial-index schema match deployed source.
```

## Changes and maintenance

### Invariants

- Session numbers and `config:session-seq` remain monotonic across rebuilds and restores.
- `scratch` is never allocated a session number; active peer names come from the roster, not a hard-coded two-peer list.
- V8 old-shape rebuilds preserve row counts, schema-owned indexes/triggers, and a consistent pre-migration backup for nonempty databases. A fresh matching shape can have v8 metadata without that backup.
- V9 retains capability and revocation evidence and the partial one-live index.
- Tests never open the production registry path under `PYTEST_CURRENT_TEST`.

### Change classification

Resetting the anchor, weakening the production-path test guard, bypassing roster admission, or discarding capability revocation evidence is BREAKING. Changing stale-session policy, migration DDL, or backup/restore behavior requires review. Read-only metadata inspection is safe within the current access procedure; applying a migration, restarting, reseeding, cleanup, or restore is conditional on the applicable approved procedure and authority.

### Boundary definitions

The module includes `tools/registry.py`, registry-facing `tools/session.py`, `tools/instance_roster.py`, `scripts/migrate_session_registry.py`, and `tools/admin_endpoints.py`. The public contract includes the six tables, `one_live_session_capability`, roster-backed admission, path override, and monotonic anchor. Runtime dependencies include SQLite, Living State, and peer bus. The shipped TTL default is 1800 seconds; the current schema is v9.

## Acceptance criteria

- A read-only primary check reports `quick_check=ok`, six expected tables, versions 1–9, and the partial one-live capability index; it does not expose capability values or rows.
- The overview, capability table, identifiers, verification, and repair text all describe three currently active peers plus `scratch`, roster-backed admission, v8/v9 behavior, and the conditional backup rule.
- A fresh v8-shaped database with migration metadata and no pre-v8 backup is not classified as lost data. A nonempty old-shape v8 rebuild has a consistent online backup beside the database, mode 0600, with no automatic pruning.
- A registry-only Time Machine restore is file proof, never whole durable-state disaster-recovery proof.
- Every live migration, restart, reseed, cleanup, SQL write, and restore remains conditional on a current approved procedure. This docs-only correction performs none of them.

## Maintenance

This S1754 correction uses production source `e8a3177ccf728107549aafa903d2574da5b7c104`, read-only primary SQLite metadata from 2026-09-27, and the isolated Time Machine registry-file observation above. Recheck when the roster, migration ladder, allocator, durable-state set, or approved recovery procedure changes.
