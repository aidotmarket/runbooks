from __future__ import annotations

from collections.abc import Callable
from datetime import timezone
import re
from typing import Any

from runbook_tools.lint import CheckContext, Finding, retag_findings
from runbook_tools.lint.forms import (
    collect_b_rule_findings,
    extract_b_rows,
    extract_c_rows,
    extract_f_rows,
    extract_g_entries,
    extract_i_payload,
    extract_j_payload,
    extract_k_payload,
    parse_gfm_table,
    validate_a,
    validate_form,
    validate_k,
)
from runbook_tools.lint.staleness import _normalize_iso_value, evaluate_staleness, write_lifecycle_update
from runbook_tools.parser.sections import Section
from runbook_tools.version import LINTER_VERSION


CheckFn = Callable[[list[Section], CheckContext], list[Finding]]

PLACEHOLDER_RE = re.compile(r"^<<[^>]+>>$")
WEIGHT_JUSTIFICATION_HEADING_RE = re.compile(r"^###\s+§I\.1\s+Weight Justification\s*$", re.MULTILINE)
LIST_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
EXPECTED_B_HEADER = [
    "Feature/Capability",
    "Status",
    "Backing Code",
    "Test Coverage",
    "Last Verified",
]


def check_01_sections_present_and_ordered(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    letters = [section.letter for section in sections]
    expected = list("ABCDEFGHIJK")
    findings: list[Finding] = []

    for letter in expected:
        if letter not in letters:
            findings.append(Finding(severity="FAIL", check=1, message=f"missing §{letter}"))

    previous_index = -1
    for letter in letters:
        current_index = expected.index(letter)
        if current_index < previous_index:
            findings.append(Finding(severity="FAIL", check=1, message=f"§{letter} appears out of order"))
        previous_index = max(previous_index, current_index)
    return findings


def check_02_agent_forms_present(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(retag_findings(validate_a(ctx.frontmatter, ctx.schemas_dir), check=2))

    for section in sections:
        findings.extend(retag_findings(validate_form(section, ctx.schemas_dir), check=2))
    return findings


def check_03_a_j_owner_agent_consistency(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    frontmatter_owner = (ctx.frontmatter or {}).get("owner_agent")
    section_j = _section_map(sections).get("J")
    payload = _get_j_payload(sections, ctx)
    lifecycle_owner = payload.get("owner_agent") if payload else None
    if frontmatter_owner and lifecycle_owner and frontmatter_owner != lifecycle_owner:
        return [
            Finding(
                severity="FAIL",
                check=3,
                message=f"§A owner_agent {frontmatter_owner!r} does not match authoritative §J owner_agent {lifecycle_owner!r}",
                line=section_j.line_start if section_j is not None else None,
            )
        ]
    return []


def check_04_a_k0_linter_version_consistency(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    frontmatter_version = (ctx.frontmatter or {}).get("linter_version")
    section_k = _section_map(sections).get("K")
    payload = _get_k_payload(sections, ctx)
    conformance_version = payload.get("linter_version") if payload else None
    if frontmatter_version and conformance_version and frontmatter_version != conformance_version:
        return [
            Finding(
                severity="FAIL",
                check=4,
                message=f"§A linter_version {frontmatter_version!r} does not match authoritative §K.0 linter_version {conformance_version!r}",
                line=section_k.line_start if section_k is not None else None,
            )
        ]
    return []


def check_05_status_values(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    section_b = _section_map(sections).get("B")
    if section_b is None:
        return []
    return [
        Finding(
            severity=finding.severity,
            check=5,
            message=finding.message,
            line=finding.line,
            hint=finding.hint,
        )
        for finding in collect_b_rule_findings(section_b, check=5)
        if "Status cell must" in finding.message
    ]


def check_06_backing_code(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    section_b = _section_map(sections).get("B")
    if section_b is None:
        return []
    findings = collect_b_rule_findings(section_b, check=6)
    return [
        Finding(
            severity=finding.severity,
            check=6,
            message=finding.message,
            line=finding.line,
            hint=finding.hint,
        )
        for finding in findings
        if "Backing Code" in finding.message
    ]


def check_07_last_verified_warn(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    section_b = _section_map(sections).get("B")
    if section_b is None:
        return []
    findings = collect_b_rule_findings(section_b, check=7)
    return [
        Finding(
            severity="WARN",
            check=7,
            message=finding.message,
            line=finding.line,
            hint=finding.hint,
        )
        for finding in findings
        if finding.severity == "WARN" and "Last Verified" in finding.message
    ]


def check_08_repair_ref_resolves(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    section_map = _section_map(sections)
    section_f = section_map.get("F")
    section_g = section_map.get("G")
    if section_f is None or section_g is None:
        return []
    repair_ids = {entry.get("id") for entry in extract_g_entries(section_g)}
    findings: list[Finding] = []
    for row in extract_f_rows(section_f):
        repair_ref = row.get("Repair Ref", "").strip()
        if not repair_ref:
            continue
        target_id = repair_ref.removeprefix("§")
        if target_id not in repair_ids:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=8,
                    message=f'§F row {row.get("ID", "<unknown>")} Repair Ref "{repair_ref}" does not resolve to any §G id',
                    line=_line_for_row(section_f, row),
                )
            )
    return findings


def check_09_symptom_ref_resolves(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    section_map = _section_map(sections)
    section_f = section_map.get("F")
    section_g = section_map.get("G")
    if section_f is None or section_g is None:
        return []
    symptom_ids = {row.get("ID") for row in extract_f_rows(section_f)}
    findings: list[Finding] = []
    for entry in extract_g_entries(section_g):
        symptom_ref = str(entry.get("symptom_ref", "")).strip()
        if symptom_ref not in symptom_ids:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=9,
                    message=f'§G entry {entry.get("id", "<unknown>")} symptom_ref "{symptom_ref}" does not resolve to any §F ID',
                    line=section_g.line_start,
                )
            )
    return findings


def check_10_component_ref_resolves(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    section_map = _section_map(sections)
    section_c = section_map.get("C")
    section_g = section_map.get("G")
    if section_c is None or section_g is None:
        return []
    component_ids = {row.get("Component") for row in extract_c_rows(section_c)}
    findings: list[Finding] = []
    for entry in extract_g_entries(section_g):
        component_ref = str(entry.get("component_ref", "")).strip()
        if component_ref not in component_ids:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=10,
                    message=f'§G entry {entry.get("id", "<unknown>")} component_ref "{component_ref}" does not resolve to any §C Component',
                    line=section_g.line_start,
                )
            )
    return findings


def check_11_scenario_distribution(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    section_i = _section_map(sections).get("I")
    payload = _get_i_payload(sections, ctx)
    if section_i is None or payload is None:
        return []

    scenario_set = payload.get("scenario_set", [])
    counts = {
        "operate": sum(1 for scenario in scenario_set if scenario.get("type") == "operate"),
        "isolate": sum(1 for scenario in scenario_set if scenario.get("type") == "isolate"),
        "repair": sum(1 for scenario in scenario_set if scenario.get("type") == "repair"),
        "evolve": sum(1 for scenario in scenario_set if scenario.get("type") == "evolve"),
        "ambiguous": sum(1 for scenario in scenario_set if scenario.get("type") == "ambiguous"),
    }

    findings: list[Finding] = []
    if len(scenario_set) < 10:
        findings.append(Finding(severity="FAIL", check=11, message=f"§I has {len(scenario_set)} total scenarios, needs ≥10", line=section_i.line_start))

    minimums = {
        "operate": 3,
        "isolate": 3,
        "repair": 2,
        "evolve": 2,
        "ambiguous": 1,
    }
    for scenario_type, minimum in minimums.items():
        if counts[scenario_type] < minimum:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=11,
                    message=f"§I has {counts[scenario_type]} {scenario_type} scenarios, needs ≥{minimum}",
                    line=section_i.line_start,
                )
            )
    return findings


def check_12_weights_sum(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    section_i = _section_map(sections).get("I")
    payload = _get_i_payload(sections, ctx)
    if section_i is None or payload is None:
        return []

    scenario_set = payload.get("scenario_set", [])
    total = sum(float(scenario.get("weight", 0.0)) for scenario in scenario_set)
    if abs(total - 1.0) <= 0.001:
        return []
    return [
        Finding(
            severity="FAIL",
            check=12,
            message=f"§I scenario weights sum to {total:.6f}, expected 1.0 ± 0.001",
            line=section_i.line_start,
        )
    ]


def check_13_unequal_weights_justified(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    section_i = _section_map(sections).get("I")
    payload = _get_i_payload(sections, ctx)
    if section_i is None or payload is None:
        return []

    scenario_set = payload.get("scenario_set", [])
    if not scenario_set:
        return []

    expected_weight = 1.0 / len(scenario_set)
    divergent_ids = [
        str(scenario.get("id"))
        for scenario in scenario_set
        if abs(float(scenario.get("weight", 0.0)) - expected_weight) > 1e-6
    ]
    if not divergent_ids:
        return []

    section_text = section_i.raw_markdown
    heading_match = WEIGHT_JUSTIFICATION_HEADING_RE.search(section_text)
    if heading_match is None:
        return [
            Finding(
                severity="FAIL",
                check=13,
                message="§I has unequal scenario weights; missing ### §I.1 Weight Justification subsection",
                line=section_i.line_start,
            )
        ]

    entries = _extract_weight_justification_entries(section_text[heading_match.end() :])
    findings: list[Finding] = []
    for scenario_id in divergent_ids:
        if scenario_id not in entries:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=13,
                    message=f"§I.1 Weight Justification is missing an entry for divergent scenario {scenario_id}",
                    line=section_i.line_start,
                )
            )
    return findings


def check_14_lifecycle_fields(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    section_j = _section_map(sections).get("J")
    payload = _get_j_payload(sections, ctx)
    if section_j is None or payload is None:
        return []

    required_fields = [
        "last_refresh_session",
        "last_refresh_commit",
        "last_refresh_date",
        "owner_agent",
        "refresh_triggers",
        "last_harness_pass_rate",
        "last_harness_date",
        "first_staleness_detected_at",
    ]
    return _required_field_findings(section_j, payload, required_fields, check=14, label="§J")


def check_15_staleness_grace_workflow(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    if ctx.now is None or ctx.git_head is None:
        return []
    if _section_map(sections).get("J") is None:
        return []
    payload = _get_j_payload(sections, ctx)
    if payload is None:
        return []

    is_stale, triggered_predicates, new_first_detected_at, recommended_action = evaluate_staleness(
        sections, ctx.now, ctx.git_head
    )
    triggered = ", ".join(triggered_predicates)
    findings: list[Finding] = []
    prev_first = _normalize_iso_value(payload.get("first_staleness_detected_at"))

    if is_stale and prev_first is None and recommended_action == "SET":
        findings.append(
            Finding(
                severity="WARN",
                check=15,
                message=f"§J.first_staleness_detected_at must be set to {new_first_detected_at}",
            )
        )
    elif is_stale and prev_first is not None and recommended_action == "NONE":
        days = _grace_days(ctx.now, prev_first)
        if days <= 30:
            findings.append(
                Finding(
                    severity="WARN",
                    check=15,
                    message=f"§J stale ({triggered}), grace clock at {days}/30 days",
                )
            )
        else:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=15,
                    message=f"§J stale ({triggered}), grace period exceeded ({days} > 30)",
                )
            )
    elif (not is_stale) and prev_first is not None and recommended_action == "CLEAR":
        findings.append(
            Finding(
                severity="WARN",
                check=15,
                message="§J.first_staleness_detected_at requires clear to null (all stale predicates fell)",
            )
        )

    if findings and ctx.update_lifecycle and ctx.readme_path is not None and recommended_action in {"SET", "CLEAR"}:
        write_lifecycle_update(ctx.readme_path, new_first_detected_at)
        findings = [
            Finding(
                severity="INFO",
                check=15,
                message=finding.message,
                line=finding.line,
                hint=finding.hint,
            )
            for finding in findings
        ]

    return findings


def check_16_linter_version_compat(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    section_k = _section_map(sections).get("K")
    payload = _get_k_payload(sections, ctx)
    if section_k is None or payload is None:
        return []

    runbook_version = str(payload.get("linter_version", "")).strip()
    current = _parse_semver(LINTER_VERSION)
    target = _parse_semver(runbook_version)
    if current is None or target is None:
        return []
    if current[:2] == target[:2]:
        return []
    return [
        Finding(
            severity="WARN",
            check=16,
            message=f"runbook validated against linter version {runbook_version} but currently running {LINTER_VERSION}",
            line=section_k.line_start,
        )
    ]


def check_17_conformance_fields(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    section_k = _section_map(sections).get("K")
    payload = _get_k_payload(sections, ctx)
    if section_k is None or payload is None:
        return []

    required_fields = [
        "linter_version",
        "last_lint_run",
        "last_lint_result",
        "trace_matrix_path",
        "word_count_delta",
    ]
    return _required_field_findings(section_k, payload, required_fields, check=17, label="§K")


def check_18_retrofit_fields(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    section_k = _section_map(sections).get("K")
    payload = _get_k_payload(sections, ctx)
    if section_k is None or payload is None:
        return []

    retrofit_findings = [
        Finding(
            severity="FAIL",
            check=18,
            message="retrofit=true requires non-null trace_matrix_path and word_count_delta",
            line=section_k.line_start,
        )
        for finding in validate_k(section_k, ctx.schemas_dir)
        if "trace_matrix_path" in finding.message or "word_count_delta" in finding.message
    ]
    if retrofit_findings:
        return retrofit_findings[:1]

    if payload.get("retrofit") is True and (
        payload.get("trace_matrix_path") is None or payload.get("word_count_delta") is None
    ):
        return [
            Finding(
                severity="FAIL",
                check=18,
                message="retrofit=true requires non-null trace_matrix_path and word_count_delta",
                line=section_k.line_start,
            )
        ]
    return []


def check_19_header_required_fields(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del sections
    frontmatter = ctx.frontmatter or {}
    required_fields = [
        "system_name",
        "purpose_sentence",
        "owner_agent",
        "escalation_contact",
        "lifecycle_ref",
        "authoritative_scope",
        "linter_version",
    ]
    findings: list[Finding] = []
    for field in required_fields:
        if field not in frontmatter:
            findings.append(Finding(severity="FAIL", check=19, message=f"§A missing required field {field}"))
            continue
        value = frontmatter[field]
        if _is_placeholder(value):
            findings.append(Finding(severity="FAIL", check=19, message=f"placeholder not filled: {value}"))
        elif _is_missing(value):
            findings.append(Finding(severity="FAIL", check=19, message=f"§A required field {field} must be non-empty"))
    return findings


def check_20_b_exact_columns(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    del ctx
    section_b = _section_map(sections).get("B")
    if section_b is None:
        return []
    headers, _ = parse_gfm_table(section_b.ast_subtree)
    if headers == EXPECTED_B_HEADER:
        return []
    got = " | ".join(headers) if headers else "<missing table header>"
    expected = " | ".join(EXPECTED_B_HEADER)
    return [
        Finding(
            severity="FAIL",
            check=20,
            message=f"§B header row must match exactly. expected '{expected}', got '{got}'",
            line=section_b.line_start,
        )
    ]


CHECKS_BUILD2: list[CheckFn] = [
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
]

ALL_CHECKS: list[CheckFn] = [
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
]


def _section_map(sections: list[Section]) -> dict[str, Section]:
    return {section.letter: section for section in sections}


def _line_for_row(section: Section, row: dict[str, str]) -> int | None:
    for value in row.values():
        if value:
            for index, line in enumerate(section.raw_markdown.splitlines(), start=section.line_start):
                if value in line:
                    return index
    return section.line_start


def _get_i_payload(sections: list[Section], ctx: CheckContext) -> dict[str, Any] | None:
    return _get_cached_payload("I", sections, ctx, extract_i_payload)


def _get_j_payload(sections: list[Section], ctx: CheckContext) -> dict[str, Any] | None:
    return _get_cached_payload("J", sections, ctx, extract_j_payload)


def _get_k_payload(sections: list[Section], ctx: CheckContext) -> dict[str, Any] | None:
    return _get_cached_payload("K", sections, ctx, extract_k_payload)


def _get_cached_payload(
    letter: str,
    sections: list[Section],
    ctx: CheckContext,
    loader: Callable[[Section], dict[str, Any] | None],
) -> dict[str, Any] | None:
    cache_key = f"section_{letter}_payload"
    cached = ctx.form_cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    section = _section_map(sections).get(letter)
    payload = loader(section) if section is not None else None
    if isinstance(payload, dict):
        ctx.form_cache[cache_key] = payload
    return payload


def _extract_weight_justification_entries(text: str) -> set[str]:
    entries: set[str] = set()
    for line in text.splitlines():
        if line.startswith("#"):
            break
        match = LIST_ITEM_RE.match(line)
        if match is None:
            continue
        scenario_id = match.group(1).split()[0].rstrip(":")
        entries.add(scenario_id)
    return entries


def _required_field_findings(
    section: Section,
    payload: dict[str, Any],
    required_fields: list[str],
    *,
    check: int,
    label: str,
) -> list[Finding]:
    nullable_fields = {
        "§J": {"first_staleness_detected_at"},
        "§K": {"trace_matrix_path", "word_count_delta"},
    }
    findings: list[Finding] = []
    for field in required_fields:
        if field not in payload:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message=f"{label} missing required field {field}",
                    line=section.line_start,
                )
            )
            continue
        value = payload[field]
        if _is_placeholder(value):
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message=f"{label} field {field} contains placeholder not filled: {value}",
                    line=section.line_start,
                )
            )
        elif _is_missing(value) and field not in nullable_fields.get(label, set()):
            findings.append(
                Finding(
                    severity="FAIL",
                    check=check,
                    message=f"{label} field {field} must be present and non-placeholder",
                    line=section.line_start,
                )
            )
    return findings


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, list):
        return len(value) == 0
    return False


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(PLACEHOLDER_RE.fullmatch(value.strip()))


def _parse_semver(value: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.fullmatch(value)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _grace_days(now: Any, prev_first: str) -> int:
    now_utc = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    prev = _parse_datetime(prev_first)
    return (now_utc.astimezone(timezone.utc) - prev).days


def _parse_datetime(value: str) -> Any:
    from dateutil import parser as dateparser

    parsed = dateparser.parse(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
