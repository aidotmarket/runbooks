# BQ-DATA-VERIFICATION-S1590 — Gate 3 record, Chunk 5 (AIM Data seller flow + shared-fixture contract fold)

**Session:** S1597 (mars). **Repository:** aim-data. **Builder:** MP (excluded from review). **Panel:** CC + Kimi + GLM (CORE S3 full panel — customer-data wire + payments-adjacent seller flow).

**Base:** `29f1575de9439bef00333bbdc712ed580dd2f9c9` (origin/main). **Approved head:** `24264417bb21d373324b43e81c31e5c847f309da`. **Merged to main:** `cfd7382aac33fa5c1ade0d69f8e87653553ec73b` (--no-ff). **Alembic:** single head `024_bq_data_verification_s1590` verified on the merged tree. Everything ships disabled behind `DATA_VERIFICATION_ENABLED`.

## Round history

| Round | Head | Verdicts |
| --- | --- | --- |
| R1 | f7a8a2ee | GLM REQUEST_CHANGES (HIGH incomplete captured-review render; M badge stub/withdrawal marker; M consent-before-quote + dead manifest link; M disabled-flag fail-open reads; M client idempotency; LOW dropped fixture receipt assertion). Kimi APPROVE_WITH_MANDATES (M1 evidence-integrity — resolved: the reviewer backend checkout was a stale working tree at 977e5802 while origin/main was 3286e0726; M2 fabricated probe objects_discovered=1). CC blocked (expired OAuth credential; repaired by Max interactive login per cc-machine-identity.md). |
| R2 | 3bc7d4d8d | CC APPROVE_WITH_NITS (full-chunk, R1-equivalent). GLM REQUEST_CHANGES (HIGH publish-unseen-narrative — backend transports only narrative_state; M withdrawal Date-header fragility; M claim-flag restart wedge). Kimi REQUEST_CHANGES (M claim wedge, convergent). |
| R3 | 0e0879728 | CC APPROVE_WITH_NITS, Kimi APPROVE_WITH_NITS, GLM REQUEST_CHANGES (single M: live-owner ingest overtake after fixed 5s claim wait, dynamically reproduced ingest_calls=2). |
| R4 | cbf6eb941 | GLM APPROVE_WITH_NITS (its M dynamically re-tested, discharged by the durable owner lease). Kimi APPROVE_WITH_NITS. CC REQUEST_CHANGES (single M, TEST-ONLY: flaky keystone lease regression could miss a mid-ingest steal). |
| R5 | 24264417b | CC APPROVE clean on the test-only diff (widened lease/heartbeat/ingest timing, robust no-lease-loss + one-ingest assertions, 200/200 determinism). GLM/Kimi R4 verdicts banked — production code byte-identical. **Unanimous approval-class, zero open HIGH/MEDIUM.** |

Final responses: CC R5 `/Users/max/council/cc/response-20260823-002220-477647.md`; GLM R4 `/Users/max/council/glm/response-20260822-233511-389534.md`; Kimi R4 `/Users/max/council/kimi/response-20260822-233515-335482.md`. Full round records on the Build Queue entity `build:bq-data-verification-s1590` (`body.gate3_chunk5`).

## What shipped

Seller-facing verification flow on the AIM Data dataset detail page: curated enum-only D6 picker (Gate 2 s6.1 vocabulary verbatim, no free text), probe+quote displayed before two separate never-prechecked acknowledgements, in-app approved-manifest field list, complete captured-review renderer (all aggregate families incl. suppressed-sentinel rendering, coverage + keyed skips, exact timestamp, charged amount), publish blocked until grounded narrative text is transportable (binding Chunk 6 contract requirement), equal publish/decline, dated 30-day withdrawal marker with durable date recovery, rerun preserving the active publication, durable start-orchestration lease (owner heartbeat/expiry) giving idempotent restart/concurrency, honest probe enumeration, fail-closed disabled-flag reads, and the shared-fixture contract fold: aim-data fixtures byte-identical to backend `3286e0726` (report a586f353…, scan_spec 2c4b1288…, hostile_reports 391b3a67…), canonicalization reconciled to `python-json-sort-compact-v1`, plus `lifecycle_client_contract.json` fixing client routes and Chunk 6 contract requirements.

## Carried non-blocking items

On the BQ entity `gate3_chunk5.nonblocking_carried`: soft-lease exactly-once documentation (server verification_id idempotency backstop); unbounded waiter poll advisory; binding Chunk 6 contract requirements (display-safe narrative + listing_claim_comparison in ingest/status; explicit withdrawn_at_utc in PaymentLifecycleStatus; backend schema_digests cross-reference update; report-ingest path/terminal-error shape acceptance); S3-pinned archive member enumeration; and the builder secret-scan push-bypass control-integrity evidence (instances 3–5 this session; systemic fix belongs to a builder-controls BQ).
