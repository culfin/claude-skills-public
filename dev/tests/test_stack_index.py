import importlib.util, os, re, pathlib

DEV = pathlib.Path(__file__).resolve().parents[1]
STACK = DEV / "stack"
INDEX = STACK / "INDEX.md"
CHECKOUTS = pathlib.Path(os.environ.get("DEV_STACK_DIR", os.path.expanduser("~/.claude/dev-stack")))
GIT_SOURCES = {"docker", "gha", "better-auth", "postgres", "stripe", "fastify"}
DOC_TECHNOLOGIES = ["Next.js", "React", "Tailwind", "shadcn", "Base UI", "Radix", "PostgreSQL",
                    "better-auth", "Zod", "Vitest", "Playwright", "Docker", "GitHub Actions", "Tauri",
                    "Rust", "Svelte", "next-intl", "TanStack", "Biome", "TypeScript", "Stripe", "Sentry",
                    "AI SDK", "Astro", "Fastify", "Kotlin", "Swift", "pnpm"]

spec = importlib.util.spec_from_file_location("check_source_update", DEV / "scripts/check-source-update.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def table(path, heading):
    """Rows (list of cells, backticks kept) of the first table after `heading`."""
    text = path.read_text()
    section = text.split(heading, 1)[1] if heading else text
    rows, started = [], False
    for line in section.splitlines():
        if line.startswith("|"):
            started = True
            if not line.startswith("|---"):
                rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif started:
            break
    return rows[1:]  # without the header


def detection():
    return table(INDEX, "## 1. Detection")


def triggers():
    return [[c.strip("`") if i else c for i, c in enumerate(r)] for r in table(INDEX, "## 2. Trigger")]


def stack_ids():
    return {r[1].strip("`") for r in detection()}


def test_detection_rows_well_formed():
    rows = detection()
    assert len(rows) >= 19
    for indicator, stack_id, also in rows:
        assert indicator and also, stack_id
        assert re.fullmatch(r"`[a-z][a-z0-9-]*`", stack_id), stack_id
    ids = [r[1] for r in rows]
    assert len(ids) == len(set(ids)), "a stack id is detected by exactly one row"
    for expected in ("nextjs", "shadcn", "postgres", "ios", "winui", "rust", "tauri", "android", "expo",
                     "svelte", "web", "docker", "gha", "better-auth", "stripe", "fastify", "ai-sdk",
                     "playwright", "tailwind"):
        assert expected in stack_ids(), expected


def test_trigger_rows_well_formed():
    rows = triggers()
    assert rows
    for trigger, load, how in rows:
        assert how in {"read", "subagent"}, trigger
        match = re.match(r"`([a-z0-9-]+)` ((?:4a|4c|5c|5g|debug)(?:/(?:4a|4c|5c|5g|debug))*): \S", trigger)
        assert match, f"trigger must read '`<stack id>` <steps>: <condition>': {trigger}"
        assert match.group(1) in stack_ids(), f"unknown stack id in trigger: {trigger}"
        if load.startswith("$DEV_STACK_DIR/"):
            source = load.split("/")[1]
            assert source == match.group(1), f"row of stack {match.group(1)} loads from source {source}"
            assert source in GIT_SOURCES, load


def test_index_paths_exist():
    """In-repo paths must exist; checkout paths only when that checkout is present (otherwise the
    step is skipped at run time); node_modules paths belong to the project, not to this repo."""
    for trigger, load, how in triggers():
        path = load.split("#")[0]
        if path.startswith("$DEV_STACK_DIR/"):
            rel = path.removeprefix("$DEV_STACK_DIR/")
            if (CHECKOUTS / rel.split("/")[0]).is_dir():
                assert (CHECKOUTS / rel).exists(), load
        elif path.startswith("node_modules/"):
            assert ".." not in path, load
        else:
            assert (DEV / path).exists(), load


def test_read_rows_stay_within_the_inline_limit():
    for trigger, load, how in triggers():
        if how == "read" and load.startswith("$DEV_STACK_DIR/"):
            path = CHECKOUTS / load.removeprefix("$DEV_STACK_DIR/")
            if path.is_file():
                assert len(path.read_text().splitlines()) <= 200, f"{load}: switch the row to subagent"


def test_index_and_checker_agree_on_every_path():
    """Every $DEV_STACK_DIR/<id>/<path> written anywhere in dev/*.md is a read path of the checker
    and the other way round; another spelling of the root fails instead of being dropped."""
    contract = DEV / "sources.md"
    checker = {f"{s}/{p}" for s in GIT_SOURCES for p in m.read_paths(s, contract) if not m.LICENSE_RE.match(p)}
    written = set()
    for f in DEV.rglob("*.md"):
        text = f.read_text()
        assert "${DEV_STACK_DIR}" not in text, f.name
        assert not re.search(r"~/\.claude/dev-stack/\w", text), f"{f.name}: write $DEV_STACK_DIR/<id>/…"
        for hit in re.findall(r"\$DEV_STACK_DIR/([^\s`|)]+)", text):
            if "<" in hit or "/" not in hit.rstrip("/"):
                continue  # placeholder (<id>) or a bare source root (contract location)
            written.add(hit.split("#")[0])
    assert written == checker
    assert written == {load.removeprefix("$DEV_STACK_DIR/") for _, load, _ in triggers()
                       if load.startswith("$DEV_STACK_DIR/")}
    for rel in written:
        assert not rel.startswith("/") and all(s not in ("", ".", "..") for s in rel.split("/")), rel


def test_every_read_path_of_a_scoped_source_is_inside_its_scope():
    contract = DEV / "sources.md"
    for source in m.source_ids(contract):
        scope = m.scan_scope(source, contract)
        assert (scope is not None) == (source in GIT_SOURCES), source
        if scope is None:
            continue
        for rel in m.read_paths(source, contract):
            assert m._in_scope(rel, scope), f"{source}: {rel} is read but not scanned"
        emitted = m.scope_paths(source, contract)
        for rel in m.read_paths(source, contract):
            assert any(rel == e or rel.startswith(e + "/") for e in emitted), f"{source}: {rel}"


def test_containment_wording():
    index = " ".join(INDEX.read_text().split())
    contract = " ".join((DEV / "sources.md").read_text().split())
    assert "In both modes nothing outside the listed file's folder is read" in index
    assert "no skill or instruction fetched from a URL the source names" in index
    assert "For `read` and `subagent` rows alike nothing outside the listed file's folder is read" in contract
    assert "no sibling skill, no skill or instruction fetched from a URL the source names" in contract
    assert "No script a source ships is executed and no vendor CLI or API call is made" in contract
    assert "except `nextjs`" in (DEV / "gate.md").read_text()
    assert "row `playwright`" in (DEV / "debugger.md").read_text()
    assert "5g = " in index and "debug = " in index


def test_every_git_stack_source_has_rows_and_a_contract_entry():
    contract = DEV / "sources.md"
    listed = {row[0]: row for row in m.list_sources(contract)}
    in_index = {load.split("/")[1] for _, load, _ in triggers() if load.startswith("$DEV_STACK_DIR/")}
    assert in_index == GIT_SOURCES
    for source in GIT_SOURCES:
        assert listed[source] == (source, "git", f"$DEV_STACK_DIR/{source}"), source
        reads = m.read_paths(source, contract)
        assert any(p.endswith("SKILL.md") for p in reads), source
        assert "stack/INDEX.md" not in reads, "the reference is resolved, not passed on"
    contract_stack = {i for i, _, loc in listed.values() if loc.startswith("$DEV_STACK_DIR/")}
    assert contract_stack == GIT_SOURCES


def test_bundled_sources_are_indexed():
    loads = [load for _, load, _ in triggers()]
    for path in ("node_modules/next/dist/docs/index.md", "node_modules/ai/docs/",
                 "node_modules/fastify/docs/index.md",
                 "node_modules/playwright-core/lib/tools/skills/playwright-trace/SKILL.md"):
        assert path in loads, path


def test_docs_table_covers_every_technology_in_fixed_order():
    text = (STACK / "docs.md").read_text()
    order = [text.index(word) for word in ("**Bundled**", "**Official access**", "**`llms.txt`**", "**Context7**")]
    assert order == sorted(order)
    assert "never `llms-full.txt`" in text
    rows = table(STACK / "docs.md", "")
    names = [r[0] for r in rows]
    for tech in DOC_TECHNOLOGIES:
        assert any(tech in n for n in names), tech
    for row in rows:
        assert len(row) == 5, row[0]
        assert any(cell != "—" for cell in row[1:]), f"no docs source at all: {row[0]}"
        assert "llms-full" not in " ".join(row), row[0]


def test_budgets():
    assert len(INDEX.read_text().splitlines()) <= 80
    assert len((STACK / "docs.md").read_text().splitlines()) <= 60
    skill = (DEV / "SKILL.md").read_text()
    assert len(skill.splitlines()) < 392, "moving the detection table out must make SKILL.md shorter"
    assert "| Indicator |" not in skill, "the detection table lives in stack/INDEX.md"
    assert "stack/INDEX.md" in skill and "$TECH_STACKS" in skill


def test_no_private_data():
    for f in list(STACK.glob("*.md")):
        t = f.read_text()
        assert "/Users/" not in t and "/home/" not in t and ".ts.net" not in t, f.name
        assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", t), f.name


def test_missing_source_is_skipped_never_passed():
    index = " ".join(INDEX.read_text().split())
    assert "skipped: <reason>" in index and "never a silent pass" in index
    gate = (DEV / "gate.md").read_text()
    assert "- [ ] Tech-Stack Review: <stack id>" in gate
    assert "$DEV_STACK_DIR" in gate
    script = (DEV / "scripts/check-evidence.py").read_text()
    assert '"tech-stack review"' in script


def test_wired_into_all_three_steps_by_one_rule():
    triggers_md = (DEV / "tech-stack-triggers.md").read_text()
    rule = triggers_md.split("**Stack sources", 1)[1].split("\n\n", 1)[0]
    for step in ("4a", "4c", "5c"):
        assert step in rule, step
    assert "stack/INDEX.md" in rule and "stack/docs.md" in rule
    for stack in GIT_SOURCES - {"postgres"}:
        assert f"`{stack}`" not in triggers_md, f"{stack}: rows belong in stack/INDEX.md, not in three files"


def test_overrides_in_contract():
    text = " ".join((DEV / "sources.md").read_text().split())
    assert "**O9**" in text and "**O10**" in text
    assert "conventions win" in text
    assert "report_usage" in text
    stripe = next(l for l in (DEV / "sources.md").read_text().splitlines() if l.startswith("| stripe |"))
    assert "O10" in stripe
