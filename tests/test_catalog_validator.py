from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

import pytest
import yaml

import runbook_tools.catalog.generator as catalog_generator
import runbook_tools.catalog.validator as catalog_validator
from runbook_tools.catalog.generator import generate_catalog
from runbook_tools.catalog.model import CatalogError
from runbook_tools.lint.conformance import structural_conformance_failures
from runbook_tools.catalog.search import search_catalog
from runbook_tools.catalog.sections import parse_markdown_document
from runbook_tools.catalog.validator import (
    _stale_claim_errors,
    parse_catalog_ref,
    validate_catalog_ref,
)
from runbook_tools.corpus_manifest import PURPOSE, SOURCE_SELECTOR
from tests.catalog_test_support import (
    conformant_catalog_document,
    ensure_catalog_schemas,
)

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
        "owner": "sysadmin",
        "owner_agent": "sysadmin",
        "last_verified_at": "2026-07-17",
    }


def _write_doc(root: Path, relative: str, metadata: dict | None, body: str = "Fixture body.") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_catalog_schemas(root)
    if metadata is None:
        path.write_text(f"# Fixture\n\n## Overview\n\n{body}\n")
    else:
        path.write_text(
            conformant_catalog_document(metadata, overview_body=body)
        )
    return path


def _init_repo(root: Path) -> None:
    ensure_catalog_schemas(root)
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


