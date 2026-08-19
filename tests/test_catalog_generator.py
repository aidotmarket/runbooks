from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

import runbook_tools.catalog.generator as generator_module
from runbook_tools.catalog.generator import (
    CATALOG_PATH,
    CORPUS_MANIFEST_PATH,
    README_PATH,
    ROUTER_PATH,
    build_catalog,
    check_catalog,
    generate_catalog,
    render_outputs,
    source_paths,
)
from runbook_tools.catalog.model import REQUIRED_ACTIVE_FIELDS, CatalogError
from runbook_tools.lint.conformance import structural_conformance_failures
from runbook_tools.parser.markdown_ast import parse_markdown, walk_tokens
from tests.catalog_test_support import (
    conformant_catalog_document,
    ensure_catalog_schemas,
)

REPO_ROOT = Path(__file__).parent.parent
KERNEL_FIXTURES = Path(__file__).parent / "fixtures" / "catalog" / "kernel_companions"
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
        "owner": "sysadmin",
        "owner_agent": "sysadmin",
        "last_verified_at": "2026-07-17",
    }


def _write_doc(root: Path, relative: str, metadata: dict | None) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_catalog_schemas(root)
    if metadata is None:
        path.write_text("# Fixture\n\n## Overview\n\nFixture body.\n")
    else:
        path.write_text(conformant_catalog_document(metadata))
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


def _clone_with_projection_policy(tmp_path: Path) -> Path:
    clone = tmp_path / "alternate-history"
    subprocess.run(
        ["git", "clone", "-q", "--no-hardlinks", str(REPO_ROOT), str(clone)],
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Projection Test"],
        cwd=clone,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "projection@example.invalid"],
        cwd=clone,
        check=True,
    )
    shutil.copy2(
        REPO_ROOT / generator_module.LEGACY_PROJECTION_POLICY_PATH,
        clone / generator_module.LEGACY_PROJECTION_POLICY_PATH,
    )
    return clone


def _unrelated_commit_with_existing_catalog(root: Path) -> str:
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return subprocess.run(
        ["git", "commit-tree", tree, "-m", "unrelated existing-ID history"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _markdown_link_targets(markdown: str) -> list[str]:
    return [
        str(token.get("attrs", {}).get("url"))
        for token, _ in walk_tokens(parse_markdown(markdown))
        if token.get("type") == "link"
    ]


def test_live_catalog_contains_every_source_without_a_brittle_roster() -> None:
    catalog, grandfathered = build_catalog(REPO_ROOT)

    expected: dict[str, str] = {}
    expected_grandfathered = 0
    for path in source_paths(REPO_ROOT):
        text = path.read_text()
        if not text.startswith("---\n"):
            expected_grandfathered += 1
            continue
        closing = text.find("\n---", 4)
        raw_frontmatter = text[4:closing] if closing >= 0 else ""
        if not any(line.startswith("runbook_id:") for line in raw_frontmatter.splitlines()):
            expected_grandfathered += 1
            continue
        metadata = yaml.safe_load(raw_frontmatter)
        if metadata.get("status") == "ACTIVE":
            expected[metadata["runbook_id"]] = path.relative_to(REPO_ROOT).as_posix()

    actual_paths = {entry["path"] for entry in catalog["entries"]}
    source_set = {
        path.relative_to(REPO_ROOT).as_posix() for path in source_paths(REPO_ROOT)
    }
    archive_set = set(generator_module._archive_markdown_paths(REPO_ROOT))
    active = {
        entry["runbook_id"]: entry["path"]
        for entry in catalog["entries"]
        if entry.get("status") == "ACTIVE"
    }
    assert actual_paths == source_set | archive_set
    assert active == expected
    assert grandfathered == expected_grandfathered
    assert len(catalog["entries"]) == len(source_set) + len(archive_set)
    assert {
        "agent-dispatch",
        "build-queue-reconciliation",
        "council",
        "infrastructure-discovery",
        "peer-instance-discipline",
    } <= active.keys()
    assert not (REPO_ROOT / "RUNBOOK-CATALOG.json").exists()


def test_reviewed_projection_freezes_exact_legacy_population_and_final_boot_delta() -> None:
    projection = generator_module._reviewed_legacy_projection(
        REPO_ROOT,
        revision="HEAD",
    )

    assert projection is not None
    assert len(projection.expected) == 26
    peer = projection.expected["peer-instance-discipline"]
    assert {
        row["topic"] for row in peer["authoritative_for"]
    } >= {
        "session-plan-runbook-context",
        "session-close-runbook-impact",
    }
    assert {
        row["signature"] for row in peer["error_signatures"]
    } >= {
        "runbook_context_delivery_unavailable",
        "runbook_impact_evidence_unavailable",
    }


def test_reviewed_projection_rejects_a_25_member_catalog() -> None:
    catalog, _ = build_catalog(REPO_ROOT)
    projection = generator_module._reviewed_legacy_projection(
        REPO_ROOT,
        revision="HEAD",
    )
    assert projection is not None
    entries = [entry for entry in catalog["entries"] if entry.get("status") == "ACTIVE"]
    removed = entries.pop()

    with pytest.raises(
        CatalogError,
        match=rf"legacy population differs.*missing={removed['runbook_id']}",
    ):
        generator_module._enforce_reviewed_legacy_projection(entries, projection)


def test_reviewed_projection_rejects_a_new_topic_on_an_existing_id() -> None:
    catalog, _ = build_catalog(REPO_ROOT)
    projection = generator_module._reviewed_legacy_projection(
        REPO_ROOT,
        revision="HEAD",
    )
    assert projection is not None
    entries = json.loads(
        json.dumps(
            [entry for entry in catalog["entries"] if entry.get("status") == "ACTIVE"]
        )
    )
    entries[0]["authoritative_for"].append(
        {"topic": "invented-authority", "section": "§E. Operate"}
    )

    with pytest.raises(CatalogError, match=r"authoritative_for differs"):
        generator_module._enforce_reviewed_legacy_projection(entries, projection)


def test_projection_policy_digest_pins_exact_final_bytes(tmp_path: Path) -> None:
    source = REPO_ROOT / generator_module.LEGACY_PROJECTION_POLICY_PATH
    payload = source.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == (
        generator_module.LEGACY_PROJECTION_POLICY_SHA256
    )
    dirty = tmp_path / "legacy_catalog_projection.policy.json"
    dirty.write_bytes(payload + b" ")

    with pytest.raises(CatalogError, match="projection policy digest mismatch"):
        generator_module._load_projection_policy(dirty)


def test_unrelated_history_with_existing_ids_cannot_validate_as_rollout_descendant(
    tmp_path: Path,
) -> None:
    clone = _clone_with_projection_policy(tmp_path)
    unrelated = _unrelated_commit_with_existing_catalog(clone)
    catalog = subprocess.run(
        ["git", "--no-replace-objects", "show", f"{unrelated}:CATALOG.json"],
        cwd=clone,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "peer-instance-discipline" in catalog

    with pytest.raises(CatalogError, match="not a descendant of immutable rollout"):
        generator_module._reviewed_legacy_projection(clone, revision=unrelated)


def test_projection_ancestry_ignores_local_replace_refs(tmp_path: Path) -> None:
    clone = _clone_with_projection_policy(tmp_path)
    unrelated = _unrelated_commit_with_existing_catalog(clone)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=clone,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "replace", head, unrelated], cwd=clone, check=True)
    control = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            generator_module.LEGACY_AUTHORITY_BASE_SHA,
            "HEAD",
        ],
        cwd=clone,
        check=False,
    )
    assert control.returncode == 1

    projection = generator_module._reviewed_legacy_projection(
        clone,
        revision="HEAD",
    )

    assert projection is not None
    assert len(projection.expected) == 26


