---
name: bug-prospector-neutral
description: 'Stack-neutrale Fassung von bug-prospector (7 Linsen: Annahmen, Zustandsautomaten, Grenzwerte, Datenlebenszyklus, Fehlerpfade, Zeitabhängigkeit, Plattformunterschiede). Wird von /gate an Subagenten übergeben; direkt nur auf ausdrücklichen Wunsch.'
disable-model-invocation: true
allowed-tools: [Grep, Glob, Read, Write, Bash, AskUserQuestion, Agent]
metadata:
  derived-from: bug-prospector 1.0.0, Herkunft und Lizenz in NOTICE
---

<!-- Angepasste Fassung, siehe NOTICE. -->

# Bug Prospector

> **Quick Ref:** Find bugs that pattern-based scanners miss by analyzing *intent*, not syntax. Output: `.agents/research/YYYY-MM-DD-bug-prospector-*.md`

**YOU MUST EXECUTE THIS WORKFLOW. Do not just describe it.**

**Required output:** Every BUG finding MUST include Urgency, Risk, ROI, and Blast Radius ratings using the Issue Rating Table format. Do not omit these ratings.

**Philosophy:** Auditing tools find what's *syntactically wrong*. Bug Prospector finds what's *semantically fragile* — the gap between "the code compiles" and "the code handles every real-world scenario."

---

## Pre-flight: Git Safety Check

```bash
git status --short
```

If uncommitted changes exist:

```
AskUserQuestion with questions:
[
  {
    "question": "You have uncommitted changes. Commit before proceeding?",
    "header": "Git",
    "options": [
      {"label": "Commit first (Recommended)", "description": "Save current work so you can revert if this skill modifies files"},
      {"label": "Continue without committing", "description": "Proceed — I accept the risk"}
    ],
    "multiSelect": false
  }
]
```

If "Commit first": Ask for a commit message, stage changed files, and commit. Then proceed.

### Freshness

Base all findings on current source code only. Do not read or reference files in `.agents/`, `scratch/`, or prior audit reports. Ignore cached findings from auto-memory or previous sessions. Every finding must come from scanning the actual codebase as it exists now.

---

## Step 1: Choose Scope and Lenses

### 1.1: Determine Scope

```
AskUserQuestion with questions:
[
  {
    "question": "What should I prospect?",
    "header": "Scope",
    "options": [
      {"label": "Specific file or feature", "description": "I'll tell you which file(s) or feature to analyze"},
      {"label": "Recently changed files", "description": "Analyze files changed in the last 5 commits"},
      {"label": "Full codebase", "description": "Broad scan across all source files (slower, more thorough)"}
    ],
    "multiSelect": false
  }
]
```

**If "Specific file or feature":** Ask which file(s) or feature name.

**If "Recently changed files":**
```bash
git diff --name-only HEAD~5 -- "*.ts" "*.tsx" "*.js" "*.svelte" "*.rs" | head -30
```

**If "Full codebase":** Use `Glob pattern="**/*.{ts,tsx,js,svelte,rs}"` to inventory, then prioritize:
1. Business logic (calculation modules, services, stores, API handlers, Rust core)
2. Data layer (persistence, sync, networking)
3. Components with complex state (forms, multi-step flows)
4. Skip: pure layout components, stories, test files, generated code

### 1.2: Choose Lenses

```
AskUserQuestion with questions:
[
  {
    "question": "Which analysis lenses should I apply?",
    "header": "Lenses",
    "options": [
      {"label": "All 7 lenses (Recommended)", "description": "Full prospecting — assumptions, state machines, boundaries, data lifecycle, error paths, time, platform"},
      {"label": "Quick 3", "description": "Assumptions + Error Paths + Boundaries — highest bug yield"},
      {"label": "Let me pick", "description": "I'll choose specific lenses"}
    ],
    "multiSelect": false
  }
]
```

**If "Let me pick":**

