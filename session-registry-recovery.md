> **S612 Process Consolidation Owner**: this runbook is part of the session lifecycle reliability runbook set after the S612 consolidation that collapsed ~15 process BQs into BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612 (P0). Paired with session-open-protocol.md and session-close-protocol.md.
>
> Disk-backed session registry work (P0) is tracked under the survivor BQ; recurrence chain currently at 9 manual primary clears (S596 through S612). See session-close-protocol.md §C.7 for the recurrence audit pattern.
>
> Revisions land as PRs; require MP+AG review-mode approval (registry criticality). Filed under S612.

---

# Session Registry Recovery Runbook

**BQ:** BQ-KOSKADEUX-SESSION-REGISTRY-DISK-BACKED-S594 · Gate 1 AC8  
**Covers:** commit 10/10 — documentation deliverable  
**Last updated:** 2026-05-11

---

## When to use this runbook

Use this runbook when `kd_session_open` cannot proceed because a lock slot appears occupied but
no live session process exists. Concrete symptoms:

- `kd_session_open` returns `primary_lock_held` or `worker_lock_held` with no visible active session
- `kd_session_open` enters the emergency-fallback path and returns an envelope that never contains a handoff (response-routing phantom — S599.W pattern)
- `state_request action=get key=infra:active-session-lock` shows a `primary` or `worker` slot with `started_at` > 2 hours ago and no matching process
- Orphaned `session-status:{id}:role=worker` entities remain open after the process died
- Gateway restart did not clear the lock (disk-persistent slot survived pid change — S589.W pattern)

**Recurrence chain** (S587–S599): Five documented cases drove this runbook:

| Case | Cleared at | Pattern | Cleared by |
|------|-----------|---------|------------|
| S589.W ghost | 2026-05-09T19:18Z | Disk-persistent ghost, survived gateway restart | Level 1 state_request |
| S590.W stale | 2026-05-09T19:55Z | Slot never patched after prior clear narrative | Level 1 state_request |
| S593+S592.W phantom | 2026-05-10T~06:54Z | Emergency-fallback phantom + 9h stale worker | Level 3 Railway psql |
| S595 primary stale | 2026-05-10T16:00Z | allAI log timeout prevented close completion | Level 1 state_request |
| S599.W routing phantom | 2026-05-10T22:07Z | Server-side success, response routed to wrong client | Level 1 state_request |

Do NOT use this runbook if you suspect a genuine in-flight session. Confirm with Vulcan-Primary first.

---

## §A Registry health quick-check

Before any intervention, confirm the gateway stack is alive and identify the registry mode.

**1. Confirm handler and proxy processes:**

```bash
ps -ef | grep -E 'koskadeux_server|gateway_server' | grep -v grep
```

Expected: `koskadeux_server.py` (handler, port 8765) and `gateway_server.py` (proxy, port 8767).
If either is missing, restart via launchctl before proceeding — a dead handler will make every
`kd_session_open` appear to hang regardless of lock state.

**2. Confirm ports are listening:**

```bash
netstat -an | grep -E '8765|8767'
```

Expected: LISTEN on both ports. If 8765 is absent but 8767 is listening, the proxy is up but
the handler crashed — restart handler: `launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp`

**3. Check lock entity state via admin endpoint:**

```bash
curl -s http://localhost:8767/health | python3 -m json.tool
curl -s http://localhost:8767/api/admin/gate_state | python3 -m json.tool
```

`/health` fields to note:
- `registry_mode`: `sqlite` (normal) or `memory_only` (see §E)
- `sqlite_db_path`: default `/var/tmp/koskadeux/registry.db`
- `last_migration`: most recently applied schema migration

`/api/admin/gate_state` fields:
- `state`: boot gate state (`IDLE`, `PLANNING`, `OPERATIONAL`, etc.)
- `active_session_id`: current holder (null if idle)
- `registry_health`: sub-object with mode + last error

**4. Read the live lock entity** (captures pre-clear state for the audit trail):

