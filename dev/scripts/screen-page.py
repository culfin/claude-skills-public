#!/usr/bin/env python3
"""Wraps a screen fragment (companion-screens.md building blocks) into a self-contained HTML page.

    python3 screen-page.py FRAGMENT.html [--name NAME] [--dir DIR]

Writes DIR/NAME.html (DIR default: ${TMPDIR:-/tmp}/dev-screens/<repo name>/, outside the repo; NAME
default: the fragment's file name) and prints its absolute path. Relative <img src> paths become absolute
(resolved next to the fragment), so html_preview/html_render inline them. Colours follow the T3 theme
variables (html_render's base sheet); the :where(:root) fallbacks apply only where no theme sets them
(a static file opened in a browser). No background on html/body, no outer card: html_render's frame rules.
"""
import argparse
import os
import re
import subprocess
import sys

STYLE = """
:where(:root) { --background:#fff; --foreground:#1d1d1f; --card:#f5f5f7; --secondary:#e5e5e7;
  --muted-foreground:#6e6e73; --border:#d1d1d6; --primary:#0a66d8; --destructive:#c4161c;
  --success:#1f8a3b; --warning:#b25e00; --radius:8px;
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
@media (prefers-color-scheme: dark) { :where(:root) { --background:#1c1c1e; --foreground:#f5f5f7;
  --card:#2c2c2e; --secondary:#3a3a3c; --muted-foreground:#a1a1a6; --border:#48484a; --primary:#3d8bff;
  --destructive:#ff6961; --success:#4cd964; --warning:#ffb340; } }
:root { --accent: var(--primary); --error: var(--destructive); --bg-secondary: var(--card);
  --bg-tertiary: var(--secondary); --text-secondary: var(--muted-foreground);
  --text-tertiary: var(--muted-foreground); }
body { font-family: var(--font-sans); color: var(--foreground); margin: 0; line-height: 1.45; }
h2 { font-size: 1.25rem; font-weight: 600; margin: 0 0 .4rem; }
h3 { font-size: 1rem; margin: 0 0 .25rem; }
.subtitle { color: var(--text-secondary); margin: 0 0 1rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
.card { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: var(--bg-secondary); }
.card-image { background: var(--bg-tertiary); aspect-ratio: 16/10; display: flex; align-items: center; justify-content: center; }
.card-body { padding: 1rem; }
.card-body p { color: var(--text-secondary); font-size: .85rem; margin: 0; }
.mockup { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; margin-bottom: 1rem; }
.mockup-header { background: var(--bg-tertiary); padding: .5rem 1rem; font-size: .8rem; font-weight: 600; color: var(--text-secondary); }
.mockup-body { padding: 1rem; }
.split { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }
.mock-content { padding: 1rem; flex: 1; }
.mock-button { background: var(--accent); color: #fff; border: none; padding: .45rem .9rem; border-radius: 6px; font-size: .85rem; }
img { max-width: 100%; }
"""

PAGE = '<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>{title}</title><style>{style}</style></head>\n<body>\n{body}\n</body></html>\n'


def repo_name(cwd):
    r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return os.path.basename(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else "screens"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fragment")
    ap.add_argument("--name")
    ap.add_argument("--dir")
    a = ap.parse_args()
    src = os.path.abspath(a.fragment)
    try:
        body = open(src, encoding="utf-8").read()
    except OSError as e:
        print(f"screen-page: cannot read {src}: {e}", file=sys.stderr)
        return 2
    if re.search(r"<html|<head", body, re.I):
        print("screen-page: pass a fragment (no <html>/<head>), not a page", file=sys.stderr)
        return 2
    base = os.path.dirname(src)

    def absolute(m):
        url = m.group(2)
        if re.match(r"^(?:[a-z][a-z0-9+.-]*:|/|#)", url, re.I):
            return m.group(0)
        return f'{m.group(1)}{os.path.normpath(os.path.join(base, url))}{m.group(3)}'

    body = re.sub(r'(<img\b[^>]*?\bsrc=")([^"]+)(")', absolute, body, flags=re.I)
    out_dir = a.dir or os.path.join(os.environ.get("TMPDIR", "/tmp"), "dev-screens", repo_name(os.getcwd()))
    os.makedirs(out_dir, exist_ok=True)
    name = a.name or os.path.splitext(os.path.basename(src))[0]
    title = re.search(r"<h2[^>]*>(.*?)</h2>", body, re.S)
    out = os.path.join(os.path.abspath(out_dir), f"{name}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(PAGE.format(title=re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else name,
                            style=STYLE, body=body))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
