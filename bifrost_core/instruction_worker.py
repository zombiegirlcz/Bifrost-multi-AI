from pathlib import Path
from .protocol import BifrostMessage, Phase, Status
from .utils.logger import log_phase
from .utils.file_manager import FileManager


class InstructionWorker:
    """Náhradní worker: nevykonává kód, jen připraví instrukce pro Copilota."""

    def __init__(self, file_manager: FileManager):
        self.fm = file_manager

    async def build(self, consensus: BifrostMessage, task: str) -> BifrostMessage:
        log_phase("worker_build", "instructions", "Vytvářím instrukce pro Copilota")
        instructions = self._format_instructions(consensus.content, task)
        path = self.fm.project_dir / "instructions_for_copilot.txt"
        path.write_text(instructions, encoding="utf-8")
        return BifrostMessage(
            phase=Phase.WORKER_BUILD,
            status=Status.PARTIAL,
            source="instruction_worker",
            content=instructions,
            files_created=[str(path)],
            dependencies=[],
            metadata={
                "instructions_file": str(path),
                "worker_type": "instructions",
            }
        )

    async def test(self, build_result: BifrostMessage) -> BifrostMessage:
        log_phase("worker_test", "instructions", "Testy nepouštím, čekám na Copilota")
        meta = {**build_result.metadata, "worker_type": "instructions"}
        return BifrostMessage(
            phase=Phase.WORKER_TEST,
            status=Status.PARTIAL,
            source="instruction_worker",
            content="Testy neproběhly – Copilot musí projekt postavit a otestovat.",
            files_created=build_result.files_created,
            dependencies=build_result.dependencies,
            test_results=[],
            metadata=meta,
        )

    def _format_instructions(self, consensus_code: str, task: str) -> str:
        return (
            "INSTRUKCE PRO COPILOTA\n"
            "=======================\n\n"
            f"Úkol: {task}\n\n"
            "Postup:\n"
            "1) Vezmi přiložený konsenzuální návrh (sekce níže) a vytvoř podle něj kompletní projekt.\n"
            "2) Pro každý soubor vypiš plný obsah (kód), včetně testů.\n"
            "3) Uveď závislosti (pip/npm) a příkaz pro spuštění + testy.\n"
            "4) Pokud jde o security mode, zahrň exploit, defense, report.\n"
            "\n"
            "Konsenzuální kód:\n"
            "-----------------\n"
            f"{consensus_code}\n"
        )
