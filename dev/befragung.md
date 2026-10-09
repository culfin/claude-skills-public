# Clarification — bundled round at run start, interview in rounds for architectural phases

The interview replaces only the clarifying-questions step of `superpowers:brainstorming`; classification, approaches, design, spec and lock stay there.

## Procedure

1. **Read what exists:** ADRs under `docs/adr/`, existing specs from the Roadmap, the milestone goal.
   Whatever is decided there is not asked again.
2. **Gather facts yourself.** Anything that code, configuration or documentation can answer is
   looked up — never ask the user. In an existing codebase, first dispatch 2–3 parallel read-only explorers (cheap tier; angles: entry points and data flow, similar features and conventions, tests and integration points), each returning at most 10 key files with one-line reasons; read them before asking. Skip for new projects. If a search is still running, only the
   questions that depend on it wait; the rest are asked now.
3. **Decisions in rounds** via `AskUserQuestion`: up to four mutually **independent**
   questions per round, each with 2–4 options, the recommended one first with "(Recommended)" and a
   rationale in its description. Questions that depend on an open answer go into the
   next round. **Never as free text** with (a)/(b)/(c) — not even in the first round.
   If the round contains a question with a UI/UX side (definition in `companion.md`), the matching
   screen is written **before the `AskUserQuestion` call** (building blocks in `companion-screens.md`)
   and the text before the call ends with the companion URL (the dialog can cover earlier output); the
   options have the same names in the browser and in the terminal.
4. **End:** when no decision is left open, or you can predict the answers to your next three questions. Summarize the decisions as a short list
   and have the user confirm it via `AskUserQuestion` ("Is this correct?"). If the user clicked
   through a round accepting only the recommendations and a later question depends on one of those
   answers, the summary explicitly names the most far-reaching of them.
5. **Hand-off to `superpowers:brainstorming`** with this note, followed by the list:

   > Clarification complete, result below. Classification: architectural. Start with the
   > approaches; do not ask clarifying questions that are answered below. The understanding is
   > confirmed — do not reflect it back again. The Visual Companion is already running (URL below).
   > Do not offer it; use it directly for every question with a UI/UX side — and only for those
   > (no plans, approaches or architecture diagrams on screens); building blocks are in
   > `companion-screens.md` of the `/dev` skill. Every message that shows a new or updated screen, or
   > asks about one, ends with this URL on its own line, verbatim; status messages carry none. Copy the list
   > into the spec as the section "Decisions from the interview".

## Bundled round at run start

A run goes through several phases without stopping, so the questions that are already foreseeable
are asked once, up front, instead of halting each phase for them.

1. Read only the remaining phases' lines in ROADMAP.md and the `Decisions:` already in STATE.md —
   never their specs or plans. Collect the decisions that will clearly be needed and that only
   the user can make — with the same filter as above: facts are looked up, not asked.
2. Ask them in one round: up to four independent questions per `AskUserQuestion` call, recommendation
   first with "(Recommended)", each labelled with its phase. More than four → further calls right
   away, still before the first phase starts. Questions with a UI/UX side follow procedure step 3.
3. Record each answer in STATE.md under its phase as `Decisions:` (`state.md`, "Run blocks").
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
