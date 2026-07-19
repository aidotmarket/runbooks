---
runbook_id: boot-kernel-v2
domain: boot-kernel
status: ACTIVE
authoritative_for:
  - topic: boot-kernel-operations
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: boot_kernel_limit_exceeded
    section: §F. Isolate
  - signature: boot_kernel_source_drift
    section: §F. Isolate
  - signature: kernel_cutover_not_live
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-19
system_name: boot-kernel-v2
purpose_sentence: Boot Kernel v2 delivers a versioned non-truncatable constitution kernel as the session boot payload while keeping full CORE reachable on demand, and this runbook is the operating authority for its modes, deploy path, ceiling, and rollback.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Operating authority for Boot Kernel v2 delivery — modes (off/shadow/on), the BOOT_KERNEL_V2_MODE flag, the session-safe reloader deploy path, the enforced kernel ceiling and manifest, and cutover rollback. It does NOT own constitution CONTENT, which remains governed by CORE and the amendment gate.
linter_version: 1.0.0
---

# Boot Kernel v2 — Operating Runbook

## §A. Header

The frontmatter is authoritative for catalog identity. **Authority: boot-delivery operating companion.** Boot Kernel v2 is a delivery projection of full CORE; it does not amend the constitution. Where the kernel and full CORE conflict, CORE wins and is fetched on demand. This runbook governs delivery mechanics only.

**Fetch trigger:** session boot behaves unexpectedly, a boot integrity error surfaces, a mode change or cutover rollback is needed, or the kernel ceiling/manifest is in question.

