"""
Bifrost 2.0 — Standardizovaný komunikační protokol
Všechny zprávy mezi komponentami používají tento formát.
"""
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class Phase(str, Enum):
    TASK_INPUT = "task_input"
    BRAIN_ROUND = "brain_round"
    BRAIN_REVIEW = "brain_review"
    BRAIN_CONSENSUS = "brain_consensus"
    WORKER_BUILD = "worker_build"
    WORKER_TEST = "worker_test"
    WORKER_REPORT = "worker_report"
    FIX_REQUEST = "fix_request"
    FIX_APPLIED = "fix_applied"
    COMPLETE = "complete"
    ERROR = "error"
    # Security simulation fáze
    SECURITY_ROUND = "security_round"
    SECURITY_REVIEW = "security_review"
    SECURITY_CONSENSUS = "security_consensus"
    SECURITY_EXPLOIT = "security_exploit"
    SECURITY_DEFENSE = "security_defense"


class Status(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class TestResult:
    test_name: str
    passed: bool
    error_message: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None


@dataclass
class BifrostMessage:
    phase: Phase
    status: Status
    source: str                          # Kdo zprávu poslal (chatgpt/claude/copilot...)
    content: str                         # Hlavní obsah (kód, report, instrukce)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    round_number: int = 0
    iteration: int = 0
    files_created: list = field(default_factory=list)
    files_modified: list = field(default_factory=list)
    test_results: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "BifrostMessage":
        data = json.loads(json_str)
        data["phase"] = Phase(data["phase"])
        data["status"] = Status(data["status"])
        data["test_results"] = [TestResult(**t) for t in data.get("test_results", [])]
        return cls(**data)

    def summary(self) -> str:
        """Krátké shrnutí zprávy pro logy."""
        return (
            f"[{self.phase.value}] {self.source} → {self.status.value} "
            f"(round={self.round_number}, iter={self.iteration})"
        )
