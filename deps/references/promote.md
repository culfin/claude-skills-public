# /deps promote — Detailed Instructions

Creates a PR to promote dependency updates from main to prod, and syncs branches after merge.

## Pre-flight

**All checks must pass. If any fails → STOP.**

1. **Read branch config:**
   ```bash
   DEV_BRANCH=$(python3 "$DEPS_DIR/scripts/branch_config.py" devBranch) || exit 1
   PROD_BRANCH=$(python3 "$DEPS_DIR/scripts/branch_config.py" prodBranch) || exit 1   # empty = single-trunk repo, no promote
   [ -n "$PROD_BRANCH" ] || { echo "prodBranch is null: single-trunk repo, nothing to promote"; exit 0; }
   ```
2. **Pull latest dev branch:** `git checkout $DEV_BRANCH && git pull origin $DEV_BRANCH`
3. **Check for REAL divergence (prod ahead of main):**
   ```bash
   git fetch origin $PROD_BRANCH
   PROD_AHEAD_REAL=$(git rev-list --count --no-merges origin/$DEV_BRANCH..origin/$PROD_BRANCH)
   ```
   - If `PROD_AHEAD_REAL > 0` → prod has real commits (a hotfix landed directly on prod) that main doesn't. **Auto-fix:** merge prod into main first:
     ```bash
     git merge origin/$PROD_BRANCH --no-edit
     git push origin $DEV_BRANCH
     ```
   - If `PROD_AHEAD_REAL == 0` (prod is ahead only by promote merge commits) → **do nothing.** main already holds all content; the merge nodes are expected for a merge-commit promote workflow without sync-back. A blind `git merge origin/prod` here would just pull those merge nodes into main for no benefit. Skip the auto-fix and proceed.
   - This ensures main is always a content-superset of prod before creating the promote PR — measured by real commits, not merge topology.
4. **Verify CI is green on $DEV_BRANCH:**
   ```bash
   gh run list --branch $DEV_BRANCH --limit 1 --json status,conclusion,name
   ```
   - CI must show `conclusion: "success"`. If CI is red or pending → STOP: "CI on $DEV_BRANCH is not green. Please wait or fix the failures before promoting."
5. **Check report exists:** `.deps/last-report.md`
   - If not → warn: "No merge report found. Showing diff instead."

## Steps

### 1. Load report

Read `.deps/last-report.md` for PR body content.

### 2. Show diff

```bash
git log --oneline origin/$PROD_BRANCH..origin/$DEV_BRANCH
```

Display summary: "N commits will be promoted to prod" with the list.

If no diff → "main and prod are already in sync. Nothing to promote."

### 3. Create PR

```bash
# Check for existing PR first
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

### 3a. Handle PR conflicts (if any)

If the promote PR shows conflicts (e.g., `changelog.json`, `pnpm-lock.yaml`):

**NEVER resolve conflicts by pushing directly to prod.** This violates Safety Rule #2 and causes prod to diverge from main.

**Correct workflow:**
1. Close the conflicting PR: `gh pr close <number>`
2. Merge prod into main to pick up any prod-only commits:
   ```bash
   git checkout $DEV_BRANCH && git pull origin $DEV_BRANCH
   git fetch origin $PROD_BRANCH
   git merge origin/$PROD_BRANCH --no-edit
   # Resolve any conflicts here — on main, not on prod
   git push origin $DEV_BRANCH
   ```
3. Recreate the promote PR (go back to Step 3)

This ensures all conflict resolution happens on main, and prod only ever receives clean merges via PR.

### 4. Inform user

"PR created: {url}

Review and merge on GitHub — **be sure to use 'Create a merge commit', NOT 'Rebase and merge'!**
Rebase creates new commit SHAs on prod, which makes the branches diverge."

**Do NOT merge the PR automatically.** The user must approve and merge on GitHub.

### 5. Sync-back after merge (tidiness, not correctness)

**After the user has merged the promote PR on GitHub**, prod has a merge commit that main doesn't know about. Syncing it back keeps `origin/main..origin/prod` at zero, so any later count there means real drift at a glance. Skipping it is harmless: a promote merge node is merge-only divergence, which Safety Rule 12 explicitly does not treat as drift.

> **Scope:** this runs only when `/deps promote` itself created and merged the PR — here the sync-back deliberately pulls back `/deps`'s *own* fresh promote merge commit (so it uses the raw `PROD_AHEAD`, unlike the Step 3 pre-flight which measures real drift with `--no-merges`). If this repo promotes via a different workflow that intentionally skips sync-back (e.g. a project's own prod-release command, leaving prod ahead by merge nodes by design), `/deps promote` is not the promote path and this step does not run — do not retrofit a sync-back onto that workflow.

**Option A: Automatic (if still in the same session)**

After user confirms the PR was merged:
```bash
git fetch origin $PROD_BRANCH $DEV_BRANCH
PROD_AHEAD=$(git rev-list --count origin/$DEV_BRANCH..origin/$PROD_BRANCH)

if [ "$PROD_AHEAD" -gt 0 ]; then
  git checkout $DEV_BRANCH
  git pull origin $DEV_BRANCH
  git merge origin/$PROD_BRANCH --no-edit
  git push origin $DEV_BRANCH
  echo "✅ Branches synchronized. prod is no longer ahead."
else
  echo "✅ Branches are already in sync."
fi
```

**Option B: Not in this session**

Nothing picks it up later — and nothing needs to. `/deps` status and the Step 3 pre-flight count divergence with `--no-merges` and deliberately ignore promote merge nodes (Safety Rule 12). prod simply stays ahead by merge-only commits; the next promote PR works the same either way.

**Inform user:**
"After merging the PR on GitHub, confirm here and I will sync prod back into main. If you skip it, nothing breaks — prod is then ahead only by the merge commit, which is not drift."
