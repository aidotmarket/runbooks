from __future__ import annotations

import pytest

from runbook_tools.lint.forms import (
    parse_gfm_table,
    validate_a,
    validate_b,
    validate_e,
    validate_h,
    validate_i,
    validate_j,
    validate_k,
)
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter
from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR


def test_validate_a_on_conformant() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()

    findings = validate_a(extract_yaml_frontmatter(markdown), SCHEMAS_DIR)

    assert findings == []


def test_validate_a_missing_required_field() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace("escalation_contact: max\n", "")

    findings = validate_a(extract_yaml_frontmatter(markdown), SCHEMAS_DIR)

    assert any(f.severity == "FAIL" and "escalation_contact" in f.message for f in findings)


def test_validate_b_header_row_parsed() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_b = next(section for section in extract_sections(markdown) if section.letter == "B")

    headers, rows = parse_gfm_table(section_b.ast_subtree)

    assert len(headers) == 5
    assert headers == [
        "Feature/Capability",
        "Status",
        "Backing Code",
        "Test Coverage",
        "Last Verified",
    ]
    assert len(rows) == 3


def test_validate_b_unknown_status() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace("| SHIPPED |", "| WORKING |", 1)
    section_b = next(section for section in extract_sections(markdown) if section.letter == "B")

    findings = validate_b(section_b, SCHEMAS_DIR)

    assert any(f.severity == "FAIL" and "WORKING" in f.message for f in findings)


def test_validate_e_on_conformant() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_e = next(section for section in extract_sections(markdown) if section.letter == "E")

    findings = validate_e(section_e, SCHEMAS_DIR)

    assert findings == []
    assert markdown.count("- id: E-") == 3


def test_validate_e_missing_idempotency() -> None:
    missing_idempotency = (FIXTURES_DIR / "conformant.md").read_text().replace("  idempotency: IDEMPOTENT\n", "", 1)
    section_e_missing = next(section for section in extract_sections(missing_idempotency) if section.letter == "E")

    missing_key = (FIXTURES_DIR / "conformant.md").read_text().replace("  idempotency_key: sync-audit-prod\n", "")
    section_e_missing_key = next(section for section in extract_sections(missing_key) if section.letter == "E")

    findings_missing = validate_e(section_e_missing, SCHEMAS_DIR)
    findings_missing_key = validate_e(section_e_missing_key, SCHEMAS_DIR)

    assert any(f.severity == "FAIL" and "idempotency" in f.message for f in findings_missing)
    assert any(f.severity == "FAIL" and "idempotency_key" in f.message for f in findings_missing_key)


def test_validate_e_accepts_empty_set_without_forcing_operations() -> None:
    section_e = extract_sections("## §E. Operate\n\n```yaml operate\n[]\n```\n")[0]

    assert validate_e(section_e, SCHEMAS_DIR) == []


def test_validate_h_all_six_subsections_present() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_h = next(section for section in extract_sections(markdown) if section.letter == "H")

    findings = validate_h(section_h, SCHEMAS_DIR)

    assert findings == []


def test_validate_h_missing_h5_subsubheading() -> None:
    markdown = (FIXTURES_DIR / "missing_h5_config_default.md").read_text()
    section_h = next(section for section in extract_sections(markdown) if section.letter == "H")

    findings = validate_h(section_h, SCHEMAS_DIR)

    assert any(f.severity == "FAIL" and "§H.5" in f.message for f in findings)


def test_validate_h_schema_failure_missing_h6() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    start = markdown.index("### §H.6 Adjudication")
    end = markdown.index("## §I. Acceptance Criteria")
    markdown = markdown[:start] + markdown[end:]
    section_h = next(section for section in extract_sections(markdown) if section.letter == "H")

    findings = validate_h(section_h, SCHEMAS_DIR)

    assert any(f.severity == "FAIL" and "'h6' is a required property" in f.message for f in findings)


def test_validate_h_schema_success_conformant_payload() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_h = next(section for section in extract_sections(markdown) if section.letter == "H")

    findings = validate_h(section_h, SCHEMAS_DIR)

    assert not any("'h" in f.message and "required property" in f.message for f in findings)


def test_validate_i_accepts_empty_set_without_forcing_filler() -> None:
    markdown = """## §I. Acceptance Criteria

```yaml acceptance
scenario_set: []
```
"""
    section_i = extract_sections(markdown)[0]

    assert validate_i(section_i, SCHEMAS_DIR) == []


