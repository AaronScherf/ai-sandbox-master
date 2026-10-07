# Agent Git Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give agents a checked, repeatable path from a finished task branch to a user-approved landing on `main`, and a read-only report of open worktrees, without letting agents merge or push on their own.

**Architecture:** Three small tools under `tools/` in the academic-rag-model package, sharing one git helper module. `land_branch.py check` runs the pre-landing steps (preflight, rebase onto `main`, tests for the changed packages, overlap report) and prints a summary. It never merges or pushes. `land_branch.py record` writes the user's answer to an append-only landing log kept in the shared git directory, outside the working tree. `active_work.py` reports open worktrees, overlaps, and retirement candidates, read-only. Then the workflow doc is updated to match.

**Tech Stack:** Python 3.13 standard library (`subprocess`, `argparse`, `dataclasses`, `json`, `unittest`), git 2.31+ (`--path-format=absolute`), pytest for the test runner. No new dependencies in this plan.

**Spec:** `docs/superpowers/specs/2026-10-06-agent-git-workflow-design.md` (approved 2026-10-06, commit `0bd8e38`). This plan implements its section 3 (landing flow), section 5 items 1 to 5, and the docs changes in section 2.

## Global Constraints

- Never `git add -A` or `git add .`. Stage explicit paths only, and inspect `git diff --cached` before each commit.
- Never print or commit `ai-sandbox/.env`.
- No `git push --force`, `git reset --hard`, or `git clean` anywhere in the tools or in the implementation steps.
- The landing tool never runs `git merge` or `git push`. Only the user's approval, relayed by the agent, triggers those.
- The tools never remove a worktree or branch, and never write to another worktree.
- Run tools and tests with the project venv: `.venv\Scripts\python.exe` from `ai-sandbox/academic-rag-model/`.
- Commit messages end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- Work happens only in `.worktrees/claude-agent-git-workflow` on branch `claude/agent-git-workflow-design`.
- Tests use temporary git repositories. No test touches the real monorepo's refs, worktrees, or `.git` directory.
- The new tools live in `academic-rag-model/tools/` and their tests in `academic-rag-model/tests/tools/`, matching the existing `audit_metadata.py` and `reconcile_needs_manual.py`.

## Review Focus

1. A rebase conflict leaves the worktree half-rebased and the branch rewritten. Expected: the rebase is aborted, the branch SHA is unchanged, the worktree is clean, and the conflicting files are named. (Task 2)
2. The check runs on `main` or on a detached HEAD, or with uncommitted changes. Expected: refused with a clear reason, and no rebase or test run. (Task 2)
3. The overlap check compares against the merge-base, so a file that only `main` changed after the branch was cut is not reported as the branch's overlap. Expected: only paths the branch itself changed are compared. (Task 2)
4. Tests fail, or no test is mapped to a code change. Expected: exit code 1 for failed tests; for an unmapped code change, the full suite runs instead of passing silently. (Task 2)
5. Git paths are monorepo-relative and the tool runs inside a subproject. Expected: only paths under `ai-sandbox/academic-rag-model/` are mapped to tests, and `core.quotePath` is off so non-ASCII filenames are not quoted. (Tasks 1 and 2)

---

### Task 1: Shared git helpers

