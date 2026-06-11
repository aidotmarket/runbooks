# Support Ticket System — operations

## §A. Header
**Owner surface:** ai.market support/trouble ticket engine (ai-market-backend `app/api/v1/endpoints/support.py`, `app/services/support_ticket_service.py`, `app/api/v1/dependencies/support_ticket_auth.py`, `app/tasks/scheduled.py`). One ticket system for dev, ops, and customer issues, operated by agents with human escalation on risk.
**Spec source of truth:** `specs/BQ-SUPPORT-TICKET-SYSTEM-S811-GATE1.md` (Gate 1 design + Gate 2 R1 changelog + **Amendment A1 / S819** schema reconciliation). Do not relitigate the decision record in §2/§14 of that spec.
**Last verified live:** 2026-06-11 (S819). Production deploy signal: the alembic fields on `api.ai.market/health` show the support + email-durability migrations at head.

## §B. Capability Matrix
**Live as of 2026-06-11:**
- Core engine tables: `support_ticket`, `support_message`, `support_rate_counter`.
- Customer/agent API behind auth at `/api/v1/support/*` (create, list, read, patch, message tickets).
- Email durability tables: `support_email_dlq`, `support_email_quarantine`.
- Seven internal-only admin endpoints: metrics, DLQ list/retry/drop, quarantine list/release/drop.
- Celery email-intake task with transient-retry backoff and per-message failure capture into the DLQ.

**NOT live (Phase 2+ / in flight):**
- Agent skills (triage_ticket, suggest_resolution) — shadow-mode design only, not shipped.
- Admin UI (`/admin/tickets` queue) — endpoints exist; no console.
- Customer surfaces — allAI ticket-status cards and in-app notifications not shipped.
- Search upgrade — in flight as chunk **C3a**; MVP search is Postgres FTS only.
- **Email polling is switched OFF** (`GMAIL_POLLING_ENABLED=False`); the poller is a break-glass fallback, not the canonical path.

## §C. Architecture & Interactions
A ticket (`support_ticket`) holds a thread of `support_message` rows. Every requester is keyed by `requester_key` = `COALESCE(party_id, actor_type:actor_id)`; rate limits and duplicate collapse are enforced on that key. Email arriving at support@ai.market is parsed by `process_support_inbound_email`, which either attaches a message to an existing ticket, opens a new one, or — when intake is unsafe — writes a durable row to `support_email_dlq` (lost/unprocessable mail) or `support_email_quarantine` (sender/ticket mismatch) instead of silently dropping or mis-attaching. CRM/allAI surfaces read denormalized ticket metadata; they do not infer ticket state from message bodies. The customer-data surface (endpoints + email durability, chunks C2 + C2b) passed one unanimous Gate 3 over the combined diff.

## §D. Agent Capability Map
Either Vulcan instance operates this runbook. Admin triage (DLQ/quarantine review) is internal-only — it requires the internal API key principal (§E auth model), never a customer or external-agent key. Schema changes to any support table require **MP schema review before dispatch** (schema gate, per Amendment A1) and must check `alembic heads` for multiple heads first. The `GMAIL_POLLING_ENABLED` flip is a **Max-gated** ops step, not an agent decision.

## §E. Operate

### Auth model — three principal classes (`get_support_principal`)
All `/api/v1/support/*` ticket and message routes resolve a `SupportPrincipal`. There are exactly three ways to authenticate, tried in this order:
1. **User JWT** (`Authorization: Bearer`) — token decoded, user confirmed active, then mapped to a party via `party_identity` (provider `auth_user`, external_id = user id). `is_internal=False`. This is the web/allAI customer.
2. **Internal API key** (`X-Internal-API-Key`, constant-time compared to `INTERNAL_API_KEY`) — `is_internal=True`, no party. This is the only principal that may run admin triage, read internal messages, PATCH tickets, and post `direction='internal'` messages.
3. **Scoped agent API key** (`X-API-Key`) — validated by `AgentAuthService`, requires scope `support:read`; party_id = the key's org. `is_internal=False` (external agent — a customer-class principal).

