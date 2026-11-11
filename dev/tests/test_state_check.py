"""state-check.py: size limits, handoff position, phase claims, main-branch reconcile, archive,
phase files (.dev/phase-<N>.md) and migrate."""
import contextlib
import datetime
import io
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
        self.phase_file("3", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, claim3="", roadmap=None):
        (self.root / "ROADMAP.md").write_text((roadmap or ROADMAP).format(claim3=claim3))
        # The phase file lives in the checkout of the claiming branch: only a claim by main keeps it here.
        if "@claim:main@" not in claim3:
            (self.root / ".dev" / "phase-3.md").unlink(missing_ok=True)

    def phase_file(self, pid, branch, body="", root=None):
        d = (root or self.root) / ".dev"
        d.mkdir(parents=True, exist_ok=True)
        head = f"Branch: {branch}\n" if branch is not None else ""
        (d / f"phase-{pid}.md").write_text(head + body)

    def migrate(self, root=None, dry_run=False, branch=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sc.migrate(root or self.root, dry_run=dry_run, today=TODAY, branch=branch)
        return rc, buf.getvalue().splitlines()

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
        git(self.root, "branch", "session/b")
        self.write(claim3="@claim:session/b@2026-10-06")
        found = self.check(branch="main")
        self.assertEqual(found, ["claimed: Phase 3 by session/b since 2026-10-06 — skip unless the user picks it"])

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

    def claim_on(self, branch, phase="4", who="other", when="2026-10-07", date=None):
        """Commit a claim for `phase` on `branch` (created from main), then return to main."""
        git(self.root, "checkout", "-qb", branch, "main")
        (self.root / "ROADMAP.md").write_text(
            (self.root / "ROADMAP.md").read_text().replace(
                f"- [ ] Phase {phase} — Export @type:backend",
                f"- [~] Phase {phase} — Export @type:backend @claim:{who}@{when}"))
        env = None
        if date:
            import os
            env = {**os.environ, "GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date}
        subprocess.run(["git", "-C", str(self.root), "commit", "-qam", f"claim {phase}"],
                       check=True, capture_output=True, env=env)
        git(self.root, "checkout", "-q", "main")

    def test_claim_on_another_branch_is_reported(self):
        self.claim_on("session/b", who="session/b", when="2026-10-06", date="2026-10-06T10:00:00")
        found = self.check(branch="main", main="main")
        self.assertIn("claimed on session/b: Phase 4 by session/b since 2026-10-06 — skip unless the user picks it",
                      found)

    def test_claim_on_a_branch_is_seen_from_a_second_worktree(self):
        self.claim_on("session/b", who="session/b", when="2026-10-06", date="2026-10-06T10:00:00")
        wt = self.root / ".worktrees" / "c"
        git(self.root, "worktree", "add", "-q", "-b", "session/c", str(wt), "main")
        found = sc.check(wt, main="main", branch="session/c", today=TODAY)
        self.assertIn("claimed on session/b: Phase 4 by session/b since 2026-10-06 — skip unless the user picks it",
                      found)

    def test_claim_on_a_branch_older_than_scan_days_is_ignored(self):
        self.claim_on("session/old", who="session/old", when="2026-09-01", date="2026-09-01T10:00:00")
        found = self.check(branch="main", main="main")
        self.assertFalse(any(f.startswith("claimed on") for f in found), found)

    def test_own_branch_and_own_claims_are_not_reported(self):
        self.claim_on("work", who="work", date="2026-10-06T10:00:00")
        self.claim_on("session/x", who="work", date="2026-10-06T10:00:00")
        found = self.check(branch="work", main="main")
        self.assertFalse(any(f.startswith("claimed on") for f in found), found)

    def test_claim_is_reported_once_main_first(self):
        git(self.root, "checkout", "-qb", "work")
        git(self.root, "checkout", "-q", "main")
        (self.root / "ROADMAP.md").write_text(
            (self.root / "ROADMAP.md").read_text().replace("- [ ] Phase 4 — Export @type:backend",
                                                           "- [~] Phase 4 — Export @type:backend @claim:other@2026-10-07"))
        git(self.root, "commit", "-qam", "roadmap: claim Phase 4")
        git(self.root, "branch", "copy")
        git(self.root, "checkout", "-q", "work")
        found = [f for f in self.check(branch="work", main="main") if f.startswith("claimed on")]
        self.assertEqual(found, ["claimed on main: Phase 4 by other since 2026-10-07 — skip unless the user picks it"])

    def test_handoff_of_a_gone_branch_is_orphan(self):
        (self.root / "STATE.md").write_text("# State\n\n## Handoff — `feature/gone`\nNext: x\n")
        found = self.check(main="main")
        self.assertEqual(found, ["orphan handoff: '## Handoff — `feature/gone`' — branch feature/gone is gone "
                                 "or merged; remove the block"])

    def test_handoff_of_a_merged_branch_is_orphan(self):
        git(self.root, "checkout", "-qb", "done")
        (self.root / "x.txt").write_text("x\n")
        git(self.root, "add", "x.txt")
        git(self.root, "commit", "-qm", "work")
        git(self.root, "checkout", "-q", "main")
        git(self.root, "merge", "-q", "--no-ff", "-m", "merge", "done")
        git(self.root, "checkout", "-qb", "work")
        (self.root / "STATE.md").write_text("# State\n\n### Handoff: done (Phase 3)\nNext: x\n")
        found = self.check(branch="work", main="main")
        self.assertIn("orphan handoff: '### Handoff: done (Phase 3)' — branch done is gone or merged; "
                      "remove the block", found)

    def test_handoff_of_a_live_branch_or_without_name_is_silent(self):
        git(self.root, "checkout", "-qb", "live")
        (self.root / "x.txt").write_text("x\n")
        git(self.root, "add", "x.txt")
        git(self.root, "commit", "-qm", "work")
        git(self.root, "checkout", "-q", "main")
        (self.root / "STATE.md").write_text("# State\n\n## Handoff - live\nNext: x\n\n## Handoff\nNext: y\n")
        self.assertEqual(self.check(main="main"), [])

    def test_long_handoff_limit(self):
        for n, expect in ((8, False), (9, True)):
            body = "".join(f"- line {i}\n\n" for i in range(n))
            (self.root / "STATE.md").write_text(f"# State\n\n## Handoff — main\n{body}### Sub\nmore\n\n## Next\nz\n")
            found = [f for f in self.check() if f.startswith("long handoff:")]
            if n == 8:
                # the ### Sub section belongs to the handoff: 8 + heading + 1 line = 10
                self.assertEqual(found, ["long handoff: '## Handoff — main' has 10 lines (limit 8) — "
                                         "keep only position, next step, open points"])
            body = "".join(f"- line {i}\n" for i in range(n))
            (self.root / "STATE.md").write_text(f"# State\n\n## Handoff — main\n{body}\n## Next\nz\n")
            found = [f for f in self.check() if f.startswith("long handoff:")]
            self.assertEqual(bool(found), expect, found)
            if expect:
                self.assertEqual(found, [f"long handoff: '## Handoff — main' has {n} lines (limit 8) — "
                                         "keep only position, next step, open points"])

    def test_checkout_behind_its_upstream_is_reported(self):
        remote = self.root.parent / (self.root.name + "-remote.git")
        git(self.root, "init", "-q", "--bare", str(remote))
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(remote)]))
        git(self.root, "remote", "add", "origin", str(remote))
        git(self.root, "push", "-q", "-u", "origin", "main")
        self.assertEqual(self.check(main="origin/main"), [])
        (self.root / "x.txt").write_text("x\n")
        git(self.root, "add", "x.txt")
        git(self.root, "commit", "-qm", "a")
        (self.root / "y.txt").write_text("y\n")
        git(self.root, "add", "y.txt")
        git(self.root, "commit", "-qm", "b")
        git(self.root, "push", "-q", "origin", "main")
        git(self.root, "reset", "-q", "--hard", "HEAD~2")
        found = self.check(main="origin/main")
        self.assertIn("behind: main is 2 commits behind origin/main — pull before trusting ROADMAP/STATE here",
                      found)

    def test_no_upstream_is_silent(self):
        self.assertFalse(any(f.startswith("behind:") for f in self.check()))

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

    # --- phase files (.dev/phase-<N>.md) ---

    def test_phase_file_parsed(self):
        self.phase_file("6a", "feat/x", "\n## Quality Gate — Phase 6a: Export\n- [ ] a\n\n## Handoff\nNext: b\n")
        files = sc.phase_files(self.root)
        self.assertEqual(files["6a"], {"path": ".dev/phase-6a.md", "branch": "feat/x",
                                       "sections": ["## Quality Gate — Phase 6a: Export", "## Handoff"]})
        self.assertEqual(files["3"]["branch"], "main")
        self.assertEqual(sorted(files), ["3", "6a"])

    def test_phase_file_without_branch_line_is_invalid(self):
        self.phase_file("3", None, "## Quality Gate — Phase 3: Login\n")
        self.assertIsNone(sc.phase_files(self.root)["3"]["branch"])
        self.assertIn("phase file invalid: .dev/phase-3.md has no 'Branch:' first line", self.check())

    def test_orphan_phase_file_branch_gone(self):
        self.phase_file("4", "feature/gone")
        self.assertIn("orphan phase file: .dev/phase-4.md — branch feature/gone is gone or Phase 4 is done "
                      "on main; archive its gate summary and delete it", self.check(main="main"))

    def test_orphan_phase_file_done_on_main_after_squash(self):
        git(self.root, "checkout", "-qb", "work")
        road = self.root / "ROADMAP.md"
        road.write_text(road.read_text().replace("- [ ] Phase 4 — Export @type:backend",
                                                 "- [~] Phase 4 — Export @type:backend @claim:work@2026-10-06"))
        self.phase_file("4", "work", "\n## Quality Gate — Phase 4: Export\n")
        (self.root / "export.txt").write_text("x\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "phase 4")
        git(self.root, "checkout", "-q", "main")
        # squash merge: the content arrives on main as a new commit, work is no ancestor of main
        git(self.root, "merge", "-q", "--squash", "work")
        road.write_text(road.read_text().replace("- [~] Phase 4 — Export @type:backend @claim:work@2026-10-06",
                                                 "- [x] Phase 4 — Export @type:backend"))
        (self.root / ".dev" / "phase-4.md").unlink()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Phase 4 (squash)")
        git(self.root, "checkout", "-q", "work")
        self.assertFalse(sc.is_ancestor(self.root, "work", "main"))
        found = self.check(branch="work", main="main")
        self.assertIn("orphan phase file: .dev/phase-4.md — branch work is gone or Phase 4 is done on main; "
                      "archive its gate summary and delete it", found)
        self.assertFalse(any(f.startswith("phase file missing") for f in found), found)

    def test_phase_id_with_letter_is_exact(self):
        self.write(claim3="@claim:main@2026-10-06",
                   roadmap=ROADMAP.replace("- [ ] Phase 4 — Export", "- [~] Phase 312a — Export @claim:main@2026-10-06"))
        self.phase_file("312", "main")
        self.assertNotIn("312a", sc.phase_files(self.root))
        self.assertIn("phase file missing: Phase 312a [~] claimed by this branch has no .dev/phase-312a.md",
                      self.check())
        self.phase_file("312a", "main")
        self.phase_file("312a-old", "main")  # not a phase id: '-' is outside [0-9A-Za-z.]
        files = sc.phase_files(self.root)
        self.assertEqual(sorted(files), ["3", "312", "312a"])
        self.assertEqual(files["312a"]["path"], ".dev/phase-312a.md")
        self.assertFalse(any("312a" in f for f in self.check()), self.check())

    def test_missing_phase_file_for_own_claim(self):
        (self.root / ".dev" / "phase-3.md").unlink()
        self.assertEqual(self.check(), ["phase file missing: Phase 3 [~] claimed by this branch has no .dev/phase-3.md"])
        git(self.root, "branch", "session/b")
        self.write(claim3="@claim:session/b@2026-10-06")
        self.assertFalse(any(f.startswith("phase file missing") for f in self.check()))

    def test_branch_mismatch(self):
        git(self.root, "branch", "other")
        self.phase_file("3", "other")
        self.assertEqual(self.check(), ["branch mismatch: .dev/phase-3.md says other, claim says main"])

    # --- migrate ---

    LEGACY = ("# State\n\n## Current Position\nPhase 3 gate pending.\n\n## Progress\n- Phase 1 done.\n\n"
              "## Phases\n\n### Phase 3: Login\nNotes on login.\n\n### Phase 4: Export\nNot started.\n\n"
              "## Quality Gate — Phase 3: Login\n- [x] Step A — 5 passed @abc1234\n\n"
              "## CI in background\n- 1a2b3c4 — Phase 3 Login: in_progress\n- 9f8e7d6 — Phase 1 Database: success\n\n"
              "### Gate summary — Phase 1: Database\n- Tier: small\n\n## Blockers & Risks\nNone.\n\n"
              "## Session Continuity\nStopped at Step B.\n")

    def tree(self):
        return {str(p.relative_to(self.root)): p.read_text() for p in self.root.rglob("*")
                if p.is_file() and ".git" not in p.parts}

    def test_migrate_dry_run_writes_nothing(self):
        (self.root / "STATE.md").write_text(self.LEGACY)
        before = self.tree()
        rc, out = self.migrate(dry_run=True)
        self.assertEqual(rc, 0)
        self.assertEqual(self.tree(), before)
        self.assertTrue(any("Quality Gate — Phase 3" in l and ".dev/phase-3.md" in l for l in out), out)

    def test_migrate_moves_sections_and_keeps_words(self):
        (self.root / "STATE.md").write_text(self.LEGACY)
        targets = [".dev/phase-3.md", "docs/gates/phase-1.md", "docs/roadmap-archive/state-2026-10-07.md"]
        count = lambda: sum(sc.words((self.root / p).read_text()) for p in ["STATE.md", *targets]
                            if (self.root / p).is_file())
        before = count()
        rc, out = self.migrate()
        self.assertEqual(rc, 0)
        self.assertGreaterEqual(count(), before)
        phase = (self.root / ".dev/phase-3.md").read_text()
        self.assertEqual(phase.splitlines()[0], "Branch: main")
        self.assertEqual(phase.count("Branch:"), 1)  # existing target is extended, not overwritten
        for part in ("## Quality Gate — Phase 3: Login", "### Phase 3: Login", "- 1a2b3c4 — Phase 3 Login: in_progress"):
            self.assertIn(part, phase)
        gate = (self.root / "docs/gates/phase-1.md").read_text()
        self.assertIn("### Gate summary — Phase 1: Database", gate)
        self.assertIn("- 9f8e7d6 — Phase 1 Database: success", gate)
        arch = (self.root / "docs/roadmap-archive/state-2026-10-07.md").read_text()
        for part in ("## Current Position", "## Progress", "## Session Continuity", "Stopped at Step B."):
            self.assertIn(part, arch)
        state = (self.root / "STATE.md").read_text()
        for part in ("## Blockers & Risks", "### Phase 4: Export", "## CI in background"):
            self.assertIn(part, state)
        for part in ("Quality Gate", "Gate summary", "### Phase 3", "1a2b3c4", "Current Position", "Session Continuity"):
            self.assertNotIn(part, state)
        self.assertIn("kept: '### Phase 4: Export' (no claimed phase)", out)
        self.assertFalse(any(f.startswith("migrate:") for f in self.check()), self.check())
        # a second run extends nothing twice
        rc, out = self.migrate()
        self.assertEqual((self.root / ".dev/phase-3.md").read_text(), phase)

    def test_migrate_nested_gate_summary_keeps_its_target(self):
        (self.root / "STATE.md").write_text("# State\n\n## Quality Gate — Phase 3: Login\n- [ ] a\n\n"
                                            "### Gate summary — Phase 1: Database\n- Tier: small\n\n"
                                            "#### Gate summary — Phase 1: Database (old)\n- Tier: tiny\n\n"
                                            "## Blockers & Risks\nNone.\n")
        self.migrate()
        self.assertIn("- [ ] a", (self.root / ".dev/phase-3.md").read_text())
        gate = (self.root / "docs/gates/phase-1.md").read_text()
        self.assertIn("- Tier: small", gate)
        self.assertIn("- Tier: tiny", gate)
        self.assertNotIn("Gate summary", (self.root / ".dev/phase-3.md").read_text())
        self.assertEqual((self.root / "STATE.md").read_text(), "# State\n\n## Blockers & Risks\nNone.\n")

    def test_legacy_project_without_dev_dir_has_no_missing_finding(self):
        import shutil
        shutil.rmtree(self.root / ".dev")
        (self.root / "STATE.md").write_text("# State\n\n## Handoff — main\nNext: x\n\n"
                                            "## Quality Gate — Phase 3: Login\n- [ ] a\n")
        self.assertEqual(self.check(), ["migrate: STATE.md holds 1 phase sections — run state-check.py migrate --dry-run"])

    def test_migrate_creates_phase_file_for_own_claim_without_parts(self):
        import shutil
        shutil.rmtree(self.root / ".dev")
        (self.root / "STATE.md").write_text("# State\n\n## Blockers & Risks\nNone.\n")
        rc, out = self.migrate(dry_run=True)
        self.assertFalse((self.root / ".dev").exists())
        self.assertIn("would create: .dev/phase-3.md (Branch: main)", out)
        rc, out = self.migrate()
        self.assertEqual(rc, 0)
        self.assertEqual((self.root / ".dev/phase-3.md").read_text(), "Branch: main\n")
        self.assertIn("created: .dev/phase-3.md (Branch: main)", out)
        self.assertEqual(self.check(), [])
        # an existing phase file is left as it is
        (self.root / ".dev/phase-3.md").write_text("Branch: main\n\n## Handoff\nNext: z\n")
        self.migrate()
        self.assertEqual((self.root / ".dev/phase-3.md").read_text(), "Branch: main\n\n## Handoff\nNext: z\n")

    def test_migrate_create_with_other_moves_keeps_own_branch(self):
        import shutil
        shutil.rmtree(self.root / ".dev")
        (self.root / "STATE.md").write_text("# State\n\n### Gate summary — Phase 1: Database\n- Tier: small\n")
        rc, out = self.migrate()
        self.assertEqual(rc, 0)
        self.assertIn("created: .dev/phase-3.md (Branch: main)", out)
        self.assertEqual((self.root / ".dev/phase-3.md").read_text().splitlines()[0], "Branch: main")
        self.assertTrue((self.root / "docs/gates/phase-1.md").is_file())
        found = self.check()
        self.assertFalse(any(f.startswith(("phase file invalid", "phase file missing")) for f in found), found)

    def test_migrate_leaves_foreign_claims_in_state(self):
        git(self.root, "branch", "session/b")
        self.write(claim3="@claim:session/b@2026-10-06")
        legacy = ("# State\n\n## Handoff — session/b\nNext: Step B.\n\n"
                  "## Quality Gate — Phase 3: Login\n- [ ] a\n\n"
                  "## CI in background\n- 1a2b3c4 — Phase 3 Login: in_progress\n- 9f8e7d6 — Phase 1 Database: success\n\n"
                  "### Gate summary — Phase 1: Database\n- Tier: small\n")
        (self.root / "STATE.md").write_text(legacy)
        rc, out = self.migrate(branch="main")
        self.assertEqual(rc, 0)
        self.assertFalse((self.root / ".dev/phase-3.md").exists())
        state = (self.root / "STATE.md").read_text()
        for part in ("## Handoff — session/b", "## Quality Gate — Phase 3: Login", "- 1a2b3c4 — Phase 3 Login"):
            self.assertIn(part, state)
        self.assertNotIn("Gate summary", state)
        self.assertNotIn("9f8e7d6", state)
        gate = (self.root / "docs/gates/phase-1.md").read_text()
        self.assertIn("- 9f8e7d6 — Phase 1 Database: success", gate)
        for head in ("## Handoff — session/b", "## Quality Gate — Phase 3: Login",
                     "- 1a2b3c4 — Phase 3 Login: in_progress"):
            self.assertIn(f"kept: '{head}' (claimed by session/b)", out)
        # check on main does not push the foreign phase's parts into migrate:
        self.assertFalse(any(f.startswith("migrate:") for f in self.check()), self.check())

    def test_migrate_handoff_follows_claim(self):
        git(self.root, "branch", "session/b")
        self.write(claim3="@claim:session/b@2026-10-06")
        (self.root / "STATE.md").write_text("# State\n\n## Handoff — session/b\nNext: Step B.\n\n"
                                            "## Handoff — feature/none\nNext: y.\n")
        rc, out = self.migrate(branch="session/b")
        self.assertEqual(rc, 0)
        phase = (self.root / ".dev/phase-3.md").read_text()
        self.assertEqual(phase.splitlines()[0], "Branch: session/b")
        self.assertIn("## Handoff — session/b\nNext: Step B.", phase)
        state = (self.root / "STATE.md").read_text()
        self.assertNotIn("session/b", state)
        self.assertIn("## Handoff — feature/none", state)
        self.assertIn("kept: '## Handoff — feature/none' (no claimed phase)", out)

    def test_check_reports_migrate_for_legacy_state(self):
        (self.root / "STATE.md").write_text("# State\n\n## Handoff — main\nNext: x\n\n"
                                            "## Quality Gate — Phase 3: Login\n- [ ] a\n\n"
                                            "### Gate summary — Phase 1: Database\n- Tier: small\n")
        self.assertEqual(self.check(), ["migrate: STATE.md holds 2 phase sections — run state-check.py migrate --dry-run"])

    def test_monorepo_subdir(self):
        app = self.root / "apps" / "web"
        app.mkdir(parents=True)
        (app / "ROADMAP.md").write_text(ROADMAP.format(claim3="@claim:main@2026-10-06"))
        self.phase_file("3", "main", root=app)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "app")
        git(self.root, "checkout", "-qb", "work")
        road = app / "ROADMAP.md"
        road.write_text(road.read_text().replace("- [ ] Phase 4 — Export @type:backend",
                                                 "- [~] Phase 4 — Export @type:backend @claim:work@2026-10-06"))
        self.phase_file("4", "work", root=app)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "claim 4")
        git(self.root, "checkout", "-q", "main")
        road.write_text(road.read_text().replace("- [ ] Phase 4", "- [x] Phase 4"))
        git(self.root, "commit", "-qam", "Phase 4 done")
        git(self.root, "checkout", "-q", "work")
        self.assertEqual(sorted(sc.phase_files(app)), ["3", "4"])
        found = sc.check(app, main="main", branch="work", today=TODAY)
        self.assertIn("orphan phase file: .dev/phase-4.md — branch work is gone or Phase 4 is done on main; "
                      "archive its gate summary and delete it", found)
        (app / "STATE.md").write_text("# State\n\n### Gate summary — Phase 1: Database\n- Tier: small\n")
        self.assertEqual(sc.migrate(app, today=TODAY), 0)
        self.assertTrue((app / "docs/gates/phase-1.md").is_file())
        self.assertFalse((self.root / "docs").exists())

    def test_cli_migrate_dry_run(self):
        (self.root / "STATE.md").write_text(self.LEGACY)
        r = subprocess.run([sys.executable, str(SCRIPT), "migrate", "--root", str(self.root), "--dry-run",
                            "--branch", "main"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(".dev/phase-3.md", r.stdout)
        self.assertEqual((self.root / "STATE.md").read_text(), self.LEGACY)


if __name__ == "__main__":
    unittest.main()
