from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from runbook_tools import deployed_contract as dc

SCHEMA_PATH = (
    Path(__file__).parents[1] / "schemas" / "deployed_tool_contract.schema.json"
)
NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
HANDLER_SHA = "1" * 40
PROXY_IDENTITY = "proxy-release-2026-07-31.1"
POLICY_REVISION = "runbook-gates-v4"
SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
SECOND_SEED = bytes.fromhex(
    "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb"
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _noncanonical_b64url_equivalent(value: str) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    for character in alphabet:
        candidate = value[:-1] + character
        if candidate == value:
            continue
        if base64.urlsafe_b64decode(candidate + "=" * (-len(candidate) % 4)) == decoded:
            return candidate
    raise AssertionError("fixture has no alternate pad-bit spelling")


def _encode_point(point: tuple[int, int, int, int]) -> bytes:
    x, y, z, _ = point
    z_inverse = pow(z, dc._ED_Q - 2, dc._ED_Q)
    affine_x = x * z_inverse % dc._ED_Q
    affine_y = y * z_inverse % dc._ED_Q
    return (affine_y | ((affine_x & 1) << 255)).to_bytes(32, "little")


def _public_key(seed: bytes) -> tuple[bytes, int, bytes]:
    expanded = hashlib.sha512(seed).digest()
    scalar_bytes = bytearray(expanded[:32])
    scalar_bytes[0] &= 248
    scalar_bytes[31] &= 63
    scalar_bytes[31] |= 64
    scalar = int.from_bytes(scalar_bytes, "little")
    return _encode_point(dc._ed_scalar_mult(dc._ED_BASE, scalar)), scalar, expanded[32:]


def _sign(seed: bytes, message: bytes) -> bytes:
    public_key, scalar, prefix = _public_key(seed)
    nonce = (
        int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % dc._ED_L
    )
    encoded_r = _encode_point(dc._ed_scalar_mult(dc._ED_BASE, nonce))
    challenge = (
        int.from_bytes(
            hashlib.sha512(encoded_r + public_key + message).digest(), "little"
        )
        % dc._ED_L
    )
    encoded_s = ((nonce + challenge * scalar) % dc._ED_L).to_bytes(32, "little")
    return encoded_r + encoded_s


def _tool(
    name: str,
    properties: dict[str, Any],
    required: list[str],
    *,
    output_properties: dict[str, Any] | None = None,
    output_required: list[str] | None = None,
    effect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effect = effect or {
        "mode": "mutating",
        "default_effect": "mutating",
        "default_risk": "medium",
        "default_receipt_requirement": "none",
        "action_discriminator": None,
        "actions": [],
    }
    return {
        "name": name,
        "title": f"{name} title",
        "description": f"Exact deployed description for {name}",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "outputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": output_properties
            or {"outcome": {"type": "string", "enum": ["OK"]}},
            "required": output_required or ["outcome"],
            "additionalProperties": False,
        },
        "effect": effect,
        "annotations": {
            "readOnlyHint": effect["default_effect"] == "read_only"
        },
        "_meta": {"ai.market/risk": "server-owned"},
    }


def _action_context_schema() -> dict[str, Any]:
    fields = {
        "context_id": {"type": "string", "minLength": 1},
        "canonical_arguments_sha256": {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$",
        },
        "session_id": {"type": "string", "minLength": 1},
        "component": {"type": "string", "minLength": 1},
        "policy_revision": {"type": "string", "minLength": 1},
        "expires_at": {"type": "string", "format": "date-time"},
    }
    return {
        "type": "object",
        "properties": fields,
        "required": list(fields),
        "additionalProperties": False,
    }


def _require_payload_for_outcome(
    tool: dict[str, Any], outcome: str, *payload_properties: str
) -> None:
    tool["outputSchema"].setdefault("allOf", []).append(
        {
            "if": {
                "properties": {"outcome": {"const": outcome}},
                "required": ["outcome"],
            },
            "then": {"required": list(payload_properties)},
        }
    )


def _bind_exact_argument_receipt(tool: dict[str, Any]) -> None:
    tool["inputSchema"]["properties"]["action_receipt"] = {
        "type": "string",
        "minLength": 1,
    }
    outcome = tool["outputSchema"]["properties"]["outcome"]
    values = outcome.setdefault("enum", [])
    if "ACTION_CONTEXT_REQUIRED" not in values:
        values.append("ACTION_CONTEXT_REQUIRED")
    tool["outputSchema"]["properties"]["action_context"] = _action_context_schema()
    _require_payload_for_outcome(tool, "ACTION_CONTEXT_REQUIRED", "action_context")
    effect = tool["effect"]
    if effect["default_effect"] == "mutating" and effect["default_risk"] == "high":
        effect["default_receipt_requirement"] = "exact_arguments"
    for action in effect["actions"]:
        if action["effect"] == "mutating" and action["risk"] == "high":
            action["receipt_requirement"] = "exact_arguments"


def _artifact(*, lifecycle_profile: str = "target") -> dict[str, Any]:
    callable_members = ["mp", "cc", "kimi", "glm", "ag"]
    state_tool = _tool(
        "state_request",
        {
            "action": {"type": "string", "enum": ["get", "patch"]},
            "key": {"type": "string"},
            "patch": {"type": "object"},
            "threshold": {"type": "number", "minimum": 0, "maximum": 1},
        },
        ["action", "key"],
    )
    state_tool["inputSchema"]["allOf"] = [
        {
            "if": {
                "properties": {"action": {"const": "patch"}},
                "required": ["action"],
            },
            "then": {"required": ["patch"]},
        },
        {
            "if": {
                "properties": {"action": {"const": "get"}},
                "required": ["action"],
            },
            "then": {"not": {"required": ["patch"]}},
        },
    ]
    state_tool["effect"] = {
        "mode": "action_discriminated",
        "default_effect": "mutating",
        "default_risk": "high",
        "default_receipt_requirement": "none",
        "action_discriminator": "action",
        "actions": [
            {
                "value": "get",
                "effect": "read_only",
                "risk": "none",
                "receipt_requirement": "none",
            },
            {
                "value": "patch",
                "effect": "mutating",
                "risk": "high",
                "receipt_requirement": "none",
            },
        ],
    }
    if lifecycle_profile == "target":
        plan_tool = _tool(
            "kd_session_plan",
            {
                "session_id": {"type": "string"},
                "objectives": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "consultation_ids": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1},
                },
                "gap_ids": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1},
                },
            },
            ["session_id", "objectives"],
            output_properties={
                "outcome": {
                    "type": "string",
                    "enum": ["RUNBOOK_CONTEXT_SELECTION_REQUIRED", "PLAN_ACCEPTED"],
                },
                "selection_set": {
                    "type": "object",
                    "properties": {
                        "selection_set_id": {"type": "string", "minLength": 1},
                        "catalog_sha": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{40}$",
                        },
                        "catalog_digest_sha256": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{64}$",
                        },
                        "complete": {"const": True},
                        "exact_byte_count": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 40000,
                        },
                        "delivery_digest_sha256": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{64}$",
                        },
                        "objectives": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "objective_index": {
                                        "type": "integer",
                                        "minimum": 1,
                                    },
                                    "candidates": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "consultation_id": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "runbook_id": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "section_id": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "path": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "heading": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "excerpt": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "excerpt_digest_sha256": {
                                                    "type": "string",
                                                    "pattern": "^[0-9a-f]{64}$",
                                                },
                                                "rank": {
                                                    "type": "integer",
                                                    "minimum": 1,
                                                },
                                                "match_evidence": {
                                                    "type": "object"
                                                },
                                            },
                                            "required": [
                                                "consultation_id",
                                                "runbook_id",
                                                "section_id",
                                                "path",
                                                "heading",
                                                "excerpt",
                                                "excerpt_digest_sha256",
                                                "rank",
                                                "match_evidence",
                                            ],
                                            "additionalProperties": False,
                                        },
                                    },
                                    "gap_id": {"type": "string", "minLength": 1},
                                },
                                "required": [
                                    "objective_index",
                                    "candidates",
                                    "gap_id",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "selection_set_id",
                        "catalog_sha",
                        "catalog_digest_sha256",
                        "complete",
                        "exact_byte_count",
                        "delivery_digest_sha256",
                        "objectives",
                    ],
                    "additionalProperties": False,
                },
                "accepted_plan_receipt": {
                    "type": "object",
                    "properties": {
                        "plan_revision": {"type": "integer", "minimum": 1},
                        "session_id": {"type": "string", "minLength": 1},
                        "instance": {"type": "string", "minLength": 1},
                        "objectives_digest_sha256": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{64}$",
                        },
                        "work_type": {"type": "string", "minLength": 1},
                        "selection_set_id": {"type": "string", "minLength": 1},
                        "catalog_sha": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{40}$",
                        },
                        "request_digest_sha256": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{64}$",
                        },
                        "delivery_digest_sha256": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{64}$",
                        },
                    },
                    "required": [
                        "plan_revision",
                        "session_id",
                        "instance",
                        "objectives_digest_sha256",
                        "work_type",
                        "selection_set_id",
                        "catalog_sha",
                        "request_digest_sha256",
                        "delivery_digest_sha256",
                    ],
                    "additionalProperties": False,
                },
            },
            output_required=["outcome"],
        )
        close_tool = _tool(
            "kd_session_close",
            {
                "session_id": {"type": "string"},
                "runbook_impact": {"type": "object"},
            },
            ["session_id"],
            output_properties={
                "outcome": {"type": "string", "enum": ["COMMITTED"]},
                "close_receipt": {
                    "type": "object",
                    "properties": {
                        "status": {"const": "COMMITTED"},
                        "transaction_id": {"type": "string", "minLength": 1},
                        "close_request_id": {"type": "string", "minLength": 1},
                        "request_digest_sha256": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{64}$",
                        },
                        "session_id": {"type": "string", "minLength": 1},
                        "committed_at": {"type": "string", "format": "date-time"},
                        "immutable": {"const": True},
                    },
                    "required": [
                        "status",
                        "transaction_id",
                        "close_request_id",
                        "request_digest_sha256",
                        "session_id",
                        "committed_at",
                        "immutable",
                    ],
                    "additionalProperties": False,
                },
                "obligation_outcomes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "obligation_id": {"type": "string", "minLength": 1},
                            "status": {
                                "type": "string",
                                "enum": [
                                    "open",
                                    "satisfied",
                                    "explicitly_deferred",
                                ],
                            },
                            "occurrence_recorded": {"type": "boolean"},
                        },
                        "required": [
                            "obligation_id",
                            "status",
                            "occurrence_recorded",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            output_required=["outcome"],
        )
        _require_payload_for_outcome(
            plan_tool,
            "RUNBOOK_CONTEXT_SELECTION_REQUIRED",
            "selection_set",
        )
        _require_payload_for_outcome(
            plan_tool,
            "PLAN_ACCEPTED",
            "accepted_plan_receipt",
        )
        _require_payload_for_outcome(
            close_tool,
            "COMMITTED",
            "close_receipt",
            "obligation_outcomes",
        )
        lifecycle = {
            "profile": "target",
            "plan": {
                "tool_name": "kd_session_plan",
                "protocol": "server_delivered_two_stage",
                "first_outcome_discriminator": "outcome",
                "selection_required_outcome": "RUNBOOK_CONTEXT_SELECTION_REQUIRED",
                "accepted_outcome": "PLAN_ACCEPTED",
                "first_outcome_typed": True,
                "first_outcome_semantic_writes": "none",
                "binding": "server_issued_ids_bound_to_session_instance_objectives_work_type_revision_catalog_excerpt_digest",
                "selection_envelope_property": "selection_set",
                "accepted_receipt_property": "accepted_plan_receipt",
            },
            "delivery": {
                "candidate_delivery_mode": "required",
                "legacy_consultation_mode": "reject",
                "candidate_limit": 3,
            },
            "close": {
                "tool_name": "kd_session_close",
                "protocol": "structured_runbook_impact",
                "outcome_discriminator": "outcome",
                "committed_outcome": "COMMITTED",
                "receipt": "typed_transaction_scoped_committed",
                "committed_receipt_property": "close_receipt",
                "obligation_outcomes_property": "obligation_outcomes",
                "obligation_transaction": "atomic_backend_transaction_outbox",
                "server_owned_evidence": True,
            },
            "action_receipts": {
                "protocol": "two_stage_exact_arguments",
                "context_required_outcome": "ACTION_CONTEXT_REQUIRED",
                "outcome_discriminator": "outcome",
                "receipt_argument": "action_receipt",
                "context_property": "action_context",
                "context_outcome_typed": True,
                "context_outcome_semantic_writes": "none",
                "one_use": True,
                "expiring": True,
                "binding": "canonical_tool_arguments_session_component_policy_revision",
            },
        }
    elif lifecycle_profile == "legacy":
        plan_tool = _tool(
            "kd_session_plan",
            {
                "session_id": {"type": "string"},
                "objectives": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "runbook_consultation": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            ["session_id", "objectives", "runbook_consultation"],
        )
        close_tool = _tool(
            "kd_session_close",
            {
                "session_id": {"type": "string"},
                "runbook_exit": {"type": "object"},
            },
            ["session_id", "runbook_exit"],
        )
        lifecycle = {
            "profile": "legacy",
            "plan": {
                "tool_name": "kd_session_plan",
                "protocol": "legacy_caller_authored",
                "first_outcome_discriminator": "outcome",
                "selection_required_outcome": "NONE",
                "accepted_outcome": "NONE",
                "first_outcome_typed": False,
                "first_outcome_semantic_writes": "not_applicable",
                "binding": "caller_authored_refs",
                "selection_envelope_property": "NONE",
                "accepted_receipt_property": "NONE",
            },
            "delivery": {
                "candidate_delivery_mode": "off",
                "legacy_consultation_mode": "allow",
                "candidate_limit": 0,
            },
            "close": {
                "tool_name": "kd_session_close",
                "protocol": "legacy_runbook_exit",
                "outcome_discriminator": "outcome",
                "committed_outcome": "NONE",
                "receipt": "none",
                "committed_receipt_property": "NONE",
                "obligation_outcomes_property": "NONE",
                "obligation_transaction": "none",
                "server_owned_evidence": False,
            },
            "action_receipts": {
                "protocol": "none",
                "context_required_outcome": "NONE",
                "outcome_discriminator": "outcome",
                "receipt_argument": "NONE",
                "context_property": "NONE",
                "context_outcome_typed": False,
                "context_outcome_semantic_writes": "not_applicable",
                "one_use": False,
                "expiring": False,
                "binding": "none",
            },
        }
    else:
        raise ValueError(lifecycle_profile)
    if lifecycle_profile == "target":
        _bind_exact_argument_receipt(state_tool)
    tools = [
        _tool(
            "council_request",
            {
                "agent": {"type": "string", "enum": list(callable_members)},
                "mode": {
                    "type": "string",
                    "enum": ["build", "review", "open_response"],
                },
                "task": {"type": "string"},
                "cwd": {"type": "string"},
            },
            ["agent", "mode", "task"],
        ),
        _tool(
            "council_hall",
            {
                "agents": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(callable_members)},
                    "default": ["cc", "kimi", "glm"],
                },
                "prompt": {"type": "string"},
            },
            ["prompt"],
        ),
        state_tool,
        plan_tool,
        close_tool,
    ]
    artifact: dict[str, Any] = {
        "artifact_format_version": "2",
        "handler_sha": HANDLER_SHA,
        "handler_release_identity": "gateway-production-2026-07-31.1",
        "proxy_release_identity": PROXY_IDENTITY,
        "policy_revision": POLICY_REVISION,
        "schema_digest_sha256": "",
        "tools": tools,
        "council": {
            "dispatch_tool_name": "council_request",
            "member_argument": "agent",
            "required_members": ["cc", "kimi", "glm"],
            "valid_member_ids": ["cc", "kimi", "glm"],
            "hall": {
                "tool_name": "council_hall",
                "agents_argument": "agents",
                "valid_agents": list(callable_members),
                "default_agents": ["cc", "kimi", "glm"],
            },
            "current_roles": {
                "builders": ["mp"],
                "voters": ["cc", "kimi", "glm"],
                "paused": ["ag"],
                "retired": ["deepseek"],
            },
        },
        "runbook_lifecycle": lifecycle,
        "source_identifiers": [],
    }
    artifact["schema_digest_sha256"] = hashlib.sha256(
        dc.canonical_json({"tools": tools})
    ).hexdigest()
    for projection in sorted(dc._REQUIRED_SOURCE_PROJECTIONS):
        artifact["source_identifiers"].append(
            {
                "projection": projection,
                "repository": "aidotmarket/koskadeux-mcp",
                "commit_sha": HANDLER_SHA if projection != "proxy" else "2" * 40,
                "path": "tools/contract_source.py"
                if projection != "proxy"
                else "proxy/index.ts",
                "symbol": projection,
                "blob_sha256": "3" * 64,
            }
        )
    return artifact


