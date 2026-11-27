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
import sys
import tempfile
import types
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
from tools import reference_review
from tools.reference_checker import DEFAULT_CACHE, RegistryClient
from tools.impact_selection import select_tests
from tools.run_tests_chunked import ChunkResult, chunk_failed, run_all, run_selected

PROJECT_SUBDIR = "ai-sandbox/academic-rag-model"
# Live tests read these outside-project paths: test_lit_gap_report.py reads
# the root .gitignore; test_audit_website_sync.py validates .obsidian targets.
# Files that decide what may land, including which tests run and how their results count.
# `check` flags a branch that edits one, so the owner reviews it before approving.
GUARD_POLICY_PATHS = (
    "ai-sandbox/academic-rag-model/tools/guard_binaries.py",
    "ai-sandbox/academic-rag-model/tools/guard_binaries_allow.txt",
    "ai-sandbox/academic-rag-model/tools/land_branch.py",
    "ai-sandbox/academic-rag-model/tools/impact_selection.py",
    "ai-sandbox/academic-rag-model/tools/run_tests_chunked.py",
    ".githooks/pre-commit",
)
# Outside-project paths that tests read (grep of tests/, proposal 2026-11-11 rule 6).
# One list for both the check step and the land-time re-test: a change to any other
# path outside the project cannot affect a test, so it never selects tests.
# tests/tools/test_outside_test_inputs.py fails when a test reads a path not listed here.
OUTSIDE_TEST_INPUTS = (
    ".gitignore",  # test_lit_gap_report.py
    "ai-sandbox/.obsidian",  # test_audit_website_sync.py
    "ai-sandbox/research/independent-research/notes/00_overview-and-strategy/"
    "03_novelty-check/Novelty Check - Summary - v3.md",  # test_reference_checker.py
)
# Outside-project paths that only some tests read: a change selects just those tests, not the
# suite. The suite pins hub_config.json to a seed (tests/conftest.py); the one test below reads
# the shipped file.
OUTSIDE_TEST_TARGETS = {
    "ai-sandbox/academic-hub/hub_config.json": ("tests/core/env/test_shipped_hub_config.py",),
}


GUARD_MODULE_PATH = "ai-sandbox/academic-rag-model/tools/guard_binaries.py"


def main_guard(worktree: Path) -> types.ModuleType:
    """`guard_binaries` as it exists on main, so a branch cannot weaken its own judge.

    Loaded from `git show main:...` rather than run as a subprocess in the main
    checkout: the check then ignores uncommitted edits there and needs no cwd
    switch (git objects are shared, so `main..<sha>` still resolves). If main has
    no guard yet (a bootstrap), nothing can be weakened and this process's copy is used.
    """
    try:
        source = run_git(["show", f"{MAIN_BRANCH}:{GUARD_MODULE_PATH}"], worktree)
    except GitError:
        return guard_binaries
    module = types.ModuleType("_main_guard_binaries")
    module.__file__ = f"{MAIN_BRANCH}:{GUARD_MODULE_PATH}"
    sys.modules[module.__name__] = module  # dataclasses resolve annotations through it
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


class LandingError(RuntimeError):
    """The branch cannot be landed as it stands; the message says why."""


LOG_NAME = "agent-landing-log.jsonl"
FULL_RUN_MAX_AGE_HOURS = 48  # older than this: `check` warns, `land` does not narrow
OUTCOMES = ("landed", "declined")


def log_path(worktree: Path) -> Path:
    return git_common_dir(worktree) / LOG_NAME


def append_log(worktree: Path, entry: dict) -> None:
    record_entry = {"at": datetime.now(timezone.utc).isoformat(), **entry}
    with log_path(worktree).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record_entry, sort_keys=True) + "\n")


def read_log(worktree: Path) -> list[dict]:
    path = log_path(worktree)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def last_scheduled_full(entries: list[dict], now: datetime | None = None) -> dict | None:
    """Most recent `full-main` run: sha, result, failed and flaky chunks, age in days."""
    runs = [e for e in entries if e.get("event") == "scheduled_full"]
    if not runs:
        return None
    last = max(runs, key=lambda e: datetime.fromisoformat(e["at"]))
    age = ((now or datetime.now(timezone.utc)) - datetime.fromisoformat(last["at"])).total_seconds() / 86400
    return {"sha": last.get("sha", ""), "result": last.get("result", "?"),
            "failed_chunks": last.get("failed_chunks", []),
            "flaky_chunks": last.get("flaky_chunks", []), "age_days": age}


