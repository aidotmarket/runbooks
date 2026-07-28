# T-2026-000422 — Lossless Peer Bus Gate 1

Status: `AUTHORED_PENDING_REVIEW_R6`

Owner: Vulcan S1373  
Evidence author: Mars (excluded from review)  
Builder: MP/Codex (excluded from review)  
Required independent reviewers: CC, Kimi, GLM

## 1. Decision and guarantee

Replace destructive unread consumption with an append-only, recipient-receipted
message log.

For every peer-message insert that commits after cutover:

- the immutable row remains durably queryable;
- reads, frames, crashes, truncation, retries, and mode changes never mark it
  delivered;
- before first presentation, a stable 256-bit token is bound to that one
  message and recipient;
- only an explicit idempotent receipt advances transport state;
- an unreceipted row stays pending and receives further complete delivery
  opportunities;
- requests/alerts still require a separate semantic acknowledgement.

Duplicate presentation is expected and harmless. Consumers key behavior by
stable message id. A duplicate frame or receipt never repeats a privileged
effect.

Receipt is a mandatory protocol action, but a missing receipt does not lock the
operator out of health, recovery, peer communication, or ordinary local work.
The gateway periodically gives a complete delivery-only turn and blocks only
privileged state-changing effects after bounded non-receipt. If the recipient
never receipts, the message remains durably pending forever and no delivery
claim is made; convergence necessarily requires recipient cooperation.

The guarantee begins after insert commit. Send-side deduplication and the known
pre-persistence path remain T-2026-000339 / F-07 / G-07.

## 2. Verified fault

The ticket proves an unsafe boundary, not an intentional non-ack-kind filter:

- the exact formatter renders every row it receives;
- automatic injection and explicit inbox use the same consuming path;
- the backend commits `consumed_at` before recipient receipt;
- only semantically unacknowledged request/alert rows remain selectable;
- S1373 live injection displayed ordinary status message `#2027`.

The historical claim/status disappearance with request replay is consistent with
either a wholly dropped response after commit or post-commit partial rendering.
Existing evidence does not distinguish them. The before-fix suite reproduces
both separately.

## 3. Binding invariants

1. `peer_messages` is immutable and append-only. No T-422 path deletes a row or
   changes body, kind, sender, recipient, ref, or id.
2. Every successfully committed post-cutover row satisfies database-enforced
   size/member constraints and enters either live pending or an explicit
   critical parked state. No row is silently excluded.
3. Fetch, selection, frame creation, presentation, timeout, disconnect, crash,
   truncation, retry, quarantine, parking, and mode transition never set
   `delivery_received_at`.
4. One token maps to exactly one immutable message and recipient.
5. Receipt authority comes only from the active `kd_session_open` session
   binding. There is no caller-supplied instance or message id.
6. Missing/partial responses without a receipt change no delivery state.
7. All kinds require transport receipt; only request/alert require semantic ack.
8. Transport, semantic, parked, quarantined, and legacy-unverified views and
   counts are separate.
9. Automatic scheduling and explicit inbox use the same selector and frame.
10. Legacy receipt uncertainty remains visible and queryable, never certified.
11. Quarantine/parking preserves the row and is not receipt, ack, or deletion.
12. Backend/gateway uncertainty never advances delivery state.
13. Duplicate frames and receipts are idempotent and harmless.

## 4. Exact persistence and frame bounds

The S1373 authenticated production snapshot, without exposing bodies, found
1,310 retained rows across the non-contiguous id range 651–2031, with 71 absent
ids. The retained-row count, not the inclusive numeric span, is authoritative.
It also found 2 legacy-unconsumed rows, 2 semantically unacknowledged
request/alert rows, and a maximum body of 7,842 UTF-8 bytes. Those rows are
legacy and remain accessible through the legacy view. Manifests iterate only
existing retained rows in ascending id order.

`priority` is exactly the closed enum `high|normal` at the gateway, backend
model, database, selector, and state table. No third value is accepted or
silently skipped.

Add `delivery_protocol_version smallint not null default 0` to
`peer_messages`. Existing and pre-cutover rows remain version 0. The shared
send/cutover lock and a database trigger derive the value from the recipient
mode: a send that commits after cutover must be version 1, and callers cannot
override it. `legacy`/`shadow` assigns 0; `enforced`/`safe_readonly` assigns 1;
unknown/missing mode rejects the insert. Conditional database CHECK constraints
apply only to version 1, so they validate safely against the existing
7,842-byte legacy row while every post-cutover commit is still
database-enforced.

Version-1 sends enforce the following at gateway, backend model, trigger, and
conditional database CHECK:

- `body`: at most 6,000 UTF-8 bytes;
- `ref_entity`: null or at most 256 UTF-8 bytes;
- sender/recipient/kind: existing fixed enums; priority: exactly
  `high|normal`;
