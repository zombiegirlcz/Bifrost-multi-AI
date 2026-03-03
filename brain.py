"""
Bifrost 2.0 — Brain modul: debata, review, konsenzus mezi AI modely
"""
import asyncio
from pathlib import Path
from session_manager import AISession
from protocol import BifrostMessage, Phase, Status
from utils.logger import log_phase, log_code
from utils.diff_viewer import show_diff, find_consensus_score
from config import TEMPLATES_DIR, BRAIN_ROUNDS


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if path.exists():
        return path.read_text()
    return "{task}"  # Fallback


class BrainCouncil:
    """Řídí debatu mezi AI mozky."""

    def __init__(self, brains: list[AISession]):
        self.brains = brains
        self.solutions: dict[str, str] = {}
        self.history: list[BifrostMessage] = []

    async def run_debate(self, task: str) -> BifrostMessage:
        """Spustí kompletní debatu — N kol."""
        log_phase("brain_round", "orchestrator",
                 f"Zahajuji debatu — {len(self.brains)} mozky, {BRAIN_ROUNDS} kola")

        # === KOLO 1: Nezávislé návrhy ===
        await self._round_independent(task)

        # === KOLA 2+: Vzájemné review ===
        for round_num in range(2, BRAIN_ROUNDS + 1):
            await self._round_review(task, round_num)

        # === FINÁLNÍ KONSENZUS ===
        final = await self._build_consensus(task)
        return final

    async def _round_independent(self, task: str):
        """Kolo 1: Každý mozek nezávisle navrhne řešení."""
        log_phase("brain_round", "orchestrator", "Kolo 1: Nezávislé návrhy")

        template = load_template("brain_round1.txt")
        prompt = template.replace("{task}", task)

        tasks = []
        for brain in self.brains:
            tasks.append(self._ask_brain(brain, prompt, round_number=1))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for brain, result in zip(self.brains, results):
            if isinstance(result, Exception):
                log_phase("error", brain.model_key, f"Chyba: {result}")
                self.solutions[brain.model_key] = f"ERROR: {result}"
            else:
                self.solutions[brain.model_key] = result

    async def _round_review(self, task: str, round_num: int):
        """Kola 2+: Každý mozek vidí řešení ostatních a vylepšuje své."""
        log_phase("brain_review", "orchestrator",
                 f"Kolo {round_num}: Vzájemné review")

        template = load_template("brain_review.txt")
        tasks = []

        for brain in self.brains:
            other_solutions = "\n\n---\n\n".join(
                f"### {k.upper()}:\n```\n{v}\n```"
                for k, v in self.solutions.items()
                if k != brain.model_key
            )

            prompt = (template
                     .replace("{task}", task)
                     .replace("{other_solutions}", other_solutions)
                     .replace("{own_solution}", self.solutions.get(brain.model_key, ""))
                     .replace("{round}", str(round_num)))

            tasks.append(self._ask_brain(brain, prompt, round_number=round_num))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for brain, result in zip(self.brains, results):
            if isinstance(result, Exception):
                log_phase("error", brain.model_key, f"Chyba v kole {round_num}: {result}")
            else:
                old = self.solutions.get(brain.model_key, "")
                self.solutions[brain.model_key] = result
                show_diff(old, result, title=f"{brain.name} — Kolo {round_num}")

    async def _build_consensus(self, task: str) -> BifrostMessage:
        """Finální kolo: vyber nejlepší části a sestav finální kód."""
        log_phase("brain_consensus", "orchestrator", "Sestavuji konsenzus")

        # Spočítej podobnost
        scores = find_consensus_score(self.solutions)
        log_phase("brain_consensus", "orchestrator",
                 f"Skóre shody: {scores}")

        template = load_template("brain_consensus.txt")
        all_solutions = "\n\n===\n\n".join(
            f"### {k.upper()} — FINÁLNÍ VERZE:\n```\n{v}\n```"
            for k, v in self.solutions.items()
        )

        prompt = (template
                 .replace("{task}", task)
                 .replace("{all_solutions}", all_solutions)
                 .replace("{scores}", str(scores)))

        # Použij prvního mozka pro finální merge
        lead_brain = self.brains[0]
        consensus_code = await lead_brain.send_message(prompt)

        log_code(consensus_code, title="🤝 Konsenzuální kód")

        return BifrostMessage(
            phase=Phase.BRAIN_CONSENSUS,
            status=Status.SUCCESS,
            source="brain_council",
            content=consensus_code,
            round_number=BRAIN_ROUNDS,
            metadata={"consensus_scores": scores}
        )

    async def _ask_brain(self, brain: AISession, prompt: str,
                         round_number: int) -> str:
        """Pošle prompt mozku a zaznamená do historie."""
        response = await brain.send_message(prompt)

        msg = BifrostMessage(
            phase=Phase.BRAIN_ROUND,
            status=Status.SUCCESS,
            source=brain.model_key,
            content=response,
            round_number=round_number
        )
        self.history.append(msg)
        return response
