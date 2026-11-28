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

    def summary(self, found, criticals, criteria="C1 met (t1)"):
        (self.root / ".dev").mkdir(exist_ok=True)
        (self.root / "docs" / "gates").mkdir(parents=True, exist_ok=True)
        phase = self.root / ".dev" / "phase-31.md"
        phase.write_text(f"# Phase 31\n\n## Quality Gate — Phase 31: x\n- [x] Diff review — 0 critical @{self.sid()}\n")
        (self.root / "docs" / "gates" / "phase-31.md").write_text(
            f"## Gate summary — Phase 31: x\n- Tier: small — 3 files\n- Found: {found}\n- Criteria: {criteria}\n"
            f"- Criticals: {criticals}\n")
        return phase

    def test_gate_summary_counts_every_critical(self):
        # v4.18.0 RED: 174 gate summaries; Spec checker test gaps were often written as "0 critical" or notes.
        ok = self.summary("2 critical + 1 notes (Diff review: 1, Spec checker: 1)",
                          "Diff review — race in save; Spec checker — C2 untested",
                          "C1 met (t1); C2 untested → test added")
        self.assertEqual(ce.summary_problems(ok), [])
        short = self.summary("1 critical + 0 notes", "Diff review — race in save; Spec checker — C2 untested")
        self.assertTrue(any("Found says 1 critical, Criticals lists 2" in p for p in ce.summary_problems(short)))
        gap = self.summary("0 critical + 1 notes (Spec checker: test gap as note)", "none",
                           "C1 met (t1); C2 untested → test added")
        self.assertTrue(any("untested" in p and "Spec checker" in p for p in ce.summary_problems(gap)))
        self.assertTrue(any("gate summary" in p for p in ce.check(self.root, gap)))

    def test_gate_summary_entries_split_only_between_findings(self):
        # Final review: a `;` inside an entry or "None — 0" were miscounted.
        semi = self.summary("1 critical + 0 notes", "Diff review — save() drops rows; see a.py:3; b.py:4")
        self.assertEqual(ce.summary_problems(semi), [])
        none = self.summary("0 critical + 2 notes", "None — 0 criticals")
        self.assertEqual(ce.summary_problems(none), [])
        step_d = self.summary("2 critical (Step D too) + 0 notes", "Diff review — race; Step D — e2e red on login")
        self.assertEqual(ce.summary_problems(step_d), [])

    def test_legacy_design_and_motion_items_still_close(self):
        # v4.18.0 removed both from the gate; checklists written before keep them and must still pass.
        i = self.sid()
        self.state([f"- [x] Diff review — 0 critical @{i}",
                    "- [x] Design detector — skipped: engine not built",
                    "- [x] Motion review — 0 critical @0123456789ab",
                    f"- [x] Fix review — 0 critical @{i}"])
        self.assertEqual(self.run_check(), [])

    def test_old_gate_summary_without_criticals_line_is_not_checked(self):
        phase = self.summary("0 critical", "none")
        g = self.root / "docs" / "gates" / "phase-31.md"
        g.write_text("\n".join(l for l in g.read_text().splitlines() if not l.startswith("- Criticals:")) + "\n")
        self.assertEqual(ce.summary_problems(phase), [])

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
                self.assertTrue(all("write the checklist anew per gate.md" in x and "rerun its checked items" in x
                                    for x in old))

    def test_rebuilt_v2_checklist_passes(self):
        # A checklist written anew per gate.md "Gate Checklist" passes once its items carry evidence.
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
                    "- [x] Polish review — skipped: vibepolish not installed",
                    f"- [x] UX review — skipped: ux-ui-design not installed @{i}",
                    "- [x] Tech-Stack Review: shadcn — skipped: skill not installed",
                    "- [x] Second opinion: codex diff — skipped: quota-exhausted"])
        self.assertEqual(self.run_check(), [])
        self.assertEqual(ce.skipped(self.root / "STATE.md"),
                         [("Polish review", "vibepolish not installed"),
                          ("UX review", "ux-ui-design not installed"),
                          ("Tech-Stack Review: shadcn", "skill not installed"),
                          ("Second opinion: codex diff", "quota-exhausted")])

    def test_skipped_item_survives_a_later_code_change(self):
        self.state(["- [x] Polish review — skipped: vibepolish not installed"])
        (self.root / "a.txt").write_text("three\n")
        self.assertEqual(self.run_check(), [])

    def test_mandatory_check_cannot_be_skipped(self):
        self.state(["- [x] Typecheck + lint + tests — skipped: took too long"])
        problems = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("not skippable", problems[0])
        self.assertEqual(ce.skipped(self.root / "STATE.md"), [])

    def test_skip_without_reason_is_reported(self):
        self.state(["- [x] Polish review — skipped:"])
        self.assertIn("no reason", self.run_check()[0])

    def test_open_skipped_item_still_blocks(self):
        self.state(["- [ ] Polish review — skipped: vibepolish not installed"])
        self.assertIn("open", self.run_check()[0])

    def test_cli_prints_skipped_not_passed(self):
        self.state([f"- [x] Diff review — 0 critical @{self.sid()}",
                    "- [x] Polish review — skipped: vibepolish not installed"])
        run = subprocess.run(["python3", str(HERE.parent / "scripts" / "check-evidence.py"), "check", "STATE.md"],
                             cwd=self.root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("skipped: Polish review — vibepolish not installed", run.stdout)
        self.assertIn("1 skipped, not passed", run.stdout)

    def test_ux_and_polish_review_can_be_skipped(self):
        self.state(["- [x] UX review — skipped: skill not installed",
                    "- [x] Polish review — skipped: skill not installed"])
        self.assertEqual(self.run_check(), [])

    def test_skippable_list_matches_gate_md(self):
        text = (HERE.parent / "gate.md").read_text()
        rule = text.split("**Skipped is closed, never passed.** Only", 1)[1].split("may be closed as", 1)[0]
        names = [n.strip().lower() for n in rule.replace(" and ", ", ").replace("items", "").split(",") if n.strip()]
        self.assertIn("ux review", names)
        for name in names:
            self.assertIn(name, ce.SKIPPABLE, name)

    def test_review_items_are_the_step_a_analyses(self):
        text = (HERE.parent / "gate.md").read_text()
        step_a = text.split("<!-- Step A, always -->", 1)[1].split("<!-- Steps B and C", 1)[0]
        items = [line.split("]", 1)[1].split("<!--")[0].strip().lower()
                 for line in step_a.splitlines() if line.startswith("- [ ]")]
        items = ["tech-stack review" if i.startswith("tech-stack review") else i for i in items]
        self.assertEqual(sorted(set(items)), sorted(set(ce.REVIEW_ITEMS) - set(ce.LEGACY) - set(ce.SLIM_REVIEW)))

    def test_full_run_in_ci_is_valid_test_evidence(self):
        i = self.sid()
        self.state([f"- [x] Typecheck + lint + tests — 37 passed; full: CI 1a2b3c4 @{i}"])
        self.assertEqual(self.run_check(), [])

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
        # v4.18.3 RED: a stale Fix review listed every Step A item as "rerun it" (23 of 27 such
        # outputs in a 3-day sample); the sessions reran all analyses instead of the Fix review.
        self.assertEqual(len(problems), 2)
        self.assertTrue(problems[0].startswith("stale: Fix review"))
        self.assertTrue(problems[1].startswith("covered: Diff review, Spec checker"))
        self.assertIn("rerun only the Fix review", problems[1])

    def test_open_fix_review_covers_the_review_items(self):
        self.state([f"- [x] Diff review — 0 findings @{self.OLD}", "- [ ] Fix review"])
        problems = self.run_check()
        self.assertEqual(problems[0], "open: Fix review")
        self.assertTrue(problems[1].startswith("covered: Diff review"))
        self.assertEqual(len(problems), 2)

    def test_covered_never_hides_tests_or_similar_bugs(self):
        self.state([f"- [x] Fix review — clean @{self.OLD}", f"- [x] Similar-bugs scan — none @{self.OLD}",
                    f"- [x] Typecheck + lint + tests — 412 passed @{self.OLD}"])
        problems = self.run_check()
        self.assertEqual([x.split(" was")[0] for x in problems],
                         ["stale: Fix review", "stale: Similar-bugs scan", "stale: Typecheck + lint + tests"])

    def test_mark_ticks_one_item_with_the_current_id(self):
        # v4.18.3 RED: agents ticked items with `sed -i` on the phase file (383 edits in 137 sessions
        # of a 3-day sample), often retrying the regex.
        self.state(["- [ ] Diff review", "- [ ] Typecheck + lint + tests", "- [ ] Polish review"])
        f = self.root / "STATE.md"
        line = ce.mark(self.root, f, "typecheck", "0 errors, 412 passed")
        self.assertEqual(line, f"- [x] Typecheck + lint + tests — 0 errors, 412 passed @{self.sid()}")
        ce.mark(self.root, f, "Diff review", "0 critical")
        ce.mark(self.root, f, "Polish review", "skipped: vibepolish not installed")
        self.assertEqual(self.run_check(), [])
        self.assertIn("- [x] unrelated", f.read_text())

    def test_mark_overwrites_a_ticked_item_and_rejects_ambiguity(self):
        self.state([f"- [x] Diff review — 1 critical @{self.OLD}", "- [ ] Second opinion: codex diff"])
        f = self.root / "STATE.md"
        ce.mark(self.root, f, "diff review", "0 critical")
        self.assertIn(f"- [x] Diff review — 0 critical @{self.sid()}", f.read_text())
        with self.assertRaises(ValueError):
            ce.mark(self.root, f, "", "x")
        with self.assertRaises(ValueError):
            ce.mark(self.root, f, "unknown", "x")
        with self.assertRaises(ValueError):
            ce.mark(self.root, f, "second", "  ")

    def test_mark_cli(self):
        self.state(["- [ ] Diff review"])
        script = HERE.parent / "scripts" / "check-evidence.py"
        r = subprocess.run(["python3", str(script), "mark", "Diff", "0 critical", "STATE.md"],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run(["python3", str(script), "mark", "Nope", "x", "STATE.md"],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("matches 0 gate items", r.stderr)
        h = subprocess.run(["python3", str(script), "--help"], capture_output=True, text=True).stdout
        self.assertIn("check-evidence.py mark 'Typecheck + lint + tests'", h)

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

    def test_codex_fix_and_similar_never_inherit(self):
        # Review fix round 1 (I-2): the Codex items of Steps B/C rerun on the final state like
        # their Claude items; only the Step A Codex items may keep the wave's state.
        i = self.sid()
        self.state([f"- [x] Fix review — fix diff clean @{i}",
                    f"- [x] Second opinion: codex diff — 0 critical @{self.OLD}",
                    f"- [x] Second opinion: codex fix — 0 critical @{self.OLD}",
                    f"- [x] Second opinion: codex similar — none @{self.OLD}"])
        problems = self.run_check()
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(any("codex fix" in x for x in problems), problems)
        self.assertTrue(any("codex similar" in x for x in problems), problems)

    def test_missing_gate_section_is_reported(self):
        (self.root / "STATE.md").write_text("# State\n\nno gate here\n")
        self.assertIn("no gate checklist", self.run_check()[0])

    # --- phase file (.dev/phase-<N>.md) instead of STATE.md ---

    def phase_file(self, base, phase, lines):
        d = Path(base) / ".dev"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"phase-{phase}.md"
        f.write_text(f"# Phase {phase}\n\n## Quality Gate \u2014 Phase {phase}: Login\n" + "\n".join(lines)
                     + "\n\n## Context\n- [x] unrelated\n")
        return f

    def claim(self, base, phase, mark="!"):
        branch = git(self.root, "branch", "--show-current").strip()
        Path(base).mkdir(parents=True, exist_ok=True)
        (Path(base) / "ROADMAP.md").write_text(
            f"# Roadmap\n\n- [x] Phase 1: Setup\n- [{mark}] Phase {phase}: Login @claim:{branch}@2026-11-11\n"
            "- [ ] Phase 4: Later\n")

    def test_phase_file_checklist_is_read(self):
        i = self.sid()
        f = self.phase_file(self.root, "3", [f"- [x] Diff review \u2014 0 critical @{i}"])
        # the phase file is bookkeeping: writing it must not have staled the id
        self.assertEqual(ce.state_id(self.root), i)
        self.assertEqual(ce.check(self.root, f), [])

    def test_default_finds_phase_file_of_claimed_phase(self):
        self.claim(self.root, "3")
        f = self.phase_file(self.root, "3", ["- [ ] Diff review"])
        self.phase_file(self.root, "4", ["- [ ] Diff review"])
        self.assertEqual(ce.default_file(self.root).resolve(), f.resolve())

    def test_default_handles_dotted_and_lettered_phase_ids(self):
        self.claim(self.root, "6a", mark="~")
        f = self.phase_file(self.root, "6a", ["- [ ] x"])
        self.assertEqual(ce.default_file(self.root).resolve(), f.resolve())
        self.claim(self.root, "4.1")
        f = self.phase_file(self.root, "4.1", ["- [ ] x"])
        self.assertEqual(ce.default_file(self.root).resolve(), f.resolve())

    def test_default_ignores_claim_on_another_branch(self):
        (self.root / "ROADMAP.md").write_text("- [!] Phase 3: Login @claim:other-branch@2026-11-11\n")
        self.phase_file(self.root, "3", ["- [ ] x"])
        self.state(["- [ ] x"])
        self.assertEqual(ce.default_file(self.root).resolve(), (self.root / "STATE.md").resolve())

    def test_legacy_state_checklist_still_works(self):
        i = self.sid()
        self.state([f"- [x] Diff review \u2014 0 critical @{i}"])
        self.assertEqual(ce.default_file(self.root).resolve(), (self.root / "STATE.md").resolve())
        self.assertEqual(self.run_check(), [])

    def test_bookkeeping_phase_and_gate_files_do_not_change_state(self):
        before = self.sid()
        self.phase_file(self.root, "3", ["- [ ] Diff review"])
        (self.root / "docs" / "gates").mkdir(parents=True)
        (self.root / "docs" / "gates" / "phase-3.md").write_text("gate record\n")
        self.assertEqual(self.sid(), before)

    def test_code_under_dev_is_not_bookkeeping(self):
        # Only phase files, the marker and gate records are bookkeeping; tools a project keeps in
        # .dev/ are code under review.
        before = self.sid()
        (self.root / ".dev").mkdir()
        (self.root / ".dev" / ".gitkeep").write_text("")
        self.assertEqual(self.sid(), before)
        (self.root / ".dev" / "tools").mkdir()
        (self.root / ".dev" / "tools" / "x.sh").write_text("echo hi\n")
        self.assertNotEqual(self.sid(), before)

    def test_bold_phase_line_finds_the_phase_file(self):
        branch = git(self.root, "branch", "--show-current").strip()
        (self.root / "ROADMAP.md").write_text(
            f"# Roadmap\n\n- [x] **Phase 1: Setup**\n- [!] **Phase 3: Login** @claim:{branch}@2026-11-11\n")
        f = self.phase_file(self.root, "3", ["- [ ] Diff review"])
        self.assertEqual(ce.default_file(self.root).resolve(), f.resolve())
        (self.root / "ROADMAP.md").write_text(f"- [~] __Phase 3: Login__ @claim:{branch}@2026-11-11\n")
        self.assertEqual(ce.default_file(self.root).resolve(), f.resolve())

    def test_italic_title_and_star_bullet_find_the_phase_file(self):
        branch = git(self.root, "branch", "--show-current").strip()
        f = self.phase_file(self.root, "3", ["- [ ] Diff review"])
        for line in (f"- [!] *Phase 3: Login* @claim:{branch}@2026-11-11", f"* [!] Phase 3: Login @claim:{branch}@2026-11-11"):
            (self.root / "ROADMAP.md").write_text(line + "\n")
            self.assertEqual(ce.default_file(self.root).resolve(), f.resolve(), line)

    def migrated_state(self, text):
        (self.root / ".dev").mkdir(exist_ok=True)
        (self.root / ".dev" / ".gitkeep").write_text("")
        (self.root / "STATE.md").write_text(text)

    def test_milestone_end_pending_line_is_bookkeeping(self):
        self.migrated_state("# State\n\n## Blockers & Risks\n- none\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "migrated")
        before = self.sid()
        self.migrated_state("# State\n\n## Blockers & Risks\n- none\nMilestone End pending: Milestone 2: Next\n"
                            "Milestone End pending: Milestone 3: Later\n")
        self.assertEqual(self.sid(), before)

    def test_content_change_in_migrated_state_is_code(self):
        # A phase that changes STATE.md content (a trap, a constraint) changes the reviewed state,
        # so its evidence goes stale and the Fix review diff shows the change.
        self.migrated_state("# State\n\n## Constraints\n- pnpm 12.x\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "migrated")
        before = self.sid()
        self.migrated_state("# State\n\n## Constraints\n- pnpm 12.7.0\n")
        after = self.sid()
        self.assertNotEqual(after, before)
        diff = git(self.root, "diff", before, after)
        self.assertIn("pnpm 12.7.0", diff)

    def test_migration_makes_ticked_items_stale(self):
        # Old format: STATE.md holds the checklist and is bookkeeping. The marker turns STATE.md into
        # code, so the migration changes @state without a code change; commands.md (`migrate:`) tells
        # the session to rerun the ticked items of its phase.
        (self.root / "STATE.md").write_text("# State\n\n## Constraints\n- x\n\n## Quality Gate — Phase 3: Login\n- [x] Diff review\n")
        before = self.sid()
        (self.root / ".dev").mkdir()
        (self.root / ".dev" / ".gitkeep").write_text("")
        (self.root / "STATE.md").write_text("# State\n\n## Constraints\n- x\n")
        self.assertNotEqual(self.sid(), before)

    def test_old_format_state_stays_bookkeeping(self):
        # Before the migration the gate checklist itself lives in STATE.md.
        before = self.sid()
        (self.root / "STATE.md").write_text("# State\n\n## Constraints\n- anything\n")
        self.assertEqual(self.sid(), before)

    def test_monorepo_subdir(self):
        app = self.root / "apps" / "web"
        self.claim(app, "3")
        i = self.sid()
        f = self.phase_file(app, "3", [f"- [x] Diff review \u2014 0 critical @{i}"])
        (app / "docs" / "gates").mkdir(parents=True)
        (app / "docs" / "gates" / "phase-3.md").write_text("gate record\n")
        self.assertEqual(self.sid(), i)
        self.assertEqual(ce.default_file(app).resolve(), f.resolve())
        self.assertEqual(ce.check(self.root, ce.default_file(app)), [])


    def test_slim_gate_lists_only_triggered_items(self):
        # Opt-in `defaults.gate: slim` (gate-slim.md): one Spec checker plus the specialists whose trigger fired;
        # untriggered specialists are simply absent, as in the default gate.
        i = self.sid()
        self.state(["<!-- gate: slim; tier: small -->", f"- [x] Spec checker — 0 critical @{i}",
                    f"- [x] Security review — 0 critical @{i}",
                    f"- [x] Typecheck + lint + tests — 0 errors, 12 passed @{i}",
                    f"- [x] Production Build — ok @{i}", "- [ ] Gate commit"])
        self.assertEqual(self.run_check(before_commit=True), [])
        self.state(["<!-- gate: slim -->", f"- [x] Spec checker — 0 critical @{i}",
                    f"- [x] Typecheck + lint + tests — 0 errors, 12 passed @{i}"])
        self.assertEqual(self.run_check(), [])

    def test_slim_gate_still_catches_stale_evidence(self):
        old = self.sid()
        self.state(["<!-- gate: slim -->", f"- [x] Spec checker — 0 critical @{old}",
                    f"- [x] Typecheck + lint + tests — 0 errors, 12 passed @{old}"])
        (self.root / "a.txt").write_text("three\n")
        problems = self.run_check()
        self.assertTrue(any(p.startswith("stale: Spec checker") for p in problems), problems)
        self.assertTrue(any(p.startswith("stale: Typecheck") for p in problems), problems)
        # A current Fix review still covers the review items in the slim gate.
        i = self.sid()
        self.state(["<!-- gate: slim -->", f"- [x] Code review — 1 finding @{old}",
                    f"- [x] Fix review — round 1: 0 critical; criticals: none @{i}",
                    f"- [x] Typecheck + lint + tests — 0 errors, 12 passed @{i}"])
        self.assertEqual(self.run_check(), [])

    def test_slim_gate_refuses_a_third_fix_round(self):
        i = self.sid()
        self.state(["<!-- gate: slim -->", f"- [x] Spec checker — 1 critical @{i}",
                    f"- [x] Fix review — round 3: 0 critical @{i}"])
        problems = self.run_check()
        self.assertTrue(any("at most 2 fix rounds" in p for p in problems), problems)
        self.state(["<!-- gate: slim -->", f"- [x] Spec checker — 1 critical @{i}",
                    f"- [x] Fix review — 0 critical @{i}"])
        self.assertTrue(any("name its round" in p for p in self.run_check()))
        self.state(["<!-- gate: slim -->", f"- [x] Spec checker — 1 critical @{i}", "- [ ] Fix review"])
        f = self.root / "STATE.md"
        with self.assertRaises(ValueError) as e:
            ce.mark(self.root, f, "Fix review", "round 3: 0 critical")
        self.assertIn("at most 2 fix rounds", str(e.exception))
        self.assertIn("round 2: 0 critical", ce.mark(self.root, f, "Fix review", "round 2: 0 critical; criticals: none"))

    def test_slim_round_names_every_critical_with_its_state(self):
        # Owner 28.11.2026: a replay fixed one of two criticals in round 1 and never said why the other stayed out.
        i = self.sid()
        self.state(["<!-- gate: slim -->", f"- [x] Fix review — round 1: C1 fixed @{i}"])
        self.assertTrue(any("must name every critical" in p for p in self.run_check()))
        self.state(["<!-- gate: slim -->", f"- [x] Fix review — round 1: 0 new; criticals: C1 fixed, C2 open @{i}"])
        self.assertTrue(any("needs its reason" in p for p in self.run_check()))
        self.state(["<!-- gate: slim -->", "- [ ] Fix review"])
        f = self.root / "STATE.md"
        for bad in ("round 1: 0 new", "round 1: 0 new; criticals:", "round 1: 0 new; criticals: C2 open"):
            with self.assertRaises(ValueError):
                ce.mark(self.root, f, "Fix review", bad)
        ok = "round 1: 0 new; criticals: C1 fixed, C2 open: needs the create hook, in round 2"
        self.assertIn("C2 open: needs", ce.mark(self.root, f, "Fix review", ok))
        self.assertEqual(self.run_check(), [])

    def test_default_gate_has_no_round_limit_in_the_script(self):
        # Without the slim marker nothing changes: rounds are counted per finding by gate.md, not here.
        i = self.sid()
        self.state([f"- [x] Diff review — 1 critical @{i}", f"- [x] Fix review — round 3: 0 critical @{i}",
                    f"- [x] Fix review — 0 critical @{i}"])
        self.assertEqual(self.run_check(), [])
        self.assertIn("round 3", ce.mark(self.root, self.root / "STATE.md", "Diff review", "round 3: x"))

if __name__ == "__main__":
    unittest.main()
