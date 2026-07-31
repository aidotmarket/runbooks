from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from runbook_tools.catalog.sections import FENCE_CLOSE_RE, FENCE_OPEN_RE
from runbook_tools.lint import Finding
from runbook_tools.parser.sections import Section, extract_fenced_yaml_block

STATUS_ENUM = {"SHIPPED", "PARTIAL", "PLANNED", "DEPRECATED", "BROKEN"}
COVERAGE_STATUS_ENUM = {"COMPLETE", "PARTIAL", "GAP", "PLANNED"}
BACKING_CODE_RE = re.compile(r"^`[^`]+`$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RFC3339_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)
LAST_VERIFIED_MAX_AGE_DAYS = 90
H_SECTION_HEADINGS = [
    "§H.1 Invariants",
    "§H.2 BREAKING predicates",
    "§H.3 REVIEW predicates",
    "§H.4 SAFE predicates",
    "§H.5 Boundary definitions",
    "§H.6 Adjudication",
]
H5_SUBHEADINGS = [
    "module",
    "public contract",
    "runtime dependency",
    "config default",
]
_FORMAT_CHECKER = FormatChecker()
_ESCAPED_FORM_RE: dict[str, re.Pattern[str]] = {
    "E": re.compile(r"^ {0,3}-[ \t]+id:[ \t]+[\"']?E-\d{2,}\b"),
    "G": re.compile(r"^ {0,3}-[ \t]+id:[ \t]+[\"']?G-\d{2,}\b"),
    "I": re.compile(
        r"^(?: {0,3}scenario_set:[ \t]*| {0,3}-[ \t]+id:[ \t]+[\"']?I-\d{2,}\b)"
    ),
    "J": re.compile(
        r"^ {0,3}(?:last_refresh_session|last_refresh_commit|last_refresh_date|"
        r"owner_agent|refresh_triggers|scheduled_cadence|"
        r"last_harness_pass_rate|last_harness_date|"
        r"first_staleness_detected_at):[ \t]*"
    ),
    "K": re.compile(
        r"^ {0,3}(?:linter_version|last_lint_run|last_lint_result|retrofit|"
        r"trace_matrix_path|word_count_delta):[ \t]*"
    ),
}


@_FORMAT_CHECKER.checks("date")
def _valid_date_format(value: object) -> bool:
    if not isinstance(value, str) or ISO_DATE_RE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


@_FORMAT_CHECKER.checks("date-time")
def _valid_datetime_format(value: object) -> bool:
    if not isinstance(value, str) or RFC3339_DATETIME_RE.fullmatch(value) is None:
        return False
    normalized = value[:-1] + "+00:00" if value[-1:].casefold() == "z" else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_form(section: Section, schemas_dir: Path) -> list[Finding]:
    validators = {
        "B": validate_b,
        "C": validate_c,
        "D": validate_d,
        "E": validate_e,
        "F": validate_f,
        "G": validate_g,
        "H": validate_h,
        "I": validate_i,
        "J": validate_j,
        "K": validate_k,
    }
    validator = validators.get(section.letter)
    if validator is None:
        return []
    return validator(section, schemas_dir)


def parse_gfm_table(markdown_subtree: list) -> tuple[list[str], list[dict[str, str]]]:
    table_node = _find_table_node(markdown_subtree)
    if table_node is None:
        return [], []

    header_node = next((child for child in table_node.get("children", []) if child.get("type") == "table_head"), None)
    body_node = next((child for child in table_node.get("children", []) if child.get("type") == "table_body"), None)
    if header_node is None or body_node is None:
        return [], []

    headers = [_flatten_text(cell) for cell in header_node.get("children", [])]
    rows: list[dict[str, str]] = []
    for row in body_node.get("children", []):
        if row.get("type") != "table_row":
            continue
        cells = [_flatten_text(cell) for cell in row.get("children", [])]
        row_dict = {header: cells[index] if index < len(cells) else "" for index, header in enumerate(headers)}
        rows.append(row_dict)
    return headers, rows


def normalize_table_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized_rows.append({_normalize_header(key): value for key, value in row.items()})
    return normalized_rows


def validate_a(frontmatter_dict: dict | None, schemas_dir: Path) -> list[Finding]:
    return _validate_schema_payload(
        payload=frontmatter_dict,
        schema_path=schemas_dir / "section_a_header.schema.json",
        line=None,
        empty_message="§A frontmatter is missing or not a YAML object",
    )


def validate_b(section: Section, schemas_dir: Path) -> list[Finding]:
    headers, rows = parse_gfm_table(section.ast_subtree)
    findings = _validate_table_schema(
        section=section,
        schema_path=schemas_dir / "section_b_capability_matrix.schema.json",
        headers=headers,
        rows=rows,
    )
    findings.extend(collect_b_rule_findings(section, check=2, include_warn=False))
    return findings


def validate_c(section: Section, schemas_dir: Path) -> list[Finding]:
    headers, rows = parse_gfm_table(section.ast_subtree)
    return _validate_table_schema(
        section=section,
        schema_path=schemas_dir / "section_c_architecture.schema.json",
        headers=headers,
        rows=rows,
    )


def validate_d(section: Section, schemas_dir: Path) -> list[Finding]:
    headers, rows = parse_gfm_table(section.ast_subtree)
    findings: list[Finding] = []
    if not rows:
        return [
            Finding(
                severity="FAIL",
                check=2,
                message="§D must contain a markdown table",
                line=section.line_start,
            )
        ]

    normalized_rows = []
    for row in rows:
        raw_value = row.get("Coverage Status", "")
        status, _, closure = raw_value.partition("— ")
        status = status.strip()
        normalized = dict(row)
        normalized["Coverage Status"] = status
        normalized_rows.append(normalized)
        if status in {"GAP", "PARTIAL"} and not closure.strip():
            findings.append(
                Finding(
                    severity="FAIL",
                    check=2,
                    message="coverage gap row requires closure text after '— '",
                    line=_line_for_text(section, raw_value),
                )
            )
        if status and status not in COVERAGE_STATUS_ENUM:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=2,
                    message=f"Coverage Status cell must be COMPLETE/PARTIAL/GAP/PLANNED (got {status})",
                    line=_line_for_text(section, raw_value),
                )
            )

    findings.extend(
        _validate_table_schema(
            section=section,
            schema_path=schemas_dir / "section_d_capability_map.schema.json",
            headers=headers,
            rows=normalized_rows,
        )
    )
    return findings