def full_main_warning(entries: list[dict], now: datetime | None = None) -> str:
    """Why the backstop needs attention, or "" when the last run is recent and passed."""
    rerun = "; run: python -m tools.land_branch full-main"
    runs = [e for e in entries if e.get("event") in ("scheduled_full", "scheduled_full_started")]
    if runs and runs[-1]["event"] == "scheduled_full_started":  # killed, crashed or still going
        return "the last full run of main did not finish" + rerun
    last = last_scheduled_full(entries, now)
    if last is None:
        return "no full run of main is logged" + rerun
    hours = last["age_days"] * 24
    if last["result"] != "passed":
        return (f"the last full run of main ({last['sha'][:8]}, {hours:.0f} hours old) FAILED: "
                + ", ".join(last["failed_chunks"] or ["?"]))
    if hours > FULL_RUN_MAX_AGE_HOURS:
        return f"the last full run of main is {hours:.0f} hours old (limit {FULL_RUN_MAX_AGE_HOURS})" + rerun
    return ""


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
    guard_policy_changed: list[str] = field(default_factory=list)  # branch edits a GUARD_POLICY_PATHS file
    citation_gate: list[dict] = field(default_factory=list)
    full_main_warning: str = ""  # the scheduled full run failed, is stale or never ran


def change_id(worktree: Path, base_ref: str = MAIN_BRANCH) -> str:
    """Fingerprint of the branch's diff against its merge-base with main.

    Whitespace-sensitive (unlike `git patch-id`), and blind to `index` and `@@`
    lines, which change when unrelated lines move, so a clean rebase keeps it.
    """
    base = run_git(["merge-base", base_ref, "HEAD"], worktree).strip()
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


def changed_research_notes(worktree: Path, prefix: str = "ai-sandbox/research/",
                           base_ref: str = MAIN_BRANCH) -> list[str]:
    """Research Markdown added or edited by this branch, excluding pure renames."""
    base = run_git(["merge-base", base_ref, "HEAD"], worktree).strip()
    fields = run_git(["diff", "--name-status", "-z", "-M", base, "HEAD"], worktree).split("\0")
    notes = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        i += 1
        if status.startswith(("R", "C")):
            i += 1  # source path
        path = fields[i]
        i += 1
        if (status in {"A", "M"} or status.startswith("R") and status != "R100") and (
                path.startswith(prefix) and path.lower().endswith(".md")):
            notes.append(path)
    return sorted(notes)


def citation_gate_error(result: reference_review.GateResult) -> LandingError:
    details = []
    for note in result.notes:
        if not note.blocked:
            continue
        action = []
        if note.defects:
            action.append("fix the note")
        if note.open_items:
            action.append("ask Claude to sync the review page")
        if note.unresolved:
            action.append("retry failed registry lookups")
        details.append(f"{note.note}: defects={note.defects}, open_items={note.open_items}, "
                       f"unresolved={note.unresolved}, URL-only={note.url_only}; " + ", ".join(action))
    return LandingError("citation gate: " + " | ".join(details))


def run_citation_gate(worktree: Path) -> reference_review.GateResult:
    paths = changed_research_notes(worktree)
    if not paths:
        return reference_review.GateResult([])
    client = RegistryClient(DEFAULT_CACHE, online=True)
    result = reference_review.gate([worktree / path for path in paths], client, repo_root=worktree)
    if result.blocked:
        raise citation_gate_error(result)
    return result


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
    """Test files a change can affect (tools.impact_selection). Empty means none, or
    that impact could not be bounded; selection_reason tells the two apart."""
    return select_tests(changed, project_root).files


def is_outside_test_input(path: str) -> bool:
    return any(path == target or path.startswith(target + "/") for target in OUTSIDE_TEST_INPUTS)


def outside_test_targets(outside: set[str]) -> list[str]:
    return sorted({t for p in outside for t in OUTSIDE_TEST_TARGETS.get(p, ())})


def _touches_guard_policy(changed: set[str], outside: set[str]) -> bool:
    prefix = PROJECT_SUBDIR + "/"
    inside = {p[len(prefix):] for p in GUARD_POLICY_PATHS if p.startswith(prefix)}
    return bool(changed & inside) or bool(outside & set(GUARD_POLICY_PATHS))


