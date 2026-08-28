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
owner: sysadmin
last_verified_at: 2026-08-28
system_name: corpus-capture-policy
purpose_sentence: This runbook is the operating authority for what ai.market retains as safe corpus evidence, what may be promoted to trusted knowledge, what may enter active projection, and what it never keeps.
owner_agent: sysadmin
escalation_contact: Max (human operator)
lifecycle_ref: §J
authoritative_scope: Capture policy for allAI semantic memory and the corpus - the keep/never-keep rules for Event Ledger admission, entity indexing, the S1299 capture classes, the S1396 corpus-capture taxonomy, human trust decisions, future automation thresholds, and qdrant_sync_outbox transport-row retention. NOT the outbox producer/consumer mechanics themselves; see qdrant-sync-outbox.md. NOT Qdrant hosting; see qdrant.md.
linter_version: 1.0.0
---

<!-- Canonical source path: runbooks/corpus-capture-policy.md -->

# Corpus Capture Policy - What We Keep

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

**Governing principle (Max, 2026-07-30, decision event d0052189-43c2-4251-9684-501ecc8daaf0):** capture only data that is necessary to operate the market, filter repetitive data, and treat metadata about customer data as the most important data. Target: reduce Google embedding API calls and new capture database writes by more than 95% against the 2026-07-21..07-28 baseline (roughly 55,000 rows and 32,000 embeddings per day, measured 100% internal-operations content).

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Event Ledger corpus admission | SHIPPED | `app/services/state_service.py` | `tests/test_state_corpus_disposition.py` | 2026-08-21 |
| Event compatibility classifier and exact-list worker gate | SHIPPED | `app/services/qdrant_event_admission.py` | `tests/test_qdrant_event_admission_s1194.py` | 2026-08-21 |
| Exact-row quarantine reconciliation, weekly owner ticket, and bounded failure escalation | SHIPPED | `app/allai/agents/sysadmin/monitors.py` | `tests/test_sysadmin_qdrant_monitoring_s1194.py`, `tests/test_sysadmin_quarantine_obligation_s1545.py` | 2026-08-21 |
| Entity churn-prefix denylist | PARTIAL | `app/services/state_service.py` | `tests/test_qdrant_producer_coalescing_s1194.py` | 2026-07-30 |
| Entity default-DENY admission at producers | SHIPPED | `app/services/state_service.py` | `tests/test_state_corpus_disposition.py` | 2026-08-21 |
| Corpus control plane (six classes) | SHIPPED | `app/services/corpus_admission_service.py` | `tests/test_corpus_admission.py` | 2026-08-21 |
| Structure-fingerprint moat capture (S1396) | PARTIAL | `app/services/metadata_corpus_capture.py` | `tests/test_s1396_chunk_c.py` | 2026-08-22 |
| S1396 semantic trust ledger and Corpus console | PARTIAL | `app/services/corpus_trust_service.py` | `tests/test_s1396_corpus_trust.py` | 2026-08-28 |
| Outbox done-row retention sweep | PLANNED | — | — | 2026-07-30 |
| Embedding cost/volume attribution alarm | PLANNED | — | — | 2026-07-30 |

