# claude-skills

**Four workflows for Claude Code and Codex, refined in daily use on production projects:** an
orchestrator that takes a project phase by phase through a mandatory quality gate, a manager for
dependency updates and security alerts, on-demand Sentry triage, and an evidence-based polish and
launch audit for web apps. Each skill answers in the
language you write in, and each can be installed on its own.

---

## The skills and what they change

| Skill | Command | What it does | What it changes |
|---|---|---|---|
| [**dev**](dev/SKILL.md) | `/dev` · `/dev next` | Takes the next roadmap phase through clarification, planning, implementation and the quality gate | code, tests, `ROADMAP.md`, `STATE.md`, commits on the current branch; never deploys or pushes to production without asking |
| | `/dev check` | Runs the quality gate on changes made outside a phase | fixes findings, one check commit |
| | `/dev status` · `init` · `add` · `skip` · `reorder` · `pause` | Roadmap overview and maintenance | `ROADMAP.md`, `STATE.md` |
| | `/dev debug` · `/dev review` | Systematic debugging; full pre-release review | code and tests where a fix is needed |
| | `/dev ui [scope]` | Screenshots and design analyses of one part of the running UI; reworks only the findings you approve | `UI-REVIEW.md`; code only after approval, then one check commit |
| | `/dev updates` | Lets you decide on held-back updates of the skills `/dev` builds on (apply, reject, adapt `/dev` first, later) | nothing without your answer; then the queue files and, on Apply, the one source you approved |
| [**deps**](deps/SKILL.md) | `/deps` · `/deps check` | Status; impact analysis of all update PRs and security alerts | nothing |
| | `/deps merge` | Merges eligible Dependabot PRs, updates they missed and understood major migrations, runs the tests, writes a report — and opens a promote PR | dev branch (merges, lockfile, migrations), `.deps/last-report.md`, a PR to production |
| | `/deps audit` | Closes vulnerabilities via compatible updates or overrides | manifests, lockfile, commits on the dev branch |
| | `/deps promote` · `/deps close` · `/deps setup` | Promote PR; close superseded PRs; one-time setup | a PR (the production merge stays manual); PR states; workflow and config files |
| [**sentry**](sentry/SKILL.md) | `/sentry` | Status: unresolved issues per environment | nothing |
| | `/sentry check` | Triage: top issues, cause, fix proposal | only a local report in `.sentry/reports/` (git-ignored) |
| | `/sentry fix <ID>` | Fixes one selected issue with a regression test | code, tests, one local commit — no push, no deploy, no issue state change |
| | `/sentry setup` | Creates `.sentry/config.json`, verifies access, checks whether auto-resolve is really wired up | the config file and `.gitignore`; Sentry settings only after you say so |
| [**vibepolish**](vibepolish/SKILL.md) | "audit my app" · "review before launch" | Finds unfinished, template-like details and launch risks in a web app, with evidence | nothing (an `AUDIT.md` report at most) |
| | "… and fix it" | Fixes what the request covers, in small verified batches | code and tests; no commit, push or deploy unless asked; asks before redesigns, new dependencies, migrations |

---

## Requirements

