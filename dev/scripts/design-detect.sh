#!/usr/bin/env bash
# Run impeccable's deterministic design detector over local files (read-only, no network).
#
#   dev/scripts/design-detect.sh [--json] [--scope type,layout] <file-or-dir>...
#
# Runs ONLY a locally built engine: $IMPECCABLE_BIN, default $DEV_DESIGN_DIR/bin/impeccable-engine
# (built by dev/scripts/design-build-detector.sh). Never downloads, never installs, never hooks.
# The engine prints human-readable findings on stderr (JSON on stdout with --json); this
# wrapper puts both on stdout. It respects the project's .impeccable/config*.json ignores.
#
# Exit: 0 scan completed (findings or none; read the output)
#       3 first line "skipped: <reason>" — engine missing, no files, URL given, or the scan failed.
#         A skip is never a pass.
# Paths that do not exist (deleted/renamed files) are dropped with "note: <N> missing path(s) ignored".
# If the engine was built from an older checkout commit, a "note: engine built from <old>,
# checkout at <new>" line precedes the findings and the scan still runs. On exit 3 the
# "skipped:" line is always first; notes follow it.
set -uo pipefail
export IMPECCABLE_NO_TELEMETRY=1 DO_NOT_TRACK=1

dir="${DEV_DESIGN_DIR:-$HOME/.claude/dev-design}"
engine="${IMPECCABLE_BIN:-$dir/bin/impeccable-engine}"

if [ ! -x "$engine" ]; then
  echo "skipped: engine not built (run dev/scripts/design-build-detector.sh)"; exit 3
fi

opts=(); files=()
while [ $# -gt 0 ]; do
  case "$1" in
    *://*) echo "skipped: URL targets are not scanned here (they launch a browser): $1"; exit 3 ;;
    --scope|--viewport) opts+=("$1" "${2:-}"); shift ;;
    --*) opts+=("$1") ;;
    *) files+=("$1") ;;
  esac
  shift
done
# Deleted or renamed files in a changed-files list are not scan failures: drop them, say so.
existing=(); missing=0
for f in ${files[@]+"${files[@]}"}; do
  if [ -e "$f" ]; then existing+=("$f"); else missing=$((missing + 1)); fi
done
[ "${#existing[@]}" -gt 0 ] || { echo "skipped: no files to scan"; exit 3; }

# Notes are buffered: on every exit-3 path the "skipped:" line must come first.
notes=""
stamp="$engine.commit"
if [ -f "$stamp" ] && git -C "$dir/impeccable" rev-parse --git-dir >/dev/null 2>&1; then
  built=$(tr -d '[:space:]' < "$stamp"); head=$(git -C "$dir/impeccable" rev-parse HEAD)
  [ "$built" = "$head" ] || notes+="note: engine built from $built, checkout at $head"$'\n'
fi
[ "$missing" = 0 ] || notes+="note: $missing missing path(s) ignored"$'\n'

out=$("$engine" detect ${opts[@]+"${opts[@]}"} "${existing[@]}" 2>&1); rc=$?
case "$rc" in
  0|2) printf '%s' "$notes"; printf '%s\n' "$out"; exit 0 ;;
  *) echo "skipped: detector failed (exit $rc)"; printf '%s' "$notes"; printf '%s\n' "$out" | head -20; exit 3 ;;
esac
