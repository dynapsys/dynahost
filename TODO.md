# TODO – arpx

- [x] Packaging with uv + pyproject.toml (hatchling, dynamic version)
- [x] CLI entrypoint `arpx` with commands: `up`, `cert`, `dns`, `compose`
- [x] HTTPS support (self-signed, mkcert, Let's Encrypt, custom)
- [x] Logging: switch internals to `logging` with namespaced loggers
- [x] Compose bridge: alias IPs + forwarders for published TCP ports
- [x] README with badges and onboarding for DevOps and juniors
- [x] CHANGELOG.md, docs/SPEC.md
- [x] Examples for CLI, API, Docker, Podman
- [x] Router dnsmasq/OpenWrt samples in `docs/router/`
- [x] Makefile cleanup and new `arpx` targets
- [ ] Add `arpx compose down` to remove alias IPs without Ctrl+C loop
- [x] Optional mDNS (zeroconf) for local name broadcasting
- [ ] Detect and avoid DHCP ranges more robustly (parse DHCP leases if available)
- [ ] nftables backend alternative to iptables
- [ ] Systemd units to run `arpx up`/`arpx compose` as services
- [ ] CI workflows (GitHub Actions) and badges
- [ ] More unit tests and a safe e2e harness with containers in CI (rootless?)
- [ ] Wyjaśnić zasadę działania (schematy/diagramy), architekturę i scenariusze użycia; stworzyć listę 10 przykładów komend z opisem