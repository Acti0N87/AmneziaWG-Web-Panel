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
.venv/bin/python -m unittest discover -s tests -v
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
before applying elsewhere. Provider firewalls must permit the configured VPN UDP
port (`amneziawg_port`, default 51820) and SSH.

## Configure the VPN UDP port

Set `amneziawg_port` under the target host in your ignored inventory. It accepts
an integer from **1 to 65535**, including privileged ports such as 53 and 443:

```yaml
amneziawg_port: 443
```

```sh
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml
```

The VPN uses UDP, independently of nginx's TCP port. VPN UDP 443 and nginx TCP
443 can run together. UDP 53 is supported only when available: a local DNS
resolver bound even to a loopback address can conflict with the VPN's wildcard
listener. The playbook checks for conflicting UDP sockets before changing the
firewall or container and refuses to stop or reconfigure another service.

A port change recreates the VPN container and briefly interrupts connections.
Server listening port, newly exported client endpoints and managed firewall rules
use the same setting. **Existing imported clients must update their Endpoint port
or download/re-import their configuration from the panel.** Update provider
firewall rules too. To undo a change, restore the previous `amneziawg_port`, reapply,
and restore client endpoint ports. Changing a port does not make VPN packets into
DNS or HTTPS traffic.

## Open the panel privately

The panel always serves plain HTTP on **127.0.0.1:51821**. By default,
`amneziawg_ui_public: false`, so the nginx proxy is disabled and no public TCP
port is opened. Access the panel through SSH:

```sh
ssh -N -L 51821:127.0.0.1:51821 root@vpn-server.example
```

Open <http://127.0.0.1:51821>. Retrieve the existing panel password in another terminal:

```sh
ssh root@vpn-server.example 'cat /opt/amneziawg/password.txt'
```

## Public access through nginx

Set these variables under the target host in the ignored `inventory.local.yml`:

```yaml
amneziawg_ui_public: true
amneziawg_nginx_port: 443
amneziawg_nginx_tls_enabled: true
amneziawg_nginx_username: admin
```

Then deploy:

```sh
.venv/bin/ansible-galaxy collection install -r requirements.yml
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml
```

Open `https://vpn-server.example/`. First sign in to nginx's browser Basic-auth
prompt, then use the panel's existing password on its login screen. Both layers
remain required. Retrieve the generated nginx credentials over verified SSH:

```sh
ssh root@vpn-server.example 'cat /opt/amneziawg/nginx-username.txt /opt/amneziawg/nginx-password.txt'
```

Ansible generates an independent random Basic-auth password once on the server.
The username defaults to `admin` and is configurable. Plaintext credentials and
the bcrypt hash live under `/opt/amneziawg` with root-only access and are retained
on redeployment. nginx workers read only a hash from
`/etc/amneziawg-nginx/htpasswd` (`root:www-data`, mode `0640`). Secret-bearing tasks
suppress output. Do not put credentials in inventory, commands, Git, or logs.

`amneziawg_ui_public` is the sole switch for public access: it enables the dedicated
`amneziawg-proxy.service`, which forwards to `http://127.0.0.1:51821`, and adds a
managed TCP firewall rule. The backend never listens publicly. nginx validates
Basic authentication on every path and removes its Authorization header before
forwarding requests. The distribution's default nginx site is not started on a
new installation; existing unrelated nginx services and sites are left intact.

`amneziawg_nginx_port` selects the public TCP port (default **80**, allowed
1–65535 except **51821**, reserved for the backend).
`amneziawg_nginx_tls_enabled` selects HTTPS (default **false**). Configured values must remain valid even in private mode. Both settings only
affect nginx while `amneziawg_ui_public: true`. For HTTP use port 80 and TLS false;
HTTP sends Basic credentials and panel sessions without encryption, so use HTTPS
for public deployments. Changing the port alone does not change the protocol.
Ensure the selected TCP port is allowed by your provider firewall.

The playbook rejects ports owned by unrelated services. Port changes reload nginx
and replace the old managed firewall rule. Set the previous port and reapply to
undo a port change. Set `amneziawg_ui_public: false` and reapply to stop/disable the
proxy, remove its managed TCP rule and remove certificate-renewal cron. Stored
nginx port/TLS settings are ignored in private mode; localhost HTTP remains
available through SSH. Switching proxy modes does not recreate the VPN container.

### Migration from direct public panel access

Keep `amneziawg_ui_public`, rename `amneziawg_ui_port` to `amneziawg_nginx_port`,
and rename `amneziawg_tls_enabled` to `amneziawg_nginx_tls_enabled` in local inventory.
Old port/TLS variable names are rejected explicitly. A former public port of
51821 must change (for example to 443 with TLS). The first migration recreates the
panel container on localhost, briefly interrupting VPN connections; panel/client
data and the existing certificate are retained. Subsequent nginx port, TLS, and
publication changes do not restart the VPN container.

### HTTPS with a self-signed certificate

