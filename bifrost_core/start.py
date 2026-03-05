#!/usr/bin/env python3
"""
🌈 Bifrost 2.0 — Quick Start
Vyber režim (coding / security) a worker (mailbox / instructions).
"""
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent


def run_with_auto_executor(cmd: list[str]):
    """Spustí main.py + auto_executor.py paralelně (executor na pozadí)."""
    print("  🤖 Spouštím Auto Executor na pozadí...")
    executor = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "auto_executor.py")],
        cwd=BASE_DIR
    )
    time.sleep(1)
    try:
        subprocess.run(cmd, cwd=BASE_DIR)
    finally:
        executor.terminate()
        executor.wait(timeout=5)
        print("  🤖 Auto Executor zastaven.")


print("""
╔════════════════════════════════════════════════════════════════╗
║                 🌈 Bifrost 2.0 — Quick Start                   ║
╚════════════════════════════════════════════════════════════════╝

Vyber si režim:

  1️⃣  CODING MAILBOX (CLI Copilot pracuje) — nejrychlejší
      python -m bifrost_core.main --task "Vytvoř kalkulačku" --worker mailbox

  2️⃣  CODING INTERACTIVE (Ty si dělník)
      Terminál A: python -m bifrost_core.main --task "..."
      Terminál B: python -m bifrost_core.copilot_executor --list

  3️⃣  🛡️ SECURITY (Red/Blue/Purple simulace)
      python -m bifrost_core.main --mode security --task "Simuluj SQL Injection"

  4️⃣  DEMO (test)
      python -m bifrost_core.main --task "Vypočítej součet čísel 1 až 10" --worker mailbox --rounds 2
────────────────────────────────────────────────────────────────
""")

choice = input("Vyber (1/2/3/4): ").strip().lower()

if choice == "1" or choice == "mailbox":
    task = input("Zadej úkol: ").strip() or "Vytvoř jednoduchou kalkulačku v Pythonu"
    print(f"\n▶ Spouštím: python -m bifrost_core.main --task '{task}' --worker mailbox\n")
    run_with_auto_executor([sys.executable, "-m", "bifrost_core.main", "--task", task, "--worker", "mailbox"])

elif choice == "2" or choice == "interactive":
    task = input("Zadej úkol: ").strip() or "Vytvoř REST API endpoint"
    print(f"\n▶ Terminal A: python -m bifrost_core.main --task '{task}'\n")
    print("▶ Terminal B: python -m bifrost_core.copilot_executor --list\n")
    subprocess.run([sys.executable, "-m", "bifrost_core.main", "--task", task], cwd=BASE_DIR)

elif choice == "3" or choice == "security":
    task = input("Zadej bezpečnostní úkol (SQL Injection, XSS, Brute Force): ").strip() \
        or "Simuluj SQL Injection na přihlašovací formulář"
    print(f"\n▶ Spouštím SECURITY MODE: python -m bifrost_core.main --mode security --task '{task}'\n")
    run_with_auto_executor([sys.executable, "-m", "bifrost_core.main", "--mode", "security", "--task", task,
                   "--worker", "mailbox"])

elif choice == "4" or choice == "demo":
    print("\n▶ Spouštím DEMO s jednoduchým úkolem...\n")
    run_with_auto_executor([sys.executable, "-m", "bifrost_core.main",
                   "--task", "Vypočítej součet čísel 1 až 10",
                   "--worker", "mailbox",
                   "--rounds", "2"])

else:
    print("❌ Neznámá volba")
    sys.exit(1)

print("\n✅ Hotovo!\n")
