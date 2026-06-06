---
system_name: alphafold-reference-listings
purpose_sentence: Publish AlphaFold model-organism proteomes to ai.market as free reference listings and keep the publish, shard-verification, and order-view paths working.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Reference-listing publish flow for public dataset proteomes including source-URL shard representation, zero-cost pricing, markdown descriptions, gsutil shard verification, and order-path enum integrity.
linter_version: 1.0.0
---

# AlphaFold Reference Listings

## §A. Header

The YAML frontmatter above defines the authoritative §A header values for this runbook.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Reference fulfillment type | SHIPPED | `app/models/order.py:FulfillmentType` | `manual: marketplace listing smoke (PR 119)` | 2026-06-06 |
| Zero-cost reference orders | SHIPPED | `alembic: orders_amount_cents_check relax (PR 120)` | `manual: zero-cent order create smoke` | 2026-06-06 |
| Multi-shard wildcard source delivery | SHIPPED | `reference listing source_delivery.url wildcard` | `manual: gsutil shard count per organism` | 2026-06-06 |
| Markdown listing descriptions | SHIPPED | `ai-market-frontend react-markdown (PR 24)` | `manual: listing detail render check` | 2026-06-06 |
| Order-detail reference delivery method | SHIPPED | `app/models/order.py and app/schemas/order.py DeliveryMethod` | `manual: OrderResponse reference round-trip` | 2026-06-06 |
| Bulk publish automation | PLANNED | — | — | 2026-06-06 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Publisher | reference-listing publish payload to `POST /api/v1/listings` | listings table, metadata enrichment cache | seller auth, public GCS bucket | Synchronous publish roughly eleven seconds each; idempotent upsert by device, dataset, and seller. |
| Order Detail | `GET /api/v1/orders/{id}` via `app/api` order endpoint | orders table | order response serializer | Serializes delivery_method through the response enum; a missing member raises during response validation. |
| Listing Frontend | listing detail page on `www.ai.market` | none | listings API, markdown renderer | Renders the markdown description through react-markdown with rehype-sanitize. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan | publish a reference listing | `Koskadeux:shell_request -> POST /api/v1/listings` | seller-token-public-at-ai-market | COMPLETE |
| vulcan | verify proteome shard count | `Koskadeux:shell_request -> gsutil ls` | gcs-read-aimarket-prod | COMPLETE |
| vulcan | verify order-view path | `Koskadeux:shell_request -> GET /api/v1/orders` | buyer-token | COMPLETE |
| mp | add a new delivery or fulfillment enum value | `Koskadeux:council_request -> build` | repo-write | PARTIAL — needs both model and schema edits in one change |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A public dataset proteome should be listed on the marketplace as a free reference listing.
  pre_conditions:
    - seller_authenticated
    - source_bucket_reachable
  tool_or_endpoint: POST /api/v1/listings
  argument_sourcing:
    seller_token: minted from the public seller account using the live signing key
    source_url: whole-proteome gcs wildcard from the shard table
    price: constant zero
    fulfillment_type: constant reference
  idempotency: IDEMPOTENT
  expected_success:
    shape: Created listing record with reference fulfillment and zero price
    verification: Fetch the public listings endpoint and confirm the organism appears exactly once
  expected_failures:
    - signature: "422 unprocessable"
      cause: price floor or fulfillment type rejected because an enabling migration is missing
  next_step_success: Apply the markdown description template and confirm the detail page renders
  next_step_failure: Escalate to §F-01 symptom isolation
- id: E-02
  trigger: A proteome wildcard must be confirmed to resolve to the expected number of shards before publish.
  pre_conditions:
    - gcloud_account_set
    - requester_pays_project_available
  tool_or_endpoint: gsutil ls -u aimarket-prod gs://public-datasets-deepmind-alphafold-v4/proteomes/proteome-tax_id-<TAX>-*_v4.tar
  argument_sourcing:
    billing_project: constant aimarket-prod
    tax_id: organism to tax id map in worker-coord state
  idempotency: IDEMPOTENT
  expected_success:
    shape: A list of shard object names whose count matches the shard table
    verification: Compare the line count against the expected shard count for the organism
  expected_failures:
    - signature: "AccessDeniedException 403"
      cause: requester-pays billing project flag omitted
  next_step_success: Proceed to publish the listing with the verified wildcard
  next_step_failure: Escalate to §F-02 symptom isolation
