#!/usr/bin/env bash
# Checks whether claude-skills is fully set up on this machine (see README,
# section "Setup"). Exit 0 = everything present. Meant for after a fresh install or a move:
# otherwise a missing symlink or hook goes unnoticed - it simply stays silent.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; f=0
t(){ if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; f=1; fi; }
for s in dev deps; do
  t "Symlink ~/.claude/skills/$s -> $REPO/$s" "[ \"\$(readlink ~/.claude/skills/$s)\" = \"$REPO/$s\" ]"
done
t "Stop-Hook dev/hooks/gate-check.py in ~/.claude/settings.json" \
  "python3 -c 'import json,os,sys;s=json.load(open(os.path.expanduser(\"~/.claude/settings.json\")));sys.exit(0 if \"dev/hooks/gate-check.py\" in json.dumps(s.get(\"hooks\",{}).get(\"Stop\",[])) else 1)'"
t "Hook executable and tests green" "[ -x \"$REPO/dev/hooks/gate-check.py\" ] && (cd \"$REPO/dev/hooks\" && python3 -m unittest -q test_gate_check >/dev/null 2>&1)"
t "superpowers companion found (active install)" "(source \"$REPO/dev/scripts/companion-resolve.sh\" && resolve_companion start-server.sh >/dev/null)"
exit $f
