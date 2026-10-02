# `/dev ui [scope]` — Analyse a UI and rework it

A standalone mode, like `/dev check`: it looks at one part of the running product, writes the
findings to `UI-REVIEW.md` in the project root, and changes code only for what the user approves.
Screens follow `companion.md` (UI only; a message ends with the URL only when there is a new screen).

## Precondition

- Phase `[~]`/`[!]` in ROADMAP.md: the rework belongs to it. Run steps 1–4 (read-only), record the
  approved IDs in STATE.md's Current Position (the active phase's entry, `state.md`), stop with
  "Phase N is active — the rework is part of it; continue with `/dev next`". No steps 5–6.
- All phases `[x]`/`[—]`, or no ROADMAP.md: proceed. Uncommitted changes at the start: name them —
  `/dev check` in step 6 snapshots them too; ask whether to commit or set them aside first.

## 1. Scope

- **Argument** (`/dev ui /settings`, `/dev ui src/components/Checkout`, `/dev ui OrderTable`): a
  route, a component name or a folder. Resolve it to `$UI_SCOPE` — the UI files that render it
  plus the stylesheets and components they import — and to the views to screenshot.
- **No argument:** `AskUserQuestion` with up to four real candidates from the project (main routes
  or screens, the most recently changed UI folder first, marked "(Recommended)"). Never review the
  whole app silently.
- **Kind:** `landing` for a marketing page (or `@type: landing`), else `ui`; platform from `$TECH_STACKS`.
- `$UI_SCOPE` is fixed for the run, like `$CHECK_SCOPE` in `dev-check.md`. No UI files → say so
  and ask for another scope; no report.

## 2. Screenshots of the running app

Start the app as the project does and capture every view in scope. **Web:** Playwright at 1440×900
and 390×844, light, and dark via `prefers-color-scheme` if supported. **Native:** simulator shots.

Save into `screen_dir` as `ui-<view>-<viewport>-<theme>.png` — the "before" set. **Show screen**:
"Real screen" (markers come in step 4). App not startable → say why; screenshot-based analyses
report `skipped: app not running`, code-based ones still run.

## 3. Analyses — parallel read-only subagents

Load only the `design/INDEX.md` rows that match the scope — never the whole index, never "all":

| Scope has | INDEX row | Used by |
|---|---|---|
| any view | "4a ui: critique a draft" (`density-critique.md`) | density subagent, on the screenshots |
| platform | "4a/4c platform web / Apple / Android" (one row) | accessibility subagent |
| forms | "4a ui: forms" | density subagent |
| empty/loading/error views | "4a ui: error, empty, loading states" | density subagent |
| visible copy | "4a ui/landing: copy in drafts" | density subagent |
| web UI files | "5c web UI changed" (design detector, `run`) | design-detector subagent |
| animation (motion sweep probes hit) | "5c motion changed" | motion subagent |
| kind `landing` | "4a landing" (taste, `subagent`) | taste subagent |

Dispatch per `analyzers/CONTRACT.md`, **mode `full` limited to `$UI_SCOPE`** (no diff, not the
whole codebase), requirement "the view
serves its primary task for its primary user", `$TECH_STACKS`; model explicitly per "Subagent
Model Choice" in `gate.md` (cheap tier; taste: standard tier):

- **accessibility** — `analyzers/accessibility.md`, plus the platform file named above.
- **design-detector** — `analyzers/design-detector.md` (web only; native: `skipped: not web`).
- **motion** — `analyzers/motion.md`; no sweep hit → `skipped: no animation in scope`.
- **density** — `design/density-critique.md` applied to each screenshot, plus the rows above.
- **taste** (kind `landing` only) — reads the taste file itself and returns findings as notes.

Wait for all (15 minutes, retry once, as in gate step 5c). A missing source under `$DEV_DESIGN_DIR`,
an unbuilt detector or a missing screenshot → that analysis returns `skipped: <reason>`, recorded
as such in `UI-REVIEW.md` — never as "no findings".

## 4. Findings, `UI-REVIEW.md`, decision

Merge and deduplicate (same element, same problem = one finding). Severity:

- **critical** — a user cannot complete the view's task, content is lost or unreadable, or a
  WCAG 2.2 AA violation (e.g. target below 24×24 CSS px, contrast below 4.5:1).
- **major** — the task works but users stumble on the main path: hierarchy, density, missing
  states, broken mobile or dark rendering.
- **minor** — polish: spacing, consistency, copy, motion detail, targets below 44×44 on touch.

Sort by benefit: severity first, then how many users and views it touches, then lowest effort.
Write (or update) `UI-REVIEW.md` in the project root:

```markdown
# UI review — <scope> — YYYY-MM-DD
Kind: ui | landing · Platform: web · Screenshots: desktop/mobile × light/dark

| Analysis | Result |
|---|---|
| accessibility | 2 critical, 3 notes |
| motion | skipped: animation standards not found |

| ID | Severity | Where | Finding | Evidence | Acceptance criterion | Status |
|---|---|---|---|---|---|---|
| UI-1 | critical | src/Cart.tsx:42 | Remove button is 16×16 px | screenshot cart-mobile-light, marker 1; `className="h-4 w-4"` | Target ≥ 24×24 CSS px at 390 px width | open |
```

IDs continue from the existing file, never renumbered; earlier open findings that no longer
reproduce become `gone`. No evidence (file:line, screenshot + marker, detector rule) or no
checkable acceptance criterion → not a finding. Then **Show screen**: "Real screen", markers
numbered by finding ID; the list stays in the terminal.

**Larger interventions** (layout, navigation, several components): 2–3 variants per INDEX row "4a
ui: show variants" as building block "UI decision"; source missing → say `skipped: prototype source
not found` and build them with the plain building block. The user picks via `AskUserQuestion`.

**Approval** — `AskUserQuestion`: "All critical and major (Recommended)", "Critical only", "Pick
by ID", "None — keep the report" (then stop: no code change, no `/dev check`). Nothing changes before.

## 5. Rework

Fix exactly the approved findings, each to its acceptance criterion, inside `$UI_SCOPE` (shared
tokens/components it needs: name them), with the stack skills from `tech-stack-triggers.md`. Status
per finding: `fixed` or `not fixed: <reason>`.

## 6. Verify

1. Retake the same screenshots (same views, viewports, themes) and check each acceptance criterion
   against them; a criterion that does not hold sets the status back to `open`.
2. **Show screen**: building block "Before/After" per changed view, from the two screenshot sets.
3. `/dev check` (`dev-check.md`) over the rework's files, `UI-REVIEW.md` and any pre-existing changes
   kept from the start (name those files). Its commit closes the run; commits not authorized → same
   steps without committing, name the open ones. If it fails, stop as `dev-check.md` says.

End in the terminal: findings fixed / open, skipped analyses, and the gate result.
