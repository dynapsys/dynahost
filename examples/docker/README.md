# Docker example

This example spins up two simple web services and shows how to bridge them into the LAN
using arpx so that each service gets its own alias IP reachable from other devices.

Steps:

1. Start the stack:

```bash
docker compose -f examples/docker/docker-compose.yml up -d
```

2. Bridge to LAN with alias IPs (requires root):

```bash
sudo arpx compose -f examples/docker/docker-compose.yml --log-level INFO
# If 'sudo arpx' is not found, either run 'make install' first or use:
# sudo $(which arpx) compose -f examples/docker/docker-compose.yml --log-level INFO
```

Optional: add an HTTPS terminator on alias IPs using a self-signed cert:

```bash
sudo arpx compose -f examples/docker/docker-compose.yml \
  --https self-signed --domains myapp.lan --https-port 443
```

The command prints each service with its alias IP and ports, e.g.:

```
web1: http://192.168.1.120:8082
web2: http://192.168.1.121:8083
```

Press Ctrl+C to stop and clean up alias IPs.

Cleanup containers:

```bash
docker compose -f examples/docker/docker-compose.yml down -v
```
