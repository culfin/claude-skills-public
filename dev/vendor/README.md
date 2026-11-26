# Vendored from superpowers

Copied unchanged from superpowers 7.0.2 (commit 22f0b463e7a5e579904dd6211a520321035526f7), MIT licence
(`LICENSE`, copyright Jesse Vincent), so `/dev` runs without the plugin installed:

- `sdd/` — `skills/subagent-driven-development/` (prompts, references, scripts; its `SKILL.md` renamed `GUIDE.md`
  so no host loads it as a skill, its frontmatter kept); `execution.md` uses the folder as `$SDD`.
  Where its texts name superpowers skills or "SKILL.md Model Selection", `/dev`'s rules win (`models.md`, `execution.md`).
- `brainstorming/builder-check-prompt.md` — the builder check of step 4a (`SKILL.md`).

Do not edit these files; `/dev`'s own rules live outside `vendor/` (`execution.md`, `SKILL.md`, `sources.md`).
Upstream changes are compared now and then (`sources.md`), never pulled automatically.
