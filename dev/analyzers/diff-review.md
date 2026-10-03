# Diff review (gate Step A)

**Question:** What is wrong with this phase's change as a whole?

One pass over the whole phase diff, prompted for refutation. The per-task reviews already checked
each task against its brief, so this pass looks at the whole and at what falls between tasks:
seams, leftovers, things no single task owned.

## Inputs

Besides the contract: the diff as a file (including untracked files), the requirement (the spec
from `@spec:` or the acceptance criteria in STATE.md) and the list of changed files. Never the
implementer's reasoning — you are reviewing the artifact, not an argument for it.

## Sweep

Run the probes from the `Sweep` section of `analyzers/bugs.md` over the changed files, plus:
`TODO`/`FIXME`/`console.log`/`print(`/`dbg!` added by the diff, and commented-out code.

## Checks

**Scope** — does the diff do what the requirement asks, and nothing else?
- Missing: every place that must change together — callers of a changed signature, other
  implementations of an interface, migrations for a model change, docs and config for a new option.
- Stray: hunks the requirement does not explain (debug code, unrelated reformatting, files outside
  the phase, files another session left in the tree).
- Tests: each behaviour change has a test that would fail without it; tests that only assert that
  code runs, or mirror the implementation, do not count.
- Irreversible: anything `git revert` cannot undo (migrations, data changes, deploy steps, messages
  to real recipients). For migrations: is there a rollback path, and does it work?

**Defects** — one lens each; construct the input that breaks the line, or drop it:
- Assumptions: non-empty, loaded, unique, logged in, a success return — where the caller does not
  guarantee it (error objects, `null`, `false`, empty collections used as the happy-path type).
- State: an operation allowed in a state it should not be; a retry that runs twice.
- Boundaries: zero/one/many, first/last, empty vs missing vs `null`, off-by-one, `>` vs `>=`.
- Data lifecycle: read after delete, double writes, partial writes when step 2 of 3 fails, stale cache.
- Error paths: swallowed errors (`catch {}`, `|| true`, `2>/dev/null`) that let a wrong value through.
- Time: overlap, check-then-act gaps, timezones, "now" read twice, timeouts shorter than the work.
- Platform: permissions, locale, GNU vs BSD tools, container vs host paths, missing binaries.
- Escaping: every boundary into URL, shell, SQL, HTML, JSON, regex or file name uses the library
  meant for it; hand-rolled escaping is a finding with the input it breaks.

The language notes in `analyzers/bugs.md` apply.

**Cleanup** — what a simplification pass would look for:
- An existing helper that already does what new code re-implements.
- Duplication introduced by the phase, across tasks too.
- Dead code the phase left behind: unused functions, parameters, imports, branches, flags.
- Needless work in hot paths: repeated computation in loops, a query per item, re-reading a file.

Cleanup findings are always notes, never critical.

## Severity

**critical** — a defect or scope violation that ships a wrong result or loses data: a reachable
failing input, a missing part of the requirement, behaviour the requirement did not ask for, an
irreversible step without a halt. Everything else is a note.

## Output

The contract format, analyzer name `Diff review`. In `Checked:`, name the three groups and the
sweep counts.
