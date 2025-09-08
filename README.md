# ARPx

![PyPI](https://img.shields.io/pypi/v/arpx)
![Python Versions](https://img.shields.io/pypi/pyversions/arpx)
![License](https://img.shields.io/github/license/dynapsys/arpx)
![Build](https://img.shields.io/github/actions/workflow/status/dynapsys/arpx/ci.yml?branch=main)

**Dynamic multi-IP LAN HTTP/HTTPS server manager with ARP visibility and optional Docker/Podman Compose bridging.**

`arpx` makes local services instantly visible across your network using ARP announcements. It’s ideal for rapid prototyping and testing where you want each service to feel like it’s running on its own host with its own IP and TLS certificate—without touching router configs.

---

## Table of Contents

- [What makes `arpx` different?](#what-makes-arpx-different)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Docker/Podman Compose Bridge](#dockerpodman-compose-bridge)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

---

### What makes `arpx` different?

Typical local dev setups bind everything to `localhost:port`. `arpx` fills the gap by providing:

* 🌐 **LAN visibility** – Services get unique IPs visible to *all* devices on your network.
* 🔑 **HTTPS everywhere** – Built-in cert management (self-signed, mkcert, Let’s Encrypt).
* 🐳 **Container bridging** – Map Docker/Podman Compose services directly to LAN IPs.
* ⚡ **Zero router hacks** – No port forwarding or DNS server required.
* 🧩 **Lightweight & scriptable** – Simple CLI for easy integration into dev/test workflows.

Think of it as giving your LAN **mini cloud-like behavior**, where each service can live on its own IP with real HTTPS.

### Requirements

- Linux with root privileges for network configuration.
- Required tools: `ip`, `arping` (from `iputils-arping` or similar).
- Optional for certificates: `mkcert` or `certbot`.

`arpx` will check for these dependencies at runtime and provide installation hints if they are missing.

### Installation

#### From PyPI (Recommended)

```bash
# Install with pip or uv
pip install arpx

# Install with optional extras for Docker bridging or mDNS
pip install "arpx[compose,mdns]"
```

#### From Repository

For development or to ensure `sudo arpx` works out of the box:

```bash
# This script installs with pip and creates a system-wide symlink
make install
```

### Quick Start

Create 3 virtual IPs with HTTP servers:

```bash
sudo arpx up -n 3
```

Enable HTTPS with a self-signed certificate:

```bash
sudo arpx up -n 2 --https self-signed --domains myapp.lan
```

### Docker/Podman Compose Bridge

Make your Compose services visible on the LAN by assigning each an alias IP:

```bash
# In your project directory with docker-compose.yml
sudo arpx compose -f docker-compose.yml
```

For more detailed examples, see the `examples/` directory.

### Architecture

For a detailed explanation of the internal components and workflows, see the [**Architecture Overview**](docs/architecture.md).

### Contributing

PRs are welcome! To set up a development environment and run tests:

```bash
# Install dev dependencies
make dev

# Run all tests
make test
```

### License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
