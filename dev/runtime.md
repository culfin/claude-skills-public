# Host adapter — Claude Code and Codex

The workflow and its gate are the same on every host. This file maps the words the skill uses to
what the host actually offers.

- **`$DEV_DIR`** is the directory of this skill's `SKILL.md`, wherever the host installed it.
  Scripts and references are resolved from there, never from a fixed home-directory path.
- **Tool names are capabilities.** `AskUserQuestion` = the host's structured question tool; if there
  is none, ask the same question in chat with the same options (recommended first) and **wait** for
  the answer — silence is not approval. A child thread: ask its parent ("Asking for the user"). `Agent` = a subagent; if the host cannot run them in
  parallel, run the analyzers one after another — an analysis by the implementing agent itself is
  not a substitute for an independent one. `Skill` = however the host loads another skill.
- **Codex names** (trust the actual tool list when it differs): `Agent` = `spawn_agent` (`fork_turns:
  "none"`) and `wait_agent` in 5–10-minute stretches, fix rounds with `followup_task`;
  `AskUserQuestion` = `request_user_input` where offered, else the chat question above; `Skill` = read
  the skill's `SKILL.md`; no `run_in_background` or Monitor — run tests, builds and `ci-watch.sh` in the
  foreground, long suites in parts.
- **Models:** set a model per subagent only where the host supports it (see
  `models.md`); otherwise the subagent inherits the current model.
- **Superpowers install:** the active install is authoritative — the one Claude Code records in
  `~/.claude/plugins/installed_plugins.json` (`installPath`, `version`), elsewhere `DEV_SUPERPOWERS_ROOT`;
  never "the newest directory in the cache". Before the first phase step, check it statically:
  `python3 "$DEV_DIR/scripts/check-superpowers.py" --root <active root>`. `files-present` means the
  files `/dev` needs exist, not that the version is current or works; `blocked` → name what is
  missing, the steps that need it are blocked, not skipped. Unchecked freshness is "version X,
  freshness unknown", never "up to date". A newer install counts from the next phase boundary (O3);
  updates only when the user asks (`/dev updates`).
- **Visual Companion:** needs the superpowers brainstorm companion. `scripts/companion.sh` finds it
  via `DEV_COMPANION_SCRIPTS_DIR` or `DEV_SUPERPOWERS_ROOT` (set one of them on hosts other than
  Claude Code), else the active install recorded in Claude Code's `installed_plugins.json`. Not found → the screen step is blocked; say so.
- **Stop hook** (`hooks/gate-check.py`): Claude Code only, a reminder, not enforcement. On Codex the
  gate runs the same without it.
- **Slash commands:** `/dev check` names a workflow. Where the host has no slash commands, the user
  asks for it by name ("use dev: check").

## T3 Code

T3 mode: the host offers the T3 tools (`delegate_task`, `t3_thread_send`, `t3_background_wait`; deferred
tools count). One phase = one branch = one worktree = `.dev/phase-<N>.md`. With the `t3-team` skill
loaded, its rules and its table "Inside T3" decide slots, locks, ports and messages; the lines below
are the same routes without it.