**Source constitution:** CORE v9.11, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` (manifest `source_constitution_sha256`).

**Phase-1 deliverable discharge (S1284-D1..D4):** D1 what Boot Kernel v2 is (§A, §C); D2 modes off/shadow/on and where `BOOT_KERNEL_V2_MODE` lives (§C Mode Selector, §E-02); D3 the session-safe reloader deploy path (§C Session-safe Reloader, §E, §F-03/§G-03); D4 the enforced kernel ceiling + manifest, rollback = revert `b13d63c3`, and scratch sessions stay openable during a boot incident (§E-03, §F-01/§G-01, §H.1).

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| On-mode kernel boot delivery | SHIPPED | `tools/session.py:kd_session_open` | `tests/test_boot_kernel_v2.py` | 2026-07-19 |
| Kernel artifact load + integrity | SHIPPED | `tools/boot_kernel_v2.py:load_boot_kernel` | `tests/test_boot_kernel_v2.py` | 2026-07-19 |
| Assembled-envelope integrity | SHIPPED | `tools/boot_kernel_v2.py:_assert_assembled_envelope_integrity` | `tests/test_boot_delivery_contract_fixture.py` | 2026-07-19 |
| Enforced kernel ceiling (16000) | SHIPPED | `tools/boot_kernel_v2.py:enforced_kernel_max_chars` | `tests/test_boot_kernel_v2.py` | 2026-07-19 |
| Mode selection (off/shadow/on) | SHIPPED | `tools/boot_kernel_v2.py:read_boot_kernel_v2_mode` | `tests/test_boot_kernel_v2.py` | 2026-07-19 |
| Session-safe reloader deploy | SHIPPED | `scripts/reload_when_idle.sh` | `tests/test_reload_build_guard.sh` | 2026-07-19 |
| Shadow measurement + telemetry | SHIPPED | `tools/session.py:_emit_boot_kernel_shadow_open` | `tests/test_boot_payload_fit.py` | 2026-07-19 |
| Full CORE on-demand reachability | SHIPPED | `infra:constitution` | boot payload `core_md_full` via context-files | 2026-07-19 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Boot Kernel Artifact | `boot_kernel/v2/KERNEL.md` + `boot_kernel/v2/manifest` | Filesystem artifact dir | Kernel Loader | Versioned kernel plus manifest; `content_sha256` and `source_constitution_sha256` pinned; observed 11922 chars. |
| Kernel Loader | `tools/boot_kernel_v2.py:load_boot_kernel` | Manifest fields | Session Boot Assembler | Validates source SHA, single SHA-pinned catalog ref, section order, and enforced ceiling; raises `BootAssemblyError`. |
| Mode Selector | `tools/boot_kernel_v2.py:read_boot_kernel_v2_mode` | `BOOT_KERNEL_V2_MODE` env | `scripts/launch_mcp_server.sh` | Code default is `off`; launcher exports `on`. Values: off, shadow, on. |
| Session Boot Assembler | `tools/session.py:kd_session_open` | Living State `infra:constitution` | Kernel Loader, Constitution Source | On-mode serves the kernel envelope and sets `core_md=None`; off serves full `core_md`; shadow serves full CORE and measures the kernel. |
| Session-safe Reloader | `scripts/reload_when_idle.sh` (`com.koskadeux.mcp-reloader`) | `registry.db`, `/var/tmp/koskadeux/deployed_sha` | launchd, git | Bounces the server only when no non-scratch session is live; fail-closed on any uncertainty; records HEAD to `deployed_sha`. |
| Constitution Source | `infra:constitution` | Living State | context-files endpoint (`core_md_full`) | Sole current normative CORE; full text reachable on demand under on-mode. |

The boot wire budget is 64000 characters; the enforced kernel ceiling is a separate manifest-derived cap (`enforced_kernel_max_chars`, currently 16000) measured against `KERNEL.md`. Protected boot content is never trimmed.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Verify on-mode boot is live | Shell + git read, session boot payload inspection | Read | COMPLETE |
| Vulcan or Mars | Change mode or roll back the cutover | Edit `launch_mcp_server.sh` / git revert `b13d63c3` + reloader | Write (main push) | COMPLETE |
| Session-safe Reloader | Bounce server to committed code when idle | `launchctl kickstart` | System | COMPLETE |
| Max | Approve cutover or rollback | Human decision | Final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Confirm the running server is delivering the on-mode kernel, not full CORE.
  pre_conditions: [server_running, git_available, boot_payload_inspectable]
  tool_or_endpoint: cat /var/tmp/koskadeux/deployed_sha ; git -C /Users/max/koskadeux-mcp rev-parse origin/main ; inspect the session boot payload
  argument_sourcing: {deployed_sha: read the marker file, origin_main: read from git, payload: read the current session boot envelope}
  idempotency: IDEMPOTENT
  expected_success: {shape: deployed_sha equals origin/main equals b13d63c3 and the boot payload carries boot_kernel with core_md null, verification: confirm wire payload well under 64000 and full CORE reachable via context-files}
  expected_failures: [{signature: kernel_cutover_not_live, cause: the reloader has not bounced the server yet because a session was live}]
  next_step_success: Record on-mode live; proceed with dependent gate or work.
  next_step_failure: Treat per F-03; wait for idle bounce or escalate for a Max-gated manual kickstart.
- id: E-02
  trigger: Change the boot kernel mode (off, shadow, or on).
  pre_conditions: [launch_script_writable, change_authorized]
  tool_or_endpoint: edit scripts/launch_mcp_server.sh BOOT_KERNEL_V2_MODE ; commit + push ; reloader bounces when idle
  argument_sourcing: {mode: use the authorized target mode off|shadow|on, flag_location: scripts/launch_mcp_server.sh (or plist EnvironmentVariables override)}
  idempotency: IDEMPOTENT
  expected_success: {shape: launcher exports the intended BOOT_KERNEL_V2_MODE and the reloader bounces the server onto it when idle, verification: read_boot_kernel_v2_mode reflects the mode after bounce}
  expected_failures: [{signature: kernel_cutover_not_live, cause: reloader deferred while a session was live or the flag was set only in an inherited environment}]
  next_step_success: Verify the delivered mode per E-01.
  next_step_failure: Follow F-03.
- id: E-03
  trigger: Roll back the on-mode cutover.
  pre_conditions: [rollback_authorized, git_main_pushable]
  tool_or_endpoint: git revert b13d63c3 (one line, launch_mcp_server.sh) OR set BOOT_KERNEL_V2_MODE=off in the plist ; push ; reloader bounces back to off
  argument_sourcing: {commit: b13d63c3 cutover commit, flag: BOOT_KERNEL_V2_MODE}
  idempotency: IDEMPOTENT
  expected_success: {shape: launcher returns to off-mode and the reloader bounces the server back to full-CORE delivery, verification: E-01 shows core_md populated and boot_kernel absent}
  expected_failures: [{signature: kernel_cutover_not_live, cause: reloader deferred while a session was live}]
  next_step_success: Confirm off-mode live; scratch sessions remain openable throughout any boot incident.
  next_step_failure: Follow F-03; if boot itself is broken, open scratch sessions and diagnose per F-01/F-02.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Session boot aborts with `BOOT_KERNEL_LIMIT_EXCEEDED` (`boot_kernel_limit_exceeded`). | KERNEL.md grew past the manifest `enforced_kernel_max_chars` ceiling (16000). | Compare `kernel_size_report` observed chars against `enforced_kernel_max_chars`; protected content is never trimmed so boot hard-stops. | G-01 | CONFIRMED |
| F-02 | Session boot aborts with `BOOT_KERNEL_SOURCE_DRIFT` (`boot_kernel_source_drift`). | Live `infra:constitution` SHA no longer matches the manifest `source_constitution_sha256`. | Recompute the live constitution SHA-256 and compare with the manifest source field. | G-02 | CONFIRMED |
| F-03 | Merged kernel code is not live; the server still serves the prior mode (`kernel_cutover_not_live`). | The session-safe reloader deferred because a non-scratch session was live, or the flag was set only in an inherited environment. | Compare `/var/tmp/koskadeux/deployed_sha` with working-tree HEAD and check for any live non-scratch session in the registry. | G-03 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Boot Kernel Artifact
  root_cause: The kernel content exceeds its manifest-enforced ceiling; protected content is not truncatable, so boot fails closed.
  repair_entry_point: boot_kernel/v2/KERNEL.md and boot_kernel/v2/manifest enforced_kernel_max_chars
  change_pattern: Trim kernel content back under the ceiling and regenerate the manifest, OR raise enforced_kernel_max_chars through the approved spec path with evidence; never weaken protected boot content.
  rollback_procedure: Revert the cutover commit b13d63c3 so the reloader bounces back to off-mode full-CORE delivery while the ceiling is corrected.
  integrity_check: load_boot_kernel succeeds, observed kernel chars are under enforced_kernel_max_chars, and a session boots on-mode.
- id: G-02
  symptom_ref: F-02
  component_ref: Constitution Source
  root_cause: The kernel was regenerated from, or the live constitution diverged from, a different CORE than the manifest records.
  repair_entry_point: infra:constitution and boot_kernel/v2/manifest source_constitution_sha256
  change_pattern: Reconcile by regenerating the kernel from the exact current CORE and rewriting the manifest source SHA to match the live constitution; do not point the manifest at a stale mirror.
  rollback_procedure: Revert to off-mode so full CORE is served directly from infra:constitution until the source SHA is reconciled.
  integrity_check: Live constitution SHA-256 equals manifest source_constitution_sha256 and load_boot_kernel passes.
- id: G-03
  symptom_ref: F-03
  component_ref: Session-safe Reloader
  root_cause: The reloader bounces only when idle and fails closed; a live non-scratch session (or an inherited-only flag) kept the server on prior code.
  repair_entry_point: scripts/reload_when_idle.sh and /var/tmp/koskadeux/deployed_sha
  change_pattern: Let both instances go idle so the next reloader tick bounces the server, or perform a Max-gated manual launchctl kickstart; ensure the flag is set in launch_mcp_server.sh (or the plist), not only an inherited shell.
  rollback_procedure: No content rollback needed; if the wrong mode deployed, correct the flag and let the reloader re-bounce.
  integrity_check: /var/tmp/koskadeux/deployed_sha equals working-tree HEAD and read_boot_kernel_v2_mode reflects the intended mode.
```

