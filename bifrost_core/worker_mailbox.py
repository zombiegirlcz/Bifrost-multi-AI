"""
Bifrost 2.0 — Worker Mailbox: file-based komunikace s CLI Copilotem

Flow:
1. Orchestrátor zapíše úkol do queue/pending/task_XXX.json
2. CLI Copilot (nebo copilot_executor.py) ho vyzvedne a provede
3. Výsledek zapíše do queue/results/task_XXX.json
4. Orchestrátor si vyzvedne výsledek a pokračuje
"""
import asyncio
import json
import time
from pathlib import Path
from .protocol import BifrostMessage, Phase, Status, TestResult
from .utils.logger import log_phase, log_error
from .utils.file_manager import FileManager
from .config import BASE_DIR


QUEUE_DIR = BASE_DIR / "queue"
PENDING_DIR = QUEUE_DIR / "pending"
RESULTS_DIR = QUEUE_DIR / "results"
POLL_INTERVAL = 2.0   # Jak často kontrolovat výsledky (sekundy)
TASK_TIMEOUT = 600.0   # Max čekání na výsledek (10 minut)


def _ensure_dirs():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class MailboxWorker:
    """Worker, který komunikuje přes soubory místo Playwright."""

    def __init__(self, file_manager: FileManager):
        self.fm = file_manager
        self._task_counter = 0
        _ensure_dirs()

    def _next_task_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter:03d}"

    async def build(self, consensus: BifrostMessage, task: str) -> BifrostMessage:
        """Zapíše build úkol do queue a čeká na výsledek."""
        task_id = self._next_task_id()
        log_phase("worker_build", "mailbox",
                 f"📋 Zapisuji úkol {task_id} do fronty...")

        task_data = {
            "id": task_id,
            "type": "build",
            "task": task,
            "consensus_code": consensus.content,
            "instructions": (
                "1. Analyzuj kód od architektů\n"
                "2. Vytvoř všechny potřebné soubory\n"
                "3. Nainstaluj závislosti\n"
                "4. Ověř že se kód spustí bez chyb\n"
                "5. Zapiš výsledek do results/"
            )
        }

        self._write_task(task_id, task_data)
        log_phase("worker_build", "mailbox",
                 f"⏳ Čekám na CLI Copilota — úkol: queue/pending/{task_id}.json")

        result_data = await self._wait_for_result(task_id)
        return self._parse_build_result(result_data)

    async def test(self, build_result: BifrostMessage) -> BifrostMessage:
        """Zapíše test úkol do queue a čeká na výsledek."""
        task_id = self._next_task_id()
        log_phase("worker_test", "mailbox",
                 f"📋 Zapisuji test úkol {task_id}...")

        task_data = {
            "id": task_id,
            "type": "test",
            "files": build_result.files_created,
            "test_command": build_result.metadata.get("test_command", "python -m pytest"),
            "instructions": (
                "1. Spusť testy pomocí příkazu výše\n"
                "2. Zapiš skutečné výsledky (ne simulované!)\n"
                "3. Pokud testy padají, zapiš přesné chybové hlášky\n"
                "4. Zapiš výsledek do results/"
            )
        }

        self._write_task(task_id, task_data)
        log_phase("worker_test", "mailbox",
                 f"⏳ Čekám na CLI Copilota — úkol: queue/pending/{task_id}.json")

        result_data = await self._wait_for_result(task_id)
        return self._parse_test_result(result_data)

    async def apply_fix(self, fix_code: str, iteration: int) -> BifrostMessage:
        """Zapíše fix úkol do queue a čeká na výsledek."""
        task_id = self._next_task_id()
        log_phase("fix_applied", "mailbox",
                 f"📋 Zapisuji opravu {task_id} (iterace {iteration})...")

        task_data = {
            "id": task_id,
            "type": "fix",
            "fix_code": fix_code,
            "iteration": iteration,
            "instructions": (
                "1. Aplikuj opravu do příslušných souborů\n"
                "2. Spusť testy znovu\n"
                "3. Zapiš skutečné výsledky\n"
                "4. Zapiš výsledek do results/"
            )
        }

        self._write_task(task_id, task_data)
        log_phase("fix_applied", "mailbox",
                 f"⏳ Čekám na CLI Copilota — úkol: queue/pending/{task_id}.json")

        result_data = await self._wait_for_result(task_id)
        return self._parse_fix_result(result_data, iteration)

    def _write_task(self, task_id: str, data: dict):
        """Zapíše úkol do pending/."""
        path = PENDING_DIR / f"{task_id}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    async def _wait_for_result(self, task_id: str) -> dict:
        """Čeká dokud se neobjeví výsledek v results/."""
        result_path = RESULTS_DIR / f"{task_id}.json"
        elapsed = 0.0

        while elapsed < TASK_TIMEOUT:
            if result_path.exists():
                try:
                    data = json.loads(result_path.read_text())
                    log_phase("complete", "mailbox",
                             f"✅ Výsledek {task_id} přijat!")
                    return data
                except json.JSONDecodeError:
                    pass  # Soubor se ještě zapisuje

            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            # Periodicky připomeň
            if elapsed % 30 == 0:
                log_phase("worker_build", "mailbox",
                         f"⏳ Stále čekám na {task_id}... ({int(elapsed)}s)")

        log_error("mailbox", f"Timeout — {task_id} nedoručen za {TASK_TIMEOUT}s")
        return {"error": f"Timeout po {TASK_TIMEOUT}s"}

    def _parse_build_result(self, data: dict) -> BifrostMessage:
        files = list(data.get("files_created", {}).keys())
        # Zapiš soubory pokud je worker poslal jako obsah (sync, aby nespadl běžící event loop)
        for filepath, content in data.get("files_created", {}).items():
            if isinstance(content, str) and self.fm.project_dir:
                target = self.fm.project_dir / filepath
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

        return BifrostMessage(
            phase=Phase.WORKER_BUILD,
            status=Status.SUCCESS if not data.get("error") else Status.ERROR,
            source="copilot_cli",
            content=data.get("summary", ""),
            files_created=files,
            dependencies=data.get("dependencies", []),
            metadata={
                "run_command": data.get("run_command", ""),
                "test_command": data.get("test_command", ""),
                "worker_type": "mailbox"
            }
        )

    def _parse_test_result(self, data: dict) -> BifrostMessage:
        test_results = [
            TestResult(**t) for t in data.get("test_results", [])
        ]
        all_passed = all(t.passed for t in test_results)

        return BifrostMessage(
            phase=Phase.WORKER_TEST,
            status=Status.SUCCESS if all_passed else Status.PARTIAL,
            source="copilot_cli",
            content=data.get("summary", ""),
            test_results=test_results,
            metadata={
                "overall_status": data.get("overall_status", "unknown"),
                "summary": data.get("summary", ""),
                "worker_type": "mailbox"
            }
        )

    def _parse_fix_result(self, data: dict, iteration: int) -> BifrostMessage:
        test_results = [
            TestResult(**t) for t in data.get("test_results", [])
        ]
        all_passed = all(t.passed for t in test_results)

        return BifrostMessage(
            phase=Phase.FIX_APPLIED,
            status=Status.SUCCESS if all_passed else Status.PARTIAL,
            source="copilot_cli",
            content=data.get("summary", ""),
            files_modified=list(data.get("files_modified", [])),
            iteration=iteration,
            test_results=test_results
        )
