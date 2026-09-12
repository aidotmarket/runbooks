# S1656 A2: seller02 Workspace activation and TEST refund amendment

Status: proposed Gate1 contract; not dispatched, approved, implemented or activated. Vulcan S1712 owns this amendment; Mars S1714 owns S1656 and S1681. This document supersedes the append-only draft retained in SELLER-INTEROP-GATE1-AMENDMENT-HISTORY-S1712.md. Preparing this amendment independently is authorized by Mars4069/4070. Implementation and live-operation gates remain separate.

## Exact baseline and release objective

Environment PR27 is merged as c6b8770e69514035b2c78f0433f86209b4cefe0f, from unanimously accepted candidate a7f1daf396c290810d1535c9049aeccb2b6f56ed on base03d3f30acf854537edd76fdb19e1cf521b577c9a. Candidate and merge trees match. This amendment adds no changes to that accepted scaffold.

Protected run25 remains on environment03d3f30acf854537edd76fdb19e1cf521b577c9a, backendd766b8e4e66d7803ebe48f8a3132521abbebe957 and both acceptance pins519b1d5893dc410392cc66051dad0902572dcef9. Mars4090 verified pending-hold with direct checker exit2. Hold deadline2026-09-13T23:41:11.491739Z is not a live-window authorization. Do not repin, reset or operate that environment independently.

The finish line is full AWS S3 and Cloudflare R2 Seller Workspace release, joint compatibility with the money path, reviewed production deployment and outside verification. This seed/TEST amendment is a prerequisite. A seed-only milestone, test hold or scaffold merge cannot close that objective. No new real-money first sale is authorized here. The existing cumulative100USD project cap remains unchanged.

## Current blockers and disposition

Normal seed clears seller02 TOTP, Connect and payout state and rejects gained readiness. Public Connect onboarding/status refuses synthetic actors. Synthetic charge.refunded events are suppressed, despite narrow TEST purchase completion admission. Seed-only activation and narrow signed refund admission are therefore required for the selected seller02/buyer01 test.

The normal refund handler is not sufficient by itself: human refunds leave the transaction unchanged; settlement reaches Transfer without checking linked-order refund/revocation; finance commits before the outer order/event session. These exact-source findings are not a reproduced live incorrect transfer. Mars4085 identifies filed dispute-hold ownership of human refund transition and settlement exclusion, and filed finance ownership of retry-safe processing. Max now authorizes the required corrections through event99af61fd-db46-42fd-a18d-1d0698e457d1, relayed in Mars4096. The earlier filed-work restriction is superseded for these release dependencies. Mars owns build:bq-refund-safe-production-s1714 and its exact design f1a5ccbf9a1d99bba10551da2560a8a98013d0cf at /Users/max/Projects/ai-market/runbooks-s1714-refund-release-spec/specs/BQ-REFUND-SAFE-PRODUCTION-S1714-GATE1.md. His CC/GLM/DeepSeek design review is dispatched. Unrelated filed scopes remain excluded.

This Workspace Gate1 design proceeds alongside that dependency. Product implementation still follows the accepted Gate2 and MP build process; refund admission cannot activate until the accepted normal product correction is deployed and tested. Mars4097 finds the consolidated lock/recovery/deactivation boundary consistent with S1681, conditional on accepted product/acceptance contracts and exact final amendment. This is a technical sequencing dependency, not a missing Max authorization. Vulcan owns Workspace activation/admission; Mars owns general refund/settlement and acceptance redesign. Avoid simultaneous edits to webhooks.py: base the narrow admission patch on Mars's accepted product candidate, or agree an exact isolated patch handoff before integration.

## Trusted fixture and readiness contract

Resolve identities only from packaged e2e/account_pool.json using load_packaged_account_pool_config()/account_pool_entries(). Require exactly one entry for each expected role and secret-name pair, database ID equality, synthetic classification and reserved fixture email equality. Current seller02 is961bd48a-3018-43f4-a7ad-6871720fd806; buyer01 is7d662d0e-22f2-4b87-bbc5-80984ba808ac. Request IDs, runtime registrations, provider metadata or email patterns alone are not identity authority.

Add only a reviewed seller02 TOTP secret-name reference. Generate/store its value through existing test-env custody only after execution authority; never copy seller01's secret or include values in code, receipts or review. The webhook binding requires no password/TOTP values. Public2FA and synthetic Connect guards remain unchanged.

Activation reuses or creates exactly one distinct seller02 TEST Custom Connect account through the established fixture pattern. Verify explicit provider livemode=false, account type, fixture ownership marker, transfers capability and payouts before projecting durable readiness. Refuse ambiguous/duplicate marked accounts, wrong ownership, missing mode and incomplete readiness. Never substitute platform or seller01 accounts. Repeated activation validates the same identity and account without creating another resource.

## Operating interface and exclusion

New bin/workspace-fixture accepts exactly activate, status and deactivate. It accepts no arbitrary user/order IDs, provider account, database URL or broad reset arguments. Status is read-only; it does not acquire/write a lock merely to inspect, repair state or expose credentials.