def test_source_set_defaults_unknown_directories_into_adjudication_and_excludes_only_declared_non_sources(
    tmp_path: Path,
) -> None:
    expected = _write_doc(tmp_path, "root.md", None)
    nested = _write_doc(tmp_path, "runbooks/nested/member.md", None)
    operational = _write_doc(tmp_path, "ops/pending-verification.md", None)
    unknown_tree = _write_doc(tmp_path, "docs/new-operational-note.md", None)
    unknown_hidden = _write_doc(tmp_path, ".ops/current-recovery.MD", None)
    venv_prefixed_file = _write_doc(tmp_path, ".venv-recovery.MD", None)
    nested_archive_name = _write_doc(
        tmp_path, "customer/archive/current-procedure.md", None
    )
    nested_runbook_archive_name = _write_doc(
        tmp_path, "runbooks/archive/old.md", None
    )
    for relative in (
        "README.md",
        "TOPIC-ROUTER.md",
        "archive/old.md",
        "contracts/README.md",
        "specs/spec.md",
        "audits/audit.md",
        "tests/test.md",
        "templates/template.md",
        ".cache/ignored.md",
        "node_modules/package/ignored.md",
    ):
        _write_doc(tmp_path, relative, None)

    assert source_paths(tmp_path) == [
        unknown_hidden,
        venv_prefixed_file,
        nested_archive_name,
        unknown_tree,
        operational,
        expected,
        nested_runbook_archive_name,
        nested,
    ]


def test_source_discovery_fails_closed_when_walk_reports_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    denied = tmp_path / "docs"

    def denied_walk(*_args: object, **kwargs: object) -> object:
        onerror = kwargs["onerror"]
        assert callable(onerror)
        onerror(PermissionError(13, "permission denied", str(denied)))
        return iter(())

    monkeypatch.setattr(generator_module.os, "walk", denied_walk)

    with pytest.raises(CatalogError, match="source discovery cannot read"):
        source_paths(tmp_path)


