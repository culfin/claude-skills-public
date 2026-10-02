#!/usr/bin/env bash
# Checks the Claude Code installation of this repository's skills (see README, "Installation").
# Exit 0 = what is installed is set up correctly. A skill that is not linked is reported as
# "not installed", not as an error — installing only some skills is valid. Errors are: a link that
# points somewhere else, no skill installed at all, a broken stop hook, or /dev without superpowers.
# A missing design source ($DEV_DESIGN_DIR, see README, "Design sources") is also optional — it is
# reported as "info", never as an error; the design steps that use it are skipped.
# The same holds for the stack sources ($DEV_STACK_DIR, see README, "Stack sources").
# Codex installs are not checked here.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; f=0; installed=0
ok(){ echo "ok    $1"; }; info(){ echo "info  $1"; }; fail(){ echo "FAIL  $1"; f=1; }

for s in dev deps sentry vibepolish; do
  link="$HOME/.claude/skills/$s"
  if [ -L "$link" ] || [ -e "$link" ]; then
    if [ "$(readlink "$link")" = "$REPO/$s" ]; then ok "skill $s -> $REPO/$s"; installed=$((installed+1))
    else fail "skill $s: ~/.claude/skills/$s points to $(readlink "$link" || echo 'a non-link') instead of $REPO/$s"; fi
  else
    info "skill $s not installed (optional)"
  fi
done
[ "$installed" -gt 0 ] || fail "no skill of this repository is installed"

if [ "$(readlink "$HOME/.claude/skills/dev" 2>/dev/null)" = "$REPO/dev" ]; then
  if python3 -c 'import json,os,sys;s=json.load(open(os.path.expanduser("~/.claude/settings.json")));sys.exit(0 if "dev/hooks/gate-check.py" in json.dumps(s.get("hooks",{}).get("Stop",[])) else 1)' 2>/dev/null; then
    if [ -x "$REPO/dev/hooks/gate-check.py" ] && (cd "$REPO/dev/hooks" && python3 -m unittest -q test_gate_check >/dev/null 2>&1); then
      ok "stop hook registered, executable, tests green"
    else fail "stop hook registered but not executable or its tests fail"; fi
  else
    info "stop hook not registered (optional reminder for /dev check)"
  fi
  if (source "$REPO/dev/scripts/companion-resolve.sh" && resolve_companion start-server.sh >/dev/null 2>&1); then
    ok "superpowers companion found (active install)"
  else fail "/dev needs the superpowers plugin (Visual Companion not found)"; fi
fi

DEV_DESIGN_DIR="${DEV_DESIGN_DIR:-$HOME/.claude/dev-design}"
for d in emil taste impeccable; do
  dir="$DEV_DESIGN_DIR/$d"
  if [ -d "$dir" ]; then
    commit="$(git -C "$dir" rev-parse --short HEAD 2>/dev/null)"
    if [ -n "$commit" ]; then ok "design source $d: $commit"
    else info "design source $d: present but not a git checkout — design steps will be skipped"; fi
  else
    info "design source $d: missing — design steps will be skipped"
  fi
done

DEV_STACK_DIR="${DEV_STACK_DIR:-$HOME/.claude/dev-stack}"
for d in docker gha better-auth postgres stripe fastify next wordpress; do
  dir="$DEV_STACK_DIR/$d"
  if [ -d "$dir" ]; then
    commit="$(git -C "$dir" rev-parse --short HEAD 2>/dev/null)"
    if [ -n "$commit" ]; then ok "stack source $d: $commit"
    else info "stack source $d: present but not a git checkout — not watched for updates"; fi
  else
    info "stack source $d: missing — its reviews are ticked as skipped"
  fi
done

exit $f
