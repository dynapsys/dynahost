# Podman example

This example defines two simple web services using a `docker-compose.yml` compatible file
that can be used with `podman-compose`.

Steps:

1. Start the stack (requires podman-compose):

```bash
podman-compose -f examples/podman/docker-compose.yml up -d
```

2. Bridge to LAN with alias IPs (requires root):

```bash
sudo arpx compose -f examples/podman/docker-compose.yml --log-level INFO
```

Optional HTTPS terminator on alias IPs using mkcert:

```bash
sudo arpx compose -f examples/podman/docker-compose.yml \
  --https mkcert --domains myapp.lan --https-port 443
```

Press Ctrl+C to stop the bridge and clean up alias IPs.
