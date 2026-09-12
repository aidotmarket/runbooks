# Gate 1: refund-safe joint production release

Owner Mars S1714. Design proposal, not implementation authority. BQ build:bq-refund-safe-production-s1714. Max authorizes necessary production dependencies in Event99af61fd-db46-42fd-a18d-1d0698e457d1 (2026-09-12): “I am authorizing you to do whatever it takes to get this done.” This supersedes the earlier filed-work restriction only as needed to complete the requested release. MP builds product code; CC/GLM/DeepSeek must unanimously approve applicable gates. No production success is claimed.

## 1. Problem and source baseline

Backend main d766b8e4e66d7803ebe48f8a3132521abbebe957. Exact source inspection: app/api/v1/endpoints/webhooks.py charge.refunded invokes synchronous _handle_refund, then async BillingService and commit, with finally:break suppressing exceptions. _handle_refund reads order without locking, treats permissive cumulative amounts as full refund, returns early for already-refunded/disputed orders, and changes linked transaction only for agent buyers. app/services/billing_service.py charge.refunded selects/creates Refund, unconditionally posts record_refund, and may commit before outer order/event transaction. app/services/settlement_service.py settle checks transaction confirmed and 48-hour hold, then calls Stripe Transfer without inspecting linked order refund/revocation. Its scheduler selection similarly lacks the order predicate. These are verified source gaps; no incorrect live Transfer has been demonstrated.

Related filed BQs retain their broader scopes: bq-dispute-hold-gate-s1711 owns refund/revocation exclusion and broader dispute behavior; bq-stripe-webhook-finance-idempotency-s1713 owns refund retry defects and unrelated credit-pack defects. This dependency implements only required portions and must cross-reference their completion evidence without closing their remaining work.

## 2. Required behavior

A full validated refund converges order, linked human or agent transaction, access rights, finance Payment/Refund/journal and event processing to one consistent result. Replayed, reordered or concurrent notifications do not double-debit agent spend or duplicate journals/events. A finance or outer-session failure remains retryable and must never be acknowledged as successful completion. Missing async session must fail, not skip finance.

Direct settlement and scheduler execution share one authoritative eligibility policy: confirmed transaction, unique consistent linked order, genuine elapsed hold, and no full refund, revocation, dispute or pending refund operation that makes payout unsafe. Invalid/missing contradictory state fails closed with durable audited refusal. The direct execution path rechecks eligibility under the concurrency protocol immediately before provider dispatch; scheduler filtering alone is insufficient. Positive eligible payments still settle exactly once under Stripe idempotency.

Refund/confirmation/revocation and payout concurrency needs a documented common lock order and durable operation state. A read-check followed by unlocked network transfer is inadequate. Specify the point at which payout ownership is reserved, how refund/revoke competes with that reservation, how crash-after-provider-success is reconciled without duplicate Transfer, and what happens if provider payout won before refund arrived. Never claim database rollback undoes a Stripe call. Late externally initiated refunds must be reconciled/audited without inventing automatic Transfer reversal authority or silently pretending no payout occurred. Gate2 must enumerate every participating writer and call path; guard only in settlement_service is not enough if another writer races it.

Validate provider refund identities, amount, currency, ownership and payment binding. Do not invent fallback refund identities or take an arbitrary first element from a truncated refund collection. For cumulative/multiple partial refunds, specify per-refund identity and monotonic aggregate semantics sufficient to preserve existing partial-refund behavior and prevent double adjustment. No broad credit-pack redesign. Full-refund production proof cannot be satisfied by synthetic allowlisting that hides a defective normal handler.

## 3. Proposed design boundaries and decisions

Prefer an explicit durable refund-processing checkpoint with idempotent phase replay across existing sync order/event and async finance sessions. Persist enough bound event/refund identity to recover either commit order. Every completed phase must validate existing records rather than merely suppress duplicate exceptions. Journal uniqueness is a backstop, not the retry algorithm. Use PostgreSQL locking/constraints and documented Stripe idempotency; avoid an in-memory lock or snapshot cache.

Council must assess whether one database transaction can cleanly replace the split-session path or whether a durable phased protocol is smaller and safer. Gate2 must select one concrete model, exact schema changes if any, transaction statuses/transition events, lock acquisition/release points, crash recovery, provider reconciliation and rollback compatibility. Unresolved concurrency semantics block implementation.

This is a new design authority for the required dependency, not permission to change unrelated payment branches. Vulcan owns the separate seller02 activation and narrow TEST admission amendment; coordinate exact shared webhooks.py scope and avoid concurrent edits or importing its fixture policy into the general product guard.