def validate_e(section: Section, schemas_dir: Path) -> list[Finding]:
    return _validate_yaml_block(
        section=section,
        schemas_dir=schemas_dir,
        marker="operate",
        schema_name="section_e_operate.schema.json",
    )


def validate_f(section: Section, schemas_dir: Path) -> list[Finding]:
    headers, rows = parse_gfm_table(section.ast_subtree)
    return _validate_table_schema(
        section=section,
        schema_path=schemas_dir / "section_f_isolate.schema.json",
        headers=headers,
        rows=rows,
    )


def validate_g(section: Section, schemas_dir: Path) -> list[Finding]:
    return _validate_yaml_block(
        section=section,
        schemas_dir=schemas_dir,
        marker="repair",
        schema_name="section_g_repair.schema.json",
    )


def validate_h(section: Section, schemas_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    h3_headings = [
        _flatten_text(token)
        for token in section.ast_subtree
        if token.get("type") == "heading" and token.get("attrs", {}).get("level") == 3
    ]
    if h3_headings != H_SECTION_HEADINGS:
        findings.append(
            Finding(
                severity="FAIL",
                check=2,
                message=f"§H subsections must be present in order: {', '.join(H_SECTION_HEADINGS)}",
                line=section.line_start,
            )
        )

    h5_started = False
    h5_subheadings: list[str] = []
    for token in section.ast_subtree:
        if token.get("type") != "heading":
            continue
        level = token.get("attrs", {}).get("level")
        text = _flatten_text(token)
        if level == 3 and text == "§H.5 Boundary definitions":
            h5_started = True
            continue
        if not h5_started:
            continue
        if level == 3:
            break
        if level == 4:
            h5_subheadings.append(text)

    if h5_subheadings != H5_SUBHEADINGS:
        findings.append(
            Finding(
                severity="FAIL",
                check=2,
                message="§H.5 must contain #### module, #### public contract, #### runtime dependency, #### config default in exact order",
                line=section.line_start,
            )
        )

    findings.extend(
        _validate_schema_payload(
            payload=_extract_h_payload(section),
            schema_path=schemas_dir / "section_h_evolve.schema.json",
            line=section.line_start,
            empty_message="§H evolve payload is empty",
        )
    )
    return findings


def validate_i(section: Section, schemas_dir: Path) -> list[Finding]:
    return _validate_yaml_block(
        section=section,
        schemas_dir=schemas_dir,
        marker="acceptance",
        schema_name="section_i_acceptance.schema.json",
    )


def validate_j(section: Section, schemas_dir: Path) -> list[Finding]:
    return _validate_yaml_block(
        section=section,
        schemas_dir=schemas_dir,
        marker="lifecycle",
        schema_name="section_j_lifecycle.schema.json",
    )


def validate_k(section: Section, schemas_dir: Path) -> list[Finding]:
    return _validate_yaml_block(
        section=section,
        schemas_dir=schemas_dir,
        marker="conformance",
        schema_name="section_k_conformance.schema.json",
    )


def extract_b_rows(section: Section) -> list[dict[str, str]]:
    _, rows = parse_gfm_table(section.ast_subtree)
    return rows


def extract_c_rows(section: Section) -> list[dict[str, str]]:
    _, rows = parse_gfm_table(section.ast_subtree)
    return rows


def extract_f_rows(section: Section) -> list[dict[str, str]]:
    _, rows = parse_gfm_table(section.ast_subtree)
    return rows


def extract_e_entries(section: Section) -> list[dict[str, Any]]:
    block = extract_fenced_yaml_block(section, "operate")
    return block if isinstance(block, list) else []


def extract_g_entries(section: Section) -> list[dict[str, Any]]:
    block = extract_fenced_yaml_block(section, "repair")
    return block if isinstance(block, list) else []


def extract_i_payload(section: Section) -> dict[str, Any] | None:
    block = extract_fenced_yaml_block(section, "acceptance")
    return block if isinstance(block, dict) else None


def extract_j_payload(section: Section) -> dict[str, Any] | None:
    block = extract_fenced_yaml_block(section, "lifecycle")
    return block if isinstance(block, dict) else None


def extract_k_payload(section: Section) -> dict[str, Any] | None:
    block = extract_fenced_yaml_block(section, "conformance")
    return block if isinstance(block, dict) else None


def collect_b_rule_findings(
    section: Section,
    check: int,
    *,
    include_warn: bool = True,
    now: datetime | None = None,
) -> list[Finding]:
    return _validate_b_rules(
        section,
        extract_b_rows(section),
        check,
        include_warn=include_warn,
        now=now,
    )


def classify_last_verified(
    value: str,
    now: datetime | None,
) -> tuple[str, int | None]:
    """Classify a §B verification cell using one shared calendar-day rule."""

    normalized = value.strip()
    if normalized in {"", "—"}:
        return "unverified", None
    if not ISO_DATE_RE.fullmatch(normalized):
        return "invalid", None
    try:
        verified_at = date.fromisoformat(normalized)
    except ValueError:
        return "invalid", None
    if now is None:
        return "verified", None
    now_utc = (
        now.replace(tzinfo=UTC)
        if now.tzinfo is None
        else now.astimezone(UTC)
    )
    age_days = (now_utc.date() - verified_at).days
    if age_days < 0:
        return "future", age_days
    if age_days > LAST_VERIFIED_MAX_AGE_DAYS:
        return "expired", age_days
    return "verified", age_days


def _validate_yaml_block(section: Section, schemas_dir: Path, marker: str, schema_name: str) -> list[Finding]:
    payload = extract_fenced_yaml_block(section, marker)
    findings = _validate_schema_payload(
        payload=payload,
        schema_path=schemas_dir / schema_name,
        line=section.line_start,
        empty_message=f"§{section.letter} must contain a ```yaml {marker}``` block",
    )
    findings.extend(_escaped_form_findings(section, marker))
    return findings


def _escaped_form_findings(section: Section, marker: str) -> list[Finding]:
    pattern = _ESCAPED_FORM_RE.get(section.letter)
    if pattern is None:
        return []
    for offset, line in _rendered_prose_lines(section.raw_markdown):
        if pattern.match(line) is not None:
            return [
                Finding(
                    severity="FAIL",
                    check=2,
                    message=(
                        f"§{section.letter} form-shaped content must be inside "
                        f"a rendered ```yaml {marker}``` block"
                    ),
                    line=section.line_start + offset,
                )
            ]
    return []


def _rendered_prose_lines(markdown: str) -> Iterable[tuple[int, str]]:
    fence: tuple[str, int] | None = None
    for offset, line in enumerate(markdown.splitlines()):
        if fence is not None:
            closing = FENCE_CLOSE_RE.fullmatch(line)
            if closing is not None:
                marks = closing.group("marks")
                if marks[0] == fence[0] and len(marks) >= fence[1]:
                    fence = None
            continue

        opening = FENCE_OPEN_RE.match(line)
        if opening is not None:
            marks = opening.group("marks")
            info = opening.group("info")
            if marks[0] == "~" or "`" not in info:
                fence = (marks[0], len(marks))
                continue
        yield offset, line


def _validate_table_schema(section: Section, schema_path: Path, headers: list[str], rows: list[dict[str, str]]) -> list[Finding]:
    if not headers or not rows:
        return [
            Finding(
                severity="FAIL",
                check=2,
                message=f"§{section.letter} must contain a markdown table",
                line=section.line_start,
            )
        ]
    return _validate_schema_payload(
        payload=normalize_table_rows(rows),
        schema_path=schema_path,
        line=section.line_start,
        empty_message=f"§{section.letter} table payload is empty",
    )


def _validate_schema_payload(payload: Any, schema_path: Path, line: int | None, empty_message: str) -> list[Finding]:
    if payload is None:
        return [Finding(severity="FAIL", check=2, message=empty_message, line=line)]

    normalized_payload = _normalize_yaml_scalars(payload)
    validator = Draft202012Validator(_load_schema(schema_path), format_checker=_FORMAT_CHECKER)
    findings: list[Finding] = []
    for error in validator.iter_errors(normalized_payload):
        location = ".".join(str(part) for part in error.absolute_path)
        message = error.message
        if location:
            message = f"{location}: {message}"
        findings.append(Finding(severity="FAIL", check=2, message=message, line=line))
    return sorted(findings, key=lambda finding: finding.message)


def _validate_b_rules(
    section: Section,
    rows: list[dict[str, str]],
    check: int,
    *,
    include_warn: bool = True,
    now: datetime | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    for row in rows:
        status = row.get("Status", "").strip()
        backing_code = row.get("Backing Code", "").strip()
        last_verified = row.get("Last Verified", "").strip()
        row_line = _line_for_text(section, row.get("Feature/Capability", "")) or section.line_start

        if status.startswith("<<") and status.endswith(">>"):
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message="Status cell must be SHIPPED/PARTIAL/PLANNED/DEPRECATED/BROKEN (got placeholder)",
                    line=row_line,
                )
            )
        elif status and status not in STATUS_ENUM:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message=f"Status cell must be SHIPPED/PARTIAL/PLANNED/DEPRECATED/BROKEN (got {status})",
                    line=row_line,
                )
            )

        if backing_code.startswith("<<") and backing_code.endswith(">>"):
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message="Backing Code cell must be backticked path or em-dash (got placeholder)",
                    line=row_line,
                )
            )
        elif backing_code == "—" and status not in {"PLANNED", "DEPRECATED"}:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message=f"Backing Code must not be em-dash when Status is {status}",
                    line=row_line,
                )
            )
        elif backing_code not in {"", "—"} and not BACKING_CODE_RE.fullmatch(backing_code):
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message="Backing Code cell must be backticked path or em-dash",
                    line=row_line,
                )
            )

        verification_state, age_days = classify_last_verified(last_verified, now)
        if verification_state == "unverified":
            if include_warn:
                findings.append(
                    Finding(
                        severity="WARN",
                        check=check,
                        message="Last Verified is empty or em-dash; row is UNVERIFIED",
                        line=row_line,
                    )
                )
        elif verification_state == "invalid":
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message=(
                        "Last Verified must be a real YYYY-MM-DD date, empty, "
                        f"or em-dash (got {last_verified})"
                    ),
                    line=row_line,
                )
            )
        elif verification_state == "future":
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message=(
                        f"Last Verified is in the future ({last_verified}); "
                        "verification evidence cannot postdate the lint clock"
                    ),
                    line=row_line,
                )
            )
        elif verification_state == "expired" and include_warn:
            findings.append(
                Finding(
                    severity="WARN",
                    check=check,
                    message=(
                        f"Last Verified is {age_days} days old "
                        f"(> {LAST_VERIFIED_MAX_AGE_DAYS}); row is UNVERIFIED"
                    ),
                    line=row_line,
                )
            )
    return findings


