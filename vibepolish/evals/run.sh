#!/usr/bin/env bash
# run.sh — runs the executable evaluation cases (evals.json, "executable": true) on Claude Code.
#
# Per case: the fixture is copied into a fresh git repository with one baseline commit; a new
# session gets only the skill (without evals/), the prompt and those files, and may read, edit and
# run `git` and `node` there — nothing else. Afterwards the harness records what actually happened
# (new commits, changed or deleted files, test result) and a second session without tools judges
# answer + observations against the case's assertions, which the working session never sees.
#
# Usage: run.sh [--cases 16,17] [--model sonnet] [--out FILE]      needs `claude`, `git`, `node`
# Uses model credit. Codex: run the same prompts in a fresh read/write sandbox and judge by hand.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(cd "$HERE/.." && pwd)"
MODEL=sonnet; ONLY=""; OUT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cases) ONLY="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

ids=$(python3 -c 'import json,sys; print(" ".join(str(c["id"]) for c in json.load(open(sys.argv[1]))["evals"] if c.get("executable")))' "$HERE/evals.json")
field() { python3 -c 'import json,sys; c=[c for c in json.load(open(sys.argv[1]))["evals"] if str(c["id"])==sys.argv[2]][0]; v=c[sys.argv[3]]; print(json.dumps(v) if isinstance(v,(list,dict)) else v)' "$HERE/evals.json" "$1" "$2"; }

run_case() {
    local id="$1" work repo prompt answer facts verdict
    work=$(mktemp -d); repo="$work/project"; mkdir -p "$repo" "$work/skill"
    ( cd "$SKILL" && tar cf - --exclude=evals . ) | ( cd "$work/skill" && tar xf - )
    python3 - "$HERE" "$id" "$repo" <<'PY'
import json, os, shutil, sys
here, cid, repo = sys.argv[1], sys.argv[2], sys.argv[3]
case = [c for c in json.load(open(os.path.join(here, "evals.json")))["evals"] if str(c["id"]) == cid][0]
for f in case["files"]:
    rel = f.split("/", 3)[3] if f.startswith("evals/fixtures/") else f     # drop evals/fixtures/<name>/
    dst = os.path.join(repo, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(os.path.dirname(here), f), dst)
PY
    git -C "$repo" init -q && git -C "$repo" config user.email eval@example.invalid && git -C "$repo" config user.name eval
    git -C "$repo" add -A && git -C "$repo" commit -qm baseline
    base=$(git -C "$repo" rev-parse HEAD)
    prompt=$(field "$id" prompt)

    (cd "$repo" && claude -p "Use the skill at $work/skill/SKILL.md (read it and the references it points to) for this request. The project is the current directory.

$prompt" --model "$MODEL" --strict-mcp-config --disable-slash-commands \
        --tools Read Grep Glob Edit Write Bash --allowedTools "Bash(git:*)" "Bash(node:*)" \
        --output-format stream-json --verbose < /dev/null > "$work/trace.jsonl" 2>/dev/null || true)
    # The final answer and every command the session actually ran, from the host's own event stream.
    answer=$(python3 -c 'import json,sys
for l in open(sys.argv[1]):
    try: e=json.loads(l)
    except ValueError: continue
    if e.get("type")=="result": print(e.get("result",""))' "$work/trace.jsonl")
    commands=$(python3 -c 'import json,sys
for l in open(sys.argv[1]):
    try: e=json.loads(l)
    except ValueError: continue
    if e.get("type")=="assistant":
        for c in e["message"].get("content",[]):
            if c.get("type")=="tool_use" and c.get("name") in ("Bash","Edit","Write"):
                i=c["input"]; print("-", c["name"]+":", (i.get("command") or i.get("file_path") or "")[:160])' "$work/trace.jsonl")

    context=$(cd "$repo" && for f in NOTES.md README.md; do [ -f "$f" ] && { echo "--- $f (as given to the agent)"; git show "$base:$f" 2>/dev/null; }; done; true)
    facts="Commands and edits the session actually ran, in order:
$commands
New commits since baseline: $(git -C "$repo" rev-list --count "$base"..HEAD)
Commit subjects: $(git -C "$repo" log --format=%s "$base"..HEAD | tr '\n' ';')
Changed or deleted files (vs baseline, incl. uncommitted): $(git -C "$repo" diff --name-status "$base" | tr '\n' ';') $(git -C "$repo" status --porcelain | tr '\n' ';')
Diff (first 80 lines): $(git -C "$repo" diff "$base" | head -80)
Tests after the run: $( [ -f "$repo/package.json" ] && (cd "$repo" && node --test 2>&1 | grep -E '^ℹ (pass|fail)|^✖ [a-z]' | head -6 | tr '\n' ';') || echo 'no test suite')"

    verdict=$(cd "$work" && claude -p "Judge one agent run against assertions. Use the observed facts (what really happened) over the agent's claims. Judge substance, not wording or placement: an assertion is met if the answer or the observed facts clearly satisfy it anywhere. For each assertion answer \"pass\", \"fail: <short reason>\" or \"not tested: <reason>\". JSON only: {\"assertions\": [\"...\", ...]}.

Task given to the agent: $prompt
$context

Assertions: $(field "$id" assertions)

Observed facts:
$facts

Agent's final answer:
$answer" --model "$MODEL" --strict-mcp-config --disable-slash-commands --tools "" < /dev/null 2>/dev/null || true)
    rm -rf "$work"
    python3 - "$id" "$(field "$id" name)" "$verdict" <<'PY'
import json, re, sys
cid, name, raw = sys.argv[1], sys.argv[2], sys.argv[3]
m = re.search(r"\{.*\}", raw, re.S)
res = json.loads(m.group(0)).get("assertions", []) if m else ["judge-error"]
ok = sum(1 for r in res if str(r).startswith("pass"))
print(f"| {cid} | {name} | {ok}/{len(res)} | " + "; ".join(r for r in res if not str(r).startswith("pass")).replace("|", "/") + " |")
PY
}

{
    echo "| Case | Name | Assertions passed | Not passed |"
    echo "|---|---|---|---|"
    for id in $ids; do
        [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]] && continue
        run_case "$id" &
    done
    wait
} | tee ${OUT:+"$OUT"}
