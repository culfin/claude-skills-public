"""state-check.py: size limits, handoff position, phase claims, main-branch reconcile, archive."""
import datetime
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "state-check.py"
spec = importlib.util.spec_from_file_location("state_check", SCRIPT)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
TODAY = datetime.date(2026, 10, 7)

ROADMAP = """---
project: demo
---
# Roadmap

## Milestone 1: Base
Goal: the base
- [x] Phase 1 — Database @type:backend
- [—] Phase 2 — Old idea @type:ui

## Milestone 2: Next
- [~] Phase 3 — Login @type:auth {claim3}
- [ ] Phase 4 — Export @type:backend
"""


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


class StateCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "t")
        self.write(claim3="@claim:main@2026-10-06")
        (self.root / "STATE.md").write_text("# State\n\n## Handoff — main\nNext: Phase 3\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, claim3="", roadmap=None):
        (self.root / "ROADMAP.md").write_text((roadmap or ROADMAP).format(claim3=claim3))

    def check(self, branch="main", main=None):
        return sc.check(self.root, main=main, branch=branch, today=TODAY)

    def test_clean_project_has_no_findings(self):
        self.assertEqual(self.check(), [])

    def test_large_state_is_reported_with_its_largest_sections(self):
        (self.root / "STATE.md").write_text("## Handoff\nx\n\n## Diary\n" + "word " * 3100 + "\n")
        found = self.check()
        self.assertEqual(len(found), 1)
        self.assertIn("size: STATE.md has", found[0])
        self.assertIn("## Diary", found[0])

    def test_large_roadmap_lists_completed_milestones_as_archivable(self):
        self.write(claim3="@claim:main@2026-10-06", roadmap=ROADMAP + "\n## Notes\n" + "word " * 8100)
        found = self.check()
        self.assertTrue(any(f.startswith("size: ROADMAP.md") for f in found))
        arch = [f for f in found if f.startswith("archivable:")]
        self.assertEqual(len(arch), 1)
        self.assertIn("1 completed milestones", arch[0])
        self.assertIn("Milestone 1: Base", arch[0])
        self.assertNotIn("Milestone 2", arch[0])

    def test_handoff_far_down_is_reported(self):
        (self.root / "STATE.md").write_text("# State\n" + "line\n" * 100 + "## Handoff\nNext: x\n")
        found = self.check()
        self.assertEqual(len(found), 1)
        self.assertIn("handoff:", found[0])
        self.assertIn("line 102", found[0])

    def test_phase_claimed_by_another_branch_is_reported(self):
        git(self.root, "branch", "sitzung/b")
        self.write(claim3="@claim:sitzung/b@2026-10-06")
        found = self.check(branch="main")
        self.assertEqual(found, ["claimed: Phase 3 by sitzung/b since 2026-10-06 — skip unless the user picks it"])

    def test_own_claim_is_silent(self):
        self.assertEqual(self.check(branch="main"), [])

    def test_claim_of_a_gone_branch_is_stale(self):
        self.write(claim3="@claim:feature/gone@2026-10-06")
        found = self.check()
        self.assertEqual(len(found), 1)
        self.assertIn("stale claim: Phase 3 by feature/gone — branch gone", found[0])

    def test_old_foreign_claim_is_stale(self):
        git(self.root, "branch", "other")
        self.write(claim3="@claim:other@2026-09-20")
        found = self.check()
        self.assertEqual(len(found), 1)
        self.assertIn("stale claim: Phase 3 by other since 2026-09-20 (17 days)", found[0])

    def test_active_phase_without_claim_is_reported(self):
        self.write(claim3="")
        self.assertEqual(self.check(), ["unclaimed: Phase 3 [~] — claim it before resuming"])

    def test_phase_done_on_main_is_reported(self):
        git(self.root, "checkout", "-qb", "work")
        git(self.root, "checkout", "-q", "main")
        self.write(claim3="@claim:main@2026-10-06")
        (self.root / "ROADMAP.md").write_text(
            (self.root / "ROADMAP.md").read_text().replace("- [ ] Phase 4", "- [x] Phase 4"))
        git(self.root, "commit", "-qam", "roadmap: complete Phase 4")
        git(self.root, "checkout", "-q", "work")
        found = self.check(branch="work", main="main")
        self.assertIn("done on main: Phase 4 [x] — mark it here, do not redo it", found)

    def test_claim_on_main_for_an_open_phase_is_reported(self):
        git(self.root, "checkout", "-qb", "work")
        git(self.root, "checkout", "-q", "main")
        (self.root / "ROADMAP.md").write_text(
            (self.root / "ROADMAP.md").read_text().replace("- [ ] Phase 4 — Export @type:backend",
                                                           "- [~] Phase 4 — Export @type:backend @claim:other@2026-10-07"))
        git(self.root, "commit", "-qam", "roadmap: claim Phase 4")
        git(self.root, "checkout", "-q", "work")
        found = self.check(branch="work", main="main")
        self.assertIn("claimed on main: Phase 4 by other since 2026-10-07 — skip unless the user picks it", found)

    def test_archive_moves_milestone_and_its_gate_summaries(self):
        (self.root / "STATE.md").write_text(
            "# State\n\n## Handoff\nNext: Phase 3\n\n### Gate summary — Phase 1: Database\n- Tier: small\n\n"
            "### Gate summary — Phase 3: Login\n- Tier: large\n\n## Blockers & Risks\nNone.\n")
        self.assertEqual(sc.archive(self.root, "Milestone 1", today=TODAY), 0)
        road = (self.root / "ROADMAP.md").read_text()
        self.assertIn("## Milestone 1: Base\n\nDone: 2 phases (Phase 1 – Phase 2) — details in "
                      "`docs/roadmap-archive/milestone-1-base.md`", road)
        self.assertNotIn("Phase 1 — Database", road)
        self.assertIn("- [~] Phase 3", road)
        arch = (self.root / "docs/roadmap-archive/milestone-1-base.md").read_text()
        self.assertIn("- [x] Phase 1 — Database", arch)
        self.assertIn("### Gate summary — Phase 1: Database", arch)
        state = (self.root / "STATE.md").read_text()
        self.assertNotIn("Phase 1: Database", state)
        self.assertIn("### Gate summary — Phase 3: Login", state)
        self.assertIn("## Blockers & Risks", state)

    def test_archive_refuses_a_milestone_with_open_phases(self):
        before = (self.root / "ROADMAP.md").read_text()
        self.assertEqual(sc.archive(self.root, "Milestone 2", today=TODAY), 2)
        self.assertEqual((self.root / "ROADMAP.md").read_text(), before)

    def test_archive_keeps_gate_summaries_when_numbers_repeat(self):
        self.write(claim3="@claim:main@2026-10-06",
                   roadmap=ROADMAP.replace("Phase 3 — Login", "Phase 1 — Login"))
        (self.root / "STATE.md").write_text("## Handoff\nx\n\n### Gate summary — Phase 1: Database\n- Tier: small\n")
        self.assertEqual(sc.archive(self.root, "Milestone 1", today=TODAY), 0)
        self.assertIn("Gate summary — Phase 1", (self.root / "STATE.md").read_text())

    def test_dry_run_writes_nothing(self):
        before = (self.root / "ROADMAP.md").read_text()
        self.assertEqual(sc.archive(self.root, "Milestone 1", dry_run=True, today=TODAY), 0)
        self.assertEqual((self.root / "ROADMAP.md").read_text(), before)
        self.assertFalse((self.root / "docs").exists())

    def test_cli_exit_codes(self):
        run = lambda *a: subprocess.run([sys.executable, str(SCRIPT), *a, "--root", str(self.root)],
                                        capture_output=True, text=True)
        self.assertEqual(run("check", "--branch", "main", "--main", "main").returncode, 0)
        self.write(claim3="")
        r = run("check", "--branch", "main", "--main", "main")
        self.assertEqual(r.returncode, 1)
        self.assertIn("unclaimed: Phase 3", r.stdout)
        (self.root / "ROADMAP.md").unlink()
        self.assertEqual(run("check").returncode, 2)


if __name__ == "__main__":
    unittest.main()
