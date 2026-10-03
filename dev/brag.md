# Launch video (brag) — when `/dev` offers it and how it runs

`brag` (plugin `brag@brag`, HyperFrames) turns the project into a 15–25 s launch video. A run
takes minutes and noticeable usage, so `/dev` **offers** it at three points and never starts it on
its own. Contract and overrides: `sources.md` (row `brag`, O13).

## When to offer

Offer only if one of these holds; otherwise do not mention it.

| Point | Condition |
|---|---|
| Milestone End, step 7 | The milestone contains a `[x]` phase with `@type: landing`. |
| Pre-Release Review, step 6 | Since the last release tag (`git describe --tags --abbrev=0`; none → whole history) a `@type: landing` phase was completed **or** files of the landing/marketing page changed (the paths the `landing` phases touched). |
| Pre-Release Review, step 6 | The release raises the **major or minor** version (the project's version field against the last tag) **and** a `@type: ui` or user-facing feature phase was completed since that tag. Patch releases never. |

Offer as one `AskUserQuestion` option: **Create launch video** — "brag renders a 15–25 s video
into `brag-output…/`; nothing is published." The other options of that dialog stay as they are.

## How it runs

1. **Installed?** `brag@brag` in `~/.claude/plugins/installed_plugins.json` and its install path
   present. Missing → report `Launch video: skipped — brag not installed`, never a silent pass.
   Installed but not loaded in this session (no `brag` skill available) → say that it is available
   from the next session on.
2. **Keep it out of git.** If `.gitignore` lacks `brag-output*/`, add that line and commit it on its
   own (`chore: ignore brag output`) before the run.
3. **Invoke** the `brag` skill. Pass the angle from the trigger (what the redesign or the release
   added). On Opus 5.5 it switches to `brag-slim` by itself — let it. `--voice` only when the user
   asks for narration.
4. **Personal data.** Products that handle patient, customer or account data show fictional stand-ins
   only (the skill's own rule in `references/step-1-inspect.md`; `/dev` holds it to that). No real
   names, IDs, hosts or screenshots of production data.
5. **Report** the path of `brag.mp4`, the poster and `share-copy.txt`. Posting the video or the
   share copy anywhere is the user's step — `/dev` never uploads, posts or commits the output.
