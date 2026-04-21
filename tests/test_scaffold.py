from runbook_tools.scaffold.template import generate_scaffold, validate_system_name


def test_generate_scaffold_substitutes_system_name() -> None:
    scaffold = generate_scaffold("infisical-secrets", "sysadmin")

    assert "infisical-secrets" in scaffold


def test_generate_scaffold_preserves_placeholders() -> None:
    scaffold = generate_scaffold("infisical-secrets", "sysadmin")

    assert "<<PURPOSE_SENTENCE:required>>" in scaffold


def test_validate_system_name_accepts_valid() -> None:
    assert validate_system_name("infisical-secrets")
    assert validate_system_name("aim-node")


def test_validate_system_name_rejects_invalid() -> None:
    assert not validate_system_name("-bad")
    assert not validate_system_name("BAD")
    assert not validate_system_name("bad_underscore")
    assert not validate_system_name("a")

