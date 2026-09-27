# Host adapter — Claude Code and Codex

- **`$SENTRY_DIR`** is the directory of this skill's `SKILL.md`, wherever the host installed it.
- **Sentry access** is a capability: the Sentry MCP server where the host has it (Claude Code and
  Codex both support MCP). Without it, the Sentry CLI or the REST API with a token from the
  environment can answer the same questions (issues per environment, issue details, resolve).
  Never paste a token into chat, files or commands that end up in logs.
- **Questions** go through the host's structured question tool if it has one; otherwise ask in chat
  and wait for the answer.
- **Slash commands:** `/sentry check` names a workflow; without slash commands the user asks for it
  by name ("use sentry: check").
