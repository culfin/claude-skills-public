---
name: deps
description: "Use when user says /deps, /deps setup, /deps check, /deps merge, /deps audit, /deps close, or /deps promote, or asks to use deps for one of these. Manages Dependabot dependency updates AND security alerts: analyzes impact, merges PRs to main with testing, fixes transitive vulnerabilities via overrides, closes superseded PRs, promotes to prod via PR."
---

# Dependency Update Management

Automates the Dependabot PR lifecycle: analyze, merge, test, promote.

## Language

**All user-facing communication in the user's language** (the language the user writes in or their instructions specify). Technical terms, commit prefixes, and file paths stay in English.

## Commands

| Command | Purpose | Reference |
|---------|---------|-----------|
| `/deps setup` | One-time project setup: detect ecosystem, install test framework, remove auto-merge workflows | `references/setup.md` |
| `/deps merge` | Analyze and merge all eligible Dependabot PRs on main, run tests, generate report | `references/merge.md` |
| `/deps promote` | Create PR to promote main → prod (also auto-triggered at end of `/deps merge`) | `references/promote.md` |
| `/deps check` | Analyze all open Dependabot PRs **and security alerts** without changing anything — impact analysis, code suggestions, report only | `references/merge.md` + `references/security-alerts.md` (read-only) |
| `/deps audit` | Scan Dependabot **security alerts**, fix transitive vulns via overrides, validate | `references/security-alerts.md` |
| `/deps close` | Close superseded and stale Dependabot PRs | `references/close.md` |
| `/deps merge --limit N` | Merge only the first N PRs (for incremental merging across sessions) | `references/merge.md` |
| `/deps` (no subcommand) | Show status: open Dependabot PRs, **open security alerts**, last merge report date, main↔prod diff | See "Status" below |

## Paths and host

`$DEPS_DIR` is the directory of this `SKILL.md` (wherever the host installed it). The helper scripts in
`$DEPS_DIR/scripts/` are read-only and need only `python3` and `gh`. On hosts other than Claude Code
(e.g. Codex) read `runtime.md` first.

## Routing

