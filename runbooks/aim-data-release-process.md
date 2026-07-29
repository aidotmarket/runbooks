---
runbook_id: aim-data-release-process
domain: product-release
status: DRAFT
authoritative_for:
  - topic: aim-data-release
    section: §E. Operate
aliases: []
error_signatures:
  - signature: gh not found
    section: §F. Isolate
  - signature: GHCR build fails
    section: §F. Isolate
  - signature: Docker pull fails
    section: §F. Isolate
  - signature: Tag collision with VZ
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-29
system_name: aim-data-release-process
purpose_sentence: Create AIM Data release-candidate tags, promote a selected candidate, and follow the source-documented image, smoke-test, release, and installer path.
owner_agent: vulcan
escalation_contact: Unknown
lifecycle_ref: §J
authoritative_scope: The source-documented AIM Data release script, tag forms, GitHub Actions workflow, GHCR image, release-candidate test steps, and installer publication pointers; live runtime behavior remains unverified in this docs-only rewrite.
linter_version: 1.0.0
---

# AIM Data Release Process

> Phase 2 Chunk C DRAFT. The root source remains in place. This document is not
> catalog authority, does not authorize a release, and does not claim live
> verification of the external product repository or release infrastructure.

## §A. Header

The frontmatter supplies the required header fields. The source names Vulcan as
the release operator and explicitly excludes CC because `gh` is not in CC's
PATH. It does not name an escalation contact, so that field remains `Unknown`.
All operational claims below are source-preserving restatements; external
repositories, GitHub Actions, GHCR, Cloudflare, and installers were not inspected.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Release-candidate tag creation | PARTIAL | `scripts/release-aim-data.sh` | Source-only verification at the exact branch base; live execution unverified | 2026-07-29 |
| Stable promotion from a release candidate | PARTIAL | `scripts/release-aim-data.sh` | Source-only verification at the exact branch base; live execution unverified | 2026-07-29 |
| Multi-architecture image build and publish | PARTIAL | `.github/workflows/aim-data-release.yml` | Source says the workflow builds AMD64 and ARM64 images; live run unverified | 2026-07-29 |
| Image smoke test and GitHub Release creation | PARTIAL | `.github/workflows/aim-data-release.yml` | Source describes both workflow jobs; results unverified | 2026-07-29 |
| Installer publication through get.ai.market | PARTIAL | `installers/aim-data/install.sh` | Source records target URLs and worker routing; live route unverified | 2026-07-29 |

`PARTIAL` means the inherited document describes the capability but this
docs-only pass did not inspect or execute the backing system.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Release Script | `scripts/release-aim-data.sh` | Git tags and release metadata | GitHub Actions | `rc` creates an `aim-data-v*` candidate; `promote` selects a candidate for stable release. |
| Release Workflow | `.github/workflows/aim-data-release.yml` | GitHub Actions run and GitHub Release | GHCR and repository release assets | Source lists build-push, smoke-test, and create-release jobs. |
| Customer Image | `ghcr.io/aidotmarket/aim-data` | GHCR image manifests | Docker clients | Source says the image is AMD64 and ARM64. |
| Installer Assets | `installers/aim-data/install.sh` and `install.ps1` | Product repository release assets | `get.ai.market` Cloudflare Worker | Source records macOS/Linux and Windows installer routes. |
| Product Repository | `aidotmarket/aim-data` | Git repository | Release script, workflow, Dockerfile, compose, installers | The source says AIM Data release machinery is decoupled from vectorAIz. |

The source records two local paths for the same product repository:
`/Users/max/aim-data` for customer-facing code and
`/Users/max/Projects/ai-market/aim-data` for the release script and workflow
inputs. Their current equivalence is unverified. It also names
`Dockerfile.customer`, `docker-compose.aim-data.yml`, `install.sh`,
`install.ps1`, and `docker-compose.aim-data.yml` as release assets.

Source-related documents are `aim-node-release-process.md`,
`vz-release-process.md`, and `cloudflare-worker.md`. They are references only;
this DRAFT does not absorb or validate them.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan | Create or promote an AIM Data release | `run_background` plus `scripts/release-aim-data.sh` | External release credentials are source-mentioned but not inspected | PARTIAL — source-supported operator; live capability unverified |
| cc | Create or promote an AIM Data release | `gh` | Source says `gh` is absent from PATH | GAP — source explicitly says never use CC for releases |

No additional operator, reviewer, or escalation capability is inferred.

## §E. Operate

