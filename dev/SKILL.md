---
name: dev
description: "Use when user says /dev, /dev next, /dev init, /dev status, /dev skip, /dev add, /dev reorder, /dev review, /dev pause, /dev debug, /dev check, /dev ui, or /dev updates. Also use when the user asks to use dev for one of these, and at session start when ROADMAP.md exists in project root (then only a one-line status)."
---

## Language

**All user-facing text is in the user's language** (the one they write in or ask for): AskUserQuestion
labels and options, status reports, errors, commit message bodies, STATE.md and ROADMAP.md prose.
Technical terms, skill names, paths, YAML keys and conventional-commit prefixes (`roadmap:`, `feat:`) stay English.

---

# /dev — Milestone Orchestrator

Manages a project's ROADMAP.md and runs its phases one after another: clarify, specify, implement,
gate. Implementation and review are delegated to subagents; the main session only steers.

## Command Router

| Input | Section | Read |
|-------|---------|------|
| `/dev` or `/dev next` | Session Start | this file |
| `/dev init` | Roadmap Creation | `roadmap-creation.md` |
| `/dev status` | Status Display | `commands.md` |
| `/dev skip` | Skip Phase | `commands.md` |
| `/dev add` | Add Phase/Milestone | `commands.md` |
| `/dev reorder` | Reorder Phases | `commands.md` |
| `/dev review` | Pre-Release Review | `commands.md` |
| `/dev debug` | Debug Flow | `commands.md` → `debugger.md` |
| `/dev pause` | Pause Session | `commands.md` |
| `/dev check` | Standalone Quality Gate | `dev-check.md` → `gate.md` |
| `/dev ui [scope]` | UI review and rework | `ui-review.md` |
| `/dev updates` | Decide on held-back skill updates | `updates.md` → `sources.md` |

## When NOT to Use

- Single-task requests ("fix this bug", "add a button") — use superpowers directly
- Projects without milestones — overkill for small fixes
- When user explicitly asks to skip the orchestrator

---

## Files of This Skill

`$DEV_DIR` is the directory of this `SKILL.md`; all paths below are relative to it. Load only what
the current step needs.

| File | Holds | Read when |
|---|---|---|
| `execution.md` | How a phase is implemented: small phase, parallel waves, task reviews, merge | Step 4c and its resume |
| `gate.md` | Quality gate: tier, steps A–D, checklist, evidence, gate commit, CI in background, phase types, project commands | Gate entry, resuming `[!]`, CI status, `/dev check` |
| `commands.md` | Status, skip, add, reorder, pause, debug, milestone end, pre-release review | Router; Milestone End; unexplained build/test failure (Debug Flow) |
| `models.md` | Which model tier each subagent gets | Before dispatching subagents |
| `state.md` | What STATE.md holds and when each part changes | Before writing STATE.md |
| `companion.md` | Visual Companion: triggers, server start, "Show screen" | Before the first screen of a session |
| `companion-screens.md` | Look and building blocks of the screens | When writing a screen |
| `runtime.md` | Host adapter: `$DEV_DIR`, tool names, Codex vs Claude Code | Once per session, at the first explicit `/dev` run |
| `superpowers.md` | Active superpowers install, static check, update path | Before the first phase step; before a plugin update |
| `befragung.md` | Bundled round at run start; interview in rounds; ADRs | Run start; 4a, architectural phase |
| `tech-stack-triggers.md` | Which tech, design and security sources fire when | Steps 4a, 4c and gate Step A |
| `roadmap-creation.md`, `dev-check.md`, `e2e-testing.md`, `debugger.md` | One flow each | As named in the router or gate |
| `stack/INDEX.md`, `stack/docs.md` | Stack detection; stack sources and docs per trigger | Detection once (section 1); else only matching rows via `tech-stack-triggers.md` |
| `design/INDEX.md` | Design guideline or source per trigger | Only matching rows, via `tech-stack-triggers.md`, `ui-review.md`, companion "UI decision" |
| `analyzers/CONTRACT.md` | How each analyzer subagent is dispatched and reports | With every analyzer dispatch |
| `brag.md` | When the launch video (brag) is offered and how it runs | Milestone End step 7, Pre-Release Review step 6 |
| `ui-review.md` | `/dev ui`: screenshots, analyses, `UI-REVIEW.md`, rework after approval | `/dev ui` |
| `sources.md`, `updates.md` | Contract per referenced skill; `/dev updates` and its queue | `/dev updates`; adding a use of a foreign skill |

