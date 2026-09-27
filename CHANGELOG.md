# Changelog

Why things changed, not just what. Rules in the skills stay free of history; it lives here.

## v1.1 — 2026-09-27

**deps**
- The 35 learned patterns moved out of `SKILL.md` into `references/patterns-workflow.md`,
  `patterns-js.md`, `patterns-cargo.md` and `patterns-ci.md`. `SKILL.md` keeps a one-line index.
  Reason: every `/deps` call loaded all of them (about 26 KB), including pnpm and Next.js details
  in Cargo or Swift projects. `SKILL.md` went from 37 KB to 11 KB; numbers are unchanged.
- Promote sync-back (`promote.md` Step 5, pattern 14): no longer claims that a skipped sync is
  "caught and fixed automatically" by the next run. It is not — status and pre-flight
  deliberately ignore merge-only divergence (Safety Rule 12). Skipping is harmless; the text now
  says so.

**dev**
- `@gate: fast` no longer recommended for documentation phases. Two places contradicted each
  other; docs phases use `@type: docs`, which is the smaller gate.

## v1.0 — 2026-09-27

First public release: `dev` and `deps`, translated to English; output follows the user's language.
