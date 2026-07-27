# T-2026-000422 — Lossless Peer Bus Gate 1

Status: `AUTHORED_PENDING_REVIEW_R3`

Owner: Vulcan S1373  
Evidence author: Mars (excluded from review)  
Builder: MP/Codex (excluded from review)  
Required independent reviewers: CC, Kimi, GLM

## 1. Decision

Replace destructive unread consumption with an append-only, recipient-receipted
message log.

For every message committed after cutover:

- the row and body remain durably queryable;
- reading or rendering never advances delivery;
- one complete message is offered with one opaque recipient-bound token;
- only an explicit idempotent receipt advances transport state;
- an unreceipted message is offered again;
- semantic acknowledgement remains separate.

The gateway does not block substantive work while delivery is pending. It
reserves output space for one complete message frame, appends the frame, and
continues replay/rotation until a receipt arrives. This removes both silent loss
and the lockout introduced by the round-2 delivery-only-turn design.

The guarantee begins after a peer-message insert commits. Send-side
deduplication and the known pre-persistence path remain T-2026-000339 / F-07 /
G-07 and are not certified here.

## 2. Verified fault

The ticket's measured rows prove an unsafe boundary, not an intentional
non-ack-kind filter:

- the exact formatter renders every row it receives;
- automatic injection and explicit inbox use the same consuming path;
- the backend commits `consumed_at` before the gateway or model proves receipt;
- only semantically unacknowledged request/alert rows remain selectable;
- S1373 live injection displayed ordinary status message `#2027`.

The historical claim/status disappearance with request replay is consistent with
either a wholly dropped response after the consuming commit or a post-commit
partial-render/truncation event. Existing evidence does not distinguish them.
The before-fix suite must reproduce both separately.

## 3. Guarantee and invariants

1. `peer_messages` is an immutable append-only log under this design. No T-422
   code path deletes a row or changes its body, kind, sender, recipient, or id.
2. Fetch, peek, offer creation, rendering, timeout, disconnect, crash,
   truncation, replay, quarantine, and mode transition never set delivery
   received.
3. An active offer contains exactly one complete message. Its token can receipt
   only that message for the bound recipient.
4. Receipt authority comes only from the active session binding established by
   `kd_session_open`; there is no caller-supplied instance parameter.
5. Every well-formed unreceipted post-cutover row remains eligible for
   deterministic replay/rotation.
6. A partial or missing response without a receipt changes no delivery state.
7. `requires_ack` and message kind retain their present meaning. All kinds
   require transport receipt; only request/alert require semantic ack.
8. Transport pending and semantic pending have separate selection, counts,
   response sections, and state transitions.
9. Automatic injection and explicit inbox call the same non-consuming offer
   implementation.
10. Legacy rows whose receipt cannot be proved stay explicitly
    `legacy_unverified`; they are preserved and queryable, never silently
    certified as delivered.
11. Quarantine preserves content and is never delivery, acknowledgement,
    pruning, or deletion.
12. Backend or gateway uncertainty never advances delivery state.

## 4. Ground-truth snapshot and size boundary

The S1373 authenticated production read, without exposing bodies, found:

- 1,310 retained rows, ids 651 through 2031;
- 2 rows still legacy-unconsumed;
- 2 request/alert rows still semantically unacknowledged;
- maximum retained UTF-8 body size 7,842 bytes.

New sends are rejected before persistence when `body` exceeds 8,192 UTF-8 bytes.
Backend request validation and gateway tool validation use the same named
constant and test 8,192 success / 8,193 refusal.

One offer contains one message. `PEER_OFFER_MAX_BYTES` is 10,240 UTF-8 bytes,
including metadata, framing, and the fixed 43-character token. Before offer
creation the gateway serializes with a 43-character placeholder and requires the
complete frame to fit. The final combined tool response is byte-aware and
limited to 50,000 UTF-8 bytes: the primary tool result is safely reduced first
to reserve the exact serialized offer size. The offer frame is never passed
through middle truncation.

