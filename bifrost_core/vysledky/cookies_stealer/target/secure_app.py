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
