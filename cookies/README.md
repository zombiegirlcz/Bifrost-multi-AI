# Bifrost 2.0 — Cookie Exporty

## 🍪 Jak exportovat cookies

### 1. Z Chrome/Edge/Brave
- Nainstaluj: [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
- Vstup na požadovanou stránku (chatgpt.com, claude.ai, gemini.google.com)
- Klikni na Cookie-Editor ikonu
- "Export" → JSON
- Ulož do `cookies/raw_SERVICE.json`

### 2. Z Firefox
- Nainstaluj: [Cookie-Editor](https://addons.mozilla.org/firefox/addon/cookie-editor/)
- Stejný postup

### 3. Očisty cookies
```bash
python clean_cookies.py cookies/raw_chatgpt.json chatgpt
python clean_cookies.py cookies/raw_claude.json claude
python clean_cookies.py cookies/raw_gemini.json gemini
```

### 4. Hotové cookies
- `chatgpt_cookies.json` — pro ChatGPT (chat.openai.com / chatgpt.com)
- `claude_cookies.json` — pro Claude (claude.ai)
- `gemini_cookies.json` — pro Gemini (gemini.google.com) ✅ hotovo
- `copilot_cookies.json` — nepoužívá se (Copilot je lokální CLI)

## 📋 Checklist
- [ ] ChatGPT cookies
- [ ] Claude cookies
- [x] Gemini cookies
- [ ] PDFs stránek pro CSS selektory

## 🔒 Bezpečnost
- Cookies se NECOMMITUJÍ (jsou v .gitignore)
- Obsahují auth tokeny — hlídej je!
- Platnost: 1-2 roky (viz expirationDate)
