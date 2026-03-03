"""
Bifrost 2.0 — Security Brain: role-based kyber-simulace (Red/Blue/Purple Team)
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
    return "{task}"


class SecurityBrainCouncil:
    """Řídí bezpečnostní simulaci s rolemi: Útočník, Obránce, Analytik."""

    ROLES = {
        "attacker": "🔴 Red Team (Útočník)",
        "defender": "🔵 Blue Team (Obránce)",
        "analyst":  "🟣 Purple Team (Analytik)",
    }

    def __init__(self, brains: list[AISession]):
        if len(brains) < 2:
            raise ValueError("Bezpečnostní simulace vyžaduje minimálně 2 mozky")

        self.brains = brains
        self.role_map: dict[str, str] = {}
        self.solutions: dict[str, str] = {}
        self.history: list[BifrostMessage] = []
        self._assign_roles()

    def _assign_roles(self):
        """Přiřadí role mozkům: 1=útočník, 2=obránce, 3+=analytik."""
        roles = list(self.ROLES.keys())
        for i, brain in enumerate(self.brains):
            role = roles[min(i, len(roles) - 1)]
            self.role_map[brain.model_key] = role
            log_phase("brain_round", brain.model_key,
                     f"Role: {self.ROLES[role]}")

    def get_role(self, brain: AISession) -> str:
        return self.role_map.get(brain.model_key, "analyst")

    async def run_security_sim(self, task: str) -> BifrostMessage:
        """Spustí kompletní bezpečnostní simulaci."""
        log_phase("brain_round", "orchestrator",
                 f"🛡️ Bezpečnostní simulace — {len(self.brains)} mozky, {BRAIN_ROUNDS} kola")

        # === KOLO 1: Útočník navrhuje exploit ===
        await self._round_attack(task)

        # === KOLO 2+: Obránce reaguje, útočník vylepšuje ===
        for round_num in range(2, BRAIN_ROUNDS + 1):
            await self._round_defense(task, round_num)

        # === FINÁLNÍ ANALÝZA ===
        final = await self._build_security_consensus(task)
        return final

    async def run_debate(self, task: str) -> BifrostMessage:
        """Alias pro kompatibilitu s FeedbackLoop."""
        return await self.run_security_sim(task)

    async def _round_attack(self, task: str):
        """Kolo 1: Útočník navrhuje exploit, ostatní analyzují cíl."""
        log_phase("brain_round", "orchestrator", "🔴 Kolo 1: Red Team — návrh útoku")

        template_attack = load_template("brain_security_round1.txt")
        tasks = []

        for brain in self.brains:
            role = self.get_role(brain)
            if role == "attacker":
                prompt = template_attack.replace("{task}", task)
            elif role == "defender":
                # Obránce v kole 1: analyzuj cíl, připrav obranu
                prompt = (
                    f"Jsi Blue Team specialista. Zadání: {task}\n\n"
                    "V tomto kole:\n"
                    "1. Analyzuj potenciální útočné vektory pro toto zadání\n"
                    "2. Připrav zranitelnou verzi aplikace pro testování\n"
                    "3. Navrhni základní obranné mechanismy\n"
                    "4. Připrav detekční pravidla (logování, SIEM)"
                )
            else:
                prompt = (
                    f"Jsi bezpečnostní analytik. Zadání: {task}\n\n"
                    "V tomto kole:\n"
                    "1. Identifikuj relevantní OWASP kategorie\n"
                    "2. Odhadni riziko a dopad\n"
                    "3. Navrhni testovací scénáře\n"
                    "4. Připrav hodnotící kritéria pro útok i obranu"
                )

            tasks.append(self._ask_brain(brain, prompt, round_number=1))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for brain, result in zip(self.brains, results):
            if isinstance(result, Exception):
                log_phase("error", brain.model_key, f"Chyba: {result}")
                self.solutions[brain.model_key] = f"ERROR: {result}"
            else:
                self.solutions[brain.model_key] = result

    async def _round_defense(self, task: str, round_num: int):
        """Kola 2+: Obránce vidí útok a reaguje, útočník se adaptuje."""
        log_phase("brain_review", "orchestrator",
                 f"🔵 Kolo {round_num}: Blue Team — obrana a adaptace")

        template_review = load_template("brain_security_review.txt")
        tasks = []

        for brain in self.brains:
            role = self.get_role(brain)
            other_solutions = "\n\n---\n\n".join(
                f"### {self.ROLES.get(self.role_map.get(k, 'analyst'), k).upper()} ({k}):\n```\n{v}\n```"
                for k, v in self.solutions.items()
                if k != brain.model_key
            )

            if role == "defender":
                prompt = (template_review
                         .replace("{task}", task)
                         .replace("{other_solutions}", other_solutions)
                         .replace("{round}", str(round_num)))
            elif role == "attacker":
                prompt = (
                    f"Jsi Red Team útočník. Kolo {round_num}. Zadání: {task}\n\n"
                    f"## REAKCE OBRÁNCE:\n{other_solutions}\n\n"
                    "## TVŮJ ÚKOL:\n"
                    "1. Analyzuj navrženou obranu\n"
                    "2. Najdi slabiny v obranných opatřeních\n"
                    "3. Navrhni VYLEPŠENÝ exploit, který obranu obejde\n"
                    "4. Pokud obrana funguje, navrhni alternativní útočný vektor"
                )
            else:
                prompt = (
                    f"Jsi bezpečnostní analytik. Kolo {round_num}. Zadání: {task}\n\n"
                    f"## PRŮBĚH SIMULACE:\n{other_solutions}\n\n"
                    "## TVŮJ ÚKOL:\n"
                    "1. Vyhodnoť efektivitu útoku vs. obrany\n"
                    "2. Identifikuj mezery v obraně\n"
                    "3. Navrhni další testovací scénáře\n"
                    "4. Aktualizuj CVSS hodnocení"
                )

            tasks.append(self._ask_brain(brain, prompt, round_number=round_num))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for brain, result in zip(self.brains, results):
            if isinstance(result, Exception):
                log_phase("error", brain.model_key, f"Chyba v kole {round_num}: {result}")
            else:
                old = self.solutions.get(brain.model_key, "")
                self.solutions[brain.model_key] = result
                show_diff(old, result,
                         title=f"{brain.name} ({self.ROLES[self.get_role(brain)]}) — Kolo {round_num}")

    async def _build_security_consensus(self, task: str) -> BifrostMessage:
        """Finální kolo: analytik vytvoří bezpečnostní report."""
        log_phase("brain_consensus", "orchestrator",
                 "🟣 Sestavuji bezpečnostní konsenzus")

        scores = find_consensus_score(self.solutions)
        log_phase("brain_consensus", "orchestrator", f"Skóre: {scores}")

        template = load_template("brain_security_consensus.txt")
        all_solutions = "\n\n===\n\n".join(
            f"### {self.ROLES.get(self.role_map.get(k, 'analyst'), k)} ({k}) — FINÁLNÍ:\n```\n{v}\n```"
            for k, v in self.solutions.items()
        )

        prompt = (template
                 .replace("{task}", task)
                 .replace("{all_solutions}", all_solutions)
                 .replace("{scores}", str(scores)))

        # Analytik (nebo první mozek) dělá finální merge
        analyst_brain = None
        for brain in self.brains:
            if self.get_role(brain) == "analyst":
                analyst_brain = brain
                break
        if not analyst_brain:
            analyst_brain = self.brains[0]

        consensus_code = await analyst_brain.send_message(prompt)
        log_code(consensus_code, title="🛡️ Bezpečnostní konsenzus")

        return BifrostMessage(
            phase=Phase.SECURITY_CONSENSUS,
            status=Status.SUCCESS,
            source="security_council",
            content=consensus_code,
            round_number=BRAIN_ROUNDS,
            metadata={
                "consensus_scores": scores,
                "roles": {k: self.ROLES[v] for k, v in self.role_map.items()}
            }
        )

    async def _ask_brain(self, brain: AISession, prompt: str,
                         round_number: int) -> str:
        response = await brain.send_message(prompt)
        msg = BifrostMessage(
            phase=Phase.SECURITY_ROUND,
            status=Status.SUCCESS,
            source=brain.model_key,
            content=response,
            round_number=round_number,
            metadata={"role": self.get_role(brain)}
        )
        self.history.append(msg)
        return response
