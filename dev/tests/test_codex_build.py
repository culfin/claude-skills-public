"""codex-build.sh lets Codex build one phase in the phase worktree, or reports a fallback.

A stub stands in for Codex (`DEV_CODEX_BIN`): it records argv and cwd, then edits, commits, sleeps
or fails according to STUB_MODE. No test talks to the real Codex.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SCRIPT = DEV / "scripts" / "codex-build.sh"

STUB = r'''#!/usr/bin/env python3
import json, os, subprocess, sys, time
args = sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 0.0.0-stub")
    sys.exit(0)
mode = os.environ.get("STUB_MODE", "edit")
root = args[args.index("-C") + 1] if "-C" in args else os.getcwd()
with open(os.environ["STUB_LOG"], "a") as fh:
    fh.write(json.dumps({"argv": args, "cwd": os.getcwd()}) + "\n")
out = args[args.index("-o") + 1]
def write(name, text):
    with open(os.path.join(root, name), "w") as fh:
        fh.write(text)
if mode in ("edit", "commit", "quota", "sleep", "fail"):
    write("feature.py", "def feature():\n    return 1\n")
    write("calc.py", "def add(a, b):\n    return a + b\n")
if mode == "commit":
    subprocess.run(["git", "-C", root, "add", "-A"], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", "codex"], check=True)
if mode == "env":
    os.remove(os.path.join(root, ".env"))
    os.symlink("/dev/null", os.path.join(root, ".env"))
    write("feature.py", "x = 1\n")
if mode == "outside":
    os.symlink("/etc", os.path.join(root, "etc-link"))
if mode == "sleep":
    time.sleep(float(os.environ.get("STUB_SLEEP", "30")))
if mode == "quota":
    print("ERROR: You've hit your usage limit. Try again later.", file=sys.stderr)
    sys.exit(1)
if mode == "fail":
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


class CodexBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.root = base / "repo"
        self.root.mkdir()
        self.tmpdir = base / "tmpdir"
        self.tmpdir.mkdir()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        (self.root / "calc.py").write_text("def add(a, b):\n    return a - b\n")
        (self.root / "ROADMAP.md").write_text(LEAN)
        (self.root / ".gitignore").write_text(".env\n.env.*\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        # The worktree's .env is a symlink to the main checkout's file, as worktree setups make it.
        self.secret = base / "main.env"
        self.secret.write_text("SECRET=never-printed-42\n")
        (self.root / ".env").symlink_to(self.secret)
        self.stub = base / "codex-stub"
        self.stub.write_text(STUB)
        self.stub.chmod(0o755)
        self.log = base / "stub.log"
        self.brief = base / "brief.md"
        self.brief.write_text("Phase 4.2: add feature(); criteria C1 feature() returns 1.\n")
        self.out = base / "build.md"

    def tearDown(self):
        self.tmp.cleanup()

    def run_build(self, mode="edit", extra_args=(), **env_extra):
        env = dict(os.environ, DEV_CODEX_BIN=str(self.stub), STUB_LOG=str(self.log), STUB_MODE=mode,
                   TMPDIR=str(self.tmpdir))
        env.update(env_extra)
        p = subprocess.run(["bash", str(SCRIPT), "--brief", str(self.brief), "--head", self.head,
                            "--out", str(self.out), *extra_args],
                           cwd=self.root, capture_output=True, text=True, env=env, timeout=60)
        return p.returncode, p.stdout, p.stderr

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

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

    def test_codex_gets_workspace_write_sandbox_on_the_worktree_only(self):
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        (call,) = self.calls()
        argv = call["argv"]
        self.assertEqual(argv[0], "exec")
        self.assertEqual(argv[argv.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(argv[argv.index("-C") + 1], str(self.root))
        joined = " ".join(argv)
        for needle in ("sandbox_workspace_write.network_access=false",
                       "sandbox_workspace_write.exclude_slash_tmp=true",
                       "sandbox_workspace_write.exclude_tmpdir_env_var=true",
                       'approval_policy="never"', "--ignore-user-config", "--ignore-rules"):
            self.assertIn(needle, joined)
        self.assertNotIn("danger", joined)
        prompt = argv[-1]
        self.assertIn("Phase 4.2: add feature()", prompt)
        for rule in ("never run `git commit`", "`git push`", "files:", "open:"):
            self.assertIn(rule, prompt)
        self.assertNotIn("never-printed-42", prompt)

    def test_runs_from_linked_worktree(self):
        wt = self.root.parent / "phase-wt"
        git(self.root, "worktree", "add", "-q", "--detach", str(wt), self.head)
        self.root = wt
        rc, out, err = self.run_build("edit")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("?? feature.py", self.status())
        self.assertEqual(self.calls()[0]["argv"][self.calls()[0]["argv"].index("-C") + 1], str(wt))

    # Exit 3

    def test_quota_error_is_fallback_exit_3(self):
        rc, out, err = self.run_build("quota")
        self.assertEqual((rc, out), (3, "fallback: quota\n"), err)
        # Partial changes are reset, and the report says what Codex had left.
        self.assertEqual(self.status(), "")
        report = self.out.read_text()
        self.assertIn("fallback: quota", report)
        self.assertIn(f"partial: reset to {self.head}", report)
        self.assertIn("- feature.py", report)
        self.assertEqual((self.root / ".env").resolve(), self.secret)   # ignored files stay
        # The marker sends the next call straight to the fallback, without calling Codex.
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
        self.assertIn("- feature.py", self.out.read_text())

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