**Files:**
- Create: `tools/git_workflow.py`
- Create: `tests/tools/git_fixture.py`
- Create: `tests/tools/test_git_workflow.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces (used by Tasks 2 to 4):
  - `MAIN_BRANCH: str = "main"`
  - `class GitError(RuntimeError)`
  - `run_git(args: list[str], cwd: Path) -> str`
  - `@dataclass(frozen=True) class Worktree: path: Path; branch: str | None; head: str`
  - `list_worktrees(cwd: Path) -> list[Worktree]` (first entry is the main checkout)
  - `main_checkout(cwd: Path) -> Worktree`
  - `current_branch(cwd: Path) -> str | None` (None when detached)
  - `git_common_dir(cwd: Path) -> Path`
  - `dirty_files(cwd: Path) -> set[str]`
  - `changed_since_merge_base(cwd: Path, base: str, ref: str) -> set[str]`
  - `commit_date(cwd: Path, rev: str) -> str` (ISO 8601)
  - `is_ancestor(cwd: Path, ancestor: str, descendant: str) -> bool`

- [ ] **Step 1: Check whether the test folder is a package**

Use Glob for `tests/tools/__init__.py`. If it exists, import helpers as `from tests.tools.git_fixture import ...`. If not, import them as `from git_fixture import ...`. Use the same import style in every test file of this plan.

- [ ] **Step 2: Write the test fixture**

Create `tests/tools/git_fixture.py`:

```python
import subprocess
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def write_and_commit(root: Path, files: dict[str, str], message: str) -> None:
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        git(root, "add", rel)
    git(root, "commit", "-q", "-m", message)


def make_repo(root: Path) -> Path:
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    write_and_commit(root, {"core/a.py": "x = 1\n"}, "init")
    return root
```

- [ ] **Step 3: Write the failing tests**

Create `tests/tools/test_git_workflow.py`:

```python
import tempfile
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.git_workflow import (
    changed_since_merge_base,
    current_branch,
    dirty_files,
    list_worktrees,
    main_checkout,
)


class GitWorkflowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_worktrees_reports_branch_and_detached(self):
        wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(wt), "main")
        detached = self.tmp / "det"
        git(self.repo, "worktree", "add", "-q", "--detach", str(detached), "main")
        entries = list_worktrees(self.repo)
        self.assertEqual(entries[0].branch, "main")
        self.assertEqual(main_checkout(wt).path.resolve(), self.repo.resolve())
        branches = {e.path.resolve(): e.branch for e in entries}
        self.assertEqual(branches[wt.resolve()], "claude/t")
        self.assertIsNone(branches[detached.resolve()])

    def test_current_branch_none_when_detached(self):
        git(self.repo, "checkout", "-q", "--detach")
        self.assertIsNone(current_branch(self.repo))

    def test_dirty_files_lists_untracked_and_renamed_paths(self):
        (self.repo / "core" / "new file.py").write_text("y = 2\n", encoding="utf-8")
        git(self.repo, "mv", "core/a.py", "core/renamed.py")
        self.assertEqual(
            dirty_files(self.repo),
            {"core/new file.py", "core/renamed.py"},
        )

    def test_changed_since_merge_base_ignores_main_only_changes(self):
        wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(wt), "main")
        write_and_commit(wt, {"core/branch.py": "b = 1\n"}, "branch work")
        write_and_commit(self.repo, {"core/main_only.py": "m = 1\n"}, "main work")
        self.assertEqual(
            changed_since_merge_base(self.repo, "main", "claude/t"),
            {"core/branch.py"},
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_git_workflow.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.git_workflow'`.

- [ ] **Step 5: Write the minimal implementation**

Create `tools/git_workflow.py`:

```python
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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_git_workflow.py -q`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add tools/git_workflow.py tests/tools/git_fixture.py tests/tools/test_git_workflow.py
git diff --cached --stat
git commit -m "Add shared git helpers for agent landing tools

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

Paths above are relative to `ai-sandbox/academic-rag-model/`. Run the git commands from that directory, or prefix the paths with it.

---

### Task 2: Landing check (`land_branch.py check`)

**Files:**
- Create: `tools/land_branch.py`
- Create: `tests/tools/test_land_branch.py`

**Interfaces:**
- Consumes (from Task 1): `MAIN_BRANCH`, `GitError`, `run_git`, `current_branch`, `dirty_files`, `list_worktrees`, `main_checkout`, `changed_since_merge_base`, `commit_date`, `is_ancestor`.
- Produces (used by Task 3):
  - `PROJECT_SUBDIR: str = "ai-sandbox/academic-rag-model"`
  - `class LandingError(RuntimeError)`
  - `@dataclass class CheckResult: branch: str; sha: str; rebased: bool; checks: str; check_targets: list[str]; check_seconds: float; days_since_cut: float; overlaps: list[str]` (`checks` is `"passed"`, `"failed"`, or `"skipped"`)
  - `check(worktree: Path, subdir: str = PROJECT_SUBDIR, full: bool = False) -> CheckResult`
  - `preflight(worktree: Path) -> str` (returns the branch name)
  - `rebase_onto_main(worktree: Path) -> bool` (True if rebased)
  - `find_overlaps(worktree: Path, branch_changed: set[str]) -> list[str]`
  - `run_checks(project_root: Path, changed: set[str], full: bool) -> tuple[str, list[str], float]`
  - `select_test_targets(changed: set[str], project_root: Path) -> list[str]`
  - `project_relative(paths: set[str], subdir: str) -> set[str]`
  - `main(argv: list[str] | None = None) -> int` (`check` subcommand only in this task)

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_land_branch.py`:

```python
import tempfile
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.git_workflow import dirty_files
from tools.land_branch import (
    LandingError,
    check,
    find_overlaps,
    preflight,
    project_relative,
    rebase_onto_main,
    select_test_targets,
)


class LandBranchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")
        self.wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(self.wt), "main")

    def tearDown(self):
        self._tmp.cleanup()

    def test_preflight_refuses_main(self):
        with self.assertRaisesRegex(LandingError, "on main"):
            preflight(self.repo)

    def test_preflight_refuses_detached_head(self):
        git(self.wt, "checkout", "-q", "--detach")
        with self.assertRaisesRegex(LandingError, "detached"):
            preflight(self.wt)

    def test_preflight_refuses_dirty_worktree(self):
        (self.wt / "scratch.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(LandingError, "uncommitted"):
            preflight(self.wt)

    def test_rebase_is_noop_when_branch_already_has_main(self):
        self.assertFalse(rebase_onto_main(self.wt))

    def test_rebase_onto_moved_main_changes_sha(self):
        write_and_commit(self.wt, {"core/branch.py": "b = 1\n"}, "branch work")
        write_and_commit(self.repo, {"core/other.py": "o = 1\n"}, "main work")
        before = git(self.wt, "rev-parse", "HEAD").strip()
        self.assertTrue(rebase_onto_main(self.wt))
        self.assertNotEqual(git(self.wt, "rev-parse", "HEAD").strip(), before)

    def test_conflicting_rebase_is_aborted_and_named(self):
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        write_and_commit(self.repo, {"core/a.py": "x = 3\n"}, "main edit")
        before = git(self.wt, "rev-parse", "HEAD").strip()
        with self.assertRaises(LandingError) as ctx:
            rebase_onto_main(self.wt)
        self.assertIn("core/a.py", str(ctx.exception))
        self.assertEqual(git(self.wt, "rev-parse", "HEAD").strip(), before)
        self.assertEqual(dirty_files(self.wt), set())

    def test_overlap_ignores_paths_only_main_changed(self):
        write_and_commit(self.wt, {"core/branch.py": "b = 1\n"}, "branch work")
        write_and_commit(self.repo, {"core/main_only.py": "m = 1\n"}, "main work")
        self.assertEqual(find_overlaps(self.wt, {"core/branch.py"}), [])

    def test_overlap_reports_uncommitted_main_checkout_edit(self):
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        (self.repo / "core" / "a.py").write_text("x = 9\n", encoding="utf-8")
        self.assertEqual(find_overlaps(self.wt, {"core/a.py"}), ["core/a.py"])

    def test_test_targets_maps_changed_packages(self):
        (self.repo / "tests" / "core").mkdir(parents=True)
        (self.repo / "tests" / "core" / "test_x.py").write_text("", encoding="utf-8")
        self.assertEqual(
            select_test_targets({"core/a.py", "docs/readme.md"}, self.repo),
            ["tests/core"],
        )

    def test_project_relative_strips_subproject_prefix(self):
        self.assertEqual(
            project_relative({"ai-sandbox/academic-rag-model/core/a.py", "docs/x.md"},
                             "ai-sandbox/academic-rag-model"),
            {"core/a.py"},
        )

    def test_check_passes_with_passing_mapped_tests(self):
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        write_and_commit(self.wt, {"tests/core/test_ok.py": "def test_ok():\n    assert True\n"}, "add test")
        result = check(self.wt, subdir="")
        self.assertEqual(result.checks, "passed")
        self.assertEqual(result.check_targets, ["tests/core"])
        self.assertEqual(result.branch, "claude/t")

    def test_check_fails_with_failing_test(self):
        write_and_commit(self.wt, {"tests/core/test_bad.py": "def test_bad():\n    assert False\n"}, "add bad test")
        result = check(self.wt, subdir="")
        self.assertEqual(result.checks, "failed")

    def test_check_skips_docs_only_branch(self):
        write_and_commit(self.wt, {"docs/note.md": "hi\n"}, "docs only")
        result = check(self.wt, subdir="")
        self.assertEqual(result.checks, "skipped")
        self.assertEqual(result.check_targets, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_land_branch.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.land_branch'`.

- [ ] **Step 3: Write the implementation**

Create `tools/land_branch.py`:

```python
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
    return sorted(targets)


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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_land_branch.py -q`
Expected: 13 passed. The `check` tests are slower because each one runs a nested pytest (about 1 to 3 s each); that is expected.

- [ ] **Step 5: Confirm the CLI prints a summary and exits non-zero on a refused branch**

From inside the worktree's `ai-sandbox/academic-rag-model/` folder, run `.venv\Scripts\python.exe -m tools.land_branch check`.
Expected: a `NOT LANDABLE` message on stderr if the worktree is on `main` or has uncommitted changes, exit code 1. Do not run it on the main checkout.

- [ ] **Step 6: Commit**

```bash
git add tools/land_branch.py tests/tools/test_land_branch.py
git diff --cached --stat
git commit -m "Add landing check: preflight, rebase, tests, overlap report

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Landing log and `record` subcommand

**Files:**
- Modify: `tools/land_branch.py`
- Modify: `tests/tools/test_land_branch.py`

**Interfaces:**
- Consumes (from Task 2): `check`, `CheckResult`, `LandingError`, `GitError`, `main`.
- Produces: `LOG_NAME = "agent-landing-log.jsonl"`, `log_path(worktree: Path) -> Path`, `append_log(worktree: Path, entry: dict) -> None`, `record(worktree: Path, sha: str, outcome: str) -> None`. The `check` subcommand logs its result or refusal; `record` logs the user's answer.

Log location decision: the log sits in the shared git directory (`git rev-parse --git-common-dir`), so it's visible to every worktree, is never committed, and never appears in `git status`. Each line is one JSON object.

- [ ] **Step 1: Write the failing tests**

Append to `tests/tools/test_land_branch.py`, before the `if __name__` block:

```python
class LandingLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")
        self.wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(self.wt), "main")

    def tearDown(self):
        self._tmp.cleanup()

    def _entries(self):
        import json
        from tools.land_branch import log_path
        return [json.loads(line) for line in log_path(self.wt).read_text(encoding="utf-8").splitlines()]

    def test_log_lives_in_shared_git_dir(self):
        from tools.land_branch import log_path
        from tools.git_workflow import git_common_dir
        self.assertEqual(log_path(self.wt).parent.resolve(), git_common_dir(self.wt).resolve())

    def test_refused_check_is_logged_then_raised(self):
        from tools.land_branch import LandingError, check
        (self.wt / "scratch.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(LandingError):
            check(self.wt, subdir="")
        entries = self._entries()
        self.assertEqual(entries[-1]["event"], "refused")
        self.assertIn("uncommitted", entries[-1]["reason"])

    def test_successful_check_is_logged(self):
        from tools.land_branch import check
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        check(self.wt, subdir="")
        entry = self._entries()[-1]
        self.assertEqual(entry["event"], "check")
        self.assertEqual(entry["branch"], "claude/t")
        self.assertIn("rebased", entry)
        self.assertIn("check_seconds", entry)

    def test_record_writes_outcome_for_sha(self):
        from tools.land_branch import record
        record(self.wt, "abc123", "landed")
        entry = self._entries()[-1]
        self.assertEqual(entry["event"], "outcome")
        self.assertEqual(entry["sha"], "abc123")
        self.assertEqual(entry["outcome"], "landed")

    def test_record_rejects_unknown_outcome(self):
        from tools.land_branch import record
        with self.assertRaises(ValueError):
            record(self.wt, "abc123", "merged")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_land_branch.py -q -k Log`
Expected: FAIL with `ImportError` for `log_path` / `record`.

- [ ] **Step 3: Write the implementation**

In `tools/land_branch.py`:

1. Add to the imports: `import json` at the top, and `from dataclasses import asdict, dataclass, field`. Add `git_common_dir` to the `tools.git_workflow` import list.
2. Add after the `LandingError` class:

```python
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
```

3. Replace the body of `check()` so it logs both results and refusals. Keep the existing logic, wrapped:

```python
def check(worktree: Path, subdir: str = PROJECT_SUBDIR, full: bool = False) -> CheckResult:
    try:
        result = _run_check(worktree, subdir, full)
    except LandingError as exc:
        append_log(worktree, {"event": "refused", "reason": str(exc)})
        raise
    append_log(worktree, {"event": "check", **asdict(result)})
    return result
```

Rename the old `check` function body to `_run_check` with the same signature. Its code stays unchanged.

4. In `main()`, add the `record` subcommand:

```python
    p_rec = sub.add_parser("record", help="log the user's answer for a SHA")
    p_rec.add_argument("--worktree", type=Path, default=Path.cwd())
    p_rec.add_argument("--sha", required=True)
    p_rec.add_argument("--outcome", required=True, choices=OUTCOMES)
```

Then, after `args = parser.parse_args(argv)`, handle it before the `check` path:

```python
    if args.cmd == "record":
        record(args.worktree.resolve(), args.sha, args.outcome)
        return 0
```

- [ ] **Step 4: Run all landing tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_land_branch.py tests/tools/test_git_workflow.py -q`
Expected: all pass (17 from Tasks 1 and 2 plus 5 new).

- [ ] **Step 5: Commit**

```bash
git add tools/land_branch.py tests/tools/test_land_branch.py
git diff --cached --stat
git commit -m "Log landing checks, refusals, and user outcomes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Active-work report (`active_work.py`)

**Files:**
- Create: `tools/active_work.py`
- Create: `tests/tools/test_active_work.py`

**Interfaces:**
- Consumes (from Task 1): `MAIN_BRANCH`, `list_worktrees`, `main_checkout`, `dirty_files`, `changed_since_merge_base`, `is_ancestor`.
- Produces: `build_report(cwd: Path) -> list[str]`, `main(argv: list[str] | None = None) -> int`.

This is read-only. It never removes a worktree and never runs `git merge` or `git push`. It covers spec items 3 and 4 in section 5. The "live vault" line is printed for reference only.

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_active_work.py`:

```python
import tempfile
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.active_work import build_report


class ActiveWorkTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")

    def tearDown(self):
        self._tmp.cleanup()

    def test_flags_merged_branch_as_retirement_candidate(self):
        wt = self.tmp / "merged"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/done", str(wt), "main")
        report = "\n".join(build_report(self.repo))
        self.assertIn("claude/done", report)
        self.assertIn("retirement candidate", report)

    def test_flags_overlap_between_two_branches(self):
        a = self.tmp / "a"
        b = self.tmp / "b"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/a", str(a), "main")
        git(self.repo, "worktree", "add", "-q", "-b", "codex/b", str(b), "main")
        write_and_commit(a, {"core/a.py": "x = 2\n"}, "a edit")
        write_and_commit(b, {"core/a.py": "x = 3\n"}, "b edit")
        report = "\n".join(build_report(self.repo))
        self.assertIn("OVERLAP claude/a <-> codex/b: core/a.py", report)

    def test_flags_overlap_with_main_checkout_edit(self):
        a = self.tmp / "a"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/a", str(a), "main")
        write_and_commit(a, {"core/a.py": "x = 2\n"}, "a edit")
        (self.repo / "core" / "a.py").write_text("x = 9\n", encoding="utf-8")
        report = "\n".join(build_report(self.repo))
        self.assertIn("OVERLAP claude/a <-> main checkout uncommitted: core/a.py", report)

    def test_reports_nothing_to_flag_for_clean_repo(self):
        report = "\n".join(build_report(self.repo))
        self.assertIn("no open worktrees", report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_active_work.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.active_work'`.

- [ ] **Step 3: Write the implementation**

Create `tools/active_work.py`:

```python
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
        if is_ancestor(main.path, wt.branch, MAIN_BRANCH):
            lines.append(f"{wt.branch} ({wt.path}): merged into main; retirement candidate")
            continue
        changed = changed_since_merge_base(main.path, MAIN_BRANCH, wt.branch)
        changes[wt.branch] = changed
        lines.append(f"{wt.branch} ({wt.path}): {len(changed)} files vs main")
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_active_work.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/active_work.py tests/tools/test_active_work.py
git diff --cached --stat
git commit -m "Add read-only active-work report for agent worktrees

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Update the workflow doc

**Files:**
- Modify: `docs/WORKTREE_WORKFLOW.md` (repo root, not the academic-rag-model folder)

**Interfaces:**
- Consumes: the decisions in spec section 2 and the tools from Tasks 2 to 4.
- Produces: the policy text that agents read.

Changes take effect only for sessions told to re-read the doc (spec section 8). After committing, notify running sessions to re-read it.

- [ ] **Step 1: Read the current "Integrate one task at a time" section**

Read lines 98 to 118 of `docs/WORKTREE_WORKFLOW.md`. Do not read the whole file.

- [ ] **Step 2: Replace that section**

Replace the whole section from `## Integrate one task at a time` through the paragraph ending "...within the user's authorized scope." with:

```markdown
## Integrate one task at a time

Only the user lands work on `main`. Agents never merge into or push to `main`
on their own. When a task branch is finished, the agent:

1. Runs the landing check from its worktree, with the project venv:
   `.venv\Scripts\python.exe -m tools.land_branch check` (run from
   `ai-sandbox/academic-rag-model/`). The check verifies the branch is clean and
   not on `main`, rebases it onto `main`, runs the tests for the changed
   packages, and reports overlaps. It never merges or pushes.
2. Asks the user in one message: may I commit this branch, and may I merge and
   push commit `<SHA>` to `main`? The message includes the branch, SHA, changed
   paths, check result, overlaps, and known risks.
3. On a yes, merges with fast-forward only, in the main checkout, and only if
   that checkout's `git status --short` is unchanged:

   ```powershell
   git merge --ff-only <branch>
   git push
   ```

   Then verify with `git log -1`.
4. Records the answer: `.venv\Scripts\python.exe -m tools.land_branch record --sha <SHA> --outcome landed|declined`.

Approval covers one commit SHA. If the SHA changes, including after a rebase,
ask again. Approval does not carry over to other sessions or branches.

Merge style is rebase onto `main`, then `--ff-only`. Do not use `--no-ff`
merges. Rebasing is allowed only on a branch that is exclusively owned and not
published.

Before a landing, `.venv\Scripts\python.exe -m tools.active_work` shows
overlaps with other open worktrees and with the main checkout's uncommitted
files. Review any overlap with the user before asking to land.

Review combined behavior even if Git finds no textual conflicts. Preserve both
tasks' intent when resolving conflicts; send design ambiguities to Claude
instead of blindly accepting ours or theirs. A PR is a useful review boundary
when publishing is part of the task. Push or deploy only within the user's
authorized scope.
```

- [ ] **Step 3: Update the docs lane rule**

In the section that lists direct-to-main exceptions (search with Grep for "exempt" or "tracker" in `docs/WORKTREE_WORKFLOW.md`), add:

```markdown
Docs under `ai-sandbox/academic-rag-model/docs/status/` and
`docs/superpowers/`, and package READMEs, may go direct to `main` with explicit
paths, only when no other session has uncommitted changes to that file. Shared
logs are append-only. Any other path goes through a branch.
```

If no such section exists, add this paragraph at the end of "Integrate one task at a time".

- [ ] **Step 4: Check the doc has no stale references**

Run Grep for `no-ff` in `docs/WORKTREE_WORKFLOW.md`. Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add docs/WORKTREE_WORKFLOW.md
git diff --cached --stat
git commit -m "Document user-only landings and ff-only merge style

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

After committing, tell the user which running sessions need to re-read the doc, since they won't pick up the change on their own.

---

### Task 6: Measure the test suite (checkpoint, no dependency change yet)

**Files:** none changed in this task.

**Interfaces:** produces timings for the user's decision on `pytest-xdist`.

The spec says the 107 s figure is a measurement, and the 25 s figure in the brief is a guess. Don't use either to decide without measuring.

- [ ] **Step 1: Time the serial suite**

Run from `ai-sandbox/academic-rag-model/`:
`Measure-Command { .venv\Scripts\python.exe -m pytest tests/ -q }` (PowerShell).
Record the wall-clock seconds and the pass/fail counts.

- [ ] **Step 2: Stop and report**

Do not install `pytest-xdist` yet. Report the serial timing to the user and ask for approval before installing it. Installing a dependency is a separate approval step under the workflow rules.

- [ ] **Step 3: After approval only**

If approved, install with `.venv\Scripts\python.exe -m pip install pytest-xdist`, time `.venv\Scripts\python.exe -m pytest tests/ -q -n auto`, and report both numbers. Adopt `-n auto` in `tools/land_branch.py`'s `run_checks` only if the parallel run passes and is faster. That change would need its own test and commit.

---

## Out of scope for this plan

- Spec item 6, the cross-repo land helper for `academic_notes/`. Deferred until the vault lane is decided.
- The metrics script. It lives in the scratchpad, outside the repo, and runs after the change has been in use. The user has a revisit reminder in memory.
- Any change to `.obsidian/` settings.

## Self-review

- **Spec coverage:** section 3 steps 1 to 4 are Task 2. Step 5 (ask the user) is agent behavior documented in Task 5. Step 6 (land) is documented in Task 5 and is a manual `--ff-only`. Step 7 (retire) is flagged by Task 4 and otherwise follows the existing retirement procedure. Section 5 items 1 to 5 are Tasks 2 to 4 (item 1 in Task 2, item 2 in Task 6, item 3 in Task 4, item 4 partly in Task 4's live-vault line, item 5 in Tasks 2 and 3). Section 2 decisions are Task 5. Section 7 metrics are supported by the log from Task 3.
- **Placeholder scan:** no TBD or TODO. Task 1 Step 1 tells the implementer how to pick an import style based on a Glob check, not a guess.
- **Type consistency:** `check(worktree, subdir, full)` in Task 2 is wrapped by Task 3 without a signature change; `CheckResult` fields match `asdict` in the log; `OUTCOMES` is defined before `main()` uses it.
- **Review Focus:** each of the five items has a test in Task 2 or Task 1.
