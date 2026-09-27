"""Tests for scripts/check-evidence.py — stale or missing gate evidence must be caught.

    cd dev/tests && python3 -m unittest test_check_evidence
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_evidence", HERE.parent / "scripts" / "check-evidence.py")
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "t")
        (self.root / "a.txt").write_text("one\n")
        git(self.root, "add", "a.txt")
        git(self.root, "commit", "-qm", "init")
        (self.root / "a.txt").write_text("two\n")          # the phase's change, uncommitted

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, lines):
        (self.root / "STATE.md").write_text(
            "# State\n\n## Quality Gate — Phase 3: Login\n" + "\n".join(lines) + "\n\n## Context\n- [x] unrelated\n")

    def run_check(self, before_commit=False):
        return ce.check(self.root, self.root / "STATE.md", before_commit=before_commit)

    def sid(self):
        return ce.state_id(self.root)

    def test_all_checked_with_current_id_passes(self):
        i = self.sid()
        self.state([f"- [x] Bug hunt — 0 critical @{i}", f"- [x] Typecheck + lint + tests — 412 passed @{i}"])
        self.assertEqual(self.run_check(), [])

    def test_change_after_check_makes_it_stale(self):
        i = self.sid()
        self.state([f"- [x] Bug hunt — 0 critical @{i}"])
        (self.root / "a.txt").write_text("three\n")
        problems = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("stale", problems[0])

    def test_new_untracked_file_changes_the_state(self):
        i = self.sid()
        (self.root / "b.txt").write_text("new\n")
        self.assertNotEqual(i, self.sid())

    def test_ignored_files_do_not_change_the_state(self):
        (self.root / ".gitignore").write_text("build/\n")
        i = self.sid()
        (self.root / "build").mkdir()
        (self.root / "build" / "out.js").write_text("x")
        self.assertEqual(i, self.sid())

    def test_committing_the_checked_content_keeps_the_id(self):
        i = self.sid()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "chore: quality gate — Phase 3 [gate-pass]")
        self.assertEqual(i, self.sid())

    def test_writing_the_checklist_does_not_change_the_state(self):
        i = self.sid()
        self.state([f"- [x] Bug hunt — 0 critical @{i}"])
        (self.root / "ROADMAP.md").write_text("- [x] Phase 3\n")
        self.assertEqual(i, self.sid())

    def test_state_id_leaves_the_index_alone(self):
        before = git(self.root, "status", "--porcelain")
        self.sid()
        self.assertEqual(before, git(self.root, "status", "--porcelain"))

    def test_missing_id_is_reported(self):
        self.state(["- [x] Bug hunt — 0 critical"])
        self.assertIn("no @state", self.run_check()[0])

    def test_missing_evidence_is_reported(self):
        self.state([f"- [x] Bug hunt @{self.sid()}"])
        self.assertIn("no evidence", self.run_check()[0])

    def test_open_item_blocks_completion(self):
        i = self.sid()
        self.state([f"- [x] Bug hunt — 0 critical @{i}", "- [ ] E2E Tests"])
        self.assertIn("open", self.run_check()[0])

    def test_before_commit_allows_gate_commit_and_ci_open(self):
        i = self.sid()
        self.state([f"- [x] Bug hunt — 0 critical @{i}", "- [ ] Gate commit", "- [ ] CI status check"])
        self.assertEqual(self.run_check(before_commit=True), [])
        self.assertEqual(len(self.run_check(before_commit=False)), 2)

    def test_items_outside_the_gate_section_are_ignored(self):
        self.state([f"- [x] Bug hunt — ok @{self.sid()}"])
        self.assertEqual(self.run_check(), [])

    def test_missing_gate_section_is_reported(self):
        (self.root / "STATE.md").write_text("# State\n\nno gate here\n")
        self.assertIn("no gate checklist", self.run_check()[0])


if __name__ == "__main__":
    unittest.main()
