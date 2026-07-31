from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.sections import (
    MarkdownDocument,
    MarkdownSection,
    parse_markdown_document,
)
from runbook_tools.catalog.validator import load_validated_catalog

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "agent",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "runbook",
    "system",
    "task",
    "the",
    "to",
    "with",
    "work",
}
_MAX_EXCERPT_LINES = 60
_MAX_EXCERPT_CHARS = 6000


def search_catalog(
    repo_root: Path,
    catalog_ref: str,
    query: str,
    *,
    limit: int = 3,
) -> dict[str, Any]:
    """Rank citable sections from one validated, immutable catalog snapshot.

    This is deliberately deterministic and dependency-light. It is the safe
    first-stage retriever; an optional semantic reranker may reorder results,
    but it must never replace the catalog SHA, Git blob, or excerpt hash that
    make a returned candidate auditable.
    """

    query_tokens = _validated_query_tokens(query)
    _validate_limit(limit)
    validated = load_validated_catalog(repo_root, catalog_ref)
    snapshot = _load_snapshot(repo_root.resolve(), validated.catalog, validated.report.catalog_sha)
    return _search_snapshot(
        validated.report.catalog_sha,
        snapshot,
        query,
        query_tokens,
        limit,
    )


def search_catalog_many(
    repo_root: Path,
    catalog_ref: str,
    queries: list[str] | tuple[str, ...],
    *,
    limit: int = 3,
) -> dict[str, Any]:
    """Search up to twenty objectives against one validated Git snapshot."""

    if not isinstance(queries, (list, tuple)) or not 1 <= len(queries) <= 20:
        raise CatalogError("search queries must contain from 1 to 20 items")
    query_tokens = [_validated_query_tokens(query) for query in queries]
    _validate_limit(limit)
    validated = load_validated_catalog(repo_root, catalog_ref)
    sha = validated.report.catalog_sha
    snapshot = _load_snapshot(repo_root.resolve(), validated.catalog, sha)
    return {
        "catalog_sha": sha,
        "results": [
            _search_snapshot(sha, snapshot, query, tokens, limit)
            for query, tokens in zip(queries, query_tokens, strict=True)
        ],
        "searched_entry_count": len(snapshot),
        "searched_section_count": sum(
            len(document.sections) for _, document in snapshot
        ),
    }


def _load_snapshot(
    repo_root: Path,
    catalog: dict[str, Any],
    sha: str,
) -> list[tuple[dict[str, Any], MarkdownDocument]]:
    return [
        (
            entry,
            parse_markdown_document(_git_show_text(repo_root, sha, entry["path"])),
        )
        for entry in catalog["entries"]
    ]


