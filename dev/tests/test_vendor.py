"""The vendored superpowers copy /dev runs on (vendor/README.md) is complete and checked."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parent.parent


class VendorTests(unittest.TestCase):
    def test_check_vendor_passes_on_the_repo(self):
        r = subprocess.run([sys.executable, str(DEV / "scripts/check-vendor.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(json.loads(r.stdout)["status"], "files-present")

    def test_check_vendor_blocks_a_missing_file(self):
        import shutil, tempfile
        d = Path(tempfile.mkdtemp())
        shutil.copytree(DEV / "vendor", d / "vendor")
        (d / "vendor/sdd/scripts/task-brief").unlink()
        r = subprocess.run([sys.executable, str(DEV / "scripts/check-vendor.py"), "--root", str(d)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("vendor/sdd/scripts/task-brief", json.loads(r.stdout)["missing"])

    def test_licence_and_provenance(self):
        self.assertIn("MIT License", (DEV / "vendor/LICENSE").read_text())
        self.assertIn("22f0b463e7a5e579904dd6211a520321035526f7", (DEV / "vendor/README.md").read_text())

    def test_no_superpowers_skill_call_outside_vendor(self):
        import re
        for f in DEV.rglob("*.md"):
            parts = f.relative_to(DEV).parts
            if {"vendor", "tests", "analyzers"} & set(parts):
                continue
            self.assertIsNone(re.search(r"superpowers:[a-z-]+", f.read_text()), f)

    def test_vendored_guide_is_not_a_skill_file(self):
        self.assertFalse((DEV / "vendor/sdd/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
