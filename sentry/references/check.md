# `/sentry check [prod|dev]` — triage

Analyzes and proposes; changes nothing in Sentry and nothing in the repository. The only file it
writes is the local report.

1. **Collect.** Per environment in scope (all separately — see "The one rule" in `SKILL.md`):
   `search_issues(..., query:"is:unresolved environment:<env>", sort:"freq")`, top ~8 each. Also
   look at `firstSeen:-24h` for new issues — a fresh issue with few events can matter more than an
   old frequent one. Merge the lists by issue ID: an issue seen in several environments is one
   issue — report it once, with all its environments, and let the most important one (production
   before staging before local) decide its priority.
2. **Sort out local noise.** In `localNoise` environments, mark an issue as noise only when it shows
   the `localNoiseHints`. Everything else there is a real issue.
3. **Detail per issue** (`get_sentry_resource` on the issue): title, culprit, event and user counts,
   first/last seen, release, environment. A regression (resolved before, now back) goes to the top.
4. **Root cause for the one to three most important** (frequency × users affected × newness):
   locate the culprit in the code from the stack trace, read the surrounding code and the change
   history of that spot (`git log -L` or blame on the lines). `analyze_issue_with_seer` can give a
   starting point where the plan includes it — its answer is a hypothesis to check against the code,
   not a finding. Result: a concrete fix proposal in one or two sentences with `file:line`.
5. **Report** to `.sentry/reports/last-<scope>.md` (create the directory if needed):

   ```
   # Sentry triage YYYY-MM-DD (scope: prod|dev|all)
   ## <ID> — <title>   [priority: high/medium/low]
   Events: <n> · users: <n> · release: <sha> · last seen: <ts> · env: <env>
   Root cause: <checked explanation, or "hypothesis: …" if not confirmed in code>
   Fix: <proposal> — `<file>:<line>`
   ```

   No raw event payloads in the report (see "Personal data" in `SKILL.md`).
6. **In chat:** the priority list, `/sentry fix <ID>` as the next step, and for a scoped run the
   scope that stayed unchecked.
