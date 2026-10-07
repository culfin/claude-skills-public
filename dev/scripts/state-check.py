#!/usr/bin/env python3
"""Keeps ROADMAP.md and STATE.md a state, not a diary, and shows who works on which phase.

    state-check.py check [--root DIR] [--main REF] [--branch NAME]
    state-check.py archive "<milestone>" [--root DIR] [--dry-run]

`check` is read-only. It prints one line per finding and exits 1 if there is any, 0 if none,
2 on a usage error (no ROADMAP.md). Findings:

- `size:` STATE.md over STATE_LIMIT words or ROADMAP.md over ROADMAP_LIMIT words. Every session
  start reads both; one project measured 71 000 words in STATE.md and 120 000 in ROADMAP.md, read
  again on every turn. With STATE.md too large the three largest sections follow; with ROADMAP.md
  too large, every completed milestone is listed as `archivable:`.
- `handoff:` a Handoff (or Session Continuity) heading below line HANDOFF_TOP — a reader that shows
  the first lines of a file never reaches it (one project had it at line 1021).
- `claimed:` a `[~]`/`[!]` phase claimed by another branch (`@claim:<branch>@<YYYY-MM-DD>`):
  another session works on it; skip it unless the user picks it.
- `stale claim:` its branch exists neither locally nor on origin, or the claim is older than
  STALE_DAYS days: ask the user before taking it over.
- `unclaimed:` a `[~]`/`[!]` phase without a claim (from before claims, or a forgotten one).
- `done on <main>:` the phase is `[x]`/`[—]` in ROADMAP.md on the main branch but not here —
  finished elsewhere, mark it instead of redoing it. `claimed on <main>:` the main branch shows a
  claim by another branch for a phase that is still `[ ]` here. Needs a current `git fetch`.

`archive` moves one milestone whose phases are all `[x]`/`[—]` to
`docs/roadmap-archive/<slug>.md` next to ROADMAP.md: its full ROADMAP.md section plus the
`Gate summary — Phase N` sections of its phases from STATE.md. ROADMAP.md keeps the heading and
one line pointing to the archive; nothing is deleted. Gate summaries are moved only when every
phase number of the milestone is unique in ROADMAP.md (numbering restarted per milestone would
make the match ambiguous). `--dry-run` prints what would move and writes nothing.
"""
import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

STATE_LIMIT = 3000
ROADMAP_LIMIT = 8000
HANDOFF_TOP = 80
STALE_DAYS = 7
PHASE = re.compile(r"^\s*- \[(.)\]\s+(Phase\s+(\d[\w.]*))(.*)$")
CLAIM = re.compile(r"@claim:(\S+)@(\d{4}-\d{2}-\d{2})\b")
HANDOFF = re.compile(r"^#{2,3}\s+(handoff|session continuity)\b", re.I)
GATE_SUMMARY = re.compile(r"^#{2,4}\s+Gate[- ]summary\b.*?\bPhase\s+(\d[\w.]*)", re.I)
DONE, ACTIVE = "xX—", "~!"


def words(text):
    return len(text.split())


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def sections(lines, level):
    """(start, end) line ranges of headings of exactly `level` '#', fenced code ignored."""
    out, fence, start = [], False, None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
        if fence:
            continue
        m = re.match(r"^(#+)\s", line)
        if m and len(m.group(1)) <= level:
            if start is not None:
                out.append((start, i))
                start = None
            if len(m.group(1)) == level:
                start = i
    if start is not None:
        out.append((start, len(lines)))
    return out


def phases(text):
    """{phase id: (state char, claim branch or None, claim date or None)} in file order."""
    out = {}
    for line in text.splitlines():
        m = PHASE.match(line)
        if m:
            c = CLAIM.search(m.group(4))
            out[m.group(3)] = (m.group(1), c.group(1) if c else None, c.group(2) if c else None)
    return out


def milestones(text):
    """[(heading, start, end, [(phase id, state char)])] for every '## ' section that lists phases."""
    lines = text.splitlines()
    out = []
    for s, e in sections(lines, 2):
        ps = [(m.group(3), m.group(1)) for m in map(PHASE.match, lines[s:e]) if m]
        if ps:
            out.append((lines[s][3:].strip(), s, e, ps))
    return out


