# Slim gate — opt-in

Only with ROADMAP.md frontmatter `defaults.gate: slim` (under `t3-team` also `docs/team.md` line
`Gate: slim`). Replaces `gate.md`'s checklist, Steps A–C and `## Minor (deferred)`; the rest stays.

1. **Deterministic checks first:** Step D; red → fix (not a round). **Green rule:** every test or guard
   script the project defines (`package.json` `test:*`/`check:*`/`guard*`, the jobs CI runs) that the diff
   can reach also runs at the gate commit. A red one is a gap for a fix round, never a note or a follow-up;
   pre-existing only with the same red run on the phase base (both runs as evidence). Still red after
   round 2 → `Open:`, `[!]`: a phase with a red test or guard is not done.
2. `gate-tier.py … --slim`: line 1 and `- …` as usual; its `+ <trigger>: <why> → <item>` lines add
   items (`gate.md` Step A rows, correctness only, criticals and at most 3 notes). Checklist: Step D's
   items, `Code review`, those items, summary, commit, headed `<!-- gate: slim; triggers: <… | none> -->`.
3. Commit, then in one message `Code review` — **exactly one fresh-context reviewer**, Claude Code's
   built-in `/code-review` (Skill `code-review`), args `high <phase base>...HEAD — review against the
   acceptance criteria in <phase file or @spec: path>; correctness gaps only, no style, no hypothetical
   cases` — and the added items in parallel, **each its own Agent dispatch** with its `gate.md` Step A
   analyzer (fresh context, never the main session's own reading; evidence: the agent's `Result:` line —
   an item ticked without one is not done). No `code-review` → `gate.md`'s Spec checker without (b)
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
