from __future__ import annotations

import copy
import subprocess
from pathlib import Path

import pytest
import yaml

import runbook_tools.corpus_manifest as corpus_manifest_module
from runbook_tools.catalog.canonical_content import requirement_mapping_digest
from runbook_tools.corpus_manifest import (
    MAX_PINNED_BATCH_BYTES,
    PURPOSE,
    SOURCE_SELECTOR,
    CorpusManifestError,
    load_pinned_corpus_manifest,
    refresh_corpus_manifest,
    validate_corpus_manifest,
)
from runbook_tools.strict_yaml import strict_yaml_load

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "CORPUS-MANIFEST.yaml"


def _manifest() -> dict:
    value = strict_yaml_load(MANIFEST_PATH.read_text())
    assert isinstance(value, dict)
    return value


def _write_manifest(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "CORPUS-MANIFEST.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False))
    return path


def _run_git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _single_source_repository(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    root.mkdir()
    _run_git(root, "init", "-q")
    source = root / "legacy.md"
    source.write_text("# Legacy\n")
    _run_git(root, "add", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "inventory",
    )
    sha = _run_git(root, "rev-parse", "HEAD")
    oid = _run_git(root, "rev-parse", "HEAD:legacy.md")
    manifest = {
        "manifest_version": 2,
        "purpose": PURPOSE,
        "inventory": {
            "repository": "example/runbooks",
            "base_sha": sha,
            "inventory_sha": sha,
            "blob_oid_scope": "Pinned inventory tree blob.",
            "inventory_path_semantics": "inventory_path selects the pinned tree path.",
            "source_selector": SOURCE_SELECTOR,
            "refresh_required_before_execution": True,
            "counts": {
                "operational_documents": 1,
                "source_documents": 1,
                "active": 0,
                "grandfathered": 1,
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
            risk: f"Definition for {risk}." for risk in ("P0", "P1", "P2", "P3")
        },
        "documents": [
            {
                "path": "legacy.md",
                "git_blob_oid": oid,
                "catalog_state": "grandfathered",
                "status": "pending_verification",
                "proposed_disposition": "promote",
                "batch": "test-batch",
                "risk": "P2",
                "target_paths": ["runbooks/legacy.md"],
                "evidence": [],
                "verify_against": ["current implementation"],
                "independent_review_required": False,
            }
        ],
    }
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    _run_git(root, "add", "CORPUS-MANIFEST.yaml")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "manifest",
    )
    return root, source


def test_repository_manifest_passes_default_check() -> None:
    manifest = _manifest()
    counts = manifest["inventory"]["counts"]
    report = validate_corpus_manifest(REPO_ROOT)

    assert report.operational_documents == counts["operational_documents"]
    assert report.source_documents == counts["source_documents"]
    assert report.active == counts["active"]
    assert report.grandfathered == counts["grandfathered"]
    assert report.archived == sum(
        document["catalog_state"] == "archived" for document in manifest["documents"]
    )
    assert report.pending == sum(
        document["status"] == "pending_verification"
        for document in manifest["documents"]
    )
    assert report.promotion_bar is False


def test_pinned_manifest_loader_reads_one_immutable_complete_snapshot() -> None:
    sha = _run_git(REPO_ROOT, "rev-parse", "HEAD")

    pinned = load_pinned_corpus_manifest(REPO_ROOT, sha)

    assert pinned.search_sha == sha
    assert pinned.operational_documents == 107
    assert pinned.source_documents == 103
    assert pinned.active == 24
    assert pinned.grandfathered == 79
    assert pinned.archived == 4
    assert len(pinned.documents) == 107
    assert len(pinned.manifest_sha256) == 64
    assert {
        document.catalog_state for document in pinned.documents
    } == {"active", "grandfathered", "archived"}


def test_pinned_manifest_loader_ignores_dirty_worktree_bytes(tmp_path: Path) -> None:
    root, source = _single_source_repository(tmp_path)
    sha = _run_git(root, "rev-parse", "HEAD")
    before = load_pinned_corpus_manifest(root, sha)
    source.write_text("# Dirty replacement\n")

    after = load_pinned_corpus_manifest(root, sha)

    assert after == before
    assert after.documents[0].markdown == "# Legacy\n"
    assert len(after.documents[0].verification_mappings) == 1
    assert after.documents[0].verification_mappings[0].adapter_type == (
        "unmapped_prose"
    )
    assert len(after.documents[0].verification_mappings[0].mapping_digest) == 64


def test_manifest_v2_accepts_one_closed_digest_bound_mapping_per_prose_item(
    tmp_path: Path,
) -> None:
    root, _ = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    policy = {
        "minimum_receipts": 1,
        "maximum_receipts": 1,
        "freshness_seconds": 0,
        "allowed_evidence_kinds": ["git"],
        "require_remote_identity": False,
        "require_distinct_sources": False,
    }
    manifest["documents"][0]["verification_mappings"] = [
        {
            "schema_version": 2,
            "ordinal": 1,
            "mapping_digest": requirement_mapping_digest(
                adapter_type="unmapped_prose",
                adapter_parameters={},
                evidence_policy=policy,
            ),
            "adapter_type": "unmapped_prose",
            "adapter_parameters": {},
            "evidence_policy": policy,
        }
    ]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    _run_git(root, "add", "CORPUS-MANIFEST.yaml")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "mapped manifest",
    )

    pinned = load_pinned_corpus_manifest(root, _run_git(root, "rev-parse", "HEAD"))

    mapping = pinned.documents[0].verification_mappings[0]
    assert mapping.ordinal == 1
    assert mapping.adapter_type == "unmapped_prose"
    assert mapping.adapter_parameters == {}
    assert mapping.evidence_policy == policy


def test_manifest_v2_rejects_mapping_digest_mismatch(tmp_path: Path) -> None:
    root, _ = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    manifest["documents"][0]["verification_mappings"] = [
        {
            "schema_version": 2,
            "ordinal": 1,
            "mapping_digest": "0" * 64,
            "adapter_type": "unmapped_prose",
            "adapter_parameters": {},
            "evidence_policy": {
                "minimum_receipts": 1,
                "maximum_receipts": 1,
                "freshness_seconds": 0,
                "allowed_evidence_kinds": ["git"],
                "require_remote_identity": False,
                "require_distinct_sources": False,
            },
        }
    ]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    _run_git(root, "add", "CORPUS-MANIFEST.yaml")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "bad mapping digest",
    )

    with pytest.raises(CorpusManifestError, match="mapping_digest is"):
        load_pinned_corpus_manifest(root, _run_git(root, "rev-parse", "HEAD"))


