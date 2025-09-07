# DynaHost

![PyPI](https://img.shields.io/pypi/v/dynahost)
![Python Versions](https://img.shields.io/pypi/pyversions/dynahost)
![License](https://img.shields.io/github/license/dynapsys/dynahost)
![Build](https://img.shields.io/github/actions/workflow/status/dynapsys/dynahost/ci.yml?branch=main)

Dynamic multi-IP LAN HTTP/HTTPS server manager with ARP visibility and optional Docker/Podman Compose bridging.

DynaHost allows you to:

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

## Installation

Using uv:

```bash
uv pip install dynahost
```

Or with pip:

```bash
pip install dynahost
```

Optional extras:

```bash
# Compose bridging (PyYAML)
uv pip install "dynahost[compose]"

# Test utilities (pytest)
uv pip install "dynahost[test]"
```

## Quick start

Create 3 virtual IPs with HTTP servers (ports starting at 8000):

```bash
sudo dynahost up -n 3
```

Enable HTTPS with a self-signed certificate, include local domains and IPs in SAN:

```bash
sudo dynahost up -n 2 --https self-signed --domains myapp.lan,myapp.local
```

Use mkcert (requires mkcert installed) and include the discovered IPs:

```bash
sudo dynahost up -n 2 --https mkcert --domains myapp.lan
```

Use Let's Encrypt (public DNS must point to your host, and port 80 must be free):

```bash
sudo dynahost up --https letsencrypt --domain myapp.example.com --email you@example.com
```

Start from a specific base IP instead of auto-discovery:

```bash
sudo dynahost up -n 2 --base-ip 192.168.1.150
```

## Docker/Podman Compose bridge

Make your Compose services visible on the LAN by assigning each service an alias IP and forwarding its published TCP ports:

```bash
# in your project directory with docker-compose.yml
sudo dynahost compose -f docker-compose.yml

# or with a specific base IP range
sudo dynahost compose -f docker-compose.yml --base-ip 192.168.1.150

# Podman: use podman-compose with the same file
sudo dynahost compose -f docker-compose.yml
```

Requirements:

- Your services must publish ports to the host (e.g. `"8080:80"` or `{published: 8080, target: 80}`).
- DynaHost forwards `alias_ip:host_port -> 127.0.0.1:host_port`, so services remain bound to localhost.
- For HTTPS services inside containers, TLS still terminates in the container and works end-to-end.

## Examples

- CLI: `examples/cli/run.sh`
- API: `examples/api/simple_api.py`
- Docker Compose: `examples/docker/docker-compose.yml` + `examples/docker/README.md`
- Podman Compose: `examples/podman/docker-compose.yml` + `examples/podman/README.md`

## Certificate utilities

Generate a self-signed certificate into .dynahost/certs:

```bash
dynahost cert self-signed --common-name myapp.lan --names myapp.lan,192.168.1.200
```

Generate mkcert certificate:

```bash
dynahost cert mkcert --names myapp.lan,192.168.1.200
```

Obtain Let's Encrypt certificate (requires root and open port 80):

```bash
sudo dynahost cert letsencrypt --domain myapp.example.com --email you@example.com
```

## Local domain (router dnsmasq) suggestions

Generate suggestions for configuring a local domain on a router running dnsmasq:

```bash
dynahost dns --domain myapp.lan --ip 192.168.1.200 -o dnsmasq.conf
```

This prints a `hosts` entry and `dnsmasq` options (either `address=/domain/ip` or an explicit `host-record`). Apply it on your router (e.g., OpenWrt) and restart dnsmasq.

## Notes

- This tool modifies network configuration (adds/removes IP aliases), announces ARP, and optionally tweaks iptables. Run it on a test machine or ensure you understand the changes.
- Many operations require root: always `sudo` when starting servers or managing IPs.
- For HTTPS with self-signed or mkcert, clients may require trust steps. mkcert typically installs a local CA in your OS trust store.

## For DevOps and junior engineers

- Start quickly with `sudo dynahost up -n 2` and confirm LAN access from a phone.
- Use `--log-level DEBUG` to see detailed logs (`dynahost.*` loggers).
- Bridge your local Compose stack to the LAN with `sudo dynahost compose`.
- Use `dynahost dns` to generate dnsmasq rules for a local domain like `myapp.lan`.

## Contributing

PRs welcome! Check `CHANGELOG.md` and `docs/SPEC.md`. To run unit tests:

```bash
uv pip install -e .
uv pip install pytest
pytest -q
```
