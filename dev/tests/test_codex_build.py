"""codex-build.sh lets Codex build one phase in the phase worktree, or reports a fallback.

A stub stands in for Codex (`DEV_CODEX_BIN`): it records argv and cwd, then runs the actions in
STUB_MODE (comma-separated: edit, commit, quota, ...). For the permission check it emulates the
sandbox from the profile on its command line (most specific path wins), or leaks per STUB_CHECK.
No test talks to the real Codex unless DEV_CODEX_SMOKE=1 (CodexBuildSmoke).
"""
import json
import os
import re
import signal
import subprocess
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SCRIPT = DEV / "scripts" / "codex-build.sh"
UTIL = DEV / "scripts" / "codex-build-util.py"
SMOKE = DEV / "scripts" / "codex-build-smoke.sh"

STUB = r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys, time, tomllib
args = sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 0.0.0-stub")
    sys.exit(0)
prompt = args[-1]
kind = "check" if prompt.startswith("permission-check:") else "build"
root = args[args.index("-C") + 1]
with open(os.environ["STUB_LOG"], "a") as fh:
    fh.write(json.dumps({"kind": kind, "argv": args, "cwd": os.getcwd()}) + "\n")
out = args[args.index("-o") + 1]
fs = next(a.split("=", 1)[1] for a in args if a.startswith("permissions.dev-build.filesystem="))
profile = tomllib.loads("p = " + fs)["p"]
scratch = re.search(r'TMPDIR="([^"]+)"', " ".join(args)).group(1)

def ident(p):
    try:
        st = os.stat(p)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)

def mode_of(path, by_string=False):
    # A real enforcer matches the file the path resolves to, so on a case-insensitive file system
    # ~/.SSH/id is under the ~/.ssh deny; by_string emulates one that compares path strings.
    path = os.path.realpath(path)
    best, mode = "", None
    for k, v in profile.items():
        if not isinstance(v, str):
            continue
        p = os.path.realpath("/tmp") if k == ":slash_tmp" else k
        if p.startswith(":"):
            continue
        if by_string:
            hit = path == p or path.startswith(p.rstrip("/") + "/")
        else:
            want, q, hit = ident(p), path, False
            while want is not None:
                if ident(q) == want:
                    hit = True
                    break
                if os.path.dirname(q) == q:
                    break
                q = os.path.dirname(q)
        if hit and len(p) > len(best):
            best, mode = p, v
    return mode

if kind == "check":
    # Emulates the probe: it logs to its own result file; the reply is never trusted.
    how = os.environ.get("STUB_CHECK", "enforced")
    script = open(re.search(r"bash (/\S+)", prompt).group(1)).read().splitlines()
    with open(os.environ["STUB_LOG"], "a") as fh:
        fh.write(json.dumps({"kind": "probe", "text": "\n".join(script)}) + "\n")
    res = None
    for line in script:
        if how in ("refuse", "fakereply"):
            break
        m = re.match(r'exec >"(.+)" 2>&1$', line)
        if m:
            res = open(m.group(1), "w"); continue
        m = re.match(r"(r|w) (\S+) '(.+)'$", line)
        if m:
            op, label, p = m.groups()
            if op == "r":
                ok = how == "leak" or (how == "leakunlisted" and label == "read-unlisted") \
                     or mode_of(p, by_string=how == "leakcase") in ("read", "write")
                if ok:
                    open(p).read()
            else:
                ok = how in ("leak", "writeout") or mode_of(p) == "write"
                if ok:
                    open(p, "w").write("x\n")
            res.write(f"{label} {'open' if ok else 'blocked'}\n"); continue
        m = re.match(r"echo '(end-\w+)'$", line)
        if m:
            res.write(m.group(1) + "\n")
    if res:
        res.close()
    with open(out, "w") as fh:
        fh.write("read-denied blocked\nread-env open\nwrite-worktree open\nend-ok" if how == "fakereply"
                 else "done")
    sys.exit(0)

