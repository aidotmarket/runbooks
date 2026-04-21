---
system_name: <<SYSTEM_NAME:required>>
purpose_sentence: <<PURPOSE_SENTENCE:required>>
owner_agent: <<OWNER_AGENT:required>>
escalation_contact: <<ESCALATION_CONTACT:required>>
lifecycle_ref: §J
authoritative_scope: <<AUTHORITATIVE_SCOPE:required>>
linter_version: <<LINTER_VERSION:required>>
---

# <<TITLE:required>>

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| <<FEATURE_CAPABILITY:example>> | <<STATUS:example>> | <<BACKING_CODE:example>> | <<TEST_COVERAGE:example>> | <<LAST_VERIFIED:example>> |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| <<COMPONENT:example>> | <<COMPONENT_ENTRY_POINT:example>> | <<STATE_STORES:example>> | <<INTEGRATES_WITH:example>> | <<NOTES:example>> |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| <<AGENT:example>> | <<OPERATION:example>> | <<SKILL_TOOL:example>> | <<AUTH_SCOPE:example>> | <<COVERAGE_STATUS:example>> |

## §E. Operate

```yaml operate
- id: <<E_ID:example>>
  trigger: <<E_TRIGGER:example>>
  pre_conditions:
    - <<E_PRECONDITION:example>>
  tool_or_endpoint: <<E_TOOL_OR_ENDPOINT:example>>
  argument_sourcing:
    arg: <<E_ARGUMENT_SOURCING:example>>
  idempotency: <<E_IDEMPOTENCY:example>>
  expected_success:
    shape: <<E_SUCCESS_SHAPE:example>>
    verification: <<E_SUCCESS_VERIFICATION:example>>
  expected_failures:
    - signature: <<E_FAILURE_SIGNATURE:example>>
      cause: <<E_FAILURE_CAUSE:example>>
  next_step_success: <<E_NEXT_STEP_SUCCESS:example>>
  next_step_failure: <<E_NEXT_STEP_FAILURE:example>>
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| <<F_ID:example>> | <<F_SYMPTOM:example>> | <<F_PROBABLE_CAUSES:example>> | <<F_VERIFICATION_PROCEDURE:example>> | <<F_REPAIR_REF:example>> | <<F_CONFIDENCE:example>> |

## §G. Repair

```yaml repair
- id: <<G_ID:example>>
  symptom_ref: <<G_SYMPTOM_REF:example>>
  component_ref: <<G_COMPONENT_REF:example>>
  root_cause: <<G_ROOT_CAUSE:example>>
  repair_entry_point: <<G_REPAIR_ENTRY_POINT:example>>
  change_pattern: <<G_CHANGE_PATTERN:example>>
  rollback_procedure: <<G_ROLLBACK_PROCEDURE:example>>
  integrity_check: <<G_INTEGRITY_CHECK:example>>
```

## §H. Evolve

### §H.1 Invariants

- <<H1_INVARIANT:example>>

### §H.2 BREAKING predicates

- <<H2_BREAKING_PREDICATE:example>>

### §H.3 REVIEW predicates

- <<H3_REVIEW_PREDICATE:example>>

### §H.4 SAFE predicates

- <<H4_SAFE_PREDICATE:example>>

### §H.5 Boundary definitions

#### module

<<H5_MODULE:example>>

#### public contract

<<H5_PUBLIC_CONTRACT:example>>

#### runtime dependency

<<H5_RUNTIME_DEPENDENCY:example>>

#### config default

<<H5_CONFIG_DEFAULT:example>>

### §H.6 Adjudication

<<H6_ADJUDICATION:example>>

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: <<I_ID:example>>
    type: <<I_TYPE:example>>
    refs:
      - <<I_REF:example>>
    scenario: <<I_SCENARIO:example>>
    expected_answers:
      - kind: <<I_EXPECTED_ANSWER_KIND:example>>
        tool: <<I_EXPECTED_ANSWER_TOOL:example>>
        argument_keys:
          - <<I_EXPECTED_ANSWER_ARGUMENT_KEY:example>>
    weight: <<I_WEIGHT:example>>
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: <<LAST_REFRESH_SESSION:required>>
last_refresh_commit: <<LAST_REFRESH_COMMIT:required>>
last_refresh_date: <<LAST_REFRESH_DATE:required>>
owner_agent: <<J_OWNER_AGENT:required>>
refresh_triggers:
  - <<REFRESH_TRIGGER:required>>
scheduled_cadence: <<SCHEDULED_CADENCE:required>>
last_harness_pass_rate: <<LAST_HARNESS_PASS_RATE:required>>
last_harness_date: <<LAST_HARNESS_DATE:required>>
first_staleness_detected_at: <<FIRST_STALENESS_DETECTED_AT:required>>
```

## §K. Conformance

```yaml conformance
linter_version: <<K_LINTER_VERSION:required>>
last_lint_run: <<LAST_LINT_RUN:required>>
last_lint_result: <<LAST_LINT_RESULT:required>>
trace_matrix_path: <<TRACE_MATRIX_PATH:required>>
word_count_delta: <<WORD_COUNT_DELTA:required>>
```
