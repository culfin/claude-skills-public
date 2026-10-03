#!/usr/bin/env python3
"""Finds ways a phase lowers the quality floor to get green. Read-only.

    floor-guard.py --base <ref> [--root <dir>]

One finding per line on stdout: `<path>:<line>: <severity>: <kind>: <text>`. Exit 0 = no critical
finding (notes may be printed), 1 = at least one critical, 2 = usage or git error (nothing on
stdout, so a caller never reads a failure as "clean").
critical: skipped-test (generic skips only in test paths), removed-assertion (test paths),
lowered-threshold, ci-bypass, allow-without-reason. note: type-suppression, lint-suppression.
Markdown files and this tool's own script and test are not scanned. `.floor-guard-allow` in the
root (`<path-glob> <kind> # reason`) suppresses one kind for matching paths; a line without a
reason suppresses nothing.

Why a script: under gate pressure the cheapest way to green is to lower the bar; reviewers read
for defects, not for this — a mechanical check catches it every time.
"""
import argparse
import fnmatch
import re
import subprocess
import sys

ALLOW_FILE = ".floor-guard-allow"
SKIP_GENERIC = re.compile(r"\.skip\(|\bxit\(|\bxdescribe\(")
SKIP_MARKER = re.compile(r"@pytest\.mark\.skip|@unittest\.skip|#\[ignore\]|\bt\.Skip\(")
TYPE_SUPPRESS = re.compile(r"@ts-ignore|@ts-nocheck|#\s*type:\s*ignore")
TS_EXPECT = re.compile(r"@ts-expect-error(.*)$")
LINT_SUPPRESS = re.compile(r"eslint-disable|#\s*noqa|#\[allow\(|//\s*nolint|@SuppressWarnings")
CI_BYPASS = re.compile(r"continue-on-error:\s*true|\|\|\s*true")
NO_VERIFY = re.compile(r"--no-verify")
ASSERTION = re.compile(r"assert|expect\(|should")
THRESHOLD = re.compile(r"threshold|fail_under|coverage|minimum|--max-warnings", re.I)
NUMBER = re.compile(r"\d+(?:\.\d+)*")
TEST_DIRS = {"test", "tests", "__tests__", "spec"}
TEST_FILE = re.compile(r"^test_.+|.+_(test|spec)\.[^.]+$|.+\.(test|spec)\.[^.]+$")
OWN_FILES = {"floor-guard.py", "test_floor_guard.py", ALLOW_FILE}
CRITICAL = {"skipped-test", "removed-assertion", "lowered-threshold", "ci-bypass", "allow-without-reason"}
WORKFLOW = re.compile(r"^\.github/workflows/")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class GitError(Exception):
    pass


def git(root, *args):
    r = subprocess.run(["git", "-C", root, "-c", "core.quotepath=off", *args], capture_output=True, text=True)
    if r.returncode:
        raise GitError(r.stderr.strip())
    return r.stdout


def parse_diff(text):
    """{path: [hunk]}, hunk = (removed [(old_lineno, text)], added [(new_lineno, text)])."""
    files, path, hunk, old, new = {}, None, None, 0, 0
    for line in text.splitlines():
        m = re.match(r"^diff --git a/.+ b/(.+)$", line)
        if m:
            path, hunk = m.group(1), None
            files.setdefault(path, [])
            continue
        m = HUNK.match(line)
        if m and path:
            old, new = int(m.group(1)), int(m.group(3))
            hunk = ([], [])
            files[path].append(hunk)
        elif hunk is not None and line.startswith("+"):
            hunk[1].append((new, line[1:]))
            new += 1
        elif hunk is not None and line.startswith("-"):
            hunk[0].append((old, line[1:]))
            old += 1
    return files


