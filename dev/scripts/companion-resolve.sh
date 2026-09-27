#!/usr/bin/env bash
# Finds a superpowers brainstorm-companion script. Order:
#   1. DEV_COMPANION_SCRIPTS_DIR  — the exact directory holding start-server.sh / stop-server.sh
#   2. DEV_SUPERPOWERS_ROOT       — the active superpowers plugin root (any host, e.g. Codex)
#   3. Claude Code plugin cache   — newest installed version (sort -V), so plugin updates need no edit
# Usage: source it, then: SP="$(resolve_companion start-server.sh)"
resolve_companion() {
  local entry="$1" candidate=""
  if [[ -n "${DEV_COMPANION_SCRIPTS_DIR:-}" ]]; then
    candidate="$DEV_COMPANION_SCRIPTS_DIR/$entry"
  elif [[ -n "${DEV_SUPERPOWERS_ROOT:-}" ]]; then
    candidate="$DEV_SUPERPOWERS_ROOT/skills/brainstorming/scripts/$entry"
  else
    local glob=(~/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/scripts/"$entry")
    candidate="$(printf '%s\n' "${glob[@]}" | sort -V | tail -1)"
  fi
  if [[ ! -f "$candidate" ]]; then
    echo "{\"error\": \"superpowers companion script not found ($entry). Set DEV_SUPERPOWERS_ROOT to the active superpowers plugin root.\"}"
    return 1
  fi
  printf '%s\n' "$candidate"
}
