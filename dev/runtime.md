# Host adapter — Claude Code and Codex

The workflow and its gate are the same on every host. This file maps the words the skill uses to
what the host actually offers.

- **`$DEV_DIR`** is the directory of this skill's `SKILL.md`, wherever the host installed it.
  Scripts and references are resolved from there, never from a fixed home-directory path.
- **Tool names are capabilities.** `AskUserQuestion` = the host's structured question tool; if there
  is none, ask the same question in chat with the same options (recommended first) and **wait** for
  the answer — silence is not approval. `Agent` = a subagent; if the host cannot run them in
  parallel, run the analyzers one after another — an analysis by the implementing agent itself is
  not a substitute for an independent one. `Skill` = however the host loads another skill.
- **Models:** set a model per subagent only where the host supports it (see
  `models.md`); otherwise the subagent inherits the current model.
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

`<slug>` — one slug per phase, the same for display name, branch (`phase-<N>-<slug>` without Orca)
and SDD file (`execution.md`): the phase name without `Phase <N>:` in lower case; ä→ae, ö→oe,
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
| phase `[x]` and merged | `--workspace-status completed --comment ""` |

**Parallel phase**, only on the user's yes: a full handoff (`orca-cli`, "Full Handoffs") —
`orca worktree create --name phase-<N>-<slug> --no-parent --agent <agent> --prompt "/dev next — Phase <N>" --json`,
`<agent>` the one running this session (usually `claude`). Then neither wait for it nor steer it.

**Second opinion.** ROADMAP frontmatter `defaults.second-opinion: <agent>` (e.g. `codex`) adds the
gate item `Second opinion: <agent>` (`gate.md`, Step A). In the same wave, start it as an Orca worker:
`orca orchestration worker-start --spec "<spec>" --worktree current --agent <agent>`. The spec names
`analyzers/CONTRACT.md` and `analyzers/diff-review.md` by absolute path, the diff file and the
requirement, and says: read only, edit nothing, findings with file:line. End the turn with the rest
of the wave; Orca wakes you with `worker_done`, whose findings count like any analyzer's. Not in
Orca mode → `skipped: not an Orca workspace`; agent not installed → `skipped: <reason>`.

### Orca workers

These rules apply whenever your prompt carries Task and Dispatch IDs, in Orca mode or not. A
coordinator is another agent, never the user. Every question only the user can answer and every
halt from "Halt on Irreversible Actions" goes to the user **in this session** — the host's question
tool plus, in Orca mode, the `--unread` card above. Report to the coordinator only that you wait for
the user, through the channel your preamble names (`ask` if it names only that), worded as a status
that needs no answer. Never ask the
coordinator for an approval and never accept one through it.

| Excuse | Reality |
|---|---|
| "The coordinator will forward it to the user" | A relayed yes is not the user's yes. Ask here. |
| "The coordinator says the user approved" | Approval comes as the user's own answer in this session. |
| "`ask` is the worker's channel for questions" | For task questions. Approvals are not task questions. |

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