## §H. Evolve

### §H.1 Invariants

The kernel is a delivery projection of CORE and MUST NOT add, remove, weaken, or reinterpret any constitutional obligation; constitution CONTENT changes require the CORE amendment gate (unanimous Council plus Max). The manifest `source_constitution_sha256` MUST match the live constitution. The boot envelope carries exactly one SHA-pinned catalog reference. Protected boot content is never trimmed; the enforced kernel ceiling and the 64000 wire budget are guards, not content authorities. Scratch sessions MUST remain openable during any boot incident.

### §H.2 BREAKING predicates

Changing the boot delivery contract (envelope shape, the comms-contract marker, the single-catalog-ref rule), altering the `source_constitution_sha256` binding, or delivering the kernel in a way that changes a constitutional obligation is BREAKING and routes through the amendment gate.

### §H.3 REVIEW predicates

Adjusting `enforced_kernel_max_chars`, changing mode-selection defaults, or modifying the reloader deploy conditions is REVIEW.

### §H.4 SAFE predicates

Regenerating the kernel from unchanged CORE, refreshing verification dates, or documentation-only edits within existing semantics are SAFE.

### §H.5 Boundary definitions

#### module

`boot_kernel/v2/` artifact directory, `tools/boot_kernel_v2.py` loader, the `tools/session.py` boot assembler, and `scripts/reload_when_idle.sh`.

