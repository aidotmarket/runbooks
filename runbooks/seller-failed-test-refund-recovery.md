---
title: Failed TEST purchase refund and recovery
owner: vulcan
last_verified: '2026-09-12'
aliases:
  - S1681 failed paid run release
  - Failed positive negative purchase recovery
error_signatures:
  - normal atomic refund effects unproved; preserve FAILED checkpoint
  - persisted canonical authority receipt differs
---

# Failed TEST purchase refund and recovery runbook

Status: implementation integrated by Mars on September 12, 2026, at environment candidate `7b50ae6db00d7457baaf29b4b5796b64f305746d`, from delegated source `07aca0f238d36efa1dbdbe54f0612265f0da4054` (follow-up to `4b46150334bb8b7601722a352cee44336c212867`), branch `codex/s1712-failed-run-release`, delegated base `1408afc57e1614d3d105e88cbaab80310dfb9ee1`. This is the bounded two-file harness slice, not a deployed or fully accepted product. Mars owns the combined normal P/N harness and final exact-candidate review; Vulcan owns this delegated slice and Seller Workspace. Authority is the accepted payment specification section8 plus F1 and peer requests4186/4196. No additional user approval is pending for that scope.

## What this process does

A failed paid test run must not be reset while money or buyer access is unresolved. Each exact failed role is bound to the owner-authored failure, source versions, packaged accounts, order, transaction, real PaymentIntent and captured Charge. The private product command establishes durable payout exclusion and revokes access before the harness can request a normal Stripe TEST refund. The normal signed webhook and processor must then apply the refund, including actual posted accounting entries. Only immutable verified per-role evidence permits closure. A successful P payout is preserved when N fails; P is never refunded merely to clear the environment.

P is buyer01, N buyer02, both purchasing the one seller01 fixture. Workspace W is a separate seller02/buyer01 namespace and cannot use this authority. A single P captured before N exists can be released. If an unpaid sibling's checkout is still live, the checkpoint remains protected until a separately reviewed expiration/no-capture procedure proves closure. No invented order, second listing, early hold completion or hidden W role is allowed.

The protected v1 run25 remains outside this path. Its recorded deadline is 2026-09-13T23:41:11.491739Z; reaching that time is not an owner window. Mars must finish/reconcile it and announce the next clean lifecycle. Never replace its source pins, convert its pending checkpoint to FAILED, add buyer02 to its containers, or invoke the legacy purchasing-abandon path to evade the hold.

## Source and integration map

Implementation: `bin/check-settlement`; executable contracts: `tests/test-refund-proof-contract.py`. Both files are in the owned checkout `work/failed-run-release-s1712` under `/Users/max/Documents/Codex/2026-09-11/seller-workspace-final-release-continuation`. The [initial implementation receipt](evidence/seller-failed-refund-s1712/SELLER-FAILED-RELEASE-IMPLEMENTATION-S1712.json) binds full source hashes, commit and logs. The [current schema fold receipt](evidence/seller-failed-refund-s1712/SELLER-FAILED-RELEASE-C9D-FOLD-S1712.json) binds the latest60-test candidate. Logs remain at the absolute retained evidence paths in those receipts.

