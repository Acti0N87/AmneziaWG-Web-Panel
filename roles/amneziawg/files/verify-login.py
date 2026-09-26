"""Verify real login without sending secrets through arguments or output."""
import http.cookiejar
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

base = f"http://127.0.0.1:{int(sys.argv[2])}"
password = (Path(sys.argv[1]) / "password.txt").read_text().strip()
client = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)


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
with client.open(base + "/api/session", timeout=10) as response:
    assert json.load(response)["authenticated"] is True
with client.open(base + "/api/wireguard/client", timeout=10) as response:
    assert isinstance(json.load(response), list), "Authenticated client API failed"
print("Invalid password rejected; authenticated session and client API verified")
