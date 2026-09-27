#!/usr/bin/env python3
# dev/hooks/gate-check.py
"""Stop hook for /dev projects: reminds about /dev check ONCE PER SESSION when code was changed
and no gate commit ([gate-pass]) followed.

Since 2026-09-27 this is a notice to the user (systemMessage), no longer a block: Claude Code showed
the block as "Stop hook error", and it came back after every new PR even though the user had
already declined the check for the session. The user decides whether to run /dev check.

- Active only if a ROADMAP.md exists in the working directory or one of its parents (the search
  stops at a Git root without ROADMAP.md). That directory is the project root.
- No notice in sessions where /dev was loaded (typed command /dev ... or Skill call "dev"): there
  /dev drives the phase and secures the gate itself. The roadmap status is unsuitable for this:
  stale [~] phases have been sitting in many projects for weeks.
- Only code files inside the project root count; docs/, .scratch/, .claude/, .superpowers/ are
  ignored only directly at the root, as is .worktrees/ (separate checkouts); node_modules/ everywhere.
- Signal "gate has run": the newest commit (HEAD and all local branches, including worktree
  branches) of the project root with [gate-pass] in the subject (author time) is not older than
  the last code change (second precision). This way commit -F, git -C and heredocs count; failed
  commits and commits in other repos do not.
- At most one notice per session. Fail-open: missing timestamp, failing git or any other
  error -> let through.
Known gaps: changes made via Bash (sed -i, heredoc, scripts) and by subagents do not appear as
Edit/Write in the main transcript and are not counted.
Origin: pilot hook from 2026-09-25, modeled on a project-specific gate hook.
"""
import datetime
import json
import os
import subprocess
import sys

CODE_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".svelte", ".vue", ".rs", ".py",
            ".go", ".swift", ".kt", ".kts", ".cs", ".sql", ".css", ".scss", ".php", ".module",
            ".inc", ".theme", ".twig", ".sh", ".java", ".rb", ".html")
# .superpowers/: working files of the Superpowers skills (brainstorming mockups, ledger) -
# git-ignored, not project code. Since 2026-09-25, after false alarms on HTML mockups.
ROOT_IGNORED = ("/docs/", "/.scratch/", "/.claude/", "/.worktrees/", "/.superpowers/")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
DEV_COMMAND = "<command-name>/dev</command-name>"
HINT = (
    "DEV-GATE: Code changed outside /dev, no /dev check since "
    "(no commit with [gate-pass]). Run /dev check if needed - "
    "this notice appears only once per session."
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
    # Author time (%at) instead of commit time: rebase, amend and cherry-pick reset the commit
    # time and would make an old gate look newer. Only the marker in the subject (%s) counts;
    # --grep searches the whole message, hence the post-filtering.
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
