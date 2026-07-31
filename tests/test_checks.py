from __future__ import annotations

from datetime import UTC, datetime

from runbook_tools.lint import CheckContext
from runbook_tools.lint.checks import (
    ALL_CHECKS,
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
    check_14_lifecycle_fields,
    check_15_current_staleness,
    check_16_linter_version_compat,
    check_17_conformance_fields,
    check_18_retrofit_fields,
    check_19_header_required_fields,
    check_20_b_exact_columns,
    check_22_i_example_identity_and_refs,
    check_23_e_operation_ids_unique,
    check_24_no_unresolved_placeholders,
)
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter
from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR


def test_check_01_sections_present_and_ordered() -> None:
    conformant = _run_check(check_01_sections_present_and_ordered, "conformant.md")
    missing = _run_check(check_01_sections_present_and_ordered, "missing_section_g.md")
    out_of_order = _run_check(check_01_sections_present_and_ordered, "out_of_order.md")

    assert conformant == []
    assert any(f.severity == "FAIL" and f.message == "missing §G" for f in missing)
    assert any(f.severity == "FAIL" and "§G appears out of order" in f.message for f in out_of_order)


def test_check_01_rejects_duplicate_current_sections() -> None:
    findings = _run_check(
        check_01_sections_present_and_ordered,
        "conformant.md",
        transform=lambda markdown: markdown.replace(
            "## §F. Isolate",
            "## §E. Duplicate\n\nDuplicate current content.\n\n## §F. Isolate",
            1,
        ),
    )

    assert any(
        finding.severity == "FAIL"
        and "§E appears 2 times" in finding.message
        for finding in findings
    )


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


def test_check_07_uses_one_utc_calendar_age_boundary() -> None:
    def set_b_dates(markdown: str, value: str) -> str:
        for original in ("2026-04-20", "2026-04-19", "2026-04-18"):
            markdown = markdown.replace(f"| {original} |", f"| {value} |", 1)
        return markdown

    exactly_90 = _run_check(
        check_07_last_verified_warn,
        "conformant.md",
        now=datetime(2026, 7, 19, 23, 59, tzinfo=UTC),
        transform=lambda markdown: set_b_dates(markdown, "2026-04-20"),
    )
    expired_91 = _run_check(
        check_07_last_verified_warn,
        "conformant.md",
        now=datetime(2026, 7, 20, tzinfo=UTC),
        transform=lambda markdown: set_b_dates(markdown, "2026-04-20"),
    )

    assert exactly_90 == []
    assert len([finding for finding in expired_91 if finding.severity == "WARN"]) == 3
    assert all("91 days old" in finding.message for finding in expired_91)


def test_check_07_fails_impossible_and_future_dates() -> None:
    impossible = _run_check(
        check_07_last_verified_warn,
        "conformant.md",
        now=datetime(2026, 7, 31, tzinfo=UTC),
        transform=lambda markdown: markdown.replace(
            "| 2026-04-20 |", "| 2026-99-99 |", 1
        ),
    )
    future = _run_check(
        check_07_last_verified_warn,
        "conformant.md",
        now=datetime(2026, 7, 31, tzinfo=UTC),
        transform=lambda markdown: markdown.replace(
            "| 2026-04-20 |", "| 2026-08-01 |", 1
        ),
    )

    assert any(
        finding.severity == "FAIL" and "real YYYY-MM-DD" in finding.message
        for finding in impossible
    )
    assert any(
        finding.severity == "FAIL" and "in the future" in finding.message
        for finding in future
    )


def test_check_08_repair_ref_resolves() -> None:
    findings = _run_check(check_08_repair_ref_resolves, "dangling_repair_ref.md")

    assert any(f.severity == "FAIL" and 'Repair Ref "§G-99"' in f.message for f in findings)


def test_check_09_symptom_ref_resolves() -> None:
    findings = _run_check(check_09_symptom_ref_resolves, "dangling_symptom_ref.md")

    assert any(f.severity == "FAIL" and 'symptom_ref "F-99"' in f.message for f in findings)