def _refresh_schema_digest(artifact: dict[str, Any]) -> None:
    artifact["schema_digest_sha256"] = hashlib.sha256(
        dc.canonical_json({"tools": artifact["tools"]})
    ).hexdigest()


def _trust_store(*, valid_until: str = "2030-01-01T00:00:00Z") -> dict[str, Any]:
    public_key, _, _ = _public_key(SEED)
    return {
        "trust_store_format_version": "1",
        "keys": [
            {
                "kid": "gateway-prod-2026-a",
                "algorithm": "Ed25519",
                "public_key_base64url": _b64url(public_key),
                "issuer": "ai.market-gateway-deployer",
                "audiences": ["runbooks-ci"],
                "valid_from": "2025-01-01T00:00:00Z",
                "valid_until": valid_until,
                "revoked_at": None,
            }
        ],
        "revoked_kids": [],
    }


def _metadata(
    artifact_digest: str,
    trust_store: dict[str, Any],
    *,
    signing_key_index: int = 0,
) -> dict[str, Any]:
    key = trust_store["keys"][signing_key_index]
    return {
        "algorithm": "Ed25519",
        "kid": key["kid"],
        "issuer": key["issuer"],
        "audience": "runbooks-ci",
        "issued_at": "2026-01-02T03:04:05Z",
        "key_valid_from": key["valid_from"],
        "key_valid_until": key["valid_until"],
        "artifact_sha256": artifact_digest,
    }


