---
name: dev
description: "Use when user says /dev, /dev next, /dev init, /dev status, /dev skip, /dev add, /dev reorder, /dev review, /dev pause, /dev debug, /dev check, /dev ui, or /dev updates. Also use when the user asks to use dev for one of these, and at session start when ROADMAP.md exists in project root (then only a one-line status)."
---

## Language

**All user-facing text is in the user's language** (the one they write in or ask for): AskUserQuestion
labels and options, status reports, errors, commit message bodies, STATE.md and ROADMAP.md prose.
Technical terms, skill names, paths, YAML keys and commit prefixes (`roadmap:`, `feat:`) stay English.

# /dev — Milestone Orchestrator

Runs a project's ROADMAP.md phases back to back: clarify, specify, implement, gate. Subagents
implement and review; the main session only steers.

## Router — what to read when

`$DEV_DIR` is the directory of this `SKILL.md`; paths are relative to it. Load only what the
current step needs. Not for single tasks, projects without milestones, or when the user skips the orchestrator.

| Command or step | File | When |
|---|---|---|
| `/dev`, `/dev next` | this file | Session Start |
| `/dev init` | `roadmap-creation.md` | Roadmap Creation (writes and commits ROADMAP.md, STATE.md) |
| `/dev status`, `skip`, `add`, `reorder`, `pause`, `review` (Pre-Release Review); Milestone End | `commands.md` | On the command |
| A `state-check.py check` finding | `commands.md` | State findings, Session Start step 1 |
| "stop", "drop it", "cancel", "do something else" in a `[~]`/`[!]` phase | `commands.md` | Phase Interruption, at once |
| `/dev debug` | `commands.md` → `debugger.md` | Debug Flow |
| `/dev check` | `dev-check.md` → `gate.md` | Standalone Quality Gate |
| `/dev ui [scope]` | `ui-review.md` | UI review and rework |
| `/dev updates`; a new use of a foreign skill | `updates.md` → `sources.md` | On the command |
| Implementation; quality gate | `execution.md`; `gate.md` | Step 4c and its resume; gate entry, resuming `[!]` |
| CI in background, CI repair | `ci.md` | Gate commit; before each phase if a phase or gate file of this milestone has a `## CI` SHA; Milestone End, Pre-Release Review, `/dev check` |
| Subagent models; state file formats | `models.md`; `state.md` | Before dispatching subagents; before writing a phase file, gate record or STATE.md |
| Visual Companion | `companion.md`; `companion-screens.md` | Before the first screen; when writing one |
| Host adapter; superpowers install | `runtime.md`; `superpowers.md` | First explicit `/dev` run; before the first phase step or a plugin update |
| Bundled round, interview, ADRs; E2E | `befragung.md`; `e2e-testing.md` | Run start, architectural 4a; gate Step D |
| Tech, design, security triggers and sources | `tech-stack-triggers.md` → `stack/INDEX.md`, `stack/docs.md`, `design/INDEX.md` | Steps 4a, 4c, gate Step A — matching rows only |
| Analyzer contract | `analyzers/CONTRACT.md` | With every analyzer dispatch |

**Visual Companion:** shows only the product's user interface (mockups, states, real screenshots — never roadmaps, plans, architecture or findings), used without asking wherever this skill says **"Show screen"** (`companion.md`); only a message pointing at a new or updated screen ends with its URL.

---

## Session Start

**Automatic trigger — one line, nothing else.** A session starts in a project with ROADMAP.md and
the user has not typed `/dev` or asked to work on the roadmap: read ROADMAP.md, print
`Roadmap: <milestone> — next: Phase N <name> [<state>]. Continue with /dev.`, then turn to what
the user asked. `${DEV_UPDATES_DIR:-$HOME/.claude/dev-updates}/pending/*.json` exist (count, read
none) → insert `, N skill updates waiting — /dev updates` before the final period. No companion,
no `AskUserQuestion`, no stack detection, no file writes. The steps below run only on an explicit
`/dev` / `/dev next` or a request to work on the roadmap.

