"""
Bifrost 2.0 — Security Orchestrátor: řídí kyber-simulační workflow
"""
import asyncio
from session_manager import SessionManager
from security_brain import SecurityBrainCouncil
from worker import Worker
from feedback_loop import FeedbackLoop
from protocol import BifrostMessage, Phase, Status
from utils.logger import log_phase, log_banner, log_code
from utils.file_manager import FileManager
from config import OUTPUT_DIR


class SecurityOrchestrator:
    """Řídí bezpečnostní simulaci: útok → obrana → analýza → sandbox test."""

    def __init__(self):
        self.session_manager = SessionManager()
        self.file_manager = FileManager(OUTPUT_DIR)
        self.security_council: SecurityBrainCouncil | None = None
        self.worker: Worker | None = None

    async def initialize(self):
        """Inicializuje sessions a přiřadí role."""
        log_banner()
        log_phase("worker_build", "orchestrator",
                 "🛡️ Inicializuji bezpečnostní simulaci...")

        await self.session_manager.initialize()

        brains = self.session_manager.get_brains()
        copilot = self.session_manager.get_worker()

        if len(brains) < 2:
            raise RuntimeError(
                "Bezpečnostní simulace vyžaduje minimálně 2 mozky! "
                f"Připojeno: {len(brains)}. Zkontroluj cookies."
            )
        if not copilot:
            raise RuntimeError("Copilot není připojen! Zkontroluj cookies.")

        self.security_council = SecurityBrainCouncil(brains)
        self.worker = Worker(copilot, self.file_manager)

        roles_str = ", ".join(
            f"{k}: {v}" for k, v in self.security_council.role_map.items()
        )
        log_phase("complete", "orchestrator",
                 f"Připojeno: {len(brains)} mozků ({roles_str}) + 1 dělník")

    async def run(self, task: str) -> BifrostMessage:
        """Spustí kompletní bezpečnostní simulaci."""
        log_phase("brain_round", "orchestrator", f"🛡️ Nový bezpečnostní úkol: {task}")

        project_dir = self.file_manager.create_project(f"security_{task[:50]}")
        log_phase("worker_build", "orchestrator", f"Projekt: {project_dir}")

        # === FÁZE 1: Red vs Blue Team debata ===
        log_phase("brain_round", "orchestrator",
                 "═══ FÁZE 1: RED vs BLUE TEAM DEBATA ═══")
        consensus = await self.security_council.run_security_sim(task)

        await self.file_manager.save_iteration(0, "security_consensus", {
            "code": consensus.content,
            "roles": consensus.metadata.get("roles", {}),
            "scores": consensus.metadata.get("consensus_scores", {})
        })

        # === FÁZE 2: Worker staví sandbox ===
        log_phase("worker_build", "orchestrator",
                 "═══ FÁZE 2: STAVBA SANDBOXU ═══")
        build_result = await self._security_build(consensus, task)

        await self.file_manager.save_iteration(0, "security_build", {
            "files": build_result.files_created,
            "dependencies": build_result.dependencies
        })

        # === FÁZE 3: Exploit test ===
        log_phase("worker_test", "orchestrator",
                 "═══ FÁZE 3: EXPLOIT TESTOVÁNÍ ═══")
        test_result = await self._security_test(build_result)

        await self.file_manager.save_iteration(0, "security_test", {
            "status": test_result.status.value,
            "results": [
                {"name": t.test_name, "passed": t.passed, "error": t.error_message}
                for t in test_result.test_results
            ]
        })

        # === FÁZE 4: Feedback loop ===
        if test_result.status != Status.SUCCESS:
            log_phase("fix_request", "orchestrator",
                     "═══ FÁZE 4: BEZPEČNOSTNÍ OPRAVNÝ CYKLUS ═══")
            feedback = FeedbackLoop(self.security_council, self.worker)
            final_result = await feedback.run(task, test_result)
        else:
            final_result = test_result

        # === VÝSLEDEK ===
        if final_result.status == Status.SUCCESS:
            log_phase("complete", "orchestrator",
                     "🎉 SIMULACE DOKONČENA — Obrana úspěšná!")
        else:
            log_phase("error", "orchestrator",
                     "⚠️ SIMULACE DOKONČENA — Obrana má mezery")

        await self.file_manager.save_code("SECURITY_REPORT.md",
            self._generate_security_report(task, final_result))

        return final_result

    async def _security_build(self, consensus: BifrostMessage,
                               task: str) -> BifrostMessage:
        """Pošle bezpečnostní konsenzus workerovi k implementaci."""
        from brain import load_template
        template = load_template("worker_security_build.txt")
        prompt = (template
                 .replace("{task}", task)
                 .replace("{code}", consensus.content))

        return await self.worker.build(
            BifrostMessage(
                phase=Phase.SECURITY_CONSENSUS,
                status=Status.SUCCESS,
                source="security_council",
                content=prompt
            ),
            task
        )

    async def _security_test(self, build_result: BifrostMessage) -> BifrostMessage:
        """Spustí bezpečnostní testy — exploit → obrana → ověření."""
        return await self.worker.test(build_result)

    async def shutdown(self):
        await self.session_manager.shutdown()

    def _generate_security_report(self, task: str,
                                   result: BifrostMessage) -> str:
        status_emoji = "✅" if result.status == Status.SUCCESS else "⚠️"

        test_lines = []
        for t in result.test_results:
            icon = "✅" if t.passed else "❌"
            test_lines.append(f"- {icon} {t.test_name}")
            if t.error_message:
                test_lines.append(f"  - Detail: {t.error_message}")

        return f"""# 🛡️ Bifrost 2.0 — Bezpečnostní Report

## {status_emoji} Status: {result.status.value.upper()}

## Zadání
{task}

## Bezpečnostní testy
{chr(10).join(test_lines) if test_lines else "Žádné testy"}

## Iterace
{result.iteration}

## Soubory
{chr(10).join(f'- {f}' for f in result.files_created + result.files_modified)}

## Metodologie
- Red Team: Penetrační testování, PoC exploity
- Blue Team: Detekce, oprava, WAF pravidla
- Purple Team: Analýza, hodnocení, doporučení

---
*Vygenerováno Bifrost 2.0 Security Module*
"""
