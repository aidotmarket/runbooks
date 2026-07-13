---
system_name: trust-channel
purpose_sentence: Operate, isolate, repair, and directionally verify the ai.market Trust Channel device and WebSocket control plane.
owner_agent: vulcan
escalation_contact: Max
lifecycle_ref: §J
authoritative_scope: Device registration, Trust Channel session establishment, both WebSocket implementations, connection registry behavior, periodic revocation decisions, and directional production verification in ai-market-backend.
linter_version: 1.0.0
---

# ai.market Trust Channel Control Plane Runbook

## §A. Header

The YAML frontmatter is authoritative. This runbook was source-audited against
`aidotmarket/ai-market-backend` `origin/main` at
`a51770aba9fe372ab3e305b4a3e3ab871b94d857` on 2026-07-13. The mounted API prefix is
`/api/v1`; use the routes below, even where an endpoint docstring omits `/api`.

Security provenance: `T-2026-000245` finding B records that
both periodic Trust Channel revocation helpers fail open when their database or
in-process registry check raises. The remediation record is
`build:bq-trust-websocket-revocation-fail-closed-s1210`, currently `planned` at the
time of this audit.

> **Binding invariant — authorization uncertainty fails closed.** A valid result may
> keep that session connected. A revoked result must close or quarantine that
> connection. An indeterminate database/registry result must close or quarantine
> **only the affected connection**; a separately proven-valid session stays connected.

Current-source warning: `trust_websocket.py:_check_session_validity` and
`trust_websocket_vc.py:_check_session_validity` catch every exception and return
`True`. That is a known live control-plane defect, not acceptable behavior. Do not
mark S1210 or an incident resolved from a happy-path check alone.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Unified RSA or Ed25519/X25519 device registration | SHIPPED | `app/api/v1/endpoints/trust.py:register_device_unified` | `tests/test_trust_dual_auth.py::TestRegisterDualAuth` | 2026-07-13 |
| Owner-scoped device soft revocation | SHIPPED | `app/api/v1/endpoints/trust.py:delete_device` | No focused revocation test found | 2026-07-13 |
| Standard encrypted WebSocket at `/api/v1/trust/stream` | SHIPPED | `app/api/v1/endpoints/trust_websocket.py:trust_channel_websocket` | `tests/test_bq_trust_channel_v2_m1.py` and `tests/test_bq_trust_channel_v2_m3.py` | 2026-07-13 |
| VC-capable WebSocket at `/api/v1/trust/stream/vc` | SHIPPED | `app/api/v1/endpoints/trust_websocket_vc.py:trust_channel_websocket_vc` | `tests/test_bq_trust_channel_v2_m1.py::test_vc_endpoint_gets_heartbeat_and_registry` | 2026-07-13 |
| Per-device in-process connection registration and replacement | SHIPPED | `app/services/trust_channel_service.py:register_connection` | `tests/test_bq_trust_channel_v2_m1.py::test_same_device_session_replacement` | 2026-07-13 |
| Periodic valid/revoked decision every 50 counted inbound frames | PARTIAL | `app/api/v1/endpoints/trust_websocket.py:_check_session_validity + app/api/v1/endpoints/trust_websocket_vc.py:_check_session_validity` | No focused valid/revoked outcome tests found; planned by S1210 | 2026-07-13 |
| Fail-closed handling of an indeterminate DB/registry revocation result | BROKEN | `app/api/v1/endpoints/trust_websocket.py:_check_session_validity + app/api/v1/endpoints/trust_websocket_vc.py:_check_session_validity` | Planned by `build:bq-trust-websocket-revocation-fail-closed-s1210` | 2026-07-13 |
| Legacy `/api/v1/trust/ws` migration response | SHIPPED | `app/api/v1/endpoints/trust.py:trust_websocket_legacy_upgrade_endpoint` | `tests/test_bq_trust_channel_v2_m1.py::test_legacy_trust_ws_websocket_returns_migration_message` | 2026-07-13 |

