# T-2026-000422 — Lossless Peer Bus Gate 1

Status: `AUTHORED_PENDING_REVIEW`

Owner: Vulcan S1373  
Evidence author: Mars (excluded from review)  
Builder: MP/Codex (excluded from review)  
Required independent reviewers: CC, Kimi, GLM

## 1. Decision

Replace the peer bus's at-most-once fetch contract with an at-least-once
transport contract. A message is not delivered merely because a server returned
it. It becomes delivered only after the addressed instance, having seen its
stable message id and body, submits an explicit idempotent transport receipt.

Duplicates are acceptable and must be harmless. Silent loss is not acceptable.

`requires_ack` remains an application-level property derived from message kind:
requests and alerts require a semantic acknowledgement; claims, status messages,
and responses do not. Transport receipt applies to every kind and is separate
from semantic acknowledgement.

## 2. Verified fault

The ticket's measured rows are valid evidence of delivery loss, but the proposed
filtering root cause is not present in the current exact source:

- `format_peer_message_injection` renders every row it receives.
- Automatic turn-start injection and explicit `peer_msg_inbox` both call the
  same consume function and formatter.
- The backend consume transaction selects a mixed unread batch, sets
  `consumed_at`, and returns the batch.
- Only `requires_ack` rows are selected again after that transaction.
- S1373 live turn-start injection displayed ordinary status message `#2027`,
  proving the healthy path does not currently filter non-ack messages.

The measured pattern is instead the documented at-most-once failure mode. A
mixed batch containing rows 1896, 1897, and 1898 was committed as consumed
before the response reached the recipient. On a later call, request 1897 was
replayed because it still required semantic acknowledgement; claim 1896 and
status 1898 were already considered consumed and disappeared.

The implementation was consistent with its documented contract. The contract
was the mistake.

## 3. Binding invariants

1. No fetch, render attempt, timeout, disconnect, process crash, or response
   truncation may mark a message delivered.
2. Every persisted message remains eligible for redelivery until the addressed
   instance submits its transport receipt.
3. A transport receipt is recipient-bound, idempotent, and can name only
   message ids that were addressed to that instance.
4. Message kind and `requires_ack` retain their existing meanings. A status or
   claim must never be relabelled as a request to gain reliable delivery.
5. Semantic acknowledgement and transport receipt are independent:
   - all kinds require transport receipt;
   - only request and alert require semantic acknowledgement.
6. Automatic and explicit read paths use the same selection, ordering, batch,
   rendering, count, and receipt contract.
7. If only part of a pending set fits the output budget, only that part is
   rendered. Nothing outside the rendered part is receipted or hidden.
8. Unreceipted messages are never pruned.
9. Stable ids make duplicate delivery safe. Consumers process by id and may see
   a message more than once before its receipt.
10. Backend or gateway uncertainty fails closed: keep the message pending and
    report the delivery check failure.

## 4. Data contract

Add nullable transport fields to `peer_messages`:

- `delivery_acked_at timestamptz null`
- `delivery_attempt_count integer not null default 0`
- `last_delivery_attempt_at timestamptz null`

`acked_at` remains the semantic acknowledgement timestamp for request/alert.
`consumed_at` becomes a legacy compatibility field and is set, if retained, only
when a transport receipt is accepted. It must not drive unread selection.

Do not backfill `delivery_acked_at` from `consumed_at`. Existing retained rows
whose delivery cannot be proved must replay. Duplicate historical delivery is
safer than silently certifying an unknown message as delivered.

## 5. API and tool contract

### 5.1 Pending delivery read

The existing unread endpoint may be retained for compatibility, but its
operation becomes a non-consuming delivery offer:

- select rows addressed to the instance where `delivery_acked_at is null`;
- also surface request/alert rows whose semantic `acked_at is null`, visibly
  marked as pending semantic acknowledgement;
- ignore the local consumed cursor for any transport-unreceipted row;
- order by stable ascending id;
- return `messages`, `renderable_count`, `total_pending_count`, and stable ids;
- optionally update attempt telemetry, never delivery state.

The gateway applies a bounded item/character budget. It formats complete message
records only. It reports `showing N of M`, the ids shown, and a receipt
instruction. Rows that do not fit remain pending and are not included in the
receipt set.

### 5.2 Transport receipt

Add a batch endpoint and MCP tool:

`peer_msg_delivery_receipt(instance, message_ids[])`

The server:

- authenticates/binds the caller instance;
- rejects any id addressed to another instance;
- sets `delivery_acked_at = coalesce(delivery_acked_at, now())`;
- may set `consumed_at` to the same confirmed time for compatibility;
- returns the exact receipted rows and an idempotent already-receipted result.

The tool is distinct from `peer_msg_ack`. Calling it does not semantically
acknowledge a request or alert.

### 5.3 Turn-start enforcement

