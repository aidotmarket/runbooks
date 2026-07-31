from __future__ import annotations

from datetime import datetime
from pathlib import Path

from runbook_tools.frontmatter import CATALOG_METADATA_FIELDS
from runbook_tools.lint import CheckContext, Finding
from runbook_tools.lint.checks import DETERMINISTIC_CONFORMANCE_CHECKS
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter


def structural_conformance_failures(
    markdown_text: str,
    schemas_dir: Path,
    *,
    now: datetime | None = None,
) -> list[Finding]:
    """Return deterministic structural/form failures for one Markdown blob.

    This deliberately excludes artifact-backed harness claims and server-owned
    staleness escalation. Callers may supply a trusted clock to reject future
    lifecycle evidence. Pinned validators supply the immutable commit clock.
    """

    frontmatter = extract_yaml_frontmatter(markdown_text)
    if frontmatter is not None:
        frontmatter = {
            key: value
            for key, value in frontmatter.items()
            if key not in CATALOG_METADATA_FIELDS
        }
    context = CheckContext(
        schemas_dir=schemas_dir.resolve(),
        readme_path=None,
        mode="strict",
        frontmatter=frontmatter,
        git_head=None,
        now=now,
        raw_markdown=markdown_text,
    )
    sections = extract_sections(markdown_text)
    findings: list[Finding] = []
    for check in DETERMINISTIC_CONFORMANCE_CHECKS:
        findings.extend(check(sections, context))
    return [finding for finding in findings if finding.severity == "FAIL"]
