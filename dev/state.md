# STATE.md — what it holds and when it changes

Read on every `/dev` run that writes STATE.md — the project's persistent state across sessions
(progress, requirements, constraints, risks, continuity). Every `/dev` run and `/dev status` reads it.

### When to Update STATE.md

| Event | What to Update |
|-------|---------------|
| Bundled clarification at run start (`befragung.md`) | Answers under each phase as `Decisions:` (below) |
| Phase starts (`[ ]` → `[~]`) | Current Position, Last activity |
| Small phase clarified (`SKILL.md` 4a) | `Acceptance criteria:` under the phase (below) — no approval round |
| Phase enters gate (`[~]` → `[!]`) | Current Position, Last activity, **create Quality Gate Checklist section** |
| Gate step completes | Check off item in Gate Checklist |
| Gate summary written | **Append Gate summary** under `### Gate summary — Phase N` in STATE.md (permanent — never removed) |
| Gate commit, CI watcher started | Line `- <sha> — Phase N <name>: pending` under `## CI in background`; replace `pending` with the status file's line whenever it is read (`gate.md`, "CI in background") |
| `/dev check` completed | **Append Check summary** under `## Context` in STATE.md (permanent — never removed) |
| Phase completes (`[!]` → `[x]`) | Current Position, Progress table, Last activity, **remove Quality Gate Checklist section**, **replace the Handoff block** (below) |
| Phase skipped (`[ ]` → `[—]`) | Current Position, Progress table, Last activity |
| Milestone completes | Progress table, Next milestone in Current Position |
| `/dev ui` approval while a phase is `[~]`/`[!]` | **Create or extend `## UI review — approved findings`** (below) |
| Key decision made | Phase-specific → `Decisions:` under the phase; otherwise Constraints or a Decisions section |
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
- **Handoff**: OVERWRITE on every phase completion
- **CI in background**: APPEND per gate commit, update the status in place; at Milestone End, once
  every line is green (or `none`, noted in its gate summary), remove the lines of that milestone

### Run blocks

After `/clear` the next session knows only STATE.md; three blocks carry the run:

```markdown
## Handoff
<!-- replaced at every phase completion; at most 8 lines; a restart works from files alone: commits done, Next, Open; approvals are only those recorded in STATE.md/ROADMAP.md -->
Next: Phase 5 — Export (@type:backend), plan docs/plans/export.md, tasks 1–2 done (ledger)
Open: Similar-bugs twin in src/report.ts parked (Blockers & Risks)
Traps: tests need `DATABASE_URL` from .env.test; the build writes to dist/ — not in parallel

## CI in background
- 3f9c2a1 — Phase 4 Connections View: green 1234567
- 8e01b7d — Phase 5 Export: pending

## Phases
### Phase 6: Filters
Decisions: date range defaults to 30 days; filters persist per user (bundled round, YYYY-MM-DD)
Acceptance criteria:
- [ ] Filter by status and date range; empty result shows the empty state
- [ ] Filters survive a reload
Criteria complete.
```

- **Handoff** — what the next phase needs and the context does not keep: next phase and where it
  stands, open notes, traps found on the way. At most 8 lines; details belong in the spec, the plan
  or Blockers & Risks.
- **Decisions:** — answers from the bundled round and from later clarification, one line per phase;
  a phase with decisions does not ask them again. **Acceptance criteria:** — the draft of a small
  phase, the requirement the Spec checker and E2E read; the last line `Criteria complete.` marks the
draft as finished — without it, a resume goes back to clarification instead of execution. Both stay until the phase is `[x]`, then the
  phase's entry is removed; its gate summary, a separate entry, keeps the result.

### UI review — approved findings

`/dev ui` during an active phase only analyses and asks (`ui-review.md`); the approved rework belongs
to that phase and is stored in its own section (Current Position is overwritten):

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

**Not for:** plan details (spec/plan files), code-level decisions (CLAUDE.md or comments), debug state
(`.debug/`), velocity metrics. **Gate and Check summaries are permanent** — a quality log; only the
`## Quality Gate — Phase N` checklist is removed.

---
