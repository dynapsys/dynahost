#!/usr/bin/env bash
# Smoke test runner for ARPx examples.
# - Safely starts each example for a short time using timeout
# - Verifies prerequisites and prints a summary
# - Attempts to clean up containers and alias IPs by sending SIGINT first

set -Eeuo pipefail

YELLOW="\033[0;33m"
GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

PASS=0
FAIL=0
SKIP=0

log() { printf "%b[examples]%b %s\n" "$YELLOW" "$NC" "$*"; }
ok() { printf "%b[ OK ]%b %s\n" "$GREEN" "$NC" "$*"; PASS=$((PASS+1)); }
err() { printf "%b[FAIL]%b %s\n" "$RED" "$NC" "$*"; FAIL=$((FAIL+1)); }
skip() { printf "%b[SKIP]%b %s\n" "$YELLOW" "$NC" "$*"; SKIP=$((SKIP+1)); }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

# Is this running with a TTY (interactive)?
has_tty() { [[ -t 0 && -t 1 ]]; }

TIMEOUT_BIN="$(command -v timeout || true)"

# run_with_timeout <seconds> -- <cmd...>
run_with_timeout() {
  local seconds="$1"; shift
  if [[ "$1" == "--" ]]; then shift; fi
  if [[ -n "$TIMEOUT_BIN" ]]; then
    # send SIGINT first to allow graceful cleanup, then SIGKILL after 5s
    "$TIMEOUT_BIN" --signal=INT --kill-after=5 "$seconds" "$@"
    local rc=$?
    # Exit code 124 means timeout in coreutils; treat as success for a smoke test
    if [[ $rc -eq 124 ]]; then return 0; else return $rc; fi
  else
    # Fallback: background + sleep + INT + KILL
    set +e
    ( "$@" ) &
    local pid=$!
    sleep "$seconds"
    kill -INT "$pid" 2>/dev/null || true
    sleep 3
    kill -KILL "$pid" 2>/dev/null || true
    set -e
    return 0
  fi
}

find_arpx() {
  local arpx_bin
  arpx_bin="$(command -v arpx || true)"
  if [[ -z "$arpx_bin" && -x "$HOME/.local/bin/arpx" ]]; then
    arpx_bin="$HOME/.local/bin/arpx"
  fi
  printf "%s" "$arpx_bin"
}

require_root_tools() {
  local missing=()
  for c in ip arping; do
    have_cmd "$c" || missing+=("$c")
  done
  if (( ${#missing[@]} > 0 )); then
    skip "missing tools: ${missing[*]} (install and re-run)"
    return 1
  fi
  return 0
}

# --- Tests ---

# CLI: arpx up (requires sudo + root network tools)
run_cli_example() {
  log "CLI example: arpx up -n 1 (smoke test)"
  local arpx_bin="$1"
  if ! require_root_tools; then return 0; fi
  if ! have_cmd sudo; then skip "sudo not available"; return 0; fi
  if ! sudo -n true 2>/dev/null; then
    if ! has_tty; then
      skip "sudo requires TTY for password; skipping in non-interactive environment"
      return 0
    fi
    log "sudo may prompt for password"
  fi
  if run_with_timeout 15 sudo "$arpx_bin" up -n 1 --log-level INFO; then
    ok "CLI example ran (timed run)"
  else
    err "CLI example failed"
  fi
}

# API: examples/api/simple_api.py (requires sudo)
run_api_example() {
  log "API example: simple_api.py (smoke test)"
  if ! require_root_tools; then return 0; fi
  if ! have_cmd sudo; then skip "sudo not available"; return 0; fi
  if ! sudo -n true 2>/dev/null && ! has_tty; then
    skip "sudo requires TTY for password; skipping in non-interactive environment"
    return 0
  fi
  if run_with_timeout 20 sudo python3 examples/api/simple_api.py; then
    ok "API example ran (timed run)"
  else
    err "API example failed"
  fi
}

# Docker: examples/docker/docker-compose.yml + arpx compose (requires docker + sudo)
run_docker_example() {
  log "Docker example: docker-compose.yml + arpx compose (smoke test)"
  if ! have_cmd docker; then skip "docker not installed"; return 0; fi
  if ! have_cmd sudo; then skip "sudo not available"; return 0; fi
  if ! sudo -n true 2>/dev/null && ! has_tty; then
    skip "sudo requires TTY for password; skipping in non-interactive environment"
    return 0
  fi
  local arpx_bin="$1"
  set +e
  docker compose -f examples/docker/docker-compose.yml up -d
  local up_rc=$?
  set -e
  if [[ $up_rc -ne 0 ]]; then err "docker compose up failed"; return 0; fi
  if run_with_timeout 20 sudo "$arpx_bin" compose -f examples/docker/docker-compose.yml --log-level INFO; then
    ok "Docker compose bridge ran (timed run)"
  else
    err "Docker compose bridge failed"
  fi
  set +e
  docker compose -f examples/docker/docker-compose.yml down -v >/dev/null 2>&1
  set -e
}

# Podman: examples/podman/docker-compose.yml + arpx compose (requires podman-compose + sudo)
run_podman_example() {
  log "Podman example: docker-compose.yml + arpx compose (smoke test)"
  if ! have_cmd podman-compose; then skip "podman-compose not installed"; return 0; fi
  if ! have_cmd sudo; then skip "sudo not available"; return 0; fi
  if ! sudo -n true 2>/dev/null && ! has_tty; then
    skip "sudo requires TTY for password; skipping in non-interactive environment"
    return 0
  fi
  local arpx_bin="$1"
  set +e
  podman-compose -f examples/podman/docker-compose.yml up -d
  local up_rc=$?
  set -e
  if [[ $up_rc -ne 0 ]]; then err "podman-compose up failed"; return 0; fi
  if run_with_timeout 20 sudo "$arpx_bin" compose -f examples/podman/docker-compose.yml --log-level INFO; then
    ok "Podman compose bridge ran (timed run)"
  else
    err "Podman compose bridge failed"
  fi
  set +e
  podman-compose -f examples/podman/docker-compose.yml down -v >/dev/null 2>&1
  set -e
}

main() {
  local arpx_bin
  arpx_bin="$(find_arpx)"
  if [[ -z "$arpx_bin" ]]; then
    err "arpx not found. Run: make install"
    exit 1
  fi
  log "Using arpx: $arpx_bin"

  run_cli_example "$arpx_bin"
  run_api_example
  run_docker_example "$arpx_bin"
  run_podman_example "$arpx_bin"

  echo
  printf "Summary: PASS=%d FAIL=%d SKIP=%d\n" "$PASS" "$FAIL" "$SKIP"
  if (( FAIL > 0 )); then exit 1; fi
}

main "$@"
