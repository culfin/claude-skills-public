# `/sentry fix <ID>` — fix one issue

Without an ID: take the most frequent unresolved production issue, or ask.

1. **Understand before changing.** Fetch the issue (`get_sentry_resource`): stack trace, culprit,
   release, tags, request context, breadcrumbs. Locate it in the code. Find the root cause — why the
   code got into that state, not only where it threw. If the project uses `/dev`, its debug flow
   (`/dev debug`) is the procedure; otherwise work hypothesis by hypothesis and confirm each against
   the code or a reproduction. A plausible story from the stack trace alone is not a root cause.
2. **Regression test first.** Write a test that reproduces the failure from the issue — same input
   shape, same state — and **see it fail** on the current code. If the failure truly cannot be
   reproduced in a test (environment-only, third-party outage), say so and why, and record what
   evidence replaces it; do not skip this silently.
3. **Fix surgically.** Only what the root cause needs. The test goes green; the project's typecheck,
   lint and test commands stay green. Also check the rest of the code for the same pattern once
   (the same fix may be needed in a sibling).
4. **Gate.** If the project uses `/dev`, run `/dev check` on the change before committing. Otherwise
   run the project's full test suite.
5. **Commit** with the auto-close reference in the message body: `Fixes <ID>` (e.g.
   `Fixes YOUR-PROJECT-42`). Stage only the files of this fix. Sentry resolves the issue when a
   release containing this commit is deployed — this needs the Sentry↔GitHub integration
   (`/sentry setup`). Without it: after the deploy, resolve it with `update_issue`, and tell the user.
6. **Do not deploy.** Show the diff and name the route from the config (`deploy.dev`,
   `deploy.prod`). Resolving on release instead of now is deliberate: if the error comes back after
   the deploy, Sentry reopens the issue as a regression, so the inbox stays honest.
