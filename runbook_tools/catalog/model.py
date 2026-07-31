from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any

from runbook_tools.frontmatter import CATALOG_METADATA_FIELDS

KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_ACTIVE_FIELDS = CATALOG_METADATA_FIELDS | {"owner_agent"}

MAX_IDENTIFIER_BYTES = 128
MAX_PATH_BYTES = 1024
MAX_OWNER_BYTES = 256
MAX_SECTION_BYTES = 512
MAX_SIGNATURE_BYTES = 1024
MAX_LIST_ITEMS = 64


class CatalogError(ValueError):
    """Raised when catalog source metadata cannot produce one valid catalog."""


def canonical_active_path(runbook_id: str) -> str:
    """Return the sole admitted source path for an ACTIVE catalog member."""

    return f"runbooks/{runbook_id}.md"


@dataclass(frozen=True, slots=True)
class Authority:
    topic: str
    section: str
    section_id: str | None = None

    def as_dict(self) -> dict[str, str]:
        row = {"section": self.section, "topic": self.topic}
        if self.section_id is not None:
            row["section_id"] = self.section_id
        return row


@dataclass(frozen=True, slots=True)
class ErrorSignature:
    signature: str
    section: str
    section_id: str | None = None

    def as_dict(self) -> dict[str, str]:
        row = {"section": self.section, "signature": self.signature}
        if self.section_id is not None:
            row["section_id"] = self.section_id
        return row


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
    integrity_only: bool = True
    integrity_status: str = "integrity_pass_unverified"
    semantic_verification: bool = False
    authority_admission: bool = False
    action_authority_eligible: bool = False

    @classmethod
    def from_frontmatter(
        cls,
        frontmatter: dict[str, Any],
        path: str,
        *,
        latest_verification_date: date | None = None,
    ) -> CatalogEntry:
        _bounded_string(path, f"{path}: path", MAX_PATH_BYTES)
        missing = sorted(REQUIRED_ACTIVE_FIELDS - frontmatter.keys())
        if missing:
            raise CatalogError(f"{path}: missing required ACTIVE fields: {', '.join(missing)}")

        runbook_id = _kebab(frontmatter["runbook_id"], f"{path}: runbook_id")
        expected_path = canonical_active_path(runbook_id)
        if path != expected_path:
            raise CatalogError(
                f"{path}: ACTIVE path must be canonical {expected_path!r}"
            )
        domain = _kebab(frontmatter["domain"], f"{path}: domain")
        if frontmatter["status"] != "ACTIVE":
            raise CatalogError(f"{path}: catalog member status must be ACTIVE")

        authoritative_for = _authority_rows(frontmatter["authoritative_for"], path)
        if not authoritative_for:
            raise CatalogError(f"{path}: authoritative_for must contain at least one row")
        error_signatures = _error_rows(frontmatter["error_signatures"], path)

        owner = _generated_text(
            frontmatter["owner"], f"{path}: owner", MAX_OWNER_BYTES
        )
        owner_agent = _generated_text(
            frontmatter.get("owner_agent"),
            f"{path}: owner_agent",
            MAX_OWNER_BYTES,
        )
        if owner != owner_agent:
            raise CatalogError(
                f"{path}: owner {owner!r} must equal owner_agent {owner_agent!r}"
            )

        raw_date = frontmatter["last_verified_at"]
        last_verified_at = raw_date.isoformat() if isinstance(raw_date, date) else raw_date
        if not isinstance(last_verified_at, str) or DATE_RE.fullmatch(last_verified_at) is None:
            raise CatalogError(f"{path}: last_verified_at must be YYYY-MM-DD")
        try:
            parsed_date = date.fromisoformat(last_verified_at)
        except ValueError as exc:
            raise CatalogError(f"{path}: last_verified_at is not a real date") from exc
        if (
            latest_verification_date is not None
            and parsed_date > latest_verification_date
        ):
            raise CatalogError(
                f"{path}: last_verified_at {last_verified_at} is after "
                f"the verification clock {latest_verification_date.isoformat()}"
            )

        return cls(
            runbook_id=runbook_id,
            domain=domain,
            status="ACTIVE",
            authoritative_for=tuple(
                sorted(
                    authoritative_for,
                    key=lambda row: (row.topic, row.section, row.section_id or ""),
                )
            ),
            aliases=tuple(sorted(_kebab_list(frontmatter["aliases"], f"{path}: aliases"))),
            error_signatures=tuple(
                sorted(
                    error_signatures,
                    key=lambda row: (row.signature, row.section, row.section_id or ""),
                )
            ),
            supersedes=tuple(
                sorted(_kebab_list(frontmatter["supersedes"], f"{path}: supersedes"))
            ),
            superseded_by=tuple(
                sorted(_kebab_list(frontmatter["superseded_by"], f"{path}: superseded_by"))
            ),
            owner=owner,
            last_verified_at=last_verified_at,
            path=path,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_authority_eligible": self.action_authority_eligible,
            "aliases": list(self.aliases),
            "authority_admission": self.authority_admission,
            "authoritative_for": [row.as_dict() for row in self.authoritative_for],
            "domain": self.domain,
            "error_signatures": [row.as_dict() for row in self.error_signatures],
            "integrity_only": self.integrity_only,
            "integrity_status": self.integrity_status,
            "last_verified_at": self.last_verified_at,
            "owner": self.owner,
            "path": self.path,
            "runbook_id": self.runbook_id,
            "semantic_verification": self.semantic_verification,
            "status": self.status,
            "superseded_by": list(self.superseded_by),
            "supersedes": list(self.supersedes),
        }


