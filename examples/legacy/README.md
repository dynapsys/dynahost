# Legacy example

This folder contains an older standalone script kept for reference:

- `network-visible-script.py` – a monolithic prototype for creating alias IPs and running simple servers.

It is not maintained anymore. Prefer the new `arpx` CLI and modular Python APIs in `src/arpx/`.

Recommended alternatives:

- CLI: `examples/cli/` (uses `arpx up`)
- API: `examples/api/` (programmatic use)
- Compose: `examples/docker/` or `examples/podman/`