- message id: signed 64-bit positive integer.

`created_at` is a server-generated, non-null `timestamptz` instant. The database
enforces non-null storage and supplies the default; it does not claim to enforce
a text encoding. The gateway serializer alone renders that stored instant as
canonical UTC RFC3339.

The delivery frame is length-prefixed plain UTF-8, not an escaped inner JSON
document. Its decoded-text worst-case budget is:

| Component | Maximum bytes |
|---|---:|
| Body | 6,000 |
| Ref entity | 256 |
| Token | 43 |
| Id/from/to/kind/priority/ack/timestamp values | 160 |
| Fixed labels, lengths, delimiters, receipt instruction | 541 |
| Total `PEER_FRAME_MAX_BYTES` | 7,000 |

The outer MCP JSON worst case is also tested: every body/ref byte chosen from
JSON's six-byte escape class still serializes below the existing 50,000-byte
transport cap. A delivery opportunity returns only this frame, so no primary
tool result is reduced, mixed, or corrupted.

The gateway serializes with a 43-character placeholder before token creation and
requires both decoded frame `<= 7,000` and outer response `< 50,000`. The build
contains an exhaustive maximum-field fixture including control characters.

The 7,000-byte frame limit applies to version-1 live delivery. Legacy rows are
never fed to the automatic live frame path. An explicit legacy offer uses the
same field serializer and stable-token receipt protocol but a separately named
`PEER_LEGACY_FRAME_MAX_BYTES=9,000` bound. It preflights both that decoded bound
and the 50,000-byte outer bound. A larger legacy row returns
`legacy_frame_unsupported` without parking or mutation and remains queryable in
complete, bounded admin pages. The post-cutover lossless guarantee does not
retroactively certify or transform legacy rows.

If a committed version-1 row violates the supposedly impossible frame
invariant, the backend atomically sets
`delivery_parked_at/reason=frame_invariant`, raises a critical alert containing
id but no body, excludes it from head-of-line selection, and advances to the
next row. Parking never marks delivery.
Requeue is accepted only after the current serializer dry-runs the same
immutable row successfully against both bounds; otherwise it remains parked
without creating another alert. If immutable data is corrupt, a Max-authorized
operator may commit a distinct replacement message referencing
the parked id and then quarantine the original. The original is preserved and
never falsely receipted.

## 5. Durable schema

Add to `peer_messages`:

- `delivery_protocol_version smallint not null default 0`
- `delivery_received_at timestamptz null`
- `delivery_attempt_count integer not null default 0`
- `last_delivery_attempt_at timestamptz null`
- `delivery_quarantined_at/by/reason`
- `delivery_parked_at/reason`

`acked_at` remains semantic ack. On accepted transport receipt,
`consumed_at = coalesce(consumed_at, delivery_received_at)` is written solely for
legacy compatibility; enforced selection ignores it.

Add `peer_message_delivery_offers`, at most one row per message and exactly one
for every message that has reached token creation:

- `offer_id uuid primary key`
- `offer_token char(43) not null unique`
- `message_id bigint not null unique references peer_messages(id)`
- `to_instance text not null`
- `state` constrained to `pending`, `active`, `received`, `quarantined`,
  `parked`
- `created_at`, `first_offered_at`, `last_offered_at`, `received_at`
- `offer_count integer not null default 0`
- partial unique index: at most one `active` row per recipient.

The token is exactly 32 cryptographically random bytes as unpadded base64url:
43 ASCII characters matching `^[A-Za-z0-9_-]{43}$`. It never expires or changes.
Rotation updates the same one-per-message row; it does not create offer history.
Offer storage is therefore bounded by message count, not elapsed checks.

Add `peer_bus_instance_state`:

- `instance` primary key;
- `mode`: `legacy`, `shadow`, `enforced`, `safe_readonly`;
- `cutover_message_id bigint null`;
- `mode_changed_at/by/reason`;
- `calls_since_delivery_opportunity integer not null default 0` constrained to
  `0..2`;
- `consecutive_offer_conflicts integer not null default 0`;
- `next_offer_attempt_at timestamptz null`;
- `last_priority_served` nullable `high|normal`.

`cutover_message_id` is null throughout shadow. It is set once at the atomic
cutover and immutable thereafter.

Add `peer_bus_legacy_manifest` with recipient, cutover id, count, min/max id,
ordered digest, creation time, actor/session.

Manifest digest is reproducible without a new body-hash column. Null and empty
bodies are distinct:

1. if body is null, use tag `N` and hash the zero-length byte string; otherwise
   use tag `V` and UTF-8 encode body exactly as stored with no normalization;
2. compute lowercase hex `sha256(body_bytes)`;
3. for ascending id, append ASCII
   `<decimal_id>:<N-or-V>:<64-hex-body-digest>\n`;
