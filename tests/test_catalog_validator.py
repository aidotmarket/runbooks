from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from runbook_tools.catalog.generator import generate_catalog
from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.validator import parse_catalog_ref, validate_catalog_ref


KERNEL_FIXTURES = Path(__file__).parent / "fixtures" / "catalog" / "kernel_companions"


def _metadata(runbook_id: str, *, topic: str | None = None) -> dict:
    return {
        "runbook_id": runbook_id,
        "domain": "test-domain",
        "status": "ACTIVE",
        "authoritative_for": [
            {"topic": topic or f"{runbook_id}-topic", "section": "Overview"}
        ],
        "aliases": [],
        "error_signatures": [],
        "supersedes": [],
        "superseded_by": [],
        "owner": "test-owner",
        "last_verified_at": "2026-07-17",
    }


def _write_doc(root: Path, relative: str, metadata: dict | None, body: str = "Fixture body.") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = ""
    if metadata is not None:
        frontmatter = "---\n" + yaml.safe_dump(metadata, sort_keys=False) + "---\n\n"
    path.write_text(frontmatter + f"# Fixture\n\n## Overview\n\n{body}\n")
    return path


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    (root / "README.md").write_text(
        "# Fixture\n\n## Adoption status\n\n"
        "| System | Runbook | Status |\n|---|---|---|\n| None | — | NOT_STARTED |\n\n"
        "## Status values\n\nFixture.\n"
    )


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _generate_commit(root: Path, message: str = "fixture") -> tuple[str, str]:
    generate_catalog(root)
    sha = _commit(root, message)
    return sha, f"git:aidotmarket/runbooks@{sha}:CATALOG.json"


def _valid_repo(tmp_path: Path) -> tuple[Path, str, str]:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    metadata["aliases"] = ["member-alias"]
    metadata["error_signatures"] = [{"signature": "EXACT_ERROR", "section": "Overview"}]
    _write_doc(tmp_path, "runbooks/member.md", metadata)
    sha, ref = _generate_commit(tmp_path)
    return tmp_path, sha, ref


def test_pinned_validation_records_full_sha_digest_and_all_sections(tmp_path: Path) -> None:
    root, sha, catalog_ref = _valid_repo(tmp_path)

    report = validate_catalog_ref(root, catalog_ref)

    assert report.status == "pass"
    assert report.catalog_sha == sha
    assert len(report.catalog_sha) == 40
    assert len(report.catalog_digest) == 64
    assert report.checked_entry_count == 1
    assert report.checked_section_count == 2


@pytest.mark.parametrize(
    "catalog_ref",
    [
        "git:aidotmarket/runbooks@main:CATALOG.json",
        "git:aidotmarket/runbooks@abc1234:CATALOG.json",
        f"git:aidotmarket/runbooks@{'A' * 40}:CATALOG.json",
        f"git:aidotmarket/runbooks@{'a' * 40}:RUNBOOK-CATALOG.json",
        f"git:other/runbooks@{'a' * 40}:CATALOG.json",
    ],
)
def test_pin_grammar_rejects_floating_short_uppercase_and_alternate_refs(catalog_ref: str) -> None:
    with pytest.raises(CatalogError, match="40-lowercase-hex"):
        parse_catalog_ref(catalog_ref)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "authoritative_for",
            [{"topic": "shared-topic", "section": "Overview"}],
            "duplicate topic",
        ),
        (
            "error_signatures",
            [{"signature": "SHARED_ERROR", "section": "Overview"}],
            "duplicate error signature",
        ),
        ("aliases", ["member"], "duplicate runbook id/alias"),
    ],
)
def test_authority_and_identity_conflicts_fail_atomically(
    tmp_path: Path, field: str, value: list, message: str
) -> None:
    root, _, _ = _valid_repo(tmp_path)
    first = yaml.safe_load((root / "runbooks/member.md").read_text().split("---", 2)[1])
    if field == "authoritative_for":
        first[field] = value
    elif field == "error_signatures":
        first[field] = value
    second = _metadata("second", topic="shared-topic" if field == "authoritative_for" else None)
    if field == "error_signatures":
        first[field] = value
        second[field] = value
    if field == "aliases":
        second[field] = value
    _write_doc(root, "runbooks/member.md", first)
    _write_doc(root, "runbooks/second.md", second)
    sha = _commit(root, "invalid conflict")

    with pytest.raises(CatalogError, match=message):
        validate_catalog_ref(root, f"git:aidotmarket/runbooks@{sha}:CATALOG.json")


