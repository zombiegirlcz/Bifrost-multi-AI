#!/usr/bin/env python3
"""
Bifrost 2.0 — Auto Executor: automaticky zpracovává úkoly z queue/

Spouštěno jako daemon vedle main.py.
Sleduje queue/pending/, vykonává úkoly a píše výsledky do queue/results/.

Použití:
  python auto_executor.py          # daemon mod (ctrl+C pro stop)
  python auto_executor.py --once   # zpracuj jeden úkol a skonči
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUEUE_DIR = BASE_DIR / "queue"
PENDING_DIR = QUEUE_DIR / "pending"
RESULTS_DIR = QUEUE_DIR / "results"
POLL_INTERVAL = 2.0   # sekundy mezi kontrolami fronty
PROCESSING_SUFFIX = ".processing"  # přejmenuj soubor při zpracování


def _ensure_dirs():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Parsování kódu z AI odpovědí ─────────────────────────────────────────────

def _extract_files_from_code(consensus_code: str) -> dict[str, str]:
    """
    Pokus se extrahovat soubory z AI consensus kódu.
    Podporuje různé formáty odpovědí AI modelů.
    """
    files = {}

    # Formát 1: ## cesta/soubor.py nebo **cesta/soubor.py:**
    # následovaný blokem kódu
    pattern1 = re.compile(
        r'(?:##\s+|^\*\*|^)([A-Za-z0-9_./-]+\.(?:py|js|ts|sh|txt|yaml|yml|json|md))\**\s*\n'
        r'(?:```\w*\n)?(.*?)(?:```|\Z)',
        re.MULTILINE | re.DOTALL
    )
    for m in pattern1.finditer(consensus_code):
        path, content = m.group(1).strip(), m.group(2).strip()
        if content and len(content) > 20:
            files[path] = content

    # Formát 2: ``` fence s cestou v komentáři uvnitř
    pattern2 = re.compile(
        r'```(?:python|bash|sh|javascript|js)?\s*\n'
        r'(?:#\s*([A-Za-z0-9_./-]+\.(?:py|js|sh|txt))\n)?'
        r'(.*?)```',
        re.DOTALL
    )
    for m in pattern2.finditer(consensus_code):
        hint_path = m.group(1)
        content = m.group(2).strip()
        if hint_path and content and len(content) > 20:
            files[hint_path] = content

    # Formát 3: sekce oddělené --- nebo ===
    pattern3 = re.compile(
        r'(?:^---+\s*\n|^===+\s*\n)'
        r'(?:File|Soubor|Path):\s*([A-Za-z0-9_./-]+)\s*\n'
        r'(.*?)(?=^---+|^===+|\Z)',
        re.MULTILINE | re.DOTALL
    )
    for m in pattern3.finditer(consensus_code):
        path, content = m.group(1).strip(), m.group(2).strip()
        if content and len(content) > 20:
            files[path] = content

    return files


def _parse_structured_json(consensus_code: str) -> dict | None:
    """Hledá strukturovaný JSON s files/dependencies v consensus kódu."""
    # Double-escaped braces (template formatting artifact)
    normalized = consensus_code.replace("{{", "{").replace("}}", "}")

    # Hledej JSON v code fence
    m = re.search(r'```json\s*(\{.*?\})\s*```', normalized, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            if "files" in data or "dependencies" in data:
                return data
        except json.JSONDecodeError:
            pass

    # Hledej volný JSON objekt s keys files/dependencies
    m = re.search(r'(\{[^{}]*"files"[^{}]*\{.*?\}[^{}]*\})', normalized, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ── Vytváření souborů ────────────────────────────────────────────────────────

def _write_files(project_dir: Path, files: dict[str, str]):
    """Zapíše soubory do projektového adresáře."""
    for rel_path, content in files.items():
        target = project_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  ✅ Zapsán: {rel_path}")


def _install_deps(project_dir: Path, deps: list[str]) -> bool:
    """Nainstaluje Python závislosti."""
    if not deps:
        return True
    print(f"  📦 Instaluji závislosti: {deps}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet"] + deps,
            cwd=project_dir, capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  ⚠️ Instalace selhala: {e}")
        return False


def _run_command(cmd: str, project_dir: Path, timeout: int = 60) -> tuple[bool, str]:
    """Spustí příkaz a vrátí (success, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=project_dir,
            capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Timeout po {timeout}s"
    except Exception as e:
        return False, str(e)


# ── Zpracování úkolů ─────────────────────────────────────────────────────────

def _get_project_dir_from_output() -> Path:
    """Najde nebo vytvoří aktuální projektový adresář v vysledky/."""
    vysledky_dir = BASE_DIR / "vysledky"
    vysledky_dir.mkdir(exist_ok=True)
    # Použij nejnovější podadresář nebo vytvoř nový
    subdirs = sorted(vysledky_dir.iterdir()) if vysledky_dir.exists() else []
    subdirs = [d for d in subdirs if d.is_dir() and not d.name.startswith(".")]
    if subdirs:
        return subdirs[-1]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_dir = vysledky_dir / f"{ts}_auto"
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir


def process_build_task(data: dict) -> dict:
    """Zpracuje build úkol — extrahuje soubory, vytvoří je, nainstaluje deps."""
    task = data.get("task", "unknown task")
    consensus_code = data.get("consensus_code", "")
    print(f"\n🔨 BUILD: {task[:80]}")

    project_dir = _get_project_dir_from_output()
    print(f"  📁 Projektový adresář: {project_dir}")

    # Pokus o extrakci struktury souborů
    structured = _parse_structured_json(consensus_code)
    extracted_files = _extract_files_from_code(consensus_code)

    files_created = {}
    deps = []
    run_cmd = ""
    test_cmd = "python -m pytest -v"

    if structured:
        deps = structured.get("dependencies", [])
        run_cmd = structured.get("run_command", "")
        test_cmd = structured.get("test_command", test_cmd)
        # Přeplní extrahované soubory strukturovanými (pokud mají reálný obsah)
        for path, content in structured.get("files", {}).items():
            if content and content not in ("obsah", "content", "..."):
                extracted_files[path] = content

    if extracted_files:
        _write_files(project_dir, extracted_files)
        files_created = {p: "written" for p in extracted_files}
    else:
        # Žádné soubory k extrakci — vytvoř základní strukturu dle plánu
        print("  ⚠️ Nepodařilo se extrahovat soubory z consensus kódu")
        print("  📝 Vytvářím stub soubory ze struktury...")
        if structured and structured.get("files"):
            for rel_path in structured["files"]:
                target = project_dir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_text(f"# Auto-generated stub: {rel_path}\n# Task: {task}\n")
                    files_created[rel_path] = "stub"
                    print(f"  📄 Stub: {rel_path}")
        else:
            # Zcela chybí struktura — zapiš prosté info
            info_file = project_dir / "task_info.txt"
            info_file.write_text(f"Task: {task}\n\nConsensus code:\n{consensus_code[:2000]}")
            files_created["task_info.txt"] = "info"

    # Nainstaluj závislosti
    if deps:
        _install_deps(project_dir, deps)

    # Ověř spuštění (pokud máme run_command)
    run_ok = True
    if run_cmd and extracted_files:
        run_ok, out = _run_command(f"timeout 10 {run_cmd}", project_dir, timeout=15)
        print(f"  🚀 Run test: {'OK' if run_ok else 'FAIL'} — {out[:100]}")

    return {
        "files_created": files_created,
        "dependencies": deps,
        "run_command": run_cmd,
        "test_command": test_cmd,
        "project_dir": str(project_dir),
        "summary": (
            f"Build dokončen. {len(files_created)} souborů vytvoření/stub. "
            f"Deps: {deps}. Run: {'OK' if run_ok else 'FAIL'}."
        )
    }


def process_test_task(data: dict) -> dict:
    """Zpracuje test úkol — spustí testy, vrátí výsledky."""
    files = data.get("files", [])
    test_cmd = data.get("test_command", "python -m pytest -v")
    print(f"\n🧪 TEST: {test_cmd}")

    project_dir = _get_project_dir_from_output()
    success, output = _run_command(test_cmd, project_dir, timeout=120)

    # Parsuj výsledky pytest
    test_results = []
    for line in output.split("\n"):
        m_pass = re.search(r'PASSED\s+(.+)', line)
        m_fail = re.search(r'FAILED\s+(.+?)(?:\s+-|$)', line)
        m_error = re.search(r'ERROR\s+(.+)', line)
        if m_pass:
            test_results.append({"test_name": m_pass.group(1).strip(),
                                  "passed": True, "error_message": None,
                                  "file": None, "line": None})
        elif m_fail:
            err_m = re.search(r'AssertionError.*?$', output, re.MULTILINE)
            test_results.append({"test_name": m_fail.group(1).strip(),
                                  "passed": False,
                                  "error_message": err_m.group(0) if err_m else "FAILED",
                                  "file": None, "line": None})
        elif m_error:
            test_results.append({"test_name": m_error.group(1).strip(),
                                  "passed": False,
                                  "error_message": "ERROR",
                                  "file": None, "line": None})

    # Shrnutí pytest
    summary_m = re.search(r'(\d+ passed|no tests ran|error)', output)
    summary = summary_m.group(0) if summary_m else ("passed" if success else "failed")

    return {
        "test_results": test_results if test_results else [
            {"test_name": "auto_run", "passed": success,
             "error_message": None if success else output[-300:],
             "file": None, "line": None}
        ],
        "overall_status": "success" if success else "partial",
        "summary": f"Testy: {summary}. Output: {output[:200]}",
        "files_modified": []
    }


def process_fix_task(data: dict) -> dict:
    """Zpracuje fix úkol — aplikuje opravu, spustí testy."""
    fix_code = data.get("fix_code", "")
    iteration = data.get("iteration", 1)
    print(f"\n🔧 FIX iterace {iteration}")

    project_dir = _get_project_dir_from_output()
    files_modified = []

    # Extrahuj soubory z fix_code
    fix_files = _extract_files_from_code(fix_code)
    if fix_files:
        _write_files(project_dir, fix_files)
        files_modified = list(fix_files.keys())
    else:
        print("  ⚠️ Nepodařilo se extrahovat soubory z fix kódu")

    # Spusť testy po opravě
    test_cmd = "python -m pytest -v"
    success, output = _run_command(test_cmd, project_dir, timeout=120)

    return {
        "test_results": [
            {"test_name": "post_fix_test", "passed": success,
             "error_message": None if success else output[-300:],
             "file": None, "line": None}
        ],
        "overall_status": "success" if success else "partial",
        "summary": f"Fix iterace {iteration} aplikován. Testy: {'OK' if success else 'FAIL'}.",
        "files_modified": files_modified
    }


# ── Hlavní smyčka ────────────────────────────────────────────────────────────

def process_one_task(task_path: Path) -> bool:
    """Zpracuje jeden úkol. Vrátí True pokud úspěšné."""
    lock_path = task_path.with_suffix(PROCESSING_SUFFIX)
    result_path = RESULTS_DIR / task_path.name

    # Skip pokud výsledek už existuje
    if result_path.exists():
        print(f"  ⏭️ Přeskakuji {task_path.name} — výsledek už existuje")
        return True

    # Atomický "lock" — přejmenuj soubor
    try:
        task_path.rename(lock_path)
    except FileNotFoundError:
        return False  # Jiný proces ho vzal

    try:
        data = json.loads(lock_path.read_text())
        task_id = data.get("id", task_path.stem)
        task_type = data.get("type", "build")

        print(f"\n{'='*60}")
        print(f"🤖 AUTO EXECUTOR — zpracovávám: {task_id} ({task_type})")
        print(f"{'='*60}")

        if task_type == "build":
            result = process_build_task(data)
        elif task_type == "test":
            result = process_test_task(data)
        elif task_type == "fix":
            result = process_fix_task(data)
        else:
            result = {"error": f"Neznámý typ úkolu: {task_type}"}

        result["task_id"] = task_id
        result["completed_at"] = datetime.now().isoformat()

        # Zapiš výsledek
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\n✅ Výsledek zapsán: {result_path.name}")

        # Odstraň lock soubor (úkol je hotový)
        lock_path.unlink(missing_ok=True)
        return True

    except Exception as e:
        print(f"\n❌ Chyba při zpracování {task_path.name}: {e}")
        import traceback
        traceback.print_exc()
        # Vrať soubor zpátky (aby ho mohl vzít znovu)
        try:
            lock_path.rename(task_path)
        except Exception:
            pass
        return False


def watch_queue(once: bool = False):
    """Sleduje frontu a zpracovává úkoly."""
    _ensure_dirs()
    print(f"🤖 Auto Executor spuštěn — sleduju {PENDING_DIR}")
    if once:
        print("  Režim: zpracuj jeden úkol a skonči")
    else:
        print("  Režim: daemon (Ctrl+C pro stop)")
    print()

    processed = 0
    try:
        while True:
            tasks = sorted(PENDING_DIR.glob("*.json"))
            # Filtruj lock soubory
            tasks = [t for t in tasks if not t.suffix == PROCESSING_SUFFIX]

            if tasks:
                task_path = tasks[0]
                print(f"📬 Nový úkol: {task_path.name}")
                ok = process_one_task(task_path)
                if ok:
                    processed += 1
                if once:
                    break
            elif once:
                print("📭 Žádné čekající úkoly.")
                break
            else:
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n⏹️ Auto Executor zastaven. Zpracováno: {processed} úkolů.")

    return processed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bifrost 2.0 — Auto Executor")
    parser.add_argument("--once", action="store_true",
                        help="Zpracuj jeden úkol a skonči")
    args = parser.parse_args()
    watch_queue(once=args.once)


if __name__ == "__main__":
    main()
