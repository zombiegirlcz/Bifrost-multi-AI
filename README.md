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
# Coding mode — klasický vývoj
python main.py --task "Vytvoř REST API pro správu úkolů"

# S parametry
python main.py --task "Snake hra v Pythonu" --rounds 5 --max-fix 10

# 🛡️ Security mode — kyber-simulace
python main.py --mode security --task "Simuluj SQL Injection na přihlašovací formulář"
python main.py -m security -t "XSS útok na komentářový systém"
python main.py -m security -t "Brute force na login endpoint"

# Interaktivní
python main.py
```

## 🏗️ Architektura

### Coding Mode
```
TY → Orchestrátor → Mozky (debata) → Copilot (stavba + testy) → Feedback loop
```

### 🛡️ Security Mode
```
TY → Security Orchestrátor → Red Team (exploit) ↔ Blue Team (obrana)
                           → Purple Team (analýza + report)
                           → Copilot (sandbox: zranitelná app + exploit + oprava)
                           → Feedback loop
```

**Role mozků v Security Mode:**
- 🔴 **Red Team (Útočník)** — navrhuje exploity, hledá zranitelnosti
- 🔵 **Blue Team (Obránce)** — detekce, WAF pravidla, oprava kódu
- 🟣 **Purple Team (Analytik)** — hodnotí útok vs. obranu, CVSS skóre

## 📁 Výstupy

Každý projekt se uloží do `output/` s:
- Kompletním kódem
- Historií iterací
- Finálním reportem (BIFROST_REPORT.md nebo SECURITY_REPORT.md)

### Security výstupy
- `target/vulnerable_app.py` — zranitelná aplikace
- `target/secure_app.py` — opravená verze
- `exploit/exploit.py` — útočný PoC skript
- `defense/detect.py` — detekční skript
- `defense/waf_rules.txt` — WAF pravidla
- `tests/test_security.py` — bezpečnostní testy
