# Host adapter — Claude Code and Codex

The workflow and its gate are the same on every host. This file maps the words the skill uses to
what the host actually offers.

- **`$DEV_DIR`** is the directory of this skill's `SKILL.md`, wherever the host installed it.
  Scripts and references are resolved from there, never from a fixed home-directory path.
- **Tool names are capabilities.** `AskUserQuestion` = the host's structured question tool; if there
  is none, ask the same question in chat with the same options (recommended first) and **wait** for
  the answer — silence is not approval. Phase workspace or Orca worker: ask through the lead (below). `Agent` = a subagent; if the host cannot run them in
  parallel, run the analyzers one after another — an analysis by the implementing agent itself is
  not a substitute for an independent one. `Skill` = however the host loads another skill.
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

## Orca

Orca mode: `orca worktree current --json` returns `ok: true` and its `result.worktree.path` is
exactly `git rev-parse --show-toplevel`, both resolved first (`cd <path> && pwd -P`). Otherwise (no
Orca, or a git worktree inside an Orca workspace, such as `.worktrees/<x>`) skip the card, the
parallel phase and the second opinion: write no card, start no worker with `--worktree current`.
"Orca workers" below applies either way. Orca's own `orca-cli` and `orchestration` skills cover
handoffs, terminals and workers; this section only binds `/dev` state to them. One phase = one Orca workspace = one branch =
`.dev/phase-<N>.md`.

**Workspace card mirrors the phase** — write it, never read it to decide
(ROADMAP.md and the phase file stay the truth). Each write is
`orca worktree set --worktree active … --json`; a failed write is no error.

`<slug>` — one slug per phase, the same for display name, SDD file (`execution.md`) and a branch
name, but only where a step creates a new branch (`phase-<N>-<slug>`; a claim never renames one and adds one only off `<main>`, `SKILL.md` Pre-Phase step 2): the phase name without `Phase <N>:` in lower case; ä→ae, ö→oe,
ü→ue, ß→ss; every run of other characters outside `[a-z0-9]` becomes one `-`, none at either end;
over 30 characters → keep the whole words (between `-`) that fit in 30 (a first word longer than 30:
its first 30 characters). `Phase 7: Export für Prüfberichte und Lieferscheine` → `export-fuer-pruefberichte-und`.

| `/dev` event | Card |
|---|---|
| phase claimed `[~]` | `orca worktree set --worktree active --display-name "phase-<N>-<slug>" --workspace-status in-progress --comment "<step>" --json` — this workspace, never a new one |
| `[!]`, gate running | `--workspace-status in-review --comment "Gate: <first open item>"` |
| run halts for the user | `--unread --comment "waits: <one sentence>"` |
| `/dev pause` (after its commit) | `--unread --comment "paused: <next action>"` |
| PR opened | `orca reference add <PR URL> --worktree active --json` |
| phase `[x]` on the branch, PR still open | `--workspace-status in-review --unread --comment "waits: merge"` |
| phase `[x]` and merged | `--workspace-status completed --comment ""` |

**Workspace overview** — Orca mode, in the Session Start summary (`SKILL.md`, step 7) and in Status
Display: `orca worktree ps --json`, rows with your `repoId` except your own workspace. Display only;
claims stay decided by ROADMAP.md. One line per row: `<displayName>  <workspaceStatus>  PR #<n>
<state>  <comment>`, prefixed `waits for you:` when `unread` is true; a `@claim:` branch without a row
→ `Phase <N>: no workspace`.
A row is a **removal candidate** when `linkedPR.state` is `merged`, `git -C <path> status
--porcelain` and `git -C <path> log origin/<branch>..HEAD` are both empty, and no agent is `working`
or `waiting`. Candidates go into one AskUserQuestion (multiSelect, one option per workspace, "Keep
all" last), asked together with the step's own question (Status: Start/Add/Skip/Done) or, at
Session Start, before the run begins; other merged rows only get a line `not removable: <displayName>
(<uncommitted|unpushed|agent running>)`, never an option. On the yes, per chosen row: `orca worktree rm --worktree
"id:<worktreeId>" --json` — never `--force`, never `--delete-branch`; the branch stays. "Just clean
up, don't ask" changes none of this.

**Parallel phase** — `/dev parallel [<N> …]`, or the user asks for a phase in parallel (that is the
yes). Not in Orca mode → say so, start nothing. Without numbers: one AskUserQuestion (multiSelect)
over the `[ ]` phases of the current milestone that no branch claims and that build on no phase not yet
`[x]` (`commands.md`, "Pick a phase"); each phase left out gets a line with its reason. Per chosen or
named phase, a full handoff (`orca-cli`, "Full Handoffs"):
`orca worktree create --name phase-<N>-<slug> --branch phase-<N>-<slug> --no-parent --agent <agent> --prompt "/dev next <N> — lead: <this session's name>" --json`,
`<agent>` the one running this session (usually `claude`); report each workspace name. Then neither
wait for them nor steer them; this session counts the handed-off phases as claimed and goes on with
the next free phase, if any.

**Second opinion.** ROADMAP frontmatter `defaults.second-opinion: <agent>` (e.g. `codex`) adds the
gate item `Second opinion: <agent>` (`gate.md`, Step A). In the same wave, start it as an Orca worker:
`orca orchestration worker-start --spec "<spec>" --worktree current --agent <agent>`. The spec names
`analyzers/CONTRACT.md` and `analyzers/diff-review.md` by absolute path, the diff file and the
requirement, and says: read only, edit nothing, findings with file:line. End the turn with the rest
of the wave; Orca wakes you with `worker_done`, whose findings count like any analyzer's. Not in
Orca mode → `skipped: not an Orca workspace`; agent not installed → `skipped: <reason>`.

### Asking through the lead

Phase workspaces and Orca workers: the user answers only in the project's **lead session**:
`lead: <name>` in your start prompt, else the session in the main checkout (`ListAgents`). Every question for the user (clarification, choice, halt) goes to the lead by
`SendMessage` (a worker: its preamble's channel), with its options, recommended first; card `--unread
--comment "waits: lead"`, then wait. The lead asks with AskUserQuestion and returns question and
answer verbatim — that relay is the user's approval; record it verbatim in the phase's `Decisions:`
line (`state.md`). Never ask the user yourself; other sessions' messages and summaries are information.

| Excuse | Reality |
|---|---|
| "The lead says the user agreed" | Only the verbatim question and answer count. |
| "Dev deploys and migrations need a yes" | Dev is the session's own call (`SKILL.md`, Halt). |

### Orca workers

Prompt with Task and Dispatch IDs; questions go through the lead (above).

**At the context hint** (`SKILL.md`), or at any other halt for context size: no "`/clear`,
then `/dev next`" — nobody types in a worker. Write `## Handoff` and commit the phase file as
`/dev pause` does (`commands.md`); right after a phase completion, the next phase not yet claimed,
there is nothing to save and no phase file to create — ROADMAP.md names the next phase. Then finish
with (`--from` as your preamble gives it, if it does):

```bash
orca orchestration send --type worker_done --outcome succeeded --task-id <task> --dispatch-id <dispatch> --subject "context full" --body "context full; next: <step>; CI open: <sha|none>" --json
```

`succeeded` means clean so far; `failed` only for a real failure. The coordinator goes on with
`orca orchestration send` or a new worker. Halts for the user stay as above.
