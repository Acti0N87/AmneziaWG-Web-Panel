"""Reject conflicting UDP listeners without reading VPN keys or configurations."""
import subprocess
import sys

port = int(sys.argv[1])
assert 1 <= port <= 65535, 'VPN UDP port must be between 1 and 65535'
listeners = subprocess.check_output(
    ['ss', '-H', '-lnup', 'sport', '=', ':' + str(port)], text=True,
).splitlines()
if listeners:
    current = subprocess.run(
        ['awg', 'show', 'wg0', 'listen-port'], capture_output=True, text=True, check=False,
    )
    # The kernel VPN socket has no userspace owner. Even a loopback DNS socket
    # conflicts with the VPN's wildcard bind; never stop another service for it.
    assert (
        current.returncode == 0
        and current.stdout.strip() == str(port)
        and all('users:' not in line for line in listeners)
    ), f'UDP port {port} is occupied by another service; choose a free port'
