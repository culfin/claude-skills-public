#!/usr/bin/env bash
# Resolves the newest installed superpowers brainstorm companion and starts it
# If DEV_COMPANION_URL_HOST is set (e.g. a Tailscale name or IP), the server binds
# to all interfaces and advertises that host; otherwise it stays on localhost.
# Update-robust: picks the highest version dir via `sort -V`, so the weekly
# superpowers auto-update is transparent — /dev never needs editing on a bump.
#
# If superpowers ever ships from a different marketplace, adjust the glob below
# (this is the single place that knows the cache path).
set -euo pipefail
GLOB=(~/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/scripts/start-server.sh)
SP="$(printf '%s\n' "${GLOB[@]}" | sort -V | tail -1)"
if [[ ! -x "$SP" ]]; then
  echo '{"error": "superpowers brainstorm companion not found — is the plugin installed?"}'
  exit 1
fi
if [[ -n "${DEV_COMPANION_URL_HOST:-}" ]]; then
  exec "$SP" --host 0.0.0.0 --url-host "$DEV_COMPANION_URL_HOST" "$@"
fi
exec "$SP" "$@"
