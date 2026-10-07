"""Pre-landing checks for an agent branch.

`check` verifies the branch, rebases it onto main, runs the tests for the
changed packages, reports overlaps, and prints a summary. It never merges or
pushes: the user approves each landing by commit SHA (spec decision 1).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from tools.git_workflow import (
    MAIN_BRANCH,
    GitError,
    changed_since_merge_base,
    commit_date,
    current_branch,
    dirty_files,
    is_ancestor,
    list_worktrees,
    main_checkout,
    run_git,
)

PROJECT_SUBDIR = "ai-sandbox/academic-rag-model"


class LandingError(RuntimeError):
    """The branch cannot be landed as it stands; the message says why."""


@dataclass
class CheckResult:
    branch: str
    sha: str
    rebased: bool
    checks: str  # "passed", "failed", or "skipped"
    check_targets: list[str] = field(default_factory=list)
    check_seconds: float = 0.0
    days_since_cut: float = 0.0
    overlaps: list[str] = field(default_factory=list)


def project_relative(paths: set[str], subdir: str) -> set[str]:
    prefix = subdir.rstrip("/") + "/" if subdir else ""
    return {p[len(prefix):] for p in paths if p.startswith(prefix)}


def preflight(worktree: Path) -> str:
    branch = current_branch(worktree)
    if branch is None:
        raise LandingError("HEAD is detached; check out the task branch first")
    if branch == MAIN_BRANCH:
        raise LandingError("this worktree is on main; agent work must be on its own branch")
    dirty = dirty_files(worktree)
    if dirty:
        raise LandingError("worktree has uncommitted changes: " + ", ".join(sorted(dirty)))
    return branch


def rebase_onto_main(worktree: Path) -> bool:
    """Rebase the branch onto main. Returns False if it already contains main."""
    if is_ancestor(worktree, MAIN_BRANCH, "HEAD"):
        return False
    try:
        run_git(["rebase", MAIN_BRANCH], worktree)
    except GitError as exc:
        conflicted = run_git(["diff", "--name-only", "--diff-filter=U"], worktree).split()
        run_git(["rebase", "--abort"], worktree)
        raise LandingError(
            f"rebase onto {MAIN_BRANCH} conflicts in: "
            f"{', '.join(conflicted) or 'unknown files'}; resolve by hand and re-run"
        ) from exc
    return True


def find_overlaps(worktree: Path, branch_changed: set[str]) -> list[str]:
    """Paths the branch changed that the main checkout or another worktree also changes."""
    main = main_checkout(worktree).path
    overlaps = branch_changed & dirty_files(main)
    here = worktree.resolve()
    for wt in list_worktrees(worktree):
        if wt.path.resolve() in (here, main.resolve()) or wt.branch is None:
            continue
        overlaps |= branch_changed & changed_since_merge_base(main, MAIN_BRANCH, wt.branch)
    return sorted(overlaps)


def select_test_targets(changed: set[str], project_root: Path) -> list[str]:
    """Map changed .py files to test directories. Empty means no code changed."""
    targets: set[str] = set()
    for path in changed:
        if not path.endswith(".py"):
            continue
        parts = path.split("/")
        if parts[0] == "tests":
            if (project_root / path).is_file():
                targets.add(path)
        elif (project_root / "tests" / parts[0]).is_dir():
            targets.add(f"tests/{parts[0]}")
    dirs = {t for t in targets if not t.endswith(".py")}
    return sorted(t for t in targets if t in dirs or not any(t.startswith(d + "/") for d in dirs))


def run_checks(project_root: Path, changed: set[str], full: bool) -> tuple[str, list[str], float]:
    code_changed = any(p.endswith(".py") for p in changed)
    if not code_changed and not full:
        return "skipped", [], 0.0
    targets = ["tests/"] if full else select_test_targets(changed, project_root)
    if not targets:
        targets = ["tests/"]  # code changed but no mapped tests: run everything
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "-q"],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    seconds = time.monotonic() - started
    if proc.returncode != 0:
        print(proc.stdout[-4000:])
        return "failed", targets, seconds
    return "passed", targets, seconds


def check(worktree: Path, subdir: str = PROJECT_SUBDIR, full: bool = False) -> CheckResult:
    branch = preflight(worktree)
    cut = run_git(["merge-base", MAIN_BRANCH, "HEAD"], worktree).strip()
    cut_date = datetime.fromisoformat(commit_date(worktree, cut))
    rebased = rebase_onto_main(worktree)
    sha = run_git(["rev-parse", "HEAD"], worktree).strip()
    changed = changed_since_merge_base(worktree, MAIN_BRANCH, "HEAD")
    overlaps = find_overlaps(worktree, changed)
    checks, targets, seconds = run_checks(
        worktree / subdir, project_relative(changed, subdir), full
    )
    age_days = (datetime.now(timezone.utc) - cut_date).total_seconds() / 86400
    return CheckResult(
        branch=branch,
        sha=sha,
        rebased=rebased,
        checks=checks,
        check_targets=targets,
        check_seconds=round(seconds, 1),
        days_since_cut=round(age_days, 1),
        overlaps=overlaps,
    )


def print_summary(r: CheckResult) -> None:
    print(f"Branch:      {r.branch}")
    print(f"Commit SHA:  {r.sha}")
    print(f"Rebased:     {'yes' if r.rebased else 'no (already contains main)'}")
    print(f"Checks:      {r.checks} {r.check_targets} ({r.check_seconds}s)")
    print(f"Branch age:  {r.days_since_cut} days since cut")
    print("Overlaps:    " + (", ".join(r.overlaps) if r.overlaps else "none"))
    print("Nothing has been merged or pushed. Ask the user to approve this SHA.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pre-landing checks for an agent branch.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="rebase, test, and report; never merges")
    p_check.add_argument("--worktree", type=Path, default=Path.cwd())
    p_check.add_argument("--full", action="store_true", help="run the full test suite")
    args = parser.parse_args(argv)
    try:
        result = check(args.worktree.resolve(), full=args.full)
    except (LandingError, GitError) as exc:
        print(f"NOT LANDABLE: {exc}", file=sys.stderr)
        return 1
    print_summary(result)
    return 0 if result.checks in ("passed", "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
