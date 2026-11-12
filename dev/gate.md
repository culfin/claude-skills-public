# Quality Gate

The gate cannot be skipped or configured away; it scales with risk (tier).

## Project Commands per Stack

Step D runs the project's own commands. **Run only what the project configures** — a missing linter or type checker is "not configured", not a failure; everything that runs must be green.
`$PM` (once per session) from the lock file: `pnpm-lock.yaml` → `pnpm`, `bun.lockb`/`bun.lock` →
`bun`, `yarn.lock` → `yarn`, `package-lock.json` → `npm`; none → first of `pnpm`/`bun`/`yarn` in PATH,
else `npm`. JS/TS script names from `package.json` (or `$PM run …`).

| Stack | Typecheck | Lint (if configured) | Tests | Build |
|---|---|---|---|---|
| JS/TS | `$PM tsc --noEmit` | `$PM lint` | `$PM test`, E2E `$PM test:e2e` | Next.js `$PM next build` (or a mapped `$PM build`); Vite, React, Vue, npm library: `$PM build` |
| Rust | `cargo check` | `cargo clippy -- -D warnings` | `cargo test` | `cargo build` |
| Swift / iOS / macOS | covered by the Production Build | `swiftlint` | `swift test` or `xcodebuild test` | `xcodebuild build` (or `swift build` for packages) |
| Go | `go vet ./...` | `golangci-lint run` | `go test ./...` | `go build ./...` |
| Python | `mypy` / `pyright` | `ruff check` | `pytest` | — |
| PHP | `php -l` on changed files; `phpstan` | `phpcs` | `phpunit` or the project's test script | — |
| .NET / WinUI | covered by the Production Build | `dotnet format --verify-no-changes` | `dotnet test` | `dotnet build` |

A `Makefile`, `justfile` or CI workflow defining these steps wins over the table. Build detection: `package.json` `scripts.build`, `Makefile`, `.csproj`, `Package.swift`, `Cargo.toml`,
`go.mod` — first match; none (pure scripts) → the item's evidence is "no build step".

---

## Tier

At gate entry, decide the tier with the script, not by eye:

```bash
python3 "$DEV_DIR/scripts/gate-tier.py" --base <phase base> --type <@type> --tasks <n> [--gate full]
```

`<phase base>` is the phase file's `Phase base:` line; a CI repair never changes it (none recorded,
or a `Phase head:` line: `commands.md`, `phase file missing:`). `*.md` files count only towards sensitive paths,
not size. Line 1 is `small` or `large`, the `- …` lines are the reasons; copy both into the checklist
header. Exit 2 means git failed — fix the base ref, never guess a tier. `@gate: full` forces large (`--gate full`).

## Phase Types

**The diff decides the gate; a type can only add reviewers or raise the tier, never remove one.**
Reviewers come from the changed files (Step A) and `gate-tier.py`.

**Phase Types — planning hints:**

| `@type:` | In planning |
|---|---|
| `ui`, `landing` | UX clarification and companion (`tech-stack-triggers.md`, 4a) |
| `migration` | The mandatory halt (`SKILL.md`, "Halt on Irreversible Actions") |
| `docs` | No interview; no Production Build or E2E Tests — only with a `*.md`-only diff |
| `refactor` | None; its gate addition is below |

**Gate additions by type (they only add, never remove):**

| `@type:` | Adds |
|---|---|
| `migration` | Security review; Diff review checks the rollback path; E2E includes a migration smoke test (migrate up, verify data, migrate down if possible) |
| `backend` | Large tier: Security review; with `postgres` also `pg:design-postgres-tables` when migrations or SQL changed |
| `data` | `pg:design-postgres-tables` with `postgres`, when migrations or SQL changed |
| `auth`, `security`, `data` | Security review in full scope, not phase scope |
| `landing` | Accessibility review, Design detector and Taste pre-flight in either tier; Taste findings are notes |
| `refactor` | Similar-bugs scan also when code moved (Step C) |

The rollback check and the smoke test also apply whenever `gate-tier.py` names `DB change:`.

---

## Gate Checklist

Appended to the phase file (`state.md`) at `[~]` → `[!]`, listing only items that will run.

```markdown
## Quality Gate — Phase N: <Name>
<!-- tier: small|large — <reasons from gate-tier.py> -->

<!-- Step A, always -->
- [ ] Diff review
- [ ] Spec checker
<!-- Step A, conditional: trigger and, except Security review, large tier (Step A) -->
- [ ] Security review
- [ ] Tech-Stack Review: Next.js docs
- [ ] Tech-Stack Review: <stack id>  <!-- one per matching stack (except `nextjs`, which has the item above), e.g. shadcn -->
- [ ] Performance review
- [ ] Accessibility review
- [ ] Design detector
- [ ] Motion review
- [ ] Taste pre-flight
- [ ] Second opinion: <agent>     <!-- defaults.second-opinion set; runtime.md "Orca" -->
<!-- Steps B and C, only when Step B fixes a defect (test patches alone: Fix review only; refactor: Similar-bugs also when code moved) -->
- [ ] Fix review
- [ ] Similar-bugs scan
<!-- Step D and closing, always; Build and E2E: not for `@type: docs` with a `*.md`-only diff (Phase Types) -->
- [ ] Typecheck + lint + tests
- [ ] Production Build
- [ ] E2E Tests                      <!-- small tier: only if UI files or a user flow changed -->
- [ ] Gate summary (docs/gates/phase-N.md)
- [ ] Gate commit
```

