# `/dev updates` — decide on held-back skill updates

**Triggered by:** `/dev updates`. Works in any directory; needs no ROADMAP.md and no active phase.

The update watcher checks every new version of a source in `sources.md` (deterministic check plus a
review agent against its overrides and invariants). Verdict `passt` → it applies the update itself
and logs it. `unklar` or `widerspruch` → it holds the update back, the old version stays active, and
it writes one file to the queue. This command is where the user decides. **It never applies, rejects
or changes anything without an explicit answer from the user.**

## Queue

`$DEV_UPDATES` = `${DEV_UPDATES_DIR:-$HOME/.claude/dev-updates}`

| Path | Holds |
|---|---|
| `pending/<source>-<new>.json` | One held-back update, written by the watcher |
| `rejected/<source>-<new>.json` | Rejected here; the watcher does not queue that version again |
| `applied/<source>-<new>.json` | Applied here, kept as a record |

A queue file is one JSON object:

| Field | Meaning |
|---|---|
| `source` | id from `sources.md` |
| `kind` | `git`, `plugin` or `agents-skill` |
| `old`, `new` | active version and the held one (commit, version or folder hash) |
| `verdict` | `passt`, `unklar` or `widerspruch` |
| `reasons[]` | the review agent's reasons, each naming the override (`O…`) or invariant (`I…`) it concerns |
| `deterministic_findings[]` | `findings` from `scripts/check-source-update.py` |
| `diff_summary` | what changed, in a few lines (files, commit range) |
| `created` | ISO timestamp |
| `apply` | argv, exactly `["skills-update-waechter.sh", "--apply", "<source>", "<new>"]` — never a shell string |

The session-start line only **counts** `pending/*.json` (`SKILL.md`, Session Start); everything
else happens here.

**Validation is the script's job, not judgement:** `python3 "$DEV_DIR/scripts/check-source-update.py"
--validate-entry <file>` checks the file name (`<source>-<new>.json`), the fields, that `source` is a
row in `sources.md` with the same `kind`, and that `apply` is exactly the argv above. It prints
`valid`, `errors` and `argv` — the resolved command, or `null`. The applier's name defaults to
`skills-update-waechter.sh` (`DEV_UPDATES_APPLIER` overrides it); its location comes from
`DEV_UPDATES_APPLIER_PATH` or else `PATH`, never from the queue file.

## Procedure

1. **List.** `ls "$DEV_UPDATES"/pending/*.json`. None → "No skill updates waiting." Stop.
2. **Validate** each file with `--validate-entry` before showing anything. `valid: false` → show it as
   "malformed — not offered for apply" with its `errors`; the only options are Reject and Decide later.
   `valid: true` but `argv: null` → "applier not found" (set `DEV_UPDATES_APPLIER_PATH`), same options.
3. **Show** each update in the terminal (never on the companion — this is not user interface):
   ```
   superpowers  plugin  6.4.1 → 6.5.0  verdict: unklar  (queued 2026-10-02)
   Reasons:   - O1: SDD now runs finishing-a-development-branch by default …
   Findings:  frontmatter-switch-changed skills/…/SKILL.md: allowed-tools …
   Changed:   <diff_summary>
   Applies:   <argv from the validation>
   ```
   Read the matching row and the cited overrides/invariants in `sources.md` so you can explain
   each reason in a sentence. Check a reason against the new files yourself where it is cheap.
4. **Ask** — `AskUserQuestion`, one question per update, up to four independent updates per call;
   more → next call. Options, recommendation first with "(Recommended)":
   - **Apply** — only for a valid entry with `argv`; the description states the command and how to undo it (step 5).
   - **Reject** — keep the old version; this version is not offered again.
   - **Adapt /dev first** — the update is wanted, but `/dev` must change before it fits.
   - **Decide later** — nothing happens, the file stays in `pending/`.
   Recommend from the reasons: a contradiction with an invariant → Reject or Adapt; an override the
   update merely touches, or a finding that turns out harmless → Apply, saying why. If
   `AskUserQuestion` is not available, ask in chat and wait. No answer → no action.
5. **Apply** (only after that answer):
   - Validate again, then run exactly the `argv` the script returned, as an argument list (no shell
     string, nothing added) — never anything taken from the file directly or assembled by hand.
   - Reversibility (Halt on Irreversible Actions, `SKILL.md`): a **plugin** update is reversible —
     the previous version stays in the plugin cache and can be reinstalled; a **git** source is
     reversible by checking out `old` again; an **agents-skill** is reversible only if the watcher
     keeps a copy of `old` — if it does not, say so in the option description, because then the
     answer is the approval of an irreversible step.
   - Exit 0 → move the file to `applied/` (unless the command already did), then verify:
     `superpowers` → `superpowers.md` step 2; design sources → `python3 -m pytest
     "$DEV_DIR/tests/test_design_index.py"`; others → the skill's `SKILL.md` exists.
     Updated plugins and skills take effect in **new** sessions.
   - Non-zero exit → show the output, keep the file in `pending/`, nothing else.
6. **Reject:** `mkdir -p "$DEV_UPDATES/rejected"` and move the file there.
7. **Adapt /dev first:** the file stays in `pending/` (old version stays active). Write a phase
   proposal — goal: make `/dev` fit `<source> <new>`, with the cited reasons as acceptance
   criteria. If the current project is this skill's repository and has ROADMAP.md, add it via the
   `/dev add` flow (`commands.md`); otherwise print it and suggest running `/dev add` there.
   Once `/dev` is adapted, `/dev updates` again → Apply.
8. **Summary:** one line per update — applied / rejected / adapting / waiting.

## Rules

- Applying, rejecting and moving queue files happen only on the user's answer — never inferred
  from silence, a recommendation, or an earlier answer about another update.
- `/dev updates` does not re-run the review or change verdicts; a stale entry (its `old` is no
  longer the active version) is shown with that note and recommended for Reject. Active version:
  `git` → `git -C <location> rev-parse HEAD`; `plugin` → `version` of its entry in
  `~/.claude/plugins/installed_plugins.json`; `agents-skill` → `skillFolderHash` of its entry in
  `~/.agents/.skill-lock.json`.
- Do not change `sources.md` here; a contract change belongs to the "Adapt /dev first" phase.