## 4. Acceptance redesign and protected state

Environment main c6b8770e69514035b2c78f0433f86209b4cefe0f includes PR27. Protected run25 stays on03d3f30acf854537edd76fdb19e1cf521b577c9a with mutual pins519b1d5893dc410392cc66051dad0902572dcef9. Bundle20260911T233041Z has passed online browser proof and is pending genuine settlement until2026-09-13T23:41:11.491739Z. No source/pin/runtime/checkpoint/identity mutation during this durable run. Its evidence proves its original contract only.

Current browser/s1681-delivery-leg.ts255-257 revokes the same order later confirmed at267 and expected to settle. This conflicts with the new guard. Review a replacement that preserves both a genuinely eligible positive payout and distinct revoked/refunded negative cases. Prefer separately identified TEST orders on the existing fixture, with explicit count, amounts, purchase/refund authority, provider cost, correlation, immutable receipt schemas and supported terminal cleanup. Do not drop assertions, clear revocation, exempt fixtures, reuse old orders ambiguously or simulate settled state. If additional orders require relaxing current one-order assertions, replace them with exact enumerated role/order binding and reject any extra order rather than weakening cardinality checks globally.

Gate2 must reconcile online/offline phase order, each real48-hour hold, same-install ownership, existing seller01 protection and a concrete migration/adoption point after run25. Do not abandon/refund a confirmed pending receipt through the purchasing-abandon command. If current protected state and new-contract proof cannot coexist, define a reviewed supported transition before any mutation. Tests and implementation may proceed in isolated worktrees/databases while that run is preserved.

## 5. Expected implementation surfaces (Gate2 freezes exact manifest)

Backend: app/api/v1/endpoints/webhooks.py; app/services/billing_service.py; app/services/settlement_service.py; app/services/transaction_service.py; app/tasks/settlement_scheduler.py; existing order refund/revoke/confirm writers where required by the reviewed common protocol; narrowly necessary finance model/migration files; PostgreSQL-backed tests. Product authorship exclusively MP.

Environment: browser/s1681-delivery-leg.ts, bin/check-settlement and affected verifier/evidence contract tests only for the approved acceptance redesign. No product fix in harness, no cache, no Compose hot polling. Runbooks: this design, bounded Gate2 specification, S1656/S1681 amendments, operator symptom/evidence instructions. Gate2 must name exact new filenames and justify every additional file.

Excluded: unrelated credit purchase double-grant changes, general dispute UI/notifications, new first-sale execution, unrelated cleanup, unreviewed money movement or existing protected fixture mutation.

## 6. Required evidence and rollout

PostgreSQL-backed tests must drive actual service paths and cover: valid eligible payout; full refund human and agent; duplicates and different event IDs for same refund; sequential partial-to-full progression; contradictory/missing amounts and provider identities; finance commit then outer failure; outer phase persisted then finance failure; no async session; concurrent refund/confirm/revoke/settlement with deterministic barriers; crash after provider success before local commit; scheduled/direct refusal and exactly one audited refusal per defined attempt; unrelated owner/order isolation. Assert journals, Payment/Refund totals, order/transaction statuses and events, provider call counts and access denial. No implementation-mirroring mocks alone.

Gate1 unanimous design; Gate2 freezes selected protocol/files/ACs/rollout; MP builds; Gate3 unanimous exact candidate; clean reviewed environment repin only at admitted boundary; new positive/negative connected proofs; stable release and scheduled proof; actual production deploy across backend/worker/Beat/profile-worker as applicable, exact source/images/config/schema and outside authorized customer-path verification. Preserve rollout/rollback compatibility and existing purchased rights. Do not close broader parent BQs for this subset.

## 7. Council questions

1. Is the bounded dependency sufficient and appropriately separate from Vulcan’s TEST admission amendment and unrelated backlog?
2. Which transaction/checkpoint model is required to prevent lost effects across sync/async commits without deadlock?
3. What exact common reservation/locking and provider reconciliation protocol is necessary for refund/revoke/confirm versus payout races and late provider refunds?
4. What per-refund/aggregate identity invariants preserve partial-refund correctness and agent spend while eliminating duplicate finance effects?
5. Does the proposed distinct-order acceptance approach preserve all original positive and negative requirements, and what exact migration constraints protect run25?
6. List mandates before MP implementation, simpler alternatives and any production-blocking gaps. This is design review; no paid run, provider mutation, product edits or bypass permitted.