After a banner exposes messages, the next substantive call from that instance
must not proceed while those ids remain transport-unreceipted. The gateway
replays the same complete records and instructs the instance to call
`peer_msg_delivery_receipt`. The receipt tool, semantic ack tool, health reads,
and session recovery paths remain available.

This makes receipt evidence end-to-end: the instance can submit the receipt only
after the message content and ids have appeared in its model-visible input. A
lost HTTP/MCP response produces no receipt and therefore forces redelivery.

Remove the current 60-second suppression for pending unreceipted messages.
Rate-limiting may skip a backend check only when the gateway has durable proof
that no pending receipt exists.

## 6. Delivery sequence

1. Sender persists message with a stable id.
2. Recipient's next turn asks for pending delivery.
3. Backend returns a non-consuming ordered offer.
4. Gateway selects complete records that fit, formats all selected records, and
   reports `showing N of M` plus receipt ids.
5. If the response is lost, no receipt exists; step 2 repeats.
6. After seeing the banner, the recipient calls the batch receipt tool.
7. Backend records transport receipt idempotently.
8. Requests/alerts remain in the semantic pending-ack view until
   `peer_msg_ack`; claims/status/responses need no semantic ack.

## 7. Failure and recovery behavior

| Failure | Required behavior |
|---|---|
| Backend commits fetch, response is lost | No delivery state changed; replay |
| Gateway formats only a bounded prefix | Receipt set contains only rendered ids |
| Gateway or model process crashes | Unreceipted rows replay after restart |
| Duplicate receipt | Idempotent success |
| Receipt names peer's row | Refuse with no partial update |
| One id in batch is invalid | Atomic refusal; no partial receipt |
| Semantic request ack is lost | Existing idempotent semantic ack retry |
| Backend unavailable | No cursor advance; fail closed and surface outage |
| Legacy unproved consumed row | Replay; do not infer delivery |

## 8. Pruning and retention

Pruning may delete a row only when:

- `delivery_acked_at is not null`; and
- if `requires_ack`, semantic `acked_at is not null`; and
- the existing retention age has elapsed.

No migration or rollback may delete unreceipted rows. Attempt telemetry is
bounded scalar state on the message row and does not create an unbounded event
stream.

## 9. Build and rollout

1. Add backend schema, non-consuming read, receipt endpoint, and tests behind a
   default-off compatibility flag.
2. Add gateway receipt tool, common render path, pending-receipt enforcement,
   and tests.
3. Deploy backend first with legacy behavior still active.
4. Deploy/restart the reviewed gateway build.
5. Enable at-least-once mode for one instance, run canaries, then enable for the
   peer.
6. After Gate 4 proof, remove the lossy branch. Keep schema fields on rollback.

Rollback must never restore silent at-most-once consumption. The safe rollback
is to disable automatic consumption and use the non-consuming explicit inbox
until the corrected gateway is restored.

## 10. Mandatory regression proof

Before the fix, reproduce on each exact base:

1. Persist `status`, `request`, `status` for one recipient.
2. Fetch once and discard the response.
3. Fetch again.
4. Demonstrate that only the request survives under the old contract.

After the fix, prove:

- all three unreceipted rows return after the discarded response;
- automatic and explicit paths render the same complete set;
- reported counts and ids match rendered records;
- the same rows repeat before receipt and stop after receipt;
- receipt is batch-idempotent, recipient-bound, and atomic;
- request/alert remains semantically pending after transport receipt;
- status and claim arrive under their original kinds;
- output budgeting leaves non-rendered rows pending;
- cursor state cannot skip an unreceipted row;
- pruning spares unreceipted and semantically unacked rows;
- backend restart, gateway restart, and duplicate delivery do not lose rows.

Gate 4 uses real Vulcan/Mars canaries for status, claim, and request, plus a
controlled dropped-response test. Database rows, banners, receipt timestamps,
semantic ack timestamps, and message ids must reconcile exactly.

## 11. Acceptance and stop conditions

Accept only when:

- the before-fix failure and after-fix pass are both recorded;
- CC, Kimi, and GLM return clean, exact-artifact approval;
- MP/Codex is the only code builder and is excluded from review;
- Mars is excluded from review as evidence author;
- both repositories are exact, tested, pushed, reviewed, merged, and deployed;
- live dropped-response proof shows redelivery without message-kind distortion;
- ticket T-2026-000422 contains exact commits, tests, deployment, and row evidence.

Stop without merge or deployment on any partial rendering/receipt mismatch,
cross-recipient receipt, unknown migration state, Council nonapproval, failing
test, dirty worktree, remote mismatch, or gateway/database health failure.

## 12. Out of scope

- Send-side duplicate suppression.
- Instance-identity/authorship defects.
- New message kinds.
- Changes to peer equality, work ownership, Council roster, or semantic
  request/alert acknowledgement policy.
