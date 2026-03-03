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
4. `cookies/copilot_cookies.json`

Formát: JSON pole cookies z prohlížeče.

## 📝 Použití

```bash
# Základní použití
python main.py --task "Vytvoř REST API pro správu úkolů"

# S parametry
python main.py --task "Snake hra v Pythonu" --rounds 5 --max-fix 10

# Interaktivní
python main.py
```

## 🏗️ Architektura

```
TY → Orchestrátor → Mozky (debata) → Copilot (stavba + testy) → Feedback loop
```

## 📁 Výstupy

Každý projekt se uloží do `output/` s:
- Kompletním kódem
- Historií iterací
- Finálním reportem (BIFROST_REPORT.md)
