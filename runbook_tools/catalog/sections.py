from __future__ import annotations

import re
from dataclasses import dataclass

from runbook_tools.catalog.model import KEBAB_CASE_RE

HEADING_RE = re.compile(
    r"^ {0,3}(?P<marks>#{1,6})[ \t]+(?P<text>.+?)[ \t]*$"
)
FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<marks>`{3,}|~{3,})(?P<info>.*)$")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(?P<marks>`{3,}|~{3,})[ \t]*$")
ANCHOR_RE = re.compile(
    r'^<a id="rb-section-(?P<section_id>[a-z0-9]+(?:-[a-z0-9]+)*)"></a>[ \t]*$'
)
HISTORICAL_BEGIN = "<!-- catalog:historical -->"
HISTORICAL_END = "<!-- /catalog:historical -->"
ATX_CLOSING_RE = re.compile(r"[ \t]+#+[ \t]*$")
RAW_HTML_TYPE_1_RE = re.compile(
    r"^ {0,3}<(?P<tag>script|pre|style|textarea)(?:[ \t]|>|$)",
    re.IGNORECASE,
)
RAW_HTML_BLOCK_RE = re.compile(
    r"^ {0,3}</?(?P<tag>address|article|aside|base|basefont|blockquote|body|"
    r"caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|"
    r"figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|"
    r"html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|"
    r"option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|"
    r"title|tr|track|ul)(?:[ \t]|/?>|$)",
    re.IGNORECASE,
)
RAW_HTML_GENERIC_RE = re.compile(
    r"^ {0,3}</?[A-Za-z][A-Za-z0-9-]*"
    r"(?:[ \t]+[A-Za-z_:][A-Za-z0-9_.:-]*"
    r"(?:[ \t]*=[ \t]*(?:[^ \t\"'=<>`]+|'[^']*'|\"[^\"]*\"))?)*"
    r"[ \t]*/?>[ \t]*$"
)
PLACEHOLDER_BODY_RE = re.compile(
    r"^(?:tbd|todo\b.*|tbc|fixme\b.*|placeholder\b.*|unknown|n/?a|none|"
    r"coming\s+soon|not\s+yet\s+documented|pending\s+documentation)[.!? ]*$",
    re.IGNORECASE,
)


def legacy_heading_anchor(heading: str) -> str:
    """Project a rendered heading to the legacy generated-link fragment."""

    anchor = heading.casefold().replace("§", "")
    anchor = re.sub(r"[^\w\- ]", "", anchor)
    return re.sub(r"[ -]+", "-", anchor).strip("-")


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
    excluded_line_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MarkdownDocument:
    sections: tuple[MarkdownSection, ...]
    anchors: tuple[tuple[int, str], ...]
    active_text: str
    excluded_line_numbers: tuple[int, ...]
    structure_errors: tuple[str, ...]


