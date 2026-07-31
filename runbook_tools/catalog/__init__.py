"""Deterministic catalog generation for ACTIVE runbooks.

Generator imports are intentionally lazy: section parsing is a lower-level
dependency of lint conformance, which catalog generation also invokes.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from runbook_tools.catalog.model import CatalogError

CATALOG_PATH = "CATALOG.json"
ROUTER_PATH = "TOPIC-ROUTER.md"
README_PATH = "README.md"


def generate_catalog(
    repo_root: Path,
    *,
    current_utc_date: date | None = None,
) -> dict[str, bytes]:
    from runbook_tools.catalog.generator import generate_catalog as implementation

    return implementation(repo_root, current_utc_date=current_utc_date)


def check_catalog(
    repo_root: Path,
    *,
    current_utc_date: date | None = None,
) -> list[str]:
    from runbook_tools.catalog.generator import check_catalog as implementation

    return implementation(repo_root, current_utc_date=current_utc_date)


def render_outputs(
    repo_root: Path,
    *,
    current_utc_date: date | None = None,
) -> dict[str, bytes]:
    from runbook_tools.catalog.generator import render_outputs as implementation

    return implementation(repo_root, current_utc_date=current_utc_date)


__all__ = [
    "CATALOG_PATH",
    "README_PATH",
    "ROUTER_PATH",
    "CatalogError",
    "check_catalog",
    "generate_catalog",
    "render_outputs",
]