4. manifest digest is lowercase hex SHA-256 of that concatenation.

No migration infers delivery from `consumed_at`.

## 6. Identity and exhaustive receipt outcomes

Model-facing tool:

`peer_msg_delivery_receipt(offer_token)`

It has no instance, message-id, mode, or override argument. The gateway resolves
the active registry session and sends that bound recipient over the
service-authenticated internal API.

| Condition | Result |
|---|---|
| Backend unreachable | gateway `peer_bus_unavailable`; no backend state change |
| Mode `legacy` or `shadow` | `mode_not_enforced`; no state change |
| Mode unknown or missing | `mode_unknown`; degraded hard refusal, no state change |
| No active session binding | `unbound_session`; benign fail-closed |
| Bad length/alphabet | `malformed_token`; 422, no lookup |
| Well-formed absent token | `unknown_token`; hard refusal + security event |
| Wrong bound recipient | hard refusal + security event |
| Token row `quarantined` | `quarantined_message`; no delivery |
| Token row `parked` | `parked_message`; no delivery |
| Token row `pending` or `active`, correct recipient, mode `enforced`/`safe_readonly` | atomic receipt |
| Token row `received`, correct recipient | idempotent success, same message id |
| Offer/message recipient mismatch or corrupt state | atomic hard refusal |

Receipt locks instance state, offer, and message; rechecks quarantine/parking;
sets message `delivery_received_at`, compatibility `consumed_at`, offer
`state=received/received_at`; never sets semantic `acked_at`.

Forged arguments, query parameters, or headers cannot replace the active
binding. Cross-recipient integration tests are a cutover prerequisite.

## 7. Per-turn check, scheduler, and delivery opportunities

### 7.1 Every-turn truth check

Every tool turn performs a backend peer-bus check before substantive dispatch.
There is no TTL suppression, proof-of-empty cache, or local unread cursor.
Backend-unavailable behavior is section 11; it never advances delivery.

The check returns scalar live/legacy/semantic/quarantined/parked counts, mode,
and the next candidate only. Hidden live ids are not exposed.

### 7.2 Bounded delivery cadence

The cadence counter has one exact owner and unit. It saturates at two. An
ordinary eligible invocation whose substantive primary result is returned sets
`calls_since_delivery_opportunity =
min(2, calls_since_delivery_opportunity + 1)` after that result is finalized;
success and tool-level error results both count. Exempt tools, every-turn
checks, receipt, privileged-gate checks, backend failures, and displaced calls
neither increment nor reset it. Any successfully emitted complete frame,
scheduled or explicit-inbox, resets it to zero. Receipt does not reset it. With
pending live messages, a value of two makes the next ordinary eligible call a
due delivery opportunity. An explicit inbox attempted during offer backoff
returns `offer_backoff` without changing the counter; after the bound it may
emit and reset normally.

For an ordinary eligible tool call with pending live messages:

1. calls 1–2 execute normally and return their untouched result;
2. call 3 is a delivery opportunity: the substantive tool is not executed and
   the gateway returns one complete delivery-only frame;
3. the caller receipts the token, then retries its original tool;
4. the three-call cadence repeats while pending remains.

Thus at most one in three ordinary calls is displaced, and no substantive result
is truncated. Receipt, semantic ack, peer send, peer status, session
open/plan/recovery, health, and explicit inbox tools are never displaced.

An explicit inbox call is itself an immediate delivery opportunity.

An offered token becomes overdue exactly when
`now >= first_offered_at + 60 minutes` and it is still unreceipted. Privileged
state-changing tools (dispatch/build authorizations, merge, deploy, production
mutation, and session close) require all overdue tokens for that recipient to
be receipted first. Before 60 minutes cadence continues but privileged effects
are not frozen. At 60 minutes they return the next complete frame instead of
executing and a critical incident opens. After receipt they are retried.
A Max-authorized, ticketed, time-bounded suspension may allow the effect without
marking any message delivered; frames and alerts continue.

Every frame states: receipt is the recipient's mandatory next protocol action.
If the recipient never receipts, ordinary work remains possible, privileged
effects stop after the bound, and the durable log continues cycling messages.

### 7.3 Fair selection

At each delivery opportunity:

- if both priorities are pending, alternate high and normal using
  `last_priority_served`;
- if only one exists, serve it;
- within a priority, choose never-offered first, then oldest
  `last_delivery_attempt_at`, then ascending id.

After the complete frame is issued, increment the message and stable offer
counts/timestamps and move the previously active row back to `pending`; the new
row becomes `active`. The token remains valid when pending, because it may have
been seen before rotation.

With delivery opportunities every third eligible call:

- with one priority lane, a new row with `Q` same-lane never-offered rows ahead
  is framed within `3 * (Q + 1)` eligible calls;