1. **Sync, then read ROADMAP.md.** None in the project root: "No ROADMAP.md found. Run `/dev init` to create one." Stop. Otherwise, **before** reading it or any phase file:
   `git fetch -q` and `python3 "$DEV_DIR/scripts/state-check.py" check`; show its findings;
   any finding → handle it per `commands.md`, "State findings" — `behind:` first, `migrate:` next.
   Then read ROADMAP.md.
2. **Read the state** (`state.md`): STATE.md (missing → create its shared sections, `roadmap-creation.md` step 7) and, for a `[~]`/`[!]` phase claimed by this branch, its `.dev/phase-<N>.md` — position, handoff and checklist come only from there. No marker `<prefix>.dev/.gitkeep` on `origin/<main>` → old format for every phase (`state.md`, "Old format").
3. **Detect tech stack** once per session: the project root against section 1 of `stack/INDEX.md`,
   ids stored as `$TECH_STACKS` (e.g. `[nextjs, shadcn, postgres]`); `nextjs`, `shadcn` and `svelte`
   also count as **web**, `ios` as **Apple** (`design/INDEX.md` platform rows match on these).
4. **Parse YAML frontmatter.** Malformed: show the error, ask the user to fix it, stop.
5. **Parse phases:** milestones (`##`), goals (`Goal:`), phases (checkbox items), annotations (`@type:`, `@spec:`, `@plan:`, `@gate:`, `@claim:<branch>@<YYYY-MM-DD>`).
   - States: `[ ]` not started, `[~]` in progress, `[!]` gate pending (implemented, gate outstanding), `[x]` done, `[—]` skipped
   - `@gate:` values other than `full` (the old `fast` and `ci-wait`) are ignored with a warning.
   - A `@type:` that `gate.md` does not name and `defaults.phase-types` has no key for → report once per type: `unknown @type: <t> — planning uses no type hints; the gate still reads the diff`.
6. **Find current position:** STATE.md has `Milestone End pending: <name>` → Milestone End first. Else the first milestone with an incomplete phase; all done: "Roadmap complete!", offer `/dev add` or `/dev review`.
   **Other sessions:** skip phases reported `claimed` unless the user picks one; `stale claim` → ask
   first; `done on <main>` → mark it, never redo it; `unclaimed` → claim it on resume. Next free phase builds on a skipped
   one → halt and say so.
7. **Show summary** in the terminal (never the companion):
   ```
   Milestone 2: UI Shell (3/5 phases done)
   Next: Phase 4 — Connections View (@type:ui)   [resume: gate, first open item "Spec checker"]
   Tech Stack: [nextjs, shadcn, postgres]
   Blockers: <from STATE.md, if any>
   CI: <SHAs not green, Pre-Phase step 1, if any>
   Updates: N skill updates waiting — /dev updates   (only if pending/ has files; count only)
   ```
   Show `@gate: full` when set, `$TECH_STACKS` only on first session start or if changed.
8. **Start the run — no menu.** `/dev` and `/dev next` go straight on: `[!]` and `[~]` phases resume
   per "Resume logic" (4), otherwise the next phase starts. Looking without starting is `/dev status`.

---

## Halt on Irreversible Actions

Across all phase steps: **for anything that `git revert` cannot undo, stop and
ask** — even in the middle of an autonomous run, even if the plan includes the step.

The criterion is not "feels risky", but: *if this was wrong, does a
commit revert restore the state?* If the answer is no, the decision belongs to the user:

- Schema and data migrations, especially destructive ones (`DROP`, `DELETE`, `TRUNCATE`, type changes)
- any change to a **shared** development or staging database — it takes effect immediately
  for all parallel sessions, not only on merge
- Deploys, releases, tags, force-pushes, deleting branches
- outgoing messages to real recipients (mail, push, webhooks) and payment transactions
- Writing to external storage, registries or object storage
- anything that touches secrets, keys or credentials