def _write_fixture(
    root: Path,
    *,
    artifact: dict[str, Any] | None = None,
    trust_store: dict[str, Any] | None = None,
    metadata_mutator: Callable[[dict[str, Any]], None] | None = None,
    signing_seed: bytes = SEED,
    signing_key_index: int = 0,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    artifact = artifact or _artifact()
    trust_store = trust_store or _trust_store()
    artifact_digest = hashlib.sha256(dc.canonical_json(artifact)).hexdigest()
    metadata = _metadata(
        artifact_digest, trust_store, signing_key_index=signing_key_index
    )
    if metadata_mutator is not None:
        metadata_mutator(metadata)
    signed_bytes = dc.canonical_json(
        {"artifact": artifact, "signature_metadata": metadata}
    )
    envelope = {
        "artifact": artifact,
        "signature": _b64url(_sign(signing_seed, signed_bytes)),
        "signature_metadata": metadata,
    }
    envelope_raw = dc.canonical_json(envelope)
    contracts_dir = root / "contracts"
    artifacts_dir = contracts_dir / "deployed"
    artifacts_dir.mkdir(parents=True)
    artifact_path = artifacts_dir / f"{artifact_digest}.json"
    artifact_path.write_bytes(envelope_raw)
    trust_raw = dc.canonical_json(trust_store)
    trust_path = contracts_dir / "deployed-tool-contract.keys.json"
    trust_path.write_bytes(trust_raw)
    pin = {
        "pin_format_version": "1",
        "artifact_path": artifact_path.relative_to(root).as_posix(),
        "artifact_sha256": artifact_digest,
        "envelope_sha256": hashlib.sha256(envelope_raw).hexdigest(),
        "handler_sha": HANDLER_SHA,
        "proxy_release_identity": PROXY_IDENTITY,
        "policy_revision": POLICY_REVISION,
        "issuer": "ai.market-gateway-deployer",
        "audience": "runbooks-ci",
        "trust_store_path": trust_path.relative_to(root).as_posix(),
        "trust_store_sha256": hashlib.sha256(trust_raw).hexdigest(),
    }
    pin_path = contracts_dir / "deployed-tool-contract.pin.json"
    pin_path.write_bytes(dc.canonical_json(pin))
    return pin_path, pin, envelope


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _rewrite_pin(pin_path: Path, pin: dict[str, Any]) -> None:
    pin_path.write_bytes(dc.canonical_json(pin))


def _rewrite_envelope(
    root: Path, pin_path: Path, pin: dict[str, Any], envelope: dict[str, Any]
) -> Path:
    raw = dc.canonical_json(envelope)
    artifact_path = root / pin["artifact_path"]
    artifact_path.write_bytes(raw)
    pin["envelope_sha256"] = hashlib.sha256(raw).hexdigest()
    _rewrite_pin(pin_path, pin)
    return artifact_path


def _resign_artifact(
    root: Path, artifact: dict[str, Any], trust_store: dict[str, Any] | None = None
) -> Path:
    pin_path, _, _ = _write_fixture(root, artifact=artifact, trust_store=trust_store)
    return pin_path


def _codes(report: dc.ValidationReport) -> set[str]:
    return {finding.code for finding in report.findings}


def _verify(root: Path, pin_path: Path) -> dc.ValidationReport:
    return dc.validate_deployed_contract(
        root,
        pin_path=pin_path,
        schema_path=SCHEMA_PATH,
        now=NOW,
        artifact_only=True,
    )


def _write_runbook(root: Path, body: str, name: str = "fixture.md") -> Path:
    directory = root / "runbooks"
    directory.mkdir(exist_ok=True)
    path = directory / name
    path.write_text(
        "---\nrunbook_id: fixture\nstatus: ACTIVE\n---\n\n# Fixture\n\n" + body,
        encoding="utf-8",
    )
    return path


def test_rfc8032_vector_and_signed_fixture_pass(tmp_path: Path) -> None:
    public_key = bytes.fromhex(
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    )
    signature = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    assert dc.verify_ed25519(public_key, b"", signature)
    pin_path, _, _ = _write_fixture(tmp_path)
    report = _verify(tmp_path, pin_path)
    assert report.ok, report.findings
    assert report.handler_sha == HANDLER_SHA
    assert report.runbook_lifecycle_readiness == "READY"


def test_honest_legacy_artifact_is_integrity_valid_but_not_ready(
    tmp_path: Path,
) -> None:
    pin_path = _resign_artifact(tmp_path, _artifact(lifecycle_profile="legacy"))

    report = _verify(tmp_path, pin_path)

    assert report.ok, report.findings
    assert report.runbook_lifecycle_readiness == "NOT_READY"
    assert {
        finding.code for finding in report.runbook_lifecycle_readiness_reasons
    } == {"LEGACY_LIFECYCLE_PROFILE"}


def test_readiness_requirement_rejects_honest_legacy_artifact(tmp_path: Path) -> None:
    pin_path = _resign_artifact(tmp_path, _artifact(lifecycle_profile="legacy"))

    report = dc.validate_deployed_contract(
        tmp_path,
        pin_path=pin_path,
        schema_path=SCHEMA_PATH,
        now=NOW,
        artifact_only=True,
        require_runbook_lifecycle_ready=True,
    )

    assert report.runbook_lifecycle_readiness == "NOT_READY"
    assert _codes(report) == {"RUNBOOK_LIFECYCLE_NOT_READY"}


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("candidate_delivery_mode", "assist", "CANDIDATE_DELIVERY_NOT_REQUIRED"),
        ("legacy_consultation_mode", "warn", "LEGACY_CONSULTATION_NOT_REJECTED"),
        ("candidate_limit", 0, "CANDIDATE_LIMIT_ZERO"),
    ],
)
def test_target_delivery_modes_are_part_of_deterministic_readiness(
    tmp_path: Path, field: str, value: Any, reason: str
) -> None:
    artifact = _artifact()
    artifact["runbook_lifecycle"]["delivery"][field] = value
    pin_path = _resign_artifact(tmp_path, artifact)

    report = _verify(tmp_path, pin_path)

    assert report.ok, report.findings
    assert report.runbook_lifecycle_readiness == "NOT_READY"
    assert [
        finding.code for finding in report.runbook_lifecycle_readiness_reasons
    ] == [reason]