nginx terminates TLS 1.2/1.3 and sets Secure, HttpOnly, SameSite=Lax session cookies
when HTTPS is enabled. There is no public plaintext listener or HTTP redirect.
The playbook creates a 3072-bit RSA key and a self-signed certificate valid for
365 days. Subject and issuer use the neutral name `Restricted`; neither names
AmneziaWG. It covers `amneziawg_host` (the configured VPN endpoint) and localhost,
including IP SANs for numeric addresses. Update `amneziawg_host` and reapply when
changing the address. TLS files remain under `/opt/amneziawg/tls` outside the image
build context; the panel container has no TLS key or certificate mount.

Upgrading from the old branded certificate reissues it with the neutral name,
preserving the private key and endpoint SANs. nginx reloads the replacement;
refresh any explicit browser/client trust of the old self-signed certificate.
Future automatic renewals retain the neutral name from the updated CSR.

Browsers show a trust warning until you explicitly trust the self-signed
certificate. Retrieve only the public certificate over verified SSH and check its
SHA-256 fingerprint before trusting it:

```sh
ssh root@vpn-server.example 'openssl x509 -in /opt/amneziawg/tls/cert.pem -noout -fingerprint -sha256'
scp root@vpn-server.example:/opt/amneziawg/tls/cert.pem /tmp/amneziawg-cert.pem
# curl prompts for the nginx password; use your configured username:
curl --cacert /tmp/amneziawg-cert.pem --user admin https://vpn-server.example/api/session
```

Keep `key.pem` on the server. Deployment checks explicitly trust the generated
certificate, verify its SAN, reject missing/wrong Basic credentials, and exercise
both authentication layers and Secure cookies through HTTPS. See the nginx
[Basic authentication](https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html)
and [cookie flags](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cookie_flags)
documentation for the proxy directives used.

### Automatic certificate renewal

With public mode and nginx TLS enabled, `/etc/cron.d/amneziawg-certificate` runs
daily at **03:17 in the server's timezone** as root. It renews when fewer than
30 days remain, using the existing private key and CSR. A lock prevents overlapping
renewals; the new certificate is verified and atomically installed. The helper
validates nginx configuration and reloads only the active `amneziawg-proxy`
service. It never restarts the VPN container or starts a stopped proxy. A failed
validation/reload leaves a marker for retry on the next run. Logs use the
`amneziawg-tls` syslog tag.

```sh
ssh root@vpn-server.example 'cat /etc/cron.d/amneziawg-certificate'
ssh root@vpn-server.example 'journalctl -t amneziawg-tls'
# Check now; a certificate with more than 30 days left stays unchanged:
ssh root@vpn-server.example /usr/local/sbin/amneziawg-renew-certificate
# Force renewal and nginx reload (changes the certificate fingerprint):
ssh root@vpn-server.example '/usr/local/sbin/amneziawg-renew-certificate --force'
```

Refresh clients that explicitly trust the old certificate after renewal. The
fingerprint changes even though the key is retained. Disabling nginx TLS removes
the cron job and serves HTTP on the configured nginx port; set the intended HTTP
port explicitly. Disabling public mode stops the proxy and removes cron regardless
of stored TLS settings. Certificates and credentials are retained.

Create a client in the panel and import its QR code/config into AmneziaWG.
Secrets and client keys stay under `/opt/amneziawg`; back it up securely. Only the
panel's bcrypt hash is passed to the container. The article's `PASSWORD` setting
is replaced with `PASSWORD_HASH`.

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
are never flushed or replaced. Only the selected public nginx TCP port is opened. IPv4 tunnel routing is
configured; client IPv6 behavior should be checked separately.

## Verification and stop procedure

```sh
ssh root@vpn-server.example 'systemctl is-active docker amneziawg-firewall; awg show wg0 listen-port'
ssh root@vpn-server.example 'curl -fsS http://127.0.0.1:51821/api/session'
# With public mode enabled, also verify the dedicated proxy:
ssh root@vpn-server.example 'systemctl is-active amneziawg-proxy && nginx -t -c /etc/amneziawg-nginx/nginx.conf'
.venv/bin/ansible-playbook -i inventory.local.yml playbook.yml
# Stop the deployment and its automatic restart; retain keys and client data:
.venv/bin/ansible-playbook -i inventory.local.yml rollback.yml
```

Rollback stops/disables the managed nginx proxy and container, removes the
renewal cron job, and removes only the managed host firewall rules. Credentials,
certificates and VPN client data are retained.
It leaves installed packages, repositories, module and IP forwarding in place to
avoid disrupting shared host functionality. Run `playbook.yml` to start again.
After a failed partial install, inspect which services exist before rollback.
Kernel/package removal is a separate operation. A reboot is not part of rollback.

For full end-to-end validation, connect an actual external VPN client, confirm a
handshake, DNS resolution and its public exit IP. Server-side checks alone cannot
prove provider UDP firewall behavior or a client tunnel's Internet connectivity.
