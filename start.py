#!/usr/bin/env python3
"""
🌈 Bifrost 2.0 — Quick Start Demo

Spuštění bez toho aby ses děsil 😄
"""
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

print("""
╔════════════════════════════════════════════════════════════════╗
║                 🌈 Bifrost 2.0 — Quick Start                  ║
╚════════════════════════════════════════════════════════════════╝

Vybrat si režim:

  1️⃣  CODING MAILBOX (Ja sam dělam) — nejrychlejší
      python main.py --task "Vytvoř kalkulačku"

  2️⃣  CODING INTERACTIVE (Ty si dělník)
      Terminál A: python main.py --task "..."
      Terminál B: python copilot_executor.py --list

  3️⃣  🛡️ SECURITY (Red/Blue/Purple Team kyber-simulace)
      python main.py --mode security --task "Simuluj SQL Injection"

  4️⃣  DEMO (test)
      python main.py --task "Vypočítej faktoriál 5" --worker mailbox

────────────────────────────────────────────────────────────────
""")

choice = input("Vyber (1/2/3/4/demo): ").strip().lower()

if choice == "1" or choice == "mailbox":
    task = input("Zadej úkol: ").strip() or "Vytvoř jednoduchou kalkulačku v Pythonu"
    print(f"\n▶ Spouštím: python main.py --task '{task}' --worker mailbox\n")
    subprocess.run([sys.executable, "main.py", "--task", task, "--worker", "mailbox"])

elif choice == "2" or choice == "interactive":
    task = input("Zadej úkol: ").strip() or "Vytvoř REST API endpoint"
    print(f"\n▶ Terminal A: python main.py --task '{task}'\n")
    print("▶ Terminal B: python copilot_executor.py --list\n")
    print("Poznámka: Spusť v dvou terminálech paralelně!\n")
    subprocess.run([sys.executable, "main.py", "--task", task])

elif choice == "3" or choice == "security":
    task = input("Zadej bezpečnostní úkol (SQL Injection, XSS, Brute Force): ").strip() \
        or "Simuluj SQL Injection na přihlašovací formulář"
    print(f"\n▶ Spouštím SECURITY MODE: python main.py --mode security --task '{task}'\n")
    subprocess.run([sys.executable, "main.py", "--mode", "security", "--task", task,
                   "--worker", "mailbox"])

elif choice == "4" or choice == "demo":
    print("\n▶ Spouštím DEMO s jednoduchým úkolem...\n")
    subprocess.run([sys.executable, "main.py", 
                   "--task", "Vypočítej součet čísel 1 až 10",
                   "--worker", "mailbox",
                   "--rounds", "2"])

else:
    print("❌ Neznámá volba")
    sys.exit(1)

print("\n✅ Hotovo!\n")
