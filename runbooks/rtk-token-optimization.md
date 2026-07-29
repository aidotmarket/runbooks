---
runbook_id: rtk-token-optimization
domain: operator-tooling
status: DRAFT
authoritative_for:
  - topic: rtk-token-optimization
    section: §E. Operate
aliases: []
error_signatures:
  - signature: Agent not using RTK
    section: §F. Isolate
  - signature: RTK stripping too much info
    section: §F. Isolate
  - signature: MP not prefixing with rtk
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: max
last_verified_at: 2026-07-29
system_name: rtk-token-optimization
purpose_sentence: Preserve the source-documented RTK installation, agent integrations, output-recovery configuration, measurement commands, upgrade path, and troubleshooting limits.
owner_agent: max
escalation_contact: Unknown
lifecycle_ref: §J
authoritative_scope: RTK command-output compression on Titan-1, its source-listed CC, AG, and MP integrations, disabled telemetry, failure-only tee recovery, savings inspection, update, exclusion, and uninstall procedures; current installation state remains unverified.
linter_version: 1.0.0
---

# RTK Token Optimization

> Phase 2 Chunk D DRAFT. The root source remains unchanged. This docs-only
> rewrite did not inspect the RTK installation, agent configuration, telemetry,
> tee files, Homebrew state, or claimed savings.

## §A. Header

The frontmatter supplies the required fields. Git provenance identifies Max as
the source maintainer. The source records RTK v0.34.3 installed through
Homebrew on Titan-1 in S388; that is historical evidence, not a current-version
claim or configuration default. Runtime ownership and escalation contact are
not stated and remain `Unknown`.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Command-output compression | PARTIAL | `rtk CLI proxy` | Source-only verification; current binary uninspected | 2026-07-29 |
| CC PreToolUse integration | PARTIAL | `~/.claude/hooks/rtk-rewrite.sh` | Source-only verification; hook state uninspected | 2026-07-29 |
| AG BeforeTool integration | PARTIAL | `~/.gemini/hooks/rtk-hook-gemini.sh` | Source-only verification; hook state uninspected | 2026-07-29 |
| MP instruction-based integration | PARTIAL | `~/.codex/AGENTS.md / ~/.codex/RTK.md` | Source says compliance is model-dependent | 2026-07-29 |
| Failure-output recovery | PARTIAL | `RTK tee configuration` | Source-only verification; tee files uninspected | 2026-07-29 |
| Savings and missed-opportunity inspection | PARTIAL | `rtk gain / rtk discover` | Source-only verification; commands not executed | 2026-07-29 |

The source claims typical 60–90% savings and lists command-specific examples.
Those figures were not remeasured in this pass.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| RTK CLI | `rtk <command>` | Local RTK statistics | Shell commands | Filters, groups, truncates, and deduplicates output before agent context receives it. |
| CC Hook | `~/.claude/hooks/rtk-rewrite.sh` | Claude configuration files | Claude Code PreToolUse | Source says restart CC after changes. |
| AG Hook | `~/.gemini/hooks/rtk-hook-gemini.sh` | Gemini configuration files | Gemini BeforeTool | Source says restart Gemini CLI after changes. |
| MP Instructions | `~/.codex/AGENTS.md` with `~/.codex/RTK.md` | Codex configuration files | Codex CLI | Instruction-based rather than hook-based; source says it is less reliable. |
| RTK Configuration | `~/Library/Application Support/rtk/config.toml` | Local TOML file | Telemetry, tee, hook exclusions | Source records telemetry disabled and failure-only tee mode. |
| Tee Recovery | `~/.local/share/rtk/tee/` | Local failure output files | RTK Configuration | Full output is source-described as retained only for failures, with 50-file maximum. |

Vulcan is explicitly outside the integration boundary: the source says MCP
shell output arrives through the gateway as JSON and is not intercepted by RTK.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| CC | Route shell commands through RTK | PreToolUse hook | Local user configuration; exact scope Unknown | PARTIAL — source-described, live state unverified |
| AG | Route shell commands through RTK | BeforeTool hook | Local user configuration; exact scope Unknown | PARTIAL — source-described, live state unverified |
| MP | Prefix shell commands with RTK | `AGENTS.md` instruction | Local user configuration; exact scope Unknown | PARTIAL — instruction compliance is not guaranteed |
| Vulcan | Use RTK on gateway tool output | Not applicable | Gateway JSON path | GAP — source explicitly excludes this path |
| max | Maintain the source documentation | Git | Documentation provenance | PARTIAL — runtime operator remains Unknown |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An operator needs to verify RTK installation and agent-hook visibility.
  pre_conditions:
    - Titan_1_local_shell_available
    - read_only_verification_intended
  tool_or_endpoint: rtk --version and rtk init --show
  argument_sourcing:
    version: Read the installed version from command output; do not assume the historical v0.34.3 value.
    hook_state: Read the status for CC, AG, and MP from rtk init --show.
  idempotency: IDEMPOTENT
  expected_success:
    shape: Installed RTK version and source-supported integration status are visible.
    verification: Compare reported integration paths with §C without modifying configuration.
  expected_failures:
    - signature: Agent not using RTK
      cause: Hook or instruction configuration is missing, stale, or the agent was not restarted.
  next_step_success: Use E-02 to inspect savings or E-03 only when a configuration change is authorized.
  next_step_failure: Isolate with F-01 or F-03.
