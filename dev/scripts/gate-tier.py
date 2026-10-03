#!/usr/bin/env python3
"""Decides the Quality Gate tier of a phase: `small` or `large`. Read-only.

    gate-tier.py --base <ref> [--type <phase type>] [--tasks <n>] [--gate full] [--root <dir>]

Prints `small` or `large` on the first line, then one `- <reason>` per line. Exit 0 = decided,
2 = usage or git error (nothing on stdout, so a caller never reads a half answer as a tier).

Why a script: the tier decides which checks run, and a judgement call ("this looks small") is
exactly how a risky one-line auth change ends up with the light gate. Size alone never makes a
phase small — a sensitive path or a risk type always makes it large.
"""
import argparse
import re
import subprocess
import sys

MAX_TASKS = 3
MAX_LINES = 400
RISK_TYPES = {"auth", "security", "migration", "data"}
DB_CHANGE = re.compile(r"(^|/)migrations?/|\.sql$|(^|/)schema\.(prisma|sql|rb)$", re.I)
SENSITIVE = re.compile(
    r"(^|/)(auth|login|logout|session|sessions|middleware|security|permissions?)(/|\.|$)"
    r"|(^|/)api/|(^|/)(routes?|actions?|controllers?)/"
    r"|(^|/)migrations?/|\.sql$", re.I)


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=True).stdout


def changed(root, base):
    """(path, changed lines) for tracked changes against base plus untracked files."""
    rows = []
    for line in git(root, "diff", "--numstat", base, "--").splitlines():
        add, rem, path = line.split("\t", 2)
        n = 0 if add == "-" else int(add) + int(rem)
        rows.append((path, n))
    for path in git(root, "ls-files", "--others", "--exclude-standard").splitlines():
        try:
            with open(f"{root}/{path}", "rb") as fh:
                rows.append((path, fh.read().count(b"\n")))
        except OSError:
            rows.append((path, 0))
    return rows


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--type", default="")
    ap.add_argument("--tasks", type=int, default=1)
    ap.add_argument("--gate", default="")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    try:
        git(a.root, "rev-parse", "--verify", f"{a.base}^{{commit}}")
        rows = changed(a.root, a.base)
    except subprocess.CalledProcessError as e:
        print(f"gate-tier: git failed: {e.stderr.strip() or e}", file=sys.stderr)
        return 2
    reasons = []
    lines = sum(n for _, n in rows)
    if a.gate == "full":
        reasons.append("@gate: full")
    if a.type in RISK_TYPES:
        reasons.append(f"risk type @type: {a.type}")
    if a.type == "backend" and any(DB_CHANGE.search(p) for p, _ in rows):
        reasons.append("backend phase with a DB change")
    hits = sorted({p for p, _ in rows if SENSITIVE.search(p)})
    if hits:
        reasons.append("sensitive files: " + ", ".join(hits[:5]) + (" …" if len(hits) > 5 else ""))
    if a.tasks > MAX_TASKS:
        reasons.append(f"{a.tasks} tasks > {MAX_TASKS}")
    if lines > MAX_LINES:
        reasons.append(f"{lines} changed lines > {MAX_LINES}")
    if reasons:
        print("large")
        for r in reasons:
            print(f"- {r}")
    else:
        print("small")
        print(f"- {a.tasks} task(s), {lines} changed lines, no risk type, no sensitive files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
