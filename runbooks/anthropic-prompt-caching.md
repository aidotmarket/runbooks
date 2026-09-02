---
title: Anthropic Prompt Caching
owner: vulcan
last_verified: '2026-08-19'
aliases: []
error_signatures: []
---

# Anthropic Prompt Caching

## Overview

This page records the verified state and remaining evidence gaps for Build Queue
item `s1555`, “Stop paying full price for the same prompt,” which received its initial
cache placement in exact `ai-market-backend` commit
`84df5f976bd5dea6730c7ea7f1f8da476cf45b88`. Git proves that commit is an
ancestor of production-reported revision
`ed12d1b86c5475f41a9bed7057946b079a6bbd75`. The Railway deployment reported
`SUCCESS` for deployment `82d8c1dc-2c81-4c22-ad65-f9f00c193ac3`, created
`2026-08-18T22:07:14.283Z`.

Preflight on 2026-08-19 found that the deployed anonymous path concatenates a
fresh `generated_at` timestamp into the cache-marked block, guaranteeing a miss
on every anonymous request. No paid proof was sent. Exact backend candidate
`ccd7fc02d5b73a1d6118549a0076f1b952e499d8` moves the complete serialized
untrusted public-facts snapshot into the immediately following unmarked system
block while keeping the marketplace instructions marked, ordered first, and
fully counted by the reservation guard. Its exact anonymous unit gate passed
346 tests; Redis integration reported one pass and 16 environment skips; CC,
Kimi, and GLM each returned `APPROVE_WITH_NITS`. The candidate is pushed but is
not production until the deployed source is verified equal to that exact SHA.

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
cost 1.25 times base input, reads cost 0.1 times base input, and the effective
production model `claude-opus-4-7` required at least 2,048 cacheable tokens.
Shorter marked prompts are processed without caching and without an error.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Mark complete system-content blocks for provider caching; some include per-request context | SHIPPED | `app/services/copilot_brain.py` | `ai-market-backend@84df5f...`: `tests/test_llm_prompt_caching.py` request-shape tests; Architecture & interactions.1 lists every surface | 2026-08-19 |
| Preserve exact prompt bytes and request semantics | SHIPPED | `tests/test_llm_prompt_caching.py` | `ai-market-backend@84df5f...`: exact request-shape tests | 2026-08-19 |
| Capture anonymous-stream cache write/read usage and accounting | SHIPPED | `app/routers/anonymous_chat.py` | direct inspection of exact deployed revision `ed12d1b...` plus its retained tests | 2026-08-19 |
| Keep anonymous live facts outside the cache-marked stable instruction block | PLANNED | `app/routers/anonymous_chat.py` | `ai-market-backend@ccd7fc02...`: 346 exact anonymous unit tests; 39 focused tests; CC/Kimi/GLM approve-class exact reviews | 2026-08-19 |
| Prove a real production cache write followed by a read of that exact prefix | PARTIAL | `app/routers/anonymous_chat.py` | existing telemetry lacks exact prefix/request linkage; no valid live pair retained | 2026-08-19 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Cache breakpoint | `cache_control: {type: ephemeral}` on the marked system-content block | Anthropic-managed ephemeral cache | Messages API | Cache identity is the complete exact ordered prefix, not an ai.market key; some non-anonymous marked blocks contain per-request context. |
| CoPilot | `app/services/copilot_brain.py` | structured application logs | Anthropic async Messages API | Non-stream response exposes usage. |
| Listing enhancement | `app/services/listing_enhancement_service.py` | structured application logs | Anthropic async Messages API | Non-stream response exposes usage. |
| Authenticated allAI | `app/services/allie_proxy_service.py` | structured logs and existing rate-limit accounting | Anthropic create/stream APIs | Verify each response form independently; do not infer stream usage from non-stream usage. |
| Anonymous allAI | `app/routers/anonymous_chat.py` | SSE usage response, Redis cost reconciliation, OTel aggregate cost/tokens | Anthropic stream API | Candidate `ccd7fc02...` sends marked stable instructions first and the complete unmarked live-facts snapshot second; usage includes input, cache-write, cache-read, output, model, and estimated cost. |

The cache prefix is provider-defined in request order: tools, system, then
messages. The s1555 candidate puts the explicit breakpoint on a system-content
block, but that block is not universally static across every surface. CoPilot
page context and listing RAG context can be inside their marked blocks. In the
reviewed anonymous candidate, page class, locale, canonical platform facts,
tools, and model remain part of the marked prefix, while `generated_at`,
retrieved listings, and message-derived live facts are confined to the next
unmarked block. Reuse therefore remains scoped to a byte-identical complete
ordered prefix. User content after a breakpoint does not change that earlier
prefix; changing any byte at or before it does. Model, tool, image, provider
scope, and prompt-affecting settings can also invalidate reuse.

No ai.market database row or Redis key stores Anthropic cache contents. The
provider owns the ephemeral cache. ai.market records only sanitized token
counts and estimated cost; it must never log prompts, credentials, responses,
or customer content to prove caching.

### Architecture & interactions.1 Exact implementation scope

