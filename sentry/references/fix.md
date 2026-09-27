# `/sentry fix <ID> [prod|dev]`

Fix exactly the selected issue. Without an unambiguous user-selected ID, ask before editing.
A scoped fix uses event evidence in that scope; if none exists, explain and ask rather than ignore
it. Read [collection](collection.md) for identity, environment and metric rules.

1. **Bind the issue to the source.** Fetch metadata and a relevant event, verify org/project and
   issue ID, then map the affected release through commit metadata/source maps. Release labels
   need not be SHAs. Compare the deployed revision with current source. If already fixed, explain
   the verified fix and pending deployment instead of making a duplicate change. If mapping is
   uncertain, investigate without claiming a confirmed cause or applying a speculative fix.
2. **Protect the worktree.** Inspect branch, HEAD, staged and unstaged changes. Reuse an appropriate
   clean task worktree or create an isolated checkout when changes would overlap. Never stash,
   reset or commit others' changes. Record the starting revision and changes owned by this task.
3. **Prove the cause.** Reproduce with sanitized, equivalent input/state. Write a regression test
   and observe it fail for the intended reason on the unfixed implementation, then pass with the
   fix. If ordinary testing cannot reproduce an environment-only failure, document the concrete
   alternative evidence and limits. Missing evidence blocks a claim of a verified fix; do not
   manufacture a test failure or treat an unrelated outage as a code defect.
4. **Fix and verify.** Apply the smallest cause-based correction and inspect sibling occurrences;
   only change siblings proven to share the cause, with tests. Discover the actual project build,
   lint/typecheck and test commands. Run relevant integration/UI coverage, not just unit tests
   renamed as E2E. Known unrelated failures need the same cause reproduced on the unchanged base,
   with the changed behavior still covered; never call a limited result fully green.
5. **Use an existing gate once.** If the project adopts `/dev`, follow its debugging/quality flow
   and reuse checks only for the same source, scope and criteria. Do not run nested completion
   workflows or duplicate gate commits. An unavailable mandatory review stays open until an
   equivalent independent check is available. If CI is required, only the exact candidate and all
   required checks count; use an already authorized publication route, otherwise report the
   publication blocker. `/sentry fix` alone does not authorize pushing.
6. **Commit owned changes after local verification.** Stage explicit owned changes, inspect the
   staged diff (including previously staged content), and do not sweep in user edits even in a
   shared file. Integrate the issue reference into the workflow's existing final commit where
   possible. If a required gate is incomplete, a candidate commit may be prepared under that
   workflow, but must be reported as pending, never as passed. Preserve hooks; do not bypass them.
7. **Report distinct states.** Show issue link, cause evidence, diff summary, test results,
   candidate SHA, remaining gate checks and the configured deploy route as text. A tested candidate
   does not by itself prove a final commit, a particular commit message or a completed full gate;
   inspect those separately and never report a proposed action as already done. End here: no
   deployment, push, manual resolve, issue comment, assignment or alert change.

## Commit references and resolution

Use `Fixes <verified short ID>` only if the project's configured integration uses that reference
and the user has authorized that automatic lifecycle behavior (including existing setup approval).
Otherwise use a neutral `Sentry issue: <ID>` reference and explain that automatic resolution is not
configured/verified. Retain the reference through the project's squash/release process.

Do not promise that a commit resolves an issue exactly when production deploys. Concrete trap: if the
dev or staging pipeline creates the release that contains the commit (release = commit SHA on every
deploy), a `Fixes` reference can resolve the issue as soon as the fix reaches staging — while
production still runs the old code. Integration,
release/commit association and Sentry lifecycle settings determine when resolution occurs; these
are separate from a verified deployment to a particular environment. Inspect existing settings
and evidence, and report auto-resolution as configured, unverified or unavailable.

Manual resolution after a deployment is a separate authorized action, not a delayed side effect
of this command. Before such an action, verify the actual deployed release contains the fix,
consider all affected environments of the grouped issue, and re-read its current state. A dev-only
fix must not be used as proof that production recovered. Never automatically ignore or delete it.
