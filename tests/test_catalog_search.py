from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

import runbook_tools.catalog.search as catalog_search
import runbook_tools.catalog.validator as catalog_validator
from runbook_tools.catalog.canonical_content import (
    canonical_json_bytes,
    canonical_string_bytes,
)
from runbook_tools.catalog.generator import generate_catalog, source_paths
from runbook_tools.catalog.limits import PRODUCTION_LIMITS
from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.search import (
    _MAX_BATCH_QUERIES,
    _score_sources,
    search_catalog,
    search_catalog_delivery,
    search_catalog_many,
)
from runbook_tools.cli import catalog_cmd
from runbook_tools.corpus_manifest import (
    MAX_PINNED_BATCH_WIRE_BYTES,
    MAX_PINNED_VERIFY_AGAINST_ITEM_WIRE_BYTES,
    PURPOSE,
    SOURCE_SELECTOR,
)
from tests.catalog_test_support import (
    conformant_catalog_document,
    ensure_catalog_schemas,
)

REPO_ROOT = Path(__file__).parent.parent
SEARCH_BENCHMARK = Path(__file__).parent / "fixtures" / "catalog" / "search_benchmark.yaml"
DISCOVERY_BENCHMARK = (
    Path(__file__).parent / "fixtures" / "catalog" / "discovery_benchmark.yaml"
)

def _metadata(
    runbook_id: str,
    *,
    topic: str,
    section: str,
    aliases: list[str] | None = None,
) -> dict:
    return {
        "runbook_id": runbook_id,
        "domain": "test-domain",
        "status": "ACTIVE",
        "authoritative_for": [{"topic": topic, "section": section}],
        "aliases": aliases or [],
        "error_signatures": [],
        "supersedes": [],
        "superseded_by": [],
        "owner": "sysadmin",
        "owner_agent": "sysadmin",
        "last_verified_at": "2026-07-31",
    }


def _write_runbook(root: Path, runbook_id: str, metadata: dict, body: str) -> Path:
    path = root / "runbooks" / f"{runbook_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_catalog_schemas(root)
    title_match = re.search(r"(?m)^# (.+)$", body)
    section_bodies: dict[str, str] = {}
    for match in re.finditer(
        r"(?ms)^## (?P<heading>.+?)\n\n(?P<body>.*?)(?=^## |\Z)",
        body,
    ):
        heading = match.group("heading")
        if heading == "§C. Architecture":
            heading = "§C. Architecture & Interactions"
        content = re.sub(
            r'(?m)^<a id="rb-section-[a-z0-9-]+"></a>\n?',
            "",
            match.group("body"),
        )
        section_bodies[heading] = content.strip()
    path.write_text(
        conformant_catalog_document(
            metadata,
            title=title_match.group(1) if title_match else runbook_id,
            overview_body=None,
            section_bodies=section_bodies,
        )
    )
    return path


def _tokens_from_excerpt(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _manifest_entry(root: Path, sha: str, path: str, state: str) -> dict:
    oid = subprocess.run(
        ["git", "rev-parse", f"{sha}:{path}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    archived = state == "archived"
    return {
        "path": path,
        **({"inventory_path": path} if archived else {}),
        "git_blob_oid": oid,
        "catalog_state": state,
        "status": (
            "active"
            if state == "active"
            else "archived"
            if archived
            else "pending_verification"
        ),
        "proposed_disposition": "archive" if archived else "retain_active" if state == "active" else "promote",
        "batch": "search-fixture",
        "risk": "P3" if archived else "P2",
        "target_paths": [path],
        **({"archive_path": path} if archived else {}),
        "evidence": [],
        "verify_against": ["fixture ground truth"],
        "independent_review_required": False,
    }


def _write_snapshot_manifest(
    root: Path,
    inventory_sha: str,
    states: dict[str, str],
    *,
    base_sha: str | None = None,
) -> None:
    entries = [
        _manifest_entry(root, inventory_sha, path, state)
        for path, state in sorted(states.items())
    ]
    counts = {
        "operational_documents": len(entries),
        "source_documents": sum(state != "archived" for state in states.values()),
        "active": sum(state == "active" for state in states.values()),
        "grandfathered": sum(
            state == "grandfathered" for state in states.values()
        ),
        "archived": sum(state == "archived" for state in states.values()),
    }
    payload = {
        "manifest_version": 2,
        "purpose": PURPOSE,
        "inventory": {
            "repository": "aidotmarket/runbooks",
            "base_sha": base_sha or inventory_sha,
            "inventory_sha": inventory_sha,
            "blob_oid_scope": "Pinned inventory tree blob.",
            "inventory_path_semantics": "inventory_path selects the pinned tree path.",
            "source_selector": SOURCE_SELECTOR,
            "refresh_required_before_execution": True,
            "counts": counts,
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
        "documents": entries,
    }
    (root / "CORPUS-MANIFEST.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False)
    )


def _commit_snapshot_manifest(
    root: Path,
    inventory_sha: str,
    states: dict[str, str],
    *,
    base_sha: str | None = None,
) -> str:
    _write_snapshot_manifest(
        root,
        inventory_sha,
        states,
        base_sha=base_sha,
    )
    generate_catalog(root)
    subprocess.run(
        [
            "git",
            "add",
            "CORPUS-MANIFEST.yaml",
            "CATALOG.json",
            "TOPIC-ROUTER.md",
            "README.md",
        ],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "pinned corpus manifest"],
        cwd=root,
        check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _refresh_search_snapshot(root: Path, message: str) -> str:
    manifest = yaml.safe_load((root / "CORPUS-MANIFEST.yaml").read_text())
    states = {
        entry["path"]: entry["catalog_state"] for entry in manifest["documents"]
    }
    base_sha = manifest["inventory"]["base_sha"]
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", message],
        cwd=root,
        check=True,
    )
    inventory_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return _commit_snapshot_manifest(
        root,
        inventory_sha,
        states,
        base_sha=base_sha,
    )


def _repository(root: Path) -> tuple[str, str, Path]:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    peer_metadata = _metadata(
        "peer-instance-discipline",
        topic="peer-bus-coordination",
        section="§E. Operate",
        aliases=["peer-message-bus"],
    )
    peer_metadata["authoritative_for"][0]["section_id"] = "operate"
    peer = _write_runbook(
        root,
        "peer-instance-discipline",
        peer_metadata,
        "# Peer Instance Discipline\n\n"
        "## §C. Architecture\n\nPeer topology.\n\n"
        '<a id="rb-section-operate"></a>\n'
        "## §E. Operate\n\nDrain the peer inbox at session open before dispatching work. "
        "Fixture authoring vocabulary: update runbook, create a runbook, write "
        "documentation, revise the deployment playbook, and edit the operator manual.\n",
    )
    _write_runbook(
        root,
        "billing-deploy",
        _metadata(
            "billing-deploy",
            topic="billing-release",
            section="§E. Deploy",
            aliases=["payments-release"],
        ),
        "# Billing Deploy\n\n## §E. Deploy\n\nVerify the payment canary.\n",
    )
    (root / "README.md").write_text(
        "# Fixture\n\n## Adoption status\n\n"
        "| System | Runbook | Status |\n|---|---|---|\n| None | — | NOT_STARTED |\n\n"
        "## Status values\n\nFixture.\n\n"
        "## Working on a runbook\n\n"
        "Use this repository contract to create, author, update, or maintain an "
        "authoritative runbook after an operational behavior or process change.\n"
    )
    generate_catalog(root)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)
    inventory_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    sha = _commit_snapshot_manifest(
        root,
        inventory_sha,
        {
            "runbooks/billing-deploy.md": "active",
            "runbooks/peer-instance-discipline.md": "active",
        },
    )
    return sha, f"git:aidotmarket/runbooks@{sha}:CATALOG.json", peer


def _working_tree_pin(root: Path) -> tuple[str, str]:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    ensure_catalog_schemas(root)
    for source in source_paths(REPO_ROOT):
        relative = source.relative_to(REPO_ROOT)
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    source_manifest = yaml.safe_load((REPO_ROOT / "CORPUS-MANIFEST.yaml").read_text())
    states = {
        entry["path"]: entry["catalog_state"]
        for entry in source_manifest["documents"]
    }
    for path, state in states.items():
        if state != "archived":
            continue
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / path, destination)
    shutil.copy2(REPO_ROOT / "README.md", root / "README.md")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "working tree catalog fixture"],
        cwd=root,
        check=True,
    )
    inventory_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    sha = _commit_snapshot_manifest(root, inventory_sha, states)
    return sha, f"git:aidotmarket/runbooks@{sha}:CATALOG.json"


