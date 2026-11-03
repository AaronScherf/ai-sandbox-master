"""Report safe retirement candidates among registered Git worktrees."""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import time
from collections import Counter
from pathlib import Path

CATEGORIES = ("main-checkout", "locked", "current", "detached-or-missing-branch",
              "unmerged", "dirty", "recent", "removable")
CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP = CACHES | {".venv", "node_modules"}
NEW_CATEGORIES = ("unknown-base", "identical-to-main", "differs", "manual-review", "kept-by-name")


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


def classify(root: Path, cwd: Path, item: dict[str, str | bool], hours: float,
             base: str = "main", allowed: Path | None = None) -> tuple[str, str]:
    path = Path(str(item["worktree"])).absolute()
    if path == root or not inside(path, allowed or root / ".worktrees"):
        return "main-checkout", ""
    if git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{base}").returncode:
        return "unknown-base", "missing local " + base
    if "locked" in item:
        return "locked", ""
    if inside(cwd, path):
        return "current", ""
    if "prunable" in item or "branch" not in item:
        return "detached-or-missing-branch", ""
    branch = str(item["branch"]).removeprefix("refs/heads/")
    merged = git(root, "merge-base", "--is-ancestor", branch, base)
    if merged.returncode:
        ahead = git(root, "rev-list", "--count", base + ".." + branch)
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


def owner_from_gitfile(path: Path) -> tuple[Path, Path] | None:
    dotgit = path / ".git"
    if not dotgit.is_file():
        return None
    try:
        content = dotgit.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content.startswith("gitdir: "):
        return None
    target = Path(content[8:])
    if not target.is_absolute():
        target = path / target
    target = target.resolve()
    if target.parent.name != "worktrees" or target.parent.parent.name != ".git":
        return None
    return target.parent.parent.parent, target


def stale_audit(root: Path, folder: Path) -> tuple[str, str, int]:
    if folder.name.startswith("_"):
        return "kept-by-name", "", 0
    if folder.is_symlink() or folder.is_junction():
        return "manual-review", "junction/symlink", 0
    tree = git(root, "ls-tree", "-r", "main")
    if tree.returncode:
        return "manual-review", "cannot read main tree", 0
    hashes = {}
    for line in tree.stdout.splitlines():
        head, _, name = line.partition("\t")
        parts = head.split()
        if len(parts) == 3:
            hashes[name.replace("/", os.sep)] = parts[2]
    differences = []
    count = 0
    for directory, dirs, files in os.walk(folder, followlinks=False):
        parent = Path(directory)
        for name in list(dirs):
            path = parent / name
            if path.is_symlink() or path.is_junction():
                return "manual-review", "junction/symlink", count
            if name in SKIP:
                dirs.remove(name)
        for name in files:
            if name == ".git" or name in SKIP:
                continue
            path = parent / name
            if path.is_symlink() or path.is_junction():
                return "manual-review", "junction/symlink", count
            count += 1
            relative = str(path.relative_to(folder))
            digest = git(root, "hash-object", str(path))
            if digest.returncode or hashes.get(relative) != digest.stdout.strip():
                differences.append(relative)
    if differences:
        return "differs", f"has files ({count}); differs ({len(differences)}): " + ", ".join(differences[:5]), count
    return "identical-to-main", f"{'empty' if count == 0 else f'has files ({count})'}", count


def remove_readonly(function, path, exc):
    os.chmod(path, stat.S_IWRITE)
    function(path)


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
    children: dict[Path, set[Path]] = {}
    stale = []
    folder = root / ".worktrees"
    if folder.exists():
        for child in sorted(folder.iterdir()):
            if not child.is_dir() or child.absolute() in registered:
                continue
            owner = owner_from_gitfile(child)
            if owner and owner[0].exists() and owner[1].exists():
                children.setdefault(owner[0], set()).add(child.absolute())
            else:
                category, note, count = stale_audit(root, child)
                stale.append((child, category, note, count))
    child_groups = []
    discovery_failed = False
    for owner, paths in sorted(children.items(), key=lambda pair: str(pair[0])):
        listed = git(owner, "worktree", "list", "--porcelain")
        if listed.returncode:
            lines.append(f"repo: {owner}")
            lines.append((listed.stderr or listed.stdout).strip())
            discovery_failed = True
            continue
        owner_items = parse_worktrees(listed.stdout)
        owner_groups = {key: [] for key in CATEGORIES + ("unknown-base",)}
        found = set()
        for item in owner_items:
            path = Path(str(item["worktree"])).absolute()
            category, note = classify(owner, cwd, item, args.min_age_hours, "main", folder)
            owner_groups[category].append((item, note))
            if path in paths:
                found.add(path)
        lines.append(f"repo: {owner}")
        for category, entries in owner_groups.items():
            lines.append(f"{category} ({len(entries)})")
            for item, note in entries:
                branch = str(item.get("branch", "-")).removeprefix("refs/heads/")
                lines.append(f"{category}  {branch}  {item['worktree']}" + (f"  {note}" if note else ""))
        child_groups.append((owner, owner_groups))
        for missing in sorted(paths - found):
            category, note, count = stale_audit(root, missing)
            stale.append((missing, category, note, count))
    counts = Counter(category for _, category, _, _ in stale)
    for path, category, note, _ in stale:
        lines.append(f"{category}  {path}" + (f"  {note}" if note else ""))
    all_groups = [(root, groups)] + child_groups
    registered_count = len(items) + sum(sum(len(v) for v in group.values()) for _, group in child_groups)
    removable_count = sum(len(group["removable"]) for _, group in all_groups)
    lines.append(f"summary: {registered_count} registered; {removable_count} removable; " +
                 "; ".join(f"{counts[name]} {name}" for name in NEW_CATEGORIES))
    if not args.apply:
        return 0, lines
    failed = discovery_failed
    for owner, group in all_groups:
      for item, _ in group["removable"]:
        path = str(item["worktree"])
        branch = str(item["branch"]).removeprefix("refs/heads/")
        if Path(path).is_symlink() or Path(path).is_junction():
            lines.append(f"Skipped junction/symlink: {path}")
            failed = True
            continue
        lines.append(f"git worktree remove {path}")
        removed = git(owner, "worktree", "remove", path)
        if removed.returncode:
            lines.append((removed.stderr or removed.stdout).strip())
            failed = True
            continue
        lines.append(f"git branch -d {branch}")
        deleted = git(owner, "branch", "-d", branch)
        if deleted.returncode:
            lines.append((deleted.stderr or deleted.stdout).strip())
            failed = True
    for owner, _ in all_groups:
        lines.append("git worktree prune")
        pruned = git(owner, "worktree", "prune")
        if pruned.returncode:
            lines.append((pruned.stderr or pruned.stdout).strip())
            failed = True
    for child, category, _, _ in stale:
        if category != "identical-to-main":
            continue
        try:
            fresh, note, _ = stale_audit(root, child)
            if fresh != "identical-to-main":
                lines.append(f"Skipped {child}: changed before removal ({fresh}: {note})")
                failed = True
                continue
            shutil.rmtree(child, onexc=remove_readonly)
            lines.append(f"shutil.rmtree {child}")
        except OSError as exc:
            lines.append(str(exc))
            failed = True
    return int(failed), lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", type=Path)
    known, rest = parser.parse_known_args(argv)
    cwd = Path.cwd()
    root = known.root or Path(git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()).parent
    code, lines = run(root, root, rest)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
