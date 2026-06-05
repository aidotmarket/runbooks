# Gateway V2 Rollback

## Purpose

Disable Gateway V2 surfaces without corrupting canonical backend records. Rollback changes traffic, flags, DIST channels, and eligibility gates; it does not rewrite listings, quotes, billing sessions, access grants, accepted meter events, receipts, settlement records, or governance decisions.

## Rollback Order

1. Freeze DIST release: disable `GATEWAY_V2_DIST_CHANNEL_ENABLED`, stop installer/update promotion, and pin the previous AIM Node stable channel.
2. Stop buyer acquisition: disable `GATEWAY_V2_BUYER_BILLING_ENABLED` and `GATEWAY_V2_SURFACES_ENABLED` for new buyer-agent billing, quote creation, and access requests.
3. Stop new supply promotion: disable `GATEWAY_V2_TRUST_GATED_PROMOTION_ENABLED` and publish promotion. Existing listings remain canonical records but no blocked listing becomes discoverable or quote-eligible.
4. Stop grant issuance: disable `GATEWAY_V2_CONNECT_ENABLED`. Existing quotes and billing sessions are preserved; new access grants are refused.
5. Stop runtime invocation: disable `GATEWAY_V2_INVOKE_ENABLED`. Active streams are allowed to drain only if payload-custody and revoked-access policies remain healthy; otherwise terminate through explicit stream failure state.
6. Stop billable metering: disable `GATEWAY_V2_METER_ACCEPTANCE_ENABLED`. Preserve already accepted meter events and receipts; reject or buffer new events according to fail-closed policy.
7. Leave receipt lookup read-only where safe so buyers, sellers, support, and governance can inspect canonical records with audit reasons.

## Surface Disablement

| Surface | Disable action | Canonical record rule |
| --- | --- | --- |
| `publish` | Reject new create/update or keep as `pending_review`; block promotion to public discover/quote. | Do not delete listing or listing-version records as rollback cleanup. |
| buyer billing | Reject `create_billing_session` and buyer-agent payment-bound actions. | Do not mutate completed/failed billing sessions except normal payment reconciliation. |
| `connect` | Refuse new grant issuance and grant redemption. | Do not rewrite quotes, billing sessions, or prior grants; mark operational denial via audit only. |
| `invoke` | Refuse new invocation and terminate unsafe active streams with explicit state. | Do not persist payload bytes during termination. |
| meter acceptance | Reject new billable meter events or fail closed. | Do not double bill, delete, or restamp accepted meter events. |
| receipt | Keep read-only lookup if safe; otherwise restrict to support/governance with audit reason. | Do not regenerate receipts with invented trust evidence. |
| DIST release | Roll back installer/update channel to previous stable. | Do not change backend canonical records because a client release regressed. |

## Trigger Conditions

- Trust Primitive blocker is unresolved for a production-required field.
- Abuse review fails to block publish, discoverability, quote, connect, invoke, meter, or receipt surfaces.
- Human approval or budget-cap checks fail for buyer agents.
- Revoked trust/access does not block new grants or new streams.
- Active stream revocation lacks explicit `trust_revoked_mid_stream` or access-denied behavior.
- Backend receives, logs, persists, transforms, or proxies payload bytes or raw seller secrets.
- Meter backpressure, duplicate billing, or receipt reconciliation checks fail.
- DIST packaging exposes old seller-wrapper, DASHBOARD, EARNINGS, or BUYER-MODE as separate products.

## Integrity Checks

After rollback:

```bash
./.venv/bin/pytest tests/gateway_v2/test_governance_gate_matrix.py
rg -n "rollback|revoked trust|abuse review|human approval|who can publish|who can buy" tests/gateway_v2 runbooks specs
```

Confirm from the customer perspective:

- buyers cannot start a new payment-bound Gateway V2 purchase when buyer billing is disabled
- sellers cannot promote a blocked publish into public discovery
- existing receipts remain readable where policy permits
- no rollback job rewrites canonical backend records to hide the incident

