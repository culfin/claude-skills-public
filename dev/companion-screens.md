# Companion screens — style rules and building blocks for `/dev`

The procedure (server, alive check, URL) is in `companion.md`. This file covers
what a screen looks like. Every building block is a **content fragment** (no `<html>`/`<head>`; the server
wraps it in the frame template). Write it into `screen_dir` with the `Write` tool, never via
`cat`/heredoc. The companion shows the newest file — for a new screen, write a new file.

**The example content comes from one project** (a practice-management software, PDF export): it only shows the form.
Every real screen contains the actual names, values and texts of the current project.

## Style rules

- **One statement per screen**; the heading states it.
- **Diagram or mockup instead of a bullet list.** Text at most one or two sentences per block.
- **Colors only via the frame template's variables:** `var(--success)` done/good,
  `var(--warning)` notice/in progress, `var(--error)` critical/blocker, `var(--accent)`
  current/recommended; surfaces `var(--bg-secondary)`, lines `var(--border)`.
- **The recommended option** visibly carries "Recommended" and **the same label** as the option in
  `AskUserQuestion` — the answer is given in the terminal; the browser only displays.
- **Real content** instead of placeholders wherever it changes the decision: real field names, real
  values, real texts from the project.
- **UI/UX questions** show the states of the view for each option (building block "State grid") and — if
  the project supports mobile and/or dark mode — building block "Responsive/Dark".
- **No UI/UX side** (data model, library choice, naming): no screen; ask the question in the terminal only.

### Building block: Roadmap

Session start and `/dev status`. Milestones with progress bars, current phase highlighted, blockers at the top.
Status icons: ✓ done, ⚡ gate, ~ in progress, ○ open, — skipped.

```html
<h2>Milestone 2: Export — 3 of 5 phases done</h2>
<p style="color:var(--error)">⛔ Blocker: practice-details field missing in settings — phase 7 is waiting for it</p>
<div class="section">
  <div style="display:flex;justify-content:space-between"><strong>M1 Foundations</strong><span style="color:var(--success)">✓ 4/4</span></div>
  <div style="height:8px;background:var(--bg-tertiary);border-radius:4px"><div style="width:100%;height:8px;background:var(--success);border-radius:4px"></div></div>
</div>
<div class="section" style="border:2px solid var(--accent);border-radius:8px;padding:12px">
  <div style="display:flex;justify-content:space-between"><strong>M2 Export</strong><span style="color:var(--accent)">3/5</span></div>
  <div style="height:8px;background:var(--bg-tertiary);border-radius:4px"><div style="width:60%;height:8px;background:var(--accent);border-radius:4px"></div></div>
  <ul style="list-style:none;padding:0;margin-top:8px">
    <li>✓ Phase 4 — Data model</li>
    <li>✓ Phase 5 — PDF template</li>
    <li>✓ Phase 6 — Print view</li>
    <li style="color:var(--accent);font-weight:600">~ Phase 7 — Header with practice details</li>
    <li style="color:var(--text-tertiary)">○ Phase 8 — Batch export</li>
  </ul>
</div>
<div class="section">
  <div style="display:flex;justify-content:space-between"><strong>M3 Tablet</strong><span style="color:var(--text-tertiary)">0/2</span></div>
  <div style="height:8px;background:var(--bg-tertiary);border-radius:4px"></div>
</div>
```

### Building block: Gate dashboard

Gate summary with 3 or more findings, and `/dev review`. Findings per checker, critical/notice, fixed/open.

```html
<h2>Gate phase 7: 2 critical fixed, 3 notices open</h2>
<table style="width:100%;border-collapse:collapse">
  <tr style="text-align:left;border-bottom:1px solid var(--border)"><th>Checker</th><th>Critical</th><th>Notices</th><th>Status</th></tr>
  <tr><td>Spec checker</td><td style="color:var(--error)">1</td><td>0</td><td style="color:var(--success)">fixed</td></tr>
  <tr><td>bug-prospector-neutral</td><td style="color:var(--error)">1</td><td>2</td><td style="color:var(--success)">fixed</td></tr>
  <tr><td>security-review</td><td>0</td><td>1</td><td style="color:var(--warning)">notice open</td></tr>
  <tr><td>performance-check</td><td>0</td><td>0</td><td style="color:var(--success)">—</td></tr>
</table>
<p class="subtitle" style="margin-top:12px">Tests: Spec checker 1 gap, test red→green verified · Build ✓ · E2E ✓</p>
```

### Building block: UI decision

Every question with a UI/UX side. Options as cards with a mockup, recommendation marked, names as in
`AskUserQuestion`.

```html
<h2>Where does the PDF export live?</h2>
<p class="subtitle">Answer in the terminal — the options have the same names there.</p>
<div class="cards">
  <div class="card" style="border:2px solid var(--accent)">
    <div class="card-image"><div class="mockup"><div class="mockup-header">Result header</div><div class="mockup-body">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:16px"><strong>Soft lens OD/OS</strong><span class="mock-button">PDF</span></div>
      <div class="mock-content" style="height:60px"></div></div></div></div>
    <div class="card-body"><h3>Button in the result header <span style="color:var(--accent)">· Recommended</span></h3><p>Visible right where the result is.</p></div>
  </div>
  <div class="card">
    <div class="card-image"><div class="mockup"><div class="mockup-header">Menu</div><div class="mockup-body">
      <div style="font-size:13px;color:var(--text-secondary);border-bottom:1px solid var(--border);padding:4px 0">File ▸ Export ▸ PDF</div><div class="mock-content" style="height:60px"></div></div></div></div>
    <div class="card-body"><h3>Menu entry</h3><p>Tidy, but hidden.</p></div>
  </div>
</div>
```

