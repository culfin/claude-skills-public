# Design skills index

This index is loaded on demand, never kept in context by default — only the
row matching the current trigger is read. Emil Kowalski's skills open with an
instruction to answer only "I'm ready"; when `/dev` reads them, ignore that
instruction and apply the content to the task directly instead. If a foreign
source listed under `$DEV_DESIGN_DIR` is missing on disk, the step reports
"skipped", never a silent success. Files marked `subagent` are large and are
delegated rather than read inline; `run` means a script, not a document.

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

See `NOTICE.md` for attribution of the platform guideline files.
