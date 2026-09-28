# Visual Companion — procedure and triggers

Read before the first screen of a session. What screens look like is in `companion-screens.md`.

The Visual Companion is a browser-based server that renders HTML screens. It is used **without asking and without permission** — it is a fixed part of the workflow, not an optional feature.

### Ground Rule: When Browser, When Terminal?

| Content | Medium |
|--------|--------|
| Roadmap progress, phase overview, milestone summary | **Browser** |
| UI layout options, design decisions, wireframes | **Browser** |
| Architecture diagrams, data flow, component relationships | **Browser** |
| Quality Gate findings dashboard (if ≥ 3 findings) | **Browser** |
| Conceptual yes/no questions ("Resume?", "Continue?") | **Terminal** |
| Technical decisions without a visual dimension | **Terminal** |
| Short answers, confirmations, one-line options | **Terminal** |

**Rule of thumb:** If the content consists of more than 3 lines of structured information or has a spatial representation → browser. Exception: questions without a UI/UX side (data model, library choice, naming) stay in the terminal, even if they are longer.

### Mandatory Triggers in `/dev` — always, automatically

| Step | What is shown | Format |
|---------|-----------------|--------|
| **Session Start** (if ≥ 2 phases or milestone change) | Roadmap progress: milestones as progress bars, current phase highlighted, blockers | Building block "Roadmap" |
| **`/dev status`** | Complete roadmap overview with all milestones, phases, status icons | Building block "Roadmap" (all milestones) |
| **Milestone End Summary** | What was built: phase list with Gate summary highlights, next steps | Building blocks "Roadmap" + "Gate dashboard" |
| **Quality Gate Summary** (if ≥ 3 findings across all checks) | Findings by category: critical/note, what was fixed | Building block "Gate dashboard" |
| **`/dev review` Pre-Release** | Quality overview across all Gate summaries: findings trend, open blockers | Building block "Gate dashboard" (across all phases) |
| **Interview / brainstorming — question with a UI/UX side** (any phase size) | The options as mockups side by side, with the states of each option; desktop/mobile and light/dark where the project has both. Answer via `AskUserQuestion`, with the options named identically there | Building blocks "UI decision", "State grid", "Responsive/Dark" |
| **Brainstorming — solution approaches, architecture phase** | One Mermaid diagram per approach (components/data flow) with pros and cons | Building block "Architecture comparison" |
| **Brainstorming — design, architecture phase** | Before/after as two diagrams side by side | Building block "Before/After" |

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
for it. So: **every message that shows a screen or refers to the companion in any way ends with the
current `url` on its own line** — verbatim, including `?key=<TOKEN>`. Not once per session: every time.

"Refers to the companion" includes: a new or updated screen; "see the browser", "on the screen",
"in the companion"; a question whose options are shown as mockups or diagrams; a gate dashboard, a
waiting screen, a summary shown there; and any subagent or delegated skill (e.g. brainstorming) that
writes a screen — it receives the URL and follows the same rule.

- When a question dialog (`AskUserQuestion`) refers to a screen, the text **before** the call ends
  with the URL — the dialog can cover everything earlier.
- **Current** means from the latest start or restart: after a restart, take the `url` from the new
  return value, not from memory. If the alive check fails and the server cannot be restarted, say so
  instead of repeating a dead link.
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

What a screen looks like — content fragments, style rules, building blocks (Roadmap, Gate dashboard, Waiting, etc.) — is described in `companion-screens.md`.

---
