from __future__ import annotations

from dataclasses import dataclass
import re

import yaml

from runbook_tools.parser.markdown_ast import parse_markdown


SECTION_HEADING_RE = re.compile(r"^##\s+§([A-K])\.\s+(.+?)\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
FENCED_YAML_BLOCK_RE = r"^```yaml\s+{info_marker}\s*\n(.*?)\n```[ \t]*$"


@dataclass(slots=True)
class Section:
    letter: str
    heading: str
    raw_markdown: str
    ast_subtree: list
    line_start: int
    line_end: int


def extract_sections(markdown_text: str) -> list[Section]:
    sections: list[Section] = []
    matches = list(SECTION_HEADING_RE.finditer(markdown_text))
    lines = markdown_text.splitlines()

    for index, match in enumerate(matches):
        start_offset = match.start()
        end_offset = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        heading = match.group(0)
        raw_markdown = markdown_text[start_offset:end_offset].rstrip()
        line_start = markdown_text.count("\n", 0, start_offset) + 1
        section_line_count = len(raw_markdown.splitlines()) or 1
        line_end = line_start + section_line_count - 1

        sections.append(
            Section(
                letter=match.group(1),
                heading=heading,
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

    loaded = yaml.safe_load(match.group(1))
    return loaded if isinstance(loaded, dict) else None


def extract_fenced_yaml_block(section: Section, info_marker: str) -> dict | list | None:
    pattern = re.compile(
        FENCED_YAML_BLOCK_RE.format(info_marker=re.escape(info_marker)),
        re.MULTILINE | re.DOTALL,
    )
    matches = pattern.findall(section.raw_markdown)
    if not matches:
        return None

    parsed_blocks = [yaml.safe_load(block) for block in matches]
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
