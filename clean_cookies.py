#!/usr/bin/env python3
"""
Bifrost 2.0 — Cookie Cleaner: vyčistí cookies z prohlížeče na produkční formát

Použití:
  1. Exportuj cookies z prohlížeče jako JSON (Cookie Editor extension)
  2. Ulož do cookies/raw_NAME.json
  3. python clean_cookies.py raw_NAME.json NAME

Příklady:
  python clean_cookies.py raw_gemini.json gemini
  python clean_cookies.py raw_chatgpt.json chatgpt
  python clean_cookies.py raw_claude.json claude
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
COOKIES_DIR = BASE_DIR / "cookies"


def clean_cookies(input_file: str, service_name: str) -> list:
    """Vyčistí cookies — zachová jen důležitá pole."""
    import re
    
    with open(input_file, encoding='utf-8') as f:
        raw_text = f.read().strip()
    
    # Oprav formát: "session[ ... ] → [ ... ]
    if raw_text.startswith('"session['):
        raw_text = raw_text.replace('"session[', '[', 1)
        if raw_text.endswith(']"'):
            raw_text = raw_text[:-1]
    
    # HLAVNÍ OPRAVA: Problematická linie typu: "sameSite": null,": false,
    # Regex: najdi `null,": false,` a nahraď `null,`
    raw_text = re.sub(r'null,": false,', 'null,', raw_text)
    
    # Odstraň neplatné klíče: ": false, (bez prvního ")
    raw_text = re.sub(r'",\s*": false,', ',', raw_text)
    
    # Normalizuj case: "lex" → "Lex", "string" → "String" (v hodnotách)
    raw_text = raw_text.replace('"lex"', '"Lex"')
    raw_text = raw_text.replace('"string"', '"String"')
    
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"   Position: line {e.lineno}, col {e.colno}")
        # Debug: vytiskni okolí chyby
        lines = raw_text.split('\n')
        if e.lineno <= len(lines):
            print(f"   Line: {lines[e.lineno-1]}")
        raise
    
    # Handle both array a "session" wrapper
    if isinstance(data, dict) and "session" in data:
        cookies = data["session"]
    else:
        cookies = data
    
    cleaned = []
    for cookie in cookies:
        cleaned_cookie = {
            "name": cookie.get("name"),
            "value": cookie.get("value"),
            "domain": cookie.get("domain"),
            "path": cookie.get("path", "/"),
            "secure": cookie.get("secure", False),
            "httpOnly": cookie.get("httpOnly", False),
        }
        
        # SameSite oprava case — Playwright chce "Strict"|"Lax"|"None" nebo CHYBÍ
        same_site = cookie.get("sameSite")
        if same_site and same_site != "null":
            if isinstance(same_site, str) and same_site.lower() == "lax":
                cleaned_cookie["sameSite"] = "Lax"
            elif isinstance(same_site, str) and same_site.lower() == "strict":
                cleaned_cookie["sameSite"] = "Strict"
            elif isinstance(same_site, str) and same_site.lower() == "none":
                cleaned_cookie["sameSite"] = "None"
            elif isinstance(same_site, str) and same_site in ("Lax", "Strict", "None"):
                cleaned_cookie["sameSite"] = same_site
        # Pokud sameSite chybí nebo je null, NEULOŽ nic (Playwright default)
        
        # Expiration date pokud existuje
        if "expirationDate" in cookie:
            cleaned_cookie["expirationDate"] = cookie["expirationDate"]
        
        cleaned.append(cleaned_cookie)
    
    return cleaned


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nPříklady souborů:")
        print("  cookies/raw_gemini.json → cookies/gemini_cookies.json")
        print("  cookies/raw_chatgpt.json → cookies/chatgpt_cookies.json")
        print("  cookies/raw_claude.json → cookies/claude_cookies.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    service_name = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"❌ Soubor nenalezen: {input_file}")
        sys.exit(1)
    
    try:
        cleaned = clean_cookies(input_file, service_name)
        output_file = COOKIES_DIR / f"{service_name}_cookies.json"
        
        with open(output_file, "w") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Cookies vyčištěny: {output_file}")
        print(f"📊 Počet cookies: {len(cleaned)}")
        
        # Statistika
        secure_count = sum(1 for c in cleaned if c.get("secure"))
        httponly_count = sum(1 for c in cleaned if c.get("httpOnly"))
        print(f"🔒 Secure: {secure_count}, HttpOnly: {httponly_count}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Neplatný JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Chyba: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
