from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import runbook_tools.catalog.search as catalog_search
import runbook_tools.catalog.validator as catalog_validator
from runbook_tools.catalog.generator import generate_catalog, source_paths
from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.search import (
    _score_sources,
    search_catalog,
    search_catalog_many,
)
from tests.catalog_test_support import (
    conformant_catalog_document,
    ensure_catalog_schemas,
)

REPO_ROOT = Path(__file__).parent.parent
SEARCH_BENCHMARK = Path(__file__).parent / "fixtures" / "catalog" / "search_benchmark.yaml"

pytestmark = pytest.mark.usefixtures("synthetic_git_catalog_projection")


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
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
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
    shutil.copy2(REPO_ROOT / "README.md", root / "README.md")
    generate_catalog(root)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "working tree catalog fixture"],
        cwd=root,
        check=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
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
    assert {row["kind"] for row in first["match_evidence"]} >= {"topic", "excerpt"}


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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "replacement fixture"],
        cwd=tmp_path,
        check=True,
    )
    replacement_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
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
    assert len(first["candidates"]) == 1
    assert first["response_budget_bytes"] == 40_000
    assert first["response_budget_truncated"] is False
    assert first["dropped_candidate_count"] == 0
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

    assert result["status"] == "no_positive_candidate_in_active_catalog"
    assert result["candidates"] == []


def test_delivery_digest_binds_the_exact_returned_payload(tmp_path: Path) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "peer inbox")
    digest = result.pop("delivery_digest")

    canonical = json.dumps(
        result,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == digest


def test_complete_single_response_reports_exact_cli_wire_size_with_multibyte_query(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "payment canary café 🛰")
    wire = json.dumps(result, sort_keys=True) + "\n"

    assert result["complete"] is True
    assert result["serialized_bytes"] == len(wire.encode())
    assert len(wire.encode()) <= result["response_budget_bytes"] == 40_000
    assert len(wire) <= result["response_budget_bytes"]


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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "historical fixture"],
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
        "quasar narwhal obsolescent",
        limit=10,
    )

    assert result["status"] == "no_positive_candidate_in_active_catalog"
    assert result["candidates"] == []

    active = search_catalog(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        "active sapphire recovery instruction",
        limit=10,
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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "duplicate heading fixture"],
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
        "operate quasar duplicate-only appendix",
        limit=10,
    )
    duplicates = [
        row
        for row in result["candidates"]
        if row["runbook_id"] == "peer-instance-discipline"
        and row["heading"] == "§E. Operate"
    ]

    assert len(duplicates) == 2
    anchored = next(row for row in duplicates if row["section_id"] == "operate")
    unanchored = next(row for row in duplicates if row["section_id"] == "e-operate")
    assert anchored["catalog_declared"] is True
    assert anchored["section_id_source"] == "catalog"
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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "multiple authorities"],
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
    catalog_ref = f"git:aidotmarket/runbooks@{sha}:CATALOG.json"

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "start by draining the peer message bus inbox",
        limit=10,
    )
    identity_candidates = [
        row
        for row in result["candidates"]
        if {evidence["kind"] for evidence in row["match_evidence"]}
        & {"runbook_id", "path", "alias"}
    ]

    assert identity_candidates
    assert {row["heading"] for row in identity_candidates} == {"§E. Operate"}


def test_alias_only_query_falls_back_to_declared_c_authority_not_generic_e(
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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "c authority alias fallback"],
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
    identity_candidates = [
        candidate
        for candidate in result["candidates"]
        if any(
            evidence["kind"] == "alias"
            for evidence in candidate["match_evidence"]
        )
    ]

    assert len(identity_candidates) == 1
    assert identity_candidates[0]["heading"] == "§C. Architecture & Interactions"
    assert identity_candidates[0]["catalog_declared"] is True


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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "child literal provenance"],
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
        "change mystery_call",
        limit=10,
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
        limit=10,
    )

    assert all(candidate["heading"] != "Peer Instance Discipline" for candidate in result["candidates"])


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
    assert {item["catalog_sha"] for item in result["results"]} == {sha}
    assert result["results"][0]["candidates"][0]["runbook_id"] == (
        "peer-instance-discipline"
    )
    assert result["results"][1]["candidates"][0]["runbook_id"] == "billing-deploy"
    assert len(result["delivery_digest"]) == 64
    assert result["complete"] is True
    assert result["serialized_bytes"] == len(
        (json.dumps(result, sort_keys=True) + "\n").encode()
    )
    assert {
        item["searched_section_count"] for item in result["results"]
    } == {result["searched_section_count"]}
    assert result["response_budget_truncated"] is False
    with pytest.raises(CatalogError, match="1 to 20"):
        search_catalog_many(tmp_path, catalog_ref, [])
    with pytest.raises(CatalogError, match="1 to 20"):
        search_catalog_many(tmp_path, catalog_ref, ["query"] * 21)


