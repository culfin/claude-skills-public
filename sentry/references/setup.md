# `/sentry setup`

Setup runs without `.sentry/config.json`. It configures local routing, verifies read access and
explains release integration. It does not install integrations, modify remote settings or commit.

1. Discover the configured Sentry connection and its schema per [runtime](../runtime.md). Use
   organization discovery or an explicit user-provided installation to obtain the correct region,
   then project discovery. An auth error is not an empty project list. If several targets match,
   present their identities and ask; never choose the first result automatically. Without access,
   explain the blocker; do not create a fictitious validated configuration.
2. If config exists, validate it per [config](config.md), verify its target, and propose a minimal
   update. Preserve existing scope assignments unless the user changes them. For a new config,
   confirm org/project, verified region/default route and actual short-ID prefix separately.
   An empty project may need the prefix supplied/verified through project settings; do not create
   a test incident just to learn it.
3. Retrieve the project's environment inventory, including hidden environments where supported.
   Ask for production/dev mappings and local-noise evidence that cannot be inferred reliably.
   Never infer business criticality from an environment name alone. Mark incomplete discovery;
   future unknown environments remain visible through the collection workflow.
4. Show the concrete non-secret config and intended ignore change. If the user has already chosen
   these values, write them under setup authorization without asking again. Only unresolved
   target/mapping choices need a reply first. Update atomically; refuse symlink escapes from the
   project and preserve unrelated keys. Add the project-root `.sentry/reports/` ignore rule if
   absent. Check ignore effectiveness: previously tracked reports remain tracked; report them
   without automatically removing files or rewriting history. Do not stage or commit anything.
5. Verify a bounded read against the chosen project with the discovered region and a fixed window.
   A successful empty result verifies access, not environment correctness or complete health.
   Report config written and access verified separately; never claim verification on an error.
6. **Release integration is a separate readiness check.** Inspect existing repository integration,
   commit association and release/deploy metadata when readable. A release whose name resembles a
   SHA alone proves none of these. Explain which prerequisites for `Fixes <ID>` are verified and
   the actual lifecycle semantics. If not configured, give the user concrete setup steps; do not
   install integrations or change release pipelines without that additional instruction.
7. Alerts are optional and separate. Suggest one only when useful; do not create a notification,
   recipient, webhook or recurring monitor as part of ordinary setup.

Afterward report target, scopes, unknown mappings, modified local files, access result and release
integration readiness. Existing authorization for a concrete integration change can be honored,
but a generic setup request is not authorization to change external organization settings.
