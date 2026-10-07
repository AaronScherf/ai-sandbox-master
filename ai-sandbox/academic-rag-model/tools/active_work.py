"""Read-only report of open agent worktrees.

Lists each task branch with its changed-file count against main, flags
overlaps between branches and with the main checkout's uncommitted files, and
marks branches already merged into main as retirement candidates. Nothing is
removed, merged, or pushed.
"""
from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

from tools.git_workflow import (
    MAIN_BRANCH,
    changed_since_merge_base,
    dirty_files,
    is_ancestor,
    list_worktrees,
    main_checkout,
)

MAIN_LABEL = "main checkout uncommitted"


def build_report(cwd: Path) -> list[str]:
    main = main_checkout(cwd)
    worktrees = list_worktrees(cwd)[1:]
    if not worktrees:
        return ["no open worktrees"]
    lines: list[str] = []
    changes: dict[str, set[str]] = {}
    for wt in worktrees:
        if wt.branch is None:
            lines.append(f"detached HEAD at {wt.path} (no branch to land)")
            continue
        uncommitted = dirty_files(wt.path)
        if is_ancestor(main.path, wt.branch, MAIN_BRANCH) and not uncommitted:
            lines.append(f"{wt.branch} ({wt.path}): merged into main; retirement candidate")
            continue
        changed = changed_since_merge_base(main.path, MAIN_BRANCH, wt.branch) | uncommitted
        changes[wt.branch] = changed
        note = f" (includes {len(uncommitted)} uncommitted)" if uncommitted else ""
        lines.append(f"{wt.branch} ({wt.path}): {len(changed)} files vs main{note}")
    for a, b in combinations(sorted(changes), 2):
        shared = changes[a] & changes[b]
        if shared:
            lines.append(f"OVERLAP {a} <-> {b}: {', '.join(sorted(shared))}")
    main_dirty = dirty_files(main.path)
    for name in sorted(changes):
        shared = changes[name] & main_dirty
        if shared:
            lines.append(f"OVERLAP {name} <-> {MAIN_LABEL}: {', '.join(sorted(shared))}")
    lines.append(
        f"Live-vault runs: run from {main.path} or pass --root "
        f"{main.path / 'ai-sandbox' / 'academic-hub'}"
    )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report open agent worktrees (read-only).")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    for line in build_report(args.cwd.resolve()):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
