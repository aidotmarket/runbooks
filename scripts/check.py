#!/usr/bin/env python3
"""Check only the simple runbook header and troubleshooting requirement."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

from index import FIELDS, ROOT, corpus_paths, read_page


def check_page(path: Path, root: Path = ROOT) -> list[str]:
    rel = path.relative_to(root).as_posix()
    try:
        header, body = read_page(path)
    except ValueError as exc:
        return [f"{rel}: {exc}"]
    errors = []
    if len(header) != len(FIELDS) or set(header) != set(FIELDS):
        errors.append(f"{rel}: frontmatter fields must be exactly {', '.join(FIELDS)}")
    if not isinstance(header.get("title"), str) or not header.get("title", "").strip():
        errors.append(f"{rel}: title must be a non-empty string")
    if not isinstance(header.get("owner"), str) or not header.get("owner", "").strip():
        errors.append(f"{rel}: owner must be a non-empty string")
    value = header.get("last_verified")
    try:
        if isinstance(value, dt.datetime):
            raise ValueError
        parsed = value if isinstance(value, dt.date) else dt.date.fromisoformat(value)
        if str(parsed) != str(value):
            raise ValueError
    except (TypeError, ValueError):
        errors.append(f"{rel}: last_verified must be an ISO date (YYYY-MM-DD)")
    for field in ("aliases", "error_signatures"):
        values = header.get(field)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            errors.append(f"{rel}: {field} must be a list of strings")
    if not rel.startswith("archive/") and "## When it breaks" not in body.splitlines():
        errors.append(f'{rel}: missing literal "## When it breaks" section')
    return errors


def main(root: Path = ROOT) -> int:
    errors = [error for path in corpus_paths(root) for error in check_page(path, root)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"checked {len(corpus_paths(root))} runbooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