`PARTIAL` is deliberate: the database and registry predicates exist, but the cadence
is message-driven, not time-driven. Each loop increments its counter for every inbound
frame, then handles control frames before the modulo check. If frame 50 is a
`ping`, `pong`, `ack`, or `subscription_update`, that iteration skips the revocation
check and the next opportunity is frame 100. An idle socket receives no periodic
revocation query. `TrustSession.expires_at` is also not consulted by either helper.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Device API | `app/api/v1/endpoints/trust.py:register_device_unified` | PostgreSQL `devices` | JWT/API-key auth, KMS | `POST /api/v1/trust/register`; active Ed25519 registrations return existing platform keys, active RSA duplicates return 409, inactive owner devices are reactivated with new keys. |
| Standard WebSocket | `app/api/v1/endpoints/trust_websocket.py:trust_channel_websocket` | connection-local crypto state, PostgreSQL `trust_sessions` | TrustChannelService, shared registry, outbound writer | `WSS /api/v1/trust/stream`; optional v2 negotiation, then hello/challenge/response/established and encrypted data. |
| VC WebSocket | `app/api/v1/endpoints/trust_websocket_vc.py:trust_channel_websocket_vc` | connection-local crypto/VC state, PostgreSQL `trust_sessions` | TrustChannelVCService, shared registry, outbound writer | `WSS /api/v1/trust/stream/vc`; optional VC capability request, then the same device/session handshake with VC or legacy message wrapping. VC-wrapped response processing persists `channel_type="vc"`; the plain-response branch currently inherits the service default `"stream"`. |
| Revocation decision | `app/api/v1/endpoints/trust_websocket.py:_check_session_validity`; `app/api/v1/endpoints/trust_websocket_vc.py:_check_session_validity` | PostgreSQL `devices` and `trust_sessions`, process registry | both WebSocket data loops | Checks active device, active session, then registry membership. Both current exception branches fail open; S1210 owns parity repair. |
| Session service | `app/services/trust_channel_service.py:TrustChannelService` | PostgreSQL `trust_sessions` | KMS, `devices` | Rejects missing/inactive devices at hello; creates a one-hour active session after signature/key verification; stores only the AES key hash. |
| Connection registry | `app/services/trust_channel_service.py:trust_connection_registry` | process memory keyed by external `device_id` | both WebSockets, trust event delivery | One current record per device per backend process. A new same-device connection tears down the previous record with close code 1012. It is not a cross-process durable registry. |
| Teardown path | `app/services/trust_channel_service.py:teardown_connection_record` | registry plus PostgreSQL `trust_sessions` | WebSocket, background tasks | Removes only the matching record, cancels its tasks, best-effort deactivates its session, and closes its socket. |

### Route and identity contract

| Operation | Current route | Authentication or proof |
|---|---|---|
| Register device | `POST /api/v1/trust/register` | JWT or accepted API key; explicit `key_type` plus matching key fields |
| Legacy RSA registration | `POST /api/v1/trust/register/legacy` | JWT or accepted API key |
| Mint short-lived trust token | `POST /api/v1/trust/token` | JWT or accepted API key; active owned device |
| List/get/revoke device | `GET /api/v1/trust/devices`, `GET` or `DELETE /api/v1/trust/devices/{device_id}` | active-user JWT dependency |
| Device heartbeat | `POST /api/v1/trust/devices/{device_id}/heartbeat` | JWT or accepted API key; active owned device |
| Standard session | `WSS /api/v1/trust/stream` | registered active device plus cryptographic hello/challenge/response proof |
| VC-capable session | `WSS /api/v1/trust/stream/vc` | registered active device plus cryptographic handshake; optional VC negotiation |
| Deprecated socket | `GET`, `POST`, or `WSS /api/v1/trust/ws` | returns 410/migration instruction or closes after the migration frame |

The current WebSocket handlers do **not** read the token minted by
`POST /api/v1/trust/token`; do not invent a token query parameter or diagnose a
handshake as token-authenticated. The active device record and cryptographic handshake
are the implemented WebSocket authorization path.

### Revocation outcome contract

| Outcome | Authoritative observation | Required connection behavior | Current source |
|---|---|---|---|
| `valid` | `Device.is_active is True`, `TrustSession.is_active is True`, and this device is present in the process registry | Continue this connection only; do not reconnect or disturb any other record. | Implemented. |
| `revoked` | Device missing/inactive, session missing/inactive, or registry says this device is no longer current | Send `SESSION_REVOKED` where possible, remove the matching registry record, deactivate its session, close that socket with policy violation, and stop processing its frame. | Implemented when the helper returns `False`. |
| `indeterminate` | A DB query or registry lookup raises, times out, or cannot authoritatively answer | Close or quarantine the affected record before another action can run. Do not sweep the registry or restart proven-valid connections. Reauthorize only through a fresh full handshake after an authoritative valid check. | **Not implemented:** both helpers currently return `True` on exception. S1210 owns the repair. |

