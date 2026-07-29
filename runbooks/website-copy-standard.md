---
runbook_id: website-copy-standard
domain: public-copy
status: DRAFT
authoritative_for:
  - topic: website-copy
    section: §E. Operate
aliases: []
error_signatures:
  - signature: Copy reads as AI-written or off-voice
    section: §F. Isolate
  - signature: Claim challenged as inaccurate
    section: §F. Isolate
  - signature: Metadata drifts from visible copy
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: max
last_verified_at: 2026-07-29
system_name: website-copy-standard
purpose_sentence: Preserve the approved ai.market public-copy rules, including voice, claims, calls to action, visible-copy and metadata alignment, and same-change verification.
owner_agent: max
escalation_contact: Unknown
lifecycle_ref: §J
authoritative_scope: Public website copy, headlines, calls to action, metadata text, structured-data text, llms.txt phrasing, and site-reused email or newsletter copy; legal pages and API reference text remain out of scope.
linter_version: 1.0.0
---

# Website Copy Standard

> Phase 2 Chunk D DRAFT. The root source remains unchanged. This page does not
> claim that any current website copy, metadata, structured data, or route was
> inspected during this docs-only rewrite.

## §A. Header

The frontmatter carries the required header fields. Git provenance identifies
Max as the source maintainer. The source names the `write-like-max` skill as a
companion but does not identify an escalation contact, so it remains
`Unknown`. English is the canonical language until internationalization ships.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Plain, first-person-plural public voice | PARTIAL | `Website copy / write-like-max` | Source-only verification; current site uninspected | 2026-07-29 |
| Mechanics adjacent to significant claims | PARTIAL | `Visible page copy` | Source-only verification; shipped claims uninspected | 2026-07-29 |
| Short verb-led calls to action | PARTIAL | `JSX / content constants` | Source-only verification; current strings uninspected | 2026-07-29 |
| Visible and machine-readable story alignment | PARTIAL | `Page metadata / JSON-LD / llms.txt / sitemap` | Source-only verification; current outputs uninspected | 2026-07-29 |
| Buyer and seller balance on shared pages | PARTIAL | `Shared-page copy` | Source-only verification; current pages uninspected | 2026-07-29 |

`PARTIAL` means the inherited source defines the rule while this pass provides
no live conformance evidence.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Visible Copy | Page JSX and content constants | Frontend Git repository | Metadata and calls to action | Copy must remain text, not be baked into images. |
| Page Metadata | Meta, Open Graph, and Twitter fields | Frontend Git repository | Visible Copy | The human and machine-readable story must agree. |
| Structured Data | JSON-LD text | Frontend Git repository | Visible Copy and search consumers | A copy change carries matching structured text in the same change. |
| Discovery Text | Backend-generated `llms.txt` and listing markdown endpoints | Backend Git repository | Frontend proxy configuration | The source says these routes are proxied through frontend configuration. |
| Sitemap | Sitemap content | Website delivery path | Visible Copy and discovery | The source requires same-change updates when relevant. |

The source applies to page copy, headlines, calls to action, descriptions,
social metadata, structured-data text, `llms.txt`, and email or newsletter copy
reused on the site. It excludes legal pages and API reference text.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Either instance | Author and ship public copy under this standard | Repository workflow and `write-like-max` | Unknown | PARTIAL — source-supported role; current access unverified |
| MP | Implement supplied final copy verbatim | Dispatch prompt with voice rules inlined | Unknown | PARTIAL — source requires verbatim diff verification |
| max | Maintain standing copy directives | Git and recorded directive | Documentation provenance | PARTIAL — operational escalation path is Unknown |

## §E. Operate

