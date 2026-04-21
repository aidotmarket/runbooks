from __future__ import annotations

from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR
from runbook_tools.lint.forms import (
    parse_gfm_table,
    validate_a,
    validate_b,
    validate_e,
    validate_h,
    validate_k,
)
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter


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


def test_validate_k_retrofit_absent() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_k = next(section for section in extract_sections(markdown) if section.letter == "K")

    findings = validate_k(section_k, SCHEMAS_DIR)

    assert findings == []


def test_validate_k_retrofit_false() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "```yaml conformance\nlinter_version: 1.0.0\n",
        "```yaml conformance\nlinter_version: 1.0.0\nretrofit: false\n",
        1,
    )
    section_k = next(section for section in extract_sections(markdown) if section.letter == "K")

    findings = validate_k(section_k, SCHEMAS_DIR)

    assert findings == []


def test_validate_k_retrofit_true_with_nulls() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "```yaml conformance\nlinter_version: 1.0.0\n",
        "```yaml conformance\nlinter_version: 1.0.0\nretrofit: true\n",
        1,
    )
    section_k = next(section for section in extract_sections(markdown) if section.letter == "K")

    findings = validate_k(section_k, SCHEMAS_DIR)

    assert any(f.severity == "FAIL" and "trace_matrix_path" in f.message for f in findings)
