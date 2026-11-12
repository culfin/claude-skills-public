import os, re, pathlib
DEV = pathlib.Path(__file__).resolve().parents[1]
DESIGN = DEV / "design"
VENDOR = pathlib.Path(os.environ.get("DEV_DESIGN_DIR", os.path.expanduser("~/.claude/dev-design")))

def rows():
    for line in (DESIGN / "INDEX.md").read_text().splitlines():
        if line.startswith("|") and not line.startswith("|---") and "Trigger" not in line:
            cells = [c.strip(" `") for c in line.strip("|").split("|")]
            yield cells

def test_index_paths_exist():
    for trig, load, how in rows():
        assert how in {"read", "subagent", "run"}, trig
        path = load.split("#")[0]
        if path.startswith("$DEV_DESIGN_DIR/"):
            if VENDOR.exists():
                assert (VENDOR / path.removeprefix("$DEV_DESIGN_DIR/")).exists(), load
        else:
            assert (DEV / path).exists(), load

def test_budget():
    assert len((DESIGN / "INDEX.md").read_text().splitlines()) <= 60
    for f in DESIGN.glob("*.md"):
        assert len(f.read_text().splitlines()) <= 120, f.name

def test_no_local_paths():
    for f in DESIGN.glob("*.md"):
        t = f.read_text()
        assert "/Users/" not in t and not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", t), f.name

def test_accessibility_trigger_by_files():
    t = (DEV / "tech-stack-triggers.md").read_text()
    row = [l for l in t.splitlines() if "Accessibility review" in l and l.startswith("|")][0]
    condition = row.split("|")[2]
    assert "@type: ui" not in condition
    assert "UI files" in condition

def test_checklist_has_accessibility():
    assert "- [ ] Accessibility review" in (DEV / "gate.md").read_text()

def test_target_size_rule():
    lines = (DEV / "analyzers/accessibility.md").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(r"\d+\.\s+\*\*Target size", l))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"\d+\.\s+\*\*", lines[i]) or lines[i].startswith("#"):
            end = i
            break
    paragraph = "\n".join(lines[start:end])
    assert "24" in paragraph and "44" in paragraph and "2.5.8" in paragraph

def test_router_has_ui():
    skill = (DEV / "SKILL.md").read_text()
    assert "| `/dev ui [scope]` | `ui-review.md` | UI review and rework |" in skill
    assert "/dev ui" in skill.split("---")[1]  # description front matter
    review = DEV / "ui-review.md"
    assert review.exists()
    assert len(review.read_text().splitlines()) <= 120

def test_skill_md_loads_on_demand():
    skill = (DEV / "SKILL.md").read_text()
    assert len(skill.splitlines()) <= 396
    # v4: one router table "Command or step | File | When"; the File column lists every file.
    section = skill.split("## Router — what to read when", 1)[1].split("\n---", 1)[0]
    listed = set()
    for line in section.splitlines():
        if line.startswith("|") and not line.startswith("|---") and "| File |" not in line:
            listed.update(re.findall(r"`([^`]+\.md)`", line.split("|")[2]))
    assert listed, "no files found in the router table"
    for path in listed:
        assert (DEV / path).exists(), f"listed but missing: {path}"
    for f in DEV.glob("*.md"):
        if f.name != "SKILL.md":
            assert f.name in listed, f"not in the router table: {f.name}"

def test_skipped_check_rule_is_the_same_everywhere():
    """A check whose optional source is missing is ticked as `skipped: <reason>`, listed in the
    summary, never a pass and never left open — gate, contract, triggers, /dev ui and the script agree."""
    gate = (DEV / "gate.md").read_text()
    assert "- [x] Design detector — skipped: engine not built" in gate
    assert "- Skipped checks:" in gate
    assert "- [ ] Taste pre-flight" in gate
    for name in ("gate.md", "analyzers/CONTRACT.md", "tech-stack-triggers.md", "ui-review.md"):
        text = (DEV / name).read_text()
        assert "skipped: <reason>" in text, name
        assert "stays open" not in text.split("skipped: <reason>", 1)[1][:200], name
        assert not re.search(r"skipped: <reason>`?;? it is never ticked", text), name
    assert "Skipped checks" in (DEV / "analyzers/CONTRACT.md").read_text()
    assert "Skipped checks" in (DEV / "tech-stack-triggers.md").read_text()
    assert 'never "no findings"' in (DEV / "ui-review.md").read_text()
    script = (DEV / "scripts/check-evidence.py").read_text()
    for check in ("design detector", "motion review", "taste pre-flight", "tech-stack review"):
        assert f'"{check}"' in script, check
        assert check in gate.lower(), check


def test_ux_ui_design_replaces_overlapping_design_rows():
    text = (DEV / "tech-stack-triggers.md").read_text()
    line = next(l for l in text.splitlines() if "`ux-ui-design` available → the rows" in l)
    for name in ("forms", "states", "onboarding", "ux-writing"):
        assert name in line
    assert "not loaded anywhere" in line and "density-critique" in line
    assert "stay" in line.rsplit("density-critique", 1)[1][:80]
    assert "Without `ux-ui-design` everything loads" in line


def test_ux_ui_design_rule_covers_landing_and_ui_review():
    # v4.4.0: the rule no longer stops at `ui` phases; landing and /dev ui drop the four rows too,
    # and reviews use ux-ui-design's Review mode (gate UX review, ui-review ux subagent).
    text = (DEV / "tech-stack-triggers.md").read_text()
    line = next(l for l in text.splitlines() if "`ux-ui-design` available → the rows" in l)
    assert "(4a, 4c, `landing`, `/dev ui`)" in line and "Review mode" in line
    assert "as before" not in text
    ux = next(l for l in text.splitlines() if "ux-ui-design" in l and "invoke it before designing" in l)
    assert "not loaded" not in ux and "INDEX.md" not in ux
    gate = (DEV / "gate.md").read_text()
    assert "- [ ] UX review" in gate
    assert "| UX review | `ux-ui-design` in Review mode" in gate
    assert "UX review" in (DEV / "models.md").read_text()
    review = (DEV / "ui-review.md").read_text()
    assert "4a ui: forms" in review and "4a ui: error, empty, loading states" in review
    assert "ux subagent" in review and "Review mode" in review


def test_motion_and_font_rules_follow_page_kind():
    # v4.4.0 RED: with both taste and ux-ui-design loaded a landing phase followed ux-ui-design's
    # "one eye-catcher", and the detector reported Inter in app UI as an overused font.
    triggers = " ".join((DEV / "tech-stack-triggers.md").read_text().split())
    assert "**Motion — which source wins.**" in triggers
    assert "taste's motion rules (intensity, entrances, scroll-reveal per section) win over" in triggers
    assert "motion stays sparse per ux-ui-design and Emil; taste's motion never carries over" in triggers
    motion = " ".join((DEV / "analyzers/motion.md").read_text().split())
    assert "entrances and scroll-reveals the page's taste rules call for are not a finding here" in motion
    detector = " ".join((DEV / "analyzers/design-detector.md").read_text().split())
    assert "`overused-font` (Inter, Roboto, …) is a note only on a `landing` page kind" in detector
    assert 'dismiss it as "app UI"' in detector
    contract = " ".join((DEV / "analyzers/CONTRACT.md").read_text().split())
    assert "and the **page kind**: `landing`" in contract
