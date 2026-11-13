#!/usr/bin/env bash
# codex-review.sh — runs one gate review through Codex, in addition to the Claude review.
#
#   codex-review.sh --role <diff|security|fix|similar> --prompt <file> --input <file> --head <sha>
#                   --out <file> [--timeout-min 15]
#
# Run from inside the repository under review. --prompt is the review prompt (analyzer, mode,
# scope, requirement), --input the diff or other material Codex reads first (pass uncommitted and
# untracked changes in it: the checkout shows only --head).
# Exit 0 = usable review: --out holds the findings, `reviewer: codex` and the `Result:` line.
# Exit 3 = Codex result unusable; one line `fallback: <reason>` on stdout, --out not written. The
#          caller closes the gate item as `skipped: <reason>`, never as "no findings".
# Exit 2 = usage error (bad arguments, not a git repository, unknown --head).
#
# Why a script: every Codex call needs the same guards, and each one missing has bitten or would:
# - Codex runs in a fresh detached checkout of --head, never in the working directory, which may
#   hold a copied `.env` (Orca workspaces). One checkout per call, so parallel reviews never share.
# - `-s read-only` does not stop reads outside the checkout. A permission profile (read everything,
#   write nothing, deny `**/.env` and `**/.env.*` anywhere) does — and only without `--sandbox`,
#   which switches Codex back to the legacy sandbox and drops the deny rule. The user config is
#   ignored (`--ignore-user-config`) so a `sandbox_mode` there cannot do the same; a `.codex/` in
#   the reviewed repository is removed from the checkout for that reason. Proven on macOS
#   (Seatbelt); on Linux Codex enumerates deny globs only `glob_scan_max_depth` levels deep.
# - stdin is closed (`</dev/null`): `codex exec` otherwise waits for input appended to the prompt.
# - macOS has no `timeout`: Codex runs in its own process group under a watchdog; the trap kills
#   it and removes the checkout on every exit path, including an interrupted gate.
# - Exit 0 is not success: codex-result.py rejects answers that read nothing or report tool
#   failures ("tool attempts timed out"), see there.
# - After a quota error the marker $TMPDIR/dev-codex-<repo hash>.off makes every further call of
#   the next hour fall back at once instead of waiting for the timeout each time.
# DEV_CODEX_BIN selects the Codex binary (default `codex`); DEV_CODEX_TIMEOUT_SEC overrides
# --timeout-min (tests).
set -uo pipefail

usage() { echo "usage: codex-review.sh --role <diff|security|fix|similar> --prompt <file> --input <file> --head <sha> --out <file> [--timeout-min N]" >&2; exit 2; }
fallback() { echo "fallback: $1"; exit 3; }

role= prompt= input= head= out= timeout_min=15
while [[ $# -gt 0 ]]; do
    [[ $# -ge 2 ]] || usage
    case "$1" in
        --role) role=$2 ;; --prompt) prompt=$2 ;; --input) input=$2 ;; --head) head=$2 ;;
        --out) out=$2 ;; --timeout-min) timeout_min=$2 ;; *) usage ;;
    esac
    shift 2
done
case "$role" in diff|security|fix|similar) ;; *) usage ;; esac
[[ -f "$prompt" && -f "$input" && -n "$head" && -n "$out" ]] || usage
[[ "$timeout_min" =~ ^[1-9][0-9]*$ ]] || usage
limit=${DEV_CODEX_TIMEOUT_SEC:-$((timeout_min * 60))}
[[ "$limit" =~ ^[1-9][0-9]*$ ]] || usage

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
schema="$here/../schemas/review-findings.json"
top=$(git rev-parse --show-toplevel 2>/dev/null) || usage
commit=$(git -C "$top" rev-parse --verify --quiet "$head^{commit}") || usage
prompt=$(cd "$(dirname "$prompt")" && pwd)/$(basename "$prompt")
input=$(cd "$(dirname "$input")" && pwd)/$(basename "$input")
out=$(cd "$(dirname "$out")" 2>/dev/null && pwd)/$(basename "$out") || usage
rm -f "$out"

base="${TMPDIR:-/tmp}"; base="${base%/}"
marker="$base/dev-codex-$(printf %s "$top" | git hash-object --stdin | cut -c1-12).off"
if [[ -e "$marker" ]]; then
    [[ -n "$(find "$marker" -mmin -60 2>/dev/null)" ]] && fallback "quota"
    rm -f "$marker"
fi

bin="${DEV_CODEX_BIN:-codex}"
command -v "$bin" >/dev/null 2>&1 || fallback "codex not found ($bin)"

work= wt= pid=
cleanup() {
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill -TERM -- "-$pid" 2>/dev/null; sleep 1; kill -KILL -- "-$pid" 2>/dev/null
    fi
    [[ -n "$wt" ]] && git -C "$top" worktree remove --force "$wt" >/dev/null 2>&1
    [[ -n "$work" ]] && rm -rf "$work"
    git -C "$top" worktree prune >/dev/null 2>&1
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

work=$(mktemp -d "$base/dev-codex-XXXXXX") || fallback "no temporary directory"
git -C "$top" worktree add --quiet --detach "$work/checkout" "$commit" >/dev/null 2>&1 \
    || fallback "checkout of $head failed"
wt="$work/checkout"
# Nothing secret and no Codex project config in the checkout, even when committed.
find "$wt" -name .git -prune -o \( -name '.env' -o -name '.env.*' \) -type f -print0 | xargs -0 rm -f
rm -rf "$wt/.codex"
cp "$input" "$work/input-$(basename "$input")"
python3 "$here/codex-result.py" model-schema --schema "$schema" >"$work/schema.json" \
    || fallback "schema unreadable"

text="$(cat "$prompt")

Input file (read it first): $work/input-$(basename "$input")
You are in a clean checkout of commit $commit (the repository root is the current directory).
Your final answer is JSON matching the given schema. files_read = the number of files you actually
opened and read (0 if none); blocked_reason = empty if you reviewed, otherwise why you could not.
Every finding needs file, line, the quoted line(s) and the concrete failing input. No findings is
a valid answer."

set -m      # own process group, so the watchdog and the trap reach every Codex child
( cd "$wt" && exec "$bin" exec --ephemeral --ignore-user-config --skip-git-repo-check --color never \
    -c 'default_permissions="dev-review"' \
    -c 'permissions.dev-review.filesystem={":root"="read", glob_scan_max_depth=3, "/"={"**/.env"="deny", "**/.env.*"="deny"}}' \
    --output-schema "$work/schema.json" -o "$work/answer.json" "$text" \
    </dev/null >"$work/codex.log" 2>&1 ) &
pid=$!
set +m

timed_out=
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
[[ -n "$timed_out" ]] && fallback "timeout after $limit s"
if (( rc != 0 )); then
    if tail -n 40 "$work/codex.log" | grep -qiE 'usage limit|rate limit|quota|too many requests|\b429\b'; then
        touch "$marker"
        fallback "quota"
    fi
    fallback "codex exit $rc"
fi

python3 "$here/codex-result.py" check --schema "$schema" --result "$work/answer.json" --role "$role" \
    --out "$out"
rc=$?
(( rc == 0 || rc == 3 )) || fallback "result check failed ($rc)"
exit "$rc"
