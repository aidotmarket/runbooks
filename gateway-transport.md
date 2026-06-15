---
system_name: Koskadeux Gateway Transport
purpose_sentence: The OAuth-fronted streamable-http gateway (:8767) that proxies both AI instances' MCP tool calls to the upstream Koskadeux tool server (:8765).
owner_agent: mars
escalation_contact: Max (via peer relay through Living State)
lifecycle_ref: §J
authoritative_scope: gateway_server.py transport/session configuration, restart, and transport-layer failure isolation/repair. NOT upstream tool dispatch (koskadeux_server.py); NOT session lifecycle locks (see session-open-protocol.md / session-registry-recovery.md).
linter_version: v1
---

# Koskadeux Gateway Transport Runbook

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

**Repo:** aidotmarket/koskadeux-mcp · **Local path:** `/Users/max/koskadeux-mcp` · **Entry:** `gateway_server.py`
**Public:** `https://mcp.ai.market`, fronted by Cloudflare via the `cloudflared` tunnel `koskadeux` (launchd `com.koskadeux.cloudflared`; MUST-KEEP, do not decommission). A parallel Tailscale Funnel surface exists at `https://koskadeux-10.tail30cd96.ts.net` (also proxies `:8767`) but no DNS record points to it; it is a documented fallback, not the live path for `mcp.ai.market`. See `cloudflare-and-dns.md` (transport source of truth) and `mcp-gateway.md`. · **Local:** `:8767`
**Process mgmt:** launchd `com.koskadeux.gateway` (wrapped by `infisical run`). The upstream tool server is a SEPARATE service: launchd `com.koskadeux.mcp`, `koskadeux_server.py` on `:8765`. Restarting the gateway does NOT restart the upstream.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Two-instance response isolation (no cross-talk) | LIVE | gateway_server.py ctor `stateless_http=True` | tests/unit/test_gateway_concurrency.py + live 2-instance test | 2026-06-01 (S751) |
| Tool-call proxy forward to upstream | LIVE | gateway_server.py ProxyFastMCP.call_tool | unit | 2026-06-01 |
| Namespace prefix normalize (Koskadeux:/koskadeux:) | LIVE | gateway_server.py _normalize_tool_name (S675) | — | 2026-05 |
| Long-call delivery (<= client ceiling) | LIVE (no keepalive forwarding) | gateway httpx read timeout 660s | live 95s probe | 2026-06-01 |
| Long-call heartbeat (>client ceiling) | LIVE | gateway_server.py _await_with_heartbeat + GATEWAY_KEEPALIVE_INTERVAL=15 | tests/unit/test_gateway_heartbeat.py + live 330s call | 2026-06-02 (S751) |
| Upstream auto-restart fallback | LIVE | gateway_server.py _try_auto_restart_upstream | — | — |

## §C. Architecture & Interactions

| Component | Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Gateway | gateway_server.py `mcp = ProxyFastMCP(...)` ctor | none (stateless transport; module-level _remote_tools_cache only) | claude.ai instances (OAuth), upstream :8765 | transport=streamable-http, path "/", stateless_http=True |
| Upstream tool server | koskadeux_server.py `/api/call` | Living State (Railway), registry.db | gateway (httpx), Council agents | keepalive (_run_with_keepalive, send_progress_notification) lives HERE, not the gateway |
| Auth | SimpleOAuthProvider | OAuth client registry | claude.ai connector | both instances share ONE connector/account |

Key fact: both AI instances authenticate via the SAME OAuth connector. Under stateful streamable-http they mapped to ONE shared server session, so concurrent in-session requests shared a response-routing map -> cross-talk (misroute or orphan -> 300s). Stateless gives each request a fresh transport (mcp_session_id=None) -> structurally isolated.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| mars/vulcan | restart gateway | shell_request -> launchctl kickstart | shell | covered |
| mars/vulcan | edit transport config | shell_request -> edit gateway_server.py + restart | shell+git | covered |
| sysadmin | service health | launchctl/lsof | local | partial |

## §E. Operate

```yaml operate
- id: gw-restart
  trigger: transport config change, or gateway unresponsive
  pre_conditions:
    - coordinated quiet window if peers active (restart drops live connections briefly)
    - change (if any) already present on disk in /Users/max/koskadeux-mcp/gateway_server.py
  tool_or_endpoint: launchctl kickstart -k gui/$(id -u)/com.koskadeux.gateway
  argument_sourcing:
    label: com.koskadeux.gateway
  idempotency: safe to repeat; -k kills then relaunches; launchd KeepAlive relaunches on crash
  expected_success:
    shape: fresh gateway pid listening on :8767
    verification: pgrep -f gateway_server.py changes; lsof -nP -iTCP:8767 -sTCP:LISTEN non-empty; curl :8767/ returns 401 (OAuth up)
  expected_failures:
    - signature: kickstart non-zero / no fresh pid
      cause: wrong launchd domain or plist not loaded
  next_step_success: verify a normal tool call returns
  next_step_failure: launchctl stop+start; if still down, §G gw-rollback
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| gw-crosstalk | One instance receives the other's response, or a 300s orphan under concurrent two-instance traffic | stateful shared session (stateless_http missing/false) | grep stateless_http=True gateway_server.py; both instances on same connector | gw-stateless | HIGH (S750) |
| gw-down | All tool calls fail / connection refused | gateway process dead, launchd not relaunching, port unbound | pgrep -f gateway_server.py; lsof :8767 | gw-rollback / gw-restart | HIGH |
| gw-replay | A mid-flight dispatch re-executes on restart | request redelivery on session re-establishment | compare dispatch logs around restart timestamp | BQ-...-REPLAY-ON-RESTART-S751 (open) | MED |
| gw-longstall | A genuinely long call (>~300s) is killed client-side though gateway+upstream still working | no client-facing heartbeat during the await | check call duration vs ceiling; confirm heartbeat present | gw-heartbeat | HIGH (S751) |

## §G. Repair

```yaml repair
- id: gw-stateless
  symptom_ref: gw-crosstalk
  component_ref: Gateway
  root_cause: stateful streamable-http shares one session across both instances (same OAuth connector); concurrent requests not response-isolated
  repair_entry_point: gateway_server.py ProxyFastMCP(...) ctor (after streamable_http_path="/")
  change_pattern: add `stateless_http=True,`
  rollback_procedure: restore prior gateway_server.py (saved backup or `git checkout origin/main -- gateway_server.py`); launchctl kickstart -k gui/$(id -u)/com.koskadeux.gateway
  integrity_check: live two-instance concurrent burst -> each gets own response, zero orphans (S751 evidence)
