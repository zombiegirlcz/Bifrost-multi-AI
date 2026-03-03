# 🌈 Bifrost 2.0

**Multi-AI Collaborative Coding System pro Termux**

Bifrost propojuje více AI modelů (ChatGPT, Claude, Gemini) jako "mozky"
a GitHub Copilot jako "dělníka" — společně navrhují, debatují, staví
a testují kód.

## 🚀 Instalace

```bash
chmod +x setup.sh
./setup.sh
```

## 🔑 Cookies

Exportuj cookies z prohlížeče (např. pomocí rozšíření "Cookie Editor"):

1. `cookies/chatgpt_cookies.json`
2. `cookies/claude_cookies.json`
3. `cookies/gemini_cookies.json`

Formát: JSON pole cookies z prohlížeče. Detaily viz `cookies/README.md`.

## 📝 Použití

```bash
# Základní použití (mailbox mode — CLI Copilot jako dělník)
python main.py --task "Vytvoř REST API pro správu úkolů"

# S parametry
python main.py --task "Snake hra v Pythonu" --rounds 5 --max-fix 10

# Playwright mode (web automation — starý způsob)
python main.py --worker playwright --task "Kalkulačka v Pythonu"

# Interaktivní
python main.py
```

## 🏗️ Architektura

### Mailbox Mode (default) — CLI Copilot jako dělník
```
Terminál 1:  python main.py -t "úkol"
             Mozky debatují (Playwright) → zapíše úkol do queue/

Terminál 2:  python copilot_executor.py
             → zobrazí úkol → uživatel řekne CLI Copilotovi "proveď to"
             → CLI Copilot SKUTEČNĚ vytvoří soubory, spustí testy
             → výsledek se zapíše do queue/results/

Terminál 1:  Orchestrátor vyzvedne výsledek → pokračuje
```

### Playwright Mode (legacy) — web automation
```
TY → Orchestrátor → Mozky (debata) → Copilot web chat (simulace) → Feedback loop
```

## 📬 Copilot Executor

```bash
# Zobraz čekající úkoly
python copilot_executor.py --list

# Detail konkrétního úkolu
python copilot_executor.py --task task_001
```

## 📁 Výstupy

Každý projekt se uloží do `output/` s:
- Kompletním kódem
- Historií iterací
- Finálním reportem (BIFROST_REPORT.md)
