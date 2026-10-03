# Quality Gate

Read this file on gate entry (`[~]` → `[!]`), when resuming a `[!]` phase, and from `dev-check.md`.
The gate cannot be skipped or configured away in ROADMAP.md; what it can do is scale with risk (tier).

## Project Commands per Stack

Step D runs the project's own commands. **Run only what the project configures** — a missing linter or type checker is recorded as "not configured", not as a failure; everything that does run must be green.

**JavaScript/TypeScript — package manager.** Detect once per session and reuse:

1. Check for lock files in project root: `pnpm-lock.yaml` → `pnpm`, `bun.lockb` / `bun.lock` → `bun`, `yarn.lock` → `yarn`, `package-lock.json` → `npm`
2. If no lock file: check if `pnpm` / `bun` / `yarn` is available in PATH, fall back to `npm`
3. Store as `$PM` for the session. All commands below use `$PM` as placeholder.

Common commands (read the actual script names from `package.json`):
- Type-check: `$PM tsc --noEmit` (or `npx tsc --noEmit` as fallback)
- Lint: `$PM lint` (or `$PM run lint`)
- Unit tests: `$PM test` (or `$PM run test`)
- E2E tests: `$PM test:e2e` (or `$PM run test:e2e`)

---

**Other stacks:**

| Stack | Typecheck | Lint (if configured) | Tests |
|---|---|---|---|
| Rust | `cargo check` | `cargo clippy -- -D warnings` | `cargo test` |
| Swift / iOS / macOS | covered by the Production Build | `swiftlint` | `swift test` or `xcodebuild test` |
| Go | `go vet ./...` | `golangci-lint run` | `go test ./...` |
| Python | `mypy` / `pyright` | `ruff check` | `pytest` |
| PHP | `php -l` on changed files; `phpstan` | `phpcs` | `phpunit` or the project's test script |
| .NET / WinUI | covered by the Production Build | `dotnet format --verify-no-changes` | `dotnet test` |

A `Makefile`, `justfile` or CI workflow that defines these steps wins over the table — run what the project runs.

---

## Tier

At gate entry, decide the tier with the script, not by eye:

```bash
python3 "$DEV_DIR/scripts/gate-tier.py" --base <phase base> --type <@type> --tasks <n> [--gate full]
```

