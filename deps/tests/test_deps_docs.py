"""Guards for the /deps scan instructions."""
import unittest
from pathlib import Path

DEPS = Path(__file__).resolve().parent.parent


def text(name):
    return (DEPS / name).read_text()


class ScanDocTests(unittest.TestCase):
    def test_every_root_is_scanned(self):
        # 2026-11-17: a package root outside the workspace was skipped by the root scan.
        merge = text("references/merge.md")
        self.assertIn("**Every root** (pattern 36)", merge)
        self.assertIn("git ls-files '*pnpm-lock.yaml'", merge)
        self.assertIn("| 36 |", text("SKILL.md"))

    def test_pins_outside_package_json_are_grepped(self):
        merge = text("references/merge.md")
        self.assertIn("**Pins outside package.json** (pattern 37)", merge)
        for needle in ("corepack (prepare|use)", "^FROM node:", "action-setup@", ".nvmrc"):
            self.assertIn(needle, merge)
        self.assertIn("| 37 |", text("SKILL.md"))


if __name__ == "__main__":
    unittest.main()
