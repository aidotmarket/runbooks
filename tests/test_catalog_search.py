from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from runbook_tools.catalog.generator import generate_catalog
from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.search import search_catalog, search_catalog_many

REPO_ROOT = Path(__file__).parent.parent


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
        "owner": "test-owner",
        "last_verified_at": "2026-07-31",
    }


def _write_runbook(root: Path, runbook_id: str, metadata: dict, body: str) -> Path:
    path = root / "runbooks" / f"{runbook_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False)
        + "---\n\n"
        + body
    )
    return path


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
        "## §E. Operate\n\nDrain the peer inbox at session open before dispatching work.\n",
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
        "## Status values\n\nFixture.\n"
    )
    generate_catalog(root)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return sha, f"git:aidotmarket/runbooks@{sha}:CATALOG.json", peer


def test_search_ranks_task_language_and_returns_pinned_excerpt_evidence(tmp_path: Path) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "drain peer bus inbox when opening a session",
    )

    assert result["catalog_sha"] == sha
    assert result["searched_entry_count"] == 2
    assert result["status"] == "matched"
    first = result["candidates"][0]
    assert first["runbook_id"] == "peer-instance-discipline"
    assert first["heading"] == "§E. Operate"
    assert first["section_id"] == "operate"
    assert first["section_id_source"] == "catalog"
    assert "Drain the peer inbox" in first["excerpt"]
    assert hashlib.sha256(first["excerpt"].encode()).hexdigest() == first["excerpt_sha256"]
    assert {row["kind"] for row in first["match_evidence"]} >= {"topic", "excerpt"}


def test_search_reads_the_pinned_blob_not_dirty_worktree_content(tmp_path: Path) -> None:
    _, catalog_ref, peer = _repository(tmp_path)
    before = search_catalog(tmp_path, catalog_ref, "peer inbox session open")
    peer.write_text("# Replaced in dirty worktree\n\nNo relevant content.\n")

    after = search_catalog(tmp_path, catalog_ref, "peer inbox session open")

    assert after == before


def test_search_is_deterministic_and_limit_is_bounded(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    first = search_catalog(tmp_path, catalog_ref, "release deploy", limit=1)
    second = search_catalog(tmp_path, catalog_ref, "release deploy", limit=1)

    assert first == second
    assert len(first["candidates"]) == 1
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

    assert result["status"] == "no_positive_match_in_active_catalog"
    assert result["candidates"] == []


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


def test_declared_section_searches_nested_content_and_centers_bounded_excerpt(
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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "nested search fixture"],
        cwd=tmp_path,
        check=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "orbital marmot",
        limit=10,
    )
    declared = next(
        row
        for row in result["candidates"]
        if row["runbook_id"] == "peer-instance-discipline"
        and row["heading"] == "§E. Operate"
    )

    assert "orbital marmot recovery token" in declared["excerpt"]
    assert declared["excerpt_truncated"] is True
    assert len(declared["excerpt"].splitlines()) <= 60
    assert len(declared["excerpt"]) <= 6000
    assert declared["excerpt_start_line"] > declared["heading_line"]


def test_raw_anchor_does_not_claim_catalog_identity(tmp_path: Path) -> None:
    _, _, peer = _repository(tmp_path)
    peer.write_text(
        peer.read_text()
        + '\n<a id="rb-section-hidden-procedure"></a>\n'
        + "### Hidden Procedure\n\nquasar narwhal diagnostic.\n"
    )
    generate_catalog(tmp_path)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "raw anchor fixture"],
        cwd=tmp_path,
        check=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "quasar narwhal",
        limit=10,
    )
    hidden = next(row for row in result["candidates"] if row["heading"] == "Hidden Procedure")

    assert hidden["section_id"] == "hidden-procedure"
    assert hidden["section_id_source"] == "legacy-derived"


def test_identity_and_alias_evidence_only_targets_default_authority(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "peer message bus", limit=10)
    identity_candidates = [
        row
        for row in result["candidates"]
        if {evidence["kind"] for evidence in row["match_evidence"]}
        & {"runbook_id", "path", "alias"}
    ]

    assert identity_candidates
    assert {row["heading"] for row in identity_candidates} == {"§E. Operate"}


def test_many_queries_share_one_catalog_snapshot(tmp_path: Path) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog_many(
        tmp_path,
        catalog_ref,
        ["peer inbox", "payment canary"],
    )

    assert result["catalog_sha"] == sha
    assert len(result["results"]) == 2
    assert {item["catalog_sha"] for item in result["results"]} == {sha}
    assert result["results"][0]["candidates"][0]["runbook_id"] == (
        "peer-instance-discipline"
    )
    assert result["results"][1]["candidates"][0]["runbook_id"] == "billing-deploy"
    with pytest.raises(CatalogError, match="1 to 20"):
        search_catalog_many(tmp_path, catalog_ref, [])
    with pytest.raises(CatalogError, match="1 to 20"):
        search_catalog_many(tmp_path, catalog_ref, ["query"] * 21)


def test_live_operational_language_benchmark_resolves_expected_top_three() -> None:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    cases = [
        ("drain peer message bus when opening a session", "peer-instance-discipline"),
        (
            "reconcile a build queue item whose git branch is ahead of main",
            "build-queue-reconciliation",
        ),
        ("stale Council roster says XAI is an active voter", "council-roster-quirks"),
        (
            "product boundary conflict between requirements and implementation",
            "product-elaboration",
        ),
        ("verify a builder branch actually landed on remote main", "branch-landed-verification"),
        ("dispatch an agent build and recover a gateway timeout", "agent-dispatch"),
        ("age an undispatched stale queue item", "aging-policy"),
        ("check whether an agent surface is complete", "agent-completeness"),
        ("Council review returned no resolution", "council"),
        ("boot constitution source drift", "constitution-history"),
    ]

    benchmark = search_catalog_many(
        REPO_ROOT,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        [query for query, _ in cases],
    )

    misses = []
    for (query, expected), result in zip(cases, benchmark["results"], strict=True):
        top_three = {candidate["runbook_id"] for candidate in result["candidates"]}
        if expected not in top_three:
            misses.append((query, expected, sorted(top_three)))
    assert not misses
