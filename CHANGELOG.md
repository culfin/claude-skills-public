# Changelog

Why things changed, not just what. Rules in the skills stay free of history; it lives here.

## v2.1.2 — 2026-09-27

Three findings from running the external review's twelve decision scenarios against v2.1.1 (Claude
Code, isolated, read-only; 11 of 12 matched, all 12 after these fixes; Codex not run).

**dev**
- A proven pre-existing failure ended as a plain `[gate-pass]` with the failure only in STATE.md.
  The gate summary now has a "Known pre-existing failures" line and the report says "completed with
  a known pre-existing failure", never "all green".
- Stop hook: a `[gate-pass]` commit on another local branch silenced the reminder even when the
  edited files were still uncommitted in this checkout — that gate cannot have checked them. Now
  only HEAD counts while an edited file is uncommitted; committed work on a feature or worktree
  branch still counts (the 2026-09-25 fix for false reminders stays).
- The Visual Companion resolved "the newest superpowers version in the cache", which can be an
  inactive install. It now reads the active `installPath` from `installed_plugins.json`.

## v2.1.1 — 2026-09-27

Two more gaps from the same external review, found when its report arrived.

**deps**
- The update scan missed workspace members: `pnpm outdated` and `npm-check-updates` check only the
  root package unless given `-r` / `--workspaces --root` (measured with a two-package workspace);
  and `npm outdated | head -40` cut long lists silently. Flags added, `head` removed. `npm outdated`
  already covers the workspaces in npm 11 — adding `--workspaces` there would drop the root.

**dev**
- A review of the same commit no longer counts if the check's scope or acceptance criteria changed.

## v2.1 — 2026-09-27

Seven defects found in an independent review of v1.0 that were still present in v2.0, each fixed
with the smallest change — plus Codex support.

**dev**
- Gate 5k waited for CI with `gh run list --branch` but never pushed: it could read the previous
  commit's green run as the verdict. Now the gate commit is made available through an already
  allowed route (else: blocker), and only runs whose `headSha` equals the gate commit count.
- "The error was already there before" now needs proof: the same failure reproduced on the unchanged
  base in a separate worktree, with the change's own tests still running. A note is not enough.
- Evidence belongs to one state of the code: a later change reopens the checks it touches.
- Old `@skills:` names of the former third-party analyzers map to `analyzers/`.

**deps**
- PR listing used `gh pr list` (30 PRs by default, all target branches). New
  `scripts/collect_prs.py`: paginated, only the dev branch, fails instead of undercounting.
- `.deps/config.json` with `"prodBranch": null` was turned into `prod` by `jq`'s `//` (pattern 25).
  New `scripts/branch_config.py` validates both branch names; empty prod = no promote.
- Major updates with a migration: the text said "migrate before merging", the steps committed the
  migration to the dev branch first — broken until the update landed. Migration now goes onto the
  PR branch; update and migration are tested and merged as one head.
- Revert counted commits (`HEAD~N..HEAD`) and reverted a bisect hit unchecked — both can hit someone
  else's push. Now every merge SHA of the run goes into a ledger under `.git`; only those are
  reverted, bisect runs in its own worktree with a fresh install per step.
- Auto-merge detection stopped on any workflow file mentioning "dependabot" and "merge". Now only an
  enabled workflow that really merges, or GitHub auto-merge on a PR, counts as competition.
- Patterns 4 and 5 were stated as laws ("Playwright never runs locally", "dev-deps have 100 % pass
  rate"); they are observations now.

**Both**
- Codex: `runtime.md` per skill maps tool names to host capabilities; paths resolve from the skill's
  own directory (`$DEV_DIR`, `$DEPS_DIR`); the Visual Companion is found via
  `DEV_COMPANION_SCRIPTS_DIR` / `DEV_SUPERPOWERS_ROOT`, with Claude Code's plugin cache as fallback.
- Found while testing on macOS: a loop variable named `path` overwrites `$PATH` in zsh.

`collect_prs.py`, `branch_config.py` and their tests come from that review's package; not adopted
from it: the JSON evidence ledger with its validator (checks form, not truth — the one rule worth
keeping is above), the shortening of the 35 deps patterns to ten general lessons, and its own
review procedures (dev keeps the benchmarked `analyzers/`).

## v2.0 — 2026-09-27

**dev — no third-party analysis skills any more.** The quality gate used to call `/bug-prospector`,
`/performance-check`, `/security-audit`, `/review-changes`, `/scan-similar-bugs` and
`/dead-code-scanner` from another repository. They were written for Swift; other stacks got a
fallback, and when they were not installed, the "mandatory" gate skipped them with a warning.

- New `dev/analyzers/`: change review, bug hunt, security, performance, similar bugs, dead code,
  accessibility — each an instruction file for one read-only subagent, with language notes for
  Swift, TypeScript/JavaScript, Rust, PHP, Python, shell and SQL. `CONTRACT.md` fixes what the gate
  hands over, how an analyzer works (sweep for risky constructs, then judge every hit, then lenses)
  and the report format. Nothing to install.
- New `dev/analyzers/benchmark/`: five anonymised cases from real production bugs and a runner that
  checks, in isolation, whether the analyzers find them. Results and their limits are in its README.
- Tech-stack skills (Next.js, shadcn, Svelte, …) stay optional extras; a missing one is skipped, a
  missing analyzer cannot happen.
- Checklist names changed accordingly: "Change review", "Bug hunt", "Performance review",
  "Security review", "Similar-bugs scan", "Dead-code scan".

Breaking: projects whose `ROADMAP.md` lists the old skill names under `@skills:` keep calling them
as extras; `/dev` itself no longer does.

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
