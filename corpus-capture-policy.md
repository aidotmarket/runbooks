---
runbook_id: corpus-capture-policy
domain: allai-corpus
status: ACTIVE
authoritative_for:
  - topic: corpus-capture-policy
    section: §C. Architecture & Interactions
aliases:
  - allai-corpus-policy
error_signatures: []
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-30
system_name: corpus-capture-policy
purpose_sentence: This runbook is the operating authority for what ai.market keeps in allAI semantic memory and the corpus, what it never keeps, and how retention of the transport queue is managed.
owner_agent: sysadmin
escalation_contact: Max (human operator)
lifecycle_ref: §J
authoritative_scope: Capture policy for allAI semantic memory and the corpus - the keep/never-keep rules for Event Ledger admission, entity indexing, the six S1299 capture classes, the S1396 moat capture, and qdrant_sync_outbox transport-row retention. NOT the outbox producer/consumer mechanics themselves; see qdrant-sync-outbox.md. NOT Qdrant hosting; see qdrant.md.
linter_version: 1.0.0
---

# Corpus Capture Policy - What We Keep

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

**Governing principle (Max, 2026-07-30, decision event d0052189-43c2-4251-9684-501ecc8daaf0):** capture only data that is necessary to operate the market, filter repetitive data, and treat metadata about customer data as the most important data. Target: reduce Google embedding API calls and new capture database writes by more than 95% against the 2026-07-21..07-28 baseline (roughly 55,000 rows and 32,000 embeddings per day, measured 100% internal-operations content).

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Event Ledger admission (embed/never/quarantine) | SHIPPED | `app/services/qdrant_event_admission.py` | `tests/test_qdrant_event_admission_s1194.py` | 2026-07-30 |
| Event outbox write conditional on admission | SHIPPED | `app/services/state_service.py` | `tests/test_qdrant_sync_worker_s1194.py` | 2026-07-30 |
| Quarantine counter and classification cooldown | SHIPPED | `app/services/qdrant_event_admission.py` | `tests/test_qdrant_event_admission_s1194.py` | 2026-07-30 |
| Entity churn-prefix denylist | PARTIAL | `app/services/state_service.py` | `tests/test_qdrant_producer_coalescing_s1194.py` | 2026-07-30 |
| Entity default-DENY admission at producers | PLANNED | — | — | 2026-07-30 |
| Corpus control plane (six classes, flags off) | PLANNED | — | — | 2026-07-30 |
| Structure-fingerprint moat capture (S1396) | PLANNED | — | — | 2026-07-30 |
| Outbox done-row retention sweep | GAP | — | — | 2026-07-30 |
| Embedding cost/volume attribution alarm | GAP | — | — | 2026-07-30 |

Status notes: "Entity default-DENY admission" is BQ-CORPUS-CAPTURE-TAXONOMY-S1299 Chunk 2 (spec `specs/BQ-CORPUS-CAPTURE-TAXONOMY-S1299-GATE2.md` at c233c9597aa1e812ba957d7139649cb0ec762917 in ai-market-backend). "Corpus control plane" is S1299 Chunk 1, dispatched to MP 2026-07-30 (task 4f658f20). The retention sweep and the attribution alarm have no owning build yet; the sweep is currently a Max-gated manual operation (§E E-03) and the attribution gap is the detection failure behind the July 2026 cost incident (allai_cost_daily has only zero rows).

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Event admission | `app/services/qdrant_event_admission.py` | `state_events`, `qdrant_event_type_quarantine` | StateService.record_event | classify_event_type returns embed, never, or quarantine; only embed writes an outbox row; unknown types increment a content-free quarantine counter awaiting human classification. |
| Entity indexing gate | `app/services/state_service.py` | `state_entities`, `qdrant_sync_outbox` | Qdrant sync consumer | Today: config denylist QDRANT_ENTITY_DENYLIST_PREFIXES only; denylisted entities are marked not semantically indexable and their Qdrant points are deleted by the consumer. After S1299 Chunk 2: default-DENY admit() at every producer, no outbox row for non-admitted writes. |
| Corpus control plane | `app/services/corpus_policy.py` | corpus tables per S1299 §4.1 | admission service, curator workflow | S1299 Chunk 1, in build. All classes and workers default off. Postgres is corpus of record; Qdrant is a derived projection. |
| Transport queue | `app/services/qdrant_sync_worker.py` | `qdrant_sync_outbox` | Vertex embeddings, Qdrant | Transport only, never canonical. Processed rows are purgeable; canonical content lives in state_entities and state_events. |