```yaml operate
- id: E-01
  trigger: An authorized operator intends to create an AIM Data release candidate.
  pre_conditions:
    - release_authority_confirmed_outside_this_runbook
    - product_repository_path_confirmed
    - explicit_homebrew_path_available
  tool_or_endpoint: scripts/release-aim-data.sh rc <patch-or-minor-or-major>
  argument_sourcing:
    release_type: Choose patch, minor, or major from the source-documented release types.
    repository: Use the source-documented AIM Data product repository.
    path_prefix: Use the explicit /opt/homebrew/bin PATH prefix recorded by the source.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: A new aim-data-v-prefixed release-candidate tag is created.
    verification: Unknown — the source does not define an independent post-command tag verification.
  expected_failures:
    - signature: gh not found
      cause: The explicit PATH prefix was not supplied.
    - signature: Tag collision with VZ
      cause: The wrong release script or tag namespace was used.
  next_step_success: Wait for the source-documented workflow and use E-03 before promotion.
  next_step_failure: Isolate with F-01 or F-04 and do not claim a release.
- id: E-02
  trigger: An authorized operator intends to promote a tested AIM Data release candidate.
  pre_conditions:
    - release_authority_confirmed_outside_this_runbook
    - selected_candidate_known
    - candidate_tested_per_E_03
  tool_or_endpoint: scripts/release-aim-data.sh promote <candidate-tag>
  argument_sourcing:
    candidate_tag: Use the tested aim-data-vX.Y.Z-rc.N tag; the source allows the latest candidate when omitted.
    repository: Use the source-documented AIM Data product repository.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: The selected candidate is promoted and the release workflow creates the stable release artifacts described by the source.
    verification: Unknown — the source does not define a complete independent stable-release verification.
  expected_failures:
    - signature: GHCR build fails
      cause: The source identifies an ARM64 QEMU issue as a likely cause.
    - signature: Docker pull fails
      cause: The image build has not completed.
  next_step_success: Confirm the workflow, image, and release artifacts through their owning systems.
  next_step_failure: Isolate with F-02 or F-03 and do not report stable completion.
- id: E-03
  trigger: A release candidate must be tested before any stable promotion.
  pre_conditions:
    - candidate_tag_known
    - docker_available
    - ghcr_build_completed
  tool_or_endpoint: docker pull and docker run for ghcr.io/aidotmarket/aim-data:<candidate-tag>
  argument_sourcing:
    candidate_tag: Use the exact release-candidate tag created by E-01.
    image: Use the source-documented ghcr.io/aidotmarket/aim-data repository.
    port_mapping: Use the source-documented 8080 to 8080 mapping.
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: exact candidate image digest or tag
  expected_success:
    shape: Docker pulls the candidate and starts the container with the documented port mapping.
    verification: Unknown — the source says to test locally but does not define the complete health assertion.
  expected_failures:
    - signature: Docker pull fails
      cause: The image build has not completed.
  next_step_success: If the separately authorized release decision is positive, E-02 may follow.
  next_step_failure: Isolate with F-03; do not promote.
```

The source also records these installer commands:

```bash
curl -fsSL https://get.ai.market/aim-data | bash
irm https://get.ai.market/aim-data/windows | iex
```

They are publication pointers, not authorization to execute remote scripts
during this docs-only pass.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `gh` is not found | Explicit Homebrew PATH prefix omitted; CC selected despite the source prohibition | Compare the invocation with the exact PATH-prefixed source command and confirm the operator identity | G-01 | CONFIRMED |
| F-02 | GHCR build fails | ARM64 QEMU issue | Read the failed GitHub Actions job identified by the source; no deeper cause is asserted here | G-02 | HYPOTHESIZED |
| F-03 | Docker pull fails | Image build has not completed | Check whether the source-documented GitHub Actions build is complete | G-03 | HYPOTHESIZED |
| F-04 | AIM Data and vectorAIz tags collide | Wrong release script or tag namespace used | Confirm the AIM Data tag begins `aim-data-v` and the vectorAIz tag begins `v` | G-04 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Release Script
  root_cause: The source-required explicit PATH prefix was absent or CC was used.
  repair_entry_point: scripts/release-aim-data.sh
  change_pattern: Re-run only with authorized release approval, Vulcan, and the explicit /opt/homebrew/bin PATH prefix.
  rollback_procedure: Unknown — the source does not define rollback for a partially created candidate tag.
  integrity_check: Unknown — the source does not define an independent verification beyond continuing to the workflow.
- id: G-02
  symptom_ref: F-02
  component_ref: Release Workflow
  root_cause: The source identifies an ARM64 QEMU issue as the likely cause.
  repair_entry_point: .github/workflows/aim-data-release.yml
  change_pattern: Use the source-documented action of re-running the GitHub Actions workflow.
  rollback_procedure: Unknown — the source does not define workflow rollback.
  integrity_check: Unknown — the source does not define a post-rerun acceptance check beyond successful completion.
