# `/dev check` — Standalone Quality Gate

Ausgelagert aus `SKILL.md`: dieser Ablauf wird ausschließlich von `/dev check` gebraucht und
hat mit dem Phasen-Lifecycle nichts zu tun. Er fährt **dieselben** Schritte 5a–5k wie das
Phasen-Gate, nur mit `$CHECK_SCOPE` anstelle der phasengeänderten Dateien — die Schrittdefinitionen
selbst stehen in `SKILL.md` unter „Mandatory Quality Gate".

## Ablauf

**Triggered by:** `/dev check`

**Precondition:** No active phase.
- If ROADMAP.md exists and contains a phase with `[~]` or `[!]`: stop with "Phase N ist noch aktiv (`[~]`/`[!]`). Nutze `/dev next` um den Quality Gate der laufenden Phase abzuschließen."
- If ROADMAP.md exists and all phases are `[x]` or `[—]` (dormant): proceed normally.
- If no ROADMAP.md: proceed, but skip STATE.md integration. Check-Commit is still created.

**1. Snapshot scope** — before ANY skill runs, capture changed files:

```bash
git diff --name-only HEAD
git diff --name-only --cached
git ls-files --others --exclude-standard   # neue, ungetrackte Dateien
```

Collect all three outputs, deduplicate, and store as `$CHECK_SCOPE`. This list is immutable for the entire run — later auto-fixes by `/simplify` do not change it.

If `$CHECK_SCOPE` is empty: AskUserQuestion — "Keine Änderungen seit dem letzten Commit gefunden. Trotzdem fortfahren?" (Ja / Nein).
- **Ja**: all scope-dependent steps run in full-codebase mode.
- **Nein**: stop, no action.

**2. Run full Quality Gate** — same steps 5a–5k as the phase gate, with `$CHECK_SCOPE` replacing "phase-changed files":

| Step | Tool | Notes |
|------|------|-------|
| 5a | `/simplify` | Scope: `$CHECK_SCOPE` |
| 5b | `/review-changes` | Scope: `$CHECK_SCOPE` |
| 5c-i | `/bug-prospector` | Scope: `$CHECK_SCOPE`; Werkzeug je Stack (`tech-stack-triggers.md`) |
| 5c-ii | `/performance-check` | Scope: `$CHECK_SCOPE` |
| 5c-iii | Tech-Stack Review | Conditional — same trigger matrix as gate, evaluated against `$CHECK_SCOPE` |
| 5c-iv | `/security-audit` | Conditional — same trigger matrix as gate, evaluated against `$CHECK_SCOPE`; Werkzeug je Stack |
| 5c-v | Spec-Prüfer | Nur wenn der Nutzer eine Spec nennt; sonst entfällt er mit Vermerk „keine Spec" |
| 5d | `/scan-similar-bugs` | After fixes from 5c |
| 5e | tsc + lint + unit tests | Full suite |
| 5f | Production Build | Full build |
| 5g | E2E Tests | Full suite |
| 5h | — | entfällt; Test-Lücken meldet 5c-v |
| 5i | Check-Summary | Written to STATE.md (see below); skipped if no ROADMAP.md |
| 5j | Check-Commit | `chore: dev check [gate-pass]` |
| 5k | CI-Status-Check | Conditional — if `.github/workflows/` exists or `@gate: ci-wait` set on any phase. When no ROADMAP.md: only `.github/workflows/` triggers this step. |

Steps 5c run as parallel Agent subagents (15-minute timeout). Any step failure stops the run — no Check-Commit is created.

**3. Check-Summary format** (STATE.md, inside `## Context`, same area as `### Gate-Summary` entries):

```markdown
### Check-Summary — YYYY-MM-DD — N Dateien
- Gefunden: <N kritisch + M Hinweise> (simplify: X Fixes, bug-prospector: Y Findings, security: W Findings)
- Behoben: <was fixiert wurde, in einem Satz>
- Tests: <Spec-Prüfer N Lücken, Tests rot→grün belegt | keine Lücken>
```

Heading uses `gesamte Codebase` instead of `N Dateien` when full-codebase mode was used. Same-day duplicates get ` #2`, ` #3` suffix. Check-Summaries are permanent — never removed.

**4. Post-check summary** — after step 5k, show a summary of what ran:

- **≥ 3 findings across all checks:** Start Visual Companion server automatically (no user prompt). Render a findings dashboard — findings grouped by category (kritisch / Hinweis), tools that ran, what was fixed. Same structure as the existing Quality Gate Summary dashboard in the skill. Runs regardless of whether ROADMAP.md exists.
- **< 3 findings:** Terminal-only — do not echo STATE.md content again. Show two-line confirmation:

```
✓ Alle Checks grün — [N kritisch + M Hinweise behoben]
Scope: N Dateien | Commit: chore: dev check [gate-pass]
```

(`N Dateien` wird zu `gesamte Codebase` wenn Full-Codebase-Mode aktiv war.)

**5. Post-check action** — AskUserQuestion after the summary:

| ROADMAP.md-Status | Optionen |
|-------------------|---------|
| Kein ROADMAP.md | "Fertig" |
| Abgeschlossen (alle `[x]`/`[—]`) | "Fertig" + "Pre-Release Review starten" |
| Aktiv (mind. eine `[ ]`-Phase) | "Fertig" + "Nächste Phase starten" |

- **Fertig** — no further action
- **Nächste Phase starten** — triggers the same flow as `/dev next`
- **Pre-Release Review starten** — triggers `/dev review`
