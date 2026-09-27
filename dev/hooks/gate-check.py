#!/usr/bin/env python3
# dev/hooks/gate-check.py
"""Stop-Hook fuer /dev-Projekte: erinnert EINMAL JE SITZUNG an /dev check, wenn Code geaendert
wurde und danach kein Gate-Commit ([gate-pass]) kam.

Seit 27.09.2026 ein Hinweis an den Nutzer (systemMessage), kein Block mehr: Der Block erschien in
Claude Code als "Stop hook error" und kam nach jedem neuen PR wieder, obwohl der Nutzer den Check
fuer die Sitzung schon abgelehnt hatte. Der Nutzer entscheidet selbst, ob er /dev check aufruft.

- Aktiv nur, wenn vom Arbeitsverzeichnis aufwaerts eine ROADMAP.md liegt (die Suche endet an
  einer Git-Wurzel ohne ROADMAP.md). Dieses Verzeichnis ist die Projektwurzel.
- Kein Block in Sitzungen, in denen /dev geladen wurde (getippter Befehl /dev ... oder
  Skill-Aufruf "dev"): dort fuehrt /dev die Phase und sichert das Gate selbst. Der Roadmap-Status
  taugt dafuer nicht: liegengebliebene [~]-Phasen stehen in vielen Projekten seit Wochen.
- Es zaehlen nur Code-Dateien innerhalb der Projektwurzel; docs/, .scratch/, .claude/,
  .superpowers/ nur direkt an der Wurzel ignoriert, ebenso .worktrees/ (eigene Checkouts), node_modules/ ueberall.
- Signal "Gate gelaufen": der juengste Commit (HEAD und alle lokalen Zweige, auch Worktree-Zweige)
  der Projektwurzel mit [gate-pass] im Betreff (Autor-Zeit) ist nicht
  aelter als die letzte Code-Aenderung (Sekundengenauigkeit). So zaehlen commit -F, git -C und
  Heredocs; fehlgeschlagene Commits und Commits in anderen Repos zaehlen nicht.
- Je Sitzung hoechstens ein Hinweis. Fail-open: fehlender Zeitstempel, scheiterndes git
  oder jeder andere Fehler -> durchlassen.
Bekannte Luecken: Aenderungen per Bash (sed -i, Heredoc, Skripte) und durch Subagenten stehen
nicht als Edit/Write im Haupttranscript und werden nicht gezaehlt.
Herkunft: Pilot-Hook vom 25.09.2026, nach dem Vorbild eines projekteigenen Gate-Hooks.
"""
import datetime
import json
import os
import subprocess
import sys

CODE_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".svelte", ".vue", ".rs", ".py",
            ".go", ".swift", ".kt", ".kts", ".cs", ".sql", ".css", ".scss", ".php", ".module",
            ".inc", ".theme", ".twig", ".sh", ".java", ".rb", ".html")
# .superpowers/: Arbeitsdateien der Superpowers-Skills (Brainstorming-Entwuerfe, Ledger) -
# git-ignoriert, kein Projektcode. Seit 25.09.2026, nach Fehlalarmen auf HTML-Entwuerfen.
ROOT_IGNORED = ("/docs/", "/.scratch/", "/.claude/", "/.worktrees/", "/.superpowers/")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
DEV_COMMAND = "<command-name>/dev</command-name>"
HINT = (
    "DEV-GATE: Code ausserhalb von /dev geaendert, seitdem kein /dev check "
    "(kein Commit mit [gate-pass]). Bei Bedarf /dev check aufrufen - "
    "dieser Hinweis kommt je Sitzung nur einmal."
)


def find_root(start):
    d = os.path.realpath(start)
    while True:
        if os.path.isfile(os.path.join(d, "ROADMAP.md")):
            return d
        if os.path.exists(os.path.join(d, ".git")):
            return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def is_code(path, root):
    if not path:
        return False
    p = os.path.realpath(path).replace("\\", "/")
    r = os.path.realpath(root).replace("\\", "/").rstrip("/")
    if not p.startswith(r + "/"):
        return False
    rel = p[len(r):]
    if rel.startswith(ROOT_IGNORED) or "/node_modules/" in rel:
        return False
    return rel.lower().endswith(CODE_EXT)


def _epoch(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def scan(lines, root):
    pos = last_edit = 0
    last_edit_ts = None
    dev_seen = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if obj.get("type") == "user":
            if not obj.get("isMeta") and DEV_COMMAND in _text(content):
                dev_seen = True
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            pos += 1
            inp = block.get("input")
            if not isinstance(inp, dict):
                continue
            name = block.get("name", "")
            if name in EDIT_TOOLS:
                if is_code(str(inp.get("file_path") or inp.get("notebook_path") or ""), root):
                    last_edit = pos
                    last_edit_ts = _epoch(obj.get("timestamp"))
            elif name == "Skill" and str(inp.get("skill", "")).split(":")[-1] == "dev":
                dev_seen = True
    return last_edit, last_edit_ts, dev_seen


def gate_time(root):
    # Autor-Zeit (%at) statt Commit-Zeit: Rebase, Amend und Cherry-pick setzen die Commit-Zeit
    # neu und wuerden ein altes Gate juenger machen. Marke nur im Betreff (%s) zaehlt; --grep
    # sucht in der ganzen Nachricht, daher wird nachgefiltert.
    r = subprocess.run(
        ["git", "-C", root, "log", "-n", "50", "HEAD", "--branches", "--fixed-strings",
         "--grep=[gate-pass]", "--format=%at%x09%s"],
        capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    newest = 0
    for line in r.stdout.splitlines():
        stamp, _, subject = line.partition("\t")
        if "[gate-pass]" in subject and stamp.isdigit():
            newest = max(newest, int(stamp))
    return newest



def decide(payload, state_dir="/tmp", env=None):
    env = os.environ if env is None else env
    try:
        start = payload.get("cwd") or env.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        root = find_root(start)
        if not root:
            return None
        with open(payload.get("transcript_path"), encoding="utf-8", errors="replace") as fh:
            last_edit, last_edit_ts, dev_seen = scan(fh, root)
    except Exception:
        return None
    if dev_seen:
        return None
    session = str(payload.get("session_id") or "unknown")
    state = os.path.join(state_dir, "dev-gate-%s.hinted" % session)
    if not last_edit or last_edit_ts is None or os.path.exists(state):
        return None
    try:
        gate = gate_time(root)
    except Exception:
        return None
    if gate >= int(last_edit_ts):
        return None
    try:
        with open(state, "w") as fh:
            fh.write(str(last_edit))
    except OSError:
        pass
    return {"systemMessage": HINT}


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    result = decide(payload if isinstance(payload, dict) else {})
    if result:
        print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
