# /deps setup — Detailed Instructions

One-time setup per project. Ensures test infrastructure and safe configuration.

## Step-by-Step

### 0. Verify Prerequisites

**Check that required CLI tools are available and authenticated:**

```bash
# gh CLI must be installed and authenticated
gh auth status 2>&1
```

- If `gh` not found → STOP: "GitHub CLI (gh) is not installed. Install via: brew install gh"
- If not authenticated → STOP: "GitHub CLI is not authenticated. Run: gh auth login"
- Must show the correct account for this repo

```bash
# git must be configured
git config user.name && git config user.email
```

- If either is empty → STOP: "Git user not configured. Run: git config --global user.name/email"

### 1. Detect Project Ecosystem(s)

Read `references/ecosystems.md` → "Project Type Detection" section.
Run detection. Report findings to user:

```
Detected ecosystems:
  - Node (pnpm) — package.json found
  - Flutter — flutter/pubspec.yaml found
```

For monorepos: list all ecosystems found with their root directories.

### 2. Check Test Framework

Per detected ecosystem, check if a test framework is installed (see `references/ecosystems.md` → "Detection").

If missing:
- Tell the user which framework will be installed and why
- Install using the recommended command from ecosystems.md
- Commit the config changes

### 3. Check and Create Smoke Tests

**Search** for existing smoke/health tests:
- Node/Playwright: files matching `**/smoke*.spec.*`, `**/health*.spec.*`
- Flutter: `test/smoke_test.dart`, `integration_test/smoke_test.dart`
- Swift: `Tests/SmokeTests/`
- Android: `src/test/**/SmokeTest.*`

**If none found → CREATE them. This is not optional.**

Analyze the project to determine what the smoke test should cover:
1. Read the project's existing test structure (directory layout, auth setup, test helpers)
2. Read the project's main routes/entry points
3. Create a smoke test file that follows the project's existing test patterns

**Smoke test requirements — MUST include all of these:**

For **web apps** (Node/Playwright), create TWO smoke test files:

**Public smoke test** (`tests/e2e/specs/public/smoke.spec.ts` or match existing test directory):
- App responds with HTTP 200 on the main route (`/`)
- Login/auth page renders form elements without JS errors (pageerror + console.error)
- Registration page renders without errors
- Locale switching produces different translations
- Static assets load without 4xx/5xx errors
- CSS is loaded (computed styles check)

**Authenticated smoke test** (`tests/e2e/specs/dashboard/smoke.spec.ts`):
- Dashboard main view loads after authentication (use existing auth setup/fixtures)
- Navigation between 2-3 core dashboard routes works without errors
- No uncaught exceptions (pageerror) on any authenticated page
- At least one data-driven component renders (table, list, or chart)

Both files must use `page.on('pageerror')` for uncaught exceptions AND `page.on('console')` for console.error tracking. Simply checking `body.toBeVisible()` is NOT sufficient — verify actual content renders.

For **mobile apps** (Flutter), create `test/smoke_test.dart`:
- App launches without crash
- Main screen widget renders
- Basic navigation works (tap on 2-3 main UI elements)

For **libraries** (no UI), create `test/smoke_test.dart` or `tests/smoke.test.ts`:
- Package imports without errors
- Main exported function/class can be instantiated
- One basic API call returns expected type

**After creating:**
```bash
git add <smoke-test-file>
git commit -m "test: add smoke tests for /deps dependency validation"
git push origin $DEV_BRANCH
```

**Do NOT skip this step.** The smoke test is the baseline that `/deps merge` runs after every dependency update. Without it, dependency breakage goes undetected.

### 4. Initialize .deps/ directory and .gitignore

```bash
mkdir -p .deps
grep -q '.deps/' .gitignore 2>/dev/null || echo -e "\n# deps skill state\n.deps/" >> .gitignore
git add .gitignore
git commit -m "chore: add .deps/ to gitignore"
```

### 5. Confirm Branch Strategy

```
Branch strategy:
  Development: main (default)
  Production:  prod

Override? [enter to confirm defaults]
```

Store in `.deps/config.json` if overridden:
```json
{ "devBranch": "main", "prodBranch": "prod" }
```

### 6. Remove Auto-Merge Workflows

**This is critical for safety. Both systems cannot coexist.**

```bash
# Find workflows that merge Dependabot PRs (don't assume filename). A hit is a candidate:
# read it and confirm it really merges before proposing removal — a workflow that only labels
# PRs or runs on merge_group is not a competitor.
FOUND_WORKFLOWS=()
for f in .github/workflows/*.yml .github/workflows/*.yaml; do
  [ -f "$f" ] || continue
  if grep -qi "dependabot" "$f" && grep -qiE 'gh pr merge|automerge|auto-merge' "$f"; then
    FOUND_WORKFLOWS+=("$f")
    echo "Found: $f"
  fi
done
```

If found:
1. Show the user which file(s) will be removed and why:
   "The /deps skill replaces this workflow. Both running simultaneously causes race conditions — the workflow could merge a PR while /deps is analyzing it."
2. Delete ALL found workflow file(s)
3. Commit: `chore: remove dependabot auto-merge workflow(s) (replaced by /deps skill)`
4. Push to dev branch (read from `.deps/config.json` or default `main`)

**Verify removal on remote — check BOTH:**
```bash
# 1. Check no workflow FILES exist for each deleted file
for f in "${FOUND_WORKFLOWS[@]}"; do
  gh api "repos/{owner}/{repo}/contents/$f" 2>&1 | grep -q "Not Found" || echo "STILL EXISTS: $f"
done

# 2. Check no active auto-merge WORKFLOW RUNS exist
gh api repos/{owner}/{repo}/actions/workflows --jq '.workflows[] | select(.name | test("dependabot|auto.merge"; "i")) | .name'
```
Both must return empty. If anything found → setup is incomplete.

### 7. Report

```
/deps setup complete:
  Ecosystems: Node (pnpm), Flutter
  Test frameworks: Playwright, flutter_test
  Smoke tests: Created (2 files)
  Auto-merge workflow: Removed
  Branch strategy: main → prod
  
Ready to run /deps merge
```
