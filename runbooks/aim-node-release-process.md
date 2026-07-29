---
runbook_id: aim-node-release-process
domain: product-release
status: DRAFT
authoritative_for:
  - topic: aim-node-release
    section: §E. Operate
aliases: []
error_signatures:
  - signature: gh not found
    section: §F. Isolate
  - signature: GHCR build fails
    section: §F. Isolate
  - signature: Smoke-test GHCR login denied
    section: §F. Isolate
  - signature: Docker pull fails
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-29
system_name: aim-node-release-process
purpose_sentence: Create AIM Node release-candidate tags, promote a selected candidate, and follow the source-documented image, smoke-test, release, and installer path.
owner_agent: vulcan
escalation_contact: Unknown
lifecycle_ref: §J
authoritative_scope: The source-documented AIM Node release script, tag forms, GitHub Actions workflow, GHCR image, release-candidate test steps, health endpoint, and installer pointer; live runtime behavior remains unverified in this docs-only rewrite.
linter_version: 1.0.0
---

# AIM Node Release Process

> Phase 2 Chunk C DRAFT. The root source remains in place. This document is not
> catalog authority, does not authorize a release, and does not claim live
> verification of the external product repository or release infrastructure.

## §A. Header

The frontmatter supplies the required header fields. The source names Vulcan as
the release operator and excludes CC because `gh` is not in CC's PATH. It does
not name an escalation contact, so that field remains `Unknown`. External
repositories, GitHub Actions, GHCR, installers, and the live health endpoint
were not inspected.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Release-candidate tag creation | PARTIAL | `scripts/release.sh` | Source-only verification at the exact branch base; live execution unverified | 2026-07-29 |
| Stable promotion from a release candidate | PARTIAL | `scripts/release.sh` | Source-only verification at the exact branch base; live execution unverified | 2026-07-29 |
| Multi-architecture image build and publish | PARTIAL | `.github/workflows/docker-build.yml` | Source says the workflow builds AMD64 and ARM64 images; live run unverified | 2026-07-29 |
| Image smoke test and health check | PARTIAL | `.github/workflows/docker-build.yml` | Source describes manifest, pull, container, and health checks; results unverified | 2026-07-29 |
| Installer publication through get.ai.market | PARTIAL | `get.ai.market/aim-node` | Source records the installer route; live route unverified | 2026-07-29 |

`PARTIAL` means the inherited document describes the capability but this
docs-only pass did not inspect or execute the backing system.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Release Script | `scripts/release.sh` | Git tags and release metadata | GitHub Actions | `rc` creates a `v*` candidate; `promote` selects a candidate for stable release. |
| Release Workflow | `.github/workflows/docker-build.yml` | GitHub Actions run and GitHub Release | GHCR and repository release assets | Source lists build-push, smoke-test, and create-release jobs. |
| Customer Image | `ghcr.io/aidotmarket/aim-node` | GHCR image manifests | Docker clients | Source says the image is multi-architecture. |
| Health Endpoint | `/api/mgmt/health` | Running AIM Node container | Smoke-test job and local tester | Source says the smoke test and local RC test use this endpoint. |
| Installer Route | `get.ai.market/aim-node` | GitHub-hosted installer script | Installer client | Source says the route proxies the installer script from GitHub. |

The source records GitHub repository `aidotmarket/aim-node`, local path
`/Users/max/Projects/ai-market/aim-node`, and release assets `install.sh`,
`install.ps1`, and `docker-compose.aim-node.yml`.

Source-related documents are `aim-node.md`, `vz-release-process.md`, and
`cloudflare-worker.md`. They are references only; this DRAFT does not absorb or
validate them.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan | Create or promote an AIM Node release | `run_background` plus `scripts/release.sh` | External release credentials are source-mentioned but not inspected | PARTIAL — source-supported operator; live capability unverified |
| cc | Create or promote an AIM Node release | `gh` | Source says `gh` is absent from PATH | GAP — source explicitly says never use CC for releases |

No additional operator, reviewer, or escalation capability is inferred.

## §E. Operate

