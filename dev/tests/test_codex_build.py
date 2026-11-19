"""codex-build.sh lets Codex build one phase in the phase worktree, or reports a fallback.

A stub stands in for Codex (`DEV_CODEX_BIN`): it records argv and cwd, then runs the actions in
STUB_MODE (comma-separated: edit, commit, quota, ...). For the permission check it emulates the
sandbox from the profile on its command line (most specific path wins), or leaks per STUB_CHECK.
No test talks to the real Codex.
"""
import json
import os
import signal
import subprocess
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SCRIPT = DEV / "scripts" / "codex-build.sh"

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

def mode_of(path):
    path = os.path.realpath(path)
    best, mode = "", None
    for k, v in profile.items():
        if not isinstance(v, str):
            continue
        p = os.path.realpath("/tmp") if k == ":slash_tmp" else k
        if p.startswith(":"):
            continue
        if (path == p or path.startswith(p.rstrip("/") + "/")) and len(p) > len(best):
            best, mode = p, v
    return mode

if kind == "check":
    how = os.environ.get("STUB_CHECK", "enforced")
    lines = []
    script = open(re.search(r"bash (/\S+)", prompt).group(1)).read().splitlines()
    for line in script:
        if how == "refuse":
            break
        m = re.match(r"cat (\S+) 2>&1$", line)
        if m:
            p = m.group(1)
            if how == "leak" or mode_of(p) in ("read", "write"):
                lines.append(open(p).read().strip())
            else:
                lines.append(f"cat: {p}: Operation not permitted")
            continue
        m = re.match(r"echo (\S+) > (\S+) 2>&1$", line)
        if m:
            text, p = m.groups()
            if how in ("leak", "writeout") or mode_of(p) == "write":
                open(p, "w").write(text + "\n")
            else:
                lines.append(f"{p}: Operation not permitted")
    with open(out, "w") as fh:
        fh.write("\n".join(lines) if lines else "I will not do that.")
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
            "import time,sys; time.sleep(3); open(sys.argv[1], 'w').write('late')", late],
            cwd=root, env=dict(os.environ, TMPDIR=scratch), start_new_session=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        open(os.environ["STUB_PIDFILE"], "w").write(str(child.pid))
    if act == "ignored":
        write("build/out.bin", "binary\n")
        write("new.log", "log\n")
    if act == "ignoredlink":
        os.symlink("/etc", os.path.join(root, "x.log"))
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
        (self.root / ".gitignore").write_text(".env\n.env.*\nbuild/\n*.log\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        self.main = self.root
        # The worktree's .env is a symlink to the main checkout's file, as worktree setups make it.
        self.secret = base / "main.env"
        self.secret.write_text("SECRET=never-printed-42\n")
        (self.root / ".env").symlink_to(self.secret)
        (self.root / "keep.log").write_text("existed before\n")
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
        if self.pidfile.exists():
            try:
                os.kill(int(self.pidfile.read_text()), signal.SIGKILL)
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

    def test_tag_is_fallback_and_removed(self):
        rc, out, err = self.run_build("edit,tag")
        self.assertEqual((rc, out), (3, "fallback: codex changed git refs\n"), err)
        self.assertIn("refs/tags/codex-tag", self.out.read_text().split("refs-changed:", 1)[1])
        self.assertEqual(git(self.root, "tag"), "")

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


if __name__ == "__main__":
    unittest.main()