def test_many_queries_enforce_a_global_serialized_response_budget(
    tmp_path: Path,
) -> None:
    _, _, peer = _repository(tmp_path)
    billing = tmp_path / "runbooks/billing-deploy.md"
    expansion = " sharedtoken café 🛰" * 2000
    peer.write_text(peer.read_text() + expansion + "\n")
    billing.write_text(billing.read_text() + expansion + "\n")
    generate_catalog(tmp_path)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "response budget fixture"],
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

    result = search_catalog_many(
        tmp_path,
        f"git:aidotmarket/runbooks@{sha}:CATALOG.json",
        ["sharedtoken"] * 20,
        limit=10,
    )

    wire = json.dumps(result, sort_keys=True) + "\n"
    assert result["complete"] is True
    assert result["serialized_bytes"] == len(wire.encode())
    assert len(wire.encode()) <= result["response_budget_bytes"] == 40_000
    assert len(wire) <= result["response_budget_bytes"]
    assert result["response_budget_truncated"] is True
    assert result["dropped_candidate_count"] > 0
    candidate_counts = [len(item["candidates"]) for item in result["results"]]
    omitted = [
        item for item in result["results"] if not item["candidates"]
    ]
    if omitted:
        assert max(candidate_counts) <= 1
        assert {
            item["status"] for item in omitted
        } == {"no_usable_candidate_id_response_budget"}