def test_admitted_source_symlink_cannot_be_followed(tmp_path: Path) -> None:
    target = _write_doc(tmp_path, "specs/target.md", None)
    source = tmp_path / "docs" / "current.md"
    source.parent.mkdir()
    source.symlink_to(target)

    with pytest.raises(CatalogError, match="must not be a symlink"):
        source_paths(tmp_path)


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


def test_no_frontmatter_document_is_indexed_without_authority(tmp_path: Path) -> None:
    _write_doc(tmp_path, "legacy.md", None)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))

    catalog, grandfathered = build_catalog(tmp_path)

    assert grandfathered == 1
    legacy = next(entry for entry in catalog["entries"] if entry["path"] == "legacy.md")
    assert legacy["runbook_id"] == "path:legacy.md"
    assert legacy["catalog_state"] == "grandfathered"
    assert catalog["discovery_entry_defaults"]["authority_admission"] is False
    assert catalog["discovery_entry_defaults"]["action_authority_eligible"] is False


def test_declared_active_page_keeps_exact_authority_fields(tmp_path: Path) -> None:
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))

    catalog, _ = build_catalog(tmp_path)
    entry = catalog["entries"][0]

    assert {
        field: entry[field]
        for field in (
            "integrity_only",
            "integrity_status",
            "semantic_verification",
            "authority_admission",
            "action_authority_eligible",
        )
    } == {
        "integrity_only": True,
        "integrity_status": "integrity_pass_unverified",
        "semantic_verification": False,
        "authority_admission": False,
        "action_authority_eligible": False,
    }


def test_archived_manifest_page_is_indexed_and_visibly_non_authoritative(
    tmp_path: Path,
) -> None:
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    archived = _write_doc(tmp_path, "archive/history.md", None)
    (tmp_path / "CORPUS-MANIFEST.yaml").write_text(
        "policy:\n"
        "  archive_is_recoverable: true\n"
        "documents:\n"
        "  - path: archive/history.md\n"
        "    catalog_state: archived\n"
        "    status: archived\n"
    )

    catalog, _ = build_catalog(tmp_path)

    entry = next(row for row in catalog["entries"] if row["path"] == "archive/history.md")
    assert archived.is_file()
    assert entry["catalog_state"] == "archived"
    assert entry["status"] == "archived"
    assert catalog["discovery_entry_defaults"]["authority_admission"] is False


def test_unclassified_archive_page_refuses_before_generated_outputs_are_written(
    tmp_path: Path,
) -> None:
    _write_readme(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    _write_doc(tmp_path, "archive/orphan.md", None)
    readme_before = (tmp_path / README_PATH).read_bytes()

    with pytest.raises(CatalogError, match=r"archive/orphan\.md"):
        build_catalog(tmp_path)
    with pytest.raises(CatalogError, match=r"archive/orphan\.md"):
        generate_catalog(tmp_path)

    assert not (tmp_path / CATALOG_PATH).exists()
    assert not (tmp_path / ROUTER_PATH).exists()
    assert (tmp_path / README_PATH).read_bytes() == readme_before

    (tmp_path / CORPUS_MANIFEST_PATH).write_text(
        "policy:\n"
        "  archive_is_recoverable: true\n"
        "documents:\n"
        "  - path: archive/orphan.md\n"
        "    catalog_state: archived\n"
        "    status: archived\n"
    )
    generate_catalog(tmp_path)

    catalog = json.loads((tmp_path / CATALOG_PATH).read_text())
    assert any(row["path"] == "archive/orphan.md" for row in catalog["entries"])


def test_page_that_fails_integrity_marker_refuses_admission(
    tmp_path: Path,
) -> None:
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        path.read_text().replace(
            "last_refresh_date: 2026-04-21T17:30:00Z",
            "last_refresh_date: 2026-07-18T00:00:00Z",
            1,
        )
    )

    with pytest.raises(
        CatalogError,
        match=r"§J field last_refresh_date cannot be in the future",
    ):
        build_catalog(
            tmp_path,
            current_utc_datetime=datetime(2026, 7, 17, 23, 59, 59),
        )


def test_router_surfaces_non_active_page_as_discovery_only(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    _write_doc(tmp_path, "legacy.md", None)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))

    router = render_outputs(tmp_path)[ROUTER_PATH].decode()

    assert "## Current discovery-only pages" in router
    assert "legacy.md" in router
    assert "not authority" in router


@pytest.mark.parametrize(
    "relative",
    [
        "member.md",
        "runbooks/wrong-name.md",
        "runbooks/nested/member.md",
        "runbooks/member](https-evil).md",
    ],
)
def test_active_member_requires_exact_canonical_runbook_path(
    tmp_path: Path,
    relative: str,
) -> None:
    _write_doc(tmp_path, relative, _metadata("member"))

    with pytest.raises(
        CatalogError,
        match=r"ACTIVE path must be canonical 'runbooks/member\.md'",
    ):
        build_catalog(tmp_path)


