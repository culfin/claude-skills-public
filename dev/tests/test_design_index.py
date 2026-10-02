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