def selection_reason(
    changed: set[str], project_root: Path, full: bool = False,
    outside: set[str] | None = None,
) -> str:
    outside = outside or set()
    if full:
        return "explicit_full"
    if _touches_guard_policy(changed, outside):
        return "guard_policy_change"
    # Before doc_only: an allowlisted file can be Markdown (a test reads the Novelty Check note).
    if any(is_outside_test_input(p) for p in outside):
        return "allowlist_hit"
    if _is_documentation_only(changed | outside):
        return "doc_only"
    mapped = outside_test_targets(outside)
    if all(p.endswith(".md") for p in changed):
        return "targeted_outside" if mapped else "outside_project_only"  # only outside data changed; no test can read it
    selection = select_tests(changed, project_root)
    if selection.run_all_reason:
        return selection.run_all_reason  # helper_change, config_change, moved_or_deleted_file, no_tests_for_code
    if not selection.files and not mapped:
        return "data_unreferenced"  # only data no Python file names; no test can read it
    packages = {p.split("/")[1] if p.startswith("tests/") and p.count("/") > 1 else p.split("/")[0]
                for p in changed if not p.endswith(".md")}
    return "targeted_multi" if len(packages) > 1 else "targeted"


# Files that compute a re-test. When main changes one, the code this process already imported may
# be out of date, so `land` does not narrow.
SELECTOR_PATHS = ("tools/land_branch.py", "tools/impact_selection.py", "tools/run_tests_chunked.py")


def affected_tests(relative: set[str], outside: set[str], project_root: Path) -> set[str] | None:
    """Test files one side's changes can affect on this tree; None when that cannot be bounded."""
    if _touches_guard_policy(relative, outside) or any(is_outside_test_input(p) for p in outside):
        return None
    try:
        selection = select_tests(relative, project_root)
    except KeyError:  # a Python file the import graph does not cover (e.g. under archive/)
        return None
    if selection.run_all_reason:
        return None
    mapped = {t for t in outside_test_targets(outside) if (project_root / t).is_file()}
    return set(selection.files) | mapped


def overlap_tests(branch: set[str] | None, main: set[str] | None) -> set[str] | None:
    """Tests both sides can affect: only these can newly fail from combining them. An unbounded
    side contributes no limit, so the other side's set stands; None means run everything."""
    if branch is None:
        return main
    if main is None:
        return branch
    return branch & main


def narrowing_off_reason(entries: list[dict], repo: Path, now: datetime | None = None) -> str:
    """Why `land` may not narrow a re-test, or "" when the latest full run of main backs it."""
    runs = [e for e in entries if e.get("event") in ("scheduled_full", "scheduled_full_started")]
    if not runs:
        return "no full-main run is logged"
    last = runs[-1]  # the log is append-only, so the last record is the newest
    if last["event"] == "scheduled_full_started":
        return "the last full-main run did not finish"
    if last.get("result") != "passed":
        return "the last full-main run did not pass"
    try:
        age = (now or datetime.now(timezone.utc)) - datetime.fromisoformat(last["at"])
        hours = age.total_seconds() / 3600
    except (KeyError, TypeError, ValueError):
        return "the last full-main record has no readable time"
    if hours > FULL_RUN_MAX_AGE_HOURS:
        return f"the last full-main run is {hours:.0f} hours old"
    try:
        in_main = bool(last.get("sha")) and is_ancestor(repo, last["sha"], MAIN_BRANCH)
    except GitError:  # a commit this clone does not have
        in_main = False
    return "" if in_main else "the last full-main run was not on a commit in main"


TARGETED_REASONS = ("targeted", "targeted_multi", "multi_package", "targeted_outside")


@dataclass
class RetestPlan:
    mode: str  # "overlap", "approved" (as before TODO-0103) or "full"
    targets: list[str] | None = None  # replaces the approved targets; [] means nothing to run
    narrowing_off: str = ""


