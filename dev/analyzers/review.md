# Change review (gate step 5b)

**Question:** Does this diff do what the requirement asks, and nothing it should not — before the
deeper analyses start?

This is the fast first pass over the whole diff. It is broad and shallow on purpose; the analyzers
in 5c go deep. Its job is to catch what they are not built to see.

## Checks

1. **Intent.** Read the requirement, then the diff. Is every changed hunk explained by it? Flag
   changes that are not (stray edits, debug code, unrelated reformatting, files another session
   left in the tree).
2. **Completeness.** Are all places updated that must change together — callers of a changed
   signature, other implementations of an interface, migrations for a model change, docs and
   config for a new option, both branches of a platform split?
3. **Obvious defects.** Typos in names and keys, inverted conditions, wrong variable used, copy-paste
   leftovers, dead branches, commented-out code, TODOs that hide unfinished work.
4. **Tests.** Does each behaviour change come with a test that would fail without it? Tests that only
   assert that code runs, or mirror the implementation, do not count.
5. **Irreversibility.** Does the diff contain or prepare something `git revert` cannot undo —
   migrations, data changes, deploy steps, messages to real recipients? Flag it; the gate halts
   there (see "Halt on Irreversible Actions" in `SKILL.md`).
6. **Readability for the next person.** Names that say what things are; comments that say why, not
   what; no clever code where plain code works.

## Critical when

The diff misses part of the requirement, changes behaviour the requirement did not ask for, or
contains an irreversible step without an explicit halt. Style and naming are notes.