def test_check_10_component_ref_resolves() -> None:
    findings = _run_check(check_10_component_ref_resolves, "dangling_component_ref.md")

    assert any(f.severity == "FAIL" and 'component_ref "GhostCLI"' in f.message for f in findings)


def test_retired_scenario_quota_and_weight_checks_are_not_registered() -> None:
    registered_names = {check.__name__ for check in ALL_CHECKS}

    assert "check_11_scenario_distribution" not in registered_names
    assert "check_12_weights_sum" not in registered_names
    assert "check_13_unequal_weights_justified" not in registered_names


def test_check_14_lifecycle_fields() -> None:
    markdown_without_legacy_fields = lambda markdown: markdown.replace(
        "last_harness_pass_rate: 1.0\n", "", 1
    ).replace(
        "last_harness_date: 2026-04-20T02:00:00Z\n", "", 1
    ).replace(
        "first_staleness_detected_at: null\n", "", 1
    )
    findings = _run_check(
        check_14_lifecycle_fields,
        "conformant.md",
        now=datetime(2026, 4, 22, tzinfo=UTC),
        transform=markdown_without_legacy_fields,
    )

    assert findings == []


def test_check_14_rejects_future_lifecycle_timestamps() -> None:
    now = datetime(2026, 4, 22, tzinfo=UTC)
    fields = [
        ("last_refresh_date", "last_refresh_date: 2026-04-21T17:30:00Z", "last_refresh_date: 2099-01-01T00:00:00Z"),
        ("last_harness_date", "last_harness_date: 2026-04-20T02:00:00Z", "last_harness_date: 2099-01-01T00:00:00Z"),
        ("first_staleness_detected_at", "first_staleness_detected_at: null", "first_staleness_detected_at: 2099-01-01T00:00:00Z"),
    ]
    for field, before, after in fields:
        findings = _run_check(
            check_14_lifecycle_fields,
            "conformant.md",
            now=now,
            transform=lambda markdown, before=before, after=after: markdown.replace(
                before, after, 1
            ),
        )
        assert any(
            finding.severity == "FAIL" and field in finding.message
            for finding in findings
        )


def test_check_15_reports_current_staleness_without_file_clock_escalation() -> None:
    without_clock = _run_check(
        check_15_current_staleness,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=UTC),
        git_head="ea70326",
    )
    recent_clock = _run_check(
        check_15_current_staleness,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=UTC),
        git_head="ea70326",
        transform=lambda markdown: markdown.replace(
            "first_staleness_detected_at: null",
            "first_staleness_detected_at: 2026-04-11T00:00:00Z",
        ),
    )
    old_clock = _run_check(
        check_15_current_staleness,
        "stale_commit_drift.md",
        now=datetime(2026, 4, 21, tzinfo=UTC),
        git_head="ea70326",
        transform=lambda markdown: markdown.replace(
            "first_staleness_detected_at: null",
            "first_staleness_detected_at: 2026-03-01T00:00:00Z",
        ),
    )
    current = _run_check(
        check_15_current_staleness,
        "conformant.md",
        now=datetime(2026, 4, 21, tzinfo=UTC),
        git_head="ea70326",
    )
    assert without_clock == recent_clock == old_clock
    assert len(without_clock) == 1
    assert without_clock[0].severity == "WARN"
    assert "commit_drift_60d" in without_clock[0].message
    assert "canonical server state" in without_clock[0].message
    assert current == []


def test_check_16_linter_version_compat(monkeypatch) -> None:
    same = _run_check(check_16_linter_version_compat, "conformant.md")
    monkeypatch.setattr("runbook_tools.lint.checks.LINTER_VERSION", "2.0.0")
    mismatch = _run_check(check_16_linter_version_compat, "conformant.md")

    assert same == []
    assert any(f.severity == "WARN" and "currently running 2.0.0" in f.message for f in mismatch)


def test_check_17_conformance_fields() -> None:
    findings = _run_check(check_17_conformance_fields, "missing_last_lint_run.md")

    assert findings == []


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


