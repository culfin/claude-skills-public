#!/usr/bin/env bash
# ci-watch.sh <sha> [<status-file>] — follows the CI runs of one commit in the background.
# Final status (one line): green <ids> | red <name>=<conclusion> ... | none | timeout.
# Why: /dev closes a phase after the local gate and goes on; CI of that exact commit is checked
# here instead of blocking. Only runs of this SHA count, skipped/cancelled is not a pass, and a
# failing gh call is never read as "no runs" — it only ever ends as timeout.
# Superseded runs: pushing a bookkeeping commit after the gate commit cancels the gate commit's run
# (cancel-in-progress). When every non-success of this SHA is `cancelled`, the newest run on the
# branch (DEV_CI_BRANCH, else the current branch) whose commit descends from this SHA is followed
# instead, in the same loop and time limits; the status line then ends in ` via <short sha>`.
set -uo pipefail
sha="${1:?usage: ci-watch.sh <sha> [<status-file>]}"
out="${2:-$(git rev-parse --git-common-dir)/dev-ci/$sha}"
if ! command -v jq >/dev/null 2>&1; then
    echo "ci-watch: jq not found in PATH" >&2
    mkdir -p "$(dirname "$out")"
    printf '%s\n' "timeout" > "$out"
    exit 0
fi
interval="${DEV_CI_INTERVAL:-60}"; none_after="${DEV_CI_NONE_AFTER:-900}"; max="${DEV_CI_MAX:-5400}"
mkdir -p "$(dirname "$out")"
put(){ printf '%s\n' "$1" > "$out.tmp" && mv "$out.tmp" "$out"; }
put pending
start=$SECONDS
branch="${DEV_CI_BRANCH:-$(git branch --show-current 2>/dev/null)}"; via=""
while :; do
    if json=$(gh run list --commit "$sha" --json databaseId,status,conclusion,name 2>/dev/null); then
        n=$(jq 'length' <<< "$json")
        if [[ "$n" -eq 0 ]]; then
            (( SECONDS - start >= none_after )) && { put none; exit 0; }
        elif [[ $(jq '[.[] | select(.status != "completed")] | length' <<< "$json") -eq 0 ]]; then
            bad=$(jq -r '[.[] | select(.conclusion != "success") | "\(.name)=\(.conclusion)"] | join(" ")' <<< "$json")
            [[ -z "$bad" ]] && { put "green $(jq -r '[.[].databaseId] | join(" ")' <<< "$json")${via:+ via $via}"; exit 0; }
            other=$(jq '[.[] | select(.conclusion != "success" and .conclusion != "cancelled")] | length' <<< "$json")
            if [[ "$other" -ne 0 || -z "$branch" ]]; then put "red $bad${via:+ via $via}"; exit 0; fi
            if runs=$(gh run list --branch "$branch" --json headSha,databaseId,status,conclusion,name --limit 20 2>/dev/null); then
                next=""
                while read -r h; do
                    [[ -n "$h" && "$h" != "$sha" ]] && git merge-base --is-ancestor "$sha" "$h" 2>/dev/null \
                        && { next=$h; break; }
                done < <(jq -r '.[].headSha' <<< "$runs")
                [[ -z "$next" ]] && { put "red $bad${via:+ via $via}"; exit 0; }
                sha=$next; via=${next:0:7}; continue
            fi
        fi
    fi
    (( SECONDS - start >= max )) && { put timeout; exit 0; }
    sleep "$interval"
done
