from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import yaml

from runbook_tools.catalog.sections import (
    FENCE_CLOSE_RE,
    FENCE_OPEN_RE,
    parse_markdown_document,
)
from runbook_tools.parser.markdown_ast import parse_markdown
from runbook_tools.strict_yaml import strict_yaml_load

SECTION_HEADING_RE = re.compile(r"^§([A-K])\.\s+(.+?)\s*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


@dataclass(slots=True)
class Section:
    letter: str
    heading: str
    raw_markdown: str
    ast_subtree: list
    line_start: int
    line_end: int


def extract_sections(markdown_text: str) -> list[Section]:
    # Reuse the rendered-heading projection rather than rescanning active text.
    # Fenced code remains available inside a real section (forms are fenced YAML),
    # but heading-shaped examples inside backtick or tilde fences cannot create
    # conformance sections. Historical/comment projection also preserves source
    # line numbers through MarkdownSection.heading_line.
    document = parse_markdown_document(markdown_text)
    sections: list[Section] = []
    for candidate in document.sections:
        if candidate.level != 2:
            continue
        match = SECTION_HEADING_RE.fullmatch(candidate.heading)
        if match is None:
            continue
        raw_markdown = candidate.text.rstrip()
        line_start = candidate.heading_line
        section_line_count = len(raw_markdown.splitlines()) or 1
        line_end = line_start + section_line_count - 1

        sections.append(
            Section(
                letter=match.group(1),
                heading=f"## {candidate.heading}",
                raw_markdown=raw_markdown,
                ast_subtree=parse_markdown(raw_markdown),
                line_start=line_start,
                line_end=line_end,
            )
        )

    return sections


def extract_yaml_frontmatter(markdown_text: str) -> dict | None:
    match = FRONTMATTER_RE.match(markdown_text)
    if match is None:
        return None

    try:
        loaded = strict_yaml_load(match.group(1))
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def extract_fenced_yaml_block(section: Section, info_marker: str) -> dict | list | None:
    # Mistune emits only rendered code blocks as block_code tokens. A literal
    # inner ```yaml form inside a longer outer example therefore remains raw
    # text on the outer token and cannot masquerade as a current form.
    blocks = [
        token.get("raw")
        for token in section.ast_subtree
        if token.get("type") == "block_code"
        and token.get("style") == "fenced"
        and str(token.get("attrs", {}).get("info", "")).split()
        == ["yaml", info_marker]
        and isinstance(token.get("raw"), str)
    ]
    closed_count = _closed_fence_info_counts(section.raw_markdown)[
        ("yaml", info_marker)
    ]
    blocks = blocks[:closed_count]
    if not blocks:
        return None

    parsed_blocks = []
    for block in blocks:
        try:
            parsed_blocks.append(strict_yaml_load(block))
        except yaml.YAMLError:
            return None
    if all(isinstance(block, list) for block in parsed_blocks):
        combined: list = []
        for block in parsed_blocks:
            combined.extend(block)
        return combined

    if len(parsed_blocks) == 1:
        parsed = parsed_blocks[0]
        if isinstance(parsed, (dict, list)):
            return parsed

    return None


def _closed_fence_info_counts(markdown: str) -> Counter[tuple[str, ...]]:
    counts: Counter[tuple[str, ...]] = Counter()
    active: tuple[str, int, tuple[str, ...]] | None = None
    for line in markdown.splitlines():
        if active is not None:
            closing = FENCE_CLOSE_RE.fullmatch(line)
            if closing is None:
                continue
            marks = closing.group("marks")
            if marks[0] == active[0] and len(marks) >= active[1]:
                counts[active[2]] += 1
                active = None
            continue

        opening = FENCE_OPEN_RE.match(line)
        if opening is None:
            continue
        marks = opening.group("marks")
        info = opening.group("info")
        if marks[0] == "`" and "`" in info:
            continue
        active = (marks[0], len(marks), tuple(info.split()))
    return counts
