# Lean flow — pilot

Read only when the ROADMAP.md frontmatter sets `defaults.flow: lean`; without it this file does not
apply. It adds to `SKILL.md` and `commands.md`; everything not named here runs as usual (claim,
branch, phase file, gate, PR). Under `t3-team`, its approval (`docs/team.md` `Flow: lean`) is also required.

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

Every new or cut phase gets 2–6 criteria when it is planned, written under its `Decisions:` line,
or straight under the phase line if it has none. A cut keeps the original `Decisions:` line on its
first phase; the others get `  - Decisions: see Phase N.1`. Example:

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
- `/dev parallel` and the lead start one child thread per phase, as before.

## Builder: Codex

With `defaults.builder: codex`, Codex replaces the Claude implementer in 4c; this session keeps
planning and the gate, so Claude reviews Codex. Pilot projects only.

1. Write the brief as for the implementer (`execution.md`: the small phase's
   `.superpowers/sdd/phase-…` file, or the plan) and add the test command. The worktree must be clean
   at the phase HEAD.
2. Run in the background (T3: its task ID to `t3_background_wait`), `--out` under `$TMPDIR`:
   `bash "$DEV_DIR/scripts/codex-build.sh" --brief <file> --head <HEAD sha> --out <file> --roadmap <path>`
   `--roadmap` is the phase's own ROADMAP.md relative to the worktree root, the same file `/dev` reads
   for the phase (`<prefix>ROADMAP.md`; monorepo: `apps/web/ROADMAP.md`); omitted = `ROADMAP.md` at the root.
   Start no other processes in the worktree while it runs: its sweep kills them.
3. **Exit 0:** Codex's changes are uncommitted in the worktree; `--out` holds `files:`,
   `ignored-new:`, `ignored-changed:`, `hooks-changed:` and its summary with `open:`. Read the diff;
   look at `ignored-new:` and `ignored-changed:` before running the tests. Open
   items or red tests → the Claude implementer finishes them in the same worktree. Inspect
   `hooks-changed:` before committing; commit the phase's paths explicitly. Add `Builder: codex` under `Phase base:` in the phase file only if
   Codex's diff is the bulk of the phase; the Claude implementer wrote a task or more than a few
   lines → no line, so `codex diff` still runs. Then the gate.
4. **Exit 3** (`fallback: <reason>`) → the usual 4c with the Claude implementer on the same worktree.
   The script has reset it to `--head` and undone any Codex commit. With `--keep-partial` Codex's
   partial changes stay uncommitted: then hand the implementer the `--out` file, which lists them.
   No `Builder:` line. `partial: not touched` (changed `.git` or git config, `codex left processes
   running`, or a failed analysis, e.g. an unreadable directory): nobody builds in that worktree until you have inspected it and those processes are
   gone (`ps`, `lsof +D <worktree>`).
5. **Exit 2:** fix the call (dirty worktree, wrong `--head`); missing `defaults.builder: codex` in that
   roadmap or a `--roadmap` outside the worktree → the Claude implementer (fix the path first).

The script runs Codex under a permission profile: writes only in the worktree, no network, no push;
`.env` files stay the worktree's symlinks, never copied or printed.
