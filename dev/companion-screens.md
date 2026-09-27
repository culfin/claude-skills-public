# Companion-Screens — Stilregeln und Bausteine für `/dev`

Verfahren (Server, Alive-Check, URL) steht in `SKILL.md`, Abschnitt „Visual Companion". Hier: wie
ein Screen aussieht. Jeder Baustein ist ein **Content-Fragment** (kein `<html>`/`<head>`, der Server
setzt die Rahmenvorlage drumherum). Mit dem `Write`-Tool in `screen_dir` schreiben, nie per
`cat`/Heredoc. Der Companion zeigt die neueste Datei — für einen neuen Screen eine neue Datei.

**Beispielinhalte stammen aus einem Projekt** (einer Praxis-Software, PDF-Export): Sie zeigen nur die Form.
In jedem Screen stehen die echten Namen, Werte und Texte des aktuellen Projekts.

## Stilregeln

- **Eine Aussage pro Screen**; die Überschrift sagt sie.
- **Diagramm oder Mockup statt Aufzählung.** Text höchstens ein bis zwei Sätze je Block.
- **Farben nur über die Variablen der Rahmenvorlage:** `var(--success)` erledigt/gut,
  `var(--warning)` Hinweis/in Arbeit, `var(--error)` kritisch/Blocker, `var(--accent)`
  aktuell/empfohlen; Flächen `var(--bg-secondary)`, Linien `var(--border)`.
- **Die empfohlene Option** trägt sichtbar „Empfohlen" und **dieselbe Bezeichnung** wie die Option in
  `AskUserQuestion` — geantwortet wird im Terminal, der Browser zeigt nur.
- **Echte Inhalte** statt Platzhaltern, wo sie die Entscheidung verändern: echte Feldnamen, echte
  Werte, echte Texte aus dem Projekt.
