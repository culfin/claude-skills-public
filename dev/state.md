# State — the phase file and the shared STATE.md

Read before writing a phase file or STATE.md. Each step says what it writes; this file holds the formats.

**1 phase = 1 branch = 1 file `.dev/phase-<N>.md`** next to ROADMAP.md (`<N>` verbatim from
ROADMAP.md: 3, 6a, 4.1). Created at the claim, committed with the phase (never git-ignored),
deleted at phase completion. Only the branch that claims the phase writes it, so
parallel sessions never edit the same lines. After `/clear` the position comes from here alone.

## Phase file

```markdown
Branch: phase-6-filters
## Position
Gate, first open item "Spec checker" — next: dispatch the review wave (YYYY-MM-DD)
Phase base: 8e01b7d
Decisions: date range defaults to 30 days; filters persist per user (bundled round, YYYY-MM-DD)
Acceptance criteria:
- [ ] Filter by status and date range; empty result shows the empty state
- [ ] Filters survive a reload
Criteria complete.

## Quality Gate — Phase 6: Filters
<!-- checklist per gate.md, "Gate Checklist" -->

## CI
- 3f9c2a1: green 1234567

## Handoff
Stopped YYYY-MM-DD: gate Step D, build red in src/filter.ts (cause found, no fix dispatched yet)
Next: Step B fix dispatch with the build error, then Step D again

## Minor (deferred)
- Task 2: date parser accepts `2026-13-01` without an error
```

- **Branch:** line 1, the only line that changes hands: a takeover (new workspace, new branch)
  replaces it in its claim commit.
- **Position:** one line — step, next action, date; every step overwrites it. Progress is never
  stored: it is counted from ROADMAP.md.
- **Phase base:** `git rev-parse HEAD` at the claim; the gate diffs against it.
- **Decisions:** answers from the bundled round and later clarification, never asked again. **Acceptance criteria:** the draft of a small phase, the requirement the Spec
  checker and E2E read; the last line `Criteria complete.` marks it finished (`SKILL.md`, Resume logic).
- **Quality Gate:** the checklist `check-evidence.py check` reads when called without a file.
- **CI:** one line per gate commit, status updated in place (`gate.md`, "CI in background").
- **Handoff:** written at pause and interruption, at most 8 lines — where it stopped, Next, Open,
  Traps. Approvals are only those recorded in the phase file or ROADMAP.md.
- **Minor (deferred):** minor task findings, non-critical gate findings, parked twins and traps later
  phases need; phase completion copies them to STATE.md Blockers & Risks.
- **`## UI review — approved findings`:** `/dev ui` during the phase appends the approved IDs
  (`- UI-1`, details in `UI-REVIEW.md`), never replacing the list. Each ID is fixed to its criterion
  in 4c, or before the gate goes on if the phase is `[!]` (a code change: touched gate checks
  reopen). An ID leaves once `UI-REVIEW.md` says `fixed` or `not fixed: <reason>`; the phase does not
  become `[x]` while one is listed.

## Gate records — `docs/gates/`

Permanent, one path per record:

- `docs/gates/phase-<N>.md` — `## Gate summary — Phase N: <Name>` (`gate.md`) and, from phase
  completion on, its `## CI` lines (updated in place; a CI repair of a closed phase opens its
  checklist here).
- `docs/gates/check-<YYYY-MM-DD>.md` — the Check summary of `/dev check` (`dev-check.md`).

Milestone End and Pre-Release Review read the folder.

## STATE.md — shared

Only what every phase shares; written rarely:

```markdown
# <Project name> — Project State
## Core Value
## Constraints
## Requirements
## Blockers & Risks
## Decisions
- Phase 7: export as CSV only (bundled round, YYYY-MM-DD)
Milestone End pending: <milestone name>
```

- **Core Value, Constraints:** fixed after init unless the user changes them. **Blockers & Risks:**
  append new, remove resolved.
- **Decisions:** only answers for phases not yet claimed; the claim moves its line into the phase file.
- **`Milestone End pending:`** set when a milestone's last phase is `[x]`; Milestone End removes it.
- **Size:** state, not a diary — ≤ ~3000 words (`state-check.py`); history goes to commits,
  `docs/gates/` and `docs/roadmap-archive/`.

**Transition:** old projects (STATE.md with Quality Gate, Handoff or CI lines) keep running in that
format — those STATE.md sections stand in for the phase file — until the user agrees to
`state-check.py migrate` (`SKILL.md`, Session Start).

**Not for either file:** plan details, code-level decisions, debug state (`.debug/`), velocity metrics.
