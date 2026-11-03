"""Report safe retirement candidates among registered Git worktrees."""
from __future__ import annotations

import argparse
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

CATEGORIES = ("main-checkout", "locked", "current", "detached-or-missing-branch",
              "unmerged", "dirty", "recent", "removable")
CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)


def inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def parse_worktrees(output: str) -> list[dict[str, str | bool]]:
    entries = []
    for block in output.strip().split("\n\n"):
        if not block:
            continue
        item: dict[str, str | bool] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            item[key] = value if value else True
        entries.append(item)
    return entries


def dirty_paths(path: Path) -> list[str]:
    normal = git(path, "status", "--short")
    ignored = git(path, "status", "--short", "--ignored")
    if normal.returncode or ignored.returncode:
        return ["status failed"]
    paths = [line[3:] for line in normal.stdout.splitlines()]
    for line in ignored.stdout.splitlines():
        if not line.startswith("!! "):
            continue
        name = line[3:].rstrip("/")
        if not any(part in CACHES for part in Path(name).parts):
            paths.append(name)
    return paths


def classify(root: Path, cwd: Path, item: dict[str, str | bool], hours: float) -> tuple[str, str]:
    path = Path(str(item["worktree"])).absolute()
    if path == root or not inside(path, root / ".worktrees"):
        return "main-checkout", ""
    if "locked" in item:
        return "locked", ""
    if inside(cwd, path):
        return "current", ""
    if "prunable" in item or "branch" not in item:
        return "detached-or-missing-branch", ""
    branch = str(item["branch"]).removeprefix("refs/heads/")
    merged = git(root, "merge-base", "--is-ancestor", branch, "main")
    if merged.returncode:
        ahead = git(root, "rev-list", "--count", "main.." + branch)
        return "unmerged", f"ahead {ahead.stdout.strip() if ahead.returncode == 0 else '?'}"
    dirty = dirty_paths(path)
    if dirty:
        return "dirty", "dirty: " + ", ".join(dirty[:5])
    dotgit = path / ".git"
    if not dotgit.is_file():
        return "detached-or-missing-branch", "missing .git file"
    if time.time() - dotgit.stat().st_mtime < hours * 3600:
        return "recent", ""
    return "removable", ""


def run(root: Path, cwd: Path, argv: list[str]) -> tuple[int, list[str]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--min-age-hours", type=float, default=24)
    args = parser.parse_args(argv)
    root, cwd = root.absolute(), cwd.absolute()
    if args.apply and any(part == ".worktrees" for part in cwd.parts):
        return 2, ["Refusing --apply from inside .worktrees; start a fresh shell in the main checkout."]
    result = git(root, "worktree", "list", "--porcelain")
    if result.returncode:
        return 2, [result.stderr.strip()]
    items = parse_worktrees(result.stdout)
    groups: dict[str, list[tuple[dict[str, str | bool], str]]] = {key: [] for key in CATEGORIES}
    registered = {Path(str(item["worktree"])).absolute() for item in items}
    for item in items:
        category, note = classify(root, cwd, item, args.min_age_hours)
        groups[category].append((item, note))
    lines = []
    for category, entries in groups.items():
        lines.append(f"{category} ({len(entries)})")
        for item, note in entries:
            branch = str(item.get("branch", "-")).removeprefix("refs/heads/")
            lines.append(f"{category}  {branch}  {item['worktree']}" + (f"  {note}" if note else ""))
    orphans = []
    folder = root / ".worktrees"
    if folder.exists():
        for child in sorted(folder.iterdir()):
            if not child.is_dir() or child.absolute() in registered:
                continue
            if child.is_symlink() or child.is_junction():
                lines.append(f"orphan  {child}  junction/symlink; manual review")
                continue
            files = sum(1 for path in child.rglob("*") if path.is_file() or path.is_symlink())
            orphans.append((child, files))
            lines.append(f"orphan  {child}  {'empty' if files == 0 else f'has files ({files})'}")
    lines.append(f"summary: {len(items)} registered; {len(groups['removable'])} removable; {len(orphans)} orphans")
    if not args.apply:
        return 0, lines
    failed = False
    for item, _ in groups["removable"]:
        path = str(item["worktree"])
        branch = str(item["branch"]).removeprefix("refs/heads/")
        if Path(path).is_symlink() or Path(path).is_junction():
            lines.append(f"Skipped junction/symlink: {path}")
            failed = True
            continue
        lines.append(f"git worktree remove {path}")
        removed = git(root, "worktree", "remove", path)
        if removed.returncode:
            lines.append((removed.stderr or removed.stdout).strip())
            failed = True
            continue
        lines.append(f"git branch -d {branch}")
        deleted = git(root, "branch", "-d", branch)
        if deleted.returncode:
            lines.append((deleted.stderr or deleted.stdout).strip())
            failed = True
    lines.append("git worktree prune")
    pruned = git(root, "worktree", "prune")
    if pruned.returncode:
        lines.append((pruned.stderr or pruned.stdout).strip())
        failed = True
    for child, files in orphans:
        if files:
            continue
        try:
            for directory, _, _ in os.walk(child, topdown=False, followlinks=False):
                Path(directory).rmdir()
            lines.append(f"rmdir {child}")
        except OSError as exc:
            lines.append(str(exc))
            failed = True
    return int(failed), lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", type=Path)
    known, rest = parser.parse_known_args(argv)
    cwd = Path.cwd()
    root = known.root or Path(git(cwd, "rev-parse", "--show-toplevel").stdout.strip())
    code, lines = run(root, cwd, rest)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