- **UI/UX-Fragen** zeigen je Option die Zustände der Ansicht (Baustein „Zustandsraster") und — wenn
  das Projekt Mobil und/oder Dark Mode unterstützt — Baustein „Responsive/Dark".
- **Keine UI/UX-Seite** (Datenmodell, Bibliothekswahl, Benennung): kein Screen; Frage nur im Terminal.

### Baustein: Roadmap

Sitzungsstart und `/dev status`. Milestones mit Balken, aktuelle Phase hervorgehoben, Blocker oben.
Status-Icons: ✓ erledigt, ⚡ Gate, ~ in Arbeit, ○ offen, — übersprungen.

```html
<h2>Milestone 2: Export — 3 von 5 Phasen erledigt</h2>
<p style="color:var(--error)">⛔ Blocker: Praxisdaten-Feld fehlt in den Einstellungen — Phase 7 wartet darauf</p>
<div class="section">
  <div style="display:flex;justify-content:space-between"><strong>M1 Grundlagen</strong><span style="color:var(--success)">✓ 4/4</span></div>
  <div style="height:8px;background:var(--bg-tertiary);border-radius:4px"><div style="width:100%;height:8px;background:var(--success);border-radius:4px"></div></div>
</div>
<div class="section" style="border:2px solid var(--accent);border-radius:8px;padding:12px">
  <div style="display:flex;justify-content:space-between"><strong>M2 Export</strong><span style="color:var(--accent)">3/5</span></div>
  <div style="height:8px;background:var(--bg-tertiary);border-radius:4px"><div style="width:60%;height:8px;background:var(--accent);border-radius:4px"></div></div>
  <ul style="list-style:none;padding:0;margin-top:8px">
    <li>✓ Phase 4 — Datenmodell</li>
    <li>✓ Phase 5 — PDF-Vorlage</li>
    <li>✓ Phase 6 — Druckansicht</li>
    <li style="color:var(--accent);font-weight:600">~ Phase 7 — Kopfzeile mit Praxisdaten</li>
    <li style="color:var(--text-tertiary)">○ Phase 8 — Stapel-Export</li>
  </ul>
</div>
<div class="section">
  <div style="display:flex;justify-content:space-between"><strong>M3 Tablet</strong><span style="color:var(--text-tertiary)">0/2</span></div>
  <div style="height:8px;background:var(--bg-tertiary);border-radius:4px"></div>
</div>
```

### Baustein: Gate-Dashboard

Gate-Summary ab 3 Befunden und `/dev review`. Befunde je Prüfer, kritisch/Hinweis, behoben/offen.

```html
<h2>Gate Phase 7: 2 kritisch behoben, 3 Hinweise offen</h2>
<table style="width:100%;border-collapse:collapse">
  <tr style="text-align:left;border-bottom:1px solid var(--border)"><th>Prüfer</th><th>kritisch</th><th>Hinweise</th><th>Stand</th></tr>
  <tr><td>Spec-Prüfer</td><td style="color:var(--error)">1</td><td>0</td><td style="color:var(--success)">behoben</td></tr>
  <tr><td>bug-prospector-neutral</td><td style="color:var(--error)">1</td><td>2</td><td style="color:var(--success)">behoben</td></tr>
  <tr><td>security-review</td><td>0</td><td>1</td><td style="color:var(--warning)">Hinweis offen</td></tr>
  <tr><td>performance-check</td><td>0</td><td>0</td><td style="color:var(--success)">—</td></tr>
</table>
<p class="subtitle" style="margin-top:12px">Tests: Spec-Prüfer 1 Lücke, Test rot→grün belegt · Build ✓ · E2E ✓</p>
```

### Baustein: UI-Entscheidung

Jede Frage mit UI/UX-Seite. Optionen als Karten mit Mockup, Empfehlung markiert, Namen wie in
`AskUserQuestion`.

```html
<h2>Wo sitzt der PDF-Export?</h2>
<p class="subtitle">Antwort im Terminal — die Optionen heißen dort genauso.</p>
<div class="cards">
  <div class="card" style="border:2px solid var(--accent)">
    <div class="card-image"><div class="mockup"><div class="mockup-header">Ergebnis-Kopf</div><div class="mockup-body">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:16px"><strong>Weichlinse OD/OS</strong><span class="mock-button">PDF</span></div>
      <div class="mock-content" style="height:60px"></div></div></div></div>
    <div class="card-body"><h3>Button im Ergebnis-Kopf <span style="color:var(--accent)">· Empfohlen</span></h3><p>Sichtbar, wo das Ergebnis steht.</p></div>
  </div>
  <div class="card">
    <div class="card-image"><div class="mockup"><div class="mockup-header">Menü</div><div class="mockup-body">
      <div style="font-size:13px;color:var(--text-secondary);border-bottom:1px solid var(--border);padding:4px 0">Datei ▸ Exportieren ▸ PDF</div><div class="mock-content" style="height:60px"></div></div></div></div>
    <div class="card-body"><h3>Eintrag im Menü</h3><p>Aufgeräumt, aber versteckt.</p></div>
  </div>
</div>
```

### Baustein: Zustandsraster

Zu jeder gezeigten UI-Option: die Ansicht leer, lädt, Fehler, Erfolg.

```html
<h2>Export-Button: vier Zustände</h2>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
  <div class="mockup"><div class="mockup-header">Leer</div><div class="mockup-body"><p style="color:var(--text-tertiary)">Noch keine Berechnung — Export ausgegraut.</p><span class="mock-button" style="opacity:.4">PDF</span></div></div>
  <div class="mockup"><div class="mockup-header">Lädt</div><div class="mockup-body"><p>PDF wird erzeugt …</p><div style="height:6px;background:var(--bg-tertiary)"><div style="width:40%;height:6px;background:var(--accent)"></div></div></div></div>
  <div class="mockup"><div class="mockup-header">Fehler</div><div class="mockup-body"><p style="color:var(--error)">Export fehlgeschlagen: Speicherort nicht beschreibbar.</p><span class="mock-button">Erneut</span></div></div>
  <div class="mockup"><div class="mockup-header">Erfolg</div><div class="mockup-body"><p style="color:var(--success)">Gespeichert: Weichlinse-2026-09-25.pdf</p><span class="mock-button">Öffnen</span></div></div>
</div>
```

### Baustein: Responsive/Dark

Nur wenn das Projekt Mobil und/oder Dark Mode unterstützt. Dunkel wird im Mockup mit eigenen
Farben dargestellt — unabhängig vom System-Theme der Seite.

```html
<h2>Ergebnis-Kopf auf Desktop und Mobil, hell und dunkel</h2>
<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;align-items:start">
  <div class="mockup" style="background:#ffffff;color:#1a1a1a"><div class="mockup-header" style="background:#f0f0f0;color:#1a1a1a">Desktop · hell</div><div class="mockup-body"><div style="display:flex;justify-content:space-between"><strong>Weichlinse OD/OS</strong><span style="border:1px solid #1a1a1a;padding:2px 10px;border-radius:4px">PDF</span></div></div></div>
  <div class="mockup" style="background:#ffffff;color:#1a1a1a;max-width:220px"><div class="mockup-header" style="background:#f0f0f0;color:#1a1a1a">Mobil · hell</div><div class="mockup-body"><strong>Weichlinse OD/OS</strong><div style="margin-top:8px;border:1px solid #1a1a1a;padding:6px;text-align:center;border-radius:4px">PDF exportieren</div></div></div>
  <div class="mockup" style="background:#1b1d22;color:#e8e8e8"><div class="mockup-header" style="background:#2a2d34;color:#e8e8e8">Desktop · dunkel</div><div class="mockup-body"><div style="display:flex;justify-content:space-between"><strong>Weichlinse OD/OS</strong><span style="border:1px solid #e8e8e8;padding:2px 10px;border-radius:4px">PDF</span></div></div></div>
  <div class="mockup" style="background:#1b1d22;color:#e8e8e8;max-width:220px"><div class="mockup-header" style="background:#2a2d34;color:#e8e8e8">Mobil · dunkel</div><div class="mockup-body"><strong>Weichlinse OD/OS</strong><div style="margin-top:8px;border:1px solid #e8e8e8;padding:6px;text-align:center;border-radius:4px">PDF exportieren</div></div></div>
</div>
```

### Baustein: Mermaid-Diagramm

Grundbaustein für alle Diagramme. Das `<script>` bindet Mermaid **einmal pro Screen** ein — jedes
Fragment ist eine eigene Seite, deshalb steht es auch in „Architektur-Vergleich" und „Vorher/Nachher".
Es lädt Mermaid 11 per CDN und folgt dem System-Theme;
ohne Netz bleibt der Quelltext im `<pre>` lesbar.

```html
<h2>Datenfluss PDF-Export</h2>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" });
  await mermaid.run();
</script>
<pre class="mermaid">
flowchart LR
  E[Ergebnisansicht] -->|Export klicken| V[PDF-Vorlage]
  P[(Praxisdaten)] --> V
  V --> R[Renderer]
  R --> D[Datei speichern]
</pre>
```

### Baustein: Architektur-Vergleich

Architektur-Phasen, Schritt „Lösungsansätze": je Ansatz ein Diagramm und Vor-/Nachteile.

```html
<h2>Zwei Wege zum PDF</h2>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" });
  await mermaid.run();
</script>
<div class="split">
  <div class="mockup"><div class="mockup-header">A · Rendern im Frontend <span style="color:var(--accent)">· Empfohlen</span></div><div class="mockup-body">
    <pre class="mermaid">
flowchart TB
  UI[Svelte-Ansicht] --> H[HTML-Druckvorlage] --> W[Webview-Druck]
    </pre>
    <div class="pros-cons"><div class="pros"><h4>Dafür</h4><ul><li>Offline, keine neue Abhängigkeit</li></ul></div><div class="cons"><h4>Dagegen</h4><ul><li>Seitenumbruch je Webview verschieden</li></ul></div></div>
  </div></div>
  <div class="mockup"><div class="mockup-header">B · Rendern im Rust-Kern</div><div class="mockup-body">
    <pre class="mermaid">
flowchart TB
  UI[Svelte-Ansicht] -->|invoke| K[Rust-Kern] --> L[PDF-Bibliothek]
    </pre>
    <div class="pros-cons"><div class="pros"><h4>Dafür</h4><ul><li>Identisches Ergebnis auf allen Systemen</li></ul></div><div class="cons"><h4>Dagegen</h4><ul><li>Neue Abhängigkeit, Layout doppelt</li></ul></div></div>
  </div></div>
</div>
```

### Baustein: Vorher/Nachher

Architektur-Phasen, Schritt „Entwurf".

```html
<h2>Was sich an den Komponenten ändert</h2>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" });
  await mermaid.run();
</script>
<div class="split">
  <div class="mockup"><div class="mockup-header">Vorher</div><div class="mockup-body"><pre class="mermaid">
flowchart LR
  E[Ergebnisansicht] --> S[Speichern als Text]
  </pre></div></div>
  <div class="mockup"><div class="mockup-header" style="color:var(--accent)">Nachher</div><div class="mockup-body"><pre class="mermaid">
flowchart LR
  E[Ergebnisansicht] --> V[PDF-Vorlage] --> D[Datei]
  P[(Praxisdaten)] --> V
  </pre></div></div>
</div>
```

### Baustein: Warten

Wenn der nächste Schritt nur im Terminal stattfindet — verhindert, dass ein veralteter Screen stehen bleibt.

```html
<div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
  <p class="subtitle">Weiter im Terminal …</p>
</div>
```
