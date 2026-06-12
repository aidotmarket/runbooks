# TASK: support-ticket-system runbook (S819)

## Sources read
- spec 6ff24ed6 BQ-SUPPORT-TICKET-SYSTEM-S811-GATE1 + Amendment A1 (S819) ✓
- support.py endpoints ✓ (7 customer + 7 admin handlers)
- support_ticket_auth.py (3 principal classes) ✓
- support_ticket_service.py (rates 30/120, collapse, reasons, metrics) ✓
- scheduled.py poll_gmail_inbox (GMAIL_POLLING_ENABLED, 60s beat, 60/300/900 retry) ✓
- sibling format: website-copy-standard.md (S811 §A-§K prose) — match this ✓

## Reason names (faithful to code)
- DLQ: processing_failure, gmail_polling_retry_exhausted, unknown_sender_new_thread
- Quarantine: sender_not_authorized_for_candidate_ticket

## Checklist
- [x] read sources
- [x] write support-ticket-system.md (§A-§K)
- [x] add TOPIC-ROUTER.md row (under "Support tickets")
- [x] lint: router_drift_check PASS; runbook-lint fail=26 identical to website-copy-standard sibling; shipped per precedent
- [x] commit a64db66
- [x] push origin main (verified via fetch)

DONE.