def test_extra_shape_in_required_active_field_fails(tmp_path: Path) -> None:
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["invented"] = "not-allowed"
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match="exactly topic and section"):
        build_catalog(tmp_path)


def test_active_status_without_runbook_id_is_discoverable_not_authority(
    tmp_path: Path,
) -> None:
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        path.read_text()
        .replace("runbook_id: member\n", "", 1)
        .replace("status: ACTIVE", 'status: "ACTIVE"', 1)
    )

    catalog, grandfathered = build_catalog(tmp_path)

    assert grandfathered == 1
    assert catalog["entries"][0]["runbook_id"] == "path:runbooks/member.md"
    assert catalog["entries"][0]["catalog_state"] == "grandfathered"


def test_draft_status_without_runbook_id_is_discoverable_not_authority(
    tmp_path: Path,
) -> None:
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        path.read_text()
        .replace("runbook_id: member\n", "", 1)
        .replace("status: ACTIVE", "status: DRAFT", 1)
    )

    catalog, grandfathered = build_catalog(tmp_path)

    assert grandfathered == 1
    assert catalog["entries"][0]["status"] == "DRAFT"
    assert catalog["entries"][0]["catalog_state"] == "grandfathered"


@pytest.mark.parametrize(
    "frontmatter",
    [
        (
            '"runbook_id": member\n'
            '"runbook_id": duplicate\n'
            '"status": ACTIVE\n'
        ),
        (
            '"\\x72unbook_id": member\n'
            '"\\x72unbook_id": duplicate\n'
            '"status": ACTIVE\n'
        ),
        '"runbook_id": [unterminated\n"status": ACTIVE\n',
        '"owner": [unterminated\n',
    ],
)
def test_quoted_or_escaped_catalog_key_parse_failures_are_fail_closed(
    tmp_path: Path,
    frontmatter: str,
) -> None:
    ensure_catalog_schemas(tmp_path)
    (tmp_path / "runbooks").mkdir()
    (tmp_path / "runbooks/member.md").write_text(
        f"---\n{frontmatter}---\n\n# Malformed Catalog Opt-in\n"
    )

    with pytest.raises(CatalogError, match="invalid YAML frontmatter"):
        build_catalog(tmp_path)


@pytest.mark.parametrize(
    "frontmatter",
    [
        "%BROKEN\nstatus: ACTIVE\nrunbook_id: hidden-active\n",
        "@bad\nstatus: ACTIVE\nrunbook_id: hidden-active\n",
        'title: "unterminated\nstatus: ACTIVE\nrunbook_id: hidden-active\n',
        '%BROKEN\n"status": ACTIVE\n"runbook_id": hidden-active\n',
        '%BROKEN\n"\\x73tatus": ACTIVE\n"\\x72unbook_id": hidden-active\n',
        "%BROKEN\n? status\n: ACTIVE\n? runbook_id\n: hidden-active\n",
        "%BROKEN\n? !!str status\n: ACTIVE\n? !!str runbook_id\n: hidden-active\n",
        "%BROKEN\n? |-\n  status\n: ACTIVE\n? |-\n  runbook_id\n: hidden-active\n",
    ],
)
def test_catalog_keys_after_early_yaml_error_cannot_evade_admission(
    tmp_path: Path,
    frontmatter: str,
) -> None:
    ensure_catalog_schemas(tmp_path)
    (tmp_path / "runbooks").mkdir()
    (tmp_path / "runbooks/hidden-active.md").write_text(
        f"---\n{frontmatter}---\n\n# Hidden\n"
    )

    with pytest.raises(CatalogError, match="invalid YAML frontmatter"):
        build_catalog(tmp_path)


def test_unclosed_catalog_frontmatter_cannot_be_grandfathered(
    tmp_path: Path,
) -> None:
    ensure_catalog_schemas(tmp_path)
    (tmp_path / "runbooks").mkdir()
    (tmp_path / "runbooks/hidden-active.md").write_text(
        "---\n"
        "status: ACTIVE\n"
        "runbook_id: hidden-active\n"
        "# missing closing delimiter\n"
    )

    with pytest.raises(CatalogError, match="missing its closing delimiter"):
        build_catalog(tmp_path)


@pytest.mark.parametrize("status", ["ACTVE", "ARCHIVED", "active", "RETIRED"])
def test_non_active_declared_status_remains_discoverable(
    tmp_path: Path,
    status: str,
) -> None:
    metadata = _metadata("member")
    metadata["status"] = status
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    catalog, grandfathered = build_catalog(tmp_path)

    assert grandfathered == 1
    assert catalog["entries"][0]["runbook_id"] == "member"
    assert catalog["entries"][0]["status"] == status
    assert catalog["entries"][0]["catalog_state"] == "grandfathered"


