# Superpowers — which version runs, and how it gets updated

`/dev` builds on the superpowers plugin (planning, execution, Visual Companion). This file says how to
know which installation is in use and how to update it. **It prepares; it changes nothing by itself**
— no install, no update, no settings change, no scheduler.

## At the start of a `/dev` session

1. **The active install is authoritative.** Claude Code records it in
   `~/.claude/plugins/installed_plugins.json` (`installPath`, `version`); `scripts/companion-resolve.sh`
   reads it. On other hosts, `DEV_SUPERPOWERS_ROOT` names it. Never pick "the newest directory in the
   cache" — it can belong to a disabled or half-updated install.
2. **Check it statically:** `python3 "$DEV_DIR/scripts/check-superpowers.py" --root <active root>`.
   `files-present` means the skills and companion scripts `/dev` needs exist — not that the version is
   current, and not that it works (`freshness: not-checked`, `runtimeCompatibility: not-tested`).
   `blocked` → name what is missing; the steps that need it are blocked, not skipped.
3. **Freshness is unknown unless checked.** Say "version X, freshness unknown" when nothing was
   checked (offline, no permission). Never call it "up to date" without asking the source.
4. **No switching mid-phase** (O3): a newer install counts from the next phase boundary, after step 2 again.

## Updating — only when the user asks

If the update watcher is set up, a new superpowers version is first checked against its contract
in `sources.md`: one that fits is applied by the watcher, one that is held back waits for
`/dev updates` (`updates.md`). `/dev` itself still never starts an update unasked.

- **Claude Code:** `claude plugin update superpowers@<marketplace>` (the marketplace from
  `claude plugin list`, e.g. `claude-plugins-official`). Automatic updates per marketplace:
  `/plugin` → Marketplaces. A downloaded update is loaded by new sessions, not by the running one.
- **Codex:** use Codex's own plugin manager for the installed source; check the exact commands with its
  `--help` on that machine rather than assuming them.
- After an update: step 2 again, then `tests/check-screens.sh`. Record version and result in STATE.md.
  If either fails, keep working with the previous install through the host's own controls; do not delete
  caches.
