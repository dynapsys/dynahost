#!/usr/bin/env bash
set -euo pipefail

# Example: CLI usage of arpx
# Requires root for network changes.

if [[ ${EUID:-0} -ne 0 ]]; then
  echo "This script needs to run as root (sudo)." >&2
  exit 1
fi

# Resolve arpx binary even when running under sudo (root PATH)
ARPX_BIN="${ARPX:-}"
if [[ -z "${ARPX_BIN}" && -n "${SUDO_USER:-}" ]]; then
  ARPX_BIN=$(sudo -u "${SUDO_USER}" sh -lc 'command -v arpx' 2>/dev/null || true)
fi
if [[ -z "${ARPX_BIN}" ]]; then
  ARPX_BIN=$(command -v arpx || true)
fi
if [[ -z "${ARPX_BIN}" ]]; then
  echo "arpx not found in PATH. Install with: 'uv tool install --force .' and run via 'sudo $(which arpx) ...'" >&2
  exit 1
fi

# Create 2 virtual IPs with HTTPS (self-signed cert)
# Access from another device:
#   https://<alias_ip_1>:8000  and  https://<alias_ip_2>:8001

"${ARPX_BIN}" up -n 2 --https self-signed --domains myapp.lan --log-level INFO