- id: G-03
  symptom_ref: F-03
  component_ref: Customer Image
  root_cause: The source says the image has not been built yet.
  repair_entry_point: ghcr.io/aidotmarket/aim-data
  change_pattern: Wait for the GitHub Actions build to complete, then retry the exact candidate pull.
  rollback_procedure: None — waiting and retrying a pull does not change release state.
  integrity_check: The exact candidate tag pulls successfully.
- id: G-04
  symptom_ref: F-04
  component_ref: Release Script
  root_cause: The wrong script or tag namespace was used.
  repair_entry_point: scripts/release-aim-data.sh
  change_pattern: Use the AIM Data script and its aim-data-v-prefixed tag namespace.
  rollback_procedure: Unknown — the source does not define deletion or rollback of an incorrectly created tag.
  integrity_check: The candidate tag uses the aim-data-v prefix and does not use the vectorAIz v-only prefix.
```

## §H. Evolve

### §H.1 Invariants

- AIM Data tags use the `aim-data-v*` namespace; vectorAIz uses `v*`.
- The source requires Vulcan through `run_background` with an explicit PATH and
  says never to use CC for releases.
- A candidate is tested before stable promotion.
- Release machinery, product code, installers, compose, and customer image are
  source-described as living in the standalone AIM Data repository.

### §H.2 BREAKING predicates

Unknown — the source does not define a BREAKING change classification.

### §H.3 REVIEW predicates

Unknown — the source does not define a REVIEW change classification.

### §H.4 SAFE predicates

Unknown — the source does not define a SAFE change classification.

### §H.5 Boundary definitions

#### module

The source-supported module boundary is the release script, release workflow,
customer Docker image, compose file, and installer assets in `aidotmarket/aim-data`.

#### public contract

The source-supported public contract is the tag namespace, GHCR image name, and
two `get.ai.market` installer routes. Further contract detail is Unknown.

#### runtime dependency

The source names GitHub Actions, GHCR, Docker, and the Cloudflare Worker as
runtime dependencies. Credential and availability details are Unknown.

#### config default

The source provides examples, not an authoritative configuration-default
contract. Configuration defaults are Unknown.

### §H.6 Adjudication

Unknown — the source does not define change-class adjudication.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: An authorized operator needs the source-documented first command for an AIM Data patch release candidate.
    expected_answers:
      - kind: tool_call
        tool: scripts/release-aim-data.sh
        argument_values: {mode: rc, release_type: patch}
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: A tested AIM Data candidate is separately authorized for stable promotion.
    expected_answers:
      - kind: tool_call
        tool: scripts/release-aim-data.sh
        argument_keys: [candidate_tag]
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: An AIM Data release candidate must be pulled and started before promotion.
    expected_answers:
      - kind: tool_call
        tool: docker
        argument_keys: [candidate_tag, port_mapping]
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: The release command reports that gh is not found.
    expected_answers:
      - kind: human_action
        verb: compare
        object: invocation and operator
        target: the explicit PATH-prefixed Vulcan source procedure
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-03]
    scenario: Docker cannot pull the exact candidate image.
    expected_answers:
      - kind: human_action
        verb: check
        object: build completion
        target: the source-documented GitHub Actions workflow
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-04]
    scenario: A candidate tag may have collided with the vectorAIz namespace.
    expected_answers:
      - kind: human_action
        verb: compare
        object: tag prefix
        target: aim-data-v versus v
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-01]
    scenario: The source-supported correction for a missing gh command is needed.
    expected_answers:
      - kind: human_action
        verb: restore
        object: explicit PATH-prefixed Vulcan invocation
        target: release command
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-03]
    scenario: The image build is not complete and the candidate pull failed.
    expected_answers:
      - kind: human_action
        verb: wait
        object: GitHub Actions build
        target: exact candidate image
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A proposal changes the AIM Data tag namespace and asks for a BREAKING classification.
    expected_answers:
      - kind: human_action
        verb: preserve
        object: unknown classification
        target: frontmatter owner adjudication
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: A proposal changes installer routing and asks whether REVIEW is required.
    expected_answers:
      - kind: human_action
        verb: preserve
        object: unknown classification
        target: frontmatter owner adjudication
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [E-02, F-02, F-03]
    scenario: Promotion was invoked but the image is absent and the workflow state is unknown.
    expected_answers:
      - kind: human_action
        verb: stop
        object: completion claim
        target: workflow and exact image verification
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1389
last_refresh_commit: 5f968f167661dcac669dd42910037e05a50221ed
last_refresh_date: 2026-07-29T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - release script contract changes
  - tag namespace changes
  - GitHub Actions workflow changes
  - GHCR image or installer route changes
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
  before: 499
  after: 2206
  pct: 342.08
```

All 21 current strict checks executed directly with zero findings. No wrapper
result is claimed while T-2026-000476 remains open.
