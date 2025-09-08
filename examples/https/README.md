# HTTPS and TLS Usage Examples with arpx

This directory demonstrates how to use `arpx` to serve content over HTTPS using various certificate management methods.

## Prerequisites

- Linux with `sudo` privileges.
- `arpx` installed and properly configured for `sudo`. If not, run `make install` from the main repository directory.
- `mkcert` installed for the mkcert example.

---

## 1. HTTPS Servers with `arpx up`

This command creates virtual IP addresses and starts HTTPS servers on them.

### a) Self-Signed Certificate

The quickest way to run HTTPS for local testing. The browser will show a security warning.

```bash
# Start 2 HTTPS servers with a self-signed certificate
# The certificate will be valid for 'myapp.lan' and the auto-assigned IPs.
sudo arpx up -n 2 --https self-signed --domains myapp.lan
```

### b) Using `mkcert` (recommended for development)

If `mkcert` is installed and its root certificate (CA) is trusted on the system, the browser will not show warnings.

```bash
# Start 2 HTTPS servers with a certificate from mkcert
sudo arpx up -n 2 --https mkcert --domains dev.app.lan
```

### c) Using a Custom Certificate

If you have your own certificate and key files.

```bash
# Start an HTTPS server, providing paths to your own files
sudo arpx up -n 1 --https custom --cert-file /path/to/cert.pem --key-file /path/to/key.pem
```

---

## 2. TLS Termination for Containerized Services (`arpx compose`)

This feature runs a proxy with TLS termination in front of your containers. `arpx` handles HTTPS traffic from the LAN and forwards it as plain HTTP to your services.

```bash
# 1. Start your containers
docker compose -f examples/docker/docker-compose.yml up -d

# 2. Start bridging with TLS termination on port 443
# Traffic to https://<alias_ip>:443 will be decrypted and forwarded to the container.
sudo arpx compose -f examples/docker/docker-compose.yml \
  --https self-signed \
  --domains myapp.lan \
  --https-port 443
```

You can also use `--https mkcert` instead of `self-signed`.
