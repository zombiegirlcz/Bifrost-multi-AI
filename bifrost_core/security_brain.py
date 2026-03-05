"""
Bifrost 2.0 — Security Brain: role-based kyber-simulace (Red/Blue/Purple Team)
Používá Monica Multi-Chat — 3 panely: Red=GPT, Blue=Claude, Purple=Gemini
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
    return "{task}"


# Mapování Monica panelů na bezpečnostní role
SECURITY_ROLES = {
    "gpt":    {"role": "attacker", "label": "🔴 Red Team (Útočník)"},
    "claude": {"role": "defender", "label": "🔵 Blue Team (Obránce)"},
    "gemini": {"role": "analyst",  "label": "🟣 Purple Team (Analytik)"},
}


class SecurityBrainCouncil:
    """Řídí bezpečnostní simulaci přes Monica multi-chat."""

    def __init__(self, monica: MonicaMultiSession):
        self.monica = monica
        self.solutions: dict[str, str] = {}
        self.history: list[BifrostMessage] = []

        for key, sec_role in SECURITY_ROLES.items():
            log_phase("brain_round", key,
                     f"Role: {sec_role['label']}")

    async def run_security_sim(self, task: str) -> BifrostMessage:
        """Spustí kompletní bezpečnostní simulaci."""
        log_phase("brain_round", "orchestrator",
                 f"🛡️ Bezpečnostní simulace — 3 mozky, {BRAIN_ROUNDS} kola")

        await self._round_attack(task)

        for round_num in range(2, BRAIN_ROUNDS + 1):
            await self._round_defense(task, round_num)

        final = await self._build_security_consensus(task)
        return final

    async def run_debate(self, task: str) -> BifrostMessage:
        """Alias pro kompatibilitu s FeedbackLoop."""
        return await self.run_security_sim(task)

    async def _round_attack(self, task: str):
        """Kolo 1: Pošle ROLE-SPECIFICKÝ prompt každému panelu."""
        log_phase("brain_round", "orchestrator", "🔴 Kolo 1: Red Team — návrh útoku")

        # Každý panel dostane svou roli
        role_templates = {
            "gpt":    load_template("brain_security_round1.txt"),       # Red Team
            "claude": load_template("brain_security_round1_blue.txt"),  # Blue Team
            "gemini": load_template("brain_security_round1_purple.txt"),# Purple Team
        }

        messages = {}
        for key, template in role_templates.items():
            messages[key] = template.replace("{task}", task)

        responses = await self.monica.send_per_panel(messages)
        for key, response in responses.items():
            self.solutions[key] = response
            self.history.append(BifrostMessage(
                phase=Phase.SECURITY_ROUND, status=Status.SUCCESS,
                source=key, content=response, round_number=1,
                metadata={"role": SECURITY_ROLES[key]["role"]}))

    async def _round_defense(self, task: str, round_num: int):
        """Kola 2+: Každý reaguje podle SVÉ role na výstupy ostatních."""
        log_phase("brain_review", "orchestrator",
                 f"🔵 Kolo {round_num}: Blue Team — obrana a adaptace")

        all_solutions = "\n\n---\n\n".join(
            f"### {SECURITY_ROLES[k]['label']} ({k}):\n```\n{v}\n```"
            for k, v in self.solutions.items()
        )

        # Per-panel prompty s rolí
        role_instructions = {
            "gpt":    "🔴 RED TEAM: Vylepši exploit. Obejdi obranu Blue Teamu. Najdi slabiny v jejich řešení.",
            "claude": "🔵 BLUE TEAM: Oprav slabiny. Zesil obranu proti útoku Red Teamu. Implementuj nové mitigace.",
            "gemini": "🟣 PURPLE TEAM: Vyhodnoť efektivitu útoku vs. obrany. Kdo vyhrává? Co schází?",
        }

        messages = {}
        for key, instruction in role_instructions.items():
            messages[key] = (
                f"Kolo {round_num}. Zadání: {task}\n\n"
                f"## TVÁ ROLE:\n{instruction}\n\n"
                f"## PŘEDCHOZÍ KOLO:\n{all_solutions}\n\n"
                "Odpověz kompletním řešením podle své role."
            )

        responses = await self.monica.send_per_panel(messages)
        for key, response in responses.items():
            old = self.solutions.get(key, "")
            self.solutions[key] = response
            show_diff(old, response,
                     title=f"{SECURITY_ROLES[key]['label']} — Kolo {round_num}")
            self.history.append(BifrostMessage(
                phase=Phase.SECURITY_ROUND, status=Status.SUCCESS,
                source=key, content=response, round_number=round_num,
                metadata={"role": SECURITY_ROLES[key]["role"]}))

    async def _build_security_consensus(self, task: str) -> BifrostMessage:
        """Finální: analytik (Gemini) vytvoří bezpečnostní report."""
        log_phase("brain_consensus", "orchestrator",
                 "🟣 Sestavuji bezpečnostní konsenzus")

        scores = find_consensus_score(self.solutions)
        log_phase("brain_consensus", "orchestrator", f"Skóre: {scores}")

        template = load_template("brain_security_consensus.txt")

        # Truncate each solution to fit per-panel input limits (~8k per solution)
        MAX_SOL_LEN = 8000
        truncated = {}
        for k, v in self.solutions.items():
            truncated[k] = v[:MAX_SOL_LEN] + "\n...[zkráceno]" if len(v) > MAX_SOL_LEN else v

        all_solutions = "\n\n===\n\n".join(
            f"### {SECURITY_ROLES[k]['label']} — FINÁLNÍ:\n```\n{truncated[k]}\n```"
            for k in truncated
        )

        prompt = (template
                 .replace("{task}", task)
                 .replace("{all_solutions}", all_solutions)
                 .replace("{scores}", str(scores)))

        # Use send_per_panel — global textarea can't handle 100k+ chars
        messages = {k: prompt for k in SECURITY_ROLES}
        responses = await self.monica.send_per_panel(messages)
        # Analytik (Gemini) je hlavní hlas pro konsenzus
        consensus = responses.get("gemini", list(responses.values())[0])
        log_code(consensus, title="🛡️ Bezpečnostní konsenzus")

        return BifrostMessage(
            phase=Phase.SECURITY_CONSENSUS,
            status=Status.SUCCESS,
            source="security_council",
            content=consensus,
            round_number=BRAIN_ROUNDS,
            metadata={
                "consensus_scores": scores,
                "roles": {k: v["label"] for k, v in SECURITY_ROLES.items()}
            }
        )