def test_search_ranks_task_language_and_returns_pinned_excerpt_evidence(tmp_path: Path) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "drain peer bus inbox when opening a session",
    )

    assert result["catalog_sha"] == sha
    assert result["searched_entry_count"] == 2
    assert result["status"] == "candidates_returned_unverified"
    first = result["candidates"][0]
    assert first["runbook_id"] == "peer-instance-discipline"
    assert first["heading"] == "§E. Operate"
    assert first["section_id"] == "operate"
    assert first["section_id_source"] == "catalog"
    assert first["catalog_declared"] is True
    assert first["declaration_kinds"] == ["topic"]
    assert first["authority_keys"] == ["topic:peer-bus-coordination"]
    assert first["owner"] == "sysadmin"
    assert first["last_verified_at"] == "2026-07-31"
    assert first["integrity_only"] is True
    assert first["integrity_status"] == "integrity_pass_unverified"
    assert first["semantic_verification"] is False
    assert first["authority_admission"] is False
    assert first["action_authority_eligible"] is False
    assert "Drain the peer inbox" in first["excerpt"]
    assert hashlib.sha256(first["excerpt"].encode()).hexdigest() == first["excerpt_sha256"]
    assert len(first["match_evidence"]) <= 1
    assert {row["kind"] for row in first["match_evidence"]} <= {
        "path",
        "title",
        "heading",
        "excerpt",
        "structured_literal",
        "intent",
        "legacy_active",
    }
    assert "topic" not in first["relevance_evidence"]


def test_search_ignores_local_git_replacement_refs_when_reading_sections(
    tmp_path: Path,
) -> None:
    original_sha, catalog_ref, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text().replace(
            "Drain the peer inbox at session open before dispatching work.",
            "REPLACEMENT_ONLY_NEBULA content from a different commit.",
            1,
        )
    )
    generate_catalog(tmp_path)
    replacement_sha = _refresh_search_snapshot(tmp_path, "replacement fixture")
    subprocess.run(
        ["git", "replace", original_sha, replacement_sha],
        cwd=tmp_path,
        check=True,
    )

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "drain peer bus inbox when opening a session",
    )

    assert result["catalog_sha"] == original_sha
    assert "Drain the peer inbox" in result["candidates"][0]["excerpt"]
    assert "REPLACEMENT_ONLY_NEBULA" not in result["candidates"][0]["excerpt"]


def test_search_reads_the_pinned_blob_not_dirty_worktree_content(tmp_path: Path) -> None:
    _, catalog_ref, peer = _repository(tmp_path)
    before = search_catalog(tmp_path, catalog_ref, "peer inbox session open")
    peer.write_text("# Replaced in dirty worktree\n\nNo relevant content.\n")

    after = search_catalog(tmp_path, catalog_ref, "peer inbox session open")

    assert after == before


def test_search_snapshot_preflights_runbook_before_reading_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sha, _, _ = _repository(tmp_path)
    catalog = {
        "entries": [
            {
                "path": "runbooks/peer-instance-discipline.md",
                "status": "ACTIVE",
            }
        ]
    }

    monkeypatch.setattr(
        catalog_validator,
        "_git_blob_size",
        lambda repo_root, checked_sha, path: (
            catalog_validator.MAX_PINNED_MARKDOWN_BYTES + 1
        ),
    )
    monkeypatch.setattr(
        catalog_search,
        "_git_show_text",
        lambda repo_root, checked_sha, path: (_ for _ in ()).throw(
            AssertionError("oversized runbook must not be read")
        ),
    )

    with pytest.raises(CatalogError, match="pinned Markdown limit"):
        catalog_search._load_snapshot(tmp_path, catalog, sha)


def test_search_is_deterministic_and_limit_is_bounded(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    first = search_catalog(tmp_path, catalog_ref, "release deploy", limit=1)
    second = search_catalog(tmp_path, catalog_ref, "release deploy", limit=1)

    assert first == second
    delivered = sorted(
        first["candidates"] + first["discovery_leads"],
        key=lambda row: row["relevance_rank"],
    )
    assert len(delivered) == min(3, first["qualifying_result_count"])
    assert [row["relevance_rank"] for row in delivered[:3]] == list(
        range(1, len(delivered[:3]) + 1)
    )
    assert first["response_budget_bytes"] == 40_000
    assert first["response_budget_truncated"] is False
    assert first["dropped_candidate_count"] == (
        first["qualifying_result_count"] - len(delivered)
    )
    assert len(json.dumps(first, sort_keys=True).encode()) <= 40_000
    with pytest.raises(CatalogError, match="limit"):
        search_catalog(tmp_path, catalog_ref, "release deploy", limit=0)
    with pytest.raises(CatalogError, match="non-empty"):
        search_catalog(tmp_path, catalog_ref, "")
    with pytest.raises(CatalogError, match="4000"):
        search_catalog(tmp_path, catalog_ref, "x" * 4001)


def test_search_result_is_json_serializable(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "payments release")

    assert json.loads(json.dumps(result)) == result


def test_no_positive_match_does_not_claim_that_no_runbook_exists(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "xylophonically zoetrope")

    assert result["status"] == "no_relevant_result"
    assert result["discovery_status"] == "no_qualifying_discovery_lead"
    assert result["candidates"] == []


def test_delivery_digest_binds_the_exact_returned_payload(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "peer inbox")
    zeroed = dict(result)
    zeroed["delivery_digest"] = "0" * 64
    assert hashlib.sha256(
        canonical_json_bytes(zeroed, final_newline=True)
    ).hexdigest() == result["delivery_digest"]


def test_complete_single_response_reports_exact_cli_wire_size_with_multibyte_query(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "payment canary café 🛰")
    wire = canonical_json_bytes(result, final_newline=True)

    assert result["complete"] is True
    assert result["serialized_bytes"] == len(wire)
    assert len(wire) <= result["response_budget_bytes"] == 40_000


def test_unanchored_section_uses_an_explicitly_labeled_legacy_id(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "payment canary")
    candidate = next(
        row
        for row in result["candidates"]
        if row["runbook_id"] == "billing-deploy" and row["heading"] == "§E. Deploy"
    )

    assert candidate["section_id"] == "e-deploy"
    assert candidate["section_id_source"] == "legacy-derived"


def test_nested_section_owns_its_content_and_centers_bounded_excerpt(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    filler = "\n".join(f"filler line {index}" for index in range(75))
    peer.write_text(
        peer.read_text().replace(
            "Drain the peer inbox at session open before dispatching work.",
            "Drain the peer inbox at session open before dispatching work.\n\n"
            "### Recovery procedure\n\n"
            f"{filler}\norbital marmot recovery token.\n",
        )
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "nested search fixture")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "orbital marmot",
        limit=3,
    )
    recovery = next(
        row
        for row in result["candidates"]
        if row["runbook_id"] == "peer-instance-discipline"
        and row["heading"] == "Recovery procedure"
    )

    assert "orbital marmot recovery token" in recovery["excerpt"]
    assert recovery["excerpt_truncated"] is True
    assert len(recovery["excerpt"].splitlines()) <= 60
    assert len(recovery["excerpt"]) <= 2400
    assert recovery["excerpt_start_line"] > recovery["heading_line"]


def test_raw_anchor_does_not_claim_catalog_identity(tmp_path: Path) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text()
        + '\n<a id="rb-section-hidden-procedure"></a>\n'
        + "### Hidden Procedure\n\nquasar narwhal diagnostic.\n"
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "raw anchor fixture")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "quasar narwhal",
        limit=3,
    )
    hidden = next(row for row in result["candidates"] if row["heading"] == "Hidden Procedure")

    assert hidden["section_id"] == "hidden-procedure"
    assert hidden["section_id_source"] == "legacy-derived"
    assert hidden["catalog_declared"] is False
    assert hidden["declaration_kinds"] == []
    assert hidden["authority_keys"] == []


