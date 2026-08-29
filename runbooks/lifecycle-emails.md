---
title: Lifecycle Emails
owner: vulcan
last_verified: '2026-08-20'
aliases: []
error_signatures:
- 'operator does not exist: userstatus = character varying'
---

# Lifecycle Emails

## Overview

This page records the verified state and remaining evidence gaps for Build Queue item
`build:bq-signup-lifecycle-emails-s1548`. It is grounded in exact
`aidotmarket/ai-market-backend` revision
`77dae96fd8a80fe768091061bc3846fb1b5e8d55`. The backend deployment
`480d2fdc-c1c1-46a5-a915-3986c04ab84c` completed with status `SUCCESS` and image
`sha256:8c9e1ffb594e90197447aebfbda3850216771210a3cbf9f4c1d06af4f9b75fd4`.
The same deployed service set records beat deployment
`3b46d1e6-5385-486f-a7f2-c2a99895f839` with image
`sha256:fdc8443f9fa9c8291630c39ec5e246547a45b42953c0ddaaf1f864f5a62050f4`
and worker deployment `8ae9b906-3a48-44d1-9783-bf029e6f055b` with image
`sha256:d965f4cd1452ff6eba1b71236547d3901f2628df1ff829a984c31ac3455642ad`.

Operator-triggered live task `lifecycle_emails.daily_sweep`
`bd169cfa-3675-4a61-bf32-cc95c1325555` ran at
`2026-08-20T20:19:19Z` and succeeded in `6.481179486960173s` with aggregate
counts `{selected: 51, claimed: 51}`. No
`operator does not exist: userstatus = character varying` log has occurred
since deployment. This proves the repaired selection/claim path. Drain and
delivery behavior and recipient inbox delivery were not part of this predicate
repair and were not re-verified here. No browser verification was performed.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Scheduled claim and drain tasks | PARTIAL | `app/core/celery_app.py; app/tasks/lifecycle_emails.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | Focused tests cover schedules; the operator-triggered daily sweep proves live selection/claim, but scheduled execution and drain/delivery were not re-verified here | 2026-08-20 |
| Idempotent outbox, suppression, and retry boundary | PARTIAL | `app/models/lifecycle_email_send.py; app/services/lifecycle_email_claims.py; app/tasks/lifecycle_emails.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | Focused tests cover the boundary; live aggregate counts prove 51 selections produced 51 claims, but drain/delivery was not re-verified here | 2026-08-20 |
| Signed lifecycle unsubscribe | PARTIAL | `app/api/v1/endpoints/lifecycle_emails.py; app/services/lifecycle_email_unsubscribe.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | `tests/test_s1548_lifecycle_emails_phase_d.py` | 2026-08-20 |
| Signup and attempt selection | PARTIAL | `app/tasks/lifecycle_emails.py; app/api/v1/endpoints/ops_signups.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | `tests/test_s1548_lifecycle_emails_phase_b.py; tests/test_s1548_ops_signups_phase_c.py` | 2026-08-20 |
| Exact production deployment and repaired daily selection/claim path | SHIPPED | `app/tasks/lifecycle_emails.py@77dae96fd8a80fe768091061bc3846fb1b5e8d55` | Backend/beat/worker deployment and image identities are in Overview; live task `bd169cfa-3675-4a61-bf32-cc95c1325555` succeeded with `{selected: 51, claimed: 51}` and no matching failure log since deployment | 2026-08-20 |

`PARTIAL` means the behavior is present in the exact deployed revision and has
focused test coverage, but the specific behavior was not fully re-verified live
here. This runbook work did not rerun those backend tests. `SHIPPED` is limited
to exact deployment identity and the repaired daily selection/claim path; it
does not extend to drain/delivery or recipient inbox delivery.

## Architecture & interactions

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

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Verify exact production SHA and observe task results | Read-only deployment identity and sanitized task evidence | Read-only until a separately reviewed deployment or rollback is authorized | COMPLETE — exact deployment and the successful operator-triggered daily selection/claim sweep are recorded; drain/delivery and recipient inbox delivery were not re-verified |

## How to operate

```yaml operate
[]
```

No production operation is prescribed here. The registered schedules are:

- `lifecycle_emails.drain_outbox`: every 300 seconds.
- `lifecycle_emails.attempt_sweep`: hourly at minute 35.
- `lifecycle_emails.daily_sweep`: daily at 15:00 UTC.

