"""Run shell test scripts via pytest."""
import subprocess
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent


class ShellScriptTests(unittest.TestCase):
    def test_load_ci_sh(self):
        """Run load/ci shell tests."""
        result = subprocess.run(
            ["bash", str(TEST_DIR / "test_load_ci.sh")],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            self.fail(f"test_load_ci.sh failed:\n{result.stdout}\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
