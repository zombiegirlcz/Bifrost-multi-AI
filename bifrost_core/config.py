"""
Bifrost 2.0 — Konfigurace
"""
import os
import shutil
from pathlib import Path

# Základní cesty
BASE_DIR = Path(__file__).parent
COOKIES_DIR = BASE_DIR / "cookies"
OUTPUT_DIR = BASE_DIR / "output"
TEMPLATES_DIR = BASE_DIR / "templates"

# Termux Chromium — nativní binárka (obchází glibc problém)
BROWSER_PATH = shutil.which("chromium-browser") or shutil.which("chromium") or "/data/data/com.termux/files/usr/bin/chromium-browser"

# ═══════════════════════════════════════════════════════════════
# Monica Multi-Chat — 1 stránka, 3 mozky najednou
# ═══════════════════════════════════════════════════════════════
MONICA_URL = "https://monica.im/cs/products/ai-chat"
MONICA_COOKIES = COOKIES_DIR / "monica_cookies.json"

# CSS selektory zjištěné live debugem z Monica stránky
MONICA_SELECTORS = {
    "layout_icons":     ".chat-footer--_4Mms .icon--dFXLr",
    "layout_3col_idx":  2,       # nth(2) = 3 sloupce
    "panel":            ".chat-item--ZYRve",
    "panel_title":      ".title--zoZYE",
    "model_dropdown":   ".dropdown-menu-item--QeH1L",
    "global_input":     ".footer--eDFl6 textarea",
    "global_send":      ".footer--eDFl6 svg.icon--R8Ygf",
    "panel_input":      "input.input--lwUSZ",   # per-panel input ("Odeslat komu X")
    "panel_send":       "svg.icon--R8Ygf",      # per-panel send button
}

# Tři mozky — role + model v Monica dropdownu
# Architekt = Claude Opus, Kreativní = Gemini, Kritik = GPT
MONICA_PANELS = {
    "claude": {
        "role": "architekt",
        "model_label": "Claude 4.5 Sonnet",      # cílový default (architekt)
        "fallback_label": "Claude 4.5 Haiku",
        "label_variants": ["Claude Sonnet", "Claude 3.7 Sonnet", "Claude 4 Sonnet"],
        "panel_index": 0,
        "system_prefix": "Jsi hlavní architekt. Navrhuj čistý, udržitelný kód.",
    },
    "gemini": {
        "role": "kreativní",
        "model_label": "Gemini 3 Flash",
        "fallback_label": "Gemini 3 Flash",
        "panel_index": 1,
        "system_prefix": "Jsi kreativní myslitel. Hledej neotřelá, inovativní řešení.",
    },
    "gpt": {
        "role": "kritik",
        "model_label": "GPT-4o",                 # free tier (GPT-5.2 vyžaduje premium)
        "fallback_label": "GPT-4o mini",
        "panel_index": 2,
        "system_prefix": "Jsi kritik. Hledej chyby, edge-casy a bezpečnostní díry.",
    },
}

# Legacy konfigurace — zachováno pro zpětnou kompatibilitu testů
MODELS = {
    "copilot": {
        "name": "Copilot",
        "role": "worker",
        "url": "https://github.com/copilot",
        "cookies": COOKIES_DIR / "copilot_cookies.json",
        "input_selector": '#user-input',
        "submit_selector": 'button[type="submit"]',
        "response_selector": '.markdown-body',
        "wait_selector": 'button[type="submit"]:not([disabled])',
        "timeout": 180000,
    },
}

# Workflow konfigurace
BRAIN_ROUNDS = 3          # Počet kol debaty mezi mozky
MAX_FIX_ITERATIONS = 5    # Max pokusů o opravu chyb
RATE_LIMIT_DELAY = 3.0    # Sekundy mezi requesty na stejný model
BROWSER_STARTUP_DELAY = 30  # Sekundy pauzy mezi spuštěním každého browseru (Termux šetření RAM)
CONSENSUS_THRESHOLD = 0.7  # Shoda potřebná pro konsenzus (0-1)
RESPONSE_POLL_INTERVAL = 3  # Sekundy mezi pokusy o přečtení odpovědi
RESPONSE_MAX_WAIT = 360     # Max sekund čekání na odpověď (Opus může trvat 200-400s)
RESPONSE_STABLE_POLLS = 3   # Kolik po sobě jdoucích pollů musí být délka stejná = hotovo

# Worker mode: "instructions" (jen generuje instrukce pro Copilota) nebo "mailbox" (CLI Copilot)
WORKER_MODE = "mailbox"

# Security mode: False = coding mode, True = kyber-simulace
SECURITY_MODE = False

# Logování
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "bifrost.log"