- with both lanes continuously nonempty, it is framed within
  `6 * (Q + 1)` eligible calls;
- no high-priority stream can consume two consecutive delivery opportunities
  while normal is pending.

These are conditional, testable bounds based on the scalar `Q` captured at
selection while the backend is reachable and offer creation does not conflict.
The exact conflict backoff and fifth-conflict safe-readonly bound in section 7.4
applies instead when that concurrency precondition fails. Privileged gating can
accelerate delivery but never weaken bounds.

An explicit legacy offer is allowed only when no live row is pending. It uses
the same stable token/counters and is displaced immediately by any newly live
row at the next opportunity.

### 7.4 Exact offer creation and concurrency

The gateway preflights one immutable candidate with the token placeholder. The
backend locks instance state and message, creates the one-per-message token row
if absent, and atomically selects it active.

If concurrency returns a different active row, the gateway discards the first
buffer, reserializes and revalidates the returned row/token against both bounds,
then returns it. If parity or size fails, it parks that row and performs one
fresh peek. On a second conflict the gateway records
`offer_create_conflict`, returns the original substantive call's untouched
result, and applies the saturating increment rule, which leaves a due counter
at two.

Conflict state is per recipient. The first through fourth consecutive
second-conflict events set `next_offer_attempt_at` to a cryptographically
random delay in, respectively, 50–100 ms, 100–200 ms, 200–400 ms, and
400–800 ms. Calls before that instant return their untouched substantive result
and leave the due counter at two. A successful offer creation resets the
conflict count and backoff timestamp; returning a substantive result, receipt,
elapsed wall time, and ordinary mode changes do not. “Consecutive” means no
successful offer creation between conflicts. Before the fifth conflict, a
successful offer creation resets both fields. The fifth conflict opens a
critical incident, latches the conflict state, and transitions that recipient
to `safe_readonly`; after latching, only ticketed recovery after the root cause
is fixed may reset it.
Explicit inbox/receipt/recovery remain available. The gateway never consumes a
call without either its primary result or a complete frame.

Peek/create/frame never increments delivery receipt state. Lost or truncated
frames without receipt simply leave the token pending for a later opportunity.

## 8. Atomic cutover and legacy preservation

Shadow qualification does not establish cutover and does not create a live
post-cutover backlog. It runs the new selector/serializer in dry-run against a
read snapshot while legacy delivery continues. The known at-most-once exposure
therefore remains until cutover, is explicitly accepted only for a maximum
30-minute qualification window, and T-2026-000422 remains open. Deletion is
already disabled, so even a shadow delivery failure preserves the row for the
legacy manifest.

Shadow pass per recipient is 100 consecutive checks completed within one
authorized 30-minute window, including status/claim/request canaries, with
exact independent-query parity, zero new-state mutation, zero selector/frame
errors, and all frame bounds met. The harness deliberately drives at least four
checks per minute. The 30-minute budget is cumulative for one rollout attempt:
expiry below 100 or any failed check aborts the attempt and forbids restart.
Another window requires a fresh ticketed Max authorization and resets the
rollout attempt, not the audit history. Total accepted legacy exposure is
reported across attempts.

All sends and cutover use the same recipient advisory lock:

`peer_bus_cutover:<recipient>`

Manifest item rows and their per-row canonical hashes are prepared and
independently reconciled outside the send lock under a repeatable-read snapshot.
The cutover transaction then acquires the advisory lock with a five-second
timeout, waits for earlier sends, captures the maximum committed id, adds and
verifies only the snapshot tail, computes count/min/max/ordered digest from the
prepared items, sets the cutover id, switches directly to `enforced`, and
releases. Lock hold has a hard five-second limit; timeout or overrun rolls back
the transaction and sends receive a retryable `cutover_busy` after at most five
seconds. A concurrent send either commits wholly before the watermark and is
manifested legacy, or acquires the lock afterward and is live. There is no
in-flight sequence-id straggler.

The measured 1,310-row snapshot requires three 500-row internal pages.
Precomputation may take up to ten minutes without blocking sends. Final locked
tail reconciliation must complete inside five seconds. Any mismatch stops
cutover.

Legacy rows remain `legacy_unverified`, visible by scalar count and manifest.
`peer_msg_legacy_page(after_id, limit<=100)` is read-only.
`peer_msg_legacy_offer(message_id)` uses the normal stable-token protocol only
when no live row is pending. No bulk receipt or automatic certification exists.
Semantic pending includes every unacked request/alert regardless of legacy or
transport state.

Manifest membership and `legacy_unverified_total` are immutable provenance:
even an individually receipted legacy row remains in both because its historical
pre-cutover delivery state is unknowable. Separate scalar subcounts report
`legacy_never_offered`, `legacy_offered_unreceipted`, and
`legacy_individually_receipted`. A valid explicit receipt moves only between
those subcounts and excludes that row from future legacy offer selection; it
does not remove or rewrite the manifest and does not certify historical
delivery.

