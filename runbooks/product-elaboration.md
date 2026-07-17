---
runbook_id: product-elaboration
domain: boot-kernel
status: ACTIVE
authoritative_for:
  - topic: product-elaboration
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: product_boundary_conflict
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: max
last_verified_at: 2026-07-17
system_name: product-elaboration
purpose_sentence: This companion preserves detailed product narrative, surfaces, boundaries, integrations, and historical or deferred elaboration outside the boot kernel.
owner_agent: max
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Delivery companion for product design, positioning, and customer-surface decisions across ai.market, allAI, AIM Data, and vectorAIz.
linter_version: 1.0.0
---

# Product Elaboration

## §A. Header

The frontmatter is authoritative for catalog identity. **Authority: delivery companion.** Full CORE and the Boot Kernel prevail. `docs/core/BUSINESS-CONTEXT.md` owns locked but evolvable product specifics; this document cannot turn deferred or historical material into a current product commitment.

**Fetch trigger:** product design, positioning, or customer-surface decision.

**Source constitution:** CORE v9.11, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`, sections 2 and 9.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| ai.market marketplace boundary | SHIPPED | `docs/core/CORE.md` | Source-SHA cross-walk and strict lint | 2026-07-17 |
| allAI engine and mediation boundary | SHIPPED | `docs/core/CORE.md` | Source-SHA cross-walk and strict lint | 2026-07-17 |
| AIM Data conduit surfaces | SHIPPED | `docs/core/CORE.md` | Source-SHA cross-walk and strict lint | 2026-07-17 |
| vectorAIz product boundary | SHIPPED | `docs/core/CORE.md` | Source-SHA cross-walk and strict lint | 2026-07-17 |
| Deferred product decisions | SHIPPED | `docs/core/BUSINESS-CONTEXT.md` | Explicit future-scope classification | 2026-07-17 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| ai.market Network | `ai.market` website and agent-readable surfaces | Marketplace metadata and transaction state | allAI, AIM Data, vectorAIz | Non-custodial B2B metadata marketplace and trust/billing layer. |
| allAI Engine | allAI mediation and metadata generation | Shared memory and metadata corpus | Marketplace and both conduits | Mandatory worker; models are swappable while the corpus compounds. |
| AIM Data Conduit | Desktop GUI, Python, CLI, MCP, SDK | Customer infrastructure | ai.market and allAI | Two audiences, one customer-hosted conduit; not the worker. |
| vectorAIz Product | `aidotmarket/vectoraiz` | Customer Qdrant-format datasets | ai.market | Co-equal product with distinct brand; standalone has no allAI access. |
| Product Decision Detail | `docs/core/BUSINESS-CONTEXT.md` | Git | Council Hall and Max decisions | Owns locked but evolvable specifics and deferred detail. |

### Normative projection — CORE §2, pillar frame

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> The ecosystem has four product pillars. The story flows: **marketplace → engine → conduits.** ai.market is where buyers and sellers transact; allAI is the engine that does the work for customers; AIM Data and vectorAIz are the customer-facing data products through which customers' data is turned into marketplace listings and reaches the network. Koskadeux/Council is the meta-orchestration layer that builds them all — important, but not itself a product. **The business is data.**

> The orchestration layer is also the thesis, dogfooded: ai.market is built to be operated by cooperating AI agents, and we run the company itself on cooperating agents to prove that model works. Building agent-first and operating agent-first are the same bet.

### Normative projection — CORE §2, ai.market

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> - **IS:** A non-custodial B2B data marketplace. Four marketplace functions: **list/sell, buy, develop/integrate, request**. Agent-first — designed for AI systems to discover, evaluate, and transact programmatically. The website is the primary transaction surface for buyers and sellers — discovering data, evaluating listings, and transacting.
> - **IS NOT:** A data warehouse. Never stores or touches raw customer data. We are the index and the trust/billing layer.
> - **AI-discoverable everywhere:** Listings on ai.market are built to be **found by LLMs and AI agents globally** — in ChatGPT, Gemini, Claude, and any agentic search — not just on our website. This is core customer value, not a feature: customers' data must be discoverable wherever buyers ask, without buyers having to come to ai.market directly. Every public listing surface carries structured metadata (JSON-LD, schema.org, llms.txt, agent-readable manifests) optimized for LLM and agent indexing. **The default question on any listing field is: "Will an LLM agent find this when a buyer asks for it elsewhere in the world, in any language?"**
> - **MUST integrate with:** allAI (mediation, search, agent-facing discovery, listing generation), AIM Data (receives metadata + listing manifests; serves both the non-dev GUI and developer/programmatic buy/sell/request surfaces), vectorAIz (receives Qdrant-format dataset uploads and their listing manifests)
> - **Revenue:** **5% commission on successful data transactions.** No listing fees. Utility pricing — infrastructure, not a broker.

### Normative projection — CORE §2, allAI

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> - **IS:** The AI brain of the ecosystem and **the worker that does the heavy lifting for customers**. **Primary customer value: making listing data easy** — allAI generates metadata, classifies fields, drafts descriptions, runs quality validation, and turns raw data into discoverable, agent-findable listings, so the customer doesn't have to. Mediates ALL buyer-seller interactions — including across languages: buyers and sellers each operate in their own language, and allAI carries meaning between them (listing metadata, search, and mediated communications). Shared memory + RAG knowledge base. **Learns from every metadata generation interaction.** Mission: **become the best metadata classifying AI in the world for data, in any language** — every customer who runs metadata generation through allAI improves the model for every other customer. The compounding metadata corpus and feedback loop is our long-term moat (the data asset, not any single model — models are swappable; the corpus is not).
> - **IS NOT:** Optional. Not just a copilot the customer can ignore. **allAI doing the work IS the product experience.** Removing allAI also enables disintermediation — buyers contact sellers directly, bypassing the platform.
> - **MUST integrate with:** ai.market (mediation, listing generation, agent-facing answers), AIM Data and vectorAIz (the customer-side data products where allAI's work happens on real data sources, including programmatic developer access), Koskadeux (dev memory)

### Normative projection — CORE §2, AIM Data

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> - **IS:** **A conduit, not a worker.** The conduit through which **allAI's metadata generation, classification, and listing work reaches the customer's data sources**, serving two audiences from one product. For non-technical users: a customer-hosted desktop GUI (Docker app running locally at the customer site) surfacing data-source profiling, PII management, metadata review and approval, listing publication, monitoring, and a request inbox. For developers operating at scale: a programmatic surface — pip-installable Python package + CLI + MCP server + SDK — giving programmatic access to all four marketplace functions (buy, sell, develop/integrate, request) and to allAI's listing/metadata work, plus peer-to-peer data transfer between buyer and seller nodes; the MCP server makes the marketplace and allAI accessible to AI agents. When in connected / approved mode, hosts ai.market agents that run on the customer's data sources to validate quality scores and assist metadata generation. Agents only run with explicit customer approval per data source.
> - **IS NOT:** A cloud service or model host. Runs on the customer's / participant's own infrastructure; outbound connections only — works behind any firewall. Never phones home with customer data. **Not the worker — the worker is allAI.**
> - **Data plane:** Non-custodial. The programmatic surface forwards opaque frames over an encrypted relay (ChaCha20-Poly1305, per-session ephemeral keys); ai.market handles the control plane and metering metadata only — never data plane content.
> - **MUST integrate with:** ai.market (metadata publishing via Trust Channel, agent dispatch in connected mode, session negotiation, metering, billing, relay routing), allAI (the engine of customer value; programmatic listing generation, classification, mediation)
> - **allAI key:** Metered allAI access, billed to customer. Only available in connected mode (ai.market proxied key).

### Normative projection — CORE §2, vectorAIz

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> - **IS:** Our second customer-facing data product, co-equal with AIM Data. It turns corporate data into a Qdrant (vector database) format and can upload that data to the marketplace the same way AIM Data does. A distinct product with its own brand and repo (`aidotmarket/vectoraiz`).
> - **IS NOT:** Branded under ai.market. It is our product, but it ships under its own brand, not as part of the AIM Data conduit. Not a worker — the worker is allAI.
> - **allAI key:** Metered allAI access only in connected mode (ai.market proxied key). **Standalone vectorAIz has no allAI access.**
> - **MUST integrate with:** ai.market (Qdrant-format dataset upload + listing path, metering, billing)

### Normative projection — CORE §9, durable and deferred surface

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> The durable shape of the product. The **locked but evolvable specifics** (deferred Federate specifics, gating policy, sequencing) live in `docs/core/BUSINESS-CONTEXT.md` under "Product Surface (locked decisions)" — they are product decisions that can change with a Council Hall, so they do not belong in the constitution.

> - **Two customer-facing data products.** Customers reach ai.market through two co-equal data products: **AIM Data** (repo `aidotmarket/aim-data`) — one conduit with two surfaces, a non-dev customer-hosted desktop GUI and a developer surface (CLI, SDK, MCP server) for programmatic access to the marketplace and to allAI; and **vectorAIz** (repo `aidotmarket/vectoraiz`) — which turns corporate data into a Qdrant (vector) format and uploads it to the marketplace the same way AIM Data does. vectorAIz is our product but is not branded under ai.market, and standalone it has no allAI access. The former AIM-Node developer conduit is retired (S1001); its features are subsumed into AIM Data.
> - **Federated learning is FUTURE scope (Max decision, 2026-06-11 / S811):** deferred — not built, not sold, and not referenced on any current product surface or marketing copy. Its defining property (models train on a seller's data without the raw data ever leaving the seller's infrastructure) is preserved in `docs/core/BUSINESS-CONTEXT.md` for when it returns. Reintroduction requires an explicit Max decision.
> - **Language-first international:** sellers list once, in their own language; allAI makes the listing discoverable and transactable in every supported language. Buyers and sellers never need to share a language — allAI mediates meaning between them.
> - **Revenue is utility pricing:** 5% commission on transactions. No listing fees.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Product designer | Resolve durable product boundaries | CORE and this companion | Read | COMPLETE |
| Council Hall | Review evolvable product decisions | Council deliberation | Decision evidence | COMPLETE |
| Max | Approve product direction and deferred-scope return | Human decision | Final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A product design or positioning decision touches a pillar boundary.
  pre_conditions: [decision_question_written, affected_pillars_known]
  tool_or_endpoint: product-elaboration plus docs/core/BUSINESS-CONTEXT.md
  argument_sourcing: {invariants: use CORE-linked sections in this companion, specifics: use current Business Context}
  idempotency: IDEMPOTENT
  expected_success: {shape: decision framed by durable and evolvable authority, verification: name every affected pillar and boundary}
  expected_failures: [{signature: product_boundary_conflict, cause: a proposal makes a conduit the worker, makes the marketplace custodial, or treats orchestration as a product}]
  next_step_success: Size the decision gate by reversibility and customer risk.
  next_step_failure: Stop and reconcile the proposal with CORE.
- id: E-02
  trigger: A customer surface needs marketplace discovery or language behavior.
  pre_conditions: [surface_known, listing_metadata_in_scope]
  tool_or_endpoint: CORE sections 2 and 9
  argument_sourcing: {discovery: apply agent-readable global indexing, language: preserve seller-original trust and allAI mediation}
  idempotency: IDEMPOTENT
  expected_success: {shape: agent-discoverable multilingual-ready surface, verification: test external discovery metadata and language trust behavior}
  expected_failures: [{signature: product_discovery_gap, cause: public listing metadata is human-only or language assumptions bypass allAI}]
  next_step_success: Verify from the buyer and seller perspectives.
  next_step_failure: Return the surface to product design.
- id: E-03
  trigger: Historical or deferred product material is proposed for active scope.
  pre_conditions: [source_decision_identified, current_business_context_read]
  tool_or_endpoint: Council Hall and Max decision
  argument_sourcing: {history: distinguish prior shape from current invariants, activation: require explicit current approval}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(topic + current_decision_sha + proposal_digest)
  expected_success: {shape: explicit keep-deferred or approved reintroduction decision, verification: current product surfaces match the recorded decision}
  expected_failures: [{signature: deferred_scope_reactivated, cause: historical prose was mistaken for current authorization}]
  next_step_success: Update Business Context and implementation specs under the approved decision.
  next_step_failure: Keep the material deferred and absent from active surfaces.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A proposal blurs marketplace, engine, or conduit responsibilities. | Historical naming or feature enthusiasm displaced current CORE boundaries. | Map every proposed behavior to ai.market, allAI, AIM Data, or vectorAIz and compare with §C. | G-01 | CONFIRMED |
| F-02 | Deferred functionality appears on a current product or marketing surface. | Historical detail was treated as active authorization. | Read current Business Context and the explicit deferred rule before inspecting surfaces. | G-02 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Product Decision Detail
  root_cause: The proposal conflicts with durable pillar roles or current evolvable decisions.
  repair_entry_point: product design and docs/core/BUSINESS-CONTEXT.md
  change_pattern: Restore the CORE boundary, then revise only evolvable specifics through the correct decision gate.
  rollback_procedure: Remove the conflicting product claim or feature exposure.
  integrity_check: Marketplace remains non-custodial, allAI remains the worker, and conduits keep distinct boundaries.
- id: G-02
  symptom_ref: F-02
  component_ref: Product Decision Detail
  root_cause: Deferred or retired material was promoted without a current Max decision.
  repair_entry_point: affected product and marketing surfaces
  change_pattern: Remove the unauthorized reference and preserve detail only in its historical or deferred authority.
  rollback_procedure: Restore the last approved current-surface content.
  integrity_check: Current surfaces contain no deferred claim and the history remains retrievable.
```