### §C.1 What we KEEP - current, live today

1. **Events, admit-list only.** Event types whose meaning is decision-grade for operating the platform: decisions, approvals and verdicts, incidents and resolutions, architecture and commitments, security events, deployment failures, lifecycle transitions, ACL violations, identity-assertion mismatches, reviews and cross-reviews. Verified live volume after admission shipped: 79 embedded events in the 7 days to 2026-07-30, versus roughly 30,000 per day before.
2. **Entities, until S1299 Chunk 2 lands.** Everything except the configured denylist prefixes still embeds on every write. This is a known temporary non-compliance with the governing principle, measured at roughly 30,000 internal embeddings per day, and is exactly what Chunk 2 removes.

### §C.2 What we KEEP - the corpus, as S1299 chunks land

Only these six classes exist; everything else is denied by default at the producer:

1. **market_demand_aggregate** - k-anonymous (k>=5) aggregates of published demand: category, format, regulated-domain, geography band, price band, urgency band, time bucket. Never request titles, descriptions, buyer identity, or free text.
2. **market_supply_public** - published, public-safe listing and AIM tool taxonomy, declared capabilities, availability state. Never seller email, private payloads, sample data, or drafts.
3. **external_market_signal** - curator-approved themes from public sources with evidence counts. Never raw posts, authors, handles, URLs, or quotes.
4. **operational_learning** - bounded structured lessons with outcome codes from platform operations, each subject to a measured retrieval-to-resolution feedback loop and pruned without demonstrated lift. Never full state bodies, event payloads, customer identifiers, secrets, or chain-of-thought.
5. **approved_knowledge** - versioned, approved documentation with owner, authority, review date, and supersession.
6. **curated_ai_output** - human-curated AI synthesis with source references and model provenance, down-weighted at 0.20 and experiment-gated.

### §C.3 What we KEEP - the moat capture (S1396, filed, design pending)

Per metadata-generation interaction: the structure fingerprint of the customer source (schema shape, never content), the metadata allAI generated for it, the seller's corrections to that metadata, and persisted equivalence mappings between differently-labeled listings that describe the same kind of data. This is the compounding classification-and-matching asset Max defined as the long-term moat on 2026-07-29.

### §C.4 What we NEVER keep

- Raw customer data in any form or transit path (non-custodial invariant, CORE S1/P2). Absolute.
- Machine housekeeping: cursors, heartbeats, scheduler ticks, unchanged-status polls, duplicate retries, session opens, ownership claims and releases, config-change chatter, dispatch results.
- The dropped classes with no enum value: raw buyer or search queries, raw customer prompts, support and chat transcripts, emails and notifications, CRM notes, order and delivery payloads, uploaded or delivered datasets, row-level clickstream, raw social posts, arbitrary web scrape, unreviewed AI output, chain-of-thought, model traces, and miscellaneous memory.
- PII anywhere on the capture path: admission is fail-closed REJECT, never redact-and-keep, and rejections persist no content, spans, or pattern names - only aggregate reason-code counters.

### §C.5 Retention of the transport queue

