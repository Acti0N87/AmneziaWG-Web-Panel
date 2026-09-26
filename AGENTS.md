# Repository instructions

- Do not put the deployment server IP address in documentation, including this
  file or project notes. Use a hostname placeholder; keep target addresses only
  in ignored `inventory.local.yml`. Commit only `inventory.example.yml`.
- Use project-local `.venv` and pinned `requirements.txt` / `requirements.yml`.
- Run `.venv/bin/ansible-lint` and playbook syntax checks after Ansible changes.
- Target is Ubuntu 24.04 amd64. Reinspect OS, kernel, interfaces, firewall and
  existing workloads before supporting another host.
- Check mode is preflight only; validate actual runtime and second-run idempotency.
- Never log passwords, bcrypt hashes, Docker environment or WireGuard configs.
  Keep secret-bearing Ansible tasks under `no_log: true`.
- Panel backend must always use HTTP on 127.0.0.1:51821. Public access is enabled
  only by `amneziawg_ui_public: true` via the dedicated `amneziawg-proxy` nginx
  service; disabling the flag stops/disables the proxy, removes its TCP rule and
  renewal cron. Always retain the panel's own password authentication.
- Public port/TLS belong to nginx: `amneziawg_nginx_port` (1..65535 except 51821)
  and `amneziawg_nginx_tls_enabled`. Both have no runtime effect in private mode,
  but configured values must still pass validation. Reject old
  direct-panel port/TLS variables with migration guidance. Check port ownership
  before migration; never stop unrelated services to take their port.
- Basic-auth credentials are generated once under /opt/amneziawg, root-only.
  nginx workers read only the hash under /etc/amneziawg-nginx. Cover every path
  with Basic authentication and strip Authorization before proxying to the panel.
- Keep nginx isolated from distribution/default or unrelated sites. Prevent the
  package from auto-starting a default port 80 listener on initial installation.
- TLS keys stay outside the build context and panel container. Validate nginx
  before activation/reload and explicitly trust its certificate during checks;
  never disable certificate verification. nginx sets Secure cookies for HTTPS.
- Daily renewal uses /etc/cron.d/amneziawg-certificate and a locked atomic helper.
  Reload only the active proxy after nginx validation; retain a retry marker on
  failure. Never start a stopped proxy or restart the VPN container for renewal.
- Verify both authentication layers, localhost binding, nginx listener, private
  mode cleanup and second-run idempotency after proxy changes.
- Do not flush firewall rules, change SSH rules, perform full OS upgrades or reboot
  as part of this installer. Only touch rules labelled `amneziawg-ansible`.
- Keep persistent VPN data on rollback. Follow the README stop procedure.
