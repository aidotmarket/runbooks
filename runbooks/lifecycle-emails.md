---
runbook_id: lifecycle-emails
domain: ai-market-backend
status: DRAFT
authoritative_for: []
aliases: []
error_signatures:
  - signature: "operator does not exist: userstatus = character varying"
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-08-20
system_name: lifecycle-emails
purpose_sentence: Discovery-only lifecycle-email task, selection, outbox, suppression, retry, unsubscribe, and recovery reference for the S1548 backend candidate.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: None while DRAFT; this page records the exact S1548 candidate behavior and post-deploy evidence gaps but authorizes no task execution, deployment, rollback, or production claim.
linter_version: 1.0.0
---

# Lifecycle Emails

## §A. Header

This is a non-authoritative DRAFT for Build Queue item
`build:bq-signup-lifecycle-emails-s1548`. It is grounded in exact
`aidotmarket/ai-market-backend` candidate and production target
`77dae96fd8a80fe768091061bc3846fb1b5e8d55`. Live deployment of that exact SHA
and a successful live sweep are **UNKNOWN**, awaiting Vulcan post-deploy
evidence.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Scheduled claim and drain tasks | PARTIAL | `app/core/celery_app.py; app/tasks/lifecycle_emails.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | `tests/test_s1548_lifecycle_emails_phase_b.py; tests/test_s1548_lifecycle_emails_phase_d.py` | 2026-08-20 |
| Idempotent outbox, suppression, and retry boundary | PARTIAL | `app/models/lifecycle_email_send.py; app/services/lifecycle_email_claims.py; app/tasks/lifecycle_emails.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | `tests/test_s1548_lifecycle_emails_phase_b.py; tests/test_s1548_lifecycle_emails_phase_d.py` | 2026-08-20 |
| Signed lifecycle unsubscribe | PARTIAL | `app/api/v1/endpoints/lifecycle_emails.py; app/services/lifecycle_email_unsubscribe.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | `tests/test_s1548_lifecycle_emails_phase_d.py` | 2026-08-20 |
| Signup and attempt selection | PARTIAL | `app/tasks/lifecycle_emails.py; app/api/v1/endpoints/ops_signups.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | `tests/test_s1548_lifecycle_emails_phase_b.py; tests/test_s1548_ops_signups_phase_c.py` | 2026-08-20 |
| Exact production deployment and live sweep | PLANNED | `aidotmarket/ai-market-backend@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | `UNKNOWN - awaiting Vulcan post-deploy evidence` | 2026-08-20 |

`PARTIAL` means the behavior is present in the exact candidate and has focused
test coverage; it does not claim that this runbook work reran those backend
tests or that production is serving the candidate.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Attempt selection | `lifecycle_emails.attempt_sweep` | `users`; `beta_signups`; `lifecycle_email_sends` | Celery beat; emails queue | Hourly at minute 35. Password users must be unverified, older than one hour, and after the configured verification-enforcement cutoff; beta signups qualify only when no case-insensitive matching user exists. Claims are inserted with conflict ignored. |
| Daily sweep selection | `lifecycle_emails.daily_sweep` | `users`; `listings`; `notification_preferences`; `lifecycle_email_sends` | Celery beat; emails queue | Daily at 15:00 UTC. Day-3/day-7 use catch-up age predicates and exclude an existing claim. |
| Outbox drain | `lifecycle_emails.drain_outbox` | `lifecycle_email_sends` | Celery beat; emails queue; existing email service | Every 300 seconds. Claim rows commit before delivery; the drain locks and sends claimed rows, then stamps `sent_at`. |
| Lifecycle unsubscribe | `GET /api/v1/emails/lifecycle/unsubscribe` | `notification_preferences` | Signed purpose-scoped token | Idempotently merges `{"lifecycle_emails":{"enabled":false}}`; invalid signatures write nothing. |

Daily selection requires a verified, active user and suppresses test/synthetic
users, the configured synthetic email domain, any existing send claim, and any
of the supported lifecycle opt-out flags (`enabled`, `email_enabled`, or
`email` set to false). Day-3 additionally suppresses a user only when Stripe
onboarding is `complete` **and** the user owns at least one listing. Day-7 has
no Stripe-plus-listing completion suppression.

`lifecycle_email_sends` is both the idempotency record and the delivery outbox.
Selection/capture creates a claim with `sent_at` unset and commits it before
network delivery. The drain owns delivery and final status; a sweep never sends
mail directly.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Verify exact production SHA and observe scheduled task results | Read-only deployment identity and sanitized task evidence | Read-only until a separately reviewed deployment or rollback is authorized | PARTIAL — exact deployment and successful live sweep remain UNKNOWN |

## §E. Operate

```yaml operate
[]
```

The operate form is intentionally empty because this DRAFT grants no production
authority. The registered schedules are:

- `lifecycle_emails.drain_outbox`: every 300 seconds.
- `lifecycle_emails.attempt_sweep`: hourly at minute 35.
- `lifecycle_emails.daily_sweep`: daily at 15:00 UTC.

Retained operator evidence is counts-only: task name, time, exact deployed SHA,
and aggregate `selected`, `claimed`, `sent`, `failed`, `suppressed`, and
`stuck_visible` counts as applicable. Do not retain recipient addresses, user
or outbox identifiers, signed tokens, email content, or per-recipient payloads.
A fixed sanitized failure signature may be retained for diagnosis.

Failed sends are deferred for six hours. Once a claim is older than 24 hours,
the drain makes at most one stuck retry, reserving that retry by incrementing
`attempt_count` before the network call. An unsent row with that retry already
reserved remains visible and is not reclaimed again.

The constants `LIFECYCLE_HOLD_UNTIL = 2026-08-18T20:00:00Z` and
`LIFECYCLE_LAUNCH_CUTOFF = 2026-08-16T00:00:00Z` describe expired historical
behavior. Before the hold expired, day-3/day-7 catch-up excluded users created
before the launch cutoff. At and after the hold instant, the launch-cutoff
filter no longer applies; do not treat either constant as a current hold.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `operator does not exist: userstatus = character varying` from `lifecycle_emails.daily_sweep` | PostgreSQL is comparing the shared `userstatus` enum mapping directly with a varchar parameter. | Retain the sanitized signature and counts, verify the active production revision exactly, and inspect whether the lifecycle selection contains `CAST(users.status AS VARCHAR) = 'active'`. Do not infer deployment from branch ancestry. | G-01 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Daily sweep selection
  root_cause: the lifecycle candidate query compared the shared userstatus mapping directly with a varchar parameter
  repair_entry_point: aidotmarket/ai-market-backend commit 77dae96fd8a80fe768091061bc3846fb1b5e8d55
  change_pattern: cast User.status to VARCHAR only in the lifecycle candidate predicate and compare it with active
  rollback_procedure: revert the single backend commit 77dae96fd8a80fe768091061bc3846fb1b5e8d55 through the normal reviewed and deployed workflow; never hot-patch production
  integrity_check: exact production SHA equals the intended reviewed target and a later scheduled daily sweep plus drain yields retained counts-only evidence without the signature
```

