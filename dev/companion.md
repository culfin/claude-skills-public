# Screens — procedure and triggers

Read before the first screen of a session. What screens look like is in `companion-screens.md`.

Screens are self-contained HTML pages shown with the host's own tools — no server, no port, no URL —
used **without asking**, a fixed part of the workflow ("Visual Companion" in older texts means this).

### Ground Rule: Screens Show the User Interface — Nothing Else

Screens exist to show the **user interface of the product being built**: how a view looks,
which states it has, how a user moves through it, how it renders on desktop/mobile and light/dark.
Every screen is **visual first** — a mockup, a wireframe or a real screenshot of the running app.
Text on a screen is limited to captions and labels (one or two sentences per block).

**Never on a screen — always in the chat:** roadmaps, phase or milestone overviews, plans,
specs, strategy, approaches and their trade-offs, architecture or data-flow diagrams, gate findings,
review results, lists of decisions, legal reasoning — text that could be written in the chat goes there.

| Content | Medium |
|--------|--------|
| UI layout options, wireframes, mockups of views, forms, cards, dialogs | **Screen** |
| States of a view (empty, loading, error, filled), desktop/mobile, light/dark | **Screen** |
| A user's flow through views (as a row of view mockups, not as a box diagram) | **Screen** |
| Real screenshots of the running app for review or acceptance, before/after of a visual change | **Screen** |
| Roadmap, status, phase/milestone summaries, plans, specs | **Terminal** |
| Architecture approaches, data model, library choice, naming, trade-offs | **Terminal** |
| Gate and review findings, test results | **Terminal** |
| Conceptual questions, confirmations, one-line options | **Terminal** |

**Test before every screen:** would the user understand this better by *seeing the interface* than by
reading it? If the honest answer is "it is text in a nicer box" → terminal.

### Mandatory Triggers in `/dev` — always, automatically

| Step | What is shown | Format |
|---------|-----------------|--------|
| **Interview / brainstorming — question with a UI/UX side** (any phase size) | The options as mockups side by side, with the states of each option; desktop/mobile and light/dark where the project has both. Answer via `AskUserQuestion`, with the options named identically there | Building blocks "UI decision", "State grid", "Responsive/Dark" |
| **Review or acceptance of views with real data** | Screenshots of the running app, annotated with markers where something is wrong | Building block "Real screen" |
| **Visual fix or UI change done** | The view before and after, side by side | Building block "Before/After" |

**When a question has a UI/UX side:** when the answer becomes visible — layout, navigation, a user's flow through views, forms, feedback (error, loading, empty), rendering across sizes and themes. Not: data model, library choice, naming — then no screen, question in the terminal only.

### Show screen — the Procedure

Wherever **"Show screen"** appears in this skill, this is exactly what is meant — automatically, without asking:

1. **Write the fragment** (a building block from `companion-screens.md`, no `<html>`/`<head>`) with the `Write`
   tool into `${TMPDIR:-/tmp}/dev-screens/<repo name>/src/<name>.html` — outside the repo, a new name per
   screen (`<phase>-<what>`, e.g. `12-export-options`). Screenshots go next to it; reference them by file name.
2. **Make the page:** `python3 "$DEV_DIR/scripts/screen-page.py" <fragment>` prints the page path
   (`…/dev-screens/<repo name>/<name>.html`): styles follow the T3 theme, images become absolute paths.
3. **Show it.** With T3's tools: `html_preview` with the page path (console empty; check the phone width
   with `width: 390` and the other theme with `appearance` when the project has them), then `html_render`
   with the same path, `height` = the preview's `contentHeight`, `title` = the screen's heading. Without
   them (another host): name the page's absolute path as the message's last line, to open in a browser.
4. **Ask after it:** a question about the screen comes after the render, via `AskUserQuestion` with the
   option labels exactly as on the screen. Under `t3-team` a task thread's question goes to the project lead,
   who does not see your thread: its text names `Screen: <page path>` (also in a `QUESTION`), and the lead shows
   that page before asking the owner.

A screen shows the state **after** the change, never the one before — it is the confirmation surface.
**Real screens** of the running app come from T3's `preview_*` browser tools (a dev server only through the
project's server action, `runtime.md`), else Playwright; save the shots into the screen's `src/` folder.
Not here: Claude Code Artifacts and `/design` publish to claude.ai (external storage) — only on the user's
explicit word.

---