**Evidence rules:**
- **A checkmark carries its evidence and the state it ran on:**
  `- [x] Typecheck + lint + tests — 0 errors, 412 passed @3f9c2a1b7d04`. The `@…` value is
  `python3 "$DEV_DIR/scripts/check-evidence.py" id`, taken when the check ran. No evidence, no
  checkmark — "should pass" and "I checked that earlier" are not evidence. **Test items name how
  many tests ran,** per suite (`unit 412 passed, e2e 18 passed`), or `no tests configured`: a runner
  that found no tests exits green too. `check-evidence.py` rejects a missing count or a 0.
- **Skipped is closed, never passed.** Only Design detector, Motion review, Taste pre-flight,
  Second opinion and Tech-Stack Review items may be closed as `skipped: <reason>` (no `@…`), when the optional source
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

---

## Step A — Review wave

Dispatch every Step A item of the checklist **in one message** as parallel Agent subagents, each
with `analyzers/CONTRACT.md` plus its analyzer file, the diff as a file (including untracked files,
`git ls-files --others --exclude-standard`), the requirement and its model (`models.md`). Record the
wave's `@state` — Step B diffs against it. `stack/INDEX.md` and `design/INDEX.md` rows tagged `5c`
belong to this wave, `5g` to E2E.

| Item | Analyzer / source | When |
|---|---|---|
| Diff review | `analyzers/diff-review.md` | always |
| Spec checker | the prompt below | always |
| Security review | `analyzers/security.md` | **either tier**, whenever its trigger matrix in `tech-stack-triggers.md` matches, including a `gate-tier.py` reason `ops files` or `dependency manifest`, or a gate addition by type; full scope for `auth`/`security`/`data` |
| Tech-Stack Review: `<stack id>` | per `tech-stack-triggers.md` and `stack/INDEX.md` | large tier, matching files changed |
| Performance review | `analyzers/performance.md` | large tier, only on cause (`tech-stack-triggers.md`) |
| Accessibility review, Design detector, Motion review | `analyzers/accessibility.md`, `analyzers/design-detector.md`, `analyzers/motion.md` | large tier, UI files changed; `landing`: Accessibility review and Design detector in either tier |
| Taste pre-flight | taste source per `design/INDEX.md` row "4a landing", pre-flight checks only | `@type: landing` |
| Second opinion: `<agent>` | `analyzers/diff-review.md`, run by that agent as an Orca worker (`runtime.md`, "Orca") | either tier, `defaults.second-opinion` set |

**Dispatch rules** (`analyzers/CONTRACT.md`, also for Spec checker and Second opinion): prompt for
refutation; hand over diff and requirement, never your reasoning.

**Spec checker** — gets the diff and the requirement (`@spec:`, else the phase file's acceptance
criteria, else the ROADMAP.md phase description; none → item closed as "no spec"). It numbers
the acceptance criteria (C1, C2, …) and returns a verdict table first —
`C1 | met / not met / untested | test name or file:line` — then its findings, each with a quote of the requirement: (a) required but missing or partial, (b) implemented but not
required, (c) implemented but probably wrong, (d) acceptance criterion without a test. (a), (c), (d)
are critical, (b) is a note. For each (d) it writes the test and **sees it red once** (break the
checked code, test red, restore, test green) and returns the test as a patch with that evidence.
Dispatch it with `isolation: "worktree"` (broken code in the shared tree misleads the other
reviewers) and the phase HEAD sha: its worktree may start from `<main>` or in another checkout, so
it first runs `git checkout --detach <sha>`, then applies the diff file for uncommitted changes.
Its patch saved: `git worktree remove --force <path>`, `git branch -D` its own agent branch only. Simplicity never removes a
requirement: a dropped criterion, error handling, trust-boundary validation, or security or
data-integrity behaviour is critical.

**Effect probe** (Spec checker, large tier only; verdict table stays in both) — for at most 2 security- or contract-critical criteria `met` by an
existing test: name that test, break the guarding line in its worktree (comment out, negate, default
value), run only that test, restore. Still green → critical, the test cannot fail; no named red
test → invalid, not passed.

**Timeouts.** A subagent still running after 15 minutes is cancelled and started once more, if
useful with the scope split in two. Still no report → its item stays open with "timeout", the phase
stays `[!]`; Step D may go on. Only an independent substitute counts (another subagent with the
same analyzer file, or an equivalent tool the project uses), never the implementer on its own change.

Former skill names in `defaults.phase-types` lists (`bug-prospector`, `security-audit`, `performance-check`,
`review-changes`, `scan-similar-bugs`, `dead-code-scanner`, `ui-scan`) mean the matching analyzer.

## Step B — Fix

