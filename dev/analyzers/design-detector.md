# Design detector (web UI phases)

**Question:** Does this change ship web UI with known anti-patterns — generic AI-generated tells
(side-tab borders, purple gradients, bounce easing, dark glows, overused fonts) or plain design
quality problems (line length, cramped padding, tiny text, skipped headings, low contrast)?

Scope: the changed web UI files (`*.tsx`, `*.jsx`, `*.svelte`, `*.vue`, `*.astro`, `*.html`,
`*.css`, plus `*.scss`/`*.less` if present) and the stylesheets they import.

The rules are impeccable's deterministic detector ([pbakaus/impeccable](https://github.com/pbakaus/impeccable),
Apache-2.0), built locally from the checkout under `$DEV_DESIGN_DIR` — no network, no API key.

## Sweep

The sweep is one script run over the scope, not a grep:

```bash
bash <dev-skill>/scripts/design-detect.sh <changed web UI files>
```

- **Exit 0:** the scan completed. Every listed finding is a candidate (rule id, file, line or
  selector, snippet). Advisory findings are candidates too, judged like the rest.
- **Exit 3:** the first line starts with `skipped:` (engine not built, no files, scan failed).
  Stop here and return `Result: skipped: <reason>` — the gate records the checkbox as
  `skipped: <reason>`. A skip is never "no findings" and never counts as a pass.
- A first line `note: engine built from <old>, checkout at <new>` means the engine is behind the
  checkout. Use the findings, and quote the note in `Checked:` so the gate shows it.

Do not run the detector against URLs, do not pass `--no-config` (the project's
`.impeccable/config*.json` ignores and in-file `impeccable-disable` comments are deliberate), and
do not run any other impeccable command.

## Judge each candidate

Open the file at the reported place and decide:

1. **Real and in scope?** The finding points at code this phase changed or now renders. A finding
   in an untouched file the scan pulled in through an import goes under "Outside scope".
2. **Intentional?** The project's `DESIGN.md`, brand or design tokens may require exactly this
   (a brand font, a gradient in the logo). Then dismiss it with that reason and suggest an
   inline `impeccable-disable-line <rule>: <reason>` instead of a silent pass.
3. **Visible?** Static scans see source, not the rendered page. A rule that depends on layout
   (contrast against an image, overflow) is a candidate to verify, not a confirmed finding — say
   what would confirm it (viewport, state).

## Critical when

Text that fails contrast or is unreadably small (`low-contrast`, `gray-on-color`, `tiny-text`) on a
primary path, content hidden or clipped so a task cannot be completed (`content-hidden-at-rest`,
`text-overflow`, `clipped-overflow-container`), or a `script-error`. Everything else — including
all AI-slop tells — is a note.