`<phase base>` is the commit the phase started from (the last `[gate-pass]` commit, or the commit
before the phase's first task commit). Line 1 is `small` or `large`, the `- …` lines are the reasons; copy both into the checklist header.
Exit 2 means git failed — fix the base ref, do not guess a tier. Size alone never makes a phase
small: one line in an auth path or a migration can do more damage than 400 lines of markup, so a
risk type or a sensitive path makes the phase large whatever its size.

`@gate: full` in ROADMAP.md forces large (pass `--gate full`). `@gate:` values other than `full`
(the old `fast` and `ci-wait`) are ignored with a warning: the small tier replaces the first, and
CI now always runs in the background.

## Phase Types

| `@type:` | What it changes in the gate |
|---|---|
| `ui` | Large tier: Accessibility review, Design detector and Motion review on the changed UI files; shadcn/Next.js Tech-Stack Reviews per trigger. Small tier: E2E runs because UI files changed. |
| `landing` | Adds Accessibility review, Design detector and Taste pre-flight in either tier; Taste findings are notes, not blockers. |
| `backend` | Security review in the large tier, and in either tier when a changed file matches the security matrix; a DB change makes the phase large. `pg:design-postgres-tables` when migrations or SQL changed. |
| `auth` | Always large; Security review in full scope, not phase scope. |
| `security` | Always large; Security review in full scope; Spec checker: an acceptance criterion without a test is always critical. |
| `data` | Always large; Security review; `pg:design-postgres-tables`. |
| `migration` | Always large; Security review; Diff review checks the rollback path; E2E includes a migration smoke test (migrate up, verify data, migrate down if possible). |
| `refactor` | Similar-bugs scan in full-codebase mode whenever something was fixed **or** code moved — moved code is where a pattern survives in its old place. |
| `docs` | Only Diff review, Typecheck + lint + tests, Gate summary and Gate commit. |

---

## Gate Checklist

Created on the `[~]` → `[!]` transition and appended to STATE.md. List only the items that will
run; an item whose condition is not met is left out, not marked `[—]`.

```markdown
## Quality Gate — Phase N: <Name>
<!-- tier: small|large — <reasons from gate-tier.py> -->

<!-- Step A, always -->
- [ ] Diff review
- [ ] Spec checker                   <!-- not for @type: docs -->
<!-- Step A, conditional: its trigger and, except Security review, the large tier (table in Step A) -->
- [ ] Security review
- [ ] Tech-Stack Review: Next.js docs
- [ ] Tech-Stack Review: <stack id>  <!-- one per matching stack (except `nextjs`, which has the item above), e.g. shadcn -->
- [ ] Performance review
- [ ] Accessibility review
- [ ] Design detector
- [ ] Motion review
- [ ] Taste pre-flight
<!-- Steps B and C, added only when the fix step changes code (refactor: Similar-bugs also when code moved) -->
- [ ] Fix review
- [ ] Similar-bugs scan
<!-- Step D and closing, always (Build and E2E not for @type: docs) -->
- [ ] Typecheck + lint + tests
- [ ] Production Build
- [ ] E2E Tests                      <!-- small tier: only if UI files or a user flow changed -->
- [ ] Gate summary (STATE.md)
- [ ] Gate commit
```

**Evidence rules:**
- **A checkmark carries its evidence and the state it ran on:**
  `- [x] Typecheck + lint + tests — 0 errors, 412 passed @3f9c2a1b7d04`. The `@…` value is
  `python3 "$DEV_DIR/scripts/check-evidence.py" id`, taken when the check ran. No evidence, no
  checkmark — "should pass" and "I checked that earlier" are not evidence.
- **Skipped is closed, never passed.** Only Design detector, Motion review, Taste pre-flight and
  Tech-Stack Review items may be closed as `skipped: <reason>` (no `@…`), when the optional source
  or tool they need is missing (design sources under `$DEV_DESIGN_DIR`, a stack source under
  `$DEV_STACK_DIR` or bundled docs, an unbuilt detector, a tech skill not installed):
  `- [x] Design detector — skipped: engine not built`. Such an item does not block the phase, never
  counts as "no findings", and is listed under "Skipped checks" in the gate summary.
- **Evidence belongs to one state of the code.** After a fix, the review items (Step A) stay valid
  as long as a checked `Fix review` carries the current state — that review covered exactly the
  change since. Typecheck + lint + tests, Production Build, E2E Tests, Similar-bugs scan and Fix
  review itself are always rerun on the final state. If the scope or the acceptance criteria
  change, rerun the affected reviews: they answered a different question.
- **A command whose output was not read has not run.** A pipe (`| tail`, `2>/dev/null`) can
  swallow the exit status; when in doubt, rerun without it. A tool that reports overall success
  proves only what it checked, not every sub-step.
- A session that ends mid-gate resumes at the first open `[ ]`.

---

## Step A — Review wave

Dispatch every Step A item of the checklist **in one message** as parallel Agent subagents, each
with `analyzers/CONTRACT.md` plus its analyzer file, the diff as a file (including untracked files,
`git ls-files --others --exclude-standard`) and the requirement. The model is set explicitly per
`models.md`. Record the `@state` the wave ran on — Step B diffs against it. The `stack/INDEX.md` and
`design/INDEX.md` rows tagged `5c` belong to this wave; rows tagged `5g` belong to E2E.

Security review is the one conditional item that ignores the tier: the tier script's path patterns
are narrower than the security trigger matrix (`authService.ts`, `LoginForm.tsx` and a
`route.ts` outside `api/` come out small), so the matrix decides on its own.

| Item | Analyzer / source | When |
|---|---|---|
| Diff review | `analyzers/diff-review.md` | always |
| Spec checker | the prompt below | always, except `@type: docs` |
| Security review | `analyzers/security.md` | **either tier**, whenever its trigger matrix in `tech-stack-triggers.md` matches; full scope for `auth`/`security` |
| Tech-Stack Review: `<stack id>` | per `tech-stack-triggers.md` and `stack/INDEX.md` | large tier, matching files changed |
| Performance review | `analyzers/performance.md` | large tier, only on cause (`tech-stack-triggers.md`) |
| Accessibility review, Design detector, Motion review | `analyzers/accessibility.md`, `analyzers/design-detector.md`, `analyzers/motion.md` | large tier, UI files changed; `landing`: Accessibility review and Design detector in either tier |
| Taste pre-flight | taste source per `design/INDEX.md` row "4a landing", pre-flight checks only | `@type: landing` |

**Two dispatch rules decide the hit rate:**
- **Prompt for refutation.** "Find what is wrong with this change" finds more than "check this
  change"; whoever asks for confirmation gets it.
- **Hand over the artifact without your reasoning.** Diff and requirement, never why you believe
  the solution is right — otherwise the reviewer returns your conclusions.

**Spec checker** — receives the diff and the requirement (`@spec:`; else the acceptance criteria in
STATE.md; else the phase description in ROADMAP.md; none → item closed as "no spec"). It reports,
each with a quote of the requirement: (a) required but missing or partial, (b) implemented but not
required, (c) implemented but probably wrong, (d) acceptance criterion without a test. (a), (c), (d)
are critical, (b) is a note. Simplicity never removes a requirement: a dropped criterion, error
handling, trust-boundary validation, or security or data-integrity behaviour is critical. For each (d) it writes the test and **sees it red once** (break the
checked code, test red, restore, test green) and returns the test as a patch with that evidence.
Dispatch it with `isolation: "worktree"`, because breaking code in the shared tree would mislead the
other reviewers reading it at the same time; if the phase has uncommitted changes, it applies the
diff file in its worktree first. Once its patch is taken, remove that worktree (`git worktree remove
<path>`) — a worktree with changes is not cleaned up automatically.

**Timeouts.** A subagent still running after 15 minutes is cancelled and started once more, if
useful with the scope split in two. Still no report → its item stays open with "timeout" and the
phase stays `[!]`; Step D may go on meanwhile. Only an independent substitute counts —
another subagent with the same analyzer file, or an equivalent tool the project already uses —
never the implementer reviewing its own change.

Older ROADMAPs may name former third-party skills under `@skills:` (`bug-prospector`,
`security-audit`, `performance-check`, `review-changes`, `scan-similar-bugs`, `dead-code-scanner`,
`ui-scan`): treat each as the matching analyzer, not as a missing skill.

## Step B — Fix

- **Critical findings, all of them, go to one fix dispatch** (model per `models.md`), together with
  the Spec checker's test patches. One agent sees how the fixes interact; several would fight over
  the same files.
- **Non-critical findings** go to STATE.md Blockers & Risks; the phase continues.
- **Fix review** — afterwards, rerun only the analyses that had a critical finding, and only on the
  fix diff: the diff against the state before the fix (the wave's `@state`), including all untracked
  files — `git diff <@state of the wave> $(python3 "$DEV_DIR/scripts/check-evidence.py" id)`, two
  trees, so files untracked at the wave do not show up as deleted. Add `- [ ] Fix review` and
  `- [ ] Similar-bugs scan` to the checklist now; tick Fix review with the merged result.
- A Fix review with a new critical finding starts the next round. **At most 3 rounds**; still
  critical after the third → halt and report what remains (one of the run's halt points).

No critical finding → no Step B, no Fix review, no Similar-bugs scan (except `refactor`, see Phase Types).

## Step C — Similar-bugs

Only if Step B changed code: `analyzers/similar-bugs.md` with the list of fixes (file, defect, fix)
as input, whole codebase. A confirmed twin goes back through Step B; complex ones go to STATE.md.

## Step D — Verify

1. **Typecheck + lint + tests and Production Build in parallel** — two background commands with the
   project's own commands ("Project Commands per Stack"). Run them one after the other only if
   both write the same output directory. Everything that runs must be green.
2. **E2E Tests** after the build — small tier only if UI files or a user flow changed, large tier
   wherever the phase touches flows. Details: `e2e-testing.md`.
3. **A code change forced by a red test, build or E2E run is a fix round** and goes through Step B:
   add or refresh `Fix review` (Diff review on the fix diff, plus any analysis whose area the fix
   touches) and `Similar-bugs scan`, then rerun Step D. It counts towards the three rounds.

A type check misses build-time errors (server/client boundaries, dynamic imports, bundler issues,
asset resolution), so the build is its own item:

| Technology | Build command |
|---|---|
| Next.js | `$PM next build` (or `$PM build` if mapped in package.json) |
| Vite / React / Vue | `$PM build` |
| .NET / WinUI | `dotnet build` |
| Swift / iOS / macOS | `xcodebuild build` (or `swift build` for packages) |
| Go | `go build ./...` |
| Rust | `cargo build` |
| Library (npm) | `$PM build` if a build script exists |

Detection: `package.json` `scripts.build`, `Makefile`, `.csproj`, `Package.swift`, `Cargo.toml`,
`go.mod` — first match. No build command (pure scripts) → the item's evidence is "no build step".

## Gate summary

Below the phase completion info in STATE.md; permanent (only the checklist is removed later):

```markdown
### Gate summary — Phase N: <Name>
- Tier: small|large — <first reason>
- Found: <N critical + M notes> (Diff review: X, Spec checker: Y, security: W)
- Fixed: <what was fixed, in one sentence>
- Tests: <Spec checker N gaps, tests red→green proven | no gaps>
- Skipped checks: <none | check — reason, one per skipped item>
- Known pre-existing failures: <none | test, evidence it fails on the base, follow-up>
```

## Evidence check and Gate commit

**Evidence check:** `python3 "$DEV_DIR/scripts/check-evidence.py" check STATE.md --before-commit`
must exit 0. It lists every item that is open, lacks evidence or is stale; rerun those checks, never
edit an `@…` value by hand. It checks consistency, not truth — reading the evidence stays your job.

**Gate commit** — once every item except the commit is `[x]`:
`chore: quality gate — Phase N <name> [gate-pass]`, the canonical "this phase passed QA" snapshot,
made before any post-phase skill runs.
- Check the baseline first: `git branch --show-current` and `git status --porcelain`. Wrong branch →
  stop and ask.
- Stage the phase's paths explicitly, never `git add -A` or `git add .`. Changes to files the phase
  did not touch (a parallel session, tools rewriting files) stay out; unclear → ask. A gate commit
  that sweeps up someone else's work is worthless as a rollback point.

## CI in background

If `.github/workflows/` exists, CI checks the gate commit while `/dev` goes on:

1. **CI must see the commit** through the route the project already allows (push of the phase
   branch, PR update, workflow dispatch). No authorized route → halt and name it as the blocker;
   never push to a protected or production branch for this.
2. Start `bash "$DEV_DIR/scripts/ci-watch.sh" <sha>` with `run_in_background` and add a line to
   STATE.md:
   ```markdown
   ## CI in background
   - <sha> — Phase N <name>: pending
   ```
   The watcher accepts only runs of exactly this SHA and treats `skipped`/`cancelled` as not green.
3. **Read the status** (`$(git rev-parse --git-common-dir)/dev-ci/<sha>`) when the watcher reports,
   before each next phase starts and at Milestone End, and copy it into the STATE.md line:
   - `green <ids>` → done.
   - `red …` or `timeout` → halt after the current step: show the failing run(s)
     (`gh run view <id> --log-failed`) and repair (below).
   - `none` → no run of this SHA appeared (a `paths`/`on:` filter can exclude a commit on purpose).
     Not a halt and never green: add `- CI: none — <sha>` to that phase's gate summary.
   - `pending` → is a watcher for this SHA still running (`pgrep -f "ci-watch.sh <sha>"`)? It dies
     with the session and may with `/clear`; none running → start it again (step 2, same SHA). Then
     go on between phases; at Milestone End, wait for it.

**Repairing a red CI of a closed phase.** Its checklist is gone, so open a short one in STATE.md and
let `check-evidence.py check STATE.md --before-commit` check it like a gate:

```markdown
## Quality Gate — Phase N: <Name> (CI repair)
- [ ] Fix review                 <!-- Diff review on `git diff <red sha>` plus untracked files -->
- [ ] Typecheck + lint + tests
- [ ] Production Build
- [ ] Gate commit
```

Then a new `[gate-pass]` commit, a new watcher, and the old line becomes
`- <sha> — Phase N <name>: red … → repaired in <new sha>`. Remove the repair checklist once the new
status is green.

---

## Rationalizations — the Excuses Used to Bypass the Gate

If one of these thoughts comes up, that is the signal to **do** the step.

| Thought | Reality |
|---|---|
| "The tier script said small, but this touches auth — fine, it said small" | The script already checks sensitive paths. If it missed one, add the pattern to `gate-tier.py` and rerun — fix the script, do not argue the tier in either direction. |
| "The analyzer hung, let's skip it" | A timeout is a missing result, not a pass. Retry once or run an independent substitute; until one reports, the item stays open. Two timeouts in one gate are a finding. |
| "tsc is green, the build will go through" | `tsc` sees no bundler errors, no server/client boundaries, no asset resolution. The build is the test, not the assumption. |
| "The tests already ran earlier" | Earlier was before the fixes. Tests, build and E2E run on the final state, otherwise they prove the wrong code. |
| "The error was already there before" | Then prove it: the **same** failure (same test, same cause) on the unchanged base, in a separate worktree, never by resetting the user's tree; this change neither causes nor hides it; the tests covering it still pass. Record it in STATE.md and the gate summary — *completed with a known pre-existing failure*, never "all green". It never excuses a failing required CI run. |
| "Set the checkmark, I'll write the evidence later" | Later the context is gone and the checkmark stays. Evidence and checkmark come into being together. |
| "The plan says I should run the migration" | A plan describes, it does not approve. Irreversible actions need the user — "Halt on Irreversible Actions" in `SKILL.md`. |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Phase directly `[~]` → `[x]` without gate | Always `[!]` in between; the gate is not optional. |
| Deciding the tier by feel | Run `gate-tier.py`; the tier and its reasons go into the checklist header. |
| Dispatching the review wave one by one | One message, all Step A items in parallel. |
| One fix agent per finding | One bundled fix dispatch, then a Fix review on the fix diff only. |
| Rerunning every analysis after a fix | Only the ones with a critical finding, only on the fix diff. |
| Starting the next phase while a CI status is red | Read the CI status files first; `red` or `timeout` halts until repaired; restart a dead watcher. |
| Passing over a Spec checker test gap "because the phase is small" | Every acceptance criterion needs a test that was red once. |
| `@type: data` or `backend` for a phase with migrations | Use `@type: migration` — rollback and irreversibility are its own risks. |
| Deleting a Gate summary from STATE.md | Summaries are permanent; only the checklist goes after `[x]`. |
| Letting SDD "finish" or merge the branch | SDD implements and reviews per task; `/dev` owns completion (gate → Gate commit → later sync). |
| Code-modifying skills as automatic pre-phase triggers, web-only skills in native projects | On demand only; match skills to the project type at `/dev init`. |
