# State — old format (project not migrated)

Read when `state.md` points here.

Migrated ⇔ the empty marker `<prefix>.dev/.gitkeep` is on `origin/<main>` (`git cat-file -e
origin/<main>:<prefix>.dev/.gitkeep`, `<prefix>`: ROADMAP.md's directory; without `origin`, the local
`<main>` stands for `origin/<main>` everywhere). Until the user agrees to `state-check.py migrate`
(`next.md`, "State findings"), **all** phases keep the old format; the migrating session uses the
new one from its `migrate` commit on. Every write a step makes to `.dev/phase-<N>.md` goes to the
same-named place in STATE.md, reads too (`### Phase N` under `## Phases`, `## Quality Gate — Phase N`,
`## Handoff — <branch>`, position first); CI lines `- <sha> — Phase N <name>`, without status, under `## CI in background`, read there by
Milestone End step 0 and the repair checklist. Gate summary (`### Gate summary — Phase N`) and minors
(Blockers & Risks) stay in STATE.md; completion removes the phase's Quality Gate, `### Phase N` and
Handoff from it. A takeover replaces the `## Handoff — <branch>` heading instead of `Branch:`.
