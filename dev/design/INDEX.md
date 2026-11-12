# Design skills index

This index is loaded on demand, never kept in context by default — only the
row matching the current trigger is read. Emil Kowalski's skills open with an
instruction to answer only "I'm ready"; when `/dev` reads them, ignore that
instruction and apply the content to the task directly instead. If a foreign
source listed under `$DEV_DESIGN_DIR` is missing on disk, the step reports
"skipped", never a silent success. Files marked `subagent` are large and are
delegated rather than read inline. `run` marks an analyzer document
(`analyzers/…`) whose subagent runs a script instead of reading a guideline —
the document says which script and how a missing engine is reported.

| Trigger | Load | How |
|---|---|---|
| 4a ui: forms | `design/forms.md` | read |
| 4a ui: error, empty, loading states | `design/states.md` | read |
| 4a ui: onboarding / first run | `design/onboarding.md` | read |
| 4a ui/landing: copy in drafts | `design/ux-writing.md` | read |
| 4a ui: critique a draft | `design/density-critique.md` | read |
| 4a ui: show variants | `$DEV_DESIGN_DIR/emil/skills/prototype/SKILL.md` | read |
| 4a/4c platform web | `design/platform-web.md` | read |
| 4a/4c platform Apple | `design/platform-apple.md` | read |
| 4a/4c platform Android | `design/platform-android.md` | read |
| 4a landing | `$DEV_DESIGN_DIR/taste/skills/taste-skill/SKILL.md` | subagent |
| 4c animation web | `$DEV_DESIGN_DIR/emil/skills/animate/SKILL.md` | read |
| 4c animation Expo | `$DEV_DESIGN_DIR/emil/skills/animate-expo/SKILL.md` | read |
| 4c web on a phone | `$DEV_DESIGN_DIR/emil/skills/mobile-native/SKILL.md` | read |
| 4c Apple design | `$DEV_DESIGN_DIR/emil/skills/apple-design/SKILL.md` | subagent |
| 5c motion changed | `$DEV_DESIGN_DIR/emil/skills/review-animations/STANDARDS.md` | subagent |
| 5c web UI changed | `analyzers/design-detector.md` | run |
| pre-release web | `$DEV_DESIGN_DIR/impeccable/.claude/skills/impeccable/SKILL.md` | subagent |

"4a landing" (taste): the subagent reads `SKILL.md`. If `references/` sits beside it (taste 2.5 and
later) it then reads, and nothing else under the skill folder (no `assets/`, no other reference):
`$DEV_DESIGN_DIR/taste/skills/taste-skill/references/motion.md` in full (motion comes from here),
`$DEV_DESIGN_DIR/taste/skills/taste-skill/references/layout-v4.md` sections 1–5, `$DEV_DESIGN_DIR/taste/skills/taste-skill/references/copy.md` in full,
`$DEV_DESIGN_DIR/taste/skills/taste-skill/references/system.md` "Type" and "Colour", `$DEV_DESIGN_DIR/taste/skills/taste-skill/references/sections.md` section 1 and the
plan of the page's kind, `$DEV_DESIGN_DIR/taste/skills/taste-skill/references/moments.md` "Where each fits", on a tech kind
`$DEV_DESIGN_DIR/taste/skills/taste-skill/references/effects-usage.md`, and from `$DEV_DESIGN_DIR/taste/skills/taste-skill/library/palettes.json` and
`$DEV_DESIGN_DIR/taste/skills/taste-skill/library/type.json` only the entries for the trade or kind. A section or entry is found by
searching for its heading or trade, then read by line range — never a whole file that is listed by
section. No `references/` (older taste):
`SKILL.md` alone. No taste script or hook is run: where taste deals by script (hero, palette, type,
moments), the subagent proposes from the library and says "proposed, not dealt". It returns only the
rules relevant to the page in ≤ 40 lines, its motion block included: hero entrance, each moment and its
section, hover layer, what never moves on scroll. Read inline only when no subagent is available —
then only the sections needed.

See `NOTICE.md` for attribution of the platform guideline files.