The retained live evidence is the operator-triggered
`lifecycle_emails.daily_sweep` task
`bd169cfa-3675-4a61-bf32-cc95c1325555` at `2026-08-20T20:19:19Z`. It
succeeded in `6.481179486960173s` with aggregate counts
`{selected: 51, claimed: 51}`. The exact deployed revision and service image
identities are recorded in Overview, and no
`operator does not exist: userstatus = character varying` log has occurred
since deployment. This evidence proves the repaired selection/claim path only.
No drain/delivery, recipient inbox delivery, or browser verification was
performed as part of this runbook refresh.

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

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `operator does not exist: userstatus = character varying` from `lifecycle_emails.daily_sweep` | PostgreSQL is comparing the shared `userstatus` enum mapping directly with a varchar parameter. | Retain the sanitized signature and counts, verify the active production revision exactly, and inspect whether the lifecycle selection contains `CAST(users.status AS VARCHAR) = 'active'`. Do not infer deployment from branch ancestry. | G-01 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Daily sweep selection
  root_cause: the lifecycle candidate query compared the shared userstatus mapping directly with a varchar parameter
  repair_entry_point: aidotmarket/ai-market-backend commit 77dae96fd8a80fe768091061bc3846fb1b5e8d55
  change_pattern: cast User.status to VARCHAR only in the lifecycle candidate predicate and compare it with active
  rollback_procedure: revert the single backend commit 77dae96fd8a80fe768091061bc3846fb1b5e8d55 through the normal reviewed and deployed workflow; never hot-patch production
  integrity_check: exact production SHA equals the intended reviewed target and a live daily sweep yields retained counts-only selection/claim evidence without the signature
```

The recorded backend deployment is exactly
`77dae96fd8a80fe768091061bc3846fb1b5e8d55`; its deployment and image identities
are in Overview. The operator-triggered task in How to operate succeeded with 51 selections and
51 claims, and the failure signature has not appeared since deployment. This
live task proves the repaired selection/claim path. It does not prove the
separate drain/delivery path or recipient inbox delivery, neither of which was
part of this predicate repair or re-verified here. A rollback uses the normal
reviewed/deployed revert above; execute it only through that reviewed workflow.

The wider shared ORM mapping mismatch is explicitly out of scope. This repair
is limited to the lifecycle selection predicate and must not change policy,
models, schemas, migrations, or other callers.

## Changes and maintenance

### Changes and maintenance.1 Invariants

- Selection/capture commits an idempotent outbox claim before the drain makes a network call.
- Lifecycle delivery never targets unverified, inactive, synthetic/test, or opted-out users.
- Day-3 suppresses only the complete-Stripe-plus-listing case.
- Exact deployment and the repaired live daily selection/claim path are bound to the evidence in Overview and How to operate.
- Drain/delivery and recipient inbox delivery remain separate from the repaired predicate and were not re-verified here.

### Changes and maintenance.2 BREAKING predicates

Changing eligibility, suppression, claim uniqueness, claim-before-drain
ordering, retry limits, unsubscribe signing, or message timing is breaking.

### Changes and maintenance.3 REVIEW predicates

Any task schedule, outbox field, lifecycle preference shape, synthetic filter,
status comparison, or production target SHA change requires focused backend
tests, exact-artifact review, and this page to be refreshed.

### Changes and maintenance.4 SAFE predicates

Counts-only evidence updates and editorial clarification are safe only when
they grant no authority, change no runtime behavior, and do not broaden the
specific path proved by the retained evidence.

### Changes and maintenance.5 Boundary definitions

#### module

The module boundary is lifecycle selection and claim helpers, the
`lifecycle_email_sends` model, its three Celery tasks, and the lifecycle-only
unsubscribe endpoint.

#### public contract

The public contract covered here is the idempotent signed
`/api/v1/emails/lifecycle/unsubscribe` route. This page does not redefine email
copy, the ops Signups response, or transactional email preferences.

#### runtime dependency

PostgreSQL, Celery beat/workers on the `emails` queue, the existing email
service, notification preferences, users, beta signups, and listings.

#### config default

Schedules and expired hold constants are the exact values above. The
verification-enforcement cutoff and synthetic email domain remain backend
configuration, not values invented by this runbook.

### Changes and maintenance.6 Adjudication

Exact backend source and post-deploy evidence win over this page. For this
refresh, exact deployment identity plus the operator-triggered counts bind the
repaired selection/claim result to the deployed revision. They do not establish
drain/delivery or recipient inbox delivery. Uncertain future deployment
identity or counts without revision binding remain `UNKNOWN`; no local test,
Git ancestry, or browser inference substitutes for live evidence.

## Acceptance criteria

```yaml acceptance
scenario_set: []
```

Focused implementation coverage is limited here to:

- `tests/test_s1548_lifecycle_emails_phase_b.py`
- `tests/test_s1548_lifecycle_emails_phase_d.py`
- `tests/test_s1548_ops_signups_phase_c.py`

This runbook-only change does not execute those backend tests. Its retained
acceptance evidence is the exact successful deployment plus the live
operator-triggered task proving the repaired selection/claim path with
counts-only output. Drain/delivery, recipient inbox delivery, and browser
verification were outside this predicate repair and were not re-verified here.

## Maintenance

```yaml lifecycle
last_refresh_session: S1588
last_refresh_commit: 77dae96fd8a80fe768091061bc3846fb1b5e8d55
last_refresh_date: 2026-08-20T20:19:19Z
owner_agent: vulcan
refresh_triggers:
  - any change to lifecycle task schedules, selection, suppression, outbox, retry, or unsubscribe behavior
  - a different backend production target or later retained counts-only task evidence
  - resolution of the shared ORM mapping mismatch
scheduled_cadence: 90d
```

The final runbooks commits and generated corpus pins belong in repository
history because this document cannot truthfully self-pin them.