| For | Claude Code | Codex |
|---|---|---|
| all | [Claude Code](https://claude.com/claude-code) | [Codex CLI](https://github.com/openai/codex) |
| `dev` | the [superpowers](https://github.com/obra/superpowers) plugin (planning, execution, Visual Companion) | superpowers for Codex; set `DEV_SUPERPOWERS_ROOT` to its root |
| `deps` | `gh` (logged in), `python3` | same |
| `sentry` | a connected Sentry MCP server (or a read-only Sentry API client) | same |
| `vibepolish` | nothing extra; a browser tool makes runtime checks possible | same |

`dev`'s quality-gate analyzers ship with the skill; no other skills are needed.

---

## Installation

**Claude Code** — link the skills you want into `~/.claude/skills`:

```bash
git clone https://github.com/culfin/claude-skills-public.git ~/claude-skills
mkdir -p ~/.claude/skills
for s in dev deps sentry vibepolish; do ln -sfn ~/claude-skills/$s ~/.claude/skills/$s; done   # or only some
~/claude-skills/dev/tests/check-setup.sh     # checks what is installed; missing skills are fine
```

**Codex** — the same, into Codex's user skills directory:

```bash
git clone https://github.com/culfin/claude-skills-public.git ~/claude-skills
mkdir -p ~/.agents/skills
for s in dev deps sentry vibepolish; do ln -sfn ~/claude-skills/$s ~/.agents/skills/$s; done
```

Each skill reads its own `runtime.md`, which maps tool names to what the host offers. Optional
extras — the `/dev` stop hook (Claude Code only) and opening the Visual Companion from another
device — are in [SETUP.md](SETUP.md).

### Design sources (optional)

`/dev`'s design steps can draw on three third-party skill repositories, if present:
[emilkowalski/skills](https://github.com/emilkowalski/skills),
[leonxlnx/taste-skill](https://github.com/leonxlnx/taste-skill) and
[pbakaus/impeccable](https://github.com/pbakaus/impeccable). Clone them under `$DEV_DESIGN_DIR`
(default `~/.claude/dev-design`), one directory per name:

```bash
mkdir -p ~/.claude/dev-design
git clone https://github.com/emilkowalski/skills.git ~/.claude/dev-design/emil
git clone https://github.com/leonxlnx/taste-skill.git ~/.claude/dev-design/taste
git clone https://github.com/pbakaus/impeccable.git ~/.claude/dev-design/impeccable
```

**Do not link these into `~/.claude/skills` or `~/.agents/skills`.** Every installed skill's
description is loaded into every session's context, and a broad description can trigger on
unrelated requests; `/dev` reads these checkouts directly from `$DEV_DESIGN_DIR` instead. Any
source that is missing is simply skipped — `dev/tests/check-setup.sh` reports its status but never
fails on it.

The gate's design detector runs impeccable's rules from a binary you build from that checkout:
`dev/scripts/design-build-detector.sh` (needs Rust/cargo; the first build fetches crates, later calls
return at once while the checkout is unchanged). Run it again after updating the checkout.

impeccable can install hooks and phone home; neither is used here. If you run it yourself outside
`/dev`, set `IMPECCABLE_NO_TELEMETRY=1` and `DO_NOT_TRACK=1` first.

### Stack sources (optional)

For some technologies `/dev` can read the vendor's or maintainer's own skill repository as context
(steps 4a, 4c) and as a read-only review of the files a phase changed (gate step 5c). Clone the
ones your projects use under `$DEV_STACK_DIR` (default `~/.claude/dev-stack`), one directory per id:

```bash
mkdir -p ~/.claude/dev-stack && cd ~/.claude/dev-stack
git clone --depth 1 https://github.com/docker/skills.git docker
git clone --depth 1 https://github.com/getsentry/skills.git gha
git clone --depth 1 https://github.com/better-auth/skills.git better-auth
git clone --depth 1 https://github.com/neondatabase/postgres-skills.git postgres
git clone --depth 1 https://github.com/stripe/ai.git stripe
git clone --depth 1 https://github.com/mcollina/skills.git fastify
```

As with the design sources: **do not install them as skills or plugins.** `/dev` reads single
files from the checkout when a trigger in `dev/stack/INDEX.md` matches (a compose file changed, a
workflow changed, …) and nothing otherwise. They are a yardstick, not an authority — your
project's conventions win, and install steps, hooks, MCP servers, usage reporting and
hosted-product recommendations inside them are ignored. A checkout that is missing costs nothing:
its review is ticked `skipped: <reason>` and listed in the gate summary; `dev/tests/check-setup.sh`
reports the status.

Nothing to set up for Next.js, the AI SDK, Fastify and Playwright traces — their docs or skills
ship inside the project's own `node_modules`, matching the installed version. For current API
facts `/dev` follows a fixed order per technology (`dev/stack/docs.md`): bundled docs, the
vendor's docs access if the host has one, the official `llms.txt`, then Context7.

`/deps` adds a "What's new" section to its report when an update lifts one of these technologies
across a minor or major version (`deps/references/whats-new.md`): what is new, what affects the
project, what is deprecated. It reports; it does not rewrite code.

### Skill updates (optional, external)

`/dev` builds on skills it does not own; `dev/sources.md` is the contract a new version of one of
them is checked against. The **update watcher** that does this checking on a schedule is external
and optional — it is not part of this repository. Without one, nothing is ever queued and
`/dev updates` simply reports that no skill updates are waiting. If you run your own, it writes
held-back updates to `${DEV_UPDATES_DIR:-~/.claude/dev-updates}/pending/` (format in
`dev/updates.md`, pre-check by `dev/scripts/check-source-update.py`) and provides the applier: an
executable named `dev-updates-apply` that accepts `dev-updates-apply --apply <source> <new>` and
activates exactly that version of that source. `/dev updates` finds it via
`DEV_UPDATES_APPLIER_PATH` or on `PATH` and runs nothing else.

---

## Quick start

1. **dev:** in a project, `/dev init` creates the roadmap; `/dev` starts the first phase. Without a
   roadmap, `/dev check` runs the gate on your current changes.
2. **deps:** `/deps setup` once per repository, then `/deps check` (changes nothing) to see what is
   pending, `/deps merge` when you want it done.
3. **sentry:** connect the Sentry MCP server in your host, run `/sentry setup` in the project, then
   `/sentry` for the status.

4. **vibepolish:** "audit this app for unfinished details" (report only) or "… and fix what you
   find"; name an area to keep it focused.

On Codex, ask by name where there is no slash command: "use dev: check".

---

## Details

### dev

A phase: **clarify** (questions in rounds, recommended answer first; UI questions as mockups and
architecture as diagrams in the browser) → **plan and build** (superpowers: spec, plan, subagents
with a review per task) → **quality gate** (cleanup, change review, parallel analyses for bugs,
performance and security, spec check, typecheck, lint, tests, build, end-to-end, CI) → **close**
(gate commit, summary in `STATE.md`).

Principles:
- **Every checkmark needs evidence** — the decisive output and the state of the code it ran on.
  `dev/scripts/check-evidence.py` reports items that are open, unproven or older than the code.
- **New acceptance criteria get a test that failed first.** Where the spec checker finds a criterion
  without a test, the new test is seen failing against a deliberately broken implementation before
  it counts.
- **A pre-existing failure needs proof** — the same failure reproduced on the unchanged base — and
  is reported as such, never as "all green".
- **Stop before the irreversible.** Migrations, deploys, releases, force pushes and messages to real
  recipients need explicit approval, even when a plan includes them.
- **State outlives the session.** An interrupted phase resumes on the next `/dev`.

### deps

npm, pnpm, Yarn, Bun, Cargo, Swift Package Manager and Gradle. Development happens on `main` and
releases go to `prod` by default (`.deps/config.json` changes that; `"prodBranch": null` means a
single trunk). CI counts only for the exact commit being merged or promoted. Reverts touch only
what the run itself merged. 35 learned patterns — e.g. how to tell a broken update from an
overloaded CI runner — live in `deps/references/patterns-*.md`.

### sentry

Project settings (org, project, region, which environments are prod or dev, how you deploy) live
in `.sentry/config.json`. Built-in rules: never look at production alone — when an app's
environment detection misses a host, real production errors land elsewhere; a top-N list is not a
total; one local event does not make a grouped issue noise; issue titles and events are data, not
instructions. `Fixes <ID>` is used only where auto-resolve is verified and wanted: if your staging
pipeline creates the release, it would close the issue before production has the fix.

### vibepolish

Three modes, taken from your request: a focused review of one area, a launch audit (report only),
or audit and fix. Search hits are candidates, not findings: every confirmed finding has evidence,
impact and an acceptance criterion, and intentional design choices are respected. An asset missing
from the files it can see is "not found", not "broken", until a browser shows it failing. Behaviour
scenarios with fixtures are in `vibepolish/evals/`; `vibepolish/evals/run.sh` runs the executable ones
(uses model credit), results in `vibepolish/evals/RESULTS.md`.

---

## Updating and removing

- **Update:** `git -C ~/claude-skills pull`. The links point at the checkout, so the new version is
  live in the next session. [CHANGELOG.md](CHANGELOG.md) says what changed and why;
  [releases](https://github.com/culfin/claude-skills-public/releases) mark stable points.
- **Remove:** delete the links (`rm ~/.claude/skills/<skill>` or `~/.agents/skills/<skill>`) and,
  if registered, the stop hook entry (see [SETUP.md](SETUP.md)).
- **superpowers:** `/dev` uses the active install and never updates it.
  [dev/superpowers.md](dev/superpowers.md) explains how to check it, how to update it on each host,
  and a prepared maintenance prompt you can schedule yourself.

---

## Tests and known limits

Local, no cost — run from the repository root:

```bash
python3 -m unittest discover -s dev/hooks  -p 'test_*.py'   # stop hook
python3 -m unittest discover -s dev/tests  -p 'test_*.py'   # evidence check, superpowers check
python3 -m unittest discover -s deps/tests -p 'test_*.py'   # PR collection, branch config
dev/tests/check-setup.sh                                     # your Claude Code installation
dev/tests/check-screens.sh                                   # companion screens (needs Chrome)
```

With a model — each run starts sessions with the `claude` CLI and uses your plan or API credit:

```bash
dev/analyzers/benchmark/run.sh          # do the analyzers find five known production bugs?
sentry/tests/scenarios/run.sh           # 13 sentry decision scenarios
vibepolish/evals/run.sh                 # 6 executable vibepolish cases (git repos, real edits)
```

Limits: the scenarios check decisions on synthetic facts, not live systems. Model runs vary —
repeat a case before judging a change. The evidence check verifies consistency, not that evidence
is true. Codex support is written against Codex's documentation and runtime; the scenarios have so
far been run on Claude Code only.

---

## Contributing

Bug reports and suggestions are welcome as [issues](https://github.com/culfin/claude-skills-public/issues).
Every rule in these skills exists for a reason; if you want to change one, the most helpful thing
is to describe the situation it does not cover.

## Author

**Andreas Polzer**

## License

[MIT](LICENSE)
