# Visual Companion — procedure and triggers

Read before the first screen of a session. What screens look like is in `companion-screens.md`.

The Visual Companion is a browser-based server that renders HTML screens. It is used **without asking and without permission** — it is a fixed part of the workflow, not an optional feature.

### Ground Rule: The Companion Shows the User Interface — Nothing Else

The companion exists to show the **user interface of the product being built**: how a view looks,
which states it has, how a user moves through it, how it renders on desktop/mobile and light/dark.
Every screen is **visual first** — a mockup, a wireframe or a real screenshot of the running app.
Text on a screen is limited to captions and labels (one or two sentences per block).

**Never in the companion — always in the terminal:** roadmaps, phase or milestone overviews, plans,
specs, strategy, approaches and their trade-offs, architecture or data-flow diagrams, gate findings,
review results, lists of decisions, legal reasoning. If a screen would mostly be text that could just
as well be written in the chat, it does not belong in the companion — write it in the chat.

| Content | Medium |
|--------|--------|
| UI layout options, wireframes, mockups of views, forms, cards, dialogs | **Browser** |
| States of a view (empty, loading, error, filled), desktop/mobile, light/dark | **Browser** |
| A user's flow through views (as a row of view mockups, not as a box diagram) | **Browser** |
| Real screenshots of the running app for review or acceptance, before/after of a visual change | **Browser** |
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

Everything else that earlier went to the browser (roadmap at session start, `/dev status`, milestone
summary, gate and review dashboards, architecture comparisons) is shown **in the terminal only**.

**When a question has a UI/UX side:** when the answer becomes visible — layout, navigation, a user's flow through views, forms, feedback (error, loading, empty), rendering across sizes and themes. Not: data model, library choice, naming — then no screen, question in the terminal only.

**Look of the screens:** Style rules and ready-made building blocks are in `companion-screens.md` (in this skill directory).

### How the Server Is Started

```bash
# Start server (automatically, without asking) — via the /dev wrapper.
# The wrapper resolves the newest installed superpowers companion and sets
# the display host itself: if DEV_COMPANION_URL_HOST is set (e.g. a Tailscale name),
# the server listens on all interfaces and reports that host, otherwise localhost.
$DEV_DIR/scripts/companion.sh --project-dir <project-root>
# Returns JSON, including:
#   "url":        http://<host>:PORT/?key=<TOKEN>  ← MUST be used verbatim
#   "screen_dir": <session>/content  ← write HTML screens here
#   "state_dir":  <session>/state    ← alive check (server-info / server-stopped)
```

- Store the returned `url` **verbatim** (incl. `?key=<TOKEN>`), as well as `screen_dir` (content dir for HTML screens) and `state_dir` (for the alive check) for the session. `session_dir` = parent directory of `state_dir`/`screen_dir` (for stopping)
- Give the user the `url` **exactly** as it was returned — never reconstruct it, never drop the token, never substitute a different host
- The server stays active for the entire `/dev` session — do not restart it at every step (auto-exit only after 4 h idle, `idle_timeout_ms` in the return value)
- **Alive check** before every HTML write: `<state_dir>/server-info` exists **and** `<state_dir>/server-stopped` is absent; otherwise restart with the **same** `--project-dir` (same port — the open browser tab reconnects by itself, no new URL needed)
- **Protocol details** (how a screen is written/updated) see superpowers `brainstorming/visual-companion.md` — that guide, versioned with superpowers, is authoritative; `/dev` only keeps its trigger table; look and building blocks are in `companion-screens.md`

### The URL Travels With Every Mention

The link from the first start scrolls away within minutes; the user must never have to search
for it. So: **as long as a companion server is running in the session, every message to the user
ends with its current `url` on its own line** — verbatim, including `?key=<TOKEN>`. Not only
messages that show or mention a screen: every message, until the server is stopped.

This also binds every subagent or delegated skill (e.g. brainstorming) that writes a screen — it
receives the URL and follows the same rule.

- When a question dialog (`AskUserQuestion`) refers to a screen, the text **before** the call ends
  with the URL — the dialog can cover everything earlier.
- **Current** means from the latest start or restart: after a restart, take the `url` from the new
  return value, not from memory. If the alive check fails and the server cannot be restarted, say so
  instead of repeating a dead link.
- **Alive check before every message that carries the URL**, not only before writing a screen: the
  server stops itself after its idle timeout (`idle_timeout_ms`, 4 h), and a dead link in every
  message is worse than none. If it stopped: restart with the same `--project-dir`.
- **A restart creates a new, empty `screen_dir`.** The page then stays blank although the server
  runs. After every restart, copy the current screen (and the images it references) from the old
  session's `content/` into the new `screen_dir` before sharing the URL, and verify it renders
  (headless Chrome `--dump-dom`, look for a heading of the screen).
- Where the host has a convention for links (e.g. "URLs last"), the URL line is the last line of
  the message.

### Show screen — the Procedure

All mandatory triggers above use the same sequence. Wherever **"Show screen"** appears in this skill, this is
exactly what is meant — automatically, without asking:

1. **Ensure the server** — alive check; if not active, start `companion.sh --project-dir <project-root>`
   (same `--project-dir` → same port, an open tab reconnects by itself).
2. **Write the HTML screen** — content fragment with the `Write` tool into `screen_dir`.
3. **Share the `url` verbatim** — exactly as returned, including `?key=<TOKEN>`, on its own line at
   the end of the message; again in every later message that refers to the screen (see "The URL
   Travels With Every Mention"). **Never reconstruct it, never substitute a different host.**

The screen is the confirmation surface: from it the user immediately sees whether the state is right.
That is why it always shows the state **after** the change, never the one before.

What a screen looks like — content fragments, style rules, building blocks (UI decision, State grid, Real screen, Before/After, Waiting, etc.) — is described in `companion-screens.md`.

---