def test_input_only_signed_artifact_is_invalid(tmp_path: Path) -> None:
    artifact = _artifact()
    artifact["tools"][0].pop("outputSchema")
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"CONTRACT_SCHEMA_INVALID"}


def test_legacy_plan_and_close_schemas_cannot_advertise_target_readiness(
    tmp_path: Path,
) -> None:
    artifact = _artifact(lifecycle_profile="legacy")
    artifact["runbook_lifecycle"] = _artifact()["runbook_lifecycle"]
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


def test_legacy_projection_cannot_claim_target_delivery_modes(tmp_path: Path) -> None:
    artifact = _artifact(lifecycle_profile="legacy")
    artifact["runbook_lifecycle"]["delivery"].update(
        {
            "candidate_delivery_mode": "required",
            "legacy_consultation_mode": "reject",
            "candidate_limit": 3,
        }
    )
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {
        "LIFECYCLE_CAPABILITY_MISMATCH"
    }


def test_action_discriminated_unknown_fallthrough_must_remain_high_risk(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    tool["effect"]["default_risk"] = "low"
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"CONTRACT_SCHEMA_INVALID"}


def test_unclassified_tool_effect_is_invalid(tmp_path: Path) -> None:
    artifact = _artifact()
    artifact["tools"][0].pop("effect")
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"CONTRACT_SCHEMA_INVALID"}


@pytest.mark.parametrize(
    ("tool_name", "risk"),
    [("kd_session_plan", "low"), ("kd_session_close", "medium")],
)
def test_explicit_low_or_medium_lifecycle_mutation_is_not_forced_high(
    tmp_path: Path, tool_name: str, risk: str
) -> None:
    artifact = _artifact()
    tool = next(tool for tool in artifact["tools"] if tool["name"] == tool_name)
    tool["effect"]["default_risk"] = risk
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    report = _verify(tmp_path, pin_path)
    assert report.ok, report.findings
    assert report.runbook_lifecycle_readiness == "READY"


@pytest.mark.parametrize("binding", ["default", "patch"])
def test_target_unrelated_high_risk_tool_requires_exact_argument_receipt(
    tmp_path: Path, binding: str
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    if binding == "default":
        state_tool["effect"]["default_receipt_requirement"] = "none"
    else:
        patch_effect = next(
            action
            for action in state_tool["effect"]["actions"]
            if action["value"] == "patch"
        )
        patch_effect["receipt_requirement"] = "none"
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {
        "LIFECYCLE_CAPABILITY_MISMATCH"
    }


@pytest.mark.parametrize(
    ("tool_name", "required_outcome"),
    [
        ("kd_session_plan", "RUNBOOK_CONTEXT_SELECTION_REQUIRED"),
        ("kd_session_close", "COMMITTED"),
    ],
)
def test_target_result_schema_must_expose_typed_lifecycle_outcomes(
    tmp_path: Path, tool_name: str, required_outcome: str
) -> None:
    artifact = _artifact()
    tool = next(tool for tool in artifact["tools"] if tool["name"] == tool_name)
    outcome_schema = tool["outputSchema"]["properties"]["outcome"]
    outcome_schema["enum"] = [
        value for value in outcome_schema["enum"] if value != required_outcome
    ] or ["OTHER_OUTCOME"]
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


@pytest.mark.parametrize(
    ("tool_name", "payload_property"),
    [
        ("kd_session_plan", "selection_set"),
        ("kd_session_plan", "accepted_plan_receipt"),
        ("kd_session_close", "close_receipt"),
        ("kd_session_close", "obligation_outcomes"),
    ],
)
def test_target_discriminator_only_result_schema_is_not_readiness_evidence(
    tmp_path: Path, tool_name: str, payload_property: str
) -> None:
    artifact = _artifact()
    tool = next(tool for tool in artifact["tools"] if tool["name"] == tool_name)
    tool["outputSchema"]["properties"][payload_property] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


def test_outcome_binding_condition_cannot_be_made_impossible(tmp_path: Path) -> None:
    artifact = _artifact()
    plan_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "kd_session_plan"
    )
    branch = next(
        branch
        for branch in plan_tool["outputSchema"]["allOf"]
        if branch["if"]["properties"]["outcome"]["const"] == "PLAN_ACCEPTED"
    )
    branch["if"]["not"] = {}
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


@pytest.mark.parametrize(
    ("tool_name", "container", "field"),
    [
        ("kd_session_plan", "selection_set", "complete"),
        ("kd_session_close", "close_receipt", "immutable"),
        ("kd_session_close", "close_receipt", "status"),
    ],
)
def test_lifecycle_singleton_literals_cannot_admit_false_or_noncommitted_values(
    tmp_path: Path, tool_name: str, container: str, field: str
) -> None:
    artifact = _artifact()
    tool = next(tool for tool in artifact["tools"] if tool["name"] == tool_name)
    field_schema = tool["outputSchema"]["properties"][container]["properties"][field]
    if field == "status":
        field_schema.clear()
        field_schema.update({"type": "string", "enum": ["COMMITTED", "FAILED"]})
    else:
        field_schema.clear()
        field_schema.update({"type": "boolean", "enum": [True, False]})
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


@pytest.mark.parametrize(
    "field",
    [
        "selection_set_id",
        "catalog_sha",
        "catalog_digest_sha256",
        "exact_byte_count",
        "delivery_digest_sha256",
    ],
)
def test_plan_selection_essentials_cannot_be_null_typed(
    tmp_path: Path, field: str
) -> None:
    artifact = _artifact()
    plan_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "kd_session_plan"
    )
    plan_tool["outputSchema"]["properties"]["selection_set"]["properties"][field] = {
        "type": "null"
    }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


def test_plan_exact_byte_count_requires_the_transport_bound(tmp_path: Path) -> None:
    artifact = _artifact()
    plan_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "kd_session_plan"
    )
    plan_tool["outputSchema"]["properties"]["selection_set"]["properties"][
        "exact_byte_count"
    ].pop("maximum")
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


@pytest.mark.parametrize("property_name", ["consultation_ids", "gap_ids"])
def test_plan_receipt_id_arrays_must_remain_optional_unique_nonempty_strings(
    tmp_path: Path, property_name: str
) -> None:
    artifact = _artifact()
    plan_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "kd_session_plan"
    )
    plan_tool["inputSchema"]["required"].append(property_name)
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


@pytest.mark.parametrize("defect", ["duplicates", "empty_item"])
def test_plan_receipt_id_array_shape_is_substantive(
    tmp_path: Path, defect: str
) -> None:
    artifact = _artifact()
    plan_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "kd_session_plan"
    )
    schema = plan_tool["inputSchema"]["properties"]["consultation_ids"]
    if defect == "duplicates":
        schema["uniqueItems"] = False
    else:
        schema["items"].pop("minLength")
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


def test_action_discriminator_enum_values_must_be_reachable_strings(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    state_tool["inputSchema"]["properties"]["action"].update(
        {"type": "null"}
    )
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"TOOL_EFFECT_MISMATCH"}


@pytest.mark.parametrize("defect", ["required", "empty", "impossible"])
def test_action_receipt_must_be_optional_satisfiable_nonempty_string(
    tmp_path: Path, defect: str
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    if defect == "required":
        state_tool["inputSchema"]["required"].append("action_receipt")
    elif defect == "empty":
        state_tool["inputSchema"]["properties"]["action_receipt"] = {
            "type": "string"
        }
    else:
        state_tool["inputSchema"]["properties"]["action_receipt"] = {
            "type": "string",
            "not": {},
        }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


@pytest.mark.parametrize("defect", ["required", "not_object", "impossible"])
def test_runbook_impact_must_be_optional_and_admit_an_object(
    tmp_path: Path, defect: str
) -> None:
    artifact = _artifact()
    close_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "kd_session_close"
    )
    if defect == "required":
        close_tool["inputSchema"]["required"].append("runbook_impact")
    elif defect == "not_object":
        close_tool["inputSchema"]["properties"]["runbook_impact"] = {
            "type": "null"
        }
    else:
        close_tool["inputSchema"]["properties"]["runbook_impact"] = {
            "type": "object",
            "not": {},
        }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


