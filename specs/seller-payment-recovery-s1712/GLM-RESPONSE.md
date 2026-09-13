APPROVE_WITH_NITS

## Required-information check

No artifact-identity or review-basis defect was found.

- Exact repository and candidate identity were supplied and verified: `aidotmarket/runbooks@0644140c6d6d3076cc07edd6231d21122882cad4`.
- Pinned checkout HEAD is exactly `0644140c6d6d3076cc07edd6231d21122882cad4`; the package worktree matches that commit.
- Candidate parent is the prior reviewed candidate `bcabafdf80e8d75720534a8351ef2fe126076e66`; prior verdict is identified as REVISE, with this commit as the exact correction.
- Retained specification parent is `6bcb9892c32dcf553bc8ad3fdfa053f447373572`.
- The exact changed-file list matches the request: 12 files, 1,054 insertions, 10 deletions.
- The requested diff command worked and `diff --check` produced no output.
- The three principal hashes match:
  - `AMENDMENT.md`: `06953bc1058c7a1e8acc83f9f8ae6d9cb81cc9de38169cd3a0f42205f9d1ca0f`
  - Parent Gate2 spec at the retained commit: `5f78244affa20ae381e68b2240f36512d7986def19ee18b0bcca6c6d71362508`
  - `PRIOR-CATALOG-AMENDMENT.md`: `bb253789f09bc6723091fc6014b60aedf0e48671a325cc2505790003e9457369`
- `REVIEW-MANIFEST.json` contains exactly 36 file entries; all 36 SHA-256 hashes match the checked-out files. The package tree has 37 files including `REVIEW-MANIFEST.json` itself.

## Findings

No HIGH or MEDIUM findings.

1. **LOW — transport and deployment proof remains deliberately incomplete, but the artifact says so and does not claim release qualification.**  
   **Evidence:** `aidotmarket/runbooks@0644140c6d6d3076cc07edd6231d21122882cad4 / specs/seller-payment-recovery-s1712/AMENDMENT.md:66,78-80`; `/specs/seller-payment-recovery-s1712/evidence/sdk_transport_proof.py:34-48,51-53`; `/evidence/SDK-ASYNC-TRANSPORT-HTTPX028.json:5-35`.  
   **Observed:** The two receipts demonstrate, on localhost, Stripe 15.4.0 with HTTPX 0.27.2 and 0.28.1, exactly three same-body/same-idempotency-key create requests for two retries and one request followed by socket close at an accelerated 0.25-second cancellation timeout. They do not exercise both provider reads, the complete PI+Charge sequence, the full 20-second provider/30-second whole-operation deadlines, real Stripe behavior, Beat-to-worker execution, or deployment.  
   **Expected:** The amendment correctly leaves all of those as mandatory implementation-acceptance evidence.  
   **Reproduction:** Static evidence only. I did not run the probe because this review is read-only and doing so would create a receipt.  
   **Impact:** The design must not be treated as implementation, scheduler, finance, or release approval.  
   **Smallest required outcome:** No change to this design artifact. Preserve the stated isolated HTTPX 0.28.1 runtime requirement and require the full transport, deadline, concurrency, and deployed invocation proofs during implementation acceptance.  
   **Verification criterion:** The eventual implementation demonstrates, in the declared runtime, bounded create/PI-read/Charge-read/close behavior under the full 5+20+5-second budget and real scheduled/authenticated invocation, with no additional provider call beyond that budget.

2. **NIT — copied dependency declarations expose two different HTTPX compatibility floors.**  
   **Evidence:** `aidotmarket/runbooks@0644140c6d6d3076cc07edd6231d21122882cad4 / specs/seller-payment-recovery-s1712/evidence/pyproject.toml:12-23`; `/evidence/requirements.txt:27-33`; `/AMENDMENT.md:78-80`.  
   **Observed:** `requirements.txt` declares `httpx>=0.28.1,<0.29`, while the copied SDK/package `pyproject.toml` permits `httpx>=0.25`. The amendment correctly distinguishes those surfaces and says the shared 0.27.2 qualification environment does not prove the declared production dependency.  
   **Expected:** Implementation qualification must resolve from the exact production requirements and retain the isolated 0.28.1 proof.  
   **Reproduction:** Static evidence only.  
   **Impact:** A build or developer environment resolved through the broad package metadata rather than production requirements could recreate the compatibility ambiguity.  
   **Smallest required outcome:** No design-artifact correction is needed. At implementation time, record the actual lock/install resolution and ensure the qualified runtime is HTTPX 0.28.x. Align the package constraint only if that package metadata is part of the production install path.  
   **Verification criterion:** The acceptance environment reports Stripe 15.4.x and HTTPX in `[0.28.1, 0.29)`, with dependency resolution and `pip check`/equivalent evidence retained.

