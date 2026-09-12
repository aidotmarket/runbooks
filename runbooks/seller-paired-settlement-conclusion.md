---
title: Seller paired settlement conclusion and recovery
owner: vulcan
last_verified: '2026-09-12'
aliases:
  - Paired online offline settlement resume
  - Seller settlement archive and cleanup diagnosis
error_signatures:
  - original acceptance differs from purchase-time receipt
  - archived original acceptance differs from purchase-time receipt
  - original acceptance criteria or pinned source differs
---

# Paired settlement conclusion: diagnosis, support and upgrade notes

Source checkpoint: environment `6b473e3006b4c87716fbe2e96a712181acd2011c`, independently reviewed in Mars4243/Vulcan4244 after the prior2b517 slice. This explains implemented source, not an accepted or executed live run. Original-acceptance binding finding4239 is corrected at this exact source: purchase-time original hash, named criteria and pinned source/payment checks are enforced before cleanup, phase advancement and conclusion. Read the current [Seller Workspace operator guide](seller-workspace-operator-guide.md), [failed TEST refund recovery](seller-failed-test-refund-recovery.md) and owner checkpoint before using any dated identity here.

## Purpose and ownership

The paired test proves two different outcomes for the same seller listing. P is seller01/buyer01: a normal paid delivery, buyer confirmation, genuine 48-hour hold and seller settlement. N is seller01/buyer02: normal paid delivery and confirmation, independent access revocation, the same genuine hold, refusal of bare-revoked settlement, then a normal full refund and continued access/payout refusal. Online and offline phases use separate clean seeds and new purchases, and exercise opposite initial signed payment-event orders. The offline phase follows verified online cleanup. W, the Seller Workspace purchase/refund proof, has its own later owner-opened window and authority; it is not a role in this pair.

Mars owns the protected environment, payment operations and accepted runtime transition. MP authors product and product tests. Vulcan independently reviews, maintains Workspace integration and runbooks, and does not create a second runtime or mutate a peer checkout. Existing user authority is cumulative up to100USD; it does not reset between phases. Consult the exact budget receipt before paid execution.

## Entry points and state transitions

All operator shell commands use `rtk proxy`. The supported entry point is `bin/verify`; `bin/check-settlement` owns its shared lock, source pins and active checkpoint. Internal functions are not alternate operator routes around those checks. Examples below are a map of existing command behavior, not instructions to run against protected run25 now.

| Entry or state | Actual behavior and support implication |
|---|---|
| `rtk proxy ./bin/verify --from-clean-seed` | Requires a clean source checkout, mutually bound acceptance specifications and exact runtime versions. It enters the existing exclusive lifecycle lock. An active run routes to resume rather than starting another purchase. |
| `rtk proxy ./bin/check-settlement` | Enters the same lock, binds the active source and purchase digest, and runs the v2 settlement stages only for the correct pending/settled pair. Both real holds are checked before effects. A zero exit still requires concluding verification. |
| `purchasing` | Purchase activity has begun but confirmation evidence is not complete. Resume returns2 and preserves the phase; establish whether money moved through supported owner recovery. Do not infer unpaid status from a missing final receipt. |
| `pending_settlement` | The pair and confirmations are recorded, but the two real holds and required post-hold work are not complete. Resume returns2. A separate settlement operation must prove both deadlines against the current PostgreSQL clock before effects. |
| `FAILED` | Durable failure evidence preserves the exact paid run. Resume returns2. Use the separately documented FAILED-v2 refund/recovery path and its exact authority. It does not authorize cleanup of protected v1 run25. |
| `settled`, online | Means the paired settlement-stage chain exists, not full acceptance. Resume validates the archived online chain and fresh cleanup admission, then invokes the supported offline clean lifecycle. Reset must perform exact S3 cleanup before removing the old environment data. |
| `settled`, offline | Resume runs `bin/verify --settlement-cleanup`, loads both completed phase archives, verifies the wrapper contract, writes an immutable summary and only then marks the active checkpoint complete. |
| `complete` | Resume validates retained archives and summary hash and returns the same result. It must not rerun purchase, refund, device replay or cleanup to create replacement success evidence. |
| `rtk proxy ./bin/verify --settlement-snapshot` | Uses the observation mode. It can support a pending pair only after the complete immutable settlement chain is present; it does not itself grant cleanup. |
| `rtk proxy ./bin/verify --settlement-cleanup` | Uses distinct cleanup admission. It takes a production observation and invokes the seed object's cleanup only through the allowed settled state. |

