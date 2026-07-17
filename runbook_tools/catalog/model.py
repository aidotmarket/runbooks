from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any


KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_ACTIVE_FIELDS = {
    "runbook_id",
    "domain",
    "status",
    "authoritative_for",
    "aliases",
    "error_signatures",
    "supersedes",
    "superseded_by",
    "owner",
    "last_verified_at",
}


class CatalogError(ValueError):
    """Raised when catalog source metadata cannot produce one valid catalog."""


@dataclass(frozen=True, slots=True)
class Authority:
    topic: str
    section: str

    def as_dict(self) -> dict[str, str]:
        return {"section": self.section, "topic": self.topic}


@dataclass(frozen=True, slots=True)
class ErrorSignature:
    signature: str
    section: str

    def as_dict(self) -> dict[str, str]:
        return {"section": self.section, "signature": self.signature}


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    runbook_id: str
    domain: str
    status: str
    authoritative_for: tuple[Authority, ...]
    aliases: tuple[str, ...]
    error_signatures: tuple[ErrorSignature, ...]
    supersedes: tuple[str, ...]
    superseded_by: tuple[str, ...]
    owner: str
    last_verified_at: str
    path: str

    @classmethod
    def from_frontmatter(cls, frontmatter: dict[str, Any], path: str) -> CatalogEntry:
        missing = sorted(REQUIRED_ACTIVE_FIELDS - frontmatter.keys())
        if missing:
            raise CatalogError(f"{path}: missing required ACTIVE fields: {', '.join(missing)}")

        runbook_id = _kebab(frontmatter["runbook_id"], f"{path}: runbook_id")
        domain = _kebab(frontmatter["domain"], f"{path}: domain")
        if frontmatter["status"] != "ACTIVE":
            raise CatalogError(f"{path}: catalog member status must be ACTIVE")

        authoritative_for = _authority_rows(frontmatter["authoritative_for"], path)
        if not authoritative_for:
            raise CatalogError(f"{path}: authoritative_for must contain at least one row")
        error_signatures = _error_rows(frontmatter["error_signatures"], path)

        owner = frontmatter["owner"]
        if not isinstance(owner, str) or not owner.strip():
            raise CatalogError(f"{path}: owner must be a non-empty string")

        raw_date = frontmatter["last_verified_at"]
        last_verified_at = raw_date.isoformat() if isinstance(raw_date, date) else raw_date
        if not isinstance(last_verified_at, str) or DATE_RE.fullmatch(last_verified_at) is None:
            raise CatalogError(f"{path}: last_verified_at must be YYYY-MM-DD")
        try:
            date.fromisoformat(last_verified_at)
        except ValueError as exc:
            raise CatalogError(f"{path}: last_verified_at is not a real date") from exc

        return cls(
            runbook_id=runbook_id,
            domain=domain,
            status="ACTIVE",
            authoritative_for=tuple(sorted(authoritative_for, key=lambda row: (row.topic, row.section))),
            aliases=tuple(sorted(_kebab_list(frontmatter["aliases"], f"{path}: aliases"))),
            error_signatures=tuple(
                sorted(error_signatures, key=lambda row: (row.signature, row.section))
            ),
            supersedes=tuple(
                sorted(_kebab_list(frontmatter["supersedes"], f"{path}: supersedes"))
            ),
            superseded_by=tuple(
                sorted(_kebab_list(frontmatter["superseded_by"], f"{path}: superseded_by"))
            ),
            owner=owner.strip(),
            last_verified_at=last_verified_at,
            path=path,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "aliases": list(self.aliases),
            "authoritative_for": [row.as_dict() for row in self.authoritative_for],
            "domain": self.domain,
            "error_signatures": [row.as_dict() for row in self.error_signatures],
            "last_verified_at": self.last_verified_at,
            "owner": self.owner,
            "path": self.path,
            "runbook_id": self.runbook_id,
            "status": self.status,
            "superseded_by": list(self.superseded_by),
            "supersedes": list(self.supersedes),
        }


def _authority_rows(value: Any, path: str) -> list[Authority]:
    if not isinstance(value, list):
        raise CatalogError(f"{path}: authoritative_for must be an array")
    rows: list[Authority] = []
    for index, row in enumerate(value):
        label = f"{path}: authoritative_for[{index}]"
        if not isinstance(row, dict) or set(row) != {"topic", "section"}:
            raise CatalogError(f"{label} must contain exactly topic and section")
        section = _nonempty_string(row["section"], f"{label}.section")
        rows.append(Authority(topic=_kebab(row["topic"], f"{label}.topic"), section=section))
    _reject_duplicates((row.topic for row in rows), f"{path}: authoritative_for topics")
    return rows


def _error_rows(value: Any, path: str) -> list[ErrorSignature]:
    if not isinstance(value, list):
        raise CatalogError(f"{path}: error_signatures must be an array")
    rows: list[ErrorSignature] = []
    for index, row in enumerate(value):
        label = f"{path}: error_signatures[{index}]"
        if not isinstance(row, dict) or set(row) != {"signature", "section"}:
            raise CatalogError(f"{label} must contain exactly signature and section")
        rows.append(
            ErrorSignature(
                signature=_nonempty_string(row["signature"], f"{label}.signature"),
                section=_nonempty_string(row["section"], f"{label}.section"),
            )
        )
    _reject_duplicates((row.signature for row in rows), f"{path}: error signatures")
    return rows


def _kebab_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise CatalogError(f"{label} must be an array")
    values = [_kebab(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _reject_duplicates(values, label)
    return values


def _kebab(value: Any, label: str) -> str:
    if not isinstance(value, str) or KEBAB_CASE_RE.fullmatch(value) is None:
        raise CatalogError(f"{label} must be lowercase kebab-case")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{label} must be a non-empty string")
    return value.strip()


def _reject_duplicates(values: Any, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise CatalogError(f"{label} contains duplicate value: {value}")
        seen.add(value)
