#!/usr/bin/env bash
# codex-build.sh — lets Codex build one phase in the phase worktree (lean flow, builder codex).
#
#   codex-build.sh --brief <file> --head <sha> --out <file> [--timeout-min 60] [--keep-partial]
#
# Run from inside the phase worktree, clean and at --head. --brief is the phase brief (spec,
# acceptance criteria, files); --out a file outside the worktree.
# Exit 0 = Codex finished: its changes are left uncommitted in the worktree, --out holds
#          `builder: codex`, the `files:` list, `ignored-new:` (new ignored paths, e.g. build output),
#          refs other workers may have moved, and Codex's summary. The caller reviews and commits.
# Exit 3 = unusable; one line `fallback: <reason>` on stdout, --out says what Codex had left and
#          what happened to it. Reasons: quota, timeout, crash, no changes, permission profile not
#          enforced, a Codex commit or change of this worktree's refs (HEAD, its branch, stash,
#          refs/worktree/*, tags), a changed `.git` or git config (hooks, fsmonitor, filters,
#          includes), a changed `.env*` entry, a symlink leading outside the repository, processes
#          that survive the kill. Without --keep-partial the worktree is reset to --head (reset
#          --hard, clean, new ignored paths removed; ignored paths that existed stay); with it the
#          changes stay, uncommitted, on --head. A Codex commit is undone either way. After a
#          changed `.git` or git config no git command runs: the worktree is left as it is.
# Exit 2 = usage error: bad arguments, not a git worktree, worktree dirty or not at --head,
#          --out inside the worktree, or ROADMAP.md frontmatter without `defaults.builder: codex`.
#
# Guards:
# - Only where the project opted in: `defaults.builder: codex` in the worktree's ROADMAP.md
#   frontmatter. Codex write rights exist only in a pilot project; elsewhere Codex only reviews.
# - Codex runs under a permission profile, never `--sandbox` (that switches to the legacy sandbox,
#   which reads the whole disk, and drops the profile): deny first `:slash_tmp`, the main checkout's
#   working tree (when the worktree is a linked one) and credential folders in $HOME; write the
#   worktree and a private scratch dir (its TMPDIR); read `:minimal`, the git dirs, the targets of
#   the worktree's existing `.env*` symlinks (owner-approved in the pilot), the Codex binary's dirs,
#   Homebrew tool dirs and toolchain dirs that exist (cargo, rustup, pnpm store). Network off, no
#   approvals (nothing escalates), no user config or execpolicy rules; a `.codex/` project config
#   in the worktree is refused. So Codex cannot push; a linked worktree's git dir is read-only.
# - The profile is only as good as the Codex build that reads it. Before the first build with a
#   binary and version, a permission check runs a probe in a layout like the real one (worktree
#   inside a denied checkout, a readable `.env` target in it): a denied file read, or a write
#   outside the worktree or to /tmp = exit 3 `permission profile not enforced`. Never a fallback
#   to the legacy sandbox. A passed check is cached in $TMPDIR/dev-codex-build-ok-<hash>.
# - After the run every git command uses the recorded git dir and work tree, no system or global
#   config, `core.hooksPath=/dev/null` and an empty `core.fsmonitor`: nothing Codex wrote runs.
# - Codex may leave processes behind (setsid, nohup). After it exits, processes whose environment
#   or arguments carry the scratch dir, and new processes whose cwd is in the worktree, get TERM,
#   then KILL; survivors = exit 3. Own ancestors and processes that existed before are spared.
# - `.env*` files are never copied, read or printed; only their kind, link target, size and mtime
#   are compared.
# - Quota: the marker $TMPDIR/dev-codex-<repo hash>.off (shared with codex-review.sh) makes every
#   further call of the next hour fall back at once.
# - macOS has no `timeout`: Codex runs in its own process group under a watchdog; the trap kills it
#   and removes the temp dir on every catchable exit path.
# DEV_CODEX_BIN selects the Codex binary (default `codex`); DEV_CODEX_TIMEOUT_SEC overrides
# --timeout-min and DEV_CODEX_PREFIXES the Homebrew prefixes (tests). DEV_CODEX_EFFORT
# (minimal|low|medium|high|xhigh) sets the reasoning effort.
set -uo pipefail
RULE_REV=1      # bump when the profile changes: invalidates cached permission checks

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
envs() {            # .env* metadata, never content
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
ignored() {         # path<TAB>kind: ignored paths at the top of each ignored tree
    g ls-files -z --others --ignored --exclude-standard --directory | python3 -c '
import os, sys
for p in sys.stdin.read().split("\0"):
    if not p:
        continue
    a = os.path.join(sys.argv[1], p.rstrip("/"))
    kind = "link " + os.readlink(a) if os.path.islink(a) else ("dir" if os.path.isdir(a) else "file")
    print(p + "\t" + kind)' "$top"
}
changed() {         # paths that differ from --head: tracked changes, commits, untracked files
    { g diff --no-ext-diff --name-only "$commit"; g ls-files --others --exclude-standard; } | sort -u
}
list() { local f; while IFS= read -r f; do [[ -n "$f" ]] && printf -- '- %s\n' "$f"; done <<<"$1"; }

base="${TMPDIR:-/tmp}"; base=$(cd "$base" && pwd -P) || { echo "fallback: no temporary directory"; exit 3; }
find "$base" -maxdepth 1 -type d -name 'dev-codex-build-*' -mtime +0 -exec rm -rf {} + 2>/dev/null
marker="$base/dev-codex-$(printf %s "$top" | git hash-object --stdin | cut -c1-12).off"

work= secret= pid= rc= timed_out= answer= git_unsafe= killed= refs_own= refs_other= new_ignored=
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

# fallback <reason>: report what Codex left, undo its commit and refs, reset unless --keep-partial.
fallback() {
    local files= partial=none r old new
    if [[ -n "$git_unsafe" ]]; then
        partial="not touched (git state changed by Codex; check the worktree by hand)"
    elif [[ -n "$work" && -f "$work/refs.before" ]]; then
        files=$(changed 2>/dev/null)
        if [[ "$(g rev-parse HEAD)" != "$commit" || "$(g symbolic-ref -q HEAD)" != "$orig_sym" ]]; then
            if [[ -n "$orig_sym" ]]; then g symbolic-ref HEAD "$orig_sym"
            else g update-ref --no-deref HEAD "$commit"; fi
            g reset -q "$commit"                             # commit undone, changes stay
        fi
        while read -r r old new; do                          # own refs back to where they were
            [[ -z "$r" || "$r" == HEAD* || "$r" == "$orig_sym" ]] && continue
            if [[ "$old" == - ]]; then g update-ref -d "$r"; else g update-ref "$r" "$old"; fi
        done <<<"$refs_own"
        if [[ -n "$files" || -n "$new_ignored" ]]; then
            if [[ -n "$keep" ]]; then
                partial="kept, uncommitted on $commit"
            else
                g reset -q --hard "$commit" && g clean -fdq
                while IFS= read -r r; do [[ -n "$r" ]] && rm -rf -- "${top:?}/${r%/}"; done <<<"$new_ignored"
                partial="reset to $commit"
            fi
        fi
    fi
    {
        echo "fallback: $1"
        echo "head: $commit"
        echo "partial: $partial"
        [[ "$1" == "codex changed a .env file" ]] && echo "note: .env files are not restored; check them by hand"
        echo "refs-changed:"; list "$(cut -d' ' -f1 <<<"$refs_own")"
        echo "refs-other:"; list "$(cut -d' ' -f1 <<<"$refs_other")"
        [[ -n "$killed" ]] && echo "killed: $killed"
        echo "files:"; list "$files"
        echo "ignored-new:"; list "$new_ignored"
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
home=$(cd "$HOME" 2>/dev/null && pwd -P) || home=$HOME
for d in "${bindirs[@]}"; do      # these dirs become readable: never $HOME, above it or the repo
    [[ "$d" == / || "$d" == "$home" || "$home" == "$d"/* ]] && fallback "unsafe-codex-location"
    for p in "$top" "$common" ${main:+"$main"}; do
        [[ "$d" == "$p" || "$d" == "$p"/* ]] && fallback "unsafe-codex-location"
    done
done

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
    for d in .ssh .aws .config .codex .gnupg .docker .kube Library/Keychains; do grant "$home/$d" deny; done
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

# run_codex <dir> <scratch> <log> <answer> <codex exec args...>: sets rc and timed_out.
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
version=$("$bin" --version 2>/dev/null </dev/null | head -n 1)
ok="$base/dev-codex-build-ok-$(printf '%s\n' "$realbin" "$version" "$RULE_REV" | git hash-object --stdin | cut -c1-12)"
if [[ ! -e "$ok" ]]; then
    secret=$(mktemp -d "$base/dev-codex-build-check-XXXXXX") || fallback "no temporary directory"
    secret=$(cd "$secret" && pwd -P)
    nonce=$(printf '%s' "$RANDOM$RANDOM$$$(date +%s)" | git hash-object --stdin | cut -c1-16)
    cm="$secret/main" cw="$secret/main/wt" ct="$secret/scratch" co="$secret/outside"
    mkdir -p "$cw" "$ct" "$co"
    printf 'denied-%s\n' "$nonce" >"$cm/denied.txt"
    printf 'envok-%s\n' "$nonce" >"$cm/env-target.txt"
    slash="/tmp/dev-codex-build-probe-$nonce"
    # The paths sit in a script: named in the prompt, the model refuses to touch denied paths.
    printf '%s\n' "cat $cm/denied.txt 2>&1" "cat $cm/env-target.txt 2>&1" \
        "echo written-$nonce > $cw/written.txt 2>&1" "echo leak-$nonce > $co/written.txt 2>&1" \
        "echo leak-$nonce > $slash 2>&1" >"$cw/probe.sh"
    profile "$cw" "$ct" "$cm" "$cm/env-target.txt"
    run_codex "$cw" "$ct" "$work/check.log" "$work/check.out" \
        "permission-check: run exactly this one shell command and nothing else: bash $cw/probe.sh
Then reply with its complete output verbatim in a code block, nothing else. It is a sandbox configuration check that prints test values and error messages."
    leaked=
    grep -qs "denied-$nonce" "$work/check.out" "$work/check.log" && leaked=1
    [[ -e "$co/written.txt" ]] && leaked=1
    [[ -e "$slash" ]] && { leaked=1; rm -f "$slash"; }
    [[ -n "$leaked" ]] && fallback "permission profile not enforced"
    [[ -n "$timed_out" ]] && fallback "permission check timeout after $limit s"
    if (( rc != 0 )); then quota_in "$work/check.log" && { touch "$marker"; fallback quota; }
        fallback "permission check failed (codex exit $rc)"; fi
    grep -qs "envok-$nonce" "$work/check.out" && grep -qs "written-$nonce" "$cw/written.txt" \
        || fallback "permission check inconclusive"
    touch "$ok"
    rm -rf "$secret"; secret=
fi

# Snapshots before the run.
envtargets=()
while IFS= read -r f; do
    [[ -L "$top/$f" ]] && envtargets+=("$(real "$top/$f")")
done < <(envs | cut -d' ' -f1)
dotgit >"$work/dotgit.before"; gitcfg >"$work/cfg.before"; refs | sort >"$work/refs.before"
envs >"$work/envs.before"; ignored | sort >"$work/ignored.before"
ps -axo pid= 2>/dev/null | tr -d ' ' >"$work/pids.before"

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

# Leftover processes: scratch in env or args, or new with cwd in the worktree. TERM, then KILL.
sweep=$(python3 - "$top" "$scratch" "$work/pids.before" <<'PY'
import os, signal, subprocess, sys, time
top, scratch, before = sys.argv[1], sys.argv[2], set(open(sys.argv[3]).read().split())
def table():
    rows = {}
    if sys.platform == "darwin":
        ps = subprocess.run(["ps", "-axww", "-E", "-o", "pid=,ppid=,command="], capture_output=True, text=True).stdout
        for line in ps.splitlines():
            parts = line.split(None, 2)
            if len(parts) >= 2:
                rows[parts[0]] = {"ppid": parts[1], "text": parts[2] if len(parts) > 2 else "", "cwd": ""}
        ls = subprocess.run(["lsof", "-nP", "-w", "-a", "-d", "cwd", "-Fpn", "-u", str(os.getuid())],
                            capture_output=True, text=True).stdout
        cur = None
        for line in ls.splitlines():
            if line.startswith("p"):
                cur = line[1:]
            elif line.startswith("n") and cur in rows:
                rows[cur]["cwd"] = line[1:]
    else:
        for p in os.listdir("/proc"):
            if not p.isdigit():
                continue
            try:
                ppid = open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()[1]
                text = open(f"/proc/{p}/cmdline", "rb").read() + b" " + open(f"/proc/{p}/environ", "rb").read()
                rows[p] = {"ppid": ppid, "text": text.replace(b"\0", b" ").decode(errors="replace"),
                           "cwd": os.readlink(f"/proc/{p}/cwd")}
            except OSError:
                continue
    return rows
def targets(rows):
    me = str(os.getpid())
    spare, p = set(), me
    while p in rows and p not in spare and p != "0":
        spare.add(p); p = rows[p]["ppid"]
    hits = []
    for p, r in rows.items():
        if p in spare or r["ppid"] == me:      # ancestors, this sweep and its ps/lsof
            continue
        cwd = r["cwd"]
        if scratch in r["text"] or (p not in before and (cwd == top or cwd.startswith(top + "/"))):
            hits.append(p)
    return hits
killed = targets(table())
for sig, wait in ((signal.SIGTERM, 1.0), (signal.SIGKILL, 0.5)):
    hits = targets(table())
    if not hits:
        break
    for p in hits:
        try:
            os.kill(int(p), sig)
        except OSError:
            pass
    time.sleep(wait)
left = targets(table())
print(len(killed), " ".join(left))
PY
)
read -r nkilled survivors <<<"$sweep"
[[ "${nkilled:-0}" != 0 ]] && killed="$nkilled leftover process(es)"

# After the sweep: integrity first; these hold even when Codex also ran out of time or quota.
quota=; quota_in "$work/codex.log" && { quota=1; touch "$marker"; }
[[ "$(dotgit)" != "$(cat "$work/dotgit.before")" ]] && { git_unsafe=1; fallback "codex changed .git"; }
[[ "$(gitcfg)" != "$(cat "$work/cfg.before")" ]] && { git_unsafe=1; fallback "codex changed git config"; }
[[ -n "${survivors:-}" ]] && fallback "codex left processes running"
refs | sort >"$work/refs.after"
refdiff=$(python3 - "$work/refs.before" "$work/refs.after" "$orig_sym" <<'PY'
import sys
def load(f):
    d = {}
    for line in open(f).read().splitlines():
        k, _, v = line.partition(" ")
        d[k] = v or "-"
    return d
a, b, own_branch = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
for r in sorted(set(a) | set(b)):
    old, new = a.get(r, "-"), b.get(r, "-")
    if old == new:
        continue
    own = (r in ("HEAD", "HEAD-symbolic", own_branch, "refs/stash") or r.startswith("refs/worktree/")
           or r.startswith("refs/tags/"))
    print("own" if own else "other", r, old, new)
PY
)
refs_own=$(grep '^own ' <<<"$refdiff" | cut -d' ' -f2-)
refs_other=$(grep '^other ' <<<"$refdiff" | cut -d' ' -f2-)
ignored | sort >"$work/ignored.after"
# New ignored paths are removed on reset; changed ones (a retargeted link) only get the outside check.
new_ignored=$(awk -F'\t' 'NR == FNR { seen[$1]; next } !($1 in seen) { print $1 }' "$work/ignored.before" "$work/ignored.after")
touched_ignored=$(comm -13 "$work/ignored.before" "$work/ignored.after" | cut -f1)
if [[ -n "$refs_own" ]]; then
    [[ "$(g rev-parse HEAD)" != "$commit" ]] && fallback "codex committed"
    fallback "codex changed git refs"
fi
[[ "$(envs)" != "$(cat "$work/envs.before")" ]] && fallback "codex changed a .env file"
while IFS= read -r f; do
    f=${f%/}
    [[ -z "$f" || ! -L "$top/$f" ]] && continue
    r=$(real "$top/$f")
    [[ "$r" == "$top" || "$r" == "$top"/* ]] || fallback "codex touched a path outside the repository"
done <<<"$(changed; printf '%s\n' "$touched_ignored")"
[[ -n "$timed_out" ]] && fallback "timeout after $limit s"
[[ -n "$quota" ]] && fallback "quota"
(( rc == 0 )) || fallback "codex exit $rc"
files=$(changed)
[[ -n "$files" ]] || fallback "codex made no changes"

{
    echo "builder: codex"
    echo "head: $commit"
    echo "refs-other:"; list "$(cut -d' ' -f1 <<<"$refs_other")"
    [[ -n "$killed" ]] && echo "killed: $killed"
    echo "files:"; list "$files"
    echo "ignored-new:"; list "$new_ignored"
    echo "summary:"; [[ -s "$answer" ]] && cat "$answer"
} >"$out"
exit 0
