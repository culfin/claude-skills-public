#!/usr/bin/env bash
# Finds a superpowers brainstorm-companion script. Order:
#   1. DEV_COMPANION_SCRIPTS_DIR  — the exact directory holding start-server.sh / stop-server.sh
#   2. DEV_SUPERPOWERS_ROOT       — the active superpowers plugin root (any host, e.g. Codex)
#   3. Claude Code: the ACTIVE install recorded in ~/.claude/plugins/installed_plugins.json — not
#      simply the newest cache directory, which may belong to an inactive or half-updated install
# Usage: source it, then: SP="$(resolve_companion start-server.sh)"
_active_superpowers_root() {
  python3 -c '
import json, os
p = os.path.expanduser("~/.claude/plugins/installed_plugins.json")
plugins = json.load(open(p)).get("plugins", {})
for key, installs in plugins.items():
    if key.split("@")[0] == "superpowers" and installs:
        print(installs[0].get("installPath", ""))
        break
' 2>/dev/null
}

resolve_companion() {
  local entry="$1" candidate="" root
  if [[ -n "${DEV_COMPANION_SCRIPTS_DIR:-}" ]]; then
    candidate="$DEV_COMPANION_SCRIPTS_DIR/$entry"
  elif [[ -n "${DEV_SUPERPOWERS_ROOT:-}" ]]; then
    candidate="$DEV_SUPERPOWERS_ROOT/skills/brainstorming/scripts/$entry"
  else
    root="$(_active_superpowers_root)"
    [[ -n "$root" ]] && candidate="$root/skills/brainstorming/scripts/$entry"
  fi
  if [[ -z "$candidate" || ! -f "$candidate" ]]; then
    echo "{\"error\": \"superpowers companion script not found ($entry). Set DEV_SUPERPOWERS_ROOT to the active superpowers plugin root.\"}"
    return 1
  fi
  printf '%s\n' "$candidate"
}