def _find_table_node(tokens: list) -> dict[str, Any] | None:
    for token in tokens:
        if token.get("type") == "table":
            return token
        children = token.get("children")
        if isinstance(children, list):
            found = _find_table_node(children)
            if found is not None:
                return found
    return None


def _extract_h_payload(section: Section) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    current_key: str | None = None
    current_h5_key: str | None = None
    for token in section.ast_subtree:
        if token.get("type") != "heading":
            continue

        level = token.get("attrs", {}).get("level")
        text = _flatten_text(token)
        if level == 3:
            current_h5_key = None
            current_key = {
                "§H.1 Invariants": "h1",
                "§H.2 BREAKING predicates": "h2",
                "§H.3 REVIEW predicates": "h3",
                "§H.4 SAFE predicates": "h4",
                "§H.5 Boundary definitions": "h5",
                "§H.6 Adjudication": "h6",
            }.get(text)
            continue
        if current_key != "h5" or level != 4:
            continue
        current_h5_key = {
            "module": "module",
            "public contract": "public_contract",
            "runtime dependency": "runtime_dependency",
            "config default": "config_default",
        }.get(text)
        if current_h5_key is not None:
            payload.setdefault("h5", {})[current_h5_key] = _extract_h_heading_body(section, text)

    for heading, key in (
        ("§H.1 Invariants", "h1"),
        ("§H.2 BREAKING predicates", "h2"),
        ("§H.3 REVIEW predicates", "h3"),
        ("§H.4 SAFE predicates", "h4"),
        ("§H.6 Adjudication", "h6"),
    ):
        body = _extract_h_heading_body(section, heading)
        if body is not None:
            payload[key] = body

    return payload


