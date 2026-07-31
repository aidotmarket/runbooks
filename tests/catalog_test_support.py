from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).parent.parent
CONFORMANT_FIXTURE = Path(__file__).parent / "fixtures" / "conformant.md"


def ensure_catalog_schemas(root: Path) -> None:
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas", dirs_exist_ok=True)


def conformant_catalog_document(
    metadata: dict[str, Any],
    *,
    title: str = "Fixture",
    overview_body: str | None = "Fixture body.",
    section_bodies: dict[str, str] | None = None,
) -> str:
    """Add catalog metadata/content to the canonical conformant A-K fixture."""

    source = CONFORMANT_FIXTURE.read_text()
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", source, re.DOTALL)
    assert match is not None
    frontmatter = yaml.safe_load(match.group(1))
    assert isinstance(frontmatter, dict)
    frontmatter.update(metadata)
    body = source[match.end() :]
    body = re.sub(r"^# .+$", f"# {title}", body, count=1, flags=re.MULTILINE)

    declared_sections = [
        row["section"]
        for collection in ("authoritative_for", "error_signatures")
        for row in metadata.get(collection, [])
        if isinstance(row, dict) and isinstance(row.get("section"), str)
    ]
    renamed: dict[str, str] = {}
    for section in declared_sections:
        if section.startswith("§E.") and section != "§E. Operate":
            renamed["§E. Operate"] = section
    for old, new in renamed.items():
        body = body.replace(f"## {old}", f"## {new}", 1)

    for section, content in (section_bodies or {}).items():
        effective = renamed.get(section, section)
        marker = f"## {effective}\n"
        assert marker in body, effective
        body = body.replace(marker, f"{marker}\n{content.rstrip()}\n", 1)

    if overview_body is not None:
        body = body.rstrip() + f"\n\n## Overview\n\n{overview_body.rstrip()}\n"

    anchored: set[tuple[str, str]] = set()
    for collection in ("authoritative_for", "error_signatures"):
        for row in metadata.get(collection, []):
            if not isinstance(row, dict) or "section_id" not in row:
                continue
            section = renamed.get(row["section"], row["section"])
            identity = (section, row["section_id"])
            if identity in anchored:
                continue
            anchored.add(identity)
            marker = f"## {section}"
            anchor = f'<a id="rb-section-{row["section_id"]}"></a>\n'
            body = body.replace(marker, anchor + marker, 1)

    return (
        "---\n"
        + yaml.safe_dump(frontmatter, sort_keys=False)
        + "---\n\n"
        + body.lstrip()
    )
