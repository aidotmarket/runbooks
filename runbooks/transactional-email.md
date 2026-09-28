---
title: Transactional email from the backend (Resend)
owner: vulcan
last_verified: '2026-09-22'
aliases: [Resend, RESEND_API_KEY, EmailService, send_email, sale notification, order ready email, noreply@ai.market]
error_signatures: ["'EmailService' object has no attribute 'send_seller_sale_notification'", "'EmailService' object has no attribute 'send_order_ready'", "idempotent email provider unavailable", "synthetic-triggered email suppressed"]
---

# Transactional email from the backend (Resend)

## What it is

Every customer-facing system email the ai.market backend sends (verification, password reset, magic links, inquiry notices, lifecycle emails, sale and order emails) goes through one class: `EmailService` in `ai-market-backend/app/services/email_service.py`, obtained with `get_email_service()`. Its single sending entry point is `EmailService.send_email(...)`; every `send_<something>` method builds the subject and HTML/text body and then calls `send_email`.

Provider selection inside `send_email` (verified at backend `1a508f4b`, 2026-09-22):

1. **Resend** when the process environment has `RESEND_API_KEY`. This is the production path. Default sender `ai.market <noreply@ai.market>` (`FROM_NAME = "ai.market"`; callers may override `from_email` / `from_name`).
2. **Gmail API fallback** (`GmailService`) only when `RESEND_API_KEY` is absent. A call that passes an `idempotency_key` refuses the fallback and returns `idempotent email provider unavailable`, because only Resend deduplicates.

Before either provider, `email_send_allowed_for_trigger(to, metadata)` blocks email that a synthetic (`is_test` / reserved-domain) actor would trigger toward a real recipient, returning `synthetic-triggered email suppressed`. New email methods must pass metadata that this guard can evaluate; do not bypass it.

