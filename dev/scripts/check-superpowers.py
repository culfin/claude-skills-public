#!/usr/bin/env python3
"""Static capability check for an explicitly selected active plugin root; no network or writes."""
import argparse
import json
from pathlib import Path

REQUIRED = ('brainstorming', 'writing-plans', 'subagent-driven-development', 'executing-plans',
            'requesting-code-review', 'verification-before-completion', 'using-git-worktrees')

# Prompts and scripts execution.md hands to implementers and task reviewers.
SDD_FILES = ('implementer-prompt.md', 'task-reviewer-prompt.md', 're-review-prompt.md',
             'scripts/task-brief', 'scripts/review-package', 'scripts/sdd-workspace')

def required_paths():
    """Files /dev needs from the plugin root (also the read paths in sources.md)."""
    return ([f'skills/{name}/SKILL.md' for name in REQUIRED]
            + ['skills/brainstorming/scripts/start-server.sh', 'skills/brainstorming/scripts/stop-server.sh']
            + [f'skills/subagent-driven-development/{name}' for name in SDD_FILES])

def inspect(root):
    root = Path(root).resolve()
    required = required_paths()
    missing = [name for name in required if not (root / name).is_file()]
    versions = {}
    errors = []
    for manifest in ('.claude-plugin/plugin.json', '.codex-plugin/plugin.json', 'plugin.json'):
        path = root / manifest
        if path.is_file():
            try:
                data = json.loads(path.read_text())
                if not isinstance(data, dict): raise ValueError('manifest must be an object')
                if data.get('version'): versions[manifest] = str(data['version'])
            except (ValueError, OSError) as exc:
                errors.append(f'{manifest}: {exc}')
    if len(set(versions.values())) > 1: errors.append('Plugin manifest versions disagree')
    return {'root': str(root), 'status': 'blocked' if missing or errors else 'files-present',
            'versions': versions, 'missing': missing, 'errors': errors,
            'freshness': 'not-checked', 'runtimeCompatibility': 'not-tested'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    result = inspect(args.root)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result['status'] == 'blocked' else 0)