“Quarantine” means the connection cannot execute control-plane actions or receive
protected delivery while its authorization is unknown. There is no current quarantine
state in `TrustConnectionRecord`; until one exists, targeted teardown is the
source-supported fail-closed primitive.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan | inspect source, run focused tests, prepare reviewed repair | local shell and git in `ai-market-backend` | repository read/write on a dedicated branch | COMPLETE |
| sysadmin | inspect production deploy, logs, and read-only session/device state | Railway CLI plus `psql` through `DATABASE_PUBLIC_URL` | Railway project and production DB read | COMPLETE |
| sysadmin | revoke a dedicated probe device | `DELETE /api/v1/trust/devices/{device_id}` with synthetic owner credential | owner-scoped synthetic account | PARTIAL — no operator route can close one in-memory record; S1210 must close or quarantine in code |
| mp | independently review the fail-closed diff and directional evidence | Council review with pinned base/head | repository read-only | COMPLETE |
| max | authorize production probe mutation or emergency connection-wide restart | human approval | production incident authority | COMPLETE |

No current operator endpoint lists or closes one in-memory registry record. Do not claim
targeted production quarantine through an invented admin route. If source repair is not
yet deployed, that capability is a gap owned by S1210.

## §E. Operate

```yaml operate
- id: E-01
  trigger: A new AIM Data or vectorAIz installation must register and establish a Trust Channel session.
  pre_conditions:
    - The caller has a JWT or accepted API key for the owning user.
    - The device has generated its own RSA or Ed25519/X25519 private keys and keeps them local.
    - The client uses the mounted /api/v1 routes and WSS in production.
  tool_or_endpoint: POST /api/v1/trust/register, then WSS /api/v1/trust/stream or /api/v1/trust/stream/vc
  argument_sourcing:
    device_id: hardware fingerprint from the client installation
    key_type: explicit rsa or ed25519 selected by the client implementation
    public_keys: generated by the device; never copied from another registration
    vectoraiz_version: installed client version
    os_type: installed client operating system
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Registration response followed by hello, challenge, response, and established frames with a new trust session id.
    verification: Confirm the devices row and trust_sessions row are active and the backend logs establishment for the same correlation and device ids. Record the observed channel_type; the VC endpoint plain-response branch currently persists the stream default.
  expected_failures:
    - signature: Device ID already registered to another user
      cause: device identity collision or wrong authenticated owner
    - signature: AUTH_FAILED or Device is inactive or revoked
      cause: missing/inactive device or failed cryptographic proof
  next_step_success: Record the session id and correlation id without recording private keys or the session key.
  next_step_failure: Isolate with F-01; do not bypass device ownership or handshake validation.
- id: E-02
  trigger: A specific owned device is compromised, retired, or must lose Trust Channel authorization.
  pre_conditions:
    - The exact external device_id and owning user are confirmed.
    - The operator is using the owner-scoped synthetic or customer-approved credential.
    - Any incident evidence is captured before mutation.
  tool_or_endpoint: DELETE /api/v1/trust/devices/{device_id}
  argument_sourcing:
    device_id: exact target from the devices inventory and incident record
    authorization: owning user's active JWT; never a different customer's credential
  idempotency: IDEMPOTENT
  expected_success:
    shape: HTTP 204; target devices.is_active becomes false and trust_score becomes 0.0.
    verification: Read the target devices row, then drive the existing socket to its next actual revocation-check opportunity and observe SESSION_REVOKED plus close; verify a separate valid control socket after the target closes.
  expected_failures:
    - signature: HTTP 404 Device not found
      cause: wrong device_id or wrong authenticated owner
    - signature: target socket remains usable after a check opportunity
      cause: indeterminate check failed open, cadence boundary was skipped by a control frame, or the socket is on another process registry
  next_step_success: Confirm only the target session is inactive and the valid control can still complete an encrypted request.
  next_step_failure: Preserve revocation, follow F-02 or F-03, and escalate under S1210; never reactivate merely to clear the symptom.
- id: E-03
  trigger: An S1210 candidate is deployed and needs directional Gate-4 verification before the fail-closed claim is accepted.
  pre_conditions:
    - Deployment SHA is recorded and contains the reviewed S1210 repair plus focused tests for both WebSocket paths.
    - Two dedicated synthetic devices A and B are registered to an approved probe account.
    - A is the failure target and B is the proven-valid control; their device, session, connection, and correlation ids are recorded separately.
    - Targeted indeterminate fault injection is available in an equivalently wired live environment; there is no public production fault-injection endpoint in current source.
  tool_or_endpoint: WSS /api/v1/trust/stream and /api/v1/trust/stream/vc plus owner-scoped revoke and targeted live-environment fault injection
  argument_sourcing:
    deployment_sha: Railway deployment matched to the reviewed git SHA
    target_A: dedicated synthetic device and session selected for revoked or indeterminate outcome
    control_B: distinct synthetic device and session proven valid immediately before and after A's decision
    evidence_window: one timestamped log and database observation window for the run
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: unique probe run id bound to deployment SHA and A/B session ids
  expected_success:
    shape: For both WebSocket implementations, revoked A closes; indeterminate A closes or is unable to process another action; valid B remains connected and completes an encrypted request after A is isolated.
    verification: Correlate deploy SHA, A/B ids, helper outcome, A close/quarantine evidence, B post-event success, matching registry/session state, and zero unrelated disconnects. Redact credentials and payloads.
  expected_failures:
    - signature: A remains authorized after an exception
      cause: old fail-open code is deployed or the repaired branch did not reach this endpoint
    - signature: B disconnects with A
      cause: process-wide isolation, shared-record teardown, or non-targeted fault injection
    - signature: no targeted indeterminate injection exists
      cause: current source has no safe public seam; production-only proof would be fabricated or excessively broad
  next_step_success: Attach directional evidence to build:bq-trust-websocket-revocation-fail-closed-s1210 and proceed through unanimous security review.
  next_step_failure: Keep S1210 open, isolate with F-03 or F-05, and repair with G-03 or G-05.
- id: E-04
  trigger: An operator needs a read-only snapshot of one device and its Trust Channel sessions during triage.
  pre_conditions:
    - Railway project access is available.
    - DATABASE_PUBLIC_URL is sourced from the Postgres service without echoing it.
    - The query is constrained to one exact device_id.
  tool_or_endpoint: psql read-only SELECT on devices joined to trust_sessions
  argument_sourcing:
    device_id: exact external device id from the incident or probe record
    database_url: DATABASE_PUBLIC_URL from the Railway Postgres service
  idempotency: IDEMPOTENT
  expected_success:
    shape: Device active state plus session id, active state, channel_type, timestamps, and teardown_reason for only the target device.
    verification: Match rows to the recorded socket session id and correlation-time window; do not infer in-memory registry membership from SQL.
  expected_failures:
    - signature: zero rows
      cause: wrong environment, wrong device_id, or no persisted registration
    - signature: active DB row but no live socket
      cause: process registry is ephemeral and is not represented by the DB row alone
  next_step_success: Classify the observation as valid, revoked, or still indeterminate using §C.
  next_step_failure: Use logs and the exact deployment SHA; do not convert missing evidence into a valid result.
```