**Visual Companion:** shows only the product's user interface (mockups, states, real screenshots — never roadmaps, plans, architecture or findings), used without asking wherever this skill says **"Show screen"** (`companion.md`); a message pointing at a new or updated screen ends with its URL, other messages carry none.

---

## Tech-Stack-Aware Skills

**Detection** — once per session, at the first explicit `/dev` run: check the project root against
section 1 of `stack/INDEX.md` and store the ids as `$TECH_STACKS` (e.g. `[nextjs, shadcn, postgres]`).
`nextjs`, `shadcn` and `svelte` also count as **web**, `ios` as **Apple** (the `design/INDEX.md`
platform rows match on these). **Triggers** — `tech-stack-triggers.md` decides which tech, stack and
design sources load in clarification (4a), execution (4c) and as read-only reviews in the gate's
review wave (Step A); critical findings are fixed in gate Step B.

---

## Session Start

**Triggered by:** `/dev`, `/dev next`, or automatically when a new session starts and ROADMAP.md exists.

**Automatic trigger — one line, nothing else.** When the session starts in a project with ROADMAP.md
and the user has not typed `/dev` or asked to work on the roadmap: read ROADMAP.md (and STATE.md if
present) and print a single line —
`Roadmap: <milestone> — next: Phase N <name> [<state>]. Continue with /dev.` — then turn to what
the user actually asked. If `${DEV_UPDATES_DIR:-$HOME/.claude/dev-updates}/pending/*.json` exist
(count the files, read none), insert `, N skill updates waiting — /dev updates` before the final
period. No companion, no `AskUserQuestion`, no stack detection, no file writes.
The steps below run only on an explicit `/dev` / `/dev next` or a request to work on the roadmap.

1. **Read ROADMAP.md** from project root. If missing: "No ROADMAP.md found. Run `/dev init` to create one." Stop.
2. **Read STATE.md** from project root. If missing: create it from ROADMAP.md (derive progress, position, session info). If present: read its top through your branch's **Handoff** block and Session Continuity, and the current phase's entry; other sections only when a step needs them.
   Then `git fetch -q` and `python3 "$DEV_DIR/scripts/state-check.py" check`; show its findings. `size:`, `handoff:`, `archivable:` → offer archiving (Milestone End, step 5) in the bundled round; never rewrite without the user's yes.
3. **Detect tech stack** once per session (Tech-Stack-Aware Skills).
4. **Parse YAML frontmatter.** If malformed: show error, ask user to fix manually, stop.
5. **Parse phases:** Extract milestones (`##`), goals (`Goal:`), phases (checkbox items), annotations (`@type:`, `@skills:`, `@spec:`, `@plan:`, `@gate:`, `@claim:<branch>@<YYYY-MM-DD>`).
   - States: `[ ]` not started, `[~]` in progress, `[!]` gate pending (implementation done, quality gate outstanding), `[x]` done, `[—]` skipped
   - `@gate:` values other than `full` (the old `fast` and `ci-wait`) are ignored with a warning.
6. **Find current position:** STATE.md has `Milestone End pending: <name>` → Milestone End first. Else the first milestone with an incomplete phase; all done: "Roadmap complete!" Offer `/dev add` or `/dev review`.
   **Other sessions:** skip phases reported `claimed` unless the user picks one; `stale claim` → ask
   first; `done on <main>` → mark it as there, never redo it. Next free phase builds on a skipped
   one → halt and say so.
7. **Show summary** — in the terminal only (the companion is for the user interface, not for roadmaps):
   ```
   Milestone 2: UI Shell (3/5 phases done)
   Next: Phase 4 — Connections View (@type:ui)   [resume: gate, first open item "Spec checker"]
   Tech Stack: [nextjs, shadcn, postgres]
   Blockers: <from STATE.md, if any>
   CI in background: <open lines from STATE.md, if any>
   Updates: N skill updates waiting — /dev updates   (only if pending/ has files; count only)
   ```
   Show `@gate: full` when set. Show `$TECH_STACKS` only on first session start or if changed.
8. **Start the run — no menu.** `/dev` and `/dev next` go straight on: a `[!]` phase resumes the gate
   at the first open checklist item, a `[~]` phase resumes per "Resume logic" (4), otherwise the next
   phase starts. Looking without starting is `/dev status`.

---

## Roadmap Creation

**Triggered by:** `/dev init`

**→ Read `roadmap-creation.md` in this skill directory for the full interactive flow.**

Creates and commits ROADMAP.md + STATE.md through an interactive question flow.

---

## Skill Trigger Resolution