```bash
state_request action=get key=infra:active-session-lock
```

Record the `primary` and `worker` sub-objects, `version`, and `updated_at` before touching anything.

---

## §B Standard recovery: stale slot auto-release

**Post-Gate-2 behaviour:** The gateway runs a live-process audit on every `kd_session_open` call
and auto-releases stale slots, emitting `role_slot_auto_released_stale_process` into the Event
Ledger. For ~90% of cases, retry `kd_session_open` after confirming §A is green — no operator
action needed.

When the auto-release path did not fire (pre-Gate-2 code or audit negative on a genuine phantom),
follow the diagnosis tree below.

### Diagnosis tree

```
kd_session_open returns *_lock_held
         │
         ▼
Check: ps -ef | grep -iE '<slot_session_id>|kd_worker|antigravity.*worker'
         │
    match found        no match
         │                  │
         ▼                  ▼
  Genuine in-flight     Is gateway healthy? (§A pass)
  — do NOT clear.            │
  Confirm with           yes │  no
  Vulcan-Primary.            │   └──► Restart gateway → retry
                             ▼
                    Is started_at < 30 min ago AND
                    client reported 300s timeout with no envelope?
                             │
                         yes │  no
                             │   └──► Stale-ghost slot
                             │        → Level 1 (§B.1)
                             ▼
                    Response-routing phantom (S599.W pattern):
                    server-side success, envelope misrouted.
                    Confirm with client actor, then → Level 1 (§B.1)
```

**Genuine in-flight vs. phantom**: if `worker_clear_audit_s{N-1}` already cleared this exact
session_id in a prior session, it is not genuine — proceed with Level 1.

### §B.1 Level 1: state_request patch

Use when Primary gateway is reachable via MCP tools. This is the standard operating path.

```bash
# Worker slot clear — fill in S{N} with the current session number
state_request action=patch key=infra:active-session-lock body='{
  "worker": null,
  "worker_clear_audit_s{N}": {
    "cleared_at": "<ISO8601_NOW>",
    "cleared_by": "vulcan-primary-S{N}",
    "cleared_reason": "<one-line reason — pattern name + evidence>",
    "pre_clear_state": {
      "worker_session_id": "<value from §A read>",
      "worker_started_at": "<value from §A read>",
      "worker_parent_session_id": "<value from §A read>"
    },
    "live_process_audit_evidence": "<ps output or 'no matching processes'>"
  }
}' updated_by=vulcan source_ref=S{N}
```

```bash
# Primary slot clear (same structure, different key names)
state_request action=patch key=infra:active-session-lock body='{
  "primary": null,
  "primary_clear_audit_s{N}": {
    "cleared_at": "<ISO8601_NOW>",
    "cleared_by": "vulcan-primary-S{N}",
    "cleared_reason": "<reason>",
    "pre_clear_state": {
      "primary_session_id": "<value from §A read>",
      "primary_started_at": "<value from §A read>"
    }
  }
}' updated_by=vulcan source_ref=S{N}
```

**Post-patch verification** — confirm both slots reflect intended state:

```bash
state_request action=get key=infra:active-session-lock
# Expect: body.worker = null and/or body.primary = null
# Expect: version incremented by 1
```

Also check for any orphaned session-status entity:

```bash
state_request action=get key=session-status:{cleared_session_id}:role=worker
# If body.ended_at is null, patch it manually (see §H post-recovery checklist)
```

---

## §C Force-release procedure

Use when Primary gateway is **unreachable via MCP** but `gateway_server.py` (proxy) is alive
(§A step 1 confirms the process is running).

The admin endpoint bypasses the boot gate entirely and is reachable even when no session is open.

```bash
# Dry run — returns 409 if session appears live, 200 if already clear or confirmed dead
curl -X POST http://localhost:8767/api/admin/release_role_slot \
  -H "Content-Type: application/json" \
  -H "X-Internal-API-Key: $INTERNAL_API_KEY" \
  -d '{"role": "worker", "session_id": "<session_id>", "force": false}'

# If 409 and ps confirms zero matches, use force=true
curl -X POST http://localhost:8767/api/admin/release_role_slot \
  -H "Content-Type: application/json" \
  -H "X-Internal-API-Key: $INTERNAL_API_KEY" \
  -d '{"role": "worker", "session_id": "<session_id>", "force": true}'
```

