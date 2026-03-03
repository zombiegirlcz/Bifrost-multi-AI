#!/usr/bin/env python3
"""
🌈 Bifrost 2.0 — Multi-AI Collaborative Coding System
Hlavní vstupní bod
"""
import asyncio
import click
from orchestrator import Orchestrator
from utils.logger import log_banner, log_phase, log_error, console


@click.command()
@click.option("--task", "-t", prompt="📝 Zadej úkol", help="Co má tým vytvořit")
@click.option("--rounds", "-r", default=3, help="Počet kol debaty (default: 3)")
@click.option("--max-fix", "-f", default=5, help="Max opravných iterací (default: 5)")
@click.option("--worker", "-w", default="mailbox",
              type=click.Choice(["mailbox", "playwright"]),
              help="Worker: mailbox (CLI Copilot) nebo playwright (web automation)")
@click.option("--verbose", "-v", is_flag=True, help="Podrobný výstup")
def main(task: str, rounds: int, max_fix: int, worker: str, verbose: bool):
    """🌈 Bifrost 2.0 — Spusť svůj AI vývojový tým."""

    import config
    if rounds != 3:
        config.BRAIN_ROUNDS = rounds
    if max_fix != 5:
        config.MAX_FIX_ITERATIONS = max_fix
    config.WORKER_MODE = worker

    asyncio.run(run_bifrost(task, verbose))


async def run_bifrost(task: str, verbose: bool):
    orchestrator = Orchestrator()

    try:
        await orchestrator.initialize()
        result = await orchestrator.run(task)

        console.print("\n")
        if result.status.value == "success":
            console.print("[bold green]🎉 HOTOVO! Projekt je připraven.[/bold green]")
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