Legacy paging also applies a 40,000-byte decoded-output budget and returns only
complete records plus a continuation id. A legacy offer preflights the actual
record against the 9,000-byte decoded legacy frame and 50,000-byte outer caps;
an exceptional row that cannot fit returns `legacy_frame_unsupported` with no
state change and remains fully queryable by paged/admin storage access.

## 9. Modes and rollback-safe behavior

- `legacy`: old consume path; new protocol inert; deletion disabled.
- `shadow`: old consume path plus bounded dry-run comparator; no token/receipt
  mutation and `cutover_message_id` remains null.
- `enforced`: non-consuming scheduled frames and receipt are authoritative; old
  consume path is disabled.
- `safe_readonly`: rollback mode; old consuming injection remains disabled;
  automatic scheduled frames are disabled, but explicit non-consuming inbox and
  receipt remain available.

Unknown/missing mode is degraded non-enforcing and never consumes.

Production schema downgrade is prohibited after any non-null cutover id. The
backward migration is tested only on a fresh never-enforced database before
release. Production rollback is a mode transition to `safe_readonly`, never an
Alembic downgrade.

`enforced -> safe_readonly` keeps stable offer tokens and all message/receipt
state. There is no return to `consumed_at`-based injection, so already-received
post-cutover history is not mass-replayed. Duplicate presentation remains
harmless in all modes.

## 10. Quarantine, parking, and recovery

Quarantine is Max-authorized/admin-only and applies only to unreceipted rows.
It locks instance, message, and offer:

- quarantine wins: set offer `quarantined`, message quarantine fields;
- receipt wins: quarantine returns `already_received`;
- receipt always rechecks quarantine.

Parking is automatic only for a violated version-1 frame invariant, emits one
immediate critical incident, and advances scheduler selection. It is never
delivery. Repair/requeue for parked or quarantined rows requires audited actor,
reason, ticket, and Max authorization. Parked requeue first dry-runs the
immutable row and returns it to `pending` only if it now fits. A failed dry-run
leaves it parked without another incident. Replacement-plus-quarantine is the
terminal remedy for irreparable immutable corruption.

## 11. Degraded-state authority and observability

Backend-reachable metrics emit to Event Ledger and SysAdmin:

| Signal | Warning | Critical |
|---|---:|---:|
| Oldest live pending age | 15 minutes | 60 minutes |
| Live pending count | 20 | 100 |
| Receipt latency after first frame | 15 minutes | 60 minutes |
| Quarantined/parked count | none; any non-zero emits informational | any row over 24 hours |
| Manifest mismatch | immediate | rollout stop |

Warnings deduplicate 15 minutes. The quarantined/parked informational event
deduplicates separately for 15 minutes and is not a warning. Critical events
remain open until cleared.
Offer count remains a metric without an alert threshold; repeated presentation
is required protocol behavior. Routine first frames and scheduler rotation do
not warn.

Backend outage uses a different authority: the local gateway writes every
failure transactionally to `registry.db.peer_bus_degraded_events`, which is
available when the backend is not. The authoritative consecutive count is
local. The fifth consecutive failure sets a durable local critical flag exposed
by `peer_status`, session open/plan/recovery, and a dedicated out-of-band
terminal diagnostic. Primary tool payloads and their byte accounting are never
changed by a bus diagnostic.
On recovery the gateway sends the exact local event range/count to Event Ledger,
verifies persistence, then marks it reconciled and resets the consecutive count.
No backend column attempts to count its own outage.

Alerts include instance, mode, count/age, oldest id, and ticket, never body or
token.

## 12. Retention and bounded storage

`peer_messages` and legacy manifests are retained indefinitely under T-422.
Existing peer-message deletion is disabled and tested for zero deletes.

Delivery-offer storage has a unique one-row-per-message bound. Scheduler
rotation updates counters/state on that row and never creates another token or
history row. Thus storage grows only with persisted messages, not turns.

A future archive/deletion policy is a separate Council-approved change proving
recoverability. Quarantine, parking, receipt, semantic ack, mode transition, and
rollback never delete.

## 13. Migration and rollout

Follow `schema-migration.md`:

- require one Alembic head; merge heads first if needed;
- test upgrade and downgrade on a fresh never-enforced database;
- test the forward migration against a production-shape fixture containing
  version-0 bodies above 6,000 bytes and refs above 256 bytes, proving
  conditional constraints accept legacy while the trigger and checks reject
  equivalent version-1 inserts;
- record exact heads and every constraint/index;
- prohibit production downgrade once cutover is non-null;
- MP build output includes migration and consumed-at reader/writer manifests.

Rollout:

