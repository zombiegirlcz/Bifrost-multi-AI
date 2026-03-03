#!/bin/bash
set -e

echo "🌈 Bifrost 2.0 — Instalace"
echo "=========================="

# Aktualizace Termuxu
pkg update -y && pkg upgrade -y

# Systémové závislosti
pkg install -y python nodejs git chromium

# Python závislosti
pip install --upgrade pip
pip install playwright asyncio aiofiles rich click difflib2

# Playwright setup
python -m playwright install chromium

# Vytvoření adresářů
mkdir -p cookies output

# Oprávnění
chmod +x main.py

echo ""
echo "✅ Instalace dokončena!"
echo ""
echo "📌 Další kroky:"
echo "1. Exportuj cookies z prohlížeče do složky cookies/"
echo "   - chatgpt_cookies.json"
echo "   - claude_cookies.json"  
echo "   - gemini_cookies.json"
echo "   - copilot_cookies.json"
echo ""
echo "2. Spusť: python main.py --task 'tvoje zadání'"