`INTERNAL_API_KEY` is resolved via Infisical (`ai-market` project). The endpoint emits a
`role_slot_force_released` audit event in the Living State Event Ledger automatically.

**A 409 with `force=false` means the session appears live.** Do NOT escalate to `force=true`
without running the ps audit in §B's diagnosis tree first.

**Post-release check:**

```bash
curl -s http://localhost:8767/api/admin/gate_state | python3 -m json.tool
# Expect: state=IDLE, active_session_id=null
```

---

## §D Emergency Railway psql procedure (last resort)

Use **only** when both Level 1 (MCP tools) and Level 2 (admin endpoint) are unavailable — the
gateway process is down and cannot be quickly restarted, or the SQLite registry is corrupt and
Postgres is the only source of truth.

**Warning:** This path writes directly to Postgres, bypassing the SQLite registry and the audit
Event Ledger. On the next gateway boot, `session_boot_gate.py` will detect the SHA divergence and
emit `emergency_psql_recovery_unrecorded` (Gate 1 AC8). That event is the automated paper trail.
You must also back-fill a `*_clear_audit_s{N}` sub-section via Level 1 once the gateway is back.

**This was the path used at S594** (~2026-05-10T06:54Z): primary slot held by phantom S593
(emergency-fallback never returned handoff) plus worker slot held by stale S592.W
(born 2026-05-09T22:29:03Z, 9+ hours old). Both cleared in a single Railway CLI session.

```bash
# Connect — unset RAILWAY_TOKEN to prevent stale env conflicts
unset RAILWAY_TOKEN && railway run psql
```

```sql
-- Step 1: Inspect current state (copy output to your audit trail before touching anything)
SELECT key,
       body->'primary'  AS primary_slot,
       body->'worker'   AS worker_slot,
       version,
       updated_at
FROM living_state_entities
WHERE key = 'infra:active-session-lock';

-- Step 2a: Clear worker slot and write inline audit sub-section
--   Replace S__N__ with the session number (e.g. S594)
UPDATE living_state_entities
SET body = jsonb_set(
        jsonb_set(
          body,
          '{worker}',
          'null'::jsonb
        ),
        '{worker_clear_audit_sN}',
        json_build_object(
          'cleared_at',     NOW()::text,
          'cleared_by',     'vulcan-direct-psql',
          'cleared_reason', 'Emergency psql clear — gateway down, Level 1+2 unavailable',
          'pre_clear_state', body->'worker'
        )::jsonb
      ),
    version    = version + 1,
    updated_at = NOW(),
    updated_by = 'vulcan-direct-psql'
WHERE key = 'infra:active-session-lock'
RETURNING key, version, updated_at;

-- Step 2b: Clear primary slot (run as a SEPARATE statement)
UPDATE living_state_entities
SET body = jsonb_set(
        jsonb_set(
          body,
          '{primary}',
          'null'::jsonb
        ),
        '{primary_clear_audit_sN}',
        json_build_object(
          'cleared_at',     NOW()::text,
          'cleared_by',     'vulcan-direct-psql',
          'cleared_reason', 'Emergency psql clear — gateway down, Level 1+2 unavailable',
          'pre_clear_state', body->'primary'
        )::jsonb
      ),
    version    = version + 1,
    updated_at = NOW(),
    updated_by = 'vulcan-direct-psql'
WHERE key = 'infra:active-session-lock'
RETURNING key, version, updated_at;

-- Step 3: Verify both slots are null
SELECT key,
       body->'primary' AS primary_slot,
       body->'worker'  AS worker_slot,
       version
FROM living_state_entities
WHERE key = 'infra:active-session-lock';

\q
```

