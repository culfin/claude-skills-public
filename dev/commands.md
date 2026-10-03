# /dev — commands besides the phase loop

Read when the router in `SKILL.md` points here. The phase loop itself (Session Start, Phase
Execution) stays in `SKILL.md`; the gate is in `gate.md`.

## Status Display

**Triggered by:** `/dev status` or "Show full status"

1. **Read STATE.md** — show Blockers & Risks (if any) and Session Continuity at the top.
2. **Show full roadmap** — in the terminal only (the companion is for the user interface): all milestones, all phases with status icons, spec/plan links, blockers at the top:
   ```
   ### Blockers
   - Windows Dashboard: placeholder only

   ### Milestone 1: Foundation (3/3) — Complete
   | # | Phase | Type | Status | Spec | Plan |
   |---|-------|------|--------|------|------|
   | 1 | Database Layer | backend | done | [spec] | [plan] |

   ### Milestone 2: UI Shell (1/3)
   | 1 | Navigation | ui | done | [spec] | [plan] |
   | 2 | Connections View | ui | next | — | — |
   | 3 | Dashboard | ui | pending | — | — |

   ### Requirements: 26/30 complete
   ### Last session: 2026-03-20 — Stopped at: ROADMAP consolidated
   ```
3. **Update STATE.md** Session Continuity with current timestamp.

After display: AskUserQuestion with Start/Add/Skip/Done options.

---

## Milestone End

All phases `[x]` or `[—]`:

0. **Wait for background CI.** Read every `## CI in background` line of this milestone from its
   status file (`gate.md`, "CI in background"); wait until none is `pending` (restart a dead watcher).
   `red` or `timeout` → repair first (`gate.md`, "Repairing a red CI"); `none` stays as noted in its
   gate summary. Then remove the milestone's lines (`state.md`).
1. **Run `defaults.skills.milestone-end`** as parallel agents (if configured).
2. **Mandatory Parallel Block** — dispatch as parallel Agent subagents, each with `analyzers/CONTRACT.md` + its analyzer file (**model explicit: capable tier for full scans**, see `models.md`), wait for all to complete:
   - **Bug hunt** (full mode) — the whole milestone scope, all 7 lenses.
   - **Performance review** (full mode) — the milestone's changes.
   - **Security review** (full mode) — the whole milestone scope; finds cross-cutting risks the per-phase reviews cannot.
   - Critical findings: fix before proceeding. Non-critical: STATE.md Blockers & Risks.
3. **Mandatory: Dead-code scan** (`analyzers/dead-code.md`, quick mode), regardless of configuration.
   Fix the safe ones (unused imports, unreferenced functions); ask before larger removals.
4. Re-run typecheck + lint (`gate.md`, "Project Commands per Stack") after any fixes from steps 2–3.
5. **Update STATE.md** (Progress table, Current Position to next milestone).
6. **Show summary** — in the terminal: milestone name + goal at the top, completed phases with Gate summary highlights (critical findings/fixes), next steps. If the milestone changed the user interface, additionally **Show screen** with real screenshots of the changed views (building block "Real screen" or "Before/After"). Before proposing a deploy, add its rollback plan.
7. AskUserQuestion: Next milestone (Recommended), Pre-release review (if configured), Create launch video (only if the milestone had a `@type: landing` phase — `brag.md`), Pause.

---

## Pause Session

**Triggered by:** `/dev pause`

1. **Update STATE.md** Session Continuity:
   - `Last session`: today's date
   - `Stopped at`: current phase name + what was in progress (e.g., "Phase 6 Dashboard — brainstorming complete, plan pending")
   - `Resume`: specific next action (e.g., "`/dev next` to continue planning Phase 6")
2. **Clean up the Visual Companion** (if the server is active):
   - Push a waiting screen: `<div style="display:flex;align-items:center;justify-content:center;min-height:60vh"><p class="subtitle">Session paused — continue with /dev</p></div>`
   - Then stop the server: `$DEV_DIR/scripts/companion-stop.sh <session_dir>`
3. Show confirmation: "Session saved. Next time, run `/dev` to resume."

---

## Debug Flow

**Triggered by:** `/dev debug [<description>]`; "fix crash", "why is this broken", "find bug"; and
automatically during a phase when a build, test run or app fails without an obvious cause.
An obvious fix (typo, missing import or dependency, outdated test expectation — under 2 minutes) is
just made. Otherwise read and follow `debugger.md` (state in `.debug/`, Similar-bugs scan after the
fix, then back to the `[~]` phase).