`qdrant_sync_outbox` is transport, not record. Rows with status done are purgeable after a short buffer; dead_letter rows are kept for diagnosis until their root cause is closed. One-shot purge executed 2026-07-30 under Max GO (event d0052189): 498,000 processed rows removed, 1.3 GB, canonical tables untouched. No automatic sweep exists yet (§B GAP); until one ships, run §E E-03 under the same gating.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| SysAdmin | Measure capture volume and composition | SQL in §E E-01 | read-only backend DB | COMPLETE |
| SysAdmin | Review and classify quarantined event types | SQL in §E E-02 plus code edit per §G G-01 | backend DB read, PR authorship | COMPLETE |
| Vulcan/Mars | One-shot purge of processed outbox rows | SQL in §E E-03 | production DB write with explicit Max GO | COMPLETE |
| Vulcan/Mars | Extend event admit/never rules | code edit per §G G-01 with Council review | PR authorship | COMPLETE |
| Corpus Curator (S1299 C6) | Class-policy ownership and candidate curation | S1299 curator workflow | corpus_curator application role | PLANNED |

## §E. Operate - Serving Customers

```yaml operate
- id: E-01
  trigger: Verify capture health and policy compliance (daily or on any cost alert)
  pre_conditions:
    - read-only database access
  tool_or_endpoint: "psql: SELECT date_trunc('day', created_at)::date, target_type, status, count(*) FROM qdrant_sync_outbox GROUP BY 1,2,3 ORDER BY 1; and SELECT indexing_disposition, count(*) FROM state_events WHERE ts >= now() - interval '7 days' GROUP BY 1"
  argument_sourcing:
    dsn: scripts/test-db-dsn.sh from the ai-market checkout root
  idempotency: IDEMPOTENT
  expected_success:
    shape: daily outbox counts in the low hundreds; admitted (embed) events in the tens per day
    verification: no single target_id repeats more than a handful of times per day; embed disposition is a small fraction of total events
  expected_failures:
    - signature: thousands of rows per day for one target_type
      cause: an unfiltered producer or a rule regression; go to §F F-01
  next_step_success: done
  next_step_failure: §F F-01
- id: E-02
  trigger: Weekly quarantine review - classify unknown event types
  pre_conditions:
    - read-only database access
  tool_or_endpoint: "psql: SELECT event_type, count, first_seen_at, last_seen_at FROM qdrant_event_type_quarantine WHERE status='open' ORDER BY count DESC"
  argument_sourcing:
    dsn: scripts/test-db-dsn.sh
  idempotency: IDEMPOTENT
  expected_success:
    shape: open list reviewed; each type either added to the never list, the embed list, or left counting
    verification: high-count operational chatter never stays open two consecutive reviews
  expected_failures:
    - signature: open count grows without review
      cause: no owner ran the review; escalate to owner_agent
  next_step_success: §G G-01 for any rule change
  next_step_failure: escalation to Max
- id: E-03
  trigger: Purge processed transport rows (Max-gated maintenance)
  pre_conditions:
    - explicit Max GO recorded as a decision event
    - consumer healthy, no pending backlog being diagnosed
  tool_or_endpoint: "psql: DELETE FROM qdrant_sync_outbox WHERE status IN ('done','superseded_s1194') AND processed_at < now() - interval '1 hour'; then VACUUM ANALYZE qdrant_sync_outbox"
  argument_sourcing:
    dsn: scripts/test-db-dsn.sh
    buffer: keep at least the last hour of done rows for in-flight diagnosis
  idempotency: IDEMPOTENT
  expected_success:
    shape: done count drops to the recent-buffer size; dead_letter and pending untouched
    verification: SELECT status, count(*) FROM qdrant_sync_outbox GROUP BY status
  expected_failures:
    - signature: pending or dead_letter rows deleted
      cause: wrong predicate; restore is not possible, transport rows are not backed up - re-check the statement before running
  next_step_success: done
  next_step_failure: escalation to Max
```

