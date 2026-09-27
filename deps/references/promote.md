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
3. **Does prod hold content main lacks?** (content, not commit topology — see Safety Rule 12)
   ```bash
   git fetch origin $PROD_BRANCH
   # Does prod hold content that main lacks? Merge prod into main *in memory* (nothing is written
   # to the working tree or any branch) and compare the result with main's tree. Equal = main already
   # contains everything; merge-only topology is fine. Unlike counting --no-merges commits, this also
   # catches content introduced INSIDE a merge commit (a conflict resolution or hotfix on prod).
   # Needs git >= 2.38. A conflict (non-zero exit) counts as "prod has own content".
   MERGED=$(git merge-tree --write-tree origin/$DEV_BRANCH origin/$PROD_BRANCH 2>/dev/null | head -1) || MERGED=conflict
   if [ "$MERGED" = "$(git rev-parse origin/$DEV_BRANCH^{tree})" ]; then PROD_OWN_CONTENT=0; else PROD_OWN_CONTENT=1; fi
   ```
   - `PROD_OWN_CONTENT == 1` → a hotfix or a conflict resolution landed on prod. Merge prod into the
     dev branch first, push, and let CI run on the new dev head (step 4 then checks that SHA):
     ```bash
     git merge origin/$PROD_BRANCH --no-edit
     git push origin $DEV_BRANCH
     ```
   - `PROD_OWN_CONTENT == 0` → **do nothing**, even if prod is ahead by promote merge commits. main
     already contains everything; a sync merge would only move merge nodes around.
4. **Candidate CI — every required check green on exactly the commit you promote:**
   ```bash
   OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
   CANDIDATE=$(git rev-parse origin/$DEV_BRANCH)          # the commit the promote PR will carry
   # Every check run on exactly this commit (not "the newest run on the branch"):
   gh api "repos/$OWNER_REPO/commits/$CANDIDATE/check-runs" --paginate \
     --jq '.check_runs[] | "\(.name)\t\(.status)\t\(.conclusion)"'
   # Which checks are required: branch protection, if readable (404/403 = not readable →
   # the required set is every workflow that runs on a push to $DEV_BRANCH):
   REQUIRED=$(gh api "repos/$OWNER_REPO/branches/$DEV_BRANCH/protection/required_status_checks" \
     --jq '.checks[].context' 2>/dev/null) || REQUIRED=""   # on 404/403 gh prints the error body to stdout
   ```
   Green means: at least one run exists for `CANDIDATE`, **every required check is present** in that
   list, and each is `completed` / `success`. An empty list is "not started", not green. `queued`,
   `in_progress`, `cancelled`, `timed_out` or `skipped` on a required check is not green. A required check that
   never ran because its workflow skips such commits (`paths-ignore`) is not green either — the candidate
   is unverified; say so instead of promoting. A green run
   of an *older* commit proves nothing about this one — after any merge, rebase or conflict
   resolution the candidate SHA changes and this step starts over. Not green → STOP:
   "CI on $CANDIDATE is not green (<check>: <state>). Wait or fix before promoting."
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

> **Scope:** this runs only when `/deps promote` itself created and merged the PR — here the sync-back deliberately pulls back `/deps`'s *own* fresh promote merge commit (so it uses the raw `PROD_AHEAD`, unlike the Step 3 pre-flight, which compares content). If this repo promotes via a different workflow that intentionally skips sync-back (e.g. a project's own prod-release command, leaving prod ahead by merge nodes by design), `/deps promote` is not the promote path and this step does not run — do not retrofit a sync-back onto that workflow.

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

Nothing picks it up later — and nothing needs to. `/deps` status and the Step 3 pre-flight compare content, and a promote merge node adds none (Safety Rule 12). prod simply stays ahead by merge-only commits; the next promote PR works the same either way.

**Inform user:**
"After merging the PR on GitHub, confirm here and I will sync prod back into main. If you skip it, nothing breaks — prod is then ahead only by the merge commit, which is not drift."