- id: E-02
  trigger: An operator needs source-supported savings or missed-command evidence.
  pre_conditions:
    - RTK_installed
    - local_statistics_available
  tool_or_endpoint: rtk gain or rtk discover
  argument_sourcing:
    savings_view: Use gain, gain --graph, or gain --daily according to the requested time view.
    discovery_view: Use discover or discover --all --since 7 according to the requested scope.
  idempotency: IDEMPOTENT
  expected_success:
    shape: RTK reports measured savings or commands that bypassed optimization.
    verification: Treat only current command output as measurement; historical percentages are context.
  expected_failures:
    - signature: RTK stripping too much info
      cause: Compressed output omitted detail required for diagnosis.
  next_step_success: Record the measurement outside this runbook if required.
  next_step_failure: Use the source-documented tee recovery or tracked passthrough path.
- id: E-03
  trigger: An authorized operator must change RTK configuration, update the package, exclude a command, or remove an integration.
  pre_conditions:
    - change_authority_confirmed_outside_this_runbook
    - exact_target_integration_known
    - current_configuration_backed_up_or_readable
  tool_or_endpoint: Homebrew, rtk init, or the RTK config file according to the selected source procedure.
  argument_sourcing:
    update: Use brew upgrade rtk; the source says hooks survive upgrades and no re-init is needed.
    exclusion: Add the exact command to hooks.exclude_commands in the RTK config.
    uninstall: Use the source-listed rtk init uninstall form for CC or AG, then brew uninstall rtk when complete removal is intended.
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Only the selected package, hook, or exclusion state changes.
    verification: Re-run rtk --version and rtk init --show; restart the affected agent when the source requires it.
  expected_failures:
    - signature: Agent not using RTK
      cause: Hook change was not followed by the source-required agent restart.
    - signature: MP not prefixing with rtk
      cause: MP integration is instruction-based and the instruction files are absent or not followed.
  next_step_success: Measure the resulting behavior with E-01 and E-02.
  next_step_failure: Isolate with F-01 through F-03; rollback detail beyond the listed uninstall forms is Unknown.
```

Source-preserved configuration:

```toml
[telemetry]
enabled = false

[tee]
enabled = true
mode = "failures"
max_files = 50
```

The source also records `RTK_TELEMETRY_DISABLED=1` in `~/.zshrc`, and an
optional `[hooks] exclude_commands` list. Exact current values remain
unverified.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | An agent is not using RTK | Hook missing, instruction missing, or agent not restarted | Run `rtk init --show`, inspect only the source-listed config path, then retry one representative command | G-01 | CONFIRMED |
| F-02 | RTK strips detail needed for diagnosis | Compression removed relevant output | Read the failure-only tee file when present or use tracked passthrough | G-02 | CONFIRMED |
| F-03 | MP does not prefix commands with `rtk` | `AGENTS.md` or `RTK.md` missing, or instruction not followed | Confirm both source-listed Codex files exist and contain the instruction | G-03 | CONFIRMED |
| F-04 | Savings claim cannot be reproduced | Historical percentages or different command mix | Run current `rtk gain` output and compare like-for-like commands | G-04 | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: RTK CLI
  root_cause: The relevant integration is absent, stale, or not active in the current agent process.
  repair_entry_point: The source-listed hook or instruction file for the affected agent
  change_pattern: Confirm the exact integration path, restore only the missing source-supported entry, and restart CC or AG after changes.
  rollback_procedure: Use the source-listed rtk init uninstall form for the affected hook; further rollback is Unknown.
  integrity_check: rtk init --show reports the integration and a representative command is compressed.
- id: G-02
  symptom_ref: F-02
  component_ref: Tee Recovery
  root_cause: Compressed output omitted detail needed for a failed command.
  repair_entry_point: The source-listed tee directory or rtk proxy passthrough
  change_pattern: Read the saved full failure output when available; otherwise use rtk proxy for tracked passthrough.
  rollback_procedure: None — reading recovery output does not alter command state.
  integrity_check: The required diagnostic detail is visible without disabling RTK globally.
- id: G-03
  symptom_ref: F-03
  component_ref: MP Instructions
  root_cause: The instruction files are absent or the model did not follow them.
  repair_entry_point: ~/.codex/AGENTS.md and ~/.codex/RTK.md
  change_pattern: Restore the source-described reference and instruction; accept that model compliance remains unguaranteed.
  rollback_procedure: Remove only the restored instruction reference if authorized.
  integrity_check: The next representative MP shell command is prefixed with rtk.
- id: G-04
  symptom_ref: F-04
  component_ref: RTK CLI
  root_cause: Historical savings figures do not match the current workload or installation.
  repair_entry_point: rtk gain measurement
  change_pattern: Replace assumptions with the current measured output; do not tune configuration from the source alone.
  rollback_procedure: None — measurement is read-only.
  integrity_check: Any reported savings cite the current measurement.
```