```
AskUserQuestion with questions:
[
  {
    "question": "Select the lenses to apply:",
    "header": "Lenses",
    "options": [
      {"label": "1. Assumption Audit", "description": "List every implicit assumption and what breaks when violated"},
      {"label": "2. State Machine Analysis", "description": "Find unreachable states, simultaneous states, interrupted transitions"},
      {"label": "3. Boundary Conditions", "description": "Zero, one, max values; empty strings; null/undefined chains; NaN/Infinity; off-by-one"},
      {"label": "4. Data Lifecycle Tracing", "description": "Follow data from creation to deletion — find gaps"}
    ],
    "multiSelect": true
  },
  {
    "question": "Additional lenses:",
    "header": "More",
    "options": [
      {"label": "5. Error Path Exerciser", "description": "What happens when every try/catch and optional chain fails?"},
      {"label": "6. Time-Dependent Bugs", "description": "Timezone, locale, rapid actions, slow network, first launch after weeks"},
      {"label": "7. Platform Divergence", "description": "Hardware assumptions, OS version gaps, device-specific behavior"}
    ],
    "multiSelect": true
  }
]
```

---

## Step 2: Execute Selected Lenses

For each file in scope, apply the selected lenses. Read the full file before analysis — never analyze from grep matches alone.

### Lens 1: Assumption Audit

**Goal:** Surface every implicit assumption the code makes, then evaluate what happens when each is violated.

**Process:**
1. Read the file completely
2. For every function/computed property, list assumptions such as:
   - "This array will always have at least one element"
   - "This network call will complete before the view disappears"
   - "The environment variable / config value is always set"
   - "This date string will always be in ISO 8601 format"
   - "This dictionary key will always exist"
   - "The parent component always passes a value (prop is never `undefined`)"
   - "This enum will never have new cases added"
3. For each assumption, determine:
   - **How likely is violation?** (Never / Rare / Occasional / Common)
   - **What happens on violation?** (Crash / Silent data loss / Wrong UI / Graceful degradation)
   - **Is there a guard?** (Yes — handled / No — unprotected)
4. Flag as BUG if: likelihood >= Rare AND consequence >= Silent data loss AND no guard

**Search accelerators** (grep for common assumption patterns):
```
Grep pattern="\[0\]|\.at\(0\)" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="[a-zA-Z0-9_)\]]!\." glob="**/*.{ts,tsx}"
Grep pattern=" as [A-Z]" glob="**/*.{ts,tsx,svelte}"
Grep pattern="\.unwrap\(\)|\.expect\(" glob="**/*.rs"
Grep pattern="\.shift\(\)|\.pop\(\)" glob="**/*.{ts,tsx,js,svelte,rs}"
```

### Lens 2: State Machine Analysis

**Goal:** Find states that become unreachable, states that can be simultaneously active, and transitions that leave the app in an inconsistent state.

**Process:**
1. Identify all state that represents user-facing status (`useState`, Svelte `$state`/stores, reducers, Rust state enums)
2. Map the state transitions:
   - Draw the state graph: which states lead to which?
   - Can any state become a dead end? (entered but never exited)
   - Can two mutually exclusive states be true simultaneously?
3. Check interruption resilience:
   - What happens if the user backgrounds the app mid-transition?
   - What happens if a sheet is dismissed during an async operation?
   - What happens if the component unmounts before an async operation completes?
4. Check reset paths:
   - After an error, does state reset to a usable starting point?
   - After cancellation, are all intermediate states cleaned up?

**Search accelerators:**
```
Grep pattern="useState\(true\)|\$state\(true\)|writable\(true\)" glob="**/*.{ts,tsx,svelte}"
Grep pattern="isLoading|isProcessing|isSaving|isAnalyzing|pending" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="showError|showAlert|isOpen|open=" glob="**/*.{ts,tsx,svelte}"
Grep pattern="enum .*State|type .*State =" glob="**/*.{ts,tsx,js,svelte,rs}"
```

### Lens 3: Boundary Conditions

**Goal:** Find off-by-one errors, empty collection crashes, and edge case failures.

**Process:**
1. For every conditional (`if`, `switch`/`match`, early returns), evaluate:
   - **Zero:** What happens with 0 items, empty string, `null`/`undefined`, `NaN`?
   - **One:** What happens with exactly 1 item? (Singular/plural, first==last)
   - **Maximum:** What happens at Int.max, massive arrays, very long strings?
   - **Negative:** What happens with negative numbers where unsigned is expected?
2. For every array/collection access:
   - Is the index bounds-checked?
   - Does `shift()` / `pop()` / `[0]` / `.first().unwrap()` have an emptiness guard?
   - Does `prefix()` / `suffix()` handle count > array.count?
