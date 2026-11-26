# Optional setup

## `/dev` stop hook (Claude Code only)

Reminds you once per session to run `/dev check` when code in a roadmap project changed without a
following gate commit. A reminder, not enforcement; Codex does not use it.

Register it:

```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser('~/.claude/settings.json')
s = json.load(open(p)) if os.path.exists(p) else {}
cmd = 'python3 "$HOME/.claude/skills/dev/hooks/gate-check.py"'
stop = s.setdefault('hooks', {}).setdefault('Stop', [])
if not any(cmd in json.dumps(e) for e in stop):
    stop.append({"hooks": [{"type": "command", "command": cmd}]})
open(p, 'w').write(json.dumps(s, indent=2, ensure_ascii=False) + '\n')
PY
```

Remove it: delete the entry whose command contains `dev/hooks/gate-check.py` from `hooks.Stop` in
`~/.claude/settings.json`.

`dev/tests/check-setup.sh` reports the hook as "not registered (optional)" when it is absent and
checks it only when it is there.

## Screens

`/dev` shows UI screens as self-contained HTML pages: in T3 with `html_preview`/`html_render` in the
thread, on other hosts as a file path to open. No server, no port, nothing to configure.

## superpowers on hosts other than Claude Code

Claude Code records the active install itself. Elsewhere, point `/dev` at it:

```bash
export DEV_SUPERPOWERS_ROOT=/path/to/active/superpowers
```

Details: [dev/runtime.md](dev/runtime.md), "Superpowers install"; updates: README, "Skill updates".
