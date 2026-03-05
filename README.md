# 🌈 Bifrost 2.0

**Multi-AI Collaborative Coding System pro Termux**

Bifrost orchestruje debatu mezi více AI modely (Claude, Gemini, GPT) prostřednictvím Monica.im,
vytvářejí konsenzus na nejlepším řešení a GitHub Copilot CLI ho pak implementuje.

## 📦 Obsah

- **`bifrost_core/`** — Jádro systému s orchestrátorem, mozky, pracovníkem a testy

## 🚀 Rychlý start

```bash
cd bifrost_core
chmod +x setup.sh
./setup.sh

# Vyžaduje cookies z Monica.im
python -m main --task "Vytvoř REST API"
```

## 🔑 Předpoklady

1. **Monica.im cookies** — Exportuj z prohlížeče a ulož do `bifrost_core/cookies/monica_cookies.json`
2. **Python 3.11+**
3. **Playwright** (pro automation)

Detaily viz [`bifrost_core/README.md`](bifrost_core/README.md)

## 📚 Dokumentace

Kompletní dokumentace a návod k použití: [`bifrost_core/README.md`](bifrost_core/README.md)

## 🧪 Testy

```bash
cd bifrost_core
pytest tests/ -v
```

## 📄 Licence

MIT
