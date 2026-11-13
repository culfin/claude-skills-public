# Subagent model choice

**Name a model in every dispatch** — an omitted one inherits the most expensive session model. Reviews: standard; cheap for transcription, capable for security and full scans:

| Role | Tier |
|---|---|
| Implementer | **cheap** when the plan carries the code (transcription), **standard** when the task needs judgement |
| Task review (per task, during implementation) | **standard** |
| Diff review (gate Step A) | **standard** |
| Spec checker | **standard** |
| Security review (phase or full scope) | **capable** |
| Performance review, Tech-Stack Review | **standard** |
| Accessibility review, Design detector, Motion review, UX review, density critique | **standard** |
| Fix agent (gate Steps B and D) | **standard**; **capable** from round 3 |
| Fix review (gate Step B) | **standard** |
| Similar-bugs scan (gate Step C) | **standard** |
| Second opinion (gate, `codex-review.sh`) | Codex's default |
| Taste subagent (4a landing digest, Taste pre-flight, `/dev ui`), impeccable subagent (pre-release audit/polish) | **standard** |
| Configured skills (pre/post-phase, milestone start, pre-release) | **standard** unless the skill says otherwise |
| Milestone End and pre-release full scans (Bug hunt, Performance review, Security review, Dead-code scan) | **capable** |