Exact `84df5f...` added cache placement to the four previously missed
large-prompt families: CoPilot, listing enhancement, authenticated allAI
non-stream/stream, and anonymous allAI stream. At that revision the anonymous
stream did not yet expose cache creation/read fields. Exact deployed revision
`ed12d1b...` contains the later anonymous extraction, SSE usage, and accounting
path. Ancestry proves only that the placement commit is contained; it never
proves that later instrumentation is present. Inspect the exact deployed
revision before relying on usage capture, and prevent double instrumentation
where a higher-level service already delegates to a measured provider wrapper.

Exact candidate `ccd7fc02...`, whose sole parent is `ed12d1b...`, repairs the
anonymous boundary only. `_system_blocks` is shared by reservation accounting
and the provider send, so both paths use the same two ordered blocks. The first
contains the existing marketplace instructions and the cache marker. The second
contains the complete `serialize_untrusted_public_facts(snapshot)` output and
no marker. This changes no validation snapshot, output-release gate, rate
limit, retry policy, schema, model selection, or customer-data handling.

### Architecture & interactions.2 Usage-field meaning

`input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, and
`output_tokens` are separate provider usage fields. Total billed input volume
is their first three values summed, while each category has its own price.
Application logs render cache creation as `cache_write` and hits as
`cache_read`. `None`, zero, or absent cache fields prove neither a regression
nor a hit: the prompt may be below the provider minimum, the surface may not
expose final stream usage, or the log sink may be unavailable.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Verify Git ancestry, deployment identity, existing logs/metrics, and runbook pins | Git plus read-only infrastructure/browser surfaces | read-only unless separately reviewed | COMPLETE |
| SysAdmin | Read deployment status and existing sanitized logs/metrics | `sysadmin_request` read-only | no traffic, secrets, restart, or config change | PARTIAL — raw log lines unavailable through the current API surface |
| Council | Review exact code/runbook artifacts | CC/GLM/DeepSeek exact-artifact review | reviewer-only | PARTIAL — backend review complete; refreshed runbook review pending |
| Human operator | Authorize a paid two-request proof when organic evidence is unavailable | explicit financial authority | narrowly bounded model/path/request count | COMPLETE |

## How to operate

```yaml operate
[]
```

No financial operation is prescribed by this page. Max separately authorized the exact harmless two-request proof in
S1572. That authorization becomes usable only after the exact reviewed backend
SHA is deployed, source and health are reverified, the effective model and its
minimum are known, and both requests can be bound to one identical eligible
prefix inside the provider TTL.

### How to operate.1 No-cost verification sequence

1. Resolve remote main and the active Railway deployment; retain deployment ID,
   status, reported revision, and timestamp.
2. Prove with replacement refs disabled that the reported deployed source is
   exactly the intended reviewed SHA. Ancestry alone is insufficient for the
   anonymous boundary repair.
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

### How to operate.2 Paid proof boundary

A synthetic proof is a financial action because it sends Anthropic requests.
It requires an explicit instruction naming the maximum request count and
acceptable spend or the exact pre-approved probe. S1572 has that instruction
for exactly one harmless two-request pair after deployment gates pass. The
smallest valid probe is:

- the anonymous production call path on one identical page class, locale,
  canonical platform-fact revision, model, tools, and prompt-affecting settings;
- a marked stable instruction prefix that exceeds the effective model's current
  provider minimum without padding;
- request 1 completes or at least begins its response and reports
  `cache_creation_input_tokens > 0`;
- request 2 reuses the exact request construction with identical complete
  opaque exact-prefix identity, model, tools, prompt-affecting parameters, and
  provider scope and deployment/configuration epoch, and starts before the TTL expires, reporting
  `cache_read_input_tokens > 0`;
- both requests use harmless non-customer test input and the minimum safe output
  budget already supported by that path.

Do not pad a real prompt merely to force eligibility, weaken rate limits, use a
customer identity, expose a key, or repeat after the first valid pair. Stop on
any different model/prefix, provider error, missing usage, unexpected output,
rate-limit effect, or uncertain charge.

### How to operate.3 Current 2026-08-19 evidence

- Railway deployment `82d8c1dc-2c81-4c22-ad65-f9f00c193ac3`: `SUCCESS`.
- Production-reported revision: `ed12d1b86c5475f41a9bed7057946b079a6bbd75`.
- Exact `84df5f...` ancestor proof: pass.
- Existing Railway logs/metrics since 2026-08-15: cache evidence ABSENT through
  the reachable API; the API returned deployment metadata but no raw log lines.
- Signed-in browser: blocked because its admin safety policy could not be
  verified; no bypass attempted.
- Anthropic Console/export: not accessed.
- Production anonymous preflight: known miss because a fresh `generated_at`
  timestamp is inside the deployed marked block.
- Reviewed repair: `ai-market-backend@ccd7fc02...`, pushed and unanimously
  approve-class reviewed, not yet deployed.
- Production configuration: `claude-opus-4-7`, anonymous output cap 2,048
  tokens. Anthropic's free token-count endpoint measured 7,278 input tokens for
  the exact tools, marked stable system block, and harmless proof message; it
  created no model response and exceeds the current 2,048-token minimum.
- Free provider preflight: two token-count API attempts only; the first was
  rejected because an empty messages array is invalid, and the second returned
  the 7,278-token count. Neither created a model response.
- Synthetic Anthropic traffic: exact two-request pair authorized but not sent;
  total paid requests in S1572 remains zero.

Therefore deployed code presence is verified, deployed anonymous reuse is known
to miss, and repaired live cache effectiveness remains `UNVERIFIED` until exact
deployment and the authorized linked pair.

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Both cache usage fields remain zero. | Prefix below current model minimum, changing prefix, unsupported request form, or cache marker absent. | Count the exact cacheable prefix and compare exact consecutive request shapes without logging content. | G-01 | CONFIRMED |
| F-02 | Writes occur but reads never occur. | Requests outside TTL, complete-prefix/model/tool/provider-scope drift, concurrency before first response, or marker on changing content. | Compare sanitized model/surface/version/timing and approved opaque exact-prefix linkage; use only non-customer fixtures for raw prefix comparison. | G-02 | CONFIRMED |
| F-03 | Application says cache fields exist but live logs show none. | No eligible traffic, stream usage not emitted, log level/sink unavailable, or query surface returns metadata only. | Confirm code path and sink separately; classify missing evidence as ABSENT, not zero. | G-03 | CONFIRMED |
| F-04 | Estimated cost is lower but cache token categories are not retained. | Aggregate accounting combined categories. | Compare the provider usage envelope mapping to logs/SSE/metrics; do not reverse-engineer cache hits from cost alone. | G-04 | CONFIRMED |
| F-05 | A synthetic probe would be the only remaining proof. | No organic matching traffic or inaccessible provider/Railway evidence. | Stop and request narrow financial authority; do not silently create model traffic. | G-05 | CONFIRMED |
| F-06 | Anonymous cache writes never become reads despite identical harmless inputs. | A fresh timestamp or retrieved live facts are inside the marked block. | Inspect the exact deployed system-block boundary and require `generated_at` plus serialized live facts only in the immediately following unmarked block. | G-06 | CONFIRMED |

## Repair

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
- id: G-06
  symptom_ref: F-06
  component_ref: Anonymous allAI
  root_cause: per-request public-fact snapshot serialized inside the marked system block
  repair_entry_point: ai-market-backend@ccd7fc02 app/routers/anonymous_chat.py
  change_pattern: mark stable marketplace instructions, then send the complete dynamic snapshot as the next unmarked system block
  rollback_procedure: redeploy exact prior production SHA ed12d1b86c5475f41a9bed7057946b079a6bbd75 and stop paid proof traffic
  integrity_check: exact tests prove stable first-block bytes, ordered complete second-block facts, conservative accounting, and unchanged fail-closed release
```

