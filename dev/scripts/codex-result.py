#!/usr/bin/env python3
"""Checks the final answer of a Codex review and writes it as an analyzer report. Writes only --out.

    codex-result.py check --schema <file> --result <file> --role <role> --out <file>
    codex-result.py model-schema --schema <file>

`check`: exit 0 = the answer is a usable review; --out then holds the findings table, a
`reviewer: codex` line and the `Result:` line of analyzers/CONTRACT.md. Exit 3 = unusable; one line
`fallback: <reason>` on stdout and --out is not written. Exit 2 = usage error.
`model-schema`: prints the schema for Codex's --output-schema without `minimum`/`minLength`, so the
model can still answer `files_read: 0` honestly instead of being forced into a made-up number; the
bounds are checked here.

Why a script: Codex has answered with exit 0 while saying "tool attempts timed out" and having read
nothing. Read as text, that looks like "no findings" and would pass a gate item that was never
checked. Here an answer counts only if it matches the schema, read at least one file, names no
blocking reason and carries evidence (file, line, quote, failing input) for every finding. The
`Result:` line is computed from the findings, not copied from the model.
"""
import argparse
import json
import re
import sys

TITLES = {"diff": "Diff review", "security": "Security review", "fix": "Fix review",
          "similar": "Similar bugs"}
# Phrases in the model's own summary that mean it did not get to look at the code.
UNVERIFIED = re.compile(r"timed? ?out|could(?: not|n't) (?:read|open|access|run)|unable to (?:read|open|access|run)"
                        r"|not able to (?:read|open|access)|nothing (?:was )?(?:read|checked)|no files? (?:were |was )?read"
                        r"|tool (?:attempts?|calls?) failed|sandbox (?:denied|blocked)", re.I)


def errors(value, schema, path="$"):
    """Minimal JSON Schema check for the keywords the review schema uses."""
    kind = schema.get("type")
    ok = {"object": isinstance(value, dict), "array": isinstance(value, list),
          "string": isinstance(value, str), "boolean": isinstance(value, bool),
          "integer": isinstance(value, int) and not isinstance(value, bool)}.get(kind, True)
    if not ok:
        return [f"{path} is not {kind}"]
    found = []
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{path} not in {schema['enum']}")
    if "minimum" in schema and value < schema["minimum"]:
        found.append(f"{path} < {schema['minimum']}")
    if "minLength" in schema and len(value.strip()) < schema["minLength"]:
        found.append(f"{path} is empty")
    if kind == "object":
        props = schema.get("properties", {})
        found += [f"{path}.{k} missing" for k in schema.get("required", []) if k not in value]
        if schema.get("additionalProperties") is False:
            found += [f"{path}.{k} not allowed" for k in value if k not in props]
        for k, sub in props.items():
            if k in value:
                found += errors(value[k], sub, f"{path}.{k}")
    if kind == "array":
        for i, item in enumerate(value):
            found += errors(item, schema["items"], f"{path}[{i}]")
    return found


def strip_bounds(node):
    if isinstance(node, dict):
        return {k: strip_bounds(v) for k, v in node.items() if k not in ("minimum", "minLength")}
    if isinstance(node, list):
        return [strip_bounds(v) for v in node]
    return node


def cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def report(answer, role):
    findings = answer["findings"]
    crit = sum(f["severity"] == "critical" for f in findings)
    result = f"{crit} critical, {len(findings) - crit} notes" if findings else "no findings"
    mode = "fix" if role == "fix" else "phase"
    lines = [f"### {TITLES[role]} (Codex) — {mode}", "", "reviewer: codex", "",
             f"Checked: {cell(answer['checked'])} (files read: {answer['files_read']})", ""]
    if findings:
        lines += ["| # | Severity | Where | Finding | Evidence | Fix |", "|---|---|---|---|---|---|"]
        for i, f in enumerate(sorted(findings, key=lambda f: f["severity"] != "critical"), 1):
            evidence = f"`{cell(f['quote'])}` — {cell(f['failing_input'])}"
            lines.append(f"| {i} | {f['severity']} | {cell(f['file'])}:{f['line']} | {cell(f['finding'])} "
                         f"| {evidence} | {cell(f['fix'])} |")
        lines.append("")
    lines.append(f"Result: {result}")
    return "\n".join(lines) + "\n"


def check(args):
    schema = json.load(open(args.schema))
    try:
        text = open(args.result, encoding="utf-8").read()
    except OSError:
        return "no answer file"
    if not text.strip():
        return "empty answer"
    try:
        answer = json.loads(text)
    except ValueError:
        return "answer is not JSON" + (" (says it could not check)" if UNVERIFIED.search(text) else "")
    if isinstance(answer, dict):
        if str(answer.get("blocked_reason", "")).strip():
            return "codex could not check: " + cell(answer["blocked_reason"])[:120]
        if isinstance(answer.get("checked"), str) and UNVERIFIED.search(answer["checked"]):
            return "codex could not check: " + cell(answer["checked"])[:120]
        if answer.get("files_read") == 0:
            return "codex read no files"
    problems = errors(answer, schema)
    if problems:
        return "answer does not match schema: " + "; ".join(problems[:3])
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report(answer, args.role))
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--schema", required=True)
    c.add_argument("--result", required=True)
    c.add_argument("--role", required=True, choices=sorted(TITLES))
    c.add_argument("--out", required=True)
    m = sub.add_parser("model-schema")
    m.add_argument("--schema", required=True)
    args = p.parse_args()
    if args.cmd == "model-schema":
        json.dump(strip_bounds(json.load(open(args.schema))), sys.stdout, indent=2)
        print()
        return 0
    reason = check(args)
    if reason:
        print(f"fallback: {reason}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
