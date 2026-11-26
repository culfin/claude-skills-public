# Clarification — bundled round at run start, interview in rounds for architectural phases

The interview is the conversation of step 4a (`SKILL.md`); the spec and its builder check follow it there.

## Procedure

1. **Read what exists:** ADRs under `docs/adr/`, existing specs from the Roadmap, the milestone goal.
   Whatever is decided there is not asked again.
2. **Gather facts yourself.** Anything that code, configuration or documentation can answer is
   looked up — never ask the user. If a search is still running, only the
   questions that depend on it wait; the rest are asked now.
3. **Decisions in rounds** via `AskUserQuestion`: up to four mutually **independent**
   questions per round, each with 2–4 options, the recommended one first with "(Recommended)" and a
   rationale in its description. Questions that depend on an open answer go into the
   next round. **Never as free text** with (a)/(b)/(c) — not even in the first round.
   If the round contains a question with a UI/UX side (definition in `companion.md`), the matching
   screen is shown **before the `AskUserQuestion` call** ("Show screen", building blocks in
   `companion-screens.md`); the options have the same names on the screen and in the dialog.
   **Core-rule phase** (`SKILL.md` 4a): the first question shows the `Domain model:` — Current and
   Intended side by side — and asks whether Intended is what the user means: "matches" or "differs"
   with the difference in their words, neither marked "(Recommended)": Intended is your draft, a
   recommendation invites a click-through. It asks about the rule, never about a solution such as a
   table design. Record the answer as `Confirmed: <who>, <date>`. Under t3-team the product role (via the
   project lead) confirms it.
4. **End:** when no decision is left open, or you can predict the answers to your next three questions. Summarize the decisions as a short list
   and have the user confirm it via `AskUserQuestion` ("Is this correct?"). If the user clicked
   through a round accepting only the recommendations and a later question depends on one of those
   answers, the summary explicitly names the most far-reaching of them.
5. **Hand-off to the spec** (`SKILL.md` 4a, step 3): the confirmed list goes into the spec verbatim as
   "Decisions from the interview"; nothing answered there is asked again.

## Bundled round at run start

A run goes through several phases without stopping, so the questions that are already foreseeable
are asked once, up front, instead of halting each phase for them.

1. Read only the remaining phases' lines in ROADMAP.md, their `Decisions:` lines included —
   never their specs or plans. Collect the decisions that will clearly be needed and that only
   the user can make — with the same filter as above: facts are looked up, not asked.
2. Ask them in one round: up to four independent questions per `AskUserQuestion` call, recommendation
   first with "(Recommended)", each labelled with its phase. More than four → further calls right
   away, still before the first phase starts. Questions with a UI/UX side follow procedure step 3.
3. Record each answer in ROADMAP.md on the phase's `Decisions:` line (`state.md`) — unclaimed phases
   and the own only; phases another session claimed get no question and no line.
4. Nothing foreseeable → no round. Questions that only appear later (from a spec, a finding) are
   asked when they appear; an architectural phase still gets its interview, minus what is decided.

## ADRs

- **Criterion** — all three must hold: hard to reverse, surprising without context, result
  of a genuine trade-off. "Do not suggest again" decisions explicitly count.
- **When:** as soon as a decision from the interview meets the criterion, offer it via `AskUserQuestion`
  ("Record as ADR?").
- **Format:** `docs/adr/NNNN-title.md`, numbered consecutively (highest existing number + 1);
  create the directory only with the first ADR. Content: heading and one to three sentences
  (context, decision, reason). "Rejected alternatives" only if the rejection is not
  obvious.
- The spec references the ADRs that came out of its interview.