For E-04, the source-grounded read shape is:

```sql
SELECT d.device_id,
       d.is_active AS device_active,
       s.id AS session_id,
       s.is_active AS session_active,
       s.channel_type,
       s.started_at,
       s.expires_at,
       s.last_heartbeat,
       s.teardown_reason
FROM devices d
LEFT JOIN trust_sessions s ON s.device_id = d.id
WHERE d.device_id = :'device_id'
ORDER BY s.started_at DESC;
```

This query cannot prove registry membership because the registry is process memory.
Use logs from the same deployment and the observed socket to complete that part of the
decision.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Registration succeeds but hello returns `AUTH_FAILED`, `Device not found`, or inactive/revoked | Wrong environment/device id, owner revoked it, or cryptographic keys do not match the stored registration | Read the one target device row; compare client route, key type, and public-key fingerprint without exposing private material; inspect the correlated handshake log | §G-01 | CONFIRMED |
| F-02 | A proven-revoked device remains usable on an existing socket | No non-control frame landed on the exact 50-frame boundary, the socket is idle, DB state was read on a different environment, or validity was indeterminate and failed open | Confirm target DB state and deployed SHA; count inbound frames and whether the boundary frame was handled as control; find `Revocation check failed` or `Session validity check failed` for the same device/time | §G-02 | CONFIRMED |
| F-03 | Log contains `Revocation check failed` or `Session validity check failed`, yet the affected connection continues | Current exception handler returns `True` in either WebSocket implementation | Pin the running SHA and inspect both `_check_session_validity` helpers; reproduce with a targeted exception while a separate valid control remains active | §G-03 | CONFIRMED |
| F-04 | An older connection closes with 1012 `New session initiated` when the same device reconnects | Expected single-record replacement in the in-process registry | Compare device id and connection ids; confirm the newer record is current and the old session teardown reason is `session_replaced` | §G-04 | CONFIRMED |
| F-05 | Valid control B disconnects when target A is revoked or made indeterminate | Broad DB outage, backend restart, registry-wide drain, shared identifiers, or non-targeted fault injection | Prove A and B have distinct device/session/connection ids; inspect close reasons and deployment restart events; repeat only in a safe environment with a target-scoped fault | §G-05 | HYPOTHESIZED |
| F-06 | Client receives HTTP 410 or a `migration_required` frame from `/api/v1/trust/ws` | Client uses the deprecated alias | Confirm the requested path in client telemetry and the migration frame's endpoint field | §G-06 | CONFIRMED |

