#!/usr/bin/env python3
"""
🌈 Bifrost 2.0 — entrypoint
Podpora coding i security režimu, volba workeru (instructions/mailbox).
"""
import asyncio
import click
from pathlib import Path
from .orchestrator import Orchestrator
from .security_orchestrator import SecurityOrchestrator
from .utils.logger import log_phase, log_error, console

BASE_DIR = Path(__file__).parent


@click.command()
@click.option("--task", "-t", prompt="📝 Zadej úkol", help="Co má tým vyřešit")
@click.option("--mode", "-m", default="coding", type=click.Choice(["coding", "security"]),
              help="Režim: coding (výchozí) nebo security (Red/Blue/Purple simulace)")
@click.option("--rounds", "-r", default=3, help="Počet kol debaty (default: 3)")
@click.option("--max-fix", "-f", default=5, help="Max opravných iterací (default: 5)")
@click.option("--worker", "-w", default="mailbox",
              type=click.Choice(["instructions", "mailbox"]),
              help="Worker: mailbox (default, Copilot CLI) nebo instructions (pouze návod)")
@click.option("--verbose", "-v", is_flag=True, help="Podrobný výstup")
def main(task: str, mode: str, rounds: int, max_fix: int, worker: str, verbose: bool):
    """Spusť Bifrost orchestraci (coding nebo security)."""

    from . import config
    config.BRAIN_ROUNDS = rounds
    config.MAX_FIX_ITERATIONS = max_fix
    config.WORKER_MODE = worker
    config.SECURITY_MODE = mode == "security"

    try:
        asyncio.run(run_bifrost(task, mode, verbose))
    finally:
        pass


async def run_bifrost(task: str, mode: str, verbose: bool):
    from . import config

    is_security = mode == "security"
    orchestrator = SecurityOrchestrator() if is_security else Orchestrator()

    try:
        await orchestrator.initialize()
        result = await orchestrator.run(task)

        console.print("\n")
        if result.status.value == "success":
            console.print("[bold green]🎉 HOTOVO! {mode} dokončeno.[/bold green]".format(mode=mode))
        elif result.status.value == "partial":
            console.print("[bold yellow]⚠️ Dokončeno, ale je potřeba akce Copilota (instructions mode).[/bold yellow]")
        else:
            console.print("[bold yellow]⚠️ Dokončeno s problémy.[/bold yellow]")

        console.print(f"\n📁 Výstup: {orchestrator.file_manager.project_dir}")

    except KeyboardInterrupt:
        log_phase("error", "orchestrator", "Přerušeno uživatelem")
    except Exception as e:
        log_error("orchestrator", f"Fatální chyba: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    main()
