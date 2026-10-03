# `/dev check` — Standalone Quality Gate

This procedure is needed exclusively by `/dev check` and has nothing to do with the phase
lifecycle. It runs **the same** gate steps (A–D, tier, evidence, commit, CI) as the phase gate, only
with `$CHECK_SCOPE` in place of the phase-changed files — the step definitions themselves are in `gate.md`.

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

Collect all three outputs, deduplicate, and store as `$CHECK_SCOPE`. This list is immutable for the entire run — later fixes do not change it.

If `$CHECK_SCOPE` is empty: AskUserQuestion — "No changes found since the last commit. Continue anyway?" (Yes / No).
- **Yes**: all scope-dependent steps run in full-codebase mode.
- **No**: stop, no action.

**2. Run the Quality Gate** — the steps of `gate.md` with `$CHECK_SCOPE` replacing "phase-changed files":

| Step | What | Notes |
|------|------|-------|
| Tier | `gate-tier.py --base HEAD` | Decides small/large for `$CHECK_SCOPE` (uncommitted and untracked changes); full-codebase mode is always large |
| A | Diff review | `analyzers/diff-review.md`, scope `$CHECK_SCOPE` |
| A | Spec checker | Only if the user names a spec; otherwise skipped with the note "no spec" |
| A | Security, Tech-Stack, Performance, design reviews | Large tier only — same trigger matrix as the gate, evaluated against `$CHECK_SCOPE` |
| B | Fix + Fix review | Bundled fix of all critical findings, Fix review on the fix diff |
| C | Similar-bugs scan | Only if Step B changed code |
| D | Typecheck + lint + tests, Production Build, E2E Tests | Full suite; tests and build in parallel |
| — | Check summary | Written to STATE.md (see below); skipped if no ROADMAP.md |
| — | Evidence check | `check-evidence.py` needs a gate checklist; `/dev check` has none. Instead, every result line in the check summary carries its `@state` (from `check-evidence.py id`), and all must be current before the check commit (review results may keep the wave's state when a current Fix review covers the change since) |
| — | Check-Commit | `chore: dev check [gate-pass]` |
| — | CI | If `.github/workflows/` exists — `ci-watch.sh` on the check commit as in `gate.md`, "CI in background". `/dev check` has no next phase to go on with, so it waits for the final status and reports it in the post-check summary; `red` or `timeout` → repair as in the gate; `none` is reported, not green |

Step A runs as one parallel wave of Agent subagents (15-minute timeout). Any step failure stops the run — no Check-Commit is created.

**3. Check summary format** (STATE.md, inside `## Context`, same area as the `### Gate summary` entries):

```markdown
### Check summary — YYYY-MM-DD — N files
- Tier: small|large — <first reason>
- Found: <N critical + M notices> (Diff review: X, Spec checker: Y, security: W)
- Fixed: <what was fixed, in one sentence>
- Tests: <Spec checker N gaps, tests red→green verified | no gaps>
- Skipped checks: <none | check — reason>
```

Heading uses `entire codebase` instead of `N files` when full-codebase mode was used. Same-day duplicates get ` #2`, ` #3` suffix. Check summaries are permanent — never removed.

**4. Post-check summary** — after the check commit, show a summary of what ran:

- **≥ 3 findings across all checks:** a findings table in the terminal — grouped by category (critical / notice), tools that ran, what was fixed. No companion screen: findings are not user interface (`companion.md`, ground rule). Runs regardless of whether ROADMAP.md exists.
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
