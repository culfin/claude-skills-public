#!/usr/bin/env python3
"""Collect every open Dependabot PR for one base; read-only, fail closed."""
import argparse
import json
import re
import subprocess
import sys


def collect(repo, base, run=subprocess.run):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not base:
        raise ValueError("A valid owner/repo and nonempty base are required")
    result = run(["gh", "api", f"repos/{repo}/pulls", "--method", "GET",
                  "--paginate", "--slurp", "-f", "state=open", "-f", f"base={base}",
                  "-f", "per_page=100"], check=True, capture_output=True, text=True)
    pages = json.loads(result.stdout)
    if not isinstance(pages, list) or any(not isinstance(p, list) for p in pages):
        raise ValueError("Unexpected paginated PR response")
    found = {}
    for page in pages:
        for pr in page:
            if not isinstance(pr, dict):
                raise ValueError("Invalid PR entry")
            if pr.get("state") != "open" or pr.get("base", {}).get("ref") != base:
                continue
            if pr.get("user", {}).get("login") != "dependabot[bot]":
                continue
            if not isinstance(pr.get("number"), int) or not pr.get("head", {}).get("sha"):
                raise ValueError("Incomplete Dependabot PR")
            number = pr["number"]
            if number in found and found[number]["head"]["sha"] != pr["head"]["sha"]:
                raise ValueError("PR changed while paginating; recollect")
            found[number] = pr
    return sorted(found.values(), key=lambda pr: pr["number"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.repo, args.base), indent=2))
    except (ValueError, subprocess.CalledProcessError, OSError) as exc:
        print(f"PR collection failed; coverage unknown: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
