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
- **Models:** set a model per subagent only where the host supports it (see "Subagent Model
  Choice" in `gate.md`); otherwise the subagent inherits the current model.
- **Visual Companion:** needs the superpowers brainstorm companion. `scripts/companion.sh` finds it
  via `DEV_COMPANION_SCRIPTS_DIR` or `DEV_SUPERPOWERS_ROOT` (set one of them on hosts other than
  Claude Code), else the active install recorded in Claude Code's `installed_plugins.json`. Not found → the screen step is blocked; say so.
- **Stop hook** (`hooks/gate-check.py`): Claude Code only, a reminder, not enforcement. On Codex the
  gate runs the same without it.
- **Slash commands:** `/dev check` names a workflow. Where the host has no slash commands, the user
  asks for it by name ("use dev: check").
