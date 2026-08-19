---
runbook_id: anthropic-prompt-caching
domain: cost-operations
status: DRAFT
authoritative_for: []
aliases: []
error_signatures: []
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-08-19
system_name: anthropic-prompt-caching
purpose_sentence: Discovery-only record of ai.market Anthropic prompt-cache placement, usage accounting, no-cost verification, and fail-closed production acceptance.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: None while DRAFT; this page documents the deployed prompt-cache candidate and its unresolved live-evidence requirement but does not authorize paid model traffic, deployment, provider changes, or a completion claim.
linter_version: 1.0.0
---

# Anthropic Prompt Caching

## §A. Header

This is a **DRAFT discovery document, not operating authority**. Build Queue
item `s1555`, “Stop paying full price for the same prompt,” received its cache
placement in exact `ai-market-backend` commit
`84df5f976bd5dea6730c7ea7f1f8da476cf45b88`. Git proves that commit is an
ancestor of production-reported revision
`ed12d1b86c5475f41a9bed7057946b079a6bbd75`. The current Railway deployment
reported `SUCCESS` for deployment `82d8c1dc-2c81-4c22-ad65-f9f00c193ac3`,
created `2026-08-18T22:07:14.283Z`. Direct inspection of that later revision,
not ancestry alone, is the evidence for its anonymous-stream usage extraction
and accounting path.

Deployment presence is not cache-effectiveness proof. As of 2026-08-19, the
available read-only Railway log/metric surface returned no line-level cache
usage and no cache time series. This is an **ABSENT evidence result**, not a
provider failure. Do not mark the item complete until existing production
evidence shows both a cache write and a later cache read for an identical
eligible prefix, or a separately authorized paid probe establishes both.

Official provider contract:
`https://platform.claude.com/docs/en/build-with-claude/prompt-caching`.
Recheck it before changing model, TTL, minimum-token assumptions, or prices.
On 2026-08-19 the documented default TTL was five minutes; 5-minute writes
cost 1.25 times base input, reads cost 0.1 times base input, and Sonnet 4.6
required at least 1,024 cacheable tokens. Shorter marked prompts are processed
without caching and without an error.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Mark complete system-content blocks for provider caching; some include per-request context | SHIPPED | `app/services/copilot_brain.py` | `ai-market-backend@84df5f...`: `tests/test_llm_prompt_caching.py` request-shape tests; §C.1 lists every surface | 2026-08-19 |
| Preserve exact prompt bytes and request semantics | SHIPPED | `tests/test_llm_prompt_caching.py` | `ai-market-backend@84df5f...`: exact request-shape tests | 2026-08-19 |
| Capture anonymous-stream cache write/read usage and accounting | SHIPPED | `app/routers/anonymous_chat.py` | direct inspection of exact deployed revision `ed12d1b...` plus its retained tests | 2026-08-19 |
| Prove a real production cache write followed by a read of that exact prefix | PARTIAL | `app/routers/anonymous_chat.py` | existing telemetry lacks exact prefix/request linkage; no valid live pair retained | 2026-08-19 |
| Dedicated indexed operating authority | PLANNED | `runbooks/anthropic-prompt-caching.md` | runbook lint/catalog/manifest tests | 2026-08-19 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Cache breakpoint | `cache_control: {type: ephemeral}` on the marked system-content block | Anthropic-managed ephemeral cache | Messages API | Cache identity is the complete exact ordered prefix, not an ai.market key; some marked blocks contain per-request context. |
| CoPilot | `app/services/copilot_brain.py` | structured application logs | Anthropic async Messages API | Non-stream response exposes usage. |
| Listing enhancement | `app/services/listing_enhancement_service.py` | structured application logs | Anthropic async Messages API | Non-stream response exposes usage. |
| Authenticated allAI | `app/services/allie_proxy_service.py` | structured logs and existing rate-limit accounting | Anthropic create/stream APIs | Verify each response form independently; do not infer stream usage from non-stream usage. |
| Anonymous allAI | `app/routers/anonymous_chat.py` | SSE usage response, Redis cost reconciliation, OTel aggregate cost/tokens | Anthropic stream API | Usage includes input, cache-write, cache-read, output, model, and estimated cost. |

