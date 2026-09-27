#!/usr/bin/env bash
# run.sh — decision scenarios for the sentry skill (read-only, synthetic facts; not a live test).
#
# A fresh session gets only the skill, cases.json and prompt.txt and decides every case. A second
# session without tools compares each decision with criteria.json. The answering session never
# sees the criteria.
#
# Usage: run.sh [--model sonnet] [--out FILE]      (needs the `claude` CLI and python3)
# Codex: give the same prompt.txt, cases.json and a copy of the skill to a fresh read-only Codex
# session, save its JSON answer, then run: run.sh --judge-only <answer.json>
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(cd "$HERE/../.." && pwd)"
MODEL=sonnet; OUT=""; ANSWER=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --judge-only) ANSWER="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
mkdir -p "$work/sentry" "$work/host"
( cd "$SKILL" && tar cf - --exclude=tests . ) | ( cd "$work/sentry" && tar xf - )
cp "$HERE/cases.json" "$work/host/"
sed "s|SKILL_DIR|$work/sentry|" "$HERE/prompt.txt" > "$work/host/prompt.txt"

if [[ -z "$ANSWER" ]]; then
    ANSWER="$work/answer.txt"
    (cd "$work/host" && claude -p "$(cat prompt.txt)

The cases are in ./cases.json (current directory $work/host)." \
        --model "$MODEL" --strict-mcp-config --disable-slash-commands --tools Read Grep Glob \
        < /dev/null > "$ANSWER" 2>/dev/null)
fi

verdict=$(cd "$work" && claude -p "Judge decisions of a workflow skill against criteria. For each case id, answer
\"pass\" if decision, reason and next actions satisfy the criterion (same substance, wording may
differ; an extra unsupported claim or action is a fail), else \"fail: <one short reason>\".
Answer with JSON only: {\"<id>\": \"pass\" | \"fail: ...\"}.

Criteria: $(cat "$HERE/criteria.json")

Answers: $(cat "$ANSWER")" --model "$MODEL" --strict-mcp-config --disable-slash-commands --tools "" \
    < /dev/null 2>/dev/null)

python3 - "$HERE/criteria.json" "$verdict" <<'PY' | tee ${OUT:+"$OUT"}
import json, re, sys
crit = json.load(open(sys.argv[1]))
m = re.search(r"\{.*\}", sys.argv[2], re.S)
v = json.loads(m.group(0)) if m else {}
print("| Case | Verdict |\n|---|---|")
for cid in crit:
    print(f"| {cid} | {v.get(cid, 'judge-error')} |")
ok = sum(1 for c in crit if str(v.get(c, "")).startswith("pass"))
print(f"\n{ok} of {len(crit)} pass")
PY