Operator mail (Max's inbox, finance@) is a different system: the Gmail logins checked daily by `gmail_login_<name>` (`backend-daily-health-check.md`). Infisical's own invite/MFA mail also uses Resend SMTP but is configured separately (`infisical-secrets.md`).

## Where the pieces live

| Piece | Location | Verified 2026-09-22 |
| --- | --- | --- |
| API key used by the app | Railway `production` / `ai-market-backend` variable `RESEND_API_KEY` | present (36 chars) |
| Key of record | Infisical backend project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, env `prod`, path `/`, `RESEND_API_KEY` | present; absent in `staging` |
| Sending domain | Resend domain `ai.market`, region `us-east-1` | `verified` (read-only `GET https://api.resend.com/domains`) |
| DNS (DKIM, SPF alignment) | `resend._domainkey.ai.market` and related records | `cloudflare-and-dns.md` |
| Domain health check | SysAdmin capability `resend_domain_status` (`app/services/sysadmin_resend.py`) | `sysadmin.md` |

Read the key only into a shell variable for a request and unset it; never print it. Rotation: rotate in Resend, update Infisical `prod`, then set `RESEND_API_KEY` on the Railway backend service (the variable change redeploys, about 3 minutes; see `ai-market-backend.md`).

## Check that email is working

- Domain: `GET https://api.resend.com/domains` with the key must list `ai.market` as `verified`.
- A specific send: grep backend logs for the method's tag or for `Failed to send`. Email failures in fulfilment and notification code are caught and logged at warning so they never fail the purchase; a missing email therefore shows up only in logs, not as an error to the customer.

## When it breaks

| Symptom | Likely cause | Check / fix |
| --- | --- | --- |
| `'EmailService' object has no attribute 'send_seller_sale_notification'` (or `send_order_ready`) in backend logs after a purchase | The fulfilment code (`app/services/fulfillment_service.py`, `_notify_seller_sale`, `_notify_buyer_ready`) called methods that never existed (since S58, `912c47ea4`). No seller "sale waiting" email and no buyer "order ready" email was ever sent from this path. First seen live 2026-09-22 04:00:20Z on a test order. | Fixed by backend PR #446 (merge `8ce33d27`, deployed 2026-09-22): both methods added, sending via Resend with idempotency keys `seller-sale:<order_id>` / `order-ready:<order_id>`, links `/dashboard/sales` and `/dashboard/orders/<id>`, synthetic suppression via buyer+seller classification. `tests/test_email_service.py::test_every_email_service_send_reference_exists` fails CI if any code calls a `send_*` method EmailService lacks, including through aliases. If this error reappears, the deploy predates `8ce33d27`. |
| A paid-order email never arrives after a Resend outage | Email failure is non-fatal and not retried: the fulfilment state is committed first and a later request short-circuits (`already_pending`) before emailing again | Known gap (Council, PR #446): no durable email outbox yet. Check backend logs for `Failed to send sale notification for order` / `Failed to send order ready notification for order` |
| `idempotent email provider unavailable` | `RESEND_API_KEY` missing from the running service | Confirm the Railway variable; redeploy after setting it |
| `synthetic-triggered email suppressed` | A test account triggered mail to a real address | Expected; a reserved test destination may pass the guard, but that is not proof of mailbox delivery |
| Mail sent but lands in spam / fails DKIM | Resend domain not `verified` or DNS drift | Resend domain status, then `cloudflare-and-dns.md` |

## S1760 recurring test email: candidate source audit (2026-09-28)

**Status:** Backend PR #520 is draft, unreviewed, unmerged and not deployed. This section describes candidate source `1face0df3a4687df1d0a2e572b8b123949b63fb7` against original full base `209780aa4907bda9b42dbb8ae6801e9fd6c69f73`; it does not advance the historical `last_verified` date or claim a live fix. Read the exact path findings in backend `docs/verification/s1760-synthetic-mail-source-audit.md` at that candidate head. Work remains under `build:bq-open-items-triage-s1754`.

**Symptom:** Recurring synthetic inquiry or notification work can send test mail toward a genuine address when a later worker uses a stored recipient without rechecking who caused the work. A test account can have an ordinary real-domain address: `is_test` and reserved-domain classification both matter. For inquiry mail, both persisted buyer and seller matter, even when only one receives the message. Missing actor rows or a failed identity lookup cannot authorize a send. Genuine customer mail and sends to reserved test destinations remain supported when the relevant guard allows them; allowance is not evidence that a mailbox received mail.

| Path | Candidate decision at the send or notification boundary |
| --- | --- |
| Inquiry creation, escalation, followup, seller response and reminders | Re-read both persisted inquiry actors and classify either synthetic origin before cross-recipient mail. Background creation and followup use their own session. Missing context or recipient suppresses; failed lookup does not permit mail. A known synthetic reminder leaves the due set without increasing the sent counter; a failed reminder remains due for retry. |
| Inquiry in-app notification | Re-read buyer and seller through the inquiry ID; missing actor rows suppress the seller task. This is separate from the email guard. |
| Listing version outbox | Re-read current buyer and listing seller, including the buyer's current address, before delivery. A synthetic-to-real entry ends with `failed` / `synthetic_actor` and no `sent_at`; this is terminal suppression, not a sent message. |
| Queued lifecycle mail and signup/attempt notices | Re-read the user for queued mail and classify the notice's subject address. The existing suppressed counter and `sent_at` terminal handling stop suppressed rows. Here `sent_at` can mean terminal processing; it alone does not prove delivery. |
| Beta and partner notices | Look up the persisted account by submitted address before the operator notice. A persisted `is_test` account at a real domain is synthetic; lookup failure sends no notice while retaining the submitted form. |

The existing provider-bound request-match filter and order fulfilment buyer/seller guard remain in place. Request-match in-app synthetic behavior is outside PR #520's repair. `EmailService.send_email` guards both Resend and its fallback; the separate operator Gmail subsystem is outside this path.

### Inspect safe evidence

At the candidate head, the inquiry decision emits only these fixed markers: `inquiry_mail_missing_context`, `inquiry_mail_missing_recipient`, `inquiry_mail_suppressed_synthetic` (`app/services/inquiry_service.py`). Bounded lookup/deferred-send failure markers are `inquiry_service_seller_lookup_failure`, `inquiry_service_reply_lookup_failure`, `inquiry_reminder_lookup_or_send_failure`, `inquiry_background_lookup_or_send_failure` (same file), plus `inquiry_followup_lookup_failure` and `inquiry_reply_lookup_failure` (`app/api/v1/endpoints/inquiries.py`). Read these exact source locations before interpreting logs.

For a classified test run, restrict the Railway backend and applicable worker service logs to the harness receipt's UTC start/end time and exact deployment, then filter `message` to that fixed marker allowlist and return marker counts only. In the Resend provider log view, query the same bounded window and any non-sensitive run tag recorded by that approved harness receipt; return aggregate accepted/rejected counts only. Without a provider-visible run tag, a time-window aggregate cannot attribute messages to the run. Keep raw exception messages, addresses, IDs, request bodies and credentials out of exports and review notes. A zero-marker result does not prove suppression or recovery: it may mean the path did not execute, logging was unavailable, or the wrong deployment was queried. A scheduled job, unchanged inbox, or reserved-destination allowance is likewise insufficient proof. Do not send QA mail to Max, Sergey, or any real recipient.

### Qualification and rollback

The source audit records 136 focused independent tests passing with no skips. Isolated real PostgreSQL passed once at the earlier `f744` exact join/outbox source; final-head PostgreSQL refresh was still in progress when this candidate note was written. Ten unchanged SQLite fixture errors near the PostgreSQL `~` constraint in `test_s1097_version_notifications` remain disclosed; `app/models/marketplace.py` was unchanged. None of these results is deployment or delivery evidence.

Before calling the repair live, require review of this exact source and runbook, a successful deployment receipt for each applicable backend/worker service, actual classified-origin suppression evidence, fake-provider genuine-path regression, and the isolated PostgreSQL result at the final source. Use one docs reviewer while this companion stays within the already approved source scope; the full CC/GLM/DS source-and-companion panel must read the exact package before normal merge and live proof. No blanket guarantee about historical sends or provider delivery follows from these checks.

If the candidate harms genuine mail, roll back the exact deployed candidate, preserve persisted records and outbox evidence, and recheck both classified-origin suppression and the genuine path. Do not hand-delete queued rows, widen test identities, or blanket-disable transactional mail.

## Related

- `ai-market-backend.md` (deploy, Railway variables)
- `infisical-secrets.md` (secret custody; its SMTP section is Infisical's own mail, not the app's)
- `cloudflare-and-dns.md` (mail DNS)
- `runbooks/lifecycle-emails.md` (welcome / day-3 / day-7 series, which use this service)