Isolation rules:

- Freeze the exact target identifiers before mutation: external `device_id`, database
  device UUID, session UUID, connection id where logged, channel type, correlation id,
  deployment SHA, and timestamps.
- Never turn a DB/registry exception into “probably valid.” That is `indeterminate`.
- Never use a backend restart as proof of target-scoped fail-closed behavior. A restart
  drains or drops unrelated connections and therefore fails the valid-control half of
  the invariant.
- If immediate containment is more important than preserving valid connections and no
  targeted repair is deployed, a Max-approved backend restart can terminate all sockets
  as an emergency last resort. Record the blast radius and reconnect/reprove valid
  controls; it is incident containment, not S1210 acceptance evidence.

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Device API
  root_cause: The client is addressing a missing/inactive device or presenting keys that do not match the owner-bound registration.
  repair_entry_point: app/api/v1/endpoints/trust.py:register_device_unified
  change_pattern: For the legitimate owner only, re-register the inactive device with a fresh device-generated keypair and explicit key_type; otherwise correct the client environment or device_id. Never copy another device's keys or reactivate a compromised identity.
  rollback_procedure: Revoke the newly registered device through DELETE /api/v1/trust/devices/{device_id}; retain incident evidence.
  integrity_check: Complete a fresh full handshake, confirm a new active session for the correct device, and verify no other owner's device row changed.
- id: G-02
  symptom_ref: F-02
  component_ref: Revocation decision
  root_cause: Revocation is checked only on a non-control inbound frame whose global message counter is exactly divisible by 50; current exception handling can also preserve authorization.
  repair_entry_point: app/api/v1/endpoints/trust_websocket.py:trust_channel_websocket and app/api/v1/endpoints/trust_websocket_vc.py:trust_channel_websocket_vc
  change_pattern: Keep the target device revoked, capture cadence/error evidence, and route the fail-open portion to G-03. Do not claim immediate revocation from the DELETE response alone. A future cadence redesign is separate from S1210 and requires review for both endpoints.
  rollback_procedure: No authorization rollback is permitted during containment. If the device was revoked in error, require owner confirmation and a fresh full re-registration after the incident is closed.
  integrity_check: At an actual check opportunity, only the target receives SESSION_REVOKED and closes; a distinct valid control completes a post-event encrypted request.
- id: G-03
  symptom_ref: F-03
  component_ref: Revocation decision
  root_cause: Both validity helpers catch DB or registry exceptions and return True, explicitly failing open.
  repair_entry_point: app/api/v1/endpoints/trust_websocket.py:_check_session_validity and app/api/v1/endpoints/trust_websocket_vc.py:_check_session_validity
  change_pattern: Implement build:bq-trust-websocket-revocation-fail-closed-s1210 so valid, revoked, and indeterminate are distinguishable and indeterminate cannot authorize another action. Tear down or quarantine only the matching connection. Add focused outcome tests to both endpoints and preserve valid-control behavior.
  rollback_procedure: Do not restore fail-open behavior. If a repair causes false-positive closes, disable only the defective candidate deployment under security-incident approval, preserve target revocation by another approved containment, and issue a corrected fail-closed build.
  integrity_check: Unit tests cover valid, revoked, and exception/indeterminate outcomes on both helpers; live directional proof shows target A closed or quarantined and proven-valid B still connected after A's event.
