"""Fail-closed validation for the pinned deployed gateway contract.

The verifier intentionally has no unsigned mode and no optional crypto path.
It accepts only a content-addressed, RFC 8785 canonical JSON envelope signed
with Ed25519 by a currently trusted key.  JSON numbers are serialized with the
ECMAScript formatting thresholds required by RFC 8785; integers remain limited
to I-JSON's exactly interoperable range.

Artifact format version 3 signs each tool's input schema, output schema, and
effect/risk projection plus the one-call runbook lifecycle, one-way cutover,
single-choke-point action evidence, and exact verifier-runtime identities.
There is no legacy lifecycle profile or fallback-valid artifact. Target
readiness proves automatic plan context, caller-runbook-field absence,
backend-observed close evidence, exact-source continuation, complete obligation
pagination, and exact-argument binding for every high-risk mutation without a
caller-supplied receipt.

ACTIVE runbooks can make a checkable current Council assertion with a fenced
block whose info string is ``yaml deployed-contract-roles``::

    contract_digest_sha256: <64 lowercase hex>
    council:
      required_members: [cc, kimi, glm]
      valid_member_ids: [cc, kimi, glm]
      hall:
        valid_agents: [cc, glm, kimi]
        default_agents: [cc, glm, kimi]
    current_roles:
      builders: [mp]
      voters: [cc, kimi, glm]
      paused: [ag]
      retired: [deepseek]

The member sets are compared exactly without assigning semantics to list order.
Current role prose in §C, §D, §E, §H, or §I is reported as an unchecked claim
even when a correct block is also present: the block is the assertion, not a
self-certification of adjacent prose.  The validator never guesses a roster
from prose.
"""

from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import json
import math
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing.exceptions import Unresolvable

from runbook_tools.catalog.generator import _frontmatter
from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.sections import (
    FENCE_CLOSE_RE,
    FENCE_OPEN_RE,
    parse_markdown_document,
)
from runbook_tools.lint.forms import extract_e_entries, extract_i_payload
from runbook_tools.parser.sections import extract_sections
from runbook_tools.strict_yaml import strict_yaml_load

DEFAULT_PIN_PATH = Path("contracts/deployed-tool-contract.pin.json")
DEFAULT_SCHEMA_PATH = Path("schemas/deployed_tool_contract.schema.json")
ROLE_ASSERTION_INFO = ("yaml", "deployed-contract-roles")
CALL_ASSERTION_INFO = ("yaml", "deployed-contract-call")
_SAFE_INTEGER = (1 << 53) - 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_RFC3339_DATETIME_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt]"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
    r"(?:[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)
_TOP_LEVEL_CALL_RE = re.compile(
    r"(?:^|\bthen\s+|\bplus\s+|\+\s*|;\s*)"
    r"([A-Za-z_][A-Za-z0-9_.:-]*)\s*\(([^()]*)\)",
    re.IGNORECASE,
)
_ANY_CALL_RE = re.compile(
    r"(?<![$A-Za-z0-9_.:-])([A-Za-z_][A-Za-z0-9_.:-]*)\s*\(([^()]*)\)"
)
_SCENARIO_ENDPOINT_RE = re.compile(
    r"\btool_or_endpoint:\s*(.+?)(?=(?:\.\s+|\n)(?:argument_sourcing|"
    r"idempotency|expected_success|expected_failures|next_step_success|"
    r"next_step_failure):|$)",
    re.IGNORECASE | re.DOTALL,
)
_ROLE_CLAIM_RE = re.compile(
    r"\b(?:voters?|non-voters?|votes?|voting|builders?|build authority|paused|retired|"
    r"active[ -]gate|gate[ -]members?|required[ -]members?|valid[ -]members?|"
    r"valid[ -]agents?|default[ -]agents?|council[ -]panel|reviewer[ -]panel)\b",
    re.IGNORECASE,
)
_ROLE_CONTEXT_RE = re.compile(
    r"\b(?:council|council roles?|active roster|current roster|agent roster|"
    r"reviewer panel|gate[ -](?:voter|member|panel))\b",
    re.IGNORECASE,
)
_RELEVANT_ROLE_SECTIONS = frozenset("CDEHI")
_REQUIRED_SOURCE_PROJECTIONS = frozenset(
    {
        "tools",
        "council.required_members",
        "council.valid_member_ids",
        "council.hall.valid_agents",
        "council.hall.default_agents",
        "council.current_roles",
        "runbook_lifecycle",
        "action_registry",
        "source_fetch",
        "runtime_lock",
        "cutover",
        "proxy",
    }
)
_HANDLER_SOURCE_PROJECTIONS = _REQUIRED_SOURCE_PROJECTIONS - {"proxy"}
_PIN_KEYS = frozenset(
    {
        "pin_format_version",
        "artifact_path",
        "artifact_sha256",
        "envelope_sha256",
        "handler_sha",
        "proxy_release_identity",
        "policy_revision",
        "issuer",
        "audience",
        "trust_store_path",
        "trust_store_sha256",
    }
)
_TRUST_STORE_KEYS = frozenset({"trust_store_format_version", "keys", "revoked_kids"})
_TRUSTED_KEY_KEYS = frozenset(
    {
        "kid",
        "algorithm",
        "public_key_base64url",
        "issuer",
        "audiences",
        "valid_from",
        "valid_until",
        "revoked_at",
    }
)


@dataclass(frozen=True, slots=True)
class ContractFinding:
    code: str
    message: str
    severity: str = "ERROR"
    path: str | None = None
    line: int | None = None