The cache prefix is provider-defined in request order: tools, system, then
messages. The s1555 candidate puts the explicit breakpoint on a system-content
block, but that block is not universally static. CoPilot page context, listing
RAG context, and anonymous page/listing/message-derived grounding can be inside
the marked block. Reuse therefore requires the complete ordered prefix,
including embedded dynamic context, to be byte-identical. User content after a
breakpoint does not change that earlier prefix; changing any byte at or before
it does. Model, tool, image, provider scope, and prompt-affecting settings can
also invalidate reuse.

No ai.market database row or Redis key stores Anthropic cache contents. The
provider owns the ephemeral cache. ai.market records only sanitized token
counts and estimated cost; it must never log prompts, credentials, responses,
or customer content to prove caching.

### §C.1 Exact implementation scope

Exact `84df5f...` added cache placement to the four previously missed
large-prompt families: CoPilot, listing enhancement, authenticated allAI
non-stream/stream, and anonymous allAI stream. At that revision the anonymous
stream did not yet expose cache creation/read fields. Exact deployed revision
`ed12d1b...` contains the later anonymous extraction, SSE usage, and accounting
path. Ancestry proves only that the placement commit is contained; it never
proves that later instrumentation is present. Inspect the exact deployed
revision before relying on usage capture, and prevent double instrumentation
where a higher-level service already delegates to a measured provider wrapper.

### §C.2 Usage-field meaning

