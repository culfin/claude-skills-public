#!/usr/bin/env bash
# Stops the superpowers brainstorm companion for the given session dir, using the
# newest installed stop-server.sh (same version-resolution rationale as companion.sh).
# Usage: companion-stop.sh <session_dir>
set -euo pipefail
GLOB=(~/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/scripts/stop-server.sh)
SP="$(printf '%s\n' "${GLOB[@]}" | sort -V | tail -1)"
if [[ ! -x "$SP" ]]; then
  echo '{"error": "superpowers stop-server not found - is the plugin installed?"}'
  exit 1
fi
exec "$SP" "$@"
