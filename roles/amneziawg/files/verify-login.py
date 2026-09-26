"""Verify real login without sending secrets through arguments or output."""
import http.cookiejar
import json
from pathlib import Path
import sys
import ssl
import urllib.error
import urllib.request

scheme = sys.argv[3] if len(sys.argv) > 3 else 'http'
base = f"{scheme}://127.0.0.1:{int(sys.argv[2])}"
password = (Path(sys.argv[1]) / "password.txt").read_text().strip()
cookies = http.cookiejar.CookieJar()
handlers = [urllib.request.HTTPCookieProcessor(cookies)]
if scheme == 'https':
    context = ssl.create_default_context(cafile=str(Path(sys.argv[1]) / 'tls/cert.pem'))
    handlers.append(urllib.request.HTTPSHandler(context=context))
client = urllib.request.build_opener(*handlers)


def login(value):
    return client.open(urllib.request.Request(
        base + "/api/session",
        data=json.dumps({"password": value}).encode(),
        headers={"Content-Type": "application/json"},
    ), timeout=10)


try:
    login("invalid-" + password)
except urllib.error.HTTPError as error:
    assert error.code == 401, "Invalid password did not return HTTP 401"
else:
    raise AssertionError("Invalid password accepted")

with login(password) as response:
    assert json.load(response)["success"] is True
if scheme == 'https':
    assert cookies and all(cookie.secure for cookie in cookies), "Session cookie must be Secure"
with client.open(base + "/api/session", timeout=10) as response:
    assert json.load(response)["authenticated"] is True
with client.open(base + "/api/wireguard/client", timeout=10) as response:
    assert isinstance(json.load(response), list), "Authenticated client API failed"
print("Invalid password rejected; authenticated session and client API verified")
