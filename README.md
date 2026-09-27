# claude-skills

**Workflows for [Claude Code](https://claude.com/claude-code), built and refined in daily use on
production projects:** an orchestrator that takes a project phase by phase through a mandatory
quality gate, and a manager for dependency updates and security alerts.

---

## Contents

| Skill | Invoke | Purpose |
|---|---|---|
| [**dev**](dev/SKILL.md) | `/dev` | Drives a project from a `ROADMAP.md` through clarification, planning, implementation and quality review. |
| [**deps**](deps/SKILL.md) | `/deps` | Manages Dependabot updates and security alerts, from impact analysis to release. |
| [**sentry**](sentry/SKILL.md) | `/sentry` | Triages Sentry issues and fixes them with a regression test — on demand instead of alert noise. |

Both skills answer in the language you write in.

---

## `/dev` — phased delivery with a quality gate

`/dev` is a conductor: it writes no code itself, but calls the right skills at the right time and
makes sure no phase counts as done without being verified.

**A phase, step by step**

1. **Clarify** — questions in rounds with selectable answers, the recommended one first.
   Architecture decisions are shown as diagrams and UI questions as mockups in the browser
   (Visual Companion).
2. **Plan and build** — via the [superpowers](https://github.com/obra/superpowers) plugin:
   specification, implementation plan, execution by subagents with a review per task.
3. **Quality gate** — cannot be switched off. Code cleanup, review, parallel analyses (bugs,
   performance, security, stack-specific rules — the analyzers ship with the skill), a check against the specification, type check,
   lint, tests, production build, end-to-end tests and CI status.
4. **Close** — a gate commit with `[gate-pass]` in the subject, a summary in `STATE.md` and the
   phase checked off in the roadmap.

**Its own analyzers.** The gate's analyses ship with the skill (`dev/analyzers/`) and run as
subagents — no other skills required. `dev/analyzers/benchmark/` measures whether they find known
bugs.

**Principles the skill enforces**

- **Every checkmark needs evidence.** A gate step only counts once its output has been read and
  recorded.
- **Every test must have failed once.** If an acceptance criterion has no test, one is written
  and proven against a deliberately broken implementation.
- **Stop before the irreversible.** Migrations, deploys, releases, force pushes and messages to
  real recipients require explicit approval, even when the plan includes them.
- **State outlives the session.** `ROADMAP.md` and `STATE.md` record where the work stands; an
  interrupted phase resumes on the next `/dev`.

**Commands**

| Command | Effect |
|---|---|
| `/dev init` | Creates `ROADMAP.md` and `STATE.md` interactively. |
| `/dev` · `/dev next` | Shows progress and starts or resumes the next phase. |
| `/dev status` | Full roadmap overview. |
| `/dev add` · `skip` · `reorder` | Maintain the roadmap. |
| `/dev check` | Runs the quality gate on changes made outside a phase. |
| `/dev debug` | Systematic debugging with a knowledge base of past cases. |
| `/dev review` | Full pre-release review. |
| `/dev pause` | Hands the session over cleanly. |

An optional **stop hook** (`dev/hooks/gate-check.py`) reminds you once per session to run
`/dev check` when code in a roadmap project changed without a subsequent gate commit.

---

## `/deps` — keep dependencies current and secure

Takes Dependabot pull requests and security alerts through a traceable process instead of
merging them blindly or letting them pile up.

| Command | Effect |
|---|---|
| `/deps` | Status: open updates, open security alerts, gap between development and production branch. |
| `/deps check` | Analyzes the impact of all open updates and alerts without changing anything. |
| `/deps merge` | Merges eligible updates, runs the tests and writes a report. |
| `/deps audit` | Works through security alerts and closes transitive vulnerabilities via overrides. |
| `/deps close` | Closes superseded and stale update PRs. |
| `/deps promote` | Brings the verified state to the production branch via pull request. |
| `/deps setup` | One-time project setup. |

Supports npm, pnpm, Yarn, Bun, Cargo, Swift Package Manager and Gradle. By default, development
happens on `main` and releases go to `prod`; other branch names can be set in `.deps/config.json`.
The skill carries 35 patterns learned in production — for example, how to tell a genuinely broken
update from an overloaded CI runner.

---

## `/sentry` — look at errors when you decide to

| Command | Effect |
|---|---|
| `/sentry` | Status: unresolved issues per environment, last triage. `prod` / `dev` narrows it. |
| `/sentry check` | Triage: top issues, root cause, a fix proposal with `file:line`. Writes only a local report. |
| `/sentry fix <ID>` | Root cause, a regression test that fails first, the fix, `/dev check` if the project uses `/dev`, a commit with `Fixes <ID>`. Never deploys. |
| `/sentry setup` | Creates `.sentry/config.json`, verifies access, sets up auto-resolve on release. |

Everything project-specific (org, project, region, which environments count as prod or dev, how
you deploy) lives in `.sentry/config.json`. One rule is built in: never look at production alone —
when an app's environment detection misses a host, real production errors land in another
environment. Needs the Sentry MCP server (or the Sentry CLI/API as a substitute).

---

## Installation

**Requirement:** [Claude Code](https://claude.com/claude-code).

```bash
git clone https://github.com/culfin/claude-skills-public.git ~/claude-skills
mkdir -p ~/.claude/skills
for s in dev deps sentry; do
  ln -sfn ~/claude-skills/$s ~/.claude/skills/$s
done
```

The skills are then available in every Claude Code session. Link only the ones you need.

**Codex:** link the same two directories into Codex's skills directory instead. Both skills resolve
their own paths (`runtime.md` in each) and need no Claude-specific setup; the stop hook below is
Claude Code only. For the Visual Companion, set `DEV_SUPERPOWERS_ROOT` to the active superpowers
plugin root.

**Stop hook for `/dev` (optional)**

```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser('~/.claude/settings.json')
s = json.load(open(p)) if os.path.exists(p) else {}
cmd = 'python3 "$HOME/.claude/skills/dev/hooks/gate-check.py"'
stop = s.setdefault('hooks', {}).setdefault('Stop', [])
if not any(cmd in json.dumps(e) for e in stop):
    stop.append({"hooks": [{"type": "command", "command": cmd}]})
open(p, 'w').write(json.dumps(s, indent=2, ensure_ascii=False) + '\n')
PY
```

**Verify the setup**

```bash
~/claude-skills/dev/tests/check-setup.sh
```

### Additional requirements for `/dev`

| What | Why |
|---|---|
| [superpowers](https://github.com/obra/superpowers) plugin | Brainstorming, plans, subagent execution, Visual Companion |
| Nothing else for the quality gate | Its analyses (change review, bug hunt, performance, security, similar bugs, dead code, accessibility) ship with the skill in `dev/analyzers/` and run as subagents. Stack-specific skills can be added per project via `@skills:`. |
| Google Chrome | Only for `dev/tests/check-screens.sh` |

**Opening the Visual Companion from another device:** by default the server listens on
`localhost` only. To use it from, say, a tablet over Tailscale, set

```bash
export DEV_COMPANION_URL_HOST=my-machine.tailnet.ts.net
```

The server then listens on all interfaces and advertises that host in its URL. To make this
permanent for Claude Code, add it under `"env"` in `~/.claude/settings.json`.

---

## Tests

```bash
dev/analyzers/benchmark/run.sh                        # analyzers against known bugs (needs claude CLI)
cd dev/hooks && python3 -m unittest test_gate_check   # stop hook
python3 -m unittest discover -s deps/tests            # deps helper scripts
dev/tests/check-setup.sh                              # installation
dev/tests/check-screens.sh                            # rendering of the companion building blocks
```

---

## Contributing

Bug reports and suggestions are welcome as [issues](https://github.com/culfin/claude-skills-public/issues).
These skills grew out of practice, and every rule in them exists for a reason. If you want to
change one, the most helpful thing is to describe the situation it does not cover.

## Author

**Andreas Polzer**

## License

[MIT](LICENSE)
