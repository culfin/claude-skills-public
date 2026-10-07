# Roadmap Creation — Detail

**Triggered by:** `/dev init`

If ROADMAP.md exists: AskUserQuestion — Overwrite (Recommended) or Cancel.

### Interactive flow using AskUserQuestion:

**1. Project goal** — free text via Other
**2. Phase types** — multiSelect from the built-in types in `gate.md`: UI, Landing (landing pages, marketing — bold design), Backend, Auth, Security, Refactor, Data, Migration, Docs + Other
**3. Milestone count** — adaptive single-select based on project scope:
  - Small (1-3 phases): 1, 2 (Recommended), 3 + Other
  - Medium (4-6 phases): 3, 4 (Recommended), 5 + Other
  - Large (7+ phases): 4, 5, 6+ (Recommended) + Other
**4. Per milestone** — name/goal (free text), phases (multiSelect from types), per-phase skills (multiSelect, optional)
**5. Triggers** — offer the installed skills (the Skill tool's list; `~/.claude/skills/`,
`.claude/skills/`) per trigger point, multiSelect: milestone-start, milestone-end, pre-release, and
pre-/post-phase per type. `/dev` does not search for or install new skills.

**Placement guidance for the user:**
- **Read-only analysis** (reports, audits, stack-specific reviews) → safe as automatic triggers
- **Code-modifying** (refactoring tools, test generators) → better on-demand, not automatic
- **Project-type-dependent** (browser automation: web only, store screenshots: app stores only)

**Recommended defaults** (mark as Recommended in AskUserQuestion):

The gate's checks (`gate.md`) and the mandatory milestone-end and pre-release analyses (`commands.md`) are not configured here; `@gate: full` forces the large tier. List only additional, optional skills:

- Post-phase any: `requesting-code-review`
- Post-phase UI (web): `playwright-cli` (for interactive browser testing beyond E2E)
- Post-phase UI (native): `writing-clearly-and-concisely`

**6. Preview and confirm** — Write and commit (Recommended), Edit first, Start over.

Write ROADMAP.md to project root.

**7. Create STATE.md** — always create alongside ROADMAP.md:

```markdown
# <Project name> — Project State

## Current Position

Milestone: 1 of N (<milestone name>)
Next phase: Phase 1 — <phase name>
Status: Starting
Last activity: <today's date> — project initialized

## Progress

| Milestone | Progress | Status |
|-----------|------------|--------|
| 1. <Name> | 0/N | Not started |
| ... | | |

## Core Value

<one sentence from the project goal>

## Constraints

<from user input at init, or empty>

## Requirements

<from user input, or "Open — defined in the first milestone">

## Blockers & Risks

None.

## Session Continuity

Last session: <today's date>
Stopped at: project initialized
Resume: `/dev next` to start the first phase
```

Commit both ROADMAP.md and STATE.md together.