1. Parse user input for subcommand: `setup`, `merge`, `check`, `audit`, `close`, `promote`
2. If `check` → load `references/merge.md` (PRs) AND `references/security-alerts.md` (alerts, read-only). Execute ONLY: pre-flight checks, collect PRs, impact analysis per PR, scan + triage security alerts. Do NOT merge or edit overrides. Generate report as read-only analysis.
3. If `audit` → load `references/security-alerts.md`. Scan security alerts, fix transitive vulns via overrides, validate, commit. (This is the read-and-fix counterpart to `check`'s read-only alert scan.)
4. If `merge` with `--limit N` → pass limit to merge process (see merge.md "Batch size control")
5. If no subcommand → show status (see below)
5a. `check` or `merge` lifts a technology listed in `references/whats-new.md` across a **minor or major** version → after the impact analysis, follow that file: a subagent reads the release notes for the skipped range and reports what is new, what affects this project (with code locations) and what is deprecated. Report only; no network → `skipped: <reason>`.
6. Load the corresponding reference file, plus the pattern files for the ecosystems in play (see "Learned Patterns" below)
7. Follow its instructions step by step

## Status (default when no subcommand)

When user runs just `/deps`:

```bash
# Read branch config (defaults: main/prod; "prodBranch": null → empty = no promote)
DEV_BRANCH=$(python3 "$DEPS_DIR/scripts/branch_config.py" devBranch) || exit 1
PROD_BRANCH=$(python3 "$DEPS_DIR/scripts/branch_config.py" prodBranch) || exit 1   # empty = single-trunk repo, no promote

# Count open Dependabot PRs targeting the dev branch (all pages; fails loudly instead of undercounting)
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
python3 "$DEPS_DIR/scripts/collect_prs.py" --repo "$OWNER_REPO" --base "$DEV_BRANCH" | jq length

# Count open security alerts by severity (SEPARATE signal from PRs — transitive vulns have NO PR)
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh api repos/$OWNER_REPO/dependabot/alerts --paginate -X GET -f state=open 2>/dev/null \
  | jq -r 'group_by(.security_advisory.severity)[] | "\(.[0].security_advisory.severity|ascii_upcase): \(length)"'

# Check last report
ls -la .deps/last-report.md 2>/dev/null

# Check dev↔prod diff (both directions)
git fetch origin $PROD_BRANCH 2>/dev/null
MAIN_AHEAD=$(git rev-list --count origin/$PROD_BRANCH..origin/$DEV_BRANCH 2>/dev/null)
PROD_AHEAD=$(git rev-list --count origin/$DEV_BRANCH..origin/$PROD_BRANCH 2>/dev/null)
# Does prod hold content that main lacks? Merge prod into main *in memory* (nothing is written
# to the working tree or any branch) and compare the result with main's tree. Equal = main already
# contains everything; merge-only topology is fine. Unlike counting --no-merges commits, this also
# catches content introduced INSIDE a merge commit (a conflict resolution or hotfix on prod).
# Needs git >= 2.38. A conflict (non-zero exit) counts as "prod has own content".
MERGED=$(git merge-tree --write-tree origin/$DEV_BRANCH origin/$PROD_BRANCH 2>/dev/null | head -1) || MERGED=conflict
if [ "$MERGED" = "$(git rev-parse origin/$DEV_BRANCH^{tree})" ]; then PROD_OWN_CONTENT=0; else PROD_OWN_CONTENT=1; fi
```

Display:
```
Dependency Status:
  Open Dependabot PRs: N
  Security alerts:     N high / N moderate / N low   (or "none")
  Last merge report:   YYYY-MM-DD (or "none")
  main ahead of prod:  N commits
  prod ahead of main:  N commits   (merge-only, in sync | ⚠️ prod has content main lacks)
```
**If security alerts > 0:** note that alerts are distinct from update PRs (transitive vulns
have no PR) and point to `/deps audit` to fix them, or `/deps check` to analyze read-only.
Show the `⚠️` and the sync offer **only when `PROD_OWN_CONTENT == 1`**. When `PROD_AHEAD > 0`
but `PROD_OWN_CONTENT == 0`, render it as in-sync, e.g.:
`  prod ahead of main:  23 commits (merge-only — in sync, no drift)`

```
Available commands:
  /deps setup   — One-time project setup
  /deps merge   — Merge eligible PRs
  /deps audit   — Fix security alerts (transitive vulns via overrides)
  /deps promote — Promote to production
```

**If prod holds content main lacks (`PROD_OWN_CONTENT == 1`):** show what it is
(`git diff origin/$DEV_BRANCH "$MERGED"` — the content a merge would bring in; on conflict,
`git log --oneline origin/$DEV_BRANCH..origin/$PROD_BRANCH`), then offer to sync:
"⚠️ prod contains changes main doesn't have (a hotfix or a conflict resolution on prod). Should I merge prod into main?"
If yes → run the sync-back (see promote.md Step 5).

**If prod is ahead only by merge commits (`PROD_AHEAD > 0` but `PROD_OWN_CONTENT == 0`):** do NOT warn and do NOT offer a sync. This is the expected steady state for a merge-commit promote workflow without sync-back (main is the linear trunk; prod accumulates promote merge nodes). main already holds all the content, so there is no drift to fix.

## Safety Rules (NON-NEGOTIABLE)

These rules apply to ALL commands. Never skip or work around them.

1. **Never merge PRs with red or pending CI** — skip and report
2. **Never push directly to prod** — always create a PR
3. **Never rewrite git history** — always `git revert` (new commit), never `git reset --hard`
4. **Never merge while something else merges Dependabot PRs** — an *enabled* workflow that merges or auto-merges them, or GitHub auto-merge switched on for a PR. A disabled or unrelated workflow file is not a blocker (check in merge.md step 6); a real competitor → STOP, run setup first
5. **Always run local validation after every runtime merge** — typecheck + lint + unit tests; revert and stop on failure. Dev-deps: validate once after all.
6. **Always wait for CI before promote** — E2E/Playwright runs on GitHub CI, not locally; promote (auto or manual) requires green CI
7. **Always push reverts immediately** — dev branch must never stay broken
8. **Always persist the report** — `/deps promote` depends on it
9. **Merge via GitHub API** — `gh pr merge --squash --delete-branch`, not local git merge
10. **Detect test scripts from package.json** — never guess script names, read them
11. **Fix ALL warnings after merges** — lint, build, and test output must be warning-free before report
12. **Prod must never hold content main lacks** — decided by content, not by commit topology: merge prod into main in memory (`git merge-tree`, see Status) and compare with main's tree. Equal → in sync, even if prod is ahead by promote merge commits; do NOT sync-merge for topology alone. Different → a hotfix or a conflict resolution landed on prod; sync prod back into main (promote.md Step 5) and rerun checks. Counting `--no-merges` commits is not enough: content inside a merge commit is invisible to it.

## Branch Strategy

Default: `main` (development) → `prod` (production)

Override: check `.deps/config.json` for custom branch names. If file doesn't exist, use defaults.

## Ecosystem Detection

Read `references/ecosystems.md` for project type detection, package manager identification, lockfile commands, and test framework setup.

## Learned Patterns (from production use)

35 patterns discovered in real use. They are binding, but live in reference files so only the relevant ecosystem is loaded. **Before a step, read the file(s) for the ecosystems in play** — `package.json` → `patterns-js.md`, `Cargo.toml` → `patterns-cargo.md`; `patterns-workflow.md` and `patterns-ci.md` always apply. Numbers are stable; other files cite them as "pattern N".

| # | Pattern | File |
|---|---|---|
| 1 | Lockfile breaks 60% of sequential merges | js |
| 2 | Grouped PRs conflict after leader merge | js |
| 3 | Next.js type cache causes false failures | js |
| 4 | E2E often cannot run locally — check, don't assume | ci |
| 5 | Dev-deps rarely break — batch them, but still validate | workflow |
| 6 | Runtime deps need individual validation | workflow |
| 7 | `gh pr merge --squash` is silent on success | ci |
| 8 | Test script names vary | js |
| 9 | Impact analysis is the core value | workflow |
| 10 | Auto-promote after merge | workflow |
| 11 | Promote PR: always "Create a merge commit" | workflow |
| 12 | `$PM outdated` is ahead of the Dependabot queue — but NOT real-time | js + cargo |
| 13 | Major updates are NOT skipped | workflow |
| 14 | Sync back after a promote merge — in the same session | workflow |
| 15 | NEVER resolve promote PR conflicts on prod | workflow |
| 16 | Security alerts are a SEPARATE signal from update PRs | workflow |
| 17 | Severity label ≠ real exposure — re-rank by importer | workflow |
| 18 | pnpm overrides live in `pnpm-workspace.yaml`, not `package.json` | js |
| 19 | Caret-cap override replacement values; force a clean re-resolve | js |
| 20 | A transitive vuln is often fixed by a MINOR bump of its importer — check that BEFORE writing an override | js |
| 21 | Supersede instead of another rebase round | workflow |
| 22 | Lockfile-conflict asymmetry: cargo merges back-to-back, npm conflicts after the first | ci |
| 23 | Red CI ≠ broken update — diagnose before skipping OR reverting | ci |
| 24 | Wave 3, step 0: check toolchain peerDependencies BEFORE reading changelogs | js |
| 25 | `prodBranch: null` = single-trunk repo — and jq's `//` eats the null | workflow |
| 26 | `gh run list -L1` proves nothing without a headSha match | ci |
| 27 | An existing override can be the reason an alert won't close | js |
| 28 | Finish all PR merges before pushing your own commit | ci |
| 29 | A mass of identical type errors is usually collateral from ONE bad key in the library's config object | js |
| 30 | A changelog entry that matches your symptom is a hypothesis, not evidence — pin the version and run the real check | js |
| 31 | Dead config options only surface when a library tightens its types — and "fixing" them can switch behavior ON | js |
| 32 | `exit 137` is a memory ceiling, not load — and a rerun on an IDLE machine is the discriminator | ci |
| 33 | Intersect knip's unused-dependency list with the security alerts' importers — those alerts can be DELETED instead of pinned | js |
| 34 | Run `ncu` as the THIRD scanner — it is the only one that sees the `packageManager` pin | js |
| 35 | `pnpm add` SILENTLY WAIVES a `minimumReleaseAge` policy by writing its own exclude list — check `git status` on `pnpm-workspace.yaml` after every add | js |