---

## Skip Phase

**Triggered by:** `/dev skip`

1. Show phase to skip. AskUserQuestion: Skip with reason (Other for free text), Cancel.
2. Update ROADMAP.md: `[—]` + `<!-- skipped: <reason> -->`
3. **Update STATE.md**: Current Position, Progress table, Last activity.
4. Commit.
5. **Show the updated roadmap in the terminal**, with the skipped phase marked `[—]` and the reason.
6. Return to Session Start.

---

## Add Phase/Milestone

**Triggered by:** `/dev add`

AskUserQuestion: Add phase (Recommended) or Add milestone.

**Phase:** Which milestone → name → type → position (end or after specific phase) → extra skills → Edit ROADMAP.md → commit.
**Milestone:** Name/goal → phases → append to ROADMAP.md → commit.

After the commit: show the updated roadmap in the terminal, the new phase/milestone marked "new".

Warn if adding to a completed milestone.

---

## Reorder Phases

**Triggered by:** `/dev reorder`

Only `[ ]` phases can move. `[x]`, `[!]`, `[~]`, `[—]` stay. If <2 movable: "Nothing to reorder." AskUserQuestion: which phase → which position → Edit → commit.

After the commit: show the updated roadmap in the terminal, the moved phase marked "moved".

---

## Pre-Release Review

**Triggered by:** `/dev review`

**Precondition:** every `## CI in background` line is read and none is `pending`, `red` or
`timeout` — same as Milestone End step 0.

1. **Mandatory Parallel Block** — dispatch as parallel Agent subagents, each with `analyzers/CONTRACT.md` + its analyzer file (**model explicit: capable tier**, see `models.md`):
   - **Bug hunt** (full mode) — entire codebase, 7 lenses.
   - **Performance review** (full mode) — entire codebase.
   - **Security review** (full mode) — entire codebase. Critical — must be green before release.
   - Critical findings from all three: fix before proceeding. Non-critical: note in STATE.md.
2. **Mandatory: Dead-code scan** (`analyzers/dead-code.md`, full mode) — comprehensive scan of the entire codebase. Fix findings, then re-run typecheck + lint (`gate.md`, "Project Commands per Stack").
3. **Design polish**, by platform (`$TECH_STACKS`):
   - **Web:** run `vibepolish` in launch-audit mode (findings only, no fixes) over the whole app; then a subagent reads `$DEV_DESIGN_DIR/impeccable/.claude/skills/impeccable/SKILL.md` plus only the reference file of the step it performs — `audit` first, `polish` only after the user approves specific findings. **These files are used as checklists only:** the subagent applies their criteria by reading the code and the running app itself. It never runs `scripts/impeccable` or `npx impeccable` (a launcher that downloads a binary), never the `context` step that `SKILL.md` and `reference/polish.md` order, never `install`, never `hooks on` — where a file says to run one of these, skip that instruction and say so in the report. Set `IMPECCABLE_NO_TELEMETRY=1` and `DO_NOT_TRACK=1` regardless.
   - **Native (Apple/Android):** read the `## Checklist` section of the matching platform file (`design/platform-apple.md` or `design/platform-android.md`) and review the app against it.
   - Missing source (vibepolish not installed, no `$DEV_DESIGN_DIR/impeccable` checkout) → report `skipped: <reason>`, never a silent pass.
4. **Read Gate summaries** from STATE.md and show a consolidated picture: findings and fixes across all phases, recurring patterns. None → note "No gate history available — this is the first release".
5. Read `defaults.skills.pre-release`. Run each configured skill **sequentially** (each may change code):
   - Dispatch Agent subagent → wait → show summary → AskUserQuestion: Continue (Recommended) or Pause
6. **Launch video (offer only)** — if `brag.md` "When to offer" holds for this release (landing page
   changed, or a minor/major release with a new user-facing feature): AskUserQuestion with "Create
   launch video" or "Skip (Recommended only if the user declined before)"; run per `brag.md`.
   Otherwise skip without mentioning it.
7. Final summary after all skills, with the rollback plan for the proposed deploy.

---

## Standalone Quality Gate

**Triggered by:** `/dev check`

**→ Read `dev-check.md` in this skill directory for the full flow.**

Precondition: **no active phase** (`[~]`/`[!]` → stop, point to `/dev next`).