## Changes and maintenance

### H.1 Invariants

- Cache reuse requires an identical complete ordered prefix; never alter prompt meaning for cost.
- Provider token fields, not estimated savings, prove cache creation/read.
- Never log prompts, responses, credentials, or customer data for evidence.
- Missing telemetry is ABSENT/UNVERIFIED, never silently converted to zero or
  completion.
- No synthetic provider request without explicit financial authority.

### H.2 BREAKING predicates

Changing prompt bytes/order, model/tool request semantics, provider, TTL,
minimum-token behavior, customer data handling, cost enforcement, or safety
fallbacks is breaking and requires design plus exact-artifact review.

### H.3 REVIEW predicates

Adding/removing a cache marker, moving the breakpoint, changing usage-field
mapping, log/metric names, cost rates, or live acceptance evidence requires
tests, this page, and exact-artifact review to move together.

### H.4 SAFE predicates

Editorial clarification and updated point-in-time provider links/prices are safe
only when they change no request, accounting, authority, or acceptance meaning.

### H.5 Boundary definitions

#### module

The module boundary is every direct Anthropic Messages API call carrying the
marked system-content block, any ordered unmarked context blocks after its
breakpoint, and its numeric usage extraction.

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

### H.6 Adjudication

Exact deployed code and provider usage fields win over this page. Official
Anthropic documentation wins for current TTL/minimum/pricing behavior. Any
mismatch or evidence uncertainty keeps the BQ `production_unknown`.

## Acceptance criteria

```yaml acceptance
scenario_set: []
```

BQ completion additionally requires: exact reviewed repair `ccd7fc02...` as the
active production revision; direct inspection of the deployed revision's usage
and two-block boundary; healthy deployment; retained sanitized evidence of a
cache write and subsequent read bound by identical opaque exact-prefix identity,
page class, locale, canonical platform-fact revision, model, tools,
prompt-affecting parameters, provider scope, deployment/configuration epoch,
and TTL; no
prompt/output/safety regression; dedicated runbook indexed; and the ground-truth
board refreshed from Git/deployment evidence. A log search returning no rows,
an unlinked write/read pair, an SDK mock, a code ancestor proof, or a single
cache write cannot substitute for the linked live pair.

## Maintenance

```yaml lifecycle
last_refresh_session: S1572
last_refresh_commit: ccd7fc02d5b73a1d6118549a0076f1b952e499d8
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