def test_catalog_frontmatter_anchors_and_aliases_fail_closed(
    tmp_path: Path,
) -> None:
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        path.read_text()
        .replace("owner: sysadmin", "owner: &owner sysadmin", 1)
        .replace("owner_agent: sysadmin", "owner_agent: *owner", 1)
    )

    with pytest.raises(
        CatalogError,
        match=r"(?s)invalid YAML frontmatter.*anchors and aliases are not allowed",
    ):
        build_catalog(tmp_path)


def test_thematic_break_pseudo_frontmatter_remains_grandfathered(
    tmp_path: Path,
) -> None:
    ensure_catalog_schemas(tmp_path)
    (tmp_path / "legacy.md").write_text(
        "---\nthis: is: deliberately not yaml\n---\n\n# Legacy\n"
    )

    catalog, grandfathered = build_catalog(tmp_path)

    assert catalog["entries"][0]["path"] == "legacy.md"
    assert catalog["entries"][0]["catalog_state"] == "grandfathered"
    assert grandfathered == 1


def test_owner_must_equal_owner_agent(tmp_path: Path) -> None:
    metadata = _metadata("member")
    metadata["owner_agent"] = "mars"
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match="owner .* must equal owner_agent"):
        build_catalog(tmp_path)


def test_working_generation_rejects_future_last_verified_at(tmp_path: Path) -> None:
    metadata = _metadata("member")
    metadata["last_verified_at"] = "2026-07-18"
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match="after the verification clock 2026-07-17"):
        build_catalog(tmp_path, current_utc_date=date(2026, 7, 17))


def test_a_to_k_conformance_is_a_convention_and_never_an_admission_condition(
    tmp_path: Path,
) -> None:
    """A page's shape must not decide whether it can be found.

    Max directive S1491 and AC9 of the approved truth-layer design. The
    deterministic A-K checks still fire - they are advice to the author through
    ``runbook-lint`` - but a page that fails them is still indexed, because an
    unfindable correct page is worse than a findable untidy one.
    """

    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        re.sub(
            r"(?ms)^## §E\..*?(?=^## §F\.)",
            "",
            path.read_text(),
            count=1,
        )
    )

    catalog, _ = build_catalog(tmp_path)

    assert [entry["runbook_id"] for entry in catalog["entries"]] == ["member"]

    findings = structural_conformance_failures(
        path.read_text(),
        REPO_ROOT / "schemas",
    )
    assert any("§E" in finding.message for finding in findings), (
        "the checks must still detect the missing section; only their authority "
        "to refuse admission is removed"
    )


@pytest.mark.parametrize(
    "body",
    [
        "",
        "TODO: document this procedure.",
        "<!-- catalog:historical -->\nOld details.\n<!-- /catalog:historical -->",
    ],
)
def test_authoritative_section_requires_substantive_active_body(
    tmp_path: Path,
    body: str,
) -> None:
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        re.sub(
            r"(?ms)^## Overview\n.*\Z",
            f"## Overview\n\n{body}\n",
            path.read_text(),
        )
    )

    with pytest.raises(CatalogError, match="no substantive ACTIVE body"):
        build_catalog(tmp_path)


def test_nested_current_subsection_satisfies_authoritative_body(tmp_path: Path) -> None:
    path = _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    path.write_text(
        re.sub(
            r"(?ms)^## Overview\n.*\Z",
            "## Overview\n\n### Current procedure\n\nInvoke the checked endpoint.\n",
            path.read_text(),
        )
    )

    catalog, _ = build_catalog(tmp_path)

    assert catalog["entries"][0]["runbook_id"] == "member"


