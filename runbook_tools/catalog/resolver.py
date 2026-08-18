from __future__ import annotations

from pathlib import Path
from typing import Any

from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.validator import load_validated_catalog


def resolve_catalog_key(repo_root: Path, catalog_ref: str, query: str) -> dict[str, Any]:
    validated = load_validated_catalog(repo_root, catalog_ref)
    catalog = validated.catalog
    entries = {
        entry["runbook_id"]: entry
        for entry in catalog["entries"]
        if isinstance(entry, dict)
        and entry.get("status") == "ACTIVE"
        and isinstance(entry.get("runbook_id"), str)
    }

    match_type: str | None = None
    runbook_id: str | None = None
    section: str | None = None
    section_id: str | None = None
    if query in entries:
        match_type = "runbook_id"
        runbook_id = query
        authorities = entries[query].get("authoritative_for", [])
        if authorities:
            section = authorities[0].get("section")
            section_id = authorities[0].get("section_id")
    else:
        for entry in entries.values():
            if query in entry["aliases"]:
                target = entry["authoritative_for"][0]
                match_type = "alias"
            else:
                target = next(
                    (
                        row
                        for row in entry["authoritative_for"]
                        if row["topic"] == query
                    ),
                    None,
                )
                if target is not None:
                    match_type = "topic"
                else:
                    target = next(
                        (
                            row
                            for row in entry["error_signatures"]
                            if row["signature"] == query
                        ),
                        None,
                    )
                    if target is not None:
                        match_type = "error_signature"
            if target is not None:
                runbook_id = entry["runbook_id"]
                section = target["section"]
                section_id = target.get("section_id")
                break

    if match_type is None or runbook_id is None or section is None:
        raise CatalogError(f"catalog key not found: {query!r}")
    entry = entries[runbook_id]
    result = {
        "catalog_sha": validated.report.catalog_sha,
        "match_type": match_type,
        "path": entry["path"],
        "query": query,
        "runbook_id": runbook_id,
        "section": section,
    }
    if section_id is not None:
        result["section_id"] = section_id
    return result
