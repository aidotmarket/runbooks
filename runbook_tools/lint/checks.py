from __future__ import annotations

import math
import re
from collections.abc import Callable
from datetime import UTC
from typing import Any

from runbook_tools.catalog.sections import parse_markdown_document
from runbook_tools.lint import CheckContext, Finding, retag_findings
from runbook_tools.lint.forms import (
    collect_b_rule_findings,
    extract_c_rows,
    extract_e_entries,
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
from runbook_tools.lint.staleness import (
    PENDING_HARNESS_TOOLING,
    _normalize_iso_value,
    evaluate_staleness,
    newest_harness_result,
)
from runbook_tools.lint.staleness import (
    _parse_datetime as _parse_staleness_datetime,
)
from runbook_tools.parser.sections import Section
from runbook_tools.placeholders import UNRESOLVED_PLACEHOLDER_RE
from runbook_tools.version import LINTER_VERSION

CheckFn = Callable[[list[Section], CheckContext], list[Finding]]

PLACEHOLDER_RE = re.compile(r"^<<[^>]+>>$")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
LOCAL_ENTRY_REF_RE = re.compile(r"^§?([EFG])-\d{2,}$")
LOCAL_SECTION_REF_RE = re.compile(r"^§([A-K])(?:\.(\d+))?$")
CROSS_FILE_REF_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*:"
    r"(?:§?(?:[EFGI]-\d{2,})|§[A-K](?:\.\d+)?)$"
)
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
        count = letters.count(letter)
        if count == 0:
            findings.append(Finding(severity="FAIL", check=1, message=f"missing §{letter}"))
        elif count > 1:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=1,
                    message=f"§{letter} appears {count} times; exactly one current section is required",
                )
            )

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
    section_b = _section_map(sections).get("B")
    if section_b is None:
        return []
    findings = collect_b_rule_findings(section_b, check=7, now=ctx.now)
    return [
        Finding(
            severity=finding.severity,
            check=7,
            message=finding.message,
            line=finding.line,
            hint=finding.hint,
        )
        for finding in findings
        if finding.severity in {"FAIL", "WARN"}
        and "Last Verified" in finding.message
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
    ]
    findings = _required_field_findings(
        section_j,
        payload,
        required_fields,
        check=14,
        label="§J",
    )
    if ctx.now is None:
        return findings

    now_utc = (
        ctx.now.replace(tzinfo=UTC)
        if ctx.now.tzinfo is None
        else ctx.now.astimezone(UTC)
    )
    for field in (
        "last_refresh_date",
        "last_harness_date",
        "first_staleness_detected_at",
    ):
        if payload.get(field) is None:
            continue
        try:
            parsed = _parse_staleness_datetime(payload[field])
        except (TypeError, ValueError, OverflowError):
            continue
        if parsed is not None and parsed > now_utc:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=14,
                    message=f"§J field {field} cannot be in the future",
                    line=section_j.line_start,
                )
            )
    return findings


def check_15_current_staleness(sections: list[Section], ctx: CheckContext) -> list[Finding]:
    if ctx.now is None or ctx.git_head is None:
        return []
    if _section_map(sections).get("J") is None:
        return []
    payload = _get_j_payload(sections, ctx)
    if payload is None:
        return []

    is_stale, triggered_predicates, _, _ = evaluate_staleness(
        sections,
        ctx.now,
        ctx.git_head,
    )
    if not is_stale:
        return []
    return [
        Finding(
            severity="WARN",
            check=15,
            message=(
                "current stale predicates: "
                + ", ".join(triggered_predicates)
                + "; age and escalation are owned by canonical server state"
            ),
            line=_section_map(sections)["J"].line_start,
        )
    ]


# Compatibility import for callers that used the pre-S1413 function name.
check_15_staleness_grace_workflow = check_15_current_staleness


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