def test_stable_sorting_newline_and_two_run_idempotency(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    second = _metadata("zeta")
    second["aliases"] = ["zeta-old", "zeta-legacy"]
    second["authoritative_for"] = [
        {"topic": "zeta-topic", "section": "Overview"},
        {"topic": "middle-topic", "section": "Overview"},
    ]
    _write_doc(tmp_path, "runbooks/zeta.md", second)
    _write_doc(tmp_path, "runbooks/alpha.md", _metadata("alpha"))

    generate_catalog(tmp_path)
    first = _digest_outputs(tmp_path)
    generate_catalog(tmp_path)
    second_digest = _digest_outputs(tmp_path)
    catalog = json.loads((tmp_path / CATALOG_PATH).read_text())

    assert first == second_digest
    assert [entry["runbook_id"] for entry in catalog["entries"]] == ["alpha", "zeta"]
    router = (tmp_path / ROUTER_PATH).read_text()
    assert router.index("`zeta-legacy`") < router.index("`zeta-old`")
    assert all((tmp_path / path).read_bytes().endswith(b"\n") for path in first)
    assert check_catalog(tmp_path) == []


def test_manual_draft_to_active_cannot_add_authority_or_mutate_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_readme(tmp_path)
    metadata = _metadata("novel-member")
    metadata["status"] = "DRAFT"
    source = _write_doc(tmp_path, "runbooks/novel-member.md", metadata)
    monkeypatch.setattr(
        generator_module,
        "_reviewed_legacy_projection",
        lambda _root, *, revision: generator_module._ReviewedLegacyProjection(
            expected={},
            allowed_paths={},
        ),
    )
    generate_catalog(tmp_path)
    before = {
        path: (tmp_path / path).read_bytes()
        for path in (CATALOG_PATH, ROUTER_PATH, README_PATH)
    }
    source.write_text(source.read_text().replace("status: DRAFT", "status: ACTIVE", 1))
    with pytest.raises(
        CatalogError,
        match="legacy population differs.*unexpected=novel-member",
    ):
        generate_catalog(tmp_path)
    with pytest.raises(
        CatalogError,
        match="legacy population differs.*unexpected=novel-member",
    ):
        check_catalog(tmp_path)

    assert {
        path: (tmp_path / path).read_bytes()
        for path in (CATALOG_PATH, ROUTER_PATH, README_PATH)
    } == before


@pytest.mark.parametrize(
    ("discovery_id", "active_aliases"),
    [
        ("shared", ["shared"]),
        ("member", []),
    ],
)
def test_discovery_id_cannot_collide_with_active_identity_and_mutate_outputs(
    tmp_path: Path,
    discovery_id: str,
    active_aliases: list[str],
) -> None:
    _write_readme(tmp_path)
    active = _metadata("member")
    active["aliases"] = active_aliases
    _write_doc(tmp_path, "runbooks/member.md", active)
    generate_catalog(tmp_path)
    before = {
        path: (tmp_path / path).read_bytes()
        for path in (CATALOG_PATH, ROUTER_PATH, README_PATH)
    }
    discovery = _metadata(discovery_id)
    discovery["status"] = "DRAFT"
    _write_doc(tmp_path, "legacy.md", discovery)

    with pytest.raises(CatalogError, match=rf"{discovery_id}"):
        generate_catalog(tmp_path)

    assert {
        path: (tmp_path / path).read_bytes()
        for path in (CATALOG_PATH, ROUTER_PATH, README_PATH)
    } == before


def test_any_alternate_git_repository_missing_exact_baseline_fails_closed(
    tmp_path: Path,
) -> None:
    _write_readme(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Alternate Repo"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "alternate@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://example.invalid/alternate-runbooks.git",
        ],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "alternate history"],
        cwd=tmp_path,
        check=True,
    )

    with pytest.raises(
        CatalogError,
        match="immutable legacy authority baseline is unavailable",
    ):
        build_catalog(tmp_path)