- id: E-03
  trigger: After a publish batch the marketplace must be confirmed healthy and free of duplicates.
  pre_conditions:
    - listings_api_reachable
  tool_or_endpoint: GET /api/v1/listings?limit=100
  argument_sourcing:
    limit: constant one hundred because the endpoint caps the limit at one hundred
  idempotency: IDEMPOTENT
  expected_success:
    shape: A listings page where each organism appears exactly once
    verification: Count organisms in the response and confirm no duplicates after the cache settles
  expected_failures:
    - signature: "422 unprocessable"
      cause: limit set above one hundred
  next_step_success: Record the live listing count in the publish log
  next_step_failure: Escalate to §F-02 symptom isolation
- id: E-04
  trigger: The order-view path must be confirmed working for a reference listing.
  pre_conditions:
    - buyer_token_available
    - reference_order_exists
  tool_or_endpoint: GET /api/v1/orders/<id>
  argument_sourcing:
    order_id: a delivered reference order id
    buyer_token: minted for the order owner using the live signing key
  idempotency: IDEMPOTENT
  expected_success:
    shape: Order detail response with delivery_method reference and http status two hundred
    verification: Confirm the response status is two hundred and the delivery method reads reference
  expected_failures:
    - signature: "500 internal server error"
      cause: a delivery or fulfillment enum value missing from the model or the response schema
  next_step_success: Record the order path as verified for reference listings
  next_step_failure: Escalate to §F-03 symptom isolation
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Publish rejected with a 422 or the marketplace 500s on a reference listing | a missing enabling migration or fulfillment enum member | Confirm the reference fulfillment and zero-price migrations are present on the deployed main | §G-01 | CONFIRMED |
| F-02 | A published listing wildcard resolves to zero or the wrong number of shards | wrong tax id, missing requester-pays flag, or a malformed wildcard | Re-run the authenticated gsutil listing and compare the count against the shard table | §G-02 | CONFIRMED |
| F-03 | Order detail returns 500 for a reference order | a delivery method value present in the database but absent from the response enum | Coerce the stored delivery method through the response schema enum and observe the validation error | §G-03 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Publisher
  root_cause: An enabling migration or fulfillment enum member required by reference listings was not present on the deployed main.
  repair_entry_point: app/models/order.py:FulfillmentType
  change_pattern: Add the reference fulfillment member and the zero-cost order migration, then redeploy from main.
  rollback_procedure: Revert the enum and migration commits and redeploy the prior main.
  integrity_check: Publish one reference listing and confirm it appears once on the public listings endpoint.
- id: G-02
  symptom_ref: F-02
  component_ref: Publisher
  root_cause: The source wildcard used a wrong tax id or omitted the requester-pays billing project.
  repair_entry_point: reference listing source_delivery.url wildcard
  change_pattern: Correct the tax id from the organism map and always pass the requester-pays project on verification.
  rollback_procedure: Restore the previous source url on the listing record.
  integrity_check: Re-run the authenticated gsutil listing and confirm the shard count matches the table.
- id: G-03
  symptom_ref: F-03
  component_ref: Order Detail
  root_cause: A delivery method value stored in the database was missing from the Pydantic response enum so serialization raised.
  repair_entry_point: app/schemas/order.py:DeliveryMethod
  change_pattern: Add the new value to both the model enum and the schema enum in the same change.
  rollback_procedure: Revert the enum additions and redeploy the prior main.
  integrity_check: Coerce the stored value through the response schema and confirm the order endpoint returns two hundred.