- **Critical findings, all of them, go to one fix dispatch** (model per `models.md`) with the Spec
  checker's test patches — one agent sees how fixes interact; it follows `receiving-code-review`.
  Lowering the floor (skipping a test, loosening a check) is not a fix. When the cause of a finding
  or red run is unclear, the fix agent follows `superpowers:systematic-debugging`.
- **Non-critical findings** go to the phase file's `## Minor (deferred)`; the phase continues.
- **Fix review** — afterwards, rerun only the analyses that had a critical finding, with the
  requirement (a weakened criterion is critical), only on the fix diff against the wave's `@state`, untracked files included:
  `git diff <@state of the wave> $(python3 "$DEV_DIR/scripts/check-evidence.py" id)` (two trees, so
  files untracked at the wave do not show as deleted). Add `- [ ] Fix review` (and
  `- [ ] Similar-bugs scan` if a defect was fixed) now; tick Fix review with the merged result.
- A Fix review with a new critical finding starts the next round. Two analyses disagree → the
  requirement's wording decides; it does not → ask the user (once per run). **The limit counts attempts per
  finding, not rounds:** halt and report when the same critical finding — or a regression caused by
  an earlier fix — is still open after 3 attempts (one of the run's halt points). New, different
  findings neither reset nor use up a count; rounds that only implement a user decision, only change
  test code, or only take along notes do not count. Backstop: halt after 6 rounds in total.

No critical finding → no Step B, no Fix review, no Similar-bugs scan (except `refactor`, Step C).

## Step C — Similar-bugs

Only if Step B fixed a defect, or `@type: refactor` moved code (a pattern survives in its old
place): `analyzers/similar-bugs.md` with the list of fixes (file, defect, fix) or of the moves as
input, whole codebase. A confirmed twin goes back through Step B; complex ones go to `## Minor (deferred)`.

## Step D — Verify

1. **Typecheck + lint + tests and Production Build in parallel** — two background commands
   ("Project Commands per Stack"); one after the other only if both write the same output directory.
   Before `[gate-pass]` also run `python3 "$DEV_DIR/scripts/floor-guard.py" --base <phase base>` (`--root` as for the tier); its result
   (`floor-guard: 0 critical` or the list) joins that evidence. A critical finding blocks: undo it,
   or record it in `.floor-guard-allow` with the reason after the user's explicit approval. Notes
   (type or lint suppressions) never block; list them in the gate summary.
2. **E2E Tests** after the build — small tier only if UI files or a user flow changed, large tier
   wherever the phase touches flows (`e2e-testing.md`).
3. **A code change forced by a red test, build or E2E run is a fix round** and goes through Step B:
   add or refresh `Fix review` (Diff review on the fix diff, plus any analysis whose area the fix
   touches) and `Similar-bugs scan`, then rerun Step D. It counts as an attempt on the finding it fixes.

## Gate summary

Permanent, in `docs/gates/phase-<N>.md` before the gate commit (old format: STATE.md):

```markdown
## Gate summary — Phase N: <Name>
- Tier: small|large — <first reason>
- Found: <N critical + M notes> (Diff review: X, Spec checker: Y, security: W)
- Fixed: <what was fixed, in one sentence>
- Tests: <Spec checker N gaps, tests red→green proven | no gaps>
- Criteria: <C1 met (<test>); C2 untested → test added; …>; effect probe: <C2 red | none | skipped (small tier)>
- Skipped checks: <none | check — reason, one per skipped item>
- Known pre-existing failures: <none | test, evidence it fails on the base, follow-up>
```

## Evidence check and Gate commit

**Evidence check:** `python3 "$DEV_DIR/scripts/check-evidence.py" check --before-commit` must
exit 0. It lists every open, evidence-less or stale item; rerun those checks, never edit an `@…`
value by hand. It checks consistency, not truth — reading the evidence stays your job.

**Gate commit** — once every other item is `[x]`, before any post-phase skill:
`chore: quality gate — Phase N <name> [gate-pass]`.
- First `git branch --show-current` and `git status --porcelain`. Wrong branch → stop and ask.
- Stage the phase's paths explicitly, `.dev/phase-<N>.md` and `docs/gates/phase-<N>.md` included,
  never `git add -A` or `git add .`. Changes to files the phase did not touch (a parallel session, tools rewriting files) stay out; unclear → ask.
- Then `ci-watch.sh` on the gate commit (`ci.md`).

---

## Rationalizations — the Excuses Used to Bypass the Gate

If one of these thoughts comes up, that is the signal to **do** the step.

| Thought | Reality |
|---|---|
| "The tier script said small, but this touches auth — fine, it said small" | If it missed a sensitive path, rerun the tier with `--gate full` and note the missed path in the gate summary; never argue the tier. |
| "The analyzer hung, let's skip it" | A timeout is a missing result, not a pass ("Timeouts", Step A). |
| "The error was already there before" | Then prove it: the **same** failure (same test, same cause) on the unchanged base, in a separate worktree, never by resetting the user's tree; this change neither causes nor hides it; the tests covering this change still run and pass. Record it in the gate summary — *completed with a known pre-existing failure*, never "all green". It never excuses a failing required CI run. |
