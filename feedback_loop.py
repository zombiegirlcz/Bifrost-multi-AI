"""
Bifrost 2.0 — Feedback loop: error → mozky opraví → dělník aplikuje → retest
"""
from brain import BrainCouncil
from worker import Worker
from protocol import BifrostMessage, Phase, Status
from utils.logger import log_phase, log_error
from config import MAX_FIX_ITERATIONS


class FeedbackLoop:
    """Iterativní opravný cyklus."""

    def __init__(self, brain_council: BrainCouncil, worker: Worker):
        self.brains = brain_council
        self.worker = worker
        self.iterations: list[BifrostMessage] = []

    async def run(self, task: str, test_result: BifrostMessage) -> BifrostMessage:
        """Spustí feedback loop dokud testy neprojdou nebo nedojdou iterace."""

        for iteration in range(1, MAX_FIX_ITERATIONS + 1):
            # Zkontroluj jestli všechny testy prošly
            if test_result.status == Status.SUCCESS:
                log_phase("complete", "orchestrator",
                         f"✅ Všechny testy prošly! (iterace {iteration - 1})")
                return test_result

            log_phase("fix_request", "orchestrator",
                     f"🔧 Iterace {iteration}/{MAX_FIX_ITERATIONS}")

            # Připrav error report pro mozky
            failed_tests = [
                t for t in test_result.test_results if not t.passed
            ]
            error_report = "\n".join(
                f"- {t.test_name}: {t.error_message} "
                f"(soubor: {t.file}, řádek: {t.line})"
                for t in failed_tests
            )

            fix_prompt = f"""
## PŮVODNÍ ZADÁNÍ:
{task}

## CHYBY Z TESTŮ (iterace {iteration}):
{error_report}

## CELKOVÝ REPORT OD DĚLNÍKA:
{test_result.metadata.get('summary', 'N/A')}

## ÚKOL:
Opravte kód tak, aby všechny testy prošly.
Zaměřte se POUZE na chyby uvedené výše.
Vysvětlete co bylo špatně a jaká je oprava.
Pošlete KOMPLETNÍ opravený kód pro všechny dotčené soubory.
"""

            # Mozky opraví
            fix_result = await self.brains.run_debate(fix_prompt)

            # Dělník aplikuje opravu
            apply_result = await self.worker.apply_fix(
                fix_result.content, iteration
            )
            self.iterations.append(apply_result)

            # Aktualizuj test_result pro další iteraci
            test_result = apply_result

        # Vyčerpány iterace
        log_error("orchestrator",
                 f"Nedořešeno po {MAX_FIX_ITERATIONS} iteracích")
        return BifrostMessage(
            phase=Phase.ERROR,
            status=Status.ERROR,
            source="feedback_loop",
            content="Maximální počet iterací vyčerpán",
            iteration=MAX_FIX_ITERATIONS,
            test_results=test_result.test_results
        )