## §F. Isolate - Diagnosing Deviations

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Embedding or outbox volume spikes above policy expectations | new unfiltered producer, entity churn before S1299 Chunk 2, rule regression | run §E E-01; then `SELECT split_part(target_id,':',1), count(*), count(distinct target_id) FROM qdrant_sync_outbox WHERE created_at >= now() - interval '1 day' AND target_type='entity' GROUP BY 1 ORDER BY 2 DESC` to see namespace and repetition | §G G-03 | CONFIRMED |
| F-02 | Quarantine backlog grows and stays open | weekly review not happening, genuinely novel event families | §E E-02 listing ordered by count | §G G-01 | CONFIRMED |
| F-03 | Junk admitted through token matching | an operational event type contains an embed token such as decision or review | `SELECT event_type, count(*) FROM state_events WHERE indexing_disposition='embed' AND ts >= now() - interval '7 days' GROUP BY 1 ORDER BY 2 DESC` and judge each type against §C.1 | §G G-01 | HYPOTHESIZED |
| F-04 | Google spend rises with no matching capture volume | generation-side spend (agents, mediation), not capture; or attribution gap hides the driver | compare §E E-01 volumes with GCP Monitoring aiplatform request_count; remember allai_cost_daily contains only zero rows and proves nothing | — | CONFIRMED |

## §G. Repair - Fixing Problems

```yaml repair
- id: G-01
  symptom_ref: F-02
  component_ref: Event admission
  root_cause: unknown or misclassified event type
  repair_entry_point: app/services/qdrant_event_admission.py
  change_pattern: add the type to _NEVER_EXACT/_NEVER_PREFIXES for housekeeping or _EMBED_EXACT for decision-grade meaning; never widen _EMBED_TOKENS casually because substring matching admits every future type containing the token; ship via PR with Council review
  rollback_procedure: revert the rule commit; quarantine counters are unaffected
  integrity_check: the type's disposition changes in classify_event_type unit tests and its quarantine row moves to classified on next occurrence
- id: G-02
  symptom_ref: F-01
  component_ref: Transport queue
  root_cause: processed transport rows accumulating (no automatic sweep exists)
  repair_entry_point: runbooks/corpus-capture-policy.md §E E-03
  change_pattern: run the Max-gated one-shot purge; file or advance the recurring-sweep build so the manual step disappears
  rollback_procedure: none - purged transport rows are not restorable; canonical data is unaffected by design
  integrity_check: table row count equals recent buffer plus dead_letter plus pending
- id: G-03
  symptom_ref: F-01
  component_ref: Entity indexing gate
  root_cause: internal entity churn embedding on every write before S1299 Chunk 2
  repair_entry_point: app/core/config.py
  change_pattern: preferred repair is landing S1299 Chunk 2 (default-DENY at producers, no outbox row at all); the interim lever QDRANT_ENTITY_DENYLIST_PREFIXES stops Vertex embeds for matching prefixes BUT the consumer deletes the matching Qdrant points and no re-embed tooling exists until S1299 Chunk 3, so treat a broad denylist extension as a production-data change needing Max approval
  rollback_procedure: removing a prefix stops further deletes but does not restore deleted points until Chunk 3 rebuild tooling exists
  integrity_check: §E E-01 daily entity counts fall to policy expectations without unexplained Qdrant point loss for kept namespaces
```

## §H. Evolve - Extending the System

### §H.1 Invariants

- The governing principle in §A binds every future capture proposal: necessary to operate the market, repetition filtered, customer-data metadata first.
- Default-DENY is the posture. A new capture class exists only through the S1299 class registry with a named owner role, a measured feedback loop, and a prune rule. No class, no capture.
- Non-custodial is absolute and senior to every other goal in this runbook.
- Rejection paths persist no content, ever. Counters and stable reason codes only.
- Postgres is the corpus of record; Qdrant is derived and rebuildable. Any change that makes Qdrant the only copy of something is wrong.
- Repetition is filtered at the producer, not the consumer: a filtered record writes no row at all.
- The Event Ledger (state_events) itself remains an append-only audit record independent of capture; capture policy governs what is embedded and projected, not what is audited. Ledger retention belongs to BQ-DATABASE-CLEANUP-RETENTION-S1300.

### §H.2 Change-class predicate tree

BREAKING if any change captures raw customer data or PII, persists rejected content, adds a capture path that bypasses admission, makes Qdrant canonical, or removes the k>=5 gate from behavioral aggregates.

