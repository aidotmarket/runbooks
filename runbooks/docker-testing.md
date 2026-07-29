---
runbook_id: docker-testing
domain: product-testing
status: DRAFT
authoritative_for:
  - topic: vectoraiz-local-docker-testing
    section: §E. Operate
aliases: []
error_signatures:
  - signature: OrbStack not running
    section: §F. Isolate
  - signature: Image not found
    section: §F. Isolate
  - signature: MemoryError on ARM64
    section: §F. Isolate
  - signature: Semaphore leak
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: max
last_verified_at: 2026-07-29
system_name: vectoraiz-local-docker-testing
purpose_sentence: Preserve the source-documented local vectorAIz Docker test path on Titan-1 without claiming unrecorded runtime ownership, verification, or repair detail.
owner_agent: max
escalation_contact: Unknown
lifecycle_ref: §J
authoritative_scope: Local vectorAIz release-candidate image pulls, customer-compose startup, OrbStack Docker location, source-listed compose and Dockerfile paths, the sandboxed import mount, and four inherited failure signatures; live runtime behavior remains unverified.
linter_version: 1.0.0
---

# Docker Testing (vectorAIz local)

> Phase 2 Chunk C DRAFT. The root source remains in place. This document is not
> catalog authority and does not authorize image promotion, destructive cleanup,
> or production-compose execution.

## §A. Header

The frontmatter supplies the required header fields. Git provenance identifies
Max as the source document author, so `owner_agent: max` records maintenance
provenance only. The source does not identify the runtime operator, runtime auth
scope, or escalation contact; each remains explicitly `Unknown`. No Docker,
OrbStack, GHCR, compose, import, or vectorAIz runtime was inspected.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| OrbStack-backed Docker CLI on Titan-1 | PARTIAL | `~/.orbstack/bin/docker` | Source-only verification at the exact branch base; live CLI unverified | 2026-07-29 |
| Release-candidate image pull | PARTIAL | `ghcr.io/aidotmarket/vectoraiz` | Source provides an example tag; live image unverified | 2026-07-29 |
| Customer-compose startup | PARTIAL | `docker-compose.customer.yml` | Source provides the compose command; live startup unverified | 2026-07-29 |
| Customer and development Docker definitions | PARTIAL | `Dockerfile.customer` | Source lists four files; their current contents are unverified | 2026-07-29 |
| Sandboxed local import mount | PARTIAL | `~/vectoraiz-imports` | Source names the mount; live mount behavior unverified | 2026-07-29 |

`PARTIAL` means the inherited document describes the capability but this
docs-only pass did not inspect or execute it.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| OrbStack Docker | `~/.orbstack/bin/docker` | Local image and container state | GHCR and compose | Source says Docker runs through OrbStack on Titan-1. |
| Candidate Image | `ghcr.io/aidotmarket/vectoraiz:<candidate-tag>` | GHCR and local image cache | Docker CLI | The source example is historical evidence, not a current version default. |
| Customer Compose | `docker-compose.customer.yml` | Local compose state | Customer Dockerfile and import mount | Source provides an `up` command from `~/Projects/vectoraiz/vectoraiz-monorepo`. |
| Docker Definitions | `Dockerfile.customer` and compose files | Git repository | Docker and compose | Source lists customer, development, and production compose paths. |
| Import Mount | `~/vectoraiz-imports` | Local filesystem | Customer container | Source describes it as sandboxed; further mount semantics are Unknown. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Unknown | Pull and test a local vectorAIz candidate | `docker` and `docker compose` | Unknown | GAP — the source does not identify a runtime operator or auth scope |
| max | Maintain the source document | `git` | Runbooks documentation provenance | PARTIAL — Git authorship is known; current operational ownership is Unknown |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A vectorAIz release-candidate image must be made available for local testing before promotion.
  pre_conditions:
    - exact_candidate_tag_known
    - OrbStack_runtime_available
    - runtime_operator_authorized_outside_this_runbook
  tool_or_endpoint: docker pull ghcr.io/aidotmarket/vectoraiz:<candidate-tag>
  argument_sourcing:
    candidate_tag: Use the exact candidate selected by the separately governed release process; do not reuse the historical example as a default.
    docker_cli: Use the source-documented OrbStack Docker CLI on Titan-1.
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: exact candidate tag or image digest
  expected_success:
    shape: The exact candidate image is present in the local Docker image cache.
    verification: Unknown — the source does not define an independent post-pull verification command.
  expected_failures:
    - signature: OrbStack not running
      cause: The local OrbStack runtime is not running.
    - signature: Image not found
      cause: The source says the GHCR build may still be in progress.
    - signature: MemoryError on ARM64
      cause: The source identifies onnxruntime remnants.
  next_step_success: Use E-02 when compose-based local testing is intended.
  next_step_failure: Isolate with F-01, F-02, or F-03; do not promote.
