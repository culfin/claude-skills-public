#!/usr/bin/env python3
"""Decides the Quality Gate tier of a phase: `small` or `large`. Read-only.

    gate-tier.py --base <ref> [--type <phase type>] [--tasks <n>] [--gate full] [--root <dir>] [--slim]

Prints `small` or `large` on the first line, then one `- <reason>` per line. With `--slim`
(gate-slim.md) it then prints which specialists of the slim gate fire, one `+ <name>: <why>` line
each (`security`, `ui`, `codex`) with the checklist items it adds after `→`, or `+ none`. Exit 0 = decided,
2 = usage or git error (nothing on stdout, so a caller never reads a half answer as a tier).

Why a script: the tier decides which checks run, and a judgement call ("this looks small") is
exactly how a risky one-line auth change ends up with the light gate. The tier comes from the diff:
sensitive paths, ops files (CI, Docker, deploy, infra), dependency manifests and DB changes make a
phase large whatever its type. `--type` can only strengthen (a risk type makes it large); an unknown
or missing type changes nothing. `*.md` files (the phase's spec and plan, STATE.md, ROADMAP.md) do
not count towards the size and never trigger ops or dependency reasons, but still count towards
sensitive paths.
"""
import argparse
import re
import subprocess
import sys

MAX_TASKS = 3
MAX_LINES = 400
RISK_TYPES = {"auth", "security", "migration", "data"}
DB_CHANGE = re.compile(r"(^|/)migrations?/|(^|/)db/migrate/|(^|/)alembic/versions/|\.sql$"
                       r"|(^|/)schema\.(prisma|sql|rb)$", re.I)
SENSITIVE = re.compile(
    r"(^|/)(auth|login|logout|session|sessions|middleware|security|permissions?)(/|\.|$)"
    r"|(^|/)api/|(^|/)(routes?|actions?|controllers?)/"
    r"|(^|/)migrations?/|\.sql$", re.I)
# Test files count toward size, not sensitivity: floor-guard catches weakened tests.
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs|e2e)/|\.(test|spec)\.[cm]?[jt]sx?$"
                       r"|(^|/)test_[^/]*\.py$|_test\.(py|go|rs)$", re.I)
OPS = re.compile(
    r"(^|/)\.github/workflows/|(^|/)(?i:dockerfile)[^/]*$|(^|/)(docker-)?compose[^/]*\.ya?ml$"
    r"|(^|/)(deploy|infra(structure)?|ops|k8s|helm|terraform)(/|$)|\.tf$"
    r"|(^|/)[^/]*deploy[^/]*\.sh$|(^|/)nginx/|(^|/)Caddyfile$|(^|/)nginx[^/]*\.conf$|(^|/)\.gitlab-ci\.ya?ml$")
DEPS = re.compile(
    r"(^|/)(package\.json|pnpm-lock\.yaml|package-lock\.json|yarn\.lock|Cargo\.toml|Cargo\.lock"
    r"|go\.mod|go\.sum|requirements[^/]*\.txt|pyproject\.toml|poetry\.lock|Gemfile\.lock"
    r"|[^/]*\.gradle[^/]*|Podfile\.lock|pom\.xml|Pipfile\.lock|uv\.lock|composer\.(json|lock)"
    r"|bun\.lockb|pnpm-workspace\.yaml|Package\.resolved|[^/]*\.csproj)$")

# Slim gate (gate-slim.md): extra security paths (secrets, tokens, access policy, expensive endpoints) ...
SECRETS = re.compile(r"(^|/)\.env|secret|credential|password|token|oauth|jwt|crypt|(^|/)[^/]*(signup|register|reset"
                     r"|otp|upload|polic)[^/]*$|(^|/)(auth|login|session|middleware)[^/]*$|(^|/)route\.[cm]?[jt]sx?$", re.I)
STYLE = (".css", ".scss", ".less")
# Test names of the native stacks, beyond TEST_PATH (which also decides the tier).
SLIM_TESTS = re.compile(r"[^/]*Tests?\.(swift|kt|java)$|(^|/)[^/]*Tests/")
# ... and UI files: the Accessibility review row of tech-stack-triggers.md.
UI = re.compile(r"\.(tsx|jsx|svelte|vue|astro|html|css|scss|less|xaml)$|(^|/)[^/]*(View|Screen)\.(swift|kt)$"
                r"|(^|/)Views?/[^/]*\.swift$|(^|/)res/layout[^/]*/[^/]*\.xml$", re.I)
