#!/usr/bin/env python3
"""Detects a project's `$TECH_STACKS` from section 1 of stack/INDEX.md. Read-only.

    detect-stack.py [--root <dir>] [--json] [--index <stack/INDEX.md>]
    detect-stack.py --triggers --step <4a|4c|gate> [--type <@type>] [--root <dir>]

Prints `stacks: <id>, …` and `groups: <group>, …` (`none` when empty), or with `--json`
{"stacks": [...], "groups": [...]}; ids in the order of the index rows. Exit 0 = detected,
2 = a broken index row or bad usage (message on stderr, nothing on stdout).

Why a script: detection is mechanical, and reading the whole index for it cost every session a
thousand words. The index stays the only list: each indicator cell is read as backticked tokens —
`x` in dependencies (package.json dependencies or devDependencies), `glob` with `text` (a file
matching glob that contains text; several texts joined by "or"), every `"x"` in double quotes a
dependency too, `dir/` (a directory),
`**/name/` (a directory at any depth up to 3), anything else a file or directory glob — and
"(no web stack above)" skips the row when a row above already counted as web. The "Also" cell
gives the groups ("counts as web") and implied ids ("implies `rust`").

Where it looks: the project root and the workspace members named by package.json `workspaces` or
pnpm-workspace.yaml `packages`; in each, its own files and those one directory down (`App/App.csproj`),
never inside node_modules, .git, build output or vendored code.

`--triggers` prints, verbatim, only the lines of tech-stack-triggers.md that the session needs for
one step. Text before its first `## ` heading is the file's preamble and never printed; the blocks
(paragraph, list item, table row) after it and before the first step lead-in hold for every step; a bold lead-in naming 4a, 4c or 5c (= gate) opens a section for those steps. A block is kept
when every "`<id>` in `$TECH_STACKS`" it names was detected and, if it or its lead-in says
"`@type:` is `x` or `y`", the given type is one of them — so an unknown or missing type keeps the
type-independent lines only. Then the section-2 rows of stack/INDEX.md for the detected ids and the
step (gate = 5c and 5g), with the "How." and "Limits." paragraphs (and "WordPress rows." with a
wordpress row). Lines starting with `# ` are the script's own headings.
"""
import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"node_modules", ".git", "vendor", "target", "dist", "build", ".next", "Pods", ".venv",
             "venv", "__pycache__", ".worktrees", ".build", "DerivedData"}
MAX_DEPTH = 3
TOKEN = re.compile(r"`([^`]+)`")
WITH = re.compile(r"\s+with\s+(?:an?\s+)?")
DEPS = re.compile(r"\s+in dependencies\b")
ID = re.compile(r"`([a-z][a-z0-9-]*)`")


class IndexError_(Exception):
    pass