1. Read `@type:` from phase (e.g., `ui`)
2. Look up `defaults.phase-types.<type>.pre` and `.post` from frontmatter
3. Apply phase overrides:
   - `@skills:+pre[a]` → append to pre defaults
   - `@skills:+post[a]` → append to post defaults
   - `@skills:pre[a]` (no `+`) → replace pre defaults
   - `@skills:post[a]` (no `+`) → replace post defaults
4. Multiple combine: `@skills:+pre[a] @skills:+post[b]`
5. Unknown type → warn, continue with empty lists

Built-in phase types and the `@gate:` annotation (both shape the gate) are in `gate.md`.

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

A run works through the phases back to back until the milestone ends or a halt applies. At its
start, ask the bundled clarification round (`befragung.md`, "Bundled round at run start"). **The run
halts only for:**

- clarification questions only the user can answer (`befragung.md`);
- irreversible actions (section above);
- a gate finding still critical after 3 attempts (or 6 gate rounds in total, `gate.md` Step B), or a task still open after its 3 fix rounds (`execution.md`);
- the context hint (below);
- Milestone End (`commands.md`);
- plus the gate's own stops (`gate.md`): wrong branch at the gate commit, unclear staging, no
  authorized route for CI (once per run), a review item that timed out twice, a floor-guard
  critical that is not undone (needs approval).

CI `red` or `timeout` halts to repair (`gate.md`), then the run continues; `none` does not halt.

Everything else goes on without asking: no spec or plan approval, no "continue?" between steps or
phases — a pause before a plain "continue" decides nothing. Each phase ends with one status line;
details are in the spec, the plan and STATE.md.

**Context hint.** After each phase: if this session has completed 3 phases, or the host shows the
context above ~250k tokens, stop at the phase boundary with "Context is large — `/clear`, then
`/dev next`; the handoff is in STATE.md." — a large context is reread on every turn.

---

## Phase Execution

Order: milestone start → pre-phase → clarify (4a) → plan (4b) → execute (4c) → `[!]` (4d) → gate
(5) → post-phase (6) → `[x]` (7) → next phase or halt (8).

### 1. Milestone Start Check

First phase of new milestone → run `defaults.skills.milestone-start` as parallel Agent subagents. Missing skills → warn and skip.

### 2. Pre-Phase

1. **CI status first:** read every open line under `## CI in background` (`gate.md`). `red` or
   `timeout` → halt and repair before this phase starts.
2. Mark phase `[~]` in ROADMAP.md (Edit tool) with `@claim:<current branch>@<today>` (taking over replaces the claim); write `Phase base: <git rev-parse HEAD>` under the phase in STATE.md. Another session in this repo (`git worktree list`, or the user says so) → bring the claim to `<main>` at once as a tiny commit `roadmap: claim Phase N` (PR or push, as the project allows).
3. Resolve pre-skills (see Skill Trigger Resolution)
4. Dispatch pre-skills as parallel Agent subagents

### 3. Pre-Skill Handoff

Pass the paths of pre-skill output files to step 4a; read only the relevant findings.

### 4. Phase Cycle

**Resume logic:**
- Phase is `[!]` → skip directly to Quality Gate (step 5), read Gate Checklist from STATE.md to find remaining steps
- Phase is `[~]` with `@plan:` path on disk, or acceptance criteria ending in `Criteria complete.` (small phase; without that line if the phase already has commits) → execution (4c); the ledger says which tasks are done (`execution.md`, "Ledger")
- Phase is `[~]` with `@spec:` path on disk → planning (4b)
- STATE.md has `## UI review — approved findings` → those IDs are part of this phase: fix each to its criterion in `UI-REVIEW.md`, then clear it (`state.md`)
- Phase is `[~]` with neither, or with criteria lacking that last line → clarification (4a)

**4a. Clarification:**
1. **Classify:** architectural if the phase creates a new project or subsystem, changes how components interact, or changes interfaces that others build on; `@type: migration` always. When in doubt, architectural. For `@type: docs`, no interview.
2. **Small → write the draft straight into STATE.md** under the phase as `Acceptance criteria:`
   (format in `state.md`), closed by the line `Criteria complete.` — no approval round; the Spec checker and a resume read it there. Ask only
   questions whose answer changes what gets built, via `AskUserQuestion`, recommendation first with
   "(Recommended)"; look up facts yourself instead of asking.
