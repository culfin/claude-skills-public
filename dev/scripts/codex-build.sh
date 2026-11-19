#!/usr/bin/env bash
# codex-build.sh — lets Codex build one phase in the phase worktree (lean flow, builder codex).
#
#   codex-build.sh --brief <file> --head <sha> --out <file> [--timeout-min 60] [--keep-partial]
#
# Run from inside the phase worktree, clean and at --head. --brief is the phase brief (spec,
# acceptance criteria, files); --out a file outside the worktree.
# Exit 0 = Codex finished: its changes are left uncommitted in the worktree, --out holds
#          `builder: codex`, the `files:` list and Codex's summary. The caller reviews and commits.
# Exit 3 = unusable (quota, timeout, crash, no changes, Codex committed or moved refs, changed a
#          .env file or wrote a path that leads outside the repository); one line
#          `fallback: <reason>` on stdout. --out says what Codex had left and what happened to it.
#          Without --keep-partial the worktree is reset to --head (git reset --hard + git clean;
#          ignored files stay); with it the changes stay, uncommitted, on --head. A Codex commit
#          is undone either way.
# Exit 2 = usage error: bad arguments, not a git worktree, worktree dirty or not at --head,
#          --out inside the worktree, or ROADMAP.md frontmatter without `defaults.builder: codex`.
#
# Guards:
# - Only where the project opted in: `defaults.builder: codex` in the worktree's ROADMAP.md
#   frontmatter. Codex write rights exist only in a pilot project; elsewhere Codex only reviews.
# - Codex runs with `--sandbox workspace-write -C <worktree>`: it writes the worktree and a private
#   scratch dir (its TMPDIR), not /tmp or $TMPDIR (excluded), no network from its commands, no
#   approval prompts (`never`: nothing escalates out of the sandbox), no user config or execpolicy
#   rules that could widen it. So it cannot push. A linked worktree's git dir lies outside the
#   writable root, so it cannot commit either; refs are compared before and after anyway.
# - `.env*` files are reachable only as the symlinks the worktree already has. The script never
#   copies, reads or prints them; it compares their kind, link target, size and mtime before and after.
# - Quota: the marker $TMPDIR/dev-codex-<repo hash>.off (shared with codex-review.sh) makes every
#   further call of the next hour fall back at once.
# - macOS has no `timeout`: Codex runs in its own process group under a watchdog; the trap kills it
#   and removes the temp dir on every catchable exit path.
# DEV_CODEX_BIN selects the Codex binary (default `codex`); DEV_CODEX_TIMEOUT_SEC overrides
# --timeout-min (tests). DEV_CODEX_EFFORT (minimal|low|medium|high|xhigh) sets the reasoning effort.
set -uo pipefail

usage() { echo "usage: codex-build.sh --brief <file> --head <sha> --out <file> [--timeout-min N] [--keep-partial]${1:+ ($1)}" >&2; exit 2; }

brief= head= out= timeout_min=60 keep=
while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep-partial) keep=1; shift; continue ;;
        --brief|--head|--out|--timeout-min) [[ $# -ge 2 ]] || usage ;;
        *) usage ;;
    esac
    case "$1" in
        --brief) brief=$2 ;; --head) head=$2 ;; --out) out=$2 ;; --timeout-min) timeout_min=$2 ;;
    esac
    shift 2
done
[[ -f "$brief" && -n "$head" && -n "$out" ]] || usage
[[ -d "$(dirname "$out")" ]] || usage "no directory for --out"
[[ "$timeout_min" =~ ^[1-9][0-9]*$ ]] || usage
limit=${DEV_CODEX_TIMEOUT_SEC:-$((timeout_min * 60))}
[[ "$limit" =~ ^[1-9][0-9]*$ ]] || usage
effort=()
if [[ -n "${DEV_CODEX_EFFORT:-}" ]]; then
    [[ "$DEV_CODEX_EFFORT" =~ ^(minimal|low|medium|high|xhigh)$ ]] || usage
    effort=(-c "model_reasoning_effort=\"$DEV_CODEX_EFFORT\"")
fi