def test_check_22_rejects_duplicate_ids_and_dangling_local_refs() -> None:
    duplicate = _run_check(
        check_22_i_example_identity_and_refs,
        "conformant.md",
        transform=lambda markdown: markdown.replace("id: I-02", "id: I-01", 1),
    )
    dangling = _run_check(
        check_22_i_example_identity_and_refs,
        "conformant.md",
        transform=lambda markdown: markdown.replace("refs: [E-01]", "refs: [E-99]", 1),
    )

    assert any("I-01" in finding.message and "duplicated" in finding.message for finding in duplicate)
    assert any("E-99" in finding.message and "does not resolve" in finding.message for finding in dangling)


def test_check_22_resolves_section_refs_and_defers_valid_cross_file_targets() -> None:
    findings = _run_check(
        check_22_i_example_identity_and_refs,
        "conformant.md",
        transform=lambda markdown: markdown.replace(
            "refs: [E-01]",
            "refs: [E-01, §H.2, other-runbook:E-01, other-runbook:I-01]",
            1,
        ),
    )

    assert findings == []


def test_check_22_rejects_unsupported_cross_file_row_id_kinds() -> None:
    findings = _run_check(
        check_22_i_example_identity_and_refs,
        "conformant.md",
        transform=lambda markdown: markdown.replace(
            "refs: [E-01]",
            "refs: [E-01, other-runbook:A-01]",
            1,
        ),
    )

    assert any(
        "other-runbook:A-01" in finding.message
        and "invalid cross-file syntax" in finding.message
        for finding in findings
    )


def test_check_23_rejects_duplicate_e_operation_ids_and_allows_empty_e() -> None:
    duplicate = _run_check(
        check_23_e_operation_ids_unique,
        "conformant.md",
        transform=lambda markdown: markdown.replace("id: E-02", "id: E-01", 1),
    )
    empty = _run_check(
        check_23_e_operation_ids_unique,
        "conformant.md",
        transform=lambda markdown: markdown.replace(
            markdown[markdown.index("```yaml operate") : markdown.index("## §F. Isolate")],
            "```yaml operate\n[]\n```\n\n",
            1,
        ),
    )

    assert any("E-01" in finding.message and "duplicated" in finding.message for finding in duplicate)
    assert empty == []


def test_check_24_rejects_any_current_placeholder_kind_but_not_history() -> None:
    current = _run_check(
        check_24_no_unresolved_placeholders,
        "conformant.md",
        transform=lambda markdown: markdown + "\n<<E_TOOL:optional>>\n",
    )
    historical = _run_check(
        check_24_no_unresolved_placeholders,
        "conformant.md",
        transform=lambda markdown: (
            markdown
            + "\n<!-- catalog:historical -->\n"
            + "<<OLD_TOOL:optional>>\n"
            + "<!-- /catalog:historical -->\n"
        ),
    )

    assert any("<<E_TOOL:optional>>" in finding.message for finding in current)
    assert historical == []


def test_check_24_rejects_malformed_scaffold_tokens_without_matching_heredocs() -> None:
    for token in (
        "<<E_TOOL:required>",
        "<<E_TOOL:REQUIRED>",
        "<<E_TOOL-required>",
        "<E_TOOL:required>>",
    ):
        findings = _run_check(
            check_24_no_unresolved_placeholders,
            "conformant.md",
            transform=lambda markdown, token=token: markdown + f"\n{token}\n",
        )
        assert any(token in finding.message for finding in findings)

    heredocs = _run_check(
        check_24_no_unresolved_placeholders,
        "conformant.md",
        transform=lambda markdown: (
            markdown
            + "\n```sh\ncat <<'PY'\nprint('ok')\nPY\ncat <<END_JSON\n{}\nEND_JSON\n```\n"
        ),
    )
    assert heredocs == []


def _run_check(
    check_fn,
    fixture_name: str,
    *,
    now: datetime | None = None,
    git_head: str | None = None,
    readme_path=None,
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
        raw_markdown=markdown,
    )
    return check_fn(sections, ctx)
