# Slim gate — opt-in

Only with ROADMAP.md frontmatter `defaults.gate: slim` (under `t3-team` also `docs/team.md` line
`Gate: slim`). Replaces `gate.md`'s checklist, Steps A–C and `## Minor (deferred)`; the rest stays.

1. **Deterministic checks first:** Step D; red → fix (not a round).
2. `gate-tier.py … --slim`: line 1 and `- …` as usual; its `+ <trigger>: <why> → <item>` lines add
   items (`gate.md` Step A rows, correctness only, criticals and at most 3 notes). Checklist: Step D's
   items, `Code review`, those items, summary, commit, headed `<!-- gate: slim; triggers: <… | none> -->`.
3. Commit, then in one message `Code review` — **exactly one fresh-context reviewer**, Claude Code's
   built-in `/code-review` (Skill `code-review`), args `high <phase base>...HEAD — review against the
   acceptance criteria in <phase file or @spec: path>; correctness gaps only, no style, no hypothetical
   cases` — and the added items in parallel. No `code-review` → `gate.md`'s Spec checker without (b)
   and effect probe, evidence `substitute: <reason>`. Fill `Criteria:` from Step D's tests; an uncovered
   criterion is a gap. Similar-bugs scan only after a fixed critical.
4. **At most 2 fix rounds.** A round is one fix dispatch with every in-spec gap plus `Fix review`
   (`/code-review high <reviewed sha>...HEAD`, and the items that found something), or a code change
   forced by red Step D (CI repair after the gate: `ci.md`). Every round counts: tick `round <k>: <result>` with `check-evidence.py mark`,
   which refuses round 3. Still a gap after round 2 → **no third round**: push, open or keep the PR
   (`ci.md`), list each gap under `Open:`, leave `[!]`, halt for the user (child thread: the lead).
5. A finding outside the spec, a pre-existing one or an unfixed note is **never a ROADMAP.md milestone
   or phase**: `python3 "$DEV_DIR/scripts/followup-issue.py" --severity <low|medium|high> --title
   "<file>: <defect>" --body-file <file>` (high: critical; medium: wrong result) dedupes against open
   `followup` issues; its output line goes under `Follow-ups:`.

The gate summary adds:

```markdown
- Gate: slim — triggers: <… | none>; rounds: <0|1|2>
- Follow-ups: <#12 severity:medium — <title>; not filed: <reason>; … | none>
- Open: <gap — file:line; … | none>
```
