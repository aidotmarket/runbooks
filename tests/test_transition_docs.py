from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def test_boot_facing_open_protocol_does_not_present_attestation_as_truth() -> None:
    protocol = _read("session-open-protocol.md")
    normalized = " ".join(protocol.split())

    assert "RUNBOOK_CONTEXT_SELECTION_REQUIRED" in protocol
    assert "caller-authored proof of reading" in normalized
    assert "Bounded legacy compatibility" in normalized
    assert "never invent a path, section, synthesis, or runbook" in normalized
    assert "not evidence that a runbook update is useful" in normalized


def test_boot_facing_close_protocol_uses_server_measured_impact() -> None:
    protocol = _read("session-close-protocol.md")
    normalized = " ".join(protocol.split())

    assert "structured `runbook_impact`" in protocol
    assert "the server owns repository baselines" in normalized
    assert "does not force filler" in normalized
    assert "legacy `runbook_exit`" in protocol
    assert "A typed committed close receipt is the only success signal" in normalized


def test_legacy_gate_runbook_is_explicitly_non_authoritative_for_redesign() -> None:
    runbook = _read("runbook-first-gates.md")
    normalized = " ".join(runbook.split())

    assert "LEGACY COMPATIBILITY — DO NOT EXTEND" in runbook
    assert "forcing a reference, attestation, waiver, or close" in normalized
    assert "Do not enable another blocking surface" in normalized
    assert "server delivers immutable context first" in normalized


def test_active_session_owner_branches_on_the_exact_deployed_capability() -> None:
    runbook = _read("runbooks/peer-instance-discipline.md")
    normalized = " ".join(runbook.split())

    assert "Target branch — PLANNED and currently UNAVAILABLE" in runbook
    assert "Deployed compatibility branch — current and harmful" in runbook
    assert "RUNBOOK_CONTEXT_SELECTION_REQUIRED" in runbook
    assert "caller-authored `runbook_consultation`" in runbook
    assert "server-owned `runbook_impact`" in normalized
    assert "compatibility input, never evidence" in normalized


def test_dispatch_refs_are_conditional_on_the_signed_deployed_capability() -> None:
    runbook = _read("runbooks/agent-dispatch.md")
    normalized = " ".join(runbook.split())

    assert "inspect the exact signed deployed capability first" in normalized
    assert "only when that capability and the connected schema prove they exist" in normalized
    assert "caller-authored legacy path/section references" in normalized
    assert "compatibility input rather than evidence of reading" in normalized
    assert "runbook_refs=<deployed_contract_appropriate_refs>" in runbook
    assert "runbook_refs=<delivered_refs>" not in runbook
    assert "runbook_refs from gateway delivery" not in normalized


def test_active_owner_exposes_roster_mismatch_without_claiming_kimi_dispatch() -> None:
    runbook = _read("runbooks/peer-instance-discipline.md")
    normalized = " ".join(runbook.split())

    assert "connected `council_request` omits Kimi" in normalized
    assert "full-roster-dependent review and promotion as UNAVAILABLE" in normalized
    assert "required full panel is not currently callable" in normalized
    assert "koskadeux-mcp/tools/session.py:kd_session_open" not in runbook


def test_transition_protocol_references_resolve_or_name_live_state() -> None:
    open_protocol = _read("session-open-protocol.md")
    close_protocol = _read("session-close-protocol.md")

    assert "live `infra:opening-prompt` Living State entity" in open_protocol
    assert "`session-close-protocol.md`" in open_protocol
    assert "`session-registry-recovery.md`" in open_protocol
    assert "`build-queue-lifecycle.md`" in open_protocol
    assert "`session-open-protocol.md`" in close_protocol
    assert "`session-registry-recovery.md`" in close_protocol
    assert "`runbooks/session-open-protocol.md`" not in close_protocol
    assert "`runbooks/session-close-protocol.md`" not in open_protocol
    assert "`runbooks/session-registry-recovery.md`" not in open_protocol
    assert "`runbooks/session-registry-recovery.md`" not in close_protocol
    assert "`runbooks/build-queue-lifecycle.md`" not in open_protocol

    for relative in (
        "session-open-protocol.md",
        "session-close-protocol.md",
        "session-registry-recovery.md",
        "build-queue-lifecycle.md",
        "runbooks/peer-instance-discipline.md",
    ):
        assert (REPO_ROOT / relative).is_file(), relative
