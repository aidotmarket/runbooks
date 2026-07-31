from __future__ import annotations

import re
from dataclasses import dataclass

from runbook_tools.catalog.model import KEBAB_CASE_RE

HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<text>.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
ANCHOR_RE = re.compile(
    r'^\s*<a id="rb-section-(?P<section_id>[a-z0-9]+(?:-[a-z0-9]+)*)"></a>\s*$'
)


@dataclass(frozen=True, slots=True)
class MarkdownSection:
    heading: str
    level: int
    heading_line: int
    end_line: int
    direct_end_line: int
    text: str
    direct_text: str
    adjacent_anchor_id: str | None


@dataclass(frozen=True, slots=True)
class MarkdownDocument:
    sections: tuple[MarkdownSection, ...]
    anchors: tuple[tuple[int, str], ...]


def parse_markdown_document(markdown: str) -> MarkdownDocument:
    """Parse citable headings and stable anchors while ignoring fenced examples."""

    lines = markdown.splitlines()
    headings: list[tuple[int, int, str, str | None]] = []
    anchors: list[tuple[int, str]] = []
    fence: str | None = None
    for index, line in enumerate(lines):
        fence_match = FENCE_RE.match(line)
        if fence_match is not None:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is not None:
            continue

        anchor_match = ANCHOR_RE.match(line)
        if anchor_match is not None:
            anchors.append((index + 1, anchor_match.group("section_id")))
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match is None:
            continue
        adjacent_anchor = ANCHOR_RE.match(lines[index - 1]) if index > 0 else None
        headings.append(
            (
                index,
                len(heading_match.group("marks")),
                heading_match.group("text").strip().rstrip("#").rstrip(),
                adjacent_anchor.group("section_id")
                if adjacent_anchor is not None
                else None,
            )
        )

    sections: list[MarkdownSection] = []
    for position, (start, level, heading, adjacent_anchor_id) in enumerate(headings):
        direct_end = (
            headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        )
        end = len(lines)
        for next_start, next_level, _, _ in headings[position + 1 :]:
            if next_level <= level:
                end = next_start
                break
        sections.append(
            MarkdownSection(
                heading=heading,
                level=level,
                heading_line=start + 1,
                end_line=end,
                direct_end_line=direct_end,
                text="\n".join(lines[start:end]).strip(),
                direct_text="\n".join(lines[start:direct_end]).strip(),
                adjacent_anchor_id=adjacent_anchor_id,
            )
        )
    return MarkdownDocument(sections=tuple(sections), anchors=tuple(anchors))


def declared_section_errors(
    markdown: str,
    path: str,
    rows: list[tuple[str, str | None]],
) -> list[str]:
    """Validate display headings and any opt-in stable identity declarations."""

    document = parse_markdown_document(markdown)
    headings = {section.heading for section in document.sections}
    errors = [
        f"{path}: dangling section {section!r}"
        for section, _ in rows
        if section not in headings
    ]

    rows_by_heading: dict[str, list[str | None]] = {}
    headings_by_id: dict[str, set[str]] = {}
    for section, section_id in rows:
        rows_by_heading.setdefault(section, []).append(section_id)
        if section_id is not None:
            if KEBAB_CASE_RE.fullmatch(section_id) is None:
                errors.append(
                    f"{path}: section_id {section_id!r} must be lowercase kebab-case"
                )
                continue
            headings_by_id.setdefault(section_id, set()).add(section)

    for section_id, declared_headings in headings_by_id.items():
        if len(declared_headings) > 1:
            errors.append(
                f"{path}: section_id {section_id!r} maps to conflicting headings: "
                + ", ".join(repr(value) for value in sorted(declared_headings))
            )

    for section, declared_ids in rows_by_heading.items():
        explicit_ids = {value for value in declared_ids if value is not None}
        if explicit_ids and any(value is None for value in declared_ids):
            errors.append(
                f"{path}: heading {section!r} mixes stable and legacy section identity"
            )
            continue
        if len(explicit_ids) > 1:
            errors.append(
                f"{path}: heading {section!r} has multiple section_ids: "
                + ", ".join(sorted(explicit_ids))
            )
            continue
        if not explicit_ids:
            continue

        section_id = next(iter(explicit_ids))
        occurrences = [
            line_number
            for line_number, found_id in document.anchors
            if found_id == section_id
        ]
        if not occurrences:
            errors.append(
                f"{path}: section_id {section_id!r} is missing "
                f"<a id=\"rb-section-{section_id}\"></a>"
            )
            continue
        if len(occurrences) > 1:
            errors.append(f"{path}: duplicate section anchor {section_id!r}")
            continue
        matches = [
            candidate
            for candidate in document.sections
            if candidate.heading == section
            and candidate.adjacent_anchor_id == section_id
        ]
        if len(matches) != 1:
            errors.append(
                f"{path}:{occurrences[0]}: section anchor {section_id!r} must "
                f"immediately precede heading {section!r}"
            )
    return errors
