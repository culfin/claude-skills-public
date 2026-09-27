---
name: deps
description: "Use when user says /deps, /deps setup, /deps check, /deps merge, /deps audit, /deps close, or /deps promote. Manages Dependabot dependency updates AND security alerts: analyzes impact, merges PRs to main with testing, fixes transitive vulnerabilities via overrides, closes superseded PRs, promotes to prod via PR."
---

# Dependency Update Management

Automates the Dependabot PR lifecycle: analyze, merge, test, promote.

## Language

**All user-facing communication in German (Deutsch).** Technical terms, commit prefixes, and file paths stay in English.

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

## Routing

1. Parse user input for subcommand: `setup`, `merge`, `check`, `audit`, `close`, `promote`
2. If `check` → load `references/merge.md` (PRs) AND `references/security-alerts.md` (alerts, read-only). Execute ONLY: pre-flight checks, collect PRs, impact analysis per PR, scan + triage security alerts. Do NOT merge or edit overrides. Generate report as read-only analysis.
3. If `audit` → load `references/security-alerts.md`. Scan security alerts, fix transitive vulns via overrides, validate, commit. (This is the read-and-fix counterpart to `check`'s read-only alert scan.)
4. If `merge` with `--limit N` → pass limit to merge process (see merge.md "Batch size control")
5. If no subcommand → show status (see below)
6. Load the corresponding reference file
7. Follow its instructions step by step

## Status (default when no subcommand)

When user runs just `/deps`:

```bash
# Read branch config (defaults: main/prod)
DEV_BRANCH=$(cat .deps/config.json 2>/dev/null | jq -r '.devBranch // "main"')
PROD_BRANCH=$(cat .deps/config.json 2>/dev/null | jq -r '.prodBranch // "prod"')

# Count open Dependabot PRs
gh pr list --author "app/dependabot" --state open --json number | jq length

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
# Only NON-MERGE commits count as real divergence. A merge-commit-only promote
# workflow (e.g. PR main→prod with --merge, no sync-back) leaves prod "ahead" by
# merge nodes while main holds all the actual content — that is NOT drift.
PROD_AHEAD_REAL=$(git rev-list --count --no-merges origin/$DEV_BRANCH..origin/$PROD_BRANCH 2>/dev/null)
```

Display:
```
Dependency Status:
  Open Dependabot PRs: N
  Security alerts:     N high / N moderate / N low   (or "none")
  Last merge report:   YYYY-MM-DD (or "none")
  main ahead of prod:  N commits
  prod ahead of main:  N commits   (M real / rest merge-only)   ⚠️ only if M > 0
```
**If security alerts > 0:** note that alerts are distinct from update PRs (transitive vulns
have no PR) and point to `/deps audit` to fix them, or `/deps check` to analyze read-only.
Show the `⚠️` and the sync offer **only when `PROD_AHEAD_REAL > 0`**. When `PROD_AHEAD > 0`
but `PROD_AHEAD_REAL == 0`, render it as in-sync, e.g.:
`  prod ahead of main:  23 commits (merge-only — in sync, no drift)`

```
Available commands:
  /deps setup   — One-time project setup
  /deps merge   — Merge eligible PRs
  /deps audit   — Fix security alerts (transitive vulns via overrides)
  /deps promote — Promote to production
```

**If prod is ahead of main with REAL commits (`PROD_AHEAD_REAL > 0`):** Display warning and offer to sync immediately:
"⚠️ prod ist {PROD_AHEAD_REAL} echte(r) Commit(s) ahead von main (kein Promote-Merge-Knoten). Soll ich prod in main mergen um die Branches zu synchronisieren?"
If yes → run the sync-back (see promote.md Step 5).

**If prod is ahead only by merge commits (`PROD_AHEAD > 0` but `PROD_AHEAD_REAL == 0`):** do NOT warn and do NOT offer a sync. This is the expected steady state for a merge-commit promote workflow without sync-back (main is the linear trunk; prod accumulates promote merge nodes). main already holds all the content, so there is no drift to fix.

## Safety Rules (NON-NEGOTIABLE)

These rules apply to ALL commands. Never skip or work around them.

1. **Never merge PRs with red or pending CI** — skip and report
2. **Never push directly to prod** — always create a PR
3. **Never rewrite git history** — always `git revert` (new commit), never `git reset --hard`
4. **Never merge if auto-merge workflow exists on remote** — hard STOP, run setup first
5. **Always run local validation after every runtime merge** — typecheck + lint + unit tests; revert and stop on failure. Dev-deps: validate once after all.
6. **Always wait for CI before promote** — E2E/Playwright runs on GitHub CI, not locally; promote (auto or manual) requires green CI
7. **Always push reverts immediately** — dev branch must never stay broken
8. **Always persist the report** — `/deps promote` depends on it
9. **Merge via GitHub API** — `gh pr merge --squash --delete-branch`, not local git merge
10. **Detect test scripts from package.json** — never guess script names, read them
11. **Fix ALL warnings after merges** — lint, build, and test output must be warning-free before report
12. **Prod must never be ahead of main with REAL commits** — measure divergence with `--no-merges` (`git rev-list --count --no-merges $DEV_BRANCH..$PROD_BRANCH`). A non-zero count means a hotfix or change landed on prod that main lacks → sync prod back into main (see promote.md Step 5). **Merge-commit-only "ahead" is NOT drift** and must not trigger a sync: a promote workflow that merges `main→prod` with `--merge` and no sync-back (e.g. a project's own `/vision-prod`) leaves prod ahead by promote merge nodes forever, while main holds all content as the linear trunk. Check for *real* divergence in `/deps` status and `/deps promote` pre-flight; ignore merge-only ahead.

## Branch Strategy

Default: `main` (development) → `prod` (production)

Override: check `.deps/config.json` for custom branch names. If file doesn't exist, use defaults.

## Ecosystem Detection

Read `references/ecosystems.md` for project type detection, package manager identification, lockfile commands, and test framework setup.

## Learned Patterns (from production use)

These patterns were discovered through real-world testing and MUST be followed:

1. **Lockfile breaks 60% of sequential merges** — Never fix per PR. One `$PM install` + one commit after ALL merges. See merge.md "Fix lockfile" section.
2. **Grouped PRs conflict after leader merge** — After merging `next`, PRs like `eslint-config-next` become CONFLICTING. Skip them — Dependabot auto-rebases. Pick up in next `/deps merge` session.
3. **Next.js type cache causes false failures** — Always `rm -rf .next/dev/types` before `typecheck` after framework updates.
4. **Playwright never runs locally** — Requires DB + specific ports. E2E validation happens via CI after push, not locally.
5. **Dev-deps have 100% pass rate** — Across 8+ merges, zero dev-dependency updates broke anything. Batch them (Wave 1) and validate once at the end.
6. **Runtime deps need individual validation** — Merge one at a time with `typecheck + lint + test` after each. This catches the exact culprit on failure.
7. **`gh pr merge --squash` is silent on success** — Don't expect output. Check with `git pull` after to confirm the merge landed.
8. **Test script names vary** — Always read from `package.json`, never assume `test:run` or similar. Common: `test` → `vitest run`.
9. **Impact analysis is the core value** — NEVER skip it. The user MUST see changelog summaries, code suggestions, and breaking changes for every PR before it's merged. This is what makes /deps better than manual Dependabot merging.
10. **Auto-promote after merge** — After all merges + CI green + code suggestions handled, automatically create the promote PR. Don't wait for a separate `/deps promote` command. The only manual step is the PR merge on GitHub.
11. **Promote PR: always "Create a merge commit"** — NEVER use "Rebase and merge" for promote PRs. Rebase creates new commit SHAs on prod, causing main and prod to diverge. Merge commit keeps branches in sync.
12. **`$PM outdated` is ahead of the Dependabot queue — but NOT real-time** — Versions published between Dependabot runs surface in `$PM outdated` before a PR exists, and cross-major updates never enter the queue at all (outside the semver range). (Dependabot's default `versioning-strategy` *does* raise a stale 0.x caret, e.g. `^0.100.1` → `^0.104.1`, so a lagging 0.x dep is batch lag, not a config gap.) Always run the **full two-command scan below** during `/deps check` and `/deps merge`. During `/deps merge`, ACT on every miss — not just report: **majors** → Wave 3 (deep analysis); **minor/patch** → fold into Wave 1 (dev) or Wave 2 (runtime) and merge by editing `package.json` directly (no PR branch exists), validated in the same wave pass. (`/deps check` stays read-only — report only.)

    **⚠ Neither scanner alone is complete — run BOTH, every time, and take the UNION.** This is not a "cross-check if suspicious"; it is the scan. Each tool misses things the other sees:
    - **`pnpm outdated` omits packages ENTIRELY** — not just showing a stale version, but leaving the row out altogether. Observed twice: `next@16.3.0` (published ~19h earlier) absent while `pnpm view next version` returned it; and `stripe 22.4.0→22.5.0` + `typescript-eslint 8.66.0→8.67.0` absent from a run where `npm outdated` listed both. Cause is the metadata cache (`~/Library/Caches/pnpm/metadata-v1.3/…` on macOS, `~/.cache/pnpm/…` on Linux) — a package can be days behind with no warning. It also under-reports patch levels (`@aws-sdk/client-s3` `3.1106.0` vs npm's `3.1107.0`).
    - **`npm outdated`'s `Latest` can be BELOW the installed version** — it reads the `latest` dist-tag, which lags when a package ships a newer line under another tag. Observed: `jsdom` installed `30.0.1`, `Latest 29.1.1`. Never treat that as a downgrade to apply — drop the row.

    ```bash
    $PM outdated 2>&1              # may silently omit rows; may under-report patch level
    npm outdated 2>&1 | head -40   # registry-direct; may show Latest < installed
    ```
    **Merge rule:** a package is outdated if EITHER tool says so; per package take the HIGHER `Latest`, and discard any `Latest` ≤ installed. Only `Current` vs `Latest` matter — npm's `Wanted` column is meaningless in a pnpm workspace (it reports per-importer copies).

    **⚠ The stale cache also breaks the FIX, not just the scan: `pnpm update <pkg>` skips such a package SILENTLY.** No error, no mention in its output — the package simply does not appear among the updated ones and its version is unchanged. Observed in the same run: `pnpm update stripe @aws-sdk/client-s3 …` listed 8 of 10 packages and left those two at their old versions. **Always verify after updating**, and reach for the explicit form when a package is missing:
    ```bash
    pnpm update <pkgs…>                       # may silently skip cache-stale packages
    npm view <pkg> version                    # or check node_modules/<pkg>/package.json
    pnpm add <pkg>@<version>                  # explicit version DOES resolve — the reliable fallback
    ```
    Never conclude "it's already current" from `pnpm update`'s output alone.

    **Measured again 16.09.2026, and worse than described above: the skip also hits plain IN-RANGE minors.** One `pnpm update` in a repo with `^`-ranges reached 20 packages and silently left five behind — `typescript-eslint 8.69.0 → 8.70.0`, `vitest 5.0.0 → 5.0.1`, `eslint-plugin-sonarjs 4.2.0 → 4.2.1`, and `@aws-sdk/client-s3` stopping at `3.1132.0` while `3.1133.0` existed. All were inside their declared caret; nothing in the output mentioned them. `pnpm add <pkg>@<exact>` resolved every one instantly. **So: diff the list of packages you intended against the list `pnpm update` printed, every time.**

    **0.x carets cannot be crossed by `pnpm update` at all** — `^0.124.0` means `>=0.124.0 <0.125.0`, so `@anthropic-ai/sdk 0.126.0` is unreachable no matter how often you run it, and the package looks "already current" in that output. Dependabot's `versioning-strategy` DOES raise such a range (its PR carried 0.125.0), so a 0.x dep that no PR covers needs an explicit `pnpm add <pkg>@<version>`, not an update.

    **⚠ Also re-check the OPEN PRs against `Latest` — a fresh PR is routinely already stale.** Observed: a group PR opened that morning carried `lucide-react 1.30.0`, `tsx 4.23.11`, `@aws-sdk/client-s3 3.1106.0` while latest were `1.31.0`, `4.23.12`, `3.1107.0`. Merging it is still right; just fold the remainder into the same wave rather than reporting the PR as "covers that package".

    **⚠ Do NOT explain an uncovered package as "batch lag" without measuring it.** Read the actual `schedule.interval` from `.github/dependabot.yml` (it may be `daily`, not `weekly`) and compare each missing version's publish time against the PR's `createdAt`:
    ```bash
    gh pr view <PR> --json createdAt -q .createdAt
    npm view <pkg> time --json | jq -r '.["<version>"]'
    ```
    Observed: `interval: daily`, and all 10 uncovered versions were published BEFORE the group PR was created (up to 2.5 days earlier) — so batch lag was ruled out and the real cause stayed unknown. Report it as "not covered by any open PR, cause unverified", never as a confident batch-lag story. The practical consequence is the same either way: PR coverage is not trustworthy, the two-command scan is what closes the gap.

    **⚠ Rust / hybrid projects (Tauri, Electron+Rust): `$PM outdated` covers only the npm half.** The cargo side needs its own scan — `cargo outdated --root-deps-only` (install once: `brew install cargo-outdated` or `cargo install cargo-outdated`; `cargo update --dry-run` is NOT a substitute, it only shows in-range updates). Observed in a Tauri workspace: `zip 4.6.1` vs `Latest 8.6.0` — a four-major gap Dependabot will never PR — plus ~10 minor/patch crates in batch lag and an open cargo PR that was already stale (bumped to 2.0.19 while `Latest` was 2.0.20). None of this is visible from the npm scan or the PR queue. See ecosystems.md for hybrid-project and workspace rules.

13. **Major updates are NOT skipped** — Wave 3 handles all major version bumps. Deep changelog analysis, usage scan, risk assessment (low/medium/high), and automatic migration for medium-risk updates. Only truly high-risk updates (unclear migration, infrastructure mismatch) are skipped with detailed explanation. See merge.md "Wave 3: Major Updates".
14. **Always sync after promote merge** — After the promote PR is merged on GitHub, prod has a merge commit that main doesn't. Always merge prod back into main to prevent divergence. This is automated in promote.md Step 5.
15. **NEVER resolve promote PR conflicts on prod** — If a promote PR has conflicts, close the PR, merge prod into main (resolve conflicts there), then recreate the PR. Pushing directly to prod violates Safety Rule #2 and causes divergence. See promote.md "Handle PR conflicts".
16. **Security alerts are a SEPARATE signal from update PRs** — `gh pr list --author app/dependabot` can be empty while `gh api .../dependabot/alerts` has dozens of open vulns. Transitive packages (in the lockfile, not `package.json`) get an alert but NO version-bump PR — so a PR-only skill silently misses them. Always scan `dependabot/alerts` in status, `check`, and `audit`. (Observed: 0 PRs, 24 alerts.) See `references/security-alerts.md`.
17. **Severity label ≠ real exposure — re-rank by importer** — GitHub rates the CVE in isolation; `pnpm why <pkg>` reveals who pulls it. A "high" in a test-only chain (undici→jsdom→vitest) or a Windows-only advisory on a Linux deploy is near-zero practical risk; a "moderate" on a prod runtime path (dompurify→jspdf in a server PDF generator) is the one that matters. Report the importer-reranked view, not GitHub's raw counts.
18. **pnpm overrides live in `pnpm-workspace.yaml`, not `package.json`** — pnpm v9+ reads `overrides` from `pnpm-workspace.yaml`; a `pnpm.overrides` block in `package.json` is silently ignored (may be dead config — leave it). Editing the wrong file = the version never moves. The lockfile's own `overrides:` block is the truth of what's applied. (npm: `overrides` in package.json; yarn: `resolutions`.)
19. **Caret-cap override replacement values; force a clean re-resolve** — An override value of `">=X"` grabs the highest match and can jump a MAJOR (real: `undici@<7.28.0: ">=7.28.0"` pulled undici 8.5.0, breaking jsdom's `undici@^7.25.0`). Always cap: `"^X.Y.Z"`. And pnpm won't re-resolve an already-locked transitive on a plain `pnpm install` (reports "Already up to date" in ~100ms) — `rm pnpm-lock.yaml && rm -rf node_modules/.pnpm/<pkg>@* && pnpm install` to force a real resolver run, then verify with `pnpm why`.
20. **A transitive vuln is often fixed by a MINOR bump of its importer — check that BEFORE writing an override** — Before overriding a transitive advisory, check whether a newer version of the package that pulls it already widened its range. Real case: `sharp@0.34.5` (HIGH) came via `next@16.2.12`, which pins `sharp@^0.34.5`; `next@16.3.0` pins `^0.35.3` and closes the alert with a plain minor bump — no override, no range violation, no request-time risk. **No `outdated` run reveals this** — you must query the importer's own dependency range:
    ```bash
    npm view <importer>@<current> optionalDependencies.<pkg> dependencies.<pkg>
    npm view <importer>@latest    optionalDependencies.<pkg> dependencies.<pkg>
    ```
    Do this for every alert whose importer is a package you could simply update. An override is the fallback for when upstream has not moved — not the first move. (It is also the only honest way to close an alert where overriding would violate the importer's declared range, e.g. forcing `sharp@^0.35` under a `next` that declares `^0.34.5`.)

21. **Supersede instead of another rebase round** — When remaining PRs keep flipping to CONFLICTING after each merge AND the beyond-Dependabot pass (`$PM update`/`cargo update`) reaches the SAME dep at an equal-or-newer in-range version, skip further rebase+CI rounds: run the beyond-pass, validate, push, then close those PRs with a comment naming the superseding commit ("Superseded: vite 8.2.1 via <sha>"). Condition to check first: PR target version ≤ what the update command reaches in-range. Observed: 2 PRs × ~8 min rebase+CI saved, and the result was NEWER than the stale PRs (vite 8.2.1 > 8.2.0, thiserror 2.0.20 > 2.0.19). pnpm v10 `pnpm update` also bumps the package.json ranges, so manifest + lockfile both end up current — the close-as-superseded is honest. This beats Pattern 2's "wait for next session" whenever the beyond-pass covers the dep anyway.

22. **Lockfile-conflict asymmetry: cargo merges back-to-back, npm conflicts after the first** — `Cargo.lock` hunks of unrelated crates rarely overlap: four sequential cargo PR merges went through with zero conflicts. npm lockfiles are the opposite: every `pnpm-lock.yaml` PR merge flipped ALL remaining npm PRs to CONFLICTING (shared dependency subtrees). Merge order that exploits this: process cargo PRs optimistically in direct sequence; for npm expect only the first merge to be clean and plan rebase (or supersede, Pattern 21) for the rest. And when a lockfile conflict hits your working tree: resolve by REGENERATION (`$PM install` / `cargo update`), never by hand-merging hunks. (Stash gotcha: during `git stash pop`, `--theirs` = the stash side, not the remote.)

    **github-actions-ecosystem PRs are the easiest tier of all:** they touch only `.github/workflows/*` (no lockfile, hunks per action-SHA) — merge them back-to-back like cargo, and skip local validation entirely: there is nothing to build or test locally; the PR's own CI run IS the validation. One caveat: after such a merge, re-check comments next to pinned action SHAs — Dependabot updates the SHA but can leave a trailing custom comment stale (observed: `# v6.0.9 — …` beside the new 6.0.10 SHA when extra text follows the version).

23. **Red CI ≠ broken update — diagnose before skipping OR reverting** — Applies to the post-merge `$DEV_BRANCH` run just as much as to PR checks: a failing **registry-login / image-pull / container-start** step means no test ever ran, so reverting a merge is the wrong move (observed: `docker login ghcr.io` → `denied: denied` on 3 of 7 shards after several deploys in quick succession — a secondary rate limit; `gh run rerun --failed` went green with zero code changes; see merge.md "Wait for CI"). When MANY PRs are red at once, check ONE failed run before writing them all off: same failing step, failure within seconds (no test ever ran), all from the same day = a transient CI-infra outage (observed: an apt step "Tauri-System-Deps (Linux)" failing after ~14s across 7 PRs on one evening), NOT seven broken updates. Remedy: comment `@dependabot rebase` on each → fresh CI runs → merge on green. Safety Rule 1 still holds — never merge on red — but "skip and report" is only the verdict for a *genuine* test failure. Check the step via `gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs --jq '.jobs[].steps[] | select(.conclusion=="failure") | .name'`.

    **⚠ After a rebase push, the old checks VANISH.** `statusCheckRollup` is empty until the new workflow registers (can take minutes after Dependabot pushes). An empty rollup means "not started", NOT "complete" — a wait-loop whose done-condition is "no PENDING entries" exits prematurely on the gap. Treat empty/missing conclusions as still-running; require an explicit SUCCESS/FAILURE per PR.

24. **Wave 3, step 0: check toolchain peerDependencies BEFORE reading changelogs** — For a major bump, first ask whether the ecosystem's tooling even accepts the new major: `npm view <toolchain-pkg> peerDependencies` for every tool that compiles/checks against the package (e.g. svelte-check, @sveltejs/kit, eslint plugins, ts-loader for typescript). An unfulfilled peer range = instant HIGH RISK skip — no changelog analysis needed, and the report gets a precise re-check trigger ("revisit when X peers ^N"). Real case: typescript 6→7 (the native Go port) — svelte-check@4.7.5 and @sveltejs/kit@2.70.2 both peer `typescript ^5 || ^6`; 30 seconds of `npm view` settled what changelog reading could not.

    **⚠ A green top-level peer proves nothing — walk the TRANSITIVE plugin chain, then dry-run.** An umbrella config can declare a permissive peer while the plugins it pulls cannot handle the new major at all. Real case: `eslint-config-next@16.3.0` peers `eslint >=9`, which formally admits 10 — but it pulls eslint-plugin-react / jsx-a11y / import, whose **newest published versions** still peer `^9` at most, so there is no override target and no migration path. Installing eslint 10 aborted the very first lint run with `TypeError: ... contextOrFilename.getFilename is not a function` (plugin calling a rule-context method v10 removed). Procedure: resolve the umbrella's plugin dependencies (`pnpm why <plugin>`), `npm view <plugin> peerDependencies.<pkg>` for each, and check whether a compatible version even EXISTS — then confirm with a throwaway install plus one real tool run (`pnpm add -D <pkg>@<new>` → `pnpm lint` → `git checkout package.json <lockfile> && $PM install`). Two minutes of dry run beats an hour of changelog reading, and rolls back cleanly.

25. **`prodBranch: null` = single-trunk repo — and jq's `//` eats the null** — Projects whose dev branch is the ONLY branch set `"prodBranch": null` in `.deps/config.json`. Then: skip promote entirely (no promote PR, no main↔prod diff in status; the merge report is the final artifact). ⚠ `jq -r '.prodBranch // "prod"'` maps an explicit `null` to `"prod"` — the alternative operator treats null as absent — so auto-promote would open a PR against a branch that doesn't exist. Guard first: `jq -e '.prodBranch != null'` before any promote step.

26. **`gh run list -L1` proves nothing without a headSha match** — Right after a push the newest run may not be registered yet, so `-L1` returns the PREVIOUS commit's green run — "CI green" for code it never tested. (Observed the same shape on a cross-repo dispatch: the dispatch itself failed, yet `-L1` in the target repo showed the prior run's success.) Always assert the run's `headSha` == your pushed SHA before trusting a verdict; for cross-repo dispatches, record `MARK=$(date -u +%FT%TZ)` before dispatching and only trust runs with `createdAt > $MARK`. Complements pattern 23 (empty rollup ≠ complete): both are "absence of the NEW signal masquerading as the OLD signal's success".

27. **An existing override can be the reason an alert won't close** — When an advisory's `vulnerable_version_range` extends up to and INCLUDING the floor you once pinned, the override holds the package on the vulnerable version and the alert can never resolve. It reads as "the override isn't working". Observed: `dompurify@<3.4.12: "^3.4.12"` vs a new range of `<= 3.4.12` (patched in 3.4.13). For every alert on an already-overridden package, diff the alert range against the pinned floor and raise **selector and value together** — bumping only the value leaves a `<oldfloor` selector that stops matching, and the package silently stays put. Invisible to `$PM outdated`: a transitive sitting exactly at its override floor is not "outdated". See `references/security-alerts.md` §1.

28. **Finish all PR merges before pushing your own commit** — Each squash-merge is a commit on `$DEV_BRANCH` and triggers its own deploy, so PR merges can't be batched; what you control is placement. Interleaving (group PR → local beyond-Dependabot push → one more PR) produced three deploy waves in ten minutes, each cancelling its predecessor and stacking registry logins until a rate limit painted two deploys red for no reason. Do all PR merges first, push the lockfile/beyond commit LAST. A cancelled intermediate deploy is expected, not a failure. See merge.md "Push order".

29. **A mass of identical type errors is usually collateral from ONE bad key in the library's config object** — Bump a library, get 40 errors of the same shape in 40 files that barely touch it, plus two lonely errors inside its config literal: the two are the cause, the 40 are the symptom. Real case: `better-auth 1.7.3 → 1.7.5` produced ~40 `Property 'accountId' does not exist on type '{ id; createdAt; … }'` across every session-reading page, plus `TS2561` (excess property `sendChangeEmailVerification`) and `TS2353` (unknown key `joins`) in `src/lib/auth.ts`. Once an options literal passed to a generic has a shape error, inference of the whole object falls back to the constraint, and everything derived from it — here `auth.$Infer.Session`, hence `additionalFields` — collapses to the base type. Fixing the two cleared all forty. **Procedure: before bisecting packages or reading changelogs, scan the error list for `TS2353`/`TS2561`/`TS2559` INSIDE the library's own config object and fix those first**, then re-run. Sorting by error code beats sorting by file count — the loud errors are never the interesting ones.

30. **A changelog entry that matches your symptom is a hypothesis, not evidence — pin the version and run the real check** — Real case: the fix list for `better-auth 1.7.5` read *"Fixed database option type inference outside Cloudflare Workers"*, which described the observed symptom precisely. It was the wrong explanation: 1.7.5 failed identically to 1.7.4. The decisive test is one install plus one real tool run (`pnpm add <pkg>@<new> && pnpm typecheck`), about four minutes, and it also produces the true error list. Do it BEFORE naming a cause in a report. Corollary that would have caught it sooner: if the old and new `.d.ts` both contain the symbol you believe changed (`grep` both store copies under `node_modules/.pnpm/<pkg>@<ver>*`), then the type did not change — the strictness of inference around it did, and the culprit is your own config, not the package's API.

31. **Dead config options only surface when a library tightens its types — and "fixing" them can switch behavior ON** — Options that a library never reads compile happily for years, because a generic type parameter absorbs excess properties; the moment the library gives that key a concrete shape, they turn into errors. Real case: `experimental: { joins: true }` (the real option is `advanced.database.joins`) and `sendChangeEmailVerification` (the real callback is `sendChangeEmailConfirmation`) had been inert at every version. **Prove deadness from the installed package, not the changelog:** `grep -rl "<optionName>" node_modules/<pkg>/dist` — zero hits in BOTH the old and new version means the runtime never read it. Then the choice is not cosmetic: **deleting is behavior-preserving; renaming to the real key activates a code path that has never run once.** Pick deliberately, say which you picked in the commit message, and flag it to the user — a behavior change riding inside a dependency commit is exactly the kind of thing nobody looks for later.

32. **`exit 137` is a memory ceiling, not load — and a rerun on an IDLE machine is the discriminator** — Extends pattern 23. `ELIFECYCLE Command failed with exit code 137` is SIGKILL, i.e. the container hit its memory limit (e.g. a 6 GiB cap per self-hosted runner instance). Load makes it *more likely*, so a first failure is ambiguous; a rerun on a verified-idle machine that fails again rules load out. Observed: a workflow-file-only PR OOM'd in its `Build` step at load 62 AND again at load 0.13. **What the second failure does NOT prove is that the code is broken** — check whether the same workflow is green on the CURRENT base branch content (`gh run list -w "<workflow>" -b <base>`). If it is, the PR is simply sitting on a stale merge-base: `@dependabot rebase`, don't rerun. Reruns replay the old merge commit forever.

33. **Intersect knip's unused-dependency list with the security alerts' importers — those alerts can be DELETED instead of pinned** — Belongs next to pattern 20 (bump the importer) as the cheaper move before writing an override. Real case: 3 of 4 open alerts were `hono`, whose only importer chain was `shadcn → @modelcontextprotocol/sdk → @hono/node-server`; `shadcn` is a devDependency knip reports as unused, because the CLI is normally invoked via `pnpm dlx`. Dropping the dep closes all three at the root; an override only freezes them at a patched floor forever. Run `pnpm exec knip --dependencies` (or `npx knip`) during `check`/`audit` and cross-reference. **Caveat, and knip tells you itself:** its "Configuration hints" name where it is blind — it does not follow `.css`, so packages used only from a stylesheet (`tailwindcss`, `tw-animate-css`) show up as unused false positives. Verify every hit with a grep that includes `.css` and config files before proposing removal, and never remove as part of a dependency-bump commit — report it as its own change.

34. **Run `ncu` as the THIRD scanner — it is the only one that sees the `packageManager` pin** — `$PM outdated` and `npm outdated` both read `dependencies`/`devDependencies` only. `npm-check-updates` additionally reports the `packageManager` field, which is a pinned dependency that nothing else surfaces (observed: `pnpm@11.0.3 → 12.4.2`, absent from both other scans), and prints declared-range-vs-latest in one table already split into minor and major. No install needed: `pnpm dlx npm-check-updates` (a global `pnpm add -g` lands in `~/Library/pnpm/bin`, which is often not on `PATH`). It does **not** replace the two-command scan of pattern 12 — ncu reports what `package.json` DECLARES, the other two report what is INSTALLED, and a caret range that is already satisfied looks current to ncu while the lockfile sits on an older patch. Run all three; take the union.

35. **`pnpm add` SILENTLY WAIVES a `minimumReleaseAge` policy by writing its own exclude list — check `git status` on `pnpm-workspace.yaml` after every add** — Projects that set `minimumReleaseAge` (a supply-chain guard: reject packages published less than N hours ago) get a second, unadvertised behaviour: when `pnpm add <pkg>@<version>` resolves a package that is too fresh, pnpm appends it to a `minimumReleaseAgeExclude:` block in `pnpm-workspace.yaml` — creating the block if absent. The install then succeeds locally, the guard is lifted for exactly the packages it exists to catch, and **nothing in pnpm's output says so**. Measured 2026-09-25: a 15-package bump wrote 11 entries (the whole `vitest@5.0.2` family, `dotenv@18.0.4`, `better-auth@1.7.6` and its two adapters) into a file that had no such block on the base branch.
    **What made it visible was an accident, not a check.** The commit staged individual files rather than `git add -A`, so `pnpm-workspace.yaml` stayed behind and CI failed all four jobs at `pnpm install --frozen-lockfile` with `ERR_PNPM_MINIMUM_RELEASE_AGE_VIOLATION`. With `-A` the waiver would have been committed, CI would have been green, and the guard would have been disabled for eight packages permanently. Same family as a `pnpm.overrides` block sitting ignored in `package.json` (pattern 18): **a declaration that does not enforce what it claims.**
    ```bash
    git status --porcelain pnpm-workspace.yaml   # after EVERY pnpm add — expect NO output
    git diff pnpm-workspace.yaml                 # if it changed, read it before staging
    ```
    **Take the waiver back, don't commit it.** Find the highest version that already satisfies the window, then set it:
    ```bash
    npm view <pkg> time --json | python3 -c "import sys,json;[print(f'{v:<12}{t}') for v,t in list(json.load(sys.stdin).items())[-6:]]"
    date -u -v-24H +%Y-%m-%dT%H:%M:%SZ   # the cutoff (macOS; GNU: date -u -d '24 hours ago')
    ```
    **The rollback mechanics matter, because `pnpm add` now refuses to help.** Once the lockfile holds rejected entries, every `pnpm add` and plain `pnpm install` aborts on the same policy — the error suggests `pnpm clean --lockfile`, which re-resolves EVERYTHING and quietly moves unrelated packages. Do this instead: restore the lockfile from the base branch, edit the target versions directly in `package.json`, then `pnpm install` — it resolves only the delta.
    ```bash
    git checkout origin/main -- pnpm-lock.yaml   # or your base branch
    # edit package.json to the permitted versions, then:
    pnpm install
    grep -c minimumReleaseAgeExclude pnpm-workspace.yaml   # must be 0
    ```
    **One subtlety worth knowing before you call an entry a violation:** the exclude list and CI's violation list can differ. A package published just over N hours ago was too fresh at `pnpm add` time (so pnpm excluded it) but old enough when CI verified (so CI did not flag it). Observed with `better-auth@1.7.6`, published 24 h 7 min before the run — it stayed, the other four were rolled back. Compare publish timestamps against the cutoff rather than trusting either list alone.
