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
        self.state([f"- [x] Diff review — 0 critical @{i}", f"- [x] Typecheck + lint + tests — 412 passed @{i}"])
        self.assertEqual(self.run_check(), [])

    def test_change_after_check_makes_it_stale(self):
        i = self.sid()
        self.state([f"- [x] Diff review — 0 critical @{i}"])
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
        self.state([f"- [x] Diff review — 0 critical @{i}"])
        (self.root / "ROADMAP.md").write_text("- [x] Phase 3\n")
        self.assertEqual(i, self.sid())

    def test_bookkeeping_files_in_a_subdirectory_do_not_change_the_state(self):
        # Monorepo: the app keeps STATE.md/ROADMAP.md next to its own code, not at the root.
        (self.root / "apps" / "web").mkdir(parents=True)
        (self.root / "apps" / "web" / "STATE.md").write_text("# State\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "add app state")
        i = self.sid()
        (self.root / "apps" / "web" / "STATE.md").write_text("# State\n\n- [x] Diff review\n")
        (self.root / "apps" / "web" / "ROADMAP.md").write_text("- [!] Phase 3\n")
        self.assertEqual(i, self.sid())

    def test_state_id_leaves_the_index_alone(self):
        before = git(self.root, "status", "--porcelain")
        self.sid()
        self.assertEqual(before, git(self.root, "status", "--porcelain"))

    def test_missing_id_is_reported(self):
        self.state(["- [x] Diff review — 0 critical"])
        self.assertIn("no @state", self.run_check()[0])

    def test_missing_evidence_is_reported(self):
        self.state([f"- [x] Diff review @{self.sid()}"])
        self.assertIn("no evidence", self.run_check()[0])

    def test_open_item_blocks_completion(self):
        i = self.sid()
        self.state([f"- [x] Diff review — 0 critical @{i}", "- [ ] E2E Tests"])
        self.assertIn("open", self.run_check()[0])

    def test_before_commit_allows_gate_commit_and_ci_open(self):
        i = self.sid()
        self.state([f"- [x] Diff review — 0 critical @{i}", "- [ ] Gate commit", "- [ ] CI status check"])
        self.assertEqual(self.run_check(before_commit=True), [])
        self.assertEqual(len(self.run_check(before_commit=False)), 2)

    def test_items_outside_the_gate_section_are_ignored(self):
        self.state([f"- [x] Diff review — ok @{self.sid()}"])
        self.assertEqual(self.run_check(), [])

    def test_skipped_optional_check_is_closed_and_reported_as_skipped(self):
        i = self.sid()
        self.state([f"- [x] Diff review — 0 critical @{i}",
                    "- [x] Design detector — skipped: engine not built",
                    f"- [x] Motion review — skipped: animation standards not found @{i}",
                    "- [x] Tech-Stack Review: shadcn — skipped: skill not installed"])
        self.assertEqual(self.run_check(), [])
        self.assertEqual(ce.skipped(self.root / "STATE.md"),
                         [("Design detector", "engine not built"),
                          ("Motion review", "animation standards not found"),
                          ("Tech-Stack Review: shadcn", "skill not installed")])

    def test_skipped_item_survives_a_later_code_change(self):
        self.state(["- [x] Design detector — skipped: engine not built"])
        (self.root / "a.txt").write_text("three\n")
        self.assertEqual(self.run_check(), [])

    def test_mandatory_check_cannot_be_skipped(self):
        self.state(["- [x] Typecheck + lint + tests — skipped: took too long"])
        problems = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("not skippable", problems[0])
        self.assertEqual(ce.skipped(self.root / "STATE.md"), [])

    def test_skip_without_reason_is_reported(self):
        self.state(["- [x] Design detector — skipped:"])
        self.assertIn("no reason", self.run_check()[0])

    def test_open_skipped_item_still_blocks(self):
        self.state(["- [ ] Design detector — skipped: engine not built"])
        self.assertIn("open", self.run_check()[0])

    def test_cli_prints_skipped_not_passed(self):
        self.state([f"- [x] Diff review — 0 critical @{self.sid()}",
                    "- [x] Design detector — skipped: engine not built"])
        run = subprocess.run(["python3", str(HERE.parent / "scripts" / "check-evidence.py"), "check", "STATE.md"],
                             cwd=self.root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("skipped: Design detector — engine not built", run.stdout)
        self.assertIn("1 skipped, not passed", run.stdout)

    OLD = "0123456789ab"

    def test_review_items_valid_with_current_fix_review(self):
        i = self.sid()
        self.state([f"- [x] Diff review — 0 findings @{self.OLD}", f"- [x] Spec checker — ok @{self.OLD}",
                    f"- [x] Fix review — fix diff clean @{i}", f"- [x] Typecheck + lint + tests — 412 passed @{i}"])
        self.assertEqual(self.run_check(), [])

    def test_review_items_stale_without_fix_review(self):
        i = self.sid()
        self.state([f"- [x] Diff review — 0 findings @{self.OLD}", f"- [x] Spec checker — ok @{self.OLD}",
                    f"- [x] Typecheck + lint + tests — 412 passed @{i}"])
        problems = self.run_check()
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("Diff review" in x for x in problems))
        self.assertTrue(any("Spec checker" in x for x in problems))

    def test_fix_review_must_be_current(self):
        self.state([f"- [x] Diff review — 0 findings @{self.OLD}", f"- [x] Spec checker — ok @{self.OLD}",
                    f"- [x] Fix review — fix diff clean @{self.OLD}"])
        problems = self.run_check()
        self.assertEqual(len(problems), 3)
        self.assertTrue(any("Fix review" in x for x in problems))

    def test_tests_item_never_inherits(self):
        i = self.sid()
        self.state([f"- [x] Fix review — fix diff clean @{i}", f"- [x] Typecheck + lint + tests — 412 passed @{self.OLD}"])
        problems = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("Typecheck", problems[0])

    def test_similar_bugs_never_inherits(self):
        i = self.sid()
        self.state([f"- [x] Fix review — fix diff clean @{i}", f"- [x] Similar-bugs scan — none @{self.OLD}"])
        problems = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("Similar-bugs", problems[0])

    def test_missing_gate_section_is_reported(self):
        (self.root / "STATE.md").write_text("# State\n\nno gate here\n")
        self.assertIn("no gate checklist", self.run_check()[0])


if __name__ == "__main__":
    unittest.main()
