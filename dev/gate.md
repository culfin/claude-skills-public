# Quality Gate — steps 5a–5k

Read this file on gate entry (`[~]` → `[!]`), when resuming a `[!]` phase, and from `dev-check.md`.
The gate is **mandatory**: it cannot be skipped and not configured away via ROADMAP.md.

## Subagent Model Choice

`/dev` dispatches many parallel Agent subagents. **Always specify a model explicitly when dispatching** — an omitted model inherits the most expensive session model (lesson from superpowers 6.x SDD). Choose the cheapest tier that can handle the task:

| Role | Tier |
|-------|------|
| Read-only analysis in Step 5c: Bug hunt, Performance review, Tech-Stack Review | **cheap tier** |
| Security review (phase or full scope), Spec checker (5c-v) | **standard/capable tier** |
| Milestone-end & pre-release full scans (Bug hunt full, Performance review full, Security review full, Dead-code scan full) | **capable tier** |

Only the **dispatch model choice** is affected — which checks run and their triggers remain unchanged.

---

---

## Project Commands per Stack

Gate steps 5e–5g run the project's own commands. **Run only what the project configures** — a missing linter or type checker is recorded as "not configured", not as a failure; everything that does run must be green.

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
| Swift / iOS / macOS | covered by the build (5f) | `swiftlint` | `swift test` or `xcodebuild test` |
| Go | `go vet ./...` | `golangci-lint run` | `go test ./...` |
| Python | `mypy` / `pyright` | `ruff check` | `pytest` |
| PHP | `php -l` on changed files; `phpstan` | `phpcs` | `phpunit` or the project's test script |
| .NET / WinUI | covered by the build (5f) | `dotnet format --verify-no-changes` | `dotnet test` |

A `Makefile`, `justfile` or CI workflow that defines these steps wins over the table — run what the project runs.

---

### Built-in Phase Types

| `@type:` | Special behavior in the Quality Gate |
|----------|------------------------------|
| `ui` | Tech-Stack Review shadcn/next-best-practices conditionally active. Accessibility review now triggers on changed UI files for any phase type (see `tech-stack-triggers.md`), not only here. |
| `landing` | taste pre-flight checks (`$DEV_DESIGN_DIR/taste/skills/taste-skill/SKILL.md`) run as notes, not blockers; Accessibility review always active |
| `backend` | Security review always active (even without auth files); pg:design-postgres-tables conditionally active |
| `auth` | Security review always active (full scope, not phase scope) |
| `security` | Security review always active (full scope); Spec checker: acceptance criteria without a test are always critical |
| `refactor` | Similar-bugs scan in full-codebase mode instead of phase scope |
| `data` | pg:design-postgres-tables always active; Security review active |
| `migration` | Specific risks: irreversibility, data loss. In addition to the `data` checks: (1) Security review always active, (2) Bug hunt explicitly checks for a missing DOWN migration / rollback path, (3) the E2E test must include a migration smoke test (migrate up + verify data + migrate down if possible). `@gate: fast` is FORBIDDEN for migration phases. |
| `docs` | Purely documentation phases (README, API docs, changelog, CLAUDE.md). Minimal gate: `/simplify`, Change review, typecheck + lint run normally. **Dropped automatically:** Security review, E2E Tests, Production Build, Spec checker (5c-v), Similar-bugs scan, Performance review, Tech-Stack Review. `@gate: fast` is semantically wrong here — use `@type: docs` instead. |

### `@gate:` Annotation — Controlling the Gate Mode

Phases can control the gate mode via a `@gate:` annotation:

| Annotation | Effect |
|------------|--------|
| `@gate: full` | Standard — all steps run (default, does not need to be specified) |
| `@gate: fast` | Skips conditional parallel checks (Tech-Stack Review, Security review, Similar-bugs scan). Mandatory steps (simplify, Change review, Bug hunt, Performance review, tsc, build, E2E) always run. For fast iteration phases. |
| `@gate: ci-wait` | Adds an explicit CI status wait before `[x]`, even if CI is otherwise not configured. |