def test_authoring_task_prepends_pinned_non_authoritative_repository_contract(
    tmp_path: Path,
) -> None:
    sha, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(
        tmp_path,
        catalog_ref,
        "create or update an authoritative runbook after implementing a process change",
    )

    guidance = next(
        candidate
        for candidate in result["candidates"]
        if candidate["candidate_kind"] == "repository_authoring_guidance"
    )
    assert guidance["path"] == "README.md"
    assert guidance["heading"] == "Working on a runbook"
    assert guidance["candidate_kind"] == "repository_authoring_guidance"
    assert guidance["candidate_id_eligible"] is False
    assert guidance["catalog_declared"] is False
    assert guidance["integrity_only"] is True
    assert guidance["integrity_status"] == "integrity_pass_unverified"
    assert guidance["semantic_verification"] is False
    assert guidance["authority_admission"] is False
    assert guidance["action_authority_eligible"] is False
    assert guidance["authority_keys"] == []
    assert guidance["rank"] is None
    assert guidance["supplemental"] is True
    assert result["eligible_candidates_returned"] >= 1
    blob = subprocess.run(
        ["git", "show", f"{sha}:README.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    selected = blob.splitlines()[
        guidance["excerpt_start_line"] - 1 : guidance["excerpt_end_line"]
    ]
    selected[-1] = selected[-1][
        : guidance["excerpt_end_column_exclusive"] - 1
    ]
    assert "\n".join(selected) == guidance["excerpt"]


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

    result = search_catalog(tmp_path, catalog_ref, query, limit=10)

    guidance = next(
        candidate
        for candidate in result["candidates"]
        if candidate["candidate_kind"] == "repository_authoring_guidance"
    )
    assert guidance["candidate_kind"] == "repository_authoring_guidance"
    assert guidance["candidate_id_eligible"] is False
    assert any(
        evidence["kind"] == "repository_guidance_intent"
        for evidence in guidance["match_evidence"]
    )


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

    result = search_catalog(tmp_path, catalog_ref, query, limit=10)

    assert all(
        candidate["candidate_kind"] != "repository_authoring_guidance"
        for candidate in result["candidates"]
    )


def test_batch_allocates_id_eligible_breadth_before_authoring_guidance(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)
    queries = [
        "update runbook",
        "create a runbook",
        "write documentation",
        "revise the deployment playbook",
        "edit the operator manual",
    ] * 4

    result = search_catalog_many(tmp_path, catalog_ref, queries, limit=10)

    wire = json.dumps(result, sort_keys=True) + "\n"
    assert result["serialized_bytes"] == len(wire.encode())
    assert len(wire.encode()) <= result["response_budget_bytes"] == 40_000
    assert len(wire) <= result["response_budget_bytes"]
    missing_eligible = []
    for objective in result["results"]:
        eligible = [
            candidate
            for candidate in objective["candidates"]
            if candidate["candidate_id_eligible"]
        ]
        if eligible:
            assert objective["status"] == "candidates_returned_unverified"
        else:
            missing_eligible.append(objective)
            assert objective["status"] == "no_usable_candidate_id_response_budget"

    if missing_eligible:
        assert all(
            candidate["candidate_kind"] != "repository_authoring_guidance"
            for objective in result["results"]
            for candidate in objective["candidates"]
        )
        assert max(
            sum(
                candidate["candidate_id_eligible"]
                for candidate in objective["candidates"]
            )
            for objective in result["results"]
        ) <= 1


def test_limit_one_preserves_active_candidate_and_adds_guidance_supplementally(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, "update runbook", limit=1)

    eligible = [
        candidate
        for candidate in result["candidates"]
        if candidate["candidate_id_eligible"]
    ]
    guidance = [
        candidate
        for candidate in result["candidates"]
        if candidate["candidate_kind"] == "repository_authoring_guidance"
    ]
    assert len(eligible) == 1
    assert len(guidance) == 1
    assert result["candidates"][0]["candidate_id_eligible"] is True
    assert result["eligible_candidates_returned"] == 1
    assert result["eligible_candidate_count"] == (
        result["eligible_candidates_returned"]
        + result["eligible_candidates_omitted_by_limit"]
        + result["eligible_candidates_omitted_by_response_budget"]
    )


def test_mixed_twenty_objective_batch_never_reports_success_without_eligible_id(
    tmp_path: Path,
) -> None:
    _, catalog_ref, _ = _repository(tmp_path)
    queries = (
        ["update runbook", "write documentation"] * 5
        + ["peer inbox", "payment canary"] * 5
    )

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
    _, catalog_ref = _working_tree_pin(tmp_path)

    credential = search_catalog(
        tmp_path,
        catalog_ref,
        "repair a credential exposure and secret disclosure",
        limit=10,
    )["candidates"][0]
    assert credential["runbook_id"] == "infrastructure-discovery"
    assert credential["heading"] == "§G. Repair"
    assert credential["catalog_declared"] is True
    assert {
        "topic:security-credential-exposure",
        "topic:security-secret-disclosure",
    } <= set(credential["authority_keys"])

    council = search_catalog(
        tmp_path,
        catalog_ref,
        "diagnose Council schema and roster drift for a required reviewer",
        limit=10,
    )["candidates"][0]
    assert council["runbook_id"] == "council"
    assert council["heading"] == "§F. Isolate"
    assert council["catalog_declared"] is True
    assert {
        "topic:council-schema-drift",
        "topic:council-roster-drift",
    } <= set(council["authority_keys"])


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
    _, catalog_ref = _working_tree_pin(tmp_path)

    result = search_catalog(tmp_path, catalog_ref, query)

    matching = [
        candidate
        for candidate in result["candidates"][:3]
        if candidate["runbook_id"] == "peer-instance-discipline"
        and candidate["heading"] == "§E. Operate"
    ]
    assert matching
    excerpt = matching[0]["excerpt"].casefold()
    assert all(token.casefold() in excerpt for token in required_tokens)


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

    benchmark_results: list[dict] = []
    benchmark_sha: str | None = None
    for start in range(0, len(cases), 4):
        group = cases[start : start + 4]
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
            matching = [
                candidate
                for candidate in result["candidates"][:3]
                if candidate["runbook_id"] == case["expected_runbook_id"]
                and (
                    candidate["section_id"] == case.get("expected_section_id")
                    if "expected_section_id" in case
                    else candidate["heading"] == case["expected_heading"]
                )
                and all(
                    token.casefold() in candidate["excerpt"].casefold()
                    for token in case["required_action_tokens"]
                )
            ]
            if matching:
                section_successes += 1
            else:
                section_misses.append(
                    (
                        case["id"],
                        [
                            (candidate["runbook_id"], candidate["heading"])
                            for candidate in result["candidates"][:3]
                        ],
                    )
                )
        elif expectation == "no_positive_candidate":
            assert result["status"] == "no_positive_candidate_in_active_catalog"
            assert result["candidates"] == []
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
            guidance = next(
                candidate
                for candidate in result["candidates"]
                if candidate["candidate_kind"] == "repository_authoring_guidance"
            )
            assert guidance["path"] == case["expected_path"]
            assert guidance["heading"] == case["expected_heading"]
            assert guidance["candidate_kind"] == "repository_authoring_guidance"
            assert guidance["candidate_id_eligible"] is False
            assert guidance["catalog_declared"] is False
        else:
            raise AssertionError(f"unknown benchmark expectation: {expectation}")
    assert section_successes / len(section_cases) >= 0.9, section_misses
    assert benchmark_sha == sha
