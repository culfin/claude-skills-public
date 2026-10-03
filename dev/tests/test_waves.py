"""waves.py groups plan tasks into waves that may run in parallel."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "waves.py"


def run(spec):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(spec, fh)
    p = subprocess.run([sys.executable, str(SCRIPT), fh.name], capture_output=True, text=True)
    Path(fh.name).unlink()
    return p.returncode, (json.loads(p.stdout) if p.returncode == 0 else None), p.stderr


def t(i, files, after=()):
    return {"id": i, "files": list(files), "after": list(after)}


class WavesTests(unittest.TestCase):
    def test_independent_tasks_share_a_wave(self):
        rc, out, _ = run({"tasks": [t("1", ["a.py"]), t("2", ["b.py"]), t("3", ["c.py"])]})
        self.assertEqual(out["waves"], [["1", "2", "3"]])

    def test_shared_file_split(self):
        rc, out, _ = run({"tasks": [t("1", ["a.py"]), t("2", ["a.py", "b.py"]), t("3", ["c.py"])]})
        self.assertEqual(out["waves"], [["1", "3"], ["2"]])

    def test_dependency_goes_to_later_wave(self):
        rc, out, _ = run({"tasks": [t("1", ["a.py"]), t("2", ["b.py"], after=["1"])]})
        self.assertEqual(out["waves"], [["1"], ["2"]])

    def test_max_five_per_wave(self):
        tasks = [t(str(i), [f"f{i}.py"]) for i in range(7)]
        rc, out, _ = run({"max": 9, "tasks": tasks})
        self.assertEqual([len(w) for w in out["waves"]], [5, 2])

    def test_serial_task_alone(self):
        for f in ("package.json", "pnpm-lock.yaml", "Cargo.lock", "db/migrations/2_x.sql", "go.sum", "uv.lock"):
            with self.subTest(f=f):
                rc, out, _ = run({"tasks": [t("1", ["a.py"]), t("2", [f]), t("3", ["c.py"])]})
                self.assertIn(["2"], out["waves"])
                self.assertEqual(out["serial"], ["2"])
                self.assertTrue(all(len(w) == 1 for w in out["waves"] if "2" in w))

    def test_cycle_exits_2(self):
        rc, out, err = run({"tasks": [t("1", ["a"], after=["2"]), t("2", ["b"], after=["1"])]})
        self.assertEqual(rc, 2)
        self.assertIn("cycle", err)

    def test_unknown_dependency_exits_2(self):
        rc, out, err = run({"tasks": [t("1", ["a"], after=["9"])]})
        self.assertEqual(rc, 2)

    def test_task_without_files_runs_alone(self):
        # unknown file set = cannot prove independence
        rc, out, _ = run({"tasks": [t("1", []), t("2", ["b.py"])]})
        self.assertEqual(out["waves"], [["1"], ["2"]])


if __name__ == "__main__":
    unittest.main()
