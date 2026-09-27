# `.sentry/config.json`

One file per project, committed. It holds everything that differs between projects, so the skill
never has to guess. `/sentry setup` creates it; edit it by hand later.

```json
{
  "org": "your-org",
  "project": "your-project",
  "regionUrl": "https://de.sentry.io",
  "issuePrefix": "YOUR-PROJECT",
  "scopes": {
    "prod": ["production"],
    "dev": ["staging", "development"]
  },
  "localNoise": ["development"],
  "localNoiseHints": ["server_name is localhost", "stack paths under .worktrees/", "HMR or compile errors"],
  "deploy": {
    "dev": "the command or steps that deploy to staging",
    "prod": "the command or steps that deploy to production"
  },
  "dashboardUrl": "https://your-org.sentry.io/issues/?project=your-project",
  "notes": "How the app decides its environment, and anything a triage must know."
}
```

| Key | Required | Meaning |
|---|---|---|
| `org`, `project` | yes | Slugs as in the Sentry URL. The project slug is often **not** the wizard default (`javascript-nextjs`, …) — check the issue IDs. |
| `regionUrl` | for non-US orgs | e.g. `https://de.sentry.io`. Omit for US. Sent with every MCP call. |
| `issuePrefix` | yes | Prefix of short IDs (`YOUR-PROJECT-42`), used in `Fixes <ID>`. |
| `scopes` | yes | Sentry environments per scope word. Every environment the app reports must appear in some scope, or it is never looked at. |
| `localNoise` | no | Environments that are usually local runs. Counted, and checked for real server errors. |
| `localNoiseHints` | no | How to tell local noise from real errors in those environments. |
| `deploy` | no | Named in the fix report; the skill never runs it. |
| `dashboardUrl` | no | Offered at the end of status and check. |
| `notes` | no | Free text for the next person — e.g. where environment detection lives in the code. |

Reports go to `.sentry/reports/` (ignored by git): `last-prod.md`, `last-dev.md`, `last-all.md`, so a
dev run never overwrites the last production triage.
