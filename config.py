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

# AI Model konfigurace
MODELS = {
    "chatgpt": {
        "name": "ChatGPT",
        "role": "brain",
        "url": "https://chatgpt.com/",
        "cookies": COOKIES_DIR / "chatgpt_cookies.json",
        "input_selector": "textarea[placeholder*='message']",
        "submit_selector": "button[aria-label*='Send']",
        "response_selector": "[data-message-author-role='assistant']",
        "wait_selector": "button[aria-label*='Send']:not([disabled])",
        "timeout": 120000,
    },
    "claude": {
        "name": "Claude",
        "role": "brain",
        "url": "https://chatbotai.co/chat",
        "cookies": COOKIES_DIR / "chatbot_ai_cookies.json",
        "input_selector": "textarea.chat-input",
        "submit_selector": "button.send-button",
        "response_selector": ".message.bot",
        "wait_selector": "button.send-button:not([disabled])",
        "timeout": 120000,
        "post_connect": {"dismiss_popup": True, "select_model": "Claude Opus 4.6"},
    },
    "gemini": {
        "name": "Gemini",
        "role": "brain",
        "url": "https://gemini.google.com/app",
        "cookies": COOKIES_DIR / "gemini_cookies.json",
        "input_selector": "textarea.gds-body-l",
        "submit_selector": "mat-icon.send-icon",
        "response_selector": "message-content",
        "wait_selector": "textarea.gds-body-l",
        "timeout": 120000,
    },
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

# Worker mode: "playwright" (web automation) nebo "mailbox" (CLI Copilot)
WORKER_MODE = "mailbox"

# Security mode: False = coding mode, True = kyber-simulace
SECURITY_MODE = False

# Logování
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "bifrost.log"