```yaml operate
- id: E-01
  trigger: An authorized operator intends to create an AIM Node release candidate.
  pre_conditions:
    - release_authority_confirmed_outside_this_runbook
    - product_repository_path_confirmed
    - explicit_homebrew_path_available
  tool_or_endpoint: scripts/release.sh rc <patch-or-minor-or-major>
  argument_sourcing:
    release_type: Choose patch, minor, or major from the source-documented release types.
    repository: Use the source-documented AIM Node product repository.
    path_prefix: Use the explicit /opt/homebrew/bin PATH prefix recorded by the source.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: A new v-prefixed release-candidate tag is created.
    verification: Unknown — the source does not define an independent post-command tag verification.
  expected_failures:
    - signature: gh not found
      cause: The explicit PATH prefix was not supplied.
  next_step_success: Wait for the source-documented workflow and use E-03 before promotion.
  next_step_failure: Isolate with F-01 and do not claim a release.
- id: E-02
  trigger: An authorized operator intends to promote a tested AIM Node release candidate.
  pre_conditions:
    - release_authority_confirmed_outside_this_runbook
    - selected_candidate_known
    - candidate_tested_per_E_03
  tool_or_endpoint: scripts/release.sh promote <candidate-tag>
  argument_sourcing:
    candidate_tag: Use the tested vX.Y.Z-rc.N tag; the source allows the latest candidate when omitted.
    repository: Use the source-documented AIM Node product repository.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: The selected candidate is promoted and the release workflow creates the stable release artifacts described by the source.
    verification: Unknown — the source does not define a complete independent stable-release verification.
  expected_failures:
    - signature: GHCR build fails
      cause: The source identifies an ARM64 QEMU issue as a likely cause.
    - signature: Smoke-test GHCR login denied
      cause: The source identifies backslash-escaped workflow expressions as the likely cause.
  next_step_success: Confirm the workflow, image, health check, and release artifacts through their owning systems.
  next_step_failure: Isolate with F-02 or F-03 and do not report stable completion.
- id: E-03
  trigger: A release candidate must be pulled, started, and health-checked before stable promotion.
  pre_conditions:
    - candidate_tag_known
    - docker_available
    - ghcr_build_completed
  tool_or_endpoint: docker pull, docker run, and curl for the AIM Node candidate
  argument_sourcing:
    candidate_tag: Use the exact release-candidate tag created by E-01.
    image: Use ghcr.io/aidotmarket/aim-node from the source.
    port_mapping: Use the source-documented 8080 to 8080 mapping.
    health_path: Use /api/mgmt/health from the source.
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: exact candidate image digest or tag
  expected_success:
    shape: Docker pulls and starts the candidate and the documented health endpoint responds successfully.
    verification: Call the source-documented health endpoint on the locally mapped port.
  expected_failures:
    - signature: Docker pull fails
      cause: The image build has not completed.
  next_step_success: If the separately authorized release decision is positive, E-02 may follow.
  next_step_failure: Isolate with F-04; do not promote.
```

The source also records this shell installer pointer:

```bash
curl -fsSL https://get.ai.market/aim-node | bash
```

It is publication evidence, not authorization to execute a remote script during
this docs-only pass.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `gh` is not found | Explicit Homebrew PATH prefix omitted; CC selected despite the source prohibition | Compare the invocation with the exact PATH-prefixed source command and confirm the operator identity | G-01 | CONFIRMED |
| F-02 | GHCR build fails | ARM64 QEMU issue | Read the failed GitHub Actions job identified by the source; no deeper cause is asserted here | G-02 | HYPOTHESIZED |
| F-03 | Smoke-test GHCR login is denied | Dollar-sign expressions were backslash-escaped in workflow YAML | Inspect the workflow expression spelling described by the source | G-03 | HYPOTHESIZED |
| F-04 | Docker pull fails | Image build has not completed | Check whether the source-documented GitHub Actions build is complete | G-04 | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Release Script
  root_cause: The source-required explicit PATH prefix was absent or CC was used.
  repair_entry_point: scripts/release.sh
  change_pattern: Re-run only with authorized release approval, Vulcan, and the explicit /opt/homebrew/bin PATH prefix.
  rollback_procedure: Unknown — the source does not define rollback for a partially created candidate tag.
  integrity_check: Unknown — the source does not define an independent verification beyond continuing to the workflow.
