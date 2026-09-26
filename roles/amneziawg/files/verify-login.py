"""Verify real login without sending secrets through arguments or output."""
import base64
import http.cookiejar
import json
from pathlib import Path
import re
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

if len(sys.argv) > 4 and sys.argv[4] == 'proxy':
    directory = Path(sys.argv[1])
    username = (directory / 'nginx-username.txt').read_text().strip()
    proxy_password = (directory / 'nginx-password.txt').read_text().strip()

    def basic_header(value):
        return 'Basic ' + base64.b64encode(f'{username}:{value}'.encode()).decode()

    for path in ['/', '/api/session', '/api/wireguard/client']:
        for headers in [{}, {'Authorization': basic_header('invalid-' + proxy_password)}]:
            try:
                client.open(urllib.request.Request(base + path, headers=headers), timeout=10)
            except urllib.error.HTTPError as error:
                assert error.code == 401, 'Proxy must reject missing or invalid credentials'
                assert 'Basic realm=' in error.headers.get('WWW-Authenticate', '')
            else:
                raise AssertionError('Proxy accepted missing or invalid credentials')
    client.addheaders = [('Authorization', basic_header(proxy_password))]
    with client.open(base + '/api/session', timeout=10) as response:
        session = json.load(response)
        assert session['requiresPassword'] and not session['authenticated']
    try:
        client.open(base + '/api/wireguard/client', timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 401, 'Panel must still require its own login'
    else:
        raise AssertionError('Basic authentication bypassed panel authentication')


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
    clients = json.load(response)
    assert isinstance(clients, list), "Authenticated client API failed"
if len(sys.argv) > 5 and clients:
    # Inspect only the endpoint port in memory; never print a client config/key.
    with client.open(base + '/api/wireguard/client/' + clients[0]['id'] + '/configuration', timeout=10) as response:
        endpoint = re.search(r'^Endpoint\s*=.*:(\d+)\s*$', response.read().decode(), re.MULTILINE)
        assert endpoint and int(endpoint.group(1)) == int(sys.argv[5]), 'Exported VPN endpoint port is incorrect'
print("Invalid password rejected; authenticated session and client API verified")
