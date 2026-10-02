# Analyzer contract

Every file in `analyzers/` is an instruction for **one read-only subagent**. The gate (`gate.md`)
dispatches it; `/dev check`, milestone end and the pre-release review use the same files with a
wider scope. No analyzer is a slash command, and none needs anything installed.

## How the gate dispatches an analyzer

Give the subagent, in this order:

1. **This contract** and **the analyzer file** — both verbatim, read from disk.
2. **Mode:** `phase` (the changed files and their direct callers/callees) or `full` (the whole
   codebase, or the whole milestone's changes).
3. **Scope:** the file list — including untracked files
   (`git ls-files --others --exclude-standard`) — and the diff for `phase` mode.
4. **The requirement** the change is supposed to meet: the spec from `@spec:`, the approved chat
   draft from STATE.md, or the phase description.
5. **`$TECH_STACKS`**, so the analyzer can pick its language notes.

**Do not** hand over why you believe the change is correct. The analyzer gets the artifact and the
requirement, never your reasoning — otherwise it returns your conclusions instead of a review.
Ask for refutation: *"Find what is wrong with this change"*, not *"check this change"*.

Set the model explicitly (see `models.md`).

## How the analyzer works: sweep, then judge

1. **Sweep.** Before judging anything, run the analyzer's **sweep probes** (the `Sweep` section of
   its file) over the scope with `grep`/`rg` and collect every hit as a candidate — mechanically,
   including hits that look harmless. Lenses tell you where to think; the sweep makes sure you look
   at every line of the risky kinds, not only the ones that caught your eye.
2. **Judge each candidate** with the evidence rule below: construct the input or sequence that
   breaks it, or dismiss it with a reason.
3. **Then the lenses** — for what no probe can find.

Report the sweep in the `Checked:` line: probes run, candidates found, candidates confirmed.

## Rules for the analyzer

- **Read-only.** Never edit files, never run anything that writes, deploys or sends. Reading,
  searching and running read-only commands (type checks, `git log`, `grep`) is fine.
- **Every finding needs evidence from the code:** file and line, the quoted line(s), and the
  concrete input or sequence that makes it fail. "Could be a problem" without a trace is not a
  finding — drop it or state it as an open question.
- **Follow the data, not the file.** A value that is safe in the changed file may be unsafe where
  it came from or where it goes. Open the caller and the callee before judging.
- **Say what you checked, not only what you found.** A short list of the lenses or paths you
  covered makes "no findings" meaningful.
- **"No findings" is a valid result.** Never invent findings to have something to report.
- **Stay in your lane.** Report what your analyzer file asks for. A strong finding outside it may
  be listed once under "Outside scope", without detail work.

## Severity

- **critical** — wrong result, data loss or corruption, a security hole, a crash or hang on a
  reachable path, a leak or cost that grows with use, or an acceptance criterion that is not met.
  The gate fixes these before it continues.
- **note** — real but bounded: an edge case with a harmless outcome, a missing guard on an
  unlikely path, a clearer alternative. The gate records these in STATE.md.

When unsure between the two, decide by the worst realistic outcome, not by how likely it is.

## Output format

Return exactly this, in the user's language (headings may stay English):

```markdown
### <Analyzer name> — <mode>

Checked: <sweep: N probes, M candidates, K confirmed; lenses covered>

| # | Severity | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| 1 | critical | path/file.ext:42 | <one sentence> | <quoted line + failing input/sequence> | <one sentence> |

Outside scope: <optional, one line each>

Result: <N critical, M notes> | no findings | skipped: <reason>
```

The `Result:` line is what the gate copies into the checklist as evidence. `skipped: <reason>`
(an analyzer whose tool or source is missing) is never a pass: the checkbox stays open with the
reason.