- id: E-02
  trigger: The candidate must be started with the source-documented customer compose file for local testing.
  pre_conditions:
    - exact_candidate_available_locally
    - vectoraiz_monorepo_path_confirmed
    - runtime_operator_authorized_outside_this_runbook
  tool_or_endpoint: docker compose -f docker-compose.customer.yml up
  argument_sourcing:
    repository: Use the source-documented vectorAIz monorepo path after confirming it still exists.
    compose_file: Use docker-compose.customer.yml.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: The customer-compose stack starts for local testing.
    verification: Unknown — the source does not define a health endpoint or complete success assertion.
  expected_failures:
    - signature: Semaphore leak
      cause: The source says the issue was fixed in recent versions and recommends updating the image.
  next_step_success: Perform only the separately defined product checks; this source does not enumerate them.
  next_step_failure: Isolate with F-04 and do not claim a passing local test.
- id: E-03
  trigger: The operator must confirm which source-listed files and mount participate before changing the local test setup.
  pre_conditions:
    - repository_readable
    - no_runtime_mutation_started
  tool_or_endpoint: Read the source-listed Dockerfile, compose files, and ~/vectoraiz-imports mount declaration.
  argument_sourcing:
    dockerfile: Dockerfile.customer
    compose_files: docker-compose.customer.yml, docker-compose.yml, and docker-compose.prod.yml
    import_mount: ~/vectoraiz-imports
  idempotency: IDEMPOTENT
  expected_success:
    shape: The operator has identified the customer, development, production, and import-mount inputs named by the source.
    verification: Confirm only path presence; file semantics remain Unknown until reviewed by the owning lane.
  expected_failures:
    - signature: source-listed path absent
      cause: Repository layout changed after the inherited source was written.
  next_step_success: Use only the file appropriate to the separately authorized local test.
  next_step_failure: Stop and transfer the layout question to the owning lane; do not substitute a production file.
```

The source uses `v1.20.33-rc.1` as its pull example and says the local customer
test container was on version `v1.20.31`. Both are historical source evidence,
not current-version claims or defaults.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | OrbStack is not running | Local OrbStack application is stopped | Confirm only the source-reported runtime state; further diagnostics are Unknown | G-01 | CONFIRMED |
| F-02 | Candidate image is not found | GHCR build is still running; source estimates 45–60 minutes | Check the separately governed image-build status for the exact tag | G-02 | HYPOTHESIZED |
| F-03 | ARM64 test raises `MemoryError` | onnxruntime remnants | Confirm the failure is tied to remnants before any deletion; exact remnant path is Unknown | G-03 | HYPOTHESIZED |
| F-04 | Test reports a semaphore leak | Older image still contains the issue | Compare the exact tested image with the separately governed newer candidate | G-04 | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: OrbStack Docker
  root_cause: The source says the OrbStack application is not running.
  repair_entry_point: OrbStack application
  change_pattern: Use the source-documented action of opening OrbStack before retrying Docker.
  rollback_procedure: Unknown — the source does not define rollback for starting OrbStack.
  integrity_check: Unknown — the source does not define a Docker-runtime health assertion.
- id: G-02
  symptom_ref: F-02
  component_ref: Candidate Image
  root_cause: The source says the GHCR build has not completed.
  repair_entry_point: ghcr.io/aidotmarket/vectoraiz
  change_pattern: Wait for the exact candidate build to complete, then retry the pull.
  rollback_procedure: None — waiting and retrying a pull does not change release state.
  integrity_check: The exact candidate tag pulls successfully.
- id: G-03
  symptom_ref: F-03
  component_ref: Candidate Image
  root_cause: The source identifies onnxruntime remnants as the cause.
  repair_entry_point: Confirmed onnxruntime remnant path
  change_pattern: The inherited source literally says rm -rf rather than pip uninstall; it does not name the target, so the exact remnant path is Unknown and must be resolved by the owning lane before any destructive command.
  rollback_procedure: Unknown — the source does not define recovery for deleted remnants.
  integrity_check: Unknown — the source does not define a post-cleanup ARM64 assertion.
- id: G-04
  symptom_ref: F-04
  component_ref: Candidate Image
  root_cause: The source says the issue was fixed in recent image versions.
  repair_entry_point: Exact vectorAIz candidate image
  change_pattern: Update the tested image only through the separately governed release path.
  rollback_procedure: Return to the previously tested local image tag; the source provides no further rollback detail.
  integrity_check: Unknown — the source does not define the semaphore-leak reproduction or pass condition.
```

