---
name: dev
description: "Use when user says /dev, /dev next [<N>], /dev parallel, /dev init, /dev status, /dev skip, /dev add, /dev reorder, /dev review, /dev pause, /dev debug, /dev check, /dev ui, or /dev updates. Also use when the user asks to use dev for one of these, and at session start when ROADMAP.md exists in project root (then only a one-line status); not in a task thread whose task is not `/dev …`."
---

## Language

**All user-facing text is in the user's language** (the one they write in or ask for): AskUserQuestion
labels and options, status reports, errors, commit message bodies, STATE.md and ROADMAP.md prose.
Technical terms, skill names, paths, YAML keys and commit prefixes (`roadmap:`, `feat:`) stay English.

# /dev — Milestone Orchestrator

Runs a project's ROADMAP.md phases back to back: clarify, specify, implement, gate. Subagents
implement and review; the main session only steers.

## Router — what to read when

`$DEV_DIR` is this `SKILL.md`'s directory; paths are relative to it. Load only what the
step needs.

| Command or step | File | When |
|---|---|---|
| `/dev`, `/dev next` | this file | Session Start |
| `/dev next <N>`; `/dev parallel [<N> …]` | `next.md`; for `parallel` also `runtime.md` | On the command |
| `/dev init` | `roadmap-creation.md` | Roadmap Creation (writes and commits ROADMAP.md, STATE.md) |
| `/dev status`, `skip`, `add`, `reorder`, `pause`, `review` (Pre-Release Review); Milestone End | `commands.md` | On the command |
| "stop", "drop it", "cancel", "do something else" in a `[~]`/`[!]` phase | `commands.md` | Phase Interruption, at once |
| `/dev debug` | `commands.md` → `debugger.md` | Debug Flow |
| `/dev check` | `dev-check.md` → `gate.md` | Standalone Quality Gate |
| `/dev ui [scope]` | `ui-review.md` | UI review and rework |
| `/dev updates` | skill `dev-updates` (separate); not available → "`/dev updates` needs the `dev-updates` skill — N updates waiting in `pending/`, nothing applied" | On the command |
| Frontmatter `defaults.flow: lean`; `defaults.gate: slim` (else never) | `lean.md`; `gate-slim.md` | `/dev init`, `add`, `reorder`, bundled round; 4a; 4c; step 7; 4d; gate |
| A new use of a foreign skill | `sources.md` | On the change |
| Spec, plan, review reception | `spec-plan.md` | Step 4a spec, 4b, before a fix round |
| Implementation; quality gate | `execution.md`; `gate.md` | Step 4c and its resume; gate entry, resuming `[!]` |
| CI in background, CI repair | `ci.md` | Gate commit; Pre-Phase step 1; Milestone End, Pre-Release Review, `/dev check` |
| Subagent models; state file formats; unmigrated project | `models.md`; `state.md`; `state-old-format.md` | Before dispatching subagents; before writing a phase file, gate record or STATE.md; old format (Session Start 2) |
| Screens ("Show screen", without asking; user interface only) | `companion.md`; `companion-screens.md` | Before the first screen; when writing one |
| Host other than Claude Code; T3 hand-off, PR, asking, child threads | `runtime.md` | When that step comes |
| Bundled round, interview, ADRs; E2E | `befragung.md`; `e2e-testing.md` | Run start over several phases, architectural 4a; gate Step D |
| Tech, design, security triggers and sources | `python3 "$DEV_DIR/scripts/detect-stack.py" --triggers --step <step> --type <@type> [--ui]` (fails → read `tech-stack-triggers.md`, say so) → `stack/docs.md`, `design/INDEX.md` | Steps `4a`, `4c`, `gate` (Step A) |
| Analyzer dispatch | `gate.md`, "Analyzer dispatch" — `analyzers/CONTRACT.md` only by path, for the subagent | Every analyzer dispatch |

---

## Session Start

**Automatic trigger — one line, nothing else.** A session starts in a project with ROADMAP.md and
the user has not typed `/dev` or asked to work on the roadmap: read ROADMAP.md, print
`Roadmap: <milestone> — next: Phase N <name> [<state>]. Continue with /dev.`, then turn to what
the user asked. `${DEV_UPDATES_DIR:-$HOME/.claude/dev-updates}/pending/*.json` exist (count, read
none) → insert `, N skill updates waiting — /dev updates` before the final period. No screen,
no `AskUserQuestion`, no stack detection, no file writes. The steps below run only on an explicit
`/dev`, `/dev next` or roadmap request.

