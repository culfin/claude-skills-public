# Befragung in Runden — Schritt 4a, architektonische Phasen

Herkunft der Technik: `grilling` aus github.com/mattpocock/skills (MIT). Das Format ist eigen:
Auswahlknöpfe statt Fließtext. Spec: `claude-skills/docs/specs/2026-09-25-dev-verbesserungen-design.md`.

Die Befragung ersetzt den Schritt „Klärungsfragen" des Brainstormings — nicht das Brainstorming.
Einstufung, Lösungsansätze, Entwurf, Spec und Sperre bleiben bei `superpowers:brainstorming`.

## Ablauf

1. **Vorhandenes lesen:** ADRs unter `docs/adr/`, bestehende Specs der Roadmap, das Milestone-Ziel.
   Was dort entschieden ist, wird nicht erneut gefragt.
2. **Fakten selbst beschaffen.** Was Code, Konfiguration oder Doku beantworten können, wird
   nachgesehen (bei Bedarf per Subagent) — nie den Nutzer fragen. Läuft eine Suche noch, warten nur
   die Fragen, die von ihr abhängen; die übrigen kommen jetzt.
3. **Entscheidungen in Runden** per `AskUserQuestion`: bis zu vier voneinander **unabhängige**
   Fragen je Runde, jede mit 2–4 Optionen, die empfohlene zuerst mit „(Recommended)" und einer
   Begründung in der Beschreibung. Fragen, die von einer offenen Antwort abhängen, kommen in die
   nächste Runde. **Nie als Fließtext** mit (a)/(b)/(c) — auch nicht in der ersten Runde.
   Enthält die Runde eine Frage mit UI/UX-Seite (Definition in `SKILL.md`), wird **vor dem
   `AskUserQuestion`-Aufruf** der passende Screen geschrieben (Bausteine in `companion-screens.md`)
   und die Companion-URL genannt; die Optionen heißen im Browser und im Terminal gleich.
4. **Ende:** wenn keine Entscheidung mehr offen ist. Die Entscheidungen als kurze Liste
   zusammenfassen und per `AskUserQuestion` bestätigen lassen („Stimmt das so?"). Hat der Nutzer
   eine Runde nur mit den Empfehlungen durchgeklickt und hängt eine spätere Frage an einer dieser
   Antworten, nennt die Zusammenfassung die weitreichendste davon ausdrücklich.
5. **Übergabe an `superpowers:brainstorming`** mit diesem Hinweis, gefolgt von der Liste:

   > Klärung abgeschlossen, Ergebnis unten. Einstufung: architektonisch. Beginne bei den
   > Lösungsansätzen; stelle keine Klärungsfragen, die unten beantwortet sind. Das Verständnis ist
   > bestätigt — nicht erneut zurückspiegeln. Der Visual Companion läuft bereits (URL unten).
   > Biete ihn nicht an, nutze ihn direkt für jede Frage mit UI/UX-Seite und für
   > Architektur-Diagramme; Bausteine in `companion-screens.md` des `/dev`-Skills. Übernimm die Liste
   > als Abschnitt „Entscheidungen aus der Befragung" in die Spec.

## ADRs

- **Kriterium** — alle drei müssen gelten: schwer umkehrbar, ohne Kontext überraschend, Ergebnis
  einer echten Abwägung. „Nicht erneut vorschlagen"-Entscheidungen zählen ausdrücklich dazu.
- **Wann:** sobald eine Entscheidung der Befragung das Kriterium erfüllt, per `AskUserQuestion`
  anbieten („Als ADR festhalten?").
- **Format:** `docs/adr/NNNN-titel.md`, fortlaufend nummeriert (höchste vorhandene Nummer + 1);
  das Verzeichnis erst beim ersten ADR anlegen. Inhalt: Überschrift und ein bis drei Sätze
  (Kontext, Entscheidung, Grund). „Verworfene Alternativen" nur, wenn die Ablehnung nicht
  offensichtlich ist.
- Die Spec verweist auf die ADRs, die in ihrer Befragung entstanden sind.