def test_duplicate_active_basename_fails(tmp_path: Path) -> None:
    root, _, _ = _valid_repo(tmp_path)
    _write_doc(root, "member.md", _metadata("other-member"))
    sha = _commit(root, "duplicate basename")

    with pytest.raises(CatalogError, match="duplicate ACTIVE basename"):
        validate_catalog_ref(root, f"git:aidotmarket/runbooks@{sha}:CATALOG.json")


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("archive/member.md", "outside bounded roots"),
        ("runbooks/missing.md", "missing at pinned SHA"),
        ("../member.md", "outside bounded roots"),
    ],
)
def test_archive_missing_and_escaping_active_paths_fail(
    tmp_path: Path, replacement: str, message: str
) -> None:
    root, _, _ = _valid_repo(tmp_path)
    catalog_path = root / "CATALOG.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["entries"][0]["path"] = replacement
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n")
    sha = _commit(root, "invalid path")

    with pytest.raises(CatalogError, match=message):
        validate_catalog_ref(root, f"git:aidotmarket/runbooks@{sha}:CATALOG.json")


def test_dangling_section_and_frontmatter_catalog_drift_fail(tmp_path: Path) -> None:
    root, _, _ = _valid_repo(tmp_path)
    path = root / "runbooks/member.md"
    text = path.read_text().replace("section: Overview", "section: Missing")
    path.write_text(text)
    generate_catalog(root)
    sha = _commit(root, "dangling section")
    with pytest.raises(CatalogError, match="dangling section"):
        validate_catalog_ref(root, f"git:aidotmarket/runbooks@{sha}:CATALOG.json")

    path.write_text(path.read_text().replace("section: Missing", "section: Overview"))
    sha = _commit(root, "catalog drift")
    with pytest.raises(CatalogError, match="differs from ACTIVE frontmatter"):
        validate_catalog_ref(root, f"git:aidotmarket/runbooks@{sha}:CATALOG.json")


@pytest.mark.parametrize(
    "claim",
    [
        "Vulcan assigns work to Mars and approves Mars output.",
        "The primary slot directs the worker slot.",
        "Active Council voters: MP, AG, and XAI.",
    ],
)
def test_stale_active_claim_fails_and_explicit_historical_span_passes(
    tmp_path: Path, claim: str
) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), claim)
    _, invalid_ref = _generate_commit(tmp_path, "active stale claim")
    with pytest.raises(CatalogError, match="stale active claim"):
        validate_catalog_ref(tmp_path, invalid_ref)

    _write_doc(
        tmp_path,
        "runbooks/member.md",
        _metadata("member"),
        f"<!-- catalog:historical -->\n{claim}\n<!-- /catalog:historical -->",
    )
    _, valid_ref = _generate_commit(tmp_path, "historical claim")
    assert validate_catalog_ref(tmp_path, valid_ref).status == "pass"


def test_stale_scan_applies_only_to_active_catalog_members(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    stale_claim = "Active Council voters: MP, AG, and XAI."
    _write_doc(tmp_path, "legacy.md", None, stale_claim)
    _, grandfathered_ref = _generate_commit(tmp_path, "grandfathered stale prose")
    assert validate_catalog_ref(tmp_path, grandfathered_ref).status == "pass"

    _write_doc(tmp_path, "legacy.md", _metadata("legacy"), stale_claim)
    _, active_ref = _generate_commit(tmp_path, "promoted stale prose")
    with pytest.raises(CatalogError, match="stale active claim"):
        validate_catalog_ref(tmp_path, active_ref)

    _write_doc(
        tmp_path,
        "legacy.md",
        _metadata("legacy"),
        "<!-- catalog:historical -->\n" + stale_claim + "\n<!-- /catalog:historical -->",
    )
    _, historical_ref = _generate_commit(tmp_path, "promoted historical prose")
    assert validate_catalog_ref(tmp_path, historical_ref).status == "pass"


@pytest.mark.parametrize(
    "body",
    [
        "<!-- catalog:historical -->\nunclosed",
        "<!-- /catalog:historical -->",
        "<!-- catalog:historical -->\n<!-- catalog:historical -->\nnested\n<!-- /catalog:historical -->",
    ],
)
def test_malformed_historical_markers_fail(tmp_path: Path, body: str) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), body)
    _, catalog_ref = _generate_commit(tmp_path)

    with pytest.raises(CatalogError, match="historical"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_all_seven_kernel_companions_generate_and_validate_at_one_pin(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    for source in KERNEL_FIXTURES.glob("*.md"):
        shutil.copy2(source, tmp_path / source.name)
    sha, catalog_ref = _generate_commit(tmp_path, "kernel companions")

    report = validate_catalog_ref(tmp_path, catalog_ref)

    assert report.catalog_sha == sha
    assert report.checked_entry_count == 7
    assert report.checked_section_count == 7
