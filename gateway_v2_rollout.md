# Gateway V2 Rollout

## Purpose

Roll out AIM Node Gateway V2 in staged gates without changing the accepted thesis: Gateway V2 is the runtime gateway for the existing ai.market marketplace, and ai.market backend remains the canonical system of record.

## Feature Flags

Use independently reversible flags for each stage:

| Flag | Controls | Default before rollout |
| --- | --- | --- |
| `GATEWAY_V2_FOUNDATION_ENABLED` | shared contract routes, protocol validation, auth harness | off |
| `GATEWAY_V2_SURFACES_ENABLED` | discover, quote, publish control-plane routes in staging | off |
| `GATEWAY_V2_TRUST_GATED_PROMOTION_ENABLED` | public discoverability and quote eligibility for trust-gated listings | off until Trust Primitive blockers clear |
| `GATEWAY_V2_CONNECT_ENABLED` | access grant issuance and connector material exchange | off |
| `GATEWAY_V2_INVOKE_ENABLED` | runtime invocation through buyer/seller AIM Node or seller edge | off |
| `GATEWAY_V2_METER_ACCEPTANCE_ENABLED` | accepted billable meter events | off |
| `GATEWAY_V2_BUYER_BILLING_ENABLED` | buyer-agent billing sessions and payment-bound flow | off until Council payment/auth/security approval |
| `GATEWAY_V2_DIST_CHANNEL_ENABLED` | DIST installer/update channel exposing Gateway V2 runtime | off |

## Rollout Sequence

1. Foundation gate: deploy shared contracts, OpenAPI/proto validation, error envelope, auth/authz matrix, idempotency, replay controls, and observability hooks with production traffic disabled.
2. Surface gate: enable `discover`, `quote`, and `publish` in staging only. Keep trust placeholders blocked from production promotion. Verify who can publish, who can buy, human approval, abuse review, and revoked trust behavior.
3. Integration gate: enable `connect`, `invoke`, `meter`, and `receipt` only against local/seller-edge staging fixtures. Prove backend payload-byte non-custody across connect, invoke, seller-edge fulfillment, meter, and receipt.
4. Buyer billing gate: enable `verify_provider`, `request_access`, `estimate_cost`, and `create_billing_session` after unanimous Council approval for payment/auth/security behavior. Require budget caps and human approval where configured.
5. Migration gate: enable Gateway Console naming, command aliases, SDK deprecations, and migration shims. Confirm DASHBOARD, EARNINGS, and BUYER-MODE are subsumed and do not reappear as standalone products.
6. DIST release gate: package Gateway V2 runtime after health checks, connector registry, local secret storage, update path, and meter-buffer visibility are green. Release through the AIM Node DIST process only.
7. Public preview gate: run the canonical paid buyer-agent E2E flow and the observability/rate-limit matrix from a customer perspective before exposing production traffic.

## Required Validation

Run before advancing past staging:

```bash
./.venv/bin/pytest tests/gateway_v2/test_governance_gate_matrix.py
./.venv/bin/pytest tests/gateway_v2/test_e2e_paid_buyer_agent_flow.py
./.venv/bin/pytest tests/gateway_v2/test_observability_matrix.py tests/gateway_v2/test_rate_limit_matrix.py
```

For DIST, use the AIM Node release process and release script only. Verify the installed runtime as a buyer local node and seller edge node before promotion.

## Staging Gates

- Trust Primitive blockers are either approved or held as blocked placeholders with production promotion disabled.
- Abuse review blocks publish, discoverability, quote eligibility, connect, invoke, meter acceptance, and receipt visibility as specified.
- Buyer billing cannot grant access by itself; `connect` remains the access-grant boundary.
- Revoked trust blocks new grants and marks active streams with explicit revoked-trust state.
- Revoked access blocks new connect/invoke and prevents new meter acceptance except separately approved reconciliation for completed delivery.
- No backend logs, traces, request bodies, persisted records, or receipts contain payload bytes or raw seller secrets.

