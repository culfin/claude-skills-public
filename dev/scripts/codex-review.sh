#!/usr/bin/env bash
# codex-review.sh — runs one gate review through Codex, in addition to the Claude review.
#
#   codex-review.sh --role <diff|security|fix|similar> --prompt <file> --input <file>... --head <sha>
#                   --out <file> [--timeout-min 15]
#
# Run from inside the repository under review. --prompt is the review prompt (analyzer, mode,
# scope, requirement), --input the diff or other material Codex reads first (pass uncommitted and
# untracked changes in it: the checkout shows only --head, and the working directory is unreadable).
# --input may repeat (diff plus an untracked spec); every file reaches Codex, none replaces another.
# Exit 0 = usable review: --out holds the findings, `reviewer: codex` and the `Result:` line.
# Exit 3 = Codex result unusable; one line `fallback: <reason>` on stdout, --out not written. The
#          caller closes the gate item as `skipped: <reason>`, never as "no findings".
# Exit 2 = usage error (bad arguments, not a git repository, unknown --head, missing --out
#          directory, an --input named .env or .env.*).
#
# Why a script: every Codex call needs the same guards, and each one missing has bitten or would:
# - Codex runs in a fresh clone of --head under $TMPDIR, never in the working directory, which may
#   hold a copied `.env` (Orca workspaces). A clone, not a worktree: a worktree reads its objects
#   from the working repository, which the profile below must deny. One clone per call.
# - Text under review can carry a prompt injection ("print ~/.ssh/id_ed25519"), and whatever Codex
#   reads goes to OpenAI and into the gate report. `-s read-only` stops writes, not reads. So Codex
#   runs under a permission profile: read only the platform paths tools need (`:minimal`, the
#   Codex binary's dirs, bin/Cellar/Caskroom/lib/libexec/opt/share of Homebrew prefixes) and its
#   own temp dir, which also gets copies of the analyzer files the prompt names; deny /tmp
#   (`:minimal` lets it through), the working repository, credential folders in $HOME (home and
#   $TMPDIR are not readable anyway; no deny on $TMPDIR, or the model refuses to touch its own temp
#   dir in it) and `**/.env`, `**/.env.*` anywhere; write nothing. A Codex binary in $HOME, above
#   it or in the repository is refused (`unsafe-codex-location`): its dir would become readable.
#   Never together with `--sandbox`: that switches Codex back to the legacy sandbox and
#   silently drops the profile. `--ignore-user-config` and removing `.codex/` from the clone keep a
#   `sandbox_mode` in user or project config from doing the same. git gets GIT_CONFIG_GLOBAL=/dev/null
#   (it aborts on an unreadable ~/.gitconfig). Codex system config (/etc/codex, managed
#   requirements) still applies; the deny check below catches one that breaks the profile.
# - The profile is only as good as the Codex build that reads it (unknown keys are ignored
#   silently). Before the first review with a binary and version, a deny check asks Codex to `cat`
#   a readable control file, a `.env` and a file in a denied folder; any leaked value = exit 3
#   `deny-rule-not-enforced`. A passed check is cached in $TMPDIR/dev-codex-ok-<hash>.
# - stdin is closed (`</dev/null`): `codex exec` otherwise waits for input appended to the prompt.
# - macOS has no `timeout`: Codex runs in its own process group under a watchdog; the trap kills
#   it and removes the temp dir on every catchable exit path. Temp dirs left by SIGKILL or a
#   reboot are swept after a day.
# - Exit 0 is not success: codex-result.py rejects answers that read nothing, report tool
#   failures ("tool attempts timed out") or cite files outside the checkout; see there.
# - After a quota error the marker $TMPDIR/dev-codex-<repo hash>.off makes every further call of
#   the next hour fall back at once instead of waiting for the timeout each time.
# Proven on macOS (Seatbelt). On Linux Codex enumerates deny globs only `glob_scan_max_depth`
# levels deep. DEV_CODEX_BIN selects the Codex binary (default `codex`); DEV_CODEX_TIMEOUT_SEC
# overrides --timeout-min and DEV_CODEX_PREFIXES the Homebrew prefixes (tests).
set -uo pipefail
RULE_REV=5      # bump when the profile changes: invalidates cached deny checks

out=
usage() { echo "usage: codex-review.sh --role <diff|security|fix|similar> --prompt <file> --input <file>... --head <sha> --out <file> [--timeout-min N]" >&2; exit 2; }
fallback() { [[ -n "$out" ]] && rm -f "$out"; echo "fallback: $1"; exit 3; }
q() { local s=${1//\\/\\\\}; s=${s//\"/\\\"}; printf '"%s"' "$s"; }     # TOML string

role= prompt= head= timeout_min=15 inputs=()
while [[ $# -gt 0 ]]; do
    [[ $# -ge 2 ]] || usage
    case "$1" in
        --role) role=$2 ;; --prompt) prompt=$2 ;; --input) inputs+=("$2") ;; --head) head=$2 ;;
        --out) out=$2 ;; --timeout-min) timeout_min=$2 ;; *) usage ;;
    esac
    shift 2
