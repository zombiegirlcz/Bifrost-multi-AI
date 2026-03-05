"""
Bifrost 2.0 — Brain modul: debata, review, konsenzus mezi AI modely
Používá Monica Multi-Chat — 1 stránka, 3 panely paralelně
"""
import asyncio
from pathlib import Path
from .session_manager import MonicaMultiSession
from .protocol import BifrostMessage, Phase, Status
from .utils.logger import log_phase, log_code
from .utils.diff_viewer import show_diff, find_consensus_score
from .config import TEMPLATES_DIR, BRAIN_ROUNDS, MONICA_PANELS


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if path.exists():
        return path.read_text()
    return "{task}"  # Fallback


class BrainCouncil:
    """Řídí debatu mezi AI mozky přes Monica multi-chat."""

    def __init__(self, monica: MonicaMultiSession):
        self.monica = monica
        self.solutions: dict[str, str] = {}  # key → poslední řešení
        self.history: list[BifrostMessage] = []

    async def run_debate(self, task: str) -> BifrostMessage:
        """Spustí kompletní debatu — N kol."""
        brain_count = len(MONICA_PANELS)
        log_phase("brain_round", "orchestrator",
                 f"Zahajuji debatu — {brain_count} mozky, {BRAIN_ROUNDS} kola")

        # === KOLO 1: Nezávislé návrhy ===
        await self._round_independent(task)

        # === KOLA 2+: Vzájemné review ===
        for round_num in range(2, BRAIN_ROUNDS + 1):
            await self._round_review(task, round_num)

        # === FINÁLNÍ KONSENZUS ===
        final = await self._build_consensus(task)
        return final

    async def _round_independent(self, task: str):
        """Kolo 1: Pošle úkol globálním inputem → všichni odpoví najednou."""
        log_phase("brain_round", "orchestrator", "Kolo 1: Nezávislé návrhy")

        template = load_template("brain_round1.txt")
        prompt = template.replace("{task}", task)

        responses = await self.monica.send_to_all(prompt)

        for key, response in responses.items():
            self.solutions[key] = response
            role = MONICA_PANELS[key]["role"]
            model = MONICA_PANELS[key]["model_label"]
            log_phase("brain_round", key,
                     f"🧠 {model} ({role}): {len(response)} znaků")

            self.history.append(BifrostMessage(
                phase=Phase.BRAIN_ROUND, status=Status.SUCCESS,
                source=key, content=response, round_number=1))

    async def _round_review(self, task: str, round_num: int):
        """Kola 2+: Každý mozek dostane JINÝ prompt podle role (per-panel)."""
        log_phase("brain_review", "orchestrator",
                 f"Kolo {round_num}: Vzájemné review (per-panel)")

        template = load_template("brain_review.txt")

        all_solutions = "\n\n---\n\n".join(
            f"### {MONICA_PANELS[k]['model_label']} ({MONICA_PANELS[k]['role']}):\n"
            f"```\n{v}\n```"
            for k, v in self.solutions.items()
        )

        # Každý mozek dostane jiný prompt podle role
        per_panel = {}
        for key, cfg in MONICA_PANELS.items():
            own = self.solutions.get(key, "")
            others = "\n\n---\n\n".join(
                f"### {MONICA_PANELS[k]['model_label']} ({MONICA_PANELS[k]['role']}):\n"
                f"```\n{v}\n```"
                for k, v in self.solutions.items() if k != key
            )
            role_prompt = cfg["system_prefix"]
            per_panel[key] = (
                f"[{cfg['role'].upper()}] {role_prompt}\n\n"
                + template
                    .replace("{task}", task)
                    .replace("{other_solutions}", others)
                    .replace("{own_solution}", own)
                    .replace("{round}", str(round_num))
            )

        responses = await self.monica.send_per_panel(per_panel)

        for key, response in responses.items():
            old = self.solutions.get(key, "")
            self.solutions[key] = response
            model = MONICA_PANELS[key]["model_label"]
            show_diff(old, response,
                     title=f"{model} — Kolo {round_num}")

            self.history.append(BifrostMessage(
                phase=Phase.BRAIN_ROUND, status=Status.SUCCESS,
                source=key, content=response, round_number=round_num))

    async def _build_consensus(self, task: str) -> BifrostMessage:
        """Finální kolo: sestav konsenzus z řešení všech mozků."""
        log_phase("brain_consensus", "orchestrator", "Sestavuji konsenzus")

        scores = find_consensus_score(self.solutions)
        log_phase("brain_consensus", "orchestrator", f"Skóre shody: {scores}")

        template = load_template("brain_consensus.txt")
        all_solutions = "\n\n===\n\n".join(
            f"### {MONICA_PANELS[k]['model_label']} ({MONICA_PANELS[k]['role']}) — FINÁLNÍ:\n"
            f"```\n{v}\n```"
            for k, v in self.solutions.items()
        )

        prompt = (template
                 .replace("{task}", task)
                 .replace("{all_solutions}", all_solutions)
                 .replace("{scores}", str(scores)))

        # Pošli konsenzus prompt → architekt (Claude) odpovídá jako vedoucí
        responses = await self.monica.send_to_all(prompt)
        lead_key = "claude"
        consensus_code = responses.get(lead_key, list(responses.values())[0])

        log_code(consensus_code, title="🤝 Konsenzuální kód")

        return BifrostMessage(
            phase=Phase.BRAIN_CONSENSUS,
            status=Status.SUCCESS,
            source="brain_council",
            content=consensus_code,
            round_number=BRAIN_ROUNDS,
            metadata={"consensus_scores": scores}
        )
