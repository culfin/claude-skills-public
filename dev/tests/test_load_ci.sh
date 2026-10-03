#!/usr/bin/env bash
# test_load_ci.sh — load-ok.sh and ci-watch.sh with stubs; no network, no real gh.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
fails=0
ok(){ echo "PASS: $*"; }; bad(){ echo "FAIL: $*"; fails=$((fails+1)); }

# load-ok
DEV_LOAD=3.2 DEV_CORES=10 bash "$here/scripts/load-ok.sh" >/dev/null && ok "low load ok" || bad "low load"
DEV_LOAD=12.5 DEV_CORES=10 bash "$here/scripts/load-ok.sh" >/dev/null && bad "high load passed" || ok "high load blocked"
DEV_LOAD=10 DEV_CORES=10 bash "$here/scripts/load-ok.sh" >/dev/null && bad "equal passed" || ok "load == cores blocked"
real=$(bash "$here/scripts/load-ok.sh")   # exit status depends on the machine; only the format is checked
grep -qE '^load [0-9.]+ cores [0-9]+$' <<< "$real" && ok "real measurement prints" || bad "real measurement format: $real"

# ci-watch: gh stub answers from $STUB_DIR/answer (or fails if $STUB_DIR/fail exists)
mkdir -p "$tmp/bin" "$tmp/stub"
cat > "$tmp/bin/gh" <<'S'
#!/usr/bin/env bash
[[ -f "$STUB_DIR/fail" ]] && { echo "HTTP 403" >&2; exit 1; }
cat "$STUB_DIR/answer"
S
chmod +x "$tmp/bin/gh"
watch(){ PATH="$tmp/bin:$PATH" STUB_DIR="$tmp/stub" DEV_CI_INTERVAL=0 DEV_CI_NONE_AFTER=0 DEV_CI_MAX=1 \
         bash "$here/scripts/ci-watch.sh" abc123 "$tmp/status"; cat "$tmp/status"; }

echo '[{"databaseId":1,"status":"completed","conclusion":"success","name":"ci"},{"databaseId":2,"status":"completed","conclusion":"success","name":"e2e"}]' > "$tmp/stub/answer"
[[ "$(watch)" == "green 1 2" ]] && ok "all success -> green" || bad "green: $(cat "$tmp/status")"
echo '[{"databaseId":1,"status":"completed","conclusion":"success","name":"ci"},{"databaseId":2,"status":"completed","conclusion":"skipped","name":"e2e"}]' > "$tmp/stub/answer"
[[ "$(watch)" == "red e2e=skipped" ]] && ok "skipped -> red" || bad "skipped: $(cat "$tmp/status")"
echo '[]' > "$tmp/stub/answer"
[[ "$(watch)" == "none" ]] && ok "no run -> none" || bad "none: $(cat "$tmp/status")"
echo '[{"databaseId":1,"status":"in_progress","conclusion":"","name":"ci"}]' > "$tmp/stub/answer"
PATH="$tmp/bin:$PATH" STUB_DIR="$tmp/stub" DEV_CI_INTERVAL=0 DEV_CI_NONE_AFTER=99 DEV_CI_MAX=1 \
  bash "$here/scripts/ci-watch.sh" abc123 "$tmp/status"
[[ "$(cat "$tmp/status")" == "timeout" ]] && ok "running too long -> timeout" || bad "timeout: $(cat "$tmp/status")"
touch "$tmp/stub/fail"
PATH="$tmp/bin:$PATH" STUB_DIR="$tmp/stub" DEV_CI_INTERVAL=0 DEV_CI_NONE_AFTER=0 DEV_CI_MAX=1 \
  bash "$here/scripts/ci-watch.sh" abc123 "$tmp/status"
[[ "$(cat "$tmp/status")" == "timeout" ]] && ok "gh error is never none/green" || bad "gh error: $(cat "$tmp/status")"

# ci-watch without jq: minimal PATH with only essential tools + gh stub
mkdir -p "$tmp/nojq/bin"
for tool in bash dirname mkdir mv git cat sleep printf; do
    ln -s /bin/$tool "$tmp/nojq/bin/$tool" 2>/dev/null || ln -s /usr/bin/$tool "$tmp/nojq/bin/$tool" 2>/dev/null || true
done
cp "$tmp/bin/gh" "$tmp/nojq/bin/gh"
PATH="$tmp/nojq/bin" STUB_DIR="$tmp/stub" DEV_CI_INTERVAL=0 DEV_CI_NONE_AFTER=0 DEV_CI_MAX=1 \
  bash "$here/scripts/ci-watch.sh" abc123 "$tmp/status_nojq" >/dev/null 2>&1
[[ "$(cat "$tmp/status_nojq")" == "timeout" ]] && [[ $? -eq 0 ]] && ok "missing jq -> timeout exit 0" || bad "missing jq: $(cat "$tmp/status_nojq")"

echo "load/ci: $fails failed"
[[ $fails -eq 0 ]]