@pytest.mark.parametrize(
    ("verify_against", "message"),
    [
        (["\x01"], "contains a control character"),
        (["\\" * 61], "120-byte JSON-wire limit"),
        (["a" * 40, "b" * 40, "c" * 41], "JSON-wire aggregate limit"),
        (["one", "two", "three", "four"], "3-item limit"),
    ],
)
def test_pinned_manifest_loader_rejects_unbounded_verify_against_wire_values(
    tmp_path: Path,
    verify_against: list[str],
    message: str,
) -> None:
    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    manifest["documents"][0]["verify_against"] = verify_against
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    _run_git(root, "add", "CORPUS-MANIFEST.yaml")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "adversarial verification projection",
    )

    with pytest.raises(CorpusManifestError, match=message):
        load_pinned_corpus_manifest(root, _run_git(root, "rev-parse", "HEAD"))


@pytest.mark.parametrize(
    ("verify_against", "message"),
    [
        (["\x01"], "contains a control character"),
        (["\\" * 61], "120-byte JSON-wire limit"),
    ],
)
def test_worktree_validator_enforces_verify_against_wire_bounds(
    tmp_path: Path,
    verify_against: list[str],
    message: str,
) -> None:
    manifest = _manifest()
    manifest["documents"][0]["verify_against"] = verify_against

    with pytest.raises(CorpusManifestError, match=message):
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))


