# claude-skills

**Arbeitsabläufe für [Claude Code](https://claude.com/claude-code), die im täglichen Einsatz an
Produktivprojekten entstanden sind:** ein Orchestrator, der Projekte Phase für Phase durch ein
verpflichtendes Quality Gate führt, eine Verwaltung für Abhängigkeits-Updates und
Sicherheitswarnungen und ein Analysewerkzeug für Fehler, die Linter und Tests nicht finden.

> **Sprache:** Die Skills sind auf Deutsch geschrieben und lassen Claude auf Deutsch antworten.
> Befehle, Dateinamen und Commit-Präfixe bleiben englisch.
> *The skills are written in German and make Claude reply in German.*

---

## Inhalt

| Skill | Aufruf | Zweck |
|---|---|---|
| [**dev**](dev/SKILL.md) | `/dev` | Führt ein Projekt anhand einer `ROADMAP.md` durch Klärung, Planung, Umsetzung und Qualitätsprüfung. |
| [**deps**](deps/SKILL.md) | `/deps` | Verwaltet Dependabot-Updates und Sicherheitswarnungen von der Analyse bis zur Auslieferung. |
| [**bug-prospector-neutral**](bug-prospector-neutral/SKILL.md) | über `/dev` oder auf Wunsch | Sucht versteckte Fehler durch sieben Analyseperspektiven, unabhängig von der Programmiersprache. |

---

## `/dev` — Projekte in Phasen, jede mit Quality Gate

`/dev` ist ein Dirigent: Er schreibt selbst keinen Code, sondern ruft zur richtigen Zeit die
passenden Skills auf und sorgt dafür, dass keine Phase ohne Prüfung als erledigt gilt.

**Ablauf einer Phase**

1. **Klärung** — Fragen in Runden mit Auswahlmöglichkeiten, die empfohlene Antwort zuerst.
   Architekturentscheidungen werden als Diagramm, Oberflächenfragen als Entwurf im Browser
   gezeigt (Visual Companion).
2. **Plan und Umsetzung** — über die Skills des Plugins
   [superpowers](https://github.com/obra/superpowers): Spezifikation, Implementierungsplan,
   Umsetzung durch Subagenten mit Review je Aufgabe.
3. **Quality Gate** — nicht abschaltbar. Code-Bereinigung, Review, parallele Analysen (Fehler,
   Performance, Sicherheit, Stack-spezifische Regeln), Abgleich gegen die Spezifikation,
   Typprüfung, Lint, Tests, Produktions-Build, E2E-Tests und CI-Status.
4. **Abschluss** — ein Gate-Commit mit `[gate-pass]` im Betreff, eine Zusammenfassung in
   `STATE.md` und der Haken in der Roadmap.

**Grundsätze, die der Skill durchsetzt**

- **Jeder Haken braucht einen Beleg.** Ein Prüfschritt gilt erst als erledigt, wenn seine
  Ausgabe gelesen und notiert ist.
- **Tests müssen einmal rot gewesen sein.** Fehlt für ein Akzeptanzkriterium ein Test, wird er
  geschrieben und gegen eine absichtlich gebrochene Stelle geprüft.
- **Halt bei Irreversiblem.** Migrationen, Deploys, Releases, Force-Pushes und Nachrichten an
  echte Empfänger brauchen eine ausdrückliche Freigabe, auch wenn der Plan sie vorsieht.
- **Zustand überlebt die Sitzung.** `ROADMAP.md` und `STATE.md` halten fest, wo die Arbeit
  steht; eine unterbrochene Phase wird beim nächsten `/dev` fortgesetzt.

**Befehle**

| Befehl | Wirkung |
|---|---|
| `/dev init` | Legt `ROADMAP.md` und `STATE.md` im Dialog an. |
| `/dev` · `/dev next` | Zeigt den Stand und startet oder setzt die nächste Phase fort. |
| `/dev status` | Vollständige Roadmap-Übersicht. |
| `/dev add` · `skip` · `reorder` | Roadmap pflegen. |
| `/dev check` | Das Quality Gate für Änderungen außerhalb einer Phase. |
| `/dev debug` | Systematische Fehlersuche mit Wissensbasis aus früheren Fällen. |
| `/dev review` | Vollprüfung vor einem Release. |
| `/dev pause` | Sitzung sauber übergeben. |

Ein optionaler **Stop-Hook** (`dev/hooks/gate-check.py`) erinnert einmal je Sitzung an
`/dev check`, wenn in einem Roadmap-Projekt Code ohne anschließenden Gate-Commit geändert wurde.

---

## `/deps` — Abhängigkeiten aktuell und sicher halten

Führt Dependabot-Pull-Requests und Sicherheitswarnungen durch einen nachvollziehbaren Ablauf,
statt sie ungeprüft zu mergen oder liegen zu lassen.

| Befehl | Wirkung |
|---|---|
| `/deps` | Stand: offene Updates, offene Sicherheitswarnungen, Abstand zwischen Entwicklungs- und Produktionszweig. |
| `/deps check` | Wirkung aller offenen Updates und Warnungen analysieren, ohne etwas zu ändern. |
| `/deps merge` | Geeignete Updates mergen, testen und einen Bericht erstellen. |
| `/deps audit` | Sicherheitswarnungen abarbeiten, transitive Lücken per Override schließen. |
| `/deps close` | Überholte und verwaiste Update-PRs schließen. |
| `/deps promote` | Den geprüften Stand per Pull Request in den Produktionszweig bringen. |
| `/deps setup` | Einmalige Einrichtung im Projekt. |

Unterstützt npm, pnpm, Yarn, Bun, Cargo, Swift Package Manager und Gradle. Standardmäßig wird auf `main`
entwickelt und nach `prod` ausgeliefert; abweichende Zweignamen stehen in `.deps/config.json`.
Der Skill enthält 34 im Betrieb gelernte Muster, etwa wie sich ein echter
Update-Fehler von einer überlasteten CI unterscheiden lässt.

---

## `bug-prospector-neutral` — Fehler finden, die niemand gesucht hat

Linter finden Muster, Tests prüfen, woran man gedacht hat. Dieser Skill sucht das Dritte: Stellen,
an denen der Code stillschweigend etwas annimmt, das nicht immer gilt. Er betrachtet den Code
durch sieben Linsen:

1. Annahmen
2. Zustandsautomaten
3. Grenzwerte
4. Datenlebenszyklus
5. Fehlerpfade
6. Zeitabhängiges Verhalten
7. Plattformunterschiede

Das Ergebnis ist ein Bericht mit Fundstellen, Schweregrad und Begründung. `/dev` setzt ihn im
Quality Gate automatisch ein; direkt aufgerufen wird er nur auf ausdrücklichen Wunsch.

---

## Installation

**Voraussetzung:** [Claude Code](https://claude.com/claude-code).

```bash
git clone https://github.com/culfin/claude-skills-public.git ~/claude-skills
mkdir -p ~/.claude/skills
for s in dev deps bug-prospector-neutral; do
  ln -sfn ~/claude-skills/$s ~/.claude/skills/$s
done
```

Die Skills stehen danach in jeder Claude-Code-Sitzung zur Verfügung. Wer nur einzelne braucht,
verlinkt nur diese.

**Stop-Hook für `/dev` (optional)**

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

**Einrichtung prüfen**

```bash
~/claude-skills/dev/tests/check-setup.sh
```

### Weitere Voraussetzungen für `/dev`

| Was | Wofür |
|---|---|
| Plugin [superpowers](https://github.com/obra/superpowers) | Brainstorming, Pläne, Umsetzung durch Subagenten, Visual Companion |
| Skills aus [Terryc21/xcode-workflow-skills](https://github.com/Terryc21/xcode-workflow-skills) | Analysen im Quality Gate für Swift-Projekte (`bug-prospector`, `performance-check`, `scan-similar-bugs`, …). Web- und Rust-Projekte nutzen `bug-prospector-neutral`. |
| Google Chrome | nur für `dev/tests/check-screens.sh` |

**Visual Companion von einem anderen Gerät öffnen:** Standardmäßig lauscht der Server nur auf
`localhost`. Wer ihn etwa über Tailscale vom Tablet aus nutzen will, setzt vorher

```bash
export DEV_COMPANION_URL_HOST=mein-rechner.tailnet.ts.net
```

Der Server lauscht dann auf allen Schnittstellen und nennt diesen Host in seiner Adresse.

---

## Tests

```bash
cd dev/hooks && python3 -m unittest test_gate_check   # Stop-Hook
dev/tests/check-setup.sh                              # Installation
dev/tests/check-screens.sh                            # Darstellung der Companion-Bausteine
```

---

## Mitwirken

Fehler und Vorschläge gern als [Issue](https://github.com/culfin/claude-skills-public/issues).
Die Skills sind aus der Praxis gewachsen; jede Regel darin hat einen Anlass. Wer eine ändern
möchte, beschreibt am besten, welche Situation sie nicht abdeckt.

## Autor

**Andreas Polzer**

## Lizenz

[MIT](LICENSE). Ausgenommen ist `bug-prospector-neutral`: Er ist eine Bearbeitung von
„Bug Prospector" aus [Terryc21/xcode-workflow-skills](https://github.com/Terryc21/xcode-workflow-skills)
(Terry Nyberg) und steht unter der Apache License 2.0 — siehe
[LICENSE](bug-prospector-neutral/LICENSE) und [NOTICE](bug-prospector-neutral/NOTICE).