```

## §H. Evolve

### §H.1 Invariants

- A reference listing must never cause raw data to transit ai.market; it carries only metadata and a public source url.
- Any delivery or fulfillment value stored in the database must have a matching member in both the model enum and the response schema enum.

### §H.2 BREAKING predicates

- Any change that removes a fulfillment or delivery enum member that existing listings or orders depend on is BREAKING.
- Any change that makes the listings endpoint reject the documented limit of one hundred is BREAKING.

### §H.3 REVIEW predicates

- Any change that adds a new fulfillment or delivery enum value requires REVIEW.
- Any change to the source-url wildcard representation for sharded datasets requires REVIEW.

### §H.4 SAFE predicates

- Editing the markdown description text of an existing listing is SAFE.
- Adding a new organism listing using the established wildcard pattern is SAFE.

### §H.5 Boundary definitions

#### module

The module boundary is one deployable unit of the publish path such as the backend listings service or the frontend listing detail page.

#### public contract

The public contract is the listing publish payload, the listings and orders endpoints, and the documented limit and pricing behavior exposed to sellers and buyers.

#### runtime dependency

A runtime dependency is any external service required for the flow such as the public GCS bucket, the requester-pays billing project, or the signing key used to mint tokens.

#### config default

A config default is a fallback such as the listings endpoint limit cap or the single-file suffix used for the one unsharded organism.

### §H.6 Adjudication

When a proposed change touches more than one boundary class, classify it at the highest-risk class and record the reasoning in the change review.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A public proteome should be listed for free and the responder needs the first publish action.
    expected_answers:
      - kind: tool_call
        tool: POST /api/v1/listings
        argument_keys: [seller_token, source_url, price, fulfillment_type]
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: Before publishing a proteome the responder must confirm the wildcard resolves to the expected shard count.
    expected_answers:
      - kind: tool_call
        tool: gsutil ls
        argument_keys: [billing_project, tax_id]
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: After a publish batch the responder must confirm the marketplace shows each organism once.
    expected_answers:
      - kind: tool_call
        tool: GET /api/v1/listings
        argument_keys: [limit]
    weight: 0.08333333333333333
  - id: I-04
    type: operate
    refs: [E-04]
    scenario: The responder must confirm a buyer can open a reference order without error.
    expected_answers:
      - kind: tool_call
        tool: GET /api/v1/orders
        argument_keys: [order_id, buyer_token]
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-01]
    scenario: A reference publish was rejected and the responder must confirm whether an enabling migration is missing.
    expected_answers:
      - kind: human_action
        verb: confirm
        object: enabling migrations
        target: deployed main for reference and zero-price support
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-02]
    scenario: A listing wildcard resolved to the wrong shard count and the responder must verify the cause.
    expected_answers:
      - kind: tool_call
        tool: gsutil ls
        argument_keys: [billing_project, tax_id]
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [F-03]
    scenario: An order detail call returned 500 and the responder must determine whether an enum value is missing.
    expected_answers:
      - kind: human_action
        verb: coerce
        object: stored delivery method
        target: response schema enum
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-01]
    scenario: A reference publish keeps failing and the fix for the missing enabling support is needed.
    expected_answers:
      - kind: human_action
        verb: patch
        object: fulfillment enum and zero-price migration
        target: app/models/order.py:FulfillmentType
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-03]
    scenario: The order endpoint 500s on reference orders and the fix for the missing enum value is needed.
    expected_answers:
      - kind: human_action
        verb: patch
        object: delivery method enum
        target: app/schemas/order.py:DeliveryMethod
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: A proposal adds a brand new fulfillment value and needs classification against the evolve predicates.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [§H]
    scenario: A proposal removes an existing delivery enum member that current orders depend on.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-04, F-03, G-03, §H]
    scenario: A single order detail 500 might be a missing enum value or an unrelated serializer regression and needs careful classification.
    expected_answers:
      - kind: human_action
        verb: investigate
        object: order detail failure
        target: stored delivery value plus response schema
    weight: 0.08333333333333333
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S790
last_refresh_commit: aedc0a1
last_refresh_date: 2026-06-06T21:50:00Z
owner_agent: vulcan
refresh_triggers:
  - bq_completion
  - gate_approval
  - incident
scheduled_cadence: 90d
last_harness_pass_rate: 1.0
last_harness_date: 2026-06-06T21:50:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S790 / 2026-06-06T21:50:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
