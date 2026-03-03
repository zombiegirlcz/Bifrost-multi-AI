"""
Bifrost 2.0 — Orchestrátor: řídí celý workflow
"""
import asyncio
from session_manager import SessionManager
from brain import BrainCouncil
from worker import Worker
from feedback_loop import FeedbackLoop
from protocol import BifrostMessage, Phase, Status
from utils.logger import log_phase, log_banner, log_code
from utils.file_manager import FileManager
from config import OUTPUT_DIR


class Orchestrator:
    """Hlavní řídící jednotka Bifrost 2.0."""

    def __init__(self):
        self.session_manager = SessionManager()
        self.file_manager = FileManager(OUTPUT_DIR)
        self.brain_council: BrainCouncil | None = None
        self.worker: Worker | None = None

    async def initialize(self):
        """Inicializuje všechny komponenty."""
        log_banner()
        log_phase("worker_build", "orchestrator", "Inicializuji sessions...")

        await self.session_manager.initialize()

        brains = self.session_manager.get_brains()
        copilot = self.session_manager.get_worker()

        if not brains:
            raise RuntimeError("Žádný mozek není připojen! Zkontroluj cookies.")

        if not copilot:
            raise RuntimeError("Copilot není připojen! Zkontroluj cookies.")

        self.brain_council = BrainCouncil(brains)
        self.worker = Worker(copilot, self.file_manager)

        log_phase("complete", "orchestrator",
                 f"Připojeno: {len(brains)} mozků + 1 dělník")

    async def run(self, task: str) -> BifrostMessage:
        """Spustí kompletní Bifrost workflow."""
        log_phase("brain_round", "orchestrator", f"Nový úkol: {task}")

        # Vytvoř projektový adresář
        project_dir = self.file_manager.create_project(task)
        log_phase("worker_build", "orchestrator", f"Projekt: {project_dir}")

        # === FÁZE 1: Mozky debatují ===
        log_phase("brain_round", "orchestrator", "═══ FÁZE 1: DEBATA MOZKŮ ═══")
        consensus = await self.brain_council.run_debate(task)

        await self.file_manager.save_iteration(0, "consensus", {
            "code": consensus.content,
            "metadata": consensus.metadata
        })

        # === FÁZE 2: Dělník staví ===
        log_phase("worker_build", "orchestrator", "═══ FÁZE 2: STAVBA ═══")
        build_result = await self.worker.build(consensus, task)

        await self.file_manager.save_iteration(0, "build", {
            "files": build_result.files_created,
            "dependencies": build_result.dependencies
        })

        # === FÁZE 3: Dělník testuje ===
        log_phase("worker_test", "orchestrator", "═══ FÁZE 3: TESTOVÁNÍ ═══")
        test_result = await self.worker.test(build_result)

        await self.file_manager.save_iteration(0, "test", {
            "status": test_result.status.value,
            "results": [
                {"name": t.test_name, "passed": t.passed, "error": t.error_message}
                for t in test_result.test_results
            ]
        })

        # === FÁZE 4: Feedback loop (pokud potřeba) ===
        if test_result.status != Status.SUCCESS:
            log_phase("fix_request", "orchestrator", "═══ FÁZE 4: OPRAVNÝ CYKLUS ═══")
            feedback = FeedbackLoop(self.brain_council, self.worker)
            final_result = await feedback.run(task, test_result)
        else:
            final_result = test_result

        # === VÝSLEDEK ===
        if final_result.status == Status.SUCCESS:
            log_phase("complete", "orchestrator",
                     "🎉 BIFROST DOKONČEN — Všechny testy prošly!")
        else:
            log_phase("error", "orchestrator",
                     "⚠️ BIFROST DOKONČEN — Některé problémy přetrvávají")

        # Ulož finální report
        await self.file_manager.save_code("BIFROST_REPORT.md",
            self._generate_report(task, final_result))

        return final_result

    async def shutdown(self):
        await self.session_manager.shutdown()

    def _generate_report(self, task: str, result: BifrostMessage) -> str:
        status_emoji = "✅" if result.status == Status.SUCCESS else "⚠️"
        
        test_lines = []
        for t in result.test_results:
            icon = "✅" if t.passed else "❌"
            test_lines.append(f"- {icon} {t.test_name}")
            if t.error_message:
                test_lines.append(f"  - Error: {t.error_message}")

        return f"""# 🌈 Bifrost 2.0 — Report

## {status_emoji} Status: {result.status.value.upper()}

## Zadání
{task}

## Výsledky testů
{chr(10).join(test_lines) if test_lines else "Žádné testy"}

## Iterace
{result.iteration}

## Soubory
{chr(10).join(f'- {f}' for f in result.files_created + result.files_modified)}
"""
