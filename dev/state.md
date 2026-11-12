# State — the phase file and the shared STATE.md

A phase has exactly one branch at a time; in Orca its workspace carries the display name
`phase-<N>-<slug>`; consecutive phases of a run may share branch and workspace. **Its file
`.dev/phase-<N>.md`** lies next to ROADMAP.md (`<N>` verbatim: 3, 6a, 4.1): created at the claim,
committed with the phase (never git-ignored), deleted at completion, written only by the claiming
branch. After `/clear` the position comes from here alone.

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
- 3f9c2a1

## Handoff
Stopped YYYY-MM-DD: gate Step D, build red in src/filter.ts (cause found, no fix dispatched yet)
Next: Step B fix dispatch with the build error, then Step D again

## Minor (deferred)
- Task 2: date parser accepts `2026-13-01` without an error
```

- **Branch:** line 1, the only line a takeover replaces.
- **Position:** one line — step, next action, date; every step overwrites it. Progress is counted
  from ROADMAP.md, never stored.
- **Phase base:** `git rev-parse HEAD` at the claim, kept on a takeover; the gate diffs against it. A `[!]` claimed after its merge: base and `Phase head:` per `commands.md`.
- **Acceptance criteria:** the draft of a small phase, the requirement the Spec checker and E2E read; the last line `Criteria complete.` marks it finished (`SKILL.md`, Resume logic).
- **Quality Gate:** read by `check-evidence.py check` without a file argument.
- **CI:** `- <sha>` per gate commit, never a status: that stays untracked in
  `$(git rev-parse --git-common-dir)/dev-ci/<sha>` (`ci.md`).
- **Handoff:** written at pause and interruption, at most 8 lines — where it stopped, Next, Open,
  Traps. Approvals are only those recorded in the phase file or ROADMAP.md.
- **Minor (deferred):** minor and non-critical findings, parked twins, traps later phases need;
  completion moves them to the gate record.
- **`## UI review — approved findings`:** `/dev ui` during the phase appends the approved IDs
  (`- UI-1`, details in `UI-REVIEW.md`). Each ID is fixed to its criterion
  in 4c, or before the gate goes on if the phase is `[!]` (a code change: touched gate checks
  reopen). An ID leaves once `UI-REVIEW.md` says `fixed` or `not fixed: <reason>`; the phase does not
  become `[x]` while one is listed.

## Gate records — `docs/gates/`

Permanent, one path per record (Milestone End and Pre-Release Review read them):

- `docs/gates/phase-<N>.md` — `## Gate summary — Phase N: <Name>` (`gate.md`); from completion on
  also its `## CI` SHAs (a later CI repair opens its checklist here) and `## Minor (deferred)`, which Milestone End gathers into Blockers & Risks.
- `docs/gates/check-<YYYY-MM-DD>-<branch slug>.md` — the Check summary of `/dev check` (`dev-check.md`).

## STATE.md — shared

Only what every phase shares. The one status line a phase writes here is `Milestone End pending:`; a change its own requirement asks for is content, in the gate's diff and reviewed like code:

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
- **`Milestone End pending:`** one line per closed milestone, set by the completion that closes it; its Milestone End removes only that line.
- **Size:** ≤ ~3000 words (`state-check.py`); history goes to commits, `docs/gates/`, `docs/roadmap-archive/`.

**Decisions** live in ROADMAP.md, one indented line under the phase line, for every session:
`  - Decisions: <answers> (<YYYY-MM-DD>)` — written only under unclaimed phases and the own, never
under another session's claim. 4a reads it, a later round extends it; it stays
after the phase and moves with it.

## Old format (not migrated)

Migrated ⇔ the empty marker `<prefix>.dev/.gitkeep` is on `origin/<main>` (`git cat-file -e
origin/<main>:<prefix>.dev/.gitkeep`, `<prefix>`: ROADMAP.md's directory; without `origin`, the local
`<main>` stands for `origin/<main>` everywhere). Until the user agrees to `state-check.py migrate`
(`commands.md`, "State findings"), **all** phases keep the old format; the migrating session uses the
new one from its `migrate` commit on. Every write a step makes to `.dev/phase-<N>.md` goes to the
same-named place in STATE.md, reads too (`### Phase N` under `## Phases`, `## Quality Gate — Phase N`,
`## Handoff — <branch>`, position first); CI lines `- <sha> — Phase N <name>`, without status, under `## CI in background`, read there by
Milestone End step 0 and the repair checklist. Gate summary (`### Gate summary — Phase N`) and minors
(Blockers & Risks) stay in STATE.md; completion removes the phase's Quality Gate, `### Phase N` and
Handoff from it. A takeover replaces the `## Handoff — <branch>` heading instead of `Branch:`.

**Not for either file:** plan details, code-level decisions, debug state (`.debug/`), velocity metrics.