def _generate_search_commit(root: Path, message: str) -> tuple[str, str]:
    """Commit one valid immutable corpus snapshot for search-specific fixtures."""

    inventory_sha, _ = _generate_commit(root, message)
    path = "runbooks/member.md"
    blob_oid = subprocess.run(
        ["git", "rev-parse", f"{inventory_sha}:{path}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = {
        "manifest_version": 2,
        "purpose": PURPOSE,
        "inventory": {
            "repository": "aidotmarket/runbooks",
            "base_sha": inventory_sha,
            "inventory_sha": inventory_sha,
            "blob_oid_scope": "Pinned inventory tree blob.",
            "inventory_path_semantics": (
                "inventory_path selects the pinned tree path."
            ),
            "source_selector": SOURCE_SELECTOR,
            "refresh_required_before_execution": True,
            "counts": {
                "operational_documents": 1,
                "source_documents": 1,
                "active": 1,
                "grandfathered": 0,
                "archived": 0,
            },
        },
        "policy": {
            "pending_is_not_authority": True,
            "manifest_grants_no_authority": True,
            "archive_is_recoverable": True,
            "promotion_requires_ground_truth_verification": True,
            "merge_or_archive_requires_section_coverage": True,
            "high_risk_requires_independent_review": True,
        },
        "risk_scale": {
            risk: f"Fixture definition for {risk}."
            for risk in ("P0", "P1", "P2", "P3")
        },
        "documents": [
            {
                "path": path,
                "git_blob_oid": blob_oid,
                "catalog_state": "active",
                "status": "active",
                "proposed_disposition": "retain_active",
                "batch": "validator-fixture",
                "risk": "P3",
                "target_paths": [path],
                "evidence": [],
                "verify_against": ["fixture source text"],
                "independent_review_required": False,
            }
        ],
    }
    (root / "CORPUS-MANIFEST.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False)
    )
    search_sha = _commit(root, "pinned corpus manifest")
    return search_sha, f"git:aidotmarket/runbooks@{search_sha}:CATALOG.json"


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

    assert report.status == "integrity_pass_unverified"
    assert report.catalog_sha == sha
    assert len(report.catalog_sha) == 40
    assert len(report.catalog_digest) == 64
    assert report.checked_entry_count == 1
    assert report.checked_section_count == 2
    assert report.integrity_only is True
    assert report.semantic_verification is False
    assert report.authority_admission is False
    assert report.action_authority_eligible is False


def test_pinned_validator_requires_catalog_v3_integrity_only_labels(
    tmp_path: Path,
) -> None:
    root, sha, _catalog_ref = _valid_repo(tmp_path)
    catalog = json.loads(catalog_validator._git_show(root, sha, "CATALOG.json"))
    tree_paths = catalog_validator._git_tree_paths(root, sha)
    labels = (
        "integrity_only",
        "semantic_verification",
        "authority_admission",
        "action_authority_eligible",
    )

    wrong_version = json.loads(json.dumps(catalog))
    wrong_version["schema_version"] = 1
    errors, _ = catalog_validator._validate_pinned_entries(
        wrong_version,
        tree_paths,
        lambda path: catalog_validator._git_show(root, sha, path),
    )
    assert "schema_version must be 3" in errors

    for scope, field in (
        *(("catalog", field) for field in ("status", *labels)),
        *(("entry", field) for field in ("integrity_status", *labels)),
    ):
        malformed = json.loads(json.dumps(catalog))
        target = malformed if scope == "catalog" else malformed["entries"][0]
        target.pop(field)
        errors, _ = catalog_validator._validate_pinned_entries(
            malformed,
            tree_paths,
            lambda path: catalog_validator._git_show(root, sha, path),
        )
        assert any(field in error for error in errors)


def test_pinned_validation_materializes_new_nested_source_directories(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    _write_doc(
        tmp_path,
        "docs/new-operational-note.MD",
        None,
        body="Unknown source directories default into corpus adjudication.",
    )
    _, catalog_ref = _generate_commit(tmp_path, "nested source fixture")

    report = validate_catalog_ref(tmp_path, catalog_ref)

    assert report.status == "integrity_pass_unverified"
    assert report.checked_entry_count == 2


def test_pinned_validation_admits_root_file_with_venv_prefix(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    _write_doc(
        tmp_path,
        ".venv-recovery.MD",
        None,
        body="A filename prefix must not masquerade as an excluded environment tree.",
    )
    _, catalog_ref = _generate_commit(tmp_path, "venv-prefixed source fixture")

    report = validate_catalog_ref(tmp_path, catalog_ref)

    assert report.status == "integrity_pass_unverified"
    assert report.checked_entry_count == 2


def test_pinned_validation_rejects_symlink_source_blob(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    target = _write_doc(tmp_path, "specs/target.md", None)
    source = tmp_path / "docs" / "current.md"
    source.parent.mkdir()
    source.symlink_to(target)

    # Build the expected generated projections while the source is a regular
    # file, then preserve those exact bytes while committing it as a symlink.
    source.unlink()
    source.write_text(target.read_text())
    generate_catalog(tmp_path)
    source.unlink()
    source.symlink_to(target)
    sha = _commit(tmp_path, "symlink source fixture")
    catalog_ref = f"git:aidotmarket/runbooks@{sha}:CATALOG.json"

    with pytest.raises(CatalogError, match="not a regular file"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_pinned_validation_rejects_symlink_that_could_hide_source_tree(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    target = _write_doc(tmp_path, "specs/target.md", None).parent

    # Preserve projections generated without the link. A Git snapshot records
    # only a symlink blob, so a validator must not assume that a suffix-less
    # entry such as ``docs`` is harmless or know what it resolves to at checkout.
    generate_catalog(tmp_path)
    (tmp_path / "docs").symlink_to(target, target_is_directory=True)
    sha = _commit(tmp_path, "symlink source-tree fixture")
    catalog_ref = f"git:aidotmarket/runbooks@{sha}:CATALOG.json"

    with pytest.raises(CatalogError, match="not a regular file"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_pinned_validation_ignores_local_git_replacement_refs(tmp_path: Path) -> None:
    root, original_sha, original_ref = _valid_repo(tmp_path)
    original_catalog = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "show",
            f"{original_sha}:CATALOG.json",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout

    replacement_metadata = _metadata("member", topic="replacement-only-topic")
    replacement_metadata["aliases"] = ["replacement-only-alias"]
    _write_doc(
        root,
        "runbooks/member.md",
        replacement_metadata,
        body="Replacement-only catalog bytes.",
    )
    replacement_sha, _ = _generate_commit(root, "replacement fixture")
    replacement_catalog = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "show",
            f"{replacement_sha}:CATALOG.json",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    assert replacement_catalog != original_catalog
    subprocess.run(
        ["git", "replace", original_sha, replacement_sha],
        cwd=root,
        check=True,
    )

    report = validate_catalog_ref(root, original_ref)

    assert report.catalog_sha == original_sha
    assert report.catalog_digest == hashlib.sha256(original_catalog).hexdigest()


def test_pinned_cross_file_ref_rejects_missing_runbook_without_worktree_fallback(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    source = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    source.write_text(
        source.read_text().replace(
            "refs: [E-01]",
            "refs: [E-01, missing-runbook:E-99]",
            1,
        )
    )
    _, catalog_ref = _generate_commit(tmp_path, "missing pinned runbook ref")

    # A matching working-tree document must not repair the immutable pin.
    fallback = _write_doc(
        tmp_path,
        "runbooks/missing-runbook.md",
        _metadata("missing-runbook"),
    )
    fallback.write_text(fallback.read_text().replace("id: E-01", "id: E-99", 1))

    with pytest.raises(CatalogError, match=r"missing-runbook:E-99.*absent from the pinned catalog"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_pinned_cross_file_ref_rejects_missing_target_without_worktree_fallback(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    source = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    source.write_text(
        source.read_text().replace(
            "refs: [E-01]",
            "refs: [E-01, target-runbook:E-99]",
            1,
        )
    )
    target = _write_doc(
        tmp_path,
        "runbooks/target-runbook.md",
        _metadata("target-runbook"),
    )
    _, catalog_ref = _generate_commit(tmp_path, "missing pinned target ref")

    # The target exists only after the pin in the working tree. Validation must
    # continue to observe the pinned E-01 form, never this E-99 replacement.
    target.write_text(target.read_text().replace("id: E-01", "id: E-99", 1))

    with pytest.raises(CatalogError, match=r"target-runbook:E-99.*does not resolve in pinned"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_pinned_cross_file_refs_resolve_entry_section_and_subsection_targets(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    source = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    source.write_text(
        source.read_text().replace(
            "refs: [E-01]",
            "refs: [E-01, target-runbook:E-01, target-runbook:I-01, target-runbook:§D, target-runbook:§H.2]",
            1,
        )
    )
    _write_doc(
        tmp_path,
        "runbooks/target-runbook.md",
        _metadata("target-runbook"),
    )
    _, catalog_ref = _generate_commit(tmp_path, "valid pinned cross refs")

    assert validate_catalog_ref(tmp_path, catalog_ref).status == "integrity_pass_unverified"


@pytest.mark.parametrize(
    ("target", "limit"),
    [
        ("CATALOG.json", catalog_validator.MAX_PINNED_CATALOG_BYTES),
        (
            "schemas/section_e_operate.schema.json",
            catalog_validator.MAX_PINNED_SCHEMA_BYTES,
        ),
        (
            "runbooks/member.md",
            catalog_validator.MAX_PINNED_MARKDOWN_BYTES,
        ),
    ],
)
def test_pinned_blob_size_is_checked_before_content_is_materialized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    limit: int,
) -> None:
    root, _, catalog_ref = _valid_repo(tmp_path)
    original_size = catalog_validator._git_blob_size
    original_show = catalog_validator._git_show
    materialized: list[str] = []

    def reported_size(repo_root: Path, sha: str, path: str) -> int:
        if path == target:
            return limit + 1
        return original_size(repo_root, sha, path)

    def observed_show(repo_root: Path, sha: str, path: str) -> bytes:
        materialized.append(path)
        return original_show(repo_root, sha, path)

    monkeypatch.setattr(catalog_validator, "_git_blob_size", reported_size)
    monkeypatch.setattr(catalog_validator, "_git_show", observed_show)

    with pytest.raises(CatalogError, match=re.escape(target) + r".*pinned"):
        validate_catalog_ref(root, catalog_ref)

    assert materialized == []


def test_pinned_snapshot_aggregate_is_checked_before_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _, catalog_ref = _valid_repo(tmp_path)
    materialized: list[str] = []

    def observed_show(repo_root: Path, sha: str, path: str) -> bytes:
        materialized.append(path)
        raise AssertionError("content must not be read before aggregate preflight")

    monkeypatch.setattr(
        catalog_validator,
        "_git_blob_size",
        lambda repo_root, sha, path: 1_200_000,
    )
    monkeypatch.setattr(catalog_validator, "_git_show", observed_show)

    with pytest.raises(CatalogError, match="aggregate limit"):
        validate_catalog_ref(root, catalog_ref)

    assert materialized == []


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
    if field == "authoritative_for" or field == "error_signatures":
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


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("member.md", "must be canonical 'runbooks/member.md'"),
        ("runbooks/wrong-name.md", "must be canonical 'runbooks/member.md'"),
        ("runbooks/nested/member.md", "must be canonical 'runbooks/member.md'"),
        ("archive/member.md", "must be canonical 'runbooks/member.md'"),
        ("../member.md", "must be canonical 'runbooks/member.md'"),
    ],
)
def test_pinned_active_paths_must_be_exactly_canonical(
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


def test_canonical_active_path_missing_at_pin_fails(tmp_path: Path) -> None:
    root, _, _ = _valid_repo(tmp_path)
    (root / "runbooks/member.md").unlink()
    sha = _commit(root, "missing canonical source")

    with pytest.raises(CatalogError, match="ACTIVE path is missing at pinned SHA"):
        validate_catalog_ref(root, f"git:aidotmarket/runbooks@{sha}:CATALOG.json")


def test_dangling_section_and_frontmatter_catalog_drift_fail(tmp_path: Path) -> None:
    root, _, _ = _valid_repo(tmp_path)
    path = root / "runbooks/member.md"
    text = path.read_text().replace("section: Overview", "section: Missing")
    path.write_text(text)
    with pytest.raises(CatalogError, match="dangling section"):
        generate_catalog(root)

    path.write_text(path.read_text().replace("section: Missing", "section: Overview"))
    generate_catalog(root)
    path.write_text(
        path.read_text()
        .replace("owner: sysadmin", "owner: mars", 1)
        .replace("owner_agent: sysadmin", "owner_agent: mars")
    )
    sha = _commit(root, "catalog drift")
    with pytest.raises(CatalogError, match="differs from ACTIVE frontmatter"):
        validate_catalog_ref(root, f"git:aidotmarket/runbooks@{sha}:CATALOG.json")


def _add_stable_overview_metadata(metadata: dict) -> None:
    metadata["authoritative_for"][0]["section_id"] = "overview"
    metadata["error_signatures"] = [
        {
            "signature": "EXACT_ERROR",
            "section": "Overview",
            "section_id": "overview",
        }
    ]


def test_stable_section_anchor_and_shared_metadata_identity_validate(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    _add_stable_overview_metadata(metadata)
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    _, catalog_ref = _generate_commit(tmp_path, "stable section")

    assert validate_catalog_ref(tmp_path, catalog_ref).status == "integrity_pass_unverified"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "is missing"),
        ("separated", "must immediately precede"),
        ("duplicate", "duplicate section anchor"),
    ],
)
def test_missing_misplaced_and_duplicate_stable_anchors_fail_before_generation(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    _add_stable_overview_metadata(metadata)
    path = _write_doc(tmp_path, "runbooks/member.md", metadata)
    if mutation == "missing":
        path.write_text(
            path.read_text().replace(
                '<a id="rb-section-overview"></a>\n',
                "",
                1,
            )
        )
    if mutation == "separated":
        path.write_text(path.read_text().replace("</a>\n##", "</a>\n\n##"))
    if mutation == "duplicate":
        path.write_text(
            path.read_text()
            + '\n<a id="rb-section-overview"></a>\n## Appendix\n'
        )

    with pytest.raises(CatalogError, match=message):
        generate_catalog(tmp_path)


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (
            (
                "````markdown\n"
                '<a id="rb-section-overview"></a>\n'
                "## Overview\n"
                "```\ninner fence\n```\n"
                "````"
            ),
            "dangling section|is missing",
        ),
        (
            (
                "<!--\n"
                '<a id="rb-section-overview"></a>\n'
                "## Overview\n"
                "-->"
            ),
            "dangling section|is missing",
        ),
        (
            '    <a id="rb-section-overview"></a>\n## Overview',
            "is missing",
        ),
    ],
)
def test_stable_identity_rejects_non_rendered_markdown_targets(
    tmp_path: Path,
    replacement: str,
    message: str,
) -> None:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    _add_stable_overview_metadata(metadata)
    path = _write_doc(tmp_path, "runbooks/member.md", metadata)
    path.write_text(
        path.read_text().replace(
            '<a id="rb-section-overview"></a>\n## Overview',
            replacement,
        )
    )

    with pytest.raises(CatalogError, match=message):
        generate_catalog(tmp_path)


def test_legacy_declared_heading_must_be_unambiguous(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(path.read_text() + "\n## Overview\n\nSecond occurrence.\n")

    with pytest.raises(CatalogError, match="legacy section.*ambiguous"):
        generate_catalog(tmp_path)


def test_one_section_id_cannot_map_to_conflicting_headings(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section_id"] = "shared"
    metadata["error_signatures"] = [
        {
            "signature": "EXACT_ERROR",
            "section": "Appendix",
            "section_id": "shared",
        }
    ]
    path = _write_doc(tmp_path, "runbooks/member.md", metadata)
    path.write_text(path.read_text() + "\n## Appendix\n")

    with pytest.raises(CatalogError, match="maps to conflicting headings"):
        generate_catalog(tmp_path)


def test_mixed_stable_and_legacy_identity_for_one_heading_fails(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section_id"] = "overview"
    metadata["error_signatures"] = [
        {"signature": "EXACT_ERROR", "section": "Overview"}
    ]
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match="mixes stable and legacy"):
        generate_catalog(tmp_path)


def test_two_stable_ids_for_one_heading_fail(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section_id"] = "overview"
    metadata["error_signatures"] = [
        {
            "signature": "EXACT_ERROR",
            "section": "Overview",
            "section_id": "other-overview",
        }
    ]
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match="multiple section_ids"):
        generate_catalog(tmp_path)


def test_duplicate_orphan_anchors_do_not_invalidate_legacy_metadata(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        path.read_text()
        + '\n<a id="rb-section-orphan"></a>\n'
        + '<a id="rb-section-orphan"></a>\n'
    )

    _, catalog_ref = _generate_commit(tmp_path, "legacy orphan anchors")

    assert validate_catalog_ref(tmp_path, catalog_ref).status == "integrity_pass_unverified"


@pytest.mark.parametrize(
    "claim",
    [
        "Vulcan assigns work to Mars and approves Mars output.",
        "The primary slot directs the worker slot.",
        "The worker slot reports to the primary slot.",
        "Use the active Primary/Worker model.",
        "Historical note: the primary slot directs the worker slot.",
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
        f"<!-- catalog:historical -->\n{claim}\n<!-- /catalog:historical -->\n"
        "Current operational fixture body.",
    )
    _, valid_ref = _generate_commit(tmp_path, "historical claim")
    assert validate_catalog_ref(tmp_path, valid_ref).status == "integrity_pass_unverified"


def test_stale_scan_does_not_reject_an_explicit_retirement_statement(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_doc(
        tmp_path,
        "runbooks/member.md",
        _metadata("member"),
        "This runbook supersedes the retired Primary/Worker discipline.",
    )
    _, catalog_ref = _generate_commit(tmp_path, "retirement statement")

    assert validate_catalog_ref(tmp_path, catalog_ref).status == "integrity_pass_unverified"


@pytest.mark.parametrize(
    "claim",
    [
        "A retired note is archived. The primary/worker slots remain in force.",
        (
            "The primary/worker slots are obsolete, but they remain the "
            "required operating model."
        ),
    ],
)
def test_retirement_context_cannot_excuse_a_separate_affirmative_claim(
    claim: str,
) -> None:
    errors = _stale_claim_errors(claim, "x.md")

    assert errors
    assert errors[0].startswith("x.md:1: stale active claim")


def test_inline_html_comment_cannot_hide_active_visible_text(tmp_path: Path) -> None:
    claim = "Primary/worker slots remain required. <!-- purported history -->"
    document = parse_markdown_document(claim)

    assert claim in document.active_text
    assert document.structure_errors == (
        "1: HTML comments must occupy whole lines",
    )

    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), claim)
    with pytest.raises(CatalogError, match="HTML comments must occupy whole lines"):
        generate_catalog(tmp_path)


def test_inline_multiline_html_comment_cannot_hide_visible_suffix() -> None:
    markdown = "Visible prefix <!--\nhidden\n--> visible suffix"
    document = parse_markdown_document(markdown)

    assert "Visible prefix <!--" in document.active_text
    assert "--> visible suffix" in document.active_text
    assert document.structure_errors == (
        "1: HTML comments must occupy whole lines",
        "3: HTML comments must occupy whole lines",
    )


def test_fenced_historical_markers_cannot_hide_an_active_stale_claim(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    body = (
        "````markdown\n"
        "<!-- catalog:historical -->\n"
        "````\n\n"
        "The worker slot reports to the primary slot.\n\n"
        "````markdown\n"
        "<!-- /catalog:historical -->\n"
        "````"
    )
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), body)
    _, catalog_ref = _generate_commit(tmp_path, "fenced marker claim")

    with pytest.raises(CatalogError, match="stale active claim"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_stale_scan_applies_only_to_active_catalog_members(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    stale_claim = "Active Council voters: MP, AG, and XAI."
    _write_doc(tmp_path, "legacy.md", None, stale_claim)
    _, grandfathered_ref = _generate_commit(tmp_path, "grandfathered stale prose")
    assert (
        validate_catalog_ref(tmp_path, grandfathered_ref).status
        == "integrity_pass_unverified"
    )

    _write_doc(tmp_path, "runbooks/legacy.md", _metadata("legacy"), stale_claim)
    _, active_ref = _generate_commit(tmp_path, "promoted stale prose")
    with pytest.raises(CatalogError, match="stale active claim"):
        validate_catalog_ref(tmp_path, active_ref)

    _write_doc(
        tmp_path,
        "runbooks/legacy.md",
        _metadata("legacy"),
        "<!-- catalog:historical -->\n"
        + stale_claim
        + "\n<!-- /catalog:historical -->\nCurrent operational fixture body.",
    )
    _, historical_ref = _generate_commit(tmp_path, "promoted historical prose")
    assert (
        validate_catalog_ref(tmp_path, historical_ref).status
        == "integrity_pass_unverified"
    )


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

    with pytest.raises(CatalogError, match="historical"):
        generate_catalog(tmp_path)


@pytest.mark.parametrize("indent", [1, 2, 3])
def test_indented_historical_marker_is_an_error_and_cannot_hide_prose(
    tmp_path: Path,
    indent: int,
) -> None:
    claim = "The primary slot directs the worker slot."
    body = (
        " " * indent
        + "<!-- catalog:historical -->\n"
        + claim
        + "\n"
        + " " * indent
        + "<!-- /catalog:historical -->"
    )
    document = parse_markdown_document(body)
    assert claim in document.active_text
    assert document.structure_errors

    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), body)
    with pytest.raises(CatalogError, match="HTML comments must occupy whole lines"):
        generate_catalog(tmp_path)


def test_four_space_historical_lookalike_remains_active_code(tmp_path: Path) -> None:
    claim = "The primary slot directs the worker slot."
    body = (
        "    <!-- catalog:historical -->\n"
        + claim
        + "\n    <!-- /catalog:historical -->"
    )
    document = parse_markdown_document(body)
    assert document.structure_errors == ()
    assert claim in document.active_text

    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), body)
    _, catalog_ref = _generate_commit(tmp_path, "indented marker lookalike")
    with pytest.raises(CatalogError, match="stale active claim"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_unclosed_html_comment_fails_and_preserves_source_prose(tmp_path: Path) -> None:
    body = "<!--\nThe primary slot directs the worker slot."
    document = parse_markdown_document(body)
    assert "primary slot" in document.active_text
    assert any("unclosed HTML comment" in error for error in document.structure_errors)

    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), body)
    with pytest.raises(CatalogError, match="unclosed HTML comment"):
        generate_catalog(tmp_path)


def test_raw_html_block_cannot_fabricate_catalog_headings(tmp_path: Path) -> None:
    body = "<script>\n## Fake Authority\nforged action\n</script>\nCurrent body."
    document = parse_markdown_document(body)
    assert "Fake Authority" not in {section.heading for section in document.sections}
    assert any("raw HTML blocks" in error for error in document.structure_errors)

    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), body)
    with pytest.raises(CatalogError, match="raw HTML blocks are not allowed"):
        generate_catalog(tmp_path)


def test_atx_closing_sequence_requires_preceding_whitespace() -> None:
    document = parse_markdown_document("## API#\n\n## API ###\n")

    assert [section.heading for section in document.sections] == ["API#", "API"]


@pytest.mark.parametrize(
    "claim",
    [
        "The primary slot\ndirects the worker slot.",
        "Vulcan\ndirects Mars.",
        "Mars reports to\nVulcan.",
    ],
)
def test_stale_hierarchy_scan_crosses_soft_line_breaks_with_source_line(
    tmp_path: Path,
    claim: str,
) -> None:
    _init_repo(tmp_path)
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), claim)
    expected_line = next(
        index
        for index, line in enumerate(path.read_text().splitlines(), start=1)
        if line == claim.splitlines()[0]
    )
    _, catalog_ref = _generate_commit(tmp_path, "soft break stale claim")

    with pytest.raises(CatalogError) as captured:
        validate_catalog_ref(tmp_path, catalog_ref)
    assert f"runbooks/member.md:{expected_line}: stale active claim" in str(
        captured.value
    )


@pytest.mark.parametrize(
    "guidance",
    [
        "Primary/worker is deprecated and must not be used.",
        "The retired Primary/Worker model must never be restored.",
        "The obsolete hierarchy should not direct current operations.",
    ],
)
def test_prohibitive_retirement_guidance_remains_active_and_searchable(
    tmp_path: Path,
    guidance: str,
) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), guidance)
    _, catalog_ref = _generate_search_commit(
        tmp_path,
        "retirement safety guidance",
    )

    assert validate_catalog_ref(tmp_path, catalog_ref).status == "integrity_pass_unverified"
    result = search_catalog(tmp_path, catalog_ref, guidance)
    assert any(guidance in row["excerpt"] for row in result["candidates"])