- id: gw-rollback
  symptom_ref: gw-down
  component_ref: Gateway
  root_cause: bad config / crash loop after a transport change
  repair_entry_point: working-tree gateway_server.py
  change_pattern: restore last-known-good file
  rollback_procedure: cp backup OR git checkout origin/main -- gateway_server.py; then kickstart
  integrity_check: fresh pid + :8767 listening + a normal tool call returns
- id: gw-heartbeat
  symptom_ref: gw-longstall
  component_ref: Gateway
  root_cause: gateway awaited upstream POST silently; no client-facing progress, so calls past the client no-progress ceiling were killed
  repair_entry_point: gateway_server.py ProxyFastMCP._await_with_heartbeat (wraps the upstream POST await in call_tool)
  change_pattern: emit send_progress_notification every GATEWAY_KEEPALIVE_INTERVAL (15s) with related_request_id=ctx.request_id; best-effort try/except; cancel+observe upstream task on client cancel
  rollback_procedure: git checkout origin/main~1 -- gateway_server.py (pre-S751) then kickstart; or revert merge de61df69
  integrity_check: a >300s call through the gateway returns its result (S751: 330s call returned 07:16:37Z)
```

## §H. Evolve

### §H.1 Invariants

- Long-call heartbeats MUST route via related_request_id=ctx.request_id, or stateless sends them to the GET stream not the per-request POST stream (no liveness). Heartbeat sends are best-effort and MUST NOT abort the call.

- The gateway carries NO progress/keepalive notifications; it is a request->response httpx forwarder. Keepalive lives upstream (koskadeux_server.py).
- Both AI instances share one OAuth connector; response isolation MUST be structural (stateless), not session-dependent.
- Gateway restart drops live connections; coordinate a quiet window when peers are active.

### §H.2 BREAKING predicates

- Removing `stateless_http=True` (reintroduces cross-talk).
- Adding shared per-session mutable response state to ProxyFastMCP.

### §H.3 REVIEW predicates

- Forwarding upstream keepalive/progress notifications through the gateway (changes long-call delivery model).
- Changing transport away from streamable-http.

### §H.4 SAFE predicates

- Editing _normalize_tool_name, _remote_tools_cache TTL, retry/backoff counts.

### §H.5 Boundary definitions

#### module

gateway_server.py (the ProxyFastMCP gateway only).

#### public contract

MCP streamable-http endpoint at PUBLIC_URL "/"; forwards tool calls to upstream /api/call.

#### runtime dependency

Upstream koskadeux_server.py on :8765; Infisical-injected MCP_BEARER_TOKEN; launchd.

#### config default

stateless_http=True; streamable_http_path="/"; httpx read timeout 660s.

### §H.6 Adjudication

Transport-layer changes affecting both instances: MP review + live two-instance verification. One-line reversible config = Charter-light (one reviewer + one round + empirical).

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: ac-crosstalk-isolation
    type: behavioral
    refs:
      - BQ-COUNCIL-GATEWAY-CONCURRENCY-RESPONSE-CROSSTALK-S750
    scenario: Two instances on the shared connector fire concurrent tool calls
    expected_answers:
      - kind: each-request-gets-own-response
        tool: any
        argument_keys:
          - none
    weight: 1.0
  - id: ac-no-longcall-regression
    type: behavioral
    refs:
      - S751-95s-probe
    scenario: A ~95s synchronous call returns to its caller without 300s orphan
    expected_answers:
      - kind: response-delivered
        tool: shell_request
        argument_keys:
          - command
    weight: 0.5
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S751.w
last_refresh_commit: de61df69
last_refresh_date: 2026-06-02
owner_agent: mars
refresh_triggers:
  - any change to gateway_server.py transport/session config
  - any gateway transport incident (cross-talk, mass 300s, gateway-down)
scheduled_cadence: on-change
last_harness_pass_rate: n/a
last_harness_date: 2026-06-01
first_staleness_detected_at: n/a
```

## §K. Conformance

```yaml conformance
linter_version: v1
last_lint_run: pending
last_lint_result: pending
trace_matrix_path: n/a
word_count_delta: new
```