top=$(git rev-parse --show-toplevel 2>/dev/null) || usage "not a git worktree"
top=$(cd "$top" && pwd -P)
commit=$(git -C "$top" rev-parse --verify --quiet "$head^{commit}") || usage "unknown --head"
[[ "$(git -C "$top" rev-parse HEAD)" == "$commit" ]] || usage "worktree is not at --head"
[[ -z "$(git -C "$top" status --porcelain -uall)" ]] || usage "worktree has uncommitted changes"
brief=$(cd "$(dirname "$brief")" && pwd -P)/$(basename "$brief")
out=$(cd "$(dirname "$out")" && pwd -P)/$(basename "$out")
[[ "$out" == "$top"/* ]] && usage "--out inside the worktree"
python3 - "$top/ROADMAP.md" <<'PY' || usage "ROADMAP.md frontmatter lacks defaults.builder: codex"
import re, sys
try:
    text = open(sys.argv[1], encoding="utf-8").read()
except OSError:
    sys.exit(1)
m = re.match(r"---\n(.*?)\n---\s*\n", text, re.S)
block, inside = m.group(1) if m else "", False
for line in block.splitlines():
    if re.match(r"\S", line):
        inside = line.split("#")[0].strip() == "defaults:"
    elif inside and re.fullmatch(r"\s+builder:\s*codex\s*(#.*)?", line):
        sys.exit(0)
sys.exit(1)
PY
rm -f "$out"

base="${TMPDIR:-/tmp}"; base=$(cd "$base" && pwd -P) || { echo "fallback: no temporary directory"; exit 3; }
find "$base" -maxdepth 1 -type d -name 'dev-codex-build-*' -mtime +0 -exec rm -rf {} + 2>/dev/null
marker="$base/dev-codex-$(printf %s "$top" | git hash-object --stdin | cut -c1-12).off"

# Snapshots: refs (commits, branch switches, pushes' tracking refs) and .env* metadata, never content.
refs() {
    git -C "$top" rev-parse HEAD; git -C "$top" symbolic-ref -q HEAD
    git -C "$top" for-each-ref --format='%(refname) %(objectname)'
}
envs() {
    python3 - "$top" <<'PY'
import os, sys
top = sys.argv[1]
for d, dirs, files in os.walk(top):
    dirs[:] = sorted(x for x in dirs if x not in (".git", "node_modules"))
    for f in sorted(files + [x for x in dirs if os.path.islink(os.path.join(d, x))]):
        if f == ".env" or f.startswith(".env."):
            p = os.path.join(d, f); st = os.lstat(p)
            print(os.path.relpath(p, top), os.readlink(p) if os.path.islink(p) else f"{st.st_size} {st.st_mtime_ns}")
PY
}
list() { local f; while IFS= read -r f; do [[ -n "$f" ]] && printf -- '- %s\n' "$f"; done <<<"$1"; }
changed() {         # paths that differ from --head: tracked changes, commits, untracked files
    { git -C "$top" diff --name-only "$commit"; git -C "$top" ls-files --others --exclude-standard; } | sort -u
}
orig_sym=$(git -C "$top" symbolic-ref -q HEAD)
refs_before=$(refs) envs_before=$(envs)

work= pid= rc= timed_out= answer=
cleanup() {
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill -TERM -- "-$pid" 2>/dev/null; sleep 1; kill -KILL -- "-$pid" 2>/dev/null
    fi
    [[ -n "$work" ]] && rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# fallback <reason>: report what Codex left, undo a commit, reset unless --keep-partial, exit 3.
fallback() {
    local files partial=none
    files=$(changed 2>/dev/null)
    if [[ "$(git -C "$top" rev-parse HEAD)" != "$commit" || "$(git -C "$top" symbolic-ref -q HEAD)" != "$orig_sym" ]]; then
        if [[ -n "$orig_sym" ]]; then git -C "$top" symbolic-ref HEAD "$orig_sym"
        else git -C "$top" update-ref --no-deref HEAD "$commit"; fi
        git -C "$top" reset -q "$commit"                     # commit undone, changes stay
    fi
    if [[ -n "$files" ]]; then
        if [[ -n "$keep" ]]; then
            partial="kept, uncommitted on $commit"
        else
            git -C "$top" reset -q --hard "$commit" && git -C "$top" clean -fdq
            partial="reset to $commit"
        fi
    fi
    {
        echo "fallback: $1"
        echo "head: $commit"
        echo "partial: $partial"
        [[ "$1" == "codex changed a .env file" ]] && echo "note: .env files are ignored by git and were not restored; check them by hand"
        echo "files:"; list "$files"
        echo "summary:"; [[ -n "$answer" && -s "$answer" ]] && cat "$answer"
    } >"$out"
    echo "fallback: $1"
    exit 3
}

if [[ -e "$marker" ]]; then
    [[ -n "$(find "$marker" -mmin -60 2>/dev/null)" ]] && fallback "quota"
    rm -f "$marker"
fi
bin="${DEV_CODEX_BIN:-codex}"
command -v "$bin" >/dev/null 2>&1 || fallback "codex not found ($bin)"
realbin=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$(command -v "$bin")")
[[ "$realbin" == "$top"/* ]] && fallback "unsafe-codex-location"     # Codex could rewrite itself

work=$(mktemp -d "$base/dev-codex-build-XXXXXX") || fallback "no temporary directory"
work=$(cd "$work" && pwd -P)
scratch="$work/scratch"; mkdir -p "$scratch"
answer="$work/answer.md"

text="$(cat "$brief")

---
You build this phase in a git worktree: the current directory, at commit $commit.
- Write the code and a test per acceptance criterion, named after it; run the unit tests.
- Leave every change uncommitted: never run \`git commit\`, \`git push\`, \`git reset\`, \`git stash\`,
  \`git checkout\` or \`git switch\`, and create no branches or tags.
- Never read, print, copy or edit \`.env\` files. Stay inside this directory; scratch files go to \$TMPDIR.
- No network: do not install packages; if one is missing, say so under open:.
Your final message: a short summary, then \`files:\` with one changed path per line, then \`open:\`
with anything left undone or failing (or \`none\`)."

set -m      # own process group, so the watchdog and the trap reach every Codex child
( cd "$top" && exec "$bin" exec --ephemeral --ignore-user-config --ignore-rules --color never \
    --sandbox workspace-write -C "$top" --add-dir "$scratch" \
    -c 'approval_policy="never"' \
    -c 'sandbox_workspace_write.network_access=false' \
    -c 'sandbox_workspace_write.exclude_slash_tmp=true' \
    -c 'sandbox_workspace_write.exclude_tmpdir_env_var=true' \
    -c "shell_environment_policy.set={TMPDIR=\"$scratch\", GIT_TERMINAL_PROMPT=\"0\"}" \
    ${effort[@]+"${effort[@]}"} -o "$answer" "$text" </dev/null >"$work/codex.log" 2>&1 ) &
pid=$!
set +m
SECONDS=0
while kill -0 "$pid" 2>/dev/null; do
    if (( SECONDS >= limit )); then
        timed_out=1
        kill -TERM -- "-$pid" 2>/dev/null; sleep 1; kill -KILL -- "-$pid" 2>/dev/null
        break
    fi
    sleep 0.5
done
wait "$pid"; rc=$?
pid=
tokens=$(awk 'f { print; exit } /^tokens used$/ { f = 1 }' "$work/codex.log" 2>/dev/null)
[[ -n "$tokens" ]] && echo "tokens used: $tokens" >&2

# Integrity first: these hold even when Codex also ran out of time or quota.
quota=
tail -n 40 "$work/codex.log" | grep -qiE '^error[: ].*(usage limit|rate limit|quota|too many requests|\b429\b)' \
    && { quota=1; touch "$marker"; }
if [[ "$(refs)" != "$refs_before" ]]; then
    [[ "$(git -C "$top" rev-parse HEAD)" != "$commit" ]] && fallback "codex committed"
    fallback "codex changed git refs"
fi
[[ "$(envs)" != "$envs_before" ]] && fallback "codex changed a .env file"
while IFS= read -r f; do
    [[ -z "$f" || ! -L "$top/$f" ]] && continue
    real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$top/$f")
    [[ "$real" == "$top" || "$real" == "$top"/* ]] || fallback "codex touched a path outside the repository"
done <<<"$(changed)"
[[ -n "$timed_out" ]] && fallback "timeout after $limit s"
[[ -n "$quota" ]] && fallback "quota"
(( rc == 0 )) || fallback "codex exit $rc"
files=$(changed)
[[ -n "$files" ]] || fallback "codex made no changes"

{
    echo "builder: codex"
    echo "head: $commit"
    echo "files:"; list "$files"
    echo "summary:"; [[ -s "$answer" ]] && cat "$answer"
} >"$out"
exit 0