3. For every string operation:
   - Does it handle empty strings?
   - Does it handle Unicode (emoji, RTL, combining characters)?
   - Does it handle strings with special characters (quotes, backslashes)?

**Search accelerators:**
```
Grep pattern="\.length\s*-\s*1|\.len\(\)\s*-\s*1" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="\.slice\(|\.substring\(|\[\.\." glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="\.split\(" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="parseFloat|parseInt|Number\(|isNaN|Infinity|/ 0" glob="**/*.{ts,tsx,js}"
Grep pattern="MAX_SAFE_INTEGER|i32::MAX|u32::MAX|as u|as i" glob="**/*.{ts,tsx,js,svelte,rs}"
```

### Lens 4: Data Lifecycle Tracing

**Goal:** Follow data from creation to deletion and find gaps where data can be lost, duplicated, or become stale.

**Process:**
1. Pick the primary data entities (models, cached values, user input)
2. For each entity, trace:
   - **Creation:** Where is it created? What validations exist at creation time?
   - **Modification:** Where is it modified? Can modifications conflict? Are changes persisted immediately or batched?
   - **Persistence:** Where is it saved? Can the save fail silently? Is there a race between saves?
   - **Display:** Where is it displayed? Can stale data be shown after a background update?
   - **Deletion:** Where is it deleted? Are all references cleaned up? Are related entities cascaded?
   - **Sync:** If synced, what happens on conflict? Is there a "last write wins" that could lose data?
3. Flag gaps:
   - Created but never persisted (in-memory only, lost on crash)
   - Modified but UI not updated (stale display)
   - Deleted but references remain (dangling pointers, orphaned data)
   - Synced but no conflict resolution

**Search accelerators:**
```
Grep pattern="\.insert\(|INSERT INTO" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="\.delete\(|DELETE FROM" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="localStorage\.|sessionStorage\.|indexedDB" glob="**/*.{ts,tsx,svelte}"
Grep pattern="ON DELETE|onDelete|cascade" glob="**/*.{ts,sql,rs}"
Grep pattern="useQuery|createQuery|revalidate|invalidate" glob="**/*.{ts,tsx,svelte}"
```

### Lens 5: Error Path Exerciser

**Goal:** For every try/catch, async/await, and optional chain — determine what happens when the error path is taken.

**Process:**
1. Find all error-producing code:
   - `try`/`catch`, `?` operator (Rust), `.unwrap()`/`.expect()`
   - `await` (rejects on network failure, abort or timeout)
   - Optional chaining (`?.`)
   - `if (!x) return` / `let Some(x) = … else { return }`
2. For each error path, evaluate:
   - **Does the UI reflect the error?** Or does it show a loading state forever?
   - **Is the app left in a consistent state?** Or is it half-modified?
   - **Can the user retry?** Or are they stuck?
   - **Is the error logged?** Or silently swallowed?
3. Specifically check for:
   - `catch {}` / `.catch(() => null)` / `.ok()` / `unwrap_or_default()` that turn a meaningful error into nothing (information loss)
   - `catch` blocks that log but don't update UI state
   - Missing `isLoading = false` in error paths (loading state trap; use `finally`)
   - Early `return` in an `if (!x)` guard that silently aborts a user-initiated action
   - Promises without `await` or `.catch` (floating promises), `tokio::spawn` without joining (errors vanish)

**Search accelerators:**
```
Grep pattern="catch\s*(\(\w*\))?\s*\{\s*\}|\.catch\(\(\)\s*=>" glob="**/*.{ts,tsx,js,svelte}"
Grep pattern="catch\s*(\(\w*\))?\s*\{" glob="**/*.{ts,tsx,js,svelte}" -A 3
Grep pattern="\.ok\(\)|unwrap_or_default\(\)|let _ =" glob="**/*.rs"
Grep pattern="tokio::spawn|spawn\(" glob="**/*.rs" -A 5
```

### Lens 6: Time-Dependent Bugs

**Goal:** Find code that behaves differently based on time, speed, or duration.

**Process:**
1. **Timezone and locale:**
   - Date formatting without explicit time zone (`toLocaleString` without `timeZone`, `new Date(string)` parsing)
   - Date comparisons using `<` instead of Calendar methods
   - String-to-date parsing that assumes a specific locale
   - Display of dates without considering user's locale
