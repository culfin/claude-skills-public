# State — the phase file and the shared STATE.md

Each step says what it writes; this file holds the formats.

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

- **Branch:** line 1, the only line a takeover (new workspace, new branch) replaces.
- **Position:** one line — step, next action, date; every step overwrites it. Progress is never
  stored: it is counted from ROADMAP.md.
- **Phase base:** `git rev-parse HEAD` at the claim, kept on a takeover; the gate diffs against it.
- **Acceptance criteria:** the draft of a small phase, the requirement the Spec checker and E2E read; the last line `Criteria complete.` marks it finished (`SKILL.md`, Resume logic).
- **Quality Gate:** read by `check-evidence.py check` without a file argument.
- **CI:** one line per gate commit, status updated in place (`gate.md`, "CI in background").
- **Handoff:** written at pause and interruption, at most 8 lines — where it stopped, Next, Open,
  Traps. Approvals are only those recorded in the phase file or ROADMAP.md.
- **Minor (deferred):** minor task findings, non-critical gate findings, parked twins and traps later
  phases need; phase completion moves them to the gate record.
- **`## UI review — approved findings`:** `/dev ui` during the phase appends the approved IDs
  (`- UI-1`, details in `UI-REVIEW.md`). Each ID is fixed to its criterion
  in 4c, or before the gate goes on if the phase is `[!]` (a code change: touched gate checks
  reopen). An ID leaves once `UI-REVIEW.md` says `fixed` or `not fixed: <reason>`; the phase does not
  become `[x]` while one is listed.

## Gate records — `docs/gates/`

Permanent, one path per record:

- `docs/gates/phase-<N>.md` — `## Gate summary — Phase N: <Name>` (`gate.md`); from phase completion
  on also its `## CI` lines (updated in place; a CI repair of a closed phase opens its checklist
  here) and `## Minor (deferred)`, which Milestone End gathers into Blockers & Risks.
- `docs/gates/check-<YYYY-MM-DD>-<short sha>.md` — the Check summary of `/dev check` (`dev-check.md`).

Milestone End and Pre-Release Review read the folder.

## STATE.md — shared

Only what every phase shares; a phase never writes it:

```markdown
# <Project name> — Project State
## Core Value
## Constraints
## Requirements
## Blockers & Risks
Milestone End pending: <milestone name>
```

- **Core Value, Constraints:** fixed after init unless the user changes them. **Blockers & Risks:**
  append new, remove resolved.
- **`Milestone End pending:`** set by the completion that closes a milestone; Milestone End removes it.
- **Size:** ≤ ~3000 words (`state-check.py`); history goes to commits, `docs/gates/`, `docs/roadmap-archive/`.

**Decisions** live in ROADMAP.md, one indented line under the phase line, for every session:
`  - Decisions: <answers> (<YYYY-MM-DD>)`. Clarification (4a) reads it; a later round extends that
line; it stays when the phase is done.

## Old format (projects without `.dev/`)

A project without `.dev/` next to ROADMAP.md keeps the old format for **all** phases until the user
agrees to `state-check.py migrate` (`SKILL.md`, Session Start). The claim creates no phase file;
STATE.md holds per phase `### Phase N: <Name>` under `## Phases` (`Phase base:`, `Acceptance
criteria:`), `## Quality Gate — Phase N: <Name>`, `## Handoff — <branch>` (position first),
`### Gate summary — Phase N: <Name>`, and under `## CI in background` lines
`- <sha> — Phase N <name>: <status>`; minors go straight to Blockers & Risks.

**Not for either file:** plan details, code-level decisions, debug state (`.debug/`), velocity metrics.