Procedure: stop, say in one sentence what would happen and what about it cannot be undone,
state the proposal, get approval. For `@type: migration` this halt is mandatory and cannot
be replaced by a line in the plan — a plan that describes the migration is not approval
to run it. An approval must name the action: "looks fine" to another question is none. A deploy
or release approval comes with a rollback plan (trigger, steps, time to restore), stated before asking.

---

## The run

A run works through the phases until the milestone ends or a halt applies. At its start, ask the
bundled round (`befragung.md`). **The run halts only for:**

- clarification questions only the user can answer (`befragung.md`);
- irreversible actions (section above);
- a gate finding still critical after 3 attempts (or 6 gate rounds in total, `gate.md` Step B), or a task still open after its 3 fix rounds (`execution.md`);
- the context hint (below);
- Milestone End (`commands.md`);
- plus the gate's own stops (`gate.md`, `ci.md`): wrong branch at the gate commit, unclear staging, no
  authorized route for CI (once per run), a review item that timed out twice, a floor-guard
  critical that is not undone (needs approval).

CI `red` or `timeout` halts its repairer (`ci.md`), then the run continues; `none` does not halt.

Everything else goes on without asking: no spec or plan approval, no "continue?" between steps or
phases — a pause before a plain "continue" decides nothing.

**Context hint.** After each phase: if this session has completed 3 phases, or the host shows the
context above ~250k tokens, stop at the phase boundary with "Context is large — `/clear`, then
`/dev next`; the position is in `## Position` of the phase file." As an Orca worker: `runtime.md`, "Orca workers" instead. A large context is reread on every turn.

---

## Phase Execution

Order: milestone start (1) → pre-phase (2–3) → clarify (4a) → plan (4b) → execute (4c) → `[!]` (4d)
→ gate (5) → post-phase (6) → `[x]` (7) → next phase or halt (8). Each step overwrites the phase
file's `## Position`; it goes into that step's next commit.

### 1. Milestone Start Check

First phase of a new milestone → `defaults.skills.milestone-start` as parallel Agent subagents; missing skills → warn, skip.

### 2–3. Pre-Phase and pre-skill handoff

1. **CI status first:** every SHA under `## CI` in `.dev/phase-*.md` and in `docs/gates/phase-*.md` of this milestone's phases; any SHA there → read `ci.md` for status and repairer: own `red`/`timeout` SHAs → repair before this phase starts. Read the gate files' `## Minor (deferred)` too, as traps for this phase.
2. Mark phase `[~]` in ROADMAP.md (Edit tool) with `@claim:<current branch>@<today>`. New phase: create `.dev/phase-<N>.md` with `Branch: <current branch>`, `## Position` and `Phase base: <git rev-parse HEAD>`. Takeover: replace the claim and only the `Branch:` line; `Phase base:` stays. Old format: no phase file (`state.md`). Commit them at once as `roadmap: claim Phase N` on this branch, push it if it has a remote — never a PR or commit to `<main>` for a claim: `state-check.py` reads claims from every recent branch. Orca mode: name and mark this workspace's card, never create one (`runtime.md`, "Orca").
3. Resolve pre-skills: `defaults.phase-types.<@type>.pre` from the frontmatter (post-skills: `.post`); an unknown type → empty lists (reported once, "Parse phases"). Built-in phase types (planning hints; gate additions that never remove a check) and `@gate:`: `gate.md`.
4. Dispatch pre-skills as parallel Agent subagents; 4a gets their output file paths and reads only the relevant findings.

### 4. Phase Cycle

**Resume logic:**
- `[!]` → Quality Gate (step 5) at the first open item of the phase file's Gate Checklist
- `[~]` with `@plan:` path on disk, or acceptance criteria ending in `Criteria complete.` (small phase; without that line if the phase already has commits) → execution (4c); the ledger says which tasks are done (`execution.md`, "Ledger")
- `[~]` with `@spec:` path on disk → planning (4b)
- The phase file has `## UI review — approved findings` → those IDs are part of this phase: fix each to its criterion in `UI-REVIEW.md`, then clear it (`state.md`)
- `[~]` with neither, or with criteria lacking that last line → clarification (4a)

