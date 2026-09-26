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
- Default to loopback. Public access is explicitly controlled by
  `amneziawg_ui_public: true`; keep password authentication enabled in both modes.
  Document that the flag does not enable TLS. Turning it off must remove the
  managed TCP rule and restore loopback binding.
- TLS is controlled separately by `amneziawg_tls_enabled`. Use the generated
  certificate as explicit trust for HTTPS checks; never disable validation.
  Keep TLS keys outside the build context and mount the TLS directory read-only.
  Certificate changes must restart the running container to load the new files.
- Custom port and TLS apply only in public mode. When `amneziawg_ui_public` is
  false, always use plain HTTP on localhost:51821 and remove renewal cron,
  regardless of stored port/TLS settings. Use effective settings in runtime checks.
- Daily renewal uses `/etc/cron.d/amneziawg-certificate` and a locked, atomic helper.
  It must never start a stopped deployment. Disabling TLS removes the cron job.
- Admin port is `amneziawg_ui_port`, an integer from 1 to 65535 (default 51821).
  Check the new port is free before changing a live deployment; verify both
  the new listener and removal of the old managed port rule.
- Do not flush firewall rules, change SSH rules, perform full OS upgrades or reboot
  as part of this installer. Only touch rules labelled `amneziawg-ansible`.
- Keep persistent VPN data on rollback. Follow the README stop procedure.
