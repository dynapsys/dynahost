# ARPx

![PyPI](https://img.shields.io/pypi/v/arpx)
![Python Versions](https://img.shields.io/pypi/pyversions/arpx)
![License](https://img.shields.io/github/license/dynapsys/arpx)
![Build](https://img.shields.io/github/actions/workflow/status/dynapsys/arpx/ci.yml?branch=main)

Dynamic multi-IP LAN HTTP/HTTPS server manager with ARP visibility and optional Docker/Podman Compose bridging.

## arpx — Multi-IP LAN Server & Compose Bridge

`arpx` is a lightweight **multi-IP LAN HTTP/HTTPS server manager** that makes local services instantly visible across your network using **ARP announcements**.
It’s ideal for **rapid prototyping, testing, and LAN demos** where you want each service to feel like it’s running on its own host with its own IP and TLS certificate — without touching router configs or setting up complex reverse proxies.

---

### What makes `arpx` different?

Typical local dev setups bind everything to `localhost:port`. Tools like **ngrok/localtunnel** tunnel services out to the cloud, while **Traefik/Caddy/nginx-proxy** are heavy production-grade proxies.

`arpx` fills the gap:

* 🌐 **LAN visibility** – Services get unique IPs visible to *all* devices on your network.
* 🔑 **HTTPS everywhere** – Built-in cert management (self-signed, mkcert, Let’s Encrypt).
* 🐳 **Container bridging** – Map Docker/Podman Compose services directly to LAN IPs.
* ⚡ **Zero router hacks** – No port forwarding, no DNS server required (but dnsmasq snippets are suggested).
* 🧩 **Lightweight & scriptable** – Simple CLI, easy integration into dev/test workflows.

Think of it as giving your LAN **mini cloud-like behavior**, where each microservice can live on its own IP with real HTTPS, testable from phones, TVs, laptops, and other devices.


ARPx allows you to:

- Create multiple virtual IP addresses on a network interface and make them visible to the whole LAN via ARP announcements.
- Run small HTTP/HTTPS servers bound to those IPs for quick testing and service simulation.
- Generate TLS certificates:
  - Self-signed certificates
  - Locally-trusted certificates using mkcert
  - Public certificates using Let's Encrypt (certbot)
- Get suggestions for configuring local domains on your router (dnsmasq) for HTTPS on your LAN.
- Bridge Docker/Podman Compose services into the LAN using alias IPs so other devices can connect directly.

## Where this helps

- Prototyping microservices reachable from other devices in the office/home LAN without changing router config.
- QA and demos: give each service its own IP and test HTTP/HTTPS from phones, TVs, laptops.
- Edge and lab setups where DNS is limited; use ARP visibility + local router dnsmasq snippets.
- Junior developers and DevOps can quickly test HTTPS with self-signed or mkcert certs.

> Tip for juniors: start with `--https self-signed` in a test LAN, then switch to mkcert for trusted local certs.

## Requirements

- Linux, root privileges for network configuration
- Utilities: `ip`, `ping`, `arping` (package: iputils-arping), `arp` (package: net-tools)
- Optional: `iptables` for firewall rules
- Optional for certificates:
  - `mkcert` for locally-trusted certs (https://github.com/FiloSottile/mkcert)
  - `certbot` and reachable port 80 for Let's Encrypt



---

### Use cases

* **Prototyping microservices**: spin up multiple APIs on separate IPs, test from any device.
* **QA and demos**: showcase apps with “real” IPs instead of messy `localhost:8080`.
* **Edge/lab setups**: where DNS is limited or unavailable, ARP makes services discoverable.
* **Learning DevOps/networking**: juniors can explore ARP, IP aliasing, and HTTPS hands-on.

---

### Feature summary

* Create multiple **virtual IP addresses** per interface with ARP broadcasts.
* Run lightweight **HTTP/HTTPS servers** bound to each IP.
* Generate **TLS certificates**:

  * 🔒 Self-signed
  * ✅ Locally-trusted (`mkcert`)
  * 🌍 Public (`Let’s Encrypt`)
* Bridge **Docker/Podman Compose** stacks into the LAN with alias IPs.
* Generate **dnsmasq snippets** for local domains.

---

### At a glance: comparison

| Tool                    | Strengths                            | Where `arpx` wins                   |
| ----------------------- | ------------------------------------ | ----------------------------------- |
| **ngrok / localtunnel** | Cloud tunneling, public exposure     | LAN-first, no internet needed       |
| **Traefik / Caddy**     | Production reverse proxy, automation | Lighter, zero config, LAN ARP       |
| **mkcert**              | Local certs                          | Adds IPs + servers + LAN vis        |
| **docker-compose**      | Popular for dev setups               | Direct LAN access, no port juggling |

---


## ARPx Installation

Using uv (from PyPI):

```bash
uv pip install arpx
```

Or with pip:

```bash
pip install arpx
```

Optional extras:

```bash
# Compose bridging (PyYAML)
uv pip install "arpx[compose]"

# Test utilities (pytest)
uv pip install "arpx[test]"
uv pip install "arpx[mdns]"  # mDNS broadcasting support
```

### Install via Makefile or script (ensures `sudo arpx` works)

From the repository root, run:

```bash
make install                # installs for current user and links /usr/local/bin/arpx (fallback /usr/bin)
```

Alternatively, run the installer script directly with optional extras:

```bash
bash scripts/install_arpx.sh "compose,mdns"
```

### Install CLI as a user tool (recommended for local dev)

If you're developing locally from this repository, install the CLI into `~/.local/bin`:

```bash
uv tool install --force .
```

This creates an `arpx` launcher in `~/.local/bin`. If you use `sudo` to run network operations, run with an absolute path so root can find it:

```bash
sudo $(which arpx) up -n 2
sudo $(which arpx) compose -f docker-compose.yml
```

## Quick start

Create 3 virtual IPs with HTTP servers (ports starting at 8000):

```bash
sudo arpx up -n 3
```

Enable HTTPS with a self-signed certificate, include local domains and IPs in SAN:

```bash
sudo arpx up -n 2 --https self-signed --domains myapp.lan,myapp.local
```

Use mkcert (requires mkcert installed) and include the discovered IPs:

```bash
sudo arpx up -n 2 --https mkcert --domains myapp.lan
```

Use Let's Encrypt (public DNS must point to your host, and port 80 must be free):

```bash
sudo arpx up --https letsencrypt --domain myapp.example.com --email you@example.com
```

Start from a specific base IP instead of auto-discovery:

```bash
sudo arpx up -n 2 --base-ip 192.168.1.150
```

## Docker/Podman Compose bridge

Make your Compose services visible on the LAN by assigning each service an alias IP and forwarding its published TCP ports:

```bash
# in your project directory with docker-compose.yml
sudo arpx compose -f docker-compose.yml

# or with a specific base IP range
sudo arpx compose -f docker-compose.yml --base-ip 192.168.1.150

# Podman: use podman-compose with the same file
sudo arpx compose -f docker-compose.yml
```

Requirements:

- Your services must publish ports to the host (e.g. `"8080:80"` or `{published: 8080, target: 80}`).
- arpx forwards `alias_ip:host_port -> 127.0.0.1:host_port`, so services remain bound to localhost.
- For HTTPS services inside containers, TLS still terminates in the container and works end-to-end.

### mDNS broadcasting (optional)

Enable mDNS so devices can discover services by name (requires `arpx[mdns]`):

```bash
sudo arpx up -n 2 --mdns --mdns-prefix myapp-
# or for compose
sudo arpx compose -f docker-compose.yml --mdns
```

Services will appear as `_http._tcp.local.` or `_https._tcp.local.` with instance names like `myapp-1._http._tcp.local.`

## Examples

- CLI: `examples/cli/run.sh`
- API: `examples/api/simple_api.py`
- Docker Compose: `examples/docker/docker-compose.yml` + `examples/docker/README.md`
- Podman Compose: `examples/podman/docker-compose.yml` + `examples/podman/README.md`

### Testing examples (smoke tests)

Run all examples briefly with automatic cleanup (requires sudo and docker/podman where applicable):

```bash
make test-examples
```

Notes:

- In non-interactive environments (no TTY), tests requiring a sudo password are skipped.
- Ensure `ip` and `arping` are installed on the host.

## Certificate utilities

Generate a self-signed certificate into .arpx/certs:

```bash
arpx cert self-signed --common-name myapp.lan --names myapp.lan,192.168.1.200
```

Generate mkcert certificate:

```bash
arpx cert mkcert --names myapp.lan,192.168.1.200
```

Obtain Let's Encrypt certificate (requires root and open port 80):

```bash
sudo arpx cert letsencrypt --domain myapp.example.com --email you@example.com
```

## Local domain (router dnsmasq) suggestions

Generate suggestions for configuring a local domain on a router running dnsmasq:

```bash
arpx dns --domain myapp.lan --ip 192.168.1.200 -o dnsmasq.conf
```

This prints a `hosts` entry and `dnsmasq` options (either `address=/domain/ip` or an explicit `host-record`). Apply it on your router (e.g., OpenWrt) and restart dnsmasq.

See also sample configs in `docs/router/`:

- `docs/router/dnsmasq.conf.example`
- `docs/router/hosts.example`
- `docs/router/openwrt-uci.sh`

## Notes

- This tool modifies network configuration (adds/removes IP aliases), announces ARP, and optionally tweaks iptables. Run it on a test machine or ensure you understand the changes.
- Many operations require root: always `sudo` when starting servers or managing IPs.
- For HTTPS with self-signed or mkcert, clients may require trust steps. mkcert typically installs a local CA in your OS trust store.

## For DevOps and junior engineers

- Start quickly with `sudo arpx up -n 2` and confirm LAN access from a phone.
- Use `--log-level DEBUG` to see detailed logs (`arpx.*` loggers).
- Bridge your local Compose stack to the LAN with `sudo arpx compose`.
- Use `arpx dns` to generate dnsmasq rules for a local domain like `myapp.lan`.

## Contributing

PRs welcome! Check `CHANGELOG.md` and `docs/SPEC.md`. To run unit tests:

```bash
uv pip install -e .
uv pip install pytest
pytest -q
```

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details. If you distribute this software, please include the license and NOTICE where appropriate.