Status notes: S1299 corpus admission and producer default-DENY are live. `CorpusAdmissionService`, called by `StateService`, is the current writer authority; the older `admit_event` helper is not on that path. S1396 B-schema, B-activate, and the default-off Chunk C metadata-generation and seller-correction producers are live. The S1632 trust-ledger/API and ops Console changes are candidates until their exact commits merge and deploy. All relevant capture and projection flags remain disabled; no candidate status in this runbook authorizes activation. The retention sweep and the attribution alarm have no owning build yet; the sweep is currently a Max-gated manual operation (§E E-03) and the attribution gap is the detection failure behind the July 2026 cost incident (allai_cost_daily has only zero rows).

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Corpus admission authority | `StateService.append_event` → `CorpusAdmissionService.admit` | `state_events`, corpus tables, `qdrant_sync_outbox` | producer writes, curator workflow, Qdrant sync consumer | Current S1299 authority. Producer writes are default-DENY; only admitted content receives the corresponding corpus disposition and derived transport work. |
| Event compatibility classifier and legacy quarantine obligation | `app/services/qdrant_event_admission.py`, `app/allai/agents/sysadmin/monitors.py` | `qdrant_event_type_quarantine` | Qdrant sync worker, weekly SupportTicket | Exact EMBED/NEVER rules remain a worker-side compatibility gate. `admit_event` has no current production caller. The existing monitor reconciles an `open` row to `classified` only when its normalized type is in an exact set, before paging rows that remain unknown. |
| Entity indexing gate | `app/services/state_service.py`, `app/services/corpus_admission_service.py` | `state_entities`, corpus tables, `qdrant_sync_outbox` | Qdrant sync consumer | S1299 producer admission is default-DENY. Non-admitted writes do not create semantic transport work; Qdrant remains a derived projection. |
| Corpus control plane | `app/services/corpus_admission_service.py` | corpus tables per S1299 | producer admission, curator workflow | The six-class control plane is live. Postgres is corpus of record; Qdrant is a derived projection. |
| S1396 moat-capture foundation and default-off producers | `app/services/metadata_corpus_capture.py`, `app/services/metadata_corpus_curator.py`, `app/tasks/scheduled.py`, S1396 migrations, `scripts/s1396_activate_moat_roles.py` | S1396 capture tables, `corpus_role_assignments` | enrichment, seller edits, admission, later projection/activation | The schema, three approved metadata-moat steward assignments, and Chunk C metadata-generation/seller-correction producers are live. Relevant flags remain off, so the deployed producers write nothing until separately approved activation. |
| S1396 semantic trust boundary and Corpus console | `app/services/corpus_trust_service.py`, `app/api/v1/endpoints/ops_corpus.py`, ops.ai.market `/corpus` | S1396 evidence tables, `corpus_trust_decisions` | authenticated ops review, future projection | Safe admission is not semantic trust. Human decisions are append-only and revisioned. The console can trust, reject, or supersede evidence and records an equivalence rating from 0 to 100. No console action enables capture or projection. CANDIDATE until exact backend/frontend commits deploy. |
| Transport queue | `app/services/qdrant_sync_worker.py` | `qdrant_sync_outbox` | Vertex embeddings, Qdrant | Transport only, never canonical. Processed rows are purgeable; canonical content lives in state_entities and state_events. |

### §C.1 What we KEEP - current, live today

1. **Events, central admission first.** `CorpusAdmissionService` is the writer authority. Decision-grade operating records may be admitted as bounded `operational_learning`; the exact event-type sets remain a secondary worker compatibility gate, not the producer admission decision.
2. **Entities, default-DENY at producers.** S1299 producer admission is live. A non-admitted entity write does not create semantic transport work; configured denylist behavior remains defense in depth.

### §C.2 What we KEEP - the live S1299 corpus classes

Only these six classes exist; everything else is denied by default at the producer:

1. **market_demand_aggregate** - k-anonymous (k>=5) aggregates of published demand: category, format, regulated-domain, geography band, price band, urgency band, time bucket. Never request titles, descriptions, buyer identity, or free text.
2. **market_supply_public** - published, public-safe listing and AIM tool taxonomy, declared capabilities, availability state. Never seller email, private payloads, sample data, or drafts.
3. **external_market_signal** - curator-approved themes from public sources with evidence counts. Never raw posts, authors, handles, URLs, or quotes.
4. **operational_learning** - bounded structured lessons with outcome codes from platform operations, each subject to a measured retrieval-to-resolution feedback loop and pruned without demonstrated lift. Never full state bodies, event payloads, customer identifiers, secrets, or chain-of-thought.
5. **approved_knowledge** - versioned, approved documentation with owner, authority, review date, and supersession.
6. **curated_ai_output** - human-curated AI synthesis with source references and model provenance, down-weighted at 0.20 and experiment-gated.

