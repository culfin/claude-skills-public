#!/usr/bin/env python3
"""Read one validated branch field. Missing file/keys use defaults; prod null disables promotion."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def read_config(path):
    path = Path(path)
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError("config must be an object")
    result = {"devBranch": data.get("devBranch", "main"), "prodBranch": data.get("prodBranch", "prod")}
    for key, value in result.items():
        if key == "prodBranch" and value is None:
            continue
        if not isinstance(value, str) or not value or value.startswith("-") or value == "HEAD" or "@{" in value:
            raise ValueError(f"invalid {key}")
        check = subprocess.run(["git", "check-ref-format", "--branch", value], capture_output=True)
        if check.returncode:
            raise ValueError(f"invalid {key}")
    if result["devBranch"] == result["prodBranch"]:
        raise ValueError("devBranch and prodBranch must differ")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("field", choices=("devBranch", "prodBranch"))
    parser.add_argument("--config", default=".deps/config.json")
    args = parser.parse_args()
    try:
        print(read_config(args.config)[args.field] or "")
    except (ValueError, OSError) as exc:
        print(f"Invalid dependency config: {exc}", file=sys.stderr)
        sys.exit(1)
