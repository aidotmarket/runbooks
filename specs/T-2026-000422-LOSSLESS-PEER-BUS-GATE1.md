# T-2026-000422 — Lossless Peer Bus Gate 1

Status: `AUTHORED_PENDING_REVIEW_R2`

Owner: Vulcan S1373  
Evidence author: Mars (excluded from review)  
Builder: MP/Codex (excluded from review)  
Required independent reviewers: CC, Kimi, GLM

## 1. Decision and guarantee boundary

Replace the peer bus's at-most-once fetch contract with a durable, recipient-
receipted, at-least-once transport. A persisted message is not delivered because
a server returned it or a gateway attempted to render it. It becomes delivered
only when the addressed instance returns an opaque, server-issued offer token
that was visible alongside the complete offered records.

Duplicates are acceptable and must be harmless. Silent loss is not acceptable.

This guarantee begins after a peer-message row commits successfully. Send-side
deduplication and the known pre-persistence loss path remain separately tracked
by T-2026-000339 / F-07 / G-07 and are not repaired or certified here.

`requires_ack` remains an application-level property derived from message kind:
requests and alerts require a semantic acknowledgement; claims, status messages,
and responses do not. Every kind requires transport receipt. Transport receipt
and semantic acknowledgement are separate state transitions.

## 2. Verified fault and proof still required

The ticket's measured rows are valid evidence of the unsafe delivery contract,
but they do not distinguish which response-boundary failure occurred:

- `format_peer_message_injection` in the exact base renders every row it is
  given.
- Automatic turn-start injection and explicit `peer_msg_inbox` call the same
  consuming backend path and formatter.
- The backend commits `consumed_at` for a mixed batch before the gateway or
  model proves receipt.
- Only `requires_ack` rows remain selectable after that commit.
- S1373 live injection displayed ordinary status message `#2027`, disproving a
  current healthy-path filter that intentionally omits non-ack kinds.

The historical disappearance of claim/status rows while a request replayed is
therefore consistent with the documented at-most-once boundary. It could have
been caused by a dropped response after the consuming commit, or by a gateway
partial-render/truncation event after that commit. The evidence does not prove
which one occurred. The contract is defective under either mechanism.

The before-fix regression must reproduce and record these as separate cases:

1. commit a mixed fetch and discard the entire response;
2. commit a mixed fetch and truncate/partially render the response;
3. prove the old code hides non-ack rows in both cases while a semantically
   unacknowledged request can replay.

## 3. Binding invariants

1. No fetch, offer creation, render attempt, timeout, disconnect, process crash,
   response loss, or response truncation marks a message delivered.
2. Every successfully persisted message remains eligible for redelivery until
   its addressed instance receipts a server-issued offer that contains it.
3. A receipt accepts an opaque offer token, not caller-selected message ids.
4. An offer token is high-entropy, recipient-bound, and names exactly the
   complete records displayed with that token. Hidden ids are never returned.
5. Caller identity comes from the active authenticated session binding. A
   caller-supplied `instance` argument or header is never receipt authority.
6. Message kind and `requires_ack` retain their meanings. A claim or status must
   never be relabelled as a request to gain reliable delivery.
7. Semantic acknowledgement and transport receipt are independent.
8. Automatic and explicit read paths use the same peek, ordering, offer,
   rendering, count, and receipt implementation.
9. A delivery response contains complete records only. Rows outside the exact
   offer remain pending and their ids are not exposed.
10. Unreceipted messages are never pruned or silently dead-lettered.
11. Stable message ids make duplicate delivery safe.
12. Backend or gateway uncertainty never advances delivery state.

## 4. Retained-data facts and bounded message size

The S1373 pre-design production snapshot, obtained through the authenticated
read API without exposing message bodies, contained:

- 1,310 retained rows, ids 651 through 2031;
- 2 rows still legacy-unconsumed;
- 2 request/alert rows still semantically unacknowledged;
- maximum retained UTF-8 body size: 7,842 bytes.

The migration treats all 1,310 retained rows as delivery-unproved. It does not
infer transport delivery from `consumed_at`.

New sends are rejected before persistence when `body` exceeds 8,192 UTF-8 bytes.
The shared validation constant is enforced by backend request validation and
gateway tool validation, with boundary tests at 8,192 and 8,193 bytes.

Every retained body fits that bound. A delivery-only response is capped at
24,000 UTF-8 bytes after full envelope serialization, well below the gateway's
50,000-character safe-response boundary. The renderer must assert the exact
serialized response fits before creating an offer. If one complete record plus
the fixed-size token and envelope cannot fit, offer creation stops, delivery
state remains unchanged, and an operator-visible invariant failure is emitted.
There is no partial-record fallback.

