# DynaHost

Dynamic multi-IP LAN HTTP/HTTPS server manager with ARP visibility.

DynaHost allows you to:

- Create multiple virtual IP addresses on a network interface and make them visible to the whole LAN via ARP announcements.
- Run small HTTP/HTTPS servers bound to those IPs for quick testing and service simulation.
- Generate TLS certificates:
  - Self-signed certificates
  - Locally-trusted certificates using mkcert
  - Public certificates using Let's Encrypt (certbot)
- Get suggestions for configuring local domains on your router (dnsmasq) for HTTPS on your LAN.

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
