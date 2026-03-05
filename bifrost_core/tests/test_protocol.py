"""Testy pro komunikační protokol."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1].parent))

import pytest
from bifrost_core.protocol import BifrostMessage, Phase, Status, TestResult


def test_message_creation():
    msg = BifrostMessage(
        phase=Phase.BRAIN_ROUND,
        status=Status.SUCCESS,
        source="chatgpt",
        content="print('hello')"
    )
    assert msg.phase == Phase.BRAIN_ROUND
    assert msg.source == "chatgpt"


def test_message_serialization():
    msg = BifrostMessage(
        phase=Phase.WORKER_TEST,
        status=Status.PARTIAL,
        source="copilot",
        content="test output",
        test_results=[
            TestResult("test_1", True),
            TestResult("test_2", False, "AssertionError", "app.py", 10)
        ]
    )
    json_str = msg.to_json()
    restored = BifrostMessage.from_json(json_str)
    assert restored.source == "copilot"
    assert len(restored.test_results) == 2
    assert restored.test_results[1].passed is False


def test_message_summary():
    msg = BifrostMessage(
        phase=Phase.COMPLETE,
        status=Status.SUCCESS,
        source="orchestrator",
        content="done"
    )
    summary = msg.summary()
    assert "complete" in summary
    assert "orchestrator" in summary
