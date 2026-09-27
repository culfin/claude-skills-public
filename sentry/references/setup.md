# `/sentry setup` — one-time prerequisites

Check each step and guide the user through the ones that need the Sentry UI.

1. **Access.** Call `find_projects` (with the region if the org is outside the US). No answer or an
   auth error → authenticate the Sentry MCP server, then repeat. Note which region answered.
2. **Config.** If `.sentry/config.json` is missing, create it from what step 1 returned — org, the
   project slug (check it against real issue IDs; the wizard default is often wrong), region, issue
   prefix. Ask the user for what Sentry cannot tell: which environments are production, which are
   dev, which are usually local runs, and how the project deploys. List every environment Sentry has
   seen for the project (`search_events` grouped by `environment`) and make sure each one lands in a
   scope. Format: `config.md`. Show the file before writing it.
3. **Reports stay local.** Add `.sentry/reports/` to `.gitignore`. The config itself is committed.
4. **Auto-resolve** (needed for `Fixes <ID>`) — a user action: Sentry → Settings → Integrations →
   GitHub → install and connect the repository. Releases must carry commit information (e.g. the
   Sentry build plugin with the release set to the commit SHA); check that recent events show a
   release that matches a commit.
5. **Optional: one alert** as a safety net between manual runs — e.g. "new issue in production" to
   one address. Keep it to one; the point of this skill is to look deliberately, not to be paged.
