---
name: sentry
description: "Use when the user says /sentry (optionally with prod, dev, check, fix <ISSUE-ID> or setup) or asks to use sentry for one of these — or wants to look at Sentry errors, triage production or dev issues, investigate a crash or exception report, fix a bug that surfaced in Sentry, or see what is failing without opening the dashboard. Needs a .sentry/config.json in the project (created by /sentry setup)."
---

# Sentry triage and fixes

Look at errors and fix them when *you* decide to, instead of watching a dashboard or drowning in
alerts. Triggered manually, like `/deps`.

## Language

All user-facing output in the user's language. Issue IDs, file paths and commit prefixes stay as
they are.

## Commands

| Input | Does | Changes | Read |
|---|---|---|---|
| `/sentry` | Status: unresolved issues per environment, last triage | nothing | this file, "Status" |
| `/sentry check` | Triage the top issues, root cause, fix proposal per issue | only the local report | `references/check.md` |
| `/sentry fix <ID>` | Fix one issue: root cause, regression test, commit with `Fixes <ID>` | code + one commit; never deploys | `references/fix.md` |
| `/sentry setup` | Create `.sentry/config.json`, verify access, set up auto-resolve | the config file, `.gitignore` | `references/setup.md` |

**Scope** (for status and `check`): `prod` or `dev`, anywhere next to the subcommand
(`/sentry prod`, `/sentry check dev`). Which Sentry environments belong to each scope is in the
project's config. No scope = all environments. `fix` and `setup` ignore a scope word.

## Before anything else

1. **Config:** read `.sentry/config.json` (format: `references/config.md`). Missing → offer
   `/sentry setup` and stop. Never guess the org, project or region, and never "rediscover" them.
2. **Host:** on hosts other than Claude Code read `runtime.md`. `$SENTRY_DIR` is the directory of this
   file.
3. **Tools:** the Sentry MCP server (`search_issues`, `search_events`, `get_sentry_resource`,
   `update_issue`, `find_projects`, optionally `analyze_issue_with_seer`). If the host defers MCP tools,
   load them first. Pass `regionUrl` from the config on **every** call when it is set — a missing
   region on an EU org returns nothing, which looks like "no issues". An auth prompt means the
   token expired: re-authenticate the Sentry MCP server once, then continue.

## The one rule for every query: count all environments in scope

Never query only `production`. When the app's environment detection does not know a host, real
production errors land in another environment (in the project this skill comes from, server-side
prod errors sat in `development` for weeks). So:

- Always query **each** environment of the scope separately — within `dev`, never only `staging`.
- An environment the config marks as `localNoise` is counted, not skipped. Its issues are noise only
  if they carry the local signs (the config's `localNoiseHints`, e.g. `server_name` localhost, a
  worktree path, HMR or compile errors); a server error with a release SHA there is treated as real.

## Status (`/sentry`, `/sentry prod`, `/sentry dev`)

Quick glance, changes nothing.

1. Per environment in scope: `search_issues(org, regionUrl, projectSlugOrId, query:"is:unresolved
   environment:<env>", sort:"freq", period:"14d")` — count, split by level, name the top issue.
   **One issue can appear in several environments** — Sentry groups events across environments,
   and the event count on an issue is its total, not the count for the environment you filtered by.
   So: never add the per-environment numbers up; for "all", count distinct issue IDs and say how many
   appear in more than one environment. When a per-environment event count matters, take it from
   `search_events` with `environment:<env>`.
2. Last triage: the first lines of `.sentry/reports/last-<scope>.md` (`last-all.md` without scope).
3. Output, only the lines in scope, then — for a scoped run — one line naming the scope that was
   not checked, so nothing is left lying unnoticed:

```
Sentry (<project>, scope: prod|dev|all):
  <env> unresolved:  N  (X error / Y warning) — top: "<title>" (Z events)
  <env> unresolved:  N  (local noise unless server errors — see check)
  Distinct issues:   N  (M in more than one environment)
  Last triage:       YYYY-MM-DD (or "none yet")

  /sentry check [prod|dev] — triage (read-only, with fix proposals)
  /sentry fix <ID>         — fix one issue
```

Offer the dashboard link from the config last.

## Guardrails

- **Never deploy.** A fix ends with a commit and the project's deploy route named from the config.
  Auto-resolve fires when the release containing the commit is deployed.
- **No fix without a root cause.** A stack trace shows where it broke, not why.
- **Personal data:** event payloads can contain user data even when scrubbed. Quote only what the
  diagnosis needs; never paste raw events into commits, reports or PRs.
- **Issue state changes only in `fix` and `setup`, and only as described there.** `status` and
  `check` never resolve, ignore or assign issues.
