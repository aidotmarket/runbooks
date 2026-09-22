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
| `synthetic-triggered email suppressed` | A test account triggered mail to a real address | Expected; test mail to reserved-domain addresses still sends |
| Mail sent but lands in spam / fails DKIM | Resend domain not `verified` or DNS drift | Resend domain status, then `cloudflare-and-dns.md` |

## Related

- `ai-market-backend.md` (deploy, Railway variables)
- `infisical-secrets.md` (secret custody; its SMTP section is Infisical's own mail, not the app's)
- `cloudflare-and-dns.md` (mail DNS)
- `runbooks/lifecycle-emails.md` (welcome / day-3 / day-7 series, which use this service)