def test_explicit_historical_spans_are_not_search_candidates(tmp_path: Path) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text()
        + "\n<!-- catalog:historical -->\n"
        + "## Superseded Procedure\n\nquasar narwhal obsolescent.\n"
        + "<!-- /catalog:historical -->\n"
        + "active sapphire recovery instruction.\n"
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "historical fixture")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "quasar narwhal obsolescent",
        limit=3,
    )

    assert result["status"] == "no_relevant_result"
    assert result["candidates"] == []

    active = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "active sapphire recovery instruction",
        limit=3,
    )["candidates"][0]
    blob = subprocess.run(
        ["git", "show", f"{sha}:{active['path']}"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    selected = blob.splitlines()[
        active["excerpt_start_line"] - 1 : active["excerpt_end_line"]
    ]
    selected[-1] = selected[-1][: active["excerpt_end_column_exclusive"] - 1]
    assert "\n".join(selected) == active["excerpt"]
    assert "obsolete instruction" not in active["excerpt"]


def test_duplicate_display_heading_does_not_inherit_stable_authority(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text()
        + "\n### §E. Operate\n\nquasar duplicate-only appendix token.\n"
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "duplicate heading fixture")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "operate quasar duplicate-only appendix",
        limit=3,
    )
    duplicates = [
        row
        for row in result["candidates"]
        if row["runbook_id"] == "peer-instance-discipline"
        and row["heading"] == "§E. Operate"
    ]

    assert len(duplicates) == 1
    unanchored = duplicates[0]
    assert unanchored["section_id"] == "e-operate"
    assert unanchored["catalog_declared"] is False
    assert unanchored["section_id_source"] == "legacy-derived"
    assert not {
        evidence["kind"] for evidence in unanchored["match_evidence"]
    } & {"topic", "error_signature", "runbook_id", "path", "alias"}


def test_excerpt_bounds_recreate_the_exact_pinned_text(tmp_path: Path) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)

    candidate = search_catalog(tmp_path, catalog_ref, "peer inbox")["candidates"][0]
    blob = subprocess.run(
        ["git", "show", f"{sha}:{candidate['path']}"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    selected = blob.splitlines()[
        candidate["excerpt_start_line"] - 1 : candidate["excerpt_end_line"]
    ]
    selected[-1] = selected[-1][
        : candidate["excerpt_end_column_exclusive"] - 1
    ]

    assert "\n".join(selected) == candidate["excerpt"]


def test_identity_selects_runbook_then_lexical_intent_selects_best_section(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text().replace(
            "authoritative_for:\n",
            "authoritative_for:\n"
            "- topic: aaa-architecture\n"
            "  section: §C. Architecture & Interactions\n",
            1,
        )
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "multiple authorities")
    catalog_ref = f"git:aidotmarket/runbooks@{sha}:CATALOG.json"

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "drain peer inbox",
        limit=3,
    )
    peer_candidates = [
        row
        for row in result["candidates"]
        if row["runbook_id"] == "peer-instance-discipline"
    ]

    assert peer_candidates
    assert peer_candidates[0]["relevance_rank"] == 1
    assert set(peer_candidates[0]["relevance_evidence"]).isdisjoint(
        {"alias", "topic", "authority", "owner"}
    )


def test_catalog_only_alias_cannot_qualify_common_retrieval(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)
    metadata = _metadata(
        "peer-instance-discipline",
        topic="peer-bus-coordination",
        section="§C. Architecture & Interactions",
        aliases=["quasar-narwhal"],
    )
    _write_runbook(
        tmp_path,
        "peer-instance-discipline",
        metadata,
        "# Peer Instance Discipline\n\n"
        "## §C. Architecture\n\nPeer topology with no alias words.\n\n"
        "## §E. Operate\n\nDrain the unrelated peer inbox.\n",
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "c authority alias fallback")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "quasar narwhal",
        limit=3,
    )
    assert result["status"] == "no_relevant_result"
    assert result["candidates"] == []


def test_undeclared_parent_cannot_claim_child_structured_literal_or_intent(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text().replace(
            "- Secret reads must always resolve against an explicitly named environment.",
            (
                "- Secret reads must always resolve against an explicitly named "
                "environment. Run `mystery_call` to inspect the invariant."
            ),
            1,
        )
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "child literal provenance")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "change mystery_call",
        limit=3,
    )

    peer_candidates = [
        candidate
        for candidate in result["candidates"]
        if candidate["runbook_id"] == "peer-instance-discipline"
    ]
    assert peer_candidates[0]["heading"] == "§H.1 Invariants"
    assert "mystery_call" in peer_candidates[0]["excerpt"]
    parent = next(
        (
            candidate
            for candidate in peer_candidates
            if candidate["heading"] == "§H. Evolve"
        ),
        None,
    )
    assert parent is None or not {
        evidence["kind"] for evidence in parent["match_evidence"]
    } & {"structured_literal", "intent"}
    for candidate in peer_candidates:
        excerpt_tokens = set(re.findall(r"[a-z0-9]+", candidate["excerpt"].casefold()))
        for evidence in candidate["match_evidence"]:
            if evidence["kind"] == "structured_literal":
                assert set(evidence["matched_tokens"]) <= excerpt_tokens


def test_h1_document_titles_are_not_search_candidates(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "Peer Instance Discipline",
        limit=3,
    )

    assert all(candidate["heading"] != "Peer Instance Discipline" for candidate in result["candidates"])


def test_document_fallback_bounds_a_large_h1_by_json_wire_width(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)
    billing = tmp_path / "runbooks/billing-deploy.md"
    raw_title = "🛰" * 10_000
    billing.write_text(
        billing.read_text().replace("# Billing Deploy", f"# {raw_title}", 1)
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "large H1 fixture")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "path:runbooks/billing-deploy.md",
        limit=1,
    )
    candidate = result["candidates"][0]

    assert candidate["unit_kind"] == "document"
    assert candidate["candidate_kind"] == "active_catalog_document"
    assert candidate["document_title_truncated"] is True
    assert candidate["excerpt_truncated"] is True
    assert raw_title.startswith(candidate["document_title"])
    assert raw_title.startswith(candidate["excerpt"])
    assert (
        len(json.dumps(candidate["document_title"], ensure_ascii=True)) - 2
        <= PRODUCTION_LIMITS.title_j
    )
    assert (
        len(json.dumps(candidate["excerpt"], ensure_ascii=True)) - 2
        <= PRODUCTION_LIMITS.corpus_excerpt_j
    )
    assert {"heading", "heading_line", "section_id"}.isdisjoint(candidate)
    assert result["serialized_bytes"] <= result["response_budget_bytes"]


