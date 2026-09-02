# BQ-DATA-VERIFICATION-S1590 — Just-in-time paid-service card amendment

**Authority:** Max, S1646, 2026-09-02: “I only want to require a card if they use one of our paid services.”

**Parent authorities:** `BQ-DATA-VERIFICATION-S1590-GATE1.md`, `BQ-DATA-VERIFICATION-S1590-GATE2.md`, and `BQ-DATA-VERIFICATION-S1590-PAYIN-ONBOARDING-AMENDMENT.md`.

## 1. Business rule

An ai.market or AIM Data user must not be asked to add a card merely to register, sell data, configure payouts, browse, publish an unpaid listing, or use any other unpaid feature.

A debit or credit card may be requested only after the authenticated user deliberately chooses a paid service. For Slice 1 data verification, the paid-service boundary is the seller's explicit action after the free local probe, returned quote, maximum-hold disclosure, and separate publication/corpus acknowledgements.

This amendment supersedes only the prior onboarding amendment's use of general **Settings** as the payment-method discoverability seam. All payment, privacy, authorization, capture, cancellation, publication, and Stripe-hosting controls remain binding.

## 2. Required just-in-time behavior

1. General ai.market **Settings** does not call payment readiness, advertise a verification card, or link to card setup.
2. AIM Data continues to offer the free probe and quote without a card.
3. The quote clearly labels the service as paid, shows the maximum card hold, and requires the existing separate acknowledgements.
4. Only when the seller selects **Accept maximum hold and start paid verification** does AIM Data check the authenticated seller's ordinary pay-in readiness.
5. If readiness is `ready`, the existing manual-capture authorization and scan-spec lifecycle proceeds unchanged.
6. If readiness is `setup_required` or `setup_pending`, no acknowledgement is persisted, no start claim is taken, no verification epoch or PaymentIntent is created, and no scan begins. AIM Data explains that a card is needed only for this paid verification and opens the existing ai.market Stripe-hosted setup in a new top-level browser context.
7. If readiness is `blocked`, the paid action fails closed with fixed support copy and no payment or scan effect. If the readiness contract is invalid, the action fails closed with a fixed generic invalid-response error and no payment or scan effect.
8. After Stripe-hosted setup succeeds, the seller returns to AIM Data and explicitly selects the paid start action again. The readiness check must return `ready` before authorization can begin.

## 3. Unchanged financial and security contract

- Paid data verification remains a card-based `$1–$25` manual-capture authorization followed by capture of the permitted final amount.
- Setup remains Stripe-hosted; ai.market and AIM Data render no card fields and receive no card or billing values.
- A Stripe Connect payout bank account remains separate and is never treated as debit authority or pay-in readiness.
- No charge occurs during card setup.
- Existing finalized cards may remain attached, but they impose no requirement or effect on unpaid use.
- This amendment does not add bank debit, invoices, subscriptions, a general wallet, or any new paid service.

## 4. Acceptance evidence

- General Settings contains no payment-method heading or management link and performs no readiness request.
- The free probe and quote complete with no card.
- Before explicit paid start, no card prompt is present.
- A no-card paid-start attempt returns the fixed just-in-time setup state with zero persisted acknowledgement, start claim, verification identity, PaymentIntent, charge, or scan.
- After readiness changes to `ready`, retrying the same paid action proceeds once through the existing idempotent lifecycle.
- Direct or ineligible access remains fail-closed and exposes no Stripe identifiers or provider error details.
- Frontend and service tests cover the fresh `setup_required` path, `ready` retry, claimed-start recovery, malformed readiness rejection, and unchanged captured-result behavior. The typed `setup_pending` and `blocked` UI branches remain fail-closed in source.

## 5. Release and rollback

Ship the AIM Data just-in-time prompt and the ai.market Settings removal as one reviewed product change. The dedicated hosted setup route remains available for the paid-service handoff.

If the just-in-time path is unsafe or incomplete, disable data verification first and pay-in onboarding second. Do not restore proactive general-Settings card solicitation as a rollback.
