# T-2026-000422 — Lossless Peer Bus Gate 1

Status: `AUTHORED_PENDING_REVIEW_R4`

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
- a stable 256-bit token is bound to that one message and recipient;
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
privileged state-changing effects after bounded nonreceipt. If the recipient
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
1,310 retained rows (ids 651–2031), 2 legacy-unconsumed rows, 2 semantically
unacknowledged request/alert rows, and a maximum body of 7,842 UTF-8 bytes.
Those rows are legacy and remain accessible through the legacy view.

Post-cutover sends enforce at gateway, backend model, and database CHECK:

- `body`: at most 6,000 UTF-8 bytes;
- `ref_entity`: null or at most 256 UTF-8 bytes;
- sender/recipient/kind/priority: existing fixed enums;
- message id: signed 64-bit positive integer;
- created timestamp: canonical UTC RFC3339.

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

If a committed row violates the supposedly impossible frame invariant, the
backend atomically sets `delivery_parked_at/reason=frame_invariant`, raises a
critical alert containing id but no body, excludes it from head-of-line
selection, and advances to the next row. Parking never marks delivery; admin
repair/requeue is required.

## 5. Durable schema

Add to `peer_messages`:

- `delivery_received_at timestamptz null`
- `delivery_attempt_count integer not null default 0`
- `last_delivery_attempt_at timestamptz null`
- `delivery_quarantined_at/by/reason`
- `delivery_parked_at/reason`

`acked_at` remains semantic ack. On accepted transport receipt,
`consumed_at = coalesce(consumed_at, delivery_received_at)` is written solely for
legacy compatibility; enforced selection ignores it.

Add `peer_message_delivery_offers`, exactly one row per message:

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
- `calls_since_delivery_opportunity integer not null default 0`;
- `last_priority_served` nullable `high|normal`.

`cutover_message_id` is null throughout shadow. It is set once at the atomic
cutover and immutable thereafter.

Add `peer_bus_legacy_manifest` with recipient, cutover id, count, min/max id,
ordered digest, creation time, actor/session.

Manifest digest is reproducible without a new body-hash column:

1. UTF-8 encode body exactly as stored, with no normalization;
2. compute lowercase hex `sha256(body_bytes)`;
3. for ascending id, append ASCII
   `<decimal_id>:<64-hex-body-digest>\n`;
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

Privileged state-changing tools (dispatch/build authorizations, merge, deploy,
production mutation, and session close) require all already-offered overdue
tokens for that recipient to be receipted first. They return the next complete
frame instead of executing. After receipt they are retried. At 60 minutes
without receipt, privileged effects remain frozen and a critical incident opens.
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
selection. Privileged gating can accelerate delivery but never weaken bounds.

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
fresh peek. A second conflict returns `PEER_BUS_DEGRADED` with no delivery
change; the substantive tool is not run on a scheduled delivery opportunity.

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

Shadow pass per recipient is 100 consecutive checks completed within 30 minutes,
including status/claim/request canaries, with exact independent-query parity,
zero new-state mutation, zero selector/frame errors, and all frame bounds met.

All sends and cutover use the same recipient advisory lock:

`peer_bus_cutover:<recipient>`

The cutover transaction waits for earlier send transactions, acquires the lock,
sets the maximum committed id, creates/verifies the manifest, switches directly
to `enforced`, and releases. A concurrent send either commits wholly before the
watermark and is manifested legacy, or acquires the lock afterward and is live.
There is no in-flight sequence-id straggler.

The measured 1,310-row snapshot requires three 500-row internal pages. At
cutover the job pages until the then-current count is exhausted and must
independently reconcile count/min/max/digest within ten minutes. Mismatch stops
cutover.

Legacy rows remain `legacy_unverified`, visible by scalar count and manifest.
`peer_msg_legacy_page(after_id, limit<=100)` is read-only.
`peer_msg_legacy_offer(message_id)` uses the normal stable-token protocol only
when no live row is pending. No bulk receipt or automatic certification exists.
Semantic pending includes every unacked request/alert regardless of legacy or
transport state.

Legacy paging also applies a 40,000-byte decoded-output budget and returns only
complete records plus a continuation id. A legacy offer preflights the actual
record against the 50,000-byte outer cap; an exceptional row that cannot fit
returns `legacy_frame_unsupported` with no state change and remains fully
queryable by paged/admin storage access.

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

Parking is automatic only for a violated database/frame invariant, emits an
immediate critical incident, and advances scheduler selection. It is never
delivery. Repair/requeue for parked or quarantined rows requires audited actor,
reason, ticket, and Max authorization; it returns the stable offer to `pending`
without changing receipt/semantic state.