actions = os.environ.get("STUB_MODE", "edit").split(",")
def write(name, text):
    p = os.path.join(root, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(text)
def git(*a):
    subprocess.run(["git", "-C", root, *a], check=True, capture_output=True)
for act in actions:
    if act in ("edit", "commit", "quota", "sleep", "fail"):
        write("feature.py", "def feature():\n    return 1\n")
        write("calc.py", "def add(a, b):\n    return a + b\n")
    if act == "commit":
        git("add", "-A"); git("commit", "-qm", "codex")
    if act == "env":
        os.remove(os.path.join(root, ".env"))
        os.symlink("/dev/null", os.path.join(root, ".env"))
        write("feature.py", "x = 1\n")
    if act == "outside":
        os.symlink("/etc", os.path.join(root, "etc-link"))
    if act == "dotgit":
        write(".git", "gitdir: /nonexistent/elsewhere\n")
        write("feature.py", "x = 1\n")
    if act == "hookcfg":
        write("hooks/reference-transaction", "#!/bin/sh\ntouch " + os.environ["STUB_MARK"] + "\n")
        os.chmod(os.path.join(root, "hooks/reference-transaction"), 0o755)
        git("config", "core.hooksPath", os.path.join(root, "hooks"))
    if act == "fsmcfg":
        write("fsm.sh", "#!/bin/sh\ntouch " + os.environ["STUB_MARK"] + "\n")
        os.chmod(os.path.join(root, "fsm.sh"), 0o755)
        git("config", "core.fsmonitor", os.path.join(root, "fsm.sh"))
    if act == "hookdir":
        # A hook written straight into the repository's own hooks dir; runs on ref updates.
        gd = subprocess.run(["git", "-C", root, "rev-parse", "--git-common-dir"], capture_output=True,
                            text=True, check=True).stdout.strip()
        hook = os.path.join(root, gd, "hooks", "reference-transaction")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        open(hook, "w").write("#!/bin/sh\ntouch " + os.environ["STUB_MARK"] + "\n")
        os.chmod(hook, 0o755)
    if act == "branch":
        git("branch", "other-worker")
    if act == "tag":
        git("tag", "codex-tag")
    if act == "detach":
        late = os.path.join(root, "late.txt")
        child = subprocess.Popen([sys.executable, "-c",
            "import time,sys; time.sleep(float(sys.argv[2])); open(sys.argv[1], 'w').write('late')", late,
            os.environ.get("STUB_CHILD_SLEEP", "3")],
            cwd=root, env=dict(os.environ, TMPDIR=scratch), start_new_session=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        open(os.environ["STUB_PIDFILE"], "w").write(str(child.pid))
    if act == "ignored":
        write("build/out.bin", "binary\n")
        write("new.log", "log\n")
    if act == "ignoredlink":
        os.symlink("/etc", os.path.join(root, "x.log"))
    if act == "hooks":
        write(".husky/pre-commit", "#!/bin/sh\ncurl evil\n")
        pj = json.load(open(os.path.join(root, "package.json")))
        pj["scripts"]["prepare"] = "node steal.js"
        write("package.json", json.dumps(pj))
        sub = json.load(open(os.path.join(root, "sub/package.json")))
        sub["version"] = "2.0.0"
        write("sub/package.json", json.dumps(sub))
    if act == "ignoredtree":
        write("node_modules/pkg/index.js", "module.exports = 2\n")
        write("node_modules/pkg/evil.js", "steal()\n")
    if act == "ignoredtreelink":
        os.symlink("/etc", os.path.join(root, "node_modules/pkg/out"))
    if act == "manyignored":
        for i in range(120):
            write(f"node_modules/pkg/f{i}.js", "x\n")
    if act == "newline":
        write("evil\nname.log", "x\n")
    if act == "newenv":
        os.symlink("/etc/hosts", os.path.join(root, ".env.local"))
    if act == "pgchild":
        # Same process group as Codex, but no scratch in its environment and cwd outside.
        late = os.path.join(root, "late.txt")
        env = {k: v for k, v in os.environ.items() if k != "TMPDIR"}
        child = subprocess.Popen([sys.executable, "-c",
            "import time,sys; time.sleep(3); open(sys.argv[1], 'w').write('late')", late],
            cwd="/", env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        open(os.environ["STUB_PIDFILE"], "w").write(str(child.pid))
    if act == "chain":
        # A detached child carrying the scratch dir starts a detached grandchild without it.
        late = os.path.join(root, "late.txt")
        code = ("import os,subprocess,sys,time; env={k:v for k,v in os.environ.items() if k!='TMPDIR'};"
                "g=subprocess.Popen([sys.executable,'-c','import time,sys; time.sleep(3); open(sys.argv[1],\"w\").write(\"late\")',"
                "sys.argv[1]],cwd='/',env=env,start_new_session=True);"
                "open(sys.argv[2],'a').write(' '+str(g.pid)); time.sleep(30)")
        child = subprocess.Popen([sys.executable, "-c", code, late, os.environ["STUB_PIDFILE"]],
            cwd=root, env=dict(os.environ, TMPDIR=scratch), start_new_session=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        open(os.environ["STUB_PIDFILE"], "w").write(str(child.pid))
        time.sleep(1)
    if act == "ignoredback":
        p = os.path.join(root, "node_modules/pkg/other.js")
        st = os.stat(p)
        open(p, "w").write("changed!!\n")
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))         # mtime set back; ctime cannot be
    if act == "envback":
        p = os.path.realpath(os.path.join(root, ".env"))
        st = os.stat(p)
        open(p, "w").write("SECRET=never-printed-43\n")
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        write("feature.py", "x = 1\n")
    if act == "buildlink":
        write("build/sub/keep.txt", "x\n")
        os.symlink("/etc", os.path.join(root, "build/sub/link"))
    if act == "lockdir":
        write("build/locked/x.txt", "x\n")
        os.chmod(os.path.join(root, "build/locked"), 0)
    if act == "sleep":
        time.sleep(float(os.environ.get("STUB_SLEEP", "30")))
    if act == "quota":
        print("ERROR: You've hit your usage limit. Try again later.", file=sys.stderr)
        sys.exit(1)
    if act == "fail":
        print("ERROR: something broke", file=sys.stderr)
        sys.exit(1)
print("tokens used\n12.345")
with open(out, "w") as fh:
    fh.write("Added feature() and fixed add.\nfiles:\nfeature.py\ncalc.py\nopen: none\n")
sys.exit(0)
'''

LEAN = "---\ndefaults:\n  flow: lean\n  builder: codex   # pilot\n---\n# Roadmap\n"


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True).stdout


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class CodexBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.base = base
        self.root = base / "repo"
        self.root.mkdir()
        self.tmpdir = base / "tmpdir"
        self.tmpdir.mkdir()
        self.home = base / "home"             # fake $HOME: credential and toolchain dirs
        for d in (".ssh", ".cargo"):
            (self.home / d).mkdir(parents=True)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        (self.root / "calc.py").write_text("def add(a, b):\n    return a - b\n")
        (self.root / "ROADMAP.md").write_text(LEAN)
        (self.root / ".gitignore").write_text(".env\n.env.*\nbuild/\n*.log\nnode_modules/\n")
        (self.root / "package.json").write_text(json.dumps({"name": "x", "scripts": {"test": "t"}}))
        (self.root / "sub").mkdir()
        (self.root / "sub" / "package.json").write_text(json.dumps({"name": "y", "version": "1.0.0"}))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        self.main = self.root
        # The worktree's .env is a symlink to the main checkout's file, as worktree setups make it.
        self.secret = self.root / ".env.real"         # main checkout's file, ignored
        self.secret.write_text("SECRET=never-printed-42\n")
        (self.root / ".env").symlink_to(self.secret)
        (self.root / "keep.log").write_text("existed before\n")
        (self.root / "node_modules" / "pkg").mkdir(parents=True)
        (self.root / "node_modules" / "pkg" / "index.js").write_text("module.exports = 1\n")
        (self.root / "node_modules" / "pkg" / "other.js").write_text("untouched\n")
        old = time.time() - 60
        for f in ("keep.log", "node_modules/pkg/index.js", "node_modules/pkg/other.js"):
            os.utime(self.root / f, (old, old))
        (base / "bin").mkdir()
        self.stub = base / "bin" / "codex-stub"
        self.stub.write_text(STUB)
        self.stub.chmod(0o755)
        self.log = base / "stub.log"
        self.mark = base / "hook-ran"
        self.pidfile = base / "child.pid"
        self.brief = base / "brief.md"
        self.brief.write_text("Phase 4.2: add feature(); criteria C1 feature() returns 1.\n")
        self.out = base / "build.md"

    def tearDown(self):
        for d, dirs, _ in os.walk(self.base):
            for x in dirs:
                p = os.path.join(d, x)
                if not os.path.islink(p) and not os.access(p, os.R_OK | os.X_OK):
                    os.chmod(p, 0o755)
        if self.pidfile.exists():
            for pid in self.pidfile.read_text().split():
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.tmp.cleanup()

    def linked_worktree(self):
        wt = self.root.parent / "main-wt"
        git(self.root, "worktree", "add", "-q", "-b", "phase-x", str(wt), self.head)
        (wt / ".env").symlink_to(self.secret)
        self.root = wt
        return wt

    def run_build(self, mode="edit", extra_args=(), **env_extra):
        env = dict(os.environ, DEV_CODEX_BIN=str(self.stub), STUB_LOG=str(self.log), STUB_MODE=mode,
                   TMPDIR=str(self.tmpdir), HOME=str(self.home), STUB_MARK=str(self.mark),
                   STUB_PIDFILE=str(self.pidfile), DEV_CODEX_PREFIXES=str(self.base / "noprefix"))
        env.update(env_extra)
        p = subprocess.run(["bash", str(SCRIPT), "--brief", str(self.brief), "--head", self.head,
                            "--out", str(self.out), *extra_args],
                           cwd=self.root, capture_output=True, text=True, env=env, timeout=90)
        return p.returncode, p.stdout, p.stderr

    def calls(self, kind="build"):
        if not self.log.exists():
            return []
        return [c for c in map(json.loads, self.log.read_text().splitlines()) if c["kind"] == kind]

    def profile(self, call):
        fs = next(a.split("=", 1)[1] for a in call["argv"]
                  if a.startswith("permissions.dev-build.filesystem="))
        return tomllib.loads("p = " + fs)["p"]

    def status(self):
        return git(self.root, "status", "--porcelain", "-uall")

    def assert_no_secret(self, *texts):
        for t in texts:
            self.assertNotIn("never-printed-42", t)

    # Exit 0

    def test_success_leaves_uncommitted_changes(self):
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(out, "")
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), self.head)
        self.assertIn(" M calc.py", self.status())
        self.assertIn("?? feature.py", self.status())
        report = self.out.read_text()
        self.assertIn("builder: codex", report)
        self.assertIn("files:\n", report)
        self.assertIn("- calc.py", report)
        self.assertIn("- feature.py", report)
        self.assertIn("Added feature()", report)
        self.assertIn("tokens used: 12.345", err)
        self.assert_no_secret(out, err, report)
        self.assertEqual((self.root / ".env").resolve(), self.secret)
        self.assertNotIn("killed:", report)             # the sweep spares the caller's processes

    def test_runs_from_linked_worktree(self):
        wt = self.linked_worktree()
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("?? feature.py", self.status())
        self.assertEqual(self.calls()[0]["argv"][self.calls()[0]["argv"].index("-C") + 1], str(wt))

    # A: permission profile, never the legacy sandbox

    def test_permission_profile_replaces_sandbox(self):
        wt = self.linked_worktree()
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        (call,) = self.calls()
        argv = call["argv"]
        joined = " ".join(argv)
        self.assertNotIn("--sandbox", argv)
        self.assertNotIn("danger", joined)
        for needle in ('default_permissions="dev-build"', "permissions.dev-build.network.enabled=false",
                       'approval_policy="never"', "--ignore-user-config", "--ignore-rules"):
            self.assertIn(needle, joined)
        p = self.profile(call)
        common = str((self.main / ".git").resolve())
        self.assertEqual(p[str(wt)], "write")
        self.assertEqual(p[":slash_tmp"], "deny")
        self.assertEqual(p[":minimal"], "read")
        self.assertEqual(p[str(self.main)], "deny")                    # main checkout's tree
        self.assertEqual(p[common], "read")
        self.assertEqual(p[str(self.secret)], "read")                  # .env symlink target
        self.assertEqual(p[str(self.home / ".ssh")], "deny")
        self.assertEqual(p[str(self.home / ".cargo")], "read")         # exists
        self.assertNotIn(str(self.home / ".rustup"), p)                # does not
        scratch = [k for k, v in p.items() if v == "write" and "dev-codex-build-" in k]
        self.assertEqual(len(scratch), 1)
        self.assertIn(f'TMPDIR="{scratch[0]}"', joined)
        keys = list(p)
        denies = [i for i, k in enumerate(keys) if p[k] == "deny"]
        others = [i for i, k in enumerate(keys) if p[k] != "deny" and k != ":minimal"]
        self.assertLess(max(denies), min(others), "denies come first")

    def test_main_checkout_tree_not_denied_when_it_is_the_worktree(self):
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.profile(self.calls()[0])[str(self.root)], "write")

    def test_profile_not_enforced_is_fallback(self):
        for how in ("leak", "writeout"):
            with self.subTest(how=how):
                for f in self.tmpdir.glob("dev-codex-build-ok-*"):
                    f.unlink()
                rc, out, err = self.run_build("edit", STUB_CHECK=how)
                self.assertEqual((rc, out), (3, "fallback: permission profile not enforced\n"), err)
                self.assertEqual(self.status(), "")
        self.assertEqual(self.calls(), [])
        self.assertFalse(list(Path("/tmp").glob("dev-codex-build-probe-*")))

    def test_permission_check_inconclusive_is_fallback(self):
        rc, out, err = self.run_build("edit", STUB_CHECK="refuse")
        self.assertEqual((rc, out), (3, "fallback: permission check inconclusive\n"), err)
        self.assertEqual(self.calls(), [])

    def test_permission_check_runs_once_per_binary(self):
        self.assertEqual(self.run_build("edit")[0], 0)
        git(self.root, "checkout", "-q", "calc.py")
        (self.root / "feature.py").unlink()
        self.assertEqual(self.run_build("edit")[0], 0)
        self.assertEqual(len(self.calls("check")), 1)
        self.assertEqual(len(self.calls("build")), 2)

    def test_codex_binary_above_home_is_fallback(self):
        self.home = self.base / "bin" / "home"
        (self.home / ".ssh").mkdir(parents=True)
        rc, out, err = self.run_build("edit")
        self.assertEqual((rc, out), (3, "fallback: unsafe-codex-location\n"), err)
        self.assertEqual(self.calls("check") + self.calls(), [])

    def test_project_codex_config_is_fallback(self):
        (self.root / ".codex").mkdir()
        (self.root / ".codex" / "config.toml").write_text('sandbox_mode = "danger-full-access"\n')
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "codex config")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        rc, out, err = self.run_build("edit")
        self.assertEqual((rc, out), (3, "fallback: project .codex config in the worktree\n"), err)
        self.assertEqual(self.calls(), [])

    # Exit 3

    def test_quota_error_is_fallback_exit_3(self):
        rc, out, err = self.run_build("quota")
        self.assertEqual((rc, out), (3, "fallback: quota\n"), err)
        self.assertEqual(self.status(), "")
        report = self.out.read_text()
        self.assertIn("fallback: quota", report)
        self.assertIn(f"partial: reset to {self.head}", report)
        self.assertIn("- feature.py", report)
        self.assertEqual((self.root / ".env").resolve(), self.secret)
        rc, out, _ = self.run_build("edit")
        self.assertEqual((rc, out), (3, "fallback: quota\n"))
        self.assertEqual(len(self.calls()), 1)

    def test_keep_partial_leaves_partial_changes_for_the_claude_implementer(self):
        rc, out, err = self.run_build("quota", ["--keep-partial"])
        self.assertEqual((rc, out), (3, "fallback: quota\n"), err)
        self.assertIn("?? feature.py", self.status())
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), self.head)
        report = self.out.read_text()
        self.assertIn("partial: kept, uncommitted", report)
        self.assertIn("- feature.py", report)

    def test_codex_commit_is_detected_and_fallback(self):
        rc, out, err = self.run_build("commit")
        self.assertEqual((rc, out), (3, "fallback: codex committed\n"), err)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), self.head)
        self.assertEqual(self.status(), "")
        report = self.out.read_text()
        self.assertIn("- feature.py", report)
        self.assertIn("HEAD", report.split("refs-changed:", 1)[1])

    def test_codex_commit_with_keep_partial_is_undone_but_changes_stay(self):
        rc, out, err = self.run_build("commit", ["--keep-partial"])
        self.assertEqual((rc, out), (3, "fallback: codex committed\n"), err)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), self.head)
        self.assertIn("feature.py", self.status())

    def test_timeout_is_fallback(self):
        rc, out, err = self.run_build("sleep", DEV_CODEX_TIMEOUT_SEC="2", STUB_SLEEP="30")
        self.assertEqual((rc, out), (3, "fallback: timeout after 2 s\n"), err)
        self.assertEqual(self.status(), "")
        self.assertIn("- feature.py", self.out.read_text())

    def test_crash_is_fallback(self):
        rc, out, err = self.run_build("fail")
        self.assertEqual((rc, out), (3, "fallback: codex exit 1\n"), err)
        self.assertFalse(list(self.tmpdir.glob("*.off")))

    def test_no_changes_is_fallback(self):
        rc, out, err = self.run_build("nothing")
        self.assertEqual((rc, out), (3, "fallback: codex made no changes\n"), err)
        self.assertIn("partial: none", self.out.read_text())

    def test_env_change_is_fallback(self):
        rc, out, err = self.run_build("env")
        self.assertEqual((rc, out), (3, "fallback: codex changed a .env file\n"), err)
        self.assert_no_secret(out, err, self.out.read_text())

    def test_path_outside_repo_is_fallback(self):
        rc, out, err = self.run_build("outside")
        self.assertEqual((rc, out), (3, "fallback: codex touched a path outside the repository\n"), err)
        self.assertFalse(os.path.lexists(self.root / "etc-link"))

    # B: git hardening

    def test_dotgit_change_is_fallback_without_git(self):
        self.linked_worktree()
        rc, out, err = self.run_build("dotgit")
        self.assertEqual((rc, out), (3, "fallback: codex changed .git\n"), err)
        report = self.out.read_text()
        self.assertIn("partial: not touched", report)
        self.assertTrue((self.root / "feature.py").exists())       # no git ran, nothing reset

    def test_hook_or_fsmonitor_config_is_fallback_and_never_runs(self):
        for act in ("hookcfg", "fsmcfg"):
            with self.subTest(act=act):
                rc, out, err = self.run_build(f"edit,{act}")
                self.assertEqual((rc, out), (3, "fallback: codex changed git config\n"), err)
                self.assertFalse(self.mark.exists())
                self.assertIn("partial: not touched", self.out.read_text())
                git(self.root, "config", "--unset", "core.hooksPath" if act == "hookcfg" else "core.fsmonitor")
                git(self.root, "reset", "-q", "--hard", self.head)
                git(self.root, "clean", "-fdq")

    def test_hook_written_into_git_dir_never_runs(self):
        rc, out, err = self.run_build("commit,hookdir")
        self.assertEqual((rc, out), (3, "fallback: codex committed\n"), err)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), self.head)
        self.assertFalse(self.mark.exists())

    # C: refs scope

    def test_other_branch_change_is_a_note_not_fallback(self):
        rc, out, err = self.run_build("edit,branch")
        self.assertEqual(rc, 0, out + err)
        report = self.out.read_text()
        self.assertIn("refs/heads/other-worker", report.split("refs-other:", 1)[1])

    def test_tag_is_fallback_but_shared_refs_are_never_touched(self):
        # Tags and refs/stash live in the shared git dir: another worker may have made them.
        rc, out, err = self.run_build("edit,tag")
        self.assertEqual((rc, out), (3, "fallback: codex changed git refs\n"), err)
        self.assertIn("refs/tags/codex-tag", self.out.read_text().split("refs-changed:", 1)[1])
        self.assertEqual(git(self.root, "tag"), "codex-tag\n")
        self.assertEqual(self.status(), "")
        self.assertNotIn("update-ref -d", SCRIPT.read_text())

    # D: process containment

    def test_detached_grandchild_is_killed(self):
        rc, out, err = self.run_build("edit,detach")
        self.assertEqual(rc, 0, out + err)
        pid = int(self.pidfile.read_text())
        self.assertFalse(alive(pid))
        self.assertIn("killed:", self.out.read_text())
        time.sleep(3.5)
        self.assertFalse((self.root / "late.txt").exists())

    # E: ignored paths

    def test_new_ignored_paths_listed_on_success(self):
        rc, out, err = self.run_build("edit,ignored")
        self.assertEqual(rc, 0, out + err)
        new = self.out.read_text().split("ignored-new:", 1)[1].split("summary:", 1)[0]
        self.assertIn("- build/", new)
        self.assertIn("- new.log", new)
        self.assertNotIn("keep.log", new)
        self.assertNotIn(".env", new)

    def test_new_ignored_paths_removed_on_reset(self):
        rc, out, err = self.run_build("ignored,quota")
        self.assertEqual((rc, out), (3, "fallback: quota\n"), err)
        self.assertFalse((self.root / "build").exists())
        self.assertFalse((self.root / "new.log").exists())
        self.assertTrue((self.root / "keep.log").exists())
        self.assertEqual((self.root / ".env").resolve(), self.secret)

    def test_new_ignored_symlink_outside_is_fallback(self):
        rc, out, err = self.run_build("edit,ignoredlink")
        self.assertEqual((rc, out), (3, "fallback: codex touched a path outside the repository\n"), err)
        self.assertFalse(os.path.lexists(self.root / "x.log"))

    # Round 2

    def test_hook_paths_listed(self):
        rc, out, err = self.run_build("edit,hooks")
        self.assertEqual(rc, 0, out + err)
        hooks = self.out.read_text().split("hooks-changed:", 1)[1].split("summary:", 1)[0]
        self.assertIn("- .husky/pre-commit", hooks)
        self.assertIn("- package.json", hooks)
        self.assertNotIn("sub/package.json", hooks)          # only its version changed

    def test_changes_inside_existing_ignored_tree_listed(self):
        rc, out, err = self.run_build("edit,ignoredtree")
        self.assertEqual(rc, 0, out + err)
        sec = self.out.read_text().split("ignored-changed:", 1)[1].split("hooks-changed:", 1)[0]
        self.assertIn("- node_modules/pkg/index.js", sec)
        self.assertIn("- node_modules/pkg/evil.js", sec)
        for f in ("other.js", "keep.log", "feature.py", "calc.py", ".env"):
            self.assertNotIn(f, sec)

    def test_ignored_changed_is_capped(self):
        rc, out, err = self.run_build("edit,manyignored")
        self.assertEqual(rc, 0, out + err)
        sec = self.out.read_text().split("ignored-changed:", 1)[1].split("hooks-changed:", 1)[0]
        self.assertEqual(sec.count("\n- "), 50)
        self.assertIn("and 70 more", sec)

    def test_symlink_outside_inside_ignored_tree_is_fallback(self):
        rc, out, err = self.run_build("edit,ignoredtreelink")
        self.assertEqual((rc, out), (3, "fallback: codex touched a path outside the repository\n"), err)

    def test_reply_without_probe_log_is_inconclusive(self):
        rc, out, err = self.run_build("edit", STUB_CHECK="fakereply")
        self.assertEqual((rc, out), (3, "fallback: permission check inconclusive\n"), err)
        self.assertEqual(self.calls(), [])

    def test_unlisted_read_must_be_denied(self):
        rc, out, err = self.run_build("edit", STUB_CHECK="leakunlisted")
        self.assertEqual((rc, out), (3, "fallback: permission profile not enforced\n"), err)
        (probe,) = self.calls("probe")
        self.assertIn("r read-unlisted '", probe["text"])
        self.assertIn('exec >"', probe["text"])

    def test_newline_name_is_not_removed_and_reported(self):
        rc, out, err = self.run_build("newline,quota")
        self.assertEqual((rc, out), (3, "fallback: quota\n"), err)
        self.assertIn("not-removed:", self.out.read_text())
        self.assertTrue((self.root / "keep.log").exists())

    def test_remove_never_follows_symlinks(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "x").write_text("keep me\n")
        (outside / "y").write_text("keep me too\n")
        (self.root / "linkdir").symlink_to(outside)
        (self.root / "lnk").symlink_to(outside / "y")
        (self.root / "real").mkdir()
        (self.root / "real" / "f").write_text("go\n")
        lst = self.base / "rm.list"
        lst.write_bytes(b"\0".join([b"linkdir/x", b"lnk", b"a\nb", b"../outside/x", b"real/", b".", b""]))
        p = subprocess.run(["python3", str(UTIL), "remove", "--top", str(self.root), "--list", str(lst)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((outside / "x").exists())
        self.assertTrue((outside / "y").exists())
        self.assertFalse(os.path.lexists(self.root / "lnk"))         # the link itself goes
        self.assertTrue((self.root / "linkdir").is_symlink())
        self.assertFalse((self.root / "real").exists())
        self.assertTrue(self.root.exists())
        refused = p.stdout
        for name in ("linkdir/x", "a\\nb", "../outside/x"):
            self.assertIn(name, refused)

    def test_env_link_targets_are_validated(self):
        (self.home / ".ssh" / "id").write_text("key\n")
        (self.base / "envdir").mkdir()
        (self.base / "other.env").write_text("X=1\n")
        mixed = self.home / ".SSH" / "id"              # case-insensitive APFS: same file as .ssh/id
        cases = {"dir": (".env.dir", self.root / "sub"),
                 "credential": (".env.key", self.home / ".ssh" / "id"),
                 "credential-mixed-case": (".env.key", mixed),
                 "outside-main": (".env.other", self.base / "other.env"),
                 "deep": ("a/b/.env", self.secret)}
        for name, (link, target) in cases.items():
            with self.subTest(case=name):
                (self.root / link).parent.mkdir(parents=True, exist_ok=True)
                (self.root / link).symlink_to(target)
                rc, out, err = self.run_build("edit")
                self.assertEqual(rc, 3, out + err)
                self.assertTrue(out.startswith("fallback: unsafe .env link"), out)
                if name.startswith("credential") and mixed.exists():
                    self.assertIn("denied folder", out)
                self.assertEqual(self.calls(), [])
                (self.root / link).unlink()

    def test_tracked_env_link_is_refused(self):
        (self.root / "apps").mkdir()
        (self.root / "apps" / ".env").symlink_to(self.secret)
        git(self.root, "add", "-f", "apps/.env")
        git(self.root, "commit", "-qm", "tracked link")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 3, out + err)
        self.assertIn("tracked", out)
        self.assertEqual(self.calls(), [])

    def test_survivors_leave_the_worktree_untouched(self):
        rc, out, err = self.run_build("edit,detach", DEV_CODEX_SWEEP_DRYRUN="1", STUB_CHILD_SLEEP="30")
        self.assertEqual((rc, out), (3, "fallback: codex left processes running\n"), err)
        self.assertIn("partial: not touched", self.out.read_text())
        self.assertTrue((self.root / "feature.py").exists())

    def test_ctime_catches_mtime_set_back(self):
        rc, out, err = self.run_build("edit,ignoredback")
        self.assertEqual(rc, 0, out + err)
        sec = self.out.read_text().split("ignored-changed:", 1)[1].split("hooks-changed:", 1)[0]
        self.assertIn("- node_modules/pkg/other.js", sec)
        git(self.root, "checkout", "-q", "calc.py")
        (self.root / "feature.py").unlink()
        rc, out, err = self.run_build("envback")
        self.assertEqual((rc, out), (3, "fallback: codex changed a .env file\n"), err)

    def test_symlink_deep_in_new_ignored_dir_is_fallback(self):
        rc, out, err = self.run_build("edit,buildlink")
        self.assertEqual((rc, out), (3, "fallback: codex touched a path outside the repository\n"), err)
        self.assertFalse((self.root / "build").exists())

    def test_env_link_one_level_down_is_granted(self):
        (self.root / "apps").mkdir()
        (self.root / "apps" / ".env").symlink_to(self.secret)
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.profile(self.calls()[0])[str(self.secret)], "read")

    def test_new_env_link_removed_even_with_keep_partial(self):
        rc, out, err = self.run_build("edit,newenv", ["--keep-partial"])
        self.assertEqual((rc, out), (3, "fallback: codex changed a .env file\n"), err)
        self.assertFalse(os.path.lexists(self.root / ".env.local"))
        self.assertTrue((self.root / "feature.py").exists())
        self.assertEqual((self.root / ".env").resolve(), self.secret)

    def test_check_cache_is_private(self):
        stale = self.tmpdir / "dev-codex-build-ok-planted"
        stale.write_text("")
        self.assertEqual(self.run_build("edit")[0], 0)
        cache = self.home / ".cache" / "dev-codex-build"
        self.assertEqual(cache.stat().st_mode & 0o777, 0o700)
        self.assertTrue(list(cache.glob("ok-*")))
        self.assertEqual(len(self.calls("check")), 1)
        git(self.root, "checkout", "-q", "calc.py"); (self.root / "feature.py").unlink()
        cache.chmod(0o777)                                    # untrusted now: check again
        self.assertEqual(self.run_build("edit")[0], 0)
        self.assertEqual(len(self.calls("check")), 2)
        cache.chmod(0o700)

    def test_process_group_member_is_killed(self):
        rc, out, err = self.run_build("edit,pgchild")
        self.assertEqual(rc, 0, out + err)
        self.assertFalse(alive(int(self.pidfile.read_text())))
        time.sleep(3.5)
        self.assertFalse((self.root / "late.txt").exists())

    def test_descendants_of_matches_are_killed(self):
        rc, out, err = self.run_build("edit,chain")
        self.assertEqual(rc, 0, out + err)
        pids = [int(p) for p in self.pidfile.read_text().split()]
        self.assertEqual(len(pids), 2)
        for pid in pids:
            self.assertFalse(alive(pid), pid)
        time.sleep(3.5)
        self.assertFalse((self.root / "late.txt").exists())

    # Task 3b: deferred minors

    def test_ls_files_failure_fails_closed(self):
        # A failing `git ls-files` gave an empty tracked set: a tracked .env link passed as untracked.
        p = subprocess.run(["python3", str(UTIL), "env-targets", "--top", str(self.root),
                            "--gitdir", str(self.base / "no-such-gitdir"), "--main", str(self.main),
                            "--home", str(self.home)], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertIn("git ls-files failed", p.stdout)
        self.assertNotIn(str(self.secret), p.stdout)

    def test_survivors_still_set_quota_marker_and_report_refs(self):
        rc, out, err = self.run_build("edit,tag,detach,quota", DEV_CODEX_SWEEP_DRYRUN="1",
                                      STUB_CHILD_SLEEP="30")
        self.assertEqual((rc, out), (3, "fallback: codex left processes running\n"), err)
        self.assertTrue(list(self.tmpdir.glob("dev-codex-*.off")))
        report = self.out.read_text()
        self.assertIn("refs/tags/codex-tag", report.split("refs-changed:", 1)[1])
        self.assertIn("partial: not touched", report)

    def test_unreadable_dir_before_run_fails_closed(self):
        locked = self.root / "build" / "locked"
        locked.mkdir(parents=True)
        (locked / ".env").symlink_to("/etc/hosts")
        locked.chmod(0)
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 3, out + err)
        self.assertTrue(out.startswith("fallback: worktree check failed: unreadable"), out)
        self.assertEqual(self.calls(), [])

    def test_unreadable_dir_after_run_fails_closed(self):
        rc, out, err = self.run_build("edit,lockdir")
        self.assertEqual((rc, out), (3, "fallback: analysis failed\n"), err)
        self.assertIn("partial: not touched", self.out.read_text())

    def test_case_variant_of_denied_folder_is_probed(self):
        # APFS is case-insensitive: an enforcer that compares path strings lets .SSH past a .ssh deny.
        rc, out, err = self.run_build("edit", STUB_CHECK="leakcase")
        self.assertEqual((rc, out), (3, "fallback: permission profile not enforced\n"), err)
        (probe,) = self.calls("probe")
        self.assertIn("r read-denied-case '", probe["text"])
        self.assertEqual(self.calls(), [])

    def test_case_variant_probe_passes_with_enforcing_codex(self):
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        check = self.calls("check")[0]
        deny = [k for k, v in self.profile(check).items() if v == "deny" and k.endswith("/.ssh")]
        self.assertTrue(any("dev-codex-build-check-" in k for k in deny), deny)

    def test_hard_linked_env_target_is_refused(self):
        os.link(self.secret, self.base / "outside-link")       # the file also lives outside main
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 3, out + err)
        self.assertTrue(out.startswith("fallback: unsafe .env link"), out)
        self.assertIn("hard link", out)
        self.assertEqual(self.calls(), [])

    # Exit 2

    def test_refuses_outside_lean_project(self):
        for roadmap in ("---\ndefaults:\n  flow: lean\n  builder: claude\n---\n",
                        "---\ndefaults:\n  flow: lean\n---\n# builder: codex\n", None):
            with self.subTest(roadmap=roadmap):
                if roadmap is None:
                    git(self.root, "rm", "-q", "ROADMAP.md")
                else:
                    (self.root / "ROADMAP.md").write_text(roadmap)
                git(self.root, "commit", "-qam", "roadmap")
                self.head = git(self.root, "rev-parse", "HEAD").strip()
                rc, out, err = self.run_build("edit")
                self.assertEqual(rc, 2, out + err)
                self.assertIn("defaults.builder: codex", err)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.calls("check"), [])

    def monorepo(self, content=LEAN):
        git(self.root, "rm", "-q", "ROADMAP.md")
        (self.root / "apps" / "web").mkdir(parents=True)
        (self.root / "apps" / "web" / "ROADMAP.md").write_text(content)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "monorepo")
        self.head = git(self.root, "rev-parse", "HEAD").strip()

    def test_roadmap_option_finds_subdirectory_roadmap(self):
        self.monorepo()
        rc, out, err = self.run_build("edit", ("--roadmap", "apps/web/ROADMAP.md"))
        self.assertEqual(rc, 0, out + err)

    def test_monorepo_without_roadmap_option_refuses(self):
        self.monorepo()
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.calls(), [])

    def test_roadmap_option_refuses_paths_outside_worktree(self):
        self.monorepo()
        outside = self.base / "x"
        outside.write_text(LEAN)
        for path in ("../x", "apps/../ROADMAP.md", str(outside), "apps/web/../../../x"):
            with self.subTest(path=path):
                rc, out, err = self.run_build("edit", ("--roadmap", path))
                self.assertEqual(rc, 2, out + err)
        (self.root / "link.md").symlink_to(outside)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "link")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        rc, out, err = self.run_build("edit", ("--roadmap", "link.md"))
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.calls(), [])

    def test_roadmap_option_without_builder_codex_refuses(self):
        self.monorepo("---\ndefaults:\n  flow: lean\n  builder: claude\n---\n")
        rc, out, err = self.run_build("edit", ("--roadmap", "apps/web/ROADMAP.md"))
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.calls(), [])

    def test_roadmap_option_untracked_or_ignored_file_refuses(self):
        self.monorepo("---\ndefaults:\n  builder: claude\n---\n")
        (self.root / "apps" / "x").mkdir()
        (self.root / "apps" / "x" / "ROADMAP.md").write_text(LEAN)
        (self.root / ".git" / "info" / "exclude").write_text("apps/x/\n")
        rc, out, err = self.run_build("edit", ("--roadmap", "apps/x/ROADMAP.md"))
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.calls(), [])

    def test_roadmap_option_other_basename_refuses(self):
        self.monorepo()
        (self.root / "apps" / "web" / "PLAN.md").write_text(LEAN)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "plan")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        rc, out, err = self.run_build("edit", ("--roadmap", "apps/web/PLAN.md"))
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.calls(), [])

    def test_roadmap_option_reads_head_not_working_tree(self):
        self.monorepo("---\ndefaults:\n  builder: claude\n---\n")
        (self.root / "apps" / "web" / "ROADMAP.md").write_text(LEAN)
        # a dirty tree is refused anyway; mark the edit as assume-unchanged so only the HEAD read can catch it
        git(self.root, "update-index", "--assume-unchanged", "apps/web/ROADMAP.md")
        rc, out, err = self.run_build("edit", ("--roadmap", "apps/web/ROADMAP.md"))
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.calls(), [])

    def test_roadmap_option_under_dot_git_refuses(self):
        self.monorepo()
        rc, out, err = self.run_build("edit", ("--roadmap", ".git/ROADMAP.md"))
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.calls(), [])

    def test_refuses_dirty_worktree_and_wrong_head(self):
        (self.root / "calc.py").write_text("user work in progress\n")
        rc, _, err = self.run_build("edit")
        self.assertEqual(rc, 2, err)
        self.assertEqual((self.root / "calc.py").read_text(), "user work in progress\n")
        git(self.root, "checkout", "-q", "calc.py")
        self.head = "0" * 40
        rc, _, err = self.run_build("edit")
        self.assertEqual(rc, 2, err)
        self.assertEqual(self.calls(), [])

    def test_refuses_out_inside_worktree(self):
        self.out = self.root / "build.md"
        rc, _, err = self.run_build("edit")
        self.assertEqual(rc, 2, err)
        self.assertEqual(self.calls(), [])

    def test_script_is_executable(self):
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        self.assertTrue(os.access(SMOKE, os.X_OK))


class CodexBuildSmoke(unittest.TestCase):
    """The real Codex in a throwaway layout; costs quota, so only with DEV_CODEX_SMOKE=1."""

    def test_smoke_usage_error_runs_no_codex(self):
        p = subprocess.run(["bash", str(SMOKE), "--only", "bogus"], capture_output=True, text=True,
                           env=dict(os.environ, DEV_CODEX_BIN="/nonexistent/codex"), timeout=30)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)

    @unittest.skipUnless(os.environ.get("DEV_CODEX_SMOKE") == "1", "real Codex: set DEV_CODEX_SMOKE=1")
    def test_real_codex_smoke(self):
        p = subprocess.run(["bash", str(SMOKE)], capture_output=True, text=True, timeout=1500)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("smoke: PASS", p.stdout)


if __name__ == "__main__":
    unittest.main()