3. **Architectural → interview in rounds per `befragung.md`** (incl. ADRs), then
   `superpowers:brainstorming` with the handoff note from `befragung.md` **and this override**: no
   section approvals, write and commit the spec, no spec review gate (`sources.md` O14). Its
   hand-off to `writing-plans` carries the 4b instruction. After the spec is committed: add `@spec:`
   to ROADMAP.md.

In both cases, include matching tech skills beforehand (`tech-stack-triggers.md`, "During
Brainstorming"). For questions with a UI/UX side, ensure the companion via the "Show screen"
procedure and pass along the companion sentences of the hand-off note (`befragung.md`, step 5).

**4b. Planning:** `superpowers:writing-plans` with "no execution-method question; do not start
execution — `/dev` does" (`sources.md` O15). Write and commit the plan, add `@plan:` to ROADMAP.md, go on to
4c — no plan approval.

**4c. Execution → read `execution.md`.** No separate verification step: gate Step D proves tests,
build and E2E on the final state.

**4d. Gate Transition (`[~]` → `[!]`):**
1. Mark phase `[!]` in ROADMAP.md (Edit tool)
2. Create the Quality Gate Checklist in STATE.md — tier and format in `gate.md`, "Tier" and "Gate Checklist"
3. Update STATE.md Last activity: "Implementation complete, Quality Gate starting"

`[!]` = implemented, gate not yet passed — the **only** path to `[x]`; `[~]` → `[x]` is **forbidden**.

### 5. Mandatory Quality Gate

**→ Read `gate.md`** (tier → review wave → bundled fix → Similar-bugs → tests and build → gate commit
`[gate-pass]` → CI in background). Every checkmark needs evidence; the phase stays `[!]` until all are `[x]`.

### 6. Post-Phase

Only with every Gate Checklist item `[x]` (else return to the first open one). Dispatch post-skills as
subagents on the gate-verified state — read-only analyses in parallel, code-changing ones after them.
A check already on the Gate Checklist is not run again, even if listed in `@skills:post[]`.

### 7. Phase Completion (`[!]` → `[x]`)

1. **Verify Gate Checklist:** `python3 "$DEV_DIR/scripts/check-evidence.py" check STATE.md` must exit 0 (the gate commit keeps the checked state). If any unchecked → STOP, return to first unchecked step 5.
2. Mark `[x]` in ROADMAP.md (replacing `[!]`, dropping `@claim:`), ensure `@spec:` and `@plan:` present (small phases have neither)
3. **Remove Gate Checklist** from STATE.md (the `## Quality Gate — Phase N` section). **The Gate summary is kept.**
4. **Update STATE.md**: Current Position, Progress table, Last activity, and replace your branch's **Handoff** block (`state.md`); copy the ledger's `minor (deferred)` lines to Blockers & Risks, then delete the phase's SDD workspace (`execution.md`)
5. Commit: `roadmap: complete Phase N — <name>`
6. All phases done in milestone? → write `Milestone End pending: <milestone name>` into STATE.md, then Milestone End (`commands.md`)

### 8. Next Action

Print one status line for the phase, then continue with the next phase — unless a halt from "The
run" applies, the context hint included.

---

## Phase Interruption

**Triggered by:** User says "drop it", "do something else", "stop", "cancel" or similar during an active `[~]` or `[!]` phase.

**Behavior:**
1. **Stop current work immediately,** including background implementers (TaskStop or the host's stop); record each as `interrupted` in the ledger (`execution.md`).
2. **AskUserQuestion** (single-select):
   - **Pause phase** (Recommended) — save progress in STATE.md, keep phase `[~]`/`[!]`, resume later with `/dev next`
   - **Skip phase** — mark `[—]` with reason, move to next phase
   - **Do something else** — pause via STATE.md, then handle the user's new request outside `/dev`
3. Pause and "something else": record what was in progress in STATE.md Session Continuity; status and checked gate items stay intact.
4. "Something else": do NOT resume on your own — only an explicit `/dev` or `/dev next` does.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Phase `[—]` found | Skip in sequencing, show reason on status. |
| `/dev check` with active phase `[~]`/`[!]` | Warn: "Phase N still active. Use `/dev next`." Stop. |
| `/dev check` + empty `$CHECK_SCOPE` + No | Not an error — the user cancelled. Stop without action. |
| `/dev check` + a step fails | Stop at that step, no check commit. |
| `/dev ui` with active phase `[~]`/`[!]` | Analyse and get approval only; the rework belongs to that phase (`ui-review.md`). |

**Principle:** Never block for recoverable errors (unknown `@type:`, a skill not installed, an `@skills` parse error): warn and continue. Stop only for missing ROADMAP.md, broken YAML and the halts in "The run".
