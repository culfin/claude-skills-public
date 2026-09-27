# /deps close — Detailed Instructions

Closes superseded or stale Dependabot PRs.

## When to Use

- After `/deps check` identifies duplicate PRs for the same package (e.g., PR #6 has 0.81.0 but PR #25 has 0.82.0)
- To clean up PRs that will never be merged (e.g., permanently red CI)

## Steps

### 1. Detect Superseded PRs

```bash
# List all open Dependabot PRs
gh pr list --author "app/dependabot" --state open --json number,title,headRefName
```

Parse package names and versions from PR titles. Group by package. If multiple PRs exist for the same package, the older version is superseded.

**Example:**
```
PR #6:  @anthropic-ai/sdk 0.80.0 → 0.81.0  (superseded)
PR #25: @anthropic-ai/sdk 0.80.0 → 0.82.0  (current)
→ Close PR #6
```

### 2. Show Findings

```
Superseded PRs (older version, newer PR exists):
  #6  @anthropic-ai/sdk 0.81.0 — superseded by #25 (0.82.0)

Stale PRs (CI persistently red):
  #5  nodemailer 8.0.4 — CI red since {date}
```

### 3. Close with Comment

For each superseded PR:
```bash
gh pr close $PR_NUMBER --comment "Closed: superseded by #$NEWER_PR (newer version). Managed by /deps skill." --delete-branch
```

For stale PRs (only after user confirmation):
```bash
gh pr close $PR_NUMBER --comment "Closed: CI persistently failing. Will retry when Dependabot creates a new PR." --delete-branch
```

### 4. Report

```
Closed:
  #6 @anthropic-ai/sdk 0.81.0 — superseded by #25
  Branches deleted: 1
```
