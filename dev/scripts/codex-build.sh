#!/usr/bin/env bash
# codex-build.sh — lets Codex build one phase in the phase worktree (lean flow, builder codex).
#
#   codex-build.sh --brief <file> --head <sha> --out <file> [--timeout-min 60] [--keep-partial]
#
# Run from inside the phase worktree, clean and at --head. --brief is the phase brief (spec,
# acceptance criteria, files); --out a file outside the worktree.
# Exit 0 = Codex finished: its changes are left uncommitted in the worktree. --out holds
#          `builder: codex`, `files:`, `ignored-new:` (new ignored paths), `ignored-changed:` (files
#          changed inside ignored trees that existed, e.g. node_modules/), `hooks-changed:` (tracked
#          hook paths and package.json scripts), refs other workers may have moved, and Codex's
#          summary. The caller reviews and commits.
# Exit 3 = unusable; one line `fallback: <reason>` on stdout, --out says what Codex had left and
#          what happened to it. Reasons: quota, timeout, crash, no changes, permission profile not
#          enforced or check inconclusive, an unsafe `.env*` link, a Codex commit or change of
#          HEAD, this worktree's branch or refs/worktree/*, a changed tag or refs/stash (reported
#          only: the shared git dir belongs to every worker), a changed `.git` or git config
#          (hooks, fsmonitor, filters, includes), a changed `.env*` entry, a symlink leading
#          outside the repository, processes that survive the kill, a worktree check that could
#          not finish (unreadable directory, failed git listing). Without --keep-partial the
#          worktree is reset to --head (reset --hard, clean, new ignored paths removed; ignored
#          paths that existed stay); with it the changes stay, uncommitted, on --head. A Codex
#          commit is undone and a new `.env*` link removed either way. After a changed `.git` or
#          git config, or with surviving processes, nothing runs in the worktree: left as it is
#          (the quota marker and the refs report still happen).
# Exit 2 = usage error: bad arguments, not a git worktree, worktree dirty or not at --head,
#          --out inside the worktree, or ROADMAP.md frontmatter without `defaults.builder: codex`.
#
# Guards:
# - Only where the project opted in: `defaults.builder: codex` in the worktree's ROADMAP.md
#   frontmatter. Codex write rights exist only in a pilot project; elsewhere Codex only reviews.
# - Codex runs under a permission profile, never `--sandbox` (that switches to the legacy sandbox,
#   which reads the whole disk, and drops the profile): deny first `:slash_tmp`, the main checkout's
#   working tree (when the worktree is a linked one) and credential folders in $HOME; write the
#   worktree and a private scratch dir (its TMPDIR); read `:minimal`, the git dirs, the Codex
#   binary's dirs, Homebrew tool dirs, toolchain dirs that exist (cargo, rustup, pnpm store) and
#   the targets of the worktree's `.env*` symlinks (owner-approved in the pilot) — only untracked
#   links at the top level or one below, to a regular file with no other hard link, inside the
#   main checkout and outside credential folders (compared by device and inode: APFS is
#   case-insensitive); else exit 3.
#   Network off, no approvals (nothing escalates), no user config or execpolicy rules; a `.codex/`
#   project config in the worktree is refused. So Codex cannot push; a linked worktree's git dir
#   is read-only.
# - The profile is only as good as the Codex build that reads it. Before the first build with a
#   binary and version, a permission check runs probe.sh in a layout like the real one (worktree
#   inside a denied checkout, a readable `.env` target in it). The probe logs one line per probe
#   and an end marker to its own result file; the model's reply is never read. A denied read (also
#   through a case variant of a denied `.ssh` inside a grant), an unlisted read, a write outside
#   the worktree or to /tmp = exit 3 `permission profile not enforced`; no end marker or a
#   blocked allowed probe = `permission check inconclusive`. Never a fallback to the legacy
#   sandbox. A pass is cached in ${XDG_CACHE_HOME:-~/.cache}/dev-codex-build
#   (0700); a marker counts only in a dir owned by the user and not group- or world-writable.
# - After the run every git command uses the recorded git dir and work tree, no system or global
#   config, `core.hooksPath=/dev/null` and an empty `core.fsmonitor`: nothing Codex wrote runs.
# - Codex may leave processes behind (setsid, nohup). After it exits, a sweep sends TERM, then
#   KILL, to processes carrying the scratch dir in environment or arguments, in Codex's process
#   group or (if not ours) session, new ones with cwd in the worktree, and their descendants; up
#   to 3 passes; survivors = exit 3. Limit: no cgroups or namespaces (macOS has none), so a
#   process that leaves the group, drops the scratch dir and its cwd escapes.
# - Deletions go through codex-build-util.py: NUL-separated paths, no newline, tab or `..`,
#   strictly inside the worktree, no symlinked parent; a symlink is removed, never its target.
# - `.env*` files are never copied, read or printed; only their kind, link target, size and mtime
#   are compared.
# - Quota: the marker $TMPDIR/dev-codex-<repo hash>.off (shared with codex-review.sh) makes every
#   further call of the next hour fall back at once.
# - macOS has no `timeout`: Codex runs in its own process group under a watchdog; the trap kills it
#   and removes the temp dir on every catchable exit path.
# DEV_CODEX_BIN selects the Codex binary (default `codex`); DEV_CODEX_TIMEOUT_SEC overrides
# --timeout-min, DEV_CODEX_PREFIXES the Homebrew prefixes and DEV_CODEX_SWEEP_DRYRUN=1 makes the
# sweep kill nothing (tests: an unkillable process). DEV_CODEX_EFFORT
# (minimal|low|medium|high|xhigh) sets the reasoning effort.
set -uo pipefail
RULE_REV=3      # bump when the profile or the check changes: invalidates cached checks