def test_batch_identifier_size_is_bounded_in_both_manifest_loaders(
    tmp_path: Path,
) -> None:
    oversized_batch = "b" * (MAX_PINNED_BATCH_BYTES + 1)
    manifest = _manifest()
    manifest["documents"][0]["batch"] = oversized_batch
    with pytest.raises(CorpusManifestError, match="batch exceeds the 128-byte limit"):
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))

    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    pinned_manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(pinned_manifest, dict)
    pinned_manifest["documents"][0]["batch"] = oversized_batch
    manifest_path.write_text(yaml.safe_dump(pinned_manifest, sort_keys=False))
    _run_git(root, "add", "CORPUS-MANIFEST.yaml")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "oversized batch",
    )
    with pytest.raises(CorpusManifestError, match="batch exceeds the 128-byte limit"):
        load_pinned_corpus_manifest(root, _run_git(root, "rev-parse", "HEAD"))


def test_pinned_blob_aggregate_limit_counts_each_document_reference(
    tmp_path: Path,
) -> None:
    root, _source = _single_source_repository(tmp_path)
    oid = _run_git(root, "rev-parse", "HEAD:legacy.md")
    size = len(b"# Legacy\n")
    errors: list[str] = []

    payloads = corpus_manifest_module._read_pinned_blob_batch(
        root,
        [oid, oid],
        per_blob_limit=size,
        aggregate_limit=(size * 2) - 1,
        label="duplicate-reference fixture",
        errors=errors,
    )

    assert payloads == {}
    assert errors == [
        f"duplicate-reference fixture exceeds the {(size * 2) - 1}-byte aggregate limit"
    ]


def test_source_selector_symlink_failure_is_reported_as_manifest_error(
    tmp_path: Path,
) -> None:
    root, _ = _single_source_repository(tmp_path)
    target = root / "ignored-target"
    target.mkdir()
    (root / "docs").symlink_to(target, target_is_directory=True)

    with pytest.raises(CorpusManifestError, match="source selector failed"):
        validate_corpus_manifest(root)


def test_manifest_file_must_not_be_a_symlink(tmp_path: Path) -> None:
    root, _ = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    target = root / "manifest-target.yaml"
    manifest_path.rename(target)
    manifest_path.symlink_to(target)

    with pytest.raises(CorpusManifestError, match="manifest file must not be a symlink"):
        validate_corpus_manifest(root)


def test_source_set_drift_is_rejected(tmp_path: Path) -> None:
    manifest = _manifest()
    removed = manifest["documents"].pop()

    with pytest.raises(CorpusManifestError) as raised:
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))

    assert "source document set mismatch" in str(raised.value)
    assert removed["path"] in str(raised.value)


def test_pinned_inventory_source_cannot_disappear_without_archive(
    tmp_path: Path,
) -> None:
    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)

    _run_git(root, "rm", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "silent deletion fixture",
    )
    manifest["documents"] = []
    manifest["inventory"]["counts"] = {
        "operational_documents": 0,
        "source_documents": 0,
        "active": 0,
        "grandfathered": 0,
        "archived": 0,
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(
        CorpusManifestError,
        match="pinned inventory document set mismatch: missing=legacy.md",
    ):
        validate_corpus_manifest(root)


def test_blob_oid_must_match_inventory_tree(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["documents"][0]["git_blob_oid"] = "0" * 40

    with pytest.raises(CorpusManifestError, match="does not match"):
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))


def test_empty_inventory_tree_still_checks_entry_paths(tmp_path: Path) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)

    _run_git(root, "rm", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "empty inventory",
    )
    empty_inventory_sha = _run_git(root, "rev-parse", "HEAD")
    assert "legacy.md" not in _run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        empty_inventory_sha,
    ).splitlines()
    source.write_text("# Legacy\n")
    manifest["inventory"]["inventory_sha"] = empty_inventory_sha
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(
        CorpusManifestError, match="inventory path 'legacy.md' is absent"
    ):
        validate_corpus_manifest(root)


