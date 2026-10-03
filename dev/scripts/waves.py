#!/usr/bin/env python3
"""Groups plan tasks into waves whose tasks may be implemented in parallel. Read-only.

    waves.py <tasks.json>

Input:  {"max": 5, "tasks": [{"id": "1", "files": ["a.py"], "after": []}, ...]}  (plan order)
Output: {"waves": [["1", "2"], ["3"]], "serial": ["3"]}

Two tasks share a wave only if neither needs the other (`after`), they touch no common file, and
neither is serial. A task is serial — alone in its wave — if it touches a lockfile, a dependency
manifest, a migration or SQL file (those collide in ways a file list does not show), or if its file
list is empty (independence cannot be proven). At most 5 tasks per wave: more parallel builds slow
the machine down more than they save. Exit 2 on an unknown dependency or a cycle.
"""
import json
import re
import sys

HARD_MAX = 5
SERIAL = re.compile(
    r"(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|pnpm-workspace\.yaml|yarn\.lock|bun\.lockb?"
    r"|Cargo\.toml|Cargo\.lock|go\.mod|go\.sum|poetry\.lock|uv\.lock|pyproject\.toml|requirements[^/]*\.txt"
    r"|composer\.(json|lock)|Gemfile(\.lock)?)$|(^|/)migrations?/|\.sql$")


def fail(msg):
    print(f"waves: {msg}", file=sys.stderr)
    return 2


def main(argv):
    if len(argv) != 2:
        return fail("usage: waves.py <tasks.json>")
    try:
        spec = json.load(open(argv[1]))
        tasks = spec["tasks"]
        limit = max(1, min(int(spec.get("max", HARD_MAX)), HARD_MAX))
        ids = [str(t["id"]) for t in tasks]
        files = {str(t["id"]): set(t.get("files") or []) for t in tasks}
        after = {str(t["id"]): [str(x) for x in t.get("after") or []] for t in tasks}
    except (OSError, ValueError, KeyError, TypeError) as e:
        return fail(f"malformed input: {e}")
    if len(ids) != len(set(ids)):
        dupes = [i for i in set(ids) if ids.count(i) > 1]
        return fail(f"duplicate task id(s): {', '.join(dupes)}")
    for i, deps in after.items():
        for d in deps:
            if d not in files:
                return fail(f"task {i} depends on unknown task {d}")
    serial = [i for i in ids if not files[i] or any(SERIAL.search(f) for f in files[i])]
    done, waves, left = set(), [], list(ids)
    while left:
        wave, used = [], set()
        for i in left:
            if len(wave) >= limit:
                break
            if any(d not in done for d in after[i]):
                continue                      # waits for an earlier wave
            if i in serial:
                if not wave:
                    wave = [i]                # a serial task runs alone ...
                    break                     # ... and closes its wave
                continue                      # not now; it gets its own wave later
            if files[i] & used:
                continue                      # shares a file with this wave
            wave.append(i)
            used |= files[i]
        if not wave:
            return fail("dependency cycle among: " + ", ".join(left))
        waves.append(wave)
        done |= set(wave)
        left = [i for i in left if i not in done]
    print(json.dumps({"waves": waves, "serial": serial}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
