"""codex-review.sh runs one gate review through Codex in a clean checkout, or reports a fallback.

A stub stands in for Codex (`DEV_CODEX_BIN`): it records argv, cwd and what the cwd contains, and
answers according to STUB_MODE. No test talks to the real Codex.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SCRIPT = DEV / "scripts" / "codex-review.sh"

VALID = {
    "checked": "sweep: 3 probes, 2 candidates, 1 confirmed; lenses: logic, errors",
    "files_read": 2,
    "blocked_reason": "",
    "findings": [
        {"severity": "critical", "file": "calc.py", "line": 2, "quote": "return a - b",
         "failing_input": "add(1, 2) returns -1, expected 3", "finding": "add subtracts",
         "fix": "use a + b"},
        {"severity": "note", "file": "calc.py", "line": 5, "quote": "return part / whole * 100",
         "failing_input": "pct(1, 0) raises ZeroDivisionError", "finding": "no guard for 0",
         "fix": "return 0 for whole == 0"},
    ],
}

STUB = r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys, time
args = sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 0.0.0-stub")
    sys.exit(0)
prompt = args[-1]
kind = "check" if "deny-check" in prompt else "review"
mode = os.environ.get("STUB_CHECK_MODE" if kind == "check" else "STUB_MODE", "valid")
cwd = os.getcwd()
rec = {"kind": kind, "argv": args, "cwd": cwd, "env_in_cwd": os.path.exists(os.path.join(cwd, ".env")),
       "files": sorted(os.listdir(cwd)), "pid": os.getpid(),
       "head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
       "prompt": args[-1],
       "analyzers": sorted(os.listdir(os.path.join(cwd, "..", "analyzers")))
                    if os.path.isdir(os.path.join(cwd, "..", "analyzers")) else []}
with open(os.environ["STUB_LOG"], "a") as fh:
    fh.write(json.dumps(rec) + "\n")
out = args[args.index("-o") + 1] if "-o" in args else None
if mode == "sleep":
    time.sleep(float(os.environ.get("STUB_SLEEP", "30")))
if mode == "quota":
    print("ERROR: You've hit your usage limit. Try again later.", file=sys.stderr)
    sys.exit(1)
if mode == "fail":
    print("ERROR: something broke", file=sys.stderr)
    sys.exit(1)
if mode == "fail-ratelimit-text":
    print("src/limits.py:3: RATE_LIMIT = 429  # rate limit and quota for the API")
    print("ERROR: stream disconnected")
    sys.exit(1)
if kind == "check":
    # Emulates the sandbox: enforced -> only the control file is readable.
    lines = []
    script = open(re.search(r"bash (/\S+)", prompt).group(1)).read()
    for path in re.findall(r"(/\S+)", script.split("cat ", 1)[1].splitlines()[0]):
        if mode == "refuse":
            break
        if mode == "leak" or os.path.basename(path) == "control.txt":
            lines.append(open(path).read().strip())
        else:
            lines.append(f"cat: {path}: Operation not permitted")
    answer = "\n".join(lines) if lines else "I will not do that."
else:
    answer = os.environ.get("STUB_ANSWER", "")
with open(out, "w") as fh:
    fh.write(answer)
sys.exit(0)
'''


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True).stdout


class CodexReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.root = base / "repo"
        self.root.mkdir()
        self.tmpdir = base / "tmpdir"       # $TMPDIR of the script: markers and checkouts
        self.tmpdir.mkdir()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        (self.root / "calc.py").write_text("def add(a, b):\n    return a - b\n")
        git(self.root, "add", "calc.py")
        git(self.root, "commit", "-qm", "base")
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        (self.root / ".env").write_text("SECRET=working-dir-only\n")   # untracked, like Orca setup
        self.stub = base / "codex-stub"
        self.stub.write_text(STUB)
        self.stub.chmod(0o755)
        self.log = base / "stub.log"
        self.prompt = base / "prompt.md"
        self.prompt.write_text("Review the diff with the diff-review analyzer.\n")
        self.input = base / "phase.diff"
        self.input.write_text("--- a/calc.py\n+++ b/calc.py\n")
        self.out = base / "review.md"

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, mode="valid", answer=None, **extra):
        env = dict(os.environ, DEV_CODEX_BIN=str(self.stub), STUB_LOG=str(self.log), STUB_MODE=mode,
                   STUB_ANSWER=json.dumps(VALID) if answer is None else answer, TMPDIR=str(self.tmpdir))
        env.update(extra)
        return env

    def args(self, out=None, role="diff"):
        return ["bash", str(SCRIPT), "--role", role, "--prompt", str(self.prompt), "--input",
                str(self.input), "--head", self.head, "--out", str(out or self.out)]

    def run_review(self, mode="valid", answer=None, out=None, role="diff", **extra):
        p = subprocess.run(self.args(out, role), cwd=self.root, capture_output=True, text=True,
                           env=self.env(mode, answer, **extra), timeout=60)
        return p.returncode, p.stdout, p.stderr

    def all_calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def calls(self):
        return [c for c in self.all_calls() if c["kind"] == "review"]

    def checks(self):
        return [c for c in self.all_calls() if c["kind"] == "check"]

    def assert_clean(self):
        worktrees = [l for l in git(self.root, "worktree", "list", "--porcelain").splitlines()
                     if l.startswith("worktree ")]
        self.assertEqual(len(worktrees), 1, worktrees)
        self.assertEqual([p.name for p in self.tmpdir.iterdir() if p.is_dir()], [])

    # Review Focus 2: Codex sees the clean checkout, never the working directory with its .env
    def test_clean_checkout_has_no_env(self):
        rc, out, err = self.run_review()
        self.assertEqual(rc, 0, out + err)
        call, = self.calls()
        self.assertFalse(call["env_in_cwd"])
        self.assertIn("calc.py", call["files"])
        self.assertNotEqual(Path(call["cwd"]).resolve(), self.root)
        self.assertEqual(call["head"], self.head)
        self.assert_clean()

    def test_deny_read_rule_passed(self):
        for role in ("diff", "security", "fix", "similar"):
            rc, out, err = self.run_review(role=role)
            self.assertEqual(rc, 0, out + err)
        calls = self.calls()
        self.assertEqual(len(calls), 4)
        home = os.environ["HOME"]
        for call in calls + self.checks():
            argv = call["argv"]
            self.assertEqual(argv[0], "exec")
            for flag in ("--ephemeral", "--skip-git-repo-check", "--ignore-user-config", "-o"):
                self.assertIn(flag, argv)
            overrides = [argv[i + 1] for i, a in enumerate(argv) if a == "-c"]
            self.assertIn('default_permissions="dev-review"', overrides)
            perms = [o for o in overrides if o.startswith("permissions.dev-review.filesystem=")]
            self.assertEqual(len(perms), 1, overrides)
            perm = perms[0]
            # Codex reads an unparsable value as a plain string and ignores the whole profile
            tomllib.loads("x = " + perm.split("=", 1)[1])
            self.assertIn('"**/.env"="deny"', perm)
            self.assertIn('"**/.env.*"="deny"', perm)
            self.assertIn('":minimal"="read"', perm)
            self.assertNotIn('":root"', perm)                 # no blanket read of the disk
            self.assertIn('":slash_tmp"="deny"', perm)
            self.assertNotIn('":tmpdir"', perm)     # not readable anyway; a deny there makes the model refuse its own temp dir
            self.assertIn(f'"{self.root}"="deny"', perm)      # the working directory itself
            for sub in (".ssh", ".aws", ".config", ".codex", ".gnupg", "Library/Keychains"):
                self.assertIn(f'"{home}/{sub}"="deny"', perm)
            self.assertNotIn("write", perm)
            self.assertIn('shell_environment_policy.set={GIT_CONFIG_GLOBAL="/dev/null"}', overrides)
            # --sandbox would switch Codex back to the legacy sandbox and drop the deny rule
            self.assertFalse({"-s", "--sandbox"} & set(argv), argv)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
        for call in calls:
            self.assertIn("--output-schema", call["argv"])
            perm = [a for a in call["argv"] if a.startswith("permissions.dev-review.filesystem=")][0]
            self.assertIn(f'"{Path(call["cwd"]).parent}"="read"', perm)   # its own temp dir only

    def test_codex_install_dir_readable(self):
        # Codex re-executes its own binary inside the sandbox: its directory must be readable.
        rc, out, err = self.run_review()
        self.assertEqual(rc, 0, out + err)
        perm = [a for a in self.calls()[0]["argv"] if a.startswith("permissions.dev-review.filesystem=")][0]
        self.assertIn(f'"{self.stub.parent}"="read"', perm)

    def test_unsafe_codex_location_is_fallback(self):
        home = self.root.parent / "home" / "user"
        home.mkdir(parents=True)
        for where in (home, home.parent, self.root, self.root / "tools" / "bin"):
            with self.subTest(str(where)):
                where.mkdir(parents=True, exist_ok=True)
                binary = where / "codex-stub"
                binary.write_text(STUB)
                binary.chmod(0o755)
                rc, out, err = self.run_review(DEV_CODEX_BIN=str(binary), HOME=str(home))
                self.assertEqual((rc, out.strip()), (3, "fallback: unsafe-codex-location"), err)
                binary.unlink()
        # A symlink from a safe place to a binary in an unsafe place counts by its target.
        target = self.root / "codex-real"
        target.write_text(STUB)
        target.chmod(0o755)
        link = self.root.parent / "safe-bin" / "codex"
        link.parent.mkdir()
        link.symlink_to(target)
        rc, out, err = self.run_review(DEV_CODEX_BIN=str(link), HOME=str(home))
        self.assertEqual((rc, out.strip()), (3, "fallback: unsafe-codex-location"), err)
        self.assertEqual(self.all_calls(), [])

    def test_tool_prefixes_granted_by_subdirectory_only(self):
        prefix = self.root.parent / "brew"
        for sub in ("bin", "Cellar", "etc", "var", "share"):
            (prefix / sub).mkdir(parents=True)
        rc, out, err = self.run_review(DEV_CODEX_PREFIXES=str(prefix))
        self.assertEqual(rc, 0, out + err)
        perm = [a for a in self.calls()[0]["argv"] if a.startswith("permissions.dev-review.filesystem=")][0]
        table = tomllib.loads("x = " + perm.split("=", 1)[1])["x"]
        for sub in ("bin", "Cellar", "share"):
            self.assertEqual(table.get(str(prefix / sub)), "read", sub)
        for path in (prefix, prefix / "etc", prefix / "var", prefix / "lib"):
            self.assertNotIn(str(path), table)          # service configs and data stay closed

    def test_skill_dir_not_granted_analyzers_copied(self):
        dev = DEV.resolve()
        self.prompt.write_text(f"Read {dev}/analyzers/CONTRACT.md and {dev}/analyzers/diff-review.md first.\n"
                               f"Also {dev}/gate.md.\n")
        rc, out, err = self.run_review()
        self.assertEqual(rc, 0, out + err)
        call, = self.calls()
        perm = [a for a in call["argv"] if a.startswith("permissions.dev-review.filesystem=")][0]
        table = tomllib.loads("x = " + perm.split("=", 1)[1])["x"]
        self.assertNotIn(str(dev), table)
        work = Path(call["cwd"]).parent
        self.assertIn(f"{work}/analyzers/CONTRACT.md", call["prompt"])
        self.assertIn(f"{work}/analyzers/diff-review.md", call["prompt"])
        self.assertNotIn(f"{dev}/analyzers/", call["prompt"])
        self.assertEqual(call["analyzers"], ["CONTRACT.md", "diff-review.md"])   # only what is named

    # Capability check: the deny rule must demonstrably work with this binary before any review
    def test_deny_check_fails_closed(self):
        for mode, reason in (("leak", "fallback: deny-rule-not-enforced"),
                             ("refuse", "fallback: deny-check inconclusive"),
                             ("fail", "fallback: deny-check failed (codex exit 1)")):
            with self.subTest(mode):
                rc, out, err = self.run_review(STUB_CHECK_MODE=mode)
                self.assertEqual((rc, out.strip()), (3, reason), err)
        rc, out, err = self.run_review(STUB_CHECK_MODE="sleep", DEV_CODEX_TIMEOUT_SEC="2")
        self.assertEqual((rc, out.strip()), (3, "fallback: deny-check timeout after 2 s"), err)
        self.assertEqual(self.calls(), [])          # no review ever ran
        self.assert_clean()

    def test_deny_check_cached_per_binary_version(self):
        for _ in range(3):
            rc, out, err = self.run_review()
            self.assertEqual(rc, 0, out + err)
        self.assertEqual((len(self.checks()), len(self.calls())), (1, 3))
        check = self.checks()[0]
        self.assertNotIn("--output-schema", check["argv"])
        self.assertNotIn(".env", check["files"])      # the check probes from its own dir
        self.assert_clean()

    def test_finding_outside_checkout_is_fallback(self):
        for path in ("/etc/passwd", "../other-repo/secret.py", str(self.root / "calc.py")):
            with self.subTest(path):
                bad = dict(VALID, findings=[dict(VALID["findings"][0], file=path)])
                rc, out, err = self.run_review(answer=json.dumps(bad))
                self.assertEqual(rc, 3, out + err)
                self.assertTrue(out.startswith("fallback: finding outside checkout"), out)
                self.assertFalse(self.out.exists())

    def test_runs_from_linked_worktree(self):
        linked = self.root.parent / "linked"
        git(self.root, "worktree", "add", "-q", "--detach", str(linked), self.head)
        (linked / ".env").write_text("SECRET=linked\n")
        p = subprocess.run(self.args(), cwd=linked, capture_output=True, text=True, env=self.env(),
                           timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        call, = self.calls()
        self.assertEqual(call["head"], self.head)
        self.assertFalse(call["env_in_cwd"])
        perm = [a for a in call["argv"] if a.startswith("permissions.dev-review.filesystem=")][0]
        tomllib.loads("x = " + perm.split("=", 1)[1])
        self.assertIn(f'"{linked}"="deny"', perm)
        self.assertIn(f'"{self.root}"="deny"', perm)    # the shared repository too

    # Review Focus 1: exit 0 without having read anything is a fallback, not "no findings"
    def test_exit0_but_unverified_is_fallback(self):
        cases = {
            "timed out": dict(VALID, findings=[], checked="tool attempts timed out; nothing checked"),
            "commands timed out": dict(VALID, findings=[], checked="all shell commands timed out"),
            "timed out reading": dict(VALID, findings=[], checked="timed out reading calc.py"),
            "files_read": dict(VALID, findings=[], files_read=0),
            "blocked": dict(VALID, findings=[], blocked_reason="could not open the diff file"),
        }
        for name, answer in cases.items():
            with self.subTest(name):
                rc, out, err = self.run_review(answer=json.dumps(answer))
                self.assertEqual(rc, 3, out + err)
                self.assertTrue(out.startswith("fallback: "), out)
                self.assertEqual(len(out.strip().splitlines()), 1, out)
                self.assertFalse(self.out.exists())
        for name, answer in {"plain text": "tool attempts timed out. Result: no findings",
                             "empty": "", "missing field": json.dumps({"checked": "x"})}.items():
            with self.subTest(name):
                rc, out, err = self.run_review(answer=answer)
                self.assertEqual(rc, 3, out + err)
                self.assertTrue(out.startswith("fallback: "), out)
        self.assert_clean()

    def test_timeout_is_fallback(self):
        start = time.monotonic()
        rc, out, err = self.run_review(mode="sleep", DEV_CODEX_TIMEOUT_SEC="2")
        self.assertLess(time.monotonic() - start, 20)
        self.assertEqual(rc, 3, out + err)
        self.assertEqual(out.strip(), "fallback: timeout after 2 s")
        pid = self.calls()[0]["pid"]
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)                 # the Codex process does not outlive the script
        self.assert_clean()

    # Review Focus 4: a quota error short-circuits every later call for an hour
    def test_quota_sets_marker_and_short_circuits(self):
        rc, out, _ = self.run_review(mode="quota")
        self.assertEqual((rc, out.strip()), (3, "fallback: quota"))
        markers = list(self.tmpdir.glob("dev-codex-*.off"))
        self.assertEqual(len(markers), 1)
        rc, out, _ = self.run_review(mode="valid")
        self.assertEqual((rc, out.strip()), (3, "fallback: quota"))
        self.assertEqual(len(self.calls()), 1)          # second call never reached Codex
        old = time.time() - 2 * 3600
        os.utime(markers[0], (old, old))                # marker older than 1 h no longer counts
        rc, out, err = self.run_review(mode="valid")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(len(self.calls()), 2)

    def test_quota_words_in_tool_output_set_no_marker(self):
        # Codex echoes tool output into its log; only its own ERROR line may set the marker.
        rc, out, _ = self.run_review(mode="fail-ratelimit-text")
        self.assertEqual((rc, out.strip()), (3, "fallback: codex exit 1"))
        self.assertEqual(list(self.tmpdir.glob("dev-codex-*.off")), [])

    # Review Focus 3: parallel reviews use their own checkout and output file
    def test_parallel_calls_use_separate_checkouts(self):
        outs = [self.out.with_name(f"review-{i}.md") for i in range(3)]
        procs = [subprocess.Popen(self.args(o), cwd=self.root, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True,
                                  env=self.env("sleep", STUB_SLEEP="1")) for o in outs]
        results = [p.communicate(timeout=60) for p in procs]
        self.assertEqual([p.returncode for p in procs], [0, 0, 0], results)
        cwds = {c["cwd"] for c in self.calls()}
        self.assertEqual(len(cwds), 3)
        for o in outs:
            self.assertIn("reviewer: codex", o.read_text())
        self.assert_clean()

    def test_checkout_removed_on_error(self):
        rc, out, _ = self.run_review(mode="fail")
        self.assertEqual(rc, 3)
        self.assertTrue(out.startswith("fallback: codex exit 1"), out)
        self.assert_clean()
        # interrupted from outside (gate aborted): checkout and Codex process are gone too
        p = subprocess.Popen(self.args(), cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, env=self.env("sleep"))
        for _ in range(100):
            if self.calls()[1:]:
                break
            time.sleep(0.1)
        p.send_signal(signal.SIGTERM)
        p.communicate(timeout=30)
        with self.assertRaises(ProcessLookupError):
            os.kill(self.calls()[1]["pid"], 0)
        self.assert_clean()

    def test_valid_result_exit0_with_reviewer_line(self):
        rc, out, err = self.run_review()
        self.assertEqual(rc, 0, out + err)
        text = self.out.read_text()
        lines = text.splitlines()
        self.assertIn("reviewer: codex", lines)
        self.assertIn("Result: 1 critical, 1 notes", lines)
        self.assertIn("calc.py:2", text)
        self.assertIn("return a - b", text)
        self.assertIn("add(1, 2) returns -1, expected 3", text)
        rc, out, err = self.run_review(answer=json.dumps(dict(VALID, findings=[])))
        self.assertEqual(rc, 0, out + err)
        self.assertIn("Result: no findings", self.out.read_text().splitlines())
        for checked in ("probes: timeout handling, retries; lenses: logic, timeout",
                        "could not run the test suite (no node_modules); read calc.py"):
            with self.subTest(checked):
                rc, out, err = self.run_review(answer=json.dumps(dict(VALID, checked=checked)))
                self.assertEqual(rc, 0, out + err)

    def test_absolute_path_inside_checkout_is_made_relative(self):
        # The stub cannot know the checkout path in advance; codex-result.py is called directly.
        result = self.root.parent / "answer.json"
        checkout = self.root.parent / "checkout"
        finding = dict(VALID["findings"][0], file=str(checkout / "calc.py"))
        result.write_text(json.dumps(dict(VALID, findings=[finding])))
        p = subprocess.run([sys.executable, str(DEV / "scripts" / "codex-result.py"), "check", "--schema",
                            str(DEV / "schemas" / "review-findings.json"), "--result", str(result),
                            "--role", "diff", "--checkout", str(checkout), "--out", str(self.out)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("| calc.py:2 |", self.out.read_text())

    def test_usage_errors_exit2(self):
        rc, _, _ = self.run_review(role="task")
        self.assertEqual(rc, 2)
        p = subprocess.run(["bash", str(SCRIPT), "--role", "diff"], cwd=self.root, capture_output=True,
                           text=True, env=self.env())
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        p = subprocess.run(self.args()[:-6] + ["--head", "0" * 40, "--out", str(self.out),
                                               "--input", str(self.input)],
                           cwd=self.root, capture_output=True, text=True, env=self.env())
        self.assertEqual(p.returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_every_input_file_reaches_codex(self):
        # Review fix round 1 (I-1): a repeated --input used to replace the earlier one, so Codex
        # reviewed the spec without the diff and could still answer with a valid "no findings".
        spec = self.input.parent / "sub"
        spec.mkdir()
        spec = spec / "phase.diff"                  # same basename as the diff: both must survive
        spec.write_text("C1: add returns the sum\n")
        p = subprocess.run(self.args() + ["--input", str(spec)], cwd=self.root, capture_output=True,
                           text=True, env=self.env(), timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        prompt = self.calls()[-1]["prompt"]
        named = [l.split(": ", 1)[1] for l in prompt.splitlines() if l.startswith("Input file")]
        self.assertEqual(len(set(named)), 2, prompt)

    def test_missing_codex_is_fallback(self):
        rc, out, _ = self.run_review(DEV_CODEX_BIN=str(self.root / "no-such-codex"))
        self.assertEqual(rc, 3)
        self.assertTrue(out.startswith("fallback: codex not found"), out)
        self.assert_clean()


class SchemaTests(unittest.TestCase):
    """The schema Codex gets must be valid for structured output: every object closed and complete."""

    def test_schema_requires_evidence_fields(self):
        schema = json.loads((DEV / "schemas" / "review-findings.json").read_text())

        def walk(node):
            if node.get("type") == "object":
                self.assertFalse(node.get("additionalProperties", True))
                self.assertEqual(sorted(node["required"]), sorted(node["properties"]))
                for child in node["properties"].values():
                    walk(child)
            if node.get("type") == "array":
                walk(node["items"])
        walk(schema)
        self.assertIn("files_read", schema["required"])
        finding = schema["properties"]["findings"]["items"]
        for field in ("file", "line", "quote", "failing_input", "severity"):
            self.assertIn(field, finding["required"])


if __name__ == "__main__":
    unittest.main()