## 5. Durable data contract

Add transport fields to `peer_messages`:

- `delivery_received_at timestamptz null`
- `delivery_attempt_count integer not null default 0`
- `last_delivery_attempt_at timestamptz null`
- `delivery_quarantined_at timestamptz null`
- `delivery_quarantined_by text null`
- `delivery_quarantine_reason text null`

`acked_at` remains the semantic acknowledgement timestamp for request/alert.
`consumed_at` remains a legacy compatibility field. It is never unread state in
enforced mode and is set there only to the accepted transport receipt time.

Add `peer_message_delivery_offers`:

- `offer_id uuid primary key`, generated with cryptographic randomness;
- `to_instance text not null`;
- `created_at`, `expires_at`, `receipted_at`, `superseded_at`;
- `state` constrained to `active`, `received`, `expired`, or `superseded`;
- one active offer per recipient, enforced by a partial unique index.

Add `peer_message_delivery_offer_items`:

- `offer_id` foreign key;
- `message_id` foreign key;
- `ordinal integer not null`;
- primary key `(offer_id, message_id)` and unique `(offer_id, ordinal)`.

Add `peer_bus_instance_state`:

- `instance` primary key;
- `mode` constrained to `legacy`, `shadow`, or `enforced`;
- `cutover_message_id`, `mode_changed_at`, and audited actor/reason.

Offer rows are bounded lifecycle records, not telemetry. Received, expired, and
superseded offers may be pruned only after the underlying message rows satisfy
the retention rule. Attempt telemetry stays scalar on each message.

No migration backfills `delivery_received_at` from `consumed_at`.

## 6. Identity and trust boundary

The MCP receipt tool is:

`peer_msg_delivery_receipt(offer_token)`

It has no `instance` parameter.

The gateway resolves the caller from the active registry session established by
`kd_session_open` and the current request context. It submits that bound
recipient to the backend over the existing service-authenticated internal API.
The backend compares the bound recipient to the offer's `to_instance`.

Any tool argument, query parameter, or client-provided header that attempts to
override the active binding is rejected and security-logged. Enforced mode may
not be enabled until an integration test proves that a Vulcan session cannot
receipt a Mars offer and vice versa, including attempts using forged arguments
and headers. This receipt-specific identity binding is in scope for T-2026-
000422; broader authorship hardening remains separately tracked.

## 7. Read, offer, render, and receipt protocol

### 7.1 Non-consuming peek

The backend returns separate sections:

- `transport_pending`: unquarantined rows where
  `delivery_received_at is null`;
- `semantic_pending`: request/alert rows where `delivery_received_at is not
  null` and `acked_at is null`;
- scalar `transport_pending_count`, `semantic_pending_count`, and mode.

The response exposes candidate transport records only. It never exposes ids for
budget-withheld rows. Semantic rows are not transport candidates and never
appear in an offer.

The backend is checked on every turn. There is no time-to-live suppression and
no local "proof of empty" cache; a sender may insert at any moment.

### 7.2 Separate live and legacy lanes

At enablement, `cutover_message_id` is the current maximum id for that recipient.
Rows at or below it enter the legacy lane; later rows enter the live lane.

An offer contains at most four messages:

- reserve one slot for the oldest live row whenever live work exists;
- fill the remaining slots from the oldest legacy rows;
- if the legacy lane is empty, fill all slots from live rows;
- if the live lane is empty, fill all slots from legacy rows.

Priority is applied within each lane (`high` before `normal`, then ascending
id), without allowing one lane to consume the other's reserved capacity. A new
live row therefore appears in the next successfully created offer even while
the 1,310-row legacy replay is draining.

Semantic reminders have their own response and counts. Transport delivery takes
precedence. Semantically pending rows cannot consume transport slots, receipt
ids, or transport character budget.

### 7.3 Exact offer creation

For automatic and explicit inbox reads, the gateway:

1. peeks candidates without changing delivery state;
2. renders complete candidate records into a delivery-only response buffer,
   using a fixed-width placeholder for the offer token;
3. selects only records whose fully serialized response fits the 24,000-byte
   cap;
4. asks the backend to create an offer for that exact ordered id set;
5. receives the opaque token plus the same immutable rows;
6. replaces the placeholder, asserts byte-for-byte id/order parity and the
   final serialized size, and returns only that delivery response.

The internal offer-create endpoint is not an MCP/model tool. It accepts the
gateway's bound recipient plus selected ids. In one transaction it locks the
recipient state, returns an existing active offer if one exists, or verifies
that every selected row is pending, unquarantined, and addressed to that
recipient before creating the offer and items.

