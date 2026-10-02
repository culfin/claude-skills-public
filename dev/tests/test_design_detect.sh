#!/usr/bin/env bash
# Tests for dev/scripts/design-detect.sh and dev/scripts/design-build-detector.sh.
# Uses fake engines and a throwaway git checkout; never builds or downloads anything.
set -u
cd "$(dirname "$0")/../.."
fail=0
check() { if [ "$1" = ok ]; then :; else echo "FAIL $2"; fail=1; fi; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

# 1. No engine, no vendor dir, minimal PATH -> exit 3 + "skipped:"
out=$(PATH=/usr/bin:/bin DEV_DESIGN_DIR=/nonexistent bash dev/scripts/design-detect.sh x.tsx); rc=$?
[ "$rc" = 3 ] && echo "$out" | grep -q '^skipped:' && check ok 1 || check no "1 rc=$rc out=$out"
echo "$out" | grep -q 'design-build-detector.sh' && check ok 1b || check no "1b hint missing: $out"

# Fake vendor dir: a git checkout and a fake engine that echoes its args and env.
d="$tmp/dd"; mkdir -p "$d/impeccable" "$d/bin"
touch "$d/impeccable/Cargo.toml"; git -C "$d/impeccable" init -q && git -C "$d/impeccable" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
head=$(git -C "$d/impeccable" rev-parse HEAD)
cat > "$d/bin/impeccable-engine" <<'EOF'
#!/bin/sh
echo "args:$* tele:$IMPECCABLE_NO_TELEMETRY dnt:$DO_NOT_TRACK"
exit "${FAKE_RC:-2}"
EOF
chmod +x "$d/bin/impeccable-engine"

# 2. Findings (engine exit 2) -> exit 0, findings on stdout, telemetry off, detect verb used
echo "$head" > "$d/bin/impeccable-engine.commit"
out=$(DEV_DESIGN_DIR="$d" bash dev/scripts/design-detect.sh a.tsx b.css); rc=$?
[ "$rc" = 0 ] && echo "$out" | grep -q '^args:detect .*a.tsx b.css tele:1 dnt:1' && check ok 2 || check no "2 rc=$rc out=$out"
echo "$out" | grep -q '^note:' && check no "2b unexpected note: $out" || check ok 2b

# 3. Clean scan (engine exit 0) -> exit 0
out=$(FAKE_RC=0 DEV_DESIGN_DIR="$d" bash dev/scripts/design-detect.sh a.tsx); rc=$?
[ "$rc" = 0 ] && check ok 3 || check no "3 rc=$rc out=$out"

# 4. Engine failure (exit 1) -> exit 3 + skipped
out=$(FAKE_RC=1 DEV_DESIGN_DIR="$d" bash dev/scripts/design-detect.sh a.tsx); rc=$?
[ "$rc" = 3 ] && echo "$out" | grep -q '^skipped:' && check ok 4 || check no "4 rc=$rc out=$out"

# 5. Stale engine -> still runs, first line is the note
echo 0000000 > "$d/bin/impeccable-engine.commit"
out=$(DEV_DESIGN_DIR="$d" bash dev/scripts/design-detect.sh a.tsx); rc=$?
[ "$rc" = 0 ] && echo "$out" | head -1 | grep -q "^note: engine built from 0000000, checkout at $head" && check ok 5 || check no "5 rc=$rc out=$out"

# 6. No files -> exit 3 + skipped
out=$(DEV_DESIGN_DIR="$d" bash dev/scripts/design-detect.sh); rc=$?
[ "$rc" = 3 ] && echo "$out" | grep -q '^skipped:' && check ok 6 || check no "6 rc=$rc out=$out"

# 7. Build script: no checkout -> exit 3 + skipped
out=$(DEV_DESIGN_DIR=/nonexistent bash dev/scripts/design-build-detector.sh); rc=$?
[ "$rc" = 3 ] && echo "$out" | grep -q '^skipped:' && check ok 7 || check no "7 rc=$rc out=$out"

# 8. Build script: no cargo -> exit 3 + skipped
out=$(PATH=/usr/bin:/bin DEV_DESIGN_DIR="$d" bash dev/scripts/design-build-detector.sh); rc=$?
[ "$rc" = 3 ] && echo "$out" | grep -q '^skipped:.*cargo' && check ok 8 || check no "8 rc=$rc out=$out"

# 9. Build script: up to date -> exit 0 without calling cargo (fake cargo would fail)
echo "$head" > "$d/bin/impeccable-engine.commit"
mkdir -p "$tmp/fakebin"; printf '#!/bin/sh\necho cargo-called; exit 1\n' > "$tmp/fakebin/cargo"; chmod +x "$tmp/fakebin/cargo"
out=$(PATH="$tmp/fakebin:/usr/bin:/bin" DEV_DESIGN_DIR="$d" bash dev/scripts/design-build-detector.sh); rc=$?
[ "$rc" = 0 ] && ! echo "$out" | grep -q cargo-called && check ok 9 || check no "9 rc=$rc out=$out"

# 10. Build script: stale -> calls cargo; a cargo failure is non-zero (not 0, not 3)
echo 0000000 > "$d/bin/impeccable-engine.commit"
out=$(PATH="$tmp/fakebin:/usr/bin:/bin" DEV_DESIGN_DIR="$d" bash dev/scripts/design-build-detector.sh 2>&1); rc=$?
[ "$rc" != 0 ] && [ "$rc" != 3 ] && echo "$out" | grep -q cargo-called && check ok 10 || check no "10 rc=$rc out=$out"

# 11. Neither script may call the downloading launcher, the npm shim, install or hooks
if grep -nE 'npx|cli/bin/cli\.js|scripts/impeccable|\b(install|hooks)\b' dev/scripts/design-detect.sh dev/scripts/design-build-detector.sh | grep -v '^\S*:[0-9]*:\s*#'; then
  check no "11 forbidden invocation"; else check ok 11; fi

[ "$fail" = 0 ] && echo PASS || exit 1
