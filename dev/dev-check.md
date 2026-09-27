# `/dev check` — Standalone Quality Gate

This procedure is needed exclusively by `/dev check` and has nothing to do with the phase
lifecycle. It runs **the same** steps 5a–5k as the
phase gate, only with `$CHECK_SCOPE` in place of the phase-changed files — the step definitions
themselves are in `gate.md`.

## Procedure

**Triggered by:** `/dev check`

**Precondition:** No active phase.
- If ROADMAP.md exists and contains a phase with `[~]` or `[!]`: stop with "Phase N is still active (`[~]`/`[!]`). Use `/dev next` to complete the quality gate of the running phase."
- If ROADMAP.md exists and all phases are `[x]` or `[—]` (dormant): proceed normally.
- If no ROADMAP.md: proceed, but skip STATE.md integration. Check-Commit is still created.

**1. Snapshot scope** — before ANY skill runs, capture changed files:

```bash
git diff --name-only HEAD
git diff --name-only --cached
git ls-files --others --exclude-standard   # new, untracked files
```

Collect all three outputs, deduplicate, and store as `$CHECK_SCOPE`. This list is immutable for the entire run — later auto-fixes by `/simplify` do not change it.

If `$CHECK_SCOPE` is empty: AskUserQuestion — "No changes found since the last commit. Continue anyway?" (Yes / No).
- **Yes**: all scope-dependent steps run in full-codebase mode.
- **No**: stop, no action.

**2. Run full Quality Gate** — same steps 5a–5k as the phase gate, with `$CHECK_SCOPE` replacing "phase-changed files":

| Step | Tool | Notes |
|------|------|-------|
| 5a | `/simplify` | Scope: `$CHECK_SCOPE` |
| 5b | `/review-changes` | Scope: `$CHECK_SCOPE` |
| 5c-i | `/bug-prospector` | Scope: `$CHECK_SCOPE`; tool per stack (`tech-stack-triggers.md`) |
| 5c-ii | `/performance-check` | Scope: `$CHECK_SCOPE` |
| 5c-iii | Tech-Stack Review | Conditional — same trigger matrix as gate, evaluated against `$CHECK_SCOPE` |
| 5c-iv | `/security-audit` | Conditional — same trigger matrix as gate, evaluated against `$CHECK_SCOPE`; tool per stack |
| 5c-v | Spec checker | Only if the user names a spec; otherwise it is skipped with the note "no spec" |
| 5d | `/scan-similar-bugs` | After fixes from 5c |
| 5e | tsc + lint + unit tests | Full suite |
| 5f | Production Build | Full build |
| 5g | E2E Tests | Full suite |
| 5h | — | Dropped; test gaps are reported by 5c-v |
| 5i | Check summary | Written to STATE.md (see below); skipped if no ROADMAP.md |
| 5j | Check-Commit | `chore: dev check [gate-pass]` |
| 5k | CI-Status-Check | Conditional — if `.github/workflows/` exists or `@gate: ci-wait` set on any phase. When no ROADMAP.md: only `.github/workflows/` triggers this step. |

Steps 5c run as parallel Agent subagents (15-minute timeout). Any step failure stops the run — no Check-Commit is created.

**3. Check summary format** (STATE.md, inside `## Context`, same area as the `### Gate summary` entries):

```markdown
### Check summary — YYYY-MM-DD — N files
- Found: <N critical + M notices> (simplify: X fixes, bug-prospector: Y findings, security: W findings)
- Fixed: <what was fixed, in one sentence>
- Tests: <Spec checker N gaps, tests red→green verified | no gaps>
```

Heading uses `entire codebase` instead of `N files` when full-codebase mode was used. Same-day duplicates get ` #2`, ` #3` suffix. Check summaries are permanent — never removed.

**4. Post-check summary** — after step 5k, show a summary of what ran:

- **≥ 3 findings across all checks:** Start Visual Companion server automatically (no user prompt). Render a findings dashboard — findings grouped by category (critical / notice), tools that ran, what was fixed. Same structure as the existing Quality Gate Summary dashboard in the skill (building block "Gate dashboard"). Runs regardless of whether ROADMAP.md exists.
- **< 3 findings:** Terminal-only — do not echo STATE.md content again. Show two-line confirmation:

```
✓ All checks green — [N critical + M notices fixed]
Scope: N files | Commit: chore: dev check [gate-pass]
```

(`N files` becomes `entire codebase` when full-codebase mode was active.)

**5. Post-check action** — AskUserQuestion after the summary:

| ROADMAP.md status | Options |
|-------------------|---------|
| No ROADMAP.md | "Done" |
| Completed (all `[x]`/`[—]`) | "Done" + "Start pre-release review" |
| Active (at least one `[ ]` phase) | "Done" + "Start next phase" |

- **Done** — no further action
- **Start next phase** — triggers the same flow as `/dev next`
- **Start pre-release review** — triggers `/dev review`
