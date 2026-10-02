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
    assert "| `/dev ui [scope]` | UI review and rework | `ui-review.md` |" in skill
    assert "/dev ui" in skill.split("---")[1]  # description front matter
    review = DEV / "ui-review.md"
    assert review.exists()
    assert len(review.read_text().splitlines()) <= 120

def test_skill_md_loads_on_demand():
    skill = (DEV / "SKILL.md").read_text()
    assert len(skill.splitlines()) <= 396
    section = skill.split("## Files of This Skill", 1)[1].split("\n---", 1)[0]
    listed = set()
    for line in section.splitlines():
        if line.startswith("|") and not line.startswith("|---") and "Read when" not in line:
            listed.update(re.findall(r"`([^`]+\.md)`", line.split("|")[1]))
    assert listed, "no files found in the 'Files of This Skill' table"
    for path in listed:
        assert (DEV / path).exists(), f"listed but missing: {path}"
    for f in DEV.glob("*.md"):
        if f.name != "SKILL.md":
            assert f.name in listed, f"not in 'Files of This Skill': {f.name}"

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