@pytest.mark.parametrize(
    "claim",
    [
        "The deprecated Primary/Worker model must be used for dispatch.",
        "Although the old hierarchy is retired, Vulcan directs Mars.",
        "The obsolete role map says Mars reports to Vulcan.",
    ],
)
def test_retirement_words_do_not_excuse_affirmative_hierarchy_claims(
    tmp_path: Path,
    claim: str,
) -> None:
    _init_repo(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"), claim)
    _, catalog_ref = _generate_commit(tmp_path, "affirmative stale hierarchy")

    with pytest.raises(CatalogError, match="stale active claim"):
        validate_catalog_ref(tmp_path, catalog_ref)


def test_pinned_last_verified_uses_committer_utc_date(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    metadata = _metadata("member")
    metadata["last_verified_at"] = "2026-08-01"
    _write_doc(tmp_path, "runbooks/member.md", metadata)
    generate_catalog(tmp_path, current_utc_date=date(2026, 8, 1))
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-07-31T12:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-07-31T12:00:00+00:00",
        }
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "future verification fixture"],
        cwd=tmp_path,
        check=True,
        env=environment,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with pytest.raises(CatalogError, match="verification clock 2026-07-31"):
        validate_catalog_ref(
            tmp_path,
            f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        )


@pytest.mark.parametrize(
    ("old", "new", "field"),
    [
        (
            "last_refresh_date: 2026-04-21T17:30:00Z",
            "last_refresh_date: 2999-01-01T00:00:00Z",
            "last_refresh_date",
        ),
        (
            "last_harness_date: 2026-04-20T02:00:00Z",
            "last_harness_date: 2999-01-01T00:00:00Z",
            "last_harness_date",
        ),
        (
            "first_staleness_detected_at: null",
            "first_staleness_detected_at: 2999-01-01T00:00:00Z",
            "first_staleness_detected_at",
        ),
    ],
)
def test_pinned_lifecycle_timestamps_use_exact_committer_utc_clock(
    tmp_path: Path,
    old: str,
    new: str,
    field: str,
) -> None:
    root, _, _ = _valid_repo(tmp_path)
    runbook = root / "runbooks/member.md"
    runbook.write_text(runbook.read_text().replace(old, new, 1))
    sha = _commit(root, f"future pinned {field}")

    with pytest.raises(
        CatalogError,
        match=rf"§J field {field} cannot be in the future",
    ):
        validate_catalog_ref(
            root,
            f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        )


