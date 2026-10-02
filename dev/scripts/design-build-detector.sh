#!/usr/bin/env bash
# Build impeccable's deterministic design detector from the local checkout.
#
#   dev/scripts/design-build-detector.sh
#
# Source:  $DEV_DESIGN_DIR/impeccable  (default DEV_DESIGN_DIR=~/.claude/dev-design)
# Output:  $DEV_DESIGN_DIR/bin/impeccable-engine         (the engine binary)
#          $DEV_DESIGN_DIR/bin/impeccable-engine.commit  (checkout commit it was built from)
#
# Builds with `cargo build --release --locked`; the target dir lives outside the checkout
# ($DEV_DESIGN_DIR/.build/impeccable) so the git checkout stays clean for fast-forward pulls.
# Does nothing when the recorded commit equals the checkout HEAD, so it is cheap to call after
# every update. Network is used only by cargo, to fetch crates; this script never runs
# impeccable's own launcher or npm shim (those download a prebuilt binary).
#
# Exit: 0 built or up to date | 3 + "skipped: <reason>" (no checkout, no cargo) | other = build failed
set -euo pipefail
export IMPECCABLE_NO_TELEMETRY=1 DO_NOT_TRACK=1

dir="${DEV_DESIGN_DIR:-$HOME/.claude/dev-design}"
src="$dir/impeccable"
bin_dir="$dir/bin"
out="$bin_dir/impeccable-engine"
stamp="$out.commit"

if ! command -v git >/dev/null 2>&1; then
  echo "skipped: git not found"; exit 3
fi
if [ ! -f "$src/Cargo.toml" ] || ! git -C "$src" rev-parse --git-dir >/dev/null 2>&1; then
  echo "skipped: no impeccable checkout at $src"; exit 3
fi
head=$(git -C "$src" rev-parse HEAD)

if [ -x "$out" ] && [ -f "$stamp" ] && [ "$(tr -d '[:space:]' < "$stamp")" = "$head" ]; then
  echo "up to date: impeccable-engine built from $head"; exit 0
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "skipped: cargo not found (set up Rust with rustup to build the detector)"; exit 3
fi

target="$dir/.build/impeccable"
mkdir -p "$target" "$bin_dir"
echo "building impeccable-engine from $head (first build fetches crates and takes a few minutes)"
# Run inside the checkout so its rust-toolchain.toml applies.
(cd "$src" && CARGO_TARGET_DIR="$target" cargo build --release --locked -p impeccable)

built="$target/release/impeccable"
[ -x "$built" ] || { echo "build finished but $built is missing" >&2; exit 1; }
tmp="$out.tmp.$$"
cp "$built" "$tmp" || exit 1
chmod +x "$tmp" || exit 1
mv -f "$tmp" "$out" || exit 1
echo "$head" > "$stamp"
echo "built: $out ($("$out" engine-probe 2>/dev/null || echo 'probe failed'))"
