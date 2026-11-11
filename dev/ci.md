# CI — background watch and repair

Read at the gate commit, before each phase when a phase or gate file of the current milestone has a
`## CI` SHA, at Milestone End, at Pre-Release Review and in `/dev check` (router in `SKILL.md`).

## CI in background

If `.github/workflows/` exists, CI checks the gate commit while `/dev` goes on:

1. **CI must see the commit** through the route the project already allows (push of the phase
   branch, PR update, workflow dispatch). No authorized route → halt once per run, name the blocker,
   note the answer (a route, or `no CI this run`) under the phase file's `## CI` and follow it.
   Never push to a protected or production branch for this.
2. Start `bash "$DEV_DIR/scripts/ci-watch.sh" <sha>` with `run_in_background` and add the SHA to
   the phase file:
   ```markdown
   ## CI
   - <sha>
   ```
   The watcher accepts only runs of exactly this SHA and treats `skipped`/`cancelled` as not green.
   One exception: a run cancelled by a later push (cancel-in-progress) is followed to the run of the
   descendant commit; the status line then ends in `via <sha>` and counts for the gate SHA.
   It writes the status to `$(git rev-parse --git-common-dir)/dev-ci/<sha>`, shared by all
   worktrees; a status never goes into a tracked file.
3. **Read the status** of every listed SHA there when the watcher reports, before each next phase
   and at Milestone End; a status after the SHA (written by earlier /dev versions) is ignored;
   `→ repaired in <sha>` is not a status. No status file, or `pending`, and no watcher
   (`pgrep -f "ci-watch.sh <sha>"`) → start it again (step 2). **Who repairs:** a SHA is **own** if
   the file it stands in (`.dev/phase-<N>.md` or `docs/gates/phase-<N>.md`) appears in
   `git diff --name-only origin/<main>...HEAD`. The session repairs own SHAs, only reports others;
   Milestone End and Pre-Release Review (one session; Milestone End also starts on its own after the
   last phase) repair every `red`/`timeout` SHA of the milestone or release.
   - `green <ids>`, or the line says `→ repaired in` → done.
   - `red …` or `timeout` → the repairer halts after the current step: show the failing run(s)
     (`gh run view <id> --log-failed`) and repair (below). A `timeout` from missing `jq` or failing
     `gh` (`gh auth status`) is a tooling problem: report it, never repair.
   - `none` → no run of this SHA appeared (a `paths`/`on:` filter can exclude a commit on purpose).
     Not a halt and never green.
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
