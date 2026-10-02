#!/usr/bin/env python3
"""Deterministic pre-check of a new version of a source /dev references (contract: sources.md).

Compares an old and a new tree of one source and reports what a reviewer must look at:
read paths that vanished, changed invocation switches in front matter, newly added hooks,
settings writes, pipe-to-shell, install steps or network calls, a changed licence, and
read files that more than doubled. Read-only: no network, no writes.

Usage: check-source-update.py --source <id> --old <dir> --new <dir> [--contract sources.md]
Prints {"source", "deterministic": "ok|findings", "findings": [{"kind", "detail"}]} as JSON.
Exit 0 whenever the check ran (findings or not), 2 on a usage error.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SWITCHES = ('disable-model-invocation', 'user-invocable', 'allowed-tools')
SCRIPT_EXT = {'.sh', '.bash', '.zsh', '.py', '.js', '.mjs', '.cjs', '.ts', '.ps1', '.rb'}
SKIP_DIRS = {'.git', 'node_modules', 'target', '.build', 'dist', '__pycache__'}
MAX_BYTES = 1_000_000
HOOK_EVENTS = r'(PreToolUse|PostToolUse|SessionStart|SessionEnd|UserPromptSubmit|Stop|SubagentStop|PreCompact|Notification)'
# kind -> (regex, where): "scripts" = script files, "json" = JSON files, "all" = scripts + read files
PATTERNS = {
    'new-hook': (re.compile(r'"hooks"\s*:|"' + HOOK_EVENTS + r'"\s*:|\bhooks\s+on\b'), 'all+json'),
    'new-settings-json': (re.compile(r'settings(\.local)?\.json'), 'all'),
    'new-pipe-to-shell': (re.compile(r'\b(curl|wget|iwr|Invoke-WebRequest)\b[^\n|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b'), 'all'),
    'new-install-step': (re.compile(r'\bnpx\s+[^\n`]*\binstall\b|\bnpm\s+(i|install)\s+(-g|--global)\b|\bplugin\s+install\b'), 'all'),
    'new-network-access': (re.compile(r'\b(curl|wget|Invoke-WebRequest)\b|\bfetch\(\s*[\'"`]https?://|\brequests\.(get|post|put)\(|\burllib\.request\b'), 'scripts'),
}
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
        if p.is_file() and not SKIP_DIRS.intersection(rel.parts[:-1]) and p.stat().st_size <= MAX_BYTES:
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


def _pattern_counts(root, reads):
    counts = {}
    for rel, path in _files(root):
        script, is_json, is_read = _is_script(rel, path), rel.endswith('.json'), rel in reads
        if not (script or is_json or is_read):
            continue
        text = _text(path)
        for kind, (regex, where) in PATTERNS.items():
            applies = (script if where == 'scripts' else script or is_read or (is_json and where == 'all+json'))
            if applies:
                n = len(regex.findall(text))
                if n:
                    counts[(kind, rel)] = n
    return counts


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

    before, after = _pattern_counts(old, set(reads)), _pattern_counts(new, set(reads))
    for (kind, rel), n in sorted(after.items()):
        if n > before.get((kind, rel), 0):
            findings.append({'kind': kind, 'detail': f'{rel}: {before.get((kind, rel), 0)} -> {n} match(es)'})

    lo, ln = _licenses(old), _licenses(new)
    for name in sorted(set(lo) | set(ln)):
        if lo.get(name) != ln.get(name):
            state = 'added' if name not in lo else 'removed' if name not in ln else 'changed'
            findings.append({'kind': 'license-changed', 'detail': f'{name} {state}'})

    return {'source': source, 'deterministic': 'findings' if findings else 'ok', 'findings': findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', required=True)
    parser.add_argument('--old', required=True)
    parser.add_argument('--new', required=True)
    parser.add_argument('--contract', default=str(DEV / 'sources.md'))
    args = parser.parse_args(argv)
    try:
        for label in ('old', 'new'):
            if not Path(getattr(args, label)).is_dir():
                raise UsageError(f'--{label} is not a directory: {getattr(args, label)}')
        if not Path(args.contract).is_file():
            raise UsageError(f'contract not found: {args.contract}')
        result = check(args.source, args.old, args.new, args.contract)
    except UsageError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
