from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from runbook_tools.catalog.generator import generate_catalog
from runbook_tools.catalog.model import CatalogError
from runbook_tools.cli import (
    PROMOTION_AUTHORITY_UNAVAILABLE,
    catalog_pin_evidence_cmd,
    catalog_promote_cmd,
    new_cmd,
)
from runbook_tools.corpus_manifest import (
    PURPOSE,
    SOURCE_SELECTOR,
    pin_draft_promotion_evidence,
    refresh_corpus_manifest,
)
from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR


def test_documented_new_to_promote_path_never_creates_grandfathered_root_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    shutil.copytree(SCHEMAS_DIR, tmp_path / "schemas")
    (tmp_path / "README.md").write_text(
        "# Fixture runbooks\n\n"
        "<!-- runbook-catalog:begin -->\n"
        "<!-- runbook-catalog:end -->\n"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    created = runner.invoke(
        new_cmd,
        [
            "demo-runbook",
            "--owner",
            "sysadmin",
            "--domain",
            "test-domain",
        ],
    )
    draft_path = tmp_path / "runbooks" / "demo-runbook.md"
    assert created.exit_code == 0
    assert draft_path.is_file()
    assert not (tmp_path / "demo-runbook.md").exists()
    with pytest.raises(CatalogError, match="dangling section"):
        generate_catalog(tmp_path)
    assert not (tmp_path / "CATALOG.json").exists()

    variants = [
        _conformant_draft("demo-runbook") + "\n<<E_TOOL:optional>>\n",
        _conformant_draft("demo-runbook"),
    ]
    for source in variants:
        draft_path.write_text(source)
        generate_catalog(tmp_path)
        before_source = draft_path.read_bytes()
        before_catalog = (tmp_path / "CATALOG.json").read_bytes()

        refused = runner.invoke(catalog_promote_cmd, ["demo-runbook"])

        assert refused.exit_code == 1
        assert refused.output.strip() == PROMOTION_AUTHORITY_UNAVAILABLE
        assert draft_path.read_bytes() == before_source
        assert (tmp_path / "CATALOG.json").read_bytes() == before_catalog
        entries = json.loads(before_catalog)["entries"]
        assert len(entries) == 1
        assert entries[0]["path"] == "runbooks/demo-runbook.md"
        assert entries[0]["status"] == "DRAFT"
        assert entries[0]["catalog_state"] == "grandfathered"
        assert not (tmp_path / "demo-runbook.md").exists()


def test_decorative_low_risk_evidence_cannot_promote_or_mutate_authority(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, draft_path, _evidence_path = _promotion_repository(tmp_path, risk="P2")
    monkeypatch.chdir(root)

    before = {
        path: (root / path).read_bytes()
        for path in ("runbooks/demo-runbook.md", "CATALOG.json", "README.md")
    }

    promoted = CliRunner().invoke(catalog_promote_cmd, ["demo-runbook"])

    assert promoted.exit_code == 1
    assert promoted.output.strip() == PROMOTION_AUTHORITY_UNAVAILABLE
    assert "status: DRAFT" in draft_path.read_text()
    assert {path: (root / path).read_bytes() for path in before} == before


def test_decorative_unknown_and_invented_claim_cannot_promote(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, draft_path, _evidence_path = _promotion_repository(tmp_path, risk="P3")
    monkeypatch.chdir(root)
    source = draft_path.read_text()
    source = source.replace(
        "- section: B\n  status: VERIFIED\n  evidence_ids:\n  - implementation-source",
        "- section: B\n  status: UNKNOWN\n  gap:\n"
        "    gap_id: invented-gap\n"
        "    reason: This claim has no independent supporting evidence.\n"
        "    tracking_ref: ticket:invented-gap",
        1,
    )
    source = source.replace(
        "## §B. Capability Matrix",
        "## §B. Capability Matrix\n\n"
        "Current state: UNKNOWN; gap: invented-gap.\n\n"
        "Invented current claim: this unsupported behavior is operational.",
        1,
    )
    draft_path.write_text(source)
    assert "Invented current claim" in source
    before = draft_path.read_bytes()

    result = CliRunner().invoke(catalog_promote_cmd, ["demo-runbook"])

    assert result.exit_code == 1
    assert result.output.strip() == PROMOTION_AUTHORITY_UNAVAILABLE
    assert draft_path.read_bytes() == before
    entries = json.loads((root / "CATALOG.json").read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["runbook_id"] == "demo-runbook"
    assert entries[0]["status"] == "DRAFT"
    assert entries[0]["catalog_state"] == "grandfathered"


def test_pin_evidence_mechanically_fills_digests_without_promoting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repository"
    _write_fixture_files(root)
    draft_path = root / "runbooks" / "demo-runbook.md"
    draft_path.write_text(_conformant_draft("demo-runbook") + _promotion_block("P2"))
    monkeypatch.chdir(root)

    pinned = CliRunner().invoke(catalog_pin_evidence_cmd, ["demo-runbook"])

    assert pinned.exit_code == 0, pinned.output
    payload = _promotion_payload(draft_path.read_text())
    evidence = payload["verified_against"][0]
    assert len(evidence["git_blob_oid"]) == 40
    assert len(evidence["content_sha256"]) == 64
    assert "status: DRAFT" in draft_path.read_text()
    assert "commit the DRAFT and evidence sources" in pinned.output
    assert "preparatory only" in pinned.output


def test_high_risk_author_supplied_receipt_id_never_self_certifies(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, draft_path, _evidence_path = _promotion_repository(
        tmp_path,
        risk="P1",
        server_receipt_id="runbook-promotion:author-asserted",
    )
    monkeypatch.chdir(root)
    before = draft_path.read_bytes()

    promoted = CliRunner().invoke(catalog_promote_cmd, ["demo-runbook"])

    assert promoted.exit_code == 1
    assert promoted.output.strip() == PROMOTION_AUTHORITY_UNAVAILABLE
    assert draft_path.read_bytes() == before


def test_dirty_manifest_and_schema_cannot_enable_promotion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, _draft_path, _evidence_path = _promotion_repository(tmp_path, risk="P2")
    monkeypatch.chdir(root)
    (root / "CORPUS-MANIFEST.yaml").write_text(
        "claimed_trusted_promotion: true\nreceipt: author-controlled\n"
    )
    (root / "schemas/runbook_promotion_receipt.schema.json").write_text("{}\n")
    before = {
        path: (root / path).read_bytes()
        for path in ("runbooks/demo-runbook.md", "CATALOG.json", "README.md")
    }

    promoted = CliRunner().invoke(catalog_promote_cmd, ["demo-runbook"])

    assert promoted.exit_code == 1
    assert promoted.output.strip() == PROMOTION_AUTHORITY_UNAVAILABLE
    assert {path: (root / path).read_bytes() for path in before} == before


@pytest.mark.parametrize(
    ("artifact_type", "locator"),
    [
        ("spec", "runbooks/demo-runbook.md"),
        ("spec", "runbooks/other-prose.md"),
        ("spec", "README.md"),
        ("spec", "TOPIC-ROUTER.md"),
    ],
)
def test_self_prose_and_generated_files_cannot_be_pinned_as_evidence(
    tmp_path: Path,
    monkeypatch,
    artifact_type: str,
    locator: str,
) -> None:
    root = tmp_path / "repository"
    _write_fixture_files(root)
    draft_path = root / "runbooks" / "demo-runbook.md"
    draft_path.write_text(
        _conformant_draft("demo-runbook")
        + _promotion_block("P2", artifact_type=artifact_type, locator=locator)
    )
    (root / "runbooks" / "other-prose.md").write_text("# Untrusted prose\n")
    monkeypatch.chdir(root)

    result = CliRunner().invoke(catalog_pin_evidence_cmd, ["demo-runbook"])

    assert result.exit_code == 1
    assert "not a permitted spec path" in result.output


def _conformant_draft(runbook_id: str) -> str:
    source = (FIXTURES_DIR / "conformant.md").read_text()
    _, raw_frontmatter, body = source.split("---", 2)
    frontmatter = yaml.safe_load(raw_frontmatter)
    frontmatter.update(
        {
            "runbook_id": runbook_id,
            "domain": "test-domain",
            "status": "DRAFT",
            "authoritative_for": [
                {
                    "topic": f"{runbook_id}-topic",
                    "section": "§C. Architecture & Interactions",
                }
            ],
            "aliases": [],
            "error_signatures": [],
            "supersedes": [],
            "superseded_by": [],
            "owner": "sysadmin",
            "last_verified_at": "2026-04-20",
        }
    )
    return "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---" + body


def _promotion_repository(
    tmp_path: Path,
    *,
    risk: str,
    server_receipt_id: str | None = None,
) -> tuple[Path, Path, Path]:
    root = tmp_path / "repository"
    _write_fixture_files(root)
    draft_path = root / "runbooks" / "demo-runbook.md"
    draft_path.write_text(
        _conformant_draft("demo-runbook")
        + _promotion_block(risk, server_receipt_id=server_receipt_id)
    )
    draft_path.write_text(
        pin_draft_promotion_evidence(
            root,
            draft_path,
            draft_path.read_text(),
            root / "schemas",
        )
    )

    manifest = {
        "manifest_version": 2,
        "purpose": PURPOSE,
        "inventory": {
            "repository": "example/runbooks",
            "base_sha": "0" * 40,
            "inventory_sha": "0" * 40,
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
            level: f"Definition for {level}." for level in ("P0", "P1", "P2", "P3")
        },
        "documents": [
            {
                "path": "runbooks/demo-runbook.md",
                "git_blob_oid": "0" * 40,
                "catalog_state": "grandfathered",
                "status": "pending_verification",
                "proposed_disposition": "promote",
                "batch": "promotion-test",
                "risk": risk,
                "target_paths": ["runbooks/demo-runbook.md"],
                "evidence": [
                    {
                        "ref": "git:content-snapshot-pending",
                        "finding": "The promotion block maps current sections to an implementation blob.",
                    }
                ],
                "verify_against": ["exact repository content snapshot"],
                "independent_review_required": risk in {"P0", "P1"},
            }
        ],
    }
    manifest_path = root / "CORPUS-MANIFEST.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    # Generate the empty DRAFT projection before the fixture becomes a Git
    # repository. Synthetic histories have no production rollout object and
    # must never be recognized by a remote-name or content heuristic.
    generate_catalog(root)

    _run_git(root, "init", "-q")
    _run_git(root, "add", ".")
    _run_git(
        root,
        "-c",
        "user.name=Promotion Test",
        "-c",
        "user.email=promotion@example.invalid",
        "commit",
        "-qm",
        "DRAFT content snapshot",
    )
    content_sha = _run_git(root, "rev-parse", "HEAD")
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["inventory"]["base_sha"] = content_sha
    manifest["documents"][0]["evidence"][0]["ref"] = (
        f"git:example/runbooks@{content_sha}:runbook_tools/evidence_source.py"
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    refresh_corpus_manifest(root, content_sha)
    _run_git(root, "add", "CORPUS-MANIFEST.yaml")
    _run_git(
        root,
        "-c",
        "user.name=Promotion Test",
        "-c",
        "user.email=promotion@example.invalid",
        "commit",
        "-qm",
        "pin DRAFT corpus manifest",
    )
    return root, draft_path, root / "runbook_tools" / "evidence_source.py"


def _write_fixture_files(root: Path) -> None:
    root.mkdir()
    shutil.copytree(SCHEMAS_DIR, root / "schemas")
    (root / "README.md").write_text(
        "# Fixture runbooks\n\n"
        "<!-- runbook-catalog:begin -->\n"
        "<!-- runbook-catalog:end -->\n"
    )
    evidence_path = root / "runbook_tools" / "evidence_source.py"
    evidence_path.parent.mkdir()
    evidence_path.write_text("CURRENT = 'verified'\n")
    (root / "runbooks").mkdir()


def _promotion_block(
    risk: str,
    *,
    artifact_type: str = "code",
    locator: str = "runbook_tools/evidence_source.py",
    server_receipt_id: str | None = None,
) -> str:
    payload = {
        "contract_version": "ai.market/runbook-promotion-evidence/v1",
        "risk": risk,
        "section_coverage": [
            {
                "section": letter,
                "status": "VERIFIED",
                "evidence_ids": ["implementation-source"],
            }
            for letter in "BCDEFGHI"
        ],
        "verified_against": [
            {
                "evidence_id": "implementation-source",
                "kind": "repository_blob",
                "artifact_type": artifact_type,
                "locator": locator,
                "supports_sections": list("BCDEFGHI"),
            }
        ],
    }
    if server_receipt_id is not None:
        payload["server_receipt_id"] = server_receipt_id
    return (
        "\n\n```yaml promotion-evidence\n"
        + yaml.safe_dump(payload, sort_keys=False)
        + "```\n"
    )


def _promotion_payload(markdown: str) -> dict:
    body = markdown.split("```yaml promotion-evidence\n", 1)[1].split("```", 1)[0]
    value = yaml.safe_load(body)
    assert isinstance(value, dict)
    return value


def _run_git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
