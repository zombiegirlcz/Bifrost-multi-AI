"""
Bifrost 2.0 — Strukturované logování s Rich
"""
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markup import escape as rich_escape
from rich import print as rprint
from datetime import datetime
import logging

console = Console()

# Emoji mapy pro fáze
PHASE_EMOJI = {
    "brain_round": "🧠",
    "brain_review": "🔍",
    "brain_consensus": "🤝",
    "worker_build": "🏗️",
    "worker_test": "🧪",
    "worker_report": "📋",
    "fix_request": "🔧",
    "fix_applied": "✅",
    "complete": "🎉",
    "error": "❌",
}

MODEL_COLORS = {
    "chatgpt": "green",
    "claude": "blue",
    "gemini": "yellow",
    "copilot": "magenta",
    "orchestrator": "cyan",
}


def log_phase(phase: str, source: str, message: str):
    emoji = PHASE_EMOJI.get(phase, "📌")
    color = MODEL_COLORS.get(source, "white")
    timestamp = datetime.now().strftime("%H:%M:%S")
    safe_msg = rich_escape(message)
    console.print(
        f"[dim]{timestamp}[/dim] {emoji} "
        f"[bold {color}]{source.upper()}[/bold {color}] → {safe_msg}"
    )


def log_code(code: str, language: str = "python", title: str = "Kód"):
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=title, border_style="green"))


def log_error(source: str, error: str):
    safe_error = rich_escape(str(error))
    console.print(Panel(
        f"[red]{safe_error}[/red]",
        title=f"❌ Chyba — {source}",
        border_style="red"
    ))


def log_test_results(results: list):
    table = Table(title="🧪 Výsledky testů")
    table.add_column("Test", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    for r in results:
        status = "[green]✅ PASS[/green]" if r.passed else "[red]❌ FAIL[/red]"
        detail = r.error_message or ""
        table.add_row(r.test_name, status, detail[:80])

    console.print(table)


def log_banner():
    console.print(Panel(
        "[bold rainbow]🌈 BIFROST 2.0[/bold rainbow]\n"
        "[dim]Multi-AI Collaborative Coding System[/dim]\n"
        "[dim]Termux Edition[/dim]",
        border_style="bright_magenta",
        padding=(1, 4),
    ))
