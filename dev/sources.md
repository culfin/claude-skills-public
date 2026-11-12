# Sources `/dev` builds on — update contract

`/dev` reads or invokes skills it does not own; each update is checked against this contract **before** it
becomes active: `fits` → applied by an update watcher; `unclear` or `conflict` → held back, old version stays
active, the user decides with `/dev updates`. Data for `scripts/check-source-update.py` (`--list-sources`,
`--help`), the watcher and its review agent — not read during phase work. **Not covered:** `vibepolish` (in
this repository, own review) and every skill `/dev` does not reference.

## Sources

`reads` are paths relative to the source root. `design/INDEX.md`, `stack/INDEX.md` and
`scripts/check-superpowers.py` there are references the checker resolves to their rows or required paths;
they belong to `/dev` (they live in this skill) — a reviewer must not expect them inside a candidate. A new use
of a source adds its paths here in the same commit.

| id | kind | location | reads | overrides |
|---|---|---|---|---|
| superpowers | plugin | `superpowers@claude-plugins-official` | `scripts/check-superpowers.py` | O1–O3, O14–O17 |
| emil | git | `$DEV_DESIGN_DIR/emil` | `design/INDEX.md`, `LICENSE` | O4 |
| taste | git | `$DEV_DESIGN_DIR/taste` | `design/INDEX.md`, `LICENSE` | O5 |
| impeccable | git | `$DEV_DESIGN_DIR/impeccable` | `design/INDEX.md`, `.claude/skills/impeccable/reference/audit.md`, `.claude/skills/impeccable/reference/polish.md`, `Cargo.toml`, `Cargo.lock`, `LICENSE` | O6, O7 |
| docker | git | `$DEV_STACK_DIR/docker` | `stack/INDEX.md`, `LICENSE` | O8, O9 |
| gha | git | `$DEV_STACK_DIR/gha` | `stack/INDEX.md`, `LICENSE` | O8, O9 |
| better-auth | git | `$DEV_STACK_DIR/better-auth` | `stack/INDEX.md` | O8, O9 |
| postgres | git | `$DEV_STACK_DIR/postgres` | `stack/INDEX.md`, `LICENSE` | O8, O9 |
| stripe | git | `$DEV_STACK_DIR/stripe` | `stack/INDEX.md`, `LICENSE` | O8, O9, O10 |
| fastify | git | `$DEV_STACK_DIR/fastify` | `stack/INDEX.md`, `LICENSE` | O8, O9 |
| wordpress | git | `$DEV_STACK_DIR/wordpress` | `stack/INDEX.md`, `LICENSE` | O8, O9, O12 |
| pg | plugin | `pg@aiguide` | `skills/design-postgres-tables/SKILL.md` | O8 |
| svelte | plugin | `svelte@svelte` | `skills/svelte-core-bestpractices/SKILL.md`, `skills/svelte-code-writer/SKILL.md` | O8 |
| shadcn | agents-skill | `~/.agents/skills/shadcn` | `SKILL.md` | O8 |
| swiftui-pro | agents-skill | `~/.agents/skills/swiftui-pro` | `SKILL.md` | O8 |
| swift-concurrency-pro | agents-skill | `~/.agents/skills/swift-concurrency-pro` | `SKILL.md` | O8 |
| swift-testing-pro | agents-skill | `~/.agents/skills/swift-testing-pro` | `SKILL.md` | O8 |
| rust-best-practices | local | `~/.claude/skills/rust-best-practices` | `SKILL.md` | O8 |
| rust-testing | local | `~/.claude/skills/rust-testing` | `SKILL.md` | O8 |
| tauri-v2 | local | `~/.claude/skills/tauri-v2` | `SKILL.md` | O8 |
| winui-pro | local | `~/.claude/skills/winui-pro` | `SKILL.md` | O8 |

## Overrides — where `/dev` deliberately departs from a source