```yaml operate
- id: E-01
  trigger: New or revised customer-facing website copy is ready to draft.
  pre_conditions:
    - shipped_capability_boundary_known
    - page_audience_known
    - legal_and_api_reference_text_excluded
  tool_or_endpoint: Edit text in JSX or content constants under the repository workflow.
  argument_sourcing:
    voice: Use we, short sentences, plain words, and the inherited banned-word list.
    claims: Place the supporting mechanics near each significant claim and make no unshipped claim.
    page_answer: State what the reader gets in the first screen; the homepage answers for buyer and seller.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Customer copy is plain, specific, mechanics-backed, and audience-directed.
    verification: Read the diff verbatim and scan against the banned list and §H.1 invariants.
  expected_failures:
    - signature: Copy reads as AI-written or off-voice
      cause: Voice or banned-word rules were not applied.
    - signature: Claim challenged as inaccurate
      cause: The claim lacks nearby mechanics or names an unshipped capability.
  next_step_success: Continue with E-02 and E-03 in the same change.
  next_step_failure: Isolate with F-01 or F-02 before review.
- id: E-02
  trigger: A page section needs a customer action or shared buyer-and-seller routing.
  pre_conditions:
    - section_goal_known
    - available_actions_confirmed_as_shipped
  tool_or_endpoint: Edit the section call to action in JSX or content constants.
  argument_sourcing:
    label: Use a verb-led two- or three-word label such as Find Data, Sell Data, or Post a Request.
    priority: Use one primary action per section.
    balance: Give buyer and seller actions equal weight on shared pages.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: The section has one clear primary action and shared pages remain balanced.
    verification: Count primary actions and compare buyer and seller treatment in the diff.
  expected_failures:
    - signature: Shared-page actions are unbalanced
      cause: One audience received stronger or more prominent treatment.
  next_step_success: Continue with E-03.
  next_step_failure: Rework the action hierarchy before review.
- id: E-03
  trigger: Visible copy changed and its machine-readable representations may be affected.
  pre_conditions:
    - visible_copy_diff_complete
    - affected_metadata_surfaces_identified
  tool_or_endpoint: Update matching meta, social, JSON-LD, llms.txt, and sitemap text in the same change.
  argument_sourcing:
    story: Derive machine-readable wording from the final visible-copy meaning.
    surfaces: Include only affected surfaces; the source does not claim every change touches every file.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Human-visible and machine-readable surfaces tell the same story.
    verification: Compare final rendered wording and generated metadata meaning before merge.
  expected_failures:
    - signature: Metadata drifts from visible copy
      cause: A machine-readable surface retained older wording.
  next_step_success: Verify final copy verbatim against the diff.
  next_step_failure: Isolate with F-03 and repair both surfaces together.
```

The inherited banned list includes: `delve`, `leverage`, `robust`,
`comprehensive`, `seamless`, `unlock`, `empower`, `streamline`, `journey`,
`game-changer`, `Moreover`, `Furthermore`, and `It's worth noting`. It also
forbids em dashes and semicolons in customer copy, first-person singular, and
language that signals the company is small. The source specifically permits
explaining discoverability as global marketing the seller does not pay for.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Copy reads as AI-written or off-voice | Banned language, long phrasing, first-person singular, or small-company signalling | Scan the exact diff against the inherited voice rules | G-01 | CONFIRMED |
| F-02 | A claim is challenged as inaccurate | Mechanics are absent nearby or capability has not shipped | Compare the claim with adjacent mechanics and the separately verified shipped-capability list | G-02 | CONFIRMED |
| F-03 | Metadata or structured text disagrees with visible copy | Only one representation changed | Compare visible copy with affected meta, social, JSON-LD, `llms.txt`, and sitemap text | G-03 | CONFIRMED |
| F-04 | A shared page favours one audience | Calls to action were not balanced | Compare buyer and seller actions and prominence within the shared page | G-04 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Visible Copy
  root_cause: The inherited voice and banned-language rules were not followed.
  repair_entry_point: The exact copy diff
  change_pattern: Rewrite as we, with short sentences and plain words; remove banned language, em dashes, semicolons, and small-company signalling.
  rollback_procedure: Revert the off-voice copy change.
  integrity_check: Zero inherited banned-list hits and a verbatim diff review.
- id: G-02
  symptom_ref: F-02
  component_ref: Visible Copy
  root_cause: The claim lacks nearby mechanics or asserts an unshipped capability.
  repair_entry_point: The challenged claim and its supporting section
  change_pattern: Add source-supported mechanics nearby or remove the claim the same day if it is unshipped.
  rollback_procedure: Restore the last supported wording.
  integrity_check: Every significant claim has nearby mechanics and no unshipped capability remains.
- id: G-03
  symptom_ref: F-03
  component_ref: Page Metadata
  root_cause: Visible and machine-readable representations changed separately.
  repair_entry_point: The visible copy plus every affected machine-readable surface
  change_pattern: Fix both representations in one change so they communicate the same meaning.
  rollback_procedure: Revert the inconsistent change as one unit.
  integrity_check: Human-visible and machine-readable wording tell the same story.
