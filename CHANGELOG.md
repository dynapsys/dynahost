# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [0.0.3] - 2025-09-07

- Add Docker/Podman Compose bridge: per-service alias IPs + TCP forwarders
- Optional HTTPS terminator on alias IPs (self-signed/mkcert/LE/custom)
- New modules: `compose.py`, `proxy.py`, `terminator.py`, `bridge.py`
- CLI: new `compose` subcommand with HTTPS options
- Logging overhaul in `network.py`, `server.py`, `certs.py`
- Examples: CLI, API, Docker, Podman under `examples/`
- Tests: unit (compose parser, proxy forwarder), e2e (compose bridge)
- README: badges, use-cases for DevOps and juniors

## [0.0.2] - 2025-09-07

- Packaging improvements, dynamic version via hatch
- Initial docs: `docs/SPEC.md`, `CHANGELOG.md`
- CLI polish and certificate utilities

## [0.0.1] - 2025-09-07

- Initial public alpha release of DynaHost
- Multi-IP HTTP/HTTPS servers visible across the LAN
- TLS certificate utilities (self-signed, mkcert, Let's Encrypt, custom)
- Local domain (dnsmasq/router) suggestions helper
- uv packaging and Makefile for publishing
- CLI entrypoint `dynahost`
- Basic README and examples scaffolding
