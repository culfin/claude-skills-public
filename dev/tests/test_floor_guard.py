"""floor-guard.py reports ways a change lowers the quality floor to get green."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "floor-guard.py"


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


class FloorGuardTests(unittest.TestCase):
    def setUp(self):
        self.fresh()

    def fresh(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")

    def put(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit_base(self, **files):
        for rel, text in files.items():
            self.put(rel.replace("__", "/"), text)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.base = git(self.root, "rev-parse", "HEAD").strip()

    def run_guard(self, base=None):
        out = subprocess.run([sys.executable, str(SCRIPT), "--base", base or self.base, "--root", str(self.root)],
                             capture_output=True, text=True)
        return out.returncode, out.stdout.splitlines()

    def kinds(self, lines):
        return [l.split(": ", 3)[2] for l in lines]

    def check_kind(self, kind, line, path="src/a.js", neutral="x = 1\n", severity="critical"):
        """The line triggers when added, and does not when it was already there at base."""
        self.fresh()
        self.commit_base(**{path.replace("/", "__"): neutral + line + "\n"})
        self.assertEqual(self.run_guard(), (0, []))
        self.put(path, neutral + line + "\n" + line + "\n")
        rc, out = self.run_guard()
        self.assertEqual(rc, 1 if severity == "critical" else 0)
        self.assertEqual(self.kinds(out), [kind])
        self.assertTrue(out[0].startswith(f"{path}:3: {severity}: {kind}: "), out[0])

    def test_skipped_test(self):
        for line in ["it.skip('a', f)", "describe.skip('a', f)", "xit('a', f)", "xdescribe('a', f)"]:
            with self.subTest(line=line):
                self.check_kind("skipped-test", line, path="src/a.test.js")
        for line in ["@pytest.mark.skip", "@unittest.skip('x')"]:
            with self.subTest(line=line):
                self.check_kind("skipped-test", line, path="tests/test_a.py")
        self.check_kind("skipped-test", "#[ignore]", path="src/lib.rs")
        self.check_kind("skipped-test", "t.Skip(\"x\")", path="a_test.go")
        self.check_kind("skipped-test", "test.skip('a', f)", path="src/b.spec.ts")

    def test_type_suppression(self):
        self.check_kind("type-suppression", severity="note", line="// @ts-ignore", path="src/a.ts")
        self.check_kind("type-suppression", severity="note", line="x = y  # type: ignore", path="a.py")
        self.check_kind("type-suppression", severity="note", line="// @ts-nocheck", path="src/a.ts")

    def test_ts_expect_error_needs_comment_text(self):
        self.commit_base(**{"a.ts": "x\n"})
        self.put("a.ts", "x\n// @ts-expect-error legacy API returns any\ny\n")
        self.assertEqual(self.run_guard(), (0, []))
        self.put("a.ts", "x\n// @ts-expect-error\ny\n")
        rc, out = self.run_guard()
        self.assertEqual((rc, self.kinds(out)), (0, ["type-suppression"]))

    def test_lint_suppression(self):
        self.check_kind("lint-suppression", severity="note", line="// eslint-disable-next-line no-x", path="src/a.js")
        self.check_kind("lint-suppression", severity="note", line="import x  # noqa", path="a.py")
        self.check_kind("lint-suppression", severity="note", line="#[allow(dead_code)]", path="src/lib.rs")
        self.check_kind("lint-suppression", severity="note", line="x() // nolint", path="a.go")
        self.check_kind("lint-suppression", severity="note", line="@SuppressWarnings(\"unchecked\")", path="A.java")

    def test_ci_bypass(self):
        self.check_kind("ci-bypass", "        continue-on-error: true", path=".github/workflows/ci.yml")
        self.check_kind("ci-bypass", "      - run: pnpm test || true", path=".github/workflows/ci.yml")
        self.check_kind("ci-bypass", "git commit --no-verify", path="scripts/x.sh")

    def test_or_true_outside_workflows_is_not_ci_bypass(self):
        self.commit_base(**{"a.sh": "x\n"})
        self.put("a.sh", "x\nrm f || true\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_clean_diff_exits_0(self):
        self.commit_base(**{"a.py": "x = 1\n"})
        self.put("a.py", "x = 2\ny = 3\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_removed_assertion(self):
        self.commit_base(**{"t_test.py": "assert a\nassert b\nx = 1\n", "app.py": "assert a\nassert b\n"})
        self.put("t_test.py", "assert a\nx = 1\n")
        rc, out = self.run_guard()
        self.assertEqual((rc, self.kinds(out)), (1, ["removed-assertion"]))

    def test_removed_assertion_only_in_test_files(self):
        self.commit_base(**{"app.py": "assert a\nassert b\n"})
        self.put("app.py", "assert a\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_replaced_assertion_is_not_removed(self):
        self.commit_base(**{"a.test.js": "expect(a).toBe(1)\n"})
        self.put("a.test.js", "expect(a).toBe(2)\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_lowered_threshold_detected_raised_not(self):
        self.commit_base(**{"cfg.toml": "fail_under = 90\nnote = 5\n"})
        self.put("cfg.toml", "fail_under = 80\nnote = 5\n")
        rc, out = self.run_guard()
        self.assertEqual((rc, self.kinds(out)), (1, ["lowered-threshold"]))
        self.put("cfg.toml", "fail_under = 95\nnote = 5\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_max_warnings_raised_is_reported(self):
        self.commit_base(**{"package.json": '{"lint": "eslint . --max-warnings 0"}\n'})
        self.put("package.json", '{"lint": "eslint . --max-warnings 50"}\n')
        rc, out = self.run_guard()
        self.assertEqual((rc, self.kinds(out)), (1, ["lowered-threshold"]))

    def test_allow_file_suppresses_with_reason(self):
        self.commit_base(**{"a.ts": "x\n"})
        self.put("a.ts", "x\n// @ts-ignore\n")
        self.put(".floor-guard-allow", "a.ts type-suppression # vendor typing bug, issue 12\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_allow_without_reason_reported(self):
        self.commit_base(**{"a.ts": "x\n"})
        self.put("a.ts", "x\n// @ts-ignore\n")
        self.put(".floor-guard-allow", "a.ts type-suppression\n")
        rc, out = self.run_guard()
        self.assertEqual(rc, 1)
        self.assertIn("allow-without-reason", self.kinds(out))
        self.assertIn("type-suppression", self.kinds(out))

    def test_untracked_file_scanned(self):
        self.commit_base(**{"a.py": "x\n"})
        self.put("new_test.py", "import pytest\n@pytest.mark.skip\ndef test_a(): pass\n")
        rc, out = self.run_guard()
        self.assertEqual(rc, 1)
        self.assertTrue(out[0].startswith("new_test.py:2: critical: skipped-test: "), out[0])

    def test_bad_base_exits_2(self):
        self.commit_base(**{"a.py": "x\n"})
        rc, out = self.run_guard(base="does-not-exist")
        self.assertEqual((rc, out), (2, []))
        err = subprocess.run([sys.executable, str(SCRIPT), "--base", "nope", "--root", str(self.root)],
                             capture_output=True, text=True).stderr
        self.assertIn("unknown base ref", err)

    def test_notes_alone_exit_0_but_print(self):
        self.commit_base(**{"a.py": "x\n"})
        self.put("a.py", "x\nimport y  # noqa: F401\n")
        rc, out = self.run_guard()
        self.assertEqual((rc, self.kinds(out)), (0, ["lint-suppression"]))
        self.assertIn(": note: ", out[0])

    def test_generic_skip_only_in_test_paths(self):
        self.commit_base(**{"a.py": "x\n", "latest.py": "x\n"})
        self.put("a.py", "x\ncur = db.cursor.skip(10)\n")
        self.put("latest.py", "x\nit.skip(3)\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_markers_flagged_outside_test_paths(self):
        self.commit_base(**{"src/lib.rs": "x\n"})
        self.put("src/lib.rs", "x\n#[ignore]\n")
        self.assertEqual(self.run_guard()[0], 1)

    def test_version_raise_not_lowered(self):
        self.commit_base(**{"cfg.json": '{"minimum_version": "1.9"}\n'})
        self.put("cfg.json", '{"minimum_version": "1.10"}\n')
        self.assertEqual(self.run_guard(), (0, []))
        self.put("cfg.json", '{"minimum_version": "1.8"}\n')
        self.assertEqual(self.run_guard()[0], 1)

    def test_unrelated_lines_not_paired_for_threshold(self):
        self.commit_base(**{"cfg.json": '{"version": "1.9"}\n'})
        self.put("cfg.json", '{"version": "1.10", "coverage": 5}\n')
        self.assertEqual(self.run_guard(), (0, []))

    def test_renamed_test_file_is_not_a_removed_assertion(self):
        self.commit_base(**{"old_test.py": "assert a\nassert b\n"})
        git(self.root, "mv", "old_test.py", "new_test.py")
        self.assertEqual(self.run_guard(), (0, []))

    def test_latest_py_is_not_a_test_path(self):
        self.commit_base(**{"latest.py": "assert a\nassert b\n"})
        self.put("latest.py", "assert a\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_tools_own_files_and_markdown_not_scanned(self):
        self.commit_base(**{"a.py": "x\n"})
        self.put("dev/scripts/floor-guard.py", "# @ts-ignore\nit.skip(1)\n#[ignore]\n")
        self.put("dev/tests/test_floor_guard.py", "#[ignore]\n")
        self.put("NOTES.md", "use `git commit --no-verify` and @ts-ignore\n")
        self.assertEqual(self.run_guard(), (0, []))

    def test_removed_dashes_line_does_not_skew_counts(self):
        self.commit_base(**{"a_test.py": "---\nassert a\n"})
        self.put("a_test.py", "assert a\n")
        self.assertEqual(self.run_guard(), (0, []))


if __name__ == "__main__":
    unittest.main()
