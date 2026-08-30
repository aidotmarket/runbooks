#!/usr/bin/env python3
"""Build the two small, human-readable runbook indexes."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("title", "owner", "last_verified", "aliases", "error_signatures")
EXCLUDED_ROOT_PAGES = {
    "ERRORS.md",
    "INDEX.md",
    "PLAN-runbook-simplification.md",
    "PLAN-v5b-controlled-dispatch.md",
    "README.md",
    "task_state.md",
}


def corpus_paths(root: Path = ROOT) -> list[Path]:
    """Return current pages and readable archives, never repo meta-documents."""
    candidates = list(root.glob("*.md"))
    candidates += list((root / "runbooks").rglob("*.md"))
    candidates += list((root / "archive").rglob("*.md"))
    return sorted(
        (
            path
            for path in candidates
            if path.is_file()
            and not (path.parent == root and path.name in EXCLUDED_ROOT_PAGES)
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def read_page(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing opening frontmatter delimiter")
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        raise ValueError("missing closing frontmatter delimiter")
    try:
        header = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed frontmatter: {exc}") from exc
    if not isinstance(header, dict):
        raise ValueError("frontmatter must be a mapping")
    return header, parts[2]


def _one_line(value: object) -> str:
    return " ".join(str(value).split())


def purpose(body: str, title: str) -> str:
    """Use the first ordinary prose paragraph; never require another field."""
    paragraph: list[str] = []
    fenced = False
    comment = False
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("<!--"):
            comment = True
        if comment:
            if "-->" in line:
                comment = False
            continue
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.startswith("#") or line.startswith("|") or line == "---":
            continue
        if re.match(r"^([-*+] |\d+[.)] )", line):
            if paragraph:
                break
            continue
        if not line:
            if paragraph:
                break
            continue
        paragraph.append(line.lstrip("> "))
    if not paragraph:
        return f"Operational notes for {_one_line(title)}."
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", " ".join(paragraph))
    return _one_line(text)


def load_pages(root: Path = ROOT) -> list[dict]:
    pages = []
    for path in corpus_paths(root):
        header, body = read_page(path)
        rel = path.relative_to(root).as_posix()
        pages.append(
            {
                **header,
                "path": rel,
                "purpose": purpose(body, header.get("title", path.stem)),
                "status": "archived" if rel.startswith("archive/") else "current",
            }
        )
    return sorted(pages, key=lambda page: (str(page["title"]).casefold(), page["path"]))


def _joined(values: object) -> str:
    return ", ".join(map(_one_line, values)) if values else "none"


def render_index(pages: list[dict]) -> str:
    lines = ["# Runbook index", ""]
    for page in pages:
        lines.extend(
            [
                f"## {_one_line(page['title'])}",
                f"- Path: `{page['path']}`",
                f"- Purpose: {page['purpose']}",
                f"- Owner: `{_one_line(page['owner'])}`",
                f"- Last verified: `{page['last_verified']}`",
                f"- Aliases: {_joined(page['aliases'])}",
                f"- Error signatures: {_joined(page['error_signatures'])}",
                f"- Status: {page['status']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_errors(pages: list[dict]) -> str:
    destinations: dict[str, list[dict]] = {}
    for page in pages:
        for signature in page["error_signatures"]:
            destinations.setdefault(str(signature), []).append(page)
    lines = ["# Error signatures", ""]
    for signature in sorted(destinations, key=str.casefold):
        lines.extend([f"## `{_one_line(signature)}`", ""])
        for page in destinations[signature]:
            lines.append(f"- [{_one_line(page['title'])}]({page['path']})")
        lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path = ROOT) -> None:
    pages = load_pages(root)
    (root / "INDEX.md").write_text(render_index(pages), encoding="utf-8")
    (root / "ERRORS.md").write_text(render_errors(pages), encoding="utf-8")
    print(f"indexed {len(pages)} runbooks")


if __name__ == "__main__":
    write_outputs()