#### public contract

The boot envelope shape, the `BOOT_KERNEL_V2_MODE` values, the manifest field set, and the single SHA-pinned catalog reference.

#### runtime dependency

Filesystem artifact availability, Living State `infra:constitution`, the registry `deployed_sha` marker, and launchd for the reloader.

#### config default

`BOOT_KERNEL_V2_MODE` code default is `off`; the launcher sets `on`. `enforced_kernel_max_chars` ships in the manifest (16000).

### §H.6 Adjudication

CORE wins any conflict with the kernel. A change that could alter a constitutional obligation is BREAKING regardless of how mechanically small it looks, and the more restrictive classification wins.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: An operator must confirm this session booted on the kernel rather than full CORE., expected_answers: [{kind: human_action, verb: compare, object: deployed_sha and origin main and the boot payload, target: on-mode delivery}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: The mode must move from off to on., expected_answers: [{kind: human_action, verb: set, object: BOOT_KERNEL_V2_MODE, target: scripts/launch_mcp_server.sh}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: The on-mode cutover must be rolled back., expected_answers: [{kind: human_action, verb: revert, object: commit b13d63c3, target: launch_mcp_server.sh}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: Boot aborts citing the kernel character limit., expected_answers: [{kind: classification, label: BOOT_KERNEL_LIMIT_EXCEEDED}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-02], scenario: Boot aborts because the constitution hash does not match the manifest., expected_answers: [{kind: classification, label: BOOT_KERNEL_SOURCE_DRIFT}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-03], scenario: Merged on-mode code is not being served though the flag is committed., expected_answers: [{kind: human_action, verb: compare, object: deployed_sha and working-tree HEAD, target: reloader idle state}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: The kernel has grown past its enforced ceiling., expected_answers: [{kind: human_action, verb: trim, object: KERNEL.md content, target: under enforced_kernel_max_chars}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: The manifest source SHA points at a different CORE than the live constitution., expected_answers: [{kind: human_action, verb: reconcile, object: manifest source_constitution_sha256, target: live infra:constitution}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal rewords a kernel clause so it weakens a CORE obligation without the amendment gate., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [§H], scenario: A proposal raises enforced_kernel_max_chars from 16000 to 18000., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [§H.6, F-03], scenario: A session boots on full CORE though the cutover flag is committed to main., expected_answers: [{kind: human_action, verb: compare, object: deployed_sha and working-tree HEAD, target: reloader idle state}, {kind: classification, label: kernel_cutover_not_live}], weight: 0.090909091}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1288
last_refresh_commit: b13d63c3
last_refresh_date: 2026-07-19T18:00:00Z
owner_agent: mars
refresh_triggers: [boot kernel mode change, cutover or rollback, enforced ceiling change, CORE version or source SHA change, reloader deploy-path change]
scheduled_cadence: 90d
last_harness_pass_rate: null
last_harness_date: 2026-07-19T18:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1288 / 2026-07-19T18:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: null
word_count_delta: null
```
