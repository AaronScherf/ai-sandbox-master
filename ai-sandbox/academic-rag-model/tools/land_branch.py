"""Pre-landing checks and approved landings for an agent branch.

`check` verifies the branch, rebases it onto main, runs the tests for the
changed packages, reports overlaps, and prints a summary with the branch's
change ID. It never merges or pushes. The user approves a change ID, and
`land` then rebases, re-checks only what main's movement could affect, and
fast-forwards and pushes main (spec 2026-10-25-landing-approval-by-change-design.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from tools.git_workflow import (
    MAIN_BRANCH,
    GitError,
    changed_since_merge_base,
    commit_date,
    current_branch,
    dirty_files,
    git_common_dir,
    is_ancestor,
    list_worktrees,
    main_checkout,
    run_git,
)
from tools import guard_binaries
from tools.run_tests_chunked import ChunkResult, chunk_failed, run_all

PROJECT_SUBDIR = "ai-sandbox/academic-rag-model"
# Live tests read these outside-project paths: test_lit_gap_report.py reads
# the root .gitignore; test_audit_website_sync.py validates .obsidian targets.
# Files that decide what may land. A branch that edits them is judged by its own edited copy.
GUARD_POLICY_PATHS = (
    "ai-sandbox/academic-rag-model/tools/guard_binaries.py",
    "ai-sandbox/academic-rag-model/tools/guard_binaries_allow.txt",
    "ai-sandbox/academic-rag-model/tools/land_branch.py",
    ".githooks/pre-commit",
)
RETEST_OUTSIDE_PATHS =(".gitignore", "ai-sandbox/.obsidian")


class LandingError(RuntimeError):
    """The branch cannot be landed as it stands; the message says why."""


LOG_NAME = "agent-landing-log.jsonl"
OUTCOMES = ("landed", "declined")


def log_path(worktree: Path) -> Path:
    return git_common_dir(worktree) / LOG_NAME


def append_log(worktree: Path, entry: dict) -> None:
    record_entry = {"at": datetime.now(timezone.utc).isoformat(), **entry}
    with log_path(worktree).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record_entry, sort_keys=True) + "\n")


def record(worktree: Path, sha: str, outcome: str) -> None:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    append_log(worktree, {"event": "outcome", "sha": sha, "outcome": outcome})


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
    change_id: str = ""
    base: str = ""  # the main commit the check ran against
    full: bool = False
    selection_reason: str = ""
    changed_packages: list[str] = field(default_factory=list)
    changed_extensions: list[str] = field(default_factory=list)
    outside_paths: int = 0
    chunk_timings: list[dict] = field(default_factory=list)
    guard: str = "passed"  # binary guard over the branch's added/modified paths
    guard_violations: list[str] = field(default_factory=list)
    guard_policy_changed: list[str] = field(default_factory=list)  # branch edits the guard or the landing tool


def change_id(worktree: Path) -> str:
    """Fingerprint of the branch's diff against its merge-base with main.

    Whitespace-sensitive (unlike `git patch-id`), and blind to `index` and `@@`
    lines, which change when unrelated lines move, so a clean rebase keeps it.
    """
    base = run_git(["merge-base", MAIN_BRANCH, "HEAD"], worktree).strip()
    diff = run_git(
        ["diff", "--no-color", "--no-ext-diff", "--binary", "-U0",
         "--src-prefix=a/", "--dst-prefix=b/", base, "HEAD"],
        worktree,
    )
    kept = [line for line in diff.splitlines() if not line.startswith(("index ", "@@"))]
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()


def project_relative(paths: set[str], subdir: str) -> set[str]:
    prefix = subdir.rstrip("/") + "/" if subdir else ""
    return {p[len(prefix):] for p in paths if p.startswith(prefix)}


def is_published(worktree: Path, branch: str) -> bool:
    """True if a remote-tracking ref for the branch exists (last fetch)."""
    try:
        run_git(["rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch}"], worktree)
    except GitError:
        return False
    return True


def preflight(worktree: Path) -> str:
    branch = current_branch(worktree)
    if branch is None:
        raise LandingError("HEAD is detached; check out the task branch first")
    if branch == MAIN_BRANCH:
        raise LandingError("this worktree is on main; agent work must be on its own branch")
    if is_published(worktree, branch):
        raise LandingError(f"{branch} is already published to origin; rebasing it would rewrite shared history")
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
        conflicted = run_git(["diff", "--name-only", "--diff-filter=U"], worktree).splitlines()
        try:
            run_git(["rebase", "--abort"], worktree)
        except GitError:
            pass  # best effort; the conflict below is the failure to report
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


def _is_documentation_only(changed: set[str]) -> bool:
    """True if every changed path is Markdown -- nothing pytest can read.

    Deliberately an allowlist of exactly one safe extension, not "no .py
    changed": a branch that only touches a dependency pin, a lockfile, a
    pytest/tox config, or a non-.py fixture under tests/ changed no .py file
    either, but could still change what the suite does. Those fall through
    to select_test_targets()/run_checks()'s "no mapped targets -> run
    everything" fallback instead of being treated as skippable here.
    """
    return all(path.endswith(".md") for path in changed)


def select_test_targets(changed: set[str], project_root: Path) -> list[str]:
    """Map changed .py files to test directories. Empty means no code changed."""
    targets: set[str] = set()
    for path in changed:
        if not path.endswith(".py"):
            continue
        parts = path.split("/")
        if parts[0] == "tests":
            name = Path(path).name
            if name.startswith("test_") and (project_root / path).is_file():
                targets.add(path)
            elif len(parts) > 1 and (project_root / "tests" / parts[1]).is_dir():
                # a non-test file under tests/ (a fixture or helper): run its
                # directory instead of the bare file, which pytest would
                # otherwise collect zero tests from and report as a failure.
                targets.add(f"tests/{parts[1]}")
            elif (project_root / "tests").is_dir():
                targets.add("tests/")  # top-level helper (e.g. conftest.py): run everything
        elif (project_root / "tests" / parts[0]).is_dir():
            targets.add(f"tests/{parts[0]}")
    dirs = {t for t in targets if not t.endswith(".py")}
    return sorted(t for t in targets if t in dirs or not any(t.startswith(d + "/") for d in dirs))


def selection_reason(
    changed: set[str], project_root: Path, full: bool = False,
    outside: set[str] | None = None,
) -> str:
    outside = outside or set()
    if full:
        return "explicit_full"
    if _is_documentation_only(changed | outside):
        return "doc_only"
    if any(Path(p).suffix not in (".py", ".md") for p in outside):
        return "non_py_file"
    if any(p.endswith(".py") for p in outside):
        return "unmapped_file"
    if any(p.startswith("core/") for p in changed):
        return "core_change"
    if any(Path(p).suffix not in (".py", ".md") for p in changed):
        return "non_py_file"
    if any(p in ("conftest.py", "tests/conftest.py") or
           (p.startswith("tests/") and p.count("/") == 1 and
            not Path(p).name.startswith("test_")) for p in changed):
        return "helper_change"
    if not select_test_targets(changed, project_root) or any(
        p.endswith(".py") and p.split("/")[0] != "tests" and
        not (project_root / "tests" / p.split("/")[0]).is_dir()
        for p in changed
    ):
        return "unmapped_file"
    packages = {p.split("/")[1] if p.startswith("tests/") and "/" in p[6:]
                else p.split("/")[0] for p in changed if p.endswith(".py")}
    return "targeted_multi" if len(packages) > 1 else "targeted"


def run_checks(
    project_root: Path, changed: set[str], full: bool,
    *, outside: set[str] | None = None, chunk_results: list[ChunkResult] | None = None,
    reason: str | None = None, selected_targets: list[str] | None = None,
) -> tuple[str, list[str], float]:
    if reason is None:
        reason = selection_reason(changed, project_root, full, outside)
    if reason == "doc_only":
        return "skipped", [], 0.0
    targets = (["tests/"] if reason not in ("targeted", "targeted_multi", "multi_package")
               else list(selected_targets) if selected_targets is not None
               else select_test_targets(changed, project_root))
    if not targets:
        targets = ["tests/"]  # code changed but no mapped tests: run everything
    if targets == ["tests/"]:
        # Whether this is an explicit --full run or a fallback that maps to
        # "run everything" (no mapped targets, or a top-level tests/ helper
        # changed): both would otherwise run as one long-lived `pytest
        # tests/ -q` process, which is the OOM this chunked runner exists
        # to avoid (spec: docs/superpowers/specs/2026-10-16-test-suite-memory.md).
        status, results, seconds = run_all(project_root)
        if chunk_results is not None:
            chunk_results.extend(results)
        targets = [f"tests/{r.name}" for r in results]
        for r in results:
            if chunk_failed(r.returncode):
                print(f"[FAILED] tests/{r.name}")
                print(r.stdout[-4000:])
        return status, targets, seconds
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
    if chunk_results is not None:
        chunk_results.append(ChunkResult(
            name=", ".join(targets), returncode=proc.returncode,
            seconds=seconds, stdout="",
        ))
    if proc.returncode != 0:
        print(proc.stdout[-4000:])
        return "failed", targets, seconds
    return "passed", targets, seconds


def check(worktree: Path, subdir: str = PROJECT_SUBDIR, full: bool = False) -> CheckResult:
    # Any folder inside the worktree works; subdir is always relative to the root.
    worktree = Path(run_git(["rev-parse", "--show-toplevel"], worktree).strip())
    try:
        result = _run_check(worktree, subdir, full)
    except LandingError as exc:
        append_log(worktree, {"event": "refused", "reason": str(exc)})
        raise
    append_log(worktree, {"event": "check", **asdict(result)})
    return result


def _run_check(worktree: Path, subdir: str, full: bool) -> CheckResult:
    branch = preflight(worktree)
    cut = run_git(["merge-base", MAIN_BRANCH, "HEAD"], worktree).strip()
    cut_date = datetime.fromisoformat(commit_date(worktree, cut))
    rebased = rebase_onto_main(worktree)
    sha = run_git(["rev-parse", "HEAD"], worktree).strip()
    changed = changed_since_merge_base(worktree, MAIN_BRANCH, "HEAD")
    guard_violations = [str(v) for v in guard_binaries.check_range(worktree, MAIN_BRANCH)]
    policy_changed = sorted(changed & set(GUARD_POLICY_PATHS))
    overlaps = find_overlaps(worktree, changed)
    relative = project_relative(changed, subdir)
    prefix = subdir.rstrip("/") + "/" if subdir else ""
    outside = {p for p in changed if not p.startswith(prefix)}
    reason = selection_reason(relative, worktree / subdir, full, outside)
    chunks: list[ChunkResult] = []
    checks, targets, seconds = run_checks(
        worktree / subdir, relative, full, outside=outside, chunk_results=chunks,
        reason=reason,
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
        change_id=change_id(worktree),
        base=run_git(["rev-parse", MAIN_BRANCH], worktree).strip(),
        full=full,
        selection_reason=reason,
        changed_packages=sorted({p.split("/")[0] for p in relative if "/" in p}),
        changed_extensions=sorted({Path(p).suffix for p in changed}),
        outside_paths=len(outside),
        chunk_timings=[{"name": r.name, "returncode": r.returncode, "seconds": r.seconds}
                       for r in chunks],
        guard="failed" if guard_violations else "passed",
        guard_violations=guard_violations,
        guard_policy_changed=policy_changed,
    )


def print_summary(r: CheckResult) -> None:
    print(f"Branch:      {r.branch}")
    print(f"Commit SHA:  {r.sha}")
    print(f"Change ID:   {r.change_id}")
    print(f"Base:        {r.base}")
    print(f"Rebased:     {'yes' if r.rebased else 'no (already contains main)'}")
    print(f"Checks:      {r.checks} {r.check_targets} ({r.check_seconds}s)")
    print(f"Branch age:  {r.days_since_cut} days since cut")
    print("Overlaps:    " + (", ".join(r.overlaps) if r.overlaps else "none"))
    print(f"Guard:       {r.guard}")
    for violation in r.guard_violations:
        print(f"  {violation}")
    if r.guard_policy_changed:
        # This branch runs its own copy of the guard, so read these changes before approving.
        print("GUARD POLICY CHANGED -- review before approving: " + ", ".join(r.guard_policy_changed))
    print(f"Nothing has been merged or pushed. Ask the user to approve change {r.change_id}.")


# A test re-run follows any code commit on main, so cap those retries; retries
# caused only by Markdown commits are unlimited apart from this loop guard.
MAX_RETEST_ATTEMPTS = 3
MAX_ATTEMPTS = 20


@dataclass
class LandResult:
    branch: str
    sha: str
    change_id: str
    attempts: int
    retested: bool
    retest_chunk_timings: list[dict] = field(default_factory=list)


def approved_check(worktree: Path, branch: str, cid: str) -> dict:
    """The strongest passing check for this branch and change ID; newest wins ties."""
    path = log_path(worktree)
    entries = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    best: dict | None = None
    best_rank = -1
    for line in reversed(entries):
        entry = json.loads(line)
        if (entry.get("event") == "check" and entry.get("branch") == branch
                and entry.get("change_id") == cid and entry.get("checks") in ("passed", "skipped")):
            reason = entry.get("selection_reason") or entry.get("full_reason")
            rank = (3 if entry.get("full") or reason == "explicit_full" else
                    2 if reason in {"core_change", "non_py_file", "unmapped_file", "helper_change"} else
                    1 if entry["checks"] == "passed" else 0)
            if rank > best_rank:
                best, best_rank = entry, rank
    if best is not None:
        return best
    raise LandingError(f"no passing check for change {cid} on {branch}; run check and ask again")


def _ff_main(main_path: Path, branch: str) -> bool:
    """Fast-forward main to the branch. False if main moved and no longer allows it."""
    try:
        run_git(["merge", "--ff-only", branch], main_path)
    except GitError:
        if not is_ancestor(main_path, MAIN_BRANCH, branch):
            return False
        raise
    return True


def _files_between(cwd: Path, old: str, new: str) -> set[str]:
    out = run_git(["diff", "--no-renames", "--name-only", old, new], cwd)
    return {line for line in out.splitlines() if line}


def land(worktree: Path, cid: str, subdir: str = PROJECT_SUBDIR) -> LandResult:
    worktree = Path(run_git(["rev-parse", "--show-toplevel"], worktree).strip())
    branch = current_branch(worktree) or ""
    try:
        result = _run_land(worktree, cid, subdir)
    except (LandingError, GitError) as exc:
        append_log(worktree, {"event": "land", "branch": branch, "change_id": cid, "result": str(exc)})
        raise LandingError(str(exc)) from exc
    append_log(worktree, {"event": "land", "result": "landed", **asdict(result)})
    append_log(worktree, {"event": "outcome", "sha": result.sha, "outcome": "landed"})
    return result


def _run_land(worktree: Path, cid: str, subdir: str) -> LandResult:
    branch = preflight(worktree)
    approved = approved_check(worktree, branch, cid)
    main_path = main_checkout(worktree).path
    if current_branch(main_path) != MAIN_BRANCH:
        raise LandingError("the main checkout is not on main; never land onto another branch")
    tested_base = approved["base"]
    retests = 0
    retest_chunks: list[ChunkResult] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        rebase_onto_main(worktree)
        if change_id(worktree) != cid:
            raise LandingError(f"the change differs from approved change {cid}; ask again")
        branch_files = changed_since_merge_base(worktree, MAIN_BRANCH, "HEAD")
        main_now = run_git(["rev-parse", MAIN_BRANCH], worktree).strip()
        touched = sorted(branch_files & _files_between(worktree, approved["base"], main_now))
        if touched:
            raise LandingError("main changed files this branch also changes: " + ", ".join(touched))
        main_changed = _files_between(worktree, tested_base, main_now)
        code_delta = [p for p in project_relative(main_changed, subdir)
                      if not p.endswith(".md")]
        code_delta.extend(p for p in main_changed if any(
            p == target or p.startswith(target + "/") for target in RETEST_OUTSIDE_PATHS))
        if code_delta and approved["checks"] != "skipped":
            retests += 1
            if retests > MAX_RETEST_ATTEMPTS:
                raise LandingError(f"main kept moving: {MAX_RETEST_ATTEMPTS} test re-runs without landing")
            prefix = subdir.rstrip("/") + "/" if subdir else ""
            status, _, _ = run_checks(
                worktree / subdir, project_relative(branch_files, subdir),
                approved.get("full", False),
                outside={p for p in branch_files if not p.startswith(prefix)},
                reason=approved.get("selection_reason") or approved.get("full_reason"),
                selected_targets=(approved.get("check_targets") if
                                  approved.get("selection_reason") or approved.get("full_reason")
                                  else None),
                chunk_results=retest_chunks,
            )
            if status not in ("passed", "skipped"):
                raise LandingError("tests failed after rebasing onto the new main")
            tested_base = main_now
        violations = guard_binaries.check_range(worktree, MAIN_BRANCH)
        if violations:
            raise LandingError(
                "binary guard refused the landing:\n  " + "\n  ".join(map(str, violations)))
        overlaps = find_overlaps(worktree, branch_files)
        if overlaps:
            raise LandingError("overlaps with uncommitted or in-progress work: " + ", ".join(overlaps))
        sha = run_git(["rev-parse", "HEAD"], worktree).strip()
        if not _ff_main(main_path, branch):
            continue
        try:
            run_git(["push", "origin", MAIN_BRANCH], main_path)
        except GitError as exc:
            raise LandingError(f"main was fast-forwarded locally to {sha} but the push failed: {exc}") from exc
        return LandResult(
            branch=branch, sha=sha, change_id=cid, attempts=attempt,
            retested=retests > 0,
            retest_chunk_timings=[{"name": r.name, "returncode": r.returncode, "seconds": r.seconds}
                                  for r in retest_chunks],
        )
    raise LandingError(f"main kept moving: no landing after {MAX_ATTEMPTS} attempts")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pre-landing checks for an agent branch.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="rebase, test, and report; never merges")
    p_check.add_argument("--worktree", type=Path, default=Path.cwd())
    p_check.add_argument("--full", action="store_true", help="run the full test suite")
    p_rec = sub.add_parser("record", help="log the user's answer for a SHA")
    p_rec.add_argument("--worktree", type=Path, default=Path.cwd())
    p_rec.add_argument("--sha", required=True)
    p_rec.add_argument("--outcome", required=True, choices=OUTCOMES)
    p_land = sub.add_parser("land", help="land a change the user approved; merges and pushes main")
    p_land.add_argument("--worktree", type=Path, default=Path.cwd())
    p_land.add_argument("--change-id", required=True)
    p_land.add_argument("--subdir", default=PROJECT_SUBDIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.cmd == "record":
        record(args.worktree.resolve(), args.sha, args.outcome)
        return 0
    if args.cmd == "land":
        try:
            landed = land(args.worktree.resolve(), args.change_id, subdir=args.subdir)
        except LandingError as exc:
            print(f"STOP: {exc}", file=sys.stderr)
            return 1
        print(f"LANDED {landed.sha} ({landed.attempts} attempt(s), "
              f"{'re-tested' if landed.retested else 'no re-test'})")
        return 0
    try:
        result = check(args.worktree.resolve(), full=args.full)
    except (LandingError, GitError) as exc:
        print(f"NOT LANDABLE: {exc}", file=sys.stderr)
        return 1
    print_summary(result)
    return 0 if result.checks in ("passed", "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
