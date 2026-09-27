# Interview in rounds — step 4a, architectural phases

Origin of the technique: `grilling` from github.com/mattpocock/skills (MIT). The format is our own:
selection buttons instead of free text.

The interview replaces the "clarifying questions" step of brainstorming — not brainstorming itself.
Classification, approaches, design, spec and lock remain with `superpowers:brainstorming`.

## Procedure

1. **Read what exists:** ADRs under `docs/adr/`, existing specs from the Roadmap, the milestone goal.
   Whatever is decided there is not asked again.
2. **Gather facts yourself.** Anything that code, configuration or documentation can answer is
   looked up (via subagent if needed) — never ask the user. If a search is still running, only the
   questions that depend on it wait; the rest are asked now.
3. **Decisions in rounds** via `AskUserQuestion`: up to four mutually **independent**
   questions per round, each with 2–4 options, the recommended one first with "(Recommended)" and a
   rationale in its description. Questions that depend on an open answer go into the
   next round. **Never as free text** with (a)/(b)/(c) — not even in the first round.
   If the round contains a question with a UI/UX side (definition in `companion.md`), the matching
   screen is written **before the `AskUserQuestion` call** (building blocks in `companion-screens.md`)
   and the companion URL is given; the options have the same names in the browser and in the terminal.
4. **End:** when no decision is left open. Summarize the decisions as a short list
   and have the user confirm it via `AskUserQuestion` ("Is this correct?"). If the user clicked
   through a round accepting only the recommendations and a later question depends on one of those
   answers, the summary explicitly names the most far-reaching of them.
5. **Hand-off to `superpowers:brainstorming`** with this note, followed by the list:

   > Clarification complete, result below. Classification: architectural. Start with the
   > approaches; do not ask clarifying questions that are answered below. The understanding is
   > confirmed — do not reflect it back again. The Visual Companion is already running (URL below).
   > Do not offer it; use it directly for every question with a UI/UX side and for
   > architecture diagrams; building blocks are in `companion-screens.md` of the `/dev` skill. Copy the list
   > into the spec as the section "Decisions from the interview".

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