### §C.3 What we KEEP - the moat capture (S1396, foundation and default-off producers live)

Per metadata-generation interaction: the structure fingerprint of the customer source (schema shape, never content), the metadata allAI generated for it, the seller's corrections to that metadata, and persisted equivalence mappings between differently-labeled listings that describe the same kind of data. This is the compounding classification-and-matching asset Max defined as the long-term moat on 2026-07-29.

The B-schema and B-activate foundation is deployed at backend commit `925e3e072bcba1ae8a601a7c961d3738cf6898ec` (Railway deployment `a72aeec9-444b-403b-984e-26d30fe4ed1d`). Production verification recorded exactly one active assignment for each of `metadata_moat_interaction_steward`, `metadata_moat_correction_steward`, and `metadata_moat_equivalence_steward`, zero legacy-role rows, all three S1396 capture flags false, and receipt `/Users/max/koskadeux-state/receipts/s1396/s1396-b-activate-925e3e072b.json` with mode `0600` and digest `d96819ee006599716f0b7329d303ebac952a9fe75bd750d3ec09dcf11ef094bd`. This evidence activates governance ownership only; it does not activate capture producers or complete S1396.

Chunk C is deployed at backend merge `54f6299129753266d9842638acc42f07b8d701a1`: API deployment `028c0e19-bbba-4d23-b790-936399910e5c`, worker `fcfc3108-cb27-4b49-8b70-29c527c759e4`, beat `6af5269d-176b-467a-a998-9f6db469517f`, and backup `a4914ef6-6c4c-4a89-bac7-c04c8750891a`, all `SUCCESS`. Read-only production verification on 2026-08-22 UTC recorded Alembic current/head `s1595_s1396_c_durability`, both new durability tables and their constraints present, zero rows in those tables, all five relevant/global flags absent and therefore on code defaults, and zero Chunk C interactions, corrections, corpus records, or projection rows since deployment. The code is live but capture remains disabled; activation, projection, equivalence mappings, and completion of S1396 remain separate governed work.

### §C.3.1 The corpus-capture taxonomy: evidence is not trust

The permanent-memory boundary has three separate layers. A record may advance only one layer at a time:

1. **Safe evidence** is privacy-safe, provenance-bound observation. It may include AI proposals, seller acceptance, seller correction, negative outcomes, unresolved schema-family proposals, and proposed equivalence edges. Admission proves only that retaining the record is allowed; it does not prove the record is correct.
2. **Trusted knowledge** is safe evidence with a current semantic decision. In v1 only a human curator can create the `trusted`, `rejected`, or `superseded` decision. Decisions are append-only and revisioned; a later decision does not erase history.
3. **Active projection** is a derived, rebuildable view of current trusted knowledge. S1396 projection remains disabled and deferred. No evidence row, numerical score, or console decision may directly switch a flag or enqueue projection work.

Negative evidence is useful and may remain in the safe-evidence layer with typed outcome codes. It must never be retrieved as truth. AI-generated metadata has zero self-confirming authority: model repetition, confidence, or reuse of its own proposal is not independent evidence. Seller acceptance of AI-drafted metadata is one weak, listing-scoped evidence vote; a seller correction is stronger but is not universal taxonomy truth.

### §C.3.2 Equivalence policy: hard gates first, score second

Every dataset-equivalence edge has a numerical rating from 0 to 100. The score explains degree of structural equivalence and prioritizes review; it never overrides a hard gate and does not by itself prove truth.

