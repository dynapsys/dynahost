# CLI example (arpx up)

This example starts multiple HTTP/HTTPS endpoints on alias IPs that are visible to your LAN.

## Prerequisites

- Linux with sudo privileges
- Tools: `ip`, `arping` (package `iputils-arping`)
- Install the `arpx` CLI and make it visible to `sudo`:

```bash
make install
# or
bash scripts/install_arpx.sh "compose,mdns"
```

## Run

Create two alias IPs and start HTTPS (self‑signed):

```bash
sudo arpx up -n 2 --https self-signed --domains myapp.lan --log-level INFO
```

You should see endpoints like:

```
https://<alias_ip_1>:8000
https://<alias_ip_2>:8001
```

Press Ctrl+C to stop and clean up.

## Options

- Add mDNS broadcasting so devices can discover names automatically:

```bash
sudo arpx up -n 2 --mdns --mdns-prefix myapp-
```

- Choose a starting IP manually:

```bash
sudo arpx up -n 2 --base-ip 192.168.1.150
```