def check_21_harness_claim_matches_result(
    sections: list[Section],
    ctx: CheckContext,
) -> list[Finding]:
    section_j = _section_map(sections).get("J")
    payload = _get_j_payload(sections, ctx)
    if section_j is None or payload is None or ctx.readme_path is None:
        return []

    has_score = "last_harness_pass_rate" in payload
    has_date = "last_harness_date" in payload
    if has_score != has_date:
        return [
            Finding(
                severity="FAIL",
                check=21,
                message=(
                    "§J last_harness_pass_rate and last_harness_date must be "
                    "present or omitted together"
                ),
                line=section_j.line_start,
            )
        ]

    newest = newest_harness_result(ctx.readme_path)
    if not has_score and not has_date:
        if newest is None:
            return []
        return [
            Finding(
                severity="FAIL",
                check=21,
                message=(
                    "§J must retain the harness claim pair because a harness "
                    f"result exists for {ctx.readme_path.stem}"
                ),
                line=section_j.line_start,
            )
        ]

    claimed_score = payload["last_harness_pass_rate"]
    claimed_date = payload["last_harness_date"]
    stem = ctx.readme_path.stem
    if newest is None:
        findings: list[Finding] = []
        if claimed_score != PENDING_HARNESS_TOOLING:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=21,
                    message=(
                        "§J claims a measured pass rate but no harness result "
                        f"exists for {stem}"
                    ),
                    line=section_j.line_start,
                )
            )
        if claimed_date is not None:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=21,
                    message=(
                        "§J last_harness_date must be null when no retained "
                        f"harness result exists for {stem}"
                    ),
                    line=section_j.line_start,
                )
            )
        return findings

    result_path, result_payload = newest
    result_value = result_payload.get("result")
    if result_value not in {"PASS", "FAIL", "INFRASTRUCTURE_FAILURE"}:
        raise ValueError(
            f"unsupported harness result value {result_value!r} in {result_path}"
        )

    measured_started_at = result_payload.get("run_started_at")
    date_finding = _harness_date_mismatch_finding(
        section_j,
        claimed_date,
        measured_started_at,
    )
    if result_value == "INFRASTRUCTURE_FAILURE":
        findings = []
        if claimed_score != PENDING_HARNESS_TOOLING:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=21,
                    message=(
                        "§J claims a measured pass rate but newest harness "
                        f"result for {stem} is an infrastructure failure"
                    ),
                    line=section_j.line_start,
                )
            )
        if date_finding is not None:
            findings.append(date_finding)
        return findings

    measured_score = float(result_payload["aggregate_score"])
    findings: list[Finding] = []
    claimed_numeric = (
        float(claimed_score)
        if isinstance(claimed_score, (int, float)) and not isinstance(claimed_score, bool)
        else None
    )
    if claimed_numeric is None or not math.isclose(
        claimed_numeric,
        measured_score,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        findings.append(
            Finding(
                severity="FAIL",
                check=21,
                message=(
                    "§J last_harness_pass_rate "
                    f"claimed {claimed_score!r} but newest harness result measured {measured_score!r}"
                ),
                line=section_j.line_start,
            )
        )

    if date_finding is not None:
        findings.append(date_finding)
    return findings


def check_22_i_example_identity_and_refs(
    sections: list[Section],
    ctx: CheckContext,
) -> list[Finding]:
    del ctx
    section_map = _section_map(sections)
    section_i = section_map.get("I")
    if section_i is None:
        return []
    payload = extract_i_payload(section_i)
    if not isinstance(payload, dict):
        return []
    scenarios = payload.get("scenario_set")
    if not isinstance(scenarios, list):
        return []

    entry_ids: dict[str, set[str]] = {"E": set(), "F": set(), "G": set()}
    section_e = section_map.get("E")
    section_f = section_map.get("F")
    section_g = section_map.get("G")
    if section_e is not None:
        entry_ids["E"] = {
            str(entry.get("id"))
            for entry in extract_e_entries(section_e)
            if isinstance(entry, dict) and entry.get("id") is not None
        }
    if section_f is not None:
        entry_ids["F"] = {
            str(row.get("ID"))
            for row in extract_f_rows(section_f)
            if row.get("ID") is not None
        }
    if section_g is not None:
        entry_ids["G"] = {
            str(entry.get("id"))
            for entry in extract_g_entries(section_g)
            if isinstance(entry, dict) and entry.get("id") is not None
        }

    findings: list[Finding] = []
    seen_ids: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        scenario_id = scenario.get("id")
        if isinstance(scenario_id, str):
            if scenario_id in seen_ids:
                findings.append(
                    Finding(
                        severity="FAIL",
                        check=22,
                        message=f'§I scenario id "{scenario_id}" is duplicated',
                        line=section_i.line_start,
                    )
                )
            seen_ids.add(scenario_id)

        refs = scenario.get("refs")
        if not isinstance(refs, list):
            continue
        for raw_ref in refs:
            if not isinstance(raw_ref, str):
                continue
            ref = raw_ref.strip()
            if CROSS_FILE_REF_RE.fullmatch(ref):
                # Existence belongs to validation against the pinned catalog
                # artifact; local lint only validates deterministic syntax.
                continue
            if ":" in ref:
                findings.append(
                    _invalid_i_ref_finding(
                        section_i,
                        scenario_id,
                        ref,
                        "has invalid cross-file syntax",
                    )
                )
                continue

            entry_match = LOCAL_ENTRY_REF_RE.fullmatch(ref)
            if entry_match is not None:
                letter = entry_match.group(1)
                normalized = ref.removeprefix("§")
                if normalized not in entry_ids[letter]:
                    findings.append(
                        _invalid_i_ref_finding(
                            section_i,
                            scenario_id,
                            ref,
                            "does not resolve within this runbook",
                        )
                    )
                continue

            section_match = LOCAL_SECTION_REF_RE.fullmatch(ref)
            if section_match is not None:
                letter, subsection = section_match.groups()
                target = section_map.get(letter)
                resolves = target is not None and (
                    subsection is None or _subsection_anchor_exists(target, ref)
                )
                if not resolves:
                    findings.append(
                        _invalid_i_ref_finding(
                            section_i,
                            scenario_id,
                            ref,
                            "does not resolve within this runbook",
                        )
                    )
                continue

            findings.append(
                _invalid_i_ref_finding(
                    section_i,
                    scenario_id,
                    ref,
                    "is not a supported local or cross-file reference",
                )
            )
    return findings


def check_23_e_operation_ids_unique(
    sections: list[Section],
    ctx: CheckContext,
) -> list[Finding]:
    del ctx
    section_e = _section_map(sections).get("E")
    if section_e is None:
        return []
    seen: set[str] = set()
    findings: list[Finding] = []
    for entry in extract_e_entries(section_e):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            continue
        entry_id = entry["id"]
        if entry_id in seen:
            findings.append(
                Finding(
                    severity="FAIL",
                    check=23,
                    message=f'§E operation id "{entry_id}" is duplicated',
                    line=section_e.line_start,
                )
            )
        seen.add(entry_id)
    return findings


def check_24_no_unresolved_placeholders(
    sections: list[Section],
    ctx: CheckContext,
) -> list[Finding]:
    """Reject every complete placeholder token in current document content."""

    del sections
    if ctx.raw_markdown is None:
        return []
    active_text = parse_markdown_document(ctx.raw_markdown).active_text
    findings: list[Finding] = []
    for match in UNRESOLVED_PLACEHOLDER_RE.finditer(active_text):
        findings.append(
            Finding(
                severity="FAIL",
                check=24,
                message=f"unresolved placeholder: {match.group(0)}",
                line=active_text.count("\n", 0, match.start()) + 1,
            )
        )
    return findings


def _harness_date_mismatch_finding(
    section_j: Section,
    claimed_date: object,
    measured_started_at: object,
) -> Finding | None:
    try:
        claimed_at = _parse_staleness_datetime(claimed_date)
    except (TypeError, ValueError, OverflowError):
        claimed_at = None
    try:
        measured_at = _parse_staleness_datetime(measured_started_at)
    except (TypeError, ValueError, OverflowError):
        measured_at = None
    if claimed_at is not None and measured_at is not None and claimed_at == measured_at:
        return None
    return Finding(
        severity="FAIL",
        check=21,
        message=(
            "§J last_harness_date "
            f"claimed {_normalize_iso_value(claimed_date)!r} "
            f"but newest harness result measured {measured_started_at!r}"
        ),
        line=section_j.line_start,
    )


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
    check_14_lifecycle_fields,
    check_15_current_staleness,
    check_16_linter_version_compat,
    check_17_conformance_fields,
    check_18_retrofit_fields,
    check_19_header_required_fields,
    check_20_b_exact_columns,
    check_21_harness_claim_matches_result,
    check_22_i_example_identity_and_refs,
    check_23_e_operation_ids_unique,
    check_24_no_unresolved_placeholders,
]

DETERMINISTIC_CONFORMANCE_CHECKS: list[CheckFn] = [
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
    check_16_linter_version_compat,
    check_17_conformance_fields,
    check_18_retrofit_fields,
    check_19_header_required_fields,
    check_20_b_exact_columns,
    check_22_i_example_identity_and_refs,
    check_23_e_operation_ids_unique,
    check_24_no_unresolved_placeholders,
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


def _invalid_i_ref_finding(
    section_i: Section,
    scenario_id: object,
    ref: str,
    reason: str,
) -> Finding:
    return Finding(
        severity="FAIL",
        check=22,
        message=f'§I scenario {scenario_id or "<unknown>"} ref "{ref}" {reason}',
        line=section_i.line_start,
    )


def _subsection_anchor_exists(section: Section, ref: str) -> bool:
    heading_re = re.compile(rf"^#{{3,6}}\s+{re.escape(ref)}(?:\s|$)")
    return any(heading_re.match(line) for line in section.raw_markdown.splitlines())


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


def _required_field_findings(
    section: Section,
    payload: dict[str, Any],
    required_fields: list[str],
    *,
    check: int,
    label: str,
) -> list[Finding]:
    nullable_fields = {
        "§J": {"last_harness_date", "first_staleness_detected_at"},
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
