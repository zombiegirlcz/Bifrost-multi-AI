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