An update that strengthens the overridden behaviour is fine; one that makes the override impossible
(the source enforces it, or `/dev`'s instruction no longer applies) is a contradiction.

- **O1** `subagent-driven-development` stops after tasks and per-task reviews: no
  `finishing-a-development-branch`, no nested worktree, no final whole-branch review (`execution.md`).
- **O2** Brainstorming asks every question via `AskUserQuestion`, recommendation first; the Visual Companion
  shows only user interface, never plans or findings (`SKILL.md` 4a, `companion.md`).
- **O3** The active install is the one Claude Code records, never "the newest cache directory"; no plugin
  switch mid-phase (`runtime.md`).
- **O4** Emil's skills open with "respond only with: I'm ready …" — `/dev` ignores that and applies the
  content directly (`design/INDEX.md`).
- **O5** taste is read only for `landing`, by a subagent returning ≤ 40 lines; conflicts with the project's
  component library become questions; `full-output-enforcement` is not used. The subagent reads only the
  files `design/INDEX.md` names; taste's scripts (dealers, `gate.mjs`, linters), its Stop hook and install
  steps never run (I4) — what taste deals by script is proposed from its `library/` and marked as such.
- **O6** impeccable: only the locally built deterministic detector is run; its `SKILL.md` and
  `audit`/`polish` references are checklists only. Never run `scripts/impeccable`, `npx impeccable`, the
  `context` step its `SKILL.md` and `polish.md` order, `install`, `hooks on`, or a downloaded binary
  (`commands.md`).
- **O7** impeccable telemetry is off: `IMPECCABLE_NO_TELEMETRY=1`, `DO_NOT_TRACK=1`.
- **O8** Stack skills and sources run as read-only reviews in gate Step A and as context in 4a/4c; their own fix or install instructions do not apply.
- **O9** Stack sources are a review yardstick and context, never an order to rebuild: the project's
  conventions win (a file name or restart policy the source prefers is not enforced); no hosted product a
  source recommends is passed on. For `read` and `subagent` rows alike nothing outside the listed file's
  folder is read — no sibling skill, no skill or instruction fetched from a URL the source names. No script
  a source ships is executed and no vendor CLI or API call is made on a source's instruction.
- **O10** stripe: only the skill files under `skills/` are read — never its plugin, hooks, MCP server or
  usage reporting (`stripe agent report_usage`).
- **O12** wordpress: O9 applies unchanged — no WP-CLI on a source's instruction anywhere; the scripts inside
  the indexed folders may be read, never run, and the sibling triage script is not run. When the task itself
  calls for WP-CLI, nothing runs against a production site without the user's go-ahead. The skills'
  "WordPress 7.0+" assumption is checked against the project's version before a rule applies.
- **O14** brainstorming: no playback or design approval; its HARD-GATE is not applied — `/dev` writes and
  commits the spec and continues; the builder check runs, its questions follow O2 (`SKILL.md` 4a).
- **O15** writing-plans: no execution-method question; `/dev` executes per `execution.md` (`SKILL.md` 4b).
- **O16** subagent-driven-development: `execution.md` uses its prompts and scripts — parallel implementers
  in worktrees (not "never parallel"), 5 fix rounds, then rulings instead of a halt, no final review or branch finishing
  (O1). Removing `implementer-prompt.md`, `task-reviewer-prompt.md`, `re-review-prompt.md`,
  `scripts/task-brief` or `scripts/review-package` is a conflict.
- **O17** systematic-debugging is `/dev debug`'s method; `debugger.md` wins, its strong wording does not. Kept:
  the obvious-fix fast path (`commands.md`), a red command before any hypothesis, questions per O2, no
  `verification-before-completion` (`test-driven-development` allowed). Replaced: "no root cause → retry or
  timeout" — timeouts under load mean re-running the same commit at low load first. Dropping its 3-failed-fixes
  rule, defense-in-depth or boundary instrumentation is a conflict; condition-based waiting never hides load.

## Invariants — must hold after every update

An update that would flip one of these is a contradiction (verdict `conflict`), whatever else it improves.

- **I1 Restrained `ui`, bold `landing`.** Product UI stays restrained and follows the project's component
  library; bold, expressive design is for `@type: landing` only.
- **I2 Target size.** 24×24 CSS px is the minimum (WCAG 2.5.8, a finding below it); 44×44 is a touch
  recommendation, reported as a note (`analyzers/accessibility.md`).
- **I3 Analyzers are read-only.** Reviews and analyzers flag; they never edit files.
- **I4 Nothing installs itself.** No hooks, no settings changes, no install steps, no pipe-to-shell;
  impeccable telemetry stays off.
- **I5 No code change before approval.** Rework (`/dev ui`, impeccable `polish`) starts only after the user
  approves specific findings.
- **I6 Load on demand only.** A source is read when its trigger fires, only the matching rows/sections;
  large files through a subagent digest. Nothing is preloaded into every session.
- **I7 Emil's "I'm ready" opening stays overridden** (O4).
- **I8 Missing means skipped.** A source that is gone yields `skipped: <reason>`, never a silent pass.