**When to use `@gate: fast`:** Only for config-only changes or when you deliberately want to iterate fast. Pure documentation phases use `@type: docs` instead (a smaller gate than `fast`). Never for phases with auth, API, or DB changes.

**Conflict rule — `@gate: fast` is automatically ignored for:**
- `@type: security`, `@type: auth` — security checks are always mandatory for these types
- `@type: backend` with DB migrations — Security review stays active
- `@type: refactor` — Similar-bugs scan stays active in full-codebase mode, even with `@gate: fast`. Refactoring moves code — that is exactly the case where similar bug patterns can show up elsewhere. Similar-bugs scan is the only CONDITIONAL check that runs for refactor phases despite `@gate: fast`.
- If changed files match auth/API/migration patterns — Security review stays active regardless of `@gate:`

On conflict: warn (`"@gate: fast ignored — @type:auth requires full gate"` / `"@gate: fast: Similar-bugs scan stays active — @type:refactor"`), then continue with the override.

---

---

## Gate Checklist

Created on the `[~]` → `[!]` transition (step 4e in `SKILL.md`). Format (append to STATE.md):

The checklist is **dynamically generated** at gate entry based on `$TECH_STACKS` and which files were changed. Only include items that will actually run.

```markdown
## Quality Gate — Phase N: <Name>
<!-- @gate: full | fast (default: full) -->

<!-- MANDATORY — always, even with @gate: fast -->
- [ ] /simplify
- [ ] Change review
- [ ] Bug hunt (phase scope)
- [ ] Performance review (phase scope)
- [ ] Spec checker (5c-v)                      <!-- against @spec:, otherwise chat draft from STATE.md -->
<!-- CONDITIONAL — dropped with @gate: fast; omit if condition not met -->
- [ ] Tech-Stack Review: next-best-practices   <!-- next.config.* changed -->
- [ ] Tech-Stack Review: shadcn                <!-- components/** with shadcn imports -->
- [ ] Tech-Stack Review: pg:design-postgres-tables  <!-- migrations/SQL changed -->
- [ ] Accessibility review  <!-- UI files changed -->
- [ ] Security review                           <!-- auth/api/migration changed OR @type: backend/auth/security/data -->
- [ ] Similar-bugs scan                       <!-- dropped with @gate: fast -->

<!-- MANDATORY — always, even with @gate: fast -->
- [ ] Typecheck + lint + tests
- [ ] Production Build
- [ ] E2E Tests

<!-- MANDATORY — always -->
- [ ] Gate summary (STATE.md)
- [ ] Gate commit
- [ ] CI status check                          <!-- only if CI configured OR @gate: ci-wait -->
```

**Rules for creating the checklist:**
- Create the checklist immediately on the `[~]` → `[!]` transition
- Read the phase's `@gate:` annotation — with `fast`: omit all CONDITIONAL entries
- **`@type: docs`**: omit all CONDITIONAL entries + additionally omit `Production Build`, `E2E Tests` and `Spec checker (5c-v)`. Only `/simplify`, Change review, `Typecheck + lint + tests`, `Gate summary`, `Gate commit` remain.
- Omit conditional entries if the condition is not met — do not mark them `[—]`, just omit them
- Each step checks off its entry after completion
- **Every checkmark needs evidence.** An `[x]` is only set if the step has run
  AND the decisive output line follows it, plus the state of the code it ran on:
  `- [x] Typecheck + lint + tests — 0 errors, 412 passed @3f9c2a1b7d04`.
  The `@…` value comes from `python3 "$DEV_DIR/scripts/check-evidence.py" id`, taken when the check
  ran (a tree id of the working tree without STATE.md/ROADMAP.md; it survives the gate commit
  unchanged if exactly that content is committed).
  No evidence → the checkmark stays open. "Looks right", "should pass" and "I already checked
  that earlier" are not evidence.