Write entry uses existing bin/check-settlement --lock with the absolute path of bin/workspace-fixture. The wrapper only accepts a command whose resolved parent is the environment bin directory. Inside inherited lock ownership, the child must invoke unchanged check-settlement --guard seed and stop on **every nonzero exit** before mutation. The new command name is absent from the wrapper's guarded-name set, so checking S1681_LOCK_ENTERED alone is insufficient. Preserve the existing token, ancestor and held-lock validation; an environment variable alone is not authority. A second lock is prohibited.

Preflight may inspect state before locking but must revalidate it under the shared lock. No writes occur before both the explicit Mars window and guard success. Pending purchasing/pending_settlement refuses. Failed lock, wrong ancestor/token, missing owner, timeout or malformed audit fails closed. Never truncate, replace or repair the peer lock yourself. Read-only status may report a transient view and must not claim a mutation-safe snapshot.

Use independent seed/workspace-host.py, not seed/host-seed.py, which also manages S3/serial/device state. Validate exact Compose project/backend identity and only invoke the dedicated seller02 mode. Do not run broad ensure_local_users, bin/seed, S3 fixture uploads, serial enrollment, device-key rotation or checkpoint operations. All new shell subprocesses use rtk. Tests redirect evidence, lock, audit and provider stubs beneath temporary roots; no live defaults.

## Durable audit, recovery and deactivation

Use private atomic .state/workspace-fixture.json with schema/version, accepted pins, phase, fixed identities, provider ownership marker and protected before-state hashes. Retain required restorable non-secret seller02 before-state privately; hashes alone cannot restore it. Keep secrets solely in reviewed custody. Phases are preparing, active, deactivating and inactive. Persist operation identity before provider creation; use stable provider idempotency identity and reconcile that exact owned resource after an interrupted response. A corrupt/unknown/incomplete audit refuses unrelated mutations and reports recovery requirements rather than starting a new operation.

Snapshot seller02 readiness plus protected seller01/buyer01 existing rows and device/trust/serial state. Require post-operation comparison showing only allowed seller02 state, owned provider resources and Workspace audit changed. Default seed/reset must refuse active/inconsistent audit and gained readiness inconsistent with absent/inactive audit. Default seed retains its baseline behavior when no amendment is active. It must not silently normalize an interrupted operation.

Deactivation requires owned Workspace access/resources removed and every new Workspace order in an accepted terminal refund/release state that cannot settle. If this cannot be proven, stop without erasing evidence. Restore captured seller02 state; delete only a newly created TOTP secret whose ownership/version still matches. Never delete preexisting credentials/accounts. A TEST account with financial history is retained with explicit disposition for deterministic reuse unless a reviewed provider rule authorizes deletion. Partial recovery must retain operation identity and permit only the same validated operation to resume under the shared lock.

## Narrow signed refund contract and product integration

After accepted product corrections, admit only authentic charge.refunded platform events through the existing signature and event-idempotency pipeline. Require explicit TEST event/object mode, exact local test predicates and production-shaped configuration refusal. Resolve the existing unambiguous payment-intent/charge, finance Payment, human transaction, order and purchased Workspace authority from persisted records. Require exact seller02/buyer01 ownership, both synthetic flags, no agent-key binding, no device authority, and correct invoice/entity/amount/currency.

Restrict the new allowance to one full refund of a strictly positive integer captured amount matching stored order/payment currency and amount. Reject missing, zero, conflicting, partial or ambiguous values. Reject disputed, transferred/settled or incompatible orders before requesting a new refund. Already accepted duplicate events must follow normal idempotent acknowledgment without duplicate finance/access effects. Existing unrelated nonsynthetic partial-refund semantics remain unchanged.

Only this predicate bypasses synthetic suppression, then normal signed dispatch reaches the accepted normal refund path. Do not invoke private handlers, fabricate events, write order status from seed or backfill finance rows. Use the authorized normal Stripe TEST refund for the exact new Workspace order; record provider refund/event IDs and application/finance outcomes. Provider success alone does not pass. Existing bearer URLs retain expiry semantics; require new-grant refusal, not recall of downloaded bytes.

Require fault injection across finance commit and outer order/event failure, retried and duplicate events, confirmation/refund races and scheduled/direct settlement. Exactly one accepted refund effect/journal and consistent Payment/Refund/order/transaction/event state must result; durable refunded/revoked settlement exclusion must prevent Transfer. Avoiding confirm during the test is insufficient. No payout or Transfer is part of the Workspace refund test.

## S1681 acceptance interaction and ownership

At protected environment03d3f30, browser/s1681-delivery-leg.ts255-257 revokes the delivery order, then267 confirms its transaction and269 expects completed/confirmed before settlement. That old contract conflicts with universal refunded/revoked settlement exclusion. Preserve old run25 as evidence of its original contract only.

A separate Mars/Council-reviewed acceptance redesign must preserve both eligible-order settlement and revocation/refund refusal. Do not remove assertions, clear revocation, exempt fixtures or silently substitute an order. If separate TEST orders are required, specify count, authority and cleanup explicitly. Existing seller01 orders remain protected. This amendment does not expand implementation scope to that harness.

