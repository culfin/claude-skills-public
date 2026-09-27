# Changelog

Why things changed, not just what. Rules in the skills stay free of history; it lives here.

## v1.2 — 2026-09-27

**dev**
- `SKILL.md` split: it keeps the router, session start, phase loop, halt rule and error table
  (58 KB → 22 KB per `/dev` call). The gate moved to `gate.md`; status, skip, add, reorder, pause,
  debug, milestone end and pre-release review to `commands.md`; STATE.md rules to `state.md`; the
  Visual Companion procedure to `companion.md`. Content unchanged apart from the points below.
- Automatic trigger at session start is now one line of status. Before, every session in a
  roadmap project started the companion server and asked a question, even when the user came for
  something else. The full flow runs on `/dev` or a request to work on the roadmap.
- Gate step 5e is stack-neutral: "Typecheck + lint + tests" with a command table for JS/TS, Rust,
  Swift, Go, Python, PHP and .NET, instead of `tsc` everywhere. Unconfigured tools are recorded as
  "not configured", not as failures.
- Removed the "5h removed" note from the gate: test gaps are covered by the spec checker (5c-v, item d).

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