- **Evidence belongs to one state of the code.** Any code change after a check — a fix from 5c,
  a simplification, a rebase — reopens every checkmark whose scope it touches; rerun those checks on
  the new state. A result from before the change is history, not evidence. The same holds without a
  code change: if the scope or the acceptance criteria of the check change, an earlier review of the
  same commit answered a different question — run it again.
- **A command whose output was not read has not run.** Exit code 0 is not enough if the
  output went through a pipe (`| tail`, `| head`, `2>/dev/null`) — a pipe can swallow the
  status of the left-hand side. When in doubt, repeat the command without the pipe.
- **"Success" at the overall level does not prove the sub-steps.** A green CI run, a green
  deploy or a tool that reports success may have skipped or silently
  omitted sub-steps. What is proven is the step that was checked — not the frame it ran in.
- If the session ends mid-gate: the next session reads STATE.md and resumes at the first open `[ ]`
- CI status check: only include if `.github/workflows/` exists or `@gate: ci-wait` is set

---

### 5. Mandatory Quality Gate

**MANDATORY — cannot be skipped, not optional. All steps run after every phase.**

These steps run regardless of `@skills:` configuration — they are hardcoded into the phase lifecycle and cannot be overridden or removed via ROADMAP.md annotations. The phase stays `[!]` until every checklist item is `[x]`.

**5a. /simplify** — modifies code: reviews all changed code for reuse, quality, and efficiency; fixes issues automatically. Must run first so that Change review sees the cleaned-up code.
- After completion: check off `[ ] /simplify` in STATE.md Gate Checklist.

**5b. Change review** (`analyzers/review.md`) — a broad first pass over the whole diff (after simplify): does it meet the requirement, is anything missing or stray, are there tests, is anything irreversible in it. Read-only — flags issues, does not auto-fix.
- **Critical issues** (security vulnerabilities, data loss risks, logic errors): fix them before proceeding to 5c.
- **Warnings** (style, minor improvements): note them but proceed — `/simplify` already handled code quality.
- After completion: check off `[ ] Change review` in STATE.md Gate Checklist.

**5c. Parallel Analysis Block** — dispatch the following as **parallel Agent subagents** (all read-only). **Set the model explicitly** (see "Subagent Model Choice" above: bug hunt/performance/Tech-Stack → cheap tier, Security review → standard/capable). Wait for all, at most **15 minutes** each. A subagent still running after 15 minutes is cancelled and
**started once more** — as a fresh subagent, if useful with the scope split in two. Still no report →
its checkbox stays open with "timeout", the phase stays `[!]`, and you say so. Meanwhile the rest of the
gate may go on (5d–5g do not wait for it), but the phase cannot be completed without that report.
Only an **independent** substitute counts: another subagent with the same analyzer file, or an
equivalent tool the project already uses for the same questions — never the implementing agent
reviewing its own change. Record which substitute ran and why it covers the same checks.

**Dispatch prompt for the analyzers — two rules that determine the hit rate:**
- **Prompt for refutation, not for checking.** "Find what is wrong with this change"
  yields different results than "check this change". Whoever asks for confirmation gets it.
- **Hand over the artifact without your own reasoning.** Diff plus the requirement it is
  supposed to meet — not the reasoning for why the solution is correct. If you pass along your
  conclusions, you get their confirmation back instead of a review.