def test_nonexistent_base_commit_is_rejected(tmp_path: Path) -> None:
    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    nonexistent_sha = "f" * 40
    manifest["inventory"]["base_sha"] = nonexistent_sha
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(
        CorpusManifestError,
        match=f"cannot resolve inventory.base_sha {nonexistent_sha} to a commit",
    ):
        validate_corpus_manifest(root)


def test_non_ancestor_base_commit_is_rejected(tmp_path: Path) -> None:
    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    inventory_sha = manifest["inventory"]["inventory_sha"]
    tree = _run_git(root, "rev-parse", f"{inventory_sha}^{{tree}}")
    unrelated_base = _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit-tree",
        tree,
        "-m",
        "unrelated root",
    )
    manifest["inventory"]["base_sha"] = unrelated_base
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(CorpusManifestError, match="is not an ancestor"):
        validate_corpus_manifest(root)


def test_inventory_commit_must_be_ancestor_of_detached_head(tmp_path: Path) -> None:
    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    tree = _run_git(root, "rev-parse", "HEAD^{tree}")
    sibling_head = _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit-tree",
        tree,
        "-m",
        "sibling root",
    )
    _run_git(root, "checkout", "--detach", "-q", sibling_head)

    with pytest.raises(
        CorpusManifestError,
        match="is not an ancestor of checked-out HEAD",
    ):
        validate_corpus_manifest(root)


def test_git_replace_cannot_substitute_inventory_identity(tmp_path: Path) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    search_sha = _run_git(root, "rev-parse", "HEAD")
    inventory_sha = manifest["inventory"]["inventory_sha"]
    inventoried_blob = manifest["documents"][0]["git_blob_oid"]

    source.write_text("# Replacement bytes\n")
    _run_git(root, "add", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "replacement commit",
    )
    replacement_commit = _run_git(root, "rev-parse", "HEAD")
    _run_git(root, "checkout", "--detach", "-q", search_sha)
    _run_git(root, "replace", inventory_sha, replacement_commit)
    replacement_visible_blob = _run_git(root, "rev-parse", f"{inventory_sha}:legacy.md")
    assert replacement_visible_blob != inventoried_blob

    report = validate_corpus_manifest(root)

    assert report.source_documents == 1


def test_inventory_path_must_be_a_regular_git_blob(tmp_path: Path) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)

    # A symlink blob stores its target bytes. Make those bytes identical to the
    # regular working document so object-ID equality alone cannot expose it.
    source.unlink()
    source.symlink_to("# Legacy\n")
    _run_git(root, "add", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "symlink inventory",
    )
    manifest["inventory"]["inventory_sha"] = _run_git(root, "rev-parse", "HEAD")
    source.unlink()
    source.write_text("# Legacy\n")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(CorpusManifestError, match="mode 120000 blob"):
        validate_corpus_manifest(root)


@pytest.mark.parametrize(
    ("pin_gitlink_commit", "tree_label"),
    [
        (True, "inventory.inventory_sha"),
        (False, "checked-out HEAD"),
    ],
)
def test_admitted_gitlink_cannot_evade_exhaustive_inventory(
    tmp_path: Path,
    pin_gitlink_commit: bool,
    tree_label: str,
) -> None:
    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    inventory_sha = manifest["inventory"]["inventory_sha"]

    _run_git(
        root,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{inventory_sha},docs-submodule",
    )
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "gitlink fixture",
    )
    gitlink_sha = _run_git(root, "rev-parse", "HEAD")
    if pin_gitlink_commit:
        manifest["inventory"]["inventory_sha"] = gitlink_sha
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(
        CorpusManifestError,
        match=rf"{tree_label} contains admitted path 'docs-submodule'.*160000 commit",
    ):
        validate_corpus_manifest(root)