def test_router_and_readme_are_rendered_from_catalog(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    metadata = _metadata("member", topic="catalog-topic")
    metadata["error_signatures"] = [{"signature": "CATALOG_BROKEN", "section": "Overview"}]
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    outputs = render_outputs(tmp_path)
    catalog = json.loads(outputs[CATALOG_PATH])
    router = outputs[ROUTER_PATH].decode()
    readme = outputs[README_PATH].decode()

    assert "indexes" not in catalog
    assert "`catalog-topic`" in router
    assert "`CATALOG_BROKEN`" in router
    assert "Declared ACTIVE authority entries: **1**" in readme
    assert "Current discovery-only entries" in readme
    assert "Every runbook conforms" not in readme
    assert "Hand-authored help remains outside" in readme


@pytest.mark.parametrize(
    ("signature", "message"),
    [
        ("failure\n| forged | router | row |", "single-line"),
        ("failure ` closes code span", "backticks"),
        ("failure\x07hidden", "control or format"),
        ("failure\u202erow", "control or format"),
    ],
)
def test_error_signature_cannot_inject_generated_markdown(
    tmp_path: Path,
    signature: str,
    message: str,
) -> None:
    _write_readme(tmp_path)
    metadata = _metadata("member")
    metadata["error_signatures"] = [
        {"signature": signature, "section": "Overview"}
    ]
    _write_doc(tmp_path, "runbooks/member.md", metadata)
    (tmp_path / ROUTER_PATH).write_bytes(b"router sentinel\n")

    with pytest.raises(CatalogError, match=message):
        generate_catalog(tmp_path)

    assert (tmp_path / ROUTER_PATH).read_bytes() == b"router sentinel\n"


def test_error_signature_pipe_is_escaped_in_generated_router(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    metadata = _metadata("member")
    metadata["error_signatures"] = [
        {"signature": "failure | retry", "section": "Overview"}
    ]
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    router = render_outputs(tmp_path)[ROUTER_PATH].decode()

    assert "`failure \\| retry`" in router


def test_generated_section_label_cannot_inject_a_markdown_link(
    tmp_path: Path,
) -> None:
    _write_readme(tmp_path)
    section = "Overview](https://evil.example/path)"
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section"] = section
    path = _write_doc(tmp_path, "runbooks/member.md", metadata)
    path.write_text(path.read_text().replace("## Overview", f"## {section}", 1))

    outputs = render_outputs(tmp_path)
    router = outputs[ROUTER_PATH].decode()
    readme = outputs[README_PATH].decode()

    assert "Overview\\]" in router
    assert "Overview\\]" in readme
    targets = _markdown_link_targets(router + "\n" + readme)
    assert targets
    assert all(
        target == "runbooks/member.md"
        or target.startswith("runbooks/member.md#")
        for target in targets
    )


def test_generated_legacy_section_fragment_is_url_encoded(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    section = "Résumé [Ops]"
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section"] = section
    path = _write_doc(tmp_path, "runbooks/member.md", metadata)
    path.write_text(path.read_text().replace("## Overview", f"## {section}", 1))

    outputs = render_outputs(tmp_path)

    assert "runbooks/member.md#r%C3%A9sum%C3%A9-ops" in outputs[ROUTER_PATH].decode()
    assert "runbooks/member.md#r%C3%A9sum%C3%A9-ops" in outputs[README_PATH].decode()


def test_declared_legacy_section_rejects_colliding_heading_slug(
    tmp_path: Path,
) -> None:
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section"] = "Foo!"
    path = _write_doc(tmp_path, "runbooks/member.md", metadata)
    path.write_text(
        path.read_text().replace(
            "## Overview\n\nFixture body.",
            "## Foo\n\nA distinct current section.\n\n## Foo!\n\nFixture body.",
            1,
        )
    )

    with pytest.raises(
        CatalogError,
        match=r"legacy section 'Foo!' shares Markdown anchor #foo.*section_id",
    ):
        build_catalog(tmp_path)


def test_stable_section_id_disambiguates_colliding_heading_slug(
    tmp_path: Path,
) -> None:
    metadata = _metadata("member")
    metadata["authoritative_for"][0].update(
        {"section": "Foo!", "section_id": "foo-bang"}
    )
    path = _write_doc(tmp_path, "runbooks/member.md", metadata)
    path.write_text(
        path.read_text().replace(
            "## Overview\n\nFixture body.",
            "## Foo\n\nA distinct current section.\n\n"
            '<a id="rb-section-foo-bang"></a>\n'
            "## Foo!\n\nFixture body.",
            1,
        )
    )

    catalog, _ = build_catalog(tmp_path)

    assert catalog["entries"][0]["authoritative_for"][0]["section_id"] == (
        "foo-bang"
    )


@pytest.mark.parametrize(
    ("section", "message"),
    [
        ("Overview `forged`", "backticks"),
        ("Overview\nforged", "single-line"),
        ("Overview\u2028forged", "single-line"),
        ("Overview\u202eforged", "control or format"),
    ],
)
def test_generated_section_text_rejects_unsafe_characters(
    tmp_path: Path,
    section: str,
    message: str,
) -> None:
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section"] = section
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match=message):
        build_catalog(tmp_path)


@pytest.mark.parametrize(
    ("owner", "message"),
    [
        ("sysadmin `forged`", "backticks"),
        ("sysadmin\nforged", "single-line"),
        ("sysadmin\u202eforged", "control or format"),
    ],
)
def test_generated_owner_text_rejects_unsafe_characters(
    tmp_path: Path,
    owner: str,
    message: str,
) -> None:
    metadata = _metadata("member")
    metadata["owner"] = owner
    metadata["owner_agent"] = owner
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match=message):
        build_catalog(tmp_path)


def test_optional_stable_section_id_is_serialized_and_used_for_links(
    tmp_path: Path,
) -> None:
    _write_readme(tmp_path)
    metadata = _metadata("member", topic="catalog-topic")
    metadata["aliases"] = ["member-alias"]
    metadata["authoritative_for"][0]["section_id"] = "overview"
    metadata["error_signatures"] = [
        {
            "signature": "CATALOG_BROKEN",
            "section": "Overview",
            "section_id": "overview",
        }
    ]
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    outputs = render_outputs(tmp_path)
    catalog = json.loads(outputs[CATALOG_PATH])
    entry = catalog["entries"][0]

    assert catalog["schema_version"] == 3
    assert entry["authoritative_for"][0]["section_id"] == "overview"
    assert entry["error_signatures"][0]["section_id"] == "overview"
    assert "runbooks/member.md#rb-section-overview" in outputs[ROUTER_PATH].decode()
    assert "runbooks/member.md#rb-section-overview" in outputs[README_PATH].decode()


def test_legacy_metadata_omits_section_id_without_schema_or_link_drift(
    tmp_path: Path,
) -> None:
    _write_readme(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))

    outputs = render_outputs(tmp_path)
    catalog = json.loads(outputs[CATALOG_PATH])

    assert catalog["schema_version"] == 3
    assert "section_id" not in json.dumps(catalog)
    assert "runbooks/member.md#overview" in outputs[ROUTER_PATH].decode()
    assert "rb-section" not in outputs[ROUTER_PATH].decode()


