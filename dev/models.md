# Subagent model choice

**Name a model in every dispatch**; an omitted one inherits the session model. Tiers: on a Claude host cheap = haiku, standard = sonnet, capable = opus:

| Role | Tier |
|---|---|
| Implementer | **cheap** when the plan carries the code (transcription), **standard** when the task needs judgement |
| Task review, Diff review, Spec checker, Fix review, Similar-bugs scan, Performance review, Tech-Stack Review, Accessibility review, UX review, Polish review; `/dev ui`: Design detector, Motion review, density critique | **standard** |
| Security review (phase or full scope) | **capable** |
| Fix agent (gate Steps B and D) | **standard**; **capable** from round 3 |
| Second opinion (gate, `codex-review.sh`) | Codex's default |
| Taste subagent (4a landing digest, Taste pre-flight, `/dev ui`), impeccable subagent (pre-release audit/polish) | **standard** |
| Configured skills (pre/post-phase, milestone start, pre-release) | **standard** unless the skill says otherwise |
| Milestone End and pre-release full scans (Bug hunt, Performance review, Security review, Dead-code scan) | **capable** |