## §H. Evolve

### §H.1 Invariants

Marketplace, engine, and conduits retain distinct roles; the business remains non-custodial metadata, globally agent-discoverable, multilingual, and utility-priced.

### §H.2 BREAKING predicates

Custody of raw data, optional allAI mediation, merged product identities, or companion override of CORE is BREAKING.

### §H.3 REVIEW predicates

Review new customer surfaces, listing schemas, conduit capabilities, branding, connected-mode behavior, or deferred-scope proposals.

### §H.4 SAFE predicates

Explanatory prose is safe only when it preserves every durable boundary and current decision.

### §H.5 Boundary definitions

#### module

The four product pillars and their approved product-decision references.

#### public contract

Marketplace functions, customer surfaces, discovery metadata, data boundary, mediation, language, branding, and pricing.

#### runtime dependency

Current Business Context, product repositories, marketplace metadata, allAI, and Council decision records.

#### config default

Historical and deferred material is off current surfaces unless explicitly reapproved.

### §H.6 Adjudication

CORE governs invariants, Business Context governs evolvable specifics, and Max resolves product-direction decisions after appropriate Council work.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: A design assigns metadata generation to AIM Data itself., expected_answers: [{kind: classification, label: PRODUCT_BOUNDARY_CONFLICT}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: A public listing page needs agent-readable metadata., expected_answers: [{kind: classification, label: AI_DISCOVERABLE_REQUIRED}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: Federated learning is proposed for a current marketing page., expected_answers: [{kind: classification, label: MAX_DECISION_REQUIRED}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: A proposal stores raw buyer data in ai.market., expected_answers: [{kind: classification, label: NON_CUSTODIAL_VIOLATION}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-01], scenario: A flow lets buyers contact sellers without allAI mediation., expected_answers: [{kind: classification, label: MEDIATION_VIOLATION}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-02], scenario: A retired AIM-Node claim appears as a current standalone product., expected_answers: [{kind: classification, label: HISTORICAL_SCOPE_LEAK}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: A conduit was incorrectly described as the worker., expected_answers: [{kind: human_action, verb: restore, object: allAI worker boundary, target: product design}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: Deferred scope appears in website copy., expected_answers: [{kind: human_action, verb: remove, object: deferred claim, target: current customer surface}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal raises commission above five percent., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [§H], scenario: AIM Data gains a new approved metadata review screen., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: Historical product prose conflicts with current CORE., expected_answers: [{kind: human_action, verb: prefer, object: current CORE invariant, target: product decision}], weight: 0.090909091}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1266
last_refresh_commit: e4d2057
last_refresh_date: 2026-07-17T22:00:00Z
owner_agent: max
refresh_triggers: [CORE product pillar or invariant changes, Business Context locked-decision changes, Max product or deferred-scope decision]
scheduled_cadence: 30d
last_harness_pass_rate: 1.0
last_harness_date: 2026-07-17T22:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1266 / 2026-07-17T22:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: null
```