**Post-psql recovery steps:**

1. Restart the gateway handler:
   ```bash
   launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp
   ```
2. Wait 10 seconds, then verify `emergency_psql_recovery_unrecorded` appears in the Event Ledger:
   ```bash
   state_request action=list kind=infra updated_since=<boot_time>
   # Look for event_type=emergency_psql_recovery_unrecorded
   ```
3. Back-fill the audit trail via Level 1 state_request patch (see §B.1 template), using
   `cleared_by=vulcan-direct-psql` and the pre-clear state you recorded in Step 1.

---

## §E SQLite fallback and corruption recovery

**Symptom:** `/health` returns `registry_mode: memory_only`, or logs contain `SQLITE_FALLBACK`
or `SQLITE_MIGRATION_ROLLBACK`.

In memory-only mode the gateway is fully functional but lock state is not crash-persistent —
any gateway restart will lose in-flight session state. Repair promptly.

**Diagnose:**

```bash
ls -la /var/tmp/koskadeux/registry.db
sqlite3 /var/tmp/koskadeux/registry.db "PRAGMA integrity_check;"
sqlite3 /var/tmp/koskadeux/registry.db "SELECT version, name, applied_at FROM schema_migrations ORDER BY version;"
```

**Rebuild from Postgres mirror (idempotent):**

```bash
cd /Users/max/koskadeux-mcp

# If DB is corrupt, rollback the hydration migration first
python3 scripts/migrate_session_registry.py \
  --db /var/tmp/koskadeux/registry.db --rollback 0002

# Re-apply: re-hydrates role_locks + sessions from infra:active-session-lock
python3 scripts/migrate_session_registry.py \
  --db /var/tmp/koskadeux/registry.db --apply

# Restart gateway to pick up the repaired DB
launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp

# Confirm recovery
curl -s http://localhost:8767/health | python3 -m json.tool
# Expect: registry_mode=sqlite
```

If the `/var/tmp/koskadeux/` directory does not exist (first boot or tmpfs wipe):

```bash
mkdir -p /var/tmp/koskadeux
python3 scripts/migrate_session_registry.py \
  --db /var/tmp/koskadeux/registry.db --apply
```

---

## §F iCloud staleness symptom and self-heal

**Symptom** (S596 live recurrence): Worker on laptop reports `parent_session_not_open` on boot
because `~/Library/Mobile Documents/com~apple~CloudDocs/koskadeux-active-session.json` points to
a session closed 8+ hours earlier (S594 while backend was at S596).

**Diagnose:**

```bash
cat ~/Library/Mobile\ Documents/com~apple~CloudDocs/koskadeux-active-session.json \
  | python3 -m json.tool | grep -E 'primary_session_id|lock_version|updated_at'
```

Compare `primary_session_id` against `body.primary.session_id` from
`state_request action=get key=infra:active-session-lock`. If they diverge, the iCloud file is
stale.

**Post-Gate-2 self-heal:** `tools/icloud_sync.py` fires atomically on every lock UPDATE. Trigger
a no-op patch to force a sync:

```bash
state_request action=patch key=infra:active-session-lock \
  body='{"_icloud_sync_force": true}' \
  updated_by=vulcan source_ref=manual-icloud-sync
```

Verify within 5 seconds:

```bash
cat ~/Library/Mobile\ Documents/com~apple~CloudDocs/koskadeux-active-session.json \
  | python3 -m json.tool | grep lock_version
# Expect: lock_version strictly greater than the stale value
```

**Note on propagation lag:** The local CloudDocs write completes in ≤50ms. Cloud-side propagation
to other devices is OS-managed and can take 30+ seconds under network load. A >30s iCloud
propagation delay is NOT a registry bug (Gate 2 RB10). The Worker bootstrap should retry with
a 60s polling window before declaring staleness.

---

## §G Migration runbook

