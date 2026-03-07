# Session Lifecycle

## What it does

Manages Vulcan session state across conversations. Ensures continuity between sessions, crash recovery, and audit trail.

## Boot sequence

```
1. kd_session_open(session_id="S{N}")
   → Returns: CORE.md + HANDOFF.md + BQ status + service health
   → Registers session in session DB
   → Logs to allAI

2. Work happens
   → kd_recovery_write() after every significant step
   → state_patch() when BQ items change

3. kd_session_close(session_id, summary, handoff_content)
   → Writes HANDOFF.md
   → Clears recovery cache
   → Logs session end to allAI + session DB
```

## Recovery (crash)

```
Max runs: touch /var/tmp/koskadeux/force_recovery
  OR says: "recover"

Vulcan calls: kd_recovery_read()
  → Returns last cached state with file consistency checks
  → Then normal boot
```

## Key files

| Path | Purpose |
|------|--------|
| `/var/tmp/koskadeux/HANDOFF.md` | Session handoff (next session's briefing) |
| `/var/tmp/koskadeux/kd_recovery_cache.json` | Crash recovery cache |
| `/var/tmp/koskadeux/kd_sessions.db` | Session history database |
| `/var/tmp/koskadeux/force_recovery` | Touch to trigger recovery |
| `docs/core/CORE.md` | Agent constitution |

## Recovery cache discipline

- Write after every significant step (build dispatch, gate decision, state change)
- 30 tool calls without a write = STALE warning and blocked tools
- Stale cache > 10 min during active work = process violation

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "BOOT GATE: Session not open" | MCP server restarted mid-session | Re-open with kd_session_open |
| "RECOVERY CACHE STALE" | Too many calls without kd_recovery_write | Write recovery cache |
| HANDOFF.md empty/stale | Session closed incorrectly | Check session DB, re-read from allAI |
| MCP server not responding | Process died | `pkill -f koskadeux_server.py` (launchd restarts) |
| All tools return errors | Checkpoint gate deadlock | See agent-dispatch.md Known bugs — kd_recovery_write not exempt |