def test_generic_only_structured_literal_cannot_qualify_a_result(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text()
        + "\n### Generic literal\n\nThe legacy helper used `run restore`.\n"
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "generic literal fixture")

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "run restore",
    )

    assert result["candidates"] == []
    assert result["discovery_leads"] == []
    assert result["status"] == "no_relevant_result"


def test_repeated_alias_or_topic_sources_do_not_sum_keyword_stuffing() -> None:
    query = "alpha procedure"
    tokens = {"alpha"}
    baseline = _score_sources(query, tokens, [("alias", "alpha", 9.0)])
    stuffed = _score_sources(
        query,
        tokens,
        [("alias", f"alpha variant {index}", 9.0) for index in range(64)],
    )

    assert stuffed[0] == baseline[0]
    assert [row["kind"] for row in stuffed[1]] == ["alias"]


def test_many_queries_share_one_catalog_snapshot(tmp_path: Path) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog_many(
        tmp_path,
        catalog_ref,
        ["peer inbox", "payment canary"],
    )

    assert result["catalog_sha"] == sha
    assert len(result["results"]) == 2
    assert [item["objective_ordinal"] for item in result["results"]] == [1, 2]
    assert result["results"][0]["candidates"][0]["runbook_id"] == (
        "peer-instance-discipline"
    )
    assert result["results"][1]["candidates"][0]["runbook_id"] == "billing-deploy"
    assert len(result["delivery_digest"]) == 64
    assert result["complete"] is True
    assert result["serialized_bytes"] == len(
        canonical_json_bytes(result, final_newline=True)
    )
    assert result["searched_section_count"] > 0
    assert result["response_budget_truncated"] is False
    with pytest.raises(CatalogError, match=f"1 to {_MAX_BATCH_QUERIES}"):
        search_catalog_many(tmp_path, catalog_ref, [])
    with pytest.raises(CatalogError, match=f"1 to {_MAX_BATCH_QUERIES}"):
        search_catalog_many(
            tmp_path,
            catalog_ref,
            ["query"] * (_MAX_BATCH_QUERIES + 1),
        )


def test_many_queries_enforce_a_global_serialized_response_budget(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    billing = tmp_path / "runbooks/billing-deploy.md"
    expansion = "\n".join(
        f"### Shared response section {index}\n\n"
        + "sharedtoken orbital café 🛰 "
        + "bounded response payload " * 300
        for index in range(12)
    )
    peer.write_text(peer.read_text() + expansion + "\n")
    billing.write_text(billing.read_text() + expansion + "\n")
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "response budget fixture")

    result = search_catalog_many(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        ["sharedtoken orbital"] * _MAX_BATCH_QUERIES,
        limit=3,
    )

    wire = canonical_json_bytes(result, final_newline=True)
    assert result["complete"] is True
    assert result["serialized_bytes"] == len(wire)
    assert len(wire) <= result["response_budget_bytes"] == 40_000
    assert result["response_budget_truncated"] is False
    assert result["dropped_candidate_count"] > 0
    assert all(item["candidates"] for item in result["results"])
    assert all(
        item["status"] == "candidates_returned_unverified"
        for item in result["results"]
    )