SLIM_CODEX_LINES = 300
WEB_UI = (".tsx", ".jsx", ".svelte", ".vue", ".astro", ".html", ".css", ".scss", ".less")


def slim_triggers(rows, typ):
    """`+ <specialist>: <why>` lines for the slim gate; tests never trigger a specialist."""
    kept = [(p, n) for p, n in rows if not TEST_PATH.search(p) and not SLIM_TESTS.search(p)]
    code = [p for p, _ in kept]
    lines = sum(n for p, n in kept if not p.lower().endswith(".md"))
    sec = sorted({p for p in code if SENSITIVE.search(p) or DB_CHANGE.search(p)
                  or (SECRETS.search(p) and not p.lower().endswith(STYLE))
                  or (not p.lower().endswith(".md") and (OPS.search(p) or DEPS.search(p)))})
    ui = sorted({p for p in code if UI.search(p)})
    web = any(p.lower().endswith(WEB_UI) for p in ui)
    out = []
    if sec or typ in RISK_TYPES:
        out.append("+ security: " + (listed(sec) if sec else f"risk type @type: {typ}") + " → Security review")
    if ui:
        out.append("+ ui: " + listed(ui) + " → UX review, Accessibility review" + (", Polish review" if web else ""))
    if lines > SLIM_CODEX_LINES or sec or typ in RISK_TYPES:
        out.append("+ codex: " + (f"{lines} changed lines (without *.md and tests) > {SLIM_CODEX_LINES}"
                                  if lines > SLIM_CODEX_LINES else "security-relevant") + " → Second opinion: codex diff")
    return out or ["+ none"]


def listed(paths):
    return ", ".join(paths[:5]) + (" …" if len(paths) > 5 else "")


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=True).stdout


def changed(root, base):
    """(path, changed lines) for tracked changes against base plus untracked files."""
    rows = []
    for line in git(root, "diff", "--numstat", "--no-renames", base, "--").splitlines():
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
    ap.add_argument("--slim", action="store_true", help="also print the slim gate's specialist triggers")
    a = ap.parse_args()
    try:
        git(a.root, "rev-parse", "--verify", f"{a.base}^{{commit}}")
        rows = changed(a.root, a.base)
    except subprocess.CalledProcessError as e:
        print(f"gate-tier: git failed: {e.stderr.strip() or e}", file=sys.stderr)
        return 2
    reasons = []
    lines = sum(n for p, n in rows if not p.lower().endswith(".md"))
    if a.gate == "full":
        reasons.append("@gate: full")
    if a.type in RISK_TYPES:
        reasons.append(f"risk type @type: {a.type}")
    db = sorted({p for p, _ in rows if DB_CHANGE.search(p)})
    if db:
        reasons.append("DB change: " + listed(db))
    hits = sorted({p for p, _ in rows if SENSITIVE.search(p) and not TEST_PATH.search(p)})
    if hits:
        reasons.append("sensitive files: " + listed(hits))
    code = [p for p, _ in rows if not p.lower().endswith(".md")]
    ops = sorted({p for p in code if OPS.search(p)})
    if ops:
        reasons.append("ops files: " + listed(ops))
    deps = sorted({p for p in code if DEPS.search(p)})
    if deps:
        reasons.append("dependency manifest: " + listed(deps))
    if a.tasks > MAX_TASKS:
        reasons.append(f"{a.tasks} tasks > {MAX_TASKS}")
    if lines > MAX_LINES:
        reasons.append(f"{lines} changed lines (without *.md) > {MAX_LINES}")
    if reasons:
        print("large")
        for r in reasons:
            print(f"- {r}")
    else:
        print("small")
        print(f"- {a.tasks} task(s), {lines} changed lines (without *.md), no risk type, no sensitive files")
    if a.slim:
        print("\n".join(slim_triggers(rows, a.type)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
