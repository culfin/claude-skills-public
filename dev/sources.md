# Sources `/dev` builds on — update contract

`/dev` reads or invokes skills it does not own. A new version of one of them can quietly change
how `/dev` behaves, so each update is checked against this contract **before** it becomes active:
fits → applied by the update watcher (with a log line); unclear or contradicting → held back, the
old version stays active, and the user decides with `/dev updates` (`updates.md`).

Read by: the update watcher, `scripts/check-source-update.py` (the table), the review agent and
`/dev updates` (table, overrides, invariants). Not loaded during normal phase work.

**Not covered:** `vibepolish` (lives in this repository, changes go through its own review) and
every skill or plugin `/dev` does not reference — those update without this check.

## Sources

`reads` lists paths relative to the source root. Two entries are references instead of copies,
resolved by the checker: `design/INDEX.md` = every row of that file under `$DEV_DESIGN_DIR/<id>/`;
`scripts/check-superpowers.py` = its `required_paths()`. Kinds: `plugin` (Claude Code plugin cache,
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>`), `git` (checkout, fast-forward),
`agents-skill` (`~/.agents/skills/<id>`, installed by the `skills` CLI), `local` (a copy without an
upstream — nothing to watch until it gets one).

| id | kind | location | reads | overrides |
|---|---|---|---|---|
| superpowers | plugin | `superpowers@claude-plugins-official` | `scripts/check-superpowers.py` | O1, O2, O3 |
| emil | git | `$DEV_DESIGN_DIR/emil` | `design/INDEX.md`, `LICENSE` | O4 |
| taste | git | `$DEV_DESIGN_DIR/taste` | `design/INDEX.md`, `LICENSE` | O5 |
| impeccable | git | `$DEV_DESIGN_DIR/impeccable` | `design/INDEX.md`, `.claude/skills/impeccable/reference/audit.md`, `.claude/skills/impeccable/reference/polish.md`, `Cargo.toml`, `Cargo.lock`, `LICENSE` | O6, O7 |
| pg | plugin | `pg@aiguide` | `skills/design-postgres-tables/SKILL.md` | O8 |
| svelte | plugin | `svelte@svelte` | `skills/svelte-core-bestpractices/SKILL.md`, `skills/svelte-code-writer/SKILL.md` | O8 |
| next-best-practices | agents-skill | `~/.agents/skills/next-best-practices` | `SKILL.md` | O8 |
| shadcn | agents-skill | `~/.agents/skills/shadcn` | `SKILL.md` | O8 |
| swiftui-pro | agents-skill | `~/.agents/skills/swiftui-pro` | `SKILL.md` | O8 |
| swift-concurrency-pro | agents-skill | `~/.agents/skills/swift-concurrency-pro` | `SKILL.md` | O8 |
| swift-testing-pro | agents-skill | `~/.agents/skills/swift-testing-pro` | `SKILL.md` | O8 |
| rust-best-practices | local | `~/.claude/skills/rust-best-practices` | `SKILL.md` | O8 |
| rust-testing | local | `~/.claude/skills/rust-testing` | `SKILL.md` | O8 |
| tauri-v2 | local | `~/.claude/skills/tauri-v2` | `SKILL.md` | O8 |
| winui-pro | local | `~/.claude/skills/winui-pro` | `SKILL.md` | O8 |

Where each is used: superpowers — `SKILL.md` steps 4a–4d, `companion.md`, `superpowers.md`;
design sources — `design/INDEX.md`, `analyzers/motion.md`, `analyzers/design-detector.md`,
`commands.md` (Pre-Release Review); stack skills — `tech-stack-triggers.md`. A new use of a source
adds its paths here in the same commit.

## Overrides — where `/dev` deliberately departs from a source

An update that strengthens the overridden behaviour is still fine; one that makes the override
impossible (the source now enforces it, or `/dev`'s instruction no longer applies) is a contradiction.

- **O1** `subagent-driven-development` stops after tasks and per-task reviews: no
  `finishing-a-development-branch`, no nested worktree, no final whole-branch review (`SKILL.md` 4c).
- **O2** Brainstorming asks every question via `AskUserQuestion`, recommendation first; the Visual
  Companion shows only user interface, never plans or findings (`SKILL.md` 4a, `companion.md`).
- **O3** The active install is the one Claude Code records, never "the newest cache directory"; no
  plugin switch mid-phase (`superpowers.md`).
- **O4** Emil's skills open with "respond only with: I'm ready …" — `/dev` ignores that and applies
  the content directly (`design/INDEX.md`).
- **O5** taste is read only for `landing`, by a subagent returning ≤ 40 lines; conflicts with the
  project's component library become questions; `full-output-enforcement` is not used.
- **O6** impeccable: only the locally built deterministic detector and the `audit`/`polish`
  references are used — never its launcher, `install`, `hooks on`, or downloaded binaries.
- **O7** impeccable telemetry is off: `IMPECCABLE_NO_TELEMETRY=1`, `DO_NOT_TRACK=1`.
- **O8** Stack skills run as read-only reviews in gate step 5c and as context in 4a/4c; their own
  "fix it now" or install instructions do not apply there.

## Invariants — must hold after every update

An update that would flip one of these is a contradiction (`widerspruch`), whatever else it improves.

- **I1 Restrained `ui`, bold `landing`.** Product UI stays restrained and follows the project's
  component library; bold, expressive design is for `@type: landing` only.
- **I2 Target size.** 24×24 CSS px is the minimum (WCAG 2.5.8, a finding below it); 44×44 is a
  touch recommendation, reported as a note (`analyzers/accessibility.md`).
- **I3 Analyzers are read-only.** Reviews and analyzers flag; they never edit files.
- **I4 Nothing installs itself.** No hooks, no settings changes, no install steps, no
  pipe-to-shell; impeccable telemetry stays off.
- **I5 No code change before approval.** Rework (`/dev ui`, impeccable `polish`) starts only after
  the user approves specific findings.
- **I6 Load on demand only.** A source is read when its trigger fires, only the matching
  rows/sections; large files through a subagent digest. Nothing is preloaded into every session.
- **I7 Emil's "I'm ready" opening stays overridden** (O4).
- **I8 Missing means skipped.** A source that is gone yields `skipped: <reason>`, never a silent pass.

## Deterministic check

`python3 "$DEV_DIR/scripts/check-source-update.py" --source <id> --old <dir> --new <dir>` compares
two trees of one source. Finding kinds: `missing-read-path`, `frontmatter-switch-changed`
(`disable-model-invocation`, `user-invocable`, `allowed-tools` in a read file), `new-hook` (in JSON:
any added or changed hook entry, compared entry by entry), `new-settings-json`, `new-pipe-to-shell`,
`new-install-step`, `new-network-access` (scripts and JSON), `license-changed`, `size-jump` (a read
file more than doubled). Otherwise "new" means more matches in that file than before. Findings are
input for the review against overrides and invariants, not a verdict — except `missing-read-path`,
`new-hook`, `new-settings-json`, `new-pipe-to-shell`, `new-install-step`, `license-changed` and
`scan-incomplete` (a new or changed script/JSON file too large to scan; only `.git` is skipped): these
always hold the update for the user's decision, whatever the review says (`--hold-kinds`).
`--list-sources` prints `id<TAB>kind<TAB>location` per row, so nothing else parses this table.
