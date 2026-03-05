"""
Bifrost 2.0 — Diff viewer pro porovnání iterací kódu
"""
import difflib
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()


def show_diff(old_code: str, new_code: str, title: str = "Změny"):
    diff = difflib.unified_diff(
        old_code.splitlines(keepends=True),
        new_code.splitlines(keepends=True),
        fromfile="předchozí verze",
        tofile="nová verze",
        lineterm=""
    )
    diff_text = "\n".join(diff)

    if not diff_text.strip():
        console.print(f"[dim]Žádné změny v: {title}[/dim]")
        return

    console.print(Panel(
        Syntax(diff_text, "diff", theme="monokai"),
        title=f"📝 {title}",
        border_style="yellow"
    ))


def calculate_similarity(code_a: str, code_b: str) -> float:
    """Vrátí podobnost dvou kódů jako float 0.0–1.0."""
    return difflib.SequenceMatcher(None, code_a, code_b).ratio()


def find_consensus_score(solutions: dict[str, str]) -> dict:
    """Spočítá vzájemnou podobnost všech řešení."""
    names = list(solutions.keys())
    scores = {}
    for i, name_a in enumerate(names):
        for name_b in names[i+1:]:
            sim = calculate_similarity(solutions[name_a], solutions[name_b])
            scores[f"{name_a} ↔ {name_b}"] = round(sim, 3)
    
    avg = sum(scores.values()) / len(scores) if scores else 0
    scores["_average"] = round(avg, 3)
    return scores