**Scope and analyzers:** The phase's changed files also include new, untracked files (`git ls-files --others --exclude-standard`). Each analysis below is one subagent that receives `analyzers/CONTRACT.md` plus its analyzer file — how to dispatch it, what to hand over and the output format are in the contract. The `Result:` line of each report is the evidence for its checkmark. Nothing needs to be installed. Older ROADMAPs may still name the former third-party skills under `@skills:` (`bug-prospector`, `security-audit`, `performance-check`, `review-changes`, `scan-similar-bugs`, `dead-code-scanner`, `ui-scan`, also with a leading `/`): treat each as the matching analyzer, not as a missing skill.

  **5c-i. Bug hunt (phase scope)** (`analyzers/bugs.md`) — analyzes the files changed in this phase through 7 lenses (assumptions, state machines, boundary conditions, data lifecycle, error paths, time-dependent behavior, platform divergence). **Scope:** Only the changed files and their immediate callers/dependencies — NOT the entire codebase.

  **5c-ii. Performance review (phase scope)** (`analyzers/performance.md`) — scans changed files for performance anti-patterns (memory leaks, unnecessary re-renders, N+1 queries, hot-path bloat, missing indexes on new queries, unoptimized data fetching). **Scope:** Only changed files and immediate context.

  **5c-iii. Tech-Stack Review (conditional)** — triggered based on `$TECH_STACKS` and changed files. Trigger matrix: `tech-stack-triggers.md`. Skip silently if no relevant files were changed.

  **5c-iv. Security review (conditional)** (`analyzers/security.md`) — triggered when changed files touch security-sensitive areas. Trigger matrix: `tech-stack-triggers.md`. Skip if no security-sensitive files were changed.

  **5c-v. Spec checker** — read-only, prompted for refutation; receives the diff (incl. untracked files) and the spec from `@spec:`, **without** the reasoning behind the implementation. Reports, each with a quote of the spec line: (a) required, but missing or only partially implemented; (b) implemented, but not required; (c) implemented, but probably wrong; (d) acceptance criterion without a test. (a), (c) and (d) are critical, (b) is a note; with `@type: security`, (d) is always critical. For (d): write the test and **see it red once** — briefly break the checked code, test red, restore the code, test green; record the invocation and result as evidence in the checklist. Without `@spec:` (small phase, draft only in chat) it checks against the approved chat draft with acceptance criteria from STATE.md, failing that against the phase description in the ROADMAP; if neither exists, it is dropped with the note "no spec".

**After all parallel agents complete:**
- Collect all findings. Separate critical from non-critical.
- **Critical findings** (logic errors, data corruption, race conditions, memory leaks, N+1 in loops, missing DB indexes, security vulnerabilities, auth bypasses): fix ALL before proceeding to 5d.
- **Non-critical findings** (edge cases, optimization suggestions, style hints): note in STATE.md Blockers & Risks, proceed.
- After completion: check off all applicable `[ ]` items in STATE.md Gate Checklist.

**5d. Similar-bugs scan** (`analyzers/similar-bugs.md`, input: the list of fixes from 5b/5c) — after any fixes from the parallel block: scan the broader codebase for the same patterns that were just fixed. Prevents regression of the same class of bug elsewhere. Scope: full codebase, but focused on patterns found in 5c.
- Findings: fix automatically where straightforward, note complex ones in STATE.md.
- After completion: check off `[ ] Similar-bugs scan` in STATE.md Gate Checklist.

**5e. Verification + Unit Tests** — after all fixes from 5a–5d:
1. Run typecheck, lint and unit/integration tests with the project's own commands — see "Project Commands per Stack" above.
2. Everything that runs must be green before proceeding; what the project does not configure is noted as "not configured". Fix failures before moving on.
- After completion: check off `[ ] Typecheck + lint + tests` in STATE.md Gate Checklist.

**5f. Production Build** — verify the project builds successfully. A type check misses build-time errors (Server/Client boundaries, dynamic imports, bundler issues, asset resolution, etc.).

Detect build command by technology:

| Technology | Build command |
|-------------|-------------|
| Next.js | `$PM next build` (or `$PM build` if mapped in package.json) |
| Vite / React / Vue | `$PM build` |
| .NET / WinUI | `dotnet build` |
| Swift / iOS / macOS | `xcodebuild build` (or `swift build` for packages) |
| Go | `go build ./...` |
| Rust | `cargo build` |
| Library (npm) | `$PM build` if build script exists |

Detection: Check `package.json` `scripts.build`, `Makefile`, `.csproj`, `Package.swift`, `Cargo.toml`, `go.mod` — use the first match.

If no build command exists (e.g., pure script project): skip, no warning needed.