def _search_snapshot(
    sha: str,
    snapshot: list[tuple[dict[str, Any], MarkdownDocument]],
    query: str,
    query_tokens: set[str],
    limit: int,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    searched_section_count = 0
    for entry, document in snapshot:
        searched_section_count += len(document.sections)
        for section in document.sections:
            declarations = [
                row
                for row in (*entry["authoritative_for"], *entry["error_signatures"])
                if row["section"] == section.heading
            ]
            explicit_ids = {
                row["section_id"] for row in declarations if "section_id" in row
            }
            if explicit_ids:
                section_id = min(explicit_ids)
                section_id_source = "catalog"
            else:
                section_id = _section_id(section.heading)
                section_id_source = "legacy-derived"

            searchable_text = section.text if declarations else section.direct_text
            excerpt, start_line, end_line, truncated = _bounded_excerpt(
                searchable_text,
                section,
                query_tokens,
            )
            scored = _score_section(
                query,
                query_tokens,
                entry,
                section.heading,
                excerpt,
            )
            if scored[0] <= 0:
                continue
            excerpt_bytes = excerpt.encode()
            excerpt_sha256 = hashlib.sha256(excerpt_bytes).hexdigest()
            candidate_digest = hashlib.sha256(
                "\0".join(
                    (
                        sha,
                        entry["runbook_id"],
                        section_id,
                        str(section.heading_line),
                        excerpt_sha256,
                    )
                ).encode()
            ).hexdigest()
            candidates.append(
                {
                    "candidate_digest": candidate_digest,
                    "excerpt": excerpt,
                    "excerpt_end_line": end_line,
                    "excerpt_sha256": excerpt_sha256,
                    "excerpt_start_line": start_line,
                    "excerpt_truncated": truncated,
                    "heading": section.heading,
                    "heading_line": section.heading_line,
                    "match_evidence": scored[1],
                    "path": entry["path"],
                    "runbook_id": entry["runbook_id"],
                    "score": round(scored[0], 6),
                    "section_id": section_id,
                    "section_id_source": section_id_source,
                }
            )

    candidates.sort(
        key=lambda row: (
            -row["score"],
            row["runbook_id"],
            row["section_id"],
            row["heading_line"],
            row["excerpt_sha256"],
        )
    )
    return {
        "catalog_sha": sha,
        "candidates": candidates[:limit],
        "query": query,
        "searched_entry_count": len(snapshot),
        "searched_section_count": searched_section_count,
        "status": "matched" if candidates else "no_positive_match_in_active_catalog",
    }


def _validated_query_tokens(query: str) -> set[str]:
    if not isinstance(query, str) or not query.strip():
        raise CatalogError("search query must be a non-empty string")
    if len(query) > 4000:
        raise CatalogError("search query must not exceed 4000 characters")
    tokens = _tokens(query)
    if not tokens:
        raise CatalogError("search query must contain at least one searchable token")
    return tokens


def _validate_limit(limit: int) -> None:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10:
        raise CatalogError("search limit must be an integer from 1 to 10")


def _score_section(
    query: str,
    query_tokens: set[str],
    entry: dict[str, Any],
    heading: str,
    excerpt: str,
) -> tuple[float, list[dict[str, Any]]]:
    normalized_query = " ".join(_TOKEN_RE.findall(query.casefold()))
    sources: list[tuple[str, str, float]] = [
        ("heading", heading, 5.0),
        ("excerpt", excerpt, 1.0),
    ]
    default_heading = entry["authoritative_for"][0]["section"]
    if heading == default_heading:
        sources.extend(
            [
                ("runbook_id", entry["runbook_id"].replace("-", " "), 6.0),
                ("path", entry["path"].replace("-", " "), 2.0),
            ]
        )
        sources.extend(
            ("alias", value.replace("-", " "), 6.0) for value in entry["aliases"]
        )
    for row in entry["authoritative_for"]:
        if row["section"] == heading:
            sources.append(("topic", row["topic"].replace("-", " "), 8.0))
    for row in entry["error_signatures"]:
        if row["section"] == heading:
            sources.append(("error_signature", row["signature"], 9.0))

    score = 0.0
    evidence: list[dict[str, Any]] = []
    for kind, value, weight in sources:
        source_tokens = _tokens(value)
        overlap = sorted(query_tokens & source_tokens)
        if not overlap:
            continue
        contribution = weight * len(overlap) / len(query_tokens)
        normalized_value = " ".join(_TOKEN_RE.findall(value.casefold()))
        if normalized_query and (
            normalized_query in normalized_value or normalized_value in normalized_query
        ):
            contribution += weight
        score += contribution
        evidence.append(
            {
                "kind": kind,
                "matched_tokens": overlap,
                "value": value[:240],
                "weight": weight,
            }
        )
    return score, evidence


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(value.casefold())
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _section_id(heading: str) -> str:
    normalized = heading.casefold().replace("§", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "document"


def _bounded_excerpt(
    searchable_text: str,
    section: MarkdownSection,
    query_tokens: set[str],
) -> tuple[str, int, int, bool]:
    lines = searchable_text.splitlines()
    best_index = 0
    best_overlap = 0
    for index, line in enumerate(lines):
        overlap = len(query_tokens & _tokens(line))
        if overlap > best_overlap:
            best_index = index
            best_overlap = overlap

    start = max(0, best_index - 8)
    if len(lines) - start < _MAX_EXCERPT_LINES:
        start = max(0, len(lines) - _MAX_EXCERPT_LINES)
    end = min(len(lines), start + _MAX_EXCERPT_LINES)
    excerpt = "\n".join(lines[start:end]).strip()
    cropped_by_chars = len(excerpt) > _MAX_EXCERPT_CHARS
    if cropped_by_chars:
        excerpt = excerpt[:_MAX_EXCERPT_CHARS].rstrip()
    excerpt_line_count = excerpt.count("\n") + 1 if excerpt else 0
    start_line = section.heading_line + start
    end_line = start_line + max(0, excerpt_line_count - 1)
    truncated = start > 0 or end < len(lines) or cropped_by_chars
    return excerpt, start_line, end_line, truncated


def _git_show_text(repo_root: Path, sha: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{sha}:{path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip()
        raise CatalogError(f"cannot read {path!r} at {sha}: {detail}")
    try:
        return completed.stdout.decode()
    except UnicodeDecodeError as exc:
        raise CatalogError(f"{path!r} at {sha} is not UTF-8 text") from exc