If an active offer exists, both automatic and explicit paths replay that exact
offer and token. Concurrent creates converge on the same active offer.

The response says `showing N of M transport-pending`, displays only the N
offered ids and complete bodies, and instructs the recipient to receipt the
opaque token. The total M is a scalar; withheld ids are not returned.

### 7.4 Delivery-only turn

When a successful check finds an active or newly created offer, the gateway does
not run or mix in the originally requested substantive tool response. It returns
only the bounded delivery offer. After the recipient receipts the token, it
retries its original call.

This removes the current middle-truncation boundary from delivery. The receipt
token is useful only if it appeared in the same model-visible response as every
complete record in its offer.

Session open/plan/recovery, peer status, receipt, semantic ack, and health tools
remain callable while an offer is active.

### 7.5 Idempotent receipt

The backend locks the offer and its items and then:

- active, correct-recipient token: atomically sets every item's
  `delivery_received_at = coalesce(delivery_received_at, now())`, sets legacy
  `consumed_at` to that same accepted time if null, marks the offer received,
  and returns exact ids;
- already received token: idempotent success with the original exact ids;
- expired or superseded token: returns `stale_offer`, changes no delivery
  state, and directs a fresh peek;
- unknown token: hard refusal and security event;
- recipient mismatch: hard refusal and security event.

There is no caller-supplied id batch, so a benign absent/already-received id
cannot poison a receipt. Database corruption or an offer-item recipient
mismatch is a hard atomic refusal with no partial state change.

Calling transport receipt never sets semantic `acked_at`.

## 8. Failure, liveness, and recovery

| Failure | Required behavior |
|---|---|
| Response lost after peek or offer create | Same active offer and token replay |
| Gateway cannot fit a complete record | No offer; invariant alert; no delivery advancement |
| Gateway/model process crash | Active offer replays after restart |
| Duplicate receipt | Idempotent success |
| Forged/other-recipient token | Hard refusal; security event; no state change |
| Expired/superseded token | Benign stale result; fresh peek; no state change |
| Concurrent peek/create/receipt | One active offer; serializable outcome; no skipped row |
| Backend unavailable at turn start | Degraded warning; substantive call may proceed; no delivery state changes |
| Unknown backend mode | Treat as degraded non-enforcing; do not consume or advance |
| Legacy unproved consumed row | Replay in legacy lane |

Backend outage must not create an unbounded operator lockout. When the delivery
check is unavailable, the gateway emits `PEER_BUS_DEGRADED`, preserves all
local/remote state, and allows the substantive call to proceed. Bus operations
that themselves require the unavailable backend fail normally. Existing
tool-specific authorization gates remain unchanged.

If a valid active offer cannot be receipted because of an offer-specific defect,
an admin-only recovery action may supersede the offer and requeue all of its
items. It requires Max authorization, actor/reason/ticket audit, never marks a
message delivered, and causes a fresh offer. This is the operator escape; it is
not a delivery waiver.

## 9. Quarantine, alerts, pruning, and retention

A permanently offline or decommissioned recipient may otherwise create an
immortal active backlog. The response is audited quarantine, not deletion or
false delivery:

- only an admin action with Max authorization, actor, reason, and ticket may
  quarantine rows;
- quarantine preserves row bodies and all receipt state and is reversible;
- quarantined rows are excluded from automatic offers but remain visible in
  admin reporting and can be requeued;
- quarantine never sets `delivery_received_at`, `consumed_at`, or `acked_at`.

Emit per-recipient metrics and alerts for pending count, quarantined count,
oldest pending age, active-offer age, receipt latency, replay count, and
degraded checks.

Pruning may delete a message only when:

- `delivery_received_at is not null`;
- if `requires_ack`, semantic `acked_at is not null`;
- it is not quarantined;
- no retained offer references it; and
- the existing retention age has elapsed.

No migration, quarantine, rollback, or operator escape may delete or certify an
unreceipted message.

## 10. Mixed-mode rollout and migration

Follow `schema-migration.md` exactly:

- verify a single Alembic head before creating the revision;
- merge existing heads first if more than one exists;
- test forward upgrade and backward downgrade on a fresh database;
- record exact pre/post heads and schema inspection.

Rollout order:

1. add schema, non-consuming peek, internal offer/receipt endpoints, per-instance
   mode, metrics, and tests; default both instances to `legacy`;
2. deploy backend first;
3. deploy a gateway that understands all three modes but enforces only when the
   backend returns `enforced` for its bound instance;
