from __future__ import annotations

from datetime import datetime, timezone

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
    check_11_scenario_distribution,
    check_12_weights_sum,
    check_13_unequal_weights_justified,
    check_14_lifecycle_fields,
    check_15_staleness_grace_workflow,
    check_16_linter_version_compat,
    check_17_conformance_fields,
    check_18_retrofit_fields,
    check_19_header_required_fields,
    check_20_b_exact_columns,
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


def test_check_11_scenario_distribution() -> None:
    too_few = _run_check(check_11_scenario_distribution, "scenarios_9.md")
    no_ambiguous = _run_check(check_11_scenario_distribution, "scenarios_no_ambiguous.md")

    assert any(f.severity == "FAIL" and "9 total scenarios" in f.message for f in too_few)
    assert any(f.severity == "FAIL" and "0 ambiguous scenarios" in f.message for f in no_ambiguous)


def test_check_12_weights_sum() -> None:
    findings = _run_check(check_12_weights_sum, "weights_sum_99.md")

    assert any(f.severity == "FAIL" and "sum to" in f.message for f in findings)


def test_check_13_unequal_weights_justified() -> None:
    findings = _run_check(check_13_unequal_weights_justified, "unequal_weights_unjustified.md")

    assert any(f.severity == "FAIL" and "Weight Justification" in f.message for f in findings)


def test_check_14_lifecycle_fields() -> None:
    findings = _run_check(check_14_lifecycle_fields, "missing_last_harness_date.md")

    assert any(f.severity == "FAIL" and "last_harness_date" in f.message for f in findings)


def test_check_15_staleness_emission_table() -> None:
    row1 = _run_check(
        check_15_staleness_grace_workflow,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=timezone.utc),
        git_head="ea70326",
    )
    row2 = _run_check(
        check_15_staleness_grace_workflow,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=timezone.utc),
        git_head="ea70326",
        transform=lambda markdown: markdown.replace(
            "first_staleness_detected_at: null",
            "first_staleness_detected_at: 2026-04-11T00:00:00Z",
        ),
    )
    row3 = _run_check(
        check_15_staleness_grace_workflow,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=timezone.utc),
        git_head="ea70326",
        transform=lambda markdown: markdown.replace(
            "first_staleness_detected_at: null",
            "first_staleness_detected_at: 2026-03-01T00:00:00Z",
        ),
    )
    row4 = _run_check(
        check_15_staleness_grace_workflow,
        "conformant.md",
        now=datetime(2026, 4, 21, tzinfo=timezone.utc),
        git_head="ea70326",
    )
    row5 = _run_check(
        check_15_staleness_grace_workflow,
        "conformant.md",
        now=datetime(2026, 4, 21, tzinfo=timezone.utc),
        git_head="ea70326",
        transform=lambda markdown: markdown.replace(
            "first_staleness_detected_at: null",
            "first_staleness_detected_at: 2026-04-01T00:00:00Z",
        ),
    )

    assert any(f.severity == "WARN" and "must be set to" in f.message for f in row1)
    assert any(f.severity == "WARN" and "grace clock at 10/30 days" in f.message for f in row2)
    assert any(f.severity == "FAIL" and "grace period exceeded" in f.message for f in row3)
    assert row4 == []
    assert any(f.severity == "WARN" and "requires clear to null" in f.message for f in row5)


def test_check_15_dual_path_pr_mode(tmp_path) -> None:
    source = FIXTURES_DIR / "stale_commit_drift.md"
    runbook_path = tmp_path / "runbook.md"
    original = source.read_text()
    runbook_path.write_text(original)

    findings = _run_check(
        check_15_staleness_grace_workflow,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=timezone.utc),
        git_head="ea70326",
        readme_path=runbook_path,
    )

    assert any(f.severity == "WARN" for f in findings)
    assert runbook_path.read_text() == original


def test_check_15_dual_path_nightly(tmp_path) -> None:
    runbook_path = tmp_path / "runbook.md"
    runbook_path.write_text((FIXTURES_DIR / "stale_commit_drift.md").read_text())

    findings = _run_check(
        check_15_staleness_grace_workflow,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=timezone.utc),
        git_head="ea70326",
        readme_path=runbook_path,
        update_lifecycle=True,
    )

    assert any(f.severity == "INFO" for f in findings)
    assert 'first_staleness_detected_at: "2026-04-21T00:00:00+00:00"' in runbook_path.read_text()


def test_check_16_linter_version_compat(monkeypatch) -> None:
    same = _run_check(check_16_linter_version_compat, "conformant.md")
    monkeypatch.setattr("runbook_tools.lint.checks.LINTER_VERSION", "2.0.0")
    mismatch = _run_check(check_16_linter_version_compat, "conformant.md")

    assert same == []
    assert any(f.severity == "WARN" and "currently running 2.0.0" in f.message for f in mismatch)


def test_check_17_conformance_fields() -> None:
    findings = _run_check(check_17_conformance_fields, "missing_last_lint_run.md")

    assert any(f.severity == "FAIL" and "last_lint_run" in f.message for f in findings)


def test_check_18_retrofit_fields() -> None:
    absent = _run_check(check_18_retrofit_fields, "conformant.md")
    explicit_false = _run_check(
        check_18_retrofit_fields,
        "conformant.md",
        transform=lambda markdown: markdown.replace(
            "```yaml conformance\nlinter_version: 1.0.0\n",
            "```yaml conformance\nlinter_version: 1.0.0\nretrofit: false\n",
            1,
        ),
    )
    true_with_nulls = _run_check(check_18_retrofit_fields, "retrofit_true_null_fields.md")

    assert absent == []
    assert explicit_false == []
    assert any(f.severity == "FAIL" and "retrofit=true requires non-null" in f.message for f in true_with_nulls)


def test_check_19_header_required_fields() -> None:
    missing = _run_check(check_19_header_required_fields, "missing_escalation_contact.md")
    placeholder = _run_check(check_19_header_required_fields, "scaffold_unfilled.md")

    assert any(f.severity == "FAIL" and "escalation_contact" in f.message for f in missing)
    assert any(f.severity == "FAIL" and "<<SYSTEM_NAME:required>>" in f.message for f in placeholder)


def test_check_20_b_exact_columns() -> None:
    findings = _run_check(check_20_b_exact_columns, "bad_b_header.md")

    assert any(f.severity == "FAIL" and "header row must match exactly" in f.message for f in findings)


def _run_check(
    check_fn,
    fixture_name: str,
    *,
    now: datetime | None = None,
    git_head: str | None = None,
    readme_path=None,
    update_lifecycle: bool = False,
    transform=None,
):
    markdown = (FIXTURES_DIR / fixture_name).read_text()
    if transform is not None:
        markdown = transform(markdown)
    sections = extract_sections(markdown)
    ctx = CheckContext(
        schemas_dir=SCHEMAS_DIR,
        readme_path=readme_path,
        mode="strict",
        frontmatter=extract_yaml_frontmatter(markdown),
        now=now,
        git_head=git_head,
        update_lifecycle=update_lifecycle,
    )
    return check_fn(sections, ctx)
