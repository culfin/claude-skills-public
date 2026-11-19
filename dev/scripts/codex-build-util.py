#!/usr/bin/env python3
"""Path, git-state and process work for codex-build.sh, NUL-safe end to end.

  env-targets --top T --home H [--deny D]...   read-grant targets of the worktree's .env* links
  snapshot    --top T --gitdir G --out F       ignored paths and .env* metadata (never content)
  analyze     --top T --gitdir G --commit C --before F --stamp F --report F --rm-list F --env-rm F
  remove      --top T --list F                 delete NUL-separated paths strictly inside T
  refdiff     BEFORE AFTER OWN_BRANCH          classify changed refs: own, shared, other
  sweep       --top T --scratch S --before F --pgid N --sid N

Git always runs against the recorded git dir and work tree, without system or global config,
hooks or fsmonitor: nothing Codex wrote runs.
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time

HOOK_FILES = {"lefthook.yml", "lefthook.yaml", ".lefthook.yml", ".lefthook.yaml",
              ".pre-commit-config.yaml"}
HOOK_DIRS = {".husky", ".githooks"}
CAP = 50


def git(a, *args):
    env = dict(os.environ, GIT_DIR=a.gitdir, GIT_WORK_TREE=a.top, GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL="/dev/null")
    p = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=", *args],
                       cwd=a.top, env=env, capture_output=True)
    return p.stdout if p.returncode == 0 else None


def nul(data):
    return [x.decode("utf-8", "surrogateescape") for x in (data or b"").split(b"\0") if x]


def show(p):
    """One display line per path: control characters escaped, never a raw newline."""
    return json.dumps(p)[1:-1] if any(c in p for c in "\n\t\r\\\"") else p


def inside(path, top):
    return path.startswith(top.rstrip("/") + "/")


def is_env(name):
    return name == ".env" or name.startswith(".env.")


def walk_envs(top):
    for d, dirs, files in os.walk(top):
        dirs[:] = sorted(x for x in dirs if x not in (".git", "node_modules"))
        for f in sorted(files + [x for x in dirs if os.path.islink(os.path.join(d, x))]):
            if is_env(f):
                yield os.path.relpath(os.path.join(d, f), top)


def env_sig(top, rel):
    p = os.path.join(top, rel)
    st = os.lstat(p)
    return "link " + os.readlink(p) if os.path.islink(p) else f"file {st.st_size} {st.st_mtime_ns}"


def cmd_env_targets(a):
    home = os.path.realpath(a.home)
    out = []
    for rel in walk_envs(a.top):
        p = os.path.join(a.top, rel)
        if not os.path.islink(p):
            continue
        reason = None
        target = os.path.realpath(p)
        if rel.count("/") > 1:
            reason = "deeper than one level"
        elif any(c in target for c in "\n\t"):
            reason = "odd target name"
        elif target == "/" or target == home or inside(home, target):
            reason = "target is / or $HOME or above it"
        elif not os.path.isfile(target):
            reason = "target is not a regular file"
        elif any(target == d or inside(target, d) for d in map(os.path.realpath, a.deny)):
            reason = "target in a denied folder"
        if reason:
            print(f"{show(rel)} ({reason})")
            return 3
        out.append(target)
    sys.stdout.write("".join(t + "\n" for t in out))
    return 0


def ignored(a):
    res = {}
    for p in nul(git(a, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory")):
        full = os.path.join(a.top, p.rstrip("/"))
        res[p] = ("link " + os.readlink(full)) if os.path.islink(full) else (
            "dir" if os.path.isdir(full) else "file")
    return res


def snapshot(a):
    return {"ignored": ignored(a), "envs": {r: env_sig(a.top, r) for r in walk_envs(a.top)}}


def cmd_snapshot(a):
    with open(a.out, "w") as fh:
        json.dump(snapshot(a), fh)
    return 0


def scripts_of(text):
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return "unparsable"
    return data.get("scripts") if isinstance(data, dict) else "unparsable"


def cmd_analyze(a):
    before = json.load(open(a.before))
    after = snapshot(a)
    changed = sorted(set(nul(git(a, "diff", "--no-ext-diff", "--name-only", "-z", a.commit)))
                     | set(nul(git(a, "ls-files", "-z", "--others", "--exclude-standard"))))
    bi, ai = before["ignored"], after["ignored"]
    new_ignored = sorted(p for p in ai if p not in bi)
    touched = sorted(p for p in ai if bi.get(p) != ai[p])
    # Changes inside ignored trees that existed (node_modules/, .venv/, target/): the listing
    # above only names their top; mtime against the stamp finds the files.
    stamp = os.stat(a.stamp).st_mtime_ns
    prefixes = tuple(p if p.endswith("/") else p + "/" for p in new_ignored)
    seen = set(changed) | set(new_ignored)
    newer = []
    for d, dirs, files in os.walk(a.top):
        if d == a.top:
            dirs[:] = [x for x in dirs if x != ".git"]
            files = [x for x in files if x != ".git"]
        for f in files + [x for x in dirs if os.path.islink(os.path.join(d, x))]:
            full = os.path.join(d, f)
            rel = os.path.relpath(full, a.top)
            if rel in seen or rel.startswith(prefixes):
                continue
            try:
                if os.lstat(full).st_mtime_ns > stamp:
                    newer.append(rel)
            except OSError:
                continue
    newer.sort()
    hooks = []
    for p in changed:
        parts = p.split("/")
        if HOOK_DIRS & set(parts[:-1]) or parts[-1] in HOOK_FILES:
            hooks.append(p)
        elif parts[-1] == "package.json":
            old = git(a, "show", f"{a.commit}:{p}")
            try:
                new = open(os.path.join(a.top, p), encoding="utf-8").read()
            except OSError:
                new = None
            if scripts_of(old.decode("utf-8", "replace") if old is not None else "{}") != scripts_of(new):
                hooks.append(p)
    outside = []
    for p in changed + touched + newer:
        full = os.path.join(a.top, p.rstrip("/"))
        if os.path.islink(full):
            r = os.path.realpath(full)
            if r != a.top and not inside(r, a.top):
                outside.append(p)
    benv, aenv = before["envs"], after["envs"]
    new_env_links = [r for r in aenv if r not in benv and os.path.islink(os.path.join(a.top, r))]

    def section(name, items, cap=None):
        lines = [f"{name}:"] + [f"- {show(p)}" for p in (items[:cap] if cap else items)]
        if cap and len(items) > cap:
            lines.append(f"… and {len(items) - cap} more")
        return "\n".join(lines) + "\n"
    with open(a.report, "w") as fh:
        fh.write(section("files", changed) + section("ignored-new", new_ignored)
                 + section("ignored-changed", newer, CAP) + section("hooks-changed", hooks))
    with open(a.rm_list, "wb") as fh:
        fh.write(b"".join(p.encode("utf-8", "surrogateescape") + b"\0" for p in new_ignored))
    with open(a.env_rm, "wb") as fh:
        fh.write(b"".join(p.encode("utf-8", "surrogateescape") + b"\0" for p in new_env_links))
    print(f"files={len(changed)} envs_changed={int(benv != aenv)} outside={int(bool(outside))}")
    return 0


def cmd_remove(a):
    """Delete each path only when it lies strictly inside top and no parent is a symlink;
    a symlink is removed itself, never its target. Prints every refused path."""
    top = os.path.realpath(a.top)
    data = open(a.list, "rb").read()
    for raw in data.split(b"\0"):
        if not raw:
            continue
        p = raw.decode("utf-8", "surrogateescape")
        rel = p.rstrip("/")
        parts = rel.split("/")
        if (not rel or any(c in p for c in "\n\t") or os.path.isabs(rel)
                or any(x in ("..", ".", "") for x in parts)):
            print(f"{show(p)} (unsafe name)")
            continue
        full = os.path.join(top, rel)
        parent = os.path.dirname(full)
        if os.path.realpath(parent) != parent or not (parent == top or inside(parent, top)):
            print(f"{show(p)} (reached through a symlink)")
            continue
        if not inside(full, top):
            print(f"{show(p)} (outside the worktree)")
            continue
        try:
            if os.path.islink(full) or not os.path.isdir(full):
                os.unlink(full)
            else:
                shutil.rmtree(full)
        except FileNotFoundError:
            pass
        except OSError as e:
            print(f"{show(p)} ({e.strerror})")
    return 0


def cmd_refdiff(a):
    def load(f):
        d = {}
        for line in open(f).read().splitlines():
            k, _, v = line.partition(" ")
            d[k] = v or "-"
        return d
    b, c = load(a.before), load(a.after)
    for r in sorted(set(b) | set(c)):
        old, new = b.get(r, "-"), c.get(r, "-")
        if old == new:
            continue
        if r in ("HEAD", "HEAD-symbolic", a.own_branch) or r.startswith("refs/worktree/"):
            kind = "own"
        elif r == "refs/stash" or r.startswith("refs/tags/"):
            kind = "shared"          # shared git dir: reported, never reset
        else:
            kind = "other"
        print(kind, r, old, new)
    return 0


def table():
    rows = {}
    if sys.platform == "darwin":
        ps = subprocess.run(["ps", "-axww", "-E", "-o", "pid=,ppid=,command="], capture_output=True,
                            text=True, errors="replace").stdout
        for line in ps.splitlines():
            parts = line.split(None, 2)
            if len(parts) >= 2:
                rows[parts[0]] = {"ppid": parts[1], "text": parts[2] if len(parts) > 2 else "", "cwd": ""}
        ls = subprocess.run(["lsof", "-nP", "-w", "-a", "-d", "cwd", "-Fpn", "-u", str(os.getuid())],
                            capture_output=True, text=True, errors="replace").stdout
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
    for p, r in rows.items():
        try:
            r["pgid"], r["sid"] = str(os.getpgid(int(p))), str(os.getsid(int(p)))
        except OSError:
            r["pgid"] = r["sid"] = ""
    return rows


def cmd_sweep(a):
    """Processes Codex left: scratch dir in args or env, Codex's process group or (if its own)
    session, new since the run with cwd in the worktree, and their descendants. Ancestors of this
    sweep, the sweep's own ps/lsof and processes that existed before are spared (except by a
    scratch match). TERM, then KILL; up to 3 passes until a scan finds nothing new."""
    before = set(open(a.before).read().split())
    me, my_sid = str(os.getpid()), str(os.getsid(0))

    def targets(rows):
        spare, p = set(), me
        while p in rows and p not in spare and p != "0":
            spare.add(p)
            p = rows[p]["ppid"]
        hits = set()
        for p, r in rows.items():
            if p in spare or r["ppid"] == me:
                continue
            cwd = r["cwd"]
            if (a.scratch in r["text"] or (a.pgid and r["pgid"] == a.pgid)
                    or (a.sid and a.sid != my_sid and r["sid"] == a.sid)
                    or (p not in before and (cwd == a.top or inside(cwd, a.top)))):
                hits.add(p)
        grew = True
        while grew:                   # descendants of a hit
            grew = False
            for p, r in rows.items():
                if p not in hits and p not in spare and r["ppid"] in hits:
                    hits.add(p)
                    grew = True
        return hits

    killed = set()
    for _ in range(3):
        hits = targets(table()) - {"1"}
        if not hits:
            break
        killed |= hits
        for sig, wait in ((signal.SIGTERM, 1.0), (signal.SIGKILL, 0.3)):
            for p in hits:
                try:
                    os.kill(int(p), sig)
                except OSError:
                    pass
            time.sleep(wait)
    left = sorted(targets(table()) - {"1"})
    print(len(killed), " ".join(left))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("env-targets"); s.add_argument("--top", required=True)
    s.add_argument("--home", required=True); s.add_argument("--deny", action="append", default=[])
    for name in ("snapshot", "analyze"):
        s = sub.add_parser(name)
        s.add_argument("--top", required=True); s.add_argument("--gitdir", required=True)
        if name == "snapshot":
            s.add_argument("--out", required=True)
        else:
            for k in ("--commit", "--before", "--stamp", "--report", "--rm-list", "--env-rm"):
                s.add_argument(k, required=True)
    s = sub.add_parser("remove"); s.add_argument("--top", required=True); s.add_argument("--list", required=True)
    s = sub.add_parser("refdiff"); s.add_argument("before"); s.add_argument("after"); s.add_argument("own_branch")
    s = sub.add_parser("sweep")
    for k in ("--top", "--scratch", "--before"):
        s.add_argument(k, required=True)
    s.add_argument("--pgid", default=""); s.add_argument("--sid", default="")
    a = ap.parse_args()
    return {"env-targets": cmd_env_targets, "snapshot": cmd_snapshot, "analyze": cmd_analyze,
            "remove": cmd_remove, "refdiff": cmd_refdiff, "sweep": cmd_sweep}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
