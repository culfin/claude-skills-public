#!/usr/bin/env bash
# ci-watch.sh <sha> [<status-file>] — follows the CI runs of one commit in the background.
# Final status (one line): green <ids> | red <name>=<conclusion> ... | none | timeout.
# Why: /dev closes a phase after the local gate and goes on; CI of that exact commit is checked
# here instead of blocking. Only runs of this SHA count, skipped/cancelled is not a pass, and a
# failing gh call is never read as "no runs" — it only ever ends as timeout.
set -uo pipefail
if ! command -v jq >/dev/null 2>&1; then
    echo "ci-watch: jq not found in PATH" >&2
    mkdir -p "$(dirname "${2:-$(git rev-parse --git-common-dir)/dev-ci/dummy}")}"
    printf '%s\n' "timeout" > "${2:-$(git rev-parse --git-common-dir)/dev-ci/dummy}"
    exit 0
fi
sha="${1:?usage: ci-watch.sh <sha> [<status-file>]}"
out="${2:-$(git rev-parse --git-common-dir)/dev-ci/$sha}"
interval="${DEV_CI_INTERVAL:-60}"; none_after="${DEV_CI_NONE_AFTER:-900}"; max="${DEV_CI_MAX:-5400}"
mkdir -p "$(dirname "$out")"
put(){ printf '%s\n' "$1" > "$out.tmp" && mv "$out.tmp" "$out"; }
put pending
start=$SECONDS
while :; do
    if json=$(gh run list --commit "$sha" --json databaseId,status,conclusion,name 2>/dev/null); then
        n=$(jq 'length' <<< "$json")
        if [[ "$n" -eq 0 ]]; then
            (( SECONDS - start >= none_after )) && { put none; exit 0; }
        elif [[ $(jq '[.[] | select(.status != "completed")] | length' <<< "$json") -eq 0 ]]; then
            bad=$(jq -r '[.[] | select(.conclusion != "success") | "\(.name)=\(.conclusion)"] | join(" ")' <<< "$json")
            if [[ -z "$bad" ]]; then put "green $(jq -r '[.[].databaseId] | join(" ")' <<< "$json")"
            else put "red $bad"; fi
            exit 0
        fi
    fi
    (( SECONDS - start >= max )) && { put timeout; exit 0; }
    sleep "$interval"
done