def retest_plan(
    approved: dict, branch_files: set[str], main_changed: set[str], worktree: Path, subdir: str,
    since_approval: set[str],
) -> RetestPlan:
    """What to re-run after rebasing onto a main that moved. Judged on the rebased tree, so an
    import either side added counts."""
    reason = approved.get("selection_reason") or approved.get("full_reason") or ""
    if approved.get("full") or reason == "explicit_full":
        return RetestPlan("approved", narrowing_off="the approved check was --full")
    prefix = subdir.rstrip("/") + "/" if subdir else ""
    root = worktree / subdir
    branch_relative = project_relative(branch_files, subdir)
    if (branch_relative & set(SELECTOR_PATHS)
            or _touches_guard_policy(branch_relative, {p for p in branch_files if not p.startswith(prefix)})):
        # the branch's own copy of this code is what would be deciding
        return RetestPlan("full", narrowing_off="the branch changes the guard or test selection code")
    # This process imported the selector before the first rebase, so any later change leaves it stale.
    if project_relative(since_approval, subdir) & set(SELECTOR_PATHS):
        return RetestPlan("approved", narrowing_off="main changed the test selection code")
    shared = overlap_tests(*(
        affected_tests(project_relative(files, subdir),
                       {p for p in files if not p.startswith(prefix)}, root)
        for files in (branch_files, main_changed)))
    if shared is None:
        return RetestPlan("full")
    path = log_path(worktree)
    entries = ([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
               if path.exists() else [])
    off = narrowing_off_reason(entries, worktree)
    if not off:
        return RetestPlan("overlap", targets=sorted(shared))
    # Narrowing is off: keep the approved selection, plus any shared test it lacks.
    targets = (sorted(set(approved.get("check_targets") or []) | shared)
               if reason in TARGETED_REASONS else None)
    return RetestPlan("approved", targets=targets, narrowing_off=off)


def run_checks(
    project_root: Path, changed: set[str], full: bool,
    *, outside: set[str] | None = None, chunk_results: list[ChunkResult] | None = None,
    reason: str | None = None, selected_targets: list[str] | None = None,
) -> tuple[str, list[str], float]:
    if reason is None:
        reason = selection_reason(changed, project_root, full, outside)
    if reason in ("doc_only", "outside_project_only", "data_unreferenced"):
        return "skipped", [], 0.0
    if reason not in TARGETED_REASONS:
        targets = ["tests/"]
    else:
        # A re-test reuses the approved files; main may have deleted one since (pytest exit 4).
        targets = [t for t in (selected_targets or []) if (project_root / t).exists()]
        if not targets:
            targets = select_test_targets(changed, project_root) if changed else []
            targets += [t for t in outside_test_targets(outside or set())
                        if t not in targets and (project_root / t).exists()]
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
    status, results, seconds = run_selected(project_root, targets)
    if chunk_results is not None:
        chunk_results.extend(results)
    for r in results:
        if chunk_failed(r.returncode):
            print(f"[FAILED] tests/{r.name}")
            print(r.stdout[-4000:])
    return status, targets, seconds


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
    # The main these tests run on. Main can move while they run; `land` must re-test that.
    base = run_git(["merge-base", MAIN_BRANCH, "HEAD"], worktree).strip()
    changed = changed_since_merge_base(worktree, MAIN_BRANCH, "HEAD")
    guard_violations = [str(v) for v in main_guard(worktree).check_range(worktree, MAIN_BRANCH)]
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
    gate_result = run_citation_gate(worktree) if checks in ("passed", "skipped") else reference_review.GateResult([])
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
        base=base,
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
        citation_gate=[asdict(note) for note in gate_result.notes],
        full_main_warning=full_main_warning(read_log(worktree)),
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
    if r.full_main_warning:
        print(f"WARNING:     {r.full_main_warning}")
    print(f"Guard:       {r.guard}")
    if r.citation_gate:
        for note in r.citation_gate:
            print(f"Citation gate: {note['note']}: defects={note['defects']}, "
                  f"open_items={note['open_items']}, unresolved={note['unresolved']}, "
                  f"URL-only={note['url_only']}")
    else:
        print("Citation gate: no added or modified research notes")
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
    approved_at: str = ""
    approved_base: str = ""
    approved_reason: str = ""
    retest_reason: str = ""
    retest_mode: str = ""
    retest_files: int = 0
    narrowing_off: str = ""


def approved_check(worktree: Path, branch: str, cid: str) -> dict:
    """The check to land on: an explicit --full pass wins, otherwise the newest pass.

    The same change ID means the same diff, so the newest check was computed by
    the current selection policy. An older "stronger" reason (e.g. non_py_file)
    may come from superseded policy and must not force a full retest.
    """
    path = log_path(worktree)
    entries = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    best: dict | None = None
    for line in reversed(entries):
        entry = json.loads(line)
        if (entry.get("event") == "check" and entry.get("branch") == branch
                and entry.get("change_id") == cid and entry.get("checks") in ("passed", "skipped")):
            reason = entry.get("selection_reason") or entry.get("full_reason")
            if entry.get("full") or reason == "explicit_full":
                return entry  # deliberate full request: newest of these wins
            if best is None:
                best = entry  # newest non-explicit pass; keep scanning for explicit full
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
    last_retest_reason = ""
    retest_mode, narrowing_off, retest_files = "", "", 0
    approved_reason = approved.get("selection_reason") or approved.get("full_reason") or ""
    print(f"Approved check: {approved.get('at', '?')} base {str(approved.get('base', ''))[:8]} "
          f"{approved.get('checks')} reason {approved_reason or '?'}")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        rebase_onto_main(worktree)
        if change_id(worktree) != cid:
            raise LandingError(f"the change differs from approved change {cid}; ask again")
        branch_files = changed_since_merge_base(worktree, MAIN_BRANCH, "HEAD")
        main_now = run_git(["rev-parse", MAIN_BRANCH], worktree).strip()
        policy_now = sorted(branch_files & set(GUARD_POLICY_PATHS))
        if policy_now and not set(policy_now) <= set(approved.get("guard_policy_changed") or []):
            raise LandingError(
                "this change edits the guard policy (" + ", ".join(policy_now) + ") but the approved "
                "check did not flag it; run check again and ask for approval of the new change ID")
        touched = sorted(branch_files & _files_between(worktree, approved["base"], main_now))
        if touched:
            raise LandingError("main changed files this branch also changes: " + ", ".join(touched))
        main_changed = _files_between(worktree, tested_base, main_now)
        code_delta = [p for p in project_relative(main_changed, subdir)
                      if not p.endswith(".md")]
        code_delta.extend(p for p in main_changed
                          if is_outside_test_input(p) or p in OUTSIDE_TEST_TARGETS)
        if code_delta and approved["checks"] != "skipped":
            prefix = subdir.rstrip("/") + "/" if subdir else ""
            plan = retest_plan(approved, branch_files, main_changed, worktree, subdir,
                               _files_between(worktree, approved["base"], main_now))
            retest_mode, narrowing_off = plan.mode, plan.narrowing_off
            count = "the full suite" if plan.mode == "full" else (
                "the approved selection" if plan.targets is None else f"{len(plan.targets)} test files")
            print(f"Retest mode: {plan.mode}, {count}"
                  + (f" (narrowing off: {plan.narrowing_off})" if plan.narrowing_off else ""))
            if plan.targets == [] and plan.mode == "overlap":
                tested_base = main_now  # no test depends on both sides; not a re-run
            else:
                retests += 1
                if retests > MAX_RETEST_ATTEMPTS:
                    raise LandingError(
                        f"main kept moving: {MAX_RETEST_ATTEMPTS} test re-runs without landing")
                retest_reason = ", ".join(sorted(code_delta)[:5]) + (
                    f" (+{len(code_delta) - 5} more)" if len(code_delta) > 5 else "")
                print(f"Retesting: main changed since {tested_base[:8]}: {retest_reason}")
                reason = approved.get("selection_reason") or approved.get("full_reason")
                selected = approved.get("check_targets") if reason else None
                full = approved.get("full", False)
                if plan.mode == "full":
                    full, reason, selected = True, None, None
                elif plan.targets is not None:
                    reason, selected = "targeted", plan.targets
                    retest_files += len(plan.targets)
                status, _, _ = run_checks(
                    worktree / subdir, project_relative(branch_files, subdir), full,
                    outside={p for p in branch_files if not p.startswith(prefix)},
                    reason=reason, selected_targets=selected,
                    chunk_results=retest_chunks,
                )
                if status not in ("passed", "skipped"):
                    raise LandingError("tests failed after rebasing onto the new main")
                tested_base = main_now
                last_retest_reason = retest_reason
        violations = main_guard(worktree).check_range(worktree, MAIN_BRANCH)
        if violations:
            raise LandingError(
                "binary guard refused the landing:\n  " + "\n  ".join(map(str, violations)))
        overlaps = find_overlaps(worktree, branch_files)
        if overlaps:
            raise LandingError("overlaps with uncommitted or in-progress work: " + ", ".join(overlaps))
        gate_result = run_citation_gate(worktree)
        for note in gate_result.notes:
            print(f"Citation gate: {note.note}: defects={note.defects}, "
                  f"open_items={note.open_items}, unresolved={note.unresolved}, "
                  f"URL-only={note.url_only}")
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
            approved_at=approved.get("at", ""), approved_base=approved.get("base", ""),
            approved_reason=approved_reason, retest_reason=last_retest_reason,
            retest_mode=retest_mode, retest_files=retest_files, narrowing_off=narrowing_off,
        )
    raise LandingError(f"main kept moving: no landing after {MAX_ATTEMPTS} attempts")