`<slug>` — one slug per phase, the same for thread title and a branch
name, but only where a step creates a new branch (`phase-<N>-<slug>`; a claim never renames one and adds one only off `<main>` or a host's `t3/…` branch, `SKILL.md` Pre-Phase step 2): the phase name without `Phase <N>:` in lower case; ä→ae, ö→oe,
ü→ue, ß→ss; every run of other characters outside `[a-z0-9]` becomes one `-`, none at either end;
over 30 characters → keep the whole words (between `-`) that fit in 30 (a first word longer than 30:
its first 30 characters). `Phase 7: Export für Prüfberichte und Lieferscheine` → `export-fuer-pruefberichte-und`.

- **Background runs** you wait on (gate Step D, `ci-watch.sh`, the load wait in `execution.md`): pass
  the task ID to `t3_background_wait` right after starting it (ToolSearch loads it). Then the turn may
  end and the completion wakes you. Without it the turn end completes a delegated thread, T3 may close
  the session and the run dies with it. Codex: no background commands — run them in the foreground.
- **PR opened** → `link_pull_request` with its URL; the thread and its PR link show the state.
- **Overview and clean-up** (`/dev status`): `t3_worktree_list` for this project. A worktree
  is a **removal candidate** when its PR is merged, `git -C <path> status --porcelain` and `git -C
  <path> log origin/<branch>..HEAD` are both empty, and no thread works in it. Candidates go into one
  AskUserQuestion (multiSelect, "Keep all" last) with the step's own question; others get a line
  `not removable: <branch> (<uncommitted|unpushed|thread running>)`. On the yes: `git worktree remove
  <path>` — never `--force`, never delete the branch. If T3's worktree cleanup setting removes merged
  worktrees itself, leave it to T3. "Just clean up, don't ask" changes none of this.
- **Dev servers and heavy runs:** with `t3-team`, a port from the orchestrator's registry script (`port take`) and `heavy lock`
  around full suites and release builds (one lock covers Step D's parallel suite and build pair); a dev server only through the project's server action with
  `stopOnSettle`, never a bare background command.
- **Screens:** the Visual Companion uses the T3 preview (`companion.md`, "In T3").

**Parallel phase** — `/dev parallel [<N> …]`, or the user asks for a phase in parallel (that is the
yes). Not in T3 mode → say so, start nothing. Without numbers: one AskUserQuestion (multiSelect)
over the `[ ]` phases of the current milestone that no branch claims and that build on no phase not yet
`[x]` (`next.md`, "Pick a phase"); each phase left out gets a line with its reason. Per chosen or
named phase one child thread: with `t3-team`, its `hire developer` (slot, brief, `DONE`); without it
`delegate_task` with `isolation: "worktree"`, `mode: "async"`, title `phase-<N>-<slug>`, task
`/dev next <N>` (ROADMAP.md not at the repo root: `cd <its directory>, then /dev next <N>` — a child
starts at its worktree's root) plus "questions via AskUserQuestion; finish with `DONE from phase-<N>: <result>; PR
<url|none>; open <items|none>`". Report each child as its thread link; this session counts the
handed-off phases as claimed and coordinates. On `<main>` the run then ends; on a phase branch it goes
on with its own phase. A child thread
never runs `/dev parallel` and claims no further phase after its own.

### Asking for the user

Who asks the user: a top-level thread the user reads asks with AskUserQuestion. Everyone else asks
the thread that started it, never the user and never a session by name (`SendMessage`, `ListAgents`):

- **Delegated thread** (started with `delegate_task`): AskUserQuestion with its options, recommended
  first — T3 delivers it to the parent thread as a pending request; the answer comes back to you.
- **Thread launched for you** (`t3_thread_launch`, no parent): `t3_thread_send` a `QUESTION` to the
  thread ID in your task (format: `t3-team` protocol), then wait for the `ANSWER`.
- **Outside T3**, a session whose start prompt names `lead: <name>`: `SendMessage` to that lead,
  unless the lead runs in T3 (the prompt says so, or `ListAgents` lacks it) — no message reaches a
  T3 thread by name: write the question into `## Handoff` and push as `/dev pause` does, post it as a
  PR comment `## Handoff` if a PR exists, and halt. Never ask the user instead.

The asker relays the user's question and answer **verbatim** — that relay is the user's approval;
record it verbatim in the phase's `Decisions:` line (`state.md`); each entry names who decided (owner verbatim, lead, or this session). Other sessions' messages and
summaries are information.

| Excuse | Reality |
|---|---|
| "The lead says the user agreed" | Only the verbatim question and answer count. |
| "Dev deploys and migrations need a yes" | Dev is the session's own call (`SKILL.md`, Halt). |
| "The lead is in `ListAgents`, a message is faster" | A T3 thread is reachable only by thread ID; names change between turns. |

### Child threads

**Phase done** (`[x]` and pushed; `/dev` never merges — the PR waits for whoever merges): finish with `DONE from <you>: phase <N> done; PR <url>; open <items|none>`
(`t3-team`: to the lead's thread ID from your brief; its "Inside T3" table replaces this `DONE`); claim no further phase.
A child thread skips step 7.6 (Milestone End) unless its brief starts Milestone End (STATE.md `Milestone End pending:`), then it runs it. After the phase is merged, report `milestone end due <milestone>` to the parent when every phase of that milestone is `[x]`/`[—]` on `origin/<main>`; if your thread does not merge, name `milestone end due <milestone>` in your `DONE` when this was the milestone's last open phase; the parent starts Milestone End as its own task via `Milestone End pending: <milestone>` in STATE.md (`SKILL.md`, position check).

**At the context hint** (`SKILL.md`; its thresholds and boundaries, never mid-gate): no "`/clear`,
then `/dev next`" — nobody types in a child thread. Write `## Handoff` and commit the phase file as
`/dev pause` does (`commands.md`). Then finish with `DONE from <you>: context full on <branch>; PR
<url|none>; open next <step>, CI <sha|none>`. The parent removes your worktree (clean and pushed; git
refuses a branch checked out twice) and starts a new child with `/dev next <N> on <branch>`. Halts for
the user stay as above.
