#!/usr/bin/env python3
"""Checks the vendored superpowers copy /dev runs on (vendor/README.md); read-only, no network.

    python3 check-vendor.py [--root DEV_DIR]

Prints JSON {"status": "files-present" | "blocked", "missing": [...]}; exit 0 when present, 1 when blocked.
"""
import argparse
import json
import os
import sys
from pathlib import Path

REQUIRED = ("vendor/LICENSE", "vendor/README.md", "vendor/brainstorming/builder-check-prompt.md",
            "vendor/sdd/GUIDE.md", "vendor/sdd/implementer-prompt.md", "vendor/sdd/task-reviewer-prompt.md",
            "vendor/sdd/re-review-prompt.md", "vendor/sdd/references/handling-reports.md")
SCRIPTS = ("vendor/sdd/scripts/task-brief", "vendor/sdd/scripts/review-package",
           "vendor/sdd/scripts/sdd-workspace", "vendor/sdd/scripts/sdd-repo")


def inspect(root):
    root = Path(root)
    missing = [p for p in REQUIRED + SCRIPTS if not (root / p).is_file()]
    missing += [f"{p} (not executable)" for p in SCRIPTS if (root / p).is_file() and not os.access(root / p, os.X_OK)]
    return {"status": "blocked" if missing else "files-present", "missing": missing}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    r = inspect(ap.parse_args().root)
    print(json.dumps(r))
    return 0 if r["status"] == "files-present" else 1


if __name__ == "__main__":
    sys.exit(main())
