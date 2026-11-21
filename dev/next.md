# /dev next — pick a phase, handle state findings

Read when the router in `SKILL.md` points here (`/dev next <N>`, Session Start step 1).

## Pick a phase

**Triggered by:** `/dev next <N>` (also the task of a child thread). `/dev next <N> on <branch>` (a
child that continues a phase): first `git fetch -q && git switch <branch>`; the claim is then this
branch's. Session Start runs as usual; step 6 then takes Phase N instead of the first open one:

- `[x]`/`[—]` → say so, stop.
- Claimed by another branch → say by whom; AskUserQuestion: leave it (Recommended) or take it over
  (Pre-Phase step 2, "Takeover").
- Builds on a phase not yet `[x]` (its line, a line below it or its `Goal:` names that phase) → say
  so; AskUserQuestion: that phase instead (Recommended), Phase N anyway, stop.
- Otherwise resume or start it as step 8 does. The run ends after Phase N (step 8: one status line,
  no next phase): one run, one phase.

---

## State findings

Session Start, step 1: each finding of `state-check.py check`, handled before ROADMAP.md is read.

- `size:`, `handoff:`, `archivable:` → offer archiving (Milestone End, step 5 in `commands.md`) in the bundled round; never rewrite without the user's yes.
- `behind:` first → `git pull --ff-only` (a dirty or diverged tree: say so and stop).
- `migrate:` next, before any other finding. The marker `<prefix>.dev/.gitkeep` on `origin/<main>` decides (`state.md`, "Old format"): `git cat-file -e origin/<main>:<prefix>.dev/.gitkeep` (`<prefix>`: ROADMAP.md's directory). Present (the project agreed) → run `migrate` for the own claim's parts without asking, commit `roadmap: migrate state to phase files`, then bring in `origin/<main>`: branch not pushed → `git rebase origin/<main>`, pushed → `git merge origin/<main>`; never a force-push. STATE.md conflict → take `origin/<main>`'s, rerun `migrate` for the own parts (it appends nothing twice), continue. Absent (until then `migrate:` counts every session's parts): offer `state-check.py migrate --dry-run` in the bundled round; only after the user's yes run `state-check.py migrate` on a fresh branch from `origin/<main>` (it creates the marker; no claim there, so no phase file reaches `<main>`), commit and bring it to `<main>` at once — own small PR or push, as the project allows — then bring in `origin/<main>` on the working branch as above and migrate its own parts, before the phase goes on. The migration changes `@state` once (STATE.md becomes code): ticked gate items of the own phase go stale — rerun them.
- `orphan phase file:` → phase done: save (unless already there) and delete as the finding says, in the next commit. Still `[~]`/`[!]`, branch gone: ask the user — take over, or discard (Position, criteria → `## Abandoned` there; delete the file; phase back to `[ ]`, no `@claim:`).
- `phase file missing:` → create it now: `Branch:`, `## Position`, `Phase base:` (parent of the phase's `roadmap: claim` commit). The same at the claim of a `[!]` phase without a phase file in a migrated project (a phase left from the old format, or a gate run after its code was merged): it keeps `[!]` and gets `@claim:`; `Phase base:` is the parent of the phase's first commit (`git log` of its files, or the parent of its squash commit) and `Phase head: <sha>` its last commit; the file gets its Gate Checklist (`SKILL.md` 4d.2). Later phases' changes are not this phase's: with a `Phase head:` line, `gate-tier.py` and `floor-guard.py` run with `--root` on a worktree at that commit (`git worktree add --detach <tmp> <sha>`, removed afterwards), never on today's tree; Step A's diff file is `git diff <Phase base> <Phase head>`. The gate's own fixes land on today's tree: Fix review as usual, and a second `floor-guard.py --base <claim commit>` there.
- `phase file invalid:`, `branch mismatch:` → own claim: correct the `Branch:` line; another branch's claim: ask the user.
- `orphan handoff:`, `long handoff:` (old format) → remove or shorten that block in the next STATE.md commit.

---
