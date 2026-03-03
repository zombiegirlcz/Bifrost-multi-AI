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
CHROMIUM_PATH = shutil.which("chromium-browser") or "/data/data/com.termux/files/usr/bin/chromium-browser"

# AI Model konfigurace
MODELS = {
    "chatgpt": {
        "name": "ChatGPT",
        "role": "brain",
        "url": "https://chat.openai.com",
        "cookies": COOKIES_DIR / "chatgpt_cookies.json",
        "input_selector": "#prompt-textarea",
        "submit_selector": 'button[data-testid="send-button"]',
        "response_selector": '[data-message-author-role="assistant"]',
        "wait_selector": 'button[data-testid="send-button"]:not([disabled])',
        "timeout": 120000,
    },
    "claude": {
        "name": "Claude",
        "role": "brain",
        "url": "https://claude.ai/new",
        "cookies": COOKIES_DIR / "claude_cookies.json",
        "input_selector": '[contenteditable="true"]',
        "submit_selector": 'button[aria-label="Send Message"]',
        "response_selector": '[data-is-streaming="false"] .font-claude-message',
        "wait_selector": 'button[aria-label="Send Message"]:not([disabled])',
        "timeout": 120000,
    },
    "gemini": {
        "name": "Gemini",
        "role": "brain",
        "url": "https://gemini.google.com/app",
        "cookies": COOKIES_DIR / "gemini_cookies.json",
        "input_selector": '.ql-editor',
        "submit_selector": 'button[aria-label="Send message"]',
        "response_selector": 'message-content',
        "wait_selector": 'button[aria-label="Send message"]:not([disabled])',
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
CONSENSUS_THRESHOLD = 0.7  # Shoda potřebná pro konsenzus (0-1)

# Security simulace
SECURITY_MODE = False         # True = kyber-simulace místo coding workflow

# Logování
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "bifrost.log"