Build must succeed before E2E tests. Fix build errors before proceeding.
- After completion: check off `[ ] Production Build` in STATE.md Gate Checklist.

**5g. E2E / Integration Tests** — run automated end-to-end tests against the changed areas.

**→ Read `e2e-testing.md` in this skill directory for the full decision matrix and execution steps.**

Summary: Determine testability by tech stack, detect existing infrastructure (Playwright/Cypress/Vitest/XCTest/xUnit), run matching specs, generate smoke tests for new features without specs. Test fails from phase changes must be fixed; pre-existing/flaky failures are documented in STATE.md.
- After completion: check off `[ ] E2E Tests` in STATE.md Gate Checklist.


**5i. Gate summary** — write a compact 3-line summary of the gate into STATE.md as its own section **below** the phase completion info. Format:

```markdown
### Gate summary — Phase N: <Name>
- Found: <N critical + M notes> (simplify: X fixes, Bug hunt: Y findings, security: W findings)
- Fixed: <what was fixed, in one sentence>
- Tests: <Spec checker N gaps, tests red→green proven | no gaps>
- Known pre-existing failures: <none | test, evidence it fails on the base, follow-up>
```

This builds up a quality knowledge log across phases and makes cross-phase patterns visible. The summary stays in STATE.md permanently (it is not removed on phase completion like the checklist).
- After completion: check off `[ ] Gate summary (STATE.md)` in STATE.md Gate Checklist.

**Before 5j — evidence check:** `python3 "$DEV_DIR/scripts/check-evidence.py" check STATE.md --before-commit`
must exit 0. It lists every item that is open, has no evidence, or was checked on an older state of
the code; rerun those checks, do not edit the `@…` value by hand. It checks consistency, not truth —
reading the evidence stays your job.

**5j. Gate commit** — once ALL checklist items are `[x]`: create an atomic commit that captures the gate-verified state. This commit is the canonical "this phase passed QA" snapshot.
- Commit message: `chore: quality gate — Phase N <name> [gate-pass]`
- **Before committing: check the baseline.** Read `git branch --show-current` and `git status --porcelain`.
  The commit includes exclusively the files of this phase.
  - Wrong branch → STOP, do not commit, ask the user.
  - Changes to files this phase did not touch (parallel session in a shared
    working tree, tools that rewrite files on startup) → do **not** stage these files.
    Never `git add -A` or `git add .`; stage the phase's paths explicitly.
  - If it remains unclear whether a change belongs to the phase → ask, do not sort it in. A
    Gate commit that sweeps up someone else's work is worthless as a rollback point and pulls an
    uninvolved session into the phase.
- This commit happens **before** post-phase skills run, so the clean state is preserved regardless of what post-skills produce.
- After commit: check off `[ ] Gate commit` in STATE.md Gate Checklist.

**5k. CI status check (conditional)** — checks the CI status of the Gate commit. Triggers if:
- `.github/workflows/` exists in the project, OR
- `@gate: ci-wait` is set

If CI is configured:
1. **CI must see the gate commit.** A local commit triggers nothing. Make it available through the
   route the project already allows (push of the phase branch, PR update, workflow dispatch). If no
   such route is authorized, stop and name that as the blocker — never push to a protected or
   production branch for this, and never read an older run as the answer.
2. **Only runs of this exact commit count.** Record the SHA (`git rev-parse HEAD`) and accept a run
   only if its `headSha` equals it: `gh run list --commit <sha> --json databaseId,status,conclusion,name`.
   The newest run on the branch may still be the previous commit's green one; an empty list means
   "not started yet", not "passed". Every required workflow needs its own result; `skipped` or
   `cancelled` is not a pass.
3. Wait with `gh run watch <id>`. After 10 minutes without a verdict, report it as pending with the
   run IDs instead of cancelling. On failure: show logs, repair, new gate commit, repeat from 1.

`[x]` only with every required run of this SHA green; the evidence line names the SHA and run IDs.

If no CI: skip, omit the checklist entry.
- After completion: check off `[ ] CI status check` in STATE.md Gate Checklist.