## Proposed exact file allowlist

Environment: bin/workspace-fixture(new), seed/workspace-host.py(new), seed/seed.py, bin/reset, bin/seed, tests/test-workspace-fixture.py(new), tests/test-seed-contract.py, workspace/README.md.

Backend: e2e/account_pool.json; app/api/v1/endpoints/webhooks.py for held narrow admission only; tests/test_workspace_test_refund_admission.py(new); tests/test_e2e_surgical_reset.py for the existing packaged-account-pool contract. Product settlement/transaction/billing/dispute corrections belong to their separately authorized specification and owner.

Runbooks: specs/BQ-MONEY-PATH-TEST-ENV-S1656-GATE1.md (A2 parent), specs/SELLER-WORKSPACE-ACTIVATION-S1712-GATE1.md (this amendment), runbooks/seller-workspace-operator-guide.md and runbooks/seller-workspace-live-release.md. Exact cross-repository implementation pins must be frozen at Gate2; no live acceptance-pin edit here. No changes to check-settlement, device/trust/serial code or S1681 harness under this allowlist.

## Acceptance matrix and gates

1. Default behavior: existing seed/reset tests pass; unauthorized gained readiness still refuses; active/inconsistent amendment cannot be erased by normal seed/reset.
2. Exclusion: pending settlement, held foreign lock, wrong token/ancestor and nonzero guard all cause zero provider/database/secret writes. Temporary-path tests prove no shared defaults are touched. Read-only status does not write a lock/audit.
3. Fixture: correct distinct TEST account projects readiness; live/missing-mode/wrong-marker/type/identity/capability refuses. Repetition and crash-after-provider-response recover the same resource. Protected before/after state matches.
4. Cleanup: resource/access and terminal-order proof precedes restore; mismatched secret version/preexisting account is preserved; interrupted audit and unresolved refund refuse destructive cleanup.
5. Refund negatives: invalid signature, live/production shape, wrong actors, device authority, agent binding, ambiguous/missing finance record, mismatched amount/currency and partial refund cause no new allowed application mutation.
6. Refund positive: normal signed full refund reaches accepted product handler; duplicate/crash/race cases converge without duplicate effects; direct and scheduled settlement cannot transfer; new Workspace grants refuse.
7. Joint live proof: seller02 Workspace and seller01 device co-listing/search, authorized buyer01 checkout, common dispatcher, downloaded byte hash, cross-seller/API-key denials, refund/release and fixture cleanup. Mars confirms exact evidence in his explicit window.
8. Production: accepted product MP build and unanimous CC/GLM/DeepSeek gates, exact source/artifact/deployment identity, outside normal-path verification and rollback readiness. Environment-only code is not deployed as product code.

Gate1 design review binds the authority/owner above and evaluates this interface with the explicitly pending product/acceptance contracts. Gate2 must freeze the resulting exact integration pins/files; unanimous Council and final Mars non-interference approval remain required before implementation/activation as applicable. Gate3 needs exact implementation, applicable regression/adversarial proof and unanimous review. Live activation additionally needs explicit owner window and TEST transaction/refund authority. This document itself satisfies none of those approvals.

## Retained evidence

SELLER-MARS-LATEST-RECOVERED-S1712.json preserves messages4077–4090; SELLER-INTEROP-PR27-MERGE-S1712.json proves the scaffold merge; SELLER-INTEROP-ROUND3-VALIDATION-S1712.json and final doc-correction review status retain validation/votes. SELLER-PRODUCTION-RELEASE-PLAN-S1712.md records production verification/rollback.

Earlier refund/settlement source hashes were verified unchanged at backendd766b8e4: refund function9c29e6e300116aa5e2cdba8f8b0fd61cb3666450b6019a4980034b81cecee567; settlement_service.py161bd06d863c208f0cc1597dcda972138f9214fea9d5b05068cb9152b20532b1; transaction_service.py58749e7c29d022aa7e36d78ff8a63b06579b723043d41558b12a9e65c436c283. Revalidate source identity before final dispatch. Future baselines require a new exact comparison, not automatic reuse of these findings.

## Design review questions and evidence limits

1. Are packaged identity binding and TEST-only provider/refund admission sufficiently strict without weakening public guards?
2. Does the exact shared-lock/inner-guard protocol preserve run25 and fail closed on every error, including lock inheritance and interrupted audit?
3. Are before-state custody, idempotent provider creation, recovery and deactivation sufficient to avoid orphan resources or protected-state loss?
4. Is the interface with Mars's refund/concurrency/acceptance design complete, and which concrete Gate2 integration requirements must precede MP work?
5. Is there a simpler or better design that preserves normal signed refund proof, all protected state and the complete production objective?

Review is design-only. No new implementation tests, provider operations or live proof were performed for this amendment. Source inspection and PR27 validation support only their stated scopes. Return explicit coverage limits and design mandates; do not treat prior scaffold votes as approval of this amendment. Read the named primary artifacts and supporting source as needed. MP remains the product builder.