def test_pinned_lifecycle_clock_uses_commit_instant_not_end_of_day(
    tmp_path: Path,
) -> None:
    root, _, _ = _valid_repo(tmp_path)
    runbook = root / "runbooks/member.md"
    runbook.write_text(
        runbook.read_text().replace(
            "last_refresh_date: 2026-04-21T17:30:00Z",
            "last_refresh_date: 2026-07-31T12:00:01Z",
            1,
        )
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-07-31T12:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-07-31T12:00:00+00:00",
        }
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "same-day future lifecycle"],
        cwd=root,
        check=True,
        env=environment,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with pytest.raises(CatalogError, match="last_refresh_date cannot be in the future"):
        validate_catalog_ref(
            root,
            f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        )


def test_a_missing_conventional_section_no_longer_hides_a_page_from_search(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    generate_catalog(tmp_path)
    path.write_text(
        re.sub(
            r"(?ms)^## §E\..*?(?=^## §F\.)",
            "",
            path.read_text(),
            count=1,
        )
    )
    sha = _commit(tmp_path, "missing required E section")
    catalog_ref = f"git:aidotmarket/runbooks@{sha}:CATALOG.json"

    # Max directive S1491 and AC7/AC9 of the approved truth-layer design: shape
    # may rank a result, never filter it. There is no query that hides a page for
    # being untidy. The section is not declared by any catalog row here, so the
    # index is not lying - the page is merely missing a conventional heading, and
    # a reader looking for it must still be able to find it.
    report = validate_catalog_ref(tmp_path, catalog_ref)
    assert report.checked_entry_count == 1

    # The check still fires; it simply no longer has the power to hide the page.
    findings = structural_conformance_failures(path.read_text(), tmp_path / "schemas")
    assert any("§E" in finding.message for finding in findings)


def test_all_seven_kernel_companions_generate_and_validate_at_one_pin(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "runbooks").mkdir(exist_ok=True)
    for source in KERNEL_FIXTURES.glob("*.md"):
        metadata = yaml.safe_load(source.read_text().split("---", 2)[1])
        metadata["owner"] = "sysadmin"
        metadata["owner_agent"] = "sysadmin"
        (tmp_path / "runbooks" / source.name).write_text(
            conformant_catalog_document(metadata, title=source.stem)
        )
    sha, catalog_ref = _generate_commit(tmp_path, "kernel companions")

    report = validate_catalog_ref(tmp_path, catalog_ref)

    assert report.catalog_sha == sha
    assert report.checked_entry_count == 7
    assert report.checked_section_count == 7