def untracked(root):
    files = {}
    for path in git(root, "ls-files", "--others", "--exclude-standard").splitlines():
        try:
            with open(f"{root}/{path}", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        files[path] = [([], list(enumerate(lines, 1)))]
    return files


def is_test_path(path):
    parts = path.split("/")
    return bool(TEST_DIRS & set(parts[:-1])) or bool(TEST_FILE.match(parts[-1]))


def numbers(s):
    """Dotted versions as integer tuples, so 1.10 is higher than 1.9."""
    return [tuple(int(x) for x in n.split(".")) for n in NUMBER.findall(s)]


def key(s):
    return NUMBER.sub("#", s).strip()


def lowered(old, new):
    """A number went down — or up for --max-warnings, where a higher count is the lower bar."""
    a, b = numbers(old), numbers(new)
    if len(a) != len(b):
        return False
    up = "--max-warnings" in old or "--max-warnings" in new
    return any((y > x) if up else (y < x) for x, y in zip(a, b))


def scan(path, hunks):
    out = []
    in_tests = is_test_path(path)
    for removed, added in hunks:
        for n, t in added:
            if SKIP_MARKER.search(t) or (in_tests and SKIP_GENERIC.search(t)):
                out.append((n, "skipped-test", t))
            if TYPE_SUPPRESS.search(t):
                out.append((n, "type-suppression", t))
            m = TS_EXPECT.search(t)
            if m and not re.sub(r"[\s*/]+", "", m.group(1)):
                out.append((n, "type-suppression", t))
            if LINT_SUPPRESS.search(t):
                out.append((n, "lint-suppression", t))
            if (WORKFLOW.match(path) and CI_BYPASS.search(t)) or NO_VERIFY.search(t):
                out.append((n, "ci-bypass", t))
    gone = [t for h in hunks for _, t in h[0]]
    for n, new in [a for h in hunks for a in h[1]]:
        for i, old in enumerate(gone):
            if key(old) == key(new) and old != new:
                del gone[i]
                if (THRESHOLD.search(old) or THRESHOLD.search(new)) and lowered(old, new):
                    out.append((n, "lowered-threshold", new))
                break
    if in_tests:
        gone = [(n, t) for h in hunks for n, t in h[0] if ASSERTION.search(t)]
        came = [1 for h in hunks for _, t in h[1] if ASSERTION.search(t)]
        if len(gone) > len(came):
            out.append((gone[0][0], "removed-assertion", gone[0][1]))
    return out


def load_allow(root):
    rules, findings = [], []
    try:
        with open(f"{root}/{ALLOW_FILE}", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return rules, findings
    for i, raw in enumerate(lines, 1):
        body, _, reason = raw.partition("#")
        parts = body.split()
        if raw.lstrip().startswith("#") or not parts:
            continue
        if len(parts) != 2 or not reason.strip():
            findings.append((ALLOW_FILE, i, "allow-without-reason", raw.strip()))
        else:
            rules.append((parts[0], parts[1]))
    return rules, findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--root", default=".")
    try:
        args = ap.parse_args()
    except SystemExit:
        sys.exit(2)
    try:
        try:
            git(args.root, "rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
        except GitError:
            raise GitError(f"unknown base ref {args.base}")
        files = parse_diff(git(args.root, "diff", "-U0", "--no-color", "-M", args.base, "--"))
        files.update(untracked(args.root))
    except (GitError, OSError) as e:
        print(f"floor-guard: {e or 'git failed'}", file=sys.stderr)
        sys.exit(2)
    rules, findings = load_allow(args.root)
    for path in sorted(files):
        if path.endswith(".md") or path.rsplit("/", 1)[-1] in OWN_FILES:
            continue
        for n, kind, text in sorted(scan(path, files[path])):
            if not any(fnmatch.fnmatch(path, g) and kind == k for g, k in rules):
                findings.append((path, n, kind, text.strip()[:100]))
    for path, n, kind, text in findings:
        print(f"{path}:{n}: {'critical' if kind in CRITICAL else 'note'}: {kind}: {text}")
    sys.exit(1 if any(f[2] in CRITICAL for f in findings) else 0)


if __name__ == "__main__":
    main()