## §H. Evolve

### §H.1 Invariants

- RTK sits between supported agent shell calls and the operating system to
  reduce output before it enters agent context.
- CC and AG integrations are hook-based; MP integration is instruction-based.
- Vulcan's MCP JSON output path is not intercepted.
- Telemetry is source-documented as disabled.
- Full-output tee recovery is source-documented for failures only.
- A historical version or savings percentage is not a current default or result.

### §H.2 BREAKING predicates

Unknown. The source does not define a BREAKING change classification.

### §H.3 REVIEW predicates

Unknown. The source does not define a REVIEW change classification.

### §H.4 SAFE predicates

Unknown. The source does not define a SAFE change classification.

### §H.5 Boundary definitions

#### module

The RTK binary, local configuration, CC and AG hooks, MP instruction files, and
failure-only tee directory.

#### public contract

The source describes CLI command forms but defines no compatibility guarantee.
The public contract is Unknown beyond those recorded forms.

#### runtime dependency

The source names Titan-1, Homebrew, the local shell, and the three agent
configuration systems. Credential requirements are Unknown.

#### config default

The recorded local configuration disables telemetry and enables failure-only
tee recovery with 50 retained files. Whether these are RTK product defaults is
Unknown.

### §H.6 Adjudication

Unknown. The source contains no change-class adjudication procedure.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Verify the currently installed RTK version without assuming the historical value.
    expected_answers:
      - kind: tool_call
        tool: rtk --version
        argument_keys: []
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: Measure recent missed optimization opportunities.
    expected_answers:
      - kind: tool_call
        tool: rtk discover
        argument_keys: [since]
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Update RTK through the source-supported package path.
    expected_answers:
      - kind: tool_call
        tool: brew upgrade
        argument_values: {package: rtk}
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: CC commands are no longer compressed after a hook edit.
    expected_answers:
      - kind: human_action
        verb: verify
        object: CC hook state and restart
        target: source-listed integration
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-02]
    scenario: A failed command output is too compressed to diagnose.
    expected_answers:
      - kind: human_action
        verb: read
        object: full failure output
        target: source-listed tee directory
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: MP repeatedly omits the RTK prefix.
    expected_answers:
      - kind: human_action
        verb: inspect
        object: Codex instruction files
        target: ~/.codex/AGENTS.md and ~/.codex/RTK.md
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-02]
    scenario: The compressed failure lacks one required diagnostic line.
    expected_answers:
      - kind: human_action
        verb: recover
        object: full output without global disablement
        target: tee file or tracked passthrough
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-04]
    scenario: The historical savings percentage does not match this week's commands.
    expected_answers:
      - kind: human_action
        verb: replace
        object: assumption with current measurement
        target: reported savings
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A proposal changes RTK integration architecture.
    expected_answers:
      - kind: classification
        label: Unknown because the source defines no BREAKING predicate
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H.4]
    scenario: A proposal adds a new command exclusion.
    expected_answers:
      - kind: classification
        label: Unknown because the source defines no SAFE predicate
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [E-02, F-04]
    scenario: Reported token savings differ sharply from the inherited estimate.
    expected_answers:
      - kind: human_action
        verb: measure
        object: current like-for-like savings
        target: rtk gain output
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1389
last_refresh_commit: 5f968f167661dcac669dd42910037e05a50221ed
last_refresh_date: 2026-07-29T00:00:00Z
owner_agent: max
refresh_triggers:
  - RTK version or package path changes.
  - Any source-listed agent integration path changes.
  - Telemetry, tee, or command-exclusion configuration changes.
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
  before: 573
  after: 2200
  pct: 283.94
```
