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
- Keep panel binding at loopback; public access needs a separately reviewed TLS setup.
- Do not flush firewall rules, change SSH rules, perform full OS upgrades or reboot
  as part of this installer. Only touch rules labelled `amneziawg-ansible`.
- Keep persistent VPN data on rollback. Follow the README stop procedure.
