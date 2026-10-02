# Notice

## Platform guideline files

`platform-web.md`, `platform-apple.md`, and `platform-android.md` adapt
content from the `ehmo/platform-design-skills` repository
(https://github.com/ehmo/platform-design-skills), published under the MIT
License. Its `LICENSE` file is reproduced here verbatim; the copyright line
names no holder upstream, so the repository above is the source:

```
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
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
checkout is missing, the step reports `skipped: <reason>` rather than passing silently.