4. run `shadow` parity without delivery-state changes;
5. enable `enforced` for one instance, run canaries, then enable the peer;
6. drain the measured legacy lane under the reserved-capacity policy;
7. after Gate 4 proof, remove the lossy branch in a separately reviewed change.

The backend-owned per-instance mode is the sole enforcement flag. A missing,
unreadable, or unknown value means degraded non-enforcing behavior, never a
local guess. This prevents a new gateway from enforcing against an unprepared
backend.

In `legacy` mode only, the old consume endpoint may still write `consumed_at`.
In `shadow` and `enforced`, fetch/peek never writes it. Before enablement, audit
and name every existing `consumed_at` reader/writer, including backend consume
selection, gateway local cursor behavior, pruning/reporting queries, explicit
inbox, automatic injection, and tests. The build manifest must show how each
one behaves in every mode.

## 11. Safe rollback

Rollback never restores silent automatic at-most-once consumption:

1. set the backend-owned instance mode to `shadow`;
2. keep non-consuming peek and all pending rows intact;
3. if the compatible gateway remains, continue non-consuming visibility without
   receipt enforcement;
4. if the gateway itself must roll back, notify both peers and Max, open/retain
   the incident ticket, and require explicit inbox polling at every turn and
   before dispatch, merge, deploy, or session close until the corrected gateway
   returns;
5. record each manual poll and reconcile oldest-pending/count metrics.

Database fields and offer records remain. A rollback does not backfill, consume,
prune, quarantine, or mark delivery.

## 12. Mandatory regression proof

Before the fix, record the two distinct failure mechanisms from section 2 on
each exact base.

After the fix, prove by named tests:

1. discarded whole response replays the same active offer/token;
2. gateway truncation cannot occur because full serialization is preflighted
   and the delivery-only response stays under its cap;
3. only complete displayed records enter the server-issued offer;
4. hidden ids are absent while the total pending count remains correct;
5. automatic and explicit paths return the same active offer;
6. receipt accepts only the bound offer token and is batch-idempotent;
7. forged argument/header, other-recipient token, and unknown token fail closed;
8. expired/superseded tokens converge on a fresh offer without loss;
9. request/alert remains semantically pending after transport receipt;
10. status and claim retain their original kinds;
11. live-lane reservation delivers a new row in the next offer while all 1,310
    retained legacy rows remain pending;
12. semantic reminders cannot consume transport count, ids, slots, or bytes;
13. 8,192-byte send passes, 8,193-byte send fails before persistence, and the
    maximum retained 7,842-byte body renders completely;
14. backend outage and unknown mode allow substantive work with a degraded
    warning and no delivery advancement;
15. one-instance canary enforcement follows only the backend-owned flag;
16. concurrent peek/create/receipt yields one active offer and no skipped row;
17. admin recovery supersedes/requeues without marking delivery;
18. quarantine is authorized, audited, reversible, excluded from pruning, and
    alerts on count/age;
19. every `consumed_at` reader/writer is mode-correct;
20. pruning spares unreceipted, semantically unacknowledged, quarantined, and
    offer-referenced rows;
21. forward upgrade/backward downgrade passes on a fresh database with one
    Alembic head;
22. backend restart, gateway restart, duplicate delivery, and receipt retry
    lose no persisted row.

Gate 4 uses real Vulcan/Mars status, claim, and request canaries plus a controlled
dropped-response test. It reconciles database rows, exact delivery-only
responses, offer/items, receipt timestamps, semantic acknowledgements, mode
transitions, and message ids.

## 13. Acceptance and stop conditions

Accept only when:

- both before-fix mechanisms and all after-fix proofs are recorded;
- CC, Kimi, and GLM return clean, exact-artifact approval with zero mandates;
- MP/Codex is the only code builder and is excluded from review;
- Mars is excluded from review as evidence author;
- both repositories are exact, tested, pushed, reviewed, merged, and deployed;
- schema migration and rollback evidence is complete;
- live dropped-response proof shows redelivery without kind distortion;
- ticket T-2026-000422 contains exact commits, tests, deployment, and row
  evidence.

Stop without merge or deployment on any receipt not bound to the exact rendered
offer, partial record, identity override, oversized-body ambiguity, starvation,
unknown migration state, lossy rollback, Council nonapproval, failing test,
dirty worktree, remote mismatch, or gateway/database health failure.

## 14. Out of scope

- Send-side duplicate suppression and T-2026-000339.
- New message kinds.
- Changes to peer equality, general work ownership, Council roster, or semantic
  request/alert acknowledgement policy.
- General authorship/identity hardening beyond the receipt-specific binding
  required here.
