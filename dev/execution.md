# Execution — step 4c

Read at step 4c and when resuming a `[~]` phase that has a plan or acceptance criteria. This file is
the only description of how a phase gets implemented. The main session dispatches every implementer
and every reviewer itself: in Claude Code a subagent cannot dispatch subagents, and a worker that
reviews its own change only repeats its own conclusions.

## Setup

- **`$SDD`** = `<active superpowers root>/skills/subagent-driven-development` (active root per
  `superpowers.md`). Its prompts and scripts are used directly; its skill is not invoked, so its own
  serial loop, five fix rounds and final review do not apply (`sources.md` O1, O16).
- **Workspace:** `bash "$SDD/scripts/sdd-workspace" <plan file>` prints the git-ignored directory for
  this phase. Ledger, tasks JSON, wave output, briefs, reports and review packages live there as files;
  the chat gets one status line per task (`Task 3: complete — 2 commits, review clean`). Everything
  pasted into the chat is reread on every later turn, so hand artifacts over as paths.
- **Ledger** `<workspace>/progress.md`, first line `# SDD ledger — plan: <plan file>`. A task with a
  `Task <N>: complete` line is done — never dispatch it again; after `/clear` or compaction trust the
  ledger and `git log` over memory.
- **Models:** every dispatch names its model per `models.md`; an omitted model inherits the most
  expensive one.
- **UI tasks:** pass the `design/INDEX.md` and `stack/INDEX.md` rows marked `4c` whose trigger the task
  meets (`tech-stack-triggers.md`, "During Execution").
- **Before the first dispatch,** scan the plan for tasks that contradict each other or the spec. Rule
  on each (the spec is binding, the plan argues from it) and write `Ruling: <what> — <why>` to the
  ledger; ask the user only if the answer changes what gets built and no reading of the spec decides it.

## Small phase (no plan)

Copy the phase's acceptance criteria from STATE.md into `.superpowers/sdd/phase-<N>.md` and run
`sdd-workspace` on that file at once (it writes the `.gitignore` that keeps it out of git); the file is
both plan and brief. One implementer with `$SDD/implementer-prompt.md`, in the current tree; one task
review and its fix loop (below); then the gate.

## Planned phase — waves

1. Read each task's `**Files:**` block and its "after"/interface notes (a task that consumes what
   another produces comes after it) into `<workspace>/tasks.json`:
   `{"tasks": [{"id": "1", "files": ["src/a.ts"], "after": []}, …]}`, in plan order.
2. `python3 "$DEV_DIR/scripts/waves.py" <workspace>/tasks.json > <workspace>/waves.json`. Exit 2 (cycle,
   unknown or duplicate id) → fix the JSON from the plan; never guess the order.
3. Per task: `bash "$SDD/scripts/task-brief" <plan> <N>` writes the brief. The dispatch carries the
   brief path ("read this first — it is your requirements"), interfaces from earlier tasks, your
   rulings, and the report path `…/task-<N>-report.md` — absolute paths, because the workspace is
   git-ignored and does not exist inside a task worktree.

**Per wave.** Before it starts, the phase's own work is committed — a task worktree starts from
`HEAD`, and uncommitted changes are not in it (changes that are not the phase's stay untouched).
Record the wave's BASE (`git rev-parse HEAD`).

- **Load brake:** before each dispatch `bash "$DEV_DIR/scripts/load-ok.sh"`. Exit 1 → wait 60 s and
  retry; after 10 minutes, dispatch the remaining tasks of the wave one at a time. Parallel builds on
  a busy machine turn every check into a timeout and save nothing.
- **More than one task in the wave:** dispatch each implementer with `isolation: "worktree"`, all in
  one message. Parallel commits, builds and test runs in one working tree collide. A single-task wave
  runs in the current tree.
- **In a worktree, implementers run unit tests only;** integration and E2E run once on the merged
  state (gate Step D) — several copies of a database or browser stack overload the machine.
- **Irreversible steps** (`SKILL.md`, "Halt on Irreversible Actions") are never run by an implementer:
  it reports `BLOCKED` with the step, and the run halts for the user.

**Task review as soon as a task finishes** — do not wait for the rest of the wave:
`bash "$SDD/scripts/review-package" <plan> <BASE> <task branch or HEAD>`, then a reviewer with
`$SDD/task-reviewer-prompt.md`, given the brief, the report, the package and the binding constraints
copied verbatim from the spec. `DONE_WITH_CONCERNS` → read the concerns first; `NEEDS_CONTEXT` →
answer and resume; `BLOCKED` → change something (context, model one tier up, smaller task) before
dispatching again.

**Fix loop — at most 3 rounds per task.** Spec ❌ or a Critical/Important finding starts it.
Rounds 1–2 resume the same implementer with the open findings verbatim; round 3 dispatches a fresh
implementer one tier up (`models.md`) with brief, report and findings, in the same worktree. After
each round, a scoped re-review: `review-package <plan> <head the last review saw> <new head>` and
`$SDD/re-review-prompt.md`. Ledger line per round: `Task <N>: fix round <R>/3 (<X> addressed, <Y> open)`.
Still open after round 3 → halt and report what remains (one of the run's halts). Minor findings go
to the ledger as `Task <N>: minor (deferred): …` and, when the phase ends, to STATE.md Blockers & Risks
— a list nobody reads is a silent discard. Never fix findings in the main session: that skips review.

**Merge after the wave,** once every task in it is complete: bring each task branch into the phase
branch in plan order (`git merge --no-ff <task branch>`, or cherry-pick its commits). A conflict →
`git merge --abort`, and run that task again serially on top of the merged state (new brief run,
same review loop). Then run the unit tests once on the merged state; red → fix loop of the task whose
merge broke it. Remove the task worktrees (`git worktree remove <path>`) and delete merged task
branches with `git branch -d` (it refuses unmerged work); an unmerged branch stays and is named in the
ledger. Ledger: `Task <N>: complete (merged <sha>)`.

## Scope boundary

Execution ends when every task is complete and merged. It does **not** run
`finishing-a-development-branch` (no merge into other branches, no PR — `/dev` owns completion via the
gate) and no final whole-branch review: the gate's review wave covers the whole phase diff. Then
back to `SKILL.md`, 4d (gate transition).
