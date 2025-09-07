# API example (programmatic use)

This example creates one alias IP and starts an HTTPS server bound to it using a self‑signed certificate. It demonstrates how to use ARPx programmatically via Python APIs.

## Prerequisites

- Linux with sudo privileges
- Tools: `ip`, `arping` (package `iputils-arping`)
- Install the `arpx` CLI and ensure root can find it (optional, not required for this API example):

```bash
make install
# or
bash scripts/install_arpx.sh "compose,mdns"
```

## Run

From the repo root:

Option A (recommended for quick run without installing the package):

```bash
sudo -E PYTHONPATH="$(pwd)/src" python3 examples/api/simple_api.py
```

Option B (install the package first and then run):

```bash
uv pip install -e .
sudo python3 examples/api/simple_api.py
```

The script will:

- Detect your active interface and network
- Allocate one free alias IP in your LAN
- Generate a self‑signed certificate for that IP
- Start an HTTPS server on port 9443 bound to the alias IP

You should see output ending with something like:

```
Now open: https://<alias_ip>:9443
```

Open the URL from another machine in the same LAN (you may need to accept the self‑signed certificate warning).

## Stop and cleanup

Press Ctrl+C. The script handles SIGINT and removes the alias IP and stops the server.