- id: G-04
  symptom_ref: F-04
  component_ref: Connection registry
  root_cause: The registry intentionally permits one current connection record per external device id and replaces the prior record.
  repair_entry_point: app/services/trust_channel_service.py:register_connection
  change_pattern: Treat 1012 replacement as expected when the newer connection is authorized. If replacement was unauthorized, revoke the device and follow G-02/G-03; do not keep both records alive.
  rollback_procedure: Close the unauthorized newer socket and require a fresh full handshake from the legitimate device after key rotation or re-registration.
  integrity_check: Registry lookup returns only the intended connection id; the stale session is inactive with teardown_reason session_replaced.
- id: G-05
  symptom_ref: F-05
  component_ref: Teardown path
  root_cause: Isolation acted on the process, registry, or shared fault domain rather than the matching connection record.
  repair_entry_point: app/services/trust_channel_service.py:teardown_connection_record
  change_pattern: Bind teardown to the exact TrustConnectionRecord and preserve the stale-record guard in unregister_connection. Make fault injection target A only; re-establish and reprove B before repeating directional verification.
  rollback_procedure: Remove the broad fault or drain, restore the last reviewed deployment, and allow valid devices to reconnect through full handshake; do not reconnect revoked A.
  integrity_check: A and B have distinct ids; A alone is removed/deactivated; B sends and receives an encrypted post-event frame with no replacement or restart.
- id: G-06
  symptom_ref: F-06
  component_ref: Standard WebSocket
  root_cause: The client still addresses the deprecated /api/v1/trust/ws alias.
  repair_entry_point: app/api/v1/endpoints/trust.py:trust_websocket_legacy_upgrade_endpoint
  change_pattern: Configure the client to use /api/v1/trust/stream, or /api/v1/trust/stream/vc when VC capability is required, then perform a full handshake.
  rollback_procedure: Revert only the client endpoint configuration if the selected modern endpoint is wrong; never re-enable the deprecated server alias as an operational fix.
  integrity_check: The client receives established on the selected modern route and no 410 or migration_required frame.
