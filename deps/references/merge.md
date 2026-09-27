# /deps merge — Detailed Instructions

Fully automated. Analyzes, merges, and tests all eligible Dependabot PRs on main.

## Pre-flight Checks

**All checks must pass. If any fails → STOP with clear error message.**

### 1. Clean working state
```bash
git status --porcelain
```
Must be empty. If not → STOP: "Uncommitted changes detected. Commit or stash before running /deps merge."

### 2. Read branch config
```bash
# Read dev branch from config, default to "main"
DEV_BRANCH=$(cat .deps/config.json 2>/dev/null | jq -r '.devBranch // "main"')
```

### 3. Pull latest dev branch
```bash
git checkout $DEV_BRANCH && git pull origin $DEV_BRANCH
```

### 4. Snapshot rollback point
```bash
ROLLBACK_HASH=$(git rev-parse HEAD)
echo "Rollback point: $ROLLBACK_HASH"
```

### 5. Detect package manager

```bash
# Detect package manager from lockfile
if [ -f "pnpm-lock.yaml" ]; then PM="pnpm"
elif [ -f "bun.lockb" ] || [ -f "bun.lock" ]; then PM="bun"
elif [ -f "yarn.lock" ]; then PM="yarn"
elif [ -f "package-lock.json" ]; then PM="npm"
else PM="npm"  # fallback
fi
echo "Package manager: $PM"
```

Use `$PM` consistently for all subsequent commands (`$PM install`, `$PM run typecheck`, etc.).

### 6. Verify no auto-merge workflow on remote (TWO checks required)
```bash
# Check 1: No auto-merge workflow FILES in repo
for f in .github/workflows/*.yml .github/workflows/*.yaml; do
  [ -f "$f" ] || continue
  if grep -qi "dependabot" "$f" && grep -qi "merge" "$f"; then
    echo "FOUND: $f — STOP"
  fi
done

# Check 2: No active auto-merge WORKFLOWS via GitHub API
gh api repos/{owner}/{repo}/actions/workflows --jq '.workflows[] | select(.name | test("dependabot|auto.merge"; "i")) | .name'
```
Both must return empty. If either finds something → STOP: "Auto-merge workflow still active on remote. Run /deps setup first."

## Collect and Sort PRs

### List open Dependabot PRs
```bash
gh pr list --author "app/dependabot" --state open --json number,title,headRefName,statusCheckRollup,updatedAt
```

### Detect and close superseded PRs first

