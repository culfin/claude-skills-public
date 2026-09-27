# `/sentry check [prod|dev]`

Read [collection](collection.md). This workflow proposes fixes; it never edits source, changes
Sentry state or creates tickets. It may save a sanitized report unless the user requests no writes.

1. Collect frequent, fresh and regressed issues with explicit scope, time window and coverage.
   Deduplicate and classify representative events; keep real server errors in local-noise
   environments. Rank severity and affected user flows before raw frequency.
2. Investigate the one to three most important issues. Verify issue/project identity, relevant
   event environment, release, stack trace and source-map quality. Map the release to repository
   commit metadata; a release name is not necessarily a Git SHA. Read deployed source/history
   without resetting the user's checkout, then compare with current code. Mark mapping uncertainty.
3. State confirmed cause only when code and reproduction or equivalent evidence support it.
   Otherwise state the hypothesis and the next discriminating check. Seer output, if authorized,
   is supporting evidence, not a verdict. Distinguish already-fixed-but-not-deployed issues from
   fixes still needed. Proposals give current file/line only when verified, otherwise identify
   the missing source mapping instead of inventing a location.
4. Prepare the report below. Include issue links and short sanitized summaries; remove sensitive
   values from titles, URLs and copied error text too. Use invented equivalent inputs in examples.
5. Before saving, verify `.sentry/reports/` is ignored by Git and resolves inside the project,
   with no symlink redirection. If it is not ignored, keep the report in chat and offer setup;
   check does not edit `.gitignore`. Never overwrite a tracked report. Archive an existing local
   `last-<scope>.md` to a unique timestamp/run name, then atomically replace the last report. An
   archive/write failure leaves the previous report intact and is reported. Partial runs get a
   clearly labelled partial report, never a success header. Status never writes reports.
6. Show prioritized findings, limitations and `/sentry fix <ID>` for the chosen candidate.

```text
# Sentry triage — <UTC timestamp> — scope <prod|dev|all>
Target: <org/project> · Window: <start> to <end>
Coverage: <complete query / sampled triage / partial; failed and unchecked areas>
Queries: <tools, filters, page/aggregate evidence; no credentials>

## <issue ID> — <sanitized title> — <priority> — <verified link>
Environments: <matched; unmapped; origin evidence>
Metrics: <value + exact scope/window, or unavailable>
Evidence: <event IDs, release and verified source revision; no raw payload>
Cause: <confirmed / hypothesis / already fixed in current code>
Proposal: <minimal change and verified source location, or next investigation>
Verification needed: <regression test or equivalent evidence>
```