@pytest.mark.parametrize(
    "missing_proof",
    ["receipt_argument", "typed_context_outcome", "action_context"],
)
def test_high_risk_tool_schema_must_prove_action_context_protocol(
    tmp_path: Path, missing_proof: str
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    if missing_proof == "receipt_argument":
        state_tool["inputSchema"]["properties"].pop("action_receipt")
    elif missing_proof == "typed_context_outcome":
        state_tool["outputSchema"]["properties"]["outcome"]["enum"].remove(
            "ACTION_CONTEXT_REQUIRED"
        )
    else:
        state_tool["outputSchema"]["properties"]["action_context"] = {
            "type": "object",
            "properties": {},
            "required": [],
        }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


def test_lifecycle_capability_must_match_plan_input_schema(tmp_path: Path) -> None:
    artifact = _artifact()
    plan_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "kd_session_plan"
    )
    plan_tool["inputSchema"]["properties"]["server_refs"] = plan_tool[
        "inputSchema"
    ]["properties"].pop("consultation_ids")
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)

    assert _codes(_verify(tmp_path, pin_path)) == {"LIFECYCLE_SCHEMA_MISMATCH"}


def test_rfc8032_second_vector_and_strict_negative_cases() -> None:
    public_key = bytes.fromhex(
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"
    )
    signature = bytes.fromhex(
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
    )
    message = b"\x72"
    assert dc.verify_ed25519(public_key, message, signature)

    scalar = int.from_bytes(signature[32:], "little")
    malleable_signature = signature[:32] + (scalar + dc._ED_L).to_bytes(32, "little")
    identity = b"\x01" + bytes(31)
    order_two = (dc._ED_Q - 1).to_bytes(32, "little")
    noncanonical_point = dc._ED_Q.to_bytes(32, "little")

    assert not dc.verify_ed25519(public_key, message, malleable_signature)
    assert not dc.verify_ed25519(identity, message, signature)
    assert not dc.verify_ed25519(order_two, message, signature)
    assert not dc.verify_ed25519(noncanonical_point, message, signature)
    assert not dc.verify_ed25519(public_key, message, identity + signature[32:])
    assert not dc.verify_ed25519(public_key, message, order_two + signature[32:])
    assert not dc.verify_ed25519(
        public_key, message, noncanonical_point + signature[32:]
    )


def test_missing_pin_fails_clearly(tmp_path: Path) -> None:
    report = _verify(tmp_path, tmp_path / "missing-pin.json")
    assert not report.ok
    assert _codes(report) == {"CONTRACT_PIN_MISSING"}