```bash
# Check what migrations are applied
python3 scripts/migrate_session_registry.py \
  --db /var/tmp/koskadeux/registry.db --status

# Apply all pending migrations (also runs automatically on gateway boot)
python3 scripts/migrate_session_registry.py \
  --db /var/tmp/koskadeux/registry.db --apply

# Roll back to a specific version
python3 scripts/migrate_session_registry.py \
  --db /var/tmp/koskadeux/registry.db --rollback 0002

# Direct schema inspection
sqlite3 /var/tmp/koskadeux/registry.db \
  "SELECT version, name, applied_at FROM schema_migrations ORDER BY version;"
```

**Registered migrations:**

| Version | Name | Notes |
|---------|------|-------|
| 0001 | `create_initial_schema` | sessions, role_locks, close_transactions, schema_migrations tables |
| 0002 | `hydrate_from_postgres` | One-shot Postgres→SQLite hydration from `infra:active-session-lock`; idempotent |

**On `SQLITE_MIGRATION_ROLLBACK` in logs:** The migration failed mid-run; DB was preserved at
pre-migration state; gateway entered memory-only mode. Steps:

1. Check sentinel logs for the exception.
2. Fix the root cause (usually a missing Postgres entity or schema mismatch).
3. Re-run `--apply`. It will re-attempt only the failed migration (idempotent).
4. Restart the gateway.

**Schema additions are append-only.** Existing column names and types are frozen for backward
compatibility with Worker bootstrap logic reading the iCloud lock-pointer JSON (Gate 2 Q-B3
resolution).

---

## §H Operator escalation tree

```
Lock intervention needed?
         │
         ▼
§A checks pass?
    no ──► Restart handler/proxy; wait 15s; re-check §A
    yes
         │
         ▼
Is blocker a stale/phantom slot with zero ps evidence?
    no  ──► Do NOT clear without Vulcan-Primary confirmation.
            Surface evidence; wait for authorization.
    yes
         │
         ▼
Primary gateway MCP-reachable?
    yes ──► Level 1: state_request patch (§B.1)
    no
         │
         ▼
Gateway HTTP process alive (gateway_server.py running)?
    yes ──► Level 2: admin endpoint (§C)
    no
         │
         ▼
Level 3: Railway psql (§D) — last resort
```

**Post-recovery checklist** (required after any level):

- [ ] `state_request get infra:active-session-lock` — cleared slots show `null`
- [ ] `session-status:{cleared_id}:role=worker` entity has `body.ended_at` populated
- [ ] iCloud file `lock_version` matches or exceeds entity version (§F)
- [ ] `worker_clear_audit_s{N}` or `primary_clear_audit_s{N}` sub-section written to entity
- [ ] If Level 3 used: `emergency_psql_recovery_unrecorded` event appears in Event Ledger post-boot

**Escalate to Max (Vulcan-Primary) when:**
- Two recovery attempts at the same level have failed
- `force=true` would target a session_id you cannot confirm is dead
- Railway psql connection fails or returns unexpected row counts
- `emergency_psql_recovery_unrecorded` fires but you did not perform a psql session

**Cross-references:**

- Gate 1 AC2 (force-release endpoint design): `specs/BQ-KOSKADEUX-SESSION-REGISTRY-DISK-BACKED-S594.md` §AC2
- Gate 1 AC6 (iCloud auto-sync hook): `specs/BQ-KOSKADEUX-SESSION-REGISTRY-DISK-BACKED-S594.md` §AC6
- Gate 1 AC8 (`emergency_psql_recovery_unrecorded` server-side enforcement): `specs/BQ-KOSKADEUX-SESSION-REGISTRY-DISK-BACKED-S594.md` §AC8
- Gate 2 build spec (this BQ): `specs/bq-koskadeux-session-registry-disk-backed-s594-gate2-build.md` §4.10, §9
- Admin endpoint implementation: `tools/admin_endpoints.py`
- iCloud sync hook: `tools/icloud_sync.py`
- Live-process audit: `tools/process_audit.py`
- SQLite registry + CAS: `tools/registry.py`
- Migration runner: `scripts/migrate_session_registry.py`
