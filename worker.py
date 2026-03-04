"""
Bifrost 2.0 — Worker modul: Copilot jako dělník — staví, testuje, reportuje
"""
import json
import re
from protocol import BifrostMessage, Phase, Status, TestResult
from utils.logger import log_phase, log_code, log_test_results, log_error
from utils.file_manager import FileManager
from config import TEMPLATES_DIR


def load_template(name: str) -> str:
    from pathlib import Path
    path = TEMPLATES_DIR / name
    if path.exists():
        return path.read_text()
    return "{code}"


class Worker:
    """Copilot jako dělník — přijímá kód, staví, testuje, reportuje."""

    def __init__(self, copilot_session, file_manager: FileManager):
        self.copilot = copilot_session
        self.fm = file_manager

    async def build(self, consensus: BifrostMessage, task: str) -> BifrostMessage:
        """Pošle konsenzuální kód Copilotovi k implementaci."""
        log_phase("worker_build", "copilot", "Začínám stavbu projektu")

        template = load_template("worker_build.txt")
        prompt = (template
                 .replace("{task}", task)
                 .replace("{code}", consensus.content))

        build_prompt = f"""
Jsi dělník v týmu Bifrost 2.0. Tým architektů ti posílá tento kód.

## ZADÁNÍ:
{task}

## KÓD OD ARCHITEKTŮ:
{consensus.content}

## TVOJE ÚKOLY:
1. Analyzuj kód a identifikuj všechny soubory, které je potřeba vytvořit
2. Pro KAŽDÝ soubor vypiš jeho kompletní obsah ve formátu:

### FILE: cesta/k/souboru.py
```python
# kompletní obsah souboru
```

3. Vypiš všechny závislosti (pip/npm packages)
4. Vypiš příkazy pro spuštění
5. Napiš základní testy

## FORMÁT ODPOVĚDI:
Odpověz PŘESNĚ v tomto JSON formátu:
```json
{{
    "files": {{
        "cesta/soubor.py": "obsah souboru",
        "cesta/dalsi.py": "obsah"
    }},
    "dependencies": ["flask", "sqlite3"],
    "run_command": "python app.py",
    "test_command": "python -m pytest tests/",
    "tests": {{
        "tests/test_main.py": "obsah testu"
    }}
}}
```
"""

        response = await self.copilot.send_message(build_prompt)

        # Parsuj odpověď
        build_data = self._parse_worker_response(response)

        # Zapiš soubory
        files_created = []
        all_files = {**build_data.get("files", {}), **build_data.get("tests", {})}
        
        for filepath, content in all_files.items():
            saved = await self.fm.save_code(filepath, content)
            files_created.append(str(filepath))
            log_phase("worker_build", "copilot", f"Vytvořen: {filepath}")

        return BifrostMessage(
            phase=Phase.WORKER_BUILD,
            status=Status.SUCCESS,
            source="copilot",
            content=response,
            files_created=files_created,
            dependencies=build_data.get("dependencies", []),
            metadata={
                "run_command": build_data.get("run_command", ""),
                "test_command": build_data.get("test_command", "")
            }
        )

    async def test(self, build_result: BifrostMessage) -> BifrostMessage:
        """Požádá Copilota o spuštění testů a analýzu výsledků."""
        log_phase("worker_test", "copilot", "Spouštím testy")

        test_prompt = f"""
Spusť testy pro projekt, který jsi právě vytvořil.

Soubory v projektu: {json.dumps(build_result.files_created)}
Test příkaz: {build_result.metadata.get('test_command', 'python -m pytest')}

Simuluj spuštění testů — projdi kód a identifikuj:
1. Které testy by prošly
2. Které by selhaly a proč
3. Jaké runtime errory by nastaly

Odpověz v tomto JSON formátu:
```json
{{
    "test_results": [
        {{
            "test_name": "test_nazev",
            "passed": true,
            "error_message": null,
            "file": null,
            "line": null
        }},
        {{
            "test_name": "test_chybny",
            "passed": false,
            "error_message": "TypeError: ...",
            "file": "app.py",
            "line": 42
        }}
    ],
    "overall_status": "partial",
    "summary": "3/5 testů prošlo, 2 selhaly kvůli..."
}}
```
"""

        response = await self.copilot.send_message(test_prompt)
        test_data = self._parse_worker_response(response)

        test_results = [
            TestResult(**t) for t in test_data.get("test_results", [])
        ]

        log_test_results(test_results)

        all_passed = all(t.passed for t in test_results)

        return BifrostMessage(
            phase=Phase.WORKER_TEST,
            status=Status.SUCCESS if all_passed else Status.PARTIAL,
            source="copilot",
            content=response,
            test_results=test_results,
            metadata={
                "overall_status": test_data.get("overall_status", "unknown"),
                "summary": test_data.get("summary", "")
            }
        )

    async def apply_fix(self, fix_code: str, iteration: int) -> BifrostMessage:
        """Aplikuje opravu od mozků."""
        log_phase("fix_applied", "copilot", f"Aplikuji opravu (iterace {iteration})")

        fix_prompt = f"""
Tým architektů poslal opravu. Aplikuj ji:

## OPRAVA:
{fix_code}

## ÚKOLY:
1. Identifikuj které soubory se mění
2. Vypiš kompletní nový obsah změněných souborů
3. Znovu spusť testy

Odpověz ve stejném JSON formátu jako předtím (files + test_results).
"""

        response = await self.copilot.send_message(fix_prompt)
        fix_data = self._parse_worker_response(response)

        # Zapiš opravené soubory
        files_modified = []
        for filepath, content in fix_data.get("files", {}).items():
            await self.fm.save_code(filepath, content)
            files_modified.append(filepath)

        test_results = [
            TestResult(**t) for t in fix_data.get("test_results", [])
        ]

        all_passed = all(t.passed for t in test_results)

        return BifrostMessage(
            phase=Phase.FIX_APPLIED,
            status=Status.SUCCESS if all_passed else Status.PARTIAL,
            source="copilot",
            content=response,
            files_modified=files_modified,
            iteration=iteration,
            test_results=test_results
        )

    def _parse_worker_response(self, response: str) -> dict:
        """Extrahuje JSON z odpovědi Copilota."""
        # Hledej JSON blok v odpovědi
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Zkus celou odpověď jako JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            log_error("copilot", "Nepodařilo se parsovat JSON z odpovědi")
            return {"raw_response": response}
