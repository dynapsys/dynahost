# ARPx

![PyPI](https://img.shields.io/pypi/v/arpx)
![Python Versions](https://img.shields.io/pypi/pyversions/arpx)
![License](https://img.shields.io/github/license/dynapsys/dynahost)
![Build](https://img.shields.io/github/actions/workflow/status/dynapsys/dynahost/ci.yml?branch=main)
![Coverage](https://img.shields.io/badge/Coverage-32%25-green)

**Dynamic multi-IP LAN HTTP/HTTPS server manager with ARP visibility and optional Docker/Podman Compose bridging.**

`arpx` makes local services instantly visible across your network using ARP announcements. It’s ideal for rapid prototyping and testing where you want each service to feel like it’s running on its own host with its own IP and TLS certificate—without touching router configs.

---

## Table of Contents

- [What makes `arpx` different?](#what-makes-arpx-different)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Real-World Use Case: Solving Port Conflicts in Docker Projects](#real-world-use-case-solving-port-conflicts-in-docker-projects)
- [Docker/Podman Compose Bridge](#dockerpodman-compose-bridge)
- [Architecture](#architecture)
- [Navigation Menu](#navigation-menu)
- [Contributing](#contributing)
- [Author](#author)
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

### Real-World Use Case: Solving Port Conflicts in Docker Projects

Imagine you're working on multiple Docker-based projects simultaneously. One project, already running on your local machine, occupies port 80 for its web server. You need to test a new project that also defaults to port 80. Normally, you'd face a dilemma: either modify the new project's configuration (and potentially dig through someone else's code to update hardcoded port references and URIs), or stop the first project to free up the port. Both options are time-consuming and disruptive to your workflow.

With `arpx`, this problem disappears. Here's how it works:

- **Dynamic IP Allocation**: `arpx` generates new, unique IP addresses within your local network's DHCP range. These virtual IPs are assigned to your services, so you don't need to worry about port conflicts on your primary machine IP.
- **Zero Configuration**: Instead of reconfiguring ports or URIs in your Docker project, `arpx` bridges the services to these new IPs. For instance, even if port 80 is occupied on your machine, you can run the new project's service on port 80 of a dynamically assigned IP.
- **LAN Visibility**: These IPs are visible across your local network, allowing you to test from other devices (like a phone or another computer) without touching router settings.

**Scenario Example**:
A developer named Alex is running a web app on `localhost:80`. He clones a new open-source project that also binds to port 80 by default. Instead of editing the project's `docker-compose.yml` or source code (which could have hardcoded URIs and untested default port assumptions), Alex uses `arpx`:

```bash
# Bridge the new project's services to unique LAN IPs
sudo arpx compose -f docker-compose.yml
```

`arpx` assigns new IPs (e.g., `192.168.1.120` and `192.168.1.121`) to each service in the Docker Compose file, mapping their ports without conflicts. Alex can now access the new app at `http://192.168.1.120:80` while his original app remains on `localhost:80`. No code changes, no downtime.

**Addressing Common Doubts**:
- *Can't Docker just redirect traffic to different ports?* While Docker allows port mapping (e.g., `-p 8080:80`), this often isn't enough. Many projects have hardcoded URIs or dependencies on specific ports across multiple services, requiring extensive reconfiguration and testing. `arpx` sidesteps this by providing entirely new IPs, avoiding the need to touch port configurations.
- *Why not run Docker in a virtual environment?* Virtual environments or separate workstations add overhead and complexity. `arpx` keeps everything on your local machine, seamlessly integrating with your existing setup.

This makes `arpx` uniquely powerful for developers dealing with complex, pre-built projects or needing to test across multiple network-visible IPs without router hacks.

### Docker/Podman Compose Bridge

Make your Compose services visible on the LAN by assigning each an alias IP:

```bash
# In your project directory with docker-compose.yml
sudo arpx compose -f docker-compose.yml
```

For more detailed examples, see the `examples/` directory.

### Architecture

For a detailed explanation of the internal components and workflows, see the [**Architecture Overview**](docs/architecture.md).

### Navigation Menu

Explore the project structure and key files:
- **Documentation:**
  - [Architecture Overview](docs/architecture.md) - Understand the internal design and workflows.
  - [Specification](docs/SPEC.md) - Detailed technical specification.
- **Core Code:**
  - [CLI Entry Point](src/arpx/cli.py) - Main command-line interface logic.
  - [Network Manager](src/arpx/network.py) - Handles virtual IPs and ARP announcements.
  - [Certificate Utilities](src/arpx/certs.py) - TLS certificate generation.
- **Tests:**
  - [Unit Tests for Network](tests/unit/test_network.py) - Tests for network operations.
  - [Unit Tests for Certs](tests/unit/test_certs.py) - Tests for certificate handling.
  - [Unit Tests for Utils](tests/unit/test_utils.py) - Tests for utility functions.

### Contributing

Contributions are welcome! Here's how you can get involved:

1. **Setup Development Environment:**
   ```bash
   # Clone the repository if you haven't already
   git clone https://github.com/dynapsys/dynahost.git
   cd dynahost

   # Install development dependencies
   make dev
   ```
2. **Run Tests:**
   ```bash
   # Run all tests to ensure nothing is broken
   make test
   ```
3. **Coding Guidelines:**
   - Follow PEP 8 for Python code style.
   - Use type hints where applicable.
   - Add unit tests for new functionality.
   - Format code with `make format` before committing.
4. **Submit a Pull Request:**
   - Create a branch for your feature or bugfix.
   - Commit your changes with descriptive messages.
   - Push your branch to the repository.
   - Open a pull request with a clear description of your changes.

For major changes, please open an issue first to discuss what you would like to change.

### Author

- **Name:** Dynapsys Team
- **Contact:** [GitHub Issues](https://github.com/dynapsys/dynahost/issues)

### License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