def test_authoring_task_prepends_pinned_non_authoritative_repository_contract(
    tmp_path: Path,
) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "create or update an authoritative runbook after implementing a process change",
    )

    assert all(
        candidate["candidate_kind"] != "repository_authoring_guidance"
        for candidate in result["candidates"]
    )
    guidance = result["supplemental_guidance"][0]
    assert guidance["path"] == "README.md"
    assert guidance["candidate_kind"] == "repository_authoring_guidance"
    assert guidance["candidate_id_eligible"] is False
    assert guidance["semantic_verification"] is False
    assert guidance["authority_admission"] is False
    assert guidance["action_authority_eligible"] is False
    assert guidance["supplemental"] is True
    assert guidance["warning_code"] == "SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY"
    assert result["supplemental_guidance_returned"] is True
    assert {
        "candidate_digest",
        "discovery_digest",
        "discovery_lead_id",
        "runbook_id",
        "authority_keys",
        "owner",
        "last_verified_at",
    }.isdisjoint(guidance)
    blob = subprocess.run(
        ["git", "show", f"{sha}:README.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert guidance["excerpt"] in blob
    assert (
        len(canonical_json_bytes(guidance["excerpt"])) - 2
        <= PRODUCTION_LIMITS.supplemental_excerpt_j
    )


@pytest.mark.parametrize(
    "query",
    [
        "update runbook",
        "create a runbook",
        "write documentation",
        "revise the deployment playbook",
        "edit the operator manual",
    ],
)
def test_short_natural_authoring_objectives_retrieve_repository_contract(
    tmp_path: Path,
    query: str,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, query, limit=3)

    guidance = result["supplemental_guidance"][0]
    assert guidance["candidate_kind"] == "repository_authoring_guidance"
    assert guidance["candidate_id_eligible"] is False
    assert guidance["warning_code"] == "SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY"


@pytest.mark.parametrize(
    "query",
    [
        "create a manual backup",
        "write a guide file to disk",
        "update the database now; the runbook service is healthy",
        "create a customer account; read the operator manual",
        "revise the deployment schedule",
    ],
)
def test_non_authoring_action_or_read_queries_do_not_receive_repository_contract(
    tmp_path: Path,
    query: str,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, query, limit=3)

    assert result["supplemental_guidance"] == []


def test_batch_guidance_never_claims_candidate_breadth_or_success(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)
    queries = ["update runbook", "write documentation"]

    result = search_catalog_many(tmp_path, catalog_ref, queries, limit=3)

    wire = canonical_json_bytes(result, final_newline=True)
    assert result["serialized_bytes"] == len(wire)
    assert len(wire) <= result["response_budget_bytes"] == 40_000
    for objective in result["results"]:
        assert objective["candidates"] == []
        assert objective["status"] == "no_relevant_result"
        assert len(objective["supplemental_guidance"]) == 1
        assert objective["eligible_candidates_returned"] == 0


def test_limit_one_preserves_active_candidate_and_adds_guidance_supplementally(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "peer inbox and update runbook",
        limit=1,
    )

    eligible = [
        candidate
        for candidate in result["candidates"]
        if candidate["candidate_id_eligible"]
    ]
    guidance = result["supplemental_guidance"]
    assert len(eligible) == 1
    assert len(guidance) == 1
    assert result["candidates"][0]["candidate_id_eligible"] is True
    assert result["eligible_candidates_returned"] == 1
    assert result["eligible_candidate_count"] == (
        result["eligible_candidates_returned"]
        + result["eligible_candidates_omitted_by_limit"]
        + result["eligible_candidates_omitted_by_response_budget"]
    )


def test_mixed_batch_is_deterministic_and_guidance_never_counts_as_eligible(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)
    queries = [
        "peer inbox and update runbook",
        "payment canary and write documentation",
    ]

    first = search_catalog_many(tmp_path, catalog_ref, queries, limit=3)
    second = search_catalog_many(tmp_path, catalog_ref, queries, limit=3)

    assert first == second
    assert first["serialized_bytes"] <= 40_000
    for objective in first["results"]:
        has_eligible = any(
            candidate["candidate_id_eligible"]
            for candidate in objective["candidates"]
        )
        assert (objective["status"] == "candidates_returned_unverified") is (
            has_eligible
        )
        assert objective["supplemental_guidance"]
        for candidate in objective["candidates"]:
            assert candidate["integrity_status"] == "integrity_pass_unverified"
            assert candidate["semantic_verification"] is False
            assert candidate["authority_admission"] is False
            assert candidate["action_authority_eligible"] is False
        assert objective["eligible_candidate_count"] == (
            objective["eligible_candidates_returned"]
            + objective["eligible_candidates_omitted_by_limit"]
            + objective["eligible_candidates_omitted_by_response_budget"]
        )


def test_operational_drift_queries_reach_catalog_declared_repair_sections(
    tmp_path: Path,
) -> None:
    sha, catalog_ref = _working_tree_pin(tmp_path)

    credential = search_catalog(
        tmp_path,
        catalog_ref,
        "repair a credential exposure and secret disclosure",
        limit=3,
    )["candidates"][0]
    assert credential["runbook_id"] == "infrastructure-discovery"
    assert credential["heading"] == "§G. Repair"
    assert credential["catalog_declared"] is True
    assert {
        "topic:security-credential-exposure",
        "topic:security-secret-disclosure",
    } <= set(credential["authority_keys"])

    council_result = search_catalog(
        tmp_path,
        catalog_ref,
        "diagnose Council schema and roster drift for a required reviewer",
        limit=3,
    )
    council = next(
        candidate
        for candidate in council_result["candidates"]
        if candidate["runbook_id"] == "council"
    )
    assert council["relevance_rank"] <= 3
    pinned_council = subprocess.run(
        ["git", "show", f"{sha}:{council['path']}"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert {"council", "schema", "roster", "reviewer"} <= _tokens_from_excerpt(
        pinned_council
    )


def test_catalog_module_is_a_clean_checkout_cli_fallback() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "runbook_tools.catalog", "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "search-many" in completed.stdout
    assert "python -m runbook_tools.catalog" in completed.stdout


@pytest.mark.parametrize(
    ("query", "required_tokens"),
    [
        (
            "after session open obtain authoritative runbook context before kd_session_plan without inventing a consultation",
            {
                "RUNBOOK_CONTEXT_SELECTION_REQUIRED",
                "runbook_consultation",
                "signed deployed contract",
            },
        ),
        (
            "close a session with truthful runbook impact evidence without inventing documentation or filler",
            {"runbook_exit", "runbook_impact", "compatibility input"},
        ),
    ],
)
def test_active_lifecycle_owner_retrieves_plan_and_close_transition_guidance(
    tmp_path: Path,
    query: str,
    required_tokens: set[str],
) -> None:
    sha, catalog_ref = _working_tree_pin(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, query)

    matching = [
        candidate
        for candidate in result["candidates"]
        if candidate["runbook_id"] == "peer-instance-discipline"
        and candidate["relevance_rank"] <= 3
    ]
    assert matching
    pinned_document = subprocess.run(
        ["git", "show", f"{sha}:{matching[0]['path']}"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.casefold()
    assert all(token.casefold() in pinned_document for token in required_tokens)


def test_operational_search_benchmark_is_relevant_and_honest(
    tmp_path: Path,
) -> None:
    sha, catalog_ref = _working_tree_pin(tmp_path)
    fixture = yaml.safe_load(SEARCH_BENCHMARK.read_text())
    assert fixture["schema_version"] == 1
    assert fixture["provenance"]["authored_session"] == "S1413"
    assert fixture["provenance"]["runbooks_base_sha"] == (
        "a6d7534a35d921138c139bdf69aaeddd0faec100"
    )
    assert fixture["provenance"]["independent_review_status"] == "pending"
    assert "reviewed_by" not in fixture["provenance"]
    cases = fixture["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    assert {
        "session-plan-context-first",
        "session-close-impact-evidence",
    }.issubset({case["id"] for case in cases})
    assert {case["area"] for case in cases} >= {
        "central-plan-close-runbook-context",
        "council-roles-and-schema",
        "peer-coordination",
        "deployment-and-recovery",
    }
    assert len(cases) >= 10
    assert sum(case["expectation"] == "no_positive_candidate" for case in cases) >= 2
    section_cases = [
        case for case in cases if case["expectation"] == "top3_actionable_section"
    ]
    assert len(section_cases) >= 10
    assert all(
        ("expected_section_id" in case or "expected_heading" in case)
        and case.get("required_action_tokens")
        for case in section_cases
    )

    guidance_case = cases[0]
    assert guidance_case["expectation"] == "repository_authoring_guidance"
    guidance_result = search_catalog(
        tmp_path,
        catalog_ref,
        guidance_case["query"],
        limit=1,
    )
    benchmark_results: list[dict] = [guidance_result]
    benchmark_sha: str | None = guidance_result["catalog_sha"]
    remaining_cases = cases[1:]
    for start in range(0, len(remaining_cases), _MAX_BATCH_QUERIES):
        group = remaining_cases[start : start + _MAX_BATCH_QUERIES]
        response = search_catalog_many(
            tmp_path,
            catalog_ref,
            [case["query"] for case in group],
        )
        benchmark_sha = response["catalog_sha"]
        benchmark_results.extend(response["results"])

    section_successes = 0
    section_misses: list[tuple[str, list[tuple[str, str]]]] = []
    for case, result in zip(cases, benchmark_results, strict=True):
        expectation = case["expectation"]
        if expectation == "top3_actionable_section":
            assert result["status"] == "candidates_returned_unverified"
            globally_ordered = sorted(
                result["candidates"] + result["discovery_leads"],
                key=lambda candidate: candidate["relevance_rank"],
            )[:3]
            matching = [
                candidate
                for candidate in globally_ordered
                if candidate.get("runbook_id") == case["expected_runbook_id"]
            ]
            if matching:
                pinned_document = subprocess.run(
                    ["git", "show", f"{sha}:{matching[0]['path']}"],
                    cwd=tmp_path,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.casefold()
                assert all(
                    token.casefold() in pinned_document
                    for token in case["required_action_tokens"]
                )
                section_successes += 1
            else:
                section_misses.append(
                    (
                        case["id"],
                        [
                            (
                                candidate.get("runbook_id", candidate["path"]),
                                candidate.get("heading", "document"),
                            )
                            for candidate in globally_ordered
                        ],
                    )
                )
        elif expectation == "no_positive_candidate":
            assert result["candidates"] == []
            assert result["status"] == (
                "no_positive_candidate_in_active_catalog"
                if result["discovery_leads"]
                else "no_relevant_result"
            )
        elif expectation == "historical_trap":
            delivered = "\n".join(
                candidate["excerpt"] for candidate in result["candidates"]
            ).casefold()
            assert all(
                token.casefold() not in delivered
                for token in case["forbidden_excerpt_tokens"]
            )
        elif expectation == "known_catalog_gap":
            actionable = [
                candidate
                for candidate in result["candidates"][:3]
                if candidate["runbook_id"] == case["expected_runbook_id"]
                and candidate["heading"] == case["expected_heading"]
                and all(
                    token.casefold() in candidate["excerpt"].casefold()
                    for token in case["missing_action_tokens"]
                )
            ]
            assert actionable == []
            assert case["stale_action_tokens"]
        elif expectation == "repository_authoring_guidance":
            guidance = result["supplemental_guidance"][0]
            assert guidance["path"] == case["expected_path"]
            assert case["expected_heading"] in guidance["excerpt"]
            assert guidance["candidate_kind"] == "repository_authoring_guidance"
            assert guidance["candidate_id_eligible"] is False
            assert guidance["warning_code"] == (
                "SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY"
            )
        else:
            raise AssertionError(f"unknown benchmark expectation: {expectation}")
    assert section_successes / len(section_cases) >= 0.9, section_misses
    assert benchmark_sha == sha


def test_complete_pinned_corpus_counts_and_every_exact_path_is_retrievable(
    tmp_path: Path,
) -> None:
    sha, catalog_ref = _working_tree_pin(tmp_path)
    validated = catalog_validator.load_validated_catalog(tmp_path, catalog_ref)
    manifest, snapshot = catalog_search._load_corpus_snapshot(
        tmp_path,
        validated.catalog,
        sha,
    )

    assert (
        manifest.operational_documents,
        manifest.active,
        manifest.grandfathered,
        manifest.archived,
    ) == (112, 26, 82, 4)
    assert len(snapshot) == 112

    seen_paths: set[str] = set()
    h1_only: dict | None = None
    archived: dict | None = None
    for start in range(0, len(snapshot), _MAX_BATCH_QUERIES):
        for record in snapshot[start : start + _MAX_BATCH_QUERIES]:
            query = f"path:{record.manifest.path}"
            result = catalog_search._search_corpus(
                sha,
                manifest,
                snapshot,
                query,
                catalog_search._validated_query_tokens(query),
            )
            rows = result["candidates"] + result["discovery_leads"]
            assert len(rows) == 1
            item = rows[0]
            assert item["path"] == record.manifest.path
            assert item["unit_kind"] == "document"
            assert {"heading", "heading_line", "section_id"}.isdisjoint(item)
            seen_paths.add(item["path"])
            if item["path"] == "session-lifecycle.md":
                h1_only = item
            if item["catalog_state"] == "archived":
                archived = item

    assert seen_paths == {record.manifest.path for record in snapshot}
    assert h1_only is not None
    assert archived is not None
    assert archived["historical_only"] is True


def test_pending_and_archived_exact_path_results_preserve_policy_boundaries(
    tmp_path: Path,
) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)

    pending = search_catalog(
        tmp_path,
        catalog_ref,
        "path:ai-market-backend.md",
    )
    assert pending["searched_entry_count"] == 112
    assert pending["status"] == "no_positive_candidate_in_active_catalog"
    assert pending["discovery_status"] == "discovery_leads_returned_unverified"
    assert pending["authoritative_gap"] is True
    assert pending["candidates"] == []
    pending_lead = pending["discovery_leads"][0]
    assert pending_lead["candidate_kind"] == "grandfathered_discovery_lead"
    assert pending_lead["historical_only"] is False
    assert pending_lead["requires_ground_truth_verification"] is True
    assert pending_lead["integrity_only"] is True
    assert pending_lead["integrity_status"] == "integrity_pass_unverified"

    archived = search_catalog(
        tmp_path,
        catalog_ref,
        "path:archive/evidence/briefing-verification-2026-04-25.md",
    )
    archived_lead = archived["discovery_leads"][0]
    assert archived_lead["candidate_kind"] == "archived_discovery_lead"
    assert archived_lead["historical_only"] is True
    assert archived_lead["catalog_state"] == "archived"

    forbidden = {
        "candidate_digest",
        "runbook_id",
        "authority_keys",
        "owner",
        "last_verified_at",
    }
    assert forbidden.isdisjoint(pending_lead)
    assert forbidden.isdisjoint(archived_lead)
    assert len(pending_lead["discovery_lead_id"]) == 192
    assert len(archived_lead["discovery_lead_id"]) == 192
    assert pending_lead["warning"]["message"] == (
        "DISCOVERY ONLY — NOT VERIFIED OPERATING AUTHORITY"
    )
    assert "discovery_digest" in pending_lead
    assert "discovery_digest" in archived_lead

    state_counts = pending["corpus_state_counts"]
    assert {
        state: state_counts[state]["searched_document_count"]
        for state in ("active", "grandfathered", "archived")
    } == {"active": 26, "grandfathered": 82, "archived": 4}
    assert state_counts["grandfathered"]["qualifying_document_count"] == 1
    assert state_counts["grandfathered"]["returned_document_count"] == 1
    assert state_counts["grandfathered"]["omitted_document_count"] == 0


def test_mixed_active_and_pending_results_share_one_global_relevance_order(
    tmp_path: Path,
) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "after session open obtain authoritative runbook context before "
        "kd_session_plan without inventing a consultation",
        limit=3,
    )

    assert result["candidates"]
    assert result["discovery_leads"]
    assert result["authoritative_gap"] is False
    merged = sorted(
        result["candidates"] + result["discovery_leads"],
        key=lambda item: item["relevance_rank"],
    )
    assert [item["relevance_rank"] for item in merged] == list(
        range(1, len(merged) + 1)
    )
    assert {item["catalog_state"] for item in merged} >= {
        "ACTIVE",
        "grandfathered",
    }


def test_catalog_manifest_active_set_drift_fails_closed(tmp_path: Path) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)
    pinned = yaml.safe_load((tmp_path / "CORPUS-MANIFEST.yaml").read_text())
    states = {
        entry["path"]: entry["catalog_state"] for entry in pinned["documents"]
    }
    active_path = min(path for path, state in states.items() if state == "active")
    states[active_path] = "grandfathered"
    changed_sha = _commit_snapshot_manifest(
        tmp_path,
        pinned["inventory"]["inventory_sha"],
        states,
        base_sha=pinned["inventory"]["base_sha"],
    )

    with pytest.raises(CatalogError, match="catalog/manifest ACTIVE path drift"):
        search_catalog(
            tmp_path,
            catalog_ref.replace(catalog_ref.split("@")[1].split(":")[0], changed_sha),
            "peer inbox",
        )


@pytest.mark.parametrize(
    "query",
    [
        "path:",
        "path:../escape.md",
        "path:/absolute.md",
        "path:runbooks\\escape.md",
        "path:wrong.txt",
        "path:two words.md",
        "path:.git/config.md",
        "path:./relative.md",
    ],
)
def test_malformed_exact_path_queries_fail_closed(
    tmp_path: Path,
    query: str,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    with pytest.raises(CatalogError, match="path query"):
        search_catalog(tmp_path, catalog_ref, query)


def test_generic_intent_without_domain_evidence_is_an_honest_miss(
    tmp_path: Path,
) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "run restore debug verify")

    assert result["candidates"] == []
    assert result["discovery_leads"] == []
    assert result["status"] == "no_relevant_result"
    assert result["discovery_status"] == "no_qualifying_discovery_lead"


def test_state_and_catalog_only_metadata_cannot_change_common_relevance(
    tmp_path: Path,
) -> None:
    sha, catalog_ref = _working_tree_pin(tmp_path)
    validated = catalog_validator.load_validated_catalog(tmp_path, catalog_ref)
    _manifest, snapshot = catalog_search._load_corpus_snapshot(
        tmp_path,
        validated.catalog,
        sha,
    )
    record = next(
        item
        for item in snapshot
        if item.manifest.path == "qdrant-sync-outbox.md"
    )
    query = "recover Qdrant synchronization after a killed worker leaves an outbox row"
    query_tokens = catalog_search._validated_query_tokens(query)
    subject_tokens = query_tokens - catalog_search._GENERIC_INTENT_TOKENS
    matching_unit = next(
        unit
        for section in record.document.sections
        if section.level != 1
        for unit in [
            catalog_search._SearchUnit(
                record=record,
                unit_kind="section",
                title=record.title,
                section=section,
                searchable_text=section.direct_text,
            )
        ]
        if catalog_search._common_relevance(
            unit,
            query,
            subject_tokens,
            None,
        )
        is not None
    )
    baseline = catalog_search._common_relevance(
        matching_unit,
        query,
        subject_tokens,
        None,
    )
    flipped_record = replace(
        record,
        manifest=replace(
            record.manifest,
            catalog_state="active",
            status="active",
            proposed_disposition="retain_active",
            risk="P3",
        ),
        catalog_entry={
            "aliases": ["catalog-only-alias"],
            "owner": "changed-owner",
            "last_verified_at": "2099-01-01",
        },
    )
    flipped = catalog_search._common_relevance(
        replace(matching_unit, record=flipped_record),
        query,
        subject_tokens,
        None,
    )

    assert flipped == baseline
    assert baseline is not None
    common_row = {
        "path": record.manifest.path,
        "unit_kind": "section",
        "section_id": "fixture",
        "heading_line": 1,
        "excerpt_sha256": "0" * 64,
        "relevance_score": baseline[0],
        "catalog_state": "grandfathered",
        "risk": "P1",
    }
    assert catalog_search._global_result_sort_key(common_row) == (
        catalog_search._global_result_sort_key(
            {
                **common_row,
                "catalog_state": "active",
                "risk": "P3",
                "owner": "changed-owner",
            }
        )
    )


def test_published_batch_maximum_preserves_worst_case_mandatory_breadth(
    tmp_path: Path,
) -> None:
    _, _catalog_ref = _working_tree_pin(tmp_path)
    manifest_path = tmp_path / "CORPUS-MANIFEST.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    for entry in manifest["documents"]:
        if entry["catalog_state"] != "active":
            entry["batch"] = "b" * MAX_PINNED_BATCH_WIRE_BYTES
            entry["verify_against"] = [
                "v" * MAX_PINNED_VERIFY_AGAINST_ITEM_WIRE_BYTES,
            ]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    subprocess.run(
        ["git", "add", "CORPUS-MANIFEST.yaml"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "maximum wire verification projection"],
        cwd=tmp_path,
        check=True,
    )
    search_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    catalog_ref = f"git:aidotmarket/runbooks@{search_sha}:CATALOG.json"
    bases = [
        (
            "after session open obtain authoritative runbook context before "
            "kd_session_plan without inventing a consultation"
        ),
        (
            "close a session with truthful runbook impact evidence without "
            "inventing documentation or filler"
        ),
    ]
    queries = [value + " " * (4000 - len(value)) for value in bases]

    delivery = search_catalog_delivery(tmp_path, catalog_ref, queries, limit=1)
    result = delivery.payload

    assert len(queries) == PRODUCTION_LIMITS.batch_objectives == _MAX_BATCH_QUERIES
    assert result["serialized_bytes"] <= 31_929
    assert 31_929 < result["response_budget_bytes"]
    assert all(
        item["candidates"] and item["discovery_leads"]
        for item in result["results"]
    )
    assert [
        [
            len(requirement["prose"])
            for requirement in delivery.verification_bundles[
                item["discovery_leads"][0]["warning"]["verification_bundle_ref"]
            ]["verification_requirements"]
        ]
        for item in result["results"]
    ] == [
        [MAX_PINNED_VERIFY_AGAINST_ITEM_WIRE_BYTES],
        [MAX_PINNED_VERIFY_AGAINST_ITEM_WIRE_BYTES],
    ]
    assert [
        len(item["discovery_leads"][0]["manifest_batch"])
        for item in result["results"]
    ] == [MAX_PINNED_BATCH_WIRE_BYTES] * 2


def test_batch_maximum_plus_one_is_rejected_before_immutable_loading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        catalog_search,
        "load_validated_catalog",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("immutable loading must not start")
        ),
    )

    with pytest.raises(CatalogError, match=f"1 to {_MAX_BATCH_QUERIES}"):
        search_catalog_many(
            tmp_path,
            "git:aidotmarket/runbooks@" + "0" * 40 + ":CATALOG.json",
            ["bounded query"] * (_MAX_BATCH_QUERIES + 1),
        )


def test_oversized_json_query_is_rejected_before_immutable_loading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        catalog_search,
        "load_validated_catalog",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("immutable loading must not start")
        ),
    )
    query = "bounded domain evidence " + "🛰" * 1000

    with pytest.raises(CatalogError, match="canonical JSON-string payload.*4000"):
        search_catalog_many(
            tmp_path,
            "git:aidotmarket/runbooks@" + "0" * 40 + ":CATALOG.json",
            [query] * _MAX_BATCH_QUERIES,
        )


