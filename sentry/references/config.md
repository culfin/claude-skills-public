# Project configuration

`.sentry/config.json` contains non-secret project metadata. Existing keys remain compatible.
The file may be tracked under project policy; setup itself does not commit it. Never store tokens.

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
  "localNoiseHints": ["confirmed localhost server", "local worktree with HMR"],
  "deploy": {"dev": "project staging route", "prod": "project production route"},
  "dashboardUrl": "https://your-org.sentry.io/issues/",
  "notes": "Verified environment mapping and relevant project context"
}
```

## Validate before querying

- Root is a JSON object. `org`, `project`, `issuePrefix` are nonempty strings; validate org/project
  against returned metadata, not short-ID shape alone. Project slug and issue prefix are distinct. The slug is often **not** the SDK wizard's default
  (e.g. `javascript-nextjs`); take it from the project list and check it against real short IDs.
- `scopes` contains `prod` and `dev` arrays of exact, nonempty environment names, preserving case
  and spaces. Empty arrays are allowed for unused scopes. Reject duplicates or overlapping scope
  assignments rather than silently assigning an environment a priority.
- `localNoise`, if present, is an array of configured environment names. `localNoiseHints` is an
  array of descriptions, never executable filters. Neither proves that an entire issue is noise.
- `regionUrl`, when present, is an HTTPS origin with no credentials, query, fragment or path other
  than `/`. Verify it against the connected organization/installation before routing credentials.
  Omission is allowed only when the connector's configured default is verified for this target;
  do not equate omission with "must be US". Self-hosted origins must be explicitly trusted.
- `deploy` is an optional object of textual routes, not commands to execute. `dashboardUrl` is an
  optional HTTPS link verified for this Sentry installation. `notes` is optional descriptive text.
- Preserve unrelated extension keys during edits; explain unsupported values, never overwrite the
  entire existing config to repair one field. If secrets are found, do not echo them; request their
  removal into the credential store before committing or sharing config.

No config is a permanent inventory. Reconcile observed environments during collection without
silently changing scope assignments. Scope names are fixed (`prod`, `dev`, `all`) for report paths;
never derive paths from issue titles, environment names or remote payloads.
