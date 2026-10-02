#!/usr/bin/env python3
"""Deterministic pre-check of a new version of a source /dev references (contract: sources.md).

Compares an old and a new tree of one source and reports what a reviewer must look at:
read paths that vanished, changed invocation switches in front matter, newly added hooks,
settings writes, pipe-to-shell, install steps or network calls, a changed licence, and
read files that more than doubled. Read-only: no network, no writes.

Usage: check-source-update.py --source <id> --old <dir> --new <dir> [--contract sources.md]
Prints {"source", "deterministic": "ok|findings", "findings": [{"kind", "detail"}]} as JSON.

       check-source-update.py --validate-entry <queue file> [--contract sources.md]
Validates one update-queue entry (updates.md) and prints {"file", "valid", "errors", "argv"};
"argv" is the only command /dev updates may run for it (null = do not offer Apply).

       check-source-update.py --list-sources [--contract sources.md]
Prints one line per source: id<TAB>kind<TAB>location. No rows is an error, never an empty list.

       check-source-update.py --hold-kinds
Prints the finding kinds that always hold an update for the user's decision, one per line.

Exit 0 whenever the check ran (findings or not, valid or not), 2 on a usage error.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SWITCHES = ('disable-model-invocation', 'user-invocable', 'allowed-tools')
SCRIPT_EXT = {'.sh', '.bash', '.zsh', '.py', '.js', '.mjs', '.cjs', '.ts', '.ps1', '.rb'}
# Only .git is skipped (candidates come from git archive and have none). No other directory is
# exempt: a hook under dist/ or node_modules/ is still a hook.
SKIP_DIRS = {'.git'}
MAX_BYTES = 1_000_000  # larger scannable files are not read; if changed -> scan-incomplete
HOOK_EVENTS = r'(PreToolUse|PostToolUse|SessionStart|SessionEnd|UserPromptSubmit|Stop|SubagentStop|PreCompact|Notification)'
# kind -> (regex, where): "scripts" = scripts + JSON; "all" = scripts + JSON + read files.
# new-hook in a JSON file that parses is decided by _hook_entries; the regex is the fallback.
PATTERNS = {
    'new-hook': (re.compile(r'"hooks"\s*:|"' + HOOK_EVENTS + r'"\s*:|\bhooks\s+on\b'), 'all'),
    'new-settings-json': (re.compile(r'settings(\.local)?\.json'), 'all'),
    'new-pipe-to-shell': (re.compile(r'\b(curl|wget|iwr|Invoke-WebRequest)\b[^\n|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b'), 'all'),
    'new-install-step': (re.compile(r'\bnpx\s+[^\n`]*\binstall\b|\bnpm\s+(i|install)\s+(-g|--global)\b|\bplugin\s+install\b'), 'all'),
    'new-network-access': (re.compile(r'\b(curl|wget|Invoke-WebRequest)\b|\bfetch\(\s*[\'"`]https?://|\brequests\.(get|post|put)\(|\burllib\.request\b'), 'scripts'),
}
APPLIER = 'skills-update-waechter.sh'
QUEUE_KINDS = {'git', 'plugin', 'agents-skill'}
# Findings that hold an update whatever the review agent says (sources.md, "Deterministic check").
HOLD_KINDS = ('missing-read-path', 'new-hook', 'new-settings-json', 'new-pipe-to-shell',
              'new-install-step', 'license-changed', 'scan-incomplete')
SAFE_TOKEN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]*$')  # source and new: no leading '-', no '/', no space
VERDICTS = {'passt', 'unklar', 'widerspruch'}
ENTRY_FIELDS = {'source': str, 'kind': str, 'old': str, 'new': str, 'verdict': str, 'reasons': list,
                'deterministic_findings': list, 'diff_summary': str, 'created': str, 'apply': list}
LICENSE_RE = re.compile(r'^(LICEN[CS]E|COPYING)(\.\w+)?$', re.I)


class UsageError(Exception):
    pass


def _rows(contract):
    for line in Path(contract).read_text().splitlines():
        if line.startswith('|') and not line.startswith('|---'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 4 and cells[0] != 'id':
                yield cells


def source_ids(contract):
    return [cells[0] for cells in _rows(contract)]


def _index_paths(source, contract):
    index = Path(contract).parent / 'design/INDEX.md'
    prefix = f'$DEV_DESIGN_DIR/{source}/'
    paths = []
    for line in index.read_text().splitlines():
        for token in re.findall(r'`([^`]+)`', line):
            if token.startswith(prefix):
                paths.append(token[len(prefix):].split('#')[0])
    return paths


def _superpowers_paths(contract):
    script = Path(contract).parent / 'scripts/check-superpowers.py'
    spec = importlib.util.spec_from_file_location('check_superpowers', script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.required_paths()


def read_paths(source, contract):
    """Paths relative to the source root that /dev reads; references are resolved, not copied."""
    for cells in _rows(contract):
        if cells[0] != source:
            continue
        paths = []
        for token in re.findall(r'`([^`]+)`', cells[3]):
            if token == 'design/INDEX.md':
                paths += _index_paths(source, contract)
            elif token == 'scripts/check-superpowers.py':
                paths += _superpowers_paths(contract)
            else:
                paths.append(token)
        return list(dict.fromkeys(paths))
    raise UsageError(f'unknown source {source!r} in {contract}')


def _files(root):
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if p.is_file() and not SKIP_DIRS.intersection(rel.parts[:-1]):
            yield rel.as_posix(), p


def _is_script(rel, path):
    if Path(rel).suffix in SCRIPT_EXT:
        return True
    try:
        with open(path, 'rb') as fh:
            return fh.read(2) == b'#!'
    except OSError:
        return False


def _text(path):
    try:
        return path.read_text(errors='replace')
    except OSError:
        return ''


def _front_matter(text):
    if not text.startswith('---'):
        return {}
    lines = text.splitlines()[1:]
    data, key = {}, None
    for line in lines:
        if line.strip() == '---':
            break
        match = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if match:
            key = match.group(1)
            data[key] = match.group(2).strip()
        elif key and line.strip():
            data[key] = (data[key] + ' ' + line.strip()).strip()
    return data


def _hook_entries(data):
    """Every hook entry in a parsed JSON document as (event, matcher, hook) strings, at any depth."""
    entries = set()
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'hooks' and isinstance(value, dict):
                    for event, groups in value.items():
                        for group in groups if isinstance(groups, list) else [groups]:
                            inner = group.get('hooks') if isinstance(group, dict) else None
                            matcher = group.get('matcher') if isinstance(group, dict) else None
                            for hook in inner if isinstance(inner, list) else [group]:
                                entries.add((str(event), json.dumps(matcher),
                                             json.dumps(hook, sort_keys=True)))
                elif key == 'hooks' and value:
                    entries.add(('<reference>', '', json.dumps(value, sort_keys=True)))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(data)
    return entries


def _scan(root, reads):
    """Pattern counts per (kind, file), hook entries per JSON file, and files too large to scan."""
    counts, hooks, oversize = {}, {}, {}
    for rel, path in _files(root):
        script, is_json, is_read = _is_script(rel, path), rel.endswith('.json'), rel in reads
        if not (script or is_json or is_read):
            continue
        if path.stat().st_size > MAX_BYTES:
            oversize[rel] = path
            continue
        text = _text(path)
        parsed = False
        if is_json:
            try:
                hooks[rel] = _hook_entries(json.loads(text))
                parsed = True
            except ValueError:
                pass
        for kind, (regex, where) in PATTERNS.items():
            if kind == 'new-hook' and parsed:
                continue
            if where == 'scripts' and not (script or is_json):
                continue
            n = len(regex.findall(text))
            if n:
                counts[(kind, rel)] = n
    return counts, hooks, oversize


def _same_bytes(a, b):
    def digest(p):
        h = hashlib.sha256()
        with open(p, 'rb') as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b''):
                h.update(chunk)
        return h.digest()
    return a.is_file() and a.stat().st_size == b.stat().st_size and digest(a) == digest(b)


def _licenses(root):
    return {p.name: ' '.join(_text(p).split()) for p in root.iterdir() if p.is_file() and LICENSE_RE.match(p.name)}


def check(source, old, new, contract):
    old, new = Path(old), Path(new)
    reads = read_paths(source, contract)
    findings = []

    for rel in reads:
        if not (new / rel).exists():
            was = 'existed in the old version' if (old / rel).exists() else 'also missing in the old version'
            findings.append({'kind': 'missing-read-path', 'detail': f'{rel} ({was})'})

    for rel in reads:
        o, n = old / rel, new / rel
        if not (o.is_file() and n.is_file()):
            continue
        if rel.endswith('.md'):
            fo, fn = _front_matter(_text(o)), _front_matter(_text(n))
            for key in SWITCHES:
                if fo.get(key) != fn.get(key):
                    findings.append({'kind': 'frontmatter-switch-changed',
                                     'detail': f'{rel}: {key}: {fo.get(key)!r} -> {fn.get(key)!r}'})
        so, sn = o.stat().st_size, n.stat().st_size
        if so and sn > 2 * so:
            findings.append({'kind': 'size-jump', 'detail': f'{rel}: {so} -> {sn} bytes ({sn / so:.1f}x)'})

    (before, hooks_old, _), (after, hooks_new, oversize) = _scan(old, set(reads)), _scan(new, set(reads))
    for rel, path in sorted(oversize.items()):
        if not _same_bytes(old / rel, path):
            findings.append({'kind': 'scan-incomplete', 'detail':
                             f'{rel}: {path.stat().st_size} bytes, new or changed and over the {MAX_BYTES}-byte scan limit'})
    for rel, entries in sorted(hooks_new.items()):
        added = sorted(entries - hooks_old.get(rel, set()))
        if added:
            event, _, hook = added[0]
            findings.append({'kind': 'new-hook', 'detail': f'{rel}: {len(added)} new or changed hook '
                             f'entr{"y" if len(added) == 1 else "ies"}, e.g. {event}: {hook[:120]}'})
    for (kind, rel), n in sorted(after.items()):
        if n > before.get((kind, rel), 0):
            findings.append({'kind': kind, 'detail': f'{rel}: {before.get((kind, rel), 0)} -> {n} match(es)'})

    lo, ln = _licenses(old), _licenses(new)
    for name in sorted(set(lo) | set(ln)):
        if lo.get(name) != ln.get(name):
            state = 'added' if name not in lo else 'removed' if name not in ln else 'changed'
            findings.append({'kind': 'license-changed', 'detail': f'{name} {state}'})

    return {'source': source, 'deterministic': 'findings' if findings else 'ok', 'findings': findings}


def list_sources(contract):
    """(id, kind, location) per contract row; raises UsageError when there is none."""
    rows = [(c[0], c[1], c[2].strip('`')) for c in _rows(contract)]
    if not rows or not all(all(r) for r in rows):
        raise UsageError(f'no usable source rows in {contract}')
    return rows


def _row_kind(source, contract):
    for cells in _rows(contract):
        if cells[0] == source:
            return cells[1]
    return None


def validate_entry(path, contract, env=None):
    """Check one queue entry against updates.md; argv is the only command allowed for Apply."""
    env = os.environ if env is None else env
    path, errors = Path(path), []
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return {'file': path.name, 'valid': False, 'errors': [f'unreadable: {exc}'], 'argv': None}
    if not isinstance(data, dict):
        return {'file': path.name, 'valid': False, 'errors': ['not a JSON object'], 'argv': None}
    for key, typ in ENTRY_FIELDS.items():
        if not isinstance(data.get(key), typ):
            errors.append(f'field {key!r} missing or not a {typ.__name__}')
    for key in sorted(set(data) - set(ENTRY_FIELDS)):
        errors.append(f'unexpected field {key!r}')
    source, new, apply = data.get('source'), data.get('new'), data.get('apply')
    for key, value in (('source', source), ('new', new)):
        if isinstance(value, str) and not SAFE_TOKEN.fullmatch(value):
            errors.append(f'{key} {value!r} is outside the allowed charset [A-Za-z0-9][A-Za-z0-9._+-]*')
    if path.name != f'{source}-{new}.json':
        errors.append(f'file name {path.name!r} is not "<source>-<new>.json"')
    row_kind = _row_kind(source, contract)
    if row_kind is None:
        errors.append(f'source {source!r} is not in sources.md')
    elif data.get('kind') != row_kind or row_kind not in QUEUE_KINDS:
        errors.append(f'kind {data.get("kind")!r} does not match sources.md ({row_kind!r})')
    if data.get('verdict') not in VERDICTS:
        errors.append(f'verdict {data.get("verdict")!r} is not one of {sorted(VERDICTS)}')
    name = env.get('DEV_UPDATES_APPLIER') or APPLIER
    if apply != [name, '--apply', source, new]:
        errors.append(f'apply must be exactly ["{name}", "--apply", "<source>", "<new>"], got {apply!r}')
    argv = None
    if not errors:
        located = env.get('DEV_UPDATES_APPLIER_PATH') or shutil.which(name, path=env.get('PATH', ''))
        if located and os.path.isfile(located) and os.access(located, os.X_OK):
            argv = [located, '--apply', source, new]
    return {'file': path.name, 'valid': not errors, 'errors': errors, 'argv': argv}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source')
    parser.add_argument('--old')
    parser.add_argument('--new')
    parser.add_argument('--validate-entry', metavar='FILE')
    parser.add_argument('--list-sources', action='store_true')
    parser.add_argument('--hold-kinds', action='store_true')
    parser.add_argument('--contract', default=str(DEV / 'sources.md'))
    args = parser.parse_args(argv)
    try:
        modes = [bool(args.validate_entry), args.list_sources, args.hold_kinds,
                 bool(args.source or args.old or args.new)]
        if sum(modes) > 1:
            raise UsageError('use one of --source/--old/--new, --validate-entry, --list-sources, --hold-kinds')
        if args.hold_kinds:
            print('\n'.join(HOLD_KINDS))
            return 0
        if not Path(args.contract).is_file():
            raise UsageError(f'contract not found: {args.contract}')
        if args.list_sources:
            print('\n'.join('\t'.join(row) for row in list_sources(args.contract)))
            return 0
        if args.validate_entry:
            result = validate_entry(args.validate_entry, args.contract)
        else:
            for label in ('source', 'old', 'new'):
                if not getattr(args, label):
                    raise UsageError(f'--{label} is required')
            for label in ('old', 'new'):
                if not Path(getattr(args, label)).is_dir():
                    raise UsageError(f'--{label} is not a directory: {getattr(args, label)}')
            result = check(args.source, args.old, args.new, args.contract)
    except (UsageError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
