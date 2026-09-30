# Companion screens — style rules and building blocks for `/dev`

The procedure (server, alive check, URL) is in `companion.md`. This file covers
what a screen looks like. Every building block is a **content fragment** (no `<html>`/`<head>`; the server
wraps it in the frame template). Write it into `screen_dir` with the `Write` tool, never via
`cat`/heredoc. The companion shows the newest file — for a new screen, write a new file.

**The example content comes from one project** (a practice-management software, PDF export): it only shows the form.
Every real screen contains the actual names, values and texts of the current project.

## Style rules

- **Only the user interface** (rule and table in `companion.md`): mockups, wireframes, real
  screenshots. No roadmaps, plans, specs, strategy, architecture diagrams, findings or decision lists —
  those go to the terminal.
- **Visual first.** A screen that is mostly text is wrong — write that text in the chat instead.
  Text on a screen: headings, labels, captions of at most one or two sentences per block.
- **One statement per screen**; the heading states it.
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

### Building block: Before/After

After a visual fix or UI change: the same view before and after, side by side — two mockups or two
real screenshots (served from `screen_dir` under `/files/<name>`), never two box diagrams.

```html
<h2>Export button now sits next to the result, not in the menu</h2>
<div class="split">
  <div class="mockup"><div class="mockup-header">Before</div><div class="mockup-body">
    <div style="display:flex;justify-content:space-between;align-items:center"><strong>Result</strong><span>☰ Menu</span></div>
    <div style="height:80px;background:var(--bg-tertiary);border-radius:6px;margin-top:8px"></div>
  </div></div>
  <div class="mockup"><div class="mockup-header" style="color:var(--accent)">After</div><div class="mockup-body">
    <div style="display:flex;justify-content:space-between;align-items:center"><strong>Result</strong><span style="padding:4px 10px;border-radius:6px;background:var(--accent);color:white">Export PDF</span></div>
    <div style="height:80px;background:var(--bg-tertiary);border-radius:6px;margin-top:8px"></div>
  </div></div>
</div>
```

### Building block: Real screen

Review or acceptance with real data: a screenshot of the running app (taken e.g. with Playwright
into `screen_dir`, served under `/files/<name>`), with numbered markers on what is wrong or worth
checking and a one-line caption per marker. No prose section below the image.

```html
<h2>Result view with real data: two things to check</h2>
<div style="position:relative;display:inline-block;max-width:100%">
  <img src="/files/result-view.png" alt="Result view" style="max-width:100%;border:1px solid var(--border);border-radius:6px">
  <span style="position:absolute;left:62%;top:18%;width:26px;height:26px;border-radius:50%;background:var(--error);color:white;text-align:center;line-height:26px;font-weight:600">1</span>
  <span style="position:absolute;left:12%;top:71%;width:26px;height:26px;border-radius:50%;background:var(--warning);color:white;text-align:center;line-height:26px;font-weight:600">2</span>
</div>
<ol>
  <li style="color:var(--error)">Total shows 0.0399999 instead of 0.04</li>
  <li style="color:var(--warning)">The table does not say why a day has 0 h</li>
</ol>
```
### Building block: Waiting

When the next step happens only in the terminal — prevents a stale screen from staying up.

```html
<div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
  <p class="subtitle">Continue in the terminal …</p>
</div>
```
