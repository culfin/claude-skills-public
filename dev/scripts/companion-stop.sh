#!/usr/bin/env bash
# Stops the superpowers brainstorm companion for the given session dir.
# Usage: companion-stop.sh <session_dir>
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/companion-resolve.sh"
SP="$(resolve_companion stop-server.sh)" || { echo "$SP"; exit 1; }
exec bash "$SP" "$@"