def test_same_path_working_content_drift_is_advisory_not_a_failure(
    tmp_path: Path,
) -> None:
    """Editing a page without re-pinning must never fail a check.

    Max directives S1491 and S1500: a stale inventory is reported, not
    enforced. Before S1525 this raised, which turned every runbook edit into a
    red main until somebody pushed a bookkeeping commit.
    """

    root, source = _single_source_repository(tmp_path)
    clean = validate_corpus_manifest(root)
    assert clean.pin_drift == ()

    source.write_text("# Legacy\n\nChanged without refreshing the inventory.\n")

    report = validate_corpus_manifest(root)

    assert any("does not match current bytes" in finding for finding in report.pin_drift)
    assert report.operational_documents == clean.operational_documents


def test_strict_pins_still_rejects_working_content_drift(tmp_path: Path) -> None:
    """The pin writer keeps the hard guard: never pin a dirty working tree."""

    root, source = _single_source_repository(tmp_path)
    source.write_text("# Legacy\n\nChanged without refreshing the inventory.\n")

    with pytest.raises(CorpusManifestError, match="does not match current bytes"):
        validate_corpus_manifest(root, strict_pins=True)


def test_pinned_draft_is_non_authoritative_grandfathered_corpus_member(
    tmp_path: Path,
) -> None:
    root, source = _single_source_repository(tmp_path)
    source.write_text(
        "---\n"
        "runbook_id: legacy\n"
        "status: DRAFT\n"
        "---\n"
        "# Legacy DRAFT\n"
    )
    _run_git(root, "add", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "pin non-authoritative DRAFT",
    )
    sha = _run_git(root, "rev-parse", "HEAD")
    oid = _run_git(root, "rev-parse", "HEAD:legacy.md")
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    manifest["inventory"]["inventory_sha"] = sha
    manifest["documents"][0]["git_blob_oid"] = oid
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    report = validate_corpus_manifest(root)

    assert report.active == 0
    assert report.grandfathered == 1


def test_refresh_mechanically_pins_exact_checked_out_content_commit(
    tmp_path: Path,
) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    before = strict_yaml_load(manifest_path.read_text())
    assert isinstance(before, dict)
    preserved = {
        key: copy.deepcopy(before["documents"][0][key])
        for key in (
            "batch",
            "evidence",
            "independent_review_required",
            "proposed_disposition",
            "risk",
            "verify_against",
        )
    }

    source.write_text("# Legacy\n\nVerified content change.\n")
    _run_git(root, "add", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "content snapshot",
    )
    content_sha = _run_git(root, "rev-parse", "HEAD")
    expected_oid = _run_git(root, "rev-parse", "HEAD:legacy.md")

    report = refresh_corpus_manifest(root, content_sha)
    refreshed = strict_yaml_load(manifest_path.read_text())
    assert isinstance(refreshed, dict)
    entry = refreshed["documents"][0]

    assert report.source_documents == 1
    assert refreshed["inventory"]["inventory_sha"] == content_sha
    assert entry["git_blob_oid"] == expected_oid
    assert "inventory_path" not in entry
    assert {key: entry[key] for key in preserved} == preserved
    validate_corpus_manifest(root)


def test_refresh_rejects_non_head_sha_without_changing_ledger(tmp_path: Path) -> None:
    root, _source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    old_sha = _run_git(root, "rev-parse", "HEAD")
    before = manifest_path.read_bytes()
    (root / "metadata.txt").write_text("new commit\n")
    _run_git(root, "add", "metadata.txt")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "advance head",
    )

    with pytest.raises(CorpusManifestError, match="must equal checked-out HEAD"):
        refresh_corpus_manifest(root, old_sha)

    assert manifest_path.read_bytes() == before