def test_duplicate_status_cannot_hide_attempted_active_runbook(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    directory = tmp_path / "runbooks"
    directory.mkdir()
    (directory / "ambiguous.md").write_text(
        "---\nrunbook_id: ambiguous\nstatus: ACTIVE\nstatus: DRAFT\n---\n\n# Ambiguous\n",
        encoding="utf-8",
    )
    assert "RUNBOOK_FRONTMATTER_INVALID" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_genuine_no_frontmatter_grandfathered_source_is_skipped(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    directory = tmp_path / "runbooks"
    directory.mkdir()
    (directory / "grandfathered.md").write_text(
        "# Grandfathered\n\nNo catalog metadata is claimed.\n", encoding="utf-8"
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings
    assert report.active_runbooks_checked == 0


def test_unclosed_attempted_active_frontmatter_fails(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    directory = tmp_path / "runbooks"
    directory.mkdir()
    (directory / "unclosed.md").write_text(
        "---\nrunbook_id: unclosed\nstatus: ACTIVE\n# no closing delimiter\n",
        encoding="utf-8",
    )
    assert "RUNBOOK_FRONTMATTER_INVALID" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_envelope_digest_mismatch_fails_before_use(tmp_path: Path) -> None:
    pin_path, pin, envelope = _write_fixture(tmp_path)
    artifact_path = tmp_path / pin["artifact_path"]
    envelope["artifact"]["policy_revision"] = "tampered"
    artifact_path.write_bytes(dc.canonical_json(envelope))
    assert _codes(_verify(tmp_path, pin_path)) == {"ENVELOPE_DIGEST_MISMATCH"}


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("handler_sha", "f" * 40, "HANDLER_SHA_MISMATCH"),
        ("proxy_release_identity", "wrong-proxy", "PROXY_IDENTITY_MISMATCH"),
        ("policy_revision", "wrong-policy", "POLICY_REVISION_MISMATCH"),
    ],
)
def test_pin_identity_must_match_artifact(
    tmp_path: Path, field: str, value: str, code: str
) -> None:
    pin_path, pin, _ = _write_fixture(tmp_path)
    pin[field] = value
    _rewrite_pin(pin_path, pin)
    assert _codes(_verify(tmp_path, pin_path)) == {code}


def test_artifact_digest_metadata_mismatch_fails_even_when_resigned(
    tmp_path: Path,
) -> None:
    pin_path, pin, envelope = _write_fixture(tmp_path)
    envelope["signature_metadata"]["artifact_sha256"] = "0" * 64
    signed = dc.canonical_json(
        {
            "artifact": envelope["artifact"],
            "signature_metadata": envelope["signature_metadata"],
        }
    )
    envelope["signature"] = _b64url(_sign(SEED, signed))
    _rewrite_envelope(tmp_path, pin_path, pin, envelope)
    assert _codes(_verify(tmp_path, pin_path)) == {"ARTIFACT_DIGEST_MISMATCH"}


def test_signature_mismatch_fails(tmp_path: Path) -> None:
    pin_path, pin, envelope = _write_fixture(tmp_path)
    signature = bytearray(base64.urlsafe_b64decode(envelope["signature"] + "=="))
    signature[0] ^= 1
    envelope["signature"] = _b64url(bytes(signature))
    _rewrite_envelope(tmp_path, pin_path, pin, envelope)
    assert _codes(_verify(tmp_path, pin_path)) == {"SIGNATURE_INVALID"}


def test_noncanonical_payload_fails_even_when_exact_bytes_are_pinned(
    tmp_path: Path,
) -> None:
    pin_path, pin, envelope = _write_fixture(tmp_path)
    artifact_path = tmp_path / pin["artifact_path"]
    raw = json.dumps(envelope, indent=2, sort_keys=True).encode()
    artifact_path.write_bytes(raw)
    pin["envelope_sha256"] = hashlib.sha256(raw).hexdigest()
    _rewrite_pin(pin_path, pin)
    assert _codes(_verify(tmp_path, pin_path)) == {"NONCANONICAL_ARTIFACT"}


def test_lone_surrogate_property_name_is_a_deterministic_jcs_failure(
    tmp_path: Path,
) -> None:
    pin_path, pin, _ = _write_fixture(tmp_path)
    artifact_path = tmp_path / pin["artifact_path"]
    envelope = _read_json(artifact_path)
    envelope[chr(0xD800)] = "invalid Unicode"
    raw = json.dumps(
        envelope, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode()
    artifact_path.write_bytes(raw)
    pin["envelope_sha256"] = hashlib.sha256(raw).hexdigest()
    _rewrite_pin(pin_path, pin)

    assert _codes(_verify(tmp_path, pin_path)) == {"JCS_INVALID_UNICODE"}


def test_noncanonical_signature_base64url_pad_bits_fail(tmp_path: Path) -> None:
    pin_path, pin, envelope = _write_fixture(tmp_path)
    envelope["signature"] = _noncanonical_b64url_equivalent(envelope["signature"])
    _rewrite_envelope(tmp_path, pin_path, pin, envelope)

    assert _codes(_verify(tmp_path, pin_path)) == {"INVALID_BASE64URL"}


def test_noncanonical_public_key_base64url_pad_bits_fail(tmp_path: Path) -> None:
    trust = _trust_store()
    key = trust["keys"][0]
    key["public_key_base64url"] = _noncanonical_b64url_equivalent(
        key["public_key_base64url"]
    )
    pin_path, _, _ = _write_fixture(tmp_path, trust_store=trust)

    assert _codes(_verify(tmp_path, pin_path)) == {"INVALID_BASE64URL"}


def test_unknown_key_fails(tmp_path: Path) -> None:
    def unknown(metadata: dict[str, Any]) -> None:
        metadata["kid"] = "not-trusted"

    pin_path, _, _ = _write_fixture(tmp_path, metadata_mutator=unknown)
    assert _codes(_verify(tmp_path, pin_path)) == {"UNKNOWN_SIGNING_KEY"}


def test_revoked_key_fails(tmp_path: Path) -> None:
    trust = _trust_store()
    trust["revoked_kids"] = [trust["keys"][0]["kid"]]
    pin_path, _, _ = _write_fixture(tmp_path, trust_store=trust)
    assert _codes(_verify(tmp_path, pin_path)) == {"REVOKED_SIGNING_KEY"}


def test_key_revoked_at_fails(tmp_path: Path) -> None:
    trust = _trust_store()
    trust["keys"][0]["revoked_at"] = "2026-07-30T00:00:00Z"
    pin_path, _, _ = _write_fixture(tmp_path, trust_store=trust)

    assert _codes(_verify(tmp_path, pin_path)) == {"REVOKED_SIGNING_KEY"}


def test_expired_key_fails(tmp_path: Path) -> None:
    trust = _trust_store(valid_until="2026-07-01T00:00:00Z")
    pin_path, _, _ = _write_fixture(tmp_path, trust_store=trust)
    assert _codes(_verify(tmp_path, pin_path)) == {"SIGNING_KEY_EXPIRED"}


def test_not_yet_valid_key_fails(tmp_path: Path) -> None:
    trust = _trust_store()
    trust["keys"][0]["valid_from"] = "2026-07-31T13:00:00Z"
    pin_path, _, _ = _write_fixture(
        tmp_path,
        trust_store=trust,
        metadata_mutator=lambda metadata: metadata.__setitem__(
            "issued_at", "2026-07-31T13:00:00Z"
        ),
    )

    assert _codes(_verify(tmp_path, pin_path)) == {"SIGNING_KEY_EXPIRED"}


def test_signature_issued_outside_key_window_fails(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(
        tmp_path,
        metadata_mutator=lambda metadata: metadata.__setitem__(
            "issued_at", "2024-12-31T23:59:59Z"
        ),
    )

    assert _codes(_verify(tmp_path, pin_path)) == {"SIGNATURE_TIME_INVALID"}


def test_signature_issued_in_future_fails(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(
        tmp_path,
        metadata_mutator=lambda metadata: metadata.__setitem__(
            "issued_at", "2026-08-01T00:00:00Z"
        ),
    )

    assert _codes(_verify(tmp_path, pin_path)) == {"SIGNATURE_TIME_INVALID"}


def test_signature_key_validity_metadata_mismatch_fails(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(
        tmp_path,
        metadata_mutator=lambda metadata: metadata.__setitem__(
            "key_valid_until", "2029-12-31T00:00:00Z"
        ),
    )

    assert _codes(_verify(tmp_path, pin_path)) == {"KEY_VALIDITY_MISMATCH"}


def test_overlapping_rotation_selects_signing_kid(tmp_path: Path) -> None:
    trust = _trust_store(valid_until="2026-07-31T11:00:00Z")
    second_public_key, _, _ = _public_key(SECOND_SEED)
    trust["keys"].append(
        {
            "kid": "gateway-prod-2026-b",
            "algorithm": "Ed25519",
            "public_key_base64url": _b64url(second_public_key),
            "issuer": "ai.market-gateway-deployer",
            "audiences": ["runbooks-ci"],
            "valid_from": "2026-07-01T00:00:00Z",
            "valid_until": "2030-01-01T00:00:00Z",
            "revoked_at": None,
        }
    )
    pin_path, _, _ = _write_fixture(
        tmp_path,
        trust_store=trust,
        metadata_mutator=lambda metadata: metadata.__setitem__(
            "issued_at", "2026-07-15T00:00:00Z"
        ),
        signing_seed=SECOND_SEED,
        signing_key_index=1,
    )

    assert _verify(tmp_path, pin_path).ok


def test_duplicate_rotation_kid_fails(tmp_path: Path) -> None:
    trust = _trust_store()
    duplicate = dict(trust["keys"][0])
    trust["keys"].append(duplicate)
    pin_path, _, _ = _write_fixture(tmp_path, trust_store=trust)

    assert _codes(_verify(tmp_path, pin_path)) == {"INVALID_TRUST_STORE"}


@pytest.mark.parametrize(
    "invalid_timestamp",
    [
        "20260102T030405Z",
        "2026-W01-5T03:04:05Z",
        "2026-01-02 03:04:05Z",
        "2026-01-02T03:04:05+00:00:30",
        "2026-02-30T03:04:05Z",
    ],
)
def test_signature_metadata_requires_strict_rfc3339(
    tmp_path: Path, invalid_timestamp: str
) -> None:
    pin_path, _, _ = _write_fixture(
        tmp_path,
        metadata_mutator=lambda metadata: metadata.__setitem__(
            "issued_at", invalid_timestamp
        ),
    )

    assert _codes(_verify(tmp_path, pin_path)) == {"CONTRACT_SCHEMA_INVALID"}


def test_trust_store_requires_strict_rfc3339(tmp_path: Path) -> None:
    trust = _trust_store()
    trust["keys"][0]["valid_from"] = "20250101T000000Z"
    pin_path, _, _ = _write_fixture(tmp_path, trust_store=trust)

    assert _codes(_verify(tmp_path, pin_path)) == {"INVALID_TIME"}


def test_naive_verification_clock_fails_closed(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    report = dc.validate_deployed_contract(
        tmp_path,
        pin_path=pin_path,
        schema_path=SCHEMA_PATH,
        now=NOW.replace(tzinfo=None),
        artifact_only=True,
    )

    assert _codes(report) == {"INVALID_TIME"}


def test_algorithm_substitution_is_schema_failure(tmp_path: Path) -> None:
    pin_path, pin, envelope = _write_fixture(tmp_path)
    envelope["signature_metadata"]["algorithm"] = "EdDSA"
    signed = dc.canonical_json(
        {
            "artifact": envelope["artifact"],
            "signature_metadata": envelope["signature_metadata"],
        }
    )
    envelope["signature"] = _b64url(_sign(SEED, signed))
    _rewrite_envelope(tmp_path, pin_path, pin, envelope)
    assert _codes(_verify(tmp_path, pin_path)) == {"CONTRACT_SCHEMA_INVALID"}


def test_internal_role_contradiction_fails_after_valid_signature(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    artifact["council"]["current_roles"]["retired"].append("ag")
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _codes(_verify(tmp_path, pin_path)) == {"ROLE_PROJECTION_CONTRADICTION"}


def test_hall_default_outside_valid_agents_fails(tmp_path: Path) -> None:
    artifact = _artifact()
    artifact["council"]["hall"]["default_agents"] = ["not-valid"]
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _codes(_verify(tmp_path, pin_path)) == {"ROLE_PROJECTION_CONTRADICTION"}


def test_source_identifier_must_name_handler_sha(tmp_path: Path) -> None:
    artifact = _artifact()
    source = next(
        item for item in artifact["source_identifiers"] if item["projection"] == "tools"
    )
    source["commit_sha"] = "4" * 40
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _codes(_verify(tmp_path, pin_path)) == {"SOURCE_PROJECTION_MISMATCH"}


def test_dispatch_and_hall_capability_sets_are_not_role_union(tmp_path: Path) -> None:
    artifact = _artifact()
    dispatch = next(
        tool for tool in artifact["tools"] if tool["name"] == "council_request"
    )
    dispatch["inputSchema"]["properties"]["agent"]["enum"] = [
        "cc",
        "kimi",
        "glm",
        "ag",
    ]
    hall_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "council_hall"
    )
    hall_tool["inputSchema"]["properties"]["agents"]["items"]["enum"] = [
        "mp",
        "ag",
        "glm",
    ]
    hall_tool["inputSchema"]["properties"]["agents"]["default"] = ["mp", "glm"]
    artifact["council"]["hall"]["valid_agents"] = ["glm", "ag", "mp"]
    artifact["council"]["hall"]["default_agents"] = ["glm", "mp"]
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _verify(tmp_path, pin_path).ok


def test_required_members_may_be_subset_of_valid_current_voters(tmp_path: Path) -> None:
    artifact = _artifact()
    artifact["council"]["required_members"] = ["cc", "glm"]
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _verify(tmp_path, pin_path).ok


def test_required_member_must_be_callable(tmp_path: Path) -> None:
    artifact = _artifact()
    dispatch = next(
        tool for tool in artifact["tools"] if tool["name"] == "council_request"
    )
    dispatch["inputSchema"]["properties"]["agent"]["enum"].remove("kimi")
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _codes(_verify(tmp_path, pin_path)) == {"COUNCIL_SCHEMA_MISMATCH"}


@pytest.mark.parametrize("surface", ["dispatch", "hall"])
def test_retired_member_must_not_remain_callable(tmp_path: Path, surface: str) -> None:
    artifact = _artifact()
    if surface == "dispatch":
        dispatch = next(
            tool for tool in artifact["tools"] if tool["name"] == "council_request"
        )
        dispatch["inputSchema"]["properties"]["agent"]["enum"].append("deepseek")
    else:
        hall_tool = next(
            tool for tool in artifact["tools"] if tool["name"] == "council_hall"
        )
        hall_tool["inputSchema"]["properties"]["agents"]["items"]["enum"].append(
            "deepseek"
        )
        artifact["council"]["hall"]["valid_agents"].append("deepseek")
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _codes(_verify(tmp_path, pin_path)) == {"ROLE_PROJECTION_CONTRADICTION"}


@pytest.mark.parametrize("surface", ["hall_enum", "hall_default"])
def test_council_linked_schema_projections_are_unique_string_lists(
    tmp_path: Path, surface: str
) -> None:
    artifact = _artifact()
    hall_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "council_hall"
    )
    if surface == "hall_enum":
        hall_tool["inputSchema"]["properties"]["agents"]["items"]["enum"] = [
            {"not": "a-member"}
        ]
    else:
        hall_tool["inputSchema"]["properties"]["agents"]["default"] = {"not": "a-list"}
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _codes(_verify(tmp_path, pin_path)) == {"COUNCIL_SCHEMA_MISMATCH"}


def test_external_schema_ref_is_rejected_before_argument_validation(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    state_tool["inputSchema"]["properties"]["key"] = {
        "$ref": "https://example.invalid/schema.json"
    }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    assert _codes(_verify(tmp_path, pin_path)) == {"EXTERNAL_SCHEMA_REF"}


def test_exact_tool_call_schema_passes(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: state_request(action=get, key=<server-key>)
```

## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, key]
        argument_values: {action: get, key: <server-key>}
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings
    assert report.tool_calls_checked == 2


def test_e_call_parser_accepts_json_float_array_and_object_literals(
    tmp_path: Path,
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: 'state_request(action=patch, key="x", patch={"dry_run":true,"agents":["cc","glm"]}, threshold=0.5)'
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings


def test_valid_bundled_local_ref_is_resolved_from_schema_root(tmp_path: Path) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    state_tool["inputSchema"]["properties"]["key_source"] = {
        "type": "string",
        "pattern": "^[a-z]+$",
    }
    state_tool["inputSchema"]["properties"]["key"] = {"$ref": "#/properties/key_source"}
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: state_request(action=get, key=valid)
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings


def test_pattern_constrained_placeholder_defers_only_value_validation(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    state_tool["inputSchema"]["properties"]["key"] = {
        "type": "string",
        "pattern": "^[A-F0-9]{40}$",
    }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: state_request(action=get, key=<sha>)
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings


def test_oneof_payload_placeholder_is_not_mistaken_for_discriminator(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    schema = state_tool["inputSchema"]
    schema["properties"].update(
        {
            "mode": {"type": "string", "enum": ["a", "b"]},
            "payload": {"type": "string", "minLength": 30},
            "count": {"type": "integer", "minimum": 1},
        }
    )
    schema["oneOf"] = [
        {
            "properties": {"mode": {"const": "a"}, "payload": {"type": "string"}},
            "required": ["mode", "payload"],
        },
        {
            "properties": {"mode": {"const": "b"}, "count": {"type": "integer"}},
            "required": ["mode", "count"],
        },
    ]
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: state_request(action=get, key=x, mode=a, payload=<text>)
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings


@pytest.mark.parametrize(
    ("endpoint", "code"),
    [
        ("state_request(action=delete, key=<server-key>)", "LITERAL_ARGUMENT_REJECTED"),
        ("state_request(action=get, bogus=<server-key>)", "UNKNOWN_ARGUMENT_KEY"),
        ("state_request(action=get)", "MISSING_REQUIRED_ARGUMENT"),
        ("state_request(action=get, imaginary=<placeholder>)", "UNKNOWN_ARGUMENT_KEY"),
        ("invented_tool(action=get, key=<server-key>)", "UNKNOWN_TOOL"),
    ],
)
def test_e_tool_enum_key_and_required_mismatches_fail(
    tmp_path: Path, endpoint: str, code: str
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: {endpoint}
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert code in _codes(report)


def test_expected_answer_literal_enum_is_checked(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, key]
        argument_values: {action: erase, key: value}
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert "LITERAL_ARGUMENT_REJECTED" in _codes(report)


@pytest.mark.parametrize(
    ("endpoint", "code"),
    [
        (
            "state_request(action=patch, key=<server-key>)",
            "MISSING_REQUIRED_ARGUMENT",
        ),
        (
            "state_request(action=get, key=<server-key>, patch={})",
            "ARGUMENT_COMBINATION_REJECTED",
        ),
        (
            "state_request(action=<operation>, key=<server-key>)",
            "CONDITIONAL_ARGUMENT_PLACEHOLDER",
        ),
    ],
)
def test_object_level_json_schema_constraints_cannot_be_bypassed(
    tmp_path: Path, endpoint: str, code: str
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: {endpoint}
```
""",
    )
    assert code in _codes(dc.validate_runbooks(tmp_path, contract))


@pytest.mark.parametrize(
    "values",
    [
        "{action: get, key: x, bogus: y}",
        "{action: get, key: x, patch: {}}",
    ],
)
def test_expected_answer_values_cannot_hide_outside_argument_keys(
    tmp_path: Path, values: str
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, key]
        argument_values: {values}
```
""",
    )
    assert "ARGUMENT_VALUE_WITHOUT_KEY" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_non_string_argument_value_key_reports_instead_of_crashing(
    tmp_path: Path,
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, key]
        argument_values: {1: bad, action: get, key: x}
```
""",
    )
    assert "MALFORMED_ARGUMENT_VALUES" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_dollar_placeholder_is_consistent_across_all_call_surfaces(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    state_tool = next(
        tool for tool in artifact["tools"] if tool["name"] == "state_request"
    )
    state_tool["inputSchema"]["properties"]["key"] = {
        "type": "string",
        "pattern": "^[A-F0-9]{40}$",
    }
    _refresh_schema_digest(artifact)
    pin_path = _resign_artifact(tmp_path, artifact)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: state_request(action=get, key=${SERVER_KEY})
```

## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, key]
        argument_values: {action: get, key: "${SERVER_KEY}"}
```

```yaml deployed-contract-call
tool: state_request
argument_keys: [action, key]
argument_values: {action: get, key: "${SERVER_KEY}"}
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings
    assert report.tool_calls_checked == 3


def test_matching_machine_readable_role_assertion_covers_current_prose(
    tmp_path: Path,
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    digest = contract.artifact_digest_sha256
    _write_runbook(
        tmp_path,
        f"""## §C. Architecture

```yaml deployed-contract-roles
contract_digest_sha256: {digest}
council:
  required_members: [cc, kimi, glm]
  valid_member_ids: [cc, kimi, glm]
  hall:
    valid_agents: [mp, cc, kimi, glm, ag]
    default_agents: [cc, kimi, glm]
current_roles:
  builders: [mp]
  voters: [cc, kimi, glm]
  paused: [ag]
  retired: [deepseek]
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings
    assert report.role_assertions_checked == 1


def test_correct_role_block_does_not_self_certify_contradictory_prose(
    tmp_path: Path,
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §D. Capability Map

DeepSeek is an active gate voter.

```yaml deployed-contract-roles
contract_digest_sha256: {contract.artifact_digest_sha256}
council:
  required_members: [cc, kimi, glm]
  valid_member_ids: [cc, kimi, glm]
  hall:
    valid_agents: [mp, cc, kimi, glm, ag]
    default_agents: [cc, kimi, glm]
current_roles:
  builders: [mp]
  voters: [cc, kimi, glm]
  paused: [ag]
  retired: [deepseek]
```
""",
    )
    assert "UNCHECKED_CURRENT_ROLE_CLAIM" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_unknown_member_current_roster_claim_is_not_silently_ignored(
    tmp_path: Path,
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        "## §D. Capability Map\n\nXAI is retired from the active roster.\n",
    )
    assert "UNCHECKED_CURRENT_ROLE_CLAIM" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_uncheckable_current_role_prose_is_a_failure(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path, "## §D. Capability Map\n\nThe required voter panel is CC only.\n"
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert "UNCHECKED_CURRENT_ROLE_CLAIM" in _codes(report)
    assert report.unchecked_claims


@pytest.mark.parametrize(
    "prose",
    [
        "The response body builder serializes exact bytes.",
        "The retired AIM-Node product is outside this process.",
        "A stale programme charter is retired after archival.",
    ],
)
def test_non_council_builder_and_retirement_prose_is_not_a_role_claim(
    tmp_path: Path, prose: str
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(tmp_path, f"## §D. Capability Map\n\n{prose}\n")
    report = dc.validate_runbooks(tmp_path, contract)
    assert "UNCHECKED_CURRENT_ROLE_CLAIM" not in _codes(report)


def test_role_claim_inside_acceptance_fence_is_not_masked(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    scenario: The Council voters are only CC and GLM.
    expected_answers:
      - kind: human_action
```
""",
    )
    assert "UNCHECKED_CURRENT_ROLE_CLAIM" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_role_assertion_contradiction_fails(tmp_path: Path) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §C. Architecture

The active gate voters are CC and GLM.

```yaml deployed-contract-roles
contract_digest_sha256: {contract.artifact_digest_sha256}
council:
  required_members: [cc, glm]
  valid_member_ids: [cc, glm]
  hall:
    valid_agents: [mp, cc, kimi, glm, ag]
    default_agents: [cc, glm]
current_roles:
  builders: [mp]
  voters: [cc, glm]
  paused: [ag]
  retired: [deepseek]
```
""",
    )
    assert "ROLE_ASSERTION_MISMATCH" in _codes(dc.validate_runbooks(tmp_path, contract))


@pytest.mark.parametrize(
    "markers",
    [
        "<!-- catalog:historical -->\nold\n",
        "<!-- /catalog:historical -->\n",
        (
            "<!-- catalog:historical -->\n"
            "<!-- catalog:historical -->\n"
            "<!-- /catalog:historical -->\n"
            "<!-- /catalog:historical -->\n"
        ),
    ],
)
def test_malformed_historical_markers_fail(tmp_path: Path, markers: str) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(tmp_path, f"## §C. Architecture\n\n{markers}")
    assert "MALFORMED_HISTORICAL_SPAN" in _codes(
        dc.validate_runbooks(tmp_path, contract)
    )


def test_balanced_historical_wrong_call_is_exempt_but_current_e_is_not(
    tmp_path: Path,
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §C. Architecture

<!-- catalog:historical -->
invented_tool(agent=retired)
<!-- /catalog:historical -->

## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: invented_tool(agent=current)
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    unknown = [finding for finding in report.findings if finding.code == "UNKNOWN_TOOL"]
    assert len(unknown) == 1


@pytest.mark.parametrize(
    "endpoint",
    [
        "external:: SQL SELECT date_trunc('day', created_at) FROM events",
        "external:: shell printf x; value=$(id -u)",
        "SQL SELECT date_trunc('day', created_at) FROM events",
        "shell printf x; value=$(id -u)",
    ],
)
def test_external_sql_and_shell_functions_are_not_gateway_tools(
    tmp_path: Path, endpoint: str
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: {endpoint}
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert "UNKNOWN_TOOL" not in _codes(report)
    assert "MALFORMED_TOOL_CALL" not in _codes(report)


@pytest.mark.parametrize(
    ("endpoint", "code"),
    [
        ("external::", "EMPTY_ENDPOINT_CLASSIFICATION"),
        (
            "external:: inspect the state_request result",
            "ENDPOINT_CLASSIFICATION_CONTRADICTION",
        ),
        ("gateway:: state_request action=get", "MALFORMED_ENDPOINT_CLASSIFICATION"),
        (
            "mixed:: state_request(action=get, key=x)",
            "MALFORMED_ENDPOINT_CLASSIFICATION",
        ),
        ("council_request result envelope", "UNCHECKED_EXECUTABLE"),
    ],
)
def test_endpoint_classification_cannot_create_an_unchecked_pass(
    tmp_path: Path, endpoint: str, code: str
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: {endpoint!r}
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert code in _codes(report)
    assert not report.ok


@pytest.mark.parametrize(
    "endpoint",
    [
        "gateway:: state_request(action=get, key=x)",
        "mixed:: shell command + state_request(action=get, key=x)",
    ],
)
def test_valid_gateway_and_mixed_classifications_pass(
    tmp_path: Path, endpoint: str
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        f"""## §E. Operate

```yaml operate
- id: E-01
  tool_or_endpoint: {endpoint}
```
""",
    )
    report = dc.validate_runbooks(tmp_path, contract)
    assert report.ok, report.findings


def test_i_scenario_structured_call_is_validated_not_only_expected_answer(
    tmp_path: Path,
) -> None:
    pin_path, _, _ = _write_fixture(tmp_path)
    contract = dc.verify_pinned_artifact(
        tmp_path, pin_path=pin_path, schema_path=SCHEMA_PATH, now=NOW
    )
    _write_runbook(
        tmp_path,
        """## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    scenario: "tool_or_endpoint: retired_tool(bogus=true). argument_sourcing: none."
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, key]
        argument_values: {action: get, key: x}
```
""",
    )
    assert "UNKNOWN_TOOL" in _codes(dc.validate_runbooks(tmp_path, contract))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0"),
        (-0.0, "0"),
        (1.0, "1"),
        (1e20, "100000000000000000000"),
        (1e21, "1e+21"),
        (1e-6, "0.000001"),
        (1e-7, "1e-7"),
        (333333333.33333329, "333333333.3333333"),
        (2e-3, "0.002"),
        (1e-27, "1e-27"),
        (5e-324, "5e-324"),
        (1.7976931348623157e308, "1.7976931348623157e+308"),
    ],
)
def test_canonicalizer_uses_rfc8785_number_format(value: float, expected: str) -> None:
    assert dc.canonical_json(value).decode() == expected


def test_module_entrypoint_reports_bootstrap_missing_pin(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = dc.main(
        ["--repo", str(tmp_path), "--schema", str(SCHEMA_PATH), "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["findings"][0]["code"] == "CONTRACT_PIN_MISSING"


def test_module_entrypoint_readiness_flag_is_deterministic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pin_path = _resign_artifact(tmp_path, _artifact(lifecycle_profile="legacy"))

    exit_code = dc.main(
        [
            "--repo",
            str(tmp_path),
            "--pin",
            str(pin_path),
            "--schema",
            str(SCHEMA_PATH),
            "--artifact-only",
            "--require-runbook-lifecycle-ready",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["runbook_lifecycle_readiness"] == "NOT_READY"
    assert [finding["code"] for finding in payload["findings"]] == [
        "RUNBOOK_LIFECYCLE_NOT_READY"
    ]
