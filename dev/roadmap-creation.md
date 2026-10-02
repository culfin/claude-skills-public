# Roadmap Creation — Detail

**Triggered by:** `/dev init`

If ROADMAP.md exists: AskUserQuestion — Overwrite (Recommended) or Cancel.

### Interactive flow using AskUserQuestion:

**1. Project goal** — free text via Other
**2. Phase types** — multiSelect from the built-in types in `gate.md`: UI, Landing (landing pages, marketing — bold design), Backend, Auth, Security, Refactor, Data, Migration, Docs + Other
**3. Milestone count** — adaptive single-select based on project scope:
  - Small (1-3 phases): 1, 2 (Recommended), 3 + Other
  - Medium (4-6 phases): 3, 4 (Recommended), 5 + Other
  - Large (7+ phases): 4, 5, 6+ (Recommended) + Other
**4. Per milestone** — name/goal (free text), phases (multiSelect from types), per-phase skills (multiSelect, optional)
**5. Skill discovery and triggers:**

First, discover what skills are available and what might be missing:

**5a. List installed skills** — check what's already available:
1. Try `npx skills ls -g`
2. If `skills` CLI is not installed: check `~/.claude/skills/` and `.claude/skills/` directories directly via Glob
3. List skills from the Skill tool's available skills list (visible in system context)

**5b. Analyze gaps** — based on the project's tech stack (from CLAUDE.md, package.json, project.yml, .csproj, etc.), identify what skill categories might be missing. For example:
- Swift project but no `swiftui-pro`? → suggest installing
- React project but no `next-best-practices`? → suggest installing
- No testing skill for the project's test framework? → search for one

**5c. Search for missing skills** — if gaps exist:

1. **Try `npx skillfish find <query>`** — searches the Skill.Fish registry. Run one query per gap.
2. **If skillfish is not installed or finds nothing:** Use WebSearch to find skills for the tech stack (e.g., "claude code skill react"), or check GitHub repos with `.claude/skills/` directories.
3. **If no external skills found:** Skip — the built-in skills and superpowers are sufficient for most projects.

**5d. Security review before installing** — for any external skill found:
- Read the SKILL.md content via WebFetch (raw GitHub URL)
- Check for suspicious patterns: shell commands that exfiltrate data, encoded strings, network calls to unknown hosts, file operations outside project scope
- AskUserQuestion: "Found skill X from <source>. Install? (Recommended)" with description of what it does
- Only install after user confirms. Install command: try `npx skills add <url> -y -g`, fallback to manual download into `~/.claude/skills/`

**5e. Configure triggers** — multiSelect per trigger point:
  - milestone-start, milestone-end, pre-release
  - pre-phase and post-phase per type

Show both installed and newly discovered skills as options.

**Placement guidance for the user:**
- **Read-only analysis** (reports, audits, stack-specific reviews) → safe as automatic triggers
- **Code-modifying** (refactoring tools, test generators) → better on-demand, not automatic
- **Project-type-dependent** (browser automation: web only, store screenshots: app stores only)

The gate's own analyzers (`analyzers/`) are not configured here — they always run.

**Recommended defaults** (mark as Recommended in AskUserQuestion):

Note: `/simplify`, Change review, Bug hunt (phase-scope), Performance review (phase-scope), and E2E/integration tests are hardcoded as mandatory in the Quality Gate (step 5) and do NOT need to be configured here. Bug hunt (full) + Performance review (full) + Dead-code scan (quick) are mandatory at milestone-end. Bug hunt (full) + Performance review (full) + Dead-code scan (full) are mandatory at pre-release. Only list additional, optional skills below.

- Post-phase any: `requesting-code-review`
- Post-phase UI (web): `playwright-cli` (for interactive browser testing beyond E2E)
- Post-phase UI (native): `writing-clearly-and-concisely`

**6. Preview and confirm** — Write and commit (Recommended), Edit first, Start over.

Write ROADMAP.md to project root.

**7. Create STATE.md** — always create alongside ROADMAP.md:

```markdown
# <Project name> — Project State

## Current Position

Milestone: 1 of N (<milestone name>)
Next phase: Phase 1 — <phase name>
Status: Starting
Last activity: <today's date> — project initialized

## Progress

| Milestone | Progress | Status |
|-----------|------------|--------|
| 1. <Name> | 0/N | Not started |
| ... | | |

## Core Value

<one sentence from the project goal>

## Constraints

<from user input at init, or empty>

## Requirements

<from user input, or "Open — defined in the first milestone">

## Blockers & Risks

None.

## Session Continuity

Last session: <today's date>
Stopped at: project initialized
Resume: `/dev next` to start the first phase
```

Commit both ROADMAP.md and STATE.md together.