def test_optional_section_id_must_be_lowercase_kebab_case(tmp_path: Path) -> None:
    metadata = _metadata("member")
    metadata["authoritative_for"][0]["section_id"] = "Not Stable"
    _write_doc(tmp_path, "runbooks/member.md", metadata)

    with pytest.raises(CatalogError, match="section_id.*lowercase kebab-case"):
        build_catalog(tmp_path)


@pytest.mark.parametrize("drifted_path", [CATALOG_PATH, ROUTER_PATH, README_PATH])
def test_check_fails_for_each_generated_output_drift(tmp_path: Path, drifted_path: str) -> None:
    _write_readme(tmp_path)
    _write_doc(tmp_path, "runbooks/member.md", _metadata("member"))
    generate_catalog(tmp_path)
    path = tmp_path / drifted_path
    content = path.read_bytes()
    if drifted_path == README_PATH:
        content = content.replace(
            b"Declared ACTIVE authority entries",
            b"Declared ACTIVE authority entriez",
            1,
        )
    elif drifted_path == CATALOG_PATH:
        content = content.replace(b'"schema_version":3', b'"schema_version":1', 1)
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
    readme = (tmp_path / README_PATH).read_text().replace(
        "Declared ACTIVE authority entries",
        "Declared ACTIVE authority entriez",
    )
    (tmp_path / README_PATH).write_text(readme)

    assert check_catalog(tmp_path) == [CATALOG_PATH, ROUTER_PATH, README_PATH]


def test_conflicting_topic_fails_generation(tmp_path: Path) -> None:
    _write_doc(tmp_path, "runbooks/alpha.md", _metadata("alpha", topic="shared-topic"))
    _write_doc(tmp_path, "runbooks/beta.md", _metadata("beta", topic="shared-topic"))

    with pytest.raises(CatalogError, match="duplicate topic"):
        build_catalog(tmp_path)


def _assign_resolver_key(metadata: dict, namespace: str, key: str) -> None:
    if namespace == "runbook_id":
        metadata["runbook_id"] = key
    elif namespace == "alias":
        metadata["aliases"] = [key]
    elif namespace == "topic":
        metadata["authoritative_for"][0]["topic"] = key
    elif namespace == "error_signature":
        metadata["error_signatures"] = [
            {"signature": key, "section": "Overview"}
        ]
    else:
        raise AssertionError(namespace)


@pytest.mark.parametrize(
    ("left_namespace", "right_namespace"),
    [
        ("runbook_id", "alias"),
        ("runbook_id", "topic"),
        ("runbook_id", "error_signature"),
        ("alias", "topic"),
        ("alias", "error_signature"),
        ("topic", "error_signature"),
    ],
)
@pytest.mark.parametrize("same_entry", [False, True])
def test_all_bare_resolver_namespaces_share_one_global_keyspace(
    tmp_path: Path,
    left_namespace: str,
    right_namespace: str,
    same_entry: bool,
) -> None:
    left = _metadata("alpha")
    _assign_resolver_key(left, left_namespace, "shared")
    if same_entry:
        if right_namespace == "topic" and left_namespace in {
            "runbook_id",
            "alias",
        }:
            left["authoritative_for"].append(
                {"topic": "shared", "section": "§E. Operate"}
            )
        elif right_namespace == "error_signature":
            left["error_signatures"] = [
                {"signature": "shared", "section": "§E. Operate"}
            ]
        else:
            _assign_resolver_key(left, right_namespace, "shared")
    _write_doc(tmp_path, f"runbooks/{left['runbook_id']}.md", left)

    if not same_entry:
        right = _metadata("beta")
        _assign_resolver_key(right, right_namespace, "shared")
        _write_doc(tmp_path, f"runbooks/{right['runbook_id']}.md", right)

    with pytest.raises(CatalogError, match="shared"):
        build_catalog(tmp_path)


def test_kernel_companion_ids_register_together(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    ensure_catalog_schemas(tmp_path)
    (tmp_path / "runbooks").mkdir()
    for source in KERNEL_FIXTURES.glob("*.md"):
        metadata = yaml.safe_load(source.read_text().split("---", 2)[1])
        metadata["owner"] = "sysadmin"
        metadata["owner_agent"] = "sysadmin"
        (tmp_path / "runbooks" / source.name).write_text(
            conformant_catalog_document(metadata, title=source.stem)
        )

    catalog, grandfathered = build_catalog(tmp_path)

    assert grandfathered == 0
    assert [entry["runbook_id"] for entry in catalog["entries"]] == KERNEL_IDS
    router = render_outputs(tmp_path)[ROUTER_PATH].decode()
    assert all(f"`{runbook_id}`" in router for runbook_id in KERNEL_IDS)
    for entry in catalog["entries"]:
        source = (tmp_path / entry["path"]).read_text()
        assert f"## {entry['authoritative_for'][0]['section']}" in source
