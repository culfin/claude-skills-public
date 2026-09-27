# Host adapter — Claude Code and Codex

The workflow and its safety rules are the same on every host.

- **`$DEPS_DIR`** is the directory of this skill's `SKILL.md`, wherever the host installed it; the
  helper scripts are `$DEPS_DIR/scripts/*.py` (need `python3` and `gh`).
- **Tool names are capabilities.** A structured question tool, if missing, becomes the same question
  in chat — then wait for the answer. Subagents run one after another if the host cannot parallelise.
- **Slash commands:** `/deps merge` names a workflow; without slash commands the user asks for it by
  name ("use deps: merge").
