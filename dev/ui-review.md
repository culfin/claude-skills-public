# `/dev ui [scope]` — Analyse a UI and rework it

Standalone mode like `/dev check`: reviews one part of the running product, writes `UI-REVIEW.md`
(project root), changes code only after approval. Screens per `companion.md` (URL only with a new screen).

## Precondition

- Phase `[~]`/`[!]` in ROADMAP.md: the rework belongs to it. Run steps 1–4 (read-only), record the
  approved IDs in STATE.md's Current Position (the active phase's entry, `state.md`), stop with
  "Phase N is active — the rework is part of it; continue with `/dev next`". No steps 5–6.
- All phases `[x]`/`[—]`, or no ROADMAP.md: proceed. Uncommitted changes at the start: name them —
  `/dev check` in step 6 snapshots them too; ask whether to commit or set them aside first.

## 1. Scope

- **Argument** (`/dev ui /settings`, `/dev ui src/components/Checkout`): a route, component or
  folder. Resolve it to `$UI_SCOPE` — the UI files that render it plus imported stylesheets and
  components — and to the views to screenshot.
- **No argument:** `AskUserQuestion` with up to four real candidates (most recently changed UI area
  first, "(Recommended)"). Never review the whole app silently.
- **Kind:** `landing` for a marketing page (or `@type: landing`), else `ui`; platform from `$TECH_STACKS`.
- `$UI_SCOPE` is fixed for the run (like `$CHECK_SCOPE`). No UI files → ask for another scope; no report.

## 2. Screenshots of the running app

Capture every view in scope. **Web:** prefer build + preview; on a dev
server hide its overlays first (Astro toolbar, Next.js indicator, Vite error overlay) — they are not
the product. Read the port from the server's own start log (the default port may belong to another
project) and check page title and URL before capturing. Playwright at 1440×900 and 390×844, light,
and dark via `prefers-color-scheme` if supported. **Native:** simulator shots. **Sub-states:** with a
forms or states row in scope (step 3), trigger error, success, empty and loading with throwaway
input (never against production) and capture them — else the finding's evidence says "judged from code, not captured".

Save into `screen_dir` as `ui-<view>[-<state>]-<viewport>-<theme>.png` — the "before" set. Capture
all views first, then **Show screen** once: "Real screen" (markers come in step 4). App not
startable → say why; screenshot-based analyses report `skipped: app not running`, the rest still run.

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
| animation (unsure → run `motion.md`'s sweep probes to decide) | "5c motion changed" | motion subagent |
| kind `landing` | "4a landing" (taste, `subagent`) | taste subagent |

Dispatch per `analyzers/CONTRACT.md`, **mode `full` limited to `$UI_SCOPE`** (no diff, not the
whole codebase), requirement "the view serves its primary task for its primary user",
`$TECH_STACKS`; model explicitly per `models.md` (cheap tier; taste: standard tier):

- **accessibility** — `analyzers/accessibility.md`, plus the platform file named above.
- **design-detector** — `analyzers/design-detector.md` (web only; native: `skipped: not web`).
- **motion** — `analyzers/motion.md`; no sweep hit → `skipped: no animation in scope`.
- **density** — `design/density-critique.md` applied to each screenshot, plus the rows above.
- **taste** (kind `landing` only) — reads the taste file itself and returns findings as notes.

Wait for all (15 minutes, retry once, as in gate step 5c). Missing source under `$DEV_DESIGN_DIR`,
unbuilt detector or missing screenshot → `skipped: <reason>` in `UI-REVIEW.md`, never "no findings".

## 4. Findings, `UI-REVIEW.md`, decision

Merge and deduplicate (same element, same problem = one finding). Analyzers report critical/note
(`CONTRACT.md`); map them once, here — guideline-checklist findings follow the same rule:

- **critical** — analyzer critical: the task cannot be completed, content is lost or unreadable.
- **major** — a note that blocks or misleads a user on a main task, or breaks a hard number
  (contrast minimum, target size minimum 24×24 CSS px).
- **minor** — every other note: spacing, consistency, copy, motion detail, targets < 44×44 on touch.

Sort by severity, then reach (users, views), then lowest effort. Write or update `UI-REVIEW.md`:

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

Outside scope: <noticed outside `$UI_SCOPE`, one line each — listed, not offered for rework>
```

IDs continue from the existing file, never renumbered; earlier open findings that no longer
reproduce become `gone`. No evidence or no checkable acceptance criterion → not a finding. Then
**Show screen**: "Real screen", markers numbered by finding ID; the list stays in the terminal.

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

1. Retake the same screenshots and check each acceptance criterion against them; one that does not
   hold goes back to `open`.
2. **Show screen**: building block "Before/After" per changed view, from the two screenshot sets.
3. `/dev check` (`dev-check.md`) over the rework's files, `UI-REVIEW.md` and any pre-existing changes
   kept from the start (name those files). Its commit closes the run; commits not authorized → same
   steps without committing, name the open ones. If it fails, stop as `dev-check.md` says.
4. End in the terminal: findings fixed / open, skipped analyses, and the gate result.