def test_market_discovery_benchmark_is_globally_top_three_and_honest(
    tmp_path: Path,
) -> None:
    sha, catalog_ref = _working_tree_pin(tmp_path)
    fixture = yaml.safe_load(DISCOVERY_BENCHMARK.read_text())
    provenance = fixture["provenance"]
    assert fixture["schema_version"] == 2
    assert fixture["taxonomy_version"] == "market-discovery-v1"
    assert provenance["authored_session"] == "S1413"
    assert provenance["contract_head"] == (
        "bbba79e1fde831f3d3d154a2af9c27388d3c16c5"
    )
    assert provenance["independent_review_status"] == "pending"
    assert "reviewed_by" not in provenance
    cases = fixture["cases"]
    assert len(cases) == 12
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(case["taxonomy_version"] == "market-discovery-v1" for case in cases)
    assert all(len(case["taxonomy_tuple"]) == 4 for case in cases)
    assert all(case["market_area"] for case in cases)
    assert all(case["expected_policy_class"] for case in cases)
    assert all(case["split"] == "implementation_fixture" for case in cases)
    assert all(case["provenance"]["session"] == "S1413" for case in cases)

    results: list[dict] = []
    for start in range(0, len(cases), _MAX_BATCH_QUERIES):
        group = cases[start : start + _MAX_BATCH_QUERIES]
        response = search_catalog_many(
            tmp_path,
            catalog_ref,
            [case["query"] for case in group],
        )
        assert response["catalog_sha"] == sha
        results.extend(response["results"])

    for case, result in zip(cases, results, strict=True):
        top_three = sorted(
            result["candidates"] + result["discovery_leads"],
            key=lambda item: item["relevance_rank"],
        )[:3]
        returned_paths = {item["path"] for item in top_three}
        if "required_paths" in case:
            assert set(case["required_paths"]) <= returned_paths, (
                case["id"],
                [(item["relevance_rank"], item["path"]) for item in top_three],
            )
        else:
            current = set(case["required_any_paths"]) & returned_paths
            assert current, (
                case["id"],
                [(item["relevance_rank"], item["path"]) for item in top_three],
            )
            assert all(
                item["catalog_state"] != "archived"
                for item in top_three
                if item["path"] in current
            )
            historical = case["historical_path_cannot_satisfy"]
            if historical in returned_paths:
                historical_item = next(
                    item for item in top_three if item["path"] == historical
                )
                assert historical_item["historical_only"] is True