`input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, and
`output_tokens` are separate provider usage fields. Total billed input volume
is their first three values summed, while each category has its own price.
Application logs render cache creation as `cache_write` and hits as
`cache_read`. `None`, zero, or absent cache fields prove neither a regression
nor a hit: the prompt may be below the provider minimum, the surface may not
expose final stream usage, or the log sink may be unavailable.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Verify Git ancestry, deployment identity, existing logs/metrics, and runbook pins | Git plus read-only infrastructure/browser surfaces | read-only unless separately reviewed | COMPLETE |
| SysAdmin | Read deployment status and existing sanitized logs/metrics | `sysadmin_request` read-only | no traffic, secrets, restart, or config change | PARTIAL — raw log lines unavailable through the current API surface |
| Council | Review exact code/runbook artifacts | CC/Kimi/GLM exact-artifact review | reviewer-only | PLANNED |
| Human operator | Authorize a paid two-request proof when organic evidence is unavailable | explicit financial authority | narrowly bounded model/path/request count | GAP — requires explicit Max financial authorization |

## §E. Operate

```yaml operate
[]
```

The operate form is empty because this page is DRAFT and live model calls cost
money. Use only existing production evidence unless Max separately authorizes
the exact paid proof.

### §E.1 No-cost verification sequence

1. Resolve remote main and the active Railway deployment; retain deployment ID,
   status, reported revision, and timestamp.
2. Prove with replacement refs disabled that exact candidate `84df5f...` is an
   ancestor of the reported deployed revision.
3. Query existing sanitized logs for
   `llm_usage provider=anthropic`, `cache_write=`, and `cache_read=`. Query
   metrics for cache-specific series if deployed instrumentation provides them.
4. Retain only timestamp, surface/route, model, numeric token counts, deployment
   ID, request/trace ID, opaque provider-scope identity, prompt-affecting
   parameter identity, and opaque exact-prefix linkage supplied by provider
   diagnostics or separately security-reviewed keyed instrumentation. Never
   retain prompt or response content, credentials, a raw content digest, or a
   reversible customer identifier.
5. Treat existing records without that exact prefix/request linkage as
   insufficient. Same route, model, deployment, configuration, and elapsed
   time are necessary context but never prove that a read consumed the earlier
   write; another request may have populated the read prefix.
6. A valid pair requires a completed request with `cache_write > 0` and a later
   request with `cache_read > 0`, with identical opaque exact-prefix identity,
   model, tools, prompt-affecting parameters, provider scope, and deployment /
   configuration epoch. The second request must start inside the provider TTL
   measured from the first request's start. Only then record
   `LIVE_CACHE_PAIR_VERIFIED`; otherwise retain `UNVERIFIED`.

A write alone proves only that an eligible prefix was stored. A read alone may
reuse an unseen write and proves caching is active only for some prefix, not the
full paired journey. The currently reachable logs lack the required exact
prefix linkage, so they cannot close this BQ even if an unrelated write and read
appear. Retain `UNVERIFIED` unless a valid linked pair is available.

### §E.2 Paid proof boundary

A synthetic proof is a financial action because it sends Anthropic requests.
It requires a new, explicit instruction naming the maximum request count and
acceptable spend or the exact pre-approved probe. The smallest valid probe is:

- one existing production call path whose complete marked prefix, including
  any embedded dynamic context, exceeds the current model minimum;
- request 1 completes or at least begins its response and reports
  `cache_creation_input_tokens > 0`;
- request 2 reuses the exact request construction with identical complete
  opaque exact-prefix identity, model, tools, prompt-affecting parameters, and
  provider scope, and starts before the TTL expires, reporting
  `cache_read_input_tokens > 0`;
- both requests use harmless non-customer test input and the minimum safe output
  budget already supported by that path.

Do not pad a real prompt merely to force eligibility, weaken rate limits, use a
customer identity, expose a key, or repeat after the first valid pair. Stop on
any different model/prefix, provider error, missing usage, unexpected output,
rate-limit effect, or uncertain charge.

### §E.3 Current 2026-08-19 evidence

- Railway deployment `82d8c1dc-2c81-4c22-ad65-f9f00c193ac3`: `SUCCESS`.
- Production-reported revision: `ed12d1b86c5475f41a9bed7057946b079a6bbd75`.
- Exact `84df5f...` ancestor proof: pass.
- Existing Railway logs/metrics since 2026-08-15: cache evidence ABSENT through
  the reachable API; the API returned deployment metadata but no raw log lines.
- Signed-in browser: blocked because its admin safety policy could not be
  verified; no bypass attempted.
- Anthropic Console/export: not accessed.
- Synthetic Anthropic traffic: not authorized and not sent.

Therefore code presence is verified but live cache effectiveness remains
`UNVERIFIED`.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Both cache usage fields remain zero. | Prefix below current model minimum, changing prefix, unsupported request form, or cache marker absent. | Count the exact cacheable prefix and compare exact consecutive request shapes without logging content. | G-01 | CONFIRMED |
| F-02 | Writes occur but reads never occur. | Requests outside TTL, complete-prefix/model/tool/provider-scope drift, concurrency before first response, or marker on changing content. | Compare sanitized model/surface/version/timing and approved opaque exact-prefix linkage; use only non-customer fixtures for raw prefix comparison. | G-02 | CONFIRMED |
| F-03 | Application says cache fields exist but live logs show none. | No eligible traffic, stream usage not emitted, log level/sink unavailable, or query surface returns metadata only. | Confirm code path and sink separately; classify missing evidence as ABSENT, not zero. | G-03 | CONFIRMED |
| F-04 | Estimated cost is lower but cache token categories are not retained. | Aggregate accounting combined categories. | Compare the provider usage envelope mapping to logs/SSE/metrics; do not reverse-engineer cache hits from cost alone. | G-04 | CONFIRMED |
| F-05 | A synthetic probe would be the only remaining proof. | No organic matching traffic or inaccessible provider/Railway evidence. | Stop and request narrow financial authority; do not silently create model traffic. | G-05 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Cache breakpoint
  root_cause: ineligible or unstable cacheable prefix
  repair_entry_point: exact request-shape tests and current provider minimum
  change_pattern: keep stable content before the explicit breakpoint without padding customer prompts
  rollback_procedure: remove only the reviewed cache marker and restore the exact prior request shape
  integrity_check: exact prompt bytes and response semantics remain unchanged
- id: G-02
  symptom_ref: F-02
  component_ref: Cache breakpoint
  root_cause: TTL, concurrency, prefix, model, or tool drift prevents reuse
  repair_entry_point: sanitized pair timing and isolated prefix identity test
  change_pattern: correct only the unstable prefix boundary or verified request ordering
  rollback_procedure: restore the prior exact cache boundary
  integrity_check: a separately authorized or organic pair reports one write then one read
- id: G-03
  symptom_ref: F-03
  component_ref: CoPilot
  root_cause: telemetry path unavailable or not emitting final usage
  repair_entry_point: shared low-cardinality usage instrumentation review
  change_pattern: emit numeric usage categories without prompt or response content
  rollback_procedure: remove the new instrument without changing the Anthropic request
  integrity_check: existing telemetry accepts sanitized cache counters and no sensitive fields
- id: G-04
  symptom_ref: F-04
  component_ref: Anonymous allAI
  root_cause: aggregate cost or token accounting hides cache categories
  repair_entry_point: provider usage mapping and anonymous reconciliation tests
  change_pattern: retain category counters separately while preserving total and price arithmetic
  rollback_procedure: restore reviewed accounting and keep completion unverified
  integrity_check: input plus cache-write plus cache-read plus output reconciles exactly
- id: G-05
  symptom_ref: F-05
  component_ref: Authenticated allAI
  root_cause: live proof would incur provider cost
  repair_entry_point: explicit Max authorization for a bounded two-request probe
  change_pattern: run the minimum harmless pair once and stop
  rollback_procedure: no retry; retain only sanitized usage evidence
  integrity_check: authorized request count and spend bound were not exceeded
```