An existing offline directory deliberately causes refusal before overwriting evidence. A crash after online cleanup/reset but before a complete offline purchase is not the same as the tested final-summary/checkpoint-write retry. Preserve the directory and active record for owner diagnosis. Never delete an offline directory or edit `active-run.json` to manufacture a clean retry.

## What is recorded and how the chain is checked

Evidence is under the configured acceptance evidence root, then `<run>/online` and `<run>/offline`. The normal root is `/Users/max/koskadeux-state/s1656/acceptance-evidence`. Treat its path and current active run as observed state, not a run ID inferred from these notes.

| Artifact | Meaning and binding |
|---|---|
| `browser-evidence.json` | Actual browser acceptance and per-role delivery/refusal observations. Its exact bytes are hashed by the purchase record. An HTTP200 or outbound ACK alone is not successful delivery. |
| `purchase-confirmation.json` | Run, phase, exact sources/images, clean seed, P/N identities, original payment/charge bindings, confirmed events, real hold deadlines, role delivery hashes and browser digest. |
| `test-negative-pair.json` | Canonical pair envelope and digest. Both fixed buyer roles, seller/listing and original captured payment identities must match the purchase record. |
| `test-negative-registration.json` | Exact N order and purpose `negative`, bound to the same envelope digest. This is neither W nor failed-run authority. |
| `bare-negative-check.json` | P's normal payout evidence plus N's refusal while only independently revoked, including the exact exclusion audit and scheduled-path outcome. |
| `negative-refund-check.json` | Normal provider-succeeded full refund for N, actual applied local effects, zero negative transfer, source-bound posted capture/refund allocations and continued settlement refusal. |
| `refund-replay-check.json` | Provider redelivery of the same signed refund event, increased duplicate observation and no second business effect. It points back to the normal refund proof. |
| `refund-access-check.json` | Actual N buyer refusal at the three required download/refresh boundaries. No usable redirect or credential is accepted as refusal. |
| `device-replay-check.json` | Actual device driver's correlated business response and unchanged P/N business state. P must remain delivered/completed; N must receive `INVALID_ORDER_STATE`. The observed message must come from the authenticated encrypted data frame, not an unrelated plaintext event or generic transport exception. |
| `settlement-check.json` | Immutable anchor over all five stage records, both roles, source/purchase/pair hashes, real hold observation and final repeated settlement outcome. `state: settled` alone is insufficient. |
| `production-before.json`, `production-after.json`, `production-settlement.json` | Read-only production observations. After removal of only the observation timestamp, the parsed snapshots must agree. A process-health flag is not this preservation proof. |
| `cleanup.json` | Immutable exact run/phase/source/seed/purchase/settlement/pair binding, fresh paired cleanup admission and verified zero remaining owned S3 objects. |
| `<run>/wrapper-contract.json` | Immutable local failure-and-overlap wrapper check with run/source identity and completion time. |
| `<run>/summary.json` | Both fully validated phase archives, distinct clean seeds/orders/transactions/events, identical purchased bytes, offline-after-online-cleanup ordering and original acceptance evidence. Original acceptance bytes must match their purchase-time hash, and exact named checks/source/clean-run/payment facts must agree with hash-bound online browser evidence. |