def _authority_rows(value: Any, path: str) -> list[Authority]:
    _bounded_list(value, f"{path}: authoritative_for")
    rows: list[Authority] = []
    for index, row in enumerate(value):
        label = f"{path}: authoritative_for[{index}]"
        if not isinstance(row, dict) or set(row) not in (
            {"topic", "section"},
            {"topic", "section", "section_id"},
        ):
            raise CatalogError(
                f"{label} must contain exactly topic and section, plus optional section_id"
            )
        section = _generated_text(
            row["section"], f"{label}.section", MAX_SECTION_BYTES
        )
        section_id = (
            _kebab(row["section_id"], f"{label}.section_id")
            if "section_id" in row
            else None
        )
        rows.append(
            Authority(
                topic=_kebab(row["topic"], f"{label}.topic"),
                section=section,
                section_id=section_id,
            )
        )
    _reject_duplicates((row.topic for row in rows), f"{path}: authoritative_for topics")
    return rows


def _error_rows(value: Any, path: str) -> list[ErrorSignature]:
    _bounded_list(value, f"{path}: error_signatures")
    rows: list[ErrorSignature] = []
    for index, row in enumerate(value):
        label = f"{path}: error_signatures[{index}]"
        if not isinstance(row, dict) or set(row) not in (
            {"signature", "section"},
            {"signature", "section", "section_id"},
        ):
            raise CatalogError(
                f"{label} must contain exactly signature and section, plus optional section_id"
            )
        section_id = (
            _kebab(row["section_id"], f"{label}.section_id")
            if "section_id" in row
            else None
        )
        rows.append(
            ErrorSignature(
                signature=_error_signature(row["signature"], f"{label}.signature"),
                section=_generated_text(
                    row["section"], f"{label}.section", MAX_SECTION_BYTES
                ),
                section_id=section_id,
            )
        )
    _reject_duplicates((row.signature for row in rows), f"{path}: error signatures")
    return rows


def _error_signature(value: Any, label: str) -> str:
    return _generated_text(value, label, MAX_SIGNATURE_BYTES)


def _generated_text(value: Any, label: str, maximum_bytes: int) -> str:
    """Admit text that can be rendered into generated Markdown safely."""

    if not isinstance(value, str):
        raise CatalogError(f"{label} must be a non-empty string")
    if "`" in value:
        raise CatalogError(f"{label} must not contain backticks")
    if any(character in "\r\n\u2028\u2029" for character in value):
        raise CatalogError(f"{label} must be single-line")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise CatalogError(f"{label} must not contain control or format characters")
    return _bounded_string(value, label, maximum_bytes)


def _kebab_list(value: Any, label: str) -> list[str]:
    _bounded_list(value, label)
    values = [_kebab(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _reject_duplicates(values, label)
    return values


def _kebab(value: Any, label: str) -> str:
    if not isinstance(value, str) or KEBAB_CASE_RE.fullmatch(value) is None:
        raise CatalogError(f"{label} must be lowercase kebab-case")
    if len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES:
        raise CatalogError(
            f"{label} must not exceed {MAX_IDENTIFIER_BYTES} UTF-8 bytes"
        )
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{label} must be a non-empty string")
    return value.strip()


def _bounded_string(value: Any, label: str, maximum_bytes: int) -> str:
    normalized = _nonempty_string(value, label)
    if len(normalized.encode("utf-8")) > maximum_bytes:
        raise CatalogError(f"{label} must not exceed {maximum_bytes} UTF-8 bytes")
    return normalized


def _bounded_list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise CatalogError(f"{label} must be an array")
    if len(value) > MAX_LIST_ITEMS:
        raise CatalogError(f"{label} must not contain more than {MAX_LIST_ITEMS} items")


def _reject_duplicates(values: Any, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise CatalogError(f"{label} contains duplicate value: {value}")
        seen.add(value)