- id: G-04
  symptom_ref: F-04
  component_ref: Visible Copy
  root_cause: Shared-page action hierarchy favours one audience.
  repair_entry_point: Calls to action on the shared page
  change_pattern: Restore equal buyer and seller weight while retaining one primary action per section.
  rollback_procedure: Restore the last balanced action layout.
  integrity_check: Buyer and seller actions have equal treatment on the shared page.
```

## §H. Evolve

### §H.1 Invariants

- The site speaks as `we`, using short sentences and plain words.
- Significant claims carry their mechanics nearby and never outrun shipped capability.
- Calls to action are verb-led, two or three words, with one primary action per section.
- Shared pages give buyer and seller actions equal weight.
- The first screen answers what the reader gets.
- Visible copy and machine-readable representations tell the same story.
- Copy remains text in JSX or constants, not pixels baked into images.

### §H.2 BREAKING predicates

Unknown. The source does not define a BREAKING classification.

### §H.3 REVIEW predicates

Unknown. The source does not define a REVIEW classification.

### §H.4 SAFE predicates

Unknown. The source does not define a SAFE classification.

### §H.5 Boundary definitions

#### module

Visible site copy, content constants, page metadata, social metadata, JSON-LD,
backend-generated discovery text, and sitemap wording.

#### public contract

The source-supported public contract is the wording customers and discovery
systems receive. Exact route, schema, and compatibility guarantees are Unknown.

#### runtime dependency

The source names the frontend, backend-generated discovery endpoints, and
frontend proxy configuration. Deployment and credential detail are Unknown.

#### config default

English is canonical until internationalization ships. Other defaults are Unknown.

### §H.6 Adjudication

New standing directives from Max are added to §E with a session reference and
noted on the active content BQ. Further adjudication detail is Unknown.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Draft a homepage claim about seller discovery.
    expected_answers:
      - kind: human_action
        verb: write
        object: mechanics-backed plain-language copy
        target: homepage first screen
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: Add buyer and seller actions to a shared section.
    expected_answers:
      - kind: human_action
        verb: balance
        object: verb-led buyer and seller calls to action
        target: shared page section
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Visible wording changed and the metadata tells the old story.
    expected_answers:
      - kind: human_action
        verb: update
        object: visible and machine-readable wording together
        target: same change
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: The draft contains banned language and first-person singular.
    expected_answers:
      - kind: human_action
        verb: scan
        object: exact diff against voice rules
        target: draft copy
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-02]
    scenario: A large capability claim has no mechanics nearby.
    expected_answers:
      - kind: human_action
        verb: compare
        object: claim, mechanics, and shipped capability
        target: challenged section
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: JSON-LD and visible copy describe different benefits.
    expected_answers:
      - kind: human_action
        verb: compare
        object: visible and structured wording
        target: affected page
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-01]
    scenario: Off-voice copy has not yet merged.
    expected_answers:
      - kind: human_action
        verb: rewrite
        object: copy under the inherited voice rules
        target: exact diff
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-03]
    scenario: Old metadata remains after visible copy changes.
    expected_answers:
      - kind: human_action
        verb: repair
        object: both representations in one change
        target: affected surfaces
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A proposal changes the public voice classification.
    expected_answers:
      - kind: classification
        label: Unknown because the source defines no BREAKING predicate
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H.6]
    scenario: Max issues a new standing copy directive.
    expected_answers:
      - kind: human_action
        verb: record
        object: directive with session reference
        target: §E and active content BQ
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [E-01, F-02]
    scenario: A persuasive claim may describe a capability that has not shipped.
    expected_answers:
      - kind: human_action
        verb: stop
        object: claim pending shipped-capability verification
        target: draft
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1389
last_refresh_commit: 5f968f167661dcac669dd42910037e05a50221ed
last_refresh_date: 2026-07-29T00:00:00Z
owner_agent: max
refresh_triggers:
  - Max issues a new standing copy directive.
  - A content refresh changes the source-supported public-copy scope.
  - Internationalization ships.
scheduled_cadence: 180d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1389 / 2026-07-29T00:00:00Z
last_lint_result: PASS
retrofit: true
trace_matrix_path: specs/ATHENA-PHASE2-CHUNK-D-TRACE-S1389.md
word_count_delta:
  before: 612
  after: 2158
  pct: 252.61
```
