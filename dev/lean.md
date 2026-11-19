# Lean flow — pilot

Read only when the ROADMAP.md frontmatter sets `defaults.flow: lean`; without it this file does not
apply. It adds to `SKILL.md` and `commands.md`; everything not named here runs as usual (claim,
branch, phase file, gate, PR).

```yaml
defaults:
  flow: lean        # opt-in for this file
  builder: claude   # claude (default) | codex
```

`defaults.builder: codex|claude` names who implements in 4c. Missing or any other value → `claude`,
the usual 4c (`execution.md`).

## Cut

Whenever phases are planned — `/dev init`, `/dev add`, the bundled round over several phases —
estimate each `[ ]` phase's diff (code and tests). Above ~500 changed lines, propose cutting it into
phases of at most ~500 lines, each mergeable on its own:

- **Vertical:** one user-visible capability, or one self-contained refactor, end to end — not
  "models", then "API", then "UI".
- **Tests pass and `<main>` works after each one.** Order them so each builds only on the ones before.
- Name each `Phase N.<k> — <capability>` under the original number, with its own `@type:`.
- Only `[ ]` phases are cut; `[~]`, `[!]`, `[x]` and `[—]` stay as they are.

One `AskUserQuestion`: the cut (Recommended), with the phase list and their size estimates, or keep
it as one phase. A hint, never a ban: the user's choice stands; record it on the phase's
`  - Decisions:` line.

## Acceptance criteria

Every new or cut phase gets 2–6 criteria when it is planned, written under its `Decisions:` line:

```markdown
- [ ] Phase 4.2 — Column mapping @type:ui
  - Decisions: mapping saved per file layout (2026-01-10)
  - Criteria:
    - Given an uploaded CSV with unknown headers, When the mapping step opens, Then each header has a target field dropdown
    - Given a saved mapping for this layout, When the same layout is uploaded, Then the mapping is pre-filled
```

- One observable outcome per criterion, with its input; no test code, no implementation detail.
- A criterion an edge case or error path needs gets its own line (empty file, duplicate, no access).
- `Criteria:` moves with its phase (`/dev reorder`) and is only written under `[ ]` phases.

In 4a the criteria become the phase file's `Acceptance criteria:` as checkbox lines, closed by
`Criteria complete.`; the phase counts as small unless 4a classifies it architectural. The gate's
Spec checker numbers them C1, C2, … and reports every criterion without a covering test as (d), as
for any phase (`gate.md`). The builder writes a test per criterion first, named after it.

## One phase, one worker

- **One session builds and gates one phase.** No hand-off inside a phase: the context hint applies
  only at the phase end, never between 4c tasks.
- **After step 7 the run ends** with "Phase N done — `/clear`, then `/dev next`" (child thread:
  report done to the parent, `runtime.md`). The next phase starts in a fresh context with the phase
  file, its criteria and `Decisions:` line, not in this session's history.
- `/dev parallel` and the T3 coordinator start one child thread per phase, as before.