If one valid 8,192-byte body cannot fit the offer cap, the gateway creates no
offer, emits `PEER_OFFER_SIZE_INVARIANT`, and leaves the row pending.

## 5. Durable schema

Add to `peer_messages`:

- `delivery_received_at timestamptz null`
- `delivery_attempt_count integer not null default 0`
- `last_delivery_attempt_at timestamptz null`
- `delivery_quarantined_at timestamptz null`
- `delivery_quarantined_by text null`
- `delivery_quarantine_reason text null`

`acked_at` remains semantic request/alert acknowledgement. `consumed_at` is
legacy-only evidence and is ignored by enforced selection.

Add `peer_message_delivery_offers`:

- `offer_id uuid primary key`, internal and never used as the receipt token;
- `offer_token char(43) not null unique`;
- `to_instance text not null`;
- `message_id bigint not null references peer_messages(id)`;
- `state text not null` constrained to `active`, `received`, `superseded`;
- `created_at`, `receipted_at`, `superseded_at`;
- `render_attempt_count integer not null default 0`;
- `last_render_attempt_at timestamptz null`;
- a partial unique index allowing one active offer per recipient.

The token is exactly 32 cryptographically random bytes encoded as unpadded
base64url: 43 ASCII characters matching `^[A-Za-z0-9_-]{43}$`. It is a
capability-bearing identifier shown only to the addressed instance. The token
column and offer history remain retained with the message log so duplicate
receipts stay idempotent; no token expiry or token tombstone pruning exists in
T-422.

Add `peer_bus_instance_state`:

- `instance` primary key;
- `mode` constrained to `legacy`, `shadow`, `enforced`;
- `cutover_message_id bigint null`;
- `mode_changed_at`, `mode_changed_by`, `mode_change_reason`;
- `consecutive_degraded_checks integer not null default 0`.

`cutover_message_id` is set exactly once, during the first `legacy -> shadow`
transition, to the recipient's current maximum id under the same transaction
lock. It is immutable across rollback and re-enablement.

Add `peer_bus_legacy_manifest`:

- recipient;
- immutable cutover id;
- row count, minimum id, maximum id;
- ordered SHA-256 digest over `(id, body_sha256)` tuples;
- creation time and verified actor/session.

The manifest is evidence and indexing metadata. It never marks legacy rows
received.

No migration backfills `delivery_received_at` from `consumed_at`.

## 6. Identity and receipt classification

The model-facing tool is:

`peer_msg_delivery_receipt(offer_token)`

It has no `instance`, message-id, or override argument.

The gateway resolves the caller from the active registry session and request
context established by `kd_session_open`, then submits the bound recipient to
the service-authenticated backend. The backend locks the offer and verifies
`to_instance`.

Receipt outcomes:

| Input/state | Outcome |
|---|---|
| No resolvable active session | `unbound_session`; benign fail-closed; no security event |
| Token wrong length/alphabet | `malformed_token`; 422; no lookup or state change |
| Well-formed token absent from retained offer log | `unknown_token`; hard refusal and security event |
| Correct token, wrong bound recipient | hard refusal and security event |
| Active token, correct recipient | atomically receipt the one message and offer |
| Received token, correct recipient | idempotent success with the same message id |
| Superseded token, correct recipient | `stale_offer`; no state change; message remains pending |
| Offer/message recipient or quarantine invariant failure | atomic hard refusal; no partial state |

Any tool argument, query parameter, or client header attempting to replace the
active binding is rejected and security-logged. Enforced mode is blocked until
integration tests prove Vulcan cannot receipt Mars's token and vice versa,
including forged argument/header attempts.

## 7. Non-consuming selection and one-message offers

### 7.1 Separate views

The backend reports:

- `live_transport_pending_count`: unquarantined rows above the immutable cutover
  id with `delivery_received_at is null`;
- `legacy_unverified_count`: rows at or below cutover with
  `delivery_received_at is null`;
- `semantic_pending_count`: every request/alert with `acked_at is null`,
  regardless of transport or legacy state;
