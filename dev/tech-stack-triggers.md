# Tech-Stack- und Security-Trigger

Ausgelagert aus `SKILL.md`, weil diese Matrizen nur an zwei Stellen gebraucht werden:
beim Brainstorming (4a) und beim Gate-Eintritt (5c). Die **Detection** selbst (welcher Stack
liegt vor → `$TECH_STACKS`) steht weiterhin in `SKILL.md`, sie läuft bei jedem Session Start.

## Where Tech Skills Auto-Trigger

**During Brainstorming (step 4a):**
- If phase `@type:` is `ui` and `shadcn` is in `$TECH_STACKS` → invoke `/shadcn` for component discovery and usage examples before designing
- If phase `@type:` is `backend` and `postgres` is in `$TECH_STACKS` → invoke `pg:design-postgres-tables` for schema guidance when DB changes are planned
- If phase involves new pages/routes and `nextjs` is in `$TECH_STACKS` → include `next-best-practices` context (RSC boundaries, file conventions, data patterns)

**During Quality Gate — Parallel Analysis Block (step 5c):**

**Tech-Stack Review** — auto-triggered based on which files the phase actually changed:

| Geänderte Dateien | Bedingung | Skill | Modus |
|-------------------|-----------|-------|-------|
| `src/app/**`, `src/pages/**`, `next.config.*` | `nextjs` in `$TECH_STACKS` | `next-best-practices` | Prüfe geänderte Dateien gegen Next.js-Patterns (RSC boundaries, metadata, route handlers) |
| `src/components/**` mit shadcn-Imports | `shadcn` in `$TECH_STACKS` | `shadcn` | Prüfe korrekte Nutzung, fehlende Varianten, Accessibility |
| `src/components/**`, `src/app/**` UI-Dateien | `@type: ui` | `ui-scan` | Accessibility-Scan: fehlende ARIA-Labels, Kontrast, Keyboard-Navigation, Screen-Reader-Unterstützung |
| `src/db/migrations/**`, SQL-Dateien, Schema-Änderungen | `postgres` in `$TECH_STACKS` | `pg:design-postgres-tables` | Prüfe Indexing, Constraints, Typen-Wahl |
| `**/*.swift` | `ios` in `$TECH_STACKS` | `swiftui-pro` | Prüfe moderne APIs, Performance-Patterns |
| `**/*.cs`, `**/*.xaml` | `winui` in `$TECH_STACKS` | `winui-pro` | Prüfe MVVM, Threading, WinUI-Patterns |
| `**/*.rs` | `rust` in `$TECH_STACKS` | `rust-best-practices` | Prüfe Ownership/Borrowing, Error-Handling (thiserror/anyhow), idiomatische APIs, Clippy-Findings |
| `src-tauri/**` (Tauri-Commands/IPC) | `tauri` in `$TECH_STACKS` | `tauri-v2` | Prüfe Command-Signaturen, IPC-Grenzen, Capabilities/Permissions |
| `**/*.svelte`, `src/lib/**` | `svelte` in `$TECH_STACKS` | `svelte:svelte-core-bestpractices` | Prüfe Runes-State ($state/$derived/$effect), Reaktivität, Event-Handling, Bits-UI-Integration; bei Bedarf Svelte-MCP `svelte-autofixer` |

**Security Review** — auto-triggered when changed files touch security-sensitive areas:

| Geänderte Dateien | Trigger-Bedingung | Modus |
|-------------------|------------------|-------|
| `**/auth*`, `**/login*`, `**/session*`, `**/middleware*` | Auth-Code geändert | `/security-audit` (Phase-Scope) |
| `src/app/api/**`, `src/actions/**`, `**/route.ts` | API-Endpoints geändert | `/security-audit` (Phase-Scope) |
| `src/db/migrations/**`, SQL, ORM-Schema | DB-Schema geändert | `/security-audit` (Phase-Scope) |
| Phase `@type: auth` oder `@type: backend` | Phase-Typ | `/security-audit` (Phase-Scope) |

**Analyse-Werkzeug je Stack** (seit 25.09.2026) — gilt für die Security-Review-Trigger oben, für Schritt 5c-i und für die Full-Scans am Milestone-Ende und im Pre-Release-Review:

| Stack (`$TECH_STACKS`) | Bug-Suche | Sicherheit |
|---|---|---|
| Swift/iOS/macOS | `/bug-prospector` | `/security-audit` |
| Web (TS/JS/Svelte, Next.js), Rust, gemischt (z.B. Tauri: Svelte + Rust) und alle anderen | `bug-prospector-neutral` — der Subagent liest `~/.claude/skills/bug-prospector-neutral/SKILL.md` | `/security-review` (prüft den Diff des Branches). Full-Scans: Subagent mit dem Auftrag, den gesamten Code nach denselben Kategorien wie `/security-review` zu prüfen (Injection, Auth/Zugriff, Secrets, unsichere Daten- und Dateiverarbeitung) |

**Werkzeugwahl je Datei**, wenn ein Projekt Swift und anderes mischt (z.B. iOS-App mit Web-Backend): Swift-Dateien gehen an die Originale, alle übrigen an `bug-prospector-neutral` / `/security-review`; sind beide Gruppen betroffen, laufen beide.

**Regeln:**
- Tech-Stack Reviews und Security Review sind **read-only Analysen** — sie flaggen Probleme, fixen nicht automatisch.
- Nur auslösen wenn tatsächlich relevante Dateien geändert wurden — nicht bei jeder Phase blind.
- Kritische Findings (falsche RSC-Boundary, fehlender DB-Index auf FK, unsafe threading, SQL-Injection, Auth-Bypass) → fixen **vor 5d**, nicht später: `/scan-similar-bugs` (5d) sucht die Muster der gerade gemachten Fixes. Läuft es auf ungefixtem Code, findet es nichts.
- Hinweise (könnte besser sein, alternative API verfügbar) → notieren, weiter.
- Wenn der jeweilige Skill nicht installiert ist → warnen, überspringen.
- **Parallelisierung:** Tech-Stack Review, Security Review, `/bug-prospector`, `/performance-check` sind alle read-only — sie können als parallele Agent-Subagenten laufen (Step 5c).
