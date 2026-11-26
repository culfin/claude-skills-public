# Spec, plan and review reception — steps 4a/4b and fix loops

`/dev`'s own texts for what it once took from superpowers' brainstorming, writing-plans and
receiving-code-review (`sources.md` O14, O15). Read at step 4a (architectural phase), 4b, and before a fix round.

## Spec (4a, architectural phase)

After the interview (`befragung.md`), no approval round: write `docs/specs/<YYYY-MM-DD>-phase-<N>-<slug>.md`
with goal, the interview's confirmed list verbatim as "Decisions from the interview", scope and non-goals,
changes to data, interfaces and UI, acceptance criteria, risks. Nothing answered in the interview is asked again.

**Builder check:** one fresh subagent with `$DEV_DIR/vendor/brainstorming/builder-check-prompt.md` (domain and
spec path filled in). Its questions go to the user via `AskUserQuestion`, recommendation first (O2); answers go
into the spec, the calls you made yourself onto the phase's `Decisions:` line in ROADMAP.md. Commit the spec.

## Plan (4b)

Next to the spec: `docs/plans/<YYYY-MM-DD>-phase-<N>-<slug>.md` — tasks in order, each with the files it
touches, the decisions and signatures it fixes, the behaviour its tests must show (red first where
`execution.md` asks for it) and what it depends on. No code beyond signatures, no execution-method question.

## Review reception (every fixer)

Check each finding against the code before changing anything. Fix what holds; push back with reasons on what
does not (wrong premise, conflicts with the spec, makes things worse). Never agree blindly, never skip one silently.