def table_rows(text, heading):
    """(line, cells) of the first table after the line starting with `heading`."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(heading)), None)
    if start is None:
        raise IndexError_(f"no section '{heading}'")
    rows, started = [], False
    for line in lines[start + 1:]:
        if line.startswith("|"):
            if started and not line.startswith("|---"):
                rows.append((line, [c.strip() for c in line.strip().strip("|").split("|")]))
            started = True
        elif started:
            break
    return rows


def parse_indicator(cell, line):
    """List of checks: ("dep", name) | ("path", glob, must_be_dir, texts or None)."""
    checks, pos = [], 0
    while True:
        m = TOKEN.search(cell, pos)
        if not m:
            break
        token, pos = m.group(1), m.end()
        rest = cell[pos:]
        if DEPS.match(rest) or (len(token) > 2 and token[0] == token[-1] == '"'):
            checks.append(("dep", token.strip('"')))
            continue
        w = WITH.match(rest)
        if w:
            texts, p = [], pos + w.end()
            while True:
                t = re.match(r"`([^`]+)`", cell[p:])
                if not t:
                    break
                texts.append(t.group(1))
                p += t.end()
                sep = re.match(r"\s*(?:or|/)\s*(?=`)", cell[p:])
                if not sep:
                    break
                p += sep.end()
            if not texts:
                raise IndexError_(f"'with' needs a backticked text: {line}")
            checks.append(("path", token, False, texts))
            pos = p
            continue
        checks.append(("path", token.rstrip("/"), token.endswith("/"), None))
    if not checks:
        raise IndexError_(f"indicator without a backticked token: {line}")
    return checks


def load_index(path):
    try:
        text = Path(path).read_text()
    except OSError as e:
        raise IndexError_(f"cannot read {path}: {e}")
    rows = []
    for line, cells in table_rows(text, "## 1. Detection"):
        if len(cells) != 3:
            raise IndexError_(f"{path}: row needs 3 cells (indicator, id, also): {line}")
        indicator, stack, also = cells
        m = re.fullmatch(r"`([a-z][a-z0-9-]*)`", stack)
        if not m:
            raise IndexError_(f"{path}: stack id must be one backticked lower-case id: {line}")
        try:
            checks = parse_indicator(indicator, line)
        except IndexError_ as e:
            raise IndexError_(f"{path}: {e}")
        rows.append({"id": m.group(1), "checks": checks, "no_web_above": "(no web stack above)" in indicator,
                     "groups": re.findall(r"counts as (\w+)", also),
                     "implies": re.findall(r"implies `([a-z][a-z0-9-]*)`", also)})
    if not rows:
        raise IndexError_(f"{path}: no rows in section 1")
    return rows


def workspace_dirs(root):
    globs = []
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            ws = json.loads(pkg.read_text()).get("workspaces", [])
        except (ValueError, AttributeError):
            ws = []
        globs += ws.get("packages", []) if isinstance(ws, dict) else ws
    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.is_file():
        inside = False
        for line in pnpm.read_text().splitlines():
            if re.match(r"packages\s*:", line):
                inside = True
            elif inside and re.match(r"\s*-\s*", line):
                globs.append(re.sub(r"^\s*-\s*", "", line).strip().strip("'\""))
            elif inside and line.strip() and not line.startswith((" ", "\t")):
                inside = False
    dirs = [root]
    for g in globs:
        if not isinstance(g, str) or g.startswith("!"):
            continue
        for d in sorted(root.glob(g.rstrip("/"))):
            if d.is_dir() and d not in dirs and not SKIP_DIRS & set(d.relative_to(root).parts):
                dirs.append(d)
    return dirs


def walk(base):
    """Relative paths (tuples of parts) under base up to MAX_DEPTH, skipping SKIP_DIRS."""
    out, stack = [], [(base, ())]
    while stack:
        d, rel = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            parts = rel + (e.name,)
            is_dir = e.is_dir()
            if is_dir and e.name in SKIP_DIRS:
                continue
            out.append((parts, is_dir, e))
            if is_dir and len(parts) < MAX_DEPTH:
                stack.append((e, parts))
    return out


def contains(path, texts):
    try:
        with open(path, "r", errors="replace") as fh:
            body = fh.read(65536)
    except OSError:
        return False
    return any(t in body for t in texts)


def path_matches(entries, glob, must_be_dir, texts):
    anywhere = glob.startswith("**/")
    parts = tuple(glob[3:].split("/")) if anywhere else tuple(glob.split("/"))
    for rel, is_dir, path in entries:
        if must_be_dir and not is_dir:
            continue
        if anywhere:
            ok = fnmatch.fnmatchcase(rel[-1], parts[-1])
        else:
            ok = any(len(rel) == len(parts) + off and
                     all(fnmatch.fnmatchcase(a, b) for a, b in zip(rel[off:], parts))
                     for off in (0, 1))
        if ok and (texts is None or (not is_dir and contains(path, texts))):
            return True
    return False


def dependencies(d):
    pkg = d / "package.json"
    if not pkg.is_file():
        return set()
    try:
        data = json.loads(pkg.read_text())
    except ValueError:
        return set()
    names = set()
    for key in ("dependencies", "devDependencies"):
        if isinstance(data.get(key), dict):
            names |= set(data[key])
    return names


def detect(root, rows):
    dirs = workspace_dirs(root)
    scans = [(walk(d), dependencies(d)) for d in dirs]
    found = []
    web = lambda: any("web" in r["groups"] for r in rows if r["id"] in found)
    for row in rows:
        if row["no_web_above"] and web():
            continue
        for entries, deps in scans:
            if any(c[1] in deps if c[0] == "dep" else path_matches(entries, *c[1:]) for c in row["checks"]):
                found.append(row["id"])
                break
    for row in rows:
        if row["id"] in found:
            found += [i for i in row["implies"] if i not in found]
    order = [r["id"] for r in rows]
    stacks = sorted(set(found), key=lambda i: order.index(i) if i in order else len(order))
    groups = []
    for row in rows:
        if row["id"] in stacks:
            groups += [g for g in row["groups"] if g not in groups]
    return stacks, groups


STACK_COND = re.compile(r"`([a-z0-9-]+)` (?:is )?in `\$TECH_STACKS`")
TYPE_COND = re.compile(r"`@type:` is `([\w-]+)`((?: or `[\w-]+`)*)")
STEP_TOKEN = re.compile(r"\b(4a|4c|5c)\b")
STEPS = {"4a": {"4a"}, "4c": {"4c"}, "gate": {"5c", "5g"}}


def blocks(text, skip_preamble=False):
    """Blocks of a markdown file: dicts with kind (para|item|row), lines and, for rows, the table head.
    skip_preamble drops everything before the first `## ` heading."""
    out, para, head = [], None, None
    lines = text.splitlines()
    if skip_preamble:
        lines = lines[next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines)):]
    for line in lines:
        if line.startswith("|"):
            para = None
            if head is None:
                head = [line]
            elif len(head) == 1:
                head.append(line)
            else:
                out.append({"kind": "row", "lines": [line], "head": tuple(head)})
            continue
        head = None
        if not line.strip() or line.startswith("#"):
            para = None
        elif line.startswith("- "):
            para = {"kind": "item", "lines": [line]}
            out.append(para)
        elif para is not None:
            para["lines"].append(line)
        else:
            para = {"kind": "para", "lines": [line]}
            out.append(para)
    return out


def types_of(text):
    found = []
    for first, more in TYPE_COND.findall(text):
        found += [first] + re.findall(r"`([\w-]+)`", more)
    return found


def lead_in_steps(block):
    first = block["lines"][0]
    if block["kind"] != "para" or not first.startswith("**"):
        return None
    span = " ".join(block["lines"])[2:].split("**", 1)[0]
    steps = set(STEP_TOKEN.findall(span))
    return {"gate" if s == "5c" else s for s in steps} or None


def emit(selected):
    """Lines of the selected blocks: a blank line between blocks, none inside a list or a table."""
    out, prev = [], None
    for b in selected:
        same = prev is not None and b["kind"] == prev["kind"] and b["kind"] in ("item", "row") \
            and b.get("head") == prev.get("head")
        if out and not same:
            out.append("")
        if b["kind"] == "row" and not same:
            out += list(b["head"])
        out += b["lines"]
        prev = b
    return out


def trigger_lines(path, stacks, step, type_):
    selected, section, lead, lead_types, pending = [], {"4a", "4c", "gate"}, None, [], []
    for b in blocks(Path(path).read_text(), skip_preamble=True):
        steps = lead_in_steps(b)
        if steps:
            section, lead, lead_types = steps, b, types_of(" ".join(b["lines"]))
            continue
        if step not in section:
            continue
        text = " ".join(b["lines"])
        types = types_of(text) or lead_types
        if not set(STACK_COND.findall(text)) <= set(stacks) or (types and type_ not in types):
            continue
        if lead is not None and lead not in selected:
            selected.append(lead)
        selected.append(b)
    return emit(selected)


def index_lines(path, stacks, step):
    text = Path(path).read_text()
    rows = []
    for line, cells in table_rows(text, "## 2. Trigger"):
        m = re.match(r"`([a-z0-9-]+)` ((?:4a|4c|5c|5g|debug)(?:/(?:4a|4c|5c|5g|debug))*):", cells[0])
        if not m:
            raise IndexError_(f"{path}: trigger must read '`<id>` <steps>: <condition>': {line}")
        if m.group(1) in stacks and STEPS[step] & set(m.group(2).split("/")):
            rows.append((m.group(1), line))
    if not rows:
        return []
    section = text.split("## 2. Trigger", 1)[1]
    head = [l for l in section.splitlines() if l.startswith("|")][:2]
    paras = {b["lines"][0].split("**")[1]: b["lines"] for b in blocks(section)
             if b["kind"] == "para" and b["lines"][0].startswith("**")}
    out = head + [l for _, l in rows]
    for name in ("How.", "Limits.") + (("WordPress rows.",) if any(i == "wordpress" for i, _ in rows) else ()):
        out += [""] + paras.get(name, [])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--index", default=str(DEV / "stack" / "INDEX.md"))
    ap.add_argument("--triggers", action="store_true", help="print the matching trigger lines")
    ap.add_argument("--step", choices=sorted(STEPS))
    ap.add_argument("--type", dest="type_", default=None, metavar="TYPE")
    args = ap.parse_args(argv)
    if args.triggers and not args.step:
        ap.error("--triggers needs --step")
    root = Path(args.root)
    if not root.is_dir():
        print(f"detect-stack: no directory {root}", file=sys.stderr)
        return 2
    try:
        rows = load_index(args.index)
    except IndexError_ as e:
        print(f"detect-stack: {e}", file=sys.stderr)
        return 2
    stacks, groups = detect(root.resolve(), rows)
    if args.triggers:
        try:
            lines = trigger_lines(DEV / "tech-stack-triggers.md", stacks, args.step, args.type_)
            rows2 = index_lines(args.index, stacks, args.step)
        except (OSError, IndexError_) as e:
            print(f"detect-stack: {e}", file=sys.stderr)
            return 2
        named = ", ".join(stacks) or "none"
        print(f"# tech-stack-triggers.md — step {args.step}, @type: {args.type_ or 'none'}, stacks: {named}")
        print("\n".join(lines))
        print()
        print(f"# stack/INDEX.md section 2 — step {args.step}" + ("" if rows2 else ": no matching rows"))
        if rows2:
            print("\n".join(rows2))
        return 0
    if args.json:
        print(json.dumps({"stacks": stacks, "groups": groups}))
    else:
        print("stacks: " + (", ".join(stacks) or "none"))
        print("groups: " + (", ".join(groups) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