Before merging, identify duplicate PRs for the same package (e.g., PR #6 has 0.81.0 but PR #25 has 0.82.0). Parse package names from PR titles. If multiple PRs target the same package, close the older version with a comment and `--delete-branch`. See `references/close.md` for details. This prevents merging an outdated version.

### Scan for updates Dependabot missed

**This is critical. Dependabot only proposes updates within the semver range in package.json (e.g., `^5.9.3` won't propose `6.x`) — and even inside that range its PRs are neither complete nor current.**

**Run BOTH scanners, every time. Not one plus an optional cross-check — both are the scan.** Neither is complete on its own (pattern 12 in `patterns-js.md`): `pnpm outdated` reads a metadata cache and drops whole rows silently; `npm outdated` queries the registry directly but its `Latest` can lag behind the installed version.

```bash
$PM outdated 2>&1              # may silently OMIT packages; may under-report patch level
npm outdated 2>&1 | head -40   # registry-direct; may show Latest < installed
pnpm dlx npm-check-updates 2>&1   # third scanner: the ONLY one that sees the `packageManager` pin
```

Build the work list as the **union** of both, per package:

1. A package is outdated if **either** tool lists it (observed: `stripe` and `typescript-eslint` appeared only in `npm outdated`).
2. Take the **higher** `Latest` of the two (observed: `@aws-sdk/client-s3` `3.1106.0` via pnpm vs `3.1107.0` via npm).
3. **Discard** any row whose `Latest` ≤ installed — a lagging `latest` dist-tag, not a downgrade to apply (observed: `jsdom` installed `30.0.1`, npm `Latest 29.1.1`).
4. Ignore npm's `Wanted` column in a pnpm workspace — only `Current` vs `Latest` are meaningful.

Then reconcile against the open PRs: **a package named in an open PR is not automatically covered at that version.** Compare each PR's target version against the union's `Latest` — group PRs are routinely stale hours after being opened (observed: a same-morning group PR carried `lucide-react 1.30.0` / `tsx 4.23.11` while latest were `1.31.0` / `4.23.12`). Merge the PR anyway, and fold the remaining delta into the same wave.

When a package is outdated with **no** open PR at all, do not assert *why* without evidence. Read `schedule.interval` from `.github/dependabot.yml` and compare publish times to the PR's creation:

```bash
gh pr view <PR> --json createdAt -q .createdAt
npm view <pkg> time --json | jq -r '.["<version>"]'
```

If the versions predate the PR, batch lag is **ruled out** — report "not covered by any open PR, cause unverified" rather than inventing an explanation (observed: `interval: daily` and all 10 uncovered versions published before the PR was created).

**Rust / hybrid projects (`Cargo.toml` present):** `$PM outdated` covers only the npm half.
ALSO run `cargo outdated` — without it, cross-major crates are invisible (Dependabot never
proposes them, and `cargo update --dry-run` only shows in-range updates):

```bash
command -v cargo-outdated >/dev/null || brew install cargo-outdated   # or: cargo install cargo-outdated
cargo outdated --root-deps-only 2>&1    # workspace-aware: one section per member crate
```

Read the `Latest` column vs `Project`. Real case: `zip 4.6.1` with `Latest 8.6.0` — a
four-major gap with no PR, found only by this scan. Also cross-check open cargo PRs
against `Latest`: a PR bumping to a version below `Latest` is already stale.

For each outdated package NOT covered by a Dependabot PR:
1. **Display to user** with current → latest version and whether it's MAJOR/MINOR/PATCH
2. **Major updates found by outdated but NOT by Dependabot** → add to Wave 3 (major updates). These need the deepest analysis since they were intentionally excluded from the semver range.
3. **Minor/Patch updates missed** → **merge them too — do NOT just report.** Add each to the appropriate wave (devDependency → Wave 1, dependency → Wave 2) and treat it exactly like a Dependabot PR of the same risk tier: impact analysis, then merge by bumping the version in `package.json` (there is no PR branch, so edit `package.json` directly), then validate in the same `$PM install` + typecheck/lint/test pass as the rest of the wave.

   **Do not assume "Dependabot should have caught them."** The usual reason is **batch lag**: Dependabot runs on a schedule (often `weekly`), so any version published *between* runs shows up in `$PM outdated` days before Dependabot opens a PR. `$PM outdated` is real-time; the Dependabot queue is not. Pick the update up now rather than waiting a cycle.

   Note on 0.x packages: Dependabot's default `versioning-strategy` **does** raise a caret range that has fallen behind (e.g. it will bump `^0.100.1` → `^0.104.1` even though `0.104` is outside the `^0.100.1` cap). So a stale 0.x dep is almost always batch lag, not a config gap — don't reach for `versioning-strategy`/`ignore` tuning before confirming the version actually predates the last Dependabot run. If a repo genuinely needs faster pickup, the lever is `schedule.interval: daily`, not `versioning-strategy`.

**Include all of these (merged and, for Wave 3, pending) in the report under a separate section "Updates beyond Dependabot" so the user sees the full picture.**

> **Note for `/deps check` (read-only):** still only *report* these — `check` never merges. The merge-them behavior above applies to `/deps merge`.

### Check CI status per PR
From `statusCheckRollup`, determine:
- All checks `COMPLETED` + `SUCCESS` → **green**
- Any check `COMPLETED` + `FAILURE` → **red**
- Any check `IN_PROGRESS` / `QUEUED` / `PENDING` → **pending**

**Stale CI detection:** After merging a PR, Dependabot may rebase other open PRs against the new $DEV_BRANCH HEAD. This invalidates their CI status. Before merging the NEXT PR in the queue, re-check its CI status:
```bash
gh pr view $NEXT_PR_NUMBER --json statusCheckRollup --jq '.statusCheckRollup | map(.conclusion // .status) | join(",")'
```
If status changed from green to pending → skip this PR for now, add to "CI pending" list.

**Diagnose red CI before skipping (see pattern 23 in `patterns-ci.md`):** many PRs red at once + same
failing step + sub-minute failure = transient CI-infra outage, not broken updates. Comment
`@dependabot rebase` on each, wait for fresh runs, merge on green. After the rebase push the
old checks vanish — an EMPTY `statusCheckRollup` means "new run not registered yet", not
"complete"; require an explicit SUCCESS/FAILURE conclusion per PR before deciding.

### Batch size control

If user specifies `--limit N` (e.g., `/deps merge --limit 5`), only process the first N PRs from the merge queue. This enables incremental merging across sessions. Default: no limit (process all).

### Sort merge queue
1. **Dependencies before dependents** — e.g., `react` before `@types/react`. Check if package A is in the dependency tree of package B (via `npm view B dependencies`). If so, merge A first.
2. **Group related packages** — same `@scope/` prefix or known pairs (e.g., `@typescript-eslint/parser` + `@typescript-eslint/eslint-plugin`, `next` + `eslint-config-next` + `@next/eslint-plugin-next`, `tailwindcss` + `@tailwindcss/postcss`). **However:** grouped PRs often conflict after the first one merges (each PR's lockfile was based on a different main). Handle this gracefully:
   - Merge the **leader** (primary package, e.g., `next`) first
   - Try merging followers (`eslint-config-next`, etc.) immediately after
   - If a follower has `CONFLICTING` mergeability → skip it, mark as "waiting for Dependabot rebase" in the report. Dependabot auto-rebases within minutes.
   - These skipped PRs will be picked up in the next `/deps merge` session — OR, faster: if the beyond-Dependabot pass reaches the same dep at an equal-or-newer in-range version, close the PR as superseded instead of waiting (pattern 21 in `patterns-workflow.md`). Cargo PRs usually DON'T need any of this — their lockfile hunks rarely overlap, merge them back-to-back (pattern 22 (`patterns-ci.md`)).
3. **Patches first** (compare semver from PR title: "from X.Y.Z to X.Y.W" where X.Y unchanged)
4. **Then minor updates** (X unchanged)
5. **Major updates go to Wave 3** (X changed) — separated for deep analysis
6. **Runtime deps before devDeps** within each wave (check `devDependencies` vs `dependencies` in package.json)

### Split into two waves

After sorting, split the queue into two waves based on risk:

**Wave 1: Dev-Dependencies (low risk)** — packages in `devDependencies` only: test tools, linters, type definitions, build tools. These don't affect production code.
- Display brief impact summary per PR (version + one-line what changed)
- Merge ALL in wave 1 sequentially via `gh pr merge --squash` + `git pull`
- One `$PM install` after all wave 1 merges
- One validation run (typecheck + lint + test) after all wave 1 merges
- If validation fails: bisect to find the causing merge, revert it

**Wave 2: Runtime Dependencies (higher risk)** — packages in `dependencies`: frameworks, UI libraries, DB drivers, auth. These affect production behavior.
- Merge ONE at a time
- `$PM install` + validation (typecheck + lint + test) after EACH merge
- If validation fails: revert immediately, STOP
- Impact analysis is REQUIRED for each runtime dep (changelog, usage, breaking changes)

**Wave 3: Major Updates** — ALL packages with a major version bump (X changed in X.Y.Z), regardless of dev or runtime. These get the deepest analysis and individual merge + validation.

For each major update:
0. **Toolchain peer check (cheap, do this FIRST)** — `npm view <toolchain-pkg> peerDependencies`
   for every tool that compiles/checks against the package (type checkers, framework kits,
   lint plugins). Unfulfilled peer range for the new major = instant HIGH RISK skip; record
   the re-check trigger ("revisit when X peers ^N") and skip steps 1–4.
1. **Deep changelog analysis** — fetch ALL release notes between old and new version. Look for migration guides, breaking changes, and deprecated APIs.
2. **Usage scan** — find every file that imports/uses the package. For each usage, check if it uses any API that changed.
3. **Risk assessment:**
   - **Low risk** (merge normally): Major bumps that don't affect our usage (e.g., dropped support for old Node versions we don't use, renamed internal APIs we don't call).
   - **Medium risk** (merge + migrate): Breaking changes that affect our code but have a clear migration path. Apply the migration BEFORE merging — create a migration commit on a temp branch, then merge the Dependabot PR.
   - **High risk** (skip + report): Breaking changes with unclear migration, or infrastructure changes that affect the whole stack (e.g., Node version bumps that mismatch CI). Skip and explain in detail in the report what needs to happen.
4. **Migration strategy for medium risk:**
   ```
   a) Read migration guide from changelog/docs
   b) Find affected files via grep
   c) Apply code changes (rename APIs, update imports, adjust config)
   d) Commit migration: "refactor: migrate to {package} v{version}"
   e) THEN merge the Dependabot PR via gh pr merge --squash
   f) Pull, install, validate (typecheck + lint + test)
   g) If validation fails: revert BOTH the migration commit AND the merge
   ```
5. **Infrastructure majors** (Node Docker image, @types/node):
   - Check if the new Node version is LTS (`node --version` schedule)
   - Check if CI uses the same Node version (read `.github/workflows/*.yml`)
   - If version mismatch between Docker and CI → update CI to match in the same session
   - If new version is not LTS → skip, explain why in report

**Why three waves:** Major updates need careful analysis that patches/minors don't. Separating them ensures: (a) safe updates land first, building confidence; (b) major updates get the attention they deserve; (c) if a major breaks things, it doesn't block the safe updates.

## Per-PR Processing Loop

**Progress tracking:** Display progress before each PR:
```
[Wave 1 — Dev] [3/8] Merging: @playwright/test 1.58.1 → 1.59.1 (PR #32)
[Wave 2 — Runtime] [2/5] Merging: better-auth 1.4.18 → 1.5.6 (PR #19)
```

For each PR (or grouped PRs) in the merge queue:

### a) Impact Analysis — MANDATORY, ALWAYS DISPLAYED TO USER

**This is the core value of the /deps skill. NEVER skip it. The user MUST see the analysis before merging proceeds.**

**Wave 1 (dev-deps):** Brief analysis — version bump + one-line summary of what changed.
**Wave 2 (runtime deps):** Full analysis with changelog, usage, and code suggestions.

**For EVERY PR, display to the user before merging:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2/8] better-auth 1.4.18 → 1.5.6 (MINOR, Runtime, 14 Dateien)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Changelog: {key changes from release notes}
Breaking Changes: {none / list}
Neue Features: {relevant new APIs}
Code-Vorschlag: {what we could adopt, where, effort}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**How to gather this information:**

1. **Read changelog:** Fetch from GitHub releases or npm registry:
   ```bash
   # For npm packages — get repo URL
   npm view {package} --json | jq -r '.repository.url'
   # Then fetch recent releases
   gh api repos/{owner}/{repo}/releases --jq '.[0:3] | .[] | "## \(.tag_name)\n\(.body)"'
   ```
   Alternative: WebFetch the changelog/release page.

2. **Find project usage:**
   ```bash
   # Which files import this package?
   grep -r "from ['\"]$PACKAGE" src/ --include="*.ts" --include="*.tsx" -l
   grep -r "require(['\"]$PACKAGE" src/ --include="*.js" -l
   ```
   Count files and list the key ones.

3. **Analyze and display:**
   - Breaking changes? (look for "BREAKING" in changelog)
   - Deprecations? (look for "deprecated" — if we use the deprecated API, this is a CODE SUGGESTION)
   - New features? (if relevant to our usage, this is a CODE SUGGESTION)
   - Rate effort: small (no code changes) / medium (< 5 files) / large (> 5 files)

4. **Code suggestions — collect for the report:**
   For each update that enables new APIs or requires migration:
   - What: specific API/feature name
   - Where: which files in our project
   - Benefit: why it matters
   - Effort: small/medium/large

5. **Record** ALL findings for the report. The report is what the user reviews to decide on code improvements.

### b) Squash-merge via GitHub API

```bash
gh pr merge $PR_NUMBER --squash --delete-branch
```

Wait for merge to complete, then pull:
```bash
git pull origin $DEV_BRANCH
```

### c) Lockfile — do NOT fix per PR

**Skip lockfile resolution during the per-PR loop.** Sequential Dependabot merges cause lockfile conflicts because each PR's lockfile was generated against a different base. Fixing per PR creates extra commits that make the next PR's lockfile conflict again (observed: 60% of merges break the lockfile).

Instead: **one lockfile fix after all merges** (see "After All Merges" section).

The only exception: if `$PM typecheck` or `$PM test` fails because of missing packages (not a type/logic error), run `$PM install` before validation to ensure packages are available.

### d) Test coverage check

1. Find which features/routes are affected (from step a2 — files that import the package)
2. Check if tests exist for those files:
   ```bash
   # For each affected file, look for corresponding test
   # src/features/auth/auth.ts → look for tests/**/auth*.spec.* or tests/**/auth*.test.*
   ```
3. If gaps found and the dependency is a runtime dependency:
   - Create targeted tests for uncovered features
   - Commit: `test: add coverage for {feature} (triggered by {package} update)`
   - Push to $DEV_BRANCH
4. If pure dev-dependency (eslint, prettier, typescript, etc.): smoke tests are sufficient

### e) Run local validation

**Detect test scripts from `package.json` — do NOT guess script names.**

```bash
# Read actual script names from package.json
cat package.json | jq -r '.scripts | keys[]' | grep -i test
# Use the EXACT script names found. Common mappings:
#   "test" → pnpm test        (vitest run, jest, etc.)
#   "test:run" → pnpm test:run
#   "typecheck" → pnpm typecheck
#   "lint" → pnpm lint
```

**Run these checks locally (fast, no DB needed):**

```bash
# 0. Ensure packages are installed (lockfile may be broken from sequential merges — this is expected)
$PM install 2>/dev/null

# 0b. Clear framework type caches (Next.js, etc.) — stale caches cause false typecheck failures
rm -rf .next/dev/types 2>/dev/null

# 1. Type check
$PM typecheck

# 2. Lint
$PM lint

# 3. Unit tests (script name from package.json — typically "test")
$PM test
```

- **All green** → continue to next PR (no push needed between PRs)
- **Any red** → go to revert strategy
- **Note:** If typecheck/lint/test fail because of a broken lockfile (missing module), run `$PM install` first. If they fail for other reasons, it's a real dependency breakage → revert.

**Playwright E2E tests are NOT run locally.** They run automatically via CI after push to $DEV_BRANCH. The CI pipeline on GitHub is the authoritative E2E validation. After all merges are complete, wait for CI to pass on the latest commit before proceeding to `/deps promote`.

**Why no local Playwright:**
- Requires running database (Docker) which may not be available
- Project rules may prohibit local testing (e.g., CLAUDE.md "NEVER test on localhost")
- CI runs E2E in a controlled environment with seeded data
- Local port conflicts (dev server occupying ports)

### e2) When validation fails: read the error list by CODE, not by count

A runtime bump that breaks the typecheck usually produces a LOUD symptom and a QUIET cause.
Before reverting or bisecting, sort the errors by TypeScript code and look for
`TS2353` / `TS2561` / `TS2559` **inside the library's own configuration object** — an
excess or unknown property there makes inference of the whole options literal fall back to
its constraint, and every type derived from it collapses.

Observed (better-auth 1.7.3 → 1.7.5): ~40 × `Property 'accountId' does not exist` spread
across every page that reads the session — none of which import better-auth directly — plus
exactly two errors in `src/lib/auth.ts`. The two were the cause; fixing them cleared all 40.
Reverting the package, or bisecting the other 17 packages in the same wave, would have
found nothing.

Then check whether the offending keys were ever READ at runtime:

```bash
grep -rl "<optionName>" node_modules/<pkg>/dist        # new version
grep -rl "<optionName>" node_modules/.pnpm/<pkg>@<oldver>*/node_modules/<pkg>/dist
```

Zero hits in both = the option was dead all along and only became visible now. Deleting it
is behavior-preserving; renaming it to the real key ACTIVATES a path that has never run.
That is a behavior change — make it deliberately, put it in the commit message, and tell
the user (pattern 31 in `patterns-js.md`).

### f) Revert strategy (on failure)

```bash
# The squash-merge was done via GitHub API, so main has the merge commit.
# Revert the most recent merge commit (and any test commits for this PR).
git revert --no-commit HEAD~N..HEAD   # N = number of commits since before this PR's merge
git commit -m "revert: $PACKAGE update (tests failed)"
git push origin $DEV_BRANCH
```

**Note:** Since lockfile fixes are deferred to "After All Merges", the revert only needs to cover the merge commit itself (and any test-coverage commits for this PR). This is typically `git revert HEAD` for a single merge.

- Report the failure with details (which test failed, error message)
- **STOP processing** — do not merge further PRs
- Generate partial report for all PRs processed before the failure

### g) Branch cleanup

Branch is automatically deleted by `--delete-branch` flag in step (b). No manual cleanup needed.

## After All Merges

### Push order — finish ALL PR merges before pushing anything local

Every squash-merge is itself a commit on `$DEV_BRANCH` and triggers a deploy, so PR merges
cannot be batched away. What you CAN control is where your own commits land relative to them.
**Do all PR merges first, then push the lockfile/beyond-Dependabot commit last**, so exactly
one deploy sees the final state.

Interleaving them is what goes wrong: merging a group PR, pushing the beyond-Dependabot
commit, then merging one more PR produced three deploy waves in ten minutes. Each cancelled
its predecessor via the concurrency group and stacked container-registry logins, which tripped
a registry rate limit and painted two deploys red that had nothing wrong with them (see
"Wait for CI" below). A cancelled intermediate deploy is EXPECTED and not a failure — the
final one covers every commit — but the fewer waves, the less rate-limit exposure.

If a PR turns out to need a decision mid-run (e.g. a CODEOWNERS review), do not stall the
whole queue: finish the mergeable PRs, push your local commit last anyway, and merge the
held-back PR afterwards as its own wave.

### Fix lockfile (single commit for all merges)

```bash
# Pull latest (catches any external pushes)
git pull origin $DEV_BRANCH

# Regenerate lockfile (sequential merges cause duplicated keys — this is expected)
$PM install

# Commit lockfile fix if changed
git diff --quiet pnpm-lock.yaml 2>/dev/null || {
  git add pnpm-lock.yaml   # or equivalent lockfile
  git commit -m "chore: update lockfile after dependency updates"
  git push origin $DEV_BRANCH
}
```

**⚠ Before staging, check `pnpm-workspace.yaml` — `$PM install`/`add` may have waived a security policy there.** If the project sets `minimumReleaseAge`, pnpm appends too-fresh packages to a `minimumReleaseAgeExclude:` block in that file, creating it if absent, and says nothing. Committing it disables the guard for exactly the packages it exists to catch. The narrow `git add pnpm-lock.yaml` above does not pick the file up — that is deliberate, but it also means the change sits unnoticed in your working tree:

```bash
git status --porcelain pnpm-workspace.yaml   # expect NO output
```

Not empty → do NOT stage it. Roll the too-fresh versions back to the highest ones that already satisfy the window. Full mechanics, including why `pnpm clean --lockfile` is the wrong repair, in pattern 35 in `patterns-js.md`.

**Why one lockfile commit:** Each Dependabot squash-merge includes a lockfile generated against a different base. Sequential merges create duplicated keys. Fixing per PR creates more conflicts for the next PR (observed: 60% breakage rate). One fix after all merges is cleaner.

### Local validation (final)

```bash
# Clear framework type caches before final validation
rm -rf .next/dev/types 2>/dev/null

# Full local validation
$PM typecheck
$PM lint
$PM test                   # Unit tests (exact script from package.json)
```

If local validation fails, use git bisect to find the causing merge:
```bash
git bisect start HEAD $ROLLBACK_HASH
git bisect run sh -c '$PM typecheck && $PM test'
BAD_COMMIT=$(git bisect view --format="%H")
git bisect reset
git revert $BAD_COMMIT --no-edit
git push origin $DEV_BRANCH
```
Update the report: mark the identified package as "reverted after local validation failure".

### Wait for CI (E2E validation)

After all merges are pushed to $DEV_BRANCH, CI runs automatically on GitHub. This includes E2E/Playwright tests.

```bash
# Check CI status on latest commit — MUST verify headSha, see below
gh run list --branch $DEV_BRANCH --limit 1 --json status,conclusion,name,headSha
```

**⚠️ Stale-success trap: `--limit 1` alone is NOT proof.** Right after a push (or when a
dispatch silently failed) the newest run may not be registered yet — `-L1` then shows the
PREVIOUS commit's green run and reads as "CI green" for code it never tested. Always compare
the run's `headSha` against your pushed commit (`git rev-parse HEAD`); if they differ, the
run you're looking at is stale — keep waiting. Same rule when watching runs in another repo
after a dispatch: record a timestamp before dispatching and only trust runs with
`createdAt > mark`.

**Wait for CI to complete.** Report CI status to user:
- **CI green** → "All merges passed. CI on $DEV_BRANCH is green. Ready for /deps promote."
- **CI red** → **diagnose before reverting anything** (see below). Only once a genuine test
  failure is confirmed: identify the failing test, find the causing merge via git log, revert
  it, push, and update the report.

**⚠ Red on $DEV_BRANCH is often infrastructure, not your updates — check the failing STEP first.**
Reverting a good merge because of a registry hiccup wastes a full cycle and puts a bogus
"reverted" entry in the report. Get the failed step names before forming any theory:

```bash
gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs --paginate \
  --jq '.jobs[] | select(.conclusion=="failure") | "\(.name)\n  step: \([.steps[]|select(.conclusion=="failure")|.name]|join(", "))"'
```

Signatures that mean **infrastructure, not regression** — rerun, do NOT revert:
- Failure in a **registry-login / image-pull / container-start step** (`Log in to GHCR`,
  `Start app container`) — no test ever ran. Observed: `docker login ghcr.io` returning
  `Error response from daemon: Get "https://ghcr.io/v2/": denied: denied` across 3 of 7 shards
  after several deploys in quick succession — a secondary rate limit, not a credentials
  problem. A plain rerun turned all shards green with zero code changes.
- Failure within seconds of job start, same step across many jobs, all in one time window
  (see pattern 23 in `patterns-ci.md`).

Remedy: `gh run rerun <run_id> --failed`, then re-check. If the rerun is green, the code was
never at fault — record it in the report as an infra flake, not as a skipped/reverted package.
Genuine test failures look different: the test step runs, individual specs fail by name, and
the same specs fail again on rerun.

**Do NOT proceed to `/deps promote` until CI is green.**

## Fix New Warnings (MANDATORY)

**After all merges: fix warnings that were INTRODUCED by the dependency updates. This is not optional.**

Focus on warnings caused by the updates — not pre-existing warnings unrelated to the merged packages. If in doubt, check if the warning references a package that was just updated.

### What to fix

1. **Lint warnings** — run `$PM run lint` and fix warnings related to updated packages
   - New deprecation warnings from updated APIs → update usage
   - Unused imports from API changes → remove them

2. **Build warnings** — run `$PM run build` and fix warnings from updated packages
   - Deprecation warnings from updated frameworks → update API usage

3. **Test warnings** — run `$PM run test` and fix warnings from updated test tools

### Process

```bash
# 1. Check lint warnings
$PM run lint 2>&1 | grep -i "warning"
# If any from updated packages → fix, commit

# 2. Check build warnings
$PM run build 2>&1 | grep -iE "warn|⨯"
# If any from updated packages → fix, commit

# 3. Push fixes
git push origin $DEV_BRANCH
```

Commit message: `fix: resolve warnings from dependency updates`

**Do NOT proceed to report if updated packages cause new warnings.**

## Persist and Display Report

### Save report to disk
```bash
mkdir -p .deps

# Archive previous report if it exists (prevents overwriting history)
if [ -f .deps/last-report.md ]; then
  PREV_DATE=$(head -5 .deps/last-report.md | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
  mv .deps/last-report.md ".deps/report-${PREV_DATE:-old}.md"
fi
```

Write `.deps/last-report.md` using this exact template:

```markdown
# Dependency Update Report — {project-name}

**Date:** {YYYY-MM-DD}
**Branch:** {dev-branch}

## Merged ({N})

| Package | Update | Summary |
|---------|--------|---------|
| {package} | {old} → {new} | {one-line impact summary} |

## Skipped — CI red ({N})

| Package | Update | Failure |
|---------|--------|---------|
| {package} | {old} → {new} | {failure reason} |

## Skipped — CI pending ({N})

| Package | Update | Note |
|---------|--------|------|
| {package} | {old} → {new} | Re-run /deps merge later |

## Reverted — tests failed ({N})

| Package | Update | What broke |
|---------|--------|-----------|
| {package} | {old} → {new} | {test name + error} |

## Code Suggestions

### 1. {package} {version} — {suggestion title}
- **Affects:** {file paths}
- **Benefit:** {description}
- **Effort:** {small/medium/large}

## Updates beyond Dependabot

Updates found via `$PM outdated` that Dependabot did not create PRs for (outside semver range):

| Package | Current | Latest | Type | Risk |
|---------|---------|--------|------|------|
| {package} | {current} | {latest} | MAJOR | {low/medium/high — see Wave 3 analysis} |
```

This file is gitignored (added during /deps setup). It is read verbatim by `/deps promote` as the PR body.

### Display report to user

Show the formatted report in the terminal. Use the template from the design spec.

### Code Suggestions — Separate Interactive Phase

After displaying the report, if there are code suggestions:

"The following improvements are possible based on the updated dependencies. Which ones should I implement?"

Per suggestion, user decides:
- **"yes"** → implement on main, commit, push
- **"later"** → create a GitHub issue or TODO
- **"no"** → skip

After all code suggestion decisions are made, proceed automatically to promote.

## Auto-Promote

**After all merges are complete, CI is green, and code suggestions are handled — automatically create the promote PR. Do NOT wait for a separate `/deps promote` command.**

**Single-trunk guard:** if `.deps/config.json` has `"prodBranch": null`, there is no prod
branch — skip this whole section; the merge report is the final artifact. Check with
`jq -e '.prodBranch != null'` (NOT `// "prod"`, which silently turns null into "prod").

```bash
# Check for existing PR
EXISTING_PR=$(gh pr list --base $PROD_BRANCH --head $DEV_BRANCH --state open --json url --jq '.[0].url' 2>/dev/null)

if [ -n "$EXISTING_PR" ]; then
  echo "PR already exists: $EXISTING_PR"
else
  DATE=$(date +%Y-%m-%d)
  gh pr create \
    --base $PROD_BRANCH \
    --head $DEV_BRANCH \
    --title "chore(deps): promote dependency updates ($DATE)" \
    --body "$(cat .deps/last-report.md)"
fi
```

Display: "PR created: {url} — review and merge on GitHub when ready."

**The only manual step is merging the PR on GitHub.** Everything else is automated.
