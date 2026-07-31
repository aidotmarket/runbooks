from __future__ import annotations

import pytest
import yaml

from runbook_tools.parser.sections import (
    extract_fenced_yaml_block,
    extract_sections,
    extract_yaml_frontmatter,
)
from runbook_tools.strict_yaml import strict_yaml_load
from tests.conftest import FIXTURES_DIR


def test_extract_yaml_frontmatter_present() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()

    frontmatter = extract_yaml_frontmatter(markdown)

    assert frontmatter is not None
    assert set(frontmatter) == {
        "system_name",
        "purpose_sentence",
        "owner_agent",
        "escalation_contact",
        "lifecycle_ref",
        "authoritative_scope",
        "linter_version",
    }


def test_extract_yaml_frontmatter_absent() -> None:
    markdown = "# Synthetic\n\n## §A. Header\n\nNo frontmatter here.\n"

    assert extract_yaml_frontmatter(markdown) is None


def test_duplicate_frontmatter_key_is_rejected_instead_of_last_key_wins() -> None:
    markdown = "---\nowner_agent: destructive-first\nowner_agent: safe-looking-last\n---\n"

    assert extract_yaml_frontmatter(markdown) is None


@pytest.mark.parametrize(
    "source",
    [
        "owner: &shared sysadmin\nowner_agent: *shared\n",
        "recursive: &loop [*loop]\n",
    ],
)
def test_strict_yaml_rejects_anchors_and_aliases(source: str) -> None:
    with pytest.raises(yaml.YAMLError, match="anchors and aliases are not allowed"):
        strict_yaml_load(source)


def test_aliased_frontmatter_is_rejected_cleanly() -> None:
    markdown = (
        "---\n"
        "owner_agent: &owner sysadmin\n"
        "escalation_contact: *owner\n"
        "---\n"
    )

    assert extract_yaml_frontmatter(markdown) is None


def test_extract_sections_finds_all_11() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()

    sections = extract_sections(markdown)

    assert len(sections) == 11
    assert [section.letter for section in sections] == list("ABCDEFGHIJK")


def test_extract_sections_section_letter_regex() -> None:
    markdown = """# Synthetic

## §E. Operate

Content.

## §E Operate

This heading is malformed and must not start a new section.

## §F. Isolate

More content.
"""

    sections = extract_sections(markdown)

    assert [section.letter for section in sections] == ["E", "F"]


def test_historical_sections_and_forms_do_not_satisfy_current_conformance() -> None:
    markdown = """# Synthetic

## §E. Operate

Current content.

<!-- catalog:historical -->
## §I. Acceptance Criteria

```yaml acceptance
- id: obsolete
```
<!-- /catalog:historical -->

## §J. Lifecycle

Current lifecycle.
"""

    sections = extract_sections(markdown)

    assert [section.letter for section in sections] == ["E", "J"]
    assert "obsolete" not in "\n".join(section.raw_markdown for section in sections)


@pytest.mark.parametrize(
    ("opening", "non_closing", "closing"),
    [
        ("````markdown", "```", "````"),
        ("~~~~markdown", "```", "~~~~"),
        ("````markdown", "~~~~", "````"),
        ("~~~markdown", "````", "~~~~"),
    ],
)
def test_fenced_heading_examples_do_not_create_sections_and_keep_line_mapping(
    opening: str,
    non_closing: str,
    closing: str,
) -> None:
    markdown = (
        "# Synthetic\n\n"
        f"{opening}\n"
        "## §A. Fenced Example\n\n"
        f"{non_closing}\n"
        "## §B. Still Fenced\n"
        f"{closing}\n\n"
        "## §C. Real Section\n\n"
        "Current content.\n"
    )
    expected_line = markdown.splitlines().index("## §C. Real Section") + 1

    sections = extract_sections(markdown)

    assert [section.letter for section in sections] == ["C"]
    assert sections[0].line_start == expected_line


@pytest.mark.parametrize("opening", ["```markdown", "~~~~markdown"])
def test_unclosed_fence_cannot_fabricate_sections(opening: str) -> None:
    markdown = f"# Synthetic\n\n{opening}\n## §A. Fenced Example\n"

    assert extract_sections(markdown) == []


def test_extract_fenced_yaml_block_operate() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_e = next(section for section in extract_sections(markdown) if section.letter == "E")

    operate = extract_fenced_yaml_block(section_e, "operate")

    assert isinstance(operate, list)
    assert len(operate) == 3


def test_extract_fenced_yaml_block_missing_returns_none() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    section_e = next(section for section in extract_sections(markdown) if section.letter == "E")

    assert extract_fenced_yaml_block(section_e, "missing") is None


@pytest.mark.parametrize(
    ("outer_open", "outer_close"),
    [
        ("````markdown", "````"),
        ("~~~~markdown", "~~~~"),
    ],
)
@pytest.mark.parametrize(
    "marker",
    ["operate", "repair", "acceptance", "lifecycle", "conformance"],
)
def test_nested_literal_yaml_form_is_not_a_rendered_form(
    outer_open: str,
    outer_close: str,
    marker: str,
) -> None:
    markdown = (
        "## §E. Operate\n\n"
        f"{outer_open}\n"
        f"```yaml {marker}\n"
        "forged: true\n"
        "```\n"
        f"{outer_close}\n"
    )
    section = extract_sections(markdown)[0]

    assert extract_fenced_yaml_block(section, marker) is None


def test_rendered_tilde_yaml_form_is_accepted() -> None:
    section = extract_sections(
        "## §E. Operate\n\n~~~yaml operate\n[]\n~~~~\n"
    )[0]

    assert extract_fenced_yaml_block(section, "operate") == []


@pytest.mark.parametrize("opening", ["```yaml operate", "~~~yaml operate"])
def test_unclosed_yaml_fence_does_not_satisfy_typed_form(opening: str) -> None:
    section = extract_sections(f"## §E. Operate\n\n{opening}\n[]\n")[0]

    assert extract_fenced_yaml_block(section, "operate") is None


def test_duplicate_fenced_yaml_key_is_rejected() -> None:
    markdown = """## §J. Lifecycle

```yaml lifecycle
owner_agent: destructive-first
owner_agent: safe-looking-last
```
"""
    section_j = extract_sections(markdown)[0]

    assert extract_fenced_yaml_block(section_j, "lifecycle") is None


def test_aliased_fenced_yaml_form_is_rejected_cleanly() -> None:
    markdown = """## §J. Lifecycle

```yaml lifecycle
owner_agent: &owner sysadmin
escalation_contact: *owner
```
"""
    section_j = extract_sections(markdown)[0]

    assert extract_fenced_yaml_block(section_j, "lifecycle") is None
