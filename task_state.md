# Gate 3 R2 MP R1 Fixes — Complete

Baseline: 149 passed. Post-fix: 156 passed, 0 failed, 0 warnings.

## Findings → file:line → test citation

- **HIGH#1** — `runbook_tools/cli.py:_default_state_reader` now POSTs to `KOSKADEUX_MCP_URL` with `{"tool":"state_request","arguments":{"op":"read","key":<entity_key>}}`; raises `click.UsageError` on missing URL, transport failure, or malformed payload. Reader remains injectable for tests via `_resolve_external_source(..., state_reader=...)`.
  - Unit test: `tests/test_harness_external_mode.py::test_default_state_reader_raises_when_mcp_url_missing`
  - Unit test: `tests/test_harness_external_mode.py::test_default_state_reader_calls_mcp_gateway`
  - Integration test (@pytest.mark.integration): `tests/test_harness_external_mode.py::test_default_state_reader_surfaces_transport_failure_as_usage_error`

- **HIGH#2** — `runbook_tools/harness/dispatch.py:_call_with_timeout` replaced `with ThreadPoolExecutor(...) as executor:` (which blocked on `__exit__` waiting for the stuck worker) with manual construction + `finally: executor.shutdown(wait=False, cancel_futures=True)`. Wall-clock bound now honors `timeout_s`.
  - Regression test: `tests/test_harness_dispatch.py::test_dispatch_timeout_returns_within_wall_clock_bound` (stuck request sleeps 5s, timeout_s=0.1, asserts elapsed < 1.0s).

- **MEDIUM#1** — `runbook_tools/cli.py:_run_harness_loop` now catches `ScenarioSetConstraintError` and `ConfigurationError` and converts them to `click.UsageError` **only when external_mode=True**, so external-mode misconfiguration surfaces as exit 2 (usage error) per spec §4.3/AC.  Non-external exit-1 semantics untouched.
  - Test: `tests/test_harness_external_mode.py::test_external_mode_invalid_set_exits_2` — asserts CliRunner exit_code == 2 and error text on undersized external set.

- **MEDIUM#2** — 3 normal-mode mirror-check regression tests added to cover spec §5.3/AC7 gaps:
  - `tests/test_harness_external_mode.py::test_normal_mode_type_mismatch_fails` (YAML type ≠ §I type)
  - `tests/test_harness_external_mode.py::test_normal_mode_refs_mismatch_fails` (YAML refs ≠ §I refs)
  - `tests/test_harness_external_mode.py::test_normal_mode_runbook_name_mismatch_fails` (YAML.runbook ≠ runbook being validated)

- **LOW#1** — `specs/BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING-CI-AUDIT.md` created. Confirms nightly schedule + workflow_dispatch, no PR trigger, normal-harness-only invocation (no `--external-scenario-set` / `--external-scenarios-from-state`), scoped `contents: write` permissions, and declares external mode is not a PR-blocking lane per D5.

## Collateral

- `pyproject.toml` — registered `integration` pytest marker to silence PytestUnknownMarkWarning.
- `runbook_tools/cli.py` — added `import os` and `ScenarioSetConstraintError` import.
