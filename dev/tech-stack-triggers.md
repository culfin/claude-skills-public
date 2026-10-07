# Tech stack and security triggers

Read in brainstorming (4a), execution (4c) and the gate's review wave (Step A, tagged `5c` in the
index files). **Detection** (`$TECH_STACKS`) is section 1 of `stack/INDEX.md`, once per session.

**Stack sources — one rule for all three steps.** For every id in `$TECH_STACKS`, consult section 2
of `stack/INDEX.md` and load only the rows whose trigger matches: step 4a → as context before
designing; step 4c → handed to the implementer with the task that meets the trigger; step 5c → as a
read-only review of the changed files in the large tier (one "Tech-Stack Review: <stack id>" item per id). `subagent`
rows come back as findings or a ≤ 40-line digest. Current API facts → `stack/docs.md`, one row.
The matrices below list what the index does not cover (skills, design, analyzers); Next.js keeps
its own item and fallback ("Next.js" below) — its bundled-docs index row is the same source, not a second review; its `next` row is a 4c runtime check.

## Where Tech Skills Auto-Trigger

**During Brainstorming (step 4a):**
- If phase `@type:` is `ui` and `shadcn` is in `$TECH_STACKS` → invoke `/shadcn` for component discovery and usage examples before designing
- If phase `@type:` is `ui` → consult `design/INDEX.md`, load only the rows whose trigger matches the phase (forms, states, onboarding, writing, platform of `$TECH_STACKS`); show variants per the prototype row; rate drafts with `design/density-critique.md`
- If phase `@type:` is `landing` → a subagent reads taste v2 (`design/INDEX.md`, row "4a landing") and returns only the rules relevant to this page (≤ 40 lines); conflicts with the project's component library (icons, dark mode) become interview questions, never silent overrides; copy in drafts per the row "4a ui/landing: copy in drafts"
- If phase `@type:` is `backend` and `postgres` is in `$TECH_STACKS` → invoke `pg:design-postgres-tables` for schema guidance when DB changes are planned
- If phase involves new pages/routes and `nextjs` is in `$TECH_STACKS` → include Next.js context (RSC boundaries, file conventions, data patterns) from the source named under "Next.js" below

**During Execution (step 4c):**
- UI tasks in the plan → pass the `design/INDEX.md` rows marked `4c` whose trigger the task meets (platform of `$TECH_STACKS`, animation, web on a phone, Apple design) to the implementer with the task — only those rows, `subagent` rows as a subagent's ≤ 40-line digest
- Svelte tasks and `svelte` in `$TECH_STACKS` → the implementer uses `svelte:svelte-code-writer` for that task

**During the Quality Gate — review wave (Step A, `5c`):** the Tech-Stack, design and performance
reviews below run in the large tier only (`gate.md`, "Tier"; `@type: landing` adds Accessibility
review and Design detector in either tier). **Security Review runs in either tier** whenever its
matrix matches — the tier script's path patterns are narrower than this matrix.

**Tech-Stack Review** — auto-triggered based on which files the phase actually changed:

| Changed files | Condition | Skill | Mode |
|-------------------|-----------|-------|-------|
| `src/app/**`, `src/pages/**`, `next.config.*` | `nextjs` in `$TECH_STACKS` | Next.js docs (see "Next.js" below) | Check changed files against Next.js patterns (RSC boundaries, metadata, route handlers) |
| `src/components/**` with shadcn imports | `shadcn` in `$TECH_STACKS` | `shadcn` | Check correct usage, missing variants, accessibility |
| `src/components/**`, `src/app/**` UI files, SwiftUI views | UI files changed (any phase type) | Accessibility review (`analyzers/accessibility.md`) | Accessibility scan: missing ARIA labels, contrast, keyboard navigation, screen-reader support, target size |
| `*.tsx`, `*.jsx`, `*.svelte`, `*.vue`, `*.astro`, `*.html`, `*.css`, `*.scss`, `*.less` | Web UI files changed (any phase type) | Design detector (`analyzers/design-detector.md`) | Runs `scripts/design-detect.sh` over the changed files (impeccable's deterministic rules, built locally); exit 3 → item ticked as `skipped: <reason>`, never a pass |
| Files hit by the motion probes (`transition`, `animation`, `@keyframes`, `motion.`, `animate(`, `withSpring`, …) | A motion sweep probe hits in the changed files | Motion review (`analyzers/motion.md`) | Judges each animation against Emil Kowalski's standards read from `$DEV_DESIGN_DIR`; standards missing → item ticked as `skipped: <reason>` |
| `src/db/migrations/**`, SQL files, schema changes | `postgres` in `$TECH_STACKS` | `pg:design-postgres-tables` | Check indexing, constraints, type choices |
| `**/*.swift` | `ios` in `$TECH_STACKS` | `swiftui-pro` | Check modern APIs, performance patterns |
| `**/*.swift` using `async`/`await`, `actor`, `Task`, `Sendable` | `ios` in `$TECH_STACKS` | `swift-concurrency-pro` | Check isolation, data races, structured concurrency |
| Swift test files (`*Tests.swift`, test targets) | `ios` in `$TECH_STACKS` | `swift-testing-pro` | Check Swift Testing usage, assertions, parameterised tests |
| `**/*.cs`, `**/*.xaml` | `winui` in `$TECH_STACKS` | `winui-pro` | Check MVVM, threading, WinUI patterns |
| `**/*.rs` | `rust` in `$TECH_STACKS` | `rust-best-practices` | Check ownership/borrowing, error handling (thiserror/anyhow), idiomatic APIs, Clippy findings |
| Rust tests (`tests/**/*.rs`, files with `#[cfg(test)]`) | `rust` in `$TECH_STACKS` | `rust-testing` | Check test structure, async tests, coverage of the change |
| `src-tauri/**` (Tauri commands/IPC) | `tauri` in `$TECH_STACKS` | `tauri-v2` | Check command signatures, IPC boundaries, capabilities/permissions |
| Files matching a `stack/INDEX.md` row marked `5c` | that row's stack id in `$TECH_STACKS` | the row's file (checkout under `$DEV_STACK_DIR` or bundled docs) | Check the changed files against it; differences from project conventions are notices at most; source missing → item ticked as `skipped: <reason>` |
| `**/*.svelte`, `src/lib/**` | `svelte` in `$TECH_STACKS` | `svelte:svelte-core-bestpractices` | Check runes state ($state/$derived/$effect), reactivity, event handling, Bits UI integration; if needed, Svelte MCP `svelte-autofixer` |

**Security Review** — auto-triggered when changed files touch security-sensitive areas:

| Changed files | Trigger condition | Mode |
|-------------------|------------------|-------|
| `**/auth*`, `**/login*`, `**/session*`, `**/middleware*` | Auth code changed | Security review (phase scope) |
| `src/app/api/**`, `src/actions/**`, `**/route.ts` | API endpoints changed | Security review (phase scope) |
| `src/db/migrations/**`, SQL, ORM schema | DB schema changed | Security review (phase scope) |
| `**/signup*`, `**/register*`, `**/reset*`, `**/otp*`, `**/upload*`, `**/polic*` | Expensive endpoint or access policy changed | Security review (phase scope) |
| Phase `@type: auth`, or `@type: backend` in the large tier | Phase type | Security review (phase scope) |

**Performance review — only on cause.** It runs only when the changed files contain at least one of:
- new or changed DB queries (ORM calls, SQL, query builders);
- loops over collections that come from I/O (database, network, files);
- list rendering of unbounded data (no pagination, no virtualization);
- new endpoints that return collections.

No cause → no Performance review item; its probes found nothing in phases without one.

**Analyzers:** each analysis is a subagent with its file from `analyzers/` (contract in
`analyzers/CONTRACT.md`), for every stack, with short notes per language. Extra stack-specific
analyses go under `@skills:` in ROADMAP.md; `/dev` depends on none.

**Next.js — where the knowledge comes from.** Next.js ships its documentation with the package
(16.3 and later), version-matched to what the project runs. A subagent reads
`node_modules/next/dist/docs/index.md` of the `next` the project resolves (in a monorepo: the
app's own) and from there only the pages that match the changed files or the planned routes; it
returns findings or a ≤ 40-line digest, never the docs themselves. No bundled docs (older Next.js,
dependencies not installed) → fall back to an installed `next-best-practices` skill if there is
one; neither → the item is ticked as `skipped: <reason>`.

**Rules:**
- Tech-Stack Reviews and Security Review are **read-only analyses** — they flag problems, they do not fix automatically.
- Only trigger when relevant files were actually changed — not blindly on every phase.
- Critical findings (wrong RSC boundary, missing DB index on an FK, unsafe threading, SQL injection, auth bypass) → the bundled fix (gate Step B), **before** the Similar-bugs scan (Step C): it searches for the patterns of the fixes just made, and on unfixed code it finds nothing.
- Notices → note, continue.
- A tech skill (shadcn, swiftui-pro, …) that is not installed, a stack checkout missing under `$DEV_STACK_DIR` or bundled docs that are absent → warn, tick its item as `skipped: <reason>`; it is an extra on top of the analyzers. The analyzers themselves are always there.
- Exception: Design detector and Motion review need the optional sources under `$DEV_DESIGN_DIR`; missing → `skipped: <reason>`, listed under "Skipped checks", never "no findings" (`gate.md`).
- **Parallelization:** all read-only, run in the one review wave (gate Step A).
