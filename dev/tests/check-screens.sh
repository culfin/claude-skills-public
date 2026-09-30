#!/usr/bin/env bash
# Renders every building block from dev/companion-screens.md in the real Visual Companion and checks the DOM.
# Regression test after every superpowers update: does the companion run, does every building block render,
# does Mermaid draw? Screenshots go to $OUT (default /tmp) for viewing.
# Usage: dev/tests/check-screens.sh            Exit 0 = all green
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
F="$HERE/../companion-screens.md"
OUT="${OUT:-/tmp}"
test -f "$F" || { echo "FAIL companion-screens.md missing"; exit 1; }
P=$(mktemp -d); J=$("$HERE/../scripts/companion.sh" --project-dir "$P")
URL=$(echo "$J" | python3 -c 'import sys,json;print(json.load(sys.stdin)["url"])')
SD=$(echo "$J" | python3 -c 'import sys,json;print(json.load(sys.stdin)["screen_dir"])')
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; f=0
python3 - "$F" "$SD" <<'PY'
import re, sys
md, sd = sys.argv[1], sys.argv[2]
blocks = re.findall(r"^### Building block: (.+?)\n.*?```html\n(.*?)```", open(md).read(), re.S | re.M)
open(sd + "/.names", "w").write("\n".join(n.strip() for n, _ in blocks) + "\n")
for i, (name, html) in enumerate(blocks):
    open("%s/block-%02d.html" % (sd, i), "w").write(html)
PY
i=0
while IFS= read -r NAME; do
  n=$(printf '%02d' $i)
  cp "$SD/block-$n.html" "$SD/zz-$n-current.html"; touch "$SD/zz-$n-current.html"; sleep 1
  DOM=$("$CH" --headless=new --disable-gpu --virtual-time-budget=8000 --dump-dom "$URL" 2>/dev/null)
  "$CH" --headless=new --disable-gpu --hide-scrollbars --window-size=1400,1000 --virtual-time-budget=8000 --screenshot="$OUT/screen-$n.png" "$URL" >/dev/null 2>&1
  if [ ${#DOM} -gt 500 ]; then echo "ok   $NAME (DOM ${#DOM} chars, $OUT/screen-$n.png)"; else echo "FAIL $NAME (empty)"; f=1; fi
  if grep -q 'class="mermaid"' "$SD/block-$n.html"; then
    if echo "$DOM" | grep -q 'data-processed="true"'; then echo "ok   $NAME: Mermaid rendered"; else echo "FAIL $NAME: Mermaid not rendered"; f=1; fi
  fi
  i=$((i+1))
done < "$SD/.names"
test $i -eq 6 || { echo "FAIL expected 6 building blocks, found $i"; f=1; }
~/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/scripts/stop-server.sh "$(dirname "$SD")" >/dev/null 2>&1
exit $f