def test_r6_exact_discovery_delivery_is_closed_and_bundle_complete(
    tmp_path: Path,
) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)

    delivery = search_catalog_delivery(
        tmp_path,
        catalog_ref,
        ["path:ai-market-backend.md"],
    )
    payload = delivery.payload
    assert set(payload) == {
        "schema_version",
        "catalog_sha",
        "manifest_sha256",
        "inventory_sha",
        "results",
        "searched_entry_count",
        "searched_section_count",
        "complete",
        "response_budget_bytes",
        "response_budget_truncated",
        "dropped_candidate_count",
        "serialized_bytes",
        "delivery_digest",
    }
    assert delivery.text.endswith("\n")
    assert len(delivery.text.encode("utf-8")) == payload["serialized_bytes"]
    zeroed = dict(payload)
    zeroed["delivery_digest"] = "0" * 64
    assert hashlib.sha256(
        canonical_json_bytes(zeroed, final_newline=True)
    ).hexdigest() == payload["delivery_digest"]

    objective = payload["results"][0]
    assert objective["status"] == "no_positive_candidate_in_active_catalog"
    assert objective["discovery_status"] == "discovery_leads_returned_unverified"
    assert objective["authoritative_gap"] is True
    assert objective["candidates"] == []
    assert len(objective["discovery_leads"]) == 1
    lead = objective["discovery_leads"][0]
    assert len(lead["discovery_lead_id"]) == 192
    assert lead["warning"]["message"] == (
        "DISCOVERY ONLY — NOT VERIFIED OPERATING AUTHORITY"
    )
    assert len(lead["warning"]["verification_bundle_ref"]) == 192
    assert "verification_requirements" not in lead

    bundle = delivery.verification_bundles[
        lead["warning"]["verification_bundle_ref"]
    ]
    assert bundle["verification_bundle_digest"] == lead["warning"][
        "verification_bundle_digest"
    ]
    assert bundle["requirement_count"] == len(bundle["verification_requirements"])
    assert [row["ordinal"] for row in bundle["verification_requirements"]] == list(
        range(1, bundle["requirement_count"] + 1)
    )
    assert all(
        row["adapter_type"] == "unmapped_prose"
        for row in bundle["verification_requirements"]
    )