def parse_markdown_document(markdown: str) -> MarkdownDocument:
    """Parse rendered headings and deliberately supported stable anchors.

    Stable anchors must begin in column zero. Fenced code and HTML comments are
    not rendered citation targets, so their apparent headings and anchors are
    ignored. Fence closing follows CommonMark's same-character, at-least-opening-
    length rule; this prevents an inner triple fence from closing a four-marker
    example.
    """

    lines = markdown.splitlines()
    searchable_lines = list(lines)
    headings: list[tuple[int, int, str, str | None]] = []
    anchors: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    in_html_comment = False
    html_comment_invalid = False
    html_comment_start_line = 0
    html_comment_indexes: list[int] = []
    raw_html: tuple[str, str] | None = None
    in_historical_span = False
    anchors_by_line: dict[int, str] = {}
    excluded_line_numbers: set[int] = set()
    structure_errors: list[str] = []
    for index, line in enumerate(lines):
        line_number = index + 1
        if fence is not None:
            if in_historical_span:
                searchable_lines[index] = ""
                excluded_line_numbers.add(line_number)
            closing = FENCE_CLOSE_RE.fullmatch(line)
            if closing is not None:
                marks = closing.group("marks")
                if marks[0] == fence[0] and len(marks) >= fence[1]:
                    fence = None
            continue

        if in_html_comment:
            html_comment_indexes.append(index)
            closing_position = line.find("-->")
            if closing_position < 0:
                if not html_comment_invalid:
                    searchable_lines[index] = ""
                    excluded_line_numbers.add(line_number)
                continue
            in_html_comment = False
            visible_suffix = bool(line[closing_position + 3 :].strip())
            if visible_suffix:
                structure_errors.append(
                    f"{line_number}: HTML comments must occupy whole lines"
                )
                html_comment_invalid = True
            if html_comment_invalid:
                for comment_index in html_comment_indexes:
                    searchable_lines[comment_index] = lines[comment_index]
                    excluded_line_numbers.discard(comment_index + 1)
            else:
                searchable_lines[index] = ""
                excluded_line_numbers.add(line_number)
            html_comment_indexes = []
            html_comment_invalid = False
            continue

        if raw_html is not None:
            mode, terminator = raw_html
            if mode == "blank" and not line.strip():
                raw_html = None
                continue
            searchable_lines[index] = ""
            excluded_line_numbers.add(line_number)
            if mode == "close" and terminator.casefold() in line.casefold():
                raw_html = None
            continue

        opening = FENCE_OPEN_RE.match(line)
        if opening is not None:
            marks = opening.group("marks")
            if marks[0] == "~" or "`" not in opening.group("info"):
                if in_historical_span:
                    searchable_lines[index] = ""
                    excluded_line_numbers.add(line_number)
                fence = (marks[0], len(marks))
                continue

        if line == HISTORICAL_BEGIN:
            searchable_lines[index] = ""
            excluded_line_numbers.add(line_number)
            if in_historical_span:
                structure_errors.append(
                    f"{line_number}: nested historical marker"
                )
            else:
                in_historical_span = True
            continue
        if line == HISTORICAL_END:
            searchable_lines[index] = ""
            excluded_line_numbers.add(line_number)
            if not in_historical_span:
                structure_errors.append(
                    f"{line_number}: unmatched historical end marker"
                )
            else:
                in_historical_span = False
            continue

        if in_historical_span:
            searchable_lines[index] = ""
            excluded_line_numbers.add(line_number)
            continue

        comment_position = line.find("<!--")
        if comment_position >= 0:
            prefix = line[:comment_position]
            if prefix:
                if prefix.strip() or (
                    prefix == " " * len(prefix) and 1 <= len(prefix) <= 3
                ):
                    structure_errors.append(
                        f"{line_number}: HTML comments must occupy whole lines"
                    )
                    remainder = line[comment_position + 4 :]
                    if "-->" not in remainder:
                        in_html_comment = True
                        html_comment_invalid = True
                        html_comment_start_line = line_number
                        html_comment_indexes = [index]
                # Four-space indentation and tab-indented lookalikes are code,
                # not policy comments. They remain active searchable prose.
                continue
            remainder = line[comment_position + 4 :]
            closing_position = remainder.find("-->")
            suffix = remainder[closing_position + 3 :] if closing_position >= 0 else ""
            in_html_comment = closing_position < 0
            if suffix.strip():
                structure_errors.append(
                    f"{line_number}: HTML comments must occupy whole lines"
                )
            else:
                searchable_lines[index] = ""
                excluded_line_numbers.add(line_number)
            if in_html_comment:
                html_comment_start_line = line_number
                html_comment_indexes = [index]
                html_comment_invalid = False
            continue

        anchor_match = ANCHOR_RE.match(line)
        if anchor_match is not None:
            section_id = anchor_match.group("section_id")
            anchors.append((line_number, section_id))
            anchors_by_line[line_number] = section_id
            continue

        raw_html = _raw_html_start(line)
        if raw_html is not None:
            structure_errors.append(
                f"{line_number}: raw HTML blocks are not allowed in ACTIVE runbooks"
            )
            searchable_lines[index] = ""
            excluded_line_numbers.add(line_number)
            mode, terminator = raw_html
            if mode == "close" and terminator.casefold() in line.casefold()[1:]:
                raw_html = None
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match is None:
            continue
        headings.append(
            (
                index,
                len(heading_match.group("marks")),
                ATX_CLOSING_RE.sub("", heading_match.group("text")).strip(),
                anchors_by_line.get(index),
            )
        )

    if in_historical_span:
        structure_errors.append("unclosed historical marker")
    if in_html_comment:
        structure_errors.append(
            f"{html_comment_start_line}: unclosed HTML comment"
        )
        for comment_index in html_comment_indexes:
            searchable_lines[comment_index] = lines[comment_index]
            excluded_line_numbers.discard(comment_index + 1)

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
                text="\n".join(searchable_lines[start:end]),
                direct_text="\n".join(searchable_lines[start:direct_end]),
                adjacent_anchor_id=adjacent_anchor_id,
                excluded_line_numbers=tuple(
                    line_number
                    for line_number in sorted(excluded_line_numbers)
                    if start < line_number <= end
                ),
            )
        )
    active_text = "\n".join(searchable_lines)
    if markdown.endswith("\n"):
        active_text += "\n"
    return MarkdownDocument(
        sections=tuple(sections),
        anchors=tuple(anchors),
        active_text=active_text,
        excluded_line_numbers=tuple(sorted(excluded_line_numbers)),
        structure_errors=tuple(structure_errors),
    )


