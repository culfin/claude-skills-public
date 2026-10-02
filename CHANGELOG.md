# Changelog

Why things changed, not just what. Rules in the skills stay free of history; it lives here.

## v2.11.0 — 2026-10-02

**dev** — the two stack sources v2.10 deferred. `next` (Next.js's own `next-dev-loop` skill)
closes a gap the gate does not: types, lint and build can all be green while the page is broken
at runtime, and the E2E step only covers what has a spec. The loop asks the running dev server
and a real browser. Its repository is far too large to clone, so the checkout is a sparse,
blob-filtered clone of the `skills` folder only, and the update check was verified on such a
tree. It is the one source that acts rather than reviews, which is why it gets its own override
(O11): it needs Next.js 16.3+ on Turbopack and an `agent-browser` the user installed — `/dev`
installs neither and reports `skipped` instead; the skill's own "install it and continue" would
have been a global install nobody approved.

`wordpress` (WordPress/agent-skills) was held back until its bundled scripts were read. They
turned out to be harmless — file-system scans that print JSON, and two that call read-only WP-CLI
subcommands — but they are still not run: `/dev` detects WordPress itself and routes by trigger,
so the upstream router and triage skill (which point at sibling skills) are not needed. Six
skills are indexed: plugin development, REST API, performance, WP-CLI/ops, block themes and
block development — what a team maintaining a few sites with custom plugins and themes touches.
Two limits are written down (O12): the skills assume WordPress 7.0+, so a rule is checked against
the project's version before it is applied; and no command is run against a live site on a
skill's say-so — a search-replace recipe is context for a plan, not something to execute.

`dev/stack/INDEX.md` grows past its 80-line budget (now 95) and `dev/sources.md` to 130: eight
more rows and two overrides are content, not prose, and the index is still read in one pass.

The index parser now also rejects `$HOME/…` and quoted `"$DEV_STACK_DIR"/…` spellings instead
of dropping such a row silently, and the tests that depend on local checkouts report `skipped`
with the missing sources rather than passing without having checked anything.

## v2.10.0 — 2026-10-02

**dev** — stack knowledge beyond the handful of installed skills. For Docker, GitHub Actions,
better-auth, Postgres, Stripe and Fastify the best material is the vendor's or maintainer's own
skill repository, but installing six more skills would put six more descriptions into every
session and let them self-trigger. They are therefore handled like the design sources: optional
git checkouts under `$DEV_STACK_DIR`, read file by file through the new `dev/stack/INDEX.md` when
a trigger matches, and tracked in `dev/sources.md` so an upstream change passes the update check
before it takes effect. Where a package ships its own docs or skills (Next.js, AI SDK, Fastify,
Playwright's trace skill) the index points into the project's `node_modules` instead — those
match the installed version by construction and need no checkout.

The stack detection table moved from `SKILL.md` into that index. It was needed once per session
but sat in context for all of it, and every new stack would have grown the one file that is
always loaded; `SKILL.md` is shorter now although eight stacks were added. Steps 4a, 4c and 5c
are wired by one generic rule in `tech-stack-triggers.md` rather than a row per stack in three
files, so adding a stack is an index row and a contract row.

Three limits are written into the contract because the sources would otherwise overreach
(O9, O10): they are a review yardstick, not an order to rebuild — a project that names its
compose file differently or sets its own restart policy is not "wrong"; Stripe's repository also
contains a plugin with hooks and usage reporting, so only its plain skill files are read; and
hosted products recommended inside a source are not passed on. A missing checkout or missing
bundled docs closes the gate item as `skipped: <reason>`, as before — never a silent pass.

Two of these repositories hold far more than the skills `/dev` reads and change almost daily, so
the update check scans a stack source only inside the folders it actually reads (plus the
licence) — otherwise an unrelated plugin hook elsewhere in the repository would hold every
update; in return, subagents may not follow a pointer out of the skill folder.

Training knowledge of fast-moving libraries goes stale, and "look it up" without an order ends in
whichever source answers first. `dev/stack/docs.md` fixes the order per technology: docs bundled
with the project, the vendor's own docs access, the official `llms.txt` (index and single pages —
the full dumps run to megabytes), then Context7 pinned to the project's version.

Deferred: a Next.js dev-loop skill (its repository is too large for a checkout and it needs a
globally installed browser tool) and WordPress (its bundled scripts have not been read yet).

**deps** — a "What's new" report for minor and major jumps of the listed technologies
(`references/whats-new.md`). The impact analysis answers "is this safe to merge"; nobody was
answering "what did we just gain, and what was deprecated under us". A subagent reads the release
notes for the skipped range and reports with code locations. Report only — automatic rewrites
after a version jump are exactly the changes nobody reviews — and `skipped` when the notes cannot
be fetched, rather than a summary from memory.

## v2.9.1 — 2026-10-02

**dev** — Next.js knowledge now comes from the docs bundled with the project's own `next`
package (`node_modules/next/dist/docs/`, 16.3+) instead of the `next-best-practices` skill. The
skill's upstream repository was emptied when the content moved into Next.js itself, so the
installed copy would have stayed frozen while the update check reported nothing. The bundled docs
match the version the project runs. The old skill remains a fallback for projects without bundled
docs and is no longer a tracked source.

## v2.9.0 — 2026-10-02

**dev** — design sources are no longer installed as skills. A skill sits in context for the
whole session and its description can self-trigger; design guidance is read once, only when a
UI change is actually in scope, so it now lives under `dev/design/`, reachable only through
`dev/design/INDEX.md` (loaded on demand, like a skill's own `SKILL.md` but never resident). The
platform and UX-pattern content that used to come from six small installed skills is rewritten
in our own words (forms, states, onboarding, writing, density, three platform checklists),
deduplicated and with contradictions resolved — notably target size: 24×24 CSS px minimum
(WCAG 2.2 SC 2.5.8 AA) is the finding, 44×44 on touch is a note, not a second rule to satisfy.
`ui-ux-pro-max` was evaluated and rejected (ADR in the private repo): a sample run produced the
generic look the other sources warn against, its sub-skills need third-party image APIs with
their own keys, and its licence is mixed.

Accessibility had a trigger gap: it only ran for `@type: ui` phases, so a UI file changed inside
any other phase type skipped it silently. It now triggers off the changed files themselves, in
any phase, and is listed on the gate checklist so a skip shows up instead of passing quietly.

Two new analyzers follow the same on-demand, skip-if-missing pattern: `design-detector` runs
impeccable's engine, but only a copy built from source on demand by
`dev/scripts/design-build-detector.sh` (`cargo --locked`, telemetry and install hooks off) —
never a downloaded binary; `motion` reads Emil Kowalski's animation standards at run time
instead of paraphrasing them into a static rule file that drifts.

Phases gain a `landing` type alongside the existing restrained `ui`: `landing` asks a subagent
for a bold pass using taste v2 in full, where `ui` stays close to Emil's narrower defaults —
previously every UI phase got the same restrained treatment regardless of whether the screen was
a dashboard or a marketing page. Pre-release work also picks up design polish explicitly:
vibepolish's launch audit, impeccable's audit/polish pair, and the native platform checklists are
now part of what a release pass runs. New `/dev ui` mode analyses and reworks a single existing
UI surface without going through a full roadmap phase. Across all of this, a missing design
source (no local checkout, no built engine, no network) is always reported as "skipped" in the
output — never a silent pass.

An audit of the whole skill against its own load-on-demand rule found content that no step ever
reached: the `4c` design rows of the index (animation, web on a phone, Apple design) and the
automatic Debug Flow and Milestone End, which lived in `commands.md` while the file table said it
was read only from the router. Each now has a pointer from the step that needs it. Two texts had
drifted from their source — the companion wrapper was described as picking the newest install
(it picks the active one), and the trigger summary in `SKILL.md` listed reviews the matrix no
longer matched — and now defer to it. A test keeps every `dev/*.md` in the file table.

What changes in behaviour: implementers now get the `4c` design rows (animation, web on a phone,
Apple design) when a task meets their trigger, and landing phases read `ux-writing.md` for copy.
Four stack skills that were detected but never called now have triggers of their own —
`swift-concurrency-pro` (Swift concurrency code changed), `swift-testing-pro` and `rust-testing`
(test files changed) in the gate's tech-stack review, `svelte:svelte-code-writer` while
implementing Svelte work. The subagent model table moved from `gate.md` to `models.md`, since
milestone end, pre-release review and `/dev ui` needed only that table, not the whole gate; and
the `@gate: fast` conflict rules and the list of gate checks now live only in `gate.md`.

Skill updates are checked before they take effect. `/dev` builds on skills it does not own, and a
new version of one could quietly change how `/dev` behaves. `dev/sources.md` is now the contract
per referenced source — what `/dev` reads from it, where `/dev` deliberately overrides it, and the
invariants that must hold after any update. `dev/scripts/check-source-update.py` compares an old and
a new tree deterministically (vanished read paths, changed invocation switches, hooks, settings
writes, pipe-to-shell, install steps, symlinks, licence); it scans every text file, compares the
matching lines rather than counting them, and validates queue entries. Some finding kinds are
**hold kinds** (`--hold-kinds`: `missing-read-path`, `new-hook`, `new-settings-json`,
`new-pipe-to-shell`, `new-install-step`, `license-changed`, `symlink`, `scan-incomplete`): they
hold an update for the user whatever a review agent concludes, because a review can be talked
into approving its own subject. Held updates wait in a queue; the new `/dev updates`
(`dev/updates.md`) shows each with its verdict (`fits` / `unclear` / `conflict`) and reasons and
applies, rejects or defers only on an explicit answer — for a `conflict`, Apply is never the
recommended option. The automatic session-start line gains a suffix, `N skill updates waiting —
/dev updates`, by counting the queue files without reading them. The watcher that fills the queue
is external and optional; the applier it provides is `dev-updates-apply --apply <source> <new>`.

A skipped check now has a way out of the gate. The rule used to say a check whose optional source
is missing "stays open", which left the phase unable to complete. Now the item is ticked with the
evidence `skipped: <reason>`, `check-evidence.py` accepts that as closed (only for checks with an
optional source — a mandatory check cannot be skipped) and prints it as skipped, and the gate
summary lists every one under "Skipped checks": visible, never counted as "no findings", not
blocking.

## v2.8.3 — 2026-10-01

**dev** — gate evidence works in monorepos. `check-evidence.py` excluded only a root-level
`STATE.md`/`ROADMAP.md` from the state id; a project that keeps them next to its app (e.g.
`apps/web/`) changed its own id with every checkmark, so every item showed as stale right after it
was written. The bookkeeping files are now excluded wherever they live (`:(glob)**/STATE.md`).

## v2.8.2 — 2026-10-01

**dev** — the companion URL no longer ends every message. v2.8 widened the rule to "every message
while the server runs"; in a long session that put the same link under every progress report and
test result, and the one message that actually had something new to look at no longer stood out.
Now the URL ends a message only when it points the user at a new or updated screen (or asks about
one); status messages carry none. Alive check and restore-after-restart from v2.8.1 stay.

## v2.8.1 — 2026-10-01

**dev** — two ways the companion link went dead in practice: the server stops itself after four idle
hours, and a restart starts with an empty screen directory, so the page loads blank although the
server runs. Now: alive check before every message carrying the URL (not only before writing a
screen), and after a restart the current screen is copied into the new directory and checked to
render before the link is shared.

## v2.8 — 2026-09-30

**dev** — the Visual Companion shows only the user interface. In practice screens had turned into
text in a box: roadmaps, plans, approach comparisons, architecture diagrams, decision lists — all of
it just as readable in the chat, and none of it worth a browser tab. Now the companion is reserved
for what has to be *seen*: mockups and wireframes of views, their states, desktop/mobile and
light/dark, flows as rows of view mockups, and real screenshots of the running app for review and
before/after. Roadmap, status, milestone and gate summaries, architecture approaches and findings go
to the terminal. The building blocks "Roadmap", "Gate dashboard", "Mermaid diagram" and
"Architecture comparison" are gone; "Before/After" now compares views, and "Real screen" (annotated
screenshot) is new. The URL rule is widened: while a companion server runs, every message ends with
its URL — not only messages that mention a screen.

## v2.7.1 — 2026-09-29

**dev** — the Visual Companion URL now travels with every mention. In practice the link from the
first start scrolled out of view within minutes, and the user had to search the history for it.
Every message that shows a screen or refers to the companion (new screen, "see the browser", a
question whose options are drawn there, gate dashboard, delegated brainstorming) ends with the
current URL on its own line; before a question dialog the URL comes first, since the dialog can
cover earlier output; after a restart the URL is taken from the new return value, and a dead
server is reported instead of a dead link.

## v2.7 — 2026-09-27

**vibepolish** — an external review of v2.6.1 checked against the current text; all six points held:
- `/dev` handover: v2.6 sent fixes to `/dev check`, which commits and refuses to start during a
  phase. Now: in an active phase the phase's gate; outside it `/dev check` only where commits are
  already authorized; another skill never grants a missing permission; no second gate or commit.
- Pre-existing failures need the same test failing for the same cause on the unchanged start —
  equal counts prove nothing; no resets of user work to compare; no "all green" for limited results.
- Substitute checks mark only the criteria they cover; static analysis does not replace a keyboard or
  browser flow; self-review never replaces an independent one.
- Assets: *not found in the supplied material* / *broken locally* (reproducible build, runtime or
  decoding failure — a real defect, not a production outage) / *broken on the target system*. v2.6
  wrongly required an HTTP failure for any defect.
- Substantial visual changes close with a before/after record (same route, state, viewport); without
  a browser the visual result stays unverified — now stated in `SKILL.md`, not only in a reference.
- Every fix, however small, ends with a line on checks run, checks open and the `/dev` gate state.
- Six new executable eval cases (active `/dev` phase, no-commit, same failure count with a different
  cause, visual fix without browser, injected instructions, CDN-served asset) and `evals/run.sh`,
  which records the commands a session really ran and the resulting git state. Results:
  `evals/RESULTS.md` — 22 of 24 assertions on Claude Code; Codex not run.

## v2.6.1 — 2026-09-27

**vibecode-polish is now called vibepolish** (directory, skill name, display name). Nothing else
changed. If you linked it under the old name: `rm ~/.claude/skills/vibecode-polish` (or
`~/.agents/skills/…`) and link `vibepolish` instead.

## v2.6 — 2026-09-27

**New skill: vibecode-polish** — audits web apps (especially quickly built or AI-assisted ones) for
unfinished details and launch risks, and fixes them when asked. Brought in from a separate
package; reviewed before publishing:
- Its own evaluation runs (on Codex) passed 20 of 21 assertions. Two fixture cases rerun here on
  Claude Code: the "intentional design" case respected all four stated choices and still found two
  real defects (a spinner without animation, focus lost on a disabled button); the "unfinished page"
  case found all four planted details but called an image missing from the supplied files "broken
  for every visitor".
- Fixed: an asset absent from the files the agent can see is now "not found in the supplied files";
  only an observed failed request makes it broken. Rerun twice: both reported it as unverified.
- Added: answer in the user's language; fixes go through `/dev check` where a project uses `/dev`.
- Not published: the package's run records (machine paths, a binary git index, ~100 files). The
  evaluation cases and fixtures are included.

## v2.5 — 2026-09-27

**sentry** — four rules from a live run against the Sentry MCP server:
- The MCP issue search takes a relative `period` (`24h` … `90d`), not start/end; the skill no longer
  asks for a frozen UTC window it cannot express, and never invents parameters.
- Completeness test for list tools: fewer results than `limit` = complete; exactly `limit` = "at
  least N" (raise the limit to 100 or label it a lower bound).
- The MCP has no environment inventory; environments come from aggregating error events, which only
  lists environments that had errors — "no errors seen" is not "does not exist".
- Catalog search also returns tools that create or change projects; status and check call only
  tools annotated `readOnlyHint: true`.
- New `sentry/tests/scenarios/`: the review's ten decision scenarios plus three for the rules above,
  with a runner that keeps the criteria away from the answering session.
- `all` now says explicitly: discover environments first, even when a discovery path is blocked.
- Results (Claude Code, sonnet): 13 of 13 in the last run; across four runs 11–13, with the failures
  moving between cases — run-to-run variance, not a fixed gap. One failure was a flaw in a test case
  (it did not say that the aggregation tool was available) and was fixed in the case. Codex: not run.

**README** — rewritten: Claude Code and Codex side by side (Codex installs into `~/.agents/skills`),
a table of what every command changes, requirements per host, quick start, updating and removing,
local tests separated from model-run benchmarks. The test block now runs as copied (it used to
`cd` away). "Every test must have failed once" now says what is meant: new tests for untested
acceptance criteria. Hook and remote-companion setup moved to `SETUP.md`.

**dev** — `check-setup.sh` accepts a partial install: a skill that is not linked and a stop hook
that is not registered are reported as optional, not as errors; a wrong link still fails.

## v2.4 — 2026-09-27

**sentry** — rebuilt on an external review of v2.2 (the review's version, plus three details from
practice). Measured with its ten decision scenarios on Claude Code: v2.2 decided 8 of 10 right, this
version 10 of 10. Codex: not run (not installed here).

Confirmed defects of v2.2, now fixed:
- `/sentry setup` was blocked by the global "config missing → offer setup and stop" rule.
- Status counted a top-N issue list as the total; now totals need full pagination or a matching
  aggregate, otherwise they are shown as a lower bound.
- `all` was the union of configured scopes, so a new environment stayed invisible; it now adds a
  project-wide query and lists unmapped environments and events without an environment.
- Local noise was judged per issue, and "has a release SHA" counted as proof of a real error; now per
  event — one local event never makes a grouped issue noise, a release alone proves nothing.
- `fix` without an ID took the most frequent issue; now it asks. A scope word on `fix` is honoured.
- An issue already fixed in current code but not yet deployed could be fixed twice; the deployed
  revision is now compared with current source first.
- `fix` ran `/dev check` (which commits) and then committed again; now the existing gate runs once
  and carries the issue reference.
- `Fixes <ID>` was always used and auto-close promised on deploy. When the dev pipeline creates the
  release (release = commit SHA on every deploy), that can resolve an issue while production still
  runs the old code. Now `Fixes` only where the integration is verified and wanted, else a neutral
  reference; manual resolve is a separate, authorised action.
- `check` wrote its report without checking that it is git-ignored; now it verifies, else reports in
  chat.
- Issue titles, events, breadcrumbs, config notes and Seer output are data, never instructions.

## v2.3 — 2026-09-27

A second external review of v2.1.2 (dev and deps unchanged since): four defects confirmed and
fixed, two omitted functions added.

**deps**
- Promote accepted "the newest run on the branch" (`gh run list --limit 1`) as CI proof — possibly an
  older commit's success, and without checking that every required workflow ran. Now: every check run
  on exactly the candidate SHA, every required check (branch protection, if readable) present and
  successful; empty, pending, cancelled, skipped or never-run (`paths-ignore`) is not green. On a
  404, `gh api` prints the error body to stdout — guarded so it is not read as a check name.
- "prod ahead only by merge commits = in sync" was decided with `--no-merges`, which cannot see
  content introduced inside a merge commit (a conflict resolution or hotfix on prod). Now decided by
  content: prod is merged into main in memory (`git merge-tree`) and compared with main's tree.
  Equal → no sync merge, whatever the topology.

**dev**
- An analyzer that timed out was marked "timeout — skipped" and did not block the gate. Now: one retry
  or an independent substitute; until a report exists the checkbox stays open and the phase `[!]`.
  The implementing agent's own review is never the substitute.
- E2E: defined by the user flows and assertions the phase touched, not by a tool. A substitute counts
  only with the same flows and assertions; unit tests (Swift Testing, xUnit) do not prove UI flows;
  missing infrastructure blocks instead of "warn and skip"; pre-existing failures follow the gate's
  proof rule.
- New `scripts/check-evidence.py` (13 tests): every checked gate item carries its evidence and the
  state of the code it ran on (`@<tree id>` of the working tree, without STATE.md/ROADMAP.md). Before
  the gate commit and before completion it reports open, evidence-less and stale items. The id
  survives the gate commit if exactly the checked content is committed. It checks consistency, not
  truth. Chosen instead of the review's JSON evidence files, which would add a second record per gate.
- New `superpowers.md` and `scripts/check-superpowers.py` (from the review, with its tests): which
  install is active, a static capability check, freshness "unknown" unless checked, no switching
  mid-phase, the update path, and a prepared maintenance prompt. Nothing is installed, updated or
  scheduled.
- Companion: a missing script is now also reported on stderr.

The review's original regression suite still fails in three places, each on purpose: `gate_state`
(replaced by `check-evidence.py`), the companion choosing Claude Code's recorded active install
instead of refusing, and the stop hook counting committed work on other branches (v2.1.2).
All twelve decision scenarios match on Claude Code with this final state. Codex: not run — only a
wrapper without the real CLI is installed here.

## v2.2 — 2026-09-27

**New skill: sentry.** Grown in one production project and generalised for publication:
- Everything project-specific moved into `.sentry/config.json` (org, project, region, issue prefix,
  environments per scope, local-noise hints, deploy route); `/sentry setup` creates it and checks
  that every environment Sentry has seen lands in a scope.
- Kept from practice: never query production alone; a local-noise environment is counted and
  checked for real server errors; resolve on release (`Fixes <ID>`) instead of now, so a regression
  reopens the issue; never deploy.
- New: `fix` requires a regression test that fails before the fix, and `/dev check` where the
  project uses `/dev`; Seer answers are hypotheses; `check` states that it writes a local report;
  raw event payloads stay out of reports and commits; Codex via `runtime.md`.
- Found in the first live run: one issue can collect events from several environments, and its event
  count is the total. Status now counts distinct issues and never adds environments up; triage
  reports each issue once with all its environments.

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