@pytest.mark.parametrize(
    ("answer", "missing_field"),
    [
        ("kind: tool_call\n        tool: council_request", "argument_keys"),
        ("kind: human_action\n        action: inspect it", "verb"),
        ("kind: classification\n        verdict: SAFE", "label"),
    ],
)
def test_validate_i_requires_meaningful_fields_for_each_answer_kind(
    answer: str,
    missing_field: str,
) -> None:
    markdown = f"""## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A concrete current condition needs one safe documented response.
    expected_answers:
      - {answer}
```
"""
    section_i = extract_sections(markdown)[0]

    findings = validate_i(section_i, SCHEMAS_DIR)

    assert any(missing_field in finding.message for finding in findings)


def test_validate_i_allows_verified_argument_free_tool_contract() -> None:
    markdown = """## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A concrete current condition needs one safe documented response.
    expected_answers:
      - kind: tool_call
        tool: read_current_status
        argument_keys: []
```
"""
    section_i = extract_sections(markdown)[0]

    assert validate_i(section_i, SCHEMAS_DIR) == []


def test_validate_k_retrofit_absent() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_k = next(section for section in extract_sections(markdown) if section.letter == "K")

    findings = validate_k(section_k, SCHEMAS_DIR)

    assert findings == []


def test_validate_j_accepts_pending_harness_tooling() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "last_harness_pass_rate: 1.0\n",
        "last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)\n",
        1,
    )
    section_j = next(section for section in extract_sections(markdown) if section.letter == "J")

    findings = validate_j(section_j, SCHEMAS_DIR)

    assert findings == []


def test_validate_j_allows_legacy_fields_to_be_omitted_but_requires_harness_pair() -> None:
    markdown = (
        (FIXTURES_DIR / "conformant.md")
        .read_text()
        .replace("last_harness_pass_rate: 1.0\n", "", 1)
        .replace("last_harness_date: 2026-04-20T02:00:00Z\n", "", 1)
        .replace("first_staleness_detected_at: null\n", "", 1)
    )
    section_j = next(section for section in extract_sections(markdown) if section.letter == "J")
    assert validate_j(section_j, SCHEMAS_DIR) == []

    one_sided = markdown.replace(
        "scheduled_cadence: 90d\n",
        "scheduled_cadence: 90d\nlast_harness_pass_rate: 1.0\n",
        1,
    )
    section_j = next(section for section in extract_sections(one_sided) if section.letter == "J")
    assert any("last_harness_date" in finding.message for finding in validate_j(section_j, SCHEMAS_DIR))


def test_validate_j_rejects_malformed_datetime_without_optional_format_package() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "last_refresh_date: 2026-04-21T17:30:00Z",
        "last_refresh_date: definitely-not-a-date",
        1,
    )
    section_j = next(
        section for section in extract_sections(markdown) if section.letter == "J"
    )

    findings = validate_j(section_j, SCHEMAS_DIR)

    assert any(
        "last_refresh_date" in finding.message and "date-time" in finding.message
        for finding in findings
    )


def test_validate_k_retrofit_false() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "```yaml conformance\nlinter_version: 1.0.0\n",
        "```yaml conformance\nlinter_version: 1.0.0\nretrofit: false\n",
        1,
    )
    section_k = next(section for section in extract_sections(markdown) if section.letter == "K")

    findings = validate_k(section_k, SCHEMAS_DIR)

    assert findings == []


def test_validate_k_allows_legacy_self_certification_fields_to_be_omitted() -> None:
    markdown = (
        (FIXTURES_DIR / "conformant.md")
        .read_text()
        .replace("last_lint_run: S487 / 2026-04-21T17:35:00Z\n", "", 1)
        .replace("last_lint_result: PASS\n", "", 1)
    )
    section_k = next(section for section in extract_sections(markdown) if section.letter == "K")

    assert validate_k(section_k, SCHEMAS_DIR) == []


def test_validate_k_retrofit_true_with_nulls() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "```yaml conformance\nlinter_version: 1.0.0\n",
        "```yaml conformance\nlinter_version: 1.0.0\nretrofit: true\n",
        1,
    )
    section_k = next(section for section in extract_sections(markdown) if section.letter == "K")

    findings = validate_k(section_k, SCHEMAS_DIR)

    assert any(f.severity == "FAIL" and "trace_matrix_path" in f.message for f in findings)
