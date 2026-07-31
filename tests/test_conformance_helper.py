from __future__ import annotations

import pytest

from runbook_tools.lint.conformance import structural_conformance_failures
from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR


def test_structural_conformance_helper_accepts_valid_markdown() -> None:
    failures = structural_conformance_failures(
        (FIXTURES_DIR / "conformant.md").read_text(),
        SCHEMAS_DIR,
    )

    assert failures == []


def test_structural_conformance_helper_rejects_missing_and_duplicate_sections() -> None:
    missing = structural_conformance_failures(
        (FIXTURES_DIR / "missing_section_g.md").read_text(),
        SCHEMAS_DIR,
    )
    conformant = (FIXTURES_DIR / "conformant.md").read_text()
    duplicate = structural_conformance_failures(
        conformant.replace(
            "## §F. Isolate",
            "## §E. Duplicate\n\nDuplicate.\n\n## §F. Isolate",
            1,
        ),
        SCHEMAS_DIR,
    )

    assert any(finding.message == "missing §G" for finding in missing)
    assert any("§E appears 2 times" in finding.message for finding in duplicate)


def test_structural_conformance_helper_excludes_file_clock_escalation() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "first_staleness_detected_at: null",
        "first_staleness_detected_at: 2099-01-01T00:00:00Z",
    )

    assert structural_conformance_failures(markdown, SCHEMAS_DIR) == []


def test_fenced_a_to_k_headings_and_forms_cannot_satisfy_conformance() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    markdown = markdown.replace(
        "## §A. Header",
        "````markdown\n## §A. Header",
        1,
    ).replace(
        "## §C. Architecture & Interactions",
        "````\n\n## §C. Architecture & Interactions",
        1,
    ).replace(
        "## §D. Agent Capability Map",
        "````markdown\n## §D. Agent Capability Map",
        1,
    )
    markdown = markdown.rstrip() + "\n````\n"

    failures = structural_conformance_failures(markdown, SCHEMAS_DIR)

    messages = {finding.message for finding in failures}
    assert "missing §A" in messages
    assert "missing §B" in messages
    assert "missing §D" in messages
    assert "missing §K" in messages


@pytest.mark.parametrize("outer_fence", ["````", "~~~~"])
@pytest.mark.parametrize(
    ("letter", "marker"),
    [
        ("E", "operate"),
        ("G", "repair"),
        ("I", "acceptance"),
        ("J", "lifecycle"),
        ("K", "conformance"),
    ],
)
def test_yaml_form_nested_in_outer_example_cannot_satisfy_conformance(
    outer_fence: str,
    letter: str,
    marker: str,
) -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    opening = f"```yaml {marker}\n"
    start = markdown.index(opening)
    end = markdown.index("\n```", start) + len("\n```")
    form = markdown[start:end]
    markdown = (
        markdown[:start]
        + f"{outer_fence}markdown\n{form}\n{outer_fence}"
        + markdown[end:]
    )

    failures = structural_conformance_failures(markdown, SCHEMAS_DIR)

    assert any(
        finding.message == f"§{letter} must contain a ```yaml {marker}``` block"
        for finding in failures
    )


def test_fenced_substantive_h_bodies_cannot_fill_empty_rendered_headings() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    start = markdown.index("### §H.1 Invariants")
    end = markdown.index("## §I. Acceptance Criteria")
    historical_example = markdown[start:end].rstrip()
    empty_current = """### §H.1 Invariants

### §H.2 BREAKING predicates

### §H.3 REVIEW predicates

### §H.4 SAFE predicates

### §H.5 Boundary definitions

#### module

#### public contract

#### runtime dependency

#### config default

### §H.6 Adjudication

"""
    markdown = (
        markdown[:start]
        + "````markdown\n"
        + historical_example
        + "\n````\n\n"
        + empty_current
        + markdown[end:]
    )

    failures = structural_conformance_failures(markdown, SCHEMAS_DIR)

    assert any(
        "'h1' is a required property" in finding.message
        or "None is not of type 'string'" in finding.message
        for finding in failures
    )


@pytest.mark.parametrize(
    ("letter", "marker", "escaped_row"),
    [
        ("E", "operate", "- id: E-99\n  trigger: escaped operation"),
        ("G", "repair", "- id: G-99\n  root_cause: escaped repair"),
        ("I", "acceptance", "  - id: I-99\n    type: operate"),
        ("J", "lifecycle", "last_refresh_date: 2999-01-01T00:00:00Z"),
        ("K", "conformance", "linter_version: 999.0.0"),
    ],
)
def test_form_shaped_content_outside_typed_fence_is_rejected(
    letter: str,
    marker: str,
    escaped_row: str,
) -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    opening = f"```yaml {marker}\n"
    start = markdown.index(opening)
    end = markdown.index("\n```", start) + len("\n```")
    markdown = markdown[:end] + f"\n\n{escaped_row}" + markdown[end:]

    failures = structural_conformance_failures(markdown, SCHEMAS_DIR)

    assert any(
        finding.message
        == (
            f"§{letter} form-shaped content must be inside "
            f"a rendered ```yaml {marker}``` block"
        )
        for finding in failures
    )


def test_form_shaped_content_inside_non_typed_outer_example_is_not_active() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    marker = "```yaml operate\n"
    start = markdown.index(marker)
    end = markdown.index("\n```", start) + len("\n```")
    example = "````text\n- id: E-99\n  trigger: example only\n````"
    markdown = markdown[:end] + f"\n\n{example}" + markdown[end:]

    failures = structural_conformance_failures(markdown, SCHEMAS_DIR)

    assert not any("form-shaped content" in finding.message for finding in failures)
