# Subagent model choice

Read before dispatching any subagent (implementation, gate, Milestone End, Pre-Release Review, `/dev ui`).

`/dev` dispatches many subagents. **Always specify a model explicitly when dispatching** — an omitted model inherits the most expensive session model (lesson from superpowers 6.x SDD). Choose the cheapest tier that can handle the role:

| Role | Tier |
|---|---|
| Implementer | **cheap** when the plan carries the code (transcription), **standard** when the task needs judgement |
| Task review (per task, during implementation) | **standard** |
| Diff review (gate Step A — carries the former bug hunt) | **standard** |
| Spec checker | **standard** |
| Security review (phase or full scope) | **capable** |
| Performance review, Tech-Stack Review | **cheap** |
| Accessibility review, Design detector, Motion review, density critique | **cheap** |
| Fix agent (gate Step B) | **standard**; **capable** from round 3 |
| Fix review (gate Step B) | **standard** |
| Similar-bugs scan (gate Step C) | **cheap** |
| Taste subagent (4a landing digest, Taste pre-flight, `/dev ui`), impeccable subagent (pre-release audit/polish) | **standard** |
| Milestone End and pre-release full scans (Bug hunt, Performance review, Security review, Dead-code scan) | **capable** |

Only the model is decided here — which checks run, and when, is in `gate.md` and `tech-stack-triggers.md`.