**4a. Clarification:** read the phase's `Decisions:` line in ROADMAP.md first; new answers extend it (`state.md`).
1. **Classify:** architectural if the phase creates a project or subsystem, changes how components interact or interfaces others build on; `@type: migration` always; in doubt, architectural. `@type: docs`: no interview.
2. **Small → write the draft straight into the phase file** as `Acceptance criteria:`
   (format in `state.md`), closed by the line `Criteria complete.` — no approval round; the Spec checker and a resume read it there. Ask only
   questions whose answer changes what gets built, via `AskUserQuestion`, recommendation first with
   "(Recommended)"; look up facts yourself instead of asking.
3. **Architectural → interview in rounds per `befragung.md`** (incl. ADRs), then
   `superpowers:brainstorming` with the handoff note from `befragung.md` **and this override**: no
   approvals, write and commit the spec (`sources.md` O14). Its hand-off to `writing-plans` carries the
   4b instruction. After the spec is committed: add `@spec:` to ROADMAP.md.

Both: matching tech skills first (`tech-stack-triggers.md`, "During Brainstorming"). Questions with a
UI/UX side: ensure the companion via "Show screen" and pass on the hand-off note's companion
sentences (`befragung.md`, step 5).

**4b. Planning:** `superpowers:writing-plans` with "no execution-method question; do not start
execution — `/dev` does" (`sources.md` O15). Commit the plan, add `@plan:` to ROADMAP.md, go on to 4c — no approval.

**4c. Execution → read `execution.md`.** No separate verification step: gate Step D proves it.

**4d. Gate Transition (`[~]` → `[!]`):**
1. Mark phase `[!]` in ROADMAP.md (Edit tool)
2. Create the Quality Gate Checklist in the phase file — tier and format in `gate.md`, "Tier" and "Gate Checklist"
3. `## Position`: "Gate starting — next: <first item>"

`[!]` = implemented, gate not yet passed — the **only** path to `[x]`; `[~]` → `[x]` is **forbidden**.

### 5. Mandatory Quality Gate

**→ Read `gate.md`**, then `ci.md` at the gate commit. Every checkmark needs evidence; the phase stays `[!]` until all are `[x]`.

### 6. Post-Phase

Only with every Gate Checklist item `[x]` (else return to the first open one). Post-skills run as
subagents on the gate-verified state — read-only ones in parallel, code-changing ones after them.
A check already on the Gate Checklist is not run again, even if a post-skill lists it (`requesting-code-review` = the gate's Diff review).

### 7. Phase Completion (`[!]` → `[x]`)

1. **Verify Gate Checklist:** `python3 "$DEV_DIR/scripts/check-evidence.py" check` (reads the phase file) must exit 0. Any unchecked → STOP, return to it in step 5.
2. Mark `[x]` in ROADMAP.md (replacing `[!]`, dropping `@claim:`); `@spec:` and `@plan:` present (small phases have neither)
3. **Gate record:** append the phase file's `## CI` and `## Minor (deferred)` to `docs/gates/phase-<N>.md` (it holds the Gate summary); STATE.md stays untouched.
4. Delete `.dev/phase-<N>.md` and the phase's SDD workspace (`execution.md`).
5. Commit all of it at once: `roadmap: complete Phase N — <name>`
6. `git fetch`, then read `git show origin/<main>:<prefix>ROADMAP.md`: every phase of the milestone `[x]`/`[—]` there, this one counted as done → write `Milestone End pending: <milestone name>` into STATE.md, then Milestone End (`commands.md`)

### 8. Next Action

One status line, then the next phase — unless a halt from "The run" applies, the context hint included.

---

## Error Handling

A `[—]` phase is skipped in sequencing, its reason shown on status. `/dev check` and `/dev ui` handle
an active phase and their own failures themselves (`dev-check.md`, `ui-review.md`).

**Principle:** Never block for recoverable errors (unknown `@type:`, a skill not installed, a malformed `defaults` entry): warn and continue. Stop only for missing ROADMAP.md, broken YAML and "The run" halts.