2. **Duration since last use:**
   - Cached data that expires but has no expiry check
   - Tokens/sessions that timeout but the app doesn't re-authenticate
   - "First launch" flags that don't account for app updates
3. **Rapid repeated actions:**
   - Buttons without debouncing that trigger duplicate network calls
   - Double-tap on save that creates duplicate records
   - Rapid navigation that crashes due to concurrent presentations
4. **Slow or absent network:**
   - Operations that assume network availability
   - Missing timeout on network requests
   - No offline fallback for features that need data
   - Optimistic UI that doesn't roll back on failure

**Search accelerators:**
```
Grep pattern="new Date\(|Date\.now\(|chrono::|SystemTime::now" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="toLocale(Date|Time)?String\(|Intl\.DateTimeFormat\(" glob="**/*.{ts,tsx,svelte}"
Grep pattern="fetch\(|axios|reqwest::" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="AbortController|timeout" glob="**/*.{ts,tsx,js,svelte,rs}"
Grep pattern="debounce|throttle|setTimeout\(" glob="**/*.{ts,tsx,svelte}"
```

### Lens 7: Platform Divergence

**Goal:** Find code that assumes one runtime, OS, or rendering engine and silently breaks on another.

**Process:**
1. **Runtime boundaries:**
   - Code that runs on the server and in the browser (Next.js Server/Client Components, SSR) but touches `window`, `document`, `localStorage` without a guard
   - Build-flag splits (e.g. `NEXT_PUBLIC_BUILD_TARGET`) where one branch is clearly less tested
   - Node-only APIs (`fs`, `path`, `process`) reachable from client bundles
2. **Webview and browser engines:**
   - CSS or APIs that only Chromium supports, used in a Tauri app that runs WKWebView on macOS and WebView2 on Windows (e.g. `-webkit-app-region`)
   - Missing permissions in Tauri capability files for APIs the frontend calls (a call that the ACL rejects looks like a UI bug)
3. **Operating system differences:**
   - Path separators, case-insensitive file systems, line endings
   - `#[cfg(target_os = ...)]` / `process.platform` branches where the other branch is incomplete
4. **Device and viewport:**
   - Hard-coded widths, missing responsive layout, touch vs pointer assumptions
   - Memory-heavy work (image analysis, large canvases) without limits

**Search accelerators:**
```
Grep pattern="typeof window|window\.|document\.|localStorage" glob="**/*.{ts,tsx,svelte}"
Grep pattern="NEXT_PUBLIC_BUILD_TARGET|process\.platform" glob="**/*.{ts,tsx,js,mjs}"
Grep pattern="cfg\(target_os" glob="**/*.rs"
Grep pattern="-webkit-app-region|::-webkit-" glob="**/*.{css,scss,svelte,tsx}"
Grep pattern="\"permissions\"" glob="**/capabilities/*.json"
```

---

## Step 3: Verification Rule

Before classifying ANY finding:

1. **Read the flagged file** — at minimum 30 lines around the issue
2. **Check for existing guards** — the assumption may already be protected
3. **Check for intentional design** — comments, documentation, or clear architectural decisions
4. **Check if it's actually reachable** — dead code or unreachable paths are not bugs
5. **Assess real-world likelihood** — theoretical issues in impossible scenarios are not bugs
6. **Count blast radius** — grep for callers/references of the affected function or property to determine how many files the fix would touch
7. **Classify** as:
   - **BUG:** Real risk, no guard, realistic scenario
   - **FRAGILE:** Works now but will break under foreseeable conditions
   - **OK:** Already guarded or intentional design
   - **REVIEW:** Unclear, needs human judgment

**Classification rules:**
- A finding is NOT a bug if the code already handles the case (even if the handling is in a different function)
- A finding is NOT a bug if the scenario requires conditions that the app's architecture prevents
- A finding IS a bug if a real user could trigger it through normal usage
- A finding is FRAGILE if it works today but depends on an assumption that could change

---

## Step 4: Generate Report

### 4.1: Check Terminal Width

Before rendering the report, check terminal width:

```bash
tput cols
```

- **160+ columns:** Use the **full 8-column table** inline and in the report file.
- **Under 160 columns:** Use the **compact 4-column table** inline, write the **full 8-column table** to the report file only. Display this notice after the inline table:

> **Compact view** — your terminal is [N] columns wide (160+ needed for full table). The complete Issue Rating Table with all 8 columns has been written to `.agents/research/YYYY-MM-DD-bug-prospector-<scope>.md`. Open that file or widen your terminal to 160+ columns to view it as a single table.

### 4.2: Render Report

**Display the summary and findings inline**, then write to `.agents/research/YYYY-MM-DD-bug-prospector-<scope>.md`.

The **report file** always uses the full 8-column table regardless of terminal width.

```markdown
# Bug Prospector Report: [Scope Description]

**Date:** YYYY-MM-DD
**Scope:** [Files/features analyzed]
**Lenses Applied:** [List of lenses used]
**Files Analyzed:** N

## Summary

| Status | Count |
|--------|-------|
| Bugs Found | X |
| Fragile Code | Y |
| OK (Already Guarded) | Z |
| Needs Review | W |

## Issue Rating Table

All BUG and FRAGILE findings rated and sorted by Urgency then ROI:
```

**Full table (160+ columns) — used inline AND in report file:**

| # | Finding | Lens | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort |
|---|---------|------|---------|-----------|-------------|-----|-------------|------------|
| 1 | format.ts:45 — array accessed without bounds check | Boundary | 🔴 Critical | ⚪ Low | 🔴 Critical | 🟠 Excellent | ⚪ 1 file | Trivial |
| 2 | useCalculation.ts:89 — isLoading never reset on error | Error Path | 🟡 High | ⚪ Low | 🟡 High | 🟠 Excellent | ⚪ 1 file | Trivial |
| 3 | export.ts:200 — date formatted without time zone | Time | 🟢 Medium | ⚪ Low | 🟢 Medium | 🟢 Good | 🟢 3 files | Small |

**Compact table (under 160 columns) — used inline only:**

| # | Finding | Urgency | Fix Effort |
|---|---------|---------|------------|
| 1 | format.ts:45 — array accessed without bounds check | 🔴 Critical | Trivial |
| 2 | useCalculation.ts:89 — isLoading never reset on error | 🟡 High | Trivial |
| 3 | export.ts:200 — date formatted without time zone | 🟢 Medium | Small |

The compact table keeps the two most actionable columns (Urgency + Fix Effort). Full ratings are in the report file.

```markdown
Use the Issue Rating scale:
- **Urgency:** 🔴 CRITICAL (crash/data loss) · 🟡 HIGH (incorrect behavior) · 🟢 MEDIUM (degraded UX) · ⚪ LOW (cosmetic/minor)
- **Risk: Fix:** Risk of the fix introducing regressions (⚪ Low for isolated changes, 🟡 High for shared code paths)
- **Risk: No Fix:** User-facing consequence if left unfixed
- **ROI:** 🟠 Excellent · 🟢 Good · 🟡 Marginal · 🔴 Poor
- **Blast Radius:** Number of files the fix touches (e.g., "⚪ 1 file", "🟢 3 files", "🟡 12 files"). Count by grepping for callers/references before rating.
- **Fix Effort:** Trivial / Small / Medium / Large
```

## Detailed Findings

### 1. [File:Line] — [Brief Description]
**Lens:** [Which lens found this]
**Assumption:** [What the code assumes]
**Violation scenario:** [How a real user triggers this]
**Consequence:** [What happens — crash, data loss, wrong UI, etc.]

**Current code:**
```ts
// problematic code
```

**Suggested fix:**
```ts
// corrected code
```

### 2. [File:Line] — [Brief Description]
...

## Fragile Code (Works Now, May Break Later)

### F1. [File:Line] — [Brief Description]
**Lens:** [Which lens found this]
**Current behavior:** [What happens now]
**Breaking scenario:** [What foreseeable change would break this]
**Recommendation:** [How to harden it]

