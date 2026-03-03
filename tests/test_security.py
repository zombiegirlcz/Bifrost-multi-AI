"""Testy pro bezpečnostní modul Bifrost 2.0."""
import pytest
from protocol import Phase, Status, BifrostMessage


def test_security_phases_exist():
    """Ověř že bezpečnostní fáze existují v protokolu."""
    assert Phase.SECURITY_ROUND == "security_round"
    assert Phase.SECURITY_REVIEW == "security_review"
    assert Phase.SECURITY_CONSENSUS == "security_consensus"
    assert Phase.SECURITY_EXPLOIT == "security_exploit"
    assert Phase.SECURITY_DEFENSE == "security_defense"


def test_security_message_serialization():
    """Ověř serializaci bezpečnostní zprávy."""
    msg = BifrostMessage(
        phase=Phase.SECURITY_CONSENSUS,
        status=Status.SUCCESS,
        source="security_council",
        content="exploit code here",
        metadata={"roles": {"chatgpt": "attacker", "claude": "defender"}}
    )
    json_str = msg.to_json()
    restored = BifrostMessage.from_json(json_str)
    assert restored.phase == Phase.SECURITY_CONSENSUS
    assert restored.metadata["roles"]["chatgpt"] == "attacker"


def test_security_brain_import():
    """Ověř že SecurityBrainCouncil je importovatelný."""
    from security_brain import SecurityBrainCouncil
    assert SecurityBrainCouncil.ROLES["attacker"] == "🔴 Red Team (Útočník)"
    assert SecurityBrainCouncil.ROLES["defender"] == "🔵 Blue Team (Obránce)"
    assert SecurityBrainCouncil.ROLES["analyst"] == "🟣 Purple Team (Analytik)"


def test_security_orchestrator_import():
    """Ověř že SecurityOrchestrator je importovatelný."""
    from security_orchestrator import SecurityOrchestrator
    orch = SecurityOrchestrator()
    assert orch.security_council is None
    assert orch.worker is None


def test_security_mode_config():
    """Ověř security config."""
    import config
    assert hasattr(config, "SECURITY_MODE")
    # Default je False
    assert config.SECURITY_MODE is False
