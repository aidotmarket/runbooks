from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check  # noqa: E402
import index  # noqa: E402


def page(title: str, signature: str = "", when_breaks: bool = True) -> str:
    errors = f"['{signature}']" if signature else "[]"
    section = "\n## When it breaks\n\nRestart the example.\n" if when_breaks else ""
    return f"""---
title: {title}
owner: ops
last_verified: 2026-08-30
aliases: []
error_signatures: {errors}
---

# {title}

This page explains {title}.{section}
"""


def write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_corpus_selection_excludes_repository_meta(tmp_path: Path) -> None:
    current = write(tmp_path, "runbooks/current.md", page("Current"))
    archived = write(tmp_path, "archive/old.md", page("Old", when_breaks=False))
    write(tmp_path, "README.md", "guide")
    write(tmp_path, "PLAN-runbook-simplification.md", "plan")
    write(tmp_path, "INDEX.md", "generated")
    write(tmp_path, "specs/design.md", page("Spec"))
    write(tmp_path, "audits/audit.md", page("Audit"))
    write(tmp_path, "tests/fixture.md", page("Fixture"))

    assert index.corpus_paths(tmp_path) == [archived, current]
    assert check.check_page(archived, tmp_path) == []


def test_index_output_is_deterministic(tmp_path: Path) -> None:
    write(tmp_path, "zeta.md", page("Zeta"))
    write(tmp_path, "runbooks/alpha.md", page("Alpha"))

    index.write_outputs(tmp_path)
    first = ((tmp_path / "INDEX.md").read_text(), (tmp_path / "ERRORS.md").read_text())
    index.write_outputs(tmp_path)
    second = ((tmp_path / "INDEX.md").read_text(), (tmp_path / "ERRORS.md").read_text())

    assert first == second
    assert first[0].index("## Alpha") < first[0].index("## Zeta")


def test_duplicate_signature_lists_every_destination(tmp_path: Path) -> None:
    write(tmp_path, "one.md", page("One", "same failure"))
    write(tmp_path, "runbooks/two.md", page("Two", "same failure"))

    errors = index.render_errors(index.load_pages(tmp_path))

    assert errors.count("## `same failure`") == 1
    assert "(one.md)" in errors
    assert "(runbooks/two.md)" in errors


def test_malformed_header_fails(tmp_path: Path) -> None:
    path = write(tmp_path, "broken.md", "---\ntitle: [broken\n---\n\n# Broken\n")

    assert any("malformed frontmatter" in error for error in check.check_page(path, tmp_path))


def test_missing_when_it_breaks_fails_for_current_page(tmp_path: Path) -> None:
    path = write(tmp_path, "missing.md", page("Missing", when_breaks=False))

    assert check.check_page(path, tmp_path) == [
        'missing.md: missing literal "## When it breaks" section'
    ]
