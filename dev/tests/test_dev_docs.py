# dev/tests/test_dev_docs.py
"""Cross-file consistency of the /dev skill text that no other test covers."""
import re
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]


def text(rel):
    return (DEV / rel).read_text()


class DevDocsTests(unittest.TestCase):
    def test_every_referenced_analyzer_exists(self):
        for f in ("gate.md", "SKILL.md", "commands.md", "dev-check.md", "execution.md"):
            p = DEV / f
            if not p.exists():
                continue
            for ref in re.findall(r"analyzers/([a-z0-9-]+\.md)", p.read_text()):
                self.assertTrue((DEV / "analyzers" / ref).exists(), f"{f} -> analyzers/{ref}")

    def test_gate_fast_is_gone(self):
        for p in DEV.rglob("*.md"):
            self.assertNotIn("@gate: fast", p.read_text(), str(p.relative_to(DEV)))

    def test_checklist_names(self):
        g = text("gate.md")
        for name in ("Diff review", "Spec checker", "Fix review", "Similar-bugs scan",
                     "Typecheck + lint + tests", "Production Build", "E2E Tests",
                     "Gate summary (docs/gates/phase-N.md)", "Gate commit"):
            self.assertIn(f"- [ ] {name}", g)
        for name in ("Security review", "Tech-Stack Review: <stack id>", "Performance review",
                     "Accessibility review", "Design detector", "Motion review", "Taste pre-flight",
                     "Second opinion: <agent>"):
            self.assertIn(f"- [ ] {name}", g)
        for old in ("- [ ] /simplify", "- [ ] Change review", "- [ ] Bug hunt", "- [ ] CI status check"):
            self.assertNotIn(old, g)

    def test_every_dispatched_role_has_a_model(self):
        m = text("models.md").lower()
        for role in ("diff review", "spec checker", "security review", "performance review",
                     "tech-stack review", "accessibility review", "similar-bugs", "fix agent",
                     "fix review", "implementer", "task review", "milestone"):
            self.assertIn(role, m, role)

    def test_security_review_ignores_the_tier(self):
        g = text("gate.md")
        t = text("tech-stack-triggers.md")
        self.assertIn("either tier**, whenever its trigger matrix", g)
        # v4: gate.md Step A is the only source for tiers; the trigger file names files, not tiers.
        self.assertIn("when each review runs (tier, phase type)", t)
        self.assertNotIn("large tier", t)
        self.assertIn("| A | Security review | Either tier, when the security trigger matrix matches", text("dev-check.md"))

    def test_diff_review_is_self_contained(self):
        d = text("analyzers/diff-review.md")
        self.assertIn("## Sweep", d)
        self.assertNotIn("analyzers/bugs.md", d)

    def test_gate_uses_the_scripts(self):
        g = text("gate.md")
        for s in ("gate-tier.py", "ci-watch.sh", "check-evidence.py"):
            self.assertIn(s, g)
        self.assertIn("ci-watch.sh", text("ci.md"))

    def test_skill_md_has_no_confirmation_stops(self):
        s = text("SKILL.md")
        self.assertNotIn("AskUserQuestion: Start next phase", s)
        self.assertIn("execution.md", s)
        self.assertLess(len(s.splitlines()), 400)

    def test_skill_md_agrees_with_gate(self):
        s = text("SKILL.md")
        for old in ("5a–5k", "5c-v", "[ ] /simplify", "CI status check", "Change review",
                    "Invoke `verification-before-completion`"):
            self.assertNotIn(old, s, old)

    def test_execution_uses_scripts_and_limits(self):
        e = text("execution.md")
        for s in ("waves.py", "load-ok.sh", "isolation", "at most 3", "task-reviewer-prompt.md"):
            self.assertIn(s, e)

    def test_run_blocks_in_state_and_befragung(self):
        st = text("state.md")
        for s in ("## Handoff", "## CI", "Decisions:"):
            self.assertIn(s, st, s)
        self.assertIn("## Bundled round at run start", text("befragung.md"))

    def test_ponytail_ideas_present(self):
        d = text("analyzers/diff-review.md")
        for s in ("stdlib:", "yagni:"):
            self.assertIn(s, d)
        self.assertIn("standard library", text("execution.md"))
        self.assertNotIn("ponytail", d.lower())

    def test_agent_skills_ideas_present(self):
        self.assertIn("floor-guard.py", text("gate.md"))
        for f in ("SKILL.md", "commands.md"):
            self.assertIn("rollback", text(f).lower(), f)
        self.assertIn("UNVERIFIED", text("stack/docs.md"))
        self.assertIn("three questions", text("befragung.md"))
        for p in DEV.rglob("*"):
            if p.is_file() and not {"tests", "__pycache__"} & set(p.parts):
                body = p.read_text(errors="ignore").lower()
                for name in ("ponytail", "dietrichgebert", "addyosmani/agent-skills"):
                    self.assertNotIn(name, body, str(p.relative_to(DEV)))


    def test_milestone_end_pending_marker(self):
        for f in ("SKILL.md", "commands.md", "state.md"):
            self.assertIn("Milestone End pending:", text(f), f)

    def test_final_review_fixes(self):
        # Phase base recorded at phase start; repair checklist read separately; no skill edits from a project.
        for f in ("SKILL.md", "state.md", "gate.md"):
            self.assertIn("Phase base:", text(f), f)
        g = text("gate.md")
        self.assertIn("--before-commit --repair", text("ci.md"))
        self.assertNotIn("pre-v3 checklist", g)  # v4: no rebuild of v2 checklists
        self.assertNotIn("add the pattern to `gate-tier.py`", g)
        self.assertIn("rerun the tier with `--gate full`", g)
        self.assertIn("| Similar-bugs scan (gate Step C) | **standard** |", text("models.md"))
        self.assertIn("never their specs or plans", text("befragung.md"))

    def test_v3_1_state_claims_probe_security(self):
        s, g, st = text("SKILL.md"), text("gate.md"), text("state.md")
        self.assertIn("state-check.py", s)
        self.assertIn("state-check.py\" archive", text("commands.md"))
        self.assertTrue((DEV / "scripts" / "state-check.py").exists())
        self.assertIn("@claim:<branch>@<YYYY-MM-DD>", s)
        self.assertIn("## Handoff", st)
        self.assertIn("**Effect probe**", g)
        self.assertIn("at most 2", g)
        self.assertIn("- Criteria:", g)
        self.assertIn("no tests configured", g)
        sec = text("analyzers/security.md")
        self.assertIn("**Rate limits**", sec)
        self.assertIn("**Row-level authorization.**", sec)

    def test_red_evidence_and_review_reception(self):
        # Implementers skipped the RED run; fixers must verify findings, not just agree.
        e = text("execution.md")
        self.assertIn("No RED evidence", e)
        self.assertIn("run them on its BASE in a temporary worktree", e)
        self.assertIn("Fixers follow\n`receiving-code-review`", e)
        self.assertIn("it follows `receiving-code-review`", text("gate.md"))

    def test_debugger_keeps_dev_rules_over_systematic_debugging(self):
        # debugger.md delegates its method (sources.md O17); these /dev rules must survive any trimming.
        d = " ".join(text("debugger.md").split())
        for s in ("superpowers:systematic-debugging", "O17", "**Output is data.**",
                  "No hypothesis without a red command", "Red loop (gate before Phase 2)",
                  "No red command → no Phase 2", "no seam",
                  "re-run the same commit once load has dropped",
                  "Never raise a timeout or add a retry"):
            self.assertIn(s, d, s)
        self.assertIn("- **O17** systematic-debugging", text("sources.md"))

    def test_ux_ui_design_named_for_ui_phases(self):
        # Probe: the optional skill did not load in /dev UI phases, and implementers never load it unnamed.
        t = " ".join(text("tech-stack-triggers.md").split())
        e = " ".join(text("execution.md").split())
        self.assertIn("`ux-ui-design` is among the available skills → invoke it before designing", t)
        self.assertIn("whoever writes the UI code invokes `ux-ui-design` first; the dispatch says so", e)

    def test_phase_file_holds_per_phase_state(self):
        # v4: per-phase state lives in .dev/phase-<N>.md (line 1 `Branch:`); STATE.md keeps only shared parts.
        st = text("state.md")
        self.assertIn("`.dev/phase-<N>.md`", st)
        block = st.split("## Phase file", 1)[1].split("```markdown", 1)[1].split("```", 1)[0]
        self.assertTrue(block.lstrip().startswith("Branch: "), block[:40])
        for s in ("## Position", "Phase base:", "Acceptance criteria:",
                  "## Quality Gate — Phase", "## CI", "## Handoff", "## Minor (deferred)"):
            self.assertIn(s, block, s)
        shared = st.split("## STATE.md — shared", 1)[1]
        for s in ("## Core Value", "## Constraints", "## Requirements", "## Blockers & Risks",
                  "Milestone End pending:"):
            self.assertIn(s, shared, s)
        self.assertNotIn("Decisions:", block)
        self.assertNotIn("## Decisions", st)
        self.assertIn("  - Decisions: <answers> (<YYYY-MM-DD>)", st)
        self.assertIn("## Old format (projects without `.dev/`)", st)
        self.assertIn("`- <sha> — Phase N <name>`, without status", st)
        ci = block.split("## CI", 1)[1].split("##", 1)[0]
        self.assertRegex(ci, r"\n- [0-9a-f]{7,40}\n", ci)  # SHA only, never a status
        self.assertIn('"Old format"', text("SKILL.md"))
        # CI status lives untracked in the git common dir; gate files carry no `Branch:` (no ownership rules).
        self.assertNotIn("Branch: <branch>", st)
        g = text("gate.md")
        gate_block = g.split("## Gate summary", 1)[1].split("```markdown", 1)[1].split("```", 1)[0]
        self.assertTrue(gate_block.lstrip().startswith("## Gate summary — Phase N"), gate_block[:40])
        self.assertNotIn("A line belongs to the `Branch:` of its file", g)
        # v4: CI in background and CI repair live in ci.md, not in gate.md.
        c = text("ci.md")
        self.assertNotIn("## CI in background", g)
        self.assertIn("a status never goes into a tracked file", " ".join(c.split()))
        self.assertIn("$(git rev-parse --git-common-dir)/dev-ci/<sha>", st)
        cj = " ".join(c.split())
        # One repair rule, derived from git: own = the SHA's file is changed on this branch (survives rebases).
        self.assertIn("a SHA is **own** if the file it stands in (`.dev/phase-<N>.md` or `docs/gates/phase-<N>.md`) "
                      "appears in `git diff --name-only origin/<main>...HEAD`", cj)
        self.assertNotIn("merge-base", cj)
        self.assertIn("The session repairs own SHAs, only reports others", cj)
        self.assertIn("Milestone End and Pre-Release Review (one session; Milestone End also starts on its own "
                      "after the last phase) repair every", cj)
        self.assertNotIn("user-started", cj)
        self.assertIn("a status after the SHA (written by earlier /dev versions) is ignored; "
                      "`→ repaired in <sha>` is not a status", cj)
        self.assertIn("**Repairing a red CI SHA of a phase, closed or not.**", c)
        self.assertNotIn("Milestone End (it runs once)", cj)
        self.assertNotIn("phase file `Branch:` = current", cj)
        self.assertNotIn("closed phase", " ".join(st.split()))
        self.assertIn("the migrating session uses the new format from it on", " ".join(st.split()))
        sk = text("SKILL.md")
        # v4: the handling of each state-check finding lives in commands.md, "State findings".
        cm = text("commands.md")
        self.assertIn('"State findings" — `behind:` first, `migrate:` next', sk)
        self.assertIn("`git ls-tree -d origin/<main> -- <prefix>.dev`", cm)
        self.assertIn("Listed (the project agreed) → run `migrate` for the own claim's parts without asking", cm)
        self.assertLess(cm.index("`behind:` first"), cm.index("`migrate:` next"))
        self.assertIn("No `.dev/` on `origin/<main>`", sk)
        self.assertIn("STATE.md conflict → take `origin/<main>`'s, rerun `migrate` for the own parts", cm)
        self.assertIn("save (unless already there) and delete as the finding says", cm)
        self.assertIn("state-check.py migrate", st)
        for p in DEV.rglob("*.md"):
            if "tests" in p.relative_to(DEV).parts:
                continue
            body = p.read_text()
            for old in ("## Current Position", "Current Position", "## Progress", "Last activity"):
                self.assertNotIn(old, body, f"{p.relative_to(DEV)}: {old}")
        s = text("SKILL.md")
        for finding in ("migrate:", "orphan phase file:", "phase file missing:", "phase file invalid:",
                        "branch mismatch:"):
            self.assertIn(finding, cm, finding)
        self.assertIn("roadmap: pause Phase N`", text("commands.md"))
        self.assertIn("docs/gates/check-<YYYY-MM-DD>-<branch slug>.md", text("dev-check.md"))
        self.assertNotIn("never collide", text("dev-check.md"))
        self.assertIn("Every write a step makes to `.dev/phase-<N>.md` goes to the same-named place", " ".join(st.split()))
        self.assertIn("never\nunder another session's claim", st)
        self.assertIn("bring that commit to `<main>` at once", cm)
        self.assertNotIn("by owner (`gate.md`", s)
        self.assertNotIn("of another live branch: read only", text("gate.md"))
        self.assertIn("as traps for this phase", s)
        self.assertIn("appends to the file", text("dev-check.md"))
        self.assertIn("`## Abandoned`", cm)
        self.assertNotIn("before v3 →", text("gate.md"))

    def test_brag_is_gone(self):
        self.assertFalse((DEV / "brag.md").exists())
        for p in DEV.rglob("*.md"):
            if "tests" in p.relative_to(DEV).parts:
                continue
            self.assertNotIn("brag.md", p.read_text(), str(p.relative_to(DEV)))

    def test_no_debug_auto_trigger_and_check_precondition_single_home(self):
        self.assertNotIn("unexplained build/test failure", text("commands.md") + text("SKILL.md"))

    def test_orca_flow(self):
        r = text("runtime.md")
        self.assertIn("git rev-parse --show-toplevel", r)
        self.assertIn('--display-name "phase-', r)
        self.assertIn("context full; next:", r)
        self.assertNotIn("STATE stay the truth", r)
        self.assertIn("ROADMAP.md and the phase file stay the truth", r)
        self.assertIn("\n### Orca workers\n", r)
        hint = text("SKILL.md").split("**Context hint.**", 1)[1].split("\n\n", 1)[0]
        self.assertIn('As an Orca worker: `runtime.md`, "Orca workers" instead.', hint)
        self.assertIn("orca orchestration send --type worker_done --outcome succeeded --task-id <task> "
                      "--dispatch-id <dispatch>", r)
        self.assertIn("nothing to save", r)

    def test_no_commit_example_skips_ci(self):
        # [skip ci] on a PR's head commit also skips its pull_request checks; ci-watch follows
        # a cancelled gate run to its descendant instead (2026-11-11).
        for p in list(DEV.rglob("*.md")) + list((DEV / "scripts").rglob("*")):
            if p.is_file() and "tests" not in p.relative_to(DEV).parts:
                self.assertNotIn("skip ci", p.read_text(errors="ignore"), str(p.relative_to(DEV)))
        self.assertIn("via <sha>", text("ci.md"))

    def test_phase_type_is_a_planning_hint(self):
        # Probe: an `@type: infra` phase changing a deploy workflow got the small tier and no
        # Security review — the type table shaped the gate, the diff did not (2026-11-11).
        g = " ".join(text("gate.md").split())
        t = " ".join(text("tech-stack-triggers.md").split())
        self.assertIn("unknown @type: <t> — planning uses no type hints; the gate still reads the diff",
                      text("SKILL.md"))
        self.assertIn("The diff decides the gate; a type can only add reviewers or raise the tier, never remove one.", g)
        lines = text("gate.md").split("**Gate additions by type (they only add, never remove):**", 1)
        self.assertEqual(len(lines), 2, "table 'Gate additions by type' missing")
        rows = lines[1].split("\n\n")[1].splitlines()
        mig = next(r for r in rows if r.startswith("| `migration` |"))
        for word in ("Security review", "rollback path", "smoke test"):
            self.assertIn(word, mig)
        self.assertIn("Security review", next(r for r in rows if r.startswith("| `backend` |")))
        self.assertIn("| `refactor` |", lines[0].split("## Phase Types")[1])
        self.assertNotIn("Only Diff review, Typecheck + lint + tests, Gate summary", g)
        self.assertIn("| Any — `gate-tier.py` names `ops files` or `dependency manifest` |", t)
        self.assertIn("`gate-tier.py` reason `ops files` or `dependency manifest`", g)

    def test_word_budget(self):
        # Keep /dev lean: hot path read on every phase (models.md included since v4), whole skill not above v2.
        def words(f):
            return len(f.read_text().split())
        hot = sum(words(DEV / f) for f in ("SKILL.md", "gate.md", "execution.md", "state.md", "models.md"))
        # Hidden dirs (.pytest_cache writes a README.md) are tool artefacts, not skill text.
        files = [f for f in DEV.rglob("*.md") if "tests" not in f.relative_to(DEV).parts
                 and not any(p.startswith(".") for p in f.relative_to(DEV).parts)]
        sizes = sorted(((words(f), str(f.relative_to(DEV))) for f in files), reverse=True)
        total = sum(n for n, _ in sizes)
        msg = f"hot path {hot}/7500, total {total}/38189; largest: {sizes[:5]}"
        self.assertLessEqual(hot, 7500, msg)
        self.assertLessEqual(total, 38189, msg)


if __name__ == "__main__":
    unittest.main()