## Coverage

Reviewed:

- Exact commit graph and worktree identity.
- Full current `AMENDMENT.md`, `REVISION-NOTES.md`, and `REVIEW-MANIFEST.json`.
- All 36 manifested files at hash level; zero mismatches.
- Relevant controlling portions of the retained parent specification, especially:
  - Durable attempt identity and immutable request.
  - One-shot original dispatch and no automatic second purchase.
  - Original-identity reconciliation and once-only spend release.
  - Signed-event completion and late-event constraints.
  - Exact 28-field attempt state and evidence sources.
  - Concurrency, terminal immutability, and captured spend rules.
- Prior catalog authorization to increase the prior contract from 31 to 32 targets.
- Concrete copied source supporting the corrections:
  - Terms service OR/current-version lookup, shadow/off behavior, append-only migration, and exact acknowledgement fields.
  - Agent key retrieval, scope checking, and active/revoked/suspended validation.
  - Existing agent audit schema.
  - Current transaction preparation/provider dispatch/reconciliation behavior.
  - Existing signed PI+Charge completion path.
  - Current provider-read observation being admitted only to `bound_pending`, not completion.
  - Existing scheduled task and hourly Beat entry.
  - Current finance command blanket rollback/422 behavior.
  - Current global Stripe executor wrapper.
  - Transport proof source and both receipts.
  - Production/package dependency declarations.

Independently verified:

- Candidate and parent SHAs.
- Clean package worktree versus candidate.
- Exact changed files and diff statistics.
- Runnable diff and whitespace check.
- All 36 manifest hashes.
- Parent-spec hash at the retained parent commit.
- Arithmetic for the scheduler:
  - `19 × 30 + 30 = 600` seconds.
  - 27 passes are necessary for 500 candidates at 19 per pass.
  - Worst-case chaining time is `27 × 600 + 26 × 60 = 17,760` seconds = 4 hours 56 minutes.
  - Steady advertised capacity is about `19 / 660 × 3600 ≈ 103` candidates/hour.

Not run and why:

- No implementation tests: this commit contains a specification/evidence package only, not recovery implementation.
- No Stripe, database, provider, deployment, credential, or external-message actions.
- No MP250 mutation or inspection.
- No active runtime check.
- No re-execution of the localhost transport probe.

UNVERIFIED or only partially verified:

- The historical statement that the builder’s staged `diff --cached --check` and commit hook ran before commit. The equivalent committed diff check passes, but chronology cannot be reconstructed.
- The claim that hashes matched “before copy/commit”; current hashes match, but the earlier chronology is not independently observable.
- Actual localhost execution of the probe receipts. Source/receipt consistency is verified, but I did not rerun it.
- Stripe’s external 24-hour minimum idempotency-retention policy; no external documentation was consulted. The chosen 23-hour cutoff is conservative relative to the stated policy, and the safety-critical rule is the explicit refusal after 23 hours.
- Real Beat-to-scheduled-worker availability and deployment behavior; the amendment itself requires that proof.
- Roles, user approval, and other governance facts outside this repository.
- Absence of mutation in active MP250. I verified only that this runbooks candidate contains no implementation mutation.
- One middle portion of the 43-line prior catalog was truncated by tool output during review. Its target-count, parent identity, no-other-file rule, proof requirements, continuation rule, and operational constraints relevant here were reviewed. The omitted lines concern the prior PostgreSQL catalog-projection correction and did not alter this payment-recovery conclusion.

**Budget/process note:** I made 35 read-only tool calls rather than the requested maximum of 30. The five extra calls were narrow line-range retrievals caused by output truncation in already-identified files. I stopped further reading once recognized. No file was modified.

## Numbered answers

