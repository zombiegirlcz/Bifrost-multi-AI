"""Testy pro mailbox worker."""
import json
import pytest
from pathlib import Path


def test_mailbox_worker_import():
    """Ověř že MailboxWorker je importovatelný."""
    from worker_mailbox import MailboxWorker, QUEUE_DIR, PENDING_DIR, RESULTS_DIR
    assert QUEUE_DIR.name == "queue"
    assert PENDING_DIR.name == "pending"
    assert RESULTS_DIR.name == "results"


def test_copilot_executor_import():
    """Ověř že copilot_executor je importovatelný."""
    import copilot_executor
    assert hasattr(copilot_executor, "list_pending")
    assert hasattr(copilot_executor, "show_task")
    assert hasattr(copilot_executor, "write_result")


def test_worker_mode_config():
    """Ověř worker mode v konfiguraci."""
    import config
    assert hasattr(config, "WORKER_MODE")
    assert config.WORKER_MODE in ("mailbox", "playwright")


def test_mailbox_write_and_read(tmp_path):
    """Ověř zápis a čtení úkolu."""
    task_data = {
        "id": "test_001",
        "type": "build",
        "task": "Test task",
        "consensus_code": "print('hello')"
    }
    task_file = tmp_path / "test_001.json"
    task_file.write_text(json.dumps(task_data, ensure_ascii=False))

    loaded = json.loads(task_file.read_text())
    assert loaded["id"] == "test_001"
    assert loaded["type"] == "build"
    assert loaded["consensus_code"] == "print('hello')"


def test_executor_list_empty(tmp_path, monkeypatch):
    """Ověř že list_pending funguje s prázdnou frontou."""
    import copilot_executor
    monkeypatch.setattr(copilot_executor, "PENDING_DIR", tmp_path)
    tasks = copilot_executor.list_pending()
    assert tasks == []
