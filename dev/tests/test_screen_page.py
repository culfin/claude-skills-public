"""screen-page.py wraps a screen fragment into a self-contained page that follows the T3 theme."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "screen-page.py"


class ScreenPageTests(unittest.TestCase):
    def run_page(self, body, *args):
        d = Path(tempfile.mkdtemp())
        (d / "src").mkdir()
        frag = d / "src" / "12-export.html"
        frag.write_text(body)
        r = subprocess.run([sys.executable, str(SCRIPT), str(frag), "--dir", str(d), *args],
                           capture_output=True, text=True)
        return r, d

    def test_wraps_fragment_with_theme_styles_and_absolute_images(self):
        r, d = self.run_page('<h2>Export <b>here</b></h2><img src="shot.png"><img src="https://x/y.png">')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = Path(r.stdout.strip())
        self.assertEqual(out, d / "12-export.html")
        page = out.read_text()
        self.assertIn("<title>Export here</title>", page)
        self.assertIn(f'src="{d / "src" / "shot.png"}"', page)
        self.assertIn('src="https://x/y.png"', page)
        self.assertIn(":where(:root)", page)          # fallbacks only where no theme sets them
        self.assertIn("--accent: var(--primary)", page)
        self.assertNotRegex(page, r"(?:html|body)\s*\{[^}]*background")  # html_render frame rule

    def test_refuses_a_full_page(self):
        r, _ = self.run_page("<html><body>x</body></html>")
        self.assertEqual(r.returncode, 2)

    def test_name_option(self):
        r, d = self.run_page("<h2>x</h2>", "--name", "other")
        self.assertEqual(Path(r.stdout.strip()), d / "other.html")


if __name__ == "__main__":
    unittest.main()
