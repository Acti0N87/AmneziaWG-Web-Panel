# AmneziaWG with Ansible

Installs AmneziaWG and the amnezia-wg-easy web panel on `root@vpn-server.example`.
Replace `vpn-server.example` in commands with your SSH alias or server address;
the deployment address is configured only in gitignored `inventory.local.yml`.
Supported target: Ubuntu 24.04 amd64 with systemd and headers for the running
kernel. The role deliberately rejects other platforms until validated.

Based on [Lyucean's guide](https://lyucean.com/vpn-amneziawg/), adapted for the
actual Ubuntu host and checked against [Amnezia's kernel installation docs](https://docs.amnezia.org/documentation/instructions/install-amneziawg-kernel-module-linux/).
It uses official Docker packages, the native noble Amnezia PPA with a scoped
signing key, a pinned container base image, and host networking with `NET_ADMIN`.
The kernel module loads at boot, Docker restarts the container, and a systemd
unit reapplies the small host firewall rules after Docker starts.

## Install Ansible on macOS

Install [Homebrew](https://brew.sh/) if needed, then run:

```sh
brew install python@3.12 git
git clone git@github.com:Leonorus/ansible-amnesiaWG.git
cd ansible-amnesiaWG
python3.12 -m venv .venv
```

## Install Ansible on Linux

The controller needs Python 3.12 or newer for the pinned Ansible version.
On Ubuntu 24.04 or a recent Debian release with Python 3.12+:

```sh
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git openssh-client
```

On a current Fedora release:

```sh
sudo dnf install -y python3 python3-pip git openssh-clients
```

Then clone the repository and create the virtual environment:

```sh
git clone git@github.com:Leonorus/ansible-amnesiaWG.git
cd ansible-amnesiaWG
python3 --version
python3 -m venv .venv
```

If `python3 --version` is older than 3.12, install a supported Python interpreter
first and use its executable (for example `python3.12`) to create `.venv`.
Linux controller support does not change the target restriction to Ubuntu 24.04.

## Install project dependencies (both platforms)

From the repository root:

```sh
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/ansible-galaxy collection install -r requirements.yml
.venv/bin/ansible --version
```

Ansible runs locally over SSH; it is not installed on the target. The target
needs Python 3 and root or passwordless sudo access. See the
[official Ansible installation guide](https://docs.ansible.com/projects/ansible/latest/installation_guide/intro_installation.html).

## Configure a private inventory and deploy

```sh
cp inventory.example.yml inventory.local.yml
chmod 600 inventory.local.yml
```

Edit `inventory.local.yml`: replace `vpn-server.example` with your target address
and set `ansible_user`. Optionally add `ansible_ssh_private_key_file` with the path
to your SSH key, or use your SSH agent. Do not paste private keys into inventory.
For a sudo account, set its username and use `--ask-become-pass` if required.

The real inventory is gitignored. `ansible.cfg` defaults to the dummy inventory,
so every real deployment requires explicit `-i inventory.local.yml`. Never force
add the local inventory. For multiple servers, use additional aliases under
`vpn.hosts` and `--limit <alias>` to deploy to one host at a time.

```sh
ssh root@vpn-server.example true
.venv/bin/ansible -i inventory.local.yml vpn -m ansible.builtin.ping
.venv/bin/ansible-lint
.venv/bin/ansible-playbook playbook.yml --syntax-check
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml --check --diff
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml
```

SSH host-key checking stays enabled. Verify the server fingerprint when first
connecting. A task-local `.known_hosts` can be used with
`--ssh-common-args='-o UserKnownHostsFile=.known_hosts -o StrictHostKeyChecking=yes'`.

Check mode is **preflight only**: it checks the platform and conflicting packages;
it does not simulate repository installation, DKMS compilation, container startup
or credential generation. Installation performs runtime assertions, followed by
an ordinary second run to verify idempotency. No full OS upgrade or reboot occurs.

Defaults are in `roles/amneziawg/defaults/main.yml`. Override endpoint, external
interface or ports in inventory/group variables. The VPN subnet is `10.8.0.0/24`;
check for overlapping networks before using it on another server. This deployment
was designed for a clean host; inspect existing VPNs, containers and firewalls
before applying elsewhere. Provider firewalls must permit UDP 51820 and SSH.

## Open the panel

By default (`amneziawg_ui_public: false`), the panel serves HTTP on
**127.0.0.1:51821**. Access it through SSH:

```sh
ssh -N -L 51821:127.0.0.1:51821 root@vpn-server.example
```

Open <http://127.0.0.1:51821>. In another terminal, retrieve the generated password:

```sh
ssh root@vpn-server.example 'cat /opt/amneziawg/password.txt'
```

### Public access

To expose the panel, set this boolean under the target host in your private
`inventory.local.yml`:

```yaml
amneziawg_ui_public: true
```

Apply the inventory setting:

```sh
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml
```

Open `http://vpn-server.example:51821` and use the same generated password.
The flag binds the panel to `0.0.0.0` and adds a managed TCP INPUT rule for
`amneziawg_ui_port` (51821 by default). Allow that port in any provider firewall
as well. Authentication remains required. **This is plain HTTP: the flag does
not configure TLS, and credentials/session traffic are not encrypted.**

For a one-off override, use a JSON boolean:

```sh
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml -e '{"amneziawg_ui_public": true}'
```

To make the panel private again, set `amneziawg_ui_public: false` in the local
inventory and rerun the playbook. This restores loopback binding and removes
the managed TCP rule. Switching modes recreates the container and briefly
interrupts VPN connections; existing credentials and client data are retained.

Create a client in the panel and import its QR code/config into AmneziaWG.
Secrets and client keys stay on the server in `/opt/amneziawg`, with root-only
directory access. Back up that directory securely. Do not commit it or paste its
contents into logs. Only the bcrypt hash is passed to the container.

The article's `PASSWORD` setting is replaced with `PASSWORD_HASH`. Port 443 alone
does not enable HTTPS. See the [upstream configuration](https://github.com/eyrafir/amnezia-wg-easy/blob/a64b79fa56ee51ddc41bb1a3dec75bdc7aa2a0fa/src/config.js).
The playbook checks password enforcement, an unauthenticated API rejection,
the selected binding, and the VPN listening port.

The base image bundles old `awg` tools that fail with the current v3 kernel module
(`netlink: attribute type 14 has an invalid length`). The role builds a small
derived image on the target, replacing `awg` with tools built from the pinned
upstream commit in the defaults. The downloaded archive is SHA-256 checked;
compiler packages remain in the build stage. The source and Dockerfile live in
`/opt/amneziawg/build`, separate from secrets. First installation needs outbound
HTTPS access to the package repositories, Docker Hub, Alpine mirrors and GitHub.
The image also includes a checked patch for the upstream authentication middleware:
native Node responses must use `writeHead`/`end`, not Express `status`/`json`.
Without that patch denied requests return HTTP 500 instead of 401. Verification
checks both wrong-password rejection and successful login with the generated
password; all secret-bearing operations suppress Ansible output.

`WG_DEVICE` uses the discovered external interface (`ens3` on this host), so the
container's own NAT rules are correct. Its legacy iptables rules are supplemented
with scoped host iptables-nft INPUT/FORWARD rules. Existing rules/default policies
are never flushed or replaced. TCP 443 is not opened. IPv4 tunnel routing is
configured; client IPv6 behavior should be checked separately.

## Verification and stop procedure

```sh
ssh root@vpn-server.example 'systemctl is-active docker amneziawg-firewall; awg show wg0 listen-port'
ssh root@vpn-server.example 'curl -fsS http://127.0.0.1:51821/api/session'
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml
# Stop the deployment and its automatic restart; retain keys and client data:
.venv/bin/ansible-playbook -i inventory.local.yml rollback.yml
```

Rollback stops the container and removes only the managed host firewall rules.
It leaves installed packages, repositories, module and IP forwarding in place to
avoid disrupting shared host functionality. Run `playbook.yml` to start again.
After a failed partial install, inspect which services exist before rollback.
Kernel/package removal is a separate operation. A reboot is not part of rollback.

For full end-to-end validation, connect an actual external VPN client, confirm a
handshake, DNS resolution and its public exit IP. Server-side checks alone cannot
prove provider UDP firewall behavior or a client tunnel's Internet connectivity.
