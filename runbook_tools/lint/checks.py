from __future__ import annotations

from typing import Any

from runbook_tools.lint import CheckContext, Finding, retag_findings
from runbook_tools.lint.forms import (
    collect_b_rule_findings,
    extract_b_rows,
    extract_c_rows,
    extract_f_rows,
    extract_g_entries,
    extract_j_payload,
    extract_k_payload,
    validate_a,
    validate_form,
)
from runbook_tools.parser.sections import Section


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
    payload = extract_j_payload(section_j) if section_j is not None else None
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
    payload = extract_k_payload(section_k) if section_k is not None else None
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


CHECKS_BUILD2 = [
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


def _section_map(sections: list[Section]) -> dict[str, Section]:
    return {section.letter: section for section in sections}


def _line_for_row(section: Section, row: dict[str, str]) -> int | None:
    for value in row.values():
        if value:
            for index, line in enumerate(section.raw_markdown.splitlines(), start=section.line_start):
                if value in line:
                    return index
    return section.line_start
