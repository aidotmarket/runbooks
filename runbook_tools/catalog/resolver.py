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
        if isinstance(entry, dict) and isinstance(entry.get("runbook_id"), str)
    }

    match_type: str | None = None
    runbook_id: str | None = None
    section: str | None = None
    if query in entries:
        match_type = "runbook_id"
        runbook_id = query
        authorities = entries[query].get("authoritative_for", [])
        section = authorities[0].get("section") if authorities else None
    else:
        for index_name, label in (
            ("aliases", "alias"),
            ("topics", "topic"),
            ("error_signatures", "error_signature"),
        ):
            target = catalog["indexes"][index_name].get(query)
            if target is not None:
                match_type = label
                runbook_id = target["runbook_id"]
                section = target["section"]
                break

    if match_type is None or runbook_id is None or section is None:
        raise CatalogError(f"catalog key not found: {query!r}")
    entry = entries[runbook_id]
    return {
        "catalog_sha": validated.report.catalog_sha,
        "match_type": match_type,
        "path": entry["path"],
        "query": query,
        "runbook_id": runbook_id,
        "section": section,
    }
