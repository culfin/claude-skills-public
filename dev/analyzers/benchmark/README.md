# Analyzer benchmark

Do the analyzers find bugs we know are there? Each case is a small, anonymised reproduction of a
defect that reached production in a real project, with some harmless code around it.

```bash
dev/analyzers/benchmark/run.sh                          # all cases, current analyzers
dev/analyzers/benchmark/run.sh --cases health-task      # one case
dev/analyzers/benchmark/run.sh --instructions a.md,b.md # other instructions on the same cases
```

Needs the `claude` CLI and `python3`. One run costs roughly one analyzer session plus one short
judge call per case.

## How a run is isolated

- The code is copied into a fresh temp directory and analyzed from there — no project memory, no
  project `CLAUDE.md`, nothing from the repository the case came from.
- No MCP servers (`--strict-mcp-config`), no skills (`--disable-slash-commands`), and only `Read`,
  `Grep` and `Glob` as tools.
- The analyzer never sees `case.json`. A second run without tools compares the report with the
  expected defects and only counts a finding with the **same place and mechanism** — reporting a
  consequence, or another bug on the same line, is a miss.

## Cases

| Case | Analyzer | Defect |
|---|---|---|
| `review-queue` | security | handler acts on any item by ID, not only on drafts — a no-login review link can trash published items |
| `terms-shape` | bugs | `WP_Error` slips through `?:` because objects are truthy |
| `upcoming-query` | performance | `meta_query` with three `OR` branches joins postmeta six times; the joins multiply |
| `alert-runner` | bugs | `grep -m1` under `pipefail` aborts the script; hand-rolled URL encoding breaks every query with `{}` and the parse error is swallowed |
| `health-task` | bugs | unchecked SSH result turns an outage into false "service down" alerts; a variable used but never set under `set -u` |

## Results (2026-09-27, model `sonnet`, one run per case)

| | found as critical | found as note | missed |
|---|---|---|---|
| `dev/analyzers` | 6 | 1 (URL encoding) | 0 |
| previous third-party instructions | 6 | 1 (URL encoding) | 0 |

The same seven defects were also run on the original, non-anonymised code (not published). There
the previous instructions found 7 of 7 (URL encoding as a note); `dev/analyzers` found 6 of 7 in
its latest run, missing the `grep -m1` abort that an earlier run had found. **Single runs vary
more than the difference between the two** — treat one run as a smoke test, and repeat a case
before concluding that a change to an analyzer made it better or worse.

Two changes came directly out of these runs: the **sweep** step in `CONTRACT.md` (probe for risky
constructs first, then judge every hit), and the rule in `performance.md` to compute the work as a
number before calling anything fast. Both cases are now tuned, not blind — new defects are the
honest test.

## Adding a case

`cases/<name>/code/` holds the code, `cases/<name>/case.json` the analyzer, the requirement and the
expected defects (`id`, `what`, `where`, `severity`, `origin`: `real` for a defect that happened,
`synthetic` for one made up). Keep comments neutral: nothing in `code/` may point at the defect.
