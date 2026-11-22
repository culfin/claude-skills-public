# CI — background watch and repair

Read when the router in `SKILL.md` points here.

## CI in background

If `.github/workflows/` exists, CI checks the gate commit while `/dev` goes on:

1. **CI must see the commit** through the route the project already allows (push of the phase
   branch, PR update, workflow dispatch). No authorized route → halt once per run, name the blocker,
   note the answer (a route, or `no CI this run`) under the phase file's (or check file's; old
   format: STATE.md) `## CI` and follow it.
   CI runs only on `pull_request` (the workflows' `on:`) and the project takes PRs → the route is a
   PR from the phase branch to `<main>` (`gh pr create`), opened once, never merged here; the push of
   each later commit updates it. T3: `runtime.md`, "PR opened".
   Never push to a protected or production branch for this. **One push, one CI run per phase:** a
   phase's gate commit goes out together with its completion commit (`SKILL.md` 7.5), which carries
   the gate SHA's `## CI` line into `docs/gates/`. A CI repair or a `/dev check` round (review findings) goes
   out once, when its checks are green — never commit by commit: every push to an open PR cancels the run of
   the push before it. `<main>` comes into the branch only on a conflict (`gh pr view <pr> --json mergeable`
   → `CONFLICTING`) or when the merge itself refuses a branch that is behind; `BEHIND` alone is no reason.
2. After the push, start `bash "$DEV_DIR/scripts/ci-watch.sh" <gate sha>` with `run_in_background` (T3: its task ID to
   `t3_background_wait` at once, `runtime.md`); the gate SHA goes into the phase file right after the gate commit:
   ```markdown
   ## CI
   - <sha>
   ```
   The watcher accepts only runs of exactly this SHA and treats `skipped`/`cancelled` as not green.
   Exception: no run of this SHA yet (pushed with a later commit), or one cancelled by a later push
   → it follows the run of a descendant commit on the branch; the status line then ends in `via <sha>`
   and counts for the gate SHA.
   It writes the status to `$(git rev-parse --git-common-dir)/dev-ci/<sha>`, shared by all
   worktrees; a status never goes into a tracked file.
3. **Read the status** of every listed SHA there when the watcher reports, before each next phase
   and at Milestone End; a status after the SHA (written by earlier /dev versions) is ignored;
   `→ repaired in <sha>` is not a status. No status file, or `pending`, and no watcher
   (`pgrep -f "ci-watch.sh <sha>"`) → start it again (step 2). **Who repairs:** a SHA is **own** if
   the file it stands in (`.dev/phase-<N>.md` or `docs/gates/phase-<N>.md`) appears in
   `git diff --name-only origin/<main>...HEAD`; old format (STATE.md `## CI in background`): a line is
   own if its `Phase N` is claimed by this branch in ROADMAP.md; any other line: report only. The
   session repairs own SHAs, only reports others;
   Milestone End and Pre-Release Review (one session; Milestone End also starts on its own after the
   last phase) repair every `red`/`timeout` SHA of the milestone or release.
   - `green <ids>`, or the line says `→ repaired in` → done.
   - `red …` or `timeout` → the repairer halts after the current step: show the failing run(s)
     (`gh run view <id> --log-failed`) and repair (below). A `timeout` from missing `jq` or failing
     `gh` (`gh auth status`) is a tooling problem: report it, never repair.
   - `none` → no run of this SHA appeared (a `paths`/`on:` filter can exclude a commit on purpose).
     Not a halt and never green: add a line `- CI: none` to `docs/gates/phase-<N>.md`.
   - `pending` → go on between phases; at Milestone End, wait for it.

## Repairing a red CI SHA

**Repairing a red CI SHA of a phase, closed or not.** Open a short checklist in
`docs/gates/phase-<N>.md` (in the phase file while it exists) and let `check-evidence.py check
<that file> --before-commit --repair` check it like a gate:

```markdown
## Quality Gate — Phase N: <Name> (CI repair)
- [ ] Fix review                 <!-- Diff review on `git diff <red sha>` plus untracked files -->
- [ ] Typecheck + lint + tests
- [ ] Production Build
- [ ] Gate commit
```

Then a new `[gate-pass]` commit, a new watcher, a new line `- <new sha>`, and the old line becomes
`- <sha> → repaired in <new sha>`. The repair checklist stays as the record.
