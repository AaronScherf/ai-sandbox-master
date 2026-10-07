"""Git helpers shared by the agent landing tools (land_branch, active_work).

Paths from git are repo-relative with forward slashes. Callers working inside
a subproject strip the subproject prefix themselves.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

MAIN_BRANCH = "main"


class GitError(RuntimeError):
    """A git command exited non-zero."""


def run_git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str | None  # None when HEAD is detached
    head: str


def list_worktrees(cwd: Path) -> list[Worktree]:
    """Parse `git worktree list --porcelain`. The first entry is the main checkout."""
    entries: list[Worktree] = []
    fields: dict[str, str] = {}
    for line in run_git(["worktree", "list", "--porcelain"], cwd).splitlines() + [""]:
        if line:
            key, _, value = line.partition(" ")
            fields[key] = value
            continue
        if fields:
            branch = fields.get("branch")
            entries.append(
                Worktree(
                    path=Path(fields["worktree"]),
                    branch=branch.removeprefix("refs/heads/") if branch else None,
                    head=fields.get("HEAD", ""),
                )
            )
            fields = {}
    return entries


def main_checkout(cwd: Path) -> Worktree:
    return list_worktrees(cwd)[0]


def current_branch(cwd: Path) -> str | None:
    name = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd).strip()
    return None if name == "HEAD" else name


def git_common_dir(cwd: Path) -> Path:
    out = run_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)
    return Path(out.strip())


def dirty_files(cwd: Path) -> set[str]:
    """Paths with uncommitted changes, including untracked files."""
    tokens = run_git(
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd
    ).split("\0")
    paths: set[str] = set()
    i = 0
    while i < len(tokens):
        entry = tokens[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.add(entry[3:])
        if entry[0] in "RC":  # rename or copy: the next token is the source path
            i += 1
    return paths


def changed_since_merge_base(cwd: Path, base: str, ref: str) -> set[str]:
    """Files `ref` changed since it forked from `base` (git's `base...ref`)."""
    out = run_git(["diff", "--name-only", f"{base}...{ref}"], cwd)
    return {line for line in out.splitlines() if line}


def commit_date(cwd: Path, rev: str) -> str:
    return run_git(["show", "-s", "--format=%cI", rev], cwd).strip()


def is_ancestor(cwd: Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=cwd,
        capture_output=True,
    )
    if proc.returncode in (0, 1):
        return proc.returncode == 0
    raise GitError(proc.stderr.decode(errors="replace").strip())
