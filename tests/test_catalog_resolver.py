from __future__ import annotations

from pathlib import Path
import subprocess

import pytest
import yaml

from runbook_tools.catalog.generator import generate_catalog
from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.resolver import resolve_catalog_key


def _repository(root: Path) -> tuple[str, str]:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    metadata = {
        "runbook_id": "member",
        "domain": "test-domain",
        "status": "ACTIVE",
        "authoritative_for": [{"topic": "member-topic", "section": "Overview"}],
        "aliases": ["member-alias"],
        "error_signatures": [{"signature": "Exact Error", "section": "Repair"}],
        "supersedes": [],
        "superseded_by": [],
        "owner": "test-owner",
        "last_verified_at": "2026-07-17",
    }
    path = root / "runbooks" / "member.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False)
        + "---\n\n# Member\n\n## Overview\n\nOverview.\n\n## Repair\n\nRepair.\n"
    )
    (root / "README.md").write_text(
        "# Fixture\n\n## Adoption status\n\n"
        "| System | Runbook | Status |\n|---|---|---|\n| None | — | NOT_STARTED |\n\n"
        "## Status values\n\nFixture.\n"
    )
    generate_catalog(root)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    return sha, f"git:aidotmarket/runbooks@{sha}:CATALOG.json"


@pytest.mark.parametrize(
    ("query", "match_type", "section"),
    [
        ("member", "runbook_id", "Overview"),
        ("member-alias", "alias", "Overview"),
        ("member-topic", "topic", "Overview"),
        ("Exact Error", "error_signature", "Repair"),
    ],
)
def test_resolves_id_alias_topic_and_exact_error_at_full_sha(
    tmp_path: Path, query: str, match_type: str, section: str
) -> None:
    sha, catalog_ref = _repository(tmp_path)

    resolved = resolve_catalog_key(tmp_path, catalog_ref, query)

    assert resolved == {
        "catalog_sha": sha,
        "match_type": match_type,
        "path": "runbooks/member.md",
        "query": query,
        "runbook_id": "member",
        "section": section,
    }


@pytest.mark.parametrize(
    "query",
    ["missing", "exact error", "member.md", "runbooks/member.md", "archive/member.md"],
)
def test_missing_uncataloged_and_path_or_basename_queries_have_no_fallback(
    tmp_path: Path, query: str
) -> None:
    _, catalog_ref = _repository(tmp_path)

    with pytest.raises(CatalogError, match="catalog key not found"):
        resolve_catalog_key(tmp_path, catalog_ref, query)


@pytest.mark.parametrize(
    "catalog_ref",
    [
        "git:aidotmarket/runbooks@main:CATALOG.json",
        "git:aidotmarket/runbooks@0123456:CATALOG.json",
        f"git:aidotmarket/runbooks@{'F' * 40}:CATALOG.json",
        f"git:aidotmarket/runbooks@{'f' * 40}:OTHER.json",
    ],
)
def test_resolver_rejects_floating_short_uppercase_and_alternate_filename(
    tmp_path: Path, catalog_ref: str
) -> None:
    with pytest.raises(CatalogError, match="40-lowercase-hex"):
        resolve_catalog_key(tmp_path, catalog_ref, "member")
