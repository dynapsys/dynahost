# ARPx Examples

This directory contains runnable examples demonstrating ARPx features.

- CLI: `examples/cli/` – quick start with `arpx up` on alias IPs.
- API: `examples/api/` – programmatic API: create an alias IP and start HTTPS.
- Docker: `examples/docker/` – bridge Docker Compose services to LAN alias IPs.
- Podman: `examples/podman/` – bridge Podman Compose services to LAN alias IPs.
- Legacy: `examples/legacy/` – old standalone script kept for reference.

## Prerequisites

- Linux with sudo privileges.
- Tools: `ip`, `arping` (package `iputils-arping`).
- Docker for the Docker example, and `podman` + `podman-compose` for the Podman example.
- Install ARPx CLI so root can find it:

```bash
make install                # user install + link /usr/local/bin/arpx (fallback /usr/bin)
# or directly
bash scripts/install_arpx.sh "compose,mdns"
```

If you prefer not linking globally, you can run with an absolute binary path:

```bash
sudo $(which arpx) up -n 2
```

## Run

- CLI: see `examples/cli/README.md`
- API: see `examples/api/README.md`
- Docker: see `examples/docker/README.md`
- Podman: see `examples/podman/README.md`

## Smoke tests for examples

Run brief smoke tests (requires sudo and docker/podman where applicable):

```bash
make test-examples
```

Notes:

- In non-interactive environments (no TTY), tests requiring a sudo password are skipped.
- Ensure `ip` and `arping` are installed on the host.
