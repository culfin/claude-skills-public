# STATE.md — what it holds and when it changes

Read on every `/dev` run that writes STATE.md.

STATE.md is the project's persistent state file. It tracks progress, requirements, constraints, risks, and session continuity across conversations.

### When to Read STATE.md

- **Every `/dev` and `/dev next` invocation** — read before showing summary
- **`/dev status`** — use STATE.md data for the status display
- **Session start** (when ROADMAP.md exists) — read STATE.md for context

### When to Update STATE.md

| Event | What to Update |
|-------|---------------|
| Phase starts (`[ ]` → `[~]`) | Current Position, Last activity |
| Phase enters gate (`[~]` → `[!]`) | Current Position, Last activity, **create Quality Gate Checklist section** |
| Gate step completes | Check off item in Gate Checklist |
| Gate summary written (5i) | **Append Gate summary** under `### Gate summary — Phase N` in STATE.md (permanent — never removed) |
| `/dev check` completed (5i) | **Append Check summary** under `## Context` in STATE.md (permanent — never removed) |
| Phase completes (`[!]` → `[x]`) | Current Position, Progress table, Last activity, **remove Quality Gate Checklist section** |
| Phase skipped (`[ ]` → `[—]`) | Current Position, Progress table, Last activity |
| Milestone completes | Progress table, Next milestone in Current Position |
| `/dev ui` approval while a phase is `[~]`/`[!]` | **Create or extend `## UI review — approved findings`** (below) |
| Key decision made | Add to Constraints or a Decisions section |
| Blocker discovered | Add to Blockers & Risks |
| Blocker resolved | Remove from Blockers & Risks |
| Session ends (user pauses) | Session Continuity: Last session, Stopped at, Resume hint |
| `/dev init` | Create fresh STATE.md |

### Update Rules

- **Current Position**: OVERWRITE on every phase transition
- **Progress table**: OVERWRITE milestone row when phase count changes
- **Blockers & Risks**: APPEND new, REMOVE resolved
- **Session Continuity**: OVERWRITE on every session pause/end
- **Constraints / Core Value**: IMMUTABLE after init (unless user explicitly changes)

### UI review — approved findings

`/dev ui` run during an active phase only analyses and asks (`ui-review.md`); the approved rework
belongs to that phase. So the approval is not lost, it is stored in its own section — not in
Current Position, which is overwritten on every phase transition:

```markdown
## UI review — approved findings
<!-- from /dev ui <scope>, YYYY-MM-DD; details and acceptance criteria in UI-REVIEW.md -->
- UI-1
- UI-4
```

- **Written by** `/dev ui`: APPEND the approved IDs (a later run adds to the list, never replaces it).
- **Read by** the active phase on resume (`SKILL.md`, Resume logic): each ID is fixed to its
  acceptance criterion in `UI-REVIEW.md` as part of the phase — in 4c, or before the gate continues
  if the phase is already `[!]` (the rework is a code change, so touched gate checks reopen).
- **Cleared:** remove an ID once its status in `UI-REVIEW.md` is `fixed` or `not fixed: <reason>`;
  remove the section when it is empty. A phase does not become `[x]` while the section still lists
  an ID — it is gone, with the gate checklist, by phase completion at the latest.

### STATE.md is NOT for

- Detailed plan contents (those go in spec/plan files)
- Code-level decisions (those belong in CLAUDE.md or code comments)
- Debug state (that goes in `.debug/` files)
- Performance metrics or velocity tracking (unnecessary overhead)

**Exception: Gate summaries** — these stay in STATE.md permanently. They are not temporary state but a quality knowledge log. Each Gate summary under `### Gate summary — Phase N` is NOT removed on phase completion. Only the `## Quality Gate — Phase N` checklist section is removed. The same applies to **Check summaries** (created by `/dev check`) — these too are kept permanently under `## Context` and are never removed.

---
