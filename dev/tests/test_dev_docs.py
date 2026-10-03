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
            self.assertNotIn("@gate: fast", p.read_text(), str(p.relative_to(DEV)))

    def test_checklist_names(self):
        g = text("gate.md")
        for name in ("Diff review", "Spec checker", "Fix review", "Similar-bugs scan",
                     "Typecheck + lint + tests", "Production Build", "E2E Tests",
                     "Gate summary (STATE.md)", "Gate commit"):
            self.assertIn(f"- [ ] {name}", g)
        for old in ("- [ ] /simplify", "- [ ] Change review", "- [ ] Bug hunt", "- [ ] CI status check"):
            self.assertNotIn(old, g)

    def test_every_dispatched_role_has_a_model(self):
        m = text("models.md").lower()
        for role in ("diff review", "spec checker", "security review", "performance review",
                     "tech-stack review", "accessibility review", "similar-bugs", "fix",
                     "fix review", "implementer", "task review", "milestone"):
            self.assertIn(role, m, role)

    def test_gate_uses_the_scripts(self):
        g = text("gate.md")
        for s in ("gate-tier.py", "ci-watch.sh", "check-evidence.py"):
            self.assertIn(s, g)


if __name__ == "__main__":
    unittest.main()
