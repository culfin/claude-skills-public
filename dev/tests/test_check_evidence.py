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

    def test_test_item_without_a_count_is_rejected(self):
        i = self.sid()
        self.state([f"- [x] Typecheck + lint + tests — all green @{i}"])
        problems = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("no test count: Typecheck + lint + tests", problems[0])

    def test_zero_tests_is_not_green(self):
        i = self.sid()
        self.state([f"- [x] Typecheck + lint + tests — 0 errors, 0 passed @{i}",
                    f"- [x] E2E Tests — unit 12 passed, e2e 0 tests passed @{i}"])
        problems = self.run_check()
        self.assertEqual(len(problems), 2)
        self.assertTrue(all("no test count" in p for p in problems))

    def test_counts_per_suite_and_no_tests_configured_pass(self):
        i = self.sid()
        self.state([f"- [x] Typecheck + lint + tests — 0 errors, vitest 412 passed, pytest 9 tests passed @{i}",
                    f"- [x] E2E Tests — no tests configured @{i}"])
        self.assertEqual(self.run_check(), [])

    def test_count_rule_applies_only_to_test_items(self):
        i = self.sid()
        self.state([f"- [x] Production Build — ok @{i}", f"- [x] Diff review — 0 critical @{i}"])
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

    def test_before_commit_allows_only_the_gate_commit_open(self):
        i = self.sid()
        self.state([f"- [x] Diff review — 0 critical @{i}", "- [ ] Gate commit"])
        self.assertEqual(self.run_check(before_commit=True), [])
        self.assertEqual(self.run_check(before_commit=False), ["open: Gate commit"])

    def v2_checklist(self, i):
        # A `[!]` phase written by /dev v2: items v3 has no step for, CI status check still open.
        return ["- [x] /simplify — 2 edits @" + i, "- [x] Change review — 0 critical @" + i,
                "- [ ] Bug hunt (phase scope)", f"- [x] Performance review (phase scope) — ok @{i}",
                f"- [x] Spec checker (5c-v) — 0 gaps @{i}", f"- [x] Typecheck + lint + tests — 412 passed @{i}",
                f"- [x] Production Build — ok @{i}", "- [ ] Gate summary (STATE.md)", "- [ ] Gate commit",
                "- [ ] CI status check"]

    def test_v2_checklist_is_reported_for_rebuild(self):
        self.state(self.v2_checklist(self.sid()))
        for before_commit in (True, False):
            with self.subTest(before_commit=before_commit):
                old = [x for x in self.run_check(before_commit) if x.startswith("pre-v3 item:")]
                self.assertEqual(len(old), 4, old)
                for name in ("/simplify", "Change review", "Bug hunt", "CI status check"):
                    self.assertTrue(any(name in x for x in old), name)
                self.assertTrue(all("rebuild the checklist" in x for x in old))

    def test_rebuilt_v2_checklist_passes(self):
        # gate.md "Gate Checklist": kept items keep their evidence (Spec checker (5c-v) -> Spec checker),
        # /simplify + Change review + Bug hunt become one open Diff review, CI status check is dropped.
        i = self.sid()
        rebuilt = ["- [ ] Diff review", f"- [x] Spec checker — 0 gaps @{i}",
                   f"- [x] Typecheck + lint + tests — 412 passed @{i}", f"- [x] Production Build — ok @{i}",
                   "- [ ] Gate summary (STATE.md)", "- [ ] Gate commit"]
        self.state(rebuilt)
        self.assertEqual(self.run_check(before_commit=True), ["open: Diff review", "open: Gate summary (STATE.md)"])
        rebuilt[0] = f"- [x] Diff review — 0 critical @{i}"
        rebuilt[4] = f"- [x] Gate summary (STATE.md) — written @{i}"
        self.state(rebuilt)
        self.assertEqual(self.run_check(before_commit=True), [])
        rebuilt[5] = f"- [x] Gate commit — abc1234 @{i}"
        self.state(rebuilt)
        self.assertEqual(self.run_check(), [])

    def test_phase_check_ignores_a_ci_repair_checklist(self):
        # A CI repair of Phase 2 lands while Phase 3 is in its gate: each check reads its own section.
        i = self.sid()
        (self.root / "STATE.md").write_text(
            "## Quality Gate — Phase 3: Login\n"
            f"- [x] Diff review — 0 critical @{i}\n- [ ] Gate commit\n\n"
            "## Quality Gate — Phase 2: Signup (CI repair)\n- [ ] Fix review\n- [ ] Production Build\n")
        self.assertEqual(self.run_check(before_commit=True), [])
        self.assertEqual(ce.check(self.root, self.root / "STATE.md", before_commit=True, repair=True),
                         ["open: Fix review", "open: Production Build"])

    def test_repair_without_repair_checklist_is_reported(self):
        self.state([f"- [x] Diff review — 0 critical @{self.sid()}"])
        problems = ce.check(self.root, self.root / "STATE.md", repair=True)
        self.assertEqual(len(problems), 1)
        self.assertIn("no CI-repair checklist", problems[0])

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