1. backend schema/API with deletion disabled, mode `legacy`;
2. compatible gateway;
3. bounded shadow qualification while cutover remains null;
4. advisory-lock atomic cutover/manifest and one-recipient canary;
5. Gate-4 dropped-response proof, then peer cutover;
6. keep legacy manifest/count visible;
7. old consuming code removal only in a separate reviewed change.

Audit every `consumed_at` reader/writer: consume selection, gateway cursor,
automatic/explicit inbox, pruning/reporting, reconciliation/escalation, rollback,
and tests.

## 14. Safe rollback

Rollback is `enforced -> safe_readonly`:

1. preserve all messages, stable tokens, receipts, quarantine/parking, cutover,
   and manifest;
2. disable automatic scheduling and old destructive consumption;
3. retain explicit non-consuming inbox and receipt;
4. notify both peers and Max; keep ticket open;
5. require explicit inbox before dispatch/merge/deploy/close;
6. reconcile live/legacy/semantic/quarantine/parked counts;
7. re-enable only after repaired gateway review and a fresh bounded dry-run.

No production schema downgrade, consume fallback, receipt fabrication, backfill,
quarantine, pruning, or deletion is a rollback action.

## 15. Mandatory proofs

Before fix:

1. discarded consuming response hides status/claim;
2. post-commit partial rendering hides status/claim;
3. semantic request can replay in both.

After fix:

1. every committed post-cutover row is live or explicitly parked; none silently
   excluded;
2. exact 6,000/256 maximum version-1 fields fit 7,000 decoded bytes and
   worst-case outer JSON under 50,000; 6,001-byte body and 257-byte ref reject
   before commit while oversized version-0 fixtures migrate safely;
3. frame-invariant failure parks/alerts/skips without receipt or head-of-line
   blocking;
4. every-turn/no-cache check is enforced;
5. ordinary calls follow two untouched results then one complete delivery-only
   opportunity; exempt tools are never displaced; explicit inbox emission
   resets the same saturating counter;
6. privileged effects remain available before the exact 60-minute overdue
   boundary, then block; Max suspension is audited and never receipts;
7. stable 43-char token maps to one message/recipient and persists through
   scheduler rotation;
8. all receipt outcomes in section 6, including modes, outage, quarantine,
   parking, unbound, forged recipient, and idempotency;
9. semantic ack remains independent;
10. alternating priority prevents sustained-high starvation; bounds
    `3*(Q+1)` / `6*(Q+1)` hold; legacy yields to live;
11. concurrency returning a different row triggers full reserialization; a
    second conflict returns the untouched primary result, preserves the due
    counter, follows the exact four-step backoff, resets only on successful
    offer creation, and reaches safe_readonly on the fifth conflict;
12. lost/truncated frame without receipt remains pending and cycles again;
13. never-receipting recipient keeps ordinary/recovery/send work, freezes
    privileged effects at 60 minutes, alerts, and is never called delivered;
14. advisory-lock cutover assigns every concurrent send exactly legacy or live;
15. 100-check shadow completes within one cumulative 30-minute attempt without
    cutover/backlog; expiry/failure forbids an unauthorized restart;
16. manifest canonical digest, including null/empty distinction and the 71
    absent ids in the non-contiguous range, independently reconciles the
    measured 1,310 retained rows in three pages, precomputes without blocking
    sends, and finalizes the locked tail within five seconds;
17. legacy page/offer never bulk certifies and semantic legacy requests remain
    visible; individual legacy receipts change only explicit transport
    subcounts and never remove manifest/unverified provenance;
18. safe_readonly rollback never calls old consume or replays received history;
19. at most one offer row per message, and exactly one after token creation,
    under indefinite rotation;
20. quarantine/receipt and parking/repair races serialize safely;
21. local outage counter works with backend down and reconciles exactly on
    recovery;
22. alert thresholds do not fire on normal first presentation/rotation and
    degraded diagnostics never mutate primary payloads;
23. zero peer-message deletes;
24. fresh-DB upgrade/downgrade passes; production downgrade after cutover refuses;
25. backend/gateway restart preserves rows/tokens/receipts;
26. all `consumed_at` paths are mode-correct;
27. real Vulcan/Mars status, claim, request and controlled dropped-response
    Gate-4 rows reconcile to exact deployed commits.

## 16. Review register

### Round 1

CC `747cbfd9`:

| Mandate | R6 discharge |
|---|---|
| R1-M1 exact rendered subset | One-message offer, exact preflight/parity, sections 3, 7.4 |
| R1-M2 authenticated identity | No instance arg; bound-session receipt, section 6 |
| R1-M3 oversize/HOL | Version-1 and explicit-legacy frame bounds, park/skip, section 4 |
| R1-M4 outage lockout | Ordinary work continues; local degraded authority, sections 1, 11 |
| R1-M5 legacy starvation | Immutable legacy manifest and live-first selector, sections 7.3, 8 |
| R1-M6 semantic/transport mixing | Separate views/counts and receipt/ack fields, sections 3, 5 |
| R1-M7 mixed-mode rollout | Explicit modes, atomic cutover, safe rollback, sections 8, 9, 13 |
| R1-M8 poison receipt | Exhaustive token outcome classification, section 6 |
| R1-M9 unobtainable empty cache | Backend truth check each turn; no cache/cursor, section 7.1 |
| R1-M10 offline recipient | Preserved quarantine/parking and recovery, section 10 |
| R1-M11 named tests | Section 15 |
| R1-M12 consumed_at audit | Sections 5, 13 |
| R1-M13 rollback polling/notice | Section 14 |

- GLM `d7eebf51`: two nits (migration single-head/forward/backward; explicit
  post-persistence boundary), discharged in sections 1 and 13.
- Kimi `f9a5329b`, retry `9e521006`: strict-verdict-invalid, no usable approval
  and no extracted mandate; recorded as nonapproval.

### Round 2

CC `3c593c43`:

| Mandate | R6 discharge |
|---|---|
| R2-M1 slot/byte starvation | One candidate/frame; live and legacy bounds, sections 4, 7 |
| R2-M2 undefined token | Exact 32-byte/43-char stable token schema, sections 5, 6 |
| R2-M3 expiry | No expiry; stable one-row rotation, sections 5, 7.3 |
| R2-M4 unbounded lockout | Ordinary/exempt tools continue; exact overdue effect gate, sections 1, 7.2 |
| R2-M5 1,310-row drain | Paged precomputation and five-second finalization, section 8 |
| R2-M6 peer send blocked | Send lock has five-second retryable bound, sections 7.2, 8 |
| R2-M7 shadow contradiction | Bounded dry-run with null cutover and explicit exposure budget, sections 8, 9 |
| R2-M8 circular pruning | Append-only/no pruning, section 12 |
| R2-M9 telemetry writer | Exact frame-attempt transaction, sections 5, 7.3 |
| R2-M10 quarantine race | Locked receipt/quarantine precedence, section 10 |
| R2-M11 mode transition/cutover | One-time cutover and lock-serialized sends, sections 8, 9 |
| R2-M12 unbound receipt | Explicit benign fail-closed outcome, section 6 |
| R2-M13 traceability | Complete round-by-round register in section 16 |
| R2-M14 semantic legacy visibility | Ack selection independent of transport, sections 7.1, 8 |
| R2-M15 alert thresholds | Numeric table and authorities, section 11 |
| R2-M16 truncation proof | Separate dropped and partial-render before-fix proofs, section 15 |

- GLM `fe185529`: infrastructure failure; retry `f708ea64` rejected with three
  findings (expiry, create-conflict handling, active-offer starvation). R6 has no
  expiry, defines second-conflict handling, stable-token cycling and bounded
  escalation.
- Kimi `94c24a61`: interim/nonterminal approval; retry `0d726c65` became stale.
  Neither produced usable mandates; both remain nonapproval.

### Round 3

- CC `27a90dfe`: 17 mandates. Discharges:

| Mandate | R6 discharge |
|---|---|
| M1 frame contradiction/HOL | exact byte table + park/skip, sections 4, 10 |
| M2 cutover race | shared send/cutover advisory lock, section 8 |
| M3 shadow loss/backlog | cutover null during bounded shadow; atomic cutover, section 8 |
| M4 rollback mass replay | safe_readonly, compatibility consumed_at, duplicate invariant, sections 1, 5, 9, 14 |
| M5 voluntary receipt only | mandatory protocol, periodic frames, privileged freeze/escalation, sections 1, 7 |
| M6 priority/legacy fairness | alternating scheduler and conditional bounds, section 7.3 |
| M7 missing per-turn rule | section 7.1 |
| M8 substituted-frame size | mandatory reserialize/reverify, section 7.4 |
| M9 primary-result corruption | no mixing; delivery-only opportunity, sections 4, 7.2 |
| M10 incomplete receipt table | exhaustive section 6 |
| M11 offer growth | one stable row/token per message, sections 5, 12 |
| M12 outage counter | local durable authority/reconciliation, section 11 |
| M13 reviewer traceability | this complete register |
| M14 destructive downgrade | fresh-only downgrade; production prohibition, sections 9, 13 |
| M15 undefined manifest hash | canonical algorithm, section 5 |
| M16 undefined well-formed | qualifier removed; DB constraints + explicit parking, sections 3, 4 |
| M17 noisy alerts | thresholds above normal envelope, section 11 |

- GLM `41bad871`: clean exact-artifact approval of R3.
- Kimi `7cb1bddc`: clean exact-artifact approval of R3.

### Round 4

- CC `82165e4f`: rejected with 15 findings. Discharges:

| Finding | R6 discharge |
|---|---|
| R4-F1 legacy rows fail new CHECK | Protocol-version conditional checks plus mode-derived trigger; production-shape migration proof, sections 4, 13, 15 |
| R4-F2 legacy frame contradiction | Live-only 7,000 bound; explicit legacy 9,000 bound and unsupported outcome, sections 4, 8 |
| R4-F3 unrepairable parked row | Dry-run-gated requeue and replacement-plus-quarantine terminal remedy, sections 4, 10 |
| R4-F4 priority enum missing | Closed `high|normal` enum at every layer, sections 4, 5, 7.3 |
| R4-F5 overdue undefined | Exact `first_offered_at + 60 minutes` predicate and effect timing, section 7.2 |
| R4-F6 cadence undefined | Exact increment/reset/non-effect rules and unit, section 7.2 |
| R4-F7 cutover lock blocks sends | Off-lock precomputation and five-second locked tail/timeout, section 8 |
| R4-F8 shadow expiry/retry undefined | One cumulative authorized window; abort and fresh authorization rule, section 8 |
| R4-F9 second conflict loses call | Untouched result, due counter, backoff, bounded safe_readonly escalation, section 7.4 |
| R4-F10 degraded banner contradiction | Out-of-band diagnostic; primary payload never changed, section 11 |
| R4-F11 unknown mode receipt omitted | Explicit `mode_unknown` outcome, section 6 |
| R4-F12 R1/R2 tables deleted | Full R1/R2 discharge tables restored in this register |
| R4-F13 offer-count warning noisy | Offer count retained as metric with no threshold, section 11 |
| R4-F14 token timing inexact | Guarantee says bound before first presentation, sections 1, 5, 7.4 |
| R4-F15 manifest null encoding | Canonical N/V tag distinguishes null and empty, section 5 |

- GLM `7ad060f9`: clean exact-artifact approval of R4.
- Kimi `e246912f`: clean exact-artifact approval of R4.

### Round 5

- CC `3fec5320`: raw completion rejected with three minor findings, but the
  wrapper failed closed as `cc_review_malformed_verdict` because its REJECT
  omitted mandates. The findings remain nonapproval evidence.
- Kimi `ebe6867d`: rejected with six mandates.
- GLM `e53a55df`: failed closed with
  `terminal_finish_reason_invalid`; no verdict transferred.

| Finding or mandate | R6 discharge |
|---|---|
| CC-F1 randomized backoff unbounded | Exact 50–100/100–200/200–400/400–800 ms schedule and fifth-conflict terminal action, sections 5, 7.4 |
| CC-F2 informational vs warning ambiguous | Explicit no-warning informational severity and separate 15-minute dedup, section 11 |
| CC-F3 snapshot count/range mismatch | Non-contiguous range and 71 absent ids stated; retained count authoritative, sections 4, 15 |
| Kimi-M1 cadence/second-conflict contradiction | Counter constrained and saturating at two; one rule covers the returned-result path, sections 5, 7.2, 7.4 |
| Kimi-M2 RFC3339 database CHECK impossible | Database stores/non-null-defaults a timestamptz instant; gateway alone canonicalizes output text, section 4 |
| Kimi-M3 legacy receipt accounting | Immutable provenance plus three exact transport subcounts and selector effect, section 8 |
| Kimi-M4 conflict counter reset undefined | Per-recipient scope; success-only reset; non-reset events and ticketed recovery defined, section 7.4 |
| Kimi-M5 grammar/consistency | Correct article and `non-receipt` spelling, sections 1, 4 |
| Kimi-M6 explicit inbox reset ambiguous | Any complete emitted frame resets; backoff outcome does not, section 7.2 |

Only R6 reviews can approve the current artifact; earlier approvals are evidence,
not transferred authority.

## 17. Acceptance and stop conditions

Gate 1 requires fresh complete-artifact `APPROVE` with zero findings, nits,
conditions, mandates, or unknowns from CC, Kimi, and GLM. Mars and MP are
excluded.

No build before approval. No merge/deploy until exact two-repository build,
migration evidence, complete tests, independent Gate-3 approval, and deployment
authorization exist.

Stop on silent exclusion, wrong receipt identity/token, state advance without
receipt, frame overflow, primary-result mutation, cutover straggler, fairness
bound failure, old-consume call after cutover, manifest mismatch, deletion,
production downgrade, Council nonapproval, failing test, dirty worktree, remote
mismatch, or unhealthy gateway/database.

Ticket T-2026-000422 must contain exact spec/build/review/deploy SHAs and Gate-4
row evidence before closure.

## 18. Out of scope

- Send-side duplicate suppression / T-2026-000339.
- New message kinds.
- General ownership, peer equality, or Council roster.
- General identity/authorship hardening beyond receipt binding.
- Future deletion/archival policy.