@dataclass(slots=True)
class ValidationReport:
    findings: list[ContractFinding] = field(default_factory=list)
    contract_digest_sha256: str | None = None
    envelope_sha256: str | None = None
    handler_sha: str | None = None
    proxy_release_identity: str | None = None
    runbook_lifecycle_readiness: str | None = None
    runbook_lifecycle_readiness_reasons: list[ContractFinding] = field(
        default_factory=list
    )
    active_runbooks_checked: int = 0
    tool_calls_checked: int = 0
    role_assertions_checked: int = 0
    unchecked_claims: list[ContractFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(item.severity == "ERROR" for item in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "contract_digest_sha256": self.contract_digest_sha256,
            "envelope_sha256": self.envelope_sha256,
            "handler_sha": self.handler_sha,
            "proxy_release_identity": self.proxy_release_identity,
            "runbook_lifecycle_readiness": self.runbook_lifecycle_readiness,
            "runbook_lifecycle_readiness_reasons": [
                asdict(item) for item in self.runbook_lifecycle_readiness_reasons
            ],
            "active_runbooks_checked": self.active_runbooks_checked,
            "tool_calls_checked": self.tool_calls_checked,
            "role_assertions_checked": self.role_assertions_checked,
            "unchecked_claims": [asdict(item) for item in self.unchecked_claims],
            "findings": [asdict(item) for item in self.findings],
        }


@dataclass(frozen=True, slots=True)
class VerifiedContract:
    artifact: dict[str, Any]
    artifact_digest_sha256: str
    envelope_digest_sha256: str
    tools_by_name: dict[str, dict[str, Any]]
    runbook_lifecycle_readiness: RunbookLifecycleReadiness


@dataclass(frozen=True, slots=True)
class RunbookLifecycleReadiness:
    status: str
    reasons: tuple[ContractFinding, ...] = ()

    @property
    def ready(self) -> bool:
        return self.status == "READY"


class ContractFailure(Exception):
    def __init__(self, code: str, message: str, *, path: str | None = None):
        super().__init__(message)
        self.finding = ContractFinding(code=code, message=message, path=path)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _load_json_bytes(raw: bytes, *, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractFailure("INVALID_UTF8", f"{label} is not UTF-8: {exc}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number {value}")
            ),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ContractFailure(
            "INVALID_JSON", f"{label} is not strict JSON: {exc}"
        ) from exc


def _jcs_string(value: str) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ContractFailure(
            "JCS_INVALID_UNICODE", "JCS input contains a Unicode surrogate"
        )
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _jcs_float(value: float) -> str:
    """Serialize one finite IEEE-754 binary64 using ECMAScript/JCS layout.

    CPython and ECMAScript both choose the shortest round-tripping decimal for
    binary64.  Their presentation thresholds differ, so this function rebuilds
    the RFC 8785 representation from Python's shortest significand.
    """

    if not math.isfinite(value):
        raise ContractFailure("JCS_NONFINITE_NUMBER", "non-finite JSON number")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    rendered = repr(abs(value)).lower()
    mantissa, marker, raw_exponent = rendered.partition("e")
    exponent = int(raw_exponent) if marker else 0
    if "." in mantissa:
        whole, fraction = mantissa.split(".", 1)
    else:
        whole, fraction = mantissa, ""
    digits = (whole + fraction).lstrip("0") or "0"
    decimal_exponent = exponent - len(fraction)
    while len(digits) > 1 and digits.endswith("0"):
        digits = digits[:-1]
        decimal_exponent += 1
    k = len(digits)
    n = k + decimal_exponent
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * (-n) + digits
    else:
        coefficient = digits if k == 1 else digits[0] + "." + digits[1:]
        scientific_exponent = n - 1
        exponent_sign = "+" if scientific_exponent >= 0 else ""
        body = f"{coefficient}e{exponent_sign}{scientific_exponent}"
    return sign + body


def canonical_json(value: Any) -> bytes:
    """Return RFC 8785 bytes for I-JSON values."""

    def encode(item: Any) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, str):
            return _jcs_string(item)
        if isinstance(item, int):
            if abs(item) > _SAFE_INTEGER:
                raise ContractFailure(
                    "JCS_UNSAFE_INTEGER",
                    f"integer {item} is outside the exact IEEE-754 range",
                )
            return str(item)
        if isinstance(item, float):
            return _jcs_float(item)
        if isinstance(item, list):
            return "[" + ",".join(encode(child) for child in item) + "]"
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ContractFailure(
                    "JCS_NONSTRING_KEY", "JSON object keys must be strings"
                )
            # Validate names before UTF-16 sorting so escaped lone surrogates
            # produce a stable contract finding instead of UnicodeEncodeError.
            for key in item:
                _jcs_string(key)
            ordered = sorted(item, key=lambda key: key.encode("utf-16be"))
            return (
                "{"
                + ",".join(f"{_jcs_string(key)}:{encode(item[key])}" for key in ordered)
                + "}"
            )
        raise ContractFailure(
            "JCS_UNSUPPORTED_TYPE", f"unsupported JSON value {type(item).__name__}"
        )

    return encode(value).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_datetime(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, str) or _RFC3339_DATETIME_RE.fullmatch(value) is None:
        raise ContractFailure("INVALID_TIME", f"{field_name} must be an RFC3339 string")
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractFailure(
            "INVALID_TIME", f"{field_name} is not RFC3339: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise ContractFailure("INVALID_TIME", f"{field_name} must include a timezone")
    return parsed.astimezone(UTC)


_CONTRACT_FORMAT_CHECKER = FormatChecker()


@_CONTRACT_FORMAT_CHECKER.checks("date-time")
def _valid_rfc3339_datetime(value: object) -> bool:
    try:
        _parse_datetime(value, field_name="date-time")
    except ContractFailure:
        return False
    return True


def _strict_relative_path(root: Path, value: Any, *, field_name: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ContractFailure(
            "INVALID_PIN_PATH", f"{field_name} must be a non-empty relative path"
        )
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise ContractFailure(
            "INVALID_PIN_PATH", f"{field_name} must be a normalized relative path"
        )
    candidate = root.joinpath(*pure.parts)
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve(strict=False)
    if (
        resolved_candidate != resolved_root
        and resolved_root not in resolved_candidate.parents
    ):
        raise ContractFailure(
            "INVALID_PIN_PATH", f"{field_name} escapes the repository root"
        )
    if candidate.is_symlink():
        raise ContractFailure(
            "INVALID_PIN_PATH", f"{field_name} must not select a symlink"
        )
    return candidate


def _require_exact_keys(
    payload: Any, expected: frozenset[str], *, label: str
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractFailure("INVALID_METADATA", f"{label} must be a JSON object")
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ContractFailure(
            "INVALID_METADATA",
            f"{label} keys differ (missing={missing}, extra={extra})",
        )
    return payload


# RFC 8032 verification, kept local so signature verification has no optional
# dependency or platform-specific fallback.
_ED_Q = 2**255 - 19
_ED_L = 2**252 + 27742317777372353535851937790883648493
_ED_D = (-121665 * pow(121666, _ED_Q - 2, _ED_Q)) % _ED_Q
_ED_I = pow(2, (_ED_Q - 1) // 4, _ED_Q)
_ED_IDENTITY = (0, 1, 1, 0)


def _ed_xrecover(y: int, sign: int) -> int:
    xx = ((y * y - 1) * pow(_ED_D * y * y + 1, _ED_Q - 2, _ED_Q)) % _ED_Q
    x = pow(xx, (_ED_Q + 3) // 8, _ED_Q)
    if (x * x - xx) % _ED_Q:
        x = (x * _ED_I) % _ED_Q
    if (x * x - xx) % _ED_Q:
        raise ValueError("encoded point is not on Ed25519")
    if (x & 1) != sign:
        x = _ED_Q - x
    if x == 0 and sign:
        raise ValueError("non-canonical Ed25519 sign bit")
    return x


def _ed_decode(encoded: bytes) -> tuple[int, int, int, int]:
    if len(encoded) != 32:
        raise ValueError("Ed25519 point must be 32 bytes")
    value = int.from_bytes(encoded, "little")
    sign = value >> 255
    y = value & ((1 << 255) - 1)
    if y >= _ED_Q:
        raise ValueError("non-canonical Ed25519 point")
    x = _ed_xrecover(y, sign)
    return x, y, 1, (x * y) % _ED_Q


def _ed_add(
    left: tuple[int, int, int, int], right: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    x1, y1, z1, t1 = left
    x2, y2, z2, t2 = right
    a = ((y1 - x1) * (y2 - x2)) % _ED_Q
    b = ((y1 + x1) * (y2 + x2)) % _ED_Q
    c = (2 * _ED_D * t1 * t2) % _ED_Q
    d = (2 * z1 * z2) % _ED_Q
    e = b - a
    f = d - c
    g = d + c
    h = b + a
    return (e * f) % _ED_Q, (g * h) % _ED_Q, (f * g) % _ED_Q, (e * h) % _ED_Q


def _ed_double(point: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, z, _ = point
    a = (x * x) % _ED_Q
    b = (y * y) % _ED_Q
    c = (2 * z * z) % _ED_Q
    d = -a
    e = ((x + y) * (x + y) - a - b) % _ED_Q
    g = d + b
    f = g - c
    h = d - b
    return (e * f) % _ED_Q, (g * h) % _ED_Q, (f * g) % _ED_Q, (e * h) % _ED_Q


def _ed_scalar_mult(
    point: tuple[int, int, int, int], scalar: int
) -> tuple[int, int, int, int]:
    result = _ED_IDENTITY
    addend = point
    while scalar:
        if scalar & 1:
            result = _ed_add(result, addend)
        addend = _ed_double(addend)
        scalar >>= 1
    return result


_ED_BASE_Y = (4 * pow(5, _ED_Q - 2, _ED_Q)) % _ED_Q
_ED_BASE = (
    _ed_xrecover(_ED_BASE_Y, 0),
    _ED_BASE_Y,
    1,
    0,
)
_ED_BASE = (_ED_BASE[0], _ED_BASE[1], 1, (_ED_BASE[0] * _ED_BASE[1]) % _ED_Q)


def _ed_equal(
    left: tuple[int, int, int, int], right: tuple[int, int, int, int]
) -> bool:
    return (left[0] * right[2] - right[0] * left[2]) % _ED_Q == 0 and (
        left[1] * right[2] - right[1] * left[2]
    ) % _ED_Q == 0


def verify_ed25519(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Strict Ed25519 verification with canonical point and subgroup checks."""

    if len(public_key) != 32 or len(signature) != 64:
        return False
    try:
        public_point = _ed_decode(public_key)
        r_point = _ed_decode(signature[:32])
    except ValueError:
        return False
    scalar = int.from_bytes(signature[32:], "little")
    if scalar >= _ED_L:
        return False
    if _ed_equal(public_point, _ED_IDENTITY) or _ed_equal(r_point, _ED_IDENTITY):
        return False
    if not _ed_equal(_ed_scalar_mult(public_point, _ED_L), _ED_IDENTITY):
        return False
    if not _ed_equal(_ed_scalar_mult(r_point, _ED_L), _ED_IDENTITY):
        return False
    challenge = (
        int.from_bytes(
            hashlib.sha512(signature[:32] + public_key + message).digest(), "little"
        )
        % _ED_L
    )
    return _ed_equal(
        _ed_scalar_mult(_ED_BASE, scalar),
        _ed_add(r_point, _ed_scalar_mult(public_point, challenge)),
    )


def _decode_base64url(value: Any, *, label: str, expected_length: int) -> bytes:
    if not isinstance(value, str) or "=" in value:
        raise ContractFailure(
            "INVALID_BASE64URL", f"{label} must be unpadded base64url"
        )
    if re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise ContractFailure("INVALID_BASE64URL", f"{label} is not base64url")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise ContractFailure(
            "INVALID_BASE64URL", f"{label} cannot be decoded"
        ) from exc
    if len(decoded) != expected_length:
        raise ContractFailure(
            "INVALID_BASE64URL", f"{label} must decode to {expected_length} bytes"
        )
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    if value != canonical:
        raise ContractFailure(
            "INVALID_BASE64URL",
            f"{label} has non-zero base64url pad bits",
        )
    return decoded


def _validate_pin(payload: Any) -> dict[str, Any]:
    pin = _require_exact_keys(payload, _PIN_KEYS, label="contract pin")
    if pin["pin_format_version"] != "1":
        raise ContractFailure(
            "PIN_VERSION_UNSUPPORTED", "pin_format_version must be '1'"
        )
    for field_name in ("artifact_sha256", "envelope_sha256", "trust_store_sha256"):
        if (
            not isinstance(pin[field_name], str)
            or _SHA256_RE.fullmatch(pin[field_name]) is None
        ):
            raise ContractFailure(
                "INVALID_PIN", f"{field_name} must be a lowercase SHA-256"
            )
    if (
        not isinstance(pin["handler_sha"], str)
        or _GIT_SHA_RE.fullmatch(pin["handler_sha"]) is None
    ):
        raise ContractFailure(
            "INVALID_PIN", "handler_sha must be a full lowercase Git SHA"
        )
    for field_name in (
        "proxy_release_identity",
        "policy_revision",
        "issuer",
        "audience",
    ):
        if not isinstance(pin[field_name], str) or not pin[field_name]:
            raise ContractFailure(
                "INVALID_PIN", f"{field_name} must be a non-empty string"
            )
    return pin


def _validate_trust_store(payload: Any) -> dict[str, Any]:
    store = _require_exact_keys(payload, _TRUST_STORE_KEYS, label="trust store")
    if store["trust_store_format_version"] != "1":
        raise ContractFailure(
            "TRUST_STORE_VERSION_UNSUPPORTED", "trust_store_format_version must be '1'"
        )
    if not isinstance(store["keys"], list) or not store["keys"]:
        raise ContractFailure(
            "INVALID_TRUST_STORE", "trust store keys must be a non-empty list"
        )
    if not isinstance(store["revoked_kids"], list) or not all(
        isinstance(value, str) for value in store["revoked_kids"]
    ):
        raise ContractFailure(
            "INVALID_TRUST_STORE", "revoked_kids must be a string list"
        )
    if len(store["revoked_kids"]) != len(set(store["revoked_kids"])):
        raise ContractFailure("INVALID_TRUST_STORE", "revoked_kids contains duplicates")
    seen: set[str] = set()
    for index, raw_key in enumerate(store["keys"]):
        key = _require_exact_keys(
            raw_key, _TRUSTED_KEY_KEYS, label=f"trusted key {index}"
        )
        kid = key["kid"]
        if not isinstance(kid, str) or not kid or kid in seen:
            raise ContractFailure(
                "INVALID_TRUST_STORE", f"trusted key kid {kid!r} is empty or duplicate"
            )
        seen.add(kid)
        if key["algorithm"] != "Ed25519":
            raise ContractFailure(
                "ALGORITHM_SUBSTITUTION", f"trusted key {kid} is not Ed25519"
            )
        _decode_base64url(
            key["public_key_base64url"], label=f"key {kid}", expected_length=32
        )
        if not isinstance(key["issuer"], str) or not key["issuer"]:
            raise ContractFailure(
                "INVALID_TRUST_STORE", f"trusted key {kid} has no issuer"
            )
        if (
            not isinstance(key["audiences"], list)
            or not key["audiences"]
            or not all(isinstance(value, str) and value for value in key["audiences"])
        ):
            raise ContractFailure(
                "INVALID_TRUST_STORE", f"trusted key {kid} has invalid audiences"
            )
        valid_from = _parse_datetime(
            key["valid_from"], field_name=f"key {kid} valid_from"
        )
        valid_until = _parse_datetime(
            key["valid_until"], field_name=f"key {kid} valid_until"
        )
        if valid_from >= valid_until:
            raise ContractFailure(
                "INVALID_TRUST_STORE", f"trusted key {kid} validity is empty"
            )
        if key["revoked_at"] is not None:
            _parse_datetime(key["revoked_at"], field_name=f"key {kid} revoked_at")
    return store


def _schema_findings(envelope: dict[str, Any], schema_path: Path) -> None:
    try:
        schema = _load_json_bytes(schema_path.read_bytes(), label=str(schema_path))
    except FileNotFoundError as exc:
        raise ContractFailure(
            "CONTRACT_SCHEMA_MISSING", f"contract schema missing: {schema_path}"
        ) from exc
    validator = Draft202012Validator(schema, format_checker=_CONTRACT_FORMAT_CHECKER)
    errors = sorted(
        validator.iter_errors(envelope), key=lambda error: list(error.absolute_path)
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ContractFailure("CONTRACT_SCHEMA_INVALID", f"{location}: {error.message}")


def _tool_property(tool: dict[str, Any], argument: str) -> dict[str, Any]:
    properties = tool["inputSchema"].get("properties", {})
    value = properties.get(argument)
    if not isinstance(value, dict):
        raise ContractFailure(
            "COUNCIL_SCHEMA_MISMATCH",
            f"{tool['name']}.{argument} is absent or not an object schema",
        )
    return value


def _enum_values(
    schema: dict[str, Any], *, array_items: bool = False
) -> list[Any] | None:
    target = schema.get("items") if array_items else schema
    if not isinstance(target, dict):
        return None
    values = target.get("enum")
    return values if isinstance(values, list) else None


def _require_unique_string_list(value: Any, *, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not all(isinstance(item, str) for item in value)
        or len(value) != len(set(value))
    ):
        raise ContractFailure(
            "COUNCIL_SCHEMA_MISMATCH", f"{label} must be a unique string list"
        )
    return value


def _validate_bundled_schema_refs(schema: dict[str, Any], *, tool_name: str) -> None:
    def resolve_fragment(reference: str) -> None:
        if reference == "#":
            return
        if not reference.startswith("#/"):
            raise ContractFailure(
                "EXTERNAL_SCHEMA_REF",
                f"tool {tool_name} contains non-fragment schema reference {reference!r}",
            )
        current: Any = schema
        for raw_part in reference[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif (
                isinstance(current, list)
                and part.isdigit()
                and int(part) < len(current)
            ):
                current = current[int(part)]
            else:
                raise ContractFailure(
                    "UNRESOLVED_SCHEMA_REF",
                    f"tool {tool_name} has unresolved local schema reference {reference!r}",
                )

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"$ref", "$dynamicRef"}:
                    if not isinstance(value, str):
                        raise ContractFailure(
                            "INVALID_TOOL_SCHEMA",
                            f"tool {tool_name} has a non-string {key}",
                        )
                    resolve_fragment(value)
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)


def _schema_property_schema(
    tool: dict[str, Any],
    schema_key: str,
    property_name: str,
    *,
    code: str,
) -> dict[str, Any]:
    schema = tool[schema_key]
    properties = schema.get("properties", {})
    value = properties.get(property_name)
    if not isinstance(value, dict):
        raise ContractFailure(
            code,
            f"{tool['name']}.{schema_key}.{property_name} is absent or not an object schema",
        )
    return value


def _schema_literal_values(schema: dict[str, Any]) -> list[Any]:
    if "const" in schema:
        return [schema["const"]]
    values = schema.get("enum")
    if isinstance(values, list):
        return values
    return []


def _schema_accepts(schema: dict[str, Any], value: Any) -> bool:
    try:
        return Draft202012Validator(
            schema, format_checker=_CONTRACT_FORMAT_CHECKER
        ).is_valid(value)
    except Unresolvable:
        return False


def _require_schema_accepts(
    schema: dict[str, Any], value: Any, *, label: str
) -> None:
    if not _schema_accepts(schema, value):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} does not admit its required typed value",
        )


def _require_exact_const(schema: dict[str, Any], value: Any, *, label: str) -> None:
    if "const" not in schema or type(schema["const"]) is not type(value):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must use the singleton const {value!r}",
        )
    if schema["const"] != value:
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must use the singleton const {value!r}",
        )
    _require_schema_accepts(schema, value, label=label)


def _string_candidates(schema: dict[str, Any], preferred: str) -> list[str]:
    candidates: list[Any] = [schema.get("const")]
    enum = schema.get("enum")
    if isinstance(enum, list):
        candidates.extend(enum)
    candidates.extend(
        (
            preferred,
            "x",
            "selection-1",
            "00000000-0000-4000-8000-000000000000",
            "runbooks/example.md",
            "bounded excerpt",
        )
    )
    return [value for value in candidates if isinstance(value, str) and value]


def _require_nonempty_string(
    schema: dict[str, Any], *, label: str, preferred: str = "x"
) -> str:
    if schema.get("type") != "string" or _schema_accepts(schema, ""):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must admit only non-empty strings",
        )
    for candidate in _string_candidates(schema, preferred):
        if _schema_accepts(schema, candidate):
            return candidate
    raise ContractFailure(
        "LIFECYCLE_SCHEMA_MISMATCH",
        f"{label} has no demonstrably satisfiable non-empty string value",
    )


def _require_sha_string(
    schema: dict[str, Any], *, label: str, length: int
) -> str:
    expected_pattern = f"^[0-9a-f]{{{length}}}$"
    if schema.get("type") != "string" or schema.get("pattern") != expected_pattern:
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must be a {length}-character lowercase hexadecimal string",
        )
    witness = "1" * length
    _require_schema_accepts(schema, witness, label=label)
    return witness


def _require_integer_bounds(
    schema: dict[str, Any], *, label: str, minimum: int, maximum: int | None = None
) -> int:
    declared_minimum = schema.get("minimum")
    if (
        schema.get("type") != "integer"
        or isinstance(declared_minimum, bool)
        or not isinstance(declared_minimum, int | float)
        or declared_minimum < minimum
    ):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must be an integer with minimum >= {minimum}",
        )
    if maximum is not None:
        declared_maximum = schema.get("maximum")
        if (
            isinstance(declared_maximum, bool)
            or not isinstance(declared_maximum, int | float)
            or declared_maximum > maximum
        ):
            raise ContractFailure(
                "LIFECYCLE_SCHEMA_MISMATCH",
                f"{label} must have maximum <= {maximum}",
            )
    start = max(minimum, math.ceil(declared_minimum))
    stop = maximum if maximum is not None else start + 128
    for witness in range(start, min(stop, start + 128) + 1):
        if _schema_accepts(schema, witness):
            return witness
    raise ContractFailure(
        "LIFECYCLE_SCHEMA_MISMATCH",
        f"{label} has no demonstrably satisfiable integer value",
    )


def _require_boolean_schema(schema: dict[str, Any], *, label: str) -> bool:
    if schema.get("type") != "boolean":
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH", f"{label} must be a boolean"
        )
    for witness in (False, True):
        if _schema_accepts(schema, witness):
            return witness
    raise ContractFailure(
        "LIFECYCLE_SCHEMA_MISMATCH", f"{label} has no satisfiable boolean value"
    )


def _require_datetime_string(schema: dict[str, Any], *, label: str) -> str:
    if schema.get("type") != "string" or schema.get("format") != "date-time":
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must be an RFC3339 date-time string",
        )
    witness = "2026-01-01T00:00:00Z"
    _require_schema_accepts(schema, witness, label=label)
    return witness


def _property_is_required_anywhere(schema: Any, property_name: str) -> bool:
    if isinstance(schema, dict):
        required = schema.get("required")
        if isinstance(required, list) and property_name in required:
            return True
        return any(
            _property_is_required_anywhere(value, property_name)
            for value in schema.values()
        )
    if isinstance(schema, list):
        return any(
            _property_is_required_anywhere(value, property_name) for value in schema
        )
    return False


def _require_optional_input_property(tool: dict[str, Any], property_name: str) -> None:
    if _property_is_required_anywhere(tool["inputSchema"], property_name):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{tool['name']}.{property_name} must remain optional for the first-stage call",
        )


def _require_optional_unique_nonempty_string_array(
    tool: dict[str, Any], property_name: str
) -> None:
    schema = _schema_property_schema(
        tool,
        "inputSchema",
        property_name,
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    _require_optional_input_property(tool, property_name)
    items = schema.get("items")
    if (
        schema.get("type") != "array"
        or schema.get("uniqueItems") is not True
        or not isinstance(items, dict)
    ):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{tool['name']}.{property_name} must be an optional unique string array",
        )
    item = _require_nonempty_string(
        items,
        label=f"{tool['name']}.{property_name} item",
    )
    _require_schema_accepts(
        schema,
        [item],
        label=f"{tool['name']}.{property_name}",
    )


def _simple_schema_witness(schema: dict[str, Any], *, label: str) -> Any:
    if "const" in schema and _schema_accepts(schema, schema["const"]):
        return schema["const"]
    enum = schema.get("enum")
    if isinstance(enum, list):
        for value in enum:
            if _schema_accepts(schema, value):
                return value
    schema_type = schema.get("type")
    if schema_type == "string":
        if schema.get("format") == "date-time":
            candidates = ["2026-01-01T00:00:00Z"]
        else:
            candidates = _string_candidates(schema, "x")
        for value in candidates:
            if _schema_accepts(schema, value):
                return value
    elif schema_type == "integer":
        minimum = schema.get("minimum", 0)
        if isinstance(minimum, int | float) and not isinstance(minimum, bool):
            for value in range(math.ceil(minimum), math.ceil(minimum) + 128):
                if _schema_accepts(schema, value):
                    return value
    elif schema_type == "number":
        for value in (0, 1, 0.5):
            if _schema_accepts(schema, value):
                return value
    elif schema_type == "boolean":
        for value in (False, True):
            if _schema_accepts(schema, value):
                return value
    elif schema_type == "null" and _schema_accepts(schema, None):
        return None
    elif schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            count = schema.get("minItems", 0)
            if isinstance(count, int) and 0 <= count <= 8:
                value = [
                    _simple_schema_witness(items, label=f"{label} item")
                    for _ in range(count)
                ]
                if _schema_accepts(schema, value):
                    return value
    elif schema_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if isinstance(properties, dict) and isinstance(required, list):
            value = {
                name: _simple_schema_witness(
                    properties[name], label=f"{label}.{name}"
                )
                for name in required
                if isinstance(properties.get(name), dict)
            }
            if len(value) == len(required) and _schema_accepts(schema, value):
                return value
    raise ContractFailure(
        "LIFECYCLE_SCHEMA_MISMATCH",
        f"{label} has no demonstrably satisfiable typed value",
    )


def _require_satisfiable_object(schema: dict[str, Any], *, label: str) -> dict[str, Any]:
    if schema.get("type") != "object":
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH", f"{label} must be an object"
        )
    value = _simple_schema_witness(schema, label=label)
    if not isinstance(value, dict):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH", f"{label} must admit an object value"
        )
    return value


def _validate_tool_effect(tool: dict[str, Any]) -> None:
    effect = tool["effect"]
    mode = effect["mode"]
    annotations = tool["annotations"]
    read_only_hint = annotations.get("readOnlyHint")
    if read_only_hint is not None:
        expected_hint = effect["default_effect"] == "read_only"
        if not isinstance(read_only_hint, bool) or read_only_hint != expected_hint:
            raise ContractFailure(
                "TOOL_EFFECT_MISMATCH",
                f"tool {tool['name']} readOnlyHint contradicts its default effect",
            )
    if mode != "action_discriminated":
        return
    discriminator = effect["action_discriminator"]
    discriminator_schema = _schema_property_schema(
        tool,
        "inputSchema",
        discriminator,
        code="TOOL_EFFECT_MISMATCH",
    )
    discriminator_values = _enum_values(discriminator_schema)
    if (
        discriminator_schema.get("type") != "string"
        or
        not isinstance(discriminator_values, list)
        or not discriminator_values
        or not all(isinstance(value, str) for value in discriminator_values)
        or len(discriminator_values) != len(set(discriminator_values))
    ):
        raise ContractFailure(
            "TOOL_EFFECT_MISMATCH",
            f"tool {tool['name']} action discriminator must have a unique string enum",
        )
    for value in discriminator_values:
        _require_schema_accepts(
            discriminator_schema,
            value,
            label=f"tool {tool['name']} action discriminator {value!r}",
        )
    action_values = [action["value"] for action in effect["actions"]]
    if len(action_values) != len(set(action_values)):
        raise ContractFailure(
            "TOOL_EFFECT_MISMATCH",
            f"tool {tool['name']} effect actions contain duplicate values",
        )
    if set(action_values) != set(discriminator_values):
        raise ContractFailure(
            "TOOL_EFFECT_MISMATCH",
            f"tool {tool['name']} effect actions must classify every advertised discriminator value exactly once",
        )


def _require_projection_values(
    projection: dict[str, Any],
    expected: dict[str, Any],
    *,
    label: str,
) -> None:
    mismatches = [
        f"{key}={projection.get(key)!r} (expected {value!r})"
        for key, value in expected.items()
        if projection.get(key) != value
    ]
    if mismatches:
        raise ContractFailure(
            "LIFECYCLE_CAPABILITY_MISMATCH",
            f"{label} contradicts its lifecycle profile: " + "; ".join(mismatches),
        )


def _require_mutating_lifecycle_tool(tool: dict[str, Any], *, role: str) -> None:
    effect = tool["effect"]
    if effect["default_effect"] != "mutating":
        raise ContractFailure(
            "LIFECYCLE_CAPABILITY_MISMATCH",
            f"{role} tool {tool['name']} must explicitly declare a mutating effect",
        )


def _require_input_properties(
    tool: dict[str, Any], property_names: Iterable[str]
) -> None:
    for property_name in property_names:
        _schema_property_schema(
            tool,
            "inputSchema",
            property_name,
            code="LIFECYCLE_SCHEMA_MISMATCH",
        )


def _require_absent_input_properties(
    tool: dict[str, Any], property_names: Iterable[str]
) -> None:
    properties = tool["inputSchema"].get("properties", {})
    forbidden = sorted(set(property_names) & set(properties))
    if forbidden:
        raise ContractFailure(
            "LEGACY_LIFECYCLE_SURFACE_PRESENT",
            f"tool {tool['name']} still exposes retired caller fields {forbidden}",
        )


def _require_typed_outcome(
    tool: dict[str, Any], *, discriminator: str, outcome: str, role: str
) -> None:
    schema = tool["outputSchema"]
    discriminator_schema = _schema_property_schema(
        tool,
        "outputSchema",
        discriminator,
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    if discriminator not in schema.get("required", []):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{role} output discriminator {discriminator!r} is not required",
        )
    if (
        discriminator_schema.get("type") != "string"
        or outcome not in _schema_literal_values(discriminator_schema)
        or not _schema_accepts(discriminator_schema, outcome)
    ):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{role} output schema does not expose typed outcome {outcome!r}",
        )


def _require_object_shape(
    schema: dict[str, Any], required_fields: Iterable[str], *, label: str
) -> dict[str, Any]:
    properties = schema.get("properties")
    required = schema.get("required")
    expected = set(required_fields)
    if (
        schema.get("type") != "object"
        or not isinstance(properties, dict)
        or not isinstance(required, list)
        or not expected.issubset(properties)
        or not expected.issubset(required)
    ):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must be an object requiring {sorted(expected)}",
        )
    return properties


def _require_array_item_object_shape(
    schema: dict[str, Any], required_fields: Iterable[str], *, label: str
) -> dict[str, Any]:
    items = schema.get("items")
    if schema.get("type") != "array" or not isinstance(items, dict):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"{label} must be an array with an object item schema",
        )
    return _require_object_shape(items, required_fields, label=f"{label} items")


def _require_true_literal(schema: dict[str, Any], *, label: str) -> None:
    _require_exact_const(schema, True, label=label)


def _require_outcome_payload_binding(
    schema: dict[str, Any],
    *,
    discriminator: str,
    outcome: str,
    payload_property: str,
    label: str,
) -> None:
    branches = schema.get("allOf")
    if not isinstance(branches, list):
        branches = []
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        condition = branch.get("if")
        consequence = branch.get("then")
        if not isinstance(condition, dict) or not isinstance(consequence, dict):
            continue
        condition_properties = condition.get("properties")
        condition_required = condition.get("required")
        consequence_required = consequence.get("required")
        if not isinstance(condition_properties, dict) or not isinstance(
            consequence_required, list
        ):
            continue
        discriminator_schema = condition_properties.get(discriminator)
        allowed_condition_keys = {
            "properties",
            "required",
            "title",
            "description",
            "$comment",
        }
        allowed_literal_keys = {
            "const",
            "type",
            "title",
            "description",
            "$comment",
        }
        if (
            not set(condition).difference(allowed_condition_keys)
            and set(condition_properties) == {discriminator}
            and condition_required == [discriminator]
            and
            isinstance(discriminator_schema, dict)
            and not set(discriminator_schema).difference(allowed_literal_keys)
            and discriminator_schema.get("const") == outcome
            and _schema_accepts(discriminator_schema, outcome)
            and payload_property in consequence_required
        ):
            return
    raise ContractFailure(
        "LIFECYCLE_SCHEMA_MISMATCH",
        f"{label} must conditionally require {payload_property!r} for outcome {outcome!r}",
    )


def _validate_target_plan_result_schema(
    tool: dict[str, Any], plan: dict[str, Any]
) -> None:
    _require_typed_outcome(
        tool,
        discriminator=plan["first_outcome_discriminator"],
        outcome=plan["selection_required_outcome"],
        role="target plan",
    )
    _require_typed_outcome(
        tool,
        discriminator=plan["first_outcome_discriminator"],
        outcome=plan["accepted_outcome"],
        role="target plan acceptance",
    )
    selection_schema = _schema_property_schema(
        tool,
        "outputSchema",
        plan["selection_envelope_property"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    selection_properties = _require_object_shape(
        selection_schema,
        (
            "selection_set_id",
            "catalog_sha",
            "catalog_digest_sha256",
            "complete",
            "exact_byte_count",
            "delivery_digest_sha256",
            "objectives",
        ),
        label="target plan selection envelope",
    )
    selection_set_id = _require_nonempty_string(
        selection_properties["selection_set_id"],
        label="target plan selection-set ID",
        preferred="selection-1",
    )
    catalog_sha = _require_sha_string(
        selection_properties["catalog_sha"],
        label="target plan catalog SHA",
        length=40,
    )
    catalog_digest = _require_sha_string(
        selection_properties["catalog_digest_sha256"],
        label="target plan catalog digest",
        length=64,
    )
    _require_true_literal(
        selection_properties["complete"], label="target plan selection complete"
    )
    exact_byte_count = _require_integer_bounds(
        selection_properties["exact_byte_count"],
        label="target plan exact byte count",
        minimum=0,
        maximum=40_000,
    )
    delivery_digest = _require_sha_string(
        selection_properties["delivery_digest_sha256"],
        label="target plan delivery digest",
        length=64,
    )
    objective_properties = _require_array_item_object_shape(
        selection_properties["objectives"],
        ("objective_index", "candidates", "gap_id"),
        label="target plan objective selections",
    )
    objective_index = _require_integer_bounds(
        objective_properties["objective_index"],
        label="target plan objective index",
        minimum=1,
    )
    candidate_properties = _require_array_item_object_shape(
        objective_properties["candidates"],
        (
            "consultation_id",
            "runbook_id",
            "section_id",
            "path",
            "heading",
            "excerpt",
            "excerpt_digest_sha256",
            "rank",
            "match_evidence",
        ),
        label="target plan candidates",
    )
    candidate_witness = {
        "consultation_id": _require_nonempty_string(
            candidate_properties["consultation_id"],
            label="target plan candidate consultation ID",
            preferred="consultation-1",
        ),
        "runbook_id": _require_nonempty_string(
            candidate_properties["runbook_id"],
            label="target plan candidate runbook ID",
            preferred="runbook-1",
        ),
        "section_id": _require_nonempty_string(
            candidate_properties["section_id"],
            label="target plan candidate section ID",
            preferred="section-e",
        ),
        "path": _require_nonempty_string(
            candidate_properties["path"],
            label="target plan candidate path",
            preferred="runbooks/example.md",
        ),
        "heading": _require_nonempty_string(
            candidate_properties["heading"],
            label="target plan candidate heading",
            preferred="Operate",
        ),
        "excerpt": _require_nonempty_string(
            candidate_properties["excerpt"],
            label="target plan candidate excerpt",
            preferred="bounded excerpt",
        ),
        "excerpt_digest_sha256": _require_sha_string(
            candidate_properties["excerpt_digest_sha256"],
            label="target plan candidate excerpt digest",
            length=64,
        ),
        "rank": _require_integer_bounds(
            candidate_properties["rank"],
            label="target plan candidate rank",
            minimum=1,
        ),
        "match_evidence": _require_satisfiable_object(
            candidate_properties["match_evidence"],
            label="target plan candidate match evidence",
        ),
    }
    _require_schema_accepts(
        objective_properties["candidates"],
        [candidate_witness],
        label="target plan candidate list",
    )
    objective_witness = {
        "objective_index": objective_index,
        "candidates": [candidate_witness],
        "gap_id": _require_nonempty_string(
            objective_properties["gap_id"],
            label="target plan objective gap ID",
            preferred="gap-1",
        ),
    }
    _require_schema_accepts(
        selection_properties["objectives"],
        [objective_witness],
        label="target plan objective selections",
    )
    selection_witness = {
        "selection_set_id": selection_set_id,
        "catalog_sha": catalog_sha,
        "catalog_digest_sha256": catalog_digest,
        "complete": True,
        "exact_byte_count": exact_byte_count,
        "delivery_digest_sha256": delivery_digest,
        "objectives": [objective_witness],
    }
    _require_schema_accepts(
        selection_schema,
        selection_witness,
        label="target plan selection envelope",
    )
    accepted_schema = _schema_property_schema(
        tool,
        "outputSchema",
        plan["accepted_receipt_property"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    accepted_properties = _require_object_shape(
        accepted_schema,
        (
            "plan_revision",
            "session_id",
            "instance",
            "objectives_digest_sha256",
            "work_type",
            "selection_set_id",
            "catalog_sha",
            "request_digest_sha256",
            "delivery_digest_sha256",
        ),
        label="target accepted-plan receipt",
    )
    accepted_witness = {
        "plan_revision": _require_integer_bounds(
            accepted_properties["plan_revision"],
            label="target accepted-plan revision",
            minimum=1,
        ),
        "session_id": _require_nonempty_string(
            accepted_properties["session_id"],
            label="target accepted-plan session ID",
        ),
        "instance": _require_nonempty_string(
            accepted_properties["instance"],
            label="target accepted-plan instance",
        ),
        "objectives_digest_sha256": _require_sha_string(
            accepted_properties["objectives_digest_sha256"],
            label="target accepted-plan objectives digest",
            length=64,
        ),
        "work_type": _require_nonempty_string(
            accepted_properties["work_type"],
            label="target accepted-plan work type",
        ),
        "selection_set_id": _require_nonempty_string(
            accepted_properties["selection_set_id"],
            label="target accepted-plan selection-set ID",
            preferred=selection_set_id,
        ),
        "catalog_sha": _require_sha_string(
            accepted_properties["catalog_sha"],
            label="target accepted-plan catalog SHA",
            length=40,
        ),
        "request_digest_sha256": _require_sha_string(
            accepted_properties["request_digest_sha256"],
            label="target accepted-plan request digest",
            length=64,
        ),
        "delivery_digest_sha256": _require_sha_string(
            accepted_properties["delivery_digest_sha256"],
            label="target accepted-plan delivery digest",
            length=64,
        ),
    }
    _require_schema_accepts(
        accepted_schema,
        accepted_witness,
        label="target accepted-plan receipt",
    )
    output_schema = tool["outputSchema"]
    _require_outcome_payload_binding(
        output_schema,
        discriminator=plan["first_outcome_discriminator"],
        outcome=plan["selection_required_outcome"],
        payload_property=plan["selection_envelope_property"],
        label="target plan selection result",
    )
    _require_outcome_payload_binding(
        output_schema,
        discriminator=plan["first_outcome_discriminator"],
        outcome=plan["accepted_outcome"],
        payload_property=plan["accepted_receipt_property"],
        label="target accepted-plan result",
    )
    _require_schema_accepts(
        output_schema,
        {
            plan["first_outcome_discriminator"]: plan["selection_required_outcome"],
            plan["selection_envelope_property"]: selection_witness,
        },
        label="target plan selection result",
    )
    _require_schema_accepts(
        output_schema,
        {
            plan["first_outcome_discriminator"]: plan["accepted_outcome"],
            plan["accepted_receipt_property"]: accepted_witness,
        },
        label="target accepted-plan result",
    )


def _validate_one_call_plan_result_schema(
    tool: dict[str, Any], plan: dict[str, Any]
) -> None:
    discriminator = plan["first_outcome_discriminator"]
    accepted = plan["accepted_outcome"]
    _require_typed_outcome(
        tool,
        discriminator=discriminator,
        outcome=accepted,
        role="one-call target plan",
    )
    if "RUNBOOK_CONTEXT_SELECTION_REQUIRED" in canonical_json(
        tool["outputSchema"]
    ).decode("utf-8"):
        raise ContractFailure(
            "LEGACY_LIFECYCLE_SURFACE_PRESENT",
            "one-call plan output still advertises the retired selection round trip",
        )

    context_schema = _schema_property_schema(
        tool,
        "outputSchema",
        plan["context_property"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    context_fields = (
        "plan_revision",
        "session_id",
        "instance",
        "request_digest_sha256",
        "activation_sha",
        "catalog_sha",
        "catalog_digest_sha256",
        "manifest_sha256",
        "inventory_sha",
        "search_projection_digest_sha256",
        "complete",
        "exact_byte_count",
        "delivery_digest_sha256",
        "obligations_complete",
        "obligation_subjects_digest_sha256",
        "objectives",
    )
    properties = _require_object_shape(
        context_schema, context_fields, label="one-call runbook context"
    )
    objective_properties = _require_array_item_object_shape(
        properties["objectives"],
        ("objective_index", "objective_digest_sha256", "authoritative_gap", "candidates"),
        label="one-call objective context",
    )
    candidate_properties = _require_array_item_object_shape(
        objective_properties["candidates"],
        (
            "candidate_kind",
            "catalog_state",
            "path",
            "section_id",
            "heading",
            "excerpt",
            "excerpt_digest_sha256",
            "source_blob_oid",
            "rank",
            "match_evidence",
            "guidance_precedence",
        ),
        label="one-call runbook candidates",
    )
    candidate = {
        "candidate_kind": _require_nonempty_string(
            candidate_properties["candidate_kind"],
            label="candidate kind",
            preferred="active_catalog_section",
        ),
        "catalog_state": _require_nonempty_string(
            candidate_properties["catalog_state"],
            label="candidate catalog state",
            preferred="ACTIVE",
        ),
        "path": _require_nonempty_string(
            candidate_properties["path"],
            label="candidate path",
            preferred="runbooks/example.md",
        ),
        "section_id": _require_nonempty_string(
            candidate_properties["section_id"],
            label="candidate section ID",
            preferred="operate",
        ),
        "heading": _require_nonempty_string(
            candidate_properties["heading"],
            label="candidate heading",
            preferred="Operate",
        ),
        "excerpt": _require_nonempty_string(
            candidate_properties["excerpt"],
            label="candidate excerpt",
            preferred="exact bounded excerpt",
        ),
        "excerpt_digest_sha256": _require_sha_string(
            candidate_properties["excerpt_digest_sha256"],
            label="candidate excerpt digest",
            length=64,
        ),
        "source_blob_oid": _require_sha_string(
            candidate_properties["source_blob_oid"],
            label="candidate source blob OID",
            length=40,
        ),
        "rank": _require_integer_bounds(
            candidate_properties["rank"], label="candidate rank", minimum=1
        ),
        "match_evidence": _require_satisfiable_object(
            candidate_properties["match_evidence"],
            label="candidate match evidence",
        ),
        "guidance_precedence": _require_nonempty_string(
            candidate_properties["guidance_precedence"],
            label="candidate guidance precedence",
            preferred="advisory",
        ),
    }
    if candidate["guidance_precedence"] != "advisory":
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            "runbook context candidates must be advisory rather than action authority",
        )
    objective = {
        "objective_index": _require_integer_bounds(
            objective_properties["objective_index"],
            label="objective index",
            minimum=1,
        ),
        "objective_digest_sha256": _require_sha_string(
            objective_properties["objective_digest_sha256"],
            label="objective digest",
            length=64,
        ),
        "authoritative_gap": _require_boolean_schema(
            objective_properties["authoritative_gap"],
            label="objective authoritative gap",
        ),
        "candidates": [candidate],
    }
    _require_schema_accepts(
        properties["objectives"], [objective], label="one-call objectives"
    )

    context = {
        "plan_revision": _require_integer_bounds(
            properties["plan_revision"], label="plan revision", minimum=1
        ),
        "session_id": _require_nonempty_string(
            properties["session_id"], label="plan session ID"
        ),
        "instance": _require_nonempty_string(
            properties["instance"], label="plan instance"
        ),
        "request_digest_sha256": _require_sha_string(
            properties["request_digest_sha256"], label="plan request digest", length=64
        ),
        "activation_sha": _require_sha_string(
            properties["activation_sha"], label="runbooks activation SHA", length=40
        ),
        "catalog_sha": _require_sha_string(
            properties["catalog_sha"], label="catalog SHA", length=40
        ),
        "catalog_digest_sha256": _require_sha_string(
            properties["catalog_digest_sha256"], label="catalog digest", length=64
        ),
        "manifest_sha256": _require_sha_string(
            properties["manifest_sha256"], label="manifest digest", length=64
        ),
        "inventory_sha": _require_sha_string(
            properties["inventory_sha"], label="inventory SHA", length=40
        ),
        "search_projection_digest_sha256": _require_sha_string(
            properties["search_projection_digest_sha256"],
            label="search projection digest",
            length=64,
        ),
        "complete": True,
        "exact_byte_count": _require_integer_bounds(
            properties["exact_byte_count"],
            label="plan exact byte count",
            minimum=0,
            maximum=40_000,
        ),
        "delivery_digest_sha256": _require_sha_string(
            properties["delivery_digest_sha256"], label="delivery digest", length=64
        ),
        "obligations_complete": True,
        "obligation_subjects_digest_sha256": _require_sha_string(
            properties["obligation_subjects_digest_sha256"],
            label="obligation subjects digest",
            length=64,
        ),
        "objectives": [objective],
    }
    _require_true_literal(properties["complete"], label="plan context complete")
    _require_true_literal(
        properties["obligations_complete"], label="obligation pagination complete"
    )
    _require_schema_accepts(context_schema, context, label="one-call runbook context")

    receipt_schema = _schema_property_schema(
        tool,
        "outputSchema",
        plan["accepted_receipt_property"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    receipt_properties = _require_object_shape(
        receipt_schema,
        (
            "status",
            "plan_revision",
            "session_id",
            "instance",
            "request_digest_sha256",
            "context_digest_sha256",
            "activation_sha",
            "committed_at",
            "immutable",
        ),
        label="one-call accepted-plan receipt",
    )
    _require_exact_const(
        receipt_properties["status"], accepted, label="accepted-plan receipt status"
    )
    _require_true_literal(
        receipt_properties["immutable"], label="accepted-plan receipt immutable"
    )
    receipt = {
        "status": accepted,
        "plan_revision": _require_integer_bounds(
            receipt_properties["plan_revision"], label="receipt revision", minimum=1
        ),
        "session_id": _require_nonempty_string(
            receipt_properties["session_id"], label="receipt session ID"
        ),
        "instance": _require_nonempty_string(
            receipt_properties["instance"], label="receipt instance"
        ),
        "request_digest_sha256": _require_sha_string(
            receipt_properties["request_digest_sha256"],
            label="receipt request digest",
            length=64,
        ),
        "context_digest_sha256": _require_sha_string(
            receipt_properties["context_digest_sha256"],
            label="receipt context digest",
            length=64,
        ),
        "activation_sha": _require_sha_string(
            receipt_properties["activation_sha"], label="receipt activation SHA", length=40
        ),
        "committed_at": _require_datetime_string(
            receipt_properties["committed_at"], label="receipt commit time"
        ),
        "immutable": True,
    }
    _require_schema_accepts(
        receipt_schema, receipt, label="one-call accepted-plan receipt"
    )
    for property_name in (plan["context_property"], plan["accepted_receipt_property"]):
        _require_outcome_payload_binding(
            tool["outputSchema"],
            discriminator=discriminator,
            outcome=accepted,
            payload_property=property_name,
            label="one-call accepted plan result",
        )
    _require_schema_accepts(
        tool["outputSchema"],
        {
            discriminator: accepted,
            plan["context_property"]: context,
            plan["accepted_receipt_property"]: receipt,
        },
        label="one-call accepted plan result",
    )


def _validate_exact_source_fetch_tool(tools_by_name: dict[str, dict[str, Any]]) -> None:
    tool = tools_by_name.get("runbook_context_fetch")
    if tool is None:
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            "target contract is missing runbook_context_fetch",
        )
    if tool["effect"]["mode"] != "read_only":
        raise ContractFailure(
            "LIFECYCLE_CAPABILITY_MISMATCH",
            "runbook_context_fetch must be read-only",
        )
    _require_input_properties(
        tool, ("catalog_sha", "source_blob_oid", "path", "unit_kind", "unit_id")
    )
    output = _require_object_shape(
        tool["outputSchema"],
        (
            "complete",
            "catalog_sha",
            "source_blob_oid",
            "path",
            "byte_start",
            "byte_end_exclusive",
            "total_bytes",
            "page_sha256",
            "source_sha256",
            "next_cursor",
            "content",
        ),
        label="exact source fetch output",
    )
    _require_boolean_schema(output["complete"], label="source fetch complete")
    for field_name in ("byte_start", "byte_end_exclusive", "total_bytes"):
        _require_integer_bounds(
            output[field_name], label=f"source fetch {field_name}", minimum=0
        )
    for field_name in ("page_sha256", "source_sha256"):
        _require_sha_string(
            output[field_name], label=f"source fetch {field_name}", length=64
        )
    _require_nonempty_string(output["content"], label="source fetch content")


def _validate_target_close_result_schema(
    tool: dict[str, Any], close: dict[str, Any]
) -> None:
    _require_typed_outcome(
        tool,
        discriminator=close["outcome_discriminator"],
        outcome=close["committed_outcome"],
        role="target close",
    )
    receipt_schema = _schema_property_schema(
        tool,
        "outputSchema",
        close["committed_receipt_property"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    receipt_properties = _require_object_shape(
        receipt_schema,
        (
            "status",
            "transaction_id",
            "close_request_id",
            "request_digest_sha256",
            "session_id",
            "committed_at",
            "immutable",
        ),
        label="target committed-close receipt",
    )
    _require_exact_const(
        receipt_properties["status"],
        close["committed_outcome"],
        label="target close receipt status",
    )
    _require_true_literal(
        receipt_properties["immutable"], label="target close receipt immutable"
    )
    receipt_witness = {
        "status": close["committed_outcome"],
        "transaction_id": _require_nonempty_string(
            receipt_properties["transaction_id"],
            label="target close transaction ID",
        ),
        "close_request_id": _require_nonempty_string(
            receipt_properties["close_request_id"],
            label="target close request ID",
        ),
        "request_digest_sha256": _require_sha_string(
            receipt_properties["request_digest_sha256"],
            label="target close request digest",
            length=64,
        ),
        "session_id": _require_nonempty_string(
            receipt_properties["session_id"],
            label="target close session ID",
        ),
        "committed_at": _require_datetime_string(
            receipt_properties["committed_at"],
            label="target close commit time",
        ),
        "immutable": True,
    }
    _require_schema_accepts(
        receipt_schema,
        receipt_witness,
        label="target committed-close receipt",
    )
    obligations_schema = _schema_property_schema(
        tool,
        "outputSchema",
        close["obligation_outcomes_property"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    obligation_properties = _require_array_item_object_shape(
        obligations_schema,
        ("obligation_id", "status", "occurrence_recorded"),
        label="target close obligation outcomes",
    )
    obligation_status = _require_nonempty_string(
        obligation_properties["status"],
        label="target close obligation status",
        preferred="satisfied",
    )
    status_values = _schema_literal_values(obligation_properties["status"])
    allowed_statuses = {"OPEN", "SATISFIED"}
    if (
        not status_values
        or not all(isinstance(value, str) for value in status_values)
        or not set(status_values).issubset(allowed_statuses)
    ):
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            "target close obligation status must be a typed lifecycle status",
        )
    obligation_witness = {
        "obligation_id": _require_nonempty_string(
            obligation_properties["obligation_id"],
            label="target close obligation ID",
        ),
        "status": obligation_status,
        "occurrence_recorded": _require_boolean_schema(
            obligation_properties["occurrence_recorded"],
            label="target close occurrence-recorded result",
        ),
    }
    _require_schema_accepts(
        obligations_schema,
        [obligation_witness],
        label="target close obligation outcomes",
    )
    output_schema = tool["outputSchema"]
    for payload_property in (
        close["committed_receipt_property"],
        close["obligation_outcomes_property"],
    ):
        _require_outcome_payload_binding(
            output_schema,
            discriminator=close["outcome_discriminator"],
            outcome=close["committed_outcome"],
            payload_property=payload_property,
            label="target committed-close result",
        )
    _require_schema_accepts(
        output_schema,
        {
            close["outcome_discriminator"]: close["committed_outcome"],
            close["committed_receipt_property"]: receipt_witness,
            close["obligation_outcomes_property"]: [obligation_witness],
        },
        label="target committed-close result",
    )


def _validate_action_context_schema(
    tool: dict[str, Any], action_receipts: dict[str, Any]
) -> None:
    receipt_schema = _schema_property_schema(
        tool,
        "inputSchema",
        action_receipts["receipt_argument"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    _require_optional_input_property(tool, action_receipts["receipt_argument"])
    _require_nonempty_string(
        receipt_schema,
        label=f"high-risk tool {tool['name']} action receipt",
        preferred="receipt-1",
    )
    _require_typed_outcome(
        tool,
        discriminator=action_receipts["outcome_discriminator"],
        outcome=action_receipts["context_required_outcome"],
        role=f"high-risk tool {tool['name']}",
    )
    context_schema = _schema_property_schema(
        tool,
        "outputSchema",
        action_receipts["context_property"],
        code="LIFECYCLE_SCHEMA_MISMATCH",
    )
    context_properties = _require_object_shape(
        context_schema,
        (
            "context_id",
            "canonical_arguments_sha256",
            "session_id",
            "component",
            "policy_revision",
            "expires_at",
        ),
        label=f"high-risk tool {tool['name']} action context",
    )
    context_witness = {
        "context_id": _require_nonempty_string(
            context_properties["context_id"],
            label=f"high-risk tool {tool['name']} context ID",
        ),
        "canonical_arguments_sha256": _require_sha_string(
            context_properties["canonical_arguments_sha256"],
            label=f"high-risk tool {tool['name']} canonical-argument digest",
            length=64,
        ),
        "session_id": _require_nonempty_string(
            context_properties["session_id"],
            label=f"high-risk tool {tool['name']} context session ID",
        ),
        "component": _require_nonempty_string(
            context_properties["component"],
            label=f"high-risk tool {tool['name']} context component",
        ),
        "policy_revision": _require_nonempty_string(
            context_properties["policy_revision"],
            label=f"high-risk tool {tool['name']} context policy revision",
        ),
        "expires_at": _require_datetime_string(
            context_properties["expires_at"],
            label=f"high-risk tool {tool['name']} context expiry",
        ),
    }
    _require_schema_accepts(
        context_schema,
        context_witness,
        label=f"high-risk tool {tool['name']} action context",
    )
    _require_outcome_payload_binding(
        tool["outputSchema"],
        discriminator=action_receipts["outcome_discriminator"],
        outcome=action_receipts["context_required_outcome"],
        payload_property=action_receipts["context_property"],
        label=f"high-risk tool {tool['name']} context result",
    )
    _require_schema_accepts(
        tool["outputSchema"],
        {
            action_receipts["outcome_discriminator"]: action_receipts[
                "context_required_outcome"
            ],
            action_receipts["context_property"]: context_witness,
        },
        label=f"high-risk tool {tool['name']} context result",
    )


def _validate_target_action_receipt_bindings(
    tools_by_name: dict[str, dict[str, Any]], action_receipts: dict[str, Any]
) -> None:
    for tool in tools_by_name.values():
        effect = tool["effect"]
        requires_schema = False
        if effect["default_effect"] == "mutating" and effect["default_risk"] == "high":
            if effect["default_receipt_requirement"] != "exact_arguments":
                raise ContractFailure(
                    "LIFECYCLE_CAPABILITY_MISMATCH",
                    f"high-risk default effect for {tool['name']} lacks exact-argument receipt binding",
                )
            requires_schema = True
        elif effect["default_receipt_requirement"] == "exact_arguments":
            requires_schema = True
        for action in effect["actions"]:
            if action["effect"] == "mutating" and action["risk"] == "high":
                if action["receipt_requirement"] != "exact_arguments":
                    raise ContractFailure(
                        "LIFECYCLE_CAPABILITY_MISMATCH",
                        f"high-risk action {tool['name']}.{action['value']} lacks exact-argument receipt binding",
                )
                requires_schema = True
            elif action["receipt_requirement"] == "exact_arguments":
                requires_schema = True
        if requires_schema:
            _validate_action_context_schema(tool, action_receipts)


def _validate_backend_action_evidence_bindings(
    tools_by_name: dict[str, dict[str, Any]]
) -> None:
    for tool in tools_by_name.values():
        _require_absent_input_properties(tool, ("action_receipt", "runbook_refs"))
        output_bytes = canonical_json(tool["outputSchema"])
        if b"ACTION_CONTEXT_REQUIRED" in output_bytes or b'"action_context"' in output_bytes:
            raise ContractFailure(
                "LEGACY_LIFECYCLE_SURFACE_PRESENT",
                f"tool {tool['name']} still exposes the retired caller action-context round trip",
            )
        effect = tool["effect"]
        if (
            effect["default_effect"] == "mutating"
            and effect["default_risk"] == "high"
            and effect["default_receipt_requirement"] != "exact_arguments"
        ):
            raise ContractFailure(
                "LIFECYCLE_CAPABILITY_MISMATCH",
                f"high-risk default effect for {tool['name']} lacks backend exact-argument binding",
            )
        for action in effect["actions"]:
            if (
                action["effect"] == "mutating"
                and action["risk"] == "high"
                and action["receipt_requirement"] != "exact_arguments"
            ):
                raise ContractFailure(
                    "LIFECYCLE_CAPABILITY_MISMATCH",
                    f"high-risk action {tool['name']}.{action['value']} lacks backend exact-argument binding",
                )


def _validate_runbook_lifecycle(
    artifact: dict[str, Any], tools_by_name: dict[str, dict[str, Any]]
) -> None:
    lifecycle = artifact["runbook_lifecycle"]
    profile = lifecycle["profile"]
    plan = lifecycle["plan"]
    close = lifecycle["close"]
    action_evidence = lifecycle["action_evidence"]
    plan_tool = tools_by_name.get(plan["tool_name"])
    close_tool = tools_by_name.get(close["tool_name"])
    if plan_tool is None or close_tool is None:
        missing = plan["tool_name"] if plan_tool is None else close["tool_name"]
        raise ContractFailure(
            "LIFECYCLE_SCHEMA_MISMATCH",
            f"runbook lifecycle names absent tool {missing!r}",
        )
    _require_mutating_lifecycle_tool(plan_tool, role="plan")
    _require_mutating_lifecycle_tool(close_tool, role="close")

    if profile != "runbook_first_v2":
        raise ContractFailure(
            "LEGACY_LIFECYCLE_PROFILE",
            "only the one-way runbook_first_v2 lifecycle is valid",
        )

    _require_projection_values(
        plan,
        {
            "protocol": "server_delivered_one_call",
            "selection_required_outcome": "NONE",
            "accepted_outcome": "PLAN_ACCEPTED",
            "first_outcome_typed": True,
            "first_outcome_semantic_writes": "atomic_after_delivery",
            "binding": "server_bound_session_instance_revision_request_activation_objectives_obligations_context_digest",
            "selection_envelope_property": "NONE",
            "accepted_receipt_property": "accepted_plan_receipt",
            "context_property": "runbook_context",
            "automatic_child_context": True,
            "obligation_subjects": "backend_cursor_complete",
            "exact_source_fetch": "section_and_full_runbook_cursor",
        },
        label="target plan projection",
    )
    _require_projection_values(
        close,
        {
            "protocol": "backend_evidence_atomic_close",
            "committed_outcome": "COMMITTED",
            "receipt": "typed_transaction_scoped_committed",
            "committed_receipt_property": "close_receipt",
            "obligation_outcomes_property": "obligation_outcomes",
            "obligation_transaction": "atomic_backend_transaction_outbox",
            "server_owned_evidence": True,
            "caller_runbook_fields": "absent",
            "semantic_uncertainty": "commit_with_open_obligation",
            "next_action_enforcement": "component_behavior_change_only",
        },
        label="target close projection",
    )
    _require_projection_values(
        action_evidence,
        {
            "protocol": "backend_intent_and_terminal_observation",
            "context_required_outcome": "NONE",
            "outcome_discriminator": "outcome",
            "receipt_argument": "NONE",
            "context_property": "NONE",
            "context_outcome_typed": False,
            "context_outcome_semantic_writes": "backend_transaction",
            "one_use": True,
            "expiring": True,
            "binding": "session_actor_handler_canonical_arguments_component_policy_action_remote_candidate",
        },
        label="target action-receipt projection",
    )
    retired_fields = (
        "runbook_consultation",
        "runbook_refs",
        "consultation_ids",
        "gap_ids",
        "no_entry_found",
        "runbook_impact",
        "runbook_exit",
        "waiver",
        "discharges",
    )
    _require_absent_input_properties(plan_tool, retired_fields)
    _require_absent_input_properties(close_tool, retired_fields)
    _validate_one_call_plan_result_schema(plan_tool, plan)
    _validate_target_close_result_schema(close_tool, close)
    _validate_exact_source_fetch_tool(tools_by_name)
    _validate_backend_action_evidence_bindings(tools_by_name)


def assess_runbook_lifecycle_readiness(
    artifact: dict[str, Any],
) -> RunbookLifecycleReadiness:
    lifecycle = artifact["runbook_lifecycle"]
    reasons: list[ContractFinding] = []
    if lifecycle["profile"] != "runbook_first_v2":
        reasons.append(
            ContractFinding(
                "LEGACY_LIFECYCLE_PROFILE",
                "signed lifecycle projection is not the one-way runbook_first_v2 protocol",
                severity="INFO",
            )
        )
    else:
        delivery = lifecycle["delivery"]
        if delivery["candidate_delivery_mode"] != "required":
            reasons.append(
                ContractFinding(
                    "CANDIDATE_DELIVERY_NOT_REQUIRED",
                    "candidate_delivery_mode is not required",
                    severity="INFO",
                )
            )
        if delivery["legacy_consultation_mode"] != "absent":
            reasons.append(
                ContractFinding(
                    "LEGACY_INPUT_SURFACE_PRESENT",
                    "legacy consultation input is not physically absent",
                    severity="INFO",
                )
            )
        if delivery["candidate_limit"] < 1:
            reasons.append(
                ContractFinding(
                    "CANDIDATE_LIMIT_ZERO",
                    "target delivery has no usable candidate capacity",
                    severity="INFO",
                )
            )
        cutover = lifecycle["cutover"]
        if (
            cutover["state"] != "ACTIVE_ONE_WAY"
            or not cutover["legacy_runtime_absent"]
            or not cutover["local_authority_absent"]
            or not cutover["fallback_absent"]
            or not cutover["database_freeze_verified"]
            or cutover["rollback_mode"] != "new_path_only"
        ):
            reasons.append(
                ContractFinding(
                    "ONE_WAY_CUTOVER_NOT_PROVEN",
                    "signed contract does not prove the legacy runtime, local authority, and fallback are absent",
                    severity="INFO",
                )
            )
    return RunbookLifecycleReadiness(
        status="NOT_READY" if reasons else "READY",
        reasons=tuple(reasons),
    )


def _validate_internal_contract(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tools = artifact["tools"]
    tool_names = [tool["name"] for tool in tools]
    if len(tool_names) != len(set(tool_names)):
        raise ContractFailure(
            "DUPLICATE_TOOL_NAME", "artifact contains duplicate tool names"
        )
    tools_by_name = {tool["name"]: tool for tool in tools}
    for tool in tools:
        for schema_key in ("inputSchema", "outputSchema"):
            schema = tool[schema_key]
            _validate_bundled_schema_refs(
                schema, tool_name=f"{tool['name']}.{schema_key}"
            )
            try:
                Draft202012Validator.check_schema(schema)
            except SchemaError as exc:
                raise ContractFailure(
                    "INVALID_TOOL_SCHEMA",
                    f"tool {tool['name']} has invalid {schema_key}: {exc.message}",
                ) from exc
            properties = schema.get("properties")
            required = schema.get("required", [])
            if not isinstance(properties, dict) or not isinstance(required, list):
                raise ContractFailure(
                    "INVALID_TOOL_SCHEMA",
                    f"tool {tool['name']} has malformed {schema_key} properties/required",
                )
            if len(required) != len(set(required)) or not set(required).issubset(
                properties
            ):
                raise ContractFailure(
                    "INVALID_TOOL_SCHEMA",
                    f"tool {tool['name']} {schema_key} required keys are duplicate or absent from properties",
                )
        _validate_tool_effect(tool)

    expected_schema_digest = _sha256(canonical_json({"tools": tools}))
    if artifact["schema_digest_sha256"] != expected_schema_digest:
        raise ContractFailure(
            "SCHEMA_DIGEST_MISMATCH",
            "schema_digest_sha256 does not match the exact tool descriptors",
        )

    council = artifact["council"]
    roles = council["current_roles"]
    role_lists = {
        name: roles[name] for name in ("builders", "voters", "paused", "retired")
    }
    for left_name, left_values in role_lists.items():
        for right_name, right_values in role_lists.items():
            if left_name < right_name and set(left_values) & set(right_values):
                raise ContractFailure(
                    "ROLE_PROJECTION_CONTRADICTION",
                    f"Council roles {left_name} and {right_name} overlap",
                )
    required_members = set(council["required_members"])
    valid_members = set(council["valid_member_ids"])
    voters = set(roles["voters"])
    if required_members != voters or voters != valid_members:
        raise ContractFailure(
            "ROLE_PROJECTION_CONTRADICTION",
            "Council required_members, current voters, and valid_member_ids must be the same exact set",
        )
    active_members = set(roles["builders"]) | voters
    inactive_members = set(roles["paused"]) | set(roles["retired"])

    dispatch_name = council["dispatch_tool_name"]
    dispatch_tool = tools_by_name.get(dispatch_name)
    if dispatch_tool is None:
        raise ContractFailure(
            "COUNCIL_SCHEMA_MISMATCH",
            f"Council dispatch tool {dispatch_name!r} is absent",
        )
    dispatch_enum = _require_unique_string_list(
        _enum_values(_tool_property(dispatch_tool, council["member_argument"])),
        label="Council dispatch member enum",
    )
    if set(dispatch_enum) != active_members:
        raise ContractFailure(
            "ROLE_PROJECTION_CONTRADICTION",
            "Council dispatch enum must equal active builders plus voters and exclude inactive members",
        )

    hall = council["hall"]
    hall_tool = tools_by_name.get(hall["tool_name"])
    if hall_tool is None:
        raise ContractFailure(
            "COUNCIL_SCHEMA_MISMATCH",
            f"Council Hall tool {hall['tool_name']!r} is absent",
        )
    hall_property = _tool_property(hall_tool, hall["agents_argument"])
    hall_enum = _require_unique_string_list(
        _enum_values(hall_property, array_items=True),
        label="Hall tool agents enum",
    )
    if set(hall_enum) != set(hall["valid_agents"]):
        raise ContractFailure(
            "COUNCIL_SCHEMA_MISMATCH",
            "Hall VALID_AGENTS must equal the Hall tool agents enum as a set",
        )
    if not set(hall["default_agents"]).issubset(hall["valid_agents"]):
        raise ContractFailure(
            "ROLE_PROJECTION_CONTRADICTION",
            "Hall DEFAULT_AGENTS are not a subset of VALID_AGENTS",
        )
    if set(hall["valid_agents"]) != required_members:
        raise ContractFailure(
            "ROLE_PROJECTION_CONTRADICTION",
            "Hall VALID_AGENTS must equal the exact active voter panel",
        )
    if set(hall["default_agents"]) != required_members:
        raise ContractFailure(
            "ROLE_PROJECTION_CONTRADICTION",
            "Hall DEFAULT_AGENTS must equal the exact active voter panel",
        )
    if inactive_members & (set(dispatch_enum) | set(hall["valid_agents"])):
        raise ContractFailure(
            "ROLE_PROJECTION_CONTRADICTION",
            "inactive Council backends remain callable through ordinary dispatch or Hall",
        )
    schema_default = hall_property.get("default")
    if schema_default is not None:
        schema_default = _require_unique_string_list(
            schema_default, label="Hall tool schema default"
        )
        if set(schema_default) != set(hall["default_agents"]):
            raise ContractFailure(
                "COUNCIL_SCHEMA_MISMATCH",
                "Hall tool schema default contradicts DEFAULT_AGENTS",
            )

    runtime_identity = artifact["runtime_identity"]
    runtime_digests = list(runtime_identity.values())
    label_only_digest = hashlib.sha256(
        b"runbook-evidence-verifier-v2-r1"
    ).hexdigest()
    if any(value == "0" * 64 for value in runtime_digests):
        raise ContractFailure(
            "RUNTIME_IDENTITY_PLACEHOLDER",
            "verifier runtime identity contains an all-zero placeholder",
        )
    if runtime_identity["verifier_tree_sha256"] == label_only_digest:
        raise ContractFailure(
            "RUNTIME_IDENTITY_LABEL_ONLY",
            "verifier tree digest hashes a contract label rather than verifier bytes",
        )
    if len(set(runtime_digests)) != len(runtime_digests):
        raise ContractFailure(
            "RUNTIME_IDENTITY_COLLAPSED",
            "independent verifier, manifest, lock, runtime, module-origin, and workflow identities collapsed to repeated labels",
        )

    identifiers = artifact["source_identifiers"]
    projections = [identifier["projection"] for identifier in identifiers]
    if (
        len(projections) != len(set(projections))
        or set(projections) != _REQUIRED_SOURCE_PROJECTIONS
    ):
        raise ContractFailure(
            "SOURCE_PROJECTION_INCOMPLETE",
            "source_identifiers must contain each required projection exactly once",
        )
    for identifier in identifiers:
        if (
            identifier["projection"] in _HANDLER_SOURCE_PROJECTIONS
            and identifier["commit_sha"] != artifact["handler_sha"]
        ):
            raise ContractFailure(
                "SOURCE_PROJECTION_MISMATCH",
                f"{identifier['projection']} source does not name artifact handler_sha",
            )
    _validate_runbook_lifecycle(artifact, tools_by_name)
    return tools_by_name


def verify_pinned_artifact(
    repo_root: Path | str,
    *,
    pin_path: Path | str = DEFAULT_PIN_PATH,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
    now: datetime | None = None,
) -> VerifiedContract:
    """Load and verify one immutable artifact selected by an exact local pin."""

    root = Path(repo_root)
    pin_file = Path(pin_path)
    if not pin_file.is_absolute():
        pin_file = root / pin_file
    try:
        pin = _validate_pin(
            _load_json_bytes(pin_file.read_bytes(), label=str(pin_file))
        )
    except FileNotFoundError as exc:
        raise ContractFailure(
            "CONTRACT_PIN_MISSING", f"deployed contract pin is missing: {pin_file}"
        ) from exc

    artifact_path = _strict_relative_path(
        root, pin["artifact_path"], field_name="artifact_path"
    )
    if artifact_path.name != f"{pin['artifact_sha256']}.json":
        raise ContractFailure(
            "MUTABLE_ARTIFACT_LOOKUP",
            "artifact_path basename must be the pinned artifact_sha256 plus .json",
        )
    trust_path = _strict_relative_path(
        root, pin["trust_store_path"], field_name="trust_store_path"
    )
    try:
        trust_raw = trust_path.read_bytes()
    except FileNotFoundError as exc:
        raise ContractFailure(
            "TRUST_STORE_MISSING", f"trust store is missing: {trust_path}"
        ) from exc
    if _sha256(trust_raw) != pin["trust_store_sha256"]:
        raise ContractFailure(
            "TRUST_STORE_DIGEST_MISMATCH", "trust store bytes do not match the pin"
        )
    trust_store = _validate_trust_store(
        _load_json_bytes(trust_raw, label=str(trust_path))
    )

    try:
        envelope_raw = artifact_path.read_bytes()
    except FileNotFoundError as exc:
        raise ContractFailure(
            "CONTRACT_ARTIFACT_MISSING", f"pinned artifact is missing: {artifact_path}"
        ) from exc
    if _sha256(envelope_raw) != pin["envelope_sha256"]:
        raise ContractFailure(
            "ENVELOPE_DIGEST_MISMATCH", "artifact envelope bytes do not match the pin"
        )
    envelope = _load_json_bytes(envelope_raw, label=str(artifact_path))
    if not isinstance(envelope, dict):
        raise ContractFailure(
            "INVALID_ARTIFACT", "signed artifact envelope must be an object"
        )
    if canonical_json(envelope) != envelope_raw:
        raise ContractFailure(
            "NONCANONICAL_ARTIFACT",
            "signed artifact bytes are not RFC 8785 canonical JSON",
        )

    schema_file = Path(schema_path)
    if not schema_file.is_absolute():
        schema_file = root / schema_file
    _schema_findings(envelope, schema_file)
    artifact = envelope["artifact"]
    metadata = envelope["signature_metadata"]
    artifact_digest = _sha256(canonical_json(artifact))
    if (
        artifact_digest != pin["artifact_sha256"]
        or artifact_digest != metadata["artifact_sha256"]
    ):
        raise ContractFailure(
            "ARTIFACT_DIGEST_MISMATCH",
            "canonical artifact digest does not agree with pin and signature metadata",
        )
    if artifact["handler_sha"] != pin["handler_sha"]:
        raise ContractFailure(
            "HANDLER_SHA_MISMATCH", "artifact handler_sha differs from the exact pin"
        )
    if artifact["proxy_release_identity"] != pin["proxy_release_identity"]:
        raise ContractFailure(
            "PROXY_IDENTITY_MISMATCH",
            "artifact proxy identity differs from the exact pin",
        )
    if artifact["policy_revision"] != pin["policy_revision"]:
        raise ContractFailure(
            "POLICY_REVISION_MISMATCH",
            "artifact policy revision differs from the exact pin",
        )
    if metadata["algorithm"] != "Ed25519":
        raise ContractFailure(
            "ALGORITHM_SUBSTITUTION", "signature algorithm must be Ed25519"
        )
    if metadata["issuer"] != pin["issuer"] or metadata["audience"] != pin["audience"]:
        raise ContractFailure(
            "SIGNATURE_SCOPE_MISMATCH", "signature issuer/audience differ from the pin"
        )

    matching_keys = [
        key for key in trust_store["keys"] if key["kid"] == metadata["kid"]
    ]
    if len(matching_keys) != 1:
        raise ContractFailure(
            "UNKNOWN_SIGNING_KEY",
            f"signing kid {metadata['kid']!r} is not uniquely trusted",
        )
    key = matching_keys[0]
    if metadata["kid"] in trust_store["revoked_kids"] or key["revoked_at"] is not None:
        raise ContractFailure(
            "REVOKED_SIGNING_KEY", f"signing kid {metadata['kid']!r} is revoked"
        )
    if key["algorithm"] != "Ed25519":
        raise ContractFailure(
            "ALGORITHM_SUBSTITUTION", "trusted key algorithm must be Ed25519"
        )
    if (
        key["issuer"] != metadata["issuer"]
        or metadata["audience"] not in key["audiences"]
    ):
        raise ContractFailure(
            "SIGNATURE_SCOPE_MISMATCH", "trusted key does not authorize issuer/audience"
        )
    if (
        metadata["key_valid_from"] != key["valid_from"]
        or metadata["key_valid_until"] != key["valid_until"]
    ):
        raise ContractFailure(
            "KEY_VALIDITY_MISMATCH",
            "envelope key validity metadata differs from trust store",
        )

    supplied_time = now or datetime.now(UTC)
    if supplied_time.tzinfo is None or supplied_time.utcoffset() is None:
        raise ContractFailure(
            "INVALID_TIME", "verification time must include an explicit timezone"
        )
    validation_time = supplied_time.astimezone(UTC)
    valid_from = _parse_datetime(key["valid_from"], field_name="key valid_from")
    valid_until = _parse_datetime(key["valid_until"], field_name="key valid_until")
    issued_at = _parse_datetime(metadata["issued_at"], field_name="signature issued_at")
    if not (valid_from <= issued_at < valid_until):
        raise ContractFailure(
            "SIGNATURE_TIME_INVALID", "signature issued_at is outside key validity"
        )
    if not (valid_from <= validation_time < valid_until):
        raise ContractFailure(
            "SIGNING_KEY_EXPIRED", "signing key is not valid at the verification time"
        )
    if issued_at > validation_time:
        raise ContractFailure(
            "SIGNATURE_TIME_INVALID", "signature issued_at is in the future"
        )

    public_key = _decode_base64url(
        key["public_key_base64url"], label=f"key {key['kid']}", expected_length=32
    )
    signature = _decode_base64url(
        envelope["signature"], label="signature", expected_length=64
    )
    signed_bytes = canonical_json(
        {"artifact": artifact, "signature_metadata": metadata}
    )
    if not verify_ed25519(public_key, signed_bytes, signature):
        raise ContractFailure(
            "SIGNATURE_INVALID", "Ed25519 signature verification failed"
        )

    tools_by_name = _validate_internal_contract(artifact)
    return VerifiedContract(
        artifact=artifact,
        artifact_digest_sha256=artifact_digest,
        envelope_digest_sha256=_sha256(envelope_raw),
        tools_by_name=tools_by_name,
        runbook_lifecycle_readiness=assess_runbook_lifecycle_readiness(artifact),
    )


def _split_arguments(raw: str) -> list[str]:
    if not raw.strip():
        return []
    parts: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    angle_depth = 0
    square_depth = 0
    brace_depth = 0
    for index, character in enumerate(raw):
        if escaped:
            escaped = False
            continue
        if quote is not None:
            if character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in ("'", '"'):
            quote = character
        elif character == "<":
            angle_depth += 1
        elif character == ">" and angle_depth:
            angle_depth -= 1
        elif character == "[":
            square_depth += 1
        elif character == "]" and square_depth:
            square_depth -= 1
        elif character == "{":
            brace_depth += 1
        elif character == "}" and brace_depth:
            brace_depth -= 1
        elif (
            character == ","
            and angle_depth == 0
            and square_depth == 0
            and brace_depth == 0
        ):
            parts.append(raw[start:index].strip())
            start = index + 1
    if quote is not None or angle_depth or square_depth or brace_depth:
        raise ValueError("unclosed quote, placeholder, array, or object")
    parts.append(raw[start:].strip())
    return parts


def _parse_literal(raw: str) -> tuple[Any, bool]:
    value = raw.strip()
    if value in {"...", "…"} or (value.startswith("<") and value.endswith(">")):
        return value, True
    if value.startswith("${") and value.endswith("}"):
        return value, True
    lowered = value.casefold()
    if lowered == "true":
        return True, False
    if lowered == "false":
        return False, False
    if lowered in {"null", "none"}:
        return None, False
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        return int(value), False
    if re.fullmatch(
        r"-?(?:(?:0|[1-9][0-9]*)\.[0-9]+|(?:0|[1-9][0-9]*)(?:[eE][+-]?[0-9]+)|"
        r"(?:0|[1-9][0-9]*)\.[0-9]+(?:[eE][+-]?[0-9]+))",
        value,
    ):
        parsed_float = float(value)
        if not math.isfinite(parsed_float):
            raise ValueError("non-finite numeric literal")
        return parsed_float, False
    if (value.startswith("[") and value.endswith("]")) or (
        value.startswith("{") and value.endswith("}")
    ):
        try:
            parsed_container = json.loads(
                value, object_pairs_hook=_reject_duplicate_keys
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid JSON container literal: {exc}") from exc
        return parsed_container, False
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value, False
        return parsed, False
    return value, False


def _is_placeholder_value(value: Any) -> bool:
    return isinstance(value, str) and (
        value in {"...", "…"}
        or (value.startswith("<") and value.endswith(">"))
        or (value.startswith("${") and value.endswith("}"))
    )


def _parse_call_arguments(raw: str) -> tuple[list[str], dict[str, Any], set[str]]:
    keys: list[str] = []
    values: dict[str, Any] = {}
    placeholders: set[str] = set()
    for part in _split_arguments(raw):
        if not part or "=" not in part:
            raise ValueError(f"argument {part!r} is not key=value")
        key, raw_value = part.split("=", 1)
        key = key.strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None or key in keys:
            raise ValueError(f"argument key {key!r} is invalid or duplicate")
        value, placeholder = _parse_literal(raw_value)
        keys.append(key)
        values[key] = value
        if placeholder:
            placeholders.add(key)
    return keys, values, placeholders


def _endpoint_call_specs(
    endpoint: str,
    contract: VerifiedContract,
    *,
    path: str,
    line: int | None,
    context: str,
) -> tuple[list[tuple[str, str]], list[ContractFinding], bool]:
    """Parse calls only at endpoint-composition boundaries.

    This deliberately ignores SQL functions and shell substitutions embedded
    in external command text.  Unknown names at an actual top-level call
    boundary remain errors.  ``external::`` is the explicit no-gateway shape.
    """

    stripped = endpoint.strip()
    classification = "implicit"
    if stripped.startswith("external::"):
        classification = "external"
        external_body = stripped.removeprefix("external::").strip()
        findings: list[ContractFinding] = []
        if not external_body:
            findings.append(
                ContractFinding(
                    "EMPTY_ENDPOINT_CLASSIFICATION",
                    f"{context} external:: endpoint is empty",
                    path=path,
                    line=line,
                )
            )
        known_mentions = sorted(
            tool_name
            for tool_name in contract.tools_by_name
            if re.search(
                rf"(?<![A-Za-z0-9_.:-]){re.escape(tool_name)}(?![A-Za-z0-9_.:-])",
                external_body,
            )
        )
        if known_mentions:
            findings.append(
                ContractFinding(
                    "ENDPOINT_CLASSIFICATION_CONTRADICTION",
                    f"{context} classifies deployed gateway calls {known_mentions} as external",
                    path=path,
                    line=line,
                )
            )
        return [], findings, True
    for prefix in ("gateway::", "mixed::"):
        if stripped.startswith(prefix):
            classification = prefix.removesuffix("::")
            stripped = stripped.removeprefix(prefix).strip()
            break
    matches = list(_TOP_LEVEL_CALL_RE.finditer(stripped))
    specs = [(match.group(1), match.group(2)) for match in matches]
    findings: list[ContractFinding] = []
    if classification in {"gateway", "mixed"} and not specs:
        findings.append(
            ContractFinding(
                "MALFORMED_ENDPOINT_CLASSIFICATION",
                f"{context} {classification}:: endpoint contains no structured gateway call",
                path=path,
                line=line,
            )
        )
    if classification == "mixed" and specs:
        remainder = stripped
        for match in reversed(matches):
            remainder = remainder[: match.start()] + " " + remainder[match.end() :]
        remainder = re.sub(r"\b(?:then|plus)\b|[+;]", " ", remainder).strip()
        if not remainder:
            findings.append(
                ContractFinding(
                    "MALFORMED_ENDPOINT_CLASSIFICATION",
                    f"{context} mixed:: endpoint contains no external portion",
                    path=path,
                    line=line,
                )
            )
    top_level_names = {name for name, _ in specs}
    hidden_known = sorted(
        {
            match.group(1)
            for match in _ANY_CALL_RE.finditer(stripped)
            if match.group(1) in contract.tools_by_name
            and match.group(1) not in top_level_names
        }
    )
    if hidden_known:
        findings.append(
            ContractFinding(
                "MALFORMED_TOOL_CALL",
                f"{context} mentions deployed tools outside the top-level endpoint grammar: {hidden_known}",
                path=path,
                line=line,
            )
        )
    return specs, findings, classification == "external"


def _property_schema(root_schema: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = root_schema.get("properties", {}).get(key)
    return value if isinstance(value, dict) else None


def _schema_property_names(node: Any) -> set[str]:
    if not isinstance(node, dict):
        return set()
    names: set[str] = set()
    properties = node.get("properties")
    if isinstance(properties, dict):
        names.update(key for key in properties if isinstance(key, str))
    required = node.get("required")
    if isinstance(required, list):
        names.update(key for key in required if isinstance(key, str))
    for keyword in ("allOf", "anyOf", "oneOf"):
        branches = node.get(keyword)
        if isinstance(branches, list):
            for branch in branches:
                names.update(_schema_property_names(branch))
    for keyword in ("not", "if", "then", "else"):
        names.update(_schema_property_names(node.get(keyword)))
    return names


def _conditional_value_keys(root_schema: dict[str, Any]) -> set[str]:
    """Return top-level values that must be literal to select schema branches."""

    sensitive: set[str] = set()

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        condition = node.get("if")
        if isinstance(condition, dict):
            sensitive.update(_schema_property_names(condition))
            visit(node.get("then"))
            visit(node.get("else"))
        for keyword in ("oneOf", "anyOf"):
            branches = node.get(keyword)
            if isinstance(branches, list):
                property_occurrences: dict[str, list[Any]] = {}
                for branch in branches:
                    if isinstance(branch, dict) and isinstance(
                        branch.get("properties"), dict
                    ):
                        for key, property_schema in branch["properties"].items():
                            if not isinstance(key, str):
                                continue
                            property_occurrences.setdefault(key, []).append(
                                property_schema
                            )
                            if isinstance(property_schema, dict) and (
                                "const" in property_schema or "enum" in property_schema
                            ):
                                sensitive.add(key)
                    visit(branch)
                for key, schemas in property_occurrences.items():
                    if len(schemas) < 2:
                        continue
                    rendered = {repr(schema) for schema in schemas}
                    if len(rendered) > 1:
                        sensitive.add(key)
        negated = node.get("not")
        if isinstance(negated, dict):
            sensitive.update(_schema_property_names(negated))
        dependent_schemas = node.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for dependent in dependent_schemas.values():
                sensitive.update(_schema_property_names(dependent))
                visit(dependent)
        branches = node.get("allOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

    visit(root_schema)
    return sensitive


def _relax_deferred_argument_values(
    root_schema: dict[str, Any], deferred: set[str]
) -> dict[str, Any]:
    """Relax deferred leaf values while retaining object/branch structure."""

    relaxed = copy.deepcopy(root_schema)

    def visit_object_schema(node: Any) -> None:
        if not isinstance(node, dict):
            return
        properties = node.get("properties")
        if isinstance(properties, dict):
            for key in deferred:
                if key in properties:
                    properties[key] = {}
        for keyword in ("allOf", "anyOf", "oneOf"):
            branches = node.get(keyword)
            if isinstance(branches, list):
                for branch in branches:
                    visit_object_schema(branch)
        for keyword in ("if", "then", "else", "not"):
            visit_object_schema(node.get(keyword))
        dependent_schemas = node.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for dependent in dependent_schemas.values():
                visit_object_schema(dependent)

    visit_object_schema(relaxed)
    return relaxed


def _walk_schema_errors(errors: Iterable[Any]) -> Iterable[Any]:
    for error in errors:
        yield error
        yield from _walk_schema_errors(error.context)


def _validate_argument_shape(
    *,
    tool: dict[str, Any],
    argument_keys: Sequence[str],
    argument_values: dict[str, Any],
    placeholders: set[str],
    path: str,
    line: int | None,
    context: str,
) -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    schema = tool["inputSchema"]
    properties = schema.get("properties", {})
    keys = list(argument_keys)
    if not all(
        isinstance(key, str)
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is not None
        for key in keys
    ) or len(keys) != len(set(keys)):
        findings.append(
            ContractFinding(
                "DUPLICATE_ARGUMENT_KEY",
                f"{context} has a non-identifier or duplicate argument key",
                path=path,
                line=line,
            )
        )
        return findings
    if not all(
        isinstance(key, str)
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is not None
        for key in argument_values
    ):
        findings.append(
            ContractFinding(
                "MALFORMED_ARGUMENT_VALUES",
                f"{context} argument_values keys must be string identifiers",
                path=path,
                line=line,
            )
        )
        return findings
    unknown = sorted(set(keys) - set(properties))
    if unknown:
        findings.append(
            ContractFinding(
                "UNKNOWN_ARGUMENT_KEY",
                f"{context} uses unknown argument keys {unknown}",
                path=path,
                line=line,
            )
        )
    value_without_key = sorted(set(argument_values) - set(keys))
    if value_without_key:
        findings.append(
            ContractFinding(
                "ARGUMENT_VALUE_WITHOUT_KEY",
                f"{context} supplies values for unrepresented keys {value_without_key}",
                path=path,
                line=line,
            )
        )
    base_required = set(schema.get("required", []))
    base_missing = sorted(base_required - set(keys))
    if base_missing:
        findings.append(
            ContractFinding(
                "MISSING_REQUIRED_ARGUMENT",
                f"{context} omits required argument keys {base_missing}",
                path=path,
                line=line,
            )
        )
    for key, value in argument_values.items():
        if key not in properties or key in placeholders:
            continue
        property_schema = _property_schema(schema, key)
        if property_schema is None:
            continue
        try:
            errors = list(
                Draft202012Validator(schema)
                .evolve(schema=property_schema)
                .iter_errors(value)
            )
        except Unresolvable as exc:
            findings.append(
                ContractFinding(
                    "SCHEMA_RESOLUTION_FAILURE",
                    f"{context} could not resolve {key!r} in the bundled schema: {exc}",
                    path=path,
                    line=line,
                )
            )
            continue
        if errors:
            findings.append(
                ContractFinding(
                    "LITERAL_ARGUMENT_REJECTED",
                    f"{context} literal {key}={value!r} is rejected: {errors[0].message}",
                    path=path,
                    line=line,
                )
            )
    if unknown or value_without_key:
        return findings

    deferred = (set(keys) - set(argument_values)) | set(placeholders)
    sensitive_deferred = sorted(deferred & _conditional_value_keys(schema))
    if sensitive_deferred:
        findings.append(
            ContractFinding(
                "CONDITIONAL_ARGUMENT_PLACEHOLDER",
                f"{context} must provide literal branch-selecting values for {sensitive_deferred}",
                path=path,
                line=line,
            )
        )
        return findings

    instance = {
        key: argument_values[key] if key not in deferred else None for key in keys
    }
    relaxed_schema = _relax_deferred_argument_values(schema, deferred)
    try:
        full_errors = list(Draft202012Validator(relaxed_schema).iter_errors(instance))
    except Unresolvable as exc:
        findings.append(
            ContractFinding(
                "SCHEMA_RESOLUTION_FAILURE",
                f"{context} could not resolve the bundled input schema: {exc}",
                path=path,
                line=line,
            )
        )
        return findings
    if not full_errors:
        return findings
    missing_from_branches: set[str] = set()
    for error in _walk_schema_errors(full_errors):
        if error.validator == "required" and not error.absolute_path:
            required_values = error.validator_value
            if isinstance(required_values, list):
                missing_from_branches.update(
                    value for value in required_values if value not in instance
                )
        elif error.validator == "dependentRequired" and not error.absolute_path:
            dependencies = error.validator_value
            if isinstance(dependencies, dict):
                for trigger, required_values in dependencies.items():
                    if trigger in instance and isinstance(required_values, list):
                        missing_from_branches.update(
                            value for value in required_values if value not in instance
                        )
    missing_from_branches -= set(base_missing)
    if missing_from_branches:
        findings.append(
            ContractFinding(
                "MISSING_REQUIRED_ARGUMENT",
                f"{context} omits conditionally required argument keys {sorted(missing_from_branches)}",
                path=path,
                line=line,
            )
        )
    remaining = [
        error
        for error in full_errors
        if not (
            error.validator in {"required", "dependentRequired"}
            and missing_from_branches
        )
    ]
    if remaining and not missing_from_branches:
        findings.append(
            ContractFinding(
                "ARGUMENT_COMBINATION_REJECTED",
                f"{context} arguments are rejected by the exact input schema: {remaining[0].message}",
                path=path,
                line=line,
            )
        )
    return findings


def _validate_named_call(
    *,
    contract: VerifiedContract,
    tool_name: str,
    argument_keys: Sequence[str],
    argument_values: dict[str, Any],
    placeholders: set[str],
    path: str,
    line: int | None,
    context: str,
) -> tuple[list[ContractFinding], int]:
    tool = contract.tools_by_name.get(tool_name)
    if tool is None:
        return [
            ContractFinding(
                "UNKNOWN_TOOL",
                f"{context} names {tool_name!r}, which is absent from the deployed contract",
                path=path,
                line=line,
            )
        ], 0
    return (
        _validate_argument_shape(
            tool=tool,
            argument_keys=argument_keys,
            argument_values=argument_values,
            placeholders=placeholders,
            path=path,
            line=line,
            context=context,
        ),
        1,
    )


def _validate_endpoint_text(
    *,
    endpoint: str,
    contract: VerifiedContract,
    path: str,
    line: int | None,
    context: str,
) -> tuple[list[ContractFinding], list[ContractFinding], int]:
    specs, findings, explicitly_external = _endpoint_call_specs(
        endpoint, contract, path=path, line=line, context=context
    )
    unchecked: list[ContractFinding] = []
    if not specs and not explicitly_external and not findings:
        unchecked_finding = ContractFinding(
            "UNCHECKED_EXECUTABLE",
            f"{context} is not a structured gateway call and was not compared with the contract",
            path=path,
            line=line,
        )
        unchecked.append(unchecked_finding)
        findings.append(unchecked_finding)
    checked = 0
    for tool_name, raw_arguments in specs:
        try:
            keys, values, placeholders = _parse_call_arguments(raw_arguments)
        except ValueError as exc:
            findings.append(
                ContractFinding(
                    "MALFORMED_TOOL_CALL",
                    f"{context} {tool_name} call is malformed: {exc}",
                    path=path,
                    line=line,
                )
            )
            continue
        call_findings, call_count = _validate_named_call(
            contract=contract,
            tool_name=tool_name,
            argument_keys=keys,
            argument_values=values,
            placeholders=placeholders,
            path=path,
            line=line,
            context=context,
        )
        findings.extend(call_findings)
        checked += call_count
    return findings, unchecked, checked


def _special_yaml_blocks(
    markdown: str, info: tuple[str, ...]
) -> tuple[list[tuple[int, Any]], list[ContractFinding], set[int]]:
    lines = markdown.splitlines()
    active: tuple[str, int, tuple[str, ...], int, list[str]] | None = None
    blocks: list[tuple[int, Any]] = []
    findings: list[ContractFinding] = []
    occupied: set[int] = set()
    for index, line in enumerate(lines, start=1):
        if active is not None:
            character, width, active_info, start, body = active
            if active_info == info:
                occupied.add(index)
            close = FENCE_CLOSE_RE.fullmatch(line)
            if (
                close is not None
                and close.group("marks")[0] == character
                and len(close.group("marks")) >= width
            ):
                if active_info == info:
                    try:
                        blocks.append((start, strict_yaml_load("\n".join(body))))
                    except yaml.YAMLError as exc:
                        findings.append(
                            ContractFinding(
                                "INVALID_ASSERTION_YAML",
                                f"line {start}: invalid {' '.join(info)} block: {exc}",
                                line=start,
                            )
                        )
                active = None
            else:
                body.append(line)
            continue
        opening = FENCE_OPEN_RE.match(line)
        if opening is None:
            continue
        marks = opening.group("marks")
        active_info = tuple(opening.group("info").split())
        active = (marks[0], len(marks), active_info, index, [])
        if active_info == info:
            occupied.add(index)
    if active is not None and active[2] == info:
        findings.append(
            ContractFinding(
                "UNCLOSED_ASSERTION_BLOCK",
                f"line {active[3]}: unclosed {' '.join(info)} block",
                line=active[3],
            )
        )
    return blocks, findings, occupied


def _validate_role_assertion(
    payload: Any, contract: VerifiedContract, *, path: str, line: int
) -> list[ContractFinding]:
    expected_keys = {"contract_digest_sha256", "council", "current_roles"}
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        return [
            ContractFinding(
                "INVALID_ROLE_ASSERTION",
                "deployed-contract-roles must contain exactly contract_digest_sha256, council, current_roles",
                path=path,
                line=line,
            )
        ]
    council = payload.get("council")
    roles = payload.get("current_roles")
    if not isinstance(council, dict) or set(council) != {
        "required_members",
        "valid_member_ids",
        "hall",
    }:
        return [
            ContractFinding(
                "INVALID_ROLE_ASSERTION",
                "role assertion council shape is invalid",
                path=path,
                line=line,
            )
        ]
    hall = council.get("hall")
    if not isinstance(hall, dict) or set(hall) != {"valid_agents", "default_agents"}:
        return [
            ContractFinding(
                "INVALID_ROLE_ASSERTION",
                "role assertion hall shape is invalid",
                path=path,
                line=line,
            )
        ]
    if not isinstance(roles, dict) or set(roles) != {
        "builders",
        "voters",
        "paused",
        "retired",
    }:
        return [
            ContractFinding(
                "INVALID_ROLE_ASSERTION",
                "role assertion current_roles shape is invalid",
                path=path,
                line=line,
            )
        ]
    for container in (council, hall, roles):
        for key, value in container.items():
            if key == "hall":
                continue
            if (
                not isinstance(value, list)
                or not all(isinstance(item, str) for item in value)
                or len(value) != len(set(value))
            ):
                return [
                    ContractFinding(
                        "INVALID_ROLE_ASSERTION",
                        f"role assertion {key} must be a unique string list",
                        path=path,
                        line=line,
                    )
                ]
    expected = contract.artifact["council"]
    mismatches: list[str] = []
    if payload["contract_digest_sha256"] != contract.artifact_digest_sha256:
        mismatches.append("contract_digest_sha256")
    if set(council["required_members"]) != set(expected["required_members"]):
        mismatches.append("council.required_members")
    if set(council["valid_member_ids"]) != set(expected["valid_member_ids"]):
        mismatches.append("council.valid_member_ids")
    if set(hall["valid_agents"]) != set(expected["hall"]["valid_agents"]):
        mismatches.append("council.hall.valid_agents")
    if set(hall["default_agents"]) != set(expected["hall"]["default_agents"]):
        mismatches.append("council.hall.default_agents")
    for role in ("builders", "voters", "paused", "retired"):
        if set(roles[role]) != set(expected["current_roles"][role]):
            mismatches.append(f"current_roles.{role}")
    if mismatches:
        return [
            ContractFinding(
                "ROLE_ASSERTION_MISMATCH",
                f"current role assertion differs from pinned contract at {mismatches}",
                path=path,
                line=line,
            )
        ]
    return []


def _is_current_role_claim(line: str, contract: VerifiedContract) -> bool:
    if _ROLE_CLAIM_RE.search(line) is None:
        return False
    if _ROLE_CONTEXT_RE.search(line) is not None:
        return True
    council = contract.artifact["council"]
    members = set(council["required_members"]) | set(council["valid_member_ids"])
    members.update(council["hall"]["valid_agents"])
    for values in council["current_roles"].values():
        members.update(values)
    return any(
        re.search(
            rf"(?<![A-Za-z0-9_-]){re.escape(member)}(?![A-Za-z0-9_-])",
            line,
            re.IGNORECASE,
        )
        is not None
        for member in members
    )


def _validate_runbook(
    path: Path, contract: VerifiedContract
) -> tuple[list[ContractFinding], list[ContractFinding], int, int]:
    relative = path.as_posix()
    markdown = path.read_text(encoding="utf-8")
    document = parse_markdown_document(markdown)
    findings = [
        ContractFinding("MALFORMED_HISTORICAL_SPAN", error, path=relative)
        for error in document.structure_errors
        if "historical" in error and "marker" in error
    ]
    unchecked: list[ContractFinding] = []
    role_blocks, role_block_findings, role_block_lines = _special_yaml_blocks(
        document.active_text, ROLE_ASSERTION_INFO
    )
    for finding in role_block_findings:
        findings.append(
            ContractFinding(
                finding.code, finding.message, path=relative, line=finding.line
            )
        )
    if len(role_blocks) > 1:
        findings.append(
            ContractFinding(
                "DUPLICATE_ROLE_ASSERTION",
                "an ACTIVE runbook may contain at most one deployed-contract-roles block",
                path=relative,
                line=role_blocks[1][0],
            )
        )
    for line, payload in role_blocks:
        role_findings = _validate_role_assertion(
            payload, contract, path=relative, line=line
        )
        findings.extend(role_findings)

    sections = extract_sections(document.active_text)
    calls_checked = 0
    for section in sections:
        if section.letter == "E":
            for entry in extract_e_entries(section):
                entry_id = entry.get("id", "<unknown>")
                endpoint = entry.get("tool_or_endpoint")
                if not isinstance(endpoint, str) or not endpoint.strip():
                    findings.append(
                        ContractFinding(
                            "UNCHECKED_EXECUTABLE",
                            f"§E {entry_id} has no checkable tool_or_endpoint string",
                            path=relative,
                            line=section.line_start,
                        )
                    )
                    continue
                endpoint_findings, endpoint_unchecked, checked = (
                    _validate_endpoint_text(
                        endpoint=endpoint,
                        contract=contract,
                        path=relative,
                        line=section.line_start,
                        context=f"§E {entry_id}",
                    )
                )
                findings.extend(endpoint_findings)
                unchecked.extend(endpoint_unchecked)
                calls_checked += checked
        elif section.letter == "I":
            payload = extract_i_payload(section)
            if not isinstance(payload, dict):
                continue
            scenarios = payload.get("scenario_set", [])
            if not isinstance(scenarios, list):
                continue
            for scenario in scenarios:
                if not isinstance(scenario, dict):
                    continue
                scenario_id = scenario.get("id", "<unknown>")
                scenario_text = scenario.get("scenario")
                if isinstance(scenario_text, str):
                    for endpoint_match in _SCENARIO_ENDPOINT_RE.finditer(scenario_text):
                        endpoint_findings, endpoint_unchecked, checked = (
                            _validate_endpoint_text(
                                endpoint=endpoint_match.group(1).strip(),
                                contract=contract,
                                path=relative,
                                line=section.line_start,
                                context=f"§I {scenario_id} scenario",
                            )
                        )
                        findings.extend(endpoint_findings)
                        unchecked.extend(endpoint_unchecked)
                        calls_checked += checked
                answers = scenario.get("expected_answers", [])
                if not isinstance(answers, list):
                    continue
                for answer in answers:
                    if (
                        not isinstance(answer, dict)
                        or answer.get("kind") != "tool_call"
                    ):
                        continue
                    tool_name = answer.get("tool")
                    keys = answer.get("argument_keys")
                    values = answer.get("argument_values", {})
                    if (
                        not isinstance(tool_name, str)
                        or not isinstance(keys, list)
                        or not all(isinstance(key, str) for key in keys)
                        or not isinstance(values, dict)
                    ):
                        findings.append(
                            ContractFinding(
                                "MALFORMED_TOOL_CALL",
                                f"§I {scenario_id} expected tool_call has invalid structured fields",
                                path=relative,
                                line=section.line_start,
                            )
                        )
                        continue
                    placeholders = {
                        key
                        for key, value in values.items()
                        if _is_placeholder_value(value)
                    }
                    call_findings, checked = _validate_named_call(
                        contract=contract,
                        tool_name=tool_name,
                        argument_keys=keys,
                        argument_values=values,
                        placeholders=placeholders,
                        path=relative,
                        line=section.line_start,
                        context=f"§I {scenario_id}",
                    )
                    findings.extend(call_findings)
                    calls_checked += checked

    call_blocks, call_block_findings, _ = _special_yaml_blocks(
        document.active_text, CALL_ASSERTION_INFO
    )
    for finding in call_block_findings:
        findings.append(
            ContractFinding(
                finding.code, finding.message, path=relative, line=finding.line
            )
        )
    for line, payload in call_blocks:
        entries = payload if isinstance(payload, list) else [payload]
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or set(entry) - {
                "tool",
                "argument_keys",
                "argument_values",
            }:
                findings.append(
                    ContractFinding(
                        "MALFORMED_TOOL_CALL",
                        "deployed-contract-call block has invalid shape",
                        path=relative,
                        line=line,
                    )
                )
                continue
            tool_name = entry.get("tool")
            keys = entry.get("argument_keys")
            values = entry.get("argument_values", {})
            if (
                not isinstance(tool_name, str)
                or not isinstance(keys, list)
                or not all(isinstance(key, str) for key in keys)
                or not isinstance(values, dict)
            ):
                findings.append(
                    ContractFinding(
                        "MALFORMED_TOOL_CALL",
                        "deployed-contract-call block has invalid fields",
                        path=relative,
                        line=line,
                    )
                )
                continue
            placeholders = {
                key for key, value in values.items() if _is_placeholder_value(value)
            }
            block_findings, checked = _validate_named_call(
                contract=contract,
                tool_name=tool_name,
                argument_keys=keys,
                argument_values=values,
                placeholders=placeholders,
                path=relative,
                line=line,
                context=f"explicit executable {index + 1}",
            )
            findings.extend(block_findings)
            calls_checked += checked

    relevant_ranges = [
        (section.line_start, section.line_end)
        for section in sections
        if section.letter in _RELEVANT_ROLE_SECTIONS
    ]
    claim_lines: list[tuple[int, str]] = []
    active_lines = document.active_text.splitlines()
    for start, end in relevant_ranges:
        for line_number in range(start, min(end, len(active_lines)) + 1):
            if line_number in role_block_lines:
                continue
            line = active_lines[line_number - 1]
            if _is_current_role_claim(line, contract):
                claim_lines.append((line_number, line.strip()))
    if claim_lines:
        for line_number, text in claim_lines:
            unchecked_finding = ContractFinding(
                "UNCHECKED_CURRENT_ROLE_CLAIM",
                f"current role prose is not bound to a deployed-contract-roles assertion: {text[:180]}",
                path=relative,
                line=line_number,
            )
            unchecked.append(unchecked_finding)
            findings.append(unchecked_finding)
    return findings, unchecked, calls_checked, len(role_blocks)


def validate_runbooks(
    repo_root: Path | str,
    contract: VerifiedContract,
    *,
    runbooks_dir: Path | str = "runbooks",
) -> ValidationReport:
    root = Path(repo_root)
    directory = Path(runbooks_dir)
    if not directory.is_absolute():
        directory = root / directory
    report = ValidationReport(
        contract_digest_sha256=contract.artifact_digest_sha256,
        envelope_sha256=contract.envelope_digest_sha256,
        handler_sha=contract.artifact["handler_sha"],
        proxy_release_identity=contract.artifact["proxy_release_identity"],
        runbook_lifecycle_readiness=contract.runbook_lifecycle_readiness.status,
        runbook_lifecycle_readiness_reasons=list(
            contract.runbook_lifecycle_readiness.reasons
        ),
    )
    if not directory.is_dir():
        report.findings.append(
            ContractFinding(
                "RUNBOOKS_DIRECTORY_MISSING",
                f"runbooks directory is missing: {directory}",
            )
        )
        return report
    for path in sorted(directory.rglob("*.md")):
        try:
            frontmatter = _frontmatter(path)
        except UnicodeDecodeError:
            report.findings.append(
                ContractFinding(
                    "RUNBOOK_INVALID_UTF8", "runbook is not UTF-8", path=path.as_posix()
                )
            )
            continue
        except CatalogError as exc:
            report.findings.append(
                ContractFinding(
                    "RUNBOOK_FRONTMATTER_INVALID",
                    f"runbook catalog admission failed: {exc}",
                    path=path.as_posix(),
                    line=1,
                )
            )
            continue
        if frontmatter is None:
            continue
        status = frontmatter.get("status")
        if status not in {"ACTIVE", "DRAFT"} or "runbook_id" not in frontmatter:
            report.findings.append(
                ContractFinding(
                    "RUNBOOK_FRONTMATTER_INVALID",
                    "catalog opt-in requires runbook_id and status ACTIVE or DRAFT",
                    path=path.as_posix(),
                    line=1,
                )
            )
            continue
        if status != "ACTIVE":
            continue
        report.active_runbooks_checked += 1
        findings, unchecked, calls_checked, assertions_checked = _validate_runbook(
            path, contract
        )
        report.findings.extend(findings)
        report.unchecked_claims.extend(unchecked)
        report.tool_calls_checked += calls_checked
        report.role_assertions_checked += assertions_checked
    report.findings.sort(
        key=lambda item: (item.path or "", item.line or 0, item.code, item.message)
    )
    return report


def validate_deployed_contract(
    repo_root: Path | str,
    *,
    pin_path: Path | str = DEFAULT_PIN_PATH,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
    runbooks_dir: Path | str = "runbooks",
    now: datetime | None = None,
    artifact_only: bool = False,
    require_runbook_lifecycle_ready: bool = False,
) -> ValidationReport:
    """Verify the exact artifact and, by default, all ACTIVE runbook claims."""

    try:
        contract = verify_pinned_artifact(
            repo_root,
            pin_path=pin_path,
            schema_path=schema_path,
            now=now,
        )
    except ContractFailure as exc:
        return ValidationReport(findings=[exc.finding])
    if artifact_only:
        report = ValidationReport(
            contract_digest_sha256=contract.artifact_digest_sha256,
            envelope_sha256=contract.envelope_digest_sha256,
            handler_sha=contract.artifact["handler_sha"],
            proxy_release_identity=contract.artifact["proxy_release_identity"],
            runbook_lifecycle_readiness=contract.runbook_lifecycle_readiness.status,
            runbook_lifecycle_readiness_reasons=list(
                contract.runbook_lifecycle_readiness.reasons
            ),
        )
    else:
        report = validate_runbooks(repo_root, contract, runbooks_dir=runbooks_dir)
    if require_runbook_lifecycle_ready and not contract.runbook_lifecycle_readiness.ready:
        reason_codes = ", ".join(
            finding.code for finding in contract.runbook_lifecycle_readiness.reasons
        )
        report.findings.append(
            ContractFinding(
                "RUNBOOK_LIFECYCLE_NOT_READY",
                f"target runbook lifecycle rollout is NOT_READY ({reason_codes})",
            )
        )
        report.findings.sort(
            key=lambda item: (item.path or "", item.line or 0, item.code, item.message)
        )
    return report


def _print_text_report(report: ValidationReport) -> None:
    for finding in report.findings:
        location = finding.path or "<contract>"
        if finding.line is not None:
            location += f":{finding.line}"
        print(f"{finding.severity} {finding.code} {location} {finding.message}")
    for finding in report.runbook_lifecycle_readiness_reasons:
        print(
            f"{finding.severity} {finding.code} <contract> {finding.message}"
        )
    status = "PASS" if report.ok else "FAIL"
    print(
        f"{status} deployed-contract active_runbooks={report.active_runbooks_checked} "
        f"tool_calls={report.tool_calls_checked} role_assertions={report.role_assertions_checked} "
        f"unchecked={len(report.unchecked_claims)} "
        f"runbook_lifecycle={report.runbook_lifecycle_readiness or 'UNKNOWN'}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the pinned signed deployed gateway contract"
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--pin", type=Path, default=DEFAULT_PIN_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--runbooks-dir", type=Path, default=Path("runbooks"))
    parser.add_argument("--artifact-only", action="store_true")
    parser.add_argument(
        "--require-runbook-lifecycle-ready",
        action="store_true",
        help="fail unless the signed target plan/close/action lifecycle is rollout-ready",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = validate_deployed_contract(
        args.repo,
        pin_path=args.pin,
        schema_path=args.schema,
        runbooks_dir=args.runbooks_dir,
        artifact_only=args.artifact_only,
        require_runbook_lifecycle_ready=args.require_runbook_lifecycle_ready,
    )
    if args.json_output:
        print(json.dumps(report.to_dict(), sort_keys=True, separators=(",", ":")))
    else:
        _print_text_report(report)
    if report.ok:
        return 0
    infrastructure_codes = {
        "CONTRACT_PIN_MISSING",
        "CONTRACT_ARTIFACT_MISSING",
        "TRUST_STORE_MISSING",
        "CONTRACT_SCHEMA_MISSING",
    }
    return (
        2 if any(item.code in infrastructure_codes for item in report.findings) else 1
    )


if __name__ == "__main__":
    sys.exit(main())
