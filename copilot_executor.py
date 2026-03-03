#!/usr/bin/env python3
"""
Bifrost 2.0 — Copilot Executor: vyzvedává úkoly z queue/ a provádí je

Použití:
  python copilot_executor.py              # Zpracuje jeden čekající úkol
  python copilot_executor.py --watch      # Sleduje frontu průběžně
  python copilot_executor.py --task ID    # Zpracuje konkrétní úkol

Tento skript je MOST mezi orchestrátorem a CLI Copilotem.
Uživatel ho spustí, skript přečte úkol a vypíše instrukce,
které uživatel předá CLI Copilotovi.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
QUEUE_DIR = BASE_DIR / "queue"
PENDING_DIR = QUEUE_DIR / "pending"
RESULTS_DIR = QUEUE_DIR / "results"


def list_pending():
    """Vypíše čekající úkoly."""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    tasks = sorted(PENDING_DIR.glob("*.json"))
    if not tasks:
        print("📭 Žádné čekající úkoly.")
        return []

    print(f"📬 Čekající úkoly ({len(tasks)}):\n")
    for t in tasks:
        data = json.loads(t.read_text())
        print(f"  📋 {t.name}")
        print(f"     Typ: {data.get('type', '?')}")
        if data.get('task'):
            print(f"     Zadání: {data['task'][:80]}...")
        print()
    return tasks


def show_task(task_path: Path):
    """Zobrazí detail úkolu jako instrukce pro Copilota."""
    data = json.loads(task_path.read_text())
    task_type = data.get("type", "unknown")
    task_id = data.get("id", task_path.stem)

    print("=" * 60)
    print(f"📋 ÚKOL: {task_id} ({task_type})")
    print("=" * 60)

    if task_type == "build":
        print(f"\n📝 Zadání: {data.get('task', 'N/A')}")
        print(f"\n📄 Kód od architektů:")
        print("-" * 40)
        code = data.get("consensus_code", "")
        print(code[:2000] + ("..." if len(code) > 2000 else ""))
        print("-" * 40)
        print(f"\n📌 Instrukce:\n{data.get('instructions', '')}")

    elif task_type == "test":
        print(f"\n📁 Soubory: {json.dumps(data.get('files', []), indent=2)}")
        print(f"\n🧪 Test příkaz: {data.get('test_command', 'python -m pytest')}")
        print(f"\n📌 Instrukce:\n{data.get('instructions', '')}")

    elif task_type == "fix":
        print(f"\n🔧 Iterace: {data.get('iteration', '?')}")
        print(f"\n📄 Opravný kód:")
        print("-" * 40)
        fix = data.get("fix_code", "")
        print(fix[:2000] + ("..." if len(fix) > 2000 else ""))
        print("-" * 40)
        print(f"\n📌 Instrukce:\n{data.get('instructions', '')}")

    print(f"\n{'=' * 60}")
    print(f"👉 ŘEKNI COPILOTOVI V TERMINÁLU:")
    print(f"   \"Proveď úkol z queue/pending/{task_id}.json\"")
    print(f"\n   Až bude hotovo, výsledek zapiš do:")
    print(f"   queue/results/{task_id}.json")
    print(f"{'=' * 60}")

    # Ukázka formátu výsledku
    print(f"\n📝 Formát výsledku (queue/results/{task_id}.json):")
    if task_type == "build":
        print(json.dumps({
            "files_created": {"cesta/soubor.py": "obsah..."},
            "dependencies": ["flask"],
            "run_command": "python app.py",
            "test_command": "python -m pytest",
            "summary": "Vytvořeno X souborů..."
        }, indent=2, ensure_ascii=False))
    elif task_type in ("test", "fix"):
        print(json.dumps({
            "test_results": [
                {"test_name": "test_example", "passed": True,
                 "error_message": None, "file": None, "line": None}
            ],
            "overall_status": "success",
            "summary": "Všechny testy prošly",
            "files_modified": []
        }, indent=2, ensure_ascii=False))


def write_result(task_id: str, result: dict):
    """Zapíše výsledek do results/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result["completed_at"] = datetime.now().isoformat()
    path = RESULTS_DIR / f"{task_id}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"✅ Výsledek zapsán: {path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bifrost 2.0 — Copilot Executor")
    parser.add_argument("--list", action="store_true", help="Zobraz čekající úkoly")
    parser.add_argument("--task", type=str, help="ID úkolu ke zpracování")
    parser.add_argument("--result", type=str, help="Zapiš výsledek (JSON string)")
    args = parser.parse_args()

    if args.list or (not args.task and not args.result):
        tasks = list_pending()
        if tasks and not args.list:
            show_task(tasks[0])
        return

    if args.task:
        task_path = PENDING_DIR / f"{args.task}.json"
        if not task_path.exists():
            # Zkus bez prefixu
            task_path = PENDING_DIR / f"task_{args.task}.json"
        if task_path.exists():
            show_task(task_path)
        else:
            print(f"❌ Úkol '{args.task}' nenalezen v {PENDING_DIR}")
            sys.exit(1)

    if args.result and args.task:
        try:
            result_data = json.loads(args.result)
            write_result(args.task, result_data)
        except json.JSONDecodeError:
            print("❌ Neplatný JSON")
            sys.exit(1)


if __name__ == "__main__":
    main()