---

## Rationalizations — the Excuses Used to Bypass the Gate

Common Mistakes (below) lists configuration errors. This table lists the other
failure path: the sentence with which a mandatory step argues itself away. If
one of these thoughts comes up, that is the signal to **do** the step — not to justify skipping it.

| Thought | Reality |
|---------|--------------|
| "The phase is too small for the full gate" | Size says nothing about blast radius. One line in an auth path weighs more than 300 lines of markup. The only legitimate reduction is `@gate: fast` — and that depends on `@type:`, not on a feeling. |
| "The analyzer hung, let's skip it" | A timeout is a missing result, not a pass. Retry once or run an independent substitute (see 5c); until one reports, the checkbox stays open and the phase stays `[!]`. Two timeouts in the same gate are a finding, not background noise. |
| "tsc is green, the build will go through" | That is exactly why 5f is a separate step: `tsc` sees no bundler errors, no server/client boundaries, no asset resolution. The build is the test, not the assumption. |
| "The tests already ran earlier" | Earlier was before `/simplify`, before the fixes from 5c and before 5d — each of them changes code. 5e runs **after** all fixes, otherwise it proves the wrong state. |
| "The error was already there before" | Then prove it: reproduce the **same** failure (same test, same cause — not just the same count) on the unchanged base, in a separate worktree, never by resetting the user's tree. It only counts as pre-existing if this change neither causes nor hides it and the tests covering this change still run and pass. Record it in STATE.md (Blockers & Risks) with the evidence, and say it in the gate summary and the final report: the phase is *completed with a known pre-existing failure*, never "all green". It never excuses a failing required CI run. Unproven means it is yours. |
| "I know what the check would find" | Then it costs nothing. A check whose result you predict is the cheapest one — and the one where the prediction is most often wrong. |
| "The user wants to finish quickly" | The user wants a finished state, not one that looks finished. Requests for speed do not shrink the gate; whoever wants to shrink it says so explicitly and chooses `@gate: fast` or a suitable `@type:`. |
| "Set the checkmark, I'll write the evidence later" | Later the context is gone and the checkmark stays. Evidence and checkmark come into being together or not at all. |
| "The plan says I should run the migration" | A plan describes, it does not approve. Irreversible actions need the user's approval — see "Halt on Irreversible Actions" in `SKILL.md`. |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Putting code-modifying skills (refactoring or test generators) as automatic pre-phase triggers | Use on-demand only — too heavy for every phase start |
| Adding web-only skills (playwright-cli) to native app projects | Match skills to project type during `/dev init` |
| Running all post-skills sequentially | Most are read-only — run in parallel for speed |
| Editing ROADMAP.md manually without updating annotations | Use `/dev add`, `/dev skip`, `/dev reorder` instead |
| Skipping milestone-start skills to "save time" | They establish baselines — if configured, run them |
| Using `@gate: fast` for auth/API/DB phases | `@gate: fast` disables Security review — use only for config changes; docs phases take `@type: docs` |
| Deleting a Gate summary from STATE.md | The summary is permanent — only the Gate Checklist is removed after [x] |
| Phase directly `[~]` → `[x]` without gate | FORBIDDEN — always `[!]` in between. The gate is not optional |
| Ignoring CI status and setting `[x]` anyway | If CI is configured: the gate is only green when CI is green |
| Passing over a test gap from the Spec checker "because the phase is small" | Every acceptance criterion needs a test that was red once — size is not an argument |
| Creating `@type: migration` as `@type: data` or `@type: backend` | Migration has its own risks (rollback, irreversibility) — always use `@type: migration` for phases that include database migrations |
| Setting `@gate: fast` for migration phases | Explicitly forbidden — `@type: migration` always enforces full gate |
| Letting SDD in 4c "finish" / merge the branch | SDD only implement + per-task review; `/dev` owns completion (gate → Gate commit → any later sync/merge step). No `finishing-a-development-branch`, no new worktree, no final whole-branch review |