- `record_purchase_failure`: the existing owner path records an actual failed purchasing invocation. It ignores successful pending and v1 runs.
- `record_settlement_failure(run_dir, exit_code)`: new hook for Mars's actual terminal settlement exception only. It accepts exact v2 pending state or a retry of its own settlement failure, rejects success/exit2 hold wait/v1, verifies the immutable purchase hash and both confirmations against the current PostgreSQL clock, then publishes the failure before updating active-run. Mars must wire it into the terminal exception callsite; there is no generic operator permission to turn a waiting run into FAILED.
- `failed_release_context`: checks current owner/source, failure schema/hash/bytes, frozen role facts, complete order/transaction selector and eligible nonsettled captured state. It permits local paid_count0 before the payment webhook, but a real captured provider payment and persisted exact PaymentIntent binding are still required. Local zero paid markers are recorded honestly.
- `register_failed_role`: sends an exact canonical envelope on stdin to `scripts/order_money_protocol.py register-test-failed-refund`. The product, not this harness, owns locking, readiness, reservation cancellation, access revocation and immutable TEST authority.
- `refund_role_provider_v2`: shared normal-N/failed-role provider helper. It independently verifies TEST settings/key shape, exact backend image, current party/order/transaction identity, captured PI/Charge and complete Transfer/Refund lists. It never calls an internal webhook or fabricates an application result.
- `validate_refund_effects_v2`: requires actual refunded/revoked order and transaction, full2500 applied, one correctly bound transaction event, one real Refund, same Payment/entity, exact posted capture/refund lines and completed/applied StripeEvent with no error marker.
- `preserve_settled_positive_v2`: integrates Mars's `pair_provider_snapshot` and `validate_positive_payout_finances`. It requires the immutable purchase and fresh real P payout/capture/posted-finance proof. If `bare-negative-check.json` exists, its positive_finances must match. If a crash occurred before that file was published, fresh complete positive proof can preserve P without inventing a bare N refusal. Missing integrated validators refuse closure.
- `close_failed_checkpoint_v2`: writes and syncs the all-role closure receipt before removing active-run, then syncs its directory. Interrupted closure can be retried without replacing earlier evidence.

## Required owner context and invocation