### Building block: State grid

For every UI option shown: the view when empty, loading, error, success.

```html
<h2>Export button: four states</h2>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
  <div class="mockup"><div class="mockup-header">Empty</div><div class="mockup-body"><p style="color:var(--text-tertiary)">No calculation yet — export greyed out.</p><span class="mock-button" style="opacity:.4">PDF</span></div></div>
  <div class="mockup"><div class="mockup-header">Loading</div><div class="mockup-body"><p>Generating PDF …</p><div style="height:6px;background:var(--bg-tertiary)"><div style="width:40%;height:6px;background:var(--accent)"></div></div></div></div>
  <div class="mockup"><div class="mockup-header">Error</div><div class="mockup-body"><p style="color:var(--error)">Export failed: save location not writable.</p><span class="mock-button">Retry</span></div></div>
  <div class="mockup"><div class="mockup-header">Success</div><div class="mockup-body"><p style="color:var(--success)">Saved: soft-lens-2026-09-25.pdf</p><span class="mock-button">Open</span></div></div>
</div>
```

### Building block: Responsive/Dark

Only if the project supports mobile and/or dark mode. Dark is rendered in the mockup with its own
colors — independent of the page's system theme.

```html
<h2>Result header on desktop and mobile, light and dark</h2>
<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;align-items:start">
  <div class="mockup" style="background:#ffffff;color:#1a1a1a"><div class="mockup-header" style="background:#f0f0f0;color:#1a1a1a">Desktop · light</div><div class="mockup-body"><div style="display:flex;justify-content:space-between"><strong>Soft lens OD/OS</strong><span style="border:1px solid #1a1a1a;padding:2px 10px;border-radius:4px">PDF</span></div></div></div>
  <div class="mockup" style="background:#ffffff;color:#1a1a1a;max-width:220px"><div class="mockup-header" style="background:#f0f0f0;color:#1a1a1a">Mobile · light</div><div class="mockup-body"><strong>Soft lens OD/OS</strong><div style="margin-top:8px;border:1px solid #1a1a1a;padding:6px;text-align:center;border-radius:4px">Export PDF</div></div></div>
  <div class="mockup" style="background:#1b1d22;color:#e8e8e8"><div class="mockup-header" style="background:#2a2d34;color:#e8e8e8">Desktop · dark</div><div class="mockup-body"><div style="display:flex;justify-content:space-between"><strong>Soft lens OD/OS</strong><span style="border:1px solid #e8e8e8;padding:2px 10px;border-radius:4px">PDF</span></div></div></div>
  <div class="mockup" style="background:#1b1d22;color:#e8e8e8;max-width:220px"><div class="mockup-header" style="background:#2a2d34;color:#e8e8e8">Mobile · dark</div><div class="mockup-body"><strong>Soft lens OD/OS</strong><div style="margin-top:8px;border:1px solid #e8e8e8;padding:6px;text-align:center;border-radius:4px">Export PDF</div></div></div>
</div>
```

### Building block: Mermaid diagram

Base building block for all diagrams. The `<script>` includes Mermaid **once per screen** — every
fragment is its own page, which is why it also appears in "Architecture comparison" and "Before/After".
It loads Mermaid 11 via CDN and follows the system theme;
without network access, the source in the `<pre>` stays readable.

```html
<h2>PDF export data flow</h2>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" });
  await mermaid.run();
</script>
<pre class="mermaid">
flowchart LR
  E[Result view] -->|click Export| V[PDF template]
  P[(Practice details)] --> V
  V --> R[Renderer]
  R --> D[Save file]
</pre>
```

### Building block: Architecture comparison

Architecture phases, step "Approaches": one diagram plus pros/cons per approach.

```html
<h2>Two ways to the PDF</h2>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" });
  await mermaid.run();
</script>
<div class="split">
  <div class="mockup"><div class="mockup-header">A · Render in the frontend <span style="color:var(--accent)">· Recommended</span></div><div class="mockup-body">
    <pre class="mermaid">
flowchart TB
  UI[Svelte view] --> H[HTML print template] --> W[Webview print]
    </pre>
    <div class="pros-cons"><div class="pros"><h4>Pros</h4><ul><li>Offline, no new dependency</li></ul></div><div class="cons"><h4>Cons</h4><ul><li>Page breaks differ per webview</li></ul></div></div>
  </div></div>
  <div class="mockup"><div class="mockup-header">B · Render in the Rust core</div><div class="mockup-body">
    <pre class="mermaid">
flowchart TB
  UI[Svelte view] -->|invoke| K[Rust core] --> L[PDF library]
    </pre>
    <div class="pros-cons"><div class="pros"><h4>Pros</h4><ul><li>Identical output on every system</li></ul></div><div class="cons"><h4>Cons</h4><ul><li>New dependency, layout maintained twice</li></ul></div></div>
  </div></div>
</div>
```

### Building block: Before/After

Architecture phases, step "Design".

```html
<h2>What changes in the components</h2>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" });
  await mermaid.run();
</script>
<div class="split">
  <div class="mockup"><div class="mockup-header">Before</div><div class="mockup-body"><pre class="mermaid">
flowchart LR
  E[Result view] --> S[Save as text]
  </pre></div></div>
  <div class="mockup"><div class="mockup-header" style="color:var(--accent)">After</div><div class="mockup-body"><pre class="mermaid">
flowchart LR
  E[Result view] --> V[PDF template] --> D[File]
  P[(Practice details)] --> V
  </pre></div></div>
</div>
```

### Building block: Waiting

When the next step happens only in the terminal — prevents a stale screen from staying up.

```html
<div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
  <p class="subtitle">Continue in the terminal …</p>
</div>
```