The immutable reader rejects symlinks, nonregular files, wrong ownership, writable modes, oversized data and noncanonical JSON. It verifies the descriptor and current path still refer to the same content metadata, including nanosecond times. Access time may change merely because a file was read; that is not content drift. A valid hash proves bytes match an anchor. Semantic checks still have to prove those bytes describe the correct run and outcome.

## Cleanup's ordering matters

`validate_pair_cleanup_v2` first checks current owner/source and the full archive. It then reads the current TEST delivery state, verifies both real confirmations/holds and unchanged business rights/history, checks provider P payout and N refund, and independently verifies local authority and posted financial effects. It rechecks owner/source afterward. Only then may `seed/s3-fixture.py` list versions under the exact recorded run prefix, refuse unexpected keys, delete those specific versions and verify absence. The durable cleanup record is written before the seed record is marked cleaned. A retry preserves the original cleanup receipt's bytes and identity while obtaining new admission observations.

Do not recover by deleting S3 objects first. Do not mark a seed cleaned because a prior command exited successfully. Do not treat a provider refund alone as proof that local effects, journals, buyer refusal, device refusal and scheduled exclusion completed.

## When it breaks

1. Establish exact active state, run/phase, source pins, clean checkout and lock owner. Read the named purchase/settlement/failure receipts. Never print tokens, signed URLs or provider secrets while diagnosing identity.
2. For an archive refusal, identify the first failing binding: file bytes/mode, source/run/role, payment/charge, event ordering, hold, posted allocation, replay, access, device disposition, cleanup or production preservation. Keep the original files unchanged. A rehash of edited evidence is not repair.
3. For cleanup refusal, compare fresh provider and local payment state before considering another attempt. An absent or ambiguous transfer/refund, changed counters, unresolved delivery, changed original identity or changed owner must remain a refusal. Reconcile through the normal owner-managed protocol.
4. For a summary refusal, check original named acceptance criteria and source/image/A2/clean-run bindings against the hash-bound online browser evidence, then both phase archives and wrapper time. The earlier2b517 source omitted those checks;6b473 corrects them. Preserve the original evidence rather than editing it to satisfy the new validator.
5. If the summary exists but writing the active checkpoint failed, retry only through the supported entry point. The implementation reads the retained end time and compares the exact summary; it must preserve the original bytes/inode rather than generate a later-looking result.
6. If a previous offline attempt left evidence, preserve it for the documented owner recovery procedure. The supported runner refuses overwrite. Distinguish unpaid failure, paid pending/FAILED recovery and already settled phase before changing lifecycle state.

## Upgrade and acceptance procedure

Bind the final product commit, built images/source labels, environment commit, `versions.env`, both exact accepted specifications and complete review responses before replacing runtime. Preserve the protected current run until Mars completes its supported lifecycle and opens the next window. Re-run meaningful isolated contracts on the final candidate, then obtain full product/environment Gate3 and actual paired runtime evidence. The6b473 retained337 tests and synthetic archive/provider observations are useful implementation evidence but do not replace that execution.

Any change to receipt schemas, role identities, financial authority, source pins, cleanup ordering or recovery states needs explicit source/test coverage in the accepted scope. Never downgrade a live receipt by silently converting it to a previous format. On failure, close new admission, retain evidence and existing paid rights, and use the reviewed compatible recovery path. Production activation separately requires all four automatic deployment triggers frozen before merge, old-writer quiescence, exact migration/image proof, restored adoption and independent outside verification.

The [independent correction review](evidence/seller-refund-access-s1712/SELLER-ORIGINAL-BINDING-6B473-REVIEW-S1712.txt) and [exact source/log verification](evidence/seller-refund-access-s1712/SELLER-ORIGINAL-BINDING-6B473-VERIFICATION-S1712.json) retain the evidence and its limits. Before any credential use, follow [Infisical](../infisical-secrets.md) and [local SecOps](../local-secops.md). Production changes follow the separate [payment cutover runbook](seller-production-payment-cutover.md).
