# Subagent model choice

Read before dispatching subagents (gate step 5c, Milestone End, Pre-Release Review, `/dev ui`).

`/dev` dispatches many parallel Agent subagents. **Always specify a model explicitly when dispatching** — an omitted model inherits the most expensive session model (lesson from superpowers 6.x SDD). Choose the cheapest tier that can handle the task:

| Role | Tier |
|-------|------|
| Read-only analysis in Step 5c: Bug hunt, Performance review, Tech-Stack Review | **cheap tier** |
| Design analyses in Step 5c and `/dev ui`: Accessibility review, Design detector, Motion review, density critique | **cheap tier** |
| Security review (phase or full scope), Spec checker (5c-v) | **standard/capable tier** |
| Taste subagent (4a landing digest, gate pre-flight, `/dev ui`), impeccable subagent (pre-release audit/polish checklists) | **standard tier** |
| Milestone-end & pre-release full scans (Bug hunt full, Performance review full, Security review full, Dead-code scan full) | **capable tier** |

Only the **dispatch model choice** is affected — which checks run and their triggers remain unchanged.