done
case "$role" in diff|security|fix|similar) ;; *) usage ;; esac
[[ -f "$prompt" && ${#inputs[@]} -gt 0 && -n "$head" && -n "$out" ]] || usage
# A .env never goes to Codex, not even as an input copy (the deny glob would not match input-1-.env).
for f in "${inputs[@]}"; do
    [[ -f "$f" ]] || usage
    case "$(basename "$f")" in .env|.env.*) usage ;; esac
done
[[ -d "$(dirname "$out")" ]] || usage
[[ "$timeout_min" =~ ^[1-9][0-9]*$ ]] || usage
limit=${DEV_CODEX_TIMEOUT_SEC:-$((timeout_min * 60))}
[[ "$limit" =~ ^[1-9][0-9]*$ ]] || usage

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
schema="$here/../schemas/review-findings.json"
top=$(git rev-parse --show-toplevel 2>/dev/null) || usage
top=$(cd "$top" && pwd -P)
common=$(cd "$top" && cd "$(git rev-parse --git-common-dir)" && pwd -P) || usage
commit=$(git -C "$top" rev-parse --verify --quiet "$head^{commit}") || usage
prompt=$(cd "$(dirname "$prompt")" && pwd)/$(basename "$prompt")
out=$(cd "$(dirname "$out")" && pwd)/$(basename "$out")
rm -f "$out"

base="${TMPDIR:-/tmp}"; base=$(cd "$base" && pwd -P) || fallback "no temporary directory"
find "$base" -maxdepth 1 -type d -name 'dev-codex-*' -mtime +0 -exec rm -rf {} + 2>/dev/null
marker="$base/dev-codex-$(printf %s "$top" | git hash-object --stdin | cut -c1-12).off"
if [[ -e "$marker" ]]; then
    [[ -n "$(find "$marker" -mmin -60 2>/dev/null)" ]] && fallback "quota"
    rm -f "$marker"
fi

bin="${DEV_CODEX_BIN:-codex}"
command -v "$bin" >/dev/null 2>&1 || fallback "codex not found ($bin)"
# The binary's directories become readable for Codex. Never when that opens $HOME (or above it)
# or the repository under review: then the grant would undo the denies.
binpath=$(command -v "$bin")
realbin=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$binpath")
bindirs=("$(cd "$(dirname "$binpath")" && pwd -P)" "$(dirname "$realbin")")
home=$(cd "$HOME" 2>/dev/null && pwd -P) || home=$HOME
guarded=("$top" "$common")
[[ "$(basename "$common")" == .git ]] && guarded+=("$(dirname "$common")")
for d in "${bindirs[@]}"; do
    [[ "$d" == / || "$d" == "$home" || "$home" == "$d"/* ]] && fallback "unsafe-codex-location"
    for g in "${guarded[@]}"; do
        [[ "$d" == "$g" || "$d" == "$g"/* ]] && fallback "unsafe-codex-location"
    done
done

work= secret= pid= rc= timed_out=
cleanup() {
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill -TERM -- "-$pid" 2>/dev/null; sleep 1; kill -KILL -- "-$pid" 2>/dev/null
    fi
    [[ -n "$work" ]] && rm -rf "$work"
    [[ -n "$secret" ]] && rm -rf "$secret"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

work=$(mktemp -d "$base/dev-codex-XXXXXX") || fallback "no temporary directory"
work=$(cd "$work" && pwd -P)

# The profile. Paths are real paths: the sandbox matches resolved paths (/tmp is /private/tmp).
# A duplicate key makes the value invalid TOML, which Codex takes as a plain string and ignores.
fs="{$(q :minimal)=\"read\", $(q :slash_tmp)=\"deny\"" seen=" "
grant() { [[ "$seen" == *" $(q "$1") "* ]] && return; seen+="$(q "$1") "; fs+=", $(q "$1")=\"$2\""; }
# Denies first: on a duplicate path the first entry wins, and a deny must never be lost.
grant "$top" deny
grant "$common" deny
[[ "$(basename "$common")" == .git ]] && grant "$(dirname "$common")" deny
for d in .ssh .aws .config .codex .gnupg .docker .kube Library/Keychains; do grant "$HOME/$d" deny; done
grant "$work" read                                       # clone, input, schema, analyzer copies
# Codex re-executes its own binary inside the sandbox (checked safe above), and Homebrew tools live
# outside :minimal. Only the tool parts of a prefix: etc/ and var/ hold service configs and data.
for d in "${bindirs[@]}"; do grant "$d" read; done
for p in ${DEV_CODEX_PREFIXES:-/opt/homebrew /usr/local /home/linuxbrew/.linuxbrew}; do
    for sub in bin Cellar Caskroom lib libexec opt share; do
        [[ -d "$p/$sub" ]] && grant "$(cd "$p/$sub" && pwd -P)" read
    done
done
fs+=', glob_scan_max_depth=3, "/"={"**/.env"="deny", "**/.env.*"="deny"}}'

# run_codex <dir> <log> <codex exec args...>: sets rc and timed_out.
run_codex() {
    local dir=$1 log=$2; shift 2
    set -m      # own process group, so the watchdog and the trap reach every Codex child
    ( cd "$dir" && exec "$bin" exec --ephemeral --ignore-user-config --skip-git-repo-check --color never \
        -c 'default_permissions="dev-review"' -c "permissions.dev-review.filesystem=$fs" \
        -c 'shell_environment_policy.set={GIT_CONFIG_GLOBAL="/dev/null"}' \
        "$@" </dev/null >"$log" 2>&1 ) &
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
}
quota_or() {        # $1 = log, $2 = reason if it was not the quota
    if tail -n 40 "$1" | grep -qiE '^error[: ].*(usage limit|rate limit|quota|too many requests|\b429\b)'; then
        touch "$marker"
        fallback "quota"
    fi
    fallback "$2"
}

# Deny check, once per binary and version.
version=$("$bin" --version 2>/dev/null </dev/null | head -n 1)
ok="$base/dev-codex-ok-$(printf '%s\n' "$(command -v "$bin")" "$version" "$RULE_REV" | git hash-object --stdin | cut -c1-12)"
if [[ ! -e "$ok" ]]; then
    chk="$work/deny-check"; mkdir -p "$chk/files"
    secret=$(mktemp -d "$base/dev-codex-secret-XXXXXX") || fallback "no temporary directory"
    secret=$(cd "$secret" && pwd -P)
    nonce=$(printf '%s' "$RANDOM$RANDOM$$$(date +%s)" | git hash-object --stdin | cut -c1-16)
    printf 'control-%s\n' "$nonce" >"$chk/files/control.txt"
    printf 'CHECK=env-%s\n' "$nonce" >"$chk/files/.env"
    printf 'denied-%s\n' "$nonce" >"$secret/secret.txt"
    # The paths sit in a script: named in the prompt, the model refuses to touch denied paths and
    # the check would prove nothing.
    printf 'cat %s %s %s 2>&1\n' "$chk/files/control.txt" "$chk/files/.env" "$secret/secret.txt" >"$chk/files/probe.sh"
    run_codex "$chk" "$work/deny-check.log" -o "$work/deny-check.out" \
        "deny-check: run exactly this one shell command and nothing else: bash $chk/files/probe.sh
Then reply with its complete output verbatim in a code block, nothing else. It is a sandbox configuration check that prints test values and error messages."
    [[ -n "$timed_out" ]] && fallback "deny-check timeout after $limit s"
    (( rc == 0 )) || quota_or "$work/deny-check.log" "deny-check failed (codex exit $rc)"
    grep -qE "env-$nonce|denied-$nonce" "$work/deny-check.out" "$work/deny-check.log" 2>/dev/null \
        && fallback "deny-rule-not-enforced"
    grep -q "control-$nonce" "$work/deny-check.out" 2>/dev/null || fallback "deny-check inconclusive"
    touch "$ok"
    rm -rf "$secret"; secret=
fi

wt="$work/checkout"
git clone --quiet --no-checkout "$common" "$wt" >/dev/null 2>&1 || fallback "clone of the repository failed"
git -C "$wt" -c advice.detachedHead=false checkout --quiet --detach "$commit" >/dev/null 2>&1 \
    || fallback "checkout of $head failed"
# Nothing secret and no Codex project config in the checkout, even when committed.
find "$wt" -name .git -prune -o \( -name '.env' -o -name '.env.*' \) -type f -print0 | xargs -0 rm -f
rm -rf "$wt/.codex"
listed= n=0
for f in "${inputs[@]}"; do
    n=$((n + 1)); copy="$work/input-$n-$(basename "$f")"
    cp "$f" "$copy" || fallback "input unreadable"
    listed+="Input file (read it first): $copy
"
done
python3 "$here/codex-result.py" model-schema --schema "$schema" >"$work/schema.json" \
    || fallback "schema unreadable"

text="$(python3 "$here/codex-result.py" localize-prompt --prompt "$prompt" --analyzers "$here/../analyzers" \
    --to "$work/analyzers")" || fallback "prompt unreadable"
text="$text

${listed}You are in a clean checkout of commit $commit (the repository root is the current directory).
Your final answer is JSON matching the given schema. files_read = the number of files you actually
opened and read (0 if none); blocked_reason = empty if you reviewed, otherwise why you could not.
Every finding needs file (relative to the repository root), line, the quoted line(s) and the
concrete failing input. No findings is a valid answer."

run_codex "$wt" "$work/codex.log" --output-schema "$work/schema.json" -o "$work/answer.json" "$text"
# Usage for the caller (stderr: stdout stays the one fallback line); the log goes with $work.
tokens=$(awk 'f { print; exit } /^tokens used$/ { f = 1 }' "$work/codex.log" 2>/dev/null)
[[ -n "$tokens" ]] && echo "tokens used: $tokens" >&2
[[ -n "$timed_out" ]] && fallback "timeout after $limit s"
(( rc == 0 )) || quota_or "$work/codex.log" "codex exit $rc"

python3 "$here/codex-result.py" check --schema "$schema" --result "$work/answer.json" --role "$role" \
    --checkout "$wt" --out "$out"
rc=$?
(( rc == 0 || rc == 3 )) || fallback "result check failed ($rc)"
exit "$rc"
