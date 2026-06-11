# Council session gate, gateway deploy, and fold dispatch — operations

Owner: Vulcan/Mars (either instance). Last verified live: 2026-06-11 (S816/S818). Covers the session arming lifecycle post-S812-fix, the gateway deploy/restart procedure, and how to run spec-fold dispatches through author-mode — including the credential mechanics and the known middleware gaps.

## A. Session arming (kd_session_open → kd_session_plan)

- Preferred open: `kd_session_open(instance=...)` with NO session_id. The gateway derives the next number from the durable registry (max+1). Handoff-text parsing and S-UNKNOWN minting are retired (c004f66f).
- Explicit session_id is allowed; if the number is registered to the OTHER instance you get a structured `session_id_collision` error naming the holder. Same-instance re-open of your own number is fine (used after restarts).
- Plan immediately after open, valid first attempt. Rejected plan submissions do NOT consume the boot marker (non-consuming validation, c004f66f) — fix the parameters and resubmit.
- Plan errors are truthful and per-row since a9350f27: "no PLANNING boot marker ... current plan slots: <list>" means your open never registered; "plan slot for X/SNNN is STATE, not PLANNING" names the actual row consulted. Plan resolution is session-id-first; an error naming the PEER's row is a regression — file against BQ-SESSION-GATE-BOOT-STATE-FAULT-S812 lineage.
- Boot states are wiped by a gateway restart. Both instances re-arm after any restart: re-open your OWN session_id, then plan, back-to-back.

## B. Gateway deploy / restart (koskadeux MCP server)

1. Code reviewed BEFORE restart: builder ≠ reviewer; at minimum one instance reads the full production diff plus DS +1 on code changes.
2. Merge to origin/main and verify with `git fetch && git log origin/main` (the pre-push hook emits spurious ref-lock errors — trust the fetch, not the push exit code).
3. Safe point: MP/CC mutex idle (no builds in flight — a restart orphans them), XAI local processes collected, peer instance informed (it will need to re-arm).
4. Restart DETACHED so the kill doesn't sever the issuing call: `shell_request action=background: sleep 3 && launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp`.
5. NEVER touch `com.koskadeux.cloudflared` (load-bearing transport) or `com.koskadeux.gateway` (the :8767 proxy) unless that is explicitly the target.
6. Verify: new pid in `launchctl list | grep com.koskadeux.mcp`, `curl localhost:8765/health` shows the expected version, checkout tip is the deployed SHA. Then re-arm (§A). Note: the :8767 proxy may report a stale version in boot payload service_health — the :8765 health endpoint is authoritative.

## C. Fold dispatch (spec folds between gates)

Sizing first (Design Charter): a fold of ≤2 findings or a wording-level change is DIRECT-AUTHORED by an instance (commit + push + independent reviewer confirm — S777 and S816 b6408252 precedent). Multi-finding folds dispatch to MP via author-mode.

Canonical gate-status vocabulary the middleware recognizes (free-text statuses are NOT recognized):
- `REQUEST_CHANGES` — review demanded changes; gate is authorable.
- `AUTHORING_IN_FLIGHT` — a dispatch holds the lease (bound_dispatch_id + lease_expires_at).
- `AUTHORED_PENDING_REVIEW` — authoring complete; NOT authorable until a review outcome is recorded.
- `APPROVED` / `REJECTED` — terminal for authoring.
Record review outcomes by transitioning the gate status to the canonical word (e.g. XAI verdict REQUEST_CHANGES → gate status REQUEST_CHANGES), preserving round detail in sibling fields.

Author-mode credentials:
- Gate 1 only: dispatch `mode=author` with NO dispatch_id / dispatch_token / target_gate — the gateway auto-signs (passing ANY of the three disables auto-sign and demands a real token; target_gate then defaults to 1).
- Gate ≥2: mint explicitly on Titan-1 — `tools/author_dispatch/signer.auto_sign_for_vulcan(target_gate=N)` (key path in koskadeux-mcp/.env: AUTHOR_DISPATCH_VULCAN_PRIVATE_KEY_PATH). Token TTL is 300s — dispatch immediately. Pass dispatch_id + dispatch_token + target_gate.
- Gate-status writes on a gate that has author-lifecycle fields require `request_dispatch_id` = the PERSISTED bound_dispatch_id (status-only writes). Writes that also SET bound_dispatch_id require request = the INTENDED id — and the persisted check still fires, which deadlocks rotation (§D).

## D. Known middleware gaps (tracked BQ-COUNCIL-MIDDLEWARE-GAPS-S816)

1. Binding rotation deadlock: once a gate has a persisted bound_dispatch_id (even lease-expired), no write can rotate it — the persisted-binding and intended-binding guards are mutually exclusive. WORKAROUND: direct-author the fold (§C sizing) — status-only writes citing the persisted binding still work, so the APPROVED flip is never blocked.
2. Build-mode compliance gate does not recognize gate1 `APPROVED_WITH_MANDATES` as passed, and blocks incident/bug entities entirely ("No Gate 1 data found"). Spec folds route through author-mode instead; genuine incident hotfix builds dispatch via `dispatch_mp_build` WITHOUT bq_code (tested skip path) with tracking maintained manually on the entity and the BQ code in commit messages.
3. `peer_msg_send` is absent from the MCP tool registry (only `peer_msg_ack` is exposed) — bus claims/sends are unreachable from chat instances. Until fixed (BQ-PEER-BUS-SEND-TOOL-GAP-S816): log claims as `decision` events in the Living State ledger and relay urgent peer signals via Max.

## E. Reviewer quirk armor (quick reference; canonical roster in infra:council-comms)

- DS: inline the FULL spec or diff (no filesystem access); demand raw JSON, no fences, first char `{`, explicit schema, ≤3 findings.
- XAI: content-cited only — inline what it must judge; verify every citation; `cwd=/tmp` on deliberation tasks.
- MP: 1200s hard cap — every build/fold prompt mandates commit+push per item.
- Review-mode `verdict_target_branch` persistence currently returns `branch_missing` even when the branch exists — capture verdict text from the task record and persist to state/branch manually.
