from __future__ import annotations

from tests.conftest import FIXTURES_DIR
from runbook_tools.parser.sections import (
    extract_fenced_yaml_block,
    extract_sections,
    extract_yaml_frontmatter,
)


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