- **Hard gates:** resolved subjects and scope; complete provenance and lineage; no raw customer data, PII, secret, redacted placeholder, unresolved typed conflict, replay, or AI self-corroboration. A failed gate makes the edge non-promotable regardless of score.
- **0-40:** reject territory for future shadow automation. Safe negative evidence may remain.
- **41-84:** manual review.
- **85-100:** future automation candidate only when every hard gate passes and independent evidence is sufficient. The initial automation target requires three independent non-AI observations, or two independent observations plus curator confirmation. Repeated captures from the same seller, account, device/session, source snapshot, or reused AI proposal collapse to one evidence cluster.
- **Typed conflict veto:** incompatible keys, types, cardinality, nullability, scope, or lineage blocks automatic promotion even when text or name similarity is high.
- **Scope rule:** similarity may prove a narrow `subset_of` relation without proving `same_data_kind`, semantic interchangeability, or universal equivalence.

The initial thresholds are Council calibration seeds, not active automation. Capture and projection stay off while shadow labels are collected. Do not enable automatic trusted promotion until audited precision in the 85-100 band is at least 99%, placeholder detection is 100% on the adversarial fixture set, AI self-promotion observed count is zero, and conflict detection is at least 95% on injected conflicts.

### §C.4 What we NEVER keep

- Raw customer data in any form or transit path (non-custodial invariant, CORE S1/P2). Absolute.
- Machine housekeeping: cursors, heartbeats, scheduler ticks, unchanged-status polls, duplicate retries, session opens, ownership claims and releases, config-change chatter, dispatch results.
- The dropped classes with no enum value: raw buyer or search queries, raw customer prompts, support and chat transcripts, emails and notifications, CRM notes, order and delivery payloads, uploaded or delivered datasets, row-level clickstream, raw social posts, arbitrary web scrape, unreviewed AI output, chain-of-thought, model traces, and miscellaneous memory.
- PII anywhere on the capture path: admission is fail-closed REJECT, never redact-and-keep, and rejections persist no content, spans, or pattern names - only aggregate reason-code counters.
- Redacted or sentinel semantic placeholders such as `redacted_term`, `redacted_stem`, `[redacted]`, `unknown`, `masked`, or an empty fallback as taxonomy terms, schema-family anchors, or equivalence endpoints. Unsafe names may leave content-free quarantine coordinates and aggregate reason codes only; they never create a semantic row.

### §C.5 Retention of the transport queue