def _raw_html_start(line: str) -> tuple[str, str] | None:
    type_1 = RAW_HTML_TYPE_1_RE.match(line)
    if type_1 is not None:
        return "close", f"</{type_1.group('tag')}>"
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) <= 3:
        if stripped.startswith("<![CDATA["):
            return ("close", "]]>")
        if stripped.startswith("<?"):
            return "close", "?>"
        if re.match(r"<![A-Z]", stripped):
            return "close", ">"
    if RAW_HTML_BLOCK_RE.match(line) is not None:
        return "blank", ""
    if RAW_HTML_GENERIC_RE.fullmatch(line) is not None:
        return "blank", ""
    return None


def declared_section_errors(
    markdown: str,
    path: str,
    rows: list[tuple[str, str | None]],
    *,
    authoritative_rows: list[tuple[str, str | None]] | None = None,
) -> list[str]:
    """Validate display headings and any opt-in stable identity declarations."""

    document = parse_markdown_document(markdown)
    sections_by_heading: dict[str, list[MarkdownSection]] = {}
    for candidate in document.sections:
        sections_by_heading.setdefault(candidate.heading, []).append(candidate)
    headings = set(sections_by_heading)
    errors = [f"{path}:{error}" for error in document.structure_errors]
    errors.extend(
        [
        f"{path}: dangling section {section!r}"
        for section, _ in rows
        if section not in headings
        ]
    )

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
            if len(sections_by_heading.get(section, [])) > 1:
                errors.append(
                    f"{path}: legacy section {section!r} is ambiguous because "
                    "the heading occurs more than once; add a stable section_id"
                )
                continue
            legacy_anchor = legacy_heading_anchor(section)
            collisions = [
                candidate
                for candidate in document.sections
                if candidate.heading != section
                and legacy_heading_anchor(candidate.heading) == legacy_anchor
            ]
            if not legacy_anchor:
                errors.append(
                    f"{path}: legacy section {section!r} has no safe Markdown "
                    "anchor; add a stable section_id"
                )
            elif collisions:
                collision_labels = ", ".join(
                    repr(candidate.heading)
                    for candidate in sorted(
                        collisions,
                        key=lambda candidate: (
                            candidate.heading_line,
                            candidate.heading,
                        ),
                    )
                )
                errors.append(
                    f"{path}: legacy section {section!r} shares Markdown anchor "
                    f"#{legacy_anchor} with {collision_labels}; add a stable section_id"
                )
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

    checked_authorities: set[tuple[str, str | None]] = set()
    for section, section_id in authoritative_rows or []:
        identity = (section, section_id)
        if identity in checked_authorities:
            continue
        checked_authorities.add(identity)
        candidates = [
            candidate
            for candidate in sections_by_heading.get(section, [])
            if section_id is None or candidate.adjacent_anchor_id == section_id
        ]
        if len(candidates) == 1 and not _has_substantive_active_body(candidates[0]):
            errors.append(
                f"{path}:{candidates[0].heading_line}: authoritative_for section "
                f"{section!r} has no substantive ACTIVE body"
            )
    return errors


def _has_substantive_active_body(section: MarkdownSection) -> bool:
    body_lines: list[str] = []
    for line in section.text.splitlines()[1:]:
        if HEADING_RE.match(line) is not None:
            continue
        if FENCE_OPEN_RE.match(line) is not None or FENCE_CLOSE_RE.match(line) is not None:
            continue
        if ANCHOR_RE.match(line) is not None:
            continue
        body_lines.append(line)
    body = " ".join(body_lines)
    body = re.sub(r"[`*_~>|#{}\[\]()]", " ", body)
    body = re.sub(r"\s+", " ", body).strip(" .,:;!?—-")
    if not re.search(r"[A-Za-z0-9]", body):
        return False
    return PLACEHOLDER_BODY_RE.fullmatch(body) is None