## 11. Degraded-state authority and observability

Backend-reachable metrics emit to Event Ledger and SysAdmin:

| Signal | Warning | Critical |
|---|---:|---:|
| Oldest live pending age | 15 minutes | 60 minutes |
| Live pending count | 20 | 100 |
| Offer count for one message | 5 | 20 |
| Receipt latency after first frame | 15 minutes | 60 minutes |
| Quarantined/parked count | any non-zero informational | any row over 24 hours |
| Manifest mismatch | immediate | rollout stop |

Warnings deduplicate 15 minutes. Critical events remain open until cleared.
Routine first frames and scheduler rotation do not warn.

Backend outage uses a different authority: the local gateway writes every
failure transactionally to `registry.db.peer_bus_degraded_events`, which is
available when the backend is not. The authoritative consecutive count is
local. Every affected tool response displays `PEER_BUS_DEGRADED`; the fifth
consecutive failure sets a durable local critical flag exposed by `peer_status`
and every subsequent terminal banner.
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
2. exact 6,000/256 maximum fields fit 7,000 decoded bytes and worst-case outer
   JSON under 50,000; 6,001-byte body and 257-byte ref reject before commit;
3. frame-invariant failure parks/alerts/skips without receipt or head-of-line
   blocking;
4. every-turn/no-cache check is enforced;
5. ordinary calls follow two untouched results then one complete delivery-only
   opportunity; exempt tools are never displaced;
6. privileged effects block on overdue offered tokens; Max suspension is
   audited and never receipts;
7. stable 43-char token maps to one message/recipient and persists through
   scheduler rotation;
8. all receipt outcomes in section 6, including modes, outage, quarantine,
   parking, unbound, forged recipient, and idempotency;
9. semantic ack remains independent;
10. alternating priority prevents sustained-high starvation; bounds
    `3*(Q+1)` / `6*(Q+1)` hold; legacy yields to live;
11. concurrency returning a different row triggers full reserialization and a
    second-conflict degraded stop;
12. lost/truncated frame without receipt remains pending and cycles again;
13. never-receipting recipient keeps ordinary/recovery/send work, freezes
    privileged effects at 60 minutes, alerts, and is never called delivered;
14. advisory-lock cutover assigns every concurrent send exactly legacy or live;
15. 100-check shadow completes within 30 minutes without cutover/backlog;
16. manifest canonical digest independently reconciles the measured 1,310-row
    snapshot in three pages and the actual cutover set in as many pages as
    required, always within ten minutes;
17. legacy page/offer never bulk certifies and semantic legacy requests remain
    visible;
18. safe_readonly rollback never calls old consume or replays received history;
19. one offer row per message under indefinite rotation;
20. quarantine/receipt and parking/repair races serialize safely;
21. local outage counter works with backend down and reconciles exactly on
    recovery;
22. alert thresholds do not fire on normal first presentation/rotation;
23. zero peer-message deletes;
24. fresh-DB upgrade/downgrade passes; production downgrade after cutover refuses;
25. backend/gateway restart preserves rows/tokens/receipts;
26. all `consumed_at` paths are mode-correct;
27. real Vulcan/Mars status, claim, request and controlled dropped-response
    Gate-4 rows reconcile to exact deployed commits.

## 16. Review register

### Round 1

- CC `747cbfd9`: 13 mandates, all mapped in R3/R4 design.
- GLM `d7eebf51`: two nits (migration single-head/forward/backward; explicit
  post-persistence boundary), discharged in sections 1 and 13.
- Kimi `f9a5329b`, retry `9e521006`: strict-verdict-invalid, no usable approval
  and no extracted mandate; recorded as nonapproval.

### Round 2

- CC `3c593c43`: 16 mandates; R4 retains their discharges and replaces the
  problematic R3 mechanisms where necessary.
- GLM `fe185529`: infrastructure failure; retry `f708ea64` rejected with three
  findings (expiry, create-conflict handling, active-offer starvation). R4 has no
  expiry, defines second-conflict handling, stable-token cycling and bounded
  escalation.
- Kimi `94c24a61`: interim/nonterminal approval; retry `0d726c65` became stale.
  Neither produced usable mandates; both remain nonapproval.

### Round 3

- CC `27a90dfe`: 17 mandates. Discharges:

| Mandate | R4 discharge |
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

Only R4 reviews can approve the current artifact; earlier approvals are evidence,
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