Before an eventual authorized test operation, read the current [payment specification](https://github.com/aidotmarket/runbooks/blob/2da7bcc476142af51047c8916bdf828e810d1db0/specs/BQ-REFUND-SAFE-PRODUCTION-S1714-GATE2.md) and environment runbook; confirm exact accepted product/environment/spec commits, current owner window and protected-run status. Use the existing [Infisical](../infisical-secrets.md) and [local SecOps](../local-secops.md) procedures for the test environment. Do not echo credentials, pass a secret or authority document in argv, or export production credentials to the test process. Refresh the exact active checkpoint and runtime image proof. A branch merge alone never changes the protected runtime.

The existing entrypoint is:

```sh
rtk proxy bin/check-settlement --abandon-refunded <exact_run_id> <exact_environment_sha40> <exact_order_uuid>
```

Run from the final integrated, reviewed, clean test-environment checkout. Arguments are the named nonsecret identities; the command acquires/proves the existing shared owner lock. Its v2 branch requires an existing genuine FAILED checkpoint. Do not manually edit active-run or call the failure-marker hook as a substitute for an actual failed owner invocation. Do not run this command in the production checkout or against run25.

Release one exact role at a time. Exit2 from this operation means another role remains protected; it does not allow reset. Exit0 means the exact failed checkpoint has a durable complete release record and its active guard was removed. A refusal/exception preserves the failure and evidence for diagnosis. A later invocation after completed closure refuses because there is no active failed run; it must not recreate authority or buy again automatically. The surrounding reviewed lifecycle controls any new clean seed/purchase.

## Durable evidence sequence

All records live under the exact evidence root/run/online-or-offline directory, with owner checks, no symlinks, canonical ASCII JSON and immutable0400 publication. Canonical object digests exclude the envelope digest and trailing newline. File hashes include the actual file bytes and newline. Source identities are lowercase40hex; content digests are lowercase64hex. Do not interchange them.

| Record | Meaning and recovery rule |
|---|---|
| `purchase-failure.json` or `settlement-failure.json` | Actual owner failure, source/run/role bindings, nonzero exit; settlement version additionally binds purchase/pair and real hold observation. Hash must equal active-run.failure_sha256. Never rewrite it. |
| `failed-paid-proof-P.json` / `-N.json` | Exact captured provider identity plus actual local paid markers. A late paid webhook may progress0 to1; the original observation stays immutable. No invented paid_at. |
| `failed-role-P.json` / `-N.json` | Product stdin envelope: schema2, run_id, phase, environment_sha, spec_sha, statusFAILED, selected role, failure_receipt_sha256 and exact nine-field role binding. |
| `failed-registration-P.json` / `-N.json` | Exact product return order_id/purpose/digest. A pre-existing exact N negative authority stays negative and is checked against `test-negative-pair.json`; it is never overwritten as failed_run. |
| `refund-request-P.json` / `-N.json` | Immutable provider request identity before the one possible create. Shared normal/failed N recovery uses the same request. A previous attempt with no exact listed refund is uncertain; no second create is permitted. |
| `failed-release-P.json` / `-N.json` | Immutable failure/source/paid-proof/authority binding, sanitized provider result and fresh actual applied order/refund/journal/event proof. It is published only after normal effects commit. |
| `failed-preserved-P.json` | Successful P Transfer and posted finances retained through the normal validators. It is not a refund receipt and does not claim any missing N bare-refusal proof. |
| `failed-release-complete.json` | Per-role receipt hashes, preserved settled roles and final disposition. It is durably written before active-run removal. A P-preserved/N-refunded close is labeled separately from all-roles-refunded. |

At product c9d8840b, pair_receipt_sha256 anchors the full canonical authority envelope for BOTH negative and failed_run purposes. For failed_run it must equal the failed-role envelope digest, while failure_receipt_sha256 still binds the separate failure evidence. The exact retained s1681_authority_receipt audit is compared to that hash; missing, duplicated or changed records refuse. Requiring a null pair digest for failed_run was the earlier88f8231e shape and is incompatible with c9d8840b. The provider entry checks both deployment S1681_ENVIRONMENT_SHA/S1681_SPEC_SHA and current DB authority pins before any provider mutation. The fixed merchant is3ed61c38-79c0-4cf7-8011-5a781ff5f3b7.

No TEST authority row is deleted during cleanup. Its immutable failure/negative purpose and independent revocation prevent a subsequent payout reservation. The CLI's same-transaction product checks are essential; the harness's provider read showing zero Transfers alone would leave a race.

## Provider and accounting details

The refund metadata is exactly `s1681_run`, `s1681_phase`, `s1681_role`, `order_id`, `transaction_id`. The deterministic key is `s1681-v2-refund-{run}-{phase}-{role}-{order_id}`. Purpose is deliberately absent so an already issued normal N refund can be reused during later failed-N recovery. A different refund, duplicate, partial, pending, foreign metadata, or Transfer prevents success. Both transaction-number and legacy order-number Transfer groups are fully paginated. No new key or TTL-based retry is allowed after an uncertain attempt.

Stripe's [Refund object](https://docs.stripe.com/api/refunds/object) has no livemode field. TEST identity comes from the configured test key, independently fetched PI/Charge and normal TEST event; do not add an impossible Refund.livemode assertion. Provider bodies remain in process memory; only selected nonsecret binding/status facts enter these receipts.

For an untransferred2500-cent order, the posted capture is DR1000=2500, CR2110=2375, CR4000=125. The full refund is CR1000=2500, DR2110=2375, DR4000=125. Zero5100 lines are omitted. Payment, Refund, state, journal source IDs and billing entity must agree, with the selected active US/USD AIM_WY_LLC merchant and exact chart names/normal balances/flags. Balanced drafts never count. The normal buyer path requires agent_spend_delta_cents0.

Exactly one transaction status_changed event must come from order_sync_trigger and bind actual prior state, exact order and provider refund ID. Normal N starts confirmed. Failed captured roles can start checkout_pending, agent_payment_pending or other accepted paid/fulfillment states; do not invent a prior confirmed state. A separate OrderEvent('refunded') is not required by accepted section5. Its actual count is retained and checked unchanged during replay. Completed/e2e_scope_suppressed, completed-without-applied, missing applied timestamp, partial total or a second transaction event is not refund completion.

## When it breaks

1. Verify checkpoint source/failure kind/hash, immutable record modes/ownership, selected role and complete current role set. A source mismatch must be reconciled to the exact existing run; repinning a failed purchase is not recovery.
2. Verify current backend container labels, running state and image against the retained image-digests file using fresh direct Docker discovery. Do not poll Compose or cache an earlier container ID.
3. Read the exact TEST authority and money-state row. Missing readiness, dynamic fixture ambiguity, changed authority/purpose, dispatch token, unknown/reconciliation payout or an existing Transfer is a product/identity condition to resolve. Do not mark the event complete or clear state manually.
4. If `refund-request-{role}.json` exists, list the exact provider Refunds/Transfers. Reuse only the single matching successful full refund. If no refund is found after a prior attempted dispatch, preserve the request and checkpoint for explicit reconciliation; deleting the marker or selecting a fresh key would risk another refund. An interruption between publishing the request and sending it is also conservatively uncertain.
5. If the provider refunded but application effects are absent, inspect the signed StripeEvent, admission phase, canonical Refund/Payment rows and actual posted journals. A retryable product/configuration failure must remain retryable; do not accept a suppressed completion or invoke internal handlers. Reconcile/fix through the reviewed product process, then retry the same normal event.
6. If N is released but P has a successful Transfer, use the integrated positive-preservation proof. Never refund P or replace its payout evidence to clean N. Missing positive integration or a changed existing positive proof keeps the checkpoint open.
7. If immutable role receipts exist but closure publication/removal failed, retry the same role. Every prior role gets fresh provider and committed-effects verification, then the same closure bytes are reused. Do not discard a valid earlier receipt.
8. After exact closure, use only the agreed next lifecycle under the owner window. Failure closure is not proof that the corrected positive/negative acceptance journey or production release passed.

## Validation and upgrades

The latest candidate passed60 refund contracts, zero failures/skips. Its parent passed58 refund and108 delivery contracts; the108 count is the parent regression, not a rerun on the follow-up. `SELLER-FAILED-RELEASE-C9D-FOLD-S1712.json` binds this distinction and the exact current source hashes. The provider main executes in tests with fake transports that cover one create, existing-refund reuse, complete pagination, duplicate/foreign/live refusal and unknown-dispatch refusal. Filesystem tests cover immutable evidence, both-role closure, interruption before closure publication and before active removal, real-hold admission logic and preservation callbacks. These are isolated tests, not a real database/Stripe/browser proof. The new financial SQL has not been executed against the protected runtime. Mars's combined candidate must run its full required suite and final CC/GLM/DeepSeek Gate3, then the actual authorized test and production verification sequence.

When upgrading, retain the exact source/receipt contract or add an explicitly reviewed version. Never rewrite v1 or priorv2 files in place. Changes to the private product CLI fields, money snapshot keys, journal chart, normal provider metadata/key, helper return schema or closure semantics require coordinated harness/product validation. Keep deployment freeze, old-writer quiescence, unknown-outcome reconciliation and no-defective-journal-trigger rollback requirements in the [production cutover runbook](seller-production-payment-cutover.md). This slice does not authorize bypassing any of those gates.


## Integration verification checkpoint

Mars message4209 reports the combined candidate passed77 refund,108 delivery,70 seed,10 journey and21 nightly contracts with zero skips; runtime Python compiled and the actual money snapshot SQL passed EXPLAIN on disposable PostgreSQL17. Vulcan independently verified all14 delegated function ASTs match the exact integrated source. These checks do not prove a paid lifecycle, normal webhook delivery, protected-run closure or production release. The full integration receipt remains `/Users/max/Documents/Codex/2026-09-11/seller-workspace-final-release-continuation/outputs/SELLER-FAILED-RELEASE-MARS-INTEGRATION-S1712.json`. For partial refunds that should retain access, use the [access diagnosis runbook](seller-refund-access-diagnosis.md); do not invoke a failed-run full refund to repair an access-status bug.