def main_ref(root, given):
    if given:
        return given
    head = git(root, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if head:
        return head
    for ref in ("origin/main", "origin/master"):
        if git(root, "rev-parse", "--verify", "-q", ref):
            return ref
    return None


def branch_exists(root, name):
    return any(git(root, "rev-parse", "--verify", "-q", ref) for ref in
               (f"refs/heads/{name}", f"refs/remotes/origin/{name}"))


def check(root, main=None, branch=None, today=None):
    root = Path(root)
    roadmap, state = root / "ROADMAP.md", root / "STATE.md"
    today = today or datetime.date.today()
    rtext = roadmap.read_text(encoding="utf-8")
    stext = state.read_text(encoding="utf-8") if state.is_file() else ""
    out = []
    if words(stext) > STATE_LIMIT:
        lines = stext.splitlines()
        big = sorted(((words("\n".join(lines[s:e])), lines[s].strip()) for s, e in sections(lines, 2)),
                     reverse=True)[:3]
        out.append(f"size: STATE.md has {words(stext)} words (limit {STATE_LIMIT}); largest: "
                   + "; ".join(f"{h} ({n})" for n, h in big))
    if words(rtext) > ROADMAP_LIMIT:
        out.append(f"size: ROADMAP.md has {words(rtext)} words (limit {ROADMAP_LIMIT})")
        lines = rtext.splitlines()
        done = [(h[:60], words("\n".join(lines[s:e]))) for h, s, e, ps in milestones(rtext)
                if all(st in DONE for _, st in ps)]
        if done:
            out.append(f"archivable: {len(done)} completed milestones, {sum(n for _, n in done)} words — "
                       + "; ".join(h for h, _ in done[:5]) + ("; …" if len(done) > 5 else ""))
    for n, line in enumerate(stext.splitlines(), 1):
        if HANDOFF.match(line) and n > HANDOFF_TOP:
            out.append(f"handoff: '{line.strip()}' at line {n} — move it into the first {HANDOFF_TOP} lines")
    branch = branch if branch is not None else (git(root, "branch", "--show-current") or "")
    own = phases(rtext)
    for pid, (st, who, when) in own.items():
        if st not in ACTIVE:
            continue
        if not who:
            out.append(f"unclaimed: Phase {pid} [{st}] — claim it before resuming")
            continue
        age = (today - datetime.date.fromisoformat(when)).days
        if not branch_exists(root, who):
            out.append(f"stale claim: Phase {pid} by {who} — branch gone; ask before taking it over")
        elif age > STALE_DAYS and who != branch:
            out.append(f"stale claim: Phase {pid} by {who} since {when} ({age} days); ask before taking it over")
        elif who != branch:
            out.append(f"claimed: Phase {pid} by {who} since {when} — skip unless the user picks it")
    ref = main_ref(root, main)
    if ref and git(root, "rev-parse", "--verify", "-q", ref):
        prefix = git(root, "rev-parse", "--show-prefix") or ""
        theirs = git(root, "show", f"{ref}:{prefix}ROADMAP.md")
        for pid, (st, who, when) in phases(theirs or "").items():
            mine = own.get(pid)
            if not mine:
                continue
            if st in DONE and mine[0] not in DONE:
                out.append(f"done on {ref}: Phase {pid} [{st}] — mark it here, do not redo it")
            elif st in ACTIVE and who and who != branch and mine[0] == " ":
                out.append(f"claimed on {ref}: Phase {pid} by {who} since {when} — skip unless the user picks it")
    return out


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "milestone"


def archive(root, name, dry_run=False, today=None):
    root = Path(root)
    roadmap, state = root / "ROADMAP.md", root / "STATE.md"
    rtext = roadmap.read_text(encoding="utf-8")
    hits = [m for m in milestones(rtext) if name.lower() in m[0].lower()]
    if len(hits) != 1:
        print(f"archive: {len(hits)} milestones match '{name}' — give a unique part of the heading", file=sys.stderr)
        return 2
    heading, s, e, ps = hits[0]
    ids = [i for i, _ in ps]
    open_ = [i for i, st in ps if st not in DONE]
    if open_:
        print(f"archive: {heading} still has open phases: " + ", ".join(f"Phase {i}" for i in open_), file=sys.stderr)
        return 2
    rlines = rtext.splitlines()
    rel = f"docs/roadmap-archive/{slug(heading)}.md"
    target = root / rel
    body = "\n".join(rlines[s:e]).rstrip()
    all_ids = [i for m in milestones(rtext) for i, _ in m[3]]
    unique = all(all_ids.count(i) == 1 for i in ids)
    moved, slines = [], []
    if state.is_file():
        slines = state.read_text(encoding="utf-8").splitlines()
        if unique:
            for lvl in (2, 3, 4):
                for a, b in sections(slines, lvl):
                    m = GATE_SUMMARY.match(slines[a])
                    if m and m.group(1) in ids:
                        moved.append((a, b))
    moved.sort()
    summaries = "\n\n".join("\n".join(slines[a:b]).rstrip() for a, b in moved)
    date = (today or datetime.date.today()).isoformat()
    print(f"archive: {heading} — {len(ids)} phases, {words(body)} words, {len(moved)} gate summaries → {rel}")
    if not unique:
        print("archive: phase numbers repeat in ROADMAP.md — gate summaries stay in STATE.md")
    if dry_run:
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    old = target.read_text(encoding="utf-8") if target.is_file() else ""
    part = f"# {heading} — archived {date}\n\n{body}\n"
    if summaries:
        part += f"\n## Gate summaries (from STATE.md)\n\n{summaries}\n"
    target.write_text((old + "\n" if old else "") + part, encoding="utf-8")
    first, last = ids[0], ids[-1]
    span = f"Phase {first}" if first == last else f"Phase {first} – Phase {last}"
    stub = [rlines[s], "", f"Done: {len(ids)} phases ({span}) — details in `{rel}`", ""]
    roadmap.write_text("\n".join(rlines[:s] + stub + rlines[e:]).rstrip() + "\n", encoding="utf-8")
    if moved:
        keep = [l for i, l in enumerate(slines) if not any(a <= i < b for a, b in moved)]
        state.write_text("\n".join(keep).rstrip() + "\n", encoding="utf-8")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--root", default=".")
    c.add_argument("--main")
    c.add_argument("--branch")
    a_ = sub.add_parser("archive")
    a_.add_argument("milestone")
    a_.add_argument("--root", default=".")
    a_.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not (Path(a.root) / "ROADMAP.md").is_file():
        print(f"no ROADMAP.md in {a.root}", file=sys.stderr)
        return 2
    if a.cmd == "archive":
        return archive(a.root, a.milestone, a.dry_run)
    found = check(a.root, a.main, a.branch)
    for line in found:
        print(line)
    if not found:
        print("state-check: ok")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
