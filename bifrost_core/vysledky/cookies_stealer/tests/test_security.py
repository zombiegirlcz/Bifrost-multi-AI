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