def test_refresh_writes_only_the_canonical_repository_ledger(tmp_path: Path) -> None:
    root, _source = _single_source_repository(tmp_path)
    content_sha = _run_git(root, "rev-parse", "HEAD")
    alternate = tmp_path / "alternate.yaml"
    alternate.write_bytes((root / "CORPUS-MANIFEST.yaml").read_bytes())
    before = alternate.read_bytes()

    with pytest.raises(CorpusManifestError, match="canonical repository ledger"):
        refresh_corpus_manifest(root, content_sha, alternate)

    assert alternate.read_bytes() == before


def test_refresh_lock_must_not_be_a_symlink(tmp_path: Path) -> None:
    root, _source = _single_source_repository(tmp_path)
    content_sha = _run_git(root, "rev-parse", "HEAD")
    target = root / "lock-target"
    target.write_text("sentinel\n")
    (root / ".runbook-manifest.lock").symlink_to(target)

    with pytest.raises(CorpusManifestError, match="regular repository refresh lock"):
        refresh_corpus_manifest(root, content_sha)

    assert target.read_text() == "sentinel\n"


def test_refresh_cas_preserves_concurrent_adjudication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    source.write_text("# Legacy\n\nCommitted content.\n")
    _run_git(root, "add", "legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "content snapshot",
    )
    content_sha = _run_git(root, "rev-parse", "HEAD")
    original_validate = corpus_manifest_module.validate_corpus_manifest
    injected = False
    evidence = {
        "ref": "state:concurrent-review",
        "finding": "Concurrent adjudication must survive a refresh race.",
    }

    def validate_with_concurrent_edit(*args: object, **kwargs: object):
        nonlocal injected
        if not injected:
            injected = True
            concurrent = strict_yaml_load(manifest_path.read_text())
            assert isinstance(concurrent, dict)
            concurrent["documents"][0]["evidence"].append(evidence)
            manifest_path.write_text(yaml.safe_dump(concurrent, sort_keys=False))
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(
        corpus_manifest_module,
        "validate_corpus_manifest",
        validate_with_concurrent_edit,
    )

    with pytest.raises(CorpusManifestError, match="concurrent adjudication"):
        refresh_corpus_manifest(root, content_sha)

    current = strict_yaml_load(manifest_path.read_text())
    assert isinstance(current, dict)
    assert current["documents"][0]["evidence"] == [evidence]


def test_refresh_rejects_dirty_source_without_changing_ledger(tmp_path: Path) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    content_sha = _run_git(root, "rev-parse", "HEAD")
    before = manifest_path.read_bytes()
    source.write_text("# Uncommitted replacement\n")

    with pytest.raises(CorpusManifestError, match="does not match current bytes"):
        refresh_corpus_manifest(root, content_sha)

    assert manifest_path.read_bytes() == before


def test_refresh_pins_committed_archive_at_its_recoverable_path(
    tmp_path: Path,
) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    entry = manifest["documents"][0]
    archive_path = root / "archive" / "legacy.md"
    archive_path.parent.mkdir()
    source.rename(archive_path)
    entry.update(
        {
            "path": "archive/legacy.md",
            "inventory_path": "legacy.md",
            "catalog_state": "archived",
            "status": "archived",
            "proposed_disposition": "archive",
            "archive_path": "archive/legacy.md",
            "target_paths": ["archive/legacy.md"],
        }
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    _run_git(root, "add", "-A", "--", "legacy.md", "archive/legacy.md")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "archive content snapshot",
    )
    content_sha = _run_git(root, "rev-parse", "HEAD")
    expected_oid = _run_git(root, "rev-parse", "HEAD:archive/legacy.md")

    report = refresh_corpus_manifest(root, content_sha)
    refreshed = strict_yaml_load(manifest_path.read_text())
    assert isinstance(refreshed, dict)
    refreshed_entry = refreshed["documents"][0]

    assert report.archived == 1
    assert refreshed_entry["inventory_path"] == "archive/legacy.md"
    assert refreshed_entry["git_blob_oid"] == expected_oid
    validate_corpus_manifest(root)


