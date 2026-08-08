from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def test_boot_facing_open_protocol_does_not_present_attestation_as_truth() -> None:
    protocol = _read("session-open-protocol.md")
    normalized = " ".join(protocol.split())

    assert "automatic server-delivered context" in normalized
    assert "one active form and no compatibility fallback" in normalized
    assert "Do not add a runbook path, section, reference" in normalized
    assert "complete ranked runbook context" in normalized
    assert "physically retired" in normalized


def test_boot_facing_close_protocol_uses_server_measured_impact() -> None:
    protocol = _read("session-close-protocol.md")
    normalized = " ".join(protocol.split())

    assert "has no runbook decision, impact, evidence" in normalized
    assert "the backend collects the session-open activation/obligation snapshot" in normalized
    assert "create or refresh one visible OPEN obligation but do not block COMMIT" in normalized
    assert "old `runbook_exit`/debt/waiver gate" in normalized
    assert "A typed signed `COMMITTED` receipt is the only success signal" in protocol


def test_active_gate_runbook_has_one_way_no_fallback_design() -> None:
    runbook = _read("runbooks/runbook-first-gates.md")
    normalized = " ".join(runbook.split())

    assert "retired caller-attestation gate is physically absent" in normalized
    assert "retired caller-attestation gate is physically absent" in normalized
    assert "Automatic first-plan context" in normalized
    assert "OPEN obligation" in runbook


def test_active_session_owner_branches_on_the_exact_deployed_capability() -> None:
    runbook = _read("runbooks/peer-instance-discipline.md")
    normalized = " ".join(runbook.split())

    assert "First action after `kd_session_open`" in runbook
    assert "one ordinary `kd_session_plan` request" in normalized
    assert "complete immutable context" in normalized
    assert "The server owns baselines" in normalized
    assert "There is no compatibility branch" in normalized


def test_dispatch_refs_are_conditional_on_the_signed_deployed_capability() -> None:
    runbook = _read("runbooks/agent-dispatch.md")
    normalized = " ".join(runbook.split())

    assert "Automatic context supplies" in normalized
    assert "callers do not" in normalized and "runbook" in normalized
    assert "AG and DeepSeek are inactive" in normalized
    assert "ordinary calls reject AG/DeepSeek" in normalized
    assert "runbook_refs=<delivered_refs>" not in runbook


def test_active_owner_exposes_roster_mismatch_without_claiming_kimi_dispatch() -> None:
    runbook = _read("runbooks/peer-instance-discipline.md")
    normalized = " ".join(runbook.split())

    assert "connected `council_request` omits Kimi" in normalized
    assert "roster-dependent work as UNAVAILABLE" in normalized
    assert "required full panel is not currently callable" in normalized
    assert "inactive AG/DeepSeek" in normalized
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