REVIEW if any change adds or retires a capture class, changes admit/never event rules, changes denylist prefixes, changes retention windows, or adds a producer.

SAFE if the change is documentation, adds tests, tightens a reject path, or adds content-free telemetry.

### §H.3 Boundary definitions

`module`: `app/services` for admission and policy, `app/allai/evolution` for legacy memory surfaces, migrations as a peer tree.

`public contract`: the six-class enum, admission reason codes, quarantine table shape, and the governing principle in §A.

`runtime dependency`: Postgres, embedding provider (swappable per CORE S6), Qdrant, Railway.

`config default`: QDRANT_ENTITY_DENYLIST_PREFIXES currently `infra:git-push-poller-cursor`; all S1299 class flags default false.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [§E E-01]
    scenario: A Google budget alert arrives; establish whether capture volume is within policy.
    expected_answers: [{kind: sql, query_contains: [qdrant_sync_outbox, "count(*)"]}]
    weight: 0.125
  - id: I-02
    type: operate
    refs: [§E E-03]
    scenario: The outbox table is 1.4 GB of processed rows; reduce it safely.
    expected_answers: [{kind: human_instruction, action: obtain Max GO then run the E-03 purge with the one-hour buffer}]
    weight: 0.125
  - id: I-03
    type: isolate
    refs: [§F F-01]
    scenario: Entity embeddings run at 30,000 per day; find what and how repetitive.
    expected_answers: [{kind: sql, query_contains: [split_part, distinct target_id]}]
    weight: 0.125
  - id: I-04
    type: isolate
    refs: [§F F-03]
    scenario: An event type named budget_decision_poll floods the embed path.
    expected_answers: [{kind: classification, verdict: token-match admission through decision; judge against §C.1 and repair via G-01}]
    weight: 0.125
  - id: I-05
    type: repair
    refs: [§G G-01]
    scenario: A high-count housekeeping event type sits open in quarantine.
    expected_answers: [{kind: human_instruction, action: add to _NEVER_EXACT or _NEVER_PREFIXES via reviewed PR}]
    weight: 0.125
  - id: I-06
    type: repair
    refs: [§G G-03]
    scenario: Stop the internal entity embed bleed this week without waiting for Chunk 2.
    expected_answers: [{kind: human_instruction, action: treat denylist extension as a Max-approved production-data change because Qdrant points are deleted with no rebuild tooling}]
    weight: 0.125
  - id: I-07
    type: evolve
    refs: [§H]
    scenario: Proposal to log rejected candidate text for debugging.
    expected_answers: [{kind: classification, verdict: BREAKING}]
    weight: 0.125
  - id: I-08
    type: evolve
    refs: [§H]
    scenario: Ambiguous - a proposal to capture per-buyer search strings hashed with SHA-256 so they are "not raw data".
    expected_answers: [{kind: classification, verdict: BREAKING - hashed customer identifiers and query content remain customer data and are a dropped class; only k-anonymous aggregates per market_demand_aggregate are permitted}]
    weight: 0.125
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1406
last_refresh_commit: 1debb321039173320854b8c5f9db429acec25f88
last_refresh_date: 2026-07-30T12:00:00Z
owner_agent: sysadmin
refresh_triggers:
  - each S1299 chunk landing
  - S1396 design approval
  - any change to event admission rules or denylist prefixes
  - any capture-related cost incident
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-30T12:00:00Z
first_staleness_detected_at: null
```

## §K. Linter / Compliance Metadata

```yaml compliance
linter_version: 1.0.0
standard_ref: specs/BQ-RUNBOOK-STANDARD.md
sections_present: [A, B, C, D, E, F, G, H, I, J, K]
agent_forms:
  B: capability_matrix
  C: architecture_table
  D: agent_capability_map
  E: operate_yaml
  F: symptom_index
  G: repair_yaml
  H: predicate_tree
  I: scenario_set
  J: lifecycle_metadata
router_registration: TOPIC-ROUTER.md
last_lint_run: S1406 / 2026-07-30T12:00:00Z
```