usage() { echo "usage: codex-build.sh --brief <file> --head <sha> --out <file> [--timeout-min N] [--keep-partial]${1:+ ($1)}" >&2; exit 2; }
q() { local s=${1//\\/\\\\}; s=${s//\"/\\\"}; printf '"%s"' "$s"; }     # TOML string
real() { python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"; }

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

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
util="$here/codex-build-util.py"
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
cd "$top" || usage

# The git layout, recorded before Codex runs; afterwards git runs only against it (g).
gitdir=$(git rev-parse --absolute-git-dir) && gitdir=$(cd "$gitdir" && pwd -P) || usage
common=$(cd "$(git rev-parse --git-common-dir)" && pwd -P) || usage
main=; [[ "$(basename "$common")" == .git ]] && main=$(dirname "$common")
orig_sym=$(git symbolic-ref -q HEAD)
g() { GIT_DIR="$gitdir" GIT_WORK_TREE="$top" GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
      git -c core.hooksPath=/dev/null -c core.fsmonitor= "$@"; }
dotgit() {
    if [[ -L "$top/.git" ]]; then echo "link $(readlink "$top/.git")"
    elif [[ -f "$top/.git" ]]; then echo file; cat "$top/.git"
    elif [[ -d "$top/.git" ]]; then echo dir
    else echo missing; fi
}
gitcfg() {          # config that makes git run code or read elsewhere
    g config --list 2>/dev/null | grep -iE '^(core\.(hookspath|fsmonitor|worktree|gitproxy|sshcommand|pager|editor|askpass|attributesfile|excludesfile)|hook\.|include\.|includeif\.|filter\.|diff\.[^=]*\.(textconv|command)|merge\.[^=]*\.driver|credential\.|alias\.|uploadpack\.|extensions\.)'
}
refs() {
    g for-each-ref --format='%(refname) %(objectname)'
    echo "HEAD $(g rev-parse -q --verify HEAD)"
    echo "HEAD-symbolic $(g symbolic-ref -q HEAD)"
}
list() { local f; while IFS= read -r f; do [[ -n "$f" ]] && printf -- '- %s\n' "$f"; done <<<"$1"; }
utilg() { python3 "$util" "$1" --top "$top" --gitdir "$gitdir" "${@:2}"; }

base="${TMPDIR:-/tmp}"; base=$(cd "$base" && pwd -P) || { echo "fallback: no temporary directory"; exit 3; }
find "$base" -maxdepth 1 -type d -name 'dev-codex-build-*' -mtime +0 -exec rm -rf {} + 2>/dev/null
marker="$base/dev-codex-$(printf %s "$top" | git hash-object --stdin | cut -c1-12).off"
home=$(cd "$HOME" 2>/dev/null && pwd -P) || home=$HOME
creds=(); for d in .ssh .aws .config .codex .gnupg .docker .kube Library/Keychains; do creds+=("$home/$d"); done

work= secret= pid= rc= timed_out= answer= git_unsafe= killed= refs_own= refs_other= analyzed= nfiles=0
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

# fallback <reason>: report what Codex left, undo its commit, reset unless --keep-partial.
# Only HEAD and this worktree's branch are reset; tags and refs/stash are shared, never touched.
fallback() {
    local partial=none refused=
    if [[ -n "$git_unsafe" ]]; then
        partial="not touched (${git_unsafe/#1/git state changed by Codex}; inspect the worktree by hand)"
    elif [[ -n "$analyzed" ]]; then
        if [[ "$(g rev-parse HEAD)" != "$commit" || "$(g symbolic-ref -q HEAD)" != "$orig_sym" ]]; then
            if [[ -n "$orig_sym" ]]; then g symbolic-ref HEAD "$orig_sym"
            else g update-ref --no-deref HEAD "$commit"; fi
            g reset -q "$commit"                             # commit undone, changes stay
        fi
        refused=$(python3 "$util" remove --top "$top" --list "$work/env.rm")   # new .env* links: always
        if (( nfiles > 0 )) || [[ -s "$work/ignored.rm" ]]; then
            if [[ -n "$keep" ]]; then
                partial="kept, uncommitted on $commit"
            else
                g reset -q --hard "$commit" && g clean -fdq
                refused=$(printf '%s\n' "$refused"; python3 "$util" remove --top "$top" --list "$work/ignored.rm")
                partial="reset to $commit"
            fi
        fi
    fi
    {
        echo "fallback: $1"
        echo "head: $commit"
        echo "partial: $partial"
        [[ "$1" == "codex changed a .env file" ]] && echo "note: existing .env files are not restored; check them by hand"
        echo "refs-changed:"; list "$(cut -d' ' -f1 <<<"$refs_own")"
        echo "refs-other:"; list "$(cut -d' ' -f1 <<<"$refs_other")"
        [[ -n "$killed" ]] && echo "killed: $killed"
        [[ -n "$analyzed" ]] && cat "$work/report"
        [[ -n "${refused//$'\n'/}" ]] && { echo "not-removed:"; list "$refused"; }
        echo "summary:"; [[ -n "$answer" && -s "$answer" ]] && cat "$answer"
    } >"$out"
    echo "fallback: $1"
    exit 3
}

if [[ -e "$marker" ]]; then
    [[ -n "$(find "$marker" -mmin -60 2>/dev/null)" ]] && fallback "quota"
    rm -f "$marker"
fi
[[ -e "$top/.codex" ]] && fallback "project .codex config in the worktree"
bin="${DEV_CODEX_BIN:-codex}"
command -v "$bin" >/dev/null 2>&1 || fallback "codex not found ($bin)"
binpath=$(command -v "$bin"); realbin=$(real "$binpath")
bindirs=("$(cd "$(dirname "$binpath")" && pwd -P)" "$(dirname "$realbin")")
for d in "${bindirs[@]}"; do      # these dirs become readable: never $HOME, above it or the repo
    [[ "$d" == / || "$d" == "$home" || "$home" == "$d"/* ]] && fallback "unsafe-codex-location"
    for p in "$top" "$common" ${main:+"$main"}; do
        [[ "$d" == "$p" || "$d" == "$p"/* ]] && fallback "unsafe-codex-location"
    done
done
envtargets=()
targets=$(utilg env-targets --main "${main:-$top}" --home "$home" "${creds[@]/#/--deny=}"); trc=$?
(( trc == 3 )) && fallback "unsafe .env link: $targets"
(( trc != 0 )) && fallback "worktree check failed: ${targets:-util exit $trc}"
while IFS= read -r t; do [[ -n "$t" ]] && envtargets+=("$t"); done <<<"$targets"

work=$(mktemp -d "$base/dev-codex-build-XXXXXX") || fallback "no temporary directory"
work=$(cd "$work" && pwd -P)
scratch="$work/scratch"; mkdir -p "$scratch"
answer="$work/answer.md"

# profile <worktree> <scratch> <main to deny or ""> <extra read paths...>: sets fs.
profile() {
    local wt=$1 tmp=$2 deny=$3 d p sub; shift 3
    fs="{$(q :minimal)=\"read\", $(q :slash_tmp)=\"deny\"" seen=" "
    grant() { [[ "$seen" == *" $(q "$1") "* ]] && return; seen+="$(q "$1") "; fs+=", $(q "$1")=\"$2\""; }
    # Denies first: on a duplicate path the first entry wins, and a deny must never be lost.
    [[ -n "$deny" && "$deny" != "$wt" ]] && grant "$deny" deny
    for d in "${creds[@]}" ${probe_deny:+"$probe_deny"}; do grant "$d" deny; done
    grant "$wt" write
    grant "$tmp" write
    for p in "$@"; do grant "$p" read; done
    for d in "${bindirs[@]}"; do grant "$d" read; done
    for p in ${DEV_CODEX_PREFIXES:-/opt/homebrew /usr/local /home/linuxbrew/.linuxbrew}; do
        for sub in bin Cellar Caskroom lib libexec opt share; do
            [[ -d "$p/$sub" ]] && grant "$(cd "$p/$sub" && pwd -P)" read
        done
    done
    for d in "$home/.cargo" "$home/.rustup" "${PNPM_HOME:-}" "$home/Library/pnpm" \
             "$home/.local/share/pnpm" "$home/.pnpm-store"; do
        [[ -n "$d" && -d "$d" ]] && grant "$(cd "$d" && pwd -P)" read
    done
    fs+="}"
}

# run_codex <dir> <scratch> <log> <answer> <codex exec args...>: sets rc, timed_out, codex_sid.
run_codex() {
    local dir=$1 tmp=$2 log=$3 ans=$4; shift 4
    set -m      # own process group, so the watchdog and the trap reach every Codex child
    ( cd "$dir" && exec "$bin" exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check \
        --color never -C "$dir" \
        -c 'default_permissions="dev-build"' -c "permissions.dev-build.filesystem=$fs" \
        -c 'permissions.dev-build.network.enabled=false' -c 'approval_policy="never"' \
        -c "shell_environment_policy.set={TMPDIR=$(q "$tmp"), GIT_CONFIG_GLOBAL=\"/dev/null\", GIT_TERMINAL_PROMPT=\"0\"}" \
        ${effort[@]+"${effort[@]}"} -o "$ans" "$@" </dev/null >"$log" 2>&1 ) &
    pid=$!
    set +m
    codex_pgid=$pid
    codex_sid=$(python3 -c 'import os,sys; print(os.getsid(int(sys.argv[1])))' "$pid" 2>/dev/null)
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
quota_in() { tail -n 40 "$1" | grep -qiE '^error[: ].*(usage limit|rate limit|quota|too many requests|\b429\b)'; }

# Permission check, once per binary and version: never build under a profile Codex ignores.
cache="${XDG_CACHE_HOME:-$home/.cache}/dev-codex-build"
[[ -d "$cache" ]] || { mkdir -p "$cache" && chmod 700 "$cache"; } || fallback "no cache directory"
cache_ok() {        # a marker counts only in a dir that only this user can write
    python3 - "$cache" <<'PY'
import os, stat, sys
st = os.lstat(sys.argv[1])
sys.exit(0 if stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and not st.st_mode & 0o022 else 1)
PY
}
version=$("$bin" --version 2>/dev/null </dev/null | head -n 1)
ok="$cache/ok-$(printf '%s\n' "$realbin" "$version" "$RULE_REV" | git hash-object --stdin | cut -c1-12)"
if ! { cache_ok && [[ -f "$ok" && ! -L "$ok" && -O "$ok" ]]; }; then
    secret=$(mktemp -d "$base/dev-codex-build-check-XXXXXX") || fallback "no temporary directory"
    secret=$(cd "$secret" && pwd -P)
    nonce=$(printf '%s' "$RANDOM$RANDOM$$$(date +%s)" | git hash-object --stdin | cut -c1-16)
    cm="$secret/main" cw="$secret/main/wt" ct="$secret/scratch" co="$secret/outside"
    cu="$cache/probe-$nonce"                   # under $HOME, covered by no grant
    mkdir -p "$cw/.ssh" "$ct" "$co" "$cu"
    printf 'denied-%s\n' "$nonce" >"$cm/denied.txt"
    printf 'case-%s\n' "$nonce" >"$cw/.ssh/id"
    printf 'unlisted-%s\n' "$nonce" >"$cu/unlisted.txt"
    printf 'envok-%s\n' "$nonce" >"$cm/env-target.txt"
    slash="/tmp/dev-codex-build-probe-$nonce"
    # The paths sit in a script: named in the prompt, the model refuses to touch denied paths.
    # The script logs every probe itself; only that log counts, never the model's reply.
    {
        echo "exec >\"$cw/result.txt\" 2>&1"
        echo 'r() { if cat -- "$2" >/dev/null 2>&1; then echo "$1 open"; else echo "$1 blocked"; fi; }'
        echo 'w() { if ( echo x >"$2" ) 2>/dev/null; then echo "$1 open"; else echo "$1 blocked"; fi; }'
        echo "r read-denied '$cm/denied.txt'"
        echo "r read-unlisted '$cu/unlisted.txt'"
        echo "r read-denied-case '$cw/.SSH/id'"     # a .ssh deny inside a grant, by another case
        echo "r read-env '$cm/env-target.txt'"
        echo "w write-worktree '$cw/written.txt'"
        echo "w write-outside '$co/written.txt'"
        echo "w write-tmp '$slash'"
        echo "echo 'end-$nonce'"
    } >"$cw/probe.sh"
    probe_deny="$cw/.ssh" profile "$cw" "$ct" "$cm" "$cm/env-target.txt"
    run_codex "$cw" "$ct" "$work/check.log" "$work/check.out" \
        "permission-check: run exactly this one shell command and nothing else: bash $cw/probe.sh
Then reply with done. It is a sandbox configuration check."
    res="$cw/result.txt" leaked=
    for p in read-denied read-unlisted read-denied-case write-outside write-tmp; do
        grep -qx "$p open" "$res" 2>/dev/null && leaked=1
    done
    [[ -e "$co/written.txt" ]] && leaked=1
    [[ -e "$slash" || -L "$slash" ]] && { leaked=1; rm -f "$slash"; }
    rm -rf "$cu"
    [[ -n "$leaked" ]] && fallback "permission profile not enforced"
    [[ -n "$timed_out" ]] && fallback "permission check timeout after $limit s"
    if (( rc != 0 )); then quota_in "$work/check.log" && { touch "$marker"; fallback quota; }
        fallback "permission check failed (codex exit $rc)"; fi
    for p in "read-denied blocked" "read-unlisted blocked" "read-denied-case blocked" "read-env open" \
             "write-worktree open" "write-outside blocked" "write-tmp blocked" "end-$nonce"; do
        grep -qx "$p" "$res" 2>/dev/null || fallback "permission check inconclusive"
    done
    cache_ok && touch "$ok"
    rm -rf "$secret"; secret=
fi

# Snapshots before the run.
dotgit >"$work/dotgit.before"; gitcfg >"$work/cfg.before"; refs | sort >"$work/refs.before"
utilg snapshot --out "$work/snap.before" || fallback "snapshot failed"
ps -axo pid= 2>/dev/null | tr -d ' ' >"$work/pids.before"
touch "$work/stamp"

text="$(cat "$brief")

---
You build this phase in a git worktree: the current directory, at commit $commit.
- Write the code and a test per acceptance criterion, named after it; run the unit tests.
- Leave every change uncommitted: never run \`git commit\`, \`git push\`, \`git reset\`, \`git stash\`,
  \`git checkout\` or \`git switch\`, and create no branches or tags. Do not edit git config or hooks.
- Never print, copy or edit \`.env\` files. Stay inside this directory; scratch files go to \$TMPDIR.
- No network: do not install packages; if one is missing, say so under open:.
- Start no background processes that outlive your commands.
Your final message: a short summary, then \`files:\` with one changed path per line, then \`open:\`
with anything left undone or failing (or \`none\`)."

profile "$top" "$scratch" "$main" "$gitdir" "$common" "$top/.git" ${envtargets[@]+"${envtargets[@]}"}
run_codex "$top" "$scratch" "$work/codex.log" "$answer" "$text"
tokens=$(awk 'f { print; exit } /^tokens used$/ { f = 1 }' "$work/codex.log" 2>/dev/null)
[[ -n "$tokens" ]] && echo "tokens used: $tokens" >&2

read -r nkilled survivors <<<"$(python3 "$util" sweep --top "$top" --scratch "$scratch" \
    --before "$work/pids.before" --pgid "$codex_pgid" --sid "${codex_sid:-}" \
    ${DEV_CODEX_SWEEP_DRYRUN:+--dry-run})"
[[ "${nkilled:-0}" != 0 ]] && killed="$nkilled leftover process(es)"
# Quota marker and refs report hold on every path, survivors included; refs are read only while
# `.git` and git config are as before (reading refs changes nothing).
quota=; quota_in "$work/codex.log" && { quota=1; touch "$marker"; }
gitbad=
[[ "$(dotgit)" != "$(cat "$work/dotgit.before")" ]] && gitbad="codex changed .git"
[[ -z "$gitbad" && "$(gitcfg)" != "$(cat "$work/cfg.before")" ]] && gitbad="codex changed git config"
if [[ -z "$gitbad" ]]; then
    refs | sort >"$work/refs.after"
    refdiff=$(python3 "$util" refdiff "$work/refs.before" "$work/refs.after" "$orig_sym")
    refs_own=$(grep -E '^(own|shared) ' <<<"$refdiff" | cut -d' ' -f2-)
    refs_other=$(grep '^other ' <<<"$refdiff" | cut -d' ' -f2-)
fi
# A live process could swap paths under a reset or delete: touch nothing, like a changed .git.
[[ -n "${survivors:-}" ]] && { git_unsafe="processes still running"; fallback "codex left processes running"; }

# After the sweep: integrity first; these hold even when Codex also ran out of time or quota.
[[ -n "$gitbad" ]] && { git_unsafe=1; fallback "$gitbad"; }
flags=$(utilg analyze --commit "$commit" --before "$work/snap.before" --stamp "$work/stamp" \
    --report "$work/report" --rm-list "$work/ignored.rm" --env-rm "$work/env.rm") \
    || { git_unsafe=1; fallback "analysis failed"; }
envs_changed=0 outside=0
for kv in $flags; do case "$kv" in files=*) nfiles=${kv#files=} ;; envs_changed=*) envs_changed=${kv#*=} ;;
    outside=*) outside=${kv#*=} ;; esac; done
analyzed=1
if [[ -n "$refs_own" ]]; then
    [[ "$(g rev-parse HEAD)" != "$commit" ]] && fallback "codex committed"
    fallback "codex changed git refs"
fi
[[ "$envs_changed" == 1 ]] && fallback "codex changed a .env file"
[[ "$outside" == 1 ]] && fallback "codex touched a path outside the repository"
[[ -n "$timed_out" ]] && fallback "timeout after $limit s"
[[ -n "$quota" ]] && fallback "quota"
(( rc == 0 )) || fallback "codex exit $rc"
(( nfiles > 0 )) || fallback "codex made no changes"

{
    echo "builder: codex"
    echo "head: $commit"
    echo "refs-other:"; list "$(cut -d' ' -f1 <<<"$refs_other")"
    [[ -n "$killed" ]] && echo "killed: $killed"
    cat "$work/report"
    echo "summary:"; [[ -s "$answer" ]] && cat "$answer"
} >"$out"
exit 0
