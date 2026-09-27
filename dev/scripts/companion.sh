#!/usr/bin/env bash
# Starts the superpowers brainstorm companion (resolution order: companion-resolve.sh).
# If DEV_COMPANION_URL_HOST is set (e.g. a Tailscale name or IP), the server binds
# to all interfaces and advertises that host; otherwise it stays on localhost.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/companion-resolve.sh"
SP="$(resolve_companion start-server.sh)" || { echo "$SP"; exit 1; }
if [[ -n "${DEV_COMPANION_URL_HOST:-}" ]]; then
  exec bash "$SP" --host 0.0.0.0 --url-host "$DEV_COMPANION_URL_HOST" "$@"
fi
exec bash "$SP" "$@"
