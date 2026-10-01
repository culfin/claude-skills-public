#!/usr/bin/env python3
"""Checks the Quality Gate checklist in STATE.md for stale or missing evidence. Read-only.

Every checked item must name its evidence and the state of the code it was checked on:

    - [x] Typecheck + lint + tests — 0 errors, 412 passed @3f9c2a1b7d04

`@<state>` is the git tree id of the working tree (tracked + untracked, .gitignore respected,
without STATE.md and ROADMAP.md, which the gate itself writes), printed by `check-evidence.py id`.
It does not change when that exact content is committed, so a gate commit that contains the checked
content keeps every item valid — and any edit to the code after a check makes that item stale.

    check-evidence.py id                              # current state id
    check-evidence.py check [STATE.md]                # before completing the phase
    check-evidence.py check [STATE.md] --before-commit   # before the gate commit (5j, 5k may be open)

Exit 0 = consistent. Exit 1 = problems, one per line. What it cannot know: whether the evidence
text is true, or whether the checklist lists every required check — that stays the gate's job.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ID_LEN = 12
# Files the gate itself writes while checking; they are bookkeeping, not the code under review.
BOOKKEEPING = ("STATE.md", "ROADMAP.md")
LATER_STEPS = ("gate commit", "ci status check")   # happen after the local checks
ITEM = re.compile(r"^\s*- \[( |x|X)\] (.*)$")
STATE_TAG = re.compile(r"@([0-9a-f]{7,64})\s*$")


def state_id(root):
    """Tree id of the working tree, computed on a throwaway index (the real index is untouched)."""
    root = Path(root)
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, "index"))
        run = lambda *a: subprocess.run(["git", "-C", str(root), *a], env=env, check=True,
                                        capture_output=True, text=True).stdout.strip()
        run("read-tree", "HEAD")
        run("add", "-A")
        # Bookkeeping files count wherever they live: monorepos keep STATE.md/ROADMAP.md next to
        # the app (e.g. apps/web/), not at the root.
        run("rm", "--cached", "-q", "--ignore-unmatch", "--",
            *(f":(glob)**/{name}" for name in BOOKKEEPING))
        return run("write-tree")[:ID_LEN]


def gate_items(text):
    """Checklist items of the (last) '## Quality Gate' section, or None if there is none."""
    lines, inside, found = [], False, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith("## Quality Gate")
            if inside:
                found, lines = True, []
            continue
        if inside:
            m = ITEM.match(line)
            if m:
                lines.append((m.group(1).lower() == "x", m.group(2).strip()))
    return lines if found else None


def check(root, state_file, before_commit=False):
    items = gate_items(Path(state_file).read_text(encoding="utf-8"))
    if items is None:
        return [f"{state_file}: no gate checklist ('## Quality Gate …' section)"]
    current = state_id(root)
    problems = []
    for done, body in items:
        name = body.split(" — ")[0].split(" @")[0].strip()
        if not done:
            if before_commit and name.lower().startswith(LATER_STEPS):
                continue
            problems.append(f"open: {name}")
            continue
        tag = STATE_TAG.search(body)
        evidence = body.split(" — ", 1)[1] if " — " in body else ""
        evidence = STATE_TAG.sub("", evidence).strip()
        if not evidence:
            problems.append(f"no evidence: {name} (write '— <decisive output>' after the item)")
        if not tag:
            problems.append(f"no @state: {name} (append '@{current}' when checked on this state)")
        elif not current.startswith(tag.group(1)[:ID_LEN]) and not tag.group(1).startswith(current):
            problems.append(f"stale: {name} was checked on @{tag.group(1)}, the code is now @{current} — rerun it")
    return problems


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("id")
    c = sub.add_parser("check")
    c.add_argument("state", nargs="?", default="STATE.md")
    c.add_argument("--before-commit", action="store_true")
    a = p.parse_args()
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if not root:
        print("not inside a git repository", file=sys.stderr)
        return 1
    if a.cmd == "id":
        print(state_id(root))
        return 0
    problems = check(root, a.state, a.before_commit)
    for line in problems:
        print(line)
    if not problems:
        print(f"gate evidence consistent @{state_id(root)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
