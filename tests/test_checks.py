from __future__ import annotations

from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR
from runbook_tools.lint import CheckContext
from runbook_tools.lint.checks import (
    check_01_sections_present_and_ordered,
    check_02_agent_forms_present,
    check_03_a_j_owner_agent_consistency,
    check_04_a_k0_linter_version_consistency,
    check_05_status_values,
    check_06_backing_code,
    check_07_last_verified_warn,
    check_08_repair_ref_resolves,
    check_09_symptom_ref_resolves,
    check_10_component_ref_resolves,
)
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter


def test_check_01_sections_present_and_ordered() -> None:
    conformant = _run_check(check_01_sections_present_and_ordered, "conformant.md")
    missing = _run_check(check_01_sections_present_and_ordered, "missing_section_g.md")
    out_of_order = _run_check(check_01_sections_present_and_ordered, "out_of_order.md")

    assert conformant == []
    assert any(f.severity == "FAIL" and f.message == "missing §G" for f in missing)
    assert any(f.severity == "FAIL" and "§G appears out of order" in f.message for f in out_of_order)


def test_check_02_agent_forms_present() -> None:
    conformant = _run_check(check_02_agent_forms_present, "conformant.md")
    bad_header = _run_check(check_02_agent_forms_present, "bad_b_header.md")

    assert conformant == []
    assert any(f.severity == "FAIL" and "Backing_Code" in f.message for f in bad_header)


def test_check_03_a_j_owner_agent_consistency() -> None:
    findings = _run_check(check_03_a_j_owner_agent_consistency, "a_j_owner_drift.md")

    assert any(f.severity == "FAIL" and "owner_agent" in f.message for f in findings)


def test_check_04_a_k0_linter_version_consistency() -> None:
    findings = _run_check(check_04_a_k0_linter_version_consistency, "a_k0_version_drift.md")

    assert any(f.severity == "FAIL" and "linter_version" in f.message for f in findings)


def test_check_05_status_values() -> None:
    findings = _run_check(check_05_status_values, "bad_status.md")

    assert any(f.severity == "FAIL" and "WORKING" in f.message for f in findings)


def test_check_06_backing_code() -> None:
    findings = _run_check(check_06_backing_code, "empty_backing_on_shipped.md")

    assert any(f.severity == "FAIL" and "Backing Code" in f.message for f in findings)


def test_check_07_last_verified_warn() -> None:
    findings = _run_check(check_07_last_verified_warn, "stale_last_verified.md")

    assert any(f.severity == "WARN" and "Last Verified" in f.message for f in findings)
    assert not any(f.severity == "FAIL" for f in findings)


def test_check_08_repair_ref_resolves() -> None:
    findings = _run_check(check_08_repair_ref_resolves, "dangling_repair_ref.md")

    assert any(f.severity == "FAIL" and 'Repair Ref "§G-99"' in f.message for f in findings)


def test_check_09_symptom_ref_resolves() -> None:
    findings = _run_check(check_09_symptom_ref_resolves, "dangling_symptom_ref.md")

    assert any(f.severity == "FAIL" and 'symptom_ref "F-99"' in f.message for f in findings)


def test_check_10_component_ref_resolves() -> None:
    findings = _run_check(check_10_component_ref_resolves, "dangling_component_ref.md")

    assert any(f.severity == "FAIL" and 'component_ref "GhostCLI"' in f.message for f in findings)


def _run_check(check_fn, fixture_name: str):
    markdown = (FIXTURES_DIR / fixture_name).read_text()
    sections = extract_sections(markdown)
    ctx = CheckContext(
        schemas_dir=SCHEMAS_DIR,
        readme_path=None,
        mode="strict",
        frontmatter=extract_yaml_frontmatter(markdown),
    )
    return check_fn(sections, ctx)
