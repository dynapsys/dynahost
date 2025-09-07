#!/usr/bin/env bash
set -euo pipefail

# Example: CLI usage of dynahost
# Requires root for network changes.

if [[ ${EUID:-0} -ne 0 ]]; then
  echo "This script needs to run as root (sudo)." >&2
  exit 1
fi

# Create 2 virtual IPs with HTTPS (self-signed cert)
# Access from another device:
#   https://<alias_ip_1>:8000  and  https://<alias_ip_2>:8001

arpx up -n 2 --https self-signed --domains myapp.lan --log-level INFO
