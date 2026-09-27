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
| `src/components/**`, `src/app/**` UI files | `@type: ui` | `ui-scan` | Accessibility scan: missing ARIA labels, contrast, keyboard navigation, screen-reader support |
| `src/db/migrations/**`, SQL files, schema changes | `postgres` in `$TECH_STACKS` | `pg:design-postgres-tables` | Check indexing, constraints, type choices |
| `**/*.swift` | `ios` in `$TECH_STACKS` | `swiftui-pro` | Check modern APIs, performance patterns |
| `**/*.cs`, `**/*.xaml` | `winui` in `$TECH_STACKS` | `winui-pro` | Check MVVM, threading, WinUI patterns |
| `**/*.rs` | `rust` in `$TECH_STACKS` | `rust-best-practices` | Check ownership/borrowing, error handling (thiserror/anyhow), idiomatic APIs, Clippy findings |
| `src-tauri/**` (Tauri commands/IPC) | `tauri` in `$TECH_STACKS` | `tauri-v2` | Check command signatures, IPC boundaries, capabilities/permissions |
| `**/*.svelte`, `src/lib/**` | `svelte` in `$TECH_STACKS` | `svelte:svelte-core-bestpractices` | Check runes state ($state/$derived/$effect), reactivity, event handling, Bits UI integration; if needed, Svelte MCP `svelte-autofixer` |

**Security Review** — auto-triggered when changed files touch security-sensitive areas:

| Changed files | Trigger condition | Mode |
|-------------------|------------------|-------|
| `**/auth*`, `**/login*`, `**/session*`, `**/middleware*` | Auth code changed | `/security-audit` (phase scope) |
| `src/app/api/**`, `src/actions/**`, `**/route.ts` | API endpoints changed | `/security-audit` (phase scope) |
| `src/db/migrations/**`, SQL, ORM schema | DB schema changed | `/security-audit` (phase scope) |
| Phase `@type: auth` or `@type: backend` | Phase type | `/security-audit` (phase scope) |

**Analysis tool per stack** (since 2026-09-25) — applies to the security review triggers above, to step 5c-i, and to the full scans at milestone end and in the pre-release review:

| Stack (`$TECH_STACKS`) | Bug hunting | Security |
|---|---|---|
| Swift/iOS/macOS | `/bug-prospector` | `/security-audit` |
| Web (TS/JS/Svelte, Next.js), Rust, mixed (e.g. Tauri: Svelte + Rust) and all others | A stack-neutral bug hunter: `bug-prospector-neutral` if installed (the subagent reads `~/.claude/skills/bug-prospector-neutral/SKILL.md`), otherwise `/bug-prospector` with the instruction to skip Swift-specific patterns and apply the seven lenses to the project's language | `/security-review` (checks the branch diff). Full scans: a subagent tasked with checking the entire codebase for the same categories as `/security-review` (injection, auth/access, secrets, unsafe data and file handling) |

**Tool choice per file** when a project mixes Swift with something else (e.g. an iOS app with a web backend): Swift files go to the originals, all others to the stack-neutral bug hunter / `/security-review`; if both groups are affected, both run.

**Rules:**
- Tech-Stack Reviews and Security Review are **read-only analyses** — they flag problems, they do not fix automatically.
- Only trigger when relevant files were actually changed — not blindly on every phase.
- Critical findings (wrong RSC boundary, missing DB index on an FK, unsafe threading, SQL injection, auth bypass) → fix **before 5d**, not later: `/scan-similar-bugs` (5d) searches for the patterns of the fixes just made. If it runs on unfixed code, it finds nothing.
- Notices (could be better, alternative API available) → note them, continue.
- If the respective skill is not installed → warn, skip.
- **Parallelization:** Tech-Stack Review, Security Review, `/bug-prospector`, `/performance-check` are all read-only — they can run as parallel Agent subagents (step 5c).