def test_r6_selection_delivers_global_top_three_plus_a_missing_policy_class(
    tmp_path: Path,
) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)
    query = (
        "after session open obtain authoritative runbook context before "
        "kd_session_plan without inventing a consultation"
    )

    objective = search_catalog_delivery(
        tmp_path,
        catalog_ref,
        [query],
    ).payload["results"][0]
    delivered = sorted(
        objective["candidates"] + objective["discovery_leads"],
        key=lambda item: item["relevance_rank"],
    )

    assert [item["relevance_rank"] for item in delivered[:3]] == [1, 2, 3]
    assert len(delivered) <= 4
    assert objective["active_qualifying_count"] > 0
    assert objective["grandfathered_qualifying_count"] > 0
    assert objective["candidates"]
    assert objective["discovery_leads"]
    assert {item["catalog_state"] for item in delivered} >= {
        "ACTIVE",
        "grandfathered",
    }


def test_r7_residual_allocator_uses_available_headroom_for_grounded_context(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text().replace(
            "Drain the peer inbox at session open before dispatching work.",
            "Drain the peer inbox at session open before dispatching work. "
            + "Verify the bounded peer receipt against durable state. " * 100,
            1,
        )
    )
    generate_catalog(tmp_path)
    sha = _refresh_search_snapshot(tmp_path, "long grounded peer procedure")

    delivery = search_catalog_delivery(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        ["drain peer inbox"],
    )
    candidate = delivery.payload["results"][0]["candidates"][0]

    assert PRODUCTION_LIMITS.initial_corpus_excerpt_j < len(
        canonical_string_bytes(candidate["excerpt"])
    ) <= PRODUCTION_LIMITS.corpus_excerpt_j
    assert delivery.payload["serialized_bytes"] <= (
        PRODUCTION_LIMITS.response_build_proof_bytes
    )


def test_r7_residual_allocation_is_identical_across_policy_state_flips(
    tmp_path: Path,
) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)
    validated = catalog_validator.load_validated_catalog(tmp_path, catalog_ref)
    manifest, snapshot = catalog_search._load_corpus_snapshot(
        tmp_path,
        validated.catalog,
        sha,
    )
    query = "drain peer inbox"
    raw = catalog_search._search_corpus(
        sha,
        manifest,
        snapshot,
        query,
        catalog_search._validated_query_tokens(query),
        excerpt_char_limit=PRODUCTION_LIMITS.corpus_excerpt_j,
    )
    base = raw["candidates"][0]

    active_batches: list[dict] = []
    discovery_batches: list[dict] = []
    for objective in range(2):
        active_rows = []
        discovery_rows = []
        for rank in range(1, 4):
            excerpt = "x" * PRODUCTION_LIMITS.corpus_excerpt_j
            common = {
                **base,
                "path": f"runbooks/state-neutral-{objective}-{rank}.md",
                "relevance_rank": rank,
                "excerpt": excerpt,
                "excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
                "excerpt_truncated": True,
                "excerpt_end_line": base["excerpt_start_line"],
                "excerpt_end_column_exclusive": len(excerpt) + 1,
            }
            active_rows.append(common)
            discovery_rows.append(
                {
                    **common,
                    "action_authority_eligible": False,
                    "authority_admission": False,
                    "candidate_id_eligible": False,
                    "candidate_kind": "grandfathered_discovery_lead",
                    "catalog_declared": False,
                    "catalog_state": "grandfathered",
                    "declaration_kinds": [],
                    "integrity_only": True,
                    "status": "pending_verification",
                }
            )
        active_batches.append({"candidates": active_rows, "discovery_leads": []})
        discovery_batches.append(
            {"candidates": [], "discovery_leads": discovery_rows}
        )

    kwargs = {
        "searched_entry_count": len(snapshot),
        "searched_section_count": catalog_search._searched_section_count(snapshot),
        "limits": PRODUCTION_LIMITS,
    }
    active_allocation = catalog_search._allocate_r7_residual_excerpts(
        active_batches,
        **kwargs,
    )
    discovery_allocation = catalog_search._allocate_r7_residual_excerpts(
        discovery_batches,
        **kwargs,
    )
    active_widths = [
        len(canonical_string_bytes(row["excerpt"]))
        for objective in active_allocation
        for row in objective
    ]
    discovery_widths = [
        len(canonical_string_bytes(row["excerpt"]))
        for objective in discovery_allocation
        for row in objective
    ]

    assert active_widths == discovery_widths
    assert any(
        PRODUCTION_LIMITS.initial_corpus_excerpt_j < width
        < PRODUCTION_LIMITS.corpus_excerpt_j
        for width in active_widths
    )
    assert [
        catalog_search._r6_common_result(row)["retrieval_digest"]
        for objective in active_allocation
        for row in objective
    ] == [
        catalog_search._r6_common_result(row)["retrieval_digest"]
        for objective in discovery_allocation
        for row in objective
    ]


def test_r7_guidance_cannot_change_fixed_corpus_allocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)
    query = "drain peer inbox and update runbook"
    with_guidance = search_catalog_delivery(tmp_path, catalog_ref, [query]).payload
    monkeypatch.setattr(
        catalog_search,
        "_repository_authoring_guidance_candidate",
        lambda *_args, **_kwargs: None,
    )
    without_guidance = search_catalog_delivery(tmp_path, catalog_ref, [query]).payload

    with_objective = with_guidance["results"][0]
    without_objective = without_guidance["results"][0]
    assert with_objective["supplemental_guidance"]
    assert without_objective["supplemental_guidance"] == []
    for field in (
        "candidates",
        "discovery_leads",
        "corpus_response_digest",
        "qualifying_result_count",
        "eligible_candidate_count",
        "eligible_candidates_returned",
        "active_returned_count",
        "grandfathered_returned_count",
        "archived_returned_count",
    ):
        assert with_objective[field] == without_objective[field]


def test_r6_cli_emits_exact_canonical_text_without_prefix_or_reencoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)
    query = "path:ai-market-backend.md"
    expected = search_catalog_delivery(tmp_path, catalog_ref, [query]).text
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        catalog_cmd,
        ["search", "--catalog-ref", catalog_ref, query],
    )

    assert result.exit_code == 0, result.output
    assert result.output == expected
    assert result.output.endswith("\n")
    assert not result.output.startswith("RUNBOOK")


def test_r6_production_entrypoint_rejects_any_limits_override_before_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        catalog_search,
        "load_validated_catalog",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("immutable loading must not start")
        ),
    )

    with pytest.raises(CatalogError, match="invalid_limits_override"):
        search_catalog_delivery(
            tmp_path,
            "git:aidotmarket/runbooks@" + "0" * 40 + ":CATALOG.json",
            ["qdrant"],
            limits=replace(PRODUCTION_LIMITS, response_bytes=39_999),
        )


def test_r7_truthfully_serializes_the_existing_sysadmin_owner(
    tmp_path: Path,
) -> None:
    _, catalog_ref = _working_tree_pin(tmp_path)

    objective = search_catalog_delivery(
        tmp_path,
        catalog_ref,
        ["path:runbooks/corpus-capture-policy.md"],
    ).payload["results"][0]

    assert len(objective["candidates"]) == 1
    assert objective["candidates"][0]["owner"] == "sysadmin"
    assert objective["candidates"][0]["catalog_state"] == "ACTIVE"
