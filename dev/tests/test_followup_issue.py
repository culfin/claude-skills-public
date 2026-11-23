"""followup-issue.py files slim-gate findings as deduplicated `followup` issues (fake gh on PATH)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "followup-issue.py"
FAKE = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["GH_LOG"], "a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
cmd = sys.argv[1:3]
if cmd == ["issue", "list"]:
    print(os.environ.get("GH_LIST", "[]"))
elif cmd == ["label", "create"]:
    if sys.argv[3] in os.environ.get("GH_LABELS", "").split(","):
        sys.stderr.write("label already exists\\n"); sys.exit(1)
elif cmd == ["issue", "create"]:
    print("https://github.com/o/r/issues/7")
"""


class FollowupIssueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        (d / "bin").mkdir()
        (d / "bin" / "gh").write_text(FAKE)
        (d / "bin" / "gh").chmod(0o755)
        self.log = d / "log"
        self.body = d / "body.md"
        self.body.write_text("finding, src/a.ts:3, phase 7\n")
        self.env = dict(os.environ, PATH=f"{d / 'bin'}{os.pathsep}{os.environ['PATH']}", GH_LOG=str(self.log))

    def tearDown(self):
        self.tmp.cleanup()

    def run_it(self, **env):
        out = subprocess.run([sys.executable, str(SCRIPT), "--severity", "medium", "--title",
                              "src/pdf.ts: totals rounded wrong", "--body-file", str(self.body)],
                             capture_output=True, text=True, env=dict(self.env, **env))
        calls = [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []
        return out.returncode, out.stdout.strip(), calls

    def test_new_finding_creates_labels_and_issue(self):
        rc, out, calls = self.run_it(GH_LABELS="followup")
        self.assertEqual((rc, out), (0, "filed: https://github.com/o/r/issues/7"))
        self.assertEqual(calls[0][:2], ["issue", "list"])
        self.assertIn(["label", "create", "severity:medium", "--color", "fbca04"], calls)
        create = next(c for c in calls if c[:2] == ["issue", "create"])
        self.assertEqual(create[create.index("--label") + 1], "followup")
        self.assertIn("severity:medium", create)

    def test_open_followup_on_same_file_gets_a_comment(self):
        rc, out, calls = self.run_it(GH_LIST=json.dumps([{"number": 4, "title": "src/other.ts: x"},
                                                         {"number": 5, "title": "src/pdf.ts: rounding"}]))
        self.assertEqual((rc, out), (0, "commented: #5"))
        self.assertFalse(any(c[:2] == ["issue", "create"] for c in calls))

    def test_search_uses_the_file_and_a_higher_severity_relabels(self):
        rc, out, calls = self.run_it(GH_LIST=json.dumps([{"number": 5, "title": "src/pdf.ts: rounding",
                                                          "labels": [{"name": "followup"}, {"name": "severity:low"}]}]))
        self.assertEqual((rc, out), (0, "commented: #5"))
        search = calls[0][calls[0].index("--search") + 1]
        self.assertEqual(search, '"src/pdf.ts" in:title')
        self.assertIn(["issue", "edit", "5", "--add-label", "severity:medium", "--remove-label", "severity:low"], calls)
        self.log.unlink()
        rc, out, calls = self.run_it(GH_LIST=json.dumps([{"number": 5, "title": "src/pdf.ts: rounding",
                                                          "labels": [{"name": "severity:high"}]}]))
        self.assertFalse(any(c[:2] == ["issue", "edit"] for c in calls))

    def test_without_gh_not_filed(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "--severity", "low", "--title", "a: b",
                              "--body-file", str(self.body)], capture_output=True, text=True,
                             env=dict(self.env, PATH="/nonexistent"))
        self.assertEqual(out.returncode, 3)
        self.assertTrue(out.stdout.startswith("not filed:"))


if __name__ == "__main__":
    unittest.main()
