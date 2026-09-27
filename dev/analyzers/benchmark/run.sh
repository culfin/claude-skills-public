#!/usr/bin/env bash
# run.sh — measure whether the analyzers find known bugs.
#
# Each case under cases/<name>/ holds code/ (copied to a temp dir and analyzed) and case.json
# (which analyzer, what the code should do, which defects must be found). The analyzer never sees
# case.json. A second, tool-less run judges the report against the expected defects.
#
# Usage: run.sh [--model sonnet] [--cases a,b] [--instructions f1.md,f2.md] [--out FILE]
#   --instructions  analyze with these files instead of CONTRACT.md + <analyzer>.md
#                   (to compare another set of instructions on the same cases)
#
# Isolation: every run starts in a fresh temp dir (no project memory, no CLAUDE.md of a project),
# without MCP servers and skills, with read-only tools. Needs the `claude` CLI and python3.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZERS="$(cd "$HERE/.." && pwd)"
MODEL=sonnet; ONLY=""; INSTR=""; OUT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="$2"; shift 2 ;;
        --cases) ONLY="$2"; shift 2 ;;
        --instructions) INSTR="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

field() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$1" "$2"; }

run_case() {
    local name="$1" dir="$HERE/cases/$1" work files analyzer requirement report verdict
    analyzer=$(field "$dir/case.json" analyzer)
    requirement=$(field "$dir/case.json" requirement)
    if [[ -n "$INSTR" ]]; then files=$(tr ',' '\n' <<< "$INSTR" | sed 's/^/- /')
    else files="- $ANALYZERS/CONTRACT.md
- $ANALYZERS/$analyzer.md"; fi
    work=$(mktemp -d); cp -R "$dir/code/." "$work/"

    report=$(cd "$work" && claude -p "You are a read-only code analyzer. Read these instruction files completely and follow them:
$files

Analyze the code in $work (mode: phase, scope: all files in the directory).
What the code is supposed to do: $requirement

Rules: only read the instruction files above and files in $work. Do not ask questions; skip any interactive, setup or report-to-disk parts of the instructions. Return findings as a markdown table (severity critical/note | where | finding | evidence) and end with \"Result: N critical, M notes\"." \
        --model "$MODEL" --strict-mcp-config --disable-slash-commands \
        --tools Read Grep Glob \
        < /dev/null 2>/dev/null)

    verdict=$(cd "$work" && claude -p "You judge a code-analysis report against known defects. For each expected defect, decide whether the report identifies the SAME defect: same place and same mechanism (a report of only a consequence, or a different bug on the same line, does not count). Answer with JSON only, one key per id, value \"critical\", \"note\" (found, but rated lower) or \"missed\".

Expected defects (JSON): $(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["expected"]))' "$dir/case.json")

Report:
$report" --model "$MODEL" --strict-mcp-config --disable-slash-commands --tools "" < /dev/null 2>/dev/null)
    rm -rf "$work"

    python3 - "$name" "$dir/case.json" "$verdict" <<'PY'
import json, re, sys
name, case, raw = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
m = re.search(r'\{.*\}', raw, re.S)
v = json.loads(m.group(0)) if m else {}
for e in case["expected"]:
    print(f"| {name} | {e['id']} | {e['origin']} | {v.get(e['id'], 'judge-error')} |")
PY
}

{
    echo "| Case | Defect | Origin | Verdict |"
    echo "|---|---|---|---|"
    for d in "$HERE"/cases/*/; do
        name=$(basename "$d")
        [[ -n "$ONLY" && ",$ONLY," != *",$name,"* ]] && continue
        run_case "$name" &
    done
    wait
} | tee ${OUT:+"$OUT"}
