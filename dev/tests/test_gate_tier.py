"""gate-tier.py decides the gate tier from phase size, type and touched files."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gate-tier.py"


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


class GateTierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        (self.root / "app.py").write_text("x = 1\n")
        git(self.root, "add", "app.py")
        git(self.root, "commit", "-qm", "base")
        self.base = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def run_tier(self, *extra):
        out = subprocess.run([sys.executable, str(SCRIPT), "--base", self.base, "--root", str(self.root), *extra],
                             capture_output=True, text=True)
        return out.returncode, out.stdout.splitlines(), out.stderr

    def write(self, rel, lines):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(f"line {i}\n" for i in range(lines)))

    def test_small_change_is_small(self):
        self.write("app.py", 20)
        rc, out, _ = self.run_tier("--tasks", "2", "--type", "ui")
        self.assertEqual(rc, 0)
        self.assertEqual(out[0], "small")

    def test_too_many_lines_is_large(self):
        self.write("big.py", 401)          # untracked file counts
        rc, out, _ = self.run_tier("--tasks", "1")
        self.assertEqual(out[0], "large")
        self.assertTrue(any("lines" in r for r in out[1:]))

    def test_exactly_400_lines_is_small(self):
        self.write("big.py", 400)
        rc, out, _ = self.run_tier("--tasks", "1")
        self.assertEqual(out[0], "small")

    def test_too_many_tasks_is_large(self):
        self.write("app.py", 3)
        rc, out, _ = self.run_tier("--tasks", "4")
        self.assertEqual(out[0], "large")

    def test_risk_type_is_large(self):
        for t in ("auth", "security", "migration", "data"):
            with self.subTest(t=t):
                rc, out, _ = self.run_tier("--tasks", "1", "--type", t)
                self.assertEqual(out[0], "large")

    def test_backend_only_large_with_db_change(self):
        self.write("svc/handler.py", 5)
        self.assertEqual(self.run_tier("--tasks", "1", "--type", "backend")[1][0], "small")
        self.write("migrations/0002_add.sql", 5)
        self.assertEqual(self.run_tier("--tasks", "1", "--type", "backend")[1][0], "large")

    def test_sensitive_file_forces_large(self):
        for rel in ("src/auth/session.ts", "app/api/orders/route.ts", "db/migrations/1.sql",
                    "src/middleware.ts", "server/routes/login.py"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                rc, out, _ = self.run_tier("--tasks", "1", "--type", "ui")
                self.assertEqual(out[0], "large")
                (self.root / rel).unlink()

    def test_gate_full_forces_large(self):
        rc, out, _ = self.run_tier("--tasks", "1", "--gate", "full")
        self.assertEqual(out[0], "large")

    def test_bad_base_exits_2(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "--base", "nope", "--root", str(self.root)],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertEqual(out.stdout, "")


if __name__ == "__main__":
    unittest.main()