- current backend-owned mode;
- an existing active offer, or the next live candidate.

Only the chosen candidate id is exposed. Counts are scalars; withheld ids are
not returned. Semantic reminders are a separate section and never enter a
transport offer.

Selection for live candidates is deterministic:

1. high priority before normal;
2. never-before-offered (`last_delivery_attempt_at is null`) before replayed;
3. oldest `last_delivery_attempt_at`;
4. ascending id.

This is a round-robin pending log with priority, not a slot/byte partition. One
valid candidate always fits by the size invariant.

### 7.2 Active-offer replay and rotation

An active offer is replayed for at most three successful gateway render
attempts. On each successful offer fetch, in a telemetry-only transaction:

- increment the offer's `render_attempt_count`;
- increment the message's `delivery_attempt_count`;
- set both last-attempt timestamps.

These writes never set `delivery_received_at`, `consumed_at`, or `acked_at` and
are not part of the receipt transaction.

At the fourth eligible check, the backend atomically supersedes the active offer
without marking delivery and creates a new offer using the selection order.
The prior message returns to the pending rotation. A high-priority message may
preempt a normal active offer at the next check. A new normal message with `Q`
never-before-offered normal messages ahead of it is offered within
`4 * (Q + 1)` successful checks. `Q` is returned as a scalar at insertion/peek
time and the pending-count alerts bound abnormal growth. This is the numeric
starvation rule; the design makes no false four-check promise when a real queue
already exists.

There is no time-based expiry. A delayed superseded token returns `stale_offer`;
the message remains pending and will rotate again.

Concurrent peek/create/rotate/receipt operations lock the instance-state row and
active offer. The receipt either wins and records delivery, or rotation wins and
the old token becomes stale. The partial unique index is the final one-active-
offer guard.

### 7.3 Exact render binding

The gateway:

1. peeks without changing delivery state;
2. serializes the one complete immutable record with a fixed 43-character token
   placeholder;
3. verifies the offer and combined-response byte bounds;
4. requests an offer for that exact bound recipient/message id;
5. receives the exact immutable row plus its 43-character token;
6. asserts id/body/kind/sender/recipient parity with the preflight record;
7. replaces the placeholder and appends the complete framed record after the
   safely reduced primary response.

If a concurrent active offer already exists, the backend returns that exact
offer and the gateway discards its preflight candidate. Automatic and explicit
paths therefore converge on the same offer.

Only the token for the displayed message is returned. The model calls receipt
only after the complete frame is present. A lost or downstream-truncated
response produces no receipt; the exact pending message remains in the log and
replays/rotates. No design claim assumes downstream truncation is impossible.

### 7.4 Non-blocking behavior

Pending or active offers never suppress the substantive tool result and never
block `peer_msg_send`, session lifecycle/recovery, status, health, receipt,
semantic ack, dispatch, or local work. Tool-specific authorization gates remain
unchanged.

If the offer check is unavailable or mode is unknown, the gateway appends
`PEER_BUS_DEGRADED`, allows the substantive call, increments the local degraded
counter when possible, and advances no delivery state.

## 8. Legacy reconciliation without starvation

The 1,310 retained unproved rows are not placed in the automatic live queue and
are not called delivered. At the first shadow transition the backend creates the
immutable per-recipient legacy manifest and verifies every row at or below the
cutover id is queryable.

The current data set requires at most three 500-row read pages. The rollout
operation must finish manifest generation and independent count/digest
verification within ten minutes or stop. Completion means every legacy row is
preserved, indexed, and reconciled to the manifest; it does not mean delivered.

The explicit read-only tool `peer_msg_legacy_page(after_id, limit<=100)` exposes
complete legacy rows without state changes. The optional
`peer_msg_legacy_offer(message_id)` promotes one selected unreceived legacy row
through the same one-message offer/receipt protocol; it cannot run while a live
offer is active and never bulk-certifies rows.

Every turn surfaces only the scalar legacy-unverified count and the manifest
reference, so old data remains discoverable without starving post-cutover
traffic. Only a separately reviewed, Max-authorized disposition may quarantine
legacy rows; no automatic cutoff, receipt, or deletion is allowed.

