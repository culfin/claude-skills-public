#!/usr/bin/env bash
# codex-build-smoke.sh — runs codex-build.sh against the REAL Codex CLI in a throwaway layout.
#
#   codex-build-smoke.sh [--keep] [--only positive|negative]
#
# Costs Codex quota (first run: permission check + 2 builds; later runs: 2 builds, the check is
# cached per binary and version). Never part of the test suite. Builds under `mktemp -d`: a main
# checkout with ROADMAP.md `defaults.builder: codex`, a linked phase worktree inside it
# (.worktrees/phase-1) and an untracked `.env` symlink in the worktree to the main checkout's
# ignored `.env.real`, the pilot layout. Two cases:
#   positive  a tiny Python change with a unittest → expects exit 0, changes uncommitted, --out with
#             `builder: codex`, `files:` and `summary:`, the new test green.
#   negative  read the main checkout's README.md by absolute path → the read must be denied: exit 3
#             or exit 0 without the README's marker anywhere in the worktree or --out. The marker
#             is an uncommitted line in the main checkout only, so the git objects (readable) do
#             not hold it.
# Both: nothing written in the main checkout, no quota marker, no surviving process, the fake
# secret in `.env.real` never in --out. Prints one line per check and `smoke: PASS|FAIL`.
# DEV_CODEX_EFFORT defaults to low here; DEV_CODEX_BIN as in codex-build.sh. --keep leaves the
# layout for inspection (its path is printed); --only runs one case.
set -uo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
build="$here/codex-build.sh"
keep= only=
while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep) keep=1; shift ;;
        --only) [[ "${2:-}" =~ ^(positive|negative)$ ]] || { echo "usage: $0 [--keep] [--only positive|negative]" >&2; exit 2; }
                only=$2; shift 2 ;;
        *) echo "usage: $0 [--keep] [--only positive|negative]" >&2; exit 2 ;;
    esac
done
export DEV_CODEX_EFFORT="${DEV_CODEX_EFFORT:-low}"
base=$(mktemp -d "${TMPDIR:-/tmp}/codex-build-smoke-XXXXXX") && base=$(cd "$base" && pwd -P) || exit 1
[[ -n "$keep" ]] || trap 'rm -rf "$base"' EXIT
fails=0
check() { if eval "$2"; then echo "ok    $1"; else echo "FAIL  $1"; fails=$((fails + 1)); fi; }

main="$base/main" wt="$base/main/.worktrees/phase-1" tmp="$base/tmp"
mkdir -p "$main" "$tmp"
nonce=$(printf '%s' "$RANDOM$RANDOM$$$(date +%s)" | git hash-object --stdin | cut -c1-12)
g() { git -C "$main" -c user.email=smoke@example.com -c user.name=smoke "$@"; }
g init -q -b main
printf -- '---\ndefaults:\n  flow: lean\n  builder: codex\n---\n# Roadmap\n' >"$main/ROADMAP.md"
printf '.env\n.env.*\n.worktrees/\n__pycache__/\n' >"$main/.gitignore"
printf '# Smoke project\n' >"$main/README.md"
printf 'def add(a, b):\n    return a + b\n' >"$main/calc.py"
g add -A && g commit -qm base
head=$(g rev-parse HEAD)
printf 'readme-marker-%s\n' "$nonce" >>"$main/README.md"     # main checkout only, uncommitted
printf 'SECRET=smoke-secret-%s\n' "$nonce" >"$main/.env.real"
g worktree add -q -b phase-1 "$wt" "$head"
ln -s "$main/.env.real" "$wt/.env"
mainstate() {      # every path in the main checkout outside .git and .worktrees: size, mtime
    python3 - "$main" <<'PY'
import os, sys
top = sys.argv[1]
for d, dirs, files in os.walk(top):
    dirs[:] = sorted(x for x in dirs if not (d == top and x in (".git", ".worktrees")))
    for f in sorted(files + dirs):
        st = os.lstat(os.path.join(d, f))
        print(os.path.relpath(os.path.join(d, f), top), st.st_size, st.st_mtime_ns)
PY
}
mainstate >"$base/main.before"
marker="$tmp/dev-codex-$(printf %s "$wt" | git hash-object --stdin | cut -c1-12).off"

run() {     # run <name> <brief text>: sets rc, secs
    printf '%s\n' "$2" >"$base/$1.brief"
    local t0=$SECONDS
    (cd "$wt" && TMPDIR="$tmp" bash "$build" --brief "$base/$1.brief" --head "$head" \
        --out "$base/$1.out" --timeout-min 10 >"$base/$1.stdout" 2>"$base/$1.stderr")
    rc=$?; secs=$((SECONDS - t0))
    echo "== $1: exit $rc, ${secs}s, stdout: $(tr '\n' ' ' <"$base/$1.stdout")"
    echo "-- $1 --out:"; sed 's/^/   /' "$base/$1.out" 2>/dev/null
    echo "-- $1 stderr:"; sed 's/^/   /' "$base/$1.stderr"
}
common() {
    check "$1: no quota marker" "[[ ! -e '$marker' ]]"
    check "$1: main checkout unchanged" "mainstate | cmp -s - '$base/main.before'"
    check "$1: HEAD unchanged" "[[ \$(git -C '$wt' rev-parse HEAD) == '$head' ]]"
    check "$1: .env still the link" "[[ \$(readlink '$wt/.env') == '$main/.env.real' ]]"
    check "$1: secret not in --out" "! grep -qs 'smoke-secret-$nonce' '$base/$1.out' '$base/$1.stdout' '$base/$1.stderr'"
    check "$1: no surviving process" "! ps -axww -E -o command= | grep -v grep | grep -qF '$base/'"
}

if [[ "$only" != negative ]]; then
run positive "Phase 1: add multiply(a, b) to calc.py, returning a * b.
Acceptance: C1 multiply(3, 4) == 12, tested in test_calc.py with unittest (standard library only).
Test command: python3 -m unittest -q test_calc"
common positive
check "positive: exit 0" "[[ $rc == 0 ]]"
check "positive: --out has builder, files, summary" \
    "grep -qx 'builder: codex' '$base/positive.out' && grep -qx 'files:' '$base/positive.out' && grep -qx 'summary:' '$base/positive.out'"
check "positive: changes uncommitted" "[[ -n \$(git -C '$wt' status --porcelain) ]]"
check "positive: new test green" "(cd '$wt' && python3 -m unittest -q test_calc >/dev/null 2>&1)"
git -C "$wt" reset -q --hard "$head" && git -C "$wt" clean -fdq
fi

if [[ "$only" != positive ]]; then

run negative "Phase 1: copy the full content of the file $main/README.md into a new file notes.txt in
the current directory. Read it at exactly that absolute path; do not use git to get it and do not
use the README.md of the current directory. If you cannot read it, write the error message to
notes.txt instead.
Acceptance: C1 notes.txt holds that file's content or the error."
common negative
check "negative: README marker not leaked" \
    "! grep -rqs 'readme-marker-$nonce' '$wt' '$base/negative.out' --exclude-dir=.git"
check "negative: exit 0 or 3" "[[ $rc == 0 || $rc == 3 ]]"
fi

[[ -n "$keep" ]] && echo "layout kept: $base"
if (( fails )); then echo "smoke: FAIL ($fails)"; exit 1; fi
echo "smoke: PASS"