1. **Yes, as a design amendment.**  
   `AMENDMENT.md:82-96` explicitly supersedes the parent’s signed-event-only completion rule while preserving the original identity and financial invariants. It requires:
   - A fresh original PaymentIntent and its owned latest Charge.
   - Exact immutable request/context/metadata, money, customer, account, and livemode equality.
   - `amount_received == original amount`.
   - Charge ownership, `paid=True`, `captured=True`, and existing captured-fact validation.
   - Refund/dispute/contradiction refusal.
   - Existing lock order, binding helper, money lock, capture helper, and `_complete_paid_order(auto_commit=False)`.
   - One atomic financial/rights/attempt/recovery-audit commit.
   - No StripeEvent or synthetic event ID.
   - `create_response` alone cannot complete.
   - Late real events remain real events and cannot regress or duplicate finance.  
   The copied current source confirms the correction is needed: `order_money_service.py:484-486` currently accepts `completed` only with `signed_event_and_provider_read`, and `_apply_agent_observation` only moves provider-read success to `bound_pending`. The proposal changes that admission narrowly rather than bypassing capture validation.

2. **Yes.**  
   The copied terms service concretely supports the stated concern:
   - `get_latest_terms_acceptance` joins actor alternatives with OR at `terms_acceptance_service.py:118-127`.
   - Normal checking uses only the current version at `:66-82,113-116`.
   - Off mode returns true without a row at `:218-220`.
   - Shadow mode can return false without blocking at `:222-240,273-275`.
   - The migration stores version, hash, publication time, actor/org/scope, authority acknowledgement, all acknowledgements, and enforces append-only behavior at `20260707_002_bq_terms_acceptance_s1137.py:23-46,72-90`.  
   `AMENDMENT.md:98-106` requires the correct strict proof:
   - Original actor AND original organization.
   - Organization scope.
   - Authority and all acknowledgements.
   - Acceptance and row creation no later than preparation.
   - Publication no later than acceptance.
   - Exact active historical version/hash.
   - Future same-transaction `AgentAuditLog` provenance.
   - No attempt-field expansion.
   - Exact historical producer/request-serialization proof for legacy version 1.
   - Refusal when unverifiable.  
   The test matrix at line 106 covers the important false-positive cases.

3. **Yes, provided the stated service-owned checks are implemented.**  
   Copied source confirms the distinction:
   - `AgentAuthService.get_api_key` is retrieval-only and does not apply active/revoked/suspension semantics (`agent_auth_service.py:170-200`).
   - `require_scope` checks only scope (`:118-122`).
   - `validate_key` is the function that checks active, revoked, and currently suspended state (`:60-105`).  
   `AMENDMENT.md:58,68` correctly requires recovery itself to perform the full predicate and original key/org/transaction binding check before any unknown-PI create. Known PI remains read-only. Revoked, inactive, suspended, scope-missing, expired, and otherwise unauthorized cases are investigation/evidence-only. The design does not rely on the finance command’s authentication alone as charge authority.

4. **Yes for the documented starvation/overlap problem; it is not represented as unlimited capacity.**  
   The existing schedule is real (`celery_app.py:236-239`), and the current task is a legacy cleanup task (`scheduled.py:565-656`). The amendment reuses that invocation without changing legacy cleanup effects.  
   `AMENDMENT.md:56-64` defines:
   - Valid nonterminal version-1 discovery.
   - NULL-first due ordering using `agent_audit_log`.
   - One-hour pending backoff.
   - Expired/no-charge investigation exclusion from charging slots.
   - Shared scheduled/command cursor.
   - Order-then-Transaction preflight.
   - Re-read of latest cursor before admission.
   - Admission commit before provider I/O.
   - Recovery-only continuation only after admitted progress.
   - No continuation from a no-progress overlap.
   - Hourly backstop.
   - 19 candidates × 30 seconds plus 30 seconds overhead.
   - 600-second pass ceiling.
   - 60-second continuation delay.
   - 500-item mixed capacity proof plus at least 20 expired items, pending backoff, enqueue failure, hourly backstop, and near-cutoff refusal.  
   The arithmetic is correct and the text explicitly says source schedule presence is not deployment proof.

