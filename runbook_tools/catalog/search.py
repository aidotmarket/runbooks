from __future__ import annotations

import hashlib
import json
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
from runbook_tools.catalog.validator import (
    _preflight_pinned_blobs,
    load_validated_catalog,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "agent",
    "active",
    "current",
    "document",
    "documentation",
    "find",
    "for",
    "from",
    "handling",
    "in",
    "information",
    "of",
    "on",
    "owner",
    "or",
    "process",
    "procedure",
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
_MAX_GUIDANCE_EXCERPT_CHARS = 1200
_MAX_SERIALIZED_BYTES = 40_000
_MAX_HEADING_BYTES = 512
_MAX_SECTION_ID_BYTES = 128
_MAX_AUTHORITY_KEYS = 32
_MAX_AUTHORITY_KEY_BYTES = 256
_MAX_MATCHED_TOKENS = 24
_MAX_MATCHED_TOKEN_BYTES = 64
_README_AUTHORING_HEADING = "Working on a runbook"
_BATCH_EXCERPT_POOL_CHARS = 14_000
_MIN_BATCH_EXCERPT_CHARS = 512
_AUTHORING_ACTION_TOKENS = frozenset(
    {"author", "create", "edit", "maintain", "promote", "revise", "update", "write"}
)
_AUTHORING_ARTIFACT_TOKENS = frozenset(
    {
        "docs",
        "documentation",
        "guide",
        "guidance",
        "manual",
        "playbook",
        "procedure",
        "runbook",
        "runbooks",
    }
)
_AUTHORING_LINK_TOKENS = frozenset(
    {
        "a",
        "an",
        "authoritative",
        "clear",
        "current",
        "deployment",
        "existing",
        "new",
        "operational",
        "operator",
        "our",
        "production",
        "the",
        "their",
        "this",
    }
)
_AUTHORING_ARTIFACT_DISQUALIFIERS = frozenset(
    {
        "api",
        "backup",
        "database",
        "endpoint",
        "file",
        "health",
        "job",
        "repository",
        "server",
        "service",
        "status",
        "system",
        "table",
        "test",
        "tests",
        "tool",
    }
)
_MAX_AUTHORING_PHRASE_DISTANCE = 4

_SECTION_INTENTS: dict[str, frozenset[str]] = {
    "E": frozenset(
        {
            "begin",
            "create",
            "dispatch",
            "execute",
            "invoke",
            "launch",
            "open",
            "operate",
            "run",
            "start",
            "submit",
            "resolve",
            "use",
        }
    ),
    "F": frozenset(
        {
            "check",
            "diagnose",
            "diagnostic",
            "error",
            "fail",
            "failed",
            "failure",
            "inspect",
            "isolate",
            "mismatch",
            "timeout",
            "troubleshoot",
            "verification",
            "verify",
        }
    ),
    "G": frozenset(
        {
            "fix",
            "recover",
            "recovery",
            "remediate",
            "repair",
            "restore",
            "retry",
            "rollback",
        }
    ),
    "H": frozenset(
        {
            "breaking",
            "change",
            "changing",
            "compatibility",
            "contract",
            "evolution",
            "evolve",
            "migrate",
            "redesign",
        }
    ),
}


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
    resolved_root = repo_root.resolve()
    snapshot = _load_snapshot(
        resolved_root,
        validated.catalog,
        validated.report.catalog_sha,
    )
    guidance = _load_repository_guidance(
        resolved_root,
        validated.report.catalog_sha,
    )
    response = _search_snapshot(
        validated.report.catalog_sha,
        snapshot,
        query,
        query_tokens,
    )
    eligible_pool = response.pop("candidates")
    guidance_candidate = _repository_authoring_guidance_candidate(
        validated.report.catalog_sha,
        guidance,
        query,
        _MAX_GUIDANCE_EXCERPT_CHARS,
    )
    response.update(
        {
            "complete": True,
            "response_budget_bytes": _MAX_SERIALIZED_BYTES,
            "response_budget_truncated": False,
            "dropped_candidate_count": 0,
            "serialized_bytes": 0,
        }
    )
    _allocate_single_response(
        response,
        eligible_pool,
        guidance_candidate,
        limit,
    )
    return _finalize_response(response)


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
    guidance = _load_repository_guidance(repo_root.resolve(), sha)
    excerpt_char_limit = _batch_excerpt_char_limit(len(queries))
    results: list[dict[str, Any]] = []
    eligible_pools: list[list[dict[str, Any]]] = []
    guidance_candidates: list[dict[str, Any] | None] = []
    for query, tokens in zip(queries, query_tokens, strict=True):
        result = _search_snapshot(
            sha,
            snapshot,
            query,
            tokens,
            excerpt_char_limit=excerpt_char_limit,
        )
        eligible_pools.append(result.pop("candidates"))
        guidance_candidates.append(
            _repository_authoring_guidance_candidate(
                sha,
                guidance,
                query,
                min(excerpt_char_limit, _MAX_GUIDANCE_EXCERPT_CHARS),
            )
        )
        result["candidates"] = []
        results.append(result)
    response = {
        "catalog_sha": sha,
        "results": results,
        "searched_entry_count": len(snapshot),
        "searched_section_count": sum(
            sum(section.level != 1 for section in document.sections)
            for _, document in snapshot
        ),
        "complete": True,
        "response_budget_bytes": _MAX_SERIALIZED_BYTES,
        "response_budget_truncated": False,
        "dropped_candidate_count": 0,
        "serialized_bytes": 0,
    }
    _allocate_batch_response(
        response,
        eligible_pools,
        guidance_candidates,
        limit,
    )
    return _finalize_response(response)


def _batch_excerpt_char_limit(query_count: int) -> int:
    """Reserve useful excerpt space across objectives before adding depth."""

    return max(
        _MIN_BATCH_EXCERPT_CHARS,
        min(_MAX_EXCERPT_CHARS, _BATCH_EXCERPT_POOL_CHARS // query_count),
    )


def _load_snapshot(
    repo_root: Path,
    catalog: dict[str, Any],
    sha: str,
) -> list[tuple[dict[str, Any], MarkdownDocument]]:
    paths = [entry["path"] for entry in catalog["entries"]]
    _preflight_pinned_blobs(repo_root, sha, paths)
    return [
        (
            entry,
            parse_markdown_document(_git_show_text(repo_root, sha, entry["path"])),
        )
        for entry in catalog["entries"]
    ]


def _load_repository_guidance(repo_root: Path, sha: str) -> MarkdownDocument:
    """Load non-authoritative repository workflow guidance from the same pin."""

    _preflight_pinned_blobs(repo_root, sha, ["README.md"])
    return parse_markdown_document(_git_show_text(repo_root, sha, "README.md"))


def _search_snapshot(
    sha: str,
    snapshot: list[tuple[dict[str, Any], MarkdownDocument]],
    query: str,
    query_tokens: set[str],
    *,
    excerpt_char_limit: int = _MAX_EXCERPT_CHARS,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    searched_section_count = 0
    for entry, document in snapshot:
        entry_sources = _entry_sources(entry)
        section_rows: list[
            tuple[
                MarkdownSection,
                list[tuple[str, dict[str, Any]]],
                str,
                str,
                str,
                int,
                int,
                int,
                bool,
                list[tuple[str, str, float]],
                float,
            ]
        ] = []
        for section in document.sections:
            if section.level == 1:
                continue
            searched_section_count += 1
            declarations = _matching_declarations(entry, section)
            explicit_ids = {
                row["section_id"]
                for _, row in declarations
                if "section_id" in row
            }
            if explicit_ids:
                section_id = min(explicit_ids)
                section_id_source = "catalog"
            else:
                section_id = _section_id(section.heading)
                section_id_source = "legacy-derived"

            searchable_text = section.text if declarations else section.direct_text
            (
                excerpt,
                start_line,
                end_line,
                end_column_exclusive,
                truncated,
            ) = _bounded_excerpt(
                searchable_text,
                section,
                query_tokens,
                maximum_chars=excerpt_char_limit,
            )
            section_sources = _section_sources(
                section,
                excerpt,
                searchable_text,
                declarations,
                query_tokens,
            )
            section_score, _ = _score_sources(query, query_tokens, section_sources)
            section_rows.append(
                (
                    section,
                    declarations,
                    section_id,
                    section_id_source,
                    excerpt,
                    start_line,
                    end_line,
                    end_column_exclusive,
                    truncated,
                    section_sources,
                    section_score,
                )
            )

        if not section_rows:
            continue
        selected_index = _selected_section_index(entry, section_rows)
        for index, row in enumerate(section_rows):
            (
                section,
                declarations,
                section_id,
                section_id_source,
                excerpt,
                start_line,
                end_line,
                end_column_exclusive,
                truncated,
                section_sources,
                _,
            ) = row
            sources = list(section_sources)
            if index == selected_index:
                sources.extend(entry_sources)
            score, evidence = _score_sources(query, query_tokens, sources)
            if score <= 0:
                continue
            excerpt_bytes = excerpt.encode()
            excerpt_sha256 = hashlib.sha256(excerpt_bytes).hexdigest()
            heading, heading_truncated = _truncate_utf8(
                section.heading,
                _MAX_HEADING_BYTES,
            )
            authority_keys, authority_keys_truncated = _bounded_authority_keys(
                declarations
            )
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
                    "action_authority_eligible": entry[
                        "action_authority_eligible"
                    ],
                    "authority_admission": entry["authority_admission"],
                    "candidate_digest": candidate_digest,
                    "candidate_id_eligible": True,
                    "candidate_kind": "active_catalog_section",
                    "catalog_declared": bool(declarations),
                    "declaration_kinds": sorted({kind for kind, _ in declarations}),
                    "excerpt": excerpt,
                    "excerpt_end_column_exclusive": end_column_exclusive,
                    "excerpt_end_line": end_line,
                    "excerpt_sha256": excerpt_sha256,
                    "excerpt_start_line": start_line,
                    "excerpt_truncated": truncated,
                    "heading": heading,
                    "heading_sha256": hashlib.sha256(
                        section.heading.encode()
                    ).hexdigest(),
                    "heading_truncated": heading_truncated,
                    "heading_line": section.heading_line,
                    "integrity_only": entry["integrity_only"],
                    "integrity_status": entry["integrity_status"],
                    "authority_keys": authority_keys,
                    "authority_keys_truncated": authority_keys_truncated,
                    "last_verified_at": entry["last_verified_at"],
                    "match_evidence": evidence,
                    "owner": entry["owner"],
                    "path": entry["path"],
                    "runbook_id": entry["runbook_id"],
                    "score": round(score, 6),
                    "semantic_verification": entry["semantic_verification"],
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
    candidates = _diversify_candidates(candidates)
    candidates = [
        {**candidate, "rank": rank}
        for rank, candidate in enumerate(candidates, start=1)
    ]
    return {
        "catalog_sha": sha,
        "candidates": candidates,
        "query": query,
        "searched_entry_count": len(snapshot),
        "searched_section_count": searched_section_count,
        "status": (
            "candidates_returned_unverified"
            if candidates
            else "no_positive_candidate_in_active_catalog"
        ),
    }


def _repository_authoring_guidance_candidate(
    sha: str,
    document: MarkdownDocument,
    query: str,
    excerpt_char_limit: int,
) -> dict[str, Any] | None:
    """Return supplemental pinned README context for a local authoring phrase.

    README guidance is deliberately labeled non-authoritative and ineligible for
    a future consultation ID. It closes the cold-start usability gap without
    pretending that a non-ACTIVE document is catalog authority.
    """

    section = next(
        (
            item
            for item in document.sections
            if item.level == 2 and item.heading == _README_AUTHORING_HEADING
        ),
        None,
    )
    if section is None:
        return None
    guidance_intent_tokens = _authoring_intent_tokens(query)
    if not guidance_intent_tokens:
        return None
    raw_query_tokens = {
        token for token in _TOKEN_RE.findall(query.casefold()) if len(token) > 1
    }

    excerpt, start_line, end_line, end_column, truncated = _bounded_excerpt(
        section.text,
        section,
        raw_query_tokens,
        maximum_chars=excerpt_char_limit,
    )
    score, evidence = _score_sources(
        query,
        raw_query_tokens,
        [
            (
                "repository_guidance_intent",
                " ".join(guidance_intent_tokens),
                12.0,
            ),
            ("heading", section.heading, 8.0),
            ("excerpt", excerpt, 2.0),
        ],
    )
    if score <= 0:
        return None
    excerpt_sha256 = hashlib.sha256(excerpt.encode()).hexdigest()
    section_id = _section_id(section.heading)
    candidate_digest = hashlib.sha256(
        "\0".join(
            (sha, "README.md", section_id, str(section.heading_line), excerpt_sha256)
        ).encode()
    ).hexdigest()
    candidate = {
        "action_authority_eligible": False,
        "authority_keys": [],
        "authority_keys_truncated": False,
        "authority_admission": False,
        "candidate_digest": candidate_digest,
        "candidate_id_eligible": False,
        "candidate_kind": "repository_authoring_guidance",
        "catalog_declared": False,
        "declaration_kinds": [],
        "excerpt": excerpt,
        "excerpt_end_column_exclusive": end_column,
        "excerpt_end_line": end_line,
        "excerpt_sha256": excerpt_sha256,
        "excerpt_start_line": start_line,
        "excerpt_truncated": truncated,
        "heading": section.heading,
        "heading_line": section.heading_line,
        "heading_sha256": hashlib.sha256(section.heading.encode()).hexdigest(),
        "heading_truncated": False,
        "integrity_only": True,
        "integrity_status": "integrity_pass_unverified",
        "last_verified_at": None,
        "match_evidence": evidence,
        "owner": None,
        "path": "README.md",
        "rank": None,
        "runbook_id": None,
        "score": round(score, 6),
        "semantic_verification": False,
        "section_id": section_id,
        "section_id_source": "repository-guidance",
        "supplemental": True,
    }
    return candidate


def _authoring_intent_tokens(query: str) -> list[str]:
    """Match one local action→artifact phrase, never cross-clause co-occurrence."""

    for clause in re.split(r"[\n,;:.!?]+", query.casefold()):
        tokens = _TOKEN_RE.findall(clause)
        for artifact_index, artifact in enumerate(tokens):
            if artifact not in _AUTHORING_ARTIFACT_TOKENS:
                continue
            if (
                artifact_index + 1 < len(tokens)
                and tokens[artifact_index + 1]
                in _AUTHORING_ARTIFACT_DISQUALIFIERS
            ):
                continue
            lower_bound = max(0, artifact_index - _MAX_AUTHORING_PHRASE_DISTANCE)
            for action_index in range(artifact_index - 1, lower_bound - 1, -1):
                action = tokens[action_index]
                if action not in _AUTHORING_ACTION_TOKENS:
                    continue
                between = tokens[action_index + 1 : artifact_index]
                if all(token in _AUTHORING_LINK_TOKENS for token in between):
                    return [action, artifact]
    return []


def _refresh_result_status(
    result: dict[str, Any],
) -> None:
    candidates = result["candidates"]
    if any(candidate["candidate_id_eligible"] for candidate in candidates):
        result["status"] = "candidates_returned_unverified"
    elif result["eligible_candidate_count"]:
        result["status"] = "no_usable_candidate_id_response_budget"
    elif candidates:
        result["status"] = "repository_guidance_returned_no_usable_candidate_id"
    else:
        result["status"] = "no_positive_candidate_in_active_catalog"


def _matching_declarations(
    entry: dict[str, Any],
    section: MarkdownSection,
) -> list[tuple[str, dict[str, Any]]]:
    declarations: list[tuple[str, dict[str, Any]]] = []
    for kind, rows in (
        ("topic", entry["authoritative_for"]),
        ("error_signature", entry["error_signatures"]),
    ):
        declarations.extend(
            (kind, row)
            for row in rows
            if _declaration_matches(row, section)
        )
    return declarations


def _declaration_matches(row: dict[str, Any], section: MarkdownSection) -> bool:
    if row["section"] != section.heading:
        return False
    section_id = row.get("section_id")
    return section_id is None or section.adjacent_anchor_id == section_id


def _authority_key(kind: str, row: dict[str, Any]) -> str:
    key = row["topic"] if kind == "topic" else row["signature"]
    return f"{kind}:{key}"


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


def _entry_sources(entry: dict[str, Any]) -> list[tuple[str, str, float]]:
    sources: list[tuple[str, str, float]] = [
        ("runbook_id", entry["runbook_id"].replace("-", " "), 9.0),
        ("path", entry["path"].replace("-", " "), 4.0),
        ("domain", entry["domain"].replace("-", " "), 4.0),
    ]
    sources.extend(
        ("alias", value.replace("-", " "), 9.0) for value in entry["aliases"]
    )
    sources.extend(
        ("topic", row["topic"].replace("-", " "), 8.0)
        for row in entry["authoritative_for"]
    )
    return sources


def _section_sources(
    section: MarkdownSection,
    excerpt: str,
    searchable_text: str,
    declarations: list[tuple[str, dict[str, Any]]],
    query_tokens: set[str],
) -> list[tuple[str, str, float]]:
    sources: list[tuple[str, str, float]] = [
        ("heading", section.heading, 8.0),
        ("excerpt", excerpt, 2.0),
    ]
    for kind, row in declarations:
        if kind == "topic":
            sources.append(("topic", row["topic"].replace("-", " "), 9.0))
        else:
            sources.append(("error_signature", row["signature"], 10.0))
    sources.extend(
        ("structured_literal", literal, 7.0)
        for literal in _structured_literals(searchable_text)
    )
    section_letter = _section_letter(section.heading)
    intent_tokens = _SECTION_INTENTS.get(section_letter or "", frozenset())
    matched_intents = sorted(query_tokens & intent_tokens)
    has_candidate_evidence = any(
        query_tokens & _tokens(value)
        for _, value, _ in sources
    )
    if matched_intents and has_candidate_evidence:
        sources.append(("intent", " ".join(matched_intents), 80.0))
    return sources


def _score_sources(
    query: str,
    query_tokens: set[str],
    sources: list[tuple[str, str, float]],
) -> tuple[float, list[dict[str, Any]]]:
    normalized_query = " ".join(_TOKEN_RE.findall(query.casefold()))
    best_by_kind: dict[str, tuple[float, dict[str, Any]]] = {}
    for kind, value, weight in sources:
        source_tokens = _tokens(value)
        overlap = sorted(query_tokens & source_tokens)
        if not overlap:
            continue
        contribution = (
            weight * len(overlap)
            if kind == "intent"
            else weight * len(overlap) / len(query_tokens)
        )
        normalized_value = " ".join(_TOKEN_RE.findall(value.casefold()))
        if kind != "intent" and len(source_tokens) > 1 and normalized_query and (
            normalized_query in normalized_value or normalized_value in normalized_query
        ):
            contribution += weight
        bounded_tokens = [
            _truncate_utf8(token, _MAX_MATCHED_TOKEN_BYTES)[0]
            for token in overlap[:_MAX_MATCHED_TOKENS]
        ]
        evidence = {
            "kind": kind,
            "matched_tokens": bounded_tokens,
            "matched_tokens_truncated": len(overlap) > len(bounded_tokens),
            "value": _truncate_utf8(value, 240)[0],
            "weight": weight,
        }
        previous = best_by_kind.get(kind)
        candidate_key = (
            contribution,
            len(overlap),
            normalized_value,
        )
        previous_key = (
            previous[0],
            len(previous[1]["matched_tokens"]),
            " ".join(_TOKEN_RE.findall(previous[1]["value"].casefold())),
        ) if previous is not None else None
        if previous_key is None or candidate_key > previous_key:
            best_by_kind[kind] = (contribution, evidence)
    score = sum(value[0] for value in best_by_kind.values())
    evidence = [best_by_kind[kind][1] for kind in sorted(best_by_kind)]
    return score, evidence


def _structured_literals(text: str) -> list[str]:
    literals: set[str] = set()
    for match in re.finditer(r"`([^`\n]{1,240})`", text):
        literals.add(match.group(1).strip())
    for match in re.finditer(
        r"(?m)^[ \t]*(?:tool_or_endpoint|repair_entry_point|action|mode|tool|"
        r"endpoint|verification)[ \t]*:[ \t]*([^\n]{1,240})$",
        text,
    ):
        literals.add(match.group(1).strip())
    return sorted(value for value in literals if value)[:64]


def _section_letter(heading: str) -> str | None:
    match = re.match(r"^§([A-K])(?:\.|\b)", heading)
    return match.group(1) if match is not None else None


def _section_selection_key(row: tuple[Any, ...]) -> tuple[Any, ...]:
    section = row[0]
    section_score = row[-1]
    preferred_order = {"E": 0, "F": 1, "G": 2, "H": 3}
    letter = _section_letter(section.heading)
    return (
        -section_score,
        preferred_order.get(letter or "", 4),
        section.heading_line,
        section.heading,
    )


def _selected_section_index(
    entry: dict[str, Any],
    section_rows: list[tuple[Any, ...]],
) -> int:
    """Choose lexical/intent evidence first, then an honest catalog fallback.

    Entry-wide identity evidence does not itself identify a section. When every
    section has zero evidence, route that evidence to the first declared
    authority instead of manufacturing an operational §E match. This is a
    fallback only: any positive section evidence still wins normally.
    """

    if any(row[-1] > 0 for row in section_rows):
        return min(
            range(len(section_rows)),
            key=lambda index: _section_selection_key(section_rows[index]),
        )

    authorities = entry.get("authoritative_for")
    if isinstance(authorities, list):
        for authority in authorities:
            if not isinstance(authority, dict):
                continue
            for index, row in enumerate(section_rows):
                if _declaration_matches(authority, row[0]):
                    return index

    declared = [
        index for index, row in enumerate(section_rows) if bool(row[1])
    ]
    if declared:
        return min(declared, key=lambda index: section_rows[index][0].heading_line)
    return min(
        range(len(section_rows)),
        key=lambda index: _section_selection_key(section_rows[index]),
    )


def _diversify_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    best: list[dict[str, Any]] = []
    remainder: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        runbook_id = candidate["runbook_id"]
        if runbook_id in seen:
            remainder.append(candidate)
        else:
            seen.add(runbook_id)
            best.append(candidate)
    return best + remainder


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(value.casefold())
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _section_id(heading: str) -> str:
    normalized = heading.casefold().replace("§", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    normalized = normalized or "document"
    if len(normalized.encode()) <= _MAX_SECTION_ID_BYTES:
        return normalized
    suffix = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    prefix, _ = _truncate_utf8(
        normalized,
        _MAX_SECTION_ID_BYTES - len(suffix) - 1,
    )
    return f"{prefix.rstrip('-')}-{suffix}"


def _truncate_utf8(value: str, maximum_bytes: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return value, False
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore"), True


def _bounded_authority_keys(
    declarations: list[tuple[str, dict[str, Any]]],
) -> tuple[list[str], bool]:
    raw = sorted({_authority_key(kind, row) for kind, row in declarations})
    result: list[str] = []
    truncated = len(raw) > _MAX_AUTHORITY_KEYS
    for value in raw[:_MAX_AUTHORITY_KEYS]:
        bounded, was_truncated = _truncate_utf8(value, _MAX_AUTHORITY_KEY_BYTES)
        result.append(bounded)
        truncated = truncated or was_truncated
    return result, truncated


def _bounded_excerpt(
    searchable_text: str,
    section: MarkdownSection,
    query_tokens: set[str],
    *,
    maximum_chars: int = _MAX_EXCERPT_CHARS,
) -> tuple[str, int, int, int, bool]:
    lines = searchable_text.splitlines()
    best_index = 0
    best_overlap = 0
    for index, line in enumerate(lines):
        overlap = len(query_tokens & _tokens(line))
        if overlap > best_overlap:
            best_index = index
            best_overlap = overlap

    excluded_offsets = {
        line_number - section.heading_line
        for line_number in section.excluded_line_numbers
        if section.heading_line <= line_number < section.heading_line + len(lines)
    }
    segment_start = max(
        (offset + 1 for offset in excluded_offsets if offset < best_index),
        default=0,
    )
    segment_end = min(
        (offset for offset in excluded_offsets if offset > best_index),
        default=len(lines),
    )
    start = max(segment_start, best_index - 8)
    if segment_end - start < _MAX_EXCERPT_LINES:
        start = max(segment_start, segment_end - _MAX_EXCERPT_LINES)
    end = min(segment_end, start + _MAX_EXCERPT_LINES)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    excerpt = "\n".join(lines[start:end])
    cropped_by_chars = len(excerpt) > maximum_chars
    if cropped_by_chars:
        excerpt = excerpt[:maximum_chars]
    excerpt_parts = excerpt.split("\n") if excerpt else []
    excerpt_line_count = len(excerpt_parts)
    start_line = section.heading_line + start
    end_line = start_line + max(0, excerpt_line_count - 1)
    end_column_exclusive = len(excerpt_parts[-1]) + 1 if excerpt_parts else 1
    truncated = (
        start > 0
        or end < len(lines)
        or bool(excluded_offsets)
        or cropped_by_chars
    )
    return excerpt, start_line, end_line, end_column_exclusive, truncated


def _finalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["serialized_bytes"] = _response_size_with_digest(result)
    digest_payload = dict(result)
    digest_payload.pop("delivery_digest", None)
    result["delivery_digest"] = hashlib.sha256(
        _canonical_json(digest_payload)
    ).hexdigest()
    wire = _cli_wire_json(result)
    if len(wire.encode()) != result["serialized_bytes"]:
        raise CatalogError("search response serialized byte count is unstable")
    if len(wire.encode()) > _MAX_SERIALIZED_BYTES or len(wire) > _MAX_SERIALIZED_BYTES:
        raise CatalogError("search response exceeds the serialized response budget")
    return result


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _response_size_with_digest(payload: dict[str, Any]) -> int:
    candidate = dict(payload)
    candidate["delivery_digest"] = "0" * 64
    size = -1
    while candidate.get("serialized_bytes") != size:
        candidate["serialized_bytes"] = size
        size = len(_cli_wire_json(candidate).encode())
    return size


def _cli_wire_json(payload: dict[str, Any]) -> str:
    """Match the CLI JSON line encoding exactly."""

    return json.dumps(payload, sort_keys=True) + "\n"


def _sync_result_budget_metadata(
    result: dict[str, Any],
    eligible_pool: list[dict[str, Any]],
    skipped_eligible_digests: set[str],
    guidance_budget_omitted: bool,
) -> int:
    eligible_returned = sum(
        candidate["candidate_id_eligible"] for candidate in result["candidates"]
    )
    guidance_returned = any(
        candidate["candidate_kind"] == "repository_authoring_guidance"
        for candidate in result["candidates"]
    )
    budget_omitted = len(skipped_eligible_digests)
    limit_omitted = max(
        0,
        len(eligible_pool) - eligible_returned - budget_omitted,
    )
    result.update(
        {
            "eligible_candidate_count": len(eligible_pool),
            "eligible_candidates_returned": eligible_returned,
            "eligible_candidates_omitted_by_limit": limit_omitted,
            "eligible_candidates_omitted_by_response_budget": budget_omitted,
            "supplemental_guidance_returned": guidance_returned,
            "supplemental_guidance_omitted_by_response_budget": (
                guidance_budget_omitted
            ),
        }
    )
    _refresh_result_status(result)
    return budget_omitted + int(guidance_budget_omitted)


def _sync_single_budget_metadata(
    response: dict[str, Any],
    eligible_pool: list[dict[str, Any]],
    skipped_eligible_digests: set[str],
    guidance_budget_omitted: bool,
) -> None:
    dropped = _sync_result_budget_metadata(
        response,
        eligible_pool,
        skipped_eligible_digests,
        guidance_budget_omitted,
    )
    response["dropped_candidate_count"] = dropped
    response["response_budget_truncated"] = dropped > 0


def _sync_batch_budget_metadata(
    response: dict[str, Any],
    eligible_pools: list[list[dict[str, Any]]],
    skipped_eligible_digests: list[set[str]],
    guidance_budget_omitted: list[bool],
) -> None:
    dropped = sum(
        _sync_result_budget_metadata(result, pool, skipped, guidance_omitted)
        for result, pool, skipped, guidance_omitted in zip(
            response["results"],
            eligible_pools,
            skipped_eligible_digests,
            guidance_budget_omitted,
            strict=True,
        )
    )
    response["dropped_candidate_count"] = dropped
    response["response_budget_truncated"] = dropped > 0


def _allocate_single_response(
    response: dict[str, Any],
    eligible_pool: list[dict[str, Any]],
    guidance_candidate: dict[str, Any] | None,
    limit: int,
) -> None:
    response["candidates"] = []
    skipped: set[str] = set()
    guidance_omitted = False
    _sync_single_budget_metadata(response, eligible_pool, skipped, False)
    if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
        raise CatalogError("search query exceeds the serialized response budget")

    target = min(len(eligible_pool), limit)
    next_index = 0

    def try_add_one() -> bool:
        nonlocal next_index
        while next_index < len(eligible_pool):
            candidate = eligible_pool[next_index]
            next_index += 1
            response["candidates"].append(candidate)
            _sync_single_budget_metadata(
                response,
                eligible_pool,
                skipped,
                guidance_omitted,
            )
            if _response_size_with_digest(response) <= _MAX_SERIALIZED_BYTES:
                return True
            response["candidates"].pop()
            skipped.add(candidate["candidate_digest"])
            _sync_single_budget_metadata(
                response,
                eligible_pool,
                skipped,
                guidance_omitted,
            )
        return False

    if target:
        try_add_one()
    breadth_complete = target == 0 or response["eligible_candidates_returned"] >= 1
    if guidance_candidate is not None and breadth_complete:
        response["candidates"].append(guidance_candidate)
        _sync_single_budget_metadata(response, eligible_pool, skipped, False)
        if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
            response["candidates"].pop()
            guidance_omitted = True
    elif guidance_candidate is not None:
        guidance_omitted = True
    while breadth_complete and response["eligible_candidates_returned"] < target:
        if not try_add_one():
            break
    _sync_single_budget_metadata(
        response,
        eligible_pool,
        skipped,
        guidance_omitted,
    )
    response["candidates"].sort(
        key=lambda candidate: (
            not candidate["candidate_id_eligible"],
            candidate["rank"] if candidate["rank"] is not None else 0,
        )
    )


def _allocate_batch_response(
    response: dict[str, Any],
    eligible_pools: list[list[dict[str, Any]]],
    guidance_candidates: list[dict[str, Any] | None],
    limit: int,
) -> None:
    skipped: list[set[str]] = [set() for _ in eligible_pools]
    guidance_omitted = [False for _ in guidance_candidates]
    next_indexes = [0 for _ in eligible_pools]
    _sync_batch_budget_metadata(
        response,
        eligible_pools,
        skipped,
        guidance_omitted,
    )
    if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
        raise CatalogError("search queries exceed the global serialized response budget")

    def try_add_one(result_index: int) -> bool:
        result = response["results"][result_index]
        pool = eligible_pools[result_index]
        while next_indexes[result_index] < len(pool):
            candidate = pool[next_indexes[result_index]]
            next_indexes[result_index] += 1
            result["candidates"].append(candidate)
            _sync_batch_budget_metadata(
                response,
                eligible_pools,
                skipped,
                guidance_omitted,
            )
            if _response_size_with_digest(response) <= _MAX_SERIALIZED_BYTES:
                return True
            result["candidates"].pop()
            skipped[result_index].add(candidate["candidate_digest"])
            _sync_batch_budget_metadata(
                response,
                eligible_pools,
                skipped,
                guidance_omitted,
            )
        return False

    # First breadth: one usable ACTIVE candidate for every eligible-positive
    # objective, in objective order, with compact lower ranks available as
    # deterministic substitutes when a larger candidate cannot fit.
    for result_index, pool in enumerate(eligible_pools):
        if pool:
            try_add_one(result_index)

    breadth_complete = all(
        not pool or response["results"][index]["eligible_candidates_returned"] >= 1
        for index, pool in enumerate(eligible_pools)
    )

    # Supplemental README context may use only capacity left after every
    # eligible-positive objective has one usable ACTIVE candidate. It is outside
    # the eligible limit and cannot replace that breadth slot.
    if breadth_complete:
        for index, candidate in enumerate(guidance_candidates):
            if candidate is None:
                continue
            response["results"][index]["candidates"].append(candidate)
            _sync_batch_budget_metadata(
                response,
                eligible_pools,
                skipped,
                guidance_omitted,
            )
            if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
                response["results"][index]["candidates"].pop()
                guidance_omitted[index] = True
    else:
        guidance_omitted = [candidate is not None for candidate in guidance_candidates]

    # Then ACTIVE depth, round-robin, up to the requested eligible limit.
    if breadth_complete:
        while True:
            pending = [
                index
                for index, pool in enumerate(eligible_pools)
                if response["results"][index]["eligible_candidates_returned"]
                < min(len(pool), limit)
            ]
            if not pending:
                break
            progress = False
            for result_index in pending:
                progress = try_add_one(result_index) or progress
            if not progress:
                break
    else:
        # Depth was withheld to protect breadth. Account the next would-be
        # eligible slots as response-budget omissions rather than hiding them as
        # ordinary limit truncation.
        for index, pool in enumerate(eligible_pools):
            missing = min(len(pool), limit) - response["results"][index][
                "eligible_candidates_returned"
            ]
            for candidate in pool[next_indexes[index] : next_indexes[index] + missing]:
                skipped[index].add(candidate["candidate_digest"])

    _sync_batch_budget_metadata(
        response,
        eligible_pools,
        skipped,
        guidance_omitted,
    )
    for result in response["results"]:
        result["candidates"].sort(
            key=lambda candidate: (
                not candidate["candidate_id_eligible"],
                candidate["rank"] if candidate["rank"] is not None else 0,
            )
        )


def _git_show_text(repo_root: Path, sha: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "--no-replace-objects", "show", f"{sha}:{path}"],
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