`qdrant_sync_outbox` is transport, not record. Rows with status done are purgeable after a short buffer; dead_letter rows are kept for diagnosis until their root cause is closed. One-shot purge executed 2026-07-30 under Max GO (event d0052189): 498,000 processed rows removed, 1.3 GB, canonical tables untouched. No automatic sweep exists yet (the §B retention-sweep row is PLANNED with no owning build); until one ships, run §E E-03 under the same gating.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| SysAdmin | Measure capture volume and composition | SQL in §E E-01 | read-only backend DB | COMPLETE |
| SysAdmin + Max (human operator) | Surface and discharge the weekly quarantined-event-type classification obligation | SupportTicket (AI-owned since S1585: human_required=false, assignee ai_agent/sysadmin; discharged via the TICKETS panel or the E-02 SQL; appears on neither Max's needs-Max rows nor the OPS Attention list), read-only SQL in §E E-02, code edit per §G G-01, then existing-monitor reconciliation | owner-surface ticket handling, backend DB read, PR authorship | COMPLETE |
| Vulcan/Mars | One-shot purge of processed outbox rows | SQL in §E E-03 | production DB write with explicit Max GO | COMPLETE |
| Vulcan/Mars | Extend event admit/never rules | code edit per §G G-01 with Council review | PR authorship | COMPLETE |
| Corpus Curator (S1299 C6) | Class-policy ownership and candidate curation | S1299 curator workflow | corpus_curator application role | PLANNED |
| Max / Corpus Curator | Review privacy-safe S1396 evidence; record trust, rejection, supersession, and 0-100 equivalence rating | ops.ai.market CORPUS tab; `/api/v1/ops/corpus/` | authenticated ops operator mapped to an active application user | PLANNED |

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
  trigger: "Weekly P2 quarantine review - classify unknown event types when the fixed-subject SupportTicket is refreshed by the sysadmin obligation run (since S1585 the ticket is AI-owned: human_required=false, assignee ai_agent/sysadmin; it appears on neither Max's needs-Max rows nor the OPS Attention list, and is discharged via the TICKETS panel or the E-02 SQL)"
  pre_conditions:
    - authenticated operator access to the ops.ai.market TICKETS tab
    - read-only database access
  tool_or_endpoint: "https://ops.ai.market TICKETS tab (the standalone /for-max page is retired in S1585); psql ticket verification: SELECT public_ref, status, human_required, created_at, updated_at FROM support_ticket WHERE subject='[auto] Qdrant event-type quarantine requires weekly classification' AND requester_key='agent:sysadmin' AND status NOT IN ('resolved','closed') ORDER BY created_at; read-only classification: SELECT event_type, count, first_seen_at, last_seen_at FROM qdrant_event_type_quarantine WHERE status='open' ORDER BY count DESC"
  argument_sourcing:
    dsn: scripts/test-db-dsn.sh
    ticket_subject: "[auto] Qdrant event-type quarantine requires weekly classification"
    deployed_backend: "ce64f51e8b377eb07520aae6210c41bf3979d5dd on API deployment 2279e5d0-9488-439d-a322-ab385196f2cf, beat c9ae4975-8267-439c-9aa5-9734163b7c9b, and worker d6358539-b01c-436e-8729-db7dd66e6c3e"
  idempotency: IDEMPOTENT
  expected_success:
    shape: "a normal breach creates or reuses exactly one open waiting_internal SupportTicket (AI-owned since S1585: human_required=false, assignee ai_agent/sysadmin) visible on the TICKETS tab; the open quarantine list is reviewed and each type is either added to an exact never/embed list or deliberately left unknown"
    verification: after an exact-rule deployment, the existing monitor changes only matching open-row status to classified before it pages remaining unknowns; a read-only query proves the intended rows are no longer open; repeated or rotating unknown breaches reuse one ticket; the operator resolves that ticket only after the monitor is healthy; routine backlog sends no Telegram page and no customer data changes
  expected_failures:
    - signature: open count grows without review
      cause: the P2 classification obligation ticket remains open; review it on the TICKETS tab without paging Telegram
    - signature: the fixed-subject ticket is absent or duplicated because its query or persistence failed
      cause: support-ticket owner-surface failure, not a higher-priority quarantine backlog; the bounded P1 operational escalation pages Telegram with stable dedup
  next_step_success: §G G-01 for any rule change, then resolve the fixed-subject ticket through the supported ticket surface only after the read-only status query is healthy
  next_step_failure: restore support-ticket query/persistence from the deduplicated P1 operational escalation; otherwise continue the P2 review on the TICKETS tab
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
- id: E-04
  trigger: Review a pending S1396 corpus item
  pre_conditions:
    - authenticated operator access to the ops.ai.market CORPUS tab
    - evidence has already passed the privacy-safe admission boundary
    - capture and projection flags are not changed by this procedure
  tool_or_endpoint: "https://ops.ai.market/corpus; GET /api/v1/ops/corpus/?trust_state=pending; POST /api/v1/ops/corpus/{evidence_kind}/{evidence_id}/decision"
  argument_sourcing:
    evidence_kind: selected from the closed console filter
    evidence_id: selected from the pending item
    equivalence_rating: operator assessment from 0 through 100, required only for an equivalence edge
    reason_code: selected from the closed decision choices; no free-text customer material
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: one new revision in corpus_trust_decisions; item moves to trusted, rejected, or superseded; no projection job is created
    verification: refresh the same filter and inspect decision_revision, reason_code, rating, and state; confirm the capture/projection banner did not change
  expected_failures:
    - signature: decision returns HTTP 403
      cause: the supplied internal-key reviewer is not in the approved ops allowlist; use an approved ops identity and never widen the allowlist to bypass review
    - signature: trust returns HTTP 409
      cause: pre-publish evidence, an unsafe or redacted placeholder, another hard gate, or a stale decision revision blocks promotion; refresh first, then reject or leave pending, never bypass
    - signature: decision returns HTTP 422
      cause: the active ops reviewer identity is missing, or an equivalence edge has no required 0-100 rating
  next_step_success: done
  next_step_failure: §F F-05
- id: E-05
  trigger: Before any S1396 capture, automatic-trust, or projection activation proposal
  pre_conditions:
    - read-only production database and Railway configuration access
  tool_or_endpoint: "read-only production queries for S1396 table counts, corpus_trust_decisions by latest state, corpus_projection_outbox, and exact Railway CORPUS_* flag values"
  argument_sourcing:
    deployed_sha: exact Railway deployment source SHA
    flags: the three S1396 capture flags plus CORPUS_APPROVED_KNOWLEDGE_ENABLED and CORPUS_GLOBAL_FREEZE_ENABLED
  idempotency: IDEMPOTENT
  expected_success:
    shape: exact deployment identity; no redacted semantic row; trusted decisions have human reviewer and valid revision; projection remains empty until a separately approved projection release
    verification: reconcile database counts, latest decisions, deployment SHA, and literal flag values; do not infer absent flags as enabled
  expected_failures:
    - signature: any semantic row contains a redacted placeholder or has no current trust lineage
      cause: corpus contamination; freeze activation and use §G G-04
  next_step_success: return evidence to the activation gate without changing flags
  next_step_failure: §G G-04
```

## §F. Isolate - Diagnosing Deviations

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Embedding or outbox volume spikes above policy expectations | new unfiltered producer, entity churn before S1299 Chunk 2, rule regression | run §E E-01; then `SELECT split_part(target_id,':',1), count(*), count(distinct target_id) FROM qdrant_sync_outbox WHERE created_at >= now() - interval '1 day' AND target_type='entity' GROUP BY 1 ORDER BY 2 DESC` to see namespace and repetition | §G-03 | CONFIRMED |
| F-02 | Quarantine backlog grows and stays open | weekly review not happening, genuinely novel event families | §E E-02 listing ordered by count | §G-01 | CONFIRMED |
| F-03 | Junk admitted through token matching | an operational event type contains an embed token such as decision or review | `SELECT event_type, count(*) FROM state_events WHERE indexing_disposition='embed' AND ts >= now() - interval '7 days' GROUP BY 1 ORDER BY 2 DESC` and judge each type against §C.1 | §G-01 | HYPOTHESIZED |
| F-04 | Google spend rises with no matching capture volume | generation-side spend (agents, mediation), not capture; or attribution gap hides the driver | compare §E E-01 volumes with GCP Monitoring aiplatform request_count; remember allai_cost_daily contains only zero rows and proves nothing |  | CONFIRMED |
| F-05 | Corpus item cannot be trusted, or trusted knowledge appears semantically wrong | hard gate failure, insufficient independent evidence, reviewer conflict, redacted placeholder, source withdrawal, or newer contradictory evidence | inspect the item and latest decision in the CORPUS tab; run §E E-05; do not inspect or copy raw customer payloads | §G-04 | CONFIRMED |

## §G. Repair - Fixing Problems

```yaml repair
- id: G-01
  symptom_ref: F-02
  component_ref: Event compatibility classifier and legacy quarantine obligation
  root_cause: unknown or misclassified event type
  repair_entry_point: app/services/qdrant_event_admission.py and the existing qdrant_event_type_quarantine monitor
  change_pattern: add the type to _NEVER_EXACT for housekeeping or _EMBED_EXACT for decision-grade meaning; never widen _EMBED_TOKENS or _NEVER_PREFIXES to discharge a known row; ship via PR with Council review; on the next scheduler cycle the existing monitor reconciles only exact-known open rows before paging remaining unknowns
  rollback_procedure: revert the rule/monitor commit to stop future reconciliation; already-classified rows remain classified because a code revert is not an inverse data mutation; reopening an incorrectly classified row requires a separately authorized exact operation
  integrity_check: the fixed expected-value unit matrix shows the intended exact disposition, broad token/prefix near-misses remain unknown, and a read-only query after the next monitor cycle shows the intended row status is classified while genuinely unknown rows remain open
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
- id: G-04
  symptom_ref: F-05
  component_ref: S1396 semantic trust boundary and Corpus console
  root_cause: trusted evidence is contradicted, withdrawn, unsafe, or superseded
  repair_entry_point: ops.ai.market CORPUS tab and app/services/corpus_trust_service.py
  change_pattern: append a rejected or superseded decision with a closed reason code; if projection exists, remove the derived projection first and rebuild only from current trusted decisions; a privacy or erasure incident separately hard-deletes the exact affected lineage under the applicable privacy procedure
  rollback_procedure: never mutate or delete an ordinary decision revision; append a later curator-confirmed revision after the evidence is re-established
  integrity_check: latest decision is the intended state, older revisions remain auditable, no redacted semantic row exists, and no rejected or superseded item appears in active projection
```

## §H. Evolve - Extending the System

### §H.1 Invariants

- The governing principle in §A binds every future capture proposal: necessary to operate the market, repetition filtered, customer-data metadata first.
- Default-DENY is the posture. A new capture class exists only through the S1299 class registry with a named owner role, a measured feedback loop, and a prune rule. No class, no capture.
- Non-custodial is absolute and senior to every other goal in this runbook.
- Rejection paths persist no content, ever. Counters and stable reason codes only.
- Safe admission and semantic trust are independent gates. A privacy-safe evidence row is never implicitly trusted.
- Corpus trust decisions are human-only in v1, append-only, revisioned, and use closed reason codes. The console accepts no free-text rationale or customer material.
- AI output cannot corroborate itself. Seller evidence is listing-scoped and cannot independently establish a universal taxonomy fact.
- Equivalence is always rated 0-100, but hard gates and typed conflict vetoes are senior to the score.
- Redacted placeholders are void for semantic use: never score them as zero, never match two placeholders, and never retain them as taxonomy or alignment records.
- Postgres is the corpus of record; Qdrant is derived and rebuildable. Any change that makes Qdrant the only copy of something is wrong.
- Repetition is filtered at the producer, not the consumer: a filtered record writes no row at all.
- The Event Ledger (state_events) itself remains an append-only audit record independent of capture; capture policy governs what is embedded and projected, not what is audited. Ledger retention belongs to BQ-DATABASE-CLEANUP-RETENTION-S1300.

### §H.2 BREAKING predicates

- Any change that captures raw customer data or PII is BREAKING.
- Any change that persists rejected content is BREAKING.
- Any change that adds a capture path which bypasses admission is BREAKING.
- Any change that makes Qdrant canonical is BREAKING.
- Any change that removes the k>=5 gate from behavioral aggregates is BREAKING.
- Any change that treats safe admission, an AI confidence, or a numerical equivalence rating as sufficient semantic trust is BREAKING.
- Any change that lets rejected, superseded, pre-publish, or placeholder-bearing evidence enter active projection is BREAKING.

### §H.3 REVIEW predicates

- Adding or retiring a capture class requires REVIEW.
- Changing admit/never event rules requires REVIEW.
- Changing denylist prefixes requires REVIEW.
- Changing retention windows requires REVIEW.
- Adding a producer requires REVIEW.
- Changing trust states, equivalence scoring, hard gates, evidence independence, automated thresholds, or projection eligibility requires REVIEW.

### §H.4 SAFE predicates

- Documentation changes are SAFE when they do not change behavior.
- Adding tests is SAFE when it does not change behavior.
- Tightening a reject path is SAFE when it preserves the governing invariants.
- Adding content-free telemetry is SAFE when it preserves the governing invariants.

### §H.5 Boundary definitions

#### module

`app/services` for admission and policy, `app/allai/evolution` for legacy memory surfaces, and migrations as a peer tree.

#### public contract

The six-class enum, admission reason codes, quarantine table shape, and the governing principle in §A.

#### runtime dependency

Postgres, embedding provider (swappable per CORE S6), Qdrant, and Railway.

#### config default

`QDRANT_ENTITY_DENYLIST_PREFIXES` is currently `infra:git-push-poller-cursor`; all S1299 and S1396 class flags default false. The S1396 Chunk C release does not change any production flag value.

### §H.6 Adjudication

Evaluate §H.2 before §H.3, and §H.3 before §H.4. If the documented predicates do not resolve a classification, do not infer a new policy: escalate the unresolved case to Max and record the resulting ruling before implementation.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A Google budget alert arrives; establish whether capture volume is within policy.
    expected_answers:
      - kind: tool_call
        tool: psql
        argument_keys: [dsn, query]
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-04]
    scenario: A pending equivalence edge is ready for Max to assess in the Corpus console.
    expected_answers:
      - kind: human_action
        verb: record
        object: 0-100 equivalence rating and closed decision
        target: append-only corpus trust revision without enabling projection
    weight: 0.09090909090909091
  - id: I-03
    type: isolate
    refs: [F-01]
    scenario: Entity embeddings run at 30,000 per day; find what and how repetitive.
    expected_answers:
      - kind: tool_call
        tool: psql
        argument_keys: [dsn, query]
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-03]
    scenario: An event type named budget_decision_poll floods the embed path.
    expected_answers:
      - kind: tool_call
        tool: psql
        argument_keys: [dsn, query]
    weight: 0.09090909090909091
  - id: I-05
    type: repair
    refs: [G-01]
    scenario: A high-count housekeeping event type sits open in quarantine.
    expected_answers:
      - kind: human_action
        verb: add
        object: event type
        target: _NEVER_EXACT or _NEVER_PREFIXES via reviewed PR
    weight: 0.09090909090909091
  - id: I-06
    type: ambiguous
    refs: [E-04]
    scenario: An AI-proposed equivalence scores 96 but has no independent non-AI evidence.
    expected_answers:
      - kind: classification
        label: pending or rejected; never automatically trusted
    weight: 0.09090909090909091
  - id: I-07
    type: evolve
    refs: [§H]
    scenario: Proposal to log rejected candidate text for debugging.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.09090909090909091
  - id: I-08
    type: evolve
    refs: [§H]
    scenario: Ambiguous - a proposal to capture per-buyer search strings hashed with SHA-256 so they are "not raw data".
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.09090909090909091
  - id: I-09
    type: isolate
    refs: [F-05, G-04]
    scenario: A trusted equivalence is contradicted by newer evidence of equal or greater weight.
    expected_answers:
      - kind: human_action
        verb: append
        object: rejected or superseded trust revision
        target: remove derived projection first and preserve prior evidence
    weight: 0.09090909090909091
  - id: I-10
    type: isolate
    refs: [F-04]
    scenario: Google spend rises while the capture tables show no corresponding volume increase.
    expected_answers:
      - kind: human_action
        verb: compare
        object: capture volume
        target: GCP Monitoring aiplatform request_count
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [F-05]
    scenario: An equivalence score is 92, but the two sources have incompatible key types.
    expected_answers:
      - kind: classification
        label: typed conflict veto; manual review, never automatic promotion
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1632
last_refresh_commit: 71090f05a3f774b798fd8933b868bb6ea335e10d
last_refresh_date: 2026-08-28T11:27:12Z
owner_agent: sysadmin
refresh_triggers:
  - each S1299 chunk landing
  - S1396 design approval
  - any change to the evidence/trust/projection boundary or Corpus console
  - any change to event admission rules or denylist prefixes
  - any capture-related cost incident
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1632 / 2026-08-28T11:27:12Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: null
word_count_delta: null
```