The two known semantically unacknowledged legacy request/alert rows remain in
`semantic_pending_count` from the first shadow check because semantic selection
does not depend on transport receipt.

## 9. Modes and transitions

The backend-owned per-instance mode is the only behavior switch:

- `legacy`: old consume/injection continues for compatibility, while the new
  tables are inert; message deletion is already disabled.
- `shadow`: old consume/injection continues; the new selector runs read-only and
  writes only comparison metrics. It creates no offers, exposes no tokens,
  accepts no receipt (`mode_not_enforced`), and never changes delivery fields.
- `enforced`: old consuming selection is disabled; the new non-consuming
  offer/receipt protocol is authoritative.

Shadow pass requires, for each recipient, 100 consecutive successful checks over
at least 24 hours, including at least one status, claim, and request canary, with:

- exact candidate/count parity against an independent SQL reference query;
- zero mutation of offer or delivery fields;
- every complete preflight frame at or below 10,240 bytes;
- zero selector error and zero unknown mode.

Transition rules are transactional:

- first `legacy -> shadow`: lock instance state, set immutable cutover id, create
  the legacy manifest;
- `shadow -> enforced`: require the shadow pass artifact and no active offer;
- `enforced -> shadow`: supersede any active offer, requeue its message without
  delivery, preserve cutover id and all receipt state;
- re-enable: reuse the original cutover id; every unreceipted post-cutover row
  accumulated during shadow remains live pending.

A missing/unreadable/unknown mode is degraded non-enforcing and advances no
delivery state.

## 10. Quarantine race and operator recovery

Quarantine is admin-only, requires explicit Max authorization plus actor,
reason, ticket, and recipient, and applies only to unreceipted rows.

The transaction locks instance state, the message, and any active offer:

- if quarantine wins, it supersedes the active offer first, then sets quarantine
  fields; all other pending rows remain eligible;
- if receipt wins first, quarantine returns `already_received` and makes no
  change;
- receipt always rechecks quarantine under the same locks before delivery.

Quarantine excludes the row from automatic offers but keeps the complete
append-only row, token history, manifest membership, and admin queryability.
Requeue clears quarantine fields under an equally audited Max-authorized action.
Neither action changes receipt or semantic ack state.

Because delivery is non-blocking and tokens do not expire, no receipt-specific
operator escape is needed for liveness. Admin offer supersede remains available
for a corrupt/stuck active offer; it requeues without marking delivery.

## 11. Numeric observability

Metrics are per recipient and emit to the Event Ledger plus the existing
SysAdmin alert channel:

| Signal | Warning | Critical |
|---|---:|---:|
| Oldest live pending age | 2 minutes | 10 minutes |
| Live pending count | 20 | 100 |
| Active offer render attempts | 3 | 6 across superseded offers for same message |
| Receipt latency | 5 minutes | 15 minutes |
| Consecutive degraded checks | 2 | 5 |
| Quarantined count | any non-zero | age over 24 hours |
| Legacy manifest mismatch | immediate | immediate rollout stop |

Warnings deduplicate for 15 minutes per instance/signal. Critical alerts remain
open until the metric clears and include oldest message id, count, mode, and
ticket reference, never body or token.

## 12. Retention and pruning

T-422 makes `peer_messages`, delivery offers, and legacy manifests append-only.
The existing peer-message deletion job is disabled; its enforced-mode code path
must prove zero deletes. No T-422 pruning condition exists, so there is no
message/offer retention cycle and no idempotency tombstone loss.

This is deliberate: current volume is small, while the objective is no lost
messages. A future retention/archival policy is a separate Gate-1/Council change
that must prove recoverability before deleting any log row.

Quarantine, rollback, mode transition, semantic ack, and receipt never delete.

## 13. Migration and rollout

Follow `schema-migration.md` exactly:

- run `alembic heads` and require one head;
- merge heads before this revision if multiple exist;
- test forward upgrade and backward downgrade on a fresh database;
- record exact heads and inspect every new constraint/index;
- MP build output must include the migration manifest.

Rollout:

1. backend schema/API/metrics first, default `legacy`, with deletion disabled;
2. gateway supporting all modes, still governed by backend mode;
3. first shadow transition sets immutable cutover/legacy manifest;
4. pass the numeric shadow oracle for one recipient, then the peer;
5. enable one recipient, run Gate 4, then enable the peer;
6. keep legacy manifest/count visible; do not auto-certify legacy rows;
7. remove the old consuming path only in a separately reviewed follow-up.

Before enablement, audit every `consumed_at` reader/writer: backend consume
selection, gateway cursor, explicit inbox, automatic injection,
pruning/reporting, reconciliation/escalation, and tests. The build manifest names
each exact file/function and behavior in all modes.

## 14. Safe rollback

Rollback sets the affected instance to `shadow` transactionally:

1. supersede any active offer and requeue without delivery;
2. preserve immutable cutover, messages, offers, receipts, quarantine, and
   manifest;
3. continue legacy compatibility injection plus read-only shadow comparison;
4. notify both peers and Max and keep T-2026-000422 open;
5. before dispatch/merge/deploy/close, report degraded state and reconcile live
   pending/legacy counts;
6. re-enable only with the original cutover id and a new shadow pass.

Rollback never consumes, receipts, backfills, quarantines, prunes, or deletes.

## 15. Mandatory named proofs

Before fix:

1. whole-response discard after consuming commit hides status/claim;
2. post-commit partial render hides status/claim;
3. semantically unacknowledged request can replay in both cases.

After fix:

1. read/peek/render/lost response changes no delivery state;
2. injected downstream truncation with no receipt leaves the exact message
   pending and replayable;
3. offer token is 43-character base64url, maps to one message/recipient, and no
   hidden id/token is returned;
4. malformed, unknown, unbound-session, wrong-recipient, active, received, and
   superseded receipt branches match section 6;
5. automatic and explicit paths return the same active offer;
6. receipt is atomic/idempotent and does not set semantic ack;
7. status, claim, request, alert, and response retain original kinds;
8. 8,192-byte send/frame passes; 8,193-byte send fails before persistence;
9. combined primary response plus full offer stays within 50,000 UTF-8 bytes
   without offer middle truncation;
10. three replays then rotation; a normal new row with `Q` never-offered normal
    rows ahead appears within `4 * (Q + 1)` successful checks under worst-case
    8,192-byte messages; high priority preempts next check;
11. concurrent peek/create/rotate/receipt yields one active offer and no skipped
    pending row;
12. attempt telemetry writes only counters/timestamps and drives exact warning
    thresholds;
13. substantive tools and `peer_msg_send` continue with an active offer;
14. backend outage/unknown mode allows work, emits degraded state, and advances
    no delivery;
15. legacy manifest reconciles all 1,310 snapshot rows in at most three pages and
    ten minutes; automatic live selection exposes no legacy id;
16. legacy page/offer is explicit, non-consuming until receipt, and never bulk
    certifies;
17. the two known legacy semantic rows remain visible independently of transport;
18. shadow runs 100 checks/24 hours with exact oracle parity and zero new-state
    mutation;
19. enforced/shadow/re-enable preserves immutable cutover and requeues in-flight
    offers;
20. quarantine-vs-receipt race serializes to either received or quarantined,
    never both; requeue is audited;
21. every alert threshold/dedup/clear behavior asserts;
22. peer-message/offer/manifest deletion paths perform zero deletes;
23. forward upgrade/backward downgrade passes with one Alembic head;
24. gateway/backend restart and duplicate receipt lose no persisted row;
25. forged instance arguments/headers cannot change receipt identity.

Gate 4 uses real Vulcan/Mars status, claim, and request canaries plus a controlled
dropped-response test and reconciles exact rows, offers, tokens, counters,
receipt timestamps, semantic acks, modes, and deployed commits.

## 16. Review mandate register

