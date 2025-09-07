#!/usr/bin/env bash
# Robust installer for arpx CLI that ensures 'sudo arpx' works.
# Usage:
#   scripts/install_arpx.sh [extras]
# Example:
#   scripts/install_arpx.sh "compose,mdns"

set -Eeuo pipefail

EXTRAS="${1:-compose,mdns}"
YELLOW="\033[0;33m"; GREEN="\033[0;32m"; RED="\033[0;31m"; NC="\033[0m"

say() { printf "%b[install]%b %s\n" "$YELLOW" "$NC" "$*"; }
ok() { printf "%b[  OK  ]%b %s\n" "$GREEN" "$NC" "$*"; }
err() { printf "%b[ERROR]%b %s\n" "$RED" "$NC" "$*"; }

ARPX_SPEC="."
if [[ -n "$EXTRAS" ]]; then
  ARPX_SPEC=".[${EXTRAS}]"
fi

say "Installing arpx for current user with extras: [${EXTRAS}]"
if ! command -v arpx >/dev/null 2>&1; then
  if command -v uv >/dev/null 2>&1; then
    if uv tool install --force "${ARPX_SPEC}"; then ok "uv tool install success"; else say "uv failed, trying plain: uv tool install ."; uv tool install --force .; fi
  elif command -v pipx >/dev/null 2>&1; then
    if pipx install --force "${ARPX_SPEC}"; then ok "pipx install success"; else say "pipx failed, trying plain: pipx install ."; pipx install --force .; fi
  else
    python3 -m pip install --user "${ARPX_SPEC}" || python3 -m pip install --user .
  fi
else
  ok "arpx already present at $(command -v arpx)"
fi

ARPX_BIN="$(command -v arpx || true)"
if [[ -z "$ARPX_BIN" && -x "$HOME/.local/bin/arpx" ]]; then
  ARPX_BIN="$HOME/.local/bin/arpx"
fi

if [[ -z "$ARPX_BIN" ]]; then
  err "arpx not found after install. Try: make install-system"
  exit 1
fi

say "Linking arpx so sudo can find it"
# Prefer /usr/local/bin, fallback to /usr/bin if necessary
if ! sudo sh -lc 'test -x /usr/local/bin/arpx'; then
  say "Linking /usr/local/bin/arpx -> $ARPX_BIN"
  sudo ln -sf "$ARPX_BIN" /usr/local/bin/arpx
else
  say "/usr/local/bin/arpx already exists"
fi

if ! sudo sh -lc 'command -v arpx >/dev/null 2>&1'; then
  say "'/usr/local/bin' not in sudo PATH; adding fallback /usr/bin/arpx"
  sudo ln -sf "$ARPX_BIN" /usr/bin/arpx
fi

ok "arpx ready. Try: sudo arpx --help"
