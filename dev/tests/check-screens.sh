#!/usr/bin/env bash
# Rendert jeden Baustein aus dev/companion-screens.md im echten Visual Companion und prueft das DOM.
# Regressionstest nach jedem superpowers-Update: Laeuft der Companion, rendert jeder Baustein,
# zeichnet Mermaid? Screenshots landen in $OUT (Standard /tmp), zum Ansehen.
# Aufruf: dev/tests/check-screens.sh            Exit 0 = alles gruen
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
F="$HERE/../companion-screens.md"
OUT="${OUT:-/tmp}"
test -f "$F" || { echo "FAIL companion-screens.md fehlt"; exit 1; }
P=$(mktemp -d); J=$("$HERE/../scripts/companion.sh" --project-dir "$P")
URL=$(echo "$J" | python3 -c 'import sys,json;print(json.load(sys.stdin)["url"])')
SD=$(echo "$J" | python3 -c 'import sys,json;print(json.load(sys.stdin)["screen_dir"])')
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; f=0
python3 - "$F" "$SD" <<'PY'
import re, sys
md, sd = sys.argv[1], sys.argv[2]
blocks = re.findall(r"^### Baustein: (.+?)\n.*?```html\n(.*?)```", open(md).read(), re.S | re.M)
open(sd + "/.namen", "w").write("\n".join(n.strip() for n, _ in blocks) + "\n")
for i, (name, html) in enumerate(blocks):
    open("%s/baustein-%02d.html" % (sd, i), "w").write(html)
PY
i=0
while IFS= read -r NAME; do
  n=$(printf '%02d' $i)
  cp "$SD/baustein-$n.html" "$SD/zz-$n-aktuell.html"; touch "$SD/zz-$n-aktuell.html"; sleep 1
  DOM=$("$CH" --headless=new --disable-gpu --virtual-time-budget=8000 --dump-dom "$URL" 2>/dev/null)
  "$CH" --headless=new --disable-gpu --hide-scrollbars --window-size=1400,1000 --virtual-time-budget=8000 --screenshot="$OUT/screen-$n.png" "$URL" >/dev/null 2>&1
  if [ ${#DOM} -gt 500 ]; then echo "ok   $NAME (DOM ${#DOM} Zeichen, $OUT/screen-$n.png)"; else echo "FAIL $NAME (leer)"; f=1; fi
  if grep -q 'class="mermaid"' "$SD/baustein-$n.html"; then
    if echo "$DOM" | grep -q 'data-processed="true"'; then echo "ok   $NAME: Mermaid gerendert"; else echo "FAIL $NAME: Mermaid nicht gerendert"; f=1; fi
  fi
  i=$((i+1))
done < "$SD/.namen"
test $i -eq 9 || { echo "FAIL erwartet 9 Bausteine, gefunden $i"; f=1; }
~/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/scripts/stop-server.sh "$(dirname "$SD")" >/dev/null 2>&1
exit $f