## §H. Evolve

### §H.1 Invariants

- Cache reuse requires an identical complete ordered prefix; never alter prompt meaning for cost.
- Provider token fields, not estimated savings, prove cache creation/read.
- Never log prompts, responses, credentials, or customer data for evidence.
- Missing telemetry is ABSENT/UNVERIFIED, never silently converted to zero or
  completion.
- No synthetic provider request without explicit financial authority.

### §H.2 BREAKING predicates

Changing prompt bytes/order, model/tool request semantics, provider, TTL,
minimum-token behavior, customer data handling, cost enforcement, or safety
fallbacks is breaking and requires design plus exact-artifact review.

### §H.3 REVIEW predicates

Adding/removing a cache marker, moving the breakpoint, changing usage-field
mapping, log/metric names, cost rates, or live acceptance evidence requires
tests, this page, and exact-artifact review to move together.

### §H.4 SAFE predicates

Editorial clarification and updated point-in-time provider links/prices are safe
only when they change no request, accounting, authority, or acceptance meaning.

### §H.5 Boundary definitions

#### module

The module boundary is every direct Anthropic Messages API call carrying the
marked system-content block, including embedded dynamic context where present,
plus its numeric usage extraction.

#### public contract

User-visible answer semantics and safety behavior remain unchanged. Anonymous
SSE may expose sanitized token categories and estimated cost already defined by
the production API.

#### runtime dependency

Anthropic Messages API, exact prompt/model/tool identity, provider TTL and token
minimum, Railway deployment/logging, Redis anonymous reconciliation, and the
configured OTel sink.

#### config default

The candidate uses provider `ephemeral` caching with its default five-minute
TTL. Cost rates remain configuration values and must follow current provider
pricing through a separately reviewed change.

### §H.6 Adjudication

Exact deployed code and provider usage fields win over this page. Official
Anthropic documentation wins for current TTL/minimum/pricing behavior. Any
mismatch or evidence uncertainty keeps the BQ `production_unknown`.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set: []
```

Documentation acceptance requires this DRAFT in the generated catalog/router,
one pending manifest record, unchanged ACTIVE authority, current generated
artifacts, lint/manifest/catalog/full-suite success, exact review, and exact
publication.

BQ completion additionally requires: exact `84df5f...` contained in the active
production revision; direct inspection of the deployed revision's usage path;
healthy deployment; retained sanitized evidence of a cache write and subsequent
read bound by identical opaque exact-prefix identity, model, tools, prompt-affecting
parameters, provider scope, deployment/configuration epoch, and TTL; no
prompt/output/safety regression; dedicated runbook indexed; and the ground-truth
board refreshed from Git/deployment evidence. A log search returning no rows,
an unlinked write/read pair, an SDK mock, a code ancestor proof, or a single
cache write cannot substitute for the linked live pair.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1572
last_refresh_commit: 84df5f976bd5dea6730c7ea7f1f8da476cf45b88
last_refresh_date: 2026-08-19T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - any Anthropic model, SDK, prompt order, cache marker, TTL, or usage-field change
  - any ai.market cost-accounting or telemetry change
  - provider minimum-token or price change
  - a retained production write/read pair or failed cache verification
scheduled_cadence: 90d
```

The final runbooks SHA, generated pins, test result, review verdicts, live pair,
and queue refresh belong in external evidence because this file cannot
truthfully self-pin its own commit.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
retrofit: false
trace_matrix_path: null
word_count_delta: null
```
