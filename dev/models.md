# Subagent model choice

Read before dispatching any subagent (implementation, gate, Milestone End, Pre-Release Review, `/dev ui`).

**Name a model in every dispatch** — an omitted one inherits the most expensive session model. Reviews are judgement work (standard tier); cheap is for transcription, capable for security and full scans:

| Role | Tier |
|---|---|
| Implementer | **cheap** when the plan carries the code (transcription), **standard** when the task needs judgement |
| Task review (per task, during implementation) | **standard** |
| Diff review (gate Step A — carries the former bug hunt) | **standard** |
| Spec checker | **standard** |
| Security review (phase or full scope) | **capable** |
| Performance review, Tech-Stack Review | **standard** |
| Accessibility review, Design detector, Motion review, density critique | **standard** |
| Fix agent (gate Steps B and D) | **standard**; **capable** from round 3 |
| Fix review (gate Step B) | **standard** |
| Similar-bugs scan (gate Step C) | **standard** |
| Second opinion (gate Step A, Orca worker of another agent) | that agent's default; `--model` only if the user named one |
| Taste subagent (4a landing digest, Taste pre-flight, `/dev ui`), impeccable subagent (pre-release audit/polish) | **standard** |
| Configured skills (pre/post-phase, milestone start, pre-release) | **standard** unless the skill says otherwise |
| Milestone End and pre-release full scans (Bug hunt, Performance review, Security review, Dead-code scan) | **capable** |

Only the model is decided here — which checks run, and when, is in `gate.md` and `tech-stack-triggers.md`.
