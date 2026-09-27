#!/usr/bin/env bash
# Prueft, ob claude-skills auf dieser Maschine vollstaendig eingerichtet ist (siehe README,
# Abschnitt "Einrichtung"). Exit 0 = alles da. Gedacht nach Neuinstallation und nach Umzug:
# ein fehlender Symlink oder Hook faellt sonst nicht auf - er schweigt einfach.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; f=0
t(){ if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; f=1; fi; }
for s in dev bug-prospector-neutral deps; do
  t "Symlink ~/.claude/skills/$s -> $REPO/$s" "[ \"\$(readlink ~/.claude/skills/$s)\" = \"$REPO/$s\" ]"
done
t "Stop-Hook dev/hooks/gate-check.py in ~/.claude/settings.json" \
  "python3 -c 'import json,os,sys;s=json.load(open(os.path.expanduser(\"~/.claude/settings.json\")));sys.exit(0 if \"dev/hooks/gate-check.py\" in json.dumps(s.get(\"hooks\",{}).get(\"Stop\",[])) else 1)'"
t "Hook ausfuehrbar und Tests gruen" "[ -x \"$REPO/dev/hooks/gate-check.py\" ] && (cd \"$REPO/dev/hooks\" && python3 -m unittest -q test_gate_check >/dev/null 2>&1)"
t "superpowers-Companion auffindbar" "ls ~/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/scripts/start-server.sh >/dev/null 2>&1"
exit $f
