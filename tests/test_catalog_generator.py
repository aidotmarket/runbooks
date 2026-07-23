from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from runbook_tools.catalog.generator import (
    CATALOG_PATH,
    README_PATH,
    ROUTER_PATH,
    build_catalog,
    check_catalog,
    generate_catalog,
    render_outputs,
    source_paths,
)
from runbook_tools.catalog.model import CatalogError, REQUIRED_ACTIVE_FIELDS


REPO_ROOT = Path(__file__).parent.parent
KERNEL_FIXTURES = Path(__file__).parent / "fixtures" / "catalog" / "kernel_companions"
SEED_IDS = [
    "agent-dispatch",
    "build-queue-reconciliation",
    "council",
    "council-gate-process",
    "council-hall-deliberation",
]
E2E_IDS = [
    "boot-kernel-companion-crosswalk",
    "e2e-programme-integrity",
    "e2e-test-status-publisher",
    "e2e-video-review",
]
KERNEL_IDS = [
    "agent-completeness",
    "aging-policy",
    "constitution-history",
    "council-roster-quirks",
    "gate-procedure",
    "infrastructure-discovery",
    "product-elaboration",
]


def _metadata(runbook_id: str, *, topic: str | None = None) -> dict:
    return {
        "runbook_id": runbook_id,
        "domain": "test-domain",
        "status": "ACTIVE",
        "authoritative_for": [{"topic": topic or f"{runbook_id}-topic", "section": "Overview"}],
        "aliases": [],
        "error_signatures": [],
        "supersedes": [],
        "superseded_by": [],
        "owner": "test-owner",
        "last_verified_at": "2026-07-17",
    }


def _write_doc(root: Path, relative: str, metadata: dict | None) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = ""
    if metadata is not None:
        frontmatter = "---\n" + yaml.safe_dump(metadata, sort_keys=False) + "---\n\n"
    path.write_text(frontmatter + "# Fixture\n\n## Overview\n\nFixture body.\n")
    return path


def _write_readme(root: Path) -> None:
    (root / README_PATH).write_text(
        "# Fixture Runbooks\n\n"
        "Cataloged documents are declared explicitly.\n\n"
        "## Adoption status\n\n"
        "| System | Runbook | Status |\n"
        "|---|---|---|\n"
        "| None | — | NOT_STARTED |\n\n"
        "## Status values\n\n"
        "Hand-authored help remains outside the generated block.\n"
    )


def _digest_outputs(root: Path) -> dict[str, str]:
    return {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in (CATALOG_PATH, ROUTER_PATH, README_PATH)
    }


def test_live_catalog_has_five_seed_and_seven_kernel_companion_members() -> None:
    catalog, grandfathered = build_catalog(REPO_ROOT)

    assert [entry["runbook_id"] for entry in catalog["entries"]] == sorted(
        SEED_IDS + KERNEL_IDS + E2E_IDS
    )
    assert {entry["path"] for entry in catalog["entries"]} == {
        "runbooks/agent-completeness.md",
        "runbooks/agent-dispatch.md",
        "runbooks/aging-policy.md",
        "runbooks/build-queue-reconciliation.md",
        "runbooks/constitution-history.md",
        "runbooks/council-gate-process.md",
        "runbooks/council-hall-deliberation.md",
        "runbooks/council-roster-quirks.md",
        "runbooks/council.md",
        "runbooks/gate-procedure.md",
        "runbooks/infrastructure-discovery.md",
        "runbooks/product-elaboration.md",
        "runbooks/boot-kernel-companion-crosswalk.md",
        "e2e-programme-integrity.md",
        "e2e-test-status-publisher.md",
        "e2e-video-review.md",
    }
    assert grandfathered == 82
    assert not (REPO_ROOT / "RUNBOOK-CATALOG.json").exists()


def test_source_set_is_bounded_and_excludes_generated_and_non_source_paths(tmp_path: Path) -> None:
    expected = _write_doc(tmp_path, "root.md", None)
    nested = _write_doc(tmp_path, "runbooks/nested/member.md", None)
    for relative in (
        "README.md",
        "TOPIC-ROUTER.md",
        "archive/old.md",
        "runbooks/archive/old.md",
        "specs/spec.md",
        "audits/audit.md",
        "tests/test.md",
        "templates/template.md",
    ):
        _write_doc(tmp_path, relative, None)

    assert source_paths(tmp_path) == [expected, nested]


@pytest.mark.parametrize("missing_field", sorted(REQUIRED_ACTIVE_FIELDS))
def test_missing_required_active_field_fails_before_writes(tmp_path: Path, missing_field: str) -> None:
    metadata = _metadata("member")
    metadata.pop(missing_field)
    _write_doc(tmp_path, "runbooks/member.md", metadata)
    (tmp_path / CATALOG_PATH).write_bytes(b"catalog sentinel\n")
    (tmp_path / ROUTER_PATH).write_bytes(b"router sentinel\n")
    (tmp_path / README_PATH).write_bytes(b"readme sentinel\n")
    before = {path: (tmp_path / path).read_bytes() for path in (CATALOG_PATH, ROUTER_PATH, README_PATH)}

    with pytest.raises(CatalogError):
        generate_catalog(tmp_path)

    assert {path: (tmp_path / path).read_bytes() for path in before} == before


