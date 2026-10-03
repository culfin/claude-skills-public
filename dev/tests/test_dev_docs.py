# dev/tests/test_dev_docs.py
"""Cross-file consistency of the /dev skill text that no other test covers."""
import re
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]


def text(rel):
    return (DEV / rel).read_text()


class DevDocsTests(unittest.TestCase):
    def test_every_referenced_analyzer_exists(self):
        for f in ("gate.md", "SKILL.md", "commands.md", "dev-check.md", "execution.md"):
            p = DEV / f
            if not p.exists():
                continue
            for ref in re.findall(r"analyzers/([a-z0-9-]+\.md)", p.read_text()):
                self.assertTrue((DEV / "analyzers" / ref).exists(), f"{f} -> analyzers/{ref}")

    def test_gate_fast_is_gone(self):
        for p in DEV.rglob("*.md"):
            self.assertNotIn("@gate: " + "fast", p.read_text(), str(p.relative_to(DEV)))

    def test_checklist_names(self):
        g = text("gate.md")
        for name in ("Diff review", "Spec checker", "Fix review", "Similar-bugs scan",
                     "Typecheck + lint + tests", "Production Build", "E2E Tests",
                     "Gate summary (STATE.md)", "Gate commit"):
            self.assertIn(f"- [ ] {name}", g)
        for name in ("Security review", "Tech-Stack Review: <stack id>", "Performance review",
                     "Accessibility review", "Design detector", "Motion review", "Taste pre-flight"):
            self.assertIn(f"- [ ] {name}", g)
        for old in ("- [ ] /simplify", "- [ ] Change review", "- [ ] Bug hunt", "- [ ] CI status check"):
            self.assertNotIn(old, g)

    def test_every_dispatched_role_has_a_model(self):
        m = text("models.md").lower()
        for role in ("diff review", "spec checker", "security review", "performance review",
                     "tech-stack review", "accessibility review", "similar-bugs", "fix agent",
                     "fix review", "implementer", "task review", "milestone"):
            self.assertIn(role, m, role)

    def test_security_review_ignores_the_tier(self):
        g = text("gate.md")
        t = text("tech-stack-triggers.md")
        self.assertIn("either tier**, whenever its trigger matrix", g)
        self.assertIn("Security Review runs in either tier", t)
        self.assertIn("| A | Security review | Either tier, when the security trigger matrix matches", text("dev-check.md"))

    def test_diff_review_is_self_contained(self):
        d = text("analyzers/diff-review.md")
        self.assertIn("## Sweep", d)
        self.assertNotIn("analyzers/bugs.md", d)

    def test_gate_uses_the_scripts(self):
        g = text("gate.md")
        for s in ("gate-tier.py", "ci-watch.sh", "check-evidence.py"):
            self.assertIn(s, g)

    def test_skill_md_has_no_confirmation_stops(self):
        s = text("SKILL.md")
        self.assertNotIn("AskUserQuestion: Start next phase", s)
        self.assertIn("execution.md", s)
        self.assertLess(len(s.splitlines()), 400)

    def test_skill_md_agrees_with_gate(self):
        s = text("SKILL.md")
        for old in ("5a–5k", "5c-v", "[ ] /simplify", "CI status check", "Change review",
                    "Invoke `verification-before-completion`"):
            self.assertNotIn(old, s, old)

    def test_execution_uses_scripts_and_limits(self):
        e = text("execution.md")
        for s in ("waves.py", "load-ok.sh", "isolation", "at most 3", "task-reviewer-prompt.md"):
            self.assertIn(s, e)

    def test_run_blocks_in_state_and_befragung(self):
        st = text("state.md")
        for s in ("## Handoff", "## CI in background", "Decisions:"):
            self.assertIn(s, st, s)
        self.assertIn("## Bundled round at run start", text("befragung.md"))


if __name__ == "__main__":
    unittest.main()
