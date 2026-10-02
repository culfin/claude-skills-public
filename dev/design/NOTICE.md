# Notice

## Platform guideline files

`platform-web.md`, `platform-apple.md`, and `platform-android.md` adapt
content from the `ehmo/platform-design-skills` repository (MIT License):

```
MIT License

Copyright (c) 2026
```

The wording in this repo's files is rephrased in our own words; see
`INDEX.md` for how each file is loaded.

## Vendored-at-runtime sources

The following are read at runtime from `$DEV_DESIGN_DIR` and are **not**
vendored into this repository:

- Emil Kowalski's skills (`prototype`, `animate`, `animate-expo`,
  `mobile-native`, `apple-design`, `review-animations`) — MIT License.
- `taste-skill` — MIT License.
- `impeccable` — Apache-2.0 License.

If `$DEV_DESIGN_DIR` is unset, the default is `~/.claude/dev-design/`. If a
checkout is missing, the step reports "skipped" rather than failing silently.