Operator boundary: if production is not exactly
`77dae96fd8a80fe768091061bc3846fb1b5e8d55`, route that exact candidate through
the normal review and deployment controls; do not manually invoke a sweep as a
substitute for deployment evidence. After deployment, Vulcan records the exact
revision and the next scheduled daily-sweep and drain aggregate results. Until
both exist, deployment and live-sweep status remain `UNKNOWN`. A rollback uses
the normal reviewed/deployed revert above and does not establish a healthy
sweep; reverting restores the pre-repair comparison.

The wider shared ORM mapping mismatch is explicitly out of scope. This repair
is limited to the lifecycle selection predicate and must not change policy,
models, schemas, migrations, or other callers.

## §H. Evolve

### §H.1 Invariants

- Selection/capture commits an idempotent outbox claim before the drain makes a network call.
- Lifecycle delivery never targets unverified, inactive, synthetic/test, or opted-out users.
- Day-3 suppresses only the complete-Stripe-plus-listing case.
- Production and sweep success remain UNKNOWN without exact post-deploy evidence.

### §H.2 BREAKING predicates

Changing eligibility, suppression, claim uniqueness, claim-before-drain
ordering, retry limits, unsubscribe signing, or message timing is breaking.

### §H.3 REVIEW predicates

Any task schedule, outbox field, lifecycle preference shape, synthetic filter,
status comparison, or production target SHA change requires focused backend
tests, exact-artifact review, and this DRAFT to be refreshed.

### §H.4 SAFE predicates

Counts-only evidence updates and editorial clarification are safe only when
they grant no authority and change no runtime behavior or UNKNOWN verdict.

### §H.5 Boundary definitions

#### module

The module boundary is lifecycle selection and claim helpers, the
`lifecycle_email_sends` model, its three Celery tasks, and the lifecycle-only
unsubscribe endpoint.

#### public contract

The public contract covered here is the idempotent signed
`/api/v1/emails/lifecycle/unsubscribe` route. This DRAFT does not redefine email
copy, the ops Signups response, or transactional email preferences.

#### runtime dependency

PostgreSQL, Celery beat/workers on the `emails` queue, the existing email
service, notification preferences, users, beta signups, and listings.

#### config default

Schedules and expired hold constants are the exact values above. The
verification-enforcement cutoff and synthetic email domain remain backend
configuration, not values invented by this runbook.

### §H.6 Adjudication

Exact backend source and post-deploy evidence win over this DRAFT. Uncertain
deployment identity, a missing scheduled result, or counts without revision
binding remains `UNKNOWN`; no local test or Git ancestry substitutes for live
evidence.

## §I. Operational Examples

```yaml acceptance
scenario_set: []
```

Focused implementation coverage is limited here to:

- `tests/test_s1548_lifecycle_emails_phase_b.py`
- `tests/test_s1548_lifecycle_emails_phase_d.py`
- `tests/test_s1548_ops_signups_phase_c.py`

This runbook-only change does not execute those backend tests. Its acceptance
does not include deployment or a live sweep, both of which remain UNKNOWN.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1588
last_refresh_commit: 77dae96fd8a80fe768091061bc3846fb1b5e8d55
last_refresh_date: 2026-08-20T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - any change to lifecycle task schedules, selection, suppression, outbox, retry, or unsubscribe behavior
  - a different backend production target or retained Vulcan post-deploy evidence
  - resolution of the shared ORM mapping mismatch
scheduled_cadence: 90d
```

The final runbooks commits and generated corpus pins belong in repository
history because this document cannot truthfully self-pin them.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
retrofit: false
trace_matrix_path: null
word_count_delta: null
```

This DRAFT remains discovery-only and must not be marked ACTIVE by local
authoring, catalog generation, or manifest registration.
