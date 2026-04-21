from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


Severity = Literal["FAIL", "WARN", "INFO"]


@dataclass(slots=True)
class Finding:
    severity: Severity
    check: int
    message: str
    line: int | None = None
    hint: str | None = None


@dataclass(slots=True)
class CheckContext:
    schemas_dir: Path
    readme_path: Path | None
    mode: str
    frontmatter: dict | None
    git_head: str | None = None
    now: datetime | None = None
    update_lifecycle: bool = False
    form_cache: dict[str, Any] = field(default_factory=dict)


def retag_findings(findings: list[Finding], *, check: int) -> list[Finding]:
    return [replace(finding, check=check) for finding in findings]
