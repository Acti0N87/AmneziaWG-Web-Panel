"""Reject occupied ports unless held by this deployment during a migration."""
from pathlib import Path
import re
import subprocess
import sys

container = subprocess.run(
    ['docker', 'top', 'amnezia-wg-easy', '-eo', 'pid'],
    capture_output=True, text=True, check=False,
)
container_pids = set(container.stdout.splitlines()[1:]) if container.returncode == 0 else set()
container_pids = {pid.strip() for pid in container_pids}
for port in sys.argv[1:]:
    listeners = subprocess.check_output(
        ['ss', '-H', '-lntp', 'sport', '=', ':' + str(int(port))], text=True,
    )
    for line in listeners.splitlines():
        pids = re.findall(r'pid=(\d+)', line)
        assert pids, f'Cannot determine listener owner on port {port}'
        for pid in pids:
            cgroup = Path(f'/proc/{pid}/cgroup').read_text()
            owned_proxy = '/system.slice/amneziawg-proxy.service' in cgroup
            assert pid in container_pids or owned_proxy, f'Port {port} is occupied by another service'