1. **Sync, then read ROADMAP.md.** None in the project root: "No ROADMAP.md found. Run `/dev init` to create one." Stop. Otherwise, **before** reading it or any phase file:
   `git fetch -q` and `python3 "$DEV_DIR/scripts/state-check.py" check`; show its findings;
   any finding → handle it per `next.md`, "State findings" — `behind:` first, `migrate:` next.
   Then read ROADMAP.md.
2. **Read the state** (`state.md`): STATE.md (missing → create its shared sections, `roadmap-creation.md` step 7) and, for a `[~]`/`[!]` phase claimed by this branch, its `.dev/phase-<N>.md` — position, handoff and checklist come only from there. No marker `<prefix>.dev/.gitkeep` on `origin/<main>` → old format for every phase (`state.md`, "Old format").
3. **Detect tech stack** once per session: `python3 "$DEV_DIR/scripts/detect-stack.py"` (project root)
   → `$TECH_STACKS` and the groups **web**/**Apple** (`design/INDEX.md` platform rows). No `python3` or
   exit ≠ 0 → say `detect-stack failed: <error>`, match the root against `stack/INDEX.md` section 1 yourself.
4. **Parse YAML frontmatter.** Malformed: show the error, ask the user to fix it, stop.
5. **Parse phases:** milestones (`##`), goals (`Goal:`), phases (checkbox items), annotations (`@type:`, `@spec:`, `@plan:`, `@gate:`, `@claim:<branch>@<YYYY-MM-DD>`).
   - States: `[ ]` not started, `[~]` in progress, `[!]` gate pending, `[x]` done, `[—]` skipped
   - `@gate:` values other than `full` are ignored with a warning.
   - A `@type:` that `gate.md` does not name and `defaults.phase-types` has no key for → report once per type: `unknown @type: <t> — planning uses no type hints; the gate still reads the diff`.
6. **Find current position:** a `Milestone End pending:` line in STATE.md → Milestone End first (several: `commands.md`). Else the first milestone with an incomplete phase; all done: "Roadmap complete!", offer `/dev add` or `/dev review`.
   **Other sessions:** skip phases reported `claimed` unless the user picks one; `stale claim` → ask
   first; `done on <main>` → mark it, never redo it; `unclaimed` → claim it on resume. Next free phase builds on a skipped
   one → halt and say so.
7. **Show summary** in the chat (never a screen):
   ```
   Milestone 2: UI Shell (3/5 phases done)
   Next: Phase 4 — Connections View (@type:ui)   [resume: gate, first open item "Spec checker"]
   Tech Stack: [nextjs, shadcn, postgres]
   Blockers: <from STATE.md, if any>
   CI: <SHAs not green, Pre-Phase step 1, if any>
   Updates: N skill updates waiting — /dev updates   (only if pending/ has files; count only)
   ```
   Show `@gate: full` when set, `$TECH_STACKS` only on first start or if changed.
8. **Start the run — no menu.** `/dev` and `/dev next` go straight on: `[!]` and `[~]` phases resume
   per "Resume logic" (4), otherwise the next phase starts. Looking without starting is `/dev status`.

---

## Halt on Irreversible Actions

**For anything beyond dev that `git revert` cannot undo, stop and ask** — even mid-run, even if
the plan includes it. Dev deploys and dev-database migrations (shared or destructive too) are the
session's own call; announce shared ones to the other sessions first.

Beyond dev, the user decides:

- Migrations and data changes on staging or production databases
- Production deploys, releases, tags, force-pushes, deleting branches (except the run's own task and agent branches)
- outgoing messages to real recipients (mail, push, webhooks) and payment transactions
- Writing to external storage, registries or object storage
- anything that touches secrets, keys or credentials

Procedure: stop, say in one sentence what would happen and what cannot be undone,
propose, get approval. A plan that describes the step is not approval. An approval must
name the action: "looks fine" to another question is none. A production deploy or release approval
comes with a rollback plan (trigger, steps, time to restore), stated before asking.

Only the thread the user reads asks the user; child threads ask their parent (`runtime.md`, "Asking for the user").

---

## The run

A run over several phases starts with the bundled round (`befragung.md`); `/dev next <N>` and a child
thread skip it. **T3:** pass every background task ID you wait on to `t3_background_wait` at once.
**The run halts only for:**

- clarification questions only the user can answer (`befragung.md`);
- irreversible actions (section above);
- a gate finding still critical after 3 attempts (or 6 gate rounds in total, `gate.md` Step B), or a task finding after 5 fix rounds that every ruling would only guess (`execution.md`);
- the context hint (below);
- Milestone End (`commands.md`);
- plus the gate's own stops (`gate.md`, `ci.md`).

CI `red` or `timeout` halts its repairer (`ci.md`), then the run continues; `none` does not halt.

Everything else goes on without asking: no spec or plan approval, no "continue?" between steps or
phases.

**Context hint.** Note the context size after onboarding (skills, first reads). Stop after 3 completed
phases, ~350k tokens of growth since that note, or ~60% of the model's window — only at a phase end or
between 4c tasks, never from the end of 4c to the gate commit (a started gate finishes here): "Context is large —
`/clear`, then `/dev next`; the position is in `## Position` of the phase file." As a child thread: `runtime.md`, "Child threads" instead.

---

## Phase Execution

Order: milestone start (1) → pre-phase (2–3) → clarify (4a) → plan (4b) → execute (4c) → `[!]` (4d)
→ gate (5) → post-phase (6) → `[x]` (7) → next phase or halt (8). Commits, ledger and Gate Checklist
carry the position; `## Position` is written only at a halt, pause or hand-off.

### 1. Milestone Start Check

First phase of a new milestone → `defaults.skills.milestone-start` as parallel Agent subagents; missing skills → warn, skip.

### 2–3. Pre-Phase and pre-skill handoff

1. **CI status first:** every SHA under `## CI` in `.dev/phase-*.md` and in `docs/gates/phase-*.md` of this milestone's phases; any SHA there → read `ci.md` for status and repairer: own `red`/`timeout` SHAs → repair before this phase starts. Of their `## Minor (deferred)`, read only the items whose files this phase touches, as traps for this phase.
2. **On `<main>`** (`git branch --show-current`) claim nothing there. T3 mode: hand Phase N off as
   `/dev parallel <N>` does (`runtime.md`, "Parallel phase"), report the child thread and end the run
   as coordinator. Otherwise, and on a host's `t3/…` branch, `git fetch -q && git switch -c phase-<N>-<slug> --no-track
   origin/<main>` (slug: `runtime.md`), then claim there; push it only as `git push -u origin HEAD:refs/heads/<branch>`.
   Mark phase `[~]` in ROADMAP.md with `@claim:<current branch>@<today>`. New phase: create `.dev/phase-<N>.md` with `Branch: <current branch>`, `## Position` and `Phase base: <git rev-parse HEAD>`; a `[!]` phase without one stays `[!]`, its file per `next.md`, `phase file missing:`. Takeover: replace the claim and only the `Branch:` line; `Phase base:` stays. Old format: no phase file (`state.md`). Commit them at once as `roadmap: claim Phase N` on this branch, push it (refspec above) if the repo has a remote — never a PR or commit to `<main>` for a claim: `state-check.py` reads claims from every recent branch.
3. Resolve pre-skills: `defaults.phase-types.<@type>.pre` from the frontmatter (post-skills: `.post`); an unknown type → empty lists (reported once, "Parse phases"). Built-in phase types and `@gate:`: `gate.md`.
4. Dispatch pre-skills as parallel Agent subagents; 4a gets their output paths and reads only relevant findings.

### 4. Phase Cycle

**Resume logic:**
- `[!]` → Quality Gate (step 5) at the first open item of the phase file's Gate Checklist
- `[~]` with `@plan:` path on disk, or acceptance criteria ending in `Criteria complete.` (small phase; without that line if the phase already has commits) → execution (4c); the ledger says which tasks are done (`execution.md`, "Ledger")
- `[~]` with `@spec:` path on disk → planning (4b)
- The phase file has `## UI review — approved findings` → those IDs are part of this phase: fix each to its criterion in `UI-REVIEW.md`, then clear it (`state.md`)
- `[~]` with neither, or with criteria lacking that last line → clarification (4a)

**4a. Clarification:** read the phase's `Decisions:` line in ROADMAP.md first; new answers extend it (`state.md`).
1. **Classify:** architectural if the phase creates a project or subsystem, changes how components interact or interfaces others build on; `@type: migration` always; in doubt, architectural. `@type: docs`: no interview.
   **Core rule:** the repo's `AGENTS.md` has `## Core rules` and the phase changes how one of them behaves → architectural, and before any question write `Domain model:` into the phase file (`state.md`): *Current* — how the code implements the rule today, with `file:line`; *Intended* — the rule after the phase in the owner's words, including what happens to existing and manually entered data. The interview's first question confirms or corrects it (`befragung.md`); no spec or plan before it is confirmed.
2. **Small → write the draft straight into the phase file** as `Acceptance criteria:`
   (format in `state.md`), closed by the line `Criteria complete.` — no approval round. Ask only
   questions whose answer changes what gets built, via `AskUserQuestion`, recommendation first with
   "(Recommended)"; look up facts yourself instead of asking.
3. **Architectural → interview in rounds per `befragung.md`** (incl. ADRs), then spec and builder check per
   `spec-plan.md`, no approval round. After the spec is committed: add `@spec:` to ROADMAP.md.

Both: matching tech skills first (`--triggers --step 4a`, router). The phase builds or changes UI
(criteria or spec name a screen, page, view, dialog or component; any `@type:`; then `--ui` in every step) and `ux-ui-design` is
available → invoke it in planning mode before the criteria or spec; its UX questions join the round. Questions with a
UI/UX side: "Show screen" (`companion.md`).

**4b. Planning:** the plan per `spec-plan.md`. Commit it, add `@plan:` to ROADMAP.md, go on to 4c — no approval.

**4c. Execution → read `execution.md`.** No separate verification step: gate Step D proves it.

**4d. Gate Transition (`[~]` → `[!]`):**
1. Mark phase `[!]` in ROADMAP.md
2. Create the Quality Gate Checklist in the phase file — tier and format in `gate.md`, "Tier" and "Gate Checklist"

`[!]` = implemented, gate not yet passed — the **only** path to `[x]`; `[~]` → `[x]` is **forbidden**.

### 5. Mandatory Quality Gate

**→ Read `gate.md`**, then `ci.md` at the gate commit. Every checkmark needs evidence; the phase stays `[!]` until all are `[x]`.

### 6. Post-Phase

Only with every Gate Checklist item `[x]` (else return to the first open one). Post-skills run as
subagents on the gate-verified state — read-only ones in parallel, code-changing ones after them.
A check already on the Gate Checklist is not run again, even if a post-skill lists it (`requesting-code-review` = the gate's Diff review).

### 7. Phase Completion (`[!]` → `[x]`)

1. **Verify Gate Checklist:** `python3 "$DEV_DIR/scripts/check-evidence.py" check` must exit 0. Any unchecked → STOP, return to it in step 5.
2. Mark `[x]` in ROADMAP.md (replacing `[!]`, dropping `@claim:`); `@spec:` and `@plan:` present (small phases have neither)
3. **Gate record:** append the phase file's `## CI` and `## Minor (deferred)` to `docs/gates/phase-<N>.md` (it holds the Gate summary); STATE.md stays untouched.
4. Delete `.dev/phase-<N>.md` and the phase's SDD workspace (`execution.md`).
5. Commit it all in one commit: `roadmap: complete Phase N — <name>`; then push gate and completion commit together (`ci.md`)
6. `git fetch`, then read `git show origin/<main>:<prefix>ROADMAP.md`: every phase of the milestone `[x]`/`[—]` there, this one counted as done → append `Milestone End pending: <milestone name>` below any such lines in STATE.md (a merge keeps all), then Milestone End (`commands.md`)

### 8. Next Action

One status line, then the next phase — unless a halt from "The run" applies.

---

## Error Handling

A `[—]` phase is skipped; status shows its reason.

**Principle:** Never block for recoverable errors (unknown `@type:`, a skill not installed, a malformed `defaults` entry): warn and continue. Stop only for missing ROADMAP.md, broken YAML and "The run" halts.