### Round 1 CC `747cbfd9`

| Mandate | Discharge |
|---|---|
| R1-M1 exact rendered subset | One-message offer, exact preflight/parity, sections 3, 7.3 |
| R1-M2 authenticated identity | No instance arg; bound-session receipt, section 6 |
| R1-M3 oversize/HOL | 8,192-byte send bound and one-message frame, section 4 |
| R1-M4 outage lockout | Non-blocking degraded behavior, section 7.4 |
| R1-M5 legacy starvation | Immutable legacy manifest and live-only automatic queue, section 8 |
| R1-M6 semantic/transport mixing | Separate views/counts, sections 3 and 7.1 |
| R1-M7 mixed-mode rollout | Backend modes and transactional canary, sections 9 and 13 |
| R1-M8 poison receipt | Token outcome classification, section 6 |
| R1-M9 unobtainable empty cache | Backend check each turn; no empty cache, section 7 |
| R1-M10 offline recipient | Audited preserved quarantine, section 10 |
| R1-M11 named tests | Section 15 |
| R1-M12 consumed_at audit | Section 13 |
| R1-M13 rollback polling/notice | Section 14 |

GLM R1 `d7eebf51`: `schema-migration.md` single-head/forward/backward rules are
in section 13; post-persistence guarantee boundary and T-2026-000339 separation
are in section 1.

### Round 2 CC `3c593c43`

| Mandate | Discharge |
|---|---|
| R2-M1 slot/byte starvation | One candidate/offer; guaranteed fit, sections 4 and 7 |
| R2-M2 undefined token | Exact 32-byte/43-char token schema, sections 5 and 6 |
| R2-M3 expiry | Expiry removed; attempt-based rotation, section 7.2 |
| R2-M4 unbounded lockout | Delivery is non-blocking, section 7.4 |
| R2-M5 1,310-row drain | Bounded manifest reconciliation, no automatic drain, section 8 |
| R2-M6 peer send blocked | All substantive/send tools continue, section 7.4 |
| R2-M7 shadow contradiction | Dry-run selector plus old compatibility path and numeric oracle, section 9 |
| R2-M8 circular pruning | Append-only/no pruning, section 12 |
| R2-M9 telemetry writer | Exact render-attempt transaction, section 7.2 |
| R2-M10 quarantine race | Locked serialize/supersede rule, section 10 |
| R2-M11 mode transition/cutover | Immutable one-time cutover and in-flight rule, section 9 |
| R2-M12 unbound receipt | Explicit benign fail-closed outcome, section 6 |
| R2-M13 traceability | This register |
| R2-M14 semantic legacy visibility | Ack selection independent of transport, sections 7.1 and 8 |
| R2-M15 alert thresholds | Numeric table/destination, section 11 |
| R2-M16 truncation proof | Injected truncation/no-receipt replay test, section 15.2 |

The round-2 note that four maximum bodies cannot fit is removed by the
one-message offer invariant.

## 17. Acceptance and stop conditions

Accept Gate 1 only when CC, Kimi, and GLM independently read this exact complete
artifact and return `APPROVE` with zero findings, nits, mandates, conditions, or
unknowns. Mars and MP remain excluded.

No build before Gate 1 approval. No merge/deploy until the two-repository build
is exact, tested, pushed, independently Gate-3-approved, migration-safe, and
authorized. Stop on identity override, token/message mismatch, delivery state
changed without receipt, lost/changed row, frame overflow, fairness bound
failure, legacy manifest mismatch, mode/cutover drift, any delete path, Council
nonapproval, failing test, dirty worktree, remote mismatch, or unhealthy
gateway/database.

Ticket T-2026-000422 must contain exact spec/build/review/deploy SHAs and Gate-4
row-level evidence before closure.

## 18. Out of scope

- Send-side duplicate suppression / T-2026-000339.
- New message kinds.
- General work ownership, peer equality, or Council roster.
- General identity/authorship hardening beyond receipt binding.
- Any future deletion, compaction, or archival policy for the append-only log.
