#!/usr/bin/env python3
"""Files one gate finding as a GitHub follow-up issue (slim gate, gate-slim.md), deduplicated.

    followup-issue.py --severity <low|medium|high> --title "<file>: <defect>" --body-file <file>

Searches the open issues labelled `followup` for the title's file part. An open follow-up whose title
starts with the same `<file>:` gets a comment with the body instead of a new issue (and the new
severity label when it is higher). Otherwise the
labels `followup` and `severity:<s>` are created if missing and the issue is opened.

Prints `filed: <url>` or `commented: #<n>`. Exit 0 = done, 2 = usage, 3 = not filed (no `gh`, no
GitHub remote, gh failed): the message after `not filed:` goes into the gate summary.
"""
import argparse
import json
import shutil
import subprocess
import sys

RANK = {"low": 1, "medium": 2, "high": 3}
COLORS = {"followup": "c5def5", "severity:low": "0e8a16", "severity:medium": "fbca04", "severity:high": "b60205"}


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--severity", required=True, choices=("low", "medium", "high"))
    ap.add_argument("--title", required=True)
    ap.add_argument("--body-file", required=True)
    a = ap.parse_args()
    if not shutil.which("gh"):
        print("not filed: gh not installed")
        return 3
    prefix = a.title.split(":", 1)[0].strip().lower() + ":" if ":" in a.title else None
    # Search for the file only: GitHub search needs every word, so the defect text would hide a twin.
    query = f'"{a.title.split(":", 1)[0].strip()}" in:title' if prefix else f"{a.title} in:title"
    found = gh("issue", "list", "--label", "followup", "--state", "open", "--limit", "50",
               "--search", query, "--json", "number,title,labels")
    if found.returncode != 0:
        # No `followup` label yet is not an error: then there is nothing to dedupe against.
        if "not found" not in found.stderr.lower():
            print(f"not filed: gh issue list failed: {found.stderr.strip()}")
            return 3
        hits = []
    else:
        hits = json.loads(found.stdout or "[]")
    for hit in hits:
        if prefix and hit["title"].strip().lower().startswith(prefix):
            done = gh("issue", "comment", str(hit["number"]), "--body-file", a.body_file)
            if done.returncode != 0:
                print(f"not filed: gh issue comment failed: {done.stderr.strip()}")
                return 3
            have = [l["name"].split(":", 1)[1] for l in hit.get("labels", []) if l["name"].startswith("severity:")]
            if all(RANK[a.severity] > RANK.get(h, 0) for h in have):
                # A more serious twin raises the issue's severity; failing to relabel still keeps the comment.
                gh("label", "create", f"severity:{a.severity}", "--color", COLORS[f"severity:{a.severity}"])
                gh("issue", "edit", str(hit["number"]), "--add-label", f"severity:{a.severity}",
                   *[x for h in have for x in ("--remove-label", f"severity:{h}")])
            print(f"commented: #{hit['number']}")
            return 0
    labels = ("followup", f"severity:{a.severity}")
    for label in labels:
        made = gh("label", "create", label, "--color", COLORS[label])
        if made.returncode != 0 and "already exists" not in made.stderr.lower():
            print(f"not filed: gh label create {label} failed: {made.stderr.strip()}")
            return 3
    done = gh("issue", "create", "--title", a.title, "--label", labels[0], "--label", labels[1],
              "--body-file", a.body_file)
    if done.returncode != 0:
        print(f"not filed: gh issue create failed: {done.stderr.strip()}")
        return 3
    print(f"filed: {done.stdout.strip().splitlines()[-1] if done.stdout.strip() else '?'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