```

`G-03` cites both `T-2026-000245` finding B and
`build:bq-trust-websocket-revocation-fail-closed-s1210`. The ticket is the verified
finding register; the build entity is the narrow P0 remediation scope. Findings C–I,
cryptography redesign, registration redesign, and data-plane work are outside S1210.

## §H. Evolve

### §H.1 Invariants

- Authorization uncertainty fails closed.
- `valid` is positive proof, not absence of a revocation signal.
- `indeterminate` closes or quarantines only the affected connection; a separately
  proven-valid session stays connected.
- Both `/stream` and `/stream/vc` must implement and test the same outcome semantics.
- A quarantined connection cannot execute an action or receive protected delivery.
- Reauthorization after revoked or indeterminate requires a fresh authoritative device
  check and full cryptographic handshake; never flip an in-memory boolean to resume.
- Device, session, connection, and correlation identifiers must remain distinct in logs
  and evidence. Never log private keys, raw session keys, bearer tokens, or decrypted
  customer payloads.
- Registry presence is process-local evidence, not durable cross-process truth.

### §H.2 BREAKING predicates

- Any change that lets a DB/registry exception continue authorization.
- Any change that treats a missing device/session/registry record as valid.
- Any change that closes all connections to isolate one indeterminate connection.
- Removing the owner binding or cryptographic proof from registration/handshake.
- Reusing `/api/v1/trust/ws` as an active data path.

### §H.3 REVIEW predicates

- Changing revocation cadence from the current 50-frame, message-driven behavior.
- Adding durable or cross-process connection-registry state.
- Introducing an explicit quarantine state or new operator endpoint.
- Changing close codes, error frames, session expiry enforcement, or reconnect policy.
- Changing either WebSocket implementation without parity tests for the other.

Security changes require unanimous Council review with builder excluded and directional
evidence bound to the reviewed deployment SHA.

### §H.4 SAFE predicates

- Documentation corrections that preserve mounted route names and runtime semantics.
- Additional redacted correlation fields that do not expose credentials or payloads.
- Focused test naming or fixture refactors that leave all three outcome assertions intact.

### §H.5 Boundary definitions

#### module

The module boundary is the Trust Channel REST device API, both Trust Channel WebSocket
endpoint modules, `trust_channel_service.py`, and their `devices`/`trust_sessions`
models. Fulfillment/data-plane business logic is outside this runbook.

#### public contract

The public contract is the mounted `/api/v1/trust/*` REST/WSS route set, owner/device
binding, handshake frame sequence, error/close behavior, and valid/revoked/indeterminate
authorization semantics.

#### runtime dependency

Runtime dependencies are Railway networking, PostgreSQL, KMS, the process-local
connection registry, the outbound writer/event bus, and the registered client keys.

#### config default

Relevant defaults are `REVOCATION_CHECK_INTERVAL = 50`, a one-hour newly created
session expiry, the heartbeat interval/timeout constants, and full-handshake reconnect.
The current revocation helpers do not enforce `expires_at`.

### §H.6 Adjudication

Classify at the highest-risk predicate touched. Any authorization-result, isolation,
quarantine, cadence, registry, or reconnect change is at least REVIEW; fail-open or
cross-connection effects are BREAKING until corrected and directionally proven.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A legitimate new device needs the correct registration and session path.
    expected_answers:
      - kind: tool_call
        tool: POST /api/v1/trust/register then WSS /api/v1/trust/stream
        argument_keys: [device_id, key_type, public_keys, vectoraiz_version, os_type]
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: One compromised owned probe device must be revoked without disturbing another session.
    expected_answers:
      - kind: tool_call
        tool: DELETE /api/v1/trust/devices/{device_id}
        argument_keys: [device_id, authorization]
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Gate 4 needs proof that an indeterminate result fails closed in the right direction.
    expected_answers:
      - kind: human_action
        verb: inject
        object: target-scoped indeterminate revocation result for A
        target: both WebSocket paths while valid B completes a post-event encrypted request
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-02]
    scenario: A revoked socket remains connected after several ping and pong frames.
    expected_answers:
      - kind: human_action
        verb: verify
        object: exact 50-frame boundary and control-frame continue behavior
        target: the affected endpoint loop plus correlated DB and error logs
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-03]
    scenario: The log reports a revocation-check database error and the socket continues.
    expected_answers:
      - kind: classification
        label: indeterminate and unauthorized to continue
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-05]
    scenario: Target A closes during a fault test, but valid control B disconnects too.
    expected_answers:
      - kind: human_action
        verb: stop
        object: broad fault or registry-wide teardown
        target: re-establish B and repeat with distinct ids and a target-scoped fault
    weight: 0.08333333333333333
  - id: I-07
    type: repair
    refs: [G-03]
    scenario: Both validity helpers currently return true when their checks raise.
    expected_answers:
      - kind: human_action
        verb: implement
        object: S1210 fail-closed outcome handling and focused parity tests
        target: both _check_session_validity helpers
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-04]
    scenario: An old socket closes with 1012 immediately after the same device reconnects successfully.
    expected_answers:
      - kind: human_action
        verb: confirm
        object: expected single-record connection replacement
        target: newer connection id and old session_replaced teardown reason
    weight: 0.08333333333333333
  - id: I-09
    type: evolve
    refs: [§H]
    scenario: A proposal changes exceptions back to continue authorization for availability.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: A proposal adds a target-scoped quarantine state to connection records.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-11
    type: ambiguous
    refs: [E-04, F-03]
    scenario: The device and session rows are active, but the registry lookup raised.
    expected_answers:
      - kind: classification
        label: indeterminate, fail closed for this connection
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-03, F-05, G-05]
    scenario: A production restart closes revoked A and valid B at the same time.
    expected_answers:
      - kind: classification
        label: containment only, not directional S1210 acceptance evidence
    weight: 0.08333333333333333
```

Pass threshold: weighted score at least 0.80. All 12 scenarios have equal weight;
no §I.1 weight justification is required.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1210
last_refresh_commit: 630b2fff0f5d04ed453ed8141237b8fc9e28a51d
last_refresh_date: 2026-07-13T19:58:06Z
owner_agent: vulcan
refresh_triggers:
  - build:bq-trust-websocket-revocation-fail-closed-s1210 changes status or lands
  - either Trust Channel WebSocket validity helper or cadence changes
  - device or session registration contract changes
  - a Trust Channel authorization or isolation incident occurs
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-13T19:58:06Z
first_staleness_detected_at: null
```

Refresh log:

- S1210 (2026-07-13): first authoring. Audited backend `origin/main` at `a51770ab`;
  recorded the current fail-open exception branches, the exact mounted routes and
  50-frame/control-frame cadence, and the directional S1210 acceptance gate.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1210 / 2026-07-13T19:58:06Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