## Already Guarded (Reference)
These were flagged by search but are correctly handled:
- file.ts:123 — [why it's OK]

## Needs Human Review
These findings require domain knowledge to classify:
- file.ts:456 — [what's unclear and why]
```

---

## Step 5: Follow-up

```
AskUserQuestion with questions:
[
  {
    "question": "How would you like to proceed?",
    "header": "Next",
    "options": [
      {"label": "Fix all bugs now", "description": "Walk through each BUG finding and apply fixes (phase-by-phase)"},
      {"label": "Fix selected bugs", "description": "I'll choose which ones to fix"},
      {"label": "Create implementation plan", "description": "Generate a phased plan from the findings"},
      {"label": "Report is sufficient", "description": "I'll handle fixes manually"}
    ],
    "multiSelect": false
  }
]
```

If creating plan: Group findings by file proximity and dependency, order by urgency, output as a numbered plan.

### Fix Workflow: "Fix all bugs now"

Group bugs into phases by file proximity and dependency (as in the report's Implementation Plan). Before each phase, prompt with a **phase gate** — one question, always includes opt-out:

```
AskUserQuestion with questions:
[
  {
    "question": "Phase N: [Phase name] ([count] fixes — [key files]). Proceed?",
    "header": "Phase N",
    "options": [
      {"label": "Proceed (Recommended)", "description": "Implement this phase now"},
      {"label": "Proceed — skip remaining phase gates", "description": "Batch mode: implement all remaining phases without prompting"},
      {"label": "Let's chat about this phase", "description": "Discuss before deciding"},
      {"label": "Stop here", "description": "Skip remaining phases"}
    ],
    "multiSelect": false
  }
]
```

**Every phase gets this same prompt** (including the opt-out) until the user either completes all phases or opts out.

**Rules:**
- If user chooses "skip remaining phase gates": execute all remaining phases without prompting
- If user chooses "Let's chat": wait for user input, answer questions, then re-prompt the same phase gate
- If user chooses "Stop here": stop fixing and report what was completed
- Always build both platforms after each phase to verify

### Fix Workflow: "Fix selected bugs"

Present the bug list for selection:

```
AskUserQuestion with questions:
[
  {
    "question": "Which bugs should I fix? (Reference the Issue Rating Table above)",
    "header": "Select",
    "options": [
      {"label": "Bug 1 — [brief description]", "description": "[Urgency] [Fix Effort]"},
      {"label": "Bug 2 — [brief description]", "description": "[Urgency] [Fix Effort]"},
      {"label": "Bug 3 — [brief description]", "description": "[Urgency] [Fix Effort]"}
    ],
    "multiSelect": true
  }
]
```

After selection, one confirmation prompt with opt-out:

```
AskUserQuestion with questions:
[
  {
    "question": "Fix [N] selected bugs: [brief list]. Proceed?",
    "header": "Confirm",
    "options": [
      {"label": "Proceed (Recommended)", "description": "Fix all selected bugs now"},
      {"label": "Let's chat first", "description": "Discuss specific bugs before fixing"},
      {"label": "Go back", "description": "Re-select bugs"}
    ],
    "multiSelect": false
  }
]
```

Then fix all selected bugs without per-bug prompting — the selection itself was the decision.

**If user chooses "Let's chat":** Answer questions, then re-prompt the confirmation.

---

## Lens Selection Guide

| Situation | Recommended Lenses |
|-----------|--------------------|
| Pre-release audit | All 7 |
| After adding a new feature | 1 (Assumptions) + 2 (State) + 5 (Errors) |
| After a crash report | 3 (Boundaries) + 5 (Errors) + 7 (Platform) |
| Debugging intermittent failures | 2 (State) + 6 (Time) |
| New platform support (macOS/iPad) | 7 (Platform) + 3 (Boundaries) |
| Data model changes | 4 (Data Lifecycle) + 1 (Assumptions) |
| Performance investigation | 3 (Boundaries) + 6 (Time) |

---

## What This Finds vs. What Auditors Find

| Auditors Find | Bug Prospector Finds |
|---------------|---------------------|
| Floating promises | State machine deadlocks |
| Force unwraps | Assumptions that hold today but break tomorrow |
| Retain cycles | Data that's created but never cleaned up |
| Unhandled promise rejection | Error paths that leave UI in loading state |
| Deprecated API usage | Code that works on Apple Silicon but fails on Intel |
| Missing accessibility labels | Rapid-tap scenarios that create duplicate data |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Too many findings | Narrow scope to specific files or use "Quick 3" lenses |
| All findings are theoretical | Increase the realism threshold — only flag scenarios a real user could trigger |
| Overlapping with auditor findings | Focus on *why* not *what* — auditors find the pattern, prospector finds the consequence |
| File too complex to analyze | Split analysis by MARK sections or extract to Agent subprocesses |
| Can't determine if guarded | Classify as REVIEW, not BUG — let the human decide |