def test_archived_record_must_remain_recoverable_with_exact_bytes(
    tmp_path: Path,
) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    entry = manifest["documents"][0]
    archive_path = root / "archive" / "legacy.md"
    archive_path.parent.mkdir()
    source.rename(archive_path)
    _run_git(root, "add", "-A")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "archive source",
    )
    entry.update(
        {
            "path": "archive/legacy.md",
            "inventory_path": "legacy.md",
            "catalog_state": "archived",
            "status": "archived",
            "proposed_disposition": "archive",
            "archive_path": "archive/legacy.md",
            "target_paths": ["archive/legacy.md"],
        }
    )
    manifest["inventory"]["counts"] = {
        "operational_documents": 1,
        "source_documents": 0,
        "active": 0,
        "grandfathered": 0,
        "archived": 1,
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    report = validate_corpus_manifest(root, promotion_bar=True)
    assert report.archived == 1
    assert report.promotion_bar is True

    archive_path.unlink()
    with pytest.raises(CorpusManifestError, match="not recoverable"):
        validate_corpus_manifest(root, promotion_bar=True)


def test_archived_record_rejects_changed_bytes(tmp_path: Path) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    entry = manifest["documents"][0]
    archive_path = root / "archive" / "legacy.md"
    archive_path.parent.mkdir()
    source.rename(archive_path)
    archive_path.write_text("# Replaced archive\n")
    entry.update(
        {
            "path": "archive/legacy.md",
            "inventory_path": "legacy.md",
            "catalog_state": "archived",
            "status": "archived",
            "proposed_disposition": "archive",
            "archive_path": "archive/legacy.md",
            "target_paths": ["archive/legacy.md"],
        }
    )
    manifest["inventory"]["counts"] = {
        "operational_documents": 1,
        "source_documents": 0,
        "active": 0,
        "grandfathered": 0,
        "archived": 1,
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(
        CorpusManifestError, match="does not match current archived bytes"
    ):
        validate_corpus_manifest(root, promotion_bar=True)


def test_archived_record_rejects_symlink_parent(tmp_path: Path) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    entry = manifest["documents"][0]
    target = root / "specs" / "archive-store"
    target.mkdir(parents=True)
    source.rename(target / "legacy.md")
    (root / "archive").symlink_to(target, target_is_directory=True)
    entry.update(
        {
            "path": "archive/legacy.md",
            "inventory_path": "legacy.md",
            "catalog_state": "archived",
            "status": "archived",
            "proposed_disposition": "archive",
            "archive_path": "archive/legacy.md",
            "target_paths": ["archive/legacy.md"],
        }
    )
    manifest["inventory"]["counts"] = {
        "operational_documents": 1,
        "source_documents": 0,
        "active": 0,
        "grandfathered": 0,
        "archived": 1,
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(CorpusManifestError, match="symlink component 'archive'"):
        validate_corpus_manifest(root, promotion_bar=True)


def test_archived_record_must_be_recoverable_from_checked_out_head(
    tmp_path: Path,
) -> None:
    root, source = _single_source_repository(tmp_path)
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest = strict_yaml_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    entry = manifest["documents"][0]

    source.unlink()
    _run_git(root, "add", "-u")
    _run_git(
        root,
        "-c",
        "user.name=Corpus Test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "-qm",
        "delete source without archive",
    )
    archive_path = root / "archive" / "legacy.md"
    archive_path.parent.mkdir()
    archive_path.write_text("# Legacy\n")
    entry.update(
        {
            "path": "archive/legacy.md",
            "inventory_path": "legacy.md",
            "catalog_state": "archived",
            "status": "archived",
            "proposed_disposition": "archive",
            "archive_path": "archive/legacy.md",
            "target_paths": ["archive/legacy.md"],
        }
    )
    manifest["inventory"]["counts"] = {
        "operational_documents": 1,
        "source_documents": 0,
        "active": 0,
        "grandfathered": 0,
        "archived": 1,
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

    with pytest.raises(
        CorpusManifestError,
        match="current path 'archive/legacy.md' is absent from checked-out HEAD",
    ):
        validate_corpus_manifest(root, promotion_bar=True)


@pytest.mark.parametrize(
    "unsafe", ["../outside.md", "/absolute.md", "runbooks//bad.md"]
)
def test_traversal_and_non_normalized_paths_are_rejected(
    tmp_path: Path,
    unsafe: str,
) -> None:
    manifest = _manifest()
    manifest["documents"][0]["path"] = unsafe

    with pytest.raises(
        CorpusManifestError, match="normalized repository-relative path"
    ):
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))


def test_duplicate_document_and_inventory_paths_are_rejected(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["documents"].append(copy.deepcopy(manifest["documents"][0]))

    with pytest.raises(CorpusManifestError) as raised:
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))

    assert ".path duplicates manifest path" in str(raised.value)
    assert ".inventory_path duplicates historical source" in str(raised.value)


@pytest.mark.parametrize("replacement", [None, "true", 1])
def test_refresh_required_before_execution_is_required_and_typed(
    tmp_path: Path,
    replacement: object,
) -> None:
    manifest = _manifest()
    if replacement is None:
        del manifest["inventory"]["refresh_required_before_execution"]
    else:
        manifest["inventory"]["refresh_required_before_execution"] = replacement

    with pytest.raises(CorpusManifestError, match="refresh_required_before_execution"):
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))


