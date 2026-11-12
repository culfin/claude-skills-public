#!/usr/bin/env python3
"""Keeps ROADMAP.md and STATE.md a state, not a diary, and shows who works on which phase.

    state-check.py check [--root DIR] [--main REF] [--branch NAME]
    state-check.py archive "<milestone>" [--root DIR] [--dry-run]
    state-check.py migrate [--root DIR] [--branch NAME] [--dry-run]

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
- `claimed on <ref>:` the same for every other local branch and every `origin/*` branch (not the
  own one) whose last commit is at most CLAIM_SCAN_DAYS days old. Claims live as a commit on the
  claiming branch; worktrees of one repo share their local branches, so every session on this
  machine sees them without a commit on main. Each phase is reported once, main first.
- `orphan handoff:` a `Handoff — <branch>` heading in STATE.md whose branch exists neither locally
  nor on origin, or is already merged into the main branch: remove the block.
- `long handoff:` a Handoff section with more than HANDOFF_LINES non-empty lines — a handoff keeps
  position, next step and open points; the diary belongs in the commits.
- `phase file invalid:` a `.dev/phase-<N>.md` whose first line is not `Branch: <branch>`.
- `orphan phase file:` a phase file whose branch exists neither locally nor on origin, or whose
  phase is `[x]`/`[—]` in ROADMAP.md on the main branch (after a squash merge the branch is no
  ancestor of main, so only the ROADMAP tells): save its Handoff and Minor sections to
  docs/gates/phase-<N>.md, then delete it (an abandoned phase: ask the user first).
- `phase file missing:` a `[~]`/`[!]` phase claimed by the current branch has no phase file
  (only once the project is migrated; before that `migrate:` applies). Migrated means the marker
  `.dev/.gitkeep` next to ROADMAP.md exists here or on the main branch.
- `branch mismatch:` the phase file names another branch than the claim in ROADMAP.md.
- `migrate:` STATE.md still holds phase sections (Quality Gate, `### Phase N` under `## Phases`,
  Gate summary, CI lines `- <sha> — Phase N …`) — see `migrate`. Until the project is migrated
  this counts parts of every phase; after that only those `migrate` would move for this branch.
- `behind:` the current branch is behind its upstream — ROADMAP.md and STATE.md here are outdated;
  pull first (counts against the last fetch, `check` fetches nothing).

`archive` moves one milestone whose phases are all `[x]`/`[—]` to
`docs/roadmap-archive/<slug>.md` next to ROADMAP.md: its full ROADMAP.md section plus the
`Gate summary — Phase N` sections of its phases from STATE.md. ROADMAP.md keeps the heading and
one line pointing to the archive; nothing is deleted. Gate summaries are moved only when every
phase number of the milestone is unique in ROADMAP.md (numbering restarted per milestone would
make the match ambiguous). `--dry-run` prints what would move and writes nothing.

Phase files `.dev/phase-<N>.md` and gate files `docs/gates/phase-<N>.md` live next to ROADMAP.md;
<N> is the phase id verbatim from ROADMAP.md (3, 6a, 4.1), only `[0-9A-Za-z.]`. Line 1 of a phase
file is `Branch: <branch>`.

`migrate` moves the phase-owned parts of an old STATE.md out of it, one output line per move:
`## Quality Gate — Phase N…`, `### Phase N…` under `## Phases` and `## Handoff — <branch>` (to the
phase claimed `@claim:<branch>@…` in ROADMAP.md) go to `.dev/phase-<N>.md`; `Gate summary — Phase N`
goes to `docs/gates/phase-<N>.md`; CI lines `- <sha> — Phase N <name>: <status>` go to the phase
file, for `[x]`/`[—]` phases to the gate file, as do the Quality Gate and `### Phase N` sections of
such phases; `## Current Position`, `## Progress` and `## Session Continuity` go to
`docs/roadmap-archive/state-<date>.md`. Only parts of the phase claimed by the current branch
(`--branch` overrides it, as for `check`) go to a phase file; parts of a phase claimed by another
branch, of an open unclaimed phase, or a handoff without a claimed phase stay in STATE.md and are
printed as `kept: … (claimed by <b>)` / `kept: … (no claimed phase)`. The `[~]`/`[!]` phase claimed
by the current branch always gets `.dev/phase-<N>.md` (`Branch: <branch>`), even with nothing to
move, and the marker `.dev/.gitkeep` (empty) is always created. Existing targets are extended,
never overwritten; a part whose text is already in its target is not appended again, only removed
from STATE.md (a rerun after a rebase conflict). Nothing is deleted. `--dry-run` prints the moves
and writes nothing.
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
CLAIM_SCAN_DAYS = 14
HANDOFF_LINES = 8
# The title may be bold (`**Phase 3: Login**`, `__…__`); ids are only [0-9A-Za-z.].
PHASE = re.compile(r"^\s*- \[(.)\]\s+(?:\*\*|__)?(Phase\s+(\d[0-9A-Za-z.]*))(.*)$")
CLAIM = re.compile(r"@claim:(\S+)@(\d{4}-\d{2}-\d{2})\b")
HANDOFF = re.compile(r"^#{2,3}\s+(handoff|session continuity)\b", re.I)
HANDOFF_BRANCH = re.compile(r"^#{2,3}\s+handoff\s*[—:-]\s*(\S+)", re.I)
GATE_SUMMARY = re.compile(r"^#{2,4}\s+Gate[- ]summary\b.*?\bPhase\s+(\d[\w.]*)", re.I)
DONE, ACTIVE = "xX—", "~!"
PHASE_FILE = re.compile(r"phase-([0-9A-Za-z.]+)\.md")
PHASE_IN_HEAD = r"\bPhase\s+(\d[0-9A-Za-z.]*)"
QUALITY_GATE = re.compile(r"^##\s+Quality Gate\b.*?" + PHASE_IN_HEAD)
PHASE_HEAD = re.compile(r"^###\s+Phase\s+(\d[0-9A-Za-z.]*)")
CI_LINE = re.compile(r"^\s*- [0-9a-f]{7,40} — Phase\s+(\d[0-9A-Za-z.]*)")
MARKER = ".dev/.gitkeep"
ARCHIVED = re.compile(r"^##\s+(current position|progress|session continuity)\b", re.I)


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


def is_ancestor(root, a, b):
    return git(root, "merge-base", "--is-ancestor", a, b) is not None


def handoffs(lines):
    """[(heading line, number of non-empty body lines)] for every Handoff section, fences ignored."""
    out, fence = [], False
    heads = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^(#+)\s", line)
        if m:
            heads.append((i, len(m.group(1))))
    for k, (i, lvl) in enumerate(heads):
        if not HANDOFF.match(lines[i]):
            continue
        end = next((j for j, l in heads[k + 1:] if l <= lvl), len(lines))
        out.append((lines[i].strip(), sum(1 for l in lines[i + 1:end] if l.strip())))
    return out


def phase_files(root):
    """{phase id: {"path", "branch", "sections"}} of `.dev/phase-<N>.md` next to ROADMAP.md.

    `branch` is None when line 1 is not `Branch: <branch>`; `sections` are the '## ' headings."""
    out = {}
    d = Path(root) / ".dev"
    for f in sorted(d.glob("phase-*.md")) if d.is_dir() else []:
        m = PHASE_FILE.fullmatch(f.name)
        if not m or not f.is_file():
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        b = re.match(r"^Branch:\s*(\S+)\s*$", lines[0]) if lines else None
        out[m.group(1)] = {"path": f".dev/{f.name}", "branch": b.group(1).strip("`") if b else None,
                           "sections": [lines[s].strip() for s, _ in sections(lines, 2)]}
    return out


def migrated(root, ref, prefix):
    """The marker `.dev/.gitkeep` next to ROADMAP.md exists in this checkout or on `ref` (main)."""
    if (Path(root) / MARKER).is_file():
        return True
    return bool(ref) and git(root, "cat-file", "-e", f"{ref}:{prefix}{MARKER}") is not None


def _pid(text):
    return text.rstrip(".")


def plan_migration(slines, own, today, branch):
    """([(line indexes, heading, target, branch)], [(kept heading, reason)]) for STATE.md's phase parts.

    Only parts of phases claimed by `branch` (the current one) move to a phase file; parts of
    phases claimed by another branch stay (`claimed by <b>`). Gate summaries and parts of
    `[x]`/`[—]` phases belong to no branch and go to docs/gates/.

    target is a path relative to ROADMAP.md's folder; branch is the `Branch:` line of a new phase
    file (None for gate and archive files). Each line belongs to at most one move."""
    claimed = {who: pid for pid, (st, who, _) in own.items() if who and st in ACTIVE}
    current = branch
    owner = [None] * len(slines)
    moves, kept = [], []

    def phase_target(pid):
        """(target, Branch line) or (None, reason it stays)."""
        st, who, _ = own.get(pid, (None, None, None))
        if st and st in DONE:
            return f"docs/gates/phase-{pid}.md", None
        if who and who == current:
            return f".dev/phase-{pid}.md", who
        return None, f"claimed by {who}" if who else "no claimed phase"

    def take(a, b, head, target, branch):
        # a part nested in it that an earlier rule already moved keeps its own target
        idx = [i for i in range(a, b) if owner[i] is None]
        if not idx:
            return
        for i in idx:
            owner[i] = len(moves)
        moves.append((idx, head, target, branch))

    for lvl in (2, 3, 4):
        for a, b in sections(slines, lvl):
            m = GATE_SUMMARY.match(slines[a])
            if m:
                take(a, b, slines[a].strip(), f"docs/gates/phase-{_pid(m.group(1))}.md", None)
    phases_sec = [(a, b) for a, b in sections(slines, 2) if re.match(r"^##\s+Phases\s*$", slines[a])]
    candidates = [(a, b, QUALITY_GATE.match(slines[a])) for a, b in sections(slines, 2)]
    candidates += [(a, b, PHASE_HEAD.match(slines[a])) for a, b in sections(slines, 3)
                   if any(pa < a < pb for pa, pb in phases_sec)]
    for a, b, m in sorted(candidates, key=lambda c: c[0]):
        if not m or owner[a] is not None:
            continue
        target, why = phase_target(_pid(m.group(1)))
        if target:
            take(a, b, slines[a].strip(), target, why)
        else:
            kept.append((slines[a].strip(), why))
    for lvl in (2, 3):
        for a, b in sections(slines, lvl):
            if not HANDOFF.match(slines[a]) or ARCHIVED.match(slines[a]) or owner[a] is not None:
                continue
            m = HANDOFF_BRANCH.match(slines[a])
            pid = claimed.get(m.group(1).strip("`")) if m else None
            if pid and own[pid][1] == current:
                take(a, b, slines[a].strip(), f".dev/phase-{pid}.md", current)
            else:
                kept.append((slines[a].strip(), f"claimed by {own[pid][1]}" if pid else "no claimed phase"))
    for i, line in enumerate(slines):
        m = CI_LINE.match(line)
        if not m or owner[i] is not None:
            continue
        target, why = phase_target(_pid(m.group(1)))
        if target:
            take(i, i + 1, line.strip(), target, why)
        else:
            kept.append((line.strip(), why))
    for a, b in sections(slines, 2):
        if ARCHIVED.match(slines[a]) and owner[a] is None:
            take(a, b, slines[a].strip(), f"docs/roadmap-archive/state-{today.isoformat()}.md", None)
    moves.sort()
    return moves, kept


def phase_moves(moves):
    """Moves of phase-titled parts (Quality Gate, ### Phase N, Gate summary, CI lines). Handoffs are
    left to `orphan handoff:`/`long handoff:`, the archived sections hold no phase state."""
    return [m for m in moves if not m[2].startswith("docs/roadmap-archive/") and not HANDOFF.match(m[1])]


def recent_refs(root, today):
    """[(short name, commit)] of local and origin branches with a commit in the last CLAIM_SCAN_DAYS days."""
    raw = git(root, "for-each-ref", "--format=%(refname) %(objectname) %(committerdate:short)",
              "refs/heads", "refs/remotes/origin") or ""
    out = []
    for line in raw.splitlines():
        name, sha, date = line.split()
        if name == "refs/remotes/origin/HEAD":
            continue
        try:
            if (today - datetime.date.fromisoformat(date)).days > CLAIM_SCAN_DAYS:
                continue
        except ValueError:
            continue
        short = name.removeprefix("refs/heads/").removeprefix("refs/remotes/")
        out.append((short, sha))
    return out


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
    for head, n in handoffs(stext.splitlines()):
        if n > HANDOFF_LINES:
            out.append(f"long handoff: '{head}' has {n} lines (limit {HANDOFF_LINES}) — "
                       "keep only position, next step, open points")
    branch = branch if branch is not None else (git(root, "branch", "--show-current") or "")
    ref = main_ref(root, main)
    if ref and not git(root, "rev-parse", "--verify", "-q", ref):
        ref = None
    main_names = {ref, ref.removeprefix("origin/")} if ref else set()
    for line in stext.splitlines():
        m = HANDOFF_BRANCH.match(line)
        if not m:
            continue
        b = m.group(1).strip("`")
        if not b or b == branch or b in main_names:
            continue
        refs = [r for r in (f"refs/heads/{b}", f"refs/remotes/origin/{b}")
                if git(root, "rev-parse", "--verify", "-q", r)]
        if not refs or (ref and all(is_ancestor(root, r, ref) for r in refs)):
            out.append(f"orphan handoff: '{line.strip()}' — branch {b} is gone or merged; remove the block")
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
    prefix = git(root, "rev-parse", "--show-prefix") or ""
    scan = []
    if ref:
        scan.append((ref, git(root, "rev-parse", ref)))
    skip = {ref, branch, f"origin/{branch}"}
    scan += [(name, sha) for name, sha in recent_refs(root, today) if name not in skip]
    seen_sha, reported = set(), set()
    for name, sha in scan:
        if sha in seen_sha:
            continue
        seen_sha.add(sha)
        theirs = git(root, "show", f"{sha}:{prefix}ROADMAP.md")
        for pid, (st, who, when) in phases(theirs or "").items():
            mine = own.get(pid)
            if not mine:
                continue
            if name == ref and st in DONE and mine[0] not in DONE:
                out.append(f"done on {ref}: Phase {pid} [{st}] — mark it here, do not redo it")
            elif st in ACTIVE and who and who != branch and mine[0] == " " and pid not in reported:
                reported.add(pid)
                out.append(f"claimed on {name}: Phase {pid} by {who} since {when} — skip unless the user picks it")
    theirs = phases((git(root, "show", f"{ref}:{prefix}ROADMAP.md") or "") if ref else "")
    files = phase_files(root)
    for pid, f in files.items():
        b = f["branch"]
        if b is None:
            out.append(f"phase file invalid: {f['path']} has no 'Branch:' first line")
            continue
        if not branch_exists(root, b) or theirs.get(pid, (" ",))[0] in DONE:
            out.append(f"orphan phase file: {f['path']} — branch {b} is gone or Phase {pid} is done on "
                       f"{ref or 'main'}; save its Handoff and Minor sections to docs/gates/phase-{pid}.md, "
                       "then delete it (an abandoned phase: ask the user first)")
            continue
        who = own.get(pid, (None, None))[1]
        if who and who != b:
            out.append(f"branch mismatch: {f['path']} says {b}, claim says {who}")
    # Without the marker the project predates phase files: `migrate:` shows the way, not a missing file.
    done = migrated(root, ref, prefix)
    for pid, (st, who, _) in own.items() if done else ():
        if st in ACTIVE and who and branch and who == branch and pid not in files:
            out.append(f"phase file missing: Phase {pid} [{st}] claimed by this branch has no .dev/phase-{pid}.md")
    moves, kept = plan_migration(stext.splitlines(), own, today, branch)
    # Before the migration every session's parts count, so the first one sees them all.
    k = len(phase_moves(moves)) + (0 if done else sum(1 for h, _ in kept if not HANDOFF.match(h)))
    if k:
        out.append(f"migrate: STATE.md holds {k} phase sections — run state-check.py migrate --dry-run")
    upstream = git(root, "rev-parse", "--abbrev-ref", "@{u}")
    if upstream:
        n = int(git(root, "rev-list", "--count", "HEAD..@{u}") or 0)
        if n:
            out.append(f"behind: {branch or 'HEAD'} is {n} commits behind {upstream} — "
                       "pull before trusting ROADMAP/STATE here")
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


def migrate(root, dry_run=False, today=None, branch=None):
    root = Path(root)
    state = root / "STATE.md"
    today = today or datetime.date.today()
    branch = branch if branch is not None else (git(root, "branch", "--show-current") or "")
    own = phases((root / "ROADMAP.md").read_text(encoding="utf-8"))
    # The active phase claimed by this branch always gets its phase file, even with nothing to move.
    create = [f".dev/phase-{pid}.md" for pid, (st, who, _) in own.items()
              if st in ACTIVE and branch and who == branch and not (root / ".dev" / f"phase-{pid}.md").is_file()]
    slines = state.read_text(encoding="utf-8").splitlines() if state.is_file() else []
    moves, kept = plan_migration(slines, own, today, branch)
    create = [c for c in create if c not in {m[2] for m in moves}]
    parts = {}
    for idx, head, target, mbranch in moves:
        chunk = "\n".join(slines[i] for i in idx).strip("\n")
        print(f"{'would move' if dry_run else 'moved'}: '{head}' → {target} ({words(chunk)} words)")
        parts.setdefault(target, [mbranch, []])[1].append(chunk)
    for rel in create:
        print(f"{'would create' if dry_run else 'created'}: {rel} (Branch: {branch})")
    if not (root / MARKER).is_file():
        print(f"{'would create' if dry_run else 'created'}: {MARKER}")
    for head, why in kept:
        print(f"kept: '{head}' ({why})")
    print(f"migrate: {len(moves)} moves, {len(kept)} kept" + (" — dry run, nothing written" if dry_run else ""))
    if dry_run:
        return 0
    (root / MARKER).parent.mkdir(parents=True, exist_ok=True)
    if not (root / MARKER).is_file():
        (root / MARKER).write_text("", encoding="utf-8")
    for rel in create:
        (root / rel).write_text(f"Branch: {branch}\n", encoding="utf-8")
    if not moves:
        return 0
    for target, (mbranch, chunks) in parts.items():
        f = root / target
        f.parent.mkdir(parents=True, exist_ok=True)
        old = f.read_text(encoding="utf-8").rstrip("\n") if f.is_file() else ""
        if not old:
            if mbranch:
                old = f"Branch: {mbranch}"
            elif target.startswith("docs/roadmap-archive/"):
                old = f"# STATE.md — archived {today.isoformat()}"
        new = [c for c in chunks if c.strip() not in old]  # already there: a rerun, not appended again
        if new:
            f.write_text("\n\n".join(([old] if old else []) + new) + "\n", encoding="utf-8")
    taken = {i for idx, *_ in moves for i in idx}
    keep = [l for i, l in enumerate(slines) if i not in taken]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip("\n")
    state.write_text(text + "\n", encoding="utf-8")
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
    m_ = sub.add_parser("migrate")
    m_.add_argument("--root", default=".")
    m_.add_argument("--dry-run", action="store_true")
    m_.add_argument("--branch")
    a = p.parse_args()
    if not (Path(a.root) / "ROADMAP.md").is_file():
        print(f"no ROADMAP.md in {a.root}", file=sys.stderr)
        return 2
    if a.cmd == "archive":
        return archive(a.root, a.milestone, a.dry_run)
    if a.cmd == "migrate":
        return migrate(a.root, a.dry_run, branch=a.branch)
    found = check(a.root, a.main, a.branch)
    for line in found:
        print(line)
    if not found:
        print("state-check: ok")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