def full_main(
    worktree: Path, *, runner=None, subdir: str = PROJECT_SUBDIR,
) -> dict:
    """Run the full chunked suite on origin/main in a scratch worktree and log it.

    Static test selection cannot see run-time imports or subprocess-only tests, so
    this scheduled run is the backstop. The scratch worktree is detached, lives in
    the system temp dir (never the main checkout) and is removed afterwards.
    Failed chunks are re-run once: one that then passes is logged as flaky, not as
    a regression. `runner` replaces `run_all` in tests.
    """
    runner = runner or run_all
    run_git(["fetch", "origin", MAIN_BRANCH], worktree)
    sha = run_git(["rev-parse", f"origin/{MAIN_BRANCH}"], worktree).strip()
    # Logged first: a run that is killed or crashes leaves this as the newest record.
    append_log(worktree, {"event": "scheduled_full_started", "sha": sha})
    scratch = Path(tempfile.mkdtemp(prefix="full-main-"))
    tree = scratch / "tree"
    run_git(["worktree", "add", "--detach", str(tree), sha], worktree)
    try:
        status, results, seconds = runner(tree / subdir)
        first_failed = [r.name for r in results if chunk_failed(r.returncode)]
        reruns: list[ChunkResult] = []
        if first_failed:
            print(f"Re-running failed chunks once: {', '.join(first_failed)}")
            _, reruns, rerun_seconds = runner(tree / subdir, only=first_failed)
            seconds += rerun_seconds
        # A chunk is cleared only if its re-run actually ran and passed.
        cleared = {r.name for r in reruns if not chunk_failed(r.returncode)}
        still_failed = [n for n in first_failed if n not in cleared]
        if first_failed and not still_failed:
            status = "passed"
    finally:
        run_git(["worktree", "remove", "--force", str(tree)], worktree)
        scratch.rmdir()
    entry = {
        "sha": sha,
        "result": status,
        "seconds": round(seconds, 1),
        "failed_chunks": still_failed,
        "flaky_chunks": [n for n in first_failed if n in cleared],
        "rerun_timings": [{"name": r.name, "returncode": r.returncode, "seconds": round(r.seconds, 1)}
                          for r in reruns],
        "chunk_timings": [{"name": r.name, "returncode": r.returncode, "seconds": round(r.seconds, 1)}
                          for r in results],
    }
    append_log(worktree, {"event": "scheduled_full", **entry})
    return entry


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
    p_full = sub.add_parser("full-main", help="run the full suite on origin/main in a scratch worktree")
    p_full.add_argument("--worktree", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.cmd == "full-main":
        try:
            entry = full_main(args.worktree.resolve())
        except GitError as exc:
            print(f"NOT RUN: {exc}", file=sys.stderr)
            return 1
        print(f"full-main {entry['sha'][:8]}: {entry['result']} in {entry['seconds']}s"
              + (f"; failed: {', '.join(entry['failed_chunks'])}" if entry["failed_chunks"] else "")
              + (f"; flaky (passed on re-run): {', '.join(entry['flaky_chunks'])}" if entry["flaky_chunks"] else ""))
        return 0 if entry["result"] == "passed" else 1
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
        prefix = "STOP" if str(exc).startswith("citation gate:") else "NOT LANDABLE"
        print(f"{prefix}: {exc}", file=sys.stderr)
        return 1
    print_summary(result)
    return 0 if result.checks in ("passed", "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
