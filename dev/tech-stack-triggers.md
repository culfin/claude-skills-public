# Tech stack and security triggers

Moved out of `SKILL.md` because these matrices are needed in only two places:
during brainstorming (4a) and on gate entry (5c). The **detection** itself (which stack
is present → `$TECH_STACKS`) remains in `SKILL.md`; it runs at every session start.

## Where Tech Skills Auto-Trigger

**During Brainstorming (step 4a):**
- If phase `@type:` is `ui` and `shadcn` is in `$TECH_STACKS` → invoke `/shadcn` for component discovery and usage examples before designing
- If phase `@type:` is `backend` and `postgres` is in `$TECH_STACKS` → invoke `pg:design-postgres-tables` for schema guidance when DB changes are planned
- If phase involves new pages/routes and `nextjs` is in `$TECH_STACKS` → include `next-best-practices` context (RSC boundaries, file conventions, data patterns)

**During Quality Gate — Parallel Analysis Block (step 5c):**

**Tech-Stack Review** — auto-triggered based on which files the phase actually changed:

| Changed files | Condition | Skill | Mode |
|-------------------|-----------|-------|-------|
| `src/app/**`, `src/pages/**`, `next.config.*` | `nextjs` in `$TECH_STACKS` | `next-best-practices` | Check changed files against Next.js patterns (RSC boundaries, metadata, route handlers) |
| `src/components/**` with shadcn imports | `shadcn` in `$TECH_STACKS` | `shadcn` | Check correct usage, missing variants, accessibility |
| `src/components/**`, `src/app/**` UI files, SwiftUI views | `@type: ui` | Accessibility review (`analyzers/accessibility.md`) | Accessibility scan: missing ARIA labels, contrast, keyboard navigation, screen-reader support |
| `src/db/migrations/**`, SQL files, schema changes | `postgres` in `$TECH_STACKS` | `pg:design-postgres-tables` | Check indexing, constraints, type choices |
| `**/*.swift` | `ios` in `$TECH_STACKS` | `swiftui-pro` | Check modern APIs, performance patterns |
| `**/*.cs`, `**/*.xaml` | `winui` in `$TECH_STACKS` | `winui-pro` | Check MVVM, threading, WinUI patterns |
| `**/*.rs` | `rust` in `$TECH_STACKS` | `rust-best-practices` | Check ownership/borrowing, error handling (thiserror/anyhow), idiomatic APIs, Clippy findings |
| `src-tauri/**` (Tauri commands/IPC) | `tauri` in `$TECH_STACKS` | `tauri-v2` | Check command signatures, IPC boundaries, capabilities/permissions |
| `**/*.svelte`, `src/lib/**` | `svelte` in `$TECH_STACKS` | `svelte:svelte-core-bestpractices` | Check runes state ($state/$derived/$effect), reactivity, event handling, Bits UI integration; if needed, Svelte MCP `svelte-autofixer` |

**Security Review** — auto-triggered when changed files touch security-sensitive areas:

| Changed files | Trigger condition | Mode |
|-------------------|------------------|-------|
| `**/auth*`, `**/login*`, `**/session*`, `**/middleware*` | Auth code changed | Security review (phase scope) |
| `src/app/api/**`, `src/actions/**`, `**/route.ts` | API endpoints changed | Security review (phase scope) |
| `src/db/migrations/**`, SQL, ORM schema | DB schema changed | Security review (phase scope) |
| Phase `@type: auth` or `@type: backend` | Phase type | Security review (phase scope) |

**Analyzers:** every analysis above and in gate step 5c is carried out by a subagent with the
matching file from `analyzers/` (contract in `analyzers/CONTRACT.md`) — bug hunt, security, performance,
accessibility. They work for every stack; each carries short notes per language (Swift, TS/JS, Rust,
PHP, Python, shell, SQL). A project that wants an extra, stack-specific analysis on top names it via
`@skills:` in ROADMAP.md; `/dev` does not depend on any.

**Rules:**
- Tech-Stack Reviews and Security Review are **read-only analyses** — they flag problems, they do not fix automatically.
- Only trigger when relevant files were actually changed — not blindly on every phase.
- Critical findings (wrong RSC boundary, missing DB index on an FK, unsafe threading, SQL injection, auth bypass) → fix **before 5d**, not later: Similar-bugs scan (5d) searches for the patterns of the fixes just made. If it runs on unfixed code, it finds nothing.
- Notices (could be better, alternative API available) → note them, continue.
- A tech skill (next-best-practices, shadcn, …) that is not installed → warn, skip; it is an extra on top of the analyzers. The analyzers themselves are always there.
- **Parallelization:** Tech-Stack Review, Security Review, Bug hunt, Performance review are all read-only — they can run as parallel Agent subagents (step 5c).
