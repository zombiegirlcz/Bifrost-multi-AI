# 🌈 Bifrost 2.0

**Multi-AI Collaborative Coding System pro Termux**

Bifrost je orchestrator, který propojuje více AI modelů jako "mozky" (Claude Architect, Gemini Creative, GPT Critic)
a GitHub Copilot CLI jako "dělníka" — společně navrhují, debatují, staví a testují kód.

## 🚀 Instalace

```bash
chmod +x setup.sh
./setup.sh
```

## 🔑 Cookies (Monica.im)

Exportuj cookies z prohlížeče (např. pomocí rozšíření "Cookie Editor"):

**Povinné:**
- `bifrost_core/cookies/monica_cookies.json` — Monica.im multi-chat pro komunikaci s AI mozky

Formát: JSON pole cookies z prohlížeče. Detaily viz `bifrost_core/cookies/README.md`.

## 📝 Použití

Spouštěj jako balíček (`python -m`) kvůli relativním importům:

```bash
# Coding režim (výchozí), mailbox worker (automaticky staví/testuje)
python -m bifrost_core.main --task "Vytvoř REST API pro správu úkolů"

# Security režim (Red/Blue/Purple simulace)
python -m bifrost_core.main --mode security --task "Simuluj SQL Injection"

# Přepínače
#  -m / --mode          coding | security (default: coding)
#  -w / --worker        mailbox | instructions (default: mailbox)
#  -r / --rounds        počet kol debaty
#  -f / --max-fix       max oprav

# Mailbox flow (CLI Copilot jako dělník)
python -m bifrost_core.main --task "Snake hra" --worker mailbox
python -m bifrost_core.copilot_executor --list   # druhý terminál nebo auto_executor
```

> Pozn.: instructions worker pouze generuje návod pro Copilota a výsledný status bude **partial**
> (projekt není fyzicky postaven). Pro automatické sestavení používej default mailbox.

## 🏗️ Architektura

### Mailbox Mode (CLI Copilot)
```
Terminál 1:  python -m bifrost_core.main -t "úkol" --worker mailbox
             Mozky debatují → zapíše úkol do queue/

Terminál 2:  python -m bifrost_core.copilot_executor (nebo auto_executor.py)
             → CLI Copilot skutečně vytváří soubory, instaluje deps, spouští testy
             → zapíše do queue/results/

Terminál 1:  Orchestrátor vyzvedne výsledek → pokračuje
```

### Instructions Mode (rychlý návrh)
```
Orchestrátor jen vytvoří instrukce pro Copilota, nic nespouští a status = partial.
```

### Security Mode
```
Red/Blue/Purple mozky → konsenzus → worker (stejný worker přepínač) → test/feedback.
```

## 📬 Copilot Executor

```bash
# Zobraz čekající úkoly
python -m bifrost_core.copilot_executor --list

# Detail konkrétního úkolu
python -m bifrost_core.copilot_executor --task task_001
```

## 📁 Výstupy

Každý projekt se uloží do `bifrost_core/output/` s:
- Kompletním kódem z konsensuální debaty mozků
- Historií iterací (iterace s debatami, testy, opravami)
- Finálním reportem (BIFROST_REPORT.md pro coding / SECURITY_REPORT.md pro security režim)

Poznámka: Výstupní adresáře jsou artefakty a při testování se ignorují (.gitignore).