def test_verify_risk_and_disposition_fields_are_typed(tmp_path: Path) -> None:
    manifest = _manifest()
    entry = manifest["documents"][0]
    entry["verify_against"] = "trust me"
    entry["risk"] = 0
    entry["proposed_disposition"] = True

    with pytest.raises(CorpusManifestError) as raised:
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))

    message = str(raised.value)
    assert ".verify_against must be a non-empty list" in message
    assert ".risk must be one of" in message
    assert ".proposed_disposition is not a recognized disposition" in message


def test_declared_counts_must_match_current_corpus(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["inventory"]["counts"]["active"] = 999

    with pytest.raises(CorpusManifestError, match="declares 999"):
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))


def test_manifest_cannot_reclassify_frontmatter_as_authority(tmp_path: Path) -> None:
    manifest = _manifest()
    entry = next(
        document
        for document in manifest["documents"]
        if document["catalog_state"] == "grandfathered"
    )
    entry["catalog_state"] = "active"
    entry["status"] = "active"
    entry["proposed_disposition"] = "retain_active"
    entry["target_paths"] = [entry["path"]]

    with pytest.raises(CorpusManifestError, match="current frontmatter classifies"):
        validate_corpus_manifest(REPO_ROOT, _write_manifest(tmp_path, manifest))


def test_strict_yaml_rejects_duplicate_mapping_keys(tmp_path: Path) -> None:
    path = tmp_path / "CORPUS-MANIFEST.yaml"
    source = MANIFEST_PATH.read_text()
    path.write_text(
        source.replace(
            "manifest_version: 2\n", "manifest_version: 2\nmanifest_version: 2\n", 1
        )
    )

    with pytest.raises(CorpusManifestError, match="duplicate key"):
        validate_corpus_manifest(REPO_ROOT, path)


def test_promotion_bar_rejects_pending_root_and_non_active_sources() -> None:
    with pytest.raises(CorpusManifestError) as raised:
        validate_corpus_manifest(REPO_ROOT, promotion_bar=True)

    message = str(raised.value)
    assert "promotion bar: pending adjudication remains" in message
    assert "promotion bar: source Markdown remains at repository root" in message
    assert "promotion bar: source documents are not ACTIVE" in message
    assert "trusted claim-bound evidence and independent review authority are not deployed" in message
    assert "has empty adjudication evidence" in message
    assert "existing ACTIVE status is shadow/grandfathered, not proof" in message