## §H. Evolve

### §H.1 Invariants

- Local vectorAIz Docker testing occurs on Titan-1 through OrbStack before
  stable promotion.
- The source names `docker-compose.customer.yml` for customer-compose testing.
- Local directory import uses the sandboxed `~/vectoraiz-imports` mount.
- The historical example tag and local-container version are not defaults.

### §H.2 BREAKING predicates

Unknown — the source does not define a BREAKING change classification.

### §H.3 REVIEW predicates

Unknown — the source does not define a REVIEW change classification.

### §H.4 SAFE predicates

Unknown — the source does not define a SAFE change classification.

### §H.5 Boundary definitions

#### module

The source-supported module boundary is the local OrbStack Docker runtime,
candidate image, customer compose file, listed Docker definitions, and import
mount.

#### public contract

Unknown — the source does not define a public API or customer-facing contract
for the local test procedure.

#### runtime dependency

The source names Titan-1, OrbStack, Docker, GHCR, the vectorAIz monorepo, and the
local import directory. Availability and credential detail are Unknown.

#### config default

The source provides historical examples, not authoritative configuration
defaults. Configuration defaults are Unknown.

### §H.6 Adjudication

Unknown — the source does not define change-class adjudication.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: An exact vectorAIz release candidate must be pulled for local testing.
    expected_answers:
      - kind: tool_call
        tool: docker pull
        argument_keys: [candidate_tag]
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: The local candidate must be started with the customer compose file.
    expected_answers:
      - kind: tool_call
        tool: docker compose
        argument_values: {compose_file: docker-compose.customer.yml}
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: The operator must identify source-listed Docker and mount inputs without changing runtime state.
    expected_answers:
      - kind: human_action
        verb: read
        object: source-listed Docker and compose paths
        target: repository plus ~/vectoraiz-imports
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: Docker is unavailable because the local OrbStack application may be stopped.
    expected_answers:
      - kind: human_action
        verb: confirm
        object: OrbStack runtime state
        target: Titan-1
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-02]
    scenario: The exact candidate tag cannot be pulled from GHCR.
    expected_answers:
      - kind: human_action
        verb: check
        object: exact candidate build
        target: separately governed build status
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: ARM64 testing raises MemoryError and a destructive cleanup has been suggested.
    expected_answers:
      - kind: human_action
        verb: stop
        object: destructive cleanup
        target: owning-lane confirmation of exact remnant path
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-01]
    scenario: OrbStack is confirmed stopped and the source-supported correction is requested.
    expected_answers:
      - kind: human_action
        verb: open
        object: OrbStack application
        target: Titan-1
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-02]
    scenario: The candidate image build is still running.
    expected_answers:
      - kind: human_action
        verb: wait
        object: exact candidate build
        target: GHCR image availability
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A proposal replaces OrbStack and asks for a BREAKING classification.
    expected_answers:
      - kind: human_action
        verb: preserve
        object: unknown classification
        target: frontmatter owner adjudication
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: A proposal changes the import mount and asks whether REVIEW is required.
    expected_answers:
      - kind: human_action
        verb: preserve
        object: unknown classification
        target: frontmatter owner adjudication
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [F-02, F-03, F-04]
    scenario: A candidate fails locally and the evidence does not distinguish image availability, remnants, or an older semaphore defect.
    expected_answers:
      - kind: human_action
        verb: isolate
        object: exact image and failure signature
        target: F-02, F-03, or F-04 without guessing
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1389
last_refresh_commit: 5f968f167661dcac669dd42910037e05a50221ed
last_refresh_date: 2026-07-29T00:00:00Z
owner_agent: max
refresh_triggers:
  - OrbStack or Docker CLI path changes
  - vectorAIz image repository or compose paths change
  - local import mount changes
  - inherited failure signatures are verified or disproved
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1389 / 2026-07-29T17:03:11Z
last_lint_result: PASS
retrofit: true
trace_matrix_path: specs/ATHENA-PHASE2-CHUNK-C-TRACE-S1389.md
word_count_delta:
  before: 174
  after: 2098
  pct: 1105.75
```

All 21 current strict checks executed directly with zero findings. No wrapper
result is claimed while T-2026-000476 remains open.