def _extract_h_heading_body(section: Section, heading_text: str) -> str | None:
    tokens = section.ast_subtree
    for index, token in enumerate(tokens):
        if token.get("type") != "heading":
            continue
        if _flatten_text(token) != heading_text:
            continue
        heading_level = token.get("attrs", {}).get("level")
        if not isinstance(heading_level, int):
            return None

        collected: list[str] = []
        for body_token in tokens[index + 1 :]:
            if body_token.get("type") == "heading":
                next_level = body_token.get("attrs", {}).get("level")
                if isinstance(next_level, int) and next_level <= heading_level:
                    break
            body = _flatten_text(body_token).strip()
            if body:
                collected.append(body)
        rendered_body = "\n".join(collected).strip()
        return rendered_body or None
    return None


def _flatten_text(token: dict[str, Any]) -> str:
    if token.get("type") == "codespan":
        return f"`{token.get('raw', '')}`"
    if "raw" in token:
        return str(token["raw"])
    parts: list[str] = []
    for child in token.get("children", []):
        parts.append(_flatten_text(child))
    return "".join(parts).strip()


def _line_for_text(section: Section, text: str) -> int | None:
    if not text:
        return section.line_start
    for index, line in enumerate(section.raw_markdown.splitlines(), start=section.line_start):
        if text in line:
            return index
    return section.line_start


def _load_schema(schema_path: Path) -> dict[str, Any]:
    import json

    return json.loads(schema_path.read_text())


def _normalize_header(header: str) -> str:
    collapsed = re.sub(r"[^A-Za-z0-9]+", "_", header.strip())
    return collapsed.strip("_")


def _normalize_yaml_scalars(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_yaml_scalars(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_normalize_yaml_scalars(child) for child in value]
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return value