def test_grandfathered_document_is_accepted_and_absent_from_indexes(tmp_path: Path) -> None:
    _write_doc(tmp_path, "legacy.md", None)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))

    catalog, grandfathered = build_catalog(tmp_path)

    assert grandfathered == 1
    assert [entry["runbook_id"] for entry in catalog["entries"]] == ["member"]
    assert "legacy" not in json.dumps(catalog)


def test_extra_shape_in_required_active_field_fails(tmp_path: Path) -> None:
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["invented"] = "not-allowed"
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match="exactly topic and section"):
        build_catalog(tmp_path)


def test_stable_sorting_newline_and_two_run_idempotency(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    second = _metadata("zeta")
    second["aliases"] = ["zeta-old", "zeta-legacy"]
    second["authoritative_for"] = [
        {"topic": "zeta-topic", "section": "Overview"},
        {"topic": "middle-topic", "section": "Overview"},
    ]
    _write_doc(tmp_path, "runbooks/zeta.md", second)
    _write_doc(tmp_path, "alpha.md", _metadata("alpha"))

    generate_catalog(tmp_path)
    first = _digest_outputs(tmp_path)
    generate_catalog(tmp_path)
    second_digest = _digest_outputs(tmp_path)
    catalog = json.loads((tmp_path / CATALOG_PATH).read_text())

    assert first == second_digest
    assert [entry["runbook_id"] for entry in catalog["entries"]] == ["alpha", "zeta"]
    assert list(catalog["indexes"]["aliases"]) == ["zeta-legacy", "zeta-old"]
    assert all((tmp_path / path).read_bytes().endswith(b"\n") for path in first)
    assert check_catalog(tmp_path) == []


def test_router_and_readme_are_rendered_from_catalog(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    metadata = _metadata("member", topic="catalog-topic")
    metadata["error_signatures"] = [{"signature": "CATALOG_BROKEN", "section": "Overview"}]
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    outputs = render_outputs(tmp_path)
    catalog = json.loads(outputs[CATALOG_PATH])
    router = outputs[ROUTER_PATH].decode()
    readme = outputs[README_PATH].decode()

    assert catalog["indexes"]["topics"]["catalog-topic"]["runbook_id"] == "member"
    assert "`catalog-topic`" in router
    assert "`CATALOG_BROKEN`" in router
    assert "ACTIVE catalog members: **1**" in readme
    assert "Grandfathered source documents" in readme
    assert "Every runbook conforms" not in readme
    assert "Hand-authored help remains outside" in readme


@pytest.mark.parametrize("drifted_path", [CATALOG_PATH, ROUTER_PATH, README_PATH])
def test_check_fails_for_each_generated_output_drift(tmp_path: Path, drifted_path: str) -> None:
    _write_readme(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    generate_catalog(tmp_path)
    path = tmp_path / drifted_path
    content = path.read_bytes()
    if drifted_path == README_PATH:
        content = content.replace(b"ACTIVE catalog members", b"ACTIVE catalog memberz", 1)
    elif drifted_path == CATALOG_PATH:
        content = content.replace(b'"schema_version": 1', b'"schema_version": 2', 1)
    else:
        content = content.replace(b"Generated", b"GeneratEd", 1)
    path.write_bytes(content)

    assert check_catalog(tmp_path) == [drifted_path]


def test_check_reports_every_drifted_output(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    generate_catalog(tmp_path)
    (tmp_path / CATALOG_PATH).write_text("{}\n")
    (tmp_path / ROUTER_PATH).write_text("drift\n")
    readme = (tmp_path / README_PATH).read_text().replace("ACTIVE catalog members", "ACTIVE catalog memberz")
    (tmp_path / README_PATH).write_text(readme)

    assert check_catalog(tmp_path) == [CATALOG_PATH, ROUTER_PATH, README_PATH]


def test_conflicting_topic_fails_generation(tmp_path: Path) -> None:
    _write_doc(tmp_path, "a.md", _metadata("alpha", topic="shared-topic"))
    _write_doc(tmp_path, "runbooks/b.md", _metadata("beta", topic="shared-topic"))

    with pytest.raises(CatalogError, match="duplicate topic"):
        build_catalog(tmp_path)


def test_duplicate_runbook_id_fails_generation(tmp_path: Path) -> None:
    _write_doc(tmp_path, "runbooks/first.md", _metadata("duplicate-member"))
    _write_doc(tmp_path, "runbooks/second.md", _metadata("duplicate-member"))

    with pytest.raises(CatalogError, match="duplicate runbook_id"):
        build_catalog(tmp_path)


def test_kernel_companion_ids_register_together() -> None:
    catalog, grandfathered = build_catalog(KERNEL_FIXTURES)

    assert grandfathered == 0
    assert [entry["runbook_id"] for entry in catalog["entries"]] == KERNEL_IDS
    assert list(catalog["indexes"]["topics"]) == KERNEL_IDS
    for entry in catalog["entries"]:
        source = (KERNEL_FIXTURES / entry["path"]).read_text()
        assert f"## {entry['authoritative_for'][0]['section']}" in source