Visibility rules:
- **Customers see only their own tickets.** `scope_tickets_to_user` restricts every ticket/message read to `requester_party_id = principal.party_id` OR an active ticket-scoped role binding (below).
- **Internal-direction messages are invisible to customers.** Message reads for any non-internal principal carry `direction <> 'internal'`, regardless of org membership.
- **Ticket-scoped role binding.** Per-ticket access for a non-owner is granted only by a `party_role_binding` row with `revoked_at IS NULL` and `role = 'support_ticket:<ticket-uuid>'`, whose `context_party_id` matches the ticket's `org_party_id` (or both NULL). Generic org/marketplace/seller/buyer roles never grant support access. Time-window (`starts_at/ends_at`) semantics are out of scope on the real schema.
- **Namespace reservation:** `role` values shaped `<resource_type>:<uuid>` are reserved resource-scoped bindings. The `support_ticket:` prefix is owned by this system. Any consumer minting a new `<prefix>:<uuid>` role MUST register the prefix in spec §A1.1 first.

### Customer/agent endpoints (`/api/v1/support`)
- `POST /tickets` — create (internal principal may set requester on behalf of a party; otherwise requester = caller's party). 429 on rate-limit rejection.
- `GET /tickets` (filters: status, issue_class, party, q, limit/offset), `GET /tickets/{public_ref}`, `GET /tickets/mine` (customer-scoped; rejects internal/party-less callers).
- `PATCH /tickets/{public_ref}` (status/assignee/priority) — **internal only**.
- `GET /tickets/{public_ref}/messages`, `POST /tickets/{public_ref}/messages` — customers may only post `direction='inbound'`; `internal` direction requires the internal principal.

### Rate limits & duplicate collapse
- **30 tickets/hour and 120 messages/hour per `requester_key`.** Enforced inside the create transaction: a single `INSERT ... ON CONFLICT DO UPDATE ... RETURNING count` on `support_rate_counter`; if the returned count exceeds the limit the transaction is rolled back and the request gets **429**.
- **Duplicate-subject collapse.** On create the service computes `subject_hash = sha256(normalized subject)`, `requester_key`, and the UTC-hour `collapse_window_start`. Within the same transaction it does a 1-hour lookback for an open ticket (status NOT IN resolved/closed) with the same hash+key; if found it folds into that ticket. The unique partial index `(subject_hash, requester_key, collapse_window_start) WHERE status NOT IN ('resolved','closed')` + `ON CONFLICT DO UPDATE` makes same-bucket concurrent creates atomic.
- **`collapsed=true` means** the create did not mint a new ticket — it returned an existing open ticket for the same normalized subject in the window, with `updated_at` bumped. Collapse is an abuse control, **not** an exactness guarantee: two creates racing across an hour boundary can produce two tickets. That cross-boundary race is an **accepted residual** — do NOT add sliding-window locking for it.

## §F. Isolate — admin triage procedures

### Email durability metrics
`GET /api/v1/support/email-durability/metrics` (internal only) returns, per source (`dlq`, `quarantine`), `pending_count` and `oldest_pending_age_seconds`. This is the primary backlog signal for both tables.

### DLQ — lost / unprocessable mail (`support_email_dlq`)
Rows are created by the intake path with one of three **reasons**:
- `processing_failure` — a fetched message failed during per-message processing in the poll loop; that one message is captured and the loop continues (a poll run is never aborted by a single bad message).
- `gmail_polling_retry_exhausted` — a transient Gmail fetch/list failure (429, 5xx, timeout, connection reset) survived all three backoff retries; the whole poll run is parked.
- `unknown_sender_new_thread` — an email on a new thread whose sender could not be resolved to any party; no ticket is created.

Triage:
- **List:** `GET /email-dlq?status=pending` (default pending; `retried`/`dropped` also queryable).
- **Retry:** `POST /email-dlq/{row_id}/retry` — marks the row `retried` and records the reviewer. Acts on `pending` rows only (404 otherwise). Use after the underlying cause (Gmail auth/quota, a sender now mapped to a party) is fixed.
- **Mark dropped:** `POST /email-dlq/{row_id}/drop` — marks `dropped` (pending only). Use for permanent junk / unrecoverable mail.

### Quarantine — sender/ticket mismatch (`support_email_quarantine`)
One **reason**: `sender_not_authorized_for_candidate_ticket`. An inbound email named a candidate ticket (via `[T-ref]` subject or References/In-Reply-To headers) but the resolved sender party did NOT equal the ticket's `requester_party_id` (or the ticket had no requester party). Routing hints alone never authorize attachment, so the message is quarantined and **no `support_message` is created**.

Triage:
- **List:** `GET /email-quarantine?status=pending`.
- **Release:** `POST /email-quarantine/{row_id}/release` with a JSON body `{"body_text": "..."}`. The body text **must be supplied** (the raw email body is not stored on the quarantine row). Release attaches **exactly one** inbound message to the candidate ticket using the resolved sender party and the Gmail message id (so re-release is idempotent — an already-`released` row returns without re-attaching), then marks the row `released`. Requires a non-null `candidate_ticket_id` and `pending` status.
- **Drop:** `POST /email-quarantine/{row_id}/drop` — marks `dropped` (pending only). Use for spoofing / wrong-recipient / abuse.

## §G. Repair — email intake go-live procedure
Email polling is **OFF** today (`GMAIL_POLLING_ENABLED=False`); the canonical path is the push webhook, and the poller is a break-glass fallback. Turning intake on:
1. **Max gate.** Flipping `GMAIL_POLLING_ENABLED=True` is a Max-approved ops step. Do not flip it autonomously.
2. **Mailbox prerequisites.** support@ai.market in Google Workspace; a `SUPPORT-INBOX` Gmail label rule on mail addressed to support@ai.market. **Label-gap behavior:** the intake does NOT depend on the label alone — a message addressed to support@ai.market but missing `SUPPORT-INBOX` is still processed, and emits a `support_email_label_gap` warning (message id + thread id) so the mailbox rule can be repaired. A missing label degrades observability, not delivery.
3. **Beat cadence.** `poll_gmail_inbox` runs on Celery beat every 60s (soft limit 50s, hard 55s, max 3 retries). When disabled it returns `{status: disabled}` and does no work.
4. **Monitoring signals after flip:**
   - **Stale-poll alert** — no successful poll in 10 minutes (poll heartbeat). This is *not* the only dropped-mail signal — DLQ rows catch what a live poll mishandles.
   - **DLQ/quarantine pending count + oldest age** via the metrics endpoint (§F). Watch `gmail_polling_retry_exhausted` rows specifically — they mean Gmail itself is degraded (auth/quota/5xx).

Transient-retry mechanics: transient Gmail errors retry at ~60s / 300s / 900s (base + jitter) before a `gmail_polling_retry_exhausted` DLQ row is written.

## §H. Evolve
Schema changes to any support table require MP schema review before dispatch and a single Alembic head (`alembic heads`; merge first if multiple). The §4.1 authorization predicate is bound to the **real** `party_role_binding` schema via Amendment A1 — any future predicate change updates spec §A1.1, not just code. Phase 2 brings the Support Steward agent, automated low-risk resolution send, portal-pages decision, and `ticket_link`/audit tables if volume proves need. Dev-class tickets carry full payload detail and are searchable but **never** auto-create build-queue entities — promotion is an explicit human/Steward action.

## §I. Acceptance Criteria
This runbook is correct when: the three principal classes and their visibility rules match `support_ticket_auth.py`; the seven admin endpoints and their internal-only guard match `support.py`; DLQ/quarantine reasons match the strings emitted in `support_ticket_service.py` and `scheduled.py`; the rate limits read 30 tickets/hour and 120 messages/hour; `collapsed` is described as fold-into-existing with the cross-boundary race called an accepted residual; and the go-live section states that polling is Max-gated and currently off.

## §J. Lifecycle
Created S819 (2026-06-11) covering the BQ-SUPPORT-TICKET-SYSTEM-S811 MVP engine + Amendment A1 email-durability chunk C2b. Refresh triggers: email intake go-live (`GMAIL_POLLING_ENABLED` flip), admin UI ship, agent skills leaving shadow mode, the C3a search upgrade landing, or any change to the auth predicate / rate limits / collapse semantics.

## §K. Conformance
Registered in TOPIC-ROUTER.md under "Support tickets". `scripts/router_drift_check.py` enforces the link. Structurally complete to the §A–§K standard; lint pending the known linter date-field defect that is consistent across sibling §A–§K runbooks (shipped per sibling precedent).