- id: G-02
  symptom_ref: F-02
  component_ref: Release Workflow
  root_cause: The source identifies an ARM64 QEMU issue as the likely cause.
  repair_entry_point: .github/workflows/docker-build.yml
  change_pattern: Use the source-documented action of re-running the GitHub Actions workflow.
  rollback_procedure: Unknown — the source does not define workflow rollback.
  integrity_check: Unknown — the source does not define a post-rerun acceptance check beyond successful completion.
- id: G-03
  symptom_ref: F-03
  component_ref: Release Workflow
  root_cause: The source says workflow expressions were backslash-escaped.
  repair_entry_point: .github/workflows/docker-build.yml
  change_pattern: Ensure the source-described expressions are not backslash-escaped.
  rollback_procedure: Unknown — the source does not define rollback for this workflow correction.
  integrity_check: Unknown — the source does not define a specific post-change login assertion beyond the smoke-test job.
- id: G-04
  symptom_ref: F-04
  component_ref: Customer Image
  root_cause: The source says the image has not been built yet.
  repair_entry_point: ghcr.io/aidotmarket/aim-node
  change_pattern: Wait for the GitHub Actions build to complete, then retry the exact candidate pull.
  rollback_procedure: None — waiting and retrying a pull does not change release state.
  integrity_check: The exact candidate tag pulls successfully.
```

## §H. Evolve

### §H.1 Invariants

- The source requires Vulcan through `run_background` with an explicit PATH and
  says never to use CC for releases.
- A candidate is pulled, started, and checked at `/api/mgmt/health` before
  stable promotion.
- The source names `ghcr.io/aidotmarket/aim-node` as the image repository and
  `get.ai.market/aim-node` as the installer route.

### §H.2 BREAKING predicates

Unknown — the source does not define a BREAKING change classification.

### §H.3 REVIEW predicates

Unknown — the source does not define a REVIEW change classification.

### §H.4 SAFE predicates

Unknown — the source does not define a SAFE change classification.

### §H.5 Boundary definitions

#### module

The source-supported module boundary is the release script, release workflow,
customer Docker image, health endpoint, compose asset, and installer route.

#### public contract

The source-supported public contract is the `v*` tag form, GHCR image name,
health path, and installer route. Further contract detail is Unknown.

#### runtime dependency

The source names GitHub Actions, GHCR, Docker, and the installer proxy as runtime
dependencies. Credential and availability details are Unknown.

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
    scenario: An authorized operator needs the source-documented first command for an AIM Node patch release candidate.
    expected_answers:
      - kind: tool_call
        tool: scripts/release.sh
        argument_values: {mode: rc, release_type: patch}
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: A tested AIM Node candidate is separately authorized for stable promotion.
    expected_answers:
      - kind: tool_call
        tool: scripts/release.sh
        argument_keys: [candidate_tag]
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: An AIM Node candidate must be pulled, started, and checked before promotion.
    expected_answers:
      - kind: tool_call
        tool: docker and curl
        argument_keys: [candidate_tag, port_mapping, health_path]
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
    scenario: The smoke-test job is denied during GHCR login.
    expected_answers:
      - kind: human_action
        verb: inspect
        object: workflow expressions
        target: backslash escaping
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-04]
    scenario: Docker cannot pull the exact candidate image.
    expected_answers:
      - kind: human_action
        verb: check
        object: build completion
        target: the source-documented GitHub Actions workflow
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
    refs: [G-04]
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
    scenario: A proposal changes the AIM Node tag form and asks for a BREAKING classification.
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
    refs: [E-02, F-02, F-04]
    scenario: Promotion was invoked but the image is absent and workflow state is unknown.
    expected_answers:
      - kind: human_action
        verb: stop
        object: completion claim
        target: workflow, exact image, and health verification
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
  - tag form changes
  - GitHub Actions workflow changes
  - GHCR image, health endpoint, or installer route changes
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
  before: 372
  after: 2150
  pct: 477.96
```

All 21 current strict checks executed directly with zero findings. No wrapper
result is claimed while T-2026-000476 remains open.
