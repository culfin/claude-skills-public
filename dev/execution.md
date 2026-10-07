# Execution — step 4c

Read at step 4c and its resume. The main session dispatches every implementer and reviewer itself
(a subagent cannot dispatch subagents).

## Setup

- **`$SDD`** = `<active superpowers root>/skills/subagent-driven-development` (active root per
  `superpowers.md`). Its prompts and scripts are used directly, its skill is not invoked (`sources.md` O1, O16).
- **Phase branch** = the branch the session is on when the phase starts. Task branches merge into it;
  nothing else is merged or pushed here.
- **Workspace:** `bash "$SDD/scripts/sdd-workspace" <plan file>` prints the git-ignored directory for
  this phase. Ledger, tasks JSON, wave output, briefs, reports and review packages live there as files;
  the chat gets one status line per task (`Task 3: complete — 2 commits, review clean`). When the phase
  reaches `[x]`, delete its workspace.
- **Models:** every dispatch names its model per `models.md` (omitted = the most expensive).
- **UI tasks:** pass the `design/INDEX.md` and `stack/INDEX.md` rows marked `4c` whose trigger the task
  meets (`tech-stack-triggers.md`, "During Execution").
- **Before the first dispatch,** scan the plan for tasks that contradict each other or the spec. Rule
  on each (the spec is binding, the plan argues from it) and write `Ruling: <what> — <why>` to the
  ledger; ask the user only if the answer changes what gets built and no reading of the spec decides it.

## Ledger

`<workspace>/progress.md`, first line `# SDD ledger — plan: <plan file>`. Every task transition gets a
line the moment it happens — memory does not survive `/clear` or compaction:

```
Task 2: dispatched (worktree /abs/path, branch task-2, BASE 3f9c2a1)
Task 2: reviewed (2 findings)
Task 2: fix round 1/3 (1 addressed, 1 open)
Task 2: reviewed clean
Task 2: complete (merged 8e01b7d)
Task 4: interrupted (worktree /abs/path, branch task-4)
```

**Resume** reads the ledger, then `git worktree list` and the task branches: `complete` → skip.
`dispatched`, `reviewed`, `fix round` or `interrupted` with its worktree or branch still there →
continue from that state — review its commits, or redispatch into that same worktree (as in fix round
3 below) — never a second fresh dispatch, which would leave two branches for one task. Worktree and
branch gone → dispatch fresh.

## Small phase (no plan)

Copy the phase's acceptance criteria from STATE.md into `.superpowers/sdd/phase-<N>-<slug>.md` (slug
of the phase name, so a renumbered or repeated phase number never adopts an old workspace) and run
`sdd-workspace` on it at once (it writes the `.gitignore` that keeps the file out of git); the file is
both plan and brief. BASE is the `<phase base>` defined in `gate.md`, "Tier". One implementer with
`$SDD/implementer-prompt.md`, in the current tree; one task review and its fix loop (below); then the
gate.

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

**Per wave.** Before it starts, the phase's own work is committed — a task worktree starts from a
commit, and uncommitted changes are not in it (changes that are not the phase's stay untouched).
Record the wave's BASE (`git rev-parse HEAD` on the phase branch).

- **More than one task in the wave:** dispatch each implementer with `isolation: "worktree"`.
  If the worktree does not start from the phase branch's HEAD (host-dependent), the implementer first
  creates its task branch from BASE (given in the dispatch) — else the review package fails. A
  single-task wave, or a host without worktree isolation, runs serially in the current tree.
- **Load brake:** one Agent call per message, with `bash "$DEV_DIR/scripts/load-ok.sh"` before each —
  the load can only change between messages. Exit 1 → wait 60 s in the background (a background
  `sleep` or the host's wait/until-loop, not a foreground `sleep`) and check again; after 10 minutes,
  run the rest of the wave serially in the current tree. A serial task's BASE is HEAD before its
  dispatch (ledger line).
- **In a worktree, implementers run unit tests only;** integration and E2E run once on the merged
  state (gate Step D).
- **Ladder before writing** (tell every implementer): the phase or repo already has it, then the
  standard library, a native platform feature, an existing dependency — only then the smallest code
  that meets the acceptance criteria.
- **Framework decisions** quote their doc (`stack/docs.md`) or are marked `UNVERIFIED`.
- **Irreversible steps** (`SKILL.md`, "Halt on Irreversible Actions") are never run by an implementer:
  it reports `BLOCKED` with the step, and the run halts for the user.

**Task review as soon as a task finishes** — do not wait for the rest of the wave:
`bash "$SDD/scripts/review-package" <plan> <BASE> <task branch or HEAD>`, then a reviewer with
`$SDD/task-reviewer-prompt.md`, given the brief, the report, the package and the binding constraints
copied verbatim from the spec. `DONE_WITH_CONCERNS` → read the concerns first; `NEEDS_CONTEXT` →
answer and resume; `BLOCKED` → change something (context, model one tier up, smaller task) before
dispatching again.

**Fix loop — at most 3 rounds per task.** Spec ❌ or a Critical/Important finding starts it.
Rounds 1–2 resume the same implementer with the open findings verbatim. Round 3 dispatches a fresh
implementer one tier up (`models.md`) with brief, report and findings — **without** isolation, told
to work only inside the task's existing worktree (its absolute path), where the task branch and its
commits are. After each round, a scoped re-review:
`review-package <plan> <head the last review saw> <new head>` and `$SDD/re-review-prompt.md`. Still
open after round 3 → halt and report what remains (one of the run's halts). An implementer or
reviewer naming a weakness of the task's own tests (one that cannot fail, tests a parameter instead
of the default) starts a fix round — never `minor`. Minor findings go to the
ledger as `Task <N>: minor (deferred): …` and, when the phase ends, to STATE.md Blockers & Risks. Never fix findings in the main session: that skips review.

**Merge after the wave,** once every task in it is reviewed clean: bring the task branches into the
phase branch one by one in plan order (`git merge --no-ff <task branch>`, or cherry-pick its commits)
and run the unit tests after each merge, so a red run names the task that broke it — that task goes
back into its fix loop. A conflict → `git merge --abort`, and run that task again serially on top of
the merged state (same brief, same review loop). Then remove the task worktrees (`git worktree remove
<path>`) and delete merged task branches with `git branch -d` (it refuses unmerged work); an unmerged
branch stays and is named in the ledger.

## Scope boundary

Execution ends when every task is complete and merged — no `finishing-a-development-branch`, no PR, no
whole-branch review (the gate covers the phase diff). Then `SKILL.md`, 4d.