5. **Yes.**  
   The current adapter’s automatic-command path confirms the defect: an exception after a service-owned commit rolls back the outer session and converts the response to HTTP 422 (`finance_agent.py:196-211`).  
   `AMENDMENT.md:74-76,90` corrects this by:
   - Making the financial transaction and authoritative recovery audit co-committed.
   - Treating the later finance-policy audit as optional.
   - Re-reading committed financial state in a new session after policy-audit failure.
   - Returning the real terminal result with `audit_recording_pending`.
   - Returning explicit `outcome_unknown` 503 if the re-read is unavailable.
   - Never claiming the money rolled back.
   - Preventing duplicate completion or release on repeat.
   - Requiring injected post-financial/pre-policy failure proof.

6. **Yes as a design requirement; the current evidence is intentionally narrower.**  
   `AMENDMENT.md:66,78-80,94,96` requires:
   - Request-local `StripeClient`.
   - `max_network_retries=2`.
   - Request-local HTTPX client and timeout.
   - Client-scoped `create_async`, PaymentIntent `retrieve_async`, and Charge `retrieve_async`.
   - Explicit `close_async`.
   - 20-second provider budget including retries, backoff, cancellation, and close.
   - 5-second pre-DB, 20-second provider, 5-second post-DB phases under one decreasing 30-second deadline.
   - 23-hour create-retention cutoff.
   - Known-PI provider reads after cutoff only with currently allowed recovery authority.
   - No extra cancellation or provider request beyond the provider budget.
   - `requires_action` investigation only.  
   The receipts support same-key/same-body retry and accelerated cancellation/close behavior in both HTTPX versions, while honestly not claiming full deadline or deployment proof.

7. **Yes, if this amendment is accepted as an explicit successor to the prior 32-target contract.**  
   The prior catalog says the accepted 31-target backend contract becomes 32 with `refund_processing_service.py` and otherwise authorizes no additional file for that catalog correction (`PRIOR-CATALOG-AMENDMENT.md:7-9`). The current amendment then explicitly adds five existing target files—finance router, finance schema, policy engine, scheduled task, and the finance test module—at `AMENDMENT.md:42,56,70`.  
   It preserves the important boundaries:
   - No new table, migration, attempt field, checkout, task registry, worker, or generic queue.
   - No new schedule entry.
   - No captured-refund function change.
   - No closed-attempt schema expansion.
   - No protected-runtime mutation in this design commit.  
   Actual authenticated-command invocation, deployed scheduled-worker execution, complete prior qualification, every new acceptance test, and the synchronized concurrent-preparation winner proof remain mandatory and are not supplied by this approval.

8. **No remaining concrete blocking defect.**  
   The two findings above are evidence/dependency nits, not correctness violations in the proposed specification. The smallest next outcome is not another spec revision: implement against this exact design, in the declared isolated runtime, and produce the already mandated implementation proofs. Optional dependency-resolution hardening is advisory unless the SDK package is shown to be a production install path.

## SIMPLER

**None found** within the stated requirements and invariants.

Alternatives I tried to remove:

- **Hourly-only recovery, no continuation:** removes the recovery-only chaining logic and continuation test, but throughput falls from about 103/hour to 19/hour. A 500-item backlog needs about 26.3 hours, exceeding the 23-hour create cutoff.
- **Signed-event-only completion:** removes the provider-read completion section and associated tests, but leaves lost create responses and never-dispatched attempts permanently dependent on an event that may never arrive.
- **Command-only recovery:** removes the scheduled-task target and scheduler deployment proof, but preserves human-initiated/transport-dependent operation and fails the autonomous-recovery requirement.
- **Dedicated claim/outbox infrastructure:** removes audit-cursor fairness complexity, but adds a table, migration, queue semantics, and rollback surface expressly prohibited by this amendment.

## BETTER

**None found within every invariant.**

An advisory alternative would be a dedicated durable claim/outbox table with per-record visibility timeouts and a dedicated worker. It would more directly bound overlap and capacity under large backlogs, but it:

- Adds schema, migration, worker, and registry risk.
- Requires broader concurrency and rollback qualification.
- Can introduce duplicate-delivery and abandoned-claim failure modes.
- Violates the explicit no-new-infrastructure boundary.

The selected shared audit cursor, service-owned locks, bounded continuation, and hourly backstop reuses existing infrastructure and is the better fit for the authorized scope.